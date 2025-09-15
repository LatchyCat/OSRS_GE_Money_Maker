"""
Market Intelligence Engine - Volume & Volatility Analyzer

Advanced real-time market analysis system that provides:
- Volume surge detection (200%+ spikes)
- Volatility analysis and risk assessment  
- Market momentum tracking with 5-minute windows
- Liquidity analysis and flip completion probability
- Predictive analytics using historical patterns
"""

import asyncio
import logging
import statistics
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Avg, Max, Min, Count, F, StdDev
from django.db import transaction
from asgiref.sync import sync_to_async

from apps.items.models import Item  
from apps.prices.models import PriceSnapshot, ProfitCalculation, HistoricalPrice
from apps.realtime_engine.models import MarketMomentum, VolumeAnalysis, RiskMetrics, MarketEvent
from services.intelligent_cache import intelligent_cache
from services.timeseries_client import timeseries_client
import pandas as pd

logger = logging.getLogger(__name__)


class MarketIntelligenceEngine:
    """
    Advanced market intelligence system for real-time OSRS trading analysis.
    Combines time-series data, caching, and machine learning for predictive insights.
    """
    
    def __init__(self):
        self.cache_ttl = {
            'hot_analysis': 30,      # 30 seconds for active items
            'market_overview': 300,  # 5 minutes for market summary
            'historical_patterns': 3600,  # 1 hour for pattern analysis
        }
        
        # Analysis thresholds
        self.volume_surge_threshold = 2.0  # 200% of normal volume
        self.high_volatility_threshold = 0.3  # 30% price volatility
        self.momentum_threshold = 50.0  # Momentum score threshold
        
        # Performance tracking
        self.analysis_count = 0
        self.cache_hit_rate = 0.0
        
    async def analyze_market_conditions(self) -> Dict[str, Any]:
        """
        Comprehensive market analysis providing real-time insights.
        
        Returns:
            Dictionary with market intelligence data
        """
        logger.info("🔍 Starting comprehensive market analysis...")
        
        try:
            # Get market overview from cache first
            cache_key = "market_intelligence:overview"
            cached_analysis = intelligent_cache.get(cache_key, tiers=["hot", "warm"])
            
            if cached_analysis:
                logger.debug("📊 Using cached market analysis")
                return cached_analysis
            
            # Perform fresh analysis
            analysis_tasks = [
                self._analyze_volume_surges(),
                self._analyze_volatility_patterns(),
                self._detect_momentum_shifts(), 
                self._assess_market_liquidity(),
                self._identify_arbitrage_opportunities(),
                self._analyze_market_events()
            ]
            
            # Run analyses in parallel
            results = await asyncio.gather(*analysis_tasks)
            
            # Combine results
            market_analysis = {
                'timestamp': timezone.now().isoformat(),
                'volume_surges': results[0],
                'volatility_analysis': results[1],
                'momentum_shifts': results[2],
                'liquidity_assessment': results[3],
                'arbitrage_opportunities': results[4],
                'market_events': results[5],
                'market_health_score': self._calculate_market_health(results),
                'recommendations': self._generate_trading_recommendations(results)
            }
            
            # Cache the analysis
            intelligent_cache.set(
                cache_key, 
                market_analysis, 
                tier="warm", 
                tags=["market_analysis", "trading_intelligence"]
            )
            
            self.analysis_count += 1
            logger.info(f"✅ Market analysis completed (#{self.analysis_count})")
            
            return market_analysis
            
        except Exception as e:
            logger.error(f"❌ Market analysis failed: {e}")
            return {'error': str(e), 'timestamp': timezone.now().isoformat()}
    
    @sync_to_async
    def _analyze_volume_surges(self) -> Dict[str, Any]:
        """
        Detect volume surges indicating market catalysts.
        
        Returns:
            Dictionary with volume surge analysis
        """
        logger.debug("📈 Analyzing volume surges...")
        
        try:
            # Get items with significant volume increases
            volume_surges = VolumeAnalysis.objects.filter(
                volume_ratio_daily__gte=self.volume_surge_threshold,
                last_updated__gte=timezone.now() - timedelta(hours=1)
            ).select_related('item').order_by('-volume_ratio_daily')[:20]
            
            surge_data = []
            for surge in volume_surges:
                # Calculate surge metrics
                surge_intensity = "extreme" if surge.volume_ratio_daily >= 5.0 else "high"
                
                # Get price change during surge
                try:
                    profit_calc = getattr(surge.item, 'profit_calc', None)
                    current_profit = profit_calc.current_profit if profit_calc else 0
                    
                    surge_data.append({
                        'item_id': surge.item.item_id,
                        'item_name': surge.item.name,
                        'volume_ratio': round(surge.volume_ratio_daily, 2),
                        'current_volume': surge.current_daily_volume,
                        'average_volume': surge.average_daily_volume,
                        'liquidity_level': surge.liquidity_level,
                        'surge_intensity': surge_intensity,
                        'current_profit': current_profit,
                        'flip_probability': round(surge.flip_completion_probability, 3),
                        'last_updated': surge.last_updated.isoformat()
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing surge for item {surge.item.item_id}: {e}")
                    continue
            
            # Market-wide volume statistics
            total_items = VolumeAnalysis.objects.count()
            surging_items = VolumeAnalysis.objects.filter(
                volume_ratio_daily__gte=self.volume_surge_threshold
            ).count()
            
            return {
                'total_surging_items': surging_items,
                'surge_percentage': round((surging_items / total_items * 100), 2) if total_items > 0 else 0,
                'top_surges': surge_data,
                'analysis_time': timezone.now().isoformat(),
                'threshold_used': self.volume_surge_threshold
            }
            
        except Exception as e:
            logger.error(f"Volume surge analysis failed: {e}")
            return {'error': str(e)}
    
    @sync_to_async  
    def _analyze_volatility_patterns(self) -> Dict[str, Any]:
        """
        Analyze price volatility patterns and risk indicators.
        
        Returns:
            Dictionary with volatility analysis
        """
        logger.debug("📊 Analyzing volatility patterns...")
        
        try:
            # Get high volatility items from recent price data
            recent_prices = PriceSnapshot.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=2),
                price_volatility__isnull=False
            ).order_by('-price_volatility')[:50]
            
            volatility_data = []
            volatility_scores = []
            
            for price_snapshot in recent_prices:
                if price_snapshot.price_volatility and price_snapshot.price_volatility > 0:
                    volatility_scores.append(price_snapshot.price_volatility)
                    
                    # Classify volatility level
                    if price_snapshot.price_volatility >= self.high_volatility_threshold:
                        volatility_level = "high"
                    elif price_snapshot.price_volatility >= 0.15:
                        volatility_level = "medium" 
                    else:
                        volatility_level = "low"
                    
                    volatility_data.append({
                        'item_id': price_snapshot.item.item_id,
                        'item_name': price_snapshot.item.name,
                        'volatility': round(price_snapshot.price_volatility, 4),
                        'volatility_level': volatility_level,
                        'high_price': price_snapshot.high_price,
                        'low_price': price_snapshot.low_price,
                        'price_change_pct': price_snapshot.price_change_pct,
                        'last_updated': price_snapshot.created_at.isoformat()
                    })
            
            # Calculate market-wide volatility statistics
            if volatility_scores:
                avg_volatility = statistics.mean(volatility_scores)
                volatility_std = statistics.stdev(volatility_scores) if len(volatility_scores) > 1 else 0
                high_vol_count = sum(1 for v in volatility_scores if v >= self.high_volatility_threshold)
            else:
                avg_volatility = volatility_std = high_vol_count = 0
            
            return {
                'market_avg_volatility': round(avg_volatility, 4),
                'volatility_std_dev': round(volatility_std, 4),
                'high_volatility_items': high_vol_count,
                'total_analyzed': len(volatility_scores),
                'top_volatile_items': volatility_data[:10],  # Top 10 most volatile
                'volatility_distribution': {
                    'high': sum(1 for v in volatility_scores if v >= 0.3),
                    'medium': sum(1 for v in volatility_scores if 0.15 <= v < 0.3), 
                    'low': sum(1 for v in volatility_scores if v < 0.15)
                },
                'analysis_time': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Volatility analysis failed: {e}")
            return {'error': str(e)}
    
    @sync_to_async
    def _detect_momentum_shifts(self) -> Dict[str, Any]:
        """
        Detect momentum shifts and trend changes.
        
        Returns:
            Dictionary with momentum analysis
        """
        logger.debug("🚀 Detecting momentum shifts...")
        
        try:
            # Get items with significant momentum
            momentum_items = MarketMomentum.objects.filter(
                momentum_score__gte=self.momentum_threshold,
                last_updated__gte=timezone.now() - timedelta(hours=1)
            ).select_related('item').order_by('-momentum_score')[:25]
            
            momentum_data = []
            momentum_distribution = {'rising': 0, 'falling': 0, 'neutral': 0}
            
            for momentum in momentum_items:
                momentum_distribution[momentum.trend_direction] += 1
                
                # Calculate momentum strength
                if momentum.momentum_score >= 80:
                    strength = "very_strong"
                elif momentum.momentum_score >= 60:
                    strength = "strong"
                else:
                    strength = "moderate"
                
                momentum_data.append({
                    'item_id': momentum.item.item_id,
                    'item_name': momentum.item.name,
                    'momentum_score': round(momentum.momentum_score, 1),
                    'trend_direction': momentum.trend_direction,
                    'momentum_strength': strength,
                    'price_velocity': round(momentum.price_velocity, 2),
                    'price_acceleration': round(momentum.price_acceleration, 2),
                    'volume_velocity': round(momentum.volume_velocity, 2),
                    'momentum_category': momentum.momentum_category,
                    'last_updated': momentum.last_updated.isoformat()
                })
            
            # Detect market-wide momentum shift
            total_momentum = MarketMomentum.objects.count()
            rising_momentum = MarketMomentum.objects.filter(trend_direction='rising').count()
            falling_momentum = MarketMomentum.objects.filter(trend_direction='falling').count()
            
            if total_momentum > 0:
                market_sentiment = "bullish" if rising_momentum > falling_momentum * 1.2 else \
                                 "bearish" if falling_momentum > rising_momentum * 1.2 else "neutral"
            else:
                market_sentiment = "neutral"
            
            return {
                'market_sentiment': market_sentiment,
                'momentum_distribution': momentum_distribution,
                'sentiment_ratios': {
                    'bullish_pct': round((rising_momentum / total_momentum * 100), 1) if total_momentum > 0 else 0,
                    'bearish_pct': round((falling_momentum / total_momentum * 100), 1) if total_momentum > 0 else 0
                },
                'top_momentum_items': momentum_data,
                'total_analyzed': total_momentum,
                'analysis_time': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Momentum analysis failed: {e}")
            return {'error': str(e)}
    
    @sync_to_async
    def _assess_market_liquidity(self) -> Dict[str, Any]:
        """
        Assess market liquidity and trading feasibility.
        
        Returns:
            Dictionary with liquidity analysis
        """
        logger.debug("💧 Assessing market liquidity...")
        
        try:
            # Analyze liquidity levels
            liquidity_analysis = VolumeAnalysis.objects.values('liquidity_level').annotate(
                count=Count('id'),
                avg_volume=Avg('current_daily_volume'),
                avg_flip_probability=Avg('flip_completion_probability')
            ).order_by('-avg_volume')
            
            # Get high liquidity opportunities
            high_liquidity_items = VolumeAnalysis.objects.filter(
                liquidity_level__in=['high', 'very_high'],
                flip_completion_probability__gte=0.7,
                current_daily_volume__gte=500
            ).select_related('item').order_by('-flip_completion_probability')[:15]
            
            liquidity_opportunities = []
            for item_analysis in high_liquidity_items:
                try:
                    profit_calc = getattr(item_analysis.item, 'profit_calc', None)
                    current_profit = profit_calc.current_profit if profit_calc else 0
                    
                    liquidity_opportunities.append({
                        'item_id': item_analysis.item.item_id,
                        'item_name': item_analysis.item.name,
                        'liquidity_level': item_analysis.liquidity_level,
                        'daily_volume': item_analysis.current_daily_volume,
                        'flip_probability': round(item_analysis.flip_completion_probability, 3),
                        'current_profit': current_profit,
                        'estimated_daily_profit': int(current_profit * item_analysis.current_daily_volume * 0.1),  # Assume 10% market capture
                        'risk_level': 'low' if item_analysis.flip_completion_probability >= 0.8 else 'medium'
                    })
                except Exception as e:
                    logger.warning(f"Error processing liquidity for item {item_analysis.item.item_id}: {e}")
                    continue
            
            # Calculate market liquidity score (0-100)
            total_volume = sum(item.get('daily_volume', 0) for item in liquidity_opportunities)
            high_prob_items = sum(1 for item in liquidity_opportunities if item.get('flip_probability', 0) >= 0.8)
            
            liquidity_score = min(100, (total_volume / 10000) * 50 + (high_prob_items / len(liquidity_opportunities) * 50) if liquidity_opportunities else 0)
            
            return {
                'market_liquidity_score': round(liquidity_score, 1),
                'liquidity_distribution': list(liquidity_analysis),
                'high_liquidity_opportunities': liquidity_opportunities,
                'total_opportunities': len(liquidity_opportunities),
                'estimated_daily_volume': total_volume,
                'analysis_time': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Liquidity analysis failed: {e}")
            return {'error': str(e)}
    
    @sync_to_async
    def _identify_arbitrage_opportunities(self) -> Dict[str, Any]:
        """
        Identify arbitrage and high-profit opportunities.
        
        Returns:
            Dictionary with arbitrage analysis
        """
        logger.debug("💰 Identifying arbitrage opportunities...")
        
        try:
            # Get high-profit items with good volume
            arbitrage_candidates = ProfitCalculation.objects.filter(
                current_profit__gte=1000,  # At least 1000gp profit
                current_profit_margin__gte=10.0,  # At least 10% margin
                volume_category__in=['hot', 'warm'],
                last_updated__gte=timezone.now() - timedelta(hours=2)
            ).select_related('item').order_by('-volume_weighted_score')[:20]
            
            arbitrage_opportunities = []
            for profit_calc in arbitrage_candidates:
                # Calculate opportunity metrics
                efficiency_score = (profit_calc.current_profit * profit_calc.daily_volume) / 10000  # Profit potential
                risk_adjusted_profit = profit_calc.current_profit * (1 - (profit_calc.price_volatility * 0.5))
                
                arbitrage_opportunities.append({
                    'item_id': profit_calc.item.item_id,
                    'item_name': profit_calc.item.name,
                    'profit_per_item': profit_calc.current_profit,
                    'profit_margin': round(profit_calc.current_profit_margin, 2),
                    'daily_volume': profit_calc.daily_volume,
                    'volume_category': profit_calc.volume_category,
                    'efficiency_score': round(efficiency_score, 1),
                    'risk_adjusted_profit': round(risk_adjusted_profit, 0),
                    'high_alch_viability': profit_calc.high_alch_viability_score,
                    'sustainability_score': profit_calc.sustainable_alch_potential,
                    'buy_limit': profit_calc.item.limit if profit_calc.item.limit else 'No limit',
                    'last_updated': profit_calc.last_updated.isoformat()
                })
            
            # Calculate market opportunity metrics
            total_profit_potential = sum(opp['efficiency_score'] for opp in arbitrage_opportunities)
            avg_margin = statistics.mean([opp['profit_margin'] for opp in arbitrage_opportunities]) if arbitrage_opportunities else 0
            
            return {
                'total_opportunities': len(arbitrage_opportunities),
                'total_profit_potential': round(total_profit_potential, 1),
                'average_margin': round(avg_margin, 2),
                'top_opportunities': arbitrage_opportunities,
                'opportunity_categories': {
                    'high_profit': sum(1 for opp in arbitrage_opportunities if opp['profit_per_item'] >= 2000),
                    'high_volume': sum(1 for opp in arbitrage_opportunities if opp['daily_volume'] >= 1000),
                    'sustainable': sum(1 for opp in arbitrage_opportunities if opp['sustainability_score'] >= 70)
                },
                'analysis_time': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Arbitrage analysis failed: {e}")
            return {'error': str(e)}
    
    @sync_to_async
    def _analyze_market_events(self) -> Dict[str, Any]:
        """
        Analyze recent market events and their impact.
        
        Returns:
            Dictionary with market events analysis
        """
        logger.debug("📰 Analyzing market events...")
        
        try:
            # Get recent market events
            recent_events = MarketEvent.objects.filter(
                is_active=True,
                detected_at__gte=timezone.now() - timedelta(hours=6)
            ).order_by('-impact_score')[:10]
            
            events_data = []
            total_impact = 0
            
            for event in recent_events:
                total_impact += event.impact_score
                
                events_data.append({
                    'id': event.id,
                    'event_type': event.event_type,
                    'title': event.title,
                    'description': event.description[:200] + '...' if len(event.description) > 200 else event.description,
                    'impact_score': event.impact_score,
                    'confidence': event.confidence,
                    'detected_at': event.detected_at.isoformat(),
                    'estimated_duration': event.estimated_duration_minutes,
                    'is_high_impact': event.is_high_impact,
                    'affected_items_count': event.get_affected_items_count()
                })
            
            # Analyze event impact on market
            avg_impact = total_impact / len(recent_events) if recent_events else 0
            market_disruption_level = "high" if avg_impact >= 70 else "medium" if avg_impact >= 40 else "low"
            
            return {
                'recent_events_count': len(recent_events),
                'total_impact_score': total_impact,
                'average_impact': round(avg_impact, 1),
                'market_disruption_level': market_disruption_level,
                'events_by_type': {},  # Could be expanded
                'high_impact_events': [e for e in events_data if e['is_high_impact']],
                'all_events': events_data,
                'analysis_time': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Market events analysis failed: {e}")
            return {'error': str(e)}
    
    def _calculate_market_health(self, analysis_results: List[Dict]) -> int:
        """
        Calculate overall market health score (0-100).
        
        Args:
            analysis_results: Results from all analysis functions
            
        Returns:
            Market health score
        """
        try:
            volume_data, volatility_data, momentum_data, liquidity_data, arbitrage_data, events_data = analysis_results
            
            # Volume health (25% weight)
            volume_score = min(25, (volume_data.get('total_surging_items', 0) / 50) * 25)
            
            # Volatility health (20% weight) - lower volatility is better
            avg_volatility = volatility_data.get('market_avg_volatility', 0)
            volatility_score = max(0, 20 - (avg_volatility * 50))
            
            # Momentum health (25% weight)
            bullish_pct = momentum_data.get('sentiment_ratios', {}).get('bullish_pct', 0)
            momentum_score = (bullish_pct / 100) * 25
            
            # Liquidity health (20% weight)  
            liquidity_score = (liquidity_data.get('market_liquidity_score', 0) / 100) * 20
            
            # Event impact (10% weight) - lower disruption is better
            disruption_level = events_data.get('market_disruption_level', 'low')
            event_score = {'low': 10, 'medium': 5, 'high': 0}.get(disruption_level, 5)
            
            total_score = volume_score + volatility_score + momentum_score + liquidity_score + event_score
            
            return round(min(100, max(0, total_score)))
            
        except Exception as e:
            logger.error(f"Market health calculation failed: {e}")
            return 50  # Default neutral score
    
    def _generate_trading_recommendations(self, analysis_results: List[Dict]) -> List[Dict]:
        """
        Generate AI-powered trading recommendations.
        
        Args:
            analysis_results: Results from all analysis functions
            
        Returns:
            List of trading recommendations
        """
        try:
            volume_data, volatility_data, momentum_data, liquidity_data, arbitrage_data, events_data = analysis_results
            
            recommendations = []
            
            # High-priority recommendations based on arbitrage opportunities
            top_arbitrage = arbitrage_data.get('top_opportunities', [])[:3]
            for opp in top_arbitrage:
                recommendations.append({
                    'type': 'arbitrage_opportunity',
                    'priority': 'high',
                    'item_id': opp['item_id'],
                    'item_name': opp['item_name'], 
                    'action': 'buy_and_alch',
                    'profit_potential': opp['profit_per_item'],
                    'confidence': 85,
                    'reason': f"High profit margin ({opp['profit_margin']}%) with good volume",
                    'risk_level': 'medium'
                })
            
            # Volume surge opportunities
            volume_surges = volume_data.get('top_surges', [])[:2] 
            for surge in volume_surges:
                if surge.get('flip_probability', 0) >= 0.7:
                    recommendations.append({
                        'type': 'volume_surge',
                        'priority': 'medium',
                        'item_id': surge['item_id'],
                        'item_name': surge['item_name'],
                        'action': 'monitor_closely', 
                        'volume_increase': f"{surge['volume_ratio']}x",
                        'confidence': 70,
                        'reason': f"Volume surge detected ({surge['volume_ratio']}x normal)",
                        'risk_level': 'high'
                    })
            
            # Market sentiment recommendations
            market_sentiment = momentum_data.get('market_sentiment', 'neutral')
            if market_sentiment == 'bullish':
                recommendations.append({
                    'type': 'market_sentiment',
                    'priority': 'low',
                    'action': 'increase_activity',
                    'confidence': 60,
                    'reason': 'Market showing bullish momentum across multiple items',
                    'risk_level': 'low'
                })
            elif market_sentiment == 'bearish':
                recommendations.append({
                    'type': 'market_sentiment', 
                    'priority': 'low',
                    'action': 'reduce_risk',
                    'confidence': 60,
                    'reason': 'Market showing bearish sentiment - consider reducing exposure',
                    'risk_level': 'medium'
                })
            
            return recommendations[:5]  # Return top 5 recommendations
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return []


# Global market intelligence engine instance
market_intelligence = MarketIntelligenceEngine()