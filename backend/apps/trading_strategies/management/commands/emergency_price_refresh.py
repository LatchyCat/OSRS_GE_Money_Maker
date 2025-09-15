"""
Emergency price refresh command to fix stale decanting price data.

This command force-refreshes price data from RuneScape Wiki API for all items
used in decanting strategies to fix the price accuracy issues.
"""

import asyncio
import logging
from typing import Set
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.items.models import Item
from apps.prices.models import ProfitCalculation
from services.unified_wiki_price_client import UnifiedPriceClient
from apps.trading_strategies.models import DecantingOpportunity

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Emergency refresh of price data for decanting items to fix accuracy issues'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force refresh even if prices were recently updated'
        )
        parser.add_argument(
            '--items',
            type=str,
            help='Comma-separated list of specific item IDs to refresh'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING('🚨 EMERGENCY PRICE REFRESH - Fixing stale decanting prices')
        )
        
        # Get all items used in decanting opportunities
        decanting_item_ids = self._get_decanting_item_ids(options.get('items'))
        
        self.stdout.write(
            f'Found {len(decanting_item_ids)} items used in decanting strategies'
        )
        
        # Force refresh prices
        updated_count = asyncio.run(self._refresh_prices(decanting_item_ids, options.get('force', False)))
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Successfully refreshed {updated_count} item prices')
        )
        
        # Trigger decanting opportunity rescan
        self.stdout.write('🔄 Rescanning decanting opportunities with fresh prices...')
        self._rescan_decanting_opportunities()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Emergency price refresh completed!')
        )
    
    def _get_decanting_item_ids(self, specific_items: str = None) -> Set[int]:
        """Get all item IDs used in decanting strategies."""
        if specific_items:
            return set(int(x.strip()) for x in specific_items.split(','))
        
        # Get items from existing decanting opportunities
        decanting_items = set()
        
        # Add items from current decanting opportunities
        for opp in DecantingOpportunity.objects.all():
            decanting_items.add(opp.item_id)
        
        # Add known problematic items that need immediate fixing
        critical_items = {
            2432,  # Defence potion (4)
            135,   # Defence potion (1) 
            2433,  # Defence potion (3)
            2434,  # Defence potion (2)
            183,   # Superantipoison (2)
            179,   # Superantipoison (1)
            181,   # Superantipoison (3)
            185,   # Superantipoison (4)
        }
        decanting_items.update(critical_items)
        
        return decanting_items
    
    async def _refresh_prices(self, item_ids: Set[int], force: bool) -> int:
        """Refresh prices for specified items using RuneScape Wiki API."""
        updated_count = 0
        
        async with UnifiedPriceClient() as price_client:
            # Get fresh price data for all items
            self.stdout.write(f'📡 Fetching fresh prices from RuneScape Wiki API...')
            
            price_data_map = await price_client.get_multiple_comprehensive_prices(
                list(item_ids),
                max_staleness_hours=48.0  # Accept data up to 48 hours old for emergency fix
            )
            
            for item_id, price_data in price_data_map.items():
                try:
                    item = Item.objects.get(item_id=item_id)
                    profit_calc, created = ProfitCalculation.objects.get_or_create(item=item)
                    
                    # Check if we should update (force or stale data)
                    should_update = force
                    if not should_update and profit_calc.last_price_update:
                        hours_old = (timezone.now() - profit_calc.last_price_update).total_seconds() / 3600
                        should_update = hours_old > 2  # Update if older than 2 hours
                    
                    if should_update or created:
                        old_buy = profit_calc.current_buy_price
                        old_sell = profit_calc.current_sell_price
                        
                        # Update with fresh price data
                        profit_calc.update_from_multi_source_data(price_data, item)
                        
                        self.stdout.write(
                            f'  📊 {item.name} (ID {item_id}): '
                            f'Buy {old_buy}→{profit_calc.current_buy_price}gp, '
                            f'Sell {old_sell}→{profit_calc.current_sell_price}gp '
                            f'[{price_data.age_hours:.1f}h old]'
                        )
                        updated_count += 1
                    else:
                        self.stdout.write(
                            f'  ⏭️  {item.name} (ID {item_id}): Skipped (recently updated)'
                        )
                        
                except Item.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Item {item_id} not found in database')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Error updating item {item_id}: {e}')
                    )
        
        return updated_count
    
    def _rescan_decanting_opportunities(self):
        """Trigger a rescan of decanting opportunities with fresh prices."""
        try:
            from apps.trading_strategies.services.decanting_detector import DecantingDetector
            
            detector = DecantingDetector()
            opportunities = detector.scan_and_create_opportunities()
            
            self.stdout.write(
                f'🔄 Created/updated {len(opportunities)} decanting opportunities'
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error rescanning opportunities: {e}')
            )
