"""
Management command for analyzing price patterns and trends using AI.

This command runs comprehensive pattern recognition and trend analysis
on historical price data to generate trading insights and market alerts.
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from services.price_pattern_analysis_service import PricePatternAnalysisService
from apps.items.models import Item
from apps.prices.models import HistoricalPricePoint

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Analyze price patterns and trends using AI-powered pattern recognition'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--items',
            type=str,
            help='Comma-separated list of item IDs to analyze'
        )
        
        parser.add_argument(
            '--test-single',
            type=int,
            help='Test pattern analysis for a single item ID'
        )
        
        parser.add_argument(
            '--trends-only',
            action='store_true',
            help='Run only trend analysis, skip pattern detection'
        )
        
        parser.add_argument(
            '--patterns-only',
            action='store_true',
            help='Run only pattern detection, skip trend analysis'
        )
        
        parser.add_argument(
            '--signals-only',
            action='store_true',
            help='Generate market signals only'
        )
        
        parser.add_argument(
            '--periods',
            type=str,
            default='1h,6h,24h',
            help='Comma-separated list of periods for trend analysis'
        )
        
        parser.add_argument(
            '--lookback-hours',
            type=int,
            default=48,
            help='Hours of historical data for pattern detection (default: 48)'
        )
        
        parser.add_argument(
            '--min-volume',
            type=int,
            default=100,
            help='Minimum trading volume threshold for analysis (default: 100)'
        )
        
        parser.add_argument(
            '--top-items',
            type=int,
            help='Analyze only the top N most traded items'
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
        
        # Initialize pattern analysis service
        analysis_service = PricePatternAnalysisService()
        
        try:
            # Parse item IDs
            item_ids = await self._get_item_ids_for_analysis(options)
            
            if not item_ids:
                self.stdout.write(self.style.WARNING("No items found for analysis"))
                return
            
            self.stdout.write(f"📈 Starting AI pattern analysis for {len(item_ids)} items...")
            
            # Single item test mode
            if options['test_single']:
                await self._test_single_item_analysis(
                    analysis_service, options['test_single'], options
                )
                return
            
            # Parse periods for trend analysis
            periods = [p.strip() for p in options['periods'].split(',')]
            
            # Analysis results
            results = {
                'trends_analyzed': 0,
                'patterns_detected': 0,
                'signals_generated': 0,
                'alerts_created': 0,
                'items_processed': 0
            }
            
            # Process items in batches to avoid overwhelming the system
            batch_size = 10
            for i in range(0, len(item_ids), batch_size):
                batch = item_ids[i:i+batch_size]
                batch_results = await self._process_item_batch(
                    analysis_service, batch, periods, options
                )
                
                # Aggregate results
                for key in results:
                    results[key] += batch_results.get(key, 0)
                
                # Progress update
                self.stdout.write(f"Processed {min(i+batch_size, len(item_ids))}/{len(item_ids)} items...")
            
            # Display final results
            await self._display_analysis_results(results, start_time, options)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Pattern analysis failed: {e}"))
            if options['verbose']:
                import traceback
                self.stdout.write(traceback.format_exc())
            raise CommandError(f"Pattern analysis failed: {e}")
    
    async def _get_item_ids_for_analysis(self, options) -> list:
        """Get list of item IDs to analyze based on options."""
        def get_items():
            if options['items']:
                # Specific items
                try:
                    return [int(x.strip()) for x in options['items'].split(',')]
                except ValueError as e:
                    raise CommandError(f"Invalid item IDs format: {e}")
            
            elif options['top_items']:
                # Top N most traded items
                from django.db.models import Sum
                
                top_items = HistoricalPricePoint.objects.values('item__item_id').annotate(
                    total_volume=Sum('total_volume')
                ).filter(
                    total_volume__gte=options['min_volume'],
                    timestamp__gte=timezone.now() - timezone.timedelta(days=7)
                ).order_by('-total_volume')[:options['top_items']]
                
                return [item['item__item_id'] for item in top_items]
            
            else:
                # All items with recent trading activity
                active_items = HistoricalPricePoint.objects.filter(
                    total_volume__gte=options['min_volume'],
                    timestamp__gte=timezone.now() - timezone.timedelta(days=3)
                ).values_list('item__item_id', flat=True).distinct()
                
                return list(active_items)[:100]  # Limit to 100 items
        
        return await asyncio.to_thread(get_items)
    
    async def _test_single_item_analysis(self, analysis_service, item_id, options):
        """Test comprehensive analysis for a single item."""
        self.stdout.write(f"🧪 Testing AI pattern analysis for item {item_id}...")
        
        try:
            # Check if item has historical data
            data_check = await asyncio.to_thread(
                HistoricalPricePoint.objects.filter(
                    item__item_id=item_id,
                    timestamp__gte=timezone.now() - timezone.timedelta(hours=options['lookback_hours'])
                ).count
            )
            
            if data_check == 0:
                self.stdout.write(self.style.WARNING(f"No historical data found for item {item_id}"))
                return
            
            self.stdout.write(f"📊 Found {data_check} historical price points")
            
            # Parse periods
            periods = [p.strip() for p in options['periods'].split(',')]
            
            # Run trend analysis
            if not options['patterns_only'] and not options['signals_only']:
                self.stdout.write("🔍 Running trend analysis...")
                trends = await analysis_service.analyze_item_trends(item_id, periods)
                
                if trends:
                    self.stdout.write(f"✅ Detected trends for {len(trends)} periods:")
                    for period, trend in trends.items():
                        self.stdout.write(
                            f"   {period}: {trend.direction} (strength: {trend.strength:.2f}, "
                            f"confidence: {trend.confidence:.2f})"
                        )
                else:
                    self.stdout.write("❌ No trends detected")
            
            # Run pattern detection
            if not options['trends_only'] and not options['signals_only']:
                self.stdout.write("🎯 Running pattern detection...")
                patterns = await analysis_service.detect_price_patterns(
                    item_id, options['lookback_hours']
                )
                
                if patterns:
                    self.stdout.write(f"✅ Detected {len(patterns)} patterns:")
                    for pattern in patterns:
                        self.stdout.write(
                            f"   {pattern.pattern_name}: {pattern.confidence:.1%} confidence, "
                            f"target: {pattern.predicted_target}"
                        )
                else:
                    self.stdout.write("❌ No patterns detected")
            
            # Generate market signals
            if not options['trends_only'] and not options['patterns_only']:
                self.stdout.write("📡 Generating market signals...")
                signals = await analysis_service.generate_market_signals(item_id)
                
                if signals:
                    self.stdout.write(f"✅ Generated {len(signals)} market signals:")
                    for signal in signals:
                        self.stdout.write(
                            f"   {signal.signal_type.upper()} ({signal.priority}): {signal.message} "
                            f"({signal.confidence:.1%} confidence)"
                        )
                else:
                    self.stdout.write("❌ No signals generated")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Test failed: {e}"))
            if options['verbose']:
                import traceback
                self.stdout.write(traceback.format_exc())
    
    async def _process_item_batch(self, analysis_service, item_ids: list, 
                                 periods: list, options) -> dict:
        """Process a batch of items for analysis."""
        results = {
            'trends_analyzed': 0,
            'patterns_detected': 0,
            'signals_generated': 0,
            'alerts_created': 0,
            'items_processed': 0
        }
        
        for item_id in item_ids:
            try:
                # Run trend analysis
                if not options['patterns_only'] and not options['signals_only']:
                    trends = await analysis_service.analyze_item_trends(item_id, periods)
                    results['trends_analyzed'] += len(trends)
                
                # Run pattern detection
                if not options['trends_only'] and not options['signals_only']:
                    patterns = await analysis_service.detect_price_patterns(
                        item_id, options['lookback_hours']
                    )
                    results['patterns_detected'] += len(patterns)
                
                # Generate signals
                if not options['trends_only'] and not options['patterns_only']:
                    signals = await analysis_service.generate_market_signals(item_id)
                    results['signals_generated'] += len(signals)
                    
                    # Count high-priority signals as alerts
                    high_priority_signals = [s for s in signals if s.priority in ['critical', 'high']]
                    results['alerts_created'] += len(high_priority_signals)
                
                results['items_processed'] += 1
                
            except Exception as e:
                logger.warning(f"Failed to analyze item {item_id}: {e}")
        
        return results
    
    async def _display_analysis_results(self, results, start_time, options):
        """Display comprehensive analysis results."""
        processing_time = (timezone.now() - start_time).total_seconds()
        
        self.stdout.write(self.style.SUCCESS("✅ AI Pattern Analysis completed!"))
        self.stdout.write("")
        
        # Analysis Statistics
        self.stdout.write("🧠 AI Analysis Statistics:")
        self.stdout.write(f"   Items processed: {results['items_processed']:,}")
        self.stdout.write(f"   Trends analyzed: {results['trends_analyzed']:,}")
        self.stdout.write(f"   Patterns detected: {results['patterns_detected']:,}")
        self.stdout.write(f"   Market signals generated: {results['signals_generated']:,}")
        self.stdout.write(f"   High-priority alerts: {results['alerts_created']:,}")
        self.stdout.write(f"   Processing time: {processing_time:.1f} seconds")
        self.stdout.write("")
        
        # Performance metrics
        if processing_time > 0:
            items_per_second = results['items_processed'] / processing_time
            self.stdout.write(f"⚡ Processing rate: {items_per_second:.2f} items/second")
            self.stdout.write("")
        
        # Quality indicators
        if results['items_processed'] > 0:
            pattern_detection_rate = (results['patterns_detected'] / results['items_processed']) * 100
            signal_generation_rate = (results['signals_generated'] / results['items_processed']) * 100
            
            self.stdout.write("📊 Analysis Quality:")
            self.stdout.write(f"   Pattern detection rate: {pattern_detection_rate:.1f}%")
            self.stdout.write(f"   Signal generation rate: {signal_generation_rate:.1f}%")
            
            if pattern_detection_rate > 30:
                quality_indicator = self.style.SUCCESS("🟢 Excellent pattern recognition")
            elif pattern_detection_rate > 15:
                quality_indicator = self.style.WARNING("🟡 Good pattern recognition") 
            else:
                quality_indicator = "🔴 Limited pattern recognition"
            
            self.stdout.write(f"   Overall quality: {quality_indicator}")
            self.stdout.write("")
        
        # Next steps
        self.stdout.write("🎯 Next Steps:")
        self.stdout.write("   1. Review generated market alerts in the admin interface")
        self.stdout.write("   2. Update AI embeddings with pattern context")
        self.stdout.write("   3. Set up automated pattern monitoring")
        self.stdout.write("   4. Implement real-time alert notifications")
        
        # Useful commands
        self.stdout.write("")
        self.stdout.write("📝 Related Commands:")
        self.stdout.write("   - Test single item: python manage.py analyze_price_patterns --test-single 995")
        self.stdout.write("   - Top 20 items: python manage.py analyze_price_patterns --top-items 20")
        self.stdout.write("   - Trends only: python manage.py analyze_price_patterns --trends-only")
        self.stdout.write("   - Extended periods: python manage.py analyze_price_patterns --periods '1h,6h,24h,7d'")