"""
Semantic Message Ontology for Agent-to-Agent Communication
============================================================

This module defines Pydantic models for all inter-agent messages in the
baggage operations system. Each message type includes semantic properties
for explainability, traceability, and confidence scoring.

Based on: gist (Semantic Arts) Foundational Ontology
Version: 1.0.0
Date: 2024-11-13

Agent Communication Flow:
1. ScanEventProcessor → RiskScorer, DigitalTwin
2. RiskScorer → CaseManager, CourierDispatch
3. WorldTracer → CaseManager, PassengerComms
4. SITAHandler → All agents
5. BaggageXMLHandler → RiskScorer, WorldTracer
6. CaseManager → All agents (orchestration)
7. CourierDispatch → CaseManager, PassengerComms
8. PassengerComms → External systems
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, validator, root_validator, EmailStr, constr, confloat, conint


# ============================================================================
# ENUMERATIONS - Type-safe message properties
# ============================================================================

class AgentType(str, Enum):
    """8 specialized AI agents in the system"""
    SCAN_PROCESSOR = "ScanProcessorAgent"
    RISK_SCORER = "RiskScorerAgent"
    WORLDTRACER = "WorldTracerAgent"
    SITA_HANDLER = "SITAHandlerAgent"
    BAGGAGE_XML = "BaggageXMLAgent"
    CASE_MANAGER = "CaseManagerAgent"
    COURIER_DISPATCH = "CourierDispatchAgent"
    PASSENGER_COMMS = "PassengerCommsAgent"


class SemanticIntent(str, Enum):
    """Semantic meaning of the message"""
    INFORM = "inform"  # Share information
    REQUEST = "request"  # Request action
    COMMAND = "command"  # Direct command
    QUERY = "query"  # Ask for data
    RESPONSE = "response"  # Reply to request/query
    NOTIFY = "notify"  # Send notification
    ALERT = "alert"  # Urgent notification
    UPDATE = "update"  # Update existing data
    CREATE = "create"  # Create new entity
    DELETE = "delete"  # Delete entity


class MessagePriority(int, Enum):
    """Message priority levels"""
    CRITICAL = 1  # Immediate action required
    HIGH = 2  # Important, process quickly
    NORMAL = 3  # Standard processing
    LOW = 4  # Background processing
    BULK = 5  # Batch processing


class ScanType(str, Enum):
    """Types of baggage scans"""
    CHECK_IN = "CheckIn"
    SORTATION = "Sortation"
    LOAD = "Load"
    OFFLOAD = "Offload"
    TRANSFER = "Transfer"
    ARRIVAL = "Arrival"
    CLAIM = "Claim"
    MANUAL = "Manual"
    BTM = "BTM"  # Baggage Tag Message
    BSM = "BSM"  # Baggage Source Message
    BPM = "BPM"  # Baggage Processing Message
    SECURITY_SCREENING = "SecurityScreening"
    CUSTOMS_INSPECTION = "CustomsInspection"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ExceptionType(str, Enum):
    """Types of baggage exceptions"""
    MISSED_CONNECTION = "MissedConnection"
    DELAYED = "Delayed"
    LOST = "Lost"
    DAMAGED = "Damaged"
    PILFERED = "Pilfered"
    OFFLOADED = "Offloaded"
    OVERSIZED = "Oversized"
    OVERWEIGHT = "Overweight"
    SCAN_GAP = "ScanGap"
    SECURITY_HOLD = "SecurityHold"


class ExceptionPriority(str, Enum):
    """Exception case priorities"""
    P0_CRITICAL = "P0"
    P1_HIGH = "P1"
    P2_MEDIUM = "P2"
    P3_LOW = "P3"


class PIRType(str, Enum):
    """WorldTracer PIR types"""
    OHD = "OHD"  # Overage, Damaged, Pilferage
    FIR = "FIR"  # Found Irregularity Report
    AHL = "AHL"  # Add to Hold Luggage
    DELAYED = "Delayed"
    DAMAGED = "Damaged"
    PILFERED = "Pilfered"


class TypeBMessageType(str, Enum):
    """IATA Type B message types"""
    BTM = "BTM"  # Baggage Tag Message
    BSM = "BSM"  # Baggage Source Message
    BPM = "BPM"  # Baggage Processing Message
    CPM = "CPM"  # Carrier Passenger Message
    UCM = "UCM"  # Unidentified Cargo Message


class NotificationChannel(str, Enum):
    """Passenger notification channels"""
    EMAIL = "Email"
    SMS = "SMS"
    PUSH = "Push"
    WHATSAPP = "WhatsApp"
    IN_APP = "InApp"


class CourierStatus(str, Enum):
    """Courier dispatch status"""
    PENDING = "Pending"
    APPROVED = "Approved"
    DISPATCHED = "Dispatched"
    IN_TRANSIT = "InTransit"
    DELIVERED = "Delivered"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


# ============================================================================
# BASE MESSAGE - All messages inherit from this
# ============================================================================

class BaseSemanticMessage(BaseModel):
    """
    Base class for all inter-agent messages.

    Every message includes semantic properties for:
    - Traceability (who sent, who receives, correlation)
    - Explainability (intent, confidence, reasoning)
    - Observability (timestamps, latency, success/failure)
    """

    # Identity
    message_id: UUID = Field(
        default_factory=uuid4,
        description="Unique message identifier"
    )

    # Routing
    source_agent: AgentType = Field(
        ...,
        description="Which agent sent this message"
    )

    target_agents: List[AgentType] = Field(
        ...,
        min_items=1,
        description="Which agents should receive this message"
    )

    # Timing
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this message was created (UTC)"
    )

    # Correlation (for tracking message chains)
    correlation_id: Optional[UUID] = Field(
        None,
        description="Links related messages together (e.g., request-response)"
    )

    # Semantic Properties
    semantic_intent: SemanticIntent = Field(
        ...,
        description="What action this message represents"
    )

    confidence_score: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="How confident the sender is in this message (0.0-1.0)"
    )

    reasoning: Optional[str] = Field(
        None,
        description="Natural language explanation of why this message was sent"
    )

    # Protocol
    requires_response: bool = Field(
        False,
        description="Does this message require a response?"
    )

    response_timeout_seconds: Optional[conint(gt=0)] = Field(
        None,
        description="How long to wait for response (if required)"
    )

    priority: MessagePriority = Field(
        MessagePriority.NORMAL,
        description="Message priority (1=Critical, 5=Bulk)"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context-specific metadata"
    )

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# ============================================================================
# MESSAGE TYPE 1: SCAN MESSAGE
# ============================================================================

class ScanMessage(BaseSemanticMessage):
    """
    Sent by: ScanProcessorAgent
    Sent to: RiskScorerAgent, DigitalTwin update

    Purpose: Notify other agents of a new scan event
    """

    # Scan Details
    bag_tag: constr(min_length=6, max_length=10) = Field(
        ...,
        description="Baggage tag number (e.g., CM123456)",
        regex="^[A-Z]{2}[0-9]{4,8}$"
    )

    scan_type: ScanType = Field(
        ...,
        description="Type of scan event"
    )

    location: str = Field(
        ...,
        min_length=3,
        description="Where the scan occurred (e.g., MIA-T3-BHS)"
    )

    scan_timestamp: datetime = Field(
        ...,
        description="When the physical scan occurred (may differ from message timestamp)"
    )

    # Raw Data
    raw_data: str = Field(
        ...,
        description="Raw scan data or Type B message"
    )

    # Parsed Data
    parsed_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data extracted from raw scan"
    )

    # Quality Metrics
    scan_quality: confloat(ge=0.0, le=1.0) = Field(
        1.0,
        description="Quality of the scan (0.0-1.0)"
    )

    read_confidence: confloat(ge=0.0, le=1.0) = Field(
        1.0,
        description="Confidence in baggage tag read (0.0-1.0)"
    )

    # Context
    flight_number: Optional[str] = Field(
        None,
        description="Associated flight number"
    )

    scanner_id: Optional[str] = Field(
        None,
        description="ID of the scanner that performed the scan"
    )

    operator_id: Optional[str] = Field(
        None,
        description="ID of operator (for manual scans)"
    )

    # Validation
    is_valid_sequence: bool = Field(
        True,
        description="Is this scan in the expected sequence?"
    )

    validation_errors: List[str] = Field(
        default_factory=list,
        description="Any validation errors detected"
    )

    @validator('scan_timestamp')
    def scan_timestamp_not_future(cls, v):
        if v > datetime.utcnow():
            raise ValueError('Scan timestamp cannot be in the future')
        return v

    class Config:
        schema_extra = {
            "example": {
                "source_agent": "ScanProcessorAgent",
                "target_agents": ["RiskScorerAgent"],
                "semantic_intent": "inform",
                "confidence_score": 0.99,
                "reasoning": "Automatic BHS scan in expected sequence",
                "bag_tag": "CM123456",
                "scan_type": "Transfer",
                "location": "MIA-T3-BHS",
                "scan_timestamp": "2024-11-13T14:30:00Z",
                "raw_data": "BPM/CM123456/MIA/T3/...",
                "flight_number": "CM405"
            }
        }


# ============================================================================
# MESSAGE TYPE 2: RISK MESSAGE
# ============================================================================

class RiskMessage(BaseSemanticMessage):
    """
    Sent by: RiskScorerAgent
    Sent to: CaseManagerAgent, CourierDispatchAgent

    Purpose: Communicate risk assessment results
    """

    # Risk Assessment
    bag_tag: constr(min_length=6, max_length=10) = Field(
        ...,
        description="Baggage tag number",
        regex="^[A-Z]{2}[0-9]{4,8}$"
    )

    risk_score: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Calculated risk score (0.0-1.0)"
    )

    risk_level: RiskLevel = Field(
        ...,
        description="Risk level category"
    )

    # Factors
    primary_factors: List[str] = Field(
        ...,
        min_items=1,
        description="Primary risk factors contributing to the score"
    )

    secondary_factors: List[str] = Field(
        default_factory=list,
        description="Secondary risk factors"
    )

    factor_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Weight of each factor in the risk calculation"
    )

    # Predictions
    prediction: str = Field(
        ...,
        description="Predicted outcome (e.g., 'MissedConnection', 'OnTimeDelivery')"
    )

    prediction_probability: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Confidence in the prediction (0.0-1.0)"
    )

    alternative_outcomes: Dict[str, float] = Field(
        default_factory=dict,
        description="Alternative outcomes with their probabilities"
    )

    # Recommendations
    recommended_action: str = Field(
        ...,
        description="Recommended action (e.g., 'Monitor', 'Alert', 'Intervene')"
    )

    recommended_action_urgency: Literal["Low", "Medium", "High", "Critical"] = Field(
        ...,
        description="Urgency of recommended action"
    )

    recommended_action_details: Optional[str] = Field(
        None,
        description="Detailed action recommendations"
    )

    # Context
    connection_time_minutes: Optional[int] = Field(
        None,
        description="Available connection time (for connection risk)"
    )

    mct_minutes: Optional[int] = Field(
        None,
        description="Minimum connection time at airport"
    )

    airport_performance_score: Optional[confloat(ge=0.0, le=10.0)] = Field(
        None,
        description="Airport performance score (0-10)"
    )

    # Model Info
    model_version: str = Field(
        "RiskScoringModel_v2.3",
        description="Version of risk scoring model used"
    )

    features_used: List[str] = Field(
        default_factory=list,
        description="Features used in the risk calculation"
    )

    @validator('risk_level')
    def risk_level_matches_score(cls, v, values):
        """Ensure risk level matches risk score"""
        if 'risk_score' in values:
            score = values['risk_score']
            if score < 0.3 and v != RiskLevel.LOW:
                raise ValueError('Risk score < 0.3 must be LOW')
            elif 0.3 <= score < 0.7 and v != RiskLevel.MEDIUM:
                raise ValueError('Risk score 0.3-0.7 must be MEDIUM')
            elif 0.7 <= score < 0.9 and v != RiskLevel.HIGH:
                raise ValueError('Risk score 0.7-0.9 must be HIGH')
            elif score >= 0.9 and v != RiskLevel.CRITICAL:
                raise ValueError('Risk score >= 0.9 must be CRITICAL')
        return v

    class Config:
        schema_extra = {
            "example": {
                "source_agent": "RiskScorerAgent",
                "target_agents": ["CaseManagerAgent"],
                "semantic_intent": "alert",
                "confidence_score": 0.87,
                "reasoning": "High risk of missed connection based on tight timing",
                "bag_tag": "CM123456",
                "risk_score": 0.85,
                "risk_level": "High",
                "primary_factors": [
                    "Connection time 32 min below MCT",
                    "High traffic period"
                ],
                "prediction": "MissedConnection",
                "prediction_probability": 0.73,
                "recommended_action": "Intervene",
                "recommended_action_urgency": "High"
            }
        }


# ============================================================================
# MESSAGE TYPE 3: EXCEPTION MESSAGE
# ============================================================================

class ExceptionMessage(BaseSemanticMessage):
    """
    Sent by: CaseManagerAgent
    Sent to: All relevant agents

    Purpose: Notify agents of exception cases requiring intervention
    """

    # Case Details
    case_id: str = Field(
        ...,
        min_length=5,
        description="Unique exception case ID"
    )

    bag_tag: constr(min_length=6, max_length=10) = Field(
        ...,
        description="Baggage tag number",
        regex="^[A-Z]{2}[0-9]{4,8}$"
    )

    exception_type: ExceptionType = Field(
        ...,
        description="Type of exception"
    )

    priority: ExceptionPriority = Field(
        ...,
        description="Exception priority"
    )

    # Description
    title: str = Field(
        ...,
        min_length=10,
        max_length=200,
        description="Brief title of the exception"
    )

    description: str = Field(
        ...,
        min_length=20,
        description="Detailed description of the exception"
    )

    root_cause: Optional[str] = Field(
        None,
        description="Identified root cause"
    )

    # Actions
    recommended_actions: List[str] = Field(
        ...,
        min_items=1,
        description="List of recommended actions"
    )

    actions_taken: List[str] = Field(
        default_factory=list,
        description="Actions already taken"
    )

    # Assignment
    assigned_to: Optional[str] = Field(
        None,
        description="Team or agent assigned to handle this"
    )

    assigned_at: Optional[datetime] = Field(
        None,
        description="When the case was assigned"
    )

    # SLA
    sla_deadline: datetime = Field(
        ...,
        description="SLA deadline for resolution"
    )

    sla_remaining_minutes: int = Field(
        ...,
        description="Minutes remaining until SLA breach"
    )

    # Financial
    potential_claim_cost: Optional[float] = Field(
        None,
        ge=0.0,
        description="Potential claim cost in USD"
    )

    prevention_cost: Optional[float] = Field(
        None,
        ge=0.0,
        description="Cost to prevent this exception in USD"
    )

    # Passenger Context
    passenger_name: Optional[str] = Field(
        None,
        description="Passenger name"
    )

    passenger_pnr: Optional[str] = Field(
        None,
        description="Passenger PNR"
    )

    passenger_elite_status: Optional[str] = Field(
        None,
        description="Passenger elite status"
    )

    @validator('sla_deadline')
    def sla_deadline_in_future(cls, v):
        if v < datetime.utcnow():
            raise ValueError('SLA deadline must be in the future')
        return v

    class Config:
        schema_extra = {
            "example": {
                "source_agent": "CaseManagerAgent",
                "target_agents": ["CourierDispatchAgent", "PassengerCommsAgent"],
                "semantic_intent": "command",
                "confidence_score": 0.85,
                "reasoning": "High-value passenger with missed connection",
                "case_id": "CASE-20241113-001",
                "bag_tag": "CM123456",
                "exception_type": "MissedConnection",
                "priority": "P1",
                "title": "High risk missed connection at MIA",
                "recommended_actions": [
                    "Alert ground handling",
                    "Dispatch courier if needed"
                ],
                "sla_deadline": "2024-11-13T15:15:00Z",
                "sla_remaining_minutes": 45
            }
        }


# ============================================================================
# MESSAGE TYPE 4: WORLDTRACER MESSAGE
# ============================================================================

class WorldTracerMessage(BaseSemanticMessage):
    """
    Sent by: WorldTracerAgent
    Sent to: CaseManagerAgent, PassengerCommsAgent

    Purpose: Communicate PIR status and baggage recovery info
    """

    # PIR Details
    pir_number: str = Field(
        ...,
        min_length=5,
        description="Property Irregularity Report number"
    )

    bag_tag: constr(min_length=6, max_length=10) = Field(
        ...,
        description="Baggage tag number",
        regex="^[A-Z]{2}[0-9]{4,8}$"
    )

    pir_type: PIRType = Field(
        ...,
        description="Type of PIR"
    )

    status: Literal["Open", "InProgress", "Resolved", "Closed"] = Field(
        ...,
        description="Current PIR status"
    )

    # Location
    last_known_location: str = Field(
        ...,
        description="Last known location of baggage"
    )

    current_location: Optional[str] = Field(
        None,
        description="Current location (if found)"
    )

    expected_destination: str = Field(
        ...,
        description="Expected destination"
    )

    # Routing
    original_routing: str = Field(
        ...,
        description="Original routing (e.g., PTY-MIA-JFK)"
    )

    new_routing: Optional[str] = Field(
        None,
        description="New routing (if rerouted)"
    )

    # Timeline
    filed_at: datetime = Field(
        ...,
        description="When PIR was filed"
    )

    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )

    resolved_at: Optional[datetime] = Field(
        None,
        description="When PIR was resolved"
    )

    # Baggage Description
    bag_description: str = Field(
        ...,
        min_length=10,
        description="Description of the baggage"
    )

    bag_color: Optional[str] = Field(
        None,
        description="Baggage color"
    )

    bag_type: Optional[str] = Field(
        None,
        description="Baggage type (Suitcase, Backpack, etc.)"
    )

    # WorldTracer Reference
    worldtracer_ref: str = Field(
        ...,
        description="WorldTracer system reference number"
    )

    filing_station: str = Field(
        ...,
        description="Airport code where PIR was filed"
    )

    # Passenger Info
    passenger_name: str = Field(
        ...,
        description="Passenger name"
    )

    passenger_contact: EmailStr = Field(
        ...,
        description="Passenger email contact"
    )

    passenger_notified: bool = Field(
        False,
        description="Has passenger been notified?"
    )

    class Config:
        schema_extra = {
            "example": {
                "source_agent": "WorldTracerAgent",
                "target_agents": ["CaseManagerAgent", "PassengerCommsAgent"],
                "semantic_intent": "inform",
                "confidence_score": 1.0,
                "reasoning": "PIR filed for missed connection",
                "pir_number": "MIAHP12345",
                "bag_tag": "CM123456",
                "pir_type": "OHD",
                "status": "Open",
                "last_known_location": "MIA-T3-BHS",
                "expected_destination": "JFK-T8",
                "original_routing": "PTY-MIA-JFK",
                "filed_at": "2024-11-13T15:45:00Z",
                "worldtracer_ref": "WT-MIA-20241113-001",
                "filing_station": "MIA",
                "passenger_name": "Smith, John",
                "passenger_contact": "john.smith@email.com"
            }
        }


# ============================================================================
# MESSAGE TYPE 5: TYPE B MESSAGE
# ============================================================================

class TypeBMessage(BaseSemanticMessage):
    """
    Sent by: SITAHandlerAgent
    Sent to: All agents (based on message type)

    Purpose: Distribute IATA Type B messages to relevant agents
    """

    # Message Details
    message_type: TypeBMessageType = Field(
        ...,
        description="Type of IATA Type B message"
    )

    raw_text: str = Field(
        ...,
        min_length=10,
        description="Raw Type B message text"
    )

    # Parsed Data
    parsed_data: Dict[str, Any] = Field(
        ...,
        description="Structured data parsed from Type B message"
    )

    # Protocol
    protocol_version: str = Field(
        "IATA_TypeB_16.1",
        description="IATA protocol version"
    )

    encoding: str = Field(
        "ASCII",
        description="Message encoding"
    )

    # Validation
    is_valid: bool = Field(
        True,
        description="Is the message valid per IATA spec?"
    )

    validation_errors: List[str] = Field(
        default_factory=list,
        description="Any validation errors"
    )

    # Context
    bag_tag: Optional[str] = Field(
        None,
        description="Baggage tag (if applicable)"
    )

    flight_number: Optional[str] = Field(
        None,
        description="Flight number (if applicable)"
    )

    origin_airport: Optional[str] = Field(
        None,
        description="Origin airport code"
    )

    destination_airport: Optional[str] = Field(
        None,
        description="Destination airport code"
    )

    # Source System
    source_system: str = Field(
        ...,
        description="Source system (BHS, DCS, etc.)"
    )

    received_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When message was received"
    )

    class Config:
        schema_extra = {
            "example": {
                "source_agent": "SITAHandlerAgent",
                "target_agents": ["ScanProcessorAgent", "RiskScorerAgent"],
                "semantic_intent": "inform",
                "confidence_score": 0.99,
                "reasoning": "Valid BPM message received from BHS",
                "message_type": "BPM",
                "raw_text": "BPM\nCM123456\n.MIA/T3\n.20241113/1430\n...",
                "parsed_data": {
                    "bag_tag": "CM123456",
                    "location": "MIA-T3",
                    "timestamp": "2024-11-13T14:30:00Z"
                },
                "is_valid": True,
                "source_system": "BHS"
            }
        }


# ============================================================================
# MESSAGE TYPE 6: XML MESSAGE
# ============================================================================

class XMLMessage(BaseSemanticMessage):
    """
    Sent by: BaggageXMLAgent
    Sent to: RiskScorerAgent, WorldTracerAgent

    Purpose: Distribute BaggageXML interline messages
    """

    # XML Details
    schema_version: str = Field(
        ...,
        description="BaggageXML schema version"
    )

    airline_code: constr(min_length=2, max_length=3) = Field(
        ...,
        description="Airline code (IATA 2-letter or ICAO 3-letter)"
    )

    # Manifest Data
    manifest_data: Dict[str, Any] = Field(
        ...,
        description="Parsed manifest data"
    )

    bags_count: conint(ge=0) = Field(
        ...,
        description="Number of bags in manifest"
    )

    flight_number: str = Field(
        ...,
        description="Flight number"
    )

    departure_date: datetime = Field(
        ...,
        description="Flight departure date/time"
    )

    # Origin/Destination
    origin_airport: constr(min_length=3, max_length=3) = Field(
        ...,
        description="Origin airport IATA code"
    )

    destination_airport: constr(min_length=3, max_length=3) = Field(
        ...,
        description="Destination airport IATA code"
    )

    # Interline Info
    is_interline: bool = Field(
        False,
        description="Is this an interline transfer?"
    )

    operating_carrier: Optional[str] = Field(
        None,
        description="Operating carrier (if different from marketing)"
    )

    marketing_carrier: Optional[str] = Field(
        None,
        description="Marketing carrier"
    )

    # Raw XML
    raw_xml: str = Field(
        ...,
        min_length=50,
        description="Raw XML content"
    )

    # Validation
    is_valid_xml: bool = Field(
        True,
        description="Is XML well-formed and valid?"
    )

    schema_validation_errors: List[str] = Field(
        default_factory=list,
        description="Schema validation errors"
    )

    class Config:
        schema_extra = {
            "example": {
                "source_agent": "BaggageXMLAgent",
                "target_agents": ["RiskScorerAgent"],
                "semantic_intent": "inform",
                "confidence_score": 1.0,
                "reasoning": "Valid BaggageXML manifest received",
                "schema_version": "3.0",
                "airline_code": "CM",
                "flight_number": "CM405",
                "bags_count": 125,
                "origin_airport": "MIA",
                "destination_airport": "JFK",
                "is_interline": False,
                "manifest_data": {"bags": []},
                "raw_xml": "<BaggageManifest>...</BaggageManifest>"
            }
        }


# ============================================================================
# MESSAGE TYPE 7: DISPATCH MESSAGE
# ============================================================================

class DispatchMessage(BaseSemanticMessage):
    """
    Sent by: CourierDispatchAgent
    Sent to: CaseManagerAgent, PassengerCommsAgent

    Purpose: Communicate courier dispatch decisions and status
    """

    # Courier Details
    courier_id: str = Field(
        ...,
        description="Unique courier dispatch ID"
    )

    bag_tag: constr(min_length=6, max_length=10) = Field(
        ...,
        description="Baggage tag number",
        regex="^[A-Z]{2}[0-9]{4,8}$"
    )

    courier_vendor: str = Field(
        ...,
        description="Courier vendor (FedEx, UPS, DHL, etc.)"
    )

    service_level: str = Field(
        ...,
        description="Service level (Priority Overnight, Standard, etc.)"
    )

    tracking_number: Optional[str] = Field(
        None,
        description="Courier tracking number"
    )

    # Pickup
    pickup_location: str = Field(
        ...,
        description="Pickup location"
    )

    pickup_address: str = Field(
        ...,
        description="Pickup address"
    )

    pickup_scheduled_time: datetime = Field(
        ...,
        description="Scheduled pickup time"
    )

    pickup_actual_time: Optional[datetime] = Field(
        None,
        description="Actual pickup time"
    )

    # Delivery
    delivery_address: str = Field(
        ...,
        description="Delivery address"
    )

    delivery_scheduled_time: datetime = Field(
        ...,
        description="Scheduled delivery time"
    )

    delivery_actual_time: Optional[datetime] = Field(
        None,
        description="Actual delivery time"
    )

    estimated_delivery_time: datetime = Field(
        ...,
        description="Estimated delivery time"
    )

    # Status
    status: CourierStatus = Field(
        ...,
        description="Current dispatch status"
    )

    status_updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When status was last updated"
    )

    # Financial
    courier_cost: confloat(ge=0.0) = Field(
        ...,
        description="Courier cost in USD"
    )

    potential_claim_cost: confloat(ge=0.0) = Field(
        ...,
        description="Potential claim cost if not dispatched (USD)"
    )

    cost_benefit_ratio: confloat(ge=0.0) = Field(
        ...,
        description="Cost-benefit ratio (potential_claim / courier_cost)"
    )

    # Approval
    requires_approval: bool = Field(
        False,
        description="Does this dispatch require approval?"
    )

    approved_by: Optional[str] = Field(
        None,
        description="Who approved this dispatch"
    )

    approved_at: Optional[datetime] = Field(
        None,
        description="When approved"
    )

    # Passenger Context
    passenger_elite_status: Optional[str] = Field(
        None,
        description="Passenger elite status"
    )

    passenger_lifetime_value: Optional[float] = Field(
        None,
        ge=0.0,
        description="Passenger lifetime value (USD)"
    )

    @validator('cost_benefit_ratio')
    def validate_cost_benefit(cls, v, values):
        """Validate cost-benefit calculation"""
        if 'courier_cost' in values and 'potential_claim_cost' in values:
            expected = values['potential_claim_cost'] / values['courier_cost']
            if abs(v - expected) > 0.01:
                raise ValueError('Cost-benefit ratio mismatch')
        return v

    class Config:
        schema_extra = {
            "example": {
                "source_agent": "CourierDispatchAgent",
                "target_agents": ["CaseManagerAgent", "PassengerCommsAgent"],
                "semantic_intent": "notify",
                "confidence_score": 0.92,
                "reasoning": "Gold elite passenger, cost-benefit favorable",
                "courier_id": "courier-uuid-55555",
                "bag_tag": "CM123456",
                "courier_vendor": "FedEx",
                "service_level": "Priority Overnight",
                "pickup_location": "MIA Airport",
                "pickup_address": "Miami Int'l Airport, Terminal 3",
                "pickup_scheduled_time": "2024-11-13T18:00:00Z",
                "delivery_address": "123 Main St, New York, NY 10001",
                "delivery_scheduled_time": "2024-11-14T10:00:00Z",
                "estimated_delivery_time": "2024-11-14T10:00:00Z",
                "status": "Approved",
                "courier_cost": 85.00,
                "potential_claim_cost": 250.00,
                "cost_benefit_ratio": 2.94
            }
        }


# ============================================================================
# MESSAGE TYPE 8: NOTIFICATION MESSAGE
# ============================================================================

class NotificationMessage(BaseSemanticMessage):
    """
    Sent by: PassengerCommsAgent
    Sent to: External notification systems

    Purpose: Send passenger notifications via multiple channels
    """

    # Passenger Details
    passenger_id: str = Field(
        ...,
        description="Passenger ID or PNR"
    )

    passenger_name: str = Field(
        ...,
        description="Passenger name"
    )

    # Notification Details
    channel: NotificationChannel = Field(
        ...,
        description="Notification channel"
    )

    template: str = Field(
        ...,
        description="Notification template name"
    )

    template_variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Variables to populate template"
    )

    # Content
    subject: Optional[str] = Field(
        None,
        description="Subject line (for email)"
    )

    message_body: str = Field(
        ...,
        min_length=10,
        description="Notification message body"
    )

    # Contact Info
    contact_email: Optional[EmailStr] = Field(
        None,
        description="Passenger email address"
    )

    contact_phone: Optional[str] = Field(
        None,
        description="Passenger phone number (E.164 format)",
        regex="^\+[1-9]\d{1,14}$"
    )

    # Delivery
    sent_at: Optional[datetime] = Field(
        None,
        description="When notification was sent"
    )

    delivery_status: Literal["Pending", "Sent", "Delivered", "Failed", "Bounced"] = Field(
        "Pending",
        description="Delivery status"
    )

    delivery_timestamp: Optional[datetime] = Field(
        None,
        description="When notification was delivered"
    )

    failure_reason: Optional[str] = Field(
        None,
        description="Reason for delivery failure"
    )

    # Context
    bag_tag: Optional[str] = Field(
        None,
        description="Related baggage tag"
    )

    case_id: Optional[str] = Field(
        None,
        description="Related exception case ID"
    )

    pir_number: Optional[str] = Field(
        None,
        description="Related PIR number"
    )

    # Preferences
    language: str = Field(
        "EN",
        description="Language code (ISO 639-1)"
    )

    timezone: str = Field(
        "UTC",
        description="Passenger timezone"
    )

    @validator('contact_email', 'contact_phone')
    def require_one_contact(cls, v, values, field):
        """Ensure at least one contact method is provided"""
        if field.name == 'contact_phone' and not v and not values.get('contact_email'):
            raise ValueError('Either contact_email or contact_phone must be provided')
        return v

    class Config:
        schema_extra = {
            "example": {
                "source_agent": "PassengerCommsAgent",
                "target_agents": [],
                "semantic_intent": "notify",
                "confidence_score": 1.0,
                "reasoning": "Passenger notification for baggage delay",
                "passenger_id": "ABC123",
                "passenger_name": "Smith, John",
                "channel": "Email",
                "template": "baggage_delay",
                "subject": "Update on Your Baggage - CM123456",
                "message_body": "Dear Mr. Smith, we want to inform you...",
                "contact_email": "john.smith@email.com",
                "delivery_status": "Sent",
                "bag_tag": "CM123456",
                "language": "EN"
            }
        }


# ============================================================================
# MESSAGE FACTORY - Create messages from dictionaries
# ============================================================================

MESSAGE_TYPE_MAP = {
    "scan": ScanMessage,
    "risk": RiskMessage,
    "exception": ExceptionMessage,
    "worldtracer": WorldTracerMessage,
    "typeb": TypeBMessage,
    "xml": XMLMessage,
    "dispatch": DispatchMessage,
    "notification": NotificationMessage
}


def create_message(message_type: str, data: dict) -> BaseSemanticMessage:
    """
    Factory function to create messages from dictionaries.

    Args:
        message_type: Type of message to create
        data: Dictionary of message data

    Returns:
        Instantiated message object

    Raises:
        ValueError: If message_type is unknown
    """
    if message_type not in MESSAGE_TYPE_MAP:
        raise ValueError(
            f"Unknown message type: {message_type}. "
            f"Valid types: {list(MESSAGE_TYPE_MAP.keys())}"
        )

    message_class = MESSAGE_TYPE_MAP[message_type]
    return message_class(**data)


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_message_chain(messages: List[BaseSemanticMessage]) -> bool:
    """
    Validate a chain of related messages using correlation_id.

    Args:
        messages: List of messages in chronological order

    Returns:
        True if chain is valid
    """
    if not messages:
        return True

    # First message starts the chain
    correlation_id = messages[0].correlation_id or messages[0].message_id

    # All subsequent messages should have same correlation_id
    for msg in messages[1:]:
        if msg.correlation_id != correlation_id:
            return False

    return True


def calculate_message_latency(
    send_time: datetime,
    receive_time: datetime
) -> int:
    """
    Calculate message latency in milliseconds.

    Args:
        send_time: When message was sent
        receive_time: When message was received

    Returns:
        Latency in milliseconds
    """
    delta = receive_time - send_time
    return int(delta.total_seconds() * 1000)
