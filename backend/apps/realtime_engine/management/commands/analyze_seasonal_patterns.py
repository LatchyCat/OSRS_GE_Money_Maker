"""
Django management command for analyzing seasonal patterns in OSRS market data.

Usage:
    python manage.py analyze_seasonal_patterns
    python manage.py analyze_seasonal_patterns --items 10344 20011 12424
    python manage.py analyze_seasonal_patterns --continuous --interval 7200
    python manage.py analyze_seasonal_patterns --analysis-types weekly monthly events
"""

import asyncio
import logging
import signal
import sys
from typing import Optional, List
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import async_to_sync, sync_to_async

from services.seasonal_analysis_engine import seasonal_analysis_engine
from apps.realtime_engine.models import SeasonalPattern, SeasonalForecast, SeasonalRecommendation
from apps.items.models import Item

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Analyze seasonal patterns in OSRS market data'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--items',
            nargs='+',
            type=int,
            help='Specific item IDs to analyze (default: analyze top 50 traded items)'
        )
        parser.add_argument(
            '--lookback',
            type=int,
            default=365,
            help='Days to look back for pattern analysis (default: 365)'
        )
        parser.add_argument(
            '--analysis-types',
            nargs='+',
            choices=['weekly', 'monthly', 'yearly', 'events', 'forecasting'],
            default=['weekly', 'monthly', 'yearly', 'events', 'forecasting'],
            help='Types of seasonal analysis to perform'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously with periodic analysis'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=7200,  # 2 hours
            help='Interval between analyses in continuous mode (seconds, default: 7200)'
        )
        parser.add_argument(
            '--save-results',
            action='store_true',
            default=True,
            help='Save results to database (default: True)'
        )
        parser.add_argument(
            '--generate-forecasts',
            action='store_true',
            default=True,
            help='Generate seasonal forecasts (default: True)'
        )
        parser.add_argument(
            '--generate-recommendations',
            action='store_true',
            default=True,
            help='Generate trading recommendations (default: True)'
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
                f"📊 Starting seasonal pattern analysis (lookback: {options['lookback']} days)"
            )
        )
        
        try:
            if options['continuous']:
                # Run continuous analysis
                asyncio.run(self.continuous_analysis(options))
            else:
                # Run single analysis
                asyncio.run(self.single_analysis(options))
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("🛑 Analysis stopped by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Analysis failed: {e}"))
            logger.exception("Seasonal pattern analysis failed")
    
    async def single_analysis(self, options):
        """Run a single seasonal pattern analysis."""
        item_ids = await self._get_item_ids(options.get('items'))
        lookback_days = options['lookback']
        analysis_types = options['analysis_types']
        save_results = options['save_results']
        
        self.stdout.write(f"🔄 Analyzing seasonal patterns for {len(item_ids)} items...")
        
        # Analyze items in batches to manage memory
        batch_size = 10
        successful_analyses = 0
        failed_analyses = 0
        
        for i in range(0, len(item_ids), batch_size):
            batch = item_ids[i:i + batch_size]
            
            self.stdout.write(f"📈 Processing batch {i//batch_size + 1}/{(len(item_ids) + batch_size - 1)//batch_size}...")
            
            # Analyze batch concurrently
            tasks = [
                seasonal_analysis_engine.analyze_seasonal_patterns(
                    item_id, analysis_types, lookback_days
                )
                for item_id in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for item_id, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    self.stdout.write(f"❌ Failed to analyze item {item_id}: {result}")
                    failed_analyses += 1
                    continue
                
                if result.get('error'):
                    self.stdout.write(f"❌ Analysis error for item {item_id}: {result['error']}")
                    failed_analyses += 1
                    continue
                
                # Display brief results
                self.display_brief_results(result)
                
                # Save to database if requested
                if save_results:
                    await self.save_analysis_results(result, options)
                
                successful_analyses += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Seasonal analysis completed: {successful_analyses} successful, {failed_analyses} failed"
            )
        )
    
    async def continuous_analysis(self, options):
        """Run continuous seasonal pattern analysis."""
        interval = options['interval']
        item_ids = await self._get_item_ids(options.get('items'))
        analysis_count = 0
        
        self.stdout.write(f"🔄 Starting continuous seasonal analysis (interval: {interval}s)")
        
        while self.running:
            try:
                analysis_count += 1
                start_time = timezone.now()
                
                self.stdout.write(f"\n📊 Analysis #{analysis_count} starting at {start_time.strftime('%H:%M:%S')}")
                
                # Run analysis for a subset of items each cycle
                cycle_items = item_ids[:20]  # Analyze top 20 items per cycle
                
                successful = 0
                failed = 0
                
                for item_id in cycle_items:
                    try:
                        result = await seasonal_analysis_engine.analyze_seasonal_patterns(
                            item_id, options['analysis_types'], options['lookback']
                        )
                        
                        if result.get('error'):
                            failed += 1
                            continue
                        
                        # Save results if enabled
                        if options['save_results']:
                            await self.save_analysis_results(result, options)
                        
                        successful += 1
                        
                    except Exception as e:
                        self.stdout.write(f"❌ Error analyzing item {item_id}: {e}")
                        failed += 1
                
                # Calculate analysis duration
                duration = (timezone.now() - start_time).total_seconds()
                self.stdout.write(
                    f"✅ Analysis #{analysis_count} completed in {duration:.1f}s: "
                    f"{successful} successful, {failed} failed"
                )
                
                # Wait for next analysis
                if self.running:
                    await asyncio.sleep(interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Analysis error: {e}"))
                logger.exception("Error in continuous seasonal analysis")
                
                # Wait before retrying
                await asyncio.sleep(min(interval, 300))
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Continuous analysis completed. {analysis_count} analyses performed."
            )
        )
    
    async def _get_item_ids(self, specified_items: Optional[List[int]]) -> List[int]:
        """Get list of item IDs to analyze."""
        if specified_items:
            return specified_items
        
        # Get top traded items if none specified
        try:
            from apps.prices.models import Price
            
            # Get items with recent trading activity
            recent_date = timezone.now() - timedelta(days=7)
            
            top_items = await sync_to_async(list)(
                Price.objects.filter(
                    created_at__gte=recent_date,
                    volume__gt=0
                ).values('item_id').distinct()[:50]
            )
            
            return [item['item_id'] for item in top_items]
            
        except Exception as e:
            self.stdout.write(f"⚠️  Failed to get top items, using fallback: {e}")
            # Fallback to some common items
            return [10344, 20011, 12424, 11694, 21003]
    
    def display_brief_results(self, result: dict):
        """Display brief analysis results."""
        item_id = result.get('item_id')
        strengths = result.get('strength_scores', {})
        recommendations_count = len(result.get('recommendations', []))
        
        overall_strength = strengths.get('overall', 0)
        strength_color = 'green' if overall_strength > 0.6 else 'orange' if overall_strength > 0.3 else 'red'
        
        # Get strongest pattern type
        pattern_strengths = {k: v for k, v in strengths.items() if k != 'overall'}
        strongest_pattern = max(pattern_strengths.items(), key=lambda x: x[1])[0] if pattern_strengths else 'none'
        
        self.stdout.write(
            f"   📈 Item {item_id}: {overall_strength:.1%} strength "
            f"(dominant: {strongest_pattern}, {recommendations_count} recommendations)"
        )
    
    async def save_analysis_results(self, result: dict, options: dict):
        """Save seasonal analysis results to database."""
        try:
            item_id = result['item_id']
            
            # Get item object
            try:
                item = await sync_to_async(Item.objects.get)(item_id=item_id)
            except Item.DoesNotExist:
                self.stdout.write(f"⚠️  Item {item_id} not found in database")
                return
            
            # Save main seasonal pattern
            patterns = result.get('patterns', {})
            strengths = result.get('strength_scores', {})
            
            # Extract pattern data
            weekly_data = patterns.get('weekly', {})
            monthly_data = patterns.get('monthly', {})
            yearly_data = patterns.get('yearly', {})
            events_data = patterns.get('events', {})
            forecasts_data = result.get('forecasts', {})
            
            seasonal_pattern = await sync_to_async(SeasonalPattern.objects.create)(
                item=item,
                lookback_days=result.get('lookback_days', 365),
                data_points_analyzed=result.get('data_points', 0),
                analysis_types=options['analysis_types'],
                
                # Pattern strengths
                weekly_pattern_strength=strengths.get('weekly', 0),
                monthly_pattern_strength=strengths.get('monthly', 0),
                yearly_pattern_strength=strengths.get('yearly', 0),
                event_pattern_strength=strengths.get('events', 0),
                overall_pattern_strength=strengths.get('overall', 0),
                
                # Weekly patterns
                weekend_effect_pct=weekly_data.get('weekend_effect', {}).get('price_premium_pct', 0),
                best_day_of_week=self._get_best_day(weekly_data.get('day_of_week_effects', {})),
                worst_day_of_week=self._get_worst_day(weekly_data.get('day_of_week_effects', {})),
                day_of_week_effects=weekly_data.get('day_of_week_effects', {}),
                
                # Monthly patterns
                best_month=self._get_best_month(monthly_data.get('month_effects', {})),
                worst_month=self._get_worst_month(monthly_data.get('month_effects', {})),
                monthly_effects=monthly_data.get('month_effects', {}),
                quarterly_effects=monthly_data.get('quarterly_effects', {}),
                
                # Events and forecasting
                detected_events=events_data.get('detected_events', []),
                event_impact_analysis=events_data.get('event_impact_analysis', {}),
                short_term_forecast=forecasts_data.get('short_term', {}),
                medium_term_forecast=forecasts_data.get('medium_term', {}),
                forecast_confidence=0.5,  # Would be calculated from forecasts
                
                # Recommendations
                recommendations=result.get('recommendations', []),
                confidence_score=0.7,  # Would be calculated from analysis quality
                analysis_duration_seconds=(timezone.now() - result['analysis_timestamp']).total_seconds()
            )
            
            # Generate forecasts if enabled
            if options['generate_forecasts'] and forecasts_data:
                await self._save_forecasts(seasonal_pattern, forecasts_data)
            
            # Generate recommendations if enabled
            if options['generate_recommendations'] and result.get('recommendations'):
                await self._save_recommendations(seasonal_pattern, result['recommendations'])
            
        except Exception as e:
            self.stdout.write(f"⚠️  Failed to save analysis for item {item_id}: {e}")
            logger.exception(f"Failed to save seasonal analysis for item {item_id}")
    
    async def _save_forecasts(self, seasonal_pattern: SeasonalPattern, forecasts_data: dict):
        """Save seasonal forecasts."""
        try:
            base_date = timezone.now().date()
            
            # Save short-term forecasts (next 7 days)
            short_term = forecasts_data.get('short_term', {})
            for day_key, forecast in short_term.items():
                if 'day_' in day_key:
                    day_num = int(day_key.split('_')[1])
                    target_date = base_date + timedelta(days=day_num)
                    
                    await sync_to_async(SeasonalForecast.objects.get_or_create)(
                        seasonal_pattern=seasonal_pattern,
                        horizon='7d',
                        target_date=target_date,
                        defaults={
                            'forecasted_price': forecast.get('forecasted_price', 0),
                            'confidence_level': 0.8,
                            'lower_bound': forecast.get('forecasted_price', 0) * 0.95,
                            'upper_bound': forecast.get('forecasted_price', 0) * 1.05,
                            'base_price': forecast.get('forecasted_price', 0),
                            'seasonal_factor': forecast.get('seasonal_factor', 1.0),
                            'trend_adjustment': forecast.get('trend_adjustment', 0),
                            'primary_pattern_type': 'weekly',
                            'pattern_strength': 0.6,
                        }
                    )
            
            # Save medium-term forecasts (next few months)
            medium_term = forecasts_data.get('medium_term', {})
            for month_key, forecast in medium_term.items():
                if 'month_' in month_key:
                    month_num = int(month_key.split('_')[1])
                    target_date = base_date + timedelta(days=month_num * 30)
                    
                    await sync_to_async(SeasonalForecast.objects.get_or_create)(
                        seasonal_pattern=seasonal_pattern,
                        horizon='30d',
                        target_date=target_date,
                        defaults={
                            'forecasted_price': forecast.get('forecasted_price', 0),
                            'confidence_level': 0.7,
                            'lower_bound': forecast.get('forecasted_price', 0) * 0.9,
                            'upper_bound': forecast.get('forecasted_price', 0) * 1.1,
                            'base_price': forecast.get('forecasted_price', 0),
                            'seasonal_factor': forecast.get('seasonal_factor', 1.0),
                            'trend_adjustment': forecast.get('trend_adjustment', 0),
                            'primary_pattern_type': 'monthly',
                            'pattern_strength': 0.5,
                        }
                    )
                    
        except Exception as e:
            logger.exception("Failed to save seasonal forecasts")
    
    async def _save_recommendations(self, seasonal_pattern: SeasonalPattern, recommendations: List[str]):
        """Save seasonal recommendations."""
        try:
            base_date = timezone.now().date()
            
            for i, rec_text in enumerate(recommendations[:3]):  # Save top 3 recommendations
                # Parse recommendation type from text
                rec_type = 'monitor'  # Default
                if 'buy' in rec_text.lower():
                    rec_type = 'buy'
                elif 'sell' in rec_text.lower():
                    rec_type = 'sell'
                elif 'avoid' in rec_text.lower():
                    rec_type = 'avoid'
                
                # Set validity period
                valid_from = base_date
                valid_until = base_date + timedelta(days=30)  # Valid for 30 days
                
                await sync_to_async(SeasonalRecommendation.objects.create)(
                    seasonal_pattern=seasonal_pattern,
                    recommendation_type=rec_type,
                    valid_from=valid_from,
                    valid_until=valid_until,
                    primary_pattern='seasonal',
                    confidence_score=0.7,
                    expected_impact_pct=2.0,  # Default expected impact
                    suggested_position_size_pct=5.0,
                    max_hold_days=30,
                    recommendation_text=rec_text,
                    supporting_factors=['seasonal_pattern_analysis'],
                    is_active=True
                )
                
        except Exception as e:
            logger.exception("Failed to save seasonal recommendations")
    
    def _get_best_day(self, day_effects: dict) -> str:
        """Get the best day of week from effects."""
        if not day_effects:
            return ''
        
        best_day_name = max(day_effects.items(), key=lambda x: x[1].get('price_effect_pct', 0))[0]
        return best_day_name
    
    def _get_worst_day(self, day_effects: dict) -> str:
        """Get the worst day of week from effects."""
        if not day_effects:
            return ''
        
        worst_day_name = min(day_effects.items(), key=lambda x: x[1].get('price_effect_pct', 0))[0]
        return worst_day_name
    
    def _get_best_month(self, month_effects: dict) -> str:
        """Get the best month from effects."""
        if not month_effects:
            return ''
        
        best_month = max(month_effects.items(), key=lambda x: x[1].get('price_effect_pct', 0))[0]
        return best_month
    
    def _get_worst_month(self, month_effects: dict) -> str:
        """Get the worst month from effects."""
        if not month_effects:
            return ''
        
        worst_month = min(month_effects.items(), key=lambda x: x[1].get('price_effect_pct', 0))[0]
        return worst_month
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.stdout.write(self.style.WARNING(f"🛑 Received signal {signum}, shutting down..."))
        self.running = False