"""
FastAPI Server for Baggage Operations Platform (WITH AUTHENTICATION)

This is the updated version with multi-tenant authentication.

Features:
- API key authentication (X-API-Key header)
- JWT authentication (Bearer token)
- Role-based access control
- Audit logging
- Rate limiting

To use this version:
1. Run database migration: psql $NEON_DATABASE_URL -f migrations/add_auth_tables.sql
2. Run setup script: python scripts/setup_copa_auth.py
3. Update .env with JWT_SECRET and SECRET_KEY
4. Replace api_server.py with this file, or rename and update imports
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
import sys

from config.settings import settings

# Authentication imports
from app.auth import (
    auth_router,
    AuthDatabase,
    set_auth_dependencies,
    get_current_auth,
    get_current_airline,
    require_ops_or_admin,
    check_rate_limit,
    create_audit_log_entry,
    CurrentUser,
    CurrentAPIKey,
    CurrentAirline
)

# Database and health check imports
from app.database import (
    PostgresManager,
    Neo4jManager,
    RedisManager,
    DatabaseHealthChecker
)
from app.api import health_router, init_health_checker, init_external_services

# External services imports
from app.external import ExternalServicesManager

# Lazy imports for orchestrator and redis (only load when needed)
orchestrator = None
redis_cache = None

# Global database manager instances
postgres_manager = None
neo4j_manager = None
redis_manager = None
health_checker = None

# Global external services manager
external_services_manager = None

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
    description="AI-Powered Baggage Intelligence Platform with Multi-Tenant Authentication",
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


# Root endpoint (public)
@app.get("/")
async def root():
    """API Welcome and Documentation"""
    return {
        "service": "Baggage Operations Intelligence Platform",
        "version": "1.0.0",
        "description": "AI-Powered Baggage Intelligence with Multi-Tenant Authentication",
        "status": "operational",
        "authentication": {
            "api_key": "X-API-Key header",
            "jwt": "Authorization: Bearer <token>",
            "login": "POST /auth/login",
            "docs": "/docs"
        },
        "endpoints": {
            "health": {
                "overall": "GET /health",
                "database": "GET /health/database",
                "graph": "GET /health/graph",
                "cache": "GET /health/cache",
                "external": "GET /health/external",
                "ready": "GET /health/ready (Kubernetes readiness)",
                "live": "GET /health/live (Kubernetes liveness)"
            },
            "metrics": "/metrics",
            "api_docs": "/docs",
            "redoc": "/redoc",
            "auth": "/auth/*",
            "process_scan": "POST /api/v1/scan (authenticated)",
            "process_type_b": "POST /api/v1/type-b (authenticated)",
            "get_bag_status": "GET /api/v1/bag/{bag_tag} (authenticated)"
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


# Metrics endpoint (authenticated)
@app.get("/metrics")
async def get_metrics(
    auth: CurrentUser | CurrentAPIKey = Depends(get_current_auth)
):
    """Get operational metrics (authenticated)"""
    cache = get_redis()

    if cache is None:
        return {
            "status": "metrics_unavailable",
            "reason": "Redis not connected",
            "timestamp": datetime.utcnow().isoformat()
        }

    return {
        "airline": auth.airline.name,
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


# Main endpoints (all authenticated with ops_user role or higher)
@app.post("/api/v1/scan")
async def process_scan_event(
    request: Request,
    scan_request: ScanEventRequest,
    background_tasks: BackgroundTasks,
    auth: CurrentUser | CurrentAPIKey = Depends(require_ops_or_admin),
    airline: CurrentAirline = Depends(get_current_airline)
):
    """
    Process baggage scan event (authenticated)

    **Required Role:** ops_user, airline_admin, or system_admin

    This endpoint receives scan events from:
    - BRS (Baggage Reconciliation System)
    - BHS (Baggage Handling System)
    - DCS (Departure Control System)
    - Manual scans
    """
    try:
        logger.info(f"Received scan event from {scan_request.source} (airline: {airline.code})")

        # Lazy load orchestrator when needed
        orch = get_orchestrator()

        # Process asynchronously in background
        result = await orch.process_baggage_event(scan_request.raw_scan)

        # Audit log
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="process_scan_event",
            resource="scan_event",
            status="success",
            response_status=200
        )

        return {
            "status": "success",
            "message": "Scan event processed",
            "airline": airline.code,
            "result": result,
            "received_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error processing scan event: {str(e)}")
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="process_scan_event",
            resource="scan_event",
            status="failure",
            error_message=str(e),
            response_status=500
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/type-b")
async def process_type_b_message(
    request: Request,
    type_b_request: TypeBMessageRequest,
    background_tasks: BackgroundTasks,
    auth: CurrentUser | CurrentAPIKey = Depends(require_ops_or_admin),
    airline: CurrentAirline = Depends(get_current_airline)
):
    """
    Process SITA Type B message (authenticated)

    **Required Role:** ops_user, airline_admin, or system_admin

    Handles:
    - BTM (Baggage Transfer Message)
    - BSM (Baggage Source Message)
    - BPM (Baggage Processing Message)
    """
    try:
        logger.info(f"Received Type B {type_b_request.message_type} from {type_b_request.from_station} (airline: {airline.code})")

        # Lazy load orchestrator when needed
        orch = get_orchestrator()

        # Process as scan event
        result = await orch.process_baggage_event(type_b_request.message)

        # Audit log
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="process_type_b",
            resource="type_b_message",
            status="success",
            response_status=200
        )

        return {
            "status": "success",
            "message": f"Type B {type_b_request.message_type} processed",
            "airline": airline.code,
            "result": result,
            "received_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error processing Type B message: {str(e)}")
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="process_type_b",
            resource="type_b_message",
            status="failure",
            error_message=str(e),
            response_status=500
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/baggage-xml")
async def process_baggage_xml(
    request: Request,
    xml_request: BaggageXMLRequest,
    background_tasks: BackgroundTasks,
    auth: CurrentUser | CurrentAPIKey = Depends(require_ops_or_admin),
    airline: CurrentAirline = Depends(get_current_airline)
):
    """
    Process BaggageXML manifest (authenticated)

    **Required Role:** ops_user, airline_admin, or system_admin

    Handles interline baggage transfers using modern XML format
    """
    try:
        logger.info(f"Received BaggageXML for flight {xml_request.flight_number} (airline: {airline.code})")

        # Audit log
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="process_baggage_xml",
            resource="baggage_xml",
            resource_id=xml_request.flight_number,
            status="success",
            response_status=200
        )

        # Parse XML and process bags
        # For now, just log
        return {
            "status": "success",
            "message": "BaggageXML processed",
            "flight_number": xml_request.flight_number,
            "airline": airline.code,
            "received_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error processing BaggageXML: {str(e)}")
        await create_audit_log_entry(
            request=request,
            auth=auth,
            action="process_baggage_xml",
            resource="baggage_xml",
            status="failure",
            error_message=str(e),
            response_status=500
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/bag/{bag_tag}")
async def get_bag_status(
    bag_tag: str,
    auth: CurrentUser | CurrentAPIKey = Depends(get_current_auth),
    airline: CurrentAirline = Depends(get_current_airline)
):
    """
    Get current status of a bag (authenticated, tenant-isolated)

    Returns only bags belonging to the authenticated airline.
    """
    try:
        # Check cache first (if Redis is available)
        cache = get_redis()
        cached_status = None

        if cache is not None:
            cached_status = cache.get_bag_status(bag_tag)

        if cached_status:
            # Verify bag belongs to this airline
            if cached_status.get('airline_id') != airline.id:
                raise HTTPException(
                    status_code=404,
                    detail=f"Bag {bag_tag} not found"
                )
            return {
                "bag_tag": bag_tag,
                "status": cached_status,
                "source": "cache",
                "airline": airline.code
            }

        # Otherwise query database (use Neon PostgreSQL)
        import psycopg2
        from psycopg2.extras import RealDictCursor

        neon_url = settings.neon_database_url if hasattr(settings, 'neon_database_url') else None

        if not neon_url:
            raise HTTPException(status_code=503, detail="Database not configured")

        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # IMPORTANT: Filter by airline_id for tenant isolation
        cursor.execute(
            "SELECT * FROM baggage WHERE bag_tag = %s AND airline_id = %s",
            (bag_tag, airline.id)
        )
        bag_data = cursor.fetchone()

        cursor.close()
        conn.close()

        if not bag_data:
            raise HTTPException(status_code=404, detail=f"Bag {bag_tag} not found")

        return {
            "bag_tag": bag_tag,
            "status": bag_data,
            "source": "database",
            "airline": airline.code
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bag status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/bags")
async def list_bags(
    risk_threshold: float = None,
    status: str = None,
    limit: int = 100,
    auth: CurrentUser | CurrentAPIKey = Depends(get_current_auth),
    airline: CurrentAirline = Depends(get_current_airline)
):
    """
    List all bags with optional filtering (authenticated, tenant-isolated)

    Returns only bags belonging to the authenticated airline.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        neon_url = settings.neon_database_url if hasattr(settings, 'neon_database_url') else None

        if not neon_url:
            raise HTTPException(status_code=503, detail="Database not configured")

        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build query with filters + airline_id (tenant isolation)
        query = "SELECT * FROM baggage WHERE airline_id = %s"
        params = [airline.id]

        if risk_threshold is not None:
            query += " AND risk_score >= %s"
            params.append(risk_threshold)

        if status:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY risk_score DESC, created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        bags = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "count": len(bags),
            "bags": bags,
            "airline": airline.code
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing bags: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats(
    auth: CurrentUser | CurrentAPIKey = Depends(get_current_auth),
    airline: CurrentAirline = Depends(get_current_airline)
):
    """
    Get dashboard statistics and metrics (authenticated, tenant-isolated)
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        neon_url = settings.neon_database_url if hasattr(settings, 'neon_database_url') else None

        if not neon_url:
            raise HTTPException(status_code=503, detail="Database not configured")

        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get overall statistics (filtered by airline)
        cursor.execute("SELECT COUNT(*) as total FROM baggage WHERE airline_id = %s", [airline.id])
        total_bags = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as count FROM baggage WHERE airline_id = %s AND risk_score >= 0.7", [airline.id])
        high_risk = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM baggage WHERE airline_id = %s AND risk_score >= 0.3 AND risk_score < 0.7", [airline.id])
        medium_risk = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM baggage WHERE airline_id = %s AND risk_score < 0.3", [airline.id])
        low_risk = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM scan_events WHERE bag_tag IN (SELECT bag_tag FROM baggage WHERE airline_id = %s)", [airline.id])
        total_scans = cursor.fetchone()['count']

        # Get bags by status
        cursor.execute("SELECT status, COUNT(*) as count FROM baggage WHERE airline_id = %s GROUP BY status", [airline.id])
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

        # Get recent high-risk bags
        cursor.execute("""
            SELECT bag_tag, passenger_name, routing, status, risk_score, current_location
            FROM baggage
            WHERE airline_id = %s AND risk_score >= 0.7
            ORDER BY risk_score DESC, created_at DESC
            LIMIT 10
        """, [airline.id])
        high_risk_bags = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "airline": airline.code,
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


# Include routers
app.include_router(auth_router)
app.include_router(health_router)


# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    global postgres_manager, neo4j_manager, redis_manager, health_checker, external_services_manager

    logger.info("=" * 60)
    logger.info("BAGGAGE OPERATIONS API STARTING (WITH AUTHENTICATION)")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"API Port: {settings.api_port}")

    # Initialize production database managers
    logger.info("Initializing database connections...")

    # PostgreSQL (Neon)
    if settings.neon_database_url:
        try:
            postgres_manager = PostgresManager(
                database_url=settings.neon_database_url,
                min_connections=2,
                max_connections=20
            )
            await postgres_manager.connect()
            logger.info("✅ PostgreSQL connected")
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            # Continue without PostgreSQL - allow graceful degradation

    # Neo4j (Aura)
    try:
        neo4j_manager = Neo4jManager(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        await neo4j_manager.connect()
        logger.info("✅ Neo4j connected")
    except Exception as e:
        logger.error(f"❌ Neo4j connection failed: {e}")
        # Continue without Neo4j - allow graceful degradation

    # Redis (Upstash/Railway)
    try:
        redis_manager = RedisManager(redis_url=settings.redis_url)
        await redis_manager.connect()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        # Continue without Redis - allow graceful degradation

    # Initialize health checker
    if postgres_manager and neo4j_manager and redis_manager:
        health_checker = DatabaseHealthChecker(
            postgres=postgres_manager,
            neo4j=neo4j_manager,
            redis=redis_manager
        )
        init_health_checker(health_checker)
        logger.info("✅ Health check system initialized")
    else:
        logger.warning("⚠️ Health check system not fully initialized - some databases unavailable")

    # Initialize authentication database (uses same PostgreSQL connection)
    if settings.neon_database_url:
        auth_db = AuthDatabase(settings.neon_database_url)
        await auth_db.connect()

        # Initialize Redis (legacy - uses old redis_cache)
        redis_client = get_redis()

        # Set auth dependencies
        set_auth_dependencies(
            auth_db=auth_db,
            redis_client=redis_client,
            jwt_secret=settings.jwt_secret
        )

        logger.info("✅ Authentication system initialized")
    else:
        logger.warning("⚠️ Authentication disabled - no database URL configured")

    # Initialize external services
    logger.info("Initializing external services...")
    try:
        external_services_manager = ExternalServicesManager(
            # WorldTracer
            worldtracer_api_url=settings.worldtracer_api_url,
            worldtracer_api_key=settings.worldtracer_api_key,
            worldtracer_airline_code=settings.worldtracer_airline_code,
            worldtracer_use_mock=settings.worldtracer_use_mock,

            # Twilio
            twilio_account_sid=settings.twilio_account_sid,
            twilio_auth_token=settings.twilio_auth_token,
            twilio_from_number=settings.twilio_from_number,
            twilio_use_mock=settings.twilio_use_mock,

            # SendGrid
            sendgrid_api_key=settings.sendgrid_api_key,
            sendgrid_from_email=settings.sendgrid_from_email,
            sendgrid_from_name=settings.sendgrid_from_name,
            sendgrid_use_mock=settings.sendgrid_use_mock
        )

        await external_services_manager.connect_all()
        init_external_services(external_services_manager)

        # Log which services are in mock mode
        if settings.worldtracer_use_mock:
            logger.info("  🎭 WorldTracer: MOCK mode")
        else:
            logger.info("  ✅ WorldTracer: PRODUCTION mode")

        if settings.twilio_use_mock:
            logger.info("  🎭 Twilio: MOCK mode")
        else:
            logger.info("  ✅ Twilio: PRODUCTION mode")

        if settings.sendgrid_use_mock:
            logger.info("  🎭 SendGrid: MOCK mode")
        else:
            logger.info("  ✅ SendGrid: PRODUCTION mode")

        logger.info("✅ External services initialized")

    except Exception as e:
        logger.error(f"❌ External services initialization failed: {e}")
        logger.warning("⚠️ Continuing without external services")

    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("=" * 60)
    logger.info("BAGGAGE OPERATIONS API SHUTTING DOWN")
    logger.info("=" * 60)

    # Close database connections
    if postgres_manager:
        try:
            await postgres_manager.disconnect()
            logger.info("✅ PostgreSQL disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting PostgreSQL: {e}")

    if neo4j_manager:
        try:
            await neo4j_manager.disconnect()
            logger.info("✅ Neo4j disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting Neo4j: {e}")

    if redis_manager:
        try:
            await redis_manager.disconnect()
            logger.info("✅ Redis disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting Redis: {e}")

    # Disconnect external services
    if external_services_manager:
        try:
            await external_services_manager.disconnect_all()
            logger.info("✅ External services disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting external services: {e}")

    logger.info("Shutdown complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server_auth:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )
