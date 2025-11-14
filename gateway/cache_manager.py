"""
Cache Manager
=============

Caches API responses to avoid redundant calls.

Features:
- TTL-based expiration
- LRU eviction policy
- Cache invalidation
- Hit/miss statistics

Version: 1.0.0
Date: 2025-11-13
"""

from typing import Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import OrderedDict
from loguru import logger
import hashlib
import json
import threading


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    hits: int = 0
    last_accessed: Optional[datetime] = None


@dataclass
class CacheConfig:
    """Cache configuration"""
    max_size: int = 1000  # Maximum entries
    default_ttl_seconds: int = 300  # 5 minutes default
    enable_stats: bool = True


class CacheManager:
    """
    Response cache with TTL and LRU eviction

    Features:
    - Automatic expiration
    - Size-based eviction (LRU)
    - Hit/miss statistics
    - Thread-safe
    """

    def __init__(self, name: str, config: Optional[CacheConfig] = None):
        """
        Initialize cache manager

        Args:
            name: Cache identifier
            config: Cache configuration
        """
        self.name = name
        self.config = config or CacheConfig()
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.Lock()

        # Statistics
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.evictions = 0
        self.expirations = 0

        logger.info(
            f"CacheManager '{name}' initialized: "
            f"max_size={self.config.max_size}, "
            f"ttl={self.config.default_ttl_seconds}s"
        )

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            self.total_requests += 1

            if key not in self.cache:
                self.cache_misses += 1
                return None

            entry = self.cache[key]

            # Check if expired
            if datetime.now() > entry.expires_at:
                self.cache_misses += 1
                self.expirations += 1
                del self.cache[key]
                logger.debug(f"Cache '{self.name}': Key '{key}' expired")
                return None

            # Cache hit!
            self.cache_hits += 1
            entry.hits += 1
            entry.last_accessed = datetime.now()

            # Move to end (LRU)
            self.cache.move_to_end(key)

            logger.debug(
                f"Cache '{self.name}': HIT for key '{key}' "
                f"(hit #{entry.hits})"
            )

            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ):
        """
        Store value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live (uses default if None)
        """
        with self.lock:
            ttl = ttl_seconds or self.config.default_ttl_seconds
            now = datetime.now()

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=now + timedelta(seconds=ttl)
            )

            # Check if cache is full
            if len(self.cache) >= self.config.max_size and key not in self.cache:
                # Evict least recently used
                evicted_key, _ = self.cache.popitem(last=False)
                self.evictions += 1
                logger.debug(
                    f"Cache '{self.name}': Evicted key '{evicted_key}' (LRU)"
                )

            self.cache[key] = entry
            self.cache.move_to_end(key)

            logger.debug(
                f"Cache '{self.name}': SET key '{key}' "
                f"(ttl={ttl}s, size={len(self.cache)})"
            )

    def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key

        Returns:
            True if key existed
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Cache '{self.name}': Deleted key '{key}'")
                return True
            return False

    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cache '{self.name}': Cleared {count} entries")

    def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable[[], Any],
        ttl_seconds: Optional[int] = None
    ) -> Any:
        """
        Get from cache or fetch and cache

        Args:
            key: Cache key
            fetch_func: Function to fetch value if not in cache
            ttl_seconds: TTL for cached value

        Returns:
            Cached or fetched value
        """
        # Try cache first
        cached = self.get(key)
        if cached is not None:
            return cached

        # Cache miss - fetch value
        logger.debug(f"Cache '{self.name}': Fetching for key '{key}'")
        value = fetch_func()

        # Cache the result
        self.set(key, value, ttl_seconds)

        return value

    def invalidate_pattern(self, pattern: str):
        """
        Invalidate all keys matching pattern

        Args:
            pattern: String pattern to match (simple substring match)
        """
        with self.lock:
            keys_to_delete = [
                key for key in self.cache.keys()
                if pattern in key
            ]

            for key in keys_to_delete:
                del self.cache[key]

            if keys_to_delete:
                logger.info(
                    f"Cache '{self.name}': Invalidated {len(keys_to_delete)} "
                    f"keys matching pattern '{pattern}'"
                )

    def cleanup_expired(self):
        """Remove all expired entries"""
        with self.lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self.cache.items()
                if now > entry.expires_at
            ]

            for key in expired_keys:
                del self.cache[key]
                self.expirations += 1

            if expired_keys:
                logger.debug(
                    f"Cache '{self.name}': Cleaned up {len(expired_keys)} expired entries"
                )

    def get_stats(self) -> dict:
        """Get cache statistics"""
        with self.lock:
            hit_rate = 0.0
            if self.total_requests > 0:
                hit_rate = self.cache_hits / self.total_requests

            return {
                "name": self.name,
                "size": len(self.cache),
                "max_size": self.config.max_size,
                "utilization": len(self.cache) / self.config.max_size,
                "total_requests": self.total_requests,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "hit_rate": hit_rate,
                "evictions": self.evictions,
                "expirations": self.expirations
            }

    def get_top_keys(self, limit: int = 10) -> list:
        """
        Get most frequently accessed keys

        Args:
            limit: Number of keys to return

        Returns:
            List of (key, hits) tuples
        """
        with self.lock:
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: x[1].hits,
                reverse=True
            )
            return [(key, entry.hits) for key, entry in sorted_entries[:limit]]


class CacheManagerRegistry:
    """Manages multiple cache instances"""

    def __init__(self):
        """Initialize cache registry"""
        self.caches: dict[str, CacheManager] = {}
        logger.info("CacheManagerRegistry initialized")

    def get_cache(
        self,
        name: str,
        config: Optional[CacheConfig] = None
    ) -> CacheManager:
        """
        Get or create cache

        Args:
            name: Cache name
            config: Configuration (only used if creating new)

        Returns:
            CacheManager instance
        """
        if name not in self.caches:
            self.caches[name] = CacheManager(name, config)
        return self.caches[name]

    def get_all_stats(self) -> dict:
        """Get statistics for all caches"""
        return {
            name: cache.get_stats()
            for name, cache in self.caches.items()
        }

    def clear_all(self):
        """Clear all caches"""
        for cache in self.caches.values():
            cache.clear()
        logger.info("All caches cleared")

    def cleanup_all_expired(self):
        """Cleanup expired entries in all caches"""
        for cache in self.caches.values():
            cache.cleanup_expired()


def generate_cache_key(operation: str, **params) -> str:
    """
    Generate cache key from operation and parameters

    Args:
        operation: Operation name
        **params: Parameters to include in key

    Returns:
        Cache key string
    """
    # Sort params for consistent keys
    sorted_params = sorted(params.items())

    # Create deterministic string
    param_str = json.dumps(sorted_params, sort_keys=True)

    # Hash for shorter keys
    key_hash = hashlib.md5(f"{operation}:{param_str}".encode()).hexdigest()[:16]

    return f"{operation}:{key_hash}"


# Predefined cache configurations
CACHE_CONFIGS = {
    "worldtracer": CacheConfig(max_size=1000, default_ttl_seconds=300),  # 5 min
    "dcs": CacheConfig(max_size=5000, default_ttl_seconds=600),  # 10 min
    "bhs": CacheConfig(max_size=10000, default_ttl_seconds=60),  # 1 min (fast changing)
    "courier": CacheConfig(max_size=500, default_ttl_seconds=3600),  # 1 hour
    "flight_info": CacheConfig(max_size=2000, default_ttl_seconds=1800),  # 30 min
}
