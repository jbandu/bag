"""
Data Validation Layer
=====================

Validates canonical bag data for:
- IATA standards compliance
- Business rule adherence
- Data quality checks
- Anomaly detection

Version: 1.0.0
Date: 2025-11-13
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from loguru import logger
import re

from models.canonical_bag import (
    CanonicalBag,
    BagState,
    RiskLevel,
    ExceptionType,
    DataSource
)


def make_aware(dt: datetime) -> datetime:
    """Make a datetime timezone-aware (UTC) if it's naive"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    severity: str  # ERROR, WARNING, INFO
    category: str  # IATA, BUSINESS_RULE, DATA_QUALITY, ANOMALY
    field: Optional[str]
    message: str
    value: Optional[Any] = None
    expected: Optional[Any] = None
    rule_code: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]
    info: List[ValidationIssue]
    confidence_score: float  # 0.0-1.0
    requires_human_review: bool = False


class DataValidator:
    """
    Validates canonical bag data against IATA standards and business rules
    """

    # IATA standard patterns
    IATA_BAG_TAG_PATTERN = r"^[0-9]{10}$"
    IATA_AIRPORT_CODE_PATTERN = r"^[A-Z]{3}$"
    IATA_AIRLINE_CODE_PATTERN = r"^[A-Z0-9]{2,3}$"
    IATA_FLIGHT_NUMBER_PATTERN = r"^[0-9]{1,4}$"

    # Business rule thresholds
    MAX_WEIGHT_KG = 32  # Standard max weight
    MAX_OVERWEIGHT_KG = 50  # Absolute max
    MAX_BAG_SEQUENCE = 15  # Max bags per passenger
    MAX_SCAN_GAP_HOURS = 24  # Max time between scans
    MAX_JOURNEY_LEGS = 5  # Max connection segments

    def __init__(self):
        """Initialize validator"""
        self.validation_history: List[ValidationResult] = []
        logger.info("DataValidator initialized")

    def validate(self, bag: CanonicalBag) -> ValidationResult:
        """
        Validate canonical bag data

        Args:
            bag: CanonicalBag instance to validate

        Returns:
            ValidationResult with all issues found
        """
        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []
        info: List[ValidationIssue] = []

        # Run all validation checks
        errors.extend(self._validate_iata_compliance(bag))
        warnings.extend(self._validate_business_rules(bag))
        issues = self._validate_data_quality(bag)
        errors.extend([i for i in issues if i.severity == "ERROR"])
        warnings.extend([i for i in issues if i.severity == "WARNING"])
        info.extend([i for i in issues if i.severity == "INFO"])

        anomalies = self._detect_anomalies(bag)
        warnings.extend(anomalies)

        # Calculate confidence score
        confidence = self._calculate_confidence(bag, errors, warnings)

        # Determine if human review needed
        requires_review = (
            len(errors) > 0 or
            len(warnings) > 3 or
            confidence < 0.7 or
            bag.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )

        result = ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info,
            confidence_score=confidence,
            requires_human_review=requires_review
        )

        self.validation_history.append(result)

        if not result.is_valid:
            logger.warning(
                f"Validation failed for bag {bag.bag_tag}: "
                f"{len(errors)} errors, {len(warnings)} warnings"
            )
        else:
            logger.debug(
                f"Validation passed for bag {bag.bag_tag}: confidence={confidence:.2f}"
            )

        return result

    def _validate_iata_compliance(self, bag: CanonicalBag) -> List[ValidationIssue]:
        """Validate IATA standard compliance"""
        issues: List[ValidationIssue] = []

        # Validate bag tag format
        if not re.match(self.IATA_BAG_TAG_PATTERN, bag.bag_tag):
            issues.append(ValidationIssue(
                severity="ERROR",
                category="IATA",
                field="bag_tag",
                message="Bag tag does not match IATA 10-digit format",
                value=bag.bag_tag,
                expected="10-digit numeric",
                rule_code="IATA-001"
            ))

        # Validate airport codes
        for field, airport in [
            ("origin", bag.origin),
            ("destination", bag.destination)
        ]:
            if not re.match(self.IATA_AIRPORT_CODE_PATTERN, airport.iata_code):
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="IATA",
                    field=field,
                    message=f"Invalid IATA airport code: {airport.iata_code}",
                    value=airport.iata_code,
                    expected="3-letter uppercase",
                    rule_code="IATA-002"
                ))

        # Validate intermediate stops
        for i, stop in enumerate(bag.intermediate_stops):
            if not re.match(self.IATA_AIRPORT_CODE_PATTERN, stop.iata_code):
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="IATA",
                    field=f"intermediate_stops[{i}]",
                    message=f"Invalid intermediate airport code: {stop.iata_code}",
                    value=stop.iata_code,
                    expected="3-letter uppercase",
                    rule_code="IATA-002"
                ))

        # Validate airline code
        if not re.match(self.IATA_AIRLINE_CODE_PATTERN, bag.outbound_flight.airline_code):
            issues.append(ValidationIssue(
                severity="ERROR",
                category="IATA",
                field="outbound_flight.airline_code",
                message=f"Invalid IATA airline code: {bag.outbound_flight.airline_code}",
                value=bag.outbound_flight.airline_code,
                expected="2-3 character alphanumeric",
                rule_code="IATA-003"
            ))

        # Validate flight number
        if not re.match(self.IATA_FLIGHT_NUMBER_PATTERN, bag.outbound_flight.flight_number):
            issues.append(ValidationIssue(
                severity="ERROR",
                category="IATA",
                field="outbound_flight.flight_number",
                message=f"Invalid flight number: {bag.outbound_flight.flight_number}",
                value=bag.outbound_flight.flight_number,
                expected="1-4 digits",
                rule_code="IATA-004"
            ))

        # Validate inbound flight if present
        if bag.inbound_flight:
            if not re.match(self.IATA_AIRLINE_CODE_PATTERN, bag.inbound_flight.airline_code):
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="IATA",
                    field="inbound_flight.airline_code",
                    message=f"Invalid inbound airline code: {bag.inbound_flight.airline_code}",
                    value=bag.inbound_flight.airline_code,
                    rule_code="IATA-003"
                ))

        return issues

    def _validate_business_rules(self, bag: CanonicalBag) -> List[ValidationIssue]:
        """Validate business rules"""
        issues: List[ValidationIssue] = []

        # Rule: Origin and destination must be different
        if bag.origin.iata_code == bag.destination.iata_code:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="BUSINESS_RULE",
                field="origin/destination",
                message="Origin and destination are the same",
                value=f"{bag.origin.iata_code} -> {bag.destination.iata_code}",
                rule_code="BR-001"
            ))

        # Rule: Bag sequence must not exceed total bags
        if bag.bag_sequence > bag.total_bags:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="BUSINESS_RULE",
                field="bag_sequence",
                message="Bag sequence exceeds total bags",
                value=f"{bag.bag_sequence}/{bag.total_bags}",
                rule_code="BR-002"
            ))

        # Rule: Total bags should be reasonable
        if bag.total_bags > self.MAX_BAG_SEQUENCE:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="BUSINESS_RULE",
                field="total_bags",
                message=f"Unusually high number of bags: {bag.total_bags}",
                value=bag.total_bags,
                expected=f"<= {self.MAX_BAG_SEQUENCE}",
                rule_code="BR-003"
            ))

        # Rule: Weight limits
        if bag.dimensions and bag.dimensions.weight_kg:
            if bag.dimensions.weight_kg > self.MAX_OVERWEIGHT_KG:
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="BUSINESS_RULE",
                    field="dimensions.weight_kg",
                    message=f"Bag weight exceeds absolute maximum: {bag.dimensions.weight_kg}kg",
                    value=bag.dimensions.weight_kg,
                    expected=f"<= {self.MAX_OVERWEIGHT_KG}kg",
                    rule_code="BR-004"
                ))
            elif bag.dimensions.weight_kg > self.MAX_WEIGHT_KG:
                # Just a note for standard overweight
                issues.append(ValidationIssue(
                    severity="INFO",
                    category="BUSINESS_RULE",
                    field="dimensions.weight_kg",
                    message=f"Bag is overweight (standard limit {self.MAX_WEIGHT_KG}kg)",
                    value=bag.dimensions.weight_kg,
                    rule_code="BR-004"
                ))

        # Rule: Journey must have reasonable number of legs
        legs = bag.get_journey_legs()
        if len(legs) > self.MAX_JOURNEY_LEGS:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="BUSINESS_RULE",
                field="intermediate_stops",
                message=f"Journey has too many legs: {len(legs)}",
                value=len(legs),
                expected=f"<= {self.MAX_JOURNEY_LEGS}",
                rule_code="BR-005"
            ))

        # Rule: Transfer bags must have inbound flight
        if bag.is_transfer_bag() and not bag.inbound_flight:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="BUSINESS_RULE",
                field="inbound_flight",
                message="Transfer bag missing inbound flight information",
                rule_code="BR-006"
            ))

        # Rule: Check timeline consistency
        if bag.checked_in_at and bag.expected_departure:
            if bag.checked_in_at > bag.expected_departure:
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="BUSINESS_RULE",
                    field="checked_in_at",
                    message="Bag checked in after flight departure time",
                    value=bag.checked_in_at,
                    expected=f"< {bag.expected_departure}",
                    rule_code="BR-007"
                ))

        if bag.expected_departure and bag.expected_arrival:
            if bag.expected_arrival <= bag.expected_departure:
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="BUSINESS_RULE",
                    field="expected_arrival",
                    message="Arrival time before or equal to departure time",
                    rule_code="BR-008"
                ))

        # Rule: Claimed bags should have claim timestamp
        if bag.current_state == BagState.CLAIMED and not bag.claimed_at:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="BUSINESS_RULE",
                field="claimed_at",
                message="Bag marked as claimed but no claim timestamp",
                rule_code="BR-009"
            ))

        # Rule: Exception status consistency
        if bag.current_state == BagState.EXCEPTION and not bag.exception_status:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="BUSINESS_RULE",
                field="exception_status",
                message="Bag in exception state but no exception case details",
                rule_code="BR-010"
            ))

        return issues

    def _validate_data_quality(self, bag: CanonicalBag) -> List[ValidationIssue]:
        """Validate data quality"""
        issues: List[ValidationIssue] = []

        # Check required fields completeness
        required_fields = {
            "passenger_name": bag.passenger_name,
            "origin": bag.origin,
            "destination": bag.destination,
            "outbound_flight": bag.outbound_flight,
        }

        for field, value in required_fields.items():
            if not value:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="DATA_QUALITY",
                    field=field,
                    message=f"Required field missing: {field}",
                    rule_code="DQ-001"
                ))

        # Check data quality metadata
        if bag.data_quality.confidence < 0.5:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="DATA_QUALITY",
                field="data_quality.confidence",
                message=f"Low data confidence: {bag.data_quality.confidence:.2f}",
                value=bag.data_quality.confidence,
                expected=">= 0.5",
                rule_code="DQ-002"
            ))

        # Check for data conflicts
        if bag.data_quality.conflicts_detected:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="DATA_QUALITY",
                field="data_quality.conflicts_detected",
                message=f"Data conflicts detected in {len(bag.data_quality.conflicts_detected)} fields",
                value=bag.data_quality.conflicts_detected,
                rule_code="DQ-003"
            ))

        # Check data freshness
        if bag.last_scan_at:
            hours_since_scan = (make_aware(datetime.now()) - make_aware(bag.last_scan_at)).total_seconds() / 3600
            if hours_since_scan > self.MAX_SCAN_GAP_HOURS:
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="DATA_QUALITY",
                    field="last_scan_at",
                    message=f"No scan for {hours_since_scan:.1f} hours",
                    value=hours_since_scan,
                    expected=f"< {self.MAX_SCAN_GAP_HOURS} hours",
                    rule_code="DQ-004"
                ))

        # Check passenger name format
        if bag.passenger_name:
            if "/" not in bag.passenger_name:
                issues.append(ValidationIssue(
                    severity="INFO",
                    category="DATA_QUALITY",
                    field="passenger_name",
                    message="Passenger name not in SURNAME/FIRSTNAME format",
                    value=bag.passenger_name,
                    expected="SURNAME/FIRSTNAME FORMAT",
                    rule_code="DQ-005"
                ))

        return issues

    def _detect_anomalies(self, bag: CanonicalBag) -> List[ValidationIssue]:
        """Detect data anomalies"""
        issues: List[ValidationIssue] = []

        # Anomaly: Bag at wrong location
        if bag.current_location and bag.expected_location:
            if bag.current_location.location_code != bag.expected_location.location_code:
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="ANOMALY",
                    field="current_location",
                    message="Bag not at expected location",
                    value=bag.current_location.location_code,
                    expected=bag.expected_location.location_code,
                    rule_code="AN-001"
                ))

        # Anomaly: High risk without exception case
        if bag.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] and not bag.exception_status:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="ANOMALY",
                field="risk_level",
                message=f"High risk ({bag.risk_level.value}) without exception case",
                value=bag.risk_level.value,
                rule_code="AN-002"
            ))

        # Anomaly: State transition issues
        invalid_transitions = {
            BagState.CLAIMED: [BagState.CHECKED_IN, BagState.IN_SYSTEM, BagState.SORTED],
            BagState.LOST: [BagState.CLAIMED],
        }

        if bag.previous_state and bag.current_state in invalid_transitions:
            if bag.previous_state in invalid_transitions[bag.current_state]:
                issues.append(ValidationIssue(
                    severity="WARNING",
                    category="ANOMALY",
                    field="current_state",
                    message=f"Unusual state transition: {bag.previous_state.value} -> {bag.current_state.value}",
                    rule_code="AN-003"
                ))

        # Anomaly: Overdue without tracking
        if bag.is_overdue() and bag.is_tracked and not bag.exception_status:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="ANOMALY",
                field="expected_arrival",
                message="Bag is overdue but no exception case opened",
                rule_code="AN-004"
            ))

        # Anomaly: Multiple scans at same location in short time
        if bag.scan_count > 10:
            # Check for duplicate scans (would need scan history)
            issues.append(ValidationIssue(
                severity="INFO",
                category="ANOMALY",
                field="scan_count",
                message=f"High number of scans: {bag.scan_count}",
                value=bag.scan_count,
                rule_code="AN-005"
            ))

        return issues

    def _calculate_confidence(
        self,
        bag: CanonicalBag,
        errors: List[ValidationIssue],
        warnings: List[ValidationIssue]
    ) -> float:
        """Calculate overall confidence score"""

        # Start with base confidence from data quality
        confidence = bag.data_quality.confidence

        # Penalize for errors and warnings
        confidence -= len(errors) * 0.15
        confidence -= len(warnings) * 0.05

        # Bonus for complete data
        if bag.data_quality.completeness > 0.9:
            confidence += 0.05

        # Bonus for multiple data sources
        if len(bag.data_quality.data_sources) > 2:
            confidence += 0.05

        # Penalize for conflicts
        if bag.data_quality.conflicts_detected:
            confidence -= len(bag.data_quality.conflicts_detected) * 0.03

        # Ensure within bounds
        return max(0.0, min(1.0, confidence))

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation statistics"""
        if not self.validation_history:
            return {"total_validations": 0}

        total = len(self.validation_history)
        valid = sum(1 for v in self.validation_history if v.is_valid)
        avg_confidence = sum(v.confidence_score for v in self.validation_history) / total

        return {
            "total_validations": total,
            "valid_count": valid,
            "invalid_count": total - valid,
            "validation_rate": valid / total,
            "avg_confidence": avg_confidence,
            "requires_review_count": sum(1 for v in self.validation_history if v.requires_human_review)
        }


# ============================================================================
# SPECIALIZED VALIDATORS
# ============================================================================

class IATAValidator:
    """IATA-specific validation functions"""

    # Known IATA airport codes (sample - would be a full database in production)
    VALID_AIRPORTS = {
        "LAX", "JFK", "ORD", "DFW", "DEN", "SFO", "SEA", "LAS", "MCO", "MIA",
        "LHR", "CDG", "FRA", "AMS", "DXB", "SIN", "HKG", "NRT", "ICN", "PEK",
        "SYD", "MEL", "YYZ", "YVR", "GRU", "MEX", "BOM", "DEL", "IST", "MAD"
    }

    # Known IATA airline codes (sample)
    VALID_AIRLINES = {
        "AA", "UA", "DL", "WN", "AS", "B6", "NK", "F9",  # US
        "BA", "AF", "LH", "KL", "IB", "AZ",  # Europe
        "EK", "QR", "EY", "SV",  # Middle East
        "SQ", "CX", "NH", "JL", "KE",  # Asia Pacific
        "QF", "NZ", "AC", "AM"  # Others
    }

    @staticmethod
    def is_valid_airport_code(code: str) -> bool:
        """Check if airport code is valid"""
        return code in IATAValidator.VALID_AIRPORTS

    @staticmethod
    def is_valid_airline_code(code: str) -> bool:
        """Check if airline code is valid"""
        return code in IATAValidator.VALID_AIRLINES

    @staticmethod
    def validate_bag_tag_checksum(bag_tag: str) -> bool:
        """Validate bag tag checksum using IATA algorithm"""
        if len(bag_tag) != 10 or not bag_tag.isdigit():
            return False

        # IATA uses modulo 7 checksum on last digit
        # This is a simplified version
        digits = [int(d) for d in bag_tag[:9]]
        check_digit = int(bag_tag[9])

        # Calculate checksum
        calculated = sum(digits) % 7

        return calculated == check_digit
