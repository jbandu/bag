#!/bin/bash
# Complete rebuild and restart

echo "🔨 Rebuilding Baggage Tracking Application..."
echo "================================================"
echo ""

# Stop everything first
echo "1️⃣ Stopping all services..."
./scripts/stop.sh

echo ""
echo "2️⃣ Cleaning up..."

# Remove Python cache
echo "   Removing __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo "   ✅ Python cache cleaned"

# Remove old log files
echo "   Archiving old logs..."
mkdir -p logs/archive
mv logs/*.log logs/archive/ 2>/dev/null
echo "   ✅ Logs archived"

echo ""
echo "3️⃣ Reinstalling dependencies..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "   Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
echo "   Installing requirements..."
pip install -r requirements.full.txt -q

echo "   ✅ Dependencies installed"

echo ""
echo "4️⃣ Rebuilding Docker containers..."

# Stop and remove containers
docker stop neo4j redis 2>/dev/null
docker rm neo4j redis 2>/dev/null

# Pull latest images
echo "   Pulling Neo4j image..."
docker pull neo4j:5-community -q

echo "   Pulling Redis image..."
docker pull redis:7-alpine -q

echo "   ✅ Docker images updated"

echo ""
echo "5️⃣ Reinitializing databases..."

# Start containers
docker-compose up -d 2>/dev/null || {
    docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
        -e NEO4J_AUTH=neo4j/baggageops123 \
        -e NEO4J_PLUGINS='["apoc"]' \
        neo4j:5-community

    docker run -d --name redis -p 6379:6379 redis:7-alpine
}

# Wait for databases
echo "   Waiting for databases to start..."
sleep 10

# Initialize databases
echo "   Initializing PostgreSQL schema..."
python3 init_database.py

echo "   Initializing Neo4j schema..."
python3 init_neo4j.py

echo "   ✅ Databases initialized"

echo ""
echo "6️⃣ Starting services..."
./scripts/start.sh

echo ""
echo "================================================"
echo "✅ Rebuild complete!"
echo "================================================"
echo ""
echo "🧪 Run tests:"
echo "   pytest tests/"
echo ""
echo "📊 Check status:"
echo "   ./scripts/status.sh"
echo ""
