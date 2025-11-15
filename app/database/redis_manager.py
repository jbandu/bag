"""
Redis Connection Manager (Upstash/Railway)

Provides caching, metrics, and session management using Redis.
"""
import redis.asyncio as aioredis
from typing import Optional, Any, Dict
from loguru import logger
import time
import json


class RedisManager:
    """
    Redis cache and metrics manager

    Features:
    - Connection with automatic reconnection
    - Health checks
    - Cache operations with TTL
    - Metrics aggregation
    - Rate limiting support
    """

    def __init__(
        self,
        redis_url: str,
        decode_responses: bool = True
    ):
        """
        Initialize Redis manager

        Args:
            redis_url: Redis connection URL
            decode_responses: Auto-decode bytes to strings
        """
        self.redis_url = redis_url
        self.decode_responses = decode_responses

        self._client: Optional[aioredis.Redis] = None
        self._is_connected = False

        logger.info("RedisManager initialized")

    async def connect(self):
        """Create Redis connection"""
        if self._client:
            logger.warning("Redis client already exists")
            return

        try:
            logger.info(f"Connecting to Redis...")

            self._client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=self.decode_responses,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )

            # Test connection
            await self._client.ping()

            self._is_connected = True
            logger.success("✅ Redis connected")

        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            logger.info("Redis connection closed")
            self._is_connected = False

    # ========================================================================
    # CACHE OPERATIONS
    # ========================================================================

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds
        """
        if not self._client:
            raise RuntimeError("Redis not connected")

        # Convert dicts/lists to JSON
        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        if ttl:
            await self._client.setex(key, ttl, value)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str):
        """Delete key from cache"""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return bool(await self._client.exists(key))

    async def expire(self, key: str, ttl: int):
        """Set expiration on key"""
        if not self._client:
            raise RuntimeError("Redis not connected")
        await self._client.expire(key, ttl)

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for key"""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.ttl(key)

    # ========================================================================
    # METRICS OPERATIONS
    # ========================================================================

    async def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment counter

        Args:
            key: Counter key
            amount: Increment amount

        Returns:
            New value
        """
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.incrby(key, amount)

    async def get_metric(self, key: str, default: int = 0) -> int:
        """
        Get metric value

        Args:
            key: Metric key
            default: Default value if not found

        Returns:
            Metric value
        """
        if not self._client:
            return default

        try:
            value = await self._client.get(key)
            return int(value) if value else default
        except:
            return default

    async def set_metric(self, key: str, value: int, ttl: Optional[int] = None):
        """
        Set metric value

        Args:
            key: Metric key
            value: Metric value
            ttl: Optional TTL in seconds
        """
        if not self._client:
            raise RuntimeError("Redis not connected")

        if ttl:
            await self._client.setex(key, ttl, value)
        else:
            await self._client.set(key, value)

    # ========================================================================
    # HASH OPERATIONS (for structured data)
    # ========================================================================

    async def hset(self, key: str, field: str, value: Any):
        """Set hash field"""
        if not self._client:
            raise RuntimeError("Redis not connected")

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        await self._client.hset(key, field, value)

    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field"""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.hget(key, field)

    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields"""
        if not self._client:
            raise RuntimeError("Redis not connected")
        return await self._client.hgetall(key)

    # ========================================================================
    # RATE LIMITING
    # ========================================================================

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> tuple[bool, int]:
        """
        Check rate limit

        Args:
            key: Rate limit key
            limit: Max requests
            window: Time window in seconds

        Returns:
            (allowed, remaining)
        """
        if not self._client:
            raise RuntimeError("Redis not connected")

        current = await self._client.incr(key)

        # Set expiration on first request
        if current == 1:
            await self._client.expire(key, window)

        remaining = max(0, limit - current)
        allowed = current <= limit

        return allowed, remaining

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Redis health

        Returns:
            Health status dictionary
        """
        if not self._client:
            return {
                "status": "disconnected",
                "healthy": False,
                "error": "No connection"
            }

        try:
            start = time.time()

            # Ping test
            await self._client.ping()

            # Get info
            info = await self._client.info("server")

            latency_ms = (time.time() - start) * 1000

            return {
                "status": "healthy",
                "healthy": True,
                "latency_ms": round(latency_ms, 2),
                "version": info.get("redis_version", "unknown"),
                "memory_used": info.get("used_memory_human", "unknown")
            }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e)
            }

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._is_connected and self._client is not None

    # ========================================================================
    # CACHE WARMING
    # ========================================================================

    async def warm_cache_for_copa(self):
        """
        Pre-populate cache with Copa Airlines data

        Caches:
        - Copa route network
        - Common airports
        - Frequently accessed data
        """
        logger.info("Warming cache for Copa Airlines...")

        # Cache Copa routes with 1 hour TTL
        copa_routes = {
            "PTY-MIA": {"distance_km": 2280, "flight_time_min": 180, "frequency_daily": 8},
            "PTY-BOG": {"distance_km": 805, "flight_time_min": 90, "frequency_daily": 6},
            "PTY-LIM": {"distance_km": 1865, "flight_time_min": 150, "frequency_daily": 4},
            "PTY-GIG": {"distance_km": 5570, "flight_time_min": 420, "frequency_daily": 2},
            "PTY-MEX": {"distance_km": 2360, "flight_time_min": 240, "frequency_daily": 3}
        }

        for route, data in copa_routes.items():
            await self.set(f"route:copa:{route}", json.dumps(data), ttl=3600)

        # Cache airport info
        airports = {
            "PTY": {"name": "Tocumen International", "city": "Panama City", "timezone": "America/Panama"},
            "MIA": {"name": "Miami International", "city": "Miami", "timezone": "America/New_York"},
            "BOG": {"name": "El Dorado", "city": "Bogotá", "timezone": "America/Bogota"},
            "LIM": {"name": "Jorge Chávez", "city": "Lima", "timezone": "America/Lima"}
        }

        for code, data in airports.items():
            await self.set(f"airport:{code}", json.dumps(data), ttl=86400)  # 24 hours

        logger.success(f"✅ Cache warmed with {len(copa_routes)} routes and {len(airports)} airports")
