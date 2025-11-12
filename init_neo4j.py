"""
Initialize Neo4j indexes and constraints
"""
from neo4j import GraphDatabase
from loguru import logger
import os
from dotenv import load_dotenv
import time

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def init_neo4j():
    """Initialize Neo4j constraints and indexes"""

    # Wait for Neo4j to be fully ready
    logger.info("Waiting for Neo4j to be ready...")
    time.sleep(10)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        logger.info("Creating Neo4j constraints and indexes...")

        # Create constraints
        try:
            session.run("""
                CREATE CONSTRAINT bag_tag_unique IF NOT EXISTS
                FOR (b:Baggage) REQUIRE b.bag_tag IS UNIQUE
            """)
            logger.info("✓ Created unique constraint on Baggage.bag_tag")
        except Exception as e:
            logger.warning(f"Constraint may already exist: {e}")

        try:
            session.run("""
                CREATE CONSTRAINT event_id_unique IF NOT EXISTS
                FOR (s:ScanEvent) REQUIRE s.event_id IS UNIQUE
            """)
            logger.info("✓ Created unique constraint on ScanEvent.event_id")
        except Exception as e:
            logger.warning(f"Constraint may already exist: {e}")

        # Create indexes
        try:
            session.run("""
                CREATE INDEX bag_tag_index IF NOT EXISTS
                FOR (b:Baggage) ON (b.bag_tag)
            """)
            logger.info("✓ Created index on Baggage.bag_tag")
        except Exception as e:
            logger.warning(f"Index may already exist: {e}")

        try:
            session.run("""
                CREATE INDEX scan_timestamp_index IF NOT EXISTS
                FOR (s:ScanEvent) ON (s.timestamp)
            """)
            logger.info("✓ Created index on ScanEvent.timestamp")
        except Exception as e:
            logger.warning(f"Index may already exist: {e}")

    driver.close()
    logger.info("✅ Neo4j initialization complete!")

if __name__ == "__main__":
    init_neo4j()
