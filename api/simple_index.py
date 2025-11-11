"""
Simplified Vercel Serverless Function Entry Point
Minimal dependencies, lazy loading
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create minimal FastAPI app
app = FastAPI(
    title="Baggage Operations API",
    description="AI-Powered Baggage Intelligence Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    """API Welcome and Documentation"""
    return {
        "service": "Baggage Operations Intelligence Platform",
        "version": "1.0.0",
        "description": "AI-Powered Baggage Intelligence with 8 Specialized Agents",
        "status": "operational",
        "deployment": "vercel_serverless",
        "endpoints": {
            "health": "/health",
            "test_db": "/test-db",
            "api_docs": "/docs",
            "redoc": "/redoc",
            "process_scan": "POST /api/v1/scan",
            "get_bag_status": "GET /api/v1/bag/{bag_tag}"
        },
        "agents": [
            "Scan Event Processor",
            "Risk Scoring Engine",
            "WorldTracer Integration",
            "SITA Message Handler",
            "BaggageXML Handler",
            "Exception Case Manager",
            "Courier Dispatch Agent",
            "Passenger Communication"
        ],
        "powered_by": "Claude Sonnet 4 + LangGraph"
    }

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "baggage-operations-api",
        "version": "1.0.0",
        "platform": "vercel_serverless"
    }

# Test database connection
@app.get("/test-db")
async def test_database():
    """Test Neon PostgreSQL connection"""
    import os
    import psycopg2

    try:
        neon_url = os.getenv("NEON_DATABASE_URL")
        if not neon_url:
            return {
                "status": "error",
                "message": "NEON_DATABASE_URL not set in environment"
            }

        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM baggage")
        bag_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return {
            "status": "connected",
            "database": "neon_postgresql",
            "baggage_count": bag_count
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Get bag status
@app.get("/api/v1/bag/{bag_tag}")
async def get_bag_status(bag_tag: str):
    """Get current status of a bag from Neon PostgreSQL"""
    import os
    import psycopg2
    from psycopg2.extras import RealDictCursor

    try:
        neon_url = os.getenv("NEON_DATABASE_URL")
        if not neon_url:
            return {
                "error": "Database not configured"
            }

        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get bag data
        cursor.execute("""
            SELECT bag_tag, passenger_name, pnr, routing,
                   status, current_location, risk_score, created_at
            FROM baggage
            WHERE bag_tag = %s
        """, (bag_tag,))

        bag_data = cursor.fetchone()

        if not bag_data:
            cursor.close()
            conn.close()
            return {
                "error": f"Bag {bag_tag} not found",
                "bag_tag": bag_tag
            }

        # Get scan events
        cursor.execute("""
            SELECT scan_type, location, timestamp
            FROM scan_events
            WHERE bag_tag = %s
            ORDER BY timestamp DESC
        """, (bag_tag,))

        scan_events = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "bag_tag": bag_tag,
            "passenger_name": bag_data['passenger_name'],
            "pnr": bag_data['pnr'],
            "routing": bag_data['routing'],
            "status": bag_data['status'],
            "current_location": bag_data['current_location'],
            "risk_score": bag_data['risk_score'],
            "scan_events": [dict(event) for event in scan_events],
            "source": "neon_postgresql"
        }

    except Exception as e:
        return {
            "error": str(e),
            "bag_tag": bag_tag
        }

# Handler for Vercel
handler = app
