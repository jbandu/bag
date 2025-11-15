"""
Structured Logging with Loguru
Simple, grep-able logging for debugging multi-agent workflows
"""

import os
import sys
import json
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime


# Environment-based configuration
ENV = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = {
    "development": "DEBUG",
    "staging": "INFO",
    "production": "WARNING"
}.get(ENV, "INFO")


def json_serializer(record: Dict[str, Any]) -> str:
    """Serialize log record to JSON for production"""
    subset = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }

    # Add extra context fields
    if record["extra"]:
        subset["context"] = record["extra"]

    # Add exception info if present
    if record["exception"]:
        subset["exception"] = {
            "type": record["exception"].type.__name__ if record["exception"].type else None,
            "value": str(record["exception"].value),
            "traceback": record["exception"].traceback
        }

    return json.dumps(subset)


def colored_formatter(record: Dict[str, Any]) -> str:
    """Colored formatter for development console"""
    # Extract context
    context_parts = []
    extra = record["extra"]

    if "trace_id" in extra:
        context_parts.append(f"<cyan>trace_id={extra['trace_id'][:8]}</cyan>")
    if "bag_tag" in extra:
        context_parts.append(f"<yellow>bag={extra['bag_tag']}</yellow>")
    if "agent_name" in extra:
        context_parts.append(f"<magenta>agent={extra['agent_name']}</magenta>")
    if "event_id" in extra:
        context_parts.append(f"<blue>event={extra['event_id']}</blue>")

    context_str = " ".join(context_parts)
    context_prefix = f"[{context_str}] " if context_str else ""

    # Build format string
    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        f"{context_prefix}"
        "<level>{message}</level>"
    )

    return fmt


def setup_logging():
    """Configure loguru for structured logging"""
    # Remove default handler
    logger.remove()

    # Add handler based on environment
    if ENV == "production":
        # JSON logging for production
        logger.add(
            sys.stdout,
            format=json_serializer,
            level=LOG_LEVEL,
            serialize=False,  # We handle serialization ourselves
        )
    else:
        # Colored console logging for dev/staging
        logger.add(
            sys.stdout,
            format=colored_formatter,
            level=LOG_LEVEL,
            colorize=True,
        )

    # Add file logging (always JSON for parsing)
    log_dir = os.getenv("LOG_DIR", "/tmp/baggage_ai_logs")
    os.makedirs(log_dir, exist_ok=True)

    logger.add(
        f"{log_dir}/baggage_ai.log",
        format=json_serializer,
        level=LOG_LEVEL,
        rotation="100 MB",
        retention="7 days",
        compression="zip",
        serialize=False,
    )

    logger.info(
        f"Logging initialized",
        environment=ENV,
        log_level=LOG_LEVEL
    )


class StructuredLogger:
    """
    Structured logger wrapper for easy context management

    Usage:
        logger = StructuredLogger(trace_id="abc123", bag_tag="CM123456")
        logger.info("Bag checked in", agent_name="ScanProcessor")
        logger.error("Processing failed", error="Timeout", service="WorldTracer")
    """

    def __init__(self, **context):
        """Initialize with base context"""
        self.context = context
        self._logger = logger.bind(**context)

    def bind(self, **kwargs) -> 'StructuredLogger':
        """Create new logger with additional context"""
        new_context = {**self.context, **kwargs}
        return StructuredLogger(**new_context)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._logger.bind(**kwargs).debug(message)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._logger.bind(**kwargs).info(message)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._logger.bind(**kwargs).warning(message)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._logger.bind(**kwargs).error(message)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._logger.bind(**kwargs).critical(message)

    def exception(self, message: str, **kwargs):
        """Log exception with stack trace"""
        self._logger.bind(**kwargs).exception(message)

    def log_request(self, endpoint: str, method: str = "POST", **kwargs):
        """Log incoming request"""
        self.info(
            f"Request received: {method} {endpoint}",
            event_type="request_received",
            endpoint=endpoint,
            method=method,
            **kwargs
        )

    def log_agent_start(self, agent_name: str, input_summary: str, **kwargs):
        """Log agent workflow start"""
        self.info(
            f"Agent workflow started: {agent_name}",
            event_type="agent_start",
            agent_name=agent_name,
            input_summary=input_summary,
            **kwargs
        )

    def log_agent_complete(
        self,
        agent_name: str,
        outcome: str,
        duration_ms: float,
        **kwargs
    ):
        """Log agent workflow completion"""
        self.info(
            f"Agent workflow completed: {agent_name}",
            event_type="agent_complete",
            agent_name=agent_name,
            outcome=outcome,
            duration_ms=duration_ms,
            **kwargs
        )

    def log_db_operation(
        self,
        operation: str,
        query: str,
        latency_ms: float,
        rows_affected: int = 0,
        **kwargs
    ):
        """Log database operation"""
        self.debug(
            f"Database operation: {operation}",
            event_type="db_operation",
            operation=operation,
            query=query[:200] if len(query) > 200 else query,  # Truncate long queries
            latency_ms=latency_ms,
            rows_affected=rows_affected,
            **kwargs
        )

    def log_api_call(
        self,
        service: str,
        endpoint: str,
        status_code: int,
        latency_ms: float,
        **kwargs
    ):
        """Log external API call"""
        self.info(
            f"API call: {service} {endpoint}",
            event_type="api_call",
            service=service,
            endpoint=endpoint,
            status_code=status_code,
            latency_ms=latency_ms,
            **kwargs
        )

    def log_error(
        self,
        error_message: str,
        error_type: str,
        stack_trace: Optional[str] = None,
        **kwargs
    ):
        """Log error with full context"""
        self.error(
            error_message,
            event_type="error",
            error_type=error_type,
            stack_trace=stack_trace,
            **kwargs
        )


# Initialize logging on module import
setup_logging()

# Export a default logger instance
default_logger = StructuredLogger()


# Convenience functions
def get_logger(**context) -> StructuredLogger:
    """Get a logger with context"""
    return StructuredLogger(**context)


def log_request(trace_id: str, endpoint: str, **kwargs):
    """Quick log for incoming requests"""
    logger.bind(trace_id=trace_id, **kwargs).info(
        f"Request received: {endpoint}",
        event_type="request_received",
        endpoint=endpoint
    )


def log_agent_workflow(
    trace_id: str,
    agent_name: str,
    bag_tag: str,
    event: str,
    **kwargs
):
    """Quick log for agent workflows"""
    logger.bind(
        trace_id=trace_id,
        agent_name=agent_name,
        bag_tag=bag_tag,
        **kwargs
    ).info(
        f"Agent {event}: {agent_name}",
        event_type=f"agent_{event}",
    )
