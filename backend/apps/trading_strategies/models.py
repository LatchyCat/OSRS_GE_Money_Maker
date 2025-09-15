from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import json


class StrategyType(models.TextChoices):
    """Types of trading strategies available"""
    FLIPPING = 'flipping', 'Flipping'
    DECANTING = 'decanting', 'Decanting'
    SET_COMBINING = 'set_combining', 'Set Combining'
    CRAFTING = 'crafting', 'Crafting'
    ARBITRAGE = 'arbitrage', 'Arbitrage'
    HIGH_ALCHEMY = 'high_alchemy', 'High Alchemy'
    BOND_FLIPPING = 'bond_flipping', 'Bond Flipping'
    RUNE_MAGIC = 'rune_magic', 'Rune & Magic'


class MarketCondition(models.TextChoices):
    """Market condition states"""
    STABLE = 'stable', 'Stable'
    VOLATILE = 'volatile', 'Volatile' 
    CRASHING = 'crashing', 'Crashing'
    RECOVERING = 'recovering', 'Recovering'
    BULLISH = 'bullish', 'Bullish'
    BEARISH = 'bearish', 'Bearish'


class TradingStrategy(models.Model):
    """Base model for all trading strategies"""
    
    strategy_type = models.CharField(
        max_length=20,
        choices=StrategyType.choices,
        help_text="Type of trading strategy"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Human-readable name for the strategy"
    )
    
    description = models.TextField(
        help_text="Detailed description of how the strategy works"
    )
    
    # Profitability metrics
    potential_profit_gp = models.BigIntegerField(
        help_text="Potential profit in GP per transaction"
    )
    
    profit_margin_pct = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('999.9999'))],
        help_text="Profit margin as percentage"
    )
    
    # Risk assessment
    risk_level = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'), 
            ('high', 'High'),
            ('extreme', 'Extreme')
        ],
        default='medium',
        help_text="Risk level of the strategy"
    )
    
    # Capital requirements
    min_capital_required = models.BigIntegerField(
        help_text="Minimum capital required in GP"
    )
    
    recommended_capital = models.BigIntegerField(
        help_text="Recommended capital for optimal returns"
    )
    
    # Market conditions
    optimal_market_condition = models.CharField(
        max_length=20,
        choices=MarketCondition.choices,
        help_text="Best market condition for this strategy"
    )
    
    # Timing and volume
    estimated_time_minutes = models.IntegerField(
        help_text="Estimated time to complete one cycle in minutes"
    )
    
    max_volume_per_day = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum recommended volume per day"
    )
    
    # Strategy metadata
    confidence_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
        help_text="Confidence score from 0.0 to 1.0"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this strategy is currently viable"
    )
    
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # JSON fields for strategy-specific data
    strategy_data = models.JSONField(
        default=dict,
        help_text="Strategy-specific data and parameters"
    )
    
    class Meta:
        verbose_name = "Trading Strategy"
        verbose_name_plural = "Trading Strategies"
        ordering = ['-potential_profit_gp', '-confidence_score']
        indexes = [
            models.Index(fields=['strategy_type', 'is_active']),
            models.Index(fields=['profit_margin_pct']),
            models.Index(fields=['risk_level']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_strategy_type_display()})"
    
    @property
    def hourly_profit_potential(self):
        """Calculate potential profit per hour"""
        if self.estimated_time_minutes > 0:
            cycles_per_hour = 60 / self.estimated_time_minutes
            return int(self.potential_profit_gp * cycles_per_hour)
        return 0
    
    @property
    def roi_percentage(self):
        """Return on Investment percentage"""
        if self.min_capital_required > 0:
            return float((self.potential_profit_gp / self.min_capital_required) * 100)
        return 0.0


class DecantingOpportunity(models.Model):
    """Specific model for potion decanting opportunities"""
    
    strategy = models.ForeignKey(
        TradingStrategy,
        on_delete=models.CASCADE,
        related_name='decanting_opportunities'
    )
    
    # Item information
    item_id = models.IntegerField(help_text="Item ID of the potion")
    item_name = models.CharField(max_length=100)
    
    # Dose information
    from_dose = models.IntegerField(help_text="Original dose count (e.g., 4)")
    to_dose = models.IntegerField(help_text="Target dose count (e.g., 3)")
    
    # Pricing
    from_dose_price = models.IntegerField(help_text="Price of original dose potion")
    to_dose_price = models.IntegerField(help_text="Price of target dose potion")
    
    # Volume and availability
    from_dose_volume = models.IntegerField(default=0)
    to_dose_volume = models.IntegerField(default=0)
    
    # Profitability
    profit_per_conversion = models.IntegerField(help_text="Profit per conversion")
    profit_per_hour = models.IntegerField(default=0, help_text="Estimated profit per hour")
    
    # Volume analysis fields
    trading_activity = models.CharField(
        max_length=20, 
        default='unknown',
        choices=[
            ('very_active', 'Very Active'),
            ('active', 'Active'),
            ('moderate', 'Moderate'),
            ('low', 'Low'),
            ('inactive', 'Inactive'),
            ('unknown', 'Unknown'),
        ],
        help_text="Trading activity level based on volume analysis"
    )
    liquidity_score = models.FloatField(
        default=0.0, 
        help_text="Liquidity score from 0.0-1.0 based on volume consistency"
    )
    confidence_score = models.FloatField(
        default=0.0,
        help_text="Overall confidence score based on price and volume analysis"
    )
    volume_analysis_data = models.JSONField(
        null=True, blank=True,
        help_text="Full volume analysis data from RuneScape Wiki API"
    )
    
    class Meta:
        unique_together = ['item_id', 'from_dose', 'to_dose']
        ordering = ['-profit_per_conversion']


class SetCombiningOpportunity(models.Model):
    """Model for armor/weapon set combining opportunities"""
    
    strategy = models.ForeignKey(
        TradingStrategy,
        on_delete=models.CASCADE,
        related_name='set_combining_opportunities'
    )
    
    # Set information
    set_name = models.CharField(max_length=100)
    set_item_id = models.IntegerField(help_text="Complete set item ID")
    
    # Individual pieces
    piece_ids = models.JSONField(
        help_text="List of individual piece item IDs"
    )
    
    piece_names = models.JSONField(
        help_text="List of individual piece names"
    )
    
    # Pricing
    individual_pieces_total_cost = models.IntegerField(
        help_text="Total cost of buying all pieces individually"
    )
    
    complete_set_price = models.IntegerField(
        help_text="Price of the complete set"
    )
    
    # The "lazy tax" profit
    lazy_tax_profit = models.IntegerField(
        help_text="Profit from player convenience (lazy tax)"
    )
    
    # Volume data
    piece_volumes = models.JSONField(
        default=dict,
        help_text="Volume data for individual pieces"
    )
    
    set_volume = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['set_name']  # Use set_name instead since set_item_id can be 0 for multiple sets
        ordering = ['-lazy_tax_profit']


class FlippingOpportunity(models.Model):
    """Model for basic flipping opportunities"""
    
    strategy = models.ForeignKey(
        TradingStrategy,
        on_delete=models.CASCADE,
        related_name='flipping_opportunities'
    )
    
    item_id = models.IntegerField()
    item_name = models.CharField(max_length=100)
    
    # Pricing
    buy_price = models.IntegerField()
    sell_price = models.IntegerField()
    margin = models.IntegerField()
    margin_percentage = models.DecimalField(max_digits=8, decimal_places=4)
    
    # Volume and liquidity
    buy_volume = models.IntegerField(default=0)
    sell_volume = models.IntegerField(default=0)
    
    # Market depth
    price_stability = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
        help_text="Price stability score (0-1)"
    )
    
    # Trading metrics
    estimated_flip_time_minutes = models.IntegerField(default=30)
    recommended_quantity = models.IntegerField(default=1)
    
    class Meta:
        unique_together = ['item_id']
        ordering = ['-margin_percentage', '-margin']


class CraftingOpportunity(models.Model):
    """Model for crafting profit opportunities"""
    
    strategy = models.ForeignKey(
        TradingStrategy,
        on_delete=models.CASCADE,
        related_name='crafting_opportunities'
    )
    
    # Product information
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=100)
    product_price = models.IntegerField()
    
    # Materials cost
    materials_cost = models.IntegerField()
    materials_data = models.JSONField(
        help_text="List of materials with IDs, names, quantities, and prices"
    )
    
    # Crafting requirements
    required_skill_level = models.IntegerField(default=1)
    skill_name = models.CharField(max_length=50)
    
    # Profitability
    profit_per_craft = models.IntegerField()
    profit_margin_pct = models.DecimalField(max_digits=8, decimal_places=4)
    
    # Volume and time
    crafting_time_seconds = models.IntegerField(default=60)
    max_crafts_per_hour = models.IntegerField(default=60)
    
    class Meta:
        unique_together = ['product_id']
        ordering = ['-profit_per_craft']


class MarketConditionSnapshot(models.Model):
    """Model to track overall market conditions"""
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Overall market state
    market_condition = models.CharField(
        max_length=20,
        choices=MarketCondition.choices
    )
    
    # Market metrics
    total_volume_24h = models.BigIntegerField(default=0)
    average_price_change_pct = models.DecimalField(max_digits=8, decimal_places=4)
    volatility_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))]
    )
    
    # Bot activity detection
    bot_activity_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
        help_text="Estimated bot activity level (0-1)"
    )
    
    # Market alerts
    crash_risk_level = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical')
        ],
        default='low'
    )
    
    # Additional data
    market_data = models.JSONField(
        default=dict,
        help_text="Additional market analysis data"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['market_condition']),
        ]


class StrategyPerformance(models.Model):
    """Track performance of strategies over time"""
    
    strategy = models.ForeignKey(
        TradingStrategy,
        on_delete=models.CASCADE,
        related_name='performance_records'
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Performance metrics
    actual_profit_gp = models.BigIntegerField()
    expected_profit_gp = models.BigIntegerField()
    accuracy_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))]
    )
    
    # Execution data
    capital_used = models.BigIntegerField()
    execution_time_minutes = models.IntegerField()
    
    # Success metrics
    successful_trades = models.IntegerField(default=0)
    failed_trades = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['strategy', 'timestamp']),
        ]


class MoneyMakerStrategy(models.Model):
    """
    Enhanced base model for money making strategies like your friend's approach:
    Bonds → Flipping → Decanting → Set Combining progression
    """
    
    strategy = models.OneToOneField(
        TradingStrategy,
        on_delete=models.CASCADE,
        related_name='money_maker_strategy'
    )
    
    # Capital progression tracking (your friend's 50M → 100M approach)
    starting_capital = models.BigIntegerField(help_text="Starting capital in GP")
    current_capital = models.BigIntegerField(help_text="Current capital in GP")
    target_capital = models.BigIntegerField(help_text="Target capital goal in GP")
    
    # Hourly profit tracking (critical for price-sensitive opportunities)
    hourly_profit_gp = models.BigIntegerField(
        default=0,
        help_text="Average profit per hour in GP"
    )
    
    hourly_profit_updated = models.DateTimeField(
        auto_now=True,
        help_text="When hourly profit was last calculated"
    )
    
    # Market timing and frequency
    optimal_trading_hours = models.JSONField(
        default=list,
        help_text="Best hours to execute this strategy (0-23)"
    )
    
    update_frequency_minutes = models.IntegerField(
        default=60,
        help_text="How often to recalculate opportunities"
    )
    
    # Strategy scaling (important for capital growth)
    scales_with_capital = models.BooleanField(
        default=True,
        help_text="Whether profits scale with increased capital"
    )
    
    capital_efficiency_multiplier = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=Decimal('1.0'),
        help_text="How efficiently capital is used (1.0 = 100% efficiency)"
    )
    
    # Risk management
    max_capital_per_trade = models.BigIntegerField(
        help_text="Maximum capital to risk per single trade"
    )
    
    stop_loss_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Stop loss threshold as percentage"
    )
    
    # Performance tracking
    success_rate_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.0'),
        help_text="Historical success rate"
    )
    
    total_trades_executed = models.IntegerField(default=0)
    total_profit_realized = models.BigIntegerField(default=0)
    
    # Lazy tax exploitation (key for set combining)
    exploits_lazy_tax = models.BooleanField(
        default=False,
        help_text="Whether this strategy exploits player laziness"
    )
    
    lazy_tax_premium_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Premium percentage players pay for convenience"
    )
    
    class Meta:
        verbose_name = "Money Maker Strategy"
        verbose_name_plural = "Money Maker Strategies"
        indexes = [
            models.Index(fields=['-hourly_profit_gp']),
            models.Index(fields=['starting_capital', 'target_capital']),
            models.Index(fields=['success_rate_percentage']),
        ]
    
    def __str__(self):
        return f"{self.strategy.name} - {self.hourly_profit_gp:,} GP/hr"
    
    @property
    def capital_growth_rate(self):
        """Calculate capital growth rate"""
        if self.starting_capital > 0:
            return ((self.current_capital - self.starting_capital) / self.starting_capital) * 100
        return 0.0
    
    @property
    def is_profitable(self):
        """Check if strategy is currently profitable"""
        return self.hourly_profit_gp > 0 and self.success_rate_percentage > 50
    
    @property
    def risk_adjusted_return(self):
        """Calculate risk-adjusted hourly return"""
        base_return = self.hourly_profit_gp
        risk_factor = (100 - self.success_rate_percentage) / 100
        return int(base_return * (1 - risk_factor))


class BondFlippingStrategy(models.Model):
    """
    Bond and high-value item flipping strategy
    Your friend's starting point: buying bonds and flipping high-value items
    """
    
    money_maker = models.OneToOneField(
        MoneyMakerStrategy,
        on_delete=models.CASCADE,
        related_name='bond_flipping'
    )
    
    # Target items for flipping
    target_item_ids = models.JSONField(
        help_text="List of high-value item IDs to flip"
    )
    
    target_item_data = models.JSONField(
        default=dict,
        help_text="Detailed data about target items with prices and margins"
    )
    
    # Bond-specific data
    bond_price_gp = models.IntegerField(
        help_text="Current Old School Bond price in GP"
    )
    
    bond_to_gp_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="GP per dollar spent on bonds"
    )
    
    # Flipping parameters
    min_margin_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.0'),
        help_text="Minimum profit margin to consider"
    )
    
    max_hold_time_hours = models.IntegerField(
        default=24,
        help_text="Maximum time to hold an item before cutting losses"
    )
    
    # Market monitoring
    price_check_frequency_minutes = models.IntegerField(
        default=5,
        help_text="How often to check prices for flip opportunities"
    )
    
    last_opportunity_scan = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When we last scanned for opportunities"
    )
    
    class Meta:
        verbose_name = "Bond Flipping Strategy"
    
    def __str__(self):
        return f"Bond Flipping - {len(self.target_item_ids)} items"


class AdvancedDecantingStrategy(models.Model):
    """
    Enhanced decanting strategy for potion profit optimization
    Your friend's 40M profit approach from decanting potions
    """
    
    money_maker = models.OneToOneField(
        MoneyMakerStrategy,
        on_delete=models.CASCADE,
        related_name='advanced_decanting'
    )
    
    # Target potions with dose variations
    target_potions = models.JSONField(
        help_text="Dict of potion_id: {doses: [4,3,2,1], base_name: str}"
    )
    
    # Profitability tracking per potion type
    potion_profits = models.JSONField(
        default=dict,
        help_text="Current profit margins for each potion/dose combination"
    )
    
    # Decanting parameters
    min_profit_per_dose_gp = models.IntegerField(
        default=100,
        help_text="Minimum profit per dose to consider worthwhile"
    )
    
    optimal_dose_combinations = models.JSONField(
        default=list,
        help_text="Most profitable dose combinations [(from_dose, to_dose, profit)]"
    )
    
    # Volume and liquidity tracking
    daily_volume_targets = models.JSONField(
        default=dict,
        help_text="Target daily volumes for each potion type"
    )
    
    market_liquidity_scores = models.JSONField(
        default=dict,
        help_text="Liquidity scores for each potion (0-100)"
    )
    
    # Automation and efficiency
    barbarian_herblore_required = models.BooleanField(
        default=True,
        help_text="Whether Barbarian Herblore is required for this strategy"
    )
    
    decanting_speed_per_hour = models.IntegerField(
        default=1000,
        help_text="Estimated potions that can be decanted per hour"
    )
    
    # Performance tracking
    total_potions_decanted = models.IntegerField(default=0)
    total_decanting_profit = models.BigIntegerField(default=0)
    
    class Meta:
        verbose_name = "Advanced Decanting Strategy"
    
    def __str__(self):
        return f"Decanting - {len(self.target_potions)} potion types"


class EnhancedSetCombiningStrategy(models.Model):
    """
    Set combining strategy exploiting the "lazy tax"
    Your friend's approach: buy pieces separately, sell as complete sets
    """
    
    money_maker = models.OneToOneField(
        MoneyMakerStrategy,
        on_delete=models.CASCADE,
        related_name='enhanced_set_combining'
    )
    
    # Target armor/weapon sets
    target_sets = models.JSONField(
        help_text="Dict of set_id: {pieces: [item_ids], set_name: str}"
    )
    
    # Current set opportunities
    set_opportunities = models.JSONField(
        default=dict,
        help_text="Current profit opportunities for each set"
    )
    
    # Lazy tax analysis
    average_lazy_tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.0'),
        help_text="Average lazy tax across all sets"
    )
    
    high_lazy_tax_sets = models.JSONField(
        default=list,
        help_text="Sets with exceptionally high lazy tax premiums"
    )
    
    # Market timing
    optimal_buying_times = models.JSONField(
        default=list,
        help_text="Best times to buy individual pieces"
    )
    
    optimal_selling_times = models.JSONField(
        default=list,
        help_text="Best times to sell complete sets"
    )
    
    # Risk management for sets
    max_sets_held_simultaneously = models.IntegerField(
        default=5,
        help_text="Maximum number of incomplete sets to hold"
    )
    
    piece_acquisition_timeout_hours = models.IntegerField(
        default=48,
        help_text="Max time to spend acquiring all pieces"
    )
    
    # Volume and competition tracking
    set_competition_levels = models.JSONField(
        default=dict,
        help_text="Competition level for each set (low/medium/high)"
    )
    
    recommended_daily_sets = models.JSONField(
        default=dict,
        help_text="Recommended number of each set to complete daily"
    )
    
    # Performance tracking
    total_sets_completed = models.IntegerField(default=0)
    total_set_profit = models.BigIntegerField(default=0)
    incomplete_sets_value = models.BigIntegerField(default=0)
    
    class Meta:
        verbose_name = "Enhanced Set Combining Strategy"
    
    def __str__(self):
        return f"Set Combining - {len(self.target_sets)} sets"


class RuneMagicStrategy(models.Model):
    """
    Rune crafting and magic-related money making strategies
    Includes rune running, crafting, and magic supply arbitrage
    """
    
    money_maker = models.OneToOneField(
        MoneyMakerStrategy,
        on_delete=models.CASCADE,
        related_name='rune_magic'
    )
    
    # Target runes and magic supplies
    target_runes = models.JSONField(
        help_text="List of profitable rune types and their margins"
    )
    
    magic_supplies = models.JSONField(
        help_text="Magic-related supplies with profit opportunities"
    )
    
    # Runecrafting specifics
    runecrafting_level_required = models.IntegerField(
        default=1,
        help_text="Minimum Runecrafting level required"
    )
    
    runes_per_hour = models.IntegerField(
        default=0,
        help_text="Estimated runes craftable per hour"
    )
    
    # Essence and supply costs
    essence_costs = models.JSONField(
        default=dict,
        help_text="Current costs for different essence types"
    )
    
    # Magic training arbitrage
    magic_training_items = models.JSONField(
        default=list,
        help_text="Items profitable for magic training arbitrage"
    )
    
    high_alch_opportunities = models.JSONField(
        default=list,
        help_text="Current high alchemy opportunities"
    )
    
    class Meta:
        verbose_name = "Rune & Magic Strategy"
    
    def __str__(self):
        return f"Rune & Magic - {len(self.target_runes)} rune types"
