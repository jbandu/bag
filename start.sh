#!/bin/bash

echo "🎒 Baggage Operations Platform - Startup Script"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Please copy .env.example to .env and configure your settings."
    exit 1
fi

echo -e "${GREEN}✓${NC} Found .env configuration"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo -e "${RED}ERROR: Python 3.11+ required. Found: $python_version${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python version check passed ($python_version)"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${RED}ERROR: Failed to install dependencies${NC}"
    exit 1
fi

# Check if databases are running
echo ""
echo "🗄️  Checking database connections..."

# Check Neo4j
if nc -z localhost 7687 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Neo4j is running (port 7687)"
else
    echo -e "${YELLOW}⚠${NC}  Neo4j not detected. Starting with Docker..."
    docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
        -e NEO4J_AUTH=neo4j/baggageops123 neo4j:5-community
    sleep 5
fi

# Check Redis
if nc -z localhost 6379 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Redis is running (port 6379)"
else
    echo -e "${YELLOW}⚠${NC}  Redis not detected. Starting with Docker..."
    docker run -d --name redis -p 6379:6379 redis:7-alpine
    sleep 2
fi

# Create log directory
mkdir -p logs
echo -e "${GREEN}✓${NC} Log directory ready"

echo ""
echo "=============================================="
echo "🚀 Starting Baggage Operations Platform"
echo "=============================================="
echo ""

# Start API server in background
echo "Starting API Server on http://localhost:8000..."
python api_server.py > logs/api.log 2>&1 &
API_PID=$!
echo -e "${GREEN}✓${NC} API Server started (PID: $API_PID)"

# Wait a moment for API to start
sleep 3

# Start Dashboard
echo ""
echo "Starting Dashboard on http://localhost:8501..."
streamlit run dashboard/app.py > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo -e "${GREEN}✓${NC} Dashboard started (PID: $DASHBOARD_PID)"

echo ""
echo "=============================================="
echo "✨ Platform is ready!"
echo "=============================================="
echo ""
echo "📍 Access points:"
echo "   • Dashboard:  http://localhost:8501"
echo "   • API:        http://localhost:8000"
echo "   • API Docs:   http://localhost:8000/docs"
echo "   • Neo4j:      http://localhost:7474"
echo ""
echo "📊 Logs:"
echo "   • API:        tail -f logs/api.log"
echo "   • Dashboard:  tail -f logs/dashboard.log"
echo ""
echo "🛑 To stop:"
echo "   kill $API_PID $DASHBOARD_PID"
echo "   # Or use: ./stop.sh"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep script running
trap "kill $API_PID $DASHBOARD_PID; exit" INT TERM
wait
