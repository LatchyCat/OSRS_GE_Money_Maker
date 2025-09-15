"""
Dynamic Set Trading Analysis Command

This command orchestrates the complete pipeline for discovering and analyzing
OSRS armor/weapon set trading opportunities using real Wiki API data.

Features:
- Dynamic set discovery from OSRS Wiki data
- Bidirectional analysis (combine vs decombine)
- Historical pattern analysis
- ML-powered confidence scoring
- Real-time market condition assessment
"""

import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.trading_strategies.services.dynamic_set_discovery_service import (
    DynamicSetDiscoveryService, SetConfiguration
)
from apps.trading_strategies.services.bidirectional_analyzer import (
    BidirectionalAnalyzer, TradingOpportunity
)
from apps.trading_strategies.models import TradingStrategy, SetCombiningOpportunity, StrategyType
from apps.items.models import Item

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Analyze dynamic set trading opportunities using OSRS Wiki API data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force-refresh',
            action='store_true',
            help='Force refresh of cached set discovery data',
        )
        parser.add_argument(
            '--include-historical',
            action='store_true',
            default=True,
            help='Include historical price analysis (default: True)',
        )
        parser.add_argument(
            '--min-profit',
            type=int,
            default=5000,
            help='Minimum profit threshold in GP (default: 5000)',
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.3,
            help='Minimum confidence score threshold (default: 0.3)',
        )
        parser.add_argument(
            '--max-opportunities',
            type=int,
            default=50,
            help='Maximum opportunities to create (default: 50)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform analysis without creating database records',
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true', 
            help='Clear existing dynamic opportunities before analysis',
        )
        parser.add_argument(
            '--strategy-type',
            choices=['combine', 'decombine', 'both'],
            default='both',
            help='Type of strategies to analyze (default: both)',
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        try:
            # Run the async analysis
            results = asyncio.run(self._run_analysis(options))
            
            # Display results
            self._display_results(results, options)
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Analysis interrupted by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Analysis failed: {e}"))
            raise
    
    async def _run_analysis(self, options) -> dict:
        """Run the complete dynamic set analysis pipeline."""
        
        self.stdout.write("🚀 Starting dynamic set trading analysis...")
        self.stdout.write(f"⚙️  Configuration:")
        self.stdout.write(f"   • Min profit: {options['min_profit']:,} GP")
        self.stdout.write(f"   • Min confidence: {options['min_confidence']:.2f}")
        self.stdout.write(f"   • Max opportunities: {options['max_opportunities']}")
        self.stdout.write(f"   • Strategy types: {options['strategy_type']}")
        self.stdout.write(f"   • Include historical: {options['include_historical']}")
        self.stdout.write(f"   • Dry run: {options['dry_run']}")
        
        results = {
            'sets_discovered': 0,
            'opportunities_analyzed': 0,
            'profitable_opportunities': 0,
            'strategies_created': 0,
            'top_opportunities': [],
            'analysis_time_seconds': 0,
            'errors': []
        }
        
        start_time = timezone.now()
        
        try:
            # Phase 1: Discover all armor/weapon sets
            self.stdout.write("\n📋 Phase 1: Discovering armor/weapon sets from OSRS Wiki...")
            
            async with DynamicSetDiscoveryService() as discovery_service:
                discovered_sets = await discovery_service.discover_all_sets(
                    force_refresh=options['force_refresh'],
                    include_historical=options['include_historical']
                )
                
                results['sets_discovered'] = len(discovered_sets)
                self.stdout.write(f"✅ Discovered {len(discovered_sets)} armor/weapon sets")
                
                if not discovered_sets:
                    self.stdout.write(self.style.WARNING("No sets discovered. Exiting."))
                    return results
            
            # Phase 2: Analyze bidirectional trading opportunities
            self.stdout.write("\n⚡ Phase 2: Analyzing bidirectional trading opportunities...")
            
            all_opportunities = []
            
            async with BidirectionalAnalyzer() as analyzer:
                for i, set_config in enumerate(discovered_sets, 1):
                    try:
                        self.stdout.write(f"   Analyzing {i}/{len(discovered_sets)}: {set_config.set_name}")
                        
                        opportunities = await analyzer.analyze_set_opportunities(
                            set_name=set_config.set_name,
                            set_item_id=set_config.set_item_id,
                            component_ids=set_config.component_ids,
                            include_historical=options['include_historical']
                        )
                        
                        # Filter by strategy type preference
                        if options['strategy_type'] != 'both':
                            opportunities = [
                                opp for opp in opportunities 
                                if opp.strategy_type == options['strategy_type']
                            ]
                        
                        # Filter by profit and confidence thresholds
                        filtered_opportunities = [
                            opp for opp in opportunities
                            if (opp.expected_profit >= options['min_profit'] and 
                                opp.confidence_score >= options['min_confidence'])
                        ]
                        
                        all_opportunities.extend(filtered_opportunities)
                        results['opportunities_analyzed'] += len(opportunities)
                        
                    except Exception as e:
                        error_msg = f"Failed to analyze {set_config.set_name}: {e}"
                        results['errors'].append(error_msg)
                        self.stdout.write(self.style.WARNING(f"⚠️  {error_msg}"))
            
            # Sort opportunities by overall score
            all_opportunities.sort(key=lambda x: x.overall_score, reverse=True)
            
            # Limit to max opportunities
            limited_opportunities = all_opportunities[:options['max_opportunities']]
            results['profitable_opportunities'] = len(limited_opportunities)
            
            # Store top opportunities for display
            results['top_opportunities'] = limited_opportunities[:10]
            
            self.stdout.write(f"✅ Found {len(limited_opportunities)} profitable opportunities")
            
            # Phase 3: Create database records (unless dry run)
            if not options['dry_run'] and limited_opportunities:
                self.stdout.write("\n💾 Phase 3: Creating database records...")
                
                created_count = await self._create_database_records(
                    limited_opportunities, options['clear_existing']
                )
                results['strategies_created'] = created_count
                
                self.stdout.write(f"✅ Created {created_count} trading strategy records")
            elif options['dry_run']:
                self.stdout.write("\n🔍 Dry run mode - skipping database creation")
                results['strategies_created'] = len(limited_opportunities)
            
            # Calculate analysis time
            end_time = timezone.now()
            results['analysis_time_seconds'] = (end_time - start_time).total_seconds()
            
            return results
            
        except Exception as e:
            results['errors'].append(f"Analysis pipeline failed: {str(e)}")
            raise
    
    async def _create_database_records(self, 
                                     opportunities: list, 
                                     clear_existing: bool) -> int:
        """Create database records for trading opportunities."""
        
        def create_records():
            created_count = 0
            
            with transaction.atomic():
                # Clear existing dynamic records if requested
                if clear_existing:
                    deleted_count = SetCombiningOpportunity.objects.filter(
                        set_name__startswith='Dynamic:'
                    ).delete()[0]
                    
                    TradingStrategy.objects.filter(
                        strategy_type=StrategyType.SET_COMBINING,
                        name__startswith='Dynamic:'
                    ).delete()
                    
                    self.stdout.write(f"🗑️  Cleared {deleted_count} existing dynamic opportunities")
                
                # Create new records
                for opp in opportunities:
                    try:
                        # Create strategy name
                        strategy_name = f"Dynamic: {opp.set_name} ({opp.strategy_type.title()})"
                        
                        # Create description
                        if opp.strategy_type == 'combine':
                            description = (
                                f"Buy individual {opp.set_name} pieces for "
                                f"{opp.capital_required:,.0f} GP, combine into complete set, "
                                f"profit: {opp.expected_profit:,.0f} GP "
                                f"({opp.profit_margin_pct:.1f}% margin)"
                            )
                        else:
                            description = (
                                f"Buy complete {opp.set_name} for "
                                f"{opp.capital_required:,.0f} GP, decombine and sell pieces, "
                                f"profit: {opp.expected_profit:,.0f} GP "
                                f"({opp.profit_margin_pct:.1f}% margin)"
                            )
                        
                        # Create trading strategy
                        strategy, created = TradingStrategy.objects.update_or_create(
                            strategy_type=StrategyType.SET_COMBINING,
                            name=strategy_name,
                            defaults={
                                'description': description,
                                'potential_profit_gp': int(opp.expected_profit),
                                'profit_margin_pct': opp.profit_margin_pct,
                                'risk_level': opp.risk_level,
                                'min_capital_required': int(opp.capital_required),
                                'recommended_capital': int(opp.capital_required * 2),
                                'optimal_market_condition': 'stable',
                                'estimated_time_minutes': int(opp.expected_duration_hours * 60),
                                'confidence_score': opp.confidence_score,
                                'is_active': True,
                                'strategy_data': {
                                    'strategy_type': opp.strategy_type,
                                    'overall_score': opp.overall_score,
                                    'risk_score': opp.risk_score,
                                    'volume_score': opp.volume_score,
                                    'liquidity_score': opp.liquidity_score,
                                    'volatility_score': opp.volatility_score,
                                    'price_momentum': opp.price_momentum,
                                    'historical_success_rate': opp.historical_success_rate,
                                    'discovery_method': 'dynamic_bidirectional_analysis'
                                }
                            }
                        )
                        
                        # Get real volume data for components
                        piece_volumes = self._get_real_volume_data_sync(opp.component_ids)
                        
                        # Get real item names for components
                        piece_names = self._get_real_item_names(opp.component_ids)
                        
                        # Create set combining opportunity
                        SetCombiningOpportunity.objects.update_or_create(
                            set_name=strategy_name,  # Use strategy name for uniqueness
                            defaults={
                                'strategy': strategy,
                                'set_item_id': opp.set_item_id or 0,
                                'piece_ids': opp.component_ids,
                                'piece_names': piece_names,
                                'individual_pieces_total_cost': int(opp.capital_required),
                                'complete_set_price': int(opp.capital_required + opp.expected_profit),
                                'lazy_tax_profit': int(opp.expected_profit),
                                'piece_volumes': piece_volumes,
                                'set_volume': int(opp.volume_score * 100),
                            }
                        )
                        
                        created_count += 1
                        
                    except Exception as e:
                        error_msg = f"Failed to create record for {opp.set_name}: {e}"
                        self.stdout.write(self.style.WARNING(f"⚠️  {error_msg}"))
            
            return created_count
        
        # Run database operations in thread
        return await asyncio.to_thread(create_records)
    
    async def _get_real_volume_data(self, component_ids: list) -> dict:
        """Get real volume data for component items from latest price snapshots."""
        def fetch_volumes():
            from apps.prices.models import PriceSnapshot
            
            volume_data = {}
            
            for item_id in component_ids:
                try:
                    # Get latest price snapshot for this item
                    latest_snapshot = PriceSnapshot.objects.filter(
                        item_id=item_id
                    ).order_by('-created_at').first()
                    
                    if latest_snapshot:
                        # Use total_volume if available, otherwise sum high/low volumes
                        volume = latest_snapshot.total_volume
                        if not volume:
                            volume = (latest_snapshot.high_price_volume or 0) + (latest_snapshot.low_price_volume or 0)
                        
                        volume_data[str(item_id)] = volume or 0
                    else:
                        volume_data[str(item_id)] = 0
                        
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"⚠️  Failed to get volume for item {item_id}: {e}"))
                    volume_data[str(item_id)] = 0
            
            return volume_data
        
        return await asyncio.to_thread(fetch_volumes)
    
    def _get_real_volume_data_sync(self, component_ids: list) -> dict:
        """Synchronous version to get real volume data for component items from latest price snapshots."""
        from apps.prices.models import PriceSnapshot, HistoricalPricePoint
        from django.db.models import Avg
        from datetime import timedelta
        from django.utils import timezone
        
        volume_data = {}
        
        for item_id in component_ids:
            try:
                volume = 0
                
                # Try latest price snapshot first
                latest_snapshot = PriceSnapshot.objects.filter(
                    item_id=item_id
                ).order_by('-created_at').first()
                
                if latest_snapshot:
                    # Use total_volume if available, otherwise sum high/low volumes
                    volume = latest_snapshot.total_volume
                    if not volume:
                        volume = (latest_snapshot.high_price_volume or 0) + (latest_snapshot.low_price_volume or 0)
                
                # If no recent volume data, try historical average
                if not volume:
                    # Try to get average volume from last 7 days of historical data
                    week_ago = timezone.now() - timedelta(days=7)
                    historical_avg = HistoricalPricePoint.objects.filter(
                        item_id=item_id,
                        timestamp__gte=week_ago,
                        total_volume__gt=0
                    ).aggregate(avg_volume=Avg('total_volume'))
                    
                    if historical_avg['avg_volume']:
                        volume = int(historical_avg['avg_volume'])
                        self.stdout.write(f"📊 Using historical volume for item {item_id}: {volume}")
                
                # If still no data, try a broader historical search (30 days)
                if not volume:
                    month_ago = timezone.now() - timedelta(days=30)
                    monthly_avg = HistoricalPricePoint.objects.filter(
                        item_id=item_id,
                        timestamp__gte=month_ago,
                        total_volume__gt=0
                    ).aggregate(avg_volume=Avg('total_volume'))
                    
                    if monthly_avg['avg_volume']:
                        volume = int(monthly_avg['avg_volume'])
                        self.stdout.write(f"📊 Using 30-day historical volume for item {item_id}: {volume}")
                
                volume_data[str(item_id)] = volume or 0
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️  Failed to get volume for item {item_id}: {e}"))
                volume_data[str(item_id)] = 0
        
        return volume_data
    
    def _get_real_item_names(self, component_ids: list) -> list:
        """Get real item names from the database for the given component IDs."""
        try:
            # Get items in the same order as component_ids
            items_dict = {}
            items = Item.objects.filter(item_id__in=component_ids).values('item_id', 'name')
            
            for item in items:
                items_dict[item['item_id']] = item['name']
            
            # Return names in the same order as component_ids
            item_names = []
            for item_id in component_ids:
                if item_id in items_dict:
                    item_names.append(items_dict[item_id])
                else:
                    # Fallback to ID if name not found
                    item_names.append(f"Item {item_id}")
                    self.stdout.write(
                        self.style.WARNING(f"⚠️  No name found for item ID {item_id}, using fallback")
                    )
            
            return item_names
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"⚠️  Failed to get item names: {e}, using fallbacks")
            )
            return [f"Item {item_id}" for item_id in component_ids]
    
    def _display_results(self, results: dict, options: dict):
        """Display analysis results."""
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("🎉 DYNAMIC SET ANALYSIS COMPLETE"))
        self.stdout.write("="*60)
        
        # Summary statistics
        self.stdout.write(f"📊 Summary:")
        self.stdout.write(f"   • Sets discovered: {results['sets_discovered']}")
        self.stdout.write(f"   • Opportunities analyzed: {results['opportunities_analyzed']}")
        self.stdout.write(f"   • Profitable opportunities: {results['profitable_opportunities']}")
        self.stdout.write(f"   • Strategies created: {results['strategies_created']}")
        self.stdout.write(f"   • Analysis time: {results['analysis_time_seconds']:.1f}s")
        
        if results['errors']:
            self.stdout.write(f"   • Errors encountered: {len(results['errors'])}")
        
        # Top opportunities
        if results['top_opportunities']:
            self.stdout.write(f"\n🏆 Top 10 Opportunities:")
            
            for i, opp in enumerate(results['top_opportunities'], 1):
                profit_str = f"{opp.expected_profit:,.0f} GP"
                margin_str = f"{opp.profit_margin_pct:.1f}%"
                score_str = f"{opp.overall_score:.1f}"
                risk_str = opp.risk_level.title()
                
                self.stdout.write(
                    f"   {i:2}. {opp.strategy_type.title():9} | "
                    f"{opp.set_name[:25]:<25} | "
                    f"Profit: {profit_str:>12} | "
                    f"Margin: {margin_str:>6} | "
                    f"Score: {score_str:>5} | "
                    f"Risk: {risk_str}"
                )
        
        # Errors
        if results['errors']:
            self.stdout.write(f"\n⚠️  Errors Encountered:")
            for error in results['errors'][:5]:  # Show first 5 errors
                self.stdout.write(f"   • {error}")
            
            if len(results['errors']) > 5:
                self.stdout.write(f"   ... and {len(results['errors']) - 5} more errors")
        
        # Success message
        if results['strategies_created'] > 0:
            if options['dry_run']:
                self.stdout.write(f"\n🔍 Dry run completed - {results['strategies_created']} opportunities would be created")
            else:
                self.stdout.write(f"\n✅ Successfully created {results['strategies_created']} dynamic trading strategies!")
                self.stdout.write("   Check the set-combining view to see the new opportunities.")
        else:
            self.stdout.write(f"\n⚠️  No profitable opportunities found with current criteria.")
            self.stdout.write(f"   Try lowering --min-profit or --min-confidence thresholds.")
        
        self.stdout.write(f"\n💡 Next steps:")
        self.stdout.write(f"   • View opportunities: http://localhost:5173/set-combining")
        self.stdout.write(f"   • Check API: http://localhost:8000/api/v1/trading/set-combining/")
        self.stdout.write(f"   • Re-run with different parameters as market conditions change")
        
        self.stdout.write("\n" + "="*60)