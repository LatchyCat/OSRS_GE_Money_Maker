"""
Enhanced Embedding Service for OSRS Trading Intelligence

This service generates comprehensive vector embeddings using snowflake-arctic-embed2:latest
with integrated volume data, confidence scoring, and multi-faceted trading context.

Features:
- Volume-weighted embedding generation
- Trading strategy-specific tagging
- Confidence score integration
- Multi-modal context (prices, volume, metadata)
- AI-ready embeddings for chat and search systems
"""

import asyncio
import hashlib
import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json
import numpy as np
import ollama

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .unified_wiki_price_client import UnifiedPriceClient, PriceData
from .runescape_wiki_client import ItemMetadata
from .advanced_confidence_scoring_service import AdvancedConfidenceScoringService, ConfidenceComponents
from apps.items.models import Item
from apps.embeddings.models import ItemEmbedding

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingContext:
    """Complete context for embedding generation."""
    item_id: int
    item_metadata: Optional[ItemMetadata] = None
    price_data: Optional[PriceData] = None
    confidence_components: Optional[ConfidenceComponents] = None
    trading_tags: List[str] = None
    embedding_text: str = ""
    
    def __post_init__(self):
        if self.trading_tags is None:
            self.trading_tags = []


class EnhancedEmbeddingService:
    """
    Enhanced embedding service with volume data and comprehensive trading context.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model_name = getattr(settings, 'EMBEDDING_MODEL', 'snowflake-arctic-embed2:latest')
        self.client = ollama.Client(host=self.base_url)
        
        # Initialize services
        self.confidence_service = AdvancedConfidenceScoringService()
        
        # Embedding configuration
        self.max_text_length = 2000  # Max characters for embedding
        self.cache_timeout = 86400  # 24 hours
        self.batch_size = 10  # Items per batch
        
        # Trading strategy keywords for enhanced tagging
        self.strategy_keywords = {
            'high_alchemy': [
                'high alch', 'alchemy', 'nature rune', 'magic training',
                'profit per cast', 'alch profitable', 'magic xp'
            ],
            'flipping': [
                'flip profit', 'buy low sell high', 'margin trading',
                'instant buy', 'instant sell', 'ge tax', 'price spread'
            ],
            'decanting': [
                'potion decanting', 'dose conversion', 'barbarian herblore',
                'potion profit', 'dose arbitrage', 'decant value'
            ],
            'crafting': [
                'craft profit', 'material cost', 'skill training',
                'crafting xp', 'production profit', 'resource conversion'
            ],
            'bond_flipping': [
                'bond trading', 'membership conversion', 'premium currency',
                'bond market', 'subscription trading', 'ge tax exempt'
            ],
            'set_combining': [
                'armor set', 'weapon set', 'set conversion',
                'lazy tax', 'set premium', 'complete set'
            ]
        }
    
    async def ensure_model_available(self) -> bool:
        """
        Ensure the embedding model is available in Ollama.
        
        Returns:
            True if model is available, False otherwise
        """
        try:
            # Check if model is already available
            models = await asyncio.get_event_loop().run_in_executor(
                None, self.client.list
            )
            
            model_names = [model.model for model in models.models] if hasattr(models, 'models') else []
            
            if self.model_name not in model_names:
                logger.info(f"Model {self.model_name} not found. Attempting to pull...")
                
                # Pull the model
                await asyncio.get_event_loop().run_in_executor(
                    None, self.client.pull, self.model_name
                )
                
                logger.info(f"Successfully pulled {self.model_name}")
            else:
                logger.debug(f"Model {self.model_name} already available")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure model availability: {e}")
            return False
    
    def create_comprehensive_embedding_text(self, context: EmbeddingContext) -> str:
        """
        Create comprehensive embedding text with volume, confidence, and trading context.
        
        Args:
            context: Complete embedding context
            
        Returns:
            Rich text representation for embedding
        """
        text_parts = []
        
        # 1. Basic Item Information
        if context.item_metadata:
            metadata = context.item_metadata
            text_parts.extend([
                f"Item: {metadata.name}",
                f"Description: {metadata.examine}" if metadata.examine else "",
                f"Type: {'Members' if metadata.members else 'Free-to-play'} item",
                f"High Alchemy Value: {metadata.highalch:,} GP",
                f"GE Buy Limit: {metadata.limit}/4h" if metadata.limit > 0 else "Unlimited GE buy limit",
                f"Base Value: {metadata.value:,} GP"
            ])
        
        # 2. Current Market Data
        if context.price_data:
            price_data = context.price_data
            text_parts.extend([
                f"Current High Price: {price_data.high_price:,} GP (instant buy)",
                f"Current Low Price: {price_data.low_price:,} GP (instant sell)",
                f"Price Data Age: {price_data.age_hours:.1f} hours",
                f"Price Data Quality: {price_data.quality.value}"
            ])
            
            # Volume information
            if price_data.total_volume > 0:
                text_parts.append(f"Trading Volume: {price_data.total_volume:,} units")
            
            # Volume analysis
            if price_data.volume_analysis:
                analysis = price_data.volume_analysis
                text_parts.extend([
                    f"Trading Activity: {analysis.get('trading_activity', 'unknown')}",
                    f"Volume Trend: {analysis.get('volume_trend', 'unknown')}",
                    f"Liquidity Score: {analysis.get('liquidity_score', 0.0):.2f}",
                    f"Average Volume per Hour: {analysis.get('avg_volume_per_hour', 0):.1f}"
                ])
        
        # 3. Confidence and Data Quality
        if context.confidence_components:
            conf = context.confidence_components
            text_parts.extend([
                f"Data Confidence: {conf.total_score:.2f} ({conf.quality_grade} grade)",
                f"Data Freshness Score: {conf.data_freshness:.2f}",
                f"Price Reliability Score: {conf.price_reliability:.2f}",
                f"Volume Consistency Score: {conf.volume_consistency:.2f}",
                f"Liquidity Score: {conf.liquidity_factor:.2f}"
            ])
        
        # 4. Trading Strategy Context
        trading_context = self._generate_trading_strategy_context(context)
        if trading_context:
            text_parts.extend(trading_context)
        
        # 5. AI Trading Tags
        if context.trading_tags:
            text_parts.append(f"Trading Categories: {', '.join(context.trading_tags)}")
        
        # 6. Money-Making Opportunity Analysis
        opportunity_analysis = self._generate_opportunity_analysis(context)
        if opportunity_analysis:
            text_parts.extend(opportunity_analysis)
        
        # Join and limit text length
        full_text = " | ".join(filter(None, text_parts))
        
        if len(full_text) > self.max_text_length:
            # Truncate gracefully at sentence boundaries
            truncated = full_text[:self.max_text_length]
            last_separator = truncated.rfind(" | ")
            if last_separator > self.max_text_length * 0.8:  # Keep if reasonably close to end
                full_text = truncated[:last_separator]
            else:
                full_text = truncated
        
        return full_text
    
    def _generate_trading_strategy_context(self, context: EmbeddingContext) -> List[str]:
        """Generate trading strategy-specific context."""
        strategy_context = []
        
        if not context.item_metadata or not context.price_data:
            return strategy_context
        
        metadata = context.item_metadata
        price_data = context.price_data
        
        # High Alchemy Analysis
        nature_rune_cost = 180
        if metadata.highalch > nature_rune_cost:
            alch_profit = metadata.highalch - nature_rune_cost
            if price_data.high_price > 0:
                net_alch_profit = metadata.highalch - nature_rune_cost - price_data.high_price
                if net_alch_profit > 0:
                    strategy_context.append(
                        f"High Alchemy Profitable: {net_alch_profit:,} GP profit per cast"
                    )
                    if net_alch_profit > 500:
                        strategy_context.append("Excellent high alchemy opportunity")
                    elif net_alch_profit > 100:
                        strategy_context.append("Good high alchemy opportunity")
        
        # Flipping Analysis
        if price_data.high_price > 0 and price_data.low_price > 0:
            # Calculate GE tax (1% with 5M cap)
            ge_tax = min(int(price_data.high_price * 0.01), 5_000_000)
            flip_profit = price_data.high_price - price_data.low_price - ge_tax
            if flip_profit > 0:
                margin_pct = (flip_profit / price_data.low_price) * 100
                strategy_context.append(
                    f"Flipping Opportunity: {flip_profit:,} GP profit ({margin_pct:.1f}% margin)"
                )
                if margin_pct > 10:
                    strategy_context.append("High margin flipping opportunity")
                elif margin_pct > 5:
                    strategy_context.append("Good margin flipping opportunity")
        
        # Volume-based trading suitability
        if price_data.volume_analysis:
            activity = price_data.volume_analysis.get('trading_activity', 'inactive')
            if activity in ['very_active', 'active']:
                strategy_context.append("High liquidity suitable for active trading")
            elif activity in ['moderate']:
                strategy_context.append("Moderate liquidity suitable for patient trading")
            elif activity in ['low', 'inactive']:
                strategy_context.append("Low liquidity requires careful timing")
        
        return strategy_context
    
    def _generate_opportunity_analysis(self, context: EmbeddingContext) -> List[str]:
        """Generate money-making opportunity analysis."""
        opportunities = []
        
        if not context.item_metadata or not context.price_data:
            return opportunities
        
        metadata = context.item_metadata
        price_data = context.price_data
        
        # Detect item categories for specific opportunities
        item_name_lower = metadata.name.lower()
        
        # Potion decanting opportunities
        if any(word in item_name_lower for word in ['potion', 'dose', 'barbarian']):
            if '(4)' in metadata.name:
                opportunities.append("Decanting source: 4-dose potion ideal for breaking down")
            elif '(3)' in metadata.name:
                opportunities.append("Decanting mid-tier: 3-dose potion conversion opportunity")
            elif '(2)' in metadata.name:
                opportunities.append("Decanting target: 2-dose potion profitable endpoint")
            elif '(1)' in metadata.name:
                opportunities.append("Decanting premium: 1-dose maximum value conversion")
        
        # Set combining opportunities
        if any(word in item_name_lower for word in ['helm', 'body', 'legs', 'set']):
            if 'set' in item_name_lower:
                opportunities.append("Complete armor set: Premium lazy tax pricing")
            else:
                opportunities.append("Armor piece: Set combining opportunity")
        
        # Bond and high-value opportunities
        if price_data.high_price > 10_000_000:  # 10M+
            opportunities.append("High-value item: Bond-funded investment opportunity")
        elif price_data.high_price > 1_000_000:  # 1M+
            opportunities.append("Medium-value item: Significant capital requirement")
        
        # Crafting opportunities (basic detection)
        crafting_materials = ['ore', 'bar', 'log', 'hide', 'leather']
        if any(material in item_name_lower for material in crafting_materials):
            opportunities.append("Crafting material: Resource processing opportunity")
        
        return opportunities
    
    def _generate_trading_tags(self, context: EmbeddingContext) -> List[str]:
        """Generate comprehensive trading tags."""
        tags = set()
        
        if not context.item_metadata:
            return list(tags)
        
        metadata = context.item_metadata
        item_name_lower = metadata.name.lower()
        
        # Basic categorization
        if metadata.members:
            tags.add("members")
        else:
            tags.add("f2p")
        
        # Value categorization
        if metadata.highalch > 100000:
            tags.add("high_value")
        elif metadata.highalch > 10000:
            tags.add("medium_value")
        else:
            tags.add("low_value")
        
        # Trading strategy tags
        nature_rune_cost = 180
        if metadata.highalch > nature_rune_cost:
            tags.add("alchable")
            if context.price_data and context.price_data.high_price > 0:
                alch_profit = metadata.highalch - nature_rune_cost - context.price_data.high_price
                if alch_profit > 500:
                    tags.add("excellent_alch")
                elif alch_profit > 100:
                    tags.add("good_alch")
                elif alch_profit > 0:
                    tags.add("profitable_alch")
        
        # Volume-based tags
        if context.price_data and context.price_data.volume_analysis:
            activity = context.price_data.volume_analysis.get('trading_activity', 'inactive')
            tags.add(f"volume_{activity}")
            
            liquidity = context.price_data.volume_analysis.get('liquidity_score', 0.0)
            if liquidity > 0.8:
                tags.add("highly_liquid")
            elif liquidity > 0.5:
                tags.add("moderately_liquid")
            elif liquidity > 0.2:
                tags.add("low_liquidity")
            else:
                tags.add("illiquid")
        
        # Item type detection
        item_type_keywords = {
            'weapon': ['sword', 'axe', 'bow', 'staff', 'wand', 'spear', 'dagger'],
            'armor': ['helm', 'body', 'legs', 'shield', 'boots', 'gloves'],
            'potion': ['potion', 'dose', 'barbarian'],
            'food': ['food', 'fish', 'bread', 'cake', 'pie'],
            'rune': ['rune', 'essence', 'talisman'],
            'resource': ['ore', 'bar', 'log', 'hide', 'cloth'],
            'jewelry': ['ring', 'amulet', 'necklace'],
            'tool': ['pickaxe', 'axe', 'hammer', 'chisel']
        }
        
        for category, keywords in item_type_keywords.items():
            if any(keyword in item_name_lower for keyword in keywords):
                tags.add(category)
                break
        
        # Confidence-based tags
        if context.confidence_components:
            grade = context.confidence_components.quality_grade
            tags.add(f"confidence_{grade.lower().replace('+', '_plus')}")
            
            score = context.confidence_components.total_score
            if score > 0.8:
                tags.add("high_confidence")
            elif score > 0.6:
                tags.add("medium_confidence")
            else:
                tags.add("low_confidence")
        
        return list(tags)
    
    async def generate_enhanced_embedding(self, item_id: int) -> Optional[np.ndarray]:
        """
        Generate enhanced embedding for a single item with full context.
        
        Args:
            item_id: OSRS item ID
            
        Returns:
            NumPy array embedding or None if failed
        """
        try:
            # Ensure model is available
            if not await self.ensure_model_available():
                raise Exception("Embedding model not available")
            
            # Build comprehensive context
            context = await self._build_embedding_context(item_id)
            
            # Generate embedding text
            embedding_text = self.create_comprehensive_embedding_text(context)
            
            if not embedding_text.strip():
                logger.warning(f"Empty embedding text for item {item_id}")
                return None
            
            # Generate embedding
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.embeddings(
                    model=self.model_name,
                    prompt=embedding_text
                )
            )
            
            if 'embedding' not in response:
                logger.error(f"No embedding in response for item {item_id}")
                return None
            
            embedding = np.array(response['embedding'], dtype=np.float32)
            logger.debug(f"Generated embedding for item {item_id}: {embedding.shape}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for item {item_id}: {e}")
            return None
    
    async def _build_embedding_context(self, item_id: int) -> EmbeddingContext:
        """Build comprehensive embedding context for an item."""
        context = EmbeddingContext(item_id=item_id)
        
        try:
            # Get unified price data (includes metadata and volume analysis)
            async with UnifiedPriceClient() as client:
                price_data = await client.get_best_price_data(item_id, include_volume=True)
                
                if price_data:
                    context.price_data = price_data
                    context.item_metadata = price_data.item_metadata
                    
                    # Calculate confidence components
                    context.confidence_components = self.confidence_service.calculate_comprehensive_confidence(
                        price_data, context.item_metadata
                    )
                
                # If no metadata attached to price data, try to get it separately
                if not context.item_metadata:
                    all_metadata = await client.wiki_client.get_item_mapping()
                    context.item_metadata = all_metadata.get(item_id)
            
            # Generate trading tags
            context.trading_tags = self._generate_trading_tags(context)
            
        except Exception as e:
            logger.warning(f"Failed to build complete context for item {item_id}: {e}")
        
        return context
    
    async def batch_generate_embeddings(
        self, 
        item_ids: List[int], 
        save_to_db: bool = True
    ) -> Dict[int, Optional[np.ndarray]]:
        """
        Generate embeddings for multiple items efficiently.
        
        Args:
            item_ids: List of item IDs to process
            save_to_db: Whether to save embeddings to database
            
        Returns:
            Dictionary mapping item_id -> embedding array (or None if failed)
        """
        logger.info(f"Generating enhanced embeddings for {len(item_ids)} items")
        
        embeddings = {}
        
        # Process in batches to avoid overwhelming the system
        for i in range(0, len(item_ids), self.batch_size):
            batch = item_ids[i:i+self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(item_ids) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing embedding batch {batch_num}/{total_batches}")
            
            # Generate embeddings for batch
            batch_tasks = [self.generate_enhanced_embedding(item_id) for item_id in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for item_id, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Embedding failed for item {item_id}: {result}")
                    embeddings[item_id] = None
                else:
                    embeddings[item_id] = result
                    
                    # Save to database if requested
                    if save_to_db and result is not None:
                        await self._save_embedding_to_db(item_id, result)
            
            # Small delay between batches
            await asyncio.sleep(1.0)
        
        success_count = sum(1 for emb in embeddings.values() if emb is not None)
        logger.info(f"Generated {success_count}/{len(item_ids)} embeddings successfully")
        
        return embeddings
    
    async def _save_embedding_to_db(self, item_id: int, embedding: np.ndarray):
        """Save embedding to database."""
        try:
            def save_embedding():
                item = Item.objects.get(item_id=item_id)
                
                # Create comprehensive source text for this embedding
                # This will be used for debugging and re-generation
                source_text = f"Enhanced embedding with volume data and confidence scoring for {item.name}"
                
                # Update or create embedding
                ItemEmbedding.objects.update_or_create(
                    item=item,
                    defaults={
                        'vector': embedding.tolist(),
                        'model_name': self.model_name.split(':')[0],  # Remove :latest part
                        'model_version': 'latest',
                        'source_text': source_text
                    }
                )
            
            await asyncio.get_event_loop().run_in_executor(None, save_embedding)
            logger.debug(f"Saved embedding for item {item_id} to database")
            
        except Exception as e:
            logger.error(f"Failed to save embedding for item {item_id}: {e}")
    
    async def regenerate_all_embeddings(self, force: bool = False) -> Dict[str, Any]:
        """
        Regenerate all embeddings with enhanced context.
        
        Args:
            force: Whether to regenerate existing embeddings
            
        Returns:
            Dictionary with regeneration results
        """
        logger.info("Starting enhanced embedding regeneration")
        
        try:
            # Get all active items
            def get_items():
                query = Item.objects.filter(is_active=True)
                if not force:
                    # Skip items that already have embeddings
                    query = query.filter(embedding__isnull=True)
                return list(query.values_list('item_id', flat=True))
            
            item_ids = await asyncio.get_event_loop().run_in_executor(None, get_items)
            
            if not item_ids:
                return {
                    'status': 'completed',
                    'message': 'No items need embedding generation',
                    'total_items': 0,
                    'successful_embeddings': 0
                }
            
            # Generate embeddings
            embeddings = await self.batch_generate_embeddings(item_ids, save_to_db=True)
            
            # Calculate results
            successful_count = sum(1 for emb in embeddings.values() if emb is not None)
            
            return {
                'status': 'completed',
                'total_items': len(item_ids),
                'successful_embeddings': successful_count,
                'failed_embeddings': len(item_ids) - successful_count,
                'success_rate': (successful_count / len(item_ids)) * 100 if item_ids else 0
            }
            
        except Exception as e:
            logger.error(f"Enhanced embedding regeneration failed: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }