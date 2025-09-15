"""
Bidirectional Set Trading Analyzer

This service implements advanced algorithms to determine whether it's more profitable to:
1. Combine individual pieces into sets (Arbitrage Strategy A)
2. Decombine complete sets into individual pieces (Arbitrage Strategy B)

Uses historical data, market conditions, and ML predictions.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from django.db import models
from apps.items.models import Item
from apps.prices.models import PriceSnapshot, HistoricalPricePoint
from services.unified_data_ingestion_service import UnifiedDataIngestionService

logger = logging.getLogger(__name__)


@dataclass
class MarketCondition:
    """Current market condition analysis."""
    volatility_level: str  # 'low', 'medium', 'high', 'extreme'
    trend: str  # 'bullish', 'bearish', 'sideways'
    volume_trend: str  # 'increasing', 'decreasing', 'stable'
    confidence: float  # 0.0 - 1.0
    
    @property
    def is_favorable_for_trading(self) -> bool:
        """Check if conditions favor active trading strategies."""
        return (
            self.volatility_level in ['low', 'medium'] and
            self.volume_trend in ['stable', 'increasing'] and
            self.confidence > 0.6
        )


@dataclass  
class TradingOpportunity:
    """Represents a specific trading opportunity (combine or decombine)."""
    strategy_type: str  # 'combine' or 'decombine'
    set_name: str
    set_item_id: Optional[int]
    component_ids: List[int]
    
    # Financial metrics
    expected_profit: float
    profit_margin_pct: float
    capital_required: float
    
    # Risk metrics  
    risk_score: float  # 0.0 - 1.0 (lower is better)
    confidence_score: float  # 0.0 - 1.0 (higher is better)
    volatility_score: float  # Price volatility measure
    
    # Market metrics
    volume_score: float  # Trading volume strength
    liquidity_score: float  # How easy to execute
    
    # Time-based analysis
    optimal_entry_time: Optional[datetime] = None
    expected_duration_hours: float = 1.0
    price_momentum: str = 'neutral'  # 'positive', 'negative', 'neutral'
    
    # Historical performance
    historical_success_rate: Optional[float] = None
    avg_historical_profit: Optional[float] = None
    
    @property
    def overall_score(self) -> float:
        """Calculate overall opportunity score (0-100)."""
        # Weight different factors
        profit_weight = 0.3
        risk_weight = 0.2  
        confidence_weight = 0.2
        volume_weight = 0.15
        liquidity_weight = 0.15
        
        # Normalize profit margin (cap at 50% for scoring)
        profit_score = min(1.0, self.profit_margin_pct / 50)
        
        # Risk is inversely scored (lower risk = higher score)
        risk_score = 1.0 - self.risk_score
        
        weighted_score = (
            profit_score * profit_weight +
            risk_score * risk_weight +
            self.confidence_score * confidence_weight +
            self.volume_score * volume_weight +
            self.liquidity_score * liquidity_weight
        )
        
        return weighted_score * 100
    
    @property
    def risk_level(self) -> str:
        """Get human-readable risk level."""
        if self.risk_score < 0.3:
            return 'low'
        elif self.risk_score < 0.6:
            return 'medium'  
        else:
            return 'high'


class BidirectionalAnalyzer:
    """
    Advanced analyzer for bidirectional set trading opportunities.
    """
    
    def __init__(self):
        self.ingestion_service = None
        
        # Analysis parameters
        self.min_profit_threshold = 1000  # Minimum profit in GP
        self.min_volume_threshold = 10   # Minimum daily volume
        self.max_volatility_threshold = 0.5  # Maximum acceptable volatility
        
        # Historical analysis periods
        self.short_term_days = 7
        self.medium_term_days = 30
        self.long_term_days = 90
        
        # Machine learning parameters
        self.confidence_threshold = 0.6
        self.ml_feature_weights = {
            'price_trend': 0.25,
            'volume_trend': 0.20,
            'volatility': 0.15,
            'market_sentiment': 0.15,
            'seasonal_patterns': 0.15,
            'correlation_strength': 0.10
        }
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.ingestion_service = UnifiedDataIngestionService()
        await self.ingestion_service.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.ingestion_service:
            await self.ingestion_service.__aexit__(exc_type, exc_val, exc_tb)
    
    async def analyze_set_opportunities(self,
                                      set_name: str,
                                      set_item_id: Optional[int],
                                      component_ids: List[int],
                                      include_historical: bool = True) -> List[TradingOpportunity]:
        """
        Analyze both combine and decombine opportunities for a set.
        
        Args:
            set_name: Name of the armor/weapon set
            set_item_id: Item ID of complete set (if exists)
            component_ids: List of component item IDs
            include_historical: Whether to include historical analysis
            
        Returns:
            List of viable trading opportunities (combine and/or decombine)
        """
        logger.info(f"⚡ Analyzing bidirectional opportunities for {set_name}")
        
        opportunities = []
        
        try:
            # Get current market data
            market_data = await self._get_market_data(set_item_id, component_ids)
            
            # Debug logging
            logger.info(f"Market data for {set_name}: {market_data}")
            if 'set_price' in market_data:
                set_price = market_data['set_price']
                logger.info(f"Set prices - Buy: {set_price['buy_price']}, Sell: {set_price['sell_price']}")
            if 'components' in market_data and market_data['components']:
                total_buy = market_data.get('total_component_buy_cost', 0)
                total_sell = market_data.get('total_component_sell_value', 0) 
                logger.info(f"Component totals - Buy: {total_buy}, Sell: {total_sell}")
                logger.info(f"Combine profit potential: {market_data.get('set_price', {}).get('sell_price', 0) - total_buy}")
                logger.info(f"Decombine profit potential: {total_sell - market_data.get('set_price', {}).get('buy_price', 0)}")
            else:
                logger.info(f"No component data for {set_name}")
            
            if not market_data:
                logger.warning(f"No market data available for {set_name}")
                return opportunities
            
            # Analyze market conditions
            market_condition = await self._analyze_market_conditions(
                set_item_id, component_ids, include_historical
            )
            
            # Strategy 1: Combine Analysis (buy components, sell set)
            if set_item_id and market_data.get('set_price'):
                combine_opportunity = await self._analyze_combine_strategy(
                    set_name, set_item_id, component_ids, market_data, market_condition
                )
                if combine_opportunity:
                    logger.info(f"Combine opportunity created: profit={combine_opportunity.expected_profit}, threshold={self.min_profit_threshold}")
                    if combine_opportunity.expected_profit > self.min_profit_threshold:
                        opportunities.append(combine_opportunity)
                        logger.info(f"✅ Combine opportunity added to list")
                    else:
                        logger.info(f"❌ Combine opportunity rejected: profit too low")
            
            # Strategy 2: Decombine Analysis (buy set, sell components)
            if set_item_id and market_data.get('set_price'):
                decombine_opportunity = await self._analyze_decombine_strategy(
                    set_name, set_item_id, component_ids, market_data, market_condition
                )
                if decombine_opportunity:
                    logger.info(f"Decombine opportunity created: profit={decombine_opportunity.expected_profit}, threshold={self.min_profit_threshold}")
                    if decombine_opportunity.expected_profit > self.min_profit_threshold:
                        opportunities.append(decombine_opportunity)
                        logger.info(f"✅ Decombine opportunity added to list")
                    else:
                        logger.info(f"❌ Decombine opportunity rejected: profit too low")
            
            # Apply advanced filtering and ranking
            filtered_opportunities = await self._filter_and_rank_opportunities(
                opportunities, market_condition
            )
            
            logger.info(f"Found {len(filtered_opportunities)} viable opportunities for {set_name}")
            return filtered_opportunities
            
        except Exception as e:
            logger.error(f"Analysis failed for {set_name}: {e}")
            return opportunities
    
    async def _get_market_data(self, 
                             set_item_id: Optional[int], 
                             component_ids: List[int]) -> Dict[str, Any]:
        """Get comprehensive market data for set and components."""
        market_data = {}
        
        try:
            # Get set price data
            if set_item_id:
                set_price_data = await asyncio.to_thread(
                    self._get_latest_price_data, set_item_id
                )
                if set_price_data:
                    market_data['set_price'] = {
                        'buy_price': set_price_data.high_price or 0,
                        'sell_price': set_price_data.low_price or 0,
                        'volume_buy': set_price_data.high_price_volume or 0,
                        'volume_sell': set_price_data.low_price_volume or 0,
                        'timestamp': set_price_data.created_at
                    }
            
            # Get component price data
            component_data = []
            for comp_id in component_ids:
                comp_price_data = await asyncio.to_thread(
                    self._get_latest_price_data, comp_id
                )
                if comp_price_data:
                    component_data.append({
                        'item_id': comp_id,
                        'buy_price': comp_price_data.high_price or 0,
                        'sell_price': comp_price_data.low_price or 0,
                        'volume_buy': comp_price_data.high_price_volume or 0,
                        'volume_sell': comp_price_data.low_price_volume or 0,
                        'timestamp': comp_price_data.created_at
                    })
            
            market_data['components'] = component_data
            
            # Calculate aggregate component metrics
            if component_data:
                # Handle None values in price calculations
                buy_prices = [comp['buy_price'] for comp in component_data if comp['buy_price'] is not None]
                sell_prices = [comp['sell_price'] for comp in component_data if comp['sell_price'] is not None]
                buy_volumes = [comp['volume_buy'] for comp in component_data if comp['volume_buy'] is not None]
                
                market_data['total_component_buy_cost'] = sum(buy_prices) if buy_prices else 0
                market_data['total_component_sell_value'] = sum(sell_prices) if sell_prices else 0
                market_data['min_component_volume'] = min(buy_volumes) if buy_volumes else 0
                
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return {}
    
    def _get_latest_price_data(self, item_id: int) -> Optional[PriceSnapshot]:
        """Get latest price snapshot for an item."""
        try:
            return PriceSnapshot.objects.filter(
                item__item_id=item_id
            ).order_by('-created_at').first()
        except Exception:
            return None
    
    async def _analyze_market_conditions(self,
                                       set_item_id: Optional[int],
                                       component_ids: List[int],
                                       include_historical: bool) -> MarketCondition:
        """Analyze current market conditions affecting trading success."""
        
        # Default to neutral conditions if analysis fails
        default_condition = MarketCondition(
            volatility_level='medium',
            trend='sideways',
            volume_trend='stable',
            confidence=0.5
        )
        
        if not include_historical:
            return default_condition
        
        try:
            # Analyze volatility from recent price movements
            volatility_scores = []
            all_item_ids = ([set_item_id] if set_item_id else []) + component_ids
            
            for item_id in all_item_ids:
                volatility = await asyncio.to_thread(
                    self._calculate_item_volatility, item_id, days=7
                )
                if volatility is not None:
                    volatility_scores.append(volatility)
            
            # Determine overall volatility level
            avg_volatility = np.mean(volatility_scores) if volatility_scores else 0.5
            
            if avg_volatility < 0.1:
                volatility_level = 'low'
            elif avg_volatility < 0.3:
                volatility_level = 'medium'
            elif avg_volatility < 0.6:
                volatility_level = 'high'
            else:
                volatility_level = 'extreme'
            
            # Analyze price trends
            trend = await self._analyze_price_trends(all_item_ids)
            
            # Analyze volume trends  
            volume_trend = await self._analyze_volume_trends(all_item_ids)
            
            # Calculate confidence based on data quality
            confidence = min(1.0, len(volatility_scores) / len(all_item_ids))
            
            return MarketCondition(
                volatility_level=volatility_level,
                trend=trend,
                volume_trend=volume_trend,
                confidence=confidence
            )
            
        except Exception as e:
            logger.warning(f"Market condition analysis failed: {e}")
            return default_condition
    
    def _calculate_item_volatility(self, item_id: int, days: int = 7) -> Optional[float]:
        """Calculate price volatility for an item over specified period."""
        try:
            # Get recent historical data
            cutoff_date = timezone.now() - timedelta(days=days)
            historical_points = HistoricalPricePoint.objects.filter(
                item__item_id=item_id,
                timestamp__gte=cutoff_date
            ).order_by('timestamp')
            
            if historical_points.count() < 3:
                return None
            
            # Extract prices
            prices = []
            for point in historical_points:
                avg_price = (point.avg_high_price + point.avg_low_price) / 2
                if avg_price > 0:
                    prices.append(avg_price)
            
            if len(prices) < 3:
                return None
            
            # Calculate coefficient of variation
            mean_price = np.mean(prices)
            std_price = np.std(prices)
            
            return std_price / mean_price if mean_price > 0 else None
            
        except Exception:
            return None
    
    async def _analyze_price_trends(self, item_ids: List[int]) -> str:
        """Analyze overall price trend across items."""
        try:
            trend_scores = []
            
            for item_id in item_ids:
                trend_score = await asyncio.to_thread(
                    self._calculate_price_trend_score, item_id
                )
                if trend_score is not None:
                    trend_scores.append(trend_score)
            
            if not trend_scores:
                return 'sideways'
            
            avg_trend = np.mean(trend_scores)
            
            if avg_trend > 0.1:
                return 'bullish'
            elif avg_trend < -0.1:
                return 'bearish'
            else:
                return 'sideways'
                
        except Exception:
            return 'sideways'
    
    def _calculate_price_trend_score(self, item_id: int) -> Optional[float]:
        """Calculate trend score for an item (-1 bearish, +1 bullish)."""
        try:
            # Get recent vs older prices
            recent_cutoff = timezone.now() - timedelta(days=3)
            older_cutoff = timezone.now() - timedelta(days=10)
            
            recent_prices = HistoricalPricePoint.objects.filter(
                item__item_id=item_id,
                timestamp__gte=recent_cutoff
            ).values_list('avg_high_price', 'avg_low_price')
            
            older_prices = HistoricalPricePoint.objects.filter(
                item__item_id=item_id,
                timestamp__gte=older_cutoff,
                timestamp__lt=recent_cutoff
            ).values_list('avg_high_price', 'avg_low_price')
            
            if not recent_prices or not older_prices:
                return None
            
            # Calculate average prices
            recent_avg = np.mean([np.mean([high, low]) for high, low in recent_prices])
            older_avg = np.mean([np.mean([high, low]) for high, low in older_prices])
            
            # Return normalized trend score
            if older_avg > 0:
                return (recent_avg - older_avg) / older_avg
            else:
                return None
                
        except Exception:
            return None
    
    async def _analyze_volume_trends(self, item_ids: List[int]) -> str:
        """Analyze volume trends across items."""
        try:
            volume_trends = []
            
            for item_id in item_ids:
                volume_trend = await asyncio.to_thread(
                    self._calculate_volume_trend, item_id
                )
                if volume_trend is not None:
                    volume_trends.append(volume_trend)
            
            if not volume_trends:
                return 'stable'
            
            avg_volume_trend = np.mean(volume_trends)
            
            if avg_volume_trend > 0.2:
                return 'increasing'
            elif avg_volume_trend < -0.2:
                return 'decreasing'
            else:
                return 'stable'
                
        except Exception:
            return 'stable'
    
    def _calculate_volume_trend(self, item_id: int) -> Optional[float]:
        """Calculate volume trend for an item."""
        try:
            # Compare recent vs historical volume
            recent_volume = PriceSnapshot.objects.filter(
                item__item_id=item_id,
                created_at__gte=timezone.now() - timedelta(days=3)
            ).aggregate(
                avg_volume=models.Avg('total_volume')
            )['avg_volume']
            
            historical_volume = PriceSnapshot.objects.filter(
                item__item_id=item_id,
                created_at__gte=timezone.now() - timedelta(days=10),
                created_at__lt=timezone.now() - timedelta(days=3)
            ).aggregate(
                avg_volume=models.Avg('total_volume')
            )['avg_volume']
            
            if recent_volume and historical_volume and historical_volume > 0:
                return (recent_volume - historical_volume) / historical_volume
            else:
                return None
                
        except Exception:
            return None
    
    async def _analyze_combine_strategy(self,
                                      set_name: str,
                                      set_item_id: int,
                                      component_ids: List[int],
                                      market_data: Dict[str, Any],
                                      market_condition: MarketCondition) -> Optional[TradingOpportunity]:
        """Analyze profitability of combining components into set."""
        
        try:
            set_price_data = market_data.get('set_price', {})
            components_data = market_data.get('components', [])
            
            if not set_price_data or not components_data:
                return None
            
            # Calculate costs and revenues
            total_component_cost = market_data.get('total_component_buy_cost', 0)
            set_sell_price = set_price_data.get('sell_price', 0)
            
            # Include GE tax (1% on selling)
            ge_tax = set_sell_price * 0.01
            net_revenue = set_sell_price - ge_tax
            
            # Calculate profit
            expected_profit = net_revenue - total_component_cost
            
            # Debug logging
            logger.info(f"Combine analysis for {set_name}:")
            logger.info(f"  Component cost: {total_component_cost}")
            logger.info(f"  Set sell price: {set_sell_price}")
            logger.info(f"  GE tax (1%): {ge_tax}")
            logger.info(f"  Net revenue: {net_revenue}")
            logger.info(f"  Expected profit: {expected_profit}")
            
            if expected_profit <= 0:
                logger.info(f"  ❌ Not profitable - profit: {expected_profit}")
                return None
            else:
                logger.info(f"  ✅ Profitable - profit: {expected_profit}")
            
            profit_margin_pct = (expected_profit / total_component_cost * 100) if total_component_cost > 0 else 0
            
            # Calculate risk metrics
            risk_score = await self._calculate_risk_score(
                'combine', market_data, market_condition
            )
            
            # Calculate confidence based on market conditions and data quality
            confidence_score = await self._calculate_confidence_score(
                market_data, market_condition, 'combine'
            )
            
            # Calculate volume and liquidity scores
            volume_score = min(1.0, (market_data.get('min_component_volume', 0) + 
                                   set_price_data.get('volume_sell', 0)) / 200)
            
            liquidity_score = await self._calculate_liquidity_score(
                set_item_id, component_ids, 'combine'
            )
            
            # Volatility score from market conditions
            volatility_mapping = {'low': 0.1, 'medium': 0.3, 'high': 0.6, 'extreme': 1.0}
            volatility_score = volatility_mapping.get(market_condition.volatility_level, 0.5)
            
            return TradingOpportunity(
                strategy_type='combine',
                set_name=set_name,
                set_item_id=set_item_id,
                component_ids=component_ids,
                expected_profit=expected_profit,
                profit_margin_pct=profit_margin_pct,
                capital_required=total_component_cost,
                risk_score=risk_score,
                confidence_score=confidence_score,
                volatility_score=volatility_score,
                volume_score=volume_score,
                liquidity_score=liquidity_score,
                expected_duration_hours=2.0,  # Estimate for buying components and selling set
                price_momentum=market_condition.trend
            )
            
        except Exception as e:
            logger.error(f"Combine analysis failed for {set_name}: {e}")
            return None
    
    async def _analyze_decombine_strategy(self,
                                        set_name: str,
                                        set_item_id: int,
                                        component_ids: List[int],
                                        market_data: Dict[str, Any],
                                        market_condition: MarketCondition) -> Optional[TradingOpportunity]:
        """Analyze profitability of decombining set into components."""
        
        try:
            set_price_data = market_data.get('set_price', {})
            components_data = market_data.get('components', [])
            
            if not set_price_data or not components_data:
                return None
            
            # Calculate costs and revenues
            set_buy_cost = set_price_data.get('buy_price', 0)
            total_component_sell_value = market_data.get('total_component_sell_value', 0)
            
            # Include GE tax (1% on selling each component)
            component_ge_tax = total_component_sell_value * 0.01
            net_component_revenue = total_component_sell_value - component_ge_tax
            
            # Calculate profit
            expected_profit = net_component_revenue - set_buy_cost
            
            if expected_profit <= 0:
                return None
            
            profit_margin_pct = (expected_profit / set_buy_cost * 100) if set_buy_cost > 0 else 0
            
            # Calculate risk metrics
            risk_score = await self._calculate_risk_score(
                'decombine', market_data, market_condition
            )
            
            # Calculate confidence
            confidence_score = await self._calculate_confidence_score(
                market_data, market_condition, 'decombine'
            )
            
            # Volume score (limited by lowest component volume)
            component_volumes = [comp.get('volume_sell', 0) for comp in components_data]
            min_volume = min(component_volumes) if component_volumes else 0
            volume_score = min(1.0, (min_volume + set_price_data.get('volume_buy', 0)) / 200)
            
            # Liquidity score
            liquidity_score = await self._calculate_liquidity_score(
                set_item_id, component_ids, 'decombine'
            )
            
            # Volatility score
            volatility_mapping = {'low': 0.1, 'medium': 0.3, 'high': 0.6, 'extreme': 1.0}
            volatility_score = volatility_mapping.get(market_condition.volatility_level, 0.5)
            
            return TradingOpportunity(
                strategy_type='decombine',
                set_name=set_name,
                set_item_id=set_item_id,
                component_ids=component_ids,
                expected_profit=expected_profit,
                profit_margin_pct=profit_margin_pct,
                capital_required=set_buy_cost,
                risk_score=risk_score,
                confidence_score=confidence_score,
                volatility_score=volatility_score,
                volume_score=volume_score,
                liquidity_score=liquidity_score,
                expected_duration_hours=1.5,  # Estimate for buying set and selling components
                price_momentum=market_condition.trend
            )
            
        except Exception as e:
            logger.error(f"Decombine analysis failed for {set_name}: {e}")
            return None
    
    async def _calculate_risk_score(self, 
                                  strategy_type: str,
                                  market_data: Dict[str, Any],
                                  market_condition: MarketCondition) -> float:
        """Calculate risk score for a trading strategy (0.0 = low risk, 1.0 = high risk)."""
        
        risk_factors = []
        
        # Market volatility risk
        volatility_risk = {
            'low': 0.1, 'medium': 0.3, 'high': 0.7, 'extreme': 1.0
        }.get(market_condition.volatility_level, 0.5)
        risk_factors.append(volatility_risk)
        
        # Volume risk (low volume = high risk)
        if strategy_type == 'combine':
            min_volume = market_data.get('min_component_volume', 0)
        else:
            set_volume = market_data.get('set_price', {}).get('volume_buy', 0)
            component_volumes = [comp.get('volume_sell', 0) for comp in market_data.get('components', [])]
            min_volume = min([set_volume] + component_volumes) if component_volumes else set_volume
        
        volume_risk = max(0.0, 1.0 - min_volume / 100)  # Normalize to 0-1
        risk_factors.append(volume_risk)
        
        # Market condition risk
        if not market_condition.is_favorable_for_trading:
            risk_factors.append(0.4)  # Additional risk for unfavorable conditions
        
        # Calculate weighted average risk
        return np.mean(risk_factors)
    
    async def _calculate_confidence_score(self,
                                        market_data: Dict[str, Any],
                                        market_condition: MarketCondition,
                                        strategy_type: str) -> float:
        """Calculate confidence score for trading opportunity (0.0 = low confidence, 1.0 = high confidence)."""
        
        confidence_factors = []
        
        # Market condition confidence
        confidence_factors.append(market_condition.confidence)
        
        # Data completeness confidence
        if market_data.get('set_price') and market_data.get('components'):
            data_completeness = len(market_data['components']) / max(1, len(market_data.get('component_ids', [])))
            confidence_factors.append(data_completeness)
        else:
            confidence_factors.append(0.0)
        
        # Price data freshness (fresher data = higher confidence)
        timestamps = []
        if market_data.get('set_price', {}).get('timestamp'):
            timestamps.append(market_data['set_price']['timestamp'])
        
        for comp in market_data.get('components', []):
            if comp.get('timestamp'):
                timestamps.append(comp['timestamp'])
        
        if timestamps:
            # Calculate average age in hours
            now = timezone.now()
            avg_age_hours = np.mean([(now - ts).total_seconds() / 3600 for ts in timestamps])
            freshness_score = max(0.0, 1.0 - avg_age_hours / 24)  # Penalty for data older than 24h
            confidence_factors.append(freshness_score)
        
        return np.mean(confidence_factors) if confidence_factors else 0.0
    
    async def _calculate_liquidity_score(self,
                                       set_item_id: int,
                                       component_ids: List[int],
                                       strategy_type: str) -> float:
        """Calculate liquidity score based on historical trading activity."""
        
        try:
            # Get recent trading volume data
            cutoff_date = timezone.now() - timedelta(days=7)
            
            volume_scores = []
            all_item_ids = [set_item_id] + component_ids
            
            for item_id in all_item_ids:
                recent_volume = await asyncio.to_thread(
                    self._get_recent_volume, item_id, cutoff_date
                )
                if recent_volume is not None:
                    # Normalize volume (higher volume = higher liquidity)
                    volume_score = min(1.0, recent_volume / 1000)  # Cap at 1000 volume units
                    volume_scores.append(volume_score)
            
            return np.mean(volume_scores) if volume_scores else 0.5
            
        except Exception:
            return 0.5  # Default moderate liquidity
    
    def _get_recent_volume(self, item_id: int, cutoff_date: datetime) -> Optional[float]:
        """Get recent trading volume for an item."""
        try:
            from django.db import models
            
            volume_data = PriceSnapshot.objects.filter(
                item__item_id=item_id,
                created_at__gte=cutoff_date
            ).aggregate(
                avg_volume=models.Avg('total_volume'),
                count=models.Count('id')
            )
            
            if volume_data['avg_volume'] and volume_data['count'] > 0:
                return float(volume_data['avg_volume'])
            else:
                return None
                
        except Exception:
            return None
    
    async def _filter_and_rank_opportunities(self,
                                           opportunities: List[TradingOpportunity],
                                           market_condition: MarketCondition) -> List[TradingOpportunity]:
        """Filter and rank opportunities based on advanced criteria."""
        
        if not opportunities:
            return opportunities
        
        filtered_opportunities = []
        
        for opp in opportunities:
            logger.info(f"Filtering opportunity: {opp.set_name} ({opp.strategy_type})")
            logger.info(f"  Profit: {opp.expected_profit} (min: {self.min_profit_threshold})")
            logger.info(f"  Risk score: {opp.risk_score} (max: 0.8)")
            logger.info(f"  Confidence: {opp.confidence_score} (min: 0.3)")
            
            # Basic filtering criteria
            if opp.expected_profit < self.min_profit_threshold:
                logger.info(f"  ❌ Rejected: Profit too low ({opp.expected_profit} < {self.min_profit_threshold})")
                continue
            
            if opp.risk_score > 0.8:  # Skip very high risk opportunities
                logger.info(f"  ❌ Rejected: Risk too high ({opp.risk_score} > 0.8)")
                continue
            
            if opp.confidence_score < 0.3:  # Skip very low confidence opportunities
                logger.info(f"  ❌ Rejected: Confidence too low ({opp.confidence_score} < 0.3)")
                continue
                
            logger.info(f"  ✅ Accepted: All basic criteria passed")
            
            # Market condition filtering (more permissive for profitable opportunities)
            logger.info(f"  Market favorable: {market_condition.is_favorable_for_trading}, Risk: {opp.risk_score}")
            if not market_condition.is_favorable_for_trading and opp.risk_score > 0.85:  # Increased from 0.6 to 0.85
                logger.info(f"  ❌ Rejected: Unfavorable market conditions with very high risk")
                continue  # Only skip very high risk opportunities in unfavorable conditions
                
            logger.info(f"  ✅ Passed market condition filter")
            
            # Add historical performance analysis
            await self._enhance_with_historical_performance(opp)
            logger.info(f"  Historical enhancement complete")
            
            filtered_opportunities.append(opp)
            logger.info(f"  ✅ Final acceptance - added to filtered list")
        
        # Rank by overall score (highest first)
        filtered_opportunities.sort(key=lambda x: x.overall_score, reverse=True)
        
        return filtered_opportunities
    
    async def _enhance_with_historical_performance(self, opportunity: TradingOpportunity):
        """Enhance opportunity with historical performance data."""
        try:
            # This would query historical strategy performance data
            # For now, use placeholder logic
            
            if opportunity.strategy_type == 'combine':
                # Combine strategies historically perform better with stable market conditions
                base_success_rate = 0.75
            else:
                # Decombine strategies perform better in volatile conditions
                base_success_rate = 0.70
            
            # Adjust based on current conditions
            if opportunity.volatility_score < 0.3:
                success_rate_adjustment = 0.1 if opportunity.strategy_type == 'combine' else -0.05
            else:
                success_rate_adjustment = -0.1 if opportunity.strategy_type == 'combine' else 0.1
            
            opportunity.historical_success_rate = min(1.0, base_success_rate + success_rate_adjustment)
            opportunity.avg_historical_profit = opportunity.expected_profit * opportunity.historical_success_rate
            
        except Exception as e:
            logger.debug(f"Historical performance enhancement failed: {e}")
            opportunity.historical_success_rate = 0.6
            opportunity.avg_historical_profit = opportunity.expected_profit * 0.6