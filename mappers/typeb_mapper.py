"""
Type B Message Mapper
=====================

Bidirectional mapper between SITA Type B message format
and Canonical Bag model.

Type B messages are legacy IATA standard messages for baggage:
- BTM (Baggage Transfer Message)
- BSM (Baggage Source Message)
- BPM (Baggage Processing Message)

Version: 1.0.0
Date: 2025-11-13
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import re

from models.canonical_bag import (
    CanonicalBag,
    AirportCode,
    FlightNumber,
    BagState,
    DataSource
)


class TypeBMapper:
    """
    Maps between SITA Type B message format and Canonical Bag model

    Type B Message Format (text-based):

    BSM (Baggage Source Message):
    ```
    BSM
    AA123/13.LAXJFK
    .V0291234567/T1
    .N1/2
    .P0291234567/SMITH/JOHN MR
    .D23K
    ```

    BTM (Baggage Transfer Message):
    ```
    BTM
    AA100/13.ORDJFK/AA123
    .V0291234567/T1
    .N1/2
    .P0291234567/SMITH/JOHN MR
    .D23K
    ```

    Fields:
    - AA123/13 = Flight/Date
    - LAXJFK = Origin/Destination
    - .V = Bag tag (V for validation)
    - /T1 = Transfer indicator
    - .N = Bag number (sequence/total)
    - .P = Passenger name
    - .D = Weight in kg
    """

    @staticmethod
    def parse_type_b(message: str) -> Dict[str, Any]:
        """
        Parse Type B message text into structured data

        Args:
            message: Type B message text

        Returns:
            Parsed message dict
        """
        lines = [line.strip() for line in message.split('\n') if line.strip()]

        if not lines:
            raise ValueError("Empty Type B message")

        # First line is message type
        message_type = lines[0].upper()

        if message_type not in ['BSM', 'BTM', 'BPM']:
            raise ValueError(f"Unknown Type B message type: {message_type}")

        parsed = {
            'message_type': message_type,
            'fields': {}
        }

        # Second line is typically flight info
        if len(lines) > 1:
            flight_line = lines[1]

            # Parse flight info: AA123/13.LAXJFK or AA100/13.ORDJFK/AA123
            flight_match = re.match(r'([A-Z0-9]{2,3})(\d{1,4})/(\d{1,2})\.([A-Z]{3})([A-Z]{3})(?:/([A-Z0-9]{2,3})(\d{1,4}))?', flight_line)

            if flight_match:
                parsed['flight'] = {
                    'airline': flight_match.group(1),
                    'number': flight_match.group(2),
                    'date': flight_match.group(3),
                    'origin': flight_match.group(4),
                    'destination': flight_match.group(5)
                }

                # BTM has connecting flight
                if flight_match.group(6):
                    parsed['connecting_flight'] = {
                        'airline': flight_match.group(6),
                        'number': flight_match.group(7)
                    }

        # Parse remaining lines (fields start with .)
        for line in lines[2:]:
            if line.startswith('.'):
                TypeBMapper._parse_field(line, parsed['fields'])

        return parsed

    @staticmethod
    def _parse_field(line: str, fields: Dict[str, Any]):
        """Parse a field line from Type B message"""

        # .V = Bag tag
        if line.startswith('.V'):
            # .V0291234567/T1 or .V0291234567
            match = re.match(r'\.V(\d{10})(?:/([A-Z]\d))?', line)
            if match:
                fields['bag_tag'] = match.group(1)
                if match.group(2):
                    fields['transfer_indicator'] = match.group(2)

        # .N = Bag number (sequence/total)
        elif line.startswith('.N'):
            # .N1/2 or .N001/002
            match = re.match(r'\.N(\d{1,3})/(\d{1,3})', line)
            if match:
                fields['bag_sequence'] = int(match.group(1))
                fields['total_bags'] = int(match.group(2))

        # .P = Passenger name and bag tag
        elif line.startswith('.P'):
            # .P0291234567/SMITH/JOHN MR
            match = re.match(r'\.P(\d{10})/([A-Z]+)/([A-Z\s]+)', line)
            if match:
                fields['passenger_bag_tag'] = match.group(1)
                fields['passenger_surname'] = match.group(2)
                fields['passenger_given_name'] = match.group(3).strip()

        # .D = Weight
        elif line.startswith('.D'):
            # .D23K (23 kg)
            match = re.match(r'\.D(\d+)([KLP])?', line)
            if match:
                weight = int(match.group(1))
                unit = match.group(2) or 'K'  # K=kg, L=lbs, P=pounds

                # Convert to kg
                if unit == 'L' or unit == 'P':
                    weight = weight * 0.453592  # lbs to kg

                fields['weight_kg'] = weight

        # .W = Onward routing
        elif line.startswith('.W'):
            # .WSFOORD
            match = re.match(r'\.W([A-Z]{3}([A-Z]{3})*)', line)
            if match:
                routing = match.group(1)
                # Split into 3-letter airport codes
                stops = [routing[i:i+3] for i in range(0, len(routing), 3)]
                fields['onward_routing'] = stops

        # .S = Security status
        elif line.startswith('.S'):
            fields['security_status'] = line[2:].strip()

    @staticmethod
    def to_canonical(typeb_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Type B message data to canonical format

        Args:
            typeb_data: Parsed Type B message

        Returns:
            Dict compatible with CanonicalBag
        """
        logger.debug(f"Mapping Type B data to canonical format")

        canonical = {}
        fields = typeb_data.get('fields', {})

        try:
            # Identity
            if 'bag_tag' in fields:
                canonical['bag_tag'] = fields['bag_tag']

            # Flight information
            flight = typeb_data.get('flight', {})

            if flight:
                # Origin and destination
                if 'origin' in flight:
                    canonical['origin'] = {'iata_code': flight['origin']}

                if 'destination' in flight:
                    canonical['destination'] = {'iata_code': flight['destination']}

                # Outbound flight
                if 'airline' in flight and 'number' in flight:
                    canonical['outbound_flight'] = {
                        'airline_code': flight['airline'],
                        'flight_number': flight['number']
                    }

            # Connecting flight (for BTM messages)
            connecting = typeb_data.get('connecting_flight', {})

            if connecting:
                # Inbound flight
                if 'airline' in connecting and 'number' in connecting:
                    canonical['inbound_flight'] = {
                        'airline_code': connecting['airline'],
                        'flight_number': connecting['number']
                    }

            # Passenger information
            if 'passenger_surname' in fields and 'passenger_given_name' in fields:
                surname = fields['passenger_surname']
                given_name = fields['passenger_given_name']
                canonical['passenger_name'] = f"{surname}/{given_name}"
                canonical['passenger_last_name'] = surname
                canonical['passenger_first_name'] = given_name

            # Bag sequence
            if 'bag_sequence' in fields:
                canonical['bag_sequence'] = fields['bag_sequence']

            if 'total_bags' in fields:
                canonical['total_bags'] = fields['total_bags']

            # Weight
            if 'weight_kg' in fields:
                canonical['dimensions'] = {
                    'weight_kg': fields['weight_kg']
                }

            # Onward routing (intermediate stops)
            if 'onward_routing' in fields:
                canonical['intermediate_stops'] = [
                    {'iata_code': stop}
                    for stop in fields['onward_routing']
                ]

            # Transfer indicator
            if 'transfer_indicator' in fields:
                canonical['bag_type'] = 'TRANSFER'

            # Message type determines state
            message_type = typeb_data.get('message_type', '')

            if message_type == 'BSM':
                # Bag source message - bag leaving origin
                canonical['current_state'] = BagState.IN_SYSTEM
            elif message_type == 'BTM':
                # Bag transfer message - bag in transfer
                canonical['current_state'] = BagState.IN_TRANSFER
            elif message_type == 'BPM':
                # Bag processed message
                canonical['current_state'] = BagState.SORTED

            # Add timestamp
            canonical['timestamp'] = datetime.now().isoformat()

            # Add data source reference
            canonical['external_references'] = {
                'typeb_message_type': message_type
            }

            logger.debug(f"Successfully mapped Type B data for bag {canonical.get('bag_tag')}")

            return canonical

        except Exception as e:
            logger.error(f"Error mapping Type B data to canonical: {e}")
            logger.debug(f"Type B data: {typeb_data}")
            raise

    @staticmethod
    def from_canonical(canonical_bag: CanonicalBag, message_type: str = 'BSM') -> str:
        """
        Map canonical bag to Type B message format

        Args:
            canonical_bag: CanonicalBag instance
            message_type: Type B message type (BSM, BTM, BPM)

        Returns:
            Type B message text
        """
        logger.debug(f"Mapping canonical bag {canonical_bag.bag_tag} to Type B format")

        try:
            lines = []

            # Line 1: Message type
            lines.append(message_type.upper())

            # Line 2: Flight info
            # Format: AA123/13.LAXJFK or AA100/13.ORDJFK/AA123 (for BTM)

            flight_line = f"{canonical_bag.outbound_flight.airline_code}{canonical_bag.outbound_flight.flight_number}"

            # Add date (day of month)
            if canonical_bag.outbound_flight.departure_date:
                day = canonical_bag.outbound_flight.departure_date.day
                flight_line += f"/{day:02d}"
            else:
                flight_line += f"/{datetime.now().day:02d}"

            # Add origin/destination
            flight_line += f".{canonical_bag.origin.iata_code}{canonical_bag.destination.iata_code}"

            # For BTM, add connecting flight
            if message_type == 'BTM' and canonical_bag.inbound_flight:
                flight_line += f"/{canonical_bag.inbound_flight.airline_code}{canonical_bag.inbound_flight.flight_number}"

            lines.append(flight_line)

            # Line 3: Bag tag (.V field)
            bag_tag_line = f".V{canonical_bag.bag_tag}"

            # Add transfer indicator if applicable
            if canonical_bag.is_transfer_bag():
                bag_tag_line += "/T1"

            lines.append(bag_tag_line)

            # Line 4: Bag number (.N field)
            lines.append(f".N{canonical_bag.bag_sequence}/{canonical_bag.total_bags}")

            # Line 5: Passenger info (.P field)
            if canonical_bag.passenger_last_name and canonical_bag.passenger_first_name:
                lines.append(
                    f".P{canonical_bag.bag_tag}/{canonical_bag.passenger_last_name}/{canonical_bag.passenger_first_name}"
                )

            # Line 6: Weight (.D field)
            if canonical_bag.dimensions and canonical_bag.dimensions.weight_kg:
                weight_kg = int(canonical_bag.dimensions.weight_kg)
                lines.append(f".D{weight_kg}K")

            # Line 7: Onward routing (.W field) if intermediate stops
            if canonical_bag.intermediate_stops:
                routing = ''.join(stop.iata_code for stop in canonical_bag.intermediate_stops)
                lines.append(f".W{routing}")

            # Join lines with newline
            message = '\n'.join(lines)

            logger.debug(f"Successfully mapped canonical bag to Type B format")

            return message

        except Exception as e:
            logger.error(f"Error mapping canonical bag to Type B format: {e}")
            raise


    @staticmethod
    def parse_from_text(message_text: str) -> Dict[str, Any]:
        """
        Parse Type B message text and convert to canonical format

        Args:
            message_text: Type B message text

        Returns:
            Canonical format dict
        """
        parsed = TypeBMapper.parse_type_b(message_text)
        return TypeBMapper.to_canonical(parsed)
