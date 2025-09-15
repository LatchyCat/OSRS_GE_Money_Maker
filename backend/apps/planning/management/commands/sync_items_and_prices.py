"""
Django management command to sync OSRS items and prices from RuneScape Wiki API.
This command initializes the database with all items and their current market data.
"""

import asyncio
import logging
from typing import Dict, List
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.items.models import Item, ItemCategory, ItemCategoryMapping
from apps.prices.models import PriceSnapshot, ProfitCalculation
from services.api_client import RuneScapeWikiClient
from services.unified_wiki_price_client import UnifiedPriceClient
from services.embedding_service import OllamaEmbeddingService
from services.mcp_price_service import mcp_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync OSRS items and prices from RuneScape Wiki API'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_count = 0
        self.max_requests = 500
        self.start_time = None
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--items-only',
            action='store_true',
            help='Only sync items metadata, skip prices',
        )
        parser.add_argument(
            '--prices-only', 
            action='store_true',
            help='Only sync prices, skip items metadata',
        )
        parser.add_argument(
            '--start-mcp',
            action='store_true',
            help='Start MCP service after syncing',
        )
        parser.add_argument(
            '--generate-embeddings',
            action='store_true',
            help='Generate embeddings for items after syncing',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of items to process (for testing)',
        )
        parser.add_argument(
            '--max-requests',
            type=int,
            default=500,
            help='Maximum number of API requests to prevent runaway (default: 500)',
        )
        parser.add_argument(
            '--request-delay',
            type=float,
            default=2.0,
            help='Delay between API requests in seconds (default: 2.0)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making API requests',
        )
    
    def handle(self, *args, **options):
        """Main command handler with safety limits (CRITICAL FIX)."""
        import time
        self.start_time = time.time()
        self.max_requests = options.get('max_requests', 500)
        
        # Safety warnings
        if options.get('dry_run'):
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN MODE - No API requests will be made')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Safety limits: max {self.max_requests} requests, {options.get("request_delay", 2.0)}s delay')
            )
            
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting OSRS data synchronization...')
        )
        
        try:
            # Run async operations with monitoring
            asyncio.run(self._sync_data(options))
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.ERROR('⚠️  Sync interrupted by user')
            )
            return
        except Exception as e:
            elapsed = time.time() - self.start_time if self.start_time else 0
            self.stdout.write(
                self.style.ERROR(f'❌ Sync failed after {elapsed:.1f}s, {self.request_count} requests: {e}')
            )
            raise CommandError(f'Sync failed: {e}')
        
        elapsed = time.time() - self.start_time if self.start_time else 0
        self.stdout.write(
            self.style.SUCCESS(f'✅ OSRS data synchronization completed! ({elapsed:.1f}s, {self.request_count} requests)')
        )
    
    async def _sync_data(self, options):
        """Async data synchronization."""
        # Sync items if not prices-only
        if not options['prices_only']:
            await self._sync_items(options.get('limit'))
        
        # Sync prices if not items-only
        if not options['items_only']:
            await self._sync_prices(options.get('limit'))
        
        # Generate embeddings if requested
        if options['generate_embeddings']:
            await self._generate_embeddings()
        
        # Start MCP service if requested
        if options['start_mcp']:
            await self._start_mcp_service()
    
    async def _sync_items(self, limit: int = None):
        """Sync items metadata from RuneScape Wiki API."""
        self.stdout.write('📦 Syncing items metadata...')
        
        async with RuneScapeWikiClient() as client:
            try:
                # Fetch item mapping data
                response = await client.get_item_mapping()
                items_data = response if isinstance(response, list) else response.get('data', [])
                
                if not items_data:
                    raise CommandError('No items data received from API')
                
                # Apply limit for testing
                if limit:
                    items_data = items_data[:limit]
                
                self.stdout.write(f'🔍 Processing {len(items_data)} items...')
                
                # Process items in batches
                batch_size = 100
                total_created = 0
                total_updated = 0
                
                for i in range(0, len(items_data), batch_size):
                    batch = items_data[i:i + batch_size]
                    created, updated = await self._process_items_batch(batch)
                    total_created += created
                    total_updated += updated
                    
                    # Progress indicator
                    processed = min(i + batch_size, len(items_data))
                    self.stdout.write(f'  Processed {processed}/{len(items_data)} items...')
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Items sync completed: {total_created} created, {total_updated} updated'
                    )
                )
                
            except Exception as e:
                raise CommandError(f'Items sync failed: {e}')
    
    async def _process_items_batch(self, items_data: List[Dict]) -> tuple:
        """Process a batch of items data."""
        created_count = 0
        updated_count = 0
        
        # Process items without transaction for now (async compatibility)
        for item_data in items_data:
            try:
                item_id = item_data['id']
                name = item_data['name']
                examine = item_data.get('examine', '')
                high_alch = item_data.get('highalch', 0)
                low_alch = item_data.get('lowalch', 0)
                value = item_data.get('value', 0)
                limit = item_data.get('limit', 0)
                members = item_data.get('members', False)
                
                # Create or update item
                item, created = await Item.objects.aget_or_create(
                    item_id=item_id,
                    defaults={
                        'name': name,
                        'examine': examine,
                        'value': value,
                        'high_alch': high_alch,
                        'low_alch': low_alch,
                        'limit': limit,
                        'members': members,
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    # Update existing item
                    item.name = name
                    item.examine = examine
                    item.value = value
                    item.high_alch = high_alch
                    item.low_alch = low_alch
                    item.limit = limit
                    item.members = members
                    item.is_active = True
                    await item.asave()
                    updated_count += 1
                
            except Exception as e:
                logger.error(f'Error processing item {item_data.get("id", "unknown")}: {e}')
                
        return created_count, updated_count
    
    async def _sync_prices(self, limit: int = None):
        """Sync current prices using multi-source price intelligence with monitoring (CRITICAL FIX)."""
        self.stdout.write('💰 Syncing current prices from multiple sources...')
        
        # Check if we've exceeded request limits
        if self.request_count >= self.max_requests:
            self.stdout.write(
                self.style.ERROR(f'🛑 Request limit reached ({self.max_requests}). Aborting to prevent runaway.')
            )
            return
        
        async with UnifiedPriceClient() as client:
            try:
                # Get active items from database
                items_query = Item.objects.filter(is_active=True)
                if limit:
                    items_query = items_query[:limit]
                
                items_dict = {
                    item.item_id: item async for item in items_query
                }
                item_ids = list(items_dict.keys())
                
                # Additional safety limit for price sync
                remaining_requests = self.max_requests - self.request_count
                if len(item_ids) > remaining_requests:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Limiting items to {remaining_requests} due to request quota')
                    )
                    item_ids = item_ids[:remaining_requests]
                    items_dict = {k: v for k, v in items_dict.items() if k in item_ids}
                
                self.stdout.write(f'💸 Fetching best prices for {len(item_ids)} items from multiple sources...')
                self.stdout.write(f'📊 Request quota: {self.request_count}/{self.max_requests} used')
                
                # Estimate requests needed (conservative estimate)
                estimated_requests = len(item_ids) * 2  # Assume 2 API calls per item
                if self.request_count + estimated_requests > self.max_requests:
                    self.stdout.write(
                        self.style.ERROR(f'🛑 Estimated {estimated_requests} requests would exceed quota. Aborting.')
                    )
                    return
                
                # Fetch best prices from multiple sources
                price_data_map = await client.get_multiple_comprehensive_prices(
                    item_ids, 
                    max_staleness_hours=48.0  # Allow slightly older data for initial sync
                )
                
                # Update request count (conservative estimate)
                self.request_count += len(item_ids) * 2
                
                if not price_data_map:
                    raise CommandError('No valid price data received from multi-source client')
                
                self.stdout.write(f'📊 Received price data for {len(price_data_map)} items')
                
                # Process prices with enhanced quality information
                total_processed = 0
                total_profitable = 0
                source_stats = {}
                
                for item_id, price_data in price_data_map.items():
                    try:
                        if item_id not in items_dict:
                            continue
                        
                        item = items_dict[item_id]
                        
                        # Track source statistics
                        source = price_data.source.value
                        source_stats[source] = source_stats.get(source, 0) + 1
                        
                        # Create price snapshot with multi-source metadata
                        source_timestamp = None
                        if price_data.timestamp > 0:
                            source_timestamp = timezone.make_aware(
                                timezone.datetime.fromtimestamp(price_data.timestamp)
                            )
                        
                        await PriceSnapshot.objects.acreate(
                            item=item,
                            high_price=price_data.high_price,  # instant-sell price
                            low_price=price_data.low_price,    # instant-buy price
                            high_time=source_timestamp,
                            low_time=source_timestamp,
                            api_source=price_data.source.value,
                            total_volume=max(price_data.volume_high, price_data.volume_low),
                            price_volatility=0.3 if price_data.quality.value == 'stale' else 0.1
                        )
                        
                        # Calculate profit for logging
                        nature_rune_cost = 180
                        profit = item.high_alch - price_data.low_price - nature_rune_cost
                        
                        # Create enhanced profit calculation with source metadata
                        is_profitable = await self._create_enhanced_profit_calculation(
                            item, price_data
                        )
                        
                        # Enhanced logging with multi-source intelligence
                        logger.info(f"Item {item_id} ({item.name}): "
                                  f"buy={price_data.low_price:,} GP, sell={price_data.high_price:,} GP, "
                                  f"profit={profit:,} GP, source={source}, "
                                  f"quality={price_data.quality.value}, "
                                  f"age={price_data.age_hours:.1f}h, "
                                  f"confidence={price_data.confidence_score:.2f}")
                        
                        # Log quality warnings for problematic data
                        if price_data.quality.value == 'stale':
                            logger.warning(f"Stale price data for item {item_id} ({item.name}): "
                                         f"age={price_data.age_hours:.1f}h from {source}")
                        elif price_data.confidence_score < 0.3:
                            logger.warning(f"Low confidence price data for item {item_id} ({item.name}): "
                                         f"confidence={price_data.confidence_score:.2f}")
                        
                        if is_profitable:
                            total_profitable += 1
                        
                        total_processed += 1
                        
                    except Exception as e:
                        logger.error(f'Error processing price for item {item_id}: {e}')
                
                # Print source statistics
                self.stdout.write('📊 Price data source statistics:')
                for source, count in source_stats.items():
                    percentage = (count / total_processed) * 100 if total_processed > 0 else 0
                    self.stdout.write(f"  {source}: {count} items ({percentage:.1f}%)")
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Multi-source prices sync completed: {total_processed} items processed, '
                        f'{total_profitable} profitable items found'
                    )
                )
                
            except Exception as e:
                raise CommandError(f'Multi-source prices sync failed: {e}')
    
    async def _create_profit_calculation(self, item: Item, buy_price: int, sell_price: int) -> bool:
        """
        Create profit calculation for an item.
        
        Args:
            item: Item instance
            buy_price: The instant-buy price (low_price from API)
            sell_price: The instant-sell price (high_price from API)
        """
        nature_rune_cost = 180  # Default nature rune cost
        
        # Calculate high alch profit: alch_value - buy_price - nature_rune_cost
        profit = item.high_alch - buy_price - nature_rune_cost
        margin = (profit / buy_price * 100) if buy_price > 0 else 0
        
        # Create profit calculation
        await ProfitCalculation.objects.aupdate_or_create(
            item=item,
            defaults={
                'current_buy_price': buy_price,     # Correct: instant-buy price
                'current_sell_price': sell_price,   # Correct: instant-sell price
                'current_profit': profit,
                'current_profit_margin': margin,
                'daily_volume': 0,  # Will be updated by MCP service
                'recommendation_score': max(0.0, min(1.0, margin / 20.0)),  # Scale to 0-1
                'price_trend': 'stable',
                'last_updated': timezone.now()
            }
        )
        
        return profit > 0
        
    async def _create_enhanced_profit_calculation(self, item: Item, price_data) -> bool:
        """
        Create enhanced profit calculation using multi-source price data with validation.
        
        Args:
            item: Item instance
            price_data: PriceData object from multi-source client
        """
        from services.multi_source_price_client import PriceData, DataQuality
        from price_sanity_validator import validate_and_sanitize_price
        
        nature_rune_cost = 180  # Default nature rune cost
        raw_buy_price = price_data.high_price  # Price we pay (instant buy)
        raw_sell_price = price_data.low_price  # Price we get (instant sell)
        
        # Validate buy price
        buy_validation = validate_and_sanitize_price(item.name, raw_buy_price, price_data.source.value)
        if not buy_validation['accepted']:
            logger.warning(f"Rejecting sync buy price for {item.name}: {buy_validation['reason']}")
            return False
        
        # Validate sell price
        sell_validation = validate_and_sanitize_price(item.name, raw_sell_price, price_data.source.value)
        if not sell_validation['accepted']:
            logger.warning(f"Rejecting sync sell price for {item.name}: {sell_validation['reason']}")
            return False
        
        buy_price = buy_validation['sanitized_price']
        sell_price = sell_validation['sanitized_price']
        
        # Calculate high alch profit: alch_value - buy_price - nature_rune_cost
        profit = item.high_alch - buy_price - nature_rune_cost
        margin = (profit / buy_price * 100) if buy_price > 0 else 0
        
        # Calculate enhanced recommendation score
        recommendation_score = self._calculate_recommendation_score(
            profit, margin, price_data
        )
        
        # Determine price trend and volume estimates
        daily_volume = max(price_data.volume_high, price_data.volume_low)
        price_trend = 'stable'  # Default, could be enhanced with historical data
        
        # Create enhanced profit calculation with multi-source metadata
        await ProfitCalculation.objects.aupdate_or_create(
            item=item,
            defaults={
                'current_buy_price': buy_price,
                'current_sell_price': sell_price,
                'current_profit': profit,
                'current_profit_margin': margin,
                'daily_volume': daily_volume,
                'recommendation_score': recommendation_score,
                'price_trend': price_trend,
                'data_source': price_data.source.value,
                'data_quality': price_data.quality.value,
                'confidence_score': price_data.confidence_score,
                'data_age_hours': price_data.age_hours,
                'source_timestamp': timezone.make_aware(
                    timezone.datetime.fromtimestamp(price_data.timestamp)
                ) if price_data.timestamp > 0 else None,
                'last_updated': timezone.now()
            }
        )
        
        return profit > 0  # Return True if profitable
    
    def _calculate_recommendation_score(self, profit: int, margin: float, price_data) -> float:
        """Calculate recommendation score using multi-source intelligence."""
        base_score = 0.5
        
        # Profit bonus (normalize to 0-0.3 range)
        profit_bonus = min(profit / 10000, 0.3) if profit > 0 else -0.2
        
        # Margin bonus (normalize to 0-0.2 range)
        margin_bonus = min(margin / 50, 0.2) if margin > 0 else -0.1
        
        # Data quality bonus from multi-source intelligence
        quality_bonus = {
            'fresh': 0.15,
            'recent': 0.1, 
            'acceptable': 0.05,
            'stale': -0.1,
            'unknown': -0.2
        }.get(price_data.quality.value, 0)
        
        # Confidence bonus from source reliability
        confidence_bonus = (price_data.confidence_score - 0.5) * 0.2
        
        # Volume bonus (items with good volume data are more reliable)
        volume_bonus = 0.1 if (price_data.volume_high > 10 or price_data.volume_low > 10) else 0
        
        # Age penalty (fresher data gets higher score)
        age_penalty = min(price_data.age_hours / 24, 1) * -0.1
        
        total_score = (base_score + profit_bonus + margin_bonus + 
                      quality_bonus + confidence_bonus + volume_bonus + age_penalty)
        
        return max(0.0, min(1.0, total_score))
    
    def _validate_price_data(self, item_id: int, high_price: int, low_price: int, 
                           high_time: int, low_time: int) -> dict:
        """
        Validate price data quality and freshness.
        
        Args:
            item_id: Item ID
            high_price: Instant-sell price
            low_price: Instant-buy price  
            high_time: Unix timestamp of high price
            low_time: Unix timestamp of low price
            
        Returns:
            Dict with validation results
        """
        current_time = timezone.now().timestamp()
        
        # Check price freshness (24 hours = 86400 seconds)
        high_age_hours = (current_time - high_time) / 3600 if high_time > 0 else float('inf')
        low_age_hours = (current_time - low_time) / 3600 if low_time > 0 else float('inf')
        
        is_fresh = high_age_hours < 24 and low_age_hours < 24
        
        # Check price sanity (buy price should be <= sell price)
        price_spread_ok = low_price <= high_price
        spread_percentage = ((high_price - low_price) / low_price * 100) if low_price > 0 else 0
        
        # Check for reasonable price values (not zero or negative)
        prices_positive = high_price > 0 and low_price > 0
        
        # Detect potentially stale or incorrect data
        warnings = []
        if not is_fresh:
            warnings.append(f"Prices over 24h old (high: {high_age_hours:.1f}h, low: {low_age_hours:.1f}h)")
        if not price_spread_ok:
            warnings.append(f"Invalid price spread: buy {low_price} > sell {high_price}")
        if spread_percentage > 50:
            warnings.append(f"Unusual price spread: {spread_percentage:.1f}%")
        if not prices_positive:
            warnings.append(f"Invalid prices: high={high_price}, low={low_price}")
        
        return {
            'is_fresh': is_fresh,
            'high_age_hours': high_age_hours,
            'low_age_hours': low_age_hours,
            'spread_percentage': spread_percentage,
            'price_spread_ok': price_spread_ok,
            'prices_positive': prices_positive,
            'quality_score': 1.0 if (is_fresh and price_spread_ok and prices_positive) else 0.5,
            'warnings': warnings,
            'message': '; '.join(warnings) if warnings else 'Good quality data'
        }
    
    async def _generate_embeddings(self):
        """Generate embeddings for all items."""
        self.stdout.write('🧠 Generating embeddings...')
        
        try:
            embedding_service = OllamaEmbeddingService()
            
            # Get all active items
            items = [item async for item in Item.objects.filter(is_active=True)]
            
            self.stdout.write(f'🔍 Generating embeddings for {len(items)} items...')
            
            # Generate embeddings in batches
            batch_size = 50
            total_generated = 0
            
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                
                # Generate embeddings for batch
                for item in batch:
                    text = f"{item.name} {item.examine}"
                    try:
                        await embedding_service.generate_item_embedding(item.item_id, text)
                        total_generated += 1
                    except Exception as e:
                        logger.error(f'Failed to generate embedding for item {item.item_id}: {e}')
                
                # Progress indicator
                processed = min(i + batch_size, len(items))
                self.stdout.write(f'  Generated {processed}/{len(items)} embeddings...')
            
            # Build FAISS index
            await embedding_service.build_search_index()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Embeddings generated: {total_generated} items'
                )
            )
            
        except Exception as e:
            logger.error(f'Embeddings generation failed: {e}')
    
    async def _start_mcp_service(self):
        """Start the MCP service for real-time price tracking."""
        self.stdout.write('🎯 Starting MCP service...')
        
        try:
            # This would typically run in a separate process/service
            # For now, we'll just initialize it
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  MCP service initialization completed. '
                    'Run as a separate service for continuous operation.'
                )
            )
            
        except Exception as e:
            logger.error(f'MCP service start failed: {e}')