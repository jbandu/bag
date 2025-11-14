# Agent Reference

Comprehensive reference for all AI agents in the baggage handling system.

**Generated**: 2025-11-14 14:46:27

**Total Agents**: 8

---

## Agent Overview

| Agent | Specialization | Autonomy Level | Throughput |
|-------|----------------|----------------|------------|
| [Scan Processor Agent](#ag001) | Baggage scan event processing | HIGH | 1000+ scans/minute |
| [Risk Scorer Agent](#ag002) | Risk assessment and scoring | HIGH | 500+ assessments/minute |
| [WorldTracer Handler Agent](#ag003) | WorldTracer PIR management | MEDIUM | 100+ PIRs/minute |
| [Case Manager Agent](#ag004) | Exception case orchestration | MEDIUM | 200+ cases/minute |
| [Courier Dispatch Agent](#ag005) | Delivery logistics coordination | MEDIUM | 50+ bookings/minute |
| [Passenger Communications Agent](#ag006) | Multi-channel passenger notifications | HIGH | 1000+ notifications/minute |
| [Data Fusion Agent](#ag007) | Multi-source data reconciliation | HIGH | 500+ fusions/minute |
| [Semantic Enrichment Agent](#ag008) | Contextual data augmentation | HIGH | 800+ enrichments/minute |

---

## Scan Processor Agent {#ag001}

**ID**: `AG001`  
**Specialization**: Baggage scan event processing  
**Autonomy Level**: HIGH

### Purpose

Processes scan events from BHS, validates sequences, detects anomalies

### Capabilities

- Parse scan events from multiple formats
- Validate scan sequences for logical consistency
- Detect missing scans or out-of-sequence events
- Enrich scan data with contextual information

### Inputs/Outputs

**Inputs**:
- BHS scan events
- Location data
- Timestamp

**Outputs**:
- Validated scan data
- Anomaly alerts
- Enriched context

### Dependencies

- BHS System
- Risk Scorer Agent

### Performance Characteristics

| Metric | Value |
|--------|-------|
| Throughput | 1000+ scans/minute |
| Latency | <10ms per scan |
| Accuracy | 99.9% |

---

## Risk Scorer Agent {#ag002}

**ID**: `AG002`  
**Specialization**: Risk assessment and scoring  
**Autonomy Level**: HIGH

### Purpose

Calculates risk scores based on multiple factors, triggers alerts for high-risk bags

### Capabilities

- Calculate multi-factor risk scores
- Identify risk factors (tight connections, high value, etc.)
- Classify priority levels (CRITICAL, HIGH, MEDIUM, LOW)
- Trigger automated alerts for high-risk bags

### Inputs/Outputs

**Inputs**:
- Bag data
- Flight data
- Connection times
- Value declarations

**Outputs**:
- Risk scores
- Risk factors
- Priority classifications
- Alerts

### Dependencies

- Scan Processor Agent
- Case Manager Agent

### Performance Characteristics

| Metric | Value |
|--------|-------|
| Throughput | 500+ assessments/minute |
| Latency | <15ms per assessment |
| Accuracy | 95% |

---

## WorldTracer Handler Agent {#ag003}

**ID**: `AG003`  
**Specialization**: WorldTracer PIR management  
**Autonomy Level**: MEDIUM

### Purpose

Creates and manages PIRs in WorldTracer system for mishandled bags

### Capabilities

- Create PIRs with complete bag details
- Update PIR status based on bag location
- Search existing PIRs to avoid duplicates
- Match found bags to open PIRs

### Inputs/Outputs

**Inputs**:
- Bag data
- Passenger data
- Mishandling reason

**Outputs**:
- PIR numbers
- PIR status
- Match results

### Dependencies

- WorldTracer System
- Case Manager Agent

### Performance Characteristics

| Metric | Value |
|--------|-------|
| Throughput | 100+ PIRs/minute |
| Latency | <50ms per operation |
| Accuracy | 98% |

---

## Case Manager Agent {#ag004}

**ID**: `AG004`  
**Specialization**: Exception case orchestration  
**Autonomy Level**: MEDIUM

### Purpose

Creates and manages exception cases, coordinates resolution across agents

### Capabilities

- Create exception cases for mishandled bags
- Assign cases to appropriate teams
- Track case resolution status
- Coordinate multi-agent workflows

### Inputs/Outputs

**Inputs**:
- Risk assessments
- Mishandling events
- PIR data

**Outputs**:
- Case IDs
- Case status
- Resolution plans
- Assignments

### Dependencies

- Risk Scorer
- WorldTracer Handler
- Courier Dispatch
- Passenger Comms

### Performance Characteristics

| Metric | Value |
|--------|-------|
| Throughput | 200+ cases/minute |
| Latency | <20ms per case |
| Accuracy | 97% |

---

## Courier Dispatch Agent {#ag005}

**ID**: `AG005`  
**Specialization**: Delivery logistics coordination  
**Autonomy Level**: MEDIUM

### Purpose

Selects courier services, books deliveries, tracks shipments

### Capabilities

- Select best courier based on cost, speed, reliability
- Book deliveries with multiple carriers
- Track delivery status in real-time
- Optimize delivery routes and costs

### Inputs/Outputs

**Inputs**:
- Bag location
- Passenger address
- Urgency level
- Cost constraints

**Outputs**:
- Booking confirmations
- Tracking numbers
- Delivery ETAs
- Cost estimates

### Dependencies

- Courier System
- Case Manager Agent

### Performance Characteristics

| Metric | Value |
|--------|-------|
| Throughput | 50+ bookings/minute |
| Latency | <100ms per booking |
| Accuracy | 96% |

---

## Passenger Communications Agent {#ag006}

**ID**: `AG006`  
**Specialization**: Multi-channel passenger notifications  
**Autonomy Level**: HIGH

### Purpose

Sends personalized notifications via SMS, email, push notifications

### Capabilities

- Compose contextual messages based on situation
- Select optimal communication channel
- Personalize messages with passenger details
- Track notification delivery and engagement

### Inputs/Outputs

**Inputs**:
- Case data
- Passenger preferences
- Urgency level
- Message templates

**Outputs**:
- Notifications sent
- Delivery confirmations
- Engagement metrics

### Dependencies

- Notification System
- Case Manager Agent

### Performance Characteristics

| Metric | Value |
|--------|-------|
| Throughput | 1000+ notifications/minute |
| Latency | <25ms per notification |
| Delivery Rate | 99.5% |

---

## Data Fusion Agent {#ag007}

**ID**: `AG007`  
**Specialization**: Multi-source data reconciliation  
**Autonomy Level**: HIGH

### Purpose

Fuses data from multiple sources, resolves conflicts, calculates confidence scores

### Capabilities

- Merge data from 7+ external systems
- Detect and resolve data conflicts
- Calculate confidence scores based on source reliability
- Maintain data quality metrics

### Inputs/Outputs

**Inputs**:
- Data from DCS, BHS, WorldTracer, Type B, XML, Courier, Notifications

**Outputs**:
- Canonical bag data
- Conflict reports
- Confidence scores
- Quality metrics

### Dependencies

- All external systems via Semantic Gateway

### Performance Characteristics

| Metric | Value |
|--------|-------|
| Throughput | 500+ fusions/minute |
| Latency | <30ms per fusion |
| Accuracy | 98% |

---

## Semantic Enrichment Agent {#ag008}

**ID**: `AG008`  
**Specialization**: Contextual data augmentation  
**Autonomy Level**: HIGH

### Purpose

Enriches bag data with semantic context, risk factors, handling instructions, tags

### Capabilities

- Calculate risk scores from multiple factors
- Generate handling instructions based on context
- Add semantic tags for search and filtering
- Recommend next steps based on current state

### Inputs/Outputs

**Inputs**:
- Canonical bag data
- Flight data
- Historical patterns

**Outputs**:
- Risk assessments
- Handling instructions
- Contextual tags
- Next step recommendations

### Dependencies

- Data Fusion Agent
- Memory System

### Performance Characteristics

| Metric | Value |
|--------|-------|
| Throughput | 800+ enrichments/minute |
| Latency | <20ms per enrichment |
| Accuracy | 96% |

---

