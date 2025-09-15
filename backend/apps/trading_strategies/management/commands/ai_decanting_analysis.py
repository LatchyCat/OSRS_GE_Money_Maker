"""
AI-powered decanting analysis using existing ProfitCalculation data.

This command uses the working ProfitCalculation system (same as high-alchemy view)
combined with AI analysis for intelligent decanting recommendations.
"""

import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from services.ai_decanting_analyzer import ai_decanting_analyzer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate AI-powered decanting recommendations using existing profit data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-profit',
            type=int,
            default=50,
            help='Minimum profit in GP to consider (default: 50)'
        )
        parser.add_argument(
            '--max-results',
            type=int,
            default=20,
            help='Maximum recommendations to generate (default: 20)'
        )
        parser.add_argument(
            '--update-db',
            action='store_true',
            help='Update DecantingOpportunity database records'
        )
        parser.add_argument(
            '--show-reasoning',
            action='store_true',
            help='Show AI reasoning for each recommendation'
        )

    def handle(self, *args, **options):
        """Execute AI decanting analysis."""
        start_time = timezone.now()
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting AI decanting analysis at {start_time}')
        )
        
        try:
            # Run async analysis
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self._run_analysis(options)
            )
            
            loop.close()
            
            duration = timezone.now() - start_time
            self.stdout.write(
                self.style.SUCCESS(
                    f'Analysis completed in {duration.total_seconds():.2f}s'
                )
            )
            
            return result
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'AI analysis failed: {str(e)}')
            )
            raise

    async def _run_analysis(self, options):
        """Run the AI decanting analysis."""
        min_profit = options['min_profit']
        max_results = options['max_results']
        update_db = options['update_db']
        show_reasoning = options['show_reasoning']
        
        self.stdout.write('🤖 Starting AI-powered decanting analysis...')
        
        # Get AI recommendations
        recommendations = await ai_decanting_analyzer.analyze_decanting_opportunities(
            min_profit_gp=min_profit,
            max_results=max_results
        )
        
        if not recommendations:
            self.stdout.write(self.style.WARNING('No viable decanting opportunities found'))
            return {'recommendations': 0}
        
        self.stdout.write(
            self.style.SUCCESS(f'🎯 Found {len(recommendations)} AI-recommended opportunities')
        )
        
        # Display recommendations
        self.stdout.write('\n🏆 Top AI Recommendations:')
        self.stdout.write('=' * 80)
        
        for i, rec in enumerate(recommendations, 1):
            confidence_emoji = '🟢' if rec.ai_confidence >= 0.8 else '🟡' if rec.ai_confidence >= 0.6 else '🟠'
            risk_emoji = '✅' if rec.risk_level == 'low' else '⚠️' if rec.risk_level == 'medium' else '❌'
            timing_emoji = '🚀' if rec.market_timing == 'excellent' else '⏰' if rec.market_timing == 'good' else '📈'
            
            self.stdout.write(
                f'\n{i:2d}. {confidence_emoji} {rec.potion_name}'
            )
            self.stdout.write(
                f'    🔄 {rec.from_dose}-dose → {rec.to_dose}-dose conversion'
            )
            self.stdout.write(
                f'    💰 Buy: {rec.buy_price}gp → Sell: {rec.sell_price}gp each'
            )
            self.stdout.write(
                f'    📊 Profit: {rec.profit_per_conversion}gp ({rec.profit_margin_pct:.1f}% margin)'
            )
            self.stdout.write(
                f'    🤖 AI Confidence: {rec.ai_confidence:.2f} {risk_emoji} Risk: {rec.risk_level}'
            )
            self.stdout.write(
                f'    {timing_emoji} Market: {rec.market_timing} | 📈 Volume: {rec.volume_rating}'
            )
            
            if show_reasoning:
                self.stdout.write(f'    💭 AI Reasoning: {rec.reasoning}')
        
        # Update database if requested
        if update_db:
            await self._update_database(recommendations)
        
        return {
            'recommendations': len(recommendations),
            'avg_confidence': sum(r.ai_confidence for r in recommendations) / len(recommendations),
            'avg_profit': sum(r.profit_per_conversion for r in recommendations) / len(recommendations)
        }

    async def _update_database(self, recommendations):
        """Update database with AI recommendations."""
        self.stdout.write('\n💾 Updating database with AI recommendations...')
        
        from apps.trading_strategies.models import DecantingOpportunity, TradingStrategy
        
        # Get or create AI decanting strategy
        strategy, created = await asyncio.to_thread(
            TradingStrategy.objects.get_or_create,
            name='AI Decanting Analyzer',
            defaults={
                'strategy_type': 'decanting',
                'description': 'AI-powered decanting opportunities using multi-model analysis with qwen2.5, deepseek-r1, and gemma2',
                'potential_profit_gp': int(sum(r.profit_per_conversion for r in recommendations) / len(recommendations)) if recommendations else 500,
                'profit_margin_pct': sum(r.profit_margin_pct for r in recommendations) / len(recommendations) if recommendations else 25.0,
                'risk_level': 'low',  # AI-validated opportunities tend to be lower risk
                'min_capital_required': 1000,
                'recommended_capital': 25000,  # Higher capital for AI-selected opportunities
                'optimal_market_condition': 'stable',
                'estimated_time_minutes': 1,
                'max_volume_per_day': 500,
                'confidence_score': sum(r.ai_confidence for r in recommendations) / len(recommendations) if recommendations else 0.75,
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write('✨ Created new AI Decanting strategy')
        
        # Clear existing AI opportunities
        deleted_count = await asyncio.to_thread(
            DecantingOpportunity.objects.filter(strategy=strategy).delete
        )
        self.stdout.write(f'🗑️  Cleared {deleted_count[0]} old AI opportunities')
        
        # Create new AI opportunities
        created_count = 0
        for rec in recommendations:
            try:
                # Find the actual item for from_dose
                from apps.items.models import Item
                
                # Look for the item by reconstructing the name
                from_item_name = f"{rec.potion_name}({rec.from_dose})"
                to_item_name = f"{rec.potion_name}({rec.to_dose})"
                
                # Find items with name containing the dose pattern
                from_item = await asyncio.to_thread(
                    lambda: Item.objects.filter(
                        name__icontains=rec.potion_name
                    ).filter(
                        name__icontains=f'({rec.from_dose})'
                    ).first()
                )
                
                if not from_item:
                    self.stdout.write(
                        self.style.WARNING(f'Could not find item for {from_item_name}')
                    )
                    continue
                
                # Calculate estimated hourly profit (conservative)
                hourly_conversions = 30  # Conservative estimate: 30 conversions per hour
                hourly_profit = rec.profit_per_conversion * hourly_conversions
                
                await asyncio.to_thread(
                    DecantingOpportunity.objects.create,
                    strategy=strategy,
                    item_id=from_item.item_id,
                    item_name=rec.potion_name,
                    from_dose=rec.from_dose,
                    to_dose=rec.to_dose,
                    from_dose_price=rec.buy_price,
                    to_dose_price=rec.sell_price,
                    from_dose_volume=100,  # Default volume estimate
                    to_dose_volume=50,     # Default volume estimate
                    profit_per_conversion=rec.profit_per_conversion,
                    profit_per_hour=hourly_profit,
                )
                created_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Failed to save {rec.potion_name}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'💾 Created {created_count} AI-powered opportunities in database')
        )