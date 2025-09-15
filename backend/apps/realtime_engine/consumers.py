"""
WebSocket Consumers for Real-Time Market Data

Handles WebSocket connections for streaming market updates, price alerts,
and real-time trading data to the frontend.
"""

import json
import logging
from typing import Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from apps.items.models import Item
from apps.realtime_engine.models import MarketMomentum, VolumeAnalysis, MarketEvent
from services.streaming_data_manager import streaming_manager

logger = logging.getLogger(__name__)


class MarketDataConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time market data streaming.
    """
    
    async def connect(self):
        """Accept WebSocket connection and join market updates group."""
        try:
            await self.channel_layer.group_add(
                'market_updates',
                self.channel_name
            )
            await self.accept()
            
            # Send initial data
            await self.send_initial_data()
            
            logger.info(f"Market data WebSocket connected: {self.channel_name}")
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Remove from market updates group on disconnect."""
        try:
            await self.channel_layer.group_discard(
                'market_updates',
                self.channel_name
            )
            logger.info(f"Market data WebSocket disconnected: {self.channel_name}")
        except Exception as e:
            logger.error(f"WebSocket disconnect error: {e}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'subscribe_item':
                await self.handle_item_subscription(data)
            elif message_type == 'unsubscribe_item':
                await self.handle_item_unsubscription(data)
            elif message_type == 'get_momentum':
                await self.send_momentum_data()
            elif message_type == 'get_volume_leaders':
                await self.send_volume_leaders()
            elif message_type == 'get_market_events':
                await self.send_market_events()
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
            await self.send_error("Internal server error")
    
    async def market_update(self, event):
        """Send market update to client."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'market_update',
                'data': event['data']
            }))
        except Exception as e:
            logger.error(f"Failed to send market update: {e}")
    
    async def price_alert(self, event):
        """Send price alert to client."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'price_alert',
                'data': event['data']
            }))
        except Exception as e:
            logger.error(f"Failed to send price alert: {e}")
    
    async def volume_surge(self, event):
        """Send volume surge notification."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'volume_surge',
                'data': event['data']
            }))
        except Exception as e:
            logger.error(f"Failed to send volume surge: {e}")
    
    async def send_initial_data(self):
        """Send initial market data on connection."""
        try:
            # Get cached hot market data
            hot_data = cache.get('streaming:hot_items', {})
            
            if hot_data:
                await self.send(text_data=json.dumps({
                    'type': 'initial_data',
                    'data': hot_data
                }))
            else:
                # Generate initial data if not cached
                initial_data = await self.get_initial_market_data()
                await self.send(text_data=json.dumps({
                    'type': 'initial_data',
                    'data': initial_data
                }))
                
        except Exception as e:
            logger.error(f"Failed to send initial data: {e}")
    
    async def send_momentum_data(self):
        """Send current momentum leaders."""
        try:
            momentum_data = await self.get_momentum_leaders()
            await self.send(text_data=json.dumps({
                'type': 'momentum_data',
                'data': momentum_data
            }))
        except Exception as e:
            logger.error(f"Failed to send momentum data: {e}")
    
    async def send_volume_leaders(self):
        """Send volume surge leaders."""
        try:
            volume_data = await self.get_volume_surge_leaders()
            await self.send(text_data=json.dumps({
                'type': 'volume_leaders',
                'data': volume_data
            }))
        except Exception as e:
            logger.error(f"Failed to send volume data: {e}")
    
    async def send_market_events(self):
        """Send recent market events."""
        try:
            events_data = await self.get_recent_market_events()
            await self.send(text_data=json.dumps({
                'type': 'market_events',
                'data': events_data
            }))
        except Exception as e:
            logger.error(f"Failed to send market events: {e}")
    
    async def send_error(self, error_message: str):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))
    
    async def handle_item_subscription(self, data):
        """Handle item-specific subscription."""
        try:
            item_id = data.get('item_id')
            if not item_id:
                await self.send_error("Missing item_id")
                return
            
            # Join item-specific group
            await self.channel_layer.group_add(
                f'item_{item_id}',
                self.channel_name
            )
            
            # Send current item data
            item_data = await self.get_item_data(item_id)
            await self.send(text_data=json.dumps({
                'type': 'item_subscription_confirmed',
                'item_id': item_id,
                'data': item_data
            }))
            
        except Exception as e:
            logger.error(f"Item subscription error: {e}")
            await self.send_error("Failed to subscribe to item")
    
    async def handle_item_unsubscription(self, data):
        """Handle item unsubscription."""
        try:
            item_id = data.get('item_id')
            if not item_id:
                await self.send_error("Missing item_id")
                return
            
            # Leave item-specific group
            await self.channel_layer.group_discard(
                f'item_{item_id}',
                self.channel_name
            )
            
            await self.send(text_data=json.dumps({
                'type': 'item_unsubscription_confirmed',
                'item_id': item_id
            }))
            
        except Exception as e:
            logger.error(f"Item unsubscription error: {e}")
            await self.send_error("Failed to unsubscribe from item")
    
    # Database query methods
    
    @database_sync_to_async
    def get_initial_market_data(self) -> Dict[str, Any]:
        """Get initial market overview data."""
        try:
            # Top momentum items
            momentum_items = list(
                MarketMomentum.objects.filter(
                    momentum_score__gte=50
                ).select_related('item').order_by('-momentum_score')[:10]
            )
            
            # High volume items
            volume_items = list(
                VolumeAnalysis.objects.filter(
                    current_daily_volume__gte=1000
                ).select_related('item').order_by('-current_daily_volume')[:10]
            )
            
            # Recent market events
            recent_events = list(
                MarketEvent.objects.filter(
                    is_active=True,
                    detected_at__gte=timezone.now() - timedelta(hours=2)
                ).order_by('-detected_at')[:5]
            )
            
            return {
                'momentum_items': [
                    {
                        'item_id': item.item.item_id,
                        'name': item.item.name,
                        'momentum_score': item.momentum_score,
                        'trend': item.trend_direction,
                        'velocity': item.price_velocity,
                    }
                    for item in momentum_items
                ],
                'volume_items': [
                    {
                        'item_id': item.item.item_id,
                        'name': item.item.name,
                        'volume': item.current_daily_volume,
                        'liquidity': item.liquidity_level,
                        'ratio': item.volume_ratio_daily,
                    }
                    for item in volume_items
                ],
                'market_events': [
                    {
                        'type': event.event_type,
                        'title': event.title,
                        'impact': event.impact_score,
                        'detected_at': event.detected_at.isoformat(),
                        'item_count': event.get_affected_items_count(),
                    }
                    for event in recent_events
                ],
                'timestamp': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to get initial market data: {e}")
            return {}
    
    @database_sync_to_async
    def get_momentum_leaders(self) -> Dict[str, Any]:
        """Get current momentum leaders."""
        try:
            momentum_items = list(
                MarketMomentum.objects.select_related('item')
                .order_by('-momentum_score')[:20]
            )
            
            return {
                'gaining_momentum': [
                    {
                        'item_id': item.item.item_id,
                        'name': item.item.name,
                        'momentum_score': item.momentum_score,
                        'trend': item.trend_direction,
                        'velocity': item.price_velocity,
                        'category': item.momentum_category,
                    }
                    for item in momentum_items if item.is_gaining_momentum
                ],
                'timestamp': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to get momentum leaders: {e}")
            return {}
    
    @database_sync_to_async
    def get_volume_surge_leaders(self) -> Dict[str, Any]:
        """Get volume surge leaders."""
        try:
            volume_items = list(
                VolumeAnalysis.objects.select_related('item')
                .filter(volume_ratio_daily__gte=1.5)  # 150%+ normal volume
                .order_by('-volume_ratio_daily')[:15]
            )
            
            return {
                'volume_surges': [
                    {
                        'item_id': item.item.item_id,
                        'name': item.item.name,
                        'current_volume': item.current_daily_volume,
                        'average_volume': item.average_daily_volume,
                        'ratio': item.volume_ratio_daily,
                        'liquidity': item.liquidity_level,
                        'surge_level': 'extreme' if item.volume_ratio_daily >= 3 else 'high',
                    }
                    for item in volume_items
                ],
                'timestamp': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to get volume surge leaders: {e}")
            return {}
    
    @database_sync_to_async
    def get_recent_market_events(self) -> Dict[str, Any]:
        """Get recent market events."""
        try:
            recent_events = list(
                MarketEvent.objects.filter(
                    is_active=True,
                    detected_at__gte=timezone.now() - timedelta(hours=4)
                ).order_by('-detected_at')[:10]
            )
            
            return {
                'events': [
                    {
                        'id': event.id,
                        'type': event.event_type,
                        'title': event.title,
                        'description': event.description,
                        'impact_score': event.impact_score,
                        'detected_at': event.detected_at.isoformat(),
                        'estimated_duration': event.estimated_duration_minutes,
                        'confidence': event.confidence,
                        'item_count': event.get_affected_items_count(),
                        'is_high_impact': event.is_high_impact,
                    }
                    for event in recent_events
                ],
                'timestamp': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to get recent market events: {e}")
            return {}
    
    @database_sync_to_async
    def get_item_data(self, item_id: int) -> Dict[str, Any]:
        """Get detailed data for a specific item."""
        try:
            item = Item.objects.get(item_id=item_id)
            
            # Get momentum data
            momentum = getattr(item, 'momentum', None)
            volume = getattr(item, 'volume_analysis', None)
            risk = getattr(item, 'risk_metrics', None)
            
            return {
                'item_id': item.item_id,
                'name': item.name,
                'momentum': {
                    'score': momentum.momentum_score if momentum else 0,
                    'trend': momentum.trend_direction if momentum else 'neutral',
                    'velocity': momentum.price_velocity if momentum else 0,
                } if momentum else None,
                'volume': {
                    'current': volume.current_daily_volume if volume else 0,
                    'liquidity': volume.liquidity_level if volume else 'minimal',
                    'flip_probability': volume.flip_completion_probability if volume else 0,
                } if volume else None,
                'risk': {
                    'score': risk.overall_risk_score if risk else 50,
                    'category': risk.risk_category if risk else 'medium',
                } if risk else None,
                'timestamp': timezone.now().isoformat(),
            }
            
        except Item.DoesNotExist:
            return {'error': 'Item not found'}
        except Exception as e:
            logger.error(f"Failed to get item data for {item_id}: {e}")
            return {'error': 'Internal server error'}


class TradingTerminalConsumer(AsyncWebsocketConsumer):
    """
    Advanced WebSocket consumer for trading terminal features.
    """
    
    async def connect(self):
        """Connect to trading terminal."""
        await self.accept()
        await self.channel_layer.group_add('trading_terminal', self.channel_name)
        logger.info(f"Trading terminal connected: {self.channel_name}")
    
    async def disconnect(self, close_code):
        """Disconnect from trading terminal."""
        await self.channel_layer.group_discard('trading_terminal', self.channel_name)
        logger.info(f"Trading terminal disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        """Handle trading terminal messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'portfolio_update':
                await self.handle_portfolio_update(data)
            elif message_type == 'capital_tracker':
                await self.handle_capital_tracking(data)
            elif message_type == 'flip_tracker':
                await self.handle_flip_tracking(data)
            
        except Exception as e:
            logger.error(f"Trading terminal error: {e}")
    
    async def handle_portfolio_update(self, data):
        """Handle portfolio update requests."""
        # Implementation for portfolio updates
        pass
    
    async def handle_capital_tracking(self, data):
        """Handle capital tracking updates."""
        # Implementation for capital tracking
        pass
    
    async def handle_flip_tracking(self, data):
        """Handle flip tracking updates."""
        # Implementation for flip tracking
        pass