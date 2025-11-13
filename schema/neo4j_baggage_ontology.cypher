// ============================================================================
// BAGGAGE OPERATIONS KNOWLEDGE GRAPH - NEO4J ONTOLOGY SCHEMA
// ============================================================================
// Purpose: Semantic data model for 8 AI agents with shared understanding
// Based on: gist (Semantic Arts) Foundational Ontology
// Version: 1.0.0
// Date: 2024-11-13
// ============================================================================

// ============================================================================
// PART 1: CONSTRAINTS - Enforce data integrity
// ============================================================================

// Baggage Digital Twin - Primary entity
CREATE CONSTRAINT baggage_tag_unique IF NOT EXISTS
FOR (b:Baggage) REQUIRE b.bagTag IS UNIQUE;

CREATE CONSTRAINT baggage_tag_exists IF NOT EXISTS
FOR (b:Baggage) REQUIRE b.bagTag IS NOT NULL;

CREATE CONSTRAINT baggage_digital_twin_id IF NOT EXISTS
FOR (b:Baggage) REQUIRE b.digitalTwinId IS UNIQUE;

// Scan Events - All checkpoint scans
CREATE CONSTRAINT scan_event_id IF NOT EXISTS
FOR (s:ScanEvent) REQUIRE s.eventId IS UNIQUE;

CREATE CONSTRAINT scan_event_timestamp IF NOT EXISTS
FOR (s:ScanEvent) REQUIRE s.timestamp IS NOT NULL;

// Flights
CREATE CONSTRAINT flight_number_date IF NOT EXISTS
FOR (f:Flight) REQUIRE (f.flightNumber, f.departureDate) IS UNIQUE;

CREATE CONSTRAINT flight_number_exists IF NOT EXISTS
FOR (f:Flight) REQUIRE f.flightNumber IS NOT NULL;

// Passengers
CREATE CONSTRAINT passenger_pnr IF NOT EXISTS
FOR (p:Passenger) REQUIRE p.pnr IS UNIQUE;

CREATE CONSTRAINT passenger_pnr_exists IF NOT EXISTS
FOR (p:Passenger) REQUIRE p.pnr IS NOT NULL;

// Locations (Airports, Terminals, Gates, Carousels)
CREATE CONSTRAINT location_id IF NOT EXISTS
FOR (l:Location) REQUIRE l.locationId IS UNIQUE;

CREATE CONSTRAINT airport_iata IF NOT EXISTS
FOR (a:Airport) REQUIRE a.iataCode IS UNIQUE;

// AI Agents
CREATE CONSTRAINT agent_id IF NOT EXISTS
FOR (a:Agent) REQUIRE a.agentId IS UNIQUE;

// Messages (Type B, XML, JSON)
CREATE CONSTRAINT message_id IF NOT EXISTS
FOR (m:Message) REQUIRE m.messageId IS UNIQUE;

// Exception Cases
CREATE CONSTRAINT exception_case_id IF NOT EXISTS
FOR (e:Exception) REQUIRE e.caseId IS UNIQUE;

// Risk Assessments
CREATE CONSTRAINT risk_assessment_id IF NOT EXISTS
FOR (r:Risk) REQUIRE r.riskId IS UNIQUE;

// Property Irregularity Reports (PIR)
CREATE CONSTRAINT pir_number IF NOT EXISTS
FOR (p:PIR) REQUIRE p.pirNumber IS UNIQUE;

// Courier Dispatches
CREATE CONSTRAINT courier_dispatch_id IF NOT EXISTS
FOR (c:CourierDispatch) REQUIRE c.dispatchId IS UNIQUE;

// ============================================================================
// PART 2: INDEXES - Optimize query performance
// ============================================================================

// Baggage indexes
CREATE INDEX baggage_status IF NOT EXISTS FOR (b:Baggage) ON (b.status);
CREATE INDEX baggage_current_location IF NOT EXISTS FOR (b:Baggage) ON (b.currentLocation);
CREATE INDEX baggage_risk_score IF NOT EXISTS FOR (b:Baggage) ON (b.riskScore);
CREATE INDEX baggage_risk_level IF NOT EXISTS FOR (b:Baggage) ON (b.riskLevel);
CREATE INDEX baggage_created_at IF NOT EXISTS FOR (b:Baggage) ON (b.createdAt);
CREATE INDEX baggage_weight IF NOT EXISTS FOR (b:Baggage) ON (b.weight);

// Scan Event indexes
CREATE INDEX scan_event_type IF NOT EXISTS FOR (s:ScanEvent) ON (s.scanType);
CREATE INDEX scan_event_location IF NOT EXISTS FOR (s:ScanEvent) ON (s.location);
CREATE INDEX scan_event_timestamp IF NOT EXISTS FOR (s:ScanEvent) ON (s.timestamp);
CREATE INDEX scan_event_bag_tag IF NOT EXISTS FOR (s:ScanEvent) ON (s.bagTag);
CREATE INDEX scan_event_flight IF NOT EXISTS FOR (s:ScanEvent) ON (s.flightNumber);

// Flight indexes
CREATE INDEX flight_origin IF NOT EXISTS FOR (f:Flight) ON (f.origin);
CREATE INDEX flight_destination IF NOT EXISTS FOR (f:Flight) ON (f.destination);
CREATE INDEX flight_departure_time IF NOT EXISTS FOR (f:Flight) ON (f.scheduledDeparture);
CREATE INDEX flight_status IF NOT EXISTS FOR (f:Flight) ON (f.status);
CREATE INDEX flight_date IF NOT EXISTS FOR (f:Flight) ON (f.departureDate);

// Passenger indexes
CREATE INDEX passenger_name IF NOT EXISTS FOR (p:Passenger) ON (p.name);
CREATE INDEX passenger_elite_status IF NOT EXISTS FOR (p:Passenger) ON (p.eliteStatus);
CREATE INDEX passenger_email IF NOT EXISTS FOR (p:Passenger) ON (p.contactEmail);
CREATE INDEX passenger_lifetime_value IF NOT EXISTS FOR (p:Passenger) ON (p.lifetimeValue);

// Location indexes
CREATE INDEX location_type IF NOT EXISTS FOR (l:Location) ON (l.locationType);
CREATE INDEX location_airport IF NOT EXISTS FOR (l:Location) ON (l.airportCode);
CREATE INDEX airport_performance IF NOT EXISTS FOR (a:Airport) ON (a.performanceScore);

// Agent indexes
CREATE INDEX agent_type IF NOT EXISTS FOR (a:Agent) ON (a.agentType);
CREATE INDEX agent_active IF NOT EXISTS FOR (a:Agent) ON (a.isActive);

// Message indexes
CREATE INDEX message_type IF NOT EXISTS FOR (m:Message) ON (m.messageType);
CREATE INDEX message_timestamp IF NOT EXISTS FOR (m:Message) ON (m.timestamp);
CREATE INDEX message_source_agent IF NOT EXISTS FOR (m:Message) ON (m.sourceAgent);

// Exception indexes
CREATE INDEX exception_priority IF NOT EXISTS FOR (e:Exception) ON (e.priority);
CREATE INDEX exception_status IF NOT EXISTS FOR (e:Exception) ON (e.status);
CREATE INDEX exception_created_at IF NOT EXISTS FOR (e:Exception) ON (e.createdAt);
CREATE INDEX exception_sla_deadline IF NOT EXISTS FOR (e:Exception) ON (e.slaDeadline);

// Risk indexes
CREATE INDEX risk_score IF NOT EXISTS FOR (r:Risk) ON (r.riskScore);
CREATE INDEX risk_level IF NOT EXISTS FOR (r:Risk) ON (r.riskLevel);
CREATE INDEX risk_timestamp IF NOT EXISTS FOR (r:Risk) ON (r.assessedAt);

// PIR indexes
CREATE INDEX pir_status IF NOT EXISTS FOR (p:PIR) ON (p.status);
CREATE INDEX pir_type IF NOT EXISTS FOR (p:PIR) ON (p.pirType);
CREATE INDEX pir_filed_at IF NOT EXISTS FOR (p:PIR) ON (p.filedAt);

// Courier indexes
CREATE INDEX courier_status IF NOT EXISTS FOR (c:CourierDispatch) ON (c.status);
CREATE INDEX courier_vendor IF NOT EXISTS FOR (c:CourierDispatch) ON (c.courierVendor);

// ============================================================================
// PART 3: NODE TYPE DEFINITIONS WITH PROPERTIES
// ============================================================================

// ----------------------------------------------------------------------------
// :Baggage - Digital Twin with 50+ properties
// ----------------------------------------------------------------------------
// Physical properties, journey state, risk metrics, semantic metadata
// Sample creation (properties documented below):
/*
CREATE (b:Baggage {
  // Identity
  bagTag: "CM123456",
  digitalTwinId: "dt-uuid-12345",

  // Physical Properties
  weight: 23.5,
  weightUnit: "kg",
  dimensions: 158,
  dimensionsUnit: "linear_cm",
  length: 70,
  width: 45,
  height: 43,
  color: "Black",
  type: "Suitcase",
  brand: "Samsonite",
  hasLock: true,
  isFragile: false,

  // Contents
  contentsValue: 1200.00,
  contentsValueCurrency: "USD",
  contentsDescription: "Clothing, electronics, toiletries",
  declaredContents: ["Clothes", "Laptop", "Camera"],

  // Special Handling
  specialHandling: ["None"],
  isOversized: false,
  isHeavy: false,
  requiresSecurityScreening: false,
  restrictedItems: [],

  // Journey Properties
  status: "InTransit",
  currentLocation: "MIA-T3-BHS",
  lastKnownLocation: "MIA-T3-BHS",
  lastKnownTimestamp: datetime("2024-11-13T14:30:00Z"),
  expectedLocation: "JFK-T8",
  destinationAirport: "JFK",
  finalDestination: "New York, NY",

  // Routing
  routing: "PTY-MIA-JFK",
  routingSegments: ["PTY-MIA", "MIA-JFK"],
  currentSegment: "MIA-JFK",
  segmentNumber: 2,
  totalSegments: 2,
  isConnecting: true,
  connectionTime: 45,
  connectionTimeUnit: "minutes",

  // Risk Scoring
  riskScore: 0.65,
  riskLevel: "Medium",
  riskFactors: ["Tight connection", "High traffic period"],
  riskLastAssessed: datetime("2024-11-13T14:28:00Z"),
  riskConfidence: 0.87,
  predictedDeliveryProbability: 0.78,

  // Scan History Metadata
  totalScans: 8,
  lastScanType: "Transfer",
  lastScanTimestamp: datetime("2024-11-13T14:30:00Z"),
  scanGapMinutes: 12,
  missedExpectedScans: 0,

  // Timeline
  checkInTimestamp: datetime("2024-11-13T08:15:00Z"),
  firstScanTimestamp: datetime("2024-11-13T08:17:00Z"),
  expectedArrivalTime: datetime("2024-11-13T19:45:00Z"),
  actualArrivalTime: null,
  claimTimestamp: null,

  // Passenger Association
  pnr: "ABC123",
  passengerName: "Smith, John",
  passengerEliteStatus: "Gold",
  passengerContactEmail: "john.smith@email.com",
  passengerContactPhone: "+1-555-0123",

  // Exception Tracking
  hasException: false,
  exceptionCount: 0,
  hasPIR: false,
  pirNumber: null,

  // Financial
  baggageFee: 35.00,
  baggageFeeCurrency: "USD",
  insuranceValue: 1200.00,
  liabilityLimit: 1500.00,

  // Semantic Metadata (for AI agents)
  createdAt: datetime("2024-11-13T08:15:00Z"),
  updatedAt: datetime("2024-11-13T14:30:00Z"),
  createdBy: "ScanProcessorAgent",
  lastUpdatedBy: "RiskScorerAgent",
  version: 12,
  dataQuality: 0.95,
  dataSourceConfidence: 0.98,

  // Agent Processing
  processedByAgents: ["ScanProcessorAgent", "RiskScorerAgent", "WorldTracerAgent"],
  lastProcessingTime: 145,
  lastProcessingTimeUnit: "milliseconds"
})
*/

// ----------------------------------------------------------------------------
// :ScanEvent - All checkpoint scans throughout journey
// ----------------------------------------------------------------------------
// Scan types: CheckIn, Sortation, Load, Offload, Transfer, Arrival, Claim,
//             Manual, BTM, BSM, BPM, SecurityScreening, CustomsInspection
/*
CREATE (s:ScanEvent {
  // Identity
  eventId: "scan-uuid-67890",
  scanSequence: 8,

  // Scan Details
  scanType: "Transfer",
  scanSubType: "AutomaticBHS",
  bagTag: "CM123456",

  // Location
  location: "MIA-T3-BHS",
  locationId: "loc-mia-t3-bhs-001",
  airportCode: "MIA",
  terminal: "T3",
  gate: null,
  carousel: null,
  sortingLine: "Line-5",

  // Timing
  timestamp: datetime("2024-11-13T14:30:00Z"),
  localTimestamp: datetime("2024-11-13T09:30:00-05:00"),
  timezone: "America/New_York",

  // Flight Association
  flightNumber: "CM405",
  flightOrigin: "MIA",
  flightDestination: "JFK",
  flightDepartureTime: datetime("2024-11-13T15:30:00Z"),

  // Scanner Details
  scannerId: "BHS-MIA-T3-SC-05",
  scannerType: "Automated",
  operatorId: null,
  operatorName: null,

  // Data Source
  dataSource: "BHS",
  messageType: "BPM",
  rawMessage: "BPM/CM123456/MIA/T3/...",
  messageFormat: "IATA_BagMessage",

  // Quality & Validation
  scanQuality: 0.98,
  readConfidence: 0.99,
  isManual: false,
  wasRetried: false,
  errorCodes: [],
  warnings: [],

  // Processing
  processedBy: "ScanProcessorAgent",
  processingTime: 87,
  processingTimeUnit: "milliseconds",
  validated: true,
  validationRules: ["SequenceCheck", "TimingCheck", "LocationCheck"],

  // Semantic Metadata
  createdAt: datetime("2024-11-13T14:30:00Z"),
  confidence: 0.99,
  reasoning: "Automatic BHS scan in expected sequence",
  agentId: "ScanProcessorAgent-001"
})
*/

// ----------------------------------------------------------------------------
// :Flight - All flight segments
// ----------------------------------------------------------------------------
/*
CREATE (f:Flight {
  // Identity
  flightId: "flight-cm405-20241113",
  flightNumber: "CM405",
  operatingCarrier: "CM",
  marketingCarrier: "CM",
  codeShareFlight: false,

  // Route
  origin: "MIA",
  destination: "JFK",
  departureDate: date("2024-11-13"),

  // Schedule
  scheduledDeparture: datetime("2024-11-13T15:30:00Z"),
  scheduledArrival: datetime("2024-11-13T19:45:00Z"),
  estimatedDeparture: datetime("2024-11-13T15:35:00Z"),
  estimatedArrival: datetime("2024-11-13T19:50:00Z"),
  actualDeparture: null,
  actualArrival: null,

  // Status
  status: "Boarding",
  statusUpdatedAt: datetime("2024-11-13T15:15:00Z"),
  delayMinutes: 5,
  delayReason: "Late arriving aircraft",
  isCancelled: false,
  isDelayed: true,

  // Aircraft
  aircraftType: "A320",
  aircraftRegistration: "HP-1234CMP",
  tailNumber: "1234",

  // Gate & Terminal
  departureTerminal: "T3",
  departureGate: "G12",
  arrivalTerminal: "T8",
  arrivalGate: "B7",

  // Baggage
  baggageClaimCarousel: "C5",
  expectedBagsCount: 127,
  checkedInBagsCount: 125,
  loadedBagsCount: null,

  // Performance Metrics
  onTimePerformance: 0.89,
  baggageMishandleRate: 0.023,
  averageBaggageDeliveryTime: 18,

  // Connection Info
  isConnection: false,
  inboundFlightNumber: null,
  minimumConnectionTime: 45,

  // Semantic Metadata
  createdAt: datetime("2024-11-13T08:00:00Z"),
  updatedAt: datetime("2024-11-13T15:15:00Z"),
  dataSource: "PSS",
  confidence: 1.0
})
*/

// ----------------------------------------------------------------------------
// :Passenger - Customer information
// ----------------------------------------------------------------------------
/*
CREATE (p:Passenger {
  // Identity
  passengerId: "pax-uuid-11111",
  pnr: "ABC123",
  recordLocator: "ABC123",
  frequentFlyerNumber: "CM12345678",

  // Personal Info
  name: "Smith, John",
  firstName: "John",
  lastName: "Smith",
  title: "Mr",
  dateOfBirth: date("1985-06-15"),

  // Contact
  contactEmail: "john.smith@email.com",
  contactPhone: "+1-555-0123",
  alternatePhone: "+1-555-0124",
  preferredContactMethod: "Email",

  // Status & Loyalty
  eliteStatus: "Gold",
  eliteStatusPoints: 75000,
  lifetimeValue: 45000.00,
  lifetimeValueCurrency: "USD",
  memberSince: date("2018-03-15"),

  // Preferences
  language: "EN",
  locale: "en_US",
  timezone: "America/New_York",
  notificationPreferences: ["Email", "SMS"],
  smsOptIn: true,
  emailOptIn: true,
  pushOptIn: false,

  // Travel Profile
  totalFlights: 145,
  baggageClaimsHistory: 2,
  averageBagsPerTrip: 1.2,
  preferredSeatType: "Aisle",
  specialAssistance: [],

  // Current Trip
  currentPNR: "ABC123",
  currentFlights: ["CM101", "CM405"],
  checkedBagsCount: 1,
  carryOnCount: 1,

  // Risk Profile
  passengerRiskScore: 0.15,
  isVIP: true,
  isPriority: true,
  requiresSpecialHandling: false,

  // Compensation History
  totalCompensationPaid: 250.00,
  lastCompensationDate: date("2023-08-12"),
  lastCompensationReason: "Delayed baggage",

  // Semantic Metadata
  createdAt: datetime("2024-11-13T08:15:00Z"),
  updatedAt: datetime("2024-11-13T14:30:00Z"),
  dataSource: "PSS",
  confidence: 1.0
})
*/

// ----------------------------------------------------------------------------
// :Location - Airports, terminals, gates, carousels, sorting areas
// ----------------------------------------------------------------------------
/*
CREATE (l:Location {
  // Identity
  locationId: "loc-mia-t3-bhs-001",
  locationType: "BaggageHandlingSystem",

  // Airport Context
  airportCode: "MIA",
  airportName: "Miami International Airport",
  city: "Miami",
  state: "FL",
  country: "USA",
  region: "North America",

  // Specific Location
  terminal: "T3",
  concourse: null,
  gate: null,
  carousel: null,
  sortingArea: "SortingLine-5",
  level: "Baggage Level",

  // Coordinates
  latitude: 25.7959,
  longitude: -80.2870,
  elevation: 11,

  // Operational
  isOperational: true,
  capacity: 500,
  capacityUnit: "bags_per_hour",
  currentLoad: 342,
  utilizationRate: 0.68,

  // Performance
  averageProcessingTime: 4.5,
  processingTimeUnit: "minutes",
  errorRate: 0.012,
  uptimePercentage: 99.2,

  // Equipment
  equipmentType: "Automated Sorter",
  manufacturer: "Siemens",
  model: "BHS-3000",
  installDate: date("2020-06-15"),
  lastMaintenanceDate: date("2024-10-25"),

  // Semantic Metadata
  createdAt: datetime("2024-01-01T00:00:00Z"),
  updatedAt: datetime("2024-11-13T14:00:00Z")
})
*/

// Specialized Location: Airport
/*
CREATE (a:Airport:Location {
  locationId: "airport-mia",
  locationType: "Airport",
  iataCode: "MIA",
  icaoCode: "KMIA",
  airportName: "Miami International Airport",
  city: "Miami",
  state: "FL",
  country: "USA",
  timezone: "America/New_York",

  // Operational Metrics
  mctDomestic: 45,
  mctInternational: 90,
  mctUnit: "minutes",
  performanceScore: 8.5,

  // Baggage Performance
  baggageMishandleRate: 0.034,
  averageBaggageDeliveryTime: 16,
  onTimeDeliveryRate: 0.957,

  // Hub Status
  isHub: true,
  hubCarrier: "CM",
  connectionBagsPerDay: 5000,

  // Weather Risk
  weatherRiskScore: 0.25,
  currentWeather: "Clear",
  forecastRisk: "Low",

  // Semantic Metadata
  confidence: 1.0,
  dataQuality: 0.99
})
*/

// ----------------------------------------------------------------------------
// :Agent - AI agents (8 specialized agents)
// ----------------------------------------------------------------------------
/*
CREATE (a:Agent {
  // Identity
  agentId: "ScanProcessorAgent-001",
  agentType: "ScanProcessorAgent",
  agentName: "Scan Event Processor",
  version: "2.1.0",

  // Capabilities
  capabilities: [
    "ProcessBHSScan",
    "ProcessDCSScan",
    "ProcessManualScan",
    "ValidateScanSequence",
    "DetectScanGaps",
    "UpdateDigitalTwin"
  ],

  // Specialization
  domain: "ScanEventProcessing",
  inputTypes: ["BTM", "BSM", "BPM", "DCS_Scan", "Manual_Scan"],
  outputTypes: ["ScanEvent", "BaggageUpdate"],

  // Performance
  averageProcessingTime: 95,
  processingTimeUnit: "milliseconds",
  successRate: 0.998,
  errorRate: 0.002,

  // Status
  isActive: true,
  lastActiveTimestamp: datetime("2024-11-13T14:30:00Z"),
  healthStatus: "Healthy",

  // Model Info
  modelName: "claude-sonnet-4-20250514",
  modelTemperature: 0.1,
  maxTokens: 2000,

  // Communication
  canCommunicateWith: [
    "RiskScorerAgent",
    "CaseManagerAgent",
    "WorldTracerAgent"
  ],
  messageQueue: "scan-events",

  // Semantic Metadata
  createdAt: datetime("2024-01-01T00:00:00Z"),
  updatedAt: datetime("2024-11-13T14:30:00Z")
})
*/

// Full list of 8 agents:
// 1. ScanProcessorAgent
// 2. RiskScorerAgent
// 3. WorldTracerAgent
// 4. SITAHandlerAgent
// 5. BaggageXMLAgent
// 6. CaseManagerAgent
// 7. CourierDispatchAgent
// 8. PassengerCommsAgent

// ----------------------------------------------------------------------------
// :Message - Inter-agent and external system messages
// ----------------------------------------------------------------------------
/*
CREATE (m:Message {
  // Identity
  messageId: "msg-uuid-99999",
  messageType: "TypeB_BSM",
  messageFormat: "IATA_TypeB",

  // Source & Target
  sourceSystem: "BHS",
  sourceAgent: "ScanProcessorAgent-001",
  targetAgent: "RiskScorerAgent-001",

  // Content
  rawMessage: "BSM/CM123456/MIA/T3/...",
  parsedMessage: {
    bagTag: "CM123456",
    location: "MIA-T3",
    timestamp: "2024-11-13T14:30:00Z"
  },
  messageBody: "Full IATA Type B message body...",

  // Protocol
  protocol: "IATA_TypeB",
  version: "16.1",
  encoding: "ASCII",

  // Timing
  timestamp: datetime("2024-11-13T14:30:00Z"),
  receivedAt: datetime("2024-11-13T14:30:01Z"),
  processedAt: datetime("2024-11-13T14:30:02Z"),

  // Processing
  processingStatus: "Processed",
  processingTime: 87,
  processingTimeUnit: "milliseconds",
  validated: true,
  validationErrors: [],

  // Semantic Context
  semanticType: "BaggageSortationEvent",
  entities: ["CM123456", "MIA-T3"],
  intent: "UpdateBaggageLocation",
  confidence: 0.99,

  // Metadata
  priority: "Normal",
  retryCount: 0,
  ttl: 3600,
  createdAt: datetime("2024-11-13T14:30:00Z")
})
*/

// ----------------------------------------------------------------------------
// :Exception - Exception cases requiring intervention
// ----------------------------------------------------------------------------
/*
CREATE (e:Exception {
  // Identity
  caseId: "CASE-20241113-001",
  exceptionType: "MissedConnection",

  // Priority & Status
  priority: "P1",
  priorityLevel: 1,
  priorityScore: 0.85,
  status: "Open",

  // Association
  bagTag: "CM123456",
  pnr: "ABC123",
  passengerName: "Smith, John",
  flightNumber: "CM405",

  // Details
  title: "High risk of missed connection at MIA",
  description: "Bag CM123456 has 32 minute connection time at MIA, below MCT of 45 minutes",
  rootCause: "Inbound flight CM101 delayed by 18 minutes",

  // Risk Context
  riskScore: 0.85,
  riskLevel: "High",
  riskFactors: [
    "Connection time below MCT",
    "High traffic period",
    "Gold elite passenger"
  ],

  // Actions
  recommendedActions: [
    "Alert ground handling team",
    "Prepare for manual intervention",
    "Notify passenger of potential delay"
  ],
  actionsTaken: [],

  // Assignment
  assignedTo: "BaggageOpsTeam-MIA",
  assignedAt: datetime("2024-11-13T14:28:00Z"),
  assignedBy: "CaseManagerAgent-001",

  // SLA
  slaDeadline: datetime("2024-11-13T15:15:00Z"),
  slaRemaining: 47,
  slaRemainingUnit: "minutes",
  slaStatus: "OnTrack",

  // Financial
  potentialClaimCost: 250.00,
  preventionCost: 75.00,
  costBenefitRatio: 3.33,

  // Resolution
  resolvedAt: null,
  resolutionTime: null,
  resolutionMethod: null,
  outcome: null,

  // Semantic Metadata
  createdAt: datetime("2024-11-13T14:28:00Z"),
  updatedAt: datetime("2024-11-13T14:28:00Z"),
  createdBy: "CaseManagerAgent-001",
  confidence: 0.85,
  reasoning: "MCT violation detected with high-value passenger"
})
*/

// ----------------------------------------------------------------------------
// :Risk - Risk assessments and predictions
// ----------------------------------------------------------------------------
/*
CREATE (r:Risk {
  // Identity
  riskId: "risk-uuid-77777",
  riskType: "MissedConnection",

  // Assessment
  riskScore: 0.85,
  riskLevel: "High",
  confidence: 0.87,

  // Factors
  primaryFactors: [
    "Connection time 32 minutes (below MCT of 45)",
    "High traffic period at MIA",
    "Historical 15% bag misconnect rate for this routing"
  ],

  secondaryFactors: [
    "Gold elite passenger (VIP status)",
    "Bag weight 23.5kg within normal range",
    "Weather conditions normal"
  ],

  // Predictions
  predictedOutcome: "MissedConnection",
  predictedOutcomeProbability: 0.73,
  alternativeOutcomes: {
    "OnTimeDelivery": 0.27
  },

  // Recommendations
  recommendedAction: "Intervene",
  recommendedActionDetails: "Alert ground handling, prepare manual transfer",
  recommendedActionUrgency: "High",

  // Analysis
  reasoning: "Connection time of 32 minutes is 13 minutes below MCT. Historical data shows 73% probability of missed connection for similar scenarios at MIA during peak hours. Passenger is Gold elite, increasing priority for intervention.",

  // Context
  connectionTimeMinutes: 32,
  mctMinutes: 45,
  timeBelowMCT: -13,
  airportPerformanceScore: 8.5,
  weatherImpactScore: 0.1,
  trafficImpactScore: 0.6,

  // Model Info
  modelUsed: "RiskScoringModel_v2.3",
  modelConfidence: 0.87,
  featuresUsed: [
    "connection_time",
    "mct",
    "airport_performance",
    "traffic_volume",
    "passenger_status",
    "historical_patterns"
  ],

  // Timing
  assessedAt: datetime("2024-11-13T14:28:00Z"),
  validUntil: datetime("2024-11-13T15:30:00Z"),

  // Semantic Metadata
  createdBy: "RiskScorerAgent-001",
  agentId: "RiskScorerAgent-001",
  confidence: 0.87
})
*/

// ----------------------------------------------------------------------------
// :PIR - Property Irregularity Reports (WorldTracer)
// ----------------------------------------------------------------------------
/*
CREATE (p:PIR {
  // Identity
  pirNumber: "MIAHP12345",
  pirType: "OHD",
  worldTracerRef: "WT-MIA-20241113-001",

  // Classification
  irregularityType: "OversizedHandBaggage",
  iataCode: "OHD",
  resolutionCode: null,

  // Association
  bagTag: "CM123456",
  pnr: "ABC123",
  passengerName: "Smith, John",
  flightNumber: "CM405",

  // Report Details
  filedAt: datetime("2024-11-13T15:45:00Z"),
  filedBy: "WorldTracerAgent-001",
  filingStation: "MIA",

  // Baggage Description
  bagDescription: "Black Samsonite hardshell suitcase",
  bagColor: "Black",
  bagType: "Suitcase",
  bagBrand: "Samsonite",
  bagWeight: 23.5,

  // Contents
  contentsDescription: "Clothing, electronics, toiletries",
  contentsValue: 1200.00,
  contentsCurrency: "USD",

  // Location
  lastKnownLocation: "MIA-T3-BHS",
  expectedDestination: "JFK-T8",
  currentLocation: "Unknown",

  // Status
  status: "Open",
  statusUpdatedAt: datetime("2024-11-13T15:45:00Z"),

  // Resolution
  resolvedAt: null,
  resolutionTime: null,
  resolutionMethod: null,
  deliveryMethod: null,

  // Communication
  passengerNotified: true,
  notificationMethod: "Email",
  notificationTimestamp: datetime("2024-11-13T15:47:00Z"),

  // Financial
  interimExpenses: 0.00,
  compensationPaid: 0.00,
  liabilityClaim: 0.00,

  // Semantic Metadata
  createdAt: datetime("2024-11-13T15:45:00Z"),
  updatedAt: datetime("2024-11-13T15:45:00Z"),
  createdBy: "WorldTracerAgent-001"
})
*/

// ----------------------------------------------------------------------------
// :CourierDispatch - Courier deliveries
// ----------------------------------------------------------------------------
/*
CREATE (c:CourierDispatch {
  // Identity
  dispatchId: "courier-uuid-55555",

  // Association
  bagTag: "CM123456",
  pnr: "ABC123",
  pirNumber: "MIAHP12345",
  caseId: "CASE-20241113-001",

  // Courier Details
  courierVendor: "FedEx",
  courierServiceLevel: "Priority Overnight",
  trackingNumber: "1234567890",

  // Pickup
  pickupLocation: "MIA Airport Baggage Services",
  pickupAddress: "Miami International Airport, Terminal 3, Miami, FL 33142",
  pickupLatitude: 25.7959,
  pickupLongitude: -80.2870,
  pickupScheduledTime: datetime("2024-11-13T18:00:00Z"),
  pickupActualTime: null,

  // Delivery
  deliveryAddress: "123 Main St, New York, NY 10001",
  deliveryLatitude: 40.7503,
  deliveryLongitude: -73.9965,
  deliveryScheduledTime: datetime("2024-11-14T10:00:00Z"),
  deliveryActualTime: null,
  estimatedDeliveryTime: datetime("2024-11-14T10:00:00Z"),

  // Status
  status: "Approved",
  statusUpdatedAt: datetime("2024-11-13T15:50:00Z"),
  trackingStatus: "PickupScheduled",

  // Financial
  courierCost: 85.00,
  courierCostCurrency: "USD",
  potentialClaimCost: 250.00,
  costBenefitRatio: 2.94,

  // Approval
  requiresApproval: true,
  approvedBy: "StationManager-MIA",
  approvedAt: datetime("2024-11-13T15:50:00Z"),
  approvalReasoning: "Gold elite passenger, cost-benefit ratio favorable",

  // Decision Context
  passengerEliteStatus: "Gold",
  bagValue: 1200.00,
  alternativeOptions: ["RouteOnNextFlight", "OfferCompensation"],
  selectedOptionReasoning: "Courier dispatch most cost-effective for Gold elite passenger",

  // Semantic Metadata
  createdAt: datetime("2024-11-13T15:48:00Z"),
  updatedAt: datetime("2024-11-13T15:50:00Z"),
  createdBy: "CourierDispatchAgent-001",
  confidence: 0.92,
  reasoning: "Gold elite passenger with high lifetime value, courier cost justified"
})
*/

// ============================================================================
// PART 4: RELATIONSHIP TYPES WITH SEMANTIC PROPERTIES
// ============================================================================

// ----------------------------------------------------------------------------
// [:SCANNED_AT] - Bag was scanned at event
// ----------------------------------------------------------------------------
// (b:Baggage)-[:SCANNED_AT]->(s:ScanEvent)
/*
Properties:
  timestamp: datetime
  scanSequence: integer
  location: string
  scanType: string
  confidence: float (0.0-1.0)
  reasoning: string
  agentId: string
  processingTime: integer (milliseconds)
  validated: boolean

Sample:
MATCH (b:Baggage {bagTag: "CM123456"}), (s:ScanEvent {eventId: "scan-uuid-67890"})
CREATE (b)-[:SCANNED_AT {
  timestamp: datetime("2024-11-13T14:30:00Z"),
  scanSequence: 8,
  location: "MIA-T3-BHS",
  scanType: "Transfer",
  confidence: 0.99,
  reasoning: "Automatic BHS scan in expected sequence",
  agentId: "ScanProcessorAgent-001",
  processingTime: 87,
  validated: true
}]->(s)
*/

// ----------------------------------------------------------------------------
// [:BELONGS_TO] - Bag belongs to passenger
// ----------------------------------------------------------------------------
// (b:Baggage)-[:BELONGS_TO]->(p:Passenger)
/*
Properties:
  pnr: string
  bookingReference: string
  checkInTimestamp: datetime
  seatNumber: string
  cabinClass: string
  confidence: float
  dataSource: string

Sample:
MATCH (b:Baggage {bagTag: "CM123456"}), (p:Passenger {pnr: "ABC123"})
CREATE (b)-[:BELONGS_TO {
  pnr: "ABC123",
  bookingReference: "ABC123",
  checkInTimestamp: datetime("2024-11-13T08:15:00Z"),
  seatNumber: "12A",
  cabinClass: "Economy",
  confidence: 1.0,
  dataSource: "DCS"
}]->(p)
*/

// ----------------------------------------------------------------------------
// [:CHECKED_ON] - Bag checked on flight
// ----------------------------------------------------------------------------
// (b:Baggage)-[:CHECKED_ON]->(f:Flight)
/*
Properties:
  flightNumber: string
  segmentNumber: integer
  totalSegments: integer
  isConnecting: boolean
  connectionTime: integer (minutes)
  routing: string
  checkInTimestamp: datetime
  expectedArrivalTime: datetime
  confidence: float

Sample:
MATCH (b:Baggage {bagTag: "CM123456"}), (f:Flight {flightNumber: "CM405"})
CREATE (b)-[:CHECKED_ON {
  flightNumber: "CM405",
  segmentNumber: 2,
  totalSegments: 2,
  isConnecting: true,
  connectionTime: 45,
  routing: "PTY-MIA-JFK",
  checkInTimestamp: datetime("2024-11-13T08:15:00Z"),
  expectedArrivalTime: datetime("2024-11-13T19:45:00Z"),
  confidence: 1.0
}]->(f)
*/

// ----------------------------------------------------------------------------
// [:LOCATED_AT] - Bag currently located at location
// ----------------------------------------------------------------------------
// (b:Baggage)-[:LOCATED_AT]->(l:Location)
/*
Properties:
  timestamp: datetime
  locationType: string
  confidence: float (0.0-1.0)
  reasoning: string
  lastScanType: string
  durationMinutes: integer
  isExpectedLocation: boolean

Sample:
MATCH (b:Baggage {bagTag: "CM123456"}), (l:Location {locationId: "loc-mia-t3-bhs-001"})
CREATE (b)-[:LOCATED_AT {
  timestamp: datetime("2024-11-13T14:30:00Z"),
  locationType: "BaggageHandlingSystem",
  confidence: 0.98,
  reasoning: "Last scan event at this location",
  lastScanType: "Transfer",
  durationMinutes: 12,
  isExpectedLocation: true
}]->(l)
*/

// ----------------------------------------------------------------------------
// [:HAS_RISK] - Bag has risk assessment
// ----------------------------------------------------------------------------
// (b:Baggage)-[:HAS_RISK]->(r:Risk)
/*
Properties:
  riskScore: float (0.0-1.0)
  riskLevel: string
  assessedAt: datetime
  validUntil: datetime
  factors: string[]
  confidence: float
  reasoning: string
  agentId: string

Sample:
MATCH (b:Baggage {bagTag: "CM123456"}), (r:Risk {riskId: "risk-uuid-77777"})
CREATE (b)-[:HAS_RISK {
  riskScore: 0.85,
  riskLevel: "High",
  assessedAt: datetime("2024-11-13T14:28:00Z"),
  validUntil: datetime("2024-11-13T15:30:00Z"),
  factors: ["Connection time below MCT", "High traffic period"],
  confidence: 0.87,
  reasoning: "32 minute connection time is 13 minutes below MCT of 45 minutes",
  agentId: "RiskScorerAgent-001"
}]->(r)
*/

// ----------------------------------------------------------------------------
// [:PROCESSED_BY] - Event processed by agent
// ----------------------------------------------------------------------------
// (s:ScanEvent)-[:PROCESSED_BY]->(a:Agent)
/*
Properties:
  timestamp: datetime
  processingTime: integer (milliseconds)
  success: boolean
  errorMessage: string
  outputType: string
  confidence: float

Sample:
MATCH (s:ScanEvent {eventId: "scan-uuid-67890"}), (a:Agent {agentId: "ScanProcessorAgent-001"})
CREATE (s)-[:PROCESSED_BY {
  timestamp: datetime("2024-11-13T14:30:01Z"),
  processingTime: 87,
  success: true,
  errorMessage: null,
  outputType: "BaggageUpdate",
  confidence: 0.99
}]->(a)
*/

// ----------------------------------------------------------------------------
// [:TRIGGERS] - Risk triggers exception
// ----------------------------------------------------------------------------
// (r:Risk)-[:TRIGGERS]->(e:Exception)
/*
Properties:
  threshold: float
  triggerReason: string
  timestamp: datetime
  priority: string
  confidence: float
  reasoning: string
  agentId: string

Sample:
MATCH (r:Risk {riskId: "risk-uuid-77777"}), (e:Exception {caseId: "CASE-20241113-001"})
CREATE (r)-[:TRIGGERS {
  threshold: 0.7,
  triggerReason: "Risk score 0.85 exceeds high risk threshold",
  timestamp: datetime("2024-11-13T14:28:00Z"),
  priority: "P1",
  confidence: 0.85,
  reasoning: "High probability of missed connection requires immediate intervention",
  agentId: "CaseManagerAgent-001"
}]->(e)
*/

// ----------------------------------------------------------------------------
// [:SENDS_MESSAGE] - Agent sends message to another agent
// ----------------------------------------------------------------------------
// (sender:Agent)-[:SENDS_MESSAGE]->(receiver:Agent)
/*
Properties:
  messageId: string
  messageType: string
  timestamp: datetime
  payload: map
  priority: string
  requiresResponse: boolean
  responseTimeout: integer (seconds)

Sample:
MATCH (sender:Agent {agentId: "ScanProcessorAgent-001"}),
      (receiver:Agent {agentId: "RiskScorerAgent-001"})
CREATE (sender)-[:SENDS_MESSAGE {
  messageId: "msg-uuid-99999",
  messageType: "BaggageUpdate",
  timestamp: datetime("2024-11-13T14:30:02Z"),
  payload: {bagTag: "CM123456", status: "InTransit"},
  priority: "Normal",
  requiresResponse: true,
  responseTimeout: 5000
}]->(receiver)
*/

// ----------------------------------------------------------------------------
// [:REQUIRES_APPROVAL] - Exception requires human approval
// ----------------------------------------------------------------------------
// (e:Exception)-[:REQUIRES_APPROVAL]->(h:HumanAgent)
/*
Properties:
  requestedAt: datetime
  priority: string
  slaDeadline: datetime
  approvalType: string
  context: string
  reasoning: string

Sample:
MATCH (e:Exception {caseId: "CASE-20241113-001"}),
      (h:Agent {agentId: "StationManager-MIA"})
CREATE (e)-[:REQUIRES_APPROVAL {
  requestedAt: datetime("2024-11-13T14:28:00Z"),
  priority: "P1",
  slaDeadline: datetime("2024-11-13T15:15:00Z"),
  approvalType: "CourierDispatch",
  context: "Gold elite passenger with tight connection",
  reasoning: "Courier cost $85 justified by potential claim cost $250 and passenger value"
}]->(h)
*/

// ----------------------------------------------------------------------------
// [:DISPATCHES] - Courier dispatch for baggage
// ----------------------------------------------------------------------------
// (c:CourierDispatch)-[:DISPATCHES]->(b:Baggage)
/*
Properties:
  dispatchId: string
  courierVendor: string
  cost: float
  estimatedDeliveryTime: datetime
  trackingNumber: string
  confidence: float
  reasoning: string
  agentId: string

Sample:
MATCH (c:CourierDispatch {dispatchId: "courier-uuid-55555"}),
      (b:Baggage {bagTag: "CM123456"})
CREATE (c)-[:DISPATCHES {
  dispatchId: "courier-uuid-55555",
  courierVendor: "FedEx",
  cost: 85.00,
  estimatedDeliveryTime: datetime("2024-11-14T10:00:00Z"),
  trackingNumber: "1234567890",
  confidence: 0.92,
  reasoning: "Gold elite passenger, cost-benefit favorable",
  agentId: "CourierDispatchAgent-001"
}]->(b)
*/

// ----------------------------------------------------------------------------
// [:GENERATED_PIR] - Exception generated PIR
// ----------------------------------------------------------------------------
// (e:Exception)-[:GENERATED_PIR]->(p:PIR)
/*
Properties:
  pirNumber: string
  filedAt: datetime
  filingStation: string
  pirType: string
  confidence: float
  agentId: string

Sample:
MATCH (e:Exception {caseId: "CASE-20241113-001"}),
      (p:PIR {pirNumber: "MIAHP12345"})
CREATE (e)-[:GENERATED_PIR {
  pirNumber: "MIAHP12345",
  filedAt: datetime("2024-11-13T15:45:00Z"),
  filingStation: "MIA",
  pirType: "OHD",
  confidence: 1.0,
  agentId: "WorldTracerAgent-001"
}]->(p)
*/

// ----------------------------------------------------------------------------
// [:AT_LOCATION] - Scan event occurred at location
// ----------------------------------------------------------------------------
// (s:ScanEvent)-[:AT_LOCATION]->(l:Location)
/*
Properties:
  timestamp: datetime
  scanType: string
  confidence: float

Sample:
MATCH (s:ScanEvent {eventId: "scan-uuid-67890"}),
      (l:Location {locationId: "loc-mia-t3-bhs-001"})
CREATE (s)-[:AT_LOCATION {
  timestamp: datetime("2024-11-13T14:30:00Z"),
  scanType: "Transfer",
  confidence: 0.99
}]->(l)
*/

// ----------------------------------------------------------------------------
// [:CONCERNS] - Exception concerns baggage
// ----------------------------------------------------------------------------
// (e:Exception)-[:CONCERNS]->(b:Baggage)
/*
Properties:
  priority: string
  createdAt: datetime
  reasoning: string

Sample:
MATCH (e:Exception {caseId: "CASE-20241113-001"}),
      (b:Baggage {bagTag: "CM123456"})
CREATE (e)-[:CONCERNS {
  priority: "P1",
  createdAt: datetime("2024-11-13T14:28:00Z"),
  reasoning: "High risk of missed connection"
}]->(b)
*/

// ----------------------------------------------------------------------------
// [:ASSIGNED_TO] - Exception assigned to human agent
// ----------------------------------------------------------------------------
// (e:Exception)-[:ASSIGNED_TO]->(h:Agent)
/*
Properties:
  assignedAt: datetime
  assignedBy: string
  priority: string
  slaDeadline: datetime

Sample:
MATCH (e:Exception {caseId: "CASE-20241113-001"}),
      (h:Agent {agentId: "BaggageOpsTeam-MIA"})
CREATE (e)-[:ASSIGNED_TO {
  assignedAt: datetime("2024-11-13T14:28:00Z"),
  assignedBy: "CaseManagerAgent-001",
  priority: "P1",
  slaDeadline: datetime("2024-11-13T15:15:00Z")
}]->(h)
*/

// ----------------------------------------------------------------------------
// [:HAS_ASSESSMENT] - Exception has risk assessment
// ----------------------------------------------------------------------------
// (e:Exception)-[:HAS_ASSESSMENT]->(r:Risk)
/*
Properties:
  assessedAt: datetime
  riskScore: float
  confidence: float

Sample:
MATCH (e:Exception {caseId: "CASE-20241113-001"}),
      (r:Risk {riskId: "risk-uuid-77777"})
CREATE (e)-[:HAS_ASSESSMENT {
  assessedAt: datetime("2024-11-13T14:28:00Z"),
  riskScore: 0.85,
  confidence: 0.87
}]->(r)
*/

// ----------------------------------------------------------------------------
// [:DOCUMENTS] - PIR documents baggage issue
// ----------------------------------------------------------------------------
// (p:PIR)-[:DOCUMENTS]->(b:Baggage)
/*
Properties:
  pirNumber: string
  pirType: string
  filedAt: datetime
  status: string

Sample:
MATCH (p:PIR {pirNumber: "MIAHP12345"}),
      (b:Baggage {bagTag: "CM123456"})
CREATE (p)-[:DOCUMENTS {
  pirNumber: "MIAHP12345",
  pirType: "OHD",
  filedAt: datetime("2024-11-13T15:45:00Z"),
  status: "Open"
}]->(b)
*/

// ----------------------------------------------------------------------------
// [:CREATED] - Agent created entity
// ----------------------------------------------------------------------------
// (a:Agent)-[:CREATED]->(entity)
/*
Properties:
  createdAt: datetime
  entityType: string
  confidence: float
  reasoning: string

Sample:
MATCH (a:Agent {agentId: "RiskScorerAgent-001"}),
      (r:Risk {riskId: "risk-uuid-77777"})
CREATE (a)-[:CREATED {
  createdAt: datetime("2024-11-13T14:28:00Z"),
  entityType: "Risk",
  confidence: 0.87,
  reasoning: "Risk assessment based on connection time analysis"
}]->(r)
*/

// ----------------------------------------------------------------------------
// [:UPDATED] - Agent updated entity
// ----------------------------------------------------------------------------
// (a:Agent)-[:UPDATED]->(entity)
/*
Properties:
  updatedAt: datetime
  updateType: string
  previousValue: map
  newValue: map
  reasoning: string

Sample:
MATCH (a:Agent {agentId: "ScanProcessorAgent-001"}),
      (b:Baggage {bagTag: "CM123456"})
CREATE (a)-[:UPDATED {
  updatedAt: datetime("2024-11-13T14:30:00Z"),
  updateType: "LocationUpdate",
  previousValue: {location: "PTY-T1"},
  newValue: {location: "MIA-T3-BHS"},
  reasoning: "Updated based on latest BHS scan event"
}]->(b)
*/

// ----------------------------------------------------------------------------
// [:CONNECTS_TO] - Flight connects to another flight
// ----------------------------------------------------------------------------
// (f1:Flight)-[:CONNECTS_TO]->(f2:Flight)
/*
Properties:
  connectionTime: integer (minutes)
  mct: integer (minutes)
  connectionAirport: string
  isLegalConnection: boolean
  confidence: float

Sample:
MATCH (f1:Flight {flightNumber: "CM101"}),
      (f2:Flight {flightNumber: "CM405"})
CREATE (f1)-[:CONNECTS_TO {
  connectionTime: 32,
  mct: 45,
  connectionAirport: "MIA",
  isLegalConnection: false,
  confidence: 1.0
}]->(f2)
*/

// ----------------------------------------------------------------------------
// [:NOTIFIED] - Passenger notified about event
// ----------------------------------------------------------------------------
// (a:Agent)-[:NOTIFIED]->(p:Passenger)
/*
Properties:
  timestamp: datetime
  notificationType: string
  channel: string (Email, SMS, Push)
  messageContent: string
  deliveryStatus: string

Sample:
MATCH (a:Agent {agentId: "PassengerCommsAgent-001"}),
      (p:Passenger {pnr: "ABC123"})
CREATE (a)-[:NOTIFIED {
  timestamp: datetime("2024-11-13T14:32:00Z"),
  notificationType: "BaggageDelay",
  channel: "Email",
  messageContent: "Your baggage may experience a delay...",
  deliveryStatus: "Delivered"
}]->(p)
*/

// ============================================================================
// PART 5: SAMPLE GRAPH PATTERNS
// ============================================================================

// Pattern 1: Complete baggage journey
/*
MATCH journey = (b:Baggage {bagTag: "CM123456"})-[:SCANNED_AT*]->(s:ScanEvent)
RETURN journey
ORDER BY s.timestamp
*/

// Pattern 2: High-risk bags with exceptions
/*
MATCH (b:Baggage)-[hr:HAS_RISK]->(r:Risk)-[t:TRIGGERS]->(e:Exception)
WHERE r.riskScore > 0.7
RETURN b, hr, r, t, e
ORDER BY r.riskScore DESC
*/

// Pattern 3: Agent communication flow
/*
MATCH (a1:Agent)-[sm:SENDS_MESSAGE]->(a2:Agent)
WHERE sm.timestamp > datetime() - duration({hours: 1})
RETURN a1.agentType, a2.agentType, sm.messageType, sm.timestamp
ORDER BY sm.timestamp DESC
*/

// Pattern 4: Passenger's baggage with risks
/*
MATCH (p:Passenger {pnr: "ABC123"})<-[:BELONGS_TO]-(b:Baggage)-[:HAS_RISK]->(r:Risk)
RETURN p, b, r
ORDER BY r.riskScore DESC
*/

// Pattern 5: Exceptions requiring approval
/*
MATCH (e:Exception)-[ra:REQUIRES_APPROVAL]->(h:Agent)
WHERE e.status = "Open"
RETURN e, ra, h
ORDER BY e.slaDeadline ASC
*/

// Pattern 6: Courier dispatches with cost analysis
/*
MATCH (c:CourierDispatch)-[d:DISPATCHES]->(b:Baggage)-[:BELONGS_TO]->(p:Passenger)
WHERE c.status = "Approved"
RETURN c, d, b, p
ORDER BY c.costBenefitRatio DESC
*/

// ============================================================================
// PART 6: FULL KNOWLEDGE GRAPH QUERIES
// ============================================================================

// Query 1: Find bags at risk of missing connections
/*
MATCH (b:Baggage)-[:CHECKED_ON {isConnecting: true}]->(f1:Flight)-[ct:CONNECTS_TO]->(f2:Flight)
WHERE ct.connectionTime < ct.mct
WITH b, f1, f2, ct
MATCH (b)-[:HAS_RISK]->(r:Risk)
WHERE r.riskLevel IN ["High", "Critical"]
RETURN b.bagTag, b.currentLocation,
       f1.flightNumber, f2.flightNumber,
       ct.connectionTime, ct.mct,
       r.riskScore, r.primaryFactors
ORDER BY r.riskScore DESC
*/

// Query 2: Agent processing pipeline
/*
MATCH path = (s:ScanEvent)-[:PROCESSED_BY]->(a1:Agent)-[:SENDS_MESSAGE]->(a2:Agent)-[:CREATED]->(r:Risk)
WHERE s.timestamp > datetime() - duration({hours: 2})
RETURN path
LIMIT 10
*/

// Query 3: Baggage with scan gaps
/*
MATCH (b:Baggage)-[sa:SCANNED_AT]->(s:ScanEvent)
WITH b, s ORDER BY s.timestamp
WITH b, collect(s) as scans
WHERE size(scans) > 1
WITH b, scans,
     [i in range(0, size(scans)-2) |
      duration.between(scans[i].timestamp, scans[i+1].timestamp).minutes] as gaps
WHERE any(gap in gaps WHERE gap > 30)
RETURN b.bagTag, b.currentLocation, b.status, gaps
ORDER BY head([gap in gaps WHERE gap > 30]) DESC
*/

// Query 4: Airport performance analysis
/*
MATCH (a:Airport)<-[:AT_LOCATION]-(s:ScanEvent)<-[:SCANNED_AT]-(b:Baggage)
WHERE s.timestamp > datetime() - duration({days: 7})
WITH a, count(DISTINCT b) as totalBags
MATCH (a)<-[:AT_LOCATION]-(s2:ScanEvent)<-[:SCANNED_AT]-(b2:Baggage)-[:HAS_RISK]->(r:Risk)
WHERE r.riskLevel IN ["High", "Critical"]
  AND s2.timestamp > datetime() - duration({days: 7})
WITH a, totalBags, count(DISTINCT b2) as highRiskBags
RETURN a.iataCode, a.airportName,
       totalBags,
       highRiskBags,
       round(100.0 * highRiskBags / totalBags, 2) as exceptionRate,
       a.performanceScore
ORDER BY exceptionRate DESC
*/

// Query 5: Semantic reasoning chain
/*
MATCH chain = (b:Baggage)-[:HAS_RISK]->(r:Risk)-[:TRIGGERS]->(e:Exception)-[:ASSIGNED_TO]->(h:Agent)
WHERE e.status = "Open"
WITH chain, b, r, e, h
MATCH (b)-[:BELONGS_TO]->(p:Passenger)
RETURN b.bagTag,
       p.name, p.eliteStatus,
       r.riskScore, r.reasoning,
       e.priority, e.recommendedActions,
       h.agentId
ORDER BY r.riskScore DESC
LIMIT 20
*/

// ============================================================================
// END OF SCHEMA
// ============================================================================

// Usage Notes:
// 1. Run constraints first (PART 1)
// 2. Run indexes after constraints (PART 2)
// 3. Use node definitions (PART 3) as templates for creating nodes
// 4. Use relationship definitions (PART 4) for creating edges
// 5. Use sample queries (PART 5-6) for testing

// Semantic Properties Legend:
// - confidence: How confident the agent is in this data (0.0-1.0)
// - reasoning: Natural language explanation of why this relationship exists
// - agentId: Which AI agent created or last updated this relationship
// - timestamp: When this relationship was created or updated

// For agent communication, all relationships should include:
// - confidence score
// - reasoning text
// - agent identifier
// - timestamp

// This enables:
// - Explainable AI decisions
// - Audit trails for all agent actions
// - Cross-agent semantic understanding
// - Confidence-based reasoning chains
