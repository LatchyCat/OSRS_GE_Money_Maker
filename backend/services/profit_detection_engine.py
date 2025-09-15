"""
Advanced Profit Detection Engine for Multi-Tier Margin Analysis
Handles 1m+ margin flips, volume analysis, and intelligent profit calculations.
"""

import logging
from typing import Dict, List, Tuple, Optional
from django.db.models import Q, F, Max, Min, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from asgiref.sync import sync_to_async
from apps.items.models import Item
from apps.prices.models import ProfitCalculation, HistoricalPrice
import statistics

logger = logging.getLogger(__name__)

class ProfitTier:
    """Represents a profit tier classification with metadata."""
    def __init__(self, name: str, min_profit: int, max_profit: int, 
                 description: str, risk_level: str, liquidity_req: str):
        self.name = name
        self.min_profit = min_profit
        self.max_profit = max_profit
        self.description = description
        self.risk_level = risk_level
        self.liquidity_req = liquidity_req

class AdvancedProfitDetectionEngine:
    """
    Advanced engine for detecting profitable trading opportunities across all margin tiers.
    """
    
    def __init__(self):
        # Define profit tiers with comprehensive analysis
        self.profit_tiers = {
            'whale_tier': ProfitTier(
                name='Whale Trading',
                min_profit=10_000_000,  # 10m+
                max_profit=float('inf'),
                description='Ultra-high value trades for massive capital players',
                risk_level='extreme',
                liquidity_req='very_low'
            ),
            'mega_margin': ProfitTier(
                name='Mega Margin Flips',
                min_profit=5_000_000,   # 5m-10m
                max_profit=10_000_000,
                description='Extremely high-margin flips for serious traders',
                risk_level='very_high',
                liquidity_req='low'
            ),
            'million_margin': ProfitTier(
                name='Million Margin Flips',
                min_profit=1_000_000,   # 1m-5m
                max_profit=5_000_000,
                description='Million+ GP margin opportunities for experienced traders',
                risk_level='high',
                liquidity_req='medium'
            ),
            'large_margin': ProfitTier(
                name='Large Margin Flips',
                min_profit=100_000,     # 100k-1m
                max_profit=1_000_000,
                description='Substantial profit opportunities for intermediate capital',
                risk_level='medium_high',
                liquidity_req='medium'
            ),
            'medium_margin': ProfitTier(
                name='Medium Margin Flips',
                min_profit=10_000,      # 10k-100k
                max_profit=100_000,
                description='Steady profit flips for regular trading',
                risk_level='medium',
                liquidity_req='high'
            ),
            'small_margin': ProfitTier(
                name='Small Margin Flips',
                min_profit=1_000,       # 1k-10k
                max_profit=10_000,
                description='High-frequency trading opportunities',
                risk_level='low',
                liquidity_req='very_high'
            ),
            'micro_margin': ProfitTier(
                name='Micro Margin Flips',
                min_profit=100,         # 100-1k
                max_profit=1_000,
                description='Volume-based micro-profit opportunities',
                risk_level='very_low',
                liquidity_req='extreme'
            )
        }
        
        # Volume analysis thresholds
        self.volume_thresholds = {
            'extreme': 10000,  # 10k+ daily volume
            'very_high': 5000, # 5k-10k daily volume
            'high': 1000,      # 1k-5k daily volume
            'medium': 500,     # 500-1k daily volume
            'low': 100,        # 100-500 daily volume
            'very_low': 50,    # 50-100 daily volume
            'minimal': 10      # 10-50 daily volume
        }

    def analyze_item_profit_potential(self, item: Item, capital: int = 0) -> Dict:
        """
        Comprehensive profit analysis for a single item.
        """
        try:
            profit_calc = ProfitCalculation.objects.filter(item=item).first()
            if not profit_calc:
                return self._create_empty_analysis(item, "No profit calculation available")
            
            # Basic profit metrics
            current_profit = getattr(profit_calc, 'current_profit', 0)
            profit_margin = getattr(profit_calc, 'current_profit_margin', 0)
            buy_price = getattr(profit_calc, 'current_buy_price', 0)
            sell_price = getattr(profit_calc, 'current_sell_price', 0)
            
            # Determine profit tier
            profit_tier = self._classify_profit_tier(current_profit)
            
            # Volume analysis
            volume_analysis = self._analyze_volume(item, profit_calc)
            
            # Risk assessment
            risk_analysis = self._assess_risk(item, profit_calc, volume_analysis)
            
            # Capital efficiency
            capital_analysis = self._analyze_capital_efficiency(
                item, profit_calc, capital, current_profit
            )
            
            # Historical performance
            historical_analysis = self._analyze_historical_performance(item)
            
            # Market timing
            timing_analysis = self._analyze_market_timing(item, profit_calc)
            
            return {
                'item_id': item.item_id,
                'item_name': item.name,
                'current_profit': current_profit,
                'profit_margin': profit_margin,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'profit_tier': profit_tier,
                'volume_analysis': volume_analysis,
                'risk_analysis': risk_analysis,
                'capital_analysis': capital_analysis,
                'historical_analysis': historical_analysis,
                'timing_analysis': timing_analysis,
                'overall_score': self._calculate_overall_score(
                    profit_tier, volume_analysis, risk_analysis, capital_analysis
                ),
                'recommendation': self._generate_recommendation(
                    profit_tier, volume_analysis, risk_analysis, capital_analysis
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing item {item.item_id}: {e}")
            return self._create_empty_analysis(item, f"Analysis error: {str(e)}")

    def find_million_margin_opportunities(self, capital: int = 0, limit: int = 50) -> List[Dict]:
        """
        Find opportunities with 1m+ profit margins.
        """
        logger.info("🎯 Searching for million+ margin opportunities...")
        
        # Query for high-profit items
        high_profit_items = Item.objects.select_related('profit_calc').filter(
            Q(is_active=True) &
            Q(profit_calc__current_profit__gte=1_000_000) &  # 1m+ profit
            Q(profit_calc__current_buy_price__gt=0) &
            Q(profit_calc__current_sell_price__gt=0)
        ).order_by('-profit_calc__current_profit')
        
        if capital > 0:
            # Filter by affordable items
            high_profit_items = high_profit_items.filter(
                profit_calc__current_buy_price__lte=capital
            )
        
        opportunities = []
        for item in high_profit_items[:limit * 2]:  # Get more for filtering
            analysis = self.analyze_item_profit_potential(item, capital)
            
            # Only include items with meaningful volume or special characteristics
            if (analysis['volume_analysis']['daily_volume'] > 10 or
                analysis['profit_tier']['name'] in ['Million Margin Flips', 'Mega Margin Flips', 'Whale Trading'] or
                item.high_alch > analysis['buy_price'] + 1_000_000):  # High alch profit
                
                opportunities.append(analysis)
                
                if len(opportunities) >= limit:
                    break
        
        logger.info(f"✅ Found {len(opportunities)} million+ margin opportunities")
        return opportunities

    def find_opportunities_by_tier(self, tier_name: str, capital: int = 0, 
                                 limit: int = 50, sort_by: str = 'profit') -> List[Dict]:
        """
        Find opportunities within a specific profit tier.
        """
        if tier_name not in self.profit_tiers:
            logger.error(f"Invalid tier name: {tier_name}")
            return []
        
        tier = self.profit_tiers[tier_name]
        logger.info(f"🎯 Searching for {tier.description} opportunities...")
        
        # Build query based on tier
        query_filters = Q(is_active=True) & Q(profit_calc__current_profit__gte=tier.min_profit)
        
        if tier.max_profit != float('inf'):
            query_filters &= Q(profit_calc__current_profit__lt=tier.max_profit)
        
        if capital > 0:
            query_filters &= Q(profit_calc__current_buy_price__lte=capital)
        
        # Order by requested criteria
        order_mapping = {
            'profit': '-profit_calc__current_profit',
            'margin': '-profit_calc__current_profit_margin',
            'volume': '-profit_calc__daily_volume',
            'value': '-profit_calc__current_sell_price'
        }
        order_field = order_mapping.get(sort_by, '-profit_calc__current_profit')
        
        items = Item.objects.select_related('profit_calc').filter(
            query_filters
        ).order_by(order_field)[:limit * 2]
        
        opportunities = []
        for item in items:
            analysis = self.analyze_item_profit_potential(item, capital)
            opportunities.append(analysis)
            
            if len(opportunities) >= limit:
                break
        
        logger.info(f"✅ Found {len(opportunities)} {tier_name} opportunities")
        return opportunities

    def get_capital_optimized_portfolio(self, capital: int, 
                                      risk_preference: str = 'balanced') -> Dict:
        """
        Generate capital-optimized trading portfolio.
        """
        logger.info(f"💰 Optimizing portfolio for {capital:,} GP capital...")
        
        portfolio = {
            'total_capital': capital,
            'risk_preference': risk_preference,
            'allocations': {},
            'expected_returns': {},
            'recommendations': []
        }
        
        # Define allocation strategy based on risk preference
        allocation_strategies = {
            'conservative': {
                'small_margin': 0.4,
                'medium_margin': 0.3,
                'large_margin': 0.2,
                'million_margin': 0.1
            },
            'balanced': {
                'small_margin': 0.2,
                'medium_margin': 0.3,
                'large_margin': 0.3,
                'million_margin': 0.2
            },
            'aggressive': {
                'small_margin': 0.1,
                'medium_margin': 0.2,
                'large_margin': 0.3,
                'million_margin': 0.4
            },
            'whale': {
                'large_margin': 0.2,
                'million_margin': 0.3,
                'mega_margin': 0.3,
                'whale_tier': 0.2
            }
        }
        
        # Select strategy based on capital size and preference
        if capital >= 100_000_000:  # 100m+ = whale
            strategy = allocation_strategies.get(risk_preference, allocation_strategies['whale'])
        else:
            strategy = allocation_strategies.get(risk_preference, allocation_strategies['balanced'])
        
        # Find opportunities for each allocation
        total_expected_return = 0
        
        for tier_name, allocation_pct in strategy.items():
            if tier_name not in self.profit_tiers:
                continue
                
            allocated_capital = int(capital * allocation_pct)
            if allocated_capital < 1000:  # Skip tiny allocations
                continue
            
            # Find best opportunities in this tier
            opportunities = self.find_opportunities_by_tier(
                tier_name, allocated_capital, limit=10, sort_by='profit'
            )
            
            if opportunities:
                # Calculate expected returns for this allocation
                avg_profit = sum(op['current_profit'] for op in opportunities[:5]) / min(5, len(opportunities))
                avg_margin = sum(op['profit_margin'] for op in opportunities[:5]) / min(5, len(opportunities))
                
                expected_return = allocated_capital * (avg_margin / 100)
                total_expected_return += expected_return
                
                portfolio['allocations'][tier_name] = {
                    'capital': allocated_capital,
                    'percentage': allocation_pct * 100,
                    'opportunities': opportunities[:3],  # Top 3 in each tier
                    'expected_return': expected_return,
                    'avg_profit_per_flip': avg_profit
                }
        
        portfolio['expected_returns'] = {
            'total_expected': total_expected_return,
            'roi_percentage': (total_expected_return / capital) * 100 if capital > 0 else 0
        }
        
        # Generate actionable recommendations
        portfolio['recommendations'] = self._generate_portfolio_recommendations(portfolio)
        
        logger.info(f"✅ Portfolio optimized with {total_expected_return:,.0f} GP expected return")
        return portfolio

    def _classify_profit_tier(self, profit: int) -> Dict:
        """Classify profit into tier."""
        for tier_name, tier in self.profit_tiers.items():
            if tier.min_profit <= profit < tier.max_profit:
                return {
                    'name': tier.name,
                    'tier_key': tier_name,
                    'description': tier.description,
                    'risk_level': tier.risk_level,
                    'liquidity_requirement': tier.liquidity_req
                }
        
        return {
            'name': 'Unclassified',
            'tier_key': 'unknown',
            'description': 'Profit tier not classified',
            'risk_level': 'unknown',
            'liquidity_requirement': 'unknown'
        }

    def _analyze_volume(self, item: Item, profit_calc) -> Dict:
        """Analyze trading volume metrics."""
        daily_volume = getattr(profit_calc, 'daily_volume', 0) or 0
        
        # Classify volume level
        volume_level = 'minimal'
        for level, threshold in sorted(self.volume_thresholds.items(), 
                                     key=lambda x: x[1], reverse=True):
            if daily_volume >= threshold:
                volume_level = level
                break
        
        # Calculate theoretical max trades per day
        max_trades_per_day = min(daily_volume, item.limit or 1000)
        
        return {
            'daily_volume': daily_volume,
            'volume_level': volume_level,
            'buy_limit': item.limit or 0,
            'max_trades_per_day': max_trades_per_day,
            'liquidity_score': min(100, (daily_volume / 1000) * 100)
        }

    def _assess_risk(self, item: Item, profit_calc, volume_analysis: Dict) -> Dict:
        """Comprehensive risk assessment."""
        risk_factors = []
        risk_score = 0  # 0-100, higher = more risky
        
        # Volume risk
        if volume_analysis['daily_volume'] < 50:
            risk_factors.append('Very low trading volume')
            risk_score += 30
        elif volume_analysis['daily_volume'] < 200:
            risk_factors.append('Low trading volume')
            risk_score += 15
        
        # Price volatility risk (if we have historical data)
        try:
            recent_prices = HistoricalPrice.objects.filter(
                item=item,
                timestamp__gte=timezone.now() - timedelta(days=7)
            ).values_list('price', flat=True)
            
            if len(recent_prices) > 5:
                price_std = statistics.stdev(recent_prices)
                avg_price = statistics.mean(recent_prices)
                volatility = (price_std / avg_price) * 100 if avg_price > 0 else 0
                
                if volatility > 20:
                    risk_factors.append('High price volatility')
                    risk_score += 25
                elif volatility > 10:
                    risk_factors.append('Medium price volatility')
                    risk_score += 10
        except:
            pass
        
        # Market depth risk
        buy_price = getattr(profit_calc, 'current_buy_price', 0)
        if buy_price > 10_000_000:  # 10m+
            risk_factors.append('Very high item value')
            risk_score += 20
        
        # Membership requirement risk
        if item.members:
            risk_score += 5
        
        return {
            'risk_score': min(100, risk_score),
            'risk_level': self._score_to_risk_level(risk_score),
            'risk_factors': risk_factors,
            'recommended_max_investment': self._calculate_max_investment(risk_score)
        }

    def _analyze_capital_efficiency(self, item: Item, profit_calc, 
                                  available_capital: int, profit_per_item: int) -> Dict:
        """Analyze capital efficiency metrics."""
        buy_price = getattr(profit_calc, 'current_buy_price', 0)
        
        if buy_price == 0 or available_capital == 0:
            return {
                'max_quantity': 0,
                'total_investment': 0,
                'total_profit_potential': 0,
                'capital_efficiency': 0,
                'roi_percentage': 0,
                'payback_periods': 0
            }
        
        # Calculate maximum quantity affordable
        max_by_capital = available_capital // buy_price
        max_by_limit = item.limit or 1000
        max_quantity = min(max_by_capital, max_by_limit)
        
        total_investment = max_quantity * buy_price
        total_profit_potential = max_quantity * profit_per_item
        
        roi_percentage = (total_profit_potential / total_investment * 100) if total_investment > 0 else 0
        
        return {
            'max_quantity': max_quantity,
            'total_investment': total_investment,
            'total_profit_potential': total_profit_potential,
            'capital_efficiency': total_profit_potential / available_capital * 100 if available_capital > 0 else 0,
            'roi_percentage': roi_percentage,
            'profit_per_gp_invested': total_profit_potential / total_investment if total_investment > 0 else 0
        }

    def _analyze_historical_performance(self, item: Item) -> Dict:
        """Analyze historical trading performance."""
        try:
            # Get last 30 days of price history
            recent_history = HistoricalPrice.objects.filter(
                item=item,
                timestamp__gte=timezone.now() - timedelta(days=30)
            ).order_by('timestamp')
            
            if not recent_history.exists():
                return {'status': 'no_data', 'trend': 'unknown'}
            
            prices = list(recent_history.values_list('price', 'timestamp'))
            
            if len(prices) < 5:
                return {'status': 'insufficient_data', 'trend': 'unknown'}
            
            # Calculate trend
            price_values = [p[0] for p in prices if p[0] > 0]
            if len(price_values) >= 5:
                recent_avg = sum(price_values[-5:]) / 5
                older_avg = sum(price_values[:5]) / 5
                
                trend = 'rising' if recent_avg > older_avg * 1.05 else 'falling' if recent_avg < older_avg * 0.95 else 'stable'
            else:
                trend = 'unknown'
            
            return {
                'status': 'analyzed',
                'trend': trend,
                'data_points': len(prices),
                'period_days': 30
            }
            
        except Exception as e:
            logger.error(f"Error analyzing historical performance for item {item.item_id}: {e}")
            return {'status': 'error', 'trend': 'unknown'}

    def _analyze_market_timing(self, item: Item, profit_calc) -> Dict:
        """Analyze optimal market timing."""
        return {
            'optimal_buy_time': 'Any time with good margin',
            'optimal_sell_time': 'When profit target is met',
            'market_conditions': 'Monitor for volume changes'
        }

    def _calculate_overall_score(self, profit_tier: Dict, volume_analysis: Dict, 
                               risk_analysis: Dict, capital_analysis: Dict) -> int:
        """Calculate overall opportunity score (0-100)."""
        score = 0
        
        # Profit tier contribution (40 points max)
        tier_scores = {
            'whale_tier': 40, 'mega_margin': 38, 'million_margin': 35,
            'large_margin': 30, 'medium_margin': 25, 'small_margin': 20, 'micro_margin': 15
        }
        score += tier_scores.get(profit_tier.get('tier_key', ''), 0)
        
        # Volume contribution (25 points max)
        score += min(25, volume_analysis.get('liquidity_score', 0) / 4)
        
        # Risk penalty (subtract up to 25 points)
        score -= min(25, risk_analysis.get('risk_score', 0) / 4)
        
        # Capital efficiency bonus (10 points max)
        roi = capital_analysis.get('roi_percentage', 0)
        score += min(10, roi / 10)
        
        return max(0, min(100, int(score)))

    def _generate_recommendation(self, profit_tier: Dict, volume_analysis: Dict,
                               risk_analysis: Dict, capital_analysis: Dict) -> str:
        """Generate actionable recommendation."""
        if profit_tier.get('tier_key') in ['million_margin', 'mega_margin', 'whale_tier']:
            if risk_analysis.get('risk_score', 0) > 60:
                return f"High-reward opportunity with elevated risk. Consider with {risk_analysis.get('recommended_max_investment', 'limited')} investment."
            else:
                return f"Excellent {profit_tier.get('name', '')} opportunity. Strong profit potential."
        
        elif volume_analysis.get('volume_level') in ['very_low', 'minimal']:
            return "Low liquidity - suitable for patient traders or small positions only."
        
        else:
            return f"Solid {profit_tier.get('name', '')} opportunity with reasonable risk profile."

    def _generate_portfolio_recommendations(self, portfolio: Dict) -> List[str]:
        """Generate portfolio-level recommendations."""
        recommendations = []
        
        total_expected_roi = portfolio['expected_returns'].get('roi_percentage', 0)
        
        if total_expected_roi > 50:
            recommendations.append(f"Excellent portfolio with {total_expected_roi:.1f}% expected ROI")
        elif total_expected_roi > 25:
            recommendations.append(f"Strong portfolio with {total_expected_roi:.1f}% expected ROI")
        else:
            recommendations.append(f"Conservative portfolio with {total_expected_roi:.1f}% expected ROI")
        
        # Check allocation balance
        allocations = portfolio.get('allocations', {})
        if 'million_margin' in allocations or 'mega_margin' in allocations:
            recommendations.append("Portfolio includes high-margin opportunities - monitor market conditions")
        
        if len(allocations) >= 3:
            recommendations.append("Well-diversified across multiple profit tiers")
        
        return recommendations

    def _create_empty_analysis(self, item: Item, reason: str) -> Dict:
        """Create empty analysis structure."""
        return {
            'item_id': item.item_id,
            'item_name': item.name,
            'error': reason,
            'current_profit': 0,
            'profit_tier': {'name': 'Unknown', 'tier_key': 'unknown'},
            'overall_score': 0
        }

    def _score_to_risk_level(self, score: int) -> str:
        """Convert risk score to level."""
        if score >= 70: return 'very_high'
        elif score >= 50: return 'high'
        elif score >= 30: return 'medium'
        elif score >= 15: return 'low'
        else: return 'very_low'

    def _calculate_max_investment(self, risk_score: int) -> str:
        """Calculate recommended maximum investment based on risk."""
        if risk_score >= 70: return '5% of capital'
        elif risk_score >= 50: return '10% of capital'
        elif risk_score >= 30: return '20% of capital'
        else: return '30% of capital'


# Global instance for use in merchant AI agent
profit_engine = AdvancedProfitDetectionEngine()