"""
Neo4j Connection Manager (Aura)

Provides connection management, health checks, and query execution for Neo4j graph database.
"""
from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional, List, Dict, Any
from loguru import logger
import time


class Neo4jManager:
    """
    Neo4j graph database connection manager

    Features:
    - Connection with retry logic
    - Health checks with latency tracking
    - Cypher query execution
    - Transaction management
    """

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j"
    ):
        """
        Initialize Neo4j manager

        Args:
            uri: Neo4j connection URI (bolt:// or neo4j://)
            user: Username
            password: Password
            database: Database name (default: neo4j)
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database

        self._driver: Optional[AsyncDriver] = None
        self._is_connected = False

        logger.info(f"Neo4jManager initialized (database: {database})")

    async def connect(self):
        """Create Neo4j driver"""
        if self._driver:
            logger.warning("Neo4j driver already exists")
            return

        try:
            logger.info(f"Connecting to Neo4j at {self.uri}...")

            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=10,
                connection_timeout=30,
                max_transaction_retry_time=15
            )

            # Verify connectivity
            await self._driver.verify_connectivity()

            self._is_connected = True
            logger.success(f"✅ Neo4j connected")

        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}")
            raise

    async def disconnect(self):
        """Close Neo4j driver"""
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j driver closed")
            self._is_connected = False

    async def execute_read(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        log_slow_queries: bool = True,
        slow_threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Execute read query

        Args:
            query: Cypher query
            parameters: Query parameters
            log_slow_queries: Log queries exceeding threshold
            slow_threshold: Slow query threshold in seconds

        Returns:
            List of result records
        """
        if not self._driver:
            raise RuntimeError("Neo4j not connected. Call connect() first.")

        start = time.time()
        results = []

        async with self._driver.session(database=self.database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            results = records

        elapsed = time.time() - start

        if log_slow_queries and elapsed > slow_threshold:
            logger.warning(f"Slow Neo4j query ({elapsed:.2f}s): {query[:100]}...")

        return results

    async def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute write query

        Args:
            query: Cypher query
            parameters: Query parameters

        Returns:
            List of result records
        """
        if not self._driver:
            raise RuntimeError("Neo4j not connected. Call connect() first.")

        async with self._driver.session(database=self.database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def load_schema(self, schema_file: str):
        """
        Load Cypher schema from file

        Args:
            schema_file: Path to .cypher file
        """
        logger.info(f"Loading Neo4j schema from {schema_file}...")

        with open(schema_file, 'r') as f:
            schema_content = f.read()

        # Split on semicolons and execute each statement
        statements = [s.strip() for s in schema_content.split(';') if s.strip()]

        async with self._driver.session(database=self.database) as session:
            for i, statement in enumerate(statements, 1):
                # Skip comments and empty lines
                if statement.startswith('//') or not statement:
                    continue

                try:
                    logger.debug(f"Executing statement {i}/{len(statements)}")
                    await session.run(statement)
                except Exception as e:
                    logger.warning(f"Statement {i} failed: {e}")
                    # Continue with next statement

        logger.success(f"✅ Schema loaded ({len(statements)} statements)")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Neo4j health

        Returns:
            Health status dictionary
        """
        if not self._driver:
            return {
                "status": "disconnected",
                "healthy": False,
                "error": "No driver"
            }

        try:
            start = time.time()

            # Test query
            async with self._driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 AS test")
                record = await result.single()

                # Get database info
                db_info = await session.run("CALL dbms.components() YIELD versions RETURN versions[0] AS version")
                version_record = await db_info.single()
                version = version_record["version"] if version_record else "unknown"

            latency_ms = (time.time() - start) * 1000

            return {
                "status": "healthy",
                "healthy": True,
                "latency_ms": round(latency_ms, 2),
                "version": version,
                "database": self.database
            }

        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e)
            }

    @property
    def is_connected(self) -> bool:
        """Check if Neo4j is connected"""
        return self._is_connected and self._driver is not None
