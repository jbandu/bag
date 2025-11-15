"""
Canonical Event Models

Defines standardized data structures for all baggage events.
All parsers convert their input formats to these canonical models.

Event Types:
- SCAN: Bag scanned at DCS/BHS/BRS
- TYPE_B: SITA Type B message (BTM/BSM/BPM)
- BAGGAGEXML: BaggageXML manifest
- WORLDTRACER: WorldTracer update/PIR
- EXCEPTION: Manual exception case
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """Types of baggage events"""
    SCAN = "scan"
    TYPE_B = "type_b"
    BAGGAGEXML = "baggagexml"
    WORLDTRACER = "worldtracer"
    EXCEPTION = "exception"
    MANUAL = "manual"


class ScanSource(str, Enum):
    """Source systems for scan events"""
    BRS = "BRS"  # Baggage Reconciliation System
    BHS = "BHS"  # Baggage Handling System
    DCS = "DCS"  # Departure Control System
    MANUAL = "MANUAL"  # Manual scan


class TypeBMessageType(str, Enum):
    """SITA Type B message types"""
    BTM = "BTM"  # Baggage Transfer Message
    BSM = "BSM"  # Baggage Source Message
    BPM = "BPM"  # Baggage Processing Message
    BNS = "BNS"  # Baggage Not Seen
    BUM = "BUM"  # Baggage Unloaded Message


class BagStatus(str, Enum):
    """Bag status values"""
    CHECKED_IN = "checked_in"
    IN_TRANSIT = "in_transit"
    LOADED = "loaded"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    MISHANDLED = "mishandled"
    DELAYED = "delayed"
    DAMAGED = "damaged"
    LOST = "lost"
    FOUND = "found"
    UNKNOWN = "unknown"


class PassengerInfo(BaseModel):
    """Passenger information"""
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    pnr: Optional[str] = None  # Passenger Name Record
    booking_reference: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    loyalty_number: Optional[str] = None
    loyalty_tier: Optional[str] = None  # ConnectMiles tier


class FlightInfo(BaseModel):
    """Flight information"""
    flight_number: str
    airline_code: str = "CM"  # Default to Copa
    origin: str
    destination: str
    scheduled_departure: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    scheduled_arrival: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    aircraft_type: Optional[str] = None


class BagInfo(BaseModel):
    """Baggage information"""
    bag_tag: str
    weight_kg: Optional[float] = None
    pieces: int = 1
    description: Optional[str] = None
    special_handling: Optional[List[str]] = Field(default_factory=list)  # e.g., ["PRIORITY", "FRAGILE"]
    status: BagStatus = BagStatus.UNKNOWN


class LocationInfo(BaseModel):
    """Location/station information"""
    station_code: str  # IATA airport code
    station_name: Optional[str] = None
    terminal: Optional[str] = None
    gate: Optional[str] = None
    carousel: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ParsingMetadata(BaseModel):
    """Metadata about the parsing process"""
    parser_name: str
    parser_version: str = "1.0.0"
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0)
    parsing_errors: List[str] = Field(default_factory=list)
    raw_input_hash: Optional[str] = None
    parsed_at: datetime = Field(default_factory=datetime.utcnow)


class BagEvent(BaseModel):
    """
    Canonical bag event model

    All parsers convert their input to this standardized format.
    This ensures consistent processing by downstream agents/workflows.
    """

    # Event metadata
    event_id: Optional[str] = None  # Generated if not provided
    event_type: EventType
    event_timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_system: Optional[str] = None  # e.g., "DCS", "BRS", "SITA", "WorldTracer"

    # Core entities
    bag: BagInfo
    passenger: Optional[PassengerInfo] = None
    flight: Optional[FlightInfo] = None
    location: Optional[LocationInfo] = None

    # Additional data
    message_type: Optional[TypeBMessageType] = None  # For Type B messages
    raw_message: Optional[str] = None  # Original message for debugging
    metadata: Optional[ParsingMetadata] = None

    # Context
    airline_id: int = 1  # Default to Copa
    correlation_id: Optional[str] = None  # For tracking related events

    # Additional fields
    extra_data: Dict[str, Any] = Field(default_factory=dict)

    @validator('event_id', always=True)
    def generate_event_id(cls, v, values):
        """Generate event ID if not provided"""
        if v is None:
            import uuid
            return str(uuid.uuid4())
        return v

    @validator('bag_tag', pre=True)
    def normalize_bag_tag(cls, v):
        """Normalize bag tag format (remove spaces, uppercase)"""
        if isinstance(v, str):
            return v.replace(" ", "").upper()
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO datetime strings"""
        return self.dict(exclude_none=True)

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class ParseResult(BaseModel):
    """
    Result of parsing operation

    Contains parsed event and metadata about the parsing process
    """
    success: bool
    event: Optional[BagEvent] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0)
    parser_name: str
    raw_input: Optional[str] = None  # For debugging

    def is_valid(self) -> bool:
        """Check if parse was successful and event is valid"""
        return self.success and self.event is not None and not self.errors
