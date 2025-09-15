"""
Technical Analysis Engine for OSRS Trading Terminal

Provides multi-timeframe technical analysis indicators optimized for MacBook M1 8GB RAM.
Uses efficient numpy/pandas calculations without heavy ML training.

Features:
- RSI, MACD, Bollinger Bands, Moving Averages
- Multiple timeframes (5m, 15m, 1h, 4h, 1d)
- Volume-based indicators (OBV, Volume Profile)
- Custom OSRS-specific indicators
- Signal generation and strength scoring
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class TechnicalAnalysisEngine:
    """
    Multi-timeframe technical analysis engine optimized for OSRS market data.
    """
    
    def __init__(self):
        self.timeframes = {
            '5m': 5,      # 5 minutes
            '15m': 15,    # 15 minutes  
            '1h': 60,     # 1 hour
            '4h': 240,    # 4 hours
            '1d': 1440,   # 1 day
        }
        
        # Default periods for indicators
        self.default_periods = {
            'rsi': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2.0,
            'sma_short': 10,
            'sma_long': 50,
            'ema_short': 12,
            'ema_long': 26,
        }
        
        # Signal strength thresholds
        self.signal_thresholds = {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'rsi_strong_oversold': 20,
            'rsi_strong_overbought': 80,
            'volume_spike_threshold': 2.0,  # 200% of average
            'momentum_threshold': 0.05,     # 5% price change
        }
    
    async def analyze_item_technical(
        self, 
        item_id: int, 
        timeframes: List[str] = None,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Perform comprehensive technical analysis for an item across multiple timeframes.
        """
        try:
            timeframes = timeframes or ['1h', '4h', '1d']
            
            # Get price data for analysis
            price_data = await self._get_price_data(item_id, lookback_days)
            
            if price_data.empty:
                return {'error': f'No price data found for item {item_id}'}
            
            # Prepare analysis results
            analysis_results = {
                'item_id': item_id,
                'analysis_timestamp': timezone.now(),
                'timeframes': {},
                'overall_signals': {},
                'strength_score': 0,
                'recommendation': 'neutral'
            }
            
            # Analyze each timeframe
            for timeframe in timeframes:
                tf_data = await self._prepare_timeframe_data(price_data, timeframe)
                
                if len(tf_data) < 50:  # Need minimum data points
                    continue
                
                tf_analysis = await self._analyze_timeframe(tf_data, timeframe)
                analysis_results['timeframes'][timeframe] = tf_analysis
            
            # Generate overall signals and recommendation
            analysis_results['overall_signals'] = await self._generate_overall_signals(analysis_results['timeframes'])
            analysis_results['strength_score'] = await self._calculate_strength_score(analysis_results['timeframes'])
            analysis_results['recommendation'] = await self._generate_recommendation(analysis_results)
            
            return analysis_results
            
        except Exception as e:
            logger.exception(f"Technical analysis failed for item {item_id}")
            return {'error': str(e)}
    
    async def _get_price_data(self, item_id: int, lookback_days: int) -> pd.DataFrame:
        """Get price data for technical analysis."""
        try:
            from apps.prices.models import Price
            
            cutoff_date = timezone.now() - timedelta(days=lookback_days)
            
            prices = await sync_to_async(list)(
                Price.objects.filter(
                    item_id=item_id,
                    created_at__gte=cutoff_date
                ).order_by('created_at').values(
                    'created_at', 'high_price', 'low_price', 'volume'
                )
            )
            
            if not prices:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(prices)
            df['timestamp'] = pd.to_datetime(df['created_at'])
            df['price'] = df['high_price']  # Use high price as main price
            df['volume'] = df['volume'].fillna(0)
            
            # Calculate OHLC data (using single price point)
            df['open'] = df['price']
            df['high'] = df['high_price']
            df['low'] = df['low_price']
            df['close'] = df['price']
            
            return df.set_index('timestamp').sort_index()
            
        except Exception as e:
            logger.exception(f"Failed to get price data for item {item_id}")
            return pd.DataFrame()
    
    async def _prepare_timeframe_data(self, price_data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Prepare data for specific timeframe analysis."""
        try:
            if timeframe not in self.timeframes:
                return pd.DataFrame()
            
            minutes = self.timeframes[timeframe]
            
            # Resample data to timeframe
            resampled = price_data.resample(f'{minutes}T').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'price': 'last',
                'volume': 'sum'
            }).dropna()
            
            # Forward fill missing values
            resampled = resampled.fillna(method='ffill')
            
            return resampled
            
        except Exception as e:
            logger.exception(f"Failed to prepare timeframe data for {timeframe}")
            return pd.DataFrame()
    
    async def _analyze_timeframe(self, data: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """Analyze a specific timeframe with all technical indicators."""
        try:
            analysis = {
                'timeframe': timeframe,
                'data_points': len(data),
                'indicators': {},
                'signals': {},
                'trend_analysis': {},
                'volume_analysis': {},
            }
            
            # Calculate all technical indicators
            indicators = await self._calculate_all_indicators(data)
            analysis['indicators'] = indicators
            
            # Generate signals from indicators
            signals = await self._generate_signals(indicators, data)
            analysis['signals'] = signals
            
            # Trend analysis
            trend_analysis = await self._analyze_trend(data, indicators)
            analysis['trend_analysis'] = trend_analysis
            
            # Volume analysis
            volume_analysis = await self._analyze_volume(data)
            analysis['volume_analysis'] = volume_analysis
            
            return analysis
            
        except Exception as e:
            logger.exception(f"Failed to analyze timeframe {timeframe}")
            return {'error': str(e)}
    
    async def _calculate_all_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all technical indicators for the given data."""
        indicators = {}
        
        try:
            prices = data['close'].values
            volumes = data['volume'].values
            highs = data['high'].values
            lows = data['low'].values
            
            # Moving Averages
            indicators['sma_short'] = await self._calculate_sma(prices, self.default_periods['sma_short'])
            indicators['sma_long'] = await self._calculate_sma(prices, self.default_periods['sma_long'])
            indicators['ema_short'] = await self._calculate_ema(prices, self.default_periods['ema_short'])
            indicators['ema_long'] = await self._calculate_ema(prices, self.default_periods['ema_long'])
            
            # RSI
            indicators['rsi'] = await self._calculate_rsi(prices, self.default_periods['rsi'])
            
            # MACD
            macd_line, macd_signal, macd_histogram = await self._calculate_macd(
                prices, 
                self.default_periods['macd_fast'], 
                self.default_periods['macd_slow'],
                self.default_periods['macd_signal']
            )
            indicators['macd'] = {
                'macd_line': macd_line,
                'signal_line': macd_signal,
                'histogram': macd_histogram
            }
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = await self._calculate_bollinger_bands(
                prices,
                self.default_periods['bb_period'],
                self.default_periods['bb_std']
            )
            indicators['bollinger_bands'] = {
                'upper': bb_upper,
                'middle': bb_middle,
                'lower': bb_lower
            }
            
            # Volume indicators
            indicators['obv'] = await self._calculate_obv(prices, volumes)
            indicators['volume_sma'] = await self._calculate_sma(volumes, 20)
            
            # Custom OSRS indicators
            indicators['osrs_momentum'] = await self._calculate_osrs_momentum(prices, volumes)
            indicators['flip_probability'] = await self._calculate_flip_probability(data)
            
            # Price action patterns
            indicators['support_resistance'] = await self._identify_support_resistance(highs, lows, prices)
            
            return indicators
            
        except Exception as e:
            logger.exception("Failed to calculate technical indicators")
            return {}
    
    async def _calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return np.array([])
        
        return pd.Series(prices).rolling(window=period).mean().values
    
    async def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return np.array([])
        
        return pd.Series(prices).ewm(span=period).mean().values
    
    async def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return np.array([])
        
        delta = np.diff(prices)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = pd.Series(gain).rolling(window=period).mean()
        avg_loss = pd.Series(loss).rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.values
    
    async def _calculate_macd(
        self, 
        prices: np.ndarray, 
        fast_period: int = 12, 
        slow_period: int = 26, 
        signal_period: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        if len(prices) < slow_period:
            return np.array([]), np.array([]), np.array([])
        
        ema_fast = await self._calculate_ema(prices, fast_period)
        ema_slow = await self._calculate_ema(prices, slow_period)
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line
        signal_line = await self._calculate_ema(macd_line, signal_period)
        
        # Histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    async def _calculate_bollinger_bands(
        self, 
        prices: np.ndarray, 
        period: int = 20, 
        std_dev: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return np.array([]), np.array([]), np.array([])
        
        sma = await self._calculate_sma(prices, period)
        rolling_std = pd.Series(prices).rolling(window=period).std().values
        
        upper_band = sma + (rolling_std * std_dev)
        lower_band = sma - (rolling_std * std_dev)
        
        return upper_band, sma, lower_band
    
    async def _calculate_obv(self, prices: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        """Calculate On-Balance Volume."""
        if len(prices) < 2 or len(volumes) < 2:
            return np.array([])
        
        price_changes = np.diff(prices)
        obv = np.zeros(len(volumes))
        
        for i in range(1, len(obv)):
            if price_changes[i-1] > 0:
                obv[i] = obv[i-1] + volumes[i]
            elif price_changes[i-1] < 0:
                obv[i] = obv[i-1] - volumes[i]
            else:
                obv[i] = obv[i-1]
        
        return obv
    
    async def _calculate_osrs_momentum(self, prices: np.ndarray, volumes: np.ndarray) -> Dict[str, float]:
        """Calculate OSRS-specific momentum indicator."""
        try:
            if len(prices) < 10:
                return {'momentum': 0, 'volume_momentum': 0, 'combined_score': 0}
            
            # Price momentum (rate of change)
            price_momentum = (prices[-1] / prices[-10] - 1) * 100 if prices[-10] != 0 else 0
            
            # Volume momentum
            recent_volume = np.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[-1]
            past_volume = np.mean(volumes[-15:-5]) if len(volumes) >= 15 else np.mean(volumes[:-5])
            volume_momentum = (recent_volume / past_volume - 1) * 100 if past_volume > 0 else 0
            
            # Combined score
            combined_score = (price_momentum * 0.7) + (volume_momentum * 0.3)
            
            return {
                'momentum': price_momentum,
                'volume_momentum': volume_momentum,
                'combined_score': combined_score
            }
            
        except Exception as e:
            logger.exception("Failed to calculate OSRS momentum")
            return {'momentum': 0, 'volume_momentum': 0, 'combined_score': 0}
    
    async def _calculate_flip_probability(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate probability of successful flip based on technical patterns."""
        try:
            if len(data) < 20:
                return {'probability': 0.5, 'confidence': 0.3}
            
            recent_data = data.tail(20)
            
            # Volatility measure
            price_std = recent_data['close'].std()
            price_mean = recent_data['close'].mean()
            volatility = (price_std / price_mean) if price_mean > 0 else 0
            
            # Volume consistency
            volume_std = recent_data['volume'].std()
            volume_mean = recent_data['volume'].mean()
            volume_consistency = 1 - (volume_std / volume_mean) if volume_mean > 0 else 0
            
            # Trend strength
            price_trend = (recent_data['close'].iloc[-1] / recent_data['close'].iloc[0] - 1)
            trend_strength = min(abs(price_trend), 0.1) / 0.1  # Normalize to 0-1
            
            # Calculate probability
            probability = 0.5 + (volume_consistency * 0.2) + (trend_strength * 0.2) - (volatility * 0.3)
            probability = max(0.1, min(0.9, probability))  # Clamp between 0.1 and 0.9
            
            # Confidence based on data quality
            confidence = min(len(data) / 50, 1.0) * 0.8  # Max 0.8 confidence
            
            return {'probability': probability, 'confidence': confidence}
            
        except Exception as e:
            logger.exception("Failed to calculate flip probability")
            return {'probability': 0.5, 'confidence': 0.3}
    
    async def _identify_support_resistance(
        self, 
        highs: np.ndarray, 
        lows: np.ndarray, 
        prices: np.ndarray
    ) -> Dict[str, List[float]]:
        """Identify support and resistance levels."""
        try:
            if len(prices) < 20:
                return {'support_levels': [], 'resistance_levels': []}
            
            # Simple peak/trough detection
            from scipy.signal import argrelextrema
            
            # Find local minima (support) and maxima (resistance)
            support_indices = argrelextrema(lows, np.less, order=5)[0]
            resistance_indices = argrelextrema(highs, np.greater, order=5)[0]
            
            # Get significant levels (recent and strong)
            current_price = prices[-1]
            
            support_levels = []
            resistance_levels = []
            
            # Filter support levels within reasonable range
            for idx in support_indices[-10:]:  # Last 10 support points
                level = lows[idx]
                if 0.9 * current_price <= level <= 1.1 * current_price:
                    support_levels.append(float(level))
            
            # Filter resistance levels
            for idx in resistance_indices[-10:]:  # Last 10 resistance points
                level = highs[idx]
                if 0.9 * current_price <= level <= 1.1 * current_price:
                    resistance_levels.append(float(level))
            
            return {
                'support_levels': sorted(list(set(support_levels))),
                'resistance_levels': sorted(list(set(resistance_levels)))
            }
            
        except Exception as e:
            logger.exception("Failed to identify support/resistance levels")
            return {'support_levels': [], 'resistance_levels': []}
    
    async def _generate_signals(self, indicators: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
        """Generate trading signals from technical indicators."""
        signals = {
            'rsi_signals': {},
            'macd_signals': {},
            'ma_signals': {},
            'bollinger_signals': {},
            'volume_signals': {},
            'overall_signal': 'neutral',
            'signal_strength': 0
        }
        
        try:
            current_price = data['close'].iloc[-1]
            
            # RSI Signals
            if 'rsi' in indicators and len(indicators['rsi']) > 0:
                current_rsi = indicators['rsi'][-1]
                if current_rsi < self.signal_thresholds['rsi_oversold']:
                    signals['rsi_signals']['signal'] = 'buy'
                    signals['rsi_signals']['strength'] = (self.signal_thresholds['rsi_oversold'] - current_rsi) / 10
                elif current_rsi > self.signal_thresholds['rsi_overbought']:
                    signals['rsi_signals']['signal'] = 'sell'
                    signals['rsi_signals']['strength'] = (current_rsi - self.signal_thresholds['rsi_overbought']) / 10
                else:
                    signals['rsi_signals']['signal'] = 'neutral'
                    signals['rsi_signals']['strength'] = 0
            
            # MACD Signals
            if 'macd' in indicators:
                macd_data = indicators['macd']
                if (len(macd_data['macd_line']) > 1 and 
                    len(macd_data['signal_line']) > 1):
                    
                    macd_current = macd_data['macd_line'][-1]
                    macd_previous = macd_data['macd_line'][-2]
                    signal_current = macd_data['signal_line'][-1]
                    signal_previous = macd_data['signal_line'][-2]
                    
                    # MACD crossover signals
                    if (macd_previous <= signal_previous and macd_current > signal_current):
                        signals['macd_signals']['signal'] = 'buy'
                        signals['macd_signals']['strength'] = min(abs(macd_current - signal_current) / current_price, 0.1) * 10
                    elif (macd_previous >= signal_previous and macd_current < signal_current):
                        signals['macd_signals']['signal'] = 'sell'
                        signals['macd_signals']['strength'] = min(abs(macd_current - signal_current) / current_price, 0.1) * 10
                    else:
                        signals['macd_signals']['signal'] = 'neutral'
                        signals['macd_signals']['strength'] = 0
            
            # Moving Average Signals
            if ('sma_short' in indicators and 'sma_long' in indicators and 
                len(indicators['sma_short']) > 1 and len(indicators['sma_long']) > 1):
                
                sma_short_current = indicators['sma_short'][-1]
                sma_long_current = indicators['sma_long'][-1]
                
                if sma_short_current > sma_long_current:
                    signals['ma_signals']['signal'] = 'buy'
                    signals['ma_signals']['strength'] = min((sma_short_current / sma_long_current - 1) * 10, 1.0)
                else:
                    signals['ma_signals']['signal'] = 'sell'
                    signals['ma_signals']['strength'] = min((sma_long_current / sma_short_current - 1) * 10, 1.0)
            
            # Bollinger Bands Signals
            if 'bollinger_bands' in indicators:
                bb = indicators['bollinger_bands']
                if (len(bb['upper']) > 0 and len(bb['lower']) > 0):
                    bb_upper = bb['upper'][-1]
                    bb_lower = bb['lower'][-1]
                    
                    if current_price <= bb_lower:
                        signals['bollinger_signals']['signal'] = 'buy'
                        signals['bollinger_signals']['strength'] = (bb_lower - current_price) / bb_lower
                    elif current_price >= bb_upper:
                        signals['bollinger_signals']['signal'] = 'sell'
                        signals['bollinger_signals']['strength'] = (current_price - bb_upper) / bb_upper
                    else:
                        signals['bollinger_signals']['signal'] = 'neutral'
                        signals['bollinger_signals']['strength'] = 0
            
            # Volume Signals
            if 'volume_sma' in indicators and len(indicators['volume_sma']) > 0:
                current_volume = data['volume'].iloc[-1]
                avg_volume = indicators['volume_sma'][-1]
                
                if current_volume > avg_volume * self.signal_thresholds['volume_spike_threshold']:
                    signals['volume_signals']['signal'] = 'strong_volume'
                    signals['volume_signals']['strength'] = min(current_volume / avg_volume, 5.0) / 5.0
                else:
                    signals['volume_signals']['signal'] = 'normal_volume'
                    signals['volume_signals']['strength'] = 0
            
            # Generate overall signal
            signals['overall_signal'], signals['signal_strength'] = await self._calculate_overall_signal(signals)
            
            return signals
            
        except Exception as e:
            logger.exception("Failed to generate signals")
            return signals
    
    async def _calculate_overall_signal(self, signals: Dict[str, Any]) -> Tuple[str, float]:
        """Calculate overall signal from individual indicator signals."""
        try:
            buy_score = 0
            sell_score = 0
            total_weight = 0
            
            # Weight different signals
            signal_weights = {
                'rsi_signals': 0.25,
                'macd_signals': 0.3,
                'ma_signals': 0.2,
                'bollinger_signals': 0.15,
                'volume_signals': 0.1
            }
            
            for signal_type, weight in signal_weights.items():
                if signal_type in signals and 'signal' in signals[signal_type]:
                    signal = signals[signal_type]['signal']
                    strength = signals[signal_type].get('strength', 0)
                    
                    if signal == 'buy':
                        buy_score += strength * weight
                    elif signal == 'sell':
                        sell_score += strength * weight
                    
                    total_weight += weight
            
            # Normalize scores
            if total_weight > 0:
                buy_score /= total_weight
                sell_score /= total_weight
            
            # Determine overall signal
            net_score = buy_score - sell_score
            signal_strength = abs(net_score)
            
            if net_score > 0.3:
                return 'buy', signal_strength
            elif net_score < -0.3:
                return 'sell', signal_strength
            else:
                return 'neutral', signal_strength
                
        except Exception as e:
            logger.exception("Failed to calculate overall signal")
            return 'neutral', 0
    
    async def _analyze_trend(self, data: pd.DataFrame, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trend direction and strength."""
        try:
            trend_analysis = {
                'direction': 'neutral',
                'strength': 0,
                'duration_periods': 0,
                'trend_line_slope': 0
            }
            
            if len(data) < 10:
                return trend_analysis
            
            # Calculate trend using linear regression
            periods = np.arange(len(data))
            prices = data['close'].values
            
            # Linear regression
            coefficients = np.polyfit(periods, prices, 1)
            trend_line_slope = coefficients[0]
            
            # Normalize slope by price level
            avg_price = np.mean(prices)
            normalized_slope = (trend_line_slope / avg_price) * 100 if avg_price > 0 else 0
            
            # Determine trend direction
            if normalized_slope > 0.1:  # 0.1% per period
                trend_analysis['direction'] = 'uptrend'
            elif normalized_slope < -0.1:
                trend_analysis['direction'] = 'downtrend'
            else:
                trend_analysis['direction'] = 'sideways'
            
            # Calculate trend strength
            trend_analysis['strength'] = min(abs(normalized_slope) / 2.0, 1.0)  # Max strength of 1.0
            trend_analysis['trend_line_slope'] = float(trend_line_slope)
            
            # Estimate trend duration (simplified)
            trend_analysis['duration_periods'] = len(data)
            
            return trend_analysis
            
        except Exception as e:
            logger.exception("Failed to analyze trend")
            return {'direction': 'neutral', 'strength': 0, 'duration_periods': 0, 'trend_line_slope': 0}
    
    async def _analyze_volume(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volume patterns and trends."""
        try:
            volume_analysis = {
                'average_volume': 0,
                'volume_trend': 'neutral',
                'volume_spikes': 0,
                'volume_profile': {}
            }
            
            if len(data) < 5:
                return volume_analysis
            
            volumes = data['volume'].values
            
            # Average volume
            volume_analysis['average_volume'] = float(np.mean(volumes))
            
            # Volume trend
            recent_volume = np.mean(volumes[-5:])
            past_volume = np.mean(volumes[:-5]) if len(volumes) > 5 else recent_volume
            
            if recent_volume > past_volume * 1.2:
                volume_analysis['volume_trend'] = 'increasing'
            elif recent_volume < past_volume * 0.8:
                volume_analysis['volume_trend'] = 'decreasing'
            else:
                volume_analysis['volume_trend'] = 'stable'
            
            # Count volume spikes
            avg_volume = np.mean(volumes)
            volume_spikes = np.sum(volumes > avg_volume * 2.0)
            volume_analysis['volume_spikes'] = int(volume_spikes)
            
            # Volume profile (simplified)
            prices = data['close'].values
            price_min, price_max = np.min(prices), np.max(prices)
            
            if price_max > price_min:
                # Create price bins
                num_bins = min(10, len(data) // 2)
                price_bins = np.linspace(price_min, price_max, num_bins + 1)
                
                volume_profile = {}
                for i in range(len(price_bins) - 1):
                    bin_mask = (prices >= price_bins[i]) & (prices < price_bins[i + 1])
                    bin_volume = np.sum(volumes[bin_mask])
                    price_level = (price_bins[i] + price_bins[i + 1]) / 2
                    volume_profile[f"{price_level:.0f}"] = float(bin_volume)
                
                volume_analysis['volume_profile'] = volume_profile
            
            return volume_analysis
            
        except Exception as e:
            logger.exception("Failed to analyze volume")
            return {'average_volume': 0, 'volume_trend': 'neutral', 'volume_spikes': 0, 'volume_profile': {}}
    
    async def _generate_overall_signals(self, timeframes: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall signals across all timeframes."""
        try:
            overall_signals = {
                'consensus_signal': 'neutral',
                'timeframe_agreement': 0,
                'dominant_timeframes': [],
                'conflicting_signals': False
            }
            
            if not timeframes:
                return overall_signals
            
            # Collect signals from all timeframes
            timeframe_signals = {}
            signal_weights = {'5m': 0.1, '15m': 0.15, '1h': 0.25, '4h': 0.3, '1d': 0.2}
            
            buy_weight = 0
            sell_weight = 0
            neutral_weight = 0
            
            for tf, tf_data in timeframes.items():
                if 'signals' in tf_data and 'overall_signal' in tf_data['signals']:
                    signal = tf_data['signals']['overall_signal']
                    strength = tf_data['signals'].get('signal_strength', 0)
                    weight = signal_weights.get(tf, 0.1)
                    
                    timeframe_signals[tf] = {'signal': signal, 'strength': strength}
                    
                    if signal == 'buy':
                        buy_weight += weight * strength
                    elif signal == 'sell':
                        sell_weight += weight * strength
                    else:
                        neutral_weight += weight
            
            # Determine consensus signal
            total_weight = buy_weight + sell_weight + neutral_weight
            if total_weight > 0:
                buy_ratio = buy_weight / total_weight
                sell_ratio = sell_weight / total_weight
                
                if buy_ratio > 0.4:
                    overall_signals['consensus_signal'] = 'buy'
                elif sell_ratio > 0.4:
                    overall_signals['consensus_signal'] = 'sell'
                else:
                    overall_signals['consensus_signal'] = 'neutral'
            
            # Calculate timeframe agreement
            consensus = overall_signals['consensus_signal']
            agreeing_timeframes = [
                tf for tf, data in timeframe_signals.items() 
                if data['signal'] == consensus
            ]
            
            overall_signals['timeframe_agreement'] = len(agreeing_timeframes) / len(timeframe_signals) if timeframe_signals else 0
            overall_signals['dominant_timeframes'] = agreeing_timeframes
            
            # Check for conflicting signals
            signals_set = set(data['signal'] for data in timeframe_signals.values())
            overall_signals['conflicting_signals'] = len(signals_set) > 2
            
            return overall_signals
            
        except Exception as e:
            logger.exception("Failed to generate overall signals")
            return {'consensus_signal': 'neutral', 'timeframe_agreement': 0, 'dominant_timeframes': [], 'conflicting_signals': False}
    
    async def _calculate_strength_score(self, timeframes: Dict[str, Any]) -> float:
        """Calculate overall technical analysis strength score (0-100)."""
        try:
            if not timeframes:
                return 0
            
            total_score = 0
            total_weight = 0
            
            # Weight different timeframes
            timeframe_weights = {'5m': 0.1, '15m': 0.15, '1h': 0.25, '4h': 0.3, '1d': 0.2}
            
            for tf, tf_data in timeframes.items():
                weight = timeframe_weights.get(tf, 0.1)
                
                # Calculate timeframe score based on signal strength and trend strength
                score = 0
                
                if 'signals' in tf_data:
                    signal_strength = tf_data['signals'].get('signal_strength', 0)
                    score += signal_strength * 40  # Max 40 points from signals
                
                if 'trend_analysis' in tf_data:
                    trend_strength = tf_data['trend_analysis'].get('strength', 0)
                    score += trend_strength * 30  # Max 30 points from trend
                
                if 'volume_analysis' in tf_data:
                    # Volume contribution (simplified)
                    volume_trend = tf_data['volume_analysis'].get('volume_trend', 'neutral')
                    if volume_trend in ['increasing', 'strong_volume']:
                        score += 15  # Max 15 points from volume
                
                # Data quality bonus
                data_points = tf_data.get('data_points', 0)
                if data_points >= 50:
                    score += 15  # Max 15 points for good data quality
                elif data_points >= 20:
                    score += 10
                elif data_points >= 10:
                    score += 5
                
                total_score += score * weight
                total_weight += weight
            
            # Normalize to 0-100 scale
            final_score = (total_score / total_weight) if total_weight > 0 else 0
            return min(max(final_score, 0), 100)
            
        except Exception as e:
            logger.exception("Failed to calculate strength score")
            return 0
    
    async def _generate_recommendation(self, analysis_results: Dict[str, Any]) -> str:
        """Generate final trading recommendation."""
        try:
            strength_score = analysis_results.get('strength_score', 0)
            overall_signals = analysis_results.get('overall_signals', {})
            consensus_signal = overall_signals.get('consensus_signal', 'neutral')
            timeframe_agreement = overall_signals.get('timeframe_agreement', 0)
            
            # Strong signal with high agreement
            if strength_score >= 70 and timeframe_agreement >= 0.6:
                if consensus_signal == 'buy':
                    return 'strong_buy'
                elif consensus_signal == 'sell':
                    return 'strong_sell'
            
            # Moderate signal with decent agreement
            elif strength_score >= 50 and timeframe_agreement >= 0.4:
                if consensus_signal == 'buy':
                    return 'buy'
                elif consensus_signal == 'sell':
                    return 'sell'
            
            # Weak signal or conflicting signals
            elif strength_score >= 30:
                if consensus_signal == 'buy':
                    return 'weak_buy'
                elif consensus_signal == 'sell':
                    return 'weak_sell'
            
            # Default to neutral
            return 'neutral'
            
        except Exception as e:
            logger.exception("Failed to generate recommendation")
            return 'neutral'
    
    async def analyze_multiple_items(
        self, 
        item_ids: List[int], 
        timeframes: List[str] = None,
        lookback_days: int = 30
    ) -> Dict[int, Dict[str, Any]]:
        """Analyze multiple items for technical signals."""
        try:
            results = {}
            
            # Process items in batches to manage memory
            batch_size = 10
            for i in range(0, len(item_ids), batch_size):
                batch = item_ids[i:i + batch_size]
                
                # Analyze batch concurrently
                tasks = [
                    self.analyze_item_technical(item_id, timeframes, lookback_days)
                    for item_id in batch
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for item_id, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to analyze item {item_id}: {result}")
                        results[item_id] = {'error': str(result)}
                    else:
                        results[item_id] = result
            
            return results
            
        except Exception as e:
            logger.exception("Failed to analyze multiple items")
            return {}


# Global instance
technical_analysis_engine = TechnicalAnalysisEngine()