"""
Semantic Tests for Data Fusion
===============================

Tests for data fusion accuracy, conflict resolution, and confidence scoring.

Version: 1.0.0
Date: 2025-11-14
"""

import pytest
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


# ============================================================================
# MOCK DATA MODELS
# ============================================================================

class BagData:
    """Canonical bag data"""
    def __init__(self, **kwargs):
        self.bag_tag = kwargs.get('bag_tag')
        self.passenger_name = kwargs.get('passenger_name')
        self.flight_number = kwargs.get('flight_number')
        self.origin = kwargs.get('origin')
        self.destination = kwargs.get('destination')
        self.weight_kg = kwargs.get('weight_kg')
        self.status = kwargs.get('status')
        self.last_scan_location = kwargs.get('last_scan_location')
        self.connection_time_minutes = kwargs.get('connection_time_minutes')
        self.confidence = kwargs.get('confidence', 1.0)
        self.source = kwargs.get('source')
        self.timestamp = kwargs.get('timestamp', datetime.now().isoformat())


# ============================================================================
# DATA FUSION ENGINE
# ============================================================================

class DataFusionEngine:
    """Fuses data from multiple sources"""

    @staticmethod
    def fuse_by_confidence(data_sources: List[BagData]) -> BagData:
        """
        Fuse data by selecting highest confidence value for each field.

        Args:
            data_sources: List of BagData from different sources

        Returns:
            Fused BagData
        """
        if not data_sources:
            return None

        # Start with first source
        fused = BagData(bag_tag=data_sources[0].bag_tag)

        # For each field, select value from highest confidence source
        fields = [
            'passenger_name', 'flight_number', 'origin', 'destination',
            'weight_kg', 'status', 'last_scan_location', 'connection_time_minutes'
        ]

        for field in fields:
            best_source = max(
                (s for s in data_sources if getattr(s, field, None) is not None),
                key=lambda s: s.confidence,
                default=None
            )

            if best_source:
                setattr(fused, field, getattr(best_source, field))

        # Set overall confidence as weighted average
        fused.confidence = sum(s.confidence for s in data_sources) / len(data_sources)

        # List all sources
        fused.source = ','.join(s.source for s in data_sources)

        return fused

    @staticmethod
    def detect_conflicts(data_sources: List[BagData]) -> List[Dict[str, Any]]:
        """
        Detect conflicts between data sources.

        Args:
            data_sources: List of BagData from different sources

        Returns:
            List of conflicts with field, values, and sources
        """
        conflicts = []

        fields = ['passenger_name', 'flight_number', 'origin', 'destination', 'weight_kg']

        for field in fields:
            # Get all unique values for this field
            values = {}
            for source in data_sources:
                value = getattr(source, field, None)
                if value is not None:
                    if value not in values:
                        values[value] = []
                    values[value].append({
                        'source': source.source,
                        'confidence': source.confidence
                    })

            # If more than one unique value, it's a conflict
            if len(values) > 1:
                conflicts.append({
                    'field': field,
                    'values': values
                })

        return conflicts

    @staticmethod
    def resolve_conflict(
        field: str,
        conflicting_values: Dict[str, List[Dict[str, Any]]]
    ) -> Any:
        """
        Resolve conflict by selecting value from highest confidence source.

        Args:
            field: Field name
            conflicting_values: Dict of value -> list of sources

        Returns:
            Resolved value
        """
        # Find value with highest confidence source
        best_value = None
        best_confidence = 0.0

        for value, sources in conflicting_values.items():
            max_conf = max(s['confidence'] for s in sources)
            if max_conf > best_confidence:
                best_confidence = max_conf
                best_value = value

        return best_value

    @staticmethod
    def calculate_data_quality_score(fused_data: BagData, data_sources: List[BagData]) -> float:
        """
        Calculate data quality score for fused data.

        Score based on:
        - Number of sources (more sources = higher quality)
        - Average confidence
        - Completeness (% of fields populated)
        - Consistency (fewer conflicts = higher quality)

        Args:
            fused_data: Fused bag data
            data_sources: Original sources

        Returns:
            Quality score (0.0 to 1.0)
        """
        # Source diversity score (0.0 to 0.25)
        source_score = min(len(data_sources) / 5.0, 1.0) * 0.25

        # Confidence score (0.0 to 0.25)
        avg_confidence = sum(s.confidence for s in data_sources) / len(data_sources)
        confidence_score = avg_confidence * 0.25

        # Completeness score (0.0 to 0.25)
        fields = [
            'passenger_name', 'flight_number', 'origin', 'destination',
            'weight_kg', 'status', 'last_scan_location'
        ]
        populated = sum(1 for f in fields if getattr(fused_data, f, None) is not None)
        completeness_score = (populated / len(fields)) * 0.25

        # Consistency score (0.0 to 0.25)
        conflicts = DataFusionEngine.detect_conflicts(data_sources)
        consistency_score = (1.0 - min(len(conflicts) / 5.0, 1.0)) * 0.25

        return source_score + confidence_score + completeness_score + consistency_score


# ============================================================================
# FUSION TESTS
# ============================================================================

class TestBasicFusion:
    """Test basic data fusion"""

    def test_fuse_single_source(self):
        """Test fusing single data source"""
        dcs_data = BagData(
            bag_tag="0016123456789",
            passenger_name="SMITH/JOHN",
            flight_number="UA1234",
            confidence=0.95,
            source="DCS"
        )

        fused = DataFusionEngine.fuse_by_confidence([dcs_data])

        assert fused.bag_tag == "0016123456789"
        assert fused.passenger_name == "SMITH/JOHN"
        assert fused.flight_number == "UA1234"
        assert fused.source == "DCS"

    def test_fuse_complementary_sources(self):
        """Test fusing complementary sources (no conflicts)"""
        dcs_data = BagData(
            bag_tag="0016123456789",
            passenger_name="SMITH/JOHN",
            flight_number="UA1234",
            confidence=0.95,
            source="DCS"
        )

        bhs_data = BagData(
            bag_tag="0016123456789",
            last_scan_location="MAKEUP_01",
            status="LOADED",
            confidence=0.99,
            source="BHS"
        )

        fused = DataFusionEngine.fuse_by_confidence([dcs_data, bhs_data])

        # Should have data from both sources
        assert fused.passenger_name == "SMITH/JOHN"  # From DCS
        assert fused.flight_number == "UA1234"  # From DCS
        assert fused.last_scan_location == "MAKEUP_01"  # From BHS
        assert fused.status == "LOADED"  # From BHS

    def test_fuse_with_confidence_selection(self):
        """Test fusing picks highest confidence source"""
        # DCS has lower confidence for weight
        dcs_data = BagData(
            bag_tag="0016123456789",
            weight_kg=23.0,
            confidence=0.85,
            source="DCS"
        )

        # BaggageXML has higher confidence for weight
        xml_data = BagData(
            bag_tag="0016123456789",
            weight_kg=23.5,
            confidence=0.95,
            source="BaggageXML"
        )

        fused = DataFusionEngine.fuse_by_confidence([dcs_data, xml_data])

        # Should pick higher confidence value
        assert fused.weight_kg == 23.5  # From BaggageXML (higher confidence)


class TestConflictDetection:
    """Test conflict detection"""

    def test_detect_no_conflicts(self):
        """Test detecting no conflicts when data agrees"""
        source1 = BagData(
            bag_tag="0016123456789",
            flight_number="UA1234",
            confidence=0.95,
            source="DCS"
        )

        source2 = BagData(
            bag_tag="0016123456789",
            flight_number="UA1234",  # Same value
            confidence=0.90,
            source="TypeB"
        )

        conflicts = DataFusionEngine.detect_conflicts([source1, source2])

        assert len(conflicts) == 0

    def test_detect_single_conflict(self):
        """Test detecting single field conflict"""
        source1 = BagData(
            bag_tag="0016123456789",
            flight_number="UA1234",
            confidence=0.95,
            source="DCS"
        )

        source2 = BagData(
            bag_tag="0016123456789",
            flight_number="UA5678",  # Different!
            confidence=0.85,
            source="TypeB"
        )

        conflicts = DataFusionEngine.detect_conflicts([source1, source2])

        assert len(conflicts) == 1
        assert conflicts[0]['field'] == 'flight_number'
        assert 'UA1234' in conflicts[0]['values']
        assert 'UA5678' in conflicts[0]['values']

    def test_detect_multiple_conflicts(self):
        """Test detecting multiple field conflicts"""
        source1 = BagData(
            bag_tag="0016123456789",
            flight_number="UA1234",
            origin="SFO",
            destination="JFK",
            confidence=0.95,
            source="DCS"
        )

        source2 = BagData(
            bag_tag="0016123456789",
            flight_number="UA5678",  # Conflict 1
            origin="LAX",  # Conflict 2
            destination="JFK",  # No conflict
            confidence=0.85,
            source="TypeB"
        )

        conflicts = DataFusionEngine.detect_conflicts([source1, source2])

        assert len(conflicts) == 2
        conflict_fields = {c['field'] for c in conflicts}
        assert 'flight_number' in conflict_fields
        assert 'origin' in conflict_fields


class TestConflictResolution:
    """Test conflict resolution"""

    def test_resolve_by_highest_confidence(self):
        """Test resolving conflict by selecting highest confidence"""
        conflicting_values = {
            'UA1234': [{'source': 'DCS', 'confidence': 0.95}],
            'UA5678': [{'source': 'TypeB', 'confidence': 0.85}]
        }

        resolved = DataFusionEngine.resolve_conflict('flight_number', conflicting_values)

        assert resolved == 'UA1234'  # Higher confidence

    def test_resolve_with_multiple_sources_same_value(self):
        """Test resolution when multiple sources agree"""
        conflicting_values = {
            'UA1234': [
                {'source': 'DCS', 'confidence': 0.95},
                {'source': 'BaggageXML', 'confidence': 0.95}
            ],
            'UA5678': [
                {'source': 'TypeB', 'confidence': 0.85}
            ]
        }

        resolved = DataFusionEngine.resolve_conflict('flight_number', conflicting_values)

        # Should pick value with highest confidence source
        assert resolved == 'UA1234'

    def test_resolve_weight_conflict(self):
        """Test resolving weight conflicts"""
        conflicting_values = {
            23.0: [{'source': 'DCS', 'confidence': 0.85}],
            23.5: [{'source': 'BaggageXML', 'confidence': 0.95}]
        }

        resolved = DataFusionEngine.resolve_conflict('weight_kg', conflicting_values)

        assert resolved == 23.5  # Higher confidence


class TestDataQualityScoring:
    """Test data quality scoring"""

    def test_quality_score_single_source(self):
        """Test quality score with single source"""
        source = BagData(
            bag_tag="0016123456789",
            passenger_name="SMITH/JOHN",
            flight_number="UA1234",
            origin="SFO",
            destination="JFK",
            weight_kg=23.5,
            status="CHECKED_IN",
            confidence=0.95,
            source="DCS"
        )

        fused = DataFusionEngine.fuse_by_confidence([source])
        score = DataFusionEngine.calculate_data_quality_score(fused, [source])

        # Should have decent score but not perfect (only 1 source)
        assert 0.6 <= score <= 0.9

    def test_quality_score_multiple_sources_no_conflicts(self):
        """Test quality score with multiple agreeing sources"""
        source1 = BagData(
            bag_tag="0016123456789",
            passenger_name="SMITH/JOHN",
            flight_number="UA1234",
            confidence=0.95,
            source="DCS"
        )

        source2 = BagData(
            bag_tag="0016123456789",
            last_scan_location="MAKEUP_01",
            status="LOADED",
            confidence=0.99,
            source="BHS"
        )

        source3 = BagData(
            bag_tag="0016123456789",
            weight_kg=23.5,
            confidence=0.95,
            source="BaggageXML"
        )

        fused = DataFusionEngine.fuse_by_confidence([source1, source2, source3])
        score = DataFusionEngine.calculate_data_quality_score(fused, [source1, source2, source3])

        # Should have high score (multiple sources, no conflicts)
        assert score >= 0.7

    def test_quality_score_with_conflicts(self):
        """Test quality score decreases with conflicts"""
        source1 = BagData(
            bag_tag="0016123456789",
            flight_number="UA1234",
            origin="SFO",
            confidence=0.95,
            source="DCS"
        )

        source2 = BagData(
            bag_tag="0016123456789",
            flight_number="UA5678",  # Conflict
            origin="LAX",  # Conflict
            confidence=0.85,
            source="TypeB"
        )

        fused = DataFusionEngine.fuse_by_confidence([source1, source2])
        score = DataFusionEngine.calculate_data_quality_score(fused, [source1, source2])

        # Score should be lower due to conflicts
        # Get score without conflicts for comparison
        source3 = BagData(
            bag_tag="0016123456789",
            flight_number="UA1234",  # No conflict
            origin="SFO",  # No conflict
            confidence=0.90,
            source="BaggageXML"
        )

        fused_no_conflict = DataFusionEngine.fuse_by_confidence([source1, source3])
        score_no_conflict = DataFusionEngine.calculate_data_quality_score(
            fused_no_conflict, [source1, source3]
        )

        assert score < score_no_conflict


class TestConfidenceWeighting:
    """Test confidence-based weighting"""

    def test_fused_confidence_is_average(self):
        """Test fused data confidence is average of sources"""
        source1 = BagData(
            bag_tag="0016123456789",
            confidence=0.90,
            source="Source1"
        )

        source2 = BagData(
            bag_tag="0016123456789",
            confidence=0.80,
            source="Source2"
        )

        fused = DataFusionEngine.fuse_by_confidence([source1, source2])

        expected_confidence = (0.90 + 0.80) / 2
        assert abs(fused.confidence - expected_confidence) < 0.01

    def test_high_confidence_source_preferred(self):
        """Test high confidence source is preferred for conflicts"""
        bhs_data = BagData(
            bag_tag="0016123456789",
            status="LOADED",
            confidence=0.99,  # Very high
            source="BHS"
        )

        typeb_data = BagData(
            bag_tag="0016123456789",
            status="CHECKED_IN",
            confidence=0.85,  # Lower
            source="TypeB"
        )

        fused = DataFusionEngine.fuse_by_confidence([bhs_data, typeb_data])

        # Should pick BHS value (higher confidence)
        assert fused.status == "LOADED"


class TestRealWorldScenarios:
    """Test real-world fusion scenarios"""

    def test_mishandled_bag_data_fusion(self):
        """Test fusing data for mishandled bag"""
        # DCS has passenger and flight info
        dcs_data = BagData(
            bag_tag="0016123456789",
            passenger_name="SMITH/JOHN",
            flight_number="UA1234",
            origin="SFO",
            destination="JFK",
            confidence=0.95,
            source="DCS"
        )

        # BHS has last scan location (bag went wrong way)
        bhs_data = BagData(
            bag_tag="0016123456789",
            last_scan_location="ORD",  # Wrong airport!
            status="LOADED",
            confidence=0.99,
            source="BHS"
        )

        # WorldTracer has PIR info
        wt_data = BagData(
            bag_tag="0016123456789",
            status="MISHANDLED",
            confidence=0.90,
            source="WorldTracer"
        )

        fused = DataFusionEngine.fuse_by_confidence([dcs_data, bhs_data, wt_data])

        # Should have complete picture
        assert fused.passenger_name == "SMITH/JOHN"
        assert fused.flight_number == "UA1234"
        assert fused.last_scan_location == "ORD"
        # Status should come from highest confidence source (BHS > WT)
        assert fused.status == "LOADED"  # BHS has 0.99 confidence

    def test_transfer_bag_data_fusion(self):
        """Test fusing data for transfer bag"""
        # DCS has original flight
        dcs_data = BagData(
            bag_tag="0016123456789",
            flight_number="UA1234",
            origin="SFO",
            destination="JFK",
            connection_time_minutes=45,
            confidence=0.95,
            source="DCS"
        )

        # BHS has current location
        bhs_data = BagData(
            bag_tag="0016123456789",
            last_scan_location="TRANSFER_01",
            confidence=0.99,
            source="BHS"
        )

        # Type B has manifest info
        typeb_data = BagData(
            bag_tag="0016123456789",
            flight_number="UA1234",
            weight_kg=23.5,
            confidence=0.85,
            source="TypeB"
        )

        fused = DataFusionEngine.fuse_by_confidence([dcs_data, bhs_data, typeb_data])

        assert fused.connection_time_minutes == 45
        assert fused.last_scan_location == "TRANSFER_01"
        assert fused.weight_kg == 23.5


class TestEdgeCases:
    """Test edge cases in data fusion"""

    def test_empty_source_list(self):
        """Test fusing empty source list"""
        fused = DataFusionEngine.fuse_by_confidence([])
        assert fused is None

    def test_sources_with_all_none_values(self):
        """Test sources with no actual data"""
        source1 = BagData(bag_tag="0016123456789", confidence=0.95, source="Source1")
        source2 = BagData(bag_tag="0016123456789", confidence=0.90, source="Source2")

        fused = DataFusionEngine.fuse_by_confidence([source1, source2])

        # Should still create fused data with bag_tag
        assert fused.bag_tag == "0016123456789"

    def test_zero_confidence_source(self):
        """Test handling source with zero confidence"""
        high_conf = BagData(
            bag_tag="0016123456789",
            flight_number="UA1234",
            confidence=0.95,
            source="DCS"
        )

        zero_conf = BagData(
            bag_tag="0016123456789",
            flight_number="UA5678",
            confidence=0.0,  # Zero confidence
            source="Unknown"
        )

        fused = DataFusionEngine.fuse_by_confidence([high_conf, zero_conf])

        # Should pick high confidence value
        assert fused.flight_number == "UA1234"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
