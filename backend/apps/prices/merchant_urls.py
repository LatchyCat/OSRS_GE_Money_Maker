"""
URL configuration for merchant trading API endpoints.
"""

from django.urls import path
from . import merchant_views

app_name = 'merchant'

urlpatterns = [
    # AI Chat Endpoint
    path('chat/', merchant_views.MerchantAIChatView.as_view(), name='ai-chat'),
    
    # Market Opportunities
    path('opportunities/', merchant_views.get_market_opportunities, name='opportunities'),
    path('opportunities/analyze/', merchant_views.analyze_market_opportunities, name='analyze-opportunities'),
    
    # Market Trends
    path('trends/', merchant_views.get_market_trends, name='trends'),
    
    # Item Analysis
    path('items/<int:item_id>/analysis/', merchant_views.get_item_analysis, name='item-analysis'),
    
    # Market Overview
    path('overview/', merchant_views.get_market_overview, name='overview'),
]