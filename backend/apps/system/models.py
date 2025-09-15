from django.db import models
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class SystemState(models.Model):
    """
    Tracks the overall system state, startup times, and sync status.
    This is a singleton model - only one record should exist.
    """
    
    # Startup tracking
    last_startup_time = models.DateTimeField(
        auto_now_add=True,
        help_text="When Django backend was last started"
    )
    previous_shutdown_time = models.DateTimeField(
        null=True, blank=True,
        help_text="When Django backend was previously shut down"
    )
    startup_count = models.IntegerField(default=1, help_text="Number of times system has started")
    
    # Data sync tracking
    last_full_sync = models.DateTimeField(
        null=True, blank=True,
        help_text="When last complete data sync was performed"
    )
    last_price_sync = models.DateTimeField(
        null=True, blank=True,
        help_text="When prices were last synced"
    )
    last_item_mapping_sync = models.DateTimeField(
        null=True, blank=True,
        help_text="When item mapping was last synced"
    )
    last_embedding_sync = models.DateTimeField(
        null=True, blank=True,
        help_text="When embeddings were last updated"
    )
    
    # Item tracking
    total_items_count = models.IntegerField(default=0, help_text="Total OSRS items in database")
    profitable_items_count = models.IntegerField(default=0, help_text="Currently profitable items")
    new_items_discovered = models.IntegerField(default=0, help_text="New items found in last sync")
    
    # System health
    data_quality_score = models.FloatField(
        default=0.0,
        help_text="Overall data quality score (0-100)"
    )
    embedding_index_status = models.CharField(
        max_length=20,
        choices=[
            ('healthy', 'Healthy'),
            ('rebuilding', 'Rebuilding'),
            ('corrupted', 'Corrupted'),
            ('missing', 'Missing'),
        ],
        default='missing'
    )
    
    # Sync strategy info
    current_sync_strategy = models.CharField(
        max_length=50,
        choices=[
            ('quick_volume', 'Quick Volume Sync'),
            ('full_price', 'Full Price Sync'),
            ('full_refresh', 'Full Data Refresh'),
            ('complete_rebuild', 'Complete Rebuild'),
            ('none', 'No Sync Needed'),
        ],
        default='none'
    )
    sync_in_progress = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'system_state'
        verbose_name = 'System State'
        verbose_name_plural = 'System States'
    
    def __str__(self):
        return f"System State - Last Startup: {self.last_startup_time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @classmethod
    def get_current_state(cls):
        """Get or create the current system state (singleton)."""
        state, created = cls.objects.get_or_create(
            id=1,  # Always use ID 1 for singleton
            defaults={
                'last_startup_time': timezone.now(),
                'startup_count': 1
            }
        )
        
        if not created:
            # Update startup info
            state.previous_shutdown_time = state.last_startup_time
            state.last_startup_time = timezone.now()
            state.startup_count += 1
            state.save(update_fields=['previous_shutdown_time', 'last_startup_time', 'startup_count'])
        
        return state
    
    @property
    def downtime_duration(self):
        """Calculate how long the system was down."""
        if self.previous_shutdown_time:
            return self.last_startup_time - self.previous_shutdown_time
        return timedelta(0)
    
    @property
    def downtime_hours(self):
        """Get downtime duration in hours."""
        return self.downtime_duration.total_seconds() / 3600
    
    @property
    def needs_sync(self):
        """Determine if any sync is needed."""
        return self.determine_sync_strategy() != 'none'
    
    def determine_sync_strategy(self):
        """
        Determine the appropriate sync strategy based on downtime and data staleness.
        """
        now = timezone.now()
        downtime_hours = self.downtime_hours
        
        # Check data staleness
        price_stale_hours = 24  # Prices are stale after 24 hours
        mapping_stale_hours = 168  # Item mapping is stale after 7 days
        embedding_stale_hours = 336  # Embeddings are stale after 14 days
        
        price_age = (now - self.last_price_sync).total_seconds() / 3600 if self.last_price_sync else float('inf')
        mapping_age = (now - self.last_item_mapping_sync).total_seconds() / 3600 if self.last_item_mapping_sync else float('inf')
        embedding_age = (now - self.last_embedding_sync).total_seconds() / 3600 if self.last_embedding_sync else float('inf')
        
        # Determine strategy based on downtime and data age
        if downtime_hours > 168 or mapping_age > mapping_stale_hours or embedding_age > embedding_stale_hours:  # > 1 week
            return 'complete_rebuild'
        elif downtime_hours > 24 or price_age > price_stale_hours:  # > 1 day
            return 'full_refresh'
        elif downtime_hours > 1 or price_age > 1:  # > 1 hour
            return 'full_price'
        elif downtime_hours > 0.25:  # > 15 minutes
            return 'quick_volume'
        else:
            return 'none'
    
    def update_sync_status(self, sync_type, success=True):
        """Update sync status after a sync operation."""
        now = timezone.now()
        
        if success:
            if sync_type in ['complete_rebuild', 'full_refresh']:
                self.last_full_sync = now
                self.last_price_sync = now
                self.last_item_mapping_sync = now
                if sync_type == 'complete_rebuild':
                    self.last_embedding_sync = now
            elif sync_type == 'full_price':
                self.last_price_sync = now
            elif sync_type == 'item_mapping':
                self.last_item_mapping_sync = now
            elif sync_type == 'embeddings':
                self.last_embedding_sync = now
        
        self.sync_in_progress = False
        self.current_sync_strategy = 'none' if success else sync_type
        self.save()
    
    def start_sync(self, sync_type):
        """Mark sync as in progress."""
        self.current_sync_strategy = sync_type
        self.sync_in_progress = True
        self.save()
    
    def update_item_counts(self, total_items=None, profitable_items=None, new_items=None):
        """Update item counts after sync."""
        if total_items is not None:
            old_count = self.total_items_count
            self.total_items_count = total_items
            if new_items is None and old_count > 0:
                self.new_items_discovered = max(0, total_items - old_count)
        
        if profitable_items is not None:
            self.profitable_items_count = profitable_items
        
        if new_items is not None:
            self.new_items_discovered = new_items
        
        self.save()
    
    def calculate_data_quality_score(self):
        """Calculate overall data quality score."""
        score = 0.0
        now = timezone.now()
        
        # Price data freshness (40 points max)
        if self.last_price_sync:
            hours_since_price_sync = (now - self.last_price_sync).total_seconds() / 3600
            if hours_since_price_sync < 1:
                score += 40
            elif hours_since_price_sync < 24:
                score += 40 * (1 - hours_since_price_sync / 24)
        
        # Item mapping freshness (20 points max)
        if self.last_item_mapping_sync:
            hours_since_mapping_sync = (now - self.last_item_mapping_sync).total_seconds() / 3600
            if hours_since_mapping_sync < 168:  # 7 days
                score += 20
            elif hours_since_mapping_sync < 336:  # 14 days
                score += 20 * (1 - (hours_since_mapping_sync - 168) / 168)
        
        # Embedding freshness (20 points max)
        if self.last_embedding_sync:
            hours_since_embedding_sync = (now - self.last_embedding_sync).total_seconds() / 3600
            if hours_since_embedding_sync < 336:  # 14 days
                score += 20
            elif hours_since_embedding_sync < 672:  # 28 days
                score += 20 * (1 - (hours_since_embedding_sync - 336) / 336)
        
        # Item count validity (20 points max)
        if self.total_items_count > 4000:  # Expected minimum OSRS items
            score += 20
        elif self.total_items_count > 0:
            score += 20 * (self.total_items_count / 4000)
        
        self.data_quality_score = min(100.0, score)
        self.save(update_fields=['data_quality_score'])
        return self.data_quality_score


class SyncOperation(models.Model):
    """
    Tracks individual sync operations for monitoring and debugging.
    """
    
    operation_type = models.CharField(
        max_length=50,
        choices=[
            ('startup_sync', 'Startup Sync'),
            ('quick_volume', 'Quick Volume Sync'),
            ('full_price', 'Full Price Sync'),
            ('full_refresh', 'Full Data Refresh'),
            ('complete_rebuild', 'Complete Rebuild'),
            ('item_mapping', 'Item Mapping Sync'),
            ('embeddings', 'Embeddings Sync'),
        ]
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('started', 'Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        default='started'
    )
    
    # Operation details
    items_processed = models.IntegerField(default=0)
    items_created = models.IntegerField(default=0)
    items_updated = models.IntegerField(default=0)
    errors_encountered = models.IntegerField(default=0)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    # Additional info
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'sync_operations'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['operation_type', '-started_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.get_status_display()} ({self.started_at})"
    
    def mark_completed(self, items_processed=0, items_created=0, items_updated=0, errors=0):
        """Mark operation as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.items_processed = items_processed
        self.items_created = items_created
        self.items_updated = items_updated
        self.errors_encountered = errors
        self.save()
    
    def mark_failed(self, error_message=""):
        """Mark operation as failed."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.error_message = error_message
        self.save()