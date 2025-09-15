"""
WebSocket consumers for real-time price updates and trading intelligence.

This module provides WebSocket consumers that integrate with the ReactiveTrading Engine
to deliver real-time market updates, recommendation changes, and trading alerts to frontend clients.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser

from services.reactive_trading_engine import ReactiveTradingEngine, MarketEvent, RecommendationUpdate
from apps.prices.models import HistoricalPricePoint, PriceTrend, MarketAlert

logger = logging.getLogger(__name__)


class TradingIntelligenceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time trading intelligence updates.
    
    Handles:
    - Real-time price updates
    - Recommendation changes
    - Market alerts and signals
    - Pattern detection notifications
    - Volume surge alerts
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trading_engine: Optional[ReactiveTradingEngine] = None
        self.user_id: Optional[int] = None
        self.subscriptions: set = set()
        self.group_name = "trading_intelligence"
    
    async def connect(self):
        """Handle WebSocket connection."""
        try:
            # Accept the connection
            await self.accept()
            
            # Get user from scope (if authenticated)
            user = self.scope.get("user")
            if user and not isinstance(user, AnonymousUser):
                self.user_id = user.id
            
            # Join the trading intelligence group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            # Initialize reactive trading engine connection
            self.trading_engine = ReactiveTradingEngine.get_instance()
            if self.trading_engine:
                await self.trading_engine.subscribe_to_updates(self.channel_name)
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'timestamp': timezone.now().isoformat(),
                'message': 'Connected to trading intelligence stream'
            }))
            
            logger.info(f"Trading intelligence WebSocket connected: {self.channel_name}")
            
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        try:
            # Unsubscribe from trading engine updates
            if self.trading_engine:
                await self.trading_engine.unsubscribe_from_updates(self.channel_name)
            
            # Leave the trading intelligence group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            
            logger.info(f"Trading intelligence WebSocket disconnected: {self.channel_name}")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages from client."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'subscribe_to_item':
                await self._handle_item_subscription(data)
            elif message_type == 'subscribe_to_route':
                await self._handle_route_subscription(data)
            elif message_type == 'unsubscribe':
                await self._handle_unsubscription(data)
            elif message_type == 'unsubscribe_from_item':
                # Handle legacy unsubscribe_from_item messages (convert to standard unsubscribe)
                await self._handle_legacy_item_unsubscription(data)
            elif message_type == 'get_current_recommendations':
                await self._handle_recommendations_request(data)
            elif message_type == 'get_market_alerts':
                await self._handle_alerts_request(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
    
    async def _handle_item_subscription(self, data: Dict[str, Any]):
        """Handle subscription to specific item updates."""
        item_id = data.get('item_id')
        if not item_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'item_id is required'
            }))
            return
        
        # Add to subscriptions
        subscription_key = f"item_{item_id}"
        self.subscriptions.add(subscription_key)
        
        # Subscribe to item-specific updates in trading engine
        if self.trading_engine:
            await self.trading_engine.subscribe_to_item_updates(item_id, self.channel_name)
        
        await self.send(text_data=json.dumps({
            'type': 'subscription_confirmed',
            'subscription': subscription_key,
            'message': f'Subscribed to updates for item {item_id}'
        }))
    
    async def _handle_route_subscription(self, data: Dict[str, Any]):
        """Handle subscription to trading route updates (e.g., high_alch, flipping)."""
        route_type = data.get('route_type')
        if not route_type:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'route_type is required'
            }))
            return
        
        # Add to subscriptions
        subscription_key = f"route_{route_type}"
        self.subscriptions.add(subscription_key)
        
        # Subscribe to route-specific updates in trading engine
        if self.trading_engine:
            await self.trading_engine.subscribe_to_route_updates(route_type, self.channel_name)
        
        await self.send(text_data=json.dumps({
            'type': 'subscription_confirmed',
            'subscription': subscription_key,
            'message': f'Subscribed to updates for {route_type} route'
        }))
    
    async def _handle_unsubscription(self, data: Dict[str, Any]):
        """Handle unsubscription from updates."""
        subscription = data.get('subscription')
        if subscription in self.subscriptions:
            self.subscriptions.remove(subscription)
            
            # Unsubscribe from trading engine
            if self.trading_engine:
                if subscription.startswith('item_'):
                    item_id = subscription.replace('item_', '')
                    await self.trading_engine.unsubscribe_from_item_updates(item_id, self.channel_name)
                elif subscription.startswith('route_'):
                    route_type = subscription.replace('route_', '')
                    await self.trading_engine.unsubscribe_from_route_updates(route_type, self.channel_name)
            
            await self.send(text_data=json.dumps({
                'type': 'unsubscription_confirmed',
                'subscription': subscription
            }))
    
    async def _handle_legacy_item_unsubscription(self, data: Dict[str, Any]):
        """Handle legacy unsubscribe_from_item messages by converting to standard unsubscribe format."""
        item_id = data.get('item_id')
        if not item_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'item_id is required for unsubscribe_from_item'
            }))
            return
        
        # Convert to standard unsubscribe format
        subscription_key = f"item_{item_id}"
        
        logger.info(f"Converting legacy unsubscribe_from_item to standard unsubscribe for item {item_id}")
        
        # Handle as standard unsubscription
        if subscription_key in self.subscriptions:
            self.subscriptions.remove(subscription_key)
            
            # Unsubscribe from trading engine
            if self.trading_engine:
                await self.trading_engine.unsubscribe_from_item_updates(item_id, self.channel_name)
            
            await self.send(text_data=json.dumps({
                'type': 'unsubscription_confirmed',
                'subscription': subscription_key,
                'message': f'Legacy unsubscribe_from_item converted to standard unsubscribe for item {item_id}'
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'No active subscription found for item {item_id}'
            }))
    
    async def _handle_recommendations_request(self, data: Dict[str, Any]):
        """Handle request for current recommendations."""
        route_type = data.get('route_type', 'all')
        
        try:
            # Get current recommendations from trading engine
            if self.trading_engine:
                recommendations = await self.trading_engine.get_current_recommendations(route_type)
                
                await self.send(text_data=json.dumps({
                    'type': 'current_recommendations',
                    'route_type': route_type,
                    'recommendations': recommendations,
                    'timestamp': timezone.now().isoformat()
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Trading engine not available'
                }))
                
        except Exception as e:
            logger.error(f"Error fetching recommendations: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to fetch recommendations'
            }))
    
    async def _handle_alerts_request(self, data: Dict[str, Any]):
        """Handle request for current market alerts."""
        try:
            # Fetch recent market alerts from database
            alerts = await self._get_recent_market_alerts()
            
            await self.send(text_data=json.dumps({
                'type': 'market_alerts',
                'alerts': alerts,
                'timestamp': timezone.now().isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Error fetching market alerts: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to fetch market alerts'
            }))
    
    @database_sync_to_async
    def _get_recent_market_alerts(self) -> list:
        """Get recent market alerts from database."""
        try:
            # Get alerts from the last 24 hours
            recent_alerts = MarketAlert.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(hours=24)
            ).order_by('-created_at')[:50]
            
            return [
                {
                    'id': alert.id,
                    'item_id': alert.item.item_id if alert.item else None,
                    'item_name': alert.item.name if alert.item else None,
                    'alert_type': alert.alert_type,
                    'priority': alert.priority,
                    'message': alert.message,
                    'confidence': float(alert.confidence),
                    'is_active': alert.is_active,
                    'created_at': alert.created_at.isoformat()
                }
                for alert in recent_alerts
            ]
        except Exception as e:
            logger.error(f"Error querying market alerts: {e}")
            return []
    
    # Channel layer event handlers (called by ReactiveTrading Engine)
    
    async def market_event_update(self, event):
        """Handle market event updates from channel layer."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'market_event',
                'event_type': event['event_type'],
                'item_id': event.get('item_id'),
                'data': event['data'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending market event: {e}")
    
    async def recommendation_update(self, event):
        """Handle recommendation updates from channel layer."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'recommendation_update',
                'route_type': event['route_type'],
                'update_type': event['update_type'],
                'recommendations': event['recommendations'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending recommendation update: {e}")
    
    async def price_update(self, event):
        """Handle real-time price updates from channel layer."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'price_update',
                'item_id': event['item_id'],
                'high_price': event['high_price'],
                'low_price': event['low_price'],
                'high_volume': event['high_volume'],
                'low_volume': event['low_volume'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending price update: {e}")
    
    async def pattern_detected(self, event):
        """Handle pattern detection notifications from channel layer."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'pattern_detected',
                'item_id': event['item_id'],
                'pattern_name': event['pattern_name'],
                'confidence': event['confidence'],
                'predicted_target': event['predicted_target'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending pattern detection: {e}")
    
    async def volume_surge(self, event):
        """Handle volume surge alerts from channel layer."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'volume_surge',
                'item_id': event['item_id'],
                'current_volume': event['current_volume'],
                'average_volume': event['average_volume'],
                'surge_factor': event['surge_factor'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending volume surge alert: {e}")


class PriceChartsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer specifically for real-time price chart updates.
    
    Optimized for high-frequency price data streaming to chart components.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscribed_items: set = set()
        self.chart_timeframe = '5m'  # Default timeframe
    
    async def connect(self):
        """Handle WebSocket connection for price charts."""
        await self.accept()
        
        # Join the price charts group
        await self.channel_layer.group_add(
            "price_charts",
            self.channel_name
        )
        
        await self.send(text_data=json.dumps({
            'type': 'chart_connection_established',
            'timestamp': timezone.now().isoformat()
        }))
        
        logger.info(f"Price charts WebSocket connected: {self.channel_name}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            "price_charts",
            self.channel_name
        )
        
        logger.info(f"Price charts WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        """Handle incoming messages for chart subscriptions."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'subscribe_chart':
                item_id = data.get('item_id')
                timeframe = data.get('timeframe', '5m')
                
                if item_id:
                    self.subscribed_items.add(item_id)
                    self.chart_timeframe = timeframe
                    
                    # Send historical chart data
                    await self._send_historical_chart_data(item_id, timeframe)
                    
                    await self.send(text_data=json.dumps({
                        'type': 'chart_subscription_confirmed',
                        'item_id': item_id,
                        'timeframe': timeframe
                    }))
            
            elif message_type == 'unsubscribe_chart':
                item_id = data.get('item_id')
                if item_id in self.subscribed_items:
                    self.subscribed_items.remove(item_id)
                    
                    await self.send(text_data=json.dumps({
                        'type': 'chart_unsubscription_confirmed',
                        'item_id': item_id
                    }))
                    
        except Exception as e:
            logger.error(f"Error handling chart message: {e}")
    
    async def _send_historical_chart_data(self, item_id: int, timeframe: str):
        """Send historical chart data for initial chart population."""
        try:
            # Get historical data based on timeframe
            hours_back = 24 if timeframe == '5m' else 168  # 24h for 5m, 1 week for 1h
            
            historical_data = await self._get_historical_chart_data(item_id, hours_back)
            
            await self.send(text_data=json.dumps({
                'type': 'historical_chart_data',
                'item_id': item_id,
                'timeframe': timeframe,
                'data': historical_data,
                'timestamp': timezone.now().isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Error sending historical chart data: {e}")
    
    @database_sync_to_async
    def _get_historical_chart_data(self, item_id: int, hours_back: int) -> list:
        """Get historical price data for charts."""
        try:
            cutoff_time = timezone.now() - timezone.timedelta(hours=hours_back)
            
            historical_points = HistoricalPricePoint.objects.filter(
                item__item_id=item_id,
                timestamp__gte=cutoff_time
            ).order_by('timestamp')[:500]  # Limit to 500 points
            
            return [
                {
                    'timestamp': point.timestamp.isoformat(),
                    'high_price': point.high_price,
                    'low_price': point.low_price,
                    'high_volume': point.high_volume,
                    'low_volume': point.low_volume
                }
                for point in historical_points
            ]
            
        except Exception as e:
            logger.error(f"Error querying historical chart data: {e}")
            return []
    
    # Channel layer event handlers
    
    async def chart_price_update(self, event):
        """Handle real-time price updates for charts."""
        item_id = event.get('item_id')
        
        # Only send updates for subscribed items
        if item_id in self.subscribed_items:
            try:
                await self.send(text_data=json.dumps({
                    'type': 'chart_price_update',
                    'item_id': item_id,
                    'timestamp': event['timestamp'],
                    'high_price': event['high_price'],
                    'low_price': event['low_price'],
                    'high_volume': event['high_volume'],
                    'low_volume': event['low_volume']
                }))
            except Exception as e:
                logger.error(f"Error sending chart price update: {e}")