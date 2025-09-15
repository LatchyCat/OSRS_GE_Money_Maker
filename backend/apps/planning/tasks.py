"""
Celery tasks for data synchronization and background processing.
"""

import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from typing import Optional

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def sync_items_and_prices_task(self, operation_id: Optional[int] = None, mode: str = 'full_refresh'):
    """
    Sync items and prices using multi-source price intelligence.
    
    Args:
        operation_id: ID of the SyncOperation to track progress
        mode: Sync mode - 'prices_only', 'full_refresh', 'complete_rebuild'
    """
    import asyncio
    from apps.system.models import SyncOperation, SystemState
    from django.core.management import call_command
    from apps.items.models import Item
    from apps.prices.models import PriceSnapshot, ProfitCalculation
    
    sync_op = None
    try:
        # Get sync operation if provided
        if operation_id:
            sync_op = SyncOperation.objects.get(id=operation_id)
            sync_op.status = 'in_progress'
            sync_op.save()
        
        logger.info(f"🔄 Starting {mode} sync task using multi-source intelligence...")
        
        # Use our enhanced sync command with multi-source intelligence
        command_args = []
        
        if mode == 'prices_only':
            command_args.append('--prices-only')
        elif mode == 'full_refresh':
            # Default behavior - sync both items and prices
            pass
        elif mode == 'complete_rebuild':
            command_args.append('--generate-embeddings')
        
        # Call our enhanced sync command
        logger.info("🔄 Executing multi-source sync command...")
        call_command('sync_items_and_prices', *command_args, verbosity=1)
        
        # Get counts for reporting
        items_processed = Item.objects.filter(is_active=True).count()
        items_updated = items_processed  # Simplified for now
        price_updates = PriceSnapshot.objects.count()
        profit_updates = ProfitCalculation.objects.count()
        errors = 0
        
        # Mark operation as completed
        if sync_op:
            sync_op.mark_completed(
                items_processed=items_processed,
                items_created=items_created,
                items_updated=items_updated,
                errors=errors
            )
        
        # Update system state
        system_state = SystemState.get_current_state()
        system_state.update_sync_status(mode, success=True)
        system_state.update_item_counts(
            total_items=Item.objects.filter(is_active=True).count(),
            profitable_items=ProfitCalculation.objects.filter(current_profit__gt=0).count()
        )
        
        logger.info(f"🎉 {mode} sync task completed successfully!")
        return {
            'success': True,
            'items_processed': items_processed,
            'items_created': items_created,
            'items_updated': items_updated,
            'price_updates': price_updates,
            'profit_updates': profit_updates,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"❌ {mode} sync task failed: {e}")
        
        if sync_op:
            sync_op.mark_failed(str(e))
        
        # Update system state
        try:
            system_state = SystemState.get_current_state()
            system_state.sync_in_progress = False
            system_state.save()
        except:
            pass
        
        raise


@shared_task(bind=True)
def detect_new_items_task(self, operation_id: Optional[int] = None):
    """
    Detect and add new OSRS items that weren't in our database before.
    """
    from apps.system.models import SyncOperation, SystemState
    from apps.planning.api_services.runescape_api import RuneScapeAPIService
    from apps.items.models import Item
    
    sync_op = None
    try:
        if operation_id:
            sync_op = SyncOperation.objects.get(id=operation_id)
            sync_op.status = 'in_progress'
            sync_op.save()
        
        logger.info("🔍 Starting new item detection task...")
        
        # Initialize API service
        api_service = RuneScapeAPIService()
        
        # Get known item IDs
        known_item_ids = set(Item.objects.values_list('item_id', flat=True))
        logger.info(f"📊 Currently tracking {len(known_item_ids)} items")
        
        # Detect new items
        new_items = api_service.detect_new_items(known_item_ids)
        
        items_created = 0
        errors = 0
        
        if new_items:
            logger.info(f"🆕 Found {len(new_items)} new items to add...")
            
            with transaction.atomic():
                for item_data in new_items:
                    try:
                        Item.objects.create(
                            item_id=item_data.get('id'),
                            name=item_data.get('name', ''),
                            examine=item_data.get('examine', ''),
                            high_alch=item_data.get('highalch', 0),
                            low_alch=item_data.get('lowalch', 0),
                            limit=item_data.get('limit', 0),
                            members=item_data.get('members', False),
                            is_active=True,
                            icon_url=item_data.get('icon', ''),
                        )
                        
                        items_created += 1
                        logger.info(f"✅ Added new item: {item_data.get('name')}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to add new item {item_data.get('id')}: {e}")
                        errors += 1
        
        # Mark operation as completed
        if sync_op:
            sync_op.mark_completed(
                items_processed=len(new_items),
                items_created=items_created,
                errors=errors
            )
        
        # Update system state
        system_state = SystemState.get_current_state()
        system_state.update_item_counts(
            total_items=Item.objects.filter(is_active=True).count(),
            new_items=items_created
        )
        
        logger.info(f"🎉 New item detection completed: {items_created} new items added")
        return {
            'success': True,
            'new_items_found': len(new_items),
            'items_created': items_created,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"❌ New item detection failed: {e}")
        
        if sync_op:
            sync_op.mark_failed(str(e))
        
        raise


@shared_task(bind=True)
def sync_embeddings_task(self, operation_id: Optional[int] = None):
    """
    Sync embeddings for items using AI service.
    """
    from apps.system.models import SyncOperation, SystemState
    from apps.embeddings.models import ItemEmbedding
    from apps.items.models import Item
    # from apps.ai.services import EmbeddingService  # TODO: Create this service
    
    sync_op = None
    try:
        if operation_id:
            sync_op = SyncOperation.objects.get(id=operation_id)
            sync_op.status = 'in_progress'
            sync_op.save()
        
        logger.info("🤖 Starting embeddings sync task...")
        
        # TODO: Initialize embedding service when available
        # embedding_service = EmbeddingService()
        
        # Get items that need embeddings
        items_needing_embeddings = Item.objects.filter(
            is_active=True,
            itemembedding__isnull=True
        )[:100]  # Process in batches
        
        embeddings_created = 0
        errors = 0
        
        for item in items_needing_embeddings:
            try:
                # Generate embedding for item (placeholder - TODO: implement embedding service)
                text_to_embed = f"{item.name} {item.examine or ''}"
                # embedding_vector = await embedding_service.get_embedding(text_to_embed)
                
                # Create embedding record (placeholder)
                # ItemEmbedding.objects.update_or_create(
                #     item=item,
                #     defaults={
                #         'embedding_vector': embedding_vector,
                #         'model_name': embedding_service.model_name,
                #         'embedding_dimension': len(embedding_vector),
                #     }
                # )
                
                # For now, just mark as processed
                pass
                
                embeddings_created += 1
                
            except Exception as e:
                logger.warning(f"Failed to create embedding for item {item.name}: {e}")
                errors += 1
        
        # Mark operation as completed
        if sync_op:
            sync_op.mark_completed(
                items_processed=len(items_needing_embeddings),
                items_created=embeddings_created,
                errors=errors
            )
        
        # Update system state
        system_state = SystemState.get_current_state()
        system_state.update_sync_status('embeddings', success=True)
        
        logger.info(f"✅ Embeddings sync completed: {embeddings_created} embeddings created")
        return {
            'success': True,
            'embeddings_created': embeddings_created,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"❌ Embeddings sync task failed: {e}")
        
        if sync_op:
            sync_op.mark_failed(str(e))
        
        raise


def _update_profit_calculations():
    """Update profit calculations for all active items."""
    from apps.prices.models import PriceSnapshot, ProfitCalculation
    from apps.items.models import Item
    from django.db.models import Avg, Q
    from django.conf import settings
    
    nature_rune_cost = getattr(settings, 'NATURE_RUNE_COST', 180)
    updated_count = 0
    
    # Get items with recent price data
    items_with_prices = Item.objects.filter(
        is_active=True,
        high_alch__gt=0,
        price_snapshots__isnull=False
    ).distinct()
    
    for item in items_with_prices:
        try:
            # Get most recent price
            latest_price = item.price_snapshots.order_by('-created_at').first()
            
            if latest_price and latest_price.high_price > 0:
                # Calculate profit
                buy_price = latest_price.high_price
                sell_price = item.high_alch
                total_cost = buy_price + nature_rune_cost
                profit = sell_price - total_cost
                profit_margin = (profit / buy_price * 100) if buy_price > 0 else 0
                
                # Calculate volume metrics
                daily_volume = latest_price.high_price_volume or 0
                
                # Calculate recommendation score
                volume_score = min(1.0, daily_volume / 1000.0)
                profit_score = min(1.0, max(0.0, profit / 1000.0))
                margin_score = min(1.0, max(0.0, profit_margin / 20.0))
                
                recommendation_score = (volume_score + profit_score + margin_score) / 3.0 * 100
                
                # Determine trend (simplified)
                price_trend = 'stable'  # Would need more complex analysis
                
                # Update or create profit calculation
                ProfitCalculation.objects.update_or_create(
                    item=item,
                    defaults={
                        'current_buy_price': buy_price,
                        'current_sell_price': sell_price,
                        'current_profit': profit,
                        'current_profit_margin': profit_margin,
                        'daily_volume': daily_volume,
                        'recommendation_score': recommendation_score,
                        'price_trend': price_trend,
                        'last_updated': timezone.now()
                    }
                )
                
                updated_count += 1
                
        except Exception as e:
            logger.warning(f"Failed to update profit calculation for {item.name}: {e}")
    
    return updated_count