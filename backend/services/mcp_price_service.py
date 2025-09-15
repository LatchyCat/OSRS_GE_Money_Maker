"""
MCP (Market Control Protocol) Service for Real-Time OSRS Price Tracking

This service implements intelligent priority-based fetching of RuneScape Grand Exchange prices
with dynamic scheduling based on volatility, user activity, and market conditions.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

import aiohttp
import asyncio
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from .api_client import RuneScapeWikiClient
from .unified_wiki_price_client import UnifiedPriceClient, PriceData

logger = logging.getLogger(__name__)


class PriorityTier(Enum):
    """Priority tiers for item update scheduling."""
    REALTIME = 1      # 30-60 second updates
    NEAR_REALTIME = 2  # 5-minute updates  
    REGULAR = 3        # 1-hour updates
    BACKGROUND = 4     # 6-hour updates


@dataclass
class ItemPriority:
    """Represents an item's priority and tracking metadata."""
    item_id: int
    tier: PriorityTier
    last_updated: datetime
    next_update: datetime
    volatility_score: float = 0.0
    volume_score: float = 0.0
    user_interest_score: float = 0.0
    price_change_score: float = 0.0
    consecutive_stable_periods: int = 0
    is_user_active: bool = False
    is_in_goal_plan: bool = False
    recent_prices: deque = field(default_factory=lambda: deque(maxlen=20))
    recent_volumes: deque = field(default_factory=lambda: deque(maxlen=20))


class MCPPriceService:
    """
    Market Control Protocol service for intelligent OSRS price tracking.
    
    Features:
    - Dynamic priority-based scheduling
    - Volatility-aware update frequencies  
    - User activity tracking
    - Smart caching and rate limiting
    - Market intelligence and trend analysis
    """
    
    def __init__(self):
        self.api_client = None
        self.multi_source_client = None
        self.item_priorities: Dict[int, ItemPriority] = {}
        self.user_activity: Dict[int, Set[int]] = defaultdict(set)  # user_id -> item_ids
        self.active_goal_items: Set[int] = set()
        self.priority_queues: Dict[PriorityTier, List[int]] = {
            tier: [] for tier in PriorityTier
        }
        
        # Scheduling intervals (in seconds)
        self.tier_intervals = {
            PriorityTier.REALTIME: 45,      # 45 seconds
            PriorityTier.NEAR_REALTIME: 300, # 5 minutes
            PriorityTier.REGULAR: 3600,      # 1 hour
            PriorityTier.BACKGROUND: 21600   # 6 hours
        }
        
        # Volatility thresholds
        self.volatility_thresholds = {
            'high': 0.05,    # 5% spread
            'medium': 0.02,  # 2% spread
            'low': 0.01      # 1% spread
        }
        
        # Volume spike thresholds
        self.volume_spike_threshold = 2.0  # 200% of average
        
        # API rate limiting
        self.last_bulk_fetch = 0
        self.min_bulk_interval = 5  # Minimum 5 seconds between bulk fetches
        
        # Cache keys
        self.cache_prefix = "mcp_prices:"
        self.cache_timeout = 30  # 30 seconds for real-time data
        
        self.is_running = False
        
    async def start(self):
        """Start the MCP service."""
        if self.is_running:
            logger.warning("MCP service is already running")
            return
            
        self.is_running = True
        logger.info("Starting MCP Price Service...")
        
        # Initialize item priorities
        await self._initialize_item_priorities()
        
        # Start background tasks
        await asyncio.gather(
            self._priority_scheduler(),
            self._volatility_analyzer(),
            self._user_activity_monitor(),
            self._cache_cleaner()
        )
        
    async def stop(self):
        """Stop the MCP service."""
        self.is_running = False
        logger.info("MCP Price Service stopped")
        
    async def get_item_price(self, item_id: int, force_fresh: bool = False) -> Optional[Dict]:
        """
        Get item price with intelligent caching and priority updating.
        
        Args:
            item_id: OSRS item ID
            force_fresh: Force fresh API fetch
            
        Returns:
            Price data dict or None if not available
        """
        cache_key = f"{self.cache_prefix}item_{item_id}"
        
        if not force_fresh:
            cached_price = cache.get(cache_key)
            if cached_price:
                return cached_price
        
        # Check if item needs priority update
        if item_id in self.item_priorities:
            priority = self.item_priorities[item_id]
            if datetime.now() >= priority.next_update:
                await self._update_item_price(item_id)
                
        return cache.get(cache_key)
        
    async def track_user_activity(self, user_id: int, item_id: int, activity_type: str):
        """
        Track user activity for priority adjustment.
        
        Args:
            user_id: User identifier (session_key hash)
            item_id: OSRS item ID
            activity_type: 'view', 'goal_plan', 'high_alch', 'search'
        """
        self.user_activity[user_id].add(item_id)
        
        if item_id in self.item_priorities:
            priority = self.item_priorities[item_id]
            priority.is_user_active = True
            
            # Boost priority based on activity type
            if activity_type in ['goal_plan', 'high_alch']:
                priority.user_interest_score = min(priority.user_interest_score + 0.3, 1.0)
                self._promote_item_tier(item_id)
            elif activity_type == 'view':
                priority.user_interest_score = min(priority.user_interest_score + 0.1, 1.0)
                
    async def update_goal_plan_items(self, item_ids: List[int]):
        """Update items that are part of active goal plans."""
        self.active_goal_items.update(item_ids)
        
        for item_id in item_ids:
            if item_id in self.item_priorities:
                priority = self.item_priorities[item_id]
                priority.is_in_goal_plan = True
                priority.user_interest_score = 1.0
                self._promote_item_tier(item_id)
                
    async def _initialize_item_priorities(self):
        """Initialize priority tracking for all items."""
        logger.info("Initializing item priorities...")
        
        # Get all active items from database
        items = [item async for item in Item.objects.filter(is_active=True).values('item_id', 'high_alch', 'limit')]
        
        current_time = datetime.now()
        
        for item_data in items:
            item_id = item_data['item_id']
            
            # Start all items in BACKGROUND tier
            priority = ItemPriority(
                item_id=item_id,
                tier=PriorityTier.BACKGROUND,
                last_updated=current_time - timedelta(hours=24),  # Force initial update
                next_update=current_time
            )
            
            self.item_priorities[item_id] = priority
            self.priority_queues[PriorityTier.BACKGROUND].append(item_id)
            
        logger.info(f"Initialized {len(self.item_priorities)} item priorities")
        
        # Get initial price data
        await self._bulk_price_update()
        
    async def _priority_scheduler(self):
        """Main scheduling loop for priority-based updates."""
        logger.info("Starting priority scheduler...")
        
        while self.is_running:
            current_time = datetime.now()
            
            # Process each priority tier
            for tier in PriorityTier:
                items_to_update = []
                
                for item_id in self.priority_queues[tier]:
                    if item_id not in self.item_priorities:
                        continue
                        
                    priority = self.item_priorities[item_id]
                    if current_time >= priority.next_update:
                        items_to_update.append(item_id)
                        
                if items_to_update:
                    await self._batch_update_items(items_to_update, tier)
                    
            # Sleep based on highest priority tier interval
            await asyncio.sleep(min(self.tier_intervals.values()))
            
    async def _volatility_analyzer(self):
        """Analyze price volatility and adjust priorities."""
        logger.info("Starting volatility analyzer...")
        
        while self.is_running:
            current_time = datetime.now()
            
            for item_id, priority in self.item_priorities.items():
                if len(priority.recent_prices) < 5:
                    continue
                    
                # Calculate volatility metrics
                prices = list(priority.recent_prices)
                avg_price = sum(prices) / len(prices)
                
                if avg_price > 0:
                    # Price spread volatility
                    max_price = max(prices)
                    min_price = min(prices)
                    spread_volatility = (max_price - min_price) / avg_price
                    
                    # Price movement volatility
                    price_changes = [abs(prices[i] - prices[i-1]) / prices[i-1] 
                                   for i in range(1, len(prices)) if prices[i-1] > 0]
                    movement_volatility = sum(price_changes) / len(price_changes) if price_changes else 0
                    
                    # Combined volatility score
                    volatility_score = (spread_volatility + movement_volatility) / 2
                    priority.volatility_score = volatility_score
                    
                    # Adjust tier based on volatility
                    if volatility_score >= self.volatility_thresholds['high']:
                        self._promote_item_tier(item_id, PriorityTier.REALTIME)
                    elif volatility_score >= self.volatility_thresholds['medium']:
                        self._promote_item_tier(item_id, PriorityTier.NEAR_REALTIME)
                    elif volatility_score < self.volatility_thresholds['low']:
                        priority.consecutive_stable_periods += 1
                        if priority.consecutive_stable_periods > 12:  # 12 stable periods
                            self._demote_item_tier(item_id)
                    else:
                        priority.consecutive_stable_periods = 0
                        
            await asyncio.sleep(300)  # Run every 5 minutes
            
    async def _user_activity_monitor(self):
        """Monitor and decay user activity scores."""
        while self.is_running:
            current_time = datetime.now()
            
            # Decay user interest scores over time
            for priority in self.item_priorities.values():
                if priority.user_interest_score > 0:
                    # Decay by 10% every hour
                    priority.user_interest_score *= 0.9
                    
                    # Reset user active flag if score is too low
                    if priority.user_interest_score < 0.1:
                        priority.is_user_active = False
                        priority.user_interest_score = 0.0
                        
            # Clean old user activity
            for user_id in list(self.user_activity.keys()):
                # Remove users with no recent activity
                if len(self.user_activity[user_id]) == 0:
                    del self.user_activity[user_id]
                    
            await asyncio.sleep(3600)  # Run every hour
            
    async def _cache_cleaner(self):
        """Clean expired cache entries."""
        while self.is_running:
            # Cache cleanup is handled by Redis TTL, but we can do maintenance here
            await asyncio.sleep(1800)  # Run every 30 minutes
            
    async def _bulk_price_update(self):
        """Fetch prices for all items in bulk using multi-source intelligence."""
        current_time = time.time()
        
        # Rate limiting
        if current_time - self.last_bulk_fetch < self.min_bulk_interval:
            return
            
        self.last_bulk_fetch = current_time
        
        try:
            # Get all item IDs we need to update
            item_ids = list(self.item_priorities.keys())
            if not item_ids:
                return
            
            # Fetch best prices from multiple sources
            async with UnifiedPriceClient() as client:
                price_data_map = await client.get_multiple_comprehensive_prices(
                    item_ids, 
                    max_staleness_hours=24.0
                )
                
                if not price_data_map:
                    logger.error("No valid price data received from multi-source client")
                    return
                    
                # Process and cache price data
                await self._process_multi_source_price_data(price_data_map)
            
        except Exception as e:
            logger.error(f"Multi-source bulk price update failed: {e}")
            
    async def _batch_update_items(self, item_ids: List[int], tier: PriorityTier):
        """Update a batch of items efficiently."""
        if not item_ids:
            return
            
        logger.debug(f"Updating {len(item_ids)} items in {tier.name} tier")
        
        # For real-time tier, use individual updates
        if tier == PriorityTier.REALTIME and len(item_ids) <= 5:
            for item_id in item_ids:
                await self._update_item_price(item_id)
        else:
            # Use bulk update for efficiency
            await self._bulk_price_update()
            
        # Update next update times
        current_time = datetime.now()
        interval = self.tier_intervals[tier]
        
        for item_id in item_ids:
            if item_id in self.item_priorities:
                priority = self.item_priorities[item_id]
                priority.last_updated = current_time
                priority.next_update = current_time + timedelta(seconds=interval)
                
    async def _update_item_price(self, item_id: int):
        """Update price for a specific item using multi-source intelligence."""
        try:
            # Fetch best available price from multiple sources
            async with UnifiedPriceClient() as client:
                price_data = await client.get_best_price_data(
                    item_id, 
                    max_staleness_hours=24.0
                )
                
                if price_data:
                    await self._process_multi_source_item_price(item_id, price_data)
                else:
                    logger.warning(f"No valid price data found for item {item_id}")
                
        except Exception as e:
            logger.error(f"Failed to update price for item {item_id}: {e}")
            
    async def _process_bulk_price_data(self, price_data: Dict):
        """Process bulk price data and update priorities."""
        current_time = timezone.now()
        
        # Process price data (async, so no transaction wrapper)
        for item_id_str, data in price_data.items():
            try:
                item_id = int(item_id_str)
                
                if item_id not in self.item_priorities:
                    continue
                    
                # Extract price information
                high_price = data.get('high', 0)
                low_price = data.get('low', 0)
                high_time = data.get('highTime', 0)
                low_time = data.get('lowTime', 0)
                
                if high_price and low_price:
                    # Use low_price for average calculation since it's the buy price
                    avg_price = (high_price + low_price) / 2
                    
                    # Update priority tracking with the buy price (low_price)
                    priority = self.item_priorities[item_id]
                    priority.recent_prices.append(low_price)  # Track buy prices for volatility
                    
                    # Cache the price data with clear labeling
                    cache_key = f"{self.cache_prefix}item_{item_id}"
                    cache_data = {
                        'high': high_price,      # instant-sell price
                        'low': low_price,        # instant-buy price  
                        'avg': avg_price,
                        'buy_price': low_price,  # Explicit buy price
                        'sell_price': high_price, # Explicit sell price
                        'high_time': high_time,
                        'low_time': low_time,
                        'updated': current_time.isoformat()
                    }
                    
                    cache.set(cache_key, cache_data, self.cache_timeout)
                    
                    # Store in database for persistence
                    await self._store_price_snapshot(item_id, cache_data)
                    
            except (ValueError, KeyError) as e:
                logger.error(f"Error processing price data for item {item_id_str}: {e}")
                    
    async def _process_multi_source_price_data(self, price_data_map: Dict[int, PriceData]):
        """Process multi-source price data for multiple items."""
        current_time = timezone.now()
        
        for item_id, price_data in price_data_map.items():
            try:
                # Update priority tracking with buy price for volatility analysis
                if item_id in self.item_priorities:
                    priority = self.item_priorities[item_id]
                    priority.recent_prices.append(price_data.low_price)  # Track buy prices
                    
                    # Update volume data if available
                    if price_data.volume_high > 0 or price_data.volume_low > 0:
                        avg_volume = (price_data.volume_high + price_data.volume_low) / 2
                        priority.recent_volumes.append(avg_volume)
                
                # Cache the enriched data with source transparency
                cache_key = f"{self.cache_prefix}item_{item_id}"
                cache_data = {
                    'high': price_data.high_price,      # instant-sell price
                    'low': price_data.low_price,        # instant-buy price  
                    'avg': (price_data.high_price + price_data.low_price) / 2,
                    'buy_price': price_data.low_price,  # Explicit buy price
                    'sell_price': price_data.high_price, # Explicit sell price
                    'timestamp': price_data.timestamp,
                    'age_hours': price_data.age_hours,
                    'source': price_data.source.value,
                    'quality': price_data.quality.value,
                    'confidence_score': price_data.confidence_score,
                    'volume_high': price_data.volume_high,
                    'volume_low': price_data.volume_low,
                    'updated': current_time.isoformat()
                }
                
                cache.set(cache_key, cache_data, self.cache_timeout)
                
                # Store in database for persistence
                await self._store_multi_source_price_snapshot(item_id, price_data)
                
            except Exception as e:
                logger.error(f"Error processing multi-source price data for item {item_id}: {e}")

    async def _process_multi_source_item_price(self, item_id: int, price_data: PriceData):
        """Process multi-source price data for a single item."""
        current_time = timezone.now()
        
        # Update priority tracking
        if item_id in self.item_priorities:
            priority = self.item_priorities[item_id]
            priority.recent_prices.append(price_data.low_price)  # Track buy prices for volatility
            
            # Update volume data if available
            if price_data.volume_high > 0 or price_data.volume_low > 0:
                avg_volume = (price_data.volume_high + price_data.volume_low) / 2
                priority.recent_volumes.append(avg_volume)
        
        # Cache the enriched data with source transparency
        cache_key = f"{self.cache_prefix}item_{item_id}"
        cache_data = {
            'high': price_data.high_price,      # instant-sell price
            'low': price_data.low_price,        # instant-buy price  
            'avg': (price_data.high_price + price_data.low_price) / 2,
            'buy_price': price_data.low_price,  # Explicit buy price
            'sell_price': price_data.high_price, # Explicit sell price
            'timestamp': price_data.timestamp,
            'age_hours': price_data.age_hours,
            'source': price_data.source.value,
            'quality': price_data.quality.value,
            'confidence_score': price_data.confidence_score,
            'volume_high': price_data.volume_high,
            'volume_low': price_data.volume_low,
            'updated': current_time.isoformat()
        }
        
        cache.set(cache_key, cache_data, self.cache_timeout)
        
        # Store in database
        await self._store_multi_source_price_snapshot(item_id, price_data)

    async def _process_item_price_data(self, item_id: int, data: Dict):
        """Process price data for a single item (legacy method for backwards compatibility)."""
        current_time = timezone.now()
        
        high_price = data.get('high', 0)
        low_price = data.get('low', 0)
        
        if high_price and low_price:
            avg_price = (high_price + low_price) / 2
            
            # Update priority tracking
            priority = self.item_priorities[item_id]
            priority.recent_prices.append(avg_price)
            
            # Cache the data
            cache_key = f"{self.cache_prefix}item_{item_id}"
            cache_data = {
                'high': high_price,
                'low': low_price,
                'avg': avg_price,
                'updated': current_time.isoformat()
            }
            
            cache.set(cache_key, cache_data, self.cache_timeout)
            
            # Store in database
            await self._store_price_snapshot(item_id, cache_data)
            
    async def _store_multi_source_price_snapshot(self, item_id: int, price_data: PriceData):
        """Store multi-source price snapshot in database with enhanced metadata."""
        try:
            # Get or create item
            item = await Item.objects.aget(item_id=item_id)
            
            # Create price snapshot with multi-source metadata
            snapshot = await PriceSnapshot.objects.acreate(
                item=item,
                high_price=price_data.high_price,
                low_price=price_data.low_price,
                # Store additional metadata in database if model supports it
                timestamp=timezone.make_aware(
                    datetime.fromtimestamp(price_data.timestamp)
                ) if price_data.timestamp > 0 else timezone.now()
            )
            
            # Update or create profit calculation with multi-source data
            await self._update_multi_source_profit_calculation(item, price_data)
            
        except Item.DoesNotExist:
            logger.warning(f"Item {item_id} not found in database")
        except Exception as e:
            logger.error(f"Failed to store multi-source price snapshot for item {item_id}: {e}")

    async def _store_price_snapshot(self, item_id: int, price_data: Dict):
        """Store price snapshot in database (legacy method for backwards compatibility)."""
        try:
            # Get or create item
            item = await Item.objects.aget(item_id=item_id)
            
            # Create price snapshot
            snapshot = await PriceSnapshot.objects.acreate(
                item=item,
                high_price=price_data['high'],
                low_price=price_data['low']
            )
            
            # Update or create profit calculation
            await self._update_profit_calculation(item, price_data)
            
        except Item.DoesNotExist:
            logger.warning(f"Item {item_id} not found in database")
        except Exception as e:
            logger.error(f"Failed to store price snapshot for item {item_id}: {e}")
            
    async def _update_profit_calculation(self, item: Item, price_data: Dict):
        """Update profit calculation for an item with price validation."""
        try:
            # Import price validator
            from price_sanity_validator import validate_and_sanitize_price
            
            # CRITICAL FIX: Use low_price as buy_price (instant-buy price)
            # high_price is the instant-sell price, low_price is the instant-buy price
            raw_buy_price = price_data['low']  # This is what we BUY at (instant-buy)
            raw_sell_price = price_data['high']  # This is what we SELL at (instant-sell)
            
            # Validate buy price
            buy_validation = validate_and_sanitize_price(item.name, raw_buy_price, "mcp_service")
            if not buy_validation['accepted']:
                logger.warning(f"Rejecting buy price for {item.name}: {buy_validation['reason']}")
                return
            
            # Validate sell price
            sell_validation = validate_and_sanitize_price(item.name, raw_sell_price, "mcp_service")
            if not sell_validation['accepted']:
                logger.warning(f"Rejecting sell price for {item.name}: {sell_validation['reason']}")
                return
            
            buy_price = buy_validation['sanitized_price']
            sell_price = sell_validation['sanitized_price']
            nature_rune_cost = getattr(settings, 'NATURE_RUNE_COST', 180)
            
            # Calculate high-alch profit: alch_value - buy_price - nature_rune_cost
            profit = item.high_alch - buy_price - nature_rune_cost
            margin = (profit / buy_price * 100) if buy_price > 0 else 0
            
            # Get or create profit calculation
            profit_calc, created = await ProfitCalculation.objects.aget_or_create(
                item=item,
                defaults={
                    'current_buy_price': buy_price,        # Correct: instant-buy price
                    'current_sell_price': sell_price,      # Correct: instant-sell price  
                    'current_profit': profit,
                    'current_profit_margin': margin,
                    'daily_volume': 0,  # Will be updated by volume analyzer
                    'recommendation_score': 0.5,
                    'price_trend': 'stable'
                }
            )
            
            if not created:
                # Update existing calculation
                profit_calc.current_buy_price = buy_price        # Fixed
                profit_calc.current_sell_price = sell_price      # Fixed
                profit_calc.current_profit = profit
                profit_calc.current_profit_margin = margin
                profit_calc.last_updated = timezone.now()
                await profit_calc.asave()
                
        except Exception as e:
            logger.error(f"Failed to update profit calculation for item {item.item_id}: {e}")
            
    async def _update_multi_source_profit_calculation(self, item: Item, price_data: PriceData):
        """Update profit calculation for an item using multi-source price data with validation."""
        try:
            # Import price validator
            from price_sanity_validator import validate_and_sanitize_price
            
            # Use multi-source price data with confidence scoring
            raw_buy_price = price_data.low_price   # instant-buy price
            raw_sell_price = price_data.high_price # instant-sell price
            
            # Validate buy price
            buy_validation = validate_and_sanitize_price(item.name, raw_buy_price, price_data.source.value)
            if not buy_validation['accepted']:
                logger.warning(f"Rejecting multi-source buy price for {item.name}: {buy_validation['reason']}")
                return
            
            # Validate sell price  
            sell_validation = validate_and_sanitize_price(item.name, raw_sell_price, price_data.source.value)
            if not sell_validation['accepted']:
                logger.warning(f"Rejecting multi-source sell price for {item.name}: {sell_validation['reason']}")
                return
            
            buy_price = buy_validation['sanitized_price']
            sell_price = sell_validation['sanitized_price']
            nature_rune_cost = getattr(settings, 'NATURE_RUNE_COST', 180)
            
            # Calculate high-alch profit: alch_value - buy_price - nature_rune_cost
            profit = item.high_alch - buy_price - nature_rune_cost
            margin = (profit / buy_price * 100) if buy_price > 0 else 0
            
            # Calculate enhanced recommendation score using multi-source data
            recommendation_score = self._calculate_recommendation_score(
                profit, margin, price_data
            )
            
            # Determine price trend based on volatility if we have priority data
            price_trend = 'stable'
            if item.item_id in self.item_priorities:
                priority = self.item_priorities[item.item_id]
                if priority.volatility_score >= self.volatility_thresholds['high']:
                    price_trend = 'volatile'
                elif len(priority.recent_prices) >= 3:
                    recent_prices = list(priority.recent_prices)[-3:]
                    if recent_prices[-1] > recent_prices[0]:
                        price_trend = 'rising'
                    elif recent_prices[-1] < recent_prices[0]:
                        price_trend = 'falling'
            
            # Get or create profit calculation
            profit_calc, created = await ProfitCalculation.objects.aget_or_create(
                item=item,
                defaults={
                    'current_buy_price': buy_price,
                    'current_sell_price': sell_price,
                    'current_profit': profit,
                    'current_profit_margin': margin,
                    'daily_volume': price_data.volume_high,  # Use high volume as daily estimate
                    'recommendation_score': recommendation_score,
                    'price_trend': price_trend
                }
            )
            
            if not created:
                # Update existing calculation with enhanced data
                profit_calc.current_buy_price = buy_price
                profit_calc.current_sell_price = sell_price
                profit_calc.current_profit = profit
                profit_calc.current_profit_margin = margin
                profit_calc.daily_volume = max(profit_calc.daily_volume, price_data.volume_high)
                profit_calc.recommendation_score = recommendation_score
                profit_calc.price_trend = price_trend
                profit_calc.last_updated = timezone.now()
                await profit_calc.asave()
                
        except Exception as e:
            logger.error(f"Failed to update multi-source profit calculation for item {item.item_id}: {e}")
    
    def _calculate_recommendation_score(self, profit: int, margin: float, price_data: PriceData) -> float:
        """Calculate enhanced recommendation score using multi-source intelligence."""
        base_score = 0.5
        
        # Profit bonus (normalize to 0-0.3 range)
        profit_bonus = min(profit / 10000, 0.3) if profit > 0 else -0.2
        
        # Margin bonus (normalize to 0-0.2 range)
        margin_bonus = min(margin / 50, 0.2) if margin > 0 else -0.1
        
        # Data quality bonus from multi-source intelligence
        quality_bonus = {
            'fresh': 0.15,
            'recent': 0.1, 
            'acceptable': 0.05,
            'stale': -0.1,
            'unknown': -0.2
        }.get(price_data.quality.value, 0)
        
        # Confidence bonus from source reliability
        confidence_bonus = (price_data.confidence_score - 0.5) * 0.2
        
        # Volume bonus (items with good volume data are more reliable)
        volume_bonus = 0.1 if (price_data.volume_high > 10 or price_data.volume_low > 10) else 0
        
        # Age penalty (fresher data gets higher score)
        age_penalty = min(price_data.age_hours / 24, 1) * -0.1
        
        total_score = (base_score + profit_bonus + margin_bonus + 
                      quality_bonus + confidence_bonus + volume_bonus + age_penalty)
        
        return max(0.0, min(1.0, total_score))
            
    def _promote_item_tier(self, item_id: int, target_tier: Optional[PriorityTier] = None):
        """Promote an item to a higher priority tier."""
        if item_id not in self.item_priorities:
            return
            
        priority = self.item_priorities[item_id]
        current_tier = priority.tier
        
        # Determine target tier
        if target_tier is None:
            tier_order = [PriorityTier.BACKGROUND, PriorityTier.REGULAR, 
                         PriorityTier.NEAR_REALTIME, PriorityTier.REALTIME]
            current_index = tier_order.index(current_tier)
            if current_index > 0:
                target_tier = tier_order[current_index - 1]
            else:
                return  # Already at highest tier
        
        if target_tier.value < current_tier.value:
            # Remove from current tier
            if item_id in self.priority_queues[current_tier]:
                self.priority_queues[current_tier].remove(item_id)
                
            # Add to new tier
            self.priority_queues[target_tier].append(item_id)
            priority.tier = target_tier
            
            # Update next update time
            interval = self.tier_intervals[target_tier]
            priority.next_update = datetime.now() + timedelta(seconds=interval)
            
            logger.debug(f"Promoted item {item_id} from {current_tier.name} to {target_tier.name}")
            
    def _demote_item_tier(self, item_id: int):
        """Demote an item to a lower priority tier."""
        if item_id not in self.item_priorities:
            return
            
        priority = self.item_priorities[item_id]
        current_tier = priority.tier
        
        # Don't demote if user is active or item is in goal plan
        if priority.is_user_active or priority.is_in_goal_plan:
            return
            
        tier_order = [PriorityTier.REALTIME, PriorityTier.NEAR_REALTIME, 
                     PriorityTier.REGULAR, PriorityTier.BACKGROUND]
        current_index = tier_order.index(current_tier)
        
        if current_index < len(tier_order) - 1:
            target_tier = tier_order[current_index + 1]
            
            # Remove from current tier
            if item_id in self.priority_queues[current_tier]:
                self.priority_queues[current_tier].remove(item_id)
                
            # Add to new tier
            self.priority_queues[target_tier].append(item_id)
            priority.tier = target_tier
            
            # Reset consecutive stable periods
            priority.consecutive_stable_periods = 0
            
            logger.debug(f"Demoted item {item_id} from {current_tier.name} to {target_tier.name}")
            
    async def get_market_stats(self) -> Dict:
        """Get current market statistics."""
        stats = {
            'total_items_tracked': len(self.item_priorities),
            'tier_distribution': {
                tier.name: len(items) for tier, items in self.priority_queues.items()
            },
            'active_users': len(self.user_activity),
            'goal_plan_items': len(self.active_goal_items),
            'high_volatility_items': sum(1 for p in self.item_priorities.values() 
                                       if p.volatility_score >= self.volatility_thresholds['high']),
            'last_bulk_update': datetime.fromtimestamp(self.last_bulk_fetch).isoformat(),
            'service_uptime': time.time() - getattr(self, 'start_time', time.time())
        }
        
        return stats
    
    # ===== AI INTEGRATION METHODS =====
    
    async def get_ai_market_context(self, item_ids: List[int], include_predictions: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive market context for AI agent queries.
        
        Args:
            item_ids: List of item IDs to analyze
            include_predictions: Whether to include price predictions
            
        Returns:
            Dict with market intelligence for AI consumption
        """
        context = {
            'timestamp': datetime.now().isoformat(),
            'items': {},
            'market_summary': {},
            'events': [],
            'recommendations': []
        }
        
        try:
            for item_id in item_ids[:10]:  # Limit to prevent overload
                if item_id in self.item_priorities:
                    priority = self.item_priorities[item_id]
                    
                    # Get recent price data
                    price_history = list(priority.recent_prices)[-10:]  # Last 10 prices
                    volume_history = list(priority.recent_volumes)[-10:]  # Last 10 volumes
                    
                    # Calculate market metrics
                    current_price = price_history[-1] if price_history else 0
                    price_change = 0
                    if len(price_history) >= 2:
                        price_change = ((current_price - price_history[0]) / price_history[0]) * 100
                    
                    # Volume analysis
                    avg_volume = sum(volume_history) / len(volume_history) if volume_history else 0
                    volume_trend = "increasing" if len(volume_history) >= 2 and volume_history[-1] > volume_history[0] else "decreasing"
                    
                    context['items'][item_id] = {
                        'current_price': current_price,
                        'price_change_pct': price_change,
                        'volatility_score': priority.volatility_score,
                        'volume_score': priority.volume_score,
                        'user_interest_score': priority.user_interest_score,
                        'tier': priority.tier.name,
                        'last_updated': priority.last_updated.isoformat(),
                        'next_update': priority.next_update.isoformat(),
                        'is_trending': abs(price_change) > 5.0,  # 5% change
                        'is_volatile': priority.volatility_score > self.volatility_thresholds['high'],
                        'avg_volume': avg_volume,
                        'volume_trend': volume_trend,
                        'price_history': price_history[-5:],  # Last 5 prices for context
                    }
                    
                    # Add predictions if requested
                    if include_predictions:
                        prediction = await self._predict_price_movement(priority, price_history)
                        context['items'][item_id]['prediction'] = prediction
            
            # Market summary
            context['market_summary'] = {
                'total_tracked_items': len(self.item_priorities),
                'high_volatility_count': sum(1 for p in self.item_priorities.values() 
                                           if p.volatility_score >= self.volatility_thresholds['high']),
                'user_active_items': sum(1 for p in self.item_priorities.values() if p.is_user_active),
                'realtime_items': len(self.priority_queues[PriorityTier.REALTIME]),
                'market_activity_level': self._calculate_market_activity_level(),
            }
            
            # Recent market events
            context['events'] = await self._get_recent_market_events(item_ids)
            
        except Exception as e:
            logger.error(f"Error getting AI market context: {e}")
            context['error'] = str(e)
        
        return context
    
    async def boost_item_priority_for_ai(self, item_id: int, user_id: str = "ai_agent", boost_duration_minutes: int = 30) -> bool:
        """
        Temporarily boost an item's priority when AI agent is analyzing it.
        
        Args:
            item_id: Item to boost
            user_id: User/AI agent identifier
            boost_duration_minutes: How long to maintain boost
            
        Returns:
            True if boosted successfully
        """
        try:
            if item_id not in self.item_priorities:
                logger.warning(f"Item {item_id} not in priorities, cannot boost")
                return False
            
            priority = self.item_priorities[item_id]
            
            # Boost to near-realtime for AI queries
            original_tier = priority.tier
            priority.tier = PriorityTier.NEAR_REALTIME
            
            # Schedule boost removal
            boost_end_time = datetime.now() + timedelta(minutes=boost_duration_minutes)
            
            # Track AI interest
            await self.track_user_activity(hash(user_id), item_id, 'ai_query')
            
            logger.info(f"Boosted item {item_id} priority from {original_tier.name} to {priority.tier.name} for AI analysis")
            
            # Force immediate update
            await self._update_item_price(item_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error boosting item priority for AI: {e}")
            return False
    
    async def get_investment_opportunities(self, 
                                        capital_amount: int,
                                        risk_tolerance: str = "moderate",
                                        investment_horizon: str = "short_term") -> List[Dict]:
        """
        Get investment opportunities tailored for AI agent recommendations.
        
        Args:
            capital_amount: Available investment capital in GP
            risk_tolerance: conservative, moderate, aggressive
            investment_horizon: short_term, medium_term, long_term
            
        Returns:
            List of investment opportunities with AI-friendly context
        """
        opportunities = []
        
        try:
            # Define risk thresholds
            risk_thresholds = {
                "conservative": {"max_volatility": 0.02, "min_volume": 1000},
                "moderate": {"max_volatility": 0.05, "min_volume": 500}, 
                "aggressive": {"max_volatility": float('inf'), "min_volume": 100}
            }
            
            threshold = risk_thresholds.get(risk_tolerance, risk_thresholds["moderate"])
            
            # Analyze items that fit criteria
            for item_id, priority in self.item_priorities.items():
                if (priority.volatility_score <= threshold["max_volatility"] and 
                    priority.volume_score >= threshold["min_volume"] / 1000):  # Normalize volume score
                    
                    # Get current market data
                    cache_key = f"{self.cache_prefix}item_{item_id}"
                    price_data = cache.get(cache_key)
                    
                    if price_data and price_data.get('price'):
                        current_price = price_data['price']
                        
                        # Calculate position sizing
                        max_position_size = min(capital_amount // 4, current_price * 1000)  # Max 25% of capital or 1000 units
                        potential_units = min(max_position_size // current_price, 1000) if current_price > 0 else 0
                        
                        if potential_units > 0:
                            # Calculate potential returns based on historical volatility
                            expected_return = self._calculate_expected_return(priority, investment_horizon)
                            total_investment = current_price * potential_units
                            
                            opportunity = {
                                'item_id': item_id,
                                'current_price': current_price,
                                'recommended_units': potential_units,
                                'total_investment': total_investment,
                                'expected_return_pct': expected_return,
                                'potential_profit': total_investment * (expected_return / 100),
                                'risk_level': risk_tolerance,
                                'volatility_score': priority.volatility_score,
                                'volume_score': priority.volume_score,
                                'user_interest_score': priority.user_interest_score,
                                'investment_grade': self._calculate_investment_grade(priority, risk_tolerance),
                                'reasoning': self._generate_investment_reasoning(priority, expected_return),
                            }
                            
                            opportunities.append(opportunity)
            
            # Sort by investment grade and potential profit
            opportunities.sort(key=lambda x: (x['investment_grade'], x['potential_profit']), reverse=True)
            
            return opportunities[:20]  # Top 20 opportunities
            
        except Exception as e:
            logger.error(f"Error getting investment opportunities: {e}")
            return []
    
    async def track_ai_query_patterns(self, query_type: str, item_ids: List[int], user_context: Dict = None):
        """
        Track AI query patterns to improve recommendations.
        
        Args:
            query_type: Type of query (price_inquiry, investment_advice, etc.)
            item_ids: Items involved in the query
            user_context: Additional context about the query
        """
        try:
            # Boost priority for queried items
            for item_id in item_ids:
                await self.boost_item_priority_for_ai(item_id)
            
            # Track query patterns for learning
            query_data = {
                'timestamp': datetime.now().isoformat(),
                'query_type': query_type,
                'item_ids': item_ids,
                'context': user_context or {}
            }
            
            # Store in cache for analytics (could be moved to database)
            cache_key = f"ai_queries:{datetime.now().strftime('%Y%m%d')}"
            queries = cache.get(cache_key, [])
            queries.append(query_data)
            cache.set(cache_key, queries[-1000:], timeout=86400)  # Keep last 1000 queries for 24h
            
        except Exception as e:
            logger.error(f"Error tracking AI query patterns: {e}")
    
    async def _predict_price_movement(self, priority: 'ItemPriority', price_history: List[int]) -> Dict:
        """Simple price movement prediction based on trends and volatility."""
        if len(price_history) < 3:
            return {"direction": "unknown", "confidence": 0.0, "reasoning": "Insufficient data"}
        
        # Simple trend analysis
        recent_trend = (price_history[-1] - price_history[-3]) / price_history[-3] if price_history[-3] > 0 else 0
        
        # Volatility-adjusted confidence
        confidence = max(0.1, 1.0 - priority.volatility_score)
        
        direction = "up" if recent_trend > 0.02 else "down" if recent_trend < -0.02 else "stable"
        
        return {
            "direction": direction,
            "confidence": confidence,
            "trend_strength": abs(recent_trend),
            "reasoning": f"Based on recent {direction} trend with {confidence:.1%} confidence"
        }
    
    async def _get_recent_market_events(self, item_ids: List[int]) -> List[Dict]:
        """Get recent market events that might affect prices."""
        events = []
        
        # Check for volume spikes
        for item_id in item_ids:
            if item_id in self.item_priorities:
                priority = self.item_priorities[item_id]
                if priority.volume_momentum > self.volume_spike_threshold:
                    events.append({
                        "type": "volume_spike",
                        "item_id": item_id,
                        "severity": priority.volume_momentum,
                        "description": f"Volume spike detected: {priority.volume_momentum:.1f}x normal volume"
                    })
        
        return events[-10:]  # Last 10 events
    
    def _calculate_market_activity_level(self) -> str:
        """Calculate overall market activity level."""
        active_items = sum(1 for p in self.item_priorities.values() if p.is_user_active)
        volatile_items = sum(1 for p in self.item_priorities.values() 
                           if p.volatility_score >= self.volatility_thresholds['medium'])
        
        total_items = len(self.item_priorities)
        if total_items == 0:
            return "inactive"
        
        activity_ratio = (active_items + volatile_items) / total_items
        
        if activity_ratio > 0.3:
            return "very_high"
        elif activity_ratio > 0.2:
            return "high"
        elif activity_ratio > 0.1:
            return "moderate"
        else:
            return "low"
    
    def _calculate_expected_return(self, priority: 'ItemPriority', investment_horizon: str) -> float:
        """Calculate expected return based on volatility and trends."""
        base_return = priority.volatility_score * 100  # Convert volatility to return %
        
        # Adjust for investment horizon
        horizon_multipliers = {
            "short_term": 0.5,   # Conservative for short-term
            "medium_term": 1.0,  # Base case
            "long_term": 1.5     # Higher potential for long-term
        }
        
        multiplier = horizon_multipliers.get(investment_horizon, 1.0)
        return base_return * multiplier
    
    def _calculate_investment_grade(self, priority: 'ItemPriority', risk_tolerance: str) -> float:
        """Calculate investment grade score (0-100)."""
        volume_score = min(priority.volume_score * 10, 40)  # Up to 40 points for volume
        stability_score = max(0, 30 - (priority.volatility_score * 100))  # Up to 30 points for stability
        interest_score = priority.user_interest_score * 20  # Up to 20 points for interest
        momentum_score = min(abs(priority.price_change_score) * 10, 10)  # Up to 10 points for momentum
        
        total_score = volume_score + stability_score + interest_score + momentum_score
        
        # Adjust for risk tolerance
        if risk_tolerance == "conservative" and priority.volatility_score > 0.03:
            total_score *= 0.7  # Penalty for volatile items in conservative portfolio
        elif risk_tolerance == "aggressive" and priority.volatility_score > 0.05:
            total_score *= 1.2  # Bonus for volatile items in aggressive portfolio
        
        return min(100, total_score)
    
    def _generate_investment_reasoning(self, priority: 'ItemPriority', expected_return: float) -> str:
        """Generate human-readable reasoning for investment recommendation."""
        reasons = []
        
        if priority.volume_score > 0.5:
            reasons.append("high trading volume indicates good liquidity")
        
        if priority.volatility_score < 0.02:
            reasons.append("low volatility suggests stable investment")
        elif priority.volatility_score > 0.05:
            reasons.append("high volatility offers profit potential but increases risk")
        
        if priority.user_interest_score > 0.3:
            reasons.append("high user interest suggests market demand")
        
        if expected_return > 5:
            reasons.append(f"projected {expected_return:.1f}% return based on historical patterns")
        
        return "; ".join(reasons) if reasons else "standard market metrics"


# Global MCP service instance
mcp_service = MCPPriceService()