# Semantic API Reference

Complete reference for the Semantic API Gateway.

**Generated**: 2025-11-14 14:46:27

**Base URL**: `https://api.baggage-ai.example.com/v1`

---

## Overview

The Semantic API Gateway provides a unified interface to 7 external systems, reducing 56 integration points to just 8.

### Key Features

- **Unified Interface**: Single API for all operations
- **Semantic Operations**: High-level business operations
- **Automatic Retries**: Configurable retry logic with exponential backoff
- **Circuit Breaking**: Automatic failure detection and recovery
- **Rate Limiting**: Token bucket and sliding window algorithms
- **Intelligent Caching**: TTL-based caching with invalidation

---

## Authentication

All API requests require authentication via API key:

```http
Authorization: Bearer YOUR_API_KEY
```

## Semantic Operations

### Get Bag Status

`GET /bags/{bag_tag}/status`

Retrieve complete bag status from all sources

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `bag_tag` | string | ✓ | 10-digit bag tag |

**Example Response**:

```json
{
  "bag_tag": "0016123456789",
  "status": "LOADED",
  "location": "MAKEUP_01",
  "flight": "UA1234",
  "risk_score": 0.65,
  "confidence": 0.95,
  "sources": [
    "DCS",
    "BHS",
    "BaggageXML"
  ]
}
```

### Create PIR

`POST /pir/create`

Create PIR in WorldTracer for mishandled bag

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `bag_tag` | string | ✓ | Bag tag number |
| `passenger_name` | string | ✓ | Passenger name |
| `flight_number` | string | ✓ | Flight number |

**Example Response**:

```json
{
  "pir_number": "SFOUA123456",
  "status": "CREATED",
  "timestamp": "2025-11-14T10:30:00Z"
}
```

### Book Courier

`POST /courier/book`

Book courier delivery for mishandled bag

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `bag_tag` | string | ✓ | Bag tag number |
| `address` | string | ✓ | Delivery address |
| `urgency` | string |  | normal or urgent |

**Example Response**:

```json
{
  "booking_id": "BOOKING_0016123456789",
  "carrier": "FedEx",
  "cost_usd": 75.0,
  "eta": "2025-11-15T14:00:00Z"
}
```

## Error Codes

| Code | Description | Action |
|------|-------------|--------|
| 200 | Success | N/A |
| 400 | Bad Request | Check request parameters |
| 401 | Unauthorized | Check API key |
| 429 | Rate Limit Exceeded | Wait and retry |
| 500 | Internal Server Error | Retry with backoff |
| 503 | Service Unavailable | Circuit breaker open, retry later |

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/bags/*` | 500 requests/minute |
| `/pir/*` | 100 requests/minute |
| `/courier/*` | 50 requests/minute |

