# Ontology Reference
Complete knowledge graph ontology for AI-powered baggage handling system.

**Generated**: 2025-11-14 14:46:27

---

## Node Types

The knowledge graph contains **7 node types**:

### Bag

**Description**: Physical baggage item tracked through the system

**Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `bag_tag` | String | ✓ | Unique 10-digit identifier |
| `weight_kg` | Float |  | Weight in kilograms |
| `value_usd` | Float |  | Declared value in USD |
| `status` | String | ✓ | Current status (CHECKED_IN, LOADED, etc.) |

### Passenger

**Description**: Traveler who owns baggage

**Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `pnr` | String | ✓ | Passenger Name Record |
| `name` | String | ✓ | Full passenger name |
| `phone` | String |  | Contact phone number |
| `email` | String |  | Contact email address |

### Flight

**Description**: Commercial flight carrying baggage

**Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `flight_number` | String | ✓ | Flight identifier (e.g., UA1234) |
| `origin` | String | ✓ | Origin airport code |
| `destination` | String | ✓ | Destination airport code |
| `scheduled_departure` | DateTime | ✓ | Scheduled departure time |

### Event

**Description**: Baggage handling event (scan, status change, etc.)

**Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `event_type` | String | ✓ | Type of event |
| `timestamp` | DateTime | ✓ | When event occurred |
| `location` | String |  | Where event occurred |
| `agent_name` | String |  | Agent that triggered event |

### Workflow

**Description**: Orchestrated sequence of agent actions

**Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | String | ✓ | Workflow identifier |
| `name` | String | ✓ | Workflow name |
| `domain` | String | ✓ | Business domain |
| `complexity` | String |  | LOW, MEDIUM, HIGH |

### Agent

**Description**: Autonomous AI agent performing specific tasks

**Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | String | ✓ | Agent identifier |
| `name` | String | ✓ | Agent name |
| `specialization` | String | ✓ | Agent's area of expertise |
| `autonomy_level` | String |  | Level of autonomy |

### System

**Description**: External system integrated via gateway

**Properties**:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | String | ✓ | System identifier |
| `name` | String | ✓ | System name |
| `type` | String | ✓ | System type |
| `criticality` | String |  | CRITICAL, HIGH, MEDIUM, LOW |

## Relationship Types

The knowledge graph contains **6 relationship types**:

### BELONGS_TO

**From**: `Bag` → **To**: `Passenger`

**Description**: Bag belongs to passenger


### BOOKED_ON

**From**: `Bag` → **To**: `Flight`

**Description**: Bag is booked on flight

**Properties**:

| Property | Type | Description |
|----------|------|-------------|
| `connection_time_minutes` | Integer | Time until flight departure |

### HAD_EVENT

**From**: `Bag` → **To**: `Event`

**Description**: Bag experienced event

**Properties**:

| Property | Type | Description |
|----------|------|-------------|
| `at` | DateTime | When relationship was created |

### HANDLES

**From**: `Agent` → **To**: `Workflow`

**Description**: Agent handles workflow execution


### DEPENDS_ON

**From**: `Workflow` → **To**: `Workflow`

**Description**: Workflow depends on another workflow

**Properties**:

| Property | Type | Description |
|----------|------|-------------|
| `dependency_type` | String | Type of dependency |

### INTEGRATES_WITH

**From**: `Agent` → **To**: `System`

**Description**: Agent integrates with external system


## Constraints and Indexes

| Label | Property | Constraint Type |
|-------|----------|----------------|
| `Bag` | `bag_tag` | UNIQUE |
| `Passenger` | `pnr` | UNIQUE |
| `Flight` | `flight_number` | INDEX |
| `Agent` | `id` | UNIQUE |
| `Workflow` | `id` | UNIQUE |

## Example Cypher Queries

### Find all bags for a passenger

```cypher
MATCH (p:Passenger {pnr: 'ABC123'})<-[:BELONGS_TO]-(b:Bag)
RETURN b
```

### Trace bag journey

```cypher
MATCH (b:Bag {bag_tag: '0016123456789'})-[:HAD_EVENT]->(e:Event)
RETURN e ORDER BY e.timestamp
```

### Find high-risk bags

```cypher
MATCH (b:Bag)-[:BOOKED_ON]->(f:Flight)
WHERE b.risk_score > 0.7
RETURN b, f
```

