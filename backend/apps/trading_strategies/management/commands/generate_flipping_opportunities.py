"""
Generate flipping opportunities using real market data.

This command uses the FlippingScanner to find profitable item flipping
opportunities and creates strategies for the most profitable ones.
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.trading_strategies.models import FlippingOpportunity, TradingStrategy, StrategyType
from apps.trading_strategies.services.flipping_scanner import FlippingScanner

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate flipping opportunities using real market data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing flipping opportunities before adding new ones'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without saving to database'
        )
        parser.add_argument(
            '--min-margin-gp',
            type=int,
            default=1000,
            help='Minimum margin in GP (default: 1000)'
        )
        parser.add_argument(
            '--min-margin-pct',
            type=float,
            default=5.0,
            help='Minimum margin percentage (default: 5.0)'
        )
        parser.add_argument(
            '--min-price',
            type=int,
            default=10000,
            help='Minimum item price to consider (default: 10000)'
        )
        parser.add_argument(
            '--max-price',
            type=int,
            default=100000000,
            help='Maximum item price to consider (default: 100000000)'
        )

    def handle(self, *args, **options):
        self.clear_existing = options['clear_existing']
        self.dry_run = options['dry_run']
        self.min_margin_gp = options['min_margin_gp']
        self.min_margin_pct = options['min_margin_pct']
        self.min_price = options['min_price']
        self.max_price = options['max_price']
        
        self.stdout.write(
            self.style.SUCCESS('💰 Generating flipping opportunities with real market data...')
        )
        
        if self.clear_existing:
            if not self.dry_run:
                self.stdout.write('🧹 Clearing existing flipping opportunities...')
                with transaction.atomic():
                    # Delete flipping opportunities and their strategies
                    flipping_strategies = TradingStrategy.objects.filter(strategy_type=StrategyType.FLIPPING)
                    flipping_count = flipping_strategies.count()
                    flipping_strategies.delete()
                    self.stdout.write(f'   Deleted {flipping_count} existing flipping strategies')
            else:
                self.stdout.write('🔍 DRY RUN: Would clear existing flipping opportunities')
        
        try:
            # Initialize scanner with custom parameters
            scanner = FlippingScanner(
                min_margin_gp=self.min_margin_gp,
                min_margin_pct=self.min_margin_pct,
                min_price=self.min_price,
                max_price=self.max_price
            )
            
            self.stdout.write(f'📊 Scanning for opportunities with parameters:')
            self.stdout.write(f'   Min margin: {self.min_margin_gp:,} GP ({self.min_margin_pct}%)')
            self.stdout.write(f'   Price range: {self.min_price:,} - {self.max_price:,} GP')
            
            if self.dry_run:
                # Just scan for opportunities without creating them
                self.stdout.write('🔍 DRY RUN: Scanning for opportunities...')
                opportunities = scanner.scan_flipping_opportunities()
                
                self.stdout.write(f'📈 Found {len(opportunities)} profitable opportunities:')
                
                for i, opp in enumerate(opportunities[:20], 1):  # Show top 20
                    self.stdout.write(
                        f'   {i:2d}. {opp["item_name"]:<25} '
                        f'Buy: {opp["buy_price"]:>8,} GP  '
                        f'Sell: {opp["sell_price"]:>8,} GP  '
                        f'Margin: {opp["margin"]:>6,} GP ({opp["margin_percentage"]:>5.1f}%)  '
                        f'Qty: {opp["recommended_quantity"]:>3} items'
                    )
                
                if len(opportunities) > 20:
                    self.stdout.write(f'   ... and {len(opportunities) - 20} more opportunities')
                
                self.stdout.write('🔍 DRY RUN: No data was saved to database')
                
            else:
                # Create opportunities for real
                self.stdout.write('💾 Creating flipping opportunities...')
                created_count = scanner.scan_and_create_opportunities()
                
                if created_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Successfully created {created_count} flipping opportunities!')
                    )
                    
                    # Show summary of created opportunities
                    recent_opportunities = FlippingOpportunity.objects.select_related('strategy').order_by('-margin_percentage')[:10]
                    
                    self.stdout.write('📈 Top 10 created opportunities:')
                    for i, opp in enumerate(recent_opportunities, 1):
                        self.stdout.write(
                            f'   {i:2d}. {opp.item_name:<25} '
                            f'Buy: {opp.buy_price:>8,} GP  '
                            f'Sell: {opp.sell_price:>8,} GP  '
                            f'Margin: {opp.margin:>6,} GP ({float(opp.margin_percentage):>5.1f}%)  '
                            f'Risk: {opp.strategy.risk_level}'
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠️  No profitable flipping opportunities found with current parameters')
                    )
                    self.stdout.write('💡 Try adjusting parameters:')
                    self.stdout.write('   - Lower --min-margin-gp or --min-margin-pct')
                    self.stdout.write('   - Adjust --min-price or --max-price range')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error generating flipping opportunities: {str(e)}')
            )
            logger.exception("Error in generate_flipping_opportunities command")
            raise
        
        self.stdout.write(
            self.style.SUCCESS('🎯 Flipping opportunity generation complete!')
        )