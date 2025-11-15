"""
Health Check API Endpoints

Provides health check endpoints for monitoring and orchestration:
- Overall system health
- Individual service health (database, graph, cache)
- External service health
- Kubernetes probes (readiness, liveness)

All endpoints are public (no authentication required) for monitoring tools.
"""
from fastapi import APIRouter, Response, status
from typing import Dict, Any
from loguru import logger

from app.database.health import DatabaseHealthChecker
from app.external.manager import ExternalServicesManager


# Router for health check endpoints
router = APIRouter(prefix="/health", tags=["Health"])


# Global health checker instances (will be initialized by main app)
_health_checker: DatabaseHealthChecker = None
_external_services: ExternalServicesManager = None


def init_health_checker(health_checker: DatabaseHealthChecker):
    """
    Initialize health checker instance

    Called by main application during startup

    Args:
        health_checker: DatabaseHealthChecker instance
    """
    global _health_checker
    _health_checker = health_checker
    logger.info("Database health checker initialized")


def init_external_services(external_services: ExternalServicesManager):
    """
    Initialize external services manager

    Called by main application during startup

    Args:
        external_services: ExternalServicesManager instance
    """
    global _external_services
    _external_services = external_services
    logger.info("External services manager initialized")


@router.get(
    "",
    summary="Overall System Health",
    description="Check health of all system components (databases, cache, external services)",
    response_model=Dict[str, Any]
)
async def health_check(response: Response):
    """
    Overall system health check

    Checks all services in parallel and returns comprehensive status.
    Used by monitoring tools for alerting.

    Response format:
    {
        "status": "healthy" | "degraded" | "unhealthy",
        "healthy": bool,
        "timestamp": "2024-12-01T10:30:00Z",
        "check_duration_ms": 45.23,
        "services": {
            "postgres": {...},
            "neo4j": {...},
            "redis": {...}
        },
        "summary": {
            "total_services": 3,
            "healthy_services": 3,
            "unhealthy_services": 0
        }
    }
    """
    if not _health_checker:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "healthy": False,
            "error": "Health checker not initialized"
        }

    try:
        health_status = await _health_checker.check_all()

        # Set HTTP status code based on health
        if health_status["status"] == "unhealthy":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health_status["status"] == "degraded":
            response.status_code = status.HTTP_200_OK  # Still serving traffic
        else:
            response.status_code = status.HTTP_200_OK

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "healthy": False,
            "error": str(e)
        }


@router.get(
    "/database",
    summary="PostgreSQL Database Health",
    description="Check PostgreSQL connection and query performance",
    response_model=Dict[str, Any]
)
async def database_health(response: Response):
    """
    PostgreSQL database health check

    Returns:
    {
        "status": "healthy" | "unhealthy",
        "healthy": bool,
        "latency_ms": 12.34,
        "pool": {
            "size": 10,
            "used": 3,
            "idle": 7,
            "max": 20
        }
    }
    """
    if not _health_checker:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "healthy": False,
            "error": "Health checker not initialized"
        }

    try:
        health_status = await _health_checker.check_postgres_only()

        if not health_status.get("healthy", False):
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            response.status_code = status.HTTP_200_OK

        return health_status

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "healthy": False,
            "error": str(e)
        }


@router.get(
    "/graph",
    summary="Neo4j Graph Database Health",
    description="Check Neo4j connection and query performance",
    response_model=Dict[str, Any]
)
async def graph_health(response: Response):
    """
    Neo4j graph database health check

    Returns:
    {
        "status": "healthy" | "unhealthy",
        "healthy": bool,
        "latency_ms": 23.45,
        "version": "5.x.x",
        "database": "neo4j"
    }
    """
    if not _health_checker:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "healthy": False,
            "error": "Health checker not initialized"
        }

    try:
        health_status = await _health_checker.check_neo4j_only()

        if not health_status.get("healthy", False):
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            response.status_code = status.HTTP_200_OK

        return health_status

    except Exception as e:
        logger.error(f"Graph health check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "healthy": False,
            "error": str(e)
        }


@router.get(
    "/cache",
    summary="Redis Cache Health",
    description="Check Redis connection and memory usage",
    response_model=Dict[str, Any]
)
async def cache_health(response: Response):
    """
    Redis cache health check

    Returns:
    {
        "status": "healthy" | "unhealthy",
        "healthy": bool,
        "latency_ms": 5.67,
        "version": "7.x.x",
        "memory_used": "1.2M"
    }
    """
    if not _health_checker:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "healthy": False,
            "error": "Health checker not initialized"
        }

    try:
        health_status = await _health_checker.check_redis_only()

        if not health_status.get("healthy", False):
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            response.status_code = status.HTTP_200_OK

        return health_status

    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "healthy": False,
            "error": str(e)
        }


@router.get(
    "/external",
    summary="External Services Health",
    description="Check health of external integrations (WorldTracer, Twilio, SendGrid)",
    response_model=Dict[str, Any]
)
async def external_services_health(response: Response):
    """
    External services health check

    Checks:
    - WorldTracer API connectivity
    - Twilio SMS service
    - SendGrid email service

    Returns:
    {
        "status": "healthy" | "degraded" | "unhealthy",
        "healthy": bool,
        "services": {
            "worldtracer": {...},
            "twilio": {...},
            "sendgrid": {...}
        },
        "summary": {
            "total_services": 3,
            "healthy_services": 3,
            "mock_services": 0
        }
    }
    """
    if not _external_services:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "healthy": False,
            "error": "External services not initialized",
            "services": {
                "worldtracer": {"status": "unknown", "healthy": False},
                "twilio": {"status": "unknown", "healthy": False},
                "sendgrid": {"status": "unknown", "healthy": False}
            }
        }

    try:
        health_status = await _external_services.health_check_all()

        # Set HTTP status code based on health
        if health_status["status"] == "unhealthy":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health_status["status"] == "degraded":
            response.status_code = status.HTTP_200_OK  # Still operational
        else:
            response.status_code = status.HTTP_200_OK

        return health_status

    except Exception as e:
        logger.error(f"External services health check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "healthy": False,
            "error": str(e)
        }



@router.get(
    "/ready",
    summary="Kubernetes Readiness Probe",
    description="Check if application is ready to serve traffic (PostgreSQL + Neo4j must be healthy)",
    status_code=status.HTTP_200_OK
)
async def readiness_probe(response: Response):
    """
    Kubernetes readiness probe

    Returns 200 if application is ready to serve traffic.
    Returns 503 if application is not ready.

    Checks:
    - PostgreSQL connection
    - Neo4j connection

    Redis is not required for readiness (graceful degradation).
    """
    if not _health_checker:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"ready": False, "reason": "Health checker not initialized"}

    try:
        is_ready = await _health_checker.is_ready()

        if is_ready:
            response.status_code = status.HTTP_200_OK
            return {"ready": True}
        else:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"ready": False, "reason": "Core databases not healthy"}

    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"ready": False, "reason": str(e)}


@router.get(
    "/live",
    summary="Kubernetes Liveness Probe",
    description="Check if application is alive (minimal check - PostgreSQL responsive)",
    status_code=status.HTTP_200_OK
)
async def liveness_probe(response: Response):
    """
    Kubernetes liveness probe

    Returns 200 if application is alive.
    Returns 503 if application should be restarted.

    Minimal check:
    - PostgreSQL responds to queries

    This is a very basic check to avoid unnecessary restarts.
    """
    if not _health_checker:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"alive": False, "reason": "Health checker not initialized"}

    try:
        is_alive = await _health_checker.is_alive()

        if is_alive:
            response.status_code = status.HTTP_200_OK
            return {"alive": True}
        else:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"alive": False, "reason": "Database not responsive"}

    except Exception as e:
        logger.error(f"Liveness probe failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"alive": False, "reason": str(e)}
