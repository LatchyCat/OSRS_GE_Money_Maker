from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    # API endpoints - these will be accessed as /api/trading-query/ from main urls.py
    path('trading-query/', views.ai_trading_query, name='trading_query'),
    path('debug-test/', views.ai_debug_test, name='debug_test'),  
    path('performance/', views.multi_agent_performance, name='multi_agent_performance'),
    
    # High Alchemy AI endpoints
    path('high-alchemy-chat/', views.high_alchemy_ai_chat, name='high_alchemy_chat'),
    
    # Class-based view alternatives (for future use)
    path('interface/', views.AITradingView.as_view(), name='trading_view'),
    path('query/', views.AITradingQueryView.as_view(), name='query_view'),
]