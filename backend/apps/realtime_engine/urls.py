"""
URL configuration for the Real-Time Market Engine API.

Provides endpoints for seasonal patterns, forecasts, events, and recommendations.
"""

from django.urls import path
from . import views

app_name = 'realtime_engine'

urlpatterns = [
    # =============================================================================
    # SEASONAL PATTERN ENDPOINTS
    # =============================================================================
    
    # List all seasonal patterns with filtering
    path('seasonal/patterns/', views.SeasonalPatternListView.as_view(), name='seasonal_patterns_list'),
    
    # Get specific seasonal pattern by ID
    path('seasonal/patterns/<int:pk>/', views.SeasonalPatternDetailView.as_view(), name='seasonal_pattern_detail'),
    
    # Get latest seasonal pattern for specific item
    path('seasonal/patterns/item/<int:item_id>/', views.SeasonalPatternByItemView.as_view(), name='seasonal_pattern_by_item'),
    
    # =============================================================================
    # SEASONAL FORECAST ENDPOINTS
    # =============================================================================
    
    # List all seasonal forecasts with filtering
    path('seasonal/forecasts/', views.SeasonalForecastListView.as_view(), name='seasonal_forecasts_list'),
    
    # Get specific forecast by ID
    path('seasonal/forecasts/<int:pk>/', views.SeasonalForecastDetailView.as_view(), name='seasonal_forecast_detail'),
    
    # =============================================================================
    # SEASONAL EVENT ENDPOINTS
    # =============================================================================
    
    # List all seasonal events with filtering
    path('seasonal/events/', views.SeasonalEventListView.as_view(), name='seasonal_events_list'),
    
    # Get specific event by ID
    path('seasonal/events/<int:pk>/', views.SeasonalEventDetailView.as_view(), name='seasonal_event_detail'),
    
    # =============================================================================
    # SEASONAL RECOMMENDATION ENDPOINTS
    # =============================================================================
    
    # List all seasonal recommendations with filtering
    path('seasonal/recommendations/', views.SeasonalRecommendationListView.as_view(), name='seasonal_recommendations_list'),
    
    # Get specific recommendation by ID
    path('seasonal/recommendations/<int:pk>/', views.SeasonalRecommendationDetailView.as_view(), name='seasonal_recommendation_detail'),
    
    # =============================================================================
    # TECHNICAL ANALYSIS ENDPOINTS
    # =============================================================================
    
    # List all technical analyses
    path('technical/analyses/', views.TechnicalAnalysisListView.as_view(), name='technical_analyses_list'),
    
    # Get latest technical analysis for specific item
    path('technical/analyses/item/<int:item_id>/', views.TechnicalAnalysisByItemView.as_view(), name='technical_analysis_by_item'),
    
    # =============================================================================
    # MARKET DATA ENDPOINTS
    # =============================================================================
    
    # Market momentum data
    path('market/momentum/', views.MarketMomentumListView.as_view(), name='market_momentum_list'),
    
    # Sentiment analysis data
    path('market/sentiment/', views.SentimentAnalysisListView.as_view(), name='sentiment_analysis_list'),
    
    # Price predictions
    path('market/predictions/', views.PricePredictionListView.as_view(), name='price_predictions_list'),
    
    # Get latest price prediction for specific item
    path('market/predictions/item/<int:item_id>/', views.PricePredictionByItemView.as_view(), name='price_prediction_by_item'),
    
    # =============================================================================
    # ANALYTICS AND OVERVIEW ENDPOINTS
    # =============================================================================
    
    # Market overview dashboard data
    path('analytics/overview/', views.market_overview, name='market_overview'),
    
    # Seasonal analytics dashboard data
    path('analytics/seasonal/', views.seasonal_analytics, name='seasonal_analytics'),
    
    # Forecast accuracy statistics
    path('analytics/forecast-accuracy/', views.forecast_accuracy_stats, name='forecast_accuracy_stats'),
]