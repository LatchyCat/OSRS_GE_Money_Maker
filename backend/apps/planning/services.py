"""
Core planning services for goal-based high alch strategy generation.
This module contains the main algorithms for calculating optimal strategies
to reach user wealth goals through high alching items.
"""

import asyncio
import logging
import math
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from django.db import transaction
from django.db.models import Q, F, Avg, Max, Min, Count
from django.utils import timezone
from asgiref.sync import sync_to_async

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from .models import GoalPlan, Strategy, StrategyItem, ProgressUpdate, StrategyRevision

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Available strategy types for goal planning."""
    MAX_PROFIT = 'max_profit'
    TIME_OPTIMAL = 'time_optimal'
    BALANCED = 'balanced'
    CONSERVATIVE = 'conservative'
    PORTFOLIO = 'portfolio'


@dataclass
class StrategyCandidate:
    """A candidate strategy with calculated metrics."""
    items: List[Dict[str, Any]]
    total_investment: int
    total_profit: int
    estimated_days: float
    risk_score: float
    feasibility_score: float
    strategy_type: StrategyType


@dataclass
class ItemAnalysis:
    """Analysis data for a single item."""
    item: Item
    profit_calculation: ProfitCalculation
    units_affordable: int
    total_profit_potential: int
    days_to_complete: float
    risk_factors: Dict[str, float]
    volume_score: float


class GoalPlanningService:
    """Main service for generating goal-based high alch strategies."""
    
    def __init__(self):
        self.nature_rune_cost = 180  # Cost per nature rune
        self.high_alch_time = 3.6  # Seconds per high alch cast
        self.daily_play_hours = 6  # Average daily play time assumption
        
    async def create_goal_plan(
        self, 
        user_id: int, 
        current_gp: int, 
        goal_gp: int,
        risk_tolerance: str = 'balanced',
        time_preference: str = 'balanced'
    ) -> GoalPlan:
        """Create a new goal plan with optimized strategies."""
        
        if goal_gp <= current_gp:
            raise ValueError("Goal GP must be greater than current GP")
            
        required_profit = goal_gp - current_gp
        
        # Create the goal plan
        goal_plan = await GoalPlan.objects.acreate(
            user_id=user_id,
            current_gp=current_gp,
            goal_gp=goal_gp,
            required_profit=required_profit,
            risk_tolerance=risk_tolerance,
            time_preference=time_preference,
            status='analyzing'
        )
        
        # Generate strategies asynchronously
        asyncio.create_task(self._generate_strategies(goal_plan))
        
        return goal_plan
    
    async def _generate_strategies(self, goal_plan: GoalPlan):
        """Generate multiple strategy options for the goal plan."""
        try:
            # Analyze available items
            item_analyses = await self._analyze_available_items(goal_plan.current_gp)
            
            if not item_analyses:
                await self._mark_goal_plan_failed(goal_plan, "No profitable items available")
                return
            
            # Generate different strategy types
            strategies = []
            
            # 1. Maximum Profit Strategy
            max_profit_strategy = await self._generate_max_profit_strategy(
                goal_plan, item_analyses
            )
            if max_profit_strategy:
                strategies.append(max_profit_strategy)
            
            # 2. Time Optimal Strategy
            time_optimal_strategy = await self._generate_time_optimal_strategy(
                goal_plan, item_analyses
            )
            if time_optimal_strategy:
                strategies.append(time_optimal_strategy)
            
            # 3. Balanced Strategy
            balanced_strategy = await self._generate_balanced_strategy(
                goal_plan, item_analyses
            )
            if balanced_strategy:
                strategies.append(balanced_strategy)
            
            # 4. Conservative Strategy
            conservative_strategy = await self._generate_conservative_strategy(
                goal_plan, item_analyses
            )
            if conservative_strategy:
                strategies.append(conservative_strategy)
            
            # 5. Portfolio Strategy (multi-item)
            portfolio_strategy = await self._generate_portfolio_strategy(
                goal_plan, item_analyses
            )
            if portfolio_strategy:
                strategies.append(portfolio_strategy)
            
            if strategies:
                # Save strategies to database
                await self._save_strategies(goal_plan, strategies)
                
                # Mark goal plan as ready
                goal_plan.status = 'ready'
                goal_plan.strategies_generated = len(strategies)
                await goal_plan.asave()
                
            else:
                await self._mark_goal_plan_failed(goal_plan, "No feasible strategies found")
                
        except Exception as e:
            logger.error(f"Strategy generation failed for plan {goal_plan.plan_id}: {e}")
            await self._mark_goal_plan_failed(goal_plan, f"Generation error: {str(e)}")
    
    async def _analyze_available_items(self, available_gp: int) -> List[ItemAnalysis]:
        """Analyze all items that could be profitable for high alching."""
        
        # Get profitable items within budget
        profit_calculations = await sync_to_async(list)(
            ProfitCalculation.objects.select_related('item')
            .filter(
                current_profit__gt=0,  # Must be profitable
                current_buy_price__lte=available_gp,  # Must be affordable
                item__is_active=True,
                item__high_alch__gt=0  # Must have high alch value
            )
            .order_by('-recommendation_score')[:500]  # Limit for performance
        )
        
        analyses = []
        
        for profit_calc in profit_calculations:
            try:
                analysis = await self._analyze_single_item(profit_calc, available_gp)
                if analysis.units_affordable > 0:
                    analyses.append(analysis)
            except Exception as e:
                logger.warning(f"Failed to analyze item {profit_calc.item.name}: {e}")
        
        # Sort by potential profit descending
        analyses.sort(key=lambda x: x.total_profit_potential, reverse=True)
        
        return analyses[:100]  # Return top 100 candidates
    
    async def _analyze_single_item(self, profit_calc: ProfitCalculation, available_gp: int) -> ItemAnalysis:
        """Perform detailed analysis on a single item."""
        
        item = profit_calc.item
        buy_price = profit_calc.current_buy_price
        profit_per_unit = profit_calc.current_profit
        
        # Calculate how many units can be afforded
        max_by_budget = available_gp // buy_price if buy_price > 0 else 0
        max_by_limit = item.limit if item.limit > 0 else float('inf')
        units_affordable = min(max_by_budget, max_by_limit) if max_by_limit != float('inf') else max_by_budget
        
        # Calculate total profit potential
        total_profit_potential = units_affordable * profit_per_unit
        
        # Estimate time to complete (high alch all units)
        total_high_alchs = units_affordable
        total_seconds = total_high_alchs * self.high_alch_time
        total_hours = total_seconds / 3600
        days_to_complete = total_hours / self.daily_play_hours
        
        # Calculate risk factors
        risk_factors = await self._calculate_risk_factors(profit_calc)
        
        # Calculate volume score (higher is better)
        volume_score = min(1.0, profit_calc.daily_volume / 1000.0) if profit_calc.daily_volume else 0.0
        
        return ItemAnalysis(
            item=item,
            profit_calculation=profit_calc,
            units_affordable=units_affordable,
            total_profit_potential=total_profit_potential,
            days_to_complete=days_to_complete,
            risk_factors=risk_factors,
            volume_score=volume_score
        )
    
    async def _calculate_risk_factors(self, profit_calc: ProfitCalculation) -> Dict[str, float]:
        """Calculate various risk factors for an item."""
        
        # Price volatility risk (0-1, higher is riskier)
        price_volatility = min(1.0, abs(profit_calc.current_profit_margin) / 50.0)
        
        # Volume risk (0-1, higher is riskier)
        volume_risk = 1.0 - min(1.0, profit_calc.daily_volume / 1000.0) if profit_calc.daily_volume else 1.0
        
        # Margin risk (0-1, higher is riskier)
        margin_risk = 1.0 - min(1.0, max(0.0, profit_calc.current_profit_margin / 20.0))
        
        # Trend risk
        trend_risk = {
            'rising': 0.2,
            'stable': 0.5,
            'falling': 0.8,
            'volatile': 0.9
        }.get(profit_calc.price_trend, 0.5)
        
        return {
            'price_volatility': price_volatility,
            'volume_risk': volume_risk,
            'margin_risk': margin_risk,
            'trend_risk': trend_risk,
            'overall_risk': (price_volatility + volume_risk + margin_risk + trend_risk) / 4.0
        }
    
    async def _generate_max_profit_strategy(
        self, 
        goal_plan: GoalPlan, 
        item_analyses: List[ItemAnalysis]
    ) -> Optional[StrategyCandidate]:
        """Generate strategy focused on maximum profit potential."""
        
        remaining_profit = goal_plan.required_profit
        remaining_budget = goal_plan.current_gp
        selected_items = []
        
        # Sort by profit potential per GP invested (efficiency)
        efficiency_sorted = sorted(
            item_analyses,
            key=lambda x: x.total_profit_potential / (x.units_affordable * x.profit_calculation.current_buy_price) if x.units_affordable > 0 else 0,
            reverse=True
        )
        
        for analysis in efficiency_sorted:
            if remaining_profit <= 0:
                break
                
            buy_price = analysis.profit_calculation.current_buy_price
            profit_per_unit = analysis.profit_calculation.current_profit
            
            # Calculate how many we can afford and need
            max_affordable = remaining_budget // buy_price
            units_needed = math.ceil(remaining_profit / profit_per_unit)
            units_to_buy = min(max_affordable, units_needed, analysis.units_affordable)
            
            if units_to_buy > 0:
                total_cost = units_to_buy * buy_price
                total_profit = units_to_buy * profit_per_unit
                
                selected_items.append({
                    'item_id': analysis.item.item_id,
                    'item_name': analysis.item.name,
                    'units_to_buy': units_to_buy,
                    'buy_price': buy_price,
                    'total_cost': total_cost,
                    'profit_per_unit': profit_per_unit,
                    'total_profit': total_profit,
                    'estimated_hours': units_to_buy * self.high_alch_time / 3600,
                    'risk_score': analysis.risk_factors['overall_risk']
                })
                
                remaining_profit -= total_profit
                remaining_budget -= total_cost
        
        if not selected_items:
            return None
        
        # Calculate strategy metrics
        total_investment = sum(item['total_cost'] for item in selected_items)
        total_profit = sum(item['total_profit'] for item in selected_items)
        total_hours = sum(item['estimated_hours'] for item in selected_items)
        estimated_days = total_hours / self.daily_play_hours
        
        # Calculate risk and feasibility scores
        avg_risk_score = sum(item['risk_score'] for item in selected_items) / len(selected_items)
        feasibility_score = min(1.0, total_profit / goal_plan.required_profit)
        
        return StrategyCandidate(
            items=selected_items,
            total_investment=total_investment,
            total_profit=total_profit,
            estimated_days=estimated_days,
            risk_score=avg_risk_score,
            feasibility_score=feasibility_score,
            strategy_type=StrategyType.MAX_PROFIT
        )
    
    async def _generate_time_optimal_strategy(
        self, 
        goal_plan: GoalPlan, 
        item_analyses: List[ItemAnalysis]
    ) -> Optional[StrategyCandidate]:
        """Generate strategy focused on completing the goal as quickly as possible."""
        
        remaining_profit = goal_plan.required_profit
        remaining_budget = goal_plan.current_gp
        selected_items = []
        
        # Sort by profit per hour (time efficiency)
        time_sorted = sorted(
            item_analyses,
            key=lambda x: (x.total_profit_potential / x.days_to_complete) if x.days_to_complete > 0 else 0,
            reverse=True
        )
        
        for analysis in time_sorted:
            if remaining_profit <= 0:
                break
                
            buy_price = analysis.profit_calculation.current_buy_price
            profit_per_unit = analysis.profit_calculation.current_profit
            
            max_affordable = remaining_budget // buy_price
            units_needed = math.ceil(remaining_profit / profit_per_unit)
            units_to_buy = min(max_affordable, units_needed, analysis.units_affordable)
            
            if units_to_buy > 0:
                total_cost = units_to_buy * buy_price
                total_profit = units_to_buy * profit_per_unit
                
                selected_items.append({
                    'item_id': analysis.item.item_id,
                    'item_name': analysis.item.name,
                    'units_to_buy': units_to_buy,
                    'buy_price': buy_price,
                    'total_cost': total_cost,
                    'profit_per_unit': profit_per_unit,
                    'total_profit': total_profit,
                    'estimated_hours': units_to_buy * self.high_alch_time / 3600,
                    'risk_score': analysis.risk_factors['overall_risk']
                })
                
                remaining_profit -= total_profit
                remaining_budget -= total_cost
        
        if not selected_items:
            return None
        
        total_investment = sum(item['total_cost'] for item in selected_items)
        total_profit = sum(item['total_profit'] for item in selected_items)
        total_hours = sum(item['estimated_hours'] for item in selected_items)
        estimated_days = total_hours / self.daily_play_hours
        
        avg_risk_score = sum(item['risk_score'] for item in selected_items) / len(selected_items)
        feasibility_score = min(1.0, total_profit / goal_plan.required_profit)
        
        return StrategyCandidate(
            items=selected_items,
            total_investment=total_investment,
            total_profit=total_profit,
            estimated_days=estimated_days,
            risk_score=avg_risk_score,
            feasibility_score=feasibility_score,
            strategy_type=StrategyType.TIME_OPTIMAL
        )
    
    async def _generate_balanced_strategy(
        self, 
        goal_plan: GoalPlan, 
        item_analyses: List[ItemAnalysis]
    ) -> Optional[StrategyCandidate]:
        """Generate strategy balancing profit, time, and risk."""
        
        remaining_profit = goal_plan.required_profit
        remaining_budget = goal_plan.current_gp
        selected_items = []
        
        # Calculate balanced score: (profit efficiency + time efficiency) / (1 + risk)
        def balanced_score(analysis):
            profit_eff = analysis.total_profit_potential / (analysis.units_affordable * analysis.profit_calculation.current_buy_price) if analysis.units_affordable > 0 else 0
            time_eff = (analysis.total_profit_potential / analysis.days_to_complete) if analysis.days_to_complete > 0 else 0
            risk_penalty = 1 + analysis.risk_factors['overall_risk']
            return (profit_eff + time_eff) / risk_penalty
        
        balanced_sorted = sorted(item_analyses, key=balanced_score, reverse=True)
        
        for analysis in balanced_sorted:
            if remaining_profit <= 0:
                break
                
            buy_price = analysis.profit_calculation.current_buy_price
            profit_per_unit = analysis.profit_calculation.current_profit
            
            max_affordable = remaining_budget // buy_price
            units_needed = math.ceil(remaining_profit / profit_per_unit)
            units_to_buy = min(max_affordable, units_needed, analysis.units_affordable)
            
            if units_to_buy > 0:
                total_cost = units_to_buy * buy_price
                total_profit = units_to_buy * profit_per_unit
                
                selected_items.append({
                    'item_id': analysis.item.item_id,
                    'item_name': analysis.item.name,
                    'units_to_buy': units_to_buy,
                    'buy_price': buy_price,
                    'total_cost': total_cost,
                    'profit_per_unit': profit_per_unit,
                    'total_profit': total_profit,
                    'estimated_hours': units_to_buy * self.high_alch_time / 3600,
                    'risk_score': analysis.risk_factors['overall_risk']
                })
                
                remaining_profit -= total_profit
                remaining_budget -= total_cost
        
        if not selected_items:
            return None
        
        total_investment = sum(item['total_cost'] for item in selected_items)
        total_profit = sum(item['total_profit'] for item in selected_items)
        total_hours = sum(item['estimated_hours'] for item in selected_items)
        estimated_days = total_hours / self.daily_play_hours
        
        avg_risk_score = sum(item['risk_score'] for item in selected_items) / len(selected_items)
        feasibility_score = min(1.0, total_profit / goal_plan.required_profit)
        
        return StrategyCandidate(
            items=selected_items,
            total_investment=total_investment,
            total_profit=total_profit,
            estimated_days=estimated_days,
            risk_score=avg_risk_score,
            feasibility_score=feasibility_score,
            strategy_type=StrategyType.BALANCED
        )
    
    async def _generate_conservative_strategy(
        self, 
        goal_plan: GoalPlan, 
        item_analyses: List[ItemAnalysis]
    ) -> Optional[StrategyCandidate]:
        """Generate low-risk strategy with stable items."""
        
        # Filter for low-risk items only
        conservative_items = [
            analysis for analysis in item_analyses
            if analysis.risk_factors['overall_risk'] <= 0.4 and
               analysis.volume_score >= 0.3 and
               analysis.profit_calculation.current_profit_margin >= 5.0
        ]
        
        if not conservative_items:
            return None
        
        remaining_profit = goal_plan.required_profit
        remaining_budget = goal_plan.current_gp
        selected_items = []
        
        # Sort by stability (low risk + good volume)
        stability_sorted = sorted(
            conservative_items,
            key=lambda x: x.volume_score - x.risk_factors['overall_risk'],
            reverse=True
        )
        
        for analysis in stability_sorted:
            if remaining_profit <= 0:
                break
                
            buy_price = analysis.profit_calculation.current_buy_price
            profit_per_unit = analysis.profit_calculation.current_profit
            
            max_affordable = remaining_budget // buy_price
            units_needed = math.ceil(remaining_profit / profit_per_unit)
            units_to_buy = min(max_affordable, units_needed, analysis.units_affordable)
            
            if units_to_buy > 0:
                total_cost = units_to_buy * buy_price
                total_profit = units_to_buy * profit_per_unit
                
                selected_items.append({
                    'item_id': analysis.item.item_id,
                    'item_name': analysis.item.name,
                    'units_to_buy': units_to_buy,
                    'buy_price': buy_price,
                    'total_cost': total_cost,
                    'profit_per_unit': profit_per_unit,
                    'total_profit': total_profit,
                    'estimated_hours': units_to_buy * self.high_alch_time / 3600,
                    'risk_score': analysis.risk_factors['overall_risk']
                })
                
                remaining_profit -= total_profit
                remaining_budget -= total_cost
        
        if not selected_items:
            return None
        
        total_investment = sum(item['total_cost'] for item in selected_items)
        total_profit = sum(item['total_profit'] for item in selected_items)
        total_hours = sum(item['estimated_hours'] for item in selected_items)
        estimated_days = total_hours / self.daily_play_hours
        
        avg_risk_score = sum(item['risk_score'] for item in selected_items) / len(selected_items)
        feasibility_score = min(1.0, total_profit / goal_plan.required_profit)
        
        return StrategyCandidate(
            items=selected_items,
            total_investment=total_investment,
            total_profit=total_profit,
            estimated_days=estimated_days,
            risk_score=avg_risk_score,
            feasibility_score=feasibility_score,
            strategy_type=StrategyType.CONSERVATIVE
        )
    
    async def _generate_portfolio_strategy(
        self, 
        goal_plan: GoalPlan, 
        item_analyses: List[ItemAnalysis]
    ) -> Optional[StrategyCandidate]:
        """Generate diversified portfolio strategy with multiple items."""
        
        # Select top items from different risk/profit categories
        high_profit_low_risk = [a for a in item_analyses if a.risk_factors['overall_risk'] <= 0.3 and a.total_profit_potential >= 50000]
        medium_risk_medium_profit = [a for a in item_analyses if 0.3 < a.risk_factors['overall_risk'] <= 0.6 and a.total_profit_potential >= 30000]
        diverse_items = [a for a in item_analyses if a.volume_score >= 0.4]
        
        # Combine and deduplicate
        portfolio_candidates = list(set(high_profit_low_risk[:3] + medium_risk_medium_profit[:3] + diverse_items[:4]))
        
        if len(portfolio_candidates) < 2:
            return None
        
        remaining_profit = goal_plan.required_profit
        remaining_budget = goal_plan.current_gp
        selected_items = []
        
        # Distribute budget across multiple items
        budget_per_item = remaining_budget // len(portfolio_candidates)
        
        for analysis in portfolio_candidates:
            if remaining_profit <= 0 or remaining_budget <= 0:
                break
                
            buy_price = analysis.profit_calculation.current_buy_price
            profit_per_unit = analysis.profit_calculation.current_profit
            
            # Use allocated budget for this item
            item_budget = min(budget_per_item, remaining_budget)
            max_affordable = item_budget // buy_price
            units_to_buy = min(max_affordable, analysis.units_affordable)
            
            if units_to_buy > 0:
                total_cost = units_to_buy * buy_price
                total_profit = units_to_buy * profit_per_unit
                
                selected_items.append({
                    'item_id': analysis.item.item_id,
                    'item_name': analysis.item.name,
                    'units_to_buy': units_to_buy,
                    'buy_price': buy_price,
                    'total_cost': total_cost,
                    'profit_per_unit': profit_per_unit,
                    'total_profit': total_profit,
                    'estimated_hours': units_to_buy * self.high_alch_time / 3600,
                    'risk_score': analysis.risk_factors['overall_risk']
                })
                
                remaining_profit -= total_profit
                remaining_budget -= total_cost
        
        if len(selected_items) < 2:
            return None
        
        total_investment = sum(item['total_cost'] for item in selected_items)
        total_profit = sum(item['total_profit'] for item in selected_items)
        total_hours = sum(item['estimated_hours'] for item in selected_items)
        estimated_days = total_hours / self.daily_play_hours
        
        avg_risk_score = sum(item['risk_score'] for item in selected_items) / len(selected_items)
        feasibility_score = min(1.0, total_profit / goal_plan.required_profit)
        
        return StrategyCandidate(
            items=selected_items,
            total_investment=total_investment,
            total_profit=total_profit,
            estimated_days=estimated_days,
            risk_score=avg_risk_score,
            feasibility_score=feasibility_score,
            strategy_type=StrategyType.PORTFOLIO
        )
    
    async def _save_strategies(self, goal_plan: GoalPlan, strategies: List[StrategyCandidate]):
        """Save generated strategies to the database."""
        
        with transaction.atomic():
            for strategy_candidate in strategies:
                # Create strategy record
                strategy = await Strategy.objects.acreate(
                    goal_plan=goal_plan,
                    strategy_type=strategy_candidate.strategy_type.value,
                    total_investment=strategy_candidate.total_investment,
                    total_profit=strategy_candidate.total_profit,
                    estimated_days=strategy_candidate.estimated_days,
                    risk_score=strategy_candidate.risk_score,
                    feasibility_score=strategy_candidate.feasibility_score,
                    ai_confidence=0.85,  # Base confidence score
                    status='ready'
                )
                
                # Create strategy items
                for item_data in strategy_candidate.items:
                    await StrategyItem.objects.acreate(
                        strategy=strategy,
                        item_id=item_data['item_id'],
                        units_to_buy=item_data['units_to_buy'],
                        buy_price=item_data['buy_price'],
                        total_cost=item_data['total_cost'],
                        profit_per_unit=item_data['profit_per_unit'],
                        total_profit=item_data['total_profit'],
                        estimated_hours=item_data['estimated_hours'],
                        risk_score=item_data['risk_score'],
                        order_priority=strategy_candidate.items.index(item_data) + 1
                    )
    
    async def _mark_goal_plan_failed(self, goal_plan: GoalPlan, error_message: str):
        """Mark a goal plan as failed with error message."""
        goal_plan.status = 'failed'
        goal_plan.error_message = error_message
        await goal_plan.asave()
        
        logger.error(f"Goal plan {goal_plan.plan_id} failed: {error_message}")


class PortfolioOptimizer:
    """Advanced portfolio optimization for multi-item strategies."""
    
    async def optimize_portfolio(
        self, 
        available_gp: int, 
        target_profit: int, 
        item_analyses: List[ItemAnalysis],
        risk_tolerance: float = 0.5
    ) -> Optional[List[Dict[str, Any]]]:
        """Optimize item selection and allocation using portfolio theory principles."""
        
        # This would implement Modern Portfolio Theory concepts
        # For now, implementing a simplified version
        pass


class TimeEstimator:
    """Service for estimating completion times and scheduling."""
    
    def __init__(self):
        self.high_alch_time = 3.6  # seconds per cast
        self.ge_interaction_time = 30  # seconds per GE interaction
        self.travel_time = 60  # seconds for travel/banking
    
    async def estimate_completion_time(
        self, 
        strategy_items: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Estimate detailed completion times for a strategy."""
        
        total_high_alchs = sum(item['units_to_buy'] for item in strategy_items)
        total_ge_interactions = len(strategy_items) * 2  # Buy and sell
        
        # Calculate time components
        high_alch_time = total_high_alchs * self.high_alch_time
        ge_time = total_ge_interactions * self.ge_interaction_time
        travel_time = total_ge_interactions * self.travel_time
        
        total_seconds = high_alch_time + ge_time + travel_time
        
        return {
            'total_seconds': total_seconds,
            'total_hours': total_seconds / 3600,
            'high_alch_hours': high_alch_time / 3600,
            'ge_hours': ge_time / 3600,
            'travel_hours': travel_time / 3600,
            'estimated_days_6h': (total_seconds / 3600) / 6,  # 6 hours per day
            'estimated_days_4h': (total_seconds / 3600) / 4,  # 4 hours per day
            'estimated_days_2h': (total_seconds / 3600) / 2,  # 2 hours per day
        }


class RiskAnalyzer:
    """Service for analyzing and scoring strategy risks."""
    
    async def analyze_strategy_risk(
        self, 
        strategy_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform comprehensive risk analysis on a strategy."""
        
        if not strategy_items:
            return {'overall_risk': 1.0, 'risk_factors': {}}
        
        # Calculate various risk metrics
        individual_risks = [item['risk_score'] for item in strategy_items]
        avg_risk = sum(individual_risks) / len(individual_risks)
        
        # Diversification score (lower is better diversified)
        unique_categories = len(set(item.get('category', 'unknown') for item in strategy_items))
        diversification_risk = max(0.0, 1.0 - (unique_categories / 10.0))
        
        # Concentration risk (too much in one item)
        total_investment = sum(item['total_cost'] for item in strategy_items)
        if total_investment > 0:
            concentrations = [item['total_cost'] / total_investment for item in strategy_items]
            max_concentration = max(concentrations)
            concentration_risk = max_concentration  # 0-1, higher is riskier
        else:
            concentration_risk = 0.0
        
        # Market capacity risk (volume vs buy amounts)
        capacity_risks = []
        for item in strategy_items:
            # This would check if we're trying to buy more than typical market volume
            capacity_risks.append(0.3)  # Placeholder
        
        avg_capacity_risk = sum(capacity_risks) / len(capacity_risks) if capacity_risks else 0.0
        
        # Overall risk calculation
        overall_risk = (
            avg_risk * 0.4 +
            diversification_risk * 0.2 +
            concentration_risk * 0.2 +
            avg_capacity_risk * 0.2
        )
        
        return {
            'overall_risk': overall_risk,
            'risk_factors': {
                'average_item_risk': avg_risk,
                'diversification_risk': diversification_risk,
                'concentration_risk': concentration_risk,
                'market_capacity_risk': avg_capacity_risk,
                'risk_breakdown': individual_risks
            },
            'risk_level': self._get_risk_level(overall_risk),
            'recommendations': self._generate_risk_recommendations(overall_risk, {
                'diversification_risk': diversification_risk,
                'concentration_risk': concentration_risk
            })
        }
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to human-readable level."""
        if risk_score <= 0.3:
            return 'Low'
        elif risk_score <= 0.6:
            return 'Medium'
        else:
            return 'High'
    
    def _generate_risk_recommendations(self, overall_risk: float, risk_factors: Dict) -> List[str]:
        """Generate risk mitigation recommendations."""
        recommendations = []
        
        if overall_risk > 0.7:
            recommendations.append("Consider more conservative item selection")
        
        if risk_factors.get('diversification_risk', 0) > 0.6:
            recommendations.append("Diversify across more item categories")
        
        if risk_factors.get('concentration_risk', 0) > 0.5:
            recommendations.append("Reduce investment concentration in single items")
        
        return recommendations