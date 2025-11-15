"""
Scan Event Parser

Parses scan events from BRS/BHS/DCS systems.

Input formats supported:
1. JSON from DCS/BHS:
   {
     "bag_tag": "0001234567",
     "flight_number": "CM101",
     "location": "PTY",
     "timestamp": "2024-11-15T10:30:00Z",
     "source": "DCS"
   }

2. Raw scan strings:
   "0001234567 CM101 PTY"
   "TAG:0001234567 FLT:CM101 LOC:PTY TIME:2024-11-15T10:30:00"
"""
from typing import Union, Dict, Any
from datetime import datetime
import re

from app.parsers.base import BaseParser
from app.parsers.models import (
    ParseResult,
    BagEvent,
    EventType,
    ScanSource,
    BagInfo,
    FlightInfo,
    LocationInfo,
    BagStatus
)


class ScanEventParser(BaseParser):
    """Parse scan events from various formats"""

    def __init__(self):
        super().__init__(parser_name="ScanEventParser", parser_version="1.0.0")

    def parse(self, input_data: Union[str, Dict[str, Any]]) -> ParseResult:
        """
        Parse scan event

        Args:
            input_data: JSON dict or raw scan string

        Returns:
            ParseResult with BagEvent
        """
        # Handle dict input (from JSON API)
        if isinstance(input_data, dict):
            return self._parse_json(input_data)

        # Handle string input (raw scan or formatted string)
        elif isinstance(input_data, str):
            return self._parse_string(input_data)

        else:
            return self.create_error_result(
                errors=[f"Unsupported input type: {type(input_data)}"],
                raw_input=str(input_data)
            )

    def _parse_json(self, data: Dict[str, Any]) -> ParseResult:
        """
        Parse JSON scan event

        Expected fields:
        - bag_tag (required)
        - flight_number (optional)
        - location (optional)
        - timestamp (optional)
        - source (optional: BRS/BHS/DCS/MANUAL)
        """
        self.log_parse_attempt("JSON scan event", str(data)[:100])

        errors = []

        # Validate required fields
        if 'bag_tag' not in data or not data['bag_tag']:
            errors.append("Missing required field: bag_tag")

        if errors:
            self.log_parse_failure(errors)
            return self.create_error_result(errors=errors, raw_input=str(data))

        # Extract bag info
        bag_tag = str(data['bag_tag']).replace(" ", "").upper()
        bag = BagInfo(
            bag_tag=bag_tag,
            weight_kg=self.safe_get(data, 'weight_kg'),
            pieces=self.safe_get(data, 'pieces', 1),
            description=self.safe_get(data, 'description'),
            status=BagStatus.IN_TRANSIT
        )

        # Extract flight info (optional)
        flight = None
        if 'flight_number' in data and data['flight_number']:
            flight_num = str(data['flight_number']).upper()
            flight = FlightInfo(
                flight_number=flight_num,
                airline_code=self.safe_get(data, 'airline_code', 'CM'),
                origin=self.safe_get(data, 'origin', 'UNKNOWN'),
                destination=self.safe_get(data, 'destination', 'UNKNOWN')
            )

        # Extract location info (optional)
        location = None
        if 'location' in data and data['location']:
            location = LocationInfo(
                station_code=str(data['location']).upper(),
                terminal=self.safe_get(data, 'terminal'),
                gate=self.safe_get(data, 'gate'),
                carousel=self.safe_get(data, 'carousel'),
                timestamp=self._parse_timestamp(self.safe_get(data, 'timestamp'))
            )

        # Determine source system
        source = self.safe_get(data, 'source', 'MANUAL')
        try:
            scan_source = ScanSource(source.upper())
        except ValueError:
            scan_source = ScanSource.MANUAL

        # Create BagEvent
        event = BagEvent(
            event_type=EventType.SCAN,
            event_timestamp=self._parse_timestamp(self.safe_get(data, 'timestamp')),
            source_system=scan_source.value,
            bag=bag,
            flight=flight,
            location=location,
            raw_message=str(data),
            metadata=self.create_metadata(
                confidence_score=1.0,
                raw_input=str(data)
            )
        )

        self.log_parse_success(event.event_id, bag_tag)
        return self.create_success_result(
            event=event,
            confidence_score=1.0,
            raw_input=str(data)
        )

    def _parse_string(self, raw_scan: str) -> ParseResult:
        """
        Parse raw scan string

        Formats supported:
        1. Simple: "0001234567 CM101 PTY"
        2. Tagged: "TAG:0001234567 FLT:CM101 LOC:PTY"
        3. Verbose: "Bag 0001234567 on flight CM101 scanned at PTY"
        """
        self.log_parse_attempt("raw scan string", raw_scan)

        # Try to extract bag tag (10 digits)
        bag_tag_match = re.search(r'\b(\d{10})\b', raw_scan)
        if not bag_tag_match:
            error = "Could not extract bag tag (expected 10 digits)"
            self.log_parse_failure([error])
            return self.create_error_result(
                errors=[error],
                raw_input=raw_scan
            )

        bag_tag = bag_tag_match.group(1)

        # Try to extract flight number (format: CM101, CMXH203, etc.)
        flight_match = re.search(r'\b(CM[A-Z0-9]{2,6})\b', raw_scan, re.IGNORECASE)
        flight_number = flight_match.group(1).upper() if flight_match else None

        # Try to extract location (3-letter IATA code)
        location_match = re.search(r'\b([A-Z]{3})\b', raw_scan.upper())
        # Avoid matching flight codes as locations
        location_code = None
        if location_match:
            potential_location = location_match.group(1)
            if not potential_location.startswith('CM'):
                location_code = potential_location

        # Create minimal event
        bag = BagInfo(
            bag_tag=bag_tag,
            status=BagStatus.IN_TRANSIT
        )

        flight = None
        if flight_number:
            flight = FlightInfo(
                flight_number=flight_number,
                airline_code="CM",
                origin="UNKNOWN",
                destination="UNKNOWN"
            )

        location = None
        if location_code:
            location = LocationInfo(station_code=location_code)

        # Confidence score depends on how much we extracted
        confidence = 0.6
        if flight_number:
            confidence += 0.2
        if location_code:
            confidence += 0.2

        event = BagEvent(
            event_type=EventType.SCAN,
            source_system=ScanSource.MANUAL.value,
            bag=bag,
            flight=flight,
            location=location,
            raw_message=raw_scan,
            metadata=self.create_metadata(
                confidence_score=confidence,
                raw_input=raw_scan
            )
        )

        warnings = []
        if not flight_number:
            warnings.append("Flight number not found in raw scan")
        if not location_code:
            warnings.append("Location code not found in raw scan")

        self.log_parse_success(event.event_id, bag_tag)
        return self.create_success_result(
            event=event,
            confidence_score=confidence,
            warnings=warnings,
            raw_input=raw_scan
        )

    def _parse_timestamp(self, timestamp_str) -> datetime:
        """
        Parse timestamp string to datetime

        Args:
            timestamp_str: ISO format or other common formats

        Returns:
            datetime object, or current time if parsing fails
        """
        if not timestamp_str:
            return datetime.utcnow()

        if isinstance(timestamp_str, datetime):
            return timestamp_str

        try:
            # Try ISO format
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            # Fall back to current time
            return datetime.utcnow()
