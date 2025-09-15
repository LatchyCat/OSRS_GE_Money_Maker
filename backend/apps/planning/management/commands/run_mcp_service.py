"""
Django management command to run the MCP (Market Control Protocol) service
for real-time OSRS price tracking and intelligent priority scheduling.
"""

import asyncio
import signal
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

from services.mcp_price_service import mcp_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the MCP service for real-time OSRS price tracking'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging',
        )
        parser.add_argument(
            '--stats-interval',
            type=int,
            default=300,
            help='Interval for stats reporting (seconds)',
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        # Set up logging
        if options['debug']:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        
        self.stdout.write(
            self.style.SUCCESS('🎯 Starting MCP Price Service...')
        )
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            self.stdout.write(
                self.style.WARNING('\n⚠️  Received shutdown signal, stopping MCP service...')
            )
            asyncio.create_task(mcp_service.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run the service
        try:
            asyncio.run(self._run_service(options))
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.SUCCESS('✅ MCP service stopped gracefully')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ MCP service error: {e}')
            )
    
    async def _run_service(self, options):
        """Run the MCP service with monitoring."""
        stats_interval = options['stats_interval']
        
        # Start the service
        service_task = asyncio.create_task(mcp_service.start())
        
        # Start stats reporting
        stats_task = asyncio.create_task(self._stats_reporter(stats_interval))
        
        # Wait for tasks to complete
        try:
            await asyncio.gather(service_task, stats_task)
        except asyncio.CancelledError:
            self.stdout.write('Service tasks cancelled')
        
    async def _stats_reporter(self, interval: int):
        """Report service statistics periodically."""
        while mcp_service.is_running:
            await asyncio.sleep(interval)
            
            try:
                stats = await mcp_service.get_market_stats()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n📊 MCP Service Stats:\n"
                        f"  Items Tracked: {stats['total_items_tracked']}\n"
                        f"  Tier Distribution:\n"
                        f"    Real-time: {stats['tier_distribution'].get('REALTIME', 0)}\n"
                        f"    Near Real-time: {stats['tier_distribution'].get('NEAR_REALTIME', 0)}\n"
                        f"    Regular: {stats['tier_distribution'].get('REGULAR', 0)}\n"
                        f"    Background: {stats['tier_distribution'].get('BACKGROUND', 0)}\n"
                        f"  Active Users: {stats['active_users']}\n"
                        f"  Goal Plan Items: {stats['goal_plan_items']}\n"
                        f"  High Volatility Items: {stats['high_volatility_items']}\n"
                        f"  Uptime: {stats['service_uptime']:.1f}s\n"
                    )
                )
                
            except Exception as e:
                logger.error(f"Stats reporting failed: {e}")