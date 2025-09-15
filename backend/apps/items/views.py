"""
API views for OSRS High Alch Tracker.
"""

import logging
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page, never_cache
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Item
from .serializers import (
    ItemListSerializer, ItemDetailSerializer, SearchResponseSerializer,
    ProfitRecommendationsSerializer, SearchResultSerializer
)
from services.search_service import HybridSearchService
from services.ai_service import SyncOpenRouterAIService

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API results."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@method_decorator(never_cache, name='dispatch')
class ItemListView(generics.ListAPIView):
    """
    List items with optional filtering.
    
    Query parameters:
    - search: Text search in name/examine
    - members: Filter by members items (true/false)
    - min_profit: Minimum profit per item
    - max_price: Maximum GE buy price
    - ordering: Sort by field (profit, profit_margin, name, high_alch)
    """
    
    serializer_class = ItemListSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = Item.objects.filter(is_active=True).select_related('profit_calc')
        
        # Text search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(examine__icontains=search)
            )
        
        # Members filter
        members = self.request.query_params.get('members')
        if members is not None:
            queryset = queryset.filter(members=members.lower() == 'true')
        
        # Profit filters
        min_profit = self.request.query_params.get('min_profit')
        if min_profit:
            try:
                queryset = queryset.filter(profit_calc__current_profit__gte=int(min_profit))
            except ValueError:
                pass
        
        max_price = self.request.query_params.get('max_price')
        if max_price:
            try:
                queryset = queryset.filter(profit_calc__current_buy_price__lte=int(max_price))
            except ValueError:
                pass
        
        # Ordering
        ordering = self.request.query_params.get('ordering', '-profit_calc__current_profit')
        valid_orderings = [
            'profit_calc__current_profit', '-profit_calc__current_profit',
            'profit_calc__current_profit_margin', '-profit_calc__current_profit_margin',
            'name', '-name', 'high_alch', '-high_alch'
        ]
        
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-profit_calc__current_profit')
        
        return queryset

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class ItemDetailView(generics.RetrieveAPIView):
    """Get detailed information about a specific item."""
    
    serializer_class = ItemDetailSerializer
    lookup_field = 'item_id'
    
    def get_queryset(self):
        return Item.objects.filter(is_active=True).select_related('profit_calc').prefetch_related(
            'categories__category', 'price_snapshots'
        )

    @method_decorator(cache_page(60 * 2))  # Cache for 2 minutes
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


@api_view(['GET'])
def search_items(request):
    """
    Hybrid search endpoint combining semantic search with profit ranking.
    
    Query parameters:
    - q: Search query (required)
    - limit: Max results (default: 20, max: 50)
    - min_profit: Minimum profit per item
    - max_price: Maximum GE buy price
    - members_only: Filter by members items (true/false)
    - semantic_weight: Weight for semantic similarity (0-1, default: 0.6)
    - profit_weight: Weight for profit ranking (0-1, default: 0.4)
    - use_ai: Enable AI insights (true/false, default: true)
    """
    try:
        query = request.query_params.get('q', '').strip()
        
        # Parse parameters
        limit = min(int(request.query_params.get('limit', 20)), 50)
        min_profit = request.query_params.get('min_profit')
        max_price = request.query_params.get('max_price')
        members_only = request.query_params.get('members_only')
        semantic_weight = float(request.query_params.get('semantic_weight', 0.6))
        profit_weight = float(request.query_params.get('profit_weight', 0.4))
        use_ai = request.query_params.get('use_ai', 'true').lower() == 'true'
        
        # Convert string parameters to appropriate types
        if min_profit:
            min_profit = int(min_profit)
        if max_price:
            max_price = int(max_price)
        if members_only is not None:
            members_only = members_only.lower() == 'true'
        
        # Perform search
        search_service = HybridSearchService()
        results = search_service.search_items(
            query=query,
            limit=limit,
            min_profit=min_profit or 0,
            max_price=max_price,
            members_only=members_only,
            semantic_weight=semantic_weight,
            profit_weight=profit_weight,
            use_ai_enhancement=use_ai
        )
        
        # Serialize and return
        serializer = SearchResponseSerializer(results)
        return Response(serializer.data)
        
    except ValueError as e:
        return Response(
            {'error': f'Invalid parameter: {e}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return Response(
            {'error': 'Search failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_similar_items(request, item_id):
    """
    Get items similar to the specified item using semantic similarity.
    
    Path parameters:
    - item_id: ID of the reference item
    
    Query parameters:
    - limit: Max results (default: 10, max: 20)
    - threshold: Minimum similarity threshold (default: 0.3)
    """
    try:
        limit = min(int(request.query_params.get('limit', 10)), 20)
        threshold = float(request.query_params.get('threshold', 0.3))
        
        search_service = HybridSearchService()
        similar_items = search_service.get_similar_items(
            item_id=item_id,
            limit=limit,
            similarity_threshold=threshold
        )
        
        return Response({
            'item_id': item_id,
            'similar_items': similar_items,
            'total_found': len(similar_items)
        })
        
    except ValueError as e:
        return Response(
            {'error': f'Invalid parameter: {e}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Similar items search failed: {e}")
        return Response(
            {'error': 'Similar items search failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@cache_page(60 * 10)  # Cache for 10 minutes
def get_profit_recommendations(request):
    """
    Get AI-powered profit recommendations.
    
    Query parameters:
    - limit: Max results (default: 20, max: 50)
    - min_profit_margin: Minimum profit margin % (default: 5.0)
    - max_risk: Maximum risk level (low/medium/high, default: medium)
    """
    try:
        limit = min(int(request.query_params.get('limit', 20)), 50)
        min_profit_margin = float(request.query_params.get('min_profit_margin', 5.0))
        max_risk_level = request.query_params.get('max_risk', 'medium')
        
        if max_risk_level not in ['low', 'medium', 'high']:
            max_risk_level = 'medium'
        
        search_service = HybridSearchService()
        recommendations = search_service.get_profit_recommendations(
            limit=limit,
            min_profit_margin=min_profit_margin,
            max_risk_level=max_risk_level
        )
        
        serializer = ProfitRecommendationsSerializer(recommendations)
        return Response(serializer.data)
        
    except ValueError as e:
        return Response(
            {'error': f'Invalid parameter: {e}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Profit recommendations failed: {e}")
        return Response(
            {'error': 'Recommendations failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def analyze_item(request, item_id):
    """
    Get AI analysis of a specific item's profitability.
    
    Path parameters:
    - item_id: ID of the item to analyze
    
    Request body (optional):
    - context: Additional context for analysis
    """
    try:
        # Get item
        try:
            item = Item.objects.select_related('profit_calc').get(
                item_id=item_id, is_active=True
            )
        except Item.DoesNotExist:
            return Response(
                {'error': 'Item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prepare item and price data
        profit_calc = getattr(item, 'profit_calc', None)
        
        item_data = {
            'name': item.name,
            'examine': item.examine,
            'high_alch': item.high_alch,
            'limit': item.limit,
            'members': item.members
        }
        
        price_data = {
            'current_buy_price': profit_calc.current_buy_price if profit_calc else 0,
            'current_profit': profit_calc.current_profit if profit_calc else 0,
            'current_profit_margin': profit_calc.current_profit_margin if profit_calc else 0.0,
            'daily_volume': profit_calc.daily_volume if profit_calc else 0
        }
        
        # Get context from request
        context = request.data.get('context', '') if hasattr(request, 'data') else ''
        
        # Generate AI analysis
        ai_service = SyncOpenRouterAIService()
        analysis = ai_service.analyze_item_profitability(
            item_data=item_data,
            price_data=price_data,
            context=context
        )
        
        return Response({
            'item': item_data,
            'price_data': price_data,
            'ai_analysis': analysis,
            'analyzed_at': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Item analysis failed: {e}")
        return Response(
            {'error': 'Analysis failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def api_health_check(request):
    """Health check endpoint for the API services."""
    try:
        # Test database connection
        item_count = Item.objects.count()
        
        # Test search service
        search_service = HybridSearchService()
        
        # Test AI service
        ai_service = SyncOpenRouterAIService()
        ai_healthy = ai_service.health_check()
        
        return Response({
            'status': 'healthy',
            'database': {'items_count': item_count},
            'ai_service': {'healthy': ai_healthy},
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response(
            {'status': 'unhealthy', 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def price_verification_debug(request, item_id):
    """
    Debug endpoint to compare our stored prices with live RuneScape Wiki API data.
    
    This endpoint helps verify pricing accuracy and detect data issues.
    
    Path parameters:
    - item_id: ID of the item to verify
    """
    try:
        # Get item from our database
        try:
            item = Item.objects.select_related('profit_calc').get(
                item_id=item_id, is_active=True
            )
        except Item.DoesNotExist:
            return Response(
                {'error': 'Item not found in our database'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Import here to avoid circular imports
        from services.api_client import RuneScapeWikiClient
        from services.multi_source_price_client import MultiSourcePriceClient
        import asyncio
        
        # Fetch data from multiple sources for comprehensive analysis
        async def fetch_multi_source_data():
            results = {}
            
            # Get multi-source intelligence data
            async with MultiSourcePriceClient() as multi_client:
                results['multi_source'] = await multi_client.get_best_price_data(item_id)
                results['source_status'] = await multi_client.get_data_source_status()
            
            # Also get raw wiki data for comparison
            async with RuneScapeWikiClient() as wiki_client:
                results['wiki_raw'] = await wiki_client.get_latest_prices(item_id=item_id)
                results['wiki_fresh'] = await wiki_client.get_freshest_price_data(item_id)
            
            return results
        
        # Run async fetch
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            multi_data = loop.run_until_complete(fetch_multi_source_data())
            loop.close()
        except Exception as e:
            logger.error(f"Failed to fetch multi-source data: {e}")
            return Response(
                {'error': f'Failed to fetch multi-source data: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Extract multi-source intelligence data
        multi_source_data = multi_data.get('multi_source')
        wiki_raw_data = multi_data.get('wiki_raw', {}).get('data', {}).get(str(item_id), {})
        wiki_fresh_data = multi_data.get('wiki_fresh', {}).get('data', {}).get(str(item_id), {})
        source_status = multi_data.get('source_status', {})
        
        if not multi_source_data and not wiki_raw_data:
            return Response({
                'item_id': item_id,
                'item_name': item.name,
                'error': 'No price data available from any source for this item',
                'source_status': source_status
            })
        
        # Get our stored prices
        profit_calc = getattr(item, 'profit_calc', None)
        our_buy_price = profit_calc.current_buy_price if profit_calc else 0
        our_sell_price = profit_calc.current_sell_price if profit_calc else 0
        our_profit = profit_calc.current_profit if profit_calc else 0
        
        # Multi-source intelligence data
        best_price_data = multi_source_data
        best_buy_price = best_price_data.low_price if best_price_data else 0
        best_sell_price = best_price_data.high_price if best_price_data else 0
        
        # Wiki raw data for comparison
        wiki_raw_buy = wiki_raw_data.get('low', 0)
        wiki_raw_sell = wiki_raw_data.get('high', 0)
        wiki_raw_high_time = wiki_raw_data.get('highTime', 0)
        wiki_raw_low_time = wiki_raw_data.get('lowTime', 0)
        
        # Wiki fresh data (from timeseries)
        wiki_fresh_buy = wiki_fresh_data.get('low', 0) if wiki_fresh_data else 0
        wiki_fresh_sell = wiki_fresh_data.get('high', 0) if wiki_fresh_data else 0
        
        # Calculate what the profit SHOULD be with best available prices
        nature_rune_cost = 180
        correct_profit_multi = item.high_alch - best_buy_price - nature_rune_cost if best_price_data else 0
        correct_profit_wiki = item.high_alch - wiki_raw_buy - nature_rune_cost if wiki_raw_buy > 0 else 0
        
        # Price comparison analysis
        buy_price_diff_multi = abs(our_buy_price - best_buy_price) if best_buy_price > 0 else 0
        sell_price_diff_multi = abs(our_sell_price - best_sell_price) if best_sell_price > 0 else 0
        profit_diff_multi = abs(our_profit - correct_profit_multi) if best_price_data else 0
        
        # Freshness analysis
        current_time = timezone.now().timestamp()
        wiki_high_age = (current_time - wiki_raw_high_time) / 3600 if wiki_raw_high_time > 0 else float('inf')
        wiki_low_age = (current_time - wiki_raw_low_time) / 3600 if wiki_raw_low_time > 0 else float('inf')
        
        # Data quality assessment with rejection logic
        data_quality_assessment = _assess_data_quality(
            best_price_data, wiki_raw_data, wiki_fresh_data, source_status
        )
        
        return Response({
            'item_info': {
                'id': item_id,
                'name': item.name,
                'high_alch': item.high_alch,
                'examine': item.examine[:100] + '...' if len(item.examine) > 100 else item.examine
            },
            'our_stored_data': {
                'buy_price': our_buy_price,
                'sell_price': our_sell_price,
                'profit': our_profit,
                'has_profit_calc': profit_calc is not None,
                'last_updated': profit_calc.last_updated.isoformat() if profit_calc and profit_calc.last_updated else None
            },
            'multi_source_intelligence': {
                'recommended_buy_price': best_buy_price,
                'recommended_sell_price': best_sell_price,
                'recommended_profit': correct_profit_multi,
                'data_source': best_price_data.source.value if best_price_data else 'none',
                'data_quality': best_price_data.quality.value if best_price_data else 'unknown',
                'confidence_score': best_price_data.confidence_score if best_price_data else 0,
                'age_hours': best_price_data.age_hours if best_price_data else float('inf'),
                'volume_high': best_price_data.volume_high if best_price_data else 0,
                'volume_low': best_price_data.volume_low if best_price_data else 0
            },
            'wiki_raw_data': {
                'instant_sell_price': wiki_raw_sell,
                'instant_buy_price': wiki_raw_buy,
                'high_time': wiki_raw_high_time,
                'low_time': wiki_raw_low_time,
                'high_age_hours': round(wiki_high_age, 2) if wiki_high_age != float('inf') else 'never',
                'low_age_hours': round(wiki_low_age, 2) if wiki_low_age != float('inf') else 'never'
            },
            'wiki_fresh_data': {
                'instant_sell_price': wiki_fresh_sell,
                'instant_buy_price': wiki_fresh_buy,
                'source': wiki_fresh_data.get('source', 'none') if wiki_fresh_data else 'none'
            },
            'price_accuracy_analysis': {
                'buy_price_difference_multi': buy_price_diff_multi,
                'sell_price_difference_multi': sell_price_diff_multi,
                'profit_difference_multi': profit_diff_multi,
                'accuracy_multi': {
                    'buy_price_accurate': buy_price_diff_multi < (best_buy_price * 0.05) if best_buy_price > 0 else False,
                    'sell_price_accurate': sell_price_diff_multi < (best_sell_price * 0.05) if best_sell_price > 0 else False,
                    'profit_accurate': profit_diff_multi < 100 if best_price_data else False
                }
            },
            'data_quality_assessment': data_quality_assessment,
            'source_status': source_status,
            'freshness_recommendations': {
                'should_reject_stale_data': data_quality_assessment.get('reject_stale', False),
                'recommended_action': data_quality_assessment.get('recommended_action', 'none'),
                'data_reliability': data_quality_assessment.get('reliability_score', 0),
                'needs_immediate_update': data_quality_assessment.get('needs_update', False)
            }
        })
        
    except ValueError as e:
        return Response(
            {'error': f'Invalid item ID: {e}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Price verification failed for item {item_id}: {e}")
        return Response(
            {'error': f'Price verification failed: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _assess_data_quality(multi_source_data, wiki_raw_data, wiki_fresh_data, source_status):
    """
    Comprehensive data quality assessment with freshness detection and rejection logic.
    
    Args:
        multi_source_data: PriceData from multi-source intelligence
        wiki_raw_data: Raw wiki API data
        wiki_fresh_data: Fresh wiki timeseries data  
        source_status: Status of all data sources
        
    Returns:
        Dictionary with quality assessment and recommendations
    """
    current_time = timezone.now().timestamp()
    
    # Initialize assessment
    assessment = {
        'overall_quality': 'unknown',
        'reliability_score': 0.0,
        'reject_stale': False,
        'needs_update': False,
        'recommended_action': 'none',
        'quality_issues': [],
        'source_analysis': {}
    }
    
    # Assess multi-source intelligence data
    if multi_source_data:
        age_hours = multi_source_data.age_hours
        quality = multi_source_data.quality.value
        confidence = multi_source_data.confidence_score
        source = multi_source_data.source.value
        
        assessment['source_analysis']['multi_source'] = {
            'age_hours': age_hours,
            'quality': quality,
            'confidence': confidence,
            'source': source,
            'acceptable': age_hours < 48 and confidence > 0.3
        }
        
        # Freshness rejection logic
        if age_hours > 72:  # Reject data older than 72 hours
            assessment['reject_stale'] = True
            assessment['quality_issues'].append(f"Multi-source data is {age_hours:.1f} hours old (>72h threshold)")
        
        if confidence < 0.2:  # Reject very low confidence data
            assessment['reject_stale'] = True
            assessment['quality_issues'].append(f"Multi-source confidence too low: {confidence:.2f}")
        
        # Calculate base reliability score
        age_penalty = min(age_hours / 48, 1.0)  # Normalize to 48 hours
        assessment['reliability_score'] = max(0, confidence - age_penalty * 0.5)
        
        # Determine overall quality
        if age_hours < 1 and confidence > 0.7:
            assessment['overall_quality'] = 'excellent'
        elif age_hours < 6 and confidence > 0.5:
            assessment['overall_quality'] = 'good'
        elif age_hours < 24 and confidence > 0.3:
            assessment['overall_quality'] = 'acceptable'
        elif age_hours < 72:
            assessment['overall_quality'] = 'poor'
        else:
            assessment['overall_quality'] = 'unacceptable'
    
    # Assess wiki raw data
    if wiki_raw_data:
        high_time = wiki_raw_data.get('highTime', 0)
        low_time = wiki_raw_data.get('lowTime', 0)
        high_age = (current_time - high_time) / 3600 if high_time > 0 else float('inf')
        low_age = (current_time - low_time) / 3600 if low_time > 0 else float('inf')
        
        assessment['source_analysis']['wiki_raw'] = {
            'high_age_hours': high_age,
            'low_age_hours': low_age,
            'has_recent_data': high_age < 24 or low_age < 24,
            'acceptable': high_age < 48 and low_age < 48
        }
        
        # Check for extremely stale wiki data
        if high_age > 168 or low_age > 168:  # 1 week old
            assessment['quality_issues'].append(f"Wiki raw data extremely stale: high={high_age:.1f}h, low={low_age:.1f}h")
    
    # Assess source status
    healthy_sources = 0
    total_sources = 0
    
    for source_name, status_info in source_status.items():
        total_sources += 1
        if status_info.get('healthy', False):
            healthy_sources += 1
        else:
            assessment['quality_issues'].append(f"Source {source_name} unhealthy: {status_info.get('error', 'unknown error')}")
    
    source_health_ratio = healthy_sources / total_sources if total_sources > 0 else 0
    assessment['source_analysis']['health_ratio'] = source_health_ratio
    
    # Determine recommended actions
    if assessment['reject_stale']:
        assessment['recommended_action'] = 'reject_and_refetch'
        assessment['needs_update'] = True
    elif assessment['overall_quality'] in ['poor', 'unacceptable']:
        assessment['recommended_action'] = 'fetch_fresh_data'
        assessment['needs_update'] = True
    elif source_health_ratio < 0.5:
        assessment['recommended_action'] = 'check_source_health'
        assessment['needs_update'] = True
    elif assessment['reliability_score'] < 0.4:
        assessment['recommended_action'] = 'verify_accuracy'
        assessment['needs_update'] = False
    else:
        assessment['recommended_action'] = 'data_acceptable'
        assessment['needs_update'] = False
    
    # Add summary
    assessment['summary'] = {
        'total_issues': len(assessment['quality_issues']),
        'data_usable': not assessment['reject_stale'] and assessment['reliability_score'] > 0.3,
        'confidence_level': 'high' if assessment['reliability_score'] > 0.7 else 
                           'medium' if assessment['reliability_score'] > 0.5 else 'low',
        'freshness_status': 'fresh' if assessment.get('source_analysis', {}).get('multi_source', {}).get('age_hours', 999) < 6 else
                           'recent' if assessment.get('source_analysis', {}).get('multi_source', {}).get('age_hours', 999) < 24 else
                           'stale'
    }
    
    return assessment
