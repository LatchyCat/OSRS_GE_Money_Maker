from django.db import models
from apps.items.models import Item


class AIRecommendation(models.Model):
    """
    AI-generated recommendations for high alch items.
    """
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='ai_recommendations')
    
    # Recommendation data
    recommendation_type = models.CharField(max_length=50, choices=[
        ('high_profit', 'High Profit'),
        ('stable_market', 'Stable Market'),
        ('trending_up', 'Trending Up'),
        ('bulk_opportunity', 'Bulk Opportunity'),
        ('quick_flip', 'Quick Flip'),
    ])
    
    confidence_score = models.FloatField(help_text="AI confidence in recommendation (0-1)")
    reasoning = models.TextField(help_text="AI-generated explanation for recommendation")
    
    # Market analysis
    predicted_profit = models.IntegerField(help_text="AI-predicted profit per item")
    risk_level = models.CharField(max_length=20, choices=[
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
    ])
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="When this recommendation expires")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'ai_recommendations'
        indexes = [
            models.Index(fields=['item', '-confidence_score']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_active', 'recommendation_type']),
        ]
    
    def __str__(self):
        return f"AI Rec: {self.item.name} - {self.recommendation_type} ({self.confidence_score:.2f})"


class MarketAnalysis(models.Model):
    """
    AI-powered market analysis for trends and patterns.
    """
    
    analysis_type = models.CharField(max_length=50, choices=[
        ('daily_summary', 'Daily Market Summary'),
        ('item_trend', 'Item Trend Analysis'),
        ('profit_forecast', 'Profit Forecast'),
        ('market_shift', 'Market Shift Detection'),
    ])
    
    # Analysis content
    title = models.CharField(max_length=200)
    summary = models.TextField(help_text="Brief summary of analysis")
    detailed_analysis = models.TextField(help_text="Detailed AI analysis")
    
    # Related items (optional)
    items = models.ManyToManyField(Item, blank=True, related_name='market_analyses')
    
    # Key insights
    insights = models.JSONField(default=dict, help_text="Structured insights from analysis")
    confidence_score = models.FloatField(help_text="Confidence in analysis (0-1)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, default='ai_system')
    
    class Meta:
        db_table = 'market_analyses'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['analysis_type']),
            models.Index(fields=['-confidence_score']),
        ]
        verbose_name_plural = 'Market analyses'
    
    def __str__(self):
        return f"{self.analysis_type}: {self.title}"


class AIPromptLog(models.Model):
    """
    Logs AI prompts and responses for debugging and optimization.
    """
    
    # Request details
    prompt_type = models.CharField(max_length=50, help_text="Type of AI operation")
    prompt_text = models.TextField(help_text="Full prompt sent to AI")
    
    # Response details
    response_text = models.TextField(help_text="AI response")
    tokens_used = models.IntegerField(default=0)
    response_time_ms = models.IntegerField(help_text="Response time in milliseconds")
    
    # Context
    user_query = models.TextField(blank=True, help_text="Original user query if applicable")
    related_items = models.ManyToManyField(Item, blank=True)
    
    # Status
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    # API details
    api_provider = models.CharField(max_length=50, default='openrouter')
    model_name = models.CharField(max_length=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ai_prompt_logs'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['prompt_type']),
            models.Index(fields=['success']),
            models.Index(fields=['api_provider', 'model_name']),
        ]
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.prompt_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class UserPreference(models.Model):
    """
    User preferences for personalized recommendations.
    Note: For now using session-based preferences, can be extended to user accounts later.
    """
    
    session_key = models.CharField(max_length=40, unique=True, help_text="Session key for anonymous users")
    
    # Preference data
    preferred_profit_range = models.JSONField(default=dict, help_text="Min/max profit preferences")
    preferred_categories = models.ManyToManyField('items.ItemCategory', blank=True)
    risk_tolerance = models.CharField(max_length=20, choices=[
        ('conservative', 'Conservative'),
        ('moderate', 'Moderate'),
        ('aggressive', 'Aggressive'),
    ], default='moderate')
    
    # Behavioral data
    search_history = models.JSONField(default=list, help_text="Recent search queries")
    clicked_items = models.ManyToManyField(Item, blank=True, related_name='clicked_by')
    
    # Settings
    members_only = models.BooleanField(default=True, help_text="Show members items")
    show_explanations = models.BooleanField(default=True, help_text="Show AI explanations")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_preferences'
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['-updated_at']),
        ]
    
    def __str__(self):
        return f"Preferences for session {self.session_key[:8]}..."
