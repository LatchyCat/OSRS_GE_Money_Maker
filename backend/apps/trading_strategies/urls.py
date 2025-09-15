from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    TradingStrategyViewSet,
    DecantingOpportunityViewSet,
    SetCombiningOpportunityViewSet,
    FlippingOpportunityViewSet,
    CraftingOpportunityViewSet,
    MarketConditionSnapshotViewSet,
    StrategyPerformanceViewSet,
    MassOperationsViewSet
)
from .money_maker_viewsets import (
    MoneyMakerStrategyViewSet,
    BondFlippingStrategyViewSet,
    AdvancedDecantingStrategyViewSet,
    EnhancedSetCombiningStrategyViewSet,
    RuneMagicStrategyViewSet,
    MoneyMakerOpportunityViewSet,
    CapitalProgressionAdvisorViewSet,
    MoneyMakerAnalyticsViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'strategies', TradingStrategyViewSet, basename='strategy')
router.register(r'decanting', DecantingOpportunityViewSet, basename='decanting')
router.register(r'set-combining', SetCombiningOpportunityViewSet, basename='set-combining')
router.register(r'flipping', FlippingOpportunityViewSet, basename='flipping')
router.register(r'crafting', CraftingOpportunityViewSet, basename='crafting')
router.register(r'market-conditions', MarketConditionSnapshotViewSet, basename='market-conditions')
router.register(r'performance', StrategyPerformanceViewSet, basename='performance')
router.register(r'mass-operations', MassOperationsViewSet, basename='mass-operations')

# Money Maker API endpoints
router.register(r'money-makers', MoneyMakerStrategyViewSet, basename='money-maker')
router.register(r'bond-flipping', BondFlippingStrategyViewSet, basename='bond-flipping')
router.register(r'advanced-decanting', AdvancedDecantingStrategyViewSet, basename='advanced-decanting')
router.register(r'enhanced-set-combining', EnhancedSetCombiningStrategyViewSet, basename='enhanced-set-combining')
router.register(r'rune-magic', RuneMagicStrategyViewSet, basename='rune-magic')
router.register(r'opportunities', MoneyMakerOpportunityViewSet, basename='opportunities')
router.register(r'capital-progression', CapitalProgressionAdvisorViewSet, basename='capital-progression')
router.register(r'analytics', MoneyMakerAnalyticsViewSet, basename='analytics')

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
]

# Named URL patterns for easy reverse lookups
app_name = 'trading_strategies'