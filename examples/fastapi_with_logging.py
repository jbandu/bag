"""
Example FastAPI Application with Structured Logging
Complete integration example for Copa Airlines demo

Run with: uvicorn examples.fastapi_with_logging:app --reload
"""

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
import time

# Import logging and middleware components
from src.logging.structured_logger import setup_logging, get_logger
from src.logging.log_context import AgentWorkflowLogger, DatabaseLogger, APICallLogger
from src.middleware.correlation_id import setup_correlation_id_middleware, get_trace_id_from_request
from src.metrics.collector import get_metrics_collector


# Initialize logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Baggage AI System",
    description="AI-powered baggage handling system for Copa Airlines",
    version="1.0.0"
)

# Add correlation ID middleware
setup_correlation_id_middleware(app)

# Get metrics collector
metrics = get_metrics_collector()


# Pydantic models
class BagCreate(BaseModel):
    bag_tag: str
    passenger_name: str
    flight_number: str
    origin: str
    destination: str


class ScanEvent(BaseModel):
    bag_tag: str
    scan_type: str
    location: str


class BagResponse(BaseModel):
    bag_tag: str
    status: str
    risk_level: str
    message: str


# Middleware to record metrics for all requests
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Record metrics for all requests"""
    start_time = time.time()

    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Record request metrics
        metrics.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            latency_ms=duration_ms,
            trace_id=get_trace_id_from_request(request)
        )

        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        metrics.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=500,
            latency_ms=duration_ms,
            trace_id=get_trace_id_from_request(request)
        )
        raise


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger = get_logger()
    logger.info("Health check requested")
    return {"status": "healthy", "service": "baggage-ai"}


# Create bag endpoint
@app.post("/api/v1/bags", response_model=BagResponse)
async def create_bag(request: Request, bag_data: BagCreate):
    """
    Create a new bag and process through scan workflow

    Demonstrates:
    - Getting trace_id from request
    - Creating logger with context
    - Using database logger
    - Recording metrics
    """
    # Get trace ID from request
    trace_id = get_trace_id_from_request(request)

    # Create logger with context
    logger = get_logger(
        trace_id=trace_id,
        bag_tag=bag_data.bag_tag
    )

    logger.info(
        "Creating bag",
        flight=bag_data.flight_number,
        origin=bag_data.origin,
        destination=bag_data.destination
    )

    try:
        # Simulate database operation with logging
        with DatabaseLogger(
            trace_id=trace_id,
            operation="CREATE_BAG",
            query="INSERT INTO bags (bag_tag, passenger_name, flight_number) VALUES ($1, $2, $3)",
            bag_tag=bag_data.bag_tag
        ) as db_logger:
            # Simulate DB operation
            time.sleep(0.01)  # Simulate latency
            db_logger.set_rows_affected(1)

        logger.info("Bag created successfully")

        return BagResponse(
            bag_tag=bag_data.bag_tag,
            status="checked_in",
            risk_level="low",
            message="Bag created successfully"
        )

    except Exception as e:
        logger.exception("Failed to create bag", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Process scan endpoint
@app.post("/api/v1/scans")
async def process_scan(request: Request, scan_data: ScanEvent):
    """
    Process bag scan through ScanProcessor agent workflow

    Demonstrates:
    - AgentWorkflowLogger for automatic workflow logging
    - Recording agent metrics
    - Step-by-step logging
    """
    # Get trace ID
    trace_id = get_trace_id_from_request(request)

    # Use agent workflow logger
    with AgentWorkflowLogger(
        trace_id=trace_id,
        agent_name="ScanProcessor",
        bag_tag=scan_data.bag_tag,
        input_data={
            "scan_type": scan_data.scan_type,
            "location": scan_data.location
        }
    ) as workflow_logger:
        # Step 1: Validate scan
        workflow_logger.log_step("validating_scan")
        time.sleep(0.05)  # Simulate processing

        # Step 2: Calculate risk score
        workflow_logger.log_step("calculating_risk")
        time.sleep(0.02)  # Simulate processing
        risk_score = 0.15  # Mock risk score

        # Step 3: Update database
        workflow_logger.log_step("updating_database")
        with DatabaseLogger(
            trace_id=trace_id,
            operation="UPDATE_BAG_LOCATION",
            query="UPDATE bags SET location = $1 WHERE bag_tag = $2",
            bag_tag=scan_data.bag_tag
        ) as db_logger:
            time.sleep(0.01)
            db_logger.set_rows_affected(1)

        # Step 4: Publish event
        workflow_logger.log_step("publishing_event")
        time.sleep(0.01)

        # Record agent metrics
        workflow_duration = time.time() * 1000  # Mock duration
        metrics.record_agent_call(
            agent_name="ScanProcessor",
            success=True,
            duration_ms=workflow_duration,
            trace_id=trace_id
        )

        return {
            "status": "success",
            "bag_tag": scan_data.bag_tag,
            "risk_score": risk_score,
            "location": scan_data.location
        }


# Get bag status endpoint
@app.get("/api/v1/bags/{bag_tag}")
async def get_bag_status(request: Request, bag_tag: str):
    """
    Get bag status

    Demonstrates:
    - Simple logging with context
    - Database query logging
    """
    trace_id = get_trace_id_from_request(request)

    logger = get_logger(trace_id=trace_id, bag_tag=bag_tag)
    logger.info("Getting bag status")

    try:
        # Simulate database query
        with DatabaseLogger(
            trace_id=trace_id,
            operation="GET_BAG",
            query="SELECT * FROM bags WHERE bag_tag = $1",
            bag_tag=bag_tag
        ) as db_logger:
            time.sleep(0.005)
            db_logger.set_rows_affected(1)

        # Mock response
        return {
            "bag_tag": bag_tag,
            "status": "in_transit",
            "current_location": "PTY_RAMP",
            "risk_level": "low"
        }

    except Exception as e:
        logger.exception("Failed to get bag status", error=str(e))
        raise HTTPException(status_code=404, detail="Bag not found")


# Mishandled bag workflow endpoint
@app.post("/api/v1/workflows/mishandled-bag")
async def handle_mishandled_bag(request: Request, bag_tag: str):
    """
    Process mishandled bag workflow

    Demonstrates:
    - Multi-step agent workflow
    - External API call logging
    - Complex workflow logging
    """
    trace_id = get_trace_id_from_request(request)

    with AgentWorkflowLogger(
        trace_id=trace_id,
        agent_name="MishandledBagHandler",
        bag_tag=bag_tag,
        input_data={"incident_type": "delayed_arrival"}
    ) as workflow_logger:
        # Step 1: Create PIR
        workflow_logger.log_step("creating_pir")

        with DatabaseLogger(
            trace_id=trace_id,
            operation="CREATE_PIR",
            query="INSERT INTO pirs (bag_tag, incident_type) VALUES ($1, $2)",
            bag_tag=bag_tag
        ) as db_logger:
            time.sleep(0.02)
            db_logger.set_rows_affected(1)

        # Step 2: File WorldTracer report
        workflow_logger.log_step("filing_worldtracer")

        with APICallLogger(
            trace_id=trace_id,
            service="WorldTracer",
            endpoint="/api/v1/pir",
            bag_tag=bag_tag
        ) as api_logger:
            # Simulate API call
            time.sleep(0.1)
            api_logger.set_status(201)

        # Step 3: Notify passenger
        workflow_logger.log_step("notifying_passenger")

        with APICallLogger(
            trace_id=trace_id,
            service="NotificationService",
            endpoint="/api/v1/notify",
            bag_tag=bag_tag
        ) as api_logger:
            time.sleep(0.05)
            api_logger.set_status(200)

        # Record agent metrics
        metrics.record_agent_call(
            agent_name="MishandledBagHandler",
            success=True,
            duration_ms=200.0,
            trace_id=trace_id
        )

        return {
            "status": "success",
            "pir_number": "MIAPTY20250115001",
            "worldtracer_ref": "CMAA123456",
            "passenger_notified": True
        }


# Error example endpoint
@app.post("/api/v1/test-error")
async def test_error(request: Request):
    """
    Test error logging

    Demonstrates:
    - Exception logging with full context
    - Stack trace capture
    """
    trace_id = get_trace_id_from_request(request)
    logger = get_logger(trace_id=trace_id)

    try:
        # Simulate error
        raise ValueError("Simulated error for testing")

    except Exception as e:
        logger.exception(
            "Test error occurred",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


# Metrics endpoint
@app.get("/api/v1/metrics")
async def get_metrics():
    """
    Get current metrics

    Returns real metrics from Redis
    """
    return {
        "current_stats": metrics.get_current_stats(),
        "latency_stats": metrics.get_latency_stats(),
        "agent_performance": metrics.get_agent_performance(),
        "db_health": metrics.get_db_health()
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "examples.fastapi_with_logging:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
