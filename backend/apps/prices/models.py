from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.items.models import Item
import json
from typing import Dict, List, Optional, Any


class PriceSnapshot(models.Model):
    """
    Stores Grand Exchange price data from RuneScape API.
    """
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='price_snapshots')
    
    # Price data from API
    high_price = models.IntegerField(null=True, blank=True, help_text="Instant buy price")
    high_time = models.DateTimeField(null=True, blank=True, help_text="When high price was recorded")
    low_price = models.IntegerField(null=True, blank=True, help_text="Instant sell price")
    low_time = models.DateTimeField(null=True, blank=True, help_text="When low price was recorded")
    
    # Volume data for frequency calculation
    high_price_volume = models.IntegerField(null=True, blank=True, help_text="Number of high price transactions")
    low_price_volume = models.IntegerField(null=True, blank=True, help_text="Number of low price transactions") 
    total_volume = models.IntegerField(null=True, blank=True, help_text="Total trading volume in time period")
    
    # Price movement indicators
    price_volatility = models.FloatField(null=True, blank=True, help_text="Price volatility score (0-1)")
    price_change_pct = models.FloatField(null=True, blank=True, help_text="Price change % from previous snapshot")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    api_source = models.CharField(max_length=50, default='runescape_wiki', help_text="API source")
    data_interval = models.CharField(max_length=10, default='latest', help_text="Data interval (latest, 5m, 1h)")
    
    class Meta:
        db_table = 'price_snapshots'
        indexes = [
            models.Index(fields=['item', '-created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['high_price']),
            models.Index(fields=['low_price']),
            models.Index(fields=['total_volume']),
            models.Index(fields=['data_interval']),
            models.Index(fields=['price_volatility']),
            models.Index(fields=['item', 'data_interval', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def profit_if_buy_high(self):
        """Calculate profit if buying at high price and alching."""
        if self.high_price is None:
            return None
        return self.item.calculate_profit(self.high_price)
    
    @property
    def profit_margin_if_buy_high(self):
        """Calculate profit margin if buying at high price and alching."""
        if self.high_price is None:
            return None
        return self.item.calculate_profit_margin(self.high_price)
    
    @property
    def is_high_volume(self):
        """Determine if this item has high trading volume."""
        if self.total_volume is None:
            return False
        return self.total_volume > 100  # Configurable threshold
    
    @property
    def is_volatile(self):
        """Determine if this item price is volatile."""
        if self.price_volatility is None:
            return False
        return self.price_volatility > 0.15  # 15% volatility threshold
    
    @property
    def recommended_update_frequency_minutes(self):
        """Calculate recommended update frequency based on volume and volatility."""
        base_frequency = 60  # 1 hour default
        
        if self.total_volume is None:
            return base_frequency
        
        # Volume-based adjustments
        if self.total_volume > 1000:  # Very high volume
            base_frequency = 1  # 1 minute
        elif self.total_volume > 500:  # High volume
            base_frequency = 5  # 5 minutes
        elif self.total_volume > 100:  # Medium volume
            base_frequency = 15  # 15 minutes
        elif self.total_volume > 10:  # Low volume
            base_frequency = 30  # 30 minutes
        
        # Volatility adjustments (reduce frequency for volatile items)
        if self.price_volatility and self.price_volatility > 0.2:
            base_frequency = max(1, base_frequency // 2)  # Half the time, min 1 minute
        
        return base_frequency
    
    @classmethod
    def get_volume_category(cls, volume):
        """Categorize items by volume for update frequency."""
        if volume is None or volume == 0:
            return 'inactive'
        elif volume >= 1000:
            return 'hot'  # 1-5 minute updates
        elif volume >= 100:
            return 'warm'  # 15-30 minute updates
        elif volume >= 10:
            return 'cool'  # 1-2 hour updates
        else:
            return 'cold'  # 6+ hour updates


class PriceAggregate(models.Model):
    """
    Aggregated price data over different time periods (5min, 1hour, etc).
    """
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='price_aggregates')
    
    # Aggregation metadata
    interval = models.CharField(max_length=20, choices=[
        ('5m', '5 minutes'),
        ('1h', '1 hour'),
        ('6h', '6 hours'),
        ('24h', '24 hours'),
    ])
    timestamp = models.DateTimeField(help_text="Start of the time period")
    
    # Aggregated price data
    avg_high_price = models.IntegerField(null=True, blank=True)
    high_price_volume = models.IntegerField(default=0)
    avg_low_price = models.IntegerField(null=True, blank=True)
    low_price_volume = models.IntegerField(default=0)
    
    # Calculated fields
    avg_profit = models.IntegerField(null=True, blank=True, help_text="Average profit from high alch")
    avg_profit_margin = models.FloatField(null=True, blank=True, help_text="Average profit margin %")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_aggregates'
        unique_together = ['item', 'interval', 'timestamp']
        indexes = [
            models.Index(fields=['item', 'interval', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['avg_profit']),
        ]
    
    def save(self, *args, **kwargs):
        # Calculate profit fields before saving
        if self.avg_high_price:
            self.avg_profit = self.item.calculate_profit(self.avg_high_price)
            self.avg_profit_margin = self.item.calculate_profit_margin(self.avg_high_price)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.item.name} - {self.interval} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class ProfitCalculation(models.Model):
    """
    Cached profit calculations for items to speed up queries.
    """
    
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name='profit_calc')
    
    # Current best prices
    current_buy_price = models.IntegerField(null=True, blank=True)
    current_sell_price = models.IntegerField(null=True, blank=True)
    
    # Profit calculations
    current_profit = models.IntegerField(default=0, help_text="Current profit per item")
    current_profit_margin = models.FloatField(default=0.0, help_text="Current profit margin %")
    
    # Volume and trend data
    daily_volume = models.IntegerField(default=0, help_text="24h trading volume")
    hourly_volume = models.IntegerField(default=0, help_text="1h trading volume")
    five_min_volume = models.IntegerField(default=0, help_text="5min trading volume")
    
    price_trend = models.CharField(max_length=20, choices=[
        ('rising', 'Rising'),
        ('falling', 'Falling'),
        ('stable', 'Stable'),
    ], default='stable')
    
    # Volume-based categorization
    volume_category = models.CharField(max_length=20, choices=[
        ('hot', 'Hot - High volume'),
        ('warm', 'Warm - Medium volume'),
        ('cool', 'Cool - Low volume'),
        ('cold', 'Cold - Very low volume'),
        ('inactive', 'Inactive'),
    ], default='inactive')
    
    # Price volatility and momentum
    price_volatility = models.FloatField(default=0.0, help_text="Price volatility score (0-1)")
    price_momentum = models.FloatField(default=0.0, help_text="Price momentum indicator")
    
    # Recommendation score (0-100)
    recommendation_score = models.IntegerField(default=0, help_text="AI-calculated recommendation score")
    volume_weighted_score = models.IntegerField(default=0, help_text="Volume-weighted recommendation score")
    
    # High Alchemy specific scoring (0-100)
    high_alch_viability_score = models.IntegerField(default=0, help_text="High alchemy viability score (0-100)")
    alch_efficiency_rating = models.IntegerField(default=0, help_text="Alch efficiency based on profit-per-time (0-100)")
    sustainable_alch_potential = models.IntegerField(default=0, help_text="Sustainable alching potential considering buy limits (0-100)")
    magic_xp_efficiency = models.FloatField(default=0.0, help_text="Magic XP per GP spent efficiency")
    
    # Data source metadata (for multi-source transparency)
    data_source = models.CharField(max_length=50, default='unknown', help_text="Source of price data (weird_gloop, wiki_timeseries_5m, etc.)")
    data_quality = models.CharField(max_length=20, default='unknown', help_text="Data quality level (fresh, recent, acceptable, stale)")
    confidence_score = models.FloatField(default=0.5, help_text="Confidence in data accuracy (0.0-1.0)")
    data_age_hours = models.FloatField(default=0.0, help_text="Age of source data in hours")
    source_timestamp = models.DateTimeField(null=True, blank=True, help_text="When source data was originally created")
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'profit_calculations'
        indexes = [
            models.Index(fields=['-current_profit']),
            models.Index(fields=['-recommendation_score']),
            models.Index(fields=['-volume_weighted_score']),
            models.Index(fields=['-high_alch_viability_score']),
            models.Index(fields=['-alch_efficiency_rating']),
            models.Index(fields=['-sustainable_alch_potential']),
            models.Index(fields=['volume_category']),
            models.Index(fields=['daily_volume']),
            models.Index(fields=['price_volatility']),
            models.Index(fields=['data_source']),
            models.Index(fields=['data_quality']),
            models.Index(fields=['last_updated']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - Profit: {self.current_profit}gp"
    
    @property
    def is_profitable(self):
        """Check if item is currently profitable for high alching."""
        return self.current_profit > 0
    
    def update_from_price_snapshot(self, price_snapshot):
        """Update profit calculation from latest price snapshot."""
        if price_snapshot.high_price:
            self.current_buy_price = price_snapshot.high_price
            self.current_profit = self.item.calculate_profit(price_snapshot.high_price)
            self.current_profit_margin = self.item.calculate_profit_margin(price_snapshot.high_price)
        
        if price_snapshot.low_price:
            self.current_sell_price = price_snapshot.low_price
        
        # Update volume data if available - FIXED: properly populate all volume fields
        if price_snapshot.total_volume is not None:
            if price_snapshot.data_interval == '5m':
                self.five_min_volume = price_snapshot.total_volume
            elif price_snapshot.data_interval == '1h':
                self.hourly_volume = price_snapshot.total_volume
                # Also populate daily_volume for decanting detector compatibility
                if not self.daily_volume or self.daily_volume < price_snapshot.total_volume:
                    # Estimate daily volume as ~24x hourly volume (conservative approach)
                    self.daily_volume = max(price_snapshot.total_volume * 20, self.daily_volume or 0)
            else:  # daily or latest
                self.daily_volume = price_snapshot.total_volume
                
        # Additional volume field updates for better compatibility
        if price_snapshot.high_price_volume is not None and price_snapshot.high_price_volume > 0:
            # Map high_price_volume to hourly_volume if not set
            if not self.hourly_volume:
                self.hourly_volume = price_snapshot.high_price_volume
                
        if price_snapshot.low_price_volume is not None and price_snapshot.low_price_volume > 0:
            # Map low_price_volume to five_min_volume if not set  
            if not self.five_min_volume:
                self.five_min_volume = price_snapshot.low_price_volume
        
        # Update volatility
        if price_snapshot.price_volatility is not None:
            self.price_volatility = price_snapshot.price_volatility
        
        # Recalculate volume category and scores
        self._update_volume_category()
        self._calculate_volume_weighted_score()
        self.calculate_high_alch_scores()
        
        self.save()
    
    def update_from_multi_source_data(self, price_data, item):
        """Update profit calculation from multi-source price data."""
        from services.multi_source_price_client import PriceData
        
        if not isinstance(price_data, PriceData):
            return
        
        # Update price information
        self.current_buy_price = price_data.low_price  # Low price = instant buy price
        self.current_sell_price = price_data.high_price  # High price = instant sell price
        
        # Calculate profits using buy price (we buy at low_price to alch)
        if price_data.low_price and price_data.low_price > 0:
            self.current_profit = item.calculate_profit(price_data.low_price)
            self.current_profit_margin = item.calculate_profit_margin(price_data.low_price)
        
        # Update volume data - FIXED: properly populate daily_volume for decanting compatibility  
        if hasattr(price_data, 'volume_high') and price_data.volume_high:
            self.hourly_volume = price_data.volume_high
            # Estimate daily volume as ~20x hourly volume (conservative estimate)
            if not self.daily_volume or self.daily_volume < price_data.volume_high:
                self.daily_volume = max(price_data.volume_high * 20, self.daily_volume or 0)
                
        if hasattr(price_data, 'volume_low') and price_data.volume_low:
            self.five_min_volume = price_data.volume_low
            
        # If we have raw WeirdGloop volume data, use it for daily estimate
        if (hasattr(price_data, 'raw_data') and price_data.raw_data and 
            isinstance(price_data.raw_data, dict) and 'volume' in price_data.raw_data):
            weirdgloop_volume = price_data.raw_data.get('volume', 0)
            if weirdgloop_volume > 0:
                # WeirdGloop volume is typically daily-ish data, use it directly
                self.daily_volume = weirdgloop_volume
                # Also update hourly estimate if not already set
                if not self.hourly_volume:
                    self.hourly_volume = max(1, weirdgloop_volume // 24)  # Rough hourly estimate
        
        # Update source metadata
        self.data_source = price_data.source.value
        self.data_quality = price_data.quality.value
        self.confidence_score = price_data.confidence_score
        self.data_age_hours = price_data.age_hours
        
        if price_data.timestamp > 0:
            from django.utils import timezone
            import datetime
            self.source_timestamp = timezone.make_aware(
                datetime.datetime.fromtimestamp(price_data.timestamp)
            )
        
        # Recalculate volume category and scores
        self._update_volume_category()
        self._calculate_volume_weighted_score()
        self.calculate_high_alch_scores()
        
        self.save()
    
    def _update_volume_category(self):
        """Update volume category based on current volume data."""
        # Use the highest available volume metric
        volume = max(self.daily_volume or 0, self.hourly_volume or 0, self.five_min_volume or 0)
        self.volume_category = PriceSnapshot.get_volume_category(volume)
    
    def _calculate_volume_weighted_score(self):
        """Calculate volume-weighted recommendation score."""
        base_score = self.recommendation_score
        
        # Volume multipliers
        volume_multipliers = {
            'hot': 1.5,      # 50% bonus for high volume
            'warm': 1.2,     # 20% bonus for medium volume
            'cool': 1.0,     # No change for low volume
            'cold': 0.8,     # 20% penalty for very low volume
            'inactive': 0.5  # 50% penalty for inactive items
        }
        
        volume_mult = volume_multipliers.get(self.volume_category, 1.0)
        
        # Volatility adjustment (higher volatility = higher risk = lower score)
        volatility_penalty = max(0, self.price_volatility * 0.3)  # Up to 30% penalty
        
        # Calculate final score
        self.volume_weighted_score = max(0, min(100, int(base_score * volume_mult * (1 - volatility_penalty))))
    
    @property
    def recommended_update_frequency_minutes(self):
        """Get recommended update frequency based on volume category."""
        frequency_map = {
            'hot': 1,      # 1 minute
            'warm': 15,    # 15 minutes
            'cool': 60,    # 1 hour
            'cold': 360,   # 6 hours
            'inactive': 1440  # 24 hours
        }
        
        base_freq = frequency_map.get(self.volume_category, 60)
        
        # Adjust for volatility (more volatile = more frequent updates)
        if self.price_volatility > 0.2:
            base_freq = max(1, base_freq // 2)
        
        return base_freq
    
    @property
    def is_hot_item(self):
        """Check if this is a hot trading item."""
        return self.volume_category == 'hot'
    
    def calculate_high_alch_scores(self):
        """Calculate high alchemy specific scoring metrics."""
        # High Alchemy Viability Score (0-100)
        # Based on profit margin, absolute profit, and magic level requirement
        viability_score = 0
        if self.current_profit > 0:
            # Profit component (0-40 points)
            profit_component = min(40, (self.current_profit / 1000) * 10)  # 1000gp = 10 points, max 40
            
            # Margin component (0-30 points) 
            margin_component = min(30, self.current_profit_margin * 2)  # 15% margin = 30 points
            
            # Volume stability component (0-30 points)
            volume_component = {
                'hot': 30, 'warm': 25, 'cool': 15, 'cold': 5, 'inactive': 0
            }.get(self.volume_category, 0)
            
            viability_score = int(profit_component + margin_component + volume_component)
        
        self.high_alch_viability_score = min(100, max(0, viability_score))
        
        # Alch Efficiency Rating (0-100)
        # Time per cast: ~3 seconds, profit per cast
        efficiency_score = 0
        if self.current_profit > 0:
            # Profit per 3-second cast (higher is better)
            profit_per_cast = self.current_profit
            # Normalize to 0-100 scale (500gp per cast = 50 points, 1000gp = 100 points)
            efficiency_score = min(100, (profit_per_cast / 10))  # 10gp = 1 point
            
        self.alch_efficiency_rating = int(max(0, efficiency_score))
        
        # Sustainable Alch Potential (0-100)
        # Based on buy limit and volume - can you sustain alching this item?
        sustainability_score = 0
        if self.current_profit > 0 and self.item.limit:
            # Buy limit component (higher limits = more sustainable)
            limit_score = min(50, self.item.limit * 2)  # 25 limit = 50 points
            
            # Volume vs limit ratio (can the market support your buy limit?)
            if self.daily_volume > 0:
                volume_ratio = min(self.daily_volume / max(self.item.limit, 1), 10)  # Cap at 10x
                volume_score = min(50, volume_ratio * 5)  # 10x volume = 50 points
            else:
                volume_score = 0
                
            sustainability_score = limit_score + volume_score
        elif self.current_profit > 0:  # No limit = unlimited sustainability
            sustainability_score = 100
            
        self.sustainable_alch_potential = int(min(100, max(0, sustainability_score)))
        
        # Magic XP Efficiency (XP per GP spent)
        # High Level Alchemy gives 65 XP per cast
        if self.current_buy_price and self.current_buy_price > 0:
            self.magic_xp_efficiency = 65.0 / self.current_buy_price  # XP per GP
        else:
            self.magic_xp_efficiency = 0.0
    
    @property
    def is_excellent_alch_item(self):
        """Check if this is an excellent high alchemy item."""
        return (self.high_alch_viability_score >= 80 and 
                self.current_profit > 0 and 
                self.current_profit_margin >= 5.0)
    
    @property
    def alch_category(self):
        """Get alch recommendation category."""
        if self.high_alch_viability_score >= 80:
            return "excellent_alch"
        elif self.high_alch_viability_score >= 60:
            return "good_alch" 
        elif self.high_alch_viability_score >= 40:
            return "fair_alch"
        else:
            return "poor_alch"

    @property
    def volume_adjusted_profit(self):
        """Calculate profit adjusted for volume feasibility."""
        if self.daily_volume == 0:
            return 0
        
        # Estimate realistic daily profit based on volume
        # Assume you can capture 1-5% of daily volume depending on volume category
        capture_rates = {
            'hot': 0.01,     # 1% of very high volume
            'warm': 0.03,    # 3% of medium volume  
            'cool': 0.05,    # 5% of low volume
            'cold': 0.1,     # 10% of very low volume
            'inactive': 0.0
        }
        
        capture_rate = capture_rates.get(self.volume_category, 0.05)
        realistic_daily_quantity = int(self.daily_volume * capture_rate)
        
        return self.current_profit * realistic_daily_quantity
    
    def calculate_ge_tax_aware_profit(self, buy_price: int, sell_price: int) -> dict:
        """
        Calculate profit considering GE tax (2% on sales over 50 GP).
        
        Args:
            buy_price: Price to buy item at
            sell_price: Price to sell item at (before tax)
            
        Returns:
            Dictionary with profit analysis including GE tax
        """
        from services.weird_gloop_client import GrandExchangeTax
        
        return GrandExchangeTax.analyze_flip_viability(
            buy_price, sell_price, self.item.item_id
        )
    
    def get_flipping_opportunity(self) -> dict:
        """
        Analyze current flipping opportunity with GE tax considerations.
        
        Returns:
            Dictionary with flipping analysis or None if not viable
        """
        if not self.current_buy_price or not self.current_sell_price:
            return None
        
        analysis = self.calculate_ge_tax_aware_profit(
            self.current_buy_price, self.current_sell_price
        )
        
        if analysis['is_profitable']:
            return {
                'item_id': self.item.item_id,
                'item_name': self.item.name,
                'buy_price': analysis['buy_price'],
                'sell_price': analysis['sell_price'], 
                'ge_tax': analysis['ge_tax'],
                'net_profit': analysis['profit_per_item'],
                'margin_pct': analysis['profit_margin_pct'],
                'volume_category': self.volume_category,
                'daily_volume': self.daily_volume,
                'is_high_volume': self.is_hot_item,
                'capital_required': analysis['buy_price'],
                'estimated_daily_profit': self.volume_adjusted_profit
            }
        
        return None
    
    def update_money_maker_scores(self):
        """Update scores specifically for money maker strategies."""
        # Flipping viability score (0-100)
        flipping_score = 0
        if self.current_buy_price and self.current_sell_price:
            analysis = self.calculate_ge_tax_aware_profit(
                self.current_buy_price, self.current_sell_price
            )
            if analysis['is_profitable']:
                # Base score on profit margin after tax
                margin_score = min(50, analysis['profit_margin_pct'] * 5)  # 10% margin = 50 points
                
                # Volume bonus
                volume_bonus = {
                    'hot': 30, 'warm': 20, 'cool': 10, 'cold': 5, 'inactive': 0
                }.get(self.volume_category, 0)
                
                # GE tax efficiency bonus (lower tax = higher score)
                tax_efficiency = (1 - (analysis['ge_tax'] / analysis['sell_price'])) * 20 if analysis['sell_price'] > 0 else 0
                
                flipping_score = int(margin_score + volume_bonus + tax_efficiency)
        
        # Set combining potential (based on item type patterns)
        set_combining_score = 0
        item_name = self.item.name.lower()
        if any(keyword in item_name for keyword in ['helm', 'body', 'legs', 'skirt', 'top', 'bottom', 'chestplate']):
            set_combining_score = 40  # Base score for armor pieces
            if self.is_profitable and self.volume_category in ['hot', 'warm']:
                set_combining_score += 30  # Bonus for liquid armor pieces
        
        # Update existing scores with money maker context
        self.recommendation_score = max(self.recommendation_score, flipping_score)
        
        # Store money maker specific scores in strategy data
        if not hasattr(self, '_money_maker_scores'):
            self._money_maker_scores = {}
        
        self._money_maker_scores.update({
            'flipping_viability': flipping_score,
            'set_combining_potential': set_combining_score,
            'ge_tax_efficiency': tax_efficiency if 'tax_efficiency' in locals() else 0,
            'updated_at': timezone.now()
        })


class HistoricalPrice(models.Model):
    """
    Stores long-term historical price data from external APIs.
    Used for trend analysis, volatility calculation, and historical pattern recognition.
    """
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='historical_prices')
    
    # Price data
    price = models.IntegerField(help_text="Historical price in GP")
    volume = models.IntegerField(null=True, blank=True, help_text="Trading volume at this timestamp")
    
    # Timestamp
    timestamp = models.DateTimeField(help_text="When this price was recorded")
    
    # Source metadata
    data_source = models.CharField(max_length=50, default='weirdgloop', help_text="API source")
    api_response_raw = models.JSONField(null=True, blank=True, help_text="Raw API response for debugging")
    
    # Processing metadata
    created_at = models.DateTimeField(auto_now_add=True)
    is_validated = models.BooleanField(default=False, help_text="Whether this data point has been validated")
    
    class Meta:
        db_table = 'historical_prices'
        unique_together = ['item', 'timestamp', 'data_source']
        indexes = [
            models.Index(fields=['item', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['data_source']),
            models.Index(fields=['is_validated']),
            models.Index(fields=['item', 'timestamp', 'data_source']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - {self.price}gp @ {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class HistoricalAnalysis(models.Model):
    """
    Stores calculated historical analysis metrics for items.
    Updated periodically to provide trend and volatility insights.
    """
    
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name='historical_analysis')
    
    # Volatility metrics (standard deviation of price changes)
    volatility_7d = models.FloatField(null=True, blank=True, help_text="7-day price volatility (0-1)")
    volatility_30d = models.FloatField(null=True, blank=True, help_text="30-day price volatility (0-1)")
    volatility_90d = models.FloatField(null=True, blank=True, help_text="90-day price volatility (0-1)")
    volatility_365d = models.FloatField(null=True, blank=True, help_text="365-day price volatility (0-1)")
    
    # Trend analysis
    trend_7d = models.CharField(max_length=20, null=True, blank=True, choices=[
        ('strong_up', 'Strong Uptrend'),
        ('up', 'Uptrend'),
        ('sideways', 'Sideways'),
        ('down', 'Downtrend'),
        ('strong_down', 'Strong Downtrend'),
    ], help_text="7-day trend direction")
    trend_30d = models.CharField(max_length=20, null=True, blank=True, choices=[
        ('strong_up', 'Strong Uptrend'),
        ('up', 'Uptrend'),
        ('sideways', 'Sideways'),
        ('down', 'Downtrend'),
        ('strong_down', 'Strong Downtrend'),
    ], help_text="30-day trend direction")
    trend_90d = models.CharField(max_length=20, null=True, blank=True, choices=[
        ('strong_up', 'Strong Uptrend'),
        ('up', 'Uptrend'),
        ('sideways', 'Sideways'),
        ('down', 'Downtrend'),
        ('strong_down', 'Strong Downtrend'),
    ], help_text="90-day trend direction")
    
    # Support and resistance levels
    support_level_7d = models.IntegerField(null=True, blank=True, help_text="7-day support level in GP")
    support_level_30d = models.IntegerField(null=True, blank=True, help_text="30-day support level in GP")
    resistance_level_7d = models.IntegerField(null=True, blank=True, help_text="7-day resistance level in GP")
    resistance_level_30d = models.IntegerField(null=True, blank=True, help_text="30-day resistance level in GP")
    
    # Historical extremes
    price_min_7d = models.IntegerField(null=True, blank=True, help_text="Lowest price in last 7 days")
    price_max_7d = models.IntegerField(null=True, blank=True, help_text="Highest price in last 7 days")
    price_min_30d = models.IntegerField(null=True, blank=True, help_text="Lowest price in last 30 days")
    price_max_30d = models.IntegerField(null=True, blank=True, help_text="Highest price in last 30 days")
    price_min_90d = models.IntegerField(null=True, blank=True, help_text="Lowest price in last 90 days")
    price_max_90d = models.IntegerField(null=True, blank=True, help_text="Highest price in last 90 days")
    price_min_all_time = models.IntegerField(null=True, blank=True, help_text="All-time low price")
    price_max_all_time = models.IntegerField(null=True, blank=True, help_text="All-time high price")
    
    # Pattern detection
    seasonal_pattern = models.JSONField(null=True, blank=True, help_text="Detected seasonal patterns")
    flash_crash_history = models.JSONField(null=True, blank=True, help_text="History of flash crashes")
    recovery_patterns = models.JSONField(null=True, blank=True, help_text="Price recovery patterns after crashes")
    
    # Current position relative to history
    current_price_percentile_30d = models.FloatField(null=True, blank=True, help_text="Current price percentile vs 30d (0-100)")
    current_price_percentile_90d = models.FloatField(null=True, blank=True, help_text="Current price percentile vs 90d (0-100)")
    
    # Analysis metadata
    data_points_count = models.IntegerField(default=0, help_text="Number of historical data points used")
    last_analyzed = models.DateTimeField(auto_now=True)
    analysis_quality = models.CharField(max_length=20, default='unknown', choices=[
        ('excellent', 'Excellent (90+ days data)'),
        ('good', 'Good (30-89 days data)'),
        ('fair', 'Fair (7-29 days data)'),
        ('poor', 'Poor (<7 days data)'),
        ('unknown', 'Unknown'),
    ], help_text="Quality of historical analysis based on data availability")
    
    class Meta:
        db_table = 'historical_analysis'
        indexes = [
            models.Index(fields=['last_analyzed']),
            models.Index(fields=['analysis_quality']),
            models.Index(fields=['trend_30d']),
            models.Index(fields=['volatility_30d']),
            models.Index(fields=['current_price_percentile_30d']),
            models.Index(fields=['current_price_percentile_90d']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - Historical Analysis (Quality: {self.analysis_quality})"
    
    @property
    def is_at_historical_high(self, threshold_percentile=90):
        """Check if current price is at or near historical high."""
        if self.current_price_percentile_90d is None:
            return False
        return self.current_price_percentile_90d >= threshold_percentile
    
    @property
    def is_at_historical_low(self, threshold_percentile=10):
        """Check if current price is at or near historical low."""
        if self.current_price_percentile_90d is None:
            return False
        return self.current_price_percentile_90d <= threshold_percentile
    
    @property
    def is_breaking_resistance(self):
        """Check if current price is breaking through resistance level."""
        if not self.resistance_level_30d or not self.item.profit_calc:
            return False
        current_price = self.item.profit_calc.current_buy_price
        return current_price > self.resistance_level_30d * 1.02  # 2% buffer
    
    @property
    def is_breaking_support(self):
        """Check if current price is breaking through support level."""
        if not self.support_level_30d or not self.item.profit_calc:
            return False
        current_price = self.item.profit_calc.current_buy_price
        return current_price < self.support_level_30d * 0.98  # 2% buffer
    
    def get_volatility_category(self, period='30d'):
        """Get volatility category for specified period."""
        volatility_field = f'volatility_{period}'
        volatility = getattr(self, volatility_field, None)
        
        if volatility is None:
            return 'unknown'
        
        if volatility < 0.1:
            return 'low'
        elif volatility < 0.3:
            return 'medium'
        elif volatility < 0.6:
            return 'high'
        else:
            return 'extreme'
    
    def get_trend_strength(self, period='30d'):
        """Get trend strength for specified period."""
        trend_field = f'trend_{period}'
        trend = getattr(self, trend_field, None)
        
        if not trend:
            return 'unknown'
        
        if 'strong' in trend:
            return 'strong'
        elif trend in ['up', 'down']:
            return 'moderate'
        else:
            return 'weak'


class HistoricalPricePoint(models.Model):
    """
    Stores individual historical price data points from 5-minute and 1-hour Wiki API endpoints.
    Used for time-series analysis, trend detection, and predictive modeling.
    """
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='historical_price_points')
    
    # Time interval and timestamp  
    interval = models.CharField(max_length=10, choices=[
        ('5m', '5 minutes'),
        ('1h', '1 hour'),
    ], help_text="Price data interval from API")
    timestamp = models.DateTimeField(help_text="Start of the time period this data represents")
    
    # Price data from API
    avg_high_price = models.IntegerField(null=True, blank=True, help_text="Average high (buy) price during period")
    avg_low_price = models.IntegerField(null=True, blank=True, help_text="Average low (sell) price during period")
    high_price_volume = models.IntegerField(default=0, help_text="Volume of high price transactions")
    low_price_volume = models.IntegerField(default=0, help_text="Volume of low price transactions")
    
    # Calculated fields
    volume_weighted_price = models.IntegerField(null=True, blank=True, help_text="Volume-weighted average price")
    total_volume = models.IntegerField(default=0, help_text="Total trading volume")
    price_spread = models.IntegerField(null=True, blank=True, help_text="Spread between high and low")
    spread_percentage = models.FloatField(null=True, blank=True, help_text="Spread as % of weighted price")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    data_source = models.CharField(max_length=50, default='runescape_wiki')
    
    class Meta:
        db_table = 'historical_price_points'
        unique_together = ['item', 'interval', 'timestamp']
        indexes = [
            models.Index(fields=['item', 'interval', '-timestamp']),
            models.Index(fields=['item', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['interval']),
            models.Index(fields=['total_volume']),
            models.Index(fields=['volume_weighted_price']),
        ]
    
    def save(self, *args, **kwargs):
        # Calculate derived fields before saving
        self.total_volume = self.high_price_volume + self.low_price_volume
        
        if self.avg_high_price and self.avg_low_price and self.total_volume > 0:
            # Calculate volume-weighted price
            total_value = 0
            if self.avg_high_price and self.high_price_volume:
                total_value += self.avg_high_price * self.high_price_volume
            if self.avg_low_price and self.low_price_volume:
                total_value += self.avg_low_price * self.low_price_volume
            
            if self.total_volume > 0:
                self.volume_weighted_price = int(total_value / self.total_volume)
            
            # Calculate spread
            self.price_spread = self.avg_high_price - self.avg_low_price
            
            # Calculate spread percentage
            if self.volume_weighted_price and self.volume_weighted_price > 0:
                self.spread_percentage = (self.price_spread / self.volume_weighted_price) * 100
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.item.name} - {self.interval} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def age_hours(self) -> float:
        """Calculate age of this price point in hours."""
        return (timezone.now() - self.timestamp).total_seconds() / 3600
    
    @property
    def has_volume(self) -> bool:
        """Check if this price point has any trading volume."""
        return self.total_volume > 0
    
    @property
    def is_recent(self) -> bool:
        """Check if this price point is from the last hour."""
        return self.age_hours <= 1.0


class PriceTrend(models.Model):
    """
    Stores calculated price trend analysis for items based on historical data.
    Updated periodically to track price momentum, direction, and volatility.
    """
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='price_trends')
    
    # Analysis period and timestamp
    analysis_period = models.CharField(max_length=20, choices=[
        ('1h', '1 hour'),
        ('6h', '6 hours'), 
        ('24h', '24 hours'),
        ('7d', '7 days'),
        ('30d', '30 days'),
    ], help_text="Period over which trend was calculated")
    calculated_at = models.DateTimeField(auto_now=True, help_text="When this trend was calculated")
    
    # Trend direction and strength
    direction = models.CharField(max_length=20, choices=[
        ('strong_up', 'Strong Uptrend'),
        ('up', 'Uptrend'),
        ('sideways', 'Sideways/Flat'),
        ('down', 'Downtrend'), 
        ('strong_down', 'Strong Downtrend'),
        ('volatile', 'Highly Volatile'),
    ], help_text="Overall price direction")
    
    strength = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)], 
                               help_text="Trend strength (0.0 = no trend, 1.0 = very strong)")
    
    # Price movement metrics
    price_change = models.IntegerField(help_text="Absolute price change in GP over period")
    price_change_percent = models.FloatField(help_text="Price change as percentage")
    volatility = models.FloatField(help_text="Price volatility during period (0.0-1.0)")
    
    # Volume analysis
    average_volume = models.IntegerField(default=0, help_text="Average trading volume per period")
    volume_trend = models.CharField(max_length=20, choices=[
        ('increasing', 'Increasing Volume'),
        ('decreasing', 'Decreasing Volume'),
        ('stable', 'Stable Volume'),
        ('volatile', 'Volatile Volume'),
    ], default='stable', help_text="Volume trend direction")
    
    # Support and resistance levels
    resistance_level = models.IntegerField(null=True, blank=True, help_text="Identified resistance level in GP")
    support_level = models.IntegerField(null=True, blank=True, help_text="Identified support level in GP")
    
    # Momentum indicators
    momentum = models.FloatField(help_text="Price momentum indicator (-1.0 to 1.0)")
    acceleration = models.FloatField(help_text="Price acceleration/deceleration indicator")
    
    # Pattern recognition
    pattern_detected = models.CharField(max_length=50, null=True, blank=True, choices=[
        ('breakout_up', 'Upward Breakout'),
        ('breakout_down', 'Downward Breakout'),
        ('reversal_up', 'Bullish Reversal'),
        ('reversal_down', 'Bearish Reversal'),
        ('consolidation', 'Price Consolidation'),
        ('flash_spike', 'Flash Price Spike'),
        ('flash_crash', 'Flash Price Crash'),
        ('steady_growth', 'Steady Growth'),
        ('steady_decline', 'Steady Decline'),
    ], help_text="Detected price pattern")
    
    pattern_confidence = models.FloatField(null=True, blank=True, 
                                         validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
                                         help_text="Confidence in pattern detection (0.0-1.0)")
    
    # Data quality metrics
    data_points_used = models.IntegerField(help_text="Number of historical data points used in analysis")
    analysis_quality = models.CharField(max_length=20, choices=[
        ('excellent', 'Excellent (>50 data points)'),
        ('good', 'Good (20-50 data points)'),
        ('fair', 'Fair (10-20 data points)'),
        ('poor', 'Poor (<10 data points)'),
    ], default='poor', help_text="Quality of trend analysis")
    
    class Meta:
        db_table = 'price_trends'
        unique_together = ['item', 'analysis_period']
        indexes = [
            models.Index(fields=['item', 'analysis_period']),
            models.Index(fields=['calculated_at']),
            models.Index(fields=['direction']),
            models.Index(fields=['strength']),
            models.Index(fields=['pattern_detected']),
            models.Index(fields=['analysis_quality']),
            models.Index(fields=['price_change_percent']),
            models.Index(fields=['momentum']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - {self.analysis_period} - {self.direction} ({self.strength:.2f})"
    
    @property
    def is_trending_up(self) -> bool:
        """Check if item is in an uptrend."""
        return self.direction in ['up', 'strong_up']
    
    @property
    def is_trending_down(self) -> bool:
        """Check if item is in a downtrend."""
        return self.direction in ['down', 'strong_down']
    
    @property
    def is_volatile(self) -> bool:
        """Check if item is highly volatile."""
        return self.volatility > 0.3 or self.direction == 'volatile'
    
    @property
    def has_momentum(self) -> bool:
        """Check if item has significant price momentum."""
        return abs(self.momentum) > 0.3
    
    @property
    def is_breaking_resistance(self) -> bool:
        """Check if recent price action suggests breaking resistance."""
        return (self.pattern_detected == 'breakout_up' and 
                self.pattern_confidence and self.pattern_confidence > 0.7)
    
    @property
    def is_breaking_support(self) -> bool:
        """Check if recent price action suggests breaking support."""
        return (self.pattern_detected == 'breakout_down' and 
                self.pattern_confidence and self.pattern_confidence > 0.7)


class MarketAlert(models.Model):
    """
    Stores market alerts for significant price movements, pattern detections, and trading opportunities.
    Used to notify users and AI systems of important market events.
    """
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='market_alerts')
    
    # Alert classification
    alert_type = models.CharField(max_length=30, choices=[
        ('price_spike', 'Sudden Price Spike'),
        ('price_crash', 'Sudden Price Crash'),
        ('volume_surge', 'Volume Surge'),
        ('trend_reversal', 'Trend Reversal'),
        ('breakout', 'Price Breakout'),
        ('pattern_detected', 'Pattern Recognition'),
        ('opportunity', 'Trading Opportunity'),
        ('risk_warning', 'Risk Warning'),
    ], help_text="Type of market alert")
    
    # Alert priority and urgency
    priority = models.CharField(max_length=20, choices=[
        ('critical', 'Critical - Immediate Action'),
        ('high', 'High - Act Soon'),
        ('medium', 'Medium - Worth Noting'),
        ('low', 'Low - Informational'),
    ], help_text="Alert priority level")
    
    # Alert details
    title = models.CharField(max_length=200, help_text="Brief alert title")
    message = models.TextField(help_text="Detailed alert message")
    
    # Market data at time of alert
    trigger_price = models.IntegerField(null=True, blank=True, help_text="Price that triggered alert")
    trigger_volume = models.IntegerField(null=True, blank=True, help_text="Volume that triggered alert")
    price_change_percent = models.FloatField(null=True, blank=True, help_text="Price change % that triggered alert")
    
    # Alert metadata  
    confidence_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
                                       help_text="Confidence in alert accuracy (0.0-1.0)")
    
    # Related trend/pattern data
    related_trend = models.ForeignKey(PriceTrend, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='triggered_alerts')
    
    # Status tracking
    is_active = models.BooleanField(default=True, help_text="Whether alert is still active")
    acknowledged_at = models.DateTimeField(null=True, blank=True, help_text="When alert was acknowledged")
    resolved_at = models.DateTimeField(null=True, blank=True, help_text="When alert condition resolved")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When alert expires")
    
    class Meta:
        db_table = 'market_alerts' 
        indexes = [
            models.Index(fields=['item', '-created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['alert_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['is_active']),
            models.Index(fields=['confidence_score']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - {self.alert_type} - {self.priority.upper()}"
    
    @property
    def is_expired(self) -> bool:
        """Check if alert has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def age_minutes(self) -> float:
        """Calculate age of alert in minutes."""
        return (timezone.now() - self.created_at).total_seconds() / 60
    
    @property
    def is_recent(self) -> bool:
        """Check if alert is from the last hour."""
        return self.age_minutes <= 60
    
    def acknowledge(self):
        """Mark alert as acknowledged."""
        self.acknowledged_at = timezone.now()
        self.save()
    
    def resolve(self):
        """Mark alert as resolved and deactivate."""
        self.resolved_at = timezone.now()
        self.is_active = False
        self.save()


class PricePattern(models.Model):
    """
    Stores detected price patterns and their characteristics for pattern matching and AI learning.
    Used to identify similar market conditions and predict future price movements.
    """
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='price_patterns')
    
    # Pattern identification
    pattern_name = models.CharField(max_length=50, choices=[
        ('double_top', 'Double Top'),
        ('double_bottom', 'Double Bottom'),
        ('head_shoulders', 'Head and Shoulders'),
        ('inverse_head_shoulders', 'Inverse Head and Shoulders'),
        ('ascending_triangle', 'Ascending Triangle'),
        ('descending_triangle', 'Descending Triangle'),
        ('symmetrical_triangle', 'Symmetrical Triangle'),
        ('bull_flag', 'Bull Flag'),
        ('bear_flag', 'Bear Flag'),
        ('cup_handle', 'Cup and Handle'),
        ('wedge_rising', 'Rising Wedge'),
        ('wedge_falling', 'Falling Wedge'),
        ('channel_up', 'Ascending Channel'),
        ('channel_down', 'Descending Channel'),
        ('spike_reversal', 'Spike Reversal'),
        ('gradual_reversal', 'Gradual Reversal'),
    ], help_text="Recognized pattern type")
    
    # Pattern timing
    start_time = models.DateTimeField(help_text="When pattern formation began")
    end_time = models.DateTimeField(help_text="When pattern completed/confirmed")
    duration_hours = models.FloatField(help_text="Pattern duration in hours")
    
    # Pattern characteristics
    start_price = models.IntegerField(help_text="Price at pattern start")
    end_price = models.IntegerField(help_text="Price at pattern completion")
    high_price = models.IntegerField(help_text="Highest price during pattern")
    low_price = models.IntegerField(help_text="Lowest price during pattern")
    
    # Pattern metrics
    price_range = models.IntegerField(help_text="High - Low price range")
    breakout_direction = models.CharField(max_length=10, choices=[
        ('up', 'Upward'),
        ('down', 'Downward'),
        ('sideways', 'Sideways'),
        ('pending', 'Pending'),
    ], help_text="Direction of pattern breakout")
    
    breakout_volume = models.IntegerField(null=True, blank=True, help_text="Volume during breakout")
    
    # Pattern reliability and outcome
    confidence_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
                                       help_text="Pattern recognition confidence")
    
    predicted_target = models.IntegerField(null=True, blank=True, help_text="Predicted price target")
    actual_outcome = models.IntegerField(null=True, blank=True, help_text="Actual price reached after pattern")
    prediction_accuracy = models.FloatField(null=True, blank=True, help_text="How accurate prediction was (0-1)")
    
    # Volume analysis during pattern
    average_volume = models.IntegerField(help_text="Average volume during pattern formation")
    volume_trend = models.CharField(max_length=20, choices=[
        ('increasing', 'Increasing'),
        ('decreasing', 'Decreasing'),
        ('stable', 'Stable'),
        ('volatile', 'Volatile'),
    ], help_text="Volume trend during pattern")
    
    # AI/ML metadata
    feature_vector = models.JSONField(null=True, blank=True, help_text="Pattern features for ML training")
    similar_patterns = models.JSONField(null=True, blank=True, help_text="IDs of similar historical patterns")
    
    # Status and validation
    is_confirmed = models.BooleanField(default=False, help_text="Whether pattern breakout confirmed")
    is_validated = models.BooleanField(default=False, help_text="Whether pattern outcome validated")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_patterns'
        indexes = [
            models.Index(fields=['item', 'pattern_name']),
            models.Index(fields=['pattern_name']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['breakout_direction']),
            models.Index(fields=['is_confirmed']),
            models.Index(fields=['prediction_accuracy']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - {self.pattern_name} - {self.start_time.strftime('%Y-%m-%d')}"
    
    @property
    def price_change_percent(self) -> float:
        """Calculate percentage price change during pattern."""
        if self.start_price > 0:
            return ((self.end_price - self.start_price) / self.start_price) * 100
        return 0.0
    
    @property
    def was_profitable(self) -> bool:
        """Check if pattern led to profitable outcome."""
        return (self.actual_outcome and 
                self.predicted_target and
                ((self.breakout_direction == 'up' and self.actual_outcome > self.end_price) or
                 (self.breakout_direction == 'down' and self.actual_outcome < self.end_price)))
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if pattern has high confidence score."""
        return self.confidence_score >= 0.8
    
    def calculate_prediction_accuracy(self):
        """Calculate and store prediction accuracy after outcome is known."""
        if self.predicted_target and self.actual_outcome:
            # Calculate how close prediction was to actual outcome
            max_error = abs(self.predicted_target - self.end_price)
            actual_error = abs(self.predicted_target - self.actual_outcome)
            
            if max_error > 0:
                self.prediction_accuracy = max(0, 1 - (actual_error / max_error))
            else:
                self.prediction_accuracy = 1.0
            
            self.save()
    
    def confirm_breakout(self, actual_direction: str, breakout_vol: int):
        """Confirm pattern breakout with actual data."""
        self.breakout_direction = actual_direction
        self.breakout_volume = breakout_vol
        self.is_confirmed = True
        self.save()
    
    def validate_outcome(self, final_price: int):
        """Validate pattern outcome with final price data."""
        self.actual_outcome = final_price
        self.calculate_prediction_accuracy()
        self.is_validated = True
        self.save()
