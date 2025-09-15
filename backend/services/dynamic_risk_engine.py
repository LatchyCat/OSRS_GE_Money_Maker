"""
Dynamic Risk Scoring Engine

Advanced risk assessment system for OSRS trading that provides:
- Real-time risk scoring (0-100 scale)
- Multi-factor risk analysis (volatility, liquidity, market, execution)
- Dynamic risk thresholds based on market conditions
- Portfolio risk management recommendations
- Risk-adjusted profit calculations
- Capital allocation optimization
"""

import logging
import statistics
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Avg, Max, Min, Count, StdDev, F
from django.db import transaction
from asgiref.sync import sync_to_async
import math

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation, HistoricalPrice
from apps.realtime_engine.models import MarketMomentum, VolumeAnalysis, RiskMetrics, MarketEvent
from services.intelligent_cache import intelligent_cache
from services.timeseries_client import timeseries_client

logger = logging.getLogger(__name__)


class RiskFactor:
    """Individual risk factor with weight and calculation method."""
    
    def __init__(self, name: str, weight: float, min_score: float = 0.0, max_score: float = 100.0):
        self.name = name
        self.weight = weight  # Weight in overall risk calculation (0.0-1.0)
        self.min_score = min_score
        self.max_score = max_score
        
    def normalize_score(self, raw_score: float) -> float:
        """Normalize score to 0-100 range."""
        return max(self.min_score, min(self.max_score, raw_score))


class DynamicRiskEngine:
    """
    Comprehensive dynamic risk assessment engine for OSRS trading.
    
    Provides multi-dimensional risk analysis combining:
    - Price volatility risk
    - Liquidity risk  
    - Market sentiment risk
    - Execution risk
    - Portfolio concentration risk
    """
    
    def __init__(self):
        # Risk factor definitions with weights
        self.risk_factors = {
            'volatility': RiskFactor('Price Volatility Risk', weight=0.25),
            'liquidity': RiskFactor('Liquidity Risk', weight=0.20),
            'market_sentiment': RiskFactor('Market Sentiment Risk', weight=0.15),
            'execution': RiskFactor('Execution Risk', weight=0.15),
            'concentration': RiskFactor('Portfolio Concentration Risk', weight=0.10),
            'momentum': RiskFactor('Momentum Risk', weight=0.10),
            'event': RiskFactor('Market Event Risk', weight=0.05)
        }
        
        # Risk thresholds (dynamic based on market conditions)
        self.risk_thresholds = {
            'very_low': 20,      # 0-20: Very Low Risk
            'low': 35,           # 20-35: Low Risk  
            'moderate': 55,      # 35-55: Moderate Risk
            'high': 75,          # 55-75: High Risk
            'very_high': 100     # 75-100: Very High Risk
        }
        
        # Market condition adjustments
        self.market_adjustment_factors = {
            'bull_market': 0.9,    # Reduce risk scores in bull markets
            'bear_market': 1.2,    # Increase risk scores in bear markets
            'volatile_market': 1.15, # Increase risk in high volatility
            'stable_market': 0.95   # Slightly reduce risk in stable conditions
        }
    
    async def calculate_comprehensive_risk(self, item_id: int, investment_amount: Optional[float] = None, 
                                         portfolio_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive risk assessment for an item.
        
        Args:
            item_id: OSRS item ID
            investment_amount: Planned investment amount (optional)
            portfolio_context: Current portfolio information (optional)
            
        Returns:
            Dictionary with comprehensive risk analysis
        """
        logger.debug(f"🎯 Calculating comprehensive risk for item {item_id}")
        
        try:
            # Check cache first
            cache_key = f"risk_analysis:{item_id}"
            cached_risk = intelligent_cache.get(cache_key, tiers=["hot", "warm"])
            
            if cached_risk and not investment_amount:  # Use cache for standard analysis
                logger.debug(f"📊 Using cached risk analysis for item {item_id}")
                return cached_risk
            
            # Gather risk calculation data
            risk_data = await self._gather_risk_data(item_id)
            
            if not risk_data:
                return {'error': 'Insufficient data for risk calculation', 'item_id': item_id}
            
            # Calculate individual risk factors
            risk_scores = {}
            risk_explanations = {}
            
            # 1. Volatility Risk
            volatility_score, volatility_explanation = await self._calculate_volatility_risk(risk_data)
            risk_scores['volatility'] = volatility_score
            risk_explanations['volatility'] = volatility_explanation
            
            # 2. Liquidity Risk
            liquidity_score, liquidity_explanation = await self._calculate_liquidity_risk(risk_data)
            risk_scores['liquidity'] = liquidity_score
            risk_explanations['liquidity'] = liquidity_explanation
            
            # 3. Market Sentiment Risk
            sentiment_score, sentiment_explanation = await self._calculate_sentiment_risk(risk_data)
            risk_scores['market_sentiment'] = sentiment_score
            risk_explanations['market_sentiment'] = sentiment_explanation
            
            # 4. Execution Risk
            execution_score, execution_explanation = await self._calculate_execution_risk(risk_data)
            risk_scores['execution'] = execution_score
            risk_explanations['execution'] = execution_explanation
            
            # 5. Momentum Risk
            momentum_score, momentum_explanation = await self._calculate_momentum_risk(risk_data)
            risk_scores['momentum'] = momentum_score
            risk_explanations['momentum'] = momentum_explanation
            
            # 6. Market Event Risk
            event_score, event_explanation = await self._calculate_event_risk(risk_data)
            risk_scores['event'] = event_score
            risk_explanations['event'] = event_explanation
            
            # 7. Portfolio Concentration Risk (if portfolio context provided)
            if portfolio_context:
                concentration_score, concentration_explanation = await self._calculate_concentration_risk(
                    risk_data, portfolio_context, investment_amount
                )
                risk_scores['concentration'] = concentration_score
                risk_explanations['concentration'] = concentration_explanation
            else:
                risk_scores['concentration'] = 20.0  # Default low concentration risk
                risk_explanations['concentration'] = "No portfolio context provided"
            
            # Calculate overall risk score
            overall_risk_score = self._calculate_weighted_risk_score(risk_scores)
            
            # Apply market condition adjustments
            market_adjusted_score = await self._apply_market_adjustments(overall_risk_score, risk_data)
            
            # Determine risk category and recommendations
            risk_category = self._determine_risk_category(market_adjusted_score)
            recommendations = self._generate_risk_recommendations(
                market_adjusted_score, risk_scores, risk_data, investment_amount
            )
            
            # Calculate risk-adjusted metrics
            risk_adjusted_metrics = await self._calculate_risk_adjusted_metrics(
                risk_data, market_adjusted_score, investment_amount
            )
            
            # Compile comprehensive risk analysis
            risk_analysis = {
                'item_id': item_id,
                'item_name': risk_data.get('item_name', 'Unknown'),
                'timestamp': timezone.now().isoformat(),
                
                # Overall risk assessment
                'overall_risk_score': round(market_adjusted_score, 1),
                'risk_category': risk_category,
                'raw_risk_score': round(overall_risk_score, 1),
                
                # Individual risk factors
                'risk_factors': {
                    factor_name: {
                        'score': round(score, 1),
                        'weight': self.risk_factors[factor_name].weight,
                        'explanation': risk_explanations[factor_name],
                        'contribution': round(score * self.risk_factors[factor_name].weight, 1)
                    }
                    for factor_name, score in risk_scores.items()
                },
                
                # Risk-adjusted metrics
                'risk_adjusted_metrics': risk_adjusted_metrics,
                
                # Recommendations
                'recommendations': recommendations,
                
                # Market context
                'market_conditions': await self._get_market_context(),
                
                # Investment guidelines
                'investment_guidelines': self._generate_investment_guidelines(
                    market_adjusted_score, risk_data, investment_amount
                )
            }
            
            # Cache the analysis (shorter TTL for high-risk items)
            cache_ttl = 60 if market_adjusted_score > 70 else 300  # 1min vs 5min
            intelligent_cache.set(
                cache_key, 
                risk_analysis, 
                tier="warm", 
                tags=[f"item_{item_id}", "risk_analysis", f"risk_{risk_category}"]
            )
            
            logger.info(f"✅ Risk analysis completed for item {item_id}: {risk_category} ({market_adjusted_score:.1f})")
            return risk_analysis
            
        except Exception as e:
            logger.error(f"❌ Risk calculation failed for item {item_id}: {e}")
            return {'error': str(e), 'item_id': item_id}
    
    @sync_to_async
    def _gather_risk_data(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Gather all necessary data for risk calculation."""
        try:
            item = Item.objects.select_related('profit_calc').get(item_id=item_id)
            
            # Get real-time analysis data
            momentum = getattr(item, 'momentum', None)
            volume_analysis = getattr(item, 'volume_analysis', None)
            risk_metrics = getattr(item, 'risk_metrics', None)
            
            # Get recent price data
            recent_prices = PriceSnapshot.objects.filter(
                item=item,
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).order_by('-created_at')[:50]
            
            # Get profit calculation
            profit_calc = getattr(item, 'profit_calc', None)
            
            return {
                'item_id': item_id,
                'item_name': item.name,
                'item': item,
                'momentum': momentum,
                'volume_analysis': volume_analysis,
                'risk_metrics': risk_metrics,
                'recent_prices': list(recent_prices),
                'profit_calc': profit_calc,
                'buy_limit': item.limit,
                'high_alch_value': item.high_alch
            }
            
        except Item.DoesNotExist:
            logger.error(f"Item {item_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error gathering risk data for item {item_id}: {e}")
            return None
    
    async def _calculate_volatility_risk(self, risk_data: Dict) -> Tuple[float, str]:
        """Calculate price volatility risk score."""
        try:
            recent_prices = risk_data.get('recent_prices', [])
            
            if not recent_prices:
                return 50.0, "No recent price data available"
            
            # Calculate price volatility from recent data
            prices = [p.high_price for p in recent_prices if p.high_price]
            
            if len(prices) < 3:
                return 45.0, "Insufficient price history for volatility calculation"
            
            # Calculate coefficient of variation (volatility measure)
            mean_price = statistics.mean(prices)
            price_std = statistics.stdev(prices)
            coefficient_of_variation = (price_std / mean_price) if mean_price > 0 else 0
            
            # Convert to 0-100 risk score (higher volatility = higher risk)
            volatility_risk = min(100, coefficient_of_variation * 500)  # Scale appropriately
            
            # Additional volatility indicators
            price_range = max(prices) - min(prices)
            range_pct = (price_range / mean_price * 100) if mean_price > 0 else 0
            
            # Combine volatility measures
            combined_volatility_risk = (volatility_risk * 0.7) + (min(100, range_pct * 2) * 0.3)
            
            explanation = f"Price volatility: {coefficient_of_variation:.3f} CV, {range_pct:.1f}% range"
            
            return combined_volatility_risk, explanation
            
        except Exception as e:
            logger.error(f"Volatility risk calculation failed: {e}")
            return 50.0, f"Volatility calculation error: {str(e)}"
    
    async def _calculate_liquidity_risk(self, risk_data: Dict) -> Tuple[float, str]:
        """Calculate liquidity risk score."""
        try:
            volume_analysis = risk_data.get('volume_analysis')
            profit_calc = risk_data.get('profit_calc')
            
            if not volume_analysis:
                return 60.0, "No volume analysis data available"
            
            # Base liquidity risk from volume analysis
            liquidity_level = volume_analysis.liquidity_level
            daily_volume = volume_analysis.current_daily_volume or 0
            flip_probability = volume_analysis.flip_completion_probability or 0.5
            
            # Map liquidity levels to risk scores
            liquidity_risk_map = {
                'very_high': 10,
                'high': 20,
                'medium': 40,
                'low': 70,
                'minimal': 90
            }
            
            base_liquidity_risk = liquidity_risk_map.get(liquidity_level, 50)
            
            # Adjust based on daily volume
            if daily_volume >= 2000:
                volume_adjustment = -10  # Lower risk for high volume
            elif daily_volume >= 500:
                volume_adjustment = -5   # Slightly lower risk
            elif daily_volume < 100:
                volume_adjustment = 15   # Higher risk for low volume
            else:
                volume_adjustment = 0
            
            # Adjust based on flip completion probability
            flip_adjustment = (1.0 - flip_probability) * 20  # Higher risk for lower flip probability
            
            # Consider bid-ask spread if available
            spread_adjustment = 0
            recent_prices = risk_data.get('recent_prices', [])
            if recent_prices:
                latest_price = recent_prices[0]
                if latest_price.high_price and latest_price.low_price:
                    spread_pct = ((latest_price.high_price - latest_price.low_price) / latest_price.high_price * 100)
                    spread_adjustment = min(15, spread_pct)  # Higher spread = higher risk
            
            total_liquidity_risk = base_liquidity_risk + volume_adjustment + flip_adjustment + spread_adjustment
            total_liquidity_risk = max(0, min(100, total_liquidity_risk))
            
            explanation = f"Liquidity: {liquidity_level}, Volume: {daily_volume}, Flip prob: {flip_probability:.2f}"
            
            return total_liquidity_risk, explanation
            
        except Exception as e:
            logger.error(f"Liquidity risk calculation failed: {e}")
            return 50.0, f"Liquidity calculation error: {str(e)}"
    
    async def _calculate_sentiment_risk(self, risk_data: Dict) -> Tuple[float, str]:
        """Calculate market sentiment risk score."""
        try:
            momentum = risk_data.get('momentum')
            
            if not momentum:
                return 45.0, "No momentum data available"
            
            # Base sentiment risk from trend direction
            trend_risk_map = {
                'rising': 25,      # Lower risk in uptrend
                'stable': 40,      # Medium risk in sideways market
                'falling': 70      # Higher risk in downtrend
            }
            
            base_sentiment_risk = trend_risk_map.get(momentum.trend_direction, 50)
            
            # Adjust based on momentum strength
            momentum_score = momentum.momentum_score or 50
            
            if momentum_score >= 80:
                momentum_adjustment = -10  # Strong momentum reduces risk
            elif momentum_score >= 60:
                momentum_adjustment = -5   # Good momentum slightly reduces risk
            elif momentum_score <= 20:
                momentum_adjustment = 15   # Weak momentum increases risk
            else:
                momentum_adjustment = 0
            
            # Adjust based on price velocity (rate of change)
            velocity = abs(momentum.price_velocity or 0)
            if velocity > 50:  # Very fast price changes increase risk
                velocity_adjustment = 10
            elif velocity < 5:  # Very slow changes may indicate stagnation
                velocity_adjustment = 5
            else:
                velocity_adjustment = 0
            
            total_sentiment_risk = base_sentiment_risk + momentum_adjustment + velocity_adjustment
            total_sentiment_risk = max(0, min(100, total_sentiment_risk))
            
            explanation = f"Trend: {momentum.trend_direction}, Momentum: {momentum_score:.1f}, Velocity: {momentum.price_velocity:.1f}"
            
            return total_sentiment_risk, explanation
            
        except Exception as e:
            logger.error(f"Sentiment risk calculation failed: {e}")
            return 45.0, f"Sentiment calculation error: {str(e)}"
    
    async def _calculate_execution_risk(self, risk_data: Dict) -> Tuple[float, str]:
        """Calculate execution risk based on item characteristics."""
        try:
            item = risk_data.get('item')
            profit_calc = risk_data.get('profit_calc')
            buy_limit = risk_data.get('buy_limit')
            
            base_execution_risk = 30.0  # Default moderate execution risk
            
            # Buy limit risk
            if buy_limit is None:
                limit_risk = 10  # No limit is actually lower risk
            elif buy_limit >= 1000:
                limit_risk = 15  # High limit, moderate risk
            elif buy_limit >= 100:
                limit_risk = 25  # Medium limit
            else:
                limit_risk = 40  # Low limit increases execution risk
            
            # Profit margin execution risk
            margin_risk = 25  # Default
            if profit_calc:
                margin = profit_calc.current_profit_margin or 0
                if margin >= 20:
                    margin_risk = 15  # High margin, lower execution risk
                elif margin >= 10:
                    margin_risk = 20  # Good margin
                elif margin >= 5:
                    margin_risk = 30  # Moderate margin
                else:
                    margin_risk = 45  # Low margin, higher execution risk
            
            # Item type execution risk (based on item ID patterns)
            item_type_risk = 25  # Default
            item_id = risk_data.get('item_id', 0)
            
            # Common item patterns (lower execution risk)
            if item_id < 5000:  # Early game items
                item_type_risk = 20
            elif 10000 <= item_id < 15000:  # Common equipment
                item_type_risk = 25
            elif item_id > 25000:  # Newer items (potentially higher risk)
                item_type_risk = 35
            
            # Combine execution risk factors
            total_execution_risk = (limit_risk * 0.4) + (margin_risk * 0.4) + (item_type_risk * 0.2)
            total_execution_risk = max(0, min(100, total_execution_risk))
            
            explanation = f"Buy limit: {buy_limit or 'None'}, Execution complexity: moderate"
            
            return total_execution_risk, explanation
            
        except Exception as e:
            logger.error(f"Execution risk calculation failed: {e}")
            return 35.0, f"Execution calculation error: {str(e)}"
    
    async def _calculate_momentum_risk(self, risk_data: Dict) -> Tuple[float, str]:
        """Calculate momentum-based risk score."""
        try:
            momentum = risk_data.get('momentum')
            
            if not momentum:
                return 40.0, "No momentum data available"
            
            # Risk increases with extreme momentum (both positive and negative)
            momentum_score = momentum.momentum_score or 50
            
            if 40 <= momentum_score <= 60:
                # Neutral momentum - lowest risk
                momentum_risk = 20
            elif 60 < momentum_score <= 80:
                # Good momentum - low risk
                momentum_risk = 30
            elif momentum_score > 80:
                # Very high momentum - potential for reversal
                momentum_risk = 50
            elif 20 <= momentum_score < 40:
                # Weak momentum - moderate risk
                momentum_risk = 45
            else:
                # Very low momentum - high risk
                momentum_risk = 65
            
            # Adjust for acceleration
            acceleration = abs(momentum.price_acceleration or 0)
            if acceleration > 5:
                acceleration_adjustment = 10  # High acceleration increases risk
            else:
                acceleration_adjustment = 0
            
            total_momentum_risk = momentum_risk + acceleration_adjustment
            total_momentum_risk = max(0, min(100, total_momentum_risk))
            
            explanation = f"Momentum score: {momentum_score:.1f}, Acceleration: {momentum.price_acceleration:.1f}"
            
            return total_momentum_risk, explanation
            
        except Exception as e:
            logger.error(f"Momentum risk calculation failed: {e}")
            return 40.0, f"Momentum calculation error: {str(e)}"
    
    @sync_to_async  
    def _calculate_event_risk(self, risk_data: Dict) -> Tuple[float, str]:
        """Calculate market event risk score."""
        try:
            # Check for recent high-impact market events
            recent_events = MarketEvent.objects.filter(
                is_active=True,
                detected_at__gte=timezone.now() - timedelta(hours=6),
                impact_score__gte=50
            )
            
            if not recent_events.exists():
                return 15.0, "No significant market events detected"
            
            # Calculate event risk based on impact and recency
            max_impact = 0
            event_count = 0
            
            for event in recent_events:
                max_impact = max(max_impact, event.impact_score)
                event_count += 1
            
            # Base event risk from highest impact event
            base_event_risk = min(80, max_impact * 0.8)
            
            # Increase risk for multiple events
            multiple_events_adjustment = min(15, event_count * 3)
            
            total_event_risk = base_event_risk + multiple_events_adjustment
            total_event_risk = max(0, min(100, total_event_risk))
            
            explanation = f"{event_count} active events, max impact: {max_impact}"
            
            return total_event_risk, explanation
            
        except Exception as e:
            logger.error(f"Event risk calculation failed: {e}")
            return 20.0, f"Event calculation error: {str(e)}"
    
    async def _calculate_concentration_risk(self, risk_data: Dict, portfolio_context: Dict, 
                                          investment_amount: Optional[float]) -> Tuple[float, str]:
        """Calculate portfolio concentration risk."""
        try:
            if not portfolio_context or not investment_amount:
                return 25.0, "No portfolio context provided"
            
            total_portfolio_value = portfolio_context.get('total_value', 100000)  # Default 100k
            current_item_exposure = portfolio_context.get('current_exposure', {}).get(str(risk_data['item_id']), 0)
            
            # Calculate new exposure percentage
            new_exposure_pct = ((current_item_exposure + investment_amount) / total_portfolio_value) * 100
            
            # Risk increases exponentially with concentration
            if new_exposure_pct <= 5:
                concentration_risk = 10  # Very low risk
            elif new_exposure_pct <= 10:
                concentration_risk = 20  # Low risk
            elif new_exposure_pct <= 20:
                concentration_risk = 40  # Moderate risk
            elif new_exposure_pct <= 35:
                concentration_risk = 65  # High risk
            else:
                concentration_risk = 85  # Very high risk
            
            explanation = f"New exposure: {new_exposure_pct:.1f}% of portfolio"
            
            return concentration_risk, explanation
            
        except Exception as e:
            logger.error(f"Concentration risk calculation failed: {e}")
            return 30.0, f"Concentration calculation error: {str(e)}"
    
    def _calculate_weighted_risk_score(self, risk_scores: Dict[str, float]) -> float:
        """Calculate weighted overall risk score."""
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for factor_name, score in risk_scores.items():
            if factor_name in self.risk_factors:
                weight = self.risk_factors[factor_name].weight
                total_weighted_score += score * weight
                total_weight += weight
        
        return total_weighted_score / total_weight if total_weight > 0 else 50.0
    
    async def _apply_market_adjustments(self, base_risk_score: float, risk_data: Dict) -> float:
        """Apply market condition adjustments to risk score."""
        try:
            # Determine market condition
            market_condition = await self._determine_market_condition()
            
            # Apply adjustment factor
            adjustment_factor = self.market_adjustment_factors.get(market_condition, 1.0)
            adjusted_score = base_risk_score * adjustment_factor
            
            return max(0, min(100, adjusted_score))
            
        except Exception as e:
            logger.error(f"Market adjustment failed: {e}")
            return base_risk_score
    
    @sync_to_async
    def _determine_market_condition(self) -> str:
        """Determine current market condition."""
        try:
            # Analyze overall market momentum
            total_momentum_items = MarketMomentum.objects.count()
            if total_momentum_items == 0:
                return 'stable_market'
            
            rising_items = MarketMomentum.objects.filter(trend_direction='rising').count()
            falling_items = MarketMomentum.objects.filter(trend_direction='falling').count()
            
            rising_pct = (rising_items / total_momentum_items) * 100
            falling_pct = (falling_items / total_momentum_items) * 100
            
            # Analyze market volatility
            avg_volatility = PriceSnapshot.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=2),
                price_volatility__isnull=False
            ).aggregate(avg_vol=Avg('price_volatility'))['avg_vol'] or 0
            
            # Determine market condition
            if avg_volatility > 0.25:
                return 'volatile_market'
            elif rising_pct > 65:
                return 'bull_market'
            elif falling_pct > 65:
                return 'bear_market'
            else:
                return 'stable_market'
                
        except Exception as e:
            logger.error(f"Market condition determination failed: {e}")
            return 'stable_market'
    
    def _determine_risk_category(self, risk_score: float) -> str:
        """Determine risk category from score."""
        if risk_score <= self.risk_thresholds['very_low']:
            return 'very_low'
        elif risk_score <= self.risk_thresholds['low']:
            return 'low'
        elif risk_score <= self.risk_thresholds['moderate']:
            return 'moderate'
        elif risk_score <= self.risk_thresholds['high']:
            return 'high'
        else:
            return 'very_high'
    
    def _generate_risk_recommendations(self, risk_score: float, risk_factors: Dict, 
                                     risk_data: Dict, investment_amount: Optional[float]) -> List[Dict]:
        """Generate risk-based recommendations."""
        recommendations = []
        
        # Overall risk recommendations
        if risk_score <= 25:
            recommendations.append({
                'type': 'position_sizing',
                'priority': 'medium',
                'message': 'Low risk profile - consider standard position sizing',
                'max_position_pct': 15.0
            })
        elif risk_score <= 50:
            recommendations.append({
                'type': 'position_sizing',
                'priority': 'medium', 
                'message': 'Moderate risk - use conservative position sizing',
                'max_position_pct': 10.0
            })
        elif risk_score <= 75:
            recommendations.append({
                'type': 'position_sizing',
                'priority': 'high',
                'message': 'High risk - use small position sizes and tight stops',
                'max_position_pct': 5.0
            })
        else:
            recommendations.append({
                'type': 'position_sizing',
                'priority': 'critical',
                'message': 'Very high risk - avoid or use minimal position size',
                'max_position_pct': 2.0
            })
        
        # Factor-specific recommendations
        if risk_factors.get('volatility', 0) > 70:
            recommendations.append({
                'type': 'volatility_management',
                'priority': 'high',
                'message': 'High price volatility - consider dollar-cost averaging or smaller positions'
            })
        
        if risk_factors.get('liquidity', 0) > 60:
            recommendations.append({
                'type': 'liquidity_management', 
                'priority': 'high',
                'message': 'Poor liquidity - allow extra time for execution and consider market orders'
            })
        
        if risk_factors.get('momentum', 0) > 70:
            recommendations.append({
                'type': 'momentum_management',
                'priority': 'medium',
                'message': 'Extreme momentum detected - monitor for potential reversals'
            })
        
        return recommendations
    
    async def _calculate_risk_adjusted_metrics(self, risk_data: Dict, risk_score: float, 
                                             investment_amount: Optional[float]) -> Dict[str, Any]:
        """Calculate risk-adjusted performance metrics."""
        try:
            profit_calc = risk_data.get('profit_calc')
            
            if not profit_calc:
                return {}
            
            # Risk adjustment factor (higher risk = lower adjustment)
            risk_adjustment_factor = max(0.1, (100 - risk_score) / 100)
            
            # Risk-adjusted profit
            raw_profit = profit_calc.current_profit or 0
            risk_adjusted_profit = raw_profit * risk_adjustment_factor
            
            # Risk-adjusted return percentage
            raw_margin = profit_calc.current_profit_margin or 0
            risk_adjusted_margin = raw_margin * risk_adjustment_factor
            
            # Sharpe-like ratio (return per unit of risk)
            sharpe_ratio = raw_margin / max(risk_score, 1) if raw_margin > 0 else 0
            
            # Kelly criterion position size (if investment amount provided)
            kelly_position = None
            if investment_amount and raw_profit > 0:
                # Simplified Kelly: (bp - q) / b where b=odds, p=win prob, q=loss prob
                win_probability = max(0.1, min(0.9, (100 - risk_score) / 100))
                loss_probability = 1 - win_probability
                odds = abs(raw_profit / max(risk_data.get('profit_calc').current_buy_price or 1000, 1))
                kelly_fraction = (odds * win_probability - loss_probability) / odds
                kelly_position = max(0, min(0.25, kelly_fraction))  # Cap at 25%
            
            return {
                'risk_adjusted_profit': round(risk_adjusted_profit, 2),
                'risk_adjusted_margin': round(risk_adjusted_margin, 2),
                'sharpe_ratio': round(sharpe_ratio, 3),
                'risk_adjustment_factor': round(risk_adjustment_factor, 3),
                'kelly_position_size': round(kelly_position, 3) if kelly_position else None,
                'recommended_max_loss': round(investment_amount * 0.02, 2) if investment_amount else None  # 2% max loss
            }
            
        except Exception as e:
            logger.error(f"Risk-adjusted metrics calculation failed: {e}")
            return {}
    
    async def _get_market_context(self) -> Dict[str, Any]:
        """Get current market context for risk assessment."""
        try:
            market_condition = await self._determine_market_condition()
            
            # Get market statistics
            total_items = await sync_to_async(MarketMomentum.objects.count)()
            high_risk_items = await sync_to_async(
                lambda: RiskMetrics.objects.filter(overall_risk_score__gte=70).count()
            )()
            
            return {
                'market_condition': market_condition,
                'total_analyzed_items': total_items,
                'high_risk_items': high_risk_items,
                'risk_environment': 'elevated' if high_risk_items > total_items * 0.3 else 'normal'
            }
            
        except Exception as e:
            logger.error(f"Market context retrieval failed: {e}")
            return {'market_condition': 'unknown'}
    
    def _generate_investment_guidelines(self, risk_score: float, risk_data: Dict, 
                                      investment_amount: Optional[float]) -> Dict[str, Any]:
        """Generate investment guidelines based on risk assessment."""
        risk_category = self._determine_risk_category(risk_score)
        
        guidelines = {
            'very_low': {
                'max_position_size_pct': 20.0,
                'stop_loss_pct': 3.0,
                'holding_period': 'Medium to Long-term',
                'monitoring_frequency': 'Daily'
            },
            'low': {
                'max_position_size_pct': 15.0,
                'stop_loss_pct': 2.5,
                'holding_period': 'Short to Medium-term',
                'monitoring_frequency': 'Daily'
            },
            'moderate': {
                'max_position_size_pct': 10.0,
                'stop_loss_pct': 2.0,
                'holding_period': 'Short-term',
                'monitoring_frequency': 'Multiple times per day'
            },
            'high': {
                'max_position_size_pct': 5.0,
                'stop_loss_pct': 1.5,
                'holding_period': 'Very Short-term',
                'monitoring_frequency': 'Hourly'
            },
            'very_high': {
                'max_position_size_pct': 2.0,
                'stop_loss_pct': 1.0,
                'holding_period': 'Intraday only',
                'monitoring_frequency': 'Continuous'
            }
        }
        
        return guidelines.get(risk_category, guidelines['moderate'])


# Global dynamic risk engine instance
dynamic_risk_engine = DynamicRiskEngine()