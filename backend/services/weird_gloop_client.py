"""
Weird Gloop API client for fresh OSRS Grand Exchange price data.

This client provides access to more recent price data than the RuneScape Wiki API,
with better data freshness and reliability for real-time trading information.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union
import httpx
from django.conf import settings
from django.utils import timezone as django_timezone

logger = logging.getLogger(__name__)


class WeirdGloopAPIError(Exception):
    """Custom exception for Weird Gloop API errors."""
    pass


class WeirdGloopAPIClient:
    """
    Async client for interacting with Weird Gloop API (api.weirdgloop.org).
    
    This API typically provides fresher data than the RuneScape Wiki API
    and includes proper volume information.
    """
    
    def __init__(self):
        self.base_url = "https://api.weirdgloop.org"
        self.user_agent = getattr(settings, 'RUNESCAPE_USER_AGENT', 'OSRS-High-Alch-Tracker/1.0')
        self.client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=httpx.Timeout(30.0, connect=10.0, read=20.0, write=10.0),
            limits=httpx.Limits(
                max_keepalive_connections=2,  # Reduced from 5
                max_connections=5,            # Reduced from 10
                keepalive_expiry=30.0         # Close idle connections after 30s
            ),
            follow_redirects=True
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with proper cleanup."""
        if self.client:
            try:
                # Force close with timeout protection
                await asyncio.wait_for(self.client.aclose(), timeout=3.0)
            except asyncio.TimeoutError:
                logger.warning("Weird Gloop client close timed out after 3s, forcing cleanup")
                # Force cleanup if timeout occurs
                try:
                    self.client._transport.close()
                except Exception as e:
                    logger.debug(f"Force cleanup failed: {e}")
            except Exception as e:
                logger.warning(f"Error closing Weird Gloop client: {e}")
            finally:
                self.client = None
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make an async HTTP request to the Weird Gloop API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            WeirdGloopAPIError: If request fails
        """
        if not self.client:
            raise WeirdGloopAPIError("Client not initialized. Use async context manager.")
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making Weird Gloop request to: {url} with params: {params}")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Weird Gloop response: {len(str(data))} characters")
            
            if not data.get('success', True):
                error_msg = data.get('error', 'Unknown API error')
                raise WeirdGloopAPIError(f"API returned error: {error_msg}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
            raise WeirdGloopAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
            
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {str(e)}")
            raise WeirdGloopAPIError(f"Request failed: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {str(e)}")
            raise WeirdGloopAPIError(f"Unexpected error: {str(e)}")
    
    async def get_exchange_status(self) -> Dict:
        """
        Get the last update timestamps for all games.
        
        Returns:
            Dictionary with last update times for each game
        """
        logger.info("Fetching exchange status from Weird Gloop API")
        return await self._make_request("/exchange")
    
    async def get_latest_price(self, item_id: int) -> Optional[Dict]:
        """
        Get the latest price for a specific item.
        
        Args:
            item_id: OSRS item ID
            
        Returns:
            Latest price data or None if not found
        """
        logger.info(f"Fetching latest price for item {item_id} from Weird Gloop API")
        
        try:
            response = await self._make_request(
                "/exchange/history/osrs/latest",
                params={"id": str(item_id)}
            )
            
            # Handle different response structures
            if isinstance(response, list) and len(response) > 0:
                return response[0]  # First item in list
            elif isinstance(response, dict):
                return response
            else:
                logger.warning(f"Unexpected response structure for item {item_id}: {response}")
                return None
                
        except WeirdGloopAPIError as e:
            logger.warning(f"Failed to get price for item {item_id} from Weird Gloop: {e}")
            return None
    
    async def get_latest_prices(self, item_ids: List[int]) -> Dict[str, Dict]:
        """
        Get latest prices for multiple items.
        
        Args:
            item_ids: List of OSRS item IDs
            
        Returns:
            Dictionary mapping item_id -> price_data
        """
        logger.info(f"Fetching latest prices for {len(item_ids)} items from Weird Gloop API")
        
        # Weird Gloop allows multiple IDs separated by |
        ids_param = "|".join(str(item_id) for item_id in item_ids)
        
        try:
            response = await self._make_request(
                "/exchange/history/osrs/latest",
                params={"id": ids_param}
            )
            
            # Convert list response to dictionary format
            result = {}
            if isinstance(response, list):
                for item_data in response:
                    if 'id' in item_data:
                        result[str(item_data['id'])] = item_data
            elif isinstance(response, dict) and 'id' in response:
                result[str(response['id'])] = response
            
            return result
            
        except WeirdGloopAPIError as e:
            logger.error(f"Failed to get prices for items {item_ids[:5]}... from Weird Gloop: {e}")
            return {}
    
    async def get_price_history(self, item_id: int, filter_type: str = "last90d") -> List[List]:
        """
        Get historical price data for an item.
        
        Args:
            item_id: OSRS item ID
            filter_type: "all", "last90d", or "sample"
            
        Returns:
            List of price history data points
        """
        logger.info(f"Fetching price history for item {item_id} with filter {filter_type}")
        
        valid_filters = ["all", "last90d", "sample"]
        if filter_type not in valid_filters:
            filter_type = "last90d"
        
        try:
            response = await self._make_request(
                f"/exchange/history/osrs/{filter_type}",
                params={"id": str(item_id)}
            )
            
            return response if isinstance(response, list) else []
            
        except WeirdGloopAPIError as e:
            logger.warning(f"Failed to get history for item {item_id} from Weird Gloop: {e}")
            return []
    
    async def get_item_mapping(self) -> Dict[str, Dict]:
        """
        Get item mapping with names and IDs for all OSRS items.
        
        Returns:
            Dictionary mapping item_id -> item_data with names
        """
        logger.info("Fetching item mapping from Weird Gloop API")
        
        try:
            response = await self._make_request("/exchange/mapping/osrs")
            
            # Convert list response to dictionary format
            result = {}
            if isinstance(response, list):
                for item in response:
                    if 'id' in item and 'name' in item:
                        result[str(item['id'])] = item
            elif isinstance(response, dict):
                # If response is already a dict, return as-is
                result = response
            
            logger.info(f"Retrieved mapping for {len(result)} OSRS items")
            return result
            
        except WeirdGloopAPIError as e:
            logger.error(f"Failed to get item mapping from Weird Gloop: {e}")
            return {}
    
    async def get_volume_timeseries(self, item_id: int, period: str = "7d") -> List[Dict]:
        """
        Get volume timeseries data for an item (crucial for AI weighting).
        
        Args:
            item_id: OSRS item ID
            period: Time period ("1d", "7d", "30d", "90d")
            
        Returns:
            List of volume data points with timestamps
        """
        logger.info(f"Fetching volume timeseries for item {item_id} over {period}")
        
        valid_periods = ["1d", "7d", "30d", "90d"]
        if period not in valid_periods:
            period = "7d"
        
        try:
            response = await self._make_request(
                f"/exchange/timeseries/osrs/{period}",
                params={"id": str(item_id), "type": "volume"}
            )
            
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and 'data' in response:
                return response['data']
            else:
                return []
                
        except WeirdGloopAPIError as e:
            logger.warning(f"Failed to get volume timeseries for item {item_id}: {e}")
            return []
    
    async def get_volume_timeseries_multiple(self, item_ids: List[int], period: str = "7d") -> Dict[str, List[Dict]]:
        """
        Get volume timeseries data for multiple items.
        
        Args:
            item_ids: List of OSRS item IDs
            period: Time period ("1d", "7d", "30d", "90d")
            
        Returns:
            Dictionary mapping item_id -> volume timeseries data
        """
        logger.info(f"Fetching volume timeseries for {len(item_ids)} items over {period}")
        
        valid_periods = ["1d", "7d", "30d", "90d"]
        if period not in valid_periods:
            period = "7d"
        
        # Weird Gloop allows multiple IDs separated by |
        ids_param = "|".join(str(item_id) for item_id in item_ids)
        
        try:
            response = await self._make_request(
                f"/exchange/timeseries/osrs/{period}",
                params={"id": ids_param, "type": "volume"}
            )
            
            result = {}
            if isinstance(response, dict):
                # Response might be grouped by item ID
                for item_id_str, volume_data in response.items():
                    if item_id_str.isdigit():
                        result[item_id_str] = volume_data if isinstance(volume_data, list) else []
            elif isinstance(response, list):
                # If response is a flat list, we need to group by item_id
                for data_point in response:
                    if isinstance(data_point, dict) and 'id' in data_point:
                        item_id = str(data_point['id'])
                        if item_id not in result:
                            result[item_id] = []
                        result[item_id].append(data_point)
            
            return result
            
        except WeirdGloopAPIError as e:
            logger.error(f"Failed to get volume timeseries for items {item_ids[:5]}... from Weird Gloop: {e}")
            return {}
    
    def calculate_volume_confidence_score(self, volume_data: List[Dict]) -> float:
        """
        Calculate volume confidence score for AI opportunity weighting.
        
        Args:
            volume_data: List of volume data points from timeseries
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not volume_data or len(volume_data) < 2:
            return 0.0
        
        try:
            volumes = [point.get('volume', 0) for point in volume_data if isinstance(point, dict)]
            volumes = [v for v in volumes if v > 0]  # Filter out zero volumes
            
            if len(volumes) < 2:
                return 0.0
            
            avg_volume = sum(volumes) / len(volumes)
            min_volume = min(volumes)
            max_volume = max(volumes)
            
            # Calculate consistency (lower variance = higher confidence)
            variance = sum((v - avg_volume) ** 2 for v in volumes) / len(volumes)
            consistency_score = min(1.0, 1.0 / (1.0 + variance / (avg_volume ** 2)))
            
            # Calculate liquidity (higher average volume = higher confidence)  
            liquidity_score = min(1.0, avg_volume / 1000)  # 1000+ volume = max score
            
            # Calculate stability (smaller range = higher confidence)
            if max_volume > 0:
                stability_score = min_volume / max_volume
            else:
                stability_score = 0.0
            
            # Weighted combination
            confidence = (
                consistency_score * 0.4 +  # 40% consistency
                liquidity_score * 0.4 +    # 40% liquidity  
                stability_score * 0.2      # 20% stability
            )
            
            return round(confidence, 3)
            
        except Exception as e:
            logger.warning(f"Error calculating volume confidence: {e}")
            return 0.0
    
    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """
        Parse ISO timestamp string to Django timezone-aware datetime.
        
        Args:
            timestamp_str: ISO format timestamp string
            
        Returns:
            Django timezone-aware datetime or None
        """
        if not timestamp_str:
            return None
        
        try:
            # Parse ISO format timestamp and convert to Django timezone-aware datetime
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            # dt is already timezone-aware, no need to make_aware
            return dt.astimezone(django_timezone.get_current_timezone())
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid timestamp {timestamp_str}: {e}")
            return None
    
    def get_data_freshness(self, timestamp_str: str) -> Dict:
        """
        Calculate data freshness metrics for a timestamp.
        
        Args:
            timestamp_str: ISO format timestamp string
            
        Returns:
            Dictionary with freshness information
        """
        parsed_time = self.parse_timestamp(timestamp_str)
        if not parsed_time:
            return {
                'age_hours': float('inf'),
                'is_fresh': False,
                'is_recent': False,
                'quality': 'unknown'
            }
        
        current_time = django_timezone.now()
        age_hours = (current_time - parsed_time).total_seconds() / 3600
        
        return {
            'age_hours': age_hours,
            'is_fresh': age_hours < 1,      # Less than 1 hour
            'is_recent': age_hours < 6,     # Less than 6 hours
            'is_acceptable': age_hours < 24, # Less than 24 hours
            'quality': (
                'fresh' if age_hours < 1 else
                'recent' if age_hours < 6 else
                'acceptable' if age_hours < 24 else
                'stale'
            ),
            'timestamp': parsed_time
        }
    
    async def health_check(self) -> bool:
        """
        Check if the Weird Gloop API is accessible and responding.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            status = await self.get_exchange_status()
            osrs_update = status.get('osrs')
            
            if osrs_update:
                freshness = self.get_data_freshness(osrs_update)
                logger.info(f"Weird Gloop API healthy. OSRS data age: {freshness['age_hours']:.1f} hours")
                return freshness['is_acceptable']  # Data should be less than 24h old
            
            return False
            
        except Exception as e:
            logger.error(f"Weird Gloop API health check failed: {e}")
            return False


# Synchronous wrapper for compatibility
class SyncWeirdGloopAPIClient:
    """
    Synchronous wrapper for WeirdGloopAPIClient.
    """
    
    def __init__(self):
        self.async_client = WeirdGloopAPIClient()
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we need to create a new loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(coro)
    
    def get_exchange_status(self) -> Dict:
        """Sync version of get_exchange_status."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_exchange_status()
        return self._run_async(_async_call())
    
    def get_latest_price(self, item_id: int) -> Optional[Dict]:
        """Sync version of get_latest_price."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_latest_price(item_id)
        return self._run_async(_async_call())
    
    def get_latest_prices(self, item_ids: List[int]) -> Dict[str, Dict]:
        """Sync version of get_latest_prices."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_latest_prices(item_ids)
        return self._run_async(_async_call())
    
    def health_check(self) -> bool:
        """Sync version of health_check."""
        async def _async_call():
            async with self.async_client as client:
                return await client.health_check()
        return self._run_async(_async_call())
    
    def get_item_mapping(self) -> Dict[str, Dict]:
        """Sync version of get_item_mapping."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_item_mapping()
        return self._run_async(_async_call())
    
    def get_volume_timeseries(self, item_id: int, period: str = "7d") -> List[Dict]:
        """Sync version of get_volume_timeseries."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_volume_timeseries(item_id, period)
        return self._run_async(_async_call())
    
    def get_volume_timeseries_multiple(self, item_ids: List[int], period: str = "7d") -> Dict[str, List[Dict]]:
        """Sync version of get_volume_timeseries_multiple."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_volume_timeseries_multiple(item_ids, period)
        return self._run_async(_async_call())


# GE Tax Calculation Utilities
class GrandExchangeTax:
    """
    Grand Exchange tax calculation utilities for OSRS money making strategies.
    
    GE Tax Rules:
    - 2% tax on items sold, deducted from seller's received gold
    - Items under 50 GP are exempt
    - Bonds are exempt
    - Tax capped at 5M GP per item for high-value items
    - Tax is rounded down (floor)
    - Applied per-item, not per total value
    """
    
    TAX_RATE = 0.02  # 2%
    TAX_EXEMPTION_THRESHOLD = 50  # GP
    TAX_CAP_PER_ITEM = 5_000_000  # 5M GP
    
    # Items exempt from GE tax
    EXEMPT_ITEMS = {
        13190,  # Old school bond
        # Add other exempt items as discovered
    }
    
    @classmethod
    def calculate_tax(cls, sell_price: int, item_id: int = None) -> int:
        """
        Calculate GE tax for selling an item.
        
        Args:
            sell_price: Price the item sells for in GP
            item_id: Item ID (for checking exemptions)
            
        Returns:
            Tax amount in GP (rounded down)
        """
        # Check exemptions
        if sell_price < cls.TAX_EXEMPTION_THRESHOLD:
            return 0
            
        if item_id and item_id in cls.EXEMPT_ITEMS:
            return 0
        
        # Calculate 2% tax
        raw_tax = int(sell_price * cls.TAX_RATE)
        
        # Apply cap (5M GP max per item)
        return min(raw_tax, cls.TAX_CAP_PER_ITEM)
    
    @classmethod
    def calculate_net_received(cls, sell_price: int, quantity: int = 1, item_id: int = None) -> int:
        """
        Calculate net GP received after GE tax.
        
        Args:
            sell_price: Price per item in GP
            quantity: Number of items sold
            item_id: Item ID (for checking exemptions)
            
        Returns:
            Total GP received after tax
        """
        tax_per_item = cls.calculate_tax(sell_price, item_id)
        net_per_item = sell_price - tax_per_item
        return net_per_item * quantity
    
    @classmethod
    def calculate_profit_after_tax(cls, buy_price: int, sell_price: int, 
                                 quantity: int = 1, item_id: int = None) -> int:
        """
        Calculate profit after GE tax for money making strategies.
        
        Args:
            buy_price: Price paid to buy each item
            sell_price: Price received for selling each item (before tax)
            quantity: Number of items
            item_id: Item ID (for checking exemptions)
            
        Returns:
            Net profit after GE tax in GP
        """
        total_cost = buy_price * quantity
        net_received = cls.calculate_net_received(sell_price, quantity, item_id)
        return net_received - total_cost
    
    @classmethod
    def get_required_margin_for_profit(cls, buy_price: int, target_profit: int, 
                                     item_id: int = None) -> int:
        """
        Calculate required sell price to achieve target profit after tax.
        
        Args:
            buy_price: Price paid for item
            target_profit: Desired profit per item
            item_id: Item ID (for checking exemptions)
            
        Returns:
            Required sell price to achieve target profit
        """
        if item_id and item_id in cls.EXEMPT_ITEMS:
            return buy_price + target_profit
        
        if target_profit <= 0:
            return buy_price
        
        # Account for tax: sell_price * (1 - tax_rate) - buy_price = target_profit
        # So: sell_price = (target_profit + buy_price) / (1 - tax_rate)
        required_gross = (target_profit + buy_price) / (1 - cls.TAX_RATE)
        
        # Handle tax cap for high-value items
        tax_at_price = cls.calculate_tax(int(required_gross), item_id)
        if tax_at_price == cls.TAX_CAP_PER_ITEM:
            # Tax is capped, so calculate differently
            return buy_price + target_profit + cls.TAX_CAP_PER_ITEM
        
        return int(required_gross)
    
    @classmethod
    def analyze_flip_viability(cls, buy_price: int, sell_price: int, 
                             item_id: int = None) -> dict:
        """
        Analyze the viability of a flipping opportunity considering GE tax.
        
        Args:
            buy_price: Current buy price
            sell_price: Current sell price
            item_id: Item ID
            
        Returns:
            Dictionary with flip analysis
        """
        tax = cls.calculate_tax(sell_price, item_id)
        net_received = sell_price - tax
        profit = net_received - buy_price
        
        if buy_price > 0:
            margin_percentage = (profit / buy_price) * 100
        else:
            margin_percentage = 0
        
        return {
            'buy_price': buy_price,
            'sell_price': sell_price,
            'ge_tax': tax,
            'net_received': net_received,
            'profit_per_item': profit,
            'profit_margin_pct': margin_percentage,
            'is_profitable': profit > 0,
            'tax_rate_effective': (tax / sell_price * 100) if sell_price > 0 else 0,
            'is_tax_exempt': tax == 0 and sell_price >= cls.TAX_EXEMPTION_THRESHOLD
        }


class MoneyMakerDataFetcher:
    """
    Enhanced data fetcher for money making strategies.
    Fetches comprehensive data needed for flipping, decanting, set combining, etc.
    """
    
    def __init__(self, weird_gloop_client: WeirdGloopAPIClient):
        self.client = weird_gloop_client
    
    async def fetch_set_combining_data(self, set_definitions: dict) -> dict:
        """
        Fetch comprehensive pricing and volume data for armor/weapon sets and their individual pieces.
        
        Args:
            set_definitions: Dict of {set_id: {'pieces': [item_ids], 'name': str}}
            
        Returns:
            Dict with enhanced set combining opportunities and volume-weighted analysis
        """
        all_item_ids = []
        
        # Collect all item IDs (sets + pieces)
        for set_id, set_info in set_definitions.items():
            all_item_ids.append(set_id)
            all_item_ids.extend(set_info['pieces'])
        
        # Fetch all prices and volume data concurrently
        price_data = await self.client.get_latest_prices(all_item_ids)
        volume_data = await self.client.get_volume_timeseries_multiple(all_item_ids, "7d")
        
        opportunities = {}
        
        for set_id, set_info in set_definitions.items():
            set_price_data = price_data.get(str(set_id))
            if not set_price_data:
                continue
            
            # Get set prices (we need both buy and sell prices for both directions)
            set_buy_price = set_price_data.get('price', 0)  # Price to buy complete set
            set_sell_price = set_price_data.get('price', 0)  # Price to sell complete set
            
            pieces_total_buy_cost = 0
            pieces_total_sell_value = 0
            pieces_data = []
            piece_volumes = []
            
            # Calculate costs for individual pieces
            for piece_id in set_info['pieces']:
                piece_data = price_data.get(str(piece_id))
                if piece_data:
                    piece_buy_price = piece_data.get('price', 0)  # Price to buy individual piece
                    piece_sell_price = piece_data.get('price', 0)  # Price to sell individual piece
                    
                    pieces_total_buy_cost += piece_buy_price
                    pieces_total_sell_value += piece_sell_price
                    
                    # Get volume confidence score
                    piece_volume_data = volume_data.get(str(piece_id), [])
                    volume_confidence = self.client.calculate_volume_confidence_score(piece_volume_data)
                    
                    pieces_data.append({
                        'item_id': piece_id,
                        'buy_price': piece_buy_price,
                        'sell_price': piece_sell_price,
                        'volume': piece_data.get('volume', 0),
                        'volume_confidence': volume_confidence,
                        'volume_timeseries': piece_volume_data
                    })
                    
                    piece_volumes.append(volume_confidence)
            
            if pieces_total_buy_cost > 0 and len(pieces_data) > 0:
                # Calculate both combining and decombining strategies
                
                # Strategy 1: Combining (buy pieces -> sell complete set)
                combining_profit = GrandExchangeTax.analyze_flip_viability(
                    pieces_total_buy_cost, set_sell_price, set_id
                )
                
                # Strategy 2: Decombining (buy complete set -> sell pieces) 
                decombining_profit = GrandExchangeTax.analyze_flip_viability(
                    set_buy_price, pieces_total_sell_value, None  # No specific item ID for combined pieces
                )
                
                # Calculate GE tax for decombining (tax on each piece sold)
                decombining_tax = sum(
                    GrandExchangeTax.calculate_tax(piece['sell_price'], piece['item_id'])
                    for piece in pieces_data
                )
                decombining_profit['ge_tax'] = decombining_tax
                decombining_profit['net_received'] = pieces_total_sell_value - decombining_tax
                decombining_profit['profit_per_item'] = decombining_profit['net_received'] - set_buy_price
                decombining_profit['is_profitable'] = decombining_profit['profit_per_item'] > 0
                
                # Choose the more profitable strategy
                if combining_profit['profit_per_item'] > decombining_profit['profit_per_item']:
                    best_strategy = 'combining'
                    best_profit = combining_profit
                    strategy_description = "Buy individual pieces → Sell complete set"
                else:
                    best_strategy = 'decombining' 
                    best_profit = decombining_profit
                    strategy_description = "Buy complete set → Sell individual pieces"
                
                # Calculate volume-weighted confidence score
                avg_volume_confidence = sum(piece_volumes) / len(piece_volumes) if piece_volumes else 0.0
                
                # Get set volume confidence
                set_volume_data = volume_data.get(str(set_id), [])
                set_volume_confidence = self.client.calculate_volume_confidence_score(set_volume_data)
                
                # Overall confidence is the minimum of set and pieces (bottleneck)
                overall_confidence = min(avg_volume_confidence, set_volume_confidence)
                
                lazy_tax_percentage = (best_profit['profit_per_item'] / best_profit['buy_price'] * 100) if best_profit['buy_price'] > 0 else 0
                
                opportunities[set_id] = {
                    'set_name': set_info['name'],
                    'set_buy_price': set_buy_price,
                    'set_sell_price': set_sell_price,
                    'pieces_total_buy_cost': pieces_total_buy_cost,
                    'pieces_total_sell_value': pieces_total_sell_value,
                    'pieces_data': pieces_data,
                    'combining_analysis': combining_profit,
                    'decombining_analysis': decombining_profit,
                    'best_strategy': best_strategy,
                    'strategy_description': strategy_description,
                    'lazy_tax_percentage': lazy_tax_percentage,
                    'profit_analysis': best_profit,
                    'ge_tax': best_profit['ge_tax'],
                    'net_profit': best_profit['profit_per_item'],
                    'is_profitable': best_profit['is_profitable'],
                    'volume_confidence': overall_confidence,
                    'avg_piece_volume_confidence': avg_volume_confidence,
                    'set_volume_confidence': set_volume_confidence,
                    'volume_data': {
                        'set_timeseries': set_volume_data,
                        'piece_timeseries': {str(piece['item_id']): piece['volume_timeseries'] for piece in pieces_data}
                    }
                }
        
        return opportunities
    
    async def fetch_decanting_data(self, potion_families: dict) -> dict:
        """
        Fetch pricing data for potion decanting opportunities.
        
        Args:
            potion_families: Dict of {base_name: {4: item_id, 3: item_id, 2: item_id, 1: item_id}}
            
        Returns:
            Dict with decanting opportunities and profit analysis
        """
        all_potion_ids = []
        for family in potion_families.values():
            all_potion_ids.extend(family.values())
        
        price_data = await self.client.get_latest_prices(all_potion_ids)
        
        opportunities = {}
        
        for potion_name, doses in potion_families.items():
            dose_prices = {}
            
            # Get prices for each dose
            for dose, item_id in doses.items():
                item_data = price_data.get(str(item_id))
                if item_data:
                    dose_prices[dose] = {
                        'item_id': item_id,
                        'price': item_data.get('price', 0),
                        'volume': item_data.get('volume', 0)
                    }
            
            # Find best decanting opportunities
            best_opportunities = []
            for from_dose in [4, 3, 2]:
                for to_dose in range(1, from_dose):
                    if from_dose in dose_prices and to_dose in dose_prices:
                        from_data = dose_prices[from_dose]
                        to_data = dose_prices[to_dose]
                        
                        # Calculate profit: buy high dose, decant to low dose, sell
                        buy_price = from_data['price']
                        sell_price = to_data['price']
                        
                        profit_analysis = GrandExchangeTax.analyze_flip_viability(
                            buy_price, sell_price, to_data['item_id']
                        )
                        
                        if profit_analysis['is_profitable']:
                            best_opportunities.append({
                                'from_dose': from_dose,
                                'to_dose': to_dose,
                                'from_item_id': from_data['item_id'],
                                'to_item_id': to_data['item_id'],
                                'buy_price': buy_price,
                                'sell_price': sell_price,
                                'profit_analysis': profit_analysis,
                                'volume_constraint': min(from_data['volume'], to_data['volume'])
                            })
            
            if best_opportunities:
                # Sort by profit per hour potential
                best_opportunities.sort(key=lambda x: x['profit_analysis']['profit_per_item'], reverse=True)
                opportunities[potion_name] = {
                    'dose_prices': dose_prices,
                    'best_opportunities': best_opportunities,
                    'top_profit': best_opportunities[0]['profit_analysis']['profit_per_item']
                }
        
        return opportunities
    
    async def fetch_bond_flipping_targets(self, min_value: int = 1_000_000) -> dict:
        """
        Fetch high-value items suitable for bond-funded flipping.
        
        Args:
            min_value: Minimum item value to consider
            
        Returns:
            Dict with high-value flipping opportunities
        """
        # High-value items that are commonly flipped
        high_value_items = [
            # Expensive weapons
            11802, # Armadyl godsword
            11804, # Bandos godsword  
            11806, # Saradomin godsword
            11808, # Zamorak godsword
            12904, # Toxic blowpipe
            13576, # Dragon warhammer
            21015, # Kodai wand
            
            # Expensive armor pieces
            11828, # Armadyl helmet
            11830, # Armadyl chestplate  
            11832, # Armadyl chainskirt
            11834, # Bandos chestplate
            11836, # Bandos tassets
            
            # High-value supplies
            13190, # Old school bond (exempt from tax!)
        ]
        
        price_data = await self.client.get_latest_prices(high_value_items)
        
        opportunities = {}
        for item_id_str, item_data in price_data.items():
            item_id = int(item_id_str)
            price = item_data.get('price', 0)
            
            if price >= min_value:
                # Calculate potential flip margins
                # Assume 5% spread for estimation
                estimated_buy = int(price * 0.975)  # Buy 2.5% below
                estimated_sell = int(price * 1.025)  # Sell 2.5% above
                
                profit_analysis = GrandExchangeTax.analyze_flip_viability(
                    estimated_buy, estimated_sell, item_id
                )
                
                opportunities[item_id] = {
                    'current_price': price,
                    'estimated_buy_price': estimated_buy,
                    'estimated_sell_price': estimated_sell,
                    'profit_analysis': profit_analysis,
                    'volume': item_data.get('volume', 0),
                    'capital_required': estimated_buy,
                    'is_bond_exempt': item_id in GrandExchangeTax.EXEMPT_ITEMS
                }
        
        return opportunities