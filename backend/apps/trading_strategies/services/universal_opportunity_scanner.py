"""
Universal Opportunity Scanner

This service analyzes each item with market data and evaluates ALL possible trading strategies:
- High Alchemy
- Decanting (if it's a potion)
- Flipping
- Set Combining (if it's armor/equipment)
- Crafting (if raw materials available)

It then recommends the most profitable strategy per item.
"""

from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from django.db.models import Q
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.items.models import Item
from .decanting_detector import DecantingDetector
from .flipping_scanner import FlippingScanner
from .crafting_calculator import CraftingCalculator
from .set_combining_analyzer import SetCombiningAnalyzer
import logging
import re

logger = logging.getLogger(__name__)


class UniversalOpportunityScanner:
    """
    Scans all items with market data and evaluates the best trading strategy for each.
    """
    
    def __init__(self, min_profit_gp: int = 1000):
        """
        Initialize the universal scanner.
        
        Args:
            min_profit_gp: Minimum profit threshold in GP
        """
        self.min_profit_gp = min_profit_gp
        
        # Initialize specialized scanners
        self.decanting_detector = DecantingDetector(min_profit_gp=min_profit_gp)
        self.flipping_scanner = FlippingScanner(min_margin_gp=min_profit_gp)
        self.crafting_calculator = CraftingCalculator()
        self.set_combining_analyzer = SetCombiningAnalyzer()
    
    def scan_all_opportunities(self) -> Dict[str, List[Dict]]:
        """
        Scan all items with market data and return the best opportunities by strategy type.
        
        Returns:
            Dictionary with strategy types and their best opportunities
        """
        logger.info("Starting universal opportunity scan...")
        
        results = {
            'decanting': [],
            'flipping': [],
            'high_alchemy': [],
            'crafting': [],
            'set_combining': [],
            'cross_strategy_analysis': []
        }
        
        # Get all items with active market data
        items_with_prices = ProfitCalculation.objects.filter(
            Q(current_buy_price__gt=0) | Q(current_sell_price__gt=0)
        ).select_related('item')
        
        logger.info(f"Analyzing {items_with_prices.count()} items with market data...")
        
        # Analyze each item for all possible strategies
        for price_data in items_with_prices:
            item_strategies = self._analyze_item_all_strategies(price_data)
            
            # Add to appropriate categories
            for strategy_type, opportunity in item_strategies.items():
                if opportunity and opportunity['profit_gp'] >= self.min_profit_gp:
                    results[strategy_type].append(opportunity)
        
        # Sort each strategy type by profit
        for strategy_type in results:
            if results[strategy_type]:
                results[strategy_type].sort(
                    key=lambda x: x.get('profit_gp', 0), 
                    reverse=True
                )
        
        # Generate cross-strategy analysis
        results['cross_strategy_analysis'] = self._generate_cross_strategy_analysis(results)
        
        logger.info(f"Universal scan complete:")
        for strategy_type, opportunities in results.items():
            if strategy_type != 'cross_strategy_analysis':
                logger.info(f"  {strategy_type}: {len(opportunities)} opportunities")
        
        return results
    
    def _analyze_item_all_strategies(self, price_data: ProfitCalculation) -> Dict[str, Optional[Dict]]:
        """
        Analyze a single item for all possible trading strategies.
        
        Args:
            price_data: ProfitCalculation object with market data
            
        Returns:
            Dictionary mapping strategy types to opportunity data
        """
        item = price_data.item
        item_name = item.name
        strategies = {}
        
        # 1. High Alchemy Analysis
        strategies['high_alchemy'] = self._analyze_high_alchemy(price_data)
        
        # 2. Flipping Analysis
        strategies['flipping'] = self._analyze_flipping(price_data)
        
        # 3. Decanting Analysis (if it's a potion)
        if self._is_potion(item_name):
            strategies['decanting'] = self._analyze_decanting(price_data)
        else:
            strategies['decanting'] = None
        
        # 4. Set Combining Analysis (if it's armor/equipment)
        if self._is_equipment(item_name):
            strategies['set_combining'] = self._analyze_set_combining(price_data)
        else:
            strategies['set_combining'] = None
        
        # 5. Crafting Analysis (simplified - check if it's a raw material)
        strategies['crafting'] = self._analyze_crafting_potential(price_data)
        
        return strategies
    
    def _analyze_high_alchemy(self, price_data: ProfitCalculation) -> Optional[Dict]:
        """Analyze high alchemy potential for an item."""
        item = price_data.item
        buy_price = price_data.current_buy_price or 0
        
        if not buy_price or not item.high_alch:
            return None
        
        # Nature rune cost (usually around 180 GP)
        nature_rune_cost = 180
        profit_gp = item.high_alch - buy_price - nature_rune_cost
        
        if profit_gp <= 0:
            return None
        
        return {
            'item_id': item.item_id,
            'item_name': item.name,
            'strategy_type': 'high_alchemy',
            'profit_gp': profit_gp,
            'buy_price': buy_price,
            'alch_value': item.high_alch,
            'profit_per_hour': profit_gp * 1200,  # ~1200 alchs per hour
            'capital_efficiency': profit_gp / buy_price if buy_price > 0 else 0,
            'description': f"Buy {item.name} for {buy_price} GP, alch for {item.high_alch} GP"
        }
    
    def _analyze_flipping(self, price_data: ProfitCalculation) -> Optional[Dict]:
        """Analyze flipping potential for an item."""
        buy_price = price_data.current_buy_price or 0
        sell_price = price_data.current_sell_price or 0
        
        if not buy_price or not sell_price or sell_price <= buy_price:
            return None
        
        profit_gp = sell_price - buy_price
        margin_pct = (profit_gp / buy_price) * 100 if buy_price > 0 else 0
        
        if profit_gp <= 0:
            return None
        
        return {
            'item_id': price_data.item.item_id,
            'item_name': price_data.item.name,
            'strategy_type': 'flipping',
            'profit_gp': profit_gp,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'margin_percentage': margin_pct,
            'profit_per_hour': profit_gp * 24,  # Assume ~24 flips per hour
            'capital_efficiency': margin_pct / 100,
            'description': f"Buy {price_data.item.name} for {buy_price} GP, sell for {sell_price} GP"
        }
    
    def _analyze_decanting(self, price_data: ProfitCalculation) -> Optional[Dict]:
        """Analyze decanting potential using the decanting detector."""
        try:
            # Check if the decanting detector has this item in discovered families
            detector_opportunities = self.decanting_detector.detect_opportunities()
            
            # Find if this item appears in the decanting opportunities
            for opp in detector_opportunities:
                if opp.get('item_id') == price_data.item.item_id:
                    return {
                        'item_id': price_data.item.item_id,
                        'item_name': price_data.item.name,
                        'strategy_type': 'decanting',
                        'profit_gp': opp.get('profit_per_item', 0),
                        'from_dose': opp.get('from_dose', 4),
                        'to_dose': opp.get('to_dose', 3),
                        'description': f"Decant {price_data.item.name} from {opp.get('from_dose', 4)} to {opp.get('to_dose', 3)} dose"
                    }
        except Exception:
            pass  # If decanting analysis fails, just return None
        return None
    
    def _analyze_set_combining(self, price_data: ProfitCalculation) -> Optional[Dict]:
        """Analyze set combining potential (simplified check)."""
        # This would need integration with set combining analysis
        # For now, return None as set combining is handled by specialized analyzer
        return None
    
    def _analyze_crafting_potential(self, price_data: ProfitCalculation) -> Optional[Dict]:
        """Analyze if item can be used as crafting material."""
        item = price_data.item
        item_name = item.name.lower()
        
        # Simple heuristic for raw materials
        raw_material_keywords = [
            'ore', 'bar', 'log', 'plank', 'hide', 'leather', 'cloth', 'thread',
            'gem', 'crystal', 'herb', 'seed', 'essence', 'shard', 'scale'
        ]
        
        if any(keyword in item_name for keyword in raw_material_keywords):
            return {
                'item_id': item.item_id,
                'item_name': item.name,
                'strategy_type': 'crafting',
                'profit_gp': 0,  # Would need recipe lookup
                'description': f"Potential crafting material: {item.name}",
                'notes': 'Requires recipe analysis'
            }
        
        return None
    
    def _is_potion(self, item_name: str) -> bool:
        """Check if item is likely a potion."""
        dose_pattern = re.compile(r'^(.+?)\s*\((\d)\)$')
        match = dose_pattern.match(item_name)
        
        if not match:
            return False
        
        base_name = match.group(1).lower()
        potion_keywords = [
            'potion', 'brew', 'elixir', 'tonic', 'mixture', 'serum',
            'super', 'combat', 'prayer', 'strength', 'attack', 'defence'
        ]
        
        return any(keyword in base_name for keyword in potion_keywords)
    
    def _is_equipment(self, item_name: str) -> bool:
        """Check if item is likely equipment/armor."""
        equipment_keywords = [
            'helm', 'helmet', 'hat', 'coif', 'mask', 'hood',
            'body', 'top', 'shirt', 'robe', 'chest', 'plate',
            'legs', 'bottom', 'skirt', 'tassets',
            'boots', 'gloves', 'gauntlets', 'vambraces',
            'shield', 'defender', 'book', 'orb',
            'sword', 'axe', 'mace', 'spear', 'bow', 'staff'
        ]
        
        name_lower = item_name.lower()
        return any(keyword in name_lower for keyword in equipment_keywords)
    
    def _generate_cross_strategy_analysis(self, results: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Generate cross-strategy analysis to find items with multiple profitable strategies.
        
        Args:
            results: Results from all strategy scans
            
        Returns:
            List of items with multiple profitable strategies
        """
        item_strategies = {}
        
        # Collect all strategies by item_id
        for strategy_type, opportunities in results.items():
            if strategy_type == 'cross_strategy_analysis':
                continue
            
            for opp in opportunities:
                item_id = opp.get('item_id')
                if item_id:
                    if item_id not in item_strategies:
                        item_strategies[item_id] = {
                            'item_id': item_id,
                            'item_name': opp.get('item_name'),
                            'strategies': []
                        }
                    
                    item_strategies[item_id]['strategies'].append({
                        'type': strategy_type,
                        'profit_gp': opp.get('profit_gp', 0),
                        'description': opp.get('description', '')
                    })
        
        # Find items with multiple strategies
        multi_strategy_items = []
        for item_data in item_strategies.values():
            if len(item_data['strategies']) > 1:
                # Sort strategies by profit
                item_data['strategies'].sort(
                    key=lambda x: x['profit_gp'], 
                    reverse=True
                )
                
                best_strategy = item_data['strategies'][0]
                item_data['best_strategy'] = best_strategy['type']
                item_data['best_profit'] = best_strategy['profit_gp']
                
                multi_strategy_items.append(item_data)
        
        # Sort by best profit
        multi_strategy_items.sort(key=lambda x: x['best_profit'], reverse=True)
        
        logger.info(f"Found {len(multi_strategy_items)} items with multiple profitable strategies")
        
        return multi_strategy_items[:50]  # Return top 50