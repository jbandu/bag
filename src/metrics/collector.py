"""
Metrics Collector for Redis
Simple metrics collection for debugging and monitoring
"""

import os
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from redis import Redis
from redis.exceptions import RedisError


class MetricsCollector:
    """
    Simple metrics collector using Redis

    Tracks:
    - Request count per minute
    - Error count per minute
    - Average latency
    - Agent performance (calls per agent, success rate)
    - Database health metrics
    """

    def __init__(self, redis_client: Optional[Redis] = None):
        """Initialize metrics collector"""
        if redis_client:
            self.redis = redis_client
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = Redis.from_url(redis_url, decode_responses=True)

        self.enabled = True

    def record_request(
        self,
        endpoint: str,
        method: str = "POST",
        status_code: int = 200,
        latency_ms: float = 0,
        trace_id: Optional[str] = None
    ):
        """Record API request metrics"""
        if not self.enabled:
            return

        try:
            timestamp = int(time.time())
            minute_key = timestamp // 60  # Round to minute

            # Increment request counter for this minute
            self.redis.hincrby("metrics:requests_per_minute", minute_key, 1)

            # Track latency
            self.redis.lpush("metrics:latencies", latency_ms)
            self.redis.ltrim("metrics:latencies", 0, 999)  # Keep last 1000

            # Track errors (4xx, 5xx)
            if status_code >= 400:
                self.redis.hincrby("metrics:errors_per_minute", minute_key, 1)

            # Track endpoint-specific metrics
            endpoint_key = f"metrics:endpoint:{endpoint}:{method}"
            self.redis.hincrby(f"{endpoint_key}:count", minute_key, 1)
            self.redis.lpush(f"{endpoint_key}:latencies", latency_ms)
            self.redis.ltrim(f"{endpoint_key}:latencies", 0, 99)

            # Set expiry on minute keys (keep 24 hours)
            self.redis.expire("metrics:requests_per_minute", 86400)
            self.redis.expire("metrics:errors_per_minute", 86400)

        except RedisError as e:
            # Don't fail the request if metrics collection fails
            print(f"Warning: Failed to record metrics: {e}")

    def record_agent_call(
        self,
        agent_name: str,
        success: bool = True,
        duration_ms: float = 0,
        trace_id: Optional[str] = None
    ):
        """Record agent workflow metrics"""
        if not self.enabled:
            return

        try:
            # Track agent call count
            self.redis.hincrby("metrics:agent_calls", agent_name, 1)

            # Track success/failure
            if success:
                self.redis.hincrby("metrics:agent_success", agent_name, 1)
            else:
                self.redis.hincrby("metrics:agent_errors", agent_name, 1)

            # Track agent latency
            self.redis.lpush(f"metrics:agent_latency:{agent_name}", duration_ms)
            self.redis.ltrim(f"metrics:agent_latency:{agent_name}", 0, 99)

        except RedisError as e:
            print(f"Warning: Failed to record agent metrics: {e}")

    def record_db_operation(
        self,
        operation: str,
        latency_ms: float,
        success: bool = True,
        rows_affected: int = 0
    ):
        """Record database operation metrics"""
        if not self.enabled:
            return

        try:
            # Track DB operations
            self.redis.hincrby("metrics:db_operations", operation, 1)

            # Track latency
            self.redis.lpush(f"metrics:db_latency:{operation}", latency_ms)
            self.redis.ltrim(f"metrics:db_latency:{operation}", 0, 99)

            # Track errors
            if not success:
                self.redis.hincrby("metrics:db_errors", operation, 1)

        except RedisError as e:
            print(f"Warning: Failed to record DB metrics: {e}")

    def get_requests_per_minute(self, last_n_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get request count per minute for last N minutes"""
        try:
            current_minute = int(time.time()) // 60
            data = []

            for i in range(last_n_minutes):
                minute_key = current_minute - i
                count = self.redis.hget("metrics:requests_per_minute", minute_key)
                count = int(count) if count else 0

                data.append({
                    "timestamp": datetime.fromtimestamp(minute_key * 60).isoformat(),
                    "minute": minute_key,
                    "requests": count
                })

            return list(reversed(data))

        except RedisError as e:
            print(f"Warning: Failed to get requests per minute: {e}")
            return []

    def get_error_rate(self, last_n_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get error rate per minute for last N minutes"""
        try:
            current_minute = int(time.time()) // 60
            data = []

            for i in range(last_n_minutes):
                minute_key = current_minute - i

                requests = self.redis.hget("metrics:requests_per_minute", minute_key)
                errors = self.redis.hget("metrics:errors_per_minute", minute_key)

                requests = int(requests) if requests else 0
                errors = int(errors) if errors else 0

                error_rate = (errors / requests * 100) if requests > 0 else 0

                data.append({
                    "timestamp": datetime.fromtimestamp(minute_key * 60).isoformat(),
                    "minute": minute_key,
                    "requests": requests,
                    "errors": errors,
                    "error_rate": error_rate
                })

            return list(reversed(data))

        except RedisError as e:
            print(f"Warning: Failed to get error rate: {e}")
            return []

    def get_latency_stats(self) -> Dict[str, float]:
        """Get latency statistics"""
        try:
            latencies = self.redis.lrange("metrics:latencies", 0, -1)
            latencies = [float(l) for l in latencies]

            if not latencies:
                return {
                    "count": 0,
                    "avg": 0,
                    "min": 0,
                    "max": 0,
                    "p50": 0,
                    "p95": 0,
                    "p99": 0
                }

            latencies_sorted = sorted(latencies)
            count = len(latencies_sorted)

            return {
                "count": count,
                "avg": sum(latencies) / count,
                "min": latencies_sorted[0],
                "max": latencies_sorted[-1],
                "p50": latencies_sorted[int(count * 0.50)],
                "p95": latencies_sorted[int(count * 0.95)],
                "p99": latencies_sorted[int(count * 0.99)]
            }

        except RedisError as e:
            print(f"Warning: Failed to get latency stats: {e}")
            return {}

    def get_agent_performance(self) -> List[Dict[str, Any]]:
        """Get performance metrics for all agents"""
        try:
            agent_calls = self.redis.hgetall("metrics:agent_calls")
            agent_success = self.redis.hgetall("metrics:agent_success")
            agent_errors = self.redis.hgetall("metrics:agent_errors")

            performance = []
            for agent_name in agent_calls.keys():
                calls = int(agent_calls.get(agent_name, 0))
                success = int(agent_success.get(agent_name, 0))
                errors = int(agent_errors.get(agent_name, 0))

                # Get latency stats
                latencies = self.redis.lrange(f"metrics:agent_latency:{agent_name}", 0, -1)
                latencies = [float(l) for l in latencies]
                avg_latency = sum(latencies) / len(latencies) if latencies else 0

                performance.append({
                    "agent_name": agent_name,
                    "total_calls": calls,
                    "successful_calls": success,
                    "failed_calls": errors,
                    "success_rate": (success / calls * 100) if calls > 0 else 0,
                    "avg_latency_ms": avg_latency
                })

            return sorted(performance, key=lambda x: x["total_calls"], reverse=True)

        except RedisError as e:
            print(f"Warning: Failed to get agent performance: {e}")
            return []

    def get_db_health(self) -> Dict[str, Any]:
        """Get database health metrics"""
        try:
            operations = self.redis.hgetall("metrics:db_operations")
            errors = self.redis.hgetall("metrics:db_errors")

            total_ops = sum(int(v) for v in operations.values())
            total_errors = sum(int(v) for v in errors.values())

            # Get average latency across all operations
            all_latencies = []
            for operation in operations.keys():
                latencies = self.redis.lrange(f"metrics:db_latency:{operation}", 0, -1)
                all_latencies.extend([float(l) for l in latencies])

            avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0

            return {
                "total_operations": total_ops,
                "total_errors": total_errors,
                "error_rate": (total_errors / total_ops * 100) if total_ops > 0 else 0,
                "avg_latency_ms": avg_latency,
                "operations_by_type": {k: int(v) for k, v in operations.items()}
            }

        except RedisError as e:
            print(f"Warning: Failed to get DB health: {e}")
            return {}

    def get_current_stats(self) -> Dict[str, Any]:
        """Get current overall stats for dashboard"""
        try:
            # Get stats for last minute
            current_minute = int(time.time()) // 60
            requests = self.redis.hget("metrics:requests_per_minute", current_minute)
            errors = self.redis.hget("metrics:errors_per_minute", current_minute)

            requests = int(requests) if requests else 0
            errors = int(errors) if errors else 0

            latency_stats = self.get_latency_stats()

            return {
                "current_minute": {
                    "requests": requests,
                    "errors": errors,
                    "error_rate": (errors / requests * 100) if requests > 0 else 0
                },
                "latency": latency_stats,
                "timestamp": datetime.now().isoformat()
            }

        except RedisError as e:
            print(f"Warning: Failed to get current stats: {e}")
            return {}

    def reset_metrics(self):
        """Reset all metrics (for testing)"""
        try:
            # Get all metrics keys
            keys = self.redis.keys("metrics:*")
            if keys:
                self.redis.delete(*keys)
        except RedisError as e:
            print(f"Warning: Failed to reset metrics: {e}")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_request_metric(
    endpoint: str,
    method: str,
    status_code: int,
    latency_ms: float,
    trace_id: Optional[str] = None
):
    """Quick function to record request metrics"""
    collector = get_metrics_collector()
    collector.record_request(endpoint, method, status_code, latency_ms, trace_id)


def record_agent_metric(
    agent_name: str,
    success: bool,
    duration_ms: float,
    trace_id: Optional[str] = None
):
    """Quick function to record agent metrics"""
    collector = get_metrics_collector()
    collector.record_agent_call(agent_name, success, duration_ms, trace_id)
