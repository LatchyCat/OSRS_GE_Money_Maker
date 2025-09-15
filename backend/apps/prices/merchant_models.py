"""
Merchant-specific models for market analysis, opportunities, and trading positions.
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from apps.items.models import Item
from apps.prices.models import PriceSnapshot


class MarketTrend(models.Model):
    """
    Historical price trend analysis for merchant opportunities.
    """
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='market_trends')
    
    # Time period for trend analysis
    period_type = models.CharField(max_length=20, choices=[
        ('1h', '1 Hour'),
        ('6h', '6 Hours'),
        ('24h', '24 Hours'),
        ('7d', '7 Days'),
        ('30d', '30 Days'),
    ])
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Price trend data
    price_min = models.IntegerField(help_text="Minimum price in period")
    price_max = models.IntegerField(help_text="Maximum price in period") 
    price_avg = models.IntegerField(help_text="Average price in period")
    price_median = models.IntegerField(help_text="Median price in period")
    price_current = models.IntegerField(help_text="Current/latest price")
    
    # Volume trend data
    volume_total = models.IntegerField(default=0, help_text="Total volume in period")
    volume_avg = models.IntegerField(default=0, help_text="Average volume in period")
    volume_current = models.IntegerField(default=0, help_text="Current volume")
    
    # Trend indicators
    trend_direction = models.CharField(max_length=20, choices=[
        ('strong_up', 'Strong Uptrend'),
        ('weak_up', 'Weak Uptrend'),
        ('sideways', 'Sideways'),
        ('weak_down', 'Weak Downtrend'),
        ('strong_down', 'Strong Downtrend'),
    ], default='sideways')
    
    volatility_score = models.FloatField(default=0.0, help_text="Price volatility (0.0-1.0)")
    momentum_score = models.FloatField(default=0.0, help_text="Price momentum (-1.0 to 1.0)")
    volume_momentum = models.FloatField(default=0.0, help_text="Volume momentum (-1.0 to 1.0)")
    
    # Support and resistance levels
    support_level = models.IntegerField(null=True, blank=True, help_text="Support price level")
    resistance_level = models.IntegerField(null=True, blank=True, help_text="Resistance price level")
    
    # Pattern recognition
    pattern_type = models.CharField(max_length=30, choices=[
        ('breakout_up', 'Upward Breakout'),
        ('breakout_down', 'Downward Breakout'),
        ('bounce_support', 'Bounce off Support'),
        ('reject_resistance', 'Rejected at Resistance'),
        ('range_bound', 'Range Bound'),
        ('trend_reversal', 'Trend Reversal'),
        ('consolidation', 'Consolidation'),
        ('unknown', 'Unknown Pattern'),
    ], default='unknown')
    
    pattern_confidence = models.FloatField(default=0.0, help_text="Pattern recognition confidence (0.0-1.0)")
    
    # Calculated at
    calculated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'market_trends'
        unique_together = ['item', 'period_type', 'period_start']
        indexes = [
            models.Index(fields=['item', 'period_type', '-period_end']),
            models.Index(fields=['-calculated_at']),
            models.Index(fields=['trend_direction']),
            models.Index(fields=['pattern_type']),
            models.Index(fields=['-volatility_score']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - {self.period_type} trend ({self.trend_direction})"
    
    @property
    def price_range_pct(self):
        """Calculate price range as percentage."""
        if self.price_avg > 0:
            return ((self.price_max - self.price_min) / self.price_avg) * 100
        return 0.0
    
    @property
    def is_volatile(self):
        """Check if item is highly volatile."""
        return self.volatility_score > 0.15  # 15% threshold
    
    @property
    def is_trending(self):
        """Check if item has a strong trend."""
        return self.trend_direction in ['strong_up', 'strong_down']


class MerchantOpportunity(models.Model):
    """
    Buy/sell opportunities identified by market analysis.
    """
    
    OPPORTUNITY_TYPES = [
        ('flip_quick', 'Quick Flip (Minutes)'),
        ('swing_short', 'Short Swing (Hours)'),
        ('swing_medium', 'Medium Swing (Days)'),
        ('position_long', 'Long Position (Weeks)'),
        ('arbitrage', 'Price Arbitrage'),
        ('pattern_trade', 'Pattern Trade'),
    ]
    
    RISK_LEVELS = [
        ('conservative', 'Conservative (Low Risk)'),
        ('moderate', 'Moderate (Medium Risk)'),
        ('aggressive', 'Aggressive (High Risk)'),
        ('speculative', 'Speculative (Very High Risk)'),
    ]
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='merchant_opportunities')
    
    # Opportunity details
    opportunity_type = models.CharField(max_length=20, choices=OPPORTUNITY_TYPES)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS)
    
    # Price targets
    current_price = models.IntegerField(help_text="Current market price")
    target_buy_price = models.IntegerField(help_text="Recommended buy price")
    target_sell_price = models.IntegerField(help_text="Target sell price")
    stop_loss_price = models.IntegerField(null=True, blank=True, help_text="Stop loss price")
    
    # Profit projections
    projected_profit_per_item = models.IntegerField(help_text="Expected profit per item")
    projected_profit_margin_pct = models.FloatField(help_text="Expected profit margin %")
    estimated_trade_volume = models.IntegerField(default=1, help_text="Estimated tradeable volume")
    total_projected_profit = models.IntegerField(help_text="Total expected profit")
    
    # Risk assessment
    risk_score = models.FloatField(default=0.5, help_text="Risk score (0.0-1.0)")
    confidence_score = models.FloatField(default=0.5, help_text="Confidence score (0.0-1.0)")
    success_probability = models.FloatField(default=0.5, help_text="Success probability (0.0-1.0)")
    
    # Timing
    opportunity_score = models.IntegerField(default=50, help_text="Overall opportunity score (0-100)")
    time_sensitivity = models.CharField(max_length=20, choices=[
        ('immediate', 'Act Immediately'),
        ('urgent', 'Act Within Hours'),
        ('moderate', 'Act Within Days'),
        ('flexible', 'Flexible Timing'),
    ], default='moderate')
    
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When opportunity expires")
    
    # Market context
    based_on_trend = models.ForeignKey(MarketTrend, null=True, blank=True, on_delete=models.SET_NULL)
    reasoning = models.TextField(help_text="AI explanation of why this is an opportunity")
    
    # Status tracking
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('executed', 'Executed'),
        ('cancelled', 'Cancelled'),
    ], default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'merchant_opportunities'
        indexes = [
            models.Index(fields=['-opportunity_score']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['opportunity_type']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['time_sensitivity']),
            models.Index(fields=['-total_projected_profit']),
        ]
    
    def __str__(self):
        return f"{self.item.name} - {self.opportunity_type} (Score: {self.opportunity_score})"
    
    @property
    def is_active(self):
        """Check if opportunity is still active."""
        if self.status != 'active':
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
    
    @property
    def potential_roi_pct(self):
        """Calculate potential return on investment percentage."""
        if self.target_buy_price > 0:
            return ((self.target_sell_price - self.target_buy_price) / self.target_buy_price) * 100
        return 0.0


class MerchantAlert(models.Model):
    """
    User-defined merchant alerts for trading opportunities.
    """
    
    ALERT_TYPES = [
        ('price_above', 'Price Above Threshold'),
        ('price_below', 'Price Below Threshold'),
        ('volume_spike', 'Volume Spike'),
        ('volatility_high', 'High Volatility'),
        ('trend_reversal', 'Trend Reversal'),
        ('opportunity', 'New Opportunity'),
    ]
    
    ALERT_STATUS = [
        ('active', 'Active'),
        ('triggered', 'Triggered'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='merchant_alerts')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='merchant_alerts')
    
    # Alert configuration
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    threshold_price = models.IntegerField(null=True, blank=True, help_text="Price threshold")
    threshold_volume = models.IntegerField(null=True, blank=True, help_text="Volume threshold")
    threshold_volatility = models.FloatField(null=True, blank=True, help_text="Volatility threshold")
    
    # Alert details
    message = models.TextField(blank=True, help_text="Custom alert message")
    notes = models.TextField(blank=True, help_text="User notes")
    
    # Status
    status = models.CharField(max_length=20, choices=ALERT_STATUS, default='active')
    triggered_at = models.DateTimeField(null=True, blank=True)
    triggered_price = models.IntegerField(null=True, blank=True)
    
    # Notification settings
    notify_email = models.BooleanField(default=True)
    notify_browser = models.BooleanField(default=True)
    repeat_notifications = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'merchant_alerts'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['item', 'status']),
            models.Index(fields=['alert_type']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.item.name} {self.alert_type}"
    
    def check_trigger(self, current_price, current_volume=None, current_volatility=None):
        """Check if alert should be triggered."""
        if self.status != 'active':
            return False
        
        triggered = False
        
        if self.alert_type == 'price_above' and self.threshold_price:
            triggered = current_price >= self.threshold_price
        elif self.alert_type == 'price_below' and self.threshold_price:
            triggered = current_price <= self.threshold_price
        elif self.alert_type == 'volume_spike' and self.threshold_volume and current_volume:
            triggered = current_volume >= self.threshold_volume
        elif self.alert_type == 'volatility_high' and self.threshold_volatility and current_volatility:
            triggered = current_volatility >= self.threshold_volatility
        
        if triggered:
            self.status = 'triggered'
            self.triggered_at = timezone.now()
            self.triggered_price = current_price
            self.save()
        
        return triggered


class TradingPosition(models.Model):
    """
    Track user's actual trading positions for merchant activities.
    """
    
    POSITION_TYPES = [
        ('long', 'Long Position (Buy to Sell)'),
        ('short', 'Short Position (Sell to Buy)'),
    ]
    
    POSITION_STATUS = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('partial', 'Partially Closed'),
        ('stopped', 'Stopped Out'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trading_positions')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='trading_positions')
    opportunity = models.ForeignKey(MerchantOpportunity, null=True, blank=True, on_delete=models.SET_NULL)
    
    # Position details
    position_type = models.CharField(max_length=10, choices=POSITION_TYPES, default='long')
    status = models.CharField(max_length=20, choices=POSITION_STATUS, default='open')
    
    # Entry details
    entry_price = models.IntegerField(help_text="Price at which position was entered")
    entry_quantity = models.IntegerField(help_text="Number of items bought/sold")
    entry_timestamp = models.DateTimeField(auto_now_add=True)
    entry_notes = models.TextField(blank=True)
    
    # Exit details (for closed positions)
    exit_price = models.IntegerField(null=True, blank=True, help_text="Price at which position was closed")
    exit_quantity = models.IntegerField(null=True, blank=True, help_text="Number of items sold/bought back")
    exit_timestamp = models.DateTimeField(null=True, blank=True)
    exit_notes = models.TextField(blank=True)
    
    # Stop loss and targets
    stop_loss_price = models.IntegerField(null=True, blank=True)
    target_price = models.IntegerField(null=True, blank=True)
    
    # P&L tracking
    realized_profit = models.IntegerField(default=0, help_text="Actual profit/loss from closed portion")
    unrealized_profit = models.IntegerField(default=0, help_text="Current unrealized profit/loss")
    total_profit = models.IntegerField(default=0, help_text="Total profit (realized + unrealized)")
    
    # Performance metrics
    return_pct = models.FloatField(default=0.0, help_text="Return percentage")
    holding_period_hours = models.IntegerField(default=0, help_text="How long position was held")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'trading_positions'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['item', 'status']),
            models.Index(fields=['-entry_timestamp']),
            models.Index(fields=['-total_profit']),
            models.Index(fields=['-return_pct']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.item.name} {self.position_type} ({self.status})"
    
    def calculate_current_pnl(self, current_price):
        """Calculate current profit/loss based on market price."""
        if self.status == 'closed':
            return self.realized_profit
        
        if self.position_type == 'long':
            # Long position: profit when price goes up
            self.unrealized_profit = (current_price - self.entry_price) * self.entry_quantity
        else:
            # Short position: profit when price goes down
            self.unrealized_profit = (self.entry_price - current_price) * self.entry_quantity
        
        self.total_profit = self.realized_profit + self.unrealized_profit
        self.return_pct = (self.total_profit / (self.entry_price * self.entry_quantity)) * 100 if self.entry_price > 0 else 0.0
        
        return self.total_profit
    
    def close_position(self, exit_price, exit_quantity=None, notes=""):
        """Close the trading position."""
        if exit_quantity is None:
            exit_quantity = self.entry_quantity
        
        self.exit_price = exit_price
        self.exit_quantity = exit_quantity
        self.exit_timestamp = timezone.now()
        self.exit_notes = notes
        
        # Calculate final profit
        if self.position_type == 'long':
            self.realized_profit = (exit_price - self.entry_price) * exit_quantity
        else:
            self.realized_profit = (self.entry_price - exit_price) * exit_quantity
        
        self.total_profit = self.realized_profit
        self.return_pct = (self.total_profit / (self.entry_price * self.entry_quantity)) * 100 if self.entry_price > 0 else 0.0
        
        # Calculate holding period
        self.holding_period_hours = int((self.exit_timestamp - self.entry_timestamp).total_seconds() / 3600)
        
        if exit_quantity >= self.entry_quantity:
            self.status = 'closed'
        else:
            self.status = 'partial'
        
        self.save()


class MerchantPortfolio(models.Model):
    """
    Track user's overall merchant portfolio performance.
    """
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='merchant_portfolio')
    
    # Portfolio metrics
    total_capital = models.IntegerField(default=0, help_text="Total capital allocated to merchant activities")
    available_capital = models.IntegerField(default=0, help_text="Available capital for new positions")
    invested_capital = models.IntegerField(default=0, help_text="Capital currently invested in positions")
    
    # Performance tracking
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    
    total_profit = models.IntegerField(default=0, help_text="Total profit across all trades")
    total_return_pct = models.FloatField(default=0.0, help_text="Total return percentage")
    
    # Risk metrics
    max_drawdown = models.IntegerField(default=0, help_text="Maximum loss from peak")
    average_win = models.IntegerField(default=0)
    average_loss = models.IntegerField(default=0)
    win_rate_pct = models.FloatField(default=0.0)
    
    # Portfolio settings
    max_position_size_pct = models.FloatField(default=10.0, help_text="Max % of capital per position")
    risk_per_trade_pct = models.FloatField(default=2.0, help_text="Max risk % per trade")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'merchant_portfolios'
    
    def __str__(self):
        return f"{self.user.username} Portfolio - {self.total_return_pct:.1f}% return"
    
    def update_from_position(self, position):
        """Update portfolio metrics when a position is closed."""
        if position.status != 'closed':
            return
        
        self.total_trades += 1
        
        if position.total_profit > 0:
            self.winning_trades += 1
            self.average_win = ((self.average_win * (self.winning_trades - 1)) + position.total_profit) / self.winning_trades
        else:
            self.losing_trades += 1
            self.average_loss = ((self.average_loss * (self.losing_trades - 1)) + abs(position.total_profit)) / self.losing_trades
        
        self.total_profit += position.total_profit
        self.win_rate_pct = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0
        
        if self.total_capital > 0:
            self.total_return_pct = (self.total_profit / self.total_capital) * 100
        
        self.save()