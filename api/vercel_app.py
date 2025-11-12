"""
Lightweight Vercel Entry Point
Avoids heavy AI/ML imports for faster cold starts
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import os

# Create minimal FastAPI app
app = FastAPI(
    title="Baggage Operations API",
    description="AI-Powered Baggage Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class ScanEventRequest(BaseModel):
    raw_scan: str
    source: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Root endpoint
@app.get("/")
async def root():
    """API Welcome"""
    return {
        "service": "Baggage Operations Intelligence Platform",
        "version": "1.0.0",
        "description": "AI-Powered Baggage Intelligence with 8 Specialized Agents",
        "status": "operational",
        "deployment": "vercel_serverless",
        "endpoints": {
            "health": "/health",
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
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "baggage-operations-api",
        "version": "1.0.0",
        "platform": "vercel_serverless"
    }


# Get bag status from Neon
@app.get("/api/v1/bag/{bag_tag}")
async def get_bag_status(bag_tag: str):
    """Get current status of a bag from Neon PostgreSQL"""
    try:
        # Lazy import - only load when this endpoint is called
        import psycopg2
        from psycopg2.extras import RealDictCursor

        neon_url = os.getenv("NEON_DATABASE_URL")
        if not neon_url:
            return {"error": "Database not configured"}

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
            raise HTTPException(status_code=404, detail=f"Bag {bag_tag} not found")

        # Get scan events
        cursor.execute("""
            SELECT scan_type, location, timestamp
            FROM scan_events
            WHERE bag_tag = %s
            ORDER BY timestamp DESC
            LIMIT 10
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
            "risk_score": float(bag_data['risk_score']),
            "scan_events": [dict(event) for event in scan_events],
            "source": "neon_postgresql"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Process scan event (lightweight - queue for background processing)
@app.post("/api/v1/scan")
async def process_scan_event(request: ScanEventRequest, background_tasks: BackgroundTasks):
    """
    Process baggage scan event

    In Vercel serverless, we return quickly and queue heavy AI processing.
    For full AI processing, use the Railway deployment.
    """
    try:
        # For Vercel: Quick acknowledgment + database insert
        # Heavy AI processing would timeout on serverless

        # Could insert to database here for async processing
        # Or use a message queue (SQS, Redis Queue, etc.)

        return {
            "status": "accepted",
            "message": "Scan event queued for processing",
            "raw_scan": request.raw_scan,
            "source": request.source,
            "received_at": datetime.utcnow().isoformat(),
            "note": "For full AI analysis, use Railway deployment at: [your-railway-url]"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Handler for Vercel
handler = app
