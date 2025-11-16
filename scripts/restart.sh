#!/bin/bash
# Restart all baggage tracking services

echo "🔄 Restarting Baggage Tracking Application..."
echo "================================================"
echo ""

# Stop everything first
./scripts/stop.sh

echo ""
echo "⏳ Waiting 3 seconds before restart..."
sleep 3
echo ""

# Start everything
./scripts/start.sh
