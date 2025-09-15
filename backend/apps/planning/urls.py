"""
URL configuration for goal planning API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    GoalPlanViewSet,
    StrategyDetailView,
    StrategyComparisonView,
    MarketAnalysisView,
    TimeEstimationView,
    PortfolioOptimizationView,
    GoalPlanStatsView
)

# Create router for ViewSet
router = DefaultRouter()
router.register(r'goal-plans', GoalPlanViewSet, basename='goalplan')

urlpatterns = [
    # ViewSet routes (includes CRUD operations and custom actions)
    path('', include(router.urls)),
    
    # Individual strategy detail
    path('strategies/<int:strategy_id>/', StrategyDetailView.as_view(), name='strategy-detail'),
    
    # Strategy comparison
    path('goal-plans/<uuid:plan_id>/compare/', StrategyComparisonView.as_view(), name='strategy-comparison'),
    
    # Market analysis
    path('market-analysis/', MarketAnalysisView.as_view(), name='market-analysis'),
    
    # Time estimation for strategies
    path('strategies/<int:strategy_id>/time-analysis/', TimeEstimationView.as_view(), name='time-estimation'),
    
    # Portfolio optimization
    path('portfolio-optimization/', PortfolioOptimizationView.as_view(), name='portfolio-optimization'),
    
    # Goal plan statistics
    path('stats/', GoalPlanStatsView.as_view(), name='goal-plan-stats'),
]

"""
API Endpoint Summary:

Goal Plan Management:
- GET /api/planning/goal-plans/ - List all goal plans for the session
- POST /api/planning/goal-plans/ - Create a new goal plan
- GET /api/planning/goal-plans/{plan_id}/ - Get specific goal plan
- PUT/PATCH /api/planning/goal-plans/{plan_id}/ - Update goal plan
- DELETE /api/planning/goal-plans/{plan_id}/ - Delete goal plan

Goal Plan Actions:
- GET /api/planning/goal-plans/{plan_id}/strategies/ - Get all strategies
- GET /api/planning/goal-plans/{plan_id}/recommended_strategy/ - Get recommended strategy
- POST /api/planning/goal-plans/{plan_id}/update_progress/ - Update progress
- GET /api/planning/goal-plans/{plan_id}/progress_history/ - Get progress history
- POST /api/planning/goal-plans/{plan_id}/regenerate_strategies/ - Regenerate strategies

Strategy Analysis:
- GET /api/planning/strategies/{strategy_id}/ - Get strategy details
- GET /api/planning/goal-plans/{plan_id}/compare/ - Compare all strategies
- GET /api/planning/strategies/{strategy_id}/time-analysis/ - Time estimation

Market & Portfolio:
- GET /api/planning/market-analysis/ - Current market analysis
- POST /api/planning/portfolio-optimization/ - Optimize portfolio allocation

Statistics:
- GET /api/planning/stats/ - Goal plan statistics
"""