"""
PostgreSQL Connection Manager (Neon)

Provides connection pooling, health checks, and query execution for PostgreSQL.
Uses asyncpg for high-performance async operations.
"""
import asyncpg
from typing import Optional, List, Dict, Any
from loguru import logger
from contextlib import asynccontextmanager
import time


class PostgresManager:
    """
    PostgreSQL database connection manager with pooling

    Features:
    - Connection pooling (min 2, max 20 connections)
    - Health checks with query latency tracking
    - Automatic reconnection
    - Read-only replica support (optional)
    - Query performance logging
    """

    def __init__(
        self,
        database_url: str,
        min_connections: int = 2,
        max_connections: int = 20,
        readonly_url: Optional[str] = None
    ):
        """
        Initialize PostgreSQL manager

        Args:
            database_url: Primary database connection string
            min_connections: Minimum pool size
            max_connections: Maximum pool size
            readonly_url: Optional readonly replica URL for analytics
        """
        self.database_url = database_url
        self.readonly_url = readonly_url
        self.min_connections = min_connections
        self.max_connections = max_connections

        self._pool: Optional[asyncpg.Pool] = None
        self._readonly_pool: Optional[asyncpg.Pool] = None
        self._is_connected = False

        logger.info(f"PostgresManager initialized (pool: {min_connections}-{max_connections})")

    async def connect(self):
        """Create connection pool"""
        if self._pool:
            logger.warning("PostgreSQL pool already exists")
            return

        try:
            logger.info("Creating PostgreSQL connection pool...")
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_connections,
                max_size=self.max_connections,
                command_timeout=60,
                server_settings={
                    'application_name': 'copa_baggage_platform',
                    'jit': 'off'  # Disable JIT for consistent performance
                }
            )

            # Test connection
            async with self._pool.acquire() as conn:
                await conn.execute("SELECT 1")

            self._is_connected = True
            logger.success(f"✅ PostgreSQL connected (pool size: {self.min_connections}-{self.max_connections})")

            # Connect to readonly replica if configured
            if self.readonly_url:
                await self._connect_readonly()

        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            raise

    async def _connect_readonly(self):
        """Connect to readonly replica for analytics queries"""
        try:
            logger.info("Creating readonly replica pool...")
            self._readonly_pool = await asyncpg.create_pool(
                self.readonly_url,
                min_size=1,
                max_size=5,
                command_timeout=120,  # Longer timeout for analytics
                server_settings={
                    'application_name': 'copa_baggage_analytics',
                    'default_transaction_read_only': 'on'
                }
            )
            logger.success("✅ Readonly replica connected")
        except Exception as e:
            logger.warning(f"⚠️ Readonly replica connection failed: {e}")
            # Not critical, continue without readonly replica

    async def disconnect(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("PostgreSQL pool closed")
            self._is_connected = False

        if self._readonly_pool:
            await self._readonly_pool.close()
            logger.info("Readonly pool closed")

    @asynccontextmanager
    async def acquire(self, readonly: bool = False):
        """
        Acquire database connection from pool

        Args:
            readonly: If True, use readonly replica (if available)

        Usage:
            async with db.acquire() as conn:
                await conn.execute("INSERT ...")
        """
        pool = self._readonly_pool if (readonly and self._readonly_pool) else self._pool

        if not pool:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with pool.acquire() as connection:
            yield connection

    async def execute(
        self,
        query: str,
        *args,
        readonly: bool = False,
        log_slow_queries: bool = True,
        slow_threshold: float = 1.0
    ):
        """
        Execute a query (INSERT, UPDATE, DELETE)

        Args:
            query: SQL query
            *args: Query parameters
            readonly: Use readonly replica
            log_slow_queries: Log queries exceeding threshold
            slow_threshold: Slow query threshold in seconds

        Returns:
            Query result
        """
        start = time.time()

        async with self.acquire(readonly=readonly) as conn:
            result = await conn.execute(query, *args)

        elapsed = time.time() - start

        if log_slow_queries and elapsed > slow_threshold:
            logger.warning(f"Slow query ({elapsed:.2f}s): {query[:100]}...")

        return result

    async def fetch(
        self,
        query: str,
        *args,
        readonly: bool = False,
        log_slow_queries: bool = True,
        slow_threshold: float = 1.0
    ) -> List[asyncpg.Record]:
        """
        Fetch multiple rows

        Args:
            query: SQL query
            *args: Query parameters
            readonly: Use readonly replica
            log_slow_queries: Log queries exceeding threshold
            slow_threshold: Slow query threshold in seconds

        Returns:
            List of records
        """
        start = time.time()

        async with self.acquire(readonly=readonly) as conn:
            results = await conn.fetch(query, *args)

        elapsed = time.time() - start

        if log_slow_queries and elapsed > slow_threshold:
            logger.warning(f"Slow query ({elapsed:.2f}s): {query[:100]}...")

        return results

    async def fetchrow(
        self,
        query: str,
        *args,
        readonly: bool = False
    ) -> Optional[asyncpg.Record]:
        """
        Fetch single row

        Args:
            query: SQL query
            *args: Query parameters
            readonly: Use readonly replica

        Returns:
            Single record or None
        """
        async with self.acquire(readonly=readonly) as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(
        self,
        query: str,
        *args,
        readonly: bool = False
    ):
        """
        Fetch single value

        Args:
            query: SQL query
            *args: Query parameters
            readonly: Use readonly replica

        Returns:
            Single value
        """
        async with self.acquire(readonly=readonly) as conn:
            return await conn.fetchval(query, *args)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check database health

        Returns:
            Health status dictionary
        """
        if not self._pool:
            return {
                "status": "disconnected",
                "healthy": False,
                "error": "No connection pool"
            }

        try:
            start = time.time()

            async with self.acquire() as conn:
                # Test query
                result = await conn.fetchval("SELECT 1")

                # Get pool stats
                pool_size = self._pool.get_size()
                pool_free = self._pool.get_idle_size()
                pool_used = pool_size - pool_free

            latency_ms = (time.time() - start) * 1000

            return {
                "status": "healthy",
                "healthy": True,
                "latency_ms": round(latency_ms, 2),
                "pool": {
                    "size": pool_size,
                    "used": pool_used,
                    "idle": pool_free,
                    "max": self.max_connections
                }
            }

        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e)
            }

    async def get_pool_stats(self) -> Dict[str, int]:
        """Get connection pool statistics"""
        if not self._pool:
            return {"size": 0, "idle": 0, "used": 0}

        pool_size = self._pool.get_size()
        pool_idle = self._pool.get_idle_size()

        return {
            "size": pool_size,
            "idle": pool_idle,
            "used": pool_size - pool_idle,
            "max": self.max_connections
        }

    @property
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._is_connected and self._pool is not None
