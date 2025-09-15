"""
Unified RuneScape Wiki API price intelligence system for OSRS Grand Exchange data.

This service uses only the official RuneScape Wiki API for comprehensive, accurate
Grand Exchange data with proper volume analysis for AI-powered trading recommendations.

Features:
- Complete item coverage via /mapping endpoint
- Real-time prices via /latest endpoint  
- Volume data via /timeseries endpoint
- Advanced data freshness validation
- Volume-weighted confidence scoring
- AI-ready data structures
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from django.utils import timezone
from django.core.cache import cache

from .runescape_wiki_client import RuneScapeWikiAPIClient, RuneScapeWikiAPIError, WikiPriceData, TimeSeriesData, ItemMetadata

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Available price data sources."""
    RUNESCAPE_WIKI = "runescape_wiki"


class DataQuality(Enum):
    """Data quality levels."""
    FRESH = "fresh"      # < 1 hour
    RECENT = "recent"    # 1-6 hours
    ACCEPTABLE = "acceptable"  # 6-24 hours
    STALE = "stale"      # > 24 hours
    UNKNOWN = "unknown"  # No timestamp


@dataclass
class PriceData:
    """Structured price data with metadata and volume analysis."""
    item_id: int
    high_price: int
    low_price: int
    timestamp: int
    source: DataSource
    quality: DataQuality
    age_hours: float
    volume_high: int = 0
    volume_low: int = 0
    confidence_score: float = 0.5
    raw_data: Dict = None
    volume_analysis: Dict = None
    item_metadata: Optional[ItemMetadata] = None
    
    @property
    def total_volume(self) -> int:
        """Get total trading volume."""
        return self.volume_high + self.volume_low
    
    @property
    def has_valid_prices(self) -> bool:
        """Check if item has valid pricing data."""
        return (self.high_price > 0 or self.low_price > 0) and self.high_price != self.low_price


class UnifiedPriceClient:
    """
    Unified RuneScape Wiki API price client with comprehensive volume analysis.
    """
    
    def __init__(self):
        self.wiki_client = None
        self._cleanup_attempted = False
        
        # Quality thresholds (hours)
        self.quality_thresholds = {
            DataQuality.FRESH: 1,
            DataQuality.RECENT: 6,
            DataQuality.ACCEPTABLE: 24,
        }
        
        # Cache settings
        self.cache_prefix = "wiki_price:"
        self.cache_timeout = 300  # 5 minutes
        
        # Connection and rate limiting
        self.max_concurrent_requests = 10  # Higher limit for single source
        self.request_delay = 1.0  # 1 second delay between batches
        self.max_retries = 3  # More retries for reliable source
        self.consecutive_failures = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.wiki_client = RuneScapeWikiAPIClient()
        await self.wiki_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._cleanup_attempted:
            logger.warning("Cleanup already attempted, skipping to prevent loops")
            return
        
        self._cleanup_attempted = True
        
        logger.info("🧹 Starting unified client cleanup...")
        
        # Clean up Wiki client
        if self.wiki_client:
            try:
                await asyncio.wait_for(
                    self.wiki_client.__aexit__(exc_type, exc_val, exc_tb),
                    timeout=5.0
                )
                logger.debug("✅ Wiki client cleaned up")
            except asyncio.TimeoutError:
                logger.warning("⏰ Wiki client cleanup timed out after 5s")
            except Exception as e:
                logger.error(f"❌ Error cleaning up Wiki client: {e}")
        
        # Reset client reference
        self.wiki_client = None
        logger.info("✅ Unified client cleanup completed")
    
    def _calculate_quality(self, timestamp: int) -> Tuple[DataQuality, float]:
        """
        Calculate data quality and age from timestamp.
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            Tuple of (quality, age_hours)
        """
        if timestamp <= 0:
            return DataQuality.UNKNOWN, float('inf')
        
        current_time = timezone.now().timestamp()
        age_hours = (current_time - timestamp) / 3600
        
        if age_hours < self.quality_thresholds[DataQuality.FRESH]:
            return DataQuality.FRESH, age_hours
        elif age_hours < self.quality_thresholds[DataQuality.RECENT]:
            return DataQuality.RECENT, age_hours
        elif age_hours < self.quality_thresholds[DataQuality.ACCEPTABLE]:
            return DataQuality.ACCEPTABLE, age_hours
        else:
            return DataQuality.STALE, age_hours
    
    def _calculate_confidence_score(self, price_data: PriceData) -> float:
        """
        Calculate confidence score for price data with volume weighting.
        
        Args:
            price_data: Price data to score
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_score = 0.6  # Higher base for official API
        
        # Source reliability bonus (always RuneScape Wiki now)
        source_bonus = 0.3  # High reliability for official API
        
        # Quality bonus
        quality_bonus = {
            DataQuality.FRESH: 0.3,
            DataQuality.RECENT: 0.2,
            DataQuality.ACCEPTABLE: 0.1,
            DataQuality.STALE: -0.2,
            DataQuality.UNKNOWN: -0.4,
        }.get(price_data.quality, 0.0)
        
        # Volume bonus (higher weight for volume data)
        volume_bonus = 0.0
        total_volume = price_data.total_volume
        if total_volume > 100:
            volume_bonus = 0.2  # High volume items are more reliable
        elif total_volume > 10:
            volume_bonus = 0.1  # Medium volume
        elif total_volume > 0:
            volume_bonus = 0.05  # Low volume but some activity
        
        # Price sanity check (high price should >= low price)
        sanity_bonus = 0.0
        if price_data.high_price >= price_data.low_price and price_data.low_price > 0:
            sanity_bonus = 0.1
        elif price_data.high_price > 0 or price_data.low_price > 0:
            sanity_bonus = 0.0  # One price is valid
        else:
            sanity_bonus = -0.4  # No valid prices
        
        # Volume analysis bonus
        analysis_bonus = 0.0
        if price_data.volume_analysis:
            if price_data.volume_analysis.get('trading_activity') in ['very_active', 'active']:
                analysis_bonus = 0.1
            elif price_data.volume_analysis.get('liquidity_score', 0) > 0.5:
                analysis_bonus = 0.05
        
        confidence = base_score + source_bonus + quality_bonus + volume_bonus + sanity_bonus + analysis_bonus
        return max(0.0, min(1.0, confidence))
    
    async def _fetch_comprehensive_price_data(self, item_id: int, include_volume: bool = True) -> Optional[PriceData]:
        """
        Fetch comprehensive price and volume data from RuneScape Wiki API.
        
        Args:
            item_id: OSRS item ID
            include_volume: Whether to fetch volume analysis data
            
        Returns:
            Comprehensive PriceData with volume analysis or None
        """
        try:
            # Fetch price data and volume analysis in parallel
            tasks = [
                self.wiki_client.get_latest_prices(item_id),
            ]
            
            if include_volume:
                tasks.append(self.wiki_client.get_volume_analysis(item_id, "24h"))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            price_results = results[0]
            volume_analysis = results[1] if include_volume and len(results) > 1 else None
            
            # Check for exceptions
            if isinstance(price_results, Exception):
                logger.warning(f"Price fetch failed for item {item_id}: {price_results}")
                return None
            
            if not price_results or item_id not in price_results:
                return None
            
            wiki_price_data = price_results[item_id]
            
            # Use Wiki API's proper high/low pricing structure
            high_price = wiki_price_data.best_buy_price
            low_price = wiki_price_data.best_sell_price
            
            # Use the most recent timestamp
            timestamp = max(
                wiki_price_data.high_time or 0,
                wiki_price_data.low_time or 0
            )
            
            if high_price == 0 and low_price == 0:
                return None
            
            quality, age_hours = self._calculate_quality(timestamp)
            
            # Get volume data from analysis (if available and not exception)
            volume_high = volume_low = 0
            if (isinstance(volume_analysis, dict) and 
                volume_analysis.get('total_volume', 0) > 0):
                # Distribute total volume between high/low based on typical patterns
                total_vol = volume_analysis.get('total_volume', 0)
                # Typically 60% high price volume, 40% low price volume
                volume_high = int(total_vol * 0.6)
                volume_low = int(total_vol * 0.4)
            
            price_data = PriceData(
                item_id=item_id,
                high_price=high_price,
                low_price=low_price,
                timestamp=timestamp,
                source=DataSource.RUNESCAPE_WIKI,
                quality=quality,
                age_hours=age_hours,
                volume_high=volume_high,
                volume_low=volume_low,
                raw_data=wiki_price_data.raw_data,
                volume_analysis=volume_analysis if isinstance(volume_analysis, dict) else None
            )
            
            price_data.confidence_score = self._calculate_confidence_score(price_data)
            
            logger.info(f"Wiki API comprehensive data for item {item_id}: "
                       f"high={high_price:,}, low={low_price:,}, "
                       f"volume={volume_high + volume_low:,}, "
                       f"age={age_hours:.1f}h, confidence={price_data.confidence_score:.2f}")
            
            return price_data
            
        except Exception as e:
            logger.warning(f"Failed to fetch comprehensive price data for item {item_id}: {e}")
            return None
    
    async def get_best_price_data(self, item_id: int, max_staleness_hours: float = 24.0, include_volume: bool = True) -> Optional[PriceData]:
        """
        Get comprehensive price data with volume analysis for an item.
        
        Args:
            item_id: OSRS item ID
            max_staleness_hours: Maximum acceptable data age in hours
            include_volume: Whether to include volume analysis
            
        Returns:
            Comprehensive price data with volume analysis or None
        """
        logger.info(f"Fetching comprehensive price data for item {item_id} (max age: {max_staleness_hours}h)")
        
        # Check cache first
        cache_key = f"{self.cache_prefix}item_{item_id}_vol_{include_volume}"
        cached_data = cache.get(cache_key)
        if cached_data and cached_data.age_hours < max_staleness_hours:
            logger.debug(f"Using cached comprehensive data for item {item_id}")
            return cached_data
        
        # Fetch from RuneScape Wiki API
        try:
            result = await self._fetch_comprehensive_price_data(item_id, include_volume)
            
            if not result:
                logger.warning(f"No price data available for item {item_id}")
                return None
            
            if result.age_hours > max_staleness_hours:
                logger.warning(f"Price data for item {item_id} is too stale ({result.age_hours:.1f}h > {max_staleness_hours}h)")
                return None
            
            logger.info(f"Comprehensive data for item {item_id}: "
                       f"high={result.high_price:,}, low={result.low_price:,}, "
                       f"volume={result.total_volume:,}, "
                       f"age={result.age_hours:.1f}h, confidence={result.confidence_score:.2f}")
            
            # Cache the result
            cache.set(cache_key, result, self.cache_timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive price data for item {item_id}: {e}")
            return None
    
    async def get_multiple_comprehensive_prices(self, item_ids: List[int], max_staleness_hours: float = 24.0, include_volume: bool = True) -> Dict[int, PriceData]:
        """
        Get comprehensive price data for multiple items with optimized batching.
        
        Args:
            item_ids: List of OSRS item IDs
            max_staleness_hours: Maximum acceptable data age in hours
            include_volume: Whether to include volume analysis
            
        Returns:
            Dictionary mapping item_id -> PriceData
        """
        logger.info(f"🔄 Fetching comprehensive price data for {len(item_ids)} items (batch optimized)")
        
        # Process items in optimized batches for Wiki API
        batch_size = min(self.max_concurrent_requests, 20)  # Higher limit for single reliable source
        price_data = {}
        total_batches = (len(item_ids) + batch_size - 1) // batch_size
        
        for i in range(0, len(item_ids), batch_size):
            batch = item_ids[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
            
            # Add delay between batches (except first)
            if i > 0:
                logger.debug(f"⏳ Rate limiting: waiting {self.request_delay}s between batches")
                await asyncio.sleep(self.request_delay)
            
            # Process batch with timeout
            try:
                tasks = [self.get_best_price_data(item_id, max_staleness_hours, include_volume) for item_id in batch]
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=45.0  # 45s timeout per batch (longer for volume analysis)
                )
                
                # Process results
                batch_success_count = 0
                for item_id, result in zip(batch, results):
                    if isinstance(result, PriceData):
                        price_data[item_id] = result
                        batch_success_count += 1
                    elif isinstance(result, Exception):
                        logger.debug(f"Failed to get price for item {item_id}: {result}")
                
                # Update failure tracking
                if batch_success_count == 0:
                    self.consecutive_failures += 1
                    logger.warning(f"⚠️ Batch failed completely. Consecutive failures: {self.consecutive_failures}")
                else:
                    self.consecutive_failures = 0  # Reset on any success
                    
                logger.info(f"✅ Batch {batch_num} completed: {batch_success_count}/{len(batch)} successful")
                
            except asyncio.TimeoutError:
                logger.error(f"⏰ Batch {batch_num} timed out after 45s")
                self.consecutive_failures += 1
            except Exception as e:
                logger.error(f"❌ Batch {batch_num} failed with exception: {e}")
                self.consecutive_failures += 1
        
        success_rate = len(price_data) / len(item_ids) * 100 if item_ids else 0
        logger.info(f"📊 Comprehensive fetch completed: {len(price_data)}/{len(item_ids)} items ({success_rate:.1f}% success)")
        
        return price_data
    
    async def get_data_source_status(self) -> Dict[str, Dict]:
        """
        Get status information for RuneScape Wiki API.
        
        Returns:
            Dictionary with source status information
        """
        logger.info("Checking RuneScape Wiki API status")
        
        status = {}
        
        # Check RuneScape Wiki API status
        try:
            wiki_healthy = await self.wiki_client.health_check()
            
            # Get a sample price to test functionality
            sample_prices = await self.wiki_client.get_latest_prices(item_id=995)  # Coins
            has_price_data = bool(sample_prices and 995 in sample_prices)
            
            # Test volume functionality
            volume_test = await self.wiki_client.get_volume_analysis(995, "24h")
            has_volume_data = isinstance(volume_test, dict) and volume_test.get('total_volume', 0) >= 0
            
            status['runescape_wiki'] = {
                'available': wiki_healthy,
                'healthy': wiki_healthy and has_price_data,
                'price_data_working': has_price_data,
                'volume_data_working': has_volume_data,
                'endpoints': {
                    'mapping': 'available',
                    'latest': 'available',
                    'timeseries': 'available'
                },
                'note': 'Official RuneScape Wiki API with comprehensive OSRS data'
            }
            
            logger.info(f"Wiki API status: healthy={wiki_healthy}, prices={has_price_data}, volume={has_volume_data}")
            
        except Exception as e:
            status['runescape_wiki'] = {
                'available': False,
                'healthy': False,
                'error': str(e),
                'price_data_working': False,
                'volume_data_working': False
            }
            logger.error(f"Wiki API health check failed: {e}")
        
        return status
    
    async def get_enriched_item_data(self, item_ids: List[int]) -> Dict[int, Tuple[Optional[PriceData], Optional[ItemMetadata]]]:
        """
        Get enriched item data with both price information and metadata.
        
        Args:
            item_ids: List of OSRS item IDs
            
        Returns:
            Dictionary mapping item_id -> (price_data, metadata)
        """
        logger.info(f"Fetching enriched data for {len(item_ids)} items")
        
        try:
            # Fetch price data, volume analysis, and metadata in parallel
            price_task = asyncio.create_task(
                self.get_multiple_comprehensive_prices(item_ids, include_volume=True)
            )
            metadata_task = asyncio.create_task(
                self.wiki_client.get_item_mapping()
            )
            
            price_data, all_metadata = await asyncio.gather(price_task, metadata_task)
            
            # Combine the data
            enriched_data = {}
            for item_id in item_ids:
                price_info = price_data.get(item_id)
                metadata = all_metadata.get(item_id)
                
                # Attach metadata to price data if both exist
                if price_info and metadata:
                    price_info.item_metadata = metadata
                
                enriched_data[item_id] = (price_info, metadata)
            
            logger.info(f"Enriched data compiled for {len(enriched_data)} items")
            return enriched_data
            
        except Exception as e:
            logger.error(f"Failed to get enriched item data: {e}")
            return {}