"""
Hybrid search service combining vector similarity and keyword search for OSRS trading opportunities.

Integrates RuneScape Wiki API data with AI embeddings for intelligent opportunity discovery.
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
import faiss
from django.core.cache import cache
from django.utils import timezone

from .runescape_wiki_client import RuneScapeWikiAPIClient, WikiPriceData, ItemMetadata
from .embedding_service import OllamaEmbeddingService
from apps.items.models import Item

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Combined search result with scoring."""
    item_id: int
    name: str
    price_data: WikiPriceData
    metadata: Optional[ItemMetadata]
    vector_score: float
    keyword_score: float
    combined_score: float
    context: Dict[str, Any]


@dataclass  
class TradingOpportunity:
    """Enhanced trading opportunity with AI insights."""
    item_id: int
    name: str
    category: str
    opportunity_type: str  # decanting, flipping, etc.
    profit_potential: float
    risk_level: str
    confidence_score: float
    market_context: Dict[str, Any]
    ai_insights: List[str]
    related_items: List[int]
    price_data: WikiPriceData
    volume_analysis: Optional[Dict[str, Any]] = None
    trading_activity: str = "unknown"
    liquidity_score: float = 0.0


class HybridSearchService:
    """
    Advanced search service for OSRS trading opportunities.
    
    Combines:
    - Vector similarity search using Ollama embeddings
    - Traditional keyword/filter search
    - RuneScape Wiki real-time price data
    - Market condition analysis
    """
    
    def __init__(self):
        self.wiki_client = RuneScapeWikiAPIClient()
        self.embedding_service = OllamaEmbeddingService()
        
        # Search indexes
        self.faiss_index = None
        self.item_embeddings = {}  # item_id -> embedding
        self.item_metadata_cache = {}  # item_id -> metadata
        
        # Search parameters
        self.vector_weight = 0.6
        self.keyword_weight = 0.4
        self.cache_timeout = 3600  # 1 hour
        
        # Trading categories for filtering
        self.potion_keywords = [
            'potion', 'brew', 'mix', 'elixir', 'dose', 'prayer', 'stamina',
            'antifire', 'combat', 'strength', 'attack', 'defence', 'ranging',
            'magic', 'agility', 'fishing', 'divine', 'super', 'antipoison'
        ]
        
        self.weapon_keywords = [
            'sword', 'bow', 'staff', 'wand', 'spear', 'dagger', 'mace',
            'axe', 'hammer', 'crossbow', 'whip', 'scimitar', 'longsword'
        ]
        
        self.armor_keywords = [
            'helmet', 'helm', 'chest', 'chestplate', 'legs', 'leggings',
            'boots', 'gloves', 'gauntlets', 'shield', 'platebody', 'chainmail'
        ]
    
    async def initialize(self):
        """Initialize the hybrid search service."""
        logger.info("Initializing hybrid search service...")
        
        try:
            # Initialize embedding service
            await self.embedding_service._ensure_model_available()
            
            # Initialize vector search index
            await self._build_item_index()
            
            logger.info("Hybrid search service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize hybrid search service: {e}")
            raise
    
    async def _build_item_index(self):
        """Build comprehensive item search index."""
        logger.info("Building item search index...")
        
        try:
            # Get all items from database for context
            db_items = await asyncio.to_thread(
                lambda: list(Item.objects.filter(
                    name__iregex=r'.*\([1-4]\).*|.*(potion|brew|mix).*'
                ).values('item_id', 'name', 'examine'))
            )
            
            logger.info(f"Found {len(db_items)} relevant items in database")
            
            # Get enriched price data from Wiki API
            item_ids = [item['item_id'] for item in db_items[:500]]  # Limit for testing
            
            async with self.wiki_client as client:
                enriched_data = await client.get_enriched_price_data(item_ids)
            
            logger.info(f"Got enriched data for {len(enriched_data)} items")
            
            # Create embeddings for items with valid data
            await self._create_item_embeddings(enriched_data, db_items)
            
        except Exception as e:
            logger.error(f"Failed to build item index: {e}")
            raise
    
    async def _create_item_embeddings(
        self,
        enriched_data: Dict[int, Tuple[WikiPriceData, Optional[ItemMetadata]]],
        db_items: List[Dict]
    ):
        """Create embeddings for items."""
        logger.info("Creating item embeddings...")
        
        # Create db item lookup
        db_item_lookup = {item['item_id']: item for item in db_items}
        
        embedding_texts = []
        item_contexts = []
        
        for item_id, (price_data, wiki_metadata) in enriched_data.items():
            if not price_data or not price_data.has_valid_prices:
                continue
            
            # Get database item info
            db_item = db_item_lookup.get(item_id, {})
            
            # Create rich context for embedding
            context_text = await self._create_embedding_context(
                item_id, price_data, wiki_metadata, db_item
            )
            
            embedding_texts.append(context_text)
            item_contexts.append({
                'item_id': item_id,
                'price_data': price_data,
                'wiki_metadata': wiki_metadata,
                'db_item': db_item
            })
        
        if not embedding_texts:
            logger.warning("No valid items for embedding")
            return
        
        # Generate embeddings in batch
        embeddings = await self.embedding_service.generate_embeddings_batch(
            embedding_texts,
            batch_size=20
        )
        
        # Build FAISS index
        valid_embeddings = []
        valid_contexts = []
        
        for i, (embedding, context) in enumerate(zip(embeddings, item_contexts)):
            if embedding is not None:
                valid_embeddings.append(embedding)
                valid_contexts.append(context)
                
                # Cache embedding and metadata
                item_id = context['item_id']
                self.item_embeddings[item_id] = embedding
                self.item_metadata_cache[item_id] = context
        
        if valid_embeddings:
            # Create FAISS index
            embedding_dim = len(valid_embeddings[0])
            self.faiss_index = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine
            
            # Normalize embeddings for cosine similarity
            embeddings_matrix = np.array(valid_embeddings, dtype=np.float32)
            faiss.normalize_L2(embeddings_matrix)
            
            self.faiss_index.add(embeddings_matrix)
            
            logger.info(f"Built FAISS index with {len(valid_embeddings)} item embeddings")
        else:
            logger.warning("No valid embeddings generated")
    
    async def _create_embedding_context(
        self,
        item_id: int,
        price_data: WikiPriceData,
        wiki_metadata: Optional[ItemMetadata],
        db_item: Dict
    ) -> str:
        """Create rich context text for embedding with volume analysis."""
        
        # Item identification
        name = wiki_metadata.name if wiki_metadata else db_item.get('name', f'Item {item_id}')
        description = wiki_metadata.examine if wiki_metadata else db_item.get('examine', '')
        
        # Category classification
        category = self._classify_item_category(name)
        
        # Get volume analysis for enhanced context
        volume_analysis = {}
        try:
            wiki_client = RuneScapeWikiAPIClient()
            async with wiki_client:
                volume_analysis = await wiki_client.get_volume_analysis(item_id, "24h")
        except Exception as e:
            logger.debug(f"Could not get volume analysis for item {item_id}: {e}")
        
        # Price analysis with volume context
        price_info = ""
        if price_data.high_price and price_data.low_price:
            avg_price = (price_data.high_price + price_data.low_price) // 2
            spread = abs(price_data.high_price - price_data.low_price)
            spread_pct = (spread / avg_price * 100) if avg_price > 0 else 0
            price_info = f"Price: {avg_price:,} GP (spread: {spread_pct:.1f}%)"
        
        # Volume and market liquidity context
        volume_info = ""
        trading_activity = volume_analysis.get('trading_activity', 'unknown')
        liquidity_score = volume_analysis.get('liquidity_score', 0.0)
        avg_volume_per_hour = volume_analysis.get('avg_volume_per_hour', 0)
        
        if volume_analysis:
            volume_info = f"Trading: {trading_activity} ({avg_volume_per_hour:.0f}/hour) "
            volume_info += f"Liquidity: {liquidity_score:.2f} "
            volume_info += f"Trend: {volume_analysis.get('volume_trend', 'unknown')}"
        
        # Market conditions with volume context
        market_status = "active" if price_data.age_hours < 1 else "normal"
        data_quality = price_data.data_quality
        
        # Trading potential with volume-aware scoring
        if trading_activity in ['very_active', 'active'] and liquidity_score > 0.8:
            trading_potential = "high"
        elif trading_activity in ['moderate'] and liquidity_score > 0.5:
            trading_potential = "normal" 
        elif trading_activity in ['low', 'inactive'] or liquidity_score < 0.3:
            trading_potential = "low"
        else:
            trading_potential = "high" if spread_pct > 5 else "normal" if spread_pct > 1 else "low"
        
        # Risk assessment based on volume
        risk_level = "low"
        if trading_activity in ['very_active', 'active'] and liquidity_score > 0.8:
            risk_level = "low"
        elif trading_activity == 'moderate' and liquidity_score > 0.5:
            risk_level = "medium"
        elif trading_activity in ['low', 'inactive'] or liquidity_score < 0.3:
            risk_level = "high"
        
        return f"""OSRS Trading Item: {name}
Category: {category}
Description: {description}
Market Data: {price_info}
Volume Analysis: {volume_info}
Data Quality: {data_quality} ({price_data.age_hours:.1f}h old)
Market Status: {market_status}
Trading Potential: {trading_potential}
Risk Level: {risk_level}
Members: {'Yes' if wiki_metadata and wiki_metadata.members else 'Unknown'}"""

    def _classify_item_category(self, name: str) -> str:
        """Classify item into trading category."""
        name_lower = name.lower()
        
        if any(kw in name_lower for kw in self.potion_keywords):
            # Detect dose level for potions
            if '(1)' in name_lower:
                return "Potion (1-dose)"
            elif '(2)' in name_lower:
                return "Potion (2-dose)"  
            elif '(3)' in name_lower:
                return "Potion (3-dose)"
            elif '(4)' in name_lower:
                return "Potion (4-dose)"
            else:
                return "Potion"
        elif any(kw in name_lower for kw in self.weapon_keywords):
            return "Weapon"
        elif any(kw in name_lower for kw in self.armor_keywords):
            return "Armor"
        else:
            return "Other"
    
    async def vector_search(
        self, 
        query_text: str, 
        k: int = 50,
        score_threshold: float = 0.3
    ) -> List[SearchResult]:
        """Perform vector similarity search."""
        if not self.faiss_index or self.faiss_index.ntotal == 0:
            logger.warning("FAISS index not available")
            return []
        
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(
                query_text, use_cache=True
            )
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Normalize query embedding
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            # Search FAISS index
            similarities, indices = self.faiss_index.search(query_vector, k)
            
            # Convert to search results
            results = []
            item_contexts = list(self.item_metadata_cache.values())
            
            for similarity, idx in zip(similarities[0], indices[0]):
                if idx >= len(item_contexts) or similarity < score_threshold:
                    continue
                
                context = item_contexts[idx]
                item_id = context['item_id']
                price_data = context['price_data']
                wiki_metadata = context['wiki_metadata']
                db_item = context['db_item']
                
                name = wiki_metadata.name if wiki_metadata else db_item.get('name', f'Item {item_id}')
                
                result = SearchResult(
                    item_id=item_id,
                    name=name,
                    price_data=price_data,
                    metadata=wiki_metadata,
                    vector_score=float(similarity),
                    keyword_score=0.0,  # Will be calculated separately
                    combined_score=float(similarity),
                    context=context
                )
                
                results.append(result)
            
            logger.info(f"Vector search found {len(results)} results for: {query_text[:50]}")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def keyword_search(
        self,
        query_text: str,
        category_filter: Optional[str] = None,
        price_range: Optional[Tuple[int, int]] = None
    ) -> List[SearchResult]:
        """Perform keyword-based search with filters."""
        keywords = query_text.lower().split()
        results = []
        
        for item_id, context in self.item_metadata_cache.items():
            price_data = context['price_data']
            wiki_metadata = context['wiki_metadata']
            db_item = context['db_item']
            
            name = wiki_metadata.name if wiki_metadata else db_item.get('name', '')
            name_lower = name.lower()
            
            # Keyword matching
            keyword_score = 0.0
            for keyword in keywords:
                if keyword in name_lower:
                    keyword_score += 1.0
                elif any(keyword in word for word in name_lower.split()):
                    keyword_score += 0.5
            
            if len(keywords) > 0:
                keyword_score /= len(keywords)  # Normalize
            
            # Category filter
            if category_filter:
                item_category = self._classify_item_category(name)
                if category_filter.lower() not in item_category.lower():
                    continue
            
            # Price filter
            if price_range and price_data.best_buy_price:
                min_price, max_price = price_range
                if not (min_price <= price_data.best_buy_price <= max_price):
                    continue
            
            if keyword_score > 0:
                result = SearchResult(
                    item_id=item_id,
                    name=name,
                    price_data=price_data,
                    metadata=wiki_metadata,
                    vector_score=0.0,  # Will be calculated if needed
                    keyword_score=keyword_score,
                    combined_score=keyword_score,
                    context=context
                )
                
                results.append(result)
        
        # Sort by keyword score
        results.sort(key=lambda x: x.keyword_score, reverse=True)
        
        logger.info(f"Keyword search found {len(results)} results for: {query_text}")
        return results
    
    async def hybrid_search(
        self,
        query_text: str,
        k: int = 30,
        category_filter: Optional[str] = None,
        price_range: Optional[Tuple[int, int]] = None,
        vector_threshold: float = 0.3,
        keyword_threshold: float = 0.1
    ) -> List[SearchResult]:
        """Perform hybrid search combining vector and keyword approaches."""
        logger.info(f"Performing hybrid search for: {query_text}")
        
        # Perform both searches in parallel
        vector_task = self.vector_search(query_text, k * 2, vector_threshold)
        keyword_task = asyncio.to_thread(
            self.keyword_search, query_text, category_filter, price_range
        )
        
        vector_results, keyword_results = await asyncio.gather(
            vector_task, keyword_task, return_exceptions=True
        )
        
        if isinstance(vector_results, Exception):
            logger.error(f"Vector search failed: {vector_results}")
            vector_results = []
        
        if isinstance(keyword_results, Exception):
            logger.error(f"Keyword search failed: {keyword_results}")
            keyword_results = []
        
        # Combine and deduplicate results
        combined_results = {}
        
        # Add vector results
        for result in vector_results:
            combined_results[result.item_id] = result
        
        # Merge keyword results
        for result in keyword_results:
            if result.item_id in combined_results:
                # Update existing result with keyword score
                existing = combined_results[result.item_id]
                existing.keyword_score = result.keyword_score
                existing.combined_score = (
                    self.vector_weight * existing.vector_score +
                    self.keyword_weight * existing.keyword_score
                )
            elif result.keyword_score >= keyword_threshold:
                # Add new result
                combined_results[result.item_id] = result
        
        # Convert to list and sort by combined score
        final_results = list(combined_results.values())
        final_results.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Limit results
        final_results = final_results[:k]
        
        logger.info(f"Hybrid search returned {len(final_results)} combined results")
        return final_results
    
    async def find_decanting_opportunities(
        self,
        min_profit: int = 100,
        risk_level: str = "medium"
    ) -> List[TradingOpportunity]:
        """Find decanting opportunities using hybrid search."""
        # Search for potions with different doses
        potion_results = await self.hybrid_search(
            "potion brew dose (1) (2) (3) (4)",
            k=100,
            category_filter="Potion"
        )
        
        # Group potions by family
        potion_families = self._group_potions_by_family(potion_results)
        
        # Analyze each family for decanting opportunities
        opportunities = []
        
        for family_name, potions in potion_families.items():
            if len(potions) < 2:  # Need at least 2 doses for decanting
                continue
            
            family_opportunities = await self._analyze_decanting_family(
                family_name, potions, min_profit, risk_level
            )
            
            opportunities.extend(family_opportunities)
        
        # Sort by profit potential
        opportunities.sort(key=lambda x: x.profit_potential, reverse=True)
        
        logger.info(f"Found {len(opportunities)} decanting opportunities")
        return opportunities
    
    def _group_potions_by_family(self, potion_results: List[SearchResult]) -> Dict[str, List[SearchResult]]:
        """Group potions by family name."""
        families = {}
        
        for result in potion_results:
            # Extract family name by removing dose information
            import re
            family_name = re.sub(r'\s*\([1-4]\)\s*', '', result.name).strip()
            
            if family_name not in families:
                families[family_name] = []
            
            families[family_name].append(result)
        
        return families
    
    async def _analyze_decanting_family(
        self,
        family_name: str,
        potions: List[SearchResult],
        min_profit: int,
        risk_level: str
    ) -> List[TradingOpportunity]:
        """Analyze a potion family for decanting opportunities."""
        opportunities = []
        
        # Sort potions by dose (extract from name)
        import re
        dose_potions = {}
        
        for potion in potions:
            dose_match = re.search(r'\(([1-4])\)', potion.name)
            if dose_match:
                dose = int(dose_match.group(1))
                dose_potions[dose] = potion
        
        # Find profitable decanting combinations
        for from_dose in sorted(dose_potions.keys(), reverse=True):
            for to_dose in sorted(dose_potions.keys()):
                if from_dose <= to_dose:
                    continue
                
                from_potion = dose_potions[from_dose]
                to_potion = dose_potions[to_dose]
                
                # Calculate decanting profit
                opportunity = await self._calculate_decanting_profit(
                    family_name, from_potion, to_potion, from_dose, to_dose
                )
                
                if opportunity and opportunity.profit_potential >= min_profit:
                    opportunities.append(opportunity)
        
        return opportunities
    
    async def _calculate_decanting_profit(
        self,
        family_name: str,
        from_potion: SearchResult,
        to_potion: SearchResult,
        from_dose: int,
        to_dose: int
    ) -> Optional[TradingOpportunity]:
        """Calculate profit for a specific decanting combination."""
        
        from_price = from_potion.price_data.best_buy_price
        to_price = to_potion.price_data.best_sell_price
        
        if not from_price or not to_price:
            return None
        
        # Calculate decanting conversion
        remaining_doses = from_dose - 1  # One dose consumed in decanting
        target_potions = remaining_doses // to_dose
        
        if target_potions <= 0:
            return None
        
        # Calculate profit
        revenue = target_potions * to_price
        cost = from_price
        profit = revenue - cost
        
        if profit <= 0:
            return None
        
        # Calculate confidence based on data quality and market conditions
        confidence_factors = [
            0.8 if from_potion.price_data.data_quality == "fresh" else 0.5,
            0.8 if to_potion.price_data.data_quality == "fresh" else 0.5,
            0.9 if from_potion.price_data.age_hours < 1 else 0.6,
            0.9 if to_potion.price_data.age_hours < 1 else 0.6
        ]
        
        confidence_score = sum(confidence_factors) / len(confidence_factors)
        
        # Risk assessment
        risk_level = "low"
        if from_price > 50000 or confidence_score < 0.6:
            risk_level = "high"
        elif from_price > 10000 or confidence_score < 0.7:
            risk_level = "medium"
        
        # AI insights (placeholder for now)
        ai_insights = [
            f"Convert {from_dose}-dose to {to_dose}-dose potions",
            f"Expected profit: {profit:,} GP per conversion",
            f"Market data confidence: {confidence_score:.1%}"
        ]
        
        return TradingOpportunity(
            item_id=from_potion.item_id,
            name=family_name,
            category="Decanting",
            opportunity_type="decanting",
            profit_potential=float(profit),
            risk_level=risk_level,
            confidence_score=confidence_score,
            market_context={
                'from_dose': from_dose,
                'to_dose': to_dose,
                'from_price': from_price,
                'to_price': to_price,
                'target_potions': target_potions,
                'from_item_id': from_potion.item_id,
                'to_item_id': to_potion.item_id
            },
            ai_insights=ai_insights,
            related_items=[from_potion.item_id, to_potion.item_id],
            price_data=from_potion.price_data
        )


# Global service instance
hybrid_search_service = HybridSearchService()