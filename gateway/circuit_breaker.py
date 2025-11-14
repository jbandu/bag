"""
Circuit Breaker
===============

Prevents calling failing external systems.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: System is failing, requests fail immediately
- HALF_OPEN: Testing if system recovered

Version: 1.0.0
Date: 2025-11-13
"""

from typing import Callable, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger
import time


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # System failing, reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5  # Open after N failures
    success_threshold: int = 2  # Close after N successes in half-open
    timeout_seconds: int = 60  # Time to wait before half-open
    window_seconds: int = 60  # Sliding window for failures


@dataclass
class CircuitStats:
    """Circuit breaker statistics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    state_changes: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation

    Protects against cascading failures by:
    - Detecting failing systems
    - Rejecting requests when system is down
    - Testing recovery periodically
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker

        Args:
            name: Identifier for this circuit breaker
            config: Configuration (uses defaults if None)
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self.opened_at: Optional[datetime] = None

        logger.info(
            f"CircuitBreaker '{name}' initialized: "
            f"threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout_seconds}s"
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        self.stats.total_requests += 1

        # Check if circuit should transition to half-open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"CircuitBreaker '{self.name}': Transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.stats.state_changes += 1
            else:
                # Circuit still open, reject request
                self.stats.rejected_requests += 1
                logger.warning(
                    f"CircuitBreaker '{self.name}': Request rejected (circuit OPEN)"
                )
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"System unavailable. "
                    f"Opened at: {self.opened_at}"
                )

        # Try to execute the function
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time

            # Success!
            self._on_success(elapsed)
            return result

        except Exception as e:
            # Failure!
            self._on_failure(e)
            raise

    def _on_success(self, elapsed_seconds: float):
        """Handle successful request"""
        self.stats.successful_requests += 1
        self.stats.consecutive_successes += 1
        self.stats.consecutive_failures = 0
        self.stats.last_success_time = datetime.now()

        logger.debug(
            f"CircuitBreaker '{self.name}': Success in {elapsed_seconds:.3f}s "
            f"(consecutive: {self.stats.consecutive_successes})"
        )

        # If in half-open state, check if we should close circuit
        if self.state == CircuitState.HALF_OPEN:
            if self.stats.consecutive_successes >= self.config.success_threshold:
                logger.info(
                    f"CircuitBreaker '{self.name}': Transitioning to CLOSED "
                    f"(recovered after {self.stats.consecutive_successes} successes)"
                )
                self.state = CircuitState.CLOSED
                self.stats.state_changes += 1
                self.stats.consecutive_successes = 0
                self.opened_at = None

    def _on_failure(self, error: Exception):
        """Handle failed request"""
        self.stats.failed_requests += 1
        self.stats.consecutive_failures += 1
        self.stats.consecutive_successes = 0
        self.stats.last_failure_time = datetime.now()

        logger.warning(
            f"CircuitBreaker '{self.name}': Failure #{self.stats.consecutive_failures} - {error}"
        )

        # If in half-open state, immediately re-open
        if self.state == CircuitState.HALF_OPEN:
            logger.warning(
                f"CircuitBreaker '{self.name}': Transitioning back to OPEN "
                f"(recovery failed)"
            )
            self.state = CircuitState.OPEN
            self.stats.state_changes += 1
            self.opened_at = datetime.now()
            self.stats.consecutive_failures = 0

        # If in closed state, check if we should open
        elif self.state == CircuitState.CLOSED:
            if self.stats.consecutive_failures >= self.config.failure_threshold:
                logger.error(
                    f"CircuitBreaker '{self.name}': Transitioning to OPEN "
                    f"(threshold reached: {self.stats.consecutive_failures} failures)"
                )
                self.state = CircuitState.OPEN
                self.stats.state_changes += 1
                self.opened_at = datetime.now()
                self.stats.consecutive_failures = 0

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.opened_at:
            return True

        elapsed = (datetime.now() - self.opened_at).total_seconds()
        return elapsed >= self.config.timeout_seconds

    def reset(self):
        """Manually reset circuit breaker to closed state"""
        logger.info(f"CircuitBreaker '{self.name}': Manually reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.stats.consecutive_failures = 0
        self.stats.consecutive_successes = 0
        self.opened_at = None

    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        success_rate = 0.0
        if self.stats.total_requests > 0:
            success_rate = self.stats.successful_requests / self.stats.total_requests

        return {
            "name": self.name,
            "state": self.state.value,
            "total_requests": self.stats.total_requests,
            "successful": self.stats.successful_requests,
            "failed": self.stats.failed_requests,
            "rejected": self.stats.rejected_requests,
            "success_rate": success_rate,
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "state_changes": self.stats.state_changes,
            "last_failure": self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None,
            "last_success": self.stats.last_success_time.isoformat() if self.stats.last_success_time else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None
        }

    def is_available(self) -> bool:
        """Check if circuit is available (not open)"""
        if self.state == CircuitState.OPEN:
            # Check if should transition to half-open
            if self._should_attempt_reset():
                return True  # Will transition on next call
            return False
        return True


class CircuitBreakerManager:
    """Manages multiple circuit breakers"""

    def __init__(self):
        """Initialize circuit breaker manager"""
        self.breakers: dict[str, CircuitBreaker] = {}
        logger.info("CircuitBreakerManager initialized")

    def get_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Get or create circuit breaker

        Args:
            name: Circuit breaker name
            config: Configuration (only used if creating new)

        Returns:
            CircuitBreaker instance
        """
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(name, config)
        return self.breakers[name]

    def get_all_stats(self) -> dict:
        """Get statistics for all circuit breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self.breakers.items()
        }

    def get_health_summary(self) -> dict:
        """Get health summary of all circuits"""
        total = len(self.breakers)
        closed = sum(1 for b in self.breakers.values() if b.state == CircuitState.CLOSED)
        half_open = sum(1 for b in self.breakers.values() if b.state == CircuitState.HALF_OPEN)
        open_circuits = sum(1 for b in self.breakers.values() if b.state == CircuitState.OPEN)

        return {
            "total_circuits": total,
            "closed": closed,
            "half_open": half_open,
            "open": open_circuits,
            "health_percentage": (closed / total * 100) if total > 0 else 100.0
        }

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")
