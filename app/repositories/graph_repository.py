"""
Graph Repository (Neo4j)

Handles all Neo4j graph database operations:
- Digital twin creation and updates
- Scan relationship tracking
- Journey path queries
- Risk propagation analysis

Features:
- Async operations
- Cypher query optimization
- Graceful degradation when Neo4j unavailable
- Relationship tracking for bag journey
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.database.neo4j_manager import Neo4jManager
from models.baggage_models import BagStatus, ScanType


class GraphRepository:
    """
    Repository for Neo4j graph operations

    Manages digital twin representations and bag journey tracking.
    Gracefully degrades if Neo4j is unavailable.
    """

    def __init__(self, neo4j: Optional[Neo4jManager]):
        """
        Initialize graph repository

        Args:
            neo4j: Neo4j manager (can be None for graceful degradation)
        """
        self.neo4j = neo4j
        self._available = neo4j is not None

    @property
    def is_available(self) -> bool:
        """Check if Neo4j is available"""
        return self._available and self.neo4j is not None and self.neo4j.is_connected

    # ========================================================================
    # DIGITAL TWIN OPERATIONS
    # ========================================================================

    async def create_digital_twin(self, bag_data: Dict[str, Any]) -> Optional[str]:
        """
        Create digital twin node for bag

        Args:
            bag_data: Bag information

        Returns:
            bag_tag if successful, None if Neo4j unavailable
        """
        if not self.is_available:
            logger.debug("Neo4j unavailable - skipping digital twin creation")
            return None

        try:
            query = """
                MERGE (b:Baggage {bag_tag: $bag_tag})
                ON CREATE SET
                    b.passenger_name = $passenger_name,
                    b.pnr = $pnr,
                    b.routing = $routing,
                    b.current_location = $current_location,
                    b.status = $status,
                    b.risk_score = $risk_score,
                    b.created_at = datetime($created_at),
                    b.updated_at = datetime()
                ON MATCH SET
                    b.passenger_name = $passenger_name,
                    b.current_location = $current_location,
                    b.status = $status,
                    b.risk_score = $risk_score,
                    b.updated_at = datetime()
                RETURN b.bag_tag AS bag_tag
            """

            params = {
                "bag_tag": bag_data.get('bag_tag'),
                "passenger_name": bag_data.get('passenger_name'),
                "pnr": bag_data.get('pnr'),
                "routing": bag_data.get('routing', []),
                "current_location": bag_data.get('current_location'),
                "status": bag_data.get('status', BagStatus.IN_TRANSIT.value),
                "risk_score": bag_data.get('risk_score', 0.0),
                "created_at": bag_data.get('created_at', datetime.utcnow()).isoformat()
            }

            results = await self.neo4j.execute_write(query, params)

            if results and len(results) > 0:
                bag_tag = results[0].get('bag_tag')
                logger.info(f"Digital twin created/updated: {bag_tag}")
                return bag_tag

            return None

        except Exception as e:
            logger.error(f"Failed to create digital twin: {e}")
            return None

    async def update_bag_location(
        self,
        bag_tag: str,
        location: str,
        status: str
    ) -> bool:
        """
        Update bag location and status in graph

        Args:
            bag_tag: Bag tag number
            location: New location
            status: New status

        Returns:
            True if successful
        """
        if not self.is_available:
            logger.debug("Neo4j unavailable - skipping location update")
            return False

        try:
            query = """
                MATCH (b:Baggage {bag_tag: $bag_tag})
                SET b.current_location = $location,
                    b.status = $status,
                    b.updated_at = datetime()
                RETURN b.bag_tag AS bag_tag
            """

            params = {
                "bag_tag": bag_tag,
                "location": location,
                "status": status
            }

            results = await self.neo4j.execute_write(query, params)

            if results and len(results) > 0:
                logger.info(f"Updated location for bag {bag_tag}: {location}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to update bag location: {e}")
            return False

    async def update_risk_score(
        self,
        bag_tag: str,
        risk_score: float,
        risk_factors: List[str]
    ) -> bool:
        """
        Update risk score in graph

        Args:
            bag_tag: Bag tag number
            risk_score: Risk score (0.0 - 1.0)
            risk_factors: List of risk factors

        Returns:
            True if successful
        """
        if not self.is_available:
            logger.debug("Neo4j unavailable - skipping risk score update")
            return False

        try:
            query = """
                MATCH (b:Baggage {bag_tag: $bag_tag})
                SET b.risk_score = $risk_score,
                    b.risk_factors = $risk_factors,
                    b.updated_at = datetime()
                RETURN b.bag_tag AS bag_tag
            """

            params = {
                "bag_tag": bag_tag,
                "risk_score": risk_score,
                "risk_factors": risk_factors
            }

            results = await self.neo4j.execute_write(query, params)
            return results is not None and len(results) > 0

        except Exception as e:
            logger.error(f"Failed to update risk score: {e}")
            return False

    # ========================================================================
    # SCAN EVENT RELATIONSHIPS
    # ========================================================================

    async def add_scan_relationship(
        self,
        bag_tag: str,
        scan_data: Dict[str, Any]
    ) -> bool:
        """
        Add scan event and create relationship to bag

        Args:
            bag_tag: Bag tag number
            scan_data: Scan event data

        Returns:
            True if successful
        """
        if not self.is_available:
            logger.debug("Neo4j unavailable - skipping scan relationship")
            return False

        try:
            query = """
                MATCH (b:Baggage {bag_tag: $bag_tag})
                CREATE (s:ScanEvent {
                    event_id: $event_id,
                    scan_type: $scan_type,
                    location: $location,
                    timestamp: datetime($timestamp)
                })
                CREATE (b)-[:SCANNED_AT {
                    timestamp: datetime($timestamp),
                    scan_type: $scan_type
                }]->(s)
                RETURN s.event_id AS event_id
            """

            params = {
                "bag_tag": bag_tag,
                "event_id": scan_data.get('event_id'),
                "scan_type": scan_data.get('scan_type'),
                "location": scan_data.get('location'),
                "timestamp": scan_data.get('timestamp', datetime.utcnow()).isoformat()
            }

            results = await self.neo4j.execute_write(query, params)

            if results and len(results) > 0:
                logger.info(f"Scan relationship created for bag {bag_tag}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to add scan relationship: {e}")
            return False

    # ========================================================================
    # JOURNEY QUERIES
    # ========================================================================

    async def get_bag_journey(self, bag_tag: str) -> List[Dict[str, Any]]:
        """
        Get complete journey history for bag

        Args:
            bag_tag: Bag tag number

        Returns:
            List of scan events in chronological order
        """
        if not self.is_available:
            logger.debug("Neo4j unavailable - cannot query journey")
            return []

        try:
            query = """
                MATCH (b:Baggage {bag_tag: $bag_tag})-[r:SCANNED_AT]->(s:ScanEvent)
                RETURN s.location AS location,
                       s.scan_type AS scan_type,
                       s.timestamp AS timestamp,
                       s.event_id AS event_id
                ORDER BY s.timestamp
            """

            params = {"bag_tag": bag_tag}

            results = await self.neo4j.execute_read(query, params)

            journey = []
            for record in results:
                journey.append({
                    "location": record.get('location'),
                    "scan_type": record.get('scan_type'),
                    "timestamp": record.get('timestamp'),
                    "event_id": record.get('event_id')
                })

            logger.info(f"Retrieved journey for bag {bag_tag}: {len(journey)} events")
            return journey

        except Exception as e:
            logger.error(f"Failed to get bag journey: {e}")
            return []

    async def find_bags_at_location(
        self,
        location: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all bags currently at location

        Args:
            location: Airport or facility code
            status: Filter by status (optional)

        Returns:
            List of bags at location
        """
        if not self.is_available:
            logger.debug("Neo4j unavailable - cannot query location")
            return []

        try:
            if status:
                query = """
                    MATCH (b:Baggage {current_location: $location, status: $status})
                    RETURN b.bag_tag AS bag_tag,
                           b.passenger_name AS passenger_name,
                           b.pnr AS pnr,
                           b.status AS status,
                           b.risk_score AS risk_score,
                           b.updated_at AS updated_at
                    ORDER BY b.updated_at DESC
                """
                params = {"location": location, "status": status}
            else:
                query = """
                    MATCH (b:Baggage {current_location: $location})
                    RETURN b.bag_tag AS bag_tag,
                           b.passenger_name AS passenger_name,
                           b.pnr AS pnr,
                           b.status AS status,
                           b.risk_score AS risk_score,
                           b.updated_at AS updated_at
                    ORDER BY b.updated_at DESC
                """
                params = {"location": location}

            results = await self.neo4j.execute_read(query, params)

            bags = []
            for record in results:
                bags.append({
                    "bag_tag": record.get('bag_tag'),
                    "passenger_name": record.get('passenger_name'),
                    "pnr": record.get('pnr'),
                    "status": record.get('status'),
                    "risk_score": record.get('risk_score'),
                    "updated_at": record.get('updated_at')
                })

            return bags

        except Exception as e:
            logger.error(f"Failed to find bags at location: {e}")
            return []

    async def find_high_risk_bags(
        self,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find high-risk bags in graph

        Args:
            threshold: Minimum risk score

        Returns:
            List of high-risk bags
        """
        if not self.is_available:
            logger.debug("Neo4j unavailable - cannot query high-risk bags")
            return []

        try:
            query = """
                MATCH (b:Baggage)
                WHERE b.risk_score >= $threshold
                  AND b.status IN ['in_transit', 'delayed', 'mishandled']
                RETURN b.bag_tag AS bag_tag,
                       b.passenger_name AS passenger_name,
                       b.pnr AS pnr,
                       b.current_location AS current_location,
                       b.status AS status,
                       b.risk_score AS risk_score,
                       b.risk_factors AS risk_factors
                ORDER BY b.risk_score DESC
                LIMIT 100
            """

            params = {"threshold": threshold}

            results = await self.neo4j.execute_read(query, params)

            bags = []
            for record in results:
                bags.append({
                    "bag_tag": record.get('bag_tag'),
                    "passenger_name": record.get('passenger_name'),
                    "pnr": record.get('pnr'),
                    "current_location": record.get('current_location'),
                    "status": record.get('status'),
                    "risk_score": record.get('risk_score'),
                    "risk_factors": record.get('risk_factors', [])
                })

            return bags

        except Exception as e:
            logger.error(f"Failed to find high-risk bags: {e}")
            return []

    # ========================================================================
    # ANALYTICS QUERIES
    # ========================================================================

    async def get_bag_statistics(self) -> Dict[str, Any]:
        """
        Get overall bag statistics from graph

        Returns:
            Statistics dict
        """
        if not self.is_available:
            logger.debug("Neo4j unavailable - cannot query statistics")
            return {}

        try:
            query = """
                MATCH (b:Baggage)
                RETURN count(b) AS total_bags,
                       avg(b.risk_score) AS avg_risk_score,
                       count(CASE WHEN b.status = 'in_transit' THEN 1 END) AS in_transit,
                       count(CASE WHEN b.status = 'delayed' THEN 1 END) AS delayed,
                       count(CASE WHEN b.status = 'mishandled' THEN 1 END) AS mishandled,
                       count(CASE WHEN b.risk_score >= 0.7 THEN 1 END) AS high_risk
            """

            results = await self.neo4j.execute_read(query, {})

            if results and len(results) > 0:
                record = results[0]
                return {
                    "total_bags": record.get('total_bags', 0),
                    "avg_risk_score": round(record.get('avg_risk_score', 0.0), 3),
                    "in_transit": record.get('in_transit', 0),
                    "delayed": record.get('delayed', 0),
                    "mishandled": record.get('mishandled', 0),
                    "high_risk": record.get('high_risk', 0)
                }

            return {}

        except Exception as e:
            logger.error(f"Failed to get bag statistics: {e}")
            return {}

    async def delete_bag(self, bag_tag: str) -> bool:
        """
        Delete bag and all related scan events

        Args:
            bag_tag: Bag tag number

        Returns:
            True if successful
        """
        if not self.is_available:
            logger.debug("Neo4j unavailable - cannot delete bag")
            return False

        try:
            query = """
                MATCH (b:Baggage {bag_tag: $bag_tag})
                OPTIONAL MATCH (b)-[r:SCANNED_AT]->(s:ScanEvent)
                DELETE r, s, b
                RETURN count(b) AS deleted_count
            """

            params = {"bag_tag": bag_tag}

            results = await self.neo4j.execute_write(query, params)

            if results and len(results) > 0:
                deleted_count = results[0].get('deleted_count', 0)
                if deleted_count > 0:
                    logger.info(f"Deleted bag {bag_tag} from graph")
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete bag: {e}")
            return False
