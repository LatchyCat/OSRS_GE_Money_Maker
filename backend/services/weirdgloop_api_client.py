"""
WeirdGloop API Client for OSRS Historical Price Data

This service integrates with the WeirdGloop API to fetch historical price data
for OSRS items. Used for trend analysis, volatility calculations, and pattern recognition.

API Documentation: https://api.weirdgloop.org/exchange/docs
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class HistoricalDataPoint:
    """Represents a single historical price data point."""
    price: int
    volume: Optional[int]
    timestamp: datetime
    
    @classmethod
    def from_api_response(cls, data_point: dict) -> 'HistoricalDataPoint':
        """Create instance from API response data."""
        return cls(
            price=int(data_point['price']),
            volume=data_point.get('volume'),
            timestamp=datetime.fromtimestamp(
                data_point['timestamp'] / 1000,  # Convert from milliseconds
                tz=timezone.utc
            )
        )


class WeirdGloopAPIClient:
    """Client for fetching OSRS historical price data from WeirdGloop API."""
    
    BASE_URL = "https://api.weirdgloop.org/exchange"
    
    def __init__(self, rate_limit_requests_per_minute=60):
        """Initialize client with rate limiting."""
        self.rate_limit = rate_limit_requests_per_minute
        self.session = None
        self._rate_limiter = asyncio.Semaphore(rate_limit_requests_per_minute)
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get_historical_data(self, 
                                item_id: int, 
                                game: str = 'osrs',
                                filter_type: str = 'all') -> List[HistoricalDataPoint]:
        """
        Fetch historical price data for a single item.
        
        Args:
            item_id: OSRS item ID
            game: Game type (osrs or rs)
            filter_type: Data filter type (all, latest, etc.)
            
        Returns:
            List of historical data points
        """
        if not self.session:
            raise RuntimeError("Client must be used as async context manager")
        
        # Check cache first
        cache_key = f"weirdgloop_history_{game}_{filter_type}_{item_id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Using cached historical data for item {item_id}")
            return [HistoricalDataPoint.from_api_response(dp) for dp in cached_data]
        
        url = f"{self.BASE_URL}/history/{game}/{filter_type}"
        params = {
            'id': str(item_id),
            'lang': 'en'
        }
        
        try:
            async with self._rate_limiter:
                logger.info(f"Fetching historical data for item {item_id} from WeirdGloop API")
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if not data.get('success', True) and 'error' in data:
                            logger.warning(f"API returned error for item {item_id}: {data['error']}")
                            return []
                        
                        # Handle response format - could be array or object
                        if isinstance(data, list):
                            raw_points = data
                        elif isinstance(data, dict) and 'data' in data:
                            raw_points = data['data']
                        else:
                            logger.warning(f"Unexpected response format for item {item_id}: {type(data)}")
                            return []
                        
                        if not raw_points:
                            logger.info(f"No historical data available for item {item_id}")
                            return []
                        
                        # Convert to data points
                        data_points = []
                        for point in raw_points:
                            try:
                                if isinstance(point, dict) and 'price' in point and 'timestamp' in point:
                                    data_points.append(HistoricalDataPoint.from_api_response(point))
                                elif isinstance(point, list) and len(point) >= 2:
                                    # Handle array format [timestamp, price, volume?]
                                    timestamp_ms = point[0]
                                    price = point[1]
                                    volume = point[2] if len(point) > 2 else None
                                    
                                    data_points.append(HistoricalDataPoint(
                                        price=int(price),
                                        volume=volume,
                                        timestamp=datetime.fromtimestamp(
                                            timestamp_ms / 1000, 
                                            tz=timezone.utc
                                        )
                                    ))
                            except (ValueError, KeyError, IndexError) as e:
                                logger.warning(f"Skipping malformed data point for item {item_id}: {point} - {e}")
                                continue
                        
                        # Cache successful results for 1 hour
                        if data_points:
                            cache.set(cache_key, raw_points, 3600)
                            logger.info(f"Fetched {len(data_points)} historical data points for item {item_id}")
                        
                        return data_points
                    
                    elif response.status == 429:
                        logger.warning(f"Rate limited by WeirdGloop API for item {item_id}")
                        # Wait and retry once
                        await asyncio.sleep(60)
                        return await self.get_historical_data(item_id, game, filter_type)
                    
                    else:
                        logger.error(f"HTTP {response.status} error fetching data for item {item_id}")
                        return []
        
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching historical data for item {item_id}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching historical data for item {item_id}: {e}")
            return []
    
    async def get_bulk_historical_data(self, 
                                     item_ids: List[int], 
                                     game: str = 'osrs',
                                     filter_type: str = 'all',
                                     batch_size: int = 10) -> Dict[int, List[HistoricalDataPoint]]:
        """
        Fetch historical data for multiple items efficiently.
        
        Args:
            item_ids: List of OSRS item IDs
            game: Game type (osrs or rs)
            filter_type: Data filter type
            batch_size: Number of items to request in parallel
            
        Returns:
            Dictionary mapping item_id to list of historical data points
        """
        if not self.session:
            raise RuntimeError("Client must be used as async context manager")
        
        results = {}
        
        # Process in batches to respect rate limits
        for i in range(0, len(item_ids), batch_size):
            batch = item_ids[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} of {(len(item_ids) + batch_size - 1)//batch_size}")
            
            # Create tasks for concurrent requests
            tasks = []
            for item_id in batch:
                task = self.get_historical_data(item_id, game, filter_type)
                tasks.append((item_id, task))
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )
            
            # Process results
            for (item_id, _), result in zip(tasks, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching data for item {item_id}: {result}")
                    results[item_id] = []
                else:
                    results[item_id] = result
            
            # Rate limiting delay between batches
            if i + batch_size < len(item_ids):
                await asyncio.sleep(1)  # 1 second between batches
        
        logger.info(f"Bulk fetch completed: {len([r for r in results.values() if r])} items with data")
        return results
    
    async def get_item_info(self, item_id: int, game: str = 'osrs') -> Optional[Dict]:
        """
        Get basic item information from the API.
        
        Args:
            item_id: OSRS item ID
            game: Game type
            
        Returns:
            Item information dict or None
        """
        if not self.session:
            raise RuntimeError("Client must be used as async context manager")
        
        cache_key = f"weirdgloop_item_{game}_{item_id}"
        cached_info = cache.get(cache_key)
        if cached_info:
            return cached_info
        
        # Use the mapping endpoint to get item info
        url = f"{self.BASE_URL}/mapping/{game}"
        params = {
            'id': str(item_id),
            'lang': 'en'
        }
        
        try:
            async with self._rate_limiter:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Cache for 24 hours (item info doesn't change often)
                        if data:
                            cache.set(cache_key, data, 86400)
                        
                        return data
                    else:
                        logger.warning(f"Failed to get item info for {item_id}: HTTP {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"Error getting item info for {item_id}: {e}")
            return None
    
    @staticmethod
    def get_data_quality_score(data_points: List[HistoricalDataPoint]) -> float:
        """
        Calculate data quality score based on historical data characteristics.
        
        Args:
            data_points: List of historical data points
            
        Returns:
            Quality score from 0.0 to 1.0
        """
        if not data_points:
            return 0.0
        
        # Factors contributing to quality score
        data_count = len(data_points)
        
        # Time span coverage
        if data_count > 1:
            time_span_days = (data_points[-1].timestamp - data_points[0].timestamp).days
            time_coverage_score = min(1.0, time_span_days / 90)  # 90 days = perfect
        else:
            time_coverage_score = 0.1
        
        # Data density (more points = better)
        density_score = min(1.0, data_count / 100)  # 100 points = perfect
        
        # Volume data availability
        volume_points = sum(1 for dp in data_points if dp.volume is not None)
        volume_score = volume_points / data_count if data_count > 0 else 0
        
        # Weighted combination
        quality_score = (
            time_coverage_score * 0.4 +
            density_score * 0.4 +
            volume_score * 0.2
        )
        
        return round(quality_score, 3)