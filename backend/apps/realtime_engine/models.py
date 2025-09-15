"""
Real-Time Market Engine Models

Handles streaming data, market momentum, volume analysis, and real-time metrics.
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta, date
from typing import List, Dict, Optional
from apps.items.models import Item
import json
import numpy as np


class MarketMomentum(models.Model):
    """
    Tracks real-time price velocity, acceleration, and momentum for market analysis.
    """
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name='momentum')
    
    # Price Movement Metrics
    price_velocity = models.FloatField(default=0.0, help_text="GP per minute price change")
    price_acceleration = models.FloatField(default=0.0, help_text="Change in velocity (GP/min²)")
    momentum_score = models.FloatField(default=0.0, help_text="Overall momentum score (0-100)")
    
    # Volume Metrics
    volume_velocity = models.FloatField(default=0.0, help_text="Volume change rate")
    volume_shock_score = models.FloatField(default=0.0, help_text="Volume spike intensity (0-100)")
    
    # Trend Classification
    trend_direction = models.CharField(
        max_length=20,
        choices=[
            ('strong_bull', 'Strong Bullish'),
            ('bull', 'Bullish'),
            ('neutral', 'Neutral'),
            ('bear', 'Bearish'),
            ('strong_bear', 'Strong Bearish'),
        ],
        default='neutral'
    )
    
    trend_strength = models.FloatField(default=0.0, help_text="Trend strength (0-100)")
    
    # Timing Data
    last_updated = models.DateTimeField(auto_now=True)
    measurement_window_minutes = models.IntegerField(default=5, help_text="Analysis window in minutes")
    
    class Meta:
        db_table = 'market_momentum'
        indexes = [
            models.Index(fields=['-momentum_score']),
            models.Index(fields=['-volume_shock_score']),
            models.Index(fields=['-price_velocity']),
            models.Index(fields=['trend_direction', '-trend_strength']),
            models.Index(fields=['-last_updated']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - Momentum: {self.momentum_score:.1f}"

    @property
    def is_gaining_momentum(self):
        """Check if item is gaining significant momentum."""
        return self.momentum_score > 60 and self.price_velocity > 0

    @property
    def is_volume_shock(self):
        """Check if item is experiencing volume shock."""
        return self.volume_shock_score > 70

    @property
    def momentum_category(self):
        """Categorize momentum level."""
        if self.momentum_score >= 80:
            return 'explosive'
        elif self.momentum_score >= 60:
            return 'strong'
        elif self.momentum_score >= 40:
            return 'moderate'
        elif self.momentum_score >= 20:
            return 'weak'
        else:
            return 'stagnant'


class VolumeAnalysis(models.Model):
    """
    Detailed volume analysis for trading opportunities.
    """
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name='volume_analysis')
    
    # Current Volume Metrics
    current_hourly_volume = models.IntegerField(default=0)
    current_daily_volume = models.IntegerField(default=0)
    average_hourly_volume = models.FloatField(default=0.0, help_text="7-day average")
    average_daily_volume = models.FloatField(default=0.0, help_text="7-day average")
    
    # Volume Ratios and Comparisons
    volume_ratio_hourly = models.FloatField(default=1.0, help_text="Current/Average hourly volume")
    volume_ratio_daily = models.FloatField(default=1.0, help_text="Current/Average daily volume")
    
    # Volume Categories
    liquidity_level = models.CharField(
        max_length=20,
        choices=[
            ('extreme', 'Extremely High (10k+ daily)'),
            ('very_high', 'Very High (5k-10k daily)'),
            ('high', 'High (1k-5k daily)'),
            ('medium', 'Medium (500-1k daily)'),
            ('low', 'Low (100-500 daily)'),
            ('very_low', 'Very Low (50-100 daily)'),
            ('minimal', 'Minimal (<50 daily)'),
        ],
        default='minimal'
    )
    
    # Risk and Trading Metrics
    flip_completion_probability = models.FloatField(default=0.0, help_text="Probability of completing flip in 4 hours")
    recommended_position_size = models.IntegerField(default=0, help_text="Recommended quantity to flip")
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    confidence_score = models.FloatField(default=0.0, help_text="Data confidence (0-100)")
    
    class Meta:
        db_table = 'volume_analysis'
        indexes = [
            models.Index(fields=['-volume_ratio_daily']),
            models.Index(fields=['-current_daily_volume']),
            models.Index(fields=['liquidity_level']),
            models.Index(fields=['-flip_completion_probability']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - Volume: {self.current_daily_volume} ({self.liquidity_level})"

    @property
    def is_high_volume_spike(self):
        """Check for significant volume spike."""
        return self.volume_ratio_daily >= 2.0  # 200% of normal volume

    @property
    def is_tradeable(self):
        """Check if item has sufficient volume for trading."""
        return self.liquidity_level in ['high', 'very_high', 'extreme']


class RiskMetrics(models.Model):
    """
    Comprehensive risk analysis for trading decisions.
    """
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name='risk_metrics')
    
    # Risk Scores (0-100, higher = more risky)
    overall_risk_score = models.FloatField(default=50.0)
    volatility_risk = models.FloatField(default=0.0, help_text="Price volatility risk")
    liquidity_risk = models.FloatField(default=0.0, help_text="Low volume risk")
    market_depth_risk = models.FloatField(default=0.0, help_text="Thin orderbook risk")
    
    # Price Metrics
    price_volatility_24h = models.FloatField(default=0.0, help_text="24h price standard deviation %")
    max_drawdown_7d = models.FloatField(default=0.0, help_text="Maximum 7-day price decline %")
    
    # Trading Safety Metrics
    recommended_max_investment_pct = models.FloatField(default=10.0, help_text="% of capital to invest")
    position_hold_time_estimate = models.IntegerField(default=240, help_text="Estimated hold time in minutes")
    
    # Risk Categories
    risk_category = models.CharField(
        max_length=20,
        choices=[
            ('very_low', 'Very Low Risk'),
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
            ('very_high', 'Very High Risk'),
            ('extreme', 'Extreme Risk'),
        ],
        default='medium'
    )
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    confidence_level = models.FloatField(default=0.8, help_text="Risk assessment confidence")
    
    class Meta:
        db_table = 'risk_metrics'
        indexes = [
            models.Index(fields=['risk_category']),
            models.Index(fields=['-overall_risk_score']),
            models.Index(fields=['-recommended_max_investment_pct']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - Risk: {self.risk_category} ({self.overall_risk_score:.1f})"

    @property
    def is_safe_for_beginners(self):
        """Check if item is safe for new traders."""
        return self.risk_category in ['very_low', 'low'] and self.overall_risk_score < 30

    @property
    def requires_experience(self):
        """Check if item requires trading experience."""
        return self.risk_category in ['high', 'very_high', 'extreme']


class MarketEvent(models.Model):
    """
    Real-time market events and anomalies detection.
    """
    EVENT_TYPES = [
        ('price_spike', 'Price Spike'),
        ('price_crash', 'Price Crash'),
        ('volume_surge', 'Volume Surge'),
        ('new_opportunity', 'New Trading Opportunity'),
        ('whale_activity', 'Large Trade Detected'),
        ('market_manipulation', 'Potential Manipulation'),
        ('news_impact', 'Game Update Impact'),
        ('seasonal_pattern', 'Seasonal Price Pattern'),
    ]
    
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    items = models.ManyToManyField(Item, related_name='market_events')
    
    # Event Details
    title = models.CharField(max_length=200)
    description = models.TextField()
    impact_score = models.FloatField(default=0.0, help_text="Event impact intensity (0-100)")
    
    # Event Data
    event_data = models.JSONField(default=dict, help_text="Additional event metadata")
    
    # Timing
    detected_at = models.DateTimeField(auto_now_add=True)
    estimated_duration_minutes = models.IntegerField(default=60, help_text="How long event might last")
    
    # Status
    is_active = models.BooleanField(default=True)
    confidence = models.FloatField(default=0.8, help_text="Detection confidence (0-1)")
    
    class Meta:
        db_table = 'market_events'
        indexes = [
            models.Index(fields=['-detected_at']),
            models.Index(fields=['event_type', '-impact_score']),
            models.Index(fields=['is_active', '-detected_at']),
        ]
        ordering = ['-detected_at']
    
    def __str__(self):
        return f"{self.event_type}: {self.title}"

    @property
    def is_high_impact(self):
        """Check if this is a high-impact market event."""
        return self.impact_score >= 70

    def get_affected_items_count(self):
        """Get number of affected items."""
        return self.items.count()


class StreamingDataStatus(models.Model):
    """
    Monitor the health and status of streaming data sources.
    """
    DATA_SOURCES = [
        ('weirdgloop', 'Weird Gloop API'),
        ('runescape_wiki', 'RuneScape Wiki API'),
        ('internal_calculations', 'Internal Calculations'),
    ]
    
    source = models.CharField(max_length=50, choices=DATA_SOURCES, unique=True)
    
    # Status Metrics
    is_active = models.BooleanField(default=True)
    last_successful_update = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    error_count_24h = models.IntegerField(default=0)
    
    # Performance Metrics
    average_response_time_ms = models.FloatField(default=0.0)
    requests_per_hour = models.IntegerField(default=0)
    success_rate_24h = models.FloatField(default=100.0, help_text="Success rate percentage")
    
    # Data Quality
    data_freshness_minutes = models.FloatField(default=0.0, help_text="Average data age in minutes")
    coverage_percentage = models.FloatField(default=100.0, help_text="% of items with recent data")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'streaming_data_status'
    
    def __str__(self):
        return f"{self.source} - {'Active' if self.is_active else 'Inactive'}"

    @property
    def is_healthy(self):
        """Check if data source is healthy."""
        if not self.is_active:
            return False
        if not self.last_successful_update:
            return False
        
        # Consider healthy if updated within last 10 minutes and success rate > 90%
        time_since_update = timezone.now() - self.last_successful_update
        return (
            time_since_update.total_seconds() < 600 and  # 10 minutes
            self.success_rate_24h > 90.0
        )


class GELimitEntry(models.Model):
    """
    Tracks individual GE buy limit usage for users.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ge_limits')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='limit_entries')
    
    # Limit tracking
    quantity_bought = models.IntegerField(default=0, help_text="Quantity bought in current 4-hour period")
    max_limit = models.IntegerField(help_text="Maximum buy limit for this item")
    
    # Timing
    last_purchase_time = models.DateTimeField(auto_now_add=True)
    limit_reset_time = models.DateTimeField(help_text="When the limit resets (4 hours from first purchase)")
    
    # Transaction details
    average_purchase_price = models.IntegerField(null=True, blank=True, help_text="Average price paid")
    total_investment = models.IntegerField(default=0, help_text="Total GP invested")
    
    # Status
    is_limit_reached = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ge_limit_entries'
        unique_together = ['user', 'item']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['limit_reset_time']),
            models.Index(fields=['is_limit_reached']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.item.name}: {self.quantity_bought}/{self.max_limit}"
    
    @property
    def remaining_limit(self) -> int:
        """Calculate remaining buy limit."""
        return max(0, self.max_limit - self.quantity_bought)
    
    @property
    def limit_utilization_pct(self) -> float:
        """Calculate limit utilization percentage."""
        return (self.quantity_bought / self.max_limit * 100) if self.max_limit > 0 else 0
    
    @property
    def time_until_reset(self) -> timedelta:
        """Calculate time until limit resets."""
        return max(timedelta(0), self.limit_reset_time - timezone.now())
    
    @property
    def minutes_until_reset(self) -> int:
        """Minutes until limit resets."""
        return max(0, int(self.time_until_reset.total_seconds() / 60))
    
    def is_limit_expired(self) -> bool:
        """Check if the 4-hour limit period has expired."""
        return timezone.now() >= self.limit_reset_time
    
    def reset_limit(self):
        """Reset the limit for a new 4-hour period."""
        self.quantity_bought = 0
        self.is_limit_reached = False
        self.limit_reset_time = timezone.now() + timedelta(hours=4)
        self.total_investment = 0
        self.average_purchase_price = None
        self.save()


class SentimentAnalysis(models.Model):
    """
    Store sentiment analysis results from news and community sources.
    """
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ]
    
    SOURCE_CHOICES = [
        ('official_news', 'Official OSRS News'),
        ('official_updates', 'Official Updates'),
        ('reddit', 'Reddit r/2007scape'),
        ('twitter', 'Twitter'),
        ('discord', 'Discord Communities'),
        ('combined', 'Combined Analysis'),
    ]
    
    # Basic Information
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    analysis_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Overall Sentiment
    overall_sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, default='neutral')
    sentiment_score = models.FloatField(default=0.0, help_text="Compound sentiment score (-1 to 1)")
    confidence = models.FloatField(default=0.0, help_text="Analysis confidence (0 to 1)")
    
    # Analysis Details
    analyzed_articles = models.IntegerField(default=0, help_text="Number of articles analyzed")
    key_themes = models.JSONField(default=list, help_text="Extracted key themes and topics")
    sentiment_breakdown = models.JSONField(default=dict, help_text="Positive/negative/neutral counts")
    
    # Market Predictions
    market_impact_predictions = models.JSONField(default=dict, help_text="Predicted market impacts")
    category_sentiment = models.JSONField(default=dict, help_text="Sentiment by item category")
    top_mentioned_items = models.JSONField(default=dict, help_text="Most mentioned items")
    
    # Metadata
    analysis_duration_seconds = models.FloatField(default=0.0)
    data_quality_score = models.FloatField(default=0.0, help_text="Quality of source data (0-100)")
    
    class Meta:
        db_table = 'sentiment_analysis'
        indexes = [
            models.Index(fields=['-analysis_timestamp']),
            models.Index(fields=['source', '-analysis_timestamp']),
            models.Index(fields=['overall_sentiment']),
            models.Index(fields=['-sentiment_score']),
        ]
        ordering = ['-analysis_timestamp']
    
    def __str__(self):
        return f"{self.source} - {self.overall_sentiment} ({self.sentiment_score:.2f}) at {self.analysis_timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def sentiment_strength(self):
        """Categorize sentiment strength."""
        abs_score = abs(self.sentiment_score)
        if abs_score >= 0.7:
            return 'strong'
        elif abs_score >= 0.3:
            return 'moderate'
        else:
            return 'weak'
    
    def get_predicted_items(self, impact_threshold: float = 0.5) -> List[str]:
        """Get items predicted to be impacted."""
        predicted_items = []
        
        for key, prediction in self.market_impact_predictions.items():
            if (key.startswith('item_') and 
                prediction.get('confidence', 0) >= impact_threshold):
                predicted_items.append(key.replace('item_', ''))
        
        return predicted_items


class ItemSentiment(models.Model):
    """
    Store item-specific sentiment analysis results.
    """
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='sentiment_history')
    analysis_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Sentiment Data
    sentiment_score = models.FloatField(default=0.0, help_text="Item-specific sentiment (-1 to 1)")
    sentiment_label = models.CharField(max_length=20, default='neutral')
    mention_count = models.IntegerField(default=0, help_text="Number of mentions found")
    confidence = models.FloatField(default=0.0, help_text="Analysis confidence (0 to 1)")
    
    # Context
    sample_contexts = models.JSONField(default=list, help_text="Sample sentences mentioning the item")
    
    # Predictions
    IMPACT_CHOICES = [
        ('no_impact', 'No Impact'),
        ('minimal_impact', 'Minimal Impact'),
        ('positive_impact', 'Positive Impact'),
        ('negative_impact', 'Negative Impact'),
        ('strong_positive_impact', 'Strong Positive Impact'),
        ('strong_negative_impact', 'Strong Negative Impact'),
        ('moderate_impact', 'Moderate Impact'),
    ]
    
    predicted_impact = models.CharField(max_length=30, choices=IMPACT_CHOICES, default='no_impact')
    
    # Sources
    sources = models.JSONField(default=list, help_text="Sources where item was mentioned")
    
    class Meta:
        db_table = 'item_sentiment'
        indexes = [
            models.Index(fields=['item', '-analysis_timestamp']),
            models.Index(fields=['-sentiment_score']),
            models.Index(fields=['predicted_impact']),
            models.Index(fields=['-mention_count']),
        ]
        ordering = ['-analysis_timestamp']
    
    def __str__(self):
        return f"{self.item.name} - {self.sentiment_label} ({self.sentiment_score:.2f}) - {self.mention_count} mentions"
    
    @property
    def is_significant(self):
        """Check if this sentiment analysis is significant."""
        return (abs(self.sentiment_score) > 0.3 and 
                self.mention_count >= 2 and 
                self.confidence > 0.5)
    
    def get_latest_sentiment_trend(self, days: int = 7):
        """Get sentiment trend for this item over past days."""
        from django.db.models import Avg
        cutoff_date = timezone.now() - timedelta(days=days)
        
        return ItemSentiment.objects.filter(
            item=self.item,
            analysis_timestamp__gte=cutoff_date
        ).aggregate(
            avg_sentiment=Avg('sentiment_score'),
            total_mentions=models.Sum('mention_count')
        )


class PricePrediction(models.Model):
    """
    Store AI/ML price predictions for items.
    """
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='price_predictions')
    prediction_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Current data
    current_price = models.FloatField(help_text="Price at time of prediction")
    
    # Predictions
    predicted_price_1h = models.FloatField(help_text="Predicted price in 1 hour")
    predicted_price_4h = models.FloatField(help_text="Predicted price in 4 hours")
    predicted_price_24h = models.FloatField(help_text="Predicted price in 24 hours")
    
    # Confidence scores (0-1)
    confidence_1h = models.FloatField(default=0.5, help_text="Prediction confidence (0-1)")
    confidence_4h = models.FloatField(default=0.5, help_text="Prediction confidence (0-1)")
    confidence_24h = models.FloatField(default=0.5, help_text="Prediction confidence (0-1)")
    
    # Trend analysis
    TREND_CHOICES = [
        ('bullish', 'Bullish'),
        ('bearish', 'Bearish'),
        ('neutral', 'Neutral'),
    ]
    trend_direction = models.CharField(max_length=20, choices=TREND_CHOICES, default='neutral')
    
    # Prediction factors (JSON)
    prediction_factors = models.JSONField(default=dict, help_text="Factors used in prediction")
    
    # Model metadata
    model_version = models.CharField(max_length=50, default='statistical_v1')
    prediction_method = models.CharField(max_length=100, default='statistical_ensemble')
    
    # Validation (to be filled in later)
    actual_price_1h = models.FloatField(null=True, blank=True)
    actual_price_4h = models.FloatField(null=True, blank=True)
    actual_price_24h = models.FloatField(null=True, blank=True)
    
    # Accuracy metrics (calculated after validation)
    error_1h = models.FloatField(null=True, blank=True, help_text="Prediction error percentage")
    error_4h = models.FloatField(null=True, blank=True, help_text="Prediction error percentage") 
    error_24h = models.FloatField(null=True, blank=True, help_text="Prediction error percentage")
    
    class Meta:
        db_table = 'price_predictions'
        indexes = [
            models.Index(fields=['item', '-prediction_timestamp']),
            models.Index(fields=['-confidence_24h']),
            models.Index(fields=['trend_direction']),
            models.Index(fields=['-prediction_timestamp']),
        ]
        ordering = ['-prediction_timestamp']
    
    def __str__(self):
        return f"{self.item.name} - {self.trend_direction} @ {self.prediction_timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def is_high_confidence(self):
        """Check if this is a high confidence prediction."""
        return (self.confidence_1h > 0.7 and 
                self.confidence_4h > 0.7 and 
                self.confidence_24h > 0.7)
    
    @property
    def predicted_change_24h_pct(self):
        """Calculate predicted 24h change percentage."""
        if self.current_price > 0:
            return ((self.predicted_price_24h / self.current_price) - 1) * 100
        return 0
    
    def calculate_accuracy(self, actual_price: float, timeframe: str) -> float:
        """Calculate prediction accuracy for a given timeframe."""
        predicted_price = getattr(self, f'predicted_price_{timeframe}')
        if predicted_price > 0:
            error = abs((actual_price - predicted_price) / predicted_price) * 100
            return max(0, 100 - error)  # Convert error to accuracy
        return 0
    
    def update_actual_prices(self, actual_1h: float = None, actual_4h: float = None, 
                           actual_24h: float = None):
        """Update actual prices and calculate errors."""
        if actual_1h is not None:
            self.actual_price_1h = actual_1h
            self.error_1h = abs((actual_1h - self.predicted_price_1h) / self.predicted_price_1h) * 100
        
        if actual_4h is not None:
            self.actual_price_4h = actual_4h
            self.error_4h = abs((actual_4h - self.predicted_price_4h) / self.predicted_price_4h) * 100
        
        if actual_24h is not None:
            self.actual_price_24h = actual_24h
            self.error_24h = abs((actual_24h - self.predicted_price_24h) / self.predicted_price_24h) * 100
        
        self.save()
    
    @classmethod
    def get_model_accuracy_stats(cls, days: int = 7) -> Dict[str, float]:
        """Get accuracy statistics for the prediction model."""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        predictions = cls.objects.filter(
            prediction_timestamp__gte=cutoff_date,
            error_24h__isnull=False
        )
        
        if not predictions.exists():
            return {}
        
        errors_1h = [p.error_1h for p in predictions if p.error_1h is not None]
        errors_4h = [p.error_4h for p in predictions if p.error_4h is not None]
        errors_24h = [p.error_24h for p in predictions if p.error_24h is not None]
        
        return {
            'avg_error_1h': np.mean(errors_1h) if errors_1h else None,
            'avg_error_4h': np.mean(errors_4h) if errors_4h else None,
            'avg_error_24h': np.mean(errors_24h) if errors_24h else None,
            'total_predictions': predictions.count(),
            'accuracy_1h': 100 - np.mean(errors_1h) if errors_1h else None,
            'accuracy_4h': 100 - np.mean(errors_4h) if errors_4h else None,
            'accuracy_24h': 100 - np.mean(errors_24h) if errors_24h else None
        }


class PortfolioOptimization(models.Model):
    """
    Store portfolio optimization results and configurations.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolio_optimizations')
    optimization_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Capital allocation
    total_capital = models.IntegerField(help_text="Total capital available for optimization (GP)")
    target_return = models.FloatField(default=0.05, help_text="Target daily return rate (0.05 = 5%)")
    risk_tolerance = models.FloatField(default=0.5, help_text="Risk tolerance (0-1, higher = more risk)")
    
    # Optimization settings
    OPTIMIZATION_METHODS = [
        ('risk_parity', 'Risk Parity'),
        ('modern_portfolio_theory', 'Modern Portfolio Theory (MPT)'),
        ('kelly_criterion', 'Kelly Criterion'),
        ('equal_weight', 'Equal Weight'),
        ('maximum_sharpe', 'Maximum Sharpe Ratio'),
        ('minimum_variance', 'Minimum Variance'),
    ]
    optimization_method = models.CharField(max_length=50, choices=OPTIMIZATION_METHODS, default='risk_parity')
    
    # Portfolio metrics
    expected_daily_return = models.FloatField(default=0.0, help_text="Expected daily return rate")
    expected_daily_risk = models.FloatField(default=0.0, help_text="Expected daily volatility")
    sharpe_ratio = models.FloatField(default=0.0, help_text="Risk-adjusted return ratio")
    sortino_ratio = models.FloatField(default=0.0, help_text="Downside risk-adjusted return")
    diversification_ratio = models.FloatField(default=1.0, help_text="Portfolio diversification score")
    
    # Constraints used
    max_position_size = models.FloatField(default=0.2, help_text="Maximum % of capital per item")
    min_position_size = models.FloatField(default=0.01, help_text="Minimum % of capital per item")
    max_items = models.IntegerField(default=10, help_text="Maximum number of items in portfolio")
    liquidity_requirement = models.CharField(max_length=20, default='medium', help_text="Required liquidity level")
    
    # Results summary
    recommended_items_count = models.IntegerField(default=0)
    total_allocated_capital = models.IntegerField(default=0, help_text="Total capital actually allocated")
    cash_reserve = models.IntegerField(default=0, help_text="Unallocated cash reserve")
    
    # Performance tracking
    is_active = models.BooleanField(default=True)
    performance_score = models.FloatField(null=True, blank=True, help_text="Actual performance vs expected")
    
    class Meta:
        db_table = 'portfolio_optimizations'
        indexes = [
            models.Index(fields=['user', '-optimization_timestamp']),
            models.Index(fields=['-sharpe_ratio']),
            models.Index(fields=['optimization_method']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['-optimization_timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.optimization_method} - {self.expected_daily_return:.2%} return"
    
    @property
    def capital_utilization(self):
        """Calculate portfolio capital utilization percentage."""
        if self.total_capital > 0:
            return (self.total_allocated_capital / self.total_capital) * 100
        return 0
    
    @property
    def risk_adjusted_score(self):
        """Calculate risk-adjusted portfolio score."""
        return self.sharpe_ratio * self.diversification_ratio
    
    def get_allocation_summary(self):
        """Get summary of portfolio allocations."""
        allocations = self.allocations.all()
        return {
            'total_items': allocations.count(),
            'total_capital': sum(alloc.allocated_capital for alloc in allocations),
            'avg_allocation': sum(alloc.weight for alloc in allocations) / allocations.count() if allocations else 0,
            'top_allocation': max(alloc.weight for alloc in allocations) if allocations else 0,
        }


class PortfolioAllocation(models.Model):
    """
    Individual item allocations within a portfolio optimization.
    """
    portfolio = models.ForeignKey(PortfolioOptimization, on_delete=models.CASCADE, related_name='allocations')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='portfolio_allocations')
    
    # Allocation details
    weight = models.FloatField(help_text="Portfolio weight (0-1)")
    allocated_capital = models.IntegerField(help_text="Capital allocated to this item (GP)")
    recommended_quantity = models.IntegerField(help_text="Recommended quantity to buy")
    target_price = models.IntegerField(help_text="Target purchase price per item")
    
    # Risk metrics
    individual_risk = models.FloatField(help_text="Individual item risk score")
    contribution_to_risk = models.FloatField(help_text="Contribution to total portfolio risk")
    beta = models.FloatField(default=1.0, help_text="Beta relative to overall OSRS market")
    
    # Expected returns
    expected_return = models.FloatField(help_text="Expected daily return for this item")
    confidence_score = models.FloatField(help_text="Confidence in allocation (0-1)")
    
    # Constraints considered
    ge_limit_utilized = models.IntegerField(default=0, help_text="GE limit utilization")
    liquidity_score = models.FloatField(help_text="Item liquidity score")
    
    # Reasons for allocation
    allocation_reasons = models.JSONField(default=list, help_text="Factors that influenced this allocation")
    
    # Execution tracking
    STATUS_CHOICES = [
        ('recommended', 'Recommended'),
        ('partially_filled', 'Partially Filled'),
        ('filled', 'Fully Filled'),
        ('failed', 'Failed to Fill'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='recommended')
    quantity_filled = models.IntegerField(default=0)
    average_fill_price = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'portfolio_allocations'
        unique_together = ['portfolio', 'item']
        indexes = [
            models.Index(fields=['portfolio', '-weight']),
            models.Index(fields=['-expected_return']),
            models.Index(fields=['status']),
            models.Index(fields=['-confidence_score']),
        ]
        ordering = ['-weight']
    
    def __str__(self):
        return f"{self.item.name}: {self.weight:.1%} ({self.allocated_capital:,} GP)"
    
    @property
    def fill_percentage(self):
        """Calculate fill percentage of the allocation."""
        if self.recommended_quantity > 0:
            return (self.quantity_filled / self.recommended_quantity) * 100
        return 0
    
    @property
    def unrealized_pnl(self):
        """Calculate unrealized P&L if partially or fully filled."""
        if self.quantity_filled > 0 and self.average_fill_price:
            current_price = getattr(self.item.latest_price, 'high_price', self.target_price)
            return (current_price - self.average_fill_price) * self.quantity_filled
        return 0
    
    @property
    def is_high_conviction(self):
        """Check if this is a high conviction allocation."""
        return self.confidence_score >= 0.8 and self.weight >= 0.1
    
    def update_fill_status(self, quantity_filled: int, fill_price: int):
        """Update the fill status of this allocation."""
        self.quantity_filled = min(quantity_filled, self.recommended_quantity)
        
        # Calculate weighted average fill price
        if self.average_fill_price and self.quantity_filled > quantity_filled:
            # Partial fill update
            total_cost = (self.average_fill_price * (self.quantity_filled - quantity_filled)) + (fill_price * quantity_filled)
            self.average_fill_price = total_cost // self.quantity_filled
        else:
            self.average_fill_price = fill_price
        
        # Update status
        if self.quantity_filled == 0:
            self.status = 'recommended'
        elif self.quantity_filled == self.recommended_quantity:
            self.status = 'filled'
        else:
            self.status = 'partially_filled'
        
        self.save()


class PortfolioRebalance(models.Model):
    """
    Track portfolio rebalancing actions and recommendations.
    """
    portfolio = models.ForeignKey(PortfolioOptimization, on_delete=models.CASCADE, related_name='rebalances')
    rebalance_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Rebalance trigger
    TRIGGER_REASONS = [
        ('scheduled', 'Scheduled Rebalance'),
        ('drift_threshold', 'Portfolio Drift Threshold'),
        ('market_condition', 'Market Condition Change'),
        ('new_opportunity', 'New Trading Opportunity'),
        ('risk_breach', 'Risk Limit Breach'),
        ('manual', 'Manual Rebalance'),
    ]
    trigger_reason = models.CharField(max_length=30, choices=TRIGGER_REASONS)
    
    # Pre-rebalance metrics
    pre_rebalance_return = models.FloatField(help_text="Portfolio return before rebalance")
    pre_rebalance_risk = models.FloatField(help_text="Portfolio risk before rebalance")
    pre_rebalance_sharpe = models.FloatField(help_text="Sharpe ratio before rebalance")
    
    # Post-rebalance metrics
    post_rebalance_return = models.FloatField(null=True, blank=True)
    post_rebalance_risk = models.FloatField(null=True, blank=True)
    post_rebalance_sharpe = models.FloatField(null=True, blank=True)
    
    # Rebalance actions
    total_trades_required = models.IntegerField(default=0)
    completed_trades = models.IntegerField(default=0)
    failed_trades = models.IntegerField(default=0)
    total_transaction_cost = models.IntegerField(default=0, help_text="Estimated transaction costs")
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending Execution'),
        ('in_progress', 'In Progress'), 
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partially Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Metadata
    rebalance_notes = models.TextField(blank=True)
    execution_duration_minutes = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'portfolio_rebalances'
        indexes = [
            models.Index(fields=['portfolio', '-rebalance_timestamp']),
            models.Index(fields=['trigger_reason']),
            models.Index(fields=['status']),
        ]
        ordering = ['-rebalance_timestamp']
    
    def __str__(self):
        return f"Rebalance {self.id} - {self.trigger_reason} - {self.status}"
    
    @property
    def completion_rate(self):
        """Calculate rebalance completion rate."""
        if self.total_trades_required > 0:
            return (self.completed_trades / self.total_trades_required) * 100
        return 0
    
    @property
    def performance_improvement(self):
        """Calculate performance improvement from rebalance."""
        if self.post_rebalance_sharpe and self.pre_rebalance_sharpe:
            return self.post_rebalance_sharpe - self.pre_rebalance_sharpe
        return None
    
    def mark_completed(self, actual_transaction_cost: int = None):
        """Mark rebalance as completed and update metrics."""
        self.status = 'completed'
        if actual_transaction_cost is not None:
            self.total_transaction_cost = actual_transaction_cost
        
        # Calculate execution duration
        if self.rebalance_timestamp:
            self.execution_duration_minutes = int((timezone.now() - self.rebalance_timestamp).total_seconds() / 60)
        
        self.save()


class PortfolioAction(models.Model):
    """
    Individual trading actions generated by portfolio optimization.
    """
    rebalance = models.ForeignKey(PortfolioRebalance, on_delete=models.CASCADE, related_name='actions')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='portfolio_actions')
    
    # Action details
    ACTION_TYPES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('hold', 'Hold'),
        ('reduce', 'Reduce Position'),
        ('increase', 'Increase Position'),
    ]
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    
    # Quantities and prices
    target_quantity = models.IntegerField(help_text="Target quantity for this action")
    current_quantity = models.IntegerField(default=0, help_text="Current quantity held")
    quantity_change = models.IntegerField(help_text="Quantity change required")
    target_price = models.IntegerField(help_text="Target price for execution")
    
    # Priority and timing
    priority = models.IntegerField(default=5, help_text="Execution priority (1=highest, 10=lowest)")
    estimated_execution_time = models.IntegerField(help_text="Estimated time to complete (minutes)")
    
    # Constraints
    respects_ge_limit = models.BooleanField(default=True)
    max_slippage_pct = models.FloatField(default=2.0, help_text="Maximum acceptable slippage %")
    
    # Execution tracking
    executed_quantity = models.IntegerField(default=0)
    average_execution_price = models.IntegerField(null=True, blank=True)
    execution_timestamp = models.DateTimeField(null=True, blank=True)
    
    # Status and results
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('queued', 'Queued for Execution'),
        ('executing', 'Executing'),
        ('completed', 'Completed'),
        ('partial', 'Partially Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    failure_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'portfolio_actions'
        indexes = [
            models.Index(fields=['rebalance', 'priority']),
            models.Index(fields=['status', '-priority']),
            models.Index(fields=['action_type']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['priority', '-created_at']
    
    def __str__(self):
        return f"{self.action_type.upper()} {self.target_quantity} {self.item.name} @ {self.target_price}"
    
    @property
    def execution_progress(self):
        """Calculate execution progress percentage."""
        if self.target_quantity > 0:
            return (self.executed_quantity / abs(self.quantity_change)) * 100
        return 0
    
    @property
    def estimated_value(self):
        """Calculate estimated value of this action."""
        return abs(self.quantity_change) * self.target_price
    
    @property
    def actual_slippage(self):
        """Calculate actual slippage if executed."""
        if self.average_execution_price and self.target_price:
            return ((self.average_execution_price / self.target_price) - 1) * 100
        return 0
    
    def execute_action(self, executed_qty: int, execution_price: int):
        """Record execution of this action."""
        self.executed_quantity += executed_qty
        self.execution_timestamp = timezone.now()
        
        # Calculate weighted average execution price
        if self.average_execution_price:
            total_cost = (self.average_execution_price * (self.executed_quantity - executed_qty)) + (execution_price * executed_qty)
            self.average_execution_price = total_cost // self.executed_quantity
        else:
            self.average_execution_price = execution_price
        
        # Update status
        if self.executed_quantity >= abs(self.quantity_change):
            self.status = 'completed'
        elif self.executed_quantity > 0:
            self.status = 'partial'
        
        self.save()


class TechnicalAnalysis(models.Model):
    """
    Store technical analysis results for items across multiple timeframes.
    """
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='technical_analyses')
    analysis_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Analysis parameters
    timeframes_analyzed = models.JSONField(default=list, help_text="List of timeframes analyzed (5m, 15m, 1h, 4h, 1d)")
    lookback_days = models.IntegerField(default=30, help_text="Days of historical data used")
    data_points_used = models.IntegerField(default=0, help_text="Total data points in analysis")
    
    # Overall results
    overall_recommendation = models.CharField(
        max_length=20,
        choices=[
            ('strong_buy', 'Strong Buy'),
            ('buy', 'Buy'),
            ('weak_buy', 'Weak Buy'),
            ('neutral', 'Neutral'),
            ('weak_sell', 'Weak Sell'),
            ('sell', 'Sell'),
            ('strong_sell', 'Strong Sell'),
        ],
        default='neutral'
    )
    
    strength_score = models.FloatField(default=0, help_text="Overall technical strength (0-100)")
    consensus_signal = models.CharField(max_length=10, default='neutral')
    timeframe_agreement = models.FloatField(default=0, help_text="Agreement between timeframes (0-1)")
    
    # Signal details
    dominant_timeframes = models.JSONField(default=list, help_text="Timeframes supporting consensus")
    conflicting_signals = models.BooleanField(default=False, help_text="Whether timeframes show conflicting signals")
    
    # Analysis metadata
    analysis_duration_seconds = models.FloatField(default=0.0)
    confidence_score = models.FloatField(default=0.0, help_text="Analysis confidence (0-1)")
    
    class Meta:
        db_table = 'technical_analyses'
        indexes = [
            models.Index(fields=['item', '-analysis_timestamp']),
            models.Index(fields=['-strength_score']),
            models.Index(fields=['overall_recommendation']),
            models.Index(fields=['-analysis_timestamp']),
        ]
        ordering = ['-analysis_timestamp']
    
    def __str__(self):
        return f"{self.item.name} - {self.overall_recommendation} ({self.strength_score:.1f})"
    
    @property
    def is_high_conviction(self):
        """Check if this is a high conviction signal."""
        return (self.strength_score >= 70 and 
                self.timeframe_agreement >= 0.6 and 
                self.overall_recommendation in ['strong_buy', 'strong_sell'])
    
    @property
    def signal_quality(self):
        """Categorize signal quality."""
        if self.strength_score >= 80 and self.timeframe_agreement >= 0.8:
            return 'excellent'
        elif self.strength_score >= 60 and self.timeframe_agreement >= 0.6:
            return 'good'
        elif self.strength_score >= 40 and self.timeframe_agreement >= 0.4:
            return 'fair'
        else:
            return 'poor'


class TechnicalIndicator(models.Model):
    """
    Store individual technical indicator results for specific timeframes.
    """
    technical_analysis = models.ForeignKey(TechnicalAnalysis, on_delete=models.CASCADE, related_name='indicators')
    
    # Timeframe details
    timeframe = models.CharField(max_length=10, help_text="5m, 15m, 1h, 4h, 1d")
    data_points = models.IntegerField(default=0)
    
    # Moving Averages
    sma_short = models.FloatField(null=True, blank=True, help_text="Short-term SMA value")
    sma_long = models.FloatField(null=True, blank=True, help_text="Long-term SMA value")
    ema_short = models.FloatField(null=True, blank=True, help_text="Short-term EMA value")
    ema_long = models.FloatField(null=True, blank=True, help_text="Long-term EMA value")
    
    # RSI
    rsi_value = models.FloatField(null=True, blank=True, help_text="RSI value (0-100)")
    rsi_signal = models.CharField(max_length=10, default='neutral', help_text="RSI signal")
    rsi_strength = models.FloatField(default=0, help_text="RSI signal strength")
    
    # MACD
    macd_line = models.FloatField(null=True, blank=True, help_text="MACD line value")
    macd_signal_line = models.FloatField(null=True, blank=True, help_text="MACD signal line")
    macd_histogram = models.FloatField(null=True, blank=True, help_text="MACD histogram")
    macd_signal = models.CharField(max_length=10, default='neutral', help_text="MACD signal")
    macd_strength = models.FloatField(default=0, help_text="MACD signal strength")
    
    # Bollinger Bands
    bb_upper = models.FloatField(null=True, blank=True, help_text="Bollinger upper band")
    bb_middle = models.FloatField(null=True, blank=True, help_text="Bollinger middle band")
    bb_lower = models.FloatField(null=True, blank=True, help_text="Bollinger lower band")
    bb_position = models.FloatField(null=True, blank=True, help_text="Price position relative to bands")
    bb_signal = models.CharField(max_length=10, default='neutral', help_text="Bollinger Bands signal")
    bb_strength = models.FloatField(default=0, help_text="BB signal strength")
    
    # Volume indicators
    obv_value = models.FloatField(null=True, blank=True, help_text="On-Balance Volume")
    volume_sma = models.FloatField(null=True, blank=True, help_text="Volume SMA")
    volume_signal = models.CharField(max_length=20, default='normal', help_text="Volume signal")
    volume_strength = models.FloatField(default=0, help_text="Volume signal strength")
    
    # OSRS-specific indicators
    osrs_momentum = models.FloatField(default=0, help_text="OSRS momentum score")
    flip_probability = models.FloatField(default=0.5, help_text="Probability of successful flip")
    flip_confidence = models.FloatField(default=0.5, help_text="Confidence in flip probability")
    
    # Trend analysis
    trend_direction = models.CharField(
        max_length=20,
        choices=[
            ('uptrend', 'Uptrend'),
            ('downtrend', 'Downtrend'),
            ('sideways', 'Sideways'),
        ],
        default='sideways'
    )
    trend_strength = models.FloatField(default=0, help_text="Trend strength (0-1)")
    trend_duration = models.IntegerField(default=0, help_text="Trend duration in periods")
    
    # Support/Resistance levels
    support_levels = models.JSONField(default=list, help_text="Identified support levels")
    resistance_levels = models.JSONField(default=list, help_text="Identified resistance levels")
    
    # Overall timeframe signal
    overall_signal = models.CharField(max_length=10, default='neutral')
    signal_strength = models.FloatField(default=0, help_text="Overall signal strength for this timeframe")
    
    class Meta:
        db_table = 'technical_indicators'
        unique_together = ['technical_analysis', 'timeframe']
        indexes = [
            models.Index(fields=['timeframe', 'overall_signal']),
            models.Index(fields=['-rsi_value']),
            models.Index(fields=['-signal_strength']),
            models.Index(fields=['trend_direction']),
        ]
        ordering = ['timeframe']
    
    def __str__(self):
        return f"{self.technical_analysis.item.name} - {self.timeframe} - {self.overall_signal}"
    
    @property
    def is_oversold(self):
        """Check if RSI indicates oversold condition."""
        return self.rsi_value is not None and self.rsi_value < 30
    
    @property
    def is_overbought(self):
        """Check if RSI indicates overbought condition."""
        return self.rsi_value is not None and self.rsi_value > 70
    
    @property
    def macd_bullish_crossover(self):
        """Check if MACD shows bullish crossover."""
        return (self.macd_line is not None and 
                self.macd_signal_line is not None and
                self.macd_line > self.macd_signal_line and
                self.macd_signal == 'buy')
    
    @property
    def bb_squeeze(self):
        """Check if Bollinger Bands are in squeeze pattern."""
        if all(x is not None for x in [self.bb_upper, self.bb_lower, self.bb_middle]):
            band_width = (self.bb_upper - self.bb_lower) / self.bb_middle
            return band_width < 0.1  # Less than 10% width indicates squeeze
        return False


class TechnicalSignal(models.Model):
    """
    Store actionable trading signals generated from technical analysis.
    """
    technical_analysis = models.ForeignKey(TechnicalAnalysis, on_delete=models.CASCADE, related_name='signals')
    signal_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Signal details
    SIGNAL_TYPES = [
        ('entry', 'Entry Signal'),
        ('exit', 'Exit Signal'),
        ('stop_loss', 'Stop Loss'),
        ('take_profit', 'Take Profit'),
        ('rebalance', 'Rebalance Signal'),
    ]
    signal_type = models.CharField(max_length=20, choices=SIGNAL_TYPES)
    
    SIGNAL_DIRECTIONS = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('hold', 'Hold'),
    ]
    direction = models.CharField(max_length=10, choices=SIGNAL_DIRECTIONS)
    
    # Signal strength and confidence
    strength = models.FloatField(help_text="Signal strength (0-1)")
    confidence = models.FloatField(help_text="Signal confidence (0-1)")
    
    # Price targets
    entry_price = models.IntegerField(null=True, blank=True, help_text="Suggested entry price")
    stop_loss_price = models.IntegerField(null=True, blank=True, help_text="Stop loss price")
    take_profit_price = models.IntegerField(null=True, blank=True, help_text="Take profit price")
    
    # Risk management
    position_size_pct = models.FloatField(default=0.05, help_text="Suggested position size (% of capital)")
    risk_reward_ratio = models.FloatField(null=True, blank=True, help_text="Risk/reward ratio")
    max_hold_time_hours = models.IntegerField(default=24, help_text="Maximum hold time in hours")
    
    # Signal basis
    primary_indicators = models.JSONField(default=list, help_text="Primary indicators supporting signal")
    supporting_timeframes = models.JSONField(default=list, help_text="Timeframes supporting signal")
    signal_reasoning = models.TextField(blank=True, help_text="Human-readable signal reasoning")
    
    # Execution tracking
    is_active = models.BooleanField(default=True)
    is_executed = models.BooleanField(default=False)
    execution_timestamp = models.DateTimeField(null=True, blank=True)
    execution_price = models.IntegerField(null=True, blank=True)
    
    # Performance tracking
    current_pnl = models.FloatField(default=0, help_text="Current P&L if executed")
    max_pnl = models.FloatField(default=0, help_text="Maximum P&L reached")
    min_pnl = models.FloatField(default=0, help_text="Minimum P&L reached")
    
    class Meta:
        db_table = 'technical_signals'
        indexes = [
            models.Index(fields=['-signal_timestamp']),
            models.Index(fields=['signal_type', 'direction']),
            models.Index(fields=['-strength', '-confidence']),
            models.Index(fields=['is_active', 'is_executed']),
        ]
        ordering = ['-signal_timestamp']
    
    def __str__(self):
        return f"{self.technical_analysis.item.name} - {self.signal_type} {self.direction} - {self.strength:.2f}"
    
    @property
    def is_high_quality(self):
        """Check if this is a high quality signal."""
        return self.strength >= 0.7 and self.confidence >= 0.7
    
    @property
    def expected_return(self):
        """Calculate expected return based on targets."""
        if self.entry_price and self.take_profit_price:
            if self.direction == 'buy':
                return (self.take_profit_price / self.entry_price - 1) * 100
            else:  # sell
                return (self.entry_price / self.take_profit_price - 1) * 100
        return 0
    
    @property
    def risk_amount(self):
        """Calculate risk amount based on stop loss."""
        if self.entry_price and self.stop_loss_price:
            if self.direction == 'buy':
                return abs(self.entry_price - self.stop_loss_price)
            else:  # sell
                return abs(self.stop_loss_price - self.entry_price)
        return 0
    
    def update_performance(self, current_price: int):
        """Update performance metrics based on current price."""
        if not self.is_executed or not self.execution_price:
            return
        
        # Calculate current P&L
        if self.direction == 'buy':
            self.current_pnl = ((current_price / self.execution_price) - 1) * 100
        else:  # sell
            self.current_pnl = ((self.execution_price / current_price) - 1) * 100
        
        # Update max/min P&L
        self.max_pnl = max(self.max_pnl, self.current_pnl)
        self.min_pnl = min(self.min_pnl, self.current_pnl)
        
        self.save()
    
    def should_exit(self, current_price: int) -> bool:
        """Check if signal should be exited based on current conditions."""
        if not self.is_executed:
            return False
        
        # Check stop loss
        if self.stop_loss_price:
            if self.direction == 'buy' and current_price <= self.stop_loss_price:
                return True
            elif self.direction == 'sell' and current_price >= self.stop_loss_price:
                return True
        
        # Check take profit
        if self.take_profit_price:
            if self.direction == 'buy' and current_price >= self.take_profit_price:
                return True
            elif self.direction == 'sell' and current_price <= self.take_profit_price:
                return True
        
        # Check max hold time
        if self.execution_timestamp:
            hours_held = (timezone.now() - self.execution_timestamp).total_seconds() / 3600
            if hours_held >= self.max_hold_time_hours:
                return True
        
        return False


class SeasonalPattern(models.Model):
    """
    Store seasonal pattern analysis results for items.
    """
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='seasonal_patterns')
    analysis_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Analysis parameters
    lookback_days = models.IntegerField(default=365, help_text="Days of historical data analyzed")
    data_points_analyzed = models.IntegerField(default=0, help_text="Number of data points used")
    analysis_types = models.JSONField(default=list, help_text="Types of analysis performed")
    
    # Pattern strength scores (0-1)
    weekly_pattern_strength = models.FloatField(default=0, help_text="Strength of weekly patterns")
    monthly_pattern_strength = models.FloatField(default=0, help_text="Strength of monthly patterns")
    yearly_pattern_strength = models.FloatField(default=0, help_text="Strength of yearly patterns")
    event_pattern_strength = models.FloatField(default=0, help_text="Strength of event-based patterns")
    overall_pattern_strength = models.FloatField(default=0, help_text="Overall seasonal pattern strength")
    
    # Weekly patterns
    weekend_effect_pct = models.FloatField(default=0, help_text="Weekend price premium/discount %")
    best_day_of_week = models.CharField(max_length=10, default='', help_text="Best day for prices")
    worst_day_of_week = models.CharField(max_length=10, default='', help_text="Worst day for prices")
    day_of_week_effects = models.JSONField(default=dict, help_text="Day-of-week price effects")
    
    # Monthly patterns
    best_month = models.CharField(max_length=15, default='', help_text="Historically best month")
    worst_month = models.CharField(max_length=15, default='', help_text="Historically worst month")
    monthly_effects = models.JSONField(default=dict, help_text="Month-by-month effects")
    quarterly_effects = models.JSONField(default=dict, help_text="Quarterly seasonal effects")
    
    # Event patterns
    detected_events = models.JSONField(default=list, help_text="Detected unusual activity periods")
    event_impact_analysis = models.JSONField(default=dict, help_text="Analysis of OSRS event impacts")
    
    # Forecasting results
    short_term_forecast = models.JSONField(default=dict, help_text="Next 7 days forecast")
    medium_term_forecast = models.JSONField(default=dict, help_text="Next 30 days forecast")
    forecast_confidence = models.FloatField(default=0.5, help_text="Forecast confidence (0-1)")
    
    # Recommendations
    recommendations = models.JSONField(default=list, help_text="Generated seasonal recommendations")
    
    # Analysis metadata
    analysis_duration_seconds = models.FloatField(default=0.0)
    confidence_score = models.FloatField(default=0.0, help_text="Overall analysis confidence (0-1)")
    
    class Meta:
        db_table = 'seasonal_patterns'
        indexes = [
            models.Index(fields=['item', '-analysis_timestamp']),
            models.Index(fields=['-overall_pattern_strength']),
            models.Index(fields=['-analysis_timestamp']),
            models.Index(fields=['best_month']),
            models.Index(fields=['weekend_effect_pct']),
        ]
        ordering = ['-analysis_timestamp']
    
    def __str__(self):
        return f"{self.item.name} - Seasonal Strength: {self.overall_pattern_strength:.2f}"
    
    @property
    def has_strong_patterns(self):
        """Check if item has strong seasonal patterns."""
        return self.overall_pattern_strength >= 0.6
    
    @property
    def dominant_pattern_type(self):
        """Identify the dominant pattern type."""
        patterns = {
            'weekly': self.weekly_pattern_strength,
            'monthly': self.monthly_pattern_strength,
            'yearly': self.yearly_pattern_strength,
            'events': self.event_pattern_strength
        }
        return max(patterns.items(), key=lambda x: x[1])[0] if any(patterns.values()) else 'none'
    
    @property
    def has_significant_weekend_effect(self):
        """Check for significant weekend price effects."""
        return abs(self.weekend_effect_pct) >= 2.0
    
    def get_current_seasonal_recommendation(self) -> str:
        """Get current seasonal recommendation based on time of analysis."""
        try:
            current_date = timezone.now()
            current_month = current_date.strftime('%B')
            current_day = current_date.strftime('%A')
            
            recommendations = []
            
            # Weekend effect recommendation
            if self.has_significant_weekend_effect:
                if current_date.weekday() >= 4:  # Friday or later
                    if self.weekend_effect_pct > 0:
                        recommendations.append("Weekend premium expected - consider selling")
                    else:
                        recommendations.append("Weekend discount expected - consider buying")
            
            # Monthly recommendation
            if current_month == self.best_month:
                recommendations.append(f"Currently in best month ({self.best_month}) - prices typically higher")
            elif current_month == self.worst_month:
                recommendations.append(f"Currently in worst month ({self.worst_month}) - prices typically lower")
            
            # Day of week recommendation
            if current_day == self.best_day_of_week:
                recommendations.append(f"Best day for prices ({self.best_day_of_week}) - consider selling")
            elif current_day == self.worst_day_of_week:
                recommendations.append(f"Worst day for prices ({self.worst_day_of_week}) - consider buying")
            
            return "; ".join(recommendations) if recommendations else "No specific seasonal recommendation for current time"
            
        except Exception:
            return "Unable to generate current recommendation"


class SeasonalForecast(models.Model):
    """
    Store individual seasonal forecasts with validation tracking.
    """
    seasonal_pattern = models.ForeignKey(SeasonalPattern, on_delete=models.CASCADE, related_name='forecasts')
    forecast_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Forecast details
    FORECAST_HORIZONS = [
        ('1d', '1 Day'),
        ('3d', '3 Days'),
        ('7d', '7 Days'),
        ('14d', '14 Days'),
        ('30d', '30 Days'),
        ('60d', '60 Days'),
        ('90d', '90 Days'),
    ]
    horizon = models.CharField(max_length=10, choices=FORECAST_HORIZONS)
    target_date = models.DateField(help_text="Date this forecast is for")
    
    # Forecasted values
    forecasted_price = models.FloatField(help_text="Forecasted price")
    confidence_level = models.FloatField(default=0.95, help_text="Confidence level (e.g., 0.95 for 95%)")
    lower_bound = models.FloatField(help_text="Lower confidence bound")
    upper_bound = models.FloatField(help_text="Upper confidence bound")
    
    # Forecast components
    base_price = models.FloatField(help_text="Base price used for forecast")
    seasonal_factor = models.FloatField(default=1.0, help_text="Seasonal adjustment factor")
    trend_adjustment = models.FloatField(default=0.0, help_text="Trend component adjustment")
    
    # Forecast basis
    primary_pattern_type = models.CharField(
        max_length=20,
        choices=[
            ('weekly', 'Weekly Pattern'),
            ('monthly', 'Monthly Pattern'),
            ('yearly', 'Yearly Pattern'),
            ('event', 'Event-Based'),
            ('combined', 'Combined Patterns'),
        ],
        default='combined'
    )
    
    pattern_strength = models.FloatField(default=0.5, help_text="Strength of pattern used (0-1)")
    forecast_method = models.CharField(max_length=50, default='seasonal_naive', help_text="Method used for forecasting")
    
    # Validation (filled when actual data becomes available)
    actual_price = models.FloatField(null=True, blank=True, help_text="Actual price on target date")
    forecast_error = models.FloatField(null=True, blank=True, help_text="Forecast error percentage")
    is_within_confidence_interval = models.BooleanField(null=True, blank=True)
    
    # Performance tracking
    absolute_error = models.FloatField(null=True, blank=True, help_text="Absolute error in price units")
    percentage_error = models.FloatField(null=True, blank=True, help_text="Percentage error")
    validation_date = models.DateTimeField(null=True, blank=True, help_text="When forecast was validated")
    
    class Meta:
        db_table = 'seasonal_forecasts'
        unique_together = ['seasonal_pattern', 'horizon', 'target_date']
        indexes = [
            models.Index(fields=['target_date', 'horizon']),
            models.Index(fields=['-forecast_timestamp']),
            models.Index(fields=['primary_pattern_type']),
            models.Index(fields=['-pattern_strength']),
            models.Index(fields=['actual_price']),  # For validation queries
        ]
        ordering = ['target_date']
    
    def __str__(self):
        return f"{self.seasonal_pattern.item.name} - {self.horizon} forecast for {self.target_date}"
    
    @property
    def is_validated(self):
        """Check if forecast has been validated with actual data."""
        return self.actual_price is not None
    
    @property
    def days_until_target(self):
        """Calculate days until target date."""
        if self.target_date:
            today = timezone.now().date()
            return (self.target_date - today).days
        return None
    
    @property
    def forecast_accuracy(self):
        """Calculate forecast accuracy (100 - absolute percentage error)."""
        if self.percentage_error is not None:
            return max(0, 100 - abs(self.percentage_error))
        return None
    
    def validate_forecast(self, actual_price: float):
        """Validate the forecast against actual price."""
        try:
            self.actual_price = actual_price
            self.validation_date = timezone.now()
            
            # Calculate errors
            self.absolute_error = abs(actual_price - self.forecasted_price)
            self.percentage_error = ((actual_price - self.forecasted_price) / self.forecasted_price) * 100
            
            # Check if within confidence interval
            self.is_within_confidence_interval = self.lower_bound <= actual_price <= self.upper_bound
            
            self.save()
            
        except Exception as e:
            logger.exception(f"Failed to validate forecast {self.id}")
    
    @classmethod
    def get_accuracy_stats(cls, days_back: int = 30) -> Dict[str, float]:
        """Get accuracy statistics for validated forecasts."""
        try:
            cutoff_date = timezone.now() - timedelta(days=days_back)
            
            validated_forecasts = cls.objects.filter(
                validation_date__gte=cutoff_date,
                actual_price__isnull=False
            )
            
            if not validated_forecasts.exists():
                return {}
            
            # Calculate statistics
            errors = [abs(f.percentage_error) for f in validated_forecasts if f.percentage_error is not None]
            accuracies = [f.forecast_accuracy for f in validated_forecasts if f.forecast_accuracy is not None]
            ci_hits = [f.is_within_confidence_interval for f in validated_forecasts if f.is_within_confidence_interval is not None]
            
            stats = {
                'total_forecasts': validated_forecasts.count(),
                'mean_absolute_error': np.mean(errors) if errors else None,
                'median_absolute_error': np.median(errors) if errors else None,
                'mean_accuracy': np.mean(accuracies) if accuracies else None,
                'confidence_interval_hit_rate': np.mean(ci_hits) if ci_hits else None,
            }
            
            # Accuracy by horizon
            for horizon_code, horizon_name in cls.FORECAST_HORIZONS:
                horizon_forecasts = validated_forecasts.filter(horizon=horizon_code)
                if horizon_forecasts.exists():
                    horizon_errors = [
                        abs(f.percentage_error) for f in horizon_forecasts 
                        if f.percentage_error is not None
                    ]
                    stats[f'{horizon_code}_mean_error'] = np.mean(horizon_errors) if horizon_errors else None
            
            return stats
            
        except Exception as e:
            logger.exception("Failed to get accuracy stats")
            return {}


class SeasonalEvent(models.Model):
    """
    Store information about detected and predicted seasonal events.
    """
    # Event identification
    event_name = models.CharField(max_length=100, help_text="Name or identifier for the event")
    event_type = models.CharField(
        max_length=30,
        choices=[
            ('osrs_official', 'Official OSRS Event'),
            ('community', 'Community Event'),
            ('detected_anomaly', 'Detected Market Anomaly'),
            ('holiday', 'Holiday Effect'),
            ('update', 'Game Update'),
            ('seasonal', 'Seasonal Pattern'),
        ]
    )
    
    # Event timing
    start_date = models.DateField(null=True, blank=True, help_text="Event start date")
    end_date = models.DateField(null=True, blank=True, help_text="Event end date")
    duration_days = models.IntegerField(default=1, help_text="Event duration in days")
    
    # Recurrence information
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(
        max_length=20,
        choices=[
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
            ('irregular', 'Irregular'),
        ],
        blank=True
    )
    
    # Impact analysis
    affected_categories = models.JSONField(default=list, help_text="Item categories affected by event")
    average_price_impact_pct = models.FloatField(default=0, help_text="Average price impact percentage")
    average_volume_impact_pct = models.FloatField(default=0, help_text="Average volume impact percentage")
    impact_confidence = models.FloatField(default=0.5, help_text="Confidence in impact estimates")
    
    # Event details
    description = models.TextField(blank=True, help_text="Event description")
    historical_occurrences = models.JSONField(default=list, help_text="Historical dates when event occurred")
    
    # Prediction and detection metadata
    detection_method = models.CharField(max_length=50, default='manual', help_text="How event was detected/defined")
    detection_timestamp = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Whether to use this event for predictions")
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('unverified', 'Unverified'),
            ('verified', 'Verified'),
            ('false_positive', 'False Positive'),
        ],
        default='unverified'
    )
    
    class Meta:
        db_table = 'seasonal_events'
        indexes = [
            models.Index(fields=['event_type', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['-average_price_impact_pct']),
            models.Index(fields=['is_recurring', 'recurrence_pattern']),
            models.Index(fields=['-detection_timestamp']),
        ]
        ordering = ['-detection_timestamp']
    
    def __str__(self):
        return f"{self.event_name} ({self.event_type}) - {self.average_price_impact_pct:+.1f}% impact"
    
    @property
    def is_upcoming(self):
        """Check if event is upcoming (within next 60 days)."""
        if not self.start_date:
            return False
        
        today = timezone.now().date()
        days_until = (self.start_date - today).days
        return 0 <= days_until <= 60
    
    @property
    def is_current(self):
        """Check if event is currently active."""
        if not self.start_date or not self.end_date:
            return False
        
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    
    @property
    def has_significant_impact(self):
        """Check if event has significant market impact."""
        return abs(self.average_price_impact_pct) >= 5.0 or abs(self.average_volume_impact_pct) >= 20.0
    
    def predict_next_occurrence(self) -> Optional[date]:
        """Predict the next occurrence of this recurring event."""
        try:
            if not self.is_recurring or not self.start_date:
                return None
            
            today = timezone.now().date()
            last_occurrence = self.start_date
            
            # Find most recent historical occurrence
            if self.historical_occurrences:
                dates = [
                    datetime.strptime(date_str, '%Y-%m-%d').date() 
                    for date_str in self.historical_occurrences 
                    if isinstance(date_str, str)
                ]
                if dates:
                    last_occurrence = max(dates)
            
            # Calculate next occurrence based on pattern
            if self.recurrence_pattern == 'weekly':
                next_occurrence = last_occurrence + timedelta(days=7)
            elif self.recurrence_pattern == 'monthly':
                # Approximate monthly recurrence
                next_occurrence = last_occurrence + timedelta(days=30)
            elif self.recurrence_pattern == 'quarterly':
                next_occurrence = last_occurrence + timedelta(days=90)
            elif self.recurrence_pattern == 'yearly':
                next_occurrence = date(last_occurrence.year + 1, last_occurrence.month, last_occurrence.day)
            else:
                return None
            
            # If calculated date is in the past, move to next cycle
            while next_occurrence <= today:
                if self.recurrence_pattern == 'weekly':
                    next_occurrence += timedelta(days=7)
                elif self.recurrence_pattern == 'monthly':
                    next_occurrence += timedelta(days=30)
                elif self.recurrence_pattern == 'quarterly':
                    next_occurrence += timedelta(days=90)
                elif self.recurrence_pattern == 'yearly':
                    next_occurrence = date(next_occurrence.year + 1, next_occurrence.month, next_occurrence.day)
                else:
                    break
            
            return next_occurrence if next_occurrence > today else None
            
        except Exception as e:
            logger.exception(f"Failed to predict next occurrence for event {self.id}")
            return None
    
    def add_historical_occurrence(self, occurrence_date: date, impact_data: Dict = None):
        """Add a historical occurrence of this event."""
        try:
            date_str = occurrence_date.strftime('%Y-%m-%d')
            
            if date_str not in self.historical_occurrences:
                self.historical_occurrences.append(date_str)
                
                # Update impact estimates if new data provided
                if impact_data:
                    price_impact = impact_data.get('price_impact_pct', 0)
                    volume_impact = impact_data.get('volume_impact_pct', 0)
                    
                    # Simple running average update
                    occurrences = len(self.historical_occurrences)
                    self.average_price_impact_pct = (
                        (self.average_price_impact_pct * (occurrences - 1) + price_impact) / occurrences
                    )
                    self.average_volume_impact_pct = (
                        (self.average_volume_impact_pct * (occurrences - 1) + volume_impact) / occurrences
                    )
                
                self.save()
                
        except Exception as e:
            logger.exception(f"Failed to add historical occurrence for event {self.id}")


class SeasonalRecommendation(models.Model):
    """
    Store actionable seasonal recommendations with tracking.
    """
    seasonal_pattern = models.ForeignKey(SeasonalPattern, on_delete=models.CASCADE, related_name='detailed_recommendations')
    recommendation_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Recommendation details
    RECOMMENDATION_TYPES = [
        ('buy', 'Buy Recommendation'),
        ('sell', 'Sell Recommendation'),
        ('hold', 'Hold Recommendation'),
        ('avoid', 'Avoid Trading'),
        ('monitor', 'Monitor for Opportunity'),
    ]
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    
    # Timing
    target_date = models.DateField(null=True, blank=True, help_text="Specific date for action")
    valid_from = models.DateField(help_text="Recommendation valid from")
    valid_until = models.DateField(help_text="Recommendation valid until")
    
    # Recommendation basis
    primary_pattern = models.CharField(max_length=20, help_text="Primary seasonal pattern driving recommendation")
    confidence_score = models.FloatField(help_text="Recommendation confidence (0-1)")
    expected_impact_pct = models.FloatField(help_text="Expected price impact percentage")
    
    # Risk management
    suggested_position_size_pct = models.FloatField(default=5.0, help_text="Suggested position size (% of capital)")
    stop_loss_pct = models.FloatField(null=True, blank=True, help_text="Suggested stop loss %")
    take_profit_pct = models.FloatField(null=True, blank=True, help_text="Suggested take profit %")
    max_hold_days = models.IntegerField(default=30, help_text="Maximum recommended holding period")
    
    # Reasoning
    recommendation_text = models.TextField(help_text="Human-readable recommendation explanation")
    supporting_factors = models.JSONField(default=list, help_text="Factors supporting this recommendation")
    
    # Execution tracking
    is_active = models.BooleanField(default=True)
    is_executed = models.BooleanField(default=False)
    execution_timestamp = models.DateTimeField(null=True, blank=True)
    execution_price = models.FloatField(null=True, blank=True)
    
    # Performance tracking
    current_performance_pct = models.FloatField(default=0, help_text="Current performance if executed")
    max_performance_pct = models.FloatField(default=0, help_text="Maximum performance reached")
    min_performance_pct = models.FloatField(default=0, help_text="Minimum performance reached")
    final_performance_pct = models.FloatField(null=True, blank=True, help_text="Final performance when closed")
    
    class Meta:
        db_table = 'seasonal_recommendations'
        indexes = [
            models.Index(fields=['valid_from', 'valid_until']),
            models.Index(fields=['recommendation_type', 'is_active']),
            models.Index(fields=['-confidence_score']),
            models.Index(fields=['-recommendation_timestamp']),
            models.Index(fields=['is_executed']),
        ]
        ordering = ['-recommendation_timestamp']
    
    def __str__(self):
        return f"{self.seasonal_pattern.item.name} - {self.recommendation_type} (confidence: {self.confidence_score:.1%})"
    
    @property
    def is_current(self):
        """Check if recommendation is currently valid."""
        today = timezone.now().date()
        return self.valid_from <= today <= self.valid_until
    
    @property
    def days_remaining(self):
        """Days remaining for this recommendation."""
        today = timezone.now().date()
        if today > self.valid_until:
            return 0
        return (self.valid_until - today).days
    
    @property
    def is_high_confidence(self):
        """Check if this is a high confidence recommendation."""
        return self.confidence_score >= 0.7
    
    def update_performance(self, current_price: float):
        """Update performance metrics based on current price."""
        if not self.is_executed or not self.execution_price:
            return
        
        # Calculate current performance
        if self.recommendation_type == 'buy':
            self.current_performance_pct = ((current_price / self.execution_price) - 1) * 100
        elif self.recommendation_type == 'sell':
            self.current_performance_pct = ((self.execution_price / current_price) - 1) * 100
        
        # Update max/min performance
        self.max_performance_pct = max(self.max_performance_pct, self.current_performance_pct)
        self.min_performance_pct = min(self.min_performance_pct, self.current_performance_pct)
        
        self.save()
    
    def close_recommendation(self, final_price: float, reason: str = ""):
        """Close the recommendation and calculate final performance."""
        if self.is_executed and self.execution_price:
            if self.recommendation_type == 'buy':
                self.final_performance_pct = ((final_price / self.execution_price) - 1) * 100
            elif self.recommendation_type == 'sell':
                self.final_performance_pct = ((self.execution_price / final_price) - 1) * 100
        
        self.is_active = False
        self.save()