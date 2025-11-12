# Baggage Operations Knowledge Graph & Ontology

## Based on Mphasis Business Domain Modeling Methodology
## Using gist (Semantic Arts) Foundational Ontology

---

## 1. CORE DOMAIN CLASSES (Data Modeling)

### 1.1 RegisteredThings (External entities we track)

**bag:Passenger** extends gist:Person
- Properties:
  - pnr: gist:ID
  - name: gist:Text
  - eliteStatus: gist:Category (None, Silver, Gold, Platinum, Diamond)
  - contactEmail: gist:EmailAddress
  - contactPhone: gist:TelephoneNumber
  - lifetimeValue: gist:Magnitude (USD)
  - frequentFlyerNumber: gist:ID

**bag:Flight** extends gist:Task
- Properties:
  - flightNumber: gist:ID
  - origin: gist:GeoPoint
  - destination: gist:GeoPoint
  - scheduledDeparture: gist:TimeInterval
  - actualDeparture: gist:TimeInterval
  - scheduledArrival: gist:TimeInterval
  - actualArrival: gist:TimeInterval
  - aircraftType: gist:Category
  - status: gist:Category (Scheduled, Boarding, Departed, Arrived, Cancelled, Delayed)

**bag:Airport** extends gist:Place
- Properties:
  - iataCode: gist:ID (3-letter)
  - icaoCode: gist:ID (4-letter)
  - city: gist:Text
  - country: gist:Text
  - timezone: gist:Text
  - mctDomestic: gist:Duration (minutes)
  - mctInternational: gist:Duration (minutes)
  - performanceScore: gist:Magnitude (0-10)

**bag:ExternalSystem** extends gist:System
- Subtypes:
  - bag:DCS (Departure Control System)
  - bag:PSS (Passenger Service System)
  - bag:BHS (Baggage Handling System)
  - bag:WorldTracer (Global tracking)
  - bag:CourierSystem (3PL)

### 1.2 ManagedThings (We create and manage)

**bag:Baggage** extends gist:PhysicalThing
- Properties:
  - bagTag: gist:ID (unique identifier)
  - weight: gist:Magnitude (kg)
  - dimensions: gist:Magnitude (cm³)
  - color: gist:Category
  - type: gist:Category (Suitcase, Backpack, DuffelBag)
  - brand: gist:Text
  - contentsValue: gist:Magnitude (USD)
  - contentsDescription: gist:Text
  - specialHandling: gist:Category[] (Fragile, Medical, Sports, LiveAnimal)

**bag:BaggageDigitalTwin** extends gist:DigitalThing
- Properties:
  - physicalBag: bag:Baggage (reference)
  - currentStatus: bag:BagStatus
  - currentLocation: gist:GeoPoint
  - riskScore: gist:Magnitude (0-1)
  - riskLevel: gist:Category (Low, Medium, High, Critical)
  - riskFactors: gist:Text[]
  - journeyHistory: bag:ScanEvent[]
  - createdAt: gist:TimeInterval
  - updatedAt: gist:TimeInterval

**bag:PropertyIrregularityReport (PIR)** extends gist:Document
- Properties:
  - pirNumber: gist:ID
  - pirType: gist:Category (OHD, FIR, AHL, Delayed)
  - baggage: bag:Baggage
  - passenger: bag:Passenger
  - flight: bag:Flight
  - lastKnownLocation: gist:GeoPoint
  - expectedDestination: gist:GeoPoint
  - bagDescription: gist:Text
  - contentsDescription: gist:Text
  - status: gist:Category (Open, InProgress, Resolved, Closed)
  - filedAt: gist:TimeInterval
  - resolvedAt: gist:TimeInterval

**bag:ExceptionCase** extends gist:Task
- Properties:
  - caseId: gist:ID
  - baggage: bag:Baggage
  - priority: gist:Category (P0-Critical, P1-High, P2-Medium, P3-Low)
  - assignedTo: bag:Agent
  - status: gist:Category (Open, InProgress, PendingApproval, Resolved, Closed)
  - riskAssessment: bag:RiskAssessment
  - slaDeadline: gist:TimeInterval
  - actionsTaken: bag:Action[]

**bag:RiskAssessment** extends gist:Assessment
- Properties:
  - baggage: bag:Baggage
  - riskScore: gist:Magnitude (0-1)
  - riskLevel: gist:Category
  - primaryFactors: gist:Text[]
  - recommendedAction: gist:Category (Monitor, Alert, Intervene, DispatchCourier)
  - confidence: gist:Magnitude (0-1)
  - reasoning: gist:Text
  - connectionTimeMinutes: gist:Duration
  - mctMinutes: gist:Duration
  - airportPerformanceScore: gist:Magnitude
  - weatherImpactScore: gist:Magnitude

**bag:CourierDispatch** extends gist:Task
- Properties:
  - dispatchId: gist:ID
  - baggage: bag:Baggage
  - pir: bag:PropertyIrregularityReport
  - courierVendor: bag:CourierVendor
  - pickupLocation: gist:Address
  - deliveryAddress: gist:Address
  - estimatedDelivery: gist:TimeInterval
  - courierCost: gist:Magnitude (USD)
  - potentialClaimCost: gist:Magnitude (USD)
  - costBenefitRatio: gist:Magnitude
  - status: gist:Category (Pending, Approved, Dispatched, InTransit, Delivered)
  - requiresApproval: gist:Boolean
  - approvedBy: bag:Agent

### 1.3 EnrolledThings (Managed elsewhere, we enroll)

**bag:Agent** extends gist:Person
- Subtypes:
  - bag:BaggageOperationsAgent
  - bag:CustomerServiceAgent
  - bag:GroundHandlingAgent
  - bag:StationManager
  - bag:AIAgent (our 8 specialized agents)

**bag:AIAgent** extends bag:Agent
- Subtypes:
  - bag:ScanProcessorAgent
  - bag:RiskScorerAgent
  - bag:WorldTracerAgent
  - bag:SITAHandlerAgent
  - bag:BaggageXMLAgent
  - bag:CaseManagerAgent
  - bag:CourierDispatchAgent
  - bag:PassengerCommsAgent

---

## 2. CAPABILITY MODELING (What Gets Done)

### 2.1 Core Capabilities

**bag:BaggageTracking** extends gist:Capability
- Inputs: bag:ScanEvent
- Outputs: bag:BaggageDigitalTwin (updated)
- Responsibilities:
  - Capture scan events from multiple sources
  - Validate scan sequence logic
  - Update digital twin in real-time
  - Detect anomalies

**bag:RiskScoring** extends gist:Capability
- Inputs: bag:BaggageDigitalTwin, bag:Flight, bag:Airport
- Outputs: bag:RiskAssessment
- Responsibilities:
  - Analyze multiple risk factors
  - Calculate probability of mishandling
  - Recommend preventive actions
  - Trigger alerts for high-risk bags

**bag:ExceptionManagement** extends gist:Capability
- Inputs: bag:RiskAssessment, bag:Baggage
- Outputs: bag:ExceptionCase, bag:PropertyIrregularityReport
- Responsibilities:
  - Create exception cases
  - Route to appropriate teams
  - File PIRs with WorldTracer
  - Coordinate resolution

**bag:CourierManagement** extends gist:Capability
- Inputs: bag:ExceptionCase
- Outputs: bag:CourierDispatch
- Responsibilities:
  - Cost-benefit analysis
  - Vendor selection
  - Dispatch coordination
  - Delivery tracking

**bag:PassengerCommunication** extends gist:Capability
- Inputs: bag:RiskAssessment, bag:Passenger
- Outputs: bag:Notification
- Responsibilities:
  - Proactive notifications
  - Multi-channel delivery (SMS, Email, Push)
  - Status updates
  - Compensation processing

---

## 3. VALUE STREAM MODELING (REA Events)

### 3.1 Economic Events (Resources, Events, Agents)

**bag:ScanEvent** extends gist:Event
- Agent: bag:Scanner OR bag:Agent (manual scan)
- Resource: bag:Baggage
- Properties:
  - eventId: gist:ID
  - scanType: gist:Category (CheckIn, Sortation, Load, Offload, Arrival, Claim, Manual, BTM, BSM, BPM)
  - location: gist:GeoPoint
  - timestamp: gist:TimeInterval
  - scannerId: gist:ID
  - operatorId: gist:ID
  - flightNumber: gist:ID
  - errorCodes: gist:Text[]
- Commitments:
  - Updates bag:BaggageDigitalTwin
  - Triggers bag:RiskAssessment

**bag:MishandlingEvent** extends gist:Event
- Agent: bag:Airport OR bag:Airline
- Resource: bag:Baggage
- Properties:
  - mishandlingType: gist:Category (Delayed, Lost, Damaged, Pilfered, Offloaded)
  - reason: gist:Text
  - detectedAt: gist:TimeInterval
- Commitments:
  - Creates bag:PropertyIrregularityReport
  - Creates bag:ExceptionCase
  - May trigger bag:CourierDispatch

**bag:RecoveryEvent** extends gist:Event
- Agent: bag:Agent
- Resource: bag:Baggage
- Properties:
  - recoveryMethod: gist:Category (FoundInSystem, Rerouted, CourierDelivered)
  - resolvedAt: gist:TimeInterval
- Fulfillments:
  - Closes bag:PropertyIrregularityReport
  - Closes bag:ExceptionCase

### 3.2 Stages & Gates

**Stage 1: Check-In**
- Gate: Bag accepted at counter
- Authorized: Passenger checked in, bag tagged
- Financial Impact: Baggage fee collected (if applicable)

**Stage 2: Sortation**
- Gate: Bag scanned in BHS
- Authorized: Routing determined
- Financial Impact: None

**Stage 3: Loading**
- Gate: Bag loaded on aircraft
- Authorized: Weight & balance confirmed
- Financial Impact: None

**Stage 4: In-Flight**
- Gate: Aircraft departed
- Authorized: Manifest finalized
- Financial Impact: Liability period active (Montreal Convention)

**Stage 5: Arrival**
- Gate: Bag arrives at destination
- Authorized: Bag delivered to claim area
- Financial Impact: Liability reduced

**Stage 6: Claim**
- Gate: Passenger retrieves bag
- Authorized: Journey complete
- Financial Impact: No claim liability

**Exception Stage: Mishandling**
- Gate: Bag missed connection OR lost OR damaged
- Authorized: PIR filed
- Financial Impact: Potential claim cost up to $1,500 USD (Montreal Convention)

---

## 4. BUSINESS RULES & ROUTING DECISIONS

### 4.1 Inferencing Rules

**Rule: High Risk Detection**
```
IF bag:BaggageDigitalTwin.riskScore > 0.7
AND bag:Flight.status = "Boarding"
THEN
  CREATE bag:ExceptionCase WITH priority = "P1"
  ASSIGN TO bag:BaggageOperationsAgent
  NOTIFY bag:PassengerCommsAgent
```

**Rule: MCT Violation**
```
IF bag:Flight.connectionTime < bag:Airport.mctDomestic + 15 minutes
THEN
  SET bag:RiskAssessment.riskScore += 0.3
  ADD "MCT violation" TO bag:RiskAssessment.primaryFactors
```

**Rule: Scan Gap Detection**
```
IF CURRENT_TIME - bag:BaggageDigitalTwin.lastScanTime > 30 minutes
AND bag:Flight.status IN ["Boarding", "Departed"]
THEN
  SET bag:RiskAssessment.riskScore += 0.2
  ADD "Scan gap detected" TO bag:RiskAssessment.primaryFactors
  CREATE bag:Alert
```

### 4.2 Routing Decisions

**Routing: Exception Case Assignment**
```
IF bag:ExceptionCase.priority = "P0"
   THEN ROUTE TO bag:StationManager
ELSE IF bag:Passenger.eliteStatus IN ["Platinum", "Diamond"]
   THEN ROUTE TO bag:CustomerServiceAgent
ELSE IF bag:RiskAssessment.connectionTimeMinutes < 30
   THEN ROUTE TO bag:GroundHandlingAgent
ELSE
   ROUTE TO bag:BaggageOperationsAgent
```

**Routing: Courier Dispatch Decision**
```
IF bag:CourierDispatch.courierCost < 0.5 * bag:CourierDispatch.potentialClaimCost
   THEN AUTO-APPROVE
ELSE IF bag:Passenger.eliteStatus IN ["Platinum", "Diamond"]
   THEN REQUIRE_APPROVAL FROM bag:StationManager
ELSE IF bag:Baggage.contentsValue > 1000 USD
   THEN REQUIRE_APPROVAL FROM bag:StationManager
ELSE
   REJECT
```

### 4.3 State Decisions

**State Transition: Baggage Status**
```
bag:BagStatus = ENUM {
  CheckedIn,
  InSortation,
  Loaded,
  InTransit,
  Arrived,
  AtClaim,
  Claimed,
  Delayed,
  Mishandled,
  InRecovery
}

TRANSITIONS:
  CheckedIn → InSortation (on first BHS scan)
  InSortation → Loaded (on load scan)
  Loaded → InTransit (on flight departure)
  InTransit → Arrived (on flight arrival)
  Arrived → AtClaim (on carousel scan)
  AtClaim → Claimed (on passenger pickup)

  ANY → Delayed (on missed connection)
  ANY → Mishandled (on PIR creation)
  Mishandled → InRecovery (on courier dispatch)
  InRecovery → Claimed (on delivery confirmation)
```

---

## 5. RELATIONSHIPS

### 5.1 Core Relationships

**bag:Baggage -[belongsTo]-> bag:Passenger**
- Type: gist:isOwnedBy
- Cardinality: Many-to-One
- Properties: None

**bag:Baggage -[routedOn]-> bag:Flight**
- Type: gist:isAssociatedWith
- Cardinality: Many-to-Many
- Properties:
  - sequence: Integer (leg number)
  - isConnecting: Boolean

**bag:BaggageDigitalTwin -[representsPhysical]-> bag:Baggage**
- Type: gist:represents
- Cardinality: One-to-One
- Properties: None

**bag:ScanEvent -[scans]-> bag:Baggage**
- Type: gist:affects
- Cardinality: Many-to-One
- Properties: None

**bag:RiskAssessment -[assesses]-> bag:Baggage**
- Type: gist:evaluates
- Cardinality: Many-to-One
- Properties:
  - assessedAt: gist:TimeInterval

**bag:ExceptionCase -[concerns]-> bag:Baggage**
- Type: gist:isAbout
- Cardinality: Many-to-One
- Properties: None

**bag:PropertyIrregularityReport -[documents]-> bag:Baggage**
- Type: gist:describes
- Cardinality: Many-to-One
- Properties: None

**bag:Agent -[handles]-> bag:ExceptionCase**
- Type: gist:isResponsibleFor
- Cardinality: One-to-Many
- Properties:
  - assignedAt: gist:TimeInterval

---

## 6. MAPPING TO GIST ONTOLOGY

### Physical Layer
- **Ps (Physical Substance)** → bag:Baggage
- **Pe (Person)** → bag:Passenger, bag:Agent
- **Pl (Place)** → bag:Airport
- **Eq (Equipment)** → bag:Scanner, bag:BHS

### Consequa (What happens)
- **Ev (Event)** → bag:ScanEvent, bag:MishandlingEvent, bag:RecoveryEvent
- **Tr (Temporal Relation)** → bag:Flight (has start and end time)
- **Tl (Time Interval)** → All timestamps

### Digital Layer
- **Co (Content)** → bag:PropertyIrregularityReport
- **In (Intention)** → bag:RiskAssessment (intent to predict)
- **ID** → bag:bagTag, bag:pirNumber, bag:caseId
- **Ct (Commitment)** → bag:SLA deadlines
- **Ta (Task)** → bag:ExceptionCase, bag:CourierDispatch
- **As (Assignment)** → Agent assignment to cases

### Aggregate Layer
- **C (Composite)** → bag:Journey (collection of flights)
- **Cn (Component)** → Individual flight legs
- **S (System)** → bag:BaggageOperationsSystem
- **N (Network)** → All airports and airlines

### Magnitude & Literal
- **M (Magnitude)** → bag:weight, bag:riskScore, bag:courierCost
- **L (Literal)** → All text descriptions

---

## 7. KNOWLEDGE GRAPH STRUCTURE (Neo4j Implementation)

### Node Types

```cypher
// Physical Things
(:Baggage {bagTag, weight, color, type, contentsValue})
(:Passenger {pnr, name, eliteStatus, email, phone})
(:Flight {flightNumber, origin, destination, status})
(:Airport {iataCode, city, country, mct})

// Digital Twins
(:BaggageDigitalTwin {digitalTwinId, riskScore, riskLevel, currentStatus})

// Events
(:ScanEvent {eventId, scanType, location, timestamp})
(:MishandlingEvent {eventId, type, reason, timestamp})

// Cases & Reports
(:ExceptionCase {caseId, priority, status, slaDeadline})
(:PIR {pirNumber, pirType, status, filedAt})
(:RiskAssessment {riskScore, riskLevel, confidence})

// Agents
(:AIAgent {agentId, agentType, capabilities})
(:HumanAgent {agentId, role, team})

// Courier
(:CourierDispatch {dispatchId, vendor, cost, status})
```

### Relationship Types

```cypher
// Ownership & Attribution
(:Baggage)-[:BELONGS_TO]->(:Passenger)
(:Baggage)-[:ROUTED_ON {sequence}]->(:Flight)
(:BaggageDigitalTwin)-[:REPRESENTS]->(:Baggage)

// Events
(:ScanEvent)-[:SCANS]->(:Baggage)
(:ScanEvent)-[:AT_LOCATION]->(:Airport)
(:MishandlingEvent)-[:AFFECTS]->(:Baggage)

// Journey Tracking
(:BaggageDigitalTwin)-[:CURRENT_LOCATION]->(:Airport)
(:BaggageDigitalTwin)-[:HAS_SCAN {sequence, timestamp}]->(:ScanEvent)

// Risk & Assessment
(:RiskAssessment)-[:ASSESSES]->(:Baggage)
(:RiskAssessment)-[:CONSIDERS_FACTOR {weight}]->(:RiskFactor)

// Case Management
(:ExceptionCase)-[:CONCERNS]->(:Baggage)
(:ExceptionCase)-[:ASSIGNED_TO]->(:HumanAgent)
(:ExceptionCase)-[:HAS_ASSESSMENT]->(:RiskAssessment)
(:ExceptionCase)-[:GENERATED_PIR]->(:PIR)

// Courier
(:CourierDispatch)-[:FOR_BAGGAGE]->(:Baggage)
(:CourierDispatch)-[:PICKUP_FROM]->(:Airport)
(:CourierDispatch)-[:DELIVER_TO]->(:Address)

// Agent Actions
(:AIAgent)-[:PROCESSED]->(:ScanEvent)
(:AIAgent)-[:CREATED]->(:RiskAssessment)
(:AIAgent)-[:TRIGGERED]->(:ExceptionCase)
```

---

## 8. SAMPLE KNOWLEDGE GRAPH QUERIES

### Query 1: Get complete journey for a bag
```cypher
MATCH journey = (:Baggage {bagTag: 'CM123456'})-[:HAS_SCAN*]->(:ScanEvent)
RETURN journey
ORDER BY ScanEvent.timestamp
```

### Query 2: Find all high-risk bags currently in system
```cypher
MATCH (dt:BaggageDigitalTwin)-[:REPRESENTS]->(b:Baggage)
WHERE dt.riskScore > 0.7
AND dt.currentStatus IN ['InSortation', 'Loaded']
RETURN b, dt
ORDER BY dt.riskScore DESC
```

### Query 3: Identify bags at risk of missing connections
```cypher
MATCH (b:Baggage)-[:ROUTED_ON]->(f1:Flight)-[:CONNECTS_TO]->(f2:Flight)
WHERE f2.scheduledDeparture - f1.actualArrival < duration({minutes: 45})
RETURN b, f1, f2
```

### Query 4: Get airport performance metrics
```cypher
MATCH (a:Airport)<-[:AT_LOCATION]-(se:ScanEvent)<-[:HAS_SCAN]-(dt:BaggageDigitalTwin)
WITH a,
     COUNT(DISTINCT dt) as totalBags,
     SUM(CASE WHEN dt.riskLevel = 'High' THEN 1 ELSE 0 END) as highRiskBags
RETURN a.iataCode,
       totalBags,
       highRiskBags,
       (highRiskBags * 100.0 / totalBags) as exceptionRate
ORDER BY exceptionRate DESC
```

### Query 5: Find all exceptions requiring immediate attention
```cypher
MATCH (ec:ExceptionCase)-[:CONCERNS]->(b:Baggage)-[:BELONGS_TO]->(p:Passenger)
WHERE ec.priority = 'P0'
AND ec.status = 'Open'
AND p.eliteStatus IN ['Platinum', 'Diamond']
RETURN ec, b, p
ORDER BY ec.slaDeadline ASC
```

---

## 9. INTEGRATION WITH AI AGENTS

Each AI agent queries and updates the knowledge graph:

**ScanProcessorAgent:**
- Creates (:ScanEvent) nodes
- Updates (:BaggageDigitalTwin) properties
- Creates [:HAS_SCAN] relationships

**RiskScorerAgent:**
- Reads (:BaggageDigitalTwin), (:Flight), (:Airport)
- Creates (:RiskAssessment) nodes
- Updates (:BaggageDigitalTwin).riskScore

**WorldTracerAgent:**
- Creates (:PIR) nodes when mishandling detected
- Creates [:GENERATED_PIR] relationships
- Updates PIR status on resolution

**CaseManagerAgent:**
- Creates (:ExceptionCase) nodes
- Creates [:ASSIGNED_TO] relationships
- Updates case status and SLA tracking

**CourierDispatchAgent:**
- Creates (:CourierDispatch) nodes
- Performs cost-benefit queries
- Creates [:FOR_BAGGAGE] relationships

**PassengerCommsAgent:**
- Reads passenger preferences
- Creates (:Notification) nodes
- Tracks delivery status

---

## 10. ONTOLOGY VERSIONING & GOVERNANCE

**Version:** 1.0.0 (Initial)
**Maintained by:** Number Labs
**Standard:** Based on gist 11.0.0 (Semantic Arts)
**Last Updated:** 2024-11-11

**Change Log:**
- 2024-11-11: Initial ontology creation
- Future: Add weather events, aircraft maintenance, crew relationships

**Governance:**
- Monthly review of class structure
- Quarterly alignment with gist updates
- Continuous refinement based on operational learnings
