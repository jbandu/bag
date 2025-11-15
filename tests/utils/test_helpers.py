"""
General Test Helper Utilities
Common utilities for all test types
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
import asyncio


def get_test_config() -> Dict[str, Any]:
    """Get test configuration from environment"""
    return {
        "railway_url": os.getenv("RAILWAY_URL", "http://localhost:8000"),
        "api_key": os.getenv("API_KEY", ""),
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD", "password"),
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "test_timeout": int(os.getenv("TEST_TIMEOUT", "30")),
        "enable_cleanup": os.getenv("ENABLE_CLEANUP", "true").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "INFO")
    }


def measure_time(func):
    """Decorator to measure function execution time"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} took {duration:.3f}s")
        return result

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} took {duration:.3f}s")
        return result

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry function on failure with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        print(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        print(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


class TestContext:
    """Context manager for test setup and teardown"""

    def __init__(self, name: str, cleanup_func: Optional[Callable] = None):
        self.name = name
        self.cleanup_func = cleanup_func
        self.start_time = None
        self.resources = []

    def __enter__(self):
        self.start_time = time.time()
        print(f"\n{'=' * 60}")
        print(f"Starting test: {self.name}")
        print(f"{'=' * 60}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        print(f"{'=' * 60}")
        if exc_type:
            print(f"Test failed: {self.name} ({duration:.3f}s)")
            print(f"Error: {exc_val}")
        else:
            print(f"Test passed: {self.name} ({duration:.3f}s)")
        print(f"{'=' * 60}\n")

        if self.cleanup_func:
            try:
                self.cleanup_func(self.resources)
            except Exception as e:
                print(f"Warning: Cleanup failed: {e}")

    def track_resource(self, resource_id: str):
        """Track a resource for cleanup"""
        self.resources.append(resource_id)


class PerformanceMetrics:
    """Track and report performance metrics"""

    def __init__(self):
        self.metrics = {
            "request_count": 0,
            "error_count": 0,
            "total_duration": 0.0,
            "durations": [],
            "start_time": None,
            "end_time": None
        }

    def start(self):
        """Start tracking"""
        self.metrics["start_time"] = time.time()

    def stop(self):
        """Stop tracking"""
        self.metrics["end_time"] = time.time()

    def record_request(self, duration: float, success: bool = True):
        """Record a request"""
        self.metrics["request_count"] += 1
        self.metrics["total_duration"] += duration
        self.metrics["durations"].append(duration)
        if not success:
            self.metrics["error_count"] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        durations = sorted(self.metrics["durations"])
        count = len(durations)

        if count == 0:
            return {"error": "No requests recorded"}

        total_time = self.metrics["end_time"] - self.metrics["start_time"] if self.metrics["end_time"] else 0

        return {
            "total_requests": self.metrics["request_count"],
            "successful_requests": self.metrics["request_count"] - self.metrics["error_count"],
            "failed_requests": self.metrics["error_count"],
            "success_rate": (self.metrics["request_count"] - self.metrics["error_count"]) / self.metrics["request_count"],
            "total_duration_seconds": total_time,
            "throughput_rps": self.metrics["request_count"] / total_time if total_time > 0 else 0,
            "average_response_time_ms": sum(durations) / count * 1000,
            "min_response_time_ms": min(durations) * 1000,
            "max_response_time_ms": max(durations) * 1000,
            "p50_response_time_ms": durations[int(count * 0.50)] * 1000,
            "p95_response_time_ms": durations[int(count * 0.95)] * 1000,
            "p99_response_time_ms": durations[int(count * 0.99)] * 1000
        }

    def print_summary(self):
        """Print performance summary"""
        summary = self.get_summary()
        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)
        print(f"Total Requests:     {summary['total_requests']}")
        print(f"Successful:         {summary['successful_requests']}")
        print(f"Failed:             {summary['failed_requests']}")
        print(f"Success Rate:       {summary['success_rate']:.1%}")
        print(f"Total Duration:     {summary['total_duration_seconds']:.2f}s")
        print(f"Throughput:         {summary['throughput_rps']:.2f} req/s")
        print(f"Avg Response Time:  {summary['average_response_time_ms']:.0f}ms")
        print(f"Min Response Time:  {summary['min_response_time_ms']:.0f}ms")
        print(f"Max Response Time:  {summary['max_response_time_ms']:.0f}ms")
        print(f"P50 Response Time:  {summary['p50_response_time_ms']:.0f}ms")
        print(f"P95 Response Time:  {summary['p95_response_time_ms']:.0f}ms")
        print(f"P99 Response Time:  {summary['p99_response_time_ms']:.0f}ms")
        print("=" * 60 + "\n")


def generate_test_id(prefix: str = "test") -> str:
    """Generate unique test ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}_{os.getpid()}"


def load_json_fixture(filename: str) -> Dict[str, Any]:
    """Load JSON fixture file"""
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    filepath = os.path.join(fixtures_dir, filename)

    with open(filepath, 'r') as f:
        return json.load(f)


def save_test_results(results: Dict[str, Any], filename: str):
    """Save test results to file"""
    output_dir = os.path.join(os.getcwd(), "test_results")
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Test results saved to: {filepath}")


def assert_within_range(value: float, expected: float, tolerance: float, message: str = ""):
    """Assert value is within tolerance of expected"""
    diff = abs(value - expected)
    tolerance_value = expected * tolerance
    assert diff <= tolerance_value, \
        f"{message or 'Value out of range'}: {value} not within {tolerance * 100}% of {expected}"


def assert_list_contains(items: List[Any], expected: Any, message: str = ""):
    """Assert list contains expected item"""
    assert expected in items, \
        f"{message or 'Item not in list'}: {expected} not found in {items}"


def assert_dict_subset(actual: Dict[str, Any], expected: Dict[str, Any]):
    """Assert actual dict contains all keys from expected dict with matching values"""
    for key, expected_value in expected.items():
        assert key in actual, f"Missing key: {key}"
        assert actual[key] == expected_value, \
            f"Value mismatch for {key}: expected {expected_value}, got {actual[key]}"


def create_mock_timestamp(hours_offset: int = 0) -> str:
    """Create ISO timestamp with offset"""
    timestamp = datetime.utcnow() + timedelta(hours=hours_offset)
    return timestamp.isoformat() + "Z"


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO timestamp string"""
    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))


def time_difference_minutes(timestamp1: str, timestamp2: str) -> float:
    """Calculate time difference in minutes between two ISO timestamps"""
    dt1 = parse_timestamp(timestamp1)
    dt2 = parse_timestamp(timestamp2)
    return abs((dt2 - dt1).total_seconds() / 60)


async def wait_for_health(url: str, timeout: int = 60):
    """Wait for service to be healthy"""
    import httpx

    start = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            try:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    print(f"Service healthy at {url}")
                    return True
            except Exception:
                pass
            await asyncio.sleep(2)

    raise TimeoutError(f"Service at {url} did not become healthy within {timeout}s")


def skip_if_not_integration():
    """Decorator to skip test if not running integration tests"""
    import pytest
    return pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"),
        reason="Integration tests not enabled"
    )


def skip_if_not_e2e():
    """Decorator to skip test if not running E2E tests"""
    import pytest
    return pytest.mark.skipif(
        not os.getenv("RUN_E2E_TESTS"),
        reason="E2E tests not enabled"
    )


class MockResponse:
    """Mock HTTP response for testing"""

    def __init__(self, status_code: int, json_data: Dict[str, Any], headers: Optional[Dict] = None):
        self.status_code = status_code
        self.json_data = json_data
        self.headers = headers or {}
        self.text = json.dumps(json_data)

    def json(self):
        return self.json_data


def create_test_database_uri(db_name: str = None) -> str:
    """Create test database URI"""
    base_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    if db_name:
        return f"{base_uri}/{db_name}"
    return base_uri
