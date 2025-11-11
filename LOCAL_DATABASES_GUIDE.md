# Local Databases Guide - Neo4j & Redis

Complete guide to working with your local Neo4j and Redis databases for the Baggage Operations Platform.

---

## 🗄️ Neo4j (Graph Database) - Digital Twin

Neo4j stores the "digital twin" of your baggage - the journey of each bag through scan events.

### Access Neo4j Browser

**URL**: http://localhost:7474

**Credentials**:
- Username: `neo4j`
- Password: `baggageops123`

### What's Stored in Neo4j

**Nodes:**
1. **Baggage** - Each bag with properties:
   - `bag_tag` (unique identifier like "CM123456")
   - `status` (checked_in, in_transit, loaded, etc.)
   - `current_location` (airport code like "PTY")
   - `risk_score` (0.0 to 1.0)
   - `passenger_name`, `pnr`, `routing`

2. **ScanEvent** - Each scan with properties:
   - `event_id` (unique)
   - `scan_type` (check-in, sortation, load, offload, etc.)
   - `location` (airport/station code)
   - `timestamp`

**Relationships:**
- `Baggage -[:SCANNED_AT]-> ScanEvent`

### Useful Cypher Queries

**View all baggage:**
```cypher
MATCH (b:Baggage)
RETURN b
LIMIT 25;
```

**View a specific bag's journey:**
```cypher
MATCH (b:Baggage {bag_tag: 'CM123456'})-[:SCANNED_AT]->(s:ScanEvent)
RETURN b, s
ORDER BY s.timestamp;
```

**Find high-risk bags:**
```cypher
MATCH (b:Baggage)
WHERE b.risk_score > 0.7
RETURN b.bag_tag, b.risk_score, b.current_location, b.status
ORDER BY b.risk_score DESC;
```

**View scan timeline for all bags:**
```cypher
MATCH (b:Baggage)-[:SCANNED_AT]->(s:ScanEvent)
RETURN b.bag_tag, s.scan_type, s.location, s.timestamp
ORDER BY s.timestamp DESC
LIMIT 50;
```

**Count bags by status:**
```cypher
MATCH (b:Baggage)
RETURN b.status, count(*) as count
ORDER BY count DESC;
```

**Find bags with no recent scans (potential issues):**
```cypher
MATCH (b:Baggage)-[:SCANNED_AT]->(s:ScanEvent)
WITH b, max(s.timestamp) as last_scan
WHERE datetime(last_scan) < datetime() - duration({hours: 2})
RETURN b.bag_tag, b.current_location, last_scan;
```

**Delete all data (reset database):**
```cypher
MATCH (n)
DETACH DELETE n;
```

### Using Neo4j from Python

```python
from utils.database import neo4j_db

# Create a digital twin for a bag
bag_data = {
    'bag_tag': 'CM123456',
    'status': 'checked_in',
    'current_location': 'PTY',
    'passenger_name': 'John Doe',
    'pnr': 'ABC123',
    'routing': 'PTY-MIA-JFK',
    'risk_score': 0.2,
    'created_at': datetime.now()
}
neo4j_db.create_digital_twin(bag_data)

# Add a scan event
scan_data = {
    'event_id': 'scan_001',
    'scan_type': 'check-in',
    'location': 'PTY',
    'timestamp': datetime.now()
}
neo4j_db.add_scan_event('CM123456', scan_data)

# Get bag journey
journey = neo4j_db.get_bag_journey('CM123456')
print(journey)

# Update risk score
neo4j_db.update_risk_score('CM123456', 0.85, ['connection_time_tight', 'weather_delay'])
```

### Neo4j CLI Access

```bash
# Access Neo4j shell
docker exec -it neo4j cypher-shell -u neo4j -p baggageops123

# Run a query
MATCH (n) RETURN count(n);

# Exit
:exit
```

### Neo4j Data Persistence

Data is stored in a Docker volume: `neo4j_data`

**View volume:**
```bash
docker volume inspect neo4j_data
```

**Backup:**
```bash
docker exec neo4j neo4j-admin dump --database=neo4j --to=/data/backup.dump
docker cp neo4j:/data/backup.dump ./neo4j_backup_$(date +%Y%m%d).dump
```

**Restore:**
```bash
docker cp ./neo4j_backup.dump neo4j:/data/
docker exec neo4j neo4j-admin load --from=/data/neo4j_backup.dump --database=neo4j --force
```

---

## 🔴 Redis (Cache & Metrics)

Redis is used for:
1. **Caching** - Fast bag status lookups
2. **Metrics** - Real-time operational counters

### Access Redis

**No web UI by default**, but you can use CLI or install RedisInsight.

### Redis CLI Access

```bash
# Connect to Redis
docker exec -it redis redis-cli

# Or directly:
redis-cli -h localhost -p 6379
```

### Common Redis Commands

**View all keys:**
```redis
KEYS *
```

**Get a specific bag status:**
```redis
GET bag:CM123456
```

**View metrics:**
```redis
GET metric:bags_processed
GET metric:scans_processed
GET metric:high_risk_bags_detected
GET metric:pirs_created
```

**Increment a metric:**
```redis
INCR metric:bags_processed
```

**Set a bag status with expiry (1 hour):**
```redis
SETEX bag:CM123456 3600 '{"status":"in_transit","location":"MIA","risk":0.3}'
```

**Delete a key:**
```redis
DEL bag:CM123456
```

**Clear all data:**
```redis
FLUSHALL
```

**View all metrics:**
```redis
KEYS metric:*
```

**Get info about Redis:**
```redis
INFO
```

**Exit:**
```redis
EXIT
```

### Using Redis from Python

```python
from utils.database import redis_cache
import json

# Cache bag status
bag_status = {
    'bag_tag': 'CM123456',
    'status': 'in_transit',
    'location': 'MIA',
    'risk_score': 0.3,
    'last_scan': '2024-11-11T12:00:00Z'
}
redis_cache.cache_bag_status('CM123456', bag_status, ttl=3600)

# Get cached status
cached = redis_cache.get_bag_status('CM123456')
print(cached)

# Increment metrics
redis_cache.increment_metric('bags_processed')
redis_cache.increment_metric('scans_processed')
redis_cache.increment_metric('high_risk_bags_detected')

# Get metric value
total_bags = redis_cache.get_metric('bags_processed')
print(f"Total bags processed: {total_bags}")
```

### Install RedisInsight (Optional GUI)

RedisInsight is a free GUI for Redis:

```bash
# Download and run RedisInsight
docker run -d --name redisinsight \
  -p 8001:8001 \
  -v redisinsight:/db \
  redislabs/redisinsight:latest

# Access at: http://localhost:8001
# Connect to: localhost:6379
```

### Redis Data Persistence

Redis is configured with **AOF (Append Only File)** persistence.

Data is stored in Docker volume: `redis_data`

**View volume:**
```bash
docker volume inspect redis_data
```

**Backup:**
```bash
docker exec redis redis-cli SAVE
docker cp redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

**Restore:**
```bash
docker stop redis
docker cp ./redis_backup.rdb redis:/data/dump.rdb
docker start redis
```

---

## 🚀 Quick Start Examples

### Test Neo4j Connection

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "baggageops123")
)

with driver.session() as session:
    result = session.run("RETURN 'Hello Neo4j!' as message")
    print(result.single()['message'])

driver.close()
```

### Test Redis Connection

```python
import redis

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Set a value
r.set('test_key', 'Hello Redis!')

# Get it back
value = r.get('test_key')
print(value)

# Delete it
r.delete('test_key')
```

### Create Sample Data

Run this to create sample baggage data for testing:

```bash
python3 -c "
from utils.database import neo4j_db, redis_cache
from datetime import datetime
import json

# Create sample bags
bags = [
    {'bag_tag': 'CM001', 'status': 'checked_in', 'current_location': 'PTY',
     'passenger_name': 'Alice Smith', 'pnr': 'ABC001', 'routing': 'PTY-MIA-JFK',
     'risk_score': 0.2, 'created_at': datetime.now()},
    {'bag_tag': 'CM002', 'status': 'in_transit', 'current_location': 'MIA',
     'passenger_name': 'Bob Jones', 'pnr': 'ABC002', 'routing': 'PTY-MIA-LAX',
     'risk_score': 0.75, 'created_at': datetime.now()},
    {'bag_tag': 'CM003', 'status': 'delayed', 'current_location': 'PTY',
     'passenger_name': 'Carol White', 'pnr': 'ABC003', 'routing': 'PTY-BOG',
     'risk_score': 0.95, 'created_at': datetime.now()},
]

for bag in bags:
    neo4j_db.create_digital_twin(bag)
    redis_cache.cache_bag_status(bag['bag_tag'], bag)
    print(f'Created bag: {bag[\"bag_tag\"]}')

print('Sample data created!')
"
```

---

## 🛠️ Managing Local Databases

### Start/Stop/Restart

```bash
# Start
docker start neo4j redis

# Stop
docker stop neo4j redis

# Restart
docker restart neo4j redis

# Check status
docker ps | grep -E "(neo4j|redis)"
```

### View Logs

```bash
# Neo4j logs
docker logs neo4j -f

# Redis logs
docker logs redis -f
```

### Remove and Recreate

```bash
# Stop and remove containers
docker stop neo4j redis
docker rm neo4j redis

# Remove volumes (WARNING: deletes all data!)
docker volume rm neo4j_data redis_data

# Recreate
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/baggageops123 \
  -v neo4j_data:/data \
  neo4j:5-community

docker run -d --name redis \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7-alpine redis-server --appendonly yes
```

---

## 📊 Monitoring

### Check Neo4j Stats

```cypher
// In Neo4j Browser
CALL dbms.queryJmx("org.neo4j:*") YIELD name, attributes
RETURN name, attributes;

// Node count
MATCH (n) RETURN count(n);

// Relationship count
MATCH ()-[r]->() RETURN count(r);
```

### Check Redis Stats

```bash
redis-cli INFO stats
redis-cli INFO memory
redis-cli DBSIZE
```

---

## 🔧 Troubleshooting

**Neo4j won't start:**
```bash
docker logs neo4j
# Check port 7474 and 7687 not in use
sudo netstat -tulpn | grep -E "(7474|7687)"
```

**Redis won't start:**
```bash
docker logs redis
# Check port 6379 not in use
sudo netstat -tulpn | grep 6379
```

**Connection refused:**
- Check containers are running: `docker ps`
- Check firewall rules
- Verify credentials

**Reset everything:**
```bash
docker stop neo4j redis
docker rm neo4j redis
docker volume rm neo4j_data redis_data
python3 init_neo4j.py  # After restarting
```

---

## 📚 Resources

- **Neo4j**: https://neo4j.com/docs/
- **Cypher Query Language**: https://neo4j.com/docs/cypher-manual/
- **Redis**: https://redis.io/docs/
- **Redis Commands**: https://redis.io/commands/
- **RedisInsight**: https://redis.com/redis-enterprise/redis-insight/

---

**Your databases are ready to use! 🎉**
