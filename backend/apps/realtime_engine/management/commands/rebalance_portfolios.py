"""
Django management command for portfolio rebalancing and execution of trading actions.

Usage:
    python manage.py rebalance_portfolios --user-id 1
    python manage.py rebalance_portfolios --all-users --drift-threshold 0.05
    python manage.py rebalance_portfolios --continuous --interval 1800
"""

import asyncio
import logging
import signal
import sys
from typing import Optional, List, Dict
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from asgiref.sync import async_to_sync, sync_to_async

from services.portfolio_optimizer import portfolio_optimizer
from apps.realtime_engine.models import (
    PortfolioOptimization, PortfolioRebalance, PortfolioAction
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Execute portfolio rebalancing and manage trading actions'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
        
    def add_arguments(self, parser):
        # User targeting
        parser.add_argument(
            '--user-id',
            type=int,
            help='Specific user ID to rebalance portfolio for'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Username to rebalance portfolio for'
        )
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Rebalance portfolios for all users with active portfolios'
        )
        
        # Rebalancing triggers
        parser.add_argument(
            '--force-rebalance',
            action='store_true',
            help='Force rebalancing regardless of drift threshold'
        )
        parser.add_argument(
            '--drift-threshold',
            type=float,
            default=0.05,
            help='Portfolio drift threshold for triggering rebalance (default: 0.05 = 5%)'
        )
        parser.add_argument(
            '--risk-breach-threshold',
            type=float,
            default=0.1,
            help='Risk breach threshold for emergency rebalancing (default: 0.1 = 10%)'
        )
        
        # Execution settings
        parser.add_argument(
            '--execute-actions',
            action='store_true',
            help='Execute pending portfolio actions'
        )
        parser.add_argument(
            '--max-slippage',
            type=float,
            default=0.02,
            help='Maximum acceptable slippage percentage (default: 0.02 = 2%)'
        )
        parser.add_argument(
            '--execution-timeout',
            type=int,
            default=300,  # 5 minutes
            help='Timeout for individual action execution in seconds (default: 300)'
        )
        
        # Action filtering
        parser.add_argument(
            '--action-type',
            choices=['buy', 'sell', 'hold', 'reduce', 'increase'],
            help='Filter actions by type'
        )
        parser.add_argument(
            '--max-actions',
            type=int,
            default=20,
            help='Maximum number of actions to execute per batch (default: 20)'
        )
        parser.add_argument(
            '--priority-only',
            action='store_true',
            help='Execute only high-priority actions (priority <= 3)'
        )
        
        # Continuous mode
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuous rebalancing monitoring'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=1800,  # 30 minutes
            help='Interval between rebalancing checks in continuous mode (seconds, default: 1800)'
        )
        
        # Analysis and reporting
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Analyze portfolio drift without executing rebalancing'
        )
        parser.add_argument(
            '--show-pending-actions',
            action='store_true',
            help='Show all pending portfolio actions'
        )
        parser.add_argument(
            '--performance-report',
            action='store_true',
            help='Generate portfolio performance report'
        )
        
        # Safety options
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without executing'
        )
        parser.add_argument(
            '--confirm-trades',
            action='store_true',
            help='Require confirmation before executing trades'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        if options['continuous']:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.stdout.write(
            self.style.SUCCESS("🔄 Starting portfolio rebalancing system")
        )
        
        try:
            if options['continuous']:
                # Run continuous rebalancing monitoring
                asyncio.run(self.continuous_rebalancing(options))
            elif options['show_pending_actions']:
                # Show pending actions
                asyncio.run(self.show_pending_actions(options))
            elif options['performance_report']:
                # Generate performance report
                asyncio.run(self.generate_performance_report(options))
            elif options['analyze_only']:
                # Analyze portfolio drift only
                asyncio.run(self.analyze_portfolio_drift(options))
            elif options['execute_actions']:
                # Execute pending actions
                asyncio.run(self.execute_pending_actions(options))
            else:
                # Run rebalancing analysis and generation
                asyncio.run(self.single_rebalancing_batch(options))
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("🛑 Portfolio rebalancing stopped by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Portfolio rebalancing failed: {e}"))
            logger.exception("Portfolio rebalancing failed")
    
    async def single_rebalancing_batch(self, options):
        """Run a single batch of portfolio rebalancing."""
        portfolios = await self.get_target_portfolios(options)
        
        if not portfolios:
            self.stdout.write(self.style.WARNING("⚠️  No active portfolios found for rebalancing"))
            return
        
        self.stdout.write(f"🔄 Analyzing {len(portfolios)} portfolio(s) for rebalancing...")
        
        rebalance_count = 0
        
        for portfolio in portfolios:
            try:
                self.stdout.write(f"\n📊 Analyzing portfolio for {portfolio.user.username}...")
                
                # Analyze portfolio drift
                drift_analysis = await portfolio_optimizer.analyze_portfolio_drift(portfolio.id)
                
                if drift_analysis.get('error'):
                    self.stdout.write(
                        self.style.ERROR(f"❌ Drift analysis failed: {drift_analysis['error']}")
                    )
                    continue
                
                # Check if rebalancing is needed
                needs_rebalancing = await self.check_rebalancing_needed(
                    drift_analysis, options, portfolio.user.username
                )
                
                if needs_rebalancing or options['force_rebalance']:
                    # Generate rebalancing actions
                    rebalance_result = await portfolio_optimizer.generate_rebalancing_actions(
                        portfolio_id=portfolio.id,
                        trigger_reason='drift_threshold' if needs_rebalancing else 'manual',
                        max_slippage=options['max_slippage']
                    )
                    
                    if rebalance_result.get('error'):
                        self.stdout.write(
                            self.style.ERROR(f"❌ Rebalancing failed: {rebalance_result['error']}")
                        )
                        continue
                    
                    # Display rebalancing summary
                    self.display_rebalancing_summary(rebalance_result, portfolio.user.username)
                    
                    # Save to database if not dry run
                    if not options['dry_run']:
                        await self.save_rebalancing_to_db(rebalance_result, portfolio)
                    
                    rebalance_count += 1
                else:
                    self.stdout.write(f"✅ {portfolio.user.username}: Portfolio within drift threshold")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to rebalance {portfolio.user.username}: {e}")
                )
                logger.exception(f"Failed to rebalance portfolio {portfolio.id}")
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Portfolio rebalancing completed. {rebalance_count} portfolios rebalanced.")
        )
    
    async def continuous_rebalancing(self, options):
        """Run continuous rebalancing monitoring."""
        interval = options['interval']
        monitoring_count = 0
        
        self.stdout.write(f"🔄 Starting continuous rebalancing monitoring (interval: {interval}s)")
        
        while self.running:
            try:
                monitoring_count += 1
                start_time = timezone.now()
                
                self.stdout.write(f"\n🔍 Rebalancing check #{monitoring_count} starting at {start_time.strftime('%H:%M:%S')}")
                
                # Run rebalancing batch
                await self.single_rebalancing_batch(options)
                
                # Execute pending actions if enabled
                if options['execute_actions']:
                    await self.execute_pending_actions(options)
                
                # Calculate batch duration
                batch_duration = (timezone.now() - start_time).total_seconds()
                self.stdout.write(f"✅ Check #{monitoring_count} completed in {batch_duration:.1f}s")
                
                # Wait for next batch
                if self.running:
                    await asyncio.sleep(interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Monitoring error: {e}"))
                logger.exception("Error in continuous rebalancing monitoring")
                
                # Wait before retrying
                await asyncio.sleep(min(interval, 300))  # Max 5 minutes
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Continuous rebalancing monitoring completed. {monitoring_count} checks processed."
            )
        )
    
    async def execute_pending_actions(self, options):
        """Execute pending portfolio actions."""
        self.stdout.write("⚡ Executing pending portfolio actions...")
        
        # Build filters for actions
        filters = {'status': 'pending'}
        
        if options.get('action_type'):
            filters['action_type'] = options['action_type']
            
        if options.get('priority_only'):
            filters['priority__lte'] = 3
        
        # Get pending actions
        actions = await sync_to_async(list)(
            PortfolioAction.objects.filter(**filters)
            .select_related('item', 'rebalance__portfolio__user')
            .order_by('priority', '-created_at')[:options['max_actions']]
        )
        
        if not actions:
            self.stdout.write("ℹ️  No pending actions found")
            return
        
        self.stdout.write(f"🎯 Found {len(actions)} pending action(s) to execute")
        
        execution_count = 0
        failed_count = 0
        
        for action in actions:
            try:
                username = action.rebalance.portfolio.user.username
                
                # Show action details
                self.stdout.write(
                    f"⚡ Executing: {action.action_type.upper()} {abs(action.quantity_change)} "
                    f"{action.item.name} @ {action.target_price} GP (User: {username})"
                )
                
                # Confirm if required
                if options['confirm_trades'] and not options['dry_run']:
                    confirm = input(f"Execute this action? (y/N): ")
                    if confirm.lower() != 'y':
                        self.stdout.write("⏭️  Skipped by user")
                        continue
                
                # Execute action (simulate for now)
                if not options['dry_run']:
                    # In a real implementation, this would integrate with GE trading API
                    success = await self.simulate_action_execution(action, options)
                    
                    if success:
                        execution_count += 1
                        self.stdout.write(self.style.SUCCESS("✅ Action executed successfully"))
                    else:
                        failed_count += 1
                        self.stdout.write(self.style.ERROR("❌ Action execution failed"))
                else:
                    self.stdout.write("🔍 DRY RUN - Action would be executed")
                
            except Exception as e:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f"❌ Failed to execute action: {e}"))
                logger.exception("Failed to execute portfolio action")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"⚡ Action execution completed: {execution_count} successful, {failed_count} failed"
            )
        )
    
    async def simulate_action_execution(self, action: PortfolioAction, options: Dict) -> bool:
        """Simulate execution of a portfolio action."""
        try:
            # Simulate execution delay
            await asyncio.sleep(0.1)
            
            # Calculate simulated execution price with slippage
            slippage = 0.01  # 1% simulated slippage
            if action.action_type == 'buy':
                execution_price = int(action.target_price * (1 + slippage))
            else:  # sell
                execution_price = int(action.target_price * (1 - slippage))
            
            # Update action with execution data
            action.executed_quantity = abs(action.quantity_change)
            action.average_execution_price = execution_price
            action.status = 'completed'
            action.execution_timestamp = timezone.now()
            
            await sync_to_async(action.save)()
            
            return True
            
        except Exception as e:
            # Mark action as failed
            action.status = 'failed'
            action.failure_reason = str(e)
            await sync_to_async(action.save)()
            return False
    
    async def show_pending_actions(self, options):
        """Show all pending portfolio actions."""
        self.stdout.write("📋 Pending Portfolio Actions:")
        
        actions = await sync_to_async(list)(
            PortfolioAction.objects.filter(status='pending')
            .select_related('item', 'rebalance__portfolio__user')
            .order_by('priority', '-created_at')
        )
        
        if not actions:
            self.stdout.write("ℹ️  No pending actions found")
            return
        
        self.stdout.write(f"📊 Found {len(actions)} pending action(s):")
        
        for action in actions:
            username = action.rebalance.portfolio.user.username
            estimated_value = action.estimated_value
            
            self.stdout.write(
                f"   • {username}: {action.action_type.upper()} {abs(action.quantity_change)} "
                f"{action.item.name} @ {action.target_price} GP "
                f"(Priority: {action.priority}, Value: {estimated_value:,} GP)"
            )
    
    async def analyze_portfolio_drift(self, options):
        """Analyze portfolio drift without executing rebalancing."""
        portfolios = await self.get_target_portfolios(options)
        
        if not portfolios:
            self.stdout.write(self.style.WARNING("⚠️  No active portfolios found"))
            return
        
        self.stdout.write(f"📊 Analyzing portfolio drift for {len(portfolios)} portfolio(s)...")
        
        for portfolio in portfolios:
            try:
                drift_analysis = await portfolio_optimizer.analyze_portfolio_drift(portfolio.id)
                
                if drift_analysis.get('error'):
                    self.stdout.write(
                        self.style.ERROR(f"❌ Analysis failed for {portfolio.user.username}: {drift_analysis['error']}")
                    )
                    continue
                
                self.display_drift_analysis(drift_analysis, portfolio.user.username)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to analyze {portfolio.user.username}: {e}")
                )
                logger.exception(f"Failed to analyze portfolio drift for {portfolio.id}")
    
    async def generate_performance_report(self, options):
        """Generate comprehensive portfolio performance report."""
        self.stdout.write("📈 Generating Portfolio Performance Report...")
        
        portfolios = await self.get_target_portfolios(options)
        
        if not portfolios:
            self.stdout.write(self.style.WARNING("⚠️  No active portfolios found"))
            return
        
        total_capital = 0
        total_return = 0
        portfolio_count = len(portfolios)
        
        self.stdout.write(f"📊 Performance Report ({portfolio_count} portfolios):")
        self.stdout.write("=" * 60)
        
        for portfolio in portfolios:
            try:
                performance_data = await portfolio_optimizer.analyze_portfolio_performance(portfolio.id)
                
                if performance_data.get('error'):
                    continue
                
                username = portfolio.user.username
                current_metrics = performance_data.get('current_metrics', {})
                
                actual_return = current_metrics.get('actual_return', 0)
                total_capital += portfolio.total_capital
                total_return += actual_return * portfolio.total_capital
                
                self.stdout.write(
                    f"{username:15} | "
                    f"Capital: {portfolio.total_capital:>8,} GP | "
                    f"Return: {actual_return:>6.2%} | "
                    f"Risk: {current_metrics.get('actual_risk', 0):>5.2%} | "
                    f"Sharpe: {current_metrics.get('actual_sharpe', 0):>5.2f}"
                )
                
            except Exception as e:
                self.stdout.write(f"❌ Error analyzing {portfolio.user.username}: {e}")
        
        # Summary statistics
        avg_return = (total_return / total_capital) if total_capital > 0 else 0
        
        self.stdout.write("=" * 60)
        self.stdout.write(f"SUMMARY: Total Capital: {total_capital:,} GP | Average Return: {avg_return:.2%}")
    
    def display_rebalancing_summary(self, rebalance_result: Dict, username: str):
        """Display rebalancing summary."""
        self.stdout.write(f"\n🔄 Rebalancing Summary for {username}:")
        
        actions = rebalance_result.get('actions', [])
        total_trades = len(actions)
        
        if total_trades == 0:
            self.stdout.write("   • No rebalancing actions needed")
            return
        
        # Count action types
        buy_actions = sum(1 for a in actions if a['action_type'] == 'buy')
        sell_actions = sum(1 for a in actions if a['action_type'] == 'sell')
        
        # Calculate total value
        total_value = sum(abs(a['quantity_change']) * a['target_price'] for a in actions)
        
        self.stdout.write(f"   • Total trades: {total_trades} ({buy_actions} buy, {sell_actions} sell)")
        self.stdout.write(f"   • Total trade value: {total_value:,} GP")
        
        # Show top actions
        high_priority_actions = [a for a in actions if a['priority'] <= 3]
        if high_priority_actions:
            self.stdout.write("   • High priority actions:")
            for action in high_priority_actions[:3]:  # Show top 3
                self.stdout.write(
                    f"     - {action['action_type'].upper()} {abs(action['quantity_change'])} "
                    f"{action['item_name']} @ {action['target_price']} GP"
                )
    
    def display_drift_analysis(self, drift_analysis: Dict, username: str):
        """Display portfolio drift analysis."""
        self.stdout.write(f"\n📊 Portfolio Drift Analysis for {username}:")
        
        drift_metrics = drift_analysis.get('drift_metrics', {})
        total_drift = drift_metrics.get('total_drift', 0)
        max_item_drift = drift_metrics.get('max_item_drift', 0)
        
        drift_color = 'green' if total_drift < 0.03 else 'yellow' if total_drift < 0.05 else 'red'
        
        self.stdout.write(f"   • Total portfolio drift: {total_drift:.2%} ({drift_color})")
        self.stdout.write(f"   • Maximum item drift: {max_item_drift:.2%}")
        
        # Show items with significant drift
        item_drifts = drift_analysis.get('item_drifts', [])
        significant_drifts = [d for d in item_drifts if abs(d['drift']) > 0.02]
        
        if significant_drifts:
            self.stdout.write("   • Items with significant drift:")
            for drift_data in significant_drifts[:3]:  # Show top 3
                self.stdout.write(
                    f"     - {drift_data['item_name']}: {drift_data['drift']:+.2%}"
                )
    
    async def check_rebalancing_needed(self, drift_analysis: Dict, options: Dict, username: str) -> bool:
        """Check if rebalancing is needed based on drift analysis."""
        drift_metrics = drift_analysis.get('drift_metrics', {})
        total_drift = drift_metrics.get('total_drift', 0)
        risk_breach = drift_metrics.get('risk_breach', False)
        
        drift_threshold = options['drift_threshold']
        risk_breach_threshold = options['risk_breach_threshold']
        
        # Check drift threshold
        if total_drift > drift_threshold:
            self.stdout.write(
                f"⚠️  {username}: Portfolio drift ({total_drift:.2%}) exceeds threshold ({drift_threshold:.2%})"
            )
            return True
        
        # Check risk breach
        if risk_breach:
            self.stdout.write(f"🚨 {username}: Risk breach detected!")
            return True
        
        return False
    
    async def save_rebalancing_to_db(self, rebalance_result: Dict, portfolio: PortfolioOptimization):
        """Save rebalancing results to database."""
        try:
            async with sync_to_async(transaction.atomic)():
                # Create PortfolioRebalance record
                rebalance = await sync_to_async(PortfolioRebalance.objects.create)(
                    portfolio=portfolio,
                    trigger_reason=rebalance_result.get('trigger_reason', 'manual'),
                    pre_rebalance_return=rebalance_result.get('pre_rebalance_metrics', {}).get('return', 0),
                    pre_rebalance_risk=rebalance_result.get('pre_rebalance_metrics', {}).get('risk', 0),
                    pre_rebalance_sharpe=rebalance_result.get('pre_rebalance_metrics', {}).get('sharpe', 0),
                    total_trades_required=len(rebalance_result.get('actions', [])),
                    status='pending'
                )
                
                # Create PortfolioAction records
                from apps.items.models import Item
                
                for action_data in rebalance_result.get('actions', []):
                    item = await sync_to_async(Item.objects.get)(item_id=action_data['item_id'])
                    
                    await sync_to_async(PortfolioAction.objects.create)(
                        rebalance=rebalance,
                        item=item,
                        action_type=action_data['action_type'],
                        target_quantity=action_data['target_quantity'],
                        current_quantity=action_data['current_quantity'],
                        quantity_change=action_data['quantity_change'],
                        target_price=action_data['target_price'],
                        priority=action_data.get('priority', 5),
                        estimated_execution_time=action_data.get('estimated_execution_time', 60),
                        max_slippage_pct=action_data.get('max_slippage_pct', 2.0),
                        respects_ge_limit=action_data.get('respects_ge_limit', True),
                    )
                
                self.stdout.write(f"💾 Saved rebalancing plan for {portfolio.user.username}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to save rebalancing: {e}"))
            logger.exception("Failed to save rebalancing plan")
    
    async def get_target_portfolios(self, options) -> List[PortfolioOptimization]:
        """Get list of portfolios to analyze for rebalancing."""
        filters = {'is_active': True}
        
        if options.get('user_id'):
            filters['user_id'] = options['user_id']
        elif options.get('username'):
            try:
                user = await sync_to_async(User.objects.get)(username=options['username'])
                filters['user_id'] = user.id
            except User.DoesNotExist:
                raise CommandError(f"User '{options['username']}' not found")
        
        portfolios = await sync_to_async(list)(
            PortfolioOptimization.objects.filter(**filters)
            .select_related('user')
            .order_by('-optimization_timestamp')
        )
        
        return portfolios
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.stdout.write(self.style.WARNING(f"🛑 Received signal {signum}, shutting down..."))
        self.running = False