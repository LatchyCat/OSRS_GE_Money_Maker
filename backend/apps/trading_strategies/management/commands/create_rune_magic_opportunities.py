"""
Create sample rune & magic money-making opportunities.

This command creates sample RuneMagicStrategy records with realistic
runecrafting profits, high alchemy opportunities, and magic supply data.
"""

import logging
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.trading_strategies.models import (
    TradingStrategy, 
    StrategyType,
    RuneMagicStrategy,
    MoneyMakerStrategy
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create sample rune & magic money-making opportunities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing rune magic strategies before adding new ones'
        )

    def handle(self, *args, **options):
        self.clear_existing = options['clear_existing']
        
        self.stdout.write(
            self.style.SUCCESS('🪄 Creating rune & magic opportunities...')
        )
        
        if self.clear_existing:
            self.stdout.write('🧹 Clearing existing rune magic strategies...')
            with transaction.atomic():
                # Delete rune magic strategies
                rune_strategies = TradingStrategy.objects.filter(strategy_type=StrategyType.RUNE_MAGIC)
                rune_count = rune_strategies.count()
                rune_strategies.delete()
                self.stdout.write(f'   Deleted {rune_count} existing rune magic strategies')
        
        try:
            created_count = self.create_rune_magic_opportunities()
            
            if created_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully created {created_count} rune & magic opportunities!')
                )
                
                # Show summary
                recent_strategies = RuneMagicStrategy.objects.select_related('money_maker__strategy').all()[:5]
                
                self.stdout.write('🔮 Created strategies:')
                for strategy in recent_strategies:
                    rune_count = len(strategy.target_runes) if strategy.target_runes else 0
                    supply_count = len(strategy.magic_supplies) if strategy.magic_supplies else 0
                    self.stdout.write(
                        f'   • {strategy.money_maker.strategy.name}: '
                        f'{rune_count} runes, {supply_count} supplies, '
                        f'Level {strategy.runecrafting_level_required}+'
                    )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  No rune magic opportunities were created')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating rune magic opportunities: {str(e)}')
            )
            logger.exception("Error in create_rune_magic_opportunities command")
            raise
        
        self.stdout.write(
            self.style.SUCCESS('🎯 Rune & magic opportunity creation complete!')
        )

    def create_rune_magic_opportunities(self) -> int:
        """Create sample rune magic strategies with realistic data"""
        
        strategies_data = [
            {
                'name': 'Nature Rune Crafting',
                'description': 'Craft nature runes at level 44+ for consistent profits. Requires access to nature altar.',
                'runecrafting_level': 44,
                'runes_per_hour': 1800,
                'target_runes': [
                    {'type': 'Nature rune', 'profit': 45, 'level': 44}
                ],
                'magic_supplies': [
                    {'type': 'rune', 'name': 'Nature rune', 'buy_price': 135, 'sell_price': 180, 'profit': 45, 'margin_pct': 33.3, 'usage': 'High alchemy casting'}
                ],
                'capital_required': 500000,
                'hourly_profit': 81000,
                'risk_level': 'low',
                'high_alch_opportunities': [
                    {
                        'item_id': 1371,
                        'item_name': 'Dragon dagger',
                        'buy_price': 17500,
                        'alch_value': 18000,
                        'profit': 320,
                        'nature_rune_cost': 180,
                        'magic_level_required': 55,
                        'hourly_profit_potential': 384000
                    }
                ]
            },
            {
                'name': 'Law Rune Crafting',
                'description': 'Craft law runes at level 54+ with good profits. Teleport access required.',
                'runecrafting_level': 54,
                'runes_per_hour': 1500,
                'target_runes': [
                    {'type': 'Law rune', 'profit': 120, 'level': 54}
                ],
                'magic_supplies': [
                    {'type': 'rune', 'name': 'Law rune', 'buy_price': 230, 'sell_price': 350, 'profit': 120, 'margin_pct': 52.2, 'usage': 'Teleport spells'},
                    {'type': 'supply', 'name': 'Pure essence', 'buy_price': 6, 'sell_price': 8, 'profit': 2, 'margin_pct': 33.3, 'usage': 'Runecrafting material'}
                ],
                'capital_required': 1000000,
                'hourly_profit': 180000,
                'risk_level': 'medium',
                'high_alch_opportunities': [
                    {
                        'item_id': 8013,
                        'item_name': 'Camelot teleport',
                        'buy_price': 650,
                        'alch_value': 900,
                        'profit': 70,
                        'nature_rune_cost': 180,
                        'magic_level_required': 55,
                        'hourly_profit_potential': 84000
                    }
                ]
            },
            {
                'name': 'Death Rune Crafting',
                'description': 'High-level runecrafting at 65+ with excellent profits but higher requirements.',
                'runecrafting_level': 65,
                'runes_per_hour': 1200,
                'target_runes': [
                    {'type': 'Death rune', 'profit': 185, 'level': 65}
                ],
                'magic_supplies': [
                    {'type': 'rune', 'name': 'Death rune', 'buy_price': 215, 'sell_price': 400, 'profit': 185, 'margin_pct': 86.0, 'usage': 'Combat spells'}
                ],
                'capital_required': 2000000,
                'hourly_profit': 222000,
                'risk_level': 'medium'
            },
            {
                'name': 'Blood Rune Crafting',
                'description': 'Elite runecrafting method at 77+. Requires Zeah access and high capital.',
                'runecrafting_level': 77,
                'runes_per_hour': 1100,
                'target_runes': [
                    {'type': 'Blood rune', 'profit': 295, 'level': 77}
                ],
                'magic_supplies': [
                    {'type': 'rune', 'name': 'Blood rune', 'buy_price': 305, 'sell_price': 600, 'profit': 295, 'margin_pct': 96.7, 'usage': 'High-level combat magic'},
                    {'type': 'supply', 'name': 'Dark essence block', 'buy_price': 8500, 'sell_price': 8600, 'profit': 100, 'margin_pct': 1.2, 'usage': 'Blood rune crafting'}
                ],
                'capital_required': 5000000,
                'hourly_profit': 324500,
                'risk_level': 'high'
            },
            {
                'name': 'Air Battlestaff Trading',
                'description': 'Buy air battlestaffs from Zaff daily shop and resell for guaranteed profit.',
                'runecrafting_level': 1,
                'runes_per_hour': 0,
                'target_runes': [],
                'magic_supplies': [
                    {'type': 'equipment', 'name': 'Air battlestaff', 'buy_price': 7000, 'sell_price': 8800, 'profit': 1800, 'margin_pct': 25.7, 'usage': 'Magic weapon / High alchemy'},
                    {'type': 'equipment', 'name': 'Water battlestaff', 'buy_price': 7000, 'sell_price': 8700, 'profit': 1700, 'margin_pct': 24.3, 'usage': 'Magic weapon / High alchemy'},
                    {'type': 'equipment', 'name': 'Earth battlestaff', 'buy_price': 7000, 'sell_price': 8900, 'profit': 1900, 'margin_pct': 27.1, 'usage': 'Magic weapon / High alchemy'},
                    {'type': 'equipment', 'name': 'Fire battlestaff', 'buy_price': 7000, 'sell_price': 8750, 'profit': 1750, 'margin_pct': 25.0, 'usage': 'Magic weapon / High alchemy'}
                ],
                'capital_required': 100000,
                'hourly_profit': 50000,  # Daily method, lower hourly
                'risk_level': 'low'
            },
            {
                'name': 'Cosmic Rune Arbitrage',
                'description': 'Trade cosmic runes between different sources for profit margins.',
                'runecrafting_level': 27,
                'runes_per_hour': 2000,
                'target_runes': [
                    {'type': 'Cosmic rune', 'profit': 25, 'level': 27}
                ],
                'magic_supplies': [
                    {'type': 'rune', 'name': 'Cosmic rune', 'buy_price': 85, 'sell_price': 110, 'profit': 25, 'margin_pct': 29.4, 'usage': 'Enchanting spells'},
                    {'type': 'equipment', 'name': 'Cosmic tiara', 'buy_price': 1200, 'sell_price': 1400, 'profit': 200, 'margin_pct': 16.7, 'usage': 'Runecrafting equipment'}
                ],
                'capital_required': 300000,
                'hourly_profit': 50000,
                'risk_level': 'low'
            }
        ]

        created_count = 0

        for strategy_data in strategies_data:
            try:
                with transaction.atomic():
                    # Create base TradingStrategy
                    base_strategy = TradingStrategy.objects.create(
                        strategy_type=StrategyType.RUNE_MAGIC,
                        name=strategy_data['name'],
                        description=strategy_data['description'],
                        potential_profit_gp=strategy_data['hourly_profit'],
                        profit_margin_pct=Decimal('15.0'),  # Average margin
                        risk_level=strategy_data['risk_level'],
                        min_capital_required=strategy_data['capital_required'],
                        recommended_capital=strategy_data['capital_required'] * 2,
                        optimal_market_condition='stable',
                        estimated_time_minutes=60,  # Per hour
                        confidence_score=Decimal('0.8'),
                        is_active=True,
                        strategy_data={
                            'method_type': 'runecrafting' if strategy_data['target_runes'] else 'trading',
                            'level_requirement': strategy_data['runecrafting_level'],
                            'profit_source': 'runes_and_supplies'
                        }
                    )

                    # Create MoneyMakerStrategy
                    money_maker = MoneyMakerStrategy.objects.create(
                        strategy=base_strategy,
                        starting_capital=strategy_data['capital_required'],
                        current_capital=strategy_data['capital_required'],
                        target_capital=strategy_data['capital_required'] + strategy_data['hourly_profit'],
                        hourly_profit_gp=strategy_data['hourly_profit'],
                        max_capital_per_trade=strategy_data['capital_required'] // 4,  # 25% of capital per trade
                        scales_with_capital=True,
                        exploits_lazy_tax=False
                    )

                    # Create RuneMagicStrategy
                    rune_magic_strategy = RuneMagicStrategy.objects.create(
                        money_maker=money_maker,
                        target_runes=strategy_data['target_runes'],
                        magic_supplies=strategy_data['magic_supplies'],
                        runecrafting_level_required=strategy_data['runecrafting_level'],
                        runes_per_hour=strategy_data['runes_per_hour'],
                        essence_costs={
                            'pure_essence': 6,
                            'rune_essence': 4,
                            'binding_necklace': 800
                        },
                        high_alch_opportunities=strategy_data.get('high_alch_opportunities', [])
                    )

                    created_count += 1
                    
                    if created_count <= 5:  # Log first 5
                        logger.info(f"Created rune magic strategy: {strategy_data['name']}")
                        
            except Exception as e:
                logger.error(f"Error creating strategy {strategy_data['name']}: {e}")
                continue

        return created_count