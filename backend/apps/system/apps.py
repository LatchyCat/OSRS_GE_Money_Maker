from django.apps import AppConfig
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class SystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.system'
    verbose_name = 'System Management'

    def ready(self):
        """
        Called when Django is ready. This is where we detect startup
        and trigger appropriate data sync based on downtime.
        """
        # Only run this in the main process, not during migrations or other commands
        import os
        import sys
        
        # Check if auto-sync is disabled (CRITICAL FIX for runaway processes)
        if os.environ.get('DISABLE_AUTO_SYNC', '').lower() in ('true', '1', 'yes'):
            logger.info("🚫 Auto-sync disabled via DISABLE_AUTO_SYNC environment variable")
            return
        
        # Skip during migrations, tests, or other management commands
        skip_conditions = [
            'migrate' in sys.argv,
            'makemigrations' in sys.argv,
            'collectstatic' in sys.argv,
            'test' in sys.argv,
            'shell' in sys.argv,
            '--help' in sys.argv,
            os.environ.get('RUN_MAIN') != 'true',  # Skip reloader process
        ]
        
        if any(skip_conditions):
            return
            
        logger.info("🚀 Django startup detected - initializing smart sync system...")
        logger.info("💡 To disable auto-sync, set DISABLE_AUTO_SYNC=true environment variable")
        
        # Import here to avoid circular imports
        try:
            from .startup import startup_manager
            startup_manager.handle_startup()
        except ImportError as e:
            logger.warning(f"Startup manager not available yet: {e}")
        except Exception as e:
            logger.error(f"Error during startup initialization: {e}")