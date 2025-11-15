# Orchestrator Façade System

**Production-grade orchestrator for Copa Airlines Baggage Intelligence Platform**

## Overview

This document describes the new orchestrator façade system that provides:

1. **Layered Configuration** - Environment-based config (dev/staging/prod)
2. **Input Normalization** - All message types → canonical `BagEvent`
3. **Dependency Injection** - Clean FastAPI integration
4. **Graceful Degradation** - Works without external services
5. **Type Safety** - Pydantic models throughout

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Entry Points                             │
│  FastAPI │ Streamlit │ CLI │ Background Jobs               │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│              OrchestratorService (Façade)                   │
│  • Input normalization                                      │
│  • Parser selection                                         │
│  • Workflow routing                                         │
│  • Error handling                                           │
└────────────────┬───────────────────────────────────────────┘
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│ Scan    │ │ Type B  │ │ Baggage │
│ Parser  │ │ Parser  │ │   XML   │
└────┬────┘ └────┬────┘ └────┬────┘
     └───────────┼────────────┘
                 ▼
      ┌──────────────────┐
      │   Canonical      │
      │    BagEvent      │
      └────────┬─────────┘
               │
               ▼
      ┌──────────────────┐
      │  LangGraph       │
      │  Workflows       │
      │  (AI Agents)     │
      └──────────────────┘
```

---

## Quick Start

### 1. Configuration

Set environment variable to control configuration:

```bash
# Development (all mocks, relaxed security)
export ENV=development

# Staging (real DBs, mock notifications)
export ENV=staging

# Production (all real services)
export ENV=production
```

### 2. Using in FastAPI

```python
from fastapi import Depends
from app.dependencies import get_orchestrator
from app.orchestrator import OrchestratorService, initialize_orchestrator

# Initialize on startup
@app.on_event("startup")
async def startup():
    await initialize_orchestrator()

# Use in routes with dependency injection
@app.post("/events")
async def process_event(
    data: dict,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    result = await orchestrator.process_event(data)
    return result
```

### 3. Using in Streamlit

```python
from app.orchestrator import get_orchestrator
import asyncio

orchestrator = get_orchestrator()

# Process Type B message
result = asyncio.run(orchestrator.process_text(type_b_message))

# Process scan event
result = asyncio.run(orchestrator.process_scan(scan_data))
```

---

## Configuration System

### Layered Configuration

**config/base.py** - Safe defaults for all settings
**config/environments/development.py** - Dev overrides
**config/environments/staging.py** - Staging overrides
**config/environments/production.py** - Production overrides

### Environment Selection

The `ENV` environment variable determines which config loads:

| ENV Value | Config Loaded | Database | AI | External Services |
|-----------|---------------|----------|-----|-------------------|
| `development` | DevelopmentConfig | Optional | Optional | All MOCK |
| `staging` | StagingConfig | Required | Required | Mock notifications |
| `production` | ProductionConfig | Required | Required | All REAL |

### Development Mode

- No crashes if env vars missing
- All external services in mock mode
- Detailed debug logging
- Fast iteration

**Required env vars:**
- None! System runs with all defaults

**Optional env vars:**
```bash
ANTHROPIC_API_KEY=sk-...          # Enable AI agents
NEON_DATABASE_URL=postgresql://...  # Enable real database
```

### Staging Mode

- Real databases required
- Real AI processing
- Mock SMS/Email (save costs)
- Production-like testing

**Required env vars:**
```bash
ENV=staging
ANTHROPIC_API_KEY=sk-...
NEON_DATABASE_URL=postgresql://...
NEO4J_URI=neo4j+s://...
NEO4J_PASSWORD=...
REDIS_URL=redis://...
JWT_SECRET=...
SECRET_KEY=...
```

### Production Mode

- All real services
- Strict validation
- Security enforced

**Required env vars:**
All staging vars PLUS:
```bash
ENV=production
WORLDTRACER_API_KEY=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=...
SENDGRID_API_KEY=...
SENDGRID_FROM_EMAIL=...
```

**Feature flags to disable mocks:**
```bash
WORLDTRACER_USE_MOCK=false
TWILIO_USE_MOCK=false
SENDGRID_USE_MOCK=false
```

---

## Input Parsers

All parsers convert inputs to canonical `BagEvent` format.

### ScanEventParser

**Handles:**
- JSON from DCS/BHS/BRS systems
- Raw scan strings

**Example JSON input:**
```json
{
  "bag_tag": "0001234567",
  "flight_number": "CM101",
  "location": "PTY",
  "source": "DCS"
}
```

**Example raw input:**
```
0001234567 CM101 PTY
```

### TypeBParser

**Handles:**
- BTM (Baggage Transfer Message)
- BSM (Baggage Source Message)
- BPM (Baggage Processing Message)

**Example BTM:**
```
BTM
CM101/15NOV PTY MIA
.SMITH/JOHN 0001234567 T2P
```

**Example BSM:**
```
BSM
CM101/15NOV PTY
.SMITH/JOHN 0001234567 1PC/25KG
```

### Canonical BagEvent

All parsers output:

```python
{
  "event_id": "...",
  "event_type": "scan" | "type_b" | ...,
  "bag": {
    "bag_tag": "0001234567",
    "status": "in_transit",
    "weight_kg": 25.0
  },
  "flight": {
    "flight_number": "CM101",
    "origin": "PTY",
    "destination": "MIA"
  },
  "passenger": {
    "name": "SMITH/JOHN",
    "first_name": "JOHN",
    "last_name": "SMITH"
  },
  "location": {
    "station_code": "PTY"
  },
  "metadata": {
    "parser_name": "TypeBParser",
    "confidence_score": 0.9
  }
}
```

---

## Orchestrator API

### Main Method

```python
async def process_event(
    input_data: Union[str, Dict[str, Any]],
    event_type_hint: Optional[str] = None
) -> Dict[str, Any]
```

**Parameters:**
- `input_data`: Raw input (any format)
- `event_type_hint`: Optional hint ('scan', 'type_b')

**Returns:**
```json
{
  "success": true,
  "request_id": "req_abc123",
  "timestamp": "2024-11-15T10:30:00Z",
  "elapsed_ms": 45.2,
  "event": {
    "event_id": "...",
    "bag_tag": "0001234567",
    "flight": "CM101"
  },
  "result": {
    "status": "processed",
    ...
  }
}
```

### Convenience Methods

```python
# Process scan event
await orchestrator.process_scan(scan_dict)

# Process Type B message
await orchestrator.process_type_b(message_text)

# Process raw text (auto-detects type)
await orchestrator.process_text(raw_text)
```

---

## Error Handling

### Parsing Errors (400)

```json
{
  "success": false,
  "status_code": 400,
  "message": "Input parsing failed",
  "errors": [
    "Missing required field: bag_tag"
  ]
}
```

### Processing Errors (500)

```json
{
  "success": false,
  "status_code": 500,
  "message": "Internal processing error",
  "errors": [
    "Database connection failed"
  ]
}
```

### Graceful Degradation

If AI agents unavailable:
- Parser still works
- Returns mock response
- Logs warning
- Doesn't crash

---

## Testing

### Unit Tests

```bash
# Test parsers
pytest tests/test_parsers.py

# Test orchestrator
pytest tests/test_orchestrator.py
```

### Integration Test

```python
from app.orchestrator import get_orchestrator, initialize_orchestrator

async def test():
    await initialize_orchestrator()
    orchestrator = get_orchestrator()

    result = await orchestrator.process_scan({
        "bag_tag": "0001234567",
        "flight_number": "CM101",
        "location": "PTY"
    })

    assert result['success']
    print(result)
```

### Manual Testing

```bash
# Start API server
ENV=development python api_server_auth.py

# Test scan endpoint
curl -X POST http://localhost:8000/api/v1/scan \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_scan": "0001234567 CM101 PTY",
    "source": "DCS"
  }'

# Test Type B endpoint
curl -X POST http://localhost:8000/api/v1/type-b \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "BTM\nCM101/15NOV PTY MIA\n.SMITH/JOHN 0001234567 T2P",
    "message_type": "BTM",
    "from_station": "PTY",
    "to_station": "MIA"
  }'
```

---

## Migration Guide

### From Old System

**Before:**
```python
# Old lazy loading
orchestrator = None

def get_orchestrator():
    global orchestrator
    if orchestrator is None:
        from orchestrator.baggage_orchestrator import orchestrator as orch
        orchestrator = orch
    return orchestrator

# Usage
orch = get_orchestrator()
result = await orch.process_baggage_event(raw_scan)
```

**After:**
```python
# New dependency injection
from app.dependencies import get_orchestrator

@app.post("/events")
async def process_event(
    data: dict,
    orchestrator = Depends(get_orchestrator)
):
    result = await orchestrator.process_event(data)
    return result
```

### Configuration Migration

**Before:**
```python
from config.settings import settings

# Crashes if JWT_SECRET not set
```

**After:**
```python
from config import config

# Safe defaults in development
# Strict validation in production
```

---

## Troubleshooting

### "Config validation failed" in production

**Problem:** Missing required environment variables

**Solution:**
```bash
# Check which vars are missing
ENV=production python -c "from config import config"

# Set missing vars
export ANTHROPIC_API_KEY=sk-...
export NEON_DATABASE_URL=postgresql://...
```

### "AI agents not enabled"

**Problem:** Processing works but returns mock responses

**Solution:**
```bash
# Enable AI agents
export ANTHROPIC_API_KEY=sk-ant-...

# Disable mock mode
export WORLDTRACER_USE_MOCK=false
export TWILIO_USE_MOCK=false
export SENDGRID_USE_MOCK=false
```

### "Parsing failed"

**Problem:** Invalid input format

**Solution:**
- Check input matches expected format
- Use correct `event_type_hint`
- Check parser logs for details

---

## Files Reference

### Configuration
- `config/base.py` - Base configuration
- `config/environments/development.py` - Dev config
- `config/environments/staging.py` - Staging config
- `config/environments/production.py` - Production config
- `config/__init__.py` - Environment loader

### Parsers
- `app/parsers/base.py` - Base parser class
- `app/parsers/models.py` - Canonical event models
- `app/parsers/scan_parser.py` - Scan event parser
- `app/parsers/type_b_parser.py` - Type B message parser

### Orchestrator
- `app/orchestrator/facade.py` - Main orchestrator façade
- `app/orchestrator/__init__.py` - Orchestrator exports
- `app/dependencies.py` - FastAPI dependencies

### Integration
- `api_server_auth.py` - FastAPI server (updated)
- `test_orchestrator.py` - Integration tests

---

## Next Steps

1. **Add BaggageXML Parser** - Handle XML manifests
2. **Add WorldTracer Parser** - Handle PIR updates
3. **Workflow Routing** - Route to specific LangGraph workflows
4. **Circuit Breakers** - Add retry logic for external services
5. **Metrics** - Track parsing success rates
6. **Caching** - Cache parsed events

---

## Support

**Questions?** Check the code comments or ask in #baggage-platform Slack

**Issues?** Create ticket in GitHub with:
- Environment (dev/staging/prod)
- Input data (sanitized)
- Error logs
- Expected vs actual behavior
