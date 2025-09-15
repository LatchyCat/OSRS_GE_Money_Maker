from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.trading_strategies.services.decanting_detector import DecantingDetector
from apps.trading_strategies.services.set_combining_analyzer import SetCombiningAnalyzer
from apps.trading_strategies.services.flipping_scanner import FlippingScanner
from apps.trading_strategies.services.crafting_calculator import CraftingCalculator
from apps.trading_strategies.services.market_monitor import MarketConditionMonitor
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scan for trading opportunities and update strategy database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strategy-type',
            type=str,
            choices=['decanting', 'set-combining', 'flipping', 'crafting', 'market', 'all'],
            default='all',
            help='Specify which strategy type to scan (default: all)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run analysis without creating database records',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        strategy_type = options['strategy_type']
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting trading strategy scan: {strategy_type}')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE: No database records will be created')
            )
        
        total_strategies_created = 0
        
        try:
            # Market condition monitoring (always run first)
            if strategy_type in ['market', 'all']:
                self.stdout.write('Monitoring market conditions...')
                monitor = MarketConditionMonitor()
                
                if not dry_run:
                    snapshot = monitor.monitor_and_record()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Market condition: {snapshot.market_condition}, '
                            f'Crash risk: {snapshot.crash_risk_level}, '
                            f'Bot activity: {snapshot.bot_activity_score:.3f}'
                        )
                    )
                else:
                    analysis = monitor.analyze_market_conditions()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Market analysis: {analysis["market_condition"]}, '
                            f'Bot activity: {analysis["bot_activity_score"]:.3f}'
                        )
                    )
            
            # Decanting opportunities
            if strategy_type in ['decanting', 'all']:
                self.stdout.write('Scanning decanting opportunities...')
                detector = DecantingDetector()
                
                if not dry_run:
                    created = detector.scan_and_create_opportunities()
                    total_strategies_created += created
                    self.stdout.write(
                        self.style.SUCCESS(f'Created {created} decanting strategies')
                    )
                else:
                    opportunities = detector.detect_opportunities()
                    self.stdout.write(
                        self.style.SUCCESS(f'Found {len(opportunities)} decanting opportunities')
                    )
                    if verbose and opportunities:
                        for opp in opportunities[:3]:  # Show top 3
                            self.stdout.write(f'  - {opp["potion_name"]} {opp["from_dose"]}→{opp["to_dose"]}: {opp["profit_per_conversion"]:,} GP')
            
            # Set combining opportunities
            if strategy_type in ['set-combining', 'all']:
                self.stdout.write('Analyzing set combining opportunities...')
                analyzer = SetCombiningAnalyzer()
                
                if not dry_run:
                    created = analyzer.scan_and_create_opportunities()
                    total_strategies_created += created
                    self.stdout.write(
                        self.style.SUCCESS(f'Created {created} set combining strategies')
                    )
                else:
                    opportunities = analyzer.analyze_opportunities()
                    self.stdout.write(
                        self.style.SUCCESS(f'Found {len(opportunities)} set combining opportunities')
                    )
                    if verbose and opportunities:
                        for opp in opportunities[:3]:  # Show top 3
                            self.stdout.write(f'  - {opp["set_name"]}: {opp["lazy_tax_profit"]:,} GP lazy tax')
            
            # Flipping opportunities
            if strategy_type in ['flipping', 'all']:
                self.stdout.write('Scanning flipping opportunities...')
                scanner = FlippingScanner()
                
                if not dry_run:
                    created = scanner.scan_and_create_opportunities()
                    total_strategies_created += created
                    self.stdout.write(
                        self.style.SUCCESS(f'Created {created} flipping strategies')
                    )
                else:
                    opportunities = scanner.scan_flipping_opportunities()
                    self.stdout.write(
                        self.style.SUCCESS(f'Found {len(opportunities)} flipping opportunities')
                    )
                    if verbose and opportunities:
                        for opp in opportunities[:3]:  # Show top 3
                            self.stdout.write(f'  - {opp["item_name"]}: {opp["margin"]:,} GP margin ({opp["margin_percentage"]:.1f}%)')
            
            # Crafting opportunities
            if strategy_type in ['crafting', 'all']:
                self.stdout.write('Calculating crafting opportunities...')
                calculator = CraftingCalculator()
                
                if not dry_run:
                    created = calculator.scan_and_create_opportunities()
                    total_strategies_created += created
                    self.stdout.write(
                        self.style.SUCCESS(f'Created {created} crafting strategies')
                    )
                else:
                    opportunities = calculator.calculate_opportunities()
                    self.stdout.write(
                        self.style.SUCCESS(f'Found {len(opportunities)} crafting opportunities')
                    )
                    if verbose and opportunities:
                        for opp in opportunities[:3]:  # Show top 3
                            self.stdout.write(f'  - {opp["recipe_name"]}: {opp["profit_per_hour"]:,} GP/hour')
            
            # Summary
            duration = timezone.now() - start_time
            
            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Strategy scan completed! Created {total_strategies_created} strategies '
                        f'in {duration.total_seconds():.1f} seconds'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Dry run completed in {duration.total_seconds():.1f} seconds '
                        f'(no database records created)'
                    )
                )
        
        except Exception as e:
            logger.exception('Error during strategy scan')
            raise CommandError(f'Strategy scan failed: {str(e)}')