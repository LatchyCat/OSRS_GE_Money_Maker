"""
URL configuration for osrs_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # AI Trading Interface (main feature)
    path("", include("apps.ai.urls")),
    path("ai/", include("apps.ai.urls")),
    
    # API endpoints
    path("api/v1/items/", include("apps.items.urls")),
    path("api/v1/planning/", include("apps.planning.urls")),
    path("api/v1/system/", include("apps.system.urls")),
    path("api/v1/prices/", include("apps.prices.urls")),
    path("api/v1/merchant/", include("apps.prices.merchant_urls")),
    path("api/v1/realtime/", include("apps.realtime_engine.urls")),
    path("api/v1/trading/", include("apps.trading_strategies.urls")),
    
    # AI API endpoints - direct access for frontend
    path("api/", include("apps.ai.urls")),
    
    # Health check
    path("health/", include("health_check.urls")),
]
