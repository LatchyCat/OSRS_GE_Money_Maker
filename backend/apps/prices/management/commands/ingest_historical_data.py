"""
Management command for ingesting historical price data from RuneScape Wiki API.

This command fetches historical price data from the /5m and /1h endpoints
and stores it in the database for trend analysis and predictive modeling.
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from services.unified_data_ingestion_service import UnifiedDataIngestionService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ingest historical price data from RuneScape Wiki API (/5m and /1h endpoints)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--items',
            type=str,
            help='Comma-separated list of item IDs to ingest historical data for'
        )
        
        parser.add_argument(
            '--periods-5m',
            type=int,
            default=12,
            help='Number of 5-minute periods to fetch (default: 12 = last hour)'
        )
        
        parser.add_argument(
            '--periods-1h',
            type=int,
            default=24,
            help='Number of 1-hour periods to fetch (default: 24 = last day)'
        )
        
        parser.add_argument(
            '--full-ingestion',
            action='store_true',
            help='Do complete ingestion (items + current prices + historical data)'
        )
        
        parser.add_argument(
            '--historical-only',
            action='store_true',
            help='Ingest only historical data, skip current price updates'
        )
        
        parser.add_argument(
            '--test-single',
            type=int,
            help='Test historical ingestion for a single item ID'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )
    
    def handle(self, *args, **options):
        # Configure logging
        if options['verbose']:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
            logger.setLevel(logging.INFO)
        
        # Run async command handler
        asyncio.run(self._async_handle(options))
    
    async def _async_handle(self, options):
        """Async handler for the management command."""
        start_time = timezone.now()
        
        # Initialize unified data ingestion service
        async with UnifiedDataIngestionService() as ingestion_service:
            
            # Parse item IDs if provided
            item_ids = None
            if options['items']:
                try:
                    item_ids = [int(x.strip()) for x in options['items'].split(',')]
                    self.stdout.write(f"Targeting {len(item_ids)} specific items")
                except ValueError as e:
                    raise CommandError(f"Invalid item IDs format: {e}")
            
            # Single item test mode
            if options['test_single']:
                await self._test_single_item_historical_data(
                    ingestion_service, options['test_single'], options
                )
                return
            
            try:
                self.stdout.write(self.style.SUCCESS("🚀 Starting historical price data ingestion..."))
                
                if options['historical_only']:
                    # Ingest only historical data
                    results = await ingestion_service.ingest_historical_data_only(
                        item_ids=item_ids,
                        periods_5m=options['periods_5m'],
                        periods_1h=options['periods_1h']
                    )
                    
                    await self._display_historical_results(results, start_time, options)
                    
                elif options['full_ingestion']:
                    # Full ingestion including historical data
                    results = await ingestion_service.ingest_complete_market_data(
                        item_ids=item_ids,
                        include_historical=True,
                        historical_periods_5m=options['periods_5m'],
                        historical_periods_1h=options['periods_1h']
                    )
                    
                    await self._display_full_ingestion_results(results, start_time, options)
                    
                else:
                    # Default: historical data only
                    results = await ingestion_service.ingest_historical_data_only(
                        item_ids=item_ids,
                        periods_5m=options['periods_5m'],
                        periods_1h=options['periods_1h']
                    )
                    
                    await self._display_historical_results(results, start_time, options)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Historical data ingestion failed: {e}"))
                if options['verbose']:
                    import traceback
                    self.stdout.write(traceback.format_exc())
                raise CommandError(f"Historical data ingestion failed: {e}")
    
    async def _test_single_item_historical_data(self, ingestion_service, item_id, options):
        """Test historical data ingestion for a single item."""
        self.stdout.write(f"🧪 Testing historical data ingestion for item {item_id}...")
        
        try:
            # Test health of historical endpoints first
            health_status = await ingestion_service.get_ingestion_health_status()
            
            self.stdout.write("📊 System Health Check:")
            self.stdout.write(f"   5m endpoint: {'✅' if health_status.get('historical_endpoints', {}).get('5m_available') else '❌'}")
            self.stdout.write(f"   1h endpoint: {'✅' if health_status.get('historical_endpoints', {}).get('1h_available') else '❌'}")
            
            # Ingest historical data for single item
            results = await ingestion_service.ingest_historical_data_only(
                item_ids=[item_id],
                periods_5m=options['periods_5m'],
                periods_1h=options['periods_1h']
            )
            
            if results['status'] == 'completed':
                self.stdout.write(self.style.SUCCESS(f"✅ Historical data ingestion test completed"))
                self.stdout.write(f"   Historical points created: {results.get('historical_points_created', 0)}")
                self.stdout.write(f"   Items with 5m data: {results.get('items_with_5m_data', 0)}")
                self.stdout.write(f"   Items with 1h data: {results.get('items_with_1h_data', 0)}")
                self.stdout.write(f"   Processing time: {results.get('processing_time_seconds', 0):.2f}s")
            else:
                self.stdout.write(self.style.ERROR(f"❌ Test failed: {results.get('error', 'Unknown error')}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Test failed with exception: {e}"))
    
    async def _display_historical_results(self, results, start_time, options):
        """Display results from historical-only ingestion."""
        if results['status'] == 'completed':
            self.stdout.write(self.style.SUCCESS("✅ Historical price data ingestion completed!"))
            self.stdout.write("")
            
            # Statistics
            self.stdout.write("📈 Historical Data Statistics:")
            self.stdout.write(f"   Historical points created: {results.get('historical_points_created', 0):,}")
            self.stdout.write(f"   Items with 5m data: {results.get('items_with_5m_data', 0):,}")
            self.stdout.write(f"   Items with 1h data: {results.get('items_with_1h_data', 0):,}")
            self.stdout.write(f"   Processing time: {results.get('processing_time_seconds', 0):.2f} seconds")
            self.stdout.write("")
            
        else:
            self.stdout.write(self.style.ERROR(f"❌ Historical ingestion failed: {results.get('error', 'Unknown error')}"))
        
        # Next steps
        self.stdout.write("🎯 Next Steps:")
        self.stdout.write("   1. Run trend analysis on the historical data")
        self.stdout.write("   2. Generate price patterns and predictions")
        self.stdout.write("   3. Update AI embeddings with historical context")
        
        # Useful commands
        self.stdout.write("")
        self.stdout.write("📝 Related Commands:")
        self.stdout.write("   - Full ingestion: python manage.py ingest_historical_data --full-ingestion")
        self.stdout.write("   - Test single item: python manage.py ingest_historical_data --test-single 995")
        self.stdout.write("   - More periods: python manage.py ingest_historical_data --periods-5m 24 --periods-1h 48")
    
    async def _display_full_ingestion_results(self, results, start_time, options):
        """Display results from full ingestion including historical data."""
        if results['status'] == 'completed':
            self.stdout.write(self.style.SUCCESS("✅ Complete market data ingestion completed!"))
            self.stdout.write("")
            
            # Statistics from save_results
            save_results = results.get('save_results', {})
            self.stdout.write("📊 Complete Ingestion Statistics:")
            self.stdout.write(f"   Items created/updated: {save_results.get('items_created', 0)} / {save_results.get('items_updated', 0)}")
            self.stdout.write(f"   Current prices created: {save_results.get('prices_created', 0):,}")
            self.stdout.write(f"   Historical points created: {save_results.get('historical_points_created', 0):,}")
            self.stdout.write(f"   Success rate: {results.get('success_rate_percent', 0):.1f}%")
            self.stdout.write(f"   Processing time: {results.get('processing_time_minutes', 0):.1f} minutes")
            self.stdout.write("")
            
        else:
            self.stdout.write(self.style.ERROR(f"❌ Complete ingestion failed: {results.get('error', 'Unknown error')}"))