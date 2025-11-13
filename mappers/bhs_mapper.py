"""
BHS Mapper
==========

Bidirectional mapper between BHS (Baggage Handling System) format
and Canonical Bag model.

BHS systems provide scan events and location tracking data.

Version: 1.0.0
Date: 2025-11-13
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from models.canonical_bag import (
    CanonicalBag,
    Location,
    BagState,
    DataSource
)


class BHSMapper:
    """
    Maps between BHS scan event format and Canonical Bag model

    BHS Format (vendor-specific):
    {
        "license_plate": "BHS123456789",
        "bag_tag": "0291234567",
        "scan_event": {
            "event_type": "SORTATION",
            "scanner_id": "SORT_LAX_01",
            "location_code": "LAX_T4_SORT_01",
            "location_type": "SORTATION",
            "terminal": "T4",
            "timestamp": "2025-11-13T10:05:00Z"
        },
        "routing": {
            "origin": "LAX",
            "destination": "JFK",
            "outbound_lp": "LP123",
            "inbound_lp": "LP100",
            "flight": "AA123"
        },
        "physical": {
            "weight_kg": 23.5,
            "length_cm": 55,
            "width_cm": 40,
            "height_cm": 23,
            "image_url": "http://bhs/images/123.jpg"
        },
        "scan_history": [
            {"type": "CHECKIN", "timestamp": "2025-11-13T10:00:00Z", "location": "LAX_T4_CKI_12"},
            {"type": "SORTATION", "timestamp": "2025-11-13T10:05:00Z", "location": "LAX_T4_SORT_01"}
        ]
    }
    """

    # Map BHS scan types to canonical states
    SCAN_TYPE_TO_STATE = {
        'CHECKIN': BagState.CHECKED_IN,
        'SORTATION': BagState.SORTED,
        'MAKEUP': BagState.SORTED,
        'LOADING': BagState.LOADED,
        'OFFLOAD': BagState.IN_SYSTEM,
        'TRANSFER': BagState.IN_TRANSFER,
        'ARRIVAL': BagState.ARRIVED,
        'CLAIM': BagState.AT_CLAIM,
        'CLAIMED': BagState.CLAIMED,
        'EXCEPTION': BagState.EXCEPTION,
        'MANUAL': BagState.IN_SYSTEM,
        'SECURITY': BagState.IN_SYSTEM,
        'CUSTOMS': BagState.IN_SYSTEM
    }

    @staticmethod
    def to_canonical(bhs_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map BHS scan event data to canonical format

        Args:
            bhs_data: BHS format data

        Returns:
            Dict compatible with CanonicalBag
        """
        logger.debug(f"Mapping BHS data to canonical format")

        canonical = {}

        try:
            # Identity
            if 'bag_tag' in bhs_data:
                canonical['bag_tag'] = str(bhs_data['bag_tag']).zfill(10)

            if 'license_plate' in bhs_data:
                canonical['license_plate'] = bhs_data['license_plate']

            # Scan event details
            scan_event = bhs_data.get('scan_event', {})

            if scan_event:
                event_type = scan_event.get('event_type', '').upper()

                # Map scan type to state
                if event_type in BHSMapper.SCAN_TYPE_TO_STATE:
                    canonical['current_state'] = BHSMapper.SCAN_TYPE_TO_STATE[event_type]

                canonical['last_scan_type'] = event_type

                # Timestamp
                if 'timestamp' in scan_event:
                    timestamp = scan_event['timestamp']
                    canonical['last_scan_at'] = timestamp

                    # If this is first scan, also set as first_scan_at
                    if event_type == 'CHECKIN':
                        canonical['first_scan_at'] = timestamp
                        canonical['checked_in_at'] = timestamp

                # Location details
                location = {}

                if 'location_code' in scan_event:
                    location['location_code'] = scan_event['location_code']

                if 'location_type' in scan_event:
                    location['location_type'] = scan_event['location_type']

                if 'terminal' in scan_event:
                    location['terminal'] = scan_event['terminal']

                if 'area' in scan_event:
                    location['area'] = scan_event['area']

                if 'facility' in scan_event:
                    location['facility'] = scan_event['facility']

                # Add semantic meaning based on location type
                location_meaning_map = {
                    'CHECKIN': 'Bag accepted at check-in counter',
                    'SORTATION': 'Bag being sorted to correct flight',
                    'MAKEUP': 'Bag waiting for loading',
                    'LOADING': 'Bag loaded onto aircraft',
                    'CLAIM': 'Bag delivered to baggage claim'
                }

                location_type = scan_event.get('location_type', '').upper()
                if location_type in location_meaning_map:
                    location['semantic_meaning'] = location_meaning_map[location_type]

                if location:
                    canonical['current_location'] = location
                    canonical['last_known_location'] = location

            # Routing information
            routing = bhs_data.get('routing', {})

            if routing:
                if 'origin' in routing:
                    canonical['origin'] = {'iata_code': routing['origin'].upper()}

                if 'destination' in routing:
                    canonical['destination'] = {'iata_code': routing['destination'].upper()}

                # License plates for routing
                if 'outbound_lp' in routing:
                    canonical['outbound_license_plate'] = routing['outbound_lp']

                if 'inbound_lp' in routing:
                    canonical['inbound_license_plate'] = routing['inbound_lp']

                # Flight number (parse if string like "AA123")
                if 'flight' in routing:
                    flight_str = routing['flight']

                    # Extract airline code (first 2-3 characters)
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

            # Physical characteristics
            physical = bhs_data.get('physical', {})

            if physical:
                dimensions = {}

                if 'weight_kg' in physical:
                    dimensions['weight_kg'] = float(physical['weight_kg'])

                if 'length_cm' in physical:
                    dimensions['length_cm'] = int(physical['length_cm'])

                if 'width_cm' in physical:
                    dimensions['width_cm'] = int(physical['width_cm'])

                if 'height_cm' in physical:
                    dimensions['height_cm'] = int(physical['height_cm'])

                if dimensions:
                    canonical['dimensions'] = dimensions

            # Scan history
            scan_history = bhs_data.get('scan_history', [])

            if scan_history:
                canonical['scan_count'] = len(scan_history)

                # Get first and last scan times
                timestamps = [s.get('timestamp') for s in scan_history if s.get('timestamp')]

                if timestamps:
                    canonical['first_scan_at'] = min(timestamps)
                    canonical['last_scan_at'] = max(timestamps)

                # Get last scan type
                if scan_history:
                    canonical['last_scan_type'] = scan_history[-1].get('type', '')

            # Add timestamp
            canonical['timestamp'] = scan_event.get('timestamp', datetime.now().isoformat())

            # Add data source reference
            canonical['external_references'] = {
                'bhs_scanner_id': scan_event.get('scanner_id', ''),
                'bhs_license_plate': bhs_data.get('license_plate', '')
            }

            logger.debug(f"Successfully mapped BHS data for bag {canonical.get('bag_tag')}")

            return canonical

        except Exception as e:
            logger.error(f"Error mapping BHS data to canonical: {e}")
            logger.debug(f"BHS data: {bhs_data}")
            raise

    @staticmethod
    def from_canonical(canonical_bag: CanonicalBag) -> Dict[str, Any]:
        """
        Map canonical bag to BHS format

        Args:
            canonical_bag: CanonicalBag instance

        Returns:
            BHS format dict
        """
        logger.debug(f"Mapping canonical bag {canonical_bag.bag_tag} to BHS format")

        try:
            # Reverse map state to scan type
            state_to_scan_type = {v: k for k, v in BHSMapper.SCAN_TYPE_TO_STATE.items()}

            # Build scan event
            scan_event = {
                'event_type': canonical_bag.last_scan_type or state_to_scan_type.get(
                    canonical_bag.current_state,
                    'MANUAL'
                ),
                'timestamp': canonical_bag.last_scan_at.isoformat() if canonical_bag.last_scan_at else datetime.now().isoformat()
            }

            # Add location details
            if canonical_bag.current_location:
                scan_event['location_code'] = canonical_bag.current_location.location_code
                scan_event['location_type'] = canonical_bag.current_location.location_type

                if canonical_bag.current_location.terminal:
                    scan_event['terminal'] = canonical_bag.current_location.terminal

                if canonical_bag.current_location.area:
                    scan_event['area'] = canonical_bag.current_location.area

                if canonical_bag.current_location.facility:
                    scan_event['facility'] = canonical_bag.current_location.facility

            # Add scanner ID from external references
            if 'bhs_scanner_id' in canonical_bag.external_references:
                scan_event['scanner_id'] = canonical_bag.external_references['bhs_scanner_id']

            # Build routing section
            routing = {
                'origin': canonical_bag.origin.iata_code,
                'destination': canonical_bag.destination.iata_code,
                'flight': canonical_bag.outbound_flight.full_flight_number
            }

            if canonical_bag.outbound_license_plate:
                routing['outbound_lp'] = canonical_bag.outbound_license_plate

            if canonical_bag.inbound_license_plate:
                routing['inbound_lp'] = canonical_bag.inbound_license_plate

            # Build physical section
            physical = {}

            if canonical_bag.dimensions:
                if canonical_bag.dimensions.weight_kg:
                    physical['weight_kg'] = canonical_bag.dimensions.weight_kg

                if canonical_bag.dimensions.length_cm:
                    physical['length_cm'] = canonical_bag.dimensions.length_cm

                if canonical_bag.dimensions.width_cm:
                    physical['width_cm'] = canonical_bag.dimensions.width_cm

                if canonical_bag.dimensions.height_cm:
                    physical['height_cm'] = canonical_bag.dimensions.height_cm

            # Build complete BHS record
            bhs_data = {
                'license_plate': canonical_bag.license_plate or canonical_bag.outbound_license_plate or '',
                'bag_tag': canonical_bag.bag_tag,
                'scan_event': scan_event,
                'routing': routing,
                'physical': physical,
                'timestamp': canonical_bag.updated_at.isoformat()
            }

            # Add scan count
            if canonical_bag.scan_count > 0:
                bhs_data['total_scans'] = canonical_bag.scan_count

            logger.debug(f"Successfully mapped canonical bag to BHS format")

            return bhs_data

        except Exception as e:
            logger.error(f"Error mapping canonical bag to BHS format: {e}")
            raise


    @staticmethod
    def parse_scan_event(scan_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a standalone scan event into canonical updates

        Args:
            scan_event: Single scan event from BHS

        Returns:
            Canonical bag updates
        """
        updates = {}

        event_type = scan_event.get('event_type', '').upper()

        # Update state based on scan type
        if event_type in BHSMapper.SCAN_TYPE_TO_STATE:
            updates['current_state'] = BHSMapper.SCAN_TYPE_TO_STATE[event_type]

        updates['last_scan_type'] = event_type
        updates['last_scan_at'] = scan_event.get('timestamp', datetime.now().isoformat())

        # Location update
        if 'location_code' in scan_event:
            updates['current_location'] = {
                'location_code': scan_event['location_code'],
                'location_type': scan_event.get('location_type', 'UNKNOWN')
            }

        return updates
