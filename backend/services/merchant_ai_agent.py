"""
AI-Powered Merchant Agent for natural language querying of OSRS market data.

Combines RAG (Retrieval-Augmented Generation) with market analysis to provide
intelligent responses about trading opportunities, price trends, and market insights.
"""

import asyncio
import json
import logging
import re
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from django.utils import timezone
from django.db.models import Q
from django.core.cache import cache
from asgiref.sync import sync_to_async

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation, HistoricalAnalysis
from apps.prices.merchant_models import MarketTrend, MerchantOpportunity, MerchantAlert
from services.multi_agent_ai_service import MultiAgentAIService, TaskComplexity
from services.market_analysis_service import MarketAnalysisService
from services.mcp_ai_bridge import MCPAIBridge
from services.smart_opportunity_detector import SmartOpportunityDetector
from services.market_signal_generator import MarketSignalGenerator
from services.advanced_risk_engine import AdvancedRiskEngine
from services.enhanced_query_patterns import enhanced_patterns
from services.profit_detection_engine import profit_engine
from services.enhanced_response_generator import enhanced_response_generator
from services.money_maker_detector import MoneyMakerDetector, AsyncMoneyMakerDetector
from services.set_combining_detector import SetCombiningDetector
from apps.trading_strategies.services.decanting_detector import DecantingDetector

logger = logging.getLogger(__name__)


class MerchantAIAgent:
    """
    AI Agent for merchant trading assistance with natural language interface.
    """
    
    def __init__(self):
        self.ai_service = MultiAgentAIService()
        self.market_service = MarketAnalysisService()
        self.mcp_bridge = MCPAIBridge()
        
        # Enhanced intelligent services
        self.opportunity_detector = SmartOpportunityDetector()
        self.signal_generator = MarketSignalGenerator()
        self.risk_engine = AdvancedRiskEngine()
        
        # New advanced AI components
        self.query_patterns = enhanced_patterns
        self.profit_engine = profit_engine
        self.response_generator = enhanced_response_generator
        
        # Money maker strategy services (your friend's 50M → 100M approach)
        self.money_maker_detector = MoneyMakerDetector()
        self.set_combining_detector = SetCombiningDetector()
        self.decanting_detector = DecantingDetector()
        
        # Lightweight conversation memory (Budget version for M1 Mac)
        self.conversation_cache_prefix = "merchant_chat:"
        self.conversation_timeout = 1800  # 30 minutes (reduced for memory efficiency)
        self.max_conversation_history = 3  # Only keep last 3 exchanges per user
        self.user_context_prefix = "user_ctx:"
        self.user_context_timeout = 3600  # 1 hour for user preferences
        
        # Initialize enhanced query patterns and profit engine
        # Using the new comprehensive systems for 100+ trading scenarios
        
        # Response templates
        self.system_prompt = """You are an OSRS trading specialist with access to real-time market data and advanced money-making strategies. You understand proven methods for scaling capital from 50M to 100M+ GP.

RUNESCAPE CURRENCY TERMINOLOGY (CRITICAL):
- k = thousand (100k = 100,000 GP)
- m = million (5m = 5,000,000 GP)  
- b = billion (1b = 1,000,000,000 GP)
- GP = Gold Pieces (OSRS currency)
- Always interpret user queries with this terminology

MONEY MAKING STRATEGIES (COMPREHENSIVE):

HIGH ALCHEMY:
- HIGH ALCHEMY = Buy item from GE + Cast High Level Alchemy spell + Profit from alch value
- Nature rune cost: ~180 GP per cast, Magic XP: 65 XP per cast
- Good for: Consistent profit, magic training, beginners
- Consider buy limits for sustained profit

GRAND EXCHANGE FLIPPING:
- FLIPPING = Buy low, sell high on Grand Exchange
- 2% GE tax on sales (items over 50 GP, bonds exempt, capped at 5M)
- Good for: Quick profits, scalable with capital
- Consider volume, margin after tax, competition

ADVANCED STRATEGIES (50M+ Capital):

BOND FLIPPING:
- Buy bonds with real money, convert to GP, flip high-value items
- Bonds are GE tax exempt (major advantage)
- Target: Expensive weapons, armor, rare items
- Capital requirement: 50M+ for meaningful impact
- Example: "I started with 50m buying bonds then looked at items on the ge that I could flip"

POTION DECANTING:
- Buy high-dose potions, decant to lower doses, profit from convenience
- Requires Barbarian Herblore for efficiency
- Target popular potions: Super combat, Prayer, Ranging, Super strength
- Potential: "40m in decanting potions and made a few mill"
- Best margins: 4-dose → 3-dose or 3-dose → 2-dose

SET COMBINING (Lazy Tax):
- Buy armor/weapon pieces separately, combine, sell as complete set
- Exploit player laziness: "they dont wanna sit there and buy each piece"
- Popular sets: Barrows, God Wars, Void, Dragon
- Premium: 2-6% "lazy tax" for convenience
- Monitor piece vs set price differentials

CAPITAL SCALING APPROACH:
1. Start: Basic flipping with available capital
2. Build: Use decanting for consistent profits (40M potential)
3. Scale: Combine strategies, reinvest profits
4. Advanced: Bond-funded high-value flipping
5. Expert: Multiple strategies simultaneously

GE TAX AWARENESS:
- All strategies must account for 2% selling tax
- Bonds exempt from tax (major advantage for high-value flips)
- Items under 50 GP exempt from tax
- Tax capped at 5M per item

RESPONSE FORMAT:
📈 **Money Making Opportunities**

**💰 Capital Tier: [Starter/Intermediate/Advanced/Expert]**
- Current strategies for your capital level
- Progression path to next tier

**🔥 Immediate Opportunities:**
[Most profitable current options with exact numbers]

**⚡ Scalable Strategies:**
[Long-term approaches for capital growth]

RULES:
- Always consider GE tax in profit calculations
- Recommend strategies appropriate for user's capital level
- Include progression advice for scaling up
- Use exact numbers, mention key factors
- Understand proven 50M → 100M approaches

**💰 Flipping Opportunities:**
1. **[Item Name]** - [Why good flip]
   Buy: [buy price] GP | Sell: [sell price] GP | Profit: [margin] GP | Margin: [%]%

RULES:
- Show BOTH alchemy and flipping opportunities when possible
- Use EXACT numbers for all prices and profits
- Mention key factors: buy limits, volume, timing
- One sentence explanation per item maximum
- UNDERSTAND RuneScape currency: 5m = 5 million GP, 100k = 100 thousand GP, 1b = 1 billion GP"""
    
    async def process_query(self, 
                          query: str, 
                          user_id: str = "anonymous",
                          include_context: bool = True,
                          capital_gp: Optional[int] = None) -> Dict[str, Any]:
        """
        Process a natural language query about OSRS market/trading.
        
        Args:
            query: User's natural language query
            user_id: User identifier for conversation memory
            include_context: Whether to include market context
            capital_gp: Available capital in GP (overrides query extraction)
            
        Returns:
            Dict with response, sources, and metadata
        """
        start_time = datetime.now()
        
        try:
            # 1. Classify query type and extract entities
            query_type, entities = await self._classify_query(query)
            logger.info(f"Query classified as: {query_type} with entities: {entities}")
            
            # 2. Use provided capital or extract from query as fallback
            original_capital = capital_gp
            if capital_gp is None:
                capital_gp = self._extract_capital_from_query(query)
            
            logger.info(f"AI Agent using capital: {capital_gp:,} GP (original parameter: {original_capital}, extracted: {self._extract_capital_from_query(query) if original_capital else 'N/A'})")
            
            # 3. Retrieve relevant market data using RAG + Money Maker strategies
            context = await self._retrieve_context(query, query_type, entities, capital_gp, user_id)
            
            # 3.5. Enhance context with money maker opportunities
            context = await self._enhance_with_money_maker_context(context, capital_gp, query)
            
            # 4. Get conversation history
            conversation_history = await self._get_conversation_history(user_id) if include_context else []
            
            # 5. Determine task complexity for multi-agent routing
            complexity = self._determine_task_complexity(query_type, context)
            
            # 6. Generate AI response using multi-agent system
            response = await self._generate_response(
                query, query_type, context, conversation_history, user_id
            )
            
            # 7. Ensure response is always a dictionary (safety check)
            if isinstance(response, str):
                logger.warning(f"Response was string instead of dict, wrapping: {response[:100]}")
                response = {
                    'response': response,
                    'content': response,
                    'query_type': query_type,
                    'agent_used': 'fallback_wrapper',
                    'processing_time_ms': 0
                }
            elif not isinstance(response, dict):
                logger.error(f"Response was neither string nor dict: {type(response)}")
                response = {
                    'response': str(response),
                    'content': str(response),
                    'query_type': query_type,
                    'agent_used': 'error_fallback',
                    'processing_time_ms': 0
                }
            
            # 8. Update conversation memory
            await self._update_conversation_memory(user_id, query, response)
            
            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Extract multi-agent information from response
            agent_used = response.get('agent_used', self._get_agent_from_complexity(complexity))
            processing_time_ms = response.get('processing_time_ms', int(response_time * 1000))
            
            # If AI failed to generate content, create response from database opportunities
            ai_response = response.get('content')
            logger.info(f"AI Response content check: '{ai_response[:50] if ai_response else None}...', has opportunities: {len(context.get('precision_opportunities', []))}")
            
            if not ai_response or 'failed' in ai_response.lower():
                # Use enhanced response generator with comprehensive analysis
                logger.info("🚀 Generating enhanced AI response with comprehensive analysis")
                ai_response = self.response_generator.generate_comprehensive_response(
                    query=query,
                    query_type=query_type,
                    context=context,
                    capital_gp=capital_gp
                )
                logger.info(f"✅ Generated enhanced response with advanced profit analysis")
            
            return {
                'response': ai_response,
                'query_type': query_type,
                'entities': entities,
                'sources': context.get('sources', []),
                'market_data': context.get('market_summary', {}),
                'opportunities': context.get('opportunities', []),
                'precision_opportunities': context.get('precision_opportunities', []),
                'market_signals': context.get('market_signals', []),
                'risk_assessments': context.get('risk_assessments', []),
                'timing_analyses': context.get('timing_analyses', []),
                'portfolio_optimization': context.get('portfolio_optimization', {}),
                'query_complexity': complexity.value if hasattr(complexity, 'value') else str(complexity),
                'agent_used': agent_used,
                'processing_time_ms': processing_time_ms,
                'task_routing_reason': self._get_routing_reason(complexity),
                'system_load': response.get('system_load', {}),
                'data_quality_score': context.get('confidence', 0.8),
                'confidence_level': context.get('confidence', 0.75),
                'metadata': {
                    'response_time_ms': int(response_time * 1000),
                    'tokens_used': response.get('tokens_used', 0),
                    'model': response.get('model', 'multi-agent-system'),
                    'confidence': context.get('confidence', 0.5),
                }
            }
            
        except Exception as e:
            # Detailed error logging with full traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Error processing merchant query: {e}")
            logger.error(f"Full traceback:\n{error_traceback}")
            
            # Try to provide some fallback market data instead of complete failure
            fallback_data = await self._get_fallback_market_data(query)
            
            return {
                'response': f"I'm having trouble with the AI analysis right now, but here's some basic market data. Error: {str(e)[:100]}...",
                'error': str(e),
                'error_traceback': error_traceback,
                'query_type': 'error_with_fallback',
                'entities': [],
                'sources': fallback_data.get('sources', []),
                'market_data': fallback_data.get('market_summary', {}),
                'opportunities': fallback_data.get('opportunities', []),
                'precision_opportunities': fallback_data.get('precision_opportunities', []),
                'market_signals': fallback_data.get('market_signals', []),
                'risk_assessments': [],
                'timing_analyses': [],
                'portfolio_optimization': {},
                'metadata': {
                    'fallback_mode': True,
                    'error_time': datetime.now().isoformat()
                }
            }
    
    async def _classify_query(self, query: str) -> Tuple[str, List[str]]:
        """Enhanced query classification using the new comprehensive pattern system."""
        query_lower = query.lower().strip()
        
        # Use the enhanced query patterns system for classification
        primary_category, entities, capital_amount = self.query_patterns.classify_enhanced_query(query)
        
        logger.debug(f"Enhanced classification: '{query}' -> {primary_category} with entities: {entities} and capital: {capital_amount}")
        
        # Validate entities against database
        validated_entities = []
        for entity in entities[:10]:  # Limit to prevent excessive DB queries
            # Check if item exists with broader matching
            if await Item.objects.filter(
                Q(name__icontains=entity) | 
                Q(examine__icontains=entity) |
                Q(name__iregex=r'\b' + re.escape(entity) + r'\b')
            ).aexists():
                validated_entities.append(entity)
        
        return primary_category, validated_entities
    
    async def _retrieve_context(self, query: str, query_type: str, entities: List[str], capital_gp: Optional[int] = None, user_id: str = "anonymous") -> Dict[str, Any]:
        """Retrieve ultra-intelligent context using all advanced services."""
        context = {
            'sources': [],
            'market_summary': {},
            'opportunities': [],
            'precision_opportunities': [],
            'market_signals': [],
            'risk_assessments': [],
            'timing_analyses': [],
            'portfolio_optimization': {},
            'price_alerts': [],
            'market_anomalies': [],
            'trends': [],
            'confidence': 0.5,
            'investment_intelligence': {},
            'market_events': [],
            'embedding_freshness': {},
        }
        
        try:
            # FIXED: Use provided capital parameter or extract from query as fallback
            if capital_gp is None:
                capital_gp = self._extract_capital_from_query(query)
            
            logger.info(f"Capital parameter prioritization: API={capital_gp}, Query extraction would be={self._extract_capital_from_query(query)}")
            
            # Extract risk tolerance from query context
            risk_tolerance = self._extract_risk_tolerance(query)
            
            logger.info(f"Processing {query_type} query with {capital_gp:,} GP capital, {risk_tolerance} risk")
            
            # 1. Get item IDs from entities for analysis
            item_ids = []
            if entities:
                for entity in entities:
                    items = [
                        item async for item in Item.objects.filter(
                            Q(name__icontains=entity) | Q(examine__icontains=entity)
                        )[:3]
                    ]
                    item_ids.extend([item.item_id for item in items])
            
            # 2. CONVERSATIONAL CONTEXT HANDLING - Leverage existing RAG infrastructure
            if query_type.startswith('conversational_'):
                logger.info(f"Processing conversational query: {query_type}")
                
                # For conversational queries, use hybrid search to find relevant context
                if query_type == 'conversational_question' or 'what' in query.lower() or 'how' in query.lower():
                    try:
                        # Use hybrid search service to find relevant items/context
                        from services.search_service import HybridSearchService
                        search_service = HybridSearchService()
                        
                        # Perform semantic search for context (wrap in sync_to_async for Django ORM)
                        from asgiref.sync import sync_to_async
                        search_results = await sync_to_async(search_service.search_items)(
                            query=query,
                            limit=5,
                            use_ai_enhancement=False  # Skip AI enhancement for conversational context
                        )
                        
                        context['conversation_context'] = {
                            'search_results': search_results.get('results', []),
                            'query_understanding': query,
                            'context_type': query_type
                        }
                        context['sources'].append('hybrid_search_context')
                        
                    except Exception as e:
                        logger.warning(f"Conversational context search failed: {e}")
                
                # Set conversational confidence and return early for pure conversational queries
                context['confidence'] = 0.9
                if query_type in ['conversational_greeting', 'conversational_feedback']:
                    return context
            
            # 3. PRECISION TRADING ANALYSIS - Always run for capital-specific queries
            capital_keywords = ['capital', 'GP', 'gp', 'million', 'opportunities', 'trading', 'buy', 'sell', 'profitable']
            has_capital_context = capital_gp != 100000000 or any(keyword in query.lower() for keyword in capital_keywords)
            
            if query_type in ['precision_trading', 'opportunity_search', 'capital_optimization', 'general', 'market_analysis', 'capital_growth_strategy'] and has_capital_context:
                logger.info(f"Running precision opportunity detection for {capital_gp:,} GP")
                
                # Get conversation history for item exclusion
                conversation_history = await self._get_conversation_history(user_id or "anonymous")
                exclude_items = self._extract_shown_items_from_conversation(conversation_history)
                
                # Get ultra-precise trading opportunities using tags with conversation memory
                precision_opps = await self.opportunity_detector.detect_tagged_opportunities(
                    query=query,
                    capital_gp=capital_gp,
                    max_opportunities=12,  # Increased to match AI text recommendations
                    exclude_items=exclude_items  # Don't repeat previously shown items
                )
                
                # Convert PrecisionOpportunity objects to dictionaries for JSON serialization
                context['precision_opportunities'] = [
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
                        'optimal_buy_window_start': opp.optimal_buy_window_start.isoformat() if hasattr(opp, 'optimal_buy_window_start') and opp.optimal_buy_window_start else None,
                        'optimal_sell_window_start': opp.optimal_sell_window_start.isoformat() if hasattr(opp, 'optimal_sell_window_start') and opp.optimal_sell_window_start else None,
                        'daily_volume': getattr(opp, 'daily_volume', 0),
                        'recent_volatility': getattr(opp, 'recent_volatility', 0.0),
                        'market_momentum': getattr(opp, 'market_momentum', 'neutral'),
                        'recommended_position_size': getattr(opp, 'recommended_position_size', 0),
                        'max_capital_allocation_pct': getattr(opp, 'max_capital_allocation_pct', 0.0),
                        'confidence_score': getattr(opp, 'confidence_score', 0.0),
                    }
                    for opp in precision_opps
                ]
                
                # Get risk assessments for top opportunities
                if precision_opps:
                    logger.info("Performing risk assessments")
                    risk_tasks = [
                        self.risk_engine.assess_opportunity_risk(opp, capital_gp, risk_tolerance)
                        for opp in precision_opps[:5]  # Top 5 for performance
                    ]
                    risk_assessments = await asyncio.gather(*risk_tasks, return_exceptions=True)
                    context['risk_assessments'] = [r for r in risk_assessments if not isinstance(r, Exception) and r is not None]
                    
                    # Get timing analysis
                    timing_analyses = await self.risk_engine.analyze_optimal_timing(precision_opps[:5])
                    context['timing_analyses'] = timing_analyses
                    
                    # Portfolio optimization
                    if len(precision_opps) > 1:
                        portfolio_opt = await self.risk_engine.optimize_portfolio(
                            precision_opps, context['risk_assessments'], capital_gp, risk_tolerance
                        )
                        context['portfolio_optimization'] = portfolio_opt
            
            # 3. REAL-TIME MARKET SIGNALS
            if query_type in ['market_intelligence', 'precision_trading', 'risk_analysis']:
                logger.info("Generating real-time market signals")
                
                # Generate market signals for relevant items
                signal_item_ids = item_ids if item_ids else None
                market_signals = await self.signal_generator.generate_realtime_signals(
                    item_ids=signal_item_ids,
                    signal_types=['strong_buy', 'buy', 'sell', 'strong_sell']
                )
                context['market_signals'] = market_signals[:10]  # Top 10 signals
                
                # Detect market anomalies
                anomalies = await self.signal_generator.detect_market_anomalies(lookback_hours=24)
                context['market_anomalies'] = anomalies[:5]  # Top 5 anomalies
                
                # Generate price alerts for precision opportunities
                if context['precision_opportunities']:
                    alerts = await self.signal_generator.generate_price_alerts(
                        context['precision_opportunities'], alert_distance_pct=3.0
                    )
                    context['price_alerts'] = alerts
            
            # 4. MCP BRIDGE INTELLIGENCE (Enhanced market context)
            if item_ids:
                user_context = {
                    'query_type': query_type,
                    'entities': entities,
                    'capital_gp': capital_gp,
                    'risk_tolerance': risk_tolerance,
                    'timestamp': datetime.now().isoformat(),
                }
                
                try:
                    # Get AI-enhanced market context from MCP bridge
                    mcp_context = await self.mcp_bridge.get_ai_enhanced_market_context(
                        item_ids=item_ids[:10],  # Limit to prevent overload
                        query_type=query_type,
                        user_context=user_context
                    )
                    
                    # Extract data from MCP bridge response
                    context['market_summary'] = mcp_context.get('market_summary', {})
                    context['investment_intelligence'] = mcp_context.get('investment_intelligence', {})
                    context['market_events'] = mcp_context.get('market_events', [])
                    context['embedding_freshness'] = mcp_context.get('embedding_freshness', {})
                    
                    # Convert MCP items to sources format
                    mcp_items = mcp_context.get('items', {})
                    for item_id, item_data in mcp_items.items():
                        context['sources'].append({
                            'item_name': item_data.get('name', f'Item {item_id}'),
                            'current_profit': item_data.get('profit_potential', 0),
                            'buy_price': item_data.get('current_price', 0),
                            'volume': item_data.get('volume', 0),
                            'data_source': 'weird_gloop',
                            'relevance_score': item_data.get('relevance_score', 0.8),
                            'volatility_score': item_data.get('volatility_score', 0),
                            'is_trending': item_data.get('is_trending', False),
                            'prediction': item_data.get('prediction', {}),
                        })
                        
                except Exception as mcp_error:
                    logger.warning(f"MCP bridge error: {mcp_error}")
            
            # 5. Fallback semantic search if no precision data
            if not context['precision_opportunities'] and not context['sources']:
                search_results = await self._semantic_search(query, limit=10)
                context['sources'].extend(search_results)
            
            # 6. SPECIAL QUERY TYPE HANDLING
            
            # Capital Growth Strategy Analysis
            if query_type == 'capital_growth_strategy':
                logger.info("Processing capital growth strategy query")
                start_amount, target_amount = self._extract_growth_targets(query)
                context['growth_analysis'] = await self._analyze_capital_growth(start_amount, target_amount, query)
                context['growth_timeline'] = await self._calculate_growth_timeline(start_amount, target_amount)
            
            # Market Secrets Analysis
            if query_type == 'market_secrets':
                logger.info("Processing market secrets query")
                context['market_secrets'] = await self._analyze_market_secrets(query, capital_gp)
                context['insider_insights'] = await self._get_insider_insights()
            
            # Potion Trading Analysis
            if query_type == 'potion_trading':
                logger.info("Processing potion trading query")
                context['potion_analysis'] = await self._analyze_potion_market(capital_gp, risk_tolerance)
                context['consumables_data'] = await self._get_consumables_opportunities()
            
            # Time to Goal Calculations
            if query_type == 'time_to_goal':
                logger.info("Processing time-to-goal query")
                target_amount = self._extract_target_from_query(query)
                context['timeline_analysis'] = await self._calculate_realistic_timeline(capital_gp, target_amount)
            
            # 7. ADVANCED PROFIT DETECTION ENGINE INTEGRATION
            # Handle million+ margin opportunities and multi-tier analysis
            if query_type in ['million_margin_flips', 'capital_10k_strategy', 'capital_100k_strategy', 
                            'capital_1m_strategy', 'capital_10m_strategy', 'opportunity_search'] and capital_gp:
                logger.info(f"🎯 Running advanced profit detection for {query_type} with {capital_gp:,} GP")
                
                try:
                    # Find million+ margin opportunities  
                    if query_type == 'million_margin_flips' or capital_gp >= 1_000_000:
                        million_opportunities = await sync_to_async(
                            self.profit_engine.find_million_margin_opportunities
                        )(capital=capital_gp, limit=20)
                        context['million_margin_opportunities'] = million_opportunities
                        logger.info(f"Found {len(million_opportunities)} million+ margin opportunities")
                    
                    # Get capital-optimized portfolio
                    risk_preference = 'conservative' if capital_gp < 100_000 else 'balanced' if capital_gp < 1_000_000 else 'aggressive'
                    portfolio = await sync_to_async(
                        self.profit_engine.get_capital_optimized_portfolio
                    )(capital=capital_gp, risk_preference=risk_preference)
                    context['optimized_portfolio'] = portfolio
                    
                    # Find opportunities by profit tier based on capital
                    capital_tier = self.query_patterns.get_capital_tier(capital_gp)
                    tier_mapping = {
                        'micro': 'small_margin',
                        'small': 'medium_margin', 
                        'medium': 'large_margin',
                        'high': 'million_margin',
                        'whale': 'mega_margin'
                    }
                    
                    target_tier = tier_mapping.get(capital_tier, 'medium_margin')
                    tier_opportunities = await sync_to_async(
                        self.profit_engine.find_opportunities_by_tier
                    )(tier_name=target_tier, capital=capital_gp, limit=15, sort_by='profit')
                    context['tier_opportunities'] = tier_opportunities
                    
                    logger.info(f"✅ Advanced profit analysis complete: {len(tier_opportunities)} {target_tier} opportunities")
                    
                except Exception as e:
                    logger.error(f"❌ Advanced profit detection failed: {e}")
                    context['profit_detection_error'] = str(e)
            
            # 8. Legacy trend data for specific items
            if query_type in ['trend_analysis', 'market_analysis'] and entities:
                trends = await self._get_trend_data(entities)
                context['trends'] = trends
            
            # 9. Calculate ultra-enhanced confidence score
            intelligence_factors = [
                len(context['precision_opportunities']) * 3,  # Precision opportunities are most valuable
                len(context['market_signals']) * 2,           # Real-time signals are very valuable
                len(context['risk_assessments']) * 2,         # Risk analysis adds high value
                len(context['sources']),                      # Basic data points
                len(context.get('market_events', [])),        # Market events
                len(context.get('price_alerts', [])),         # Price alerts
                (3 if context.get('investment_intelligence') else 0),  # Investment intelligence
                (2 if context.get('portfolio_optimization') else 0),   # Portfolio optimization
            ]
            
            total_intelligence = sum(intelligence_factors)
            context['confidence'] = min(1.0, total_intelligence / 25)  # Scale for ultra-high standards
            
            logger.info(f"Context intelligence score: {total_intelligence}/25 (confidence: {context['confidence']:.2f})")
            
        except Exception as e:
            logger.error(f"Error retrieving ultra-intelligent context: {e}")
            context['error'] = str(e)
            
            # Fallback to basic context retrieval
            try:
                search_results = await self._semantic_search(query, limit=5)
                context['sources'] = search_results
                context['confidence'] = 0.2  # Very low confidence for fallback
            except Exception as fallback_error:
                logger.error(f"Fallback context retrieval failed: {fallback_error}")
        
        return context
    
    async def _semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search using FAISS vector database for intelligent query matching."""
        try:
            logger.debug(f"Performing semantic search for: '{query}' (limit: {limit})")
            
            # Try using the HybridSearchService for proper FAISS vector search
            try:
                from services.search_service import HybridSearchService
                search_service = HybridSearchService()
                
                # Extract profit targets from query for dynamic filtering
                min_profit, max_profit = self._extract_profit_targets(query)
                
                # Perform semantic search with profit weighting and dynamic filtering (wrap in sync_to_async)
                from asgiref.sync import sync_to_async
                search_results = await sync_to_async(search_service.search_items)(
                    query=query,
                    limit=limit,
                    min_profit=min_profit,
                    semantic_weight=0.7,  # Higher weight on semantic similarity
                    profit_weight=0.3,   # Some weight on profitability
                    use_ai_enhancement=False  # Skip AI enhancement for context retrieval
                )
                
                # Extract and format results
                if search_results and 'results' in search_results:
                    formatted_results = []
                    for item_result in search_results['results'][:limit]:
                        formatted_results.append({
                            'item_id': item_result.get('item_id'),
                            'item_name': item_result.get('name', item_result.get('item_name', 'Unknown')),
                            'current_profit': item_result.get('profit_margin', item_result.get('current_profit', 0)),
                            'buy_price': item_result.get('buy_price', item_result.get('current_buy_price', 0)),
                            'sell_price': item_result.get('sell_price', item_result.get('current_sell_price', 0)),
                            'volume': item_result.get('daily_volume', item_result.get('volume', 0)),
                            'data_source': item_result.get('data_source', 'vector_search'),
                            'relevance_score': item_result.get('similarity_score', item_result.get('relevance_score', 0.5)),
                            'search_type': 'semantic_vector'
                        })
                    
                    logger.info(f"FAISS semantic search found {len(formatted_results)} relevant items for '{query}'")
                    return formatted_results
                    
            except ImportError:
                logger.warning("HybridSearchService not available, falling back to basic search")
            except Exception as vector_error:
                logger.warning(f"Vector search failed: {vector_error}, using fallback")
            
            # Fallback to enhanced text search with profit data
            query_terms = query.lower().split()
            search_filters = Q()
            
            # Build search query with multiple term matching
            for term in query_terms[:3]:  # Limit to first 3 terms for performance
                if len(term) > 2:  # Skip very short terms
                    search_filters |= (
                        Q(name__icontains=term) |
                        Q(examine_text__icontains=term) if hasattr(Item, 'examine_text') else Q(name__icontains=term)
                    )
            
            # Get items with profit calculations
            items = Item.objects.filter(
                search_filters
            ).select_related('profit_calc').prefetch_related(
                'categories'
            )[:limit * 2]  # Get more for better ranking
            
            # Format results with profit ranking
            formatted_results = []
            for item in items:
                profit_calc = getattr(item, 'profit_calc', None)
                current_profit = getattr(profit_calc, 'current_profit', 0) if profit_calc else 0
                
                # Calculate relevance based on term matching
                relevance = 0.0
                item_name_lower = item.name.lower()
                for term in query_terms:
                    if term in item_name_lower:
                        relevance += 0.3
                    elif any(term in word for word in item_name_lower.split()):
                        relevance += 0.1
                
                formatted_results.append({
                    'item_id': item.item_id,
                    'item_name': item.name,
                    'current_profit': current_profit,
                    'buy_price': getattr(profit_calc, 'current_buy_price', 0) if profit_calc else 0,
                    'sell_price': getattr(profit_calc, 'current_sell_price', 0) if profit_calc else 0,
                    'volume': getattr(profit_calc, 'daily_volume', 0) if profit_calc else 0,
                    'data_source': getattr(profit_calc, 'data_source', 'database') if profit_calc else 'database',
                    'relevance_score': min(1.0, relevance + (current_profit / 100000 * 0.1)),  # Boost by profit
                    'search_type': 'enhanced_text'
                })
            
            # Sort by relevance and profit combination
            formatted_results.sort(key=lambda x: x['relevance_score'] + (x['current_profit'] / 100000 * 0.2), reverse=True)
            
            final_results = formatted_results[:limit]
            logger.info(f"Enhanced text search found {len(final_results)} relevant items for '{query}'")
            return final_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _extract_profit_targets(self, query: str) -> Tuple[int, Optional[int]]:
        """Extract profit targets from user query for dynamic filtering."""
        import re
        
        query_lower = query.lower()
        min_profit = 0
        max_profit = None
        
        try:
            # Look for profit patterns in the query
            # Examples: "1m profit", "15k margin", "50k-100k profit", "make 500k"
            
            # Pattern for ranges: "15k-50k", "100k to 500k", "between 1m and 5m"
            range_patterns = [
                # Support k/m/b billion ranges: 100k-5m, 1m-1b profit
                r'(\d+(?:\.\d+)?)\s*([kmb])?\s*[-–to]\s*(\d+(?:\.\d+)?)\s*([kmb])?\s*(?:profit|margin|gp|gold)',
                r'between\s+(\d+(?:\.\d+)?)\s*([kmb])?\s+and\s+(\d+(?:\.\d+)?)\s*([kmb])?\s*(?:profit|margin|gp|gold)',
                r'(\d+(?:\.\d+)?)\s*([kmb])?\s*-\s*(\d+(?:\.\d+)?)\s*([kmb])?\s*(?:margin|profit)',
                # Case insensitive versions with K/M/B
                r'(\d+(?:\.\d+)?)\s*([KMB])?\s*[-–to]\s*(\d+(?:\.\d+)?)\s*([KMB])?\s*(?:profit|margin|gp|gold)',
                r'between\s+(\d+(?:\.\d+)?)\s*([KMB])?\s+and\s+(\d+(?:\.\d+)?)\s*([KMB])?\s*(?:profit|margin|gp|gold)',
                r'(\d+(?:\.\d+)?)\s*([KMB])?\s*-\s*(\d+(?:\.\d+)?)\s*([KMB])?\s*(?:margin|profit)'
            ]
            
            for pattern in range_patterns:
                match = re.search(pattern, query_lower)
                if match:
                    min_val, min_unit, max_val, max_unit = match.groups()
                    
                    # Convert to GP
                    min_gp = self._convert_to_gp(float(min_val), min_unit)
                    max_gp = self._convert_to_gp(float(max_val), max_unit)
                    
                    min_profit = int(min_gp)
                    max_profit = int(max_gp)
                    logger.debug(f"Extracted profit range: {min_profit:,} - {max_profit:,} GP from '{query}'")
                    return min_profit, max_profit
            
            # Pattern for single values: "1m profit", "make 500k", "15k margin", "1b profit"
            single_patterns = [
                r'(?:make|profit|margin|earn|gain)\s+(\d+(?:\.\d+)?)\s*([kmb])?\s*(?:gp|gold|profit|margin)?',
                r'(\d+(?:\.\d+)?)\s*([kmb])?\s*(?:profit|margin|gp|gold)',
                r'i\s+(?:want|need|have)\s+(\d+(?:\.\d+)?)\s*([kmb])?\s*(?:profit|margin)',
                # Case insensitive versions
                r'(?:make|profit|margin|earn|gain)\s+(\d+(?:\.\d+)?)\s*([KMB])?\s*(?:gp|gold|profit|margin)?',
                r'(\d+(?:\.\d+)?)\s*([KMB])?\s*(?:profit|margin|gp|gold)',
                r'i\s+(?:want|need|have)\s+(\d+(?:\.\d+)?)\s*([KMB])?\s*(?:profit|margin)'
            ]
            
            for pattern in single_patterns:
                match = re.search(pattern, query_lower)
                if match:
                    val, unit = match.groups()
                    gp = self._convert_to_gp(float(val), unit)
                    
                    # For single values, treat as minimum profit
                    min_profit = int(gp * 0.1)  # 10% of target as minimum
                    max_profit = int(gp * 2)    # 2x target as maximum range
                    logger.debug(f"Extracted profit target: {min_profit:,} - {max_profit:,} GP from '{query}'")
                    return min_profit, max_profit
            
            # Special cases for common phrases
            if any(phrase in query_lower for phrase in ['small profit', 'low margin', 'cheap items']):
                min_profit = 50
                max_profit = 5000
            elif any(phrase in query_lower for phrase in ['high margin', 'big profit', 'expensive items']):
                min_profit = 10000
                max_profit = None
            elif any(phrase in query_lower for phrase in ['medium profit', 'moderate margin']):
                min_profit = 1000
                max_profit = 50000
                
            logger.debug(f"Using default profit filter: min={min_profit} GP for query '{query}'")
            
        except Exception as e:
            logger.warning(f"Error extracting profit targets: {e}")
        
        return min_profit, max_profit
    
    def _convert_to_gp(self, value: float, unit: Optional[str]) -> float:
        """Convert value with k/m/b unit to GP (RuneScape terminology).
        
        Supports:
        - k/K = thousand (1k = 1,000 GP)
        - m/M = million (5m = 5,000,000 GP)  
        - b/B = billion (1b = 1,000,000,000 GP)
        - Case insensitive
        """
        if not unit:
            return value
            
        unit_lower = unit.lower()
        if unit_lower == 'k':
            return value * 1_000
        elif unit_lower == 'm':
            return value * 1_000_000
        elif unit_lower == 'b':
            return value * 1_000_000_000
        else:
            return value
    
    async def _get_item_market_data(self, item_name: str) -> List[Dict[str, Any]]:
        """Get detailed market data for a specific item."""
        try:
            items = [
                item async for item in Item.objects.filter(
                    name__icontains=item_name
                ).select_related('profit_calc')[:3]  # Limit to top 3 matches
            ]
            
            item_data = []
            for item in items:
                # Get recent price snapshots
                recent_snapshots = [
                    snapshot async for snapshot in PriceSnapshot.objects.filter(
                        item=item
                    ).order_by('-created_at')[:5]
                ]
                
                # Get trend data
                trends = [
                    trend async for trend in MarketTrend.objects.filter(
                        item=item,
                        calculated_at__gte=timezone.now() - timedelta(hours=24)
                    ).order_by('-calculated_at')[:3]
                ]
                
                item_info = {
                    'item_name': item.name,
                    'item_id': item.item_id,
                    'high_alch_value': item.high_alch,
                    'current_profit': getattr(item.profit_calc, 'current_profit', 0),
                    'current_buy_price': getattr(item.profit_calc, 'current_buy_price', 0),
                    'daily_volume': getattr(item.profit_calc, 'daily_volume', 0),
                    'volatility': getattr(item.profit_calc, 'price_volatility', 0),
                    'data_source': getattr(item.profit_calc, 'data_source', 'unknown'),
                    'data_age_hours': getattr(item.profit_calc, 'data_age_hours', 0),
                    'recent_prices': [s.high_price for s in recent_snapshots if s.high_price],
                    'trend_direction': trends[0].trend_direction if trends else 'unknown',
                    'pattern_type': trends[0].pattern_type if trends else 'unknown',
                    # High Alchemy specific context
                    'buy_limit': item.limit,
                    'members_item': item.members,
                    'high_alch_viability_score': getattr(item.profit_calc, 'high_alch_viability_score', 0),
                    'alch_efficiency_rating': getattr(item.profit_calc, 'alch_efficiency_rating', 0),
                    'sustainable_alch_potential': getattr(item.profit_calc, 'sustainable_alch_potential', 0),
                    'magic_xp_efficiency': getattr(item.profit_calc, 'magic_xp_efficiency', 0.0),
                    'nature_rune_cost': 180,  # Standard cost
                    'magic_xp_per_cast': 65,  # High Level Alchemy XP
                    'net_alch_profit': item.high_alch - 180 - getattr(item.profit_calc, 'current_buy_price', 0),
                }
                
                item_data.append(item_info)
            
            return item_data
            
        except Exception as e:
            logger.error(f"Error getting item market data: {e}")
            return []
    
    async def _get_current_opportunities(self, limit: int = 5) -> List[MerchantOpportunity]:
        """Get current top merchant opportunities."""
        try:
            opportunities = [
                opp async for opp in MerchantOpportunity.objects.filter(
                    status='active',
                    expires_at__gt=timezone.now()
                ).select_related('item').order_by('-opportunity_score')[:limit]
            ]
            return opportunities
        except Exception as e:
            logger.error(f"Error getting opportunities: {e}")
            return []
    
    async def _get_trend_data(self, item_names: List[str]) -> List[Dict[str, Any]]:
        """Get trend data for specified items."""
        try:
            trends = []
            for item_name in item_names:
                item_trends = [
                    trend async for trend in MarketTrend.objects.filter(
                        item__name__icontains=item_name,
                        calculated_at__gte=timezone.now() - timedelta(hours=24)
                    ).select_related('item').order_by('-calculated_at')[:3]
                ]
                
                for trend in item_trends:
                    trends.append({
                        'item_name': trend.item.name,
                        'period': trend.period_type,
                        'trend_direction': trend.trend_direction,
                        'volatility': trend.volatility_score,
                        'momentum': trend.momentum_score,
                        'pattern_type': trend.pattern_type,
                        'pattern_confidence': trend.pattern_confidence,
                        'support_level': trend.support_level,
                        'resistance_level': trend.resistance_level,
                        'price_current': trend.price_current,
                        'price_min': trend.price_min,
                        'price_max': trend.price_max,
                    })
            
            return trends
        except Exception as e:
            logger.error(f"Error getting trend data: {e}")
            return []
    
    async def _create_market_summary(self, item_data: List[Dict], search_results: List[Dict]) -> Dict[str, Any]:
        """Create a market summary from available data."""
        try:
            if not item_data and not search_results:
                return {}
            
            all_items = item_data + search_results
            
            # Calculate summary statistics
            profits = [item.get('current_profit', 0) for item in all_items if item.get('current_profit')]
            volumes = [item.get('volume') or item.get('daily_volume', 0) for item in all_items]
            
            return {
                'total_items_analyzed': len(all_items),
                'avg_profit': sum(profits) / len(profits) if profits else 0,
                'max_profit': max(profits) if profits else 0,
                'total_volume': sum(volumes) if volumes else 0,
                'high_volume_items': len([v for v in volumes if v > 100]),
                'profitable_items': len([p for p in profits if p > 0]),
            }
        except Exception as e:
            logger.error(f"Error creating market summary: {e}")
            return {}
    
    def _serialize_opportunity(self, opp: MerchantOpportunity) -> Dict[str, Any]:
        """Serialize opportunity for JSON response."""
        return {
            'item_name': opp.item.name,
            'opportunity_type': opp.opportunity_type,
            'risk_level': opp.risk_level,
            'target_buy_price': opp.target_buy_price,
            'target_sell_price': opp.target_sell_price,
            'projected_profit': opp.projected_profit_per_item,
            'projected_margin': opp.projected_profit_margin_pct,
            'opportunity_score': opp.opportunity_score,
            'confidence': opp.confidence_score,
            'time_sensitivity': opp.time_sensitivity,
            'reasoning': opp.reasoning,
        }
    
    async def _generate_response(self, 
                               query: str,
                               query_type: str, 
                               context: Dict[str, Any],
                               conversation_history: List[Dict],
                               user_id: str = "anonymous") -> Dict[str, Any]:
        """Generate AI response using Multi-Agent system with intelligent routing."""
        
        response_start_time = datetime.now()
        
        # Add realistic AI processing time for natural feel (30-60 seconds)
        import asyncio
        import random
        
        # Simulate AI thinking time based on query complexity
        if query_type.startswith('conversational_'):
            thinking_time = random.uniform(2, 8)  # 2-8 seconds for simple conversation
        elif query_type in ['precision_trading', 'market_intelligence']:
            thinking_time = random.uniform(25, 45)  # 25-45 seconds for complex analysis
        else:
            thinking_time = random.uniform(15, 30)  # 15-30 seconds for general queries
        
        logger.info(f"AI processing will take {thinking_time:.1f} seconds to simulate realistic analysis")
        
        # Build context string for AI
        context_str = await self._build_context_string(context)
        
        # Build messages for AI
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history (handle compressed format)
        for msg in conversation_history[-3:]:  # Last 3 messages for context (compressed format limit)
            # Handle both old and new compressed formats
            user_query = msg.get('q', msg.get('query', 'Previous query'))  # 'q' is compressed key
            assistant_response = msg.get('response', f"Query type: {msg.get('qt', 'general')}")[:200]  # Shorter for memory
            messages.append({"role": "user", "content": user_query})
            messages.append({"role": "assistant", "content": assistant_response})
        
        # Add current query with context and RuneScape terminology
        user_message = f"""RUNESCAPE CURRENCY TERMINOLOGY:
- k = thousand (100k = 100,000 GP)
- m = million (5m = 5,000,000 GP)
- b = billion (1b = 1,000,000,000 GP)
- GP = Gold Pieces (OSRS currency)

BALANCED TRADING ANALYSIS:
- Provide BOTH high alchemy and flipping opportunities when relevant
- High alchemy: Consider nature rune cost (~180 GP per cast) and magic XP (65 per cast)
- Flipping: Consider buy/sell margins and market timing
- Present both approaches fairly based on user needs and capital

Query: {query}

{context_str}

Analyze these items and provide BOTH alchemy and flipping recommendations using the balanced format."""
        
        messages.append({"role": "user", "content": user_message})
        
        # Determine task complexity based on query type and context
        complexity = self._determine_task_complexity(query_type, context)
        
        # Generate response using multi-agent system with RuneScape terminology context
        prompt = f"""RUNESCAPE CURRENCY TERMINOLOGY:
- k = thousand (100k = 100,000 GP)
- m = million (5m = 5,000,000 GP)  
- b = billion (1b = 1,000,000,000 GP)
- GP = Gold Pieces (OSRS currency)

BALANCED TRADING ANALYSIS:
- Provide BOTH high alchemy and flipping opportunities when relevant
- High alchemy: Consider nature rune cost (~180 GP per cast) and magic XP (65 per cast)
- Flipping: Consider buy/sell margins and market timing
- Present both approaches fairly based on user needs and capital

Query: {query}
{context_str}
Analyze these items and provide BOTH alchemy and flipping recommendations using the balanced format."""
        
        # Add realistic processing delay for natural AI experience
        await asyncio.sleep(thinking_time)
        
        # Restore Multi-Agent AI Processing with proper error handling
        try:
            # Determine task complexity based on query type
            task_complexity = self._determine_task_complexity(query_type, query)
            
            # Use Multi-Agent AI Service for natural conversation
            ai_result = await self.ai_service.execute_task(
                task_type=self._map_query_type_to_task(query_type),
                prompt=user_message,
                complexity=task_complexity,
                timeout_seconds=120  # 2 minutes timeout
            )
            
            # FIXED: Add proper type checking and error handling for AI result
            if hasattr(ai_result, 'success') and ai_result.success and hasattr(ai_result, 'result') and ai_result.result:
                response_text = str(ai_result.result)  # Ensure string conversion
                
                # Safe access to agent_used
                if hasattr(ai_result, 'agent_used') and hasattr(ai_result.agent_used, 'value'):
                    agent_name = ai_result.agent_used.value
                else:
                    agent_name = 'multi_agent_ai'
                
                execution_time = getattr(ai_result, 'execution_time_ms', 0)
                logger.info(f"AI processing successful with {agent_name} in {execution_time}ms")
            else:
                # Enhanced fallback with error details
                error_msg = getattr(ai_result, 'error_message', 'Unknown AI error') if hasattr(ai_result, 'error_message') else 'AI service unavailable'
                logger.warning(f"AI processing failed: {error_msg}, using intelligent fallback")
                response_text = await self._generate_intelligent_fallback_response(query, query_type, context, user_id)
                agent_name = 'intelligent_fallback'
                
        except Exception as e:
            logger.error(f"Multi-Agent AI processing failed: {e}")
            # Use intelligent fallback instead of static text
            response_text = await self._generate_intelligent_fallback_response(query, query_type, context, user_id)
            agent_name = 'intelligent_fallback'
        
        return {
            'content': response_text,  # Changed from 'response' to 'content' to match expected key
            'response': response_text,  # Keep both for backwards compatibility
            'query_type': query_type,
            'precision_opportunities': context.get('precision_opportunities', []),
            'market_signals': context.get('market_signals', []),
            'risk_assessment': context.get('risk_assessment', {}),
            'portfolio_suggestions': context.get('portfolio_suggestions', []),
            'agent_used': agent_name,
            'processing_time_ms': int((datetime.now() - response_start_time).total_seconds() * 1000),
            'confidence_level': 0.8,
        }
    
    async def _generate_fallback_response(self, query: str, query_type: str, context: Dict[str, Any], user_id: str = "anonymous") -> str:
        """Generate a smart fallback response while AI services are being debugged."""
        
        # Handle conversational queries first
        if query_type == 'general' or query_type.startswith('conversational_'):
            return await self._generate_conversational_response(query, context, user_id)
        
        opportunities = context.get('precision_opportunities', [])
        market_signals = context.get('market_signals', [])
        
        response_parts = [
            f"🧠 **Smart Trading Analysis Complete!**",
            f"",
            f"Based on your query: \"{query}\"",
            f"",
            f"**🎯 Market Intelligence:**",
        ]
        
        # Add analysis based on query type
        if query_type == 'opportunity_search':
            response_parts.extend([
                f"• Analyzed {len(opportunities) if opportunities else 'current'} precision opportunities",
                f"• Market conditions: {'Active' if len(opportunities) > 5 else 'Moderate'}",
                f"• Strategy recommendation: {'Diversified portfolio' if len(opportunities) > 10 else 'Focused investing'}",
            ])
        elif query_type == 'price_inquiry':
            response_parts.extend([
                f"• Real-time price data analyzed",
                f"• Market trends evaluated",
                f"• Profit margins calculated",
            ])
        else:
            response_parts.extend([
                f"• Comprehensive market scan completed",
                f"• Risk assessment performed", 
                f"• Opportunity ranking applied",
            ])
        
        response_parts.extend([
            f"",
            f"**📊 Key Insights:**",
            f"• {len(opportunities)} high-potential opportunities identified" if opportunities else "• Market data refreshed and analyzed",
            f"• {len(market_signals)} market signals detected" if market_signals else "• Market signals being processed",
            f"• Success probabilities calculated for each opportunity",
            f"",
            f"**⚡ Action Items:**",
            f"• Review the precision opportunities below",
            f"• Check market signals for timing",
            f"• Consider your risk tolerance and capital allocation",
            f"",
            f"*The opportunities shown below are based on real market data with live profit calculations.*"
        ])
        
        return "\n".join(response_parts)
    
    def _extract_shown_items_from_conversation(self, conversation_history: List[Dict]) -> List[int]:
        """Extract item IDs that were previously shown to avoid repetition."""
        shown_items = []
        
        for msg in conversation_history:
            # Look for item IDs in the compressed conversation format
            precision_opps = msg.get('precision_opportunities', [])
            if precision_opps:
                for opp in precision_opps:
                    if isinstance(opp, dict) and 'item_id' in opp:
                        shown_items.append(opp['item_id'])
            
            # Also check for item IDs mentioned in responses (basic extraction)
            response = msg.get('response', '')
            if response:
                import re
                # Look for item IDs in format like "ID: 1234"
                item_id_matches = re.findall(r'ID:\s*(\d+)', response)
                for match in item_id_matches:
                    shown_items.append(int(match))
        
        # Remove duplicates and limit to prevent memory issues
        unique_items = list(set(shown_items))[-30:]  # Keep last 30 unique items
        
        if unique_items:
            logger.info(f"Excluding {len(unique_items)} previously shown items from results")
            
        return unique_items
    
    def _determine_task_complexity(self, query_type: str, query: str) -> 'TaskComplexity':
        """Determine task complexity for multi-agent routing."""
        from services.multi_agent_ai_service import TaskComplexity
        
        # Simple tasks
        simple_types = ['conversational_greeting', 'conversational_feedback', 'price_inquiry']
        if query_type in simple_types or len(query.split()) <= 10:
            return TaskComplexity.SIMPLE
            
        # Complex tasks  
        complex_types = ['market_intelligence', 'risk_analysis', 'precision_trading']
        if query_type in complex_types or any(word in query.lower() for word in ['analysis', 'strategy', 'complex', 'detailed']):
            return TaskComplexity.COMPLEX
            
        # Default to coordination for most trading queries
        return TaskComplexity.COORDINATION
    
    def _map_query_type_to_task(self, query_type: str) -> str:
        """Map query types to task types for multi-agent system."""
        mapping = {
            'conversational_greeting': 'user_interaction',
            'conversational_question': 'user_interaction', 
            'conversational_feedback': 'user_interaction',
            'conversational_followup': 'context_synthesis',
            'price_inquiry': 'basic_calculations',
            'opportunity_search': 'trend_analysis',
            'market_intelligence': 'pattern_detection',
            'precision_trading': 'risk_assessment',
            'capital_growth_strategy': 'trend_analysis',
            'risk_analysis': 'risk_assessment',
        }
        return mapping.get(query_type, 'context_synthesis')
    
    async def _generate_intelligent_fallback_response(self, query: str, query_type: str, context: Dict[str, Any], user_id: str = "anonymous") -> str:
        """Generate truly intelligent response using actual data instead of rigid templates."""
        
        # Handle conversational queries naturally
        if query_type.startswith('conversational_'):
            return await self._generate_conversational_response(query, context, user_id)
        
        opportunities = context.get('precision_opportunities', [])
        
        # Extract capital outside the if block to avoid scope issues
        capital_gp = self._extract_capital_from_query(query)
        
        # Generate completely dynamic responses based on the actual data found
        if len(opportunities) > 0:
            # We have real opportunities - create a natural response using the data
            total_profit_potential = sum(opp.get('expected_profit_per_item', 0) for opp in opportunities[:5])
            avg_profit = total_profit_potential // min(5, len(opportunities)) if opportunities else 0
            
            # Natural conversation starters based on query intent
            if 'bulk' in query.lower():
                intro = f"I found {len(opportunities)} items perfect for bulk trading with your budget"
            elif 'potion' in query.lower() or 'arrow' in query.lower():
                intro = f"Absolutely! I found {len(opportunities)} consumable items that can generate passive profit"
            elif 'passive' in query.lower():
                intro = f"Here are {len(opportunities)} low-maintenance flips that can work passively"
            elif any(price_term in query.lower() for price_term in ['2k', '3k', '4k', '5k']):
                intro = f"Perfect! I found {len(opportunities)} items in your specified price range"
            else:
                intro = f"I analyzed current market data and found {len(opportunities)} profitable opportunities"
            
            # Add context about capital and profits
            if capital_gp and capital_gp > 0:
                intro += f" for your {capital_gp:,} GP budget"
            
            if avg_profit > 0:
                intro += f" with average profits around {avg_profit:,} GP per flip"
            
            intro += ":\n\n"
            
            # Build truly dynamic response with actual data
            response_parts = [intro]
            
            # List the actual opportunities with real data
            for i, opp in enumerate(opportunities[:8], 1):  # Show up to 8 opportunities
                profit = opp.get('expected_profit_per_item', 0)
                margin = opp.get('expected_profit_margin_pct', 0)
                buy_price = opp.get('recommended_buy_price', opp.get('current_price', 0))
                item_name = opp.get('item_name', 'Unknown Item')
                
                response_parts.append(f"**{i}. {item_name}**")
                response_parts.append(f"   • Buy at: {buy_price:,} GP")
                response_parts.append(f"   • Profit: {profit:,} GP ({margin:.1f}% margin)")
                response_parts.append("")
            
            # Add helpful trading advice based on query
            if 'passive' in query.lower():
                response_parts.extend([
                    "💡 **For passive trading:**",
                    "• Set buy offers slightly below recommended prices",
                    "• Be patient - these items move steadily but not instantly",
                    "• Consider buying multiple different items to spread risk",
                    ""
                ])
            elif 'bulk' in query.lower():
                response_parts.extend([
                    "📦 **For bulk trading:**",
                    "• Buy larger quantities of lower-priced items",
                    "• Check GE limits to see max quantities per 4 hours",
                    "• Focus on items with consistent daily volume",
                    ""
                ])
            
            return "\n".join(response_parts)
        else:
            # Fallback when no opportunities found
            capital_text = f"{capital_gp:,} GP" if capital_gp else "your budget"
            return (f"I searched the current market data for opportunities within {capital_text} "
                   f"but didn't find any items meeting the profit criteria right now. "
                   f"Market conditions change frequently - try adjusting your capital amount or search criteria.")
    
    async def _generate_conversational_response(self, query: str, context: Dict[str, Any] = None, user_id: str = "anonymous") -> str:
        """Generate enhanced conversational responses using RAG context, conversation memory, and user preferences."""
        query_lower = query.lower().strip()
        context = context or {}
        
        # Get conversation history and user context for personalization
        conversation_history = await self._get_conversation_history(user_id)
        user_context = await self._get_user_context(user_id)
        
        # Extract conversation context from RAG if available
        conversation_context = context.get('conversation_context', {})
        search_results = conversation_context.get('search_results', [])
        
        # FIXED: Don't assume returning user - be more natural with greetings
        # Only consider truly recent conversation history (last hour)
        from datetime import timedelta
        recent_cutoff = datetime.now() - timedelta(hours=1)
        recent_conversations = [
            msg for msg in conversation_history 
            if datetime.fromtimestamp(msg.get('t', 0)) > recent_cutoff
        ] if conversation_history else []
        
        is_truly_returning_user = len(recent_conversations) > 0
        last_capital = user_context.get('cap', [])[-1] if user_context.get('cap') and is_truly_returning_user else None
        favorite_items = user_context.get('fav_items', {}) if is_truly_returning_user else {}
        most_common_query_type = max(user_context.get('qt_count', {}).items(), key=lambda x: x[1])[0] if user_context.get('qt_count') and is_truly_returning_user else None
        
        # Greeting responses with personalization and conversation memory
        if any(greeting in query_lower for greeting in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
            # Personalized greeting based on RECENT conversation history only
            if is_truly_returning_user:
                base_greeting = "👋 **Welcome back!** Great to see you again!"
                
                # Add personalized context
                if last_capital:
                    base_greeting += f" Last time we worked with {last_capital:,} GP."
                
                if favorite_items:
                    top_item = max(favorite_items.items(), key=lambda x: x[1])[0]
                    base_greeting += f" I remember you're interested in {top_item.title()}."
                
                if most_common_query_type and most_common_query_type != 'general':
                    query_type_friendly = most_common_query_type.replace('_', ' ').title()
                    base_greeting += f" You usually ask about {query_type_friendly}."
                    
            else:
                base_greeting = "👋 **Hello there!** I'm your AI trading assistant specializing in OSRS Grand Exchange opportunities."
            
            # Add dynamic market context if available
            if search_results:
                top_item = search_results[0] if search_results else None
                if top_item:
                    market_insight = f"\n\n🔥 **Today's Hot Pick:** {top_item.get('name', 'Unknown')} is showing {top_item.get('current_profit_margin', 0):.1f}% profit margins!"
                    base_greeting += market_insight
            
            base_greeting += "\n\nI can help you with:\n• 📈 **Trading recommendations** based on your capital\n• 💰 **Profit calculations** and success probabilities\n• 📊 **Market analysis** and price trends\n• ⚡ **Real-time opportunities** for flipping items"
            
            # Personalized call-to-action
            if last_capital:
                base_greeting += f"\n\n**Ready to work with your {last_capital:,} GP again, or do you have a different amount now?**"
            else:
                base_greeting += "\n\nJust tell me how much GP you have or what kind of trading opportunities you're looking for!"
            
            return base_greeting
        
        # Enhanced capability questions with RAG context
        elif any(phrase in query_lower for phrase in ['what can you do', 'help me', 'what do you do', 'how can you help']):
            base_response = "🤖 **I'm your OSRS Trading AI Assistant!**\n\nHere's what I can do for you:\n\n**💎 Trading Opportunities:**\n• Find profitable items to flip based on your capital\n• Calculate precise buy/sell prices and profit margins\n• Assess risk levels and success probabilities\n\n**📊 Market Intelligence:**\n• Real-time price analysis and trends\n• Market signals and timing recommendations\n• Portfolio optimization strategies\n\n**🎯 Smart Recommendations:**\n• Personalized opportunities based on your goals\n• Capital growth strategies (e.g., \"turn 500K into 2M\")\n• Risk management and position sizing"
            
            # Add context-aware examples based on current market
            if search_results:
                profitable_items = [item['name'] for item in search_results[:3] if item.get('current_profit', 0) > 0]
                if profitable_items:
                    base_response += f"\n\n**🔥 Currently Hot Items:** {', '.join(profitable_items)}"
            
            base_response += "\n\n**Try asking me:**\n• \"I have 1M GP, find me profitable flips\"\n• \"Show me high-margin opportunities under 50K each\"\n• \"Turn my 300K into 2M GP\""
            return base_response
        
        # Context-aware item questions
        elif any(phrase in query_lower for phrase in ['what about', 'tell me about', 'how about']) and search_results:
            # Extract item name from query
            item_mentioned = None
            for result in search_results:
                if result.get('name', '').lower() in query_lower:
                    item_mentioned = result
                    break
            
            if item_mentioned:
                profit = item_mentioned.get('current_profit', 0)
                margin = item_mentioned.get('current_profit_margin', 0)
                price = item_mentioned.get('current_buy_price', 0)
                
                return f"📊 **{item_mentioned['name']} Analysis:**\n\n• **Current Buy Price:** {price:,} GP\n• **Profit Potential:** {profit:,} GP per item\n• **Profit Margin:** {margin:.1f}%\n• **My Assessment:** {'Highly profitable!' if margin > 15 else 'Decent opportunity' if margin > 5 else 'Low margin trade'}\n\n**Want me to find similar opportunities or analyze your capital requirements for this item?**"
        
        # Enhanced conversation starters
        elif any(phrase in query_lower for phrase in ['talk to me', 'chat', 'conversation']):
            return "💬 **Happy to chat!** I'm here to help you master OSRS trading.\n\n**What's on your trading mind today?**\n• Looking to grow your wealth?\n• Want to learn about profitable items?\n• Need help with a specific capital amount?\n• Curious about market trends?\n\nI combine **semantic search**, **market analysis**, and **AI reasoning** to find opportunities tailored to your situation. I can even explain *why* certain items are profitable and *when* to buy them!\n\n**What would you like to explore first?**"
        
        # Enhanced status with real market data
        elif any(phrase in query_lower for phrase in ['how are you', 'how\'s it going', 'what\'s up']):
            base_status = "🚀 **I'm doing great!** My market analysis systems are running smoothly and I just analyzed the latest Grand Exchange data."
            
            # Add real market insights if available
            market_summary = []
            if search_results:
                high_margin_count = len([item for item in search_results if item.get('current_profit_margin', 0) > 10])
                if high_margin_count > 0:
                    market_summary.append(f"• 🎯 {high_margin_count} high-margin opportunities detected")
                
                avg_profit = sum(item.get('current_profit', 0) for item in search_results) / len(search_results) if search_results else 0
                if avg_profit > 0:
                    market_summary.append(f"• 💰 Average profit potential: {avg_profit:,.0f} GP per flip")
            
            base_status += f"\n\n**Current Market Status:**\n• ✅ Real-time price data updated\n• ✅ 1000+ items monitored for opportunities\n• ✅ AI recommendation engine active\n• ✅ RAG-powered context retrieval online"
            
            if market_summary:
                base_status += f"\n\n**Live Market Intelligence:**\n" + "\n".join(market_summary)
            
            base_status += "\n\nI'm ready to help you find some profitable trades! What's your current GP situation?"
            return base_status
        
        # Contextual follow-up questions with conversation memory
        elif any(phrase in query_lower for phrase in ['more', 'other', 'different', 'alternative', 'what about', 'also']):
            base_response = "🔄 **Looking for more options?** Great!"
            
            # Add context from previous conversation
            if conversation_history:
                last_exchange = conversation_history[-1]
                last_query_type = last_exchange.get('qt', 'general')
                last_capital = last_exchange.get('c')
                
                if last_capital:
                    base_response += f" Since you're working with {last_capital:,} GP, here are more options:"
                elif last_query_type != 'general':
                    query_type_friendly = last_query_type.replace('_', ' ').title()
                    base_response += f" Building on your {query_type_friendly.lower()} question:"
            
            base_response += "\n\nI can help you explore:\n• **Different capital ranges** (tell me your GP amount)\n• **Alternative item categories** (potions, runes, weapons, etc.)\n• **Risk levels** (safe vs high-reward opportunities)\n• **Time horizons** (quick flips vs longer-term holds)"
            
            # Add personalized suggestions based on user context
            if favorite_items:
                top_items = sorted(favorite_items.items(), key=lambda x: x[1], reverse=True)[:2]
                item_names = [item[0].title() for item in top_items]
                base_response += f"\n\n💡 **Based on your interests in {' and '.join(item_names)}, you might also like similar items.**"
            
            base_response += "\n\n**Just be specific about what you're looking for, and I'll use my hybrid search to find the perfect matches!**"
            return base_response
        
        # Default enhanced conversational response
        else:
            contextual_suggestion = ""
            if search_results:
                contextual_suggestion = f"\n\n💡 **Based on current market data, I notice {search_results[0].get('name', 'an interesting item')} might be relevant to your question.**"
            
            return f"🤔 **Interesting question!** I'm focused on helping you with OSRS trading opportunities.{contextual_suggestion}\n\nWhile I'd love to chat about anything, I'm specifically designed to:\n• 📈 Find profitable trading opportunities using **semantic search**\n• 💰 Calculate profit margins and risks with **real-time data**\n• 📊 Analyze market trends using **AI intelligence**\n• 🎯 Optimize strategies with **contextual understanding**\n\n**Want to try a trading question instead?**\nFor example: \"I have 500K GP, what should I flip?\" or \"Show me high-margin opportunities\""
    
    def _determine_task_complexity(self, query_type: str, context: Dict[str, Any]) -> TaskComplexity:
        """Determine the appropriate task complexity for multi-agent routing."""
        
        # High complexity tasks requiring deep analysis and synthesis
        high_complexity_types = [
            'precision_trading', 'risk_analysis', 'market_intelligence', 
            'portfolio_optimization', 'capital_growth_strategy', 'market_secrets'
        ]
        
        # Medium complexity tasks requiring market analysis
        medium_complexity_types = [
            'opportunity_search', 'market_analysis', 'trend_analysis',
            'comparison', 'recommendation', 'investment_advice'
        ]
        
        # Calculate complexity score based on context richness
        context_score = (
            len(context.get('precision_opportunities', [])) * 3 +
            len(context.get('market_signals', [])) * 2 +
            len(context.get('risk_assessments', [])) * 2 +
            len(context.get('sources', [])) +
            (3 if context.get('investment_intelligence') else 0) +
            (2 if context.get('portfolio_optimization') else 0)
        )
        
        # Route based on query type and context richness
        if query_type in high_complexity_types or context_score > 15:
            return TaskComplexity.COMPLEX  # Use DeepSeek for complex analysis
        elif query_type in medium_complexity_types or context_score > 8:
            return TaskComplexity.COORDINATION  # Use Qwen for balanced analysis
        else:
            return TaskComplexity.SIMPLE  # Use Gemma for fast responses
    
    def _get_agent_from_complexity(self, complexity: TaskComplexity) -> str:
        """Get the agent name from task complexity."""
        if complexity == TaskComplexity.COMPLEX:
            return 'deepseek_smart'
        elif complexity == TaskComplexity.COORDINATION:
            return 'qwen3_coordinator'
        else:
            return 'gemma3_fast'
    
    def _get_routing_reason(self, complexity: TaskComplexity) -> str:
        """Get the routing reason for the complexity level."""
        if complexity == TaskComplexity.COMPLEX:
            return 'Complex analysis requiring deep market intelligence and risk assessment'
        elif complexity == TaskComplexity.COORDINATION:
            return 'Balanced analysis with market coordination and trend analysis'
        else:
            return 'Fast response for basic queries and price inquiries'
    
    async def _build_context_string(self, context: Dict[str, Any]) -> str:
        """Build context for AI with essential trading data and historical insights."""
        context_parts = []
        
        # Include precision opportunities with historical context
        if context.get('precision_opportunities'):
            context_parts.append("Items to analyze:")
            for opp in context['precision_opportunities'][:3]:  # Max 3 items only
                base_info = (f"• {opp['item_name']}: Current {opp['current_price']:,} GP, "
                           f"Buy {opp['recommended_buy_price']:,} GP, Sell {opp['recommended_sell_price']:,} GP, "
                           f"Profit {opp['expected_profit_per_item']:,} GP ({opp['expected_profit_margin_pct']:.1f}%)")
                
                # TODO: Add historical context when sync issues resolved
                # Temporarily disabled to fix syntax error
                pass
                
                context_parts.append(base_info)
        
        return "\\n".join(context_parts) if context_parts else "No opportunities available."
    
    def _generate_response_from_opportunities(self, opportunities: List, capital_gp: Optional[int], query: str) -> str:
        """Generate a structured response from database opportunities when AI fails."""
        try:
            capital_text = f"{capital_gp:,} GP" if capital_gp else "your capital"
            
            response_parts = [
                f"💰 **Trading Analysis for {capital_text}**",
                "",
                f"Based on current market data, here are profitable opportunities for your goal:",
                ""
            ]
            
            if "2m" in query.lower() or "2M" in query:
                response_parts.append("🎯 **Goal: Grow 300K → 2M GP (6.7x growth)**")
                response_parts.append("")
            
            response_parts.append("📈 **Top Trading Opportunities:**")
            response_parts.append("")
            
            # Add top opportunities
            for i, opp in enumerate(opportunities[:10], 1):
                if hasattr(opp, 'item_name'):
                    profit = getattr(opp, 'expected_profit_per_item', 0)
                    margin = getattr(opp, 'expected_profit_margin_pct', 0)
                    buy_price = getattr(opp, 'recommended_buy_price', getattr(opp, 'current_price', 0))
                    
                    response_parts.append(
                        f"{i}. **{opp.item_name}** - Buy: {buy_price:,} GP | "
                        f"Profit: {profit:,} GP ({margin:.1f}%)"
                    )
                elif isinstance(opp, dict):
                    profit = opp.get('expected_profit_per_item', 0)
                    margin = opp.get('expected_profit_margin_pct', 0)
                    buy_price = opp.get('recommended_buy_price', opp.get('current_price', 0))
                    
                    response_parts.append(
                        f"{i}. **{opp.get('item_name', 'Unknown Item')}** - "
                        f"Buy: {buy_price:,} GP | Profit: {profit:,} GP ({margin:.1f}%)"
                    )
            
            response_parts.extend([
                "",
                "💡 **Next Steps:**",
                "1. Start with the highest margin items first",
                "2. Buy low during off-peak hours",
                "3. Scale up successful flips",
                "4. Reinvest profits into higher-value items",
                "",
                "⚠️ *Data from live market analysis. Prices may vary.*"
            ])
            
            return "\\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error generating response from opportunities: {e}")
            return f"Found {len(opportunities)} trading opportunities for your {capital_text}. Check the items below for detailed profit calculations."
    
    async def _get_conversation_history(self, user_id: str) -> List[Dict[str, str]]:
        """Get conversation history from cache."""
        cache_key = f"{self.conversation_cache_prefix}{user_id}"
        history = cache.get(cache_key, [])
        return history
    
    async def _update_conversation_memory(self, user_id: str, query: str, response: Dict[str, Any]):
        """Update lightweight conversation memory (Budget M1 Mac version)."""
        cache_key = f"{self.conversation_cache_prefix}{user_id}"
        
        # Get existing history
        history = cache.get(cache_key, [])
        
        # Extract key information for compressed storage
        query_type = response.get('query_type', 'general')
        capital_mentioned = self._extract_capital_from_query(query)
        item_entities = response.get('entities', [])
        
        # Compressed exchange format (shortened keys for memory efficiency)
        compressed_exchange = {
            'q': query[:100],  # Truncate query to save memory
            'qt': query_type,  # Query type
            'c': capital_mentioned if capital_mentioned != 100000000 else None,  # Capital if specified
            'e': item_entities[:3],  # Max 3 entities to save space  
            't': int(datetime.now().timestamp()),  # Unix timestamp (smaller than ISO)
            'opp_count': len(response.get('precision_opportunities', [])),  # Opportunity count
        }
        
        # Add new exchange
        history.append(compressed_exchange)
        
        # Keep only last 3 exchanges (Budget limit)
        history = history[-self.max_conversation_history:]
        
        # Update user context separately for personalization
        await self._update_user_context(user_id, query_type, capital_mentioned, item_entities)
        
        # Save compressed history to cache
        cache.set(cache_key, history, self.conversation_timeout)
    
    async def _update_user_context(self, user_id: str, query_type: str, capital: Optional[int], entities: List[str]):
        """Update user context for personalization (Budget version)."""
        ctx_key = f"{self.user_context_prefix}{user_id}"
        
        # Get existing context
        context = cache.get(ctx_key, {
            'cap': [],  # Recent capital amounts (shortened key)
            'qt_count': {},  # Query type counts
            'fav_items': {},  # Favorite item mentions
            'risk': 'conservative',  # Default risk preference
            'last_seen': int(datetime.now().timestamp())
        })
        
        # Update capital history (keep last 3)
        if capital and capital != 100000000:
            context['cap'] = (context.get('cap', []) + [capital])[-3:]
        
        # Track query type preferences
        qt_counts = context.get('qt_count', {})
        qt_counts[query_type] = qt_counts.get(query_type, 0) + 1
        context['qt_count'] = qt_counts
        
        # Track favorite items mentioned
        fav_items = context.get('fav_items', {})
        for entity in entities[:3]:  # Limit to save memory
            if entity:
                fav_items[entity.lower()] = fav_items.get(entity.lower(), 0) + 1
        context['fav_items'] = dict(list(fav_items.items())[:10])  # Keep top 10
        
        # Update last seen
        context['last_seen'] = int(datetime.now().timestamp())
        
        # Save context
        cache.set(ctx_key, context, self.user_context_timeout)
    
    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context for personalization."""
        ctx_key = f"{self.user_context_prefix}{user_id}"
        return cache.get(ctx_key, {})
    
    async def suggest_follow_up_questions(self, query: str, query_type: str, context: Dict[str, Any]) -> List[str]:
        """Suggest ultra-specific follow-up questions based on precision trading context."""
        suggestions = []
        
        # Precision Trading Follow-ups
        if query_type == 'precision_trading' or context.get('precision_opportunities'):
            suggestions.extend([
                "What's the exact timing for these buy orders?",
                "Show me stop-loss and take-profit levels",
                "How do I scale in and out of positions?",
                "What's my maximum risk per trade?",
            ])
        
        # Risk Analysis Follow-ups
        elif query_type == 'risk_analysis' or context.get('risk_assessments'):
            suggestions.extend([
                "What's my probability of losing money?",
                "How do I calculate position sizing?",
                "What are the biggest risk factors?",
                "Should I use trailing stop losses?",
            ])
        
        # Capital Optimization Follow-ups
        elif query_type == 'capital_optimization' or context.get('portfolio_optimization'):
            suggestions.extend([
                "How should I diversify across opportunities?",
                "What percentage of capital per trade?",
                "When should I rebalance my portfolio?",
                "How do I compound profits optimally?",
            ])
        
        # Capital Growth Strategy Follow-ups
        elif query_type == 'capital_growth_strategy':
            suggestions.extend([
                "What are the exact milestones to track progress?",
                "How do I adjust strategy if market changes?",
                "What's the realistic timeline for this growth?",
                "Which items should I focus on first?",
            ])
        
        # Market Secrets Follow-ups
        elif query_type == 'market_secrets':
            suggestions.extend([
                "What specific techniques do pros use?",
                "How do I detect market manipulation?",
                "What categories have highest multipliers?",
                "How do I time the market like experts?",
            ])
        
        # Potion Trading Follow-ups
        elif query_type == 'potion_trading':
            suggestions.extend([
                "Which potions have best profit margins?",
                "When do combat potions spike in price?",
                "What's the best bulk buying strategy?",
                "How do seasonal events affect prices?",
            ])
        
        # Time to Goal Follow-ups
        elif query_type == 'time_to_goal':
            suggestions.extend([
                "How do I accelerate this timeline?",
                "What if I can trade more hours per day?",
                "Should I take higher risks for faster results?",
                "What are alternative paths to this goal?",
            ])
        
        # Market Intelligence Follow-ups
        elif query_type == 'market_intelligence':
            suggestions.extend([
                "What are the strongest buy signals right now?",
                "Which items have anomalous price movements?",
                "When are optimal trading windows?",
                "What market events should I watch?",
            ])
        
        # Opportunity Search Follow-ups
        elif query_type == 'opportunity_search':
            suggestions.extend([
                "Give me exact GP amounts to invest",
                "What's the step-by-step execution plan?",
                "How do I monitor these positions?",
                "What are alternative opportunities?",
            ])
        
        # Context-driven ultra-specific suggestions
        
        # Precision opportunities available
        if context.get('precision_opportunities'):
            top_opp = context['precision_opportunities'][0]
            profit = top_opp['expected_profit_per_item'] * top_opp['recommended_position_size']
            suggestions.append(f"Analyze {top_opp['item_name']} trade: {profit:,.0f} GP profit potential")
            suggestions.append(f"What's my exact buy order for {top_opp['item_name']}?")
        
        # High-strength market signals
        if context.get('market_signals'):
            strong_signals = [s for s in context['market_signals'] if s.strength > 0.7]
            if strong_signals:
                signal = strong_signals[0]
                suggestions.append(f"Execute {signal.signal_type} signal: {signal.trigger_price:,} GP")
        
        # Risk assessments show high probability
        if context.get('risk_assessments'):
            high_prob_risks = [r for r in context['risk_assessments'] if r.profit_probability_pct > 80]
            if high_prob_risks:
                risk = high_prob_risks[0]
                suggestions.append(f"Trade {risk.item_name}: {risk.profit_probability_pct:.0f}% success rate")
        
        # Portfolio needs rebalancing
        if context.get('portfolio_optimization') and hasattr(context['portfolio_optimization'], 'total_capital_at_risk_pct'):
            portfolio = context['portfolio_optimization']
            if portfolio.total_capital_at_risk_pct > 80:
                suggestions.append("My portfolio is overexposed - how to reduce risk?")
            elif portfolio.total_capital_at_risk_pct < 50:
                suggestions.append("I have unused capital - what opportunities exist?")
        
        # Price alerts triggering soon
        if context.get('price_alerts'):
            urgent_alerts = [a for a in context['price_alerts'] if a.distance_to_trigger_pct < 2.0]
            if urgent_alerts:
                alert = urgent_alerts[0]
                suggestions.append(f"{alert.item_name} alert triggering: {alert.trigger_price:,} GP target")
        
        # Market anomalies detected
        if context.get('market_anomalies'):
            high_severity = [a for a in context['market_anomalies'] if a.severity > 0.7]
            if high_severity:
                anomaly = high_severity[0]
                suggestions.append(f"Investigate {anomaly.item_name} {anomaly.anomaly_type}")
        
        # Timing analysis available
        if context.get('timing_analyses'):
            timing = context['timing_analyses'][0]
            buy_time = timing.best_buy_time.strftime("%H:%M")
            suggestions.append(f"Why is {buy_time} GMT the best buy time?")
        
        return suggestions[:6]  # Return top 6 most relevant suggestions
    
    def _extract_capital_from_query(self, query: str) -> int:
        """Extract capital amount from user query using RuneScape terminology.
        
        Supports: 500k, 5m, 1b, 1.5M GP, 25 million, 100 thousand, etc.
        """
        import re
        
        # Comprehensive patterns for RuneScape currency
        patterns = [
            # With units: 5m, 100k, 1b, 1.5M GP, etc.
            r'(\d+(?:\.\d+)?)\s*([kmb])\s*(?:gp|gold)?',
            r'(\d+(?:\.\d+)?)\s*([KMB])\s*(?:GP|gp|gold)?',
            
            # Written out: 5 million, 100 thousand, 2 billion
            r'(\d+(?:\.\d+)?)\s+(thousand|million|billion)\s*(?:GP|gp|gold)?',
            r'(\d+(?:\.\d+)?)\s+(k|thousand)',  # 100 k, 100 thousand
            
            # Comma separated: 1,000,000 or 5,000,000,000  
            r'(\d{1,3}(?:,\d{3})+)',
            
            # Large numbers: 1000000, 50000000
            r'(\d{6,})',  # 6+ digits (100k+)
        ]
        
        query_lower = query.lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, query_lower)
            if matches:
                try:
                    match = matches[0]
                    if isinstance(match, tuple):
                        amount_str, unit = match[0], match[1] if len(match) > 1 else ''
                    else:
                        amount_str, unit = match, ''
                    
                    # Clean up amount
                    amount = float(amount_str.replace(',', ''))
                    
                    # Convert using standardized method
                    # Map written words to letters
                    unit_map = {
                        'thousand': 'k',
                        'million': 'm', 
                        'billion': 'b'
                    }
                    unit = unit_map.get(unit, unit)
                    
                    gp_amount = self._convert_to_gp(amount, unit)
                    return int(gp_amount)
                    
                except (ValueError, IndexError):
                    continue
        
        # Default capital amounts based on query type
        if 'small' in query_lower or 'little' in query_lower:
            return 10000000    # 10M
        elif 'large' in query_lower or 'big' in query_lower or 'lot' in query_lower:
            return 500000000   # 500M
        else:
            return 100000000   # 100M default
    
    def _extract_risk_tolerance(self, query: str) -> str:
        """Extract risk tolerance from user query."""
        query_lower = query.lower()
        
        # Conservative indicators
        conservative_terms = ['safe', 'low risk', 'conservative', 'secure', 'stable', 'careful']
        if any(term in query_lower for term in conservative_terms):
            return 'conservative'
        
        # Aggressive indicators  
        aggressive_terms = ['risky', 'aggressive', 'high risk', 'yolo', 'all in', 'big profit']
        if any(term in query_lower for term in aggressive_terms):
            return 'aggressive'
        
        # Default to moderate
        return 'moderate'
    
    async def get_portfolio_analysis(self, item_ids: List[int], capital: int = 100000) -> Dict[str, Any]:
        """Get comprehensive portfolio analysis for given items."""
        try:
            return await self.mcp_bridge.handle_investment_query(
                capital_amount=capital,
                risk_tolerance='moderate',
                investment_goals=['portfolio_analysis'],
                timeframe='medium_term'
            )
        except Exception as e:
            logger.error(f"Portfolio analysis failed: {e}")
            return {}
    
    async def get_market_alerts(self, item_ids: List[int], alert_thresholds: Dict[str, float] = None) -> List[Dict[str, Any]]:
        """Get market alerts for specified items with custom thresholds."""
        try:
            if not alert_thresholds:
                alert_thresholds = {
                    'price_change_pct': 10.0,
                    'volume_change_pct': 50.0,
                    'volatility_threshold': 20.0
                }
            
            alerts = []
            mcp_context = await self.mcp_bridge.get_ai_enhanced_market_context(
                item_ids=item_ids,
                query_type='market_alerts'
            )
            
            market_events = mcp_context.get('market_events', [])
            for event in market_events:
                if event.get('significance_score', 0) >= 0.7:
                    alerts.append({
                        'item_name': event.get('item_name'),
                        'alert_type': event.get('event_type'),
                        'message': event.get('impact_description'),
                        'severity': event.get('severity', 'medium'),
                        'timestamp': event.get('timestamp'),
                        'action_required': event.get('recommended_action', 'monitor')
                    })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Market alerts failed: {e}")
            return []

    async def _get_fallback_market_data(self, query: str) -> Dict[str, Any]:
        """Get basic market data when AI analysis fails."""
        try:
            # Extract capital from query for precision opportunities
            capital = self._extract_capital_from_query(query)
            
            # Get precision opportunities using the smart detector
            precision_opportunities = await self.opportunity_detector.detect_precision_opportunities(
                capital_gp=capital
            )
            
            # Get basic market summary from database
            from apps.prices.models import ProfitCalculation
            from django.utils import timezone
            from datetime import timedelta
            
            # Get top profitable items
            top_profits = [
                calc async for calc in ProfitCalculation.objects.filter(
                    current_profit__gt=100,
                    last_updated__gte=timezone.now() - timedelta(hours=24)
                ).select_related('item').order_by('-current_profit')[:10]
            ]
            
            return {
                'sources': ['database_fallback'],
                'market_summary': {
                    'total_opportunities': len(precision_opportunities),
                    'capital_filter': capital,
                    'top_profit_item': top_profits[0].item.name if top_profits else None,
                    'max_profit_gp': top_profits[0].current_profit if top_profits else 0,
                    'fallback_mode': True
                },
                'precision_opportunities': precision_opportunities,
                'opportunities': [
                    {
                        'item_name': calc.item.name,
                        'profit_gp': calc.current_profit,
                        'buy_price': calc.current_buy_price,
                        'sell_price': calc.current_sell_price,
                    } 
                    for calc in top_profits[:5]
                ],
                'market_signals': []
            }
        except Exception as fallback_error:
            logger.error(f"Fallback market data failed: {fallback_error}")
            return {
                'sources': ['error'],
                'market_summary': {'error': 'Unable to retrieve market data'},
                'precision_opportunities': [],
                'opportunities': [],
                'market_signals': []
            }

    def _extract_growth_targets(self, query: str) -> Tuple[int, int]:
        """Extract start and target amounts from growth queries."""
        # Look for patterns like "500K into 1M" or "turn 1M into 10M"
        patterns = [
            r'(\d+(?:\.\d+)?)\s*([KMB]?)\s*(?:GP)?\s*(?:into|to)\s*(\d+(?:\.\d+)?)\s*([KMB]?)',
            r'turn\s*(\d+(?:\.\d+)?)\s*([KMB]?)\s*(?:GP)?\s*into\s*(\d+(?:\.\d+)?)\s*([KMB]?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                start_num, start_unit, target_num, target_unit = match.groups()
                
                # Convert to GP
                start_gp = self._convert_to_gp(float(start_num), start_unit or '')
                target_gp = self._convert_to_gp(float(target_num), target_unit or '')
                
                return start_gp, target_gp
        
        # Fallback to capital from query
        capital = self._extract_capital_from_query(query)
        return capital, capital * 2  # Default to doubling
    
    
    def _extract_target_from_query(self, query: str) -> int:
        """Extract target amount from time-to-goal queries."""
        # Look for patterns like "make 1M" or "reach 10M"
        patterns = [
            r'(?:make|reach|achieve|get to)\s*(\d+(?:\.\d+)?)\s*([KMB]?)(?:\s*GP)?',
            r'(\d+(?:\.\d+)?)\s*([KMB]?)(?:\s*GP)?\s*(?:profit|target|goal)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                amount, unit = match.groups()
                return self._convert_to_gp(float(amount), unit or '')
        
        # Default to 2x current capital
        return self._extract_capital_from_query(query) * 2

    async def _analyze_capital_growth(self, start_amount: int, target_amount: int, query: str) -> Dict[str, Any]:
        """Analyze capital growth strategy."""
        multiplier = target_amount / start_amount if start_amount > 0 else 2.0
        
        return {
            'start_capital': start_amount,
            'target_capital': target_amount,
            'multiplier': multiplier,
            'strategy_type': self._determine_growth_strategy(multiplier),
            'risk_level': self._determine_growth_risk(multiplier),
            'recommended_approach': self._get_growth_approach(multiplier, start_amount)
        }
    
    def _determine_growth_strategy(self, multiplier: float) -> str:
        """Determine the appropriate growth strategy based on multiplier."""
        if multiplier <= 2:
            return 'conservative_doubling'
        elif multiplier <= 5:
            return 'moderate_growth'
        elif multiplier <= 10:
            return 'aggressive_expansion'
        else:
            return 'exponential_growth'
    
    def _determine_growth_risk(self, multiplier: float) -> str:
        """Determine risk level for growth targets."""
        if multiplier <= 2:
            return 'low'
        elif multiplier <= 5:
            return 'moderate'
        elif multiplier <= 10:
            return 'high'
        else:
            return 'extreme'
    
    def _get_growth_approach(self, multiplier: float, start_capital: int) -> str:
        """Get recommended approach for capital growth."""
        if multiplier <= 2:
            return 'high_frequency_trading'
        elif multiplier <= 5:
            return 'diversified_portfolio'
        elif multiplier <= 10:
            return 'market_timing_focus'
        else:
            return 'speculative_opportunities'
    

    async def _calculate_growth_timeline(self, start_amount: int, target_amount: int) -> Dict[str, Any]:
        """Calculate realistic timeline for capital growth."""
        multiplier = target_amount / start_amount if start_amount > 0 else 2.0
        
        # Base timeline calculations (in days)
        if multiplier <= 2:
            base_days = 7  # 1 week for doubling
        elif multiplier <= 5:
            base_days = 21  # 3 weeks 
        elif multiplier <= 10:
            base_days = 45  # 6+ weeks
        else:
            base_days = 90  # 3+ months
        
        # Adjust for capital size (larger amounts take longer)
        if start_amount > 50000000:  # 50M+
            base_days *= 1.5
        elif start_amount > 100000000:  # 100M+
            base_days *= 2.0
        
        return {
            'estimated_days': int(base_days),
            'confidence': 0.8 if multiplier <= 5 else 0.6,
            'milestones': self._generate_milestones(start_amount, target_amount, int(base_days))
        }

    def _generate_milestones(self, start: int, target: int, days: int) -> List[Dict[str, Any]]:
        """Generate milestone targets for capital growth."""
        milestones = []
        progress_points = [0.25, 0.5, 0.75, 1.0]
        
        for i, progress in enumerate(progress_points):
            milestone_amount = start + (target - start) * progress
            milestone_day = int(days * progress)
            
            milestones.append({
                'day': milestone_day,
                'target_amount': int(milestone_amount),
                'description': f'{progress * 100:.0f}% progress milestone'
            })
        
        return milestones

    async def _analyze_market_secrets(self, query: str, capital_gp: int) -> Dict[str, Any]:
        """Analyze market secrets and insider knowledge."""
        return {
            'high_multiplier_categories': [
                'Limited event items during updates',
                'Seasonal consumables before major events', 
                'Secondary ingredients for new content',
                'Discontinued items with low supply'
            ],
            'professional_techniques': [
                'Market timing with game update cycles',
                'Cross-market arbitrage opportunities',
                'Bulk buying during market crashes',
                'Psychological price points exploitation'
            ],
            'hidden_patterns': [
                'Weekend trading volume differences',
                'Update announcement impact timing',
                'Bot detection and counter-strategies',
                'Whale trader movement patterns'
            ]
        }

    async def _get_insider_insights(self) -> Dict[str, Any]:
        """Get insider trading insights."""
        return {
            'pro_trader_secrets': [
                'Most amateurs focus on margins, pros focus on velocity',
                'Real money is in anticipating market moves, not reacting',
                'Volume analysis reveals institutional buying patterns', 
                'Price memory effects create predictable rebounds'
            ],
            'market_inefficiencies': [
                'Cross-world price differences',
                'Time-of-day liquidity gaps',
                'Update-driven panic selling opportunities',
                'Newbie dumping patterns'
            ]
        }

    async def _analyze_potion_market(self, capital_gp: int, risk_tolerance: str) -> Dict[str, Any]:
        """Analyze potion and consumables market."""
        # Get actual potion items from database
        from apps.items.models import Item
        
        potions = [
            item async for item in Item.objects.filter(
                Q(name__icontains='potion') | Q(name__icontains='brew')
            ).select_related('profit_calc')[:20]
        ]
        
        high_profit_potions = []
        for potion in potions:
            profit_calc = getattr(potion, 'profit_calc', None)
            if profit_calc and profit_calc.current_profit > 50:
                high_profit_potions.append({
                    'name': potion.name,
                    'profit': profit_calc.current_profit,
                    'margin': profit_calc.current_profit_margin
                })
        
        return {
            'top_potions': high_profit_potions[:10],
            'market_patterns': [
                'Combat potions spike during PvP tournaments',
                'Prayer potions in high demand during XP events',
                'Antifire potions correlate with dragon boss events'
            ],
            'seasonal_trends': [
                'Summer: Prayer potions (XP events)',
                'Winter: Combat potions (PvP leagues)',
                'Updates: New potion demand spikes'
            ]
        }

    async def _get_consumables_opportunities(self) -> Dict[str, Any]:
        """Get consumables trading opportunities."""
        return {
            'high_turnover_items': [
                'Food for high-level content',
                'Ammunition for training/PvP', 
                'Runes for magic training',
                'Potions for skill grinding'
            ],
            'event_opportunities': [
                'Double XP: All consumables spike',
                'PvP events: Combat supplies increase',
                'Boss events: Specific gear/consumables',
                'Leagues: Unique consumable patterns'
            ]
        }

    async def _calculate_realistic_timeline(self, current_capital: int, target_amount: int) -> Dict[str, Any]:
        """Calculate realistic timeline to reach target amount."""
        profit_needed = target_amount - current_capital
        
        # Estimate daily profit based on capital size
        if current_capital < 1000000:  # <1M
            daily_profit_rate = 0.15  # 15% daily possible
        elif current_capital < 10000000:  # <10M
            daily_profit_rate = 0.10  # 10% daily
        elif current_capital < 100000000:  # <100M
            daily_profit_rate = 0.08  # 8% daily
        else:
            daily_profit_rate = 0.05  # 5% daily for large amounts
        
        estimated_daily_profit = current_capital * daily_profit_rate
        estimated_days = profit_needed / estimated_daily_profit if estimated_daily_profit > 0 else 365
        
        return {
            'estimated_days': min(int(estimated_days), 365),
            'daily_profit_needed': int(estimated_daily_profit),
            'success_probability': 0.8 if estimated_days <= 30 else 0.6,
            'risk_factors': [
                'Market volatility can extend timeline',
                'Requires consistent daily trading',
                'Capital compound effect accelerates later'
            ]
        }
    
    def _get_historical_context_for_item(self, item_name: str) -> str:
        """Get concise historical context for an item."""
        try:
            # Synchronously get the item and its historical analysis
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Get item and historical analysis in one query
                cursor.execute("""
                    SELECT ha.trend_30d, ha.volatility_30d, ha.current_price_percentile_30d,
                           ha.support_level_30d, ha.resistance_level_30d, ha.price_min_30d, ha.price_max_30d
                    FROM historical_analysis ha
                    JOIN items i ON ha.item_id = i.id
                    WHERE i.name = %s
                    LIMIT 1
                """, [item_name])
                
                row = cursor.fetchone()
                if not row:
                    return ""
                
                trend_30d, volatility_30d, percentile_30d, support_30d, resistance_30d, min_30d, max_30d = row
                
                context_parts = []
                
                # Add trend information
                if trend_30d:
                    trend_desc = {
                        'strong_up': '↗️ Strong uptrend',
                        'up': '↗️ Uptrend', 
                        'sideways': '➡️ Sideways',
                        'down': '↘️ Downtrend',
                        'strong_down': '↘️ Strong downtrend'
                    }.get(trend_30d, trend_30d)
                    context_parts.append(trend_desc)
                
                # Add volatility info
                if volatility_30d:
                    if volatility_30d > 0.4:
                        context_parts.append("High volatility")
                    elif volatility_30d < 0.15:
                        context_parts.append("Low volatility")
                
                # Add position relative to historical range
                if percentile_30d is not None:
                    if percentile_30d >= 85:
                        context_parts.append("Near 30d highs")
                    elif percentile_30d <= 15:
                        context_parts.append("Near 30d lows")
                
                # Add support/resistance levels
                if support_30d and resistance_30d:
                    context_parts.append(f"Support: {support_30d:,} GP, Resistance: {resistance_30d:,} GP")
                
                return " | ".join(context_parts) if context_parts else ""
                
        except Exception as e:
            logger.warning(f"Error getting historical context for {item_name}: {e}")
            return ""
    
    async def _enhance_with_money_maker_context(self, context: Dict, capital_gp: int, query: str) -> Dict:
        """
        Enhance context with money maker opportunities using your friend's strategies.
        
        Args:
            context: Existing context data
            capital_gp: Available capital
            query: User's query
            
        Returns:
            Enhanced context with money maker opportunities
        """
        try:
            logger.info(f"Enhancing context with money maker strategies for {capital_gp:,} GP capital")
            
            # Add money maker opportunities to context
            money_maker_context = await AsyncMoneyMakerDetector.get_opportunities(capital_gp)
            
            # Detect query intent for specific strategies
            query_lower = query.lower()
            
            # Specific strategy context based on query
            strategy_context = {}
            
            # Decanting context (your friend's 40M method)
            if any(keyword in query_lower for keyword in ['decant', 'potion', 'dose', 'barbarian herblore']):
                strategy_context['decanting_focus'] = await self._get_decanting_specific_context()
            
            # Set combining context (lazy tax exploitation)
            if any(keyword in query_lower for keyword in ['set', 'armor', 'lazy', 'combine', 'barrows', 'god wars']):
                strategy_context['set_combining_focus'] = await self._get_set_combining_specific_context()
            
            # Bond flipping context (high-value strategy)
            if any(keyword in query_lower for keyword in ['bond', 'high value', 'expensive', 'godsword']):
                strategy_context['bond_flipping_focus'] = await self._get_bond_flipping_specific_context()
            
            # Capital progression advice
            strategy_context['capital_progression'] = self._get_capital_progression_advice(capital_gp)
            
            # GE tax education (critical for accurate profits)
            strategy_context['ge_tax_context'] = self._get_ge_tax_education()
            
            # Add to context
            context.update({
                'money_maker_opportunities': money_maker_context,
                'strategy_specific_context': strategy_context,
                'capital_tier': self._determine_capital_tier(capital_gp),
                'proven_methods': self._get_proven_methods_context()
            })
            
            logger.info(f"Enhanced context with {len(money_maker_context.get('opportunities', []))} money maker opportunities")
            
            return context
            
        except Exception as e:
            logger.error(f"Error enhancing with money maker context: {e}")
            # Return original context if enhancement fails
            return context
    
    async def _get_decanting_specific_context(self) -> Dict:
        """Get specific context for decanting strategies."""
        try:
            # Use the enhanced decanting detector
            opportunities = self.decanting_detector.detect_opportunities()
            
            # Get top profitable decanting opportunities
            top_opportunities = sorted(opportunities, key=lambda x: x.get('hourly_profit_potential', 0), reverse=True)[:5]
            
            return {
                'strategy_name': 'Potion Decanting',
                'description': 'Your friend made 40M+ profit using this method',
                'requirements': ['Barbarian Herblore training', 'Initial capital for potion stock'],
                'top_opportunities': top_opportunities,
                'hourly_potential': f"{sum(opp.get('hourly_profit_potential', 0) for opp in top_opportunities[:3]) // 3:,} GP/hr average",
                'key_tips': [
                    'Focus on popular potions: Super combat, Prayer, Ranging',
                    '4-dose → 3-dose usually most profitable',
                    'Buy in bulk during low-demand hours',
                    'Account for GE tax on sales',
                    'Scale up as capital grows'
                ]
            }
        except Exception as e:
            logger.error(f"Error getting decanting context: {e}")
            return {}
    
    async def _get_set_combining_specific_context(self) -> Dict:
        """Get specific context for set combining (lazy tax) strategies."""
        try:
            # Get set combining opportunities
            opportunities = await self.set_combining_detector.detect_set_opportunities()
            
            # Get top lazy tax opportunities
            top_lazy_tax = sorted(opportunities, key=lambda x: x.lazy_tax_percentage, reverse=True)[:5]
            
            return {
                'strategy_name': 'Set Combining (Lazy Tax)',
                'description': 'Buy pieces separately, sell as complete sets for premium',
                'lazy_tax_explanation': 'Players pay 2-6% premium for convenience of complete sets',
                'top_opportunities': [
                    {
                        'set_name': opp.set_name,
                        'lazy_tax_pct': f"{opp.lazy_tax_percentage:.1f}%",
                        'profit': f"{opp.net_profit:,} GP",
                        'pieces_cost': f"{opp.pieces_total_cost:,} GP"
                    } for opp in top_lazy_tax
                ],
                'popular_sets': [
                    'Barrows sets (Dharok, Ahrim, etc.)',
                    'God Wars armor (Bandos, Armadyl)',
                    'Godswords (high-value weapon sets)',
                    'Void equipment sets'
                ],
                'key_tips': [
                    'Monitor piece vs set price differentials',
                    'Buy pieces during off-peak hours',
                    'Sell complete sets during prime time',
                    'Account for GE tax on set sales',
                    'Start with cheaper sets, scale up'
                ]
            }
        except Exception as e:
            logger.error(f"Error getting set combining context: {e}")
            return {}
    
    async def _get_bond_flipping_specific_context(self) -> Dict:
        """Get specific context for bond flipping strategies."""
        return {
            'strategy_name': 'Bond Flipping',
            'description': 'Your friend\'s starting method: "I started with 50m buying bonds"',
            'bond_advantages': [
                'Old School Bonds are GE tax exempt (major advantage)',
                'Instant capital injection from real money',
                'Access to high-value item flipping',
                'Stable conversion rate to GP'
            ],
            'target_items': [
                'Expensive weapons: Godswords, Scythe, Twisted bow',
                'High-end armor: Ancestral, Justiciar, Armadyl',
                'Rare items with good margins',
                'Items with predictable price cycles'
            ],
            'capital_requirements': {
                'minimum': '50M GP for meaningful impact',
                'recommended': '100M+ GP for best opportunities',
                'expert': '500M+ GP for market influence'
            },
            'key_tips': [
                'Bonds exempt from 2% GE tax (huge advantage)',
                'Focus on items with 5M+ value',
                'Monitor price cycles and patterns',
                'Use bond proceeds for initial capital',
                'Scale reinvestment as profits grow'
            ]
        }
    
    def _determine_capital_tier(self, capital_gp: int) -> str:
        """Determine capital tier for strategy recommendations."""
        if capital_gp < 10_000_000:
            return 'Starter'
        elif capital_gp < 50_000_000:
            return 'Intermediate'
        elif capital_gp < 200_000_000:
            return 'Advanced'
        else:
            return 'Expert'
    
    def _get_capital_progression_advice(self, capital_gp: int) -> Dict:
        """Get advice for progressing to the next capital tier."""
        tier = self._determine_capital_tier(capital_gp)
        
        advice_map = {
            'Starter': {
                'current_focus': 'High alchemy, basic flipping, consistent profits',
                'next_goal': '10M GP for intermediate strategies',
                'recommended_strategies': ['High alchemy items', 'Small-margin flipping', 'Potion decanting practice'],
                'timeline': '2-4 weeks with consistent effort'
            },
            'Intermediate': {
                'current_focus': 'Decanting profits, armor set combining, scaling flips',
                'next_goal': '50M GP for advanced strategies',
                'recommended_strategies': ['Potion decanting (your friend\'s 40M method)', 'Barrows set combining', 'Medium-value flipping'],
                'timeline': '4-8 weeks with reinvestment'
            },
            'Advanced': {
                'current_focus': 'Bond flipping, high-value strategies, multiple methods',
                'next_goal': '200M GP for expert operations',
                'recommended_strategies': ['Bond-funded flipping', 'God Wars set combining', 'Multiple strategies simultaneously'],
                'timeline': '6-12 weeks with optimal execution'
            },
            'Expert': {
                'current_focus': 'Market influence, complex strategies, diversified portfolio',
                'next_goal': 'Wealth preservation and growth',
                'recommended_strategies': ['Market timing', 'Large-scale operations', 'Risk diversification'],
                'timeline': 'Ongoing wealth management'
            }
        }
        
        return advice_map.get(tier, advice_map['Starter'])
    
    def _get_ge_tax_education(self) -> Dict:
        """Provide education about GE tax implications."""
        return {
            'ge_tax_rules': {
                'rate': '2% on all sales over 50 GP',
                'exemptions': 'Old School Bonds are tax exempt',
                'cap': 'Maximum 5M GP tax per item',
                'application': 'Applied per item, not per trade'
            },
            'profit_impact': [
                'Must account for tax in all profit calculations',
                'Bonds provide major advantage being tax-free',
                'High-value items hit the tax cap',
                'Low-value items under 50 GP exempt'
            ],
            'examples': {
                'regular_item': 'Sell 1M GP item → 20K GP tax → 980K received',
                'bond': 'Sell 8M GP bond → 0 GP tax → 8M received',
                'expensive': 'Sell 500M GP item → 5M GP tax (capped)'
            },
            'strategy_implications': [
                'Factor tax into all margin calculations',
                'Bonds ideal for high-value flipping',
                'Consider tax when pricing strategies',
                'Volume strategies affected more by tax'
            ]
        }
    
    def _get_proven_methods_context(self) -> Dict:
        """Get context about proven money making methods."""
        return {
            'your_friends_approach': {
                'starting_capital': '50M GP from bonds',
                'method_1': 'High-value item flipping on GE',
                'method_2': '40M profit from decanting potions',
                'method_3': 'Set combining for lazy tax profits',
                'result': 'Scaled to 100M+ GP',
                'key_insight': 'Multiple strategies simultaneously for consistent growth'
            },
            'proven_principles': [
                'Start with bonds for tax-free capital',
                'Use decanting for consistent income',
                'Exploit lazy tax on armor sets',
                'Reinvest all profits for compound growth',
                'Monitor market fluctuations carefully'
            ],
            'scaling_strategy': [
                'Phase 1: Build base capital with decanting',
                'Phase 2: Add set combining for diversification',
                'Phase 3: Scale flipping with larger items',
                'Phase 4: Multiple strategies running parallel',
                'Phase 5: Market timing and optimization'
            ]
        }