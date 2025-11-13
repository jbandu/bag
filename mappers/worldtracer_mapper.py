"""
WorldTracer Mapper
==================

Bidirectional mapper between IATA WorldTracer (PIR) format
and Canonical Bag model.

WorldTracer handles mishandled baggage (delayed, damaged, lost).

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
    ExceptionCase,
    ExceptionType,
    BagState,
    RiskLevel,
    DataSource
)


class WorldTracerMapper:
    """
    Maps between WorldTracer PIR (Property Irregularity Report) format
    and Canonical Bag model

    WorldTracer PIR Format (IATA standard):
    {
        "ohd_reference": "LAXAA12345",
        "pir_type": "DELAYED",
        "bag_tag": "0291234567",
        "passenger": {
            "surname": "SMITH",
            "first_name": "JOHN",
            "pnr": "ABC123",
            "contact_phone": "+1234567890",
            "contact_email": "john.smith@example.com",
            "delivery_address": "123 Main St, New York, NY 10001"
        },
        "itinerary": {
            "origin": "LAX",
            "destination": "JFK",
            "flight": "AA123"
        },
        "bag_description": {
            "type": "SUITCASE",
            "color": "BLACK",
            "brand": "SAMSONITE",
            "material": "HARDSIDE",
            "special_characteristics": ["WHEELS", "TSA_LOCK"]
        },
        "irregularity": {
            "type": "DELAYED",
            "station": "LAX",
            "date_time": "2025-11-13T10:00:00Z",
            "last_seen_location": "LAX",
            "remarks": "Bag did not make connecting flight"
        },
        "current_status": {
            "status": "TRACING",
            "located": false,
            "current_location": null,
            "forwarding_details": null
        },
        "created_at": "2025-11-13T11:00:00Z",
        "created_by": "AGENT123",
        "updated_at": "2025-11-13T12:00:00Z"
    }
    """

    # Map WorldTracer irregularity types to canonical exception types
    PIR_TYPE_TO_EXCEPTION = {
        'DELAYED': ExceptionType.DELAYED,
        'MISHANDLED': ExceptionType.MISHANDLED,
        'DAMAGED': ExceptionType.DAMAGED,
        'PILFERED': ExceptionType.PILFERED,
        'LOST': ExceptionType.LOST,
        'MISROUTED': ExceptionType.MISROUTED,
        'OFFLOADED': ExceptionType.OFFLOADED,
        'SHORT_SHIPPED': ExceptionType.SHORT_SHIPPED
    }

    @staticmethod
    def to_canonical(wt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map WorldTracer PIR data to canonical format

        Args:
            wt_data: WorldTracer PIR format data

        Returns:
            Dict compatible with CanonicalBag
        """
        logger.debug(f"Mapping WorldTracer data to canonical format")

        canonical = {}

        try:
            # Identity
            if 'bag_tag' in wt_data:
                canonical['bag_tag'] = str(wt_data['bag_tag']).zfill(10)

            # Passenger information
            passenger = wt_data.get('passenger', {})

            if passenger:
                # Build full name
                surname = passenger.get('surname', '').upper()
                first_name = passenger.get('first_name', '').upper()

                if surname and first_name:
                    canonical['passenger_name'] = f"{surname}/{first_name}"
                    canonical['passenger_last_name'] = surname
                    canonical['passenger_first_name'] = first_name

                # PNR
                if 'pnr' in passenger:
                    canonical['pnr'] = passenger['pnr']

                # Contact information
                contact = {}

                if 'contact_email' in passenger:
                    contact['email'] = passenger['contact_email']

                if 'contact_phone' in passenger:
                    contact['phone'] = passenger['contact_phone']

                if 'contact_mobile' in passenger:
                    contact['mobile'] = passenger['contact_mobile']

                if 'delivery_address' in passenger:
                    contact['address'] = passenger['delivery_address']

                if 'preferred_language' in passenger:
                    contact['preferred_language'] = passenger['preferred_language']

                if contact:
                    canonical['contact'] = contact

            # Itinerary
            itinerary = wt_data.get('itinerary', {})

            if itinerary:
                if 'origin' in itinerary:
                    canonical['origin'] = {'iata_code': itinerary['origin'].upper()}

                if 'destination' in itinerary:
                    canonical['destination'] = {'iata_code': itinerary['destination'].upper()}

                # Parse flight
                if 'flight' in itinerary:
                    flight_str = itinerary['flight']
                    airline_code = ''
                    flight_number = ''

                    for i, char in enumerate(flight_str):
                        if char.isdigit():
                            airline_code = flight_str[:i]
                            flight_number = flight_str[i:]
                            break

                    if airline_code and flight_number:
                        canonical['outbound_flight'] = {
                            'airline_code': airline_code,
                            'flight_number': flight_number
                        }

            # Bag description
            bag_desc = wt_data.get('bag_description', {})

            if bag_desc:
                # Build description string
                desc_parts = []

                if 'color' in bag_desc:
                    desc_parts.append(bag_desc['color'])

                if 'brand' in bag_desc:
                    desc_parts.append(bag_desc['brand'])

                if 'type' in bag_desc:
                    desc_parts.append(bag_desc['type'])

                if 'material' in bag_desc:
                    desc_parts.append(bag_desc['material'])

                canonical['description'] = ' '.join(desc_parts)

                # Special characteristics as handling codes
                if 'special_characteristics' in bag_desc:
                    canonical['special_handling_codes'] = bag_desc['special_characteristics']

            # Irregularity details - this is the key WorldTracer data
            irregularity = wt_data.get('irregularity', {})

            if irregularity:
                # Map PIR type to exception type
                pir_type = irregularity.get('type', '').upper()
                exception_type = WorldTracerMapper.PIR_TYPE_TO_EXCEPTION.get(
                    pir_type,
                    ExceptionType.MISHANDLED
                )

                # Build exception case
                exception_case = {
                    'exception_type': exception_type.value,
                    'worldtracer_ref': wt_data.get('ohd_reference', ''),
                    'reported_at': irregularity.get('date_time', datetime.now().isoformat()),
                    'reported_by': wt_data.get('created_by', ''),
                    'description': irregularity.get('remarks', ''),
                    'status': wt_data.get('current_status', {}).get('status', 'OPEN')
                }

                # Determine severity based on type
                severity_map = {
                    ExceptionType.LOST: 'CRITICAL',
                    ExceptionType.PILFERED: 'CRITICAL',
                    ExceptionType.DAMAGED: 'HIGH',
                    ExceptionType.DELAYED: 'MEDIUM',
                    ExceptionType.MISHANDLED: 'MEDIUM',
                    ExceptionType.MISROUTED: 'HIGH'
                }

                exception_case['severity'] = severity_map.get(exception_type, 'MEDIUM')

                canonical['exception_status'] = exception_case

                # Set state to EXCEPTION
                canonical['current_state'] = BagState.EXCEPTION

                # Set mishandled flag
                canonical['is_mishandled'] = True

                # Determine risk level based on exception type
                risk_map = {
                    ExceptionType.LOST: RiskLevel.CRITICAL,
                    ExceptionType.PILFERED: RiskLevel.CRITICAL,
                    ExceptionType.DAMAGED: RiskLevel.HIGH,
                    ExceptionType.DELAYED: RiskLevel.MEDIUM,
                    ExceptionType.MISHANDLED: RiskLevel.MEDIUM,
                    ExceptionType.MISROUTED: RiskLevel.HIGH
                }

                canonical['risk_level'] = risk_map.get(exception_type, RiskLevel.MEDIUM)

                # Add risk factors
                canonical['risk_factors'] = [f"worldtracer_case_{exception_type.value}"]

                # Last known location
                if 'last_seen_location' in irregularity:
                    canonical['last_known_location'] = {
                        'location_code': irregularity['last_seen_location'],
                        'location_type': 'UNKNOWN'
                    }

            # Current status
            current_status = wt_data.get('current_status', {})

            if current_status:
                # Update location if bag has been located
                if current_status.get('located') and current_status.get('current_location'):
                    canonical['current_location'] = {
                        'location_code': current_status['current_location'],
                        'location_type': 'UNKNOWN'
                    }

                # If bag is found, update state
                if current_status.get('status') == 'FOUND':
                    canonical['current_state'] = BagState.FOUND

                    if canonical.get('exception_status'):
                        canonical['exception_status']['status'] = 'RESOLVED'
                        canonical['exception_status']['resolved_at'] = wt_data.get('updated_at', datetime.now().isoformat())

            # Timestamps
            canonical['timestamp'] = wt_data.get('updated_at', datetime.now().isoformat())

            # Add data source reference
            canonical['external_references'] = {
                'worldtracer_ohd': wt_data.get('ohd_reference', ''),
                'worldtracer_station': irregularity.get('station', '')
            }

            logger.debug(f"Successfully mapped WorldTracer data for bag {canonical.get('bag_tag')}")

            return canonical

        except Exception as e:
            logger.error(f"Error mapping WorldTracer data to canonical: {e}")
            logger.debug(f"WorldTracer data: {wt_data}")
            raise

    @staticmethod
    def from_canonical(canonical_bag: CanonicalBag) -> Dict[str, Any]:
        """
        Map canonical bag to WorldTracer PIR format

        Args:
            canonical_bag: CanonicalBag instance

        Returns:
            WorldTracer PIR format dict
        """
        logger.debug(f"Mapping canonical bag {canonical_bag.bag_tag} to WorldTracer format")

        try:
            # Build passenger section
            passenger = {}

            if canonical_bag.passenger_last_name:
                passenger['surname'] = canonical_bag.passenger_last_name

            if canonical_bag.passenger_first_name:
                passenger['first_name'] = canonical_bag.passenger_first_name

            if canonical_bag.pnr:
                passenger['pnr'] = canonical_bag.pnr

            # Contact info
            if canonical_bag.contact:
                if canonical_bag.contact.email:
                    passenger['contact_email'] = canonical_bag.contact.email
                if canonical_bag.contact.phone:
                    passenger['contact_phone'] = canonical_bag.contact.phone
                if canonical_bag.contact.mobile:
                    passenger['contact_mobile'] = canonical_bag.contact.mobile
                if canonical_bag.contact.address:
                    passenger['delivery_address'] = canonical_bag.contact.address
                if canonical_bag.contact.preferred_language:
                    passenger['preferred_language'] = canonical_bag.contact.preferred_language

            # Build itinerary section
            itinerary = {
                'origin': canonical_bag.origin.iata_code,
                'destination': canonical_bag.destination.iata_code,
                'flight': canonical_bag.outbound_flight.full_flight_number
            }

            # Build bag description
            bag_description = {}

            if canonical_bag.description:
                # Try to parse description back into components
                # This is best-effort since we combined them earlier
                bag_description['description'] = canonical_bag.description

            if canonical_bag.special_handling_codes:
                bag_description['special_characteristics'] = canonical_bag.special_handling_codes

            # Build irregularity section (if exception exists)
            irregularity = {}

            if canonical_bag.exception_status:
                # Reverse map exception type to PIR type
                exception_to_pir = {v: k for k, v in WorldTracerMapper.PIR_TYPE_TO_EXCEPTION.items()}

                try:
                    exception_type = ExceptionType(canonical_bag.exception_status.exception_type)
                    pir_type = exception_to_pir.get(exception_type, 'MISHANDLED')
                except:
                    pir_type = 'MISHANDLED'

                irregularity = {
                    'type': pir_type,
                    'date_time': canonical_bag.exception_status.reported_at.isoformat() if canonical_bag.exception_status.reported_at else datetime.now().isoformat(),
                    'remarks': canonical_bag.exception_status.description or ''
                }

                if canonical_bag.last_known_location:
                    irregularity['last_seen_location'] = canonical_bag.last_known_location.location_code

                if 'worldtracer_station' in canonical_bag.external_references:
                    irregularity['station'] = canonical_bag.external_references['worldtracer_station']

            # Build current status
            current_status = {}

            if canonical_bag.exception_status:
                current_status['status'] = canonical_bag.exception_status.status

                # Check if bag has been located
                if canonical_bag.current_state in [BagState.FOUND, BagState.FORWARDED]:
                    current_status['located'] = True
                    if canonical_bag.current_location:
                        current_status['current_location'] = canonical_bag.current_location.location_code
                else:
                    current_status['located'] = False
            else:
                current_status['status'] = 'N/A'
                current_status['located'] = True

            # Build complete WorldTracer PIR
            wt_data = {
                'ohd_reference': canonical_bag.exception_status.worldtracer_ref if canonical_bag.exception_status else '',
                'pir_type': irregularity.get('type', 'MISHANDLED'),
                'bag_tag': canonical_bag.bag_tag,
                'passenger': passenger,
                'itinerary': itinerary,
                'bag_description': bag_description,
                'irregularity': irregularity,
                'current_status': current_status,
                'created_at': canonical_bag.exception_status.reported_at.isoformat() if canonical_bag.exception_status else canonical_bag.created_at.isoformat(),
                'updated_at': canonical_bag.updated_at.isoformat()
            }

            # Add external reference if available
            if 'worldtracer_ohd' in canonical_bag.external_references:
                wt_data['ohd_reference'] = canonical_bag.external_references['worldtracer_ohd']

            logger.debug(f"Successfully mapped canonical bag to WorldTracer format")

            return wt_data

        except Exception as e:
            logger.error(f"Error mapping canonical bag to WorldTracer format: {e}")
            raise
