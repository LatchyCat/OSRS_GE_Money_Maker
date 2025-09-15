import logging
from django.utils import timezone
from django.conf import settings
from .models import SystemState, SyncOperation

logger = logging.getLogger(__name__)


class StartupManager:
    """
    Handles Django startup detection and triggers appropriate data sync
    based on system downtime and data staleness.
    """
    
    def handle_startup(self):
        """
        Main entry point called when Django starts up.
        Determines sync strategy and triggers appropriate sync operations.
        """
        try:
            # Get or create system state
            system_state = SystemState.get_current_state()
            
            # Log startup info
            downtime_hours = system_state.downtime_hours
            logger.info(f"📊 System startup detected:")
            logger.info(f"   • Startup #{system_state.startup_count}")
            logger.info(f"   • Downtime: {downtime_hours:.2f} hours")
            logger.info(f"   • Last startup: {system_state.previous_shutdown_time or 'Never'}")
            
            # Determine sync strategy
            sync_strategy = system_state.determine_sync_strategy()
            logger.info(f"   • Recommended sync strategy: {sync_strategy}")
            
            # Update data quality score
            quality_score = system_state.calculate_data_quality_score()
            logger.info(f"   • Current data quality score: {quality_score:.1f}/100")
            
            # Skip if no sync needed
            if sync_strategy == 'none':
                logger.info("✅ Data is fresh, no sync needed")
                return
            
            # Start sync operation
            self._trigger_sync(system_state, sync_strategy)
            
        except Exception as e:
            logger.error(f"❌ Error during startup handling: {e}")
    
    def _trigger_sync(self, system_state, sync_strategy):
        """
        Trigger the appropriate sync operation based on strategy.
        """
        # Create sync operation record
        sync_op = SyncOperation.objects.create(
            operation_type='startup_sync',
            status='started'
        )
        
        # Mark system state as syncing
        system_state.start_sync(sync_strategy)
        
        try:
            logger.info(f"🔄 Starting {sync_strategy} sync operation...")
            
            # Import sync tasks here to avoid circular imports
            from apps.planning.tasks import (
                sync_items_and_prices_task,
                sync_embeddings_task,
            )
            
            # Trigger appropriate sync based on strategy
            if sync_strategy == 'quick_volume':
                # Just update trading volumes and current prices
                self._quick_volume_sync(sync_op)
                
            elif sync_strategy == 'full_price':
                # Full price update for all items
                self._full_price_sync(sync_op)
                
            elif sync_strategy == 'full_refresh':
                # Complete item and price refresh
                self._full_refresh_sync(sync_op)
                
            elif sync_strategy == 'complete_rebuild':
                # Complete rebuild including embeddings
                self._complete_rebuild(sync_op)
                
            logger.info(f"✅ {sync_strategy} sync operation queued successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger {sync_strategy} sync: {e}")
            sync_op.mark_failed(str(e))
            system_state.sync_in_progress = False
            system_state.save()
    
    def _quick_volume_sync(self, sync_op):
        """
        Quick sync that only updates trading volumes and latest prices using multi-source intelligence.
        """
        try:
            from django.core.management import call_command
            
            logger.info("🔄 Starting quick volume sync with multi-source intelligence...")
            
            # Use our multi-source sync command with limit for hot items only
            call_command('sync_items_and_prices', '--prices-only', '--limit', '200', verbosity=1)
            
            # Get updated count
            from datetime import timedelta
            from apps.prices.models import PriceSnapshot
            updated_count = PriceSnapshot.objects.filter(
                created_at__gte=timezone.now() - timedelta(minutes=10)
            ).count()
            
            # Mark operation complete
            sync_op.mark_completed(
                items_processed=200,  # Limited to top 200 items
                items_updated=updated_count
            )
            
            # Update system state
            system_state = SystemState.get_current_state()
            system_state.update_sync_status('quick_volume', success=True)
            
            logger.info(f"✅ Quick volume sync completed: {updated_count} items updated")
            
        except Exception as e:
            logger.error(f"❌ Quick volume sync failed: {e}")
            sync_op.mark_failed(str(e))
    
    def _full_price_sync(self, sync_op):
        """
        Full price update for all items using multi-source intelligence.
        """
        try:
            from django.core.management import call_command
            from datetime import timedelta
            from apps.prices.models import PriceSnapshot
            
            logger.info("🔄 Starting full price sync with multi-source intelligence...")
            
            # Use our multi-source sync command for all items
            call_command('sync_items_and_prices', '--prices-only', verbosity=1)
            
            # Get updated count
            updated_count = PriceSnapshot.objects.filter(
                created_at__gte=timezone.now() - timedelta(minutes=30)
            ).count()
            
            # Mark operation complete
            sync_op.mark_completed(
                items_processed=4307,  # All items
                items_updated=updated_count
            )
            
            # Update system state
            system_state = SystemState.get_current_state()
            system_state.update_sync_status('full_price', success=True)
            
            logger.info(f"✅ Full price sync completed: {updated_count} items updated")
            
        except Exception as e:
            logger.error(f"❌ Full price sync failed: {e}")
            sync_op.mark_failed(str(e))
    
    def _full_refresh_sync(self, sync_op):
        """
        Complete item and price refresh using multi-source intelligence.
        """
        try:
            from django.core.management import call_command
            from datetime import timedelta
            from apps.prices.models import PriceSnapshot
            
            logger.info("🔄 Starting full refresh with multi-source intelligence...")
            
            # Use our multi-source sync command for items and prices
            call_command('sync_items_and_prices', verbosity=1)
            
            # Get updated count
            updated_count = PriceSnapshot.objects.filter(
                created_at__gte=timezone.now() - timedelta(minutes=60)
            ).count()
            
            # Mark operation complete
            sync_op.mark_completed(
                items_processed=4307,  # All items
                items_updated=updated_count
            )
            
            # Update system state
            system_state = SystemState.get_current_state()
            system_state.update_sync_status('full_refresh', success=True)
            
            logger.info(f"✅ Full refresh completed: {updated_count} items updated")
            
        except Exception as e:
            logger.error(f"❌ Full refresh failed: {e}")
            sync_op.mark_failed(str(e))
    
    def _complete_rebuild(self, sync_op):
        """
        Complete rebuild including items, prices, and embeddings.
        """
        try:
            from django.core.management import call_command
            from datetime import timedelta
            from apps.prices.models import PriceSnapshot
            
            logger.info("🔄 Starting complete rebuild with multi-source intelligence...")
            
            # Use our multi-source sync command with embeddings generation
            call_command('sync_items_and_prices', '--generate-embeddings', verbosity=1)
            
            # Get updated count
            updated_count = PriceSnapshot.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=2)
            ).count()
            
            # Mark operation complete
            sync_op.mark_completed(
                items_processed=4307,  # All items
                items_updated=updated_count
            )
            
            # Update system state
            system_state = SystemState.get_current_state()
            system_state.update_sync_status('complete_rebuild', success=True)
            
            logger.info(f"✅ Complete rebuild completed: {updated_count} items updated")
            
        except Exception as e:
            logger.error(f"❌ Failed to start complete rebuild: {e}")
            sync_op.mark_failed(str(e))


# Global instance
startup_manager = StartupManager()