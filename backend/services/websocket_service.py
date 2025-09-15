"""
WebSocket service for sending real-time updates to connected clients.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

from apps.realtime.models import WebSocketConnection, PriceAlert

logger = logging.getLogger(__name__)


class WebSocketService:
    """
    Service for managing WebSocket communications and real-time updates.
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def send_price_update(
        self, 
        item_data: Dict[str, Any], 
        price_data: Dict[str, Any],
        profit_data: Dict[str, Any] = None
    ):
        """
        Send price update to all connected WebSocket clients.
        
        Args:
            item_data: Item information
            price_data: Updated price information
            profit_data: Calculated profit information
        """
        try:
            message = {
                'type': 'price_update',
                'data': {
                    'item': item_data,
                    'prices': price_data,
                    'profits': profit_data or {},
                    'timestamp': timezone.now().isoformat()
                }
            }
            
            # Send to all clients in price_updates group
            async_to_sync(self.channel_layer.group_send)(
                "price_updates",
                {
                    'type': 'price_update',
                    'data': message['data']
                }
            )
            
            # Check for triggered alerts
            self._check_price_alerts(item_data, price_data, profit_data)
            
            logger.debug(f"Sent price update for item {item_data.get('name', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to send price update: {e}")
    
    def send_ai_recommendation(
        self,
        recommendation_data: Dict[str, Any],
        target_sessions: List[str] = None
    ):
        """
        Send AI recommendation to WebSocket clients.
        
        Args:
            recommendation_data: AI recommendation data
            target_sessions: Optional list of session keys to target
        """
        try:
            message = {
                'type': 'ai_recommendation',
                'data': {
                    'recommendation': recommendation_data,
                    'timestamp': timezone.now().isoformat()
                }
            }
            
            if target_sessions:
                # Send to specific sessions
                for session_key in target_sessions:
                    connections = WebSocketConnection.objects.filter(
                        session_key=session_key,
                        is_active=True
                    )
                    
                    for connection in connections:
                        async_to_sync(self.channel_layer.send)(
                            connection.channel_name,
                            {
                                'type': 'ai_recommendation',
                                'data': message['data']
                            }
                        )
            else:
                # Send to all clients
                async_to_sync(self.channel_layer.group_send)(
                    "price_updates",
                    {
                        'type': 'ai_recommendation',
                        'data': message['data']
                    }
                )
            
            logger.debug("Sent AI recommendation update")
            
        except Exception as e:
            logger.error(f"Failed to send AI recommendation: {e}")
    
    def send_market_summary(self, summary_data: Dict[str, Any]):
        """
        Send market summary update to all clients.
        
        Args:
            summary_data: Market summary data from AI
        """
        try:
            message = {
                'type': 'market_summary',
                'data': {
                    'summary': summary_data,
                    'timestamp': timezone.now().isoformat()
                }
            }
            
            async_to_sync(self.channel_layer.group_send)(
                "price_updates",
                {
                    'type': 'market_update',
                    'data': message['data']
                }
            )
            
            logger.debug("Sent market summary update")
            
        except Exception as e:
            logger.error(f"Failed to send market summary: {e}")
    
    def send_alert(
        self,
        alert_data: Dict[str, Any],
        session_key: str
    ):
        """
        Send alert to a specific user session.
        
        Args:
            alert_data: Alert information
            session_key: Target session key
        """
        try:
            connections = WebSocketConnection.objects.filter(
                session_key=session_key,
                is_active=True
            )
            
            message = {
                'type': 'alert',
                'data': {
                    'alert': alert_data,
                    'timestamp': timezone.now().isoformat()
                }
            }
            
            for connection in connections:
                async_to_sync(self.channel_layer.send)(
                    connection.channel_name,
                    {
                        'type': 'profit_alert',
                        'data': message['data']
                    }
                )
            
            logger.debug(f"Sent alert to session {session_key}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def _check_price_alerts(
        self,
        item_data: Dict[str, Any],
        price_data: Dict[str, Any],
        profit_data: Dict[str, Any] = None
    ):
        """
        Check if any price alerts should be triggered.
        
        Args:
            item_data: Item information
            price_data: Price data
            profit_data: Profit data
        """
        try:
            item_id = item_data.get('item_id')
            if not item_id:
                return
            
            # Get active alerts for this item
            alerts = PriceAlert.objects.filter(
                item__item_id=item_id,
                is_active=True
            )
            
            for alert in alerts:
                triggered = False
                alert_message = ""
                
                high_price = price_data.get('high_price')
                low_price = price_data.get('low_price')
                profit = profit_data.get('current_profit', 0) if profit_data else 0
                
                if alert.alert_type == 'price_below' and high_price:
                    if high_price <= alert.threshold_value:
                        triggered = True
                        alert_message = f"{item_data['name']} price dropped to {high_price:,}gp (target: {alert.threshold_value:,}gp)"
                
                elif alert.alert_type == 'price_above' and high_price:
                    if high_price >= alert.threshold_value:
                        triggered = True
                        alert_message = f"{item_data['name']} price rose to {high_price:,}gp (target: {alert.threshold_value:,}gp)"
                
                elif alert.alert_type == 'profit_above' and profit:
                    if profit >= alert.threshold_value:
                        triggered = True
                        alert_message = f"{item_data['name']} profit reached {profit:,}gp (target: {alert.threshold_value:,}gp)"
                
                if triggered:
                    # Send alert
                    alert_data = {
                        'item_name': item_data['name'],
                        'item_id': item_id,
                        'alert_type': alert.alert_type,
                        'message': alert_message,
                        'threshold': alert.threshold_value,
                        'current_value': high_price or profit
                    }
                    
                    self.send_alert(alert_data, alert.session_key)
                    
                    # Update alert
                    alert.triggered_count += 1
                    alert.last_triggered = timezone.now()
                    alert.save()
            
        except Exception as e:
            logger.error(f"Error checking price alerts: {e}")
    
    def broadcast_system_message(self, message: str, message_type: str = "info"):
        """
        Broadcast a system message to all connected clients.
        
        Args:
            message: Message content
            message_type: Type of message (info, warning, error)
        """
        try:
            async_to_sync(self.channel_layer.group_send)(
                "price_updates",
                {
                    'type': 'system_message',
                    'data': {
                        'message': message,
                        'message_type': message_type,
                        'timestamp': timezone.now().isoformat()
                    }
                }
            )
            
            logger.info(f"Broadcast system message: {message}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast system message: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about WebSocket connections.
        
        Returns:
            Dictionary with connection statistics
        """
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            # Active connections
            active_connections = WebSocketConnection.objects.filter(is_active=True).count()
            
            # Connections in last hour
            hour_ago = timezone.now() - timedelta(hours=1)
            recent_connections = WebSocketConnection.objects.filter(
                connected_at__gte=hour_ago
            ).count()
            
            # Connection types breakdown
            connection_types = WebSocketConnection.objects.filter(
                is_active=True
            ).values('connection_type').distinct().count()
            
            return {
                'active_connections': active_connections,
                'recent_connections': recent_connections,
                'connection_types': connection_types,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return {
                'active_connections': 0,
                'recent_connections': 0,
                'connection_types': 0,
                'error': str(e)
            }