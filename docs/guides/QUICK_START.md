# Quick Start Guide - Local Development

## 🚀 Your App is Running!

### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **API Server** | http://localhost:8000 | N/A |
| **API Docs** | http://localhost:8000/docs | N/A |
| **Dashboard** | http://localhost:8501 | N/A |
| **Neo4j Browser** | http://localhost:7474 | neo4j / baggageops123 |
| **Redis** | localhost:6379 | N/A |

### Quick Commands

**Check what's running:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
ps aux | grep -E "(api_server|streamlit)"
docker ps | grep -E "(neo4j|redis)"
```

**Create sample data:**
```bash
python3 create_sample_data.py
```

**View Neo4j data:**
1. Open http://localhost:7474
2. Login with: neo4j / baggageops123
3. Run query:
```cypher
MATCH (b:Baggage)-[:SCANNED_AT]->(s:ScanEvent)
RETURN b, s
```

**View Redis data:**
```bash
# List all keys
docker exec redis redis-cli KEYS "*"

# Get a bag
docker exec redis redis-cli GET "bag:CM12345"

# Get metrics
docker exec redis redis-cli GET "metric:bags_processed"
```

**Test the API:**
```bash
# Health check
curl http://localhost:8000/health

# Get metrics
curl http://localhost:8000/metrics

# Process a scan event
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{
    "raw_scan": "Bag Tag: CM99999\nLocation: PTY-T1\nTimestamp: 2024-11-11T10:00:00Z",
    "source": "BHS",
    "timestamp": "2024-11-11T10:00:00Z"
  }'
```

### Useful Python Commands

**Query Neo4j:**
```python
from utils.database import neo4j_db

# Get bag journey
journey = neo4j_db.get_bag_journey('CM12345')
print(journey)
```

**Query Redis:**
```python
from utils.database import redis_cache

# Get cached bag
bag = redis_cache.get_bag_status('CM12345')
print(bag)

# Get metrics
total = redis_cache.get_metric('bags_processed')
print(f"Total bags: {total}")
```

### Restart Services

```bash
# Restart API
pkill -f api_server && python3 api_server.py &

# Restart Dashboard
pkill -f streamlit && streamlit run dashboard/app.py --server.port 8501 --server.headless true &

# Restart Databases
docker restart neo4j redis
```

### View Logs

```bash
# API logs
tail -f logs/api_server.log

# Dashboard logs
tail -f logs/dashboard.log

# Neo4j logs
docker logs neo4j -f

# Redis logs
docker logs redis -f
```

### Stop Everything

```bash
# Stop servers
pkill -f api_server
pkill -f streamlit

# Stop databases
docker stop neo4j redis
```

### Full Guides

- **Neo4j & Redis**: See `LOCAL_DATABASES_GUIDE.md`
- **Local Setup**: See `LOCAL_SETUP_COMPLETE.md`
- **Deployment**: See `VERCEL_DEPLOYMENT.md`

---

**Happy coding! 🎉**
