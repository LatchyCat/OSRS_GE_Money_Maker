"""
Django management command for running sentiment analysis on OSRS news and updates.

Usage:
    python manage.py analyze_sentiment
    python manage.py analyze_sentiment --items 10344 20011 12424
    python manage.py analyze_sentiment --continuous --interval 3600
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

from services.news_sentiment_analyzer import news_sentiment_analyzer
from apps.realtime_engine.models import SentimentAnalysis, ItemSentiment
from apps.items.models import Item

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Analyze sentiment from OSRS news and community sources'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--lookback',
            type=int,
            default=24,
            help='Hours to look back for news analysis (default: 24)'
        )
        parser.add_argument(
            '--items',
            nargs='+',
            type=int,
            help='Specific item IDs to analyze sentiment for'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously with periodic analysis'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=3600,  # 1 hour
            help='Interval between analyses in continuous mode (seconds, default: 3600)'
        )
        parser.add_argument(
            '--source',
            choices=['all', 'official_news', 'official_updates', 'reddit'],
            default='all',
            help='News source to analyze (default: all)'
        )
        parser.add_argument(
            '--save-results',
            action='store_true',
            default=True,
            help='Save results to database (default: True)'
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
                f"🔍 Starting sentiment analysis (lookback: {options['lookback']}h)"
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
            logger.exception("Sentiment analysis failed")
    
    async def single_analysis(self, options):
        """Run a single sentiment analysis."""
        lookback_hours = options['lookback']
        item_ids = options.get('items')
        save_results = options['save_results']
        
        self.stdout.write("🔄 Running market sentiment analysis...")
        
        # Run general market sentiment analysis
        market_sentiment = await news_sentiment_analyzer.analyze_market_sentiment(lookback_hours)
        
        if market_sentiment.get('error'):
            self.stdout.write(self.style.ERROR(f"❌ Market analysis failed: {market_sentiment['error']}"))
        else:
            # Display results
            self.display_market_sentiment(market_sentiment)
            
            # Save to database if requested
            if save_results:
                await self.save_market_sentiment(market_sentiment)
        
        # Run item-specific analysis if requested
        if item_ids:
            self.stdout.write(f"\n🔄 Running item-specific analysis for {len(item_ids)} items...")
            
            item_sentiment = await news_sentiment_analyzer.analyze_item_specific_sentiment(item_ids)
            
            if item_sentiment.get('error'):
                self.stdout.write(self.style.ERROR(f"❌ Item analysis failed: {item_sentiment['error']}"))
            else:
                self.display_item_sentiment(item_sentiment)
                
                # Save to database if requested
                if save_results:
                    await self.save_item_sentiment(item_sentiment, item_ids)
        
        self.stdout.write(self.style.SUCCESS("✅ Sentiment analysis completed"))
    
    async def continuous_analysis(self, options):
        """Run continuous sentiment analysis."""
        interval = options['interval']
        lookback_hours = options['lookback']
        item_ids = options.get('items')
        save_results = options['save_results']
        
        analysis_count = 0
        
        self.stdout.write(f"🔄 Starting continuous sentiment analysis (interval: {interval}s)")
        
        while self.running:
            try:
                analysis_count += 1
                start_time = timezone.now()
                
                self.stdout.write(f"\n🔍 Analysis #{analysis_count} starting at {start_time.strftime('%H:%M:%S')}")
                
                # Run market sentiment analysis
                market_sentiment = await news_sentiment_analyzer.analyze_market_sentiment(lookback_hours)
                
                if market_sentiment.get('error'):
                    self.stdout.write(self.style.ERROR(f"❌ Market analysis failed: {market_sentiment['error']}"))
                else:
                    # Brief display of results
                    self.stdout.write(
                        f"📊 Market sentiment: {market_sentiment['overall_sentiment']} "
                        f"(score: {market_sentiment['sentiment_score']:.2f}, "
                        f"confidence: {market_sentiment['confidence']:.2f})"
                    )
                    
                    if save_results:
                        await self.save_market_sentiment(market_sentiment)
                
                # Run item analysis if specified
                if item_ids:
                    item_sentiment = await news_sentiment_analyzer.analyze_item_specific_sentiment(item_ids)
                    
                    if not item_sentiment.get('error'):
                        significant_items = [
                            item for item in item_sentiment['item_sentiment'].values()
                            if item['mention_count'] > 0 and abs(item['sentiment_score']) > 0.3
                        ]
                        
                        if significant_items:
                            self.stdout.write(f"📈 {len(significant_items)} items with significant sentiment")
                            for item in significant_items[:3]:  # Show top 3
                                self.stdout.write(f"   • {item['item_name']}: {item['sentiment_label']} ({item['sentiment_score']:.2f})")
                        
                        if save_results:
                            await self.save_item_sentiment(item_sentiment, item_ids)
                
                # Calculate analysis duration
                duration = (timezone.now() - start_time).total_seconds()
                self.stdout.write(f"✅ Analysis #{analysis_count} completed in {duration:.1f}s")
                
                # Wait for next analysis
                if self.running:
                    await asyncio.sleep(interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Analysis error: {e}"))
                logger.exception("Error in continuous analysis")
                
                # Wait before retrying
                await asyncio.sleep(min(interval, 60))
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Continuous analysis completed. {analysis_count} analyses performed."
            )
        )
    
    def display_market_sentiment(self, sentiment: dict):
        """Display market sentiment results."""
        self.stdout.write("\n📊 Market Sentiment Analysis Results:")
        self.stdout.write(f"   • Overall sentiment: {sentiment['overall_sentiment']}")
        self.stdout.write(f"   • Sentiment score: {sentiment['sentiment_score']:.3f}")
        self.stdout.write(f"   • Confidence: {sentiment['confidence']:.3f}")
        self.stdout.write(f"   • Articles analyzed: {sentiment['analyzed_articles']}")
        
        if sentiment['key_themes']:
            self.stdout.write(f"   • Key themes: {', '.join(sentiment['key_themes'][:5])}")
        
        # Show category sentiment
        if sentiment['category_sentiment']:
            self.stdout.write("   • Category sentiment:")
            for category, score in sentiment['category_sentiment'].items():
                if abs(score) > 0.1:  # Only show significant sentiment
                    self.stdout.write(f"     - {category}: {score:.2f}")
        
        # Show market predictions
        if sentiment['market_impact_predictions']:
            significant_predictions = [
                (key, pred) for key, pred in sentiment['market_impact_predictions'].items()
                if pred.get('confidence', 0) > 0.5
            ]
            
            if significant_predictions:
                self.stdout.write("   • Market predictions:")
                for key, pred in significant_predictions[:3]:  # Show top 3
                    self.stdout.write(f"     - {key}: {pred['impact_direction']} (confidence: {pred['confidence']:.2f})")
    
    def display_item_sentiment(self, sentiment: dict):
        """Display item sentiment results."""
        self.stdout.write("\n📈 Item Sentiment Analysis Results:")
        self.stdout.write(f"   • Items analyzed: {sentiment['analyzed_items']}")
        
        summary = sentiment['summary']
        self.stdout.write(f"   • Total mentions: {summary['total_mentions']}")
        self.stdout.write(f"   • Positive items: {summary['positive_items']}")
        self.stdout.write(f"   • Negative items: {summary['negative_items']}")
        self.stdout.write(f"   • Neutral items: {summary['neutral_items']}")
        
        # Show items with significant sentiment
        significant_items = [
            item for item in sentiment['item_sentiment'].values()
            if item['mention_count'] > 0 and abs(item['sentiment_score']) > 0.2
        ]
        
        if significant_items:
            self.stdout.write("   • Items with notable sentiment:")
            for item in sorted(significant_items, key=lambda x: abs(x['sentiment_score']), reverse=True)[:5]:
                self.stdout.write(
                    f"     - {item['item_name']}: {item['sentiment_label']} "
                    f"({item['sentiment_score']:.2f}, {item['mention_count']} mentions)"
                )
    
    async def save_market_sentiment(self, sentiment: dict):
        """Save market sentiment to database."""
        try:
            await sync_to_async(SentimentAnalysis.objects.create)(
                source='combined',
                overall_sentiment=sentiment['overall_sentiment'],
                sentiment_score=sentiment['sentiment_score'],
                confidence=sentiment['confidence'],
                analyzed_articles=sentiment['analyzed_articles'],
                key_themes=sentiment['key_themes'],
                sentiment_breakdown=sentiment['sentiment_breakdown'],
                market_impact_predictions=sentiment['market_impact_predictions'],
                category_sentiment=sentiment['category_sentiment'],
                top_mentioned_items=sentiment['top_mentioned_items']
            )
            
            self.stdout.write("💾 Market sentiment saved to database")
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️  Failed to save market sentiment: {e}"))
    
    async def save_item_sentiment(self, sentiment: dict, item_ids: List[int]):
        """Save item sentiment to database."""
        try:
            saved_count = 0
            
            for item_id in item_ids:
                if item_id in sentiment['item_sentiment']:
                    item_data = sentiment['item_sentiment'][item_id]
                    
                    # Get item object
                    try:
                        item = await sync_to_async(Item.objects.get)(item_id=item_id)
                        
                        await sync_to_async(ItemSentiment.objects.create)(
                            item=item,
                            sentiment_score=item_data['sentiment_score'],
                            sentiment_label=item_data['sentiment_label'],
                            mention_count=item_data['mention_count'],
                            confidence=item_data['confidence'],
                            sample_contexts=item_data['sample_contexts'],
                            predicted_impact=item_data['predicted_impact'],
                            sources=['news_analysis']  # Could be expanded
                        )
                        
                        saved_count += 1
                        
                    except Item.DoesNotExist:
                        self.stdout.write(f"⚠️  Item {item_id} not found in database")
            
            self.stdout.write(f"💾 {saved_count} item sentiment records saved to database")
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️  Failed to save item sentiment: {e}"))
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.stdout.write(self.style.WARNING(f"🛑 Received signal {signum}, shutting down..."))
        self.running = False