"""
Data Access Layer - Repository Pattern

Provides high-level repositories for all database operations:
- BaggageRepository - PostgreSQL operations (bags, scans, risks)
- GraphRepository - Neo4j operations (digital twins, journey tracking)
- MetricsRepository - Redis operations (caching, metrics)

All repositories support:
- Async operations with connection pooling
- Retry logic with exponential backoff
- Graceful degradation when services unavailable
- Query performance logging

Usage:
    from app.repositories import BaggageRepository, GraphRepository, MetricsRepository
    from app.database.factory import get_postgres, get_neo4j, get_redis

    # Initialize repositories
    baggage_repo = BaggageRepository(get_postgres())
    graph_repo = GraphRepository(get_neo4j())
    metrics_repo = MetricsRepository(get_redis())

    # Use repositories
    bag = await baggage_repo.get_bag("0001234567")
    journey = await graph_repo.get_bag_journey("0001234567")
    await metrics_repo.increment_counter("scans_processed")
"""

from app.repositories.baggage_repository import BaggageRepository
from app.repositories.graph_repository import GraphRepository
from app.repositories.metrics_repository import MetricsRepository

__all__ = [
    "BaggageRepository",
    "GraphRepository",
    "MetricsRepository"
]
