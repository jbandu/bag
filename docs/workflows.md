# Workflow Execution Guide

Complete guide to all orchestrated workflows in the baggage handling system.

**Generated**: 2025-11-14 14:46:27

**Total Workflows**: 5

---

## Workflow Overview

| Workflow | Domain | Complexity | Avg Duration | Success Rate |
|----------|--------|------------|--------------|-------------|
| [High-Risk Bag Workflow](#wf001) | Exception Handling | HIGH | 45ms | 99.2% |
| [Transfer Coordination Workflow](#wf002) | Operations | MEDIUM | 30ms | 99.7% |
| [IRROPs Bulk Rebooking Workflow](#wf003) | Disruption Management | HIGH | 120ms | 98.5% |
| [Delivery Coordination Workflow](#wf004) | Customer Service | MEDIUM | 80ms | 99.0% |
| [Bulk Processing Workflow](#wf005) | Operations | MEDIUM | 200ms | 99.5% |

---

## High-Risk Bag Workflow {#wf001}

**ID**: `WF001`  
**Domain**: Exception Handling  
**Complexity**: HIGH

### Description

Handles bags with risk score > 0.7 requiring immediate attention and approval

### Execution Flow

**Entry Point**: `assess_risk`

#### Steps

1. **assess_risk** (Risk Scorer)
   - Calculate comprehensive risk score

2. **create_exception_case** (Case Manager)
   - Create high-priority case

3. **request_approval** (Case Manager)
   - Request human approval if needed

4. **create_pir** (WorldTracer Handler)
   - Create WorldTracer PIR

5. **notify_passenger** (Passenger Comms)
   - Send proactive notification

### Decision Points

- **IF** `risk_score > 0.9 AND value_usd > 500`  
  **THEN** require_human_approval

- **IF** `approved == true`  
  **THEN** proceed_to_pir

- **IF** `approved == false`  
  **THEN** notify_only

### Error Handling

| Error | Strategy |
|-------|----------|
| `PIR_creation_failed` | retry_3_times_then_alert |
| `notification_failed` | try_alternate_channel |

### Performance Metrics

| Metric | Value |
|--------|-------|
| Avg Duration Ms | 45 |
| P95 Duration Ms | 80 |
| Success Rate | 99.2% |

---

## Transfer Coordination Workflow {#wf002}

**ID**: `WF002`  
**Domain**: Operations  
**Complexity**: MEDIUM

### Description

Handles tight connections (< 60 minutes) with priority transfer processing

### Execution Flow

**Entry Point**: `assess_connection`

#### Steps

1. **assess_connection** (Risk Scorer)
   - Evaluate connection time

2. **prioritize_handling** (Scan Processor)
   - Flag for priority handling

3. **alert_ramp** (Passenger Comms)
   - Alert ramp personnel

4. **track_progress** (Scan Processor)
   - Monitor bag progress

### Decision Points

- **IF** `connection_time_minutes < 30`  
  **THEN** critical_priority

- **IF** `connection_time_minutes < 60`  
  **THEN** priority_handling

- **IF** `connection_time_minutes >= 60`  
  **THEN** normal_handling

### Error Handling

| Error | Strategy |
|-------|----------|
| `missed_connection` | trigger_mishandled_workflow |

### Performance Metrics

| Metric | Value |
|--------|-------|
| Avg Duration Ms | 30 |
| P95 Duration Ms | 55 |
| Success Rate | 99.7% |

---

## IRROPs Bulk Rebooking Workflow {#wf003}

**ID**: `WF003`  
**Domain**: Disruption Management  
**Complexity**: HIGH

### Description

Handles flight disruptions affecting 10+ bags with bulk processing

### Execution Flow

**Entry Point**: `detect_disruption`

#### Steps

1. **detect_disruption** (Scan Processor)
   - Detect flight cancellation/delay

2. **identify_affected_bags** (Data Fusion)
   - Find all bags on flight

3. **coordinate_rebooking** (Case Manager)
   - Coordinate bulk rebooking

4. **update_routing** (Data Fusion)
   - Update bag routing

5. **notify_stakeholders** (Passenger Comms)
   - Notify all passengers

### Decision Points

- **IF** `affected_count >= 10`  
  **THEN** enable_bulk_mode

- **IF** `alternate_flight_available`  
  **THEN** auto_rebook

- **IF** `no_alternate_available`  
  **THEN** create_pirs

### Error Handling

| Error | Strategy |
|-------|----------|
| `rebooking_failed` | escalate_to_ops_center |

### Performance Metrics

| Metric | Value |
|--------|-------|
| Avg Duration Ms | 120 |
| P95 Duration Ms | 250 |
| Success Rate | 98.5% |

---

## Delivery Coordination Workflow {#wf004}

**ID**: `WF004`  
**Domain**: Customer Service  
**Complexity**: MEDIUM

### Description

Books courier delivery for mishandled bags to passenger address

### Execution Flow

**Entry Point**: `assess_delivery_need`

#### Steps

1. **assess_delivery_need** (Case Manager)
   - Determine delivery requirements

2. **select_courier** (Courier Dispatch)
   - Select optimal courier

3. **book_courier** (Courier Dispatch)
   - Book delivery

4. **track_delivery** (Courier Dispatch)
   - Monitor delivery progress

5. **confirm_delivery** (Passenger Comms)
   - Confirm with passenger

### Decision Points

- **IF** `distance_km > 100`  
  **THEN** use_premium_courier

- **IF** `urgency == CRITICAL`  
  **THEN** expedited_delivery

- **IF** `cost_usd > 150`  
  **THEN** request_approval

### Error Handling

| Error | Strategy |
|-------|----------|
| `booking_failed` | try_alternate_courier |

### Performance Metrics

| Metric | Value |
|--------|-------|
| Avg Duration Ms | 80 |
| P95 Duration Ms | 150 |
| Success Rate | 99.0% |

---

## Bulk Processing Workflow {#wf005}

**ID**: `WF005`  
**Domain**: Operations  
**Complexity**: MEDIUM

### Description

Processes large batches of bags (50+ per batch) with parallel execution

### Execution Flow

**Entry Point**: `identify_scope`

#### Steps

1. **identify_scope** (Data Fusion)
   - Identify all bags in scope

2. **batch_process** (Data Fusion)
   - Create processing batches

3. **parallel_actions** (Multiple)
   - Execute actions in parallel

4. **consolidate_results** (Data Fusion)
   - Merge results

5. **report_outcomes** (Passenger Comms)
   - Report to stakeholders

### Decision Points

- **IF** `total_items > 100`  
  **THEN** use_max_parallelism

- **IF** `batch_failures > 5%`  
  **THEN** reduce_parallelism

### Error Handling

| Error | Strategy |
|-------|----------|
| `batch_failed` | retry_failed_items_individually |

### Performance Metrics

| Metric | Value |
|--------|-------|
| Avg Duration Ms | 200 |
| P95 Duration Ms | 400 |
| Success Rate | 99.5% |

---

