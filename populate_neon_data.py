#!/usr/bin/env python3
"""
Populate Neon PostgreSQL database with sample baggage data
"""
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

NEON_URL = os.getenv("NEON_DATABASE_URL")

print("Populating Neon PostgreSQL with sample data...")
print("=" * 60)

# Connect to Neon
conn = psycopg2.connect(NEON_URL)
cursor = conn.cursor()

# Sample bags
bags = [
    {
        'bag_tag': 'CM12345',
        'passenger_name': 'Alice Johnson',
        'pnr': 'ABC123',
        'routing': 'PTY-MIA-JFK',
        'status': 'checked_in',
        'current_location': 'PTY',
        'risk_score': 0.15
    },
    {
        'bag_tag': 'CM67890',
        'passenger_name': 'Bob Smith',
        'pnr': 'DEF456',
        'routing': 'PTY-MIA-LAX',
        'status': 'in_transit',
        'current_location': 'MIA',
        'risk_score': 0.75
    },
    {
        'bag_tag': 'CM11111',
        'passenger_name': 'Carol White',
        'pnr': 'GHI789',
        'routing': 'PTY-BOG-LIM',
        'status': 'delayed',
        'current_location': 'PTY',
        'risk_score': 0.92
    },
    {
        'bag_tag': 'CM22222',
        'passenger_name': 'David Brown',
        'pnr': 'JKL012',
        'routing': 'PTY-MIA',
        'status': 'loaded',
        'current_location': 'PTY',
        'risk_score': 0.05
    },
]

print("\n📦 Inserting baggage records...")
for bag in bags:
    try:
        cursor.execute("""
            INSERT INTO baggage (
                bag_tag, passenger_name, pnr, routing,
                status, current_location, risk_score
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (bag_tag) DO UPDATE SET
                status = EXCLUDED.status,
                current_location = EXCLUDED.current_location,
                risk_score = EXCLUDED.risk_score,
                updated_at = NOW()
        """, (
            bag['bag_tag'], bag['passenger_name'], bag['pnr'],
            bag['routing'], bag['status'], bag['current_location'],
            bag['risk_score']
        ))
        print(f"  ✅ {bag['bag_tag']}: {bag['passenger_name']} - {bag['status']} - Risk: {bag['risk_score']}")
    except Exception as e:
        print(f"  ⚠️  {bag['bag_tag']}: Error - {e}")

conn.commit()

print("\n🔍 Adding scan events...")
scan_events = [
    {'event_id': 'scan_001', 'bag_tag': 'CM12345', 'scan_type': 'check-in', 'location': 'PTY'},
    {'event_id': 'scan_002', 'bag_tag': 'CM12345', 'scan_type': 'brs', 'location': 'PTY'},
    {'event_id': 'scan_003', 'bag_tag': 'CM67890', 'scan_type': 'check-in', 'location': 'PTY'},
    {'event_id': 'scan_004', 'bag_tag': 'CM67890', 'scan_type': 'sortation', 'location': 'MIA'},
    {'event_id': 'scan_005', 'bag_tag': 'CM11111', 'scan_type': 'check-in', 'location': 'PTY'},
    {'event_id': 'scan_006', 'bag_tag': 'CM22222', 'scan_type': 'check-in', 'location': 'PTY'},
    {'event_id': 'scan_007', 'bag_tag': 'CM22222', 'scan_type': 'load', 'location': 'PTY'},
]

for event in scan_events:
    try:
        cursor.execute("""
            INSERT INTO scan_events (
                event_id, bag_tag, scan_type, location, timestamp
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING
        """, (
            event['event_id'], event['bag_tag'], event['scan_type'],
            event['location'], datetime.now()
        ))
        print(f"  ✅ {event['bag_tag']}: {event['scan_type']} at {event['location']}")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

conn.commit()

print("\n📊 Adding risk assessments...")
risk_assessments = [
    {'bag_tag': 'CM67890', 'risk_score': 0.75, 'risk_level': 'HIGH', 'risk_factors': ['tight_connection', 'weather_delay']},
    {'bag_tag': 'CM11111', 'risk_score': 0.92, 'risk_level': 'CRITICAL', 'risk_factors': ['scan_gap_detected', 'tight_connection', 'high_value']},
]

for assessment in risk_assessments:
    try:
        cursor.execute("""
            INSERT INTO risk_assessments (
                bag_tag, risk_score, risk_level, risk_factors, confidence
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            assessment['bag_tag'], assessment['risk_score'],
            assessment['risk_level'], assessment['risk_factors'], 0.85
        ))
        print(f"  ✅ {assessment['bag_tag']}: Risk {assessment['risk_score']} - {assessment['risk_factors']}")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

conn.commit()

# Verify data
print("\n📈 Verifying data...")
cursor.execute("SELECT COUNT(*) FROM baggage")
bag_count = cursor.fetchone()[0]
print(f"  ✅ Baggage records: {bag_count}")

cursor.execute("SELECT COUNT(*) FROM scan_events")
scan_count = cursor.fetchone()[0]
print(f"  ✅ Scan events: {scan_count}")

cursor.execute("SELECT COUNT(*) FROM risk_assessments")
risk_count = cursor.fetchone()[0]
print(f"  ✅ Risk assessments: {risk_count}")

cursor.close()
conn.close()

print("\n" + "=" * 60)
print("✅ Neon database populated successfully!")
print("\nNext steps:")
print("1. Query Neon database to verify:")
print("   SELECT bag_tag, passenger_name, status, risk_score FROM baggage;")
print("\n2. Your Vercel deployment can now use this data!")
print("   (Don't forget to add NEON_DATABASE_URL to Vercel environment variables)")
