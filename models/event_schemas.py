"""
Event Schema Definitions
=========================

Pydantic models for baggage tracking events.

Event Types:
- BagScanEvent: RFID/barcode scan events
- BagLoadEvent: Bag loaded onto aircraft/vehicle
- BagTransferEvent: Bag transfer between locations
- BagClaimEvent: Bag claimed by passenger
- BagAnomalyEvent: Anomalies detected (damage, tamper, etc.)

Version: 1.0.0
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


class ScanType(str, Enum):
    """Scan event types"""
    CHECK_IN = "check_in"
    SORTATION = "sortation"
    LOAD = "load"
    ARRIVAL = "arrival"
    TRANSFER = "transfer"
    CLAIM = "claim"
    MANUAL = "manual"
    RFID = "rfid"
    BARCODE = "barcode"


class LoadStatus(str, Enum):
    """Load event statuses"""
    LOADED = "loaded"
    OFFLOADED = "offloaded"
    REJECTED = "rejected"


class AnomalyType(str, Enum):
    """Anomaly types"""
    DAMAGE = "damage"
    TAMPER = "tamper"
    OVERSIZED = "oversized"
    OVERWEIGHT = "overweight"
    MISSING_TAG = "missing_tag"
    DUPLICATE_TAG = "duplicate_tag"
    SECURITY_HOLD = "security_hold"


class BaseEvent(BaseModel):
    """Base event model with common fields"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    bag_id: str = Field(..., description="Bag tag (10-digit IATA format)")
    location: str = Field(..., description="Airport/terminal/checkpoint code")
    device_id: Optional[str] = Field(None, description="Scanner/sensor device ID")
    handler_id: Optional[str] = Field(None, description="Handler/agent ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BagScanEvent(BaseEvent):
    """
    Bag scan event from RFID reader, barcode scanner, or manual entry

    Example:
        {
            "event_id": "uuid-here",
            "timestamp": "2025-11-16T10:30:00Z",
            "bag_id": "0001234567",
            "location": "PTY_CHECKIN_12",
            "device_id": "RFID_READER_001",
            "handler_id": "AGT_123",
            "scan_type": "check_in",
            "signal_strength": 85,
            "read_count": 1
        }
    """
    scan_type: ScanType = Field(..., description="Type of scan")
    signal_strength: Optional[int] = Field(None, ge=0, le=100, description="Signal strength (0-100)")
    read_count: Optional[int] = Field(1, description="Number of reads (for deduplication)")
    raw_data: Optional[str] = Field(None, description="Raw scan data")

    @validator('bag_id')
    def validate_bag_id(cls, v):
        """Validate bag ID format (10 digits)"""
        if not v.isdigit() or len(v) != 10:
            raise ValueError('Bag ID must be exactly 10 digits')
        return v


class BagLoadEvent(BaseEvent):
    """
    Bag loaded onto aircraft, truck, or cart

    Example:
        {
            "event_id": "uuid-here",
            "timestamp": "2025-11-16T11:30:00Z",
            "bag_id": "0001234567",
            "location": "PTY_GATE_A12",
            "device_id": "LOAD_SCANNER_005",
            "handler_id": "LOADER_456",
            "flight_number": "CM123",
            "container_id": "AKE12345",
            "load_status": "loaded",
            "position_in_container": 23
        }
    """
    flight_number: str = Field(..., description="Flight number (e.g., CM123)")
    container_id: Optional[str] = Field(None, description="ULD/container ID")
    load_status: LoadStatus = Field(..., description="Load status")
    position_in_container: Optional[int] = Field(None, description="Position in container")
    weight_kg: Optional[float] = Field(None, description="Bag weight in kg")


class BagTransferEvent(BaseEvent):
    """
    Bag transfer between locations/handlers

    Example:
        {
            "event_id": "uuid-here",
            "timestamp": "2025-11-16T12:00:00Z",
            "bag_id": "0001234567",
            "location": "MIA_TRANSFER_HUB",
            "from_location": "MIA_ARRIVAL_BELT_3",
            "to_location": "MIA_SORTATION_5",
            "from_handler": "AGT_789",
            "to_handler": "AGT_101",
            "transfer_type": "interline"
        }
    """
    from_location: str = Field(..., description="Source location")
    to_location: str = Field(..., description="Destination location")
    from_handler: Optional[str] = Field(None, description="Source handler")
    to_handler: Optional[str] = Field(None, description="Destination handler")
    transfer_type: Optional[str] = Field(None, description="Transfer type (interline, domestic, etc.)")


class BagClaimEvent(BaseEvent):
    """
    Bag claimed by passenger at carousel

    Example:
        {
            "event_id": "uuid-here",
            "timestamp": "2025-11-16T15:00:00Z",
            "bag_id": "0001234567",
            "location": "JFK_CAROUSEL_7",
            "passenger_id": "ABC123",
            "claim_time_seconds": 1200,
            "verified": true
        }
    """
    passenger_id: str = Field(..., description="Passenger PNR or ID")
    claim_time_seconds: Optional[int] = Field(None, description="Time to claim (seconds since arrival)")
    verified: bool = Field(False, description="Verified by agent or self-service")
    carousel_number: Optional[str] = Field(None, description="Carousel number")


class BagAnomalyEvent(BaseEvent):
    """
    Anomaly detected during bag handling

    Example:
        {
            "event_id": "uuid-here",
            "timestamp": "2025-11-16T11:45:00Z",
            "bag_id": "0001234567",
            "location": "PTY_SECURITY_SCAN",
            "anomaly_type": "security_hold",
            "severity": "high",
            "description": "Security screening required",
            "action_required": true,
            "assigned_to": "SECURITY_TEAM"
        }
    """
    anomaly_type: AnomalyType = Field(..., description="Type of anomaly")
    severity: str = Field(..., description="Severity (low, medium, high, critical)")
    description: str = Field(..., description="Anomaly description")
    action_required: bool = Field(False, description="Requires manual intervention")
    assigned_to: Optional[str] = Field(None, description="Assigned agent/team")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")

    @validator('severity')
    def validate_severity(cls, v):
        """Validate severity level"""
        if v not in ['low', 'medium', 'high', 'critical']:
            raise ValueError('Severity must be low, medium, high, or critical')
        return v


class EventBatch(BaseModel):
    """
    Batch of events for bulk ingestion

    Example:
        {
            "batch_id": "uuid-here",
            "events": [event1, event2, ...],
            "source_system": "BHS_SYSTEM_1",
            "total_events": 100
        }
    """
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    events: List[Dict[str, Any]] = Field(..., description="List of events")
    source_system: str = Field(..., description="Source system identifier")
    total_events: int = Field(..., description="Total events in batch")
    ingestion_timestamp: datetime = Field(default_factory=datetime.now)

    @validator('total_events')
    def validate_total_events(cls, v, values):
        """Ensure total_events matches actual count"""
        if 'events' in values and len(values['events']) != v:
            raise ValueError(f'total_events ({v}) does not match events length ({len(values["events"])})')
        return v


class EventProcessingResult(BaseModel):
    """Result of event processing"""
    event_id: str
    success: bool
    error: Optional[str] = None
    processing_time_ms: float
    written_to_postgres: bool = False
    written_to_neo4j: bool = False
    notifications_sent: int = 0


class BatchProcessingResult(BaseModel):
    """Result of batch processing"""
    batch_id: str
    total_events: int
    successful: int
    failed: int
    results: List[EventProcessingResult]
    total_processing_time_ms: float
