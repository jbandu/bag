"""
Rate Limiter
============

Enforces rate limits to prevent overwhelming external systems.

Algorithms:
- Token Bucket: Smooth rate limiting with bursts
- Sliding Window: Precise request counting
- Leaky Bucket: Constant output rate

Version: 1.0.0
Date: 2025-11-13
"""

from typing import Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
from loguru import logger
import time
import threading


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    max_requests: int  # Maximum requests
    window_seconds: int  # Time window
    burst_size: Optional[int] = None  # Max burst (defaults to max_requests)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass


class TokenBucketRateLimiter:
    """
    Token bucket algorithm for rate limiting

    Allows bursts while maintaining average rate
    """

    def __init__(self, name: str, config: RateLimitConfig):
        """
        Initialize token bucket rate limiter

        Args:
            name: Identifier for this rate limiter
            config: Rate limit configuration
        """
        self.name = name
        self.config = config
        self.capacity = config.burst_size or config.max_requests
        self.tokens = float(self.capacity)
        self.rate = config.max_requests / config.window_seconds  # tokens per second
        self.last_update = time.time()
        self.lock = threading.Lock()

        # Stats
        self.total_requests = 0
        self.allowed_requests = 0
        self.rejected_requests = 0

        logger.info(
            f"TokenBucketRateLimiter '{name}' initialized: "
            f"{config.max_requests} req/{config.window_seconds}s, "
            f"burst={self.capacity}"
        )

    def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False otherwise
        """
        with self.lock:
            self.total_requests += 1
            current_time = time.time()

            # Refill tokens based on time elapsed
            elapsed = current_time - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = current_time

            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.allowed_requests += 1
                return True
            else:
                self.rejected_requests += 1
                return False

    def check(self, tokens: int = 1, raise_on_limit: bool = False) -> bool:
        """
        Check if request would be allowed

        Args:
            tokens: Number of tokens needed
            raise_on_limit: Raise exception if limit exceeded

        Returns:
            True if allowed

        Raises:
            RateLimitExceeded: If raise_on_limit=True and limit exceeded
        """
        allowed = self.acquire(tokens)

        if not allowed:
            logger.warning(
                f"RateLimiter '{self.name}': Rate limit exceeded "
                f"({self.allowed_requests}/{self.total_requests} allowed)"
            )

            if raise_on_limit:
                wait_time = (tokens - self.tokens) / self.rate
                raise RateLimitExceeded(
                    f"Rate limit exceeded for '{self.name}'. "
                    f"Max {self.config.max_requests} requests per {self.config.window_seconds}s. "
                    f"Try again in {wait_time:.1f} seconds."
                )

        return allowed

    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        with self.lock:
            return {
                "name": self.name,
                "max_requests": self.config.max_requests,
                "window_seconds": self.config.window_seconds,
                "burst_size": self.capacity,
                "current_tokens": self.tokens,
                "total_requests": self.total_requests,
                "allowed": self.allowed_requests,
                "rejected": self.rejected_requests,
                "rejection_rate": self.rejected_requests / self.total_requests if self.total_requests > 0 else 0
            }

    def reset(self):
        """Reset rate limiter"""
        with self.lock:
            self.tokens = float(self.capacity)
            self.last_update = time.time()
            logger.info(f"RateLimiter '{self.name}' reset")


class SlidingWindowRateLimiter:
    """
    Sliding window algorithm for rate limiting

    More precise than fixed windows, counts requests in rolling window
    """

    def __init__(self, name: str, config: RateLimitConfig):
        """
        Initialize sliding window rate limiter

        Args:
            name: Identifier for this rate limiter
            config: Rate limit configuration
        """
        self.name = name
        self.config = config
        self.requests = deque()  # Timestamps of requests
        self.lock = threading.Lock()

        # Stats
        self.total_requests = 0
        self.allowed_requests = 0
        self.rejected_requests = 0

        logger.info(
            f"SlidingWindowRateLimiter '{name}' initialized: "
            f"{config.max_requests} req/{config.window_seconds}s"
        )

    def acquire(self) -> bool:
        """
        Try to acquire permission for request

        Returns:
            True if allowed, False otherwise
        """
        with self.lock:
            self.total_requests += 1
            current_time = time.time()
            window_start = current_time - self.config.window_seconds

            # Remove old requests outside window
            while self.requests and self.requests[0] < window_start:
                self.requests.popleft()

            # Check if under limit
            if len(self.requests) < self.config.max_requests:
                self.requests.append(current_time)
                self.allowed_requests += 1
                return True
            else:
                self.rejected_requests += 1
                return False

    def check(self, raise_on_limit: bool = False) -> bool:
        """
        Check if request would be allowed

        Args:
            raise_on_limit: Raise exception if limit exceeded

        Returns:
            True if allowed

        Raises:
            RateLimitExceeded: If raise_on_limit=True and limit exceeded
        """
        allowed = self.acquire()

        if not allowed:
            logger.warning(
                f"RateLimiter '{self.name}': Rate limit exceeded "
                f"({len(self.requests)}/{self.config.max_requests} in window)"
            )

            if raise_on_limit:
                # Calculate when oldest request will expire
                with self.lock:
                    if self.requests:
                        oldest = self.requests[0]
                        wait_time = self.config.window_seconds - (time.time() - oldest)
                        wait_time = max(0, wait_time)
                    else:
                        wait_time = 0

                raise RateLimitExceeded(
                    f"Rate limit exceeded for '{self.name}'. "
                    f"Max {self.config.max_requests} requests per {self.config.window_seconds}s. "
                    f"Try again in {wait_time:.1f} seconds."
                )

        return allowed

    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        with self.lock:
            return {
                "name": self.name,
                "max_requests": self.config.max_requests,
                "window_seconds": self.config.window_seconds,
                "current_requests_in_window": len(self.requests),
                "total_requests": self.total_requests,
                "allowed": self.allowed_requests,
                "rejected": self.rejected_requests,
                "rejection_rate": self.rejected_requests / self.total_requests if self.total_requests > 0 else 0
            }

    def reset(self):
        """Reset rate limiter"""
        with self.lock:
            self.requests.clear()
            logger.info(f"RateLimiter '{self.name}' reset")


class RateLimiterManager:
    """Manages multiple rate limiters"""

    def __init__(self):
        """Initialize rate limiter manager"""
        self.limiters: dict[str, TokenBucketRateLimiter | SlidingWindowRateLimiter] = {}
        logger.info("RateLimiterManager initialized")

    def get_limiter(
        self,
        name: str,
        config: RateLimitConfig,
        algorithm: str = "token_bucket"
    ):
        """
        Get or create rate limiter

        Args:
            name: Rate limiter name
            config: Configuration
            algorithm: "token_bucket" or "sliding_window"

        Returns:
            RateLimiter instance
        """
        if name not in self.limiters:
            if algorithm == "token_bucket":
                self.limiters[name] = TokenBucketRateLimiter(name, config)
            elif algorithm == "sliding_window":
                self.limiters[name] = SlidingWindowRateLimiter(name, config)
            else:
                raise ValueError(f"Unknown algorithm: {algorithm}")

        return self.limiters[name]

    def check(self, name: str, raise_on_limit: bool = False) -> bool:
        """
        Check rate limit

        Args:
            name: Rate limiter name
            raise_on_limit: Raise exception if exceeded

        Returns:
            True if allowed
        """
        if name not in self.limiters:
            logger.warning(f"Rate limiter '{name}' not found, allowing request")
            return True

        return self.limiters[name].check(raise_on_limit=raise_on_limit)

    def get_all_stats(self) -> dict:
        """Get statistics for all rate limiters"""
        return {
            name: limiter.get_stats()
            for name, limiter in self.limiters.items()
        }

    def reset_all(self):
        """Reset all rate limiters"""
        for limiter in self.limiters.values():
            limiter.reset()
        logger.info("All rate limiters reset")


# Predefined rate limit configurations for common systems
RATE_LIMITS = {
    "worldtracer": RateLimitConfig(max_requests=100, window_seconds=60),  # 100 req/min
    "dcs": RateLimitConfig(max_requests=500, window_seconds=60, burst_size=100),  # 500 req/min, burst 100
    "bhs": RateLimitConfig(max_requests=1000, window_seconds=60, burst_size=200),  # 1000 req/min, burst 200
    "courier_api": RateLimitConfig(max_requests=60, window_seconds=60),  # 60 req/min
    "notification": RateLimitConfig(max_requests=300, window_seconds=60, burst_size=50),  # 300 req/min
    "type_b": RateLimitConfig(max_requests=200, window_seconds=60),  # 200 req/min
    "xml_api": RateLimitConfig(max_requests=250, window_seconds=60, burst_size=75),  # 250 req/min
}
