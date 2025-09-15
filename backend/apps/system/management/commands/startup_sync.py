"""
Django management command to manually trigger startup sync process.
This can be used for testing or manual execution of the startup sync logic.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.system.models import SystemState, SyncOperation
from apps.system.startup import startup_manager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manually trigger the startup sync process based on system downtime'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force-strategy',
            type=str,
            choices=['quick_volume', 'full_price', 'full_refresh', 'complete_rebuild'],
            help='Force a specific sync strategy instead of auto-detecting'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually doing it'
        )
        parser.add_argument(
            '--reset-state',
            action='store_true',
            help='Reset system state to simulate fresh startup'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Manual Startup Sync Command')
        )
        
        try:
            # Reset state if requested
            if options.get('reset_state'):
                self._reset_system_state()
            
            # Get current system state
            system_state = SystemState.get_current_state()
            
            # Display current system info
            self._display_system_info(system_state)
            
            # Determine sync strategy
            if options.get('force_strategy'):
                sync_strategy = options['force_strategy']
                self.stdout.write(
                    self.style.WARNING(f"🔧 Forcing sync strategy: {sync_strategy}")
                )
            else:
                sync_strategy = system_state.determine_sync_strategy()
                self.stdout.write(
                    self.style.SUCCESS(f"🤖 Auto-detected sync strategy: {sync_strategy}")
                )
            
            if sync_strategy == 'none':
                self.stdout.write(
                    self.style.SUCCESS("✅ No sync needed - data is fresh!")
                )
                return
            
            # Dry run mode
            if options.get('dry_run'):
                self._dry_run_explanation(sync_strategy)
                return
            
            # Execute sync
            self.stdout.write("🔄 Executing sync...")
            startup_manager.handle_startup()
            
            self.stdout.write(
                self.style.SUCCESS("🎉 Startup sync completed successfully!")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Startup sync failed: {e}")
            )
            raise
    
    def _reset_system_state(self):
        """Reset system state to simulate fresh startup."""
        self.stdout.write("🔄 Resetting system state...")
        
        # Delete existing system state
        SystemState.objects.all().delete()
        
        # Create fresh state
        system_state = SystemState.get_current_state()
        
        self.stdout.write(
            self.style.SUCCESS("✅ System state reset - simulating fresh startup")
        )
    
    def _display_system_info(self, system_state):
        """Display current system information."""
        self.stdout.write("\n📊 Current System State:")
        self.stdout.write(f"   • Startup #{system_state.startup_count}")
        self.stdout.write(f"   • Last startup: {system_state.last_startup_time}")
        self.stdout.write(f"   • Previous shutdown: {system_state.previous_shutdown_time or 'Never'}")
        self.stdout.write(f"   • Downtime: {system_state.downtime_hours:.2f} hours")
        self.stdout.write(f"   • Total items: {system_state.total_items_count:,}")
        self.stdout.write(f"   • Profitable items: {system_state.profitable_items_count:,}")
        self.stdout.write(f"   • Data quality score: {system_state.data_quality_score:.1f}/100")
        self.stdout.write(f"   • Sync in progress: {system_state.sync_in_progress}")
        
        # Display sync timestamps
        self.stdout.write("\n🕐 Last Sync Times:")
        self.stdout.write(f"   • Full sync: {system_state.last_full_sync or 'Never'}")
        self.stdout.write(f"   • Price sync: {system_state.last_price_sync or 'Never'}")
        self.stdout.write(f"   • Item mapping: {system_state.last_item_mapping_sync or 'Never'}")
        self.stdout.write(f"   • Embeddings: {system_state.last_embedding_sync or 'Never'}")
    
    def _dry_run_explanation(self, sync_strategy):
        """Explain what would happen in dry run mode."""
        self.stdout.write(f"\n🧪 DRY RUN - Would execute '{sync_strategy}' sync:")
        
        explanations = {
            'quick_volume': [
                "• Update trading volumes and current prices only",
                "• Skip item mapping and embedding updates", 
                "• Fastest sync option (~1-2 minutes)",
                "• Best for short downtimes (15 minutes - 1 hour)"
            ],
            'full_price': [
                "• Complete price refresh for all items",
                "• Update profit calculations",
                "• Skip item mapping and embedding updates",
                "• Moderate sync time (~5-10 minutes)",
                "• Best for medium downtimes (1-24 hours)"
            ],
            'full_refresh': [
                "• Complete item and price data refresh",
                "• Update all profit calculations",
                "• Skip embedding updates to preserve existing data",
                "• Longer sync time (~10-20 minutes)",
                "• Best for long downtimes (1-7 days)"
            ],
            'complete_rebuild': [
                "• Complete rebuild of all data including embeddings",
                "• Fetch all items, prices, and regenerate embeddings",
                "• Longest sync time (~30+ minutes)",
                "• Best for very long downtimes (1+ weeks) or data corruption"
            ]
        }
        
        for point in explanations.get(sync_strategy, ["Unknown strategy"]):
            self.stdout.write(f"  {point}")
        
        self.stdout.write("\n💡 Run without --dry-run to execute the sync.")
    
    def _display_recent_sync_operations(self):
        """Display recent sync operations for context."""
        recent_ops = SyncOperation.objects.order_by('-started_at')[:5]
        
        if recent_ops:
            self.stdout.write("\n📋 Recent Sync Operations:")
            for op in recent_ops:
                status_emoji = {
                    'completed': '✅',
                    'failed': '❌',
                    'in_progress': '🔄',
                    'started': '🟡',
                    'cancelled': '🟠'
                }.get(op.status, '❓')
                
                self.stdout.write(
                    f"  {status_emoji} {op.get_operation_type_display()} - "
                    f"{op.status} ({op.started_at.strftime('%Y-%m-%d %H:%M')})"
                )
                
                if op.status == 'completed':
                    self.stdout.write(
                        f"     Processed: {op.items_processed}, "
                        f"Created: {op.items_created}, "
                        f"Updated: {op.items_updated}"
                    )
        else:
            self.stdout.write("\n📋 No recent sync operations found.")