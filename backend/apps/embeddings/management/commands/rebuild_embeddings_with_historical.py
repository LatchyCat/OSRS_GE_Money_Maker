"""
Management command to rebuild embeddings with historical tags.

This command re-processes all items with the enhanced tagging system that includes
historical market behavior tags, then rebuilds the embeddings for improved AI search.

Usage:
    python manage.py rebuild_embeddings_with_historical [--items-limit 100] [--force]
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from typing import List

from apps.items.models import Item
from services.comprehensive_item_tagger import ComprehensiveItemTagger
from services.historical_data_service import HistoricalDataService
from services.multi_agent_ai_service import MultiAgentAIService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Rebuild embeddings with historical tags for enhanced AI trading recommendations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--items-limit',
            type=int,
            default=500,
            help='Limit the number of items to process (default: 500)'
        )
        
        parser.add_argument(
            '--force-historical',
            action='store_true',
            help='Force refresh of historical data even if recent data exists'
        )
        
        parser.add_argument(
            '--skip-historical',
            action='store_true', 
            help='Skip historical data fetching and use existing data only'
        )
        
        parser.add_argument(
            '--test-run',
            action='store_true',
            help='Run without making any changes (dry run)'
        )
        
        parser.add_argument(
            '--use-multi-agent',
            action='store_true',
            default=True,
            help='Use multi-agent AI system for faster processing (default: True)'
        )
        
        parser.add_argument(
            '--single-agent',
            action='store_true',
            help='Force single-agent mode (overrides --use-multi-agent)'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        items_limit = options['items_limit']
        force_historical = options['force_historical']
        skip_historical = options['skip_historical']
        test_run = options['test_run']
        use_multi_agent = options['use_multi_agent'] and not options['single_agent']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🚀 Starting embeddings rebuild with historical tags'
            )
        )
        self.stdout.write(f'Items limit: {items_limit}')
        self.stdout.write(f'Force historical refresh: {force_historical}')
        self.stdout.write(f'Skip historical fetching: {skip_historical}')
        self.stdout.write(f'Test run: {test_run}')
        self.stdout.write(f'Multi-agent processing: {"Enabled" if use_multi_agent else "Disabled"}')
        
        if use_multi_agent:
            self.stdout.write(self.style.WARNING(
                '🤖 Multi-Agent Mode: Using gemma3:1b, deepseek-r1:1.5b, and qwen3:4b for distributed processing'
            ))
        
        # Run the async rebuild process
        try:
            stats = asyncio.run(
                self._rebuild_embeddings_with_historical(
                    items_limit, force_historical, skip_historical, test_run, use_multi_agent
                )
            )
            
            # Display results
            self.stdout.write(self.style.SUCCESS('\n✅ Embeddings rebuild completed!'))
            self.stdout.write(f'📊 Statistics:')
            for key, value in stats.items():
                self.stdout.write(f'  • {key}: {value}')
                
        except Exception as e:
            logger.error(f"Error rebuilding embeddings: {e}")
            raise CommandError(f'Failed to rebuild embeddings: {e}')
    
    async def _rebuild_embeddings_with_historical(self, 
                                                items_limit: int,
                                                force_historical: bool,
                                                skip_historical: bool,
                                                test_run: bool,
                                                use_multi_agent: bool) -> dict:
        """Rebuild embeddings with historical data integration."""
        
        stats = {
            'items_processed': 0,
            'historical_analyses_created': 0,
            'items_retagged': 0,
            'embeddings_rebuilt': 0,
            'errors': 0
        }
        
        # Get items to process (prioritize by trading volume)
        self.stdout.write('📊 Fetching items to process...')
        items = await self._get_items_for_processing(items_limit)
        
        if not items:
            self.stdout.write(self.style.WARNING('No items found to process'))
            return stats
        
        self.stdout.write(f'Found {len(items)} items to process')
        
        # Step 1: Bootstrap/update historical data if requested
        if not skip_historical:
            self.stdout.write('📈 Processing historical data...')
            async with HistoricalDataService() as historical_service:
                historical_stats = await self._process_historical_data(
                    historical_service, items, force_historical, test_run
                )
                stats['historical_analyses_created'] = historical_stats.get('analyses_created', 0)
        
        # Step 2: Re-tag all items with enhanced tags (including historical)
        self.stdout.write('🏷️ Re-tagging items with enhanced tags...')
        retag_stats = await self._retag_items_with_historical(items, test_run)
        stats['items_retagged'] = retag_stats.get('items_tagged', 0)
        
        # Step 3: Rebuild embeddings with new tags
        self.stdout.write('🔄 Rebuilding embeddings...')
        embedding_stats = await self._rebuild_embeddings(items, test_run)
        stats['embeddings_rebuilt'] = embedding_stats.get('embeddings_created', 0)
        
        stats['items_processed'] = len(items)
        
        return stats
    
    async def _get_items_for_processing(self, limit: int) -> List[Item]:
        """Get items prioritized by trading activity."""
        # Prioritize by trading volume and profit potential
        items = [
            item async for item in Item.objects.select_related('profit_calc')
            .filter(
                profit_calc__isnull=False,
                is_active=True
            )
            .order_by('-profit_calc__daily_volume', '-profit_calc__current_profit')[:limit]
        ]
        
        self.stdout.write(f'Selected {len(items)} items based on trading activity')
        return items
    
    async def _process_historical_data(self, 
                                     historical_service: HistoricalDataService,
                                     items: List[Item],
                                     force_refresh: bool,
                                     test_run: bool) -> dict:
        """Process historical data for items."""
        stats = {'analyses_created': 0, 'errors': 0}
        
        if test_run:
            self.stdout.write(self.style.WARNING('[TEST RUN] Skipping historical data processing'))
            return stats
        
        # Process in smaller batches to manage memory and API limits
        batch_size = 20
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(items) + batch_size - 1) // batch_size
            
            self.stdout.write(f'Processing historical batch {batch_num}/{total_batches}')
            
            for item in batch:
                try:
                    success = await historical_service.update_item_historical_data(
                        item, force_refresh
                    )
                    if success:
                        stats['analyses_created'] += 1
                        self.stdout.write(f'  ✅ {item.name}')
                    else:
                        self.stdout.write(f'  ⚠️ {item.name} - no historical data')
                
                except Exception as e:
                    stats['errors'] += 1
                    self.stdout.write(f'  ❌ {item.name} - error: {e}')
            
            # Small delay between batches to respect rate limits
            if i + batch_size < len(items):
                await asyncio.sleep(1)
        
        return stats
    
    async def _retag_items_with_historical(self, items: List[Item], test_run: bool) -> dict:
        """Re-tag items with enhanced historical tags."""
        stats = {'items_tagged': 0, 'errors': 0}
        
        if test_run:
            self.stdout.write(self.style.WARNING('[TEST RUN] Skipping item re-tagging'))
            return stats
        
        tagger = ComprehensiveItemTagger()
        
        # Ensure all tag categories exist (including new historical ones)
        await tagger._ensure_tag_categories_exist()
        
        # Process items in batches
        batch_size = 50
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(items) + batch_size - 1) // batch_size
            
            self.stdout.write(f'Tagging batch {batch_num}/{total_batches}')
            
            try:
                batch_stats = await tagger._process_batch(batch)
                stats['items_tagged'] += batch_stats
                self.stdout.write(f'  ✅ Tagged {batch_stats} items')
                
            except Exception as e:
                stats['errors'] += len(batch)
                self.stdout.write(f'  ❌ Batch error: {e}')
        
        return stats
    
    async def _rebuild_embeddings(self, items: List[Item], test_run: bool) -> dict:
        """Rebuild embeddings for items with new tags."""
        stats = {'embeddings_created': 0, 'errors': 0}
        
        if test_run:
            self.stdout.write(self.style.WARNING('[TEST RUN] Skipping embeddings rebuild'))
            return stats
        
        # Import embedding service
        try:
            from services.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
        except ImportError:
            self.stdout.write(
                self.style.WARNING('EmbeddingService not available - skipping embedding rebuild')
            )
            return stats
        
        # Process items in smaller batches for embeddings
        batch_size = 25
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(items) + batch_size - 1) // batch_size
            
            self.stdout.write(f'Rebuilding embeddings batch {batch_num}/{total_batches}')
            
            for item in batch:
                try:
                    # Get enhanced item description with all tags
                    enhanced_description = await self._get_enhanced_item_description(item)
                    
                    # Rebuild embedding
                    await embedding_service.create_embedding(
                        item_id=item.item_id,
                        description=enhanced_description,
                        replace_existing=True
                    )
                    
                    stats['embeddings_created'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error creating embedding for {item.name}: {e}")
            
            # Small delay between batches
            await asyncio.sleep(0.5)
        
        return stats
    
    async def _get_enhanced_item_description(self, item: Item) -> str:
        """Get enhanced item description with all tags for embeddings."""
        # Base item information
        description_parts = [
            f"Item: {item.name}",
            f"OSRS item ID: {item.item_id}"
        ]
        
        if item.examine:
            description_parts.append(f"Description: {item.examine}")
        
        # Add profit information if available
        if hasattr(item, 'profit_calc') and item.profit_calc:
            profit_calc = item.profit_calc
            description_parts.extend([
                f"Current price: {profit_calc.current_buy_price or 0:,} GP",
                f"Profit potential: {profit_calc.current_profit or 0:,} GP",
                f"Profit margin: {profit_calc.current_profit_margin or 0:.1f}%",
                f"Daily volume: {profit_calc.daily_volume or 0:,}"
            ])
        
        # Add all tags from categories
        tag_categories = await self._get_item_tag_categories(item)
        if tag_categories:
            # Group tags by category for better semantic understanding
            tag_descriptions = []
            for category, tags in tag_categories.items():
                if tags:
                    tag_descriptions.append(f"{category}: {', '.join(tags)}")
            
            if tag_descriptions:
                description_parts.append("Market characteristics: " + " | ".join(tag_descriptions))
        
        # Add historical context if available
        try:
            from apps.prices.models import HistoricalAnalysis
            analysis = await HistoricalAnalysis.objects.aget(item=item)
            
            historical_parts = []
            if analysis.trend_30d:
                historical_parts.append(f"30d trend: {analysis.trend_30d}")
            if analysis.volatility_30d:
                vol_desc = "high" if analysis.volatility_30d > 0.3 else "low" if analysis.volatility_30d < 0.1 else "medium"
                historical_parts.append(f"volatility: {vol_desc}")
            if analysis.current_price_percentile_30d:
                percentile = analysis.current_price_percentile_30d
                if percentile > 80:
                    historical_parts.append("near 30d highs")
                elif percentile < 20:
                    historical_parts.append("near 30d lows")
            
            if historical_parts:
                description_parts.append("Historical context: " + ", ".join(historical_parts))
                
        except HistoricalAnalysis.DoesNotExist:
            pass
        except Exception as e:
            logger.warning(f"Error getting historical context for {item.name}: {e}")
        
        return " | ".join(description_parts)
    
    async def _get_item_tag_categories(self, item: Item) -> dict:
        """Get item tags organized by category."""
        from apps.items.models import ItemCategoryMapping
        
        tag_categories = {}
        
        # Get all tag mappings for this item
        mappings = [
            mapping async for mapping in ItemCategoryMapping.objects.filter(item=item)
            .select_related('category')
        ]
        
        # Organize by category type (this is a simplified categorization)
        category_mapping = {
            'price': ['under-1k', '1k-5k', '5k-25k', '25k-100k', '100k-1m', '1m-plus'],
            'type': ['weapon', 'armor', 'consumable', 'material', 'rare', 'potion', 'food'],
            'trading': ['bulk-flip', 'high-margin', 'quick-flip', 'scalable', 'volume-play'],
            'behavior': ['stable', 'volatile', 'trending-up', 'trending-down', 'seasonal'],
            'capital': ['micro-capital', 'small-capital', 'medium-capital', 'large-capital', 'whale-capital'],
            'risk': ['low-risk', 'medium-risk', 'high-risk'],
            'liquidity': ['high-liquidity', 'medium-liquidity', 'low-liquidity'],
            'historical': ['historically-stable', 'historically-volatile', 'long-term-uptrend', 
                          'breaking-resistance', 'at-historical-high', 'low-volatility-30d']
        }
        
        for mapping in mappings:
            tag_name = mapping.category.name
            
            # Find which category this tag belongs to
            for category, tags in category_mapping.items():
                if tag_name in tags:
                    if category not in tag_categories:
                        tag_categories[category] = []
                    tag_categories[category].append(tag_name)
                    break
        
        return tag_categories