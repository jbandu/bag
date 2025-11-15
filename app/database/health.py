"""
Database Health Checker

Provides unified health check system for all database connections:
- PostgreSQL (Neon)
- Neo4j (Aura)
- Redis (Upstash/Railway)

Features:
- Parallel health checks for fast response
- Latency tracking
- Connection pool monitoring
- Graceful degradation
"""
from typing import Dict, Any, List
from loguru import logger
import asyncio
import time

from app.database.postgres import PostgresManager
from app.database.neo4j_manager import Neo4jManager
from app.database.redis_manager import RedisManager


class DatabaseHealthChecker:
    """
    Unified health checker for all database connections

    Features:
    - Parallel health checks (all databases checked simultaneously)
    - Latency tracking for each service
    - Connection pool statistics
    - Overall system health determination
    """

    def __init__(
        self,
        postgres: PostgresManager,
        neo4j: Neo4jManager,
        redis: RedisManager
    ):
        """
        Initialize health checker

        Args:
            postgres: PostgreSQL manager instance
            neo4j: Neo4j manager instance
            redis: Redis manager instance
        """
        self.postgres = postgres
        self.neo4j = neo4j
        self.redis = redis

    async def check_all(self) -> Dict[str, Any]:
        """
        Check health of all database services in parallel

        Returns:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "healthy": bool,
                "timestamp": str,
                "services": {
                    "postgres": {...},
                    "neo4j": {...},
                    "redis": {...}
                },
                "summary": {
                    "total_services": int,
                    "healthy_services": int,
                    "degraded_services": int,
                    "unhealthy_services": int
                }
            }
        """
        start_time = time.time()

        # Run all health checks in parallel for speed
        postgres_check, neo4j_check, redis_check = await asyncio.gather(
            self._check_postgres(),
            self._check_neo4j(),
            self._check_redis(),
            return_exceptions=True
        )

        # Handle exceptions
        if isinstance(postgres_check, Exception):
            postgres_check = {
                "status": "unhealthy",
                "healthy": False,
                "error": str(postgres_check)
            }

        if isinstance(neo4j_check, Exception):
            neo4j_check = {
                "status": "unhealthy",
                "healthy": False,
                "error": str(neo4j_check)
            }

        if isinstance(redis_check, Exception):
            redis_check = {
                "status": "unhealthy",
                "healthy": False,
                "error": str(redis_check)
            }

        # Count service statuses
        services = {
            "postgres": postgres_check,
            "neo4j": neo4j_check,
            "redis": redis_check
        }

        healthy_count = sum(1 for s in services.values() if s.get("healthy", False))
        total_count = len(services)

        # Determine overall status
        if healthy_count == total_count:
            overall_status = "healthy"
            overall_healthy = True
        elif healthy_count >= 2:  # At least 2/3 services healthy
            overall_status = "degraded"
            overall_healthy = True
        else:
            overall_status = "unhealthy"
            overall_healthy = False

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "status": overall_status,
            "healthy": overall_healthy,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "check_duration_ms": round(elapsed_ms, 2),
            "services": services,
            "summary": {
                "total_services": total_count,
                "healthy_services": healthy_count,
                "degraded_services": 0,  # We don't have degraded state per service
                "unhealthy_services": total_count - healthy_count
            }
        }

    async def _check_postgres(self) -> Dict[str, Any]:
        """Check PostgreSQL health"""
        try:
            return await self.postgres.health_check()
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e)
            }

    async def _check_neo4j(self) -> Dict[str, Any]:
        """Check Neo4j health"""
        try:
            return await self.neo4j.health_check()
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e)
            }

    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            return await self.redis.health_check()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e)
            }

    async def check_postgres_only(self) -> Dict[str, Any]:
        """
        Check only PostgreSQL health

        Returns:
            Health status dictionary
        """
        return await self._check_postgres()

    async def check_neo4j_only(self) -> Dict[str, Any]:
        """
        Check only Neo4j health

        Returns:
            Health status dictionary
        """
        return await self._check_neo4j()

    async def check_redis_only(self) -> Dict[str, Any]:
        """
        Check only Redis health

        Returns:
            Health status dictionary
        """
        return await self._check_redis()

    async def is_ready(self) -> bool:
        """
        Kubernetes readiness probe

        Returns True if core services (PostgreSQL + Neo4j) are healthy.
        Redis is not required for readiness.

        Returns:
            True if ready to serve traffic
        """
        try:
            postgres_check, neo4j_check = await asyncio.gather(
                self._check_postgres(),
                self._check_neo4j(),
                return_exceptions=True
            )

            postgres_healthy = not isinstance(postgres_check, Exception) and postgres_check.get("healthy", False)
            neo4j_healthy = not isinstance(neo4j_check, Exception) and neo4j_check.get("healthy", False)

            return postgres_healthy and neo4j_healthy

        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return False

    async def is_alive(self) -> bool:
        """
        Kubernetes liveness probe

        Returns True if at least PostgreSQL is responsive.
        This is a minimal check to determine if the application should be restarted.

        Returns:
            True if application is alive
        """
        try:
            postgres_check = await self._check_postgres()
            return postgres_check.get("healthy", False)
        except Exception as e:
            logger.error(f"Liveness check failed: {e}")
            return False
