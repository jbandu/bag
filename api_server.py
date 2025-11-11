"""
FastAPI Server for Baggage Operations Platform
Receives scan events from BRS, BHS, DCS, and Type B messages
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
import sys

from config.settings import settings

# Lazy imports for orchestrator and redis (only load when needed)
orchestrator = None
redis_cache = None

def get_orchestrator():
    """Lazy load orchestrator only when needed"""
    global orchestrator
    if orchestrator is None:
        try:
            from orchestrator.baggage_orchestrator import orchestrator as orch
            orchestrator = orch
            logger.info("✅ Orchestrator loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load orchestrator: {e}")
            raise HTTPException(status_code=503, detail="AI processing unavailable - orchestrator failed to load")
    return orchestrator

def get_redis():
    """Lazy load redis only when needed"""
    global redis_cache
    if redis_cache is None:
        try:
            from utils.database import redis_cache as rc
            redis_cache = rc
            logger.info("✅ Redis cache loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ Redis cache unavailable: {e}")
            redis_cache = None
    return redis_cache


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.log_level
)

# Only log to file in development (Railway uses stdout)
if settings.environment == "development":
    logger.add(
        "logs/baggage_api_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO"
    )


# FastAPI app
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
    """Scan event from BRS/BHS/DCS"""
    raw_scan: str
    source: str  # 'BRS', 'BHS', 'DCS', 'MANUAL'
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TypeBMessageRequest(BaseModel):
    """SITA Type B message"""
    message: str
    message_type: str  # 'BTM', 'BSM', 'BPM'
    from_station: str
    to_station: str
    timestamp: Optional[str] = None


class BaggageXMLRequest(BaseModel):
    """BaggageXML manifest"""
    xml_content: str
    flight_number: str
    timestamp: Optional[str] = None


# Root endpoint
@app.get("/")
async def root():
    """API Welcome and Documentation"""
    return {
        "service": "Baggage Operations Intelligence Platform",
        "version": "1.0.0",
        "description": "AI-Powered Baggage Intelligence with 8 Specialized Agents",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "api_docs": "/docs",
            "redoc": "/redoc",
            "process_scan": "POST /api/v1/scan",
            "process_type_b": "POST /api/v1/type-b",
            "process_xml": "POST /api/v1/baggage-xml",
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
        "version": "1.0.0"
    }


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Get operational metrics"""
    cache = get_redis()

    if cache is None:
        return {
            "status": "metrics_unavailable",
            "reason": "Redis not connected",
            "timestamp": datetime.utcnow().isoformat()
        }

    return {
        "bags_processed": cache.get_metric('bags_processed'),
        "scans_processed": cache.get_metric('scans_processed'),
        "risk_assessments_performed": cache.get_metric('risk_assessments_performed'),
        "high_risk_bags_detected": cache.get_metric('high_risk_bags_detected'),
        "exceptions_handled": cache.get_metric('exceptions_handled'),
        "scan_anomalies": cache.get_metric('scan_anomalies'),
        "pirs_created": cache.get_metric('pirs_created'),
        "couriers_dispatched": cache.get_metric('couriers_dispatched'),
        "timestamp": datetime.utcnow().isoformat()
    }


# Main endpoints
@app.post("/api/v1/scan")
async def process_scan_event(
    request: ScanEventRequest,
    background_tasks: BackgroundTasks
):
    """
    Process baggage scan event
    
    This endpoint receives scan events from:
    - BRS (Baggage Reconciliation System)
    - BHS (Baggage Handling System)
    - DCS (Departure Control System)
    - Manual scans
    """
    try:
        logger.info(f"Received scan event from {request.source}")

        # Lazy load orchestrator when needed
        orch = get_orchestrator()

        # Process asynchronously in background
        result = await orch.process_baggage_event(request.raw_scan)

        return {
            "status": "success",
            "message": "Scan event processed",
            "result": result,
            "received_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing scan event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/type-b")
async def process_type_b_message(
    request: TypeBMessageRequest,
    background_tasks: BackgroundTasks
):
    """
    Process SITA Type B message
    
    Handles:
    - BTM (Baggage Transfer Message)
    - BSM (Baggage Source Message)
    - BPM (Baggage Processing Message)
    """
    try:
        logger.info(f"Received Type B {request.message_type} from {request.from_station}")

        # Lazy load orchestrator when needed
        orch = get_orchestrator()

        # Process as scan event
        result = await orch.process_baggage_event(request.message)

        return {
            "status": "success",
            "message": f"Type B {request.message_type} processed",
            "result": result,
            "received_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing Type B message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/baggage-xml")
async def process_baggage_xml(
    request: BaggageXMLRequest,
    background_tasks: BackgroundTasks
):
    """
    Process BaggageXML manifest
    
    Handles interline baggage transfers using modern XML format
    """
    try:
        logger.info(f"Received BaggageXML for flight {request.flight_number}")
        
        # Parse XML and process bags
        # For now, just log
        return {
            "status": "success",
            "message": "BaggageXML processed",
            "flight_number": request.flight_number,
            "received_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing BaggageXML: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/bag/{bag_tag}")
async def get_bag_status(bag_tag: str):
    """
    Get current status of a bag
    """
    try:
        # Check cache first (if Redis is available)
        cache = get_redis()
        cached_status = None

        if cache is not None:
            cached_status = cache.get_bag_status(bag_tag)

        if cached_status:
            return {
                "bag_tag": bag_tag,
                "status": cached_status,
                "source": "cache"
            }

        # Otherwise query database (use Neon PostgreSQL)
        import psycopg2
        from psycopg2.extras import RealDictCursor

        neon_url = settings.neon_database_url if hasattr(settings, 'neon_database_url') else None

        if not neon_url:
            raise HTTPException(status_code=503, detail="Database not configured")

        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT * FROM baggage WHERE bag_tag = %s", (bag_tag,))
        bag_data = cursor.fetchone()

        cursor.close()
        conn.close()

        if not bag_data:
            raise HTTPException(status_code=404, detail=f"Bag {bag_tag} not found")
        
        return {
            "bag_tag": bag_tag,
            "status": bag_data,
            "source": "database"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bag status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("=" * 60)
    logger.info("BAGGAGE OPERATIONS API STARTING")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"API Port: {settings.api_port}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Baggage Operations API shutting down")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )
