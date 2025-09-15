"""
Fresh price service for decanting analysis using RuneScape Wiki API exclusively.

This service provides real-time decanting opportunities using comprehensive 
price and volume data from the official RuneScape Wiki API.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from django.utils import timezone
from django.core.cache import cache

from .unified_wiki_price_client import UnifiedPriceClient
from .runescape_wiki_client import RuneScapeWikiAPIError
from apps.items.models import Item

logger = logging.getLogger(__name__)


class PotionType(Enum):
    """Categories of potions for decanting analysis."""
    COMBAT = "combat"
    PRAYER = "prayer" 
    SKILL_BOOST = "skill_boost"
    POISON_CURE = "poison_cure"
    SPECIAL = "special"
    MIX = "mix"  # Barbarian mixes (2-dose max)


@dataclass
class PotionFamily:
    """Represents a family of potions (1-4 doses)."""
    base_name: str
    potion_type: PotionType
    item_ids: Dict[int, int]  # dose -> item_id mapping
    current_prices: Dict[int, Dict[str, int]]  # dose -> {high, low} prices
    volumes: Dict[int, int]  # dose -> volume data
    last_updated: datetime
    data_quality: str  # fresh, recent, stale
    
    @property
    def has_complete_data(self) -> bool:
        """Check if family has price data for all available doses."""
        return all(
            dose in self.current_prices and 
            self.current_prices[dose].get('high', 0) > 0
            for dose in self.item_ids.keys()
        )


@dataclass
class DecantingOpportunity:
    """Represents a potential decanting opportunity with AI confidence."""
    potion_family: PotionFamily
    from_dose: int
    to_dose: int
    from_price: int
    to_price: int
    profit_per_conversion: int
    profit_margin_pct: float
    volume_score: float  # 0-1 based on trading volume
    confidence_score: float  # AI confidence in opportunity
    risk_level: str
    estimated_conversions_per_hour: int


class DecantingPriceService:
    """
    Real-time price service for decanting analysis using WeirdGloop API.
    
    Mirrors the successful high-alchemy approach:
    1. Fresh WeirdGloop data only
    2. Hourly refresh cycles  
    3. Data quality validation
    4. Real market conditions
    """
    
    def __init__(self):
        self.price_client = UnifiedPriceClient()
        self.cache_timeout = 3600  # 1 hour cache
        self.max_data_age_hours = 24  # Reject data older than 24h
        
        # High-value potion item IDs to ensure they're always included
        self.high_value_potion_ids = {
            # Prayer potions (4-dose, 3-dose, 2-dose, 1-dose)
            2434: "Prayer potion", 139: "Prayer potion", 141: "Prayer potion", 143: "Prayer potion",
            # Super restore potions 
            3024: "Super restore", 3026: "Super restore", 3028: "Super restore", 3030: "Super restore",
            # Divine super combat potions
            23685: "Divine super combat potion", 23688: "Divine super combat potion", 
            23691: "Divine super combat potion", 23694: "Divine super combat potion",
            # Divine ranging potions
            23733: "Divine ranging potion", 23736: "Divine ranging potion",
            23739: "Divine ranging potion", 23742: "Divine ranging potion", 
            # Divine magic potions
            23757: "Divine magic potion", 23760: "Divine magic potion",
            23763: "Divine magic potion", 23766: "Divine magic potion",
            # Saradomin brews
            6685: "Saradomin brew", 6687: "Saradomin brew", 6689: "Saradomin brew", 6691: "Saradomin brew",
            # Extended antifire potions
            11951: "Extended antifire", 11953: "Extended antifire", 11955: "Extended antifire", 11957: "Extended antifire",
            # Stamina potions
            12625: "Stamina potion", 12627: "Stamina potion", 12629: "Stamina potion", 12631: "Stamina potion",
        }
        
        # Potion patterns for automatic family discovery
        self.potion_patterns = {
            PotionType.COMBAT: [
                'attack', 'strength', 'defence', 'combat', 'super combat',
                'super attack', 'super strength', 'super defence',
                'ranging', 'magic potion'
            ],
            PotionType.PRAYER: ['prayer', 'super restore'],
            PotionType.SKILL_BOOST: [
                'agility', 'fishing', 'hunter', 'energy', 'super energy',
                'stamina', 'extended antifire', 'antifire'
            ],
            PotionType.POISON_CURE: [
                'antipoison', 'superantipoison', 'antidote+', 'antidote++',
                'sanfew serum'
            ],
            PotionType.MIX: [
                'mix'  # All barbarian mixes
            ],
            PotionType.SPECIAL: [
                'zamorak brew', 'saradomin brew', 'battlemage', 'bastion',
                'divine'
            ]
        }
    
    async def refresh_potion_prices(self, force_refresh: bool = False) -> Dict[str, PotionFamily]:
        """
        Refresh prices for all potion families using WeirdGloop API.
        
        Args:
            force_refresh: Skip cache and fetch fresh data
            
        Returns:
            Dictionary of potion families with fresh price data
        """
        cache_key = "decanting:potion_families"
        
        if not force_refresh:
            cached_families = cache.get(cache_key)
            if cached_families:
                logger.info("Using cached potion family data")
                return cached_families
        
        logger.info("Refreshing potion prices from WeirdGloop API")
        
        # Discover all potion families
        potion_families = await self._discover_potion_families()
        
        # Fetch fresh prices for all potion items
        all_item_ids = []
        for family_name, family in potion_families.items():
            family_item_ids = list(family.item_ids.values())
            all_item_ids.extend(family_item_ids)
            logger.info(f"Family '{family_name}' has {len(family_item_ids)} item IDs: {family_item_ids}")
        
        logger.info(f"Collected {len(all_item_ids)} total item IDs for price fetching: {all_item_ids[:10]}...")
        
        if not all_item_ids:
            logger.warning("No potion items found for price refresh")
            return {}
        
        # Get fresh prices from WeirdGloop
        try:
            price_data = await self.price_client.get_multiple_comprehensive_prices(
                item_ids=all_item_ids,
                max_staleness_hours=self.max_data_age_hours
            )
            
            logger.info(f"Retrieved fresh prices for {len(price_data)} potion items")
            
            # Update families with fresh price data
            updated_families = await self._update_families_with_prices(
                potion_families, price_data
            )
            
            # Cache updated families
            cache.set(cache_key, updated_families, self.cache_timeout)
            
            return updated_families
            
        except Exception as e:
            logger.error(f"Failed to refresh potion prices: {e}")
            raise
    
    async def _discover_potion_families(self) -> Dict[str, PotionFamily]:
        """
        Discover potion families by analyzing item names and patterns.
        
        Returns:
            Dictionary of discovered potion families
        """
        # Get all items that match potion patterns
        potion_items = await self._get_potion_items()
        
        families = {}
        
        for item in potion_items:
            family_name = self._extract_family_name(item.name)
            if not family_name:
                continue
            
            dose = self._extract_dose_count(item.name)
            if dose is None:
                continue
                
            potion_type = self._classify_potion_type(item.name)
            
            # Create or update family
            if family_name not in families:
                families[family_name] = PotionFamily(
                    base_name=family_name,
                    potion_type=potion_type,
                    item_ids={},
                    current_prices={},
                    volumes={},
                    last_updated=timezone.now(),
                    data_quality="unknown"
                )
            
            families[family_name].item_ids[dose] = item.item_id
        
        # Add high-value potions that might be missing from database due to corruption
        logger.info(f"Processing {len(self.high_value_potion_ids)} high-value potions")
        for item_id, potion_name in self.high_value_potion_ids.items():
            dose = self._extract_dose_count_from_name(potion_name, item_id)
            family_name = self._extract_family_name_from_manual(potion_name)
            logger.info(f"Item {item_id} ({potion_name}) -> family='{family_name}', dose={dose}")
            
            if family_name and dose and family_name not in families:
                logger.info(f"Creating new family '{family_name}' for {potion_name}")
                families[family_name] = PotionFamily(
                    base_name=family_name,
                    potion_type=self._classify_potion_type(potion_name),
                    item_ids={},
                    current_prices={},
                    volumes={},
                    last_updated=timezone.now(),
                    data_quality="unknown"
                )
            
            if family_name and dose and family_name in families:
                logger.info(f"Adding item {item_id} (dose {dose}) to family '{family_name}'")
                families[family_name].item_ids[dose] = item_id
            else:
                logger.warning(f"Failed to add item {item_id} ({potion_name}): family_name='{family_name}', dose={dose}")
        
        logger.info(f"Discovered {len(families)} potion families (including {len(self.high_value_potion_ids)} high-value items)")
        return families
    
    async def _get_potion_items(self) -> List[Item]:
        """Get all items that appear to be potions."""
        # Look for items with dose indicators (1), (2), (3), (4)
        dose_pattern_items = await asyncio.to_thread(
            lambda: list(Item.objects.filter(
                name__regex=r'.*\([1-4]\).*'
            ).values('item_id', 'name'))
        )
        
        # Convert to Item objects
        return [Item(item_id=item['item_id'], name=item['name']) for item in dose_pattern_items]
    
    def _extract_family_name(self, item_name: str) -> Optional[str]:
        """Extract the base potion name without dose information."""
        # Remove dose indicators like (1), (2), (3), (4)
        import re
        base_name = re.sub(r'\s*\([1-4]\)\s*', '', item_name).strip()
        
        # Only return if it looks like a potion
        if any(keyword in base_name.lower() for pattern_list in self.potion_patterns.values() for keyword in pattern_list):
            return base_name
        
        return None
    
    def _extract_dose_count(self, item_name: str) -> Optional[int]:
        """Extract dose count from item name."""
        import re
        match = re.search(r'\(([1-4])\)', item_name)
        return int(match.group(1)) if match else None
    
    def _classify_potion_type(self, item_name: str) -> PotionType:
        """Classify potion into a type category."""
        name_lower = item_name.lower()
        
        for potion_type, keywords in self.potion_patterns.items():
            if any(keyword in name_lower for keyword in keywords):
                return potion_type
        
        return PotionType.SPECIAL  # Default fallback
    
    def _extract_dose_count_from_name(self, potion_name: str, item_id: int) -> Optional[int]:
        """Extract dose count from manual potion mapping based on item ID patterns."""
        # Common patterns for OSRS item IDs:
        # Prayer potions: 2434(4), 139(3), 141(2), 143(1)
        # Super restore: 3024(4), 3026(3), 3028(2), 3030(1)
        # Divine super combat: 23685(4), 23688(3), 23691(2), 23694(1)
        
        # Extract pattern from similar known potions
        prayer_pattern = [2434, 139, 141, 143]
        restore_pattern = [3024, 3026, 3028, 3030]
        div_combat_pattern = [23685, 23688, 23691, 23694]
        div_ranging_pattern = [23733, 23736, 23739, 23742]
        div_magic_pattern = [23757, 23760, 23763, 23766]
        sara_brew_pattern = [6685, 6687, 6689, 6691]
        ext_antifire_pattern = [11951, 11953, 11955, 11957]
        stamina_pattern = [12625, 12627, 12629, 12631]
        
        all_patterns = [
            prayer_pattern, restore_pattern, div_combat_pattern,
            div_ranging_pattern, div_magic_pattern, sara_brew_pattern,
            ext_antifire_pattern, stamina_pattern
        ]
        
        for pattern in all_patterns:
            if item_id in pattern:
                return 4 - pattern.index(item_id)  # 4-dose, 3-dose, 2-dose, 1-dose
        
        # Fallback: try to extract from name if it has (N) pattern
        return self._extract_dose_count(potion_name)
    
    def _extract_family_name_from_manual(self, potion_name: str) -> Optional[str]:
        """Extract family name from manual potion names."""
        # Remove common dose indicators and variations
        import re
        base_name = re.sub(r'\s*\([1-4]\)\s*', '', potion_name).strip()
        
        # Clean up common variations
        base_name = re.sub(r'\s+potion$', '', base_name, flags=re.IGNORECASE)
        base_name = re.sub(r'\s+brew$', '', base_name, flags=re.IGNORECASE)
        
        return base_name if base_name else None
    
    async def _update_families_with_prices(
        self, 
        families: Dict[str, PotionFamily], 
        price_data: Dict[int, Dict]
    ) -> Dict[str, PotionFamily]:
        """
        Update potion families with fresh price data from WeirdGloop.
        
        Args:
            families: Discovered potion families
            price_data: Fresh price data from WeirdGloop API
            
        Returns:
            Updated families with current prices
        """
        current_time = timezone.now()
        
        for family_name, family in families.items():
            family.current_prices = {}
            family.volumes = {}
            
            for dose, item_id in family.item_ids.items():
                if item_id in price_data:
                    price_info = price_data[item_id]
                    
                    # WeirdGloop API returns a single 'price' field, not separate high/low
                    price = price_info.get('price', 0)
                    
                    family.current_prices[dose] = {
                        'high': price,
                        'low': price  # Use same price for both high and low
                    }
                    
                    # WeirdGloop doesn't provide volume data, use a default
                    family.volumes[dose] = price_info.get('volume', 100)
                    
                    # Assess data quality based on timestamp
                    if 'timestamp' in price_info:
                        data_age = current_time - price_info['timestamp']
                        if data_age.total_seconds() < 3600:  # < 1 hour
                            family.data_quality = "fresh"
                        elif data_age.total_seconds() < 21600:  # < 6 hours  
                            family.data_quality = "recent"
                        elif data_age.total_seconds() < 86400:  # < 24 hours
                            family.data_quality = "acceptable"
                        else:
                            family.data_quality = "stale"
                    else:
                        family.data_quality = "unknown"
            
            family.last_updated = current_time
        
        # Filter out families without sufficient price data
        valid_families = {
            name: family for name, family in families.items()
            if family.has_complete_data and family.data_quality != "stale"
        }
        
        logger.info(f"Updated {len(valid_families)} families with fresh price data")
        return valid_families
    
    async def get_decanting_opportunities(self, min_profit_gp: int = 1) -> List[DecantingOpportunity]:
        """
        Get real decanting opportunities using fresh WeirdGloop price data.
        
        Args:
            min_profit_gp: Minimum profit in GP to consider
            
        Returns:
            List of viable decanting opportunities with AI confidence scores
        """
        # Get fresh potion families data
        families = await self.refresh_potion_prices()
        
        opportunities = []
        
        for family_name, family in families.items():
            if not family.has_complete_data:
                continue
            
            # Analyze all possible decanting combinations
            for from_dose in sorted(family.item_ids.keys(), reverse=True):
                for to_dose in sorted(family.item_ids.keys()):
                    if from_dose <= to_dose:
                        continue  # Can only decant to lower doses
                    
                    opportunity = await self._analyze_decanting_pair(
                        family, from_dose, to_dose, min_profit_gp
                    )
                    
                    if opportunity:
                        opportunities.append(opportunity)
        
        # Sort by multiple criteria to prioritize high-value potions:
        # 1. Profit margin % (higher is better for % returns)
        # 2. Potion value (higher base price = more valuable potion) 
        # 3. Absolute profit (tiebreaker for similar margin/value)
        opportunities.sort(
            key=lambda x: (
                x.profit_margin_pct,      # Percentage return
                x.from_price,             # Potion value (expensive potions first)  
                x.profit_per_conversion   # Absolute profit as tiebreaker
            ), 
            reverse=True
        )
        
        logger.info(f"Found {len(opportunities)} viable decanting opportunities")
        return opportunities
    
    async def _analyze_decanting_pair(
        self, 
        family: PotionFamily, 
        from_dose: int, 
        to_dose: int,
        min_profit_gp: int
    ) -> Optional[DecantingOpportunity]:
        """
        Analyze a specific decanting pair for profitability.
        
        Args:
            family: Potion family data
            from_dose: Source dose count
            to_dose: Target dose count  
            min_profit_gp: Minimum profit threshold
            
        Returns:
            DecantingOpportunity if profitable, None otherwise
        """
        if from_dose not in family.current_prices or to_dose not in family.current_prices:
            return None
        
        from_prices = family.current_prices[from_dose]
        to_prices = family.current_prices[to_dose]
        
        # Use high price for buying, low price for selling (realistic GE trading)
        from_price = from_prices['high']  # Price to buy the source potion
        to_price = to_prices['low']       # Price to sell target potions
        
        if from_price <= 0 or to_price <= 0:
            return None
        
        # Filter out very cheap potions (less than 100gp) to focus on valuable ones
        if from_price < 100:
            return None
        
        # Calculate decanting conversion (drinking reduces dose by 1)
        # from_dose potion -> drink once -> (from_dose-1) doses remaining
        # Those remaining doses can be split into target potions
        remaining_doses = from_dose - 1
        target_potions_created = remaining_doses // to_dose
        
        if target_potions_created <= 0:
            return None
        
        # Calculate profit
        revenue = target_potions_created * to_price
        cost = from_price
        profit_per_conversion = revenue - cost
        
        if profit_per_conversion < min_profit_gp:
            return None
        
        # Calculate metrics
        profit_margin_pct = (profit_per_conversion / from_price) * 100 if from_price > 0 else 0
        
        # Volume scoring based on trading activity
        from_volume = family.volumes.get(from_dose, 0)
        to_volume = family.volumes.get(to_dose, 0)
        volume_score = min(1.0, min(from_volume, to_volume) / 100.0)  # Normalize to 0-1
        
        # Basic confidence scoring (will be enhanced with AI in Phase 2)
        confidence_factors = []
        
        # Data quality factor
        if family.data_quality == "fresh":
            confidence_factors.append(0.9)
        elif family.data_quality == "recent":
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        # Volume factor
        confidence_factors.append(volume_score)
        
        # Profit margin factor
        if profit_margin_pct >= 50:
            confidence_factors.append(0.9)
        elif profit_margin_pct >= 20:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        confidence_score = sum(confidence_factors) / len(confidence_factors)
        
        # Risk assessment
        if profit_margin_pct >= 50 and volume_score >= 0.5:
            risk_level = "low"
        elif profit_margin_pct >= 20 and volume_score >= 0.3:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        # Estimate conversions per hour (conservative estimate)
        base_conversions = 60  # 1 per minute base rate
        efficiency_multiplier = min(1.5, volume_score + 0.5)  # Volume affects efficiency
        estimated_conversions_per_hour = int(base_conversions * efficiency_multiplier)
        
        return DecantingOpportunity(
            potion_family=family,
            from_dose=from_dose,
            to_dose=to_dose,
            from_price=from_price,
            to_price=to_price,
            profit_per_conversion=profit_per_conversion,
            profit_margin_pct=profit_margin_pct,
            volume_score=volume_score,
            confidence_score=confidence_score,
            risk_level=risk_level,
            estimated_conversions_per_hour=estimated_conversions_per_hour
        )


# Singleton instance for the application
decanting_price_service = DecantingPriceService()