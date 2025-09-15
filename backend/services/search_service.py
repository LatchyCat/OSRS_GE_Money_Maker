"""
Hybrid search service combining semantic search, profit calculations, and AI insights.
"""

import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

# Import our models and services
from apps.items.models import Item
from apps.prices.models import ProfitCalculation
from apps.embeddings.models import ItemEmbedding, SearchQuery
from services.embedding_service import SyncOllamaEmbeddingService
from services.faiss_manager import FaissVectorDatabase
from services.ai_service import SyncOpenRouterAIService

logger = logging.getLogger(__name__)


class SearchServiceError(Exception):
    """Custom exception for search service errors."""
    pass


class HybridSearchService:
    """
    Service for hybrid search combining semantic search with profit-based ranking.
    """
    
    def __init__(self):
        self.embedding_service = SyncOllamaEmbeddingService()
        self.faiss_db = FaissVectorDatabase(index_name="osrs_items")
        self.ai_service = SyncOpenRouterAIService()
    
    def _is_alchemy_query(self, query: str) -> bool:
        """Detect if query is related to high alchemy."""
        query_lower = query.lower()
        alchemy_keywords = [
            'alch', 'alchemy', 'high alchemy', 'high level alchemy',
            'magic training', 'magic xp', 'nature rune', 'alching',
            'alch profit', 'alch value', 'good for alching',
            'best alch', 'alch items', 'alch opportunities'
        ]
        return any(keyword in query_lower for keyword in alchemy_keywords)
    
    def _is_decanting_query(self, query: str) -> bool:
        """Detect if query is related to decanting potions."""
        query_lower = query.lower()
        decanting_keywords = [
            'decant', 'decanting', 'potion', 'dose', 'doses',
            'barbarian herblore', '4 dose', '3 dose', '2 dose', '1 dose',
            'super combat', 'prayer potion', 'ranging potion',
            'super strength', 'super attack', 'super defence',
            'combat potion', 'potion profit', 'dose conversion'
        ]
        return any(keyword in query_lower for keyword in decanting_keywords)
    
    def _is_set_combining_query(self, query: str) -> bool:
        """Detect if query is related to set combining (lazy tax)."""
        query_lower = query.lower()
        set_keywords = [
            'set', 'armor set', 'weapon set', 'lazy tax', 'set combining',
            'barrows', 'dharok', 'ahrim', 'karil', 'torag', 'verac', 'guthan',
            'god wars', 'armadyl', 'bandos', 'saradomin', 'zamorak',
            'godsword', 'void', 'dragon set', 'pieces', 'complete set',
            'armor pieces', 'set pieces', 'combine pieces'
        ]
        return any(keyword in query_lower for keyword in set_keywords)
    
    def _is_bond_flipping_query(self, query: str) -> bool:
        """Detect if query is related to bond flipping or high-value items."""
        query_lower = query.lower()
        bond_keywords = [
            'bond', 'bonds', 'old school bond', 'bond flipping',
            'high value', 'expensive', 'premium items', 'rare items',
            'twisted bow', 'scythe', 'kodai', 'ancestral', 'justiciar',
            'big ticket', 'whale items', 'high ticket', 'bond funded'
        ]
        return any(keyword in query_lower for keyword in bond_keywords)
    
    def _is_money_maker_query(self, query: str) -> bool:
        """Detect if query is about general money making."""
        query_lower = query.lower()
        money_keywords = [
            'money making', 'money maker', 'profit', 'profitable',
            'gp per hour', 'gp/hr', 'best money', 'capital', 'investment',
            'trading', 'flipping', 'margins', 'ge tax', 'lazy tax',
            '50m to 100m', 'scaling capital', 'progression'
        ]
        return any(keyword in query_lower for keyword in money_keywords)
    
    def _get_alchemy_weighted_queryset(self, base_queryset):
        """Get items sorted by high alchemy viability."""
        return base_queryset.filter(
            profit_calc__high_alch_viability_score__gt=0
        ).order_by(
            '-profit_calc__high_alch_viability_score',
            '-profit_calc__alch_efficiency_rating',
            '-profit_calc__current_profit'
        )
    
    def _get_decanting_weighted_queryset(self, base_queryset):
        """Get potions sorted by decanting potential."""
        return base_queryset.filter(
            Q(name__icontains='potion') | Q(name__icontains='dose'),
            profit_calc__isnull=False
        ).order_by(
            '-profit_calc__current_profit_margin',
            '-profit_calc__daily_volume',
            'name'
        )
    
    def _get_set_combining_weighted_queryset(self, base_queryset):
        """Get items sorted by set combining potential."""
        # Focus on armor pieces and complete sets
        armor_keywords = Q(name__icontains='helm') | Q(name__icontains='body') | Q(name__icontains='legs') | \
                        Q(name__icontains='chestplate') | Q(name__icontains='tassets') | Q(name__icontains='skirt') | \
                        Q(name__icontains='set') | Q(name__icontains='dharok') | Q(name__icontains='ahrim') | \
                        Q(name__icontains='karil') | Q(name__icontains='torag') | Q(name__icontains='verac') | \
                        Q(name__icontains='guthan') | Q(name__icontains='armadyl') | Q(name__icontains='bandos') | \
                        Q(name__icontains='godsword') | Q(name__icontains='void')
        
        return base_queryset.filter(
            armor_keywords,
            profit_calc__isnull=False
        ).order_by(
            '-profit_calc__current_buy_price',  # Higher value items first
            '-profit_calc__volume_weighted_score',
            'name'
        )
    
    def _get_bond_flipping_weighted_queryset(self, base_queryset):
        """Get high-value items suitable for bond flipping."""
        return base_queryset.filter(
            profit_calc__current_buy_price__gte=1_000_000,  # 1M+ items
            profit_calc__isnull=False
        ).order_by(
            '-profit_calc__current_buy_price',
            '-profit_calc__current_profit_margin',
            '-profit_calc__volume_weighted_score'
        )
    
    def _get_money_maker_weighted_queryset(self, base_queryset):
        """Get items sorted by general money making potential."""
        return base_queryset.filter(
            profit_calc__is_profitable=True,
            profit_calc__current_profit__gt=100
        ).order_by(
            '-profit_calc__volume_weighted_score',
            '-profit_calc__current_profit_margin',
            '-profit_calc__current_profit'
        )

    def search_items(
        self,
        query: str,
        limit: int = 20,
        min_profit: int = 0,
        max_price: int = None,
        members_only: bool = None,
        semantic_weight: float = 0.6,
        profit_weight: float = 0.4,
        use_ai_enhancement: bool = True
    ) -> Dict[str, Any]:
        """
        Perform hybrid search combining semantic similarity and profit ranking.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            min_profit: Minimum profit per item
            max_price: Maximum GE buy price
            members_only: Filter by members items only
            semantic_weight: Weight for semantic similarity (0-1)
            profit_weight: Weight for profit ranking (0-1)
            use_ai_enhancement: Whether to use AI to enhance results
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            logger.info(f"Hybrid search for: '{query}' (limit: {limit})")
            
            # Check cache first
            cache_key = self._generate_cache_key(query, limit, min_profit, max_price, members_only)
            cached_results = cache.get(cache_key)
            if cached_results:
                logger.debug(f"Cache hit for query: {query}")
                return cached_results
            
            # Step 1: Get base queryset with profit filters
            base_queryset = self._get_base_queryset(min_profit, max_price, members_only)
            
            if not query.strip():
                # No search query, just return top profitable items
                results = self._get_top_profitable_items(base_queryset, limit)
            else:
                # Balanced approach: Perform semantic search and include both alchemy and flipping opportunities
                semantic_results = self._semantic_search(query, limit * 3)  # Get more for ranking
                
                # Use balanced ranking that considers both alchemy and regular trading
                results = self._hybrid_rank_results_balanced(
                    semantic_results, 
                    base_queryset,
                    query,  # Pass query for context
                    semantic_weight,
                    profit_weight,
                    limit
                )
                
                # Log search query
                self._log_search_query(query, len(results))
            
            # Step 5: Enhance with AI insights if requested
            ai_insights = None
            if use_ai_enhancement and results and query.strip():
                try:
                    ai_insights = self.ai_service.semantic_search_enhancement(query, results)
                except Exception as e:
                    logger.warning(f"AI enhancement failed: {e}")
            
            # Prepare final response
            response = {
                'query': query,
                'results': results,
                'total_found': len(results),
                'search_time_ms': 0,  # Would measure in real implementation
                'filters_applied': {
                    'min_profit': min_profit,
                    'max_price': max_price,
                    'members_only': members_only
                },
                'ai_insights': ai_insights,
                'timestamp': timezone.now().isoformat()
            }
            
            # Cache results for 5 minutes
            cache.set(cache_key, response, timeout=300)
            
            return response
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise SearchServiceError(f"Search failed: {e}")
    
    def get_similar_items(
        self,
        item_id: int,
        limit: int = 10,
        similarity_threshold: float = 0.3
    ) -> List[Dict]:
        """
        Get items similar to a given item using semantic similarity.
        
        Args:
            item_id: ID of the reference item
            limit: Maximum number of similar items
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of similar items with similarity scores
        """
        try:
            # Get the reference item
            try:
                item = Item.objects.get(item_id=item_id)
            except Item.DoesNotExist:
                logger.warning(f"Item {item_id} not found")
                return []
            
            # Get item embedding
            try:
                item_embedding = ItemEmbedding.objects.get(item=item)
                query_vector = item_embedding.vector
            except ItemEmbedding.DoesNotExist:
                logger.warning(f"No embedding found for item {item_id}")
                return []
            
            # Search for similar items using FAISS
            similar_results = self.faiss_db.search(
                query_vector=query_vector,
                k=limit + 1,  # +1 to exclude the item itself
                threshold=similarity_threshold
            )
            
            # Remove the item itself from results
            similar_results = [(id_, score) for id_, score in similar_results if id_ != item_id]
            
            # Get item details and profit data
            results = []
            for similar_item_id, similarity in similar_results[:limit]:
                try:
                    similar_item = Item.objects.get(item_id=similar_item_id)
                    profit_calc = getattr(similar_item, 'profit_calc', None)
                    
                    result = {
                        'item_id': similar_item.item_id,
                        'name': similar_item.name,
                        'examine': similar_item.examine,
                        'high_alch': similar_item.high_alch,
                        'similarity_score': similarity,
                        'current_profit': profit_calc.current_profit if profit_calc else 0,
                        'current_profit_margin': profit_calc.current_profit_margin if profit_calc else 0.0,
                        'current_buy_price': profit_calc.current_buy_price if profit_calc else None,
                    }
                    results.append(result)
                    
                except Item.DoesNotExist:
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Similar items search failed: {e}")
            return []
    
    def get_profit_recommendations(
        self,
        limit: int = 20,
        min_profit_margin: float = 5.0,
        max_risk_level: str = "medium"
    ) -> Dict[str, Any]:
        """
        Get AI-powered profit recommendations.
        
        Args:
            limit: Maximum number of recommendations
            min_profit_margin: Minimum profit margin percentage
            max_risk_level: Maximum risk level (low, medium, high)
            
        Returns:
            Dictionary with recommendations and market analysis
        """
        try:
            # Get top profitable items
            queryset = ProfitCalculation.objects.filter(
                current_profit__gt=0,
                current_profit_margin__gte=min_profit_margin,
                item__is_active=True
            ).select_related('item').order_by('-current_profit')
            
            # Apply risk filter
            risk_levels = {'low': 1, 'medium': 2, 'high': 3}
            max_risk_num = risk_levels.get(max_risk_level, 2)
            
            items_data = []
            for profit_calc in queryset[:limit]:
                item = profit_calc.item
                
                # Simple risk assessment
                risk_score = self._assess_item_risk(profit_calc)
                if risk_score > max_risk_num:
                    continue
                
                item_data = {
                    'item_id': item.item_id,
                    'name': item.name,
                    'examine': item.examine,
                    'high_alch': item.high_alch,
                    'current_profit': profit_calc.current_profit,
                    'current_profit_margin': profit_calc.current_profit_margin,
                    'current_buy_price': profit_calc.current_buy_price,
                    'daily_volume': profit_calc.daily_volume,
                    'recommendation_score': profit_calc.recommendation_score,
                    'risk_level': ['low', 'medium', 'high'][risk_score - 1] if risk_score > 0 else 'low'
                }
                items_data.append(item_data)
                
                if len(items_data) >= limit:
                    break
            
            # Generate AI market summary
            market_summary = None
            try:
                market_summary = self.ai_service.generate_market_summary(items_data)
            except Exception as e:
                logger.warning(f"Market summary generation failed: {e}")
            
            return {
                'recommendations': items_data,
                'total_found': len(items_data),
                'market_summary': market_summary,
                'filters': {
                    'min_profit_margin': min_profit_margin,
                    'max_risk_level': max_risk_level
                },
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Profit recommendations failed: {e}")
            raise SearchServiceError(f"Recommendations failed: {e}")
    
    def _get_base_queryset(self, min_profit: int, max_price: int, members_only: bool):
        """Get base queryset with profit filters."""
        queryset = Item.objects.filter(is_active=True)
        
        if members_only is not None:
            queryset = queryset.filter(members=members_only)
        
        # Join with profit calculations if we have profit/price filters
        if min_profit is not None or max_price is not None:
            queryset = queryset.filter(profit_calc__isnull=False)
            
            if min_profit is not None:
                queryset = queryset.filter(profit_calc__current_profit__gte=min_profit)
            
            if max_price is not None:
                queryset = queryset.filter(profit_calc__current_buy_price__lte=max_price)
        
        return queryset.select_related('profit_calc')
    
    def _semantic_search(self, query: str, limit: int) -> List[Tuple[int, float]]:
        """Perform semantic search using embeddings and FAISS."""
        try:
            # Generate embedding for query
            query_embedding = self.embedding_service.generate_embedding(query)
            if not query_embedding:
                logger.warning(f"Failed to generate embedding for query: {query}")
                return []
            
            # Search FAISS index
            results = self.faiss_db.search(
                query_vector=query_embedding,
                k=limit,
                threshold=0.1  # Low threshold to get more candidates
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _hybrid_rank_results(
        self,
        semantic_results: List[Tuple[int, float]],
        base_queryset,
        semantic_weight: float,
        profit_weight: float,
        limit: int
    ) -> List[Dict]:
        """Combine semantic similarity with profit ranking."""
        try:
            # Get semantic item IDs
            semantic_item_ids = [item_id for item_id, _ in semantic_results]
            semantic_scores = {item_id: score for item_id, score in semantic_results}
            
            # Get items that match both semantic search and filters
            items = base_queryset.filter(item_id__in=semantic_item_ids)
            
            # Calculate hybrid scores
            scored_items = []
            for item in items:
                semantic_score = semantic_scores.get(item.item_id, 0.0)
                
                # Calculate profit score (normalized)
                profit_calc = getattr(item, 'profit_calc', None)
                if profit_calc and profit_calc.current_profit > 0:
                    # Simple normalization: profit_margin / 100 (cap at 1.0)
                    profit_score = min(1.0, max(0.0, profit_calc.current_profit_margin / 100.0))
                else:
                    profit_score = 0.0
                
                # Calculate hybrid score
                hybrid_score = (semantic_weight * semantic_score + profit_weight * profit_score)
                
                item_data = {
                    'item_id': item.item_id,
                    'name': item.name,
                    'examine': item.examine,
                    'high_alch': item.high_alch,
                    'members': item.members,
                    'limit': item.limit,
                    'semantic_score': semantic_score,
                    'profit_score': profit_score,
                    'hybrid_score': hybrid_score,
                    'current_profit': profit_calc.current_profit if profit_calc else 0,
                    'current_profit_margin': profit_calc.current_profit_margin if profit_calc else 0.0,
                    'current_buy_price': profit_calc.current_buy_price if profit_calc else None,
                    'daily_volume': profit_calc.daily_volume if profit_calc else 0,
                }
                
                scored_items.append(item_data)
            
            # Sort by hybrid score and return top results
            scored_items.sort(key=lambda x: x['hybrid_score'], reverse=True)
            return scored_items[:limit]
            
        except Exception as e:
            logger.error(f"Hybrid ranking failed: {e}")
            return []
    
    def _hybrid_rank_results_for_alchemy(
        self,
        semantic_results: List[Tuple[int, float]],
        alchemy_queryset,
        limit: int
    ) -> List[Dict]:
        """Combine semantic similarity with high alchemy viability scoring."""
        try:
            # Get semantic item IDs and scores
            semantic_scores = {item_id: score for item_id, score in semantic_results}
            
            # Get top alchemy items from queryset (handle async context)
            try:
                alchemy_items = list(alchemy_queryset[:limit * 2])  # Get more for better ranking
            except Exception as async_error:
                logger.warning(f"Async context issue, falling back to sync query: {async_error}")
                from asgiref.sync import sync_to_async
                alchemy_items = list(alchemy_queryset.select_related('profit_calc')[:limit * 2])
            
            scored_items = []
            for item in alchemy_items:
                semantic_score = semantic_scores.get(item.item_id, 0.0)
                profit_calc = getattr(item, 'profit_calc', None)
                
                if not profit_calc:
                    continue
                
                # High Alchemy focused scoring (normalized to 0-1)
                alch_viability = (profit_calc.high_alch_viability_score or 0) / 100.0
                alch_efficiency = (profit_calc.alch_efficiency_rating or 0) / 100.0  
                sustainability = (profit_calc.sustainable_alch_potential or 0) / 100.0
                
                # Weighted hybrid score heavily favoring alchemy metrics
                hybrid_score = (
                    0.3 * semantic_score +      # 30% semantic relevance
                    0.35 * alch_viability +     # 35% alchemy viability
                    0.20 * alch_efficiency +    # 20% efficiency 
                    0.15 * sustainability       # 15% sustainability
                )
                
                item_data = {
                    'item_id': item.item_id,
                    'name': item.name,
                    'examine': item.examine,
                    'high_alch': item.high_alch,
                    'members': item.members,
                    'limit': item.limit,
                    'semantic_score': semantic_score,
                    'hybrid_score': hybrid_score,
                    'current_profit': profit_calc.current_profit,
                    'current_profit_margin': profit_calc.current_profit_margin,
                    'current_buy_price': profit_calc.current_buy_price,
                    'daily_volume': profit_calc.daily_volume,
                    # Alchemy specific metrics
                    'high_alch_viability_score': profit_calc.high_alch_viability_score,
                    'alch_efficiency_rating': profit_calc.alch_efficiency_rating,
                    'sustainable_alch_potential': profit_calc.sustainable_alch_potential,
                    'magic_xp_efficiency': profit_calc.magic_xp_efficiency,
                    'net_alch_profit': item.high_alch - 180 - (profit_calc.current_buy_price or 0),
                }
                
                scored_items.append(item_data)
            
            # Sort by hybrid score and return top results
            scored_items.sort(key=lambda x: x['hybrid_score'], reverse=True)
            return scored_items[:limit]
            
        except Exception as e:
            logger.error(f"Alchemy ranking failed: {e}")
            return []

    def _hybrid_rank_results_balanced(
        self,
        semantic_results: List[Tuple[int, float]],
        base_queryset,
        query: str,
        semantic_weight: float,
        profit_weight: float,
        limit: int
    ) -> List[Dict]:
        """Balanced ranking considering both alchemy and flipping opportunities."""
        try:
            # Get semantic item IDs
            semantic_item_ids = [item_id for item_id, _ in semantic_results]
            semantic_scores = {item_id: score for item_id, score in semantic_results}
            
            # Get items that match both semantic search and filters
            items = base_queryset.filter(item_id__in=semantic_item_ids)
            
            # Detect query strategy context
            is_alchemy_context = self._is_alchemy_query(query)
            is_decanting_context = self._is_decanting_query(query)
            is_set_combining_context = self._is_set_combining_query(query)
            is_bond_flipping_context = self._is_bond_flipping_query(query)
            is_money_maker_context = self._is_money_maker_query(query)
            
            logger.info(f"Query context: alchemy={is_alchemy_context}, decanting={is_decanting_context}, "
                       f"set_combining={is_set_combining_context}, bond_flipping={is_bond_flipping_context}, "
                       f"money_maker={is_money_maker_context}")
            
            # Calculate hybrid scores
            scored_items = []
            for item in items:
                semantic_score = semantic_scores.get(item.item_id, 0.0)
                profit_calc = getattr(item, 'profit_calc', None)
                
                if not profit_calc:
                    continue
                
                # Base trading metrics (normalized to 0-1)
                profit_margin = min(1.0, max(0.0, profit_calc.current_profit_margin / 100.0)) if profit_calc.current_profit_margin else 0.0
                
                # High alchemy metrics (normalized to 0-1)  
                alch_viability = (profit_calc.high_alch_viability_score or 0) / 100.0
                alch_efficiency = (profit_calc.alch_efficiency_rating or 0) / 100.0
                
                # Money maker specific scoring
                decanting_bonus = 0.0
                set_combining_bonus = 0.0
                bond_flipping_bonus = 0.0
                
                # Decanting scoring
                if is_decanting_context and ('potion' in item.name.lower() or 'dose' in item.name.lower()):
                    decanting_bonus = 0.3
                    
                # Set combining scoring  
                item_name_lower = item.name.lower()
                if is_set_combining_context and any(keyword in item_name_lower for keyword in 
                    ['helm', 'body', 'legs', 'chestplate', 'tassets', 'set', 'dharok', 'ahrim', 
                     'karil', 'torag', 'verac', 'guthan', 'armadyl', 'bandos', 'godsword', 'void']):
                    set_combining_bonus = 0.3
                
                # Bond flipping scoring (high-value items)
                if is_bond_flipping_context and profit_calc.current_buy_price and profit_calc.current_buy_price >= 1_000_000:
                    bond_flipping_bonus = 0.3
                
                # Calculate context-aware hybrid score
                if is_alchemy_context:
                    # Alchemy-focused scoring
                    hybrid_score = (
                        0.20 * semantic_score +
                        0.20 * profit_margin +
                        0.35 * alch_viability +
                        0.25 * alch_efficiency
                    )
                elif is_decanting_context:
                    # Decanting-focused scoring
                    hybrid_score = (
                        0.20 * semantic_score +
                        0.30 * profit_margin +
                        0.15 * alch_viability +
                        0.15 * alch_efficiency +
                        0.20 * decanting_bonus
                    )
                elif is_set_combining_context:
                    # Set combining-focused scoring
                    hybrid_score = (
                        0.20 * semantic_score +
                        0.25 * profit_margin +
                        0.10 * alch_viability +
                        0.15 * alch_efficiency +
                        0.30 * set_combining_bonus
                    )
                elif is_bond_flipping_context:
                    # Bond flipping-focused scoring
                    hybrid_score = (
                        0.20 * semantic_score +
                        0.35 * profit_margin +
                        0.10 * alch_viability +
                        0.05 * alch_efficiency +
                        0.30 * bond_flipping_bonus
                    )
                elif is_money_maker_context:
                    # General money making - balanced approach
                    hybrid_score = (
                        0.15 * semantic_score +
                        0.30 * profit_margin +
                        0.20 * alch_viability +
                        0.15 * alch_efficiency +
                        0.10 * decanting_bonus +
                        0.05 * set_combining_bonus +
                        0.05 * bond_flipping_bonus
                    )
                else:
                    # Default balanced scoring
                    hybrid_score = (
                        0.25 * semantic_score +
                        0.30 * profit_margin +
                        0.25 * alch_viability +
                        0.20 * alch_efficiency
                    )
                
                # Calculate GE tax aware profit
                from services.weird_gloop_client import GrandExchangeTax
                ge_tax = 0
                net_profit_after_tax = profit_calc.current_profit
                
                if profit_calc.current_buy_price and profit_calc.current_sell_price:
                    ge_tax = GrandExchangeTax.calculate_tax(profit_calc.current_sell_price, item.item_id)
                    net_profit_after_tax = profit_calc.current_sell_price - ge_tax - profit_calc.current_buy_price
                
                item_data = {
                    'item_id': item.item_id,
                    'name': item.name,
                    'examine': item.examine,
                    'high_alch': item.high_alch,
                    'members': item.members,
                    'limit': item.limit,
                    'semantic_score': semantic_score,
                    'hybrid_score': hybrid_score,
                    'current_profit': profit_calc.current_profit,
                    'current_profit_margin': profit_calc.current_profit_margin,
                    'current_buy_price': profit_calc.current_buy_price,
                    'recommendation_score': profit_calc.recommendation_score,
                    'profit_calc': {
                        'current_profit': profit_calc.current_profit,
                        'current_profit_margin': profit_calc.current_profit_margin,
                        'current_buy_price': profit_calc.current_buy_price,
                        'current_sell_price': profit_calc.current_sell_price,
                        'recommendation_score': profit_calc.recommendation_score,
                        'high_alch_viability_score': profit_calc.high_alch_viability_score,
                        'alch_efficiency_rating': profit_calc.alch_efficiency_rating,
                        'sustainable_alch_potential': profit_calc.sustainable_alch_potential,
                        'magic_xp_efficiency': profit_calc.magic_xp_efficiency,
                        'volume_category': profit_calc.volume_category,
                        'daily_volume': profit_calc.daily_volume,
                    },
                    'money_maker_context': {
                        'ge_tax': ge_tax,
                        'net_profit_after_tax': net_profit_after_tax,
                        'is_decanting_candidate': decanting_bonus > 0,
                        'is_set_combining_candidate': set_combining_bonus > 0,
                        'is_bond_flipping_candidate': bond_flipping_bonus > 0,
                        'strategy_bonuses': {
                            'decanting': decanting_bonus,
                            'set_combining': set_combining_bonus,
                            'bond_flipping': bond_flipping_bonus
                        }
                    }
                }
                scored_items.append(item_data)
            
            # Sort by hybrid score and return top results
            scored_items.sort(key=lambda x: x['hybrid_score'], reverse=True)
            return scored_items[:limit]
            
        except Exception as e:
            logger.error(f"Balanced ranking failed: {e}")
            return []

    def _get_top_profitable_items(self, base_queryset, limit: int) -> List[Dict]:
        """Get top profitable items without semantic search."""
        try:
            items = base_queryset.filter(
                profit_calc__isnull=False,
                profit_calc__current_profit__gt=0
            ).order_by('-profit_calc__current_profit')[:limit]
            
            results = []
            for item in items:
                profit_calc = item.profit_calc
                
                item_data = {
                    'item_id': item.item_id,
                    'name': item.name,
                    'examine': item.examine,
                    'high_alch': item.high_alch,
                    'members': item.members,
                    'limit': item.limit,
                    'semantic_score': 0.0,
                    'profit_score': 1.0,
                    'hybrid_score': profit_calc.current_profit_margin / 100.0,
                    'current_profit': profit_calc.current_profit,
                    'current_profit_margin': profit_calc.current_profit_margin,
                    'current_buy_price': profit_calc.current_buy_price,
                    'daily_volume': profit_calc.daily_volume,
                }
                results.append(item_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Top profitable items query failed: {e}")
            return []
    
    def _assess_item_risk(self, profit_calc) -> int:
        """Assess risk level for an item (1=low, 2=medium, 3=high)."""
        profit_margin = profit_calc.current_profit_margin
        volume = profit_calc.daily_volume
        
        if profit_margin > 20 and volume < 100:
            return 3  # High risk: high margin but low volume
        elif profit_margin > 15 or volume < 500:
            return 2  # Medium risk
        else:
            return 1  # Low risk: reasonable margin and good volume
    
    def _log_search_query(self, query: str, result_count: int):
        """Log search query for analytics."""
        try:
            query_hash = hashlib.sha256(query.encode()).hexdigest()
            
            # Generate embedding for the query to store in the database
            query_embedding = self.embedding_service.generate_embedding(query)
            if not query_embedding:
                # Use zero vector as fallback to avoid database errors
                query_embedding = [0.0] * 1024  # Match the model's vector size
            
            search_query, created = SearchQuery.objects.get_or_create(
                query_hash=query_hash,
                defaults={
                    'query_text': query,
                    'vector': query_embedding,
                    'result_count': result_count
                }
            )
            
            if not created:
                search_query.search_count += 1
                search_query.result_count = result_count
                search_query.save()
                
        except Exception as e:
            logger.warning(f"Failed to log search query: {e}")
    
    def _generate_cache_key(
        self, 
        query: str, 
        limit: int, 
        min_profit: int, 
        max_price: int, 
        members_only: bool
    ) -> str:
        """Generate cache key for search results."""
        key_data = f"{query}:{limit}:{min_profit}:{max_price}:{members_only}"
        return f"search:{hashlib.md5(key_data.encode()).hexdigest()}"