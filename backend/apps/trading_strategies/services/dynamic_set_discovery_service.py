"""
Dynamic Set Discovery Service for OSRS Trading

This service dynamically discovers all armor/weapon sets from OSRS Wiki data
and creates bidirectional trading strategies (combine vs decombine).
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from services.unified_data_ingestion_service import UnifiedDataIngestionService
from services.runescape_wiki_client import RuneScapeWikiAPIClient
from apps.items.models import Item
from apps.prices.models import PriceSnapshot, HistoricalPricePoint
from apps.trading_strategies.models import TradingStrategy, SetCombiningOpportunity, StrategyType

logger = logging.getLogger(__name__)


class SetType(Enum):
    """Types of armor/weapon sets detected."""
    BARROWS = "barrows"
    METAL_ARMOR = "metal_armor"  # Bronze, Iron, Steel, etc.
    DRAGONHIDE = "dragonhide"
    GOD_ARMOR = "god_armor"
    MYSTIC_ROBES = "mystic_robes"
    TRIMMED_ARMOR = "trimmed_armor"
    GILDED_ARMOR = "gilded_armor"
    HIGH_VALUE = "high_value"  # Torva, Virtus, Masori, etc.
    SPECIALTY = "specialty"    # Void, Fighter, etc.
    UNKNOWN = "unknown"


class TradingStrategy(Enum):
    """Trading strategies for sets."""
    COMBINE = "combine"        # Buy pieces, sell set
    DECOMBINE = "decombine"    # Buy set, sell pieces  
    BOTH = "both"             # Both strategies viable
    NONE = "none"             # No viable strategy


@dataclass
class SetConfiguration:
    """Configuration for a detected armor/weapon set."""
    set_name: str
    set_type: SetType
    set_item_id: Optional[int] = None
    component_ids: List[int] = field(default_factory=list)
    component_names: List[str] = field(default_factory=list)
    
    # Market data
    set_price: Optional[float] = None
    components_total_price: Optional[float] = None
    set_volume: Optional[int] = None
    components_volumes: List[int] = field(default_factory=list)
    
    # Historical analysis
    price_history_available: bool = False
    volatility_score: Optional[float] = None
    
    # Trading analysis
    optimal_strategy: TradingStrategy = TradingStrategy.NONE
    combine_profit: Optional[float] = None
    decombine_profit: Optional[float] = None
    confidence_score: Optional[float] = None
    
    # Metadata
    discovered_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def is_profitable(self) -> bool:
        """Check if any strategy is profitable."""
        return (self.combine_profit and self.combine_profit > 0) or \
               (self.decombine_profit and self.decombine_profit > 0)
    
    @property
    def best_profit(self) -> Optional[float]:
        """Get the highest profit from available strategies."""
        profits = [p for p in [self.combine_profit, self.decombine_profit] if p is not None]
        return max(profits) if profits else None
    
    @property
    def risk_level(self) -> str:
        """Calculate risk level based on volatility and volume."""
        if not self.volatility_score or not self.confidence_score:
            return 'high'
        
        if self.volatility_score < 0.1 and self.confidence_score > 0.8:
            return 'low'
        elif self.volatility_score < 0.3 and self.confidence_score > 0.6:
            return 'medium'
        else:
            return 'high'


class DynamicSetDiscoveryService:
    """
    Service for dynamically discovering and analyzing OSRS armor/weapon sets.
    """
    
    def __init__(self):
        self.ingestion_service = None
        self.wiki_client = None
        
        # Set detection patterns
        self.set_patterns = {
            SetType.BARROWS: [
                r"(.+)'s armour set$",
                r"(Ahrim|Dharok|Guthan|Karil|Torag|Verac)'s set$"
            ],
            SetType.METAL_ARMOR: [
                r"(Bronze|Iron|Steel|Black|Mithril|Adamant|Rune|Dragon) (?:armour )?set \((lg|sk)\)$",
                r"(Bronze|Iron|Steel|Black|Mithril|Adamant|Rune|Dragon) set$"
            ],
            SetType.DRAGONHIDE: [
                r"(Green|Blue|Red|Black|White) dragonhide set$",
                r"(Guthix|Saradomin|Zamorak|Ancient|Armadyl|Bandos) dragonhide set$"
            ],
            SetType.GOD_ARMOR: [
                r"(Guthix|Saradomin|Zamorak|Ancient|Armadyl|Bandos) (?:armour|rune armour) set \((lg|sk)\)$"
            ],
            SetType.MYSTIC_ROBES: [
                r"Mystic set \((blue|light|dark|dusk)\)$"
            ],
            SetType.TRIMMED_ARMOR: [
                r"(Bronze|Iron|Steel|Black|Mithril|Adamant|Rune) (?:trimmed|gold-trimmed) set \((lg|sk)\)$"
            ],
            SetType.GILDED_ARMOR: [
                r"Gilded (?:armour|dragonhide) set \((lg|sk)\)$"
            ],
            SetType.HIGH_VALUE: [
                r"(Ancestral robes|Inquisitor's armour|Justiciar armour|Torva armour|Virtus armour|Masori armour) set( \([^\)]+\))?$"
            ]
        }
        
        # Component naming patterns
        self.component_patterns = {
            SetType.BARROWS: {
                'helm': r"(.+)'s (?:helm|hood|coif)(?:\s+0)?$",
                'body': r"(.+)'s (?:platebody|robetop|leathertop|brassard)(?:\s+0)?$",
                'legs': r"(.+)'s (?:platelegs|robeskirt|leatherskirt|chainskirt|plateskirt)(?:\s+0)?$",
                'weapon': r"(.+)'s (?:greataxe|staff|crossbow|hammers|flail|warspear)(?:\s+0)?$"
            },
            SetType.METAL_ARMOR: {
                'full_helm': r"(Bronze|Iron|Steel|Black|Mithril|Adamant|Rune|Dragon) full helm$",
                'platebody': r"(Bronze|Iron|Steel|Black|Mithril|Adamant|Rune|Dragon) platebody$",
                'platelegs': r"(Bronze|Iron|Steel|Black|Mithril|Adamant|Rune|Dragon) plate(?:legs|skirt)$"
            },
            SetType.DRAGONHIDE: {
                'body': r"(Green|Blue|Red|Black|White|Guthix|Saradomin|Zamorak|Ancient|Armadyl|Bandos) d'hide body$",
                'chaps': r"(Green|Blue|Red|Black|White|Guthix|Saradomin|Zamorak|Ancient|Armadyl|Bandos) d'hide chaps$",
                'vambraces': r"(Green|Blue|Red|Black|White|Guthix|Saradomin|Zamorak|Ancient|Armadyl|Bandos) d'hide vambraces$"
            }
        }
        
        # Cache configuration
        self.cache_timeout = 3600  # 1 hour
        self.discovered_sets_cache_key = 'dynamic_set_discovery:sets'
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.ingestion_service = UnifiedDataIngestionService()
        self.wiki_client = RuneScapeWikiAPIClient()
        
        await self.ingestion_service.__aenter__()
        await self.wiki_client.__aenter__()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.ingestion_service:
            await self.ingestion_service.__aexit__(exc_type, exc_val, exc_tb)
        if self.wiki_client:
            await self.wiki_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def discover_all_sets(self, 
                              force_refresh: bool = False,
                              include_historical: bool = True) -> List[SetConfiguration]:
        """
        Discover all armor/weapon sets from OSRS Wiki data.
        
        Args:
            force_refresh: Whether to bypass cache and rediscover sets
            include_historical: Whether to include historical price analysis
            
        Returns:
            List of discovered set configurations
        """
        logger.info("🔍 Starting dynamic set discovery...")
        
        # Check cache first
        if not force_refresh:
            cached_sets = cache.get(self.discovered_sets_cache_key)
            if cached_sets:
                logger.info(f"📋 Using cached set discovery data ({len(cached_sets)} sets)")
                return cached_sets
        
        try:
            # Get all item metadata from ingestion service
            logger.info("📊 Fetching complete item metadata...")
            
            # Use the unified ingestion service to get all item data
            ingestion_results = await self.ingestion_service.ingest_complete_market_data(
                include_historical=include_historical
            )
            
            if ingestion_results['status'] != 'completed':
                raise Exception(f"Data ingestion failed: {ingestion_results.get('error', 'Unknown error')}")
            
            # Get item data from database (now populated by ingestion)
            all_items = await asyncio.to_thread(self._get_all_items_from_db)
            logger.info(f"📦 Analyzing {len(all_items)} items for set patterns...")
            
            # Discover sets using pattern matching
            discovered_sets = await self._discover_sets_from_items(all_items)
            
            # Analyze market data for each set
            analyzed_sets = await self._analyze_set_market_data(discovered_sets)
            
            # Cache results
            cache.set(self.discovered_sets_cache_key, analyzed_sets, self.cache_timeout)
            
            logger.info(f"✅ Discovered {len(analyzed_sets)} armor/weapon sets")
            return analyzed_sets
            
        except Exception as e:
            logger.error(f"❌ Set discovery failed: {e}")
            return []
    
    def _get_all_items_from_db(self) -> List[Item]:
        """Get all items from database."""
        return list(Item.objects.filter(is_active=True).select_related())
    
    async def _discover_sets_from_items(self, items: List[Item]) -> List[SetConfiguration]:
        """Discover sets by analyzing item names and patterns."""
        logger.info("🔍 Discovering sets using pattern matching...")
        
        discovered_sets = []
        items_by_name = {item.name: item for item in items}
        
        # Find set items (complete sets)
        set_items = []
        for item in items:
            set_type = self._classify_set_type(item.name)
            if set_type != SetType.UNKNOWN and self._is_complete_set(item.name):
                set_items.append((item, set_type))
        
        logger.info(f"Found {len(set_items)} potential set items")
        
        # For each set item, find its components
        for set_item, set_type in set_items:
            try:
                components = await self._find_set_components(
                    set_item.name, set_type, items_by_name
                )
                
                if len(components) >= 2:  # Need at least 2 components for a valid set
                    set_config = SetConfiguration(
                        set_name=set_item.name,
                        set_type=set_type,
                        set_item_id=set_item.item_id,
                        component_ids=[comp.item_id for comp in components],
                        component_names=[comp.name for comp in components]
                    )
                    discovered_sets.append(set_config)
            except Exception as e:
                logger.warning(f"Failed to find components for {set_item.name}: {e}")
        
        # Also discover sets without official set items (like GWD armor)
        implied_sets = await self._discover_implied_sets(items_by_name)
        discovered_sets.extend(implied_sets)
        
        logger.info(f"Discovered {len(discovered_sets)} complete sets with components")
        return discovered_sets
    
    def _classify_set_type(self, item_name: str) -> SetType:
        """Classify the type of set based on item name."""
        for set_type, patterns in self.set_patterns.items():
            for pattern in patterns:
                if re.search(pattern, item_name, re.IGNORECASE):
                    return set_type
        return SetType.UNKNOWN
    
    def _is_complete_set(self, item_name: str) -> bool:
        """Check if this item name represents a complete set."""
        set_indicators = [
            'set', 'armour set', 'armor set', 'robes set',
            'harness', 'equipment'
        ]
        return any(indicator in item_name.lower() for indicator in set_indicators)
    
    async def _find_set_components(self, 
                                 set_name: str, 
                                 set_type: SetType, 
                                 items_by_name: Dict[str, Item]) -> List[Item]:
        """Find component items for a given set."""
        components = []
        
        if set_type == SetType.BARROWS:
            # Extract brother name from set name
            match = re.search(r"(.+)'s (?:armour )?set", set_name, re.IGNORECASE)
            if match:
                brother_name = match.group(1)
                
                # Find all items with this brother's name
                for item_name, item in items_by_name.items():
                    if brother_name.lower() in item_name.lower() and 'set' not in item_name.lower():
                        # Avoid degraded items (ending with " 0")
                        if not item_name.endswith(' 0'):
                            components.append(item)
        
        elif set_type == SetType.METAL_ARMOR:
            # Extract metal type
            match = re.search(r"(Bronze|Iron|Steel|Black|Mithril|Adamant|Rune|Dragon)", set_name, re.IGNORECASE)
            if match:
                metal_type = match.group(1)
                
                # Look for standard armor components
                component_types = ['full helm', 'platebody', 'platelegs', 'plateskirt']
                for comp_type in component_types:
                    comp_name = f"{metal_type} {comp_type}"
                    if comp_name in items_by_name:
                        components.append(items_by_name[comp_name])
        
        elif set_type == SetType.DRAGONHIDE:
            # Extract hide type
            match = re.search(r"(.+) dragonhide set", set_name, re.IGNORECASE)
            if match:
                hide_type = match.group(1)
                
                # Look for dragonhide components
                component_types = ["d'hide body", "d'hide chaps", "d'hide vambraces"]
                for comp_type in component_types:
                    comp_name = f"{hide_type} {comp_type}"
                    if comp_name in items_by_name:
                        components.append(items_by_name[comp_name])
        
        return components
    
    async def _discover_implied_sets(self, items_by_name: Dict[str, Item]) -> List[SetConfiguration]:
        """Discover sets that don't have official set items (like GWD armor)."""
        implied_sets = []
        
        # GWD armor sets
        gwd_gods = ['Bandos', 'Armadyl', 'Saradomin', 'Zamorak']
        for god in gwd_gods:
            components = []
            
            # Look for common GWD armor pieces
            potential_pieces = [
                f"{god} helmet", f"{god} chestplate", f"{god} chainskirt",
                f"{god} tassets", f"{god} boots"
            ]
            
            for piece_name in potential_pieces:
                if piece_name in items_by_name:
                    components.append(items_by_name[piece_name])
            
            if len(components) >= 2:
                set_config = SetConfiguration(
                    set_name=f"{god} set",
                    set_type=SetType.GOD_ARMOR,
                    set_item_id=None,  # No official set item
                    component_ids=[comp.item_id for comp in components],
                    component_names=[comp.name for comp in components]
                )
                implied_sets.append(set_config)
        
        # Void armor sets
        void_types = ['melee', 'ranger', 'mage']
        for void_type in void_types:
            components = []
            
            # Void components
            void_pieces = [
                f"Void {void_type} helm",
                "Void knight top",
                "Void knight robe",
                "Void knight gloves"
            ]
            
            for piece_name in void_pieces:
                if piece_name in items_by_name:
                    components.append(items_by_name[piece_name])
            
            if len(components) >= 3:
                set_config = SetConfiguration(
                    set_name=f"Void {void_type} set",
                    set_type=SetType.SPECIALTY,
                    set_item_id=None,
                    component_ids=[comp.item_id for comp in components],
                    component_names=[comp.name for comp in components]
                )
                implied_sets.append(set_config)
        
        return implied_sets
    
    async def _analyze_set_market_data(self, sets: List[SetConfiguration]) -> List[SetConfiguration]:
        """Analyze market data for discovered sets to determine profitability."""
        logger.info(f"📊 Analyzing market data for {len(sets)} sets...")
        
        analyzed_sets = []
        
        for set_config in sets:
            try:
                # Get current price data
                if set_config.set_item_id:
                    # Get set price
                    set_price_data = await asyncio.to_thread(
                        self._get_latest_price, set_config.set_item_id
                    )
                    if set_price_data:
                        set_config.set_price = set_price_data.low_price  # Price to sell set
                        set_config.set_volume = set_price_data.low_price_volume
                
                # Get component prices
                components_total = 0
                components_volumes = []
                
                for comp_id in set_config.component_ids:
                    comp_price_data = await asyncio.to_thread(
                        self._get_latest_price, comp_id
                    )
                    if comp_price_data:
                        components_total += comp_price_data.high_price  # Price to buy component
                        components_volumes.append(comp_price_data.high_price_volume)
                    else:
                        components_volumes.append(0)
                
                set_config.components_total_price = components_total if components_total > 0 else None
                set_config.components_volumes = components_volumes
                
                # Calculate trading strategies
                await self._calculate_trading_strategies(set_config)
                
                # Get historical analysis if available
                await self._analyze_historical_patterns(set_config)
                
                # Calculate confidence score
                set_config.confidence_score = self._calculate_confidence_score(set_config)
                
                if set_config.is_profitable:
                    analyzed_sets.append(set_config)
                    
            except Exception as e:
                logger.warning(f"Failed to analyze set {set_config.set_name}: {e}")
        
        logger.info(f"Found {len(analyzed_sets)} profitable sets")
        return analyzed_sets
    
    def _get_latest_price(self, item_id: int) -> Optional[PriceSnapshot]:
        """Get latest price data for an item."""
        try:
            return PriceSnapshot.objects.filter(
                item__item_id=item_id
            ).order_by('-created_at').first()
        except Exception:
            return None
    
    async def _calculate_trading_strategies(self, set_config: SetConfiguration):
        """Calculate profitability of combine vs decombine strategies."""
        if not set_config.set_price or not set_config.components_total_price:
            return
        
        # Strategy 1: Combine (buy components, sell set)
        if set_config.set_item_id and set_config.set_price > 0:
            # Include GE tax (1% for selling)
            ge_tax = set_config.set_price * 0.01
            combine_profit = set_config.set_price - set_config.components_total_price - ge_tax
            set_config.combine_profit = combine_profit if combine_profit > 0 else None
        
        # Strategy 2: Decombine (buy set, sell components)
        if set_config.set_item_id and set_config.set_price > 0:
            # Include GE tax for selling each component (1% each)
            total_component_sale_value = sum([
                price * 0.99 for price in [  # 99% after tax
                    comp_price for comp_price in self._estimate_component_sell_prices(set_config)
                ]
            ])
            decombine_profit = total_component_sale_value - set_config.set_price
            set_config.decombine_profit = decombine_profit if decombine_profit > 0 else None
        
        # Determine optimal strategy
        if set_config.combine_profit and set_config.decombine_profit:
            if set_config.combine_profit > set_config.decombine_profit:
                set_config.optimal_strategy = TradingStrategy.COMBINE
            else:
                set_config.optimal_strategy = TradingStrategy.DECOMBINE
        elif set_config.combine_profit:
            set_config.optimal_strategy = TradingStrategy.COMBINE
        elif set_config.decombine_profit:
            set_config.optimal_strategy = TradingStrategy.DECOMBINE
        else:
            set_config.optimal_strategy = TradingStrategy.NONE
    
    def _estimate_component_sell_prices(self, set_config: SetConfiguration) -> List[float]:
        """Estimate sell prices for components."""
        sell_prices = []
        
        for comp_id in set_config.component_ids:
            price_data = self._get_latest_price(comp_id)
            if price_data and price_data.low_price:
                sell_prices.append(price_data.low_price)
            else:
                # Fallback to buy price if no sell price
                if price_data and price_data.high_price:
                    sell_prices.append(price_data.high_price * 0.9)  # Estimate 10% lower
                else:
                    sell_prices.append(0)
        
        return sell_prices
    
    async def _analyze_historical_patterns(self, set_config: SetConfiguration):
        """Analyze historical price patterns for better predictions."""
        try:
            # Check if historical data is available
            if set_config.set_item_id:
                historical_count = await asyncio.to_thread(
                    lambda: HistoricalPricePoint.objects.filter(
                        item__item_id=set_config.set_item_id
                    ).count()
                )
                set_config.price_history_available = historical_count > 0
                
                if historical_count > 0:
                    # Calculate volatility from historical data
                    volatility = await asyncio.to_thread(
                        self._calculate_price_volatility, set_config.set_item_id
                    )
                    set_config.volatility_score = volatility
                    
        except Exception as e:
            logger.debug(f"Historical analysis failed for {set_config.set_name}: {e}")
    
    def _calculate_price_volatility(self, item_id: int) -> float:
        """Calculate price volatility from historical data."""
        try:
            # Get recent historical points
            recent_points = HistoricalPricePoint.objects.filter(
                item__item_id=item_id,
                timestamp__gte=timezone.now() - timedelta(days=7)
            ).order_by('timestamp')
            
            if recent_points.count() < 3:
                return 1.0  # High volatility if insufficient data
            
            prices = [point.avg_high_price for point in recent_points if point.avg_high_price]
            if len(prices) < 3:
                return 1.0
            
            # Calculate coefficient of variation
            mean_price = sum(prices) / len(prices)
            variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
            std_dev = variance ** 0.5
            
            return std_dev / mean_price if mean_price > 0 else 1.0
            
        except Exception:
            return 1.0  # High volatility if calculation fails
    
    def _calculate_confidence_score(self, set_config: SetConfiguration) -> float:
        """Calculate overall confidence score for a set trading strategy."""
        score = 0.0
        
        # Base score for having complete price data
        if set_config.set_price and set_config.components_total_price:
            score += 0.3
        
        # Volume score (higher volume = higher confidence)
        if set_config.set_volume and set_config.components_volumes:
            min_volume = min([v for v in set_config.components_volumes if v > 0] + [set_config.set_volume])
            volume_score = min(1.0, min_volume / 100)  # Normalize to max 1.0
            score += volume_score * 0.3
        
        # Historical data availability
        if set_config.price_history_available:
            score += 0.2
        
        # Volatility score (lower volatility = higher confidence)
        if set_config.volatility_score is not None:
            volatility_bonus = max(0, 1.0 - set_config.volatility_score) * 0.2
            score += volatility_bonus
        
        return min(1.0, score)
    
    async def create_trading_opportunities(self, 
                                         sets: List[SetConfiguration],
                                         min_profit: float = 1000,
                                         min_confidence: float = 0.1) -> int:
        """
        Create trading strategy opportunities from discovered sets.
        
        Args:
            sets: List of set configurations to create opportunities from
            min_profit: Minimum profit threshold in GP
            min_confidence: Minimum confidence score threshold
            
        Returns:
            Number of opportunities created
        """
        logger.info(f"💰 Creating trading opportunities from {len(sets)} sets...")
        
        created_count = 0
        
        def create_opportunities_sync():
            nonlocal created_count
            
            with transaction.atomic():
                # Clear existing dynamic opportunities
                SetCombiningOpportunity.objects.filter(
                    set_name__icontains='Dynamic:'
                ).delete()
                
                for set_config in sets:
                    try:
                        if not set_config.is_profitable:
                            continue
                        
                        best_profit = set_config.best_profit
                        if not best_profit or best_profit < min_profit:
                            continue
                        
                        if not set_config.confidence_score or set_config.confidence_score < min_confidence:
                            continue
                        
                        # Create trading strategy
                        strategy_name = f"Dynamic: {set_config.set_name}"
                        if set_config.optimal_strategy == TradingStrategy.COMBINE:
                            strategy_name += " (Combine)"
                            description = f"Buy individual {set_config.set_name} pieces, combine into set"
                            profit = set_config.combine_profit
                        else:
                            strategy_name += " (Decombine)"  
                            description = f"Buy complete {set_config.set_name}, sell individual pieces"
                            profit = set_config.decombine_profit
                        
                        # Calculate additional metrics
                        min_capital = set_config.components_total_price or set_config.set_price or 0
                        profit_margin = (profit / min_capital * 100) if min_capital > 0 else 0
                        
                        # Create strategy
                        strategy, created = TradingStrategy.objects.update_or_create(
                            strategy_type=StrategyType.SET_COMBINING,
                            name=strategy_name,
                            defaults={
                                'description': description,
                                'potential_profit_gp': int(profit),
                                'profit_margin_pct': profit_margin,
                                'risk_level': set_config.risk_level,
                                'min_capital_required': int(min_capital),
                                'recommended_capital': int(min_capital * 3),
                                'optimal_market_condition': 'stable',
                                'estimated_time_minutes': 10,
                                'confidence_score': set_config.confidence_score,
                                'is_active': True,
                                'strategy_data': {
                                    'set_type': set_config.set_type.value,
                                    'optimal_strategy': set_config.optimal_strategy.value,
                                    'component_count': len(set_config.component_ids),
                                    'has_historical_data': set_config.price_history_available,
                                    'discovery_method': 'dynamic_pattern_matching'
                                }
                            }
                        )
                        
                        # Create set combining opportunity
                        SetCombiningOpportunity.objects.update_or_create(
                            set_name=f"Dynamic: {set_config.set_name}",
                            defaults={
                                'strategy': strategy,
                                'set_item_id': set_config.set_item_id or 0,
                                'piece_ids': set_config.component_ids,
                                'piece_names': set_config.component_names,
                                'individual_pieces_total_cost': int(set_config.components_total_price or 0),
                                'complete_set_price': int(set_config.set_price or 0),
                                'lazy_tax_profit': int(profit),
                                'piece_volumes': {
                                    str(comp_id): vol for comp_id, vol in 
                                    zip(set_config.component_ids, set_config.components_volumes)
                                },
                                'set_volume': set_config.set_volume or 0,
                                'profit_margin_pct': profit_margin
                            }
                        )
                        
                        created_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to create opportunity for {set_config.set_name}: {e}")
        
        # Run database operations synchronously
        await asyncio.to_thread(create_opportunities_sync)
        
        logger.info(f"✅ Created {created_count} dynamic trading opportunities")
        return created_count