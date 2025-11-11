# ✅ Local Setup Complete!

Your Baggage Operations Intelligence Platform is now running successfully!

## 🚀 What's Running

### 1. API Server (FastAPI)
- **URL**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **Status**: ✅ Running with 8 AI Agents
  - Scan Event Processor
  - Risk Scoring Engine
  - WorldTracer Integration
  - SITA Message Handler
  - BaggageXML Handler
  - Exception Case Manager
  - Courier Dispatch
  - Passenger Communication

### 2. Dashboard (Streamlit)
- **URL**: http://localhost:8501
- **Status**: ✅ Running
- **Features**: Real-time monitoring, KPIs, risk visualization

### 3. Databases
- **Neo4j** (Graph DB - Digital Twin)
  - URL: http://localhost:7474
  - Bolt: bolt://localhost:7687
  - Username: neo4j
  - Password: baggageops123
  - Status: ✅ Running with indexes initialized

- **Redis** (Cache & Metrics)
  - URL: redis://localhost:6379
  - Status: ✅ Running

- **Neon PostgreSQL** (Operational Data)
  - Status: ✅ Connected & Initialized
  - Tables: baggage, scan_events, risk_assessments, worldtracer_pirs, exception_cases, courier_dispatches, passenger_notifications

## 🧪 Testing Your API

### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

### Test Metrics
```bash
curl http://localhost:8000/metrics
```

### Test Scan Processing (Example)
```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{
    "raw_scan": "Bag Tag: CM123456\\nLocation: PTY-T1\\nTimestamp: 2024-11-11T10:00:00Z",
    "source": "BHS",
    "timestamp": "2024-11-11T10:00:00Z"
  }'
```

### Interactive API Documentation
Open in browser: http://localhost:8000/docs

## 📊 Access the Dashboard
Open in browser: http://localhost:8501

## 🗄️ Database Access

### Neo4j Browser
1. Open http://localhost:7474
2. Login with:
   - Username: `neo4j`
   - Password: `baggageops123`

### Query Examples
```cypher
// View all baggage
MATCH (b:Baggage) RETURN b LIMIT 10;

// View baggage journey
MATCH (b:Baggage {bag_tag: 'CM123456'})-[:SCANNED_AT]->(s:ScanEvent)
RETURN b, s ORDER BY s.timestamp;
```

## 📁 Project Structure
```
/home/jbandu/bag/
├── api_server.py           # FastAPI server (running on :8000)
├── dashboard/app.py        # Streamlit dashboard (running on :8501)
├── agents/                 # 8 AI agents
├── orchestrator/           # LangGraph orchestration
├── utils/database.py       # DB connections
├── config/settings.py      # Configuration
├── init_database.py        # Neon DB initialization
├── init_neo4j.py          # Neo4j initialization
├── vercel.json            # Vercel deployment config
└── api/index.py           # Vercel serverless handler
```

## 🔧 Managing Services

### Stop All Services
```bash
# Stop API server
pkill -f "python3 api_server.py"

# Stop Dashboard
pkill -f streamlit

# Stop Docker containers
docker stop neo4j redis
```

### Restart Services
```bash
# API Server
python3 api_server.py &

# Dashboard
streamlit run dashboard/app.py --server.port 8501 --server.headless true &
```

### View Logs
```bash
# API Server logs
tail -f logs/api_server.log

# Dashboard logs
tail -f logs/dashboard.log
```

## 🌐 Deploying to Vercel

Complete deployment guide: [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md)

Quick start:
```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

## 📈 Next Steps

1. **Test the API**: Use the `/docs` endpoint to try out different endpoints
2. **View the Dashboard**: Check real-time metrics and monitoring
3. **Process Sample Data**: Send test scan events via the API
4. **Deploy to Vercel**: Follow VERCEL_DEPLOYMENT.md for production deployment
5. **Set Up Cloud DBs**: For Vercel, you'll need Neo4j Aura and Upstash Redis

## 🆘 Troubleshooting

### API not responding
- Check if process is running: `ps aux | grep api_server`
- Check logs: `tail -f logs/api_server.log`
- Restart: `pkill -f api_server && python3 api_server.py &`

### Dashboard not loading
- Check if process is running: `ps aux | grep streamlit`
- Check logs: `tail -f logs/dashboard.log`
- Restart: `pkill -f streamlit && streamlit run dashboard/app.py --server.port 8501 &`

### Database connection errors
- Verify Docker containers: `docker ps`
- Restart containers: `docker restart neo4j redis`

## 📚 Documentation

- API Documentation: http://localhost:8000/docs
- README: [README.md](README.md)
- Deployment Guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Vercel Guide: [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md)

## 💾 Git Repository

All code is synced to GitHub:
- Repository: https://github.com/jbandu/bag
- Latest commit: Includes local setup + Vercel deployment config

---

**Congratulations! Your AI-powered baggage operations platform is ready to use! 🎉**
