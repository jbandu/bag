"""
DCS Mapper
==========

Bidirectional mapper between DCS (Departure Control System) format
and Canonical Bag model.

DCS systems provide check-in and passenger booking data.

Version: 1.0.0
Date: 2025-11-13
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from models.canonical_bag import (
    CanonicalBag,
    AirportCode,
    FlightNumber,
    ContactInfo,
    BagDimensions,
    BagState,
    BagType,
    ServiceClass,
    DataSource
)


class DCSMapper:
    """
    Maps between DCS format and Canonical Bag model

    DCS Format (proprietary):
    {
        "bag_tag_number": "0291234567",
        "passenger": {
            "surname": "SMITH",
            "given_name": "JOHN",
            "title": "MR",
            "pnr": "ABC123",
            "ticket": "0011234567890",
            "ffn": "AA1234567",
            "class": "Y",
            "email": "john.smith@example.com",
            "phone": "+1234567890"
        },
        "itinerary": {
            "origin": "LAX",
            "destination": "JFK",
            "connections": ["ORD"],
            "outbound_flight": {"carrier": "AA", "number": "123", "date": "2025-11-13T10:00:00Z"},
            "inbound_flight": {"carrier": "AA", "number": "100", "date": "2025-11-13T08:00:00Z"}
        },
        "baggage": {
            "sequence": 1,
            "total": 2,
            "weight_kg": 23.5,
            "type": "CHECKED",
            "special_tags": ["FRAG"]
        },
        "check_in": {
            "timestamp": "2025-11-13T07:00:00Z",
            "agent": "AGENT001",
            "location": "LAX_T4_CKI_12"
        }
    }
    """

    @staticmethod
    def to_canonical(dcs_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map DCS data to canonical format

        Args:
            dcs_data: DCS format data

        Returns:
            Dict compatible with CanonicalBag
        """
        logger.debug(f"Mapping DCS data to canonical format")

        canonical = {}

        try:
            # Identity
            if 'bag_tag_number' in dcs_data:
                canonical['bag_tag'] = str(dcs_data['bag_tag_number']).zfill(10)

            # Passenger information
            passenger = dcs_data.get('passenger', {})

            if passenger:
                # Build full name in IATA format: SURNAME/GIVENNAME TITLE
                surname = passenger.get('surname', '').upper()
                given_name = passenger.get('given_name', '').upper()
                title = passenger.get('title', '').upper()

                if surname and given_name:
                    canonical['passenger_name'] = f"{surname}/{given_name} {title}".strip()
                    canonical['passenger_last_name'] = surname
                    canonical['passenger_first_name'] = given_name

                # PNR and ticket
                if 'pnr' in passenger:
                    canonical['pnr'] = passenger['pnr']

                if 'ticket' in passenger:
                    canonical['ticket_number'] = passenger['ticket']

                if 'ffn' in passenger:
                    canonical['frequent_flyer_number'] = passenger['ffn']

                # Service class mapping
                service_class_map = {
                    'F': ServiceClass.FIRST,
                    'J': ServiceClass.BUSINESS,
                    'W': ServiceClass.PREMIUM_ECONOMY,
                    'Y': ServiceClass.ECONOMY,
                    'C': ServiceClass.BUSINESS,
                    'M': ServiceClass.ECONOMY
                }

                class_code = passenger.get('class', 'Y')
                canonical['service_class'] = service_class_map.get(
                    class_code,
                    ServiceClass.ECONOMY
                )

                # Contact information
                contact = ContactInfo()

                if 'email' in passenger:
                    contact.email = passenger['email']

                if 'phone' in passenger:
                    contact.phone = passenger['phone']

                if 'mobile' in passenger:
                    contact.mobile = passenger['mobile']

                if 'language' in passenger:
                    contact.preferred_language = passenger['language']

                if any([contact.email, contact.phone, contact.mobile]):
                    canonical['contact'] = contact.model_dump()

                # VIP status
                if passenger.get('vip') or passenger.get('ffn_tier') in ['GOLD', 'PLATINUM', 'DIAMOND']:
                    canonical['is_vip'] = True

            # Itinerary
            itinerary = dcs_data.get('itinerary', {})

            if itinerary:
                # Origin and destination
                if 'origin' in itinerary:
                    canonical['origin'] = {
                        'iata_code': itinerary['origin'].upper()
                    }

                if 'destination' in itinerary:
                    canonical['destination'] = {
                        'iata_code': itinerary['destination'].upper()
                    }

                # Connections
                if 'connections' in itinerary and itinerary['connections']:
                    canonical['intermediate_stops'] = [
                        {'iata_code': stop.upper()}
                        for stop in itinerary['connections']
                    ]

                # Outbound flight
                if 'outbound_flight' in itinerary:
                    flight = itinerary['outbound_flight']
                    canonical['outbound_flight'] = {
                        'airline_code': flight.get('carrier', '').upper(),
                        'flight_number': str(flight.get('number', '')),
                        'departure_date': flight.get('date')
                    }

                    # Flight times
                    if 'scheduled_departure' in flight:
                        canonical['expected_departure'] = flight['scheduled_departure']

                    if 'scheduled_arrival' in flight:
                        canonical['expected_arrival'] = flight['scheduled_arrival']

                # Inbound flight (for transfers)
                if 'inbound_flight' in itinerary and itinerary['inbound_flight']:
                    flight = itinerary['inbound_flight']
                    canonical['inbound_flight'] = {
                        'airline_code': flight.get('carrier', '').upper(),
                        'flight_number': str(flight.get('number', '')),
                        'departure_date': flight.get('date')
                    }

            # Baggage details
            baggage = dcs_data.get('baggage', {})

            if baggage:
                # Bag sequence and count
                if 'sequence' in baggage:
                    canonical['bag_sequence'] = int(baggage['sequence'])

                if 'total' in baggage:
                    canonical['total_bags'] = int(baggage['total'])

                # Bag type
                bag_type_map = {
                    'CHECKED': BagType.CHECKED,
                    'CABIN': BagType.CABIN,
                    'TRANSFER': BagType.TRANSFER,
                    'PRIORITY': BagType.PRIORITY,
                    'HEAVY': BagType.HEAVY,
                    'OVERSIZE': BagType.OVERSIZE
                }

                bag_type_str = baggage.get('type', 'CHECKED').upper()
                canonical['bag_type'] = bag_type_map.get(bag_type_str, BagType.CHECKED)

                # Dimensions
                dimensions = {}

                if 'weight_kg' in baggage:
                    dimensions['weight_kg'] = float(baggage['weight_kg'])

                if 'length_cm' in baggage:
                    dimensions['length_cm'] = int(baggage['length_cm'])

                if 'width_cm' in baggage:
                    dimensions['width_cm'] = int(baggage['width_cm'])

                if 'height_cm' in baggage:
                    dimensions['height_cm'] = int(baggage['height_cm'])

                if dimensions:
                    canonical['dimensions'] = dimensions

                # Special handling codes
                if 'special_tags' in baggage:
                    canonical['special_handling_codes'] = baggage['special_tags']

                # Description
                if 'description' in baggage:
                    canonical['description'] = baggage['description']

            # Check-in information
            check_in = dcs_data.get('check_in', {})

            if check_in:
                if 'timestamp' in check_in:
                    canonical['checked_in_at'] = check_in['timestamp']

                # Set initial state
                canonical['current_state'] = BagState.CHECKED_IN

            # Add source metadata
            canonical['timestamp'] = dcs_data.get('timestamp', datetime.now().isoformat())

            # Add data source reference
            canonical['external_references'] = {
                'dcs_record_id': dcs_data.get('record_id', ''),
                'dcs_station': check_in.get('location', '')
            }

            logger.debug(f"Successfully mapped DCS data for bag {canonical.get('bag_tag')}")

            return canonical

        except Exception as e:
            logger.error(f"Error mapping DCS data to canonical: {e}")
            logger.debug(f"DCS data: {dcs_data}")
            raise

    @staticmethod
    def from_canonical(canonical_bag: CanonicalBag) -> Dict[str, Any]:
        """
        Map canonical bag to DCS format

        Args:
            canonical_bag: CanonicalBag instance

        Returns:
            DCS format dict
        """
        logger.debug(f"Mapping canonical bag {canonical_bag.bag_tag} to DCS format")

        try:
            # Build passenger section
            passenger = {}

            if canonical_bag.passenger_last_name:
                passenger['surname'] = canonical_bag.passenger_last_name

            if canonical_bag.passenger_first_name:
                passenger['given_name'] = canonical_bag.passenger_first_name

            if canonical_bag.pnr:
                passenger['pnr'] = canonical_bag.pnr

            if canonical_bag.ticket_number:
                passenger['ticket'] = canonical_bag.ticket_number

            if canonical_bag.frequent_flyer_number:
                passenger['ffn'] = canonical_bag.frequent_flyer_number

            # Service class mapping (reverse)
            class_map = {
                ServiceClass.FIRST: 'F',
                ServiceClass.BUSINESS: 'J',
                ServiceClass.PREMIUM_ECONOMY: 'W',
                ServiceClass.ECONOMY: 'Y'
            }

            if canonical_bag.service_class:
                passenger['class'] = class_map.get(canonical_bag.service_class, 'Y')

            # Contact info
            if canonical_bag.contact:
                if canonical_bag.contact.email:
                    passenger['email'] = canonical_bag.contact.email
                if canonical_bag.contact.phone:
                    passenger['phone'] = canonical_bag.contact.phone
                if canonical_bag.contact.mobile:
                    passenger['mobile'] = canonical_bag.contact.mobile

            if canonical_bag.is_vip:
                passenger['vip'] = True

            # Build itinerary section
            itinerary = {
                'origin': canonical_bag.origin.iata_code,
                'destination': canonical_bag.destination.iata_code
            }

            if canonical_bag.intermediate_stops:
                itinerary['connections'] = [
                    stop.iata_code for stop in canonical_bag.intermediate_stops
                ]

            # Outbound flight
            itinerary['outbound_flight'] = {
                'carrier': canonical_bag.outbound_flight.airline_code,
                'number': canonical_bag.outbound_flight.flight_number
            }

            if canonical_bag.outbound_flight.departure_date:
                itinerary['outbound_flight']['date'] = canonical_bag.outbound_flight.departure_date.isoformat()

            if canonical_bag.expected_departure:
                itinerary['outbound_flight']['scheduled_departure'] = canonical_bag.expected_departure.isoformat()

            if canonical_bag.expected_arrival:
                itinerary['outbound_flight']['scheduled_arrival'] = canonical_bag.expected_arrival.isoformat()

            # Inbound flight (if transfer)
            if canonical_bag.inbound_flight:
                itinerary['inbound_flight'] = {
                    'carrier': canonical_bag.inbound_flight.airline_code,
                    'number': canonical_bag.inbound_flight.flight_number
                }

                if canonical_bag.inbound_flight.departure_date:
                    itinerary['inbound_flight']['date'] = canonical_bag.inbound_flight.departure_date.isoformat()

            # Build baggage section
            baggage = {
                'sequence': canonical_bag.bag_sequence,
                'total': canonical_bag.total_bags,
                'type': canonical_bag.bag_type.value
            }

            if canonical_bag.dimensions:
                if canonical_bag.dimensions.weight_kg:
                    baggage['weight_kg'] = canonical_bag.dimensions.weight_kg
                if canonical_bag.dimensions.length_cm:
                    baggage['length_cm'] = canonical_bag.dimensions.length_cm
                if canonical_bag.dimensions.width_cm:
                    baggage['width_cm'] = canonical_bag.dimensions.width_cm
                if canonical_bag.dimensions.height_cm:
                    baggage['height_cm'] = canonical_bag.dimensions.height_cm

            if canonical_bag.special_handling_codes:
                baggage['special_tags'] = canonical_bag.special_handling_codes

            if canonical_bag.description:
                baggage['description'] = canonical_bag.description

            # Build check-in section
            check_in = {}

            if canonical_bag.checked_in_at:
                check_in['timestamp'] = canonical_bag.checked_in_at.isoformat()

            # Build complete DCS record
            dcs_data = {
                'bag_tag_number': canonical_bag.bag_tag,
                'passenger': passenger,
                'itinerary': itinerary,
                'baggage': baggage,
                'check_in': check_in,
                'timestamp': canonical_bag.updated_at.isoformat()
            }

            # Add external reference if available
            if 'dcs_record_id' in canonical_bag.external_references:
                dcs_data['record_id'] = canonical_bag.external_references['dcs_record_id']

            logger.debug(f"Successfully mapped canonical bag to DCS format")

            return dcs_data

        except Exception as e:
            logger.error(f"Error mapping canonical bag to DCS format: {e}")
            raise
