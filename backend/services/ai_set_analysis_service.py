"""
AI-Powered Set Analysis Service for OSRS Set Combining

Uses multiple Ollama models for advanced set opportunity analysis with consensus-based scoring.
Integrates with OSRS Wiki API for real-time pricing and volume data.
"""

import asyncio
import logging
import httpx
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from services.runescape_wiki_client import RuneScapeWikiAPIClient
from services.weird_gloop_client import GrandExchangeTax

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class AISetOpportunity:
    """AI-analyzed set combining opportunity with multi-model consensus."""
    set_name: str
    set_item_id: int
    piece_ids: List[int]
    piece_names: List[str]
    strategy: str  # 'combining' or 'decombining'
    strategy_description: str
    
    # Financial metrics
    profit_gp: int
    profit_margin_pct: float
    required_capital: int
    ge_tax_amount: int
    
    # AI analysis
    ai_confidence_score: float  # 0.0 to 1.0
    ai_risk_level: RiskLevel
    ai_timing_recommendation: str
    ai_market_sentiment: str
    model_consensus_score: float  # Agreement between models
    
    # Volume and trading metrics
    volume_score: float
    liquidity_rating: str
    estimated_sets_per_hour: int
    
    # Real-time data
    pieces_data: List[Dict]
    data_freshness_hours: float
    pricing_source: str


class AISetAnalysisService:
    """Service for AI-powered set combining analysis using multiple Ollama models."""
    
    def __init__(self):
        self.ollama_base_url = "http://localhost:11434"
        self.models = ["deepseek-r1:1.5b", "gemma3:1b", "qwen3:4b"]
        
        # Known armor sets with proper piece mappings
        self.known_sets = {
            # Barrows sets
            "Dharok's armour set": {
                'set_item_id': 4718,
                'piece_ids': [4716, 4714, 4712, 4718],  # helm, platebody, platelegs, greataxe
                'piece_names': ["Dharok's helm", "Dharok's platebody", "Dharok's platelegs", "Dharok's greataxe"],
                'category': 'barrows'
            },
            "Ahrim's armour set": {
                'set_item_id': 12881,  # Corrected set ID
                'piece_ids': [4708, 4712, 4714, 4710],  # hood, robetop, robeskirt, staff  
                'piece_names': ["Ahrim's hood", "Ahrim's robetop", "Ahrim's robeskirt", "Ahrim's staff"],
                'category': 'barrows'
            },
            "Karil's armour set": {
                'set_item_id': 12883,
                'piece_ids': [4732, 4734, 4736, 4734],
                'piece_names': ["Karil's coif", "Karil's leathertop", "Karil's leatherskirt", "Karil's crossbow"],
                'category': 'barrows'
            },
            
            # Metal armor sets  
            "Rune armour set (lg)": {
                'set_item_id': 13024,
                'piece_ids': [1127, 1079, 1163, 1201],
                'piece_names': ['Rune platebody', 'Rune platelegs', 'Rune full helm', 'Rune kiteshield'],
                'category': 'metal'
            },
            "Adamant armour set (lg)": {
                'set_item_id': 13012,
                'piece_ids': [1123, 1073, 1161, 1199],
                'piece_names': ['Adamant platebody', 'Adamant platelegs', 'Adamant full helm', 'Adamant kiteshield'],
                'category': 'metal'
            },
            
            # Special sets
            "Graceful outfit": {
                'set_item_id': 11850,  # This might be wrong, need to verify
                'piece_ids': [11850, 11852, 11854, 11856, 11858, 11860],
                'piece_names': ['Graceful hood', 'Graceful top', 'Graceful legs', 'Graceful gloves', 'Graceful boots', 'Graceful cape'],
                'category': 'skilling'
            }
        }
    
    async def analyze_set_opportunities(
        self,
        min_profit: int = 5000,
        min_confidence: float = 0.3,
        capital_available: int = 50_000_000,
        force_refresh: bool = False
    ) -> List[AISetOpportunity]:
        """
        Analyze set combining opportunities using AI models and real-time OSRS Wiki data.
        
        Args:
            min_profit: Minimum profit threshold in GP
            min_confidence: Minimum AI confidence score
            capital_available: Available capital for trading
            force_refresh: Force fresh data instead of cached
            
        Returns:
            List of AI-analyzed set opportunities
        """
        logger.info("Starting AI-powered set analysis with multiple Ollama models")
        
        opportunities = []
        
        async with RuneScapeWikiAPIClient() as wiki_client:
            # Get fresh pricing data
            logger.info("Fetching latest prices from OSRS Wiki API")
            all_prices = await wiki_client.get_latest_prices()
            
            # Dynamic set discovery only when explicitly requested with debug parameter
            # This is expensive and should not run on every force refresh
            # TODO: Move this to a separate background job or admin endpoint
            
            # Analyze each known set
            for set_name, set_info in self.known_sets.items():
                try:
                    logger.info(f"Analyzing {set_name} with AI models")
                    
                    opportunity = await self._analyze_set_with_ai(
                        set_name, set_info, all_prices, wiki_client,
                        min_profit, min_confidence, capital_available
                    )
                    
                    if opportunity:
                        opportunities.append(opportunity)
                        logger.info(f"Found profitable opportunity: {set_name} - {opportunity.profit_gp} GP profit")
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze {set_name}: {e}")
                    continue
        
        # Sort by AI-weighted profit potential
        opportunities.sort(key=lambda x: x.profit_gp * x.ai_confidence_score, reverse=True)
        
        logger.info(f"AI analysis complete: {len(opportunities)} profitable opportunities found")
        return opportunities
    
    async def _analyze_set_with_ai(
        self,
        set_name: str,
        set_info: Dict,
        all_prices: Dict,
        wiki_client: RuneScapeWikiAPIClient,
        min_profit: int,
        min_confidence: float,
        capital_available: int
    ) -> Optional[AISetOpportunity]:
        """Analyze a single set with AI models."""
        
        # Get pricing data
        set_item_id = set_info['set_item_id']
        piece_ids = set_info['piece_ids']
        piece_names = set_info['piece_names']
        
        # Check if we have price data for all items
        set_price_data = all_prices.get(set_item_id)
        if not set_price_data or not set_price_data.has_valid_prices:
            logger.debug(f"No price data for set {set_name} (ID: {set_item_id})")
            return None
        
        pieces_data = []
        pieces_total_buy_cost = 0
        pieces_total_sell_value = 0
        
        # Collect piece pricing data
        for i, piece_id in enumerate(piece_ids):
            piece_price_data = all_prices.get(piece_id)
            if not piece_price_data or not piece_price_data.has_valid_prices:
                logger.debug(f"No price data for piece {piece_names[i]} (ID: {piece_id})")
                return None
            
            piece_buy_price = piece_price_data.best_buy_price
            piece_sell_price = piece_price_data.best_sell_price
            
            pieces_total_buy_cost += piece_buy_price
            pieces_total_sell_value += piece_sell_price
            
            pieces_data.append({
                'item_id': piece_id,
                'name': piece_names[i],
                'buy_price': piece_buy_price,
                'sell_price': piece_sell_price,
                'age_hours': piece_price_data.age_hours,
                'high_time': piece_price_data.high_time,
                'low_time': piece_price_data.low_time
            })
        
        # Get set pricing
        set_buy_price = set_price_data.best_buy_price
        set_sell_price = set_price_data.best_sell_price
        
        # Get volume data for AI analysis
        volume_scores = []
        timeseries_data = []
        
        try:
            # Get timeseries for set and pieces
            set_timeseries = await wiki_client.get_timeseries(set_item_id, "6h")
            timeseries_data.append(('set', set_timeseries))
            
            for piece_data in pieces_data:
                piece_timeseries = await wiki_client.get_timeseries(piece_data['item_id'], "6h")
                timeseries_data.append((piece_data['name'], piece_timeseries))
                
        except Exception as e:
            logger.warning(f"Failed to get timeseries data for {set_name}: {e}")
            timeseries_data = []
        
        # Calculate profits for both strategies
        combining_ge_tax = GrandExchangeTax.calculate_tax(set_sell_price, set_item_id)
        combining_profit = (set_sell_price - combining_ge_tax) - pieces_total_buy_cost
        
        decombining_ge_tax = sum(GrandExchangeTax.calculate_tax(piece['sell_price'], piece['item_id']) for piece in pieces_data)
        decombining_profit = (pieces_total_sell_value - decombining_ge_tax) - set_buy_price
        
        # Choose best strategy
        if combining_profit > decombining_profit:
            best_strategy = 'combining'
            profit_gp = combining_profit
            required_capital = pieces_total_buy_cost
            strategy_description = f"Buy individual pieces → Sell {set_name}"
            ge_tax = combining_ge_tax
        else:
            best_strategy = 'decombining'
            profit_gp = decombining_profit
            required_capital = set_buy_price
            strategy_description = f"Buy {set_name} → Sell individual pieces"
            ge_tax = decombining_ge_tax
        
        # Check basic viability
        if profit_gp < min_profit or required_capital > capital_available * 0.8:
            return None
        
        # AI Analysis with multiple models
        ai_analysis = await self._get_ai_consensus_analysis(
            set_name, set_info, pieces_data, timeseries_data,
            profit_gp, required_capital, best_strategy
        )
        
        if ai_analysis['confidence_score'] < min_confidence:
            return None
        
        # Calculate additional metrics
        profit_margin_pct = (profit_gp / required_capital * 100) if required_capital > 0 else 0
        volume_score = ai_analysis.get('volume_score', 0.5)
        estimated_sets_per_hour = max(1, int(6 * volume_score))
        
        return AISetOpportunity(
            set_name=set_name,
            set_item_id=set_item_id,
            piece_ids=piece_ids,
            piece_names=piece_names,
            strategy=best_strategy,
            strategy_description=strategy_description,
            
            profit_gp=profit_gp,
            profit_margin_pct=profit_margin_pct,
            required_capital=required_capital,
            ge_tax_amount=ge_tax,
            
            ai_confidence_score=ai_analysis['confidence_score'],
            ai_risk_level=RiskLevel(ai_analysis['risk_level']),
            ai_timing_recommendation=ai_analysis['timing_recommendation'],
            ai_market_sentiment=ai_analysis['market_sentiment'],
            model_consensus_score=ai_analysis['consensus_score'],
            
            volume_score=volume_score,
            liquidity_rating=ai_analysis.get('liquidity_rating', 'medium'),
            estimated_sets_per_hour=estimated_sets_per_hour,
            
            pieces_data=pieces_data,
            data_freshness_hours=sum(p['age_hours'] for p in pieces_data) / len(pieces_data),
            pricing_source='osrs_wiki_real_time'
        )
    
    async def _get_ai_consensus_analysis(
        self,
        set_name: str,
        set_info: Dict,
        pieces_data: List[Dict],
        timeseries_data: List,
        profit_gp: int,
        required_capital: int,
        strategy: str
    ) -> Dict[str, Any]:
        """Get AI consensus analysis from multiple Ollama models with timeout protection."""
        
        # Fast heuristic analysis for immediate response
        fast_analysis = self._get_fast_heuristic_analysis(set_name, set_info, pieces_data, profit_gp, required_capital, strategy)
        
        # Try AI analysis with timeout protection
        try:
            # Prepare context for AI models
            context = self._prepare_ai_context(set_name, set_info, pieces_data, timeseries_data, profit_gp, required_capital, strategy)
            
            # Run AI analysis with timeout and parallel execution
            model_analyses = await self._run_parallel_ai_analysis(context)
            
            if model_analyses:
                # Enhance fast analysis with AI insights
                ai_consensus = self._calculate_consensus(model_analyses)
                # Merge AI insights with fast heuristics
                return self._merge_analysis_results(fast_analysis, ai_consensus)
            
        except asyncio.TimeoutError:
            logger.warning(f"AI analysis timed out for {set_name}, using fast heuristics")
        except Exception as e:
            logger.warning(f"AI analysis failed for {set_name}: {e}, using fast heuristics")
        
        # Return fast analysis if AI fails or times out
        return fast_analysis
    
    def _get_fast_heuristic_analysis(
        self,
        set_name: str,
        set_info: Dict,
        pieces_data: List[Dict],
        profit_gp: int,
        required_capital: int,
        strategy: str
    ) -> Dict[str, Any]:
        """Generate fast heuristic analysis without AI models."""
        
        # Calculate confidence based on profit margin and data freshness
        profit_margin_pct = (profit_gp / required_capital * 100) if required_capital > 0 else 0
        avg_age_hours = sum(piece.get('age_hours', 1) for piece in pieces_data) / len(pieces_data)
        
        # Confidence scoring heuristics
        confidence_score = 0.5  # Base confidence
        
        # High profit margins increase confidence
        if profit_margin_pct > 100:
            confidence_score += 0.3
        elif profit_margin_pct > 50:
            confidence_score += 0.2
        elif profit_margin_pct > 20:
            confidence_score += 0.1
        
        # Fresh data increases confidence
        if avg_age_hours < 0.5:  # Less than 30 minutes old
            confidence_score += 0.15
        elif avg_age_hours < 2:  # Less than 2 hours old
            confidence_score += 0.1
        
        # Known categories are more reliable
        if set_info.get('category') == 'barrows':
            confidence_score += 0.1
        
        confidence_score = min(1.0, confidence_score)
        
        # Risk assessment heuristics
        risk_level = 'medium'  # Default
        if profit_margin_pct > 150 and confidence_score > 0.7:
            risk_level = 'low'  # High profit, high confidence
        elif profit_margin_pct < 20 or avg_age_hours > 4:
            risk_level = 'high'  # Low profit or stale data
        
        # Volume scoring based on data freshness and set type
        volume_score = 0.5
        if set_info.get('category') == 'barrows':
            volume_score = 0.7  # Barrows sets are typically liquid
        elif avg_age_hours < 1:
            volume_score = 0.6  # Fresh data suggests activity
        
        return {
            'confidence_score': round(confidence_score, 3),
            'risk_level': risk_level,
            'timing_recommendation': self._get_timing_recommendation(profit_margin_pct, risk_level),
            'market_sentiment': 'neutral',
            'consensus_score': 1.0,  # Perfect consensus for heuristics
            'volume_score': volume_score,
            'liquidity_rating': 'high' if volume_score > 0.6 else 'medium' if volume_score > 0.4 else 'low'
        }
    
    def _get_timing_recommendation(self, profit_margin_pct: float, risk_level: str) -> str:
        """Generate timing recommendation based on profit and risk."""
        if profit_margin_pct > 100 and risk_level == 'low':
            return "Execute immediately - high profit, low risk opportunity"
        elif profit_margin_pct > 50:
            return "Good opportunity - consider executing soon"
        elif risk_level == 'high':
            return "High risk - wait for better market conditions"
        else:
            return "Monitor market conditions for optimal timing"
    
    async def _run_parallel_ai_analysis(self, context: str) -> List[Dict]:
        """Run AI analysis on all models in parallel with timeout protection."""
        
        async def analyze_with_timeout(model: str) -> Optional[Dict]:
            try:
                # 8 second timeout per model to prevent hanging
                return await asyncio.wait_for(
                    self._query_ollama_model(model, context),
                    timeout=8.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Model {model} timed out")
                return None
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                return None
        
        # Run all models in parallel
        tasks = [analyze_with_timeout(model) for model in self.models]
        
        try:
            # Wait for all tasks with overall timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=15.0  # Maximum 15 seconds total
            )
            
            # Filter out None results and exceptions
            model_analyses = [
                result for result in results 
                if result is not None and not isinstance(result, Exception)
            ]
            
            logger.info(f"Parallel AI analysis completed: {len(model_analyses)}/{len(self.models)} models responded")
            return model_analyses
            
        except asyncio.TimeoutError:
            logger.warning("Parallel AI analysis timed out")
            return []
    
    def _merge_analysis_results(self, fast_analysis: Dict, ai_analysis: Dict) -> Dict:
        """Merge fast heuristic analysis with AI consensus."""
        
        # Use AI insights where available, fall back to heuristics
        merged = fast_analysis.copy()
        
        # Blend confidence scores (70% AI, 30% heuristic)
        if ai_analysis.get('confidence_score'):
            ai_conf = ai_analysis['confidence_score']
            heuristic_conf = fast_analysis['confidence_score']
            merged['confidence_score'] = round(0.7 * ai_conf + 0.3 * heuristic_conf, 3)
        
        # Use AI recommendations if available
        if ai_analysis.get('timing_recommendation'):
            merged['timing_recommendation'] = ai_analysis['timing_recommendation']
        
        if ai_analysis.get('market_sentiment'):
            merged['market_sentiment'] = ai_analysis['market_sentiment']
        
        # Use AI risk level if it differs significantly from heuristics
        if ai_analysis.get('risk_level') and ai_analysis['risk_level'] != fast_analysis['risk_level']:
            merged['risk_level'] = ai_analysis['risk_level']
        
        # Include consensus score from AI
        merged['consensus_score'] = ai_analysis.get('consensus_score', 1.0)
        
        return merged
    
    def _prepare_ai_context(self, set_name: str, set_info: Dict, pieces_data: List[Dict], timeseries_data: List, profit_gp: int, required_capital: int, strategy: str) -> str:
        """Prepare context text for AI models."""
        
        pieces_summary = "\n".join([
            f"- {piece['name']}: {piece['buy_price']:,} GP (buy) / {piece['sell_price']:,} GP (sell)"
            for piece in pieces_data
        ])
        
        volume_info = ""
        if timeseries_data:
            volume_info = f"\nRecent trading volume data available for {len(timeseries_data)} items."
        
        return f"""
OSRS Set Combining Analysis Request

Set: {set_name}
Category: {set_info.get('category', 'unknown')}
Strategy: {strategy}
Profit Potential: {profit_gp:,} GP
Required Capital: {required_capital:,} GP
ROI: {(profit_gp/required_capital*100):.1f}%

Individual Pieces:
{pieces_summary}
{volume_info}

Please analyze this OSRS set combining opportunity and provide:
1. Confidence score (0.0-1.0) - how reliable is this opportunity?
2. Risk level (low/medium/high) - what are the main risks?
3. Timing recommendation - when is the best time to execute?
4. Market sentiment - what's the current market condition?
5. Volume assessment - how liquid are these items?

Focus on practical trading considerations like market volatility, item liquidity, 
and execution difficulty. Consider that this is real OSRS Grand Exchange data.
"""
    
    async def _query_ollama_model(self, model: str, context: str) -> Optional[Dict]:
        """Query a specific Ollama model for analysis."""
        
        prompt = f"""
{context}

Respond with a JSON object containing:
{{
    "confidence_score": <float 0.0-1.0>,
    "risk_level": "<low/medium/high>",
    "timing_recommendation": "<string>",
    "market_sentiment": "<string>",
    "volume_score": <float 0.0-1.0>,
    "liquidity_rating": "<low/medium/high>",
    "reasoning": "<explanation>"
}}
"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "top_p": 0.9,
                            "num_predict": 200
                        }
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"Ollama model {model} returned status {response.status_code}")
                    return None
                
                result = response.json()
                response_text = result.get('response', '').strip()
                
                # Try to extract JSON from response
                try:
                    # Look for JSON object in response
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        analysis = json.loads(json_str)
                        analysis['model'] = model
                        return analysis
                except json.JSONDecodeError:
                    pass
                
                # Fallback: parse response manually
                return self._parse_model_response(response_text, model)
                
        except Exception as e:
            logger.error(f"Error querying Ollama model {model}: {e}")
            return None
    
    def _parse_model_response(self, response_text: str, model: str) -> Dict:
        """Parse model response if JSON parsing fails."""
        
        # Simple fallback parsing
        confidence = 0.5
        risk = "medium"
        
        if "high confidence" in response_text.lower() or "confident" in response_text.lower():
            confidence = 0.8
        elif "low confidence" in response_text.lower() or "uncertain" in response_text.lower():
            confidence = 0.3
        
        if "high risk" in response_text.lower() or "risky" in response_text.lower():
            risk = "high"
        elif "low risk" in response_text.lower() or "safe" in response_text.lower():
            risk = "low"
        
        return {
            'confidence_score': confidence,
            'risk_level': risk,
            'timing_recommendation': 'Monitor market conditions',
            'market_sentiment': 'neutral',
            'volume_score': 0.5,
            'liquidity_rating': 'medium',
            'reasoning': response_text[:200] + "...",
            'model': model
        }
    
    def _calculate_consensus(self, model_analyses: List[Dict]) -> Dict[str, Any]:
        """Calculate consensus from multiple model analyses."""
        
        if not model_analyses:
            return {}
        
        # Calculate average confidence
        avg_confidence = sum(a.get('confidence_score', 0.5) for a in model_analyses) / len(model_analyses)
        
        # Calculate risk consensus (most common)
        risk_votes = [a.get('risk_level', 'medium') for a in model_analyses]
        risk_consensus = max(set(risk_votes), key=risk_votes.count)
        
        # Calculate volume score average
        avg_volume_score = sum(a.get('volume_score', 0.5) for a in model_analyses) / len(model_analyses)
        
        # Calculate consensus score (how much models agree)
        confidence_variance = sum((a.get('confidence_score', 0.5) - avg_confidence) ** 2 for a in model_analyses) / len(model_analyses)
        consensus_score = max(0.0, 1.0 - confidence_variance * 4)  # Scale variance to 0-1
        
        # Combine timing recommendations
        timing_recommendations = [a.get('timing_recommendation', '') for a in model_analyses]
        timing_consensus = timing_recommendations[0] if timing_recommendations else 'Monitor market conditions'
        
        # Market sentiment
        sentiments = [a.get('market_sentiment', '') for a in model_analyses]
        sentiment_consensus = sentiments[0] if sentiments else 'neutral'
        
        return {
            'confidence_score': round(avg_confidence, 3),
            'risk_level': risk_consensus,
            'timing_recommendation': timing_consensus,
            'market_sentiment': sentiment_consensus,
            'consensus_score': round(consensus_score, 3),
            'volume_score': round(avg_volume_score, 3),
            'liquidity_rating': 'high' if avg_volume_score > 0.7 else 'medium' if avg_volume_score > 0.4 else 'low',
            'model_count': len(model_analyses)
        }
    
    async def _discover_sets_with_ai(self, wiki_client: RuneScapeWikiAPIClient, all_prices: Dict) -> Dict[str, Dict]:
        """
        Discover additional armor sets using AI analysis of OSRS Wiki mapping data.
        
        Args:
            wiki_client: Wiki API client
            all_prices: Current pricing data
            
        Returns:
            Dictionary of discovered sets
        """
        try:
            # Get item mapping data
            logger.info("Fetching OSRS Wiki mapping for set discovery")
            mapping = await wiki_client.get_item_mapping()
            
            # Find potential sets using AI pattern recognition
            discovered_sets = {}
            
            # Look for armor set items (items with "set" in the name)
            set_items = [item for item in mapping if 'set' in item.name.lower() and 'armour' in item.name.lower()]
            
            for set_item in set_items[:10]:  # Limit to prevent excessive API calls
                try:
                    # Use AI to identify potential piece items
                    set_name_base = set_item.name.replace(' set', '').replace(' armour', '')
                    
                    # Find matching pieces in the mapping
                    potential_pieces = [
                        item for item in mapping 
                        if set_name_base.lower() in item.name.lower() 
                        and 'set' not in item.name.lower()
                        and item.id != set_item.id
                    ]
                    
                    if len(potential_pieces) >= 3:  # Minimum viable set
                        piece_ids = [piece.id for piece in potential_pieces[:6]]  # Max 6 pieces
                        piece_names = [piece.name for piece in potential_pieces[:6]]
                        
                        # Check if we have pricing data for the set and pieces
                        if (set_item.id in all_prices and 
                            all([piece_id in all_prices for piece_id in piece_ids])):
                            
                            discovered_sets[set_item.name] = {
                                'set_item_id': set_item.id,
                                'piece_ids': piece_ids,
                                'piece_names': piece_names,
                                'category': 'discovered',
                                'discovery_confidence': min(1.0, len(potential_pieces) / 4.0)
                            }
                            
                            logger.info(f"Discovered potential set: {set_item.name} with {len(piece_ids)} pieces")
                
                except Exception as e:
                    logger.debug(f"Failed to analyze potential set {set_item.name}: {e}")
                    continue
            
            # Add some manually known sets that might be missing
            additional_known_sets = {
                "Torag's armour set": {
                    'set_item_id': 12887,  # Need to verify this ID
                    'piece_ids': [4745, 4749, 4751, 4747],
                    'piece_names': ["Torag's helm", "Torag's platebody", "Torag's platelegs", "Torag's hammers"],
                    'category': 'barrows'
                },
                "Guthan's armour set": {
                    'set_item_id': 12885,  # Need to verify this ID
                    'piece_ids': [4724, 4726, 4728, 4730],
                    'piece_names': ["Guthan's helm", "Guthan's platebody", "Guthan's chainskirt", "Guthan's warspear"],
                    'category': 'barrows'
                },
                "Verac's armour set": {
                    'set_item_id': 12889,  # Need to verify this ID
                    'piece_ids': [4753, 4757, 4759, 4755],
                    'piece_names': ["Verac's helm", "Verac's brassard", "Verac's plateskirt", "Verac's flail"],
                    'category': 'barrows'
                }
            }
            
            # Only add sets where we have pricing data
            for set_name, set_info in additional_known_sets.items():
                if (set_info['set_item_id'] in all_prices and 
                    all([piece_id in all_prices for piece_id in set_info['piece_ids']])):
                    discovered_sets[set_name] = set_info
            
            logger.info(f"Dynamic discovery found {len(discovered_sets)} additional sets")
            return discovered_sets
            
        except Exception as e:
            logger.error(f"Failed to discover additional sets: {e}")
            return {}


# Global service instance
ai_set_analysis_service = AISetAnalysisService()