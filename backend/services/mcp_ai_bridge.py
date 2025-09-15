"""
MCP-AI Bridge Service for real-time market intelligence integration.

This service coordinates between the MCP (Market Control Protocol) service and
the AI merchant agent, ensuring the AI has access to real-time market data
and can trigger appropriate market analysis.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass

from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.prices.merchant_models import MarketTrend, MerchantOpportunity
from services.mcp_price_service import mcp_service
from services.embedding_service import OllamaEmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class MarketEvent:
    """Represents a market event that affects AI decision making."""
    event_type: str
    item_id: int
    timestamp: datetime
    severity: float
    description: str
    context: Dict[str, Any]


class MCPAIBridge:
    """
    Bridge service that connects MCP real-time market data with AI agent intelligence.
    """
    
    def __init__(self):
        self.embedding_service = OllamaEmbeddingService()
        
        # Event tracking
        self.market_events: List[MarketEvent] = []
        self.watched_items: Set[int] = set()
        self.ai_active_queries: Dict[str, Dict] = {}
        
        # Embedding update tracking
        self.embedding_update_queue: Set[int] = set()
        self.last_embedding_update = datetime.now()
        
        # Cache settings
        self.cache_prefix = "mcp_ai_bridge:"
        self.cache_timeout = 300  # 5 minutes
        
        # Market intelligence thresholds
        self.price_change_threshold = 0.05  # 5% price change
        self.volume_spike_threshold = 2.0    # 200% volume increase
        self.embedding_update_threshold = 0.10  # 10% price change triggers re-embedding
    
    async def get_ai_enhanced_market_context(self, 
                                           item_ids: List[int],
                                           query_type: str = "general",
                                           user_context: Dict = None) -> Dict[str, Any]:
        """
        Get comprehensive market context enhanced for AI analysis.
        
        Args:
            item_ids: Items to analyze
            query_type: Type of AI query (investment, price_inquiry, etc.)
            user_context: Additional context from user query
            
        Returns:
            Enhanced market context with AI-relevant intelligence
        """
        try:
            # Track AI query pattern
            await mcp_service.track_ai_query_patterns(query_type, item_ids, user_context)
            
            # Get base MCP context
            mcp_context = await mcp_service.get_ai_market_context(item_ids)
            
            # Enhance with additional AI-specific data
            enhanced_context = {
                **mcp_context,
                'ai_enhancements': await self._get_ai_enhancements(item_ids, query_type),
                'market_events': await self._get_relevant_market_events(item_ids),
                'embedding_freshness': await self._check_embedding_freshness(item_ids),
                'investment_intelligence': await self._get_investment_intelligence(item_ids, user_context),
                'query_metadata': {
                    'query_type': query_type,
                    'timestamp': datetime.now().isoformat(),
                    'context': user_context or {}
                }
            }
            
            # Add item names for better AI context
            enhanced_context['item_metadata'] = await self._get_item_metadata(item_ids)
            
            return enhanced_context
            
        except Exception as e:
            logger.error(f"Error getting AI enhanced market context: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    async def handle_investment_query(self, 
                                    capital_amount: int,
                                    risk_tolerance: str = "moderate", 
                                    investment_goals: List[str] = None,
                                    timeframe: str = "short_term") -> Dict[str, Any]:
        """
        Handle investment-specific queries with comprehensive analysis.
        
        Args:
            capital_amount: Available capital in GP
            risk_tolerance: conservative, moderate, aggressive
            investment_goals: List of investment objectives
            timeframe: Investment timeframe
            
        Returns:
            Comprehensive investment analysis
        """
        try:
            # Get investment opportunities from MCP
            opportunities = await mcp_service.get_investment_opportunities(
                capital_amount, risk_tolerance, timeframe
            )
            
            # Enhance opportunities with AI context
            enhanced_opportunities = []
            for opp in opportunities:
                enhanced_opp = {
                    **opp,
                    'market_context': await self._get_opportunity_context(opp['item_id']),
                    'risk_analysis': await self._analyze_investment_risk(opp),
                    'timing_analysis': await self._analyze_market_timing(opp['item_id']),
                }
                enhanced_opportunities.append(enhanced_opp)
            
            # Create portfolio suggestions
            portfolio_allocation = await self._suggest_portfolio_allocation(
                enhanced_opportunities, capital_amount, risk_tolerance
            )
            
            return {
                'investment_analysis': {
                    'capital_amount': capital_amount,
                    'risk_tolerance': risk_tolerance,
                    'timeframe': timeframe,
                    'opportunities_found': len(enhanced_opportunities),
                },
                'opportunities': enhanced_opportunities[:10],  # Top 10
                'portfolio_suggestion': portfolio_allocation,
                'market_outlook': await self._get_market_outlook(),
                'risk_warnings': await self._generate_risk_warnings(enhanced_opportunities),
                'timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error handling investment query: {e}")
            return {"error": str(e)}
    
    async def trigger_embedding_updates(self, item_ids: List[int] = None, force: bool = False):
        """
        Trigger embedding updates for items with significant price changes.
        
        Args:
            item_ids: Specific items to update (None for automatic detection)
            force: Force update even if not needed
        """
        try:
            if item_ids is None:
                # Auto-detect items needing embedding updates
                item_ids = await self._detect_embedding_update_candidates()
            
            if not item_ids and not force:
                return
            
            logger.info(f"Triggering embedding updates for {len(item_ids)} items")
            
            # Get items with current market data
            items_data = []
            for item_id in item_ids:
                try:
                    item = await Item.objects.aget(item_id=item_id)
                    market_context = await self._get_market_context_for_embedding(item_id)
                    items_data.append((item, market_context))
                except Item.DoesNotExist:
                    continue
            
            # Update embeddings with market context
            await self._update_embeddings_with_market_context(items_data)
            
            # Track update
            self.last_embedding_update = datetime.now()
            cache.set(f"{self.cache_prefix}last_embedding_update", 
                     self.last_embedding_update.isoformat(), timeout=86400)
            
        except Exception as e:
            logger.error(f"Error triggering embedding updates: {e}")
    
    async def stream_market_events_to_ai(self, event_types: List[str] = None) -> List[MarketEvent]:
        """
        Stream recent market events relevant to AI decision making.
        
        Args:
            event_types: Filter by specific event types
            
        Returns:
            List of recent market events
        """
        try:
            # Get events from cache or generate
            cache_key = f"{self.cache_prefix}market_events"
            cached_events = cache.get(cache_key)
            
            if cached_events is None:
                cached_events = await self._generate_market_events()
                cache.set(cache_key, cached_events, timeout=60)  # 1 minute cache
            
            # Filter by event types if specified
            if event_types:
                filtered_events = [e for e in cached_events if e.event_type in event_types]
                return filtered_events
            
            return cached_events
            
        except Exception as e:
            logger.error(f"Error streaming market events: {e}")
            return []
    
    async def _get_ai_enhancements(self, item_ids: List[int], query_type: str) -> Dict[str, Any]:
        """Get AI-specific enhancements for market context."""
        enhancements = {
            'semantic_context': {},
            'market_patterns': {},
            'user_behavior_insights': {},
            'prediction_confidence': {}
        }
        
        # Add semantic context from embeddings
        for item_id in item_ids:
            try:
                # Get similar items for context
                similar_items = await self._find_similar_items(item_id, limit=5)
                enhancements['semantic_context'][item_id] = similar_items
            except Exception as e:
                logger.debug(f"Could not get semantic context for item {item_id}: {e}")
        
        return enhancements
    
    async def _get_relevant_market_events(self, item_ids: List[int]) -> List[Dict[str, Any]]:
        """Get market events relevant to specific items."""
        events = []
        
        # Check for recent price movements
        for item_id in item_ids:
            try:
                recent_snapshots = [
                    snapshot async for snapshot in PriceSnapshot.objects.filter(
                        item_id=item_id
                    ).order_by('-created_at')[:5]
                ]
                
                if len(recent_snapshots) >= 2:
                    latest = recent_snapshots[0]
                    previous = recent_snapshots[1]
                    
                    if latest.high_price and previous.high_price:
                        price_change = (latest.high_price - previous.high_price) / previous.high_price
                        
                        if abs(price_change) > self.price_change_threshold:
                            events.append({
                                'type': 'significant_price_change',
                                'item_id': item_id,
                                'price_change_pct': price_change * 100,
                                'description': f"Price {'increased' if price_change > 0 else 'decreased'} by {abs(price_change):.1%}",
                                'timestamp': latest.created_at.isoformat(),
                            })
            
            except Exception as e:
                logger.debug(f"Error checking price movements for item {item_id}: {e}")
        
        return events
    
    async def _check_embedding_freshness(self, item_ids: List[int]) -> Dict[str, Any]:
        """Check how fresh the embeddings are for given items."""
        from apps.embeddings.models import ItemEmbedding
        
        freshness_data = {
            'total_items': len(item_ids),
            'embedded_items': 0,
            'stale_embeddings': 0,
            'missing_embeddings': 0,
            'freshness_scores': {}
        }
        
        for item_id in item_ids:
            try:
                embedding = await ItemEmbedding.objects.select_related('item').aget(item_id=item_id)
                freshness_data['embedded_items'] += 1
                
                # Check if embedding is stale (>24 hours old)
                age_hours = (timezone.now() - embedding.updated_at).total_seconds() / 3600
                
                if age_hours > 24:
                    freshness_data['stale_embeddings'] += 1
                
                freshness_data['freshness_scores'][item_id] = {
                    'age_hours': age_hours,
                    'is_stale': age_hours > 24,
                    'last_updated': embedding.updated_at.isoformat(),
                }
                
            except ItemEmbedding.DoesNotExist:
                freshness_data['missing_embeddings'] += 1
                freshness_data['freshness_scores'][item_id] = {
                    'age_hours': float('inf'),
                    'is_stale': True,
                    'last_updated': None,
                }
        
        return freshness_data
    
    async def _get_investment_intelligence(self, item_ids: List[int], user_context: Dict) -> Dict[str, Any]:
        """Get investment-specific intelligence for items."""
        intelligence = {
            'portfolio_fit': {},
            'diversification_value': {},
            'risk_metrics': {},
            'return_projections': {}
        }
        
        # Analyze each item for investment characteristics
        for item_id in item_ids:
            try:
                # Get recent trends
                trends = [
                    trend async for trend in MarketTrend.objects.filter(
                        item_id=item_id,
                        calculated_at__gte=timezone.now() - timedelta(days=7)
                    ).order_by('-calculated_at')[:3]
                ]
                
                if trends:
                    latest_trend = trends[0]
                    intelligence['risk_metrics'][item_id] = {
                        'volatility': latest_trend.volatility_score,
                        'trend_direction': latest_trend.trend_direction,
                        'pattern_confidence': latest_trend.pattern_confidence,
                    }
            
            except Exception as e:
                logger.debug(f"Error getting investment intelligence for item {item_id}: {e}")
        
        return intelligence
    
    async def _get_item_metadata(self, item_ids: List[int]) -> Dict[int, Dict]:
        """Get item metadata for better AI context."""
        metadata = {}
        
        items = [
            item async for item in Item.objects.filter(item_id__in=item_ids)
        ]
        
        for item in items:
            metadata[item.item_id] = {
                'name': item.name,
                'examine_text': item.examine,
                'high_alch_value': item.high_alch,
                'members_only': item.members,
            }
        
        return metadata
    
    async def _detect_embedding_update_candidates(self) -> List[int]:
        """Detect items that need embedding updates due to significant changes."""
        candidates = []
        
        # Check items with recent significant price changes
        recent_snapshots = [
            snapshot async for snapshot in PriceSnapshot.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).select_related('item')
        ]
        
        for snapshot in recent_snapshots:
            # Check if price changed significantly
            prev_snapshots = [
                prev async for prev in PriceSnapshot.objects.filter(
                    item=snapshot.item,
                    created_at__lt=snapshot.created_at
                ).order_by('-created_at')[:1]
            ]
            
            if prev_snapshots and snapshot.high_price and prev_snapshots[0].high_price:
                price_change = abs(snapshot.high_price - prev_snapshots[0].high_price) / prev_snapshots[0].high_price
                
                if price_change > self.embedding_update_threshold:
                    candidates.append(snapshot.item.item_id)
        
        return list(set(candidates))  # Remove duplicates
    
    async def _get_market_context_for_embedding(self, item_id: int) -> str:
        """Get market context to include in embedding text."""
        try:
            # Get current market data
            profit_calc = await ProfitCalculation.objects.select_related('item').aget(item_id=item_id)
            
            context_parts = [
                f"Current buy price: {profit_calc.current_buy_price}GP",
                f"Current profit: {profit_calc.current_profit}GP", 
                f"Daily volume: {profit_calc.daily_volume}",
                f"Data source: {profit_calc.data_source}",
                f"Quality: {profit_calc.data_quality}",
            ]
            
            # Add trend information
            latest_trend = await MarketTrend.objects.filter(
                item_id=item_id
            ).order_by('-calculated_at').afirst()
            
            if latest_trend:
                context_parts.extend([
                    f"Trend: {latest_trend.trend_direction}",
                    f"Volatility: {latest_trend.volatility_score:.3f}",
                    f"Pattern: {latest_trend.pattern_type}",
                ])
            
            return " | ".join(context_parts)
            
        except Exception as e:
            logger.debug(f"Could not get market context for item {item_id}: {e}")
            return ""
    
    async def _update_embeddings_with_market_context(self, items_data: List[tuple]):
        """Update embeddings including current market context."""
        from apps.embeddings.models import ItemEmbedding
        
        for item, market_context in items_data:
            try:
                # Create enhanced source text
                base_text = ItemEmbedding.create_source_text(item)
                enhanced_text = f"{base_text} | Market: {market_context}" if market_context else base_text
                
                # Generate new embedding
                embedding_vector = await self.embedding_service.generate_embedding(enhanced_text)
                
                if embedding_vector:
                    # Update or create embedding
                    embedding, created = await ItemEmbedding.objects.aupdate_or_create(
                        item=item,
                        defaults={
                            'vector': embedding_vector,
                            'source_text': enhanced_text,
                        }
                    )
                    
                    action = "Created" if created else "Updated"
                    logger.info(f"{action} embedding for {item.name} with market context")
                
            except Exception as e:
                logger.error(f"Error updating embedding for {item.name}: {e}")
    
    async def _find_similar_items(self, item_id: int, limit: int = 5) -> List[Dict]:
        """Find semantically similar items using embeddings."""
        try:
            from apps.embeddings.models import ItemEmbedding
            
            # Get the item's embedding
            embedding = await ItemEmbedding.objects.select_related('item').aget(item_id=item_id)
            
            # Find similar items (simplified - would use FAISS in production)
            similar_items = []
            
            async for other_embedding in ItemEmbedding.objects.select_related('item').exclude(item_id=item_id)[:50]:
                similarity = embedding.calculate_similarity(other_embedding.vector)
                if similarity > 0.7:  # High similarity threshold
                    similar_items.append({
                        'item_id': other_embedding.item.item_id,
                        'name': other_embedding.item.name,
                        'similarity': similarity,
                    })
            
            # Sort by similarity and return top results
            similar_items.sort(key=lambda x: x['similarity'], reverse=True)
            return similar_items[:limit]
            
        except Exception as e:
            logger.debug(f"Error finding similar items for {item_id}: {e}")
            return []
    
    async def _generate_market_events(self) -> List[MarketEvent]:
        """Generate current market events for AI consumption."""
        events = []
        
        # Check for volume spikes
        recent_snapshots = [
            snapshot async for snapshot in PriceSnapshot.objects.filter(
                created_at__gte=timezone.now() - timedelta(minutes=30),
                total_volume__gt=1000  # Only high-volume items
            ).order_by('-total_volume')[:20]
        ]
        
        for snapshot in recent_snapshots:
            # Simple volume spike detection (would be more sophisticated in production)
            if snapshot.total_volume and snapshot.total_volume > 2000:  # Arbitrary threshold
                events.append(MarketEvent(
                    event_type="volume_spike",
                    item_id=snapshot.item.item_id,
                    timestamp=snapshot.created_at,
                    severity=min(snapshot.total_volume / 1000, 10),  # Normalize severity
                    description=f"High trading volume: {snapshot.total_volume} units",
                    context={"volume": snapshot.total_volume, "price": snapshot.high_price}
                ))
        
        return events
    
    async def _get_opportunity_context(self, item_id: int) -> Dict[str, Any]:
        """Get additional context for an investment opportunity."""
        return {
            'market_events': await self._get_relevant_market_events([item_id]),
            'embedding_freshness': await self._check_embedding_freshness([item_id]),
            'similar_opportunities': await self._find_similar_items(item_id, 3),
        }
    
    async def _analyze_investment_risk(self, opportunity: Dict) -> Dict[str, Any]:
        """Analyze investment risk for an opportunity."""
        return {
            'volatility_risk': "high" if opportunity['volatility_score'] > 0.05 else "moderate" if opportunity['volatility_score'] > 0.02 else "low",
            'liquidity_risk': "low" if opportunity['volume_score'] > 0.5 else "moderate" if opportunity['volume_score'] > 0.2 else "high",
            'confidence_level': opportunity.get('investment_grade', 50) / 100,
            'risk_warnings': self._generate_opportunity_warnings(opportunity),
        }
    
    async def _analyze_market_timing(self, item_id: int) -> Dict[str, Any]:
        """Analyze market timing for an investment."""
        try:
            # Get recent trends
            trend = await MarketTrend.objects.filter(
                item_id=item_id
            ).order_by('-calculated_at').afirst()
            
            if trend:
                return {
                    'timing_score': self._calculate_timing_score(trend),
                    'trend_direction': trend.trend_direction,
                    'pattern_strength': trend.pattern_confidence,
                    'recommendation': self._get_timing_recommendation(trend),
                }
            
        except Exception as e:
            logger.debug(f"Error analyzing market timing for item {item_id}: {e}")
        
        return {
            'timing_score': 0.5,
            'trend_direction': 'unknown',
            'pattern_strength': 0.0,
            'recommendation': 'neutral',
        }
    
    def _calculate_timing_score(self, trend: MarketTrend) -> float:
        """Calculate a timing score for market entry."""
        score = 0.5  # Base neutral score
        
        # Adjust based on trend direction
        if trend.trend_direction in ['strong_up', 'weak_up']:
            score += 0.2
        elif trend.trend_direction in ['strong_down', 'weak_down']:
            score -= 0.2
        
        # Adjust based on pattern confidence
        score += (trend.pattern_confidence - 0.5) * 0.3
        
        # Adjust based on volatility (lower volatility = better timing)
        score += (0.05 - trend.volatility_score) * 2
        
        return max(0.0, min(1.0, score))
    
    def _get_timing_recommendation(self, trend: MarketTrend) -> str:
        """Get timing recommendation based on trend analysis."""
        timing_score = self._calculate_timing_score(trend)
        
        if timing_score > 0.7:
            return "excellent_timing"
        elif timing_score > 0.6:
            return "good_timing"
        elif timing_score > 0.4:
            return "neutral_timing"
        elif timing_score > 0.3:
            return "poor_timing"
        else:
            return "avoid"
    
    def _generate_opportunity_warnings(self, opportunity: Dict) -> List[str]:
        """Generate risk warnings for an opportunity."""
        warnings = []
        
        if opportunity['volatility_score'] > 0.1:
            warnings.append("High price volatility increases risk")
        
        if opportunity['volume_score'] < 0.2:
            warnings.append("Low trading volume may impact liquidity")
        
        if opportunity['expected_return_pct'] > 20:
            warnings.append("Very high projected returns indicate elevated risk")
        
        return warnings
    
    async def _suggest_portfolio_allocation(self, opportunities: List[Dict], total_capital: int, risk_tolerance: str) -> Dict[str, Any]:
        """Suggest portfolio allocation across opportunities."""
        if not opportunities:
            return {"message": "No suitable opportunities found"}
        
        # Risk-based allocation percentages
        risk_allocations = {
            "conservative": {"max_single_position": 0.15, "max_aggressive_allocation": 0.3},
            "moderate": {"max_single_position": 0.25, "max_aggressive_allocation": 0.5},
            "aggressive": {"max_single_position": 0.4, "max_aggressive_allocation": 0.8},
        }
        
        allocation_rules = risk_allocations.get(risk_tolerance, risk_allocations["moderate"])
        
        # Sort opportunities by investment grade
        sorted_opps = sorted(opportunities, key=lambda x: x.get('investment_grade', 0), reverse=True)
        
        allocations = []
        remaining_capital = total_capital
        
        for opp in sorted_opps[:5]:  # Top 5 opportunities
            # Calculate allocation percentage
            max_allocation = min(
                allocation_rules["max_single_position"],
                opp['total_investment'] / total_capital
            )
            
            allocation_amount = min(remaining_capital * max_allocation, opp['total_investment'])
            
            if allocation_amount > 1000:  # Minimum 1000 GP investment
                allocations.append({
                    'item_id': opp['item_id'],
                    'allocation_amount': int(allocation_amount),
                    'allocation_percentage': allocation_amount / total_capital * 100,
                    'reasoning': f"High investment grade ({opp.get('investment_grade', 0):.1f})",
                })
                
                remaining_capital -= allocation_amount
            
            if remaining_capital < total_capital * 0.1:  # Keep 10% reserve
                break
        
        return {
            'allocations': allocations,
            'total_allocated': total_capital - remaining_capital,
            'remaining_capital': remaining_capital,
            'diversification_score': len(allocations) / 5.0,  # Score based on diversification
        }
    
    async def _get_market_outlook(self) -> Dict[str, Any]:
        """Get general market outlook."""
        # Simplified market outlook - would be more sophisticated in production
        return {
            'overall_sentiment': 'neutral',
            'market_volatility': 'moderate',
            'recommended_strategy': 'balanced_approach',
            'key_factors': ['price_stability', 'volume_trends', 'seasonal_patterns'],
        }
    
    async def _generate_risk_warnings(self, opportunities: List[Dict]) -> List[str]:
        """Generate general risk warnings for the opportunity set."""
        warnings = []
        
        high_risk_count = sum(1 for opp in opportunities if opp.get('volatility_score', 0) > 0.05)
        if high_risk_count > len(opportunities) * 0.5:
            warnings.append("Over half of opportunities involve high volatility items")
        
        low_volume_count = sum(1 for opp in opportunities if opp.get('volume_score', 0) < 0.2)
        if low_volume_count > 0:
            warnings.append(f"{low_volume_count} opportunities have low trading volume")
        
        return warnings


# Global bridge instance
mcp_ai_bridge = MCPAIBridge()