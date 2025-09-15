"""
Ollama AI Service for Local AI Integration

This service provides intelligent trading analysis and chat functionality using
local Ollama models (deepseek-r1:1.5b and gemma3:1b) with comprehensive
OSRS trading context and market data understanding.

Features:
- Multi-model AI analysis with fallback
- Trading strategy recommendations
- Natural language market explanations
- Context-aware responses based on trading view
- Volume-weighted decision making
- Real-time market commentary
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union, Literal
from dataclasses import dataclass, field
from enum import Enum
import ollama
from datetime import datetime

from django.conf import settings
from django.core.cache import cache

from .unified_wiki_price_client import UnifiedPriceClient, PriceData
from .advanced_confidence_scoring_service import AdvancedConfidenceScoringService, ConfidenceComponents
from .runescape_wiki_client import ItemMetadata

logger = logging.getLogger(__name__)


class AIModel(Enum):
    """Available AI models."""
    DEEPSEEK_R1 = "deepseek-r1:1.5b"
    GEMMA3 = "gemma3:1b" 
    GEMMA2 = "gemma2:2b"


class TradingView(Enum):
    """Different trading views/contexts."""
    HIGH_ALCHEMY = "high-alchemy"
    FLIPPING = "flipping"
    DECANTING = "decanting"
    CRAFTING = "crafting"
    SET_COMBINING = "set-combining"
    BOND_FLIPPING = "bond-flipping"
    MAGIC_RUNES = "magic-runes"
    GENERAL = "general"


@dataclass
class AIResponse:
    """Structured AI response."""
    response_text: str
    confidence_score: float
    model_used: str
    processing_time: float
    context_items: List[int] = field(default_factory=list)
    trading_recommendations: List[str] = field(default_factory=list)
    market_insights: List[str] = field(default_factory=list)
    warning_flags: List[str] = field(default_factory=list)


@dataclass
class TradingContext:
    """Complete trading context for AI analysis."""
    current_view: TradingView
    user_query: str
    relevant_items: List[Dict[str, Any]] = field(default_factory=list)
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)


class OllamaAIService:
    """
    Local AI service using Ollama models for trading intelligence.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.client = ollama.Client(host=self.base_url)
        
        # Model configuration with fallbacks
        self.models = {
            AIModel.DEEPSEEK_R1: {
                'name': 'deepseek-r1:1.5b',
                'max_tokens': 1024,
                'temperature': 0.3,  # Conservative for trading advice
                'specialties': ['analysis', 'recommendations', 'complex_reasoning']
            },
            AIModel.GEMMA3: {
                'name': 'gemma3:1b',
                'max_tokens': 800,
                'temperature': 0.4,
                'specialties': ['chat', 'explanations', 'simple_queries']
            },
            AIModel.GEMMA2: {
                'name': 'gemma2:2b',
                'max_tokens': 1000,
                'temperature': 0.35,
                'specialties': ['analysis', 'detailed_responses']
            }
        }
        
        # Initialize services
        self.confidence_service = AdvancedConfidenceScoringService()
        
        # AI system prompts for different contexts
        self.system_prompts = {
            TradingView.HIGH_ALCHEMY: """You are an expert OSRS (Old School RuneScape) high alchemy advisor. You help players identify profitable high alchemy opportunities by analyzing item costs, alch values, and market conditions. Focus on GP profit per cast, magic XP efficiency, and sustainable trading strategies. Always consider nature rune costs and GE buy limits.""",
            
            TradingView.FLIPPING: """You are an expert OSRS Grand Exchange flipping advisor. You analyze price spreads, market volumes, and trading patterns to identify profitable flipping opportunities. Consider GE tax (1% with 5M cap), liquidity, price volatility, and timing. Emphasize risk management and capital efficiency.""",
            
            TradingView.DECANTING: """You are an expert OSRS potion decanting advisor. You help players profit from converting potions between different dose levels (4-dose to 1-dose). Focus on dose arbitrage opportunities, barbarian herblore requirements, and sustainable profit strategies. Consider potion popularity and volume patterns.""",
            
            TradingView.CRAFTING: """You are an expert OSRS crafting profit advisor. You analyze material costs, finished product values, and XP rates to identify profitable crafting opportunities. Consider skill requirements, time investment, and market demand patterns.""",
            
            TradingView.SET_COMBINING: """You are an expert OSRS armor/weapon set trading advisor. You identify opportunities to profit from combining individual armor pieces into complete sets and vice versa. Focus on 'lazy tax' premiums, set completion bonuses, and popular PvP/PvM gear.""",
            
            TradingView.BOND_FLIPPING: """You are an expert OSRS bond and high-value item trading advisor. You help players trade expensive items (10M+ GP) using bond-funded strategies. Focus on capital efficiency, market timing, and risk management for premium items.""",
            
            TradingView.GENERAL: """You are an expert OSRS trading and money-making advisor. You provide comprehensive market analysis, trading strategies, and profit opportunities across all aspects of the Grand Exchange. Focus on data-driven insights and sustainable profit methods."""
        }
        
        # Cache configuration
        self.cache_timeout = 300  # 5 minutes for AI responses
        self.max_context_items = 10  # Maximum items to include in context
    
    async def ensure_models_available(self) -> Dict[str, bool]:
        """
        Check availability of AI models.
        
        Returns:
            Dictionary mapping model names to availability status
        """
        availability = {}
        
        try:
            models_response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.list
            )
            
            available_models = [model.model for model in models_response.models] if hasattr(models_response, 'models') else []
            
            for ai_model in AIModel:
                model_name = self.models[ai_model]['name']
                availability[model_name] = model_name in available_models
            
            logger.info(f"Model availability: {availability}")
            
        except Exception as e:
            logger.error(f"Failed to check model availability: {e}")
            for ai_model in AIModel:
                availability[self.models[ai_model]['name']] = False
        
        return availability
    
    def _select_best_model_for_task(self, task_type: str, query_complexity: str = 'medium') -> AIModel:
        """
        Select the best AI model for a specific task.
        
        Args:
            task_type: Type of task (chat, analysis, recommendation)
            query_complexity: Complexity level (simple, medium, complex)
            
        Returns:
            Best AI model for the task
        """
        # Task-specific model selection
        if task_type == 'analysis' or query_complexity == 'complex':
            return AIModel.DEEPSEEK_R1  # Best reasoning capabilities
        elif task_type == 'chat' or query_complexity == 'simple':
            return AIModel.GEMMA3  # Fast and conversational
        else:
            return AIModel.GEMMA2  # Good balance
    
    def _build_trading_prompt(self, context: TradingContext) -> str:
        """
        Build comprehensive trading prompt with market context.
        
        Args:
            context: Complete trading context
            
        Returns:
            Formatted prompt for AI model
        """
        prompt_parts = []
        
        # Add system context for current view
        system_prompt = self.system_prompts.get(context.current_view, self.system_prompts[TradingView.GENERAL])
        prompt_parts.append(f"ROLE: {system_prompt}")
        
        # Add current market context
        if context.relevant_items:
            prompt_parts.append("\nCURRENT MARKET DATA:")
            for item_data in context.relevant_items[:self.max_context_items]:
                item_context = self._format_item_for_prompt(item_data)
                prompt_parts.append(item_context)
        
        # Add market conditions
        if context.market_conditions:
            prompt_parts.append(f"\nMARKET CONDITIONS: {json.dumps(context.market_conditions, indent=2)}")
        
        # Add trading view specific context
        view_context = self._get_view_specific_context(context.current_view)
        if view_context:
            prompt_parts.append(f"\nTRADING FOCUS: {view_context}")
        
        # Add user query
        prompt_parts.append(f"\nUSER QUESTION: {context.user_query}")
        
        # Add response guidelines
        prompt_parts.append("""
RESPONSE GUIDELINES:
1. Provide specific, actionable trading advice
2. Include actual GP profit estimates when possible
3. Mention risks and considerations
4. Use current market data in your analysis
5. Be concise but comprehensive
6. Focus on sustainable, realistic strategies
7. Always consider volume and liquidity factors
""")
        
        return "\n".join(prompt_parts)
    
    def _format_item_for_prompt(self, item_data: Dict[str, Any]) -> str:
        """Format item data for AI prompt."""
        item_id = item_data.get('item_id', 'Unknown')
        name = item_data.get('name', 'Unknown Item')
        
        # Basic item info
        info_parts = [f"Item: {name} (ID: {item_id})"]
        
        # Price information
        if 'price_data' in item_data and item_data['price_data']:
            price = item_data['price_data']
            info_parts.append(f"High Price: {price.get('high_price', 0):,} GP")
            info_parts.append(f"Low Price: {price.get('low_price', 0):,} GP")
            info_parts.append(f"Volume: {price.get('total_volume', 0):,}")
            info_parts.append(f"Data Age: {price.get('age_hours', 0):.1f}h")
        
        # Metadata
        if 'metadata' in item_data and item_data['metadata']:
            meta = item_data['metadata']
            info_parts.append(f"High Alch: {meta.get('highalch', 0):,} GP")
            info_parts.append(f"GE Limit: {meta.get('limit', 0)}")
            info_parts.append(f"Members: {meta.get('members', False)}")
        
        # Confidence score
        if 'confidence' in item_data:
            conf = item_data['confidence']
            info_parts.append(f"Confidence: {conf:.2f}")
        
        return " | ".join(info_parts)
    
    def _get_view_specific_context(self, view: TradingView) -> str:
        """Get specific context for trading view."""
        context_map = {
            TradingView.HIGH_ALCHEMY: "Focus on items with high alch profit potential. Consider nature rune cost (180 GP), buy limits, and magic XP rates. Prioritize sustainable, high-volume opportunities.",
            
            TradingView.FLIPPING: "Focus on price spreads and margin opportunities. Factor in 1% GE tax (5M cap), trading volume, and price volatility. Emphasize quick turnover and capital efficiency.",
            
            TradingView.DECANTING: "Focus on potion dose arbitrage. Consider barbarian herblore requirements, potion popularity, and dose conversion profits. Look for 4-dose to lower dose opportunities.",
            
            TradingView.CRAFTING: "Focus on material to finished product profit margins. Consider skill requirements, time investment, XP rates, and resource availability.",
            
            TradingView.SET_COMBINING: "Focus on individual pieces vs complete sets. Look for lazy tax premiums, popular PvP/PvM gear, and set completion bonuses.",
            
            TradingView.BOND_FLIPPING: "Focus on high-value items (10M+) and bond-funded strategies. Consider market timing, capital requirements, and premium item liquidity."
        }
        
        return context_map.get(view, "Provide comprehensive trading analysis considering all profit opportunities.")
    
    async def generate_ai_response(
        self, 
        context: TradingContext,
        preferred_model: Optional[AIModel] = None
    ) -> AIResponse:
        """
        Generate AI response for trading query.
        
        Args:
            context: Complete trading context
            preferred_model: Preferred AI model (will fallback if unavailable)
            
        Returns:
            Structured AI response with analysis and recommendations
        """
        start_time = datetime.now()
        
        # Select model
        if preferred_model:
            selected_model = preferred_model
        else:
            # Auto-select based on query complexity
            complexity = 'complex' if len(context.user_query) > 100 else 'medium'
            selected_model = self._select_best_model_for_task('analysis', complexity)
        
        # Check cache first
        cache_key = f"ai_response:{hash(context.user_query + str(context.current_view))}"
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.debug("Using cached AI response")
            return cached_response
        
        try:
            # Build prompt
            prompt = self._build_trading_prompt(context)
            
            # Try primary model
            response_text = await self._call_ollama_model(selected_model, prompt)
            
            if not response_text:
                # Fallback to alternative model
                fallback_model = AIModel.GEMMA2 if selected_model != AIModel.GEMMA2 else AIModel.GEMMA3
                logger.warning(f"Primary model {selected_model.value} failed, trying {fallback_model.value}")
                response_text = await self._call_ollama_model(fallback_model, prompt)
                selected_model = fallback_model
            
            if not response_text:
                raise Exception("All AI models failed to generate response")
            
            # Process response
            ai_response = self._process_ai_response(
                response_text, 
                selected_model, 
                context,
                (datetime.now() - start_time).total_seconds()
            )
            
            # Cache response
            cache.set(cache_key, ai_response, self.cache_timeout)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Failed to generate AI response: {e}")
            
            # Return fallback response
            return AIResponse(
                response_text=f"I'm having trouble analyzing the market data right now. Please try again in a moment. Error: {str(e)}",
                confidence_score=0.1,
                model_used="fallback",
                processing_time=(datetime.now() - start_time).total_seconds(),
                warning_flags=["ai_service_error"]
            )
    
    async def _call_ollama_model(self, model: AIModel, prompt: str) -> Optional[str]:
        """
        Call Ollama model with error handling.
        
        Args:
            model: AI model to use
            prompt: Input prompt
            
        Returns:
            Response text or None if failed
        """
        try:
            model_config = self.models[model]
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.generate(
                    model=model_config['name'],
                    prompt=prompt,
                    options={
                        'num_predict': model_config['max_tokens'],
                        'temperature': model_config['temperature'],
                        'top_p': 0.9,
                        'stop': ['\n\nUSER:', '\n\nHuman:', '<|end|>']
                    }
                )
            )
            
            if response and 'response' in response:
                return response['response'].strip()
            else:
                logger.warning(f"Invalid response from {model.value}: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to call {model.value}: {e}")
            return None
    
    def _process_ai_response(
        self, 
        response_text: str, 
        model: AIModel, 
        context: TradingContext,
        processing_time: float
    ) -> AIResponse:
        """
        Process and enhance raw AI response.
        
        Args:
            response_text: Raw response from AI
            model: Model that generated the response
            context: Original context
            processing_time: Time taken to generate
            
        Returns:
            Structured AI response
        """
        # Extract recommendations and insights
        recommendations = self._extract_recommendations(response_text)
        insights = self._extract_market_insights(response_text)
        warnings = self._extract_warnings(response_text)
        
        # Calculate confidence based on response quality
        confidence = self._calculate_response_confidence(response_text, context)
        
        return AIResponse(
            response_text=response_text,
            confidence_score=confidence,
            model_used=self.models[model]['name'],
            processing_time=processing_time,
            context_items=[item.get('item_id') for item in context.relevant_items],
            trading_recommendations=recommendations,
            market_insights=insights,
            warning_flags=warnings
        )
    
    def _extract_recommendations(self, text: str) -> List[str]:
        """Extract specific trading recommendations from AI response."""
        recommendations = []
        
        # Look for recommendation patterns
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'should', 'consider', 'try']):
                if len(line) > 10 and len(line) < 200:  # Reasonable length
                    recommendations.append(line)
        
        return recommendations[:5]  # Limit to top 5
    
    def _extract_market_insights(self, text: str) -> List[str]:
        """Extract market insights from AI response."""
        insights = []
        
        # Look for insight patterns
        insight_keywords = ['market', 'price', 'volume', 'trend', 'demand', 'supply']
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in insight_keywords):
                if len(line) > 20 and len(line) < 200:
                    insights.append(line)
        
        return insights[:3]  # Limit to top 3
    
    def _extract_warnings(self, text: str) -> List[str]:
        """Extract warning flags from AI response."""
        warnings = []
        
        warning_keywords = ['risk', 'careful', 'warning', 'volatile', 'uncertain', 'low volume']
        text_lower = text.lower()
        
        for keyword in warning_keywords:
            if keyword in text_lower:
                warnings.append(f"contains_{keyword.replace(' ', '_')}")
        
        return warnings
    
    def _calculate_response_confidence(self, text: str, context: TradingContext) -> float:
        """Calculate confidence score for AI response quality."""
        confidence = 0.5  # Base confidence
        
        # Length and detail bonus
        if len(text) > 100:
            confidence += 0.1
        if len(text) > 300:
            confidence += 0.1
        
        # Specific data usage bonus
        if any(str(item.get('item_id', '')) in text for item in context.relevant_items):
            confidence += 0.15
        
        # Trading term usage bonus
        trading_terms = ['gp', 'profit', 'margin', 'volume', 'price', 'buy', 'sell']
        term_count = sum(1 for term in trading_terms if term in text.lower())
        confidence += min(0.15, term_count * 0.03)
        
        # Numerical data bonus
        import re
        numbers = re.findall(r'\d{1,3}(?:,\d{3})*', text)
        if numbers:
            confidence += min(0.1, len(numbers) * 0.02)
        
        return min(1.0, confidence)
    
    async def get_trading_view_recommendations(
        self, 
        view: TradingView, 
        item_ids: Optional[List[int]] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Get AI recommendations for a specific trading view.
        
        Args:
            view: Trading view context
            item_ids: Optional specific items to analyze
            limit: Maximum number of recommendations
            
        Returns:
            Dictionary with recommendations and analysis
        """
        try:
            # Build context
            context = TradingContext(
                current_view=view,
                user_query=f"What are the best {view.value} opportunities right now?",
                market_conditions={'timestamp': datetime.now().isoformat()}
            )
            
            # Get relevant items if not specified
            if item_ids:
                context.relevant_items = await self._get_item_data_for_context(item_ids)
            else:
                # Get top items for this view type
                context.relevant_items = await self._get_top_items_for_view(view, limit)
            
            # Generate AI response
            ai_response = await self.generate_ai_response(context)
            
            return {
                'view': view.value,
                'recommendations': ai_response.trading_recommendations,
                'analysis': ai_response.response_text,
                'market_insights': ai_response.market_insights,
                'confidence_score': ai_response.confidence_score,
                'item_count': len(context.relevant_items),
                'model_used': ai_response.model_used,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get {view.value} recommendations: {e}")
            return {
                'view': view.value,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _get_item_data_for_context(self, item_ids: List[int]) -> List[Dict[str, Any]]:
        """Get comprehensive item data for AI context."""
        item_data = []
        
        try:
            async with UnifiedPriceClient() as client:
                # Get enriched data for items
                enriched_data = await client.get_enriched_item_data(item_ids)
                
                for item_id, (price_data, metadata) in enriched_data.items():
                    item_info = {'item_id': item_id}
                    
                    if metadata:
                        item_info['name'] = metadata.name
                        item_info['metadata'] = {
                            'highalch': metadata.highalch,
                            'limit': metadata.limit,
                            'members': metadata.members,
                            'examine': metadata.examine
                        }
                    
                    if price_data:
                        item_info['price_data'] = {
                            'high_price': price_data.high_price,
                            'low_price': price_data.low_price,
                            'total_volume': price_data.total_volume,
                            'age_hours': price_data.age_hours,
                            'confidence_score': price_data.confidence_score
                        }
                        
                        # Calculate confidence components
                        if metadata:
                            confidence = self.confidence_service.calculate_comprehensive_confidence(
                                price_data, metadata
                            )
                            item_info['confidence'] = confidence.total_score
                    
                    item_data.append(item_info)
        
        except Exception as e:
            logger.error(f"Failed to get item data for context: {e}")
        
        return item_data
    
    async def _get_top_items_for_view(self, view: TradingView, limit: int) -> List[Dict[str, Any]]:
        """Get top items for a specific trading view."""
        # This would be implemented based on view-specific logic
        # For now, return empty list as placeholder
        logger.debug(f"Getting top {limit} items for {view.value} view")
        return []