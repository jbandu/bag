"""
Unit Tests for Data Mappers
============================

Tests for canonical data mappers that transform external system data
into canonical BagData format.

Version: 1.0.0
Date: 2025-11-14
"""

import pytest
from datetime import datetime
from typing import Dict, Any


# ============================================================================
# MOCK CANONICAL MODEL
# ============================================================================

class BagData:
    """Mock canonical bag data model"""
    def __init__(self, **kwargs):
        self.bag_tag = kwargs.get('bag_tag')
        self.passenger_name = kwargs.get('passenger_name')
        self.flight_number = kwargs.get('flight_number')
        self.origin = kwargs.get('origin')
        self.destination = kwargs.get('destination')
        self.weight_kg = kwargs.get('weight_kg')
        self.status = kwargs.get('status')
        self.last_scan_location = kwargs.get('last_scan_location')
        self.last_scan_time = kwargs.get('last_scan_time')
        self.connection_time_minutes = kwargs.get('connection_time_minutes')
        self.value_usd = kwargs.get('value_usd')
        self.confidence = kwargs.get('confidence', 1.0)
        self.source = kwargs.get('source')


# ============================================================================
# MAPPER IMPLEMENTATIONS (Mocked)
# ============================================================================

class DCSMapper:
    """Maps DCS (Departure Control System) data to canonical format"""

    @staticmethod
    def map_to_canonical(dcs_data: Dict[str, Any]) -> BagData:
        """
        Map DCS data to canonical BagData.

        DCS provides: passenger info, flight info, baggage count
        """
        # Extract passenger info
        pax = dcs_data.get('passenger', {})
        flight = dcs_data.get('flight', {})
        baggage = dcs_data.get('baggage', {})

        return BagData(
            bag_tag=baggage.get('tag_number'),
            passenger_name=f"{pax.get('first_name', '')} {pax.get('last_name', '')}".strip(),
            flight_number=flight.get('flight_number'),
            origin=flight.get('origin'),
            destination=flight.get('destination'),
            weight_kg=baggage.get('weight_kg'),
            status='CHECKED_IN',
            confidence=0.95,  # DCS is authoritative for check-in
            source='DCS'
        )


class BHSMapper:
    """Maps BHS (Baggage Handling System) data to canonical format"""

    @staticmethod
    def map_to_canonical(bhs_data: Dict[str, Any]) -> BagData:
        """
        Map BHS scan data to canonical BagData.

        BHS provides: scan events, location, timestamp
        """
        return BagData(
            bag_tag=bhs_data.get('bag_tag'),
            last_scan_location=bhs_data.get('location'),
            last_scan_time=bhs_data.get('timestamp'),
            status=bhs_data.get('scan_type', 'IN_SYSTEM'),
            confidence=0.99,  # BHS scans are highly reliable
            source='BHS'
        )


class WorldTracerMapper:
    """Maps WorldTracer PIR data to canonical format"""

    @staticmethod
    def map_to_canonical(wt_data: Dict[str, Any]) -> BagData:
        """
        Map WorldTracer PIR to canonical BagData.

        WorldTracer provides: mishandled bag info, last known location
        """
        pir = wt_data.get('pir', {})

        return BagData(
            bag_tag=pir.get('bag_tag_number'),
            passenger_name=pir.get('passenger_name'),
            flight_number=pir.get('flight_number'),
            origin=pir.get('origin_station'),
            destination=pir.get('destination_station'),
            last_scan_location=pir.get('last_seen_station'),
            status='MISHANDLED',
            confidence=0.90,  # WorldTracer data quality varies
            source='WorldTracer'
        )


class TypeBMapper:
    """Maps Type B message data to canonical format"""

    @staticmethod
    def map_to_canonical(typeb_data: Dict[str, Any]) -> BagData:
        """
        Map Type B message to canonical BagData.

        Type B provides: baggage manifest, transfer info
        """
        msg = typeb_data.get('message', {})

        return BagData(
            bag_tag=msg.get('bag_tag'),
            flight_number=msg.get('flight_number'),
            origin=msg.get('origin'),
            destination=msg.get('destination'),
            weight_kg=msg.get('weight'),
            status='MANIFESTED',
            confidence=0.85,  # Type B messages can have transmission errors
            source='TypeB'
        )


class BaggageXMLMapper:
    """Maps BaggageXML manifest data to canonical format"""

    @staticmethod
    def map_to_canonical(xml_data: Dict[str, Any]) -> BagData:
        """
        Map BaggageXML to canonical BagData.

        BaggageXML provides: IATA resolution 753 compliant tracking
        """
        bag = xml_data.get('BagDetails', {})
        journey = xml_data.get('JourneyDetails', {})

        return BagData(
            bag_tag=bag.get('BagTagNumber'),
            passenger_name=journey.get('PassengerName'),
            flight_number=journey.get('FlightNumber'),
            origin=journey.get('OriginAirport'),
            destination=journey.get('DestinationAirport'),
            weight_kg=bag.get('Weight'),
            status='TRACKED',
            confidence=0.95,  # IATA standard format
            source='BaggageXML'
        )


# ============================================================================
# UNIT TESTS
# ============================================================================

class TestDCSMapper:
    """Test DCS mapper"""

    def test_map_complete_dcs_data(self):
        """Test mapping complete DCS data"""
        dcs_data = {
            'passenger': {
                'first_name': 'John',
                'last_name': 'Smith',
                'pnr': 'ABC123'
            },
            'flight': {
                'flight_number': 'UA1234',
                'origin': 'SFO',
                'destination': 'JFK'
            },
            'baggage': {
                'tag_number': '0016123456789',
                'weight_kg': 23.5,
                'pieces': 1
            }
        }

        result = DCSMapper.map_to_canonical(dcs_data)

        assert result.bag_tag == '0016123456789'
        assert result.passenger_name == 'John Smith'
        assert result.flight_number == 'UA1234'
        assert result.origin == 'SFO'
        assert result.destination == 'JFK'
        assert result.weight_kg == 23.5
        assert result.status == 'CHECKED_IN'
        assert result.confidence == 0.95
        assert result.source == 'DCS'

    def test_map_partial_dcs_data(self):
        """Test mapping partial DCS data"""
        dcs_data = {
            'passenger': {
                'first_name': 'Jane'
            },
            'baggage': {
                'tag_number': '0016987654321'
            }
        }

        result = DCSMapper.map_to_canonical(dcs_data)

        assert result.bag_tag == '0016987654321'
        assert result.passenger_name == 'Jane'
        assert result.flight_number is None
        assert result.source == 'DCS'

    def test_map_empty_passenger_name(self):
        """Test handling of missing passenger name"""
        dcs_data = {
            'passenger': {},
            'baggage': {
                'tag_number': '0016111111111'
            }
        }

        result = DCSMapper.map_to_canonical(dcs_data)

        assert result.passenger_name == ''
        assert result.bag_tag == '0016111111111'


class TestBHSMapper:
    """Test BHS mapper"""

    def test_map_scan_event(self):
        """Test mapping BHS scan event"""
        bhs_data = {
            'bag_tag': '0016123456789',
            'location': 'MAKEUP_01',
            'timestamp': '2025-11-14T10:30:00Z',
            'scan_type': 'LOADED',
            'device_id': 'SCAN_034'
        }

        result = BHSMapper.map_to_canonical(bhs_data)

        assert result.bag_tag == '0016123456789'
        assert result.last_scan_location == 'MAKEUP_01'
        assert result.last_scan_time == '2025-11-14T10:30:00Z'
        assert result.status == 'LOADED'
        assert result.confidence == 0.99
        assert result.source == 'BHS'

    def test_map_multiple_scan_types(self):
        """Test different scan types"""
        scan_types = ['ARRIVAL', 'LOADED', 'MAKEUP', 'DELIVERED']

        for scan_type in scan_types:
            bhs_data = {
                'bag_tag': '0016999999999',
                'location': 'TEST_LOCATION',
                'timestamp': '2025-11-14T12:00:00Z',
                'scan_type': scan_type
            }

            result = BHSMapper.map_to_canonical(bhs_data)

            assert result.status == scan_type
            assert result.confidence == 0.99


class TestWorldTracerMapper:
    """Test WorldTracer mapper"""

    def test_map_pir_data(self):
        """Test mapping PIR data"""
        wt_data = {
            'pir': {
                'pir_number': 'SFOUA12345',
                'bag_tag_number': '0016123456789',
                'passenger_name': 'SMITH/JOHN',
                'flight_number': 'UA1234',
                'origin_station': 'SFO',
                'destination_station': 'JFK',
                'last_seen_station': 'ORD',
                'mishandled_reason': 'DELAYED'
            }
        }

        result = WorldTracerMapper.map_to_canonical(wt_data)

        assert result.bag_tag == '0016123456789'
        assert result.passenger_name == 'SMITH/JOHN'
        assert result.flight_number == 'UA1234'
        assert result.origin == 'SFO'
        assert result.destination == 'JFK'
        assert result.last_scan_location == 'ORD'
        assert result.status == 'MISHANDLED'
        assert result.confidence == 0.90
        assert result.source == 'WorldTracer'

    def test_map_minimal_pir(self):
        """Test mapping minimal PIR"""
        wt_data = {
            'pir': {
                'pir_number': 'TEST123',
                'bag_tag_number': '0016000000000'
            }
        }

        result = WorldTracerMapper.map_to_canonical(wt_data)

        assert result.bag_tag == '0016000000000'
        assert result.status == 'MISHANDLED'
        assert result.source == 'WorldTracer'


class TestTypeBMapper:
    """Test Type B message mapper"""

    def test_map_typeb_message(self):
        """Test mapping Type B message"""
        typeb_data = {
            'message': {
                'message_type': 'BPM',
                'bag_tag': '0016123456789',
                'flight_number': 'UA1234',
                'origin': 'SFO',
                'destination': 'JFK',
                'weight': 23,
                'pieces': 1
            }
        }

        result = TypeBMapper.map_to_canonical(typeb_data)

        assert result.bag_tag == '0016123456789'
        assert result.flight_number == 'UA1234'
        assert result.origin == 'SFO'
        assert result.destination == 'JFK'
        assert result.weight_kg == 23
        assert result.status == 'MANIFESTED'
        assert result.confidence == 0.85
        assert result.source == 'TypeB'

    def test_map_different_message_types(self):
        """Test different Type B message types"""
        message_types = ['BPM', 'CPM', 'UCM', 'BTM']

        for msg_type in message_types:
            typeb_data = {
                'message': {
                    'message_type': msg_type,
                    'bag_tag': '0016111111111'
                }
            }

            result = TypeBMapper.map_to_canonical(typeb_data)

            assert result.bag_tag == '0016111111111'
            assert result.confidence == 0.85


class TestBaggageXMLMapper:
    """Test BaggageXML mapper"""

    def test_map_baggagexml_data(self):
        """Test mapping BaggageXML data"""
        xml_data = {
            'BagDetails': {
                'BagTagNumber': '0016123456789',
                'Weight': 23.5,
                'TagIssuer': 'UA'
            },
            'JourneyDetails': {
                'PassengerName': 'Smith/John',
                'FlightNumber': 'UA1234',
                'OriginAirport': 'SFO',
                'DestinationAirport': 'JFK',
                'DepartureDate': '2025-11-14'
            }
        }

        result = BaggageXMLMapper.map_to_canonical(xml_data)

        assert result.bag_tag == '0016123456789'
        assert result.passenger_name == 'Smith/John'
        assert result.flight_number == 'UA1234'
        assert result.origin == 'SFO'
        assert result.destination == 'JFK'
        assert result.weight_kg == 23.5
        assert result.status == 'TRACKED'
        assert result.confidence == 0.95
        assert result.source == 'BaggageXML'

    def test_map_minimal_baggagexml(self):
        """Test mapping minimal BaggageXML"""
        xml_data = {
            'BagDetails': {
                'BagTagNumber': '0016000000000'
            },
            'JourneyDetails': {}
        }

        result = BaggageXMLMapper.map_to_canonical(xml_data)

        assert result.bag_tag == '0016000000000'
        assert result.status == 'TRACKED'
        assert result.confidence == 0.95


# ============================================================================
# CONFIDENCE SCORING TESTS
# ============================================================================

class TestConfidenceScoring:
    """Test confidence scores across mappers"""

    def test_confidence_ordering(self):
        """Test that confidence scores reflect data quality"""
        # BHS scans should have highest confidence (physical scans)
        bhs_data = {'bag_tag': 'TEST', 'location': 'LOC', 'timestamp': 'NOW'}
        bhs_result = BHSMapper.map_to_canonical(bhs_data)

        # DCS should have high confidence (authoritative source)
        dcs_data = {'passenger': {}, 'flight': {}, 'baggage': {'tag_number': 'TEST'}}
        dcs_result = DCSMapper.map_to_canonical(dcs_data)

        # WorldTracer should have lower confidence (data quality varies)
        wt_data = {'pir': {'bag_tag_number': 'TEST'}}
        wt_result = WorldTracerMapper.map_to_canonical(wt_data)

        # Type B should have lower confidence (transmission errors)
        typeb_data = {'message': {'bag_tag': 'TEST'}}
        typeb_result = TypeBMapper.map_to_canonical(typeb_data)

        assert bhs_result.confidence == 0.99  # Highest
        assert dcs_result.confidence == 0.95  # High
        assert wt_result.confidence == 0.90   # Medium
        assert typeb_result.confidence == 0.85  # Lower

    def test_all_confidences_in_range(self):
        """Test that all confidence scores are between 0 and 1"""
        mappers = [
            (DCSMapper, {'passenger': {}, 'flight': {}, 'baggage': {'tag_number': 'T'}}),
            (BHSMapper, {'bag_tag': 'T', 'location': 'L', 'timestamp': 'T'}),
            (WorldTracerMapper, {'pir': {'bag_tag_number': 'T'}}),
            (TypeBMapper, {'message': {'bag_tag': 'T'}}),
            (BaggageXMLMapper, {'BagDetails': {'BagTagNumber': 'T'}, 'JourneyDetails': {}})
        ]

        for mapper_class, test_data in mappers:
            result = mapper_class.map_to_canonical(test_data)
            assert 0.0 <= result.confidence <= 1.0, \
                f"{mapper_class.__name__} confidence out of range: {result.confidence}"


# ============================================================================
# DATA VALIDATION TESTS
# ============================================================================

class TestDataValidation:
    """Test data validation across mappers"""

    def test_all_mappers_set_source(self):
        """Test that all mappers set the source field"""
        test_cases = [
            (DCSMapper, {'passenger': {}, 'flight': {}, 'baggage': {'tag_number': 'T'}}, 'DCS'),
            (BHSMapper, {'bag_tag': 'T', 'location': 'L', 'timestamp': 'T'}, 'BHS'),
            (WorldTracerMapper, {'pir': {'bag_tag_number': 'T'}}, 'WorldTracer'),
            (TypeBMapper, {'message': {'bag_tag': 'T'}}, 'TypeB'),
            (BaggageXMLMapper, {'BagDetails': {'BagTagNumber': 'T'}, 'JourneyDetails': {}}, 'BaggageXML')
        ]

        for mapper_class, test_data, expected_source in test_cases:
            result = mapper_class.map_to_canonical(test_data)
            assert result.source == expected_source, \
                f"{mapper_class.__name__} should set source to {expected_source}"

    def test_bag_tag_extraction(self):
        """Test that all mappers extract bag tag correctly"""
        test_cases = [
            (DCSMapper, {'passenger': {}, 'flight': {}, 'baggage': {'tag_number': 'BAG123'}}),
            (BHSMapper, {'bag_tag': 'BAG456', 'location': 'L', 'timestamp': 'T'}),
            (WorldTracerMapper, {'pir': {'bag_tag_number': 'BAG789'}}),
            (TypeBMapper, {'message': {'bag_tag': 'BAG000'}}),
            (BaggageXMLMapper, {'BagDetails': {'BagTagNumber': 'BAG999'}, 'JourneyDetails': {}})
        ]

        for mapper_class, test_data in test_cases:
            result = mapper_class.map_to_canonical(test_data)
            assert result.bag_tag is not None, \
                f"{mapper_class.__name__} should extract bag_tag"
            assert result.bag_tag.startswith('BAG'), \
                f"{mapper_class.__name__} extracted wrong bag_tag: {result.bag_tag}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
