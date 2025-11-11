"""
Core data models for baggage operations platform
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BagStatus(str, Enum):
    """Baggage tracking status"""
    CHECKED_IN = "checked_in"
    IN_TRANSIT = "in_transit"
    LOADED = "loaded"
    OFFLOADED = "offloaded"
    ARRIVED = "arrived"
    CLAIMED = "claimed"
    DELAYED = "delayed"
    MISHANDLED = "mishandled"
    IN_RECOVERY = "in_recovery"


class ScanType(str, Enum):
    """Types of baggage scans"""
    CHECK_IN = "check_in"
    SORTATION = "sortation"
    LOAD = "load"
    OFFLOAD = "offload"
    ARRIVAL = "arrival"
    CLAIM = "claim"
    MANUAL = "manual"
    BTM = "btm"  # Baggage Transfer Message
    BSM = "bsm"  # Baggage Source Message
    BPM = "bpm"  # Baggage Processing Message


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PIRType(str, Enum):
    """WorldTracer PIR types"""
    OHD = "ohd"  # Offload
    FIR = "fir"  # Found in system
    AHL = "ahl"  # Arrival hall (unclaimed)
    PIR = "pir"  # Property Irregularity Report
    DELAYED = "delayed"


class PassengerInfo(BaseModel):
    """Passenger information"""
    name: str
    pnr: str
    email: Optional[str] = None
    phone: Optional[str] = None
    elite_status: Optional[str] = None
    lifetime_value: Optional[float] = None
    frequent_flyer_number: Optional[str] = None


class FlightInfo(BaseModel):
    """Flight details"""
    flight_number: str
    origin: str
    destination: str
    scheduled_departure: datetime
    scheduled_arrival: datetime
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    aircraft_type: str
    status: str


class BagData(BaseModel):
    """Core baggage data model"""
    bag_tag: str
    passenger: PassengerInfo
    routing: List[str]  # List of airport codes
    current_location: str
    status: BagStatus
    weight_kg: float
    contents_value: Optional[float] = None
    special_handling: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Journey tracking
    origin_flight: FlightInfo
    destination_flight: Optional[FlightInfo] = None
    connection_flights: List[FlightInfo] = Field(default_factory=list)
    
    # Risk tracking
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    risk_factors: List[str] = Field(default_factory=list)
    
    # Digital twin
    digital_twin_id: Optional[str] = None


class ScanEvent(BaseModel):
    """Baggage scan event"""
    event_id: str = Field(default_factory=lambda: f"scan_{datetime.utcnow().timestamp()}")
    bag_tag: str
    scan_type: ScanType
    location: str
    timestamp: datetime
    scanner_id: Optional[str] = None
    operator_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    error_codes: List[str] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    """Risk assessment result"""
    bag_tag: str
    risk_score: float  # 0-1
    risk_level: RiskLevel
    primary_factors: List[str]
    recommended_action: str
    confidence: float
    reasoning: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Context
    connection_time_minutes: Optional[int] = None
    mct_minutes: Optional[int] = None
    airport_performance_score: Optional[float] = None
    weather_impact_score: Optional[float] = None


class WorldTracerPIR(BaseModel):
    """WorldTracer Property Irregularity Report"""
    pir_number: str
    pir_type: PIRType
    bag_tag: str
    passenger: PassengerInfo
    flight: FlightInfo
    
    # Details
    bag_description: str
    contents_description: Optional[str] = None
    last_known_location: str
    expected_destination: str
    
    # Status
    status: str = "open"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


class ExceptionCase(BaseModel):
    """Exception case management"""
    case_id: str = Field(default_factory=lambda: f"case_{datetime.utcnow().timestamp()}")
    bag_tag: str
    priority: str  # P0, P1, P2, P3
    assigned_to: Optional[str] = None
    status: str = "open"
    
    # Details
    risk_assessment: RiskAssessment
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    
    # Timeline
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    sla_deadline: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class CourierDispatch(BaseModel):
    """Courier dispatch information"""
    dispatch_id: str = Field(default_factory=lambda: f"dispatch_{datetime.utcnow().timestamp()}")
    bag_tag: str
    pir_number: Optional[str] = None
    
    # Logistics
    courier_vendor: str
    pickup_location: str
    delivery_address: str
    estimated_delivery: datetime
    
    # Costs
    courier_cost: float
    potential_claim_cost: float
    cost_benefit_ratio: float
    
    # Status
    status: str = "pending"
    requires_approval: bool = False
    approved_by: Optional[str] = None
    tracking_number: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PassengerNotification(BaseModel):
    """Passenger communication tracking"""
    notification_id: str = Field(default_factory=lambda: f"notif_{datetime.utcnow().timestamp()}")
    bag_tag: str
    passenger: PassengerInfo
    
    # Message
    message_type: str  # proactive, update, resolved
    channels: List[str]  # sms, email, push, web
    sms_content: Optional[str] = None
    email_content: Optional[str] = None
    push_content: Optional[str] = None
    
    # Status
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    delivery_status: Dict[str, str] = Field(default_factory=dict)


class BaggageOperationsState(BaseModel):
    """LangGraph state for orchestrator"""
    # Input
    raw_scan: Optional[str] = None
    scan_event: Optional[ScanEvent] = None
    
    # Processing
    bag_data: Optional[BagData] = None
    parsed_event: Optional[Dict[str, Any]] = None
    is_valid_sequence: bool = True
    
    # Risk assessment
    risk_assessment: Optional[RiskAssessment] = None
    
    # Actions taken
    worldtracer_pir: Optional[WorldTracerPIR] = None
    exception_case: Optional[ExceptionCase] = None
    courier_dispatch: Optional[CourierDispatch] = None
    notifications_sent: List[PassengerNotification] = Field(default_factory=list)
    
    # Control flow
    requires_exception_handling: bool = False
    requires_human_approval: bool = False
    actions_completed: List[str] = Field(default_factory=list)
    
    # Metadata
    processing_started_at: datetime = Field(default_factory=datetime.utcnow)
    processing_completed_at: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True
