"""
Orchestrator Module

Provides unified orchestration façade for baggage event processing.

Main components:
- OrchestratorService: Singleton façade for event processing
- get_orchestrator(): Get singleton instance
- initialize_orchestrator(): Initialize on app startup

Usage (FastAPI):
    from app.orchestrator import initialize_orchestrator, get_orchestrator

    @app.on_event("startup")
    async def startup():
        await initialize_orchestrator()

    @app.post("/events")
    async def process_event(
        data: dict,
        orchestrator: OrchestratorService = Depends(get_orchestrator)
    ):
        result = await orchestrator.process_event(data)
        return result

Usage (Streamlit):
    from app.orchestrator import get_orchestrator

    orchestrator = get_orchestrator()
    result = await orchestrator.process_text(type_b_message)
"""
from app.orchestrator.facade import (
    OrchestratorService,
    get_orchestrator,
    initialize_orchestrator
)

__all__ = [
    "OrchestratorService",
    "get_orchestrator",
    "initialize_orchestrator"
]
