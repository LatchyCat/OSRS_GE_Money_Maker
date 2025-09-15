"""
Celery beat schedule configuration for periodic tasks.
"""

from celery.schedules import crontab

# Celery beat schedule
CELERY_BEAT_SCHEDULE = {
    # === VOLUME-BASED REAL-TIME UPDATES ===
    
    # Sync hot items (high volume) every 5 minutes with 5m data
    'sync-hot-items-5m': {
        'task': 'tasks.sync_data.sync_hot_items_5m',
        'schedule': 300.0,  # 5 minutes
    },
    
    # Sync warm items (medium volume) every 15 minutes with 1h data
    'sync-warm-items-1h': {
        'task': 'tasks.sync_data.sync_warm_items_1h',  
        'schedule': 900.0,  # 15 minutes
    },
    
    # Sync all items (including cool/cold) every 30 minutes
    'sync-latest-prices': {
        'task': 'tasks.sync_data.sync_latest_prices',
        'schedule': 1800.0,  # 30 minutes (was 5 minutes)
    },
    
    # === REGULAR MAINTENANCE ===
    
    # Sync item mapping every 4 hours (new items are rare)
    'sync-item-mapping': {
        'task': 'tasks.sync_data.sync_item_mapping',
        'schedule': crontab(minute=0, hour='*/4'),  # Every 4 hours
    },
    
    # Generate embeddings for new items every hour
    'generate-embeddings': {
        'task': 'tasks.sync_data.generate_embeddings_for_new_items',
        'schedule': crontab(minute=0),  # Every hour
    },
    
    # Generate daily market summary twice per day
    'daily-market-summary': {
        'task': 'tasks.sync_data.generate_daily_market_summary',
        'schedule': crontab(hour=[8, 20], minute=0),  # 8 AM and 8 PM UTC
    },
    
    # Clean up old data daily at 2 AM UTC
    'cleanup-old-data': {
        'task': 'tasks.sync_data.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM UTC
    },
    
    # Health check every 3 minutes
    'health-check': {
        'task': 'tasks.sync_data.health_check_services',
        'schedule': 180.0,  # 3 minutes
    },
}