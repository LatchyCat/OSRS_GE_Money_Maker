"""
Serializers for goal planning API endpoints.
"""

from rest_framework import serializers
from django.core.validators import MinValueValidator

from .models import GoalPlan, Strategy, StrategyItem, ProgressUpdate, StrategyRevision


class StrategyItemSerializer(serializers.ModelSerializer):
    """Serializer for individual strategy items."""
    
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_id = serializers.IntegerField(source='item.id', read_only=True)
    high_alch_value = serializers.IntegerField(source='item.high_alch_value', read_only=True)
    
    # Calculated fields
    profit_margin = serializers.FloatField(read_only=True)
    four_hour_periods_needed = serializers.FloatField(read_only=True)
    
    class Meta:
        model = StrategyItem
        fields = [
            'id', 'item_id', 'item_name', 'high_alch_value',
            'allocation_percentage', 'items_to_buy', 
            'buy_price_when_calculated', 'profit_per_item',
            'total_cost', 'expected_profit', 'ge_limit',
            'estimated_buy_time_hours', 'daily_volume',
            'price_volatility', 'volume_risk', 'profit_margin',
            'four_hour_periods_needed', 'is_primary', 'is_active'
        ]


class StrategySerializer(serializers.ModelSerializer):
    """Serializer for strategies."""
    
    items = StrategyItemSerializer(many=True, read_only=True)
    
    # Calculated fields
    daily_profit_rate = serializers.FloatField(read_only=True)
    roi_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Strategy
        fields = [
            'id', 'name', 'strategy_type', 'estimated_days',
            'estimated_profit', 'required_initial_investment',
            'risk_level', 'feasibility_score', 'ge_limit_constrained',
            'volume_risk', 'ai_confidence', 'ai_reasoning',
            'is_recommended', 'is_active', 'created_at',
            'daily_profit_rate', 'roi_percentage', 'items'
        ]


class GoalPlanSerializer(serializers.ModelSerializer):
    """Serializer for goal plans."""
    
    strategies = StrategySerializer(many=True, read_only=True)
    
    # Calculated fields
    profit_needed = serializers.IntegerField(read_only=True)
    completion_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = GoalPlan
        fields = [
            'plan_id', 'session_key', 'current_gp', 'goal_gp',
            'required_profit', 'preferred_timeframe_days',
            'risk_tolerance', 'is_active', 'is_achievable',
            'created_at', 'updated_at', 'last_calculated',
            'profit_needed', 'completion_percentage', 'strategies'
        ]
        read_only_fields = ['plan_id', 'required_profit', 'last_calculated']


class CreateGoalPlanSerializer(serializers.Serializer):
    """Serializer for creating new goal plans."""
    
    current_gp = serializers.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Current GP amount you have"
    )
    goal_gp = serializers.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Target GP amount you want to reach"
    )
    preferred_timeframe_days = serializers.IntegerField(
        required=False,
        validators=[MinValueValidator(1)],
        help_text="Preferred timeframe in days (optional)"
    )
    risk_tolerance = serializers.ChoiceField(
        choices=[
            ('conservative', 'Conservative'),
            ('moderate', 'Moderate'),
            ('aggressive', 'Aggressive')
        ],
        default='moderate',
        help_text="Your risk tolerance level"
    )


class ProgressUpdateSerializer(serializers.ModelSerializer):
    """Serializer for progress updates."""
    
    goal_plan_id = serializers.UUIDField(source='goal_plan.plan_id', read_only=True)
    active_strategy_name = serializers.CharField(source='active_strategy.name', read_only=True)
    
    # Calculated fields
    daily_profit_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = ProgressUpdate
        fields = [
            'id', 'goal_plan_id', 'current_gp_at_time',
            'profit_made', 'remaining_profit_needed',
            'completion_percentage', 'days_elapsed',
            'estimated_days_remaining', 'active_strategy_name',
            'market_notes', 'is_on_track', 'needs_strategy_update',
            'daily_profit_rate', 'created_at'
        ]


class UpdateProgressSerializer(serializers.Serializer):
    """Serializer for updating progress."""
    
    current_gp = serializers.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="Your current GP amount"
    )
    market_notes = serializers.CharField(
        required=False,
        max_length=500,
        help_text="Optional notes about market conditions"
    )


class StrategyRevisionSerializer(serializers.ModelSerializer):
    """Serializer for strategy revisions."""
    
    strategy_name = serializers.CharField(source='original_strategy.name', read_only=True)
    
    class Meta:
        model = StrategyRevision
        fields = [
            'id', 'strategy_name', 'revision_reason',
            'changes_summary', 'impact_description',
            'old_estimated_days', 'new_estimated_days',
            'old_feasibility_score', 'new_feasibility_score',
            'created_at'
        ]


class StrategyComparisonSerializer(serializers.Serializer):
    """Serializer for comparing multiple strategies."""
    
    strategy_id = serializers.IntegerField()
    name = serializers.CharField()
    strategy_type = serializers.CharField()
    estimated_days = serializers.FloatField()
    estimated_profit = serializers.IntegerField()
    required_investment = serializers.IntegerField()
    roi_percentage = serializers.FloatField()
    risk_level = serializers.CharField()
    feasibility_score = serializers.FloatField()
    is_recommended = serializers.BooleanField()


class MarketAnalysisSerializer(serializers.Serializer):
    """Serializer for market analysis data."""
    
    total_profitable_items = serializers.IntegerField()
    average_profit_margin = serializers.FloatField()
    highest_profit_item = serializers.CharField()
    highest_profit_amount = serializers.IntegerField()
    market_volatility_score = serializers.FloatField()
    recommended_risk_level = serializers.CharField()
    data_freshness = serializers.CharField(required=False)
    data_age_hours = serializers.IntegerField(required=False)
    message = serializers.CharField(required=False)


class TimeEstimateSerializer(serializers.Serializer):
    """Serializer for time estimates."""
    
    item_name = serializers.CharField()
    quantity_needed = serializers.IntegerField()
    estimated_hours = serializers.FloatField()
    estimated_days = serializers.FloatField()
    confidence_level = serializers.FloatField()
    bottleneck_factor = serializers.FloatField()
    notes = serializers.CharField()


class StrategyTimeBreakdownSerializer(serializers.Serializer):
    """Serializer for strategy time breakdown."""
    
    total_estimated_hours = serializers.FloatField()
    total_estimated_days = serializers.FloatField()
    critical_path_item = serializers.CharField()
    parallel_acquisition_hours = serializers.FloatField()
    sequential_acquisition_hours = serializers.FloatField()
    ge_limit_constrained = serializers.BooleanField()
    item_estimates = TimeEstimateSerializer(many=True)


class RiskAnalysisSerializer(serializers.Serializer):
    """Serializer for risk analysis."""
    
    overall_risk = serializers.CharField()
    risk_score = serializers.FloatField()
    risk_factors = serializers.ListField(child=serializers.CharField())
    recommended_actions = serializers.ListField(child=serializers.CharField())