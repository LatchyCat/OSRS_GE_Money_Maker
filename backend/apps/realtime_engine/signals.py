"""
Signal handlers for real-time market data processing.

These signals handle automatic updates to market momentum and volume analysis
when price data changes, ensuring the system remains data-reactive.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from apps.prices.models import PriceSnapshot
from .models import MarketMomentum, VolumeAnalysis
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PriceSnapshot)
def update_market_data_on_price_change(sender, instance, created, **kwargs):
    """
    Update market momentum and volume data when price changes.
    This keeps our real-time analysis current without polling.
    """
    try:
        # Invalidate relevant cache entries
        cache.delete(f'momentum_data_{instance.item.item_id}')
        cache.delete(f'volume_data_{instance.item.item_id}')
        cache.delete('streaming:hot_items')
        
        # Log the price update for monitoring
        logger.debug(f"Price update detected for {instance.item.name}: {instance.high_price}")
        
    except Exception as e:
        logger.error(f"Error processing price signal for item {instance.item.item_id}: {e}")


@receiver(post_save, sender=MarketMomentum)
def broadcast_momentum_update(sender, instance, created, **kwargs):
    """
    Broadcast momentum updates to connected WebSocket clients.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                'market_updates',
                {
                    'type': 'market_update',
                    'data': {
                        'type': 'momentum_update',
                        'item_id': instance.item.item_id,
                        'momentum_score': instance.momentum_score,
                        'trend_direction': instance.trend_direction,
                        'price_velocity': instance.price_velocity,
                    }
                }
            )
            
    except Exception as e:
        logger.error(f"Error broadcasting momentum update: {e}")


@receiver(post_save, sender=VolumeAnalysis)
def broadcast_volume_update(sender, instance, created, **kwargs):
    """
    Broadcast volume surge alerts to connected clients.
    """
    try:
        # Only broadcast if it's a significant volume event
        if instance.volume_ratio_daily >= 2.0:  # 200%+ volume spike
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    'market_updates',
                    {
                        'type': 'volume_surge',
                        'data': {
                            'item_id': instance.item.item_id,
                            'current_volume': instance.current_daily_volume,
                            'volume_ratio': instance.volume_ratio_daily,
                            'liquidity_level': instance.liquidity_level,
                        }
                    }
                )
                
    except Exception as e:
        logger.error(f"Error broadcasting volume update: {e}")