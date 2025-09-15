"""
Django management command for managing seasonal trading recommendations.

Usage:
    python manage.py seasonal_recommendations --generate
    python manage.py seasonal_recommendations --list-active
    python manage.py seasonal_recommendations --monitor-performance
    python manage.py seasonal_recommendations --cleanup-expired
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

from apps.realtime_engine.models import SeasonalRecommendation, SeasonalPattern, SeasonalEvent
from apps.prices.models import Price

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manage seasonal trading recommendations'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--generate',
            action='store_true',
            help='Generate new seasonal recommendations'
        )
        parser.add_argument(
            '--list-active',
            action='store_true',
            help='List currently active recommendations'
        )
        parser.add_argument(
            '--monitor-performance',
            action='store_true',
            help='Monitor performance of active recommendations'
        )
        parser.add_argument(
            '--cleanup-expired',
            action='store_true',
            help='Clean up expired recommendations'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuous monitoring/generation'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=1800,  # 30 minutes
            help='Interval for continuous mode (seconds, default: 1800)'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.6,
            help='Minimum confidence for generating recommendations (0.0-1.0)'
        )
        parser.add_argument(
            '--max-recommendations',
            type=int,
            default=20,
            help='Maximum number of active recommendations to maintain'
        )
        parser.add_argument(
            '--export-performance',
            action='store_true',
            help='Export performance statistics'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        if options['continuous']:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            if options['generate']:
                asyncio.run(self.generate_recommendations(options))
            elif options['list_active']:
                asyncio.run(self.list_active_recommendations())
            elif options['monitor_performance']:
                asyncio.run(self.monitor_performance(options))
            elif options['cleanup_expired']:
                asyncio.run(self.cleanup_expired_recommendations())
            elif options['continuous']:
                asyncio.run(self.continuous_management(options))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "No action specified. Use --help to see available options."
                    )
                )
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("🛑 Management stopped by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Management failed: {e}"))
            logger.exception("Seasonal recommendations management failed")
    
    async def generate_recommendations(self, options):
        """Generate new seasonal recommendations."""
        self.stdout.write("🎯 Generating seasonal trading recommendations...")
        
        min_confidence = options['min_confidence']
        max_recommendations = options['max_recommendations']
        
        # Get current active recommendations count
        active_count = await sync_to_async(
            SeasonalRecommendation.objects.filter(is_active=True).count
        )()
        
        if active_count >= max_recommendations:
            self.stdout.write(f"📊 Already have {active_count} active recommendations (max: {max_recommendations})")
            return
        
        # Get seasonal patterns with strong signals
        strong_patterns = await sync_to_async(list)(
            SeasonalPattern.objects.filter(
                overall_pattern_strength__gte=min_confidence,
                analysis_timestamp__gte=timezone.now() - timedelta(days=7)  # Recent analysis
            ).select_related('item').order_by('-overall_pattern_strength')[:50]
        )
        
        if not strong_patterns:
            self.stdout.write("📊 No strong seasonal patterns found for recommendations")
            return
        
        generated_count = 0
        skipped_count = 0
        
        for pattern in strong_patterns:
            if generated_count >= (max_recommendations - active_count):
                break
            
            try:
                # Check if we already have active recommendations for this item
                existing = await sync_to_async(
                    SeasonalRecommendation.objects.filter(
                        seasonal_pattern__item=pattern.item,
                        is_active=True
                    ).exists
                )()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Generate recommendation based on pattern
                recommendation = await self._generate_recommendation_from_pattern(pattern)
                
                if recommendation:
                    self.stdout.write(
                        f"   ✅ {pattern.item.name}: {recommendation.recommendation_type} "
                        f"({recommendation.confidence_score:.1%} confidence)"
                    )
                    generated_count += 1
                else:
                    skipped_count += 1
                
            except Exception as e:
                self.stdout.write(f"   ❌ Failed to generate recommendation for {pattern.item.name}: {e}")
                skipped_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Generated {generated_count} new recommendations, skipped {skipped_count}"
            )
        )
    
    async def _generate_recommendation_from_pattern(self, pattern: SeasonalPattern) -> Optional[SeasonalRecommendation]:
        """Generate a recommendation from a seasonal pattern."""
        try:
            current_date = timezone.now().date()
            current_month = current_date.strftime('%B')
            current_day = current_date.strftime('%A')
            
            # Determine recommendation type based on patterns
            rec_type = 'monitor'  # Default
            expected_impact = 0.0
            confidence = pattern.overall_pattern_strength
            reasoning_parts = []
            
            # Check monthly patterns
            if pattern.best_month == current_month:
                rec_type = 'buy'
                expected_impact = 3.0
                reasoning_parts.append(f"Currently in historically strong month ({current_month})")
            elif pattern.worst_month == current_month:
                rec_type = 'sell'
                expected_impact = -2.0
                reasoning_parts.append(f"Currently in historically weak month ({current_month})")
            
            # Check weekly patterns
            weekend_effect = pattern.weekend_effect_pct
            if abs(weekend_effect) >= 2.0:
                if current_date.weekday() >= 4:  # Friday or weekend
                    if weekend_effect > 0:
                        if rec_type == 'monitor':
                            rec_type = 'sell'
                        expected_impact += weekend_effect * 0.5
                        reasoning_parts.append(f"Weekend premium expected ({weekend_effect:+.1f}%)")
                    else:
                        if rec_type == 'monitor':
                            rec_type = 'buy'
                        expected_impact += abs(weekend_effect) * 0.3
                        reasoning_parts.append(f"Weekend discount expected ({weekend_effect:+.1f}%)")
            
            # Check for upcoming events
            upcoming_events = await self._get_upcoming_events_for_item(pattern.item.item_id)
            for event in upcoming_events:
                if event.average_price_impact_pct != 0:
                    event_impact = event.average_price_impact_pct * 0.7  # Moderate the impact
                    expected_impact += event_impact
                    
                    if event_impact > 3.0 and rec_type == 'monitor':
                        rec_type = 'buy'
                    elif event_impact < -3.0 and rec_type == 'monitor':
                        rec_type = 'sell'
                    
                    reasoning_parts.append(f"Upcoming {event.event_name} (impact: {event_impact:+.1f}%)")
            
            # Only create recommendations with meaningful signals
            if abs(expected_impact) < 1.0 and rec_type == 'monitor':
                return None
            
            # Set validity period
            valid_from = current_date
            if rec_type in ['buy', 'sell']:
                valid_until = current_date + timedelta(days=14)  # 2 weeks for trading recs
            else:
                valid_until = current_date + timedelta(days=30)  # 1 month for monitoring
            
            # Create recommendation
            recommendation_text = f"Seasonal analysis suggests {rec_type} opportunity. " + "; ".join(reasoning_parts)
            
            recommendation = await sync_to_async(SeasonalRecommendation.objects.create)(
                seasonal_pattern=pattern,
                recommendation_type=rec_type,
                valid_from=valid_from,
                valid_until=valid_until,
                primary_pattern=pattern.dominant_pattern_type,
                confidence_score=confidence,
                expected_impact_pct=expected_impact,
                suggested_position_size_pct=min(10.0, max(2.0, abs(expected_impact))),  # 2-10% position size
                stop_loss_pct=abs(expected_impact) * 0.5 if rec_type in ['buy', 'sell'] else None,
                take_profit_pct=abs(expected_impact) * 1.5 if rec_type in ['buy', 'sell'] else None,
                max_hold_days=14 if rec_type in ['buy', 'sell'] else 30,
                recommendation_text=recommendation_text,
                supporting_factors=reasoning_parts,
                is_active=True
            )
            
            return recommendation
            
        except Exception as e:
            logger.exception(f"Failed to generate recommendation from pattern {pattern.id}")
            return None
    
    async def _get_upcoming_events_for_item(self, item_id: int) -> List[SeasonalEvent]:
        """Get upcoming events that might affect the item."""
        today = timezone.now().date()
        future_date = today + timedelta(days=30)
        
        events = await sync_to_async(list)(
            SeasonalEvent.objects.filter(
                start_date__range=[today, future_date],
                is_active=True,
                verification_status='verified'
            )
        )
        
        # Filter events relevant to item (simplified logic)
        relevant_events = []
        for event in events:
            if not event.affected_categories:
                continue
            
            # All categories affect all items for now
            if 'all' in event.affected_categories:
                relevant_events.append(event)
            else:
                # In a real implementation, you'd check item category against event categories
                relevant_events.append(event)
        
        return relevant_events
    
    async def list_active_recommendations(self):
        """List currently active recommendations."""
        self.stdout.write("📋 Active Seasonal Recommendations:")
        
        active_recs = await sync_to_async(list)(
            SeasonalRecommendation.objects.filter(is_active=True)
            .select_related('seasonal_pattern__item')
            .order_by('-confidence_score')
        )
        
        if not active_recs:
            self.stdout.write("   No active recommendations found.")
            return
        
        for rec in active_recs:
            status_icon = "🟢" if rec.is_current else "🟡"
            execution_status = "📈 Executed" if rec.is_executed else "⏳ Pending"
            
            self.stdout.write(
                f"   {status_icon} {rec.seasonal_pattern.item.name} - {rec.recommendation_type.upper()}"
            )
            self.stdout.write(
                f"      Confidence: {rec.confidence_score:.1%} | "
                f"Expected: {rec.expected_impact_pct:+.1f}% | "
                f"Days left: {rec.days_remaining} | "
                f"{execution_status}"
            )
            
            if rec.is_executed and rec.current_performance_pct != 0:
                perf_color = "+" if rec.current_performance_pct > 0 else ""
                self.stdout.write(
                    f"      Performance: {perf_color}{rec.current_performance_pct:.1f}%"
                )
            
            self.stdout.write(f"      Reasoning: {rec.recommendation_text[:100]}...")
            self.stdout.write("")
    
    async def monitor_performance(self, options):
        """Monitor performance of active recommendations."""
        self.stdout.write("📊 Monitoring seasonal recommendation performance...")
        
        executed_recs = await sync_to_async(list)(
            SeasonalRecommendation.objects.filter(
                is_executed=True,
                is_active=True
            ).select_related('seasonal_pattern__item')
        )
        
        if not executed_recs:
            self.stdout.write("   No executed recommendations to monitor.")
            return
        
        updated_count = 0
        failed_count = 0
        
        for rec in executed_recs:
            try:
                # Get current price
                current_price = await self._get_current_price(rec.seasonal_pattern.item.item_id)
                
                if current_price is None:
                    self.stdout.write(f"⚠️  No current price data for {rec.seasonal_pattern.item.name}")
                    failed_count += 1
                    continue
                
                # Update performance
                rec.update_performance(current_price)
                
                # Check if should exit
                if rec.should_exit(int(current_price)):
                    self.stdout.write(
                        f"🚨 Exit signal for {rec.seasonal_pattern.item.name}: "
                        f"Current P&L: {rec.current_performance_pct:+.1f}%"
                    )
                
                self.stdout.write(
                    f"   📈 {rec.seasonal_pattern.item.name}: "
                    f"{rec.current_performance_pct:+.1f}% "
                    f"(Max: {rec.max_performance_pct:+.1f}%, Min: {rec.min_performance_pct:+.1f}%)"
                )
                
                updated_count += 1
                
            except Exception as e:
                self.stdout.write(f"❌ Failed to update {rec.seasonal_pattern.item.name}: {e}")
                failed_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Performance monitoring: {updated_count} updated, {failed_count} failed"
            )
        )
        
        # Export performance summary if requested
        if options.get('export_performance'):
            await self._export_performance_summary(executed_recs)
    
    async def _get_current_price(self, item_id: int) -> Optional[float]:
        """Get current price for an item."""
        try:
            recent_price = await sync_to_async(
                Price.objects.filter(item_id=item_id)
                .order_by('-created_at').first
            )()
            
            if recent_price:
                return float(recent_price.high_price)
            
            return None
            
        except Exception as e:
            logger.exception(f"Failed to get current price for item {item_id}")
            return None
    
    async def _export_performance_summary(self, executed_recs: List[SeasonalRecommendation]):
        """Export performance summary for executed recommendations."""
        self.stdout.write("\n📊 Performance Summary:")
        
        if not executed_recs:
            return
        
        # Calculate overall stats
        performances = [rec.current_performance_pct for rec in executed_recs if rec.current_performance_pct != 0]
        
        if performances:
            avg_performance = sum(performances) / len(performances)
            positive_recs = sum(1 for p in performances if p > 0)
            negative_recs = sum(1 for p in performances if p < 0)
            
            self.stdout.write(f"   📈 Average performance: {avg_performance:+.2f}%")
            self.stdout.write(f"   📈 Positive recommendations: {positive_recs}/{len(performances)} ({positive_recs/len(performances)*100:.1f}%)")
            self.stdout.write(f"   📈 Negative recommendations: {negative_recs}/{len(performances)} ({negative_recs/len(performances)*100:.1f}%)")
            
            # Best and worst performers
            best_rec = max(executed_recs, key=lambda x: x.current_performance_pct)
            worst_rec = min(executed_recs, key=lambda x: x.current_performance_pct)
            
            self.stdout.write(f"   🏆 Best performer: {best_rec.seasonal_pattern.item.name} ({best_rec.current_performance_pct:+.1f}%)")
            self.stdout.write(f"   📉 Worst performer: {worst_rec.seasonal_pattern.item.name} ({worst_rec.current_performance_pct:+.1f}%)")
    
    async def cleanup_expired_recommendations(self):
        """Clean up expired recommendations."""
        self.stdout.write("🧹 Cleaning up expired seasonal recommendations...")
        
        today = timezone.now().date()
        
        # Deactivate expired recommendations
        expired_count = await sync_to_async(
            SeasonalRecommendation.objects.filter(
                valid_until__lt=today,
                is_active=True
            ).update
        )(is_active=False)
        
        self.stdout.write(f"   🧹 Deactivated {expired_count} expired recommendations")
        
        # Clean up very old recommendations (older than 90 days)
        old_date = today - timedelta(days=90)
        deleted_count = await sync_to_async(
            SeasonalRecommendation.objects.filter(
                valid_until__lt=old_date,
                is_active=False
            ).delete
        )()
        
        deleted_count = deleted_count[0] if deleted_count else 0
        
        self.stdout.write(f"   🗑️  Deleted {deleted_count} old recommendations (>90 days)")
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Cleanup completed: {expired_count + deleted_count} recommendations processed")
        )
    
    async def continuous_management(self, options):
        """Run continuous recommendation management."""
        interval = options['interval']
        cycle_count = 0
        
        self.stdout.write(f"🔄 Starting continuous recommendation management (interval: {interval}s)")
        
        while self.running:
            try:
                cycle_count += 1
                start_time = timezone.now()
                
                self.stdout.write(f"\n🎯 Management cycle #{cycle_count} starting at {start_time.strftime('%H:%M:%S')}")
                
                # Run all management tasks
                await self.cleanup_expired_recommendations()
                await self.generate_recommendations(options)
                await self.monitor_performance(options)
                
                # Calculate cycle duration
                duration = (timezone.now() - start_time).total_seconds()
                self.stdout.write(f"✅ Cycle #{cycle_count} completed in {duration:.1f}s")
                
                # Wait for next cycle
                if self.running:
                    await asyncio.sleep(interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Management cycle error: {e}"))
                logger.exception("Error in continuous management")
                
                # Wait before retrying
                await asyncio.sleep(min(interval, 300))
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Continuous management completed. {cycle_count} cycles performed."
            )
        )
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.stdout.write(self.style.WARNING(f"🛑 Received signal {signum}, shutting down..."))
        self.running = False