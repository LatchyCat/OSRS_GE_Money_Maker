"""
Management command for refreshing decanting prices using RuneScape Wiki API.

This command should be run hourly via cron to ensure fresh price and volume data
for accurate decanting opportunity analysis with AI-powered recommendations.
"""

import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from services.decanting_price_service import decanting_price_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Refresh decanting prices from RuneScape Wiki API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force refresh even if cached data is available'
        )
        parser.add_argument(
            '--min-profit',
            type=int,
            default=50,
            help='Minimum profit in GP to consider (default: 50)'
        )
        parser.add_argument(
            '--update-db',
            action='store_true',
            help='Update DecantingOpportunity database records with fresh data'
        )

    def handle(self, *args, **options):
        """Execute the price refresh command."""
        start_time = timezone.now()
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting decanting price refresh at {start_time}')
        )
        
        try:
            # Run async refresh in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self._async_refresh(options)
            )
            
            loop.close()
            
            duration = timezone.now() - start_time
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully completed refresh in {duration.total_seconds():.2f}s'
                )
            )
            
            return result
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Price refresh failed: {str(e)}')
            )
            raise

    async def _async_refresh(self, options):
        """Perform the async price refresh operations."""
        force_refresh = options['force']
        min_profit = options['min_profit']
        update_db = options['update_db']
        
        # Step 1: Refresh potion family price data
        self.stdout.write('Refreshing potion family prices from RuneScape Wiki API...')
        
        families = await decanting_price_service.refresh_potion_prices(
            force_refresh=force_refresh
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Retrieved price data for {len(families)} potion families')
        )
        
        # Log family details
        fresh_count = sum(1 for f in families.values() if f.data_quality == "fresh")
        recent_count = sum(1 for f in families.values() if f.data_quality == "recent")
        acceptable_count = sum(1 for f in families.values() if f.data_quality == "acceptable")
        
        self.stdout.write(f'Data quality: {fresh_count} fresh, {recent_count} recent, {acceptable_count} acceptable')
        
        # Step 2: Generate decanting opportunities
        self.stdout.write(f'Analyzing decanting opportunities (min profit: {min_profit} GP)...')
        
        opportunities = await decanting_price_service.get_decanting_opportunities(
            min_profit_gp=min_profit
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {len(opportunities)} viable opportunities')
        )
        
        # Display top opportunities
        if opportunities:
            self.stdout.write('\nTop 10 opportunities:')
            for i, opp in enumerate(opportunities[:10], 1):
                self.stdout.write(
                    f'{i:2d}. {opp.potion_family.base_name} '
                    f'{opp.from_dose}→{opp.to_dose} doses: '
                    f'{opp.profit_per_conversion}gp profit '
                    f'({opp.profit_margin_pct:.1f}% margin, '
                    f'{opp.confidence_score:.2f} confidence)'
                )
        
        # Step 3: Update database if requested
        if update_db:
            await self._update_database(opportunities)
        
        return {
            'families_refreshed': len(families),
            'opportunities_found': len(opportunities),
            'fresh_data_count': fresh_count,
        }

    async def _update_database(self, opportunities):
        """Update DecantingOpportunity database records with fresh data."""
        self.stdout.write('Updating database with fresh opportunities...')
        
        from apps.trading_strategies.models import DecantingOpportunity, TradingStrategy
        
        # Get or create decanting strategy
        strategy, created = await asyncio.to_thread(
            TradingStrategy.objects.get_or_create,
            name='AI-Powered Decanting',
            defaults={
                'strategy_type': 'decanting',
                'description': 'AI-powered decanting opportunities using fresh RuneScape Wiki price and volume data',
                'potential_profit_gp': 500,
                'profit_margin_pct': 25.0,
                'risk_level': 'low',
                'min_capital_required': 1000,
                'recommended_capital': 10000,
                'optimal_market_condition': 'stable',
                'estimated_time_minutes': 1,
                'max_volume_per_day': 1000,
                'confidence_score': 0.85,
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write('Created new AI-powered decanting strategy')
        
        # Clear existing opportunities
        deleted_count = await asyncio.to_thread(
            DecantingOpportunity.objects.filter(strategy=strategy).delete
        )
        self.stdout.write(f'Cleared {deleted_count[0]} old opportunities')
        
        # Create new opportunities
        created_count = 0
        for opp in opportunities[:20]:  # Limit to top 20 opportunities
            try:
                await asyncio.to_thread(
                    DecantingOpportunity.objects.create,
                    strategy=strategy,
                    item_id=opp.potion_family.item_ids[opp.from_dose],
                    item_name=opp.potion_family.base_name,
                    from_dose=opp.from_dose,
                    to_dose=opp.to_dose,
                    from_dose_price=opp.from_price,
                    to_dose_price=opp.to_price,
                    from_dose_volume=opp.potion_family.volumes.get(opp.from_dose, 0),
                    to_dose_volume=opp.potion_family.volumes.get(opp.to_dose, 0),
                    profit_per_conversion=opp.profit_per_conversion,
                    profit_per_hour=opp.profit_per_conversion * opp.estimated_conversions_per_hour,
                )
                created_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f'Failed to create opportunity for {opp.potion_family.base_name}: {e}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {created_count} new opportunities in database')
        )