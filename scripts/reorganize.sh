#!/bin/bash
# Reorganize repository structure for better clarity

echo "📁 Reorganizing Repository Structure..."
echo "================================================"

# Create new directory structure
echo "Creating new directories..."
mkdir -p docs/guides
mkdir -p docs/deployment
mkdir -p docs/architecture
mkdir -p scripts/setup
mkdir -p deploy/requirements
mkdir -p deploy/configs

# Move documentation files
echo "Moving documentation files..."

# Deployment guides
mv DEPLOYMENT.md docs/deployment/ 2>/dev/null
mv RAILWAY_DEPLOYMENT.md docs/deployment/ 2>/dev/null
mv VERCEL_DEPLOYMENT.md docs/deployment/ 2>/dev/null
mv AUTHENTICATION_DEPLOYMENT.md docs/deployment/ 2>/dev/null

# Setup guides
mv LOCAL_SETUP_COMPLETE.md docs/guides/ 2>/dev/null
mv LOCAL_DATABASES_GUIDE.md docs/guides/ 2>/dev/null
mv QUICK_START.md docs/guides/ 2>/dev/null

# Architecture/Analysis docs
mv CURRENT_STATE_ANALYSIS.md docs/architecture/ 2>/dev/null
mv AUTHENTICATION_SUMMARY.md docs/architecture/ 2>/dev/null
mv AUTH_README.md docs/architecture/ 2>/dev/null
mv baggage-ontology-setup-guide.md docs/architecture/ 2>/dev/null
mv ROADMAP.md docs/ 2>/dev/null

# Move setup scripts
echo "Moving setup scripts..."
mv init_database.py scripts/setup/ 2>/dev/null
mv init_neo4j.py scripts/setup/ 2>/dev/null
mv create_sample_data.py scripts/setup/ 2>/dev/null
mv populate_neon_data.py scripts/setup/ 2>/dev/null
mv seed_neon_data.py scripts/setup/ 2>/dev/null

# Move deployment configs
echo "Moving deployment configs..."
mv railway-dashboard.json deploy/configs/ 2>/dev/null
mv railway.dashboard.json.example deploy/configs/ 2>/dev/null
mv runtime.txt deploy/ 2>/dev/null

# Move requirements files
echo "Moving requirements files..."
mv requirements.full.txt deploy/requirements/ 2>/dev/null
mv requirements-vercel.txt deploy/requirements/ 2>/dev/null

# Create symlinks for backward compatibility
echo "Creating symlinks for backward compatibility..."
ln -sf deploy/requirements/requirements.full.txt requirements.full.txt 2>/dev/null
ln -sf scripts/setup/init_database.py init_database.py 2>/dev/null
ln -sf scripts/setup/init_neo4j.py init_neo4j.py 2>/dev/null

# Update documentation references
echo "Creating root README with links..."

cat > ROOT_STRUCTURE.md << 'EOF'
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
EOF

echo ""
echo "================================================"
echo "✅ Repository reorganized!"
echo "================================================"
echo ""
echo "New structure:"
echo "  docs/guides/          - Setup and user guides"
echo "  docs/deployment/      - Deployment documentation"
echo "  docs/architecture/    - Architecture documents"
echo "  scripts/setup/        - Database initialization scripts"
echo "  deploy/requirements/  - All requirements files"
echo "  deploy/configs/       - Deployment configurations"
echo ""
echo "Root directory now contains:"
echo "  - README.md"
echo "  - requirements.txt (symlink)"
echo "  - docker-compose.yml"
echo "  - Dockerfile"
echo "  - Main Python files (api_server.py, index.py)"
echo "  - Application directories (app/, services/, agents/, etc.)"
echo ""
echo "Next steps:"
echo "  1. Review ROOT_STRUCTURE.md"
echo "  2. Update README.md with new paths"
echo "  3. Commit changes: git add -A && git commit -m 'Reorganize repository structure'"
echo ""
