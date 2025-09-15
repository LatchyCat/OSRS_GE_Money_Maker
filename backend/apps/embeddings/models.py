from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.items.models import Item
import numpy as np


class ItemEmbedding(models.Model):
    """
    Stores vector embeddings for items to enable semantic search.
    """
    
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name='embedding')
    
    # Embedding data
    vector = ArrayField(
        models.FloatField(),
        size=1024,  # Adjust based on embedding model dimensions
        help_text="Vector embedding of item name + examine text"
    )
    model_name = models.CharField(max_length=100, default='snowflake-arctic-embed2')
    model_version = models.CharField(max_length=50, default='latest')
    
    # Text used for embedding
    source_text = models.TextField(help_text="Text that was embedded")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'item_embeddings'
        indexes = [
            models.Index(fields=['model_name', 'model_version']),
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        return f"Embedding for {self.item.name}"
    
    @classmethod
    def create_source_text(cls, item):
        """Create the text that will be embedded for an item with comprehensive money maker context."""
        parts = [item.name]
        
        if item.examine:
            parts.append(item.examine)
        
        # Add category information if available
        categories = item.categories.all()
        if categories:
            category_names = [cat.category.name for cat in categories]
            parts.append(f"Categories: {', '.join(category_names)}")
        
        # Add membership status
        parts.append("Members item" if item.members else "Free-to-play item")
        
        # Money Maker Strategy Context
        cls._add_flipping_context(parts, item)
        cls._add_decanting_context(parts, item)
        cls._add_set_combining_context(parts, item)
        cls._add_high_alchemy_context(parts, item)
        cls._add_bond_flipping_context(parts, item)
        
        # Add profit calculation context if available
        if hasattr(item, 'profit_calc') and item.profit_calc:
            profit_calc = item.profit_calc
            cls._add_profit_analysis_context(parts, profit_calc)
        
        return " | ".join(parts)
    
    @classmethod
    def _add_flipping_context(cls, parts: list, item):
        """Add flipping-specific embedding context."""
        # Check if item has good flipping characteristics
        if hasattr(item, 'profit_calc') and item.profit_calc:
            profit_calc = item.profit_calc
            
            # Volume-based flipping potential
            if profit_calc.volume_category in ['hot', 'warm']:
                parts.append("High volume suitable for flipping")
                parts.append("Good liquidity for quick buy/sell")
                
            if profit_calc.current_buy_price and profit_calc.current_sell_price:
                # Calculate potential flip profit with GE tax
                buy_price = profit_calc.current_buy_price
                sell_price = profit_calc.current_sell_price
                
                if buy_price < sell_price:
                    # Standard GE tax calculation (1% with 5M cap)
                    ge_tax = min(int(sell_price * 0.01), 5_000_000)
                    net_profit = sell_price - ge_tax - buy_price
                    
                    if net_profit > 1000:  # 1K+ profit
                        margin_pct = (net_profit / buy_price * 100) if buy_price > 0 else 0
                        parts.append(f"Profitable flipping opportunity: {net_profit} GP profit")
                        parts.append(f"Flip margin {margin_pct:.1f}% after GE tax")
                        
                        if margin_pct >= 10:
                            parts.append("Excellent flip margins")
                        elif margin_pct >= 5:
                            parts.append("Good flip margins")
                        else:
                            parts.append("Decent flip margins")
    
    @classmethod  
    def _add_decanting_context(cls, parts: list, item):
        """Add potion decanting embedding context."""
        item_name = item.name.lower()
        
        # Check if this is a potion that can be decanted
        potion_indicators = ['potion', 'barbarian', 'dose', 'drink']
        is_potion = any(indicator in item_name for indicator in potion_indicators)
        
        if is_potion:
            parts.append("Potion suitable for decanting")
            
            # Check for dose information in name
            if '(4)' in item.name:
                parts.append("4-dose potion ideal for decanting to lower doses")
                parts.append("Decanting source potion")
            elif '(3)' in item.name:
                parts.append("3-dose potion can be decanted to lower doses")
                parts.append("Mid-tier decanting option")
            elif '(2)' in item.name:
                parts.append("2-dose potion decanting target")
                parts.append("Decanting destination option")
            elif '(1)' in item.name:
                parts.append("1-dose potion final decanting target")
                parts.append("Maximum decanting value")
                
            # Popular potions for decanting (your friend's 40M method)
            high_demand_potions = ['combat', 'prayer', 'super combat', 'ranging', 'super strength', 'super attack', 'super defence']
            if any(potion_type in item_name for potion_type in high_demand_potions):
                parts.append("High demand potion excellent for decanting profits")
                parts.append("Popular training potion good for consistent sales")
                
            # Barbarian Herblore context
            if 'barbarian' in item_name or any(pot in item_name for pot in ['combat', 'super combat']):
                parts.append("Requires Barbarian Herblore for efficient decanting")
    
    @classmethod
    def _add_set_combining_context(cls, parts: list, item):
        """Add armor/weapon set combining embedding context."""
        item_name = item.name.lower()
        
        # Armor piece indicators
        armor_pieces = ['helm', 'helmet', 'body', 'top', 'chestplate', 'legs', 'skirt', 'chainskirt', 'tassets', 'coif']
        weapon_pieces = ['sword', 'axe', 'spear', 'bow', 'staff', 'wand', 'blade', 'hilt']
        
        is_armor_piece = any(piece in item_name for piece in armor_pieces)
        is_weapon_piece = any(piece in item_name for piece in weapon_pieces)
        
        if is_armor_piece:
            parts.append("Armor piece suitable for set combining")
            parts.append("Can be combined with matching pieces for lazy tax profit")
            
            # Popular armor sets
            if any(set_name in item_name for set_name in ['dharok', 'ahrim', 'karil', 'torag', 'verac', 'guthan']):
                parts.append("Popular Barrows armor piece")
                parts.append("High demand set piece good for lazy tax exploitation")
                
            if any(set_name in item_name for set_name in ['armadyl', 'bandos']):
                parts.append("God Wars armor piece")
                parts.append("Premium armor set component with high lazy tax potential")
                
            if 'void' in item_name:
                parts.append("Void armor piece")
                parts.append("PvP/PvM popular set component")
                
        elif is_weapon_piece:
            parts.append("Weapon component for set combining")
            
            if 'godsword' in item_name or 'hilt' in item_name or 'blade' in item_name:
                parts.append("Godsword component")
                parts.append("High-value weapon set piece")
                parts.append("Premium lazy tax opportunity")
        
        # Set item detection (complete sets)
        if 'set' in item_name or ('armor' in item_name and len(item_name.split()) <= 3):
            parts.append("Complete armor/weapon set")
            parts.append("Set combining destination item")
            parts.append("Lazy tax premium price item")
    
    @classmethod
    def _add_high_alchemy_context(cls, parts: list, item):
        """Add enhanced high alchemy embedding context."""
        parts.append(f"High alchemy value: {item.high_alch} GP")
        
        # Calculate base high alch profit (without GE price)
        nature_rune_cost = 180  # Standard nature rune cost
        base_profit = item.high_alch - nature_rune_cost
        
        if base_profit > 0:
            parts.append(f"High alchemy profitable: {base_profit} GP base profit")
            parts.append("Good for high level alchemy spell")
            parts.append("Suitable for magic training")
            
            # Enhanced alch efficiency ratings
            if base_profit >= 1000:
                parts.append("Excellent high alchemy profit margins")
            elif base_profit >= 500:
                parts.append("Good high alchemy profit margins")
            elif base_profit >= 200:
                parts.append("Decent high alchemy profit margins")
        else:
            parts.append("Not profitable for high alchemy")
            
        # Add alch efficiency context based on high alch value
        if item.high_alch >= 100000:  # 100k+
            parts.append("High value alch item")
        elif item.high_alch >= 10000:   # 10k+
            parts.append("Medium value alch item")  
        elif item.high_alch >= 1000:    # 1k+
            parts.append("Low value alch item")
        
        # Add buy limit context for sustainability
        if item.limit:
            if item.limit >= 100:
                parts.append("High buy limit good for sustained alching")
            elif item.limit >= 25:
                parts.append("Medium buy limit suitable for alching")
            else:
                parts.append("Low buy limit for alching")
        else:
            parts.append("Unlimited buy limit excellent for alching")
    
    @classmethod
    def _add_bond_flipping_context(cls, parts: list, item):
        """Add bond flipping and high-value item context."""
        # High-value items suitable for bond-funded flipping
        if item.item_id == 13190:  # Old School Bond
            parts.append("Old School Bond")
            parts.append("GE tax exempt item")
            parts.append("Premium currency for high-value flipping")
            parts.append("Can be converted to GP for capital")
            
        elif hasattr(item, 'profit_calc') and item.profit_calc:
            current_price = getattr(item.profit_calc, 'current_buy_price', 0) or 0
            
            if current_price >= 50_000_000:  # 50M+ items
                parts.append("Very high value item suitable for bond flipping")
                parts.append("Premium item requiring significant capital")
                parts.append("Bond-funded investment opportunity")
            elif current_price >= 10_000_000:  # 10M+ items
                parts.append("High value item suitable for advanced flipping")
                parts.append("Significant capital requirement item")
            elif current_price >= 1_000_000:  # 1M+ items
                parts.append("Medium value item for intermediate flipping")
        
        # Expensive item indicators by name
        expensive_indicators = ['godsword', 'twisted', 'scythe', 'kodai', 'ancestral', 'justiciar', 'avernic']
        if any(indicator in item.name.lower() for indicator in expensive_indicators):
            parts.append("Expensive rare item")
            parts.append("High-end equipment suitable for bond flipping")
    
    @classmethod
    def _add_profit_analysis_context(cls, parts: list, profit_calc):
        """Add profit calculation and money maker scoring context."""
        # High alchemy scores
        if hasattr(profit_calc, 'high_alch_viability_score'):
            if profit_calc.high_alch_viability_score >= 80:
                parts.append("Excellent high alchemy opportunity")
            elif profit_calc.high_alch_viability_score >= 60:
                parts.append("Good high alchemy opportunity")
            elif profit_calc.high_alch_viability_score >= 40:
                parts.append("Fair high alchemy opportunity")
        
        # Money maker specific scoring
        if hasattr(profit_calc, '_money_maker_scores'):
            scores = profit_calc._money_maker_scores
            
            flipping_score = scores.get('flipping_viability', 0)
            if flipping_score >= 70:
                parts.append("Excellent flipping opportunity")
            elif flipping_score >= 50:
                parts.append("Good flipping opportunity")
            elif flipping_score >= 30:
                parts.append("Fair flipping opportunity")
                
            set_combining_score = scores.get('set_combining_potential', 0)  
            if set_combining_score >= 60:
                parts.append("High set combining potential")
            elif set_combining_score >= 40:
                parts.append("Good set combining potential")
        
        # Volume and liquidity context
        if profit_calc.volume_category == 'hot':
            parts.append("Very high trading volume")
            parts.append("Excellent liquidity for all strategies")
        elif profit_calc.volume_category == 'warm':
            parts.append("High trading volume")
            parts.append("Good liquidity for most strategies")
        elif profit_calc.volume_category == 'cool':
            parts.append("Moderate trading volume")
            parts.append("Decent liquidity with patience required")
        elif profit_calc.volume_category == 'cold':
            parts.append("Low trading volume")
            parts.append("Limited liquidity requires careful timing")
        elif profit_calc.volume_category == 'inactive':
            parts.append("Very low trading volume")
            parts.append("Poor liquidity not recommended for active strategies")
    
    @property
    def vector_numpy(self):
        """Return the vector as a numpy array."""
        return np.array(self.vector, dtype=np.float32)
    
    def calculate_similarity(self, other_vector):
        """
        Calculate cosine similarity with another vector.
        
        Args:
            other_vector: numpy array or list
            
        Returns:
            float: Cosine similarity score
        """
        if isinstance(other_vector, list):
            other_vector = np.array(other_vector, dtype=np.float32)
        
        # Cosine similarity
        dot_product = np.dot(self.vector_numpy, other_vector)
        norm_a = np.linalg.norm(self.vector_numpy)
        norm_b = np.linalg.norm(other_vector)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


class SearchQuery(models.Model):
    """
    Stores user search queries and their embeddings for analytics and caching.
    """
    
    query_text = models.TextField(db_index=True)
    query_hash = models.CharField(max_length=64, unique=True, help_text="SHA256 hash of query")
    
    # Embedding data
    vector = ArrayField(
        models.FloatField(),
        size=1024,  # Adjust based on embedding model dimensions
        help_text="Vector embedding of search query"
    )
    
    # Usage analytics
    search_count = models.IntegerField(default=1, help_text="Number of times this query was searched")
    last_searched = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Results metadata
    result_count = models.IntegerField(default=0, help_text="Number of results returned")
    
    class Meta:
        db_table = 'search_queries'
        indexes = [
            models.Index(fields=['query_hash']),
            models.Index(fields=['-search_count']),
            models.Index(fields=['-last_searched']),
        ]
    
    def __str__(self):
        return f"Query: {self.query_text[:50]}..."
    
    @property
    def vector_numpy(self):
        """Return the vector as a numpy array."""
        return np.array(self.vector, dtype=np.float32)


class SimilarityCache(models.Model):
    """
    Caches similarity calculations between items for faster recommendations.
    """
    
    item_a = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='similarity_a')
    item_b = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='similarity_b')
    
    similarity_score = models.FloatField(help_text="Cosine similarity score (0-1)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'similarity_cache'
        unique_together = ['item_a', 'item_b']
        indexes = [
            models.Index(fields=['item_a', '-similarity_score']),
            models.Index(fields=['item_b', '-similarity_score']),
            models.Index(fields=['-similarity_score']),
        ]
    
    def __str__(self):
        return f"{self.item_a.name} <-> {self.item_b.name}: {self.similarity_score:.3f}"


class FaissIndex(models.Model):
    """
    Metadata about FAISS indices for different embedding models.
    """
    
    name = models.CharField(max_length=100, unique=True)
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=50)
    
    # Index metadata
    dimension = models.IntegerField(help_text="Vector dimension")
    index_type = models.CharField(max_length=50, help_text="FAISS index type (e.g., IndexFlatIP)")
    num_vectors = models.IntegerField(default=0)
    
    # File paths
    index_file_path = models.CharField(max_length=500, help_text="Path to FAISS index file")
    metadata_file_path = models.CharField(max_length=500, help_text="Path to metadata JSON file")
    
    # Status
    is_active = models.BooleanField(default=True)
    last_rebuilt = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'faiss_indices'
        indexes = [
            models.Index(fields=['is_active', 'model_name']),
            models.Index(fields=['-last_rebuilt']),
        ]
    
    def __str__(self):
        return f"FAISS Index: {self.name} ({self.num_vectors} vectors)"
