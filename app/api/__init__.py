"""
API Routes Module

Contains FastAPI routers for different API sections:
- Health check endpoints
- (Future) Baggage tracking endpoints
- (Future) Analytics endpoints
"""

from app.api.health import (
    router as health_router,
    init_health_checker,
    init_external_services
)

__all__ = [
    "health_router",
    "init_health_checker",
    "init_external_services"
]
