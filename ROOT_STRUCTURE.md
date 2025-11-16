# Repository Structure

This repository is organized for clarity and maintainability.

## 📁 Directory Structure

```
bag/
├── README.md                    # Main documentation
├── requirements.txt             # Core dependencies
├── docker-compose.yml          # Local development
├── Dockerfile                  # Container definition
│
├── api_server.py               # Main API server
├── index.py                    # Entry point
│
├── app/                        # Application core
│   ├── api/                    # API endpoints
│   ├── auth/                   # Authentication
│   ├── core/                   # Core logic
│   └── database/               # Database managers
│
├── services/                   # Business logic services
│   ├── dual_write_service.py
│   ├── event_ingestion_service.py
│   ├── event_processor_service.py
│   └── graph_query_service.py
│
├── agents/                     # AI agents
├── orchestrator/              # Workflow orchestration
├── models/                    # Data models
├── gateway/                   # Integration adapters
├── mappers/                   # Data transformation
├── memory/                    # Agent memory
│
├── dashboard/                 # Streamlit dashboard
│
├── scripts/                   # Management scripts
│   ├── start.sh              # Start all services
│   ├── stop.sh               # Stop all services
│   ├── restart.sh            # Restart services
│   ├── status.sh             # Check status
│   ├── rebuild.sh            # Complete rebuild
│   ├── sync_neo4j.py         # Database sync
│   └── setup/                # Setup scripts
│       ├── init_database.py
│       ├── init_neo4j.py
│       └── seed_neon_data.py
│
├── docs/                      # Documentation
│   ├── README.md             # Documentation index
│   ├── ROADMAP.md            # Project roadmap
│   ├── api.md                # API documentation
│   ├── agents.md             # Agent documentation
│   ├── NEO4J_INTEGRATION.md  # Neo4j guide
│   ├── EVENT_INGESTION.md    # Event system guide
│   ├── guides/               # Setup guides
│   │   ├── QUICK_START.md
│   │   ├── LOCAL_SETUP_COMPLETE.md
│   │   └── LOCAL_DATABASES_GUIDE.md
│   ├── deployment/           # Deployment guides
│   │   ├── DEPLOYMENT.md
│   │   ├── RAILWAY_DEPLOYMENT.md
│   │   ├── VERCEL_DEPLOYMENT.md
│   │   └── AUTHENTICATION_DEPLOYMENT.md
│   └── architecture/         # Architecture docs
│       ├── CURRENT_STATE_ANALYSIS.md
│       ├── AUTHENTICATION_SUMMARY.md
│       └── baggage-ontology-setup-guide.md
│
├── deploy/                    # Deployment configs
│   ├── requirements/         # Requirements files
│   │   ├── requirements.full.txt
│   │   └── requirements-vercel.txt
│   ├── configs/              # Deployment configs
│   │   ├── railway-dashboard.json
│   │   └── railway.dashboard.json.example
│   └── runtime.txt
│
├── schema/                    # Database schemas
├── queries/                   # SQL/Cypher queries
├── migrations/                # Database migrations
├── tests/                     # Test files
└── examples/                  # Example code
```

## 🚀 Quick Start

See [docs/guides/QUICK_START.md](docs/guides/QUICK_START.md)

## 📖 Documentation

- **Setup**: [docs/guides/](docs/guides/)
- **Deployment**: [docs/deployment/](docs/deployment/)
- **Architecture**: [docs/architecture/](docs/architecture/)
- **API**: [docs/api.md](docs/api.md)

## 🛠️ Development

```bash
# Start everything
./scripts/start.sh

# Check status
./scripts/status.sh

# Stop everything
./scripts/stop.sh
```

See [scripts/README.md](scripts/README.md) for more management commands.
