from django.contrib import admin
from .models import SystemState, SyncOperation


@admin.register(SystemState)
class SystemStateAdmin(admin.ModelAdmin):
    list_display = [
        'last_startup_time', 'startup_count', 'downtime_hours', 
        'total_items_count', 'profitable_items_count', 
        'data_quality_score', 'sync_in_progress'
    ]
    readonly_fields = [
        'startup_count', 'downtime_duration', 'downtime_hours',
        'needs_sync', 'data_quality_score'
    ]
    
    fieldsets = (
        ('Startup Tracking', {
            'fields': (
                'last_startup_time', 'previous_shutdown_time', 'startup_count',
                'downtime_duration', 'downtime_hours'
            )
        }),
        ('Data Sync Status', {
            'fields': (
                'last_full_sync', 'last_price_sync', 'last_item_mapping_sync',
                'last_embedding_sync', 'current_sync_strategy', 'sync_in_progress'
            )
        }),
        ('Item Statistics', {
            'fields': (
                'total_items_count', 'profitable_items_count', 'new_items_discovered'
            )
        }),
        ('System Health', {
            'fields': (
                'data_quality_score', 'embedding_index_status', 'needs_sync'
            )
        })
    )
    
    def downtime_hours(self, obj):
        return f"{obj.downtime_hours:.2f} hours"
    downtime_hours.short_description = "Downtime Duration"


@admin.register(SyncOperation)
class SyncOperationAdmin(admin.ModelAdmin):
    list_display = [
        'operation_type', 'status', 'started_at', 'duration_seconds',
        'items_processed', 'items_created', 'items_updated', 'errors_encountered'
    ]
    list_filter = ['operation_type', 'status', 'started_at']
    readonly_fields = ['started_at', 'completed_at', 'duration_seconds']
    search_fields = ['operation_type', 'error_message']
    
    fieldsets = (
        ('Operation Info', {
            'fields': ('operation_type', 'status', 'started_at', 'completed_at', 'duration_seconds')
        }),
        ('Results', {
            'fields': ('items_processed', 'items_created', 'items_updated', 'errors_encountered')
        }),
        ('Error Info', {
            'fields': ('error_message',)
        }),
        ('Metadata', {
            'fields': ('metadata',)
        })
    )