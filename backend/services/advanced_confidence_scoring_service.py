"""
Advanced Confidence Scoring Service for OSRS Trading Data

This service provides sophisticated confidence scoring algorithms that combine:
- Price data freshness and reliability
- Volume analysis and trading activity
- Historical price stability patterns
- Market liquidity indicators
- Item-specific trading characteristics

Used to weight AI recommendations and filter high-quality trading opportunities.
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from dataclasses import dataclass
from enum import Enum
import asyncio

from django.utils import timezone
from django.core.cache import cache
from django.db.models import Avg, StdDev, Count, Q

from .unified_wiki_price_client import PriceData
from .runescape_wiki_client import TimeSeriesData, ItemMetadata
from apps.items.models import Item
from apps.prices.models import PriceSnapshot

logger = logging.getLogger(__name__)


class TradingActivity(Enum):
    """Trading activity levels."""
    DORMANT = "dormant"          # No recent trading activity
    INACTIVE = "inactive"        # Very low volume
    LOW = "low"                  # Some activity but inconsistent  
    MODERATE = "moderate"        # Regular trading activity
    ACTIVE = "active"            # High consistent activity
    VERY_ACTIVE = "very_active"  # Extremely high volume
    VOLATILE = "volatile"        # High volume but unstable


class LiquidityTier(Enum):
    """Liquidity tier classifications."""
    ILLIQUID = "illiquid"        # Very difficult to trade
    LOW_LIQUIDITY = "low"        # Takes time to buy/sell
    MODERATE_LIQUIDITY = "moderate"  # Reasonable trading speed
    HIGH_LIQUIDITY = "high"      # Quick trading
    ULTRA_LIQUID = "ultra"       # Instant trading


@dataclass
class ConfidenceComponents:
    """Breakdown of confidence score components."""
    base_score: float = 0.5
    data_freshness: float = 0.0
    price_reliability: float = 0.0
    volume_consistency: float = 0.0
    liquidity_factor: float = 0.0
    historical_stability: float = 0.0
    market_activity: float = 0.0
    item_specific_bonus: float = 0.0
    
    @property
    def total_score(self) -> float:
        """Calculate total confidence score."""
        return max(0.0, min(1.0, 
            self.base_score + 
            self.data_freshness + 
            self.price_reliability + 
            self.volume_consistency + 
            self.liquidity_factor + 
            self.historical_stability + 
            self.market_activity + 
            self.item_specific_bonus
        ))
    
    @property
    def quality_grade(self) -> str:
        """Get letter grade for confidence score."""
        score = self.total_score
        if score >= 0.9: return "A+"
        elif score >= 0.8: return "A"
        elif score >= 0.7: return "B+"
        elif score >= 0.6: return "B"
        elif score >= 0.5: return "C+"
        elif score >= 0.4: return "C"
        elif score >= 0.3: return "D"
        else: return "F"


class AdvancedConfidenceScoringService:
    """
    Advanced confidence scoring system for trading data quality assessment.
    """
    
    def __init__(self):
        # Scoring weights (must sum to 1.0)
        self.weights = {
            'data_freshness': 0.25,      # How recent is the data
            'price_reliability': 0.20,    # Price data quality
            'volume_consistency': 0.20,   # Volume pattern reliability
            'liquidity_factor': 0.15,     # How easy to trade
            'historical_stability': 0.10, # Price stability over time
            'market_activity': 0.05,      # Overall market activity
            'item_specific': 0.05         # Item-specific factors
        }
        
        # Cache settings
        self.cache_timeout = 1800  # 30 minutes
        self.historical_days = 30  # Days of history to analyze
        
        # Trading thresholds
        self.volume_thresholds = {
            TradingActivity.DORMANT: 0,
            TradingActivity.INACTIVE: 1,
            TradingActivity.LOW: 10,
            TradingActivity.MODERATE: 50,
            TradingActivity.ACTIVE: 200,
            TradingActivity.VERY_ACTIVE: 1000,
            TradingActivity.VOLATILE: 2000  # High volume but potentially unstable
        }
        
        self.liquidity_thresholds = {
            LiquidityTier.ILLIQUID: 0.1,
            LiquidityTier.LOW_LIQUIDITY: 0.3,
            LiquidityTier.MODERATE_LIQUIDITY: 0.6,
            LiquidityTier.HIGH_LIQUIDITY: 0.8,
            LiquidityTier.ULTRA_LIQUID: 0.95
        }
    
    def calculate_comprehensive_confidence(
        self, 
        price_data: PriceData, 
        item_metadata: Optional[ItemMetadata] = None,
        historical_data: Optional[List[TimeSeriesData]] = None
    ) -> ConfidenceComponents:
        """
        Calculate comprehensive confidence score with detailed breakdown.
        
        Args:
            price_data: Current price data
            item_metadata: Item metadata from Wiki API
            historical_data: Historical time series data
            
        Returns:
            ConfidenceComponents with detailed scoring breakdown
        """
        components = ConfidenceComponents()
        
        # 1. Data Freshness Analysis (25%)
        components.data_freshness = self._calculate_freshness_score(price_data) * self.weights['data_freshness']
        
        # 2. Price Reliability Analysis (20%)
        components.price_reliability = self._calculate_price_reliability_score(price_data) * self.weights['price_reliability']
        
        # 3. Volume Consistency Analysis (20%)
        components.volume_consistency = self._calculate_volume_consistency_score(
            price_data, historical_data
        ) * self.weights['volume_consistency']
        
        # 4. Liquidity Factor Analysis (15%)
        components.liquidity_factor = self._calculate_liquidity_score(price_data) * self.weights['liquidity_factor']
        
        # 5. Historical Stability Analysis (10%)
        components.historical_stability = self._calculate_historical_stability_score(
            historical_data
        ) * self.weights['historical_stability']
        
        # 6. Market Activity Analysis (5%)
        components.market_activity = self._calculate_market_activity_score(price_data) * self.weights['market_activity']
        
        # 7. Item-Specific Bonuses (5%)
        components.item_specific_bonus = self._calculate_item_specific_bonus(
            item_metadata, price_data
        ) * self.weights['item_specific']
        
        logger.debug(f"Confidence breakdown for item {price_data.item_id}: "
                    f"Fresh={components.data_freshness:.3f}, "
                    f"Price={components.price_reliability:.3f}, "
                    f"Volume={components.volume_consistency:.3f}, "
                    f"Liquidity={components.liquidity_factor:.3f}, "
                    f"Stability={components.historical_stability:.3f}, "
                    f"Activity={components.market_activity:.3f}, "
                    f"Bonus={components.item_specific_bonus:.3f}, "
                    f"Total={components.total_score:.3f}")
        
        return components
    
    def _calculate_freshness_score(self, price_data: PriceData) -> float:
        """
        Calculate freshness score based on data age.
        
        Fresh data (< 1 hour) = 1.0
        Recent data (1-6 hours) = 0.8
        Acceptable data (6-24 hours) = 0.5
        Stale data (24-48 hours) = 0.2
        Very stale data (> 48 hours) = 0.0
        """
        age_hours = price_data.age_hours
        
        if age_hours < 1:
            return 1.0
        elif age_hours < 6:
            return 0.8 - (age_hours - 1) * 0.04  # Linear decay from 0.8 to 0.6
        elif age_hours < 24:
            return 0.6 - (age_hours - 6) * 0.0056  # Linear decay from 0.6 to 0.5
        elif age_hours < 48:
            return 0.5 - (age_hours - 24) * 0.0125  # Linear decay from 0.5 to 0.2
        else:
            return max(0.0, 0.2 - (age_hours - 48) * 0.01)  # Gradual decay to 0
    
    def _calculate_price_reliability_score(self, price_data: PriceData) -> float:
        """
        Calculate price reliability score based on data quality indicators.
        """
        score = 0.0
        
        # Both high and low prices available
        if price_data.high_price > 0 and price_data.low_price > 0:
            score += 0.4
            
            # Reasonable spread (high >= low)
            if price_data.high_price >= price_data.low_price:
                score += 0.3
                
                # Realistic spread (not too wide or too narrow)
                if price_data.low_price > 0:
                    spread_ratio = price_data.high_price / price_data.low_price
                    if 1.0 <= spread_ratio <= 2.0:  # Reasonable spread
                        score += 0.2
                    elif spread_ratio > 2.0:  # Wide spread, might be volatile
                        score += 0.1
            else:
                score -= 0.2  # Penalty for invalid price relationship
        elif price_data.high_price > 0 or price_data.low_price > 0:
            score += 0.2  # Partial credit for one price
        
        # Non-zero prices
        if price_data.high_price > 0 or price_data.low_price > 0:
            score += 0.1
        
        return min(1.0, score)
    
    def _calculate_volume_consistency_score(
        self, 
        price_data: PriceData, 
        historical_data: Optional[List[TimeSeriesData]]
    ) -> float:
        """
        Calculate volume consistency score based on trading activity patterns.
        """
        if not price_data.volume_analysis:
            return 0.3  # Default score when no volume data available
        
        analysis = price_data.volume_analysis
        score = 0.0
        
        # Trading activity level
        activity_level = analysis.get('trading_activity', 'inactive')
        activity_scores = {
            'very_active': 1.0,
            'active': 0.8,
            'moderate': 0.6,
            'low': 0.4,
            'inactive': 0.2,
            'error': 0.1
        }
        score += activity_scores.get(activity_level, 0.2) * 0.4
        
        # Volume trend stability
        volume_trend = analysis.get('volume_trend', 'insufficient_data')
        trend_scores = {
            'stable': 0.3,
            'increasing': 0.25,
            'decreasing': 0.15,
            'insufficient_data': 0.1,
            'error': 0.05
        }
        score += trend_scores.get(volume_trend, 0.1)
        
        # Liquidity score from analysis
        liquidity_score = analysis.get('liquidity_score', 0.0)
        score += liquidity_score * 0.3
        
        return min(1.0, score)
    
    def _calculate_liquidity_score(self, price_data: PriceData) -> float:
        """
        Calculate liquidity score based on volume and trading patterns.
        """
        if not price_data.volume_analysis:
            # Fallback to basic volume if available
            total_volume = price_data.total_volume
            if total_volume > 500:
                return 0.8
            elif total_volume > 100:
                return 0.6
            elif total_volume > 10:
                return 0.4
            elif total_volume > 0:
                return 0.2
            else:
                return 0.1
        
        analysis = price_data.volume_analysis
        
        # Get liquidity indicators
        liquidity_score = analysis.get('liquidity_score', 0.0)
        avg_volume_per_hour = analysis.get('avg_volume_per_hour', 0)
        trading_activity = analysis.get('trading_activity', 'inactive')
        
        # Combine liquidity indicators
        score = 0.0
        
        # Base liquidity score from analysis
        score += liquidity_score * 0.5
        
        # Volume per hour bonus
        if avg_volume_per_hour > 50:
            score += 0.3
        elif avg_volume_per_hour > 20:
            score += 0.2
        elif avg_volume_per_hour > 5:
            score += 0.1
        
        # Activity level bonus
        activity_bonus = {
            'very_active': 0.2,
            'active': 0.15,
            'moderate': 0.1,
            'low': 0.05,
            'inactive': 0.0
        }
        score += activity_bonus.get(trading_activity, 0.0)
        
        return min(1.0, score)
    
    def _calculate_historical_stability_score(
        self, 
        historical_data: Optional[List[TimeSeriesData]]
    ) -> float:
        """
        Calculate historical stability score based on price volatility patterns.
        """
        if not historical_data or len(historical_data) < 5:
            return 0.5  # Neutral score when insufficient data
        
        # Calculate price volatility from historical data
        prices = []
        for data_point in historical_data:
            if data_point.volume_weighted_price:
                prices.append(data_point.volume_weighted_price)
            elif data_point.avg_high_price and data_point.avg_low_price:
                avg_price = (data_point.avg_high_price + data_point.avg_low_price) / 2
                prices.append(avg_price)
        
        if len(prices) < 3:
            return 0.5
        
        # Calculate coefficient of variation (volatility measure)
        mean_price = np.mean(prices)
        std_price = np.std(prices)
        
        if mean_price == 0:
            return 0.2
        
        cv = std_price / mean_price  # Coefficient of variation
        
        # Convert volatility to stability score (inverse relationship)
        if cv < 0.05:  # Very stable (< 5% volatility)
            return 1.0
        elif cv < 0.10:  # Stable (5-10% volatility)
            return 0.8
        elif cv < 0.20:  # Moderate volatility (10-20%)
            return 0.6
        elif cv < 0.35:  # High volatility (20-35%)
            return 0.4
        elif cv < 0.50:  # Very high volatility (35-50%)
            return 0.2
        else:  # Extremely volatile (>50%)
            return 0.1
    
    def _calculate_market_activity_score(self, price_data: PriceData) -> float:
        """
        Calculate overall market activity score.
        """
        if not price_data.volume_analysis:
            return 0.5
        
        analysis = price_data.volume_analysis
        
        # Total volume in recent period
        total_volume = analysis.get('total_volume', 0)
        
        if total_volume > 5000:
            return 1.0  # Very high market activity
        elif total_volume > 1000:
            return 0.8  # High activity
        elif total_volume > 200:
            return 0.6  # Moderate activity
        elif total_volume > 50:
            return 0.4  # Low activity
        elif total_volume > 0:
            return 0.2  # Minimal activity
        else:
            return 0.0  # No activity
    
    def _calculate_item_specific_bonus(
        self, 
        item_metadata: Optional[ItemMetadata], 
        price_data: PriceData
    ) -> float:
        """
        Calculate item-specific confidence bonuses.
        """
        if not item_metadata:
            return 0.0
        
        bonus = 0.0
        
        # High-value items tend to have more reliable data
        if item_metadata.highalch > 100000:  # 100K+ alch value
            bonus += 0.1
        elif item_metadata.highalch > 10000:  # 10K+ alch value
            bonus += 0.05
        
        # Popular items (members items often more actively traded)
        if item_metadata.members:
            bonus += 0.05
        
        # Items with reasonable GE limits
        if item_metadata.limit > 0:
            if item_metadata.limit >= 100:
                bonus += 0.05  # High limit = more liquid
            elif item_metadata.limit >= 25:
                bonus += 0.03  # Medium limit
            # Low limits might indicate special/rare items - no bonus but no penalty
        else:
            bonus += 0.02  # Unlimited items are often very liquid
        
        # Well-described items (complete metadata)
        if item_metadata.examine and len(item_metadata.examine) > 10:
            bonus += 0.02
        
        return min(0.2, bonus)  # Cap item-specific bonus at 20%
    
    async def batch_calculate_confidence_scores(
        self, 
        price_data_list: List[PriceData],
        include_historical: bool = True
    ) -> Dict[int, ConfidenceComponents]:
        """
        Calculate confidence scores for multiple items efficiently.
        
        Args:
            price_data_list: List of price data objects
            include_historical: Whether to include historical analysis
            
        Returns:
            Dictionary mapping item_id -> ConfidenceComponents
        """
        logger.info(f"Calculating confidence scores for {len(price_data_list)} items")
        
        confidence_scores = {}
        
        # Group items for batch processing
        batch_size = 50
        for i in range(0, len(price_data_list), batch_size):
            batch = price_data_list[i:i+batch_size]
            
            # Process batch
            for price_data in batch:
                try:
                    # Get metadata if attached to price data
                    metadata = price_data.item_metadata
                    
                    # Get historical data if requested (placeholder for now)
                    historical_data = None
                    if include_historical:
                        # TODO: Implement historical data fetching
                        pass
                    
                    # Calculate confidence
                    confidence = self.calculate_comprehensive_confidence(
                        price_data, metadata, historical_data
                    )
                    
                    confidence_scores[price_data.item_id] = confidence
                    
                except Exception as e:
                    logger.warning(f"Failed to calculate confidence for item {price_data.item_id}: {e}")
                    # Provide fallback confidence
                    confidence_scores[price_data.item_id] = ConfidenceComponents(base_score=0.3)
        
        logger.info(f"Calculated confidence scores for {len(confidence_scores)} items")
        return confidence_scores
    
    def get_trading_recommendation(self, confidence: ConfidenceComponents) -> Dict[str, Any]:
        """
        Generate trading recommendation based on confidence analysis.
        
        Args:
            confidence: Confidence components analysis
            
        Returns:
            Dictionary with trading recommendations
        """
        score = confidence.total_score
        grade = confidence.quality_grade
        
        if score >= 0.8:
            recommendation = {
                'action': 'highly_recommended',
                'confidence_level': 'very_high',
                'suggested_strategy': 'active_trading',
                'risk_assessment': 'low',
                'notes': 'Excellent data quality, suitable for all trading strategies'
            }
        elif score >= 0.6:
            recommendation = {
                'action': 'recommended',
                'confidence_level': 'high',
                'suggested_strategy': 'moderate_trading',
                'risk_assessment': 'low_to_moderate',
                'notes': 'Good data quality, suitable for most trading strategies'
            }
        elif score >= 0.4:
            recommendation = {
                'action': 'proceed_with_caution',
                'confidence_level': 'moderate',
                'suggested_strategy': 'conservative_trading',
                'risk_assessment': 'moderate',
                'notes': 'Acceptable data quality, verify with additional sources'
            }
        elif score >= 0.3:
            recommendation = {
                'action': 'not_recommended',
                'confidence_level': 'low',
                'suggested_strategy': 'avoid_or_minimal',
                'risk_assessment': 'high',
                'notes': 'Poor data quality, high uncertainty'
            }
        else:
            recommendation = {
                'action': 'avoid',
                'confidence_level': 'very_low',
                'suggested_strategy': 'avoid',
                'risk_assessment': 'very_high',
                'notes': 'Insufficient or unreliable data'
            }
        
        recommendation['confidence_score'] = score
        recommendation['grade'] = grade
        recommendation['breakdown'] = {
            'data_freshness': confidence.data_freshness,
            'price_reliability': confidence.price_reliability,
            'volume_consistency': confidence.volume_consistency,
            'liquidity_factor': confidence.liquidity_factor,
            'historical_stability': confidence.historical_stability,
            'market_activity': confidence.market_activity,
            'item_specific_bonus': confidence.item_specific_bonus
        }
        
        return recommendation