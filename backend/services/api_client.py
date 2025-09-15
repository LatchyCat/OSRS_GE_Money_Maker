"""
RuneScape Wiki API client for fetching item data and prices.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import httpx
from django.conf import settings
from django.utils import timezone as django_timezone

logger = logging.getLogger(__name__)


class RuneScapeWikiAPIError(Exception):
    """Custom exception for RuneScape Wiki API errors."""
    pass


class RuneScapeWikiClient:
    """
    Async client for interacting with RuneScape Wiki API.
    """
    
    def __init__(self):
        self.base_url = settings.RUNESCAPE_API_BASE_URL
        self.user_agent = settings.RUNESCAPE_USER_AGENT
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
                logger.warning("RuneScape Wiki client close timed out after 3s, forcing cleanup")
                # Force cleanup if timeout occurs
                try:
                    self.client._transport.close()
                except Exception as e:
                    logger.debug(f"Force cleanup failed: {e}")
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
            
        Raises:
            RuneScapeWikiAPIError: If request fails
        """
        if not self.client:
            raise RuneScapeWikiAPIError("Client not initialized. Use async context manager.")
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making request to: {url} with params: {params}")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Received response with {len(str(data))} characters")
            
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
    
    async def get_item_mapping(self) -> Dict:
        """
        Fetch the complete item mapping data.
        
        Returns:
            Dictionary with item mapping data
        """
        logger.info("Fetching item mapping data")
        return await self._make_request("/mapping")
    
    async def get_latest_prices(self, item_id: Optional[int] = None) -> Dict:
        """
        Fetch latest prices for all items or a specific item.
        
        Args:
            item_id: Optional specific item ID to fetch
            
        Returns:
            Dictionary with latest price data
        """
        params = {"id": item_id} if item_id else None
        logger.info(f"Fetching latest prices{f' for item {item_id}' if item_id else ''}")
        
        return await self._make_request("/latest", params=params)
    
    async def get_5m_prices(self, timestamp: Optional[int] = None) -> Dict:
        """
        Fetch 5-minute aggregated prices with volume data.
        
        Args:
            timestamp: Optional Unix timestamp for specific time period
            
        Returns:
            Dictionary with 5-minute price and volume data
        """
        params = {"timestamp": timestamp} if timestamp else None
        logger.info(f"Fetching 5m prices{f' for timestamp {timestamp}' if timestamp else ''}")
        
        return await self._make_request("/5m", params=params)
    
    async def get_5m_volume_data(self, item_ids: Optional[List[int]] = None) -> Dict:
        """
        Fetch 5-minute volume data for specific items or all items.
        
        Args:
            item_ids: Optional list of item IDs to fetch volume for
            
        Returns:
            Dictionary with 5-minute volume data
        """
        # If specific items requested, batch them
        if item_ids:
            all_data = {}
            for item_id in item_ids:
                params = {"id": item_id}
                try:
                    data = await self._make_request("/5m", params=params)
                    if 'data' in data and str(item_id) in data['data']:
                        all_data[str(item_id)] = data['data'][str(item_id)]
                except Exception as e:
                    logger.warning(f"Failed to fetch 5m data for item {item_id}: {e}")
            return {"data": all_data}
        else:
            # Fetch all 5-minute data
            return await self.get_5m_prices()
    
    async def get_1h_prices(self, timestamp: Optional[int] = None) -> Dict:
        """
        Fetch 1-hour aggregated prices.
        
        Args:
            timestamp: Optional Unix timestamp for specific time period
            
        Returns:
            Dictionary with 1-hour price data
        """
        params = {"timestamp": timestamp} if timestamp else None
        logger.info(f"Fetching 1h prices{f' for timestamp {timestamp}' if timestamp else ''}")
        
        return await self._make_request("/1h", params=params)
    
    async def get_timeseries(self, item_id: int, timestep: str) -> Dict:
        """
        Fetch time series data for a specific item.
        
        Args:
            item_id: Item ID to get time series for
            timestep: Time step ("5m", "1h", "6h", "24h")
            
        Returns:
            Dictionary with time series data
        """
        if timestep not in ["5m", "1h", "6h", "24h"]:
            raise ValueError(f"Invalid timestep: {timestep}. Must be one of: 5m, 1h, 6h, 24h")
        
        params = {"id": item_id, "timestep": timestep}
        logger.info(f"Fetching timeseries for item {item_id} with timestep {timestep}")
        
        return await self._make_request("/timeseries", params=params)
    
    async def get_latest_from_timeseries(self, item_id: int, timestep: str = "5m") -> Optional[Dict]:
        """
        Get the latest price data from timeseries API (often fresher than /latest).
        
        Args:
            item_id: Item ID to get latest data for
            timestep: Time step to use ("5m", "1h", "6h", "24h")
            
        Returns:
            Latest price data from timeseries or None if not available
        """
        try:
            timeseries_data = await self.get_timeseries(item_id, timestep)
            data_points = timeseries_data.get('data', [])
            
            if not data_points:
                logger.warning(f"No timeseries data found for item {item_id}")
                return None
            
            # Get the most recent data point
            latest_point = data_points[-1]
            
            # Convert timeseries format to match /latest API format
            return {
                'data': {
                    str(item_id): {
                        'high': latest_point.get('avgHighPrice', 0),
                        'low': latest_point.get('avgLowPrice', 0),
                        'highTime': latest_point.get('timestamp', 0),
                        'lowTime': latest_point.get('timestamp', 0),
                        'highVolume': latest_point.get('highPriceVolume', 0),
                        'lowVolume': latest_point.get('lowPriceVolume', 0),
                        'source': f'timeseries_{timestep}'
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get latest from timeseries for item {item_id}: {e}")
            return None
    
    async def get_freshest_price_data(self, item_id: int) -> Optional[Dict]:
        """
        Get the freshest available price data by trying multiple sources.
        
        Tries in order: 5m timeseries -> 1h timeseries -> latest endpoint
        
        Args:
            item_id: Item ID to get price data for
            
        Returns:
            Freshest price data available or None
        """
        logger.info(f"Getting freshest price data for item {item_id}")
        
        # Try 5-minute timeseries first (freshest data)
        try:
            result = await self.get_latest_from_timeseries(item_id, "5m")
            if result and result.get('data', {}).get(str(item_id)):
                data = result['data'][str(item_id)]
                timestamp = data.get('highTime', 0)
                age_hours = (django_timezone.now().timestamp() - timestamp) / 3600 if timestamp > 0 else float('inf')
                
                if age_hours < 24:  # Data is less than 24 hours old
                    logger.info(f"Using 5m timeseries data for item {item_id} (age: {age_hours:.1f}h)")
                    return result
        except Exception as e:
            logger.debug(f"5m timeseries failed for item {item_id}: {e}")
        
        # Try 1-hour timeseries
        try:
            result = await self.get_latest_from_timeseries(item_id, "1h")
            if result and result.get('data', {}).get(str(item_id)):
                data = result['data'][str(item_id)]
                timestamp = data.get('highTime', 0)
                age_hours = (django_timezone.now().timestamp() - timestamp) / 3600 if timestamp > 0 else float('inf')
                
                if age_hours < 24:  # Data is less than 24 hours old
                    logger.info(f"Using 1h timeseries data for item {item_id} (age: {age_hours:.1f}h)")
                    return result
        except Exception as e:
            logger.debug(f"1h timeseries failed for item {item_id}: {e}")
        
        # Fall back to regular latest endpoint
        try:
            result = await self.get_latest_prices(item_id)
            if result and result.get('data', {}).get(str(item_id)):
                logger.info(f"Using /latest endpoint for item {item_id}")
                # Mark the source for transparency
                if 'data' in result:
                    for item_data in result['data'].values():
                        item_data['source'] = 'latest_endpoint'
                return result
        except Exception as e:
            logger.debug(f"/latest endpoint failed for item {item_id}: {e}")
        
        logger.warning(f"No price data available from any source for item {item_id}")
        return None
    
    async def batch_fetch_latest_prices(self, item_ids: List[int], batch_size: int = 50) -> Dict:
        """
        Fetch latest prices for multiple items in batches to avoid overwhelming the API.
        
        Args:
            item_ids: List of item IDs to fetch prices for
            batch_size: Number of individual requests to make concurrently
            
        Returns:
            Combined dictionary with all price data
        """
        logger.info(f"Batch fetching prices for {len(item_ids)} items in batches of {batch_size}")
        
        all_data = {}
        
        # Process in batches to be respectful to the API
        for i in range(0, len(item_ids), batch_size):
            batch = item_ids[i:i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1}: items {i+1}-{min(i+batch_size, len(item_ids))}")
            
            # Create tasks for this batch
            tasks = [self.get_latest_prices(item_id) for item_id in batch]
            
            try:
                # Execute batch concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for item_id, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to fetch price for item {item_id}: {result}")
                        continue
                    
                    # Merge data (assuming API returns {data: {item_id: {...}}} format)
                    if 'data' in result:
                        all_data.update(result['data'])
                
                # Small delay between batches to be respectful
                if i + batch_size < len(item_ids):
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error in batch {i//batch_size + 1}: {e}")
                continue
        
        logger.info(f"Batch fetch completed. Retrieved data for {len(all_data)} items")
        return {"data": all_data}
    
    def parse_unix_timestamp(self, timestamp: Optional[int]) -> Optional[datetime]:
        """
        Convert Unix timestamp to Django timezone-aware datetime.
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            Django timezone-aware datetime or None
        """
        if timestamp is None:
            return None
        
        try:
            return django_timezone.make_aware(
                datetime.fromtimestamp(timestamp),
                timezone=django_timezone.get_current_timezone()
            )
        except (ValueError, OSError) as e:
            logger.warning(f"Invalid timestamp {timestamp}: {e}")
            return None
    
    async def health_check(self) -> bool:
        """
        Check if the API is accessible and responding.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Try to fetch a simple endpoint
            await self.get_latest_prices(2)  # Cannonball - common item
            logger.info("API health check passed")
            return True
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return False


# Synchronous wrapper for compatibility
class SyncRuneScapeWikiClient:
    """
    Synchronous wrapper for RuneScapeWikiClient.
    """
    
    def __init__(self):
        self.async_client = RuneScapeWikiClient()
    
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
    
    def get_item_mapping(self) -> Dict:
        """Sync version of get_item_mapping."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_item_mapping()
        return self._run_async(_async_call())
    
    def get_latest_prices(self, item_id: Optional[int] = None) -> Dict:
        """Sync version of get_latest_prices."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_latest_prices(item_id)
        return self._run_async(_async_call())
    
    def get_5m_prices(self, timestamp: Optional[int] = None) -> Dict:
        """Sync version of get_5m_prices."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_5m_prices(timestamp)
        return self._run_async(_async_call())
    
    def get_5m_volume_data(self, item_ids: Optional[List[int]] = None) -> Dict:
        """Sync version of get_5m_volume_data."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_5m_volume_data(item_ids)
        return self._run_async(_async_call())
    
    def get_1h_prices(self, timestamp: Optional[int] = None) -> Dict:
        """Sync version of get_1h_prices."""
        async def _async_call():
            async with self.async_client as client:
                return await client.get_1h_prices(timestamp)
        return self._run_async(_async_call())
    
    def health_check(self) -> bool:
        """Sync version of health_check."""
        async def _async_call():
            async with self.async_client as client:
                return await client.health_check()
        return self._run_async(_async_call())