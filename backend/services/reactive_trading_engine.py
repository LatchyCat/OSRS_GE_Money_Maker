"""
Real-Time Reactive Trading Engine

This service creates a reactive, event-driven trading system that:
- Continuously monitors price changes and market conditions
- Automatically updates recommendations based on new data
- Triggers real-time alerts for significant market events
- Maintains WebSocket connections for live frontend updates
- Implements smart caching and update scheduling
- Provides autonomous market intelligence

The system is designed to be truly reactive - responding to market changes
in real-time rather than requiring manual refresh or periodic updates.
"""

import asyncio
import logging
import json
import weakref
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import hashlib

from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, F, Count, Sum, Avg
from django.db import models
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .unified_data_ingestion_service import UnifiedDataIngestionService
from .price_pattern_analysis_service import PricePatternAnalysisService
from .context_aware_chat_service import ContextAwareChatService
from .ollama_ai_service import TradingView
from apps.items.models import Item
from apps.prices.models import (
    HistoricalPricePoint, PriceTrend, MarketAlert, PriceSnapshot, ProfitCalculation
)

logger = logging.getLogger(__name__)


class UpdatePriority(Enum):
    """Priority levels for reactive updates."""
    CRITICAL = "critical"  # Flash crashes, major breakouts
    HIGH = "high"         # Strong trends, pattern confirmations
    MEDIUM = "medium"     # Regular price changes, volume shifts
    LOW = "low"           # Minor fluctuations, maintenance updates


class EventType(Enum):
    """Types of market events that trigger reactions."""
    PRICE_CHANGE = "price_change"
    VOLUME_SURGE = "volume_surge"
    TREND_REVERSAL = "trend_reversal"
    PATTERN_DETECTED = "pattern_detected"
    BREAKOUT_CONFIRMED = "breakout_confirmed"
    ALERT_TRIGGERED = "alert_triggered"
    RECOMMENDATION_UPDATE = "recommendation_update"


@dataclass
class MarketEvent:
    """Represents a market event that requires reactive processing."""
    event_id: str
    event_type: EventType
    item_id: int
    priority: UpdatePriority
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=timezone.now)
    processed: bool = False
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class RecommendationUpdate:
    """Represents an updated recommendation to be pushed to frontend."""
    item_id: int
    item_name: str
    update_type: str  # 'price_change', 'trend_update', 'alert', 'pattern'
    message: str
    confidence: float
    priority: UpdatePriority
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=timezone.now)


@dataclass
class WebSocketSubscription:
    """Tracks WebSocket subscriptions for different trading views."""
    channel_name: str
    user_id: Optional[str]
    trading_view: TradingView
    item_filters: Set[int] = field(default_factory=set)  # Specific items to watch
    last_update: datetime = field(default_factory=timezone.now)
    active: bool = True


class ReactiveTaskScheduler:
    """Manages scheduling and execution of reactive tasks."""
    
    def __init__(self):
        self.pending_tasks: Dict[str, asyncio.Task] = {}
        self.task_queues: Dict[UpdatePriority, asyncio.Queue] = {
            priority: asyncio.Queue() for priority in UpdatePriority
        }
        self.running = False
        self.workers: Dict[UpdatePriority, asyncio.Task] = {}
    
    async def start(self):
        """Start the reactive task scheduler."""
        if self.running:
            return
        
        self.running = True
        logger.info("🚀 Starting reactive task scheduler")
        
        # Start priority-based workers
        self.workers[UpdatePriority.CRITICAL] = asyncio.create_task(
            self._process_priority_queue(UpdatePriority.CRITICAL, max_concurrent=5)
        )
        self.workers[UpdatePriority.HIGH] = asyncio.create_task(
            self._process_priority_queue(UpdatePriority.HIGH, max_concurrent=3)
        )
        self.workers[UpdatePriority.MEDIUM] = asyncio.create_task(
            self._process_priority_queue(UpdatePriority.MEDIUM, max_concurrent=2)
        )
        self.workers[UpdatePriority.LOW] = asyncio.create_task(
            self._process_priority_queue(UpdatePriority.LOW, max_concurrent=1)
        )
    
    async def stop(self):
        """Stop the reactive task scheduler."""
        if not self.running:
            return
        
        self.running = False
        logger.info("🛑 Stopping reactive task scheduler")
        
        # Cancel all workers
        for worker in self.workers.values():
            worker.cancel()
        
        # Cancel pending tasks
        for task in self.pending_tasks.values():
            task.cancel()
        
        self.pending_tasks.clear()
    
    async def schedule_event(self, event: MarketEvent, handler: Callable):
        """Schedule a market event for processing."""
        await self.task_queues[event.priority].put((event, handler))
    
    async def _process_priority_queue(self, priority: UpdatePriority, max_concurrent: int):
        """Process events from a priority queue."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        while self.running:
            try:
                # Get next event from queue
                event, handler = await self.task_queues[priority].get()
                
                # Process with concurrency limit
                async def process_with_semaphore():
                    async with semaphore:
                        try:
                            await handler(event)
                            event.processed = True
                            logger.debug(f"Processed {event.event_type.value} event for item {event.item_id}")
                        except Exception as e:
                            event.retry_count += 1
                            if event.retry_count < event.max_retries:
                                # Retry with exponential backoff
                                await asyncio.sleep(2 ** event.retry_count)
                                await self.task_queues[priority].put((event, handler))
                            else:
                                logger.error(f"Failed to process event {event.event_id} after {event.max_retries} retries: {e}")
                
                # Start processing task
                task = asyncio.create_task(process_with_semaphore())
                self.pending_tasks[event.event_id] = task
                
                # Clean up completed tasks
                def cleanup_task(task_future):
                    self.pending_tasks.pop(event.event_id, None)
                
                task.add_done_callback(cleanup_task)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in {priority.value} priority queue: {e}")
                await asyncio.sleep(1)
    
    async def process_scheduled_tasks(self):
        """Process scheduled tasks - placeholder for monitoring cycle integration."""
        # This is called by the monitoring cycle
        # For now, just check if scheduler is running
        if not self.running:
            await self.start()
        
        # Clean up completed tasks
        completed_tasks = [
            event_id for event_id, task in self.pending_tasks.items() 
            if task.done()
        ]
        for event_id in completed_tasks:
            self.pending_tasks.pop(event_id, None)


class ReactiveTradingEngine:
    """
    Main reactive trading engine that orchestrates real-time market intelligence.
    """
    
    _instance = None
    _initialized = False
    
    @classmethod
    def get_instance(cls, config: Dict[str, Any] = None) -> 'ReactiveTradingEngine':
        """
        Get or create the singleton instance of the reactive trading engine.
        
        Args:
            config: Optional configuration dictionary for initial setup
            
        Returns:
            ReactiveTradingEngine: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any] = None):
        # Prevent multiple initialization of singleton
        if self._initialized:
            return
            
        # Configuration
        self.config = config or {
            'monitoring_interval': 30,
            'pattern_analysis_interval': 300,
            'recommendation_update_interval': 600,
            'volume_surge_threshold': 2.0,
            'test_mode': False
        }
        
        # Core services
        self.ingestion_service = None  # Will be initialized async
        self.pattern_analyzer = PricePatternAnalysisService()
        self.chat_service = ContextAwareChatService()
        self.task_scheduler = ReactiveTaskScheduler()
        
        # WebSocket management
        self.channel_layer = get_channel_layer()
        self.active_subscriptions: Dict[str, WebSocketSubscription] = {}
        self.subscription_groups: Dict[TradingView, Set[str]] = defaultdict(set)
        
        # Event tracking
        self.event_history: deque = deque(maxlen=1000)  # Recent events
        self.price_change_thresholds = {
            UpdatePriority.CRITICAL: 0.15,  # 15% price change
            UpdatePriority.HIGH: 0.08,       # 8% price change  
            UpdatePriority.MEDIUM: 0.05,     # 5% price change
            UpdatePriority.LOW: 0.02         # 2% price change
        }
        
        # Update frequencies (in seconds)
        self.update_intervals = {
            'critical_items': 30,     # 30 seconds for high-priority items
            'active_items': 120,      # 2 minutes for active items
            'regular_items': 300,     # 5 minutes for regular items
            'pattern_analysis': 180,  # 3 minutes for pattern updates
            'trend_analysis': 600,    # 10 minutes for trend analysis
        }
        
        # Cache keys
        self.cache_keys = {
            'item_priorities': 'reactive:item_priorities',
            'last_prices': 'reactive:last_prices',
            'active_alerts': 'reactive:active_alerts',
        }
        
        # System state
        self.running = False
        self.background_tasks: List[asyncio.Task] = []
        
        # Mark as initialized
        self._initialized = True
    
    async def initialize(self):
        """Initialize the reactive trading engine."""
        logger.info("🔧 Initializing Reactive Trading Engine")
        
        # Initialize services
        self.ingestion_service = UnifiedDataIngestionService()
        await self.ingestion_service.__aenter__()
        
        # Initialize chat service
        await self.chat_service.initialize_chat_system()
        
        # Load item priorities from cache or database
        await self._load_item_priorities()
        
        # Start task scheduler
        await self.task_scheduler.start()
        
        logger.info("✅ Reactive Trading Engine initialized")
    
    async def start(self):
        """Start the reactive trading engine."""
        if self.running:
            logger.warning("Reactive engine already running")
            return
        
        self.running = True
        logger.info("🚀 Starting Reactive Trading Engine")
        
        # Start background monitoring tasks
        self.background_tasks = [
            asyncio.create_task(self._monitor_price_changes()),
            asyncio.create_task(self._monitor_volume_changes()),
            asyncio.create_task(self._monitor_pattern_signals()),
            asyncio.create_task(self._update_recommendations()),
            asyncio.create_task(self._cleanup_old_data()),
        ]
        
        logger.info("✅ Reactive Trading Engine started with background monitoring")
    
    async def stop(self):
        """Stop the reactive trading engine."""
        if not self.running:
            return
        
        self.running = False
        logger.info("🛑 Stopping Reactive Trading Engine")
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Stop task scheduler
        await self.task_scheduler.stop()
        
        # Clean up services
        if self.ingestion_service:
            await self.ingestion_service.__aexit__(None, None, None)
        
        logger.info("✅ Reactive Trading Engine stopped")
    
    async def register_websocket_subscription(self, subscription: WebSocketSubscription):
        """Register a WebSocket subscription for real-time updates."""
        self.active_subscriptions[subscription.channel_name] = subscription
        self.subscription_groups[subscription.trading_view].add(subscription.channel_name)
        
        logger.info(f"📡 Registered WebSocket subscription: {subscription.trading_view.value} view")
        
        # Send initial data to new subscriber
        await self._send_initial_data(subscription)
    
    async def unregister_websocket_subscription(self, channel_name: str):
        """Unregister a WebSocket subscription."""
        if channel_name in self.active_subscriptions:
            subscription = self.active_subscriptions[channel_name]
            self.subscription_groups[subscription.trading_view].discard(channel_name)
            del self.active_subscriptions[channel_name]
            
            logger.info(f"📡 Unregistered WebSocket subscription: {channel_name}")
    
    async def subscribe_to_updates(self, channel_name: str):
        """
        Subscribe a WebSocket channel to trading intelligence updates.
        This method is called by the WebSocket consumer.
        
        Args:
            channel_name: The WebSocket channel name to subscribe
        """
        try:
            # Check if channel is already subscribed to prevent infinite loops
            if channel_name in self.active_subscriptions:
                logger.debug(f"⚠️ Channel {channel_name} already subscribed, skipping registration")
                return
            
            # Create a default subscription for trading intelligence
            subscription = WebSocketSubscription(
                channel_name=channel_name,
                user_id=None,
                trading_view=TradingView.GENERAL,  # Default to general trading view
                item_filters=set()  # No specific item filters by default
            )
            
            # Register the subscription
            await self.register_websocket_subscription(subscription)
            
            logger.info(f"✅ Successfully subscribed channel {channel_name} to trading updates")
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe channel {channel_name}: {e}")
            raise
    
    async def _monitor_price_changes(self):
        """Monitor price changes and trigger reactive updates."""
        logger.info("👁️ Starting price change monitoring")
        
        while self.running:
            try:
                # Get current prices for active items
                active_items = await self._get_active_items()
                
                if active_items:
                    # Ingest latest price data
                    results = await self.ingestion_service.ingest_complete_market_data(
                        item_ids=active_items[:50],  # Limit to avoid overload
                        include_historical=True,
                        historical_periods_5m=2,  # Just last 2 periods for comparison
                        historical_periods_1h=1
                    )
                    
                    # Analyze price changes
                    await self._analyze_price_changes(active_items)
                
                # Wait based on system load and priority
                await asyncio.sleep(self.update_intervals['active_items'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Price monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _monitor_volume_changes(self):
        """Monitor volume changes for surge detection."""
        logger.info("📊 Starting volume change monitoring")
        
        while self.running:
            try:
                # Get items with recent volume data
                volume_items = await self._get_high_volume_items()
                
                for item_id in volume_items:
                    # Check for volume surges
                    volume_change = await self._calculate_volume_change(item_id)
                    
                    if volume_change > 2.0:  # 200% volume increase
                        event = MarketEvent(
                            event_id=f"volume_surge_{item_id}_{int(timezone.now().timestamp())}",
                            event_type=EventType.VOLUME_SURGE,
                            item_id=item_id,
                            priority=UpdatePriority.HIGH,
                            data={'volume_change': volume_change}
                        )
                        
                        await self.task_scheduler.schedule_event(event, self._handle_volume_surge)
                
                await asyncio.sleep(self.update_intervals['pattern_analysis'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Volume monitoring error: {e}")
                await asyncio.sleep(120)
    
    async def _monitor_pattern_signals(self):
        """Monitor for new pattern detection and trend changes."""
        logger.info("🎯 Starting pattern signal monitoring")
        
        while self.running:
            try:
                # Get items with recent trading activity
                pattern_items = await self._get_pattern_analysis_items()
                
                # Batch process pattern analysis
                batch_size = 10
                for i in range(0, len(pattern_items), batch_size):
                    batch = pattern_items[i:i+batch_size]
                    
                    # Process each item in the batch
                    tasks = []
                    for item_id in batch:
                        task = asyncio.create_task(self._check_pattern_changes(item_id))
                        tasks.append(task)
                    
                    # Wait for batch completion with timeout
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*tasks, return_exceptions=True), 
                            timeout=60
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"Pattern analysis batch timeout for items: {batch}")
                
                await asyncio.sleep(self.update_intervals['pattern_analysis'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pattern monitoring error: {e}")
                await asyncio.sleep(180)
    
    async def _update_recommendations(self):
        """Generate and broadcast updated recommendations."""
        logger.info("🔄 Starting recommendation updates")
        
        while self.running:
            try:
                # Update recommendations for each trading view
                for trading_view in TradingView:
                    if trading_view == TradingView.GENERAL:
                        continue
                    
                    # Get top items for this view
                    view_items = await self._get_items_for_view(trading_view)
                    
                    if view_items:
                        # Generate updated recommendations
                        recommendations = await self._generate_view_recommendations(
                            trading_view, view_items[:10]
                        )
                        
                        # Broadcast to subscribers
                        await self._broadcast_recommendation_updates(
                            trading_view, recommendations
                        )
                
                await asyncio.sleep(self.update_intervals['trend_analysis'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Recommendation update error: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_old_data(self):
        """Clean up old events and cache data."""
        logger.info("🧹 Starting data cleanup")
        
        while self.running:
            try:
                # Clean up old events
                cutoff_time = timezone.now() - timedelta(hours=6)
                self.event_history = deque(
                    [event for event in self.event_history if event.timestamp > cutoff_time],
                    maxlen=1000
                )
                
                # Clean up old market alerts
                await asyncio.to_thread(
                    MarketAlert.objects.filter(
                        created_at__lt=timezone.now() - timedelta(days=1),
                        is_active=False
                    ).delete
                )
                
                # Clean up stale cache entries
                await self._cleanup_stale_cache()
                
                await asyncio.sleep(3600)  # Run every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(1800)
    
    async def _analyze_price_changes(self, item_ids: List[int]):
        """Analyze price changes and generate events."""
        last_prices = cache.get(self.cache_keys['last_prices'], {})
        
        # Get current prices
        def get_current_prices():
            current_prices = {}
            snapshots = PriceSnapshot.objects.filter(
                item__item_id__in=item_ids,
                created_at__gte=timezone.now() - timedelta(minutes=30)
            ).select_related('item')
            
            for snapshot in snapshots:
                if snapshot.volume_weighted_price:
                    current_prices[snapshot.item.item_id] = {
                        'price': snapshot.volume_weighted_price,
                        'volume': snapshot.total_volume or 0,
                        'timestamp': snapshot.created_at
                    }
            
            return current_prices
        
        current_prices = await asyncio.to_thread(get_current_prices)
        
        # Compare with last known prices
        for item_id, current_data in current_prices.items():
            if item_id in last_prices:
                last_price = last_prices[item_id]['price']
                current_price = current_data['price']
                
                if last_price > 0:
                    price_change_pct = abs(current_price - last_price) / last_price
                    
                    # Determine priority based on price change magnitude
                    priority = UpdatePriority.LOW
                    for threshold_priority, threshold in self.price_change_thresholds.items():
                        if price_change_pct >= threshold:
                            priority = threshold_priority
                            break
                    
                    # Generate event if significant change
                    if price_change_pct >= self.price_change_thresholds[UpdatePriority.LOW]:
                        event = MarketEvent(
                            event_id=f"price_change_{item_id}_{int(timezone.now().timestamp())}",
                            event_type=EventType.PRICE_CHANGE,
                            item_id=item_id,
                            priority=priority,
                            data={
                                'old_price': last_price,
                                'new_price': current_price,
                                'change_pct': price_change_pct,
                                'volume': current_data['volume']
                            }
                        )
                        
                        await self.task_scheduler.schedule_event(event, self._handle_price_change)
        
        # Update cache with current prices
        cache.set(self.cache_keys['last_prices'], current_prices, timeout=3600)
    
    async def _handle_price_change(self, event: MarketEvent):
        """Handle a price change event."""
        item_id = event.item_id
        change_data = event.data
        
        try:
            # Get item info
            item = await asyncio.to_thread(Item.objects.get, item_id=item_id)
            
            # Create update message
            direction = "up" if change_data['new_price'] > change_data['old_price'] else "down"
            update = RecommendationUpdate(
                item_id=item_id,
                item_name=item.name,
                update_type='price_change',
                message=f"{item.name} price moved {direction} {change_data['change_pct']:.1%} to {change_data['new_price']:,} GP",
                confidence=0.9,
                priority=event.priority,
                data=change_data
            )
            
            # Broadcast to relevant subscribers
            await self._broadcast_update_to_subscribers(update)
            
            # If significant change, trigger pattern analysis
            if event.priority in [UpdatePriority.CRITICAL, UpdatePriority.HIGH]:
                pattern_event = MarketEvent(
                    event_id=f"pattern_check_{item_id}_{int(timezone.now().timestamp())}",
                    event_type=EventType.PATTERN_DETECTED,
                    item_id=item_id,
                    priority=UpdatePriority.MEDIUM,
                    data={'trigger': 'significant_price_change'}
                )
                
                await self.task_scheduler.schedule_event(pattern_event, self._handle_pattern_check)
        
        except Exception as e:
            logger.error(f"Failed to handle price change event: {e}")
    
    async def _handle_volume_surge(self, event: MarketEvent):
        """Handle a volume surge event."""
        item_id = event.item_id
        volume_data = event.data
        
        try:
            item = await asyncio.to_thread(Item.objects.get, item_id=item_id)
            
            update = RecommendationUpdate(
                item_id=item_id,
                item_name=item.name,
                update_type='volume_surge',
                message=f"{item.name} volume surged {volume_data['volume_change']:.1f}x - increased trading activity detected",
                confidence=0.8,
                priority=event.priority,
                data=volume_data
            )
            
            await self._broadcast_update_to_subscribers(update)
        
        except Exception as e:
            logger.error(f"Failed to handle volume surge event: {e}")
    
    async def _handle_pattern_check(self, event: MarketEvent):
        """Handle a pattern analysis check."""
        item_id = event.item_id
        
        try:
            # Run pattern analysis
            patterns = await self.pattern_analyzer.detect_price_patterns(item_id, 24)
            signals = await self.pattern_analyzer.generate_market_signals(item_id)
            
            if patterns or signals:
                item = await asyncio.to_thread(Item.objects.get, item_id=item_id)
                
                # Create pattern update
                pattern_info = []
                if patterns:
                    for pattern in patterns[:2]:  # Top 2 patterns
                        pattern_info.append(f"{pattern.pattern_name} ({pattern.confidence:.1%})")
                
                signal_info = []
                if signals:
                    priority_signals = [s for s in signals if s.priority in ['critical', 'high']]
                    for signal in priority_signals[:2]:
                        signal_info.append(f"{signal.signal_type}: {signal.message}")
                
                if pattern_info or signal_info:
                    message_parts = []
                    if pattern_info:
                        message_parts.append(f"Patterns: {', '.join(pattern_info)}")
                    if signal_info:
                        message_parts.append(f"Signals: {'; '.join(signal_info)}")
                    
                    update = RecommendationUpdate(
                        item_id=item_id,
                        item_name=item.name,
                        update_type='pattern_detected',
                        message=f"{item.name} - {' | '.join(message_parts)}",
                        confidence=0.75,
                        priority=UpdatePriority.HIGH,
                        data={
                            'patterns': len(patterns),
                            'signals': len(signals)
                        }
                    )
                    
                    await self._broadcast_update_to_subscribers(update)
        
        except Exception as e:
            logger.error(f"Failed to handle pattern check: {e}")
    
    async def _broadcast_update_to_subscribers(self, update: RecommendationUpdate):
        """Broadcast update to relevant WebSocket subscribers."""
        if not self.channel_layer:
            return
        
        # Determine which subscribers should receive this update
        relevant_channels = set()
        
        # Add subscribers watching this specific item
        for channel_name, subscription in self.active_subscriptions.items():
            if (not subscription.item_filters or 
                update.item_id in subscription.item_filters):
                relevant_channels.add(channel_name)
        
        if relevant_channels:
            message = {
                'type': 'recommendation.update',
                'data': {
                    'item_id': update.item_id,
                    'item_name': update.item_name,
                    'update_type': update.update_type,
                    'message': update.message,
                    'confidence': update.confidence,
                    'priority': update.priority.value,
                    'timestamp': update.timestamp.isoformat(),
                    'data': update.data
                }
            }
            
            # Send to all relevant channels
            tasks = []
            for channel_name in relevant_channels:
                task = asyncio.create_task(
                    self._send_to_channel(channel_name, message)
                )
                tasks.append(task)
            
            # Wait for all sends to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.debug(f"Broadcasted {update.update_type} update to {len(tasks)} subscribers")
    
    async def _send_to_channel(self, channel_name: str, message: dict):
        """Send message to specific WebSocket channel."""
        try:
            await self.channel_layer.send(channel_name, message)
        except Exception as e:
            logger.warning(f"Failed to send to channel {channel_name}: {e}")
            # Remove dead channel
            await self.unregister_websocket_subscription(channel_name)
    
    # Utility methods for getting item lists and data
    async def _get_active_items(self) -> List[int]:
        """Get list of currently active/high-priority items."""
        def get_items():
            # Get items with recent trading activity
            recent_cutoff = timezone.now() - timedelta(hours=6)
            
            active_items = HistoricalPricePoint.objects.filter(
                timestamp__gte=recent_cutoff,
                total_volume__gt=50  # Minimum volume threshold
            ).values_list('item__item_id', flat=True).distinct()
            
            return list(active_items)[:100]  # Limit to top 100
        
        return await asyncio.to_thread(get_items)
    
    async def _get_high_volume_items(self) -> List[int]:
        """Get items with high trading volumes for monitoring."""
        def get_items():
            recent_cutoff = timezone.now() - timedelta(hours=2)
            
            volume_items = HistoricalPricePoint.objects.filter(
                timestamp__gte=recent_cutoff,
                total_volume__gt=200  # Higher threshold for volume monitoring
            ).values_list('item__item_id', flat=True).distinct()
            
            return list(volume_items)[:50]
        
        return await asyncio.to_thread(get_items)
    
    async def _get_pattern_analysis_items(self) -> List[int]:
        """Get items that should be analyzed for patterns."""
        def get_items():
            # Items with sufficient data for pattern analysis
            cutoff_time = timezone.now() - timedelta(hours=24)
            
            pattern_items = HistoricalPricePoint.objects.filter(
                timestamp__gte=cutoff_time
            ).values('item__item_id').annotate(
                point_count=models.Count('id')
            ).filter(
                point_count__gte=10  # At least 10 data points
            ).values_list('item__item_id', flat=True)
            
            return list(pattern_items)[:30]  # Limit for performance
        
        return await asyncio.to_thread(get_items)
    
    async def _get_items_for_view(self, trading_view: TradingView) -> List[int]:
        """Get items relevant for a specific trading view."""
        def get_view_items():
            # Get recent items with good trading volume
            cutoff_time = timezone.now() - timedelta(hours=6)
            
            # Base query for items with recent activity
            recent_items = HistoricalPricePoint.objects.filter(
                timestamp__gte=cutoff_time
            ).values('item__item_id').annotate(
                total_volume=Sum('total_volume'),
                avg_high_price=Avg('avg_high_price'),
                avg_low_price=Avg('avg_low_price'),
                data_points=Count('id')
            ).filter(
                total_volume__gt=100,  # Minimum volume
                data_points__gte=3     # Minimum data points
            )
            
            # For now, return same items for all views
            # In the future, could filter based on trading view type
            item_ids = list(recent_items.values_list('item__item_id', flat=True))
            
            return item_ids[:20]  # Limit for performance
        
        return await asyncio.to_thread(get_view_items)
    
    async def _load_item_priorities(self):
        """Load item priorities from cache or calculate them."""
        priorities = cache.get(self.cache_keys['item_priorities'])
        
        if not priorities:
            # Calculate priorities based on recent activity
            def calculate_priorities():
                from django.db.models import Avg, Sum
                
                recent_cutoff = timezone.now() - timedelta(days=3)
                
                item_stats = HistoricalPricePoint.objects.filter(
                    timestamp__gte=recent_cutoff
                ).values('item__item_id').annotate(
                    avg_volume=Avg('total_volume'),
                    total_volume=Sum('total_volume'),
                    data_points=Count('id')
                ).filter(
                    avg_volume__gt=10
                )
                
                priorities = {}
                for stat in item_stats:
                    item_id = stat['item__item_id']
                    score = (stat['avg_volume'] or 0) * (stat['data_points'] or 1)
                    
                    if score > 1000:
                        priorities[item_id] = UpdatePriority.HIGH
                    elif score > 500:
                        priorities[item_id] = UpdatePriority.MEDIUM
                    else:
                        priorities[item_id] = UpdatePriority.LOW
                
                return priorities
            
            priorities = await asyncio.to_thread(calculate_priorities)
            cache.set(self.cache_keys['item_priorities'], priorities, timeout=3600)
        
        return priorities
    
    async def _send_initial_data(self, subscription: WebSocketSubscription):
        """Send initial data to new WebSocket subscriber."""
        try:
            # Get recent alerts for this view
            recent_alerts = await asyncio.to_thread(
                list,
                MarketAlert.objects.filter(
                    is_active=True,
                    created_at__gte=timezone.now() - timedelta(hours=1)
                ).select_related('item').order_by('-created_at')[:5]
            )
            
            alerts_data = [
                {
                    'item_id': alert.item.item_id,
                    'item_name': alert.item.name,
                    'alert_type': alert.alert_type,
                    'message': alert.message,
                    'priority': alert.priority,
                    'confidence': alert.confidence_score,
                    'created_at': alert.created_at.isoformat()
                }
                for alert in recent_alerts
            ]
            
            initial_message = {
                'type': 'initial.data',
                'data': {
                    'trading_view': subscription.trading_view.value,
                    'alerts': alerts_data,
                    'timestamp': timezone.now().isoformat(),
                    'status': 'connected'
                }
            }
            
            await self._send_to_channel(subscription.channel_name, initial_message)
            
        except Exception as e:
            logger.error(f"Failed to send initial data: {e}")
    
    async def _calculate_volume_change(self, item_id: int) -> float:
        """Calculate volume change ratio for an item."""
        def get_volume_data():
            recent_cutoff = timezone.now() - timedelta(hours=2)
            older_cutoff = timezone.now() - timedelta(hours=6)
            
            recent_volume = HistoricalPricePoint.objects.filter(
                item__item_id=item_id,
                timestamp__gte=recent_cutoff
            ).aggregate(total=Sum('total_volume'))['total'] or 0
            
            older_volume = HistoricalPricePoint.objects.filter(
                item__item_id=item_id,
                timestamp__gte=older_cutoff,
                timestamp__lt=recent_cutoff
            ).aggregate(total=Sum('total_volume'))['total'] or 0
            
            return recent_volume, older_volume
        
        try:
            recent, older = await asyncio.to_thread(get_volume_data)
            
            if older > 0:
                return recent / older
            elif recent > 0:
                return 2.0  # Assume 100% increase if no historical data
            else:
                return 0.0
        except Exception as e:
            logger.debug(f"Volume change calculation failed for item {item_id}: {e}")
            return 0.0
    
    async def _cleanup_stale_cache(self):
        """Clean up stale cache entries."""
        # This would implement cache cleanup logic
        # For now, just clear old last_prices entries
        pass
    
    async def run_monitoring_cycle(self):
        """Run one complete monitoring cycle."""
        try:
            # Check if we're running
            if not self.running:
                return
            
            # Run scheduled tasks
            await self.task_scheduler.process_scheduled_tasks()
            
            # Log cycle completion
            logger.debug("Monitoring cycle completed successfully")
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            raise
    
    async def get_engine_status(self) -> Dict[str, Any]:
        """Get current engine status and statistics."""
        try:
            # Get basic status
            status = {
                'is_running': self.running,
                'active_subscriptions': len(self.active_subscriptions),
                'events_processed': len(self.event_history),
                'recommendations_updated': 0,  # Would track this
                'alerts_generated': 0,  # Would track this
                'last_price_check': timezone.now().isoformat(),
                'last_pattern_analysis': timezone.now().isoformat(),
            }
            
            # Add subscription details
            status['subscription_groups'] = {
                view.value: len(channels) 
                for view, channels in self.subscription_groups.items()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting engine status: {e}")
            return {
                'is_running': False,
                'error': str(e)
            }
    
    async def get_current_recommendations(self, route_type: str = 'all') -> List[Dict[str, Any]]:
        """Get current recommendations for a trading route."""
        try:
            # This would fetch current recommendations from the database
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Error getting recommendations for {route_type}: {e}")
            return []
    
    async def subscribe_to_item_updates(self, item_id: int, channel_name: str):
        """Subscribe to updates for a specific item."""
        try:
            # Create item-specific subscription
            subscription = WebSocketSubscription(
                channel_name=channel_name,
                user_id=None,
                trading_view=TradingView.GENERAL,
                item_filters={item_id}
            )
            
            await self.register_websocket_subscription(subscription)
            logger.debug(f"Subscribed {channel_name} to item {item_id} updates")
            
        except Exception as e:
            logger.error(f"Error subscribing to item {item_id} updates: {e}")
    
    async def unsubscribe_from_item_updates(self, item_id: int, channel_name: str):
        """Unsubscribe from updates for a specific item."""
        try:
            # Remove item-specific subscription
            if channel_name in self.active_subscriptions:
                subscription = self.active_subscriptions[channel_name]
                if item_id in subscription.item_filters:
                    subscription.item_filters.remove(item_id)
                    
                    # If no items left, remove subscription entirely
                    if not subscription.item_filters:
                        await self.unregister_websocket_subscription(channel_name)
                    
                    logger.debug(f"Unsubscribed {channel_name} from item {item_id} updates")
            
        except Exception as e:
            logger.error(f"Error unsubscribing from item {item_id} updates: {e}")
    
    async def subscribe_to_route_updates(self, route_type: str, channel_name: str):
        """Subscribe to updates for a trading route."""
        try:
            # Map route types to trading views
            # NOTE: These enum values MUST match the TradingView enum in ollama_ai_service.py
            # Any mismatch will cause infinite WebSocket subscription loops!
            route_view_map = {
                'high_alch': TradingView.HIGH_ALCHEMY,  # Fixed: was HIGH_ALCH, now HIGH_ALCHEMY
                'flipping': TradingView.FLIPPING,
                'decanting': TradingView.DECANTING,
                'crafting': TradingView.CRAFTING,
                'general': TradingView.GENERAL
            }
            
            # Check if channel is already subscribed to prevent infinite loops
            if channel_name in self.active_subscriptions:
                existing_subscription = self.active_subscriptions[channel_name]
                # Update the existing subscription to the new trading view
                existing_subscription.trading_view = route_view_map.get(route_type, TradingView.GENERAL)
                logger.debug(f"⚠️ Channel {channel_name} already subscribed, updating to {route_type} route")
                return
            
            trading_view = route_view_map.get(route_type, TradingView.GENERAL)
            
            subscription = WebSocketSubscription(
                channel_name=channel_name,
                user_id=None,
                trading_view=trading_view,
                item_filters=set()
            )
            
            await self.register_websocket_subscription(subscription)
            logger.debug(f"Subscribed {channel_name} to {route_type} route updates")
            
        except Exception as e:
            logger.error(f"Error subscribing to {route_type} route updates: {e}")
    
    async def unsubscribe_from_route_updates(self, route_type: str, channel_name: str):
        """Unsubscribe from updates for a trading route."""
        try:
            await self.unregister_websocket_subscription(channel_name)
            logger.debug(f"Unsubscribed {channel_name} from {route_type} route updates")
            
        except Exception as e:
            logger.error(f"Error unsubscribing from {route_type} route updates: {e}")
    
    async def unsubscribe_from_updates(self, channel_name: str):
        """Unsubscribe from all updates for a channel."""
        try:
            await self.unregister_websocket_subscription(channel_name)
            logger.debug(f"Unsubscribed {channel_name} from all updates")
            
        except Exception as e:
            logger.error(f"Error unsubscribing {channel_name} from updates: {e}")


# Global reactive engine instance
_reactive_engine: Optional[ReactiveTradingEngine] = None


async def get_reactive_engine() -> ReactiveTradingEngine:
    """Get or create the global reactive trading engine."""
    global _reactive_engine
    
    if _reactive_engine is None:
        _reactive_engine = ReactiveTradingEngine()
        await _reactive_engine.initialize()
        await _reactive_engine.start()
    
    return _reactive_engine


async def shutdown_reactive_engine():
    """Shutdown the global reactive trading engine."""
    global _reactive_engine
    
    if _reactive_engine is not None:
        await _reactive_engine.stop()
        _reactive_engine = None