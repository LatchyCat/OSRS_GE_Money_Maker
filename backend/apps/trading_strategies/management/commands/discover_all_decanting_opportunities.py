"""
Comprehensive Decanting Opportunity Discovery Command

Scans all potions in the database, groups them by potion families,
and generates decanting opportunities for all profitable combinations.
"""

import logging
import re
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Tuple, Optional

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.items.models import Item
from apps.trading_strategies.models import DecantingOpportunity, TradingStrategy
from services.runescape_wiki_client import RuneScapeWikiAPIClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Discover and generate comprehensive decanting opportunities for all potion families'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-profit',
            type=int,
            default=10,
            help='Minimum profit in GP to consider (default: 10)'
        )
        parser.add_argument(
            '--max-opportunities',
            type=int,
            default=100,
            help='Maximum opportunities to generate (default: 100)'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing opportunities before generating new ones'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without saving to database'
        )
        parser.add_argument(
            '--families-only',
            nargs='+',
            help='Generate only for specific potion families (e.g. "Prayer potion" "Divine")'
        )

    def handle(self, *args, **options):
        self.min_profit = options['min_profit']
        self.max_opportunities = options['max_opportunities']
        self.clear_existing = options['clear_existing']
        self.dry_run = options['dry_run']
        self.families_only = options.get('families_only', [])
        
        self.wiki_client = RuneScapeWikiAPIClient()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🔍 Starting comprehensive decanting opportunity discovery...'
            )
        )
        
        try:
            # Step 1: Discover potion families
            potion_families = self.discover_potion_families()
            self.stdout.write(f'📋 Found {len(potion_families)} potion families')
            
            # Step 2: Generate opportunities
            opportunities = self.generate_opportunities(potion_families)
            self.stdout.write(f'💡 Generated {len(opportunities)} potential opportunities')
            
            # Step 3: Save to database
            if not self.dry_run:
                saved_count = self.save_opportunities(opportunities)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Successfully saved {saved_count} decanting opportunities!'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING('🔍 DRY RUN - No opportunities saved to database')
                )
                for opp in opportunities[:10]:  # Show first 10 as preview
                    self.stdout.write(
                        f'  • {opp["name"]}: {opp["from_dose"]}→{opp["to_dose"]} '
                        f'(Profit: {opp["profit_per_conversion"]} GP)'
                    )
                    
        except Exception as e:
            logger.exception("Error in decanting discovery")
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            )

    def discover_potion_families(self) -> Dict[str, List[Item]]:
        """Discover and group potions by family."""
        self.stdout.write('🔍 Discovering potion families...')
        
        # Get all potion items
        potion_items = Item.objects.filter(
            name__icontains='potion'
        ).union(
            Item.objects.filter(name__iregex=r'.*\([1-4]\)$')
        ).order_by('name')
        
        families = defaultdict(list)
        dose_pattern = re.compile(r'^(.+?)\(([1-4])\)$')
        
        for item in potion_items:
            match = dose_pattern.match(item.name)
            if match:
                base_name = match.group(1).strip()
                dose = int(match.group(2))
                
                # Filter by specific families if requested
                if self.families_only:
                    if not any(family.lower() in base_name.lower() for family in self.families_only):
                        continue
                
                families[base_name].append({
                    'item': item,
                    'dose': dose,
                    'name': item.name
                })
        
        # Sort each family by dose and filter to families with multiple doses
        filtered_families = {}
        for family_name, items in families.items():
            if len(items) >= 2:  # Need at least 2 doses for decanting
                items.sort(key=lambda x: x['dose'])
                filtered_families[family_name] = items
                self.stdout.write(
                    f'  • {family_name}: {len(items)} doses '
                    f'({", ".join(str(item["dose"]) for item in items)})'
                )
        
        return filtered_families

    def generate_opportunities(self, potion_families: Dict[str, List]) -> List[Dict]:
        """Generate decanting opportunities for all families."""
        self.stdout.write('💡 Generating decanting opportunities...')
        
        opportunities = []
        
        for family_name, items in potion_families.items():
            family_opportunities = self.generate_family_opportunities(family_name, items)
            opportunities.extend(family_opportunities)
            
            if len(opportunities) >= self.max_opportunities:
                self.stdout.write(f'⚠️  Reached maximum opportunities limit ({self.max_opportunities})')
                break
        
        # Sort by profit descending
        opportunities.sort(key=lambda x: x['profit_per_conversion'], reverse=True)
        return opportunities[:self.max_opportunities]

    def generate_family_opportunities(self, family_name: str, items: List) -> List[Dict]:
        """Generate opportunities for a single potion family."""
        opportunities = []
        
        # Generate all possible dose combinations
        for i, higher_dose_item in enumerate(items):
            for j, lower_dose_item in enumerate(items):
                if higher_dose_item['dose'] > lower_dose_item['dose']:
                    opportunity = self.calculate_opportunity(
                        family_name,
                        higher_dose_item,
                        lower_dose_item
                    )
                    
                    if opportunity and opportunity['profit_per_conversion'] >= self.min_profit:
                        opportunities.append(opportunity)
        
        return opportunities

    def calculate_opportunity(self, family_name: str, from_item: Dict, to_item: Dict) -> Optional[Dict]:
        """Calculate a single decanting opportunity."""
        try:
            # Get current prices from RuneScape Wiki
            from_price = self.get_item_price(from_item['item'].id)
            to_price = self.get_item_price(to_item['item'].id)
            
            if not from_price or not to_price:
                return None
            
            # Calculate decanting mathematics
            from_dose = from_item['dose']
            to_dose = to_item['dose']
            doses_per_conversion = from_dose // to_dose
            
            # Calculate profit (proper OSRS mechanics)
            cost_per_conversion = from_price
            revenue_per_conversion = to_price * doses_per_conversion
            profit_per_conversion = revenue_per_conversion - cost_per_conversion
            
            # Skip if not profitable
            if profit_per_conversion <= 0:
                return None
            
            # Calculate additional metrics
            profit_margin = (profit_per_conversion / cost_per_conversion) * 100
            profit_per_hour = profit_per_conversion * 1000  # Assume 1000 conversions/hour
            roi_percentage = (profit_per_conversion / cost_per_conversion) * 100
            
            return {
                'family_name': family_name,
                'name': f"{family_name} ({from_dose}→{to_dose})",
                'item_id': to_item['item'].id,  # Use target item as primary
                'from_dose': from_dose,
                'to_dose': to_dose,
                'from_dose_price': from_price,
                'to_dose_price': to_price,
                'profit_per_conversion': profit_per_conversion,
                'profit_per_hour': profit_per_hour,
                'roi_percentage': roi_percentage,
                'profit_margin': profit_margin,
                'from_item': from_item['item'],
                'to_item': to_item['item'],
            }
            
        except Exception as e:
            logger.warning(f"Error calculating opportunity for {family_name}: {e}")
            return None

    def get_item_price(self, item_id: int) -> Optional[int]:
        """Get current price for an item from RuneScape Wiki API."""
        try:
            # Use the async method to get price data
            import asyncio
            
            # Create async wrapper for price fetching
            async def fetch_price():
                try:
                    async with self.wiki_client:
                        price_data_dict = await self.wiki_client.get_latest_prices(item_id)
                        if item_id in price_data_dict:
                            price_data = price_data_dict[item_id]
                            if price_data.has_valid_prices:
                                # Use best_buy_price which prefers high price
                                return price_data.best_buy_price
                    return None
                except Exception as e:
                    logger.warning(f"Failed to get price for item {item_id}: {e}")
                    return None
            
            # Run the async function synchronously
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're already in an event loop, need to use a different approach
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, fetch_price())
                        return future.result(timeout=30)
                else:
                    return loop.run_until_complete(fetch_price())
            except RuntimeError:
                # No event loop, create a new one
                return asyncio.run(fetch_price())
                
        except Exception as e:
            logger.warning(f"Failed to get price for item {item_id}: {e}")
            return None

    def save_opportunities(self, opportunities: List[Dict]) -> int:
        """Save opportunities to database."""
        if self.clear_existing:
            self.stdout.write('🧹 Clearing existing opportunities...')
            DecantingOpportunity.objects.all().delete()
        
        self.stdout.write('💾 Saving opportunities to database...')
        saved_count = 0
        
        with transaction.atomic():
            # Create a default strategy for all decanting opportunities
            strategy, created = TradingStrategy.objects.get_or_create(
                name="Comprehensive Decanting Analysis",
                defaults={
                    'strategy_type': 'decanting',
                    'description': 'Auto-generated comprehensive decanting opportunities',
                    'potential_profit_gp': 0,  # Will be updated
                    'profit_margin_pct': Decimal('0.00'),
                    'risk_level': 'low',
                    'min_capital_required': 1000,
                    'recommended_capital': 10000,
                    'optimal_market_condition': 'stable',
                    'estimated_time_minutes': 1,
                    'confidence_score': Decimal('0.80'),
                    'is_active': True,
                }
            )
            
            for opp_data in opportunities:
                try:
                    opportunity = DecantingOpportunity.objects.create(
                        strategy=strategy,
                        item_id=opp_data['item_id'],
                        item_name=opp_data['name'],
                        from_dose=opp_data['from_dose'],
                        to_dose=opp_data['to_dose'],
                        from_dose_price=opp_data['from_dose_price'],
                        to_dose_price=opp_data['to_dose_price'],
                        from_dose_volume=100,  # Default volume
                        to_dose_volume=50,     # Default volume
                        profit_per_conversion=opp_data['profit_per_conversion'],
                        profit_per_hour=opp_data['profit_per_hour'],
                    )
                    saved_count += 1
                    
                    if saved_count % 10 == 0:
                        self.stdout.write(f'  📊 Saved {saved_count} opportunities...')
                        
                except Exception as e:
                    logger.warning(f"Failed to save opportunity {opp_data['name']}: {e}")
        
        return saved_count