"""
Smart Opportunity Detection Service - Ultra-Intelligent Trading Signal Generator

This service provides precision price analysis to detect exact buy/sell opportunities
with specific GP amounts, optimal timing, and profit probability scoring.
Optimized for M1 MacBook Pro with 8GB RAM using efficient streaming algorithms.
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field
from django.db.models import Q, Avg, Count, Max, Min
from django.utils import timezone
from django.core.cache import cache
import statistics

from apps.items.models import Item, ItemCategoryMapping
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.prices.merchant_models import MarketTrend, MerchantOpportunity

logger = logging.getLogger(__name__)


@dataclass
class PrecisionOpportunity:
    """Represents a precise trading opportunity with exact GP amounts."""
    item_id: int
    item_name: str
    
    # Exact pricing
    current_price: int
    recommended_buy_price: int
    recommended_sell_price: int
    expected_profit_per_item: int
    expected_profit_margin_pct: float
    
    # Timing intelligence  
    optimal_buy_window_start: datetime
    optimal_sell_window_start: datetime
    estimated_hold_time_hours: float
    
    # Risk & confidence
    success_probability_pct: float
    confidence_score: float
    risk_level: str  # 'low', 'medium', 'high'
    
    # Volume & market data
    daily_volume: int
    recent_volatility: float
    market_momentum: str  # 'bullish', 'bearish', 'neutral'
    
    # Position sizing
    recommended_position_size: int
    buy_limit: int  # GE buy limit per 4 hours
    max_capital_allocation_pct: float
    
    # Reasoning
    signals: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass  
class MarketSignal:
    """Real-time market signal for trading decisions."""
    signal_type: str  # 'strong_buy', 'buy', 'hold', 'sell', 'strong_sell'
    strength: float  # 0.0 to 1.0
    trigger_price: int
    target_price: int
    stop_loss_price: Optional[int]
    reasoning: str
    expires_at: datetime


class SmartOpportunityDetector:
    """
    Ultra-intelligent opportunity detection engine optimized for M1 MacBook.
    
    Uses streaming analysis and efficient algorithms to minimize memory usage
    while providing maximum trading intelligence.
    """
    
    def __init__(self):
        # Memory-efficient configuration for M1 8GB RAM
        self.max_analysis_items = 500  # Limit concurrent analysis
        self.cache_duration = 300  # 5 minutes cache
        self.batch_size = 50  # Process in small batches
        
        # Trading intelligence thresholds
        self.min_profit_margin = 0.02  # 2% minimum profit
        self.high_volume_threshold = 100  # High volume items
        self.volatility_opportunity_threshold = 0.15  # 15% volatility sweet spot
        
        # Pattern recognition parameters
        self.support_resistance_periods = [24, 72, 168]  # Hours to analyze
        self.momentum_periods = [1, 6, 24]  # Hours for momentum calculation
        self.anomaly_detection_std = 2.0  # Standard deviations for anomalies
        
    async def detect_precision_opportunities(self, 
                                           capital_gp: int = 100000000,
                                           risk_tolerance: str = 'moderate',
                                           max_opportunities: int = 10) -> List[PrecisionOpportunity]:
        """
        Detect precise trading opportunities with exact buy/sell prices.
        
        Args:
            capital_gp: Available trading capital in GP
            risk_tolerance: 'conservative', 'moderate', 'aggressive'
            max_opportunities: Maximum opportunities to return
            
        Returns:
            List of precision opportunities sorted by expected profit
        """
        try:
            logger.info(f"Detecting precision opportunities for {capital_gp:,} GP capital")
            
            # Get price range constraints based on capital
            min_price, max_price = self._get_price_range_for_capital(capital_gp)
            logger.info(f"Using price range: {min_price:,} - {max_price:,} GP")
            
            # Generate variation seed for different item selection
            variation_seed = int(datetime.now().timestamp()) % 1000
            
            # Get high-potential items using streaming analysis with capital filtering and variation
            candidate_items = await self._get_high_potential_items(
                min_price, max_price, variation_seed=variation_seed
            )
            logger.info(f"Found {len(candidate_items)} candidate items in price range")
            
            # If no items found in the target range, try progressively lower ranges  
            used_fallback = False
            if not candidate_items:
                logger.warning(f"No items found in {min_price:,}-{max_price:,} range, trying fallback ranges")
                fallback_ranges = self._get_fallback_price_ranges(capital_gp)
                used_fallback = True
                
                for fallback_min, fallback_max in fallback_ranges:
                    logger.info(f"Trying fallback range: {fallback_min:,}-{fallback_max:,} GP")
                    candidate_items = await self._get_high_potential_items(
                        fallback_min, fallback_max, variation_seed=variation_seed
                    )
                    if candidate_items:
                        logger.info(f"Found {len(candidate_items)} items in fallback range {fallback_min:,}-{fallback_max:,}")
                        break
                
                if not candidate_items:
                    logger.warning("No items found even in fallback ranges, using all available items")
                    candidate_items = await self._get_high_potential_items(
                        0, 50000000, variation_seed=variation_seed
                    )
            
            opportunities = []
            processed_count = 0
            
            # Process items in memory-efficient batches
            for i in range(0, len(candidate_items), self.batch_size):
                batch = candidate_items[i:i + self.batch_size]
                
                for item in batch:
                    if processed_count >= self.max_analysis_items:
                        break
                        
                    opportunity = await self._analyze_item_opportunity(
                        item, capital_gp, risk_tolerance
                    )
                    
                    if opportunity and opportunity.success_probability_pct >= 60:
                        opportunities.append(opportunity)
                        
                    processed_count += 1
                
                # Yield control to prevent blocking
                await asyncio.sleep(0.001)
                
                if processed_count >= self.max_analysis_items:
                    break
            
            # Sort by expected profit and risk-adjusted returns
            opportunities.sort(
                key=lambda x: x.expected_profit_per_item * x.confidence_score,
                reverse=True
            )
            
            logger.info(f"Found {len(opportunities)} precision opportunities")
            return opportunities[:max_opportunities]
            
        except Exception as e:
            logger.error(f"Error detecting opportunities: {e}")
            return []
    
    def _get_price_range_for_capital(self, capital_gp: int) -> Tuple[int, int]:
        """
        Get appropriate price range for items based on available capital.
        
        Args:
            capital_gp: Available trading capital in GP
            
        Returns:
            Tuple of (min_price, max_price) for items
        """
        if capital_gp <= 1000000:  # 1M GP - Conservative trading
            return (100, 50000)  # Items under 50K each
        elif capital_gp <= 5000000:  # 5M GP - Medium-risk diversified
            return (1000, 200000)  # 1K-200K range
        elif capital_gp <= 10000000:  # 10M GP - Balanced strategies
            return (10000, 500000)  # 10K-500K range  
        elif capital_gp <= 25000000:  # 25M GP - Advanced trading
            return (50000, 2000000)  # 50K-2M range
        elif capital_gp <= 50000000:  # 50M GP - Premium strategies
            return (200000, 5000000)  # 200K-5M range
        else:  # 100M+ GP - Elite trading
            return (500000, 50000000)  # 500K-50M+ range
    
    def _get_fallback_price_ranges(self, capital_gp: int) -> List[Tuple[int, int]]:
        """
        Get fallback price ranges if no items found in the primary range.
        
        Returns progressively lower ranges to ensure we find some items.
        """
        if capital_gp <= 1000000:  # 1M GP
            return [(100, 25000), (100, 10000), (100, 5000)]
        elif capital_gp <= 5000000:  # 5M GP  
            return [(1000, 100000), (500, 50000), (100, 25000)]
        elif capital_gp <= 10000000:  # 10M GP
            return [(5000, 300000), (1000, 150000), (500, 75000)]
        elif capital_gp <= 25000000:  # 25M GP
            return [(10000, 500000), (5000, 300000), (1000, 200000)]
        elif capital_gp <= 50000000:  # 50M GP
            return [(50000, 1000000), (10000, 500000), (5000, 300000)]
        else:  # 100M+ GP
            return [(100000, 2000000), (50000, 1000000), (10000, 500000)]
    
    async def _get_high_potential_items(self, 
                                      min_price: int = 0, 
                                      max_price: int = 50000000,
                                      variation_seed: int = None,
                                      exclude_items: List[int] = None) -> List[Item]:
        """Get items with high trading potential using efficient querying with query variation support."""
        exclude_items = exclude_items or []
        
        # Use variation seed for consistent but different results per query
        if variation_seed is None:
            import time
            variation_seed = int(time.time()) % 1000
        
        # Don't cache when variation is applied or items are excluded
        cache_key = f"high_potential_items_{min_price}_{max_price}" if not exclude_items and variation_seed else None
        
        if cache_key:
            cached = cache.get(cache_key)
            if cached:
                return cached
        
        # Efficient query to get items with recent price data, volume, and price filtering
        # FIXED: Include more diverse items by lowering profit threshold and adding category variety
        queryset = Item.objects.filter(
            profit_calc__isnull=False,
            profit_calc__current_buy_price__gte=min_price,
            profit_calc__current_buy_price__lte=max_price,
            profit_calc__daily_volume__gte=5,  # Lowered minimum volume for more diversity
        ).select_related('profit_calc')
        
        # Include items with any positive profit OR high-value items (even with small margins)
        queryset = queryset.filter(
            Q(profit_calc__current_profit__gte=50) |  # Lowered from 100 to 50 GP minimum
            Q(profit_calc__current_buy_price__gte=100000)  # OR expensive items (100K+) regardless of margin
        )
        
        # Exclude previously shown items
        if exclude_items:
            queryset = queryset.exclude(item_id__in=exclude_items)
            logger.info(f"Excluding {len(exclude_items)} previously shown items")
        
        # Apply different ordering based on variation seed for different results
        ordering_options = [
            '-profit_calc__current_profit',  # Highest profit first
            '-profit_calc__current_profit_margin',  # Best margin first  
            '-profit_calc__daily_volume',  # Highest volume first
            'profit_calc__current_buy_price',  # Cheapest first
            '-profit_calc__current_buy_price',  # Most expensive first
            '?'  # Random
        ]
        
        selected_ordering = ordering_options[variation_seed % len(ordering_options)]
        queryset = queryset.order_by(selected_ordering)
        
        logger.info(f"Using ordering: {selected_ordering} (seed: {variation_seed})")
        
        items = []
        async for item in queryset[:500]:  # Get up to 500 items
            items.append(item)
        
        # Only cache if no exclusions and consistent seed
        if cache_key and not exclude_items:
            cache.set(cache_key, items, 60)  # Short cache for item rotation
            
        logger.info(f"Retrieved {len(items)} items with variation seed {variation_seed}")
        return items
    
    def _generate_variation_seed(self, query: str, exclude_items: List[int]) -> int:
        """Generate a variation seed based on query content for consistent but different results."""
        import hashlib
        
        # Create seed based on query content and exclusion list
        query_lower = query.lower()
        
        # Base seed from query
        query_hash = hashlib.md5(query_lower.encode()).hexdigest()[:8]
        base_seed = int(query_hash, 16) % 10000
        
        # Modify seed based on query content for different item sets
        if 'different' in query_lower or 'other' in query_lower or 'new' in query_lower:
            base_seed += 1000  # Shift to different range
        elif 'expensive' in query_lower or 'bigger' in query_lower:
            base_seed += 2000  # Shift to higher value items
        elif 'cheap' in query_lower or 'smaller' in query_lower:
            base_seed += 3000  # Shift to lower value items
        elif any(num in query_lower for num in ['5', 'five', '10', 'ten', '20', 'twenty']):
            # Different seed for specific number requests
            base_seed += 4000
            
        # Add exclusion list influence
        if exclude_items:
            exclusion_hash = sum(exclude_items) % 1000
            base_seed += exclusion_hash
            
        return base_seed % 10000
    
    async def _analyze_item_opportunity(self, 
                                      item: Item, 
                                      capital_gp: int,
                                      risk_tolerance: str) -> Optional[PrecisionOpportunity]:
        """Analyze a specific item for trading opportunities."""
        try:
            # Get recent price history efficiently
            price_history = await self._get_recent_price_history(item)
            if len(price_history) < 5:  # Need minimum data
                return None
            
            # Calculate support/resistance levels
            support_level, resistance_level = await self._calculate_support_resistance(
                item, price_history
            )
            
            # Detect price anomalies (opportunities)
            current_price = item.profit_calc.current_buy_price
            if not current_price:
                return None
                
            # Check if current price represents an opportunity
            opportunity_signal = await self._detect_price_opportunity(
                current_price, support_level, resistance_level, price_history
            )
            
            if not opportunity_signal:
                return None
            
            # Calculate precise buy/sell prices
            buy_price, sell_price = await self._calculate_optimal_prices(
                current_price, support_level, resistance_level, 
                item.profit_calc.daily_volume, risk_tolerance
            )
            
            # Calculate profit metrics
            profit_per_item = sell_price - buy_price
            if profit_per_item <= 0:
                return None
                
            profit_margin_pct = (profit_per_item / buy_price) * 100
            
            # Calculate timing intelligence
            buy_window, sell_window, hold_time = await self._calculate_optimal_timing(
                item, price_history
            )
            
            # Calculate success probability using multiple factors
            success_probability = await self._calculate_success_probability(
                item, buy_price, sell_price, price_history
            )
            
            # Position sizing based on capital and risk
            position_size, max_allocation = await self._calculate_position_sizing(
                capital_gp, buy_price, risk_tolerance, item.profit_calc.daily_volume
            )
            
            # Generate trading signals and warnings
            signals, warnings = await self._generate_trading_intelligence(
                item, current_price, buy_price, sell_price, price_history
            )
            
            return PrecisionOpportunity(
                item_id=item.item_id,
                item_name=item.name,
                current_price=current_price,
                recommended_buy_price=buy_price,
                recommended_sell_price=sell_price,
                expected_profit_per_item=profit_per_item,
                expected_profit_margin_pct=profit_margin_pct,
                optimal_buy_window_start=buy_window,
                optimal_sell_window_start=sell_window,
                estimated_hold_time_hours=hold_time,
                success_probability_pct=success_probability,
                confidence_score=min(success_probability / 100 * 1.2, 1.0),
                risk_level=await self._assess_risk_level(item, profit_margin_pct),
                daily_volume=item.profit_calc.daily_volume,
                recent_volatility=await self._calculate_volatility(price_history),
                market_momentum=await self._detect_momentum(price_history),
                recommended_position_size=position_size,
                buy_limit=item.limit,
                max_capital_allocation_pct=max_allocation,
                signals=signals,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error analyzing item {item.name}: {e}")
            return None
    
    async def _get_recent_price_history(self, item: Item, hours: int = 168) -> List[dict]:
        """Get recent price history efficiently."""
        cache_key = f"price_history_{item.item_id}_{hours}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        since = timezone.now() - timedelta(hours=hours)
        
        prices = []
        async for snapshot in PriceSnapshot.objects.filter(
            item=item,
            created_at__gte=since,
            high_price__isnull=False
        ).order_by('created_at'):
            prices.append({
                'price': snapshot.high_price,
                'timestamp': snapshot.created_at,
                'volume': snapshot.total_volume or 0
            })
        
        cache.set(cache_key, prices, 60)  # 1 minute cache
        return prices
    
    async def _calculate_support_resistance(self, 
                                          item: Item,
                                          price_history: List[dict]) -> Tuple[int, int]:
        """Calculate support and resistance levels using efficient algorithms."""
        if len(price_history) < 10:
            current_price = price_history[-1]['price'] if price_history else 1000
            return int(current_price * 0.95), int(current_price * 1.05)
        
        prices = [p['price'] for p in price_history]
        
        # Calculate support (recent low areas with volume)
        recent_prices = prices[-48:]  # Last 48 data points
        support_level = int(np.percentile(recent_prices, 25))
        
        # Calculate resistance (recent high areas)
        resistance_level = int(np.percentile(recent_prices, 75))
        
        return support_level, resistance_level
    
    async def _detect_price_opportunity(self,
                                      current_price: int,
                                      support: int,
                                      resistance: int,
                                      price_history: List[dict]) -> bool:
        """Detect if current price represents a trading opportunity."""
        if not price_history:
            return False
        
        # Opportunity exists if price is near support (buy opportunity)
        # or showing momentum toward resistance
        price_range = resistance - support
        if price_range <= 0:
            return False
        
        # Check if price is in lower 30% of range (good buy opportunity)
        position_in_range = (current_price - support) / price_range
        
        if position_in_range <= 0.3:  # Near support - buy opportunity
            return True
            
        # Check for momentum opportunities
        recent_trend = await self._get_recent_trend(price_history)
        if recent_trend == 'upward' and position_in_range <= 0.6:
            return True
            
        return False
    
    async def _calculate_optimal_prices(self,
                                      current_price: int,
                                      support: int,
                                      resistance: int,
                                      volume: int,
                                      risk_tolerance: str) -> Tuple[int, int]:
        """Calculate optimal buy and sell prices based on risk tolerance."""
        price_range = resistance - support
        
        # Adjust for risk tolerance
        risk_multipliers = {
            'conservative': {'buy': 0.98, 'sell': 1.03},
            'moderate': {'buy': 0.96, 'sell': 1.05},
            'aggressive': {'buy': 0.94, 'sell': 1.08}
        }
        
        multiplier = risk_multipliers.get(risk_tolerance, risk_multipliers['moderate'])
        
        # Calculate buy price (slightly above support)
        buy_price = max(
            int(support * 1.02),  # 2% above support for safety
            int(current_price * multiplier['buy'])  # Or below current price
        )
        
        # Calculate sell price (below resistance with margin)
        sell_price = min(
            int(resistance * 0.95),  # 5% below resistance for quick sale
            int(buy_price * multiplier['sell'])  # Or reasonable profit target
        )
        
        # Ensure minimum profit
        min_profit = max(50, int(buy_price * 0.02))  # 2% minimum
        if sell_price - buy_price < min_profit:
            sell_price = buy_price + min_profit
        
        return buy_price, sell_price
    
    async def _calculate_optimal_timing(self,
                                      item: Item,
                                      price_history: List[dict]) -> Tuple[datetime, datetime, float]:
        """Calculate optimal buy/sell timing windows."""
        now = timezone.now()
        
        # Default timing (can be enhanced with more data)
        optimal_buy_time = now + timedelta(minutes=30)  # Give time to prepare
        optimal_sell_time = now + timedelta(hours=4)    # Conservative hold time
        hold_time_hours = 6.0  # Default hold time
        
        # Analyze historical patterns for better timing
        if len(price_history) >= 24:
            # Find best historical buying hours
            hourly_patterns = {}
            for price_data in price_history:
                hour = price_data['timestamp'].hour
                if hour not in hourly_patterns:
                    hourly_patterns[hour] = []
                hourly_patterns[hour].append(price_data['price'])
            
            # Find hour with lowest average prices (best buy time)
            best_buy_hour = min(hourly_patterns.keys(),
                               key=lambda h: statistics.mean(hourly_patterns[h]))
            
            # Calculate next occurrence of best buy hour
            next_buy_time = now.replace(hour=best_buy_hour, minute=0, second=0)
            if next_buy_time <= now:
                next_buy_time += timedelta(days=1)
            
            optimal_buy_time = next_buy_time
            optimal_sell_time = optimal_buy_time + timedelta(hours=6)
        
        return optimal_buy_time, optimal_sell_time, hold_time_hours
    
    async def _calculate_success_probability(self,
                                           item: Item,
                                           buy_price: int,
                                           sell_price: int,
                                           price_history: List[dict]) -> float:
        """Calculate probability of successful trade."""
        if not price_history:
            return 50.0  # Default probability
        
        scores = []
        
        # Volume score (higher volume = higher success rate)
        volume = item.profit_calc.daily_volume
        if volume >= 1000:
            scores.append(90)
        elif volume >= 100:
            scores.append(75)
        elif volume >= 50:
            scores.append(60)
        else:
            scores.append(40)
        
        # Price range analysis
        prices = [p['price'] for p in price_history]
        price_max = max(prices)
        price_min = min(prices)
        
        # Check if sell price is realistic based on history
        if sell_price <= price_max:
            scores.append(85)
        elif sell_price <= price_max * 1.1:
            scores.append(70)
        else:
            scores.append(30)  # Unrealistic sell price
        
        # Volatility score (moderate volatility is best)
        volatility = await self._calculate_volatility(price_history)
        if 0.05 <= volatility <= 0.15:  # Sweet spot
            scores.append(80)
        elif volatility <= 0.25:
            scores.append(65)
        else:
            scores.append(45)  # Too volatile
        
        # Trend score
        trend = await self._get_recent_trend(price_history)
        if trend == 'upward':
            scores.append(85)
        elif trend == 'stable':
            scores.append(70)
        else:
            scores.append(50)
        
        return statistics.mean(scores)
    
    async def _calculate_position_sizing(self,
                                       capital_gp: int,
                                       buy_price: int,
                                       risk_tolerance: str,
                                       daily_volume: int) -> Tuple[int, float]:
        """Calculate optimal position size based on capital and risk."""
        # Risk-based allocation limits
        risk_limits = {
            'conservative': 0.15,  # 15% max per position
            'moderate': 0.25,      # 25% max per position  
            'aggressive': 0.40     # 40% max per position
        }
        
        max_allocation_pct = risk_limits.get(risk_tolerance, 0.25)
        max_capital = int(capital_gp * max_allocation_pct)
        
        # Volume-based sizing (don't exceed daily volume capacity)
        volume_limit = daily_volume // 4  # Don't exceed 25% of daily volume
        
        # Calculate position size
        max_units_by_capital = max_capital // buy_price
        max_units_by_volume = volume_limit
        
        position_size = min(max_units_by_capital, max_units_by_volume)
        
        return position_size, max_allocation_pct * 100
    
    async def _generate_trading_intelligence(self,
                                           item: Item,
                                           current_price: int,
                                           buy_price: int,
                                           sell_price: int,
                                           price_history: List[dict]) -> Tuple[List[str], List[str]]:
        """Generate trading signals and warnings."""
        signals = []
        warnings = []
        
        # Price signals
        if current_price > buy_price:
            signals.append(f"Current price ({current_price:,} GP) is above target buy ({buy_price:,} GP)")
        else:
            signals.append(f"STRONG BUY SIGNAL: Price at target or below ({current_price:,} GP ≤ {buy_price:,} GP)")
        
        # Volume signals  
        volume = item.profit_calc.daily_volume
        if volume >= 500:
            signals.append("HIGH LIQUIDITY: Easy entry/exit")
        elif volume >= 100:
            signals.append("GOOD LIQUIDITY: Moderate trading ease")
        else:
            warnings.append("LOW LIQUIDITY: May be difficult to buy/sell quickly")
        
        # Profit signals
        profit_margin = ((sell_price - buy_price) / buy_price) * 100
        if profit_margin >= 10:
            signals.append(f"EXCELLENT PROFIT: {profit_margin:.1f}% margin")
        elif profit_margin >= 5:
            signals.append(f"GOOD PROFIT: {profit_margin:.1f}% margin")
        else:
            warnings.append(f"LOW PROFIT: Only {profit_margin:.1f}% margin")
        
        # Volatility warnings
        volatility = await self._calculate_volatility(price_history)
        if volatility > 0.3:
            warnings.append("HIGH VOLATILITY: Price swings may be large")
        elif volatility < 0.02:
            warnings.append("LOW VOLATILITY: Price may move slowly")
        
        return signals, warnings
    
    # Helper methods
    async def _calculate_volatility(self, price_history: List[dict]) -> float:
        """Calculate price volatility."""
        if len(price_history) < 2:
            return 0.0
        
        prices = [p['price'] for p in price_history]
        if len(prices) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        return np.std(returns) if returns else 0.0
    
    async def _get_recent_trend(self, price_history: List[dict]) -> str:
        """Determine recent price trend."""
        if len(price_history) < 5:
            return 'stable'
        
        recent_prices = [p['price'] for p in price_history[-5:]]
        
        # Simple trend detection
        if recent_prices[-1] > recent_prices[0] * 1.02:
            return 'upward'
        elif recent_prices[-1] < recent_prices[0] * 0.98:
            return 'downward' 
        else:
            return 'stable'
    
    async def _detect_momentum(self, price_history: List[dict]) -> str:
        """Detect market momentum."""
        if len(price_history) < 10:
            return 'neutral'
        
        prices = [p['price'] for p in price_history]
        
        # Compare recent vs older prices
        recent_avg = statistics.mean(prices[-5:])
        older_avg = statistics.mean(prices[-10:-5])
        
        change_pct = (recent_avg - older_avg) / older_avg
        
        if change_pct > 0.03:
            return 'bullish'
        elif change_pct < -0.03:
            return 'bearish'
        else:
            return 'neutral'
    
    async def _assess_risk_level(self, item: Item, profit_margin_pct: float) -> str:
        """Assess risk level of the opportunity."""
        volume = item.profit_calc.daily_volume
        
        # High volume + good margin = low risk
        if volume >= 500 and profit_margin_pct >= 5:
            return 'low'
        
        # Moderate volume or margin = medium risk
        if volume >= 100 or profit_margin_pct >= 3:
            return 'medium'
        
        # Low volume and/or margin = high risk
        return 'high'
    
    async def detect_tagged_opportunities(self, 
                                        query: str, 
                                        capital_gp: int = 100000000,
                                        max_opportunities: int = 10,
                                        exclude_items: List[int] = None) -> List[PrecisionOpportunity]:
        """
        Detect opportunities using comprehensive tagging system with query variation.
        
        Args:
            query: User query to analyze for tags
            capital_gp: Available trading capital
            max_opportunities: Maximum opportunities to return
            exclude_items: Item IDs to exclude from results (for conversation memory)
            
        Returns:
            List of precision opportunities matching query tags
        """
        try:
            logger.info(f"Detecting tagged opportunities for query: '{query}'")
            exclude_items = exclude_items or []
            
            # Get relevant tags from query with enhanced variation support
            relevant_tags = self._extract_tags_from_query(query, capital_gp)
            logger.info(f"Extracted tags: {relevant_tags}")
            
            # Add query variation logic for "different", "other", "new" requests
            variation_seed = self._generate_variation_seed(query, exclude_items)
            logger.info(f"Using variation seed: {variation_seed} for query differentiation")
            
            if not relevant_tags:
                # Fall back to regular opportunity detection
                return await self.detect_precision_opportunities(capital_gp, 'moderate', max_opportunities)
            
            # Build query to find items with relevant tags
            items_query = Q()
            for tag in relevant_tags:
                items_query |= Q(categories__category__name=tag)
            
            # Get price range for capital filtering
            min_price, max_price = self._get_price_range_for_capital(capital_gp)
            
            # Get items matching tags with profit calculations and price filtering
            tagged_items = []
            async for item in Item.objects.filter(items_query).select_related('profit_calc').filter(
                profit_calc__isnull=False,
                profit_calc__current_buy_price__gte=min_price,
                profit_calc__current_buy_price__lte=max_price,
                profit_calc__daily_volume__gte=10,  # Minimum volume like regular detection
                profit_calc__current_profit__gte=100  # Minimum profit potential like regular detection
            ).distinct()[:max_opportunities * 3]:  # Get more for filtering
                tagged_items.append(item)
            
            logger.info(f"Found {len(tagged_items)} items matching tags")
            
            if not tagged_items:
                # Fall back to regular detection if no tagged items found
                return await self.detect_precision_opportunities(capital_gp, 'moderate', max_opportunities)
            
            # Analyze each tagged item
            opportunities = []
            for item in tagged_items:
                opportunity = await self._analyze_item_opportunity(item, capital_gp, 'moderate')
                if opportunity and opportunity.success_probability_pct >= 50:  # Lower threshold for tagged items
                    opportunities.append(opportunity)
            
            # Sort by profit potential
            opportunities.sort(
                key=lambda x: x.expected_profit_per_item * x.confidence_score,
                reverse=True
            )
            
            logger.info(f"Generated {len(opportunities)} tagged opportunities")
            return opportunities[:max_opportunities]
            
        except Exception as e:
            logger.error(f"Error detecting tagged opportunities: {e}")
            # Fall back to regular detection on error
            return await self.detect_precision_opportunities(capital_gp, 'moderate', max_opportunities)
    
    def _extract_tags_from_query(self, query: str, capital_gp: int) -> List[str]:
        """Extract relevant tags from user query."""
        tags = []
        query_lower = query.lower()
        
        # Price-based tags (only add if relevant to capital)
        if 'cheap' in query_lower or 'under' in query_lower:
            if '1k' in query_lower and capital_gp <= 100000:  # Only for small capital
                tags.append('under-1k')
            elif '5k' in query_lower and capital_gp <= 500000:  # Only for small-medium capital
                tags.extend(['under-1k', '1k-5k'])
            elif capital_gp <= 100000:  # Only add cheap tags for small capital
                tags.extend(['under-1k', '1k-5k'])
        
        # Strategy tags
        if 'bulk' in query_lower or 'lot of' in query_lower or 'many' in query_lower:
            tags.append('bulk-flip')
        if 'quick' in query_lower or 'fast' in query_lower:
            tags.append('quick-flip')
        if 'high margin' in query_lower or 'margin' in query_lower:
            tags.append('high-margin')
        if 'scalable' in query_lower or 'scale' in query_lower:
            tags.append('scalable')
        
        # Item type tags
        if 'potion' in query_lower:
            tags.append('potion')
        if 'weapon' in query_lower:
            tags.append('weapon')
        if 'armor' in query_lower or 'armour' in query_lower:
            tags.append('armor')
        if 'consumable' in query_lower:
            tags.append('consumable')
        if 'material' in query_lower:
            tags.append('material')
        if 'jewelry' in query_lower or 'jewellery' in query_lower:
            tags.append('jewelry')
        if 'rune' in query_lower:
            tags.append('rune')
        if 'tool' in query_lower:
            tags.append('tool')
        
        # Capital-based tags based on available capital
        if capital_gp < 10000:
            tags.append('micro-capital')
        elif capital_gp < 100000:
            tags.append('small-capital')
        elif capital_gp < 1000000:
            tags.append('medium-capital')
        elif capital_gp <= 25000000:  # Up to 25M is large-capital
            tags.append('large-capital')
        else:  # 50M+ is whale-capital
            tags.append('whale-capital')
        
        # Risk-based tags
        if 'safe' in query_lower or 'low risk' in query_lower or 'conservative' in query_lower:
            tags.append('low-risk')
        elif 'risky' in query_lower or 'high risk' in query_lower or 'aggressive' in query_lower:
            tags.append('high-risk')
        else:
            tags.append('medium-risk')
        
        # Liquidity tags
        if 'liquid' in query_lower or 'volume' in query_lower:
            tags.append('high-liquidity')
        
        # Special numeric queries (only for small capital amounts)
        if '10' in query_lower and ('items' in query_lower or 'cheap' in query_lower) and capital_gp <= 100000:
            tags.extend(['under-1k', '1k-5k', 'quick-flip'])
        
        return tags