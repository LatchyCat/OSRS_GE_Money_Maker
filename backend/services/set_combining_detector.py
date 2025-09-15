"""
Set Combining Detector Service

Detects profitable armor/weapon set combining opportunities.
Exploits the "lazy tax" - premium players pay for convenience of buying complete sets
instead of individual pieces.

Your friend's approach: buy pieces separately, combine, sell as complete set
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Q, F, Count, Avg, Min, Max
from django.utils import timezone
from django.db import transaction

from apps.items.models import Item
from apps.prices.models import ProfitCalculation, PriceSnapshot
from apps.trading_strategies.models import (
    TradingStrategy, SetCombiningOpportunity, StrategyType, MarketCondition
)
from services.weird_gloop_client import WeirdGloopAPIClient, GrandExchangeTax, MoneyMakerDataFetcher

logger = logging.getLogger(__name__)


@dataclass
class SetCombiningAnalysis:
    """Analysis data for a set combining opportunity"""
    set_id: int
    set_name: str
    pieces: List[Dict]
    
    # Pricing
    pieces_total_cost: int
    set_sell_price: int
    gross_profit: int
    ge_tax: int
    net_profit: int
    
    # Lazy tax metrics
    lazy_tax_gp: int
    lazy_tax_percentage: float
    
    # Risk factors
    liquidity_score: float  # 0-1, based on volumes
    price_stability: float  # 0-1, based on volatility
    acquisition_difficulty: float  # 0-1, how hard to get all pieces
    
    # Capital efficiency
    capital_required: int
    profit_margin_pct: float
    hourly_profit_potential: int
    
    # Market timing
    optimal_buy_times: List[int] = None  # Hours when pieces are cheapest
    optimal_sell_times: List[int] = None  # Hours when sets sell best


class SetCombiningDetector:
    """
    Detects profitable set combining opportunities.
    
    This strategy exploits player laziness - many players prefer to buy complete
    armor/weapon sets rather than individual pieces, creating profit opportunities.
    """
    
    def __init__(self):
        self.weird_gloop_client = WeirdGloopAPIClient()
        self.data_fetcher = MoneyMakerDataFetcher(self.weird_gloop_client)
        
        # Known profitable armor/weapon sets
        # Based on OSRS Wiki and common player usage
        self.armor_sets = {
            # Barrows sets (very popular)
            4856: {  # Ahrim's set
                'pieces': [4708, 4710, 4712, 4714],  # Hood, Top, Skirt, Staff
                'name': "Ahrim's armor set",
                'set_type': 'barrows',
                'popularity': 'high'
            },
            4857: {  # Dharok's set  
                'pieces': [4716, 4718, 4720, 4722],  # Helm, Body, Legs, Axe
                'name': "Dharok's armor set",
                'set_type': 'barrows',
                'popularity': 'very_high'  # Most popular barrows set
            },
            4858: {  # Guthan's set
                'pieces': [4724, 4726, 4728, 4730],  # Helm, Body, Skirt, Spear
                'name': "Guthan's armor set", 
                'set_type': 'barrows',
                'popularity': 'high'
            },
            4859: {  # Karil's set
                'pieces': [4732, 4734, 4736, 4738],  # Coif, Top, Skirt, Bow
                'name': "Karil's armor set",
                'set_type': 'barrows', 
                'popularity': 'medium'
            },
            4860: {  # Torag's set
                'pieces': [4740, 4742, 4744, 4745, 4746],  # Helm, Body, Legs, Hammers
                'name': "Torag's armor set",
                'set_type': 'barrows',
                'popularity': 'medium'
            },
            4861: {  # Verac's set
                'pieces': [4753, 4755, 4757, 4759],  # Helm, Top, Skirt, Flail
                'name': "Verac's armor set",
                'set_type': 'barrows',
                'popularity': 'high'
            },
            
            # God Wars Dungeon sets (high value)
            11828: {  # Armadyl armor set (constructed from pieces)
                'pieces': [11826, 11828, 11830],  # Helm, Chestplate, Chainskirt  
                'name': 'Armadyl armor set',
                'set_type': 'god_wars',
                'popularity': 'very_high'
            },
            11832: {  # Bandos armor set (constructed from pieces)
                'pieces': [11832, 11834],  # Chestplate, Tassets
                'name': 'Bandos armor set',
                'set_type': 'god_wars', 
                'popularity': 'very_high'
            },
            
            # Void sets (popular for PvP/PvM)
            11665: {  # Void melee set
                'pieces': [11665, 11664, 11668, 8842],  # Helm, Top, Robe, Gloves
                'name': 'Void melee set',
                'set_type': 'void',
                'popularity': 'high'
            },
            
            # Dragon sets (mid-level popular)
            1149: {  # Dragon med helm
                'pieces': [1149, 1127, 4087],  # Med helm, Chainbody, Legs
                'name': 'Dragon armor set',
                'set_type': 'dragon',
                'popularity': 'medium'
            }
        }
        
        # Weapon sets that can be combined
        self.weapon_sets = {
            # Godswords (very high value)
            11802: {  # Armadyl godsword
                'pieces': [11798, 11704],  # Godsword blade, Armadyl hilt
                'name': 'Armadyl godsword',
                'set_type': 'godsword',
                'popularity': 'very_high'
            },
            11804: {  # Bandos godsword
                'pieces': [11798, 11702],  # Godsword blade, Bandos hilt  
                'name': 'Bandos godsword',
                'set_type': 'godsword',
                'popularity': 'very_high'
            },
            11806: {  # Saradomin godsword
                'pieces': [11798, 11700],  # Godsword blade, Saradomin hilt
                'name': 'Saradomin godsword', 
                'set_type': 'godsword',
                'popularity': 'high'
            },
            11808: {  # Zamorak godsword
                'pieces': [11798, 11706],  # Godsword blade, Zamorak hilt
                'name': 'Zamorak godsword',
                'set_type': 'godsword', 
                'popularity': 'medium'
            }
        }
        
        # Combine all sets
        self.all_sets = {**self.armor_sets, **self.weapon_sets}
    
    async def detect_set_opportunities(self, capital_available: int = 50_000_000) -> List[SetCombiningAnalysis]:
        """
        Detect all profitable set combining opportunities using real-time Wiki data and volume analysis.
        
        Args:
            capital_available: Available capital for set combining
            
        Returns:
            List of profitable set opportunities ranked by volume-weighted profit
        """
        logger.info(f"Detecting set combining opportunities with {capital_available:,} GP using real-time Wiki data")
        
        opportunities = []
        
        async with self.weird_gloop_client as client:
            # Fetch comprehensive pricing and volume data
            set_data = await self.data_fetcher.fetch_set_combining_data(self.all_sets)
            
            for set_id, data in set_data.items():
                if not data['is_profitable']:
                    continue
                
                set_info = self.all_sets.get(set_id, {})
                if not set_info:
                    continue
                
                # Check capital requirements for both strategies
                combining_capital = data.get('pieces_total_buy_cost', 0)
                decombining_capital = data.get('set_buy_price', 0)
                
                required_capital = combining_capital if data['best_strategy'] == 'combining' else decombining_capital
                
                # Only consider sets within our capital range
                if required_capital > capital_available * 0.8:  # Don't use more than 80%
                    continue
                
                # Apply volume confidence filter - only consider opportunities with decent volume
                if data.get('volume_confidence', 0) < 0.1:  # Less than 10% confidence = skip
                    continue
                
                analysis = await self._analyze_set_opportunity(set_id, set_info, data)
                if analysis and analysis.net_profit > 5000:  # Minimum 5K profit (reduced from 10K due to better accuracy)
                    opportunities.append(analysis)
        
        # Sort by volume-weighted profit (profit * volume_confidence)
        opportunities.sort(key=lambda x: x.net_profit * x.liquidity_score, reverse=True)
        
        logger.info(f"Found {len(opportunities)} volume-validated profitable set opportunities")
        return opportunities
    
    async def _analyze_set_opportunity(self, set_id: int, set_info: Dict, 
                                     pricing_data: Dict) -> Optional[SetCombiningAnalysis]:
        """
        Perform detailed analysis of a set combining opportunity using enhanced Wiki data.
        
        Args:
            set_id: Complete set item ID
            set_info: Set metadata
            pricing_data: Enhanced pricing data with volume analysis from weird gloop
            
        Returns:
            Detailed analysis or None if not viable
        """
        try:
            # Use the best strategy determined by the data fetcher
            best_strategy = pricing_data['best_strategy']
            profit_analysis = pricing_data['profit_analysis']
            
            if best_strategy == 'combining':
                # Buy pieces -> sell set
                capital_required = pricing_data['pieces_total_buy_cost']
                revenue = pricing_data['set_sell_price']
                strategy_description = pricing_data['strategy_description']
            else:
                # Buy set -> sell pieces
                capital_required = pricing_data['set_buy_price']
                revenue = pricing_data['pieces_total_sell_value']
                strategy_description = pricing_data['strategy_description']
            
            net_profit = profit_analysis['profit_per_item']
            ge_tax = profit_analysis['ge_tax']
            
            if net_profit <= 0:
                return None
            
            # Use volume confidence scores from Wiki API
            liquidity_score = pricing_data['volume_confidence']
            piece_liquidity = pricing_data['avg_piece_volume_confidence']
            set_liquidity = pricing_data['set_volume_confidence']
            
            # Enhanced price stability using volume data
            price_stability = self._calculate_price_stability_from_volume(pricing_data['volume_data'])
            
            # Acquisition difficulty based on volume confidence
            if best_strategy == 'combining':
                # Difficulty acquiring individual pieces
                acquisition_difficulty = 1.0 - piece_liquidity
            else:
                # Difficulty acquiring complete set
                acquisition_difficulty = 1.0 - set_liquidity
            
            # Calculate profit metrics
            lazy_tax_gp = net_profit
            lazy_tax_pct = pricing_data['lazy_tax_percentage']
            profit_margin_pct = (net_profit / capital_required * 100) if capital_required > 0 else 0
            
            # Estimate hourly profit with volume-based adjustment
            base_sets_per_hour = self._estimate_sets_per_hour(set_info['set_type'], len(pricing_data['pieces_data']))
            volume_adjusted_rate = base_sets_per_hour * liquidity_score  # Reduce rate based on volume constraints
            hourly_profit = int(net_profit * volume_adjusted_rate)
            
            return SetCombiningAnalysis(
                set_id=set_id,
                set_name=set_info['name'],
                pieces=[
                    {
                        'item_id': piece['item_id'],
                        'buy_price': piece['buy_price'],
                        'sell_price': piece['sell_price'],
                        'volume': piece['volume'],
                        'volume_confidence': piece['volume_confidence']
                    }
                    for piece in pricing_data['pieces_data']
                ],
                pieces_total_cost=capital_required,
                set_sell_price=revenue,
                gross_profit=revenue - capital_required,
                ge_tax=ge_tax,
                net_profit=net_profit,
                lazy_tax_gp=lazy_tax_gp,
                lazy_tax_percentage=lazy_tax_pct,
                liquidity_score=liquidity_score,
                price_stability=price_stability,
                acquisition_difficulty=acquisition_difficulty,
                capital_required=capital_required,
                profit_margin_pct=profit_margin_pct,
                hourly_profit_potential=hourly_profit,
                optimal_buy_times=None,  # Could be enhanced with time-based volume analysis
                optimal_sell_times=None
            )
            
        except Exception as e:
            logger.error(f"Error analyzing set {set_id}: {e}")
            return None
    
    def _calculate_price_stability_from_volume(self, volume_data: Dict) -> float:
        """
        Calculate price stability score from volume timeseries data.
        
        Args:
            volume_data: Volume timeseries data for set and pieces
            
        Returns:
            Price stability score (0.0 to 1.0)
        """
        try:
            all_volume_series = []
            
            # Collect all volume timeseries
            if 'set_timeseries' in volume_data:
                all_volume_series.append(volume_data['set_timeseries'])
            
            if 'piece_timeseries' in volume_data:
                for piece_series in volume_data['piece_timeseries'].values():
                    all_volume_series.append(piece_series)
            
            if not all_volume_series:
                return 0.5  # Default stability
            
            stability_scores = []
            
            for series in all_volume_series:
                if len(series) < 2:
                    continue
                
                volumes = [point.get('volume', 0) for point in series if isinstance(point, dict)]
                volumes = [v for v in volumes if v > 0]
                
                if len(volumes) < 2:
                    continue
                
                # Calculate coefficient of variation (stability indicator)
                avg_volume = sum(volumes) / len(volumes)
                if avg_volume > 0:
                    variance = sum((v - avg_volume) ** 2 for v in volumes) / len(volumes)
                    cv = (variance ** 0.5) / avg_volume  # Coefficient of variation
                    stability = max(0.0, 1.0 - cv)  # Higher CV = lower stability
                    stability_scores.append(stability)
            
            if stability_scores:
                return sum(stability_scores) / len(stability_scores)
            else:
                return 0.5  # Default stability
                
        except Exception as e:
            logger.warning(f"Error calculating price stability from volume: {e}")
            return 0.5
    
    def _calculate_liquidity_score(self, pieces_data: List[Dict]) -> float:
        """Calculate liquidity score based on piece volumes."""
        if not pieces_data:
            return 0.0
        
        # Score based on minimum volume (weakest link)
        min_volume = min(piece.get('volume', 0) for piece in pieces_data)
        avg_volume = sum(piece.get('volume', 0) for piece in pieces_data) / len(pieces_data)
        
        # Normalize to 0-1 scale
        min_score = min(1.0, min_volume / 100)  # 100+ volume = good liquidity
        avg_score = min(1.0, avg_volume / 500)  # 500+ avg = excellent liquidity
        
        return (min_score * 0.7 + avg_score * 0.3)  # Weighted towards minimum
    
    def _estimate_price_stability(self, set_type: str) -> float:
        """Estimate price stability based on set type."""
        stability_scores = {
            'barrows': 0.8,      # Very stable, consistent demand
            'god_wars': 0.6,     # Moderately stable, can be volatile  
            'godsword': 0.5,     # Can be quite volatile
            'void': 0.9,         # Very stable, PvP demand
            'dragon': 0.7,       # Stable mid-level gear
            'other': 0.5         # Unknown stability
        }
        
        return stability_scores.get(set_type, 0.5)
    
    def _assess_acquisition_difficulty(self, pieces_data: List[Dict]) -> float:
        """Assess how difficult it is to acquire all pieces."""
        if not pieces_data:
            return 1.0  # Very difficult
        
        # Based on number of pieces and their volumes
        piece_count = len(pieces_data)
        avg_volume = sum(piece.get('volume', 0) for piece in pieces_data) / piece_count
        
        # More pieces = harder to acquire
        piece_difficulty = min(1.0, piece_count / 6)  # 6+ pieces = max difficulty
        
        # Lower volume = harder to acquire
        volume_difficulty = max(0.0, 1.0 - (avg_volume / 200))  # 200+ volume = easy
        
        return (piece_difficulty * 0.4 + volume_difficulty * 0.6)
    
    def _estimate_sets_per_hour(self, set_type: str, piece_count: int) -> int:
        """Estimate how many sets can be completed per hour."""
        # Base rate depends on set complexity
        base_rates = {
            'barrows': 3,        # 3 sets per hour
            'god_wars': 2,       # 2 sets per hour (expensive, careful)
            'godsword': 1,       # 1 set per hour (very expensive)
            'void': 4,           # 4 sets per hour (cheaper pieces)
            'dragon': 4,         # 4 sets per hour
            'other': 2           # Conservative default
        }
        
        base_rate = base_rates.get(set_type, 2)
        
        # Adjust for piece count (more pieces = slower)
        if piece_count > 4:
            base_rate = max(1, base_rate - 1)
        elif piece_count <= 2:
            base_rate += 1
        
        return base_rate
    
    @transaction.atomic
    def create_strategy_from_analysis(self, analysis: SetCombiningAnalysis) -> Optional[TradingStrategy]:
        """
        Create a TradingStrategy and SetCombiningOpportunity from analysis.
        
        Args:
            analysis: Set combining analysis
            
        Returns:
            Created TradingStrategy or None if failed
        """
        try:
            # Determine risk level
            if analysis.liquidity_score > 0.7 and analysis.price_stability > 0.7:
                risk_level = 'low'
            elif analysis.liquidity_score > 0.5 and analysis.price_stability > 0.5:
                risk_level = 'medium'
            elif analysis.acquisition_difficulty > 0.8:
                risk_level = 'extreme'  # Very hard to acquire pieces
            else:
                risk_level = 'high'
            
            # Calculate confidence score
            confidence_factors = [
                analysis.liquidity_score,
                analysis.price_stability,
                1.0 - analysis.acquisition_difficulty,  # Lower difficulty = higher confidence
                min(1.0, analysis.profit_margin_pct / 50)  # 50% margin = max confidence
            ]
            confidence = sum(confidence_factors) / len(confidence_factors)
            
            # Estimate time (includes acquisition time)
            time_per_set = max(15, int(30 * analysis.acquisition_difficulty))  # 15-30 minutes per set
            
            # Create or update strategy
            strategy, created = TradingStrategy.objects.get_or_create(
                strategy_type=StrategyType.SET_COMBINING,
                name=f"Combine {analysis.set_name}",
                defaults={
                    'description': (
                        f"Buy {len(analysis.pieces)} pieces for {analysis.pieces_total_cost:,} GP total, "
                        f"combine into {analysis.set_name}, sell for {analysis.set_sell_price:,} GP. "
                        f"Net profit: {analysis.net_profit:,} GP ({analysis.profit_margin_pct:.1f}% margin) "
                        f"after {analysis.ge_tax:,} GP GE tax. "
                        f"Lazy tax: {analysis.lazy_tax_percentage:.1f}%."
                    ),
                    'potential_profit_gp': analysis.net_profit,
                    'profit_margin_pct': Decimal(str(round(analysis.profit_margin_pct, 4))),
                    'risk_level': risk_level,
                    'min_capital_required': analysis.capital_required,
                    'recommended_capital': analysis.capital_required * 3,  # For 3 sets
                    'optimal_market_condition': 'stable',
                    'estimated_time_minutes': time_per_set,
                    'max_volume_per_day': analysis.hourly_profit_potential * 8 // analysis.net_profit,  # 8h day
                    'confidence_score': Decimal(str(round(confidence, 3))),
                    'is_active': True,
                    'strategy_data': {
                        'set_type': 'set_combining',
                        'piece_count': len(analysis.pieces),
                        'lazy_tax_percentage': analysis.lazy_tax_percentage,
                        'ge_tax': analysis.ge_tax,
                        'liquidity_score': analysis.liquidity_score,
                        'price_stability': analysis.price_stability,
                        'acquisition_difficulty': analysis.acquisition_difficulty
                    }
                }
            )
            
            if not created:
                # Update existing strategy
                strategy.potential_profit_gp = analysis.net_profit
                strategy.profit_margin_pct = Decimal(str(round(analysis.profit_margin_pct, 4)))
                strategy.risk_level = risk_level
                strategy.min_capital_required = analysis.capital_required
                strategy.recommended_capital = analysis.capital_required * 3
                strategy.confidence_score = Decimal(str(round(confidence, 3)))
                strategy.save()
            
            # Create or update set combining opportunity
            set_opportunity, _ = SetCombiningOpportunity.objects.update_or_create(
                set_item_id=analysis.set_id,
                defaults={
                    'strategy': strategy,
                    'set_name': analysis.set_name,
                    'piece_ids': [piece['item_id'] for piece in analysis.pieces],
                    'piece_names': [f"Piece {piece['item_id']}" for piece in analysis.pieces],
                    'individual_pieces_total_cost': analysis.pieces_total_cost,
                    'complete_set_price': analysis.set_sell_price,
                    'lazy_tax_profit': analysis.lazy_tax_gp,
                    'piece_volumes': {
                        str(piece['item_id']): piece['volume'] for piece in analysis.pieces
                    },
                    'set_volume': 0  # TODO: Get set volume data
                }
            )
            
            logger.info(f"Created set combining strategy: {strategy.name}")
            return strategy
            
        except Exception as e:
            logger.error(f"Error creating strategy for {analysis.set_name}: {e}")
            return None
    
    async def scan_and_create_opportunities(self, capital_available: int = 50_000_000) -> int:
        """
        Full scan: detect opportunities and create strategy records.
        
        Args:
            capital_available: Available capital for strategies
            
        Returns:
            Number of strategies created
        """
        logger.info("Starting set combining opportunity scan...")
        
        opportunities = await self.detect_set_opportunities(capital_available)
        logger.info(f"Found {len(opportunities)} set combining opportunities")
        
        created_count = 0
        for analysis in opportunities:
            strategy = self.create_strategy_from_analysis(analysis)
            if strategy:
                created_count += 1
        
        logger.info(f"Created {created_count} set combining strategies")
        return created_count
    
    def get_top_lazy_tax_opportunities(self, limit: int = 10) -> List[Dict]:
        """
        Get top opportunities sorted by lazy tax percentage.
        
        Args:
            limit: Maximum number of opportunities to return
            
        Returns:
            List of opportunity data sorted by lazy tax
        """
        opportunities = SetCombiningOpportunity.objects.select_related(
            'strategy'
        ).filter(
            strategy__is_active=True,
            lazy_tax_profit__gt=0
        ).order_by('-lazy_tax_profit')[:limit]
        
        return [
            {
                'set_name': opp.set_name,
                'lazy_tax_profit': opp.lazy_tax_profit,
                'pieces_cost': opp.individual_pieces_total_cost,
                'set_price': opp.complete_set_price,
                'lazy_tax_percentage': (opp.lazy_tax_profit / opp.individual_pieces_total_cost * 100) if opp.individual_pieces_total_cost > 0 else 0,
                'piece_count': len(opp.piece_ids),
                'strategy_risk_level': opp.strategy.risk_level,
                'strategy_confidence': float(opp.strategy.confidence_score)
            }
            for opp in opportunities
        ]