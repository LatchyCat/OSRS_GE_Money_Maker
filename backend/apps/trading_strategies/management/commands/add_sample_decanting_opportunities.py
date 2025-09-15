"""
Add sample decanting opportunities for high-value potions.

This command creates realistic decanting opportunities for Prayer potions,
Divine potions, and other high-value families that users expect to see.
"""

import logging
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.trading_strategies.models import DecantingOpportunity, TradingStrategy

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Add sample decanting opportunities for high-value potions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing opportunities before adding new ones'
        )

    def handle(self, *args, **options):
        self.clear_existing = options['clear_existing']
        
        self.stdout.write(
            self.style.SUCCESS('🧪 Adding sample decanting opportunities...')
        )
        
        if self.clear_existing:
            self.stdout.write('🧹 Clearing existing opportunities...')
            DecantingOpportunity.objects.all().delete()
        
        # Create sample opportunities with realistic data
        opportunities = [
            # Prayer potions (high demand)
            {
                'name': 'Prayer potion (4→1)',
                'item_id': 143,  # Prayer potion(1)
                'from_dose': 4, 'to_dose': 1,
                'from_price': 8200, 'to_price': 2950,
                'profit_per_conversion': 3600,
                'family': 'Prayer'
            },
            {
                'name': 'Prayer potion (4→2)',
                'item_id': 141,  # Prayer potion(2)
                'from_dose': 4, 'to_dose': 2,
                'from_price': 8200, 'to_price': 4800,
                'profit_per_conversion': 1400,
                'family': 'Prayer'
            },
            {
                'name': 'Prayer potion (3→1)',
                'item_id': 143,  # Prayer potion(1)
                'from_dose': 3, 'to_dose': 1,
                'from_price': 6500, 'to_price': 2950,
                'profit_per_conversion': 2350,
                'family': 'Prayer'
            },
            
            # Divine super combat (very high value)
            {
                'name': 'Divine super combat potion (4→1)',
                'item_id': 23694,  # Divine super combat potion(1)
                'from_dose': 4, 'to_dose': 1,
                'from_price': 26000, 'to_price': 7500,
                'profit_per_conversion': 4000,
                'family': 'Divine Combat'
            },
            {
                'name': 'Divine super combat potion (4→2)',
                'item_id': 23691,  # Divine super combat potion(2)
                'from_dose': 4, 'to_dose': 2,
                'from_price': 26000, 'to_price': 14500,
                'profit_per_conversion': 3000,
                'family': 'Divine Combat'
            },
            
            # Divine bastion (high value)
            {
                'name': 'Divine bastion potion (4→1)',
                'item_id': 24644,  # Divine bastion potion(1)
                'from_dose': 4, 'to_dose': 1,
                'from_price': 18500, 'to_price': 5200,
                'profit_per_conversion': 2300,
                'family': 'Divine Bastion'
            },
            {
                'name': 'Divine bastion potion (3→1)',
                'item_id': 24644,  # Divine bastion potion(1)
                'from_dose': 3, 'to_dose': 1,
                'from_price': 14200, 'to_price': 5200,
                'profit_per_conversion': 1400,
                'family': 'Divine Bastion'
            },
            
            # Divine battlemage (high value)
            {
                'name': 'Divine battlemage potion (4→1)',
                'item_id': 24632,  # Divine battlemage potion(1)
                'from_dose': 4, 'to_dose': 1,
                'from_price': 17800, 'to_price': 4900,
                'profit_per_conversion': 2300,
                'family': 'Divine Battlemage'
            },
            
            # Super restore (popular)
            {
                'name': 'Super restore (4→1)',
                'item_id': 3026,  # Super restore(1) - estimated ID
                'from_dose': 4, 'to_dose': 1,
                'from_price': 11500, 'to_price': 3200,
                'profit_per_conversion': 1300,
                'family': 'Super Restore'
            },
            {
                'name': 'Super restore (4→2)',
                'item_id': 3024,  # Super restore(2) - estimated ID
                'from_dose': 4, 'to_dose': 2,
                'from_price': 11500, 'to_price': 6100,
                'profit_per_conversion': 700,
                'family': 'Super Restore'
            },
            
            # Stamina potions (popular)
            {
                'name': 'Stamina potion (4→1)',
                'item_id': 12628,  # Stamina potion(1) - estimated ID
                'from_dose': 4, 'to_dose': 1,
                'from_price': 3200, 'to_price': 1100,
                'profit_per_conversion': 200,
                'family': 'Stamina'
            },
            
            # Saradomin brew (useful)
            {
                'name': 'Saradomin brew (4→1)',
                'item_id': 6686,  # Saradomin brew(1) - estimated ID
                'from_dose': 4, 'to_dose': 1,
                'from_price': 4800, 'to_price': 1400,
                'profit_per_conversion': 800,
                'family': 'Saradomin Brew'
            },
            
            # Super combat potion (common)
            {
                'name': 'Super combat potion (4→1)',
                'item_id': 12698,  # Super combat potion(1) - estimated ID  
                'from_dose': 4, 'to_dose': 1,
                'from_price': 13200, 'to_price': 3600,
                'profit_per_conversion': 1200,
                'family': 'Super Combat'
            },
            
            # Anti-venom+ (useful for bossing)
            {
                'name': 'Anti-venom+ (4→1)',
                'item_id': 5958,  # Anti-venom+(1) - estimated ID
                'from_dose': 4, 'to_dose': 1,
                'from_price': 8200, 'to_price': 2300,
                'profit_per_conversion': 1000,
                'family': 'Anti-venom+'
            },
        ]
        
        saved_count = 0
        
        with transaction.atomic():
            # Create a default strategy for comprehensive decanting
            strategy, created = TradingStrategy.objects.get_or_create(
                name="High-Value Decanting Opportunities",
                defaults={
                    'strategy_type': 'decanting',
                    'description': 'Curated high-value decanting opportunities for Prayer, Divine, and other valuable potions',
                    'potential_profit_gp': 2500,
                    'profit_margin_pct': Decimal('25.00'),
                    'risk_level': 'low',
                    'min_capital_required': 5000,
                    'recommended_capital': 50000,
                    'optimal_market_condition': 'stable',
                    'estimated_time_minutes': 1,
                    'confidence_score': Decimal('0.85'),
                    'is_active': True,
                }
            )
            
            for opp_data in opportunities:
                try:
                    # Calculate metrics
                    profit_per_hour = opp_data['profit_per_conversion'] * 800  # Conservative rate
                    
                    opportunity = DecantingOpportunity.objects.create(
                        strategy=strategy,
                        item_id=opp_data['item_id'],
                        item_name=opp_data['name'],
                        from_dose=opp_data['from_dose'],
                        to_dose=opp_data['to_dose'],
                        from_dose_price=opp_data['from_price'],
                        to_dose_price=opp_data['to_price'],
                        from_dose_volume=150,  # Decent volume
                        to_dose_volume=80,     # Lower volume for individual doses
                        profit_per_conversion=opp_data['profit_per_conversion'],
                        profit_per_hour=profit_per_hour,
                    )
                    saved_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to create opportunity {opp_data['name']}: {e}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Successfully added {saved_count} high-value decanting opportunities!'
            )
        )
        
        # Show summary of what was added
        families = {}
        for opp in opportunities[:saved_count]:
            family = opp['family']
            if family not in families:
                families[family] = 0
            families[family] += 1
        
        self.stdout.write('\n📊 Added opportunities by family:')
        for family, count in families.items():
            self.stdout.write(f'  • {family}: {count} opportunities')