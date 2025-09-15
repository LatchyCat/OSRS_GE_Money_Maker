"""
Advanced portfolio optimization for multi-item high alch strategies.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy.optimize import minimize
from dataclasses import dataclass
from decimal import Decimal

from apps.items.models import Item


@dataclass
class ItemAllocation:
    """Represents an item's allocation in a portfolio."""
    item: Item
    allocation_percentage: float
    quantity: int
    expected_return: float
    risk_score: float
    time_to_acquire_hours: float


class PortfolioOptimizer:
    """
    Advanced portfolio optimization using Modern Portfolio Theory adapted for OSRS high alching.
    """
    
    def __init__(self):
        self.risk_free_rate = 0.0  # Assume no risk-free option in OSRS
    
    def optimize_portfolio(self, items: List[Dict], available_capital: int, 
                          required_profit: int, risk_tolerance: str = 'moderate',
                          time_constraint_days: Optional[int] = None) -> List[ItemAllocation]:
        """
        Optimize portfolio allocation using risk-adjusted returns.
        
        Args:
            items: List of item dictionaries with profit and risk data
            available_capital: Total GP available for investment
            required_profit: Target profit to achieve
            risk_tolerance: 'conservative', 'moderate', or 'aggressive'
            time_constraint_days: Maximum time constraint in days
        
        Returns:
            List of ItemAllocation objects with optimal allocations
        """
        if not items or available_capital <= 0:
            return []
        
        # Filter items by time constraint if provided
        if time_constraint_days:
            max_hours = time_constraint_days * 24
            items = [item for item in items if self._estimate_buy_time(item) <= max_hours]
        
        if not items:
            return []
        
        # Calculate expected returns and risk for each item
        returns = np.array([self._calculate_expected_return(item) for item in items])
        risks = np.array([item['price_volatility'] for item in items])
        
        # Create correlation matrix (simplified - assume some correlation between similar items)
        correlation_matrix = self._estimate_correlation_matrix(items)
        
        # Calculate covariance matrix
        risk_matrix = np.outer(risks, risks) * correlation_matrix
        
        # Set up optimization constraints
        constraints = self._setup_constraints(items, available_capital, required_profit)
        
        # Set risk tolerance parameter
        risk_aversion = self._get_risk_aversion(risk_tolerance)
        
        # Optimize allocation using mean-variance optimization
        optimal_weights = self._optimize_weights(returns, risk_matrix, constraints, risk_aversion)
        
        # Convert weights to allocations
        allocations = self._weights_to_allocations(optimal_weights, items, available_capital)
        
        return allocations
    
    def _calculate_expected_return(self, item: Dict) -> float:
        """Calculate expected return per GP invested."""
        buy_price = item['buy_price']
        profit_per_item = item['profit_per_item']
        
        if buy_price <= 0:
            return 0.0
        
        return profit_per_item / buy_price
    
    def _estimate_buy_time(self, item: Dict) -> float:
        """Estimate time to buy items considering GE limits."""
        ge_limit = item['ge_limit']
        daily_volume = item['daily_volume']
        
        # Estimate based on GE limit (6 resets per day)
        daily_buyable = ge_limit * 6
        
        # Consider market volume constraints
        effective_daily_limit = min(daily_buyable, daily_volume * 0.1)  # Don't exceed 10% of daily volume
        
        # Return time for one day's worth (used as baseline)
        return 24.0
    
    def _estimate_correlation_matrix(self, items: List[Dict]) -> np.ndarray:
        """
        Estimate correlation matrix between items.
        In reality, this would use historical price data.
        """
        n = len(items)
        correlation_matrix = np.eye(n)  # Start with identity matrix
        
        for i in range(n):
            for j in range(i+1, n):
                # Simple heuristic: similar items have higher correlation
                item1 = items[i]['item']
                item2 = items[j]['item']
                
                # Check if items are in similar categories or price ranges
                correlation = 0.1  # Base correlation
                
                # Similar high alch values suggest similar item types
                alch_diff = abs(item1.high_alch_value - item2.high_alch_value)
                max_alch = max(item1.high_alch_value, item2.high_alch_value)
                
                if max_alch > 0:
                    alch_similarity = 1.0 - (alch_diff / max_alch)
                    correlation += alch_similarity * 0.3
                
                # Similar buy prices suggest similar market behavior
                price_diff = abs(items[i]['buy_price'] - items[j]['buy_price'])
                max_price = max(items[i]['buy_price'], items[j]['buy_price'])
                
                if max_price > 0:
                    price_similarity = 1.0 - (price_diff / max_price)
                    correlation += price_similarity * 0.2
                
                correlation = min(correlation, 0.8)  # Cap correlation
                correlation_matrix[i][j] = correlation
                correlation_matrix[j][i] = correlation
        
        return correlation_matrix
    
    def _setup_constraints(self, items: List[Dict], available_capital: int, 
                          required_profit: int) -> List[Dict]:
        """Set up optimization constraints."""
        n = len(items)
        
        constraints = []
        
        # Constraint 1: Weights sum to 1
        constraints.append({
            'type': 'eq',
            'fun': lambda w: np.sum(w) - 1.0
        })
        
        # Constraint 2: All weights non-negative
        for i in range(n):
            constraints.append({
                'type': 'ineq',
                'fun': lambda w, i=i: w[i]
            })
        
        # Constraint 3: No single item should exceed 50% of portfolio (diversification)
        for i in range(n):
            constraints.append({
                'type': 'ineq',
                'fun': lambda w, i=i: 0.5 - w[i]
            })
        
        # Constraint 4: Portfolio should generate minimum required profit
        def min_profit_constraint(w):
            total_profit = 0
            for i, weight in enumerate(w):
                item = items[i]
                allocation = available_capital * weight
                items_buyable = int(allocation // item['buy_price'])
                profit = items_buyable * item['profit_per_item']
                total_profit += profit
            return total_profit - required_profit
        
        constraints.append({
            'type': 'ineq',
            'fun': min_profit_constraint
        })
        
        return constraints
    
    def _get_risk_aversion(self, risk_tolerance: str) -> float:
        """Convert risk tolerance to numerical risk aversion parameter."""
        risk_aversion_map = {
            'aggressive': 1.0,
            'moderate': 3.0,
            'conservative': 8.0
        }
        return risk_aversion_map.get(risk_tolerance, 3.0)
    
    def _optimize_weights(self, returns: np.ndarray, risk_matrix: np.ndarray, 
                         constraints: List[Dict], risk_aversion: float) -> np.ndarray:
        """
        Optimize portfolio weights using mean-variance optimization.
        """
        n = len(returns)
        
        # Objective function: maximize return - risk_aversion * risk
        def objective(weights):
            portfolio_return = np.dot(weights, returns)
            portfolio_risk = np.sqrt(np.dot(weights, np.dot(risk_matrix, weights)))
            return -(portfolio_return - risk_aversion * portfolio_risk)  # Minimize negative utility
        
        # Initial guess: equal weights
        initial_weights = np.ones(n) / n
        
        # Bounds: each weight between 0 and 1
        bounds = [(0, 1) for _ in range(n)]
        
        try:
            # Optimize
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )
            
            if result.success:
                return result.x
            else:
                # Fallback to equal weights if optimization fails
                return initial_weights
        
        except Exception:
            # Fallback to equal weights on any error
            return initial_weights
    
    def _weights_to_allocations(self, weights: np.ndarray, items: List[Dict], 
                               available_capital: int) -> List[ItemAllocation]:
        """Convert optimization weights to ItemAllocation objects."""
        allocations = []
        
        for i, weight in enumerate(weights):
            if weight < 0.01:  # Skip very small allocations
                continue
            
            item_data = items[i]
            item = item_data['item']
            
            allocation_capital = int(available_capital * weight)
            quantity = allocation_capital // item_data['buy_price']
            
            if quantity > 0:
                expected_return = quantity * item_data['profit_per_item']
                risk_score = item_data['price_volatility']
                time_hours = self._calculate_buy_time_for_quantity(item_data, quantity)
                
                allocation = ItemAllocation(
                    item=item,
                    allocation_percentage=weight * 100,
                    quantity=quantity,
                    expected_return=expected_return,
                    risk_score=risk_score,
                    time_to_acquire_hours=time_hours
                )
                
                allocations.append(allocation)
        
        return sorted(allocations, key=lambda x: x.allocation_percentage, reverse=True)
    
    def _calculate_buy_time_for_quantity(self, item_data: Dict, quantity: int) -> float:
        """Calculate time needed to buy specific quantity of an item."""
        ge_limit = item_data['ge_limit']
        daily_volume = item_data['daily_volume']
        
        # Calculate based on GE limits (6 resets per day)
        daily_buyable = ge_limit * 6
        
        # Consider volume constraints
        effective_daily_limit = min(daily_buyable, daily_volume * 0.1)
        
        if effective_daily_limit <= 0:
            return float('inf')
        
        days_needed = quantity / effective_daily_limit
        return days_needed * 24  # Convert to hours
    
    def calculate_portfolio_metrics(self, allocations: List[ItemAllocation]) -> Dict:
        """Calculate portfolio-level metrics."""
        if not allocations:
            return {
                'total_expected_return': 0,
                'total_risk_score': 0,
                'max_time_to_complete': 0,
                'diversification_ratio': 0,
                'sharpe_ratio': 0
            }
        
        total_expected_return = sum(alloc.expected_return for alloc in allocations)
        max_time_to_complete = max(alloc.time_to_acquire_hours for alloc in allocations)
        
        # Weighted average risk
        total_allocation = sum(alloc.allocation_percentage for alloc in allocations)
        if total_allocation > 0:
            weighted_risk = sum(
                alloc.risk_score * (alloc.allocation_percentage / total_allocation)
                for alloc in allocations
            )
        else:
            weighted_risk = 0
        
        # Diversification ratio (1/max_weight)
        max_weight = max(alloc.allocation_percentage for alloc in allocations) / 100
        diversification_ratio = 1 / max_weight if max_weight > 0 else 0
        
        # Simplified Sharpe ratio (return/risk)
        sharpe_ratio = total_expected_return / weighted_risk if weighted_risk > 0 else 0
        
        return {
            'total_expected_return': total_expected_return,
            'total_risk_score': weighted_risk,
            'max_time_to_complete': max_time_to_complete,
            'diversification_ratio': diversification_ratio,
            'sharpe_ratio': sharpe_ratio
        }


class SimplePortfolioOptimizer:
    """
    Simpler portfolio optimizer for cases where advanced optimization isn't needed.
    """
    
    def optimize_simple(self, items: List[Dict], available_capital: int, 
                       required_profit: int, max_items: int = 5) -> List[ItemAllocation]:
        """
        Simple optimization using profit-to-risk ratios.
        """
        if not items:
            return []
        
        # Calculate profit-to-risk ratio for each item
        scored_items = []
        for item_data in items:
            profit_per_gp = item_data['profit_per_item'] / item_data['buy_price']
            risk_adjusted_return = profit_per_gp / (1 + item_data['price_volatility'])
            
            scored_items.append({
                'item_data': item_data,
                'score': risk_adjusted_return
            })
        
        # Sort by score and select top items
        scored_items.sort(key=lambda x: x['score'], reverse=True)
        selected_items = scored_items[:max_items]
        
        # Allocate capital proportionally to scores
        total_score = sum(item['score'] for item in selected_items)
        allocations = []
        
        for item in selected_items:
            if total_score <= 0:
                break
            
            weight = item['score'] / total_score
            item_data = item['item_data']
            
            allocation_capital = int(available_capital * weight)
            quantity = allocation_capital // item_data['buy_price']
            
            if quantity > 0:
                expected_return = quantity * item_data['profit_per_item']
                time_hours = self._estimate_time(item_data, quantity)
                
                allocation = ItemAllocation(
                    item=item_data['item'],
                    allocation_percentage=weight * 100,
                    quantity=quantity,
                    expected_return=expected_return,
                    risk_score=item_data['price_volatility'],
                    time_to_acquire_hours=time_hours
                )
                
                allocations.append(allocation)
        
        return allocations
    
    def _estimate_time(self, item_data: Dict, quantity: int) -> float:
        """Estimate time to acquire quantity."""
        ge_limit = item_data['ge_limit']
        daily_buyable = ge_limit * 6  # 6 resets per day
        
        if daily_buyable <= 0:
            return float('inf')
        
        days_needed = quantity / daily_buyable
        return days_needed * 24