"""
Initialize database schemas for Neon PostgreSQL
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()

# Neon database URL
NEON_URL = os.getenv("NEON_DATABASE_URL")

def init_database():
    """Initialize database tables"""

    # Connect to Neon
    conn = psycopg2.connect(NEON_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    logger.info("Creating database tables...")

    # Baggage table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS baggage (
            id SERIAL PRIMARY KEY,
            bag_tag VARCHAR(20) UNIQUE NOT NULL,
            passenger_name VARCHAR(255),
            pnr VARCHAR(10),
            routing VARCHAR(100),
            status VARCHAR(50),
            current_location VARCHAR(10),
            risk_score FLOAT DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✓ Created baggage table")

    # Scan events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_events (
            id SERIAL PRIMARY KEY,
            event_id VARCHAR(50) UNIQUE NOT NULL,
            bag_tag VARCHAR(20) REFERENCES baggage(bag_tag),
            scan_type VARCHAR(50),
            location VARCHAR(10),
            timestamp TIMESTAMP,
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✓ Created scan_events table")

    # Risk assessments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_assessments (
            id SERIAL PRIMARY KEY,
            bag_tag VARCHAR(20) REFERENCES baggage(bag_tag),
            risk_score FLOAT,
            risk_level VARCHAR(20),
            risk_factors TEXT[],
            confidence FLOAT,
            assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✓ Created risk_assessments table")

    # WorldTracer PIRs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS worldtracer_pirs (
            id SERIAL PRIMARY KEY,
            pir_number VARCHAR(20) UNIQUE NOT NULL,
            bag_tag VARCHAR(20) REFERENCES baggage(bag_tag),
            pir_type VARCHAR(10),
            status VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✓ Created worldtracer_pirs table")

    # Exception cases table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exception_cases (
            id SERIAL PRIMARY KEY,
            case_id VARCHAR(50) UNIQUE NOT NULL,
            bag_tag VARCHAR(20) REFERENCES baggage(bag_tag),
            case_type VARCHAR(50),
            priority VARCHAR(20),
            status VARCHAR(20),
            assigned_to VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✓ Created exception_cases table")

    # Courier dispatches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courier_dispatches (
            id SERIAL PRIMARY KEY,
            dispatch_id VARCHAR(50) UNIQUE NOT NULL,
            bag_tag VARCHAR(20) REFERENCES baggage(bag_tag),
            courier_service VARCHAR(100),
            cost DECIMAL(10, 2),
            status VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✓ Created courier_dispatches table")

    # Passenger notifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passenger_notifications (
            id SERIAL PRIMARY KEY,
            bag_tag VARCHAR(20) REFERENCES baggage(bag_tag),
            channel VARCHAR(20),
            recipient VARCHAR(255),
            message TEXT,
            status VARCHAR(20),
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    logger.info("✓ Created passenger_notifications table")

    # Create indexes for performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bag_tag ON scan_events(bag_tag);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON scan_events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_risk_bag ON risk_assessments(bag_tag);
    """)
    logger.info("✓ Created indexes")

    conn.commit()
    cursor.close()
    conn.close()

    logger.info("✅ Database initialization complete!")

if __name__ == "__main__":
    init_database()
