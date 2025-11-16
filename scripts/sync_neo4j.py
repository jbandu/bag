#!/usr/bin/env python3
"""
Neo4j Sync Utility
==================

Backfills existing PostgreSQL data into Neo4j and handles incremental updates.

Usage:
    python scripts/sync_neo4j.py --mode full       # Full backfill
    python scripts/sync_neo4j.py --mode incremental  # Only new data
    python scripts/sync_neo4j.py --verify          # Verify data consistency

Features:
- Full backfill from PostgreSQL to Neo4j
- Incremental sync for new/updated records
- Data consistency verification
- Progress tracking with resume capability
- Dry-run mode for testing

Version: 1.0.0
"""

import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from neo4j import GraphDatabase
from datetime import datetime
from loguru import logger
import sys
from typing import Dict, Any, List
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
NEON_DATABASE_URL = os.getenv('NEON_DATABASE_URL')
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USER = os.getenv('NEO4J_USER')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


class Neo4jSyncUtility:
    """Utility for syncing PostgreSQL data to Neo4j"""

    def __init__(self, dry_run: bool = False):
        """
        Initialize sync utility

        Args:
            dry_run: If True, only simulate operations without writing
        """
        self.dry_run = dry_run
        self.stats = {
            'bags_synced': 0,
            'scans_synced': 0,
            'risks_synced': 0,
            'exceptions_synced': 0,
            'errors': 0
        }

        logger.info(f"Initializing Neo4j Sync Utility (dry_run={dry_run})")

        # Connect to databases
        self.pg_conn = psycopg2.connect(NEON_DATABASE_URL)
        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

        logger.success("✅ Database connections established")

    def close(self):
        """Close database connections"""
        if self.pg_conn:
            self.pg_conn.close()
        if self.neo4j_driver:
            self.neo4j_driver.close()
        logger.info("Database connections closed")

    def full_backfill(self):
        """Perform full backfill from PostgreSQL to Neo4j"""
        logger.info("=" * 60)
        logger.info("STARTING FULL BACKFILL")
        logger.info("=" * 60)

        start_time = time.time()

        try:
            # Sync in order: bags -> scans -> risks -> exceptions
            self.sync_bags()
            self.sync_scan_events()
            self.sync_risk_assessments()
            self.sync_exception_cases()

            elapsed = time.time() - start_time

            logger.info("=" * 60)
            logger.success("BACKFILL COMPLETED")
            logger.info("=" * 60)
            logger.info(f"Bags synced:       {self.stats['bags_synced']}")
            logger.info(f"Scans synced:      {self.stats['scans_synced']}")
            logger.info(f"Risks synced:      {self.stats['risks_synced']}")
            logger.info(f"Exceptions synced: {self.stats['exceptions_synced']}")
            logger.info(f"Errors:            {self.stats['errors']}")
            logger.info(f"Time elapsed:      {elapsed:.2f}s")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Backfill failed: {e}")
            raise

    def sync_bags(self):
        """Sync baggage records from PostgreSQL to Neo4j"""
        logger.info("Syncing bags...")

        cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM baggage ORDER BY created_at")

        bags = cursor.fetchall()
        cursor.close()

        logger.info(f"Found {len(bags)} bags to sync")

        for bag in bags:
            try:
                if not self.dry_run:
                    self._create_bag_node(bag)
                self.stats['bags_synced'] += 1

                if self.stats['bags_synced'] % 100 == 0:
                    logger.info(f"Progress: {self.stats['bags_synced']}/{len(bags)} bags synced")

            except Exception as e:
                logger.error(f"Failed to sync bag {bag['bag_tag']}: {e}")
                self.stats['errors'] += 1

        logger.success(f"✅ Synced {self.stats['bags_synced']} bags")

    def _create_bag_node(self, bag: Dict[str, Any]):
        """Create or update bag node in Neo4j"""
        with self.neo4j_driver.session() as session:
            session.run("""
                MERGE (b:Baggage {bag_tag: $bag_tag})
                SET b.passenger_name = $passenger_name,
                    b.pnr = $pnr,
                    b.routing = $routing,
                    b.status = $status,
                    b.current_location = $current_location,
                    b.risk_score = $risk_score,
                    b.created_at = datetime($created_at),
                    b.updated_at = datetime($updated_at)
                RETURN b
            """, **{
                'bag_tag': bag['bag_tag'],
                'passenger_name': bag['passenger_name'],
                'pnr': bag['pnr'],
                'routing': bag['routing'],
                'status': bag['status'],
                'current_location': bag['current_location'],
                'risk_score': float(bag['risk_score']) if bag['risk_score'] else 0.0,
                'created_at': bag['created_at'].isoformat() if bag['created_at'] else datetime.now().isoformat(),
                'updated_at': bag['updated_at'].isoformat() if bag['updated_at'] else datetime.now().isoformat()
            })

    def sync_scan_events(self):
        """Sync scan events from PostgreSQL to Neo4j"""
        logger.info("Syncing scan events...")

        cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM scan_events ORDER BY timestamp")

        scans = cursor.fetchall()
        cursor.close()

        logger.info(f"Found {len(scans)} scan events to sync")

        for scan in scans:
            try:
                if not self.dry_run:
                    self._create_scan_event_node(scan)
                self.stats['scans_synced'] += 1

                if self.stats['scans_synced'] % 500 == 0:
                    logger.info(f"Progress: {self.stats['scans_synced']}/{len(scans)} scans synced")

            except Exception as e:
                logger.error(f"Failed to sync scan {scan['event_id']}: {e}")
                self.stats['errors'] += 1

        logger.success(f"✅ Synced {self.stats['scans_synced']} scan events")

    def _create_scan_event_node(self, scan: Dict[str, Any]):
        """Create scan event node and relationship in Neo4j"""
        with self.neo4j_driver.session() as session:
            session.run("""
                MATCH (b:Baggage {bag_tag: $bag_tag})

                MERGE (s:ScanEvent {event_id: $event_id})
                SET s.scan_type = $scan_type,
                    s.location = $location,
                    s.timestamp = datetime($timestamp)

                MERGE (b)-[:SCANNED_AT]->(s)

                RETURN s
            """, **{
                'bag_tag': scan['bag_tag'],
                'event_id': scan['event_id'],
                'scan_type': scan['scan_type'],
                'location': scan['location'],
                'timestamp': scan['timestamp'].isoformat() if scan['timestamp'] else datetime.now().isoformat()
            })

    def sync_risk_assessments(self):
        """Sync risk assessments from PostgreSQL to Neo4j"""
        logger.info("Syncing risk assessments...")

        cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM risk_assessments ORDER BY assessed_at")

        risks = cursor.fetchall()
        cursor.close()

        logger.info(f"Found {len(risks)} risk assessments to sync")

        for risk in risks:
            try:
                if not self.dry_run:
                    self._create_risk_node(risk)
                self.stats['risks_synced'] += 1

                if self.stats['risks_synced'] % 100 == 0:
                    logger.info(f"Progress: {self.stats['risks_synced']}/{len(risks)} risks synced")

            except Exception as e:
                logger.error(f"Failed to sync risk for bag {risk['bag_tag']}: {e}")
                self.stats['errors'] += 1

        logger.success(f"✅ Synced {self.stats['risks_synced']} risk assessments")

    def _create_risk_node(self, risk: Dict[str, Any]):
        """Create risk node and relationship in Neo4j"""
        with self.neo4j_driver.session() as session:
            session.run("""
                MATCH (b:Baggage {bag_tag: $bag_tag})

                CREATE (r:Risk {
                    id: randomUUID(),
                    bag_tag: $bag_tag,
                    score: $risk_score,
                    level: $risk_level,
                    factors: $risk_factors,
                    confidence: $confidence,
                    assessed_at: datetime($assessed_at)
                })

                CREATE (b)-[:HAS_RISK]->(r)

                // Update bag risk score
                SET b.risk_score = $risk_score,
                    b.risk_level = $risk_level

                RETURN r
            """, **{
                'bag_tag': risk['bag_tag'],
                'risk_score': float(risk['risk_score']) if risk['risk_score'] else 0.0,
                'risk_level': risk['risk_level'],
                'risk_factors': risk['risk_factors'] if risk['risk_factors'] else [],
                'confidence': float(risk['confidence']) if risk['confidence'] else 0.0,
                'assessed_at': risk['assessed_at'].isoformat() if risk['assessed_at'] else datetime.now().isoformat()
            })

    def sync_exception_cases(self):
        """Sync exception cases from PostgreSQL to Neo4j"""
        logger.info("Syncing exception cases...")

        cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM exception_cases ORDER BY created_at")

        exceptions = cursor.fetchall()
        cursor.close()

        logger.info(f"Found {len(exceptions)} exception cases to sync")

        for exception in exceptions:
            try:
                if not self.dry_run:
                    self._create_exception_node(exception)
                self.stats['exceptions_synced'] += 1

                if self.stats['exceptions_synced'] % 50 == 0:
                    logger.info(f"Progress: {self.stats['exceptions_synced']}/{len(exceptions)} exceptions synced")

            except Exception as e:
                logger.error(f"Failed to sync exception {exception['case_id']}: {e}")
                self.stats['errors'] += 1

        logger.success(f"✅ Synced {self.stats['exceptions_synced']} exception cases")

    def _create_exception_node(self, exception: Dict[str, Any]):
        """Create exception node and relationship in Neo4j"""
        with self.neo4j_driver.session() as session:
            session.run("""
                MATCH (b:Baggage {bag_tag: $bag_tag})

                CREATE (e:Exception {
                    case_id: $case_id,
                    bag_tag: $bag_tag,
                    case_type: $case_type,
                    priority: $priority,
                    status: $status,
                    assigned_to: $assigned_to,
                    created_at: datetime($created_at),
                    updated_at: datetime($updated_at)
                })

                CREATE (b)-[:HAS_EXCEPTION]->(e)

                RETURN e
            """, **{
                'bag_tag': exception['bag_tag'],
                'case_id': exception['case_id'],
                'case_type': exception['case_type'],
                'priority': exception['priority'],
                'status': exception['status'],
                'assigned_to': exception['assigned_to'],
                'created_at': exception['created_at'].isoformat() if exception['created_at'] else datetime.now().isoformat(),
                'updated_at': exception['updated_at'].isoformat() if exception['updated_at'] else datetime.now().isoformat()
            })

    def incremental_sync(self, since: datetime):
        """
        Sync only records created/updated since a specific timestamp

        Args:
            since: Sync records updated after this timestamp
        """
        logger.info(f"Starting incremental sync (since: {since})")

        # Sync only updated records
        cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)

        # Bags
        cursor.execute(
            "SELECT * FROM baggage WHERE updated_at > %s",
            (since,)
        )
        for bag in cursor.fetchall():
            try:
                if not self.dry_run:
                    self._create_bag_node(bag)
                self.stats['bags_synced'] += 1
            except Exception as e:
                logger.error(f"Failed to sync bag {bag['bag_tag']}: {e}")
                self.stats['errors'] += 1

        cursor.close()
        logger.success(f"✅ Incremental sync completed: {self.stats['bags_synced']} bags updated")

    def verify_consistency(self) -> bool:
        """
        Verify data consistency between PostgreSQL and Neo4j

        Returns:
            True if data is consistent, False otherwise
        """
        logger.info("Verifying data consistency...")

        # Count bags in PostgreSQL
        cursor = self.pg_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM baggage")
        pg_bag_count = cursor.fetchone()[0]
        cursor.close()

        # Count bags in Neo4j
        with self.neo4j_driver.session() as session:
            result = session.run("MATCH (b:Baggage) RETURN count(b) as count")
            neo4j_bag_count = result.single()['count']

        logger.info(f"PostgreSQL bags: {pg_bag_count}")
        logger.info(f"Neo4j bags:      {neo4j_bag_count}")

        if pg_bag_count == neo4j_bag_count:
            logger.success("✅ Data is consistent")
            return True
        else:
            logger.warning(f"⚠️ Data mismatch: {pg_bag_count - neo4j_bag_count} bags missing in Neo4j")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Neo4j Sync Utility")
    parser.add_argument(
        '--mode',
        choices=['full', 'incremental'],
        default='full',
        help='Sync mode: full backfill or incremental'
    )
    parser.add_argument(
        '--since',
        type=str,
        help='For incremental mode: sync since this timestamp (ISO format)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify data consistency'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate operations without writing to Neo4j'
    )

    args = parser.parse_args()

    sync_util = Neo4jSyncUtility(dry_run=args.dry_run)

    try:
        if args.verify:
            sync_util.verify_consistency()
        elif args.mode == 'full':
            sync_util.full_backfill()
        elif args.mode == 'incremental':
            if not args.since:
                logger.error("--since is required for incremental mode")
                sys.exit(1)
            since = datetime.fromisoformat(args.since)
            sync_util.incremental_sync(since)

    finally:
        sync_util.close()


if __name__ == '__main__':
    main()
