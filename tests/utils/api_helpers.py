"""
API Helper Utilities for Testing
Reusable functions for API testing and validation
"""

import asyncio
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
import json


class APITestClient:
    """Enhanced HTTP client for API testing with retry and validation"""

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(timeout=self.timeout)

    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get request headers with API key"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "BaggageAI-Test-Client/1.0"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if additional_headers:
            headers.update(additional_headers)
        return headers

    async def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(self.max_retries):
            try:
                response = await self.client.request(
                    method,
                    url,
                    headers=self._get_headers(kwargs.pop('headers', None)),
                    **kwargs
                )
                return response
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        raise Exception("Max retries exceeded")

    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """GET request"""
        return await self.request("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, data: Dict[str, Any], **kwargs) -> httpx.Response:
        """POST request"""
        return await self.request("POST", endpoint, json=data, **kwargs)

    async def put(self, endpoint: str, data: Dict[str, Any], **kwargs) -> httpx.Response:
        """PUT request"""
        return await self.request("PUT", endpoint, json=data, **kwargs)

    async def patch(self, endpoint: str, data: Dict[str, Any], **kwargs) -> httpx.Response:
        """PATCH request"""
        return await self.request("PATCH", endpoint, json=data, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """DELETE request"""
        return await self.request("DELETE", endpoint, **kwargs)

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def wait_for_condition(
    condition_func,
    timeout: int = 30,
    interval: int = 1,
    error_message: str = "Condition not met within timeout"
) -> Any:
    """Wait for a condition to be true with timeout"""
    start_time = datetime.utcnow()
    while (datetime.utcnow() - start_time).total_seconds() < timeout:
        result = await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func()
        if result:
            return result
        await asyncio.sleep(interval)
    raise TimeoutError(error_message)


async def poll_until_status(
    client: APITestClient,
    endpoint: str,
    expected_status: str,
    status_field: str = "status",
    timeout: int = 60,
    interval: int = 2
) -> Dict[str, Any]:
    """Poll an endpoint until resource reaches expected status"""
    async def check_status():
        response = await client.get(endpoint)
        if response.status_code == 200:
            data = response.json()
            if data.get(status_field) == expected_status:
                return data
        return None

    return await wait_for_condition(
        check_status,
        timeout=timeout,
        interval=interval,
        error_message=f"Resource did not reach status '{expected_status}' within {timeout}s"
    )


def assert_valid_response(
    response: httpx.Response,
    expected_status: int = 200,
    expected_fields: Optional[List[str]] = None
):
    """Assert response is valid with expected status and fields"""
    assert response.status_code == expected_status, \
        f"Expected status {expected_status}, got {response.status_code}: {response.text}"

    if expected_fields:
        data = response.json()
        for field in expected_fields:
            assert field in data, f"Expected field '{field}' not in response: {list(data.keys())}"


def assert_error_response(
    response: httpx.Response,
    expected_status: int,
    expected_error_message: Optional[str] = None
):
    """Assert response is an error with expected status and message"""
    assert response.status_code == expected_status, \
        f"Expected error status {expected_status}, got {response.status_code}"

    if expected_error_message:
        data = response.json()
        error_message = data.get('error') or data.get('message') or data.get('detail') or ''
        assert expected_error_message.lower() in error_message.lower(), \
            f"Expected error message containing '{expected_error_message}', got: {error_message}"


def assert_response_time(response: httpx.Response, max_ms: int):
    """Assert response time is within limit"""
    elapsed_ms = response.elapsed.total_seconds() * 1000
    assert elapsed_ms <= max_ms, \
        f"Response time {elapsed_ms:.0f}ms exceeds limit of {max_ms}ms"


def assert_valid_bag_data(bag: Dict[str, Any]):
    """Assert bag data has all required fields and valid values"""
    required_fields = ['bag_tag', 'status', 'risk_level', 'passenger', 'flight']
    for field in required_fields:
        assert field in bag, f"Missing required field: {field}"

    assert len(bag['bag_tag']) >= 6, "Bag tag too short"
    assert bag['status'] in ['checked_in', 'in_transit', 'arrived', 'mishandled', 'delivered'], \
        f"Invalid status: {bag['status']}"
    assert bag['risk_level'] in ['low', 'medium', 'high', 'critical'], \
        f"Invalid risk level: {bag['risk_level']}"


def assert_valid_workflow_output(output: Dict[str, Any], workflow_type: str):
    """Assert workflow output has valid structure"""
    assert 'status' in output, "Missing status field"
    assert output['status'] in ['success', 'failed', 'pending'], \
        f"Invalid status: {output['status']}"

    if workflow_type == "scan_processor":
        assert 'risk_score' in output, "Missing risk_score for scan processor"
        assert 0 <= output['risk_score'] <= 1, "Risk score out of range"

    elif workflow_type == "mishandled_bag":
        assert 'pir_number' in output or 'error' in output, \
            "Missing PIR number or error"

    elif workflow_type == "transfer_coordination":
        assert 'connection_made' in output or 'status' in output, \
            "Missing connection status"


async def run_concurrent_requests(
    client: APITestClient,
    requests: List[tuple],
    max_concurrent: int = 10
) -> List[httpx.Response]:
    """Run multiple requests concurrently with concurrency limit"""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_request(method: str, endpoint: str, **kwargs):
        async with semaphore:
            return await client.request(method, endpoint, **kwargs)

    tasks = [
        limited_request(method, endpoint, **kwargs)
        for method, endpoint, kwargs in requests
    ]

    return await asyncio.gather(*tasks, return_exceptions=True)


def calculate_percentile(values: List[float], percentile: int) -> float:
    """Calculate percentile from list of values"""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile / 100)
    return sorted_values[min(index, len(sorted_values) - 1)]


def format_test_duration(seconds: float) -> str:
    """Format test duration for human reading"""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds / 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.0f}s"


def log_request(method: str, url: str, status_code: int, duration_ms: float):
    """Log HTTP request for debugging"""
    print(f"[{method}] {url} -> {status_code} ({duration_ms:.0f}ms)")


def log_test_step(step: str, details: str = ""):
    """Log test step for debugging"""
    timestamp = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{timestamp}] {step}", end="")
    if details:
        print(f": {details}")
    else:
        print()


async def cleanup_test_data(client: APITestClient, resource_ids: List[str], endpoint: str):
    """Clean up test data after tests"""
    for resource_id in resource_ids:
        try:
            await client.delete(f"{endpoint}/{resource_id}")
        except Exception as e:
            print(f"Warning: Failed to cleanup {resource_id}: {e}")


def validate_timestamp(timestamp_str: str) -> bool:
    """Validate ISO 8601 timestamp format"""
    try:
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False


def validate_bag_tag_format(bag_tag: str) -> bool:
    """Validate bag tag format (e.g., CM123456)"""
    if len(bag_tag) < 6:
        return False
    # First 2-3 characters should be airline code (letters)
    # Remaining should be numbers
    airline_code = bag_tag[:2]
    if not airline_code.isalpha():
        return False
    number_part = bag_tag[2:]
    return number_part.isdigit()
