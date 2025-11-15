"""
Metrics Repository (Redis)

Handles all Redis operations:
- Caching bag data for quick lookups
- Operational metrics and counters
- Rate limiting
- Real-time statistics

Features:
- Async operations
- Graceful degradation when Redis unavailable
- TTL-based caching
- Metrics aggregation
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
import json

from app.database.redis_manager import RedisManager


class MetricsRepository:
    """
    Repository for Redis caching and metrics

    Provides caching and metrics collection.
    Gracefully degrades if Redis is unavailable.
    """

    def __init__(self, redis: Optional[RedisManager]):
        """
        Initialize metrics repository

        Args:
            redis: Redis manager (can be None for graceful degradation)
        """
        self.redis = redis
        self._available = redis is not None

    @property
    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self._available and self.redis is not None and self.redis.is_connected

    # ========================================================================
    # BAG CACHING
    # ========================================================================

    async def cache_bag_status(
        self,
        bag_tag: str,
        bag_data: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """
        Cache bag status for quick lookup

        Args:
            bag_tag: Bag tag number
            bag_data: Bag status data
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if cached successfully
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot cache bag status")
            return False

        try:
            key = f"bag:{bag_tag}"
            await self.redis.set(key, json.dumps(bag_data), ttl=ttl)
            logger.debug(f"Cached bag status: {bag_tag}")
            return True

        except Exception as e:
            logger.error(f"Failed to cache bag status: {e}")
            return False

    async def get_cached_bag_status(self, bag_tag: str) -> Optional[Dict[str, Any]]:
        """
        Get cached bag status

        Args:
            bag_tag: Bag tag number

        Returns:
            Cached bag data or None if not found/Redis unavailable
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot get cached bag")
            return None

        try:
            key = f"bag:{bag_tag}"
            cached = await self.redis.get(key)

            if cached:
                logger.debug(f"Cache hit for bag: {bag_tag}")
                return json.loads(cached)

            logger.debug(f"Cache miss for bag: {bag_tag}")
            return None

        except Exception as e:
            logger.error(f"Failed to get cached bag status: {e}")
            return None

    async def invalidate_bag_cache(self, bag_tag: str) -> bool:
        """
        Invalidate cached bag status

        Args:
            bag_tag: Bag tag number

        Returns:
            True if deleted successfully
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot invalidate cache")
            return False

        try:
            key = f"bag:{bag_tag}"
            await self.redis.delete(key)
            logger.debug(f"Cache invalidated for bag: {bag_tag}")
            return True

        except Exception as e:
            logger.error(f"Failed to invalidate bag cache: {e}")
            return False

    # ========================================================================
    # METRICS OPERATIONS
    # ========================================================================

    async def increment_counter(
        self,
        key: str,
        airline_id: Optional[int] = None,
        amount: int = 1
    ) -> int:
        """
        Increment operational counter

        Args:
            key: Counter key (e.g., "scans_processed", "pirs_created")
            airline_id: Optional airline ID for scoping
            amount: Increment amount

        Returns:
            New counter value (0 if Redis unavailable)
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot increment counter")
            return 0

        try:
            if airline_id:
                full_key = f"metric:{airline_id}:{key}"
            else:
                full_key = f"metric:{key}"

            new_value = await self.redis.incr(full_key, amount)
            logger.debug(f"Incremented counter {full_key}: {new_value}")
            return new_value

        except Exception as e:
            logger.error(f"Failed to increment counter: {e}")
            return 0

    async def get_counter(
        self,
        key: str,
        airline_id: Optional[int] = None
    ) -> int:
        """
        Get counter value

        Args:
            key: Counter key
            airline_id: Optional airline ID for scoping

        Returns:
            Counter value (0 if not found or Redis unavailable)
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot get counter")
            return 0

        try:
            if airline_id:
                full_key = f"metric:{airline_id}:{key}"
            else:
                full_key = f"metric:{key}"

            value = await self.redis.get_metric(full_key, default=0)
            return value

        except Exception as e:
            logger.error(f"Failed to get counter: {e}")
            return 0

    async def record_latency(
        self,
        operation: str,
        duration_ms: float,
        airline_id: Optional[int] = None
    ) -> bool:
        """
        Record operation latency

        Args:
            operation: Operation name (e.g., "scan_processing", "risk_assessment")
            duration_ms: Duration in milliseconds
            airline_id: Optional airline ID for scoping

        Returns:
            True if recorded successfully
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot record latency")
            return False

        try:
            timestamp = datetime.utcnow().isoformat()

            if airline_id:
                key = f"latency:{airline_id}:{operation}"
            else:
                key = f"latency:{operation}"

            # Store as hash with timestamp
            await self.redis.hset(key, timestamp, str(duration_ms))

            # Set expiration to 24 hours
            await self.redis.expire(key, 86400)

            logger.debug(f"Recorded latency for {operation}: {duration_ms}ms")
            return True

        except Exception as e:
            logger.error(f"Failed to record latency: {e}")
            return False

    async def get_average_latency(
        self,
        operation: str,
        airline_id: Optional[int] = None
    ) -> float:
        """
        Get average latency for operation

        Args:
            operation: Operation name
            airline_id: Optional airline ID for scoping

        Returns:
            Average latency in milliseconds (0.0 if no data)
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot get average latency")
            return 0.0

        try:
            if airline_id:
                key = f"latency:{airline_id}:{operation}"
            else:
                key = f"latency:{operation}"

            latencies = await self.redis.hgetall(key)

            if not latencies:
                return 0.0

            values = [float(v) for v in latencies.values()]
            avg = sum(values) / len(values)

            return round(avg, 2)

        except Exception as e:
            logger.error(f"Failed to get average latency: {e}")
            return 0.0

    # ========================================================================
    # STATISTICS AGGREGATION
    # ========================================================================

    async def get_metrics_summary(
        self,
        airline_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get summary of all metrics

        Args:
            airline_id: Optional airline ID for scoping

        Returns:
            Metrics summary dict
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot get metrics summary")
            return {}

        try:
            metrics = {
                "scans_processed": await self.get_counter("scans_processed", airline_id),
                "bags_tracked": await self.get_counter("bags_tracked", airline_id),
                "risk_assessments": await self.get_counter("risk_assessments", airline_id),
                "pirs_created": await self.get_counter("pirs_created", airline_id),
                "exceptions_created": await self.get_counter("exceptions_created", airline_id),
                "notifications_sent": await self.get_counter("notifications_sent", airline_id),
                "avg_scan_latency_ms": await self.get_average_latency("scan_processing", airline_id),
                "avg_risk_latency_ms": await self.get_average_latency("risk_assessment", airline_id)
            }

            return metrics

        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}

    async def reset_daily_metrics(self, airline_id: Optional[int] = None) -> bool:
        """
        Reset daily metrics (call this in a daily cron job)

        Args:
            airline_id: Optional airline ID for scoping

        Returns:
            True if successful
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot reset metrics")
            return False

        try:
            # Archive current metrics before reset
            timestamp = datetime.utcnow().strftime("%Y%m%d")

            metrics = await self.get_metrics_summary(airline_id)

            if airline_id:
                archive_key = f"metrics_archive:{airline_id}:{timestamp}"
            else:
                archive_key = f"metrics_archive:{timestamp}"

            await self.redis.set(archive_key, json.dumps(metrics), ttl=2592000)  # 30 days

            # Reset counters
            counters = [
                "scans_processed",
                "bags_tracked",
                "risk_assessments",
                "pirs_created",
                "exceptions_created",
                "notifications_sent"
            ]

            for counter in counters:
                if airline_id:
                    full_key = f"metric:{airline_id}:{counter}"
                else:
                    full_key = f"metric:{counter}"

                await self.redis.delete(full_key)

            logger.info(f"Daily metrics reset and archived: {archive_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to reset daily metrics: {e}")
            return False

    # ========================================================================
    # RATE LIMITING
    # ========================================================================

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> tuple[bool, int]:
        """
        Check rate limit for identifier

        Args:
            identifier: Unique identifier (user_id, api_key, etc.)
            limit: Max requests allowed
            window: Time window in seconds

        Returns:
            (allowed, remaining) tuple
        """
        if not self.is_available:
            logger.debug("Redis unavailable - rate limiting disabled")
            return (True, limit)

        try:
            key = f"ratelimit:{identifier}"
            allowed, remaining = await self.redis.check_rate_limit(key, limit, window)

            if not allowed:
                logger.warning(f"Rate limit exceeded for {identifier}")

            return (allowed, remaining)

        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            # Fail open - allow request if Redis unavailable
            return (True, limit)

    # ========================================================================
    # DASHBOARD CACHING
    # ========================================================================

    async def cache_dashboard_data(
        self,
        airline_id: int,
        dashboard_data: Dict[str, Any],
        ttl: int = 300
    ) -> bool:
        """
        Cache dashboard data for quick loading

        Args:
            airline_id: Airline ID
            dashboard_data: Dashboard data
            ttl: Time to live in seconds (default: 5 minutes)

        Returns:
            True if cached successfully
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot cache dashboard")
            return False

        try:
            key = f"dashboard:{airline_id}"
            await self.redis.set(key, json.dumps(dashboard_data), ttl=ttl)
            logger.debug(f"Cached dashboard data for airline {airline_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cache dashboard data: {e}")
            return False

    async def get_cached_dashboard(
        self,
        airline_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached dashboard data

        Args:
            airline_id: Airline ID

        Returns:
            Dashboard data or None if not found
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot get cached dashboard")
            return None

        try:
            key = f"dashboard:{airline_id}"
            cached = await self.redis.get(key)

            if cached:
                logger.debug(f"Dashboard cache hit for airline {airline_id}")
                return json.loads(cached)

            logger.debug(f"Dashboard cache miss for airline {airline_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get cached dashboard: {e}")
            return None

    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================

    async def store_session(
        self,
        session_id: str,
        session_data: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """
        Store user session data

        Args:
            session_id: Session identifier
            session_data: Session data
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if stored successfully
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot store session")
            return False

        try:
            key = f"session:{session_id}"
            await self.redis.set(key, json.dumps(session_data), ttl=ttl)
            logger.debug(f"Stored session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store session: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot get session")
            return None

        try:
            key = f"session:{session_id}"
            cached = await self.redis.get(key)

            if cached:
                return json.loads(cached)

            return None

        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session

        Args:
            session_id: Session identifier

        Returns:
            True if deleted successfully
        """
        if not self.is_available:
            logger.debug("Redis unavailable - cannot delete session")
            return False

        try:
            key = f"session:{session_id}"
            await self.redis.delete(key)
            logger.debug(f"Deleted session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
