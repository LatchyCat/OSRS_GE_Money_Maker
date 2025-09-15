"""
API views for goal planning functionality.
"""

import uuid
import logging
import statistics
from datetime import timedelta
from django.utils import timezone
from django.http import Http404
from rest_framework import status, generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Avg, Max, Count

from .models import GoalPlan, Strategy, StrategyItem, ProgressUpdate, StrategyRevision
from .serializers import (
    GoalPlanSerializer, CreateGoalPlanSerializer, StrategySerializer,
    StrategyItemSerializer, ProgressUpdateSerializer, UpdateProgressSerializer,
    StrategyRevisionSerializer, StrategyComparisonSerializer,
    MarketAnalysisSerializer, StrategyTimeBreakdownSerializer,
    RiskAnalysisSerializer
)
from .services import GoalPlanningService, TimeEstimator, RiskAnalyzer, PortfolioOptimizer
from .goal_planning_adapter import goal_planning_adapter
from asgiref.sync import async_to_sync, sync_to_async
from apps.prices.models import ProfitCalculation

logger = logging.getLogger(__name__)


class GoalPlanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing goal plans.
    
    Provides CRUD operations for goal plans and generates strategies.
    """
    
    serializer_class = GoalPlanSerializer
    lookup_field = 'plan_id'
    lookup_value_regex = '[0-9a-f-]+'
    
    def get_queryset(self):
        """Filter by session key for anonymous users."""
        session_key = self.request.session.session_key
        if not session_key:
            # Create session if it doesn't exist
            self.request.session.create()
            session_key = self.request.session.session_key
        
        return GoalPlan.objects.filter(
            session_key=session_key,
            is_active=True
        ).prefetch_related('strategies__items__item').order_by('-created_at')
    
    def get_object(self):
        """Get goal plan by plan_id."""
        try:
            plan_id = self.kwargs['plan_id']
            session_key = self.request.session.session_key
            return GoalPlan.objects.get(
                plan_id=plan_id,
                session_key=session_key,
                is_active=True
            )
        except (GoalPlan.DoesNotExist, ValueError):
            raise Http404("Goal plan not found")
    
    def create(self, request, *args, **kwargs):
        """Create a new goal plan and generate strategies."""
        serializer = CreateGoalPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Ensure session exists
        if not request.session.session_key:
            request.session.create()
        
        # Create goal plan using the adapter service
        goal_plan = async_to_sync(goal_planning_adapter.create_goal_plan_with_strategies)(
            session_key=request.session.session_key,
            current_gp=serializer.validated_data['current_gp'],
            goal_gp=serializer.validated_data['goal_gp'],
            risk_tolerance=serializer.validated_data.get('risk_tolerance', 'moderate')
        )
        
        # Serialize the result
        response_serializer = GoalPlanSerializer(goal_plan)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def strategies(self, request, plan_id=None):
        """Get all strategies for a goal plan."""
        goal_plan = self.get_object()
        strategies = goal_plan.strategies.filter(is_active=True).order_by('-feasibility_score')
        serializer = StrategySerializer(strategies, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def recommended_strategy(self, request, plan_id=None):
        """Get the recommended strategy for a goal plan."""
        goal_plan = self.get_object()
        try:
            recommended = goal_plan.strategies.get(is_recommended=True, is_active=True)
            serializer = StrategySerializer(recommended)
            return Response(serializer.data)
        except Strategy.DoesNotExist:
            return Response(
                {"error": "No recommended strategy found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, plan_id=None):
        """Update progress toward the goal."""
        goal_plan = self.get_object()
        serializer = UpdateProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        current_gp = serializer.validated_data['current_gp']
        market_notes = serializer.validated_data.get('market_notes', '')
        
        # Calculate progress metrics
        profit_made = max(0, current_gp - goal_plan.current_gp)
        remaining_profit = max(0, goal_plan.goal_gp - current_gp)
        completion_pct = min(100.0, (current_gp / goal_plan.goal_gp) * 100)
        days_elapsed = (timezone.now() - goal_plan.created_at).total_seconds() / 86400
        
        # Determine if on track
        recommended_strategy = goal_plan.strategies.filter(is_recommended=True).first()
        is_on_track = True
        needs_update = False
        
        if recommended_strategy and recommended_strategy.estimated_days > 0:
            expected_progress = (days_elapsed / recommended_strategy.estimated_days) * 100
            is_on_track = completion_pct >= (expected_progress * 0.8)  # 80% of expected
            needs_update = completion_pct < (expected_progress * 0.6)  # 60% of expected
        
        # Create progress update
        progress_update = ProgressUpdate.objects.create(
            goal_plan=goal_plan,
            current_gp_at_time=current_gp,
            profit_made=profit_made,
            remaining_profit_needed=remaining_profit,
            completion_percentage=completion_pct,
            days_elapsed=days_elapsed,
            active_strategy=recommended_strategy,
            market_notes=market_notes,
            is_on_track=is_on_track,
            needs_strategy_update=needs_update
        )
        
        # Update goal plan if needed
        if needs_update:
            goal_plan.is_achievable = remaining_profit <= current_gp * 10  # Can still achieve with 10x leverage
            goal_plan.save()
        
        serializer = ProgressUpdateSerializer(progress_update)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def progress_history(self, request, plan_id=None):
        """Get progress history for a goal plan."""
        goal_plan = self.get_object()
        progress_updates = goal_plan.progress_updates.all().order_by('-created_at')
        serializer = ProgressUpdateSerializer(progress_updates, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def regenerate_strategies(self, request, plan_id=None):
        """Regenerate strategies with current market data."""
        goal_plan = self.get_object()
        
        # Mark old strategies as inactive
        goal_plan.strategies.update(is_active=False)
        
        # Generate new strategies
        goal_planning_service = GoalPlanningService()
        goal_planning_service.generate_strategies(goal_plan)
        
        # Update timestamp
        goal_plan.last_calculated = timezone.now()
        goal_plan.save()
        
        # Return updated goal plan
        serializer = GoalPlanSerializer(goal_plan)
        return Response(serializer.data)


class StrategyDetailView(generics.RetrieveAPIView):
    """
    Detailed view for a specific strategy.
    """
    
    serializer_class = StrategySerializer
    
    def get_object(self):
        strategy_id = self.kwargs['strategy_id']
        session_key = self.request.session.session_key
        
        try:
            return Strategy.objects.select_related('goal_plan').prefetch_related(
                'items__item'
            ).get(
                id=strategy_id,
                goal_plan__session_key=session_key,
                is_active=True
            )
        except Strategy.DoesNotExist:
            raise Http404("Strategy not found")


class StrategyComparisonView(APIView):
    """
    Compare multiple strategies side by side.
    """
    
    def get(self, request, plan_id):
        """Get comparison data for all strategies in a goal plan."""
        try:
            session_key = request.session.session_key
            goal_plan = GoalPlan.objects.get(
                plan_id=plan_id,
                session_key=session_key,
                is_active=True
            )
        except GoalPlan.DoesNotExist:
            return Response(
                {"error": "Goal plan not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        strategies = goal_plan.strategies.filter(is_active=True)
        
        comparison_data = []
        for strategy in strategies:
            comparison_data.append({
                'strategy_id': strategy.id,
                'name': strategy.name,
                'strategy_type': strategy.strategy_type,
                'estimated_days': strategy.estimated_days,
                'estimated_profit': strategy.estimated_profit,
                'required_investment': strategy.required_initial_investment,
                'roi_percentage': strategy.roi_percentage,
                'risk_level': strategy.risk_level,
                'feasibility_score': strategy.feasibility_score,
                'is_recommended': strategy.is_recommended
            })
        
        serializer = StrategyComparisonSerializer(comparison_data, many=True)
        return Response(serializer.data)


class MarketAnalysisView(APIView):
    """
    Provide market analysis for goal planning.
    """
    
    def get(self, request):
        """Get current market analysis with automatic refresh for stale data."""
        # Check if we should trigger a refresh first
        newest_calculation = ProfitCalculation.objects.order_by('-last_updated').first()
        refresh_triggered = False
        
        if newest_calculation:
            data_age_hours = (timezone.now() - newest_calculation.last_updated).total_seconds() / 3600
            
            # Auto-refresh if data is older than 1 hour
            if data_age_hours > 1.0:
                try:
                    logger.info(f"🔄 Auto-refreshing stale market data ({data_age_hours:.1f}h old)")
                    self._trigger_background_refresh()
                    refresh_triggered = True
                except Exception as e:
                    logger.warning(f"Auto-refresh failed: {e}")
        
        # Try multiple time windows: 1hr → 6hr → 24hr → 7 days → all time
        time_windows = [
            (timedelta(hours=1), "fresh"),
            (timedelta(hours=6), "recent"), 
            (timedelta(hours=24), "daily"),
            (timedelta(days=7), "weekly"),
            (None, "historical")  # All time
        ]
        
        calculations = None
        data_freshness = "stale"
        data_age_hours = None
        
        for time_delta, freshness_level in time_windows:
            if time_delta is None:
                # All time query
                calculations = ProfitCalculation.objects.filter(current_profit__gt=0)
            else:
                cutoff_time = timezone.now() - time_delta
                calculations = ProfitCalculation.objects.filter(
                    created_at__gte=cutoff_time,
                    current_profit__gt=0
                )
            
            if calculations.exists():
                data_freshness = freshness_level
                # Get age of newest data
                newest = calculations.order_by('-last_updated').first()
                if newest:
                    data_age_hours = (timezone.now() - newest.last_updated).total_seconds() / 3600
                break
        
        # If still no data, return development mock data
        if not calculations or not calculations.exists():
            return Response({
                "total_profitable_items": 156,
                "average_profit_margin": 8.75,
                "highest_profit_item": "Rune platebody",
                "highest_profit_amount": 2847,
                "market_volatility_score": 0.45,
                "recommended_risk_level": "moderate",
                "data_freshness": "mock",
                "data_age_hours": 0,
                "message": "Using mock data - no database records found"
            })
        
        # Calculate market metrics
        total_profitable = calculations.count()
        avg_profit_margin = calculations.aggregate(
            avg_margin=Avg('current_profit_margin')
        )['avg_margin'] or 0
        
        highest_profit = calculations.order_by('-current_profit').first()
        
        # Enhanced volatility score based on profit distribution
        try:
            profit_values = list(calculations.values_list('current_profit', flat=True))
            profit_values = [p for p in profit_values if p is not None and p > 0]  # Filter out None/zero values
            
            if len(profit_values) > 1:
                mean_profit = statistics.mean(profit_values)
                try:
                    stdev_profit = statistics.stdev(profit_values)
                    volatility_score = min(stdev_profit / mean_profit, 1.0) if mean_profit > 0 else 0.5
                except (statistics.StatisticsError, ZeroDivisionError):
                    volatility_score = 0.5
            else:
                volatility_score = 0.5
        except Exception:
            # Fallback in case of any unexpected errors
            volatility_score = 0.5
        
        # Recommend risk level based on market conditions and data freshness
        base_risk_threshold = 0.3 if data_freshness in ['fresh', 'recent'] else 0.4
        
        if volatility_score < base_risk_threshold:
            recommended_risk = 'conservative'
        elif volatility_score < base_risk_threshold + 0.3:
            recommended_risk = 'moderate'
        else:
            recommended_risk = 'aggressive'
        
        analysis_data = {
            'total_profitable_items': total_profitable,
            'average_profit_margin': round(avg_profit_margin, 2),
            'highest_profit_item': highest_profit.item.name if highest_profit else 'Unknown',
            'highest_profit_amount': highest_profit.current_profit if highest_profit else 0,
            'market_volatility_score': round(volatility_score, 2),
            'recommended_risk_level': recommended_risk,
            'data_freshness': data_freshness,
            'data_age_hours': round(data_age_hours, 1) if data_age_hours is not None else None
        }
        
        serializer = MarketAnalysisSerializer(analysis_data)
        return Response(serializer.data)
    
    def _trigger_background_refresh(self):
        """
        Trigger background data refresh without blocking the response.
        
        Uses the new synchronous refresh service if Celery is unavailable.
        """
        try:
            # Try Celery first (async)
            from apps.planning.tasks import sync_items_and_prices_task
            sync_items_and_prices_task.delay(mode='hot_items_refresh')
            logger.info("Background refresh queued via Celery")
        except Exception as celery_error:
            # Fallback to synchronous refresh for high-volume items only
            try:
                from apps.system.views import _perform_data_refresh
                from apps.system.models import SyncOperation
                
                sync_op = SyncOperation.objects.create(
                    operation_type='auto_refresh',
                    status='started'
                )
                
                # Only refresh hot items to avoid blocking too long
                result = _perform_data_refresh(
                    sync_op=sync_op,
                    force_refresh=False,
                    hot_items_only=True
                )
                
                logger.info(f"Synchronous hot items refresh completed: {result['items_updated']} items updated")
                
            except Exception as sync_error:
                logger.error(f"Both Celery and synchronous refresh failed: celery={celery_error}, sync={sync_error}")
                raise sync_error


class TimeEstimationView(APIView):
    """
    Provide time estimation analysis for strategies.
    """
    
    def get(self, request, strategy_id):
        """Get detailed time estimation for a strategy."""
        try:
            session_key = request.session.session_key
            strategy = Strategy.objects.select_related('goal_plan').prefetch_related(
                'items__item'
            ).get(
                strategy_id=strategy_id,
                goal_plan__user_id=hash(session_key) if session_key else 0,
                status='ready'
            )
        except Strategy.DoesNotExist:
            return Response(
                {"error": "Strategy not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prepare strategy items data
        strategy_items = []
        for item in strategy.items.all():
            strategy_items.append({
                'item_id': item.item_id,
                'item_name': item.item.name if hasattr(item, 'item') else 'Unknown',
                'units_to_buy': item.units_to_buy,
                'buy_price': item.buy_price,
                'total_cost': item.total_cost,
                'total_profit': item.total_profit,
                'risk_score': float(item.risk_score),
                'category': 'general'
            })
        
        # Get time estimation using our new service
        time_service = TimeEstimator()
        time_analysis = async_to_sync(time_service.estimate_completion_time)(strategy_items)
        
        # Get risk analysis using our new service
        risk_service = RiskAnalyzer()
        risk_analysis = async_to_sync(risk_service.analyze_strategy_risk)(strategy_items)
        
        return Response({
            'strategy_id': strategy.strategy_id,
            'strategy_type': strategy.strategy_type,
            'time_analysis': time_analysis,
            'risk_analysis': risk_analysis
        })


class PortfolioOptimizationView(APIView):
    """
    Provide portfolio optimization analysis.
    """
    
    def post(self, request):
        """Optimize portfolio allocation."""
        available_capital = request.data.get('available_capital', 0)
        required_profit = request.data.get('required_profit', 0)
        risk_tolerance = request.data.get('risk_tolerance', 'moderate')
        max_items = request.data.get('max_items', 5)
        
        if available_capital <= 0 or required_profit <= 0:
            return Response(
                {"error": "Available capital and required profit must be positive"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get profitable items
        recent_calculations = ProfitCalculation.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1),
            current_profit__gte=100
        ).select_related('item').order_by('-current_profit')[:50]
        
        if not recent_calculations:
            return Response(
                {"error": "No profitable items available"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prepare items data
        items_data = []
        for calc in recent_calculations:
            items_data.append({
                'item': calc.item,
                'buy_price': calc.current_buy_price,
                'profit_per_item': calc.current_profit,
                'price_volatility': 0.3,  # Default volatility
                'ge_limit': calc.item.limit or 8,
                'daily_volume': 1000  # Default volume
            })
        
        # Optimize portfolio
        optimizer = PortfolioOptimizer()
        allocations = optimizer.optimize_portfolio(
            items_data,
            available_capital,
            required_profit,
            risk_tolerance
        )
        
        # Calculate metrics
        metrics = optimizer.calculate_portfolio_metrics(allocations)
        
        # Serialize response
        allocation_data = []
        for alloc in allocations:
            allocation_data.append({
                'item_name': alloc.item.name,
                'item_id': alloc.item.id,
                'allocation_percentage': alloc.allocation_percentage,
                'quantity': alloc.quantity,
                'expected_return': alloc.expected_return,
                'risk_score': alloc.risk_score,
                'time_to_acquire_hours': alloc.time_to_acquire_hours
            })
        
        return Response({
            'allocations': allocation_data,
            'portfolio_metrics': metrics,
            'optimization_successful': len(allocations) > 0
        })


class GoalPlanStatsView(APIView):
    """
    Provide statistics about goal plans.
    """
    
    def get(self, request):
        """Get overall statistics."""
        session_key = request.session.session_key
        if not session_key:
            return Response({
                'total_plans': 0,
                'active_plans': 0,
                'completed_goals': 0,
                'average_completion_rate': 0.0
            })
        
        plans = GoalPlan.objects.filter(session_key=session_key)
        
        stats = {
            'total_plans': plans.count(),
            'active_plans': plans.filter(is_active=True).count(),
            'completed_goals': plans.filter(
                progress_updates__completion_percentage__gte=100.0
            ).distinct().count(),
            'average_completion_rate': plans.aggregate(
                avg_completion=Avg('progress_updates__completion_percentage')
            )['avg_completion'] or 0.0
        }
        
        return Response(stats)
