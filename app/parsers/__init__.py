"""
Input Parsers Module

Provides parsers for all baggage event input formats.
All parsers convert inputs to canonical BagEvent format.

Available parsers:
- ScanEventParser: DCS/BHS/BRS scan events
- TypeBParser: SITA Type B messages (BTM/BSM/BPM)
- (Future) BaggageXMLParser: BaggageXML manifests
- (Future) WorldTracerParser: WorldTracer PIR updates
"""
from app.parsers.base import BaseParser
from app.parsers.models import (
    BagEvent,
    ParseResult,
    EventType,
    ScanSource,
    TypeBMessageType,
    BagStatus,
    BagInfo,
    FlightInfo,
    PassengerInfo,
    LocationInfo,
    ParsingMetadata
)
from app.parsers.scan_parser import ScanEventParser
from app.parsers.type_b_parser import TypeBParser

__all__ = [
    # Base
    "BaseParser",

    # Models
    "BagEvent",
    "ParseResult",
    "EventType",
    "ScanSource",
    "TypeBMessageType",
    "BagStatus",
    "BagInfo",
    "FlightInfo",
    "PassengerInfo",
    "LocationInfo",
    "ParsingMetadata",

    # Parsers
    "ScanEventParser",
    "TypeBParser",
]
