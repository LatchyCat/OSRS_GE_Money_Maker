"""
Advanced Portfolio Optimization Engine for OSRS Trading

Sophisticated portfolio management optimized for MacBook Pro M1 8GB:
- Modern Portfolio Theory (MPT) implementation
- Kelly Criterion position sizing
- Risk parity and equal weight strategies
- Capital allocation optimization
- Correlation-based diversification
- Dynamic rebalancing algorithms
- Multi-objective optimization (return vs risk vs liquidity)
- GE limit-aware portfolio construction
- Real-time portfolio performance tracking
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import models, transaction
from asgiref.sync import sync_to_async
from dataclasses import dataclass
import json
import math
from scipy import optimize
from scipy.stats import norm
from collections import defaultdict

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.realtime_engine.models import (
    RiskMetrics, VolumeAnalysis, PricePrediction, 
    GELimitEntry, MarketMomentum
)
from services.intelligent_cache import intelligent_cache

logger = logging.getLogger(__name__)


@dataclass
class PortfolioAllocation:
    """Portfolio allocation result."""
    item_id: int
    item_name: str
    target_weight: float
    target_amount_gp: int
    target_quantity: int
    current_weight: float
    current_amount_gp: int
    rebalance_needed: bool
    expected_return: float
    risk_contribution: float
    liquidity_score: float
    ge_limit_utilization: float


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics."""
    total_value: int
    expected_return: float
    portfolio_risk: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    diversification_ratio: float
    liquidity_score: float
    risk_parity_score: float


class PortfolioOptimizer:
    """
    Advanced portfolio optimization engine for OSRS trading.
    """
    
    def __init__(self):
        self.cache_prefix = "portfolio_optimizer:"
        
        # Optimization parameters
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        self.max_position_size = 0.25  # Max 25% in single position
        self.min_position_size = 0.01  # Min 1% in single position
        self.rebalance_threshold = 0.05  # 5% deviation threshold
        
        # Portfolio constraints
        self.max_portfolio_risk = 0.20  # Max 20% portfolio volatility
        self.min_liquidity_score = 0.3  # Minimum liquidity requirement
        self.max_correlation = 0.8  # Max correlation between positions
        
        # Kelly Criterion parameters
        self.kelly_fraction = 0.25  # Use 25% of full Kelly
        self.max_kelly_position = 0.20  # Cap Kelly at 20%
        
    async def optimize_portfolio(self, user_id: int, total_capital: int,
                               optimization_method: str = "risk_parity",
                               constraints: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Optimize portfolio allocation for maximum risk-adjusted returns.
        
        Args:
            user_id: User ID for personalized optimization
            total_capital: Total available capital in GP
            optimization_method: "risk_parity", "mean_variance", "kelly", "equal_weight"
            constraints: Additional constraints
            
        Returns:
            Optimized portfolio allocation
        """
        logger.debug(f"🎯 Optimizing portfolio for user {user_id} with {total_capital:,} GP")
        
        try:
            # Get available investment universe
            investment_universe = await self._get_investment_universe(user_id)
            
            if len(investment_universe) < 3:
                return {
                    'error': 'Insufficient items for portfolio optimization (minimum 3 required)',
                    'available_items': len(investment_universe)
                }
            
            # Get historical data and calculate metrics
            portfolio_data = await self._prepare_portfolio_data(investment_universe)
            
            # Apply optimization method
            if optimization_method == "risk_parity":
                allocations = await self._optimize_risk_parity(
                    portfolio_data, total_capital, constraints
                )
            elif optimization_method == "mean_variance":
                allocations = await self._optimize_mean_variance(
                    portfolio_data, total_capital, constraints
                )
            elif optimization_method == "kelly":
                allocations = await self._optimize_kelly_criterion(
                    portfolio_data, total_capital, constraints
                )
            elif optimization_method == "equal_weight":
                allocations = await self._optimize_equal_weight(
                    portfolio_data, total_capital, constraints
                )
            else:
                return {'error': f'Unknown optimization method: {optimization_method}'}
            
            # Calculate portfolio metrics
            portfolio_metrics = self._calculate_portfolio_metrics(allocations, portfolio_data)
            
            # Generate rebalancing recommendations
            rebalance_actions = await self._generate_rebalance_actions(
                user_id, allocations, total_capital
            )
            
            # Prepare result
            result = {
                'user_id': user_id,
                'optimization_method': optimization_method,
                'total_capital': total_capital,
                'timestamp': timezone.now().isoformat(),
                'portfolio_allocations': [self._allocation_to_dict(a) for a in allocations],
                'portfolio_metrics': self._metrics_to_dict(portfolio_metrics),
                'rebalance_actions': rebalance_actions,
                'optimization_summary': {
                    'total_items': len(allocations),
                    'allocated_capital': sum(a.target_amount_gp for a in allocations),
                    'cash_reserve': total_capital - sum(a.target_amount_gp for a in allocations),
                    'diversification_score': portfolio_metrics.diversification_ratio * 100,
                    'risk_score': portfolio_metrics.portfolio_risk * 100
                }
            }
            
            # Cache result
            cache_key = f"{self.cache_prefix}optimization:{user_id}"
            intelligent_cache.set(
                cache_key,
                result,
                tier="warm",
                tags=[f"user_{user_id}", "portfolio_optimization"]
            )
            
            logger.info(f"✅ Portfolio optimization completed for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Portfolio optimization failed: {e}")
            return {'error': str(e)}
    
    async def _get_investment_universe(self, user_id: int) -> List[Dict[str, Any]]:
        """Get available items for investment universe."""
        # Get items with good profit potential and reasonable risk
        items = await sync_to_async(list)(
            Item.objects.filter(
                profit_calc__current_profit__gte=100,  # Min 100gp profit
                profit_calc__current_profit_margin__gte=3.0,  # Min 3% margin
                profit_calc__volume_category__in=['hot', 'warm', 'cool'],
                prices__created_at__gte=timezone.now() - timedelta(hours=48)
            ).distinct().select_related('profit_calc')[:50]  # Top 50 items
        )
        
        investment_universe = []
        
        for item in items:
            # Get additional data
            risk_metrics = await self._get_risk_metrics(item.item_id)
            volume_analysis = await self._get_volume_analysis(item.item_id)
            price_prediction = await self._get_latest_price_prediction(item.item_id)
            
            # Calculate investment suitability score
            suitability_score = self._calculate_suitability_score(
                item, risk_metrics, volume_analysis, price_prediction
            )
            
            if suitability_score > 0.3:  # Minimum suitability threshold
                investment_universe.append({
                    'item_id': item.item_id,
                    'item_name': item.name,
                    'current_price': (item.profit_calc.current_buy_price + item.profit_calc.current_sell_price) / 2,
                    'expected_return': item.profit_calc.current_profit_margin / 100,
                    'profit_per_item': item.profit_calc.current_profit,
                    'volume_score': self._get_volume_score(volume_analysis),
                    'risk_score': risk_metrics.overall_risk_score if risk_metrics else 50.0,
                    'liquidity_score': self._get_liquidity_score(volume_analysis),
                    'suitability_score': suitability_score,
                    'ge_limit': item.limit or 100,
                    'price_prediction': price_prediction
                })
        
        # Sort by suitability score
        investment_universe.sort(key=lambda x: x['suitability_score'], reverse=True)
        
        # Return top candidates
        return investment_universe[:20]  # Max 20 items for optimization
    
    def _calculate_suitability_score(self, item: Item, risk_metrics: Optional[RiskMetrics],
                                   volume_analysis: Optional[VolumeAnalysis],
                                   price_prediction: Optional[PricePrediction]) -> float:
        """Calculate investment suitability score."""
        score = 0.0
        
        # Profit potential (30%)
        profit_margin = item.profit_calc.current_profit_margin
        if profit_margin > 10:
            score += 0.3
        elif profit_margin > 5:
            score += 0.2
        elif profit_margin > 2:
            score += 0.1
        
        # Risk assessment (25%)
        if risk_metrics:
            risk_score = (100 - risk_metrics.overall_risk_score) / 100
            score += 0.25 * risk_score
        else:
            score += 0.125  # Neutral risk
        
        # Liquidity (25%)
        if volume_analysis:
            if volume_analysis.liquidity_level in ['extreme', 'very_high', 'high']:
                score += 0.25
            elif volume_analysis.liquidity_level in ['medium']:
                score += 0.15
            elif volume_analysis.liquidity_level in ['low']:
                score += 0.05
        
        # Price prediction (20%)
        if price_prediction and price_prediction.confidence_24h > 0.6:
            if price_prediction.trend_direction == 'bullish':
                score += 0.2
            elif price_prediction.trend_direction == 'neutral':
                score += 0.1
        else:
            score += 0.05  # Neutral prediction
        
        return min(1.0, score)
    
    async def _prepare_portfolio_data(self, investment_universe: List[Dict]) -> Dict[str, Any]:
        """Prepare data needed for portfolio optimization."""
        n_items = len(investment_universe)
        
        # Expected returns vector
        expected_returns = np.array([item['expected_return'] for item in investment_universe])
        
        # Risk vector (convert risk scores to volatility estimates)
        risk_scores = np.array([item['risk_score'] for item in investment_universe])
        volatilities = risk_scores / 1000 + 0.01  # Convert to reasonable volatility range
        
        # Correlation matrix (simplified - would use historical price correlations)
        correlation_matrix = await self._estimate_correlation_matrix(investment_universe)
        
        # Covariance matrix
        cov_matrix = np.outer(volatilities, volatilities) * correlation_matrix
        
        # Additional constraints
        min_weights = np.full(n_items, self.min_position_size)
        max_weights = np.array([
            min(self.max_position_size, item['ge_limit'] * item['current_price'] / 1000000)  # GE limit constraint
            for item in investment_universe
        ])
        
        return {
            'items': investment_universe,
            'expected_returns': expected_returns,
            'volatilities': volatilities,
            'correlation_matrix': correlation_matrix,
            'cov_matrix': cov_matrix,
            'min_weights': min_weights,
            'max_weights': max_weights,
            'n_items': n_items
        }
    
    async def _estimate_correlation_matrix(self, investment_universe: List[Dict]) -> np.ndarray:
        """Estimate correlation matrix between items."""
        n_items = len(investment_universe)
        
        # For now, use a simple model based on item categories
        # In practice, this would use historical price correlations
        correlation_matrix = np.eye(n_items)  # Start with identity matrix
        
        for i in range(n_items):
            for j in range(i + 1, n_items):
                # Estimate correlation based on item similarity
                item1 = investment_universe[i]
                item2 = investment_universe[j]
                
                # Items in similar price ranges tend to be more correlated
                price_ratio = min(item1['current_price'], item2['current_price']) / max(item1['current_price'], item2['current_price'])
                
                # Similar profit margins suggest similar market dynamics
                return_diff = abs(item1['expected_return'] - item2['expected_return'])
                
                # Calculate correlation estimate
                base_correlation = 0.1  # Base correlation
                price_correlation = price_ratio * 0.2
                return_correlation = max(0, 0.3 - return_diff * 2)
                
                correlation = min(0.8, base_correlation + price_correlation + return_correlation)
                
                correlation_matrix[i, j] = correlation
                correlation_matrix[j, i] = correlation
        
        return correlation_matrix
    
    async def _optimize_risk_parity(self, portfolio_data: Dict, total_capital: int,
                                  constraints: Optional[Dict]) -> List[PortfolioAllocation]:
        """Optimize portfolio using risk parity approach."""
        logger.debug("🎯 Optimizing portfolio using Risk Parity")
        
        n_items = portfolio_data['n_items']
        items = portfolio_data['items']
        cov_matrix = portfolio_data['cov_matrix']
        volatilities = portfolio_data['volatilities']
        
        # Risk parity objective: equal risk contribution
        def risk_parity_objective(weights):
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            marginal_contrib = np.dot(cov_matrix, weights) / portfolio_vol
            contrib = weights * marginal_contrib
            target_contrib = portfolio_vol / n_items  # Equal risk contribution
            return np.sum((contrib - target_contrib) ** 2)
        
        # Constraints
        constraints_list = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},  # Weights sum to 1
        ]
        
        # Bounds
        bounds = [(portfolio_data['min_weights'][i], portfolio_data['max_weights'][i]) 
                 for i in range(n_items)]
        
        # Initial guess (equal weights)
        x0 = np.ones(n_items) / n_items
        
        # Optimize
        result = optimize.minimize(
            risk_parity_objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list,
            options={'maxiter': 1000}
        )
        
        if result.success:
            optimal_weights = result.x
        else:
            logger.warning("Risk parity optimization failed, using equal weights")
            optimal_weights = np.ones(n_items) / n_items
        
        # Convert to allocations
        return self._weights_to_allocations(optimal_weights, portfolio_data, total_capital)
    
    async def _optimize_mean_variance(self, portfolio_data: Dict, total_capital: int,
                                    constraints: Optional[Dict]) -> List[PortfolioAllocation]:
        """Optimize portfolio using Modern Portfolio Theory (mean-variance)."""
        logger.debug("🎯 Optimizing portfolio using Mean-Variance (MPT)")
        
        expected_returns = portfolio_data['expected_returns']
        cov_matrix = portfolio_data['cov_matrix']
        n_items = portfolio_data['n_items']
        
        # Target return (can be parameterized)
        target_return = np.mean(expected_returns) * 1.2  # 20% above average
        
        # Objective: minimize portfolio variance
        def portfolio_variance(weights):
            return np.dot(weights.T, np.dot(cov_matrix, weights))
        
        # Constraints
        constraints_list = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},  # Weights sum to 1
            {'type': 'eq', 'fun': lambda w: np.dot(w, expected_returns) - target_return}  # Target return
        ]
        
        # Bounds
        bounds = [(portfolio_data['min_weights'][i], portfolio_data['max_weights'][i]) 
                 for i in range(n_items)]
        
        # Initial guess
        x0 = np.ones(n_items) / n_items
        
        # Optimize
        result = optimize.minimize(
            portfolio_variance,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list,
            options={'maxiter': 1000}
        )
        
        if result.success:
            optimal_weights = result.x
        else:
            logger.warning("Mean-variance optimization failed, using risk parity fallback")
            return await self._optimize_risk_parity(portfolio_data, total_capital, constraints)
        
        return self._weights_to_allocations(optimal_weights, portfolio_data, total_capital)
    
    async def _optimize_kelly_criterion(self, portfolio_data: Dict, total_capital: int,
                                      constraints: Optional[Dict]) -> List[PortfolioAllocation]:
        """Optimize portfolio using Kelly Criterion for position sizing."""
        logger.debug("🎯 Optimizing portfolio using Kelly Criterion")
        
        items = portfolio_data['items']
        expected_returns = portfolio_data['expected_returns']
        volatilities = portfolio_data['volatilities']
        
        kelly_weights = np.zeros(len(items))
        
        for i, (item, expected_return, volatility) in enumerate(zip(items, expected_returns, volatilities)):
            if volatility > 0 and expected_return > 0:
                # Kelly formula: f = (bp - q) / b
                # where p = probability of win, q = probability of loss, b = odds
                
                # Estimate win probability from expected return and volatility
                win_prob = norm.cdf(expected_return / volatility) if volatility > 0 else 0.5
                loss_prob = 1 - win_prob
                
                if win_prob > 0.5:  # Only bet if positive expectation
                    # Simplified Kelly calculation
                    kelly_fraction = (expected_return * win_prob - loss_prob) / expected_return
                    kelly_weight = max(0, min(self.max_kelly_position, kelly_fraction * self.kelly_fraction))
                    kelly_weights[i] = kelly_weight
        
        # Normalize weights
        total_kelly = np.sum(kelly_weights)
        if total_kelly > 0:
            kelly_weights = kelly_weights / total_kelly
        else:
            # Fallback to equal weights if no positive Kelly positions
            kelly_weights = np.ones(len(items)) / len(items)
        
        return self._weights_to_allocations(kelly_weights, portfolio_data, total_capital)
    
    async def _optimize_equal_weight(self, portfolio_data: Dict, total_capital: int,
                                   constraints: Optional[Dict]) -> List[PortfolioAllocation]:
        """Simple equal weight optimization."""
        logger.debug("🎯 Optimizing portfolio using Equal Weight")
        
        n_items = portfolio_data['n_items']
        equal_weights = np.ones(n_items) / n_items
        
        return self._weights_to_allocations(equal_weights, portfolio_data, total_capital)
    
    def _weights_to_allocations(self, weights: np.ndarray, portfolio_data: Dict,
                              total_capital: int) -> List[PortfolioAllocation]:
        """Convert optimization weights to portfolio allocations."""
        allocations = []
        items = portfolio_data['items']
        cov_matrix = portfolio_data['cov_matrix']
        
        # Calculate portfolio-level risk contributions
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        marginal_contrib = np.dot(cov_matrix, weights) / portfolio_vol if portfolio_vol > 0 else np.zeros(len(weights))
        
        for i, (weight, item) in enumerate(zip(weights, items)):
            if weight > 0.001:  # Only include meaningful allocations
                target_amount_gp = int(weight * total_capital)
                current_price = item['current_price']
                target_quantity = max(1, int(target_amount_gp / current_price))
                
                # Adjust for actual quantity and price
                actual_amount_gp = target_quantity * current_price
                actual_weight = actual_amount_gp / total_capital
                
                allocation = PortfolioAllocation(
                    item_id=item['item_id'],
                    item_name=item['item_name'],
                    target_weight=actual_weight,
                    target_amount_gp=actual_amount_gp,
                    target_quantity=target_quantity,
                    current_weight=0.0,  # Would be filled from current holdings
                    current_amount_gp=0,  # Would be filled from current holdings
                    rebalance_needed=True,  # Always true for new allocations
                    expected_return=item['expected_return'],
                    risk_contribution=weights[i] * marginal_contrib[i] / portfolio_vol if portfolio_vol > 0 else 0,
                    liquidity_score=item['liquidity_score'],
                    ge_limit_utilization=target_quantity / item['ge_limit'] if item['ge_limit'] > 0 else 0
                )
                
                allocations.append(allocation)
        
        return allocations
    
    def _calculate_portfolio_metrics(self, allocations: List[PortfolioAllocation],
                                   portfolio_data: Dict) -> PortfolioMetrics:
        """Calculate comprehensive portfolio metrics."""
        if not allocations:
            return PortfolioMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        # Portfolio weights
        total_value = sum(a.target_amount_gp for a in allocations)
        weights = np.array([a.target_weight for a in allocations])
        
        # Expected return
        expected_returns = np.array([a.expected_return for a in allocations])
        portfolio_return = np.dot(weights, expected_returns)
        
        # Portfolio risk
        relevant_cov = portfolio_data['cov_matrix'][:len(allocations), :len(allocations)]
        portfolio_variance = np.dot(weights.T, np.dot(relevant_cov, weights))
        portfolio_risk = np.sqrt(portfolio_variance)
        
        # Sharpe ratio
        excess_return = portfolio_return - self.risk_free_rate
        sharpe_ratio = excess_return / portfolio_risk if portfolio_risk > 0 else 0
        
        # Sortino ratio (simplified - assumes downside deviation = risk/2)
        downside_risk = portfolio_risk / 2
        sortino_ratio = excess_return / downside_risk if downside_risk > 0 else 0
        
        # Diversification ratio
        weighted_avg_vol = np.dot(weights, portfolio_data['volatilities'][:len(allocations)])
        diversification_ratio = weighted_avg_vol / portfolio_risk if portfolio_risk > 0 else 1
        
        # Liquidity score
        liquidity_scores = np.array([a.liquidity_score for a in allocations])
        portfolio_liquidity = np.dot(weights, liquidity_scores)
        
        # Risk parity score (how close to equal risk contribution)
        risk_contribs = np.array([a.risk_contribution for a in allocations])
        target_contrib = 1.0 / len(allocations)
        risk_parity_score = 1.0 - np.std(risk_contribs - target_contrib)
        
        return PortfolioMetrics(
            total_value=total_value,
            expected_return=portfolio_return,
            portfolio_risk=portfolio_risk,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=0.0,  # Would need historical data
            diversification_ratio=diversification_ratio,
            liquidity_score=portfolio_liquidity,
            risk_parity_score=max(0, risk_parity_score)
        )
    
    async def _generate_rebalance_actions(self, user_id: int, allocations: List[PortfolioAllocation],
                                        total_capital: int) -> List[Dict[str, Any]]:
        """Generate specific rebalancing actions."""
        actions = []
        
        # Get current GE limit usage
        current_limits = await self._get_user_ge_limits(user_id)
        
        for allocation in allocations:
            # Check if we need to buy this item
            current_quantity = current_limits.get(allocation.item_id, 0)
            target_quantity = allocation.target_quantity
            
            if target_quantity > current_quantity:
                quantity_to_buy = target_quantity - current_quantity
                action = {
                    'action': 'buy',
                    'item_id': allocation.item_id,
                    'item_name': allocation.item_name,
                    'quantity': quantity_to_buy,
                    'estimated_cost': quantity_to_buy * (allocation.target_amount_gp / allocation.target_quantity),
                    'priority': 'high' if allocation.target_weight > 0.1 else 'medium',
                    'rationale': f"Portfolio optimization recommends {allocation.target_weight:.1%} allocation"
                }
                actions.append(action)
            elif target_quantity < current_quantity:
                quantity_to_sell = current_quantity - target_quantity
                action = {
                    'action': 'sell',
                    'item_id': allocation.item_id,
                    'item_name': allocation.item_name,
                    'quantity': quantity_to_sell,
                    'estimated_revenue': quantity_to_sell * (allocation.target_amount_gp / allocation.target_quantity),
                    'priority': 'medium',
                    'rationale': f"Reduce allocation to optimal {allocation.target_weight:.1%}"
                }
                actions.append(action)
        
        # Sort by priority and expected impact
        actions.sort(key=lambda x: (
            0 if x['priority'] == 'high' else 1,
            -x.get('estimated_cost', x.get('estimated_revenue', 0))
        ))
        
        return actions
    
    # Helper methods
    
    def _get_volume_score(self, volume_analysis: Optional[VolumeAnalysis]) -> float:
        """Convert volume analysis to numerical score."""
        if not volume_analysis:
            return 0.3
        
        scores = {
            'extreme': 1.0, 'very_high': 0.9, 'high': 0.8,
            'medium': 0.6, 'low': 0.4, 'very_low': 0.2, 'minimal': 0.1
        }
        return scores.get(volume_analysis.liquidity_level, 0.3)
    
    def _get_liquidity_score(self, volume_analysis: Optional[VolumeAnalysis]) -> float:
        """Get liquidity score for portfolio optimization."""
        if not volume_analysis:
            return 0.3
        
        base_score = self._get_volume_score(volume_analysis)
        
        # Boost score based on volume ratio
        if volume_analysis.volume_ratio_daily > 1.5:
            base_score *= 1.2
        elif volume_analysis.volume_ratio_daily < 0.5:
            base_score *= 0.8
        
        return min(1.0, base_score)
    
    def _allocation_to_dict(self, allocation: PortfolioAllocation) -> Dict[str, Any]:
        """Convert allocation to dictionary."""
        return {
            'item_id': allocation.item_id,
            'item_name': allocation.item_name,
            'target_weight': round(allocation.target_weight, 4),
            'target_amount_gp': allocation.target_amount_gp,
            'target_quantity': allocation.target_quantity,
            'expected_return': round(allocation.expected_return, 4),
            'risk_contribution': round(allocation.risk_contribution, 4),
            'liquidity_score': round(allocation.liquidity_score, 2),
            'ge_limit_utilization': round(allocation.ge_limit_utilization, 2)
        }
    
    def _metrics_to_dict(self, metrics: PortfolioMetrics) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'total_value': metrics.total_value,
            'expected_return': round(metrics.expected_return, 4),
            'portfolio_risk': round(metrics.portfolio_risk, 4),
            'sharpe_ratio': round(metrics.sharpe_ratio, 2),
            'sortino_ratio': round(metrics.sortino_ratio, 2),
            'diversification_ratio': round(metrics.diversification_ratio, 2),
            'liquidity_score': round(metrics.liquidity_score, 2),
            'risk_parity_score': round(metrics.risk_parity_score, 2)
        }
    
    # Database helper methods
    
    @sync_to_async
    def _get_risk_metrics(self, item_id: int) -> Optional[RiskMetrics]:
        """Get risk metrics for item."""
        try:
            return RiskMetrics.objects.get(item__item_id=item_id)
        except RiskMetrics.DoesNotExist:
            return None
    
    @sync_to_async
    def _get_volume_analysis(self, item_id: int) -> Optional[VolumeAnalysis]:
        """Get volume analysis for item."""
        try:
            return VolumeAnalysis.objects.get(item__item_id=item_id)
        except VolumeAnalysis.DoesNotExist:
            return None
    
    @sync_to_async
    def _get_latest_price_prediction(self, item_id: int) -> Optional[PricePrediction]:
        """Get latest price prediction for item."""
        try:
            return PricePrediction.objects.filter(
                item__item_id=item_id
            ).order_by('-prediction_timestamp').first()
        except PricePrediction.DoesNotExist:
            return None
    
    @sync_to_async
    def _get_user_ge_limits(self, user_id: int) -> Dict[int, int]:
        """Get current GE limit usage for user."""
        try:
            limits = GELimitEntry.objects.filter(
                user_id=user_id, 
                is_active=True
            ).values('item__item_id', 'quantity_bought')
            
            return {limit['item__item_id']: limit['quantity_bought'] for limit in limits}
        except Exception:
            return {}


# Global portfolio optimizer instance
portfolio_optimizer = PortfolioOptimizer()