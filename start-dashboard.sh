#!/bin/bash
# Railway startup script for Streamlit dashboard

# Railway sets PORT environment variable
PORT=${PORT:-8501}

echo "Starting Streamlit dashboard on port $PORT..."
exec streamlit run dashboard/simple_app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
