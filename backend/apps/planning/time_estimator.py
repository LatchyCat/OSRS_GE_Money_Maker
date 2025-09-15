"""
Time estimation service for high alch strategies considering GE limits and market dynamics.
"""

import math
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from django.utils import timezone

from apps.items.models import Item
from apps.prices.models import PriceSnapshot


@dataclass
class TimeEstimate:
    """Represents time estimation for acquiring items."""
    item_name: str
    quantity_needed: int
    ge_limit: int
    estimated_hours: float
    estimated_days: float
    bottleneck_factor: float
    confidence_level: float
    notes: str


@dataclass
class StrategyTimeBreakdown:
    """Detailed time breakdown for a strategy."""
    total_estimated_hours: float
    total_estimated_days: float
    critical_path_item: str
    parallel_acquisition_hours: float
    sequential_acquisition_hours: float
    ge_limit_constrained: bool
    item_estimates: List[TimeEstimate]


class TimeEstimationService:
    """
    Service for estimating time to complete high alch strategies.
    """
    
    def __init__(self):
        self.ge_reset_hours = 4  # GE buy limits reset every 4 hours
        self.resets_per_day = 24 / self.ge_reset_hours
        self.trading_efficiency = 0.9  # 90% efficiency assuming some failed purchases
    
    def estimate_strategy_time(self, strategy_items: List[Dict]) -> StrategyTimeBreakdown:
        """
        Estimate total time for a strategy considering parallel vs sequential acquisition.
        
        Args:
            strategy_items: List of dictionaries with item data and quantities
        
        Returns:
            StrategyTimeBreakdown with detailed time analysis
        """
        if not strategy_items:
            return StrategyTimeBreakdown(0, 0, "", 0, 0, False, [])
        
        item_estimates = []
        max_time_hours = 0
        total_sequential_hours = 0
        critical_path_item = ""
        ge_constrained = False
        
        for item_data in strategy_items:
            estimate = self._estimate_item_acquisition_time(
                item_data['item'],
                item_data['quantity'],
                item_data.get('buy_price', 0),
                item_data.get('daily_volume', 1000)
            )
            
            item_estimates.append(estimate)
            total_sequential_hours += estimate.estimated_hours
            
            # Track critical path (longest single item)
            if estimate.estimated_hours > max_time_hours:
                max_time_hours = estimate.estimated_hours
                critical_path_item = estimate.item_name
            
            # Check if any item is GE limit constrained
            if estimate.bottleneck_factor > 0.7:
                ge_constrained = True
        
        # Calculate parallel acquisition time (items can be bought simultaneously)
        parallel_hours = self._calculate_parallel_acquisition_time(item_estimates)
        
        return StrategyTimeBreakdown(
            total_estimated_hours=parallel_hours,
            total_estimated_days=parallel_hours / 24,
            critical_path_item=critical_path_item,
            parallel_acquisition_hours=parallel_hours,
            sequential_acquisition_hours=total_sequential_hours,
            ge_limit_constrained=ge_constrained,
            item_estimates=item_estimates
        )
    
    def _estimate_item_acquisition_time(self, item: Item, quantity: int, 
                                      buy_price: int, daily_volume: int) -> TimeEstimate:
        """
        Estimate time to acquire a specific quantity of an item.
        """
        ge_limit = item.ge_limit or 8  # Default GE limit if not set
        item_name = item.name
        
        # Calculate theoretical maximum per day based on GE limits
        theoretical_daily_max = ge_limit * self.resets_per_day * self.trading_efficiency
        
        # Calculate market-constrained daily max
        # Conservative estimate: don't try to buy more than 5% of daily volume
        market_daily_max = daily_volume * 0.05
        
        # Effective daily limit is the minimum of theoretical and market constraints
        effective_daily_limit = min(theoretical_daily_max, market_daily_max)
        
        # Calculate time needed
        if effective_daily_limit <= 0:
            estimated_days = float('inf')
            estimated_hours = float('inf')
            confidence = 0.0
            bottleneck_factor = 1.0
            notes = "Cannot acquire - no GE limit or volume data"
        else:
            estimated_days = quantity / effective_daily_limit
            estimated_hours = estimated_days * 24
            
            # Calculate confidence based on various factors
            confidence = self._calculate_confidence(
                item, quantity, ge_limit, daily_volume, buy_price
            )
            
            # Calculate bottleneck factor (how constrained this item is)
            bottleneck_factor = min(theoretical_daily_max / market_daily_max, 1.0)
            
            # Generate notes
            notes = self._generate_acquisition_notes(
                quantity, ge_limit, daily_volume, theoretical_daily_max, market_daily_max
            )
        
        return TimeEstimate(
            item_name=item_name,
            quantity_needed=quantity,
            ge_limit=ge_limit,
            estimated_hours=estimated_hours,
            estimated_days=estimated_days,
            bottleneck_factor=bottleneck_factor,
            confidence_level=confidence,
            notes=notes
        )
    
    def _calculate_parallel_acquisition_time(self, item_estimates: List[TimeEstimate]) -> float:
        """
        Calculate time for parallel acquisition of multiple items.
        
        Since players can have multiple GE slots active simultaneously,
        the total time is dominated by the longest acquisition time.
        """
        if not item_estimates:
            return 0.0
        
        # Find the critical path (longest acquisition time)
        max_time = max(estimate.estimated_hours for estimate in item_estimates 
                      if estimate.estimated_hours != float('inf'))
        
        # Add some overhead for managing multiple concurrent trades
        overhead_factor = 1.1  # 10% overhead
        
        return max_time * overhead_factor
    
    def _calculate_confidence(self, item: Item, quantity: int, ge_limit: int, 
                            daily_volume: int, buy_price: int) -> float:
        """
        Calculate confidence level for time estimate based on multiple factors.
        """
        confidence_factors = []
        
        # Factor 1: GE limit availability (higher limit = higher confidence)
        if ge_limit > 0:
            ge_confidence = min(ge_limit / 100, 1.0)  # Normalize around 100 limit
        else:
            ge_confidence = 0.1  # Low confidence for unknown limits
        confidence_factors.append(ge_confidence)
        
        # Factor 2: Market volume (higher volume = higher confidence)
        if daily_volume > 0:
            volume_confidence = min(daily_volume / 1000, 1.0)  # Normalize around 1000 volume
        else:
            volume_confidence = 0.3  # Medium confidence for unknown volume
        confidence_factors.append(volume_confidence)
        
        # Factor 3: Price stability (check recent price history)
        price_confidence = self._calculate_price_stability_confidence(item)
        confidence_factors.append(price_confidence)
        
        # Factor 4: Quantity reasonableness (very large quantities have lower confidence)
        quantity_confidence = self._calculate_quantity_confidence(quantity, ge_limit)
        confidence_factors.append(quantity_confidence)
        
        # Factor 5: Item liquidity (popular items are more predictable)
        liquidity_confidence = self._calculate_liquidity_confidence(item, buy_price)
        confidence_factors.append(liquidity_confidence)
        
        # Calculate weighted average
        weights = [0.25, 0.25, 0.2, 0.15, 0.15]  # Sum to 1.0
        weighted_confidence = sum(f * w for f, w in zip(confidence_factors, weights))
        
        return min(max(weighted_confidence, 0.0), 1.0)  # Clamp to [0, 1]
    
    def _calculate_price_stability_confidence(self, item: Item) -> float:
        """Calculate confidence based on price stability."""
        try:
            # Get recent price data
            recent_prices = PriceSnapshot.objects.filter(
                item=item,
                timestamp__gte=timezone.now() - timedelta(days=7)
            ).values_list('buy_price', flat=True).order_by('timestamp')
            
            if len(recent_prices) < 2:
                return 0.5  # Medium confidence for insufficient data
            
            prices = list(recent_prices)
            avg_price = sum(prices) / len(prices)
            
            if avg_price <= 0:
                return 0.1  # Low confidence for zero prices
            
            # Calculate coefficient of variation
            variance = sum((price - avg_price) ** 2 for price in prices) / len(prices)
            std_dev = variance ** 0.5
            coef_variation = std_dev / avg_price
            
            # Lower variation = higher confidence
            stability_confidence = max(1.0 - coef_variation * 2, 0.1)
            
            return stability_confidence
        
        except Exception:
            return 0.5  # Medium confidence on error
    
    def _calculate_quantity_confidence(self, quantity: int, ge_limit: int) -> float:
        """Calculate confidence based on quantity reasonableness."""
        if ge_limit <= 0:
            return 0.5
        
        # Calculate how many days at full GE limit
        days_at_full_limit = quantity / (ge_limit * self.resets_per_day)
        
        # Reasonable quantities have higher confidence
        if days_at_full_limit <= 1:
            return 0.9  # Very confident for 1-day acquisitions
        elif days_at_full_limit <= 7:
            return 0.8  # Good confidence for 1-week acquisitions
        elif days_at_full_limit <= 30:
            return 0.6  # Medium confidence for 1-month acquisitions
        else:
            return 0.3  # Low confidence for very long acquisitions
    
    def _calculate_liquidity_confidence(self, item: Item, buy_price: int) -> float:
        """Calculate confidence based on item liquidity indicators."""
        # Higher value items tend to have lower liquidity
        if buy_price > 1000000:  # 1M+
            return 0.4
        elif buy_price > 100000:  # 100K+
            return 0.6
        elif buy_price > 10000:  # 10K+
            return 0.8
        else:
            return 0.9  # High confidence for low-value items
    
    def _generate_acquisition_notes(self, quantity: int, ge_limit: int, daily_volume: int,
                                  theoretical_max: float, market_max: float) -> str:
        """Generate human-readable notes about acquisition challenges."""
        notes = []
        
        # GE limit analysis
        days_at_ge_limit = quantity / (ge_limit * self.resets_per_day) if ge_limit > 0 else float('inf')
        if days_at_ge_limit > 30:
            notes.append(f"Very long acquisition time due to GE limits ({days_at_ge_limit:.1f} days at max limit)")
        elif days_at_ge_limit > 7:
            notes.append(f"Extended acquisition time due to GE limits ({days_at_ge_limit:.1f} days)")
        
        # Market volume analysis
        market_share = (quantity / daily_volume * 100) if daily_volume > 0 else 0
        if market_share > 10:
            notes.append(f"High market impact - requesting {market_share:.1f}% of daily volume")
        elif market_share > 5:
            notes.append("Moderate market impact - may affect prices")
        
        # Bottleneck identification
        if theoretical_max > market_max * 2:
            notes.append("Market volume is the limiting factor")
        elif market_max > theoretical_max * 2:
            notes.append("GE buy limit is the limiting factor")
        else:
            notes.append("Balanced constraint between GE limits and market volume")
        
        return "; ".join(notes) if notes else "Standard acquisition timeline expected"
    
    def estimate_goal_completion_time(self, strategies: List[Dict]) -> Dict[str, float]:
        """
        Estimate completion time for different strategies.
        
        Returns:
            Dictionary mapping strategy names to estimated days
        """
        strategy_times = {}
        
        for strategy_data in strategies:
            strategy_name = strategy_data.get('name', 'Unknown Strategy')
            items = strategy_data.get('items', [])
            
            time_breakdown = self.estimate_strategy_time(items)
            strategy_times[strategy_name] = time_breakdown.total_estimated_days
        
        return strategy_times
    
    def optimize_acquisition_schedule(self, item_estimates: List[TimeEstimate]) -> List[Dict]:
        """
        Create an optimized schedule for acquiring items.
        
        Returns:
            List of schedule entries with timing and priorities
        """
        if not item_estimates:
            return []
        
        # Sort items by acquisition time (shortest first)
        sorted_estimates = sorted(item_estimates, key=lambda x: x.estimated_hours)
        
        schedule = []
        current_time = 0
        
        for i, estimate in enumerate(sorted_estimates):
            # Calculate start and end times
            start_time = current_time
            end_time = start_time + estimate.estimated_hours
            
            # Determine priority based on critical path analysis
            is_critical = estimate.estimated_hours == max(e.estimated_hours for e in item_estimates)
            
            schedule_entry = {
                'item_name': estimate.item_name,
                'start_hour': start_time,
                'end_hour': end_time,
                'duration_hours': estimate.estimated_hours,
                'is_critical_path': is_critical,
                'confidence': estimate.confidence_level,
                'notes': estimate.notes,
                'can_parallel': True if i < 8 else False,  # Assume max 8 GE slots
            }
            
            schedule.append(schedule_entry)
        
        return schedule
    
    def calculate_time_risk_analysis(self, time_breakdown: StrategyTimeBreakdown) -> Dict:
        """
        Analyze time-related risks for a strategy.
        
        Returns:
            Dictionary with risk analysis metrics
        """
        if not time_breakdown.item_estimates:
            return {'overall_risk': 'unknown', 'risk_factors': []}
        
        risk_factors = []
        risk_score = 0
        
        # Analyze each item for time risks
        for estimate in time_breakdown.item_estimates:
            # High quantity risk
            if estimate.estimated_days > 30:
                risk_factors.append(f"{estimate.item_name}: Very long acquisition time")
                risk_score += 0.3
            
            # Low confidence risk
            if estimate.confidence_level < 0.5:
                risk_factors.append(f"{estimate.item_name}: Low confidence in estimate")
                risk_score += 0.2
            
            # Market bottleneck risk
            if estimate.bottleneck_factor > 0.8:
                risk_factors.append(f"{estimate.item_name}: Severe market constraints")
                risk_score += 0.2
        
        # GE limit constraint risk
        if time_breakdown.ge_limit_constrained:
            risk_factors.append("Strategy heavily constrained by GE buy limits")
            risk_score += 0.2
        
        # Critical path dependency risk
        if len(time_breakdown.item_estimates) > 1:
            critical_item_time = max(e.estimated_hours for e in time_breakdown.item_estimates)
            avg_item_time = sum(e.estimated_hours for e in time_breakdown.item_estimates) / len(time_breakdown.item_estimates)
            
            if critical_item_time > avg_item_time * 3:
                risk_factors.append("High dependency on single critical path item")
                risk_score += 0.1
        
        # Determine overall risk level
        if risk_score < 0.3:
            risk_level = 'low'
        elif risk_score < 0.6:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        return {
            'overall_risk': risk_level,
            'risk_score': min(risk_score, 1.0),
            'risk_factors': risk_factors,
            'recommended_actions': self._generate_risk_mitigation_actions(risk_factors)
        }
    
    def _generate_risk_mitigation_actions(self, risk_factors: List[str]) -> List[str]:
        """Generate recommended actions to mitigate time risks."""
        actions = []
        
        for factor in risk_factors:
            if "Very long acquisition" in factor:
                actions.append("Consider breaking into smaller goals or finding alternative items")
            elif "Low confidence" in factor:
                actions.append("Monitor market conditions closely and have backup items ready")
            elif "market constraints" in factor:
                actions.append("Consider spreading purchases over longer time period")
            elif "GE buy limits" in factor:
                actions.append("Plan for extended timeline and set realistic expectations")
            elif "critical path" in factor:
                actions.append("Have contingency plans for alternative items")
        
        # Remove duplicates
        return list(set(actions))