#!/bin/bash
# Start all baggage tracking services

echo "🚀 Starting Baggage Tracking Application..."
echo "================================================"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated!"
    echo "   Run: source venv/bin/activate"
    echo ""
    read -p "Activate now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        source venv/bin/activate
    else
        echo "❌ Aborted. Please activate venv first."
        exit 1
    fi
fi

# Check .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "   Copy .env.example to .env and configure it:"
    echo "   cp .env.example .env"
    exit 1
fi

# Start Docker containers
echo "📍 Starting Docker containers..."
if [ -f "docker-compose.yml" ]; then
    docker-compose up -d
else
    # Start individually if docker-compose.yml doesn't exist
    if ! docker ps -q --filter "name=neo4j" | grep -q .; then
        echo "   Starting Neo4j..."
        docker run -d \
            --name neo4j \
            -p 7474:7474 -p 7687:7687 \
            -e NEO4J_AUTH=neo4j/baggageops123 \
            -e NEO4J_PLUGINS='["apoc"]' \
            neo4j:5-community 2>/dev/null || docker start neo4j
    fi

    if ! docker ps -q --filter "name=redis" | grep -q .; then
        echo "   Starting Redis..."
        docker run -d \
            --name redis \
            -p 6379:6379 \
            redis:7-alpine 2>/dev/null || docker start redis
    fi
fi

# Wait for databases to be ready
echo "📍 Waiting for databases to be ready..."
sleep 5

# Check Neo4j
echo "   Checking Neo4j..."
timeout 30 bash -c 'until curl -s http://localhost:7474 > /dev/null; do sleep 1; done'
if [ $? -eq 0 ]; then
    echo "   ✅ Neo4j ready"
else
    echo "   ⚠️  Neo4j might not be ready yet"
fi

# Check Redis
echo "   Checking Redis..."
timeout 10 bash -c 'until docker exec redis redis-cli ping > /dev/null 2>&1; do sleep 1; done'
if [ $? -eq 0 ]; then
    echo "   ✅ Redis ready"
else
    echo "   ⚠️  Redis might not be ready yet"
fi

# Start API Server in background
echo "📍 Starting API server..."
nohup python3 api_server.py > logs/api_server.log 2>&1 &
API_PID=$!
echo "   ✅ API server started (PID: $API_PID)"
echo "   📄 Logs: logs/api_server.log"

# Wait a moment for API to start
sleep 3

# Start Streamlit Dashboard in background
echo "📍 Starting Streamlit dashboard..."
nohup streamlit run dashboard/app.py --server.port 8501 --server.headless true > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo "   ✅ Dashboard started (PID: $DASHBOARD_PID)"
echo "   📄 Logs: logs/dashboard.log"

echo ""
echo "================================================"
echo "✅ All services started!"
echo "================================================"
echo ""
echo "🌐 Access Points:"
echo "   Dashboard:    http://localhost:8501"
echo "   API:          http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   Neo4j:        http://localhost:7474"
echo ""
echo "📊 Check status:"
echo "   ./scripts/status.sh"
echo ""
echo "📄 View logs:"
echo "   tail -f logs/api_server.log"
echo "   tail -f logs/dashboard.log"
echo ""
echo "🛑 Stop all services:"
echo "   ./scripts/stop.sh"
echo ""
