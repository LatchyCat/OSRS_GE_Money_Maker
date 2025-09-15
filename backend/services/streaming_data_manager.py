"""
Streaming Data Manager

Handles real-time data ingestion, processing, and distribution for the trading terminal.
Implements data-reactive architecture with continuous market monitoring.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Avg, Max, Min, Count
from asgiref.sync import sync_to_async, async_to_sync
from channels.layers import get_channel_layer

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.realtime_engine.models import (
    MarketMomentum, VolumeAnalysis, RiskMetrics, 
    MarketEvent, StreamingDataStatus
)
from services.weirdgloop_api_client import WeirdGloopAPIClient
from services.timeseries_client import timeseries_client
import statistics

logger = logging.getLogger(__name__)

class StreamingDataManager:
    """
    Central manager for real-time market data streaming and processing.
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.api_client = WeirdGloopAPIClient()
        self.is_running = False
        self.update_intervals = {
            'high_volume': 60,      # 1 minute for high-volume items
            'medium_volume': 300,   # 5 minutes for medium-volume items
            'low_volume': 900,      # 15 minutes for low-volume items
            'calculations': 120,    # 2 minutes for calculations update
            'momentum': 180,        # 3 minutes for momentum analysis
        }
        
        # Cache keys
        self.cache_keys = {
            'momentum_data': 'streaming:momentum:{}',
            'volume_data': 'streaming:volume:{}',
            'risk_data': 'streaming:risk:{}',
            'market_events': 'streaming:events',
            'hot_items': 'streaming:hot_items',
        }
    
    async def start_streaming(self):
        """Start the continuous data streaming process."""
        if self.is_running:
            logger.warning("Streaming already running")
            return
        
        self.is_running = True
        logger.info("🚀 Starting data-reactive streaming system...")
        
        # Start concurrent streaming tasks
        tasks = [
            asyncio.create_task(self._stream_price_data()),
            asyncio.create_task(self._calculate_momentum()),
            asyncio.create_task(self._analyze_volume()),
            asyncio.create_task(self._assess_risks()),
            asyncio.create_task(self._detect_market_events()),
            asyncio.create_task(self._broadcast_updates()),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            self.is_running = False
            raise
    
    async def stop_streaming(self):
        """Stop the streaming system gracefully."""
        logger.info("🛑 Stopping streaming system...")
        self.is_running = False
    
    async def _stream_price_data(self):
        """Continuously fetch and update price data."""
        while self.is_running:
            try:
                start_time = time.time()
                
                # Get items prioritized by volume and activity
                priority_items = await self._get_priority_items()
                
                # Process in batches based on priority
                for priority_level, items in priority_items.items():
                    if not self.is_running:
                        break
                        
                    interval = self.update_intervals.get(priority_level, 300)
                    batch_size = 50 if priority_level == 'high_volume' else 25
                    
                    await self._process_price_batch(items, batch_size)
                    
                    # Rate limiting between batches
                    await asyncio.sleep(2)
                
                # Update data source status
                await self._update_source_status(
                    'weirdgloop', 
                    success=True, 
                    response_time=time.time() - start_time
                )
                
                # Wait before next cycle
                await asyncio.sleep(60)  # Base cycle: 1 minute
                
            except Exception as e:
                logger.error(f"Price streaming error: {e}")
                await self._update_source_status('weirdgloop', success=False, error=str(e))
                await asyncio.sleep(30)  # Shorter wait on error
    
    async def _calculate_momentum(self):
        """Calculate price velocity, acceleration, and momentum."""
        while self.is_running:
            try:
                logger.info("📊 Calculating market momentum...")
                
                # Get recent price history for all active items
                items_with_prices = await sync_to_async(list)(
                    Item.objects.filter(is_active=True)
                    .prefetch_related('price_snapshots')[:500]  # Limit for performance
                )
                
                momentum_updates = []
                
                for item in items_with_prices:
                    momentum_data = await self._calculate_item_momentum(item)
                    if momentum_data:
                        momentum_updates.append(momentum_data)
                
                # Bulk update momentum data
                if momentum_updates:
                    await self._bulk_update_momentum(momentum_updates)
                    logger.info(f"✅ Updated momentum for {len(momentum_updates)} items")
                
                await asyncio.sleep(self.update_intervals['momentum'])
                
            except Exception as e:
                logger.error(f"Momentum calculation error: {e}")
                await asyncio.sleep(60)
    
    async def _analyze_volume(self):
        """Analyze trading volume patterns and liquidity."""
        while self.is_running:
            try:
                logger.info("📈 Analyzing volume patterns...")
                
                # Get items with recent volume data
                volume_analyses = []
                
                items = await sync_to_async(list)(
                    Item.objects.filter(is_active=True)
                    .select_related('volume_analysis')[:500]
                )
                
                for item in items:
                    volume_data = await self._analyze_item_volume(item)
                    if volume_data:
                        volume_analyses.append(volume_data)
                
                # Update volume analysis
                if volume_analyses:
                    await self._bulk_update_volume_analysis(volume_analyses)
                    logger.info(f"✅ Analyzed volume for {len(volume_analyses)} items")
                
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Volume analysis error: {e}")
                await asyncio.sleep(60)
    
    async def _assess_risks(self):
        """Assess trading risks for all active items."""
        while self.is_running:
            try:
                logger.info("⚠️ Assessing trading risks...")
                
                risk_updates = []
                
                items = await sync_to_async(list)(
                    Item.objects.filter(is_active=True)
                    .select_related('risk_metrics', 'volume_analysis')[:500]
                )
                
                for item in items:
                    risk_data = await self._calculate_item_risk(item)
                    if risk_data:
                        risk_updates.append(risk_data)
                
                if risk_updates:
                    await self._bulk_update_risk_metrics(risk_updates)
                    logger.info(f"✅ Updated risk metrics for {len(risk_updates)} items")
                
                await asyncio.sleep(600)  # 10 minutes
                
            except Exception as e:
                logger.error(f"Risk assessment error: {e}")
                await asyncio.sleep(60)
    
    async def _detect_market_events(self):
        """Detect and create market events."""
        while self.is_running:
            try:
                logger.info("🔍 Detecting market events...")
                
                events = []
                
                # Detect volume surges
                volume_events = await self._detect_volume_surges()
                events.extend(volume_events)
                
                # Detect price spikes/crashes
                price_events = await self._detect_price_events()
                events.extend(price_events)
                
                # Detect whale activity
                whale_events = await self._detect_whale_activity()
                events.extend(whale_events)
                
                # Create market events
                if events:
                    await self._create_market_events(events)
                    logger.info(f"📢 Created {len(events)} market events")
                
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Market event detection error: {e}")
                await asyncio.sleep(60)
    
    async def _broadcast_updates(self):
        """Broadcast real-time updates to connected clients."""
        while self.is_running:
            try:
                # Get hot market data
                hot_data = await self._get_hot_market_data()
                
                # Cache hot data
                cache.set(
                    self.cache_keys['hot_items'], 
                    hot_data, 
                    300  # 5 minutes
                )
                
                # Broadcast to WebSocket clients
                if self.channel_layer and hot_data:
                    await self.channel_layer.group_send(
                        'market_updates',
                        {
                            'type': 'market_update',
                            'data': hot_data
                        }
                    )
                
                await asyncio.sleep(30)  # 30 seconds broadcast interval
                
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                await asyncio.sleep(30)
    
    # Helper Methods
    
    @sync_to_async
    def _get_priority_items(self) -> Dict[str, List[Item]]:
        """Get items categorized by update priority."""
        # High volume items (updated every minute)
        high_volume = list(
            Item.objects.filter(
                is_active=True,
                price_snapshots__total_volume__gte=1000
            ).distinct()[:100]
        )
        
        # Medium volume items (updated every 5 minutes) 
        medium_volume = list(
            Item.objects.filter(
                is_active=True,
                price_snapshots__total_volume__gte=100,
                price_snapshots__total_volume__lt=1000
            ).distinct()[:200]
        )
        
        # Low volume items (updated every 15 minutes)
        low_volume = list(
            Item.objects.filter(
                is_active=True,
                price_snapshots__total_volume__lt=100
            ).distinct()[:500]
        )
        
        return {
            'high_volume': high_volume,
            'medium_volume': medium_volume,
            'low_volume': low_volume,
        }
    
    async def _process_price_batch(self, items: List[Item], batch_size: int):
        """Process a batch of price updates."""
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # Fetch prices for batch
            price_updates = []
            for item in batch:
                try:
                    price_data = await sync_to_async(
                        self.api_client.get_latest_price
                    )(item.item_id)
                    
                    if price_data:
                        price_updates.append((item, price_data))
                        
                except Exception as e:
                    logger.warning(f"Failed to fetch price for {item.name}: {e}")
            
            # Update prices in batch
            if price_updates:
                await self._batch_update_prices(price_updates)
    
    @sync_to_async
    def _batch_update_prices(self, price_updates: List[Tuple[Item, Dict]]):
        """Batch update prices in database."""
        with transaction.atomic():
            for item, price_data in price_updates:
                # Create new price snapshot
                PriceSnapshot.objects.create(
                    item=item,
                    high_price=price_data.get('high'),
                    low_price=price_data.get('low'),
                    total_volume=price_data.get('volume', 0),
                    api_source='weirdgloop',
                )
                
                # Update profit calculation if needed
                if hasattr(item, 'profit_calc'):
                    profit_calc = item.profit_calc
                    profit_calc.current_buy_price = price_data.get('high', 0)
                    profit_calc.current_sell_price = price_data.get('low', 0)
                    profit_calc.save()
    
    async def _calculate_item_momentum(self, item: Item) -> Optional[Dict]:
        """Calculate momentum metrics for a single item."""
        try:
            # Get recent price history (last 30 minutes)
            recent_snapshots = await sync_to_async(list)(
                item.price_snapshots.filter(
                    created_at__gte=timezone.now() - timedelta(minutes=30)
                ).order_by('created_at')
            )
            
            if len(recent_snapshots) < 3:
                return None
            
            # Calculate price changes
            prices = [s.high_price for s in recent_snapshots if s.high_price]
            volumes = [s.total_volume for s in recent_snapshots if s.total_volume]
            
            if len(prices) < 2:
                return None
            
            # Price velocity (GP per minute)
            time_span = (recent_snapshots[-1].created_at - recent_snapshots[0].created_at).total_seconds() / 60
            price_change = prices[-1] - prices[0]
            price_velocity = price_change / max(time_span, 1)
            
            # Volume velocity
            volume_velocity = 0
            if len(volumes) >= 2:
                volume_change = volumes[-1] - volumes[0]
                volume_velocity = volume_change / max(time_span, 1)
            
            # Momentum score (0-100)
            momentum_score = min(100, abs(price_velocity) * 10)
            
            # Trend determination
            if price_velocity > 5:
                trend = 'strong_bull' if price_velocity > 50 else 'bull'
            elif price_velocity < -5:
                trend = 'strong_bear' if price_velocity < -50 else 'bear'
            else:
                trend = 'neutral'
            
            return {
                'item': item,
                'price_velocity': price_velocity,
                'volume_velocity': volume_velocity,
                'momentum_score': momentum_score,
                'trend_direction': trend,
                'trend_strength': min(100, abs(price_velocity)),
            }
            
        except Exception as e:
            logger.warning(f"Failed to calculate momentum for {item.name}: {e}")
            return None
    
    async def _analyze_item_volume(self, item: Item) -> Optional[Dict]:
        """Analyze volume patterns for a single item."""
        try:
            # Get recent volume data
            recent_snapshots = await sync_to_async(list)(
                item.price_snapshots.filter(
                    created_at__gte=timezone.now() - timedelta(hours=24),
                    total_volume__isnull=False
                ).order_by('-created_at')
            )
            
            if not recent_snapshots:
                return None
            
            current_volume = recent_snapshots[0].total_volume or 0
            
            # Calculate average volume (7 days)
            avg_volume = await sync_to_async(
                item.price_snapshots.filter(
                    created_at__gte=timezone.now() - timedelta(days=7),
                    total_volume__isnull=False
                ).aggregate
            )(avg_vol=Avg('total_volume'))['avg_vol'] or 0
            
            # Volume ratios
            volume_ratio = current_volume / max(avg_volume, 1)
            
            # Liquidity level
            if current_volume >= 10000:
                liquidity_level = 'extreme'
            elif current_volume >= 5000:
                liquidity_level = 'very_high'
            elif current_volume >= 1000:
                liquidity_level = 'high'
            elif current_volume >= 500:
                liquidity_level = 'medium'
            elif current_volume >= 100:
                liquidity_level = 'low'
            elif current_volume >= 50:
                liquidity_level = 'very_low'
            else:
                liquidity_level = 'minimal'
            
            # Flip completion probability
            flip_probability = min(95, current_volume / 10)
            
            return {
                'item': item,
                'current_daily_volume': current_volume,
                'average_daily_volume': avg_volume,
                'volume_ratio_daily': volume_ratio,
                'liquidity_level': liquidity_level,
                'flip_completion_probability': flip_probability,
            }
            
        except Exception as e:
            logger.warning(f"Failed to analyze volume for {item.name}: {e}")
            return None
    
    async def _calculate_item_risk(self, item: Item) -> Optional[Dict]:
        """Calculate risk metrics for a single item."""
        try:
            # Get price volatility
            recent_prices = await sync_to_async(list)(
                item.price_snapshots.filter(
                    created_at__gte=timezone.now() - timedelta(hours=24),
                    high_price__isnull=False
                ).values_list('high_price', flat=True)
            )
            
            if len(recent_prices) < 5:
                return None
            
            # Calculate volatility
            price_std = statistics.stdev(recent_prices)
            price_mean = statistics.mean(recent_prices)
            volatility_pct = (price_std / price_mean * 100) if price_mean > 0 else 0
            
            # Volume risk
            volume_analysis = await sync_to_async(
                lambda: getattr(item, 'volume_analysis', None)
            )()
            
            liquidity_risk = 0
            if volume_analysis:
                if volume_analysis.liquidity_level in ['minimal', 'very_low']:
                    liquidity_risk = 60
                elif volume_analysis.liquidity_level == 'low':
                    liquidity_risk = 40
                elif volume_analysis.liquidity_level == 'medium':
                    liquidity_risk = 20
            
            # Overall risk score
            volatility_risk = min(50, volatility_pct * 2)
            overall_risk = (volatility_risk + liquidity_risk) / 2
            
            # Risk category
            if overall_risk < 20:
                risk_category = 'very_low'
            elif overall_risk < 35:
                risk_category = 'low'
            elif overall_risk < 50:
                risk_category = 'medium'
            elif overall_risk < 70:
                risk_category = 'high'
            else:
                risk_category = 'very_high'
            
            return {
                'item': item,
                'overall_risk_score': overall_risk,
                'volatility_risk': volatility_risk,
                'liquidity_risk': liquidity_risk,
                'price_volatility_24h': volatility_pct,
                'risk_category': risk_category,
            }
            
        except Exception as e:
            logger.warning(f"Failed to calculate risk for {item.name}: {e}")
            return None
    
    @sync_to_async
    def _bulk_update_momentum(self, momentum_updates: List[Dict]):
        """Bulk update momentum data."""
        with transaction.atomic():
            for data in momentum_updates:
                MarketMomentum.objects.update_or_create(
                    item=data['item'],
                    defaults={
                        'price_velocity': data['price_velocity'],
                        'volume_velocity': data.get('volume_velocity', 0),
                        'momentum_score': data['momentum_score'],
                        'trend_direction': data['trend_direction'],
                        'trend_strength': data['trend_strength'],
                    }
                )
    
    @sync_to_async
    def _bulk_update_volume_analysis(self, volume_analyses: List[Dict]):
        """Bulk update volume analysis."""
        with transaction.atomic():
            for data in volume_analyses:
                VolumeAnalysis.objects.update_or_create(
                    item=data['item'],
                    defaults={
                        'current_daily_volume': data['current_daily_volume'],
                        'average_daily_volume': data['average_daily_volume'],
                        'volume_ratio_daily': data['volume_ratio_daily'],
                        'liquidity_level': data['liquidity_level'],
                        'flip_completion_probability': data['flip_completion_probability'],
                    }
                )
    
    @sync_to_async
    def _bulk_update_risk_metrics(self, risk_updates: List[Dict]):
        """Bulk update risk metrics."""
        with transaction.atomic():
            for data in risk_updates:
                RiskMetrics.objects.update_or_create(
                    item=data['item'],
                    defaults={
                        'overall_risk_score': data['overall_risk_score'],
                        'volatility_risk': data['volatility_risk'],
                        'liquidity_risk': data['liquidity_risk'],
                        'price_volatility_24h': data['price_volatility_24h'],
                        'risk_category': data['risk_category'],
                    }
                )
    
    async def _detect_volume_surges(self) -> List[Dict]:
        """Detect unusual volume spikes."""
        # Implementation for volume surge detection
        return []
    
    async def _detect_price_events(self) -> List[Dict]:
        """Detect significant price movements."""
        # Implementation for price event detection
        return []
    
    async def _detect_whale_activity(self) -> List[Dict]:
        """Detect large trades indicating whale activity."""
        # Implementation for whale detection
        return []
    
    @sync_to_async
    def _create_market_events(self, events: List[Dict]):
        """Create market event records."""
        with transaction.atomic():
            for event_data in events:
                MarketEvent.objects.create(**event_data)
    
    async def _get_hot_market_data(self) -> Dict:
        """Get current hot market data for broadcasting."""
        try:
            # Get top momentum items
            hot_items = await sync_to_async(list)(
                MarketMomentum.objects.filter(
                    momentum_score__gte=60
                ).select_related('item').order_by('-momentum_score')[:20]
            )
            
            # Get recent market events
            recent_events = await sync_to_async(list)(
                MarketEvent.objects.filter(
                    is_active=True,
                    detected_at__gte=timezone.now() - timedelta(hours=1)
                ).order_by('-detected_at')[:10]
            )
            
            return {
                'timestamp': timezone.now().isoformat(),
                'hot_items': [
                    {
                        'item_id': item.item.item_id,
                        'name': item.item.name,
                        'momentum_score': item.momentum_score,
                        'trend': item.trend_direction,
                        'price_velocity': item.price_velocity,
                    }
                    for item in hot_items
                ],
                'market_events': [
                    {
                        'type': event.event_type,
                        'title': event.title,
                        'impact': event.impact_score,
                        'detected_at': event.detected_at.isoformat(),
                    }
                    for event in recent_events
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get hot market data: {e}")
            return {}
    
    @sync_to_async
    def _update_source_status(self, source: str, success: bool = True, 
                            response_time: float = 0, error: str = ""):
        """Update data source status."""
        try:
            status, created = StreamingDataStatus.objects.get_or_create(
                source=source,
                defaults={
                    'is_active': True,
                    'last_successful_update': timezone.now() if success else None,
                    'average_response_time_ms': response_time * 1000,
                }
            )
            
            if not created:
                if success:
                    status.last_successful_update = timezone.now()
                    status.error_count_24h = 0
                    status.last_error = ""
                else:
                    status.error_count_24h += 1
                    status.last_error = error
                    
                status.average_response_time_ms = response_time * 1000
                status.save()
                
        except Exception as e:
            logger.error(f"Failed to update source status: {e}")


# Global instance
streaming_manager = StreamingDataManager()