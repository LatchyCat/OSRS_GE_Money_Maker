"""
AI-Enhanced Decanting Service

Integrates RuneScape Wiki pricing, vector embeddings, hybrid search, and multi-AI analysis
for intelligent decanting opportunity discovery and optimization.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

from django.core.cache import cache
from django.utils import timezone

from .runescape_wiki_client import RuneScapeWikiAPIClient
from .unified_wiki_price_client import UnifiedPriceClient
from .hybrid_search_service import HybridSearchService, TradingOpportunity
from .multi_ai_analysis_service import MultiAIAnalysisService, ConsensusAnalysis
from apps.items.models import Item

logger = logging.getLogger(__name__)


@dataclass
class AIDecantingOpportunity:
    """Enhanced decanting opportunity with AI insights."""
    # Basic opportunity data
    item_id: int
    name: str
    from_dose: int
    to_dose: int
    from_item_id: int
    to_item_id: int
    
    # Price and profit data
    buy_price: int
    sell_price: int
    profit_per_conversion: int
    profit_per_hour: int
    roi_percentage: float
    
    # Market data
    price_spread: float
    data_freshness: str
    trading_volume: int
    liquidity_score: float
    
    # AI analysis results
    ai_confidence: float
    ai_risk_level: str
    ai_timing: str
    ai_success_probability: float
    ai_recommendations: List[str]
    model_agreement: float
    
    # Execution planning
    execution_strategy: str
    estimated_time_per_conversion: int
    max_hourly_conversions: int
    capital_requirement: int
    
    # Additional context
    market_context: Dict[str, Any]
    uncertainty_factors: List[str]
    similar_opportunities: List[int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization."""
        return asdict(self)


class AIEnhancedDecantingService:
    """
    Advanced decanting service powered by multiple AI models and comprehensive market data.
    
    Features:
    - RuneScape Wiki API for accurate pricing
    - Vector embeddings for opportunity discovery
    - Hybrid search for intelligent filtering
    - Multi-AI consensus analysis (Gemma, DeepSeek, Qwen)
    - Real-time market condition assessment
    """
    
    def __init__(self, performance_mode=True):
        # PERFORMANCE MODE: Disable heavy AI features to prevent system overload
        self.performance_mode = performance_mode
        
        # Core services
        self.wiki_client = RuneScapeWikiAPIClient()
        self.price_client = UnifiedPriceClient()
        
        # Only initialize heavy AI services in non-performance mode
        if not self.performance_mode:
            self.search_service = HybridSearchService()
            self.ai_service = MultiAIAnalysisService()
        else:
            self.search_service = None
            self.ai_service = None
            logger.warning("🚀 PERFORMANCE MODE: AI services disabled to prevent system overload")
        
        # Service state
        self._initialized = False
        
        # Configuration
        self.cache_timeout = 1800  # 30 minutes
        self.min_profit_threshold = 10  # Minimum 10 GP profit for more opportunities
        self.max_opportunities = 50  # Limit results
        
        # High-value potion families for priority analysis with dose mapping
        self.priority_potions = {
            'Prayer potion': [2434, 139, 141, 143],
            'Super restore': [3024, 3026, 3028, 3030],
            'Stamina potion': [12625, 12627, 12629, 12631],
            'Divine super combat potion': [23685, 23688, 23691, 23694],
            'Divine ranging potion': [23733, 23736, 23739, 23742],
            'Divine magic potion': [23757, 23760, 23763, 23766],
            'Saradomin brew': [6685, 6687, 6689, 6691],
            'Extended antifire': [11951, 11953, 11955, 11957]
        }
        
        # Dose mapping - maps item ID to dose level (assuming typical pattern: 1,2,3,4 dose order)
        self.dose_mapping = {}
        for family_name, item_ids in self.priority_potions.items():
            if len(item_ids) >= 4:  # Typical 4-dose pattern
                self.dose_mapping.update({
                    item_ids[0]: 1,  # 1-dose
                    item_ids[1]: 2,  # 2-dose  
                    item_ids[2]: 3,  # 3-dose
                    item_ids[3]: 4   # 4-dose
                })
            elif len(item_ids) == 3:  # 3-dose pattern
                self.dose_mapping.update({
                    item_ids[0]: 1,  # 1-dose
                    item_ids[1]: 2,  # 2-dose
                    item_ids[2]: 3   # 3-dose
                })
            elif len(item_ids) == 2:  # 2-dose pattern
                self.dose_mapping.update({
                    item_ids[0]: 1,  # 1-dose
                    item_ids[1]: 2   # 2-dose
                })
    
    async def initialize(self):
        """Initialize services (lightweight in performance mode)."""
        if self._initialized:
            return
            
        if self.performance_mode:
            logger.info("🚀 PERFORMANCE MODE: Quick initialization (AI features disabled)")
            self._initialized = True
            return
            
        logger.info("Initializing AI-Enhanced Decanting Service...")
        
        try:
            # Initialize heavy AI services only in non-performance mode
            init_tasks = []
            if self.search_service:
                init_tasks.append(self.search_service.initialize())
            if self.ai_service:
                init_tasks.append(self.ai_service.ensure_models_available())
            
            if init_tasks:
                await asyncio.gather(*init_tasks)
            
            self._initialized = True
            
            logger.info("AI-Enhanced Decanting Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI services: {e}")
            raise
    
    async def discover_ai_opportunities(
        self,
        min_profit: int = 100,
        max_risk: str = "medium",
        min_confidence: float = 0.5,
        force_refresh: bool = False
    ) -> List[AIDecantingOpportunity]:
        """
        Discover decanting opportunities using AI-powered analysis.
        Prioritizes high-value potions first, then fills with other opportunities.
        
        Args:
            min_profit: Minimum profit per conversion in GP
            max_risk: Maximum acceptable risk level
            min_confidence: Minimum AI confidence threshold
            
        Returns:
            List of AI-analyzed decanting opportunities, sorted by profit
        """
        if not self._initialized:
            await self.initialize()
        
        logger.info(f"Discovering AI opportunities (profit≥{min_profit}, risk≤{max_risk}, confidence≥{min_confidence})")
        
        # Check cache first (skip if force refresh)
        cache_key = f"ai_decanting:{min_profit}_{max_risk}_{min_confidence}"
        cached_opportunities = None if force_refresh else cache.get(cache_key)
        if cached_opportunities and not force_refresh:
            logger.info("Using cached AI opportunities")
            return cached_opportunities
        
        if force_refresh:
            logger.info("🔄 FORCE REFRESH: Bypassing cache and generating fresh opportunities")
        
        try:
            ai_opportunities = []
            
            # Step 1: Prioritize high-value potions first (works in both modes)
            logger.info("Analyzing priority high-value potion families...")
            priority_opportunities = await self.get_priority_analysis()
            
            # Filter priority opportunities by criteria
            for opp in priority_opportunities:
                if (opp.profit_per_conversion >= min_profit and
                    self._risk_level_acceptable(opp.ai_risk_level, max_risk) and
                    opp.ai_confidence >= min_confidence):
                    ai_opportunities.append(opp)
            
            logger.info(f"Found {len(ai_opportunities)} qualifying priority opportunities")
            
            # Step 2: Skip hybrid search in performance mode (AI services disabled)
            if self.performance_mode:
                logger.info("🚀 PERFORMANCE MODE: Skipping hybrid search to reduce resource usage")
            elif len(ai_opportunities) < self.max_opportunities and self.search_service:
                remaining_slots = self.max_opportunities - len(ai_opportunities)
                logger.info(f"Searching for {remaining_slots} additional opportunities via hybrid search...")
                
                search_opportunities = await self.search_service.find_decanting_opportunities(
                    min_profit=max(min_profit, 50),  # Lower threshold for additional opportunities
                    risk_level=max_risk
                )
                
                logger.info(f"Found {len(search_opportunities)} additional opportunities from hybrid search")
                
                # Process additional opportunities in batches to manage AI model load
                batch_size = 5
                already_analyzed_items = {opp.name for opp in ai_opportunities}
                
                for i in range(0, len(search_opportunities), batch_size):
                    if len(ai_opportunities) >= self.max_opportunities:
                        break
                        
                    batch = search_opportunities[i:i + batch_size]
                    
                    # Skip items we've already analyzed in priority analysis
                    filtered_batch = [opp for opp in batch if opp.name not in already_analyzed_items]
                    if not filtered_batch:
                        continue
                    
                    # Analyze batch in parallel
                    analysis_tasks = [
                        self._analyze_opportunity_with_ai(opp)
                        for opp in filtered_batch
                    ]
                    
                    batch_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
                    
                    # Process results
                    for opp, result in zip(filtered_batch, batch_results):
                        if len(ai_opportunities) >= self.max_opportunities:
                            break
                            
                        if isinstance(result, Exception):
                            logger.warning(f"AI analysis failed for {opp.name}: {result}")
                            continue
                        
                        ai_opp = result
                        
                        # Filter by AI criteria (more lenient for additional opportunities)
                        if (ai_opp.ai_confidence >= max(min_confidence - 0.1, 0.3) and
                            self._risk_level_acceptable(ai_opp.ai_risk_level, max_risk) and
                            ai_opp.profit_per_conversion >= max(min_profit, 50)):
                            ai_opportunities.append(ai_opp)
                    
                    # Small delay between batches
                    if i + batch_size < len(search_opportunities):
                        await asyncio.sleep(0.5)
            
            # Step 3: Sort by profit and AI confidence (prioritize profit over confidence)
            ai_opportunities.sort(
                key=lambda x: (x.profit_per_conversion, x.ai_confidence, x.model_agreement),
                reverse=True
            )
            
            # Ensure we don't exceed max results
            ai_opportunities = ai_opportunities[:self.max_opportunities]
            
            # Cache results
            cache.set(cache_key, ai_opportunities, self.cache_timeout)
            
            logger.info(f"Generated {len(ai_opportunities)} AI-enhanced opportunities")
            return ai_opportunities
            
        except Exception as e:
            logger.error(f"Failed to discover AI opportunities: {e}")
            raise
    
    async def _analyze_opportunity_with_ai(self, opportunity: TradingOpportunity) -> AIDecantingOpportunity:
        """Run comprehensive AI analysis on a trading opportunity."""
        
        # Run AI consensus analysis
        consensus_analysis = await self.ai_service.analyze_opportunity(opportunity)
        
        # Extract market context
        market_ctx = opportunity.market_context
        
        # Calculate enhanced metrics
        profit_per_hour = await self._calculate_profit_per_hour(
            opportunity, consensus_analysis
        )
        
        roi_percentage = (opportunity.profit_potential / market_ctx.get('from_price', 1)) * 100
        
        # Determine execution parameters
        execution_strategy = self._generate_execution_strategy(opportunity, consensus_analysis)
        time_per_conversion = self._estimate_conversion_time(opportunity)
        max_hourly = 3600 // time_per_conversion if time_per_conversion > 0 else 0
        
        # Calculate market metrics
        from_price = market_ctx.get('from_price', 0)
        to_price = market_ctx.get('to_price', 0)
        price_spread = abs(from_price - to_price) / max(from_price, 1) * 100
        
        # Find similar opportunities using embeddings
        similar_opportunities = await self._find_similar_opportunities(opportunity)
        
        return AIDecantingOpportunity(
            item_id=opportunity.item_id,
            name=opportunity.name,
            from_dose=market_ctx.get('from_dose', 0),
            to_dose=market_ctx.get('to_dose', 0),
            from_item_id=market_ctx.get('from_item_id', 0),
            to_item_id=market_ctx.get('to_item_id', 0),
            
            buy_price=from_price,
            sell_price=to_price,
            profit_per_conversion=int(opportunity.profit_potential),
            profit_per_hour=profit_per_hour,
            roi_percentage=roi_percentage,
            
            price_spread=price_spread,
            data_freshness=opportunity.price_data.data_quality,
            trading_volume=0,  # Will enhance with real volume data
            liquidity_score=0.5,  # Placeholder
            
            ai_confidence=consensus_analysis.consensus_confidence,
            ai_risk_level=consensus_analysis.consensus_risk,
            ai_timing=consensus_analysis.consensus_timing,
            ai_success_probability=consensus_analysis.consensus_profit / 100.0,  # Normalize
            ai_recommendations=consensus_analysis.final_recommendations,
            model_agreement=consensus_analysis.model_agreement,
            
            execution_strategy=execution_strategy,
            estimated_time_per_conversion=time_per_conversion,
            max_hourly_conversions=max_hourly,
            capital_requirement=from_price,
            
            market_context=market_ctx,
            uncertainty_factors=consensus_analysis.uncertainty_factors,
            similar_opportunities=similar_opportunities
        )
    
    def _risk_level_acceptable(self, ai_risk: str, max_risk: str) -> bool:
        """Check if AI risk level is acceptable."""
        risk_levels = {"low": 1, "medium": 2, "high": 3}
        return risk_levels.get(ai_risk, 3) <= risk_levels.get(max_risk, 2)
    
    async def _calculate_profit_per_hour(
        self,
        opportunity: TradingOpportunity,
        consensus: ConsensusAnalysis
    ) -> int:
        """Calculate realistic profit per hour considering AI insights."""
        
        base_profit = opportunity.profit_potential
        confidence_multiplier = consensus.consensus_confidence
        
        # Estimate conversions per hour based on potion type and market conditions
        base_conversions_per_hour = 60  # Conservative estimate
        
        # Adjust based on AI timing recommendation
        timing_multipliers = {
            "immediate": 1.0,
            "wait": 0.7,
            "avoid": 0.3
        }
        
        timing_multiplier = timing_multipliers.get(consensus.consensus_timing, 0.5)
        
        # Final calculation
        effective_conversions = base_conversions_per_hour * confidence_multiplier * timing_multiplier
        
        return int(base_profit * effective_conversions)
    
    def _generate_execution_strategy(
        self,
        opportunity: TradingOpportunity,
        consensus: ConsensusAnalysis
    ) -> str:
        """Generate execution strategy based on AI analysis."""
        
        strategies = []
        
        if consensus.consensus_timing == "immediate":
            strategies.append("Execute immediately while market conditions are favorable")
        elif consensus.consensus_timing == "wait":
            strategies.append("Wait for better market entry point")
        
        if consensus.consensus_risk == "low":
            strategies.append("Consider larger position sizes due to low risk")
        elif consensus.consensus_risk == "high":
            strategies.append("Use smaller position sizes and tight stop-losses")
        
        if consensus.model_agreement < 0.7:
            strategies.append("Monitor closely due to model disagreement")
        
        return "; ".join(strategies) if strategies else "Standard execution approach"
    
    def _estimate_conversion_time(self, opportunity: TradingOpportunity) -> int:
        """Estimate time per conversion in seconds."""
        # Base time includes:
        # - Banking time
        # - Decanting time
        # - Market interaction time
        
        base_time = 60  # 1 minute per conversion (conservative)
        
        # Adjust based on potion type
        market_ctx = opportunity.market_context
        from_dose = market_ctx.get('from_dose', 4)
        to_dose = market_ctx.get('to_dose', 1)
        
        # More complex conversions take longer
        complexity_factor = 1.0 + (from_dose - to_dose) * 0.1
        
        return int(base_time * complexity_factor)
    
    async def _find_similar_opportunities(self, opportunity: TradingOpportunity) -> List[int]:
        """Find similar opportunities using vector embeddings."""
        try:
            # Use hybrid search service to find similar items
            similar_results = await self.search_service.hybrid_search(
                f"{opportunity.name} potion similar",
                k=5,
                category_filter="Potion"
            )
            
            return [result.item_id for result in similar_results if result.item_id != opportunity.item_id]
            
        except Exception as e:
            logger.warning(f"Failed to find similar opportunities: {e}")
            return []
    
    async def get_priority_analysis(self) -> List[AIDecantingOpportunity]:
        """Get AI analysis for high-priority potion families."""
        logger.info("Running priority analysis on high-value potions")
        
        priority_opportunities = []
        
        async with self.price_client as client:
            # Get prices for all priority potions
            all_priority_ids = []
            for potion_family, item_ids in self.priority_potions.items():
                all_priority_ids.extend(item_ids)
            
            price_data = await client.get_multiple_best_prices(all_priority_ids)
            logger.info(f"Retrieved price data for {len(price_data)} items")
            
            # Analyze each family
            for family_name, item_ids in self.priority_potions.items():
                logger.info(f"Starting analysis for {family_name}")
                try:
                    family_opportunities = await self._analyze_potion_family(
                        family_name, item_ids, price_data
                    )
                    logger.info(f"Completed {family_name}: found {len(family_opportunities)} opportunities")
                    priority_opportunities.extend(family_opportunities)
                except Exception as e:
                    logger.error(f"Error analyzing {family_name}: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Sort by profit per conversion first, then AI confidence (prioritize profit)
        priority_opportunities.sort(
            key=lambda x: (x.profit_per_conversion, x.ai_confidence, x.profit_per_hour),
            reverse=True
        )
        
        logger.info(f"Generated {len(priority_opportunities)} priority opportunities from {len(self.priority_potions)} families")
        return priority_opportunities  # Return all priority opportunities, let caller decide limits
    
    async def _analyze_potion_family(
        self,
        family_name: str,
        item_ids: List[int],
        price_data: Dict[int, Any]
    ) -> List[AIDecantingOpportunity]:
        """Analyze a specific potion family for decanting opportunities with proper dose logic."""
        
        logger.info(f"Analyzing family: {family_name} with IDs: {item_ids}")
        
        # Log available price data for debugging
        available_items = []
        for item_id in item_ids:
            if item_id in price_data:
                dose_level = self.dose_mapping.get(item_id, 'unknown')
                high_price = price_data[item_id].high_price
                low_price = price_data[item_id].low_price
                logger.info(f"  Item {item_id} ({dose_level}-dose): buy={low_price}, sell={high_price}")
                available_items.append((item_id, dose_level, low_price, high_price))
            else:
                logger.warning(f"  Item {item_id}: NO PRICE DATA")
        
        if len(available_items) < 2:
            logger.warning(f"Not enough price data for {family_name} - need at least 2 items")
            return []
        
        # Find the most profitable decanting opportunity for this family
        # Strategy: Find best combination where we can buy lower-priced doses and sell higher-priced doses
        best_opportunity = None
        best_profit = 0
        
        for buy_item in available_items:
            for sell_item in available_items:
                buy_id, buy_dose, buy_price, _ = buy_item
                sell_id, sell_dose, _, sell_price = sell_item
                
                if buy_id == sell_id or not buy_price or not sell_price:
                    continue
                
                # FIXED: Proper OSRS decanting mechanics
                # In RuneScape, you can only combine lower doses to higher doses (never break down)
                # Strategy: Buy multiple lower-dose potions, combine them into higher-dose potions
                
                # Skip impossible scenarios (can't break down potions in OSRS)
                if buy_dose >= sell_dose:
                    continue
                
                # Only allow realistic dose combinations
                if sell_dose % buy_dose != 0:
                    continue  # Must be valid combination (e.g., 1→2, 1→3, 1→4, 2→4)
                
                # Calculate how many lower-dose potions needed for one higher-dose potion
                doses_needed = sell_dose // buy_dose
                
                # Calculate real costs and profit
                total_buy_cost = buy_price * doses_needed
                sell_price_after_tax = sell_price * 0.99  # 1% GE tax
                
                profit = sell_price_after_tax - total_buy_cost
                
                logger.info(f"    {family_name}: {buy_dose}-dose→{sell_dose}-dose | "
                           f"buy={buy_price}, sell={sell_price_after_tax}, profit={profit:.0f}")
                
                if profit > best_profit and profit >= self.min_profit_threshold:
                    best_profit = profit
                    best_opportunity = {
                        'buy_id': buy_id,
                        'sell_id': sell_id,
                        'buy_dose': buy_dose,
                        'sell_dose': sell_dose,
                        'buy_price': buy_price,  # Price per individual lower-dose potion
                        'sell_price': sell_price_after_tax,  # Price for one higher-dose potion
                        'total_buy_cost': total_buy_cost,  # Cost to buy all needed lower-dose potions
                        'doses_needed': doses_needed,  # How many lower-dose potions needed
                        'profit': profit
                    }
        
        if not best_opportunity:
            logger.info(f"No profitable opportunities found for {family_name}")
            return []
        
        logger.info(f"Best opportunity for {family_name}: "
                   f"{best_opportunity['buy_dose']}-dose→{best_opportunity['sell_dose']}-dose "
                   f"profit={best_opportunity['profit']:.0f}")
        
        # Create the single best opportunity for this family (eliminates duplicates)
        try:
            opportunity = TradingOpportunity(
                item_id=best_opportunity['buy_id'],
                name=f"{family_name} conversion",
                category="Decanting",
                opportunity_type="decanting",
                profit_potential=float(best_opportunity['profit']),
                risk_level="medium",
                confidence_score=0.8,
                market_context={
                    'from_price': best_opportunity['buy_price'],
                    'to_price': best_opportunity['sell_price'],
                    'from_item_id': best_opportunity['buy_id'],
                    'to_item_id': best_opportunity['sell_id'],
                    'profit_per_conversion': best_opportunity['profit']
                },
                ai_insights=[],
                related_items=[best_opportunity['buy_id'], best_opportunity['sell_id']],
                price_data=price_data[best_opportunity['buy_id']]
            )
            
            # Skip AI analysis in performance mode
            if not self.performance_mode:
                # Try AI analysis first
                try:
                    ai_opportunity = await self._analyze_opportunity_with_ai(opportunity)
                    return [ai_opportunity]
                except Exception as e:
                    logger.warning(f"AI analysis failed for {family_name}: {e}")
                    # Fallback to basic opportunity
                    pass
            else:
                logger.debug(f"🚀 PERFORMANCE MODE: Skipping AI analysis for {family_name}")
        except Exception as e:
            logger.warning(f"Failed to create opportunity object for {family_name}: {e}")
        
        # Create fallback opportunity with corrected data
        fallback_opportunity = AIDecantingOpportunity(
            # Basic opportunity data
            item_id=best_opportunity['buy_id'],
            name=f"{family_name} conversion",
            from_dose=best_opportunity['buy_dose'],
            to_dose=best_opportunity['sell_dose'],
            from_item_id=best_opportunity['buy_id'],
            to_item_id=best_opportunity['sell_id'],
            
            # Price and profit data (FIXED: Use correct costs for display)
            buy_price=best_opportunity['total_buy_cost'],  # Total cost for all lower-dose potions needed
            sell_price=best_opportunity['sell_price'],     # Revenue from selling one higher-dose potion
            profit_per_conversion=int(best_opportunity['profit']),
            profit_per_hour=int(best_opportunity['profit'] * 10),  # Realistic: 10 conversions/hour (decanting takes time)
            roi_percentage=(best_opportunity['profit'] / best_opportunity['total_buy_cost']) * 100,
            
            # Market data (FIXED: Use correct spread calculation)
            price_spread=(best_opportunity['sell_price'] - best_opportunity['total_buy_cost']) / best_opportunity['total_buy_cost'] * 100,
            data_freshness="current",
            trading_volume=1000,
            liquidity_score=0.8,
            
            # AI analysis results (defaults since AI failed)
            ai_confidence=0.7,
            ai_risk_level="medium",
            ai_timing="good",
            ai_success_probability=0.75,
            ai_recommendations=["AI analysis unavailable - using price-based analysis"],
            model_agreement=0.0,
            
            # Execution planning (FIXED: Correct strategy description)
            execution_strategy=f"Buy {best_opportunity['doses_needed']}× {family_name} ({best_opportunity['buy_dose']}-dose), combine to 1× {best_opportunity['sell_dose']}-dose",
            estimated_time_per_conversion=360,  # seconds (6 minutes - decanting is slow)
            max_hourly_conversions=10,  # Realistic rate
            capital_requirement=int(best_opportunity['total_buy_cost'] * 5),  # Capital for 5 conversions
            
            # Additional context (FIXED: Remove dose_ratio, add correct data)
            market_context={
                'from_price': best_opportunity['total_buy_cost'],  # Total cost
                'to_price': best_opportunity['sell_price'],       # Revenue
                'profit_per_conversion': best_opportunity['profit'],
                'doses_needed': best_opportunity['doses_needed'],
                'ai_analysis_failed': True
            },
            uncertainty_factors=["AI analysis failed", "Price data age unknown"],
            similar_opportunities=[]
        )
        
        return [fallback_opportunity]


# Global service instance (performance mode enabled by default to prevent system overload)
ai_decanting_service = AIEnhancedDecantingService(performance_mode=True)