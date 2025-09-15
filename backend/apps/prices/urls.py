"""
URL configuration for Prices API.
"""

from django.urls import path
from . import views

app_name = 'prices'

urlpatterns = [
    # Historical price endpoints
    path('historical/<int:item_id>/', views.historical_price_data, name='historical-price-data'),
    
    # Health check
    path('health/', views.price_api_health, name='price-health'),
]