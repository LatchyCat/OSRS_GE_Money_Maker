"""
RuneScape Wiki Real-time Prices API client for accurate OSRS Grand Exchange data.

This client provides access to the official RuneScape Wiki price API which offers:
- Complete item coverage with real Grand Exchange data
- Separate high/low prices with timestamps
- Real-time accuracy (updated every few minutes)
- Proper volume and trading activity data
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union
import httpx
from django.conf import settings
from django.utils import timezone as django_timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class RuneScapeWikiAPIError(Exception):
    """Custom exception for RuneScape Wiki API errors."""
    pass


@dataclass
class WikiPriceData:
    """Structured price data from RuneScape Wiki API."""
    item_id: int
    high_price: Optional[int]
    low_price: Optional[int]
    high_time: Optional[int]
    low_time: Optional[int]
    age_hours: float
    data_quality: str
    raw_data: Dict
    
    @property
    def has_valid_prices(self) -> bool:
        """Check if item has valid pricing data."""
        return (self.high_price is not None and self.high_price > 0) or \
               (self.low_price is not None and self.low_price > 0)
    
    @property
    def best_buy_price(self) -> int:
        """Get best available buy price (high price preferred)."""
        if self.high_price and self.high_price > 0:
            return self.high_price
        return self.low_price or 0
    
    @property
    def best_sell_price(self) -> int:
        """Get best available sell price (low price preferred)."""
        if self.low_price and self.low_price > 0:
            return self.low_price
        return self.high_price or 0


@dataclass
class TimeSeriesData:
    """Time-series data point from RuneScape Wiki API."""
    timestamp: int
    avg_high_price: Optional[int]
    avg_low_price: Optional[int]
    high_price_volume: int
    low_price_volume: int
    
    @property
    def total_volume(self) -> int:
        """Calculate total trading volume."""
        return self.high_price_volume + self.low_price_volume
    
    @property
    def has_volume(self) -> bool:
        """Check if this data point has any trading volume."""
        return self.total_volume > 0
    
    @property
    def volume_weighted_price(self) -> Optional[int]:
        """Calculate volume-weighted average price."""
        if not self.has_volume:
            return None
        
        total_value = 0
        total_volume = 0
        
        if self.avg_high_price and self.high_price_volume > 0:
            total_value += self.avg_high_price * self.high_price_volume
            total_volume += self.high_price_volume
        
        if self.avg_low_price and self.low_price_volume > 0:
            total_value += self.avg_low_price * self.low_price_volume
            total_volume += self.low_price_volume
        
        return int(total_value / total_volume) if total_volume > 0 else None


@dataclass
class HistoricalPriceData:
    """Historical price data from /5m and /1h endpoints."""
    item_id: int
    interval: str  # '5m' or '1h'
    timestamp: int
    avg_high_price: Optional[int]
    avg_low_price: Optional[int] 
    high_price_volume: int
    low_price_volume: int
    data_source: str = 'runescape_wiki'
    
    @property
    def total_volume(self) -> int:
        """Calculate total trading volume."""
        return self.high_price_volume + self.low_price_volume
    
    @property
    def has_volume(self) -> bool:
        """Check if this data point has any trading volume."""
        return self.total_volume > 0
    
    @property 
    def volume_weighted_price(self) -> Optional[int]:
        """Calculate volume-weighted average price."""
        if not self.has_volume:
            return None
        
        total_value = 0
        total_volume = 0
        
        if self.avg_high_price and self.high_price_volume > 0:
            total_value += self.avg_high_price * self.high_price_volume
            total_volume += self.high_price_volume
        
        if self.avg_low_price and self.low_price_volume > 0:
            total_value += self.avg_low_price * self.low_price_volume
            total_volume += self.low_price_volume
        
        return int(total_value / total_volume) if total_volume > 0 else None
    
    @property
    def age_hours(self) -> float:
        """Calculate age of this data point in hours."""
        current_time = django_timezone.now().timestamp()
        return (current_time - self.timestamp) / 3600
    
    @property
    def price_spread(self) -> Optional[int]:
        """Calculate spread between high and low prices."""
        if self.avg_high_price and self.avg_low_price:
            return self.avg_high_price - self.avg_low_price
        return None
    
    @property
    def spread_percentage(self) -> Optional[float]:
        """Calculate spread as percentage of volume-weighted price."""
        spread = self.price_spread
        weighted_price = self.volume_weighted_price
        
        if spread and weighted_price and weighted_price > 0:
            return (spread / weighted_price) * 100
        return None


@dataclass
class ItemMetadata:
    """Item metadata from RuneScape Wiki mapping."""
    id: int
    name: str
    examine: str
    members: bool
    lowalch: int
    highalch: int
    limit: int
    value: int
    icon: str
    
    def to_embedding_context(self) -> str:
        """Convert item metadata to text for embedding."""
        return f"""Item: {self.name}
Description: {self.examine}
Members: {'Yes' if self.members else 'No'}
High Alch: {self.highalch:,} GP
Low Alch: {self.lowalch:,} GP
GE Limit: {self.limit}/4h
Store Value: {self.value:,} GP
Category: {'Members Item' if self.members else 'F2P Item'}"""


class RuneScapeWikiAPIClient:
    """
    Async client for RuneScape Wiki Real-time Prices API.
    
    Provides accurate Grand Exchange data with proper high/low pricing,
    timestamps, and comprehensive item metadata for AI analysis.
    """
    
    def __init__(self):
        self.base_url = "https://prices.runescape.wiki/api/v1/osrs"
        self.user_agent = getattr(settings, 'RUNESCAPE_USER_AGENT', 'OSRS-AI-Tracker/2.0')
        self.client = None
        self._item_metadata_cache = {}
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json"
            },
            timeout=httpx.Timeout(30.0, connect=10.0, read=20.0, write=10.0),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=60.0
            ),
            follow_redirects=True
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            try:
                await asyncio.wait_for(self.client.aclose(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("RuneScape Wiki client close timed out")
            except Exception as e:
                logger.warning(f"Error closing RuneScape Wiki client: {e}")
            finally:
                self.client = None
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make an async HTTP request to the RuneScape Wiki API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Response data as dictionary
        """
        if not self.client:
            raise RuneScapeWikiAPIError("Client not initialized")
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making Wiki API request to: {url} with params: {params}")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Wiki API response: {len(str(data))} characters")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
            raise RuneScapeWikiAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
            
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {str(e)}")
            raise RuneScapeWikiAPIError(f"Request failed: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {str(e)}")
            raise RuneScapeWikiAPIError(f"Unexpected error: {str(e)}")
    
    async def get_latest_prices(self, item_id: Optional[int] = None) -> Dict[int, WikiPriceData]:
        """
        Get latest prices from RuneScape Wiki API.
        
        Args:
            item_id: Specific item ID to fetch, or None for all items
            
        Returns:
            Dictionary mapping item_id -> WikiPriceData
        """
        endpoint = "/latest"
        params = {"id": str(item_id)} if item_id else None
        
        logger.info(f"Fetching latest prices from Wiki API" + 
                   (f" for item {item_id}" if item_id else " for all items"))
        
        try:
            response = await self._make_request(endpoint, params)
            
            # Parse response data
            price_data = {}
            current_time = django_timezone.now().timestamp()
            
            # Response format: {"data": {item_id: {high, highTime, low, lowTime}}}
            data_dict = response.get("data", {})
            
            for item_id_str, price_info in data_dict.items():
                try:
                    item_id_int = int(item_id_str)
                    
                    high_price = price_info.get("high")
                    low_price = price_info.get("low")
                    high_time = price_info.get("highTime")
                    low_time = price_info.get("lowTime")
                    
                    # Calculate data age
                    most_recent_time = max(
                        high_time or 0,
                        low_time or 0
                    )
                    
                    if most_recent_time > 0:
                        age_hours = (current_time - most_recent_time) / 3600
                    else:
                        age_hours = float('inf')
                    
                    # Determine data quality
                    if age_hours < 1:
                        data_quality = "fresh"
                    elif age_hours < 6:
                        data_quality = "recent"
                    elif age_hours < 24:
                        data_quality = "acceptable"
                    else:
                        data_quality = "stale"
                    
                    price_data[item_id_int] = WikiPriceData(
                        item_id=item_id_int,
                        high_price=high_price,
                        low_price=low_price,
                        high_time=high_time,
                        low_time=low_time,
                        age_hours=age_hours,
                        data_quality=data_quality,
                        raw_data=price_info
                    )
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse price data for item {item_id_str}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(price_data)} items from Wiki API")
            return price_data
            
        except RuneScapeWikiAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get latest prices: {e}")
            raise RuneScapeWikiAPIError(f"Failed to fetch prices: {e}")
    
    async def get_item_mapping(self) -> Dict[int, ItemMetadata]:
        """
        Get complete item mapping with metadata for AI analysis.
        
        Returns:
            Dictionary mapping item_id -> ItemMetadata
        """
        if self._item_metadata_cache:
            logger.info("Using cached item metadata")
            return self._item_metadata_cache
        
        logger.info("Fetching item mapping from Wiki API")
        
        try:
            response = await self._make_request("/mapping")
            
            metadata_dict = {}
            
            # Response format: List of item objects
            if isinstance(response, list):
                for item_data in response:
                    try:
                        item_id = item_data.get("id")
                        if not item_id:
                            continue
                        
                        metadata = ItemMetadata(
                            id=item_id,
                            name=item_data.get("name", ""),
                            examine=item_data.get("examine", ""),
                            members=item_data.get("members", False),
                            lowalch=item_data.get("lowalch", 0),
                            highalch=item_data.get("highalch", 0),
                            limit=item_data.get("limit", 0),
                            value=item_data.get("value", 0),
                            icon=item_data.get("icon", "")
                        )
                        
                        metadata_dict[item_id] = metadata
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse item metadata: {e}")
                        continue
            
            self._item_metadata_cache = metadata_dict
            logger.info(f"Cached metadata for {len(metadata_dict)} items")
            
            return metadata_dict
            
        except Exception as e:
            logger.error(f"Failed to get item mapping: {e}")
            raise RuneScapeWikiAPIError(f"Failed to fetch item mapping: {e}")
    
    async def get_enriched_price_data(self, item_ids: List[int]) -> Dict[int, Tuple[WikiPriceData, Optional[ItemMetadata]]]:
        """
        Get price data enriched with item metadata for AI analysis.
        
        Args:
            item_ids: List of item IDs to fetch
            
        Returns:
            Dictionary mapping item_id -> (price_data, metadata)
        """
        logger.info(f"Fetching enriched data for {len(item_ids)} items")
        
        # Fetch both price and metadata in parallel
        price_task = asyncio.create_task(self.get_latest_prices())
        metadata_task = asyncio.create_task(self.get_item_mapping())
        
        try:
            all_prices, all_metadata = await asyncio.gather(price_task, metadata_task)
            
            enriched_data = {}
            
            for item_id in item_ids:
                price_data = all_prices.get(item_id)
                metadata = all_metadata.get(item_id)
                
                if price_data or metadata:
                    enriched_data[item_id] = (price_data, metadata)
            
            logger.info(f"Enriched data for {len(enriched_data)} items")
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to get enriched price data: {e}")
            raise RuneScapeWikiAPIError(f"Failed to fetch enriched data: {e}")
    
    async def get_timeseries(self, item_id: int, timestep: str = "1h") -> List[TimeSeriesData]:
        """
        Get time-series volume and price data from RuneScape Wiki API.
        
        Args:
            item_id: OSRS item ID to fetch time-series for
            timestep: Timestep interval ("5m", "1h", "6h", "24h")
            
        Returns:
            List of TimeSeriesData points with volume and price information
        """
        endpoint = "/timeseries"
        params = {
            "id": str(item_id),
            "timestep": timestep
        }
        
        logger.info(f"Fetching timeseries data for item {item_id} with timestep {timestep}")
        
        try:
            response = await self._make_request(endpoint, params)
            
            # Parse response data
            timeseries_data = []
            data_list = response.get("data", [])
            
            for data_point in data_list:
                try:
                    timeseries_data.append(TimeSeriesData(
                        timestamp=data_point.get("timestamp", 0),
                        avg_high_price=data_point.get("avgHighPrice"),
                        avg_low_price=data_point.get("avgLowPrice"),
                        high_price_volume=data_point.get("highPriceVolume", 0),
                        low_price_volume=data_point.get("lowPriceVolume", 0)
                    ))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse timeseries data point: {e}")
                    continue
            
            logger.info(f"Retrieved {len(timeseries_data)} timeseries data points for item {item_id}")
            return timeseries_data
            
        except RuneScapeWikiAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get timeseries data for item {item_id}: {e}")
            raise RuneScapeWikiAPIError(f"Failed to fetch timeseries: {e}")
    
    async def get_historical_prices_5m(self, timestamp: Optional[int] = None) -> Dict[int, HistoricalPriceData]:
        """
        Get 5-minute historical price data from RuneScape Wiki API.
        
        Args:
            timestamp: Optional timestamp for specific 5m period, or None for latest
            
        Returns:
            Dictionary mapping item_id -> HistoricalPriceData
        """
        endpoint = "/5m"
        params = {"timestamp": str(timestamp)} if timestamp else None
        
        logger.info(f"Fetching 5-minute price data from Wiki API" + 
                   (f" for timestamp {timestamp}" if timestamp else " for latest period"))
        
        try:
            response = await self._make_request(endpoint, params)
            
            # Parse response data
            historical_data = {}
            
            # Response format: {"data": {item_id: {avgHighPrice, highPriceVolume, avgLowPrice, lowPriceVolume}}}
            data_dict = response.get("data", {})
            
            # Get timestamp from response or use current time
            response_timestamp = response.get("timestamp", int(django_timezone.now().timestamp()))
            
            for item_id_str, price_info in data_dict.items():
                try:
                    item_id_int = int(item_id_str)
                    
                    historical_data[item_id_int] = HistoricalPriceData(
                        item_id=item_id_int,
                        interval='5m',
                        timestamp=response_timestamp,
                        avg_high_price=price_info.get("avgHighPrice"),
                        avg_low_price=price_info.get("avgLowPrice"),
                        high_price_volume=price_info.get("highPriceVolume", 0),
                        low_price_volume=price_info.get("lowPriceVolume", 0)
                    )
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse 5m price data for item {item_id_str}: {e}")
                    continue
            
            logger.info(f"Retrieved 5-minute data for {len(historical_data)} items")
            return historical_data
            
        except RuneScapeWikiAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get 5-minute price data: {e}")
            raise RuneScapeWikiAPIError(f"Failed to fetch 5m prices: {e}")
    
    async def get_historical_prices_1h(self, timestamp: Optional[int] = None) -> Dict[int, HistoricalPriceData]:
        """
        Get 1-hour historical price data from RuneScape Wiki API.
        
        Args:
            timestamp: Optional timestamp for specific 1h period, or None for latest
            
        Returns:
            Dictionary mapping item_id -> HistoricalPriceData
        """
        endpoint = "/1h"
        params = {"timestamp": str(timestamp)} if timestamp else None
        
        logger.info(f"Fetching 1-hour price data from Wiki API" + 
                   (f" for timestamp {timestamp}" if timestamp else " for latest period"))
        
        try:
            response = await self._make_request(endpoint, params)
            
            # Parse response data
            historical_data = {}
            
            # Response format: {"data": {item_id: {avgHighPrice, highPriceVolume, avgLowPrice, lowPriceVolume}}}
            data_dict = response.get("data", {})
            
            # Get timestamp from response or use current time  
            response_timestamp = response.get("timestamp", int(django_timezone.now().timestamp()))
            
            for item_id_str, price_info in data_dict.items():
                try:
                    item_id_int = int(item_id_str)
                    
                    historical_data[item_id_int] = HistoricalPriceData(
                        item_id=item_id_int,
                        interval='1h',
                        timestamp=response_timestamp,
                        avg_high_price=price_info.get("avgHighPrice"),
                        avg_low_price=price_info.get("avgLowPrice"),
                        high_price_volume=price_info.get("highPriceVolume", 0),
                        low_price_volume=price_info.get("lowPriceVolume", 0)
                    )
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse 1h price data for item {item_id_str}: {e}")
                    continue
            
            logger.info(f"Retrieved 1-hour data for {len(historical_data)} items")
            return historical_data
            
        except RuneScapeWikiAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get 1-hour price data: {e}")
            raise RuneScapeWikiAPIError(f"Failed to fetch 1h prices: {e}")
    
    async def get_comprehensive_historical_data(self, 
                                               include_5m: bool = True,
                                               include_1h: bool = True,
                                               timestamps_5m: Optional[List[int]] = None,
                                               timestamps_1h: Optional[List[int]] = None) -> Dict[str, Dict[int, List[HistoricalPriceData]]]:
        """
        Get comprehensive historical price data from multiple endpoints.
        
        Args:
            include_5m: Whether to include 5-minute data
            include_1h: Whether to include 1-hour data
            timestamps_5m: Specific 5m timestamps to fetch (optional)
            timestamps_1h: Specific 1h timestamps to fetch (optional)
            
        Returns:
            Dictionary with structure:
            {
                '5m': {item_id: [HistoricalPriceData, ...]},
                '1h': {item_id: [HistoricalPriceData, ...]}
            }
        """
        logger.info("Fetching comprehensive historical price data")
        
        results = {'5m': {}, '1h': {}}
        
        # Fetch 5-minute data
        if include_5m:
            if timestamps_5m:
                # Fetch specific timestamps
                for timestamp in timestamps_5m:
                    try:
                        data_5m = await self.get_historical_prices_5m(timestamp)
                        for item_id, price_data in data_5m.items():
                            if item_id not in results['5m']:
                                results['5m'][item_id] = []
                            results['5m'][item_id].append(price_data)
                    except Exception as e:
                        logger.warning(f"Failed to fetch 5m data for timestamp {timestamp}: {e}")
            else:
                # Fetch latest only
                try:
                    data_5m = await self.get_historical_prices_5m()
                    for item_id, price_data in data_5m.items():
                        results['5m'][item_id] = [price_data]
                except Exception as e:
                    logger.warning(f"Failed to fetch latest 5m data: {e}")
        
        # Fetch 1-hour data
        if include_1h:
            if timestamps_1h:
                # Fetch specific timestamps
                for timestamp in timestamps_1h:
                    try:
                        data_1h = await self.get_historical_prices_1h(timestamp)
                        for item_id, price_data in data_1h.items():
                            if item_id not in results['1h']:
                                results['1h'][item_id] = []
                            results['1h'][item_id].append(price_data)
                    except Exception as e:
                        logger.warning(f"Failed to fetch 1h data for timestamp {timestamp}: {e}")
            else:
                # Fetch latest only
                try:
                    data_1h = await self.get_historical_prices_1h()
                    for item_id, price_data in data_1h.items():
                        results['1h'][item_id] = [price_data]
                except Exception as e:
                    logger.warning(f"Failed to fetch latest 1h data: {e}")
        
        total_items_5m = len(results['5m'])
        total_items_1h = len(results['1h'])
        
        logger.info(f"Retrieved comprehensive historical data: {total_items_5m} items (5m), {total_items_1h} items (1h)")
        
        return results

    async def get_volume_analysis(self, item_id: int, duration: str = "24h") -> Dict:
        """
        Get comprehensive volume analysis for an item.
        
        Args:
            item_id: OSRS item ID
            duration: Analysis duration (maps to timestep: 24h="1h", 7d="6h", 30d="24h")
            
        Returns:
            Dictionary with volume analysis metrics
        """
        # Map duration to appropriate timestep
        timestep_map = {
            "1h": "5m",    # Last hour with 5m intervals  
            "24h": "1h",   # Last 24h with 1h intervals
            "7d": "6h",    # Last 7 days with 6h intervals  
            "30d": "24h"   # Last 30 days with 24h intervals
        }
        
        timestep = timestep_map.get(duration, "1h")
        
        try:
            timeseries = await self.get_timeseries(item_id, timestep)
            
            if not timeseries:
                return {
                    "total_volume": 0,
                    "avg_volume_per_hour": 0,
                    "volume_trend": "no_data",
                    "trading_activity": "inactive",
                    "liquidity_score": 0.0,
                    "price_stability": 0.0
                }
            
            # Calculate volume metrics
            active_points = [point for point in timeseries if point.has_volume]
            total_volume = sum(point.total_volume for point in active_points)
            
            # Calculate average volume per hour (normalize based on timestep)
            timestep_hours = {"5m": 1/12, "1h": 1, "6h": 6, "24h": 24}
            avg_volume_per_hour = total_volume / (len(active_points) * timestep_hours.get(timestep, 1)) if active_points else 0
            
            # Volume trend analysis
            if len(active_points) >= 2:
                recent_volume = sum(point.total_volume for point in active_points[-3:])
                older_volume = sum(point.total_volume for point in active_points[:3])
                
                if recent_volume > older_volume * 1.2:
                    volume_trend = "increasing"
                elif recent_volume < older_volume * 0.8:
                    volume_trend = "decreasing"
                else:
                    volume_trend = "stable"
            else:
                volume_trend = "insufficient_data"
            
            # Trading activity classification
            if avg_volume_per_hour > 100:
                trading_activity = "very_active"
            elif avg_volume_per_hour > 50:
                trading_activity = "active"
            elif avg_volume_per_hour > 10:
                trading_activity = "moderate"
            elif avg_volume_per_hour > 1:
                trading_activity = "low"
            else:
                trading_activity = "inactive"
            
            # Liquidity score (0-1 based on consistent trading)
            trading_periods = len(active_points)
            total_periods = len(timeseries)
            liquidity_score = trading_periods / total_periods if total_periods > 0 else 0.0
            
            # Price stability (lower value = more stable)
            prices = [point.volume_weighted_price for point in active_points if point.volume_weighted_price]
            if len(prices) >= 2:
                price_std = np.std(prices) if prices else 0
                avg_price = np.mean(prices) if prices else 1
                price_stability = price_std / avg_price if avg_price > 0 else 1.0
            else:
                price_stability = 1.0
            
            return {
                "total_volume": total_volume,
                "avg_volume_per_hour": round(avg_volume_per_hour, 2),
                "volume_trend": volume_trend,
                "trading_activity": trading_activity,
                "liquidity_score": round(liquidity_score, 3),
                "price_stability": round(price_stability, 3),
                "active_trading_periods": trading_periods,
                "total_periods_analyzed": total_periods,
                "timestep": timestep
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze volume for item {item_id}: {e}")
            return {
                "total_volume": 0,
                "avg_volume_per_hour": 0,
                "volume_trend": "error",
                "trading_activity": "error",
                "liquidity_score": 0.0,
                "price_stability": 0.0,
                "error": str(e)
            }

    async def health_check(self) -> bool:
        """
        Check if the RuneScape Wiki API is accessible.
        
        Returns:
            True if API is healthy
        """
        try:
            # Test with a simple request for a known item (coins)
            prices = await self.get_latest_prices(item_id=995)
            
            if prices:
                logger.info("RuneScape Wiki API health check passed")
                return True
            
            logger.warning("RuneScape Wiki API returned empty data")
            return False
            
        except Exception as e:
            logger.error(f"RuneScape Wiki API health check failed: {e}")
            return False


# Synchronous wrapper for compatibility
class SyncRuneScapeWikiAPIClient:
    """Synchronous wrapper for RuneScapeWikiAPIClient."""
    
    def __init__(self):
        self.async_client = RuneScapeWikiAPIClient()
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)
    
    def get_latest_prices(self, item_id: Optional[int] = None) -> Dict[int, WikiPriceData]:
        """Sync version of get_latest_prices."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_latest_prices(item_id)
        return self._run_async(_async_call())
    
    def get_item_mapping(self) -> Dict[int, ItemMetadata]:
        """Sync version of get_item_mapping."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_item_mapping()
        return self._run_async(_async_call())
    
    def get_timeseries(self, item_id: int, timestep: str = "1h") -> List[TimeSeriesData]:
        """Sync version of get_timeseries."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_timeseries(item_id, timestep)
        return self._run_async(_async_call())
    
    def get_volume_analysis(self, item_id: int, duration: str = "24h") -> Dict:
        """Sync version of get_volume_analysis."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_volume_analysis(item_id, duration)
        return self._run_async(_async_call())
    
    def get_historical_prices_5m(self, timestamp: Optional[int] = None) -> Dict[int, HistoricalPriceData]:
        """Sync version of get_historical_prices_5m."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_historical_prices_5m(timestamp)
        return self._run_async(_async_call())
    
    def get_historical_prices_1h(self, timestamp: Optional[int] = None) -> Dict[int, HistoricalPriceData]:
        """Sync version of get_historical_prices_1h."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_historical_prices_1h(timestamp)
        return self._run_async(_async_call())
    
    def get_comprehensive_historical_data(self, 
                                          include_5m: bool = True,
                                          include_1h: bool = True,
                                          timestamps_5m: Optional[List[int]] = None,
                                          timestamps_1h: Optional[List[int]] = None) -> Dict[str, Dict[int, List[HistoricalPriceData]]]:
        """Sync version of get_comprehensive_historical_data."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_comprehensive_historical_data(
                    include_5m, include_1h, timestamps_5m, timestamps_1h
                )
        return self._run_async(_async_call())

    def health_check(self) -> bool:
        """Sync version of health_check."""
        async def _async_call():
            async with self.async_client as client:
                return await client.health_check()
        return self._run_async(_async_call())


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