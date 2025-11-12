"""
FastAPI Server for Baggage Operations Platform
Receives scan events from BRS, BHS, DCS, and Type B messages
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
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
    description="AI-Powered Baggage Intelligence Platform with Advanced Filtering, Batch Operations & Automated Passenger Notifications",
    version="1.2.0",
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


class PaginationParams(BaseModel):
    """Pagination parameters"""
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")


class BagFilterParams(BaseModel):
    """Advanced filtering for bags"""
    status: Optional[str] = Field(None, description="Filter by bag status")
    risk_min: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum risk score")
    risk_max: Optional[float] = Field(None, ge=0.0, le=1.0, description="Maximum risk score")
    location: Optional[str] = Field(None, description="Filter by current location (airport code)")
    airline: Optional[str] = Field(None, description="Filter by airline code")
    date_from: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    passenger_name: Optional[str] = Field(None, description="Filter by passenger name (partial match)")
    pnr: Optional[str] = Field(None, description="Filter by PNR")


class ScanFilterParams(BaseModel):
    """Advanced filtering for scan events"""
    bag_tag: Optional[str] = Field(None, description="Filter by bag tag")
    location: Optional[str] = Field(None, description="Filter by scan location")
    scan_type: Optional[str] = Field(None, description="Filter by scan type")
    date_from: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="Filter by status")


class BatchScanRequest(BaseModel):
    """Batch scan processing"""
    scans: List[Dict[str, Any]] = Field(..., description="List of scan events to process")
    source: str = Field(default="BATCH", description="Source system identifier")


class BatchBagQuery(BaseModel):
    """Batch bag status query"""
    bag_tags: List[str] = Field(..., description="List of bag tags to query", min_items=1, max_items=100)


class NotificationRequest(BaseModel):
    """Send notification to passenger"""
    bag_tag: str = Field(..., description="Bag tag identifier")
    passenger_phone: Optional[str] = Field(None, description="Phone number (E.164 format)")
    passenger_email: Optional[str] = Field(None, description="Email address")
    device_token: Optional[str] = Field(None, description="Firebase device token for push")
    passenger_name: str = Field(..., description="Passenger name")
    notification_type: str = Field(..., description="Type: high_risk, delayed, found, delivered")
    channels: List[str] = Field(default=["sms", "email"], description="Notification channels")
    custom_message: Optional[str] = Field(None, description="Optional custom message override")


class BulkNotificationRequest(BaseModel):
    """Send notifications to multiple passengers"""
    notifications: List[NotificationRequest] = Field(..., description="List of notifications", max_items=50)


# Root endpoint
@app.get("/")
async def root():
    """API Welcome and Documentation"""
    return {
        "service": "Baggage Operations Intelligence Platform",
        "version": "1.2.0",
        "description": "AI-Powered Baggage Intelligence with 8 Specialized Agents + Automated Notifications",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "api_docs": "/docs",
            "redoc": "/redoc",
            "process_scan": "POST /api/v1/scan",
            "process_type_b": "POST /api/v1/type-b",
            "process_xml": "POST /api/v1/baggage-xml",
            "get_bag_status": "GET /api/v1/bag/{bag_tag}",
            "list_bags": "GET /api/v1/bags (with pagination & filtering)",
            "list_scans": "GET /api/v1/scans (with pagination & filtering)",
            "batch_query_bags": "POST /api/v1/bags/batch",
            "batch_process_scans": "POST /api/v1/scans/batch",
            "dashboard_stats": "GET /api/v1/dashboard/stats",
            "send_notification": "POST /api/v1/notifications/send",
            "send_bulk_notifications": "POST /api/v1/notifications/bulk",
            "get_notification_history": "GET /api/v1/notifications/history/{bag_tag}"
        },
        "features": {
            "pagination": "All list endpoints support limit/offset pagination",
            "filtering": "Advanced filtering by status, risk, location, date range, etc.",
            "batch_operations": "Process up to 100 bags/scans in a single request",
            "notifications": "Multi-channel passenger communications (SMS, Email, Push)"
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


@app.get("/api/v1/bags")
async def list_bags(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    status: Optional[str] = Query(None, description="Filter by bag status"),
    risk_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum risk score"),
    risk_max: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum risk score"),
    location: Optional[str] = Query(None, description="Filter by current location"),
    airline: Optional[str] = Query(None, description="Filter by airline code"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    passenger_name: Optional[str] = Query(None, description="Filter by passenger name"),
    pnr: Optional[str] = Query(None, description="Filter by PNR")
):
    """
    List bags with advanced filtering and pagination

    **Pagination:**
    - `limit`: Maximum number of results (1-1000, default: 100)
    - `offset`: Number of results to skip (for pagination)

    **Filters:**
    - `status`: Bag status (checked_in, in_transit, loaded, etc.)
    - `risk_min`, `risk_max`: Risk score range (0.0-1.0)
    - `location`: Current location (airport code)
    - `airline`: Airline code
    - `date_from`, `date_to`: Date range (YYYY-MM-DD)
    - `passenger_name`: Partial name match
    - `pnr`: Booking reference

    **Example:**
    ```
    /api/v1/bags?limit=50&offset=0&risk_min=0.7&location=PTY
    ```
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        neon_url = settings.neon_database_url if hasattr(settings, 'neon_database_url') else None

        if not neon_url:
            raise HTTPException(status_code=503, detail="Database not configured")

        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build query with filters
        query = "SELECT * FROM baggage WHERE 1=1"
        params = []

        if status:
            query += " AND status = %s"
            params.append(status)

        if risk_min is not None:
            query += " AND risk_score >= %s"
            params.append(risk_min)

        if risk_max is not None:
            query += " AND risk_score <= %s"
            params.append(risk_max)

        if location:
            query += " AND current_location = %s"
            params.append(location)

        if airline:
            query += " AND bag_tag LIKE %s"
            params.append(f"{airline}%")

        if date_from:
            query += " AND created_at >= %s"
            params.append(date_from)

        if date_to:
            query += " AND created_at <= %s"
            params.append(f"{date_to} 23:59:59")

        if passenger_name:
            query += " AND passenger_name ILIKE %s"
            params.append(f"%{passenger_name}%")

        if pnr:
            query += " AND pnr = %s"
            params.append(pnr)

        # Get total count for pagination metadata
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['count']

        # Add ordering and pagination
        query += " ORDER BY risk_score DESC, created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        bags = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "total": total_count,
            "count": len(bags),
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(bags)) < total_count,
            "bags": bags
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing bags: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/scans")
async def list_scans(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    bag_tag: Optional[str] = Query(None, description="Filter by bag tag"),
    location: Optional[str] = Query(None, description="Filter by scan location"),
    scan_type: Optional[str] = Query(None, description="Filter by scan type"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """
    List scan events with advanced filtering and pagination

    **Pagination:**
    - `limit`: Maximum number of results (1-1000, default: 100)
    - `offset`: Number of results to skip

    **Filters:**
    - `bag_tag`: Specific bag tag
    - `location`: Scan location (airport/station code)
    - `scan_type`: Type of scan (check-in, sortation, load, etc.)
    - `date_from`, `date_to`: Date range
    - `status`: Scan status

    **Example:**
    ```
    /api/v1/scans?bag_tag=CM123456&limit=50
    ```
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        neon_url = settings.neon_database_url if hasattr(settings, 'neon_database_url') else None

        if not neon_url:
            raise HTTPException(status_code=503, detail="Database not configured")

        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build query with filters
        query = "SELECT * FROM scan_events WHERE 1=1"
        params = []

        if bag_tag:
            query += " AND bag_tag = %s"
            params.append(bag_tag)

        if location:
            query += " AND location = %s"
            params.append(location)

        if scan_type:
            query += " AND scan_type = %s"
            params.append(scan_type)

        if date_from:
            query += " AND timestamp >= %s"
            params.append(date_from)

        if date_to:
            query += " AND timestamp <= %s"
            params.append(f"{date_to} 23:59:59")

        if status:
            query += " AND status = %s"
            params.append(status)

        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['count']

        # Add ordering and pagination
        query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        scans = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "total": total_count,
            "count": len(scans),
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(scans)) < total_count,
            "scans": scans
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing scans: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/bags/batch")
async def batch_query_bags(request: BatchBagQuery):
    """
    Query status of multiple bags in a single request

    **Request Body:**
    ```json
    {
      "bag_tags": ["CM123456", "CM789012", "CM345678"]
    }
    ```

    **Response:** Returns status for all requested bags (up to 100 at once)
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        neon_url = settings.neon_database_url if hasattr(settings, 'neon_database_url') else None

        if not neon_url:
            raise HTTPException(status_code=503, detail="Database not configured")

        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Query all bags in one go
        placeholders = ', '.join(['%s'] * len(request.bag_tags))
        query = f"SELECT * FROM baggage WHERE bag_tag IN ({placeholders})"

        cursor.execute(query, request.bag_tags)
        bags = cursor.fetchall()

        cursor.close()
        conn.close()

        # Create a map for quick lookup
        bag_map = {bag['bag_tag']: bag for bag in bags}

        # Return results in same order as requested, with null for not found
        results = []
        for tag in request.bag_tags:
            results.append({
                "bag_tag": tag,
                "found": tag in bag_map,
                "data": bag_map.get(tag)
            })

        return {
            "total_requested": len(request.bag_tags),
            "total_found": len(bags),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/scans/batch")
async def batch_process_scans(request: BatchScanRequest, background_tasks: BackgroundTasks):
    """
    Process multiple scan events in a single request

    **Request Body:**
    ```json
    {
      "source": "BHS",
      "scans": [
        {"raw_scan": "Bag Tag: CM123456...", "metadata": {}},
        {"raw_scan": "Bag Tag: CM789012...", "metadata": {}}
      ]
    }
    ```

    **Response:** Returns processing status for each scan
    """
    try:
        logger.info(f"Received batch of {len(request.scans)} scans from {request.source}")

        orch = get_orchestrator()

        results = []
        for idx, scan_data in enumerate(request.scans):
            try:
                raw_scan = scan_data.get('raw_scan', '')
                result = await orch.process_baggage_event(raw_scan)
                results.append({
                    "index": idx,
                    "status": "success",
                    "result": result
                })
            except Exception as e:
                logger.error(f"Error processing scan {idx}: {str(e)}")
                results.append({
                    "index": idx,
                    "status": "error",
                    "error": str(e)
                })

        success_count = sum(1 for r in results if r['status'] == 'success')
        error_count = len(results) - success_count

        return {
            "status": "completed",
            "total_scans": len(request.scans),
            "successful": success_count,
            "failed": error_count,
            "results": results,
            "received_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats():
    """
    Get dashboard statistics and metrics
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        neon_url = settings.neon_database_url if hasattr(settings, 'neon_database_url') else None

        if not neon_url:
            raise HTTPException(status_code=503, detail="Database not configured")

        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get overall statistics
        cursor.execute("SELECT COUNT(*) as total FROM baggage")
        total_bags = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as count FROM baggage WHERE risk_score >= 0.7")
        high_risk = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM baggage WHERE risk_score >= 0.3 AND risk_score < 0.7")
        medium_risk = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM baggage WHERE risk_score < 0.3")
        low_risk = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM scan_events")
        total_scans = cursor.fetchone()['count']

        # Get bags by status
        cursor.execute("SELECT status, COUNT(*) as count FROM baggage GROUP BY status")
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

        # Get recent high-risk bags
        cursor.execute("""
            SELECT bag_tag, passenger_name, routing, status, risk_score, current_location
            FROM baggage
            WHERE risk_score >= 0.7
            ORDER BY risk_score DESC, created_at DESC
            LIMIT 10
        """)
        high_risk_bags = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "total_bags": total_bags,
            "high_risk_count": high_risk,
            "medium_risk_count": medium_risk,
            "low_risk_count": low_risk,
            "total_scans": total_scans,
            "status_breakdown": status_counts,
            "high_risk_bags": high_risk_bags
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# Notification Endpoints
# ========================================

def get_notification_service():
    """Lazy load notification service"""
    try:
        from utils.notifications import notification_service
        return notification_service
    except Exception as e:
        logger.error(f"Failed to load notification service: {e}")
        raise HTTPException(status_code=503, detail="Notification service unavailable")


@app.post("/api/v1/notifications/send")
async def send_notification(request: NotificationRequest):
    """
    Send notification to a passenger

    **Channels supported:**
    - `sms`: SMS via Twilio
    - `email`: Email via SendGrid
    - `push`: Push notification via Firebase

    **Notification types:**
    - `high_risk`: Bag requires attention
    - `delayed`: Bag delayed, arriving on next flight
    - `found`: Bag located and forwarded
    - `delivered`: Bag successfully delivered
    - `custom`: Use custom_message field

    **Example:**
    ```json
    {
      "bag_tag": "CM123456",
      "passenger_phone": "+15551234567",
      "passenger_email": "passenger@example.com",
      "passenger_name": "John Smith",
      "notification_type": "high_risk",
      "channels": ["sms", "email"]
    }
    ```
    """
    try:
        notif_service = get_notification_service()

        # Get bag data from database
        bag_data = {
            'bag_tag': request.bag_tag,
            'current_location': 'PTY',  # TODO: Fetch from database
            'destination': 'Unknown',    # TODO: Fetch from database
            'risk_score': 0.0            # TODO: Fetch from database
        }

        # Prepare passenger info
        passenger_info = {
            'name': request.passenger_name,
            'phone': request.passenger_phone,
            'email': request.passenger_email,
            'device_token': request.device_token
        }

        # Send multi-channel notification
        result = notif_service.send_multi_channel(
            channels=request.channels,
            passenger_info=passenger_info,
            notification_type=request.notification_type,
            bag_data=bag_data,
            custom_message=request.custom_message
        )

        logger.info(f"Notification sent for bag {request.bag_tag} | Success: {result['success_count']}/{result['total_channels']}")

        return {
            "status": "success",
            "notification_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/notifications/bulk")
async def send_bulk_notifications(request: BulkNotificationRequest, background_tasks: BackgroundTasks):
    """
    Send notifications to multiple passengers (up to 50 at once)

    **Example:**
    ```json
    {
      "notifications": [
        {
          "bag_tag": "CM123456",
          "passenger_phone": "+15551234567",
          "passenger_email": "passenger1@example.com",
          "passenger_name": "John Smith",
          "notification_type": "high_risk",
          "channels": ["sms", "email"]
        },
        {
          "bag_tag": "CM789012",
          "passenger_email": "passenger2@example.com",
          "passenger_name": "Jane Doe",
          "notification_type": "delayed",
          "channels": ["email"]
        }
      ]
    }
    ```
    """
    try:
        notif_service = get_notification_service()

        results = []
        for idx, notif_request in enumerate(request.notifications):
            try:
                # Get bag data (simplified for now)
                bag_data = {
                    'bag_tag': notif_request.bag_tag,
                    'current_location': 'PTY',
                    'destination': 'Unknown',
                    'risk_score': 0.0
                }

                passenger_info = {
                    'name': notif_request.passenger_name,
                    'phone': notif_request.passenger_phone,
                    'email': notif_request.passenger_email,
                    'device_token': notif_request.device_token
                }

                result = notif_service.send_multi_channel(
                    channels=notif_request.channels,
                    passenger_info=passenger_info,
                    notification_type=notif_request.notification_type,
                    bag_data=bag_data,
                    custom_message=notif_request.custom_message
                )

                results.append({
                    "index": idx,
                    "bag_tag": notif_request.bag_tag,
                    "status": "success",
                    "channels_sent": result['success_count'],
                    "total_channels": result['total_channels']
                })

            except Exception as e:
                logger.error(f"Error sending notification {idx}: {str(e)}")
                results.append({
                    "index": idx,
                    "bag_tag": notif_request.bag_tag if hasattr(notif_request, 'bag_tag') else "unknown",
                    "status": "error",
                    "error": str(e)
                })

        success_count = sum(1 for r in results if r['status'] == 'success')

        return {
            "status": "completed",
            "total_notifications": len(request.notifications),
            "successful": success_count,
            "failed": len(request.notifications) - success_count,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in bulk notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/notifications/history/{bag_tag}")
async def get_notification_history(bag_tag: str, limit: int = Query(10, ge=1, le=100)):
    """
    Get notification history for a specific bag

    Returns list of notifications sent for this bag tag
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        neon_url = settings.neon_database_url if hasattr(settings, 'neon_database_url') else None

        if not neon_url:
            return {
                "bag_tag": bag_tag,
                "notifications": [],
                "message": "Database not configured - history unavailable"
            }

        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT * FROM passenger_notifications
            WHERE bag_tag = %s
            ORDER BY sent_at DESC
            LIMIT %s
        """, (bag_tag, limit))

        notifications = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "bag_tag": bag_tag,
            "total_notifications": len(notifications),
            "notifications": notifications
        }

    except Exception as e:
        logger.warning(f"Error fetching notification history: {str(e)}")
        return {
            "bag_tag": bag_tag,
            "notifications": [],
            "error": str(e)
        }


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
