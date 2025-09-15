"""
Real-Time Market Anomaly Detection Engine

Advanced anomaly detection system for identifying unusual market conditions:
- Price spike/crash detection using statistical methods
- Volume surge identification with confidence scoring  
- Market manipulation pattern recognition
- Flash crash and pump detection
- Correlation breakdowns between related items
- Liquidity shock identification
- Real-time alert generation with severity levels
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from asgiref.sync import sync_to_async
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
import json

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.realtime_engine.models import MarketEvent, MarketMomentum, VolumeAnalysis
from services.intelligent_cache import intelligent_cache
from services.streaming_data_manager import streaming_manager

logger = logging.getLogger(__name__)


class AnomalyDetectionEngine:
    """
    Advanced real-time market anomaly detection system.
    """
    
    def __init__(self):
        self.cache_prefix = "anomaly_detection:"
        self.lookback_minutes = 60  # Analysis window
        self.confidence_threshold = 0.75  # Minimum confidence for alerts
        
        # Statistical thresholds
        self.price_spike_threshold = 3.0  # Standard deviations
        self.volume_surge_threshold = 5.0  # Standard deviations
        self.velocity_anomaly_threshold = 2.5  # Standard deviations
        
        # Pattern recognition parameters
        self.correlation_threshold = 0.8  # For related items
        self.manipulation_score_threshold = 80.0  # Out of 100
        
    async def detect_market_anomalies(self, item_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Run comprehensive anomaly detection across all items or specific items.
        
        Args:
            item_ids: Optional list of item IDs to analyze
            
        Returns:
            Dictionary with detected anomalies and analysis
        """
        logger.debug(f"🔍 Running market anomaly detection for {len(item_ids) if item_ids else 'all'} items")
        
        try:
            # Get items to analyze
            if item_ids:
                items = await self._get_items_by_ids(item_ids)
            else:
                items = await self._get_active_items()
            
            if not items:
                return {'anomalies': [], 'analysis': {'total_items': 0}}
            
            # Run different types of anomaly detection
            price_anomalies = await self._detect_price_anomalies(items)
            volume_anomalies = await self._detect_volume_anomalies(items)
            velocity_anomalies = await self._detect_velocity_anomalies(items)
            manipulation_alerts = await self._detect_manipulation_patterns(items)
            correlation_breaks = await self._detect_correlation_breakdowns(items)
            
            # Combine and rank anomalies
            all_anomalies = (
                price_anomalies + volume_anomalies + velocity_anomalies + 
                manipulation_alerts + correlation_breaks
            )
            
            # Sort by severity and confidence
            all_anomalies.sort(
                key=lambda x: (x['severity_score'] * x['confidence']),
                reverse=True
            )
            
            # Generate market events for high-confidence anomalies
            await self._generate_market_events(all_anomalies)
            
            # Cache results
            cache_key = f"{self.cache_prefix}latest_scan"
            scan_result = {
                'timestamp': timezone.now().isoformat(),
                'items_analyzed': len(items),
                'anomalies_detected': len(all_anomalies),
                'high_severity_count': len([a for a in all_anomalies if a['severity_score'] >= 80]),
                'anomalies': all_anomalies[:50],  # Top 50 anomalies
                'analysis': {
                    'total_items': len(items),
                    'price_anomalies': len(price_anomalies),
                    'volume_anomalies': len(volume_anomalies),
                    'velocity_anomalies': len(velocity_anomalies),
                    'manipulation_alerts': len(manipulation_alerts),
                    'correlation_breaks': len(correlation_breaks)
                }
            }
            
            intelligent_cache.set(
                cache_key,
                scan_result,
                tier="hot",
                tags=["anomaly_detection", "market_scan"]
            )
            
            logger.info(f"✅ Anomaly detection completed: {len(all_anomalies)} anomalies detected")
            return scan_result
            
        except Exception as e:
            logger.error(f"❌ Anomaly detection failed: {e}")
            return {'error': str(e), 'anomalies': []}
    
    async def _detect_price_anomalies(self, items: List[Item]) -> List[Dict[str, Any]]:
        """Detect price spikes, crashes, and unusual movements."""
        logger.debug("🔍 Detecting price anomalies")
        anomalies = []
        
        for item in items:
            try:
                # Get recent price history
                price_history = await self._get_price_history(item.item_id, hours=24)
                if len(price_history) < 10:  # Need minimum data points
                    continue
                
                # Calculate price statistics
                prices = [p['price'] for p in price_history]
                price_changes = np.diff(prices)
                mean_change = np.mean(price_changes)
                std_change = np.std(price_changes)
                
                if std_change == 0:  # No price movement
                    continue
                
                # Check latest price change
                latest_change = price_changes[-1] if len(price_changes) > 0 else 0
                z_score = abs((latest_change - mean_change) / std_change)
                
                if z_score >= self.price_spike_threshold:
                    # Determine if spike or crash
                    anomaly_type = 'price_spike' if latest_change > 0 else 'price_crash'
                    
                    # Calculate additional metrics
                    price_change_pct = (latest_change / prices[-2] * 100) if len(prices) > 1 else 0
                    severity_score = min(100, z_score * 15)  # Scale to 0-100
                    confidence = min(1.0, z_score / 5.0)  # Higher z-score = higher confidence
                    
                    anomaly = {
                        'type': anomaly_type,
                        'item_id': item.item_id,
                        'item_name': item.name,
                        'detected_at': timezone.now().isoformat(),
                        'severity_score': severity_score,
                        'confidence': confidence,
                        'metrics': {
                            'z_score': round(z_score, 2),
                            'price_change_gp': latest_change,
                            'price_change_pct': round(price_change_pct, 2),
                            'current_price': prices[-1],
                            'previous_price': prices[-2] if len(prices) > 1 else prices[-1],
                        },
                        'description': f"{'Significant price spike' if latest_change > 0 else 'Significant price crash'} detected (Z-score: {z_score:.1f})"
                    }
                    
                    anomalies.append(anomaly)
                    
            except Exception as e:
                logger.error(f"Error analyzing price anomalies for item {item.item_id}: {e}")
                continue
        
        logger.debug(f"✅ Price anomaly detection completed: {len(anomalies)} anomalies")
        return anomalies
    
    async def _detect_volume_anomalies(self, items: List[Item]) -> List[Dict[str, Any]]:
        """Detect volume surges and unusual trading activity."""
        logger.debug("🔍 Detecting volume anomalies")
        anomalies = []
        
        for item in items:
            try:
                # Get volume analysis
                volume_analysis = await self._get_volume_analysis(item.item_id)
                if not volume_analysis:
                    continue
                
                # Check for volume surge
                volume_ratio = volume_analysis.volume_ratio_daily
                if volume_ratio >= 3.0:  # 300% of normal volume
                    severity_score = min(100, volume_ratio * 20)
                    confidence = min(1.0, (volume_ratio - 1) / 4)  # Scale confidence
                    
                    anomaly = {
                        'type': 'volume_surge',
                        'item_id': item.item_id,
                        'item_name': item.name,
                        'detected_at': timezone.now().isoformat(),
                        'severity_score': severity_score,
                        'confidence': confidence,
                        'metrics': {
                            'volume_ratio': round(volume_ratio, 2),
                            'current_daily_volume': volume_analysis.current_daily_volume,
                            'average_daily_volume': volume_analysis.average_daily_volume,
                            'liquidity_level': volume_analysis.liquidity_level
                        },
                        'description': f"Volume surge detected: {volume_ratio:.1f}x normal trading volume"
                    }
                    
                    anomalies.append(anomaly)
                    
            except Exception as e:
                logger.error(f"Error analyzing volume anomalies for item {item.item_id}: {e}")
                continue
        
        logger.debug(f"✅ Volume anomaly detection completed: {len(anomalies)} anomalies")
        return anomalies
    
    async def _detect_velocity_anomalies(self, items: List[Item]) -> List[Dict[str, Any]]:
        """Detect unusual price velocity and acceleration patterns."""
        logger.debug("🔍 Detecting velocity anomalies")
        anomalies = []
        
        for item in items:
            try:
                # Get momentum data
                momentum = await self._get_momentum_data(item.item_id)
                if not momentum:
                    continue
                
                # Check for extreme velocity
                velocity = abs(momentum.price_velocity)
                acceleration = abs(momentum.price_acceleration)
                
                # Get historical velocity statistics
                velocity_stats = await self._get_velocity_statistics(item.item_id)
                if not velocity_stats:
                    continue
                
                # Calculate velocity z-score
                if velocity_stats['std'] > 0:
                    velocity_z_score = (velocity - velocity_stats['mean']) / velocity_stats['std']
                    
                    if velocity_z_score >= self.velocity_anomaly_threshold:
                        severity_score = min(100, velocity_z_score * 20)
                        confidence = min(1.0, velocity_z_score / 4)
                        
                        # Determine anomaly subtype
                        if acceleration > velocity * 0.5:  # High acceleration
                            anomaly_type = 'acceleration_surge'
                            description = f"Rapid price acceleration detected (velocity: {velocity:.0f} GP/min)"
                        else:
                            anomaly_type = 'velocity_spike'
                            description = f"Unusual price velocity detected (Z-score: {velocity_z_score:.1f})"
                        
                        anomaly = {
                            'type': anomaly_type,
                            'item_id': item.item_id,
                            'item_name': item.name,
                            'detected_at': timezone.now().isoformat(),
                            'severity_score': severity_score,
                            'confidence': confidence,
                            'metrics': {
                                'price_velocity': round(velocity, 2),
                                'price_acceleration': round(acceleration, 2),
                                'velocity_z_score': round(velocity_z_score, 2),
                                'momentum_score': momentum.momentum_score,
                                'trend_direction': momentum.trend_direction
                            },
                            'description': description
                        }
                        
                        anomalies.append(anomaly)
                        
            except Exception as e:
                logger.error(f"Error analyzing velocity anomalies for item {item.item_id}: {e}")
                continue
        
        logger.debug(f"✅ Velocity anomaly detection completed: {len(anomalies)} anomalies")
        return anomalies
    
    async def _detect_manipulation_patterns(self, items: List[Item]) -> List[Dict[str, Any]]:
        """Detect potential market manipulation patterns."""
        logger.debug("🔍 Detecting manipulation patterns")
        anomalies = []
        
        for item in items:
            try:
                # Get comprehensive item data
                price_history = await self._get_price_history(item.item_id, hours=6)
                volume_analysis = await self._get_volume_analysis(item.item_id)
                momentum = await self._get_momentum_data(item.item_id)
                
                if len(price_history) < 5 or not volume_analysis or not momentum:
                    continue
                
                # Calculate manipulation indicators
                manipulation_score = 0
                indicators = {}
                
                # 1. Price ladder patterns (consistent small increases)
                prices = [p['price'] for p in price_history[-10:]]
                price_changes = np.diff(prices)
                if len(price_changes) > 0:
                    consistent_increases = sum(1 for change in price_changes if 0 < change < np.mean(prices) * 0.02)
                    if consistent_increases >= len(price_changes) * 0.7:  # 70% consistent small increases
                        manipulation_score += 25
                        indicators['price_ladder'] = True
                
                # 2. Volume concentration (high volume, low price movement)
                if volume_analysis.volume_ratio_daily > 2.0 and momentum.price_velocity < 100:
                    manipulation_score += 30
                    indicators['volume_concentration'] = True
                
                # 3. Artificial momentum (high momentum score but low real trading)
                if momentum.momentum_score > 70 and volume_analysis.liquidity_level in ['low', 'very_low']:
                    manipulation_score += 25
                    indicators['artificial_momentum'] = True
                
                # 4. Price ceiling testing (repeated price rejections)
                if len(price_history) >= 20:
                    recent_prices = [p['price'] for p in price_history[-20:]]
                    max_price = max(recent_prices)
                    ceiling_tests = sum(1 for p in recent_prices if abs(p - max_price) < max_price * 0.01)
                    if ceiling_tests >= 3:
                        manipulation_score += 20
                        indicators['ceiling_testing'] = True
                
                # Generate alert if manipulation score is high
                if manipulation_score >= self.manipulation_score_threshold:
                    confidence = min(1.0, manipulation_score / 100)
                    
                    anomaly = {
                        'type': 'market_manipulation',
                        'item_id': item.item_id,
                        'item_name': item.name,
                        'detected_at': timezone.now().isoformat(),
                        'severity_score': manipulation_score,
                        'confidence': confidence,
                        'metrics': {
                            'manipulation_score': manipulation_score,
                            'indicators': indicators,
                            'volume_ratio': volume_analysis.volume_ratio_daily,
                            'momentum_score': momentum.momentum_score,
                            'price_velocity': momentum.price_velocity
                        },
                        'description': f"Potential market manipulation detected (score: {manipulation_score}/100)"
                    }
                    
                    anomalies.append(anomaly)
                    
            except Exception as e:
                logger.error(f"Error analyzing manipulation patterns for item {item.item_id}: {e}")
                continue
        
        logger.debug(f"✅ Manipulation pattern detection completed: {len(anomalies)} anomalies")
        return anomalies
    
    async def _detect_correlation_breakdowns(self, items: List[Item]) -> List[Dict[str, Any]]:
        """Detect when correlated items break their normal relationships."""
        logger.debug("🔍 Detecting correlation breakdowns")
        anomalies = []
        
        try:
            # Find item correlations (simplified - would use more sophisticated grouping)
            item_groups = await self._get_correlated_item_groups(items)
            
            for group_name, item_group in item_groups.items():
                if len(item_group) < 2:
                    continue
                
                # Get recent performance for all items in group
                group_performances = {}
                for item in item_group:
                    momentum = await self._get_momentum_data(item.item_id)
                    if momentum:
                        group_performances[item.item_id] = {
                            'momentum_score': momentum.momentum_score,
                            'price_velocity': momentum.price_velocity,
                            'item_name': item.name
                        }
                
                if len(group_performances) < 2:
                    continue
                
                # Check for correlation breakdown
                momentum_scores = [perf['momentum_score'] for perf in group_performances.values()]
                momentum_std = np.std(momentum_scores)
                momentum_range = max(momentum_scores) - min(momentum_scores)
                
                # If one item is significantly different from others
                if momentum_range > 40 and momentum_std > 15:  # High divergence
                    # Find the outlier
                    mean_momentum = np.mean(momentum_scores)
                    for item_id, perf in group_performances.items():
                        deviation = abs(perf['momentum_score'] - mean_momentum)
                        if deviation > 25:  # Significant deviation
                            severity_score = min(100, deviation * 2)
                            confidence = min(1.0, deviation / 40)
                            
                            anomaly = {
                                'type': 'correlation_breakdown',
                                'item_id': item_id,
                                'item_name': perf['item_name'],
                                'detected_at': timezone.now().isoformat(),
                                'severity_score': severity_score,
                                'confidence': confidence,
                                'metrics': {
                                    'group_name': group_name,
                                    'momentum_deviation': round(deviation, 1),
                                    'group_mean_momentum': round(mean_momentum, 1),
                                    'item_momentum': perf['momentum_score'],
                                    'group_momentum_range': round(momentum_range, 1)
                                },
                                'description': f"Correlation breakdown in {group_name} group (deviation: {deviation:.1f})"
                            }
                            
                            anomalies.append(anomaly)
            
        except Exception as e:
            logger.error(f"Error detecting correlation breakdowns: {e}")
        
        logger.debug(f"✅ Correlation breakdown detection completed: {len(anomalies)} anomalies")
        return anomalies
    
    # Helper methods
    
    @sync_to_async
    def _get_items_by_ids(self, item_ids: List[int]) -> List[Item]:
        """Get items by IDs."""
        return list(Item.objects.filter(item_id__in=item_ids))
    
    @sync_to_async
    def _get_active_items(self) -> List[Item]:
        """Get actively traded items."""
        return list(
            Item.objects.filter(
                profit_calc__volume_category__in=['hot', 'warm', 'cool']
            ).distinct()[:100]  # Limit for performance
        )
    
    @sync_to_async
    def _get_price_history(self, item_id: int, hours: int = 24) -> List[Dict]:
        """Get recent price history for an item."""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        snapshots = PriceSnapshot.objects.filter(
            item__item_id=item_id,
            created_at__gte=cutoff_time
        ).order_by('created_at').values('high_price', 'low_price', 'created_at')
        
        return [
            {
                'price': (snapshot['high_price'] + snapshot['low_price']) / 2 if snapshot['high_price'] and snapshot['low_price'] else 0,
                'timestamp': snapshot['created_at']
            }
            for snapshot in snapshots
        ]
    
    @sync_to_async
    def _get_volume_analysis(self, item_id: int) -> Optional[VolumeAnalysis]:
        """Get volume analysis for an item."""
        try:
            return VolumeAnalysis.objects.select_related('item').get(
                item__item_id=item_id
            )
        except VolumeAnalysis.DoesNotExist:
            return None
    
    @sync_to_async
    def _get_momentum_data(self, item_id: int) -> Optional[MarketMomentum]:
        """Get momentum data for an item."""
        try:
            return MarketMomentum.objects.select_related('item').get(
                item__item_id=item_id
            )
        except MarketMomentum.DoesNotExist:
            return None
    
    async def _get_velocity_statistics(self, item_id: int) -> Optional[Dict[str, float]]:
        """Get historical velocity statistics for an item."""
        # This would typically calculate from historical momentum data
        # For now, return mock statistics
        return {
            'mean': 50.0,
            'std': 25.0,
            'min': 0.0,
            'max': 200.0
        }
    
    async def _get_correlated_item_groups(self, items: List[Item]) -> Dict[str, List[Item]]:
        """Get groups of correlated items (simplified implementation)."""
        # This would use more sophisticated correlation analysis
        # For now, group by basic categories
        
        groups = {
            '3rd_age_items': [item for item in items if '3rd age' in item.name.lower()],
            'dragon_items': [item for item in items if 'dragon' in item.name.lower()],
            'rune_items': [item for item in items if 'rune' in item.name.lower()],
            'barrows_items': [item for item in items if any(name in item.name.lower() 
                             for name in ['ahrim', 'dharok', 'guthan', 'karil', 'torag', 'verac'])]
        }
        
        # Filter out empty groups
        return {name: group for name, group in groups.items() if len(group) > 1}
    
    @sync_to_async
    def _generate_market_events(self, anomalies: List[Dict[str, Any]]):
        """Generate MarketEvent records for high-confidence anomalies."""
        high_confidence_anomalies = [
            anomaly for anomaly in anomalies 
            if anomaly['confidence'] >= self.confidence_threshold and 
               anomaly['severity_score'] >= 70
        ]
        
        for anomaly in high_confidence_anomalies:
            try:
                # Check if similar event already exists recently
                recent_events = MarketEvent.objects.filter(
                    event_type=anomaly['type'],
                    items__item_id=anomaly['item_id'],
                    detected_at__gte=timezone.now() - timedelta(minutes=30)
                )
                
                if recent_events.exists():
                    continue  # Don't create duplicate events
                
                # Create market event
                event = MarketEvent.objects.create(
                    event_type=anomaly['type'],
                    title=f"{anomaly['item_name']} - {anomaly['type'].replace('_', ' ').title()}",
                    description=anomaly['description'],
                    impact_score=anomaly['severity_score'],
                    confidence=anomaly['confidence'],
                    event_data=anomaly['metrics']
                )
                
                # Add the item to the event
                item = Item.objects.get(item_id=anomaly['item_id'])
                event.items.add(item)
                
                logger.info(f"📢 Market event created: {event.title}")
                
            except Exception as e:
                logger.error(f"Failed to create market event: {e}")


# Global anomaly detection engine instance
anomaly_detection_engine = AnomalyDetectionEngine()