"""
Semantic API Gateway Demo
==========================

Demonstrates the unified gateway eliminating API friction across 7 systems.

Shows:
- ONE interface for all external systems
- Circuit breaking
- Rate limiting  
- Caching
- Intelligent retries
- Monitoring

Version: 1.0.0
"""

import asyncio
import sys
sys.path.insert(0, '/home/user/bag')

from datetime import datetime
from gateway.semantic_gateway import SemanticAPIGateway
from gateway.adapters import (
    DCSAdapter, BHSAdapter, WorldTracerAdapter,
    TypeBAdapter, XMLAdapter, CourierAdapter,
    NotificationAdapter, AdapterConfig
)
from models.canonical_bag import CanonicalBag, AirportCode, FlightNumber, BagType


async def main():
    print("=" * 80)
    print("SEMANTIC API GATEWAY - ELIMINATING API FRICTION")
    print("=" * 80)
    print()

    # ========================================================================
    # 1. INITIALIZE GATEWAY
    # ========================================================================

    print("1. INITIALIZING GATEWAY")
    print("-" * 80)

    gateway = SemanticAPIGateway()

    # Register all adapters
    adapters = {
        "worldtracer": WorldTracerAdapter(AdapterConfig(
            base_url="https://worldtracer.sita.aero/api",
            auth_type="api_key",
            api_key="WT_API_KEY_HERE"
        )),
        "dcs": DCSAdapter(AdapterConfig(
            base_url="https://dcs.amadeus.com/api",
            auth_type="oauth",
            oauth_token="DCS_TOKEN_HERE"
        )),
        "bhs": BHSAdapter(AdapterConfig(
            base_url="https://bhs.vendor.com/api",
            auth_type="api_key",
            api_key="BHS_KEY_HERE"
        )),
        "typeb": TypeBAdapter(AdapterConfig(
            base_url="sita://typeb",
            auth_type="certificate",
            certificate_path="/path/to/cert.pem"
        )),
        "xml": XMLAdapter(AdapterConfig(
            base_url="https://baggagexml.iata.org/api",
            auth_type="basic",
            username="xml_user",
            password="xml_pass"
        )),
        "courier": CourierAdapter(AdapterConfig(
            base_url="https://api.fedex.com",
            auth_type="api_key",
            api_key="FEDEX_KEY_HERE"
        )),
        "notification": NotificationAdapter(AdapterConfig(
            base_url="https://api.twilio.com",
            auth_type="basic",
            username="twilio_sid",
            password="twilio_token"
        ))
    }

    for name, adapter in adapters.items():
        gateway.register_adapter(name, adapter)

    print(f"✓ Gateway initialized with {len(adapters)} adapters")
    print()

    # ========================================================================
    # 2. CREATE SAMPLE BAG
    # ========================================================================

    print("2. CREATING SAMPLE BAG")
    print("-" * 80)

    sample_bag = CanonicalBag(
        bag_tag="0291234567",
        passenger_name="SMITH/JOHN MR",
        pnr="ABC123",
        origin=AirportCode(iata_code="LAX"),
        destination=AirportCode(iata_code="JFK"),
        outbound_flight=FlightNumber(airline_code="AA", flight_number="123"),
        bag_type=BagType.CHECKED,
        bag_sequence=1,
        total_bags=2
    )

    print(f"✓ Created bag: {sample_bag.get_summary()}")
    print()

    # ========================================================================
    # 3. SEMANTIC OPERATIONS - No need to know which API!
    # ========================================================================

    print("3. MAKING SEMANTIC API CALLS")
    print("-" * 80)
    print()

    # Operation 1: Create PIR in WorldTracer
    print("→ Creating PIR in WorldTracer...")
    pir_response = await gateway.create_pir(
        bag=sample_bag,
        irregularity_type="DELAYED",
        description="Bag missed connection at LAX"
    )

    if pir_response.success:
        print(f"  ✓ PIR created: {pir_response.data.get('ohd_reference')}")
        print(f"    Latency: {pir_response.latency_ms:.1f}ms")
        print(f"    Source: {pir_response.source}")
    else:
        print(f"  ✗ Failed: {pir_response.error}")
    print()

    # Operation 2: Get passenger PNR from DCS
    print("→ Getting passenger PNR from DCS...")
    pnr_response = await gateway.get_passenger_pnr(pnr="ABC123")

    if pnr_response.success:
        print(f"  ✓ PNR retrieved: {pnr_response.data.get('passenger', {}).get('surname')}")
        print(f"    Cached: {pnr_response.cached}")
        print(f"    Latency: {pnr_response.latency_ms:.1f}ms")
    print()

    # Operation 3: Get bag location from BHS
    print("→ Getting bag location from BHS...")
    location_response = await gateway.get_bag_location(bag_tag="0291234567")

    if location_response.success:
        print(f"  ✓ Location: {location_response.data.get('location')}")
        print(f"    Latency: {location_response.latency_ms:.1f}ms")
    print()

    # Operation 4: Create courier shipment
    print("→ Creating courier shipment...")
    shipment_response = await gateway.create_shipment(
        courier="fedex",
        origin="LAX",
        destination="123 Main St, New York, NY",
        recipient={"name": "JOHN SMITH", "phone": "+1234567890"},
        bag_tag="0291234567"
    )

    if shipment_response.success:
        print(f"  ✓ Shipment created: {shipment_response.data.get('tracking_number')}")
        print(f"    Label: {shipment_response.data.get('label_url')}")
        print(f"    Latency: {shipment_response.latency_ms:.1f}ms")
    print()

    # Operation 5: Send SMS notification
    print("→ Sending SMS notification...")
    sms_response = await gateway.send_sms(
        phone="+12025551234",
        message="Your bag is delayed. Tracking: FedEx123456",
        priority="HIGH"
    )

    if sms_response.success:
        print(f"  ✓ SMS sent: {sms_response.data.get('message_id')}")
        print(f"    Status: {sms_response.data.get('status')}")
        print(f"    Latency: {sms_response.latency_ms:.1f}ms")
    print()

    # ========================================================================
    # 4. DEMONSTRATE CACHING
    # ========================================================================

    print("4. DEMONSTRATING CACHING")
    print("-" * 80)

    print("→ First call to get PNR (cache miss)...")
    response1 = await gateway.get_passenger_pnr(pnr="ABC123")
    print(f"  Cached: {response1.cached}, Latency: {response1.latency_ms:.1f}ms")

    print("→ Second call to get PNR (cache hit!)...")
    response2 = await gateway.get_passenger_pnr(pnr="ABC123")
    print(f"  Cached: {response2.cached}, Latency: {response2.latency_ms:.1f}ms")
    print(f"  ✓ Latency reduced by {response1.latency_ms - response2.latency_ms:.1f}ms with caching!")
    print()

    # ========================================================================
    # 5. MONITORING & OBSERVABILITY
    # ========================================================================

    print("5. GATEWAY HEALTH & STATISTICS")
    print("-" * 80)

    health = gateway.get_health()
    print(f"Status: {health['status'].upper()}")
    print(f"Total Requests: {health['total_requests']}")
    print(f"Successful: {health['successful']} ({health['success_rate']:.1%})")
    print(f"Failed: {health['failed']}")
    print(f"Cache Hit Rate: {health['cache_hit_rate']:.1%}")
    print(f"Circuit Breakers: {health['circuit_breakers']['closed']} closed, {health['circuit_breakers']['open']} open")
    print()

    # Detailed stats for each adapter
    print("ADAPTER STATISTICS:")
    print("-" * 80)

    for adapter_name in ["worldtracer", "dcs", "bhs", "courier", "notification"]:
        adapter_health = gateway.get_adapter_health(adapter_name)
        cb_stats = adapter_health['circuit_breaker']

        print(f"\n{adapter_name.upper()}:")
        print(f"  Circuit State: {cb_stats['state']}")
        print(f"  Requests: {cb_stats['total_requests']} (success rate: {cb_stats['success_rate']:.1%})")

        if adapter_health['rate_limiter']:
            rl_stats = adapter_health['rate_limiter']
            print(f"  Rate Limit: {rl_stats['allowed']}/{rl_stats['max_requests']} per {rl_stats['window_seconds']}s")
            print(f"  Current Tokens: {rl_stats.get('current_tokens', 'N/A')}")

        if adapter_health['cache']:
            cache_stats = adapter_health['cache']
            print(f"  Cache: {cache_stats['size']}/{cache_stats['max_size']} entries ({cache_stats['hit_rate']:.1%} hit rate)")

    print()

    # ========================================================================
    # 6. SUMMARY
    # ========================================================================

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("✓ ONE unified interface for ALL external systems")
    print("✓ Agents call semantic operations, not REST endpoints")
    print("✓ Gateway handles:")
    print("    • Authentication (OAuth, API keys, certificates)")
    print("    • Rate limiting (per-system policies)")
    print("    • Circuit breaking (isolate failures)")
    print("    • Caching (reduce latency & API costs)")
    print("    • Retries (intelligent backoff)")
    print("    • Data transformation (JSON, XML, Type B)")
    print()
    print("BEFORE: 8 agents × 7 systems = 56 integration points")
    print("AFTER:  8 agents × 1 gateway = 8 integration points")
    print()
    print("Result: 85% reduction in API friction!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
