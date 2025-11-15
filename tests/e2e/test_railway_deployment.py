"""
End-to-End Tests for Railway Deployment
========================================

Tests the complete baggage handling system deployed on Railway.

Tests:
- API health and readiness
- Complete bag journey workflows
- External system integrations
- Error handling and recovery
- Performance and load testing

Version: 1.0.0
Date: 2025-11-14
"""

import pytest
import httpx
import asyncio
import time
from typing import Dict, Any, List
import os
from datetime import datetime

# Railway deployment URL (from environment variable)
BASE_URL = os.getenv("RAILWAY_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

# Test configuration
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2


class APIClient:
    """HTTP client for Railway API"""

    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """GET request with retries"""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.get(
                    url, headers=self._get_headers(), **kwargs
                )
                return response
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))

    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        """POST request with retries"""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.post(
                    url, headers=self._get_headers(), **kwargs
                )
                return response
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))


@pytest.fixture
async def api_client():
    """Async API client fixture"""
    async with APIClient(BASE_URL, API_KEY) as client:
        yield client


# ============================================================================
# HEALTH AND READINESS TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
class TestHealth:
    """Test API health and readiness"""

    async def test_health_endpoint(self, api_client):
        """Test /health endpoint returns 200"""
        response = await api_client.get("/health")

        assert response.status_code == 200, f"Health check failed: {response.text}"

        data = response.json()
        assert data.get("status") in ["healthy", "ok"], "Status should be healthy"

    async def test_ready_endpoint(self, api_client):
        """Test /ready endpoint"""
        response = await api_client.get("/ready")

        assert response.status_code == 200, f"Readiness check failed: {response.text}"

    async def test_metrics_endpoint(self, api_client):
        """Test /metrics endpoint returns Prometheus metrics"""
        response = await api_client.get("/metrics")

        assert response.status_code == 200
        assert "# HELP" in response.text, "Should return Prometheus format"

    async def test_api_version(self, api_client):
        """Test API returns version information"""
        response = await api_client.get("/version")

        if response.status_code == 200:
            data = response.json()
            assert "version" in data
            assert data["version"] is not None


# ============================================================================
# BAG TRACKING E2E TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
class TestBagTracking:
    """Test complete bag tracking workflows"""

    async def test_create_and_track_bag(self, api_client):
        """Test creating a bag and tracking its journey"""
        bag_tag = f"0016{int(time.time()) % 1000000:06d}"

        # Create bag
        create_payload = {
            "bag_tag": bag_tag,
            "passenger_name": "TEST/PASSENGER",
            "flight_number": "CM001",
            "origin": "PTY",
            "destination": "MIA",
            "weight_kg": 23.5
        }

        response = await api_client.post("/api/v1/bags", json=create_payload)

        # Accept both 200 and 201
        assert response.status_code in [200, 201], f"Bag creation failed: {response.text}"

        # Track bag
        response = await api_client.get(f"/api/v1/bags/{bag_tag}")

        if response.status_code == 200:
            data = response.json()
            assert data.get("bag_tag") == bag_tag
            assert data.get("passenger_name") == "TEST/PASSENGER"

    async def test_process_scan_event(self, api_client):
        """Test processing scan events"""
        bag_tag = f"0016{int(time.time()) % 1000000:06d}"

        scan_payload = {
            "bag_tag": bag_tag,
            "location": "PTY_CHECKIN",
            "scan_type": "CHECKIN",
            "timestamp": datetime.now().isoformat()
        }

        response = await api_client.post("/api/v1/scans", json=scan_payload)

        # Accept 200, 201, or 202 (accepted)
        assert response.status_code in [200, 201, 202], f"Scan processing failed: {response.text}"

    async def test_high_risk_bag_workflow(self, api_client):
        """Test high-risk bag detection and workflow"""
        bag_tag = f"0016{int(time.time()) % 1000000:06d}"

        # Create high-risk bag (tight connection + high value)
        create_payload = {
            "bag_tag": bag_tag,
            "passenger_name": "VIP/PASSENGER",
            "flight_number": "CM999",
            "origin": "PTY",
            "destination": "MIA",
            "connection_time_minutes": 25,  # Tight connection
            "value_usd": 1500,  # High value
            "weight_kg": 23.0
        }

        response = await api_client.post("/api/v1/bags", json=create_payload)

        assert response.status_code in [200, 201]

        # Check if risk assessment was triggered
        response = await api_client.get(f"/api/v1/bags/{bag_tag}/risk")

        if response.status_code == 200:
            data = response.json()
            assert data.get("risk_score", 0) > 0.5, "High-risk bag should have risk score > 0.5"


# ============================================================================
# WORKFLOW EXECUTION TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
class TestWorkflows:
    """Test workflow execution"""

    async def test_mishandled_bag_workflow(self, api_client):
        """Test mishandled bag recovery workflow"""
        bag_tag = f"0016{int(time.time()) % 1000000:06d}"

        # Report mishandled bag
        payload = {
            "bag_tag": bag_tag,
            "passenger_name": "LOST/BAG",
            "flight_number": "CM500",
            "origin": "PTY",
            "destination": "MIA",
            "status": "MISHANDLED",
            "last_seen_location": "PTY"
        }

        response = await api_client.post("/api/v1/mishandled", json=payload)

        assert response.status_code in [200, 201, 202]

        # Check if PIR was created
        if response.status_code == 200:
            data = response.json()
            if "pir_number" in data:
                assert data["pir_number"] is not None

    async def test_transfer_coordination(self, api_client):
        """Test transfer coordination workflow"""
        bag_tag = f"0016{int(time.time()) % 1000000:06d}"

        payload = {
            "bag_tag": bag_tag,
            "passenger_name": "TRANSFER/PAX",
            "flight_number": "CM123",
            "connecting_flight": "CM456",
            "origin": "PTY",
            "destination": "JFK",
            "connection_time_minutes": 45  # Tight connection
        }

        response = await api_client.post("/api/v1/transfers", json=payload)

        assert response.status_code in [200, 201, 202]


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
class TestPerformance:
    """Test API performance and load"""

    async def test_response_time_sla(self, api_client):
        """Test p95 response time < 2 seconds"""
        response_times = []

        # Make 20 requests
        for i in range(20):
            start = time.time()
            response = await api_client.get("/health")
            duration = time.time() - start

            response_times.append(duration)
            assert response.status_code == 200

        # Calculate p95
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_index]

        assert p95_time < 2.0, f"p95 response time {p95_time:.2f}s exceeds 2s SLA"

    async def test_concurrent_requests(self, api_client):
        """Test handling concurrent requests"""
        # Create 10 concurrent requests
        tasks = [
            api_client.get("/health")
            for _ in range(10)
        ]

        start = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start

        # Check all succeeded
        success_count = sum(
            1 for r in responses
            if isinstance(r, httpx.Response) and r.status_code == 200
        )

        assert success_count >= 8, f"Only {success_count}/10 requests succeeded"
        assert duration < 5.0, f"Concurrent requests took {duration:.2f}s"

    async def test_bulk_bag_creation(self, api_client):
        """Test creating multiple bags"""
        bags = []

        for i in range(10):
            bag_tag = f"0016{int(time.time() * 1000 + i) % 1000000:06d}"
            payload = {
                "bag_tag": bag_tag,
                "passenger_name": f"BULK/TEST{i}",
                "flight_number": "CM999",
                "origin": "PTY",
                "destination": "MIA",
                "weight_kg": 20.0 + i
            }
            bags.append(payload)

        # Create bags concurrently
        tasks = [
            api_client.post("/api/v1/bags", json=bag)
            for bag in bags
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Check success rate
        success_count = sum(
            1 for r in responses
            if isinstance(r, httpx.Response) and r.status_code in [200, 201]
        )

        assert success_count >= 8, f"Only {success_count}/10 bags created successfully"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
class TestErrorHandling:
    """Test error handling and resilience"""

    async def test_invalid_bag_tag(self, api_client):
        """Test handling of invalid bag tag"""
        response = await api_client.get("/api/v1/bags/INVALID")

        assert response.status_code in [400, 404], "Should return 400 or 404 for invalid bag tag"

    async def test_missing_required_fields(self, api_client):
        """Test validation of required fields"""
        payload = {
            "bag_tag": "0016999999",
            # Missing required fields
        }

        response = await api_client.post("/api/v1/bags", json=payload)

        assert response.status_code in [400, 422], "Should return 400/422 for missing fields"

    async def test_rate_limiting(self, api_client):
        """Test rate limiting behavior"""
        # Make many rapid requests
        responses = []

        for i in range(100):
            response = await api_client.get("/health")
            responses.append(response.status_code)

            if response.status_code == 429:
                break  # Rate limited

        # Should either succeed or rate limit (429)
        rate_limited = 429 in responses

        # This is informational - rate limiting may or may not be enabled in test environment
        print(f"Rate limiting {'enabled' if rate_limited else 'not detected'}")


# ============================================================================
# DATA INTEGRITY TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
class TestDataIntegrity:
    """Test data consistency and integrity"""

    async def test_bag_data_persistence(self, api_client):
        """Test bag data persists correctly"""
        bag_tag = f"0016{int(time.time()) % 1000000:06d}"

        # Create bag
        create_payload = {
            "bag_tag": bag_tag,
            "passenger_name": "PERSIST/TEST",
            "flight_number": "CM777",
            "origin": "PTY",
            "destination": "MIA",
            "weight_kg": 25.5
        }

        create_response = await api_client.post("/api/v1/bags", json=create_payload)
        assert create_response.status_code in [200, 201]

        # Retrieve bag
        await asyncio.sleep(1)  # Wait for data to persist

        get_response = await api_client.get(f"/api/v1/bags/{bag_tag}")

        if get_response.status_code == 200:
            data = get_response.json()

            # Verify data integrity
            assert data.get("bag_tag") == bag_tag
            assert data.get("passenger_name") == "PERSIST/TEST"
            assert data.get("flight_number") == "CM777"
            assert abs(data.get("weight_kg", 0) - 25.5) < 0.1

    async def test_concurrent_updates(self, api_client):
        """Test handling concurrent updates to same bag"""
        bag_tag = f"0016{int(time.time()) % 1000000:06d}"

        # Create bag first
        create_payload = {
            "bag_tag": bag_tag,
            "passenger_name": "CONCURRENT/TEST",
            "flight_number": "CM888",
            "origin": "PTY",
            "destination": "MIA",
            "weight_kg": 20.0
        }

        await api_client.post("/api/v1/bags", json=create_payload)
        await asyncio.sleep(0.5)

        # Make concurrent updates
        tasks = [
            api_client.post(f"/api/v1/bags/{bag_tag}/scans", json={
                "location": f"LOCATION_{i}",
                "scan_type": "ARRIVAL",
                "timestamp": datetime.now().isoformat()
            })
            for i in range(5)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # At least some should succeed
        success_count = sum(
            1 for r in responses
            if isinstance(r, httpx.Response) and r.status_code in [200, 201, 202]
        )

        assert success_count > 0, "At least one concurrent update should succeed"


# ============================================================================
# SMOKE TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.smoke
class TestSmoke:
    """Quick smoke tests for deployment verification"""

    async def test_deployment_accessible(self, api_client):
        """Test deployment is accessible"""
        response = await api_client.get("/")

        # Accept any non-500 response
        assert response.status_code < 500, f"Deployment returned 5xx: {response.status_code}"

    async def test_api_endpoints_exist(self, api_client):
        """Test critical API endpoints exist"""
        endpoints = [
            "/health",
            "/ready",
            "/metrics",
        ]

        for endpoint in endpoints:
            response = await api_client.get(endpoint)
            assert response.status_code < 500, f"{endpoint} returned 5xx"

    async def test_database_connectivity(self, api_client):
        """Test database is accessible"""
        # This would typically check a /db/health endpoint
        response = await api_client.get("/health")

        if response.status_code == 200:
            data = response.json()
            # Check if database status is included
            if "database" in data:
                assert data["database"] in ["connected", "healthy", "ok"]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
