"""
Orchestrator Façade

Single entry point for all baggage event processing.
Provides unified interface for FastAPI, Streamlit, and other clients.

Responsibilities:
1. Input normalization (all formats → canonical BagEvent)
2. Workflow routing (event → appropriate agent/workflow)
3. Error handling and recovery
4. Response standardization

Design pattern: Façade + Singleton
"""
from typing import Union, Dict, Any, Optional
from loguru import logger
from datetime import datetime
import asyncio

from app.parsers import (
    ScanEventParser,
    TypeBParser,
    BagEvent,
    ParseResult,
    EventType
)
from config import config


class OrchestratorService:
    """
    Orchestrator service façade

    Single entry point for all baggage event processing.
    Singleton pattern - one instance per application.
    """

    def __init__(self):
        """Initialize orchestrator with parsers and config"""
        self.config = config
        self.parsers = {
            'scan': ScanEventParser(),
            'type_b': TypeBParser(),
        }

        # These will be initialized when agents are ready
        self._langgraph_available = False
        self._orchestrator_graph = None

        logger.info("OrchestratorService initialized")
        logger.info(f"Environment: {self.config.environment.value}")
        logger.info(f"AI Agents enabled: {self.config.enable_ai_agents}")
        logger.info(f"Using mocks: {self.config.use_mocks}")

    async def initialize(self):
        """
        Initialize orchestrator async components

        Loads AI agents and LangGraph workflows if available.
        Gracefully degrades if not available.
        """
        logger.info("Initializing orchestrator components...")

        # Try to load LangGraph orchestrator if available
        if self.config.enable_ai_agents and self.config.has_anthropic_key:
            try:
                # Import lazily to avoid crashes if not available
                from orchestrator.baggage_orchestrator import orchestrator
                self._orchestrator_graph = orchestrator
                self._langgraph_available = True
                logger.info("✅ LangGraph orchestrator loaded")
            except ImportError as e:
                logger.warning(f"⚠️ LangGraph orchestrator not available: {e}")
                logger.warning("Continuing in degraded mode (parsing only)")
                self._langgraph_available = False
            except Exception as e:
                logger.error(f"❌ Error loading LangGraph orchestrator: {e}")
                self._langgraph_available = False
        else:
            logger.info("AI agents disabled or API key missing - running in parse-only mode")

        logger.info("Orchestrator initialization complete")

    async def process_event(
        self,
        input_data: Union[str, Dict[str, Any]],
        event_type_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process baggage event (unified entry point)

        Steps:
        1. Normalize input → canonical BagEvent
        2. Route to appropriate workflow
        3. Execute processing
        4. Return standardized response

        Args:
            input_data: Raw input (string, JSON dict, XML, etc.)
            event_type_hint: Optional hint about input type ('scan', 'type_b', etc.)

        Returns:
            Standardized response dict with result and metadata
        """
        start_time = datetime.utcnow()
        request_id = self._generate_request_id()

        logger.info(f"[{request_id}] Processing event (type_hint: {event_type_hint})")

        try:
            # Step 1: Normalize input to canonical BagEvent
            parse_result = await self._normalize_input(input_data, event_type_hint)

            if not parse_result.is_valid():
                return self._create_error_response(
                    request_id=request_id,
                    errors=parse_result.errors,
                    status_code=400,
                    message="Input parsing failed"
                )

            event = parse_result.event
            logger.info(f"[{request_id}] ✅ Parsed event for bag {event.bag.bag_tag}")

            # Step 2: Route and execute workflow
            result = await self._execute_workflow(event, request_id)

            # Step 3: Return standardized response
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            return self._create_success_response(
                request_id=request_id,
                event=event,
                result=result,
                elapsed_ms=elapsed_ms
            )

        except Exception as e:
            logger.error(f"[{request_id}] ❌ Error processing event: {e}", exc_info=True)
            return self._create_error_response(
                request_id=request_id,
                errors=[str(e)],
                status_code=500,
                message="Internal processing error"
            )

    async def process_text(self, text: str) -> Dict[str, Any]:
        """
        Process raw text input (convenience method for Streamlit)

        Auto-detects input type and processes accordingly.

        Args:
            text: Raw text (Type B message, scan string, etc.)

        Returns:
            Processing result
        """
        # Auto-detect type
        text_upper = text.strip().upper()

        if text_upper.startswith(('BTM', 'BSM', 'BPM', 'BNS', 'BUM')):
            event_type_hint = 'type_b'
        else:
            event_type_hint = 'scan'

        return await self.process_event(text, event_type_hint=event_type_hint)

    async def process_scan(self, scan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process scan event (convenience method for FastAPI)

        Args:
            scan_data: Scan event dict

        Returns:
            Processing result
        """
        return await self.process_event(scan_data, event_type_hint='scan')

    async def process_type_b(self, message: str) -> Dict[str, Any]:
        """
        Process Type B message (convenience method)

        Args:
            message: Type B message text

        Returns:
            Processing result
        """
        return await self.process_event(message, event_type_hint='type_b')

    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================

    async def _normalize_input(
        self,
        input_data: Union[str, Dict[str, Any]],
        event_type_hint: Optional[str]
    ) -> ParseResult:
        """
        Normalize input to canonical BagEvent

        Args:
            input_data: Raw input
            event_type_hint: Hint about input type

        Returns:
            ParseResult with BagEvent or errors
        """
        # Select appropriate parser
        if event_type_hint == 'type_b':
            parser = self.parsers['type_b']
        else:
            # Default to scan parser
            parser = self.parsers['scan']

        # Parse
        parse_result = parser.parse(input_data)

        return parse_result

    async def _execute_workflow(
        self,
        event: BagEvent,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Route event to appropriate workflow and execute

        Args:
            event: Canonical BagEvent
            request_id: Request tracking ID

        Returns:
            Workflow result
        """
        # If LangGraph available, use it
        if self._langgraph_available and self._orchestrator_graph:
            logger.info(f"[{request_id}] Routing to LangGraph workflow")
            try:
                # Convert event to format expected by LangGraph
                result = await self._orchestrator_graph.process_baggage_event(
                    event.raw_message or event.bag.bag_tag
                )
                return result
            except Exception as e:
                logger.error(f"[{request_id}] LangGraph processing failed: {e}")
                # Fall through to mock processing

        # Fallback: Mock processing (when agents not available)
        logger.info(f"[{request_id}] Using mock processing (agents not available)")
        return await self._mock_processing(event)

    async def _mock_processing(self, event: BagEvent) -> Dict[str, Any]:
        """
        Mock processing for development/testing

        Args:
            event: BagEvent to process

        Returns:
            Mock result
        """
        return {
            "status": "processed",
            "bag_tag": event.bag.bag_tag,
            "event_type": event.event_type.value,
            "timestamp": event.event_timestamp.isoformat(),
            "flight": event.flight.flight_number if event.flight else None,
            "location": event.location.station_code if event.location else None,
            "message": "Event processed (mock mode - AI agents not enabled)",
            "mock": True
        }

    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return f"req_{uuid.uuid4().hex[:12]}"

    def _create_success_response(
        self,
        request_id: str,
        event: BagEvent,
        result: Dict[str, Any],
        elapsed_ms: float
    ) -> Dict[str, Any]:
        """
        Create standardized success response

        Args:
            request_id: Request ID
            event: Processed event
            result: Processing result
            elapsed_ms: Processing time

        Returns:
            Standardized response dict
        """
        return {
            "success": True,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed_ms": round(elapsed_ms, 2),
            "event": {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "bag_tag": event.bag.bag_tag,
                "flight": event.flight.flight_number if event.flight else None,
                "location": event.location.station_code if event.location else None
            },
            "result": result
        }

    def _create_error_response(
        self,
        request_id: str,
        errors: list,
        status_code: int = 500,
        message: str = "Processing failed"
    ) -> Dict[str, Any]:
        """
        Create standardized error response

        Args:
            request_id: Request ID
            errors: List of error messages
            status_code: HTTP-like status code
            message: Error message

        Returns:
            Standardized error response
        """
        return {
            "success": False,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": status_code,
            "message": message,
            "errors": errors
        }


# =========================================================================
# SINGLETON INSTANCE
# =========================================================================

# Global orchestrator instance (lazy initialization)
_orchestrator_instance: Optional[OrchestratorService] = None


def get_orchestrator() -> OrchestratorService:
    """
    Get orchestrator singleton instance

    Lazy initialization - creates instance on first call.

    Returns:
        OrchestratorService singleton
    """
    global _orchestrator_instance

    if _orchestrator_instance is None:
        _orchestrator_instance = OrchestratorService()
        logger.info("Created new OrchestratorService singleton")

    return _orchestrator_instance


async def initialize_orchestrator() -> OrchestratorService:
    """
    Initialize orchestrator (call during app startup)

    Returns:
        Initialized OrchestratorService
    """
    orchestrator = get_orchestrator()
    await orchestrator.initialize()
    return orchestrator
