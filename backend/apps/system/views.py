"""
API views for system management and data refresh functionality.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.db import models
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import SystemState, SyncOperation
# from services.multi_source_price_client import MultiSourcePriceClient  # Temporarily disabled
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.items.models import Item

logger = logging.getLogger(__name__)


@api_view(['POST'])
def refresh_data(request):
    """
    Manual data refresh endpoint that works without Celery dependency.
    
    Forces immediate refresh of price data from OSRS API and updates
    profit calculations. This is called by the frontend refresh button.
    
    Query parameters:
    - force: If true, refresh all data regardless of age
    - hot_items_only: If true, only refresh high-volume items
    """
    try:
        force_refresh = request.data.get('force', False)
        hot_items_only = request.data.get('hot_items_only', False)
        
        logger.info(f"🔄 Manual data refresh requested (force={force_refresh}, hot_items_only={hot_items_only})")
        
        # Create sync operation record
        sync_op = SyncOperation.objects.create(
            operation_type='manual_refresh',
            status='started'
        )
        
        # Get system state
        system_state = SystemState.get_current_state()
        
        try:
            # Perform the refresh
            result = _perform_data_refresh(
                sync_op=sync_op,
                force_refresh=force_refresh,
                hot_items_only=hot_items_only
            )
            
            # Update system state
            system_state.update_sync_status('manual_refresh', success=True)
            
            return Response({
                'success': True,
                'message': 'Data refresh completed successfully',
                'items_processed': result['items_processed'],
                'items_updated': result['items_updated'],
                'price_snapshots_created': result.get('snapshots_created', 0),
                'profit_calculations_updated': result.get('calculations_updated', 0),
                'refresh_time': timezone.now().isoformat(),
                'operation_id': sync_op.id
            })
            
        except Exception as e:
            logger.error(f"❌ Manual refresh failed: {e}")
            sync_op.mark_failed(str(e))
            
            return Response({
                'success': False,
                'error': f'Data refresh failed: {str(e)}',
                'operation_id': sync_op.id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"❌ Manual refresh request failed: {e}")
        return Response({
            'success': False,
            'error': f'Request failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def data_freshness_status(request):
    """
    Get current data freshness status and recommendations.
    
    Returns information about:
    - Age of newest price data
    - Items needing refresh based on volume
    - Overall data quality score
    - Recommended refresh actions
    """
    try:
        # Get newest price data age
        newest_calculation = ProfitCalculation.objects.order_by('-last_updated').first()
        data_age_hours = None
        data_status = 'unknown'
        
        if newest_calculation:
            data_age_hours = (timezone.now() - newest_calculation.last_updated).total_seconds() / 3600
            
            if data_age_hours < 0.25:  # 15 minutes
                data_status = 'fresh'
            elif data_age_hours < 1:   # 1 hour
                data_status = 'recent'  
            elif data_age_hours < 6:   # 6 hours
                data_status = 'stale'
            else:
                data_status = 'very_stale'
        
        # Count items needing refresh based on volume/profit
        hot_items_needing_refresh = _get_hot_items_needing_refresh()
        
        # Get system state
        system_state = SystemState.get_current_state()
        quality_score = system_state.calculate_data_quality_score()
        
        # Determine recommended actions
        recommendations = []
        if data_age_hours is None:
            recommendations.append('no_data_available')
        elif data_age_hours > 1:
            recommendations.append('full_refresh_needed')
        elif hot_items_needing_refresh.count() > 0:
            recommendations.append('hot_items_refresh_needed')
        
        return Response({
            'data_age_hours': round(data_age_hours, 2) if data_age_hours else None,
            'data_status': data_status,
            'quality_score': quality_score,
            'hot_items_needing_refresh': hot_items_needing_refresh.count(),
            'total_items_tracked': Item.objects.filter(is_active=True).count(),
            'total_calculations': ProfitCalculation.objects.count(),
            'recommendations': recommendations,
            'last_refresh': newest_calculation.created_at.isoformat() if newest_calculation else None,
            'sync_in_progress': system_state.sync_in_progress,
            'last_sync_success': system_state.last_full_sync.isoformat() if system_state.last_full_sync else None
        })
        
    except Exception as e:
        logger.error(f"❌ Data freshness status failed: {e}")
        return Response({
            'error': f'Status check failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _perform_data_refresh(sync_op, force_refresh=False, hot_items_only=False):
    """
    Perform data refresh using multi-source price intelligence.
    
    Args:
        sync_op: SyncOperation instance to track progress
        force_refresh: If True, refresh all data regardless of age
        hot_items_only: If True, only refresh high-volume/high-profit items
    
    Returns:
        dict: Results with counts of processed/updated items
    """
    import asyncio
    
    items_processed = 0
    items_updated = 0
    snapshots_created = 0
    calculations_updated = 0
    
    try:
        # Get items to refresh
        if hot_items_only:
            items_to_refresh = _get_hot_items_needing_refresh()
            logger.info(f"🔥 Refreshing {items_to_refresh.count()} hot items using multi-source intelligence")
        elif force_refresh:
            items_to_refresh = Item.objects.filter(is_active=True)
            logger.info(f"⚡ Force refreshing all {items_to_refresh.count()} items using multi-source intelligence")
        else:
            # Refresh items with stale data (>1 hour old)
            one_hour_ago = timezone.now() - timedelta(hours=1)
            items_to_refresh = Item.objects.filter(
                is_active=True,
                profit_calc__last_updated__lt=one_hour_ago
            ).distinct()
            logger.info(f"🔄 Refreshing {items_to_refresh.count()} items with stale data using multi-source intelligence")
        
        # Get item IDs
        item_ids = list(items_to_refresh.values_list('item_id', flat=True))
        items_processed = len(item_ids)
        
        # Use multi-source client to fetch best prices
        async def fetch_multi_source_prices():
            # async with MultiSourcePriceClient() as client:  # Temporarily disabled
                return await client.get_multiple_best_prices(
                    item_ids,
                    max_staleness_hours=24.0  # Accept data up to 24h old for manual refresh
                )
        
        # Run async fetch
        logger.info("🔄 Fetching best prices from multiple sources...")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            price_data_map = loop.run_until_complete(fetch_multi_source_prices())
            loop.close()
        except Exception as e:
            logger.error(f"Failed to fetch multi-source prices: {e}")
            raise
        
        logger.info(f"📊 Received price data for {len(price_data_map)} items from multi-source intelligence")
        
        # Process each item with transaction
        with transaction.atomic():
            for item in items_to_refresh:
                if item.item_id not in price_data_map:
                    logger.debug(f"No price data available for item {item.item_id}")
                    continue
                
                try:
                    price_data = price_data_map[item.item_id]
                    
                    # Create or update price snapshot with multi-source metadata
                    snapshot_created = _create_or_update_multi_source_price_snapshot(item, price_data)
                    if snapshot_created:
                        snapshots_created += 1
                    
                    # Update profit calculation with enhanced data
                    calculation_updated = _update_multi_source_profit_calculation(item, price_data)
                    if calculation_updated:
                        calculations_updated += 1
                        items_updated += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to update data for item {item.item_id}: {e}")
                    continue
    
        # Mark sync operation as completed
        sync_op.mark_completed(
            items_processed=items_processed,
            items_updated=items_updated
        )
        
        logger.info(f"✅ Multi-source data refresh completed: {items_updated}/{items_processed} items updated")
        
        return {
            'items_processed': items_processed,
            'items_updated': items_updated,
            'snapshots_created': snapshots_created,
            'calculations_updated': calculations_updated
        }
        
    except Exception as e:
        logger.error(f"❌ Multi-source data refresh failed: {e}")
        sync_op.mark_failed(str(e))
        raise


def _get_hot_items_needing_refresh():
    """
    Get items that are considered "hot" and need frequent refresh.
    
    Hot items are defined as:
    - High profit (>500 GP per item)
    - OR high volume (daily_volume > 1000)
    - OR high recommendation score (>0.7)
    - AND data older than 5 minutes
    """
    five_minutes_ago = timezone.now() - timedelta(minutes=5)
    
    return Item.objects.filter(
        is_active=True,
        profit_calc__last_updated__lt=five_minutes_ago
    ).filter(
        models.Q(profit_calc__current_profit__gt=500) |
        models.Q(profit_calc__daily_volume__gt=1000) |
        models.Q(profit_calc__recommendation_score__gt=0.7)
    ).distinct()


def _create_or_update_multi_source_price_snapshot(item, price_data):
    """
    Create or update price snapshot for an item using multi-source price data.
    
    Args:
        item: Item instance
        price_data: PriceData object from multi-source client
    
    Returns True if a new snapshot was created, False if updated.
    """
    # Get the most recent snapshot for this item
    latest_snapshot = PriceSnapshot.objects.filter(item=item).order_by('-created_at').first()
    
    if latest_snapshot:
        # Update the existing latest snapshot with multi-source data
        latest_snapshot.high_price = price_data.high_price
        latest_snapshot.low_price = price_data.low_price
        latest_snapshot.high_price_volume = price_data.volume_high
        latest_snapshot.low_price_volume = price_data.volume_low
        latest_snapshot.created_at = timezone.now()
        latest_snapshot.save()
        return False
    else:
        # Create new snapshot with multi-source data
        PriceSnapshot.objects.create(
            item=item,
            high_price=price_data.high_price,
            low_price=price_data.low_price,
            high_price_volume=price_data.volume_high,
            low_price_volume=price_data.volume_low,
            created_at=timezone.now()
        )
        return True

def _create_or_update_price_snapshot(item, price_data):
    """
    Legacy function: Create or update price snapshot for an item.
    
    Returns True if a new snapshot was created, False if updated.
    """
    # Get the most recent snapshot for this item
    latest_snapshot = PriceSnapshot.objects.filter(item=item).order_by('-created_at').first()
    
    if latest_snapshot:
        # Update the existing latest snapshot
        latest_snapshot.high_price = price_data.get('high', latest_snapshot.high_price)
        latest_snapshot.low_price = price_data.get('low', latest_snapshot.low_price)
        latest_snapshot.high_price_volume = price_data.get('highVolume', latest_snapshot.high_price_volume)
        latest_snapshot.low_price_volume = price_data.get('lowVolume', latest_snapshot.low_price_volume)
        latest_snapshot.created_at = timezone.now()
        latest_snapshot.save()
        return False
    else:
        # Create new snapshot if none exists
        PriceSnapshot.objects.create(
            item=item,
            high_price=price_data.get('high'),
            low_price=price_data.get('low'),
            high_price_volume=price_data.get('highVolume'),
            low_price_volume=price_data.get('lowVolume'),
            created_at=timezone.now()
        )
        return True


def _update_multi_source_profit_calculation(item, price_data):
    """
    Update or create profit calculation using multi-source price data.
    
    Args:
        item: Item instance
        price_data: PriceData object from multi-source client
    
    Returns True if calculation was updated/created.
    """
    buy_price = price_data.low_price   # instant-buy price
    sell_price = price_data.high_price # instant-sell price
    nature_rune_cost = 180
    
    if buy_price <= 0:
        return False
    
    # Calculate high alch profit: alch_value - buy_price - nature_rune_cost
    profit_per_item = max(0, item.high_alch - buy_price - nature_rune_cost)
    profit_margin = (profit_per_item / buy_price * 100) if buy_price > 0 else 0
    
    # Calculate volumes from multi-source data
    daily_volume = max(price_data.volume_high, price_data.volume_low)
    
    # Enhanced recommendation score using multi-source intelligence
    recommendation_score = _calculate_multi_source_recommendation_score(
        profit_per_item, profit_margin, price_data
    )
    
    # Create or update profit calculation with multi-source metadata
    profit_calc, created = ProfitCalculation.objects.update_or_create(
        item=item,
        defaults={
            'current_buy_price': buy_price,
            'current_sell_price': sell_price,
            'current_profit': profit_per_item,
            'current_profit_margin': profit_margin,
            'daily_volume': daily_volume,
            'hourly_volume': daily_volume // 24 if daily_volume > 0 else 0,
            'five_min_volume': daily_volume // 288 if daily_volume > 0 else 0,
            'recommendation_score': recommendation_score,
            'volume_weighted_score': recommendation_score * (daily_volume / 10000) if daily_volume > 0 else recommendation_score,
            'price_trend': 'stable',  # Could be enhanced with trend analysis
            'volume_category': _get_volume_category(daily_volume),
            'price_volatility': 0.3,  # Could be calculated from historical data
            'price_momentum': 0.0,
            # Multi-source metadata
            'data_source': price_data.source.value,
            'data_quality': price_data.quality.value,
            'confidence_score': price_data.confidence_score,
            'data_age_hours': price_data.age_hours,
            'source_timestamp': timezone.make_aware(
                timezone.datetime.fromtimestamp(price_data.timestamp)
            ) if price_data.timestamp > 0 else None,
            'last_updated': timezone.now()
        }
    )
    
    return True

def _calculate_multi_source_recommendation_score(profit: int, margin: float, price_data) -> float:
    """Calculate enhanced recommendation score using multi-source intelligence."""
    base_score = 0.5
    
    # Profit bonus (normalize to 0-0.3 range)
    profit_bonus = min(profit / 10000, 0.3) if profit > 0 else -0.2
    
    # Margin bonus (normalize to 0-0.2 range)
    margin_bonus = min(margin / 50, 0.2) if margin > 0 else -0.1
    
    # Data quality bonus from multi-source intelligence
    quality_bonus = {
        'fresh': 0.15,
        'recent': 0.1, 
        'acceptable': 0.05,
        'stale': -0.1,
        'unknown': -0.2
    }.get(price_data.quality.value, 0)
    
    # Confidence bonus from source reliability
    confidence_bonus = (price_data.confidence_score - 0.5) * 0.2
    
    # Volume bonus (items with good volume data are more reliable)
    volume_bonus = 0.1 if (price_data.volume_high > 10 or price_data.volume_low > 10) else 0
    
    # Age penalty (fresher data gets higher score)
    age_penalty = min(price_data.age_hours / 24, 1) * -0.1
    
    total_score = (base_score + profit_bonus + margin_bonus + 
                  quality_bonus + confidence_bonus + volume_bonus + age_penalty)
    
    return max(0.0, min(1.0, total_score))

def _update_profit_calculation(item, price_data):
    """
    Legacy function: Update or create profit calculation for an item.
    
    Returns True if calculation was updated/created.
    """
    high_price = price_data.get('high', 0) or 0
    low_price = price_data.get('low', 0) or 0
    
    # Use the buy price (low) for profit calculation
    buy_price = low_price if low_price > 0 else high_price
    
    if buy_price <= 0:
        return False
    
    # Calculate profit (high alch value - buy price)
    profit_per_item = max(0, item.high_alch - buy_price)
    profit_margin = (profit_per_item / buy_price * 100) if buy_price > 0 else 0
    
    # Calculate volumes
    daily_volume = (price_data.get('highVolume', 0) or 0) + (price_data.get('lowVolume', 0) or 0)
    
    # Simple recommendation score based on profit and margin
    recommendation_score = min(1.0, (profit_per_item / 1000) * (profit_margin / 50))
    
    # Create or update profit calculation
    profit_calc, created = ProfitCalculation.objects.update_or_create(
        item=item,
        defaults={
            'current_buy_price': buy_price,
            'current_sell_price': item.high_alch,  # High alch is the sell price
            'current_profit': profit_per_item,
            'current_profit_margin': profit_margin,
            'daily_volume': daily_volume,
            'hourly_volume': daily_volume // 24 if daily_volume > 0 else 0,
            'five_min_volume': daily_volume // 288 if daily_volume > 0 else 0,  # 24*60/5
            'recommendation_score': recommendation_score,
            'volume_weighted_score': recommendation_score * (daily_volume / 10000) if daily_volume > 0 else recommendation_score,
            'price_trend': 'stable',  # Default, could be enhanced later
            'volume_category': _get_volume_category(daily_volume),
            'price_volatility': 0.3,  # Default, could be calculated from historical data
            'price_momentum': 0.0,    # Default
            'last_updated': timezone.now()
        }
    )
    
    return True


def _get_volume_category(daily_volume):
    """Get volume category based on daily volume."""
    if daily_volume > 10000:
        return 'very_high'
    elif daily_volume > 5000:
        return 'high'
    elif daily_volume > 1000:
        return 'medium'
    elif daily_volume > 100:
        return 'low'
    else:
        return 'very_low'


