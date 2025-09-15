"""
Comprehensive risk analysis service for high alch strategies.
"""

import math
from typing import Dict, List, Tuple, Optional
from datetime import timedelta
from django.utils import timezone
from dataclasses import dataclass

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from .models import GoalPlan, Strategy, StrategyItem


@dataclass
class RiskFactor:
    """Represents a specific risk factor."""
    factor_type: str
    severity: str  # 'low', 'medium', 'high'
    description: str
    impact_score: float  # 0.0 to 1.0
    mitigation_advice: str


@dataclass
class StrategyRiskProfile:
    """Complete risk profile for a strategy."""
    overall_risk_score: float
    risk_level: str
    confidence_score: float
    risk_factors: List[RiskFactor]
    market_risks: Dict[str, float]
    time_risks: Dict[str, float]
    liquidity_risks: Dict[str, float]
    recommendations: List[str]


class RiskAnalyzer:
    """
    Comprehensive risk analysis for goal planning strategies.
    """
    
    def __init__(self):
        self.risk_weights = {
            'market_volatility': 0.25,
            'liquidity_risk': 0.20,
            'time_constraint': 0.20,
            'concentration_risk': 0.15,
            'capital_risk': 0.10,
            'execution_risk': 0.10
        }
    
    def analyze_strategy_risk(self, strategy: Strategy) -> StrategyRiskProfile:
        """
        Perform comprehensive risk analysis on a strategy.
        """
        risk_factors = []
        market_risks = {}
        time_risks = {}
        liquidity_risks = {}
        
        # Analyze each risk category
        market_risks = self._analyze_market_risks(strategy)
        time_risks = self._analyze_time_risks(strategy)
        liquidity_risks = self._analyze_liquidity_risks(strategy)
        concentration_risk = self._analyze_concentration_risk(strategy)
        capital_risk = self._analyze_capital_risk(strategy)
        execution_risk = self._analyze_execution_risk(strategy)
        
        # Collect all risk factors
        risk_factors.extend(self._market_risks_to_factors(market_risks))
        risk_factors.extend(self._time_risks_to_factors(time_risks))
        risk_factors.extend(self._liquidity_risks_to_factors(liquidity_risks))
        risk_factors.append(self._concentration_risk_to_factor(concentration_risk))
        risk_factors.append(self._capital_risk_to_factor(capital_risk))
        risk_factors.append(self._execution_risk_to_factor(execution_risk))
        
        # Calculate overall risk score
        overall_risk = self._calculate_overall_risk(
            market_risks, time_risks, liquidity_risks,
            concentration_risk, capital_risk, execution_risk
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_risk)
        
        # Calculate confidence in the analysis
        confidence = self._calculate_analysis_confidence(strategy)
        
        # Generate recommendations
        recommendations = self._generate_risk_recommendations(risk_factors, overall_risk)
        
        return StrategyRiskProfile(
            overall_risk_score=overall_risk,
            risk_level=risk_level,
            confidence_score=confidence,
            risk_factors=risk_factors,
            market_risks=market_risks,
            time_risks=time_risks,
            liquidity_risks=liquidity_risks,
            recommendations=recommendations
        )
    
    def _analyze_market_risks(self, strategy: Strategy) -> Dict[str, float]:
        """Analyze market-related risks."""
        risks = {}
        
        strategy_items = strategy.items.all()
        if not strategy_items:
            return {'no_items': 1.0}
        
        # Price volatility risk
        volatilities = [item.price_volatility for item in strategy_items]
        avg_volatility = sum(volatilities) / len(volatilities)
        risks['price_volatility'] = min(avg_volatility, 1.0)
        
        # Market impact risk (based on volume requirements)
        total_volume_impact = 0
        for item in strategy_items:
            daily_volume = item.daily_volume or 1000
            required_volume = item.items_to_buy
            volume_impact = min(required_volume / daily_volume, 1.0)
            total_volume_impact += volume_impact * (item.allocation_percentage / 100)
        
        risks['market_impact'] = total_volume_impact
        
        # Correlation risk (items moving together)
        if len(strategy_items) > 1:
            # Simplified correlation risk based on price similarity
            price_ranges = []
            for item in strategy_items:
                price_ranges.append(item.buy_price_when_calculated)
            
            price_variance = self._calculate_variance(price_ranges)
            avg_price = sum(price_ranges) / len(price_ranges)
            
            if avg_price > 0:
                correlation_risk = 1.0 - min(price_variance / (avg_price ** 2), 1.0)
            else:
                correlation_risk = 0.5
            
            risks['correlation_risk'] = correlation_risk
        else:
            risks['correlation_risk'] = 0.0
        
        return risks
    
    def _analyze_time_risks(self, strategy: Strategy) -> Dict[str, float]:
        """Analyze time-related risks."""
        risks = {}
        
        # Timeline feasibility risk
        estimated_days = strategy.estimated_days
        goal_plan = strategy.goal_plan
        
        if goal_plan.preferred_timeframe_days:
            timeline_pressure = estimated_days / goal_plan.preferred_timeframe_days
            risks['timeline_pressure'] = min(timeline_pressure - 1.0, 1.0) if timeline_pressure > 1.0 else 0.0
        else:
            risks['timeline_pressure'] = 0.0
        
        # GE limit constraint risk
        ge_constrained_items = strategy.items.filter(
            estimated_buy_time_hours__gte=24
        ).count()
        total_items = strategy.items.count()
        
        if total_items > 0:
            risks['ge_constraint'] = ge_constrained_items / total_items
        else:
            risks['ge_constraint'] = 0.0
        
        # Market timing risk (longer strategies are riskier)
        if estimated_days > 30:
            risks['market_timing'] = 0.8
        elif estimated_days > 7:
            risks['market_timing'] = 0.4
        else:
            risks['market_timing'] = 0.1
        
        return risks
    
    def _analyze_liquidity_risks(self, strategy: Strategy) -> Dict[str, float]:
        """Analyze liquidity-related risks."""
        risks = {}
        
        strategy_items = strategy.items.all()
        if not strategy_items:
            return {'no_items': 1.0}
        
        # Volume adequacy risk
        total_volume_risk = 0
        for item in strategy_items:
            daily_volume = item.daily_volume or 1000
            required_daily = item.items_to_buy / max(strategy.estimated_days, 1)
            
            volume_adequacy = required_daily / daily_volume if daily_volume > 0 else 1.0
            volume_risk = min(volume_adequacy, 1.0)
            
            total_volume_risk += volume_risk * (item.allocation_percentage / 100)
        
        risks['volume_adequacy'] = total_volume_risk
        
        # Bid-ask spread risk (estimated based on item value)
        spread_risks = []
        for item in strategy_items:
            buy_price = item.buy_price_when_calculated
            # Higher value items typically have higher spreads
            if buy_price > 1000000:  # 1M+
                spread_risk = 0.8
            elif buy_price > 100000:  # 100K+
                spread_risk = 0.5
            elif buy_price > 10000:  # 10K+
                spread_risk = 0.3
            else:
                spread_risk = 0.1
            
            spread_risks.append(spread_risk)
        
        risks['bid_ask_spread'] = sum(spread_risks) / len(spread_risks)
        
        return risks
    
    def _analyze_concentration_risk(self, strategy: Strategy) -> float:
        """Analyze portfolio concentration risk."""
        strategy_items = strategy.items.all()
        if not strategy_items:
            return 1.0
        
        allocations = [item.allocation_percentage for item in strategy_items]
        
        # Calculate Herfindahl-Hirschman Index (HHI) for concentration
        hhi = sum((allocation / 100) ** 2 for allocation in allocations)
        
        # HHI ranges from 1/n (perfect diversification) to 1 (complete concentration)
        # Convert to risk score: higher HHI = higher concentration risk
        return hhi
    
    def _analyze_capital_risk(self, strategy: Strategy) -> float:
        """Analyze capital adequacy and leverage risk."""
        goal_plan = strategy.goal_plan
        
        # Capital adequacy
        available_capital = goal_plan.current_gp
        required_investment = strategy.required_initial_investment
        
        if available_capital <= 0:
            return 1.0  # Maximum risk if no capital
        
        capital_utilization = required_investment / available_capital
        
        # Higher utilization = higher risk
        if capital_utilization > 1.0:
            return 1.0  # Cannot execute - maximum risk
        elif capital_utilization > 0.9:
            return 0.8  # Very high utilization
        elif capital_utilization > 0.7:
            return 0.5  # High utilization
        else:
            return capital_utilization * 0.5  # Proportional risk
    
    def _analyze_execution_risk(self, strategy: Strategy) -> float:
        """Analyze execution complexity and operational risk."""
        strategy_items = strategy.items.all()
        if not strategy_items:
            return 1.0
        
        complexity_factors = []
        
        # Number of items complexity
        item_count = strategy_items.count()
        if item_count > 10:
            complexity_factors.append(0.8)
        elif item_count > 5:
            complexity_factors.append(0.5)
        else:
            complexity_factors.append(0.2)
        
        # GE slot management complexity
        concurrent_items = min(item_count, 8)  # Max 8 GE slots
        if concurrent_items >= 8:
            complexity_factors.append(0.7)
        elif concurrent_items >= 5:
            complexity_factors.append(0.4)
        else:
            complexity_factors.append(0.2)
        
        # Price monitoring complexity
        total_volatility = sum(item.price_volatility for item in strategy_items)
        avg_volatility = total_volatility / item_count
        complexity_factors.append(avg_volatility)
        
        return sum(complexity_factors) / len(complexity_factors)
    
    def _calculate_overall_risk(self, market_risks: Dict, time_risks: Dict,
                               liquidity_risks: Dict, concentration_risk: float,
                               capital_risk: float, execution_risk: float) -> float:
        """Calculate weighted overall risk score."""
        
        # Aggregate category scores
        market_score = sum(market_risks.values()) / len(market_risks) if market_risks else 0
        time_score = sum(time_risks.values()) / len(time_risks) if time_risks else 0
        liquidity_score = sum(liquidity_risks.values()) / len(liquidity_risks) if liquidity_risks else 0
        
        # Apply weights
        overall_risk = (
            market_score * self.risk_weights['market_volatility'] +
            liquidity_score * self.risk_weights['liquidity_risk'] +
            time_score * self.risk_weights['time_constraint'] +
            concentration_risk * self.risk_weights['concentration_risk'] +
            capital_risk * self.risk_weights['capital_risk'] +
            execution_risk * self.risk_weights['execution_risk']
        )
        
        return min(overall_risk, 1.0)
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Convert risk score to categorical risk level."""
        if risk_score < 0.3:
            return 'low'
        elif risk_score < 0.6:
            return 'medium'
        else:
            return 'high'
    
    def _calculate_analysis_confidence(self, strategy: Strategy) -> float:
        """Calculate confidence in the risk analysis."""
        confidence_factors = []
        
        # Data availability confidence
        strategy_items = strategy.items.all()
        items_with_volume_data = strategy_items.filter(daily_volume__gt=0).count()
        if strategy_items.count() > 0:
            data_confidence = items_with_volume_data / strategy_items.count()
        else:
            data_confidence = 0.0
        confidence_factors.append(data_confidence)
        
        # Price data recency confidence
        recent_calculations = ProfitCalculation.objects.filter(
            item__in=[item.item for item in strategy_items],
            created_at__gte=timezone.now() - timedelta(hours=2)
        ).count()
        
        recency_confidence = min(recent_calculations / strategy_items.count(), 1.0) if strategy_items.count() > 0 else 0
        confidence_factors.append(recency_confidence)
        
        # Strategy complexity confidence (simpler = more confident)
        complexity_confidence = max(1.0 - (strategy_items.count() / 10), 0.3)
        confidence_factors.append(complexity_confidence)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _generate_risk_recommendations(self, risk_factors: List[RiskFactor],
                                     overall_risk: float) -> List[str]:
        """Generate actionable risk mitigation recommendations."""
        recommendations = []
        
        # High-severity factor recommendations
        high_severity_factors = [f for f in risk_factors if f.severity == 'high']
        for factor in high_severity_factors:
            recommendations.append(factor.mitigation_advice)
        
        # Overall risk recommendations
        if overall_risk > 0.7:
            recommendations.append("Consider reducing position sizes or extending timeline")
            recommendations.append("Implement strict stop-loss rules for price-volatile items")
        elif overall_risk > 0.4:
            recommendations.append("Monitor market conditions closely during execution")
            recommendations.append("Consider diversifying across more items")
        
        # Remove duplicates
        return list(set(recommendations))
    
    def _market_risks_to_factors(self, market_risks: Dict) -> List[RiskFactor]:
        """Convert market risk scores to RiskFactor objects."""
        factors = []
        
        for risk_type, score in market_risks.items():
            if score > 0.7:
                severity = 'high'
            elif score > 0.4:
                severity = 'medium'
            else:
                severity = 'low'
            
            descriptions = {
                'price_volatility': f"Items show high price volatility (score: {score:.2f})",
                'market_impact': f"Strategy may significantly impact item prices (score: {score:.2f})",
                'correlation_risk': f"Items may move together in adverse conditions (score: {score:.2f})"
            }
            
            mitigations = {
                'price_volatility': "Monitor prices closely and adjust quantities if volatility increases",
                'market_impact': "Spread purchases over longer time period to reduce market impact",
                'correlation_risk': "Consider adding items from different categories or price ranges"
            }
            
            factors.append(RiskFactor(
                factor_type=f"market_{risk_type}",
                severity=severity,
                description=descriptions.get(risk_type, f"Market risk: {risk_type}"),
                impact_score=score,
                mitigation_advice=mitigations.get(risk_type, "Monitor market conditions")
            ))
        
        return factors
    
    def _time_risks_to_factors(self, time_risks: Dict) -> List[RiskFactor]:
        """Convert time risk scores to RiskFactor objects."""
        factors = []
        
        for risk_type, score in time_risks.items():
            if score > 0.7:
                severity = 'high'
            elif score > 0.4:
                severity = 'medium'
            else:
                severity = 'low'
            
            descriptions = {
                'timeline_pressure': f"Strategy may not complete within preferred timeframe (score: {score:.2f})",
                'ge_constraint': f"GE buy limits significantly constrain acquisition speed (score: {score:.2f})",
                'market_timing': f"Extended timeline increases market timing risk (score: {score:.2f})"
            }
            
            mitigations = {
                'timeline_pressure': "Extend target timeline or reduce scope",
                'ge_constraint': "Consider items with higher GE limits or accept longer timeline",
                'market_timing': "Implement regular strategy reviews and adjustment triggers"
            }
            
            factors.append(RiskFactor(
                factor_type=f"time_{risk_type}",
                severity=severity,
                description=descriptions.get(risk_type, f"Time risk: {risk_type}"),
                impact_score=score,
                mitigation_advice=mitigations.get(risk_type, "Monitor timing constraints")
            ))
        
        return factors
    
    def _liquidity_risks_to_factors(self, liquidity_risks: Dict) -> List[RiskFactor]:
        """Convert liquidity risk scores to RiskFactor objects."""
        factors = []
        
        for risk_type, score in liquidity_risks.items():
            if score > 0.7:
                severity = 'high'
            elif score > 0.4:
                severity = 'medium'
            else:
                severity = 'low'
            
            descriptions = {
                'volume_adequacy': f"Market volume may be insufficient for strategy (score: {score:.2f})",
                'bid_ask_spread': f"Trading costs may be higher due to spreads (score: {score:.2f})"
            }
            
            mitigations = {
                'volume_adequacy': "Reduce quantities or extend acquisition timeline",
                'bid_ask_spread': "Use limit orders and avoid market orders"
            }
            
            factors.append(RiskFactor(
                factor_type=f"liquidity_{risk_type}",
                severity=severity,
                description=descriptions.get(risk_type, f"Liquidity risk: {risk_type}"),
                impact_score=score,
                mitigation_advice=mitigations.get(risk_type, "Monitor liquidity conditions")
            ))
        
        return factors
    
    def _concentration_risk_to_factor(self, concentration_risk: float) -> RiskFactor:
        """Convert concentration risk to RiskFactor."""
        if concentration_risk > 0.7:
            severity = 'high'
        elif concentration_risk > 0.4:
            severity = 'medium'
        else:
            severity = 'low'
        
        return RiskFactor(
            factor_type="concentration",
            severity=severity,
            description=f"Portfolio is concentrated in few items (HHI: {concentration_risk:.2f})",
            impact_score=concentration_risk,
            mitigation_advice="Diversify across more items or categories"
        )
    
    def _capital_risk_to_factor(self, capital_risk: float) -> RiskFactor:
        """Convert capital risk to RiskFactor."""
        if capital_risk > 0.8:
            severity = 'high'
        elif capital_risk > 0.5:
            severity = 'medium'
        else:
            severity = 'low'
        
        return RiskFactor(
            factor_type="capital",
            severity=severity,
            description=f"High capital utilization increases risk (score: {capital_risk:.2f})",
            impact_score=capital_risk,
            mitigation_advice="Consider reducing position sizes or securing additional capital"
        )
    
    def _execution_risk_to_factor(self, execution_risk: float) -> RiskFactor:
        """Convert execution risk to RiskFactor."""
        if execution_risk > 0.7:
            severity = 'high'
        elif execution_risk > 0.4:
            severity = 'medium'
        else:
            severity = 'low'
        
        return RiskFactor(
            factor_type="execution",
            severity=severity,
            description=f"Strategy complexity increases execution risk (score: {execution_risk:.2f})",
            impact_score=execution_risk,
            mitigation_advice="Simplify strategy or implement systematic execution procedures"
        )
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    def compare_strategies_risk(self, strategies: List[Strategy]) -> Dict:
        """Compare risk profiles of multiple strategies."""
        if not strategies:
            return {}
        
        risk_profiles = []
        for strategy in strategies:
            profile = self.analyze_strategy_risk(strategy)
            risk_profiles.append({
                'strategy_name': strategy.name,
                'strategy_id': strategy.id,
                'overall_risk_score': profile.overall_risk_score,
                'risk_level': profile.risk_level,
                'confidence_score': profile.confidence_score,
                'major_risk_factors': [f.factor_type for f in profile.risk_factors if f.severity == 'high']
            })
        
        # Sort by risk score
        risk_profiles.sort(key=lambda x: x['overall_risk_score'])
        
        return {
            'strategy_risk_profiles': risk_profiles,
            'lowest_risk_strategy': risk_profiles[0]['strategy_name'] if risk_profiles else None,
            'highest_risk_strategy': risk_profiles[-1]['strategy_name'] if risk_profiles else None,
            'average_risk_score': sum(p['overall_risk_score'] for p in risk_profiles) / len(risk_profiles)
        }