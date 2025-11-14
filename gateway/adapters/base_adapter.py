"""
Base Adapter
============

Base class for all external system adapters.

Provides common functionality:
- Authentication handling
- Request/response logging
- Error handling
- Metrics collection

Version: 1.0.0
Date: 2025-11-13
"""

from typing import Any, Optional, Dict
from datetime import datetime
from loguru import logger
from dataclasses import dataclass, field


@dataclass
class AdapterConfig:
    """Base adapter configuration"""
    base_url: str
    auth_type: str  # "api_key", "oauth", "basic", "certificate"
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    oauth_token: Optional[str] = None
    certificate_path: Optional[str] = None
    timeout_seconds: int = 30
    verify_ssl: bool = True


@dataclass
class AdapterStats:
    """Adapter statistics"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_latency_ms: float = 0.0
    last_call_at: Optional[datetime] = None
    last_error: Optional[str] = None


class BaseAdapter:
    """
    Base class for all adapters

    Each adapter implements specific system integration
    """

    def __init__(self, name: str, config: AdapterConfig):
        """
        Initialize base adapter

        Args:
            name: Adapter name
            config: Adapter configuration
        """
        self.name = name
        self.config = config
        self.stats = AdapterStats()

        logger.info(f"Adapter '{name}' initialized: {config.base_url}")

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {}

        if self.config.auth_type == "api_key":
            headers["X-API-Key"] = self.config.api_key or ""

        elif self.config.auth_type == "oauth":
            headers["Authorization"] = f"Bearer {self.config.oauth_token}"

        elif self.config.auth_type == "basic":
            # In real implementation, would use base64
            headers["Authorization"] = f"Basic {self.config.username}:{self.config.password}"

        return headers

    def _log_call(self, method: str, success: bool, latency_ms: float, error: Optional[str] = None):
        """Log adapter call"""
        self.stats.total_calls += 1
        self.stats.last_call_at = datetime.now()

        if success:
            self.stats.successful_calls += 1
        else:
            self.stats.failed_calls += 1
            self.stats.last_error = error

        self.stats.total_latency_ms += latency_ms

        logger.info(
            f"Adapter '{self.name}.{method}': "
            f"{'SUCCESS' if success else 'FAILED'} "
            f"({latency_ms:.1f}ms)"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics"""
        avg_latency = 0.0
        if self.stats.total_calls > 0:
            avg_latency = self.stats.total_latency_ms / self.stats.total_calls

        success_rate = 0.0
        if self.stats.total_calls > 0:
            success_rate = self.stats.successful_calls / self.stats.total_calls

        return {
            "name": self.name,
            "total_calls": self.stats.total_calls,
            "successful": self.stats.successful_calls,
            "failed": self.stats.failed_calls,
            "success_rate": success_rate,
            "avg_latency_ms": avg_latency,
            "last_call": self.stats.last_call_at.isoformat() if self.stats.last_call_at else None,
            "last_error": self.stats.last_error
        }
