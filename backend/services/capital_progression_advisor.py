"""
AI-Powered Capital Progression Advisor

Intelligent advisor for scaling OSRS capital using proven money making strategies.
Implements your friend's successful 50M → 100M approach with AI-powered recommendations.

Key Features:
- Capital tier analysis and progression paths
- Strategy recommendations based on current capital
- Risk assessment and diversification advice
- Market timing and opportunity identification
- Performance tracking and optimization
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

from django.utils import timezone
from django.db.models import Q, Avg, Sum, Count
from django.core.cache import cache

from apps.items.models import Item
from apps.prices.models import ProfitCalculation
from apps.trading_strategies.models import (
    TradingStrategy, MoneyMakerStrategy, StrategyType, MarketCondition
)
from services.money_maker_detector import MoneyMakerDetector, AsyncMoneyMakerDetector
from services.set_combining_detector import SetCombiningDetector
from apps.trading_strategies.services.decanting_detector import DecantingDetector
from services.weird_gloop_client import GrandExchangeTax
from services.ai_service import SyncOpenRouterAIService

logger = logging.getLogger(__name__)


class CapitalTier(Enum):
    """Capital tiers for progressive money making"""
    STARTER = "starter"          # 0-10M GP
    INTERMEDIATE = "intermediate"  # 10-50M GP  
    ADVANCED = "advanced"        # 50-200M GP
    EXPERT = "expert"           # 200M+ GP


class RiskProfile(Enum):
    """User risk tolerance profiles"""
    CONSERVATIVE = "conservative"  # Low risk, steady growth
    BALANCED = "balanced"         # Medium risk, balanced approach
    AGGRESSIVE = "aggressive"     # High risk, maximum growth


@dataclass
class ProgressionGoal:
    """Represents a capital progression goal"""
    current_capital: int
    target_capital: int
    target_timeline_days: int
    risk_tolerance: RiskProfile
    preferred_strategies: List[StrategyType]
    
    @property
    def daily_profit_needed(self) -> int:
        """Calculate daily profit needed to reach goal."""
        profit_gap = self.target_capital - self.current_capital
        return profit_gap // max(1, self.target_timeline_days)
    
    @property
    def daily_return_needed(self) -> float:
        """Calculate daily return percentage needed."""
        if self.current_capital > 0:
            return (self.daily_profit_needed / self.current_capital) * 100
        return 0.0


@dataclass
class StrategyRecommendation:
    """AI-generated strategy recommendation"""
    strategy_type: StrategyType
    strategy_name: str
    description: str
    
    # Financial projections
    expected_daily_profit: int
    capital_required: int
    expected_roi_percentage: float
    
    # Risk assessment
    risk_level: str  # low, medium, high, extreme
    volatility_score: float  # 0-1
    market_dependency: float  # 0-1
    
    # Implementation guidance
    setup_time_hours: int
    learning_curve_difficulty: str  # easy, medium, hard
    automation_potential: str  # none, partial, high
    
    # Performance tracking
    success_rate_estimate: float  # 0-1
    confidence_score: float  # 0-1
    
    # Strategic context
    synergy_strategies: List[str]  # Compatible strategies
    competitive_strategies: List[str]  # Resource-competing strategies
    progression_stage: CapitalTier


@dataclass
class ProgressionPlan:
    """Complete capital progression plan"""
    goal: ProgressionGoal
    current_tier: CapitalTier
    target_tier: CapitalTier
    
    # Strategy mix
    primary_strategies: List[StrategyRecommendation]
    diversification_strategies: List[StrategyRecommendation]
    
    # Timeline and milestones
    milestones: List[Dict[str, Any]]
    estimated_timeline_days: int
    success_probability: float
    
    # Risk management
    risk_factors: List[str]
    mitigation_strategies: List[str]
    
    # Market context
    market_conditions_required: List[MarketCondition]
    optimal_execution_times: List[str]


class CapitalProgressionAdvisor:
    """
    AI-powered advisor for capital progression using proven money making strategies.
    """
    
    def __init__(self):
        self.money_maker_detector = MoneyMakerDetector()
        self.set_combining_detector = SetCombiningDetector()
        self.decanting_detector = DecantingDetector()
        self.ai_service = SyncOpenRouterAIService()
        
        # Your friend's proven progression path
        self.proven_progression = {
            'starting_capital': 50_000_000,
            'target_capital': 100_000_000,
            'methods_used': [
                'bond_funded_capital_injection',
                'high_value_item_flipping',
                'potion_decanting_40m_profit',
                'armor_set_combining_lazy_tax'
            ],
            'key_insights': [
                'Multiple strategies simultaneously',
                'GE tax awareness critical',
                'Market fluctuation monitoring',
                'Capital reinvestment discipline'
            ]
        }
    
    async def analyze_current_position(self, current_capital: int, 
                                     user_preferences: Dict = None) -> Dict[str, Any]:
        """
        Analyze user's current financial position and money making potential.
        
        Args:
            current_capital: Current available capital in GP
            user_preferences: User preferences and constraints
            
        Returns:
            Comprehensive analysis of current position
        """
        logger.info(f"Analyzing current position for {current_capital:,} GP capital")
        
        # Determine current tier and capabilities
        current_tier = self._determine_capital_tier(current_capital)
        
        # Get available opportunities
        opportunities = await AsyncMoneyMakerDetector.get_opportunities(current_capital)
        
        # Calculate current earning potential
        earning_potential = self._calculate_earning_potential(current_capital, opportunities)
        
        # Assess market position
        market_assessment = await self._assess_market_position(current_capital)
        
        # Compare to proven benchmarks
        benchmark_comparison = self._compare_to_benchmarks(current_capital)
        
        return {
            'current_capital': current_capital,
            'capital_tier': current_tier.value,
            'earning_potential': earning_potential,
            'available_opportunities': opportunities,
            'market_assessment': market_assessment,
            'benchmark_comparison': benchmark_comparison,
            'progression_readiness': self._assess_progression_readiness(current_capital),
            'next_tier_requirements': self._get_next_tier_requirements(current_tier)
        }
    
    async def create_progression_plan(self, goal: ProgressionGoal) -> ProgressionPlan:
        """
        Create a comprehensive capital progression plan.
        
        Args:
            goal: Progression goal with targets and preferences
            
        Returns:
            Detailed progression plan with strategies and timelines
        """
        logger.info(f"Creating progression plan: {goal.current_capital:,} → {goal.target_capital:,} GP")
        
        current_tier = self._determine_capital_tier(goal.current_capital)
        target_tier = self._determine_capital_tier(goal.target_capital)
        
        # Get strategy recommendations
        primary_strategies = await self._recommend_primary_strategies(goal)
        diversification_strategies = await self._recommend_diversification_strategies(goal)
        
        # Create progression milestones
        milestones = self._create_progression_milestones(goal, primary_strategies)
        
        # Assess timeline and success probability
        timeline_assessment = self._assess_timeline_feasibility(goal, primary_strategies)
        
        # Risk analysis
        risk_analysis = self._analyze_progression_risks(goal, primary_strategies)
        
        return ProgressionPlan(
            goal=goal,
            current_tier=current_tier,
            target_tier=target_tier,
            primary_strategies=primary_strategies,
            diversification_strategies=diversification_strategies,
            milestones=milestones,
            estimated_timeline_days=timeline_assessment['estimated_days'],
            success_probability=timeline_assessment['success_probability'],
            risk_factors=risk_analysis['risk_factors'],
            mitigation_strategies=risk_analysis['mitigation_strategies'],
            market_conditions_required=self._get_optimal_market_conditions(primary_strategies),
            optimal_execution_times=self._get_optimal_execution_times()
        )
    
    def _determine_capital_tier(self, capital: int) -> CapitalTier:
        """Determine capital tier based on available funds."""
        if capital < 10_000_000:
            return CapitalTier.STARTER
        elif capital < 50_000_000:
            return CapitalTier.INTERMEDIATE
        elif capital < 200_000_000:
            return CapitalTier.ADVANCED
        else:
            return CapitalTier.EXPERT
    
    def _calculate_earning_potential(self, capital: int, opportunities: Dict) -> Dict[str, Any]:
        """Calculate maximum earning potential with current capital."""
        
        # Extract opportunity data
        total_opportunities = len(opportunities.get('opportunities', []))
        
        if total_opportunities == 0:
            return {
                'daily_potential': 0,
                'hourly_potential': 0,
                'strategies_available': 0,
                'efficiency_score': 0.0
            }
        
        # Calculate potential from top opportunities
        top_opportunities = opportunities.get('opportunities', [])[:5]  # Top 5
        
        total_hourly_potential = sum(opp.get('hourly_profit_gp', 0) for opp in top_opportunities)
        daily_potential = total_hourly_potential * 8  # 8 hours active trading
        
        # Calculate capital efficiency
        total_capital_required = sum(opp.get('capital_required', 0) for opp in top_opportunities)
        efficiency_score = (total_hourly_potential / max(1, total_capital_required)) * 1000000 if total_capital_required > 0 else 0
        
        return {
            'daily_potential': daily_potential,
            'hourly_potential': total_hourly_potential,
            'strategies_available': total_opportunities,
            'efficiency_score': min(1.0, efficiency_score),  # Normalize to 0-1
            'capital_utilization': min(1.0, total_capital_required / max(1, capital))
        }
    
    async def _assess_market_position(self, capital: int) -> Dict[str, Any]:
        """Assess current market position and opportunities."""
        
        # Get market data
        try:
            # Count available profitable items by category
            profitable_items = ProfitCalculation.objects.filter(is_profitable=True)
            
            high_alchemy_count = profitable_items.filter(
                high_alch_viability_score__gte=60
            ).count()
            
            flipping_count = profitable_items.filter(
                current_profit_margin__gte=5.0,
                volume_category__in=['hot', 'warm']
            ).count()
            
            # Assess market volatility
            volatile_items = profitable_items.filter(
                volume_category='hot'
            ).count()
            
            total_items = profitable_items.count()
            
            return {
                'market_health': 'good' if total_items > 100 else 'moderate' if total_items > 50 else 'poor',
                'high_alchemy_opportunities': high_alchemy_count,
                'flipping_opportunities': flipping_count,
                'market_volatility': 'high' if volatile_items > 20 else 'moderate' if volatile_items > 10 else 'low',
                'total_profitable_items': total_items,
                'market_score': min(100, total_items)  # 0-100 score
            }
            
        except Exception as e:
            logger.error(f"Error assessing market position: {e}")
            return {
                'market_health': 'unknown',
                'high_alchemy_opportunities': 0,
                'flipping_opportunities': 0,
                'market_volatility': 'unknown',
                'total_profitable_items': 0,
                'market_score': 0
            }
    
    def _compare_to_benchmarks(self, capital: int) -> Dict[str, Any]:
        """Compare current capital to proven benchmarks."""
        
        # Your friend's benchmarks
        benchmarks = {
            'friend_starting_point': {
                'capital': 50_000_000,
                'methods': ['bonds', 'flipping', 'decanting', 'set_combining'],
                'achievement': 'Scaled to 100M+'
            },
            'decanting_benchmark': {
                'profit_achieved': 40_000_000,
                'method': 'potion_decanting',
                'timeframe': 'sustained_period'
            }
        }
        
        position_vs_friend = 'above' if capital > 50_000_000 else 'below'
        readiness_for_advanced = capital >= 50_000_000
        
        return {
            'vs_friend_starting_point': {
                'position': position_vs_friend,
                'capital_ratio': capital / 50_000_000,
                'ready_for_friend_methods': readiness_for_advanced
            },
            'decanting_potential': {
                'can_replicate': capital >= 5_000_000,  # Minimum for meaningful decanting
                'scale_factor': capital / 5_000_000 if capital >= 5_000_000 else 0
            },
            'benchmarks': benchmarks
        }
    
    def _assess_progression_readiness(self, capital: int) -> Dict[str, Any]:
        """Assess readiness for progression to next tier."""
        
        current_tier = self._determine_capital_tier(capital)
        
        readiness_factors = {
            CapitalTier.STARTER: {
                'capital_readiness': capital / 10_000_000,  # Progress to 10M
                'strategy_complexity': 'basic',
                'focus_areas': ['high_alchemy', 'basic_flipping', 'learning_market']
            },
            CapitalTier.INTERMEDIATE: {
                'capital_readiness': capital / 50_000_000,  # Progress to 50M
                'strategy_complexity': 'intermediate',
                'focus_areas': ['decanting', 'set_combining', 'volume_flipping']
            },
            CapitalTier.ADVANCED: {
                'capital_readiness': capital / 200_000_000,  # Progress to 200M
                'strategy_complexity': 'advanced',
                'focus_areas': ['bond_flipping', 'multiple_strategies', 'market_timing']
            },
            CapitalTier.EXPERT: {
                'capital_readiness': 1.0,  # Already at top tier
                'strategy_complexity': 'expert',
                'focus_areas': ['wealth_preservation', 'market_influence', 'diversification']
            }
        }
        
        return readiness_factors.get(current_tier, readiness_factors[CapitalTier.STARTER])
    
    def _get_next_tier_requirements(self, current_tier: CapitalTier) -> Dict[str, Any]:
        """Get requirements for progression to next tier."""
        
        next_tier_map = {
            CapitalTier.STARTER: {
                'next_tier': 'intermediate',
                'capital_needed': 10_000_000,
                'key_strategies': ['potion_decanting', 'armor_flipping'],
                'skills_needed': ['barbarian_herblore', 'market_analysis'],
                'estimated_time': '2-4 weeks'
            },
            CapitalTier.INTERMEDIATE: {
                'next_tier': 'advanced',
                'capital_needed': 50_000_000,
                'key_strategies': ['bond_flipping', 'set_combining', 'high_value_flipping'],
                'skills_needed': ['risk_management', 'strategy_diversification'],
                'estimated_time': '6-12 weeks'
            },
            CapitalTier.ADVANCED: {
                'next_tier': 'expert',
                'capital_needed': 200_000_000,
                'key_strategies': ['market_timing', 'portfolio_management', 'compound_strategies'],
                'skills_needed': ['advanced_analysis', 'market_psychology'],
                'estimated_time': '3-6 months'
            },
            CapitalTier.EXPERT: {
                'next_tier': 'wealth_management',
                'capital_needed': float('inf'),
                'key_strategies': ['preservation', 'influence', 'teaching'],
                'skills_needed': ['mentorship', 'long_term_planning'],
                'estimated_time': 'ongoing'
            }
        }
        
        return next_tier_map.get(current_tier, next_tier_map[CapitalTier.STARTER])
    
    async def _recommend_primary_strategies(self, goal: ProgressionGoal) -> List[StrategyRecommendation]:
        """Recommend primary strategies based on goal and capital."""
        
        recommendations = []
        current_tier = self._determine_capital_tier(goal.current_capital)
        
        # Get opportunities for current capital
        opportunities = await AsyncMoneyMakerDetector.get_opportunities(goal.current_capital)
        
        # Strategy recommendations based on tier and your friend's approach
        if current_tier == CapitalTier.INTERMEDIATE and goal.target_capital >= 50_000_000:
            # Intermediate → Advanced (your friend's path)
            recommendations.extend([
                self._create_decanting_recommendation(goal),
                self._create_set_combining_recommendation(goal),
                self._create_flipping_recommendation(goal)
            ])
            
        elif current_tier == CapitalTier.ADVANCED:
            # Advanced tier (50M+ capital)
            recommendations.extend([
                self._create_bond_flipping_recommendation(goal),
                self._create_advanced_decanting_recommendation(goal),
                self._create_premium_set_combining_recommendation(goal)
            ])
        
        elif current_tier == CapitalTier.STARTER:
            # Starter tier
            recommendations.extend([
                self._create_alchemy_recommendation(goal),
                self._create_basic_flipping_recommendation(goal),
                self._create_learning_recommendation(goal)
            ])
        
        else:  # Expert tier
            recommendations.extend([
                self._create_portfolio_recommendation(goal),
                self._create_market_timing_recommendation(goal),
                self._create_diversification_recommendation(goal)
            ])
        
        # Sort by expected ROI and filter top recommendations
        recommendations.sort(key=lambda x: x.expected_roi_percentage, reverse=True)
        return recommendations[:3]  # Top 3 primary strategies
    
    def _create_decanting_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Create decanting strategy recommendation (your friend's 40M method)."""
        return StrategyRecommendation(
            strategy_type=StrategyType.DECANTING,
            strategy_name="Potion Decanting (Friend's 40M Method)",
            description="Buy high-dose potions, decant to lower doses, profit from convenience premium",
            expected_daily_profit=2_000_000,  # Conservative estimate
            capital_required=5_000_000,
            expected_roi_percentage=40.0,
            risk_level="low",
            volatility_score=0.2,
            market_dependency=0.3,
            setup_time_hours=2,
            learning_curve_difficulty="medium",
            automation_potential="partial",
            success_rate_estimate=0.85,
            confidence_score=0.9,  # High confidence based on friend's success
            synergy_strategies=["high_alchemy", "flipping"],
            competitive_strategies=["bond_flipping"],
            progression_stage=CapitalTier.INTERMEDIATE
        )
    
    def _create_set_combining_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Create set combining strategy recommendation (lazy tax exploitation)."""
        return StrategyRecommendation(
            strategy_type=StrategyType.SET_COMBINING,
            strategy_name="Armor Set Combining (Lazy Tax)",
            description="Buy armor pieces separately, combine and sell complete sets for premium",
            expected_daily_profit=1_500_000,
            capital_required=15_000_000,
            expected_roi_percentage=10.0,
            risk_level="medium",
            volatility_score=0.4,
            market_dependency=0.5,
            setup_time_hours=3,
            learning_curve_difficulty="medium",
            automation_potential="none",
            success_rate_estimate=0.75,
            confidence_score=0.8,
            synergy_strategies=["flipping", "market_analysis"],
            competitive_strategies=["high_volume_flipping"],
            progression_stage=CapitalTier.INTERMEDIATE
        )
    
    def _create_bond_flipping_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Create bond flipping recommendation (your friend's starting method).""" 
        return StrategyRecommendation(
            strategy_type=StrategyType.BOND_FLIPPING,
            strategy_name="Bond-Funded High-Value Flipping",
            description="Use bonds for tax-free capital, flip expensive items for premium margins",
            expected_daily_profit=3_000_000,
            capital_required=50_000_000,
            expected_roi_percentage=6.0,
            risk_level="high",
            volatility_score=0.7,
            market_dependency=0.8,
            setup_time_hours=1,
            learning_curve_difficulty="hard",
            automation_potential="none",
            success_rate_estimate=0.7,
            confidence_score=0.85,  # Friend's proven method
            synergy_strategies=["market_timing", "risk_management"],
            competitive_strategies=["volume_strategies"],
            progression_stage=CapitalTier.ADVANCED
        )
    
    def _create_flipping_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Create general flipping recommendation."""
        return StrategyRecommendation(
            strategy_type=StrategyType.FLIPPING,
            strategy_name="Strategic Item Flipping",
            description="Buy low, sell high with GE tax awareness and volume analysis",
            expected_daily_profit=1_000_000,
            capital_required=goal.current_capital // 4,  # Use 25% of capital
            expected_roi_percentage=15.0,
            risk_level="medium",
            volatility_score=0.5,
            market_dependency=0.6,
            setup_time_hours=1,
            learning_curve_difficulty="easy",
            automation_potential="partial",
            success_rate_estimate=0.8,
            confidence_score=0.75,
            synergy_strategies=["market_analysis", "alchemy"],
            competitive_strategies=["capital_intensive_strategies"],
            progression_stage=self._determine_capital_tier(goal.current_capital)
        )
    
    # Additional recommendation methods would be implemented similarly...
    def _create_alchemy_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Create high alchemy recommendation for beginners."""
        return StrategyRecommendation(
            strategy_type=StrategyType.HIGH_ALCHEMY,
            strategy_name="High Alchemy Training",
            description="Consistent profits while training Magic, perfect for beginners",
            expected_daily_profit=500_000,
            capital_required=2_000_000,
            expected_roi_percentage=25.0,
            risk_level="low",
            volatility_score=0.1,
            market_dependency=0.2,
            setup_time_hours=0.5,
            learning_curve_difficulty="easy",
            automation_potential="high",
            success_rate_estimate=0.95,
            confidence_score=0.9,
            synergy_strategies=["item_collection", "magic_training"],
            competitive_strategies=["active_trading"],
            progression_stage=CapitalTier.STARTER
        )
    
    def _create_basic_flipping_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Create basic flipping recommendation for starters."""
        return StrategyRecommendation(
            strategy_type=StrategyType.FLIPPING,
            strategy_name="Basic Item Flipping",
            description="Start with low-value, high-volume items to learn market dynamics",
            expected_daily_profit=300_000,
            capital_required=1_000_000,
            expected_roi_percentage=30.0,
            risk_level="low",
            volatility_score=0.3,
            market_dependency=0.4,
            setup_time_hours=1,
            learning_curve_difficulty="easy",
            automation_potential="partial",
            success_rate_estimate=0.8,
            confidence_score=0.7,
            synergy_strategies=["market_learning", "risk_management"],
            competitive_strategies=["high_capital_strategies"],
            progression_stage=CapitalTier.STARTER
        )
    
    def _create_learning_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Create learning-focused recommendation."""
        return StrategyRecommendation(
            strategy_type=StrategyType.ARBITRAGE,
            strategy_name="Market Learning & Analysis",
            description="Focus on understanding market patterns and building knowledge base",
            expected_daily_profit=200_000,
            capital_required=500_000,
            expected_roi_percentage=40.0,
            risk_level="low",
            volatility_score=0.2,
            market_dependency=0.3,
            setup_time_hours=2,
            learning_curve_difficulty="medium",
            automation_potential="none",
            success_rate_estimate=0.9,
            confidence_score=0.95,
            synergy_strategies=["all_strategies"],
            competitive_strategies=["none"],
            progression_stage=CapitalTier.STARTER
        )
    
    # Placeholder methods for other recommendations
    def _create_advanced_decanting_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Advanced decanting with higher capital."""
        rec = self._create_decanting_recommendation(goal)
        rec.strategy_name = "Advanced Potion Decanting"
        rec.expected_daily_profit = 3_000_000
        rec.capital_required = 20_000_000
        rec.progression_stage = CapitalTier.ADVANCED
        return rec
    
    def _create_premium_set_combining_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Premium set combining for advanced capital."""
        rec = self._create_set_combining_recommendation(goal)
        rec.strategy_name = "Premium Set Combining (God Wars)"
        rec.expected_daily_profit = 2_500_000
        rec.capital_required = 50_000_000
        rec.progression_stage = CapitalTier.ADVANCED
        return rec
    
    def _create_portfolio_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Portfolio management for expert tier."""
        return StrategyRecommendation(
            strategy_type=StrategyType.ARBITRAGE,
            strategy_name="Diversified Portfolio Management",
            description="Manage multiple strategies simultaneously for consistent returns",
            expected_daily_profit=5_000_000,
            capital_required=200_000_000,
            expected_roi_percentage=2.5,
            risk_level="medium",
            volatility_score=0.3,
            market_dependency=0.4,
            setup_time_hours=4,
            learning_curve_difficulty="hard",
            automation_potential="partial",
            success_rate_estimate=0.8,
            confidence_score=0.8,
            synergy_strategies=["all_strategies"],
            competitive_strategies=["none"],
            progression_stage=CapitalTier.EXPERT
        )
    
    def _create_market_timing_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Market timing for expert tier."""
        return StrategyRecommendation(
            strategy_type=StrategyType.ARBITRAGE,
            strategy_name="Market Timing & Cycle Analysis",
            description="Time market entry/exit for maximum profit from price cycles",
            expected_daily_profit=4_000_000,
            capital_required=100_000_000,
            expected_roi_percentage=4.0,
            risk_level="high",
            volatility_score=0.8,
            market_dependency=0.9,
            setup_time_hours=6,
            learning_curve_difficulty="hard",
            automation_potential="none",
            success_rate_estimate=0.6,
            confidence_score=0.7,
            synergy_strategies=["analysis_tools", "risk_management"],
            competitive_strategies=["steady_strategies"],
            progression_stage=CapitalTier.EXPERT
        )
    
    def _create_diversification_recommendation(self, goal: ProgressionGoal) -> StrategyRecommendation:
        """Diversification for expert tier.""" 
        return StrategyRecommendation(
            strategy_type=StrategyType.ARBITRAGE,
            strategy_name="Risk Diversification",
            description="Spread risk across multiple uncorrelated strategies and markets",
            expected_daily_profit=3_500_000,
            capital_required=150_000_000,
            expected_roi_percentage=2.3,
            risk_level="low",
            volatility_score=0.2,
            market_dependency=0.3,
            setup_time_hours=8,
            learning_curve_difficulty="hard",
            automation_potential="high",
            success_rate_estimate=0.9,
            confidence_score=0.85,
            synergy_strategies=["all_strategies"],
            competitive_strategies=["concentrated_strategies"],
            progression_stage=CapitalTier.EXPERT
        )
    
    async def _recommend_diversification_strategies(self, goal: ProgressionGoal) -> List[StrategyRecommendation]:
        """Recommend diversification strategies to reduce risk."""
        # Return complementary strategies that don't compete for the same resources
        diversification = []
        
        if goal.risk_tolerance == RiskProfile.CONSERVATIVE:
            diversification.append(self._create_alchemy_recommendation(goal))
        
        if goal.current_capital >= 10_000_000:
            # Can diversify into different markets
            diversification.append(self._create_flipping_recommendation(goal))
        
        return diversification[:2]  # Max 2 diversification strategies
    
    def _create_progression_milestones(self, goal: ProgressionGoal, 
                                     strategies: List[StrategyRecommendation]) -> List[Dict[str, Any]]:
        """Create progression milestones based on goal and strategies."""
        milestones = []
        
        # Calculate milestone intervals
        capital_gap = goal.target_capital - goal.current_capital
        milestone_count = 4  # 4 milestones
        milestone_increment = capital_gap // milestone_count
        
        for i in range(1, milestone_count + 1):
            milestone_capital = goal.current_capital + (milestone_increment * i)
            milestone_days = (goal.target_timeline_days * i) // milestone_count
            
            milestones.append({
                'milestone_number': i,
                'target_capital': milestone_capital,
                'target_days': milestone_days,
                'key_strategies': [s.strategy_name for s in strategies[:2]],
                'success_metrics': [
                    f'Achieve {milestone_capital:,} GP',
                    f'Complete within {milestone_days} days',
                    'Maintain risk management'
                ],
                'validation_criteria': [
                    'Consistent daily profits',
                    'Strategy execution proficiency', 
                    'Market awareness development'
                ]
            })
        
        return milestones
    
    def _assess_timeline_feasibility(self, goal: ProgressionGoal, 
                                   strategies: List[StrategyRecommendation]) -> Dict[str, Any]:
        """Assess feasibility of timeline given strategies."""
        
        # Calculate expected daily profit from strategies
        total_daily_profit = sum(s.expected_daily_profit for s in strategies)
        
        # Account for execution efficiency (new users won't achieve max immediately)
        efficiency_factor = 0.7  # Assume 70% efficiency initially
        realistic_daily_profit = int(total_daily_profit * efficiency_factor)
        
        # Calculate realistic timeline
        capital_gap = goal.target_capital - goal.current_capital
        realistic_days = capital_gap // max(1, realistic_daily_profit)
        
        # Success probability based on multiple factors
        timeline_pressure = goal.target_timeline_days / max(1, realistic_days)
        strategy_difficulty = sum(1 for s in strategies if s.learning_curve_difficulty == 'hard')
        risk_factor = sum(s.volatility_score for s in strategies) / len(strategies)
        
        success_probability = max(0.1, min(0.95, 
            0.9 * timeline_pressure *  # Timeline feasibility
            (1 - strategy_difficulty * 0.1) *  # Difficulty penalty
            (1 - risk_factor * 0.2)  # Risk penalty
        ))
        
        return {
            'estimated_days': realistic_days,
            'success_probability': success_probability,
            'daily_profit_needed': goal.daily_profit_needed,
            'daily_profit_expected': realistic_daily_profit,
            'feasibility': 'high' if timeline_pressure >= 1.0 else 'medium' if timeline_pressure >= 0.5 else 'low'
        }
    
    def _analyze_progression_risks(self, goal: ProgressionGoal, 
                                 strategies: List[StrategyRecommendation]) -> Dict[str, Any]:
        """Analyze risks associated with progression plan."""
        
        risk_factors = []
        mitigation_strategies = []
        
        # Market dependency risks
        high_dependency_strategies = [s for s in strategies if s.market_dependency > 0.7]
        if high_dependency_strategies:
            risk_factors.append("High market dependency - vulnerable to market crashes")
            mitigation_strategies.append("Diversify into market-independent strategies")
        
        # Capital concentration risks
        total_capital_required = sum(s.capital_required for s in strategies)
        if total_capital_required > goal.current_capital * 0.8:
            risk_factors.append("Over-leveraged - using too much capital")
            mitigation_strategies.append("Reduce position sizes and maintain cash reserves")
        
        # Strategy complexity risks
        complex_strategies = [s for s in strategies if s.learning_curve_difficulty == 'hard']
        if len(complex_strategies) > 1:
            risk_factors.append("Multiple complex strategies - high learning curve")
            mitigation_strategies.append("Master one strategy before adding others")
        
        # Timeline pressure risks
        if goal.daily_return_needed > 5.0:  # > 5% daily return needed
            risk_factors.append("Aggressive timeline requires high daily returns")
            mitigation_strategies.append("Consider extending timeline or reducing target")
        
        # GE tax impact
        risk_factors.append("GE tax reduces all profit margins by ~2%")
        mitigation_strategies.append("Factor GE tax into all profit calculations")
        
        return {
            'risk_factors': risk_factors,
            'mitigation_strategies': mitigation_strategies,
            'overall_risk_level': 'high' if len(risk_factors) > 4 else 'medium' if len(risk_factors) > 2 else 'low'
        }
    
    def _get_optimal_market_conditions(self, strategies: List[StrategyRecommendation]) -> List[MarketCondition]:
        """Get optimal market conditions for strategies."""
        # Most money making strategies work best in stable markets
        return [MarketCondition.STABLE, MarketCondition.BULLISH]
    
    def _get_optimal_execution_times(self) -> List[str]:
        """Get optimal times for strategy execution."""
        return [
            "Prime time (16:00-20:00 UTC) - Highest volume",
            "Morning (10:00-12:00 UTC) - Good for buying",
            "Evening (20:00-22:00 UTC) - Good for selling",
            "Weekend mornings - Lower competition"
        ]