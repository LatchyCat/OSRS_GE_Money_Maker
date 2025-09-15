from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.trading_strategies.services.market_monitor import MarketConditionMonitor
from apps.trading_strategies.models import MarketConditionSnapshot
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor market conditions and detect bot activity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuous monitoring (every 5 minutes)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=300,  # 5 minutes
            help='Monitoring interval in seconds (default: 300)',
        )
        parser.add_argument(
            '--max-iterations',
            type=int,
            default=0,  # 0 = infinite
            help='Maximum iterations for continuous mode (default: infinite)',
        )

    def handle(self, *args, **options):
        continuous = options['continuous']
        interval = options['interval']
        max_iterations = options['max_iterations']
        
        monitor = MarketConditionMonitor()
        
        if not continuous:
            # Single monitoring run
            self.stdout.write('Running market condition analysis...')
            try:
                snapshot = monitor.monitor_and_record()
                self.display_market_status(snapshot)
            except Exception as e:
                logger.exception('Error during market monitoring')
                raise CommandError(f'Market monitoring failed: {str(e)}')
        else:
            # Continuous monitoring
            self.stdout.write(
                self.style.SUCCESS(
                    f'Starting continuous market monitoring (interval: {interval}s)'
                )
            )
            
            iteration = 0
            try:
                while True:
                    iteration += 1
                    self.stdout.write(f'\n--- Monitoring iteration {iteration} ---')
                    
                    try:
                        snapshot = monitor.monitor_and_record()
                        self.display_market_status(snapshot)
                        
                        # Check for critical conditions
                        if snapshot.crash_risk_level == 'critical':
                            self.stdout.write(
                                self.style.ERROR('⚠️  CRITICAL: Market crash risk detected!')
                            )
                        elif snapshot.bot_activity_score > 0.8:
                            self.stdout.write(
                                self.style.WARNING('⚠️  HIGH BOT ACTIVITY: Potential market manipulation')
                            )
                        
                    except Exception as e:
                        logger.exception(f'Error in monitoring iteration {iteration}')
                        self.stdout.write(
                            self.style.ERROR(f'Iteration {iteration} failed: {str(e)}')
                        )
                    
                    # Check if we should stop
                    if max_iterations > 0 and iteration >= max_iterations:
                        self.stdout.write(
                            self.style.SUCCESS(f'Completed {max_iterations} iterations')
                        )
                        break
                    
                    # Wait for next iteration
                    if iteration < max_iterations or max_iterations == 0:
                        self.stdout.write(f'Waiting {interval} seconds until next check...')
                        import time
                        time.sleep(interval)
                        
            except KeyboardInterrupt:
                self.stdout.write(
                    self.style.SUCCESS('\nMonitoring stopped by user')
                )
            except Exception as e:
                logger.exception('Error during continuous monitoring')
                raise CommandError(f'Continuous monitoring failed: {str(e)}')
    
    def display_market_status(self, snapshot: MarketConditionSnapshot):
        """Display market status information"""
        # Market condition with color coding
        condition_colors = {
            'stable': self.style.SUCCESS,
            'volatile': self.style.WARNING,
            'crashing': self.style.ERROR,
            'recovering': self.style.SUCCESS,
            'bullish': self.style.SUCCESS,
            'bearish': self.style.WARNING,
        }
        
        condition_color = condition_colors.get(snapshot.market_condition, self.style.SUCCESS)
        
        self.stdout.write(f'Timestamp: {snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'Market Condition: {condition_color(snapshot.market_condition.upper())}')
        
        # Risk level with color coding
        risk_colors = {
            'low': self.style.SUCCESS,
            'medium': self.style.WARNING,
            'high': self.style.ERROR,
            'critical': self.style.ERROR,
        }
        
        risk_color = risk_colors.get(snapshot.crash_risk_level, self.style.SUCCESS)
        self.stdout.write(f'Crash Risk: {risk_color(snapshot.crash_risk_level.upper())}')
        
        # Bot activity with color coding
        bot_score = float(snapshot.bot_activity_score)
        if bot_score > 0.8:
            bot_color = self.style.ERROR
        elif bot_score > 0.6:
            bot_color = self.style.WARNING
        else:
            bot_color = self.style.SUCCESS
        
        self.stdout.write(f'Bot Activity: {bot_color(f"{bot_score:.3f}")} (0.0 = none, 1.0 = maximum)')
        
        # Other metrics
        self.stdout.write(f'Volatility Score: {float(snapshot.volatility_score):.3f}')
        self.stdout.write(f'Total Volume (24h): {snapshot.total_volume_24h:,}')
        self.stdout.write(f'Avg Price Change: {float(snapshot.average_price_change_pct):.3f}%')
        
        # Analysis details if available
        if snapshot.market_data:
            details = snapshot.market_data
            self.stdout.write(f'Items Analyzed: {details.get("items_analyzed", 0)}')
            self.stdout.write(f'Volume Spikes: {details.get("volume_spikes_detected", 0)}')
            self.stdout.write(f'Price Crashes: {details.get("price_crashes_detected", 0)}')
            self.stdout.write(f'High Volatility Items: {details.get("high_volatility_items", 0)}')
        
        # Trading recommendation
        is_safe = monitor.is_market_safe_for_trading()
        if is_safe:
            self.stdout.write(self.style.SUCCESS('✅ Market is SAFE for trading'))
        else:
            self.stdout.write(self.style.ERROR('❌ Market is UNSAFE for trading'))

# Create an instance for easier access
monitor = MarketConditionMonitor()