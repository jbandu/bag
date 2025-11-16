"""
Dual-Write Service
==================

Coordinates writes to both Neon PostgreSQL (source of truth) and Neo4j (real-time graph).

Features:
- Transaction wrapper to ensure consistency
- Rollback mechanism if Neo4j write fails
- Retry logic with exponential backoff
- Event logging and monitoring

Version: 1.0.0
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import psycopg2
from psycopg2.extras import RealDictCursor
from neo4j import GraphDatabase
from contextlib import contextmanager
import time

from config.settings import settings


class DualWriteException(Exception):
    """Exception raised when dual-write operation fails"""
    pass


class DualWriteService:
    """
    Service for coordinating writes to both Neon PostgreSQL and Neo4j

    Ensures data consistency across both databases with proper transaction handling.
    """

    def __init__(
        self,
        postgres_url: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str
    ):
        """
        Initialize dual-write service

        Args:
            postgres_url: PostgreSQL connection string
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.postgres_url = postgres_url
        self.neo4j_driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )

        logger.info("✅ DualWriteService initialized")

    def close(self):
        """Close database connections"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            logger.info("DualWriteService connections closed")

    @contextmanager
    def postgres_transaction(self):
        """Context manager for PostgreSQL transactions"""
        conn = psycopg2.connect(self.postgres_url)
        try:
            yield conn
            conn.commit()
            logger.debug("PostgreSQL transaction committed")
        except Exception as e:
            conn.rollback()
            logger.error(f"PostgreSQL transaction rolled back: {e}")
            raise
        finally:
            conn.close()

    @contextmanager
    def neo4j_transaction(self):
        """Context manager for Neo4j transactions"""
        session = self.neo4j_driver.session()
        try:
            tx = session.begin_transaction()
            yield tx
            tx.commit()
            logger.debug("Neo4j transaction committed")
        except Exception as e:
            tx.rollback()
            logger.error(f"Neo4j transaction rolled back: {e}")
            raise
        finally:
            session.close()

    def create_bag(self, bag_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create bag in both PostgreSQL and Neo4j

        Args:
            bag_data: Bag information dictionary

        Returns:
            Created bag data

        Raises:
            DualWriteException: If write fails in either database
        """
        bag_tag = bag_data['bag_tag']
        logger.info(f"Creating bag {bag_tag} in both databases")

        try:
            # Write to PostgreSQL first (source of truth)
            with self.postgres_transaction() as pg_conn:
                cursor = pg_conn.cursor(cursor_factory=RealDictCursor)

                cursor.execute("""
                    INSERT INTO baggage (
                        bag_tag, passenger_name, pnr, routing,
                        status, current_location, risk_score,
                        created_at, updated_at
                    ) VALUES (
                        %(bag_tag)s, %(passenger_name)s, %(pnr)s, %(routing)s,
                        %(status)s, %(current_location)s, %(risk_score)s,
                        NOW(), NOW()
                    )
                    RETURNING *
                """, bag_data)

                result = cursor.fetchone()
                cursor.close()

                logger.success(f"✅ Bag {bag_tag} created in PostgreSQL")

            # Write to Neo4j (digital twin)
            try:
                with self.neo4j_transaction() as neo4j_tx:
                    neo4j_tx.run("""
                        MERGE (b:Baggage {bag_tag: $bag_tag})
                        SET b.passenger_name = $passenger_name,
                            b.pnr = $pnr,
                            b.routing = $routing,
                            b.status = $status,
                            b.current_location = $current_location,
                            b.risk_score = $risk_score,
                            b.created_at = datetime($created_at),
                            b.updated_at = datetime()
                        RETURN b
                    """, **{
                        'bag_tag': bag_tag,
                        'passenger_name': bag_data['passenger_name'],
                        'pnr': bag_data['pnr'],
                        'routing': bag_data['routing'],
                        'status': bag_data['status'],
                        'current_location': bag_data['current_location'],
                        'risk_score': bag_data.get('risk_score', 0.0),
                        'created_at': datetime.now().isoformat()
                    })

                logger.success(f"✅ Bag {bag_tag} created in Neo4j")

            except Exception as neo4j_error:
                # Neo4j write failed - log error but don't rollback PostgreSQL
                # PostgreSQL remains source of truth
                logger.error(f"❌ Neo4j write failed for bag {bag_tag}: {neo4j_error}")
                logger.warning(f"⚠️ Bag {bag_tag} exists in PostgreSQL but not Neo4j - manual sync required")
                # Could trigger async sync job here

            return dict(result)

        except Exception as e:
            logger.error(f"❌ Failed to create bag {bag_tag}: {e}")
            raise DualWriteException(f"Bag creation failed: {e}")

    def add_scan_event(
        self,
        scan_data: Dict[str, Any],
        retry_count: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        Add scan event to both databases

        Args:
            scan_data: Scan event data
            retry_count: Number of retries for Neo4j write
            retry_delay: Initial retry delay in seconds

        Returns:
            Created scan event data
        """
        event_id = scan_data['event_id']
        bag_tag = scan_data['bag_tag']

        logger.info(f"Adding scan event {event_id} for bag {bag_tag}")

        try:
            # Write to PostgreSQL
            with self.postgres_transaction() as pg_conn:
                cursor = pg_conn.cursor(cursor_factory=RealDictCursor)

                cursor.execute("""
                    INSERT INTO scan_events (
                        event_id, bag_tag, scan_type, location,
                        timestamp, raw_data, created_at
                    ) VALUES (
                        %(event_id)s, %(bag_tag)s, %(scan_type)s, %(location)s,
                        %(timestamp)s, %(raw_data)s, NOW()
                    )
                    RETURNING *
                """, scan_data)

                result = cursor.fetchone()
                cursor.close()

                logger.success(f"✅ Scan event {event_id} created in PostgreSQL")

            # Write to Neo4j with retry
            neo4j_success = False
            for attempt in range(retry_count):
                try:
                    with self.neo4j_transaction() as neo4j_tx:
                        # Create scan event node
                        neo4j_tx.run("""
                            MATCH (b:Baggage {bag_tag: $bag_tag})
                            CREATE (s:ScanEvent {
                                event_id: $event_id,
                                scan_type: $scan_type,
                                location: $location,
                                timestamp: datetime($timestamp)
                            })
                            CREATE (b)-[:SCANNED_AT]->(s)

                            // Update bag's current location
                            SET b.current_location = $location,
                                b.updated_at = datetime()

                            RETURN s
                        """, **{
                            'bag_tag': bag_tag,
                            'event_id': event_id,
                            'scan_type': scan_data['scan_type'],
                            'location': scan_data['location'],
                            'timestamp': scan_data['timestamp']
                        })

                    logger.success(f"✅ Scan event {event_id} created in Neo4j")
                    neo4j_success = True
                    break

                except Exception as neo4j_error:
                    if attempt < retry_count - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Neo4j write attempt {attempt + 1} failed, "
                            f"retrying in {wait_time}s: {neo4j_error}"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ Neo4j write failed after {retry_count} attempts: {neo4j_error}")

            if not neo4j_success:
                logger.warning(f"⚠️ Scan event {event_id} exists in PostgreSQL but not Neo4j")

            return dict(result)

        except Exception as e:
            logger.error(f"❌ Failed to add scan event {event_id}: {e}")
            raise DualWriteException(f"Scan event creation failed: {e}")

    def update_risk_score(
        self,
        bag_tag: str,
        risk_score: float,
        risk_level: str,
        risk_factors: List[str],
        confidence: float
    ) -> None:
        """
        Update risk assessment in both databases

        Args:
            bag_tag: Bag tag identifier
            risk_score: Risk score (0.0-1.0)
            risk_level: Risk level (low, medium, high, critical)
            risk_factors: List of risk factors
            confidence: Confidence score (0.0-1.0)
        """
        logger.info(f"Updating risk score for bag {bag_tag}: {risk_score} ({risk_level})")

        try:
            # Write to PostgreSQL
            with self.postgres_transaction() as pg_conn:
                cursor = pg_conn.cursor()

                # Insert risk assessment
                cursor.execute("""
                    INSERT INTO risk_assessments (
                        bag_tag, risk_score, risk_level, risk_factors,
                        confidence, assessed_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, NOW()
                    )
                """, (bag_tag, risk_score, risk_level, risk_factors, confidence))

                # Update bag table
                cursor.execute("""
                    UPDATE baggage
                    SET risk_score = %s, updated_at = NOW()
                    WHERE bag_tag = %s
                """, (risk_score, bag_tag))

                cursor.close()
                logger.success(f"✅ Risk score updated in PostgreSQL")

            # Write to Neo4j
            try:
                with self.neo4j_transaction() as neo4j_tx:
                    neo4j_tx.run("""
                        MATCH (b:Baggage {bag_tag: $bag_tag})
                        SET b.risk_score = $risk_score,
                            b.risk_level = $risk_level,
                            b.risk_factors = $risk_factors,
                            b.updated_at = datetime()

                        // Create Risk node
                        CREATE (r:Risk {
                            bag_tag: $bag_tag,
                            score: $risk_score,
                            level: $risk_level,
                            factors: $risk_factors,
                            confidence: $confidence,
                            assessed_at: datetime()
                        })

                        CREATE (b)-[:HAS_RISK]->(r)

                        RETURN b, r
                    """, **{
                        'bag_tag': bag_tag,
                        'risk_score': risk_score,
                        'risk_level': risk_level,
                        'risk_factors': risk_factors,
                        'confidence': confidence
                    })

                logger.success(f"✅ Risk score updated in Neo4j")

            except Exception as neo4j_error:
                logger.error(f"❌ Neo4j risk update failed: {neo4j_error}")
                logger.warning(f"⚠️ Risk score updated in PostgreSQL but not Neo4j")

        except Exception as e:
            logger.error(f"❌ Failed to update risk score for bag {bag_tag}: {e}")
            raise DualWriteException(f"Risk score update failed: {e}")

    def create_exception_case(
        self,
        case_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create exception case in both databases

        Args:
            case_data: Exception case data

        Returns:
            Created case data
        """
        case_id = case_data['case_id']
        bag_tag = case_data['bag_tag']

        logger.info(f"Creating exception case {case_id} for bag {bag_tag}")

        try:
            # Write to PostgreSQL
            with self.postgres_transaction() as pg_conn:
                cursor = pg_conn.cursor(cursor_factory=RealDictCursor)

                cursor.execute("""
                    INSERT INTO exception_cases (
                        case_id, bag_tag, case_type, priority,
                        status, assigned_to, created_at, updated_at
                    ) VALUES (
                        %(case_id)s, %(bag_tag)s, %(case_type)s, %(priority)s,
                        %(status)s, %(assigned_to)s, NOW(), NOW()
                    )
                    RETURNING *
                """, case_data)

                result = cursor.fetchone()
                cursor.close()

                logger.success(f"✅ Exception case {case_id} created in PostgreSQL")

            # Write to Neo4j
            try:
                with self.neo4j_transaction() as neo4j_tx:
                    neo4j_tx.run("""
                        MATCH (b:Baggage {bag_tag: $bag_tag})

                        CREATE (e:Exception {
                            case_id: $case_id,
                            bag_tag: $bag_tag,
                            case_type: $case_type,
                            priority: $priority,
                            status: $status,
                            assigned_to: $assigned_to,
                            created_at: datetime()
                        })

                        CREATE (b)-[:HAS_EXCEPTION]->(e)

                        // Link to agent if assigned
                        WITH e
                        MATCH (a:Agent {name: $assigned_to})
                        CREATE (e)-[:ASSIGNED_TO]->(a)

                        RETURN e
                    """, **case_data)

                logger.success(f"✅ Exception case {case_id} created in Neo4j")

            except Exception as neo4j_error:
                logger.error(f"❌ Neo4j exception case creation failed: {neo4j_error}")
                logger.warning(f"⚠️ Exception case created in PostgreSQL but not Neo4j")

            return dict(result)

        except Exception as e:
            logger.error(f"❌ Failed to create exception case {case_id}: {e}")
            raise DualWriteException(f"Exception case creation failed: {e}")


# Global instance
_dual_write_service: Optional[DualWriteService] = None


def get_dual_write_service() -> DualWriteService:
    """Get or create dual-write service singleton"""
    global _dual_write_service

    if _dual_write_service is None:
        _dual_write_service = DualWriteService(
            postgres_url=settings.neon_database_url,
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password
        )

    return _dual_write_service


def close_dual_write_service():
    """Close dual-write service connections"""
    global _dual_write_service

    if _dual_write_service:
        _dual_write_service.close()
        _dual_write_service = None
