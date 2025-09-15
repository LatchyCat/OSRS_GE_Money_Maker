"""
Celery tasks for syncing data from RuneScape Wiki API.
"""

import logging
from typing import Dict, List, Any
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import datetime

from apps.items.models import Item, ItemCategory, ItemCategoryMapping
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.embeddings.models import ItemEmbedding
from services.api_client import SyncRuneScapeWikiClient
from services.embedding_service import SyncOllamaEmbeddingService
from services.faiss_manager import FaissVectorDatabase
from services.websocket_service import WebSocketService
from services.ai_service import SyncOpenRouterAIService

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def sync_item_mapping(self):
    """
    Sync item mapping data from RuneScape Wiki API.
    This should be run periodically to get new items.
    """
    try:
        logger.info("Starting item mapping sync...")
        
        client = SyncRuneScapeWikiClient()
        mapping_data = client.get_item_mapping()
        
        if not isinstance(mapping_data, list):
            raise ValueError("Invalid mapping data format")
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for item_data in mapping_data:
                item_id = item_data.get('id')
                if not item_id:
                    continue
                
                # Create or update item
                item, created = Item.objects.update_or_create(
                    item_id=item_id,
                    defaults={
                        'name': item_data.get('name', ''),
                        'examine': item_data.get('examine', ''),
                        'icon': item_data.get('icon', ''),
                        'value': item_data.get('value', 0),
                        'high_alch': item_data.get('highalch', 0),
                        'low_alch': item_data.get('lowalch', 0),
                        'limit': item_data.get('limit', 0),
                        'members': item_data.get('members', False),
                        'is_active': True,
                        'updated_at': timezone.now()
                    }
                )
                
                if created:
                    created_count += 1
                    # Create initial profit calculation record
                    ProfitCalculation.objects.get_or_create(
                        item=item,
                        defaults={
                            'current_profit': 0,
                            'current_profit_margin': 0.0
                        }
                    )
                else:
                    updated_count += 1
        
        logger.info(f"Item mapping sync completed: {created_count} created, {updated_count} updated")
        
        # Schedule embedding generation for new items
        if created_count > 0:
            generate_embeddings_for_new_items.delay()
        
        return {
            'status': 'success',
            'items_created': created_count,
            'items_updated': updated_count,
            'total_processed': len(mapping_data)
        }
        
    except Exception as e:
        logger.error(f"Item mapping sync failed: {e}")
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def sync_hot_items_5m(self):
    """
    Sync 5-minute data for hot trading items (high volume).
    This runs every 1-5 minutes for the most active items.
    """
    try:
        logger.info("Starting 5-minute hot items sync...")
        
        # Get hot items (high volume items that need frequent updates)
        hot_items = ProfitCalculation.objects.filter(
            volume_category='hot',
            item__is_active=True
        ).select_related('item')[:50]  # Top 50 hot items
        
        if not hot_items.exists():
            logger.info("No hot items found for 5m sync")
            return {'status': 'success', 'items_updated': 0}
        
        hot_item_ids = [profit_calc.item.item_id for profit_calc in hot_items]
        
        client = SyncRuneScapeWikiClient()
        volume_data = client.get_5m_volume_data(hot_item_ids)
        
        if 'data' not in volume_data:
            raise ValueError("Invalid 5m volume data format")
        
        updated_count = 0
        websocket_service = WebSocketService()
        
        with transaction.atomic():
            for item_id_str, price_info in volume_data['data'].items():
                try:
                    item_id = int(item_id_str)
                    item = Item.objects.get(item_id=item_id)
                except (ValueError, Item.DoesNotExist):
                    continue
                
                # Extract volume data
                high_volume = price_info.get('highPriceVolume', 0)
                low_volume = price_info.get('lowPriceVolume', 0)
                total_volume = high_volume + low_volume
                
                # Calculate price change and volatility
                previous_snapshot = PriceSnapshot.objects.filter(
                    item=item, data_interval='5m'
                ).order_by('-created_at').first()
                
                price_change_pct = 0.0
                if previous_snapshot and previous_snapshot.high_price and price_info.get('avgHighPrice'):
                    old_price = previous_snapshot.high_price
                    new_price = price_info['avgHighPrice']
                    price_change_pct = ((new_price - old_price) / old_price) * 100
                
                # Create 5m price snapshot with volume data
                price_snapshot = PriceSnapshot.objects.create(
                    item=item,
                    high_price=price_info.get('avgHighPrice'),
                    low_price=price_info.get('avgLowPrice'),
                    high_price_volume=high_volume,
                    low_price_volume=low_volume,
                    total_volume=total_volume,
                    price_change_pct=price_change_pct,
                    data_interval='5m',
                    api_source='runescape_wiki'
                )
                
                # Update profit calculation
                profit_calc = ProfitCalculation.objects.get(item=item)
                profit_calc.update_from_price_snapshot(price_snapshot)
                
                updated_count += 1
                
                # Send WebSocket notification for significant changes
                if abs(price_change_pct) > 5.0:  # 5% price change
                    websocket_service.send_price_alert(
                        item.item_id,
                        item.name,
                        price_change_pct,
                        profit_calc.current_profit,
                        'hot_item_update'
                    )
        
        logger.info(f"5-minute hot items sync completed: {updated_count} items updated")
        
        return {
            'status': 'success',
            'items_updated': updated_count,
            'sync_type': '5m_hot_items'
        }
        
    except Exception as e:
        logger.error(f"5-minute hot items sync failed: {e}")
        raise

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def sync_warm_items_1h(self):
    """
    Sync 1-hour data for warm trading items (medium volume).
    This runs every 15-30 minutes for moderately active items.
    """
    try:
        logger.info("Starting 1-hour warm items sync...")
        
        # Get warm items (medium volume items)
        warm_items = ProfitCalculation.objects.filter(
            volume_category='warm',
            item__is_active=True
        ).select_related('item')[:100]  # Top 100 warm items
        
        if not warm_items.exists():
            logger.info("No warm items found for 1h sync")
            return {'status': 'success', 'items_updated': 0}
        
        warm_item_ids = [profit_calc.item.item_id for profit_calc in warm_items]
        
        client = SyncRuneScapeWikiClient()
        hour_data = client.get_1h_prices()
        
        if 'data' not in hour_data:
            raise ValueError("Invalid 1h data format")
        
        updated_count = 0
        
        with transaction.atomic():
            for item_id_str, price_info in hour_data['data'].items():
                item_id = int(item_id_str)
                if item_id not in warm_item_ids:
                    continue
                
                try:
                    item = Item.objects.get(item_id=item_id)
                except Item.DoesNotExist:
                    continue
                
                # Extract volume data
                high_volume = price_info.get('highPriceVolume', 0)
                low_volume = price_info.get('lowPriceVolume', 0)
                total_volume = high_volume + low_volume
                
                # Create 1h price snapshot with volume data
                price_snapshot = PriceSnapshot.objects.create(
                    item=item,
                    high_price=price_info.get('avgHighPrice'),
                    low_price=price_info.get('avgLowPrice'),
                    high_price_volume=high_volume,
                    low_price_volume=low_volume,
                    total_volume=total_volume,
                    data_interval='1h',
                    api_source='runescape_wiki'
                )
                
                # Update profit calculation
                profit_calc = ProfitCalculation.objects.get(item=item)
                profit_calc.hourly_volume = total_volume
                profit_calc.update_from_price_snapshot(price_snapshot)
                
                updated_count += 1
        
        logger.info(f"1-hour warm items sync completed: {updated_count} items updated")
        
        return {
            'status': 'success',
            'items_updated': updated_count,
            'sync_type': '1h_warm_items'
        }
        
    except Exception as e:
        logger.error(f"1-hour warm items sync failed: {e}")
        raise

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 30})
def sync_latest_prices(self):
    """
    Sync latest prices from RuneScape Wiki API for all items.
    This should be run frequently (every 5-10 minutes).
    """
    try:
        logger.info("Starting latest prices sync...")
        
        client = SyncRuneScapeWikiClient()
        prices_data = client.get_latest_prices()
        
        if 'data' not in prices_data:
            raise ValueError("Invalid price data format")
        
        price_data = prices_data['data']
        updated_count = 0
        profit_updates = []
        websocket_service = WebSocketService()
        
        with transaction.atomic():
            for item_id_str, price_info in price_data.items():
                try:
                    item_id = int(item_id_str)
                    item = Item.objects.get(item_id=item_id)
                except (ValueError, Item.DoesNotExist):
                    continue
                
                # Create price snapshot
                high_time = None
                low_time = None
                
                if price_info.get('highTime'):
                    high_time = datetime.fromtimestamp(price_info['highTime'], tz=timezone.get_current_timezone())
                
                if price_info.get('lowTime'):
                    low_time = datetime.fromtimestamp(price_info['lowTime'], tz=timezone.get_current_timezone())
                
                price_snapshot = PriceSnapshot.objects.create(
                    item=item,
                    high_price=price_info.get('high'),
                    high_time=high_time,
                    low_price=price_info.get('low'),
                    low_time=low_time
                )
                
                # Update profit calculation
                profit_calc, _ = ProfitCalculation.objects.get_or_create(
                    item=item,
                    defaults={
                        'current_profit': 0,
                        'current_profit_margin': 0.0
                    }
                )
                
                old_profit = profit_calc.current_profit
                profit_calc.update_from_price_snapshot(price_snapshot)
                
                updated_count += 1
                
                # Prepare data for WebSocket notification
                if price_info.get('high') and abs(profit_calc.current_profit - old_profit) > 10:
                    profit_updates.append({
                        'item_data': {
                            'item_id': item.item_id,
                            'name': item.name,
                            'high_alch': item.high_alch
                        },
                        'price_data': {
                            'high_price': price_info.get('high'),
                            'low_price': price_info.get('low'),
                            'high_time': high_time.isoformat() if high_time else None,
                            'low_time': low_time.isoformat() if low_time else None
                        },
                        'profit_data': {
                            'current_profit': profit_calc.current_profit,
                            'current_profit_margin': profit_calc.current_profit_margin,
                            'previous_profit': old_profit
                        }
                    })
        
        # Send WebSocket notifications for significant price changes
        for update in profit_updates[:50]:  # Limit to avoid spam
            websocket_service.send_price_update(
                update['item_data'],
                update['price_data'], 
                update['profit_data']
            )
        
        logger.info(f"Latest prices sync completed: {updated_count} items updated, {len(profit_updates)} notifications sent")
        
        return {
            'status': 'success',
            'items_updated': updated_count,
            'notifications_sent': len(profit_updates)
        }
        
    except Exception as e:
        logger.error(f"Latest prices sync failed: {e}")
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 2, 'countdown': 300})
def generate_embeddings_for_new_items(self):
    """
    Generate embeddings for items that don't have them yet.
    This is a heavy task and should be run less frequently.
    """
    try:
        logger.info("Starting embedding generation for new items...")
        
        # Get items without embeddings
        items_without_embeddings = Item.objects.filter(
            is_active=True,
            embedding__isnull=True
        )[:100]  # Process in batches
        
        if not items_without_embeddings.exists():
            logger.info("No items need embedding generation")
            return {'status': 'success', 'items_processed': 0}
        
        embedding_service = SyncOllamaEmbeddingService()
        faiss_db = FaissVectorDatabase()
        
        # Prepare texts for embedding
        items_data = []
        texts = []
        
        for item in items_without_embeddings:
            source_text = ItemEmbedding.create_source_text(item)
            items_data.append(item)
            texts.append(source_text)
        
        # Generate embeddings in batch
        embeddings = embedding_service.generate_embeddings_batch(texts, batch_size=5)
        
        created_count = 0
        faiss_updates = []
        
        with transaction.atomic():
            for item, embedding, source_text in zip(items_data, embeddings, texts):
                if embedding is None:
                    logger.warning(f"Failed to generate embedding for item {item.name}")
                    continue
                
                # Create embedding record
                item_embedding = ItemEmbedding.objects.create(
                    item=item,
                    vector=embedding,
                    source_text=source_text,
                    model_name='snowflake-arctic-embed2',
                    model_version='latest'
                )
                
                # Prepare for FAISS update
                faiss_updates.append((item.item_id, embedding))
                created_count += 1
        
        # Update FAISS index
        for item_id, embedding in faiss_updates:
            faiss_db.add_vector(item_id, embedding)
        
        if faiss_updates:
            faiss_db.save_index()
        
        logger.info(f"Embedding generation completed: {created_count} embeddings created")
        
        return {
            'status': 'success',
            'embeddings_created': created_count,
            'faiss_updated': len(faiss_updates)
        }
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 2, 'countdown': 600})
def generate_daily_market_summary(self):
    """
    Generate daily AI market summary and send to WebSocket clients.
    Should be run once or twice per day.
    """
    try:
        logger.info("Starting daily market summary generation...")
        
        # Get top profitable items
        top_items_qs = ProfitCalculation.objects.filter(
            current_profit__gt=0,
            item__is_active=True
        ).select_related('item').order_by('-current_profit')[:20]
        
        top_items = []
        for profit_calc in top_items_qs:
            item = profit_calc.item
            top_items.append({
                'name': item.name,
                'item_id': item.item_id,
                'current_profit': profit_calc.current_profit,
                'current_profit_margin': profit_calc.current_profit_margin,
                'daily_volume': profit_calc.daily_volume,
                'high_alch': item.high_alch
            })
        
        if not top_items:
            logger.warning("No profitable items found for market summary")
            return {'status': 'success', 'summary_generated': False}
        
        # Generate AI market summary
        ai_service = SyncOpenRouterAIService()
        market_summary = ai_service.generate_market_summary(top_items)
        
        # Send to WebSocket clients
        websocket_service = WebSocketService()
        websocket_service.send_market_summary(market_summary)
        
        # Broadcast system message
        websocket_service.broadcast_system_message(
            "Daily market analysis complete! Check the latest recommendations.",
            "info"
        )
        
        logger.info("Daily market summary generation completed")
        
        return {
            'status': 'success',
            'summary_generated': True,
            'items_analyzed': len(top_items),
            'tokens_used': market_summary.get('tokens_used', 0)
        }
        
    except Exception as e:
        logger.error(f"Daily market summary generation failed: {e}")
        raise


@shared_task(bind=True)
def cleanup_old_data(self):
    """
    Clean up old price snapshots and other temporary data.
    Should be run daily.
    """
    try:
        logger.info("Starting data cleanup...")
        
        from datetime import timedelta
        
        # Delete price snapshots older than 7 days
        week_ago = timezone.now() - timedelta(days=7)
        old_snapshots = PriceSnapshot.objects.filter(created_at__lt=week_ago)
        deleted_snapshots = old_snapshots.count()
        old_snapshots.delete()
        
        # Delete inactive WebSocket connections older than 1 day
        day_ago = timezone.now() - timedelta(days=1)
        old_connections = WebSocketConnection.objects.filter(
            is_active=False,
            last_activity__lt=day_ago
        )
        deleted_connections = old_connections.count()
        old_connections.delete()
        
        # Deactivate very old search queries (keep for analytics)
        month_ago = timezone.now() - timedelta(days=30)
        old_queries = SearchQuery.objects.filter(
            last_searched__lt=month_ago,
            search_count=1
        )
        old_queries_count = old_queries.count()
        old_queries.delete()
        
        logger.info(f"Data cleanup completed: {deleted_snapshots} snapshots, {deleted_connections} connections, {old_queries_count} queries deleted")
        
        return {
            'status': 'success',
            'snapshots_deleted': deleted_snapshots,
            'connections_deleted': deleted_connections,
            'queries_deleted': old_queries_count
        }
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        raise


# Schedule periodic tasks
@shared_task
def health_check_services():
    """
    Health check for all services.
    Run every few minutes to ensure everything is working.
    """
    try:
        results = {
            'database': False,
            'api_client': False,
            'ai_service': False,
            'embedding_service': False,
            'timestamp': timezone.now().isoformat()
        }
        
        # Database check
        try:
            Item.objects.count()
            results['database'] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        # API client check
        try:
            client = SyncRuneScapeWikiClient()
            results['api_client'] = client.health_check()
        except Exception as e:
            logger.error(f"API client health check failed: {e}")
        
        # AI service check
        try:
            ai_service = SyncOpenRouterAIService()
            results['ai_service'] = ai_service.health_check()
        except Exception as e:
            logger.error(f"AI service health check failed: {e}")
        
        # Embedding service check
        try:
            embedding_service = SyncOllamaEmbeddingService()
            results['embedding_service'] = embedding_service.health_check()
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
        
        # Log overall status
        healthy_services = sum(1 for status in results.values() if status is True)
        total_services = len([k for k in results.keys() if k != 'timestamp'])
        
        if healthy_services == total_services:
            logger.info("All services are healthy")
        else:
            logger.warning(f"Only {healthy_services}/{total_services} services are healthy")
        
        return results
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }