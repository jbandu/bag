"""
Database Connection Factory

Provides centralized database connection management with:
- Lazy initialization (connect at app startup, not import time)
- Connection pooling for all services
- Health checks and retry logic
- Graceful degradation when services unavailable
- Singleton pattern to prevent multiple connections

Usage:
    # In app startup
    await initialize_databases()

    # Get database instances
    postgres = get_postgres()
    neo4j = get_neo4j()
    redis = get_redis()
"""
from typing import Optional
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import asyncio

from config import config
from app.database.postgres import PostgresManager
from app.database.neo4j_manager import Neo4jManager
from app.database.redis_manager import RedisManager
from app.database.health import DatabaseHealthChecker


# ============================================================================
# SINGLETON INSTANCES (initialized at startup, not import time)
# ============================================================================

_postgres_instance: Optional[PostgresManager] = None
_neo4j_instance: Optional[Neo4jManager] = None
_redis_instance: Optional[RedisManager] = None
_health_checker_instance: Optional[DatabaseHealthChecker] = None

_initialized = False


# ============================================================================
# RETRY DECORATORS
# ============================================================================

def retry_on_connection_error():
    """
    Retry decorator for connection failures

    - Retry up to 3 times
    - Exponential backoff: 2s, 4s, 8s
    - Only retry on connection errors, not logic errors
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True
    )


# ============================================================================
# CONNECTION INITIALIZATION
# ============================================================================

@retry_on_connection_error()
async def _create_postgres_connection() -> Optional[PostgresManager]:
    """
    Create PostgreSQL connection with retry logic

    Returns:
        PostgresManager instance or None if connection fails
    """
    if not config.neon_database_url:
        logger.warning("⚠️ PostgreSQL: No database URL configured (skipping)")
        return None

    try:
        logger.info("PostgreSQL: Creating connection pool...")

        manager = PostgresManager(
            database_url=config.neon_database_url,
            min_connections=2,
            max_connections=20
        )

        await manager.connect()

        logger.success("✅ PostgreSQL: Connected successfully")
        return manager

    except Exception as e:
        logger.error(f"❌ PostgreSQL: Connection failed: {e}")

        # In production, PostgreSQL is critical - re-raise
        if config.is_production:
            raise

        # In dev/staging, allow graceful degradation
        logger.warning("⚠️ PostgreSQL: Continuing without PostgreSQL (degraded mode)")
        return None


@retry_on_connection_error()
async def _create_neo4j_connection() -> Optional[Neo4jManager]:
    """
    Create Neo4j connection with retry logic

    Returns:
        Neo4jManager instance or None if connection fails
    """
    if not config.neo4j_uri or not config.neo4j_password:
        logger.warning("⚠️ Neo4j: No connection credentials configured (skipping)")
        return None

    try:
        logger.info("Neo4j: Creating driver...")

        manager = Neo4jManager(
            uri=config.neo4j_uri,
            user=config.neo4j_user,
            password=config.neo4j_password,
            database=config.neo4j_database
        )

        await manager.connect()

        logger.success("✅ Neo4j: Connected successfully")
        return manager

    except Exception as e:
        logger.error(f"❌ Neo4j: Connection failed: {e}")

        # Neo4j is optional - graph features degrade gracefully
        logger.warning("⚠️ Neo4j: Continuing without graph database (digital twin disabled)")
        return None


@retry_on_connection_error()
async def _create_redis_connection() -> Optional[RedisManager]:
    """
    Create Redis connection with retry logic

    Returns:
        RedisManager instance or None if connection fails
    """
    if not config.redis_url:
        logger.warning("⚠️ Redis: No Redis URL configured (skipping)")
        return None

    try:
        logger.info("Redis: Creating connection...")

        manager = RedisManager(
            redis_url=config.redis_url,
            decode_responses=True
        )

        await manager.connect()

        logger.success("✅ Redis: Connected successfully")
        return manager

    except Exception as e:
        logger.error(f"❌ Redis: Connection failed: {e}")

        # Redis is optional - caching will be skipped
        logger.warning("⚠️ Redis: Continuing without cache (in-memory fallback)")
        return None


async def initialize_databases() -> dict:
    """
    Initialize all database connections at application startup

    This should be called in FastAPI startup event, NOT at import time.
    Connections are created in parallel for speed.

    Returns:
        dict: Status of each database connection

    Example:
        @app.on_event("startup")
        async def startup():
            await initialize_databases()
    """
    global _postgres_instance, _neo4j_instance, _redis_instance
    global _health_checker_instance, _initialized

    if _initialized:
        logger.warning("Databases already initialized")
        return {
            "postgres": _postgres_instance is not None,
            "neo4j": _neo4j_instance is not None,
            "redis": _redis_instance is not None
        }

    logger.info("=" * 60)
    logger.info("Initializing database connections...")
    logger.info("=" * 60)

    # Connect to all databases in parallel for speed
    postgres_task = _create_postgres_connection()
    neo4j_task = _create_neo4j_connection()
    redis_task = _create_redis_connection()

    results = await asyncio.gather(
        postgres_task,
        neo4j_task,
        redis_task,
        return_exceptions=True
    )

    # Unpack results
    postgres_result, neo4j_result, redis_result = results

    # Store successful connections
    if not isinstance(postgres_result, Exception):
        _postgres_instance = postgres_result
    else:
        logger.error(f"PostgreSQL initialization failed: {postgres_result}")

    if not isinstance(neo4j_result, Exception):
        _neo4j_instance = neo4j_result
    else:
        logger.error(f"Neo4j initialization failed: {neo4j_result}")

    if not isinstance(redis_result, Exception):
        _redis_instance = redis_result
    else:
        logger.error(f"Redis initialization failed: {redis_result}")

    # Create health checker if we have at least one connection
    if _postgres_instance or _neo4j_instance or _redis_instance:
        _health_checker_instance = DatabaseHealthChecker(
            postgres=_postgres_instance or PostgresManager("", 0, 0),  # Dummy if None
            neo4j=_neo4j_instance or Neo4jManager("", "", ""),
            redis=_redis_instance or RedisManager("")
        )

    _initialized = True

    # Print summary
    logger.info("=" * 60)
    logger.info("Database initialization complete:")
    logger.info(f"  PostgreSQL: {'✅ Connected' if _postgres_instance else '❌ Not available'}")
    logger.info(f"  Neo4j:      {'✅ Connected' if _neo4j_instance else '❌ Not available'}")
    logger.info(f"  Redis:      {'✅ Connected' if _redis_instance else '❌ Not available'}")
    logger.info("=" * 60)

    # Warn if critical services down in production
    if config.is_production and not _postgres_instance:
        logger.critical("🚨 CRITICAL: PostgreSQL unavailable in production!")

    return {
        "postgres": _postgres_instance is not None,
        "neo4j": _neo4j_instance is not None,
        "redis": _redis_instance is not None
    }


async def shutdown_databases():
    """
    Gracefully close all database connections

    Should be called in FastAPI shutdown event.

    Example:
        @app.on_event("shutdown")
        async def shutdown():
            await shutdown_databases()
    """
    global _postgres_instance, _neo4j_instance, _redis_instance
    global _health_checker_instance, _initialized

    logger.info("Shutting down database connections...")

    # Close all connections in parallel
    tasks = []

    if _postgres_instance:
        tasks.append(_postgres_instance.disconnect())

    if _neo4j_instance:
        tasks.append(_neo4j_instance.disconnect())

    if _redis_instance:
        tasks.append(_redis_instance.disconnect())

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    # Clear instances
    _postgres_instance = None
    _neo4j_instance = None
    _redis_instance = None
    _health_checker_instance = None
    _initialized = False

    logger.success("✅ All database connections closed")


# ============================================================================
# ACCESSOR FUNCTIONS (for dependency injection)
# ============================================================================

def get_postgres() -> Optional[PostgresManager]:
    """
    Get PostgreSQL manager instance

    Returns:
        PostgresManager or None if not connected

    Raises:
        RuntimeError: If called before initialize_databases()
    """
    if not _initialized:
        raise RuntimeError(
            "Databases not initialized. Call initialize_databases() in app startup."
        )

    return _postgres_instance


def get_neo4j() -> Optional[Neo4jManager]:
    """
    Get Neo4j manager instance

    Returns:
        Neo4jManager or None if not connected

    Raises:
        RuntimeError: If called before initialize_databases()
    """
    if not _initialized:
        raise RuntimeError(
            "Databases not initialized. Call initialize_databases() in app startup."
        )

    return _neo4j_instance


def get_redis() -> Optional[RedisManager]:
    """
    Get Redis manager instance

    Returns:
        RedisManager or None if not connected

    Raises:
        RuntimeError: If called before initialize_databases()
    """
    if not _initialized:
        raise RuntimeError(
            "Databases not initialized. Call initialize_databases() in app startup."
        )

    return _redis_instance


def get_health_checker() -> Optional[DatabaseHealthChecker]:
    """
    Get database health checker instance

    Returns:
        DatabaseHealthChecker or None if databases not initialized
    """
    return _health_checker_instance


def is_initialized() -> bool:
    """
    Check if databases have been initialized

    Returns:
        True if initialize_databases() has been called
    """
    return _initialized


def get_connection_status() -> dict:
    """
    Get current connection status for all databases

    Returns:
        dict with boolean status for each database
    """
    return {
        "initialized": _initialized,
        "postgres": _postgres_instance is not None and _postgres_instance.is_connected,
        "neo4j": _neo4j_instance is not None and _neo4j_instance.is_connected,
        "redis": _redis_instance is not None and _redis_instance.is_connected
    }
