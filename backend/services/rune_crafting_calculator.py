"""
Real-time Rune Crafting Profit Calculator using OSRS Wiki API data.

This service calculates accurate rune crafting profits by:
1. Getting real-time essence prices (Pure essence, Rune essence, etc.)
2. Getting real-time rune sell prices from GE
3. Calculating profits per rune and per hour
4. Factoring in transportation costs, level requirements, and equipment needs
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from django.utils import timezone
from apps.items.models import Item
from apps.prices.models import PriceSnapshot

logger = logging.getLogger(__name__)


@dataclass
class RuneCraftingOpportunity:
    """Represents a rune crafting profit opportunity with real market data."""
    rune_type: str
    rune_item_id: int
    level_required: int
    runes_per_essence: float  # Multiplier (e.g., 1.0 for most, 1.4 for elemental with gloves)
    
    # Prices from real market data
    essence_buy_price: int
    rune_sell_price: int
    
    # Calculated profits
    profit_per_essence: int
    profit_per_rune: float
    
    # Volume and market data
    rune_volume: int
    essence_volume: int
    
    # Metadata
    last_updated: str
    confidence_score: float


class RuneCraftingCalculator:
    """Calculator for real-time rune crafting profits using OSRS data."""
    
    # Rune type definitions with their requirements
    RUNE_TYPES = {
        'air': {'item_id': 556, 'level': 1, 'altar': 'Air Altar'},
        'water': {'item_id': 555, 'level': 5, 'altar': 'Water Altar'},
        'earth': {'item_id': 557, 'level': 9, 'altar': 'Earth Altar'},
        'fire': {'item_id': 554, 'level': 14, 'altar': 'Fire Altar'},
        'mind': {'item_id': 558, 'level': 2, 'altar': 'Mind Altar'},
        'body': {'item_id': 559, 'level': 20, 'altar': 'Body Altar'},
        'cosmic': {'item_id': 564, 'level': 27, 'altar': 'Cosmic Altar'},
        'chaos': {'item_id': 562, 'level': 35, 'altar': 'Chaos Altar'},
        'nature': {'item_id': 561, 'level': 44, 'altar': 'Nature Altar'},
        'law': {'item_id': 563, 'level': 54, 'altar': 'Law Altar'},
        'death': {'item_id': 560, 'level': 65, 'altar': 'Death Altar'},
        'blood': {'item_id': 565, 'level': 77, 'altar': 'Blood Altar (Zeah)'},
        'soul': {'item_id': 566, 'level': 90, 'altar': 'Soul Altar (Zeah)'},
    }
    
    # Essence types
    ESSENCE_TYPES = {
        'rune_essence': 1436,    # For F2P runes (Air, Water, Earth, Fire, Mind, Body)
        'pure_essence': 7936,   # For P2P runes (Cosmic, Chaos, Nature, Law, Death, Blood, Soul)
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_latest_price(self, item_id: int) -> Optional[Tuple[int, int, PriceSnapshot]]:
        """
        Get latest buy/sell prices for an item.
        
        Returns:
            Tuple of (buy_price, sell_price, price_snapshot) or None
        """
        try:
            item = Item.objects.get(item_id=item_id)
            latest_price = item.price_snapshots.filter(
                high_price__isnull=False,
                low_price__isnull=False,
                high_price__gt=0,
                low_price__gt=0
            ).order_by('-created_at').first()
            
            if latest_price:
                # Use high_price as buy price (instant buy) and low_price as sell price (instant sell)
                return (latest_price.high_price, latest_price.low_price, latest_price)
            
            return None
            
        except Item.DoesNotExist:
            self.logger.warning(f"Item {item_id} not found in database")
            return None
    
    def calculate_rune_crafting_profits(self, min_level: int = 1, max_level: int = 99) -> List[RuneCraftingOpportunity]:
        """
        Calculate current rune crafting profit opportunities.
        
        Args:
            min_level: Minimum runecrafting level to consider
            max_level: Maximum runecrafting level to consider
            
        Returns:
            List of RuneCraftingOpportunity objects sorted by profit
        """
        opportunities = []
        
        # Get essence prices first
        pure_essence_data = self.get_latest_price(self.ESSENCE_TYPES['pure_essence'])
        rune_essence_data = self.get_latest_price(self.ESSENCE_TYPES['rune_essence'])
        
        if not pure_essence_data and not rune_essence_data:
            self.logger.error("Could not get essence prices - no opportunities available")
            return opportunities
        
        for rune_name, rune_info in self.RUNE_TYPES.items():
            level_req = rune_info['level']
            
            # Skip if outside level range
            if level_req < min_level or level_req > max_level:
                continue
            
            # Get rune prices
            rune_price_data = self.get_latest_price(rune_info['item_id'])
            if not rune_price_data:
                continue
                
            rune_buy_price, rune_sell_price, rune_snapshot = rune_price_data
            
            # Determine which essence to use
            if level_req <= 20:  # F2P runes use rune essence
                essence_data = rune_essence_data
                essence_name = 'rune_essence'
            else:  # P2P runes use pure essence
                essence_data = pure_essence_data
                essence_name = 'pure_essence'
            
            if not essence_data:
                continue
                
            essence_buy_price, essence_sell_price, essence_snapshot = essence_data
            
            # Calculate basic profit (1 essence = 1 rune at base level)
            base_runes_per_essence = 1.0
            
            # Apply level multipliers (simplified - real game has complex mechanics)
            if level_req >= 44:  # Nature and above get better multipliers
                base_runes_per_essence = 1.2
            if level_req >= 65:  # Death and above 
                base_runes_per_essence = 1.3
            if level_req >= 77:  # Blood and soul
                base_runes_per_essence = 1.4
            
            # Calculate profits
            gross_profit_per_essence = (rune_sell_price * base_runes_per_essence) - essence_buy_price
            profit_per_rune = gross_profit_per_essence / base_runes_per_essence
            
            # Calculate confidence based on volume and price freshness
            confidence = min(1.0, (
                (min(rune_snapshot.total_volume or 0, 100) / 100) * 0.5 +  # Volume component
                (min(essence_snapshot.total_volume or 0, 1000) / 1000) * 0.5  # Essence volume
            ))
            
            opportunities.append(RuneCraftingOpportunity(
                rune_type=rune_name.title(),
                rune_item_id=rune_info['item_id'],
                level_required=level_req,
                runes_per_essence=base_runes_per_essence,
                essence_buy_price=essence_buy_price,
                rune_sell_price=rune_sell_price,
                profit_per_essence=int(gross_profit_per_essence),
                profit_per_rune=profit_per_rune,
                rune_volume=rune_snapshot.total_volume or 0,
                essence_volume=essence_snapshot.total_volume or 0,
                last_updated=rune_snapshot.created_at.isoformat() if rune_snapshot.created_at else '',
                confidence_score=confidence
            ))
        
        # Sort by profit per essence (descending)
        opportunities.sort(key=lambda x: x.profit_per_essence, reverse=True)
        
        return opportunities
    
    def calculate_hourly_profits(self, opportunity: RuneCraftingOpportunity) -> Dict:
        """
        Calculate hourly profit projections for a rune crafting opportunity.
        
        Args:
            opportunity: RuneCraftingOpportunity to analyze
            
        Returns:
            Dict with hourly profit calculations
        """
        # Assume different rates based on rune type and level
        if opportunity.level_required <= 20:
            # F2P runes - faster banking, closer altars
            essences_per_hour = 2000
        elif opportunity.level_required <= 44:
            # Mid-level runes
            essences_per_hour = 1500
        elif opportunity.level_required <= 65:
            # High-level runes - teleports available but further altars
            essences_per_hour = 1200
        else:
            # Blood/Soul runes - special mechanics, slower
            essences_per_hour = 800
        
        runes_per_hour = int(essences_per_hour * opportunity.runes_per_essence)
        hourly_profit = int(opportunity.profit_per_essence * essences_per_hour)
        
        return {
            'essences_per_hour': essences_per_hour,
            'runes_per_hour': runes_per_hour,
            'hourly_profit_gp': hourly_profit,
            'hourly_xp': essences_per_hour * 10,  # Simplified XP calc
            'capital_required': essences_per_hour * opportunity.essence_buy_price,
            'profit_margin_pct': (opportunity.profit_per_essence / opportunity.essence_buy_price) * 100 if opportunity.essence_buy_price > 0 else 0
        }