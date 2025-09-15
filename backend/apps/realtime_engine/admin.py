from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.forms import TextInput, Textarea
from .models import (MarketMomentum, VolumeAnalysis, RiskMetrics, MarketEvent, 
                     StreamingDataStatus, GELimitEntry, SentimentAnalysis, ItemSentiment, PricePrediction,
                     PortfolioOptimization, PortfolioAllocation, PortfolioRebalance, PortfolioAction,
                     TechnicalAnalysis, TechnicalIndicator, TechnicalSignal, SeasonalPattern,
                     SeasonalForecast, SeasonalEvent, SeasonalRecommendation)


@admin.register(MarketMomentum)
class MarketMomentumAdmin(admin.ModelAdmin):
    list_display = ['item', 'momentum_score', 'trend_direction', 'price_velocity', 'last_updated']
    list_filter = ['trend_direction', 'last_updated']
    search_fields = ['item__name']
    ordering = ['-momentum_score']
    readonly_fields = ['last_updated']


@admin.register(VolumeAnalysis)
class VolumeAnalysisAdmin(admin.ModelAdmin):
    list_display = ['item', 'current_daily_volume', 'liquidity_level', 'flip_completion_probability', 'last_updated']
    list_filter = ['liquidity_level', 'last_updated']
    search_fields = ['item__name']
    ordering = ['-current_daily_volume']


@admin.register(RiskMetrics)
class RiskMetricsAdmin(admin.ModelAdmin):
    list_display = ['item', 'overall_risk_score', 'risk_category', 'recommended_max_investment_pct', 'last_updated']
    list_filter = ['risk_category', 'last_updated']
    search_fields = ['item__name']
    ordering = ['overall_risk_score']


@admin.register(MarketEvent)
class MarketEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'title', 'impact_score', 'is_active', 'detected_at']
    list_filter = ['event_type', 'is_active', 'detected_at']
    search_fields = ['title', 'description']
    ordering = ['-detected_at']


@admin.register(StreamingDataStatus)
class StreamingDataStatusAdmin(admin.ModelAdmin):
    list_display = ['source', 'status_indicator', 'last_successful_update', 'success_rate_24h', 'data_freshness_minutes']
    list_filter = ['is_active', 'source']
    ordering = ['-last_successful_update']
    
    def status_indicator(self, obj):
        if obj.is_healthy:
            return format_html('<span style="color: green;">●</span> Healthy')
        elif obj.is_active:
            return format_html('<span style="color: orange;">●</span> Active (Issues)')
        else:
            return format_html('<span style="color: red;">●</span> Inactive')
    status_indicator.short_description = 'Status'
    status_indicator.admin_order_field = 'is_active'


@admin.register(GELimitEntry)
class GELimitEntryAdmin(admin.ModelAdmin):
    list_display = [
        'user_username', 'item_name', 'utilization_display', 
        'total_investment', 'average_purchase_price', 'reset_status', 'is_active'
    ]
    list_filter = ['is_active', 'is_limit_reached', 'created_at']
    search_fields = ['user__username', 'item__name']
    readonly_fields = [
        'created_at', 'updated_at', 'remaining_limit', 
        'limit_utilization_pct', 'minutes_until_reset'
    ]
    
    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'User'
    user_username.admin_order_field = 'user__username'
    
    def item_name(self, obj):
        return obj.item.name
    item_name.short_description = 'Item'
    item_name.admin_order_field = 'item__name'
    
    def utilization_display(self, obj):
        pct = obj.limit_utilization_pct
        color = 'red' if pct >= 90 else 'orange' if pct >= 75 else 'green'
        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color, obj.quantity_bought, obj.max_limit, round(pct, 1)
        )
    utilization_display.short_description = 'Utilization'
    utilization_display.admin_order_field = 'quantity_bought'
    
    def reset_status(self, obj):
        if obj.is_limit_expired():
            return format_html('<span style="color: green;">Ready to Reset</span>')
        else:
            minutes = obj.minutes_until_reset
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m remaining"
    reset_status.short_description = 'Reset Status'
    
    fieldsets = (
        ('User & Item', {
            'fields': ('user', 'item')
        }),
        ('Limit Information', {
            'fields': (
                'quantity_bought', 'max_limit', 'remaining_limit', 
                'limit_utilization_pct', 'is_limit_reached'
            )
        }),
        ('Financial Details', {
            'fields': ('total_investment', 'average_purchase_price')
        }),
        ('Timing', {
            'fields': (
                'last_purchase_time', 'limit_reset_time', 
                'minutes_until_reset'
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['reset_selected_limits', 'activate_limits', 'deactivate_limits']
    
    def reset_selected_limits(self, request, queryset):
        """Admin action to reset selected GE limits."""
        count = 0
        for limit_entry in queryset:
            limit_entry.reset_limit()
            count += 1
        
        self.message_user(
            request,
            f'Successfully reset {count} GE limit entries.'
        )
    reset_selected_limits.short_description = "Reset selected GE limits"
    
    def activate_limits(self, request, queryset):
        """Admin action to activate selected limits."""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f'Successfully activated {count} GE limit entries.'
        )
    activate_limits.short_description = "Activate selected limits"
    
    def deactivate_limits(self, request, queryset):
        """Admin action to deactivate selected limits."""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f'Successfully deactivated {count} GE limit entries.'
        )
    deactivate_limits.short_description = "Deactivate selected limits"


@admin.register(SentimentAnalysis)
class SentimentAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'source', 'overall_sentiment', 'sentiment_score', 'confidence',
        'analyzed_articles', 'analysis_timestamp'
    ]
    list_filter = ['source', 'overall_sentiment', 'analysis_timestamp']
    search_fields = ['key_themes']
    readonly_fields = ['analysis_timestamp', 'sentiment_strength']
    
    def sentiment_strength(self, obj):
        return obj.sentiment_strength
    sentiment_strength.short_description = 'Sentiment Strength'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('source', 'analysis_timestamp', 'analyzed_articles')
        }),
        ('Sentiment Analysis', {
            'fields': ('overall_sentiment', 'sentiment_score', 'confidence', 'sentiment_strength')
        }),
        ('Analysis Results', {
            'fields': ('key_themes', 'sentiment_breakdown', 'top_mentioned_items')
        }),
        ('Market Predictions', {
            'fields': ('market_impact_predictions', 'category_sentiment')
        }),
        ('Metadata', {
            'fields': ('analysis_duration_seconds', 'data_quality_score'),
            'classes': ('collapse',)
        })
    )
    
    formfield_overrides = {
        models.JSONField: {'widget': Textarea(attrs={'rows': 4, 'cols': 80})},
    }


@admin.register(ItemSentiment)
class ItemSentimentAdmin(admin.ModelAdmin):
    list_display = [
        'item_name', 'sentiment_display', 'mention_count', 
        'predicted_impact', 'confidence', 'analysis_timestamp', 'significance_indicator'
    ]
    list_filter = ['sentiment_label', 'predicted_impact', 'analysis_timestamp']
    search_fields = ['item__name']
    readonly_fields = ['analysis_timestamp', 'is_significant']
    
    def item_name(self, obj):
        return obj.item.name
    item_name.short_description = 'Item'
    item_name.admin_order_field = 'item__name'
    
    def sentiment_display(self, obj):
        color = 'green' if obj.sentiment_score > 0.1 else 'red' if obj.sentiment_score < -0.1 else 'gray'
        return format_html(
            '<span style="color: {};">{} ({:.2f})</span>',
            color, obj.sentiment_label, obj.sentiment_score
        )
    sentiment_display.short_description = 'Sentiment'
    sentiment_display.admin_order_field = 'sentiment_score'
    
    def significance_indicator(self, obj):
        if obj.is_significant:
            return format_html('<span style="color: orange;">●</span> Significant')
        return format_html('<span style="color: lightgray;">○</span> Minor')
    significance_indicator.short_description = 'Significance'
    
    fieldsets = (
        ('Item Information', {
            'fields': ('item',)
        }),
        ('Sentiment Data', {
            'fields': ('sentiment_score', 'sentiment_label', 'mention_count', 'confidence')
        }),
        ('Analysis Context', {
            'fields': ('sample_contexts', 'sources')
        }),
        ('Predictions', {
            'fields': ('predicted_impact', 'is_significant')
        }),
        ('Metadata', {
            'fields': ('analysis_timestamp',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_significant', 'export_sentiment_data']
    
    def mark_as_significant(self, request, queryset):
        """Mark selected items as having significant sentiment."""
        # This would typically update some field or create alerts
        count = queryset.count()
        self.message_user(
            request,
            f'Marked {count} sentiment analyses for review.'
        )
    mark_as_significant.short_description = "Mark as significant for review"
    
    def export_sentiment_data(self, request, queryset):
        """Export sentiment data for analysis."""
        # This would typically generate CSV or JSON export
        count = queryset.count()
        self.message_user(
            request,
            f'Export functionality would process {count} records.'
        )
    export_sentiment_data.short_description = "Export sentiment data"


@admin.register(PricePrediction)
class PricePredictionAdmin(admin.ModelAdmin):
    list_display = [
        'item_name', 'trend_direction', 'current_price', 'predicted_24h_change',
        'confidence_display', 'prediction_timestamp', 'accuracy_indicator'
    ]
    list_filter = ['trend_direction', 'model_version', 'prediction_timestamp']
    search_fields = ['item__name']
    readonly_fields = ['prediction_timestamp', 'is_high_confidence', 'predicted_change_24h_pct']
    
    def item_name(self, obj):
        return obj.item.name
    item_name.short_description = 'Item'
    item_name.admin_order_field = 'item__name'
    
    def predicted_24h_change(self, obj):
        change_pct = obj.predicted_change_24h_pct
        color = 'green' if change_pct > 0 else 'red' if change_pct < 0 else 'gray'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, change_pct
        )
    predicted_24h_change.short_description = '24h Change'
    predicted_24h_change.admin_order_field = 'predicted_price_24h'
    
    def confidence_display(self, obj):
        avg_confidence = (obj.confidence_1h + obj.confidence_4h + obj.confidence_24h) / 3
        color = 'green' if avg_confidence > 0.7 else 'orange' if avg_confidence > 0.5 else 'red'
        return format_html(
            '<span style="color: {};">{:.1%}</span>',
            color, avg_confidence
        )
    confidence_display.short_description = 'Avg Confidence'
    
    def accuracy_indicator(self, obj):
        if obj.error_24h is not None:
            accuracy = 100 - obj.error_24h
            if accuracy > 85:
                return format_html('<span style="color: green;">●</span> Excellent')
            elif accuracy > 70:
                return format_html('<span style="color: orange;">●</span> Good')
            else:
                return format_html('<span style="color: red;">●</span> Poor')
        return format_html('<span style="color: lightgray;">○</span> Pending')
    accuracy_indicator.short_description = 'Accuracy'
    
    fieldsets = (
        ('Item & Timing', {
            'fields': ('item', 'prediction_timestamp', 'current_price')
        }),
        ('Predictions', {
            'fields': (
                ('predicted_price_1h', 'confidence_1h'),
                ('predicted_price_4h', 'confidence_4h'), 
                ('predicted_price_24h', 'confidence_24h')
            )
        }),
        ('Analysis', {
            'fields': ('trend_direction', 'is_high_confidence', 'predicted_change_24h_pct')
        }),
        ('Model Data', {
            'fields': ('prediction_factors', 'model_version', 'prediction_method'),
            'classes': ('collapse',)
        }),
        ('Validation', {
            'fields': (
                ('actual_price_1h', 'error_1h'),
                ('actual_price_4h', 'error_4h'),
                ('actual_price_24h', 'error_24h')
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = ['validate_predictions', 'export_prediction_data']
    
    def validate_predictions(self, request, queryset):
        """Validate selected predictions against current prices."""
        # This would typically update predictions with actual prices
        count = queryset.count()
        self.message_user(
            request,
            f'Validation would process {count} predictions.'
        )
    validate_predictions.short_description = "Validate predictions"
    
    def export_prediction_data(self, request, queryset):
        """Export prediction data for analysis."""
        count = queryset.count()
        self.message_user(
            request,
            f'Export would process {count} predictions.'
        )
    export_prediction_data.short_description = "Export prediction data"


# Customize admin site headers
@admin.register(PortfolioOptimization)
class PortfolioOptimizationAdmin(admin.ModelAdmin):
    list_display = [
        'user_name', 'optimization_method', 'expected_return_display', 
        'risk_display', 'sharpe_ratio_display', 'items_count', 'capital_utilization_display', 
        'optimization_timestamp', 'is_active'
    ]
    list_filter = ['optimization_method', 'is_active', 'optimization_timestamp', 'risk_tolerance']
    search_fields = ['user__username']
    readonly_fields = [
        'optimization_timestamp', 'capital_utilization', 'risk_adjusted_score',
        'total_allocated_capital', 'cash_reserve'
    ]
    
    def user_name(self, obj):
        return obj.user.username
    user_name.short_description = 'User'
    user_name.admin_order_field = 'user__username'
    
    def expected_return_display(self, obj):
        color = 'green' if obj.expected_daily_return > 0.03 else 'orange' if obj.expected_daily_return > 0.01 else 'red'
        return format_html(
            '<span style="color: {};">{:.2%}</span>',
            color, obj.expected_daily_return
        )
    expected_return_display.short_description = 'Expected Return'
    expected_return_display.admin_order_field = 'expected_daily_return'
    
    def risk_display(self, obj):
        color = 'red' if obj.expected_daily_risk > 0.1 else 'orange' if obj.expected_daily_risk > 0.05 else 'green'
        return format_html(
            '<span style="color: {};">{:.2%}</span>',
            color, obj.expected_daily_risk
        )
    risk_display.short_description = 'Risk'
    risk_display.admin_order_field = 'expected_daily_risk'
    
    def sharpe_ratio_display(self, obj):
        color = 'green' if obj.sharpe_ratio > 1.5 else 'orange' if obj.sharpe_ratio > 1.0 else 'red'
        return format_html(
            '<span style="color: {};">{:.2f}</span>',
            color, obj.sharpe_ratio
        )
    sharpe_ratio_display.short_description = 'Sharpe Ratio'
    sharpe_ratio_display.admin_order_field = 'sharpe_ratio'
    
    def items_count(self, obj):
        return obj.allocations.count()
    items_count.short_description = 'Items'
    
    def capital_utilization_display(self, obj):
        utilization = obj.capital_utilization
        color = 'green' if utilization > 90 else 'orange' if utilization > 70 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, utilization
        )
    capital_utilization_display.short_description = 'Capital Use'
    
    fieldsets = (
        ('User & Timing', {
            'fields': ('user', 'optimization_timestamp', 'is_active')
        }),
        ('Capital Allocation', {
            'fields': ('total_capital', 'total_allocated_capital', 'cash_reserve', 'capital_utilization')
        }),
        ('Optimization Settings', {
            'fields': ('optimization_method', 'target_return', 'risk_tolerance')
        }),
        ('Portfolio Constraints', {
            'fields': ('max_position_size', 'min_position_size', 'max_items', 'liquidity_requirement')
        }),
        ('Performance Metrics', {
            'fields': (
                ('expected_daily_return', 'expected_daily_risk'),
                ('sharpe_ratio', 'sortino_ratio'),
                ('diversification_ratio', 'risk_adjusted_score')
            )
        }),
        ('Results', {
            'fields': ('recommended_items_count', 'performance_score')
        })
    )
    
    actions = ['deactivate_portfolios', 'reoptimize_portfolios']
    
    def deactivate_portfolios(self, request, queryset):
        """Deactivate selected portfolio optimizations."""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f'Successfully deactivated {count} portfolio optimizations.'
        )
    deactivate_portfolios.short_description = "Deactivate selected portfolios"
    
    def reoptimize_portfolios(self, request, queryset):
        """Mark selected portfolios for re-optimization."""
        count = queryset.count()
        self.message_user(
            request,
            f'Re-optimization would process {count} portfolios.'
        )
    reoptimize_portfolios.short_description = "Mark for re-optimization"


@admin.register(PortfolioAllocation)
class PortfolioAllocationAdmin(admin.ModelAdmin):
    list_display = [
        'portfolio_user', 'item_name', 'weight_display', 'allocated_capital_display',
        'quantity_display', 'expected_return_display', 'confidence_display',
        'status', 'fill_progress'
    ]
    list_filter = ['status', 'portfolio__optimization_method', 'created_at']
    search_fields = ['item__name', 'portfolio__user__username']
    readonly_fields = [
        'created_at', 'updated_at', 'fill_percentage', 'unrealized_pnl', 'is_high_conviction'
    ]
    
    def portfolio_user(self, obj):
        return obj.portfolio.user.username
    portfolio_user.short_description = 'User'
    portfolio_user.admin_order_field = 'portfolio__user__username'
    
    def item_name(self, obj):
        return obj.item.name
    item_name.short_description = 'Item'
    item_name.admin_order_field = 'item__name'
    
    def weight_display(self, obj):
        color = 'green' if obj.weight > 0.15 else 'orange' if obj.weight > 0.05 else 'gray'
        return format_html(
            '<span style="color: {};">{:.1%}</span>',
            color, obj.weight
        )
    weight_display.short_description = 'Weight'
    weight_display.admin_order_field = 'weight'
    
    def allocated_capital_display(self, obj):
        return f"{obj.allocated_capital:,} GP"
    allocated_capital_display.short_description = 'Capital'
    allocated_capital_display.admin_order_field = 'allocated_capital'
    
    def quantity_display(self, obj):
        if obj.quantity_filled > 0:
            return f"{obj.quantity_filled}/{obj.recommended_quantity}"
        return str(obj.recommended_quantity)
    quantity_display.short_description = 'Quantity'
    
    def expected_return_display(self, obj):
        color = 'green' if obj.expected_return > 0.05 else 'orange' if obj.expected_return > 0.02 else 'red'
        return format_html(
            '<span style="color: {};">{:.2%}</span>',
            color, obj.expected_return
        )
    expected_return_display.short_description = 'Expected Return'
    expected_return_display.admin_order_field = 'expected_return'
    
    def confidence_display(self, obj):
        color = 'green' if obj.confidence_score > 0.8 else 'orange' if obj.confidence_score > 0.6 else 'red'
        return format_html(
            '<span style="color: {};">{:.1%}</span>',
            color, obj.confidence_score
        )
    confidence_display.short_description = 'Confidence'
    confidence_display.admin_order_field = 'confidence_score'
    
    def fill_progress(self, obj):
        progress = obj.fill_percentage
        color = 'green' if progress == 100 else 'orange' if progress > 0 else 'gray'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, progress
        )
    fill_progress.short_description = 'Filled'
    
    fieldsets = (
        ('Portfolio & Item', {
            'fields': ('portfolio', 'item')
        }),
        ('Allocation Details', {
            'fields': ('weight', 'allocated_capital', 'recommended_quantity', 'target_price')
        }),
        ('Risk & Returns', {
            'fields': ('individual_risk', 'contribution_to_risk', 'beta', 'expected_return', 'confidence_score')
        }),
        ('Execution', {
            'fields': ('status', 'quantity_filled', 'average_fill_price', 'fill_percentage', 'unrealized_pnl')
        }),
        ('Analysis', {
            'fields': ('allocation_reasons', 'ge_limit_utilized', 'liquidity_score', 'is_high_conviction'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_filled', 'cancel_allocations']
    
    def mark_as_filled(self, request, queryset):
        """Mark selected allocations as filled."""
        count = 0
        for allocation in queryset:
            if allocation.status == 'recommended':
                allocation.status = 'filled'
                allocation.quantity_filled = allocation.recommended_quantity
                allocation.save()
                count += 1
        
        self.message_user(
            request,
            f'Marked {count} allocations as filled.'
        )
    mark_as_filled.short_description = "Mark as filled"
    
    def cancel_allocations(self, request, queryset):
        """Cancel selected allocations."""
        count = queryset.update(status='cancelled')
        self.message_user(
            request,
            f'Cancelled {count} allocations.'
        )
    cancel_allocations.short_description = "Cancel allocations"


@admin.register(PortfolioRebalance)
class PortfolioRebalanceAdmin(admin.ModelAdmin):
    list_display = [
        'portfolio_user', 'trigger_reason', 'status', 'completion_display',
        'performance_change', 'rebalance_timestamp', 'duration'
    ]
    list_filter = ['trigger_reason', 'status', 'rebalance_timestamp']
    search_fields = ['portfolio__user__username']
    readonly_fields = [
        'rebalance_timestamp', 'completion_rate', 'performance_improvement',
        'execution_duration_minutes'
    ]
    
    def portfolio_user(self, obj):
        return obj.portfolio.user.username
    portfolio_user.short_description = 'User'
    portfolio_user.admin_order_field = 'portfolio__user__username'
    
    def completion_display(self, obj):
        completion = obj.completion_rate
        color = 'green' if completion == 100 else 'orange' if completion > 50 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, completion
        )
    completion_display.short_description = 'Completion'
    
    def performance_change(self, obj):
        improvement = obj.performance_improvement
        if improvement is not None:
            color = 'green' if improvement > 0 else 'red' if improvement < 0 else 'gray'
            return format_html(
                '<span style="color: {};">{:+.3f}</span>',
                color, improvement
            )
        return '-'
    performance_change.short_description = 'Δ Sharpe'
    
    def duration(self, obj):
        if obj.execution_duration_minutes:
            hours = obj.execution_duration_minutes // 60
            minutes = obj.execution_duration_minutes % 60
            return f"{hours}h {minutes}m"
        return '-'
    duration.short_description = 'Duration'
    
    fieldsets = (
        ('Portfolio & Timing', {
            'fields': ('portfolio', 'rebalance_timestamp', 'trigger_reason')
        }),
        ('Pre-Rebalance Metrics', {
            'fields': ('pre_rebalance_return', 'pre_rebalance_risk', 'pre_rebalance_sharpe')
        }),
        ('Post-Rebalance Metrics', {
            'fields': ('post_rebalance_return', 'post_rebalance_risk', 'post_rebalance_sharpe')
        }),
        ('Execution', {
            'fields': ('status', 'total_trades_required', 'completed_trades', 'failed_trades')
        }),
        ('Performance', {
            'fields': ('completion_rate', 'performance_improvement', 'total_transaction_cost')
        }),
        ('Metadata', {
            'fields': ('execution_duration_minutes', 'rebalance_notes'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_completed', 'cancel_rebalances']
    
    def mark_completed(self, request, queryset):
        """Mark selected rebalances as completed."""
        count = 0
        for rebalance in queryset:
            if rebalance.status in ['pending', 'in_progress']:
                rebalance.mark_completed()
                count += 1
        
        self.message_user(
            request,
            f'Marked {count} rebalances as completed.'
        )
    mark_completed.short_description = "Mark as completed"
    
    def cancel_rebalances(self, request, queryset):
        """Cancel selected rebalances."""
        count = queryset.filter(status__in=['pending', 'in_progress']).update(status='failed')
        self.message_user(
            request,
            f'Cancelled {count} rebalances.'
        )
    cancel_rebalances.short_description = "Cancel rebalances"


@admin.register(PortfolioAction)
class PortfolioActionAdmin(admin.ModelAdmin):
    list_display = [
        'rebalance_user', 'action_type', 'item_name', 'quantity_display',
        'target_price', 'status', 'progress_display', 'priority', 'created_at'
    ]
    list_filter = ['action_type', 'status', 'priority', 'created_at']
    search_fields = ['item__name', 'rebalance__portfolio__user__username']
    readonly_fields = [
        'created_at', 'updated_at', 'execution_progress', 'estimated_value', 'actual_slippage'
    ]
    
    def rebalance_user(self, obj):
        return obj.rebalance.portfolio.user.username
    rebalance_user.short_description = 'User'
    rebalance_user.admin_order_field = 'rebalance__portfolio__user__username'
    
    def item_name(self, obj):
        return obj.item.name
    item_name.short_description = 'Item'
    item_name.admin_order_field = 'item__name'
    
    def quantity_display(self, obj):
        if obj.executed_quantity > 0:
            return f"{obj.executed_quantity}/{abs(obj.quantity_change)}"
        return str(abs(obj.quantity_change))
    quantity_display.short_description = 'Quantity'
    
    def progress_display(self, obj):
        progress = obj.execution_progress
        color = 'green' if progress == 100 else 'orange' if progress > 0 else 'gray'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, progress
        )
    progress_display.short_description = 'Progress'
    
    fieldsets = (
        ('Action Details', {
            'fields': ('rebalance', 'item', 'action_type', 'priority')
        }),
        ('Quantities & Pricing', {
            'fields': ('target_quantity', 'current_quantity', 'quantity_change', 'target_price')
        }),
        ('Execution', {
            'fields': ('status', 'executed_quantity', 'average_execution_price', 'execution_timestamp')
        }),
        ('Constraints', {
            'fields': ('respects_ge_limit', 'max_slippage_pct', 'estimated_execution_time')
        }),
        ('Analysis', {
            'fields': ('execution_progress', 'estimated_value', 'actual_slippage'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('failure_reason', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['execute_actions', 'cancel_actions', 'set_high_priority']
    
    def execute_actions(self, request, queryset):
        """Mark selected actions as executed."""
        count = 0
        for action in queryset:
            if action.status == 'pending':
                action.status = 'completed'
                action.executed_quantity = abs(action.quantity_change)
                action.average_execution_price = action.target_price
                action.save()
                count += 1
        
        self.message_user(
            request,
            f'Executed {count} actions.'
        )
    execute_actions.short_description = "Execute actions"
    
    def cancel_actions(self, request, queryset):
        """Cancel selected actions."""
        count = queryset.update(status='cancelled')
        self.message_user(
            request,
            f'Cancelled {count} actions.'
        )
    cancel_actions.short_description = "Cancel actions"
    
    def set_high_priority(self, request, queryset):
        """Set selected actions to high priority."""
        count = queryset.update(priority=1)
        self.message_user(
            request,
            f'Set {count} actions to high priority.'
        )
    set_high_priority.short_description = "Set high priority"


@admin.register(TechnicalAnalysis)
class TechnicalAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'item_name', 'overall_recommendation', 'strength_display', 'consensus_signal',
        'timeframe_agreement_display', 'signal_quality_display', 'analysis_timestamp',
        'high_conviction_indicator'
    ]
    list_filter = ['overall_recommendation', 'consensus_signal', 'analysis_timestamp', 'conflicting_signals']
    search_fields = ['item__name']
    readonly_fields = [
        'analysis_timestamp', 'is_high_conviction', 'signal_quality', 
        'analysis_duration_seconds'
    ]
    
    def item_name(self, obj):
        return obj.item.name
    item_name.short_description = 'Item'
    item_name.admin_order_field = 'item__name'
    
    def strength_display(self, obj):
        color = 'green' if obj.strength_score >= 70 else 'orange' if obj.strength_score >= 50 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}</span>',
            color, obj.strength_score
        )
    strength_display.short_description = 'Strength'
    strength_display.admin_order_field = 'strength_score'
    
    def timeframe_agreement_display(self, obj):
        agreement = obj.timeframe_agreement * 100
        color = 'green' if agreement >= 60 else 'orange' if agreement >= 40 else 'red'
        return format_html(
            '<span style="color: {};">{:.0f}%</span>',
            color, agreement
        )
    timeframe_agreement_display.short_description = 'Agreement'
    timeframe_agreement_display.admin_order_field = 'timeframe_agreement'
    
    def signal_quality_display(self, obj):
        quality = obj.signal_quality
        color_map = {'excellent': 'green', 'good': 'blue', 'fair': 'orange', 'poor': 'red'}
        color = color_map.get(quality, 'gray')
        return format_html(
            '<span style="color: {};">{}</span>',
            color, quality.title()
        )
    signal_quality_display.short_description = 'Quality'
    
    def high_conviction_indicator(self, obj):
        if obj.is_high_conviction:
            return format_html('<span style="color: green; font-weight: bold;">●</span> High')
        return format_html('<span style="color: lightgray;">○</span> Normal')
    high_conviction_indicator.short_description = 'Conviction'
    
    fieldsets = (
        ('Item & Timing', {
            'fields': ('item', 'analysis_timestamp', 'analysis_duration_seconds')
        }),
        ('Analysis Parameters', {
            'fields': ('timeframes_analyzed', 'lookback_days', 'data_points_used')
        }),
        ('Overall Results', {
            'fields': (
                ('overall_recommendation', 'strength_score'),
                ('consensus_signal', 'timeframe_agreement'),
                ('is_high_conviction', 'signal_quality')
            )
        }),
        ('Signal Details', {
            'fields': ('dominant_timeframes', 'conflicting_signals', 'confidence_score')
        })
    )
    
    actions = ['generate_signals', 'recalculate_strength']
    
    def generate_signals(self, request, queryset):
        """Generate trading signals from selected analyses."""
        count = queryset.count()
        self.message_user(
            request,
            f'Signal generation would process {count} technical analyses.'
        )
    generate_signals.short_description = "Generate trading signals"
    
    def recalculate_strength(self, request, queryset):
        """Recalculate strength scores for selected analyses."""
        count = queryset.count()
        self.message_user(
            request,
            f'Recalculation would process {count} analyses.'
        )
    recalculate_strength.short_description = "Recalculate strength scores"


@admin.register(TechnicalIndicator)
class TechnicalIndicatorAdmin(admin.ModelAdmin):
    list_display = [
        'analysis_item', 'timeframe', 'overall_signal', 'signal_strength_display',
        'rsi_display', 'trend_display', 'bb_position_display', 'volume_signal'
    ]
    list_filter = ['timeframe', 'overall_signal', 'trend_direction', 'rsi_signal']
    search_fields = ['technical_analysis__item__name']
    readonly_fields = [
        'is_oversold', 'is_overbought', 'macd_bullish_crossover', 'bb_squeeze'
    ]
    
    def analysis_item(self, obj):
        return obj.technical_analysis.item.name
    analysis_item.short_description = 'Item'
    analysis_item.admin_order_field = 'technical_analysis__item__name'
    
    def signal_strength_display(self, obj):
        strength = obj.signal_strength * 100
        color = 'green' if strength >= 70 else 'orange' if strength >= 40 else 'red'
        return format_html(
            '<span style="color: {};">{:.0f}%</span>',
            color, strength
        )
    signal_strength_display.short_description = 'Signal Strength'
    signal_strength_display.admin_order_field = 'signal_strength'
    
    def rsi_display(self, obj):
        if obj.rsi_value is None:
            return '-'
        
        color = 'red' if obj.rsi_value >= 70 else 'green' if obj.rsi_value <= 30 else 'gray'
        return format_html(
            '<span style="color: {};">{:.1f}</span>',
            color, obj.rsi_value
        )
    rsi_display.short_description = 'RSI'
    rsi_display.admin_order_field = 'rsi_value'
    
    def trend_display(self, obj):
        color_map = {'uptrend': 'green', 'downtrend': 'red', 'sideways': 'gray'}
        color = color_map.get(obj.trend_direction, 'gray')
        strength = obj.trend_strength * 100
        
        return format_html(
            '<span style="color: {};">{} ({:.0f}%)</span>',
            color, obj.trend_direction.title(), strength
        )
    trend_display.short_description = 'Trend'
    trend_display.admin_order_field = 'trend_direction'
    
    def bb_position_display(self, obj):
        if obj.bb_position is None:
            return '-'
        
        if obj.bb_position <= 0.2:
            color = 'green'
            label = 'Lower'
        elif obj.bb_position >= 0.8:
            color = 'red'
            label = 'Upper'
        else:
            color = 'gray'
            label = 'Middle'
        
        return format_html(
            '<span style="color: {};">{}</span>',
            color, label
        )
    bb_position_display.short_description = 'BB Position'
    bb_position_display.admin_order_field = 'bb_position'
    
    fieldsets = (
        ('Analysis & Timeframe', {
            'fields': ('technical_analysis', 'timeframe', 'data_points')
        }),
        ('Moving Averages', {
            'fields': (
                ('sma_short', 'sma_long'),
                ('ema_short', 'ema_long')
            )
        }),
        ('Momentum Indicators', {
            'fields': (
                ('rsi_value', 'rsi_signal', 'rsi_strength'),
                ('is_oversold', 'is_overbought')
            )
        }),
        ('MACD', {
            'fields': (
                ('macd_line', 'macd_signal_line', 'macd_histogram'),
                ('macd_signal', 'macd_strength', 'macd_bullish_crossover')
            )
        }),
        ('Bollinger Bands', {
            'fields': (
                ('bb_upper', 'bb_middle', 'bb_lower'),
                ('bb_position', 'bb_signal', 'bb_strength', 'bb_squeeze')
            )
        }),
        ('Volume Analysis', {
            'fields': (
                ('obv_value', 'volume_sma'),
                ('volume_signal', 'volume_strength')
            )
        }),
        ('OSRS Indicators', {
            'fields': (
                ('osrs_momentum', 'flip_probability', 'flip_confidence')
            )
        }),
        ('Trend Analysis', {
            'fields': (
                ('trend_direction', 'trend_strength', 'trend_duration')
            )
        }),
        ('Support/Resistance', {
            'fields': ('support_levels', 'resistance_levels'),
            'classes': ('collapse',)
        }),
        ('Overall Signal', {
            'fields': ('overall_signal', 'signal_strength')
        })
    )
    
    actions = ['update_signals', 'export_indicators']
    
    def update_signals(self, request, queryset):
        """Update signals for selected indicators."""
        count = queryset.count()
        self.message_user(
            request,
            f'Signal update would process {count} indicators.'
        )
    update_signals.short_description = "Update signals"
    
    def export_indicators(self, request, queryset):
        """Export indicator data for analysis."""
        count = queryset.count()
        self.message_user(
            request,
            f'Export would process {count} indicators.'
        )
    export_indicators.short_description = "Export indicator data"


@admin.register(TechnicalSignal)
class TechnicalSignalAdmin(admin.ModelAdmin):
    list_display = [
        'analysis_item', 'signal_type', 'direction', 'strength_confidence_display',
        'entry_price', 'quality_indicator', 'execution_status', 'performance_display',
        'signal_timestamp'
    ]
    list_filter = [
        'signal_type', 'direction', 'is_active', 'is_executed', 'signal_timestamp'
    ]
    search_fields = ['technical_analysis__item__name', 'signal_reasoning']
    readonly_fields = [
        'signal_timestamp', 'is_high_quality', 'expected_return', 'risk_amount',
        'current_pnl', 'max_pnl', 'min_pnl'
    ]
    
    def analysis_item(self, obj):
        return obj.technical_analysis.item.name
    analysis_item.short_description = 'Item'
    analysis_item.admin_order_field = 'technical_analysis__item__name'
    
    def strength_confidence_display(self, obj):
        strength_pct = obj.strength * 100
        confidence_pct = obj.confidence * 100
        
        # Color based on average of strength and confidence
        avg = (obj.strength + obj.confidence) / 2
        color = 'green' if avg >= 0.7 else 'orange' if avg >= 0.5 else 'red'
        
        return format_html(
            '<span style="color: {};">S:{:.0f}% C:{:.0f}%</span>',
            color, strength_pct, confidence_pct
        )
    strength_confidence_display.short_description = 'S/C'
    
    def quality_indicator(self, obj):
        if obj.is_high_quality:
            return format_html('<span style="color: green; font-weight: bold;">●</span> High')
        return format_html('<span style="color: orange;">○</span> Normal')
    quality_indicator.short_description = 'Quality'
    
    def execution_status(self, obj):
        if obj.is_executed:
            return format_html('<span style="color: blue;">●</span> Executed')
        elif obj.is_active:
            return format_html('<span style="color: green;">●</span> Active')
        else:
            return format_html('<span style="color: gray;">○</span> Inactive')
    execution_status.short_description = 'Status'
    
    def performance_display(self, obj):
        if not obj.is_executed:
            return '-'
        
        pnl = obj.current_pnl
        color = 'green' if pnl > 0 else 'red' if pnl < 0 else 'gray'
        
        return format_html(
            '<span style="color: {};">{:+.1f}%</span>',
            color, pnl
        )
    performance_display.short_description = 'P&L'
    performance_display.admin_order_field = 'current_pnl'
    
    fieldsets = (
        ('Signal Details', {
            'fields': (
                ('technical_analysis', 'signal_timestamp'),
                ('signal_type', 'direction'),
                ('strength', 'confidence', 'is_high_quality')
            )
        }),
        ('Price Targets', {
            'fields': (
                ('entry_price', 'stop_loss_price', 'take_profit_price'),
                ('expected_return', 'risk_amount')
            )
        }),
        ('Risk Management', {
            'fields': (
                ('position_size_pct', 'risk_reward_ratio'),
                ('max_hold_time_hours',)
            )
        }),
        ('Signal Basis', {
            'fields': (
                'primary_indicators',
                'supporting_timeframes',
                'signal_reasoning'
            ),
            'classes': ('collapse',)
        }),
        ('Execution', {
            'fields': (
                ('is_active', 'is_executed'),
                ('execution_timestamp', 'execution_price')
            )
        }),
        ('Performance Tracking', {
            'fields': (
                ('current_pnl', 'max_pnl', 'min_pnl')
            )
        })
    )
    
    actions = ['activate_signals', 'deactivate_signals', 'execute_signals', 'update_performance']
    
    def activate_signals(self, request, queryset):
        """Activate selected signals."""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f'Activated {count} signals.'
        )
    activate_signals.short_description = "Activate signals"
    
    def deactivate_signals(self, request, queryset):
        """Deactivate selected signals."""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f'Deactivated {count} signals.'
        )
    deactivate_signals.short_description = "Deactivate signals"
    
    def execute_signals(self, request, queryset):
        """Mark selected signals as executed."""
        count = 0
        for signal in queryset.filter(is_active=True, is_executed=False):
            signal.is_executed = True
            signal.execution_price = signal.entry_price
            signal.save()
            count += 1
        
        self.message_user(
            request,
            f'Executed {count} signals.'
        )
    execute_signals.short_description = "Execute signals"
    
    def update_performance(self, request, queryset):
        """Update performance for executed signals."""
        count = queryset.filter(is_executed=True).count()
        self.message_user(
            request,
            f'Performance update would process {count} executed signals.'
        )
    update_performance.short_description = "Update performance"


@admin.register(SeasonalPattern)
class SeasonalPatternAdmin(admin.ModelAdmin):
    list_display = [
        'item_name', 'overall_strength_display', 'dominant_pattern', 'best_month',
        'weekend_effect_display', 'forecast_confidence_display', 'analysis_timestamp', 'strong_patterns_indicator'
    ]
    list_filter = ['best_month', 'worst_month', 'analysis_timestamp', 'best_day_of_week']
    search_fields = ['item__name']
    readonly_fields = [
        'analysis_timestamp', 'has_strong_patterns', 'dominant_pattern_type',
        'has_significant_weekend_effect', 'analysis_duration_seconds'
    ]
    
    def item_name(self, obj):
        return obj.item.name
    item_name.short_description = 'Item'
    item_name.admin_order_field = 'item__name'
    
    def overall_strength_display(self, obj):
        strength = obj.overall_pattern_strength
        color = 'green' if strength >= 0.6 else 'orange' if strength >= 0.3 else 'red'
        return format_html(
            '<span style="color: {};">{:.1%}</span>',
            color, strength
        )
    overall_strength_display.short_description = 'Overall Strength'
    overall_strength_display.admin_order_field = 'overall_pattern_strength'
    
    def dominant_pattern(self, obj):
        return obj.dominant_pattern_type.replace('_', ' ').title()
    dominant_pattern.short_description = 'Dominant Pattern'
    
    def weekend_effect_display(self, obj):
        effect = obj.weekend_effect_pct
        if abs(effect) < 1:
            return format_html('<span style="color: gray;">Minimal</span>')
        color = 'green' if effect > 0 else 'red'
        return format_html(
            '<span style="color: {};">{:+.1f}%</span>',
            color, effect
        )
    weekend_effect_display.short_description = 'Weekend Effect'
    weekend_effect_display.admin_order_field = 'weekend_effect_pct'
    
    def forecast_confidence_display(self, obj):
        confidence = obj.forecast_confidence
        color = 'green' if confidence >= 0.7 else 'orange' if confidence >= 0.5 else 'red'
        return format_html(
            '<span style="color: {};">{:.1%}</span>',
            color, confidence
        )
    forecast_confidence_display.short_description = 'Forecast Confidence'
    forecast_confidence_display.admin_order_field = 'forecast_confidence'
    
    def strong_patterns_indicator(self, obj):
        if obj.has_strong_patterns:
            return format_html('<span style="color: green; font-weight: bold;">●</span> Strong')
        return format_html('<span style="color: orange;">○</span> Weak')
    strong_patterns_indicator.short_description = 'Pattern Strength'
    
    fieldsets = (
        ('Item & Timing', {
            'fields': ('item', 'analysis_timestamp', 'analysis_duration_seconds')
        }),
        ('Analysis Parameters', {
            'fields': ('lookback_days', 'data_points_analyzed', 'analysis_types')
        }),
        ('Pattern Strengths', {
            'fields': (
                ('weekly_pattern_strength', 'monthly_pattern_strength'),
                ('yearly_pattern_strength', 'event_pattern_strength'),
                ('overall_pattern_strength', 'has_strong_patterns')
            )
        }),
        ('Weekly Patterns', {
            'fields': (
                ('weekend_effect_pct', 'has_significant_weekend_effect'),
                ('best_day_of_week', 'worst_day_of_week'),
                ('day_of_week_effects',)
            )
        }),
        ('Monthly & Seasonal Patterns', {
            'fields': (
                ('best_month', 'worst_month'),
                ('monthly_effects', 'quarterly_effects'),
                ('dominant_pattern_type',)
            )
        }),
        ('Events & Forecasting', {
            'fields': (
                ('detected_events', 'event_impact_analysis'),
                ('short_term_forecast', 'medium_term_forecast'),
                ('forecast_confidence',)
            )
        }),
        ('Recommendations', {
            'fields': ('recommendations',),
            'classes': ('collapse',)
        }),
        ('Analysis Quality', {
            'fields': ('confidence_score',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['regenerate_patterns', 'update_forecasts', 'export_patterns']
    
    def regenerate_patterns(self, request, queryset):
        """Regenerate seasonal patterns for selected items."""
        count = queryset.count()
        self.message_user(
            request,
            f'Pattern regeneration would process {count} seasonal analyses.'
        )
    regenerate_patterns.short_description = "Regenerate seasonal patterns"
    
    def update_forecasts(self, request, queryset):
        """Update forecasts for selected patterns."""
        count = queryset.count()
        self.message_user(
            request,
            f'Forecast update would process {count} patterns.'
        )
    update_forecasts.short_description = "Update forecasts"
    
    def export_patterns(self, request, queryset):
        """Export seasonal pattern data."""
        count = queryset.count()
        self.message_user(
            request,
            f'Export would process {count} seasonal patterns.'
        )
    export_patterns.short_description = "Export pattern data"


@admin.register(SeasonalForecast)
class SeasonalForecastAdmin(admin.ModelAdmin):
    list_display = [
        'pattern_item', 'horizon', 'target_date', 'forecasted_price', 'confidence_display',
        'accuracy_display', 'validation_status', 'days_until_target_display', 'forecast_timestamp'
    ]
    list_filter = ['horizon', 'primary_pattern_type', 'is_within_confidence_interval', 'forecast_timestamp']
    search_fields = ['seasonal_pattern__item__name']
    readonly_fields = [
        'forecast_timestamp', 'is_validated', 'days_until_target', 'forecast_accuracy',
        'validation_date'
    ]
    
    def pattern_item(self, obj):
        return obj.seasonal_pattern.item.name
    pattern_item.short_description = 'Item'
    pattern_item.admin_order_field = 'seasonal_pattern__item__name'
    
    def confidence_display(self, obj):
        confidence = obj.confidence_level * 100
        color = 'green' if confidence >= 90 else 'orange' if confidence >= 80 else 'red'
        return format_html(
            '<span style="color: {};">{:.0f}%</span>',
            color, confidence
        )
    confidence_display.short_description = 'Confidence'
    confidence_display.admin_order_field = 'confidence_level'
    
    def accuracy_display(self, obj):
        if not obj.is_validated:
            return format_html('<span style="color: gray;">Pending</span>')
        
        accuracy = obj.forecast_accuracy
        if accuracy is None:
            return format_html('<span style="color: gray;">N/A</span>')
        
        color = 'green' if accuracy >= 85 else 'orange' if accuracy >= 70 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, accuracy
        )
    accuracy_display.short_description = 'Accuracy'
    
    def validation_status(self, obj):
        if not obj.is_validated:
            return format_html('<span style="color: orange;">Pending</span>')
        elif obj.is_within_confidence_interval:
            return format_html('<span style="color: green;">●</span> Within CI')
        else:
            return format_html('<span style="color: red;">○</span> Outside CI')
    validation_status.short_description = 'Validation'
    
    def days_until_target_display(self, obj):
        days = obj.days_until_target
        if days is None:
            return '-'
        elif days < 0:
            return format_html('<span style="color: red;">{} days ago</span>', abs(days))
        elif days == 0:
            return format_html('<span style="color: orange;">Today</span>')
        else:
            return format_html('<span style="color: blue;">In {} days</span>', days)
    days_until_target_display.short_description = 'Target Date'
    
    fieldsets = (
        ('Forecast Details', {
            'fields': (
                ('seasonal_pattern', 'forecast_timestamp'),
                ('horizon', 'target_date', 'days_until_target')
            )
        }),
        ('Forecasted Values', {
            'fields': (
                ('forecasted_price', 'confidence_level'),
                ('lower_bound', 'upper_bound')
            )
        }),
        ('Forecast Components', {
            'fields': (
                ('base_price', 'seasonal_factor', 'trend_adjustment'),
                ('primary_pattern_type', 'pattern_strength'),
                ('forecast_method',)
            )
        }),
        ('Validation Results', {
            'fields': (
                ('actual_price', 'forecast_error'),
                ('is_within_confidence_interval', 'validation_date'),
                ('absolute_error', 'percentage_error', 'forecast_accuracy')
            )
        })
    )
    
    actions = ['validate_forecasts', 'export_forecasts', 'recalculate_accuracy']
    
    def validate_forecasts(self, request, queryset):
        """Validate selected forecasts against actual prices."""
        count = queryset.filter(actual_price__isnull=True).count()
        self.message_user(
            request,
            f'Validation would process {count} unvalidated forecasts.'
        )
    validate_forecasts.short_description = "Validate against actual prices"
    
    def export_forecasts(self, request, queryset):
        """Export forecast data for analysis."""
        count = queryset.count()
        self.message_user(
            request,
            f'Export would process {count} forecasts.'
        )
    export_forecasts.short_description = "Export forecast data"
    
    def recalculate_accuracy(self, request, queryset):
        """Recalculate accuracy metrics for validated forecasts."""
        count = queryset.filter(actual_price__isnull=False).count()
        self.message_user(
            request,
            f'Accuracy recalculation would process {count} validated forecasts.'
        )
    recalculate_accuracy.short_description = "Recalculate accuracy metrics"


@admin.register(SeasonalEvent)
class SeasonalEventAdmin(admin.ModelAdmin):
    list_display = [
        'event_name', 'event_type', 'impact_display', 'recurrence_display',
        'upcoming_status', 'verification_status', 'duration_days', 'detection_timestamp'
    ]
    list_filter = ['event_type', 'is_recurring', 'recurrence_pattern', 'verification_status', 'is_active']
    search_fields = ['event_name', 'description']
    readonly_fields = [
        'detection_timestamp', 'last_updated', 'is_upcoming', 'is_current',
        'has_significant_impact'
    ]
    
    def impact_display(self, obj):
        price_impact = abs(obj.average_price_impact_pct)
        volume_impact = abs(obj.average_volume_impact_pct)
        
        if obj.has_significant_impact:
            color = 'red' if price_impact >= 10 else 'orange'
            return format_html(
                '<span style="color: {};">P:{:+.1f}% V:{:+.1f}%</span>',
                color, obj.average_price_impact_pct, obj.average_volume_impact_pct
            )
        else:
            return format_html(
                '<span style="color: gray;">P:{:+.1f}% V:{:+.1f}%</span>',
                obj.average_price_impact_pct, obj.average_volume_impact_pct
            )
    impact_display.short_description = 'Price/Volume Impact'
    
    def recurrence_display(self, obj):
        if not obj.is_recurring:
            return format_html('<span style="color: gray;">One-time</span>')
        
        pattern = obj.recurrence_pattern.replace('_', ' ').title()
        return format_html('<span style="color: blue;">{}</span>', pattern)
    recurrence_display.short_description = 'Recurrence'
    recurrence_display.admin_order_field = 'recurrence_pattern'
    
    def upcoming_status(self, obj):
        if obj.is_current:
            return format_html('<span style="color: green; font-weight: bold;">●</span> Active')
        elif obj.is_upcoming:
            return format_html('<span style="color: orange;">●</span> Upcoming')
        else:
            return format_html('<span style="color: gray;">○</span> Not Scheduled')
    upcoming_status.short_description = 'Status'
    
    fieldsets = (
        ('Event Information', {
            'fields': (
                ('event_name', 'event_type'),
                ('description',),
                ('is_active', 'verification_status')
            )
        }),
        ('Event Timing', {
            'fields': (
                ('start_date', 'end_date', 'duration_days'),
                ('is_recurring', 'recurrence_pattern'),
                ('is_upcoming', 'is_current')
            )
        }),
        ('Impact Analysis', {
            'fields': (
                ('average_price_impact_pct', 'average_volume_impact_pct'),
                ('impact_confidence', 'has_significant_impact'),
                ('affected_categories',)
            )
        }),
        ('Historical Data', {
            'fields': ('historical_occurrences',),
            'classes': ('collapse',)
        }),
        ('Detection Metadata', {
            'fields': (
                ('detection_method', 'detection_timestamp', 'last_updated')
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = ['predict_next_occurrence', 'verify_events', 'update_impact_data']
    
    def predict_next_occurrence(self, request, queryset):
        """Predict next occurrence for recurring events."""
        recurring_events = queryset.filter(is_recurring=True)
        count = recurring_events.count()
        self.message_user(
            request,
            f'Next occurrence prediction would process {count} recurring events.'
        )
    predict_next_occurrence.short_description = "Predict next occurrence"
    
    def verify_events(self, request, queryset):
        """Mark selected events as verified."""
        count = queryset.update(verification_status='verified')
        self.message_user(
            request,
            f'Marked {count} events as verified.'
        )
    verify_events.short_description = "Mark as verified"
    
    def update_impact_data(self, request, queryset):
        """Update impact data for selected events."""
        count = queryset.count()
        self.message_user(
            request,
            f'Impact data update would process {count} events.'
        )
    update_impact_data.short_description = "Update impact data"


@admin.register(SeasonalRecommendation)
class SeasonalRecommendationAdmin(admin.ModelAdmin):
    list_display = [
        'pattern_item', 'recommendation_type', 'confidence_display', 'validity_period',
        'performance_display', 'execution_status', 'days_remaining_display', 'recommendation_timestamp'
    ]
    list_filter = ['recommendation_type', 'is_active', 'is_executed', 'primary_pattern', 'recommendation_timestamp']
    search_fields = ['seasonal_pattern__item__name', 'recommendation_text']
    readonly_fields = [
        'recommendation_timestamp', 'is_current', 'days_remaining',
        'is_high_confidence', 'current_performance_pct', 'max_performance_pct', 'min_performance_pct'
    ]
    
    def pattern_item(self, obj):
        return obj.seasonal_pattern.item.name
    pattern_item.short_description = 'Item'
    pattern_item.admin_order_field = 'seasonal_pattern__item__name'
    
    def confidence_display(self, obj):
        confidence = obj.confidence_score
        color = 'green' if confidence >= 0.8 else 'orange' if confidence >= 0.6 else 'red'
        icon = '●' if obj.is_high_confidence else '○'
        
        return format_html(
            '<span style="color: {};"><strong>{}</strong> {:.1%}</span>',
            color, icon, confidence
        )
    confidence_display.short_description = 'Confidence'
    confidence_display.admin_order_field = 'confidence_score'
    
    def validity_period(self, obj):
        valid_from = obj.valid_from.strftime('%m/%d')
        valid_until = obj.valid_until.strftime('%m/%d')
        
        if obj.is_current:
            return format_html('<span style="color: green;">{} - {} (Active)</span>', valid_from, valid_until)
        else:
            return f"{valid_from} - {valid_until}"
    validity_period.short_description = 'Valid Period'
    
    def performance_display(self, obj):
        if not obj.is_executed:
            expected = obj.expected_impact_pct
            color = 'green' if expected > 0 else 'red'
            return format_html(
                '<span style="color: {};">Expected: {:+.1f}%</span>',
                color, expected
            )
        
        current = obj.current_performance_pct
        color = 'green' if current > 0 else 'red' if current < 0 else 'gray'
        return format_html(
            '<span style="color: {};">Actual: {:+.1f}%</span>',
            color, current
        )
    performance_display.short_description = 'Performance'
    performance_display.admin_order_field = 'current_performance_pct'
    
    def execution_status(self, obj):
        if obj.is_executed:
            return format_html('<span style="color: blue;">●</span> Executed')
        elif obj.is_active and obj.is_current:
            return format_html('<span style="color: green;">●</span> Active')
        elif obj.is_active:
            return format_html('<span style="color: orange;">●</span> Pending')
        else:
            return format_html('<span style="color: gray;">○</span> Inactive')
    execution_status.short_description = 'Status'
    
    def days_remaining_display(self, obj):
        days = obj.days_remaining
        if days <= 0:
            return format_html('<span style="color: red;">Expired</span>')
        elif days <= 3:
            return format_html('<span style="color: orange;">{} days</span>', days)
        else:
            return format_html('<span style="color: green;">{} days</span>', days)
    days_remaining_display.short_description = 'Days Left'
    
    fieldsets = (
        ('Recommendation Details', {
            'fields': (
                ('seasonal_pattern', 'recommendation_timestamp'),
                ('recommendation_type', 'primary_pattern'),
                ('confidence_score', 'is_high_confidence')
            )
        }),
        ('Timing & Validity', {
            'fields': (
                ('target_date', 'valid_from', 'valid_until'),
                ('is_current', 'days_remaining')
            )
        }),
        ('Expected Impact', {
            'fields': (
                ('expected_impact_pct', 'suggested_position_size_pct'),
                ('stop_loss_pct', 'take_profit_pct'),
                ('max_hold_days',)
            )
        }),
        ('Recommendation Reasoning', {
            'fields': (
                ('recommendation_text',),
                ('supporting_factors',)
            )
        }),
        ('Execution Tracking', {
            'fields': (
                ('is_active', 'is_executed'),
                ('execution_timestamp', 'execution_price')
            )
        }),
        ('Performance Tracking', {
            'fields': (
                ('current_performance_pct', 'max_performance_pct', 'min_performance_pct'),
                ('final_performance_pct',)
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = ['activate_recommendations', 'execute_recommendations', 'close_recommendations']
    
    def activate_recommendations(self, request, queryset):
        """Activate selected recommendations."""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f'Activated {count} recommendations.'
        )
    activate_recommendations.short_description = "Activate recommendations"
    
    def execute_recommendations(self, request, queryset):
        """Mark selected recommendations as executed."""
        count = 0
        for rec in queryset.filter(is_active=True, is_executed=False):
            rec.is_executed = True
            rec.execution_timestamp = timezone.now()
            # You would set execution_price from current market price
            rec.save()
            count += 1
        
        self.message_user(
            request,
            f'Executed {count} recommendations.'
        )
    execute_recommendations.short_description = "Execute recommendations"
    
    def close_recommendations(self, request, queryset):
        """Close selected recommendations."""
        count = 0
        for rec in queryset.filter(is_active=True):
            # You would call rec.close_recommendation(final_price) with current market price
            rec.is_active = False
            rec.save()
            count += 1
        
        self.message_user(
            request,
            f'Closed {count} recommendations.'
        )
    close_recommendations.short_description = "Close recommendations"


# Customize admin site headers
admin.site.site_header = "OSRS Trading Terminal Admin"
admin.site.site_title = "Trading Terminal"
admin.site.index_title = "Real-Time Market Engine Administration"