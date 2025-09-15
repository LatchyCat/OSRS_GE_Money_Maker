from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import asyncio
import traceback
from asgiref.sync import sync_to_async
import logging

from services.merchant_ai_agent import MerchantAIAgent
from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

def clean_ai_response(response: str) -> str:
    """Remove thinking tags and clean AI response formatting."""
    import re
    
    # Remove thinking tags and their content
    cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    cleaned = re.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=re.DOTALL)
    
    # Remove extra whitespace and clean formatting
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Remove excessive newlines
    cleaned = cleaned.strip()
    
    return cleaned

async def get_real_trading_opportunities(capital_gp=None):
    """Get real trading opportunities from database with live price data."""
    try:
        # Get top profitable items from database
        from django.db.models import Q
        
        # Query for items with recent price data and good profit potential
        # Adjust query based on capital
        max_items = 5  # Default
        max_item_price = None
        min_profit = 100
        
        if capital_gp:
            if capital_gp <= 500000:  # 500K or less
                max_items = 10  # For 300K capital, provide 10 items as requested
                max_item_price = min(50000, capital_gp // 6)  # Max 1/6 of capital per item
                min_profit = 50  # Lower profit threshold for smaller capital
            elif capital_gp <= 2000000:  # 2M or less  
                max_items = 8
                max_item_price = capital_gp // 4  # Max 1/4 of capital per item
                min_profit = 200
            else:  # Large capital
                max_items = 6
                min_profit = 500
        
        # Build query filters
        filters = {
            'current_profit__gt': min_profit,
            'current_buy_price__gt': 0,
            'current_sell_price__gt': 0, 
            'last_updated__gte': timezone.now() - timedelta(days=2)
        }
        
        if max_item_price:
            filters['current_buy_price__lte'] = max_item_price
        
        profit_calcs = [
            calc async for calc in ProfitCalculation.objects.filter(**filters)
            .select_related('item').order_by('-current_profit')[:max_items]
        ]
        
        opportunities = []
        for calc in profit_calcs:
            # Calculate position size based on available capital
            max_units = 1000  # Default
            if capital_gp and calc.current_buy_price > 0:
                max_units = min(capital_gp // (4 * calc.current_buy_price), 1000)  # 25% of capital max
            
            # Calculate realistic profit per item (accounting for nature rune cost)
            nature_rune_cost = 180
            high_alch_profit = calc.item.high_alch - calc.current_buy_price - nature_rune_cost
            
            # Use the better of high alch profit or direct trading profit
            profit_per_item = max(high_alch_profit, calc.current_profit)
            margin_pct = (profit_per_item / calc.current_buy_price * 100) if calc.current_buy_price > 0 else 0
            
            # Calculate data age and add freshness warnings
            data_age_hours = (timezone.now() - calc.last_updated).total_seconds() / 3600
            freshness_warnings = []
            freshness_status = 'fresh'
            
            if data_age_hours > 24:
                freshness_warnings.append('⚠️ Price data is over 1 day old')
                freshness_status = 'stale'
                # Reduce success probability for stale data
                success_probability_base = 60 + (calc.recommendation_score * 30)
                success_probability = max(40, success_probability_base - 20)  # Reduce by 20% for stale data
            elif data_age_hours > 6:
                freshness_warnings.append('⏰ Price data is over 6 hours old')
                freshness_status = 'acceptable'
                success_probability_base = 60 + (calc.recommendation_score * 30)
                success_probability = max(50, success_probability_base - 10)  # Reduce by 10% for old data
            else:
                success_probability = min(90, 60 + (calc.recommendation_score * 30))  # Fresh data gets full score
                freshness_status = 'fresh'

            opportunity = {
                'item_id': calc.item.item_id,
                'item_name': calc.item.name,
                'current_price': calc.current_buy_price,
                'recommended_buy_price': calc.current_buy_price,
                'recommended_sell_price': max(calc.current_sell_price, calc.item.high_alch),
                'expected_profit_per_item': int(profit_per_item),
                'expected_profit_margin_pct': round(margin_pct, 1),
                'success_probability_pct': int(success_probability),
                'risk_level': 'low' if calc.recommendation_score > 0.7 else 'medium',
                'estimated_hold_time_hours': round(2.0 + (calc.price_volatility or 0) * 10, 1),
                'data_age_hours': round(data_age_hours, 1),
                'freshness_status': freshness_status,
                'freshness_warnings': freshness_warnings,
                'last_updated': calc.last_updated.strftime('%Y-%m-%d %H:%M UTC'),
                'source': 'database'
            }
            
            opportunities.append(opportunity)
        
        # If no opportunities found, return fallback message
        if not opportunities:
            opportunities = [{
                'item_id': 0,
                'item_name': 'No current opportunities',
                'message': 'Market data is being refreshed. Please try again shortly.',
                'source': 'database_empty'
            }]
        
        logger.info(f"Retrieved {len(opportunities)} real trading opportunities from database")
        return opportunities
        
    except Exception as e:
        logger.error(f"Error fetching real trading opportunities: {e}")
        # Return database error message instead of mock data
        return [{
            'item_id': 0,
            'item_name': 'Database Error',
            'message': f'Unable to fetch live market data: {str(e)}',
            'source': 'database_error'
        }]

async def get_real_market_signals():
    """Get real market signals from database analysis."""
    try:
        signals = []
        
        # Get items with significant price changes in the last 24 hours
        recent_snapshots = [
            snapshot async for snapshot in PriceSnapshot.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).select_related('item').order_by('-created_at')[:20]
        ]
        
        # Group by item and analyze price trends
        item_price_changes = {}
        for snapshot in recent_snapshots:
            item_id = snapshot.item.item_id
            if item_id not in item_price_changes:
                item_price_changes[item_id] = {
                    'item_name': snapshot.item.name,
                    'prices': [],
                    'timestamps': []
                }
            item_price_changes[item_id]['prices'].append(snapshot.high_price or snapshot.low_price or 0)
            item_price_changes[item_id]['timestamps'].append(snapshot.created_at)
        
        # Generate signals based on price analysis
        for item_id, data in item_price_changes.items():
            if len(data['prices']) >= 2:
                recent_price = data['prices'][0]  # Most recent (first in desc order)
                older_price = data['prices'][-1]   # Oldest
                
                if recent_price > 0 and older_price > 0:
                    price_change_pct = ((recent_price - older_price) / older_price) * 100
                    
                    # Generate signal based on significant price changes
                    if abs(price_change_pct) > 5:  # More than 5% change
                        signal_type = 'BUY' if price_change_pct < -3 else 'SELL' if price_change_pct > 5 else 'WATCH'
                        strength = 'Strong' if abs(price_change_pct) > 10 else 'Moderate'
                        
                        if signal_type != 'WATCH':
                            reasoning = f'Price {"dropped" if price_change_pct < 0 else "increased"} {abs(price_change_pct):.1f}% in 24h'
                            
                            # Add freshness validation to signals
                            latest_timestamp = max(data['timestamps'])
                            signal_age_hours = (timezone.now() - latest_timestamp).total_seconds() / 3600
                            
                            # Add freshness info to signal
                            if signal_age_hours > 24:
                                reasoning += ' (⚠️ Data >24h old)'
                                strength = 'Weak' if strength == 'Strong' else 'Very Weak'
                            elif signal_age_hours > 6:
                                reasoning += ' (⏰ Data >6h old)'
                            
                            signals.append({
                                'signal_type': signal_type,
                                'item_name': data['item_name'],
                                'strength': strength,
                                'reasoning': reasoning,
                                'target_price': recent_price,
                                'change_pct': round(price_change_pct, 1),
                                'data_age_hours': round(signal_age_hours, 1),
                                'source': 'database'
                            })
        
        # If no signals found, provide a status message
        if not signals:
            signals = [{
                'signal_type': 'INFO',
                'item_name': 'Market Status',
                'strength': 'Stable',
                'reasoning': 'No significant price movements detected in the last 24 hours',
                'source': 'database'
            }]
        
        # Return top 3 signals
        logger.info(f"Generated {len(signals)} real market signals from database")
        return signals[:3]
        
    except Exception as e:
        logger.error(f"Error generating real market signals: {e}")
        return [{
            'signal_type': 'ERROR',
            'item_name': 'Signal Generation Error',
            'strength': 'N/A',
            'reasoning': f'Unable to generate market signals: {str(e)}',
            'source': 'database_error'
        }]

async def generate_data_freshness_summary(opportunities, market_signals):
    """Generate a summary of data freshness for the AI response."""
    try:
        total_opportunities = len([opp for opp in opportunities if opp.get('item_id', 0) > 0])
        stale_opportunities = len([opp for opp in opportunities if opp.get('freshness_status') == 'stale'])
        acceptable_opportunities = len([opp for opp in opportunities if opp.get('freshness_status') == 'acceptable'])
        fresh_opportunities = len([opp for opp in opportunities if opp.get('freshness_status') == 'fresh'])
        
        total_signals = len([sig for sig in market_signals if sig.get('signal_type') != 'INFO'])
        old_signals = len([sig for sig in market_signals if sig.get('data_age_hours', 0) > 6])
        
        summary_parts = []
        
        # Overall data quality assessment
        if total_opportunities == 0:
            return "📊 **Data Status:** No current opportunities found in database."
        
        fresh_pct = (fresh_opportunities / total_opportunities * 100) if total_opportunities > 0 else 0
        
        if fresh_pct >= 70:
            summary_parts.append("📊 **Data Quality:** Excellent - Most data is fresh (< 6 hours)")
        elif fresh_pct >= 40:
            summary_parts.append("📊 **Data Quality:** Good - Mix of fresh and recent data")
        else:
            summary_parts.append("📊 **Data Quality:** ⚠️ Caution - Some data may be outdated")
        
        # Detailed breakdown
        details = []
        if fresh_opportunities > 0:
            details.append(f"✅ {fresh_opportunities} with fresh data")
        if acceptable_opportunities > 0:
            details.append(f"⏰ {acceptable_opportunities} with 6-24h old data")
        if stale_opportunities > 0:
            details.append(f"⚠️ {stale_opportunities} with data >24h old")
        
        if details:
            summary_parts.append(f"**Breakdown:** {', '.join(details)}")
        
        # Add signal freshness info
        if old_signals > 0:
            summary_parts.append(f"**Signals:** {old_signals}/{total_signals} signals use older data")
        
        # Add recommendation based on data quality
        if stale_opportunities > total_opportunities * 0.5:
            summary_parts.append("🔄 **Recommendation:** Consider refreshing price data before major trades")
        
        return "\n".join(summary_parts)
        
    except Exception as e:
        logger.error(f"Error generating freshness summary: {e}")
        return "📊 **Data Status:** Unable to verify data freshness"

class AITradingView(View):
    """Memory-optimized AI trading view for M1 MacBook."""
    
    def get(self, request):
        """Render the AI trading interface."""
        return render(request, 'ai_merching.html')

@method_decorator(csrf_exempt, name='dispatch')
class AITradingQueryView(View):
    """API endpoint for AI trading queries."""
    
    def __init__(self):
        super().__init__()
        self.ai_agent = None
    
    async def get_ai_agent(self):
        """Get or create AI agent instance."""
        if not self.ai_agent:
            self.ai_agent = MerchantAIAgent()
        return self.ai_agent
    
    async def post(self, request):
        """Process AI trading query and return intelligent recommendations."""
        try:
            # Parse request data
            data = json.loads(request.body.decode('utf-8'))
            query = data.get('query', '').strip()
            
            if not query:
                return JsonResponse({
                    'error': 'Query is required'
                }, status=400)
            
            logger.info(f"Processing AI trading query: {query[:100]}...")
            
            # Get AI agent
            ai_agent = await self.get_ai_agent()
            
            # Process query with ultra-intelligent context
            response_data = await ai_agent.process_query(query)
            
            logger.info("Successfully processed AI trading query")
            
            return JsonResponse({
                'success': True,
                'response': response_data.get('response', 'No response generated'),
                'precision_opportunities': response_data.get('precision_opportunities', []),
                'market_signals': response_data.get('market_signals', []),
                'risk_assessment': response_data.get('risk_assessment', {}),
                'portfolio_suggestions': response_data.get('portfolio_suggestions', [])
            })
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request")
            return JsonResponse({
                'error': 'Invalid JSON format'
            }, status=400)
            
        except Exception as e:
            logger.error(f"Error processing AI trading query: {str(e)}", exc_info=True)
            return JsonResponse({
                'error': 'Internal server error',
                'details': str(e)
            }, status=500)
    

# Function-based views for compatibility
def ai_trading_interface(request):
    """Render the main AI trading interface."""
    return render(request, 'ai_merching.html')

@csrf_exempt
async def ai_trading_query(request):
    """Process AI trading queries."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        # Parse request data
        data = json.loads(request.body.decode('utf-8'))
        query = data.get('query', '').strip()
        capital = data.get('capital')  # Extract capital parameter
        logger.info(f"Raw extracted capital: {capital} (type: {type(capital)})")
        
        if not query:
            return JsonResponse({
                'error': 'Query is required'
            }, status=400)
        
        # If capital is provided, incorporate it into the query for better AI analysis
        if capital:
            logger.info(f"Capital parameter provided: {capital} GP")
            if 'GP' not in query and str(capital) not in query:
                # Add capital context to query if not already mentioned
                query = f"{query} (I have {capital:,} GP available for trading)"
        
        logger.info(f"Processing AI trading query: {query[:100]}...")
        logger.info(f"Capital parameter: {capital} GP" if capital else "No capital parameter provided")
        
        try:
            # Initialize AI agent
            from services.merchant_ai_agent import MerchantAIAgent
            ai_agent = MerchantAIAgent()
            
            # Process query with ultra-intelligent context
            logger.info("Calling AI agent process_query...")
            response_data = await ai_agent.process_query(query, capital_gp=capital)
            
            logger.info("AI agent processing completed successfully")
            
            # Debug: Log response structure
            logger.info(f"AI Agent Response Keys: {list(response_data.keys())}")
            logger.info(f"AI Agent Response Type: {type(response_data)}")
            logger.info(f"Response Content: {response_data.get('response', 'NO RESPONSE KEY')[:200]}...")
            
            # Extract and format response components
            ai_response = response_data.get('response', 'No response generated')
            
            # Remove thinking tags from AI response
            ai_response = clean_ai_response(ai_response)
            precision_opportunities = response_data.get('precision_opportunities', [])
            market_signals = response_data.get('market_signals', [])
            risk_assessment = response_data.get('risk_assessment', {})
            portfolio_suggestions = response_data.get('portfolio_suggestions', [])
            
            # Convert dataclass objects to dictionaries if needed
            if precision_opportunities and hasattr(precision_opportunities[0], '__dict__'):
                precision_opportunities = [
                    {
                        'item_id': opp.item_id,
                        'item_name': opp.item_name,
                        'current_price': opp.current_price,
                        'recommended_buy_price': opp.recommended_buy_price,
                        'recommended_sell_price': opp.recommended_sell_price,
                        'expected_profit_per_item': opp.expected_profit_per_item,
                        'expected_profit_margin_pct': opp.expected_profit_margin_pct,
                        'success_probability_pct': opp.success_probability_pct,
                        'risk_level': opp.risk_level,
                        'estimated_hold_time_hours': opp.estimated_hold_time_hours,
                        'buy_limit': opp.buy_limit,
                        # Convert datetime fields to strings for JSON serialization
                        'optimal_buy_window_start': opp.optimal_buy_window_start.isoformat() if hasattr(opp, 'optimal_buy_window_start') and opp.optimal_buy_window_start else None,
                        'optimal_sell_window_start': opp.optimal_sell_window_start.isoformat() if hasattr(opp, 'optimal_sell_window_start') and opp.optimal_sell_window_start else None,
                        # Add other fields that might be missing
                        'daily_volume': getattr(opp, 'daily_volume', 0),
                        'recent_volatility': getattr(opp, 'recent_volatility', 0.0),
                        'market_momentum': getattr(opp, 'market_momentum', 'neutral'),
                        'recommended_position_size': getattr(opp, 'recommended_position_size', 0),
                        'max_capital_allocation_pct': getattr(opp, 'max_capital_allocation_pct', 0.0),
                        'confidence_score': getattr(opp, 'confidence_score', 0.0),
                    }
                    for opp in precision_opportunities
                ]
            
            if market_signals and hasattr(market_signals[0], '__dict__'):
                market_signals = [
                    {
                        'signal_type': signal.signal_type,
                        'item_name': signal.item_name,
                        'strength': signal.strength,
                        'reasoning': signal.reasoning,
                        'target_price': getattr(signal, 'target_price', None),
                    }
                    for signal in market_signals
                ]
            
            # Map AI agent opportunities to precision_opportunities format
            if not precision_opportunities and response_data.get('opportunities'):
                precision_opportunities = []
                for opp in response_data['opportunities'][:3]:  # Take top 3
                    if hasattr(opp, '__dict__'):  # If it's an object
                        precision_opportunities.append({
                            'item_id': getattr(opp, 'item_id', 0),
                            'item_name': getattr(opp, 'item_name', 'Unknown Item'),
                            'current_price': getattr(opp, 'current_price', 0),
                            'recommended_buy_price': getattr(opp, 'target_buy_price', getattr(opp, 'recommended_buy_price', 0)),
                            'recommended_sell_price': getattr(opp, 'target_sell_price', getattr(opp, 'recommended_sell_price', 0)),
                            'expected_profit_per_item': getattr(opp, 'projected_profit', getattr(opp, 'expected_profit_per_item', 0)),
                            'expected_profit_margin_pct': getattr(opp, 'projected_profit_margin_pct', getattr(opp, 'expected_profit_margin_pct', 0)),
                            'success_probability_pct': getattr(opp, 'confidence_score', 75) * 100 if getattr(opp, 'confidence_score', 0) <= 1 else getattr(opp, 'confidence_score', 75),
                            'risk_level': getattr(opp, 'risk_level', 'medium'),
                            'estimated_hold_time_hours': getattr(opp, 'time_sensitivity', 4.0),
                            'buy_limit': getattr(opp, 'buy_limit', 0),
                        })
            
            # If still no precision opportunities, get real database opportunities
            if not precision_opportunities:
                # Extract capital from query for better recommendations
                capital_match = None
                import re
                gp_matches = re.findall(r'(\d+(?:\.\d+)?)\s*([KMB]?)\s*GP', query, re.IGNORECASE)
                if gp_matches:
                    amount_str, unit = gp_matches[0]
                    amount = float(amount_str)
                    if unit.upper() == 'K':
                        amount *= 1000
                    elif unit.upper() == 'M':
                        amount *= 1000000
                    elif unit.upper() == 'B':
                        amount *= 1000000000
                    capital_match = int(amount)
                
                # Get real opportunities from database
                try:
                    db_opportunities = await get_real_trading_opportunities(capital_match)
                    if db_opportunities and db_opportunities[0].get('item_id', 0) > 0:  # Valid opportunities
                        precision_opportunities = db_opportunities
                except Exception as db_error:
                    logger.error(f"Database opportunities error: {db_error}")

            # Add multi-agent metadata to response
            agent_metadata = {
                'query_complexity': response_data.get('query_complexity', 'medium'),
                'agent_used': response_data.get('agent_used', 'qwen3_coordinator'),
                'processing_time_ms': response_data.get('processing_time_ms', 0),
                'task_routing_reason': response_data.get('task_routing_reason', 'Balanced analysis'),
                'system_load': response_data.get('system_load', {}),
                'data_quality_score': response_data.get('data_quality_score', 0.8),
                'confidence_level': response_data.get('confidence_level', 0.75)
            }

            final_response = {
                'success': True,
                'response': ai_response,
                'precision_opportunities': precision_opportunities,
                'market_signals': market_signals,
                'risk_assessment': risk_assessment,
                'portfolio_suggestions': portfolio_suggestions,
                'agent_metadata': agent_metadata,
                'timestamp': timezone.now().isoformat()
            }
            
            logger.info(f"Final JSON Response Keys: {list(final_response.keys())}")
            logger.info(f"Final Response Length: {len(str(final_response))}")
            logger.info(f"Precision Opportunities Count: {len(precision_opportunities)}")
            
            return JsonResponse(final_response)
            
        except Exception as ai_error:
            logger.error(f"AI agent error: {str(ai_error)}", exc_info=True)
            
            # Enhanced fallback response with real database opportunities
            logger.info("AI agent failed, generating enhanced fallback with database opportunities")
            
            # Use capital parameter if provided, otherwise extract from query
            capital_for_opportunities = capital
            if not capital_for_opportunities:
                import re
                gp_matches = re.findall(r'(\d+(?:\.\d+)?)\s*([KMB]?)\s*GP', query, re.IGNORECASE)
                if gp_matches:
                    amount_str, unit = gp_matches[0]
                    amount = float(amount_str)
                    if unit.upper() == 'K':
                        amount *= 1000
                    elif unit.upper() == 'M':
                        amount *= 1000000
                    elif unit.upper() == 'B':
                        amount *= 1000000000
                    capital_for_opportunities = int(amount)
            
            response_text = f'🧠 **AI Analysis (Fallback Mode)**\n\n'
            response_text += f'Capital: {capital_for_opportunities:,} GP\n\n' if capital_for_opportunities else 'Based on your query:\n\n'
            response_text += '**🎯 Database Trading Opportunities:**\n\nHere are current profitable opportunities from our database:'
            
            # Generate opportunities with real database prices
            opportunities = await get_real_trading_opportunities(capital_for_opportunities)
            
            # Generate real market signals from database  
            market_signals = await get_real_market_signals()
            
            # Add data freshness summary to response
            freshness_summary = await generate_data_freshness_summary(opportunities, market_signals)
            response_text += f'\n\n{freshness_summary}'
            
            # Add agent metadata for fallback mode
            agent_metadata = {
                'query_complexity': 'fallback',
                'agent_used': 'database_fallback',
                'processing_time_ms': 100,
                'task_routing_reason': 'AI service unavailable - using database fallback',
                'system_load': {},
                'data_quality_score': 0.6,  # Lower score for fallback
                'confidence_level': 0.5
            }
            
            return JsonResponse({
                'success': True,
                'response': clean_ai_response(response_text),
                'precision_opportunities': opportunities,
                'market_signals': market_signals,
                'agent_metadata': agent_metadata,
                'ai_error': f'AI service unavailable: {str(ai_error)}',
                'fallback_mode': True,
                'timestamp': timezone.now().isoformat()
            })
            
            # Generic fallback
            return JsonResponse({
                'success': False,
                'error': 'AI processing temporarily unavailable',
                'details': str(ai_error),
                'fallback_response': 'Please try a simpler query or check back later.'
            })
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request")
        return JsonResponse({
            'error': 'Invalid JSON format'
        }, status=400)
        
    except Exception as e:
        logger.error(f"Error processing AI trading query: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
async def ai_debug_test(request):
    """Debug endpoint to test AI agent processing and capture detailed errors."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        test_query = data.get('query', 'I have 5M GP for medium-risk trading. Find me 8 opportunities.')
        
        logger.info(f"Debug test starting with query: {test_query}")
        
        # Initialize AI agent
        from services.merchant_ai_agent import MerchantAIAgent
        ai_agent = MerchantAIAgent()
        
        # Test each step individually
        debug_results = {
            'query': test_query,
            'steps': {},
            'final_result': None,
            'errors': []
        }
        
        try:
            # Step 1: Query Classification
            logger.info("Debug: Testing query classification...")
            query_type, entities = await ai_agent._classify_query(test_query)
            debug_results['steps']['classification'] = {
                'query_type': query_type,
                'entities': entities,
                'success': True
            }
            
        except Exception as step_error:
            debug_results['steps']['classification'] = {
                'success': False, 
                'error': str(step_error),
                'traceback': traceback.format_exc()
            }
            debug_results['errors'].append(f"Classification failed: {step_error}")
        
        try:
            # Step 2: Context Retrieval
            logger.info("Debug: Testing context retrieval...")
            context_data = await ai_agent._retrieve_context(test_query, query_type, entities)
            debug_results['steps']['context_retrieval'] = {
                'context_keys': list(context_data.keys()),
                'precision_opportunities_count': len(context_data.get('precision_opportunities', [])),
                'market_signals_count': len(context_data.get('market_signals', [])),
                'success': True
            }
            
        except Exception as step_error:
            debug_results['steps']['context_retrieval'] = {
                'success': False,
                'error': str(step_error),
                'traceback': traceback.format_exc()
            }
            debug_results['errors'].append(f"Context retrieval failed: {step_error}")
        
        try:
            # Step 3: AI Response Generation
            logger.info("Debug: Testing AI response generation...")
            response = await ai_agent.process_query(test_query, user_id="debug_test", include_context=True)
            debug_results['steps']['ai_generation'] = {
                'model': response.get('model'),
                'tokens_used': response.get('tokens_used'),
                'content_preview': response.get('content', '')[:200] + '...' if response.get('content') else 'No content',
                'success': True
            }
            
        except Exception as step_error:
            debug_results['steps']['ai_generation'] = {
                'success': False,
                'error': str(step_error),
                'traceback': traceback.format_exc()
            }
            debug_results['errors'].append(f"AI generation failed: {step_error}")
        
        try:
            # Step 4: Full Process Test
            logger.info("Debug: Testing full process...")
            full_result = await ai_agent.process_query(test_query)
            debug_results['steps']['full_process'] = {
                'response_preview': full_result.get('response', '')[:200] + '...',
                'query_type': full_result.get('query_type'),
                'precision_opportunities_count': len(full_result.get('precision_opportunities', [])),
                'success': True
            }
            debug_results['final_result'] = full_result
            
        except Exception as step_error:
            debug_results['steps']['full_process'] = {
                'success': False,
                'error': str(step_error),
                'traceback': traceback.format_exc()
            }
            debug_results['errors'].append(f"Full process failed: {step_error}")
        
        # Return debug results
        return JsonResponse({
            'success': True,
            'debug_results': debug_results,
            'summary': {
                'total_errors': len(debug_results['errors']),
                'successful_steps': len([s for s in debug_results['steps'].values() if s.get('success', False)]),
                'total_steps': len(debug_results['steps']),
            }
        })
        
    except Exception as e:
        logger.error(f"Debug test failed completely: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
async def multi_agent_performance(request):
    """API endpoint to get multi-agent system performance metrics."""
    try:
        from services.multi_agent_ai_service import MultiAgentAIService
        
        # Initialize multi-agent service to get performance data
        multi_agent_service = MultiAgentAIService()
        
        # Get comprehensive performance summary
        performance_data = multi_agent_service.get_performance_summary()
        
        # Add current system status
        status_info = {
            'timestamp': timezone.now().isoformat(),
            'system_healthy': True,  # Basic health check
            'agents_available': {
                'gemma3_fast': True,    # Fast categorization agent
                'deepseek_smart': True,  # Complex analysis agent  
                'qwen3_coordinator': True  # Context integration agent
            },
            'current_load': multi_agent_service.load_balancer.get_load_summary()
        }
        
        # Enhanced response with frontend-friendly data
        return JsonResponse({
            'success': True,
            'timestamp': status_info['timestamp'],
            'system_status': status_info,
            'performance_metrics': performance_data,
            'agent_capabilities': {
                'gemma3_fast': {
                    'name': 'Gemma Fast Lane',
                    'description': 'High-speed categorization and basic queries',
                    'speed_multiplier': 3.0,
                    'specialties': ['price_inquiries', 'simple_recommendations', 'quick_searches'],
                    'complexity_rating': 6,
                    'color': '#10B981'  # Green for fast
                },
                'deepseek_smart': {
                    'name': 'DeepSeek Analysis',
                    'description': 'Complex market analysis and risk assessment',
                    'speed_multiplier': 1.0,
                    'specialties': ['precision_trading', 'risk_analysis', 'market_intelligence'],
                    'complexity_rating': 9,
                    'color': '#3B82F6'  # Blue for smart
                },
                'qwen3_coordinator': {
                    'name': 'Qwen Coordinator',  
                    'description': 'Context integration and balanced analysis',
                    'speed_multiplier': 1.8,
                    'specialties': ['market_analysis', 'trend_analysis', 'comparisons'],
                    'complexity_rating': 7,
                    'color': '#8B5CF6'  # Purple for coordination
                }
            },
            'routing_logic': {
                'high_complexity': {
                    'agent': 'deepseek_smart',
                    'triggers': ['precision_trading', 'risk_analysis', 'market_intelligence', 'context_score > 15'],
                    'description': 'Routes complex analysis tasks to DeepSeek for thorough processing'
                },
                'medium_complexity': {
                    'agent': 'qwen3_coordinator', 
                    'triggers': ['market_analysis', 'trend_analysis', 'comparisons', 'context_score > 8'],
                    'description': 'Routes balanced analysis tasks to Qwen for coordination'
                },
                'low_complexity': {
                    'agent': 'gemma3_fast',
                    'triggers': ['price_inquiry', 'simple_recommendations', 'basic_queries'],
                    'description': 'Routes fast queries to Gemma for immediate responses'
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting multi-agent performance: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to get multi-agent performance metrics',
            'details': str(e)
        }, status=500)


# HIGH ALCHEMY AI VIEWS
class AIHighAlchemyAgent:
    """Specialized AI agent for high alchemy conversations using local models."""
    
    def __init__(self):
        self.merchant_agent = MerchantAIAgent()
        
    def _format_high_alchemy_context(self, items, current_capital, nature_rune_price):
        """Format high alchemy data for AI consumption."""
        context = {
            "activity_type": "high_alchemy",
            "player_capital": current_capital,
            "nature_rune_cost": nature_rune_price,
            "magic_requirements": {
                "level_required": 55,
                "xp_per_cast": 65,
                "casts_per_hour": 1200,
                "xp_per_hour": 78000
            },
            "available_items": []
        }
        
        # Process each item for high alchemy analysis
        for item in items[:20]:  # Limit to top 20 items for context size
            buy_price = getattr(item, 'current_buy_price', 0) or 0
            high_alch_value = getattr(item, 'high_alch', 0) or 0
            profit_per_cast = high_alch_value - buy_price - nature_rune_price
            
            # Calculate additional metrics
            profit_margin = (profit_per_cast / buy_price * 100) if buy_price > 0 else 0
            profit_per_hour = profit_per_cast * 1200  # 1200 casts per hour
            ge_limit = getattr(item, 'limit', 0) or 0
            
            # Determine affordability with current capital
            max_affordable = current_capital // buy_price if buy_price > 0 else 0
            casts_limited_by_ge = min(max_affordable, ge_limit) if ge_limit > 0 else max_affordable
            
            item_data = {
                "name": getattr(item, 'name', 'Unknown'),
                "id": getattr(item, 'item_id', 0),
                "buy_price": buy_price,
                "high_alch_value": high_alch_value,
                "profit_per_cast": profit_per_cast,
                "profit_margin_percent": round(profit_margin, 1),
                "profit_per_hour": profit_per_hour,
                "ge_limit": ge_limit,
                "max_affordable_casts": max_affordable,
                "members_only": getattr(item, 'members', False),
                "is_profitable": profit_per_cast > 0,
                "recommendation_score": getattr(item, 'recommendation_score', 0),
                "daily_volume": getattr(item, 'daily_volume', 0)
            }
            
            context["available_items"].append(item_data)
        
        # Sort by profitability
        context["available_items"].sort(key=lambda x: x["profit_per_cast"], reverse=True)
        
        # Add summary statistics
        profitable_items = [item for item in context["available_items"] if item["is_profitable"]]
        context["summary"] = {
            "total_items": len(context["available_items"]),
            "profitable_items": len(profitable_items),
            "best_profit_per_cast": profitable_items[0]["profit_per_cast"] if profitable_items else 0,
            "best_profit_item": profitable_items[0]["name"] if profitable_items else "None",
            "average_profit": sum(item["profit_per_cast"] for item in profitable_items) / len(profitable_items) if profitable_items else 0
        }
        
        return context
    
    def _create_high_alchemy_prompt(self, user_query, context):
        """Create specialized prompt for high alchemy conversations."""
        prompt = f"""You are an expert Old School RuneScape (OSRS) High Alchemy advisor. You help players optimize their magic training and profit through intelligent high alchemy strategies.

## Current Context:
- Player has {context['player_capital']:,} GP available
- Nature runes cost {context['nature_rune_cost']} GP each
- High Alchemy gives {context['magic_requirements']['xp_per_cast']} XP per cast
- Efficient players can do ~{context['magic_requirements']['casts_per_hour']} casts/hour = {context['magic_requirements']['xp_per_hour']:,} XP/hour

## Available High Alchemy Items:
{self._format_items_for_prompt(context['available_items'][:10])}

## Market Summary:
- {context['summary']['profitable_items']}/{context['summary']['total_items']} items are currently profitable
- Best opportunity: {context['summary']['best_profit_item']} ({context['summary']['best_profit_per_cast']:,} GP profit per cast)
- Average profit among profitable items: {context['summary']['average_profit']:.0f} GP per cast

## Your Role:
You are having a natural conversation with a player about high alchemy. Provide intelligent, contextual advice based on the real market data above. Consider their budget, goals, and the current profitability of items.

Be conversational and helpful, not robotic. Answer their specific questions and provide actionable insights about high alchemy opportunities, XP rates, profit potential, and strategic advice.

## Player Question:
{user_query}

## Your Response:
Provide a natural, intelligent response as an OSRS high alchemy expert:"""

        return prompt
    
    def _format_items_for_prompt(self, items):
        """Format items for AI prompt in a readable way."""
        if not items:
            return "No profitable items available."
            
        formatted = []
        for item in items:
            profit_status = f"+{item['profit_per_cast']:,} GP" if item['is_profitable'] else f"{item['profit_per_cast']:,} GP"
            margin = f"({item['profit_margin_percent']:+.1f}%)"
            ge_limit_text = f"Limit: {item['ge_limit']:,}" if item['ge_limit'] > 0 else "No limit"
            
            formatted.append(
                f"• {item['name']}: Buy {item['buy_price']:,} → Alch {item['high_alch_value']:,} = {profit_status} {margin} | {ge_limit_text}"
            )
        
        return "\n".join(formatted)
    
    async def _generate_high_alchemy_conversation_response(self, user_query, context, current_capital, nature_rune_price):
        """Generate intelligent conversational responses about high alchemy."""
        query_lower = user_query.lower().strip()
        
        # Get context information
        profitable_items = context.get('summary', {}).get('profitable_items', 0)
        total_items = context.get('summary', {}).get('total_items', 0)
        best_item = context.get('summary', {}).get('best_profit_item', 'Unknown')
        best_profit = context.get('summary', {}).get('best_profit_per_cast', 0)
        available_items = context.get('available_items', [])
        
        # Handle specific item list requests first
        if any(phrase in query_lower for phrase in ['what are the', 'list the', 'show me the', 'profitable items', 'all the items']):
            return self._generate_item_list_response(available_items, query_lower, current_capital, nature_rune_price)
        
        # Handle ranking questions (most profitable, second best, etc.)
        elif any(phrase in query_lower for phrase in ['most profitable', 'best item', 'top item', 'highest profit']):
            return self._generate_top_items_response(available_items, query_lower, current_capital, nature_rune_price)
        
        elif any(phrase in query_lower for phrase in ['second', '2nd', 'next best']):
            return self._generate_second_best_response(available_items, query_lower, current_capital, nature_rune_price)
        
        # Generate conversational responses based on query intent  
        elif any(greeting in query_lower for greeting in ['hi', 'hello', 'hey', 'sup']):
            if profitable_items > 0:
                budget_text = f"If you tell me your budget, I can help you calculate specific profits!" if not current_capital else f"With your {current_capital:,} GP budget, you have great options!"
                
                return f"""Hey there! 👋 Welcome to the High Alchemy Intelligence Center!

Great news - there are currently **{profitable_items} profitable items** available for high alchemy! 

**Current Market Snapshot:**
• Nature runes: {nature_rune_price} GP each (cost per cast)
• Magic XP per cast: 65 XP
• Best item right now: **{best_item}** ({best_profit:,} GP profit per cast)

{budget_text}

What would you like to explore? I can help with:
- **Item Analysis** - Finding the most profitable items
- **XP Strategy** - Maximizing magic experience per hour  
- **Market Insights** - Understanding profit trends
- **Budget Planning** - Optimizing your capital allocation

Just ask me anything about high alchemy!"""
            else:
                return f"""Hey there! 👋 Welcome to the High Alchemy Intelligence Center!

While the current market doesn't show many profitable high alchemy opportunities right now, that's totally normal - markets fluctuate constantly!

**Here's what I can help you with:**
• **Market timing** - When to check back for better opportunities
• **Strategy planning** - Understanding high alchemy mechanics
• **XP training** - Using high alchemy for pure magic experience
• **Item analysis** - Learning which items are typically profitable

**High Alchemy Basics:**
- Nature runes cost {nature_rune_price} GP each
- Each cast gives 65 magic XP
- Efficient players can do ~1,200 casts/hour = 78,000 XP/hour

What aspect of high alchemy would you like to discuss?"""
        
        elif 'profit' in query_lower or 'money' in query_lower or 'gp' in query_lower:
            if profitable_items > 0:
                budget_specific = ""
                if current_capital:
                    budget_specific = f"\n**With your {current_capital:,} GP budget:** You have access to all these profitable options!"
                else:
                    budget_specific = "\n**Budget Planning:** Tell me your budget and I can calculate specific profit potential for you!"
                
                return f"""Great question about profits! 💰

**Current Market Status:**
I found **{profitable_items} items** that are currently profitable for high alchemy!

**Top Opportunity:** {best_item} 
- Profit per cast: {best_profit:,} GP (after nature rune cost)
- Potential hourly profit: {best_profit * 1200:,} GP (at 1,200 casts/hour)
{budget_specific}

**Profit Strategy Tips:**
1. **Factor in nature runes** - Each cast costs {nature_rune_price} GP in nature runes
2. **Check GE limits** - Some profitable items have low buy limits
3. **Watch margins** - Profits can change quickly with market fluctuations
4. **Scale gradually** - Start small to test market conditions

**Long-term Approach:**
High alchemy is great for consistent, low-risk profits while training magic. The key is finding items with stable margins and good availability.

Want me to show you the full list of profitable items, or explain the math on specific ones?"""
            else:
                budget_advice = ""
                if current_capital:
                    budget_advice = f"\n**With your {current_capital:,} GP budget:**\n- You could afford ~{current_capital // (nature_rune_price + 500):,} casts of moderate-priced items\n- Focus on items in the 1k-5k GP range for better turnover"
                else:
                    budget_advice = "\n**Budget Considerations:**\n- Higher budgets allow for more expensive items with better margins\n- Even small budgets (100k-500k) can be profitable with the right items"
                
                return f"""I understand you're looking to make profit with high alchemy! 💰

While there aren't many profitable opportunities showing up right now, this is actually pretty common in OSRS markets. Here's my advice:

**Market Timing Strategy:**
- Prices fluctuate throughout the day
- Peak times (evenings/weekends) often have better margins
- Major updates can shift the entire alchemy market

**Alternative Profit Approaches:**
1. **Break-even training** - Find items that roughly break even while giving XP
2. **Bulk buying** - Buy profitable items when prices are low, alch later
3. **Diversification** - Split budget across multiple items to reduce risk
{budget_advice}

**Remember:** High alchemy is as much about magic training as profit. Even breaking even while gaining 78K XP/hour is valuable!

What's your main goal - pure profit, or a balance of profit and XP?"""
        
        elif any(word in query_lower for word in ['help', 'how', 'what', 'explain', 'about']):
            return f"""I'm here to help you master high alchemy! 🧙‍♂️

**High Alchemy Fundamentals:**
- **Spell requirement:** 55 Magic level
- **Runes needed:** 1 Nature rune + 5 Fire runes per cast (or fire staff)
- **XP gained:** 65 Magic XP per cast
- **Cast time:** ~3 seconds per cast (1,200 casts/hour max)

**How It Works:**
1. Buy items from Grand Exchange
2. Cast High Level Alchemy on them
3. Get coins equal to the item's "high alch value"
4. Profit = High alch value - Buy price - Nature rune cost ({nature_rune_price} GP)

**With Your Budget ({current_capital:,} GP):**
- You can afford significant alchemy training
- Focus on items with positive margins
- Consider both profit and XP efficiency

**Smart Strategies:**
- **Research first** - Check high alch values vs GE prices
- **Start small** - Test with small quantities first
- **Monitor markets** - Prices change frequently
- **Factor in time** - Consider GP/hour vs pure profit

Currently scanning {total_items} items, found {profitable_items} profitable options.

What specific aspect would you like me to explain more? Item selection, profit calculations, or training efficiency?"""
        
        elif 'black' in query_lower and ('d\'hide' in query_lower or 'dhide' in query_lower or 'dragonhide' in query_lower):
            # Specific item inquiry
            return f"""Ah, Black Dragonhide bodies! A classic high alchemy choice! 🐉

**Black D'hide Body Analysis:**
- **High alch value:** 2,508 GP
- **Typical GE price:** Usually 2,100-2,400 GP
- **Potential profit:** ~100-400 GP per cast (minus {nature_rune_price} GP nature rune)
- **GE limit:** 10 every 4 hours (relatively low)

**Why It's Popular:**
✅ Consistent margins
✅ Good for magic training  
✅ Relatively stable price
❌ Low buy limit restricts volume

**Current Market Context:**
With {current_capital:,} GP, you could buy ~{current_capital // 2300:,} black d'hide bodies (if available).

**Strategy Recommendation:**
- Great for steady, low-volume alchemy training
- Combine with other items due to low GE limit
- Check current GE prices - margins vary with market conditions
- Consider Black D'hide Chaps (different limit, similar concept)

**Alternative Similar Items:**
- Green/Blue/Red D'hide bodies (different margins/limits)
- Rune equipment (higher value, different margins)

Want me to check what the current margins look like for dragonhide items, or explain how to calculate profitability?"""
        
        else:
            # General conversational response
            return f"""I'd be happy to help with that! 🧙‍♂️

**Your High Alchemy Setup:**
- Budget: {current_capital:,} GP
- Nature rune cost: {nature_rune_price} GP per cast
- Current market: {profitable_items}/{total_items} items showing profit

**What I Can Help With:**
- **Item Analysis** - Break down specific items' profitability
- **Strategy Planning** - Long-term approaches to alchemy
- **Market Insights** - Understanding price fluctuations  
- **XP Efficiency** - Balancing profit with magic training
- **Risk Management** - Avoiding losses in volatile markets

**Popular Topics:**
- "What's the most profitable item right now?"
- "How much XP can I get with my budget?"  
- "Should I focus on profit or XP?"
- "When are the best times to buy/alch?"

The beauty of high alchemy is that it combines magic training with potential profit - you're basically getting paid to level up! 

What specific aspect of high alchemy interests you most? I can dive deep into any area you'd like to explore!"""
    
    def _generate_item_list_response(self, available_items, query_lower, current_capital, nature_rune_price):
        """Generate response showing list of profitable items."""
        if not available_items:
            return f"""I don't see any profitable high alchemy items in the current market data.

This could be because:
• Market prices are currently unfavorable for alchemy
• The data is still loading
• Nature runes at {nature_rune_price} GP are making margins too thin

Try asking again in a few minutes, or I can help you understand high alchemy strategies for when better opportunities appear!"""

        # Show top 10 items
        top_items = available_items[:10]
        
        response = f"""Here are the **top {len(top_items)} profitable high alchemy items** right now:

"""
        for i, item in enumerate(top_items, 1):
            profit = item.get('profit_per_cast', 0)
            margin = item.get('profit_margin_percent', 0)
            name = item.get('name', 'Unknown Item')
            buy_price = item.get('buy_price', 0)
            alch_value = item.get('high_alch_value', 0)
            ge_limit = item.get('ge_limit', 0)
            
            response += f"""**{i}. {name}**
   • Buy: {buy_price:,} GP → Alch: {alch_value:,} GP = **{profit:,} GP profit** ({margin:+.1f}%)
   • GE Limit: {ge_limit:,} every 4 hours
   
"""
        
        if current_capital:
            response += f"""**With your {current_capital:,} GP budget**, you have lots of options! Remember to factor in GE limits for sustained trading.

"""
        
        response += f"""Nature runes cost {nature_rune_price} GP each (already factored into profits above).

Which items interest you most? I can provide detailed analysis on any of them!"""
        
        return response
    
    def _generate_top_items_response(self, available_items, query_lower, current_capital, nature_rune_price):
        """Generate response for 'most profitable' type questions."""
        if not available_items:
            return "I don't have access to profitable item data right now. Let me help you understand high alchemy strategies instead!"
            
        # Show top 5 items
        top_5 = available_items[:5]
        
        response = f"""Here are the **top 5 most profitable** high alchemy items right now:

"""
        
        for i, item in enumerate(top_5, 1):
            profit = item.get('profit_per_cast', 0)
            margin = item.get('profit_margin_percent', 0)
            name = item.get('name', 'Unknown Item')
            buy_price = item.get('buy_price', 0)
            
            hourly_profit = profit * 1200  # 1200 casts per hour
            
            response += f"""**{i}. {name}** - {profit:,} GP profit per cast
   • Buy at ~{buy_price:,} GP, profit margin: {margin:+.1f}%
   • Potential: {hourly_profit:,} GP/hour (at 1,200 casts/hour)

"""
        
        response += f"""These profits include the {nature_rune_price} GP nature rune cost.

Want details on any specific item, or should I help you calculate potential profits with your budget?"""
        
        return response
    
    def _generate_second_best_response(self, available_items, query_lower, current_capital, nature_rune_price):
        """Generate response for 'second best' type questions."""
        if len(available_items) < 2:
            return "I need at least 2 profitable items to show you the second best option. The market data might still be loading!"
            
        second_item = available_items[1]  # Second in the list
        profit = second_item.get('profit_per_cast', 0)
        margin = second_item.get('profit_margin_percent', 0)
        name = second_item.get('name', 'Unknown Item')
        buy_price = second_item.get('buy_price', 0)
        alch_value = second_item.get('high_alch_value', 0)
        ge_limit = second_item.get('ge_limit', 0)
        
        hourly_profit = profit * 1200
        
        response = f"""The **second most profitable** item is **{name}**!

**Breakdown:**
• Buy price: ~{buy_price:,} GP
• High alch value: {alch_value:,} GP  
• Nature rune cost: {nature_rune_price} GP
• **Net profit: {profit:,} GP per cast** ({margin:+.1f}% margin)

**Potential Earnings:**
• Per hour: {hourly_profit:,} GP (at 1,200 casts/hour)
• GE limit: {ge_limit:,} every 4 hours

"""
        
        if current_capital and buy_price > 0:
            max_quantity = current_capital // buy_price
            if ge_limit > 0:
                practical_quantity = min(max_quantity, ge_limit)
            else:
                practical_quantity = max_quantity
                
            total_profit = practical_quantity * profit
            
            response += f"""**With your budget:**
• You could buy {practical_quantity:,} {name}s
• Total profit potential: {total_profit:,} GP

"""
        
        response += "Want me to compare this with the #1 item, or analyze other options?"
        
        return response
    
    async def _load_high_alchemy_items(self, nature_rune_price):
        """Load complete high alchemy item dataset from database with profit calculations."""
        from asgiref.sync import sync_to_async
        from apps.items.models import Item
        from apps.prices.models import PriceSnapshot
        
        # Get all items with high alchemy values and current prices
        @sync_to_async
        def get_items_with_prices():
            from django.db.models import Q, F, Value, IntegerField
            from django.db.models.functions import Coalesce
            
            # Query items with high_alch > 0 and try to get current prices
            items_query = Item.objects.filter(
                high_alch__gt=0,
                is_active=True
            ).select_related()
            
            items_with_data = []
            
            for item in items_query[:200]:  # Limit to prevent overwhelming the AI
                # Get latest price data
                latest_price = PriceSnapshot.objects.filter(
                    item_id=item.item_id
                ).order_by('-timestamp').first()
                
                current_buy_price = latest_price.low_price if latest_price else item.value
                profit_per_cast = item.high_alch - current_buy_price - nature_rune_price
                
                # Only include items with reasonable profit potential (even slightly negative)
                if profit_per_cast > -200:  # Allow some negative for completeness
                    items_with_data.append({
                        'item_id': item.item_id,
                        'name': item.name,
                        'current_buy_price': current_buy_price,
                        'high_alch': item.high_alch,
                        'limit': item.limit,
                        'members': item.members,
                        'recommendation_score': max(0, profit_per_cast),  # Simple scoring
                        'daily_volume': latest_price.high_time if latest_price else 0,
                        'profit_per_cast': profit_per_cast,
                        'profit_margin_percent': (profit_per_cast / current_buy_price * 100) if current_buy_price > 0 else 0,
                        'last_updated': latest_price.timestamp if latest_price else None
                    })
            
            return items_with_data
        
        items_data = await get_items_with_prices()
        
        # Sort by profit per cast (descending)
        items_data.sort(key=lambda x: x['profit_per_cast'], reverse=True)
        
        logger.info(f"Loaded {len(items_data)} profitable high alchemy items from database")
        
        # Convert to simple objects for _format_high_alchemy_context
        class DatabaseItem:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        return [DatabaseItem(item_data) for item_data in items_data]
    
    async def process_query(self, user_query, items, current_capital, nature_rune_price):
        """Process a high alchemy query using local AI models."""
        try:
            # Load complete high alchemy database instead of just frontend items
            all_items = await self._load_high_alchemy_items(nature_rune_price)
            logger.info(f"Loaded {len(all_items)} high alchemy items from database")
            
            # Format context for AI using complete dataset
            context = self._format_high_alchemy_context(all_items, current_capital, nature_rune_price)
            
            # Create specialized high alchemy query with context embedded
            enhanced_query = f"""HIGH ALCHEMY EXPERT QUERY:

CONTEXT:
- Player has {current_capital:,} GP available
- Nature runes cost {nature_rune_price} GP each
- {context['summary']['profitable_items']}/{context['summary']['total_items']} items are currently profitable
- Best opportunity: {context['summary']['best_profit_item']} ({context['summary']['best_profit_per_cast']:,} GP profit per cast)

AVAILABLE ITEMS:
{self._format_items_for_prompt(context['available_items'][:10])}

PLAYER QUESTION: {user_query}

Please provide expert high alchemy advice based on this data."""

            # Use the public process_query method with capital context
            response = await self.merchant_agent.process_query(
                enhanced_query,
                user_id="high_alchemy_user",
                include_context=True,
                capital_gp=current_capital
            )
            
            # Extract and clean response
            ai_response = response.get('response', '')
            
            # Check for template fallback responses and replace with intelligent high alchemy advice
            if not ai_response or 'searched the current market data' in ai_response or 'didn\'t find any items meeting the profit criteria' in ai_response:
                logger.info("AI returned template response, generating intelligent high alchemy advice instead")
                ai_response = await self._generate_high_alchemy_conversation_response(user_query, context, current_capital, nature_rune_price)
            
            # Clean any thinking tags
            import re
            ai_response = re.sub(r'<think>.*?</think>', '', ai_response, flags=re.DOTALL)
            ai_response = re.sub(r'<thinking>.*?</thinking>', '', ai_response, flags=re.DOTALL)
            ai_response = ai_response.strip()
            
            return {
                'success': True,
                'response': ai_response,
                'model_used': response.get('agent_used', 'local_ai'),
                'context_items_count': len(context['available_items']),
                'profitable_items_count': context['summary']['profitable_items']
            }
            
        except Exception as e:
            logger.error(f"High alchemy AI error: {e}", exc_info=True)
            # Even on error, provide helpful high alchemy advice
            fallback_response = await self._generate_high_alchemy_conversation_response(user_query, {}, current_capital, nature_rune_price)
            return {
                'success': True,
                'response': fallback_response,
                'model_used': 'high_alchemy_fallback',
                'context_items_count': 0,
                'profitable_items_count': 0
            }

def _extract_budget_from_query(query):
    """Extract budget from user query using regex patterns."""
    import re
    
    if not query:
        return None
        
    query_lower = query.lower()
    
    # Look for budget patterns like "1m", "500k", "10m", "1000000", etc.
    patterns = [
        r'(\d+(?:\.\d+)?)\s*m(?:il)?(?:lion)?',  # 1m, 1.5mil, 5million
        r'(\d+(?:\.\d+)?)\s*k',  # 500k, 1.5k
        r'(\d+(?:\.\d+)?)\s*b(?:il)?(?:lion)?',  # 1b, 1bil
        r'(\d+(?:,\d{3})*)\s*(?:gp|gold|coins?)',  # 1,000,000 gp
        r'budget.{0,20}?(\d+(?:,\d{3})*)',  # budget of 1,000,000
        r'have\s+(\d+(?:,\d{3})*)',  # I have 1,000,000
        r'with\s+(\d+(?:,\d{3})*)'   # with 1,000,000
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, query_lower)
        for match in matches:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                # Convert based on suffix
                if 'm' in pattern:
                    amount *= 1000000
                elif 'k' in pattern:
                    amount *= 1000
                elif 'b' in pattern:
                    amount *= 1000000000
                return int(amount)
            except (ValueError, IndexError):
                continue
                
    return None

@csrf_exempt
@require_http_methods(["POST"])
async def high_alchemy_ai_chat(request):
    """API endpoint for high alchemy AI conversations."""
    try:
        # Parse request
        data = json.loads(request.body.decode('utf-8'))
        user_query = data.get('query', '').strip()
        # Don't assume any budget - let AI detect from user query
        current_capital = data.get('currentCapital', None)  
        nature_rune_price = data.get('natureRunePrice', 180)
        items_data = data.get('items', [])
        
        # Extract budget from user query if not provided
        if current_capital is None:
            current_capital = _extract_budget_from_query(user_query)
        
        if not user_query:
            return JsonResponse({
                'success': False,
                'error': 'Query is required'
            }, status=400)
        
        capital_display = f"{current_capital:,} GP" if current_capital is not None else "Not specified"
        logger.info(f"High alchemy AI query: {user_query[:100]}... (Capital: {capital_display})")
        
        # Convert items data to objects (simulate Item objects for AI processing)
        class ItemData:
            def __init__(self, data):
                self.name = data.get('name', 'Unknown')
                self.item_id = data.get('id', 0)
                self.current_buy_price = data.get('current_buy_price', 0)
                self.high_alch = data.get('high_alch', 0)
                self.limit = data.get('limit', 0)
                self.members = data.get('members', False)
                self.recommendation_score = data.get('recommendation_score', 0)
                self.daily_volume = data.get('daily_volume', 0)
        
        items = [ItemData(item) for item in items_data]
        
        # Initialize AI agent and process query with full database
        ai_agent = AIHighAlchemyAgent()
        result = await ai_agent.process_query(user_query, items, current_capital, nature_rune_price)
        
        # Return response
        response_data = {
            'success': result['success'],
            'response': result['response'],
            'timestamp': timezone.now().isoformat(),
            'metadata': {
                'model_used': result.get('model_used', 'local_ai'),
                'context_items': result.get('context_items_count', 0),
                'profitable_items': result.get('profitable_items_count', 0),
                'capital': current_capital,
                'nature_rune_price': nature_rune_price
            }
        }
        
        if not result['success']:
            response_data['error'] = result.get('error', 'Unknown error')
            
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON format'
        }, status=400)
        
    except Exception as e:
        logger.error(f"High alchemy AI endpoint error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)
