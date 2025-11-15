"""
Test Orchestrator Façade

Simple integration test demonstrating the new orchestrator system.

Run with:
    ENV=development python test_orchestrator.py
"""
import asyncio
from loguru import logger

# Set environment before importing
import os
os.environ['ENV'] = 'development'

from app.orchestrator import initialize_orchestrator, get_orchestrator
from config import config


async def test_scan_event():
    """Test processing a scan event"""
    logger.info("=" * 60)
    logger.info("TEST: Scan Event Processing")
    logger.info("=" * 60)

    orchestrator = get_orchestrator()

    # Test data: simple scan event
    scan_data = {
        "bag_tag": "0001234567",
        "flight_number": "CM101",
        "origin": "PTY",
        "destination": "MIA",
        "location": "PTY",
        "source": "DCS",
        "timestamp": "2024-11-15T10:30:00Z"
    }

    logger.info(f"Processing scan event: {scan_data}")

    result = await orchestrator.process_scan(scan_data)

    logger.info(f"Result: {result}")
    assert result['success'], f"Processing failed: {result.get('errors')}"
    logger.info("✅ Scan event test passed")

    return result


async def test_type_b_message():
    """Test processing a Type B message"""
    logger.info("=" * 60)
    logger.info("TEST: Type B Message Processing")
    logger.info("=" * 60)

    orchestrator = get_orchestrator()

    # Test data: BTM message
    type_b_message = """BTM
CM101/15NOV PTY MIA
.SMITH/JOHN 0001234567 T2P"""

    logger.info(f"Processing Type B message:\n{type_b_message}")

    result = await orchestrator.process_type_b(type_b_message)

    logger.info(f"Result: {result}")
    assert result['success'], f"Processing failed: {result.get('errors')}"
    logger.info("✅ Type B message test passed")

    return result


async def test_text_input():
    """Test processing raw text input"""
    logger.info("=" * 60)
    logger.info("TEST: Raw Text Processing")
    logger.info("=" * 60)

    orchestrator = get_orchestrator()

    # Test data: raw scan string
    raw_text = "0001234567 CM101 PTY"

    logger.info(f"Processing raw text: {raw_text}")

    result = await orchestrator.process_text(raw_text)

    logger.info(f"Result: {result}")
    assert result['success'], f"Processing failed: {result.get('errors')}"
    logger.info("✅ Raw text test passed")

    return result


async def main():
    """Run all tests"""
    logger.info("=" * 70)
    logger.info("ORCHESTRATOR INTEGRATION TESTS")
    logger.info("=" * 70)
    logger.info(f"Environment: {config.environment.value}")
    logger.info(f"Using mocks: {config.use_mocks}")
    logger.info("=" * 70)

    # Initialize orchestrator
    logger.info("Initializing orchestrator...")
    await initialize_orchestrator()
    logger.info("✅ Orchestrator initialized")
    logger.info("")

    try:
        # Run tests
        await test_scan_event()
        logger.info("")

        await test_type_b_message()
        logger.info("")

        await test_text_input()
        logger.info("")

        logger.info("=" * 70)
        logger.info("✅ ALL TESTS PASSED")
        logger.info("=" * 70)

    except AssertionError as e:
        logger.error(f"❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ TEST ERROR: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
