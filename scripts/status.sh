#!/bin/bash
# Check status of all baggage tracking services

echo "📊 Baggage Tracking Application Status"
echo "================================================"
echo ""

# Function to check if process is running
check_process() {
    if pgrep -f "$1" > /dev/null; then
        echo "✅ RUNNING"
        return 0
    else
        echo "❌ STOPPED"
        return 1
    fi
}

# Function to check if port is listening
check_port() {
    if nc -z localhost $1 2>/dev/null; then
        echo "✅ LISTENING"
        return 0
    else
        echo "❌ NOT LISTENING"
        return 1
    fi
}

# Check Python services
echo "🐍 Python Services:"
echo "-------------------"
printf "API Server (8000):     "
check_process "api_server.py"

printf "Dashboard (8501):      "
check_process "streamlit run dashboard"

echo ""

# Check Docker containers
echo "🐳 Docker Containers:"
echo "---------------------"
printf "Neo4j:                 "
if docker ps --filter "name=neo4j" --filter "status=running" | grep -q neo4j; then
    echo "✅ RUNNING"
else
    echo "❌ STOPPED"
fi

printf "Redis:                 "
if docker ps --filter "name=redis" --filter "status=running" | grep -q redis; then
    echo "✅ RUNNING"
else
    echo "❌ STOPPED"
fi

echo ""

# Check ports
echo "🌐 Port Status:"
echo "---------------"
printf "API (8000):            "
check_port 8000

printf "Dashboard (8501):      "
check_port 8501

printf "Neo4j HTTP (7474):     "
check_port 7474

printf "Neo4j Bolt (7687):     "
check_port 7687

printf "Redis (6379):          "
check_port 6379

echo ""

# Check database connections
echo "🔌 Database Health:"
echo "-------------------"

# Check API health endpoint
printf "API Health:            "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ HEALTHY"
    # Show database status from API
    curl -s http://localhost:8000/health | python3 -c "import sys, json; d=json.load(sys.stdin).get('databases', {}); print(f\"   PostgreSQL: {'✅' if d.get('postgres')=='connected' else '❌'} {d.get('postgres', 'unknown')}\"); print(f\"   Neo4j:      {'✅' if d.get('neo4j')=='connected' else '❌'} {d.get('neo4j', 'unknown')}\"); print(f\"   Redis:      {'✅' if d.get('redis')=='connected' else '❌'} {d.get('redis', 'unknown')}\")" 2>/dev/null
else
    echo "❌ UNHEALTHY"
fi

echo ""

# Show process details
echo "📋 Process Details:"
echo "-------------------"
ps aux | grep -E "(api_server|streamlit)" | grep -v grep | awk '{printf "%-60s PID: %s\n", substr($11" "$12" "$13,1,60), $2}'

echo ""

# Show Docker containers
echo "🐳 Docker Details:"
echo "------------------"
docker ps --filter "name=neo4j" --filter "name=redis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null

echo ""
echo "================================================"
echo "💡 Quick Commands:"
echo "   Start:   ./scripts/start.sh"
echo "   Stop:    ./scripts/stop.sh"
echo "   Restart: ./scripts/restart.sh"
echo "   Logs:    tail -f logs/api_server.log"
echo "================================================"
