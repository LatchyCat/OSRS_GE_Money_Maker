"""
API views for merchant trading features and AI agent.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import json

from apps.items.models import Item
from apps.prices.models import ProfitCalculation
from apps.prices.merchant_models import MarketTrend, MerchantOpportunity, MerchantAlert
from services.merchant_ai_agent import MerchantAIAgent
from services.market_analysis_service import MarketAnalysisService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class MerchantAIChatView(View):
    """
    API endpoint for conversational AI merchant assistant.
    """
    
    def __init__(self):
        super().__init__()
        self.ai_agent = MerchantAIAgent()
    
    async def post(self, request):
        """Process merchant AI chat query."""
        try:
            # Parse request data
            data = json.loads(request.body)
            query = data.get('query', '').strip()
            user_id = data.get('user_id', 'anonymous')
            include_context = data.get('include_context', True)
            
            if not query:
                return JsonResponse({
                    'error': 'Query is required',
                    'response': 'Please ask me something about OSRS merchant trading!'
                }, status=400)
            
            # Process query with AI agent
            result = await self.ai_agent.process_query(
                query=query,
                user_id=user_id,
                include_context=include_context
            )
            
            # Add suggested follow-up questions
            if not result.get('error'):
                suggestions = await self.ai_agent.suggest_follow_up_questions(
                    query, result.get('query_type', 'general'), result
                )
                result['suggested_questions'] = suggestions
            
            return JsonResponse(result)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON in request body',
                'response': 'Please check your request format.'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in merchant AI chat: {e}")
            return JsonResponse({
                'error': 'Internal server error',
                'response': 'I encountered an error while processing your query. Please try again.'
            }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_market_opportunities(request):
    """Get current merchant opportunities."""
    try:
        # Parse query parameters
        risk_levels = request.GET.get('risk_levels', 'conservative,moderate').split(',')
        min_profit = int(request.GET.get('min_profit', 100))
        max_results = int(request.GET.get('limit', 20))
        opportunity_types = request.GET.get('types', '').split(',') if request.GET.get('types') else None
        
        # Build query
        query = MerchantOpportunity.objects.filter(
            status='active',
            projected_profit_per_item__gte=min_profit
        ).select_related('item', 'based_on_trend')
        
        if risk_levels:
            query = query.filter(risk_level__in=risk_levels)
        
        if opportunity_types:
            query = query.filter(opportunity_type__in=opportunity_types)
        
        # Get opportunities ordered by score
        opportunities = list(query.order_by('-opportunity_score')[:max_results])
        
        # Serialize data
        data = []
        for opp in opportunities:
            item_data = {
                'id': opp.id,
                'item_name': opp.item.name,
                'item_id': opp.item.item_id,
                'opportunity_type': opp.opportunity_type,
                'risk_level': opp.risk_level,
                'current_price': opp.current_price,
                'target_buy_price': opp.target_buy_price,
                'target_sell_price': opp.target_sell_price,
                'projected_profit_per_item': opp.projected_profit_per_item,
                'projected_profit_margin_pct': opp.projected_profit_margin_pct,
                'total_projected_profit': opp.total_projected_profit,
                'estimated_trade_volume': opp.estimated_trade_volume,
                'opportunity_score': opp.opportunity_score,
                'confidence_score': opp.confidence_score,
                'success_probability': opp.success_probability,
                'time_sensitivity': opp.time_sensitivity,
                'reasoning': opp.reasoning,
                'created_at': opp.created_at.isoformat(),
                'expires_at': opp.expires_at.isoformat() if opp.expires_at else None,
            }
            
            # Add trend data if available
            if opp.based_on_trend:
                item_data['trend'] = {
                    'period_type': opp.based_on_trend.period_type,
                    'trend_direction': opp.based_on_trend.trend_direction,
                    'volatility_score': opp.based_on_trend.volatility_score,
                    'momentum_score': opp.based_on_trend.momentum_score,
                    'pattern_type': opp.based_on_trend.pattern_type,
                }
            
            data.append(item_data)
        
        return Response({
            'opportunities': data,
            'total': len(data),
            'filters': {
                'risk_levels': risk_levels,
                'min_profit': min_profit,
                'opportunity_types': opportunity_types,
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting market opportunities: {e}")
        return Response({
            'error': 'Failed to retrieve opportunities',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_market_trends(request):
    """Get market trend analysis for items."""
    try:
        # Parse parameters
        item_name = request.GET.get('item_name')
        period_type = request.GET.get('period', '24h')
        limit = int(request.GET.get('limit', 10))
        
        # Build query
        query = MarketTrend.objects.select_related('item')
        
        if item_name:
            query = query.filter(item__name__icontains=item_name)
        
        if period_type:
            query = query.filter(period_type=period_type)
        
        # Get recent trends
        trends = list(query.filter(
            calculated_at__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-calculated_at')[:limit])
        
        # Serialize data
        data = []
        for trend in trends:
            data.append({
                'item_name': trend.item.name,
                'item_id': trend.item.item_id,
                'period_type': trend.period_type,
                'trend_direction': trend.trend_direction,
                'volatility_score': trend.volatility_score,
                'momentum_score': trend.momentum_score,
                'volume_momentum': trend.volume_momentum,
                'price_current': trend.price_current,
                'price_min': trend.price_min,
                'price_max': trend.price_max,
                'price_avg': trend.price_avg,
                'support_level': trend.support_level,
                'resistance_level': trend.resistance_level,
                'pattern_type': trend.pattern_type,
                'pattern_confidence': trend.pattern_confidence,
                'calculated_at': trend.calculated_at.isoformat(),
                'price_range_pct': trend.price_range_pct,
                'is_volatile': trend.is_volatile,
                'is_trending': trend.is_trending,
            })
        
        return Response({
            'trends': data,
            'total': len(data),
            'filters': {
                'item_name': item_name,
                'period_type': period_type,
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting market trends: {e}")
        return Response({
            'error': 'Failed to retrieve trends',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_item_analysis(request, item_id):
    """Get detailed market analysis for a specific item."""
    try:
        # Get item
        try:
            item = Item.objects.select_related('profit_calc').get(item_id=item_id)
        except Item.DoesNotExist:
            return Response({
                'error': 'Item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get recent trends
        trends = list(MarketTrend.objects.filter(
            item=item,
            calculated_at__gte=timezone.now() - timedelta(days=7)
        ).order_by('period_type', '-calculated_at'))
        
        # Get recent opportunities
        opportunities = list(MerchantOpportunity.objects.filter(
            item=item,
            status='active'
        ).order_by('-opportunity_score')[:5])
        
        # Get recent price snapshots
        from apps.prices.models import PriceSnapshot
        price_history = list(PriceSnapshot.objects.filter(
            item=item
        ).order_by('-created_at')[:24])  # Last 24 snapshots
        
        # Build response data
        data = {
            'item': {
                'name': item.name,
                'item_id': item.item_id,
                'high_alch_value': item.high_alch,
                'examine_text': item.examine_text,
                'members_only': item.members,
            },
            'current_market': {
                'current_profit': getattr(item.profit_calc, 'current_profit', 0),
                'current_buy_price': getattr(item.profit_calc, 'current_buy_price', 0),
                'current_sell_price': getattr(item.profit_calc, 'current_sell_price', 0),
                'daily_volume': getattr(item.profit_calc, 'daily_volume', 0),
                'price_volatility': getattr(item.profit_calc, 'price_volatility', 0),
                'data_source': getattr(item.profit_calc, 'data_source', 'unknown'),
                'data_age_hours': getattr(item.profit_calc, 'data_age_hours', 0),
            },
            'trends': [],
            'opportunities': [],
            'price_history': [],
        }
        
        # Add trend data
        for trend in trends:
            data['trends'].append({
                'period_type': trend.period_type,
                'trend_direction': trend.trend_direction,
                'volatility_score': trend.volatility_score,
                'momentum_score': trend.momentum_score,
                'pattern_type': trend.pattern_type,
                'pattern_confidence': trend.pattern_confidence,
                'price_current': trend.price_current,
                'price_min': trend.price_min,
                'price_max': trend.price_max,
                'support_level': trend.support_level,
                'resistance_level': trend.resistance_level,
                'calculated_at': trend.calculated_at.isoformat(),
            })
        
        # Add opportunity data
        for opp in opportunities:
            data['opportunities'].append({
                'opportunity_type': opp.opportunity_type,
                'risk_level': opp.risk_level,
                'target_buy_price': opp.target_buy_price,
                'target_sell_price': opp.target_sell_price,
                'projected_profit_per_item': opp.projected_profit_per_item,
                'opportunity_score': opp.opportunity_score,
                'confidence_score': opp.confidence_score,
                'time_sensitivity': opp.time_sensitivity,
                'reasoning': opp.reasoning,
                'created_at': opp.created_at.isoformat(),
            })
        
        # Add price history
        for snapshot in price_history:
            data['price_history'].append({
                'high_price': snapshot.high_price,
                'low_price': snapshot.low_price,
                'total_volume': snapshot.total_volume,
                'created_at': snapshot.created_at.isoformat(),
            })
        
        return Response(data)
        
    except Exception as e:
        logger.error(f"Error getting item analysis: {e}")
        return Response({
            'error': 'Failed to retrieve item analysis',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def analyze_market_opportunities(request):
    """Trigger market analysis to identify new opportunities."""
    try:
        # Parse request data
        data = request.data if hasattr(request, 'data') else json.loads(request.body)
        risk_levels = data.get('risk_levels', ['conservative', 'moderate'])
        min_profit = data.get('min_profit', 100)
        max_results = data.get('max_results', 50)
        
        # Run market analysis
        market_service = MarketAnalysisService()
        
        # Use asyncio to run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            opportunities = loop.run_until_complete(
                market_service.identify_opportunities(
                    risk_levels=risk_levels,
                    min_profit=min_profit,
                    max_results=max_results
                )
            )
        finally:
            loop.close()
        
        # Format response
        opportunity_data = []
        for opp in opportunities:
            opportunity_data.append({
                'item_name': opp.item.name,
                'opportunity_type': opp.opportunity_type,
                'risk_level': opp.risk_level,
                'projected_profit': opp.projected_profit_per_item,
                'opportunity_score': opp.opportunity_score,
                'confidence': opp.confidence_score,
                'reasoning': opp.reasoning,
            })
        
        return Response({
            'message': f'Analysis complete: found {len(opportunities)} opportunities',
            'opportunities': opportunity_data,
            'analysis_time': datetime.now().isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Error analyzing market opportunities: {e}")
        return Response({
            'error': 'Market analysis failed',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_market_overview(request):
    """Get overall market overview and statistics."""
    try:
        # Get market statistics
        from django.db.models import Count, Avg, Max, Min
        
        # Opportunity statistics
        opportunity_stats = MerchantOpportunity.objects.filter(
            status='active'
        ).aggregate(
            total_opportunities=Count('id'),
            avg_opportunity_score=Avg('opportunity_score'),
            max_projected_profit=Max('projected_profit_per_item'),
            avg_projected_profit=Avg('projected_profit_per_item'),
        )
        
        # Risk distribution
        risk_distribution = list(
            MerchantOpportunity.objects.filter(status='active')
            .values('risk_level')
            .annotate(count=Count('id'))
            .order_by('risk_level')
        )
        
        # Opportunity type distribution
        type_distribution = list(
            MerchantOpportunity.objects.filter(status='active')
            .values('opportunity_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Recent trend analysis
        from django.db import models
        
        recent_trends = MarketTrend.objects.filter(
            calculated_at__gte=timezone.now() - timedelta(hours=24)
        ).aggregate(
            total_items_analyzed=Count('item', distinct=True),
            avg_volatility=Avg('volatility_score'),
            trending_up=Count('id', filter=models.Q(trend_direction__in=['strong_up', 'weak_up'])),
            trending_down=Count('id', filter=models.Q(trend_direction__in=['strong_down', 'weak_down'])),
        )
        
        # Build response
        data = {
            'market_overview': {
                'total_active_opportunities': opportunity_stats['total_opportunities'] or 0,
                'average_opportunity_score': round(opportunity_stats['avg_opportunity_score'] or 0, 1),
                'max_profit_opportunity': opportunity_stats['max_projected_profit'] or 0,
                'average_projected_profit': round(opportunity_stats['avg_projected_profit'] or 0),
                'items_analyzed_24h': recent_trends['total_items_analyzed'] or 0,
                'average_volatility': round(recent_trends['avg_volatility'] or 0, 3),
                'trending_up_count': recent_trends['trending_up'] or 0,
                'trending_down_count': recent_trends['trending_down'] or 0,
            },
            'risk_distribution': risk_distribution,
            'opportunity_types': type_distribution,
            'generated_at': datetime.now().isoformat(),
        }
        
        return Response(data)
        
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        return Response({
            'error': 'Failed to retrieve market overview',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)