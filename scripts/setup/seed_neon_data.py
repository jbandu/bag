#!/usr/bin/env python3
"""
Seed Neon PostgreSQL with sample baggage data for production dashboard
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import random
import os
from dotenv import load_dotenv

load_dotenv()

NEON_URL = os.getenv("NEON_DATABASE_URL")

if not NEON_URL:
    print("❌ NEON_DATABASE_URL not found in .env file")
    exit(1)

print("🚀 Seeding Neon PostgreSQL with sample baggage data...")
print("=" * 70)

# Connect to Neon
conn = psycopg2.connect(NEON_URL)
cursor = conn.cursor()

# Drop and recreate tables to ensure clean schema
print("\n📊 Creating tables...")
cursor.execute("DROP TABLE IF EXISTS scan_events CASCADE")
cursor.execute("DROP TABLE IF EXISTS baggage CASCADE")

cursor.execute("""
CREATE TABLE baggage (
    bag_tag VARCHAR(50) PRIMARY KEY,
    passenger_name VARCHAR(200),
    pnr VARCHAR(20),
    routing VARCHAR(200),
    status VARCHAR(50),
    current_location VARCHAR(10),
    risk_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE scan_events (
    id SERIAL PRIMARY KEY,
    bag_tag VARCHAR(50) REFERENCES baggage(bag_tag),
    scan_type VARCHAR(50),
    location VARCHAR(10),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
print("  ✅ Tables created/verified")

# Sample data - mix of normal, at-risk, and high-risk bags
bags = [
    # Normal bags
    {'bag_tag': 'CM12345', 'passenger_name': 'Alice Johnson', 'pnr': 'ABC123',
     'routing': 'PTY-MIA-JFK', 'status': 'checked_in', 'location': 'PTY', 'risk': 0.15},
    {'bag_tag': 'CM22222', 'passenger_name': 'David Brown', 'pnr': 'JKL012',
     'routing': 'PTY-MIA', 'status': 'loaded', 'location': 'PTY', 'risk': 0.05},
    {'bag_tag': 'CM33333', 'passenger_name': 'Emma Wilson', 'pnr': 'MNO345',
     'routing': 'PTY-BOG', 'status': 'in_transit', 'location': 'BOG', 'risk': 0.12},
    {'bag_tag': 'CM44444', 'passenger_name': 'Frank Martinez', 'pnr': 'PQR678',
     'routing': 'PTY-LIM-SCL', 'status': 'loaded', 'location': 'PTY', 'risk': 0.08},
    {'bag_tag': 'CM55555', 'passenger_name': 'Grace Lee', 'pnr': 'STU901',
     'routing': 'PTY-MIA-ATL', 'status': 'checked_in', 'location': 'PTY', 'risk': 0.18},

    # At-risk bags
    {'bag_tag': 'CM67890', 'passenger_name': 'Bob Smith', 'pnr': 'DEF456',
     'routing': 'PTY-MIA-LAX', 'status': 'delayed', 'location': 'MIA', 'risk': 0.65},
    {'bag_tag': 'CM77777', 'passenger_name': 'Henry Garcia', 'pnr': 'VWX234',
     'routing': 'PTY-MEX-LAX', 'status': 'in_transit', 'location': 'MEX', 'risk': 0.58},
    {'bag_tag': 'CM88888', 'passenger_name': 'Iris Chen', 'pnr': 'YZA567',
     'routing': 'PTY-MIA-ORD', 'status': 'delayed', 'location': 'MIA', 'risk': 0.62},

    # High-risk bags
    {'bag_tag': 'CM11111', 'passenger_name': 'Carol White', 'pnr': 'GHI789',
     'routing': 'PTY-BOG-LIM', 'status': 'mishandled', 'location': 'PTY', 'risk': 0.92},
    {'bag_tag': 'CM99999', 'passenger_name': 'Jack Thompson', 'pnr': 'BCD890',
     'routing': 'PTY-MIA-DFW', 'status': 'missing', 'location': 'UNKNOWN', 'risk': 0.95},
]

# Insert bags
print("\n💼 Inserting baggage records...")
for bag in bags:
    try:
        cursor.execute("""
            INSERT INTO baggage (bag_tag, passenger_name, pnr, routing, status,
                                current_location, risk_score, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (bag_tag) DO UPDATE SET
                status = EXCLUDED.status,
                current_location = EXCLUDED.current_location,
                risk_score = EXCLUDED.risk_score
        """, (bag['bag_tag'], bag['passenger_name'], bag['pnr'], bag['routing'],
              bag['status'], bag['location'], bag['risk'],
              datetime.now() - timedelta(hours=random.randint(1, 48))))

        risk_emoji = "🟢" if bag['risk'] < 0.3 else "🟡" if bag['risk'] < 0.7 else "🔴"
        print(f"  {risk_emoji} {bag['bag_tag']}: {bag['passenger_name']} - Risk: {bag['risk']:.0%} - {bag['status']}")
    except Exception as e:
        print(f"  ⚠️  {bag['bag_tag']}: {e}")

conn.commit()

# Insert scan events
print("\n🔍 Adding scan events...")
scan_events = [
    # CM12345 - Normal journey
    {'bag_tag': 'CM12345', 'scan_type': 'check-in', 'location': 'PTY', 'hours_ago': 2},
    {'bag_tag': 'CM12345', 'scan_type': 'sortation', 'location': 'PTY', 'hours_ago': 1},

    # CM67890 - Delayed
    {'bag_tag': 'CM67890', 'scan_type': 'check-in', 'location': 'PTY', 'hours_ago': 6},
    {'bag_tag': 'CM67890', 'scan_type': 'load', 'location': 'PTY', 'hours_ago': 5},
    {'bag_tag': 'CM67890', 'scan_type': 'arrival', 'location': 'MIA', 'hours_ago': 3},
    {'bag_tag': 'CM67890', 'scan_type': 'sortation', 'location': 'MIA', 'hours_ago': 2},

    # CM11111 - Mishandled
    {'bag_tag': 'CM11111', 'scan_type': 'check-in', 'location': 'PTY', 'hours_ago': 12},
    {'bag_tag': 'CM11111', 'scan_type': 'exception', 'location': 'PTY', 'hours_ago': 11},

    # CM22222 - Normal
    {'bag_tag': 'CM22222', 'scan_type': 'check-in', 'location': 'PTY', 'hours_ago': 1},
    {'bag_tag': 'CM22222', 'scan_type': 'load', 'location': 'PTY', 'hours_ago': 0},
]

for event in scan_events:
    try:
        timestamp = datetime.now() - timedelta(hours=event['hours_ago'])
        cursor.execute("""
            INSERT INTO scan_events (bag_tag, scan_type, location, timestamp)
            VALUES (%s, %s, %s, %s)
        """, (event['bag_tag'], event['scan_type'], event['location'], timestamp))
        print(f"  ✅ {event['bag_tag']}: {event['scan_type']} at {event['location']}")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

conn.commit()

# Show summary
print("\n📊 Database Summary:")
cursor.execute("SELECT COUNT(*) as total FROM baggage")
total_bags = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) as total FROM baggage WHERE risk_score >= 0.7")
high_risk = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) as total FROM scan_events")
total_scans = cursor.fetchone()[0]

print(f"  📦 Total Bags: {total_bags}")
print(f"  🔴 High Risk Bags: {high_risk}")
print(f"  🔍 Scan Events: {total_scans}")

cursor.close()
conn.close()

print("\n" + "=" * 70)
print("✅ Sample data seeded successfully to Neon PostgreSQL!")
print("\nNext steps:")
print("1. Test API: curl https://web-production-3965.up.railway.app/api/v1/bag/CM12345")
print("2. View Dashboard: https://bag-production.up.railway.app")
print("3. Try bag lookup in dashboard with: CM12345, CM67890, CM11111")
