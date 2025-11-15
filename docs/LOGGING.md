# Logging and Monitoring Guide

**Structured logging and correlation IDs for debugging multi-agent workflows**

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Structured Logging](#structured-logging)
- [Correlation IDs](#correlation-ids)
- [Key Log Points](#key-log-points)
- [Metrics Dashboard](#metrics-dashboard)
- [Log Aggregation on Railway](#log-aggregation-on-railway)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

The baggage AI system uses **structured logging** with **correlation IDs** to debug complex multi-agent workflows during the Copa Airlines demo.

### Key Features

- **Structured logging** with loguru (JSON in production, colored console in dev)
- **Correlation IDs** (trace_id) propagated through all requests and agents
- **Environment-based log levels**: DEBUG (dev), INFO (staging), WARNING (prod)
- **Real-time metrics** collected in Redis
- **Streamlit dashboard** for monitoring
- **grep-able logs** by bag_tag, trace_id, agent_name

---

## Quick Start

### 1. Setup FastAPI with Logging

```python
from fastapi import FastAPI
from src.middleware.correlation_id import setup_correlation_id_middleware
from src.logging.structured_logger import setup_logging

# Initialize logging
setup_logging()

# Create FastAPI app
app = FastAPI()

# Add correlation ID middleware
setup_correlation_id_middleware(app)
```

### 2. Use Structured Logger

```python
from src.logging.structured_logger import get_logger

# Create logger with context
logger = get_logger(
    trace_id="abc-123",
    bag_tag="CM123456",
    agent_name="ScanProcessor"
)

# Log with context
logger.info("Processing bag scan")
logger.error("Processing failed", error="Timeout")
```

### 3. Use Context Managers for Workflows

```python
from src.logging.log_context import AgentWorkflowLogger

# Automatically log workflow start/complete with duration
with AgentWorkflowLogger(
    trace_id="abc-123",
    agent_name="ScanProcessor",
    bag_tag="CM123456",
    input_data={"scan_type": "arrival"}
) as workflow_logger:
    # Do work
    workflow_logger.log_step("validating_scan")
    process_scan(data)
    workflow_logger.log_step("updating_database")
    update_db(data)
    # Automatically logs completion with duration
```

### 4. View Metrics Dashboard

```bash
# Run Streamlit dashboard
streamlit run dashboard.py

# Dashboard will be available at http://localhost:8501
```

---

## Structured Logging

### Log Formats

#### Development (Colored Console)
```
2025-01-15 14:23:45.123 | INFO     | api.bags:create_bag:42 | [trace_id=abc12345 bag=CM123456 agent=ScanProcessor] Bag checked in
```

#### Production (JSON)
```json
{
  "timestamp": "2025-01-15T14:23:45.123Z",
  "level": "INFO",
  "message": "Bag checked in",
  "module": "api.bags",
  "function": "create_bag",
  "line": 42,
  "context": {
    "trace_id": "abc-123-def-456",
    "bag_tag": "CM123456",
    "agent_name": "ScanProcessor",
    "event_id": "evt_001"
  }
}
```

### Environment Configuration

Set via `ENVIRONMENT` environment variable:

- **development**: DEBUG level, colored console
- **staging**: INFO level, colored console
- **production**: WARNING level, JSON format

```bash
# Development
export ENVIRONMENT=development

# Production
export ENVIRONMENT=production
```

### Log Levels

```python
logger.debug("Detailed debugging info")      # DEBUG level
logger.info("Normal operation")              # INFO level
logger.warning("Warning condition")          # WARNING level
logger.error("Error occurred")               # ERROR level
logger.critical("Critical failure")          # CRITICAL level
logger.exception("Error with stack trace")   # ERROR + traceback
```

---

## Correlation IDs

### How It Works

1. **Incoming request** ’ Middleware generates/extracts `trace_id`
2. **trace_id** set in context variables
3. **All logs** in request scope include `trace_id`
4. **All agent calls** receive and propagate `trace_id`
5. **Response headers** include `X-Trace-ID`

### Middleware Integration

```python
from src.middleware.correlation_id import setup_correlation_id_middleware

app = FastAPI()
setup_correlation_id_middleware(app)
```

### Getting Trace ID in Endpoints

```python
from fastapi import Request
from src.middleware.correlation_id import get_trace_id_from_request

@app.post("/api/v1/bags")
async def create_bag(request: Request, bag_data: BagCreate):
    trace_id = get_trace_id_from_request(request)

    logger = get_logger(trace_id=trace_id, bag_tag=bag_data.bag_tag)
    logger.info("Creating bag")

    # ... rest of endpoint
```

### Client-Side Usage

Clients can provide their own trace ID:

```bash
curl -X POST https://api.example.com/bags \
  -H "X-Trace-ID: my-custom-trace-id" \
  -H "Content-Type: application/json" \
  -d '{"bag_tag": "CM123456"}'
```

Response will include:
```
X-Trace-ID: my-custom-trace-id
```

---

## Key Log Points

### 1. Request Received

```python
logger.log_request(
    endpoint="/api/v1/bags",
    method="POST",
    bag_tag="CM123456"
)
```

Output:
```json
{
  "event_type": "request_received",
  "endpoint": "/api/v1/bags",
  "method": "POST",
  "bag_tag": "CM123456",
  "trace_id": "abc-123"
}
```

### 2. Agent Workflow Started

```python
logger.log_agent_start(
    agent_name="ScanProcessor",
    input_summary="scan_type=arrival, location=PTY_RAMP"
)
```

### 3. Database Operations

```python
from src.logging.log_context import DatabaseLogger

with DatabaseLogger(
    trace_id=trace_id,
    operation="CREATE_BAG",
    query="INSERT INTO bags ..."
) as db_logger:
    result = db.execute(query)
    db_logger.set_rows_affected(1)
```

Output:
```json
{
  "event_type": "db_operation",
  "operation": "CREATE_BAG",
  "query": "INSERT INTO bags ...",
  "latency_ms": 12.5,
  "rows_affected": 1
}
```

### 4. External API Calls

```python
from src.logging.log_context import APICallLogger

with APICallLogger(
    trace_id=trace_id,
    service="WorldTracer",
    endpoint="/api/pir"
) as api_logger:
    response = requests.post(url, json=data)
    api_logger.set_status(response.status_code)
```

Output:
```json
{
  "event_type": "api_call",
  "service": "WorldTracer",
  "endpoint": "/api/pir",
  "status_code": 201,
  "latency_ms": 245.7
}
```

### 5. Agent Workflow Completed

```python
logger.log_agent_complete(
    agent_name="ScanProcessor",
    outcome="success",
    duration_ms=523.4
)
```

### 6. Errors

```python
try:
    process_bag(bag_data)
except Exception as e:
    logger.exception(
        "Failed to process bag",
        bag_tag="CM123456",
        error=str(e)
    )
    raise
```

Output includes full stack trace in `exception` field.

---

## Metrics Dashboard

### Running the Dashboard

```bash
# Install Streamlit
pip install streamlit plotly

# Run dashboard
streamlit run dashboard.py
```

Dashboard available at: `http://localhost:8501`

### Dashboard Features

#### 1. **Current Metrics**
- Requests per minute
- Error count and rate
- Average latency
- P95 latency with SLA status

#### 2. **Request Volume Chart**
- Requests per minute over time window
- Configurable time window (15, 30, 60, 120 minutes)

#### 3. **Error Rate Chart**
- Requests, errors, and error rate percentage
- Dual-axis visualization

#### 4. **Latency Statistics**
- Min, avg, p50, p95, p99, max latencies
- SLA compliance indicator (p95 < 2000ms)

#### 5. **Agent Performance**
- Call volume per agent
- Success rate per agent
- Average latency per agent
- Detailed table with all metrics

#### 6. **Database Health**
- Total operations
- Error rate
- Average query latency
- Operations by type (CREATE, UPDATE, DELETE, etc.)

### Dashboard Controls

- **Auto-refresh**: Automatically refresh dashboard
- **Refresh interval**: Set refresh rate (1-60 seconds)
- **Time window**: Select time window for charts
- **Reset Metrics**: Clear all metrics (for testing)

---

## Log Aggregation on Railway

### 1. View Logs in Railway Dashboard

```bash
# Via Railway CLI
railway logs

# Follow logs in real-time
railway logs --follow
```

### 2. Filter Logs by Bag Tag

Production logs are in JSON format, making them easy to filter:

```bash
# Filter by bag_tag
railway logs | grep '"bag_tag":"CM123456"'

# Filter by trace_id
railway logs | grep '"trace_id":"abc-123"'

# Filter by agent_name
railway logs | grep '"agent_name":"ScanProcessor"'
```

### 3. Parse JSON Logs

```bash
# Install jq for JSON parsing
# On Railway, logs are available via dashboard or CLI

# Local log parsing
cat baggage_ai.log | jq 'select(.context.bag_tag == "CM123456")'

# Filter by event type
cat baggage_ai.log | jq 'select(.context.event_type == "agent_start")'

# Get all errors
cat baggage_ai.log | jq 'select(.level == "ERROR")'
```

### 4. Log Rotation

Logs automatically rotate at 100 MB and are retained for 7 days.

Configure in `src/logging/structured_logger.py`:

```python
logger.add(
    f"{log_dir}/baggage_ai.log",
    rotation="100 MB",    # Rotate at 100 MB
    retention="7 days",   # Keep for 7 days
    compression="zip"     # Compress old logs
)
```

### 5. Railway Environment Variables

Set these in Railway dashboard:

```bash
# Set environment
ENVIRONMENT=production

# Set log directory (optional)
LOG_DIR=/app/logs

# Redis URL for metrics
REDIS_URL=redis://redis:6379
```

---

## Best Practices

### 1. Always Use Context

```python
# Good: Context added to logger
logger = get_logger(trace_id=trace_id, bag_tag=bag_tag)
logger.info("Processing bag")

# Bad: No context
logger.info("Processing bag")
```

### 2. Use Context Managers for Workflows

```python
# Good: Automatic timing and error handling
with AgentWorkflowLogger(
    trace_id=trace_id,
    agent_name="ScanProcessor",
    bag_tag=bag_tag
) as workflow_logger:
    process_bag()

# Bad: Manual logging
logger.info("Starting workflow")
start = time.time()
try:
    process_bag()
    logger.info(f"Workflow completed in {time.time() - start}s")
except Exception as e:
    logger.error(f"Workflow failed: {e}")
```

### 3. Log Structured Data

```python
# Good: Structured fields
logger.info(
    "Bag processed",
    bag_tag="CM123456",
    status="delivered",
    duration_ms=523.4
)

# Bad: String formatting
logger.info(f"Bag CM123456 processed with status delivered in 523.4ms")
```

### 4. Include Context in Errors

```python
# Good: Full context
try:
    process_bag(bag_data)
except Exception as e:
    logger.exception(
        "Failed to process bag",
        bag_tag=bag_data.bag_tag,
        agent_name="ScanProcessor",
        input_data=bag_data.dict()
    )

# Bad: Minimal context
except Exception as e:
    logger.error(str(e))
```

### 5. Use Appropriate Log Levels

```python
# DEBUG: Detailed debugging info (only in dev)
logger.debug("Validating bag tag format", bag_tag=bag_tag)

# INFO: Normal operations
logger.info("Bag checked in", bag_tag=bag_tag)

# WARNING: Unexpected but handled
logger.warning("Slow database query", latency_ms=3000)

# ERROR: Errors that need attention
logger.error("Failed to create PIR", bag_tag=bag_tag, error=str(e))

# CRITICAL: System-level failures
logger.critical("Redis connection lost", error=str(e))
```

---

## Examples

### Example 1: Simple API Endpoint with Logging

```python
from fastapi import FastAPI, Request
from src.middleware.correlation_id import get_trace_id_from_request
from src.logging.structured_logger import get_logger

@app.post("/api/v1/bags")
async def create_bag(request: Request, bag_data: BagCreate):
    # Get trace ID
    trace_id = get_trace_id_from_request(request)

    # Create logger with context
    logger = get_logger(
        trace_id=trace_id,
        bag_tag=bag_data.bag_tag
    )

    # Log request
    logger.info("Creating bag", flight=bag_data.flight_number)

    try:
        # Create bag
        bag = create_bag_in_db(bag_data)

        # Log success
        logger.info("Bag created successfully", bag_id=bag.id)

        return {"bag_id": bag.id, "bag_tag": bag.bag_tag}

    except Exception as e:
        # Log error
        logger.exception("Failed to create bag", error=str(e))
        raise
```

### Example 2: Agent Workflow with Context Manager

```python
from src.logging.log_context import AgentWorkflowLogger

async def process_scan_workflow(scan_data: ScanData, trace_id: str):
    """Process scan with automatic logging"""

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
        validate_scan(scan_data)

        # Step 2: Calculate risk
        workflow_logger.log_step("calculating_risk")
        risk_score = calculate_risk(scan_data)

        # Step 3: Update database
        workflow_logger.log_step("updating_database")
        update_bag_location(scan_data.bag_tag, scan_data.location)

        # Step 4: Publish event
        workflow_logger.log_step("publishing_event")
        publish_scan_event(scan_data)

        return {"status": "success", "risk_score": risk_score}
```

### Example 3: Database Operation Logging

```python
from src.logging.log_context import DatabaseLogger

async def create_bag_in_db(bag_data: BagCreate, trace_id: str):
    """Create bag with database logging"""

    query = """
        INSERT INTO bags (bag_tag, passenger_name, flight_number)
        VALUES ($1, $2, $3)
        RETURNING id
    """

    with DatabaseLogger(
        trace_id=trace_id,
        operation="CREATE_BAG",
        query=query,
        bag_tag=bag_data.bag_tag
    ) as db_logger:
        result = await db.execute(
            query,
            bag_data.bag_tag,
            bag_data.passenger_name,
            bag_data.flight_number
        )
        db_logger.set_rows_affected(1)

        return result[0]["id"]
```

### Example 4: External API Call Logging

```python
from src.logging.log_context import APICallLogger
import httpx

async def create_worldtracer_pir(pir_data: PIRData, trace_id: str):
    """Create PIR in WorldTracer with API logging"""

    with APICallLogger(
        trace_id=trace_id,
        service="WorldTracer",
        endpoint="/api/v1/pir",
        bag_tag=pir_data.bag_tag
    ) as api_logger:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://worldtracer.example.com/api/v1/pir",
                json=pir_data.dict()
            )
            api_logger.set_status(response.status_code)

            if response.status_code == 201:
                return response.json()
            else:
                raise Exception(f"WorldTracer API error: {response.text}")
```

### Example 5: Grepping Logs for Debugging

```bash
# Find all logs for specific bag
railway logs | grep '"bag_tag":"CM123456"'

# Find all agent workflow logs
railway logs | grep '"event_type":"agent_start"'

# Find all errors
railway logs | grep '"level":"ERROR"'

# Trace specific request through entire journey
railway logs | grep '"trace_id":"abc-123-def-456"'

# Find slow database queries
railway logs | grep '"event_type":"db_operation"' | grep -E '"latency_ms":[0-9]{4,}'

# Find failed agent workflows
railway logs | grep '"event_type":"agent_complete"' | grep '"outcome":"failed"'
```

---

## Troubleshooting

### Logs Not Appearing

1. Check environment variable: `echo $ENVIRONMENT`
2. Check log level is appropriate (DEBUG in dev, INFO in staging)
3. Verify logging is initialized: `setup_logging()` called

### Trace IDs Not Propagating

1. Ensure middleware is added: `setup_correlation_id_middleware(app)`
2. Check trace ID is being passed to agent calls
3. Verify context variables are being set

### Metrics Not Showing in Dashboard

1. Check Redis is running: `redis-cli ping`
2. Verify metrics are being recorded
3. Check Redis URL: `echo $REDIS_URL`
4. Reset metrics if needed (button in dashboard)

### Dashboard Not Loading

1. Install dependencies: `pip install streamlit plotly`
2. Check Redis connection
3. Run with: `streamlit run dashboard.py`

---

## Summary

- **Structured logging** with loguru provides JSON logs in production, colored console in dev
- **Correlation IDs** (trace_id) propagate through all requests and agents
- **Context managers** automatically log workflow start/complete with duration
- **Metrics collector** tracks requests, errors, latency, agent performance in Redis
- **Streamlit dashboard** provides real-time monitoring
- **grep-able logs** make debugging easy on Railway

For Copa demo: Focus on grepping logs by `bag_tag` to trace bag journey through all 8 agents.
