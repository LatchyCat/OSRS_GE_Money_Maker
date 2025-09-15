"""
Test Dynamic Set Analysis with Known Sets

This command tests the dynamic set analysis on a small subset of known
profitable sets to validate the system without the full data ingestion.
"""

import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.trading_strategies.services.bidirectional_analyzer import BidirectionalAnalyzer
from apps.items.models import Item

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test dynamic set analysis with known profitable sets'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--min-profit',
            type=int,
            default=1000,
            help='Minimum profit threshold in GP (default: 1000)',
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        try:
            results = asyncio.run(self._test_known_sets(options))
            self._display_results(results)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Test failed: {e}"))
            raise
    
    async def _test_known_sets(self, options) -> dict:
        """Test analysis on known profitable sets."""
        
        self.stdout.write("🧪 Testing dynamic set analysis on known sets...")
        
        # Known profitable sets with real item IDs from our database
        test_sets = [
            {
                'name': 'Adamant set',
                'set_item_id': 13012,  # Adamant set (lg) from our database
                'component_ids': [1161, 1123, 1073],  # Adamant full helm, platebody, platelegs
                'description': 'Basic adamant armor set'
            },
            {
                'name': 'Ahrim\'s armour set', 
                'set_item_id': 12881,  # From our database query
                'component_ids': [4708, 4712, 4714, 4710],  # Common Ahrim's piece IDs
                'description': 'Barrows armor set'
            },
            {
                'name': 'Black dragonhide set',
                'set_item_id': 12871,  # From our database
                'component_ids': [2503, 2497, 2491],  # Black d'hide pieces  
                'description': 'Dragonhide armor set'
            }
        ]
        
        results = {
            'sets_tested': len(test_sets),
            'total_opportunities': 0,
            'profitable_opportunities': 0,
            'top_opportunities': [],
            'analysis_time_seconds': 0
        }
        
        start_time = timezone.now()
        all_opportunities = []
        
        async with BidirectionalAnalyzer() as analyzer:
            for test_set in test_sets:
                self.stdout.write(f"   Testing: {test_set['name']}")
                
                try:
                    # Verify components exist in database
                    existing_components = []
                    for comp_id in test_set['component_ids']:
                        if await self._item_exists(comp_id):
                            existing_components.append(comp_id)
                    
                    if not existing_components:
                        self.stdout.write(f"   ⚠️  No components found for {test_set['name']}")
                        continue
                    
                    # Analyze opportunities
                    opportunities = await analyzer.analyze_set_opportunities(
                        set_name=test_set['name'],
                        set_item_id=test_set['set_item_id'],
                        component_ids=existing_components,
                        include_historical=True
                    )
                    
                    results['total_opportunities'] += len(opportunities)
                    
                    # Filter profitable opportunities
                    profitable_opps = [
                        opp for opp in opportunities 
                        if opp.expected_profit >= options['min_profit']
                    ]
                    
                    results['profitable_opportunities'] += len(profitable_opps)
                    all_opportunities.extend(profitable_opps)
                    
                    if profitable_opps:
                        best_opp = max(profitable_opps, key=lambda x: x.expected_profit)
                        self.stdout.write(
                            f"   ✅ Best: {best_opp.strategy_type} - "
                            f"{best_opp.expected_profit:,.0f} GP profit "
                            f"({best_opp.profit_margin_pct:.1f}% margin)"
                        )
                    else:
                        self.stdout.write(f"   ❌ No profitable opportunities found")
                        
                except Exception as e:
                    self.stdout.write(f"   ⚠️  Analysis failed: {e}")
        
        # Sort and store top opportunities
        all_opportunities.sort(key=lambda x: x.overall_score, reverse=True)
        results['top_opportunities'] = all_opportunities[:5]
        
        end_time = timezone.now()
        results['analysis_time_seconds'] = (end_time - start_time).total_seconds()
        
        return results
    
    async def _item_exists(self, item_id: int) -> bool:
        """Check if item exists in database."""
        try:
            def check_item():
                return Item.objects.filter(item_id=item_id).exists()
            
            return await asyncio.to_thread(check_item)
        except:
            return False
    
    def _display_results(self, results: dict):
        """Display test results."""
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("🧪 DYNAMIC SET ANALYSIS TEST RESULTS"))
        self.stdout.write("="*50)
        
        self.stdout.write(f"📊 Summary:")
        self.stdout.write(f"   • Sets tested: {results['sets_tested']}")
        self.stdout.write(f"   • Total opportunities: {results['total_opportunities']}")
        self.stdout.write(f"   • Profitable opportunities: {results['profitable_opportunities']}")
        self.stdout.write(f"   • Analysis time: {results['analysis_time_seconds']:.1f}s")
        
        if results['top_opportunities']:
            self.stdout.write(f"\n🏆 Top Opportunities Found:")
            
            for i, opp in enumerate(results['top_opportunities'], 1):
                profit_str = f"{opp.expected_profit:,.0f} GP"
                margin_str = f"{opp.profit_margin_pct:.1f}%"
                score_str = f"{opp.overall_score:.1f}"
                
                self.stdout.write(
                    f"   {i}. {opp.strategy_type.title():9} | "
                    f"{opp.set_name[:20]:<20} | "
                    f"Profit: {profit_str:>10} | "
                    f"Margin: {margin_str:>6} | "
                    f"Score: {score_str:>5}"
                )
        else:
            self.stdout.write(f"\n❌ No profitable opportunities found with current thresholds")
        
        if results['profitable_opportunities'] > 0:
            self.stdout.write(f"\n✅ Dynamic analysis system is working!")
            self.stdout.write(f"   The bidirectional analyzer successfully identified profitable opportunities.")
        else:
            self.stdout.write(f"\n⚠️  System needs tuning - no profitable opportunities found.")
            self.stdout.write(f"   This might be due to:")
            self.stdout.write(f"   • High minimum profit threshold")
            self.stdout.write(f"   • Insufficient price data in database")
            self.stdout.write(f"   • Market conditions unfavorable for test sets")
        
        self.stdout.write("\n" + "="*50)