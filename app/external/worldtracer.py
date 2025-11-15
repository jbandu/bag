"""
WorldTracer API Client

Provides integration with SITA WorldTracer for lost baggage tracking.

Features:
- Create PIR (Property Irregularity Report)
- Update baggage status
- Search for missing bags
- Match found bags with PIRs
- Track bag movement across airlines

Supports both mock and production modes via feature flags.
"""
from typing import Optional, Dict, Any, List
from loguru import logger
import httpx
import time
from datetime import datetime


class WorldTracerClient:
    """
    WorldTracer API client for baggage tracking

    Features:
    - PIR creation and management
    - Baggage status updates
    - Cross-airline bag matching
    - Health checks
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        airline_code: str,
        use_mock: bool = False,
        timeout: int = 30
    ):
        """
        Initialize WorldTracer client

        Args:
            api_url: WorldTracer API base URL
            api_key: API authentication key
            airline_code: IATA airline code (e.g., "CM" for Copa)
            use_mock: If True, use mock responses instead of real API
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.airline_code = airline_code
        self.use_mock = use_mock
        self.timeout = timeout

        self._client: Optional[httpx.AsyncClient] = None

        logger.info(f"WorldTracerClient initialized (airline: {airline_code}, mock: {use_mock})")

    async def connect(self):
        """Initialize HTTP client"""
        if self._client:
            logger.warning("WorldTracer client already connected")
            return

        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "X-Airline-Code": self.airline_code,
                "Content-Type": "application/json"
            },
            timeout=self.timeout
        )

        logger.success("✅ WorldTracer client connected")

    async def disconnect(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("WorldTracer client disconnected")

    async def create_pir(
        self,
        bag_tag: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        flight_number: str,
        origin: str,
        destination: str,
        description: str,
        claim_station: str
    ) -> Dict[str, Any]:
        """
        Create Property Irregularity Report (PIR)

        Args:
            bag_tag: Bag tag number (10-digit)
            passenger_name: Passenger full name
            passenger_phone: Contact phone
            passenger_email: Contact email
            flight_number: Flight number (e.g., "CM101")
            origin: Origin airport code
            destination: Destination airport code
            description: Bag description
            claim_station: Where passenger filed claim

        Returns:
            {
                "pir_number": "CMPTY12345",
                "status": "open",
                "created_at": "2024-12-01T10:30:00Z",
                "estimated_delivery": "2024-12-02T14:00:00Z"
            }
        """
        if self.use_mock:
            return await self._create_pir_mock(bag_tag, passenger_name, flight_number, claim_station)

        try:
            response = await self._client.post("/api/v1/pir", json={
                "bag_tag": bag_tag,
                "passenger": {
                    "name": passenger_name,
                    "phone": passenger_phone,
                    "email": passenger_email
                },
                "flight": {
                    "number": flight_number,
                    "origin": origin,
                    "destination": destination
                },
                "description": description,
                "claim_station": claim_station,
                "airline_code": self.airline_code
            })

            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ PIR created: {result.get('pir_number')} for bag {bag_tag}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to create PIR for bag {bag_tag}: {e}")
            raise

    async def _create_pir_mock(
        self,
        bag_tag: str,
        passenger_name: str,
        flight_number: str,
        claim_station: str
    ) -> Dict[str, Any]:
        """Mock PIR creation for testing"""
        pir_number = f"{self.airline_code}{claim_station}{int(time.time()) % 100000:05d}"

        logger.info(f"🎭 MOCK: Created PIR {pir_number} for bag {bag_tag}")

        return {
            "pir_number": pir_number,
            "bag_tag": bag_tag,
            "passenger_name": passenger_name,
            "flight_number": flight_number,
            "claim_station": claim_station,
            "status": "open",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "estimated_delivery": "2024-12-02T14:00:00Z",
            "mock": True
        }

    async def update_bag_status(
        self,
        pir_number: str,
        status: str,
        location: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update bag status in WorldTracer

        Args:
            pir_number: PIR reference number
            status: New status (found, in_transit, delivered, closed)
            location: Current location code
            notes: Update notes

        Returns:
            Updated PIR information
        """
        if self.use_mock:
            return await self._update_bag_status_mock(pir_number, status, location)

        try:
            response = await self._client.patch(f"/api/v1/pir/{pir_number}", json={
                "status": status,
                "location": location,
                "notes": notes,
                "updated_by": self.airline_code
            })

            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ PIR {pir_number} updated to status: {status}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to update PIR {pir_number}: {e}")
            raise

    async def _update_bag_status_mock(
        self,
        pir_number: str,
        status: str,
        location: Optional[str]
    ) -> Dict[str, Any]:
        """Mock status update for testing"""
        logger.info(f"🎭 MOCK: Updated PIR {pir_number} to {status} at {location}")

        return {
            "pir_number": pir_number,
            "status": status,
            "location": location or "PTY",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "mock": True
        }

    async def search_bag(
        self,
        bag_tag: Optional[str] = None,
        pir_number: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search for bag in WorldTracer database

        Args:
            bag_tag: Bag tag to search for
            pir_number: PIR number to search for

        Returns:
            Bag information if found, None otherwise
        """
        if self.use_mock:
            return await self._search_bag_mock(bag_tag, pir_number)

        try:
            params = {}
            if bag_tag:
                params["bag_tag"] = bag_tag
            if pir_number:
                params["pir_number"] = pir_number

            response = await self._client.get("/api/v1/search", params=params)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ Bag found in WorldTracer: {bag_tag or pir_number}")
            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"❌ Failed to search WorldTracer: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ WorldTracer search error: {e}")
            raise

    async def _search_bag_mock(
        self,
        bag_tag: Optional[str],
        pir_number: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Mock bag search for testing"""
        # 70% chance of finding bag in mock mode
        if hash(bag_tag or pir_number or "") % 10 < 7:
            logger.info(f"🎭 MOCK: Bag found: {bag_tag or pir_number}")
            return {
                "bag_tag": bag_tag,
                "pir_number": pir_number or f"CMPTY{int(time.time()) % 100000:05d}",
                "status": "found",
                "location": "MIA",
                "found_at": datetime.utcnow().isoformat() + "Z",
                "mock": True
            }
        else:
            logger.info(f"🎭 MOCK: Bag not found: {bag_tag or pir_number}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """
        Check WorldTracer API health

        Returns:
            {
                "status": "healthy" | "unhealthy",
                "healthy": bool,
                "latency_ms": float,
                "mode": "production" | "mock"
            }
        """
        if self.use_mock:
            return {
                "status": "healthy",
                "healthy": True,
                "latency_ms": 5.0,
                "mode": "mock",
                "message": "Mock mode - no real API connection"
            }

        try:
            if not self._client:
                return {
                    "status": "disconnected",
                    "healthy": False,
                    "error": "Client not connected"
                }

            start = time.time()

            # Ping endpoint
            response = await self._client.get("/api/v1/health")
            response.raise_for_status()

            latency_ms = (time.time() - start) * 1000

            return {
                "status": "healthy",
                "healthy": True,
                "latency_ms": round(latency_ms, 2),
                "mode": "production",
                "api_url": self.api_url
            }

        except Exception as e:
            logger.error(f"WorldTracer health check failed: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e),
                "mode": "production"
            }

    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._client is not None
