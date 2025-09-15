"""
Adapter service to integrate our new goal planning algorithms with existing models.
This bridges the gap between our advanced async services and the existing Django models.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from asgiref.sync import sync_to_async

from .models import GoalPlan, Strategy, StrategyItem
from .services import GoalPlanningService, ItemAnalysis, StrategyCandidate, StrategyType
from apps.items.models import Item
from apps.prices.models import ProfitCalculation

logger = logging.getLogger(__name__)


class GoalPlanningAdapter:
    """Adapter to integrate new services with existing Django models."""
    
    def __init__(self):
        self.goal_planning_service = GoalPlanningService()
    
    async def create_goal_plan_with_strategies(
        self,
        session_key: str,
        current_gp: int,
        goal_gp: int,
        risk_tolerance: str = 'moderate'
    ) -> GoalPlan:
        """Create a goal plan using existing models but new algorithms."""
        
        # Calculate required profit
        required_profit = goal_gp - current_gp
        
        # Create goal plan with existing model structure
        goal_plan = await sync_to_async(GoalPlan.objects.create)(
            session_key=session_key,
            current_gp=current_gp,
            goal_gp=goal_gp,
            required_profit=required_profit,
            risk_tolerance=risk_tolerance,
            is_active=True,
            is_achievable=True
        )
        
        # Generate strategies using our new service
        await self._generate_strategies_for_existing_plan(goal_plan)
        
        return goal_plan
    
    async def _generate_strategies_for_existing_plan(self, goal_plan: GoalPlan):
        """Generate strategies for an existing goal plan."""
        try:
            # Analyze available items using our new service
            item_analyses = await self._analyze_available_items(goal_plan.current_gp)
            
            if not item_analyses:
                goal_plan.is_achievable = False
                await sync_to_async(goal_plan.save)()
                logger.warning(f"No profitable items found for goal plan {goal_plan.plan_id}")
                return
            
            # Generate different strategy types
            strategy_candidates = []
            
            # 1. Maximum Profit Strategy
            max_profit = await self._generate_max_profit_strategy(goal_plan, item_analyses)
            if max_profit:
                strategy_candidates.append(max_profit)
            
            # 2. Time Optimal Strategy
            time_optimal = await self._generate_time_optimal_strategy(goal_plan, item_analyses)
            if time_optimal:
                strategy_candidates.append(time_optimal)
            
            # 3. Balanced Strategy
            balanced = await self._generate_balanced_strategy(goal_plan, item_analyses)
            if balanced:
                strategy_candidates.append(balanced)
            
            # 4. Conservative Strategy (if user prefers low risk)
            if goal_plan.risk_tolerance in ['conservative', 'moderate']:
                conservative = await self._generate_conservative_strategy(goal_plan, item_analyses)
                if conservative:
                    strategy_candidates.append(conservative)
            
            # 5. Portfolio Strategy
            portfolio = await self._generate_portfolio_strategy(goal_plan, item_analyses)
            if portfolio:
                strategy_candidates.append(portfolio)
            
            if strategy_candidates:
                # Save strategies to existing model structure
                await self._save_strategies_to_existing_models(goal_plan, strategy_candidates)
                
                # Update goal plan
                goal_plan.is_achievable = True
                await sync_to_async(goal_plan.save)()
                
                logger.info(f"Generated {len(strategy_candidates)} strategies for goal plan {goal_plan.plan_id}")
            else:
                goal_plan.is_achievable = False
                await sync_to_async(goal_plan.save)()
                logger.warning(f"No feasible strategies generated for goal plan {goal_plan.plan_id}")
                
        except Exception as e:
            logger.error(f"Strategy generation failed for plan {goal_plan.plan_id}: {e}")
            goal_plan.is_achievable = False
            await sync_to_async(goal_plan.save)()
    
    async def _analyze_available_items(self, available_gp: int) -> List[ItemAnalysis]:
        """Analyze items compatible with existing models."""
        
        # Get profitable items from existing model structure
        profit_calculations = await sync_to_async(list)(
            ProfitCalculation.objects.select_related('item')
            .filter(
                current_profit__gt=0,
                current_buy_price__lte=available_gp,
                item__is_active=True,
                item__high_alch__gt=0
            )
            .order_by('-recommendation_score')[:100]
        )
        
        analyses = []
        
        for profit_calc in profit_calculations:
            try:
                analysis = await self._analyze_single_item_adapted(profit_calc, available_gp)
                if analysis.units_affordable > 0:
                    analyses.append(analysis)
            except Exception as e:
                logger.warning(f"Failed to analyze item {profit_calc.item.name}: {e}")
        
        # Sort by potential profit
        analyses.sort(key=lambda x: x.total_profit_potential, reverse=True)
        
        return analyses[:50]  # Return top 50
    
    async def _analyze_single_item_adapted(self, profit_calc: ProfitCalculation, available_gp: int) -> ItemAnalysis:
        """Analyze single item adapted for existing models."""
        
        item = profit_calc.item
        buy_price = profit_calc.current_buy_price
        profit_per_unit = profit_calc.current_profit
        
        # Calculate units affordable
        max_by_budget = available_gp // buy_price if buy_price > 0 else 0
        max_by_limit = item.limit if item.limit > 0 else 999999  # Large number for unlimited items
        units_affordable = min(max_by_budget, max_by_limit)
        
        # Calculate total profit potential
        total_profit_potential = units_affordable * profit_per_unit
        
        # Estimate time to complete
        high_alch_time = 3.6  # seconds per cast
        daily_play_hours = 6  # assumed daily play time
        total_seconds = units_affordable * high_alch_time
        total_hours = total_seconds / 3600
        days_to_complete = total_hours / daily_play_hours
        
        # Calculate risk factors based on available data
        risk_factors = {
            'price_volatility': min(1.0, abs(profit_calc.current_profit_margin) / 50.0),
            'volume_risk': 1.0 - min(1.0, profit_calc.daily_volume / 1000.0) if profit_calc.daily_volume else 1.0,
            'margin_risk': 1.0 - min(1.0, max(0.0, profit_calc.current_profit_margin / 20.0)),
            'trend_risk': {
                'rising': 0.2,
                'falling': 0.8,
                'stable': 0.5
            }.get(profit_calc.price_trend, 0.5),
        }
        risk_factors['overall_risk'] = sum(risk_factors.values()) / len(risk_factors)
        
        # Volume score
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
    
    async def _generate_max_profit_strategy(
        self, 
        goal_plan: GoalPlan, 
        item_analyses: List[ItemAnalysis]
    ) -> Optional[StrategyCandidate]:
        """Generate max profit strategy adapted for existing models."""
        
        remaining_profit = goal_plan.required_profit
        remaining_budget = goal_plan.current_gp
        selected_items = []
        
        # Sort by efficiency (profit per GP invested)
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
            
            max_affordable = remaining_budget // buy_price
            units_needed = max(1, remaining_profit // profit_per_unit)
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
                    'estimated_hours': units_to_buy * 3.6 / 3600,  # High alch time
                    'risk_score': analysis.risk_factors['overall_risk']
                })
                
                remaining_profit -= total_profit
                remaining_budget -= total_cost
        
        if not selected_items:
            return None
        
        total_investment = sum(item['total_cost'] for item in selected_items)
        total_profit = sum(item['total_profit'] for item in selected_items)
        total_hours = sum(item['estimated_hours'] for item in selected_items)
        estimated_days = total_hours / 6  # 6 hours per day
        
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
        """Generate time optimal strategy."""
        
        remaining_profit = goal_plan.required_profit
        remaining_budget = goal_plan.current_gp
        selected_items = []
        
        # Sort by time efficiency (profit per day)
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
            units_needed = max(1, remaining_profit // profit_per_unit)
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
                    'estimated_hours': units_to_buy * 3.6 / 3600,
                    'risk_score': analysis.risk_factors['overall_risk']
                })
                
                remaining_profit -= total_profit
                remaining_budget -= total_cost
        
        if not selected_items:
            return None
        
        total_investment = sum(item['total_cost'] for item in selected_items)
        total_profit = sum(item['total_profit'] for item in selected_items)
        total_hours = sum(item['estimated_hours'] for item in selected_items)
        estimated_days = total_hours / 6
        
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
        """Generate balanced strategy."""
        
        remaining_profit = goal_plan.required_profit
        remaining_budget = goal_plan.current_gp
        selected_items = []
        
        # Balanced score considering profit, time, and risk
        def balanced_score(analysis):
            if analysis.units_affordable <= 0:
                return 0
            
            profit_eff = analysis.total_profit_potential / (analysis.units_affordable * analysis.profit_calculation.current_buy_price)
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
            units_needed = max(1, remaining_profit // profit_per_unit)
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
                    'estimated_hours': units_to_buy * 3.6 / 3600,
                    'risk_score': analysis.risk_factors['overall_risk']
                })
                
                remaining_profit -= total_profit
                remaining_budget -= total_cost
        
        if not selected_items:
            return None
        
        total_investment = sum(item['total_cost'] for item in selected_items)
        total_profit = sum(item['total_profit'] for item in selected_items)
        total_hours = sum(item['estimated_hours'] for item in selected_items)
        estimated_days = total_hours / 6
        
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
        """Generate conservative strategy with low-risk items."""
        
        # Filter for low-risk items
        conservative_items = [
            analysis for analysis in item_analyses
            if analysis.risk_factors['overall_risk'] <= 0.4 and
               analysis.volume_score >= 0.2 and
               analysis.profit_calculation.current_profit_margin >= 3.0
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
            units_needed = max(1, remaining_profit // profit_per_unit)
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
                    'estimated_hours': units_to_buy * 3.6 / 3600,
                    'risk_score': analysis.risk_factors['overall_risk']
                })
                
                remaining_profit -= total_profit
                remaining_budget -= total_cost
        
        if not selected_items:
            return None
        
        total_investment = sum(item['total_cost'] for item in selected_items)
        total_profit = sum(item['total_profit'] for item in selected_items)
        total_hours = sum(item['estimated_hours'] for item in selected_items)
        estimated_days = total_hours / 6
        
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
        """Generate diversified portfolio strategy."""
        
        if len(item_analyses) < 3:
            return None
        
        # Select diverse items
        high_profit_low_risk = [a for a in item_analyses if a.risk_factors['overall_risk'] <= 0.3 and a.total_profit_potential >= 10000]
        medium_risk_items = [a for a in item_analyses if 0.3 < a.risk_factors['overall_risk'] <= 0.6 and a.total_profit_potential >= 5000]
        high_volume_items = [a for a in item_analyses if a.volume_score >= 0.4]
        
        # Combine and deduplicate
        portfolio_candidates = list(set(high_profit_low_risk[:2] + medium_risk_items[:2] + high_volume_items[:2]))
        
        if len(portfolio_candidates) < 2:
            return None
        
        remaining_profit = goal_plan.required_profit
        remaining_budget = goal_plan.current_gp
        selected_items = []
        
        # Distribute budget across items
        budget_per_item = remaining_budget // len(portfolio_candidates)
        
        for analysis in portfolio_candidates:
            if remaining_profit <= 0 or remaining_budget <= 0:
                break
                
            buy_price = analysis.profit_calculation.current_buy_price
            profit_per_unit = analysis.profit_calculation.current_profit
            
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
                    'estimated_hours': units_to_buy * 3.6 / 3600,
                    'risk_score': analysis.risk_factors['overall_risk']
                })
                
                remaining_profit -= total_profit
                remaining_budget -= total_cost
        
        if len(selected_items) < 2:
            return None
        
        total_investment = sum(item['total_cost'] for item in selected_items)
        total_profit = sum(item['total_profit'] for item in selected_items)
        total_hours = sum(item['estimated_hours'] for item in selected_items)
        estimated_days = total_hours / 6
        
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
    
    async def _save_strategies_to_existing_models(self, goal_plan: GoalPlan, candidates: List[StrategyCandidate]):
        """Save strategy candidates to existing Django models."""
        
        strategy_type_names = {
            StrategyType.MAX_PROFIT: 'Maximum Profit',
            StrategyType.TIME_OPTIMAL: 'Time Optimal',
            StrategyType.BALANCED: 'Balanced Risk/Reward',
            StrategyType.CONSERVATIVE: 'Conservative',
            StrategyType.PORTFOLIO: 'Multi-Item Portfolio'
        }
        
        for candidate in candidates:
            # Create Strategy using existing model structure
            strategy = await sync_to_async(Strategy.objects.create)(
                goal_plan=goal_plan,
                name=strategy_type_names.get(candidate.strategy_type, candidate.strategy_type.value.title()),
                strategy_type=candidate.strategy_type.value,
                estimated_days=candidate.estimated_days,
                estimated_profit=candidate.total_profit,
                required_initial_investment=candidate.total_investment,
                risk_level='high' if candidate.risk_score > 0.7 else 'medium' if candidate.risk_score > 0.4 else 'low',
                feasibility_score=candidate.feasibility_score,
                ai_confidence=0.85,
                is_recommended=candidate.feasibility_score >= 0.8,  # Mark high-feasibility strategies as recommended
                is_active=True
            )
            
            # Create StrategyItems
            for i, item_data in enumerate(candidate.items):
                # Get the actual Item instance
                item = await sync_to_async(Item.objects.get)(item_id=item_data['item_id'])
                
                await sync_to_async(StrategyItem.objects.create)(
                    strategy=strategy,
                    item=item,
                    allocation_percentage=(item_data['total_cost'] / candidate.total_investment * 100),
                    items_to_buy=item_data['units_to_buy'],
                    buy_price_when_calculated=item_data['buy_price'],
                    profit_per_item=item_data['profit_per_unit'],
                    total_cost=item_data['total_cost'],
                    expected_profit=item_data['total_profit'],
                    ge_limit=item.limit or 8,
                    estimated_buy_time_hours=item_data['estimated_hours'],
                    daily_volume=1000,  # Default value
                    price_volatility=item_data['risk_score'],
                    is_primary=(i == 0),
                    is_active=True
                )
        
        # Ensure at least one strategy is marked as recommended
        if not any(c.feasibility_score >= 0.8 for c in candidates):
            # Mark the best strategy as recommended
            best_candidate = max(candidates, key=lambda x: x.feasibility_score)
            best_strategy = await sync_to_async(Strategy.objects.filter(
                goal_plan=goal_plan,
                strategy_type=best_candidate.strategy_type.value
            ).first)()
            if best_strategy:
                best_strategy.is_recommended = True
                await sync_to_async(best_strategy.save)()


# Global instance
goal_planning_adapter = GoalPlanningAdapter()