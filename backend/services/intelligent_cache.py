"""
Intelligent Multi-Tier Redis Caching System

Implements a sophisticated caching strategy for the OSRS trading terminal:
- Hot Cache: Sub-second access for active trading data
- Warm Cache: Fast access for recent market data  
- Cold Cache: Background data with longer TTL
- Predictive Cache: Pre-loads data based on user patterns
"""

import json
import logging
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.conf import settings
import redis
import pickle

logger = logging.getLogger(__name__)


class CacheTier:
    """Cache tier configuration and behavior."""
    
    def __init__(self, name: str, ttl: int, priority: int, redis_db: int = 0):
        self.name = name
        self.ttl = ttl  # Time to live in seconds
        self.priority = priority  # Higher = more important
        self.redis_db = redis_db
        self.key_prefix = f"osrs_cache:{name}:"


class IntelligentCache:
    """
    Multi-tier intelligent caching system for high-performance data access.
    """
    
    # Cache tier definitions
    HOT_TIER = CacheTier("hot", ttl=30, priority=100, redis_db=1)      # 30 second TTL
    WARM_TIER = CacheTier("warm", ttl=300, priority=70, redis_db=2)    # 5 minute TTL  
    COLD_TIER = CacheTier("cold", ttl=3600, priority=40, redis_db=3)   # 1 hour TTL
    PREDICTION_TIER = CacheTier("predict", ttl=1800, priority=90, redis_db=4)  # 30 minute TTL
    
    def __init__(self):
        self.redis_clients = {}
        self.access_patterns = {}  # Track access patterns for prediction
        self.cache_hits = {}       # Track cache performance
        self.cache_misses = {}
        
        # Initialize Redis connections
        self._initialize_redis_clients()
        
        # Track performance
        self.performance_window = 1000  # Track last N requests
        
    def _initialize_redis_clients(self):
        """Initialize Redis clients for each cache tier."""
        redis_url = getattr(settings, 'CACHES', {}).get('default', {}).get('LOCATION', 'redis://127.0.0.1:6379/1')
        redis_host = redis_url.replace('redis://', '').split('/')[0].split(':')[0]
        redis_port = int(redis_url.replace('redis://', '').split('/')[0].split(':')[1]) if ':' in redis_url else 6379
        
        for tier in [self.HOT_TIER, self.WARM_TIER, self.COLD_TIER, self.PREDICTION_TIER]:
            try:
                client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=tier.redis_db,
                    decode_responses=False,  # Handle binary data
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
                
                # Test connection
                client.ping()
                self.redis_clients[tier.name] = client
                logger.debug(f"✅ Connected to Redis tier: {tier.name} (DB {tier.redis_db})")
                
            except Exception as e:
                logger.error(f"❌ Failed to connect to Redis tier {tier.name}: {e}")
                self.redis_clients[tier.name] = None
    
    def _get_cache_key(self, tier: CacheTier, key: str) -> str:
        """Generate cache key with tier prefix."""
        return f"{tier.key_prefix}{key}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage."""
        try:
            if isinstance(data, (dict, list)):
                # Use JSON for simple objects
                return json.dumps(data, cls=DjangoJSONEncoder).encode('utf-8')
            else:
                # Use pickle for complex objects
                return pickle.dumps(data)
        except Exception as e:
            logger.error(f"Data serialization failed: {e}")
            return pickle.dumps(data)  # Fallback to pickle
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis."""
        try:
            # Try JSON first (faster)
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            try:
                # Fallback to pickle
                return pickle.loads(data)
            except Exception as e:
                logger.error(f"Data deserialization failed: {e}")
                return None
    
    def set(self, key: str, value: Any, tier: str = "warm", tags: List[str] = None) -> bool:
        """
        Set a value in the specified cache tier.
        
        Args:
            key: Cache key
            value: Data to cache
            tier: Cache tier ("hot", "warm", "cold", "predict")
            tags: Optional tags for cache invalidation
            
        Returns:
            True if successful, False otherwise
        """
        # Map tier names to actual tier objects
        tier_mapping = {
            "hot": self.HOT_TIER,
            "warm": self.WARM_TIER,
            "cold": self.COLD_TIER,
            "predict": self.PREDICTION_TIER
        }
        tier_obj = tier_mapping.get(tier)
        if not tier_obj:
            logger.error(f"Invalid tier: {tier}")
            return False
            
        client = self.redis_clients.get(tier)
        
        if not client:
            logger.warning(f"Redis client not available for tier: {tier}")
            return False
        
        try:
            cache_key = self._get_cache_key(tier_obj, key)
            serialized_data = self._serialize_data(value)
            
            # Set with TTL
            success = client.setex(cache_key, tier_obj.ttl, serialized_data)
            
            # Set tags for invalidation if provided
            if tags and success:
                for tag in tags:
                    tag_key = f"tag:{tag}:{cache_key}"
                    client.sadd(tag_key, cache_key)
                    client.expire(tag_key, tier_obj.ttl + 300)  # Tags live longer than data
            
            if success:
                logger.debug(f"Cached key '{key}' in {tier} tier (TTL: {tier_obj.ttl}s)")
                
            return bool(success)
            
        except Exception as e:
            logger.error(f"Cache set failed for key '{key}' in tier '{tier}': {e}")
            return False
    
    def get(self, key: str, tiers: List[str] = None) -> Any:
        """
        Get a value from cache, checking multiple tiers in priority order.
        
        Args:
            key: Cache key
            tiers: List of tiers to check (defaults to all tiers)
            
        Returns:
            Cached value or None if not found
        """
        if tiers is None:
            tiers = ["hot", "warm", "predict", "cold"]
        
        # Track access pattern
        self._track_access_pattern(key)
        
        # Check tiers in order of priority
        for tier_name in tiers:
            # Map tier names to actual tier objects
            tier_mapping = {
                "hot": self.HOT_TIER,
                "warm": self.WARM_TIER, 
                "cold": self.COLD_TIER,
                "predict": self.PREDICTION_TIER
            }
            tier_obj = tier_mapping.get(tier_name)
            if not tier_obj:
                continue
                
            client = self.redis_clients.get(tier_name)
            
            if not client:
                continue
            
            try:
                cache_key = self._get_cache_key(tier_obj, key)
                data = client.get(cache_key)
                
                if data is not None:
                    # Cache hit
                    self._record_cache_hit(tier_name, key)
                    value = self._deserialize_data(data)
                    
                    # Promote to higher tier if accessed from lower tier
                    if tier_name in ["cold", "warm"] and value is not None:
                        self._promote_to_hot_cache(key, value)
                    
                    logger.debug(f"Cache hit for '{key}' in {tier_name} tier")
                    return value
                    
            except Exception as e:
                logger.error(f"Cache get failed for key '{key}' in tier '{tier_name}': {e}")
                continue
        
        # Cache miss
        self._record_cache_miss(key)
        logger.debug(f"Cache miss for key '{key}' across all tiers")
        return None
    
    def delete(self, key: str, all_tiers: bool = True) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key
            all_tiers: Whether to delete from all tiers (default) or just hot
            
        Returns:
            True if at least one deletion succeeded
        """
        success_count = 0
        tiers_to_check = ["hot", "warm", "cold", "predict"] if all_tiers else ["hot"]
        
        for tier_name in tiers_to_check:
            # Map tier names to actual tier objects
            tier_mapping = {
                "hot": self.HOT_TIER,
                "warm": self.WARM_TIER,
                "cold": self.COLD_TIER,
                "predict": self.PREDICTION_TIER
            }
            tier_obj = tier_mapping.get(tier_name)
            if not tier_obj:
                continue
                
            client = self.redis_clients.get(tier_name)
            
            if client:
                try:
                    cache_key = self._get_cache_key(tier_obj, key)
                    deleted = client.delete(cache_key)
                    if deleted:
                        success_count += 1
                        logger.debug(f"Deleted key '{key}' from {tier_name} tier")
                except Exception as e:
                    logger.error(f"Cache delete failed for '{key}' in {tier_name}: {e}")
        
        return success_count > 0
    
    def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries with a specific tag.
        
        Args:
            tag: Tag to invalidate
            
        Returns:
            Number of keys invalidated
        """
        invalidated_count = 0
        
        for tier_name in ["hot", "warm", "cold", "predict"]:
            client = self.redis_clients.get(tier_name)
            if not client:
                continue
                
            try:
                tag_key = f"tag:{tag}:*"
                for tag_key in client.scan_iter(match=tag_key):
                    # Get all keys for this tag
                    cache_keys = client.smembers(tag_key)
                    for cache_key in cache_keys:
                        if client.delete(cache_key):
                            invalidated_count += 1
                    
                    # Delete the tag key itself
                    client.delete(tag_key)
                    
            except Exception as e:
                logger.error(f"Tag invalidation failed for '{tag}' in {tier_name}: {e}")
        
        logger.info(f"Invalidated {invalidated_count} cache keys with tag '{tag}'")
        return invalidated_count
    
    def _promote_to_hot_cache(self, key: str, value: Any):
        """Promote frequently accessed data to hot cache."""
        self.set(key, value, tier="hot")
    
    def _track_access_pattern(self, key: str):
        """Track access patterns for predictive caching."""
        now = timezone.now()
        if key not in self.access_patterns:
            self.access_patterns[key] = []
        
        self.access_patterns[key].append(now)
        
        # Keep only recent access patterns (last hour)
        cutoff = now - timedelta(hours=1)
        self.access_patterns[key] = [
            access_time for access_time in self.access_patterns[key]
            if access_time > cutoff
        ]
    
    def _record_cache_hit(self, tier: str, key: str):
        """Record cache hit for performance tracking."""
        metric_key = f"{tier}_hits"
        if metric_key not in self.cache_hits:
            self.cache_hits[metric_key] = 0
        self.cache_hits[metric_key] += 1
    
    def _record_cache_miss(self, key: str):
        """Record cache miss for performance tracking."""
        if 'total_misses' not in self.cache_misses:
            self.cache_misses['total_misses'] = 0
        self.cache_misses['total_misses'] += 1
    
    def get_performance_stats(self) -> Dict:
        """Get cache performance statistics."""
        total_hits = sum(self.cache_hits.values())
        total_misses = self.cache_misses.get('total_misses', 0)
        total_requests = total_hits + total_misses
        
        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hit_rate_percent': round(hit_rate, 2),
            'total_requests': total_requests,
            'total_hits': total_hits,
            'total_misses': total_misses,
            'tier_breakdown': self.cache_hits,
            'active_patterns': len(self.access_patterns)
        }
    
    def preload_market_data(self, items: List[int], data_generator: Callable):
        """
        Preload market data into prediction cache.
        
        Args:
            items: List of item IDs to preload
            data_generator: Function that generates data for an item
        """
        logger.info(f"Preloading market data for {len(items)} items")
        
        for item_id in items:
            try:
                data = data_generator(item_id)
                if data:
                    cache_key = f"market_data:{item_id}"
                    self.set(cache_key, data, tier="predict", tags=[f"item_{item_id}", "market_data"])
                    
            except Exception as e:
                logger.error(f"Failed to preload data for item {item_id}: {e}")
    
    def flush_tier(self, tier: str) -> bool:
        """
        Flush an entire cache tier.
        
        Args:
            tier: Tier name to flush
            
        Returns:
            True if successful
        """
        client = self.redis_clients.get(tier)
        if not client:
            return False
        
        try:
            client.flushdb()
            logger.info(f"Flushed {tier} cache tier")
            return True
        except Exception as e:
            logger.error(f"Failed to flush {tier} tier: {e}")
            return False
    
    def get_cache_size_stats(self) -> Dict:
        """Get cache size statistics for all tiers."""
        stats = {}
        
        for tier_name in ["hot", "warm", "cold", "predict"]:
            client = self.redis_clients.get(tier_name)
            if client:
                try:
                    info = client.info()
                    stats[tier_name] = {
                        'keys': info.get('db0', {}).get('keys', 0),
                        'memory_used': info.get('used_memory_human', 'Unknown')
                    }
                except Exception as e:
                    stats[tier_name] = {'error': str(e)}
            else:
                stats[tier_name] = {'error': 'Client not available'}
        
        return stats


# Global intelligent cache instance
intelligent_cache = IntelligentCache()