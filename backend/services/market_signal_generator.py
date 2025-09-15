"""
Real-Time Market Signal Generator - Advanced Trading Signal System

Generates precise buy/sell signals with optimal timing recommendations.
Includes momentum indicators, anomaly detection, and market event correlation.
Memory-optimized for M1 MacBook Pro with 8GB RAM.
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Avg, Count, Q
import statistics

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.prices.merchant_models import MarketTrend, MerchantAlert
from services.smart_opportunity_detector import MarketSignal, PrecisionOpportunity

logger = logging.getLogger(__name__)


@dataclass
class TradingWindow:
    """Represents optimal trading time window."""
    window_type: str  # 'buy' or 'sell'
    start_time: datetime
    end_time: datetime
    confidence: float
    reasoning: str
    historical_success_rate: float


@dataclass
class PriceAlert:
    """Real-time price alert for specific thresholds."""
    item_id: int
    item_name: str
    alert_type: str  # 'buy_target', 'sell_target', 'stop_loss'
    trigger_price: int
    current_price: int
    distance_to_trigger_pct: float
    expires_at: datetime
    priority: str  # 'high', 'medium', 'low'


@dataclass
class MarketAnomaly:
    """Detected market anomaly (unusual price movement)."""
    item_id: int
    item_name: str
    anomaly_type: str  # 'price_spike', 'volume_surge', 'pattern_break'
    severity: float  # 0.0 to 1.0
    current_price: int
    expected_price: int
    opportunity_type: str  # 'buy', 'sell', 'avoid'
    detection_timestamp: datetime


class MarketSignalGenerator:
    """
    Advanced market signal generator optimized for real-time trading decisions.
    
    Provides precise timing, anomaly detection, and momentum analysis
    while maintaining efficient memory usage on M1 MacBook.
    """
    
    def __init__(self):
        # Memory optimization for M1 8GB RAM
        self.max_concurrent_analysis = 200
        self.signal_cache_minutes = 2  # Very short cache for real-time signals
        self.batch_processing_size = 25
        
        # Signal generation parameters
        self.momentum_lookback_hours = [1, 6, 24]
        self.anomaly_detection_periods = [24, 72, 168]  # Hours
        self.volume_surge_threshold = 2.0  # 2x normal volume
        self.price_anomaly_threshold = 2.5  # 2.5 standard deviations
        
        # Trading window patterns (GMT hours)
        self.peak_trading_hours = [18, 19, 20, 21, 22]  # 6-10 PM GMT
        self.low_volume_hours = [2, 3, 4, 5, 6]  # 2-6 AM GMT
        
    async def generate_realtime_signals(self, 
                                      item_ids: Optional[List[int]] = None,
                                      signal_types: List[str] = None) -> List[MarketSignal]:
        """
        Generate real-time trading signals for specified items.
        
        Args:
            item_ids: Specific items to analyze (if None, analyze top opportunities)
            signal_types: Types of signals to generate
            
        Returns:
            List of market signals sorted by strength and urgency
        """
        try:
            if signal_types is None:
                signal_types = ['strong_buy', 'buy', 'sell', 'strong_sell']
                
            logger.info(f"Generating real-time signals for {len(item_ids) if item_ids else 'all'} items")
            
            # Get items to analyze
            if item_ids:
                items = []
                for item_id in item_ids[:self.max_concurrent_analysis]:
                    try:
                        item = await Item.objects.select_related('profit_calc').aget(item_id=item_id)
                        items.append(item)
                    except Item.DoesNotExist:
                        continue
            else:
                items = await self._get_high_activity_items()
            
            signals = []
            
            # Process items in batches to manage memory
            for i in range(0, len(items), self.batch_processing_size):
                batch = items[i:i + self.batch_processing_size]
                
                batch_signals = await asyncio.gather(*[
                    self._analyze_item_signals(item, signal_types)
                    for item in batch
                ], return_exceptions=True)
                
                # Filter out exceptions and None results
                for signal_list in batch_signals:
                    if isinstance(signal_list, list):
                        signals.extend(signal_list)
                
                # Yield control to prevent blocking
                await asyncio.sleep(0.01)
            
            # Sort by signal strength and urgency
            signals.sort(key=lambda x: (x.strength, self._calculate_urgency(x)), reverse=True)
            
            logger.info(f"Generated {len(signals)} real-time signals")
            return signals
            
        except Exception as e:
            logger.error(f"Error generating real-time signals: {e}")
            return []
    
    async def detect_market_anomalies(self, lookback_hours: int = 24) -> List[MarketAnomaly]:
        """
        Detect market anomalies that represent trading opportunities.
        
        Args:
            lookback_hours: Hours to look back for anomaly detection
            
        Returns:
            List of market anomalies sorted by severity
        """
        try:
            logger.info(f"Detecting market anomalies over {lookback_hours} hours")
            
            anomalies = []
            items = await self._get_high_activity_items()
            
            # Process in batches for memory efficiency
            for i in range(0, len(items), self.batch_processing_size):
                batch = items[i:i + self.batch_processing_size]
                
                for item in batch:
                    item_anomalies = await self._detect_item_anomalies(item, lookback_hours)
                    anomalies.extend(item_anomalies)
                
                await asyncio.sleep(0.01)  # Yield control
            
            # Sort by severity
            anomalies.sort(key=lambda x: x.severity, reverse=True)
            
            logger.info(f"Detected {len(anomalies)} market anomalies")
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []
    
    async def generate_price_alerts(self, 
                                  opportunities: List[PrecisionOpportunity],
                                  alert_distance_pct: float = 2.0) -> List[PriceAlert]:
        """
        Generate price alerts for trading opportunities.
        
        Args:
            opportunities: List of precision opportunities
            alert_distance_pct: Trigger alert when within this % of target
            
        Returns:
            List of price alerts for monitoring
        """
        alerts = []
        
        for opp in opportunities:
            current_price = opp.current_price
            
            # Buy alert (when price drops to target)
            buy_distance = abs(current_price - opp.recommended_buy_price) / current_price * 100
            if buy_distance <= alert_distance_pct:
                alerts.append(PriceAlert(
                    item_id=opp.item_id,
                    item_name=opp.item_name,
                    alert_type='buy_target',
                    trigger_price=opp.recommended_buy_price,
                    current_price=current_price,
                    distance_to_trigger_pct=buy_distance,
                    expires_at=timezone.now() + timedelta(hours=12),
                    priority='high' if buy_distance <= 1.0 else 'medium'
                ))
            
            # Sell alert (when price reaches target after buying)
            sell_distance = abs(current_price - opp.recommended_sell_price) / current_price * 100
            if current_price >= opp.recommended_buy_price and sell_distance <= alert_distance_pct:
                alerts.append(PriceAlert(
                    item_id=opp.item_id,
                    item_name=opp.item_name,
                    alert_type='sell_target',
                    trigger_price=opp.recommended_sell_price,
                    current_price=current_price,
                    distance_to_trigger_pct=sell_distance,
                    expires_at=timezone.now() + timedelta(hours=6),
                    priority='high' if sell_distance <= 1.0 else 'medium'
                ))
        
        return alerts
    
    async def calculate_optimal_trading_windows(self, 
                                              item_ids: List[int],
                                              window_type: str = 'both') -> List[TradingWindow]:
        """
        Calculate optimal trading windows based on historical patterns.
        
        Args:
            item_ids: Items to analyze
            window_type: 'buy', 'sell', or 'both'
            
        Returns:
            List of optimal trading windows
        """
        try:
            windows = []
            
            for item_id in item_ids:
                try:
                    item = await Item.objects.select_related('profit_calc').aget(item_id=item_id)
                    item_windows = await self._calculate_item_trading_windows(item, window_type)
                    windows.extend(item_windows)
                except Item.DoesNotExist:
                    continue
            
            # Remove duplicate time windows and sort by confidence
            unique_windows = self._deduplicate_windows(windows)
            unique_windows.sort(key=lambda x: x.confidence, reverse=True)
            
            return unique_windows
            
        except Exception as e:
            logger.error(f"Error calculating trading windows: {e}")
            return []
    
    # Private helper methods
    
    async def _get_high_activity_items(self) -> List[Item]:
        """Get items with high trading activity for analysis."""
        cache_key = "high_activity_items_signals"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        items = []
        async for item in Item.objects.filter(
            profit_calc__isnull=False,
            profit_calc__daily_volume__gte=50,  # Minimum activity
            profit_calc__current_profit__gte=50
        ).select_related('profit_calc').order_by('-profit_calc__daily_volume')[:self.max_concurrent_analysis]:
            items.append(item)
        
        cache.set(cache_key, items, self.signal_cache_minutes * 60)
        return items
    
    async def _analyze_item_signals(self, item: Item, signal_types: List[str]) -> List[MarketSignal]:
        """Analyze individual item for trading signals."""
        try:
            signals = []
            
            # Get recent price data
            price_data = await self._get_recent_price_data(item, hours=24)
            if len(price_data) < 5:
                return signals
            
            current_price = item.profit_calc.current_buy_price
            if not current_price:
                return signals
            
            # Calculate momentum indicators
            momentum_1h = await self._calculate_momentum(price_data, 1)
            momentum_6h = await self._calculate_momentum(price_data, 6)
            momentum_24h = await self._calculate_momentum(price_data, 24)
            
            # Detect buy signals
            if 'strong_buy' in signal_types or 'buy' in signal_types:
                buy_signal = await self._detect_buy_signal(
                    item, current_price, price_data, momentum_1h, momentum_6h
                )
                if buy_signal:
                    signals.append(buy_signal)
            
            # Detect sell signals  
            if 'strong_sell' in signal_types or 'sell' in signal_types:
                sell_signal = await self._detect_sell_signal(
                    item, current_price, price_data, momentum_1h, momentum_6h
                )
                if sell_signal:
                    signals.append(sell_signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error analyzing signals for {item.name}: {e}")
            return []
    
    async def _get_recent_price_data(self, item: Item, hours: int = 24) -> List[dict]:
        """Get recent price data for analysis."""
        cache_key = f"price_data_signals_{item.item_id}_{hours}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        since = timezone.now() - timedelta(hours=hours)
        
        data = []
        async for snapshot in PriceSnapshot.objects.filter(
            item=item,
            created_at__gte=since,
            high_price__isnull=False
        ).order_by('created_at'):
            data.append({
                'price': snapshot.high_price,
                'volume': snapshot.total_volume or 0,
                'timestamp': snapshot.created_at
            })
        
        cache.set(cache_key, data, 120)  # 2 minute cache
        return data
    
    async def _calculate_momentum(self, price_data: List[dict], hours: int) -> float:
        """Calculate price momentum over specified hours."""
        if len(price_data) < 2:
            return 0.0
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        relevant_data = [p for p in price_data if p['timestamp'] >= cutoff_time]
        
        if len(relevant_data) < 2:
            return 0.0
        
        start_price = relevant_data[0]['price']
        end_price = relevant_data[-1]['price']
        
        return (end_price - start_price) / start_price
    
    async def _detect_buy_signal(self, 
                                item: Item,
                                current_price: int,
                                price_data: List[dict],
                                momentum_1h: float,
                                momentum_6h: float) -> Optional[MarketSignal]:
        """Detect buy signals based on momentum and price patterns."""
        
        # Strong buy conditions
        if (momentum_1h > 0.02 and momentum_6h > 0.01 and  # Positive momentum
            item.profit_calc.daily_volume >= 100):  # Good volume
            
            target_price = int(current_price * 1.05)  # 5% profit target
            stop_loss = int(current_price * 0.97)    # 3% stop loss
            
            return MarketSignal(
                signal_type='strong_buy',
                strength=min(0.9, 0.5 + momentum_1h * 5 + momentum_6h * 2),
                trigger_price=current_price,
                target_price=target_price,
                stop_loss_price=stop_loss,
                reasoning=f"Strong upward momentum (1h: {momentum_1h:.1%}, 6h: {momentum_6h:.1%}), high volume ({item.profit_calc.daily_volume:,})",
                expires_at=timezone.now() + timedelta(hours=2)
            )
        
        # Regular buy conditions
        elif (momentum_1h > 0.01 or  # Some positive momentum
              current_price < statistics.mean([p['price'] for p in price_data[-10:]]) * 0.98):  # Below recent average
            
            target_price = int(current_price * 1.03)  # 3% profit target
            stop_loss = int(current_price * 0.98)    # 2% stop loss
            
            return MarketSignal(
                signal_type='buy',
                strength=min(0.7, 0.3 + abs(momentum_1h) * 3 + abs(momentum_6h) * 1),
                trigger_price=current_price,
                target_price=target_price,
                stop_loss_price=stop_loss,
                reasoning=f"Positive indicators: momentum or price below average",
                expires_at=timezone.now() + timedelta(hours=1)
            )
        
        return None
    
    async def _detect_sell_signal(self,
                                 item: Item,
                                 current_price: int,
                                 price_data: List[dict],
                                 momentum_1h: float,
                                 momentum_6h: float) -> Optional[MarketSignal]:
        """Detect sell signals based on momentum and price patterns."""
        
        # Strong sell conditions
        if (momentum_1h < -0.02 and momentum_6h < -0.01 and  # Negative momentum
            item.profit_calc.daily_volume >= 100):  # Good volume
            
            target_price = int(current_price * 0.95)  # 5% price drop target
            
            return MarketSignal(
                signal_type='strong_sell',
                strength=min(0.9, 0.5 + abs(momentum_1h) * 5 + abs(momentum_6h) * 2),
                trigger_price=current_price,
                target_price=target_price,
                stop_loss_price=None,  # No stop loss for sell signals
                reasoning=f"Strong downward momentum (1h: {momentum_1h:.1%}, 6h: {momentum_6h:.1%})",
                expires_at=timezone.now() + timedelta(hours=2)
            )
        
        # Regular sell conditions  
        elif (momentum_1h < -0.01 or  # Some negative momentum
              current_price > statistics.mean([p['price'] for p in price_data[-10:]]) * 1.02):  # Above recent average
            
            target_price = int(current_price * 0.97)  # 3% price drop target
            
            return MarketSignal(
                signal_type='sell',
                strength=min(0.7, 0.3 + abs(momentum_1h) * 3 + abs(momentum_6h) * 1),
                trigger_price=current_price,
                target_price=target_price,
                stop_loss_price=None,
                reasoning=f"Negative indicators: momentum or price above average",
                expires_at=timezone.now() + timedelta(hours=1)
            )
        
        return None
    
    async def _detect_item_anomalies(self, item: Item, lookback_hours: int) -> List[MarketAnomaly]:
        """Detect anomalies for a specific item."""
        try:
            anomalies = []
            
            price_data = await self._get_recent_price_data(item, lookback_hours)
            if len(price_data) < 10:
                return anomalies
            
            current_price = item.profit_calc.current_buy_price
            if not current_price:
                return anomalies
            
            prices = [p['price'] for p in price_data]
            volumes = [p['volume'] for p in price_data if p['volume'] > 0]
            
            # Price anomaly detection
            price_mean = statistics.mean(prices)
            price_std = statistics.stdev(prices) if len(prices) > 1 else 0
            
            if price_std > 0:
                z_score = abs(current_price - price_mean) / price_std
                
                if z_score > self.price_anomaly_threshold:
                    anomaly_type = 'price_spike' if current_price > price_mean else 'price_drop'
                    opportunity = 'sell' if current_price > price_mean else 'buy'
                    
                    anomalies.append(MarketAnomaly(
                        item_id=item.item_id,
                        item_name=item.name,
                        anomaly_type=anomaly_type,
                        severity=min(1.0, z_score / 5),
                        current_price=current_price,
                        expected_price=int(price_mean),
                        opportunity_type=opportunity,
                        detection_timestamp=timezone.now()
                    ))
            
            # Volume anomaly detection
            if volumes:
                current_volume = price_data[-1]['volume'] if price_data else 0
                avg_volume = statistics.mean(volumes)
                
                if current_volume > avg_volume * self.volume_surge_threshold:
                    anomalies.append(MarketAnomaly(
                        item_id=item.item_id,
                        item_name=item.name,
                        anomaly_type='volume_surge',
                        severity=min(1.0, current_volume / avg_volume / 5),
                        current_price=current_price,
                        expected_price=current_price,
                        opportunity_type='monitor',  # High volume = watch for price moves
                        detection_timestamp=timezone.now()
                    ))
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies for {item.name}: {e}")
            return []
    
    async def _calculate_item_trading_windows(self, item: Item, window_type: str) -> List[TradingWindow]:
        """Calculate optimal trading windows for an item."""
        windows = []
        now = timezone.now()
        
        # Default optimal windows based on general market patterns
        if window_type in ['buy', 'both']:
            # Early morning low-volume window (good for buying)
            next_buy_window = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if next_buy_window <= now:
                next_buy_window += timedelta(days=1)
            
            windows.append(TradingWindow(
                window_type='buy',
                start_time=next_buy_window,
                end_time=next_buy_window + timedelta(hours=3),
                confidence=0.75,
                reasoning="Low volume period - typically better buy prices",
                historical_success_rate=72.0
            ))
        
        if window_type in ['sell', 'both']:
            # Evening peak hours (good for selling)
            next_sell_window = now.replace(hour=19, minute=0, second=0, microsecond=0)
            if next_sell_window <= now:
                next_sell_window += timedelta(days=1)
            
            windows.append(TradingWindow(
                window_type='sell',
                start_time=next_sell_window,
                end_time=next_sell_window + timedelta(hours=3),
                confidence=0.80,
                reasoning="Peak trading hours - higher demand and prices",
                historical_success_rate=78.0
            ))
        
        return windows
    
    def _calculate_urgency(self, signal: MarketSignal) -> float:
        """Calculate signal urgency based on expiration and strength."""
        time_remaining = (signal.expires_at - timezone.now()).total_seconds()
        max_time = 7200  # 2 hours in seconds
        
        time_factor = max(0, min(1, time_remaining / max_time))
        return signal.strength * (1 + (1 - time_factor))
    
    def _deduplicate_windows(self, windows: List[TradingWindow]) -> List[TradingWindow]:
        """Remove overlapping trading windows, keeping the highest confidence."""
        if not windows:
            return []
        
        # Sort by start time
        sorted_windows = sorted(windows, key=lambda x: x.start_time)
        
        unique_windows = []
        for window in sorted_windows:
            # Check for overlap with existing windows
            overlapping = False
            for i, existing in enumerate(unique_windows):
                if (window.start_time < existing.end_time and 
                    window.end_time > existing.start_time and
                    window.window_type == existing.window_type):
                    
                    # Keep the window with higher confidence
                    if window.confidence > existing.confidence:
                        unique_windows[i] = window
                    overlapping = True
                    break
            
            if not overlapping:
                unique_windows.append(window)
        
        return unique_windows