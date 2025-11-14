# Integration Guide

Guide to all external system integrations via the Semantic API Gateway.

**Generated**: 2025-11-14 14:46:27

**Total Integrations**: 7

---

## Integration Overview

| System | Type | Criticality | API Type | Rate Limit |
|--------|------|-------------|----------|------------|
| [WorldTracer](#sys001) | Mishandled Baggage System | CRITICAL | SOAP/REST | 100 requests/minute |
| [DCS (Departure Control System)](#sys002) | Airline Passenger System | CRITICAL | REST | 500 requests/minute |
| [BHS (Baggage Handling System)](#sys003) | Facility Automation | CRITICAL | Message Queue (AMQP) | 10,000 events/minute |
| [Type B Messaging](#sys004) | Industry Standard Messaging | HIGH | TCP/IP Socket | 1,000 messages/minute |
| [BaggageXML](#sys005) | IATA Resolution 753 | HIGH | REST/SOAP | 200 requests/minute |
| [Courier Services](#sys006) | Third-party Logistics | MEDIUM | REST | 50 requests/minute per carrier |
| [Notification Services](#sys007) | Multi-channel Communications | MEDIUM | REST | 1,000 messages/minute |

---

## WorldTracer {#sys001}

**ID**: `SYS001`  
**Type**: Mishandled Baggage System  
**Criticality**: CRITICAL

### Description

IATA global baggage tracing system for mishandled bags

### API Specifications

**API Type**: SOAP/REST  
**Authentication**: API Key + OAuth 2.0  
**Rate Limits**: 100 requests/minute

### Endpoints

| Path | Method | Description |
|------|--------|-------------|
| `/pir/create` | POST | Create new PIR |
| `/pir/{pir_number}` | GET | Retrieve PIR |
| `/pir/{pir_number}` | PUT | Update PIR |
| `/pir/search` | POST | Search PIRs |

### Data Formats

**Input**: JSON with IATA standard fields  
**Output**: JSON PIR object with status

### SLA

99.9% uptime, <500ms response time

---

## DCS (Departure Control System) {#sys002}

**ID**: `SYS002`  
**Type**: Airline Passenger System  
**Criticality**: CRITICAL

### Description

Manages passenger check-in, boarding, and baggage data

### API Specifications

**API Type**: REST  
**Authentication**: API Key + mTLS  
**Rate Limits**: 500 requests/minute

### Endpoints

| Path | Method | Description |
|------|--------|-------------|
| `/passenger/{pnr}` | GET | Get passenger data |
| `/baggage/{bag_tag}` | GET | Get baggage data |
| `/baggage` | POST | Create baggage record |

### Data Formats

**Input**: JSON with airline-specific schema  
**Output**: JSON passenger/baggage objects

### SLA

99.95% uptime, <200ms response time

---

## BHS (Baggage Handling System) {#sys003}

**ID**: `SYS003`  
**Type**: Facility Automation  
**Criticality**: CRITICAL

### Description

Automated baggage sorting and tracking system

### API Specifications

**API Type**: Message Queue (AMQP)  
**Authentication**: Username/Password + SSL  
**Rate Limits**: 10,000 events/minute

### Endpoints

| Path | Method | Description |
|------|--------|-------------|
| `scan.events` | CONSUME | Receive scan events |
| `commands.routing` | PUBLISH | Send routing commands |

### Data Formats

**Input**: Binary scan event format  
**Output**: JSON-encoded scan data

### SLA

99.99% uptime, <10ms latency

---

## Type B Messaging {#sys004}

**ID**: `SYS004`  
**Type**: Industry Standard Messaging  
**Criticality**: HIGH

### Description

IATA Type B telegram messaging for baggage manifests

### API Specifications

**API Type**: TCP/IP Socket  
**Authentication**: IP Whitelist + Message signing  
**Rate Limits**: 1,000 messages/minute

### Endpoints

| Path | Method | Description |
|------|--------|-------------|
| `N/A` | RECEIVE | Receive Type B messages |
| `N/A` | SEND | Send Type B messages |

### Data Formats

**Input**: IATA Type B text format  
**Output**: Parsed JSON objects

### SLA

99.5% uptime

---

## BaggageXML {#sys005}

**ID**: `SYS005`  
**Type**: IATA Resolution 753  
**Criticality**: HIGH

### Description

IATA XML standard for baggage tracking

### API Specifications

**API Type**: REST/SOAP  
**Authentication**: IATA credentials + certificate  
**Rate Limits**: 200 requests/minute

### Endpoints

| Path | Method | Description |
|------|--------|-------------|
| `/baggage/track` | POST | Submit tracking event |
| `/baggage/{bag_tag}/history` | GET | Get bag history |

### Data Formats

**Input**: IATA BaggageXML schema  
**Output**: IATA BaggageXML response

### SLA

99.7% uptime

---

## Courier Services {#sys006}

**ID**: `SYS006`  
**Type**: Third-party Logistics  
**Criticality**: MEDIUM

### Description

FedEx, UPS, DHL APIs for delivery booking and tracking

### API Specifications

**API Type**: REST  
**Authentication**: API Key  
**Rate Limits**: 50 requests/minute per carrier

### Endpoints

| Path | Method | Description |
|------|--------|-------------|
| `/shipments` | POST | Book shipment |
| `/shipments/{tracking_id}` | GET | Track shipment |
| `/shipments/{tracking_id}` | DELETE | Cancel shipment |

### Data Formats

**Input**: Carrier-specific JSON  
**Output**: JSON booking confirmation

### SLA

99.0% uptime

---

## Notification Services {#sys007}

**ID**: `SYS007`  
**Type**: Multi-channel Communications  
**Criticality**: MEDIUM

### Description

Twilio, SendGrid for SMS, email, push notifications

### API Specifications

**API Type**: REST  
**Authentication**: API Key  
**Rate Limits**: 1,000 messages/minute

### Endpoints

| Path | Method | Description |
|------|--------|-------------|
| `/sms` | POST | Send SMS |
| `/email` | POST | Send email |
| `/push` | POST | Send push notification |

### Data Formats

**Input**: JSON with recipient, message, channel  
**Output**: JSON delivery confirmation

### SLA

99.5% uptime

---

