# 🎒 Baggage Operations Intelligence Platform

**AI-Powered Predictive Baggage Management System**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.4-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39.0-FF4B4B.svg)](https://streamlit.io/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.25.0-008CC1.svg)](https://neo4j.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> A production-ready baggage tracking system powered by Claude Sonnet 4, Neo4j graph database, and real-time event ingestion for intelligent baggage operations.

---

## ✨ Features

- 🤖 **8 Specialized AI Agents** - Powered by Claude Sonnet 4 with LangGraph orchestration
- 📊 **Real-Time Dashboard** - Streamlit-based monitoring with live KPIs
- 🔄 **Event Ingestion** - Redis Streams processing 10K+ events/second
- 🌐 **Graph Database** - Neo4j digital twins for complex relationship queries
- 🔍 **Risk Scoring** - Predictive analytics for misconnection detection
- 📱 **Multi-Channel Notifications** - SMS, Email, Push (Twilio, SendGrid, Firebase)
- 🛡️ **Production-Ready** - Health checks, metrics, error handling

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Anthropic API key ([get one here](https://console.anthropic.com))
- PostgreSQL database ([Neon.tech](https://neon.tech) recommended)

### 1. Clone and Setup

```bash
git clone https://github.com/jbandu/bag.git
cd bag

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required variables:**
```bash
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
NEON_DATABASE_URL=postgresql://user:password@host/database
JWT_SECRET=<generate-random-32-chars>
SECRET_KEY=<generate-random-32-chars>
```

### 3. Start Services

```bash
# Start all services (Docker + Python)
./scripts/start.sh

# Check status
./scripts/status.sh
```

### 4. Access Application

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | http://localhost:8501 | Main UI |
| **API** | http://localhost:8000 | REST API |
| **API Docs** | http://localhost:8000/docs | Interactive docs |
| **Neo4j** | http://localhost:7474 | Graph browser |

---

## 📖 Documentation

- **[Quick Start Guide](docs/guides/QUICK_START.md)** - Get up and running in 5 minutes
- **[Local Setup Guide](docs/guides/LOCAL_SETUP_COMPLETE.md)** - Complete local development setup
- **[API Documentation](docs/api.md)** - REST API reference
- **[Neo4j Integration](docs/NEO4J_INTEGRATION.md)** - Graph database guide
- **[Event Ingestion](docs/EVENT_INGESTION.md)** - High-throughput event processing
- **[Deployment Guides](docs/deployment/)** - Railway, Vercel deployment

### Architecture

- **[System Architecture](docs/architecture/CURRENT_STATE_ANALYSIS.md)** - Complete system analysis
- **[AI Agents](docs/agents.md)** - 8 specialized agents documentation
- **[Workflows](docs/workflows.md)** - Orchestration and decision flows

---

## 🏗️ Architecture

```mermaid
graph TB
    A[RFID/IoT Devices] --> B[API Endpoints]
    B --> C[Redis Streams]
    C --> D[Event Processor]
    D --> E[PostgreSQL]
    D --> F[Neo4j]
    D --> G[AI Agents]
    G --> H[Notifications]
    E --> I[Dashboard]
    F --> I
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **AI/LLM** | Claude Sonnet 4 | Intelligent decision making |
| **Orchestration** | LangGraph | Multi-agent workflows |
| **API** | FastAPI | REST endpoints |
| **Dashboard** | Streamlit | Real-time monitoring |
| **Database** | PostgreSQL (Neon) | Operational data |
| **Graph DB** | Neo4j | Digital twins & relationships |
| **Cache** | Redis | Event buffering & metrics |
| **Messaging** | Twilio, SendGrid | Notifications |

---

## 🛠️ Management Scripts

```bash
# Start all services
./scripts/start.sh

# Stop all services
./scripts/stop.sh

# Restart services
./scripts/restart.sh

# Check status
./scripts/status.sh

# Complete rebuild
./scripts/rebuild.sh
```

See [scripts/README.md](scripts/README.md) for details.

---

## 📊 Key Features

### AI Agents

8 specialized agents orchestrated by LangGraph:

1. **Scan Event Processor** - Parse and validate scan events
2. **Risk Scoring Engine** - Predictive misconnection analysis
3. **WorldTracer Integration** - PIR filing automation
4. **SITA Handler** - Type B message processing
5. **BaggageXML Handler** - Modern XML manifest parsing
6. **Exception Manager** - Case creation and assignment
7. **Courier Dispatch** - Delivery optimization
8. **Passenger Communication** - Multi-channel notifications

### Event Ingestion

- **10K+ events/second** throughput
- Redis Streams for buffering
- Automatic deduplication
- Event replay capability
- Dead letter queue for errors

### Graph Queries

Neo4j-powered queries:
- Full bag journey reconstruction (<100ms)
- Real-time location tracking
- Connection risk analysis
- Bottleneck detection
- Network relationship traversal

---

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Test API endpoint
curl http://localhost:8000/health

# Process test event
curl -X POST http://localhost:8000/api/v1/events/scan \
  -H "Content-Type: application/json" \
  -d '{
    "bag_id": "0001234567",
    "location": "PTY_CHECKIN_12",
    "scan_type": "check_in"
  }'
```

---

## 🚢 Deployment

### Railway (Recommended)

```bash
# See detailed guide
cat docs/deployment/RAILWAY_DEPLOYMENT.md

# Quick deploy
railway up
```

### Vercel (Serverless)

```bash
# See detailed guide
cat docs/deployment/VERCEL_DEPLOYMENT.md

# Quick deploy
vercel --prod
```

---

## 📁 Repository Structure

```
bag/
├── README.md                 # This file
├── api_server.py            # Main API server
├── dashboard/               # Streamlit dashboard
├── services/                # Business logic
│   ├── dual_write_service.py
│   ├── event_ingestion_service.py
│   └── graph_query_service.py
├── agents/                  # AI agents
├── orchestrator/           # LangGraph workflows
├── models/                 # Data models
├── scripts/                # Management scripts
│   ├── start.sh
│   ├── stop.sh
│   └── setup/
├── docs/                   # Documentation
│   ├── guides/
│   ├── deployment/
│   └── architecture/
└── deploy/                 # Deployment configs
```

See [ROOT_STRUCTURE.md](ROOT_STRUCTURE.md) for complete structure.

---

## 🔧 Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=         # Claude API key
NEON_DATABASE_URL=         # PostgreSQL connection
JWT_SECRET=                # JWT signing key
SECRET_KEY=                # App secret key

# Databases
NEO4J_URI=                 # Neo4j connection (default: bolt://localhost:7687)
NEO4J_USER=                # Neo4j username (default: neo4j)
NEO4J_PASSWORD=            # Neo4j password
REDIS_URL=                 # Redis connection (default: redis://localhost:6379)

# Optional Services
TWILIO_ACCOUNT_SID=        # SMS notifications
SENDGRID_API_KEY=          # Email notifications
FIREBASE_CREDENTIALS=      # Push notifications
WORLDTRACER_API_KEY=       # WorldTracer integration
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file

---

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/jbandu/bag/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jbandu/bag/discussions)

---

## 🙏 Acknowledgments

- Built with [Claude](https://www.anthropic.com/claude) by Anthropic
- Powered by [LangChain](https://www.langchain.com/) and [LangGraph](https://www.langchain.com/langgraph)
- Graph database by [Neo4j](https://neo4j.com/)
- Dashboard by [Streamlit](https://streamlit.io/)

---

**Made with ❤️ for Copa Airlines**

Powered by Number Labs
