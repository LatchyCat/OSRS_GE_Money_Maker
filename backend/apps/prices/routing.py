"""
WebSocket routing for real-time price updates and trading intelligence.

This module defines the WebSocket URL patterns for Django Channels,
connecting WebSocket paths to their respective consumer classes.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Main trading intelligence WebSocket
    re_path(r'ws/trading/$', consumers.TradingIntelligenceConsumer.as_asgi()),
    
    # Real-time price charts WebSocket
    re_path(r'ws/charts/$', consumers.PriceChartsConsumer.as_asgi()),
]