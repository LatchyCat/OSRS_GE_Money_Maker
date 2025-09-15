"""
OSRS Wiki Profit Calculator for Set Combining

Uses only the official OSRS Wiki API endpoints:
- /mapping: Gets item names and IDs  
- /latest: Gets current prices for items
- /timeseries: Gets volume data for AI opportunity weighting

Calculates accurate profits with GE tax for both combining and decombining strategies.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from services.runescape_wiki_client import RuneScapeWikiAPIClient
from services.weird_gloop_client import GrandExchangeTax

logger = logging.getLogger(__name__)


class OSRSWikiProfitCalculator:
    """
    Enhanced profit calculator using only OSRS Wiki API endpoints for accurate set combining analysis.
    """
    
    def __init__(self):
        # Define known profitable armor/weapon sets for OSRS
        self.armor_sets = {
            # === BARROWS SETS (Most Popular) ===
            "Dharok's armour set": {
                'set_item_id': 4718,
                'piece_ids': [4716, 4714, 4712, 4718],
                'piece_names': ["Dharok's helm", "Dharok's platebody", "Dharok's platelegs", "Dharok's greataxe"]
            },
            "Ahrim's armour set": {
                'set_item_id': 4708, 
                'piece_ids': [4708, 4710, 4712, 4714],
                'piece_names': ["Ahrim's hood", "Ahrim's robetop", "Ahrim's robeskirt", "Ahrim's staff"]
            },
            "Karil's armour set": {
                'set_item_id': 4732,
                'piece_ids': [4732, 4734, 4736, 4734],
                'piece_names': ["Karil's coif", "Karil's leathertop", "Karil's leatherskirt", "Karil's crossbow"]
            },
            "Torag's armour set": {
                'set_item_id': 4747,
                'piece_ids': [4745, 4749, 4751, 4747], 
                'piece_names': ["Torag's helm", "Torag's platebody", "Torag's platelegs", "Torag's hammers"]
            },
            "Guthan's armour set": {
                'set_item_id': 4724,
                'piece_ids': [4724, 4726, 4728, 4726],
                'piece_names': ["Guthan's helm", "Guthan's platebody", "Guthan's chainskirt", "Guthan's warspear"]  
            },
            "Verac's armour set": {
                'set_item_id': 4753,
                'piece_ids': [4753, 4757, 4759, 4755],
                'piece_names': ["Verac's helm", "Verac's brassard", "Verac's plateskirt", "Verac's flail"]
            },
            
            # === VOID KNIGHT SETS ===
            'Void knight set': {
                'set_item_id': 8839,
                'piece_ids': [8839, 8840, 8842, 8844],
                'piece_names': ['Void knight top', 'Void knight robe', 'Void knight gloves', 'Void knight helm']
            },
            
            # === GRACEFUL OUTFIT ===
            'Graceful outfit': {
                'set_item_id': 11850,
                'piece_ids': [11850, 11852, 11854, 11856, 11858, 11860],
                'piece_names': ['Graceful hood', 'Graceful top', 'Graceful legs', 'Graceful gloves', 'Graceful boots', 'Graceful cape']
            },
            
            # === ANGLER OUTFIT ===
            'Angler outfit': {
                'set_item_id': 13258,
                'piece_ids': [13258, 13259, 13260, 13261], 
                'piece_names': ['Angler hat', 'Angler top', 'Angler waders', 'Angler boots']
            },
            
            # === HIGH VALUE GILDED SETS ===
            'Gilded armour set (lg)': {
                'set_item_id': 3481,
                'piece_ids': [3481, 3483, 3485, 3486],
                'piece_names': ['Gilded platebody', 'Gilded platelegs', 'Gilded full helm', 'Gilded kiteshield']
            },
            
            # === METAL ARMOR SETS ===
            'Rune armour set (lg)': {
                'set_item_id': 1127,
                'piece_ids': [1127, 1079, 1163, 1201],
                'piece_names': ['Rune platebody', 'Rune platelegs', 'Rune full helm', 'Rune kiteshield']
            },
            'Adamant armour set (lg)': {
                'set_item_id': 1123,
                'piece_ids': [1123, 1073, 1161, 1199],
                'piece_names': ['Adamant platebody', 'Adamant platelegs', 'Adamant full helm', 'Adamant kiteshield']
            },
        }
    
    async def calculate_set_combining_opportunities(
        self, 
        min_profit: int = 5000,
        min_volume_score: float = 0.1,
        capital_available: int = 50_000_000
    ) -> List[Dict]:
        """
        Calculate set combining opportunities using OSRS Wiki API endpoints.
        
        Args:
            min_profit: Minimum profit required in GP
            min_volume_score: Minimum volume confidence score (0.0-1.0)
            capital_available: Available capital for trading
            
        Returns:
            List of profitable set combining opportunities
        """
        logger.info("Starting set combining analysis with OSRS Wiki API")
        
        opportunities = []
        
        async with RuneScapeWikiAPIClient() as wiki_client:
            # Step 1: Get item mapping (/mapping endpoint)
            logger.info("Fetching item mapping from /mapping endpoint...")
            mapping = await wiki_client.get_item_mapping()
            logger.info(f"Retrieved mapping for {len(mapping)} items")
            
            # Step 2: Get latest prices (/latest endpoint)  
            logger.info("Fetching latest prices from /latest endpoint...")
            all_prices = await wiki_client.get_latest_prices()
            logger.info(f"Retrieved pricing data for {len(all_prices)} items")
            
            # Step 3: Analyze each armor set
            for set_name, set_info in self.armor_sets.items():
                try:
                    opportunity = await self._analyze_single_set(
                        set_name, set_info, all_prices, wiki_client, min_profit, min_volume_score, capital_available
                    )
                    
                    if opportunity:
                        opportunities.append(opportunity)
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze {set_name}: {e}")
                    continue
        
        # Sort opportunities by volume-weighted profit
        opportunities.sort(key=lambda x: x.get('volume_weighted_profit', 0), reverse=True)
        
        logger.info(f"Found {len(opportunities)} profitable set combining opportunities")
        return opportunities
    
    async def _analyze_single_set(
        self,
        set_name: str,
        set_info: Dict,
        all_prices: Dict,
        wiki_client: RuneScapeWikiAPIClient,
        min_profit: int,
        min_volume_score: float,
        capital_available: int
    ) -> Optional[Dict]:
        """
        Analyze a single armor set for combining/decombining profit.
        
        Args:
            set_name: Name of the armor set
            set_info: Set configuration with item IDs
            all_prices: Price data from /latest endpoint
            wiki_client: Wiki API client for timeseries data
            min_profit: Minimum profit threshold
            min_volume_score: Minimum volume threshold
            capital_available: Available capital
            
        Returns:
            Opportunity data or None if not profitable
        """
        set_item_id = set_info['set_item_id']
        piece_ids = set_info['piece_ids']
        piece_names = set_info['piece_names']
        
        # Get price data for complete set and individual pieces
        set_price_data = all_prices.get(set_item_id)
        if not set_price_data or not set_price_data.has_valid_prices:
            return None
        
        pieces_data = []
        pieces_total_buy_cost = 0
        pieces_total_sell_value = 0
        
        # Collect piece pricing data
        for i, piece_id in enumerate(piece_ids):
            piece_price_data = all_prices.get(piece_id)
            if not piece_price_data or not piece_price_data.has_valid_prices:
                return None  # Skip sets with missing piece data
            
            piece_buy_price = piece_price_data.best_buy_price
            piece_sell_price = piece_price_data.best_sell_price
            
            pieces_total_buy_cost += piece_buy_price
            pieces_total_sell_value += piece_sell_price
            
            pieces_data.append({
                'item_id': piece_id,
                'name': piece_names[i],
                'buy_price': piece_buy_price,
                'sell_price': piece_sell_price,
                'high_time': piece_price_data.high_time,
                'low_time': piece_price_data.low_time,
                'age_hours': piece_price_data.age_hours
            })
        
        # Get complete set pricing
        set_buy_price = set_price_data.best_buy_price
        set_sell_price = set_price_data.best_sell_price
        
        # Step 3: Get volume data from /timeseries endpoint for AI weighting
        volume_scores = []
        
        # Get volume confidence for complete set
        set_timeseries = await wiki_client.get_timeseries(set_item_id, "1h")
        set_volume_score = self._calculate_volume_confidence(set_timeseries)
        volume_scores.append(set_volume_score)
        
        # Get volume confidence for individual pieces
        for piece_data in pieces_data:
            piece_timeseries = await wiki_client.get_timeseries(piece_data['item_id'], "1h")
            piece_volume_score = self._calculate_volume_confidence(piece_timeseries)
            volume_scores.append(piece_volume_score)
            piece_data['volume_score'] = piece_volume_score
        
        # Overall volume confidence is the minimum (bottleneck)
        overall_volume_score = min(volume_scores) if volume_scores else 0.0
        
        # Skip if volume is too low
        if overall_volume_score < min_volume_score:
            return None
        
        # Step 4: Calculate profits for both strategies with GE tax
        
        # Strategy 1: Combining (buy pieces -> sell complete set)
        combining_ge_tax = GrandExchangeTax.calculate_tax(set_sell_price, set_item_id)
        combining_net_revenue = set_sell_price - combining_ge_tax
        combining_profit = combining_net_revenue - pieces_total_buy_cost
        
        # Strategy 2: Decombining (buy complete set -> sell individual pieces)
        decombining_ge_tax = sum(GrandExchangeTax.calculate_tax(piece['sell_price'], piece['item_id']) for piece in pieces_data)
        decombining_net_revenue = pieces_total_sell_value - decombining_ge_tax
        decombining_profit = decombining_net_revenue - set_buy_price
        
        # Choose the more profitable strategy
        if combining_profit > decombining_profit:
            best_strategy = 'combining'
            best_profit = combining_profit
            required_capital = pieces_total_buy_cost
            strategy_description = "Buy individual pieces → Sell complete set"
            ge_tax = combining_ge_tax
        else:
            best_strategy = 'decombining'
            best_profit = decombining_profit
            required_capital = set_buy_price
            strategy_description = "Buy complete set → Sell individual pieces"
            ge_tax = decombining_ge_tax
        
        # Check profit and capital requirements
        if best_profit < min_profit:
            return None
        
        if required_capital > capital_available * 0.8:  # Don't use more than 80% of capital
            return None
        
        # Calculate additional metrics
        profit_margin_pct = (best_profit / required_capital * 100) if required_capital > 0 else 0
        volume_weighted_profit = best_profit * overall_volume_score
        
        # Calculate estimated sets per hour based on volume
        estimated_sets_per_hour = max(1, int(6 * overall_volume_score))  # 1-6 sets per hour
        profit_per_hour = best_profit * estimated_sets_per_hour
        
        return {
            'id': hash(f"osrs_wiki_{set_name}") % 100000 + 90000,  # Generate unique ID
            'set_name': set_name,
            'set_item_id': set_item_id,
            'strategy': best_strategy,
            'strategy_description': strategy_description,
            'piece_ids': piece_ids,
            'piece_names': piece_names,
            'piece_prices': [piece['sell_price'] for piece in pieces_data],  # For display
            'individual_pieces_total_cost': pieces_total_buy_cost,
            'complete_set_price': set_buy_price if best_strategy == 'decombining' else set_sell_price,
            'lazy_tax_profit': best_profit,
            'profit_margin_pct': profit_margin_pct,
            'ge_tax': ge_tax,
            'required_capital': required_capital,
            'piece_volumes': [piece.get('volume_score', 0) for piece in pieces_data],
            'set_volume': set_volume_score,
            'volume_score': overall_volume_score,
            'confidence_score': overall_volume_score,  # Use volume as confidence
            'ai_risk_level': 'low' if overall_volume_score > 0.7 else 'medium' if overall_volume_score > 0.3 else 'high',
            'estimated_sets_per_hour': estimated_sets_per_hour,
            'profit_per_hour': profit_per_hour,
            'volume_weighted_profit': volume_weighted_profit,
            'avg_data_age_hours': sum(piece.get('age_hours', 0) for piece in pieces_data) / len(pieces_data),
            'pieces_data': pieces_data,  # Detailed piece information
            'data_source': 'osrs_wiki_api',
            'pricing_source': '/latest endpoint',
            'volume_source': '/timeseries endpoint'
        }
    
    def _calculate_volume_confidence(self, timeseries_data: List) -> float:
        """
        Calculate volume confidence score from timeseries data.
        
        Args:
            timeseries_data: Timeseries data from /timeseries endpoint
            
        Returns:
            Volume confidence score between 0.0 and 1.0
        """
        if not timeseries_data or len(timeseries_data) < 2:
            return 0.0
        
        try:
            # Extract volumes from timeseries
            volumes = []
            for data_point in timeseries_data:
                if hasattr(data_point, 'avgHighPrice') and hasattr(data_point, 'highPriceVolume'):
                    if data_point.highPriceVolume and data_point.highPriceVolume > 0:
                        volumes.append(data_point.highPriceVolume)
                elif hasattr(data_point, 'avgLowPrice') and hasattr(data_point, 'lowPriceVolume'):
                    if data_point.lowPriceVolume and data_point.lowPriceVolume > 0:
                        volumes.append(data_point.lowPriceVolume)
            
            if len(volumes) < 2:
                return 0.0
            
            # Calculate metrics
            avg_volume = sum(volumes) / len(volumes)
            min_volume = min(volumes)
            max_volume = max(volumes)
            
            # Liquidity score (higher average volume = better)
            liquidity_score = min(1.0, avg_volume / 1000)  # 1000+ volume = max score
            
            # Consistency score (lower variance = better)
            if avg_volume > 0:
                variance = sum((v - avg_volume) ** 2 for v in volumes) / len(volumes)
                cv = (variance ** 0.5) / avg_volume  # Coefficient of variation
                consistency_score = max(0.0, 1.0 - cv)
            else:
                consistency_score = 0.0
            
            # Stability score (smaller range = better)
            if max_volume > 0:
                stability_score = min_volume / max_volume
            else:
                stability_score = 0.0
            
            # Weighted combination
            confidence = (
                liquidity_score * 0.5 +      # 50% liquidity  
                consistency_score * 0.3 +    # 30% consistency
                stability_score * 0.2        # 20% stability
            )
            
            return round(confidence, 3)
            
        except Exception as e:
            logger.warning(f"Error calculating volume confidence: {e}")
            return 0.0