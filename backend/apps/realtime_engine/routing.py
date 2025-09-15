"""
WebSocket routing configuration for real-time market data.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/market-data/$', consumers.MarketDataConsumer.as_asgi()),
    re_path(r'ws/trading-terminal/$', consumers.TradingTerminalConsumer.as_asgi()),
]