"""
Semantic API Gateway
====================

Unified gateway providing ONE consistent interface for all external systems.

Instead of agents dealing with 56 different integration points (8 agents × 7 systems),
they call semantic operations like:
  - gateway.create_pir(bag_data, context)
  - gateway.get_flight_info(flight_number)
  - gateway.send_notification(passenger, message)

The gateway handles ALL the complexity:
  - Authentication (OAuth, API keys, certificates)
  - Rate limiting (per-system policies)
  - Circuit breaking (isolate failures)
  - Caching (avoid redundant calls)
  - Retries (intelligent backoff)
  - Data transformation (JSON, XML, Type B)
  - Error handling (unified responses)

Version: 1.0.0
Date: 2025-11-13
"""

from typing import Any, Optional, Dict, List, Callable
from datetime import datetime
from dataclasses import dataclass
from loguru import logger
import time
import asyncio

from gateway.circuit_breaker import CircuitBreakerManager, CircuitBreakerConfig, CircuitBreakerError
from gateway.rate_limiter import RateLimiterManager, RateLimitConfig, RateLimitExceeded, RATE_LIMITS
from gateway.cache_manager import CacheManagerRegistry, CacheConfig, generate_cache_key, CACHE_CONFIGS

from models.canonical_bag import CanonicalBag, DataSource


@dataclass
class GatewayResponse:
    """Unified gateway response"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    source: Optional[str] = None
    cached: bool = False
    latency_ms: float = 0.0
    retries: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_retries: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 5000
    exponential_backoff: bool = True
    retry_on_rate_limit: bool = True


class SemanticAPIGateway:
    """
    Semantic API Gateway - ONE interface for ALL external systems

    Agents call semantic operations:
      result = gateway.create_pir(bag_data)
      result = gateway.track_shipment(tracking_number)
      result = gateway.send_sms(phone, message)

    Gateway handles:
      - Routing to correct adapter
      - Authentication
      - Rate limiting
      - Circuit breaking
      - Caching
      - Retries
      - Data transformation
    """

    def __init__(self):
        """Initialize semantic API gateway"""

        # Infrastructure managers
        self.circuit_breakers = CircuitBreakerManager()
        self.rate_limiters = RateLimiterManager()
        self.caches = CacheManagerRegistry()

        # Adapters (will be registered)
        self.adapters: Dict[str, Any] = {}

        # Retry configuration per operation
        self.retry_configs: Dict[str, RetryConfig] = {
            "default": RetryConfig(),
            "worldtracer": RetryConfig(max_retries=3, base_delay_ms=200),
            "dcs": RetryConfig(max_retries=2, base_delay_ms=100),
            "bhs": RetryConfig(max_retries=5, base_delay_ms=50),
            "courier": RetryConfig(max_retries=3, base_delay_ms=500),
            "notification": RetryConfig(max_retries=2, base_delay_ms=100),
        }

        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.cache_hits = 0
        self.start_time = datetime.now()

        logger.info("SemanticAPIGateway initialized")

    def register_adapter(self, name: str, adapter: Any):
        """
        Register an adapter for a system

        Args:
            name: System name (e.g., "worldtracer", "dcs")
            adapter: Adapter instance
        """
        self.adapters[name] = adapter
        logger.info(f"Registered adapter: {name}")

        # Initialize circuit breaker for this adapter
        breaker_config = CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=2,
            timeout_seconds=60
        )
        self.circuit_breakers.get_breaker(name, breaker_config)

        # Initialize rate limiter for this adapter
        if name in RATE_LIMITS:
            self.rate_limiters.get_limiter(
                name,
                RATE_LIMITS[name],
                algorithm="token_bucket"
            )

        # Initialize cache for this adapter
        if name in CACHE_CONFIGS:
            self.caches.get_cache(name, CACHE_CONFIGS[name])

    async def call(
        self,
        operation: str,
        adapter_name: str,
        adapter_method: str,
        use_cache: bool = False,
        cache_ttl: Optional[int] = None,
        **params
    ) -> GatewayResponse:
        """
        Make a semantic API call through the gateway

        Args:
            operation: Semantic operation name (for logging/monitoring)
            adapter_name: Which adapter to use
            adapter_method: Method to call on adapter
            use_cache: Whether to cache response
            cache_ttl: Cache TTL in seconds
            **params: Parameters to pass to adapter

        Returns:
            GatewayResponse with result
        """
        self.total_requests += 1
        start_time = time.time()

        logger.info(f"Gateway call: {operation} via {adapter_name}.{adapter_method}")

        # Check cache first
        if use_cache:
            cache_key = generate_cache_key(f"{adapter_name}.{adapter_method}", **params)
            cache = self.caches.get_cache(adapter_name)
            cached_data = cache.get(cache_key)

            if cached_data is not None:
                self.cache_hits += 1
                latency = (time.time() - start_time) * 1000
                logger.info(f"Cache HIT for {operation} ({latency:.1f}ms)")

                return GatewayResponse(
                    success=True,
                    data=cached_data,
                    source=adapter_name,
                    cached=True,
                    latency_ms=latency
                )

        # Get adapter
        if adapter_name not in self.adapters:
            error_msg = f"Adapter '{adapter_name}' not registered"
            logger.error(error_msg)
            return GatewayResponse(
                success=False,
                error=error_msg,
                source=adapter_name,
                latency_ms=(time.time() - start_time) * 1000
            )

        adapter = self.adapters[adapter_name]
        method = getattr(adapter, adapter_method, None)

        if not method:
            error_msg = f"Method '{adapter_method}' not found on adapter '{adapter_name}'"
            logger.error(error_msg)
            return GatewayResponse(
                success=False,
                error=error_msg,
                source=adapter_name,
                latency_ms=(time.time() - start_time) * 1000
            )

        # Get retry config
        retry_config = self.retry_configs.get(adapter_name, self.retry_configs["default"])

        # Execute with retries
        retry_count = 0
        last_error = None

        for attempt in range(retry_config.max_retries + 1):
            try:
                # Check rate limit
                if adapter_name in self.rate_limiters.limiters:
                    rate_limiter = self.rate_limiters.limiters[adapter_name]
                    if not rate_limiter.check(raise_on_limit=True):
                        raise RateLimitExceeded(f"Rate limit exceeded for {adapter_name}")

                # Get circuit breaker
                breaker = self.circuit_breakers.get_breaker(adapter_name)

                # Call through circuit breaker
                if asyncio.iscoroutinefunction(method):
                    # Async method
                    result = await breaker.call(lambda: method(**params))
                else:
                    # Sync method - wrap in executor
                    result = breaker.call(method, **params)

                # Success!
                self.successful_requests += 1
                latency = (time.time() - start_time) * 1000

                # Cache if requested
                if use_cache and result is not None:
                    cache_key = generate_cache_key(f"{adapter_name}.{adapter_method}", **params)
                    cache = self.caches.get_cache(adapter_name)
                    cache.set(cache_key, result, ttl_seconds=cache_ttl)

                logger.info(
                    f"Gateway call SUCCESS: {operation} "
                    f"({latency:.1f}ms, retries={retry_count})"
                )

                return GatewayResponse(
                    success=True,
                    data=result,
                    source=adapter_name,
                    cached=False,
                    latency_ms=latency,
                    retries=retry_count
                )

            except CircuitBreakerError as e:
                # Circuit breaker open - don't retry
                logger.error(f"Circuit breaker OPEN for {adapter_name}: {e}")
                last_error = str(e)
                break

            except RateLimitExceeded as e:
                # Rate limit - retry if configured
                if not retry_config.retry_on_rate_limit:
                    logger.warning(f"Rate limit exceeded for {adapter_name}, not retrying")
                    last_error = str(e)
                    break

                logger.warning(f"Rate limit exceeded for {adapter_name}, will retry")
                last_error = str(e)

            except Exception as e:
                # Other error - retry
                logger.warning(f"Attempt {attempt + 1} failed for {operation}: {e}")
                last_error = str(e)

            # Calculate retry delay
            if attempt < retry_config.max_retries:
                retry_count += 1

                if retry_config.exponential_backoff:
                    delay_ms = min(
                        retry_config.base_delay_ms * (2 ** attempt),
                        retry_config.max_delay_ms
                    )
                else:
                    delay_ms = retry_config.base_delay_ms

                logger.debug(f"Retrying {operation} in {delay_ms}ms (attempt {retry_count})")
                await asyncio.sleep(delay_ms / 1000.0)

        # All retries exhausted
        self.failed_requests += 1
        latency = (time.time() - start_time) * 1000

        logger.error(
            f"Gateway call FAILED: {operation} after {retry_count} retries "
            f"({latency:.1f}ms) - {last_error}"
        )

        return GatewayResponse(
            success=False,
            error=last_error or "Unknown error",
            source=adapter_name,
            latency_ms=latency,
            retries=retry_count
        )

    # ========================================================================
    # SEMANTIC OPERATIONS - WorldTracer
    # ========================================================================

    async def create_pir(
        self,
        bag: CanonicalBag,
        irregularity_type: str,
        description: str
    ) -> GatewayResponse:
        """
        Create Property Irregularity Report in WorldTracer

        Semantic operation - agent just provides bag and description

        Args:
            bag: Canonical bag data
            irregularity_type: Type of irregularity
            description: Description of issue

        Returns:
            GatewayResponse with PIR reference
        """
        return await self.call(
            operation="create_pir",
            adapter_name="worldtracer",
            adapter_method="create_pir",
            use_cache=False,
            bag=bag,
            irregularity_type=irregularity_type,
            description=description
        )

    async def update_pir_status(
        self,
        pir_reference: str,
        status: str,
        location: Optional[str] = None
    ) -> GatewayResponse:
        """Update PIR status in WorldTracer"""
        return await self.call(
            operation="update_pir_status",
            adapter_name="worldtracer",
            adapter_method="update_status",
            use_cache=False,
            pir_reference=pir_reference,
            status=status,
            location=location
        )

    async def get_pir(self, pir_reference: str) -> GatewayResponse:
        """Get PIR details from WorldTracer"""
        return await self.call(
            operation="get_pir",
            adapter_name="worldtracer",
            adapter_method="get_pir",
            use_cache=True,
            cache_ttl=300,  # 5 minutes
            pir_reference=pir_reference
        )

    # ========================================================================
    # SEMANTIC OPERATIONS - DCS
    # ========================================================================

    async def get_passenger_pnr(self, pnr: str) -> GatewayResponse:
        """Get passenger booking from DCS"""
        return await self.call(
            operation="get_passenger_pnr",
            adapter_name="dcs",
            adapter_method="get_pnr",
            use_cache=True,
            cache_ttl=600,  # 10 minutes
            pnr=pnr
        )

    async def get_baggage_info(self, bag_tag: str) -> GatewayResponse:
        """Get baggage info from DCS"""
        return await self.call(
            operation="get_baggage_info",
            adapter_name="dcs",
            adapter_method="get_baggage",
            use_cache=True,
            cache_ttl=300,
            bag_tag=bag_tag
        )

    # ========================================================================
    # SEMANTIC OPERATIONS - BHS
    # ========================================================================

    async def get_bag_location(self, bag_tag: str) -> GatewayResponse:
        """Get current bag location from BHS"""
        return await self.call(
            operation="get_bag_location",
            adapter_name="bhs",
            adapter_method="get_location",
            use_cache=True,
            cache_ttl=60,  # 1 minute (fast changing)
            bag_tag=bag_tag
        )

    async def get_scan_history(self, bag_tag: str) -> GatewayResponse:
        """Get scan history from BHS"""
        return await self.call(
            operation="get_scan_history",
            adapter_name="bhs",
            adapter_method="get_scan_history",
            use_cache=True,
            cache_ttl=120,
            bag_tag=bag_tag
        )

    # ========================================================================
    # SEMANTIC OPERATIONS - Courier
    # ========================================================================

    async def create_shipment(
        self,
        courier: str,
        origin: str,
        destination: str,
        recipient: Dict[str, str],
        bag_tag: str
    ) -> GatewayResponse:
        """Create courier shipment"""
        return await self.call(
            operation="create_shipment",
            adapter_name="courier",
            adapter_method="create_shipment",
            use_cache=False,
            courier=courier,
            origin=origin,
            destination=destination,
            recipient=recipient,
            bag_tag=bag_tag
        )

    async def track_shipment(
        self,
        courier: str,
        tracking_number: str
    ) -> GatewayResponse:
        """Track courier shipment"""
        return await self.call(
            operation="track_shipment",
            adapter_name="courier",
            adapter_method="track",
            use_cache=True,
            cache_ttl=300,
            courier=courier,
            tracking_number=tracking_number
        )

    # ========================================================================
    # SEMANTIC OPERATIONS - Notifications
    # ========================================================================

    async def send_sms(
        self,
        phone: str,
        message: str,
        priority: str = "NORMAL"
    ) -> GatewayResponse:
        """Send SMS notification"""
        return await self.call(
            operation="send_sms",
            adapter_name="notification",
            adapter_method="send_sms",
            use_cache=False,
            phone=phone,
            message=message,
            priority=priority
        )

    async def send_email(
        self,
        email: str,
        subject: str,
        body: str,
        template: Optional[str] = None
    ) -> GatewayResponse:
        """Send email notification"""
        return await self.call(
            operation="send_email",
            adapter_name="notification",
            adapter_method="send_email",
            use_cache=False,
            email=email,
            subject=subject,
            body=body,
            template=template
        )

    # ========================================================================
    # MONITORING & OBSERVABILITY
    # ========================================================================

    def get_health(self) -> Dict[str, Any]:
        """Get gateway health status"""
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        success_rate = 0.0
        if self.total_requests > 0:
            success_rate = self.successful_requests / self.total_requests

        return {
            "status": "healthy" if success_rate > 0.95 else "degraded",
            "uptime_seconds": uptime_seconds,
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "success_rate": success_rate,
            "cache_hit_rate": self.cache_hits / self.total_requests if self.total_requests > 0 else 0,
            "circuit_breakers": self.circuit_breakers.get_health_summary(),
            "adapters_registered": len(self.adapters)
        }

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed statistics"""
        return {
            "gateway": self.get_health(),
            "circuit_breakers": self.circuit_breakers.get_all_stats(),
            "rate_limiters": self.rate_limiters.get_all_stats(),
            "caches": self.caches.get_all_stats()
        }

    def get_adapter_health(self, adapter_name: str) -> Dict[str, Any]:
        """Get health of specific adapter"""
        breaker_stats = self.circuit_breakers.get_breaker(adapter_name).get_stats()

        rate_limiter = None
        if adapter_name in self.rate_limiters.limiters:
            rate_limiter = self.rate_limiters.limiters[adapter_name].get_stats()

        cache = None
        if adapter_name in self.caches.caches:
            cache = self.caches.caches[adapter_name].get_stats()

        return {
            "adapter": adapter_name,
            "registered": adapter_name in self.adapters,
            "circuit_breaker": breaker_stats,
            "rate_limiter": rate_limiter,
            "cache": cache
        }
