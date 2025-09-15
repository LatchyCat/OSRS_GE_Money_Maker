"""
Advanced Risk & Timing Engine - Intelligent Risk Assessment and Timing Optimization

Provides sophisticated risk analysis, capital optimization, and precise timing
for trading decisions. Includes profit probability scoring and stop-loss integration.
Memory-optimized for M1 MacBook Pro.
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum
import statistics
import math

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from services.smart_opportunity_detector import PrecisionOpportunity
from services.market_signal_generator import MarketSignal, TradingWindow

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    """Comprehensive risk assessment for trading opportunity."""
    item_id: int
    item_name: str
    
    # Risk scoring (0-10, where 0 = no risk, 10 = maximum risk)
    overall_risk_score: float
    liquidity_risk: float
    volatility_risk: float
    market_risk: float
    timing_risk: float
    
    # Probability metrics
    profit_probability_pct: float
    loss_probability_pct: float
    breakeven_probability_pct: float
    
    # Capital optimization
    recommended_position_size: int
    max_position_size: int
    capital_at_risk_gp: int
    capital_at_risk_pct: float
    
    # Risk management
    stop_loss_price: int
    take_profit_price: int
    max_hold_time_hours: float
    risk_reward_ratio: float
    
    # Risk factors
    risk_factors: List[str] = field(default_factory=list)
    mitigation_strategies: List[str] = field(default_factory=list)
    
    # Risk level classification
    risk_level: str = "medium"  # 'low', 'medium', 'high'


@dataclass
class TimingAnalysis:
    """Advanced timing analysis for optimal trade execution."""
    item_id: int
    item_name: str
    
    # Optimal timing
    best_buy_time: datetime
    best_sell_time: datetime
    worst_buy_time: datetime
    worst_sell_time: datetime
    
    # Timing confidence
    timing_confidence: float
    historical_pattern_strength: float
    
    # Market timing factors
    volume_pattern_score: float
    price_pattern_score: float
    volatility_timing_score: float
    
    # Execution strategy
    entry_strategy: str
    exit_strategy: str
    position_scaling_strategy: str
    
    # Performance metrics
    expected_hold_time_hours: float
    time_decay_risk: float
    seasonal_factors: List[str] = field(default_factory=list)


@dataclass
class PortfolioOptimization:
    """Portfolio-level optimization recommendations."""
    total_capital_gp: int
    recommended_allocations: Dict[int, float]  # item_id -> allocation percentage
    
    # Portfolio metrics
    portfolio_risk_score: float
    expected_portfolio_return_pct: float
    portfolio_sharpe_ratio: float
    diversification_score: float
    
    # Risk management
    total_capital_at_risk_pct: float
    correlation_risk: float
    concentration_risk: float
    
    # Rebalancing recommendations
    rebalancing_frequency_hours: int
    rebalancing_threshold_pct: float
    
    optimization_reasoning: List[str] = field(default_factory=list)


class AdvancedRiskEngine:
    """
    Advanced risk assessment and timing optimization engine.
    
    Provides intelligent risk scoring, capital optimization, and precise
    timing recommendations while maintaining efficient memory usage.
    """
    
    def __init__(self):
        # Memory optimization settings
        self.max_portfolio_items = 50
        self.risk_cache_minutes = 5
        self.batch_analysis_size = 20
        
        # Risk assessment parameters
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        self.max_position_risk_pct = 0.20  # 20% max position risk
        self.high_risk_threshold = 7.0  # Risk scores above this are high risk
        self.optimal_risk_range = (3.0, 6.0)  # Optimal risk score range
        
        # Timing analysis parameters
        self.timing_lookback_days = 30
        self.min_pattern_occurrences = 5
        self.seasonal_analysis_days = 90
        
        # Portfolio optimization settings
        self.min_diversification_items = 5
        self.max_correlation_threshold = 0.7
        self.rebalancing_threshold = 0.05  # 5% deviation triggers rebalancing
    
    async def assess_opportunity_risk(self, 
                                    opportunity: PrecisionOpportunity,
                                    capital_gp: int,
                                    risk_tolerance: str = 'moderate') -> RiskAssessment:
        """
        Comprehensive risk assessment for a trading opportunity.
        
        Args:
            opportunity: Precision trading opportunity
            capital_gp: Available trading capital
            risk_tolerance: Risk tolerance level
            
        Returns:
            Detailed risk assessment with recommendations
        """
        try:
            logger.info(f"Assessing risk for {opportunity.item_name}")
            
            # Get historical data for risk analysis
            price_history = await self._get_extended_price_history(opportunity.item_id, days=30)
            
            # Calculate individual risk components
            liquidity_risk = await self._calculate_liquidity_risk(opportunity, price_history)
            volatility_risk = await self._calculate_volatility_risk(price_history)
            market_risk = await self._calculate_market_risk(opportunity, price_history)
            timing_risk = await self._calculate_timing_risk(opportunity)
            
            # Calculate overall risk score
            risk_weights = {'conservative': 0.8, 'moderate': 1.0, 'aggressive': 1.2}
            weight = risk_weights.get(risk_tolerance, 1.0)
            
            overall_risk = (liquidity_risk * 0.3 + volatility_risk * 0.3 + 
                          market_risk * 0.25 + timing_risk * 0.15) * weight
            
            # Calculate probability metrics
            profit_prob, loss_prob, breakeven_prob = await self._calculate_outcome_probabilities(
                opportunity, price_history
            )
            
            # Optimize position sizing
            recommended_size, max_size, capital_at_risk = await self._optimize_position_size(
                opportunity, capital_gp, overall_risk, risk_tolerance
            )
            
            # Calculate risk management levels
            stop_loss, take_profit = await self._calculate_risk_levels(
                opportunity, overall_risk, price_history
            )
            
            # Calculate risk-reward ratio
            potential_profit = opportunity.recommended_sell_price - opportunity.recommended_buy_price
            potential_loss = opportunity.recommended_buy_price - stop_loss
            risk_reward_ratio = potential_profit / max(potential_loss, 1)
            
            # Generate risk factors and mitigation strategies
            risk_factors, mitigations = await self._generate_risk_insights(
                opportunity, overall_risk, price_history
            )
            
            return RiskAssessment(
                item_id=opportunity.item_id,
                item_name=opportunity.item_name,
                overall_risk_score=overall_risk,
                liquidity_risk=liquidity_risk,
                volatility_risk=volatility_risk,
                market_risk=market_risk,
                timing_risk=timing_risk,
                profit_probability_pct=profit_prob,
                loss_probability_pct=loss_prob,
                breakeven_probability_pct=breakeven_prob,
                recommended_position_size=recommended_size,
                max_position_size=max_size,
                capital_at_risk_gp=capital_at_risk,
                capital_at_risk_pct=(capital_at_risk / capital_gp) * 100,
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
                max_hold_time_hours=opportunity.estimated_hold_time_hours * 1.5,
                risk_reward_ratio=risk_reward_ratio,
                risk_factors=risk_factors,
                mitigation_strategies=mitigations
            )
            
        except Exception as e:
            logger.error(f"Error assessing risk for {opportunity.item_name}: {e}")
            return None
    
    async def analyze_optimal_timing(self, 
                                   opportunities: List[PrecisionOpportunity]) -> List[TimingAnalysis]:
        """
        Advanced timing analysis for multiple opportunities.
        
        Args:
            opportunities: List of trading opportunities
            
        Returns:
            List of timing analyses for optimal execution
        """
        try:
            timing_analyses = []
            
            # Process opportunities in batches
            for i in range(0, len(opportunities), self.batch_analysis_size):
                batch = opportunities[i:i + self.batch_analysis_size]
                
                batch_analyses = await asyncio.gather(*[
                    self._analyze_item_timing(opp) for opp in batch
                ], return_exceptions=True)
                
                for analysis in batch_analyses:
                    if isinstance(analysis, TimingAnalysis):
                        timing_analyses.append(analysis)
                
                await asyncio.sleep(0.01)  # Yield control
            
            # Sort by timing confidence
            timing_analyses.sort(key=lambda x: x.timing_confidence, reverse=True)
            
            logger.info(f"Completed timing analysis for {len(timing_analyses)} opportunities")
            return timing_analyses
            
        except Exception as e:
            logger.error(f"Error in timing analysis: {e}")
            return []
    
    async def optimize_portfolio(self, 
                               opportunities: List[PrecisionOpportunity],
                               risk_assessments: List[RiskAssessment],
                               capital_gp: int,
                               risk_tolerance: str = 'moderate') -> PortfolioOptimization:
        """
        Portfolio-level optimization using Modern Portfolio Theory principles.
        
        Args:
            opportunities: Available trading opportunities
            risk_assessments: Risk assessments for opportunities
            capital_gp: Total available capital
            risk_tolerance: Portfolio risk tolerance
            
        Returns:
            Portfolio optimization recommendations
        """
        try:
            logger.info(f"Optimizing portfolio with {capital_gp:,} GP capital")
            
            if not opportunities or not risk_assessments:
                return self._create_empty_portfolio(capital_gp)
            
            # Filter opportunities by risk tolerance
            filtered_opps = await self._filter_opportunities_by_risk(
                opportunities, risk_assessments, risk_tolerance
            )
            
            if len(filtered_opps) < 2:
                # Single opportunity portfolio
                return await self._create_single_asset_portfolio(
                    filtered_opps[0] if filtered_opps else opportunities[0],
                    capital_gp, risk_tolerance
                )
            
            # Calculate expected returns and correlations
            returns_data = await self._calculate_expected_returns(filtered_opps)
            correlation_matrix = await self._calculate_correlation_matrix(filtered_opps)
            
            # Optimize allocations using simplified Markowitz optimization
            optimal_allocations = await self._optimize_allocations(
                filtered_opps, returns_data, correlation_matrix, capital_gp, risk_tolerance
            )
            
            # Calculate portfolio metrics
            portfolio_metrics = await self._calculate_portfolio_metrics(
                optimal_allocations, filtered_opps, returns_data, correlation_matrix
            )
            
            return PortfolioOptimization(
                total_capital_gp=capital_gp,
                recommended_allocations=optimal_allocations,
                **portfolio_metrics
            )
            
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            return self._create_empty_portfolio(capital_gp)
    
    # Private helper methods
    
    async def _get_extended_price_history(self, item_id: int, days: int = 30) -> List[dict]:
        """Get extended price history for detailed analysis."""
        cache_key = f"extended_price_history_{item_id}_{days}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            item = await Item.objects.aget(item_id=item_id)
            since = timezone.now() - timedelta(days=days)
            
            history = []
            async for snapshot in PriceSnapshot.objects.filter(
                item=item,
                created_at__gte=since,
                high_price__isnull=False
            ).order_by('created_at'):
                history.append({
                    'price': snapshot.high_price,
                    'volume': snapshot.total_volume or 0,
                    'timestamp': snapshot.created_at,
                    'volatility': snapshot.price_volatility or 0
                })
            
            cache.set(cache_key, history, self.risk_cache_minutes * 60)
            return history
            
        except Exception as e:
            logger.error(f"Error getting price history for item {item_id}: {e}")
            return []
    
    async def _calculate_liquidity_risk(self, 
                                      opportunity: PrecisionOpportunity,
                                      price_history: List[dict]) -> float:
        """Calculate liquidity risk based on volume and spread patterns."""
        if not price_history:
            return 8.0  # High risk if no data
        
        # Volume-based liquidity assessment
        avg_volume = opportunity.daily_volume
        if avg_volume >= 1000:
            volume_risk = 1.0  # Very liquid
        elif avg_volume >= 500:
            volume_risk = 2.0  # Good liquidity
        elif avg_volume >= 100:
            volume_risk = 4.0  # Moderate liquidity
        elif avg_volume >= 50:
            volume_risk = 6.0  # Low liquidity
        else:
            volume_risk = 9.0  # Very low liquidity
        
        # Volume consistency risk
        volumes = [p['volume'] for p in price_history if p['volume'] > 0]
        if volumes:
            volume_cv = np.std(volumes) / max(np.mean(volumes), 1) if len(volumes) > 1 else 0
            consistency_risk = min(3.0, volume_cv * 5)  # Higher CV = higher risk
        else:
            consistency_risk = 5.0
        
        return min(10.0, (volume_risk + consistency_risk) / 2)
    
    async def _calculate_volatility_risk(self, price_history: List[dict]) -> float:
        """Calculate volatility-based risk."""
        if len(price_history) < 5:
            return 5.0  # Medium risk if insufficient data
        
        prices = [p['price'] for p in price_history]
        
        # Calculate price volatility
        returns = []
        for i in range(1, len(prices)):
            returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if not returns:
            return 5.0
        
        volatility = np.std(returns) * math.sqrt(24)  # Annualized volatility
        
        # Convert volatility to risk score (0-10)
        if volatility < 0.05:  # < 5% volatility
            return 1.0
        elif volatility < 0.1:  # 5-10% volatility
            return 2.5
        elif volatility < 0.2:  # 10-20% volatility
            return 5.0
        elif volatility < 0.4:  # 20-40% volatility
            return 7.5
        else:  # > 40% volatility
            return 10.0
    
    async def _calculate_market_risk(self, 
                                   opportunity: PrecisionOpportunity,
                                   price_history: List[dict]) -> float:
        """Calculate market and systematic risk."""
        if not price_history:
            return 5.0
        
        risk_factors = []
        
        # Profit margin risk (lower margins = higher risk)
        margin_pct = opportunity.expected_profit_margin_pct
        if margin_pct >= 10:
            risk_factors.append(1.0)  # Low risk
        elif margin_pct >= 5:
            risk_factors.append(3.0)  # Medium risk
        elif margin_pct >= 2:
            risk_factors.append(6.0)  # High risk
        else:
            risk_factors.append(9.0)  # Very high risk
        
        # Price level risk (very expensive items have higher risk)
        current_price = opportunity.current_price
        if current_price >= 100000000:  # 100M+ GP
            risk_factors.append(8.0)
        elif current_price >= 10000000:  # 10M+ GP
            risk_factors.append(5.0)
        elif current_price >= 1000000:  # 1M+ GP
            risk_factors.append(3.0)
        else:
            risk_factors.append(1.0)
        
        # Success probability risk
        success_prob = opportunity.success_probability_pct
        if success_prob >= 80:
            risk_factors.append(2.0)
        elif success_prob >= 60:
            risk_factors.append(4.0)
        elif success_prob >= 40:
            risk_factors.append(6.0)
        else:
            risk_factors.append(8.0)
        
        return statistics.mean(risk_factors)
    
    async def _calculate_timing_risk(self, opportunity: PrecisionOpportunity) -> float:
        """Calculate timing-related risk."""
        risk_factors = []
        
        # Hold time risk (longer holds = higher risk)
        hold_hours = opportunity.estimated_hold_time_hours
        if hold_hours <= 4:
            risk_factors.append(1.0)
        elif hold_hours <= 12:
            risk_factors.append(3.0)
        elif hold_hours <= 24:
            risk_factors.append(5.0)
        elif hold_hours <= 72:
            risk_factors.append(7.0)
        else:
            risk_factors.append(9.0)
        
        # Time until optimal buy window
        time_to_buy = (opportunity.optimal_buy_window_start - timezone.now()).total_seconds() / 3600
        if time_to_buy <= 1:
            risk_factors.append(2.0)  # Good timing
        elif time_to_buy <= 6:
            risk_factors.append(4.0)
        elif time_to_buy <= 24:
            risk_factors.append(6.0)
        else:
            risk_factors.append(8.0)  # Long wait increases risk
        
        return statistics.mean(risk_factors)
    
    async def _calculate_outcome_probabilities(self,
                                            opportunity: PrecisionOpportunity,
                                            price_history: List[dict]) -> Tuple[float, float, float]:
        """Calculate profit, loss, and breakeven probabilities."""
        base_success_prob = opportunity.success_probability_pct
        
        # Adjust based on historical performance
        if price_history:
            prices = [p['price'] for p in price_history]
            buy_price = opportunity.recommended_buy_price
            sell_price = opportunity.recommended_sell_price
            
            # How often did price exceed sell target?
            exceed_count = sum(1 for p in prices if p >= sell_price)
            exceed_rate = exceed_count / len(prices) * 100
            
            # How often did price fall below buy level?
            below_count = sum(1 for p in prices if p <= buy_price * 0.95)  # 5% buffer
            loss_rate = below_count / len(prices) * 100
            
            # Weighted adjustment
            historical_weight = 0.3
            profit_prob = (base_success_prob * 0.7) + (exceed_rate * historical_weight)
            loss_prob = min(100 - profit_prob, loss_rate + 10)  # Add some buffer
            breakeven_prob = 100 - profit_prob - loss_prob
        else:
            profit_prob = base_success_prob
            loss_prob = 100 - base_success_prob
            breakeven_prob = 0
        
        # Ensure probabilities sum to 100%
        total = profit_prob + loss_prob + breakeven_prob
        if total > 0:
            profit_prob = (profit_prob / total) * 100
            loss_prob = (loss_prob / total) * 100
            breakeven_prob = (breakeven_prob / total) * 100
        
        return profit_prob, loss_prob, breakeven_prob
    
    async def _optimize_position_size(self,
                                    opportunity: PrecisionOpportunity,
                                    capital_gp: int,
                                    risk_score: float,
                                    risk_tolerance: str) -> Tuple[int, int, int]:
        """Optimize position sizing using Kelly criterion and risk management."""
        
        # Base allocation limits by risk tolerance
        base_limits = {
            'conservative': 0.10,  # 10% max
            'moderate': 0.20,      # 20% max
            'aggressive': 0.35     # 35% max
        }
        
        max_allocation_pct = base_limits.get(risk_tolerance, 0.20)
        
        # Adjust for risk score (higher risk = lower allocation)
        if risk_score <= 3:
            risk_multiplier = 1.0
        elif risk_score <= 5:
            risk_multiplier = 0.8
        elif risk_score <= 7:
            risk_multiplier = 0.6
        else:
            risk_multiplier = 0.4
        
        adjusted_allocation = max_allocation_pct * risk_multiplier
        
        # Volume constraints
        max_by_volume = opportunity.daily_volume // 3  # Don't exceed 1/3 daily volume
        
        # Calculate sizes
        max_capital = int(capital_gp * adjusted_allocation)
        buy_price = opportunity.recommended_buy_price
        
        max_units_by_capital = max_capital // buy_price
        max_units_by_volume = max_by_volume
        
        recommended_size = min(max_units_by_capital, max_units_by_volume)
        max_size = int(recommended_size * 1.5)  # Allow 50% more if conditions improve
        capital_at_risk = recommended_size * buy_price
        
        return recommended_size, max_size, capital_at_risk
    
    async def _calculate_risk_levels(self,
                                   opportunity: PrecisionOpportunity,
                                   risk_score: float,
                                   price_history: List[dict]) -> Tuple[int, int]:
        """Calculate stop-loss and take-profit levels."""
        buy_price = opportunity.recommended_buy_price
        sell_price = opportunity.recommended_sell_price
        
        # Stop-loss calculation based on risk score
        if risk_score <= 3:
            stop_loss_pct = 0.03  # 3% stop loss for low risk
        elif risk_score <= 5:
            stop_loss_pct = 0.05  # 5% stop loss for medium risk
        elif risk_score <= 7:
            stop_loss_pct = 0.07  # 7% stop loss for high risk
        else:
            stop_loss_pct = 0.10  # 10% stop loss for very high risk
        
        stop_loss = int(buy_price * (1 - stop_loss_pct))
        
        # Take-profit at recommended sell price, but add buffer for high-risk items
        if risk_score > 7:
            take_profit = int(sell_price * 0.95)  # Take profits earlier for high risk
        else:
            take_profit = sell_price
        
        return stop_loss, take_profit
    
    async def _generate_risk_insights(self,
                                    opportunity: PrecisionOpportunity,
                                    risk_score: float,
                                    price_history: List[dict]) -> Tuple[List[str], List[str]]:
        """Generate risk factors and mitigation strategies."""
        risk_factors = []
        mitigations = []
        
        # Volume-based risks
        if opportunity.daily_volume < 100:
            risk_factors.append("Low trading volume may cause liquidity issues")
            mitigations.append("Use smaller position sizes and limit orders")
        
        # Volatility risks
        if len(price_history) > 10:
            prices = [p['price'] for p in price_history]
            volatility = np.std(prices) / np.mean(prices)
            if volatility > 0.2:
                risk_factors.append(f"High price volatility ({volatility:.1%})")
                mitigations.append("Use tighter stop-losses and take partial profits")
        
        # Profit margin risks
        if opportunity.expected_profit_margin_pct < 3:
            risk_factors.append("Low profit margin reduces room for error")
            mitigations.append("Monitor closely and exit quickly if price moves against position")
        
        # Timing risks
        if opportunity.estimated_hold_time_hours > 24:
            risk_factors.append("Long hold time increases market risk exposure")
            mitigations.append("Set time-based exit rules and review position daily")
        
        # Overall risk level guidance
        if risk_score > 7:
            risk_factors.append("Overall high risk score")
            mitigations.append("Consider reducing position size or finding alternative opportunities")
        
        return risk_factors, mitigations
    
    async def _analyze_item_timing(self, opportunity: PrecisionOpportunity) -> TimingAnalysis:
        """Analyze optimal timing for individual opportunity."""
        try:
            now = timezone.now()
            
            # Get historical timing data
            price_history = await self._get_extended_price_history(
                opportunity.item_id, days=self.timing_lookback_days
            )
            
            # Calculate timing scores
            volume_score = await self._calculate_volume_timing_score(price_history)
            price_score = await self._calculate_price_timing_score(price_history)
            volatility_score = await self._calculate_volatility_timing_score(price_history)
            
            # Overall timing confidence
            timing_confidence = (volume_score + price_score + volatility_score) / 3
            
            # Default timing windows (can be enhanced with more sophisticated analysis)
            best_buy_time = opportunity.optimal_buy_window_start
            best_sell_time = opportunity.optimal_sell_window_start
            worst_buy_time = now.replace(hour=12, minute=0, second=0)  # Noon (high activity)
            worst_sell_time = now.replace(hour=4, minute=0, second=0)   # 4 AM (low activity)
            
            return TimingAnalysis(
                item_id=opportunity.item_id,
                item_name=opportunity.item_name,
                best_buy_time=best_buy_time,
                best_sell_time=best_sell_time,
                worst_buy_time=worst_buy_time,
                worst_sell_time=worst_sell_time,
                timing_confidence=timing_confidence,
                historical_pattern_strength=0.7,  # Default value
                volume_pattern_score=volume_score,
                price_pattern_score=price_score,
                volatility_timing_score=volatility_score,
                entry_strategy="Gradual accumulation during low-volume periods",
                exit_strategy="Scale out during high-volume periods",
                position_scaling_strategy="25% initial, then 25% every 2 hours if price favorable",
                expected_hold_time_hours=opportunity.estimated_hold_time_hours,
                time_decay_risk=0.1,  # Low time decay for most OSRS items
                seasonal_factors=["Weekend volume patterns", "Update announcement effects"]
            )
            
        except Exception as e:
            logger.error(f"Error analyzing timing for {opportunity.item_name}: {e}")
            return None
    
    async def _calculate_volume_timing_score(self, price_history: List[dict]) -> float:
        """Calculate volume-based timing score."""
        if not price_history:
            return 0.5
        
        volumes = [p['volume'] for p in price_history if p['volume'] > 0]
        if not volumes:
            return 0.5
        
        # Simple volume consistency score
        if len(volumes) > 1:
            cv = np.std(volumes) / np.mean(volumes)
            return max(0.1, min(0.9, 1 - cv))  # Lower CV = better timing predictability
        
        return 0.5
    
    async def _calculate_price_timing_score(self, price_history: List[dict]) -> float:
        """Calculate price pattern timing score."""
        if len(price_history) < 10:
            return 0.5
        
        prices = [p['price'] for p in price_history]
        
        # Look for cyclical patterns
        price_changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        if not price_changes:
            return 0.5
        
        # Simple pattern strength based on price change consistency
        positive_changes = sum(1 for change in price_changes if change > 0)
        pattern_strength = abs(positive_changes - len(price_changes) / 2) / (len(price_changes) / 2)
        
        return min(0.9, pattern_strength)
    
    async def _calculate_volatility_timing_score(self, price_history: List[dict]) -> float:
        """Calculate volatility timing score."""
        if len(price_history) < 5:
            return 0.5
        
        prices = [p['price'] for p in price_history]
        volatility = np.std(prices) / np.mean(prices) if len(prices) > 1 else 0
        
        # Moderate volatility is best for timing (0.05 to 0.15 range)
        if 0.05 <= volatility <= 0.15:
            return 0.8
        elif volatility < 0.02:
            return 0.4  # Too stable
        elif volatility > 0.3:
            return 0.3  # Too volatile
        else:
            return 0.6  # Decent
    
    def _create_empty_portfolio(self, capital_gp: int) -> PortfolioOptimization:
        """Create empty portfolio optimization when no opportunities available."""
        return PortfolioOptimization(
            total_capital_gp=capital_gp,
            recommended_allocations={},
            portfolio_risk_score=0.0,
            expected_portfolio_return_pct=0.0,
            portfolio_sharpe_ratio=0.0,
            diversification_score=0.0,
            total_capital_at_risk_pct=0.0,
            correlation_risk=0.0,
            concentration_risk=0.0,
            rebalancing_frequency_hours=24,
            rebalancing_threshold_pct=5.0,
            optimization_reasoning=["No suitable opportunities found"]
        )
    
    async def _filter_opportunities_by_risk(self,
                                          opportunities: List[PrecisionOpportunity],
                                          risk_assessments: List[RiskAssessment],
                                          risk_tolerance: str) -> List[PrecisionOpportunity]:
        """Filter opportunities based on risk tolerance."""
        risk_limits = {
            'conservative': 5.0,
            'moderate': 7.0,
            'aggressive': 10.0
        }
        
        max_risk = risk_limits.get(risk_tolerance, 7.0)
        
        # Create risk lookup
        risk_lookup = {ra.item_id: ra.overall_risk_score for ra in risk_assessments}
        
        filtered = []
        for opp in opportunities:
            risk_score = risk_lookup.get(opp.item_id, 5.0)
            if risk_score <= max_risk:
                filtered.append(opp)
        
        return filtered[:self.max_portfolio_items]  # Limit portfolio size
    
    async def _calculate_expected_returns(self, opportunities: List[PrecisionOpportunity]) -> Dict[int, float]:
        """Calculate expected returns for each opportunity."""
        returns = {}
        for opp in opportunities:
            # Expected return = profit margin * success probability
            expected_return = (opp.expected_profit_margin_pct / 100) * (opp.success_probability_pct / 100)
            returns[opp.item_id] = expected_return
        
        return returns
    
    async def _calculate_correlation_matrix(self, opportunities: List[PrecisionOpportunity]) -> Dict[Tuple[int, int], float]:
        """Calculate simplified correlation matrix between opportunities."""
        # For simplicity, assume low correlation between different items
        # In reality, this would require extensive historical analysis
        correlations = {}
        
        for i, opp1 in enumerate(opportunities):
            for j, opp2 in enumerate(opportunities):
                if i == j:
                    correlations[(opp1.item_id, opp2.item_id)] = 1.0
                else:
                    # Assume low correlation between different items
                    correlations[(opp1.item_id, opp2.item_id)] = 0.2
        
        return correlations
    
    async def _optimize_allocations(self,
                                  opportunities: List[PrecisionOpportunity],
                                  returns: Dict[int, float],
                                  correlations: Dict[Tuple[int, int], float],
                                  capital_gp: int,
                                  risk_tolerance: str) -> Dict[int, float]:
        """Optimize portfolio allocations using simplified Markowitz approach."""
        
        if not opportunities:
            return {}
        
        # Simple equal-risk allocation with return weighting
        total_return = sum(returns.values())
        allocations = {}
        
        for opp in opportunities:
            # Base allocation on expected return
            if total_return > 0:
                base_weight = returns[opp.item_id] / total_return
            else:
                base_weight = 1.0 / len(opportunities)
            
            # Adjust for volume constraints
            max_capital_for_item = opp.daily_volume * opp.recommended_buy_price * 0.3  # 30% of daily volume
            max_allocation_pct = min(0.25, max_capital_for_item / capital_gp)  # Cap at 25%
            
            final_allocation = min(base_weight, max_allocation_pct)
            allocations[opp.item_id] = final_allocation
        
        # Normalize to ensure allocations sum to reasonable total
        total_allocation = sum(allocations.values())
        target_allocation = 0.8  # Use 80% of capital, keep 20% liquid
        
        if total_allocation > 0:
            scale_factor = target_allocation / total_allocation
            allocations = {k: v * scale_factor for k, v in allocations.items()}
        
        return allocations
    
    async def _calculate_portfolio_metrics(self,
                                         allocations: Dict[int, float],
                                         opportunities: List[PrecisionOpportunity],
                                         returns: Dict[int, float],
                                         correlations: Dict[Tuple[int, int], float]) -> Dict:
        """Calculate portfolio-level metrics."""
        
        if not allocations:
            return {
                'portfolio_risk_score': 0.0,
                'expected_portfolio_return_pct': 0.0,
                'portfolio_sharpe_ratio': 0.0,
                'diversification_score': 0.0,
                'total_capital_at_risk_pct': 0.0,
                'correlation_risk': 0.0,
                'concentration_risk': 0.0,
                'rebalancing_frequency_hours': 24,
                'rebalancing_threshold_pct': 5.0,
                'optimization_reasoning': []
            }
        
        # Expected portfolio return
        expected_return = sum(allocations[item_id] * returns[item_id] 
                            for item_id in allocations.keys())
        
        # Portfolio risk (simplified)
        portfolio_risk = statistics.mean([opp.risk_level == 'high' for opp in opportunities 
                                        if opp.item_id in allocations]) * 10
        
        # Diversification score
        diversification = min(10.0, len(allocations) * 2)  # More assets = better diversification
        
        # Concentration risk
        max_allocation = max(allocations.values()) if allocations else 0
        concentration_risk = max_allocation * 10  # Higher concentration = higher risk
        
        return {
            'portfolio_risk_score': portfolio_risk,
            'expected_portfolio_return_pct': expected_return * 100,
            'portfolio_sharpe_ratio': max(0, expected_return / max(portfolio_risk / 10, 0.1)),
            'diversification_score': diversification,
            'total_capital_at_risk_pct': sum(allocations.values()) * 100,
            'correlation_risk': 0.2,  # Simplified
            'concentration_risk': concentration_risk,
            'rebalancing_frequency_hours': 12,
            'rebalancing_threshold_pct': 5.0,
            'optimization_reasoning': [
                f"Allocated across {len(allocations)} opportunities",
                f"Expected portfolio return: {expected_return * 100:.1f}%",
                f"Diversification score: {diversification:.1f}/10"
            ]
        }
    
    async def _create_single_asset_portfolio(self,
                                           opportunity: PrecisionOpportunity,
                                           capital_gp: int,
                                           risk_tolerance: str) -> PortfolioOptimization:
        """Create portfolio with single opportunity."""
        allocation_pct = {'conservative': 0.15, 'moderate': 0.25, 'aggressive': 0.4}
        alloc = allocation_pct.get(risk_tolerance, 0.25)
        
        return PortfolioOptimization(
            total_capital_gp=capital_gp,
            recommended_allocations={opportunity.item_id: alloc},
            portfolio_risk_score=5.0,  # Medium risk for single asset
            expected_portfolio_return_pct=opportunity.expected_profit_margin_pct * alloc,
            portfolio_sharpe_ratio=0.5,
            diversification_score=1.0,  # Low diversification
            total_capital_at_risk_pct=alloc * 100,
            correlation_risk=0.0,  # No correlation with single asset
            concentration_risk=alloc * 10,
            rebalancing_frequency_hours=24,
            rebalancing_threshold_pct=10.0,
            optimization_reasoning=[
                "Single opportunity portfolio",
                "Consider diversifying with additional opportunities"
            ]
        )