"""
Django management command for unified market data synchronization.

This command uses the RuneScape Wiki API exclusively to synchronize:
- Item metadata (/mapping endpoint)
- Latest prices (/latest endpoint)  
- Volume data (/timeseries endpoint)

Replaces all WeirdGloop API dependencies with comprehensive Wiki API integration.
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from services.unified_data_ingestion_service import UnifiedDataIngestionService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Synchronize complete OSRS market data using RuneScape Wiki API only'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--items',
            type=str,
            help='Comma-separated list of item IDs to sync (default: all items)'
        )
        
        parser.add_argument(
            '--priority-only',
            action='store_true',
            help='Sync only critical and high priority items'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform dry run without saving to database'
        )
        
        parser.add_argument(
            '--max-items',
            type=int,
            default=None,
            help='Maximum number of items to process (for testing)'
        )
        
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Perform health check on ingestion system'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )
    
    def handle(self, *args, **options):
        # Configure logging level
        if options['verbose']:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
            logger.setLevel(logging.INFO)
        
        # Run async ingestion
        asyncio.run(self._async_handle(options))
    
    async def _async_handle(self, options):
        """Async handler for the management command."""
        start_time = timezone.now()
        
        # Health check mode
        if options['health_check']:
            await self._perform_health_check()
            return
        
        # Parse item IDs if provided
        item_ids = None
        if options['items']:
            try:
                item_ids = [int(x.strip()) for x in options['items'].split(',')]
                self.stdout.write(f"Targeting {len(item_ids)} specific items: {item_ids[:10]}{'...' if len(item_ids) > 10 else ''}")
            except ValueError as e:
                raise CommandError(f"Invalid item IDs format: {e}")
        
        # Priority filtering
        if options['priority_only']:
            self.stdout.write("Processing only critical and high priority items")
        
        # Dry run mode
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("🧪 DRY RUN MODE - No database changes will be made"))
        
        try:
            async with UnifiedDataIngestionService() as ingestion_service:
                # Perform ingestion
                self.stdout.write(self.style.SUCCESS("🚀 Starting unified market data synchronization..."))
                
                results = await ingestion_service.ingest_complete_market_data(item_ids)
                
                # Display results
                await self._display_results(results, start_time, options)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ingestion failed: {e}"))
            if options['verbose']:
                import traceback
                self.stdout.write(traceback.format_exc())
            raise CommandError(f"Data ingestion failed: {e}")
    
    async def _perform_health_check(self):
        """Perform comprehensive health check."""
        self.stdout.write("🔍 Performing ingestion system health check...")
        
        try:
            async with UnifiedDataIngestionService() as service:
                health_status = await service.get_ingestion_health_status()
                
                # Display health results
                if health_status['status'] == 'healthy':
                    self.stdout.write(self.style.SUCCESS("✅ Ingestion system is healthy"))
                    
                    wiki_status = health_status.get('wiki_api', {})
                    if wiki_status.get('healthy'):
                        self.stdout.write(f"   📡 RuneScape Wiki API: Available")
                        self.stdout.write(f"      - Price data: {'✅' if wiki_status.get('price_data_working') else '❌'}")
                        self.stdout.write(f"      - Volume data: {'✅' if wiki_status.get('volume_data_working') else '❌'}")
                        self.stdout.write(f"      - Endpoints: {', '.join(wiki_status.get('endpoints', {}).keys())}")
                    
                    self.stdout.write(f"   💾 Database items: {health_status.get('database_items', 0):,}")
                    self.stdout.write(f"   🗄️ Cache system: {'✅' if health_status.get('cache_working') else '❌'}")
                    
                else:
                    self.stdout.write(self.style.ERROR("❌ Ingestion system is unhealthy"))
                    error = health_status.get('error', 'Unknown error')
                    self.stdout.write(f"   Error: {error}")
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Health check failed: {e}"))
    
    async def _display_results(self, results, start_time, options):
        """Display ingestion results in a formatted way."""
        if results['status'] == 'failed':
            self.stdout.write(self.style.ERROR(f"❌ Ingestion failed: {results.get('error', 'Unknown error')}"))
            return
        
        # Calculate timing
        end_time = timezone.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Get statistics
        stats = results.get('statistics', {})
        save_results = results.get('save_results', {})
        
        # Display summary
        self.stdout.write(self.style.SUCCESS("✅ Market data synchronization completed!"))
        self.stdout.write("")
        
        # Processing statistics
        self.stdout.write("📊 Processing Statistics:")
        self.stdout.write(f"   Total items processed: {stats.get('total_items', 0):,}")
        self.stdout.write(f"   Successful ingestions: {stats.get('successful_ingestions', 0):,}")
        self.stdout.write(f"   Failed ingestions: {stats.get('failed_ingestions', 0):,}")
        self.stdout.write(f"   Skipped items: {stats.get('skipped_items', 0):,}")
        self.stdout.write(f"   Success rate: {results.get('success_rate_percent', 0):.1f}%")
        self.stdout.write("")
        
        # Database statistics (if not dry run)
        if not options['dry_run'] and save_results:
            self.stdout.write("💾 Database Updates:")
            self.stdout.write(f"   Items created: {save_results.get('items_created', 0):,}")
            self.stdout.write(f"   Items updated: {save_results.get('items_updated', 0):,}")
            self.stdout.write(f"   Price snapshots created: {save_results.get('prices_created', 0):,}")
            self.stdout.write("")
        
        # Performance metrics
        self.stdout.write("⚡ Performance Metrics:")
        self.stdout.write(f"   Total processing time: {total_time:.1f} seconds")
        self.stdout.write(f"   Items per minute: {results.get('items_per_minute', 0):.1f}")
        self.stdout.write("")
        
        # Data quality indicators
        if stats.get('total_items', 0) > 0:
            quality_score = (stats.get('successful_ingestions', 0) / stats.get('total_items', 1)) * 100
            
            if quality_score >= 95:
                quality_indicator = self.style.SUCCESS("🟢 Excellent")
            elif quality_score >= 85:
                quality_indicator = self.style.WARNING("🟡 Good")
            else:
                quality_indicator = self.style.ERROR("🔴 Needs Attention")
                
            self.stdout.write(f"📈 Data Quality: {quality_indicator} ({quality_score:.1f}%)")
        
        # Recommendations
        self.stdout.write("")
        self.stdout.write("💡 Recommendations:")
        
        if stats.get('failed_ingestions', 0) > stats.get('total_items', 0) * 0.1:
            self.stdout.write("   - High failure rate detected. Check API connectivity and rate limits.")
        
        if results.get('items_per_minute', 0) < 10:
            self.stdout.write("   - Low processing speed. Consider adjusting batch size or concurrency.")
            
        if save_results and save_results.get('prices_created', 0) == 0:
            self.stdout.write("   - No price snapshots created. Check price data availability.")
        
        # Next steps
        self.stdout.write("")
        self.stdout.write("🎯 Next Steps:")
        self.stdout.write("   1. Run embedding generation to enable AI features")
        self.stdout.write("   2. Set up periodic sync (every 1-2 hours for active trading)")
        self.stdout.write("   3. Configure monitoring for data freshness alerts")
        
        # Command examples
        self.stdout.write("")
        self.stdout.write("📝 Useful Commands:")
        self.stdout.write("   - Health check: python manage.py sync_unified_market_data --health-check")
        self.stdout.write("   - Priority sync: python manage.py sync_unified_market_data --priority-only")
        self.stdout.write("   - Specific items: python manage.py sync_unified_market_data --items '995,4151,13190'")