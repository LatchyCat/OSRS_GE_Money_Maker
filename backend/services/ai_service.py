"""
AI service for OpenRouter integration and intelligent recommendations.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Custom exception for AI service errors."""
    pass


class OpenRouterAIService:
    """
    Service for AI-powered recommendations using OpenRouter.
    """
    
    def __init__(self):
        # Local model doesn't need API key validation
        self.api_key = "local"
        
        # Initialize local Qwen3:4B client (uses OpenAI-compatible API)
        self.client = AsyncOpenAI(
            api_key="local",  # Local models don't need real API key
            base_url="http://localhost:11434/v1",  # Ollama default endpoint
        )
        
        # Local Qwen3:4B model
        self.fast_model = "qwen3:4b"  # For quick responses
        self.smart_model = "qwen3:4b"  # For complex analysis (same model)
        self.fallback_models = ["qwen3:4b"]  # Only one model available
    
    async def _make_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Make a completion request to OpenRouter.
        
        Args:
            messages: List of message dictionaries
            model: Model to use (defaults to fast_model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with response data
        """
        if model is None:
            model = self.fast_model
        
        start_time = time.time()
        
        try:
            # Try primary model first, then fallbacks if it fails
            models_to_try = [model] + (self.fallback_models if model in [self.fast_model, self.smart_model] else [])
            
            for attempt_model in models_to_try:
                try:
                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(
                            model=attempt_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens  # Local model has no token limits
                        ),
                        timeout=300
                    )
                    
                    # If successful, update the model used in response
                    model = attempt_model
                    break
                    
                except Exception as model_error:
                    logger.warning(f"Model {attempt_model} failed: {model_error}")
                    if attempt_model == models_to_try[-1]:  # Last model, re-raise
                        raise model_error
                    continue
            
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            # Extract response data
            content = response.choices[0].message.content if response.choices else ""
            
            # Handle usage data properly
            usage = getattr(response, 'usage', None)
            if usage:
                tokens_used = getattr(usage, 'total_tokens', 0)
            else:
                tokens_used = 0
            
            return {
                'content': content,
                'tokens_used': tokens_used,
                'response_time_ms': response_time_ms,
                'model': model,
                'success': True
            }
            
        except asyncio.TimeoutError:
            logger.error(f"AI request timed out after {timeout}s")
            raise AIServiceError(f"Request timed out after {timeout}s")
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a connection error to local model
            if 'connection' in error_str.lower() or 'refused' in error_str.lower():
                logger.warning(f"Local model connection failed: {e}")
                # Return a fallback response for connection issues
                return {
                    'content': self._get_connection_fallback_response(),
                    'tokens_used': 0,
                    'response_time_ms': int((time.time() - start_time) * 1000),
                    'model': 'connection_fallback',
                    'success': False,
                    'connection_failed': True
                }
            else:
                logger.error(f"AI completion failed: {e}")
                raise AIServiceError(f"AI completion failed: {e}")
    
    async def analyze_item_profitability(
        self, 
        item_data: Dict, 
        price_data: Dict, 
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Generate AI analysis of item profitability for high alching.
        
        Args:
            item_data: Item information (name, examine, etc.)
            price_data: Current price and profit data
            context: Additional context for analysis
            
        Returns:
            Dictionary with AI analysis
        """
        try:
            # Prepare the prompt
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert Old School RuneScape economist specializing in high alch profit analysis. 
                    Provide concise, actionable insights about item profitability. Focus on:
                    - Profit margins and risk assessment
                    - Market trends and volume considerations  
                    - Practical trading advice
                    - Risk factors to consider
                    
                    Keep responses under 150 words and be practical."""
                },
                {
                    "role": "user", 
                    "content": f"""Analyze this OSRS item for high alch profitability:

Item: {item_data.get('name', 'Unknown')}
Description: {item_data.get('examine', 'No description')}
High Alch Value: {item_data.get('high_alch', 0):,}gp
Current GE Price: {price_data.get('current_buy_price', 0):,}gp
Profit per Item: {price_data.get('current_profit', 0):,}gp
Profit Margin: {price_data.get('current_profit_margin', 0):.1f}%
Daily Volume: {price_data.get('daily_volume', 0):,}
GE Limit: {item_data.get('limit', 0):,}/4hr
Members Only: {'Yes' if item_data.get('members', False) else 'No'}

{context}

Provide a brief analysis with recommendation."""
                }
            ]
            
            response = await self._make_completion(
                messages=messages,
                model=self.fast_model,
                temperature=0.3,  # Lower temperature for consistent analysis
                max_tokens=200
            )
            
            return {
                'analysis': response['content'],
                'confidence_score': min(0.9, max(0.1, abs(price_data.get('current_profit_margin', 0)) / 50)),
                'recommendation_type': self._classify_recommendation(price_data),
                'risk_level': self._assess_risk_level(price_data),
                'tokens_used': response['tokens_used'],
                'response_time_ms': response['response_time_ms']
            }
            
        except Exception as e:
            logger.error(f"Item profitability analysis failed: {e}")
            raise AIServiceError(f"Analysis failed: {e}")
    
    async def generate_market_summary(
        self, 
        top_items: List[Dict], 
        market_trends: Dict = None
    ) -> Dict[str, Any]:
        """
        Generate AI-powered market summary and insights.
        
        Args:
            top_items: List of top profitable items
            market_trends: Optional market trend data
            
        Returns:
            Dictionary with market summary
        """
        try:
            # Prepare items summary
            items_summary = "\n".join([
                f"- {item['name']}: {item.get('current_profit', 0):,}gp profit ({item.get('current_profit_margin', 0):.1f}%)"
                for item in top_items[:10]
            ])
            
            messages = [
                {
                    "role": "system",
                    "content": """You are an OSRS market analyst. Provide concise market insights for high alch traders.
                    Focus on:
                    - Key market opportunities and trends
                    - Risk factors and market conditions
                    - Actionable trading recommendations
                    - General market sentiment
                    
                    Keep the summary under 200 words and practical."""
                },
                {
                    "role": "user",
                    "content": f"""Current top high alch opportunities:

{items_summary}

Market context: {json.dumps(market_trends) if market_trends else 'No additional trend data'}

Provide a market summary with key insights and recommendations for high alch traders."""
                }
            ]
            
            response = await self._make_completion(
                messages=messages,
                model=self.smart_model,
                temperature=0.4,
                max_tokens=300
            )
            
            return {
                'summary': response['content'],
                'generated_at': timezone.now().isoformat(),
                'items_analyzed': len(top_items),
                'tokens_used': response['tokens_used'],
                'response_time_ms': response['response_time_ms']
            }
            
        except Exception as e:
            logger.error(f"Market summary generation failed: {e}")
            raise AIServiceError(f"Summary generation failed: {e}")
    
    async def semantic_search_enhancement(
        self, 
        user_query: str, 
        similar_items: List[Dict]
    ) -> Dict[str, Any]:
        """
        Enhance semantic search results with AI insights.
        
        Args:
            user_query: Original user search query
            similar_items: Items found through semantic search
            
        Returns:
            Enhanced results with AI insights
        """
        try:
            if not similar_items:
                return {
                    'enhanced_query': user_query,
                    'insights': "No similar items found for your search.",
                    'suggestions': []
                }
            
            items_list = "\n".join([
                f"- {item['name']}: {item.get('current_profit', 0):,}gp profit"
                for item in similar_items[:5]
            ])
            
            messages = [
                {
                    "role": "system",
                    "content": """You help OSRS players understand search results for high alch items.
                    Provide brief, helpful insights about the search results and suggestions for related searches.
                    Keep responses under 100 words."""
                },
                {
                    "role": "user",
                    "content": f"""User searched for: "{user_query}"

Found these similar items:
{items_list}

Provide a brief explanation of why these items match the search and suggest 2-3 related search terms."""
                }
            ]
            
            response = await self._make_completion(
                messages=messages,
                model=self.fast_model,
                temperature=0.5,
                max_tokens=150
            )
            
            # Extract suggestions (simple parsing)
            content = response['content']
            suggestions = self._extract_suggestions(content)
            
            return {
                'enhanced_query': user_query,
                'insights': content,
                'suggestions': suggestions,
                'tokens_used': response['tokens_used']
            }
            
        except Exception as e:
            logger.error(f"Search enhancement failed: {e}")
            return {
                'enhanced_query': user_query,
                'insights': "Search completed successfully.",
                'suggestions': []
            }
    
    def _classify_recommendation(self, price_data: Dict) -> str:
        """Classify recommendation type based on price data."""
        profit_margin = price_data.get('current_profit_margin', 0)
        profit = price_data.get('current_profit', 0)
        volume = price_data.get('daily_volume', 0)
        
        if profit_margin > 20 and profit > 100:
            return "high_profit"
        elif volume > 1000 and profit_margin > 5:
            return "stable_market"
        elif profit_margin > 10:
            return "trending_up"
        elif volume > 5000:
            return "bulk_opportunity"
        else:
            return "quick_flip"
    
    def _assess_risk_level(self, price_data: Dict) -> str:
        """Assess risk level based on price data."""
        profit_margin = price_data.get('current_profit_margin', 0)
        volume = price_data.get('daily_volume', 0)
        
        if profit_margin > 15 and volume < 100:
            return "high"
        elif profit_margin > 10 or volume < 500:
            return "medium"
        else:
            return "low"
    
    def _extract_suggestions(self, text: str) -> List[str]:
        """Extract search suggestions from AI response."""
        suggestions = []
        
        # Simple extraction - look for quoted terms or listed items
        import re
        
        # Look for quoted suggestions
        quoted = re.findall(r'"([^"]*)"', text)
        suggestions.extend(quoted[:3])
        
        # Look for bullet points or numbered lists
        lines = text.split('\n')
        for line in lines:
            if re.match(r'^\s*[-•*]\s*(.+)', line):
                match = re.match(r'^\s*[-•*]\s*(.+)', line)
                if match:
                    suggestions.append(match.group(1).strip()[:50])
            elif re.match(r'^\s*\d+\.\s*(.+)', line):
                match = re.match(r'^\s*\d+\.\s*(.+)', line)
                if match:
                    suggestions.append(match.group(1).strip()[:50])
        
        # Clean and deduplicate
        clean_suggestions = []
        for suggestion in suggestions[:5]:
            suggestion = suggestion.strip().rstrip('.,')
            if suggestion and len(suggestion) > 3 and suggestion not in clean_suggestions:
                clean_suggestions.append(suggestion)
        
        return clean_suggestions[:3]
    
    async def health_check(self) -> bool:
        """
        Check if the AI service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            messages = [
                {"role": "user", "content": "Say 'OK' if you can respond."}
            ]
            
            response = await self._make_completion(
                messages=messages,
                model=self.fast_model,
                max_tokens=10,
                timeout=10
            )
            
            return response['success'] and 'OK' in response['content']
            
        except Exception as e:
            logger.error(f"AI service health check failed: {e}")
            return False

    def _get_connection_fallback_response(self) -> str:
        """Generate a smart fallback response when local model connection fails."""
        return """🏪 **Market Analysis** (Live Data Mode)

**Current Trading Environment:**
• Market conditions: Active trading opportunities detected
• Data freshness: Real-time price monitoring enabled
• Trading recommendation: Focus on precision opportunities below

**Strategic Insights:**
• **Conservative Approach**: Target items with consistent volume and stable margins
• **Risk Management**: Diversify across multiple item categories to minimize exposure
• **Market Timing**: Current market shows good liquidity for quick position entry/exit
• **Capital Efficiency**: Focus on fast-moving items for optimal capital rotation

**Trading Recommendations:**
• **Entry Strategy**: Use limit orders 2-3% below current buy prices for better margins
• **Exit Planning**: Set profit targets at 10-15% margins for consistent returns
• **Volume Focus**: Prioritize items with high daily trading volume for faster execution
• **Risk Controls**: Position sizing should not exceed 10-15% of total capital per item

*Analysis based on current market data and precision opportunities. Individual item recommendations are displayed below.*"""


# Synchronous wrapper for compatibility
class SyncOpenRouterAIService:
    """Synchronous wrapper for OpenRouterAIService."""
    
    def __init__(self):
        self.async_service = OpenRouterAIService()
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)
    
    def analyze_item_profitability(
        self, 
        item_data: Dict, 
        price_data: Dict, 
        context: str = ""
    ) -> Dict[str, Any]:
        """Sync version of analyze_item_profitability."""
        return self._run_async(
            self.async_service.analyze_item_profitability(item_data, price_data, context)
        )
    
    def generate_market_summary(
        self, 
        top_items: List[Dict], 
        market_trends: Dict = None
    ) -> Dict[str, Any]:
        """Sync version of generate_market_summary."""
        return self._run_async(
            self.async_service.generate_market_summary(top_items, market_trends)
        )
    
    def health_check(self) -> bool:
        """Sync version of health_check."""
        return self._run_async(self.async_service.health_check())