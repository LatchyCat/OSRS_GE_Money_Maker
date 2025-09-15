"""
WebSocket Consumer for Real-Time Market Anomaly Alerts

Provides real-time streaming of market anomalies to connected clients.
"""

import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from datetime import datetime, timedelta
from django.utils import timezone

from services.anomaly_detection_engine import anomaly_detection_engine
from services.intelligent_cache import intelligent_cache

logger = logging.getLogger(__name__)


class AnomalyAlertConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time market anomaly alerts.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_group_name = "market_anomalies"
        self.user_preferences = {}
        self.last_scan_time = None
        
    async def connect(self):
        """Accept WebSocket connection and join anomaly alerts group."""
        try:
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            logger.info(f"🔔 Anomaly alert client connected: {self.channel_name}")
            
            # Send initial connection message
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to real-time anomaly alerts',
                'timestamp': timezone.now().isoformat()
            }))
            
            # Send latest anomalies if available
            await self.send_latest_anomalies()
            
            # Start periodic anomaly scanning for this client
            asyncio.create_task(self.periodic_anomaly_scan())
            
        except Exception as e:
            logger.error(f"❌ Error connecting anomaly alert client: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Leave room group on disconnect."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"🔔 Anomaly alert client disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages from client."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'set_preferences':
                await self.handle_set_preferences(data)
            elif message_type == 'request_scan':
                await self.handle_request_scan(data)
            elif message_type == 'subscribe_items':
                await self.handle_subscribe_items(data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.send_error(str(e))
    
    async def handle_set_preferences(self, data):
        """Handle user preference updates."""
        preferences = data.get('preferences', {})
        
        # Validate and set preferences
        self.user_preferences.update({
            'min_severity': max(0, min(100, preferences.get('min_severity', 50))),
            'min_confidence': max(0.0, min(1.0, preferences.get('min_confidence', 0.75))),
            'anomaly_types': preferences.get('anomaly_types', [
                'price_spike', 'price_crash', 'volume_surge', 'market_manipulation'
            ]),
            'item_categories': preferences.get('item_categories', []),
            'alert_frequency': preferences.get('alert_frequency', 'real_time')  # real_time, hourly, daily
        })
        
        await self.send(text_data=json.dumps({
            'type': 'preferences_updated',
            'preferences': self.user_preferences,
            'timestamp': timezone.now().isoformat()
        }))
        
        logger.debug(f"Updated anomaly alert preferences for {self.channel_name}")
    
    async def handle_request_scan(self, data):
        """Handle manual anomaly scan requests."""
        try:
            item_ids = data.get('item_ids')  # Optional specific items
            
            # Run anomaly detection
            results = await anomaly_detection_engine.detect_market_anomalies(item_ids)
            
            # Filter results based on user preferences
            filtered_anomalies = self.filter_anomalies(results.get('anomalies', []))
            
            await self.send(text_data=json.dumps({
                'type': 'scan_results',
                'anomalies': filtered_anomalies,
                'analysis': results.get('analysis', {}),
                'timestamp': timezone.now().isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Error handling scan request: {e}")
            await self.send_error(f"Scan failed: {str(e)}")
    
    async def handle_subscribe_items(self, data):
        """Handle item subscription updates."""
        item_ids = data.get('item_ids', [])
        
        # Store subscribed items for targeted alerts
        self.user_preferences['subscribed_items'] = item_ids
        
        await self.send(text_data=json.dumps({
            'type': 'subscription_updated',
            'subscribed_items': item_ids,
            'timestamp': timezone.now().isoformat()
        }))
    
    async def send_latest_anomalies(self):
        """Send the latest detected anomalies to client."""
        try:
            # Get cached latest anomalies
            cache_key = "anomaly_detection:latest_scan"
            cached_results = intelligent_cache.get(cache_key)
            
            if cached_results:
                filtered_anomalies = self.filter_anomalies(cached_results.get('anomalies', []))
                
                if filtered_anomalies:
                    await self.send(text_data=json.dumps({
                        'type': 'latest_anomalies',
                        'anomalies': filtered_anomalies,
                        'cached_at': cached_results.get('timestamp'),
                        'timestamp': timezone.now().isoformat()
                    }))
            
        except Exception as e:
            logger.error(f"Error sending latest anomalies: {e}")
    
    async def periodic_anomaly_scan(self):
        """Periodically scan for anomalies and send alerts."""
        try:
            while True:
                # Check if it's time for a new scan
                now = timezone.now()
                if (self.last_scan_time is None or 
                    (now - self.last_scan_time).total_seconds() >= 300):  # 5 minutes
                    
                    # Get subscribed items if any
                    item_ids = self.user_preferences.get('subscribed_items')
                    
                    # Run anomaly detection
                    results = await anomaly_detection_engine.detect_market_anomalies(item_ids)
                    
                    # Filter and send new anomalies
                    if results.get('anomalies'):
                        filtered_anomalies = self.filter_anomalies(results['anomalies'])
                        
                        if filtered_anomalies:
                            await self.send(text_data=json.dumps({
                                'type': 'new_anomalies',
                                'anomalies': filtered_anomalies,
                                'scan_timestamp': results.get('timestamp'),
                                'timestamp': timezone.now().isoformat()
                            }))
                    
                    self.last_scan_time = now
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
        except asyncio.CancelledError:
            logger.info(f"Periodic scan cancelled for {self.channel_name}")
        except Exception as e:
            logger.error(f"Error in periodic anomaly scan: {e}")
    
    def filter_anomalies(self, anomalies: list) -> list:
        """Filter anomalies based on user preferences."""
        if not self.user_preferences:
            return anomalies[:10]  # Default: top 10
        
        min_severity = self.user_preferences.get('min_severity', 50)
        min_confidence = self.user_preferences.get('min_confidence', 0.75)
        allowed_types = self.user_preferences.get('anomaly_types', [])
        subscribed_items = self.user_preferences.get('subscribed_items', [])
        
        filtered = []
        for anomaly in anomalies:
            # Check severity threshold
            if anomaly['severity_score'] < min_severity:
                continue
            
            # Check confidence threshold
            if anomaly['confidence'] < min_confidence:
                continue
            
            # Check anomaly type filter
            if allowed_types and anomaly['type'] not in allowed_types:
                continue
            
            # Check item subscription filter
            if subscribed_items and anomaly['item_id'] not in subscribed_items:
                continue
            
            filtered.append(anomaly)
        
        return filtered[:20]  # Limit to top 20 results
    
    async def send_error(self, message: str):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': timezone.now().isoformat()
        }))
    
    # Group message handlers (for broadcasting to all clients)
    
    async def anomaly_broadcast(self, event):
        """Handle anomaly broadcast messages."""
        anomaly = event['anomaly']
        
        # Filter based on user preferences
        if self.should_send_anomaly(anomaly):
            await self.send(text_data=json.dumps({
                'type': 'broadcast_anomaly',
                'anomaly': anomaly,
                'timestamp': timezone.now().isoformat()
            }))
    
    def should_send_anomaly(self, anomaly: dict) -> bool:
        """Check if anomaly should be sent based on user preferences."""
        if not self.user_preferences:
            return anomaly['severity_score'] >= 70  # Default threshold
        
        # Apply the same filtering logic
        return len(self.filter_anomalies([anomaly])) > 0


class MarketAnomalyBroadcaster:
    """
    Utility class for broadcasting anomalies to all connected clients.
    """
    
    @staticmethod
    async def broadcast_anomaly(channel_layer, anomaly: dict):
        """Broadcast an anomaly to all connected clients."""
        try:
            await channel_layer.group_send(
                "market_anomalies",
                {
                    "type": "anomaly_broadcast",
                    "anomaly": anomaly
                }
            )
            logger.debug(f"📢 Broadcasted anomaly: {anomaly['type']} for {anomaly['item_name']}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast anomaly: {e}")


# Global broadcaster instance
anomaly_broadcaster = MarketAnomalyBroadcaster()