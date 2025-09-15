"""
AI-Powered Price Pattern Recognition and Trend Analysis Service

This service analyzes historical price data to:
- Detect common trading patterns (breakouts, reversals, consolidations)
- Calculate price momentum and trend strength
- Identify support and resistance levels
- Generate predictive price targets
- Create market alerts for significant events

Uses machine learning and statistical analysis for pattern recognition.
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from scipy import stats
from scipy.signal import find_peaks, savgol_filter
from sklearn.preprocessing import StandardScaler
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Avg, Count, Max, Min
import json

from apps.items.models import Item
from apps.prices.models import (
    HistoricalPricePoint, PriceTrend, MarketAlert, PricePattern,
    ProfitCalculation
)

logger = logging.getLogger(__name__)


@dataclass
class TrendAnalysis:
    """Complete trend analysis results for an item."""
    item_id: int
    period: str
    direction: str
    strength: float
    momentum: float
    acceleration: float
    volatility: float
    price_change: int
    price_change_percent: float
    resistance_level: Optional[int] = None
    support_level: Optional[int] = None
    confidence: float = 0.0


@dataclass
class PatternMatch:
    """Detected price pattern with confidence and characteristics."""
    pattern_name: str
    confidence: float
    start_time: datetime
    end_time: datetime
    characteristics: Dict[str, Any]
    predicted_target: Optional[int] = None
    breakout_direction: str = 'pending'


@dataclass
class MarketSignal:
    """Market signal with trading implications."""
    signal_type: str  # 'buy', 'sell', 'hold', 'alert'
    priority: str    # 'critical', 'high', 'medium', 'low'
    message: str
    confidence: float
    price_target: Optional[int] = None
    time_horizon: str = '1h'  # '5m', '1h', '1d'


class PricePatternAnalysisService:
    """
    Advanced service for analyzing price patterns and generating trading insights.
    """
    
    def __init__(self):
        # Pattern detection configuration
        self.min_pattern_length = 5      # Minimum data points for pattern
        self.max_pattern_length = 48     # Maximum data points (48 hours)
        self.confidence_threshold = 0.7  # Minimum confidence for pattern detection
        
        # Trend analysis configuration
        self.trend_smoothing_window = 5  # Savitzky-Golay filter window
        self.momentum_periods = 3        # Periods for momentum calculation
        self.volatility_window = 10      # Window for volatility calculation
        
        # Support/resistance detection
        self.support_resistance_strength = 3  # Minimum touches for S/R level
        self.price_tolerance_percent = 2.0     # Price tolerance for S/R levels
    
    async def analyze_item_trends(self, item_id: int, 
                                 periods: List[str] = None) -> Dict[str, TrendAnalysis]:
        """
        Perform comprehensive trend analysis for an item across multiple time periods.
        
        Args:
            item_id: Item ID to analyze
            periods: List of periods to analyze ['1h', '6h', '24h', '7d']
            
        Returns:
            Dictionary mapping period -> TrendAnalysis
        """
        if periods is None:
            periods = ['1h', '6h', '24h', '7d']
        
        logger.info(f"🔍 Analyzing trends for item {item_id} across {len(periods)} periods")
        
        try:
            # Get item
            item = await self._get_item_async(item_id)
            if not item:
                return {}
            
            # Get historical data
            historical_data = await self._get_historical_data_for_analysis(item_id)
            if not historical_data:
                logger.warning(f"No historical data found for item {item_id}")
                return {}
            
            trend_results = {}
            
            # Analyze each time period
            for period in periods:
                try:
                    trend_analysis = await self._analyze_period_trend(
                        item, historical_data, period
                    )
                    if trend_analysis:
                        trend_results[period] = trend_analysis
                        
                        # Save trend to database
                        await self._save_trend_to_database(trend_analysis)
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze {period} trend for item {item_id}: {e}")
            
            logger.info(f"Completed trend analysis for item {item_id}: {len(trend_results)} periods")
            return trend_results
            
        except Exception as e:
            logger.error(f"Trend analysis failed for item {item_id}: {e}")
            return {}
    
    async def detect_price_patterns(self, item_id: int,
                                   lookback_hours: int = 48) -> List[PatternMatch]:
        """
        Detect price patterns using technical analysis and machine learning.
        
        Args:
            item_id: Item ID to analyze
            lookback_hours: Hours of historical data to analyze
            
        Returns:
            List of detected patterns with confidence scores
        """
        logger.info(f"🎯 Detecting price patterns for item {item_id}")
        
        try:
            # Get historical price data
            historical_data = await self._get_recent_historical_data(item_id, lookback_hours)
            
            if len(historical_data) < self.min_pattern_length:
                logger.debug(f"Insufficient data for pattern detection: {len(historical_data)} points")
                return []
            
            # Extract price series
            prices = np.array([point['volume_weighted_price'] for point in historical_data 
                              if point['volume_weighted_price']])
            timestamps = [point['timestamp'] for point in historical_data 
                         if point['volume_weighted_price']]
            
            if len(prices) < self.min_pattern_length:
                return []
            
            # Smooth price data for pattern detection
            if len(prices) >= self.trend_smoothing_window:
                smoothed_prices = savgol_filter(prices, 
                                              min(self.trend_smoothing_window, len(prices)//2*2-1), 
                                              2)
            else:
                smoothed_prices = prices
            
            detected_patterns = []
            
            # Detect various pattern types
            patterns_to_detect = [
                self._detect_breakout_patterns,
                self._detect_reversal_patterns,
                self._detect_consolidation_patterns,
                self._detect_trend_patterns
            ]
            
            for pattern_detector in patterns_to_detect:
                try:
                    patterns = await pattern_detector(prices, smoothed_prices, timestamps)
                    detected_patterns.extend(patterns)
                except Exception as e:
                    logger.debug(f"Pattern detector failed: {e}")
            
            # Filter by confidence and save to database
            high_confidence_patterns = [p for p in detected_patterns 
                                      if p.confidence >= self.confidence_threshold]
            
            for pattern in high_confidence_patterns:
                await self._save_pattern_to_database(item_id, pattern)
            
            logger.info(f"Detected {len(high_confidence_patterns)} high-confidence patterns for item {item_id}")
            return high_confidence_patterns
            
        except Exception as e:
            logger.error(f"Pattern detection failed for item {item_id}: {e}")
            return []
    
    async def generate_market_signals(self, item_id: int) -> List[MarketSignal]:
        """
        Generate actionable market signals based on trend and pattern analysis.
        
        Args:
            item_id: Item ID to generate signals for
            
        Returns:
            List of market signals with trading recommendations
        """
        logger.info(f"📡 Generating market signals for item {item_id}")
        
        try:
            # Get current analysis data
            trends = await self.analyze_item_trends(item_id, ['1h', '24h'])
            patterns = await self.detect_price_patterns(item_id, 24)
            
            signals = []
            
            # Generate trend-based signals
            for period, trend in trends.items():
                trend_signals = self._generate_trend_signals(trend, period)
                signals.extend(trend_signals)
            
            # Generate pattern-based signals
            for pattern in patterns:
                pattern_signals = self._generate_pattern_signals(pattern)
                signals.extend(pattern_signals)
            
            # Generate volume-based signals
            volume_signals = await self._generate_volume_signals(item_id)
            signals.extend(volume_signals)
            
            # Deduplicate and prioritize signals
            prioritized_signals = self._prioritize_signals(signals)
            
            # Create market alerts for high-priority signals
            await self._create_market_alerts(item_id, prioritized_signals)
            
            logger.info(f"Generated {len(prioritized_signals)} market signals for item {item_id}")
            return prioritized_signals
            
        except Exception as e:
            logger.error(f"Signal generation failed for item {item_id}: {e}")
            return []
    
    async def _analyze_period_trend(self, item: Item, historical_data: List[Dict], 
                                   period: str) -> Optional[TrendAnalysis]:
        """Analyze trend for a specific time period."""
        try:
            # Filter data for the period
            period_data = self._filter_data_for_period(historical_data, period)
            
            if len(period_data) < 3:
                return None
            
            # Extract price series
            prices = np.array([point['volume_weighted_price'] for point in period_data])
            timestamps = np.array([point['timestamp'].timestamp() for point in period_data])
            
            # Calculate trend metrics
            direction, strength = self._calculate_trend_direction_strength(prices)
            momentum = self._calculate_momentum(prices)
            acceleration = self._calculate_acceleration(prices)
            volatility = self._calculate_volatility(prices)
            
            # Price changes
            price_change = int(prices[-1] - prices[0])
            price_change_percent = (price_change / prices[0]) * 100 if prices[0] > 0 else 0
            
            # Support and resistance levels
            support_level, resistance_level = self._find_support_resistance(prices)
            
            # Overall confidence based on data quality and consistency
            confidence = self._calculate_trend_confidence(prices, direction, strength, len(period_data))
            
            return TrendAnalysis(
                item_id=item.item_id,
                period=period,
                direction=direction,
                strength=strength,
                momentum=momentum,
                acceleration=acceleration,
                volatility=volatility,
                price_change=price_change,
                price_change_percent=price_change_percent,
                resistance_level=resistance_level,
                support_level=support_level,
                confidence=confidence
            )
            
        except Exception as e:
            logger.warning(f"Period trend analysis failed for {period}: {e}")
            return None
    
    def _calculate_trend_direction_strength(self, prices: np.ndarray) -> Tuple[str, float]:
        """Calculate trend direction and strength using linear regression."""
        if len(prices) < 2:
            return 'sideways', 0.0
        
        # Linear regression
        x = np.arange(len(prices))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, prices)
        
        # Determine direction
        if slope > 0:
            if r_value > 0.8:
                direction = 'strong_up'
            elif r_value > 0.5:
                direction = 'up'
            else:
                direction = 'sideways'
        elif slope < 0:
            if r_value < -0.8:
                direction = 'strong_down'
            elif r_value < -0.5:
                direction = 'down'
            else:
                direction = 'sideways'
        else:
            direction = 'sideways'
        
        # Strength is absolute correlation coefficient
        strength = min(abs(r_value), 1.0)
        
        return direction, strength
    
    def _calculate_momentum(self, prices: np.ndarray) -> float:
        """Calculate price momentum indicator."""
        if len(prices) < self.momentum_periods + 1:
            return 0.0
        
        # Rate of change over momentum periods
        recent_avg = np.mean(prices[-self.momentum_periods:])
        older_avg = np.mean(prices[:-self.momentum_periods][-self.momentum_periods:])
        
        if older_avg > 0:
            momentum = (recent_avg - older_avg) / older_avg
            return np.clip(momentum, -1.0, 1.0)
        
        return 0.0
    
    def _calculate_acceleration(self, prices: np.ndarray) -> float:
        """Calculate price acceleration (second derivative)."""
        if len(prices) < 3:
            return 0.0
        
        # Calculate first derivative (velocity)
        velocity = np.diff(prices)
        
        # Calculate second derivative (acceleration)
        if len(velocity) < 2:
            return 0.0
        
        acceleration = np.diff(velocity)
        
        # Return normalized mean acceleration
        return float(np.mean(acceleration) / np.std(prices) if np.std(prices) > 0 else 0.0)
    
    def _calculate_volatility(self, prices: np.ndarray) -> float:
        """Calculate price volatility."""
        if len(prices) < 2:
            return 0.0
        
        # Calculate returns
        returns = np.diff(prices) / prices[:-1]
        
        # Return standard deviation of returns
        return float(np.std(returns))
    
    def _find_support_resistance(self, prices: np.ndarray) -> Tuple[Optional[int], Optional[int]]:
        """Find support and resistance levels using peak/valley detection."""
        if len(prices) < 5:
            return None, None
        
        try:
            # Find peaks (resistance) and valleys (support)
            peaks, _ = find_peaks(prices, prominence=np.std(prices) * 0.5)
            valleys, _ = find_peaks(-prices, prominence=np.std(prices) * 0.5)
            
            resistance_level = None
            support_level = None
            
            if len(peaks) > 0:
                # Resistance is around peak levels
                resistance_levels = prices[peaks]
                resistance_level = int(np.median(resistance_levels))
            
            if len(valleys) > 0:
                # Support is around valley levels
                support_levels = prices[valleys]
                support_level = int(np.median(support_levels))
            
            return support_level, resistance_level
            
        except Exception as e:
            logger.debug(f"Support/resistance calculation failed: {e}")
            return None, None
    
    def _calculate_trend_confidence(self, prices: np.ndarray, direction: str, 
                                  strength: float, data_points: int) -> float:
        """Calculate confidence in trend analysis."""
        # Base confidence on correlation strength
        base_confidence = strength
        
        # Adjust for data quality
        if data_points >= 20:
            data_quality_bonus = 0.1
        elif data_points >= 10:
            data_quality_bonus = 0.05
        else:
            data_quality_bonus = 0.0
        
        # Adjust for trend clarity
        if direction in ['strong_up', 'strong_down']:
            clarity_bonus = 0.1
        elif direction in ['up', 'down']:
            clarity_bonus = 0.05
        else:
            clarity_bonus = 0.0
        
        # Final confidence
        confidence = min(base_confidence + data_quality_bonus + clarity_bonus, 1.0)
        
        return confidence
    
    async def _detect_breakout_patterns(self, prices: np.ndarray, smoothed: np.ndarray, 
                                       timestamps: List[datetime]) -> List[PatternMatch]:
        """Detect breakout patterns in price data."""
        patterns = []
        
        try:
            # Look for consolidation followed by breakout
            for i in range(len(smoothed) - 10):
                window = smoothed[i:i+10]
                
                # Check for consolidation (low volatility)
                if len(window) >= 5:
                    volatility = np.std(window)
                    mean_price = np.mean(window)
                    
                    # Low volatility indicates consolidation
                    if volatility < (mean_price * 0.05):  # Less than 5% volatility
                        
                        # Check for breakout after consolidation
                        if i + 12 < len(smoothed):
                            post_consolidation = smoothed[i+10:i+12]
                            
                            # Upward breakout
                            if np.mean(post_consolidation) > mean_price * 1.03:  # 3% breakout
                                pattern = PatternMatch(
                                    pattern_name='breakout_up',
                                    confidence=0.7 + min(0.2, (np.mean(post_consolidation) - mean_price) / mean_price * 10),
                                    start_time=timestamps[i],
                                    end_time=timestamps[min(i+12, len(timestamps)-1)],
                                    characteristics={
                                        'consolidation_range': float(volatility),
                                        'breakout_strength': float((np.mean(post_consolidation) - mean_price) / mean_price),
                                        'base_price': float(mean_price)
                                    },
                                    predicted_target=int(mean_price * 1.08),  # 8% target
                                    breakout_direction='up'
                                )
                                patterns.append(pattern)
                            
                            # Downward breakout
                            elif np.mean(post_consolidation) < mean_price * 0.97:  # 3% breakdown
                                pattern = PatternMatch(
                                    pattern_name='breakout_down',
                                    confidence=0.7 + min(0.2, (mean_price - np.mean(post_consolidation)) / mean_price * 10),
                                    start_time=timestamps[i],
                                    end_time=timestamps[min(i+12, len(timestamps)-1)],
                                    characteristics={
                                        'consolidation_range': float(volatility),
                                        'breakdown_strength': float((mean_price - np.mean(post_consolidation)) / mean_price),
                                        'base_price': float(mean_price)
                                    },
                                    predicted_target=int(mean_price * 0.92),  # 8% target down
                                    breakout_direction='down'
                                )
                                patterns.append(pattern)
        
        except Exception as e:
            logger.debug(f"Breakout pattern detection failed: {e}")
        
        return patterns
    
    async def _detect_reversal_patterns(self, prices: np.ndarray, smoothed: np.ndarray,
                                       timestamps: List[datetime]) -> List[PatternMatch]:
        """Detect reversal patterns in price data."""
        patterns = []
        
        try:
            # Look for trend reversals
            if len(smoothed) >= 10:
                # Calculate moving averages for trend detection
                short_ma = np.convolve(smoothed, np.ones(3)/3, mode='valid')
                long_ma = np.convolve(smoothed, np.ones(7)/7, mode='valid')
                
                # Find crossover points
                for i in range(1, min(len(short_ma), len(long_ma))):
                    # Bullish reversal (short MA crosses above long MA)
                    if short_ma[i] > long_ma[i] and short_ma[i-1] <= long_ma[i-1]:
                        # Confirm with price action
                        current_idx = i + 6  # Adjust for MA lag
                        if current_idx < len(prices):
                            pattern = PatternMatch(
                                pattern_name='reversal_up',
                                confidence=0.6 + min(0.3, abs(short_ma[i] - long_ma[i]) / long_ma[i] * 20),
                                start_time=timestamps[max(0, current_idx-5)],
                                end_time=timestamps[min(current_idx+2, len(timestamps)-1)],
                                characteristics={
                                    'reversal_strength': float(abs(short_ma[i] - long_ma[i]) / long_ma[i]),
                                    'base_price': float(long_ma[i])
                                },
                                predicted_target=int(prices[current_idx] * 1.05),
                                breakout_direction='up'
                            )
                            patterns.append(pattern)
                    
                    # Bearish reversal (short MA crosses below long MA)
                    elif short_ma[i] < long_ma[i] and short_ma[i-1] >= long_ma[i-1]:
                        current_idx = i + 6
                        if current_idx < len(prices):
                            pattern = PatternMatch(
                                pattern_name='reversal_down',
                                confidence=0.6 + min(0.3, abs(short_ma[i] - long_ma[i]) / long_ma[i] * 20),
                                start_time=timestamps[max(0, current_idx-5)],
                                end_time=timestamps[min(current_idx+2, len(timestamps)-1)],
                                characteristics={
                                    'reversal_strength': float(abs(short_ma[i] - long_ma[i]) / long_ma[i]),
                                    'base_price': float(long_ma[i])
                                },
                                predicted_target=int(prices[current_idx] * 0.95),
                                breakout_direction='down'
                            )
                            patterns.append(pattern)
        
        except Exception as e:
            logger.debug(f"Reversal pattern detection failed: {e}")
        
        return patterns
    
    async def _detect_consolidation_patterns(self, prices: np.ndarray, smoothed: np.ndarray,
                                           timestamps: List[datetime]) -> List[PatternMatch]:
        """Detect consolidation/sideways patterns."""
        patterns = []
        
        try:
            # Look for extended periods of low volatility
            window_size = 8
            
            for i in range(len(smoothed) - window_size):
                window = smoothed[i:i+window_size]
                volatility = np.std(window)
                mean_price = np.mean(window)
                
                # Low volatility indicates consolidation
                if volatility < (mean_price * 0.03):  # Less than 3% volatility
                    pattern = PatternMatch(
                        pattern_name='consolidation',
                        confidence=0.7 - min(0.2, volatility / (mean_price * 0.03)),
                        start_time=timestamps[i],
                        end_time=timestamps[i+window_size-1],
                        characteristics={
                            'consolidation_range': float(volatility),
                            'consolidation_center': float(mean_price),
                            'duration_periods': window_size
                        },
                        breakout_direction='pending'
                    )
                    patterns.append(pattern)
        
        except Exception as e:
            logger.debug(f"Consolidation pattern detection failed: {e}")
        
        return patterns
    
    async def _detect_trend_patterns(self, prices: np.ndarray, smoothed: np.ndarray,
                                    timestamps: List[datetime]) -> List[PatternMatch]:
        """Detect sustained trend patterns."""
        patterns = []
        
        try:
            # Look for sustained trends
            min_trend_length = 6
            
            for start_idx in range(len(smoothed) - min_trend_length):
                for end_idx in range(start_idx + min_trend_length, len(smoothed)):
                    trend_data = smoothed[start_idx:end_idx]
                    
                    # Calculate trend strength
                    x = np.arange(len(trend_data))
                    slope, intercept, r_value, p_value, std_err = stats.linregress(x, trend_data)
                    
                    # Strong uptrend
                    if r_value > 0.7 and slope > 0:
                        pattern = PatternMatch(
                            pattern_name='steady_growth',
                            confidence=min(0.9, r_value + 0.1),
                            start_time=timestamps[start_idx],
                            end_time=timestamps[end_idx-1],
                            characteristics={
                                'trend_strength': float(r_value),
                                'slope': float(slope),
                                'duration_periods': end_idx - start_idx
                            },
                            predicted_target=int(trend_data[-1] + slope * 3),  # Project 3 periods ahead
                            breakout_direction='up'
                        )
                        patterns.append(pattern)
                        break  # Don't overlap patterns
                    
                    # Strong downtrend
                    elif r_value < -0.7 and slope < 0:
                        pattern = PatternMatch(
                            pattern_name='steady_decline',
                            confidence=min(0.9, abs(r_value) + 0.1),
                            start_time=timestamps[start_idx],
                            end_time=timestamps[end_idx-1],
                            characteristics={
                                'trend_strength': float(abs(r_value)),
                                'slope': float(slope),
                                'duration_periods': end_idx - start_idx
                            },
                            predicted_target=int(trend_data[-1] + slope * 3),
                            breakout_direction='down'
                        )
                        patterns.append(pattern)
                        break
        
        except Exception as e:
            logger.debug(f"Trend pattern detection failed: {e}")
        
        return patterns
    
    def _generate_trend_signals(self, trend: TrendAnalysis, period: str) -> List[MarketSignal]:
        """Generate trading signals based on trend analysis."""
        signals = []
        
        try:
            # Strong uptrend signals
            if trend.direction == 'strong_up' and trend.confidence > 0.7:
                signals.append(MarketSignal(
                    signal_type='buy',
                    priority='high' if period == '1h' else 'medium',
                    message=f"Strong uptrend detected ({period}): {trend.strength:.2f} strength, {trend.price_change_percent:+.1f}%",
                    confidence=trend.confidence,
                    price_target=trend.resistance_level,
                    time_horizon=period
                ))
            
            # Strong downtrend signals
            elif trend.direction == 'strong_down' and trend.confidence > 0.7:
                signals.append(MarketSignal(
                    signal_type='sell',
                    priority='high' if period == '1h' else 'medium',
                    message=f"Strong downtrend detected ({period}): {trend.strength:.2f} strength, {trend.price_change_percent:+.1f}%",
                    confidence=trend.confidence,
                    price_target=trend.support_level,
                    time_horizon=period
                ))
            
            # High momentum signals
            if abs(trend.momentum) > 0.5 and trend.confidence > 0.6:
                direction = 'bullish' if trend.momentum > 0 else 'bearish'
                signals.append(MarketSignal(
                    signal_type='alert',
                    priority='medium',
                    message=f"High {direction} momentum ({period}): {trend.momentum:+.2f}",
                    confidence=trend.confidence,
                    time_horizon=period
                ))
            
            # Volatility alerts
            if trend.volatility > 0.15:  # High volatility
                signals.append(MarketSignal(
                    signal_type='alert',
                    priority='low',
                    message=f"High volatility warning ({period}): {trend.volatility:.2f}",
                    confidence=0.8,
                    time_horizon=period
                ))
        
        except Exception as e:
            logger.debug(f"Trend signal generation failed: {e}")
        
        return signals
    
    def _generate_pattern_signals(self, pattern: PatternMatch) -> List[MarketSignal]:
        """Generate trading signals based on detected patterns."""
        signals = []
        
        try:
            # Breakout signals
            if pattern.pattern_name in ['breakout_up', 'breakout_down']:
                signal_type = 'buy' if pattern.breakout_direction == 'up' else 'sell'
                priority = 'high' if pattern.confidence > 0.8 else 'medium'
                
                signals.append(MarketSignal(
                    signal_type=signal_type,
                    priority=priority,
                    message=f"{pattern.pattern_name.title()} pattern detected with {pattern.confidence:.1%} confidence",
                    confidence=pattern.confidence,
                    price_target=pattern.predicted_target,
                    time_horizon='1h'
                ))
            
            # Reversal signals
            elif pattern.pattern_name in ['reversal_up', 'reversal_down']:
                signal_type = 'buy' if pattern.breakout_direction == 'up' else 'sell'
                
                signals.append(MarketSignal(
                    signal_type=signal_type,
                    priority='medium',
                    message=f"Trend reversal pattern: {pattern.pattern_name} ({pattern.confidence:.1%} confidence)",
                    confidence=pattern.confidence,
                    price_target=pattern.predicted_target,
                    time_horizon='6h'
                ))
            
            # Consolidation signals
            elif pattern.pattern_name == 'consolidation':
                signals.append(MarketSignal(
                    signal_type='hold',
                    priority='low',
                    message=f"Price consolidation detected - expect breakout soon",
                    confidence=pattern.confidence,
                    time_horizon='1h'
                ))
        
        except Exception as e:
            logger.debug(f"Pattern signal generation failed: {e}")
        
        return signals
    
    async def _generate_volume_signals(self, item_id: int) -> List[MarketSignal]:
        """Generate signals based on volume analysis."""
        signals = []
        
        try:
            # Get recent volume data
            recent_points = await self._get_recent_historical_data(item_id, 6)  # Last 6 hours
            
            if len(recent_points) < 3:
                return signals
            
            volumes = [point.get('total_volume', 0) for point in recent_points]
            avg_volume = np.mean(volumes)
            current_volume = volumes[-1] if volumes else 0
            
            # Volume surge detection
            if current_volume > avg_volume * 2 and avg_volume > 0:
                signals.append(MarketSignal(
                    signal_type='alert',
                    priority='high',
                    message=f"Volume surge detected: {current_volume:,} vs avg {avg_volume:,.0f}",
                    confidence=0.8,
                    time_horizon='1h'
                ))
            
            # Volume dry-up
            elif current_volume < avg_volume * 0.3 and avg_volume > 100:
                signals.append(MarketSignal(
                    signal_type='alert',
                    priority='medium',
                    message=f"Volume declining: {current_volume:,} vs avg {avg_volume:,.0f}",
                    confidence=0.7,
                    time_horizon='1h'
                ))
        
        except Exception as e:
            logger.debug(f"Volume signal generation failed: {e}")
        
        return signals
    
    def _prioritize_signals(self, signals: List[MarketSignal]) -> List[MarketSignal]:
        """Prioritize and deduplicate signals."""
        # Sort by priority and confidence
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        
        sorted_signals = sorted(signals, 
                              key=lambda s: (priority_order.get(s.priority, 3), -s.confidence))
        
        # Remove duplicates (keep highest priority/confidence)
        seen_types = set()
        unique_signals = []
        
        for signal in sorted_signals:
            signal_key = f"{signal.signal_type}_{signal.time_horizon}"
            if signal_key not in seen_types:
                unique_signals.append(signal)
                seen_types.add(signal_key)
        
        return unique_signals[:10]  # Limit to top 10 signals
    
    # Database and utility methods
    async def _get_item_async(self, item_id: int) -> Optional[Item]:
        """Get item from database asynchronously."""
        try:
            return await asyncio.to_thread(Item.objects.get, item_id=item_id)
        except Item.DoesNotExist:
            return None
    
    async def _get_historical_data_for_analysis(self, item_id: int) -> List[Dict]:
        """Get historical price data for analysis."""
        def get_data():
            # Get last 7 days of data from both intervals
            cutoff_time = timezone.now() - timedelta(days=7)
            
            points_5m = HistoricalPricePoint.objects.filter(
                item__item_id=item_id,
                interval='5m',
                timestamp__gte=cutoff_time,
                total_volume__gt=0
            ).order_by('timestamp').values(
                'timestamp', 'volume_weighted_price', 'total_volume', 
                'avg_high_price', 'avg_low_price'
            )
            
            points_1h = HistoricalPricePoint.objects.filter(
                item__item_id=item_id,
                interval='1h',
                timestamp__gte=cutoff_time,
                total_volume__gt=0
            ).order_by('timestamp').values(
                'timestamp', 'volume_weighted_price', 'total_volume',
                'avg_high_price', 'avg_low_price'
            )
            
            # Combine and sort by timestamp
            all_points = list(points_5m) + list(points_1h)
            all_points.sort(key=lambda x: x['timestamp'])
            
            return all_points
        
        return await asyncio.to_thread(get_data)
    
    async def _get_recent_historical_data(self, item_id: int, hours: int) -> List[Dict]:
        """Get recent historical data for pattern detection."""
        def get_data():
            cutoff_time = timezone.now() - timedelta(hours=hours)
            
            return list(HistoricalPricePoint.objects.filter(
                item__item_id=item_id,
                timestamp__gte=cutoff_time
            ).order_by('timestamp').values(
                'timestamp', 'volume_weighted_price', 'total_volume',
                'avg_high_price', 'avg_low_price', 'interval'
            ))
        
        return await asyncio.to_thread(get_data)
    
    def _filter_data_for_period(self, data: List[Dict], period: str) -> List[Dict]:
        """Filter historical data for specific time period."""
        now = timezone.now()
        
        period_hours = {
            '1h': 1,
            '6h': 6, 
            '24h': 24,
            '7d': 168
        }
        
        hours = period_hours.get(period, 24)
        cutoff_time = now - timedelta(hours=hours)
        
        return [point for point in data if point['timestamp'] >= cutoff_time]
    
    async def _save_trend_to_database(self, trend: TrendAnalysis):
        """Save trend analysis to database."""
        def save_trend():
            try:
                item = Item.objects.get(item_id=trend.item_id)
                
                PriceTrend.objects.update_or_create(
                    item=item,
                    analysis_period=trend.period,
                    defaults={
                        'direction': trend.direction,
                        'strength': trend.strength,
                        'momentum': trend.momentum,
                        'acceleration': trend.acceleration,
                        'volatility': trend.volatility,
                        'price_change': trend.price_change,
                        'price_change_percent': trend.price_change_percent,
                        'resistance_level': trend.resistance_level,
                        'support_level': trend.support_level,
                        'data_points_used': 10,  # Approximate
                        'analysis_quality': 'good' if trend.confidence > 0.7 else 'fair'
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to save trend to database: {e}")
        
        await asyncio.to_thread(save_trend)
    
    async def _save_pattern_to_database(self, item_id: int, pattern: PatternMatch):
        """Save detected pattern to database."""
        def save_pattern():
            try:
                item = Item.objects.get(item_id=item_id)
                
                duration_hours = (pattern.end_time - pattern.start_time).total_seconds() / 3600
                
                PricePattern.objects.create(
                    item=item,
                    pattern_name=pattern.pattern_name,
                    start_time=pattern.start_time,
                    end_time=pattern.end_time,
                    duration_hours=duration_hours,
                    confidence_score=pattern.confidence,
                    breakout_direction=pattern.breakout_direction,
                    predicted_target=pattern.predicted_target,
                    feature_vector=pattern.characteristics,
                    start_price=int(pattern.characteristics.get('base_price', 0)),
                    end_price=int(pattern.characteristics.get('base_price', 0)),
                    high_price=int(pattern.characteristics.get('base_price', 0) * 1.05),
                    low_price=int(pattern.characteristics.get('base_price', 0) * 0.95),
                    price_range=int(pattern.characteristics.get('base_price', 0) * 0.1),
                    average_volume=1000  # Placeholder
                )
            except Exception as e:
                logger.warning(f"Failed to save pattern to database: {e}")
        
        await asyncio.to_thread(save_pattern)
    
    async def _create_market_alerts(self, item_id: int, signals: List[MarketSignal]):
        """Create market alerts for high-priority signals."""
        def create_alerts():
            try:
                item = Item.objects.get(item_id=item_id)
                
                for signal in signals:
                    if signal.priority in ['critical', 'high']:
                        # Map signal types to alert types
                        alert_type_map = {
                            'buy': 'opportunity',
                            'sell': 'risk_warning',
                            'alert': 'pattern_detected',
                            'hold': 'pattern_detected'
                        }
                        
                        MarketAlert.objects.create(
                            item=item,
                            alert_type=alert_type_map.get(signal.signal_type, 'pattern_detected'),
                            priority=signal.priority,
                            title=f"{signal.signal_type.title()} Signal - {item.name}",
                            message=signal.message,
                            confidence_score=signal.confidence,
                            trigger_price=signal.price_target,
                            expires_at=timezone.now() + timedelta(hours=6)
                        )
            except Exception as e:
                logger.warning(f"Failed to create market alerts: {e}")
        
        await asyncio.to_thread(create_alerts)