#!/bin/bash
# Railway startup script

# Railway sets PORT environment variable
PORT=${PORT:-8000}

echo "Starting FastAPI on port $PORT..."
exec uvicorn api_server:app --host 0.0.0.0 --port $PORT
