"""
Management command to start the real-time streaming data manager.
This runs the continuous market data analysis and WebSocket broadcasting.
"""

from django.core.management.base import BaseCommand
from services.streaming_data_manager import streaming_manager
import asyncio
import signal
import sys


class Command(BaseCommand):
    help = 'Start the real-time streaming data manager for continuous market analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Analysis interval in seconds (default: 60)'
        )
        parser.add_argument(
            '--broadcast-interval', 
            type=int,
            default=5,
            help='WebSocket broadcast interval in seconds (default: 5)'
        )

    def handle(self, *args, **options):
        analysis_interval = options['interval']
        broadcast_interval = options['broadcast_interval']
        
        self.stdout.write('🚀 Starting Real-Time Market Data Streaming Manager')
        self.stdout.write(f'📊 Analysis interval: {analysis_interval} seconds')
        self.stdout.write(f'📡 Broadcast interval: {broadcast_interval} seconds')
        self.stdout.write('=' * 60)
        
        # Set up signal handling for graceful shutdown
        def signal_handler(sig, frame):
            self.stdout.write('\n🛑 Received shutdown signal, stopping streaming manager...')
            if streaming_manager.is_running:
                asyncio.create_task(streaming_manager.stop())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Start the streaming manager
            self.stdout.write('⚡ Initializing streaming data manager...')
            
            # Configure intervals
            streaming_manager.analysis_interval = analysis_interval
            streaming_manager.broadcast_interval = broadcast_interval
            
            # Run the streaming manager
            asyncio.run(self.run_streaming_manager())
            
        except KeyboardInterrupt:
            self.stdout.write('\n🛑 Keyboard interrupt received, shutting down...')
        except Exception as e:
            self.stdout.write(f'❌ Streaming manager error: {e}')
            raise e
        finally:
            self.stdout.write('✅ Streaming manager stopped')

    async def run_streaming_manager(self):
        """Run the streaming manager with proper async context."""
        try:
            self.stdout.write('🔄 Starting continuous market analysis...')
            await streaming_manager.start()
            
            # Keep the manager running
            while streaming_manager.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.stdout.write(f'❌ Runtime error: {e}')
            raise e