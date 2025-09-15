"""
Management command for starting the reactive trading engine.

This command initializes and runs the reactive trading engine that continuously
monitors market conditions and generates real-time trading intelligence.
"""

import asyncio
import logging
import signal
import sys
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from services.reactive_trading_engine import ReactiveTradingEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start the reactive trading engine for real-time market monitoring'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine: ReactiveTradingEngine = None
        self.shutdown_requested = False
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--monitoring-interval',
            type=int,
            default=30,
            help='Price monitoring interval in seconds (default: 30)'
        )
        
        parser.add_argument(
            '--pattern-analysis-interval',
            type=int,
            default=300,
            help='Pattern analysis interval in seconds (default: 300)'
        )
        
        parser.add_argument(
            '--recommendation-update-interval',
            type=int,
            default=600,
            help='Recommendation update interval in seconds (default: 600)'
        )
        
        parser.add_argument(
            '--volume-surge-threshold',
            type=float,
            default=2.0,
            help='Volume surge detection threshold multiplier (default: 2.0)'
        )
        
        parser.add_argument(
            '--test-mode',
            action='store_true',
            help='Run in test mode with increased logging and shorter intervals'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )
    
    def handle(self, *args, **options):
        # Configure logging
        if options['verbose'] or options['test_mode']:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
            logger.setLevel(logging.INFO)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Run async engine
        try:
            asyncio.run(self._async_handle(options))
        except KeyboardInterrupt:
            self.stdout.write("\n🛑 Shutdown requested by user")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Engine failed: {e}"))
            raise CommandError(f"Reactive engine failed: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.shutdown_requested = True
        self.stdout.write(f"\n🔄 Received signal {signum}, shutting down gracefully...")
    
    async def _async_handle(self, options):
        """Async handler for the reactive trading engine."""
        start_time = timezone.now()
        
        try:
            # Initialize engine configuration
            config = {
                'monitoring_interval': options['monitoring_interval'],
                'pattern_analysis_interval': options['pattern_analysis_interval'],
                'recommendation_update_interval': options['recommendation_update_interval'],
                'volume_surge_threshold': options['volume_surge_threshold'],
                'test_mode': options['test_mode']
            }
            
            # Adjust intervals for test mode
            if options['test_mode']:
                config['monitoring_interval'] = min(config['monitoring_interval'], 10)
                config['pattern_analysis_interval'] = min(config['pattern_analysis_interval'], 60)
                config['recommendation_update_interval'] = min(config['recommendation_update_interval'], 120)
                self.stdout.write("🧪 Running in test mode with shortened intervals")
            
            self.stdout.write(self.style.SUCCESS("🚀 Starting Reactive Trading Engine..."))
            self.stdout.write("")
            self.stdout.write("⚙️  Engine Configuration:")
            self.stdout.write(f"   Price monitoring: every {config['monitoring_interval']}s")
            self.stdout.write(f"   Pattern analysis: every {config['pattern_analysis_interval']}s")
            self.stdout.write(f"   Recommendation updates: every {config['recommendation_update_interval']}s")
            self.stdout.write(f"   Volume surge threshold: {config['volume_surge_threshold']}x")
            self.stdout.write("")
            
            # Initialize and start the reactive engine using singleton pattern
            self.engine = ReactiveTradingEngine.get_instance(config)
            
            # Start the engine
            await self.engine.start()
            
            self.stdout.write(self.style.SUCCESS("✅ Reactive Trading Engine started successfully!"))
            self.stdout.write("")
            self.stdout.write("🔍 Real-time monitoring active:")
            self.stdout.write("   • Price change detection")
            self.stdout.write("   • Volume surge alerts")
            self.stdout.write("   • Pattern recognition")
            self.stdout.write("   • Automatic recommendation updates")
            self.stdout.write("   • WebSocket broadcasting")
            self.stdout.write("")
            self.stdout.write("Press Ctrl+C to stop the engine gracefully")
            self.stdout.write("")
            
            # Run the main monitoring loop
            iteration = 0
            while not self.shutdown_requested:
                try:
                    iteration += 1
                    
                    # Run one monitoring cycle
                    await self.engine.run_monitoring_cycle()
                    
                    # Display periodic status updates
                    if iteration % 10 == 0 or options['test_mode']:
                        uptime = (timezone.now() - start_time).total_seconds()
                        status = await self.engine.get_engine_status()
                        
                        self.stdout.write(f"📊 Status Update (uptime: {uptime:.0f}s)")
                        self.stdout.write(f"   Active subscriptions: {status.get('active_subscriptions', 0)}")
                        self.stdout.write(f"   Events processed: {status.get('events_processed', 0)}")
                        self.stdout.write(f"   Recommendations updated: {status.get('recommendations_updated', 0)}")
                        self.stdout.write(f"   Market alerts generated: {status.get('alerts_generated', 0)}")
                        
                        if options['test_mode']:
                            self.stdout.write(f"   Last price check: {status.get('last_price_check', 'Never')}")
                            self.stdout.write(f"   Last pattern analysis: {status.get('last_pattern_analysis', 'Never')}")
                        
                        self.stdout.write("")
                    
                    # Sleep until next monitoring cycle
                    await asyncio.sleep(config['monitoring_interval'])
                    
                except Exception as e:
                    logger.error(f"Error in monitoring cycle: {e}")
                    if options['test_mode']:
                        self.stdout.write(self.style.ERROR(f"⚠️  Monitoring cycle error: {e}"))
                    
                    # Continue monitoring unless it's a critical error
                    await asyncio.sleep(5)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Engine initialization failed: {e}"))
            if options['verbose']:
                import traceback
                self.stdout.write(traceback.format_exc())
            raise
        
        finally:
            # Graceful shutdown
            if self.engine:
                self.stdout.write("🔄 Shutting down engine...")
                await self.engine.stop()
                
                # Display final statistics
                final_status = await self.engine.get_engine_status()
                uptime = (timezone.now() - start_time).total_seconds()
                
                self.stdout.write("")
                self.stdout.write(self.style.SUCCESS("📈 Final Engine Statistics:"))
                self.stdout.write(f"   Total uptime: {uptime:.1f} seconds")
                self.stdout.write(f"   Events processed: {final_status.get('events_processed', 0):,}")
                self.stdout.write(f"   Recommendations updated: {final_status.get('recommendations_updated', 0):,}")
                self.stdout.write(f"   Market alerts generated: {final_status.get('alerts_generated', 0):,}")
                self.stdout.write(f"   Average events/minute: {(final_status.get('events_processed', 0) / max(uptime/60, 1)):.1f}")
            
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("✅ Reactive Trading Engine stopped gracefully"))
            self.stdout.write("")
            self.stdout.write("🎯 Next Steps:")
            self.stdout.write("   1. Review generated market alerts and recommendations")
            self.stdout.write("   2. Check WebSocket connections and frontend updates")
            self.stdout.write("   3. Analyze pattern detection effectiveness")
            self.stdout.write("   4. Monitor database performance and optimization needs")
            
            # Useful commands for next steps
            self.stdout.write("")
            self.stdout.write("📝 Related Commands:")
            self.stdout.write("   - Test engine: python manage.py start_reactive_engine --test-mode")
            self.stdout.write("   - View market alerts: python manage.py shell -c \"from apps.prices.models import MarketAlert; print(MarketAlert.objects.count())\"")
            self.stdout.write("   - Pattern analysis: python manage.py analyze_price_patterns --test-single 995")
            self.stdout.write("   - Historical data: python manage.py ingest_historical_data --test-single 995")