import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import WebSocketConnection

logger = logging.getLogger(__name__)


class PriceUpdatesConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time price updates and recommendations.
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Join the price updates group
        self.group_name = "price_updates"
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Track this connection
        await self.create_connection_record()
        
        logger.info(f"WebSocket connected: {self.channel_name}")
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'status': 'connected',
            'message': 'Connected to OSRS High Alch Tracker'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave the price updates group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        # Mark connection as inactive
        await self.deactivate_connection_record()
        
        logger.info(f"WebSocket disconnected: {self.channel_name} (code: {close_code})")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'subscribe_items':
                await self.handle_item_subscription(data)
            elif message_type == 'set_profit_threshold':
                await self.handle_profit_threshold(data)
            elif message_type == 'ping':
                await self.handle_ping()
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
    
    async def handle_item_subscription(self, data):
        """Handle item subscription requests."""
        item_ids = data.get('item_ids', [])
        
        # Update connection record with subscribed items
        await self.update_subscribed_items(item_ids)
        
        await self.send(text_data=json.dumps({
            'type': 'subscription_updated',
            'subscribed_items': item_ids,
            'message': f'Subscribed to {len(item_ids)} items'
        }))
    
    async def handle_profit_threshold(self, data):
        """Handle profit threshold updates."""
        threshold = data.get('threshold', 0)
        
        await self.update_profit_threshold(threshold)
        
        await self.send(text_data=json.dumps({
            'type': 'threshold_updated',
            'threshold': threshold,
            'message': f'Profit threshold set to {threshold}gp'
        }))
    
    async def handle_ping(self):
        """Handle ping/pong for connection health."""
        await self.update_last_activity()
        
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat()
        }))
    
    # Group message handlers
    async def price_update(self, event):
        """Send price update to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'price_update',
            'data': event['data']
        }))
    
    async def profit_alert(self, event):
        """Send profit alert to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'profit_alert',
            'data': event['data']
        }))
    
    async def ai_recommendation(self, event):
        """Send AI recommendation to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'ai_recommendation',
            'data': event['data']
        }))
    
    # Database operations
    @database_sync_to_async
    def create_connection_record(self):
        """Create a database record for this connection."""
        try:
            connection, created = WebSocketConnection.objects.get_or_create(
                channel_name=self.channel_name,
                defaults={
                    'connection_type': 'price_updates',
                    'is_active': True
                }
            )
            if not created:
                connection.is_active = True
                connection.save()
            return connection
        except Exception as e:
            logger.error(f"Error creating connection record: {str(e)}")
    
    @database_sync_to_async
    def deactivate_connection_record(self):
        """Mark connection as inactive in database."""
        try:
            WebSocketConnection.objects.filter(
                channel_name=self.channel_name
            ).update(is_active=False)
        except Exception as e:
            logger.error(f"Error deactivating connection record: {str(e)}")
    
    @database_sync_to_async
    def update_subscribed_items(self, item_ids):
        """Update subscribed items for this connection."""
        try:
            WebSocketConnection.objects.filter(
                channel_name=self.channel_name
            ).update(
                subscribed_items=item_ids,
                last_activity=timezone.now()
            )
        except Exception as e:
            logger.error(f"Error updating subscribed items: {str(e)}")
    
    @database_sync_to_async
    def update_profit_threshold(self, threshold):
        """Update profit threshold for this connection."""
        try:
            WebSocketConnection.objects.filter(
                channel_name=self.channel_name
            ).update(
                min_profit_threshold=threshold,
                last_activity=timezone.now()
            )
        except Exception as e:
            logger.error(f"Error updating profit threshold: {str(e)}")
    
    @database_sync_to_async
    def update_last_activity(self):
        """Update last activity timestamp."""
        try:
            WebSocketConnection.objects.filter(
                channel_name=self.channel_name
            ).update(last_activity=timezone.now())
        except Exception as e:
            logger.error(f"Error updating last activity: {str(e)}")