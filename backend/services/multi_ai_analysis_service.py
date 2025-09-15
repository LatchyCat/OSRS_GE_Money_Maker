"""
Multi-AI analysis service using three Ollama models for comprehensive trading analysis.

Uses Gemma 3:1B, DeepSeek R1:1.5B, and Qwen 3:4B for consensus-based opportunity scoring.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import ollama
from django.conf import settings
from django.core.cache import cache

from .hybrid_search_service import TradingOpportunity, SearchResult
from .runescape_wiki_client import WikiPriceData

logger = logging.getLogger(__name__)


@dataclass
class AIModelConfig:
    """Configuration for an AI model."""
    name: str
    model_id: str
    specialization: str
    temperature: float
    max_tokens: int
    weight: float  # Weight in consensus scoring


@dataclass
class AIAnalysisResult:
    """Result from a single AI model analysis."""
    model_name: str
    confidence_score: float
    risk_assessment: str
    profit_prediction: float
    market_timing: str
    reasoning: List[str]
    recommendations: List[str]
    execution_strategy: str
    success_probability: float
    raw_response: str


@dataclass
class ConsensusAnalysis:
    """Consensus analysis from multiple AI models."""
    opportunity_id: str
    consensus_confidence: float
    consensus_risk: str
    consensus_profit: float
    consensus_timing: str
    model_agreement: float  # How much models agree (0-1)
    individual_analyses: List[AIAnalysisResult]
    final_recommendations: List[str]
    execution_plan: Dict[str, Any]
    uncertainty_factors: List[str]


class MultiAIAnalysisService:
    """
    Service for analyzing trading opportunities using multiple AI models.
    
    Each model brings different strengths:
    - Gemma 3:1B: Fast risk assessment and basic profitability
    - DeepSeek R1:1.5B: Market trend analysis and reasoning
    - Qwen 3:4B: Complex strategy optimization and detailed analysis
    """
    
    def __init__(self):
        self.client = ollama.Client(
            host=getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        )
        
        # Configure AI models
        self.models = {
            'gemma': AIModelConfig(
                name='Gemma Risk Analyzer',
                model_id='gemma2:2b',  # Use available model
                specialization='Risk Assessment & Quick Analysis',
                temperature=0.3,
                max_tokens=500,
                weight=0.25
            ),
            'deepseek': AIModelConfig(
                name='DeepSeek Market Analyst',
                model_id='deepseek-r1:1.5b',
                specialization='Market Trends & Reasoning',
                temperature=0.5,
                max_tokens=800,
                weight=0.35
            ),
            'qwen': AIModelConfig(
                name='Qwen Strategy Optimizer',
                model_id='qwen2.5:3b',  # Use available model size
                specialization='Strategy Optimization & Planning',
                temperature=0.4,
                max_tokens=1000,
                weight=0.40
            )
        }
        
        # Cache settings
        self.cache_prefix = "ai_analysis:"
        self.cache_timeout = 1800  # 30 minutes
        
        # Analysis templates
        self.analysis_templates = {
            'decanting': self._get_decanting_prompt_template(),
            'flipping': self._get_flipping_prompt_template(),
            'general': self._get_general_prompt_template()
        }
    
    def _get_decanting_prompt_template(self) -> str:
        """Get prompt template for decanting analysis."""
        return """You are an expert OSRS (Old School RuneScape) trader analyzing a decanting opportunity.

OPPORTUNITY DATA:
Item: {item_name}
Category: {category}
From Dose: {from_dose} -> To Dose: {to_dose}
Buy Price: {from_price:,} GP
Sell Price: {to_price:,} GP
Potential Profit: {profit:,} GP per conversion
Market Data Age: {data_age}h
Price Data Quality: {data_quality}

MARKET CONTEXT:
- Current GE spread: {price_spread:.1f}%
- Trading volume: {volume_info}
- Recent price trend: {price_trend}
- Data freshness: {freshness}

ANALYSIS REQUIRED:
1. Risk Assessment (low/medium/high)
2. Confidence Score (0.0-1.0)
3. Profit Prediction (GP per hour)
4. Market Timing (immediate/wait/avoid)
5. Success Probability (0.0-1.0)

Please analyze this opportunity considering:
- GE tax (2% on sales)
- Time required for conversions
- Market volatility
- Competition from other players
- Item liquidity and demand

Format your response as JSON:
{{
    "confidence_score": 0.0-1.0,
    "risk_assessment": "low/medium/high",
    "profit_prediction": estimated_gp_per_hour,
    "market_timing": "immediate/wait/avoid",
    "reasoning": ["reason1", "reason2", "reason3"],
    "recommendations": ["rec1", "rec2", "rec3"],
    "execution_strategy": "detailed_strategy",
    "success_probability": 0.0-1.0
}}"""
    
    def _get_flipping_prompt_template(self) -> str:
        """Get prompt template for flipping analysis."""
        return """You are an expert OSRS trader analyzing a flipping opportunity.

OPPORTUNITY DATA:
Item: {item_name}
Category: {category}
Current Buy Price: {buy_price:,} GP
Current Sell Price: {sell_price:,} GP
Potential Profit: {profit:,} GP per flip
GE Limit: {ge_limit}/4h
Market Data Age: {data_age}h

Analyze this flipping opportunity and respond in JSON format with the same structure as the decanting template."""
    
    def _get_general_prompt_template(self) -> str:
        """Get general analysis template."""
        return """You are an expert OSRS trader analyzing a trading opportunity.

OPPORTUNITY DATA:
{opportunity_data}

Provide detailed analysis in JSON format with confidence, risk, profit prediction, timing, reasoning, recommendations, execution strategy, and success probability."""
    
    async def ensure_models_available(self) -> Dict[str, bool]:
        """Ensure all AI models are available."""
        model_status = {}
        
        for model_key, config in self.models.items():
            try:
                # Check if model exists
                models = await asyncio.to_thread(self.client.list)
                model_names = [m.model for m in models.models] if hasattr(models, 'models') else []
                
                if config.model_id not in model_names:
                    logger.info(f"Pulling model {config.model_id}...")
                    await asyncio.to_thread(self.client.pull, config.model_id)
                    logger.info(f"Successfully pulled {config.model_id}")
                
                model_status[model_key] = True
                
            except Exception as e:
                logger.error(f"Failed to ensure {config.model_id} availability: {e}")
                model_status[model_key] = False
        
        return model_status
    
    async def analyze_opportunity(
        self,
        opportunity: TradingOpportunity,
        context_data: Optional[Dict] = None
    ) -> ConsensusAnalysis:
        """
        Analyze a trading opportunity using all AI models.
        
        Args:
            opportunity: The trading opportunity to analyze
            context_data: Additional context for analysis
            
        Returns:
            Consensus analysis from all models
        """
        logger.info(f"Analyzing opportunity: {opportunity.name} ({opportunity.opportunity_type})")
        
        # Check cache first
        cache_key = f"{self.cache_prefix}{opportunity.item_id}_{hash(str(opportunity.market_context))}"
        cached_analysis = cache.get(cache_key)
        if cached_analysis:
            logger.info("Using cached AI analysis")
            return cached_analysis
        
        # Ensure models are available
        model_status = await self.ensure_models_available()
        available_models = [k for k, v in model_status.items() if v]
        
        if not available_models:
            raise Exception("No AI models available for analysis")
        
        # Run analysis on all available models
        analysis_tasks = []
        for model_key in available_models:
            task = self._analyze_with_model(model_key, opportunity, context_data)
            analysis_tasks.append(task)
        
        # Execute analyses in parallel
        individual_analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Filter successful analyses
        successful_analyses = []
        for i, analysis in enumerate(individual_analyses):
            if isinstance(analysis, AIAnalysisResult):
                successful_analyses.append(analysis)
            else:
                model_key = available_models[i]
                logger.error(f"Analysis failed for {model_key}: {analysis}")
        
        if not successful_analyses:
            raise Exception("All AI analyses failed")
        
        # Generate consensus
        consensus = await self._generate_consensus(opportunity, successful_analyses)
        
        # Cache the result
        cache.set(cache_key, consensus, self.cache_timeout)
        
        logger.info(f"Completed AI analysis with {len(successful_analyses)} models")
        return consensus
    
    async def _analyze_with_model(
        self,
        model_key: str,
        opportunity: TradingOpportunity,
        context_data: Optional[Dict]
    ) -> AIAnalysisResult:
        """Analyze opportunity with a specific AI model."""
        config = self.models[model_key]
        
        try:
            # Prepare prompt
            prompt = self._prepare_prompt(opportunity, context_data)
            
            # Generate analysis
            response = await asyncio.to_thread(
                self._call_model,
                config.model_id,
                prompt,
                config.temperature,
                config.max_tokens
            )
            
            # Parse response
            parsed_result = self._parse_ai_response(response, config.name)
            
            logger.info(f"Model {config.name} completed analysis")
            return parsed_result
            
        except Exception as e:
            logger.error(f"Analysis failed for model {config.name}: {e}")
            raise e
    
    def _call_model(self, model_id: str, prompt: str, temperature: float, max_tokens: int) -> str:
        """Call Ollama model synchronously."""
        response = self.client.generate(
            model=model_id,
            prompt=prompt,
            options={
                'temperature': temperature,
                'num_predict': max_tokens,
                'top_k': 40,
                'top_p': 0.9
            }
        )
        
        return response['response']
    
    def _prepare_prompt(self, opportunity: TradingOpportunity, context_data: Optional[Dict]) -> str:
        """Prepare analysis prompt for the opportunity."""
        template = self.analysis_templates.get(
            opportunity.opportunity_type,
            self.analysis_templates['general']
        )
        
        # Prepare context variables
        market_context = opportunity.market_context
        price_data = opportunity.price_data
        
        prompt_vars = {
            'item_name': opportunity.name,
            'category': opportunity.category,
            'profit': opportunity.profit_potential,
            'data_age': price_data.age_hours,
            'data_quality': price_data.data_quality,
            'price_spread': 0.0,  # Will calculate
            'volume_info': 'Unknown',
            'price_trend': 'Unknown',
            'freshness': price_data.data_quality
        }
        
        # Add decanting-specific variables
        if opportunity.opportunity_type == 'decanting':
            prompt_vars.update({
                'from_dose': market_context.get('from_dose', 'Unknown'),
                'to_dose': market_context.get('to_dose', 'Unknown'),
                'from_price': market_context.get('from_price', 0),
                'to_price': market_context.get('to_price', 0)
            })
            
            # Calculate price spread
            if price_data.high_price and price_data.low_price:
                spread = abs(price_data.high_price - price_data.low_price)
                avg_price = (price_data.high_price + price_data.low_price) / 2
                prompt_vars['price_spread'] = (spread / avg_price * 100) if avg_price > 0 else 0
        
        # Add flipping-specific variables
        elif opportunity.opportunity_type == 'flipping':
            prompt_vars.update({
                'buy_price': market_context.get('buy_price', 0),
                'sell_price': market_context.get('sell_price', 0),
                'ge_limit': market_context.get('ge_limit', 'Unknown')
            })
        
        return template.format(**prompt_vars)
    
    def _parse_ai_response(self, response: str, model_name: str) -> AIAnalysisResult:
        """Parse AI model response into structured result."""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                parsed_data = json.loads(json_str)
            else:
                # Fallback: try to parse the entire response
                parsed_data = json.loads(response)
            
            return AIAnalysisResult(
                model_name=model_name,
                confidence_score=float(parsed_data.get('confidence_score', 0.5)),
                risk_assessment=parsed_data.get('risk_assessment', 'medium'),
                profit_prediction=float(parsed_data.get('profit_prediction', 0)),
                market_timing=parsed_data.get('market_timing', 'wait'),
                reasoning=parsed_data.get('reasoning', []),
                recommendations=parsed_data.get('recommendations', []),
                execution_strategy=parsed_data.get('execution_strategy', ''),
                success_probability=float(parsed_data.get('success_probability', 0.5)),
                raw_response=response
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse AI response from {model_name}: {e}")
            
            # Fallback: create basic analysis
            return AIAnalysisResult(
                model_name=model_name,
                confidence_score=0.3,
                risk_assessment='unknown',
                profit_prediction=0.0,
                market_timing='wait',
                reasoning=[f"Parse error: {str(e)}"],
                recommendations=["Manual review required"],
                execution_strategy="Could not generate strategy",
                success_probability=0.3,
                raw_response=response
            )
    
    async def _generate_consensus(
        self,
        opportunity: TradingOpportunity,
        analyses: List[AIAnalysisResult]
    ) -> ConsensusAnalysis:
        """Generate consensus analysis from individual model results."""
        
        if not analyses:
            raise ValueError("No analyses to generate consensus from")
        
        # Weight analyses by model configuration
        weighted_confidence = 0.0
        weighted_profit = 0.0
        weighted_success = 0.0
        total_weight = 0.0
        
        risk_votes = {'low': 0, 'medium': 0, 'high': 0}
        timing_votes = {'immediate': 0, 'wait': 0, 'avoid': 0}
        
        all_reasoning = []
        all_recommendations = []
        
        for analysis in analyses:
            # Find model weight
            model_weight = 0.33  # Default equal weight
            for model_config in self.models.values():
                if model_config.name == analysis.model_name:
                    model_weight = model_config.weight
                    break
            
            # Weighted averages
            weighted_confidence += analysis.confidence_score * model_weight
            weighted_profit += analysis.profit_prediction * model_weight
            weighted_success += analysis.success_probability * model_weight
            total_weight += model_weight
            
            # Votes
            risk_votes[analysis.risk_assessment] += model_weight
            timing_votes[analysis.market_timing] += model_weight
            
            # Collect insights
            all_reasoning.extend(analysis.reasoning)
            all_recommendations.extend(analysis.recommendations)
        
        # Normalize weighted values
        if total_weight > 0:
            consensus_confidence = weighted_confidence / total_weight
            consensus_profit = weighted_profit / total_weight
            consensus_success = weighted_success / total_weight
        else:
            consensus_confidence = sum(a.confidence_score for a in analyses) / len(analyses)
            consensus_profit = sum(a.profit_prediction for a in analyses) / len(analyses)
            consensus_success = sum(a.success_probability for a in analyses) / len(analyses)
        
        # Consensus votes
        consensus_risk = max(risk_votes.items(), key=lambda x: x[1])[0]
        consensus_timing = max(timing_votes.items(), key=lambda x: x[1])[0]
        
        # Calculate model agreement
        confidence_std = np.std([a.confidence_score for a in analyses]) if len(analyses) > 1 else 0
        model_agreement = max(0.0, 1.0 - confidence_std)
        
        # Generate final recommendations
        final_recommendations = self._synthesize_recommendations(
            analyses, consensus_confidence, consensus_risk, consensus_timing
        )
        
        # Create execution plan
        execution_plan = self._create_execution_plan(
            opportunity, consensus_timing, consensus_profit, analyses
        )
        
        # Identify uncertainty factors
        uncertainty_factors = self._identify_uncertainty_factors(analyses, model_agreement)
        
        return ConsensusAnalysis(
            opportunity_id=f"{opportunity.item_id}_{opportunity.opportunity_type}",
            consensus_confidence=consensus_confidence,
            consensus_risk=consensus_risk,
            consensus_profit=consensus_profit,
            consensus_timing=consensus_timing,
            model_agreement=model_agreement,
            individual_analyses=analyses,
            final_recommendations=final_recommendations,
            execution_plan=execution_plan,
            uncertainty_factors=uncertainty_factors
        )
    
    def _synthesize_recommendations(
        self,
        analyses: List[AIAnalysisResult],
        consensus_confidence: float,
        consensus_risk: str,
        consensus_timing: str
    ) -> List[str]:
        """Synthesize final recommendations from all analyses."""
        recommendations = []
        
        # Base recommendation
        if consensus_confidence >= 0.7 and consensus_timing == 'immediate':
            recommendations.append("✅ Highly recommended - Execute immediately")
        elif consensus_confidence >= 0.5 and consensus_timing in ['immediate', 'wait']:
            recommendations.append("⚠️ Proceed with caution - Monitor closely")
        else:
            recommendations.append("❌ Not recommended - High risk or uncertainty")
        
        # Risk-specific advice
        if consensus_risk == 'high':
            recommendations.append("🔴 High risk - Consider smaller position sizes")
        elif consensus_risk == 'medium':
            recommendations.append("🟡 Medium risk - Standard position sizing")
        else:
            recommendations.append("🟢 Low risk - Suitable for larger positions")
        
        # Add most common recommendations from models
        all_recs = []
        for analysis in analyses:
            all_recs.extend(analysis.recommendations)
        
        # Find most frequent recommendations
        from collections import Counter
        rec_counts = Counter(all_recs)
        top_recs = [rec for rec, count in rec_counts.most_common(3) if count > 1]
        recommendations.extend(top_recs)
        
        return recommendations[:5]  # Limit to top 5
    
    def _create_execution_plan(
        self,
        opportunity: TradingOpportunity,
        timing: str,
        profit: float,
        analyses: List[AIAnalysisResult]
    ) -> Dict[str, Any]:
        """Create execution plan based on consensus."""
        plan = {
            'timing': timing,
            'expected_profit': profit,
            'steps': [],
            'risk_mitigation': [],
            'monitoring': []
        }
        
        if opportunity.opportunity_type == 'decanting':
            plan['steps'] = [
                "1. Buy source potions at market price",
                "2. Use barbarian training to decant",
                "3. Sell converted potions",
                "4. Monitor profit margins"
            ]
        
        # Add risk mitigation
        plan['risk_mitigation'] = [
            "Monitor price movements before execution",
            "Start with small test quantities",
            "Set stop-loss limits if prices move against position"
        ]
        
        # Add monitoring recommendations
        plan['monitoring'] = [
            "Check prices every 30 minutes during active trading",
            "Monitor competing offers in GE",
            "Track overall market sentiment"
        ]
        
        return plan
    
    def _identify_uncertainty_factors(
        self,
        analyses: List[AIAnalysisResult],
        model_agreement: float
    ) -> List[str]:
        """Identify factors that create uncertainty in the analysis."""
        factors = []
        
        if model_agreement < 0.7:
            factors.append("Low model agreement - conflicting predictions")
        
        # Check for data quality issues
        data_quality_mentioned = any(
            'data' in ' '.join(analysis.reasoning).lower() or 
            'stale' in ' '.join(analysis.reasoning).lower()
            for analysis in analyses
        )
        
        if data_quality_mentioned:
            factors.append("Data quality concerns mentioned by models")
        
        # Check confidence spread
        confidences = [a.confidence_score for a in analyses]
        if max(confidences) - min(confidences) > 0.3:
            factors.append("Wide confidence range between models")
        
        return factors


# Global service instance
multi_ai_service = MultiAIAnalysisService()