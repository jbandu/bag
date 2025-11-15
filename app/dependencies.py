"""
FastAPI Dependencies

Provides dependency injection for FastAPI routes.

Dependencies:
- get_orchestrator: Inject OrchestratorService
- get_config: Inject application config
- get_baggage_repo: Inject BaggageRepository
- get_graph_repo: Inject GraphRepository
- get_metrics_repo: Inject MetricsRepository
- get_postgres: Inject PostgreSQL manager
- get_neo4j: Inject Neo4j manager
- get_redis: Inject Redis manager
"""
from typing import Optional
from fastapi import Depends

from app.orchestrator import get_orchestrator as get_orchestrator_singleton, OrchestratorService
from config import config as app_config, BaseConfig
from app.database.factory import (
    get_postgres,
    get_neo4j,
    get_redis,
    get_health_checker
)
from app.database.postgres import PostgresManager
from app.database.neo4j_manager import Neo4jManager
from app.database.redis_manager import RedisManager
from app.database.health import DatabaseHealthChecker
from app.repositories import BaggageRepository, GraphRepository, MetricsRepository


# ============================================================================
# ORCHESTRATOR & CONFIG
# ============================================================================

def get_orchestrator() -> OrchestratorService:
    """
    Get orchestrator service dependency

    Usage in FastAPI routes:
        @app.post("/events")
        async def process_event(
            data: dict,
            orchestrator: OrchestratorService = Depends(get_orchestrator)
        ):
            result = await orchestrator.process_event(data)
            return result

    Returns:
        OrchestratorService singleton instance
    """
    return get_orchestrator_singleton()


def get_config() -> BaseConfig:
    """
    Get application config dependency

    Usage in FastAPI routes:
        @app.get("/info")
        async def get_info(config: BaseConfig = Depends(get_config)):
            return {"environment": config.environment.value}

    Returns:
        Application config
    """
    return app_config


# ============================================================================
# DATABASE MANAGERS
# ============================================================================

def get_postgres_dependency() -> Optional[PostgresManager]:
    """
    Get PostgreSQL manager dependency

    Usage in FastAPI routes:
        @app.get("/data")
        async def get_data(postgres: PostgresManager = Depends(get_postgres_dependency)):
            result = await postgres.fetchrow("SELECT * FROM bags WHERE id = $1", 123)
            return result

    Returns:
        PostgresManager instance or None if unavailable
    """
    return get_postgres()


def get_neo4j_dependency() -> Optional[Neo4jManager]:
    """
    Get Neo4j manager dependency

    Returns:
        Neo4jManager instance or None if unavailable
    """
    return get_neo4j()


def get_redis_dependency() -> Optional[RedisManager]:
    """
    Get Redis manager dependency

    Returns:
        RedisManager instance or None if unavailable
    """
    return get_redis()


def get_health_checker_dependency() -> Optional[DatabaseHealthChecker]:
    """
    Get database health checker dependency

    Usage in health check endpoints:
        @app.get("/health")
        async def health_check(
            checker: DatabaseHealthChecker = Depends(get_health_checker_dependency)
        ):
            return await checker.check_all()

    Returns:
        DatabaseHealthChecker instance or None if unavailable
    """
    return get_health_checker()


# ============================================================================
# REPOSITORIES
# ============================================================================

def get_baggage_repo(
    postgres: Optional[PostgresManager] = Depends(get_postgres_dependency)
) -> Optional[BaggageRepository]:
    """
    Get baggage repository dependency

    Usage in FastAPI routes:
        @app.post("/bags")
        async def create_bag(
            bag_data: dict,
            repo: BaggageRepository = Depends(get_baggage_repo)
        ):
            bag_tag = await repo.create_bag(bag_data)
            return {"bag_tag": bag_tag}

    Returns:
        BaggageRepository instance or None if PostgreSQL unavailable
    """
    if postgres is None:
        return None
    return BaggageRepository(postgres)


def get_graph_repo(
    neo4j: Optional[Neo4jManager] = Depends(get_neo4j_dependency)
) -> Optional[GraphRepository]:
    """
    Get graph repository dependency

    Usage in FastAPI routes:
        @app.get("/bags/{bag_tag}/journey")
        async def get_journey(
            bag_tag: str,
            repo: GraphRepository = Depends(get_graph_repo)
        ):
            journey = await repo.get_bag_journey(bag_tag)
            return {"journey": journey}

    Returns:
        GraphRepository instance (gracefully degrades if Neo4j unavailable)
    """
    # GraphRepository handles None neo4j gracefully
    return GraphRepository(neo4j)


def get_metrics_repo(
    redis: Optional[RedisManager] = Depends(get_redis_dependency)
) -> Optional[MetricsRepository]:
    """
    Get metrics repository dependency

    Usage in FastAPI routes:
        @app.get("/metrics")
        async def get_metrics(
            repo: MetricsRepository = Depends(get_metrics_repo)
        ):
            metrics = await repo.get_metrics_summary()
            return metrics

    Returns:
        MetricsRepository instance (gracefully degrades if Redis unavailable)
    """
    # MetricsRepository handles None redis gracefully
    return MetricsRepository(redis)


# Export for easy importing
__all__ = [
    "get_orchestrator",
    "get_config",
    "get_postgres_dependency",
    "get_neo4j_dependency",
    "get_redis_dependency",
    "get_health_checker_dependency",
    "get_baggage_repo",
    "get_graph_repo",
    "get_metrics_repo"
]
