"""
Django REST Framework views for the Real-Time Market Engine.

Provides API endpoints for seasonal patterns, forecasts, events, and recommendations.
"""

from rest_framework import generics, status, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Avg, Max
from django.utils import timezone
from datetime import timedelta, date
# from django_filters.rest_framework import DjangoFilterBackend  # Will add when available

from .models import (
    MarketMomentum, VolumeAnalysis, RiskMetrics, MarketEvent, StreamingDataStatus,
    SeasonalPattern, SeasonalForecast, SeasonalEvent, SeasonalRecommendation,
    SentimentAnalysis, ItemSentiment, PricePrediction,
    PortfolioOptimization, PortfolioAllocation, PortfolioRebalance,
    TechnicalAnalysis, TechnicalIndicator, TechnicalSignal
)
from .serializers import (
    MarketMomentumSerializer, SentimentAnalysisSerializer, PricePredictionSerializer,
    TechnicalAnalysisSerializer, SeasonalPatternSerializer, SeasonalForecastSerializer,
    SeasonalEventSerializer, SeasonalRecommendationSerializer, SeasonalPatternSummarySerializer,
    MarketOverviewSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# =============================================================================
# SEASONAL PATTERN VIEWS
# =============================================================================

class SeasonalPatternListView(generics.ListAPIView):
    """
    List seasonal patterns with filtering and ordering.
    
    Query Parameters:
    - item_id: Filter by specific item
    - min_strength: Minimum pattern strength (0-1)
    - pattern_type: weekly, monthly, yearly, event
    - ordering: Field to order by (default: -overall_pattern_strength)
    """
    queryset = SeasonalPattern.objects.select_related('item').all()
    serializer_class = SeasonalPatternSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    # filterset_fields = ['item__item_id']  # Will add when django-filter is available
    ordering_fields = ['overall_pattern_strength', 'analysis_timestamp', 'forecast_confidence']
    ordering = ['-overall_pattern_strength']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by minimum strength
        min_strength = self.request.query_params.get('min_strength')
        if min_strength:
            try:
                min_strength = float(min_strength)
                queryset = queryset.filter(overall_pattern_strength__gte=min_strength)
            except (ValueError, TypeError):
                pass
        
        # Filter by pattern type (dominant pattern)
        pattern_type = self.request.query_params.get('pattern_type')
        if pattern_type in ['weekly', 'monthly', 'yearly', 'event']:
            if pattern_type == 'weekly':
                queryset = queryset.filter(weekly_pattern_strength__gte=0.5)
            elif pattern_type == 'monthly':
                queryset = queryset.filter(monthly_pattern_strength__gte=0.5)
            elif pattern_type == 'yearly':
                queryset = queryset.filter(yearly_pattern_strength__gte=0.5)
            elif pattern_type == 'event':
                queryset = queryset.filter(event_pattern_strength__gte=0.5)
        
        # Filter by recent analysis
        days_back = self.request.query_params.get('days_back', 7)
        try:
            days_back = int(days_back)
            cutoff_date = timezone.now() - timedelta(days=days_back)
            queryset = queryset.filter(analysis_timestamp__gte=cutoff_date)
        except (ValueError, TypeError):
            pass
        
        return queryset


class SeasonalPatternDetailView(generics.RetrieveAPIView):
    """Get detailed seasonal pattern analysis for a specific pattern."""
    queryset = SeasonalPattern.objects.select_related('item').all()
    serializer_class = SeasonalPatternSerializer


class SeasonalPatternByItemView(generics.RetrieveAPIView):
    """Get the latest seasonal pattern analysis for a specific item."""
    serializer_class = SeasonalPatternSerializer
    
    def get_object(self):
        item_id = self.kwargs['item_id']
        return SeasonalPattern.objects.select_related('item').filter(
            item__item_id=item_id
        ).order_by('-analysis_timestamp').first()


# =============================================================================
# SEASONAL FORECAST VIEWS
# =============================================================================

class SeasonalForecastListView(generics.ListAPIView):
    """
    List seasonal forecasts with filtering.
    
    Query Parameters:
    - item_id: Filter by specific item
    - horizon: Forecast horizon (1d, 7d, 30d, etc.)
    - validated: true/false - show only validated forecasts
    - upcoming: true/false - show only upcoming forecasts
    """
    queryset = SeasonalForecast.objects.select_related('seasonal_pattern__item').all()
    serializer_class = SeasonalForecastSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    # filterset_fields = ['horizon', 'primary_pattern_type']  # Will add when django-filter is available
    ordering_fields = ['target_date', 'confidence_level', 'forecast_timestamp']
    ordering = ['target_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by item
        item_id = self.request.query_params.get('item_id')
        if item_id:
            queryset = queryset.filter(seasonal_pattern__item__item_id=item_id)
        
        # Filter by validation status
        validated = self.request.query_params.get('validated')
        if validated == 'true':
            queryset = queryset.filter(actual_price__isnull=False)
        elif validated == 'false':
            queryset = queryset.filter(actual_price__isnull=True)
        
        # Filter by upcoming forecasts
        upcoming = self.request.query_params.get('upcoming')
        if upcoming == 'true':
            today = timezone.now().date()
            queryset = queryset.filter(target_date__gte=today)
        
        # Filter by minimum confidence
        min_confidence = self.request.query_params.get('min_confidence')
        if min_confidence:
            try:
                min_confidence = float(min_confidence)
                queryset = queryset.filter(confidence_level__gte=min_confidence)
            except (ValueError, TypeError):
                pass
        
        return queryset


class SeasonalForecastDetailView(generics.RetrieveAPIView):
    """Get detailed forecast information."""
    queryset = SeasonalForecast.objects.select_related('seasonal_pattern__item').all()
    serializer_class = SeasonalForecastSerializer


# =============================================================================
# SEASONAL EVENT VIEWS
# =============================================================================

class SeasonalEventListView(generics.ListAPIView):
    """
    List seasonal events with filtering.
    
    Query Parameters:
    - event_type: Type of event to filter by
    - upcoming: true/false - show only upcoming events
    - active: true/false - show only active events
    - verified: true/false - show only verified events
    """
    queryset = SeasonalEvent.objects.all()
    serializer_class = SeasonalEventSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    # filterset_fields = ['event_type', 'is_recurring', 'verification_status']  # Will add when django-filter is available
    ordering_fields = ['start_date', 'detection_timestamp', 'average_price_impact_pct']
    ordering = ['start_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by upcoming events
        upcoming = self.request.query_params.get('upcoming')
        if upcoming == 'true':
            today = timezone.now().date()
            future_date = today + timedelta(days=90)  # Next 90 days
            queryset = queryset.filter(
                start_date__range=[today, future_date],
                is_active=True
            )
        
        # Filter by active events
        active = self.request.query_params.get('active')
        if active == 'true':
            queryset = queryset.filter(is_active=True)
        elif active == 'false':
            queryset = queryset.filter(is_active=False)
        
        # Filter by verified events
        verified = self.request.query_params.get('verified')
        if verified == 'true':
            queryset = queryset.filter(verification_status='verified')
        
        # Filter by significant impact
        significant_impact = self.request.query_params.get('significant_impact')
        if significant_impact == 'true':
            queryset = queryset.filter(
                Q(average_price_impact_pct__gte=5.0) |
                Q(average_price_impact_pct__lte=-5.0) |
                Q(average_volume_impact_pct__gte=20.0) |
                Q(average_volume_impact_pct__lte=-20.0)
            )
        
        return queryset


class SeasonalEventDetailView(generics.RetrieveAPIView):
    """Get detailed event information."""
    queryset = SeasonalEvent.objects.all()
    serializer_class = SeasonalEventSerializer


# =============================================================================
# SEASONAL RECOMMENDATION VIEWS
# =============================================================================

class SeasonalRecommendationListView(generics.ListAPIView):
    """
    List seasonal trading recommendations.
    
    Query Parameters:
    - item_id: Filter by specific item
    - recommendation_type: buy, sell, hold, avoid
    - active: true/false - show only active recommendations
    - executed: true/false - show only executed recommendations
    - min_confidence: Minimum confidence level (0-1)
    """
    queryset = SeasonalRecommendation.objects.select_related('seasonal_pattern__item').all()
    serializer_class = SeasonalRecommendationSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    # filterset_fields = ['recommendation_type', 'primary_pattern', 'is_active', 'is_executed']  # Will add when django-filter is available
    ordering_fields = ['confidence_score', 'recommendation_timestamp', 'expected_impact_pct']
    ordering = ['-confidence_score']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by item
        item_id = self.request.query_params.get('item_id')
        if item_id:
            queryset = queryset.filter(seasonal_pattern__item__item_id=item_id)
        
        # Filter by current validity
        current = self.request.query_params.get('current')
        if current == 'true':
            today = timezone.now().date()
            queryset = queryset.filter(
                valid_from__lte=today,
                valid_until__gte=today
            )
        
        # Filter by minimum confidence
        min_confidence = self.request.query_params.get('min_confidence')
        if min_confidence:
            try:
                min_confidence = float(min_confidence)
                queryset = queryset.filter(confidence_score__gte=min_confidence)
            except (ValueError, TypeError):
                pass
        
        return queryset


class SeasonalRecommendationDetailView(generics.RetrieveAPIView):
    """Get detailed recommendation information."""
    queryset = SeasonalRecommendation.objects.select_related('seasonal_pattern__item').all()
    serializer_class = SeasonalRecommendationSerializer


# =============================================================================
# TECHNICAL ANALYSIS VIEWS
# =============================================================================

class TechnicalAnalysisListView(generics.ListAPIView):
    """List technical analysis data."""
    queryset = TechnicalAnalysis.objects.select_related('item').all()
    serializer_class = TechnicalAnalysisSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    # filterset_fields = ['overall_recommendation', 'consensus_signal']  # Will add when django-filter is available
    ordering_fields = ['strength_score', 'analysis_timestamp', 'timeframe_agreement']
    ordering = ['-strength_score']


class TechnicalAnalysisByItemView(generics.RetrieveAPIView):
    """Get the latest technical analysis for a specific item."""
    serializer_class = TechnicalAnalysisSerializer
    
    def get_object(self):
        item_id = self.kwargs['item_id']
        return TechnicalAnalysis.objects.select_related('item').filter(
            item__item_id=item_id
        ).order_by('-analysis_timestamp').first()


# =============================================================================
# MARKET OVERVIEW AND ANALYTICS
# =============================================================================

@api_view(['GET'])
def market_overview(request):
    """
    Get comprehensive market overview with seasonal data.
    """
    try:
        # Calculate overview statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        # Seasonal patterns stats
        total_patterns = SeasonalPattern.objects.count()
        strong_patterns = SeasonalPattern.objects.filter(overall_pattern_strength__gte=0.6).count()
        recent_patterns = SeasonalPattern.objects.filter(analysis_timestamp__gte=week_ago).count()
        
        # Recommendations stats
        active_recommendations = SeasonalRecommendation.objects.filter(
            is_active=True,
            valid_from__lte=today,
            valid_until__gte=today
        ).count()
        
        # Events stats
        upcoming_events = SeasonalEvent.objects.filter(
            start_date__gte=today,
            start_date__lte=today + timedelta(days=30),
            is_active=True
        ).count()
        
        # Forecast accuracy
        validated_forecasts = SeasonalForecast.objects.filter(
            actual_price__isnull=False,
            forecast_timestamp__gte=timezone.now() - timedelta(days=30)
        )
        
        avg_accuracy = 0
        if validated_forecasts.exists():
            total_accuracy = 0
            count = 0
            for forecast in validated_forecasts:
                if forecast.percentage_error is not None:
                    accuracy = 100 - abs(forecast.percentage_error)
                    total_accuracy += accuracy
                    count += 1
            
            if count > 0:
                avg_accuracy = total_accuracy / count
        
        # Market sentiment (from latest sentiment analysis)
        latest_sentiment = SentimentAnalysis.objects.order_by('-analysis_timestamp').first()
        market_sentiment = 'neutral'
        if latest_sentiment:
            market_sentiment = latest_sentiment.overall_sentiment
        
        overview_data = {
            'total_items_analyzed': total_patterns,
            'strong_patterns_count': strong_patterns,
            'active_recommendations': active_recommendations,
            'upcoming_events': upcoming_events,
            'forecast_accuracy': round(avg_accuracy, 1),
            'market_sentiment': market_sentiment,
            'last_updated': timezone.now(),
            'recent_analyses': recent_patterns
        }
        
        serializer = MarketOverviewSerializer(overview_data)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to generate market overview: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def seasonal_analytics(request):
    """
    Get seasonal analytics dashboard data.
    """
    try:
        # Get top performing patterns
        top_patterns = SeasonalPattern.objects.select_related('item').filter(
            overall_pattern_strength__gte=0.5
        ).order_by('-overall_pattern_strength')[:10]
        
        # Get upcoming high-confidence forecasts
        today = timezone.now().date()
        upcoming_forecasts = SeasonalForecast.objects.select_related('seasonal_pattern__item').filter(
            target_date__gte=today,
            target_date__lte=today + timedelta(days=30),
            confidence_level__gte=0.7
        ).order_by('target_date')[:10]
        
        # Get active high-confidence recommendations
        active_recommendations = SeasonalRecommendation.objects.select_related('seasonal_pattern__item').filter(
            is_active=True,
            valid_from__lte=today,
            valid_until__gte=today,
            confidence_score__gte=0.7
        ).order_by('-confidence_score')[:10]
        
        # Get upcoming significant events
        upcoming_events = SeasonalEvent.objects.filter(
            start_date__gte=today,
            start_date__lte=today + timedelta(days=60),
            is_active=True,
            verification_status='verified'
        ).order_by('start_date')[:5]
        
        data = {
            'top_patterns': SeasonalPatternSummarySerializer(top_patterns, many=True).data,
            'upcoming_forecasts': SeasonalForecastSerializer(upcoming_forecasts, many=True).data,
            'active_recommendations': SeasonalRecommendationSerializer(active_recommendations, many=True).data,
            'upcoming_events': SeasonalEventSerializer(upcoming_events, many=True).data,
            'generated_at': timezone.now()
        }
        
        return Response(data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to generate seasonal analytics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def forecast_accuracy_stats(request):
    """
    Get forecast accuracy statistics and performance metrics.
    """
    try:
        days_back = int(request.query_params.get('days_back', 30))
        cutoff_date = timezone.now() - timedelta(days=days_back)
        
        # Get validated forecasts
        validated_forecasts = SeasonalForecast.objects.filter(
            actual_price__isnull=False,
            validation_date__gte=cutoff_date
        )
        
        if not validated_forecasts.exists():
            return Response({'message': 'No validated forecasts found for the specified period'})
        
        # Calculate accuracy by horizon
        accuracy_by_horizon = {}
        for horizon in ['1d', '3d', '7d', '14d', '30d']:
            horizon_forecasts = validated_forecasts.filter(horizon=horizon)
            if horizon_forecasts.exists():
                total_accuracy = 0
                count = 0
                
                for forecast in horizon_forecasts:
                    if forecast.percentage_error is not None:
                        accuracy = 100 - abs(forecast.percentage_error)
                        total_accuracy += accuracy
                        count += 1
                
                if count > 0:
                    accuracy_by_horizon[horizon] = {
                        'average_accuracy': round(total_accuracy / count, 1),
                        'forecast_count': count,
                        'ci_hit_rate': round(
                            (horizon_forecasts.filter(is_within_confidence_interval=True).count() / count) * 100, 1
                        )
                    }
        
        # Overall statistics
        total_forecasts = validated_forecasts.count()
        ci_hits = validated_forecasts.filter(is_within_confidence_interval=True).count()
        ci_hit_rate = (ci_hits / total_forecasts) * 100 if total_forecasts > 0 else 0
        
        data = {
            'total_validated_forecasts': total_forecasts,
            'overall_ci_hit_rate': round(ci_hit_rate, 1),
            'accuracy_by_horizon': accuracy_by_horizon,
            'period_days': days_back,
            'generated_at': timezone.now()
        }
        
        return Response(data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to generate accuracy stats: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =============================================================================
# LEGACY/ADDITIONAL VIEWS
# =============================================================================

class MarketMomentumListView(generics.ListAPIView):
    """List market momentum data."""
    queryset = MarketMomentum.objects.select_related('item').all()
    serializer_class = MarketMomentumSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    # filterset_fields = ['trend_direction']  # Will add when django-filter is available
    ordering_fields = ['momentum_score', 'last_updated']
    ordering = ['-momentum_score']


class SentimentAnalysisListView(generics.ListAPIView):
    """List sentiment analysis data."""
    queryset = SentimentAnalysis.objects.all()
    serializer_class = SentimentAnalysisSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['analysis_timestamp', 'sentiment_score']
    ordering = ['-analysis_timestamp']


class PricePredictionListView(generics.ListAPIView):
    """List price predictions."""
    queryset = PricePrediction.objects.select_related('item').all()
    serializer_class = PricePredictionSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    # filterset_fields = ['trend_direction']  # Will add when django-filter is available
    ordering_fields = ['prediction_timestamp']
    ordering = ['-prediction_timestamp']


class PricePredictionByItemView(generics.RetrieveAPIView):
    """Get the latest price prediction for a specific item."""
    serializer_class = PricePredictionSerializer
    
    def get_object(self):
        item_id = self.kwargs['item_id']
        return PricePrediction.objects.select_related('item').filter(
            item__item_id=item_id
        ).order_by('-prediction_timestamp').first()