"""
FastAPI Dependencies

Provides dependency injection for FastAPI routes.

Dependencies:
- get_orchestrator: Inject OrchestratorService
- get_config: Inject application config
- (Future) get_database: Inject database connections
- (Future) get_external_services: Inject external service managers
"""
from typing import Generator
from fastapi import Depends

from app.orchestrator import get_orchestrator as get_orchestrator_singleton, OrchestratorService
from config import config as app_config, BaseConfig


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


# Export for easy importing
__all__ = [
    "get_orchestrator",
    "get_config"
]
