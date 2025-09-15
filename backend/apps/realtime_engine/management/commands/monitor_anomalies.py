"""
Django management command for continuous market anomaly monitoring.

Usage:
    python manage.py monitor_anomalies
    python manage.py monitor_anomalies --interval 60 --threshold 80
"""

import asyncio
import logging
import signal
import sys
from typing import Optional
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from services.anomaly_detection_engine import anomaly_detection_engine
from apps.realtime_engine.anomaly_consumer import anomaly_broadcaster

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor market anomalies and send real-time alerts'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
        self.channel_layer = None
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=300,  # 5 minutes
            help='Scan interval in seconds (default: 300)'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=70.0,
            help='Minimum severity threshold for alerts (default: 70.0)'
        )
        parser.add_argument(
            '--confidence',
            type=float,
            default=0.75,
            help='Minimum confidence threshold for alerts (default: 0.75)'
        )
        parser.add_argument(
            '--broadcast',
            action='store_true',
            help='Enable WebSocket broadcasting of anomalies'
        )
        parser.add_argument(
            '--items',
            nargs='+',
            type=int,
            help='Specific item IDs to monitor (optional)'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon process'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.setup_monitoring(options)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"🔍 Starting market anomaly monitor (interval: {options['interval']}s)"
            )
        )
        
        try:
            # Use asyncio to run the monitoring loop
            asyncio.run(self.monitoring_loop(options))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("🛑 Monitoring stopped by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Monitoring failed: {e}"))
            logger.exception("Anomaly monitoring failed")
    
    def setup_monitoring(self, options):
        """Setup monitoring configuration."""
        self.running = True
        
        if options['broadcast']:
            self.channel_layer = get_channel_layer()
            if self.channel_layer is None:
                self.stdout.write(
                    self.style.WARNING("⚠️  WebSocket broadcasting disabled: no channel layer")
                )
        
        # Configure logging
        if options['daemon']:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('/var/log/anomaly_monitor.log'),
                    logging.StreamHandler()
                ]
            )
    
    async def monitoring_loop(self, options):
        """Main monitoring loop."""
        interval = options['interval']
        threshold = options['threshold']
        confidence = options['confidence']
        item_ids = options.get('items')
        broadcast_enabled = options['broadcast'] and self.channel_layer is not None
        
        scan_count = 0
        last_scan_time = None
        
        self.stdout.write(f"🎯 Monitoring parameters:")
        self.stdout.write(f"   • Interval: {interval}s")
        self.stdout.write(f"   • Severity threshold: {threshold}")
        self.stdout.write(f"   • Confidence threshold: {confidence}")
        self.stdout.write(f"   • Broadcasting: {'enabled' if broadcast_enabled else 'disabled'}")
        self.stdout.write(f"   • Items filter: {'all items' if not item_ids else f'{len(item_ids)} specific items'}")
        
        while self.running:
            try:
                scan_start = timezone.now()
                scan_count += 1
                
                self.stdout.write(f"🔍 Scan #{scan_count} starting at {scan_start.strftime('%H:%M:%S')}")
                
                # Run anomaly detection
                results = await anomaly_detection_engine.detect_market_anomalies(item_ids)
                
                if results.get('error'):
                    self.stdout.write(self.style.ERROR(f"❌ Scan failed: {results['error']}"))
                    await asyncio.sleep(interval)
                    continue
                
                # Filter anomalies by thresholds
                all_anomalies = results.get('anomalies', [])
                significant_anomalies = [
                    anomaly for anomaly in all_anomalies
                    if anomaly['severity_score'] >= threshold and 
                       anomaly['confidence'] >= confidence
                ]
                
                # Report results
                scan_duration = (timezone.now() - scan_start).total_seconds()
                self.stdout.write(
                    f"📊 Scan completed in {scan_duration:.1f}s: "
                    f"{len(all_anomalies)} anomalies detected, "
                    f"{len(significant_anomalies)} significant"
                )
                
                # Process significant anomalies
                if significant_anomalies:
                    await self.process_anomalies(significant_anomalies, broadcast_enabled)
                
                # Update statistics
                last_scan_time = scan_start
                
                # Wait for next scan
                if self.running:
                    await asyncio.sleep(interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Scan error: {e}"))
                logger.exception("Error in monitoring loop")
                
                # Wait before retrying
                await asyncio.sleep(min(interval, 60))
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Monitoring completed. {scan_count} scans performed."
            )
        )
    
    async def process_anomalies(self, anomalies: list, broadcast_enabled: bool):
        """Process detected anomalies."""
        for anomaly in anomalies:
            # Log anomaly
            severity_icon = self.get_severity_icon(anomaly['severity_score'])
            self.stdout.write(
                f"{severity_icon} {anomaly['type'].upper()}: {anomaly['item_name']} "
                f"(severity: {anomaly['severity_score']:.0f}, confidence: {anomaly['confidence']:.2f})"
            )
            self.stdout.write(f"   {anomaly['description']}")
            
            # Broadcast to WebSocket clients if enabled
            if broadcast_enabled:
                try:
                    await anomaly_broadcaster.broadcast_anomaly(
                        self.channel_layer, 
                        anomaly
                    )
                except Exception as e:
                    logger.error(f"Failed to broadcast anomaly: {e}")
    
    def get_severity_icon(self, severity: float) -> str:
        """Get icon based on severity level."""
        if severity >= 90:
            return "🚨"  # Critical
        elif severity >= 80:
            return "⚠️"   # High
        elif severity >= 70:
            return "🔶"  # Medium
        else:
            return "🔵"  # Low
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.stdout.write(self.style.WARNING(f"🛑 Received signal {signum}, shutting down..."))
        self.running = False