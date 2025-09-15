from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.items.models import Item
from apps.trading_strategies.models import MarketConditionSnapshot, MarketCondition
import logging
import statistics

logger = logging.getLogger(__name__)


class MarketConditionMonitor:
    """
    Monitors overall market conditions and detects bot activity.
    
    The user's friend mentioned that markets crash due to bots, so this
    monitor tracks various market indicators to detect:
    - Bot activity patterns
    - Market volatility
    - Crash risk assessment
    - Overall market health
    """
    
    def __init__(self):
        """Initialize the market condition monitor."""
        self.crash_indicators = {
            'volume_spike_threshold': 3.0,    # 3x normal volume indicates bot activity
            'price_drop_threshold': 0.15,     # 15% price drop threshold
            'volatility_threshold': 0.25,     # 25% volatility threshold
            'bot_activity_threshold': 0.7,    # 70% bot activity score threshold
        }
    
    def analyze_market_conditions(self) -> Dict:
        """
        Analyze current market conditions across all items.
        
        Returns:
            Market condition analysis dictionary
        """
        logger.info("Starting market condition analysis...")
        
        # Get recent price data (last 24 hours)
        recent_prices = self._get_recent_price_data()
        
        if not recent_prices:
            logger.warning("No recent price data available for market analysis")
            return self._default_market_condition()
        
        # Calculate market metrics
        volume_metrics = self._calculate_volume_metrics(recent_prices)
        price_metrics = self._calculate_price_metrics(recent_prices)
        volatility_metrics = self._calculate_volatility_metrics(recent_prices)
        bot_activity = self._detect_bot_activity(recent_prices)
        
        # Determine overall market condition
        market_condition = self._determine_market_condition(
            volume_metrics, price_metrics, volatility_metrics, bot_activity
        )
        
        # Assess crash risk
        crash_risk = self._assess_crash_risk(
            volume_metrics, price_metrics, volatility_metrics, bot_activity
        )
        
        return {
            'timestamp': timezone.now(),
            'market_condition': market_condition,
            'total_volume_24h': volume_metrics['total_volume'],
            'average_price_change_pct': price_metrics['avg_price_change'],
            'volatility_score': volatility_metrics['overall_volatility'],
            'bot_activity_score': bot_activity['overall_score'],
            'crash_risk_level': crash_risk,
            'analysis_details': {
                'items_analyzed': len(recent_prices),
                'volume_spikes_detected': bot_activity['volume_spikes'],
                'price_crashes_detected': price_metrics['crashes_detected'],
                'high_volatility_items': volatility_metrics['high_volatility_count'],
            }
        }
    
    def _get_recent_price_data(self) -> List[ProfitCalculation]:
        """
        Get recent price data for market analysis.
        
        Returns:
            List of recent ItemPrice objects
        """
        # Get active profit calculations (recent activity)
        cutoff_time = timezone.now() - timedelta(hours=4)
        
        return list(ProfitCalculation.objects.filter(
            last_updated__gte=cutoff_time,
            current_buy_price__gt=0,
            current_sell_price__gt=0
        ).select_related('item')[:1000])  # Limit to top 1000 active items
    
    def _calculate_volume_metrics(self, price_data: List[ProfitCalculation]) -> Dict:
        """Calculate volume-based metrics."""
        total_volume = 0
        volume_spikes = 0
        
        for price in price_data:
            item_volume = (price.daily_volume or 0) + (price.hourly_volume or 0)
            total_volume += item_volume
            
            # Detect volume spikes (simplified - would need historical data for accuracy)
            if item_volume > 5000:  # High volume threshold
                volume_spikes += 1
        
        return {
            'total_volume': total_volume,
            'average_volume': total_volume / len(price_data) if price_data else 0,
            'volume_spikes': volume_spikes,
        }
    
    def _calculate_price_metrics(self, price_data: List[ProfitCalculation]) -> Dict:
        """Calculate price-based metrics."""
        price_changes = []
        crashes_detected = 0
        
        for price in price_data:
            if price.current_buy_price and price.current_sell_price:
                # Calculate spread as proxy for price volatility
                spread = (price.current_buy_price - price.current_sell_price) / price.current_buy_price
                price_changes.append(spread)
                
                # Detect potential crashes (large spreads)
                if spread > self.crash_indicators['price_drop_threshold']:
                    crashes_detected += 1
        
        avg_price_change = statistics.mean(price_changes) if price_changes else 0
        
        return {
            'avg_price_change': avg_price_change,
            'crashes_detected': crashes_detected,
            'price_changes': price_changes,
        }
    
    def _calculate_volatility_metrics(self, price_data: List[ProfitCalculation]) -> Dict:
        """Calculate market volatility metrics."""
        volatility_scores = []
        high_volatility_count = 0
        
        for price in price_data:
            if price.current_buy_price and price.current_sell_price and price.current_buy_price > 0:
                # Use stored volatility if available, otherwise calculate from spread
                volatility = price.price_volatility if price.price_volatility else abs(price.current_buy_price - price.current_sell_price) / price.current_buy_price
                volatility_scores.append(volatility)
                
                if volatility > self.crash_indicators['volatility_threshold']:
                    high_volatility_count += 1
        
        overall_volatility = statistics.mean(volatility_scores) if volatility_scores else 0
        
        return {
            'overall_volatility': overall_volatility,
            'high_volatility_count': high_volatility_count,
            'volatility_scores': volatility_scores,
        }
    
    def _detect_bot_activity(self, price_data: List[ProfitCalculation]) -> Dict:
        """
        Detect bot activity patterns in market data.
        
        Bot indicators:
        - Unusual volume spikes
        - Perfect price matching across items
        - Abnormal trading frequency
        """
        bot_indicators = []
        volume_spikes = 0
        suspicious_patterns = 0
        
        for price in price_data:
            bot_score = 0
            
            # Volume spike indicator
            item_volume = (price.daily_volume or 0) + (price.hourly_volume or 0)
            if item_volume > 10000:  # Very high volume
                bot_score += 0.3
                volume_spikes += 1
            
            # Perfect price matching (bots often use exact prices)
            if price.current_buy_price and price.current_sell_price:
                spread_pct = abs(price.current_buy_price - price.current_sell_price) / price.current_buy_price
                if spread_pct < 0.01:  # Less than 1% spread - suspicious
                    bot_score += 0.2
                    suspicious_patterns += 1
            
            # Recent update frequency (bots update more frequently)
            if price.last_updated and price.last_updated > timezone.now() - timedelta(minutes=30):
                bot_score += 0.1
            
            bot_indicators.append(min(1.0, bot_score))  # Cap at 1.0
        
        overall_score = statistics.mean(bot_indicators) if bot_indicators else 0
        
        return {
            'overall_score': overall_score,
            'volume_spikes': volume_spikes,
            'suspicious_patterns': suspicious_patterns,
            'bot_indicators': bot_indicators,
        }
    
    def _determine_market_condition(self, volume_metrics: Dict, price_metrics: Dict, 
                                  volatility_metrics: Dict, bot_activity: Dict) -> str:
        """
        Determine overall market condition based on metrics.
        
        Returns:
            Market condition string (stable, volatile, crashing, etc.)
        """
        volatility = volatility_metrics['overall_volatility']
        bot_score = bot_activity['overall_score']
        crashes = price_metrics['crashes_detected']
        total_items = len(price_metrics.get('price_changes', []))
        
        # Market is crashing if many crashes detected
        crash_rate = crashes / total_items if total_items > 0 else 0
        if crash_rate > 0.2:  # More than 20% of items crashing
            return MarketCondition.CRASHING
        
        # High bot activity indicates manipulation
        if bot_score > self.crash_indicators['bot_activity_threshold']:
            return MarketCondition.VOLATILE
        
        # High volatility indicates unstable market
        if volatility > self.crash_indicators['volatility_threshold']:
            return MarketCondition.VOLATILE
        
        # Positive price movements indicate recovery
        avg_change = price_metrics['avg_price_change']
        if avg_change > 0.05:  # 5% average positive change
            return MarketCondition.RECOVERING
        
        # Strong positive momentum
        if avg_change > 0.1:  # 10% average positive change
            return MarketCondition.BULLISH
        
        # Negative trends
        if avg_change < -0.05:
            return MarketCondition.BEARISH
        
        # Default to stable
        return MarketCondition.STABLE
    
    def _assess_crash_risk(self, volume_metrics: Dict, price_metrics: Dict,
                          volatility_metrics: Dict, bot_activity: Dict) -> str:
        """
        Assess crash risk level based on market indicators.
        
        Returns:
            Risk level: low, medium, high, critical
        """
        risk_factors = 0
        
        # High bot activity increases crash risk
        if bot_activity['overall_score'] > 0.7:
            risk_factors += 2
        elif bot_activity['overall_score'] > 0.5:
            risk_factors += 1
        
        # High volatility increases risk
        if volatility_metrics['overall_volatility'] > 0.3:
            risk_factors += 2
        elif volatility_metrics['overall_volatility'] > 0.2:
            risk_factors += 1
        
        # Multiple price crashes indicate system risk
        total_items = len(price_metrics.get('price_changes', []))
        crash_rate = price_metrics['crashes_detected'] / total_items if total_items > 0 else 0
        if crash_rate > 0.15:
            risk_factors += 2
        elif crash_rate > 0.1:
            risk_factors += 1
        
        # Volume spikes can precede crashes
        if bot_activity['volume_spikes'] > 50:
            risk_factors += 1
        
        # Determine risk level
        if risk_factors >= 5:
            return 'critical'
        elif risk_factors >= 3:
            return 'high'
        elif risk_factors >= 1:
            return 'medium'
        else:
            return 'low'
    
    def _default_market_condition(self) -> Dict:
        """Return default market condition when no data is available."""
        return {
            'timestamp': timezone.now(),
            'market_condition': MarketCondition.STABLE,
            'total_volume_24h': 0,
            'average_price_change_pct': 0.0,
            'volatility_score': 0.0,
            'bot_activity_score': 0.0,
            'crash_risk_level': 'low',
            'analysis_details': {
                'items_analyzed': 0,
                'volume_spikes_detected': 0,
                'price_crashes_detected': 0,
                'high_volatility_items': 0,
            }
        }
    
    @transaction.atomic
    def create_market_snapshot(self, analysis: Dict) -> MarketConditionSnapshot:
        """
        Create a market condition snapshot record.
        
        Args:
            analysis: Market analysis dictionary
            
        Returns:
            Created MarketConditionSnapshot object
        """
        try:
            snapshot = MarketConditionSnapshot.objects.create(
                market_condition=analysis['market_condition'],
                total_volume_24h=analysis['total_volume_24h'],
                average_price_change_pct=Decimal(str(analysis['average_price_change_pct'])),
                volatility_score=Decimal(str(analysis['volatility_score'])),
                bot_activity_score=Decimal(str(analysis['bot_activity_score'])),
                crash_risk_level=analysis['crash_risk_level'],
                market_data=analysis['analysis_details']
            )
            
            logger.info(f"Created market snapshot: {analysis['market_condition']} condition, "
                       f"{analysis['crash_risk_level']} crash risk")
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating market snapshot: {e}")
            raise
    
    def monitor_and_record(self) -> MarketConditionSnapshot:
        """
        Full monitoring cycle: analyze conditions and record snapshot.
        
        Returns:
            Created MarketConditionSnapshot object
        """
        logger.info("Starting market condition monitoring cycle...")
        
        analysis = self.analyze_market_conditions()
        snapshot = self.create_market_snapshot(analysis)
        
        logger.info(f"Market monitoring complete. Condition: {analysis['market_condition']}, "
                   f"Bot activity: {analysis['bot_activity_score']:.3f}, "
                   f"Crash risk: {analysis['crash_risk_level']}")
        
        return snapshot
    
    def get_latest_market_condition(self) -> Optional[MarketConditionSnapshot]:
        """
        Get the most recent market condition snapshot.
        
        Returns:
            Latest MarketConditionSnapshot or None if none exists
        """
        return MarketConditionSnapshot.objects.order_by('-timestamp').first()
    
    def is_market_safe_for_trading(self) -> bool:
        """
        Check if current market conditions are safe for trading.
        
        Returns:
            True if market is safe for trading, False otherwise
        """
        latest = self.get_latest_market_condition()
        
        if not latest:
            return True  # Assume safe if no data
        
        # Don't trade during crashes or high-risk periods
        if latest.market_condition in [MarketCondition.CRASHING]:
            return False
        
        if latest.crash_risk_level in ['critical', 'high']:
            return False
        
        if latest.bot_activity_score > 0.8:  # Very high bot activity
            return False
        
        return True