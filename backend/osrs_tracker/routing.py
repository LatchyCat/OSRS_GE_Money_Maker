"""
WebSocket URL routing for osrs_tracker project.
"""

from django.urls import re_path, include
from apps.realtime.consumers import PriceUpdatesConsumer
from apps.realtime_engine.consumers import MarketDataConsumer, TradingTerminalConsumer
from apps.realtime_engine.anomaly_consumer import AnomalyAlertConsumer
from apps.prices.consumers import TradingIntelligenceConsumer, PriceChartsConsumer

websocket_urlpatterns = [
    # Legacy price updates
    re_path(r"ws/prices/$", PriceUpdatesConsumer.as_asgi()),
    
    # New real-time market data
    re_path(r"ws/market-data/$", MarketDataConsumer.as_asgi()),
    re_path(r"ws/trading-terminal/$", TradingTerminalConsumer.as_asgi()),
    
    # Real-time anomaly alerts
    re_path(r"ws/anomaly-alerts/$", AnomalyAlertConsumer.as_asgi()),
    
    # AI-powered trading intelligence and reactive system
    re_path(r"ws/trading/$", TradingIntelligenceConsumer.as_asgi()),
    re_path(r"ws/charts/$", PriceChartsConsumer.as_asgi()),
]