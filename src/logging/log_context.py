"""
Log Context Manager
Context managers for adding structured context to logs
"""

import time
from typing import Optional, Dict, Any
from contextvars import ContextVar
from .structured_logger import StructuredLogger, get_logger


# Context variables for request-scoped data
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
bag_tag_var: ContextVar[Optional[str]] = ContextVar('bag_tag', default=None)
agent_name_var: ContextVar[Optional[str]] = ContextVar('agent_name', default=None)


class LogContext:
    """
    Context manager for adding structured context to logs

    Usage:
        with LogContext(trace_id="abc123", bag_tag="CM123456"):
            logger.info("Processing bag")  # Will include trace_id and bag_tag
    """

    def __init__(self, **context):
        self.context = context
        self.tokens = {}

    def __enter__(self):
        # Set context variables
        if 'trace_id' in self.context:
            self.tokens['trace_id'] = trace_id_var.set(self.context['trace_id'])
        if 'bag_tag' in self.context:
            self.tokens['bag_tag'] = bag_tag_var.set(self.context['bag_tag'])
        if 'agent_name' in self.context:
            self.tokens['agent_name'] = agent_name_var.set(self.context['agent_name'])

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Reset context variables
        for var_name, token in self.tokens.items():
            if var_name == 'trace_id':
                trace_id_var.reset(token)
            elif var_name == 'bag_tag':
                bag_tag_var.reset(token)
            elif var_name == 'agent_name':
                agent_name_var.reset(token)


class AgentWorkflowLogger:
    """
    Context manager for logging complete agent workflow

    Usage:
        with AgentWorkflowLogger(
            trace_id="abc123",
            agent_name="ScanProcessor",
            bag_tag="CM123456",
            input_data={"scan_type": "arrival"}
        ) as workflow_logger:
            # Do work
            workflow_logger.log("Processing scan")
            # Automatically logs completion with duration
    """

    def __init__(
        self,
        trace_id: str,
        agent_name: str,
        bag_tag: str,
        input_data: Optional[Dict[str, Any]] = None,
        **extra_context
    ):
        self.trace_id = trace_id
        self.agent_name = agent_name
        self.bag_tag = bag_tag
        self.input_data = input_data or {}
        self.extra_context = extra_context

        self.logger = get_logger(
            trace_id=trace_id,
            agent_name=agent_name,
            bag_tag=bag_tag,
            **extra_context
        )

        self.start_time = None
        self.outcome = "unknown"
        self.error = None

    def __enter__(self):
        """Log agent workflow start"""
        self.start_time = time.time()

        # Create input summary
        input_summary = ", ".join(
            f"{k}={v}" for k, v in list(self.input_data.items())[:3]
        )

        self.logger.log_agent_start(
            agent_name=self.agent_name,
            input_summary=input_summary,
            input_data=self.input_data
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log agent workflow completion"""
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type:
            # Workflow failed
            self.outcome = "failed"
            self.error = str(exc_val)
            self.logger.log_agent_complete(
                agent_name=self.agent_name,
                outcome="failed",
                duration_ms=duration_ms,
                error=self.error,
                error_type=exc_type.__name__ if exc_type else None
            )
            self.logger.exception(
                f"Agent workflow failed: {self.agent_name}",
                error=self.error
            )
        else:
            # Workflow succeeded
            self.outcome = "success"
            self.logger.log_agent_complete(
                agent_name=self.agent_name,
                outcome="success",
                duration_ms=duration_ms
            )

        # Don't suppress exceptions
        return False

    def log(self, message: str, **kwargs):
        """Log message within workflow context"""
        self.logger.info(message, **kwargs)

    def log_step(self, step_name: str, **kwargs):
        """Log workflow step"""
        self.logger.info(
            f"Workflow step: {step_name}",
            step_name=step_name,
            **kwargs
        )

    def set_outcome(self, outcome: str):
        """Set workflow outcome"""
        self.outcome = outcome


class DatabaseLogger:
    """
    Context manager for logging database operations

    Usage:
        with DatabaseLogger(trace_id="abc123", operation="CREATE_BAG") as db_logger:
            # Execute query
            result = db.execute(query)
            db_logger.set_rows_affected(len(result))
    """

    def __init__(
        self,
        trace_id: str,
        operation: str,
        query: str,
        **extra_context
    ):
        self.trace_id = trace_id
        self.operation = operation
        self.query = query
        self.extra_context = extra_context

        self.logger = get_logger(trace_id=trace_id, **extra_context)
        self.start_time = None
        self.rows_affected = 0

    def __enter__(self):
        """Start timing"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log database operation"""
        latency_ms = (time.time() - self.start_time) * 1000

        if exc_type:
            # Query failed
            self.logger.error(
                f"Database operation failed: {self.operation}",
                event_type="db_operation_failed",
                operation=self.operation,
                query=self.query[:200],
                latency_ms=latency_ms,
                error=str(exc_val),
                error_type=exc_type.__name__ if exc_type else None
            )
        else:
            # Query succeeded
            self.logger.log_db_operation(
                operation=self.operation,
                query=self.query,
                latency_ms=latency_ms,
                rows_affected=self.rows_affected
            )

        return False

    def set_rows_affected(self, count: int):
        """Set number of rows affected"""
        self.rows_affected = count


class APICallLogger:
    """
    Context manager for logging external API calls

    Usage:
        with APICallLogger(
            trace_id="abc123",
            service="WorldTracer",
            endpoint="/api/pir"
        ) as api_logger:
            response = requests.post(url, json=data)
            api_logger.set_status(response.status_code)
    """

    def __init__(
        self,
        trace_id: str,
        service: str,
        endpoint: str,
        **extra_context
    ):
        self.trace_id = trace_id
        self.service = service
        self.endpoint = endpoint
        self.extra_context = extra_context

        self.logger = get_logger(trace_id=trace_id, **extra_context)
        self.start_time = None
        self.status_code = 0

    def __enter__(self):
        """Start timing"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log API call"""
        latency_ms = (time.time() - self.start_time) * 1000

        if exc_type:
            # API call failed
            self.logger.error(
                f"API call failed: {self.service} {self.endpoint}",
                event_type="api_call_failed",
                service=self.service,
                endpoint=self.endpoint,
                latency_ms=latency_ms,
                error=str(exc_val),
                error_type=exc_type.__name__ if exc_type else None
            )
        else:
            # API call succeeded
            self.logger.log_api_call(
                service=self.service,
                endpoint=self.endpoint,
                status_code=self.status_code,
                latency_ms=latency_ms
            )

        return False

    def set_status(self, status_code: int):
        """Set response status code"""
        self.status_code = status_code


def get_current_trace_id() -> Optional[str]:
    """Get current trace ID from context"""
    return trace_id_var.get()


def get_current_bag_tag() -> Optional[str]:
    """Get current bag tag from context"""
    return bag_tag_var.get()


def get_current_agent_name() -> Optional[str]:
    """Get current agent name from context"""
    return agent_name_var.get()
