"""
Money Maker Embedding Tasks

Celery tasks for maintaining up-to-date embeddings for money maker strategies.
Critical for price-sensitive opportunities like your friend's approach.

Key schedules:
- Hourly: High-volume items and price-sensitive strategies  
- Every 4 hours: Standard money maker items
- Daily: Full re-embedding with relationship updates
- Weekly: Complete vector database rebuild
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
import numpy as np

from celery import shared_task
from django.db.models import Q, F, Count, Min, Max
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from apps.items.models import Item
from apps.prices.models import ProfitCalculation, PriceSnapshot
from apps.embeddings.models import ItemEmbedding, FaissIndex
from apps.trading_strategies.models import TradingStrategy, MoneyMakerStrategy
from services.embedding_service import EmbeddingService
from services.faiss_manager import FAISSManager
from services.money_maker_detector import MoneyMakerDetector
from services.set_combining_detector import SetCombiningDetector
from apps.trading_strategies.services.decanting_detector import DecantingDetector

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='money_maker.reembed_hourly_items')
def reembed_hourly_money_maker_items(self):
    """
    Hourly re-embedding task for price-sensitive money maker items.
    
    Focuses on:
    - Hot volume items (active flipping targets)
    - Recently profitable decanting potions  
    - High-value bond flipping targets
    - Set pieces with volatile pricing
    """
    try:
        logger.info("Starting hourly money maker re-embedding")
        
        # Get items that need hourly updates
        target_items = _get_hourly_update_targets()
        
        if not target_items:
            logger.info("No items require hourly re-embedding")
            return {'status': 'success', 'items_processed': 0}
        
        logger.info(f"Re-embedding {len(target_items)} items for hourly update")
        
        # Update embeddings
        embedding_service = EmbeddingService()
        updated_count = 0
        
        for item in target_items:
            try:
                # Update money maker scores first
                if hasattr(item, 'profit_calc') and item.profit_calc:
                    item.profit_calc.update_money_maker_scores()
                    item.profit_calc.save()
                
                # Re-generate embedding with fresh money maker context
                new_source_text = ItemEmbedding.create_source_text(item)
                
                # Get existing embedding
                embedding = ItemEmbedding.objects.filter(item=item).first()
                if embedding:
                    # Check if source text changed (price-sensitive context)
                    if embedding.source_text != new_source_text:
                        # Generate new vector
                        new_vector = embedding_service.generate_embedding(new_source_text)
                        if new_vector:
                            embedding.vector = new_vector.tolist()
                            embedding.source_text = new_source_text
                            embedding.updated_at = timezone.now()
                            embedding.save()
                            updated_count += 1
                            
                            logger.debug(f"Updated embedding for {item.name}")
                
            except Exception as e:
                logger.error(f"Error re-embedding {item.name}: {e}")
                continue
        
        # Update FAISS index if we changed embeddings
        if updated_count > 0:
            _update_faiss_index_incremental(target_items)
        
        logger.info(f"Hourly re-embedding complete: {updated_count} items updated")
        
        return {
            'status': 'success',
            'items_processed': updated_count,
            'total_candidates': len(target_items)
        }
        
    except Exception as e:
        logger.error(f"Hourly re-embedding task failed: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True, name='money_maker.detect_and_embed_opportunities')
def detect_and_embed_new_opportunities(self, capital_range: str = 'all'):
    """
    Detect new money maker opportunities and ensure they're embedded.
    
    Args:
        capital_range: 'starter' (0-10M), 'intermediate' (10-50M), 
                      'advanced' (50-200M), 'expert' (200M+), or 'all'
    """
    try:
        logger.info(f"Detecting money maker opportunities for {capital_range} capital range")
        
        # Define capital ranges
        capital_ranges = {
            'starter': 10_000_000,
            'intermediate': 50_000_000, 
            'advanced': 200_000_000,
            'expert': 1_000_000_000,
            'all': 1_000_000_000
        }
        
        capital_limit = capital_ranges.get(capital_range, 50_000_000)
        
        # Detect opportunities
        detector = MoneyMakerDetector()
        opportunities_data = asyncio.run(
            detector.detect_all_opportunities(capital_limit)
        )
        
        # Collect item IDs that need embedding updates
        items_to_update = set()
        
        for opp in opportunities_data:
            # Add primary items
            for item_data in opp.primary_items:
                if 'item_id' in item_data:
                    items_to_update.add(item_data['item_id'])
            
            # Add secondary items (for sets)
            for item_data in opp.secondary_items:
                if 'item_id' in item_data:
                    items_to_update.add(item_data['item_id'])
        
        # Update embeddings for opportunity items
        items = Item.objects.filter(item_id__in=list(items_to_update))
        embedding_service = EmbeddingService()
        updated_count = 0
        
        for item in items:
            try:
                # Ensure item has updated profit calculation
                if hasattr(item, 'profit_calc') and item.profit_calc:
                    item.profit_calc.update_money_maker_scores()
                    item.profit_calc.save()
                
                # Update embedding
                _update_item_embedding(item, embedding_service)
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error updating embedding for opportunity item {item.name}: {e}")
                continue
        
        logger.info(f"Opportunity detection complete: {len(opportunities_data)} opportunities, {updated_count} embeddings updated")
        
        return {
            'status': 'success',
            'opportunities_found': len(opportunities_data),
            'embeddings_updated': updated_count,
            'capital_range': capital_range
        }
        
    except Exception as e:
        logger.error(f"Opportunity detection task failed: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True, name='money_maker.full_reembedding_cycle')
def full_money_maker_reembedding_cycle(self):
    """
    Complete re-embedding cycle for all money maker relevant items.
    Runs daily to ensure comprehensive coverage.
    """
    try:
        logger.info("Starting full money maker re-embedding cycle")
        
        # Get all items with profit calculations (active in strategies)
        items_with_profits = Item.objects.filter(
            profit_calc__isnull=False
        ).select_related('profit_calc').prefetch_related('categories')
        
        # Add money maker specific items (potions, armor pieces, weapons, etc.)
        money_maker_items = Item.objects.filter(
            Q(name__icontains='potion') |
            Q(name__icontains='armor') |
            Q(name__icontains='helm') |
            Q(name__icontains='body') |
            Q(name__icontains='legs') |
            Q(name__icontains='skirt') |
            Q(name__icontains='chestplate') |
            Q(name__icontains='tassets') |
            Q(name__icontains='godsword') |
            Q(name__icontains='hilt') |
            Q(name__icontains='blade') |
            Q(name__icontains='dharok') |
            Q(name__icontains='ahrim') |
            Q(name__icontains='karil') |
            Q(name__icontains='torag') |
            Q(name__icontains='verac') |
            Q(name__icontains='guthan') |
            Q(name__icontains='armadyl') |
            Q(name__icontains='bandos') |
            Q(name__icontains='bond')
        )
        
        # Combine and dedupe
        all_target_items = (items_with_profits | money_maker_items).distinct()
        
        logger.info(f"Re-embedding {all_target_items.count()} money maker items")
        
        # Process in batches to avoid memory issues
        embedding_service = EmbeddingService()
        batch_size = 100
        updated_count = 0
        error_count = 0
        
        for i in range(0, all_target_items.count(), batch_size):
            batch = all_target_items[i:i + batch_size]
            
            for item in batch:
                try:
                    # Update money maker scores
                    if hasattr(item, 'profit_calc') and item.profit_calc:
                        item.profit_calc.update_money_maker_scores()
                        item.profit_calc.save()
                    
                    # Update embedding
                    if _update_item_embedding(item, embedding_service):
                        updated_count += 1
                        
                except Exception as e:
                    logger.error(f"Error in full re-embedding for {item.name}: {e}")
                    error_count += 1
                    continue
            
            # Log progress
            logger.info(f"Full re-embedding progress: {i + len(batch)}/{all_target_items.count()}")
        
        # Rebuild FAISS index with all updated embeddings
        logger.info("Rebuilding FAISS index after full re-embedding")
        _rebuild_faiss_index()
        
        logger.info(f"Full re-embedding cycle complete: {updated_count} updated, {error_count} errors")
        
        return {
            'status': 'success',
            'items_updated': updated_count,
            'errors': error_count,
            'total_processed': all_target_items.count()
        }
        
    except Exception as e:
        logger.error(f"Full re-embedding cycle failed: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True, name='money_maker.update_strategy_embeddings')
def update_trading_strategy_embeddings(self):
    """
    Update embeddings for items involved in active trading strategies.
    """
    try:
        logger.info("Updating embeddings for active trading strategies")
        
        # Get items from active money maker strategies
        active_strategies = TradingStrategy.objects.filter(
            is_active=True,
            strategy_type__in=['flipping', 'decanting', 'set_combining', 'bond_flipping']
        )
        
        items_to_update = set()
        
        # Collect items from decanting strategies
        for strategy in active_strategies.filter(strategy_type='decanting'):
            decanting_opportunities = strategy.decanting_opportunities.all()
            for opp in decanting_opportunities:
                items_to_update.add(opp.item_id)
        
        # Collect items from set combining strategies  
        for strategy in active_strategies.filter(strategy_type='set_combining'):
            set_opportunities = strategy.set_combining_opportunities.all()
            for opp in set_opportunities:
                items_to_update.update(opp.piece_ids)
                items_to_update.add(opp.set_item_id)
        
        # Get the actual Item objects
        items = Item.objects.filter(item_id__in=list(items_to_update))
        
        embedding_service = EmbeddingService()
        updated_count = 0
        
        for item in items:
            try:
                if _update_item_embedding(item, embedding_service):
                    updated_count += 1
            except Exception as e:
                logger.error(f"Error updating strategy embedding for {item.name}: {e}")
                continue
        
        logger.info(f"Strategy embedding update complete: {updated_count} items updated")
        
        return {
            'status': 'success',
            'items_updated': updated_count,
            'strategies_processed': active_strategies.count()
        }
        
    except Exception as e:
        logger.error(f"Strategy embedding update failed: {e}")
        return {'status': 'error', 'error': str(e)}


def _get_hourly_update_targets() -> List[Item]:
    """Get items that need hourly embedding updates."""
    
    # Hot volume items (active trading)
    hot_items = Item.objects.filter(
        profit_calc__volume_category='hot',
        profit_calc__is_profitable=True
    ).select_related('profit_calc')[:50]
    
    # Recently updated prices (last 2 hours)
    recently_updated = Item.objects.filter(
        price_snapshots__created_at__gte=timezone.now() - timedelta(hours=2),
        profit_calc__isnull=False
    ).select_related('profit_calc').distinct()[:30]
    
    # High-value items (bond flipping targets)
    high_value_items = Item.objects.filter(
        profit_calc__current_buy_price__gte=10_000_000  # 10M+
    ).select_related('profit_calc')[:20]
    
    # Popular potions for decanting
    potion_items = Item.objects.filter(
        Q(name__icontains='combat potion') |
        Q(name__icontains='prayer potion') |
        Q(name__icontains='ranging potion') |
        Q(name__icontains='super strength') |
        Q(name__icontains='super attack') |
        Q(name__icontains='super defence')
    ).select_related('profit_calc')[:20]
    
    # Combine and dedupe
    all_targets = set()
    for queryset in [hot_items, recently_updated, high_value_items, potion_items]:
        all_targets.update(queryset)
    
    return list(all_targets)


def _update_item_embedding(item: Item, embedding_service: EmbeddingService) -> bool:
    """Update embedding for a single item."""
    try:
        new_source_text = ItemEmbedding.create_source_text(item)
        
        embedding, created = ItemEmbedding.objects.get_or_create(
            item=item,
            defaults={
                'source_text': new_source_text,
                'model_name': 'snowflake-arctic-embed2',
                'model_version': 'latest'
            }
        )
        
        # Generate new vector if text changed or embedding is new
        if created or embedding.source_text != new_source_text:
            new_vector = embedding_service.generate_embedding(new_source_text)
            if new_vector:
                embedding.vector = new_vector.tolist()
                embedding.source_text = new_source_text
                embedding.updated_at = timezone.now()
                embedding.save()
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error updating embedding for {item.name}: {e}")
        return False


def _update_faiss_index_incremental(updated_items: List[Item]):
    """Update FAISS index with new embeddings."""
    try:
        faiss_manager = FAISSManager()
        
        # Get updated embeddings
        embeddings = ItemEmbedding.objects.filter(
            item__in=updated_items,
            vector__isnull=False
        )
        
        vectors = []
        item_ids = []
        
        for emb in embeddings:
            vectors.append(np.array(emb.vector, dtype=np.float32))
            item_ids.append(emb.item.item_id)
        
        if vectors:
            # Update index
            faiss_manager.add_vectors(np.array(vectors), item_ids)
            logger.info(f"Updated FAISS index with {len(vectors)} vectors")
        
    except Exception as e:
        logger.error(f"Error updating FAISS index: {e}")


def _rebuild_faiss_index():
    """Completely rebuild the FAISS index."""
    try:
        faiss_manager = FAISSManager()
        
        # Get all embeddings
        all_embeddings = ItemEmbedding.objects.filter(
            vector__isnull=False
        ).select_related('item')
        
        vectors = []
        item_ids = []
        metadata = []
        
        for emb in all_embeddings:
            vectors.append(np.array(emb.vector, dtype=np.float32))
            item_ids.append(emb.item.item_id)
            metadata.append({
                'item_name': emb.item.name,
                'updated_at': emb.updated_at.isoformat(),
                'model_name': emb.model_name
            })
        
        if vectors:
            # Rebuild index completely
            faiss_manager.build_index(np.array(vectors), item_ids, metadata)
            logger.info(f"Rebuilt FAISS index with {len(vectors)} vectors")
        
    except Exception as e:
        logger.error(f"Error rebuilding FAISS index: {e}")


# Scheduled task configurations for Celery Beat
MONEY_MAKER_SCHEDULE = {
    'reembed-hourly-money-makers': {
        'task': 'money_maker.reembed_hourly_items',
        'schedule': 3600.0,  # Every hour
    },
    'detect-opportunities-every-4h': {
        'task': 'money_maker.detect_and_embed_opportunities',
        'schedule': 14400.0,  # Every 4 hours
        'kwargs': {'capital_range': 'all'}
    },
    'full-reembedding-daily': {
        'task': 'money_maker.full_reembedding_cycle',
        'schedule': 86400.0,  # Daily at midnight
    },
    'update-strategy-embeddings-every-6h': {
        'task': 'money_maker.update_strategy_embeddings',
        'schedule': 21600.0,  # Every 6 hours
    }
}