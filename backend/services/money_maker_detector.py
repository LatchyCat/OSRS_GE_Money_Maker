"""
Money Maker Detector Service

Advanced service for identifying profitable money-making opportunities
using your friend's proven strategies:
- Bond flipping for initial capital
- High-value item flipping 
- Decanting potions for consistent profit
- Set combining to exploit the "lazy tax"
- Scaling strategies based on available capital
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from django.db.models import Q, F, Count, Avg
from django.utils import timezone
from django.conf import settings

from apps.items.models import Item
from apps.prices.models import ProfitCalculation, PriceSnapshot
from apps.trading_strategies.models import (
    TradingStrategy, MoneyMakerStrategy, BondFlippingStrategy,
    AdvancedDecantingStrategy, EnhancedSetCombiningStrategy,
    StrategyType, MarketCondition
)
from services.weird_gloop_client import WeirdGloopAPIClient, GrandExchangeTax, MoneyMakerDataFetcher

logger = logging.getLogger(__name__)


class CapitalTier(Enum):
    """Capital tiers for scaling money maker strategies"""
    STARTER = "starter"      # < 10M GP
    INTERMEDIATE = "intermediate"  # 10M - 50M GP
    ADVANCED = "advanced"    # 50M - 200M GP
    EXPERT = "expert"        # 200M+ GP


@dataclass
class OpportunityScore:
    """Scoring system for money making opportunities"""
    profit_potential: int = 0    # Profit per hour in GP
    risk_level: int = 0         # Risk score 1-10 (10 = highest risk)
    capital_efficiency: float = 0.0  # Profit per GP invested ratio
    market_stability: int = 0   # Stability score 1-10 (10 = most stable)
    time_investment: int = 0    # Active time required (minutes per hour)
    overall_score: int = 0      # Calculated overall score 0-100


@dataclass 
class MoneyMakerOpportunity:
    """Complete money making opportunity data"""
    strategy_type: StrategyType
    name: str
    description: str
    
    # Financial metrics
    hourly_profit_gp: int
    capital_required: int
    profit_margin_pct: float
    ge_tax_cost: int = 0
    
    # Risk and timing
    time_required_minutes: int = 60  # Per cycle
    risk_level: str = "medium"  # low, medium, high, extreme
    market_volatility: float = 0.0
    
    # Item data
    primary_items: List[Dict] = field(default_factory=list)
    secondary_items: List[Dict] = field(default_factory=list)  # For sets/combinations
    
    # Strategy specific data
    strategy_data: Dict[str, Any] = field(default_factory=dict)
    
    # Scoring
    opportunity_score: OpportunityScore = field(default_factory=OpportunityScore)
    
    # Market conditions
    optimal_conditions: List[MarketCondition] = field(default_factory=list)
    current_viability: bool = True


class MoneyMakerDetector:
    """
    Core service for detecting money making opportunities.
    Implements your friend's proven 50M → 100M strategies.
    """
    
    def __init__(self):
        self.weird_gloop_client = WeirdGloopAPIClient()
        self.data_fetcher = MoneyMakerDataFetcher(self.weird_gloop_client)
        
        # Your friend's known profitable item sets and strategies
        self.known_profitable_sets = {
            # Bandos armor sets
            11828: {  # Bandos chestplate
                'pieces': [11832, 11834],  # Tassets, Chestplate  
                'name': 'Bandos armor set',
                'typical_lazy_tax': 2.5  # 2-3% premium for convenience
            },
            
            # Armadyl armor sets  
            11826: {  # Armadyl armor set
                'pieces': [11828, 11830, 11832],  # Helm, Chestplate, Chainskirt
                'name': 'Armadyl armor set', 
                'typical_lazy_tax': 3.0
            },
            
            # Dharok's set
            4718: {  # Dharok's set
                'pieces': [4716, 4720, 4722, 4724],  # Helm, Body, Legs, Axe
                'name': 'Dharoks armor set',
                'typical_lazy_tax': 1.5
            }
        }
        
        # Common potion families for decanting
        self.profitable_potion_families = {
            'Super combat potion': {
                4: 12695,  # Super combat potion(4)
                3: 12697,  # Super combat potion(3) 
                2: 12699,  # Super combat potion(2)
                1: 12701   # Super combat potion(1)
            },
            'Ranging potion': {
                4: 2444,   # Ranging potion(4)
                3: 169,    # Ranging potion(3)
                2: 171,    # Ranging potion(2) 
                1: 173     # Ranging potion(1)
            },
            'Super strength': {
                4: 2440,   # Super strength(4)
                3: 157,    # Super strength(3)
                2: 159,    # Super strength(2)
                1: 161     # Super strength(1)
            }
        }
    
    async def detect_all_opportunities(self, capital_available: int = 50_000_000) -> List[MoneyMakerOpportunity]:
        """
        Detect all available money making opportunities for given capital.
        
        Args:
            capital_available: Available capital in GP
            
        Returns:
            List of opportunities sorted by profitability
        """
        logger.info(f"Detecting money maker opportunities for {capital_available:,} GP capital")
        
        opportunities = []
        
        async with self.weird_gloop_client as client:
            # Detect different strategy types in parallel
            tasks = [
                self._detect_flipping_opportunities(capital_available),
                self._detect_decanting_opportunities(capital_available),
                self._detect_set_combining_opportunities(capital_available),
                self._detect_bond_strategies(capital_available)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error detecting opportunities: {result}")
                    continue
                opportunities.extend(result)
        
        # Score and sort opportunities
        scored_opportunities = []
        for opp in opportunities:
            opp.opportunity_score = self._calculate_opportunity_score(opp, capital_available)
            if opp.opportunity_score.overall_score > 30:  # Minimum viable score
                scored_opportunities.append(opp)
        
        # Sort by overall score
        scored_opportunities.sort(key=lambda x: x.opportunity_score.overall_score, reverse=True)
        
        logger.info(f"Found {len(scored_opportunities)} viable opportunities")
        return scored_opportunities[:50]  # Return top 50
    
    async def _detect_flipping_opportunities(self, capital: int) -> List[MoneyMakerOpportunity]:
        """Detect basic flipping opportunities with GE tax consideration."""
        logger.debug("Detecting flipping opportunities")
        
        opportunities = []
        
        # Get items with good profit potential
        profitable_items = ProfitCalculation.objects.filter(
            is_profitable=True,
            current_buy_price__lte=capital // 4,  # Don't risk more than 25% on single item
            volume_category__in=['hot', 'warm', 'cool'],
            current_profit_margin__gte=3.0  # Minimum 3% margin before tax
        ).select_related('item').order_by('-volume_weighted_score')[:100]
        
        for profit_calc in profitable_items:
            flip_data = profit_calc.get_flipping_opportunity()
            if flip_data and flip_data['net_profit'] > 1000:  # Min 1K profit after tax
                
                # Calculate cycles per hour (assume 5 minutes per flip)
                cycles_per_hour = 12
                hourly_profit = flip_data['net_profit'] * cycles_per_hour
                
                opportunities.append(MoneyMakerOpportunity(
                    strategy_type=StrategyType.FLIPPING,
                    name=f"Flip {flip_data['item_name']}",
                    description=f"Buy at {flip_data['buy_price']:,}, sell at {flip_data['sell_price']:,}",
                    hourly_profit_gp=hourly_profit,
                    capital_required=flip_data['capital_required'],
                    profit_margin_pct=flip_data['margin_pct'],
                    ge_tax_cost=flip_data['ge_tax'],
                    risk_level='medium' if flip_data['is_high_volume'] else 'high',
                    time_required_minutes=5,
                    primary_items=[{
                        'item_id': flip_data['item_id'],
                        'name': flip_data['item_name'],
                        'buy_price': flip_data['buy_price'],
                        'sell_price': flip_data['sell_price']
                    }],
                    strategy_data={
                        'volume_category': flip_data['volume_category'],
                        'daily_volume': flip_data['daily_volume'],
                        'ge_tax': flip_data['ge_tax']
                    }
                ))
        
        return opportunities
    
    async def _detect_decanting_opportunities(self, capital: int) -> List[MoneyMakerOpportunity]:
        """Detect potion decanting opportunities (your friend's 40M profit method)."""
        logger.debug("Detecting decanting opportunities")
        
        opportunities = []
        
        try:
            decanting_data = await self.data_fetcher.fetch_decanting_data(
                self.profitable_potion_families
            )
            
            for potion_name, data in decanting_data.items():
                if data['best_opportunities']:
                    best_opp = data['best_opportunities'][0]  # Top opportunity
                    
                    if best_opp['profit_analysis']['profit_per_item'] > 50:
                        # Estimate hourly profit (assume 1000 potions per hour)
                        hourly_potions = 1000
                        hourly_profit = best_opp['profit_analysis']['profit_per_item'] * hourly_potions
                        
                        opportunities.append(MoneyMakerOpportunity(
                            strategy_type=StrategyType.DECANTING,
                            name=f"Decant {potion_name}",
                            description=f"Buy {best_opp['from_dose']}-dose, decant to {best_opp['to_dose']}-dose",
                            hourly_profit_gp=hourly_profit,
                            capital_required=best_opp['buy_price'] * 1000,  # Capital for 1K potions
                            profit_margin_pct=best_opp['profit_analysis']['profit_margin_pct'],
                            ge_tax_cost=best_opp['profit_analysis']['ge_tax'],
                            risk_level='low',  # Decanting is low risk
                            time_required_minutes=45,  # Active time per hour
                            primary_items=[{
                                'item_id': best_opp['from_item_id'],
                                'name': f"{potion_name}({best_opp['from_dose']})",
                                'buy_price': best_opp['buy_price']
                            }],
                            secondary_items=[{
                                'item_id': best_opp['to_item_id'],  
                                'name': f"{potion_name}({best_opp['to_dose']})",
                                'sell_price': best_opp['sell_price']
                            }],
                            strategy_data={
                                'from_dose': best_opp['from_dose'],
                                'to_dose': best_opp['to_dose'],
                                'volume_constraint': best_opp['volume_constraint'],
                                'barbarian_herblore_required': True
                            }
                        ))
            
        except Exception as e:
            logger.error(f"Error detecting decanting opportunities: {e}")
        
        return opportunities
    
    async def _detect_set_combining_opportunities(self, capital: int) -> List[MoneyMakerOpportunity]:
        """Detect set combining opportunities (lazy tax exploitation)."""
        logger.debug("Detecting set combining opportunities")
        
        opportunities = []
        
        try:
            set_data = await self.data_fetcher.fetch_set_combining_data(
                self.known_profitable_sets
            )
            
            for set_id, data in set_data.items():
                if data['is_profitable'] and data['net_profit'] > 10000:  # Min 10K profit
                    lazy_tax = data['lazy_tax_percentage'] 
                    
                    # Estimate daily sets (conservative)
                    daily_sets = min(5, capital // data['pieces_total_cost'])
                    hourly_profit = (data['net_profit'] * daily_sets) // 8  # 8 hours active
                    
                    opportunities.append(MoneyMakerOpportunity(
                        strategy_type=StrategyType.SET_COMBINING,
                        name=f"Combine {data['set_name']}",
                        description=f"Buy pieces for {data['pieces_total_cost']:,}, sell set for {data['set_sell_price']:,}",
                        hourly_profit_gp=hourly_profit,
                        capital_required=data['pieces_total_cost'] * 3,  # Capital for 3 sets
                        profit_margin_pct=lazy_tax,
                        ge_tax_cost=data['ge_tax'],
                        risk_level='medium',
                        time_required_minutes=30,  # Time to acquire and sell
                        primary_items=[{
                            'item_id': set_id,
                            'name': data['set_name'],
                            'sell_price': data['set_sell_price']
                        }],
                        secondary_items=data['pieces_data'],
                        strategy_data={
                            'lazy_tax_percentage': lazy_tax,
                            'pieces_count': len(data['pieces_data']),
                            'recommended_daily_sets': daily_sets
                        }
                    ))
        
        except Exception as e:
            logger.error(f"Error detecting set combining opportunities: {e}")
        
        return opportunities
    
    async def _detect_bond_strategies(self, capital: int) -> List[MoneyMakerOpportunity]:
        """Detect bond and high-value flipping strategies."""
        logger.debug("Detecting bond strategies") 
        
        opportunities = []
        
        # Only relevant for high capital (50M+)
        if capital < 50_000_000:
            return opportunities
        
        try:
            bond_data = await self.data_fetcher.fetch_bond_flipping_targets(
                min_value=5_000_000  # 5M+ items
            )
            
            for item_id, data in bond_data.items():
                if data['profit_analysis']['is_profitable']:
                    profit = data['profit_analysis']['profit_per_item']
                    
                    # Calculate hourly profit (slower flips for high value items)
                    cycles_per_hour = 6  # 10 minutes per flip
                    hourly_profit = profit * cycles_per_hour
                    
                    risk = 'high' if data['capital_required'] > 100_000_000 else 'medium'
                    
                    opportunities.append(MoneyMakerOpportunity(
                        strategy_type=StrategyType.BOND_FLIPPING,
                        name=f"High-value flip: Item {item_id}",
                        description=f"Flip high-value items funded by bonds",
                        hourly_profit_gp=hourly_profit,
                        capital_required=data['capital_required'],
                        profit_margin_pct=data['profit_analysis']['profit_margin_pct'],
                        ge_tax_cost=data['profit_analysis']['ge_tax'],
                        risk_level=risk,
                        time_required_minutes=10,
                        primary_items=[{
                            'item_id': item_id,
                            'current_price': data['current_price'],
                            'estimated_buy': data['estimated_buy_price'],
                            'estimated_sell': data['estimated_sell_price']
                        }],
                        strategy_data={
                            'is_bond_funded': True,
                            'is_tax_exempt': data.get('is_bond_exempt', False),
                            'volume': data['volume']
                        }
                    ))
        
        except Exception as e:
            logger.error(f"Error detecting bond strategies: {e}")
        
        return opportunities
    
    def _calculate_opportunity_score(self, opportunity: MoneyMakerOpportunity, 
                                   available_capital: int) -> OpportunityScore:
        """Calculate comprehensive opportunity score."""
        
        score = OpportunityScore()
        
        # Profit potential (0-40 points)
        profit_score = min(40, opportunity.hourly_profit_gp // 100_000)  # 100K/hr = 1 point
        score.profit_potential = profit_score
        
        # Capital efficiency (0-25 points) 
        if available_capital > 0:
            efficiency_ratio = opportunity.hourly_profit_gp / available_capital
            efficiency_score = min(25, efficiency_ratio * 1000000)  # 1M ratio = 25 points
            score.capital_efficiency = efficiency_ratio
        
        # Risk assessment (0-20 points, lower risk = higher score)
        risk_scores = {'low': 20, 'medium': 15, 'high': 10, 'extreme': 5}
        risk_score = risk_scores.get(opportunity.risk_level, 10)
        score.risk_level = risk_score
        
        # Market stability (0-15 points)
        stability_score = 15  # Default, could be enhanced with volatility data
        if opportunity.market_volatility > 0.3:
            stability_score -= 5
        score.market_stability = stability_score
        
        # Calculate overall score
        score.overall_score = (
            profit_score + efficiency_score + risk_score + stability_score
        )
        
        # Bonus for capital fit
        if opportunity.capital_required <= available_capital * 0.5:
            score.overall_score += 10  # Bonus for not over-leveraging
        
        return score
    
    def get_recommended_strategy_progression(self, current_capital: int) -> List[str]:
        """
        Get recommended strategy progression based on your friend's approach.
        
        Args:
            current_capital: Current available capital
            
        Returns:
            List of recommended strategies in order
        """
        capital_tier = self._get_capital_tier(current_capital)
        
        progressions = {
            CapitalTier.STARTER: [
                "Start with basic flipping (consistent small profits)",
                "Focus on decanting potions (40M potential like your friend)",
                "Build capital to 10M for better opportunities"
            ],
            CapitalTier.INTERMEDIATE: [
                "Continue decanting for steady income", 
                "Begin set combining for lazy tax profits",
                "Scale up flipping with larger items",
                "Target 50M capital for advanced strategies"
            ],
            CapitalTier.ADVANCED: [
                "Your friend's sweet spot: bonds + high-value flips",
                "Multiple set combining operations simultaneously", 
                "Premium decanting with rare potions",
                "Scale to 200M+ for expert tier"
            ],
            CapitalTier.EXPERT: [
                "Bond-funded high-value item flipping",
                "Multiple parallel strategies",
                "Market manipulation opportunities",
                "Consider real estate (Construction contracts)"
            ]
        }
        
        return progressions.get(capital_tier, progressions[CapitalTier.STARTER])
    
    def _get_capital_tier(self, capital: int) -> CapitalTier:
        """Determine capital tier for strategy recommendations."""
        if capital < 10_000_000:
            return CapitalTier.STARTER
        elif capital < 50_000_000:
            return CapitalTier.INTERMEDIATE  
        elif capital < 200_000_000:
            return CapitalTier.ADVANCED
        else:
            return CapitalTier.EXPERT


# Async wrapper for Django integration
class AsyncMoneyMakerDetector:
    """Async wrapper for use in Django views and tasks."""
    
    @staticmethod
    async def get_opportunities(capital: int) -> Dict:
        """Get opportunities in Django-compatible format."""
        detector = MoneyMakerDetector()
        opportunities = await detector.detect_all_opportunities(capital)
        
        return {
            'opportunities': [
                {
                    'strategy_type': opp.strategy_type.value,
                    'name': opp.name,
                    'description': opp.description,
                    'hourly_profit_gp': opp.hourly_profit_gp,
                    'capital_required': opp.capital_required,
                    'profit_margin_pct': opp.profit_margin_pct,
                    'risk_level': opp.risk_level,
                    'overall_score': opp.opportunity_score.overall_score,
                    'ge_tax_cost': opp.ge_tax_cost,
                    'primary_items': opp.primary_items,
                    'strategy_data': opp.strategy_data
                }
                for opp in opportunities
            ],
            'total_found': len(opportunities),
            'capital_tier': detector._get_capital_tier(capital).value,
            'recommendations': detector.get_recommended_strategy_progression(capital)
        }