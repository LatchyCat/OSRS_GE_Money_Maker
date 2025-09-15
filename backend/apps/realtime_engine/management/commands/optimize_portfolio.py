"""
Django management command for portfolio optimization using statistical methods and Ollama integration.

Usage:
    python manage.py optimize_portfolio --user-id 1 --capital 10000000
    python manage.py optimize_portfolio --user-id 1 --capital 5000000 --method risk_parity --max-items 8
    python manage.py optimize_portfolio --continuous --interval 3600
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
from apps.realtime_engine.models import PortfolioOptimization, PortfolioAllocation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Optimize portfolios using statistical methods and risk analysis'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
        
    def add_arguments(self, parser):
        # User targeting
        parser.add_argument(
            '--user-id',
            type=int,
            help='Specific user ID to optimize portfolio for'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Username to optimize portfolio for'
        )
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Optimize portfolios for all active users'
        )
        
        # Capital allocation
        parser.add_argument(
            '--capital',
            type=int,
            help='Total capital available for optimization (GP)'
        )
        parser.add_argument(
            '--target-return',
            type=float,
            default=0.05,
            help='Target daily return rate (default: 0.05 = 5%)'
        )
        parser.add_argument(
            '--risk-tolerance',
            type=float,
            default=0.5,
            help='Risk tolerance level (0-1, default: 0.5)'
        )
        
        # Optimization settings
        parser.add_argument(
            '--method',
            choices=['risk_parity', 'modern_portfolio_theory', 'kelly_criterion', 'equal_weight'],
            default='risk_parity',
            help='Optimization method (default: risk_parity)'
        )
        parser.add_argument(
            '--max-items',
            type=int,
            default=10,
            help='Maximum number of items in portfolio (default: 10)'
        )
        parser.add_argument(
            '--max-position-size',
            type=float,
            default=0.25,
            help='Maximum position size as fraction of capital (default: 0.25)'
        )
        parser.add_argument(
            '--min-position-size',
            type=float,
            default=0.02,
            help='Minimum position size as fraction of capital (default: 0.02)'
        )
        parser.add_argument(
            '--liquidity-requirement',
            choices=['minimal', 'low', 'medium', 'high', 'very_high'],
            default='medium',
            help='Required liquidity level (default: medium)'
        )
        
        # Continuous mode
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuous portfolio optimization'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=3600,  # 1 hour
            help='Interval between optimizations in continuous mode (seconds, default: 3600)'
        )
        
        # Output options
        parser.add_argument(
            '--save-to-db',
            action='store_true',
            default=True,
            help='Save optimization results to database (default: True)'
        )
        parser.add_argument(
            '--execute-trades',
            action='store_true',
            help='Generate rebalancing actions for execution'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show optimization results without saving'
        )
        
        # Analysis options
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.6,
            help='Minimum confidence threshold for allocations (default: 0.6)'
        )
        parser.add_argument(
            '--analyze-performance',
            action='store_true',
            help='Analyze performance of existing portfolios'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        if options['continuous']:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"🎯 Starting portfolio optimization (method: {options['method']})"
            )
        )
        
        try:
            if options['continuous']:
                # Run continuous optimization
                asyncio.run(self.continuous_optimization(options))
            elif options['analyze_performance']:
                # Analyze existing portfolio performance
                asyncio.run(self.analyze_portfolio_performance(options))
            else:
                # Run single optimization batch
                asyncio.run(self.single_optimization_batch(options))
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("🛑 Portfolio optimization stopped by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Portfolio optimization failed: {e}"))
            logger.exception("Portfolio optimization failed")
    
    async def single_optimization_batch(self, options):
        """Run a single batch of portfolio optimization."""
        users = await self.get_target_users(options)
        
        if not users:
            self.stdout.write(self.style.WARNING("⚠️  No users found for optimization"))
            return
        
        self.stdout.write(f"🔄 Optimizing portfolios for {len(users)} user(s)...")
        
        optimization_count = 0
        
        for user in users:
            try:
                self.stdout.write(f"\n📊 Optimizing portfolio for {user.username}...")
                
                # Get capital for this user
                capital = options.get('capital')
                if not capital:
                    # Try to get from existing portfolio or use default
                    latest_portfolio = await sync_to_async(
                        PortfolioOptimization.objects.filter(user=user).first
                    )()
                    capital = latest_portfolio.total_capital if latest_portfolio else 1000000  # 1M default
                
                # Prepare optimization parameters
                optimization_params = {
                    'total_capital': capital,
                    'target_return': options['target_return'],
                    'risk_tolerance': options['risk_tolerance'],
                    'optimization_method': options['method'],
                    'max_position_size': options['max_position_size'],
                    'min_position_size': options['min_position_size'],
                    'max_items': options['max_items'],
                    'liquidity_requirement': options['liquidity_requirement'],
                }
                
                # Run optimization
                result = await portfolio_optimizer.optimize_portfolio(
                    user_id=user.id,
                    **optimization_params
                )
                
                if result.get('error'):
                    self.stdout.write(self.style.ERROR(f"❌ Optimization failed for {user.username}: {result['error']}"))
                    continue
                
                # Display results
                self.display_optimization_results(result, user.username)
                
                # Save to database if requested
                if options['save_to_db'] and not options['dry_run']:
                    await self.save_optimization_to_db(result, user)
                
                # Generate rebalancing actions if requested
                if options['execute_trades'] and not options['dry_run']:
                    await self.generate_rebalancing_actions(result, user, options['min_confidence'])
                
                optimization_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Failed to optimize for {user.username}: {e}"))
                logger.exception(f"Failed to optimize portfolio for user {user.username}")
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Portfolio optimization completed for {optimization_count} users")
        )
    
    async def continuous_optimization(self, options):
        """Run continuous portfolio optimization."""
        interval = options['interval']
        optimization_count = 0
        
        self.stdout.write(f"🔄 Starting continuous portfolio optimization (interval: {interval}s)")
        
        while self.running:
            try:
                optimization_count += 1
                start_time = timezone.now()
                
                self.stdout.write(f"\n🎯 Portfolio optimization batch #{optimization_count} starting at {start_time.strftime('%H:%M:%S')}")
                
                # Run optimization batch
                await self.single_optimization_batch(options)
                
                # Calculate batch duration
                batch_duration = (timezone.now() - start_time).total_seconds()
                self.stdout.write(f"✅ Batch #{optimization_count} completed in {batch_duration:.1f}s")
                
                # Wait for next batch
                if self.running:
                    await asyncio.sleep(interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Batch error: {e}"))
                logger.exception("Error in continuous portfolio optimization")
                
                # Wait before retrying
                await asyncio.sleep(min(interval, 300))  # Max 5 minutes
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Continuous portfolio optimization completed. {optimization_count} batches processed."
            )
        )
    
    async def analyze_portfolio_performance(self, options):
        """Analyze performance of existing portfolios."""
        self.stdout.write("📈 Analyzing portfolio performance...")
        
        # Get active portfolios
        portfolios = await sync_to_async(list)(
            PortfolioOptimization.objects.filter(is_active=True).select_related('user')
        )
        
        if not portfolios:
            self.stdout.write(self.style.WARNING("⚠️  No active portfolios found"))
            return
        
        self.stdout.write(f"🔍 Found {len(portfolios)} active portfolio(s) to analyze")
        
        for portfolio in portfolios:
            try:
                # Analyze portfolio performance
                performance_data = await portfolio_optimizer.analyze_portfolio_performance(portfolio.id)
                
                if performance_data.get('error'):
                    self.stdout.write(
                        self.style.ERROR(f"❌ Analysis failed for {portfolio.user.username}: {performance_data['error']}")
                    )
                    continue
                
                # Display performance analysis
                self.display_performance_analysis(performance_data, portfolio)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to analyze {portfolio.user.username}: {e}")
                )
                logger.exception(f"Failed to analyze portfolio {portfolio.id}")
    
    def display_optimization_results(self, result: Dict, username: str):
        """Display optimization results."""
        self.stdout.write(f"\n💼 Portfolio Optimization Results for {username}:")
        
        portfolio_metrics = result.get('portfolio_metrics', {})
        allocations = result.get('allocations', [])
        
        # Portfolio metrics
        expected_return = portfolio_metrics.get('expected_daily_return', 0)
        expected_risk = portfolio_metrics.get('expected_daily_risk', 0)
        sharpe_ratio = portfolio_metrics.get('sharpe_ratio', 0)
        
        self.stdout.write(f"   • Expected daily return: {expected_return:.2%}")
        self.stdout.write(f"   • Expected daily risk: {expected_risk:.2%}")
        self.stdout.write(f"   • Sharpe ratio: {sharpe_ratio:.2f}")
        self.stdout.write(f"   • Total allocations: {len(allocations)}")
        
        # Capital allocation
        total_allocated = sum(alloc['allocated_capital'] for alloc in allocations)
        self.stdout.write(f"   • Total capital allocated: {total_allocated:,} GP")
        
        # Top allocations
        if allocations:
            self.stdout.write("\n📈 Top Allocations:")
            
            # Sort by weight
            sorted_allocations = sorted(allocations, key=lambda x: x['weight'], reverse=True)[:5]
            
            for alloc in sorted_allocations:
                self.stdout.write(
                    f"   • {alloc['item_name']}: {alloc['weight']:.1%} "
                    f"({alloc['allocated_capital']:,} GP, qty: {alloc['recommended_quantity']})"
                )
    
    def display_performance_analysis(self, performance_data: Dict, portfolio: PortfolioOptimization):
        """Display portfolio performance analysis."""
        username = portfolio.user.username
        
        self.stdout.write(f"\n📊 Performance Analysis for {username}:")
        
        # Current metrics
        current_metrics = performance_data.get('current_metrics', {})
        self.stdout.write(f"   • Current return: {current_metrics.get('actual_return', 0):.2%}")
        self.stdout.write(f"   • Current risk: {current_metrics.get('actual_risk', 0):.2%}")
        self.stdout.write(f"   • Current Sharpe: {current_metrics.get('actual_sharpe', 0):.2f}")
        
        # Performance vs expectations
        performance_vs_expected = performance_data.get('performance_vs_expected', {})
        return_diff = performance_vs_expected.get('return_difference', 0)
        risk_diff = performance_vs_expected.get('risk_difference', 0)
        
        return_color = 'green' if return_diff > 0 else 'red'
        risk_color = 'green' if risk_diff < 0 else 'red'  # Lower risk is better
        
        self.stdout.write(f"   • Return vs expected: {return_diff:+.2%} ({return_color})")
        self.stdout.write(f"   • Risk vs expected: {risk_diff:+.2%} ({risk_color})")
        
        # Recommendations
        recommendations = performance_data.get('recommendations', [])
        if recommendations:
            self.stdout.write("   • Recommendations:")
            for rec in recommendations[:3]:  # Show top 3
                self.stdout.write(f"     - {rec}")
    
    async def save_optimization_to_db(self, result: Dict, user: User):
        """Save optimization results to database."""
        try:
            # Create portfolio optimization record
            portfolio_data = result['portfolio_metrics']
            allocations_data = result['allocations']
            
            async with sync_to_async(transaction.atomic)():
                # Create PortfolioOptimization
                portfolio = await sync_to_async(PortfolioOptimization.objects.create)(
                    user=user,
                    total_capital=result['total_capital'],
                    target_return=result['target_return'],
                    risk_tolerance=result['risk_tolerance'],
                    optimization_method=result['optimization_method'],
                    expected_daily_return=portfolio_data['expected_daily_return'],
                    expected_daily_risk=portfolio_data['expected_daily_risk'],
                    sharpe_ratio=portfolio_data['sharpe_ratio'],
                    sortino_ratio=portfolio_data.get('sortino_ratio', 0),
                    diversification_ratio=portfolio_data.get('diversification_ratio', 1),
                    max_position_size=result.get('max_position_size', 0.25),
                    min_position_size=result.get('min_position_size', 0.02),
                    max_items=result.get('max_items', 10),
                    liquidity_requirement=result.get('liquidity_requirement', 'medium'),
                    recommended_items_count=len(allocations_data),
                    total_allocated_capital=sum(alloc['allocated_capital'] for alloc in allocations_data),
                    cash_reserve=result['total_capital'] - sum(alloc['allocated_capital'] for alloc in allocations_data),
                )
                
                # Create PortfolioAllocation records
                from apps.items.models import Item
                
                for alloc_data in allocations_data:
                    item = await sync_to_async(Item.objects.get)(item_id=alloc_data['item_id'])
                    
                    await sync_to_async(PortfolioAllocation.objects.create)(
                        portfolio=portfolio,
                        item=item,
                        weight=alloc_data['weight'],
                        allocated_capital=alloc_data['allocated_capital'],
                        recommended_quantity=alloc_data['recommended_quantity'],
                        target_price=alloc_data['target_price'],
                        individual_risk=alloc_data.get('individual_risk', 0),
                        contribution_to_risk=alloc_data.get('contribution_to_risk', 0),
                        beta=alloc_data.get('beta', 1.0),
                        expected_return=alloc_data.get('expected_return', 0),
                        confidence_score=alloc_data.get('confidence_score', 0.5),
                        ge_limit_utilized=alloc_data.get('ge_limit_utilized', 0),
                        liquidity_score=alloc_data.get('liquidity_score', 0.5),
                        allocation_reasons=alloc_data.get('allocation_reasons', []),
                    )
                
                self.stdout.write(f"💾 Saved portfolio optimization for {user.username} to database")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to save optimization: {e}"))
            logger.exception("Failed to save portfolio optimization")
    
    async def generate_rebalancing_actions(self, result: Dict, user: User, min_confidence: float):
        """Generate rebalancing actions for portfolio execution."""
        try:
            # Get user's current portfolio if any
            current_portfolio = await sync_to_async(
                PortfolioOptimization.objects.filter(user=user, is_active=True).first
            )()
            
            if not current_portfolio:
                self.stdout.write(f"ℹ️  No current portfolio for {user.username}, skipping rebalancing actions")
                return
            
            # Generate rebalancing recommendations
            rebalance_result = await portfolio_optimizer.generate_rebalancing_actions(
                current_portfolio.id,
                result,
                min_confidence=min_confidence
            )
            
            if rebalance_result.get('error'):
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to generate rebalancing actions: {rebalance_result['error']}")
                )
                return
            
            actions_count = len(rebalance_result.get('actions', []))
            self.stdout.write(f"🔄 Generated {actions_count} rebalancing actions for {user.username}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to generate rebalancing actions: {e}"))
            logger.exception("Failed to generate rebalancing actions")
    
    async def get_target_users(self, options) -> List[User]:
        """Get list of users to optimize portfolios for."""
        users = []
        
        if options.get('user_id'):
            try:
                user = await sync_to_async(User.objects.get)(id=options['user_id'])
                users = [user]
            except User.DoesNotExist:
                raise CommandError(f"User with ID {options['user_id']} not found")
                
        elif options.get('username'):
            try:
                user = await sync_to_async(User.objects.get)(username=options['username'])
                users = [user]
            except User.DoesNotExist:
                raise CommandError(f"User '{options['username']}' not found")
                
        elif options.get('all_users'):
            users = await sync_to_async(list)(
                User.objects.filter(is_active=True)
            )
            
        else:
            # Default to users with existing portfolios
            portfolio_user_ids = await sync_to_async(list)(
                PortfolioOptimization.objects.filter(is_active=True)
                .values_list('user_id', flat=True)
                .distinct()
            )
            users = await sync_to_async(list)(
                User.objects.filter(id__in=portfolio_user_ids)
            )
        
        return users
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.stdout.write(self.style.WARNING(f"🛑 Received signal {signum}, shutting down..."))
        self.running = False