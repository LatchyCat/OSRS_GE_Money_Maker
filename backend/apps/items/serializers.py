"""
Serializers for Items API endpoints.
"""

from rest_framework import serializers
from .models import Item, ItemCategory
from apps.prices.models import PriceSnapshot, ProfitCalculation


class ItemCategorySerializer(serializers.ModelSerializer):
    """Serializer for item categories."""
    
    class Meta:
        model = ItemCategory
        fields = ['id', 'name', 'description']


class PriceSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for price snapshots."""
    
    profit_if_buy_high = serializers.ReadOnlyField()
    profit_margin_if_buy_high = serializers.ReadOnlyField()
    is_high_volume = serializers.ReadOnlyField()
    is_volatile = serializers.ReadOnlyField()
    recommended_update_frequency_minutes = serializers.ReadOnlyField()
    
    class Meta:
        model = PriceSnapshot
        fields = [
            'id', 'high_price', 'high_time', 'low_price', 'low_time',
            'high_price_volume', 'low_price_volume', 'total_volume',
            'price_volatility', 'price_change_pct', 'data_interval',
            'created_at', 'profit_if_buy_high', 'profit_margin_if_buy_high',
            'is_high_volume', 'is_volatile', 'recommended_update_frequency_minutes'
        ]


class ProfitCalculationSerializer(serializers.ModelSerializer):
    """Serializer for profit calculations."""
    
    is_profitable = serializers.ReadOnlyField()
    is_hot_item = serializers.ReadOnlyField()
    volume_adjusted_profit = serializers.ReadOnlyField()
    recommended_update_frequency_minutes = serializers.ReadOnlyField()
    price_source_metadata = serializers.SerializerMethodField()
    
    class Meta:
        model = ProfitCalculation
        fields = [
            'current_buy_price', 'current_sell_price', 'current_profit',
            'current_profit_margin', 'daily_volume', 'hourly_volume', 'five_min_volume',
            'price_trend', 'volume_category', 'price_volatility', 'price_momentum',
            'recommendation_score', 'volume_weighted_score', 'is_profitable',
            'is_hot_item', 'volume_adjusted_profit', 'recommended_update_frequency_minutes',
            'data_source', 'data_quality', 'confidence_score', 'data_age_hours', 'source_timestamp',
            'last_updated', 'price_source_metadata'
        ]
    
    def get_price_source_metadata(self, obj):
        """Build nested price source metadata for frontend."""
        return {
            'source': obj.data_source,
            'quality': obj.data_quality, 
            'confidence_score': obj.confidence_score,
            'age_hours': obj.data_age_hours,
            'timestamp': int(obj.source_timestamp.timestamp()) if obj.source_timestamp else 0,
            'volume_high': obj.daily_volume or 0,
            'volume_low': obj.daily_volume or 0
        }


class ItemListSerializer(serializers.ModelSerializer):
    """Serializer for item list view (minimal data)."""
    
    current_profit = serializers.IntegerField(source='profit_calc.current_profit', read_only=True)
    current_profit_margin = serializers.FloatField(source='profit_calc.current_profit_margin', read_only=True)
    current_buy_price = serializers.IntegerField(source='profit_calc.current_buy_price', read_only=True)
    recommendation_score = serializers.IntegerField(source='profit_calc.recommendation_score', read_only=True)
    volume_weighted_score = serializers.IntegerField(source='profit_calc.volume_weighted_score', read_only=True)
    volume_category = serializers.CharField(source='profit_calc.volume_category', read_only=True)
    daily_volume = serializers.IntegerField(source='profit_calc.daily_volume', read_only=True)
    is_hot_item = serializers.BooleanField(source='profit_calc.is_hot_item', read_only=True)
    volume_adjusted_profit = serializers.IntegerField(source='profit_calc.volume_adjusted_profit', read_only=True)
    
    # Multi-source transparency fields (backward compatibility)
    data_source = serializers.CharField(source='profit_calc.data_source', read_only=True)
    data_quality = serializers.CharField(source='profit_calc.data_quality', read_only=True)
    confidence_score = serializers.FloatField(source='profit_calc.confidence_score', read_only=True)
    data_age_hours = serializers.FloatField(source='profit_calc.data_age_hours', read_only=True)
    
    # Nested profit calc with price_source_metadata for frontend
    profit_calc = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = [
            'item_id', 'name', 'examine', 'high_alch', 'members', 'limit',
            'current_profit', 'current_profit_margin', 'current_buy_price',
            'recommendation_score', 'volume_weighted_score', 'volume_category',
            'daily_volume', 'is_hot_item', 'volume_adjusted_profit',
            'data_source', 'data_quality', 'confidence_score', 'data_age_hours',
            'profit_calc'
        ]
    
    def get_profit_calc(self, obj):
        """Get minimal profit calc data with price_source_metadata for frontend."""
        if not obj.profit_calc:
            return None
            
        profit_calc = obj.profit_calc
        return {
            'current_buy_price': profit_calc.current_buy_price,
            'current_profit': profit_calc.current_profit,
            'current_profit_margin': profit_calc.current_profit_margin,
            'recommendation_score': profit_calc.recommendation_score,
            'is_hot_item': profit_calc.is_hot_item,
            'volume_adjusted_profit': profit_calc.volume_adjusted_profit,
            'price_source_metadata': {
                'source': profit_calc.data_source,
                'quality': profit_calc.data_quality,
                'confidence_score': profit_calc.confidence_score,
                'age_hours': profit_calc.data_age_hours,
                'timestamp': int(profit_calc.source_timestamp.timestamp()) if profit_calc.source_timestamp else 0,
                'volume_high': profit_calc.daily_volume or 0,
                'volume_low': profit_calc.daily_volume or 0
            }
        }


class ItemDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed item view."""
    
    base_profit_per_item = serializers.ReadOnlyField()
    categories = ItemCategorySerializer(source='categories.all', many=True, read_only=True)
    profit_calc = ProfitCalculationSerializer(read_only=True)
    latest_price = serializers.SerializerMethodField()
    price_history = serializers.SerializerMethodField()
    
    class Meta:
        model = Item
        fields = [
            'item_id', 'name', 'examine', 'icon', 'value', 'high_alch', 'low_alch',
            'limit', 'members', 'is_active', 'created_at', 'updated_at',
            'base_profit_per_item', 'categories', 'profit_calc',
            'latest_price', 'price_history'
        ]
    
    def get_latest_price(self, obj):
        """Get the latest price snapshot."""
        latest = obj.price_snapshots.order_by('-created_at').first()
        if latest:
            return PriceSnapshotSerializer(latest).data
        return None
    
    def get_price_history(self, obj):
        """Get recent price history (last 24 hours)."""
        from django.utils import timezone
        from datetime import timedelta
        
        since = timezone.now() - timedelta(hours=24)
        history = obj.price_snapshots.filter(created_at__gte=since).order_by('-created_at')[:10]
        return PriceSnapshotSerializer(history, many=True).data


class SearchResultSerializer(serializers.Serializer):
    """Serializer for search results."""
    
    item_id = serializers.IntegerField()
    name = serializers.CharField()
    examine = serializers.CharField()
    high_alch = serializers.IntegerField()
    members = serializers.BooleanField()
    limit = serializers.IntegerField()
    
    # Search scoring
    semantic_score = serializers.FloatField()
    profit_score = serializers.FloatField()
    hybrid_score = serializers.FloatField()
    
    # Profit data
    current_profit = serializers.IntegerField()
    current_profit_margin = serializers.FloatField()
    current_buy_price = serializers.IntegerField(allow_null=True)
    daily_volume = serializers.IntegerField()


class SearchResponseSerializer(serializers.Serializer):
    """Serializer for search response."""
    
    query = serializers.CharField()
    results = SearchResultSerializer(many=True)
    total_found = serializers.IntegerField()
    search_time_ms = serializers.IntegerField()
    filters_applied = serializers.DictField()
    ai_insights = serializers.DictField(allow_null=True)
    timestamp = serializers.DateTimeField()


class RecommendationSerializer(serializers.Serializer):
    """Serializer for AI recommendations."""
    
    item_id = serializers.IntegerField()
    name = serializers.CharField()
    examine = serializers.CharField()
    high_alch = serializers.IntegerField()
    current_profit = serializers.IntegerField()
    current_profit_margin = serializers.FloatField()
    current_buy_price = serializers.IntegerField(allow_null=True)
    daily_volume = serializers.IntegerField()
    recommendation_score = serializers.IntegerField()
    risk_level = serializers.CharField()


class ProfitRecommendationsSerializer(serializers.Serializer):
    """Serializer for profit recommendations response."""
    
    recommendations = RecommendationSerializer(many=True)
    total_found = serializers.IntegerField()
    market_summary = serializers.DictField(allow_null=True)
    filters = serializers.DictField()
    generated_at = serializers.DateTimeField()