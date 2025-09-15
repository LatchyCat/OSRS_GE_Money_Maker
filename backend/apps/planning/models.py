from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.items.models import Item
import uuid


class GoalPlan(models.Model):
    """
    Represents a user's wealth-building goal for high alch profit.
    """
    
    # Unique identifier for the plan
    plan_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Session tracking (anonymous users)
    session_key = models.CharField(max_length=40, db_index=True, help_text="Session key for anonymous users")
    
    # Goal parameters
    current_gp = models.BigIntegerField(
        validators=[MinValueValidator(0)],
        help_text="Current GP amount user has"
    )
    goal_gp = models.BigIntegerField(
        validators=[MinValueValidator(1)], 
        help_text="Target GP amount user wants to reach"
    )
    required_profit = models.BigIntegerField(
        help_text="Calculated profit needed (goal_gp - current_gp)"
    )
    
    # Plan settings
    preferred_timeframe_days = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1)],
        help_text="User's preferred timeframe in days"
    )
    risk_tolerance = models.CharField(
        max_length=20,
        choices=[
            ('conservative', 'Conservative'),
            ('moderate', 'Moderate'), 
            ('aggressive', 'Aggressive')
        ],
        default='moderate',
        help_text="User's risk tolerance level"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_achievable = models.BooleanField(default=True, help_text="Whether goal is mathematically achievable")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_calculated = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'goal_plans'
        indexes = [
            models.Index(fields=['session_key', '-created_at']),
            models.Index(fields=['plan_id']),
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-calculate required profit
        self.required_profit = max(0, self.goal_gp - self.current_gp)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Goal: {self.current_gp:,}gp → {self.goal_gp:,}gp ({self.required_profit:,}gp needed)"
    
    @property
    def profit_needed(self):
        """Calculate profit still needed."""
        return max(0, self.goal_gp - self.current_gp)
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage if goal was updated."""
        if self.goal_gp <= 0:
            return 0.0
        return min(100.0, (self.current_gp / self.goal_gp) * 100)


class Strategy(models.Model):
    """
    Different strategies to achieve the goal (Max Profit, Balanced, etc).
    """
    
    goal_plan = models.ForeignKey(GoalPlan, on_delete=models.CASCADE, related_name='strategies')
    
    # Strategy metadata
    name = models.CharField(max_length=100, help_text="Human-readable strategy name")
    strategy_type = models.CharField(
        max_length=50,
        choices=[
            ('max_profit', 'Maximum Profit'),
            ('time_optimal', 'Time Optimal'),
            ('balanced', 'Balanced Risk/Reward'),
            ('conservative', 'Conservative'),
            ('portfolio', 'Multi-Item Portfolio')
        ],
        help_text="Type of strategy"
    )
    
    # Strategy calculations
    estimated_days = models.FloatField(help_text="Estimated days to complete")
    estimated_profit = models.BigIntegerField(help_text="Expected total profit")
    required_initial_investment = models.BigIntegerField(help_text="GP needed to start this strategy")
    
    # Risk and feasibility
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'), 
            ('high', 'High Risk')
        ]
    )
    feasibility_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Feasibility score from 0 (impossible) to 1 (highly feasible)"
    )
    
    # Market constraints
    ge_limit_constrained = models.BooleanField(
        default=False,
        help_text="Whether strategy is limited by GE buy limits"
    )
    volume_risk = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Risk score based on market volume (0=safe, 1=risky)"
    )
    
    # AI analysis
    ai_confidence = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="AI confidence in this strategy"
    )
    ai_reasoning = models.TextField(blank=True, help_text="AI-generated reasoning")
    
    # Status
    is_recommended = models.BooleanField(default=False, help_text="Whether this is the recommended strategy")
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'strategies'
        indexes = [
            models.Index(fields=['goal_plan', '-feasibility_score']),
            models.Index(fields=['strategy_type']),
            models.Index(fields=['is_recommended', '-feasibility_score']),
        ]
        unique_together = ['goal_plan', 'strategy_type']
    
    def __str__(self):
        return f"{self.name} - {self.estimated_days:.1f} days, {self.risk_level} risk"
    
    @property
    def daily_profit_rate(self):
        """Calculate average daily profit rate."""
        if self.estimated_days <= 0:
            return 0
        return self.estimated_profit / self.estimated_days
    
    @property
    def roi_percentage(self):
        """Calculate return on investment percentage."""
        if self.required_initial_investment <= 0:
            return 0.0
        return (self.estimated_profit / self.required_initial_investment) * 100


class StrategyItem(models.Model):
    """
    Individual items within a strategy with their allocation and calculations.
    """
    
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='strategy_items')
    
    # Allocation and quantities
    allocation_percentage = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Percentage of strategy allocated to this item"
    )
    items_to_buy = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of items to purchase"
    )
    
    # Price calculations (snapshot at strategy creation)
    buy_price_when_calculated = models.IntegerField(help_text="GE buy price when strategy was created")
    profit_per_item = models.IntegerField(help_text="Profit per item when high alched")
    total_cost = models.BigIntegerField(help_text="Total cost to buy all items")
    expected_profit = models.BigIntegerField(help_text="Expected profit from this item allocation")
    
    # Time and volume calculations
    ge_limit = models.IntegerField(help_text="GE 4-hour buy limit for this item")
    estimated_buy_time_hours = models.FloatField(help_text="Time needed to buy all items (considering GE limits)")
    daily_volume = models.IntegerField(default=0, help_text="Daily trading volume when calculated")
    
    # Risk assessment for this item
    price_volatility = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Price volatility risk (0=stable, 1=very volatile)"
    )
    volume_risk = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)], 
        help_text="Volume/liquidity risk (0=safe, 1=risky)"
    )
    
    # Status
    is_primary = models.BooleanField(default=False, help_text="Whether this is the main item in the strategy")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'strategy_items'
        indexes = [
            models.Index(fields=['strategy', '-allocation_percentage']),
            models.Index(fields=['item', '-expected_profit']),
            models.Index(fields=['is_primary']),
        ]
        unique_together = ['strategy', 'item']
    
    def __str__(self):
        return f"{self.item.name} - {self.allocation_percentage}% ({self.items_to_buy:,} items)"
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage."""
        if self.buy_price_when_calculated <= 0:
            return 0.0
        return (self.profit_per_item / self.buy_price_when_calculated) * 100
    
    @property
    def four_hour_periods_needed(self):
        """Calculate how many 4-hour periods needed to buy all items."""
        if self.ge_limit <= 0:
            return float('inf')
        return self.items_to_buy / self.ge_limit


class ProgressUpdate(models.Model):
    """
    Track user's progress toward their goal over time.
    """
    
    goal_plan = models.ForeignKey(GoalPlan, on_delete=models.CASCADE, related_name='progress_updates')
    
    # Progress data
    current_gp_at_time = models.BigIntegerField(help_text="User's GP at this point in time")
    profit_made = models.BigIntegerField(default=0, help_text="Profit made since goal started")
    remaining_profit_needed = models.BigIntegerField(help_text="Profit still needed to reach goal")
    
    # Progress calculations
    completion_percentage = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Percentage of goal completed"
    )
    days_elapsed = models.FloatField(help_text="Days since goal was created")
    estimated_days_remaining = models.FloatField(null=True, blank=True, help_text="Estimated days to completion")
    
    # Current strategy being used
    active_strategy = models.ForeignKey(
        Strategy, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        help_text="Strategy user was following at this time"
    )
    
    # Market conditions
    market_notes = models.TextField(blank=True, help_text="Notes about market conditions")
    
    # Status
    is_on_track = models.BooleanField(default=True, help_text="Whether user is on track to meet goal")
    needs_strategy_update = models.BooleanField(default=False, help_text="Whether strategy needs updating")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'progress_updates'
        indexes = [
            models.Index(fields=['goal_plan', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.goal_plan} - {self.completion_percentage:.1f}% complete"
    
    @property
    def daily_profit_rate(self):
        """Calculate daily profit rate based on progress."""
        if self.days_elapsed <= 0:
            return 0
        return self.profit_made / self.days_elapsed


class StrategyRevision(models.Model):
    """
    Track changes to strategies over time due to market conditions.
    """
    
    original_strategy = models.ForeignKey(
        Strategy, 
        on_delete=models.CASCADE, 
        related_name='revisions'
    )
    
    # Revision details
    revision_reason = models.CharField(
        max_length=100,
        choices=[
            ('price_change', 'Price Change'),
            ('market_shift', 'Market Shift'),
            ('ge_limit_reached', 'GE Limit Reached'),
            ('user_request', 'User Request'),
            ('ai_recommendation', 'AI Recommendation'),
            ('performance_poor', 'Poor Performance'),
        ]
    )
    
    # Changes made
    changes_summary = models.TextField(help_text="Summary of changes made")
    impact_description = models.TextField(help_text="Expected impact of changes")
    
    # Metrics comparison
    old_estimated_days = models.FloatField()
    new_estimated_days = models.FloatField()
    old_feasibility_score = models.FloatField()
    new_feasibility_score = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'strategy_revisions'
        indexes = [
            models.Index(fields=['original_strategy', '-created_at']),
            models.Index(fields=['revision_reason', '-created_at']),
        ]
    
    def __str__(self):
        return f"Revision: {self.revision_reason} - {self.created_at.strftime('%Y-%m-%d')}"
