"""
SITA Type B Message Parser

Parses IATA Type B messages (BTM, BSM, BPM).

Type B Message Format (simplified):
BTM
CM101/15NOV PTY MIA
.SMITH/JOHN 0001234567 T2P

BSM
CM101/15NOV PTY
.SMITH/JOHN 0001234567 1PC/25KG
.JONES/JANE 0001234568 1PC/23KG

BPM
0001234567/CM101/15NOV/PTY/BXY
"""
from typing import Union, Dict, Any, List
from datetime import datetime
import re

from app.parsers.base import BaseParser
from app.parsers.models import (
    ParseResult,
    BagEvent,
    EventType,
    TypeBMessageType,
    BagInfo,
    FlightInfo,
    PassengerInfo,
    LocationInfo,
    BagStatus
)


class TypeBParser(BaseParser):
    """Parse SITA Type B messages"""

    def __init__(self):
        super().__init__(parser_name="TypeBParser", parser_version="1.0.0")

    def parse(self, input_data: Union[str, Dict[str, Any]]) -> ParseResult:
        """
        Parse Type B message

        Args:
            input_data: Type B message text

        Returns:
            ParseResult with BagEvent
        """
        if isinstance(input_data, dict):
            # If dict, extract 'message' field
            message_text = input_data.get('message', '')
        else:
            message_text = str(input_data)

        self.log_parse_attempt("Type B message", message_text)

        # Determine message type
        message_type = self._detect_message_type(message_text)
        if not message_type:
            error = "Could not determine Type B message type (BTM/BSM/BPM expected)"
            self.log_parse_failure([error])
            return self.create_error_result(
                errors=[error],
                raw_input=message_text
            )

        # Parse based on type
        if message_type == TypeBMessageType.BTM:
            return self._parse_btm(message_text)
        elif message_type == TypeBMessageType.BSM:
            return self._parse_bsm(message_text)
        elif message_type == TypeBMessageType.BPM:
            return self._parse_bpm(message_text)
        else:
            error = f"Unsupported message type: {message_type}"
            self.log_parse_failure([error])
            return self.create_error_result(
                errors=[error],
                raw_input=message_text
            )

    def _detect_message_type(self, message: str) -> TypeBMessageType:
        """
        Detect Type B message type from header

        Args:
            message: Message text

        Returns:
            TypeBMessageType or None
        """
        message_upper = message.upper().strip()

        if message_upper.startswith('BTM'):
            return TypeBMessageType.BTM
        elif message_upper.startswith('BSM'):
            return TypeBMessageType.BSM
        elif message_upper.startswith('BPM'):
            return TypeBMessageType.BPM
        elif message_upper.startswith('BNS'):
            return TypeBMessageType.BNS
        elif message_upper.startswith('BUM'):
            return TypeBMessageType.BUM

        # Try to infer from bag tag pattern
        if re.search(r'\d{10}', message):
            # Has bag tag - likely BSM or BTM
            if '/' in message and re.search(r'\d+NOV|\d+DEC|\d+JAN', message):
                return TypeBMessageType.BTM
            return TypeBMessageType.BSM

        return None

    def _parse_btm(self, message: str) -> ParseResult:
        """
        Parse BTM (Baggage Transfer Message)

        Format:
        BTM
        CM101/15NOV PTY MIA
        .SMITH/JOHN 0001234567 T2P
        """
        lines = [line.strip() for line in message.strip().split('\n') if line.strip()]

        errors = []
        warnings = []

        # Extract flight line (line 2): CM101/15NOV PTY MIA
        if len(lines) < 2:
            errors.append("BTM missing flight line")
            return self.create_error_result(errors=errors, raw_input=message)

        flight_line = lines[1]
        flight_match = re.search(r'(CM\w+)/(\d+\w+)\s+([A-Z]{3})\s+([A-Z]{3})', flight_line)

        if not flight_match:
            errors.append("Could not parse flight line in BTM")
            return self.create_error_result(errors=errors, raw_input=message)

        flight_number = flight_match.group(1)
        date_str = flight_match.group(2)
        origin = flight_match.group(3)
        destination = flight_match.group(4)

        # Extract passenger/bag line (line 3): .SMITH/JOHN 0001234567 T2P
        bag_tag = None
        passenger_name = None

        for line in lines[2:]:
            if line.startswith('.'):
                # Passenger line
                parts = line[1:].split()
                if len(parts) >= 2:
                    passenger_name = parts[0]  # SMITH/JOHN
                    bag_tag_match = re.search(r'\d{10}', ' '.join(parts[1:]))
                    if bag_tag_match:
                        bag_tag = bag_tag_match.group()
                        break

        if not bag_tag:
            errors.append("Could not extract bag tag from BTM")
            return self.create_error_result(errors=errors, raw_input=message)

        # Build event
        bag = BagInfo(
            bag_tag=bag_tag,
            status=BagStatus.IN_TRANSIT
        )

        flight = FlightInfo(
            flight_number=flight_number,
            airline_code="CM",
            origin=origin,
            destination=destination
        )

        passenger = None
        if passenger_name:
            name_parts = passenger_name.split('/')
            passenger = PassengerInfo(
                name=passenger_name,
                last_name=name_parts[0] if len(name_parts) > 0 else None,
                first_name=name_parts[1] if len(name_parts) > 1 else None
            )

        location = LocationInfo(
            station_code=origin
        )

        event = BagEvent(
            event_type=EventType.TYPE_B,
            message_type=TypeBMessageType.BTM,
            source_system="SITA",
            bag=bag,
            passenger=passenger,
            flight=flight,
            location=location,
            raw_message=message,
            metadata=self.create_metadata(
                confidence_score=0.9,
                raw_input=message
            )
        )

        self.log_parse_success(event.event_id, bag_tag)
        return self.create_success_result(
            event=event,
            confidence_score=0.9,
            warnings=warnings,
            raw_input=message
        )

    def _parse_bsm(self, message: str) -> ParseResult:
        """
        Parse BSM (Baggage Source Message)

        Format:
        BSM
        CM101/15NOV PTY
        .SMITH/JOHN 0001234567 1PC/25KG
        """
        lines = [line.strip() for line in message.strip().split('\n') if line.strip()]

        errors = []

        # Extract flight line
        if len(lines) < 2:
            errors.append("BSM missing flight line")
            return self.create_error_result(errors=errors, raw_input=message)

        flight_line = lines[1]
        flight_match = re.search(r'(CM\w+)/(\d+\w+)\s+([A-Z]{3})', flight_line)

        if not flight_match:
            errors.append("Could not parse flight line in BSM")
            return self.create_error_result(errors=errors, raw_input=message)

        flight_number = flight_match.group(1)
        origin = flight_match.group(3)

        # Extract bag lines
        bag_tag = None
        passenger_name = None
        weight_kg = None

        for line in lines[2:]:
            if line.startswith('.'):
                parts = line[1:].split()
                if len(parts) >= 2:
                    passenger_name = parts[0]
                    bag_tag_match = re.search(r'\d{10}', ' '.join(parts[1:]))
                    if bag_tag_match:
                        bag_tag = bag_tag_match.group()

                    # Extract weight if present (format: 1PC/25KG or 25KG)
                    weight_match = re.search(r'(\d+)KG', ' '.join(parts))
                    if weight_match:
                        weight_kg = float(weight_match.group(1))
                    break

        if not bag_tag:
            errors.append("Could not extract bag tag from BSM")
            return self.create_error_result(errors=errors, raw_input=message)

        # Build event
        bag = BagInfo(
            bag_tag=bag_tag,
            weight_kg=weight_kg,
            status=BagStatus.CHECKED_IN
        )

        flight = FlightInfo(
            flight_number=flight_number,
            airline_code="CM",
            origin=origin,
            destination="UNKNOWN"  # BSM doesn't always have destination
        )

        passenger = None
        if passenger_name:
            name_parts = passenger_name.split('/')
            passenger = PassengerInfo(
                name=passenger_name,
                last_name=name_parts[0] if len(name_parts) > 0 else None,
                first_name=name_parts[1] if len(name_parts) > 1 else None
            )

        location = LocationInfo(
            station_code=origin
        )

        event = BagEvent(
            event_type=EventType.TYPE_B,
            message_type=TypeBMessageType.BSM,
            source_system="SITA",
            bag=bag,
            passenger=passenger,
            flight=flight,
            location=location,
            raw_message=message,
            metadata=self.create_metadata(
                confidence_score=0.85,
                raw_input=message
            )
        )

        self.log_parse_success(event.event_id, bag_tag)
        return self.create_success_result(
            event=event,
            confidence_score=0.85,
            raw_input=message
        )

    def _parse_bpm(self, message: str) -> ParseResult:
        """
        Parse BPM (Baggage Processing Message)

        Format:
        BPM
        0001234567/CM101/15NOV/PTY/BXY
        """
        # Extract bag tag and details from BPM format
        bpm_match = re.search(r'(\d{10})/(CM\w+)/(\d+\w+)/([A-Z]{3})/(\w+)', message)

        if not bpm_match:
            error = "Could not parse BPM format"
            self.log_parse_failure([error])
            return self.create_error_result(
                errors=[error],
                raw_input=message
            )

        bag_tag = bpm_match.group(1)
        flight_number = bpm_match.group(2)
        origin = bpm_match.group(4)
        process_code = bpm_match.group(5)

        bag = BagInfo(
            bag_tag=bag_tag,
            status=BagStatus.IN_TRANSIT
        )

        flight = FlightInfo(
            flight_number=flight_number,
            airline_code="CM",
            origin=origin,
            destination="UNKNOWN"
        )

        location = LocationInfo(
            station_code=origin
        )

        event = BagEvent(
            event_type=EventType.TYPE_B,
            message_type=TypeBMessageType.BPM,
            source_system="SITA",
            bag=bag,
            flight=flight,
            location=location,
            raw_message=message,
            extra_data={"process_code": process_code},
            metadata=self.create_metadata(
                confidence_score=0.9,
                raw_input=message
            )
        )

        self.log_parse_success(event.event_id, bag_tag)
        return self.create_success_result(
            event=event,
            confidence_score=0.9,
            raw_input=message
        )
