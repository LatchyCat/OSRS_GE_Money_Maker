"""
Market Analysis Service for identifying merchant opportunities and price trends.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.db.models import Avg, Max, Min, Count, Q
from django.utils import timezone
from dataclasses import dataclass

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.prices.merchant_models import MarketTrend, MerchantOpportunity

logger = logging.getLogger(__name__)


@dataclass
class PricePattern:
    """Represents a detected price pattern."""
    pattern_type: str
    confidence: float
    description: str
    signals: List[str]
    timeframe: str


@dataclass
class OpportunitySignal:
    """Represents a trading signal for an item."""
    signal_type: str  # 'buy', 'sell', 'hold'
    strength: float   # 0.0 to 1.0
    reasoning: str
    target_price: int
    confidence: float


class MarketAnalysisService:
    """
    Service for analyzing market trends and identifying merchant opportunities.
    """
    
    def __init__(self):
        self.trend_periods = ['1h', '6h', '24h', '7d', '30d']
        
        # Pattern recognition thresholds
        self.volatility_threshold = 0.15  # 15%
        self.momentum_threshold = 0.1     # 10%
        self.volume_spike_threshold = 2.0  # 200% of average
        
        # Opportunity scoring weights
        self.scoring_weights = {
            'profit_potential': 0.25,
            'volume_feasibility': 0.20,
            'trend_strength': 0.15,
            'pattern_confidence': 0.15,
            'volatility_risk': -0.10,  # Negative weight (higher volatility = higher risk)
            'data_freshness': 0.15,
        }
    
    async def analyze_item_trends(self, item_id: int, periods: List[str] = None) -> List[MarketTrend]:
        """
        Analyze price trends for an item across different time periods.
        
        Args:
            item_id: Item to analyze
            periods: Time periods to analyze (defaults to all standard periods)
            
        Returns:
            List of MarketTrend objects
        """
        if periods is None:
            periods = self.trend_periods
        
        try:
            item = await Item.objects.aget(item_id=item_id)
        except Item.DoesNotExist:
            logger.error(f"Item {item_id} not found")
            return []
        
        trends = []
        
        for period in periods:
            trend = await self._analyze_period_trend(item, period)
            if trend:
                trends.append(trend)
        
        return trends
    
    async def _analyze_period_trend(self, item: Item, period: str) -> Optional[MarketTrend]:
        """Analyze trend for a specific time period."""
        
        # Calculate time range
        period_hours = self._get_period_hours(period)
        period_start = timezone.now() - timedelta(hours=period_hours)
        period_end = timezone.now()
        
        # Get price snapshots for the period
        snapshots = [
            snapshot async for snapshot in PriceSnapshot.objects.filter(
                item=item,
                created_at__gte=period_start,
                created_at__lte=period_end
            ).order_by('created_at')
        ]
        
        if len(snapshots) < 3:  # Need minimum data points
            return None
        
        # Calculate price statistics
        prices = [s.high_price for s in snapshots if s.high_price]
        volumes = [s.total_volume for s in snapshots if s.total_volume]
        
        if not prices:
            return None
        
        price_stats = {
            'min': min(prices),
            'max': max(prices),
            'avg': int(sum(prices) / len(prices)),
            'median': int(statistics.median(prices)),
            'current': prices[-1],
        }
        
        volume_stats = {
            'total': sum(volumes) if volumes else 0,
            'avg': int(sum(volumes) / len(volumes)) if volumes else 0,
            'current': volumes[-1] if volumes else 0,
        }
        
        # Calculate trend indicators
        trend_direction = self._calculate_trend_direction(prices)
        volatility_score = self._calculate_volatility(prices)
        momentum_score = self._calculate_momentum(prices)
        volume_momentum = self._calculate_volume_momentum(volumes) if volumes else 0.0
        
        # Detect support and resistance levels
        support_level, resistance_level = self._detect_support_resistance(prices)
        
        # Pattern recognition
        pattern_type, pattern_confidence = self._detect_price_patterns(snapshots)
        
        # Create or update trend record
        trend, created = await MarketTrend.objects.aupdate_or_create(
            item=item,
            period_type=period,
            period_start=period_start,
            defaults={
                'period_end': period_end,
                'price_min': price_stats['min'],
                'price_max': price_stats['max'],
                'price_avg': price_stats['avg'],
                'price_median': price_stats['median'],
                'price_current': price_stats['current'],
                'volume_total': volume_stats['total'],
                'volume_avg': volume_stats['avg'],
                'volume_current': volume_stats['current'],
                'trend_direction': trend_direction,
                'volatility_score': volatility_score,
                'momentum_score': momentum_score,
                'volume_momentum': volume_momentum,
                'support_level': support_level,
                'resistance_level': resistance_level,
                'pattern_type': pattern_type,
                'pattern_confidence': pattern_confidence,
            }
        )
        
        return trend
    
    async def identify_opportunities(self, 
                                   risk_levels: List[str] = None,
                                   min_profit: int = 100,
                                   max_results: int = 50) -> List[MerchantOpportunity]:
        """
        Identify merchant opportunities across all items.
        
        Args:
            risk_levels: Risk levels to consider (conservative, moderate, aggressive)
            min_profit: Minimum profit per item to consider
            max_results: Maximum opportunities to return
            
        Returns:
            List of MerchantOpportunity objects sorted by opportunity score
        """
        if risk_levels is None:
            risk_levels = ['conservative', 'moderate']
        
        opportunities = []
        
        # Get items with recent price data and minimum volume
        items = [
            item async for item in Item.objects.filter(
                is_active=True,
                profit_calc__current_profit__gte=min_profit,
                profit_calc__daily_volume__gte=10,  # Minimum volume for feasibility
            ).select_related('profit_calc')[:200]  # Limit to top 200 items for performance
        ]
        
        for item in items:
            item_opportunities = await self._analyze_item_opportunities(item, risk_levels)
            opportunities.extend(item_opportunities)
        
        # Sort by opportunity score
        opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        # Save top opportunities to database
        for opp in opportunities[:max_results]:
            await self._save_opportunity(opp)
        
        return opportunities[:max_results]
    
    async def _analyze_item_opportunities(self, item: Item, risk_levels: List[str]) -> List[MerchantOpportunity]:
        """Analyze opportunities for a specific item."""
        opportunities = []
        
        # Get recent trends
        trends = await self._get_recent_trends(item)
        if not trends:
            return opportunities
        
        # Get current market data
        profit_calc = item.profit_calc
        current_price = profit_calc.current_buy_price or 0
        
        if current_price == 0:
            return opportunities
        
        # Analyze different opportunity types
        for trend in trends:
            # Quick flip opportunities (based on volatility and volume)
            if trend.period_type in ['1h', '6h'] and trend.is_volatile:
                flip_opp = await self._create_flip_opportunity(item, trend, risk_levels)
                if flip_opp:
                    opportunities.append(flip_opp)
            
            # Swing trade opportunities (based on trend and patterns)
            if trend.period_type in ['24h', '7d'] and trend.is_trending:
                swing_opp = await self._create_swing_opportunity(item, trend, risk_levels)
                if swing_opp:
                    opportunities.append(swing_opp)
            
            # Pattern-based opportunities
            if trend.pattern_confidence > 0.6:
                pattern_opp = await self._create_pattern_opportunity(item, trend, risk_levels)
                if pattern_opp:
                    opportunities.append(pattern_opp)
        
        return opportunities
    
    async def _create_flip_opportunity(self, item: Item, trend: MarketTrend, risk_levels: List[str]) -> Optional[MerchantOpportunity]:
        """Create a quick flip opportunity."""
        
        # Calculate flip targets based on volatility
        current_price = trend.price_current
        price_range = trend.price_max - trend.price_min
        volatility_range = int(price_range * 0.3)  # Use 30% of price range
        
        target_buy_price = max(trend.price_min, current_price - volatility_range)
        target_sell_price = min(trend.price_max, current_price + volatility_range)
        
        projected_profit = target_sell_price - target_buy_price
        
        if projected_profit < 100:  # Minimum 100 GP profit
            return None
        
        # Risk assessment
        risk_score = min(1.0, trend.volatility_score * 2)  # Higher volatility = higher risk
        risk_level = self._determine_risk_level(risk_score, risk_levels)
        
        if not risk_level:
            return None
        
        # Calculate opportunity score
        opportunity_score = await self._calculate_opportunity_score(
            item, trend, projected_profit, risk_score, 'flip_quick'
        )
        
        return MerchantOpportunity(
            item=item,
            opportunity_type='flip_quick',
            risk_level=risk_level,
            current_price=current_price,
            target_buy_price=target_buy_price,
            target_sell_price=target_sell_price,
            projected_profit_per_item=projected_profit,
            projected_profit_margin_pct=(projected_profit / target_buy_price) * 100,
            estimated_trade_volume=min(trend.volume_current or 10, 100),
            total_projected_profit=projected_profit * min(trend.volume_current or 10, 100),
            risk_score=risk_score,
            confidence_score=min(1.0, trend.pattern_confidence + 0.3),
            success_probability=max(0.3, 0.8 - risk_score * 0.3),
            opportunity_score=opportunity_score,
            time_sensitivity='urgent',
            based_on_trend=trend,
            reasoning=f"Quick flip opportunity based on high volatility ({trend.volatility_score:.1%}). "
                     f"Target {projected_profit}GP profit per item with {trend.volume_current} volume."
        )
    
    async def _create_swing_opportunity(self, item: Item, trend: MarketTrend, risk_levels: List[str]) -> Optional[MerchantOpportunity]:
        """Create a swing trade opportunity."""
        
        current_price = trend.price_current
        
        # Determine buy/sell targets based on trend direction
        if trend.trend_direction in ['strong_up', 'weak_up']:
            # Uptrend - buy on pullbacks, sell near resistance
            target_buy_price = int(current_price * 0.95)  # 5% pullback
            target_sell_price = trend.resistance_level or int(current_price * 1.15)
        elif trend.trend_direction in ['strong_down', 'weak_down']:
            # Downtrend - short opportunity (buy back lower)
            target_buy_price = int(current_price * 1.05)  # Buy higher to short
            target_sell_price = trend.support_level or int(current_price * 0.85)
        else:
            # Sideways - range trading
            target_buy_price = trend.support_level or int(current_price * 0.95)
            target_sell_price = trend.resistance_level or int(current_price * 1.05)
        
        projected_profit = abs(target_sell_price - target_buy_price)
        
        if projected_profit < 200:  # Minimum 200 GP for swing trades
            return None
        
        # Risk assessment based on trend strength
        risk_score = 0.4 if trend.trend_direction in ['strong_up', 'strong_down'] else 0.6
        risk_level = self._determine_risk_level(risk_score, risk_levels)
        
        if not risk_level:
            return None
        
        opportunity_score = await self._calculate_opportunity_score(
            item, trend, projected_profit, risk_score, 'swing_short'
        )
        
        return MerchantOpportunity(
            item=item,
            opportunity_type='swing_short',
            risk_level=risk_level,
            current_price=current_price,
            target_buy_price=target_buy_price,
            target_sell_price=target_sell_price,
            projected_profit_per_item=projected_profit,
            projected_profit_margin_pct=(projected_profit / min(target_buy_price, target_sell_price)) * 100,
            estimated_trade_volume=min(trend.volume_avg or 50, 200),
            total_projected_profit=projected_profit * min(trend.volume_avg or 50, 200),
            risk_score=risk_score,
            confidence_score=trend.pattern_confidence,
            success_probability=0.6 if trend.is_trending else 0.4,
            opportunity_score=opportunity_score,
            time_sensitivity='moderate',
            based_on_trend=trend,
            reasoning=f"Swing trade based on {trend.trend_direction} trend. "
                     f"Pattern: {trend.pattern_type} with {trend.pattern_confidence:.1%} confidence."
        )
    
    def _get_period_hours(self, period: str) -> int:
        """Convert period string to hours."""
        period_map = {
            '1h': 1,
            '6h': 6,
            '24h': 24,
            '7d': 168,  # 7 * 24
            '30d': 720,  # 30 * 24
        }
        return period_map.get(period, 24)
    
    def _calculate_trend_direction(self, prices: List[int]) -> str:
        """Determine trend direction from price series."""
        if len(prices) < 3:
            return 'sideways'
        
        # Calculate linear regression slope
        n = len(prices)
        x_values = list(range(n))
        
        # Simple linear regression
        x_mean = sum(x_values) / n
        y_mean = sum(prices) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, prices))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 'sideways'
        
        slope = numerator / denominator
        slope_pct = (slope / y_mean) * 100  # Percentage slope
        
        if slope_pct > 2:
            return 'strong_up'
        elif slope_pct > 0.5:
            return 'weak_up'
        elif slope_pct < -2:
            return 'strong_down'
        elif slope_pct < -0.5:
            return 'weak_down'
        else:
            return 'sideways'
    
    def _calculate_volatility(self, prices: List[int]) -> float:
        """Calculate price volatility as coefficient of variation."""
        if len(prices) < 2:
            return 0.0
        
        mean_price = sum(prices) / len(prices)
        variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5
        
        return std_dev / mean_price if mean_price > 0 else 0.0
    
    def _calculate_momentum(self, prices: List[int]) -> float:
        """Calculate price momentum (-1 to 1)."""
        if len(prices) < 2:
            return 0.0
        
        # Simple momentum: (current - start) / start
        start_price = prices[0]
        current_price = prices[-1]
        
        if start_price == 0:
            return 0.0
        
        momentum = (current_price - start_price) / start_price
        return max(-1.0, min(1.0, momentum))  # Clamp to [-1, 1]
    
    def _calculate_volume_momentum(self, volumes: List[int]) -> float:
        """Calculate volume momentum."""
        if len(volumes) < 2:
            return 0.0
        
        recent_avg = sum(volumes[-3:]) / len(volumes[-3:])
        older_avg = sum(volumes[:-3]) / len(volumes[:-3]) if len(volumes) > 3 else sum(volumes) / len(volumes)
        
        if older_avg == 0:
            return 0.0
        
        volume_momentum = (recent_avg - older_avg) / older_avg
        return max(-1.0, min(1.0, volume_momentum))
    
    def _detect_support_resistance(self, prices: List[int]) -> Tuple[Optional[int], Optional[int]]:
        """Detect support and resistance levels."""
        if len(prices) < 5:
            return None, None
        
        # Simple approach: use price quantiles
        sorted_prices = sorted(prices)
        support_level = sorted_prices[len(sorted_prices) // 4]  # 25th percentile
        resistance_level = sorted_prices[3 * len(sorted_prices) // 4]  # 75th percentile
        
        return support_level, resistance_level
    
    def _detect_price_patterns(self, snapshots: List[PriceSnapshot]) -> Tuple[str, float]:
        """Detect price patterns and return type and confidence."""
        if len(snapshots) < 5:
            return 'unknown', 0.0
        
        prices = [s.high_price for s in snapshots if s.high_price]
        volumes = [s.total_volume for s in snapshots if s.total_volume]
        
        if len(prices) < 5:
            return 'unknown', 0.0
        
        # Simple pattern detection
        recent_prices = prices[-5:]
        
        # Breakout detection
        price_range = max(prices) - min(prices)
        recent_high = max(recent_prices)
        recent_low = min(recent_prices)
        
        if recent_high > max(prices[:-2]) and recent_high - recent_low > price_range * 0.1:
            return 'breakout_up', 0.7
        
        if recent_low < min(prices[:-2]) and recent_high - recent_low > price_range * 0.1:
            return 'breakout_down', 0.7
        
        # Range bound detection
        if price_range < sum(prices) / len(prices) * 0.1:  # Range < 10% of average
            return 'range_bound', 0.6
        
        return 'unknown', 0.3
    
    async def _get_recent_trends(self, item: Item) -> List[MarketTrend]:
        """Get recent trend analysis for an item."""
        return [
            trend async for trend in MarketTrend.objects.filter(
                item=item,
                calculated_at__gte=timezone.now() - timedelta(hours=24)
            ).order_by('-calculated_at')[:5]
        ]
    
    def _determine_risk_level(self, risk_score: float, allowed_levels: List[str]) -> Optional[str]:
        """Determine risk level based on risk score and user preferences."""
        if risk_score <= 0.3 and 'conservative' in allowed_levels:
            return 'conservative'
        elif risk_score <= 0.6 and 'moderate' in allowed_levels:
            return 'moderate'
        elif risk_score <= 0.8 and 'aggressive' in allowed_levels:
            return 'aggressive'
        elif 'speculative' in allowed_levels:
            return 'speculative'
        
        return None
    
    async def _calculate_opportunity_score(self, item: Item, trend: MarketTrend, 
                                         projected_profit: int, risk_score: float,
                                         opportunity_type: str) -> int:
        """Calculate overall opportunity score (0-100)."""
        
        # Base score components
        profit_score = min(100, projected_profit / 10)  # 10 GP = 1 point, max 100
        volume_score = min(100, (trend.volume_current or 0) / 10)  # 10 volume = 1 point
        trend_score = 50 + (trend.momentum_score * 50)  # -1 to 1 momentum -> 0 to 100
        pattern_score = trend.pattern_confidence * 100
        volatility_penalty = trend.volatility_score * 100  # Higher volatility = penalty
        
        # Data freshness (newer data = higher score)
        hours_old = (timezone.now() - trend.calculated_at).total_seconds() / 3600
        freshness_score = max(0, 100 - (hours_old * 5))  # Lose 5 points per hour
        
        # Weighted average
        score = (
            profit_score * self.scoring_weights['profit_potential'] +
            volume_score * self.scoring_weights['volume_feasibility'] +
            trend_score * self.scoring_weights['trend_strength'] +
            pattern_score * self.scoring_weights['pattern_confidence'] +
            volatility_penalty * self.scoring_weights['volatility_risk'] +  # This is negative
            freshness_score * self.scoring_weights['data_freshness']
        )
        
        return max(0, min(100, int(score)))
    
    async def _save_opportunity(self, opportunity: MerchantOpportunity) -> MerchantOpportunity:
        """Save opportunity to database, avoiding duplicates."""
        
        # Check for existing similar opportunity
        existing = await MerchantOpportunity.objects.filter(
            item=opportunity.item,
            opportunity_type=opportunity.opportunity_type,
            status='active',
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).afirst()
        
        if existing:
            # Update existing opportunity if new one has better score
            if opportunity.opportunity_score > existing.opportunity_score:
                for field, value in opportunity.__dict__.items():
                    if not field.startswith('_') and field != 'id':
                        setattr(existing, field, value)
                existing.updated_at = timezone.now()
                await existing.asave()
                return existing
            else:
                return existing
        
        # Save new opportunity
        await opportunity.asave()
        return opportunity