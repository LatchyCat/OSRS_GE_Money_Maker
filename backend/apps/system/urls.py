"""
URL configuration for system management endpoints.
"""

from django.urls import path
from . import views

app_name = 'system'

urlpatterns = [
    # Data refresh endpoints
    path('refresh-data/', views.refresh_data, name='refresh_data'),
    path('data-status/', views.data_freshness_status, name='data_freshness_status'),
]