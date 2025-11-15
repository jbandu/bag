"""
Correlation ID Middleware for FastAPI
Generates and propagates trace IDs through all requests
"""

import uuid
import time
from typing import Callable
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..logging.structured_logger import get_logger
from ..logging.log_context import trace_id_var


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and propagate correlation IDs (trace IDs)

    Features:
    - Generates unique trace_id for each request
    - Accepts X-Trace-ID header if provided
    - Adds trace_id to response headers
    - Sets trace_id in context for logging
    - Logs request/response with trace_id
    """

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Trace-ID"
    ):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add correlation ID"""

        # Get or generate trace ID
        trace_id = request.headers.get(self.header_name)
        if not trace_id:
            trace_id = self.generate_trace_id()

        # Set trace ID in context
        token = trace_id_var.set(trace_id)

        # Create logger with trace ID
        logger = get_logger(trace_id=trace_id)

        # Log request
        start_time = time.time()
        logger.log_request(
            endpoint=request.url.path,
            method=request.method,
            client_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path}",
                event_type="request_completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Add trace ID to response headers
            response.headers[self.header_name] = trace_id

            return response

        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(
                f"Request failed: {request.method} {request.url.path}",
                event_type="request_failed",
                duration_ms=duration_ms,
                error=str(e),
            )
            raise

        finally:
            # Reset trace ID context
            trace_id_var.reset(token)

    @staticmethod
    def generate_trace_id() -> str:
        """Generate unique trace ID"""
        return str(uuid.uuid4())


def setup_correlation_id_middleware(app: FastAPI):
    """
    Setup correlation ID middleware on FastAPI app

    Usage:
        from fastapi import FastAPI
        from src.middleware.correlation_id import setup_correlation_id_middleware

        app = FastAPI()
        setup_correlation_id_middleware(app)
    """
    app.add_middleware(CorrelationIDMiddleware)


# Helper function to get current trace ID
def get_trace_id_from_request(request: Request) -> str:
    """
    Get trace ID from request headers or context

    Usage:
        @app.get("/endpoint")
        async def endpoint(request: Request):
            trace_id = get_trace_id_from_request(request)
    """
    # Try to get from context first
    trace_id = trace_id_var.get()
    if trace_id:
        return trace_id

    # Fallback to request headers
    trace_id = request.headers.get("X-Trace-ID")
    if trace_id:
        return trace_id

    # Generate new one as last resort
    return str(uuid.uuid4())
