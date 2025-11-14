"""
Event Ontology for Baggage Scan Events
======================================

Defines semantic meaning for all baggage scan events with enrichment,
validation rules, and correlation patterns.

Version: 1.0.0
Date: 2024-11-13
"""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field, validator, conint, confloat


# ============================================================================
# ENUMERATIONS
# ============================================================================

class ScanEventType(str, Enum):
    """All possible scan event types"""
    CHECKIN = "CHECKIN"              # Bag accepted at counter
    SORTATION = "SORTATION"          # Bag in BHS sorting
    LOADING = "LOADING"              # Bag loaded on aircraft
    OFFLOAD = "OFFLOAD"              # Bag offloaded from aircraft
    TRANSFER = "TRANSFER"            # Bag moving to connecting flight
    ARRIVAL = "ARRIVAL"              # Bag arrived at destination
    CLAIM = "CLAIM"                  # Bag at baggage claim
    MANUAL = "MANUAL"                # Manual scan by agent
    EXCEPTION = "EXCEPTION"          # Scan during exception handling
    SECURITY = "SECURITY"            # Security screening
    CUSTOMS = "CUSTOMS"              # Customs inspection
    BTM = "BTM"                      # Baggage Tag Message (IATA)
    BSM = "BSM"                      # Baggage Source Message (IATA)
    BPM = "BPM"                      # Baggage Processing Message (IATA)


class ScanLocation(str, Enum):
    """Location types where scans occur"""
    CHECK_IN_COUNTER = "check_in_counter"
    SELF_SERVICE_KIOSK = "self_service_kiosk"
    BHS_INDUCTION = "bhs_induction"
    BHS_SORTATION = "bhs_sortation"
    BHS_MAKEUP = "bhs_makeup"
    AIRCRAFT_HOLD = "aircraft_hold"
    TRANSFER_AREA = "transfer_area"
    ARRIVAL_HALL = "arrival_hall"
    BAGGAGE_CLAIM = "baggage_claim"
    MANUAL_STATION = "manual_station"
    EXCEPTION_DESK = "exception_desk"
    SECURITY_CHECKPOINT = "security_checkpoint"
    CUSTOMS_AREA = "customs_area"


class ScanAnomaly(str, Enum):
    """Types of scan anomalies"""
    OUT_OF_SEQUENCE = "out_of_sequence"        # Scan not in expected order
    DUPLICATE_SCAN = "duplicate_scan"          # Same scan repeated
    MISSING_EXPECTED = "missing_expected"      # Expected scan didn't happen
    UNEXPECTED_LOCATION = "unexpected_location"  # Scan at wrong location
    TIME_GAP = "time_gap"                      # Too much time since last scan
    WRONG_FLIGHT = "wrong_flight"              # Scanned for wrong flight
    ALREADY_CLAIMED = "already_claimed"        # Bag already claimed


class RiskFactor(str, Enum):
    """Risk factors introduced by events"""
    TIGHT_CONNECTION = "tight_connection"
    WEATHER_DELAY = "weather_delay"
    EQUIPMENT_FAILURE = "equipment_failure"
    MANUAL_HANDLING = "manual_handling"
    SECURITY_HOLD = "security_hold"
    CUSTOMS_DELAY = "customs_delay"
    SCAN_GAP = "scan_gap"
    WRONG_ROUTING = "wrong_routing"
    OVERSIZED = "oversized"
    FRAGILE = "fragile"


# ============================================================================
# SEMANTIC EVENT MODELS
# ============================================================================

class ExpectedNextScan(BaseModel):
    """What scan should happen next"""

    scan_type: ScanEventType = Field(
        ...,
        description="Expected next scan type"
    )

    location_type: ScanLocation = Field(
        ...,
        description="Expected location type"
    )

    time_window_minutes: conint(gt=0) = Field(
        ...,
        description="Expected time window in minutes"
    )

    probability: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Probability this scan will occur (0.0-1.0)"
    )

    alternative_scans: List[ScanEventType] = Field(
        default_factory=list,
        description="Alternative scans that might occur instead"
    )


class SemanticEnrichment(BaseModel):
    """Semantic enrichment for scan events"""

    event_meaning: str = Field(
        ...,
        description="Human-readable meaning of this event"
    )

    journey_stage: Literal[
        "origin_processing",
        "in_transit",
        "connection",
        "destination_processing",
        "completed",
        "exception_handling"
    ] = Field(
        ...,
        description="Stage in the bag's journey"
    )

    expected_next_scans: List[ExpectedNextScan] = Field(
        default_factory=list,
        description="Possible next scans (empty for terminal events)"
    )

    risk_factors: List[RiskFactor] = Field(
        default_factory=list,
        description="Risk factors introduced by this event"
    )

    relevant_agents: List[str] = Field(
        ...,
        min_items=1,
        description="Agents that should be notified"
    )

    required_actions: List[str] = Field(
        default_factory=list,
        description="Actions that should be triggered"
    )

    data_quality_score: confloat(ge=0.0, le=1.0) = Field(
        1.0,
        description="Quality of scan data (0.0-1.0)"
    )


class ScanEventDefinition(BaseModel):
    """Complete definition for a scan event type"""

    event_type: ScanEventType = Field(
        ...,
        description="Type of scan event"
    )

    description: str = Field(
        ...,
        description="Description of what this event means"
    )

    typical_locations: List[ScanLocation] = Field(
        ...,
        min_items=1,
        description="Where this scan typically occurs"
    )

    semantic_enrichment: SemanticEnrichment = Field(
        ...,
        description="Semantic enrichment for this event type"
    )

    sequence_position: conint(ge=1, le=20) = Field(
        ...,
        description="Typical position in scan sequence (1-20)"
    )

    is_optional: bool = Field(
        False,
        description="Is this scan optional in the journey?"
    )

    is_terminal: bool = Field(
        False,
        description="Is this a terminal event (ends journey)?"
    )


# ============================================================================
# EVENT SEQUENCE VALIDATION
# ============================================================================

class SequenceRule(BaseModel):
    """Rule for valid scan sequences"""

    must_follow: Optional[List[ScanEventType]] = Field(
        None,
        description="Scan types that must come before this one"
    )

    cannot_follow: Optional[List[ScanEventType]] = Field(
        None,
        description="Scan types that cannot come before this one"
    )

    must_precede: Optional[List[ScanEventType]] = Field(
        None,
        description="Scan types that must come after this one"
    )

    max_time_since_previous: Optional[conint(gt=0)] = Field(
        None,
        description="Maximum minutes since previous scan"
    )

    min_time_since_previous: Optional[conint(gt=0)] = Field(
        None,
        description="Minimum minutes since previous scan"
    )


class ValidationResult(BaseModel):
    """Result of event sequence validation"""

    is_valid: bool = Field(
        ...,
        description="Is the sequence valid?"
    )

    anomalies: List[ScanAnomaly] = Field(
        default_factory=list,
        description="Detected anomalies"
    )

    missing_scans: List[ScanEventType] = Field(
        default_factory=list,
        description="Expected scans that are missing"
    )

    confidence: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Confidence in validation result (0.0-1.0)"
    )

    reasoning: str = Field(
        ...,
        description="Explanation of validation result"
    )


# ============================================================================
# EVENT CORRELATION
# ============================================================================

class CorrelationPattern(BaseModel):
    """Pattern for correlating related events"""

    pattern_type: Literal[
        "same_flight",
        "same_passenger",
        "same_location",
        "same_time_window",
        "same_exception_type"
    ] = Field(
        ...,
        description="Type of correlation pattern"
    )

    correlation_key: str = Field(
        ...,
        description="Key used for correlation (flight number, PNR, etc.)"
    )

    event_count: conint(ge=1) = Field(
        ...,
        description="Number of correlated events"
    )

    time_window_minutes: conint(gt=0) = Field(
        ...,
        description="Time window for correlation"
    )

    confidence: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Confidence in correlation (0.0-1.0)"
    )


class CorrelatedEventGroup(BaseModel):
    """Group of correlated events"""

    group_id: str = Field(
        ...,
        description="Unique group identifier"
    )

    pattern: CorrelationPattern = Field(
        ...,
        description="Correlation pattern"
    )

    events: List[Dict[str, Any]] = Field(
        ...,
        min_items=2,
        description="List of correlated events"
    )

    aggregate_risk_score: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Aggregate risk score for the group"
    )

    recommended_actions: List[str] = Field(
        default_factory=list,
        description="Actions recommended for this group"
    )


# ============================================================================
# PREDEFINED EVENT DEFINITIONS
# ============================================================================

# Check-In Event
CHECKIN_EVENT = ScanEventDefinition(
    event_type=ScanEventType.CHECKIN,
    description="Bag accepted at check-in counter and tagged",
    typical_locations=[
        ScanLocation.CHECK_IN_COUNTER,
        ScanLocation.SELF_SERVICE_KIOSK
    ],
    semantic_enrichment=SemanticEnrichment(
        event_meaning="Bag entered the baggage handling system",
        journey_stage="origin_processing",
        expected_next_scans=[
            ExpectedNextScan(
                scan_type=ScanEventType.SORTATION,
                location_type=ScanLocation.BHS_SORTATION,
                time_window_minutes=15,
                probability=0.95,
                alternative_scans=[ScanEventType.SECURITY]
            )
        ],
        risk_factors=[],
        relevant_agents=[
            "ScanProcessorAgent",
            "RiskScorerAgent"
        ],
        required_actions=[
            "create_digital_twin",
            "validate_routing",
            "check_special_handling"
        ]
    ),
    sequence_position=1,
    is_optional=False,
    is_terminal=False
)

# Sortation Event
SORTATION_EVENT = ScanEventDefinition(
    event_type=ScanEventType.SORTATION,
    description="Bag being sorted in BHS to correct flight",
    typical_locations=[
        ScanLocation.BHS_SORTATION,
        ScanLocation.BHS_MAKEUP
    ],
    semantic_enrichment=SemanticEnrichment(
        event_meaning="Bag routed to correct flight makeup area",
        journey_stage="origin_processing",
        expected_next_scans=[
            ExpectedNextScan(
                scan_type=ScanEventType.LOADING,
                location_type=ScanLocation.BHS_MAKEUP,
                time_window_minutes=30,
                probability=0.90,
                alternative_scans=[ScanEventType.MANUAL, ScanEventType.EXCEPTION]
            )
        ],
        risk_factors=[RiskFactor.EQUIPMENT_FAILURE],
        relevant_agents=[
            "ScanProcessorAgent",
            "RiskScorerAgent"
        ],
        required_actions=[
            "update_digital_twin",
            "verify_routing",
            "calculate_connection_risk"
        ]
    ),
    sequence_position=2,
    is_optional=False,
    is_terminal=False
)

# Loading Event
LOADING_EVENT = ScanEventDefinition(
    event_type=ScanEventType.LOADING,
    description="Bag loaded onto aircraft",
    typical_locations=[
        ScanLocation.BHS_MAKEUP,
        ScanLocation.AIRCRAFT_HOLD
    ],
    semantic_enrichment=SemanticEnrichment(
        event_meaning="Bag confirmed on aircraft",
        journey_stage="in_transit",
        expected_next_scans=[
            ExpectedNextScan(
                scan_type=ScanEventType.ARRIVAL,
                location_type=ScanLocation.ARRIVAL_HALL,
                time_window_minutes=240,  # Flight time dependent
                probability=0.98,
                alternative_scans=[ScanEventType.TRANSFER, ScanEventType.OFFLOAD]
            )
        ],
        risk_factors=[],
        relevant_agents=[
            "ScanProcessorAgent",
            "PassengerCommsAgent"
        ],
        required_actions=[
            "update_digital_twin",
            "notify_passenger_loaded",
            "clear_low_risk_alerts"
        ]
    ),
    sequence_position=3,
    is_optional=False,
    is_terminal=False
)

# Transfer Event
TRANSFER_EVENT = ScanEventDefinition(
    event_type=ScanEventType.TRANSFER,
    description="Bag being transferred to connecting flight",
    typical_locations=[
        ScanLocation.TRANSFER_AREA,
        ScanLocation.BHS_SORTATION
    ],
    semantic_enrichment=SemanticEnrichment(
        event_meaning="Bag in transfer process for connection",
        journey_stage="connection",
        expected_next_scans=[
            ExpectedNextScan(
                scan_type=ScanEventType.LOADING,
                location_type=ScanLocation.BHS_MAKEUP,
                time_window_minutes=45,  # MCT dependent
                probability=0.85,
                alternative_scans=[ScanEventType.EXCEPTION, ScanEventType.MANUAL]
            )
        ],
        risk_factors=[
            RiskFactor.TIGHT_CONNECTION,
            RiskFactor.SCAN_GAP
        ],
        relevant_agents=[
            "ScanProcessorAgent",
            "RiskScorerAgent",
            "CaseManagerAgent"
        ],
        required_actions=[
            "update_digital_twin",
            "calculate_mct_risk",
            "check_connection_time",
            "alert_if_tight_connection"
        ]
    ),
    sequence_position=5,
    is_optional=True,
    is_terminal=False
)

# Arrival Event
ARRIVAL_EVENT = ScanEventDefinition(
    event_type=ScanEventType.ARRIVAL,
    description="Bag arrived at destination",
    typical_locations=[
        ScanLocation.ARRIVAL_HALL,
        ScanLocation.BHS_SORTATION
    ],
    semantic_enrichment=SemanticEnrichment(
        event_meaning="Bag has reached destination airport",
        journey_stage="destination_processing",
        expected_next_scans=[
            ExpectedNextScan(
                scan_type=ScanEventType.CLAIM,
                location_type=ScanLocation.BAGGAGE_CLAIM,
                time_window_minutes=20,
                probability=0.95,
                alternative_scans=[ScanEventType.CUSTOMS, ScanEventType.EXCEPTION]
            )
        ],
        risk_factors=[],
        relevant_agents=[
            "ScanProcessorAgent",
            "PassengerCommsAgent"
        ],
        required_actions=[
            "update_digital_twin",
            "notify_passenger_arrived",
            "send_carousel_info"
        ]
    ),
    sequence_position=6,
    is_optional=False,
    is_terminal=False
)

# Claim Event
CLAIM_EVENT = ScanEventDefinition(
    event_type=ScanEventType.CLAIM,
    description="Bag at baggage claim carousel",
    typical_locations=[
        ScanLocation.BAGGAGE_CLAIM
    ],
    semantic_enrichment=SemanticEnrichment(
        event_meaning="Bag delivered to baggage claim",
        journey_stage="completed",
        expected_next_scans=[],  # Terminal event
        risk_factors=[],
        relevant_agents=[
            "ScanProcessorAgent",
            "PassengerCommsAgent"
        ],
        required_actions=[
            "update_digital_twin",
            "mark_journey_complete",
            "calculate_delivery_time",
            "close_monitoring"
        ]
    ),
    sequence_position=7,
    is_optional=False,
    is_terminal=True
)

# Manual Event
MANUAL_EVENT = ScanEventDefinition(
    event_type=ScanEventType.MANUAL,
    description="Manual scan by baggage handler or agent",
    typical_locations=[
        ScanLocation.MANUAL_STATION,
        ScanLocation.EXCEPTION_DESK
    ],
    semantic_enrichment=SemanticEnrichment(
        event_meaning="Bag manually processed by agent",
        journey_stage="exception_handling",
        expected_next_scans=[
            ExpectedNextScan(
                scan_type=ScanEventType.LOADING,
                location_type=ScanLocation.BHS_MAKEUP,
                time_window_minutes=60,
                probability=0.70,
                alternative_scans=[
                    ScanEventType.EXCEPTION,
                    ScanEventType.SORTATION
                ]
            )
        ],
        risk_factors=[
            RiskFactor.MANUAL_HANDLING,
            RiskFactor.SCAN_GAP
        ],
        relevant_agents=[
            "ScanProcessorAgent",
            "RiskScorerAgent",
            "CaseManagerAgent"
        ],
        required_actions=[
            "update_digital_twin",
            "increase_risk_score",
            "create_exception_case",
            "notify_supervisor"
        ]
    ),
    sequence_position=10,
    is_optional=True,
    is_terminal=False
)

# Exception Event
EXCEPTION_EVENT = ScanEventDefinition(
    event_type=ScanEventType.EXCEPTION,
    description="Scan during exception handling (delayed, lost, etc.)",
    typical_locations=[
        ScanLocation.EXCEPTION_DESK,
        ScanLocation.MANUAL_STATION
    ],
    semantic_enrichment=SemanticEnrichment(
        event_meaning="Bag in exception handling workflow",
        journey_stage="exception_handling",
        expected_next_scans=[
            ExpectedNextScan(
                scan_type=ScanEventType.MANUAL,
                location_type=ScanLocation.MANUAL_STATION,
                time_window_minutes=120,
                probability=0.60,
                alternative_scans=[
                    ScanEventType.LOADING,
                    ScanEventType.CLAIM
                ]
            )
        ],
        risk_factors=[
            RiskFactor.MANUAL_HANDLING,
            RiskFactor.SCAN_GAP,
            RiskFactor.WRONG_ROUTING
        ],
        relevant_agents=[
            "ScanProcessorAgent",
            "RiskScorerAgent",
            "CaseManagerAgent",
            "WorldTracerAgent",
            "PassengerCommsAgent"
        ],
        required_actions=[
            "update_digital_twin",
            "create_exception_case",
            "file_pir_if_needed",
            "notify_passenger",
            "alert_supervisor",
            "track_recovery"
        ]
    ),
    sequence_position=15,
    is_optional=True,
    is_terminal=False
)

# Security Event
SECURITY_EVENT = ScanEventDefinition(
    event_type=ScanEventType.SECURITY,
    description="Security screening scan",
    typical_locations=[
        ScanLocation.SECURITY_CHECKPOINT
    ],
    semantic_enrichment=SemanticEnrichment(
        event_meaning="Bag undergoing security screening",
        journey_stage="origin_processing",
        expected_next_scans=[
            ExpectedNextScan(
                scan_type=ScanEventType.SORTATION,
                location_type=ScanLocation.BHS_SORTATION,
                time_window_minutes=10,
                probability=0.90,
                alternative_scans=[ScanEventType.EXCEPTION]
            )
        ],
        risk_factors=[RiskFactor.SECURITY_HOLD],
        relevant_agents=[
            "ScanProcessorAgent",
            "RiskScorerAgent"
        ],
        required_actions=[
            "update_digital_twin",
            "monitor_security_clearance_time"
        ]
    ),
    sequence_position=2,
    is_optional=True,
    is_terminal=False
)

# Customs Event
CUSTOMS_EVENT = ScanEventDefinition(
    event_type=ScanEventType.CUSTOMS,
    description="Customs inspection scan",
    typical_locations=[
        ScanLocation.CUSTOMS_AREA
    ],
    semantic_enrichment=SemanticEnrichment(
        event_meaning="Bag undergoing customs inspection",
        journey_stage="destination_processing",
        expected_next_scans=[
            ExpectedNextScan(
                scan_type=ScanEventType.CLAIM,
                location_type=ScanLocation.BAGGAGE_CLAIM,
                time_window_minutes=15,
                probability=0.85,
                alternative_scans=[ScanEventType.EXCEPTION]
            )
        ],
        risk_factors=[RiskFactor.CUSTOMS_DELAY],
        relevant_agents=[
            "ScanProcessorAgent",
            "RiskScorerAgent"
        ],
        required_actions=[
            "update_digital_twin",
            "monitor_customs_clearance_time"
        ]
    ),
    sequence_position=6,
    is_optional=True,
    is_terminal=False
)


# ============================================================================
# EVENT ONTOLOGY REGISTRY
# ============================================================================

EVENT_ONTOLOGY: Dict[ScanEventType, ScanEventDefinition] = {
    ScanEventType.CHECKIN: CHECKIN_EVENT,
    ScanEventType.SORTATION: SORTATION_EVENT,
    ScanEventType.LOADING: LOADING_EVENT,
    ScanEventType.TRANSFER: TRANSFER_EVENT,
    ScanEventType.ARRIVAL: ARRIVAL_EVENT,
    ScanEventType.CLAIM: CLAIM_EVENT,
    ScanEventType.MANUAL: MANUAL_EVENT,
    ScanEventType.EXCEPTION: EXCEPTION_EVENT,
    ScanEventType.SECURITY: SECURITY_EVENT,
    ScanEventType.CUSTOMS: CUSTOMS_EVENT,
}


# ============================================================================
# SEQUENCE VALIDATION RULES
# ============================================================================

SEQUENCE_RULES: Dict[ScanEventType, SequenceRule] = {
    ScanEventType.CHECKIN: SequenceRule(
        must_follow=None,  # First event
        cannot_follow=[ScanEventType.CLAIM],
        must_precede=[ScanEventType.SORTATION, ScanEventType.SECURITY],
        max_time_since_previous=None,
        min_time_since_previous=None
    ),
    ScanEventType.SORTATION: SequenceRule(
        must_follow=[ScanEventType.CHECKIN, ScanEventType.SECURITY],
        cannot_follow=[ScanEventType.CLAIM, ScanEventType.ARRIVAL],
        must_precede=[ScanEventType.LOADING],
        max_time_since_previous=30,
        min_time_since_previous=1
    ),
    ScanEventType.LOADING: SequenceRule(
        must_follow=[ScanEventType.SORTATION],
        cannot_follow=[ScanEventType.CLAIM],
        must_precede=[ScanEventType.ARRIVAL, ScanEventType.TRANSFER],
        max_time_since_previous=60,
        min_time_since_previous=5
    ),
    ScanEventType.TRANSFER: SequenceRule(
        must_follow=[ScanEventType.ARRIVAL, ScanEventType.OFFLOAD],
        cannot_follow=[ScanEventType.CHECKIN, ScanEventType.CLAIM],
        must_precede=[ScanEventType.LOADING],
        max_time_since_previous=90,
        min_time_since_previous=10
    ),
    ScanEventType.ARRIVAL: SequenceRule(
        must_follow=[ScanEventType.LOADING],
        cannot_follow=[ScanEventType.CHECKIN, ScanEventType.SORTATION],
        must_precede=[ScanEventType.CLAIM, ScanEventType.CUSTOMS],
        max_time_since_previous=600,  # Max flight time ~10 hours
        min_time_since_previous=30
    ),
    ScanEventType.CLAIM: SequenceRule(
        must_follow=[ScanEventType.ARRIVAL],
        cannot_follow=[ScanEventType.CHECKIN, ScanEventType.LOADING],
        must_precede=None,  # Terminal event
        max_time_since_previous=60,
        min_time_since_previous=5
    ),
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_event_definition(event_type: ScanEventType) -> Optional[ScanEventDefinition]:
    """Get event definition for a scan type"""
    return EVENT_ONTOLOGY.get(event_type)


def get_sequence_rule(event_type: ScanEventType) -> Optional[SequenceRule]:
    """Get sequence validation rule for a scan type"""
    return SEQUENCE_RULES.get(event_type)


def get_expected_next_scans(current_event: ScanEventType) -> List[ExpectedNextScan]:
    """Get expected next scans for current event"""
    definition = get_event_definition(current_event)
    if definition:
        return definition.semantic_enrichment.expected_next_scans
    return []
