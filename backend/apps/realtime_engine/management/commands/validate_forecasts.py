"""
Django management command for validating seasonal forecasts against actual market data.

Usage:
    python manage.py validate_forecasts
    python manage.py validate_forecasts --days-back 7
    python manage.py validate_forecasts --continuous --interval 3600
    python manage.py validate_forecasts --export-accuracy-stats
"""

import asyncio
import logging
import signal
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Avg, Count, Q
from asgiref.sync import sync_to_async

from apps.realtime_engine.models import SeasonalForecast, SeasonalPattern
from apps.prices.models import Price

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Validate seasonal forecasts against actual market data'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days-back',
            type=int,
            default=30,
            help='Days back to validate forecasts (default: 30)'
        )
        parser.add_argument(
            '--forecast-ids',
            nargs='+',
            type=int,
            help='Specific forecast IDs to validate'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuous validation with periodic updates'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=3600,  # 1 hour
            help='Interval between validations in continuous mode (seconds, default: 3600)'
        )
        parser.add_argument(
            '--export-accuracy-stats',
            action='store_true',
            help='Export accuracy statistics to console'
        )
        parser.add_argument(
            '--horizon',
            choices=['1d', '3d', '7d', '14d', '30d', '60d', '90d'],
            help='Validate forecasts for specific horizon only'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.0,
            help='Minimum confidence level to validate (0.0-1.0)'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        if options['continuous']:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.stdout.write(
            self.style.SUCCESS("🔍 Starting seasonal forecast validation...")
        )
        
        try:
            if options['continuous']:
                asyncio.run(self.continuous_validation(options))
            else:
                asyncio.run(self.single_validation(options))
                
            if options['export_accuracy_stats']:
                asyncio.run(self.export_accuracy_stats(options))
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("🛑 Validation stopped by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Validation failed: {e}"))
            logger.exception("Forecast validation failed")
    
    async def single_validation(self, options):
        """Run a single validation cycle."""
        days_back = options['days_back']
        forecast_ids = options.get('forecast_ids')
        horizon = options.get('horizon')
        min_confidence = options['min_confidence']
        
        # Get forecasts to validate
        forecasts = await self._get_forecasts_to_validate(
            days_back, forecast_ids, horizon, min_confidence
        )
        
        if not forecasts:
            self.stdout.write("📊 No forecasts found for validation.")
            return
        
        self.stdout.write(f"📊 Validating {len(forecasts)} forecasts...")
        
        validated_count = 0
        failed_count = 0
        
        for forecast in forecasts:
            try:
                # Get actual price for the target date
                actual_price = await self._get_actual_price(
                    forecast.seasonal_pattern.item.item_id, 
                    forecast.target_date
                )
                
                if actual_price is None:
                    self.stdout.write(f"⚠️  No price data for forecast {forecast.id} on {forecast.target_date}")
                    failed_count += 1
                    continue
                
                # Validate the forecast
                await self._validate_forecast(forecast, actual_price)
                
                # Display results
                accuracy = forecast.forecast_accuracy
                within_ci = "✅" if forecast.is_within_confidence_interval else "❌"
                
                self.stdout.write(
                    f"   📈 {forecast.seasonal_pattern.item.name} ({forecast.horizon}): "
                    f"Accuracy {accuracy:.1f}% {within_ci}"
                )
                
                validated_count += 1
                
            except Exception as e:
                self.stdout.write(f"❌ Failed to validate forecast {forecast.id}: {e}")
                failed_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Validation completed: {validated_count} validated, {failed_count} failed"
            )
        )
    
    async def continuous_validation(self, options):
        """Run continuous forecast validation."""
        interval = options['interval']
        validation_count = 0
        
        self.stdout.write(f"🔄 Starting continuous forecast validation (interval: {interval}s)")
        
        while self.running:
            try:
                validation_count += 1
                start_time = timezone.now()
                
                self.stdout.write(f"\n🔍 Validation #{validation_count} starting at {start_time.strftime('%H:%M:%S')}")
                
                # Run validation
                await self.single_validation(options)
                
                # Calculate validation duration
                duration = (timezone.now() - start_time).total_seconds()
                self.stdout.write(f"✅ Validation #{validation_count} completed in {duration:.1f}s")
                
                # Wait for next validation
                if self.running:
                    await asyncio.sleep(interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Validation error: {e}"))
                logger.exception("Error in continuous validation")
                
                # Wait before retrying
                await asyncio.sleep(min(interval, 300))
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Continuous validation completed. {validation_count} validations performed."
            )
        )
    
    async def _get_forecasts_to_validate(
        self, 
        days_back: int, 
        forecast_ids: Optional[List[int]], 
        horizon: Optional[str],
        min_confidence: float
    ) -> List[SeasonalForecast]:
        """Get forecasts that need validation."""
        
        if forecast_ids:
            # Validate specific forecasts
            forecasts = await sync_to_async(list)(
                SeasonalForecast.objects.filter(
                    id__in=forecast_ids,
                    actual_price__isnull=True  # Only unvalidated
                ).select_related('seasonal_pattern__item')
            )
        else:
            # Get forecasts within date range
            start_date = timezone.now().date() - timedelta(days=days_back)
            end_date = timezone.now().date()
            
            query = Q(
                target_date__range=[start_date, end_date],
                actual_price__isnull=True,  # Only unvalidated
                confidence_level__gte=min_confidence
            )
            
            if horizon:
                query &= Q(horizon=horizon)
            
            forecasts = await sync_to_async(list)(
                SeasonalForecast.objects.filter(query)
                .select_related('seasonal_pattern__item')
                .order_by('target_date')
            )
        
        return forecasts
    
    async def _get_actual_price(self, item_id: int, target_date: date) -> Optional[float]:
        """Get actual price for an item on the target date."""
        try:
            # Look for price data on the target date (within +/- 1 day tolerance)
            start_date = datetime.combine(target_date - timedelta(days=1), datetime.min.time())
            end_date = datetime.combine(target_date + timedelta(days=1), datetime.max.time())
            
            # Get the closest price to the target date
            price_record = await sync_to_async(
                Price.objects.filter(
                    item_id=item_id,
                    created_at__range=[start_date, end_date]
                ).order_by('created_at').last
            )()
            
            if price_record:
                return float(price_record.high_price)
            
            return None
            
        except Exception as e:
            logger.exception(f"Failed to get actual price for item {item_id} on {target_date}")
            return None
    
    async def _validate_forecast(self, forecast: SeasonalForecast, actual_price: float):
        """Validate a forecast against actual price."""
        try:
            # Update forecast with actual data
            forecast.actual_price = actual_price
            forecast.validation_date = timezone.now()
            
            # Calculate errors
            forecast.absolute_error = abs(actual_price - forecast.forecasted_price)
            if forecast.forecasted_price > 0:
                forecast.percentage_error = (
                    (actual_price - forecast.forecasted_price) / forecast.forecasted_price
                ) * 100
            else:
                forecast.percentage_error = 0
            
            # Check if within confidence interval
            forecast.is_within_confidence_interval = (
                forecast.lower_bound <= actual_price <= forecast.upper_bound
            )
            
            # Save updates
            await sync_to_async(forecast.save)()
            
        except Exception as e:
            logger.exception(f"Failed to validate forecast {forecast.id}")
            raise
    
    async def export_accuracy_stats(self, options):
        """Export accuracy statistics."""
        self.stdout.write("\n📊 Forecast Accuracy Statistics:")
        
        days_back = options['days_back']
        horizon = options.get('horizon')
        
        # Get validated forecasts
        cutoff_date = timezone.now() - timedelta(days=days_back)
        
        query = Q(
            validation_date__gte=cutoff_date,
            actual_price__isnull=False
        )
        
        if horizon:
            query &= Q(horizon=horizon)
        
        validated_forecasts = await sync_to_async(list)(
            SeasonalForecast.objects.filter(query)
        )
        
        if not validated_forecasts:
            self.stdout.write("   No validated forecasts found for statistics.")
            return
        
        # Calculate overall statistics
        total_forecasts = len(validated_forecasts)
        errors = [abs(f.percentage_error) for f in validated_forecasts if f.percentage_error is not None]
        ci_hits = [f.is_within_confidence_interval for f in validated_forecasts if f.is_within_confidence_interval is not None]
        
        if errors:
            mean_error = sum(errors) / len(errors)
            median_error = sorted(errors)[len(errors) // 2]
            mean_accuracy = 100 - mean_error
        else:
            mean_error = median_error = mean_accuracy = 0
        
        ci_hit_rate = (sum(ci_hits) / len(ci_hits)) * 100 if ci_hits else 0
        
        self.stdout.write(f"   📈 Total forecasts validated: {total_forecasts}")
        self.stdout.write(f"   📈 Mean absolute error: {mean_error:.2f}%")
        self.stdout.write(f"   📈 Median absolute error: {median_error:.2f}%")
        self.stdout.write(f"   📈 Mean accuracy: {mean_accuracy:.2f}%")
        self.stdout.write(f"   📈 Confidence interval hit rate: {ci_hit_rate:.1f}%")
        
        # Accuracy by horizon
        horizons = ['1d', '3d', '7d', '14d', '30d', '60d', '90d']
        
        self.stdout.write("\n   📊 Accuracy by forecast horizon:")
        
        for h in horizons:
            horizon_forecasts = [f for f in validated_forecasts if f.horizon == h]
            
            if horizon_forecasts:
                horizon_errors = [
                    abs(f.percentage_error) for f in horizon_forecasts 
                    if f.percentage_error is not None
                ]
                
                if horizon_errors:
                    horizon_accuracy = 100 - (sum(horizon_errors) / len(horizon_errors))
                    self.stdout.write(f"      {h:>3s}: {horizon_accuracy:.1f}% accuracy ({len(horizon_forecasts)} forecasts)")
        
        # Top performing patterns
        self.stdout.write("\n   🏆 Top performing seasonal patterns:")
        
        pattern_performance = {}
        for forecast in validated_forecasts:
            pattern_id = forecast.seasonal_pattern_id
            if pattern_id not in pattern_performance:
                pattern_performance[pattern_id] = []
            
            if forecast.percentage_error is not None:
                accuracy = 100 - abs(forecast.percentage_error)
                pattern_performance[pattern_id].append(accuracy)
        
        # Calculate average accuracy per pattern
        pattern_averages = {}
        for pattern_id, accuracies in pattern_performance.items():
            if len(accuracies) >= 3:  # Minimum 3 forecasts for meaningful stats
                avg_accuracy = sum(accuracies) / len(accuracies)
                pattern_averages[pattern_id] = (avg_accuracy, len(accuracies))
        
        # Sort by accuracy and show top 5
        top_patterns = sorted(pattern_averages.items(), key=lambda x: x[1][0], reverse=True)[:5]
        
        for i, (pattern_id, (accuracy, count)) in enumerate(top_patterns, 1):
            try:
                pattern = await sync_to_async(SeasonalPattern.objects.select_related('item').get)(id=pattern_id)
                self.stdout.write(
                    f"      {i}. {pattern.item.name}: {accuracy:.1f}% avg accuracy ({count} forecasts)"
                )
            except SeasonalPattern.DoesNotExist:
                continue
        
        # Recent forecast performance trend
        self.stdout.write("\n   📈 Recent forecast performance (last 7 days):")
        
        recent_date = timezone.now() - timedelta(days=7)
        recent_forecasts = [f for f in validated_forecasts if f.validation_date >= recent_date]
        
        if recent_forecasts:
            recent_errors = [
                abs(f.percentage_error) for f in recent_forecasts 
                if f.percentage_error is not None
            ]
            
            if recent_errors:
                recent_accuracy = 100 - (sum(recent_errors) / len(recent_errors))
                self.stdout.write(f"      Recent accuracy: {recent_accuracy:.1f}% ({len(recent_forecasts)} forecasts)")
            else:
                self.stdout.write("      No error data available for recent forecasts")
        else:
            self.stdout.write("      No recent forecasts validated")
        
        self.stdout.write("")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.stdout.write(self.style.WARNING(f"🛑 Received signal {signum}, shutting down..."))
        self.running = False