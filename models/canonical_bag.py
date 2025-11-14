"""
Canonical Baggage Data Model
=============================

The single source of truth for baggage data across all systems.

This canonical model eliminates data friction by providing:
- Standardized field names and data types
- Semantic meaning for all attributes
- Data quality metadata (confidence, sources, lineage)
- IATA standard compliance
- Business rule validation

All external formats (DCS, BHS, WorldTracer, Type B, XML) map to/from this model.

Version: 1.0.0
Date: 2025-11-13
"""

from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator, constr, confloat
from uuid import UUID, uuid4


def make_aware(dt: datetime) -> datetime:
    """Make a datetime timezone-aware (UTC) if it's naive"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ============================================================================
# ENUMERATIONS
# ============================================================================

class BagState(str, Enum):
    """Semantic baggage states"""
    CHECKED_IN = "CHECKED_IN"
    IN_SYSTEM = "IN_SYSTEM"
    SORTED = "SORTED"
    LOADED = "LOADED"
    IN_FLIGHT = "IN_FLIGHT"
    ARRIVED = "ARRIVED"
    AT_CLAIM = "AT_CLAIM"
    CLAIMED = "CLAIMED"
    IN_TRANSFER = "IN_TRANSFER"
    EXCEPTION = "EXCEPTION"
    DELAYED = "DELAYED"
    MISHANDLED = "MISHANDLED"
    DAMAGED = "DAMAGED"
    PILFERED = "PILFERED"
    LOST = "LOST"
    FOUND = "FOUND"
    FORWARDED = "FORWARDED"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BagType(str, Enum):
    """Baggage types"""
    CHECKED = "CHECKED"
    CABIN = "CABIN"
    TRANSFER = "TRANSFER"
    RUSH = "RUSH"
    PRIORITY = "PRIORITY"
    HEAVY = "HEAVY"
    OVERSIZE = "OVERSIZE"
    SPORTS = "SPORTS"
    FRAGILE = "FRAGILE"
    DIPLOMATIC = "DIPLOMATIC"


class ServiceClass(str, Enum):
    """Passenger service class"""
    ECONOMY = "ECONOMY"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    BUSINESS = "BUSINESS"
    FIRST = "FIRST"


class ExceptionType(str, Enum):
    """Exception categories"""
    DELAYED = "DELAYED"
    MISHANDLED = "MISHANDLED"
    DAMAGED = "DAMAGED"
    PILFERED = "PILFERED"
    LOST = "LOST"
    MISROUTED = "MISROUTED"
    OFFLOADED = "OFFLOADED"
    SHORT_SHIPPED = "SHORT_SHIPPED"
    RUSH_TAG = "RUSH_TAG"
    SECURITY_HOLD = "SECURITY_HOLD"
    CUSTOMS_HOLD = "CUSTOMS_HOLD"


class DataSource(str, Enum):
    """External data sources"""
    DCS = "DCS"  # Departure Control System
    BHS = "BHS"  # Baggage Handling System
    WORLDTRACER = "WORLDTRACER"  # IATA WorldTracer
    TYPE_B = "TYPE_B"  # SITA Type B messages
    BAGGAGE_XML = "BAGGAGE_XML"  # BaggageXML format
    MANUAL_ENTRY = "MANUAL_ENTRY"
    AGENT = "AGENT"  # AI agent inference


# ============================================================================
# VALUE OBJECTS
# ============================================================================

class AirportCode(BaseModel):
    """IATA 3-letter airport code with validation"""

    iata_code: constr(min_length=3, max_length=3, pattern="^[A-Z]{3}$") = Field(
        ...,
        description="IATA 3-letter airport code"
    )

    airport_name: Optional[str] = Field(
        None,
        description="Full airport name"
    )

    city: Optional[str] = Field(
        None,
        description="City name"
    )

    country: Optional[str] = Field(
        None,
        description="Country code (ISO 3166-1 alpha-2)"
    )

    def __str__(self) -> str:
        return self.iata_code

    def __repr__(self) -> str:
        return f"AirportCode({self.iata_code})"


class FlightNumber(BaseModel):
    """IATA flight number with validation"""

    airline_code: constr(min_length=2, max_length=3, pattern="^[A-Z0-9]{2,3}$") = Field(
        ...,
        description="IATA 2-letter or 3-digit airline code"
    )

    flight_number: constr(min_length=1, max_length=4, pattern="^[0-9]{1,4}$") = Field(
        ...,
        description="Flight number (1-4 digits)"
    )

    suffix: Optional[str] = Field(
        None,
        description="Optional flight suffix (e.g., A, B)"
    )

    departure_date: Optional[datetime] = Field(
        None,
        description="Scheduled departure date/time"
    )

    @property
    def full_flight_number(self) -> str:
        """Get full flight number string"""
        base = f"{self.airline_code}{self.flight_number}"
        return f"{base}{self.suffix}" if self.suffix else base

    def __str__(self) -> str:
        return self.full_flight_number

    def __repr__(self) -> str:
        return f"FlightNumber({self.full_flight_number})"


class Location(BaseModel):
    """Semantic location information"""

    location_code: str = Field(
        ...,
        description="Location identifier code"
    )

    location_type: str = Field(
        ...,
        description="Type of location (e.g., CHECKIN, SORTATION, MAKEUP)"
    )

    airport: Optional[AirportCode] = Field(
        None,
        description="Airport where location is situated"
    )

    terminal: Optional[str] = Field(
        None,
        description="Terminal identifier"
    )

    area: Optional[str] = Field(
        None,
        description="Area within terminal"
    )

    facility: Optional[str] = Field(
        None,
        description="Specific facility (e.g., carousel number)"
    )

    semantic_meaning: Optional[str] = Field(
        None,
        description="Human-readable meaning of this location"
    )

    def __str__(self) -> str:
        return self.location_code


class ContactInfo(BaseModel):
    """Passenger contact information"""

    email: Optional[str] = Field(
        None,
        description="Email address"
    )

    phone: Optional[str] = Field(
        None,
        description="Phone number (international format)"
    )

    mobile: Optional[str] = Field(
        None,
        description="Mobile number (international format)"
    )

    address: Optional[str] = Field(
        None,
        description="Delivery address"
    )

    preferred_language: Optional[str] = Field(
        "EN",
        description="ISO 639-1 language code"
    )


class BagDimensions(BaseModel):
    """Physical bag dimensions"""

    weight_kg: Optional[float] = Field(
        None,
        description="Weight in kilograms",
        ge=0,
        le=200
    )

    length_cm: Optional[int] = Field(
        None,
        description="Length in centimeters",
        ge=0,
        le=300
    )

    width_cm: Optional[int] = Field(
        None,
        description="Width in centimeters",
        ge=0,
        le=200
    )

    height_cm: Optional[int] = Field(
        None,
        description="Height in centimeters",
        ge=0,
        le=200
    )

    @property
    def volume_liters(self) -> Optional[float]:
        """Calculate volume in liters"""
        if all([self.length_cm, self.width_cm, self.height_cm]):
            return (self.length_cm * self.width_cm * self.height_cm) / 1000
        return None

    @property
    def is_oversize(self) -> bool:
        """Check if bag exceeds standard size limits"""
        if self.volume_liters and self.volume_liters > 158:  # Linear dimensions > 158cm
            return True
        if self.weight_kg and self.weight_kg > 32:
            return True
        return False


class ExceptionCase(BaseModel):
    """Exception/irregularity case details"""

    case_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique case identifier"
    )

    exception_type: ExceptionType = Field(
        ...,
        description="Type of exception"
    )

    worldtracer_ref: Optional[str] = Field(
        None,
        description="WorldTracer OHD reference number"
    )

    reported_at: datetime = Field(
        default_factory=datetime.now,
        description="When exception was reported"
    )

    reported_by: Optional[str] = Field(
        None,
        description="Who reported the exception"
    )

    description: Optional[str] = Field(
        None,
        description="Exception description"
    )

    severity: str = Field(
        "MEDIUM",
        description="Severity level (LOW/MEDIUM/HIGH/CRITICAL)"
    )

    status: str = Field(
        "OPEN",
        description="Case status (OPEN/IN_PROGRESS/RESOLVED/CLOSED)"
    )

    assigned_to: Optional[str] = Field(
        None,
        description="Agent/person handling the case"
    )

    resolution_notes: Optional[str] = Field(
        None,
        description="How the case was resolved"
    )

    resolved_at: Optional[datetime] = Field(
        None,
        description="When case was resolved"
    )


class DataQuality(BaseModel):
    """Data quality metadata"""

    confidence: confloat(ge=0.0, le=1.0) = Field(
        1.0,
        description="Overall data confidence (0.0-1.0)"
    )

    completeness: confloat(ge=0.0, le=1.0) = Field(
        1.0,
        description="Percentage of fields populated"
    )

    accuracy: confloat(ge=0.0, le=1.0) = Field(
        1.0,
        description="Estimated accuracy of data"
    )

    timeliness: confloat(ge=0.0, le=1.0) = Field(
        1.0,
        description="How current is the data"
    )

    data_sources: List[DataSource] = Field(
        default_factory=list,
        description="Which systems contributed data"
    )

    source_timestamps: Dict[str, datetime] = Field(
        default_factory=dict,
        description="When each source last updated"
    )

    conflicts_detected: List[str] = Field(
        default_factory=list,
        description="Fields with conflicting data from sources"
    )

    conflicts_resolved: Dict[str, str] = Field(
        default_factory=dict,
        description="How conflicts were resolved"
    )

    validation_warnings: List[str] = Field(
        default_factory=list,
        description="Data quality warnings"
    )

    validation_errors: List[str] = Field(
        default_factory=list,
        description="Data validation errors"
    )

    last_validated: datetime = Field(
        default_factory=datetime.now,
        description="Last validation timestamp"
    )


# ============================================================================
# CANONICAL BAG MODEL
# ============================================================================

class CanonicalBag(BaseModel):
    """
    Canonical Baggage Data Model - Single Source of Truth

    This model represents the complete, unified view of a baggage item
    across all systems (DCS, BHS, WorldTracer, Type B, XML).
    """

    # ========================================================================
    # IDENTITY
    # ========================================================================

    bag_tag: constr(min_length=10, max_length=10, pattern="^[0-9]{10}$") = Field(
        ...,
        description="10-digit IATA standard bag tag number"
    )

    license_plate: Optional[str] = Field(
        None,
        description="BHS internal license plate number"
    )

    outbound_license_plate: Optional[str] = Field(
        None,
        description="Outbound flight license plate"
    )

    inbound_license_plate: Optional[str] = Field(
        None,
        description="Inbound flight license plate (for transfers)"
    )

    # ========================================================================
    # JOURNEY
    # ========================================================================

    origin: AirportCode = Field(
        ...,
        description="Origin airport (IATA 3-letter code)"
    )

    destination: AirportCode = Field(
        ...,
        description="Final destination airport"
    )

    intermediate_stops: List[AirportCode] = Field(
        default_factory=list,
        description="Connection airports in order"
    )

    current_location: Optional[Location] = Field(
        None,
        description="Current semantic location"
    )

    last_known_location: Optional[Location] = Field(
        None,
        description="Last confirmed location"
    )

    expected_location: Optional[Location] = Field(
        None,
        description="Where bag should be based on flight plan"
    )

    # ========================================================================
    # PASSENGER
    # ========================================================================

    passenger_name: str = Field(
        ...,
        description="Passenger full name"
    )

    passenger_first_name: Optional[str] = Field(
        None,
        description="Passenger first name"
    )

    passenger_last_name: Optional[str] = Field(
        None,
        description="Passenger last name"
    )

    pnr: Optional[str] = Field(
        None,
        description="Passenger Name Record / Booking reference"
    )

    ticket_number: Optional[str] = Field(
        None,
        description="E-ticket number"
    )

    contact: Optional[ContactInfo] = Field(
        None,
        description="Passenger contact information"
    )

    frequent_flyer_number: Optional[str] = Field(
        None,
        description="Frequent flyer membership number"
    )

    service_class: Optional[ServiceClass] = Field(
        None,
        description="Passenger service class"
    )

    is_vip: bool = Field(
        False,
        description="VIP passenger flag"
    )

    # ========================================================================
    # FLIGHT
    # ========================================================================

    outbound_flight: FlightNumber = Field(
        ...,
        description="Outbound flight information"
    )

    inbound_flight: Optional[FlightNumber] = Field(
        None,
        description="Inbound flight (for transfer bags)"
    )

    onward_flights: List[FlightNumber] = Field(
        default_factory=list,
        description="Subsequent flights for multi-leg journeys"
    )

    # ========================================================================
    # BAG CHARACTERISTICS
    # ========================================================================

    bag_type: BagType = Field(
        BagType.CHECKED,
        description="Type of baggage"
    )

    bag_sequence: int = Field(
        1,
        description="Bag sequence number for passenger (1, 2, 3...)",
        ge=1,
        le=99
    )

    total_bags: int = Field(
        1,
        description="Total number of bags for this passenger",
        ge=1,
        le=99
    )

    dimensions: Optional[BagDimensions] = Field(
        None,
        description="Physical dimensions and weight"
    )

    description: Optional[str] = Field(
        None,
        description="Bag description (color, type, brand)"
    )

    special_handling_codes: List[str] = Field(
        default_factory=list,
        description="Special handling indicators (e.g., FRAG, HEAVY)"
    )

    # ========================================================================
    # STATUS
    # ========================================================================

    current_state: BagState = Field(
        BagState.CHECKED_IN,
        description="Current semantic state"
    )

    previous_state: Optional[BagState] = Field(
        None,
        description="Previous state for state transition tracking"
    )

    state_updated_at: datetime = Field(
        default_factory=datetime.now,
        description="When state was last updated"
    )

    risk_level: RiskLevel = Field(
        RiskLevel.NONE,
        description="Current risk assessment"
    )

    risk_factors: List[str] = Field(
        default_factory=list,
        description="Active risk factors"
    )

    risk_score: confloat(ge=0.0, le=1.0) = Field(
        0.0,
        description="Quantitative risk score (0.0-1.0)"
    )

    exception_status: Optional[ExceptionCase] = Field(
        None,
        description="Exception case details if applicable"
    )

    is_mishandled: bool = Field(
        False,
        description="Mishandled flag"
    )

    is_tracked: bool = Field(
        True,
        description="Active tracking flag"
    )

    # ========================================================================
    # TIMELINE
    # ========================================================================

    checked_in_at: Optional[datetime] = Field(
        None,
        description="Check-in timestamp"
    )

    expected_departure: Optional[datetime] = Field(
        None,
        description="Expected departure time"
    )

    actual_departure: Optional[datetime] = Field(
        None,
        description="Actual departure time"
    )

    expected_arrival: Optional[datetime] = Field(
        None,
        description="Expected arrival time"
    )

    actual_arrival: Optional[datetime] = Field(
        None,
        description="Actual arrival time"
    )

    claimed_at: Optional[datetime] = Field(
        None,
        description="When bag was claimed"
    )

    # ========================================================================
    # SCAN HISTORY
    # ========================================================================

    first_scan_at: Optional[datetime] = Field(
        None,
        description="First scan timestamp"
    )

    last_scan_at: Optional[datetime] = Field(
        None,
        description="Most recent scan timestamp"
    )

    last_scan_type: Optional[str] = Field(
        None,
        description="Type of last scan"
    )

    scan_count: int = Field(
        0,
        description="Total number of scans",
        ge=0
    )

    # ========================================================================
    # SEMANTIC METADATA
    # ========================================================================

    canonical_id: UUID = Field(
        default_factory=uuid4,
        description="Unique canonical identifier"
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When canonical record was created"
    )

    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )

    updated_by_agent: Optional[str] = Field(
        None,
        description="Which agent last updated this record"
    )

    data_quality: DataQuality = Field(
        default_factory=DataQuality,
        description="Data quality metadata"
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Semantic tags for search/categorization"
    )

    notes: Optional[str] = Field(
        None,
        description="Free-text notes"
    )

    # ========================================================================
    # EXTERNAL REFERENCES
    # ========================================================================

    external_references: Dict[str, str] = Field(
        default_factory=dict,
        description="References to external system records"
    )

    # Store original data from each source for debugging
    raw_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw data from source systems"
    )

    # ========================================================================
    # VALIDATORS
    # ========================================================================

    @field_validator('bag_sequence', 'total_bags')
    @classmethod
    def validate_bag_count(cls, v, info):
        """Validate bag sequence and total"""
        if info.field_name == 'bag_sequence':
            total = info.data.get('total_bags', 1)
            if v > total:
                raise ValueError(f"bag_sequence ({v}) cannot exceed total_bags ({total})")
        return v

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def is_transfer_bag(self) -> bool:
        """Check if this is a transfer bag"""
        return self.inbound_flight is not None

    def is_international(self) -> bool:
        """Check if this is an international journey"""
        if self.origin.country and self.destination.country:
            return self.origin.country != self.destination.country
        return False

    def is_overdue(self) -> bool:
        """Check if bag is overdue based on expected arrival"""
        if self.expected_arrival and not self.claimed_at:
            return make_aware(datetime.now()) > make_aware(self.expected_arrival)
        return False

    def time_since_last_scan(self) -> Optional[float]:
        """Get minutes since last scan"""
        if self.last_scan_at:
            return (make_aware(datetime.now()) - make_aware(self.last_scan_at)).total_seconds() / 60
        return None

    def get_journey_legs(self) -> List[tuple[AirportCode, AirportCode]]:
        """Get journey as list of (origin, destination) legs"""
        legs = []

        if not self.intermediate_stops:
            # Direct flight
            legs.append((self.origin, self.destination))
        else:
            # Multi-leg journey
            current = self.origin
            for stop in self.intermediate_stops:
                legs.append((current, stop))
                current = stop
            legs.append((current, self.destination))

        return legs

    def update_state(self, new_state: BagState, updated_by: Optional[str] = None):
        """Update bag state with tracking"""
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_updated_at = datetime.now()
        self.updated_at = datetime.now()
        if updated_by:
            self.updated_by_agent = updated_by

    def add_risk_factor(self, factor: str, severity: RiskLevel):
        """Add a risk factor and update risk level"""
        if factor not in self.risk_factors:
            self.risk_factors.append(factor)

        # Update risk level to highest severity
        severity_order = [RiskLevel.NONE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        current_index = severity_order.index(self.risk_level)
        new_index = severity_order.index(severity)

        if new_index > current_index:
            self.risk_level = severity

    def get_summary(self) -> str:
        """Get human-readable summary"""
        return (
            f"Bag {self.bag_tag}: {self.passenger_name} | "
            f"{self.origin} → {self.destination} | "
            f"Flight {self.outbound_flight} | "
            f"State: {self.current_state.value} | "
            f"Risk: {self.risk_level.value}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization"""
        return self.model_dump(mode='json')

    class Config:
        json_schema_extra = {
            "example": {
                "bag_tag": "0291234567",
                "passenger_name": "SMITH/JOHN MR",
                "origin": {"iata_code": "LAX"},
                "destination": {"iata_code": "JFK"},
                "outbound_flight": {
                    "airline_code": "AA",
                    "flight_number": "123"
                },
                "current_state": "IN_SYSTEM",
                "risk_level": "LOW"
            }
        }
