"""
Django management command for generating price predictions using Ollama and statistical models.

Usage:
    python manage.py predict_prices
    python manage.py predict_prices --items 10344 20011 12424
    python manage.py predict_prices --continuous --interval 1800
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

from services.price_prediction_engine import price_prediction_engine
from apps.realtime_engine.models import PricePrediction
from apps.items.models import Item

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate AI/ML price predictions for OSRS items'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--items',
            nargs='+',
            type=int,
            help='Specific item IDs to generate predictions for'
        )
        parser.add_argument(
            '--horizon',
            choices=['1h', '4h', '24h', 'all'],
            default='all',
            help='Prediction time horizon (default: all)'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously with periodic predictions'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=1800,  # 30 minutes
            help='Interval between predictions in continuous mode (seconds, default: 1800)'
        )
        parser.add_argument(
            '--save-to-db',
            action='store_true',
            default=True,
            help='Save predictions to database (default: True)'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.3,
            help='Minimum confidence threshold for saving predictions (default: 0.3)'
        )
        parser.add_argument(
            '--max-items',
            type=int,
            default=50,
            help='Maximum number of items to predict (default: 50)'
        )
        parser.add_argument(
            '--test-ollama',
            action='store_true',
            help='Test Ollama connection before running predictions'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.running = True
        
        # Test Ollama connection if requested
        if options['test_ollama']:
            self.test_ollama_connection()
        
        # Setup signal handlers for graceful shutdown
        if options['continuous']:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"🔮 Starting price predictions (horizon: {options['horizon']})"
            )
        )
        
        try:
            if options['continuous']:
                # Run continuous predictions
                asyncio.run(self.continuous_predictions(options))
            else:
                # Run single prediction batch
                asyncio.run(self.single_prediction_batch(options))
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("🛑 Predictions stopped by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Predictions failed: {e}"))
            logger.exception("Price predictions failed")
    
    def test_ollama_connection(self):
        """Test connection to Ollama."""
        self.stdout.write("🔄 Testing Ollama connection...")
        
        try:
            import aiohttp
            import asyncio
            
            async def test_connection():
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "http://localhost:11434/api/generate",
                            json={
                                "model": "llama3.2:3b",
                                "prompt": "Test connection",
                                "stream": False,
                                "options": {"max_tokens": 10}
                            },
                            timeout=10
                        ) as response:
                            if response.status == 200:
                                self.stdout.write(self.style.SUCCESS("✅ Ollama connection successful"))
                                return True
                            else:
                                self.stdout.write(self.style.ERROR(f"❌ Ollama returned status {response.status}"))
                                return False
                                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Ollama connection failed: {e}"))
                    self.stdout.write("💡 Make sure Ollama is running: ollama serve")
                    return False
            
            success = asyncio.run(test_connection())
            if not success:
                self.stdout.write(self.style.WARNING("⚠️  Continuing without Ollama (statistical predictions only)"))
            
        except ImportError:
            self.stdout.write(self.style.WARNING("⚠️  aiohttp not available for Ollama testing"))
    
    async def single_prediction_batch(self, options):
        """Run a single batch of price predictions."""
        item_ids = options.get('items')
        horizon = options['horizon']
        save_to_db = options['save_to_db']
        min_confidence = options['min_confidence']
        max_items = options['max_items']
        
        # Get items to predict
        if item_ids:
            self.stdout.write(f"🎯 Predicting prices for {len(item_ids)} specific items")
        else:
            self.stdout.write(f"🔄 Getting top {max_items} items for predictions...")
            item_ids = await self.get_predictable_items(max_items)
            self.stdout.write(f"📊 Selected {len(item_ids)} items for prediction")
        
        if not item_ids:
            self.stdout.write(self.style.WARNING("⚠️  No items found for prediction"))
            return
        
        # Generate predictions
        self.stdout.write("🔮 Generating price predictions...")
        start_time = timezone.now()
        
        results = await price_prediction_engine.predict_item_prices(item_ids, horizon)
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        if results.get('error'):
            self.stdout.write(self.style.ERROR(f"❌ Prediction failed: {results['error']}"))
            return
        
        # Display results
        self.display_prediction_results(results, duration)
        
        # Save to database
        if save_to_db:
            await self.save_predictions_to_db(results, min_confidence)
        
        self.stdout.write(self.style.SUCCESS("✅ Price predictions completed"))
    
    async def continuous_predictions(self, options):
        """Run continuous price predictions."""
        interval = options['interval']
        horizon = options['horizon']
        save_to_db = options['save_to_db']
        min_confidence = options['min_confidence']
        max_items = options['max_items']
        
        prediction_count = 0
        
        self.stdout.write(f"🔄 Starting continuous predictions (interval: {interval}s)")
        
        while self.running:
            try:
                prediction_count += 1
                start_time = timezone.now()
                
                self.stdout.write(f"\n🔮 Prediction batch #{prediction_count} starting at {start_time.strftime('%H:%M:%S')}")
                
                # Get items for this batch
                item_ids = await self.get_predictable_items(max_items)
                
                if not item_ids:
                    self.stdout.write("⚠️  No items available for prediction")
                    await asyncio.sleep(interval)
                    continue
                
                # Generate predictions
                results = await price_prediction_engine.predict_item_prices(item_ids, horizon)
                
                if results.get('error'):
                    self.stdout.write(self.style.ERROR(f"❌ Batch failed: {results['error']}"))
                else:
                    # Brief results display
                    successful = results['successful_predictions']
                    failed = results['failed_predictions']
                    
                    self.stdout.write(f"📊 Batch completed: {successful} successful, {failed} failed")
                    
                    if results.get('predictions'):
                        # Show high confidence predictions
                        high_conf_predictions = [
                            p for p in results['predictions']
                            if p.get('predictions', {}).get('24h', {}).get('confidence', 0) > 0.7
                        ]
                        
                        if high_conf_predictions:
                            self.stdout.write(f"🎯 {len(high_conf_predictions)} high-confidence predictions:")
                            for pred in high_conf_predictions[:3]:  # Show top 3
                                change = pred['predictions']['24h']['change_pct']
                                conf = pred['predictions']['24h']['confidence']
                                self.stdout.write(f"   • {pred['item_name']}: {change:+.1f}% (conf: {conf:.1%})")
                    
                    # Show AI analysis if available
                    if results.get('market_context', {}).get('ai_analysis'):
                        ai_analysis = results['market_context']['ai_analysis'][:100]  # First 100 chars
                        self.stdout.write(f"🤖 AI Analysis: {ai_analysis}...")
                    
                    # Save to database
                    if save_to_db:
                        await self.save_predictions_to_db(results, min_confidence)
                
                # Calculate batch duration
                batch_duration = (timezone.now() - start_time).total_seconds()
                self.stdout.write(f"✅ Batch #{prediction_count} completed in {batch_duration:.1f}s")
                
                # Wait for next batch
                if self.running:
                    await asyncio.sleep(interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Batch error: {e}"))
                logger.exception("Error in continuous predictions")
                
                # Wait before retrying
                await asyncio.sleep(min(interval, 300))  # Max 5 minutes
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Continuous predictions completed. {prediction_count} batches processed."
            )
        )
    
    def display_prediction_results(self, results: dict, duration: float):
        """Display prediction results."""
        self.stdout.write(f"\n🔮 Price Prediction Results (completed in {duration:.1f}s):")
        self.stdout.write(f"   • Successful predictions: {results['successful_predictions']}")
        self.stdout.write(f"   • Failed predictions: {results['failed_predictions']}")
        
        # Show summary statistics
        summary = results.get('prediction_summary', {})
        if summary:
            trend_dist = summary.get('trend_distribution', {})
            self.stdout.write(f"   • Trend distribution: {trend_dist.get('bullish', 0)} bull, {trend_dist.get('bearish', 0)} bear, {trend_dist.get('neutral', 0)} neutral")
            
            conf_stats = summary.get('confidence_stats', {})
            if conf_stats:
                self.stdout.write(f"   • Average confidence: 24h={conf_stats.get('24h_avg', 0):.1%}")
        
        # Show market context
        market_context = results.get('market_context', {})
        if market_context.get('ai_analysis'):
            self.stdout.write(f"   • AI Market Analysis: {market_context['ai_analysis']}")
        
        # Show top predictions
        predictions = results.get('predictions', [])
        if predictions:
            self.stdout.write("\n📈 Top Predictions:")
            
            # Sort by 24h confidence
            sorted_predictions = sorted(
                predictions, 
                key=lambda x: x.get('predictions', {}).get('24h', {}).get('confidence', 0), 
                reverse=True
            )[:5]
            
            for pred in sorted_predictions:
                pred_24h = pred.get('predictions', {}).get('24h', {})
                change_pct = pred_24h.get('change_pct', 0)
                confidence = pred_24h.get('confidence', 0)
                
                self.stdout.write(
                    f"   • {pred['item_name']}: {change_pct:+.1f}% "
                    f"(confidence: {confidence:.1%}, trend: {pred['trend_direction']})"
                )
    
    async def save_predictions_to_db(self, results: dict, min_confidence: float):
        """Save predictions to database."""
        try:
            predictions = results.get('predictions', [])
            saved_count = 0
            
            for pred_data in predictions:
                # Check confidence threshold
                conf_24h = pred_data.get('predictions', {}).get('24h', {}).get('confidence', 0)
                if conf_24h < min_confidence:
                    continue
                
                try:
                    # Get item
                    item = await sync_to_async(Item.objects.get)(item_id=pred_data['item_id'])
                    
                    # Create prediction record
                    prediction = await sync_to_async(PricePrediction.objects.create)(
                        item=item,
                        current_price=pred_data['current_price'],
                        predicted_price_1h=pred_data['predictions']['1h']['price'],
                        predicted_price_4h=pred_data['predictions']['4h']['price'],
                        predicted_price_24h=pred_data['predictions']['24h']['price'],
                        confidence_1h=pred_data['predictions']['1h']['confidence'],
                        confidence_4h=pred_data['predictions']['4h']['confidence'],
                        confidence_24h=pred_data['predictions']['24h']['confidence'],
                        trend_direction=pred_data['trend_direction'],
                        prediction_factors=pred_data['prediction_factors'],
                        model_version='statistical_v1',
                        prediction_method='statistical_ensemble_ollama'
                    )
                    
                    saved_count += 1
                    
                except Item.DoesNotExist:
                    self.stdout.write(f"⚠️  Item {pred_data['item_id']} not found")
                except Exception as e:
                    self.stdout.write(f"⚠️  Failed to save prediction for {pred_data['item_name']}: {e}")
            
            self.stdout.write(f"💾 Saved {saved_count} predictions to database")
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️  Failed to save predictions: {e}"))
    
    async def get_predictable_items(self, max_items: int) -> List[int]:
        """Get list of items suitable for prediction."""
        try:
            # Get items with recent price data and profit calculations
            items = await sync_to_async(list)(
                Item.objects.filter(
                    profit_calc__isnull=False,
                    prices__created_at__gte=timezone.now() - timedelta(hours=24)
                ).distinct().values_list('item_id', flat=True)[:max_items]
            )
            
            return list(items)
            
        except Exception as e:
            self.stdout.write(f"⚠️  Error getting predictable items: {e}")
            return []
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.stdout.write(self.style.WARNING(f"🛑 Received signal {signum}, shutting down..."))
        self.running = False