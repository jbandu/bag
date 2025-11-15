"""
Database Connection Management

Provides unified database connection management for:
- PostgreSQL (Neon) - Operational data
- Neo4j (Aura) - Graph database for digital twins
- Redis (Upstash/Railway) - Cache and metrics

Features:
- Connection pooling with health checks
- Automatic reconnection with exponential backoff
- Circuit breaker pattern for resilience
- Monitoring and metrics
"""

from app.database.postgres import PostgresManager
from app.database.neo4j_manager import Neo4jManager
from app.database.redis_manager import RedisManager
from app.database.health import DatabaseHealthChecker

__all__ = [
    "PostgresManager",
    "Neo4jManager",
    "RedisManager",
    "DatabaseHealthChecker"
]
