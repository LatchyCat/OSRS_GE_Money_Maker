"""
Unified Data Ingestion Service for OSRS Trading Data

This service orchestrates the complete data pipeline using the RuneScape Wiki API:
1. /mapping - Gets all item metadata (names, IDs, high alch values, etc.)
2. /latest - Gets latest prices for all items
3. /timeseries - Gets volume data for AI-powered confidence scoring

The service matches items → prices → volume data and provides a complete
data foundation for AI-powered trading recommendations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from django.db import transaction, IntegrityError
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings

from .unified_wiki_price_client import UnifiedPriceClient, PriceData
from .runescape_wiki_client import RuneScapeWikiAPIClient, ItemMetadata, TimeSeriesData, HistoricalPriceData
from apps.items.models import Item
from apps.prices.models import PriceSnapshot, HistoricalPricePoint

logger = logging.getLogger(__name__)


class IngestionPriority(Enum):
    """Ingestion priority levels."""
    CRITICAL = "critical"    # High-value items, popular trading items
    HIGH = "high"           # Members items, decent volume
    NORMAL = "normal"       # Regular items
    LOW = "low"             # Low volume, niche items
    SKIP = "skip"           # Invalid/untradeable items


@dataclass
class ItemDataPackage:
    """Complete data package for a single item with historical price data."""
    # Core item data
    item_id: int
    metadata: Optional[ItemMetadata] = None
    price_data: Optional[PriceData] = None
    volume_analysis: Optional[Dict] = None
    
    # Historical price data
    historical_5m: List[HistoricalPriceData] = field(default_factory=list)
    historical_1h: List[HistoricalPriceData] = field(default_factory=list)
    
    # Processing metadata
    priority: IngestionPriority = IngestionPriority.NORMAL
    processing_time: Optional[datetime] = None
    error_messages: List[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        """Check if data package has all required components."""
        return (
            self.metadata is not None and 
            self.price_data is not None and
            self.volume_analysis is not None
        )
    
    @property
    def has_historical_data(self) -> bool:
        """Check if package has historical price data."""
        return len(self.historical_5m) > 0 or len(self.historical_1h) > 0
    
    @property
    def has_valid_price_data(self) -> bool:
        """Check if price data is valid and recent."""
        if not self.price_data:
            return False
        return (
            self.price_data.has_valid_prices and 
            self.price_data.age_hours < 48  # Within 48 hours
        )
    
    @property
    def confidence_score(self) -> float:
        """Get overall confidence score for this data package."""
        if not self.is_complete:
            return 0.0
        
        base_score = 0.5
        
        # Price data confidence
        if self.price_data and self.price_data.confidence_score:
            base_score += self.price_data.confidence_score * 0.4
        
        # Volume data quality
        if self.volume_analysis:
            activity_level = self.volume_analysis.get('trading_activity', 'inactive')
            activity_bonus = {
                'very_active': 0.3,
                'active': 0.2,
                'moderate': 0.1,
                'low': 0.05,
                'inactive': 0.0
            }.get(activity_level, 0.0)
            base_score += activity_bonus
        
        # Metadata completeness
        if self.metadata and self.metadata.examine:
            base_score += 0.1  # Bonus for complete metadata
        
        return min(1.0, base_score)


class UnifiedDataIngestionService:
    """
    Unified service for ingesting complete OSRS trading data from RuneScape Wiki API.
    """
    
    def __init__(self):
        self.wiki_client = None
        self.unified_client = None
        
        # Processing configuration
        self.batch_size = 100  # Items per batch
        self.max_concurrent_items = 50  # Max concurrent processing
        self.cache_timeout = 3600  # 1 hour
        self.volume_analysis_timeout = 30  # 30s per volume analysis
        
        # Historical data configuration
        self.include_historical_5m = True  # Include 5-minute historical data
        self.include_historical_1h = True  # Include 1-hour historical data
        self.max_historical_points = 24  # Maximum historical data points per interval
        self.historical_data_timeout = 45  # 45s timeout for historical data
        
        # Priority item sets (will be loaded from settings/cache)
        self.critical_items = set()
        self.high_priority_items = set()
        self.skip_items = set()
        
        # Statistics tracking
        self.stats = {
            'total_items': 0,
            'successful_ingestions': 0,
            'failed_ingestions': 0,
            'skipped_items': 0,
            'processing_time': 0.0
        }
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.wiki_client = RuneScapeWikiAPIClient()
        self.unified_client = UnifiedPriceClient()
        
        await self.wiki_client.__aenter__()
        await self.unified_client.__aenter__()
        
        # Load priority item lists
        await self._load_priority_items()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.unified_client:
            await self.unified_client.__aexit__(exc_type, exc_val, exc_tb)
        if self.wiki_client:
            await self.wiki_client.__aexit__(exc_type, exc_val, exc_tb)
            
        # Log final statistics
        self._log_ingestion_stats()
    
    async def _load_priority_items(self):
        """Load priority item configurations."""
        try:
            # Critical items - always process first (high-value, popular items)
            self.critical_items = {
                13190,  # Old School Bond
                995,    # Coins
                4151,   # Abyssal Whip
                11802,  # Dragon Claws
                # Add more high-value items
            }
            
            # High priority items - members items, decent volume
            existing_items = await asyncio.to_thread(
                Item.objects.filter(members=True, is_active=True).values_list,
                'item_id', flat=True
            )
            self.high_priority_items = set(existing_items)
            
            # Skip items - untradeable, invalid items
            self.skip_items = {0, -1}  # Invalid IDs
            
            logger.info(f"Loaded priority items: {len(self.critical_items)} critical, "
                       f"{len(self.high_priority_items)} high priority, "
                       f"{len(self.skip_items)} skip")
                       
        except Exception as e:
            logger.warning(f"Failed to load priority items: {e}")
    
    def _determine_priority(self, item_id: int, metadata: Optional[ItemMetadata] = None) -> IngestionPriority:
        """Determine processing priority for an item."""
        if item_id in self.skip_items:
            return IngestionPriority.SKIP
        
        if item_id in self.critical_items:
            return IngestionPriority.CRITICAL
        
        if item_id in self.high_priority_items:
            return IngestionPriority.HIGH
        
        if metadata:
            # High-value items get higher priority
            if metadata.highalch > 100000:  # 100K+ alch value
                return IngestionPriority.HIGH
            
            # Members items get higher priority
            if metadata.members:
                return IngestionPriority.HIGH
        
        return IngestionPriority.NORMAL
    
    async def ingest_complete_market_data(self, 
                                       item_ids: Optional[List[int]] = None,
                                       include_historical: bool = True,
                                       historical_periods_5m: int = 12,  # Last 12x5m = 1 hour
                                       historical_periods_1h: int = 24   # Last 24x1h = 24 hours
                                      ) -> Dict[str, Any]:
        """
        Ingest complete market data for all or specified items including historical price data.
        
        Args:
            item_ids: Specific item IDs to ingest, or None for all items
            include_historical: Whether to include historical price data
            historical_periods_5m: Number of 5-minute periods to fetch
            historical_periods_1h: Number of 1-hour periods to fetch
            
        Returns:
            Dictionary with ingestion results and statistics
        """
        start_time = datetime.now()
        logger.info("🚀 Starting unified data ingestion process")
        
        try:
            # Step 1: Get all item metadata from /mapping endpoint
            logger.info("📋 Fetching item mapping data...")
            all_metadata = await self.wiki_client.get_item_mapping()
            
            if not all_metadata:
                raise Exception("Failed to fetch item mapping data")
            
            # Filter to specific items if provided
            if item_ids:
                filtered_metadata = {
                    item_id: metadata for item_id, metadata in all_metadata.items()
                    if item_id in item_ids
                }
                all_metadata = filtered_metadata
            
            logger.info(f"📊 Processing {len(all_metadata)} items")
            
            # Step 2: Create data packages with priority sorting
            data_packages = []
            for item_id, metadata in all_metadata.items():
                priority = self._determine_priority(item_id, metadata)
                if priority == IngestionPriority.SKIP:
                    self.stats['skipped_items'] += 1
                    continue
                
                package = ItemDataPackage(
                    item_id=item_id,
                    metadata=metadata,
                    priority=priority
                )
                data_packages.append(package)
            
            # Sort by priority
            data_packages.sort(key=lambda x: {
                IngestionPriority.CRITICAL: 0,
                IngestionPriority.HIGH: 1,
                IngestionPriority.NORMAL: 2,
                IngestionPriority.LOW: 3
            }[x.priority])
            
            # Step 3: Fetch historical price data if requested
            historical_data_5m = {}
            historical_data_1h = {}
            
            if include_historical:
                logger.info("📈 Fetching historical price data...")
                
                # Fetch historical data in parallel
                historical_tasks = []
                
                if self.include_historical_5m:
                    historical_tasks.append(
                        self._fetch_historical_data_with_periods('5m', historical_periods_5m)
                    )
                
                if self.include_historical_1h:
                    historical_tasks.append(
                        self._fetch_historical_data_with_periods('1h', historical_periods_1h)
                    )
                
                if historical_tasks:
                    historical_results = await asyncio.gather(*historical_tasks, return_exceptions=True)
                    
                    for i, result in enumerate(historical_results):
                        if isinstance(result, Exception):
                            logger.warning(f"Historical data fetch {i} failed: {result}")
                        elif i == 0 and self.include_historical_5m:
                            historical_data_5m = result
                        elif (i == 1 and self.include_historical_1h) or (i == 0 and not self.include_historical_5m):
                            historical_data_1h = result
                
                # Integrate historical data into packages
                await self._integrate_historical_data_into_packages(
                    data_packages, historical_data_5m, historical_data_1h
                )
            
            # Step 4: Process data packages in batches
            self.stats['total_items'] = len(data_packages)
            logger.info(f"⚡ Processing {len(data_packages)} items in priority order")
            
            processed_packages = await self._process_data_packages_in_batches(data_packages)
            
            # Step 4: Save to database
            logger.info("💾 Saving data to database...")
            save_results = await self._save_packages_to_database(processed_packages)
            
            # Step 5: Calculate final statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats['processing_time'] = processing_time
            
            success_rate = (self.stats['successful_ingestions'] / self.stats['total_items'] * 100) if self.stats['total_items'] > 0 else 0
            
            results = {
                'status': 'completed',
                'statistics': self.stats.copy(),
                'save_results': save_results,
                'success_rate_percent': round(success_rate, 2),
                'processing_time_minutes': round(processing_time / 60, 2),
                'items_per_minute': round(self.stats['total_items'] / (processing_time / 60), 2) if processing_time > 0 else 0
            }
            
            logger.info(f"✅ Data ingestion completed: {success_rate:.1f}% success rate, "
                       f"{processing_time:.1f}s total time")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Data ingestion failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'statistics': self.stats.copy()
            }
    
    async def _process_data_packages_in_batches(self, data_packages: List[ItemDataPackage]) -> List[ItemDataPackage]:
        """Process data packages in optimized batches."""
        processed_packages = []
        
        for i in range(0, len(data_packages), self.batch_size):
            batch = data_packages[i:i+self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(data_packages) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
            
            # Process batch with concurrency control
            batch_results = await self._process_batch_with_concurrency_control(batch)
            processed_packages.extend(batch_results)
            
            # Add small delay between batches to be respectful to API
            if i + self.batch_size < len(data_packages):
                await asyncio.sleep(1.0)
        
        return processed_packages
    
    async def _process_batch_with_concurrency_control(self, batch: List[ItemDataPackage]) -> List[ItemDataPackage]:
        """Process a batch of data packages with concurrency control."""
        semaphore = asyncio.Semaphore(self.max_concurrent_items)
        
        async def process_single_package(package: ItemDataPackage) -> ItemDataPackage:
            async with semaphore:
                return await self._process_single_data_package(package)
        
        # Process all packages in parallel with concurrency limit
        tasks = [process_single_package(package) for package in batch]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_data_package(self, package: ItemDataPackage) -> ItemDataPackage:
        """Process a single data package to completion."""
        package.processing_time = datetime.now()
        
        try:
            # Step 1: Get comprehensive price data (includes basic volume info)
            price_data = await self.unified_client.get_best_price_data(
                package.item_id, 
                max_staleness_hours=48.0,
                include_volume=True
            )
            
            if price_data:
                package.price_data = price_data
                
                # Use volume analysis from price data if available
                if price_data.volume_analysis:
                    package.volume_analysis = price_data.volume_analysis
                else:
                    # Step 2: Get detailed volume analysis if not included
                    try:
                        volume_analysis = await asyncio.wait_for(
                            self.wiki_client.get_volume_analysis(package.item_id, "24h"),
                            timeout=self.volume_analysis_timeout
                        )
                        package.volume_analysis = volume_analysis
                    except asyncio.TimeoutError:
                        logger.debug(f"Volume analysis timeout for item {package.item_id}")
                        package.volume_analysis = {'error': 'timeout'}
                    except Exception as e:
                        logger.debug(f"Volume analysis failed for item {package.item_id}: {e}")
                        package.volume_analysis = {'error': str(e)}
                
                self.stats['successful_ingestions'] += 1
            else:
                package.error_messages.append("No price data available")
                self.stats['failed_ingestions'] += 1
                
        except Exception as e:
            package.error_messages.append(f"Processing failed: {str(e)}")
            self.stats['failed_ingestions'] += 1
            logger.debug(f"Failed to process item {package.item_id}: {e}")
        
        return package
    
    async def _fetch_historical_data_with_periods(self, interval: str, periods: int) -> Dict[int, List[HistoricalPriceData]]:
        """
        Fetch historical price data for specified interval and periods.
        
        Args:
            interval: '5m' or '1h'
            periods: Number of periods to fetch
            
        Returns:
            Dictionary mapping item_id -> List[HistoricalPriceData]
        """
        logger.info(f"📊 Fetching {periods} periods of {interval} historical data")
        
        historical_data = {}
        
        try:
            # Generate timestamps for the requested periods
            now = datetime.now()
            timestamps = []
            
            if interval == '5m':
                # Generate 5-minute intervals
                for i in range(periods):
                    timestamp = now - timedelta(minutes=5 * i)
                    # Round to 5-minute boundary
                    timestamp = timestamp.replace(minute=timestamp.minute // 5 * 5, second=0, microsecond=0)
                    timestamps.append(int(timestamp.timestamp()))
            elif interval == '1h':
                # Generate 1-hour intervals
                for i in range(periods):
                    timestamp = now - timedelta(hours=i)
                    # Round to hour boundary
                    timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
                    timestamps.append(int(timestamp.timestamp()))
            
            # Fetch latest data point (current)
            if interval == '5m':
                latest_data = await self.wiki_client.get_historical_prices_5m()
            else:
                latest_data = await self.wiki_client.get_historical_prices_1h()
            
            # Convert to the expected format
            for item_id, price_data in latest_data.items():
                if item_id not in historical_data:
                    historical_data[item_id] = []
                historical_data[item_id].append(price_data)
            
            # Optionally fetch additional historical points with specific timestamps
            # (This would require API support for historical timestamps)
            
            logger.info(f"Retrieved {interval} data for {len(historical_data)} items")
            return historical_data
            
        except Exception as e:
            logger.error(f"Failed to fetch {interval} historical data: {e}")
            return {}
    
    async def _integrate_historical_data_into_packages(self, 
                                                      packages: List[ItemDataPackage],
                                                      data_5m: Dict[int, List[HistoricalPriceData]],
                                                      data_1h: Dict[int, List[HistoricalPriceData]]):
        """
        Integrate fetched historical data into item data packages.
        
        Args:
            packages: List of ItemDataPackage objects
            data_5m: 5-minute historical data
            data_1h: 1-hour historical data
        """
        logger.info("🔗 Integrating historical data into packages")
        
        integrated_count = 0
        
        for package in packages:
            # Add 5-minute historical data
            if package.item_id in data_5m:
                package.historical_5m.extend(data_5m[package.item_id])
            
            # Add 1-hour historical data  
            if package.item_id in data_1h:
                package.historical_1h.extend(data_1h[package.item_id])
            
            # Count packages with historical data
            if package.has_historical_data:
                integrated_count += 1
        
        logger.info(f"Integrated historical data for {integrated_count}/{len(packages)} packages")
    
    async def _save_packages_to_database(self, packages: List[ItemDataPackage]) -> Dict[str, int]:
        """Save processed packages to database."""
        def save_batch():
            items_created = 0
            items_updated = 0
            prices_created = 0
            historical_points_created = 0
            
            with transaction.atomic():
                for package in packages:
                    if not package.metadata:
                        continue
                    
                    try:
                        # Update or create Item
                        item, created = Item.objects.update_or_create(
                            item_id=package.item_id,
                            defaults={
                                'name': package.metadata.name,
                                'examine': package.metadata.examine,
                                'icon': package.metadata.icon,
                                'value': package.metadata.value,
                                'high_alch': package.metadata.highalch,
                                'low_alch': package.metadata.lowalch,
                                'limit': package.metadata.limit,
                                'members': package.metadata.members,
                                'is_active': True,
                                'updated_at': timezone.now()
                            }
                        )
                        
                        if created:
                            items_created += 1
                        else:
                            items_updated += 1
                        
                        # Create PriceSnapshot if we have valid price data
                        if package.has_valid_price_data:
                            price_data = package.price_data
                            
                            # Convert timestamps
                            high_time = datetime.fromtimestamp(price_data.timestamp, tz=timezone.get_current_timezone()) if price_data.timestamp > 0 else None
                            low_time = high_time  # Same timestamp for both in latest API
                            
                            # Calculate volume metrics
                            total_volume = price_data.volume_high + price_data.volume_low
                            
                            # Calculate volatility from volume analysis
                            price_volatility = None
                            if package.volume_analysis and isinstance(package.volume_analysis, dict):
                                price_volatility = package.volume_analysis.get('price_stability', 0.0)
                            
                            PriceSnapshot.objects.create(
                                item=item,
                                high_price=price_data.high_price,
                                high_time=high_time,
                                low_price=price_data.low_price,
                                low_time=low_time,
                                high_price_volume=price_data.volume_high,
                                low_price_volume=price_data.volume_low,
                                total_volume=total_volume,
                                price_volatility=price_volatility,
                                api_source='runescape_wiki',
                                data_interval='latest'
                            )
                            
                            prices_created += 1
                        
                        # Create historical price points
                        for historical_data in package.historical_5m:
                            try:
                                HistoricalPricePoint.objects.update_or_create(
                                    item=item,
                                    interval='5m',
                                    timestamp=datetime.fromtimestamp(
                                        historical_data.timestamp, 
                                        tz=timezone.get_current_timezone()
                                    ),
                                    defaults={
                                        'avg_high_price': historical_data.avg_high_price,
                                        'avg_low_price': historical_data.avg_low_price,
                                        'high_price_volume': historical_data.high_price_volume,
                                        'low_price_volume': historical_data.low_price_volume,
                                        'data_source': historical_data.data_source,
                                    }
                                )
                                historical_points_created += 1
                            except Exception as e:
                                logger.warning(f"Failed to save 5m historical point for {item.name}: {e}")
                        
                        for historical_data in package.historical_1h:
                            try:
                                HistoricalPricePoint.objects.update_or_create(
                                    item=item,
                                    interval='1h',
                                    timestamp=datetime.fromtimestamp(
                                        historical_data.timestamp, 
                                        tz=timezone.get_current_timezone()
                                    ),
                                    defaults={
                                        'avg_high_price': historical_data.avg_high_price,
                                        'avg_low_price': historical_data.avg_low_price,
                                        'high_price_volume': historical_data.high_price_volume,
                                        'low_price_volume': historical_data.low_price_volume,
                                        'data_source': historical_data.data_source,
                                    }
                                )
                                historical_points_created += 1
                            except Exception as e:
                                logger.warning(f"Failed to save 1h historical point for {item.name}: {e}")
                            
                    except IntegrityError as e:
                        logger.warning(f"Database integrity error for item {package.item_id}: {e}")
                    except Exception as e:
                        logger.error(f"Database error for item {package.item_id}: {e}")
            
            return {
                'items_created': items_created,
                'items_updated': items_updated,
                'prices_created': prices_created,
                'historical_points_created': historical_points_created
            }
        
        # Run database operations in thread to avoid blocking
        return await asyncio.to_thread(save_batch)
    
    def _log_ingestion_stats(self):
        """Log final ingestion statistics."""
        if self.stats['total_items'] > 0:
            success_rate = (self.stats['successful_ingestions'] / self.stats['total_items']) * 100
            logger.info(f"📈 Ingestion Statistics:")
            logger.info(f"   Total items: {self.stats['total_items']}")
            logger.info(f"   Successful: {self.stats['successful_ingestions']} ({success_rate:.1f}%)")
            logger.info(f"   Failed: {self.stats['failed_ingestions']}")
            logger.info(f"   Skipped: {self.stats['skipped_items']}")
            logger.info(f"   Processing time: {self.stats['processing_time']:.1f}s")
    
    async def ingest_historical_data_only(self, 
                                       item_ids: Optional[List[int]] = None,
                                       periods_5m: int = 12,
                                       periods_1h: int = 24) -> Dict[str, Any]:
        """
        Ingest only historical price data without updating current prices.
        Useful for backfilling historical data or real-time updates.
        
        Args:
            item_ids: Specific item IDs to ingest historical data for
            periods_5m: Number of 5-minute periods to fetch
            periods_1h: Number of 1-hour periods to fetch
            
        Returns:
            Dictionary with ingestion results
        """
        start_time = datetime.now()
        logger.info("📈 Starting historical data ingestion")
        
        try:
            # Fetch historical data
            historical_data_5m = {}
            historical_data_1h = {}
            
            if self.include_historical_5m:
                historical_data_5m = await self._fetch_historical_data_with_periods('5m', periods_5m)
            
            if self.include_historical_1h:
                historical_data_1h = await self._fetch_historical_data_with_periods('1h', periods_1h)
            
            # Filter by specific item IDs if provided
            if item_ids:
                item_id_set = set(item_ids)
                historical_data_5m = {k: v for k, v in historical_data_5m.items() if k in item_id_set}
                historical_data_1h = {k: v for k, v in historical_data_1h.items() if k in item_id_set}
            
            # Save directly to database
            historical_points_created = await self._save_historical_data_only(
                historical_data_5m, historical_data_1h
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'completed',
                'historical_points_created': historical_points_created,
                'items_with_5m_data': len(historical_data_5m),
                'items_with_1h_data': len(historical_data_1h),
                'processing_time_seconds': processing_time
            }
            
        except Exception as e:
            logger.error(f"Historical data ingestion failed: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    async def _save_historical_data_only(self, 
                                       data_5m: Dict[int, List[HistoricalPriceData]],
                                       data_1h: Dict[int, List[HistoricalPriceData]]) -> int:
        """Save only historical price data to database."""
        def save_historical():
            points_created = 0
            
            with transaction.atomic():
                # Process 5-minute data
                for item_id, price_points in data_5m.items():
                    try:
                        item = Item.objects.get(item_id=item_id)
                        for historical_data in price_points:
                            HistoricalPricePoint.objects.update_or_create(
                                item=item,
                                interval='5m',
                                timestamp=datetime.fromtimestamp(
                                    historical_data.timestamp, 
                                    tz=timezone.get_current_timezone()
                                ),
                                defaults={
                                    'avg_high_price': historical_data.avg_high_price,
                                    'avg_low_price': historical_data.avg_low_price,
                                    'high_price_volume': historical_data.high_price_volume,
                                    'low_price_volume': historical_data.low_price_volume,
                                    'data_source': historical_data.data_source,
                                }
                            )
                            points_created += 1
                    except Item.DoesNotExist:
                        logger.warning(f"Item {item_id} not found, skipping historical data")
                    except Exception as e:
                        logger.warning(f"Failed to save 5m data for item {item_id}: {e}")
                
                # Process 1-hour data
                for item_id, price_points in data_1h.items():
                    try:
                        item = Item.objects.get(item_id=item_id)
                        for historical_data in price_points:
                            HistoricalPricePoint.objects.update_or_create(
                                item=item,
                                interval='1h',
                                timestamp=datetime.fromtimestamp(
                                    historical_data.timestamp, 
                                    tz=timezone.get_current_timezone()
                                ),
                                defaults={
                                    'avg_high_price': historical_data.avg_high_price,
                                    'avg_low_price': historical_data.avg_low_price,
                                    'high_price_volume': historical_data.high_price_volume,
                                    'low_price_volume': historical_data.low_price_volume,
                                    'data_source': historical_data.data_source,
                                }
                            )
                            points_created += 1
                    except Item.DoesNotExist:
                        logger.warning(f"Item {item_id} not found, skipping historical data")
                    except Exception as e:
                        logger.warning(f"Failed to save 1h data for item {item_id}: {e}")
            
            return points_created
        
        return await asyncio.to_thread(save_historical)

    async def get_ingestion_health_status(self) -> Dict[str, Any]:
        """Get health status of the ingestion system including historical data support."""
        try:
            # Test all API endpoints
            status_results = await self.unified_client.get_data_source_status()
            
            # Test historical endpoints
            historical_5m_test = False
            historical_1h_test = False
            
            try:
                test_5m = await self.wiki_client.get_historical_prices_5m()
                historical_5m_test = len(test_5m) > 0
            except Exception as e:
                logger.debug(f"5m endpoint test failed: {e}")
            
            try:
                test_1h = await self.wiki_client.get_historical_prices_1h()
                historical_1h_test = len(test_1h) > 0
            except Exception as e:
                logger.debug(f"1h endpoint test failed: {e}")
            
            # Test database connectivity
            db_test = await asyncio.to_thread(Item.objects.count)
            historical_points_count = await asyncio.to_thread(HistoricalPricePoint.objects.count)
            
            # Check cache connectivity
            cache_test = cache.get('health_check', 'not_found') != 'not_found'
            
            return {
                'status': 'healthy',
                'wiki_api': status_results.get('runescape_wiki', {}),
                'historical_endpoints': {
                    '5m_available': historical_5m_test,
                    '1h_available': historical_1h_test
                },
                'database_items': db_test,
                'historical_points_stored': historical_points_count,
                'cache_working': cache_test,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }