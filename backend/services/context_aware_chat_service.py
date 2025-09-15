"""
Context-Aware AI Chat Service for OSRS Trading Intelligence

This service combines FAISS similarity search, comprehensive market data, and local AI models
to provide intelligent, context-aware trading conversations. It understands:

- Current trading view context (decanting, flipping, etc.)
- Real-time market conditions and item data  
- User's historical trading patterns
- Volume-weighted market analysis
- Confidence-scored recommendations

Features:
- FAISS-powered semantic search across all items
- Context-aware responses based on current view
- Real-time market data integration
- Multi-model AI reasoning with fallbacks
- Conversation memory and learning
- Trading strategy recommendations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import hashlib
import numpy as np

from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q

from .faiss_manager import FaissVectorDatabase
from .enhanced_embedding_service import EnhancedEmbeddingService
from .ollama_ai_service import OllamaAIService, TradingView, TradingContext, AIResponse
from .unified_wiki_price_client import UnifiedPriceClient
from .advanced_confidence_scoring_service import AdvancedConfidenceScoringService
from .price_pattern_analysis_service import PricePatternAnalysisService
from apps.items.models import Item
from apps.embeddings.models import ItemEmbedding, SearchQuery
from apps.prices.models import PriceTrend, MarketAlert, PricePattern

logger = logging.getLogger(__name__)


@dataclass
class ChatContext:
    """Complete chat context with trading intelligence."""
    # User context
    user_id: Optional[str] = None
    session_id: str = ""
    current_view: TradingView = TradingView.GENERAL
    
    # Query context  
    user_message: str = ""
    query_intent: str = ""  # search, analysis, recommendation, chat
    
    # Market context
    relevant_items: List[Dict[str, Any]] = field(default_factory=list)
    similar_items: List[Tuple[int, float]] = field(default_factory=list)  # (item_id, similarity)
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Conversation context
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    previous_recommendations: List[str] = field(default_factory=list)
    
    # System context
    confidence_threshold: float = 0.6
    max_similar_items: int = 10
    include_volume_analysis: bool = True


@dataclass
class ChatResponse:
    """Structured response from context-aware chat system."""
    # Core response
    message: str
    confidence_score: float
    processing_time: float
    
    # Context information
    relevant_items: List[Dict[str, Any]] = field(default_factory=list)
    trading_recommendations: List[str] = field(default_factory=list)
    market_insights: List[str] = field(default_factory=list)
    
    # System metadata
    query_intent: str = ""
    search_results_count: int = 0
    ai_model_used: str = ""
    faiss_query_time: float = 0.0
    
    # Interaction guidance
    suggested_follow_ups: List[str] = field(default_factory=list)
    warning_flags: List[str] = field(default_factory=list)


class ContextAwareChatService:
    """
    Advanced AI chat service with FAISS similarity search and trading intelligence.
    """
    
    def __init__(self):
        # Initialize core services
        self.faiss_db = FaissVectorDatabase("items", dimension=1024)
        self.embedding_service = EnhancedEmbeddingService()
        self.ai_service = OllamaAIService()
        self.confidence_service = AdvancedConfidenceScoringService()
        self.pattern_analyzer = PricePatternAnalysisService()
        
        # Chat configuration
        self.max_conversation_history = 10  # Messages to remember
        self.similarity_threshold = 0.7  # Minimum similarity for relevance
        self.cache_timeout = 600  # 10 minutes for chat responses
        
        # Intent detection keywords
        self.intent_patterns = {
            'search': ['find', 'search', 'look for', 'show me', 'what is', 'tell me about'],
            'analysis': ['analyze', 'compare', 'evaluate', 'assess', 'how good', 'profitable'],
            'recommendation': ['recommend', 'suggest', 'best', 'should i', 'what to', 'advice'],
            'chat': ['hello', 'hi', 'help', 'explain', 'why', 'how', 'thanks']
        }
        
        # View-specific response templates
        self.view_contexts = {
            TradingView.HIGH_ALCHEMY: {
                'focus_keywords': ['alch', 'alchemy', 'nature rune', 'magic', 'profit per cast'],
                'default_suggestions': [
                    "Show me items with good alch profit",
                    "What's the current nature rune cost?",
                    "Find high-volume alchable items"
                ]
            },
            TradingView.FLIPPING: {
                'focus_keywords': ['flip', 'margin', 'buy low', 'sell high', 'ge tax'],
                'default_suggestions': [
                    "Find items with good flip margins",
                    "Show me high-volume flipping opportunities", 
                    "What items have the best profit margins?"
                ]
            },
            TradingView.DECANTING: {
                'focus_keywords': ['decant', 'potion', 'dose', 'barbarian herblore'],
                'default_suggestions': [
                    "Show me profitable decanting opportunities",
                    "Find 4-dose potions to break down",
                    "What potions have the best dose arbitrage?"
                ]
            }
        }
        
    async def initialize_chat_system(self) -> Dict[str, Any]:
        """
        Initialize the chat system and verify all components are working.
        
        Returns:
            Initialization status and component health
        """
        logger.info("Initializing context-aware chat system...")
        
        status = {
            'faiss_index': False,
            'embedding_service': False,
            'ai_models': {},
            'overall_health': False,
            'initialization_time': None
        }
        
        start_time = datetime.now()
        
        try:
            # 1. Check FAISS index
            stats = self.faiss_db.get_stats()
            status['faiss_index'] = stats['total_vectors'] > 0
            logger.info(f"FAISS index: {stats['total_vectors']} vectors")
            
            # 2. Check embedding service
            status['embedding_service'] = await self.embedding_service.ensure_model_available()
            
            # 3. Check AI models
            status['ai_models'] = await self.ai_service.ensure_models_available()
            
            # 4. Overall health check
            status['overall_health'] = (
                status['faiss_index'] and 
                status['embedding_service'] and 
                any(status['ai_models'].values())
            )
            
            status['initialization_time'] = (datetime.now() - start_time).total_seconds()
            
            if status['overall_health']:
                logger.info(f"✅ Chat system initialized successfully in {status['initialization_time']:.1f}s")
            else:
                logger.warning("⚠️ Chat system initialized with issues")
                
        except Exception as e:
            logger.error(f"Failed to initialize chat system: {e}")
            status['error'] = str(e)
        
        return status
    
    def _detect_query_intent(self, user_message: str) -> str:
        """
        Detect user query intent based on message content.
        
        Args:
            user_message: User's message
            
        Returns:
            Detected intent (search, analysis, recommendation, chat)
        """
        message_lower = user_message.lower()
        
        # Score each intent based on keyword matches
        intent_scores = {}
        for intent, keywords in self.intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Return highest scoring intent, default to chat
        if intent_scores:
            return max(intent_scores.items(), key=lambda x: x[1])[0]
        else:
            return 'chat'
    
    async def _perform_similarity_search(
        self, 
        user_message: str, 
        current_view: TradingView,
        max_results: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Perform FAISS similarity search based on user query.
        
        Args:
            user_message: User's query
            current_view: Current trading view for context
            max_results: Maximum number of results
            
        Returns:
            List of (item_id, similarity_score) tuples
        """
        try:
            # Enhance query with view context
            enhanced_query = await self._enhance_query_with_context(user_message, current_view)
            
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_enhanced_embedding(-1)  # Special ID for queries
            
            if query_embedding is None:
                # Fallback: try to generate embedding for enhanced query text
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.embedding_service.client.embeddings(
                        model=self.embedding_service.model_name,
                        prompt=enhanced_query
                    )
                )
                
                if 'embedding' in response:
                    query_embedding = np.array(response['embedding'], dtype=np.float32)
            
            if query_embedding is None:
                logger.warning("Failed to generate query embedding")
                return []
            
            # Search FAISS index
            results = self.faiss_db.search(
                query_vector=query_embedding.tolist(),
                k=max_results,
                threshold=self.similarity_threshold
            )
            
            logger.debug(f"FAISS search found {len(results)} similar items")
            return results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []
    
    async def _enhance_query_with_context(self, user_message: str, current_view: TradingView) -> str:
        """
        Enhance user query with trading view context.
        
        Args:
            user_message: Original user message
            current_view: Current trading view
            
        Returns:
            Enhanced query string
        """
        # Get view-specific context
        view_context = self.view_contexts.get(current_view, {})
        focus_keywords = view_context.get('focus_keywords', [])
        
        # Build enhanced query
        enhanced_parts = [user_message]
        
        # Add view-specific context
        if current_view != TradingView.GENERAL:
            enhanced_parts.append(f"Context: {current_view.value} trading strategy")
        
        # Add focus keywords if not already present
        for keyword in focus_keywords:
            if keyword not in user_message.lower():
                enhanced_parts.append(keyword)
        
        return " | ".join(enhanced_parts)
    
    async def _enhance_with_pattern_analysis(self, item_ids: List[int], context: ChatContext) -> Dict[str, Any]:
        """
        Enhance chat responses with AI-powered pattern analysis.
        
        Args:
            item_ids: List of item IDs to analyze
            context: Chat context for targeted analysis
            
        Returns:
            Dictionary with pattern insights and market signals
        """
        if not item_ids:
            return {}
        
        try:
            # Limit analysis to top items to avoid performance issues
            analysis_items = item_ids[:5]
            
            pattern_insights = {
                'trends': {},
                'patterns': [],
                'market_signals': [],
                'alerts': [],
                'temporal_context': []
            }
            
            for item_id in analysis_items:
                try:
                    # Get trend analysis for key periods
                    trends = await self.pattern_analyzer.analyze_item_trends(
                        item_id, ['1h', '24h']
                    )
                    
                    if trends:
                        pattern_insights['trends'][item_id] = trends
                        
                        # Add temporal context for AI
                        for period, trend in trends.items():
                            if trend.confidence > 0.6:
                                direction_text = trend.direction.replace('_', ' ').title()
                                pattern_insights['temporal_context'].append(
                                    f"Item {item_id} shows {direction_text} trend over {period} "
                                    f"({trend.price_change_percent:+.1f}%, confidence: {trend.confidence:.1%})"
                                )
                    
                    # Get recent patterns
                    patterns = await self.pattern_analyzer.detect_price_patterns(item_id, 24)
                    if patterns:
                        high_conf_patterns = [p for p in patterns if p.confidence > 0.7]
                        pattern_insights['patterns'].extend(high_conf_patterns)
                    
                    # Generate market signals
                    signals = await self.pattern_analyzer.generate_market_signals(item_id)
                    if signals:
                        # Filter for high-priority signals
                        priority_signals = [s for s in signals if s.priority in ['critical', 'high']]
                        pattern_insights['market_signals'].extend(priority_signals)
                
                except Exception as e:
                    logger.debug(f"Pattern analysis failed for item {item_id}: {e}")
            
            # Get recent market alerts
            recent_alerts = await self._get_recent_market_alerts(analysis_items)
            pattern_insights['alerts'] = recent_alerts
            
            return pattern_insights
            
        except Exception as e:
            logger.warning(f"Pattern analysis enhancement failed: {e}")
            return {}
    
    async def _get_recent_market_alerts(self, item_ids: List[int]) -> List[Dict]:
        """Get recent market alerts for items."""
        def get_alerts():
            try:
                alerts = MarketAlert.objects.filter(
                    item__item_id__in=item_ids,
                    is_active=True,
                    created_at__gte=timezone.now() - timedelta(hours=6)
                ).select_related('item').order_by('-created_at')[:10]
                
                return [
                    {
                        'item_id': alert.item.item_id,
                        'item_name': alert.item.name,
                        'alert_type': alert.alert_type,
                        'priority': alert.priority,
                        'message': alert.message,
                        'confidence': alert.confidence_score,
                        'created_at': alert.created_at.isoformat()
                    }
                    for alert in alerts
                ]
            except Exception as e:
                logger.debug(f"Failed to get recent alerts: {e}")
                return []
        
        return await asyncio.to_thread(get_alerts)
    
    async def _get_item_data_for_chat(self, item_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get comprehensive item data optimized for chat responses.
        
        Args:
            item_ids: List of item IDs to fetch
            
        Returns:
            List of item data dictionaries
        """
        if not item_ids:
            return []
        
        try:
            async with UnifiedPriceClient() as client:
                # Get enriched item data
                enriched_data = await client.get_enriched_item_data(item_ids)
                
                chat_items = []
                for item_id, (price_data, metadata) in enriched_data.items():
                    if not metadata:  # Skip items without metadata
                        continue
                    
                    item_info = {
                        'item_id': item_id,
                        'name': metadata.name,
                        'examine': metadata.examine,
                        'members': metadata.members,
                        'high_alch': metadata.highalch,
                        'ge_limit': metadata.limit,
                        'base_value': metadata.value
                    }
                    
                    if price_data:
                        # Calculate key trading metrics
                        nature_rune_cost = 180
                        alch_profit = metadata.highalch - nature_rune_cost - (price_data.high_price or 0)
                        
                        # GE tax calculation (1% with 5M cap)
                        ge_tax = min(int((price_data.high_price or 0) * 0.01), 5_000_000)
                        flip_profit = (price_data.high_price or 0) - (price_data.low_price or 0) - ge_tax
                        
                        item_info.update({
                            'current_high_price': price_data.high_price,
                            'current_low_price': price_data.low_price,
                            'price_age_hours': price_data.age_hours,
                            'trading_volume': price_data.total_volume,
                            'data_confidence': price_data.confidence_score,
                            'alch_profit': max(0, alch_profit),
                            'flip_profit': max(0, flip_profit),
                            'volume_analysis': price_data.volume_analysis
                        })
                    
                    chat_items.append(item_info)
                
                # Sort by relevance (confidence score or profit potential)
                chat_items.sort(key=lambda x: x.get('data_confidence', 0), reverse=True)
                
                return chat_items
                
        except Exception as e:
            logger.error(f"Failed to get item data for chat: {e}")
            return []
    
    def _build_trading_context_for_ai(self, chat_context: ChatContext) -> TradingContext:
        """
        Build TradingContext for AI service from ChatContext.
        
        Args:
            chat_context: Complete chat context
            
        Returns:
            TradingContext optimized for AI analysis
        """
        # Convert relevant items to AI-compatible format
        relevant_items = []
        for item in chat_context.relevant_items[:5]:  # Limit to top 5 for AI
            ai_item = {
                'item_id': item['item_id'],
                'name': item['name'],
                'metadata': {
                    'highalch': item.get('high_alch', 0),
                    'limit': item.get('ge_limit', 0),
                    'members': item.get('members', False),
                    'examine': item.get('examine', '')
                }
            }
            
            if 'current_high_price' in item:
                ai_item['price_data'] = {
                    'high_price': item['current_high_price'],
                    'low_price': item['current_low_price'],
                    'total_volume': item.get('trading_volume', 0),
                    'age_hours': item.get('price_age_hours', 0),
                    'confidence_score': item.get('data_confidence', 0)
                }
            
            relevant_items.append(ai_item)
        
        return TradingContext(
            current_view=chat_context.current_view,
            user_query=chat_context.user_message,
            relevant_items=relevant_items,
            market_conditions=chat_context.market_conditions
        )
    
    def _generate_follow_up_suggestions(
        self, 
        chat_context: ChatContext, 
        ai_response: AIResponse
    ) -> List[str]:
        """
        Generate contextual follow-up suggestions.
        
        Args:
            chat_context: Original chat context
            ai_response: AI's response
            
        Returns:
            List of suggested follow-up questions
        """
        suggestions = []
        
        # View-specific suggestions
        view_context = self.view_contexts.get(chat_context.current_view, {})
        default_suggestions = view_context.get('default_suggestions', [])
        
        # Add pattern analysis suggestions if available
        pattern_analysis = chat_context.market_conditions.get('pattern_analysis', {})
        
        if pattern_analysis.get('market_signals'):
            suggestions.append("What do these market signals mean for my trading strategy?")
            suggestions.append("Should I act on these patterns now or wait?")
        
        if pattern_analysis.get('trends'):
            suggestions.append("Explain the price trends you detected")
            suggestions.append("How reliable are these trend predictions?")
        
        if pattern_analysis.get('alerts'):
            suggestions.append("Tell me about these market alerts")
            suggestions.append("Which alerts should I prioritize?")
        
        # If we found relevant items, suggest deeper analysis
        if chat_context.relevant_items:
            top_item = chat_context.relevant_items[0]
            suggestions.append(f"Tell me more about {top_item['name']}")
            
            if top_item.get('alch_profit', 0) > 0:
                suggestions.append(f"Is {top_item['name']} good for high alchemy?")
            
            if top_item.get('flip_profit', 0) > 0:
                suggestions.append(f"What's the flipping potential for {top_item['name']}?")
        
        # Intent-based suggestions
        if chat_context.query_intent == 'search':
            suggestions.extend([
                "Compare these items for profitability",
                "Show me volume analysis for these items"
            ])
        elif chat_context.query_intent == 'recommendation':
            suggestions.extend([
                "What are the risks with these strategies?",
                "How much capital do I need for this?"
            ])
        
        # Add view defaults if we have space
        remaining_slots = 3 - len(suggestions)
        if remaining_slots > 0:
            suggestions.extend(default_suggestions[:remaining_slots])
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    async def process_chat_message(self, chat_context: ChatContext) -> ChatResponse:
        """
        Process a chat message with full context awareness.
        
        Args:
            chat_context: Complete chat context
            
        Returns:
            Comprehensive chat response with trading intelligence
        """
        start_time = datetime.now()
        logger.info(f"Processing chat message in {chat_context.current_view.value} context")
        
        # Detect query intent
        chat_context.query_intent = self._detect_query_intent(chat_context.user_message)
        
        # Check cache for similar queries
        cache_key = f"chat:{hashlib.md5(chat_context.user_message.encode()).hexdigest()}:{chat_context.current_view.value}"
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.debug("Using cached chat response")
            return cached_response
        
        try:
            # Perform similarity search for relevant items
            faiss_start = datetime.now()
            similar_items = await self._perform_similarity_search(
                chat_context.user_message,
                chat_context.current_view,
                chat_context.max_similar_items
            )
            faiss_time = (datetime.now() - faiss_start).total_seconds()
            
            # Get detailed item data for relevant items
            if similar_items:
                relevant_item_ids = [item_id for item_id, score in similar_items 
                                   if score >= chat_context.confidence_threshold]
                chat_context.relevant_items = await self._get_item_data_for_chat(relevant_item_ids[:5])
                
                # Enhance with AI-powered pattern analysis
                pattern_insights = await self._enhance_with_pattern_analysis(
                    relevant_item_ids[:5], chat_context
                )
                
                # Add pattern insights to market conditions
                chat_context.market_conditions.update({
                    'pattern_analysis': pattern_insights,
                    'has_temporal_context': len(pattern_insights.get('temporal_context', [])) > 0,
                    'active_alerts': len(pattern_insights.get('alerts', [])) > 0
                })
            
            # Build AI context
            trading_context = self._build_trading_context_for_ai(chat_context)
            
            # Generate AI response
            ai_response = await self.ai_service.generate_ai_response(trading_context)
            
            # Build comprehensive chat response
            processing_time = (datetime.now() - start_time).total_seconds()
            
            chat_response = ChatResponse(
                message=ai_response.response_text,
                confidence_score=ai_response.confidence_score,
                processing_time=processing_time,
                relevant_items=chat_context.relevant_items,
                trading_recommendations=ai_response.trading_recommendations,
                market_insights=ai_response.market_insights,
                query_intent=chat_context.query_intent,
                search_results_count=len(similar_items),
                ai_model_used=ai_response.model_used,
                faiss_query_time=faiss_time,
                warning_flags=ai_response.warning_flags
            )
            
            # Generate follow-up suggestions
            chat_response.suggested_follow_ups = self._generate_follow_up_suggestions(
                chat_context, ai_response
            )
            
            # Cache response
            cache.set(cache_key, chat_response, self.cache_timeout)
            
            logger.info(f"Chat response generated in {processing_time:.2f}s "
                       f"(FAISS: {faiss_time:.2f}s, {len(chat_context.relevant_items)} items)")
            
            return chat_response
            
        except Exception as e:
            logger.error(f"Failed to process chat message: {e}")
            
            # Return error response
            return ChatResponse(
                message=f"I'm having trouble processing your request right now. Please try rephrasing your question or try again in a moment. Error: {str(e)}",
                confidence_score=0.1,
                processing_time=(datetime.now() - start_time).total_seconds(),
                query_intent=chat_context.query_intent,
                warning_flags=["processing_error"]
            )
    
    async def get_view_context_help(self, trading_view: TradingView) -> Dict[str, Any]:
        """
        Get contextual help and examples for a trading view.
        
        Args:
            trading_view: Trading view to get help for
            
        Returns:
            Context help information
        """
        view_info = self.view_contexts.get(trading_view, {})
        
        help_context = {
            'view': trading_view.value,
            'description': self.ai_service.system_prompts.get(trading_view, "General trading assistance"),
            'focus_keywords': view_info.get('focus_keywords', []),
            'example_queries': [
                f"What are the best {trading_view.value} opportunities?",
                f"Show me profitable {trading_view.value} items",
                f"Analyze {trading_view.value} market conditions"
            ],
            'suggested_questions': view_info.get('default_suggestions', [])
        }
        
        return help_context