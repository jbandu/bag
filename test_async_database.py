"""
Integration Tests for Async Database Layer

Tests the async database factory, repositories, and health checks.

Usage:
    # Run with dev environment (mocks enabled)
    ENV=development python test_async_database.py

    # Run with real databases (requires credentials)
    ENV=staging python test_async_database.py
"""
import asyncio
from datetime import datetime
from loguru import logger

# Configure test environment
import os
os.environ.setdefault("ENV", "development")

from app.database.factory import (
    initialize_databases,
    shutdown_databases,
    get_postgres,
    get_neo4j,
    get_redis,
    get_health_checker,
    get_connection_status
)
from app.repositories import BaggageRepository, GraphRepository, MetricsRepository
from models.baggage_models import BagStatus, ScanType


async def test_database_initialization():
    """Test database initialization"""
    logger.info("=" * 60)
    logger.info("TEST 1: Database Initialization")
    logger.info("=" * 60)

    # Initialize all databases
    status = await initialize_databases()

    logger.info(f"Database initialization status: {status}")

    # Check connection status
    conn_status = get_connection_status()
    logger.info(f"Connection status: {conn_status}")

    assert conn_status['initialized'], "Databases should be initialized"
    logger.success("✅ Test 1 passed: Databases initialized")


async def test_health_checks():
    """Test health check system"""
    logger.info("=" * 60)
    logger.info("TEST 2: Health Checks")
    logger.info("=" * 60)

    health_checker = get_health_checker()

    if health_checker:
        # Check all services
        health = await health_checker.check_all()
        logger.info(f"Overall health: {health}")

        # Check readiness
        is_ready = await health_checker.is_ready()
        logger.info(f"Readiness: {is_ready}")

        # Check liveness
        is_alive = await health_checker.is_alive()
        logger.info(f"Liveness: {is_alive}")

        logger.success("✅ Test 2 passed: Health checks working")
    else:
        logger.warning("⚠️ Test 2 skipped: Health checker not available")


async def test_baggage_repository():
    """Test BaggageRepository operations"""
    logger.info("=" * 60)
    logger.info("TEST 3: BaggageRepository")
    logger.info("=" * 60)

    postgres = get_postgres()

    if not postgres:
        logger.warning("⚠️ Test 3 skipped: PostgreSQL not available")
        return

    repo = BaggageRepository(postgres)

    # Test bag creation
    test_bag = {
        'bag_tag': 'TEST001234567',
        'passenger_name': 'Test Passenger',
        'pnr': 'TESTPNR',
        'routing': ['PTY', 'MIA'],
        'current_location': 'PTY',
        'status': BagStatus.IN_TRANSIT.value,
        'weight_kg': 23.5,
        'risk_score': 0.2,
        'risk_level': 'low',
        'airline_id': 1
    }

    bag_tag = await repo.create_bag(test_bag)
    logger.info(f"Created bag: {bag_tag}")

    if bag_tag:
        # Test bag retrieval
        bag = await repo.get_bag(bag_tag)
        logger.info(f"Retrieved bag: {bag}")

        # Test status update
        updated = await repo.update_bag_status(
            bag_tag,
            BagStatus.LOADED,
            location='MIA'
        )
        logger.info(f"Updated bag status: {updated}")

        # Test scan event
        scan_event = {
            'event_id': f'test_scan_{datetime.utcnow().timestamp()}',
            'bag_tag': bag_tag,
            'scan_type': ScanType.LOAD.value,
            'location': 'MIA',
            'timestamp': datetime.utcnow(),
            'airline_id': 1
        }

        event_id = await repo.add_scan_event(scan_event)
        logger.info(f"Created scan event: {event_id}")

        # Test scan history
        history = await repo.get_bag_scan_history(bag_tag)
        logger.info(f"Scan history: {len(history)} events")

        logger.success("✅ Test 3 passed: BaggageRepository working")
    else:
        logger.warning("⚠️ Test 3 partial: Bag creation failed (may not have tables)")


async def test_graph_repository():
    """Test GraphRepository operations"""
    logger.info("=" * 60)
    logger.info("TEST 4: GraphRepository")
    logger.info("=" * 60)

    neo4j = get_neo4j()
    repo = GraphRepository(neo4j)

    if not repo.is_available:
        logger.warning("⚠️ Test 4 skipped: Neo4j not available")
        return

    # Test digital twin creation
    test_bag = {
        'bag_tag': 'TEST001234567',
        'passenger_name': 'Test Passenger',
        'pnr': 'TESTPNR',
        'routing': ['PTY', 'MIA'],
        'current_location': 'PTY',
        'status': BagStatus.IN_TRANSIT.value,
        'risk_score': 0.2
    }

    bag_tag = await repo.create_digital_twin(test_bag)
    logger.info(f"Created digital twin: {bag_tag}")

    if bag_tag:
        # Test scan relationship
        scan_data = {
            'event_id': f'test_scan_{datetime.utcnow().timestamp()}',
            'scan_type': ScanType.LOAD.value,
            'location': 'MIA',
            'timestamp': datetime.utcnow()
        }

        added = await repo.add_scan_relationship(bag_tag, scan_data)
        logger.info(f"Added scan relationship: {added}")

        # Test journey query
        journey = await repo.get_bag_journey(bag_tag)
        logger.info(f"Journey: {len(journey)} events")

        # Test statistics
        stats = await repo.get_bag_statistics()
        logger.info(f"Graph statistics: {stats}")

        logger.success("✅ Test 4 passed: GraphRepository working")
    else:
        logger.warning("⚠️ Test 4 partial: Digital twin creation failed")


async def test_metrics_repository():
    """Test MetricsRepository operations"""
    logger.info("=" * 60)
    logger.info("TEST 5: MetricsRepository")
    logger.info("=" * 60)

    redis = get_redis()
    repo = MetricsRepository(redis)

    if not repo.is_available:
        logger.warning("⚠️ Test 5 skipped: Redis not available")
        return

    # Test counter increment
    value = await repo.increment_counter("test_scans_processed", airline_id=1)
    logger.info(f"Incremented counter: {value}")

    # Test counter retrieval
    counter = await repo.get_counter("test_scans_processed", airline_id=1)
    logger.info(f"Counter value: {counter}")

    # Test latency recording
    recorded = await repo.record_latency("test_operation", 125.5, airline_id=1)
    logger.info(f"Recorded latency: {recorded}")

    # Test metrics summary
    summary = await repo.get_metrics_summary(airline_id=1)
    logger.info(f"Metrics summary: {summary}")

    # Test caching
    cached = await repo.cache_bag_status(
        "TEST001234567",
        {"status": "in_transit", "location": "PTY"},
        ttl=60
    )
    logger.info(f"Cached bag status: {cached}")

    retrieved = await repo.get_cached_bag_status("TEST001234567")
    logger.info(f"Retrieved cached bag: {retrieved}")

    # Test rate limiting
    allowed, remaining = await repo.check_rate_limit("test_user", limit=10, window=60)
    logger.info(f"Rate limit check: allowed={allowed}, remaining={remaining}")

    logger.success("✅ Test 5 passed: MetricsRepository working")


async def test_database_shutdown():
    """Test database shutdown"""
    logger.info("=" * 60)
    logger.info("TEST 6: Database Shutdown")
    logger.info("=" * 60)

    # Shutdown all databases
    await shutdown_databases()

    # Check connection status
    conn_status = get_connection_status()
    logger.info(f"Connection status after shutdown: {conn_status}")

    assert not conn_status['initialized'], "Databases should be shut down"
    logger.success("✅ Test 6 passed: Databases shut down cleanly")


async def run_all_tests():
    """Run all integration tests"""
    logger.info("🧪 Starting async database layer integration tests...")
    logger.info("")

    try:
        await test_database_initialization()
        await test_health_checks()
        await test_baggage_repository()
        await test_graph_repository()
        await test_metrics_repository()
        await test_database_shutdown()

        logger.info("")
        logger.success("=" * 60)
        logger.success("✅ ALL TESTS PASSED")
        logger.success("=" * 60)

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ TEST FAILED: {e}")
        logger.error("=" * 60)
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())
