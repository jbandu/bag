#!/usr/bin/env python3
"""
Create sample baggage data for testing
"""
from utils.database import neo4j_db, redis_cache
from datetime import datetime
import json

print("Creating sample baggage data...")
print("=" * 60)

# Sample bags with different scenarios
bags = [
    {
        'bag_tag': 'CM12345',
        'status': 'checked_in',
        'current_location': 'PTY',
        'passenger_name': 'Alice Johnson',
        'pnr': 'ABC123',
        'routing': 'PTY-MIA-JFK',
        'risk_score': 0.15,
        'created_at': datetime.now()
    },
    {
        'bag_tag': 'CM67890',
        'status': 'in_transit',
        'current_location': 'MIA',
        'passenger_name': 'Bob Smith',
        'pnr': 'DEF456',
        'routing': 'PTY-MIA-LAX',
        'risk_score': 0.75,
        'created_at': datetime.now()
    },
    {
        'bag_tag': 'CM11111',
        'status': 'delayed',
        'current_location': 'PTY',
        'passenger_name': 'Carol White',
        'pnr': 'GHI789',
        'routing': 'PTY-BOG-LIM',
        'risk_score': 0.92,
        'created_at': datetime.now()
    },
    {
        'bag_tag': 'CM22222',
        'status': 'loaded',
        'current_location': 'PTY',
        'passenger_name': 'David Brown',
        'pnr': 'JKL012',
        'routing': 'PTY-MIA',
        'risk_score': 0.05,
        'created_at': datetime.now()
    },
]

# Create digital twins in Neo4j
print("\n📊 Creating digital twins in Neo4j...")
for bag in bags:
    try:
        neo4j_db.create_digital_twin(bag)
        print(f"  ✅ {bag['bag_tag']}: {bag['passenger_name']} - Risk: {bag['risk_score']} - {bag['status']}")
    except Exception as e:
        print(f"  ⚠️  {bag['bag_tag']}: Already exists or error: {e}")

# Add scan events
print("\n🔍 Adding scan events...")
scan_events = [
    {'bag_tag': 'CM12345', 'event_id': 'scan_001', 'scan_type': 'check-in', 'location': 'PTY', 'timestamp': datetime.now()},
    {'bag_tag': 'CM67890', 'event_id': 'scan_002', 'scan_type': 'sortation', 'location': 'MIA', 'timestamp': datetime.now()},
    {'bag_tag': 'CM11111', 'event_id': 'scan_003', 'scan_type': 'check-in', 'location': 'PTY', 'timestamp': datetime.now()},
    {'bag_tag': 'CM22222', 'event_id': 'scan_004', 'scan_type': 'load', 'location': 'PTY', 'timestamp': datetime.now()},
]

for event in scan_events:
    try:
        bag_tag = event.pop('bag_tag')
        neo4j_db.add_scan_event(bag_tag, event)
        print(f"  ✅ {bag_tag}: {event['scan_type']} at {event['location']}")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

# Cache in Redis
print("\n💾 Caching in Redis...")
for bag in bags:
    bag_status = {
        'bag_tag': bag['bag_tag'],
        'status': bag['status'],
        'location': bag['current_location'],
        'risk_score': bag['risk_score'],
        'passenger': bag['passenger_name'],
        'cached_at': datetime.now().isoformat()
    }
    redis_cache.cache_bag_status(bag['bag_tag'], bag_status, ttl=3600)
    print(f"  ✅ {bag['bag_tag']}: Cached for 1 hour")

# Initialize metrics
print("\n📈 Initializing metrics...")
redis_cache.increment_metric('bags_processed')
redis_cache.increment_metric('bags_processed')
redis_cache.increment_metric('bags_processed')
redis_cache.increment_metric('bags_processed')
redis_cache.increment_metric('scans_processed')
redis_cache.increment_metric('scans_processed')
redis_cache.increment_metric('scans_processed')
redis_cache.increment_metric('scans_processed')
redis_cache.increment_metric('high_risk_bags_detected')
redis_cache.increment_metric('high_risk_bags_detected')

print(f"  ✅ Bags processed: {redis_cache.get_metric('bags_processed')}")
print(f"  ✅ Scans processed: {redis_cache.get_metric('scans_processed')}")
print(f"  ✅ High risk bags: {redis_cache.get_metric('high_risk_bags_detected')}")

print("\n" + "=" * 60)
print("✅ Sample data created successfully!")
print("\nNext steps:")
print("1. Open Neo4j Browser: http://localhost:7474")
print("   Query: MATCH (b:Baggage)-[:SCANNED_AT]->(s) RETURN b, s")
print("\n2. Test Redis CLI:")
print("   docker exec -it redis redis-cli")
print("   KEYS *")
print("\n3. Test API:")
print("   curl http://localhost:8000/metrics")
