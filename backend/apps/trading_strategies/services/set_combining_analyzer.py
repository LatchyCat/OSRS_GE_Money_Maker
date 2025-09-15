from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from django.db import transaction
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.items.models import Item
from apps.trading_strategies.models import TradingStrategy, SetCombiningOpportunity, StrategyType
import logging

logger = logging.getLogger(__name__)


class SetCombiningAnalyzer:
    """
    Analyzes armor and weapon set combining opportunities for "lazy tax" profits.
    
    The "lazy tax" is profit made from players who prefer to buy complete sets
    rather than individual pieces. For example:
    - Buy individual barrows pieces for 15M total
    - Combine into full set
    - Sell full set for 18M
    - Profit: 3M GP from player convenience
    """
    
    # Armor and weapon sets that can be combined for profit
    SET_COMBINATIONS = {
        # Barrows sets
        'Ahrim\'s set': {
            'set_item_id': 4856,
            'pieces': [
                {'id': 4708, 'name': 'Ahrim\'s hood'},
                {'id': 4714, 'name': 'Ahrim\'s robetop'},
                {'id': 4720, 'name': 'Ahrim\'s robeskirt'},
                {'id': 4710, 'name': 'Ahrim\'s staff'},
            ]
        },
        'Dharok\'s set': {
            'set_item_id': 4857,
            'pieces': [
                {'id': 4716, 'name': 'Dharok\'s helm'},
                {'id': 4720, 'name': 'Dharok\'s platebody'},
                {'id': 4722, 'name': 'Dharok\'s platelegs'},
                {'id': 4718, 'name': 'Dharok\'s greataxe'},
            ]
        },
        'Guthan\'s set': {
            'set_item_id': 4858,
            'pieces': [
                {'id': 4724, 'name': 'Guthan\'s helm'},
                {'id': 4726, 'name': 'Guthan\'s platebody'},
                {'id': 4728, 'name': 'Guthan\'s chainskirt'},
                {'id': 4726, 'name': 'Guthan\'s warspear'},
            ]
        },
        'Karil\'s set': {
            'set_item_id': 4859,
            'pieces': [
                {'id': 4732, 'name': 'Karil\'s coif'},
                {'id': 4736, 'name': 'Karil\'s leathertop'},
                {'id': 4738, 'name': 'Karil\'s leatherskirt'},
                {'id': 4734, 'name': 'Karil\'s crossbow'},
            ]
        },
        'Torag\'s set': {
            'set_item_id': 4860,
            'pieces': [
                {'id': 4745, 'name': 'Torag\'s helm'},
                {'id': 4749, 'name': 'Torag\'s platebody'},
                {'id': 4751, 'name': 'Torag\'s platelegs'},
                {'id': 4747, 'name': 'Torag\'s hammers'},
            ]
        },
        'Verac\'s set': {
            'set_item_id': 4861,
            'pieces': [
                {'id': 4753, 'name': 'Verac\'s helm'},
                {'id': 4757, 'name': 'Verac\'s brassard'},
                {'id': 4759, 'name': 'Verac\'s plateskirt'},
                {'id': 4755, 'name': 'Verac\'s flail'},
            ]
        },
        
        # God Wars Dungeon sets
        'Bandos set': {
            'set_item_id': None,  # No official set item, but can be combined
            'pieces': [
                {'id': 11832, 'name': 'Bandos chestplate'},
                {'id': 11834, 'name': 'Bandos tassets'},
                {'id': 11836, 'name': 'Bandos boots'},
            ]
        },
        'Armadyl set': {
            'set_item_id': None,
            'pieces': [
                {'id': 11826, 'name': 'Armadyl helmet'},
                {'id': 11828, 'name': 'Armadyl chestplate'},
                {'id': 11830, 'name': 'Armadyl chainskirt'},
            ]
        },
        
        # Dragon sets
        'Green d\'hide set': {
            'set_item_id': None,
            'pieces': [
                {'id': 1135, 'name': 'Green d\'hide body'},
                {'id': 1099, 'name': 'Green d\'hide chaps'},
                {'id': 1065, 'name': 'Green d\'hide vambraces'},
            ]
        },
        'Blue d\'hide set': {
            'set_item_id': None,
            'pieces': [
                {'id': 2499, 'name': 'Blue d\'hide body'},
                {'id': 2493, 'name': 'Blue d\'hide chaps'},
                {'id': 2487, 'name': 'Blue d\'hide vambraces'},
            ]
        },
        'Red d\'hide set': {
            'set_item_id': None,
            'pieces': [
                {'id': 2501, 'name': 'Red d\'hide body'},
                {'id': 2495, 'name': 'Red d\'hide chaps'},
                {'id': 2489, 'name': 'Red d\'hide vambraces'},
            ]
        },
        'Black d\'hide set': {
            'set_item_id': None,
            'pieces': [
                {'id': 2503, 'name': 'Black d\'hide body'},
                {'id': 2497, 'name': 'Black d\'hide chaps'},
                {'id': 2491, 'name': 'Black d\'hide vambraces'},
            ]
        },
        
        # Void sets
        'Void melee set': {
            'set_item_id': None,
            'pieces': [
                {'id': 8842, 'name': 'Void melee helm'},
                {'id': 8839, 'name': 'Void knight top'},
                {'id': 8840, 'name': 'Void knight robe'},
                {'id': 8841, 'name': 'Void knight gloves'},
            ]
        },
        'Void ranger set': {
            'set_item_id': None,
            'pieces': [
                {'id': 8843, 'name': 'Void ranger helm'},
                {'id': 8839, 'name': 'Void knight top'},
                {'id': 8840, 'name': 'Void knight robe'},
                {'id': 8841, 'name': 'Void knight gloves'},
            ]
        },
        'Void mage set': {
            'set_item_id': None,
            'pieces': [
                {'id': 8844, 'name': 'Void mage helm'},
                {'id': 8839, 'name': 'Void knight top'},
                {'id': 8840, 'name': 'Void knight robe'},
                {'id': 8841, 'name': 'Void knight gloves'},
            ]
        },
    }
    
    def __init__(self, min_lazy_tax: int = 100000, min_margin_pct: float = 5.0):
        """
        Initialize the set combining analyzer.
        
        Args:
            min_lazy_tax: Minimum "lazy tax" profit in GP
            min_margin_pct: Minimum profit margin percentage
        """
        self.min_lazy_tax = min_lazy_tax
        self.min_margin_pct = min_margin_pct
    
    def analyze_opportunities(self) -> List[Dict]:
        """
        Analyze all set combining opportunities.
        
        Returns:
            List of profitable set combining opportunities
        """
        opportunities = []
        
        for set_name, set_data in self.SET_COMBINATIONS.items():
            try:
                opportunity = self._analyze_set(set_name, set_data)
                if opportunity:
                    opportunities.append(opportunity)
            except Exception as e:
                logger.warning(f"Error analyzing set {set_name}: {e}")
        
        # Sort by lazy tax profit (highest first)
        opportunities.sort(key=lambda x: x['lazy_tax_profit'], reverse=True)
        
        return opportunities
    
    def _analyze_set(self, set_name: str, set_data: Dict) -> Optional[Dict]:
        """
        Analyze a specific armor/weapon set for combining profitability.
        
        Args:
            set_name: Name of the set
            set_data: Set data with pieces and set item ID
            
        Returns:
            Opportunity dictionary or None if not profitable
        """
        pieces = set_data['pieces']
        set_item_id = set_data.get('set_item_id')
        
        # Get prices for individual pieces
        piece_prices = []
        piece_volumes = {}
        total_pieces_cost = 0
        
        for piece in pieces:
            piece_price_data = self._get_item_price(piece['id'])
            if not piece_price_data:
                logger.warning(f"No price data for {piece['name']} ({piece['id']})")
                return None
            
            piece_cost = piece_price_data['high']  # Price we buy at
            piece_prices.append({
                'id': piece['id'],
                'name': piece['name'],
                'price': piece_cost,
                'volume': piece_price_data.get('highTime', 0)
            })
            piece_volumes[piece['id']] = piece_price_data.get('highTime', 0)
            total_pieces_cost += piece_cost
        
        # If there's no official set item, estimate set value
        if set_item_id:
            set_price_data = self._get_item_price(set_item_id)
            if not set_price_data:
                return None
            set_price = set_price_data['low']  # Price we sell at
            set_volume = set_price_data.get('lowTime', 0)
        else:
            # For sets without official set item, estimate premium
            # Players typically pay 10-20% premium for convenience
            estimated_premium = 0.15  # 15% premium
            set_price = int(total_pieces_cost * (1 + estimated_premium))
            set_volume = min([p['volume'] for p in piece_prices])  # Limited by lowest volume piece
        
        # Calculate lazy tax profit
        lazy_tax_profit = set_price - total_pieces_cost
        
        if lazy_tax_profit < self.min_lazy_tax:
            return None
        
        margin_pct = (lazy_tax_profit / total_pieces_cost * 100) if total_pieces_cost > 0 else 0
        
        if margin_pct < self.min_margin_pct:
            return None
        
        return {
            'set_name': set_name,
            'set_item_id': set_item_id,
            'piece_ids': [p['id'] for p in pieces],
            'piece_names': [p['name'] for p in pieces],
            'piece_prices': piece_prices,
            'individual_pieces_total_cost': total_pieces_cost,
            'complete_set_price': set_price,
            'lazy_tax_profit': lazy_tax_profit,
            'margin_pct': round(margin_pct, 2),
            'piece_volumes': piece_volumes,
            'set_volume': set_volume if set_item_id else set_volume,
        }
    
    def _get_item_price(self, item_id: int) -> Optional[Dict]:
        """
        Get current price data for an item.
        
        Args:
            item_id: OSRS item ID
            
        Returns:
            Price data dictionary or None if not available
        """
        try:
            # Try to get from ProfitCalculation first (cached data)
            profit_calc = ProfitCalculation.objects.filter(item_id=item_id).first()
            if profit_calc and profit_calc.current_buy_price and profit_calc.current_sell_price:
                return {
                    'high': profit_calc.current_buy_price or 0,
                    'low': profit_calc.current_sell_price or 0,
                    'highTime': profit_calc.daily_volume or 0,
                    'lowTime': profit_calc.hourly_volume or 0,
                }
            
            # Fallback to latest PriceSnapshot
            price_obj = PriceSnapshot.objects.filter(item_id=item_id).order_by('-created_at').first()
            if not price_obj:
                return None
            
            return {
                'high': price_obj.high_price or 0,
                'low': price_obj.low_price or 0,
                'highTime': price_obj.high_price_volume or 0,
                'lowTime': price_obj.low_price_volume or 0,
            }
        except Exception as e:
            logger.warning(f"Error getting price for item {item_id}: {e}")
            return None
    
    @transaction.atomic
    def create_strategy_opportunities(self, opportunities: List[Dict]) -> int:
        """
        Create TradingStrategy and SetCombiningOpportunity records.
        
        Args:
            opportunities: List of opportunity dictionaries
            
        Returns:
            Number of strategies created
        """
        created_count = 0
        
        for opp in opportunities:
            try:
                lazy_tax_profit = opp['lazy_tax_profit']
                margin_pct = Decimal(str(opp['margin_pct']))
                
                # Calculate capital requirements
                min_capital = opp['individual_pieces_total_cost']
                recommended_capital = min_capital * 5  # Recommend 5 sets worth
                
                # Estimate time (buying pieces takes time, combining is instant)
                estimated_time_minutes = 15  # 15 minutes to buy all pieces and combine
                
                # Calculate confidence based on volume and margin
                min_piece_volume = min(opp['piece_volumes'].values()) if opp['piece_volumes'] else 0
                volume_score = min(1.0, min_piece_volume / 100)  # Based on minimum piece availability
                margin_score = min(1.0, opp['margin_pct'] / 50)  # Cap at 50% margin
                confidence = (volume_score * 0.7 + margin_score * 0.3)
                
                # Risk assessment
                if opp['margin_pct'] > 20 and volume_score > 0.3:
                    risk_level = 'low'
                elif opp['margin_pct'] > 10:
                    risk_level = 'medium'
                else:
                    risk_level = 'high'
                
                # Create or update strategy
                strategy, created = TradingStrategy.objects.get_or_create(
                    strategy_type=StrategyType.SET_COMBINING,
                    name=f"Combine {opp['set_name']}",
                    defaults={
                        'description': (
                            f"Buy individual {opp['set_name']} pieces for {opp['individual_pieces_total_cost']:,} GP, "
                            f"combine into complete set, sell for {opp['complete_set_price']:,} GP. "
                            f"Lazy tax profit: {lazy_tax_profit:,} GP ({opp['margin_pct']:.1f}% margin). "
                            f"Pieces: {', '.join(opp['piece_names'])}"
                        ),
                        'potential_profit_gp': lazy_tax_profit,
                        'profit_margin_pct': margin_pct,
                        'risk_level': risk_level,
                        'min_capital_required': min_capital,
                        'recommended_capital': recommended_capital,
                        'optimal_market_condition': 'stable',
                        'estimated_time_minutes': estimated_time_minutes,
                        'confidence_score': Decimal(str(confidence)),
                        'is_active': True,
                        'strategy_data': {
                            'set_type': opp['set_name'],
                            'piece_count': len(opp['piece_names']),
                            'has_official_set_item': opp['set_item_id'] is not None,
                        }
                    }
                )
                
                if not created:
                    # Update existing strategy
                    strategy.potential_profit_gp = lazy_tax_profit
                    strategy.profit_margin_pct = margin_pct
                    strategy.risk_level = risk_level
                    strategy.min_capital_required = min_capital
                    strategy.recommended_capital = recommended_capital
                    strategy.confidence_score = Decimal(str(confidence))
                    strategy.save()
                
                # Create or update set combining opportunity
                set_opp, _ = SetCombiningOpportunity.objects.update_or_create(
                    set_name=opp['set_name'],  # Use set_name as unique identifier
                    defaults={
                        'strategy': strategy,
                        'set_item_id': opp['set_item_id'] or 0,  # Store set_item_id but don't use for uniqueness
                        'piece_ids': opp['piece_ids'],
                        'piece_names': opp['piece_names'],
                        'individual_pieces_total_cost': opp['individual_pieces_total_cost'],
                        'complete_set_price': opp['complete_set_price'],
                        'lazy_tax_profit': lazy_tax_profit,
                        'piece_volumes': opp['piece_volumes'],
                        'set_volume': opp['set_volume'],
                    }
                )
                
                created_count += 1
                logger.info(f"Created set combining strategy: {strategy.name}")
                
            except Exception as e:
                logger.error(f"Error creating strategy for {opp['set_name']}: {e}")
        
        return created_count
    
    def scan_and_create_opportunities(self) -> int:
        """
        Full scan: analyze opportunities and create strategy records.
        
        Returns:
            Number of strategies created
        """
        logger.info("Starting set combining opportunity analysis...")
        
        opportunities = self.analyze_opportunities()
        logger.info(f"Found {len(opportunities)} set combining opportunities")
        
        if opportunities:
            created_count = self.create_strategy_opportunities(opportunities)
            logger.info(f"Created {created_count} set combining strategies")
            return created_count
        
        return 0