"""
Predictive Price Modeling Engine using Ollama and Statistical Methods

Lightweight ML approach optimized for MacBook Pro M1 8GB RAM:
- Statistical trend analysis and pattern recognition
- Ollama integration for market context analysis
- Time series decomposition and forecasting
- Market regime detection using moving averages
- Volume-weighted price predictions
- Sentiment-influenced price modeling
- Resource-efficient prediction algorithms
"""

import logging
import asyncio
import aiohttp
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import models
from asgiref.sync import sync_to_async
import json
from dataclasses import dataclass
from scipy import stats
from scipy.signal import find_peaks
import math

from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.realtime_engine.models import MarketMomentum, VolumeAnalysis, SentimentAnalysis, ItemSentiment
from services.intelligent_cache import intelligent_cache

logger = logging.getLogger(__name__)


@dataclass
class PricePrediction:
    """Price prediction result."""
    item_id: int
    item_name: str
    current_price: float
    predicted_price_1h: float
    predicted_price_4h: float
    predicted_price_24h: float
    confidence_1h: float
    confidence_4h: float
    confidence_24h: float
    trend_direction: str
    prediction_factors: Dict[str, Any]
    generated_at: datetime


class PricePredictionEngine:
    """
    Lightweight price prediction engine using statistical methods and Ollama.
    """
    
    def __init__(self):
        self.cache_prefix = "price_prediction:"
        self.ollama_base_url = "http://localhost:11434"
        self.model_name = "llama3.2:3b"  # Lightweight model for M1 8GB
        
        # Prediction parameters
        self.min_price_history = 10  # Minimum price points needed
        self.trend_window = 20  # Points for trend analysis
        self.volatility_window = 50  # Points for volatility calculation
        
        # Market regime thresholds
        self.high_volatility_threshold = 0.05  # 5% volatility
        self.trend_strength_threshold = 0.3  # 30% trend strength
        
    async def predict_item_prices(self, item_ids: List[int], 
                                prediction_horizon: str = "all") -> Dict[str, Any]:
        """
        Generate price predictions for specified items.
        
        Args:
            item_ids: List of item IDs to predict
            prediction_horizon: "1h", "4h", "24h", or "all"
            
        Returns:
            Dictionary with predictions and analysis
        """
        logger.debug(f"🔮 Generating price predictions for {len(item_ids)} items")
        
        try:
            predictions = []
            failed_predictions = []
            
            for item_id in item_ids:
                try:
                    prediction = await self._predict_single_item(item_id, prediction_horizon)
                    if prediction:
                        predictions.append(prediction)
                    else:
                        failed_predictions.append(item_id)
                        
                except Exception as e:
                    logger.error(f"Failed to predict item {item_id}: {e}")
                    failed_predictions.append(item_id)
            
            # Generate market summary using Ollama
            market_context = await self._get_market_context_analysis(predictions)
            
            result = {
                'timestamp': timezone.now().isoformat(),
                'predictions': [self._prediction_to_dict(p) for p in predictions],
                'successful_predictions': len(predictions),
                'failed_predictions': len(failed_predictions),
                'market_context': market_context,
                'prediction_summary': self._generate_prediction_summary(predictions)
            }
            
            # Cache results
            cache_key = f"{self.cache_prefix}batch_predictions"
            intelligent_cache.set(
                cache_key,
                result,
                tier="warm",
                tags=["price_predictions", "ml_analysis"]
            )
            
            logger.info(f"✅ Generated {len(predictions)} price predictions")
            return result
            
        except Exception as e:
            logger.error(f"❌ Price prediction failed: {e}")
            return {'error': str(e)}
    
    async def _predict_single_item(self, item_id: int, 
                                 prediction_horizon: str) -> Optional[PricePrediction]:
        """Generate prediction for a single item."""
        try:
            # Get item data
            item = await self._get_item(item_id)
            if not item:
                return None
            
            # Get price history
            price_history = await self._get_price_history(item_id, hours=72)  # 3 days
            if len(price_history) < self.min_price_history:
                logger.debug(f"Insufficient price history for item {item_id}")
                return None
            
            # Get current market data
            momentum = await self._get_momentum_data(item_id)
            volume_analysis = await self._get_volume_analysis(item_id)
            sentiment = await self._get_latest_sentiment(item_id)
            
            # Prepare data for analysis
            prices = np.array([p['price'] for p in price_history])
            timestamps = [p['timestamp'] for p in price_history]
            
            current_price = prices[-1]
            
            # Statistical analysis
            trend_analysis = self._analyze_trend(prices)
            volatility_analysis = self._analyze_volatility(prices)
            support_resistance = self._find_support_resistance(prices)
            cycle_analysis = self._detect_price_cycles(prices, timestamps)
            
            # Volume influence
            volume_factor = self._calculate_volume_influence(volume_analysis)
            
            # Sentiment influence
            sentiment_factor = self._calculate_sentiment_influence(sentiment)
            
            # Momentum influence
            momentum_factor = self._calculate_momentum_influence(momentum)
            
            # Generate predictions using ensemble methods
            predictions = {}
            confidences = {}
            
            if prediction_horizon in ["1h", "all"]:
                pred_1h, conf_1h = self._predict_price_statistical(
                    prices, trend_analysis, volatility_analysis, 1, 
                    volume_factor, sentiment_factor, momentum_factor
                )
                predictions['1h'] = pred_1h
                confidences['1h'] = conf_1h
            
            if prediction_horizon in ["4h", "all"]:
                pred_4h, conf_4h = self._predict_price_statistical(
                    prices, trend_analysis, volatility_analysis, 4,
                    volume_factor, sentiment_factor, momentum_factor
                )
                predictions['4h'] = pred_4h
                confidences['4h'] = conf_4h
            
            if prediction_horizon in ["24h", "all"]:
                pred_24h, conf_24h = self._predict_price_statistical(
                    prices, trend_analysis, volatility_analysis, 24,
                    volume_factor, sentiment_factor, momentum_factor
                )
                predictions['24h'] = pred_24h
                confidences['24h'] = conf_24h
            
            # Determine trend direction
            trend_direction = self._determine_trend_direction(
                trend_analysis, momentum_factor, sentiment_factor
            )
            
            # Compile prediction factors
            prediction_factors = {
                'trend_strength': trend_analysis['strength'],
                'volatility': volatility_analysis['current_volatility'],
                'volume_influence': volume_factor,
                'sentiment_influence': sentiment_factor,
                'momentum_influence': momentum_factor,
                'support_level': support_resistance['support'],
                'resistance_level': support_resistance['resistance'],
                'market_regime': volatility_analysis['regime']
            }
            
            return PricePrediction(
                item_id=item_id,
                item_name=item.name,
                current_price=current_price,
                predicted_price_1h=predictions.get('1h', current_price),
                predicted_price_4h=predictions.get('4h', current_price),
                predicted_price_24h=predictions.get('24h', current_price),
                confidence_1h=confidences.get('1h', 0.5),
                confidence_4h=confidences.get('4h', 0.5),
                confidence_24h=confidences.get('24h', 0.5),
                trend_direction=trend_direction,
                prediction_factors=prediction_factors,
                generated_at=timezone.now()
            )
            
        except Exception as e:
            logger.error(f"Single item prediction failed for {item_id}: {e}")
            return None
    
    def _analyze_trend(self, prices: np.ndarray) -> Dict[str, Any]:
        """Analyze price trend using statistical methods."""
        # Linear regression for trend
        x = np.arange(len(prices))
        slope, intercept, r_value, _, _ = stats.linregress(x, prices)
        
        # Moving averages
        ma_short = np.mean(prices[-5:]) if len(prices) >= 5 else prices[-1]
        ma_long = np.mean(prices[-20:]) if len(prices) >= 20 else prices[-1]
        
        # Trend strength
        trend_strength = abs(r_value)
        
        return {
            'slope': slope,
            'strength': trend_strength,
            'r_squared': r_value ** 2,
            'ma_short': ma_short,
            'ma_long': ma_long,
            'ma_crossover': ma_short > ma_long
        }
    
    def _analyze_volatility(self, prices: np.ndarray) -> Dict[str, Any]:
        """Analyze price volatility."""
        # Calculate returns
        returns = np.diff(prices) / prices[:-1]
        
        # Current volatility (standard deviation of returns)
        current_vol = np.std(returns) if len(returns) > 1 else 0
        
        # Historical volatility percentile
        vol_window = min(len(returns), self.volatility_window)
        if vol_window > 10:
            rolling_vols = [
                np.std(returns[i:i+5]) for i in range(vol_window-5)
            ]
            vol_percentile = stats.percentileofscore(rolling_vols, current_vol) / 100
        else:
            vol_percentile = 0.5
        
        # Market regime
        if current_vol > self.high_volatility_threshold:
            regime = 'high_volatility'
        elif current_vol < self.high_volatility_threshold / 2:
            regime = 'low_volatility'
        else:
            regime = 'normal'
        
        return {
            'current_volatility': current_vol,
            'volatility_percentile': vol_percentile,
            'regime': regime,
            'mean_reversion_strength': 1 - vol_percentile  # Higher vol = lower mean reversion
        }
    
    def _find_support_resistance(self, prices: np.ndarray) -> Dict[str, float]:
        """Find support and resistance levels."""
        # Find local minima (support) and maxima (resistance)
        if len(prices) < 10:
            return {'support': prices.min(), 'resistance': prices.max()}
        
        # Use peak detection
        peaks, _ = find_peaks(prices, distance=5)
        troughs, _ = find_peaks(-prices, distance=5)
        
        if len(peaks) > 0:
            resistance = np.mean(prices[peaks[-3:]])  # Last 3 peaks
        else:
            resistance = prices.max()
        
        if len(troughs) > 0:
            support = np.mean(prices[troughs[-3:]])  # Last 3 troughs
        else:
            support = prices.min()
        
        return {
            'support': support,
            'resistance': resistance,
            'current_to_support': (prices[-1] - support) / support,
            'current_to_resistance': (resistance - prices[-1]) / resistance
        }
    
    def _detect_price_cycles(self, prices: np.ndarray, timestamps: List) -> Dict[str, Any]:
        """Detect cyclical patterns in prices."""
        if len(prices) < 20:
            return {'cycle_detected': False}
        
        # Simple cycle detection using autocorrelation
        from scipy import signal
        
        # Detrend the data
        detrended = signal.detrend(prices)
        
        # Find dominant frequency
        fft = np.fft.fft(detrended)
        freqs = np.fft.fftfreq(len(detrended))
        
        # Find peak frequency (excluding DC component)
        magnitude = np.abs(fft[1:len(fft)//2])
        if len(magnitude) > 0:
            peak_idx = np.argmax(magnitude)
            peak_freq = freqs[peak_idx + 1]
            cycle_length = 1 / abs(peak_freq) if peak_freq != 0 else len(prices)
        else:
            cycle_length = len(prices)
        
        return {
            'cycle_detected': cycle_length < len(prices),
            'cycle_length': cycle_length,
            'cycle_strength': magnitude[peak_idx] / np.sum(magnitude) if len(magnitude) > 0 else 0
        }
    
    def _calculate_volume_influence(self, volume_analysis: Optional[VolumeAnalysis]) -> float:
        """Calculate volume influence on price prediction."""
        if not volume_analysis:
            return 0.0
        
        # Volume ratio influence
        volume_factor = 0.0
        
        if volume_analysis.volume_ratio_daily > 2.0:  # High volume
            volume_factor = 0.3
        elif volume_analysis.volume_ratio_daily > 1.5:  # Above average volume
            volume_factor = 0.1
        elif volume_analysis.volume_ratio_daily < 0.5:  # Low volume
            volume_factor = -0.1
        
        # Liquidity influence
        liquidity_levels = {
            'extreme': 0.2, 'very_high': 0.15, 'high': 0.1,
            'medium': 0.0, 'low': -0.05, 'very_low': -0.1, 'minimal': -0.15
        }
        
        liquidity_factor = liquidity_levels.get(volume_analysis.liquidity_level, 0.0)
        
        return (volume_factor + liquidity_factor) / 2
    
    def _calculate_sentiment_influence(self, sentiment: Optional[ItemSentiment]) -> float:
        """Calculate sentiment influence on price prediction."""
        if not sentiment or sentiment.mention_count == 0:
            return 0.0
        
        # Weight sentiment by mention count and confidence
        mention_weight = min(1.0, sentiment.mention_count / 5)  # Cap at 5 mentions
        confidence_weight = sentiment.confidence
        
        sentiment_influence = sentiment.sentiment_score * mention_weight * confidence_weight
        
        # Scale to reasonable range
        return max(-0.2, min(0.2, sentiment_influence))
    
    def _calculate_momentum_influence(self, momentum: Optional[MarketMomentum]) -> float:
        """Calculate momentum influence on price prediction."""
        if not momentum:
            return 0.0
        
        # Normalize momentum score to influence range
        momentum_influence = (momentum.momentum_score - 50) / 100  # Scale from -0.5 to 0.5
        
        # Price velocity influence
        velocity_influence = max(-0.1, min(0.1, momentum.price_velocity / 1000))
        
        return (momentum_influence + velocity_influence) / 2
    
    def _predict_price_statistical(self, prices: np.ndarray, trend: Dict, 
                                 volatility: Dict, hours: int,
                                 volume_factor: float, sentiment_factor: float, 
                                 momentum_factor: float) -> Tuple[float, float]:
        """Generate statistical price prediction."""
        current_price = prices[-1]
        
        # Base prediction using trend
        trend_component = trend['slope'] * hours
        
        # Mean reversion component
        ma_long = trend['ma_long']
        mean_reversion = (ma_long - current_price) * volatility['mean_reversion_strength'] * 0.1
        
        # External factor influences
        external_influence = (volume_factor + sentiment_factor + momentum_factor) * current_price * 0.1
        
        # Volatility-based uncertainty
        vol_adjustment = volatility['current_volatility'] * current_price * np.sqrt(hours) / 24
        
        # Combine components
        predicted_price = current_price + trend_component + mean_reversion + external_influence
        
        # Calculate confidence
        base_confidence = 0.7
        trend_confidence = min(0.3, trend['strength'])
        vol_confidence = max(-0.2, -volatility['volatility_percentile'] * 0.2)
        data_confidence = min(0.1, len(prices) / 100)
        
        confidence = max(0.1, min(0.95, 
            base_confidence + trend_confidence + vol_confidence + data_confidence
        ))
        
        # Ensure reasonable bounds
        max_change = current_price * 0.5  # Max 50% change
        predicted_price = max(current_price - max_change, 
                            min(current_price + max_change, predicted_price))
        
        return predicted_price, confidence
    
    def _determine_trend_direction(self, trend: Dict, momentum_factor: float, 
                                 sentiment_factor: float) -> str:
        """Determine overall trend direction."""
        # Combine multiple signals
        trend_signal = 1 if trend['slope'] > 0 else -1 if trend['slope'] < 0 else 0
        ma_signal = 1 if trend['ma_crossover'] else -1
        momentum_signal = 1 if momentum_factor > 0.05 else -1 if momentum_factor < -0.05 else 0
        sentiment_signal = 1 if sentiment_factor > 0.05 else -1 if sentiment_factor < -0.05 else 0
        
        combined_signal = trend_signal + ma_signal + momentum_signal + sentiment_signal
        
        if combined_signal >= 2:
            return 'bullish'
        elif combined_signal <= -2:
            return 'bearish'
        else:
            return 'neutral'
    
    async def _get_market_context_analysis(self, predictions: List[PricePrediction]) -> Dict[str, Any]:
        """Get market context analysis using Ollama."""
        if not predictions:
            return {'analysis': 'No predictions available for analysis'}
        
        try:
            # Prepare context data for Ollama
            market_summary = {
                'total_items': len(predictions),
                'bullish_items': len([p for p in predictions if p.trend_direction == 'bullish']),
                'bearish_items': len([p for p in predictions if p.trend_direction == 'bearish']),
                'neutral_items': len([p for p in predictions if p.trend_direction == 'neutral']),
                'avg_confidence_1h': np.mean([p.confidence_1h for p in predictions]),
                'avg_confidence_24h': np.mean([p.confidence_24h for p in predictions]),
                'high_volatility_items': len([p for p in predictions 
                                            if p.prediction_factors.get('market_regime') == 'high_volatility'])
            }
            
            # Create prompt for Ollama
            prompt = f"""
Analyze this OSRS market prediction summary and provide brief insights:

Market Data:
- {market_summary['total_items']} items analyzed
- {market_summary['bullish_items']} bullish, {market_summary['bearish_items']} bearish, {market_summary['neutral_items']} neutral
- Average 1h confidence: {market_summary['avg_confidence_1h']:.2f}
- Average 24h confidence: {market_summary['avg_confidence_24h']:.2f}
- High volatility items: {market_summary['high_volatility_items']}

Provide a concise 2-3 sentence market outlook focusing on:
1. Overall market sentiment
2. Key risks or opportunities
3. Trading recommendations

Keep response under 100 words and OSRS-focused.
"""

            # Call Ollama
            analysis = await self._call_ollama(prompt)
            
            return {
                'summary': market_summary,
                'ai_analysis': analysis,
                'analysis_timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Market context analysis failed: {e}")
            return {
                'analysis': 'AI analysis temporarily unavailable',
                'error': str(e)
            }
    
    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API for analysis."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Low temperature for consistent analysis
                        "top_p": 0.9,
                        "max_tokens": 150
                    }
                }
                
                async with session.post(
                    f"{self.ollama_base_url}/api/generate",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('response', 'Analysis unavailable')
                    else:
                        return 'Ollama service unavailable'
                        
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return 'AI analysis temporarily unavailable'
    
    def _generate_prediction_summary(self, predictions: List[PricePrediction]) -> Dict[str, Any]:
        """Generate summary statistics for predictions."""
        if not predictions:
            return {}
        
        return {
            'total_predictions': len(predictions),
            'trend_distribution': {
                'bullish': len([p for p in predictions if p.trend_direction == 'bullish']),
                'bearish': len([p for p in predictions if p.trend_direction == 'bearish']),
                'neutral': len([p for p in predictions if p.trend_direction == 'neutral'])
            },
            'confidence_stats': {
                '1h_avg': np.mean([p.confidence_1h for p in predictions]),
                '4h_avg': np.mean([p.confidence_4h for p in predictions]),
                '24h_avg': np.mean([p.confidence_24h for p in predictions])
            },
            'market_regime_distribution': {
                regime: len([p for p in predictions 
                           if p.prediction_factors.get('market_regime') == regime])
                for regime in ['low_volatility', 'normal', 'high_volatility']
            }
        }
    
    def _prediction_to_dict(self, prediction: PricePrediction) -> Dict[str, Any]:
        """Convert prediction object to dictionary."""
        return {
            'item_id': prediction.item_id,
            'item_name': prediction.item_name,
            'current_price': prediction.current_price,
            'predictions': {
                '1h': {
                    'price': prediction.predicted_price_1h,
                    'confidence': prediction.confidence_1h,
                    'change_pct': ((prediction.predicted_price_1h / prediction.current_price) - 1) * 100
                },
                '4h': {
                    'price': prediction.predicted_price_4h,
                    'confidence': prediction.confidence_4h,
                    'change_pct': ((prediction.predicted_price_4h / prediction.current_price) - 1) * 100
                },
                '24h': {
                    'price': prediction.predicted_price_24h,
                    'confidence': prediction.confidence_24h,
                    'change_pct': ((prediction.predicted_price_24h / prediction.current_price) - 1) * 100
                }
            },
            'trend_direction': prediction.trend_direction,
            'prediction_factors': prediction.prediction_factors,
            'generated_at': prediction.generated_at.isoformat()
        }
    
    # Helper methods for data retrieval
    
    @sync_to_async
    def _get_item(self, item_id: int) -> Optional[Item]:
        """Get item by ID."""
        try:
            return Item.objects.get(item_id=item_id)
        except Item.DoesNotExist:
            return None
    
    @sync_to_async
    def _get_price_history(self, item_id: int, hours: int = 72) -> List[Dict]:
        """Get recent price history."""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        snapshots = PriceSnapshot.objects.filter(
            item__item_id=item_id,
            created_at__gte=cutoff_time
        ).order_by('created_at').values('high_price', 'low_price', 'created_at')
        
        return [
            {
                'price': (snapshot['high_price'] + snapshot['low_price']) / 2 
                        if snapshot['high_price'] and snapshot['low_price'] else 0,
                'timestamp': snapshot['created_at']
            }
            for snapshot in snapshots
        ]
    
    @sync_to_async
    def _get_momentum_data(self, item_id: int) -> Optional[MarketMomentum]:
        """Get momentum data for item."""
        try:
            return MarketMomentum.objects.get(item__item_id=item_id)
        except MarketMomentum.DoesNotExist:
            return None
    
    @sync_to_async
    def _get_volume_analysis(self, item_id: int) -> Optional[VolumeAnalysis]:
        """Get volume analysis for item."""
        try:
            return VolumeAnalysis.objects.get(item__item_id=item_id)
        except VolumeAnalysis.DoesNotExist:
            return None
    
    @sync_to_async
    def _get_latest_sentiment(self, item_id: int) -> Optional[ItemSentiment]:
        """Get latest sentiment for item."""
        try:
            return ItemSentiment.objects.filter(
                item__item_id=item_id
            ).order_by('-analysis_timestamp').first()
        except ItemSentiment.DoesNotExist:
            return None


# Global price prediction engine instance
price_prediction_engine = PricePredictionEngine()