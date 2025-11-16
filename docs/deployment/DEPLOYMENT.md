# 🚀 Deployment Guide - Baggage Operations Platform

## Quick Start (Local Development)

### Option 1: One-Command Startup

```bash
./start.sh
```

This script will:
1. Check Python version (requires 3.11+)
2. Install dependencies
3. Start Neo4j and Redis (via Docker if needed)
4. Launch API server on port 8000
5. Launch Dashboard on port 8501

### Option 2: Docker Compose (Production-Ready)

```bash
# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Detailed Setup

### 1. Environment Configuration

Required environment variables in `.env`:

```bash
# Critical - Get from Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Supabase (create free account at supabase.com)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Optional - for production features
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
SENDGRID_API_KEY=SG...
WORLDTRACER_API_KEY=...
```

### 2. Database Setup

#### Supabase Tables

Run this SQL in Supabase SQL Editor:

```sql
-- Baggage master table
CREATE TABLE baggage (
    bag_tag VARCHAR(20) PRIMARY KEY,
    status VARCHAR(50),
    current_location VARCHAR(100),
    passenger_name VARCHAR(200),
    pnr VARCHAR(20),
    routing TEXT[],
    risk_score DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scan events
CREATE TABLE scan_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE,
    bag_tag VARCHAR(20),
    scan_type VARCHAR(50),
    location VARCHAR(100),
    timestamp TIMESTAMPTZ,
    scanner_id VARCHAR(50),
    operator_id VARCHAR(50),
    flight_number VARCHAR(20),
    status VARCHAR(50),
    error_codes TEXT[],
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Risk assessments
CREATE TABLE risk_assessments (
    id SERIAL PRIMARY KEY,
    bag_tag VARCHAR(20),
    risk_score DECIMAL(3,2),
    risk_level VARCHAR(20),
    primary_factors TEXT[],
    recommended_action VARCHAR(100),
    confidence DECIMAL(3,2),
    reasoning TEXT,
    connection_time_minutes INTEGER,
    mct_minutes INTEGER,
    airport_performance_score DECIMAL(3,2),
    weather_impact_score DECIMAL(3,2),
    timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- WorldTracer PIRs
CREATE TABLE worldtracer_pirs (
    id SERIAL PRIMARY KEY,
    pir_number VARCHAR(50) UNIQUE,
    pir_type VARCHAR(20),
    bag_tag VARCHAR(20),
    passenger_name VARCHAR(200),
    passenger_pnr VARCHAR(20),
    flight_number VARCHAR(20),
    bag_description TEXT,
    contents_description TEXT,
    last_known_location VARCHAR(100),
    expected_destination VARCHAR(100),
    status VARCHAR(50),
    created_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

-- Exception cases
CREATE TABLE exception_cases (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(100) UNIQUE,
    bag_tag VARCHAR(20),
    priority VARCHAR(10),
    assigned_to VARCHAR(100),
    status VARCHAR(50),
    risk_score DECIMAL(3,2),
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    sla_deadline TIMESTAMPTZ,
    closed_at TIMESTAMPTZ
);

-- Courier dispatches
CREATE TABLE courier_dispatches (
    id SERIAL PRIMARY KEY,
    dispatch_id VARCHAR(100) UNIQUE,
    bag_tag VARCHAR(20),
    pir_number VARCHAR(50),
    courier_vendor VARCHAR(100),
    pickup_location VARCHAR(200),
    delivery_address TEXT,
    estimated_delivery TIMESTAMPTZ,
    courier_cost DECIMAL(10,2),
    potential_claim_cost DECIMAL(10,2),
    status VARCHAR(50),
    requires_approval BOOLEAN,
    approved_by VARCHAR(100),
    tracking_number VARCHAR(100),
    created_at TIMESTAMPTZ
);

-- Passenger notifications
CREATE TABLE passenger_notifications (
    id SERIAL PRIMARY KEY,
    notification_id VARCHAR(100) UNIQUE,
    bag_tag VARCHAR(20),
    passenger_name VARCHAR(200),
    message_type VARCHAR(50),
    channels TEXT[],
    sms_content TEXT,
    email_content TEXT,
    push_content TEXT,
    sent_at TIMESTAMPTZ,
    delivery_status JSONB
);

-- Indexes for performance
CREATE INDEX idx_baggage_tag ON baggage(bag_tag);
CREATE INDEX idx_scan_events_bag_tag ON scan_events(bag_tag);
CREATE INDEX idx_scan_events_timestamp ON scan_events(timestamp);
CREATE INDEX idx_risk_assessments_bag_tag ON risk_assessments(bag_tag);
CREATE INDEX idx_exception_cases_status ON exception_cases(status);
CREATE INDEX idx_pirs_status ON worldtracer_pirs(status);
```

#### Neo4j Setup

```cypher
// Create indexes
CREATE INDEX bag_tag_index FOR (b:Baggage) ON (b.bag_tag);
CREATE INDEX scan_event_index FOR (s:ScanEvent) ON (s.event_id);

// Create constraints
CREATE CONSTRAINT bag_tag_unique FOR (b:Baggage) REQUIRE b.bag_tag IS UNIQUE;
```

### 3. Testing

```bash
# Run test suite
python tests/test_system.py

# Expected output:
# ✅ normal_scan: PASSED
# ✅ tight_connection: PASSED
# ✅ scan_gap: PASSED
# ✅ type_b_message: PASSED
```

### 4. Production Deployment

#### AWS Deployment

```bash
# Install AWS CLI and configure
aws configure

# Create ECS cluster
aws ecs create-cluster --cluster-name baggage-ops

# Build and push Docker image
docker build -t baggage-ops:latest .
docker tag baggage-ops:latest <your-ecr-repo>:latest
docker push <your-ecr-repo>:latest

# Deploy via ECS task definition
aws ecs create-service --cluster baggage-ops \
  --service-name baggage-api \
  --task-definition baggage-ops-task \
  --desired-count 2 \
  --launch-type FARGATE
```

#### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/service.yml
kubectl apply -f k8s/ingress.yml

# Check status
kubectl get pods -n baggage-ops
kubectl logs -f deployment/baggage-api -n baggage-ops
```

### 5. Monitoring Setup

#### Prometheus + Grafana

```bash
# Install Prometheus
kubectl apply -f monitoring/prometheus.yml

# Install Grafana
kubectl apply -f monitoring/grafana.yml

# Import dashboard
# Use dashboard ID: baggage-ops-dashboard.json
```

#### Log Aggregation

```bash
# Install Loki
helm install loki grafana/loki-stack

# Configure log forwarding
kubectl apply -f logging/promtail.yml
```

### 6. Integration Testing

#### Test Scan Event Processing

```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{
    "raw_scan": "Bag Tag: CM999999\nLocation: PTY-T1\nTimestamp: 2024-11-11T15:00:00Z",
    "source": "TEST"
  }'
```

Expected response:
```json
{
  "status": "success",
  "result": {
    "bag_tag": "CM999999",
    "risk_level": "low",
    "actions_completed": ["scan_processed", "risk_assessed", "monitoring_active"]
  }
}
```

### 7. Performance Tuning

#### API Server

```bash
# Increase workers for production
uvicorn api_server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

#### Neo4j Optimization

```cypher
// Warm up cache
CALL apoc.warmup.run();

// Check memory settings in neo4j.conf:
dbms.memory.heap.initial_size=2G
dbms.memory.heap.max_size=4G
dbms.memory.pagecache.size=2G
```

### 8. Backup & Recovery

```bash
# Backup Neo4j
docker exec neo4j neo4j-admin database backup neo4j \
  --to-path=/backups/neo4j-$(date +%Y%m%d)

# Backup Supabase (automated via Supabase)
# Download from Supabase Dashboard > Database > Backups

# Backup Redis
docker exec redis redis-cli BGSAVE
```

### 9. Troubleshooting

#### Common Issues

**1. API not responding**
```bash
# Check logs
tail -f logs/api.log

# Check if port is in use
lsof -i :8000

# Restart service
docker-compose restart api
```

**2. Neo4j connection failed**
```bash
# Check Neo4j status
docker logs neo4j

# Reset password
docker exec -it neo4j cypher-shell -u neo4j -p neo4j
ALTER USER neo4j SET PASSWORD 'baggageops123';
```

**3. High memory usage**
```bash
# Check Docker stats
docker stats

# Limit memory in docker-compose.yml
services:
  api:
    mem_limit: 2g
    mem_reservation: 1g
```

### 10. Security Hardening

```bash
# Use secrets management
# Store sensitive vars in AWS Secrets Manager or HashiCorp Vault

# Enable HTTPS
# Use Let's Encrypt or AWS Certificate Manager

# Set up WAF rules
# Configure AWS WAF or Cloudflare for DDoS protection

# Enable audit logging
# Track all API calls and agent decisions
```

## Support

For deployment issues:
- GitHub: https://github.com/jbandu/bag/issues
- Email: support@numberlabs.ai
- Docs: https://docs.numberlabs.ai

---

**Number Labs** | Enterprise AI for Airlines
