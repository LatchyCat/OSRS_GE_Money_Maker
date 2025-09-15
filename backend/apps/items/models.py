from django.db import models
from django.utils import timezone


class Item(models.Model):
    """
    Represents a RuneScape item with its metadata and high alch information.
    """
    
    # Core item data from RuneScape API
    item_id = models.IntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    examine = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=255, blank=True, null=True)
    
    # Economic data
    value = models.IntegerField(help_text="Item's base value in GP")
    high_alch = models.IntegerField(help_text="High alch value in GP")
    low_alch = models.IntegerField(help_text="Low alch value in GP", default=0)
    
    # Trading limits and membership
    limit = models.IntegerField(help_text="GE buy limit", default=0)
    members = models.BooleanField(default=False, help_text="Members only item")
    
    # Tracking and metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Item is actively traded")
    
    class Meta:
        db_table = 'items'
        indexes = [
            models.Index(fields=['item_id']),
            models.Index(fields=['name']),
            models.Index(fields=['high_alch']),
            models.Index(fields=['members']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} (ID: {self.item_id})"
    
    @property
    def base_profit_per_item(self):
        """
        Calculate base profit per item (high alch value minus nature rune cost).
        Does not include GE buy price.
        """
        from django.conf import settings
        nature_rune_cost = getattr(settings, 'NATURE_RUNE_COST', 180)
        return self.high_alch - nature_rune_cost
    
    def calculate_profit(self, ge_buy_price):
        """
        Calculate profit for high alching this item at given GE buy price.
        
        Args:
            ge_buy_price (int): Grand Exchange buy price in GP
            
        Returns:
            int: Profit in GP (can be negative)
        """
        return self.base_profit_per_item - ge_buy_price
    
    def calculate_profit_margin(self, ge_buy_price):
        """
        Calculate profit margin percentage for high alching.
        
        Args:
            ge_buy_price (int): Grand Exchange buy price in GP
            
        Returns:
            float: Profit margin as percentage
        """
        if ge_buy_price == 0:
            return 0.0
        profit = self.calculate_profit(ge_buy_price)
        return (profit / ge_buy_price) * 100


class ItemCategory(models.Model):
    """
    Categories for organizing items (e.g., Weapons, Armor, Consumables).
    """
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'item_categories'
        verbose_name_plural = 'Item categories'
    
    def __str__(self):
        return self.name


class ItemCategoryMapping(models.Model):
    """
    Many-to-many mapping between items and categories.
    """
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='categories')
    category = models.ForeignKey(ItemCategory, on_delete=models.CASCADE, related_name='items')
    confidence = models.FloatField(default=1.0, help_text="AI confidence in categorization (0-1)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'item_category_mappings'
        unique_together = ['item', 'category']
    
    def __str__(self):
        return f"{self.item.name} -> {self.category.name}"
