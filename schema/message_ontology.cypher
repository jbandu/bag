// ============================================================================
// MESSAGE ONTOLOGY - NEO4J SCHEMA FOR AGENT COMMUNICATION
// ============================================================================
// Purpose: Track all inter-agent messages with semantic properties
// Version: 1.0.0
// Date: 2024-11-13
//
// Message Flow:
// 1. ScanProcessorAgent → RiskScorerAgent
// 2. RiskScorerAgent → CaseManagerAgent, CourierDispatchAgent
// 3. WorldTracerAgent → CaseManagerAgent, PassengerCommsAgent
// 4. SITAHandlerAgent → All agents
// 5. BaggageXMLAgent → RiskScorerAgent, WorldTracerAgent
// 6. CaseManagerAgent → All agents (orchestration)
// 7. CourierDispatchAgent → CaseManagerAgent, PassengerCommsAgent
// 8. PassengerCommsAgent → External systems
// ============================================================================

// ============================================================================
// PART 1: MESSAGE NODE CONSTRAINTS
// ============================================================================

// Base Message Constraints
CREATE CONSTRAINT message_id_unique IF NOT EXISTS
FOR (m:Message) REQUIRE m.messageId IS UNIQUE;

CREATE CONSTRAINT message_id_exists IF NOT EXISTS
FOR (m:Message) REQUIRE m.messageId IS NOT NULL;

CREATE CONSTRAINT message_timestamp_exists IF NOT EXISTS
FOR (m:Message) REQUIRE m.timestamp IS NOT NULL;

// Specific Message Type Constraints
CREATE CONSTRAINT scan_message_bag_tag IF NOT EXISTS
FOR (m:ScanMessage) REQUIRE m.bagTag IS NOT NULL;

CREATE CONSTRAINT risk_message_bag_tag IF NOT EXISTS
FOR (m:RiskMessage) REQUIRE m.bagTag IS NOT NULL;

CREATE CONSTRAINT exception_message_case_id IF NOT EXISTS
FOR (m:ExceptionMessage) REQUIRE m.caseId IS NOT NULL;

CREATE CONSTRAINT worldtracer_message_pir IF NOT EXISTS
FOR (m:WorldTracerMessage) REQUIRE m.pirNumber IS NOT NULL;

CREATE CONSTRAINT dispatch_message_courier_id IF NOT EXISTS
FOR (m:DispatchMessage) REQUIRE m.courierId IS NOT NULL;

// ============================================================================
// PART 2: MESSAGE NODE INDEXES
// ============================================================================

// Base Message Indexes
CREATE INDEX message_timestamp IF NOT EXISTS FOR (m:Message) ON (m.timestamp);
CREATE INDEX message_source_agent IF NOT EXISTS FOR (m:Message) ON (m.sourceAgent);
CREATE INDEX message_semantic_intent IF NOT EXISTS FOR (m:Message) ON (m.semanticIntent);
CREATE INDEX message_priority IF NOT EXISTS FOR (m:Message) ON (m.priority);
CREATE INDEX message_correlation_id IF NOT EXISTS FOR (m:Message) ON (m.correlationId);

// Specific Message Type Indexes
CREATE INDEX scan_message_bag_tag IF NOT EXISTS FOR (m:ScanMessage) ON (m.bagTag);
CREATE INDEX scan_message_type IF NOT EXISTS FOR (m:ScanMessage) ON (m.scanType);
CREATE INDEX scan_message_location IF NOT EXISTS FOR (m:ScanMessage) ON (m.location);

CREATE INDEX risk_message_bag_tag IF NOT EXISTS FOR (m:RiskMessage) ON (m.bagTag);
CREATE INDEX risk_message_risk_level IF NOT EXISTS FOR (m:RiskMessage) ON (m.riskLevel);
CREATE INDEX risk_message_risk_score IF NOT EXISTS FOR (m:RiskMessage) ON (m.riskScore);

CREATE INDEX exception_message_case_id IF NOT EXISTS FOR (m:ExceptionMessage) ON (m.caseId);
CREATE INDEX exception_message_priority IF NOT EXISTS FOR (m:ExceptionMessage) ON (m.exceptionPriority);
CREATE INDEX exception_message_type IF NOT EXISTS FOR (m:ExceptionMessage) ON (m.exceptionType);

CREATE INDEX worldtracer_message_pir IF NOT EXISTS FOR (m:WorldTracerMessage) ON (m.pirNumber);
CREATE INDEX worldtracer_message_status IF NOT EXISTS FOR (m:WorldTracerMessage) ON (m.status);

CREATE INDEX typeb_message_type IF NOT EXISTS FOR (m:TypeBMessage) ON (m.messageType);
CREATE INDEX typeb_message_source IF NOT EXISTS FOR (m:TypeBMessage) ON (m.sourceSystem);

CREATE INDEX xml_message_airline IF NOT EXISTS FOR (m:XMLMessage) ON (m.airlineCode);
CREATE INDEX xml_message_flight IF NOT EXISTS FOR (m:XMLMessage) ON (m.flightNumber);

CREATE INDEX dispatch_message_courier IF NOT EXISTS FOR (m:DispatchMessage) ON (m.courierId);
CREATE INDEX dispatch_message_status IF NOT EXISTS FOR (m:DispatchMessage) ON (m.status);
CREATE INDEX dispatch_message_vendor IF NOT EXISTS FOR (m:DispatchMessage) ON (m.courierVendor);

CREATE INDEX notification_message_passenger IF NOT EXISTS FOR (m:NotificationMessage) ON (m.passengerId);
CREATE INDEX notification_message_channel IF NOT EXISTS FOR (m:NotificationMessage) ON (m.channel);
CREATE INDEX notification_message_status IF NOT EXISTS FOR (m:NotificationMessage) ON (m.deliveryStatus);

// ============================================================================
// PART 3: MESSAGE NODE DEFINITIONS
// ============================================================================

// ----------------------------------------------------------------------------
// :Message - Base message type (abstract)
// ----------------------------------------------------------------------------
/*
All messages inherit these properties:

CREATE (m:Message {
  // Identity
  messageId: "uuid-string",

  // Routing
  sourceAgent: "ScanProcessorAgent",
  targetAgents: ["RiskScorerAgent", "CaseManagerAgent"],

  // Timing
  timestamp: datetime("2024-11-13T14:30:00Z"),

  // Correlation
  correlationId: "uuid-string-for-chain",

  // Semantic Properties
  semanticIntent: "inform",  // inform, request, command, query, response, notify, alert
  confidenceScore: 0.99,
  reasoning: "Natural language explanation",

  // Protocol
  requiresResponse: false,
  responseTimeoutSeconds: 5,
  priority: 3,  // 1=Critical, 5=Bulk

  // Metadata
  metadata: {}
})
*/

// ----------------------------------------------------------------------------
// :ScanMessage - Scan event notifications
// ----------------------------------------------------------------------------
/*
CREATE (m:ScanMessage:Message {
  // Base Message properties +

  // Scan Details
  bagTag: "CM123456",
  scanType: "Transfer",
  location: "MIA-T3-BHS",
  scanTimestamp: datetime("2024-11-13T14:30:00Z"),

  // Raw Data
  rawData: "BPM/CM123456/MIA/T3/...",
  parsedData: {
    bag_tag: "CM123456",
    location: "MIA-T3",
    timestamp: "2024-11-13T14:30:00Z"
  },

  // Quality
  scanQuality: 0.98,
  readConfidence: 0.99,

  // Context
  flightNumber: "CM405",
  scannerId: "BHS-MIA-T3-SC-05",
  operatorId: null,

  // Validation
  isValidSequence: true,
  validationErrors: []
})
*/

// ----------------------------------------------------------------------------
// :RiskMessage - Risk assessment results
// ----------------------------------------------------------------------------
/*
CREATE (m:RiskMessage:Message {
  // Base Message properties +

  // Risk Assessment
  bagTag: "CM123456",
  riskScore: 0.85,
  riskLevel: "High",

  // Factors
  primaryFactors: [
    "Connection time below MCT",
    "High traffic period"
  ],
  secondaryFactors: [],
  factorWeights: {
    connection_time: 0.6,
    traffic: 0.4
  },

  // Predictions
  prediction: "MissedConnection",
  predictionProbability: 0.73,
  alternativeOutcomes: {
    "OnTimeDelivery": 0.27
  },

  // Recommendations
  recommendedAction: "Intervene",
  recommendedActionUrgency: "High",
  recommendedActionDetails: "Alert ground handling, prepare manual transfer",

  // Context
  connectionTimeMinutes: 32,
  mctMinutes: 45,
  airportPerformanceScore: 8.5,

  // Model Info
  modelVersion: "RiskScoringModel_v2.3",
  featuresUsed: [
    "connection_time",
    "mct",
    "airport_performance"
  ]
})
*/

// ----------------------------------------------------------------------------
// :ExceptionMessage - Exception case notifications
// ----------------------------------------------------------------------------
/*
CREATE (m:ExceptionMessage:Message {
  // Base Message properties +

  // Case Details
  caseId: "CASE-20241113-001",
  bagTag: "CM123456",
  exceptionType: "MissedConnection",
  exceptionPriority: "P1",

  // Description
  title: "High risk missed connection at MIA",
  description: "Bag CM123456 has 32 minute connection time...",
  rootCause: "Inbound flight delayed",

  // Actions
  recommendedActions: [
    "Alert ground handling",
    "Dispatch courier if needed"
  ],
  actionsTaken: [],

  // Assignment
  assignedTo: "BaggageOpsTeam-MIA",
  assignedAt: datetime("2024-11-13T14:28:00Z"),

  // SLA
  slaDeadline: datetime("2024-11-13T15:15:00Z"),
  slaRemainingMinutes: 45,

  // Financial
  potentialClaimCost: 250.00,
  preventionCost: 75.00,

  // Passenger Context
  passengerName: "Smith, John",
  passengerPnr: "ABC123",
  passengerEliteStatus: "Gold"
})
*/

// ----------------------------------------------------------------------------
// :WorldTracerMessage - PIR and recovery info
// ----------------------------------------------------------------------------
/*
CREATE (m:WorldTracerMessage:Message {
  // Base Message properties +

  // PIR Details
  pirNumber: "MIAHP12345",
  bagTag: "CM123456",
  pirType: "OHD",
  status: "Open",

  // Location
  lastKnownLocation: "MIA-T3-BHS",
  currentLocation: null,
  expectedDestination: "JFK-T8",

  // Routing
  originalRouting: "PTY-MIA-JFK",
  newRouting: null,

  // Timeline
  filedAt: datetime("2024-11-13T15:45:00Z"),
  lastUpdated: datetime("2024-11-13T15:45:00Z"),
  resolvedAt: null,

  // Baggage Description
  bagDescription: "Black Samsonite hardshell suitcase",
  bagColor: "Black",
  bagType: "Suitcase",

  // WorldTracer Reference
  worldtracerRef: "WT-MIA-20241113-001",
  filingStation: "MIA",

  // Passenger Info
  passengerName: "Smith, John",
  passengerContact: "john.smith@email.com",
  passengerNotified: true
})
*/

// ----------------------------------------------------------------------------
// :TypeBMessage - IATA Type B messages
// ----------------------------------------------------------------------------
/*
CREATE (m:TypeBMessage:Message {
  // Base Message properties +

  // Message Details
  messageType: "BPM",
  rawText: "BPM\nCM123456\n.MIA/T3\n...",

  // Parsed Data
  parsedData: {
    bag_tag: "CM123456",
    location: "MIA-T3",
    timestamp: "2024-11-13T14:30:00Z"
  },

  // Protocol
  protocolVersion: "IATA_TypeB_16.1",
  encoding: "ASCII",

  // Validation
  isValid: true,
  validationErrors: [],

  // Context
  bagTag: "CM123456",
  flightNumber: "CM405",
  originAirport: "MIA",
  destinationAirport: "JFK",

  // Source
  sourceSystem: "BHS",
  receivedAt: datetime("2024-11-13T14:30:00Z")
})
*/

// ----------------------------------------------------------------------------
// :XMLMessage - BaggageXML interline messages
// ----------------------------------------------------------------------------
/*
CREATE (m:XMLMessage:Message {
  // Base Message properties +

  // XML Details
  schemaVersion: "3.0",
  airlineCode: "CM",

  // Manifest Data
  manifestData: {bags: []},
  bagsCount: 125,
  flightNumber: "CM405",
  departureDate: datetime("2024-11-13T15:30:00Z"),

  // Origin/Destination
  originAirport: "MIA",
  destinationAirport: "JFK",

  // Interline
  isInterline: false,
  operatingCarrier: "CM",
  marketingCarrier: "CM",

  // Raw XML
  rawXml: "<BaggageManifest>...</BaggageManifest>",

  // Validation
  isValidXml: true,
  schemaValidationErrors: []
})
*/

// ----------------------------------------------------------------------------
// :DispatchMessage - Courier dispatch notifications
// ----------------------------------------------------------------------------
/*
CREATE (m:DispatchMessage:Message {
  // Base Message properties +

  // Courier Details
  courierId: "courier-uuid-55555",
  bagTag: "CM123456",
  courierVendor: "FedEx",
  serviceLevel: "Priority Overnight",
  trackingNumber: "1234567890",

  // Pickup
  pickupLocation: "MIA Airport",
  pickupAddress: "Miami Int'l Airport, Terminal 3",
  pickupScheduledTime: datetime("2024-11-13T18:00:00Z"),
  pickupActualTime: null,

  // Delivery
  deliveryAddress: "123 Main St, New York, NY 10001",
  deliveryScheduledTime: datetime("2024-11-14T10:00:00Z"),
  deliveryActualTime: null,
  estimatedDeliveryTime: datetime("2024-11-14T10:00:00Z"),

  // Status
  status: "Approved",
  statusUpdatedAt: datetime("2024-11-13T15:50:00Z"),

  // Financial
  courierCost: 85.00,
  potentialClaimCost: 250.00,
  costBenefitRatio: 2.94,

  // Approval
  requiresApproval: true,
  approvedBy: "StationManager-MIA",
  approvedAt: datetime("2024-11-13T15:50:00Z"),

  // Passenger Context
  passengerEliteStatus: "Gold",
  passengerLifetimeValue: 45000.00
})
*/

// ----------------------------------------------------------------------------
// :NotificationMessage - Passenger notifications
// ----------------------------------------------------------------------------
/*
CREATE (m:NotificationMessage:Message {
  // Base Message properties +

  // Passenger Details
  passengerId: "ABC123",
  passengerName: "Smith, John",

  // Notification Details
  channel: "Email",
  template: "baggage_delay",
  templateVariables: {},

  // Content
  subject: "Update on Your Baggage - CM123456",
  messageBody: "Dear Mr. Smith, we want to inform you...",

  // Contact
  contactEmail: "john.smith@email.com",
  contactPhone: "+15550123",

  // Delivery
  sentAt: datetime("2024-11-13T15:47:00Z"),
  deliveryStatus: "Sent",
  deliveryTimestamp: datetime("2024-11-13T15:47:05Z"),
  failureReason: null,

  // Context
  bagTag: "CM123456",
  caseId: "CASE-20241113-001",
  pirNumber: "MIAHP12345",

  // Preferences
  language: "EN",
  timezone: "America/New_York"
})
*/

// ============================================================================
// PART 4: MESSAGE RELATIONSHIPS
// ============================================================================

// ----------------------------------------------------------------------------
// [:SENDS] - Agent sends message
// ----------------------------------------------------------------------------
// (agent:Agent)-[:SENDS]->(message:Message)
/*
Properties:
  timestamp: datetime - When message was sent
  latencyMs: integer - Processing time in milliseconds
  success: boolean - Was send successful
  errorMessage: string - Error if failed
  retryCount: integer - Number of retries

Sample:
MATCH (a:Agent {agentId: "ScanProcessorAgent-001"}),
      (m:ScanMessage {messageId: "msg-uuid-123"})
CREATE (a)-[:SENDS {
  timestamp: datetime("2024-11-13T14:30:00Z"),
  latencyMs: 87,
  success: true,
  errorMessage: null,
  retryCount: 0
}]->(m)
*/

// ----------------------------------------------------------------------------
// [:RECEIVES] - Agent receives message
// ----------------------------------------------------------------------------
// (agent:Agent)-[:RECEIVES]->(message:Message)
/*
Properties:
  receivedAt: datetime - When message was received
  processedAt: datetime - When processing completed
  processingTimeMs: integer - Processing time
  success: boolean - Was processing successful
  errorMessage: string - Error if failed
  outputMessageIds: string[] - Messages created in response

Sample:
MATCH (a:Agent {agentId: "RiskScorerAgent-001"}),
      (m:ScanMessage {messageId: "msg-uuid-123"})
CREATE (a)-[:RECEIVES {
  receivedAt: datetime("2024-11-13T14:30:01Z"),
  processedAt: datetime("2024-11-13T14:30:02Z"),
  processingTimeMs: 95,
  success: true,
  errorMessage: null,
  outputMessageIds: ["risk-msg-uuid-456"]
}]->(m)
*/

// ----------------------------------------------------------------------------
// [:TARGETS] - Message targets agent
// ----------------------------------------------------------------------------
// (message:Message)-[:TARGETS]->(agent:Agent)
/*
Properties:
  priority: integer - Message priority for this target
  deliveryStatus: string - Pending, Delivered, Failed
  deliveredAt: datetime - When delivered
  acknowledgmentRequired: boolean - Needs ACK

Sample:
MATCH (m:RiskMessage {messageId: "risk-msg-uuid-456"}),
      (a:Agent {agentId: "CaseManagerAgent-001"})
CREATE (m)-[:TARGETS {
  priority: 1,
  deliveryStatus: "Delivered",
  deliveredAt: datetime("2024-11-13T14:28:01Z"),
  acknowledgmentRequired: true
}]->(a)
*/

// ----------------------------------------------------------------------------
// [:IN_RESPONSE_TO] - Message is response to another message
// ----------------------------------------------------------------------------
// (response:Message)-[:IN_RESPONSE_TO]->(request:Message)
/*
Properties:
  responseTime: integer - Time to respond (milliseconds)
  correlationId: string - Shared correlation ID
  fulfillsRequest: boolean - Does this fully answer the request

Sample:
MATCH (response:RiskMessage {messageId: "risk-msg-uuid-456"}),
      (request:ScanMessage {messageId: "msg-uuid-123"})
CREATE (response)-[:IN_RESPONSE_TO {
  responseTime: 95,
  correlationId: "correlation-uuid-789",
  fulfillsRequest: true
}]->(request)
*/

// ----------------------------------------------------------------------------
// [:PART_OF_CHAIN] - Messages in same conversation
// ----------------------------------------------------------------------------
// (message:Message)-[:PART_OF_CHAIN]->(chain:MessageChain)
/*
Properties:
  sequenceNumber: integer - Position in chain
  timestamp: datetime - When added to chain

Sample:
MATCH (m:Message {messageId: "msg-uuid-123"}),
      (chain:MessageChain {chainId: "chain-uuid-001"})
CREATE (m)-[:PART_OF_CHAIN {
  sequenceNumber: 1,
  timestamp: datetime("2024-11-13T14:30:00Z")
}]->(chain)
*/

// ----------------------------------------------------------------------------
// [:ABOUT_BAG] - Message is about specific baggage
// ----------------------------------------------------------------------------
// (message:Message)-[:ABOUT_BAG]->(bag:Baggage)
/*
Properties:
  timestamp: datetime
  confidence: float

Sample:
MATCH (m:ScanMessage {bagTag: "CM123456"}),
      (b:Baggage {bagTag: "CM123456"})
CREATE (m)-[:ABOUT_BAG {
  timestamp: datetime("2024-11-13T14:30:00Z"),
  confidence: 0.99
}]->(b)
*/

// ----------------------------------------------------------------------------
// [:TRIGGERS_ACTION] - Message triggers agent action
// ----------------------------------------------------------------------------
// (message:Message)-[:TRIGGERS_ACTION]->(action:Action)
/*
Properties:
  triggeredAt: datetime
  actionType: string
  success: boolean
  reasoning: string

Sample:
MATCH (m:RiskMessage {riskLevel: "High"}),
      (e:Exception {caseId: "CASE-20241113-001"})
CREATE (m)-[:TRIGGERS_ACTION {
  triggeredAt: datetime("2024-11-13T14:28:00Z"),
  actionType: "CreateException",
  success: true,
  reasoning: "High risk score exceeds threshold"
}]->(e)
*/

// ============================================================================
// PART 5: MESSAGE CHAIN PATTERNS
// ============================================================================

// Pattern 1: Complete agent communication flow
/*
MATCH path = (sender:Agent)-[:SENDS]->(msg:Message)-[:TARGETS]->(receiver:Agent)
WHERE msg.timestamp > datetime() - duration({hours: 1})
RETURN path
ORDER BY msg.timestamp DESC
LIMIT 100
*/

// Pattern 2: Message chains (request-response)
/*
MATCH chain = (request:Message)<-[:IN_RESPONSE_TO*]-(response:Message)
WHERE request.timestamp > datetime() - duration({hours: 1})
RETURN chain
ORDER BY request.timestamp DESC
*/

// Pattern 3: High-priority messages
/*
MATCH (m:Message)
WHERE m.priority <= 2
  AND m.timestamp > datetime() - duration({hours: 1})
OPTIONAL MATCH (m)-[:TARGETS]->(a:Agent)
RETURN m, collect(a.agentType) as targets
ORDER BY m.priority ASC, m.timestamp DESC
*/

// Pattern 4: Failed message deliveries
/*
MATCH (a:Agent)-[r:RECEIVES]->(m:Message)
WHERE r.success = false
  AND r.receivedAt > datetime() - duration({hours: 24})
RETURN a.agentType, m.messageId, r.errorMessage, r.receivedAt
ORDER BY r.receivedAt DESC
*/

// Pattern 5: Messages about specific baggage
/*
MATCH (b:Baggage {bagTag: "CM123456"})<-[:ABOUT_BAG]-(m:Message)
RETURN m
ORDER BY m.timestamp ASC
*/

// Pattern 6: Agent communication metrics
/*
MATCH (sender:Agent)-[s:SENDS]->(m:Message)-[t:TARGETS]->(receiver:Agent)
WHERE m.timestamp > datetime() - duration({hours: 24})
WITH sender.agentType as from,
     receiver.agentType as to,
     count(m) as messageCount,
     avg(s.latencyMs) as avgLatencyMs,
     sum(CASE WHEN s.success = false THEN 1 ELSE 0 END) as failureCount
RETURN from, to, messageCount, avgLatencyMs, failureCount
ORDER BY messageCount DESC
*/

// ============================================================================
// PART 6: SEMANTIC QUERIES
// ============================================================================

// Query 1: Find all messages in a semantic chain (correlation)
/*
MATCH (m:Message)
WHERE m.correlationId = "correlation-uuid-789"
RETURN m
ORDER BY m.timestamp ASC
*/

// Query 2: Messages with low confidence scores
/*
MATCH (m:Message)
WHERE m.confidenceScore < 0.7
  AND m.timestamp > datetime() - duration({hours: 24})
RETURN m.messageId, m.sourceAgent, m.confidenceScore, m.reasoning
ORDER BY m.confidenceScore ASC
*/

// Query 3: Agent communication graph
/*
MATCH (sender:Agent)-[:SENDS]->(m:Message)-[:TARGETS]->(receiver:Agent)
WHERE m.timestamp > datetime() - duration({hours: 1})
WITH sender, receiver, count(m) as messageCount
RETURN sender.agentType, receiver.agentType, messageCount
ORDER BY messageCount DESC
*/

// Query 4: Message latency analysis
/*
MATCH (a:Agent)-[s:SENDS]->(m:Message)
WHERE m.timestamp > datetime() - duration({hours: 24})
WITH a.agentType as agent,
     avg(s.latencyMs) as avgLatency,
     min(s.latencyMs) as minLatency,
     max(s.latencyMs) as maxLatency,
     count(m) as messageCount
RETURN agent, avgLatency, minLatency, maxLatency, messageCount
ORDER BY avgLatency DESC
*/

// Query 5: Response time analysis
/*
MATCH (response:Message)-[r:IN_RESPONSE_TO]->(request:Message)
WHERE request.timestamp > datetime() - duration({hours: 24})
WITH request.sourceAgent as requester,
     response.sourceAgent as responder,
     avg(r.responseTime) as avgResponseTime,
     count(response) as responseCount
RETURN requester, responder, avgResponseTime, responseCount
ORDER BY avgResponseTime DESC
*/

// ============================================================================
// PART 7: PERFORMANCE INDEXES FOR MESSAGE QUERIES
// ============================================================================

// Composite indexes for common query patterns
CREATE INDEX message_agent_timestamp IF NOT EXISTS
FOR (m:Message) ON (m.sourceAgent, m.timestamp);

CREATE INDEX message_priority_timestamp IF NOT EXISTS
FOR (m:Message) ON (m.priority, m.timestamp);

CREATE INDEX message_correlation_timestamp IF NOT EXISTS
FOR (m:Message) ON (m.correlationId, m.timestamp);

// Relationship indexes
CREATE INDEX sends_timestamp IF NOT EXISTS
FOR ()-[r:SENDS]-() ON (r.timestamp);

CREATE INDEX receives_timestamp IF NOT EXISTS
FOR ()-[r:RECEIVES]-() ON (r.receivedAt);

CREATE INDEX receives_success IF NOT EXISTS
FOR ()-[r:RECEIVES]-() ON (r.success);

// ============================================================================
// END OF MESSAGE ONTOLOGY SCHEMA
// ============================================================================

// Usage Notes:
// 1. All messages inherit from :Message base type
// 2. Use correlation_id to track message chains
// 3. Every message includes semantic properties (intent, confidence, reasoning)
// 4. Monitor message latency and success rates for system health
// 5. Use SENDS/RECEIVES relationships to track agent performance

// Message Flow Example:
// ScanProcessorAgent -[:SENDS]-> ScanMessage -[:TARGETS]-> RiskScorerAgent
// RiskScorerAgent -[:RECEIVES]-> ScanMessage
// RiskScorerAgent -[:SENDS]-> RiskMessage -[:TARGETS]-> CaseManagerAgent
// RiskMessage -[:IN_RESPONSE_TO]-> ScanMessage

// This enables:
// - Complete audit trail of all agent communication
// - Performance monitoring (latency, success rates)
// - Semantic reasoning (intent, confidence, correlation)
// - Message chain reconstruction
// - Agent collaboration visualization
