"""
URL configuration for Items API.
"""

from django.urls import path
from . import views

app_name = 'items'

urlpatterns = [
    # Item CRUD endpoints
    path('', views.ItemListView.as_view(), name='item-list'),
    path('<int:item_id>/', views.ItemDetailView.as_view(), name='item-detail'),
    
    # Search endpoints
    path('search/', views.search_items, name='search-items'),
    path('<int:item_id>/similar/', views.get_similar_items, name='similar-items'),
    
    # AI-powered endpoints
    path('recommendations/', views.get_profit_recommendations, name='profit-recommendations'),
    path('<int:item_id>/analyze/', views.analyze_item, name='analyze-item'),
    
    # Health check
    path('health/', views.api_health_check, name='health-check'),
    
    # Debug and verification endpoints
    path('<int:item_id>/price-debug/', views.price_verification_debug, name='price-debug'),
]