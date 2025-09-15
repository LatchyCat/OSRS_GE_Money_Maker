from typing import List, Dict, Optional
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.items.models import Item
from apps.trading_strategies.models import TradingStrategy, DecantingOpportunity, StrategyType
import logging
import re

logger = logging.getLogger(__name__)


class DecantingDetector:
    """
    Detects profitable potion decanting opportunities.
    
    Potion decanting involves converting higher-dose potions to lower doses
    and selling the extra doses for profit. For example:
    - Buy 4-dose combat potion for 1000 GP
    - Drink 1 dose to make it 3-dose
    - Sell 3-dose for 800 GP each (2400 GP total)
    - Profit: 2400 - 1000 = 1400 GP per conversion
    """
    
    # Common potion types that can be decanted
    POTION_MAPPING = {
        # Format: base_name -> {dose: item_id}
        'Combat potion': {
            4: 9739,  # Combat potion(4)
            3: 9741,  # Combat potion(3) 
            2: 9743,  # Combat potion(2)
            1: 9745,  # Combat potion(1)
        },
        'Prayer potion': {
            4: 2434,  # Prayer potion(4)
            3: 139,   # Prayer potion(3)
            2: 141,   # Prayer potion(2) 
            1: 143,   # Prayer potion(1)
        },
        'Super combat potion': {
            4: 12695, # Super combat potion(4)
            3: 12697, # Super combat potion(3)
            2: 12699, # Super combat potion(2)
            1: 12701, # Super combat potion(1)
        },
        'Ranging potion': {
            4: 2444,  # Ranging potion(4)
            3: 169,   # Ranging potion(3)
            2: 171,   # Ranging potion(2)
            1: 173,   # Ranging potion(1)
        },
        'Super strength': {
            4: 2440,  # Super strength(4)
            3: 157,   # Super strength(3)
            2: 159,   # Super strength(2)
            1: 161,   # Super strength(1)
        },
        'Super attack': {
            4: 2436,  # Super attack(4)
            3: 145,   # Super attack(3)
            2: 147,   # Super attack(2)
            1: 149,   # Super attack(1)
        },
        'Super defence': {
            4: 2442,  # Super defence(4)
            3: 163,   # Super defence(3)
            2: 165,   # Super defence(2)
            1: 167,   # Super defence(1)
        },
    }
    
    def __init__(self, min_profit_margin: float = 0.02, min_profit_gp: int = 50):
        """
        Initialize the decanting detector.
        
        Args:
            min_profit_margin: Minimum profit margin percentage (0.15 = 15%)
            min_profit_gp: Minimum profit in GP per conversion
        """
        self.min_profit_margin = min_profit_margin
        self.min_profit_gp = min_profit_gp
    
    def detect_opportunities(self) -> List[Dict]:
        """
        Scan for profitable decanting opportunities using market-driven discovery.
        
        Returns:
            List of opportunity dictionaries with profit data
        """
        opportunities = []
        
        # Step 1: Discover all potion families from market data
        potion_families = self._discover_potion_families_from_market()
        logger.info(f"Discovered {len(potion_families)} potion families from market data")
        
        # Step 2: Analyze each potion family for decanting opportunities
        for potion_name, dose_mapping in potion_families.items():
            for from_dose in [4, 3, 2]:  # We can only decant from higher to lower
                for to_dose in range(1, from_dose):  # Target all lower doses
                    if from_dose in dose_mapping and to_dose in dose_mapping:
                        try:
                            opportunity = self._analyze_decanting_pair(
                                potion_name, dose_mapping, from_dose, to_dose
                            )
                            if opportunity:
                                opportunities.append(opportunity)
                        except Exception as e:
                            logger.warning(f"Error analyzing {potion_name} {from_dose}->{to_dose}: {e}")
        
        # Sort by profit potential
        opportunities.sort(key=lambda x: x['profit_per_conversion'], reverse=True)
        
        logger.info(f"Found {len(opportunities)} profitable decanting opportunities")
        return opportunities
    
    def _discover_potion_families_from_market(self) -> Dict[str, Dict[int, int]]:
        """
        Discover potion families dynamically from items with active market data.
        
        Returns:
            Dictionary mapping potion names to dose mappings
            Format: {'Potion name': {4: item_id, 3: item_id, 2: item_id, 1: item_id}}
        """
        potion_families = {}
        
        # Get all items with recent price data that match potion patterns
        items_with_prices = ProfitCalculation.objects.filter(
            Q(current_buy_price__gt=0) | Q(current_sell_price__gt=0)
        ).select_related('item')
        
        # Pattern to match dose potions: "Potion name(X)" where X is 1-4
        dose_pattern = re.compile(r'^(.+?)\s*\((\d)\)$')
        
        logger.info(f"Analyzing {items_with_prices.count()} items for potion patterns...")
        
        for price_data in items_with_prices:
            item_name = price_data.item.name
            match = dose_pattern.match(item_name)
            
            if match:
                base_name = match.group(1).strip()
                dose_count = int(match.group(2))
                
                # Only consider doses 1-4
                if 1 <= dose_count <= 4:
                    # Filter for likely potions (exclude food, teleports, etc.)
                    if self._is_likely_potion(base_name, item_name):
                        if base_name not in potion_families:
                            potion_families[base_name] = {}
                        
                        potion_families[base_name][dose_count] = price_data.item.item_id
        
        # Filter out incomplete families (need at least 2 dose variants)
        complete_families = {
            name: doses for name, doses in potion_families.items() 
            if len(doses) >= 2
        }
        
        # Log discovered families for debugging
        for name, doses in complete_families.items():
            dose_list = sorted(doses.keys())
            logger.info(f"Discovered potion family: {name} with doses {dose_list}")
        
        return complete_families
    
    def _is_likely_potion(self, base_name: str, full_name: str) -> bool:
        """
        Determine if an item is likely a potion based on name patterns.
        
        Args:
            base_name: Base name without dose info (e.g., "Super strength")
            full_name: Full item name (e.g., "Super strength(4)")
        
        Returns:
            True if likely a potion, False otherwise
        """
        # Common potion keywords
        potion_keywords = [
            'potion', 'brew', 'elixir', 'tonic', 'mixture', 'serum',
            'super', 'combat', 'prayer', 'strength', 'attack', 'defence',
            'magic', 'ranging', 'fishing', 'hunter', 'agility', 'thieving',
            'slayer', 'antifire', 'poison', 'relicym', 'barbarian', 'overload',
            'antidote', 'restore', 'energy', 'stamina', 'antipoison'
        ]
        
        name_lower = base_name.lower()
        
        # Must contain at least one potion keyword
        if not any(keyword in name_lower for keyword in potion_keywords):
            return False
        
        # Exclude items that are clearly not potions
        exclusion_keywords = [
            'seed', 'ore', 'bar', 'log', 'plank', 'arrow', 'bolt', 'rune',
            'gem', 'crystal', 'tablet', 'scroll', 'book', 'key', 'coin',
            'food', 'fish', 'meat', 'cake', 'pie', 'bread', 'cheese',
            'teleport', 'tab', 'ring', 'amulet', 'weapon', 'sword', 'bow',
            'shield', 'armour', 'helmet', 'boots', 'gloves', 'cape'
        ]
        
        if any(keyword in name_lower for keyword in exclusion_keywords):
            return False
        
        return True
    
    def _analyze_decanting_pair(self, potion_name: str, dose_mapping: Dict[int, int], 
                               from_dose: int, to_dose: int) -> Optional[Dict]:
        """
        Analyze a specific decanting pair for profitability.
        
        Args:
            potion_name: Name of the potion type
            dose_mapping: Mapping of dose counts to item IDs
            from_dose: Source dose count
            to_dose: Target dose count
            
        Returns:
            Opportunity dictionary or None if not profitable
        """
        from_item_id = dose_mapping.get(from_dose)
        to_item_id = dose_mapping.get(to_dose)
        
        if not from_item_id or not to_item_id:
            return None
        
        # Get current prices
        from_price_data = self._get_item_price(from_item_id)
        to_price_data = self._get_item_price(to_item_id)
        
        if not from_price_data or not to_price_data:
            return None
        
        from_price = from_price_data['high']  # Price we buy at
        to_price = to_price_data['low']       # Price we sell at
        
        # Validate prices are realistic (potions shouldn't cost millions)
        max_reasonable_price = 50000  # 50k GP max for any potion dose
        min_reasonable_price = 5      # 5 GP minimum (allow low-value single doses)
        
        if (from_price > max_reasonable_price or from_price < min_reasonable_price or
            to_price > max_reasonable_price or to_price < min_reasonable_price):
            logger.warning(f"Skipping {potion_name} {from_dose}→{to_dose}: unrealistic prices "
                          f"(from: {from_price}, to: {to_price})")
            return None
        
        # Calculate conversion profit with GE tax consideration
        # Import GE tax calculator
        from services.weird_gloop_client import GrandExchangeTax
        
        # Calculate actual potions gained from decanting conversion
        # When decanting in OSRS:
        # - Drinking a 4-dose potion once gives you 3 doses worth of effect + 1 empty vial
        # - You can then split those 3 doses into separate potions (e.g., 1x 3-dose, or 1x 2-dose + 1x 1-dose)
        
        if from_dose == 4 and to_dose == 2:
            # 4-dose → drink once → split into 2x 2-dose potions  
            potions_gained = 2
        elif from_dose == 4 and to_dose == 3:
            # 4-dose → drink once → 1x 3-dose potion
            potions_gained = 1  
        elif from_dose == 4 and to_dose == 1:
            # 4-dose → drink once → split into 3x 1-dose potions
            potions_gained = 3
        elif from_dose == 3 and to_dose == 2:
            # 3-dose → drink once → 1x 2-dose potion
            potions_gained = 1
        elif from_dose == 3 and to_dose == 1:
            # 3-dose → drink once → split into 2x 1-dose potions  
            potions_gained = 2
        elif from_dose == 2 and to_dose == 1:
            # 2-dose → split directly → 2x 1-dose potions
            potions_gained = 2
        else:
            # Invalid or unsupported conversion
            return None
        
        # Calculate revenue after GE tax (we're selling)
        gross_revenue = to_price * potions_gained
        ge_tax = GrandExchangeTax.calculate_tax(to_price, to_item_id) * potions_gained
        net_revenue = gross_revenue - ge_tax
        
        cost = from_price  # We're buying, no tax
        profit_per_conversion = net_revenue - cost
        
        if profit_per_conversion < self.min_profit_gp:
            return None
        
        profit_margin = (profit_per_conversion / cost) * 100 if cost > 0 else 0
        
        if profit_margin < (self.min_profit_margin * 100):
            return None
        
        # Additional sanity check: reject opportunities with unrealistic profit margins
        # Real decanting profits are typically 5-100 GP per conversion, so margins over 1000% are likely data errors
        if profit_margin > 1000:  # 1000% maximum reasonable margin
            logger.warning(f"Skipping {potion_name} {from_dose}→{to_dose}: unrealistic profit margin "
                          f"({profit_margin:.1f}% with {profit_per_conversion:.0f} GP profit)")
            return None
        
        # Calculate volume constraints
        from_volume = from_price_data.get('highTime', 0) or 0
        to_volume = to_price_data.get('lowTime', 0) or 0
        
        # Calculate hourly profit potential (your friend's approach)
        # Assume 1000 potions per hour with Barbarian Herblore
        potions_per_hour = 1000
        hourly_profit = profit_per_conversion * potions_per_hour
        
        # Calculate capital efficiency  
        capital_required = from_price * 100  # Capital for 100 potions
        capital_efficiency = (hourly_profit / capital_required) if capital_required > 0 else 0
        
        return {
            'potion_name': potion_name,
            'from_dose': from_dose,
            'to_dose': to_dose,
            'from_item_id': from_item_id,
            'to_item_id': to_item_id,
            'from_dose_price': from_price,
            'to_dose_price': to_price,
            'profit_per_conversion': profit_per_conversion,
            'profit_margin_pct': round(profit_margin, 4),
            'from_dose_volume': from_volume,
            'to_dose_volume': to_volume,
            'potions_gained': potions_gained,
            'ge_tax_per_conversion': ge_tax,
            'net_revenue': net_revenue,
            'gross_revenue': gross_revenue,
            'hourly_profit_potential': hourly_profit,
            'capital_required_100_potions': capital_required,
            'capital_efficiency_ratio': capital_efficiency,
            'barbarian_herblore_required': True,  # Required for efficient decanting
        }
    
    def _get_item_price(self, item_id: int) -> Optional[Dict]:
        """
        Get current price data for an item from market sources.
        
        Args:
            item_id: OSRS item ID
            
        Returns:
            Price data dictionary or None if not available
        """
        try:
            # Try to get from ProfitCalculation first (most recent cached data)
            profit_calc = ProfitCalculation.objects.filter(item__item_id=item_id).first()
            if profit_calc and (profit_calc.current_buy_price or profit_calc.current_sell_price):
                buy_price = profit_calc.current_buy_price or 0
                sell_price = profit_calc.current_sell_price or 0
                
                # VOLUME VALIDATION: Ensure realistic volume data
                daily_volume = self._validate_volume(profit_calc.daily_volume, "daily")
                hourly_volume = self._validate_volume(profit_calc.hourly_volume, "hourly")
                
                # If both volumes are 0, estimate from volume category
                if daily_volume == 0 and hourly_volume == 0:
                    daily_volume, hourly_volume = self._estimate_volume_from_category(profit_calc.volume_category)
                
                logger.debug(f"Item {item_id} volume data: daily={daily_volume}, hourly={hourly_volume}, category={profit_calc.volume_category}")
                
                # Correct price mapping: current_buy_price is what we pay (high), current_sell_price is what we receive (low)
                return {
                    'high': buy_price,   # What we pay to buy instantly (current_buy_price)
                    'low': sell_price,   # What we receive when selling instantly (current_sell_price)
                    'highTime': daily_volume,
                    'lowTime': hourly_volume,
                }
            
            # Fallback to latest PriceSnapshot
            price_obj = PriceSnapshot.objects.filter(item_id=item_id).order_by('-created_at').first()
            if not price_obj:
                return None
            
            # Validate snapshot volumes
            high_volume = self._validate_volume(price_obj.high_price_volume, "price_volume")
            low_volume = self._validate_volume(price_obj.low_price_volume, "price_volume")
            
            return {
                'high': price_obj.high_price or 0,
                'low': price_obj.low_price or 0,
                'highTime': high_volume,
                'lowTime': low_volume,
            }
        except Exception as e:
            logger.warning(f"Error getting price for item {item_id}: {e}")
            return None
    
    def _validate_volume(self, volume: int, volume_type: str) -> int:
        """
        Validate and sanitize volume data to ensure realistic values.
        
        Args:
            volume: Raw volume value
            volume_type: Type of volume for context (daily, hourly, price_volume)
            
        Returns:
            Validated volume value (minimum 0, maximum reasonable limits)
        """
        if volume is None or volume < 0:
            return 0
        
        # Set reasonable upper limits to prevent data corruption issues
        max_limits = {
            "daily": 1000000,    # 1M daily trades max
            "hourly": 50000,     # 50K hourly trades max  
            "price_volume": 10000,  # 10K volume snapshots max
        }
        
        max_volume = max_limits.get(volume_type, 100000)
        
        if volume > max_volume:
            logger.warning(f"Volume {volume} exceeds reasonable limit for {volume_type}, capping at {max_volume}")
            return max_volume
            
        return volume
    
    def _estimate_volume_from_category(self, volume_category: str) -> tuple[int, int]:
        """
        Estimate realistic volume values based on volume category.
        
        Args:
            volume_category: Volume category (hot, warm, cool, cold, inactive)
            
        Returns:
            Tuple of (daily_volume, hourly_volume) estimates
        """
        volume_estimates = {
            'hot': (5000, 200),      # High volume items
            'warm': (1500, 60),      # Medium volume items  
            'cool': (500, 20),       # Low volume items
            'cold': (100, 5),        # Very low volume items
            'inactive': (10, 1),     # Barely traded items
        }
        
        return volume_estimates.get(volume_category, (100, 5))  # Default to 'cold' estimates
    
    @transaction.atomic
    def create_strategy_opportunities(self, opportunities: List[Dict]) -> int:
        """
        Create TradingStrategy and DecantingOpportunity records from detected opportunities.
        
        Args:
            opportunities: List of opportunity dictionaries
            
        Returns:
            Number of strategies created
        """
        created_count = 0
        
        for opp in opportunities:
            try:
                # Get item names
                from_item = Item.objects.filter(id=opp['from_item_id']).first()
                to_item = Item.objects.filter(id=opp['to_item_id']).first()
                
                if not from_item or not to_item:
                    continue
                
                # Calculate strategy metrics
                profit_gp = opp['profit_per_conversion']
                
                # Cap profit margin to prevent decimal overflow (max 999.9999%)
                raw_margin = opp['profit_margin_pct']
                profit_margin_pct = Decimal(str(min(raw_margin, 999.9999)))
                
                # Estimate capital requirements
                min_capital = opp['from_dose_price'] * 10  # Start with 10 potions
                recommended_capital = opp['from_dose_price'] * 100  # Recommend 100 potions
                
                # Estimate time (decanting is very fast, ~30 seconds per potion)
                estimated_time_minutes = 1
                
                # Calculate confidence based on volume and margin
                volume_score = min(1.0, (opp['from_dose_volume'] + opp['to_dose_volume']) / 1000)
                margin_score = min(1.0, opp['profit_margin_pct'] / 100)
                confidence = round((volume_score * 0.6 + margin_score * 0.4), 3)
                
                # Risk assessment based on margin and volume
                if opp['profit_margin_pct'] > 50 and volume_score > 0.5:
                    risk_level = 'low'
                elif opp['profit_margin_pct'] > 25:
                    risk_level = 'medium'
                else:
                    risk_level = 'high'
                
                # Create or update strategy
                strategy, created = TradingStrategy.objects.get_or_create(
                    strategy_type=StrategyType.DECANTING,
                    name=f"Decant {opp['potion_name']} ({opp['from_dose']}→{opp['to_dose']})",
                    defaults={
                        'description': (
                            f"Buy {opp['potion_name']}({opp['from_dose']}) for {opp['from_dose_price']} GP, "
                            f"drink to ({opp['to_dose']}) doses, sell for {opp['to_dose_price']} GP each. "
                            f"Profit: {profit_gp} GP per conversion ({opp['profit_margin_pct']:.1f}% margin)."
                        ),
                        'potential_profit_gp': profit_gp,
                        'profit_margin_pct': round(float(profit_margin_pct), 4),
                        'risk_level': risk_level,
                        'min_capital_required': min_capital,
                        'recommended_capital': recommended_capital,
                        'optimal_market_condition': 'stable',  # Decanting works in stable markets
                        'estimated_time_minutes': estimated_time_minutes,
                        'confidence_score': Decimal(str(confidence)),
                        'is_active': True,
                        'strategy_data': {
                            'potion_type': opp['potion_name'],
                            'conversion_ratio': f"{opp['from_dose']}→{opp['to_dose']}",
                            'potions_gained': opp['potions_gained'],
                        }
                    }
                )
                
                if not created:
                    # Update existing strategy with new data
                    strategy.potential_profit_gp = profit_gp
                    strategy.profit_margin_pct = profit_margin_pct
                    strategy.risk_level = risk_level
                    strategy.min_capital_required = min_capital
                    strategy.recommended_capital = recommended_capital
                    strategy.confidence_score = Decimal(str(confidence))
                    strategy.save()
                
                # Calculate profit per hour
                profit_per_hour = opp['hourly_profit_potential']
                
                # Create or update decanting opportunity
                decanting_opp, _ = DecantingOpportunity.objects.update_or_create(
                    item_id=opp['from_item_id'],
                    from_dose=opp['from_dose'],
                    to_dose=opp['to_dose'],
                    defaults={
                        'strategy': strategy,
                        'item_name': opp['potion_name'],
                        'from_dose_price': opp['from_dose_price'],
                        'to_dose_price': opp['to_dose_price'],
                        'from_dose_volume': opp['from_dose_volume'],
                        'to_dose_volume': opp['to_dose_volume'],
                        'profit_per_conversion': profit_gp,
                        'profit_per_hour': profit_per_hour,
                    }
                )
                
                created_count += 1
                logger.info(f"Created decanting strategy: {strategy.name}")
                
            except Exception as e:
                logger.error(f"Error creating strategy for {opp}: {e}")
        
        return created_count
    
    def scan_and_create_opportunities(self) -> int:
        """
        Full scan: detect opportunities and create strategy records.
        
        Returns:
            Number of strategies created
        """
        logger.info("Starting decanting opportunity scan...")
        
        opportunities = self.detect_opportunities()
        logger.info(f"Found {len(opportunities)} decanting opportunities")
        
        if opportunities:
            created_count = self.create_strategy_opportunities(opportunities)
            logger.info(f"Created {created_count} decanting strategies")
            return created_count
        
        return 0