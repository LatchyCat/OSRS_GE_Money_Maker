from django.db import models


class WebSocketConnection(models.Model):
    """
    Tracks active WebSocket connections for analytics and management.
    """
    
    channel_name = models.CharField(max_length=255, unique=True)
    connection_type = models.CharField(max_length=50, choices=[
        ('price_updates', 'Price Updates'),
        ('recommendations', 'AI Recommendations'),
        ('general', 'General Updates'),
    ], default='price_updates')
    
    # Connection metadata
    connected_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Optional user/session tracking
    session_key = models.CharField(max_length=40, blank=True, help_text="Session key if available")
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    # Subscription preferences
    subscribed_items = models.JSONField(default=list, help_text="List of item IDs to receive updates for")
    min_profit_threshold = models.IntegerField(default=0, help_text="Minimum profit to send updates")
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'websocket_connections'
        indexes = [
            models.Index(fields=['is_active', 'connection_type']),
            models.Index(fields=['-last_activity']),
            models.Index(fields=['session_key']),
        ]
    
    def __str__(self):
        return f"WS {self.connection_type}: {self.channel_name[:20]}..."


class PriceAlert(models.Model):
    """
    User-configured price alerts for specific items.
    """
    
    session_key = models.CharField(max_length=40, db_index=True)
    item = models.ForeignKey('items.Item', on_delete=models.CASCADE, related_name='price_alerts')
    
    # Alert conditions
    alert_type = models.CharField(max_length=50, choices=[
        ('price_below', 'Price drops below threshold'),
        ('price_above', 'Price rises above threshold'),
        ('profit_above', 'Profit exceeds threshold'),
        ('volume_spike', 'Trading volume spike'),
    ])
    threshold_value = models.IntegerField(help_text="Threshold value in GP")
    
    # Alert status
    is_active = models.BooleanField(default=True)
    triggered_count = models.IntegerField(default=0)
    last_triggered = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_alerts'
        indexes = [
            models.Index(fields=['session_key', 'is_active']),
            models.Index(fields=['item', 'alert_type']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Alert: {self.item.name} {self.alert_type} {self.threshold_value}gp"
