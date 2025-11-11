"""
Test Script for Baggage Operations Platform
Tests the complete workflow with sample scan events
"""
import asyncio
import json
from datetime import datetime
from loguru import logger

from orchestrator.baggage_orchestrator import orchestrator


# Sample scan events
SAMPLE_SCANS = [
    # Normal scan - low risk
    """
    Bag Tag: CM123456
    Scan Type: check_in
    Location: PTY-T1-Counter-05
    Timestamp: 2024-11-11T10:00:00Z
    Flight: CM101
    Status: checked_in
    """,
    
    # Tight connection - high risk
    """
    Bag Tag: CM789012
    Scan Type: sortation
    Location: MIA-T3-BHS-02
    Timestamp: 2024-11-11T14:30:00Z
    Flight: CM202
    Status: in_transit
    Connection Time: 35 minutes
    Next Flight: CM303 (departs 15:05)
    """,
    
    # Missing scan - critical risk
    """
    Bag Tag: CM345678
    Scan Type: load
    Location: JFK-T8-Gate-42
    Timestamp: 2024-11-11T16:45:00Z
    Flight: CM404
    Status: loaded
    Last Scan: 2 hours ago
    Warning: Large scan gap detected
    """,
    
    # SITA Type B message - BTM
    """BTM
FM PTYCMXH
TO MIACMXA
CM101/11NOV.PTY-MIA
-BAGGAGE TRANSFER
.L/15
.C/15
BAG/CM123456/23KG/MIA
BAG/CM234567/21KG/MIA
BAG/CM345678/25KG/MIA
""",
]


async def test_single_scan(scan_data: str, test_name: str):
    """Test a single scan event"""
    logger.info("=" * 80)
    logger.info(f"TEST: {test_name}")
    logger.info("=" * 80)
    
    try:
        result = await orchestrator.process_baggage_event(scan_data)
        
        logger.success("Test completed successfully!")
        logger.info(f"Result: {json.dumps(result, indent=2, default=str)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return None


async def test_all_scenarios():
    """Run all test scenarios"""
    logger.info("\n\n")
    logger.info("*" * 80)
    logger.info("BAGGAGE OPERATIONS PLATFORM - TEST SUITE")
    logger.info("*" * 80)
    logger.info("\n")
    
    results = []
    
    # Test 1: Normal scan
    result1 = await test_single_scan(
        SAMPLE_SCANS[0],
        "Normal Check-in Scan (Low Risk)"
    )
    results.append(('normal_scan', result1))
    await asyncio.sleep(2)
    
    # Test 2: Tight connection
    result2 = await test_single_scan(
        SAMPLE_SCANS[1],
        "Tight Connection Scan (High Risk)"
    )
    results.append(('tight_connection', result2))
    await asyncio.sleep(2)
    
    # Test 3: Missing scan
    result3 = await test_single_scan(
        SAMPLE_SCANS[2],
        "Large Scan Gap (Critical Risk)"
    )
    results.append(('scan_gap', result3))
    await asyncio.sleep(2)
    
    # Test 4: Type B message
    result4 = await test_single_scan(
        SAMPLE_SCANS[3],
        "SITA Type B Message (BTM)"
    )
    results.append(('type_b_message', result4))
    
    # Summary
    logger.info("\n\n")
    logger.info("*" * 80)
    logger.info("TEST SUMMARY")
    logger.info("*" * 80)
    
    for test_name, result in results:
        if result and result['status'] == 'success':
            logger.success(f"✅ {test_name}: PASSED")
        else:
            logger.error(f"❌ {test_name}: FAILED")
    
    logger.info("\n" + "*" * 80)
    logger.info("ALL TESTS COMPLETED")
    logger.info("*" * 80 + "\n")


async def test_api_endpoints():
    """Test API endpoints"""
    import httpx
    
    logger.info("\n" + "=" * 80)
    logger.info("TESTING API ENDPOINTS")
    logger.info("=" * 80)
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Test health check
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                logger.success("✅ Health check: PASSED")
            else:
                logger.error(f"❌ Health check: FAILED ({response.status_code})")
        except Exception as e:
            logger.error(f"❌ Health check: FAILED ({str(e)})")
        
        # Test metrics endpoint
        try:
            response = await client.get(f"{base_url}/metrics")
            if response.status_code == 200:
                logger.success("✅ Metrics endpoint: PASSED")
                metrics = response.json()
                logger.info(f"Metrics: {json.dumps(metrics, indent=2)}")
            else:
                logger.error(f"❌ Metrics endpoint: FAILED ({response.status_code})")
        except Exception as e:
            logger.error(f"❌ Metrics endpoint: FAILED ({str(e)})")
        
        # Test scan event endpoint
        try:
            response = await client.post(
                f"{base_url}/api/v1/scan",
                json={
                    "raw_scan": SAMPLE_SCANS[0],
                    "source": "TEST",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            if response.status_code == 200:
                logger.success("✅ Scan event endpoint: PASSED")
            else:
                logger.error(f"❌ Scan event endpoint: FAILED ({response.status_code})")
        except Exception as e:
            logger.error(f"❌ Scan event endpoint: FAILED ({str(e)})")


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Run tests
    logger.info("\n🚀 Starting Baggage Operations Platform Tests\n")
    
    # Test orchestrator
    asyncio.run(test_all_scenarios())
    
    # Test API (if running)
    logger.info("\n📡 Testing API Endpoints (make sure API server is running)\n")
    try:
        asyncio.run(test_api_endpoints())
    except Exception as e:
        logger.warning(f"API tests skipped: {str(e)}")
    
    logger.info("\n✨ Test suite completed!\n")
