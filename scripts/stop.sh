#!/bin/bash
# Stop all baggage tracking services

echo "🛑 Stopping Baggage Tracking Application..."
echo "================================================"

# Stop Python processes
echo "📍 Stopping API server..."
pkill -f "api_server.py" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ API server stopped"
else
    echo "   ℹ️  API server not running"
fi

echo "📍 Stopping Streamlit dashboard..."
pkill -f "streamlit run dashboard" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Dashboard stopped"
else
    echo "   ℹ️  Dashboard not running"
fi

echo "📍 Stopping event processor workers..."
pkill -f "event_processor" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Event processors stopped"
else
    echo "   ℹ️  Event processors not running"
fi

# Stop Docker containers
echo "📍 Stopping Docker containers..."
if docker ps -q --filter "name=neo4j" | grep -q .; then
    docker stop neo4j 2>/dev/null
    echo "   ✅ Neo4j stopped"
else
    echo "   ℹ️  Neo4j not running"
fi

if docker ps -q --filter "name=redis" | grep -q .; then
    docker stop redis 2>/dev/null
    echo "   ✅ Redis stopped"
else
    echo "   ℹ️  Redis not running"
fi

# Alternative: stop docker-compose services
if [ -f "docker-compose.yml" ]; then
    docker-compose down 2>/dev/null
fi

echo ""
echo "================================================"
echo "✅ All services stopped!"
echo "================================================"
