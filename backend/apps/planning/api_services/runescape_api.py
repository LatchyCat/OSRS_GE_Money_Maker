"""
RuneScape API service for fetching item data and prices.
"""

import logging
import requests
from typing import Dict, List, Any, Optional
from django.conf import settings
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class RuneScapeAPIService:
    """Service for interacting with RuneScape Wiki API."""
    
    def __init__(self):
        self.base_url = getattr(settings, 'RUNESCAPE_API_BASE_URL', 'https://prices.runescape.wiki/api/v1/osrs')
        self.user_agent = getattr(settings, 'RUNESCAPE_USER_AGENT', 'OSRS_High_Alch_Tracker - @latchy Discord')
        
        # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'User-Agent': self.user_agent
        })
    
    def get_latest_prices(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get latest price data for all items.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary containing price data
        """
        cache_key = 'runescape_latest_prices'
        cache_timeout = 300  # 5 minutes
        
        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info("📈 Using cached price data")
                return cached_data
        
        try:
            logger.info("📈 Fetching latest prices from RuneScape API...")
            response = self.session.get(f"{self.base_url}/latest", timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the data
            if use_cache:
                cache.set(cache_key, data, cache_timeout)
            
            logger.info(f"✅ Fetched price data for {len(data.get('data', {}))} items")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch latest prices: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching prices: {e}")
            raise
    
    def get_5m_prices(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get 5-minute average prices.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary containing 5-minute price data
        """
        cache_key = 'runescape_5m_prices'
        cache_timeout = 300  # 5 minutes
        
        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info("📊 Using cached 5m price data")
                return cached_data
        
        try:
            logger.info("📊 Fetching 5-minute prices from RuneScape API...")
            response = self.session.get(f"{self.base_url}/5m", timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the data
            if use_cache:
                cache.set(cache_key, data, cache_timeout)
            
            logger.info(f"✅ Fetched 5m price data for {len(data.get('data', {}))} items")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch 5m prices: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching 5m prices: {e}")
            raise
    
    def get_1h_prices(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get 1-hour average prices.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary containing 1-hour price data
        """
        cache_key = 'runescape_1h_prices'
        cache_timeout = 900  # 15 minutes
        
        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info("📊 Using cached 1h price data")
                return cached_data
        
        try:
            logger.info("📊 Fetching 1-hour prices from RuneScape API...")
            response = self.session.get(f"{self.base_url}/1h", timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the data
            if use_cache:
                cache.set(cache_key, data, cache_timeout)
            
            logger.info(f"✅ Fetched 1h price data for {len(data.get('data', {}))} items")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch 1h prices: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching 1h prices: {e}")
            raise
    
    def get_item_mapping(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get complete item mapping data.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            List of item data dictionaries
        """
        cache_key = 'runescape_item_mapping'
        cache_timeout = 3600 * 24  # 24 hours
        
        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info("📦 Using cached item mapping data")
                return cached_data
        
        try:
            logger.info("📦 Fetching item mapping from RuneScape API...")
            response = self.session.get(f"{self.base_url}/mapping", timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the data
            if use_cache:
                cache.set(cache_key, data, cache_timeout)
            
            logger.info(f"✅ Fetched mapping data for {len(data)} items")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch item mapping: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching item mapping: {e}")
            raise
    
    def get_timeseries_data(self, timestep: str, item_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get timeseries price data.
        
        Args:
            timestep: Time step (5m, 1h, 6h, 24h)
            item_id: Optional specific item ID
            
        Returns:
            Dictionary containing timeseries data
        """
        try:
            url = f"{self.base_url}/timeseries"
            params = {'timestep': timestep}
            
            if item_id:
                params['id'] = item_id
            
            logger.info(f"📊 Fetching {timestep} timeseries data...")
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ Fetched timeseries data")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch timeseries data: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching timeseries data: {e}")
            raise
    
    def detect_new_items(self, known_item_ids: set) -> List[Dict[str, Any]]:
        """
        Detect new items by comparing current mapping with known items.
        
        Args:
            known_item_ids: Set of item IDs we already know about
            
        Returns:
            List of new item data
        """
        try:
            current_mapping = self.get_item_mapping(use_cache=False)  # Always fetch fresh data
            new_items = []
            
            for item_data in current_mapping:
                item_id = item_data.get('id')
                if item_id and item_id not in known_item_ids:
                    new_items.append(item_data)
            
            if new_items:
                logger.info(f"🆕 Detected {len(new_items)} new items!")
                for item in new_items[:5]:  # Log first 5 new items
                    logger.info(f"   • {item.get('name')} (ID: {item.get('id')})")
                if len(new_items) > 5:
                    logger.info(f"   • ... and {len(new_items) - 5} more")
            else:
                logger.info("✅ No new items detected")
            
            return new_items
            
        except Exception as e:
            logger.error(f"❌ Failed to detect new items: {e}")
            raise
    
    def get_item_info(self, item_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific item.
        
        Args:
            item_id: The item ID to get information for
            
        Returns:
            Dictionary containing item information
        """
        try:
            # Try to find the item in the mapping data
            mapping_data = self.get_item_mapping()
            
            for item_data in mapping_data:
                if item_data.get('id') == item_id:
                    return item_data
            
            logger.warning(f"Item {item_id} not found in mapping data")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Failed to get item info for {item_id}: {e}")
            raise
    
    def get_bulk_price_data(self, item_ids: List[int]) -> Dict[str, Any]:
        """
        Get price data for multiple specific items.
        
        Args:
            item_ids: List of item IDs to get prices for
            
        Returns:
            Dictionary containing price data for specified items
        """
        try:
            all_prices = self.get_latest_prices()
            
            filtered_data = {}
            for item_id in item_ids:
                item_id_str = str(item_id)
                if item_id_str in all_prices.get('data', {}):
                    filtered_data[item_id_str] = all_prices['data'][item_id_str]
            
            logger.info(f"📊 Retrieved price data for {len(filtered_data)}/{len(item_ids)} items")
            return {'data': filtered_data}
            
        except Exception as e:
            logger.error(f"❌ Failed to get bulk price data: {e}")
            raise