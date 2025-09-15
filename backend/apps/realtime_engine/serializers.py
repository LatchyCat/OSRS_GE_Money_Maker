"""
Django REST Framework serializers for the Real-Time Market Engine.

Handles serialization of seasonal patterns, forecasts, events, and recommendations.
"""

from rest_framework import serializers
from django.utils import timezone
from .models import (
    MarketMomentum, VolumeAnalysis, RiskMetrics, MarketEvent, StreamingDataStatus,
    SeasonalPattern, SeasonalForecast, SeasonalEvent, SeasonalRecommendation,
    SentimentAnalysis, ItemSentiment, PricePrediction,
    PortfolioOptimization, PortfolioAllocation, PortfolioRebalance,
    TechnicalAnalysis, TechnicalIndicator, TechnicalSignal
)
from apps.items.models import Item


class ItemBasicSerializer(serializers.ModelSerializer):
    """Basic item serializer for nested relationships."""
    
    class Meta:
        model = Item
        fields = ['item_id', 'name', 'current_price', 'profit_margin']


class SeasonalPatternSerializer(serializers.ModelSerializer):
    """Serializer for seasonal pattern analysis data."""
    
    item = ItemBasicSerializer(read_only=True)
    has_strong_patterns = serializers.SerializerMethodField()
    dominant_pattern_type = serializers.SerializerMethodField()
    has_significant_weekend_effect = serializers.SerializerMethodField()
    signal_quality = serializers.SerializerMethodField()
    is_high_conviction = serializers.SerializerMethodField()
    
    class Meta:
        model = SeasonalPattern
        fields = [
            'id', 'item', 'analysis_timestamp', 'lookback_days', 'data_points_analyzed',
            'analysis_types', 'weekly_pattern_strength', 'monthly_pattern_strength',
            'yearly_pattern_strength', 'event_pattern_strength', 'overall_pattern_strength',
            'weekend_effect_pct', 'best_day_of_week', 'worst_day_of_week', 'day_of_week_effects',
            'best_month', 'worst_month', 'monthly_effects', 'quarterly_effects',
            'detected_events', 'event_impact_analysis', 'short_term_forecast', 'medium_term_forecast',
            'forecast_confidence', 'recommendations', 'confidence_score', 'analysis_duration_seconds',
            'has_strong_patterns', 'dominant_pattern_type', 'has_significant_weekend_effect',
            'signal_quality', 'is_high_conviction'
        ]
    
    def get_has_strong_patterns(self, obj):
        return obj.overall_pattern_strength >= 0.6
    
    def get_dominant_pattern_type(self, obj):
        strengths = {
            'weekly': obj.weekly_pattern_strength,
            'monthly': obj.monthly_pattern_strength,
            'yearly': obj.yearly_pattern_strength,
            'event': obj.event_pattern_strength
        }
        return max(strengths, key=strengths.get)
    
    def get_has_significant_weekend_effect(self, obj):
        return abs(obj.weekend_effect_pct) >= 2.0
    
    def get_signal_quality(self, obj):
        if obj.overall_pattern_strength >= 0.8:
            return 'excellent'
        elif obj.overall_pattern_strength >= 0.6:
            return 'good'
        elif obj.overall_pattern_strength >= 0.4:
            return 'fair'
        else:
            return 'poor'
    
    def get_is_high_conviction(self, obj):
        return obj.overall_pattern_strength >= 0.7 and obj.confidence_score >= 0.8


class SeasonalForecastSerializer(serializers.ModelSerializer):
    """Serializer for seasonal forecasts with validation data."""
    
    seasonal_pattern = serializers.PrimaryKeyRelatedField(read_only=True)
    item_name = serializers.CharField(source='seasonal_pattern.item.name', read_only=True)
    is_validated = serializers.SerializerMethodField()
    days_until_target = serializers.SerializerMethodField()
    forecast_accuracy = serializers.SerializerMethodField()
    
    class Meta:
        model = SeasonalForecast
        fields = [
            'id', 'seasonal_pattern', 'item_name', 'forecast_timestamp', 'horizon',
            'target_date', 'forecasted_price', 'confidence_level', 'lower_bound', 'upper_bound',
            'base_price', 'seasonal_factor', 'trend_adjustment', 'primary_pattern_type',
            'pattern_strength', 'forecast_method', 'actual_price', 'forecast_error',
            'is_within_confidence_interval', 'validation_date', 'absolute_error',
            'percentage_error', 'is_validated', 'days_until_target', 'forecast_accuracy'
        ]
    
    def get_is_validated(self, obj):
        return obj.actual_price is not None
    
    def get_days_until_target(self, obj):
        if obj.target_date:
            delta = obj.target_date - timezone.now().date()
            return delta.days
        return None
    
    def get_forecast_accuracy(self, obj):
        if obj.percentage_error is not None:
            return 100 - abs(obj.percentage_error)
        return None


class SeasonalEventSerializer(serializers.ModelSerializer):
    """Serializer for seasonal events with impact analysis."""
    
    is_upcoming = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()
    has_significant_impact = serializers.SerializerMethodField()
    days_until_start = serializers.SerializerMethodField()
    
    class Meta:
        model = SeasonalEvent
        fields = [
            'id', 'event_name', 'event_type', 'description', 'start_date', 'end_date',
            'duration_days', 'is_recurring', 'recurrence_pattern', 'average_price_impact_pct',
            'average_volume_impact_pct', 'impact_confidence', 'affected_categories',
            'historical_occurrences', 'verification_status', 'detection_method',
            'detection_timestamp', 'last_updated', 'is_active', 'is_upcoming', 'is_current',
            'has_significant_impact', 'days_until_start'
        ]
    
    def get_is_upcoming(self, obj):
        today = timezone.now().date()
        return obj.start_date and obj.start_date > today
    
    def get_is_current(self, obj):
        today = timezone.now().date()
        return (obj.start_date and obj.end_date and 
                obj.start_date <= today <= obj.end_date)
    
    def get_has_significant_impact(self, obj):
        return (abs(obj.average_price_impact_pct) >= 5.0 or 
                abs(obj.average_volume_impact_pct) >= 20.0)
    
    def get_days_until_start(self, obj):
        if obj.start_date:
            delta = obj.start_date - timezone.now().date()
            return delta.days if delta.days >= 0 else None
        return None


class SeasonalRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for seasonal trading recommendations."""
    
    seasonal_pattern = serializers.PrimaryKeyRelatedField(read_only=True)
    item_name = serializers.CharField(source='seasonal_pattern.item.name', read_only=True)
    is_current = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    is_high_confidence = serializers.SerializerMethodField()
    current_performance_pct = serializers.SerializerMethodField()
    max_performance_pct = serializers.SerializerMethodField()
    min_performance_pct = serializers.SerializerMethodField()
    
    class Meta:
        model = SeasonalRecommendation
        fields = [
            'id', 'seasonal_pattern', 'item_name', 'recommendation_timestamp',
            'recommendation_type', 'target_date', 'valid_from', 'valid_until',
            'primary_pattern', 'confidence_score', 'expected_impact_pct',
            'suggested_position_size_pct', 'stop_loss_pct', 'take_profit_pct',
            'max_hold_days', 'recommendation_text', 'supporting_factors',
            'is_active', 'is_executed', 'execution_timestamp', 'execution_price',
            'final_performance_pct', 'is_current', 'days_remaining', 'is_high_confidence',
            'current_performance_pct', 'max_performance_pct', 'min_performance_pct'
        ]
    
    def get_is_current(self, obj):
        today = timezone.now().date()
        return obj.valid_from <= today <= obj.valid_until
    
    def get_days_remaining(self, obj):
        today = timezone.now().date()
        delta = obj.valid_until - today
        return max(0, delta.days)
    
    def get_is_high_confidence(self, obj):
        return obj.confidence_score >= 0.8
    
    def get_current_performance_pct(self, obj):
        # This would be calculated based on current market price vs execution price
        return 0.0  # Placeholder
    
    def get_max_performance_pct(self, obj):
        # This would be calculated based on max price reached
        return 0.0  # Placeholder
    
    def get_min_performance_pct(self, obj):
        # This would be calculated based on min price reached
        return 0.0  # Placeholder


class MarketMomentumSerializer(serializers.ModelSerializer):
    """Serializer for market momentum data."""
    
    item = ItemBasicSerializer(read_only=True)
    
    class Meta:
        model = MarketMomentum
        fields = [
            'id', 'item', 'momentum_score', 'trend_direction', 'price_velocity',
            'price_acceleration', 'volatility', 'support_level', 'resistance_level',
            'breakout_probability', 'last_updated'
        ]


class TechnicalAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for technical analysis data."""
    
    item = ItemBasicSerializer(read_only=True)
    signal_quality = serializers.SerializerMethodField()
    is_high_conviction = serializers.SerializerMethodField()
    
    class Meta:
        model = TechnicalAnalysis
        fields = [
            'id', 'item', 'analysis_timestamp', 'timeframes_analyzed', 'lookback_days',
            'data_points_used', 'overall_recommendation', 'strength_score',
            'consensus_signal', 'timeframe_agreement', 'dominant_timeframes',
            'conflicting_signals', 'confidence_score', 'analysis_duration_seconds',
            'signal_quality', 'is_high_conviction'
        ]
    
    def get_signal_quality(self, obj):
        if obj.strength_score >= 80:
            return 'excellent'
        elif obj.strength_score >= 60:
            return 'good'
        elif obj.strength_score >= 40:
            return 'fair'
        else:
            return 'poor'
    
    def get_is_high_conviction(self, obj):
        return obj.strength_score >= 70 and obj.timeframe_agreement >= 0.6


class SentimentAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for market sentiment analysis."""
    
    sentiment_strength = serializers.SerializerMethodField()
    
    class Meta:
        model = SentimentAnalysis
        fields = [
            'id', 'source', 'analysis_timestamp', 'overall_sentiment', 'sentiment_score',
            'confidence', 'analyzed_articles', 'key_themes', 'sentiment_breakdown',
            'market_impact_predictions', 'category_sentiment', 'top_mentioned_items',
            'analysis_duration_seconds', 'data_quality_score', 'sentiment_strength'
        ]
    
    def get_sentiment_strength(self, obj):
        if abs(obj.sentiment_score) >= 0.7:
            return 'strong'
        elif abs(obj.sentiment_score) >= 0.4:
            return 'moderate'
        else:
            return 'weak'


class PricePredictionSerializer(serializers.ModelSerializer):
    """Serializer for price predictions."""
    
    item = ItemBasicSerializer(read_only=True)
    is_high_confidence = serializers.SerializerMethodField()
    predicted_change_24h_pct = serializers.SerializerMethodField()
    
    class Meta:
        model = PricePrediction
        fields = [
            'id', 'item', 'prediction_timestamp', 'current_price', 'predicted_price_1h',
            'predicted_price_4h', 'predicted_price_24h', 'confidence_1h', 'confidence_4h',
            'confidence_24h', 'trend_direction', 'prediction_factors', 'model_version',
            'prediction_method', 'actual_price_1h', 'actual_price_4h', 'actual_price_24h',
            'error_1h', 'error_4h', 'error_24h', 'is_high_confidence', 'predicted_change_24h_pct'
        ]
    
    def get_is_high_confidence(self, obj):
        avg_confidence = (obj.confidence_1h + obj.confidence_4h + obj.confidence_24h) / 3
        return avg_confidence >= 0.7
    
    def get_predicted_change_24h_pct(self, obj):
        if obj.current_price and obj.predicted_price_24h and obj.current_price > 0:
            return ((obj.predicted_price_24h - obj.current_price) / obj.current_price) * 100
        return 0


# Summary serializers for dashboard/overview endpoints
class SeasonalPatternSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for seasonal pattern summaries."""
    
    item_name = serializers.CharField(source='item.name', read_only=True)
    dominant_pattern = serializers.SerializerMethodField()
    
    class Meta:
        model = SeasonalPattern
        fields = [
            'id', 'item_name', 'overall_pattern_strength', 'forecast_confidence',
            'analysis_timestamp', 'dominant_pattern'
        ]
    
    def get_dominant_pattern(self, obj):
        strengths = {
            'weekly': obj.weekly_pattern_strength,
            'monthly': obj.monthly_pattern_strength,
            'yearly': obj.yearly_pattern_strength,
            'event': obj.event_pattern_strength
        }
        return max(strengths, key=strengths.get)


class MarketOverviewSerializer(serializers.Serializer):
    """Serializer for market overview dashboard data."""
    
    total_items_analyzed = serializers.IntegerField()
    strong_patterns_count = serializers.IntegerField()
    active_recommendations = serializers.IntegerField()
    upcoming_events = serializers.IntegerField()
    forecast_accuracy = serializers.FloatField()
    market_sentiment = serializers.CharField()
    last_updated = serializers.DateTimeField()