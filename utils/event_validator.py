"""
Event Sequence Validator
========================

Validates baggage scan event sequences for correctness, detects anomalies,
and identifies missing scans.

Version: 1.0.0
Date: 2024-11-13
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from loguru import logger

from models.event_ontology import (
    ScanEventType,
    ScanAnomaly,
    ValidationResult,
    SequenceRule,
    SEQUENCE_RULES,
    get_event_definition,
    get_sequence_rule
)


class EventSequenceValidator:
    """
    Validates baggage scan event sequences

    Features:
    - Checks if scan sequence is valid
    - Detects missing scans (gaps)
    - Flags anomalies (unexpected scans)
    - Validates timing between scans
    """

    def __init__(self):
        """Initialize validator"""
        self.sequence_rules = SEQUENCE_RULES
        logger.info("EventSequenceValidator initialized")

    def validate_sequence(
        self,
        events: List[Dict[str, Any]],
        bag_tag: str
    ) -> ValidationResult:
        """
        Validate a sequence of scan events for a bag

        Args:
            events: List of scan events (must be chronologically ordered)
            bag_tag: Baggage tag number

        Returns:
            ValidationResult with validation details
        """
        if not events:
            return ValidationResult(
                is_valid=False,
                anomalies=[],
                missing_scans=[],
                confidence=1.0,
                reasoning="No scan events found for bag"
            )

        anomalies: List[ScanAnomaly] = []
        missing_scans: List[ScanEventType] = []
        reasoning_parts: List[str] = []

        # Sort events by timestamp to ensure chronological order
        sorted_events = sorted(events, key=lambda e: e.get('timestamp', ''))

        logger.info(f"Validating sequence for bag {bag_tag} with {len(sorted_events)} events")

        # Validate each event in sequence
        for i, event in enumerate(sorted_events):
            event_type = self._parse_event_type(event.get('scan_type'))

            if not event_type:
                logger.warning(f"Unknown scan type: {event.get('scan_type')}")
                continue

            # Get previous event if exists
            previous_event = sorted_events[i - 1] if i > 0 else None

            # Validate this event against previous
            event_anomalies = self._validate_single_event(
                event,
                event_type,
                previous_event,
                sorted_events[:i]  # All previous events
            )

            anomalies.extend(event_anomalies)

            # Check for missing expected scans
            if previous_event:
                missing = self._check_missing_scans(
                    previous_event,
                    event,
                    sorted_events[:i]
                )
                missing_scans.extend(missing)

        # Check for duplicate scans
        duplicates = self._detect_duplicates(sorted_events)
        if duplicates:
            anomalies.append(ScanAnomaly.DUPLICATE_SCAN)
            reasoning_parts.append(f"Found {len(duplicates)} duplicate scans")

        # Determine if sequence is valid
        is_valid = len(anomalies) == 0 and len(missing_scans) == 0

        # Calculate confidence based on anomalies
        confidence = self._calculate_confidence(anomalies, missing_scans)

        # Build reasoning
        if is_valid:
            reasoning = "Scan sequence is valid and follows expected pattern"
        else:
            reasoning_parts = []
            if anomalies:
                reasoning_parts.append(f"Detected {len(anomalies)} anomalies: {', '.join([a.value for a in anomalies])}")
            if missing_scans:
                reasoning_parts.append(f"Missing {len(missing_scans)} expected scans: {', '.join([s.value for s in missing_scans])}")
            reasoning = ". ".join(reasoning_parts)

        logger.info(f"Validation complete for {bag_tag}: valid={is_valid}, anomalies={len(anomalies)}, confidence={confidence}")

        return ValidationResult(
            is_valid=is_valid,
            anomalies=list(set(anomalies)),  # Remove duplicates
            missing_scans=list(set(missing_scans)),
            confidence=confidence,
            reasoning=reasoning
        )

    def _validate_single_event(
        self,
        event: Dict[str, Any],
        event_type: ScanEventType,
        previous_event: Optional[Dict[str, Any]],
        all_previous: List[Dict[str, Any]]
    ) -> List[ScanAnomaly]:
        """Validate a single event against sequence rules"""
        anomalies: List[ScanAnomaly] = []

        if not previous_event:
            # First event - validate it's a valid starting point
            if event_type not in [
                ScanEventType.CHECKIN,
                ScanEventType.MANUAL,
                ScanEventType.EXCEPTION
            ]:
                anomalies.append(ScanAnomaly.OUT_OF_SEQUENCE)
                logger.warning(f"Invalid first scan: {event_type.value}")
            return anomalies

        # Get sequence rule for this event type
        rule = get_sequence_rule(event_type)
        if not rule:
            # No rule defined, assume valid
            return anomalies

        # Get previous event type
        prev_type = self._parse_event_type(previous_event.get('scan_type'))
        if not prev_type:
            return anomalies

        # Check must_follow rule
        if rule.must_follow:
            prev_types_in_history = [
                self._parse_event_type(e.get('scan_type'))
                for e in all_previous
            ]
            if not any(req_type in prev_types_in_history for req_type in rule.must_follow):
                anomalies.append(ScanAnomaly.OUT_OF_SEQUENCE)
                logger.warning(
                    f"{event_type.value} requires one of {[t.value for t in rule.must_follow]} "
                    f"but found {[t.value for t in prev_types_in_history if t]}"
                )

        # Check cannot_follow rule
        if rule.cannot_follow and prev_type in rule.cannot_follow:
            anomalies.append(ScanAnomaly.OUT_OF_SEQUENCE)
            logger.warning(f"{event_type.value} cannot follow {prev_type.value}")

        # Check timing constraints
        time_anomalies = self._validate_timing(
            event,
            previous_event,
            rule
        )
        anomalies.extend(time_anomalies)

        return anomalies

    def _validate_timing(
        self,
        event: Dict[str, Any],
        previous_event: Dict[str, Any],
        rule: SequenceRule
    ) -> List[ScanAnomaly]:
        """Validate timing between events"""
        anomalies: List[ScanAnomaly] = []

        try:
            current_time = datetime.fromisoformat(event.get('timestamp', '').replace('Z', '+00:00'))
            previous_time = datetime.fromisoformat(previous_event.get('timestamp', '').replace('Z', '+00:00'))

            time_diff_minutes = (current_time - previous_time).total_seconds() / 60

            # Check max time constraint
            if rule.max_time_since_previous and time_diff_minutes > rule.max_time_since_previous:
                anomalies.append(ScanAnomaly.TIME_GAP)
                logger.warning(
                    f"Time gap of {time_diff_minutes:.1f} minutes exceeds maximum "
                    f"of {rule.max_time_since_previous} minutes"
                )

            # Check min time constraint
            if rule.min_time_since_previous and time_diff_minutes < rule.min_time_since_previous:
                anomalies.append(ScanAnomaly.OUT_OF_SEQUENCE)
                logger.warning(
                    f"Time gap of {time_diff_minutes:.1f} minutes is less than minimum "
                    f"of {rule.min_time_since_previous} minutes"
                )

        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing timestamps: {e}")

        return anomalies

    def _check_missing_scans(
        self,
        previous_event: Dict[str, Any],
        current_event: Dict[str, Any],
        all_previous: List[Dict[str, Any]]
    ) -> List[ScanEventType]:
        """Check for missing expected scans between events"""
        missing: List[ScanEventType] = []

        prev_type = self._parse_event_type(previous_event.get('scan_type'))
        if not prev_type:
            return missing

        # Get expected next scans from ontology
        prev_definition = get_event_definition(prev_type)
        if not prev_definition:
            return missing

        expected_scans = prev_definition.semantic_enrichment.expected_next_scans

        # Get current event type
        current_type = self._parse_event_type(current_event.get('scan_type'))
        if not current_type:
            return missing

        # Check if current scan is in expected list
        expected_types = [exp.scan_type for exp in expected_scans]

        # Also include alternative scans
        for exp in expected_scans:
            expected_types.extend(exp.alternative_scans)

        if current_type not in expected_types and expected_scans:
            # Current scan not in expected list
            # Check if it's a high-probability expected scan that's missing
            for expected in expected_scans:
                if expected.probability > 0.8 and expected.scan_type != current_type:
                    # Check if this expected scan already occurred
                    prev_scan_types = [
                        self._parse_event_type(e.get('scan_type'))
                        for e in all_previous
                    ]
                    if expected.scan_type not in prev_scan_types:
                        missing.append(expected.scan_type)
                        logger.info(
                            f"Expected {expected.scan_type.value} (prob={expected.probability}) "
                            f"between {prev_type.value} and {current_type.value}"
                        )

        return missing

    def _detect_duplicates(
        self,
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect duplicate scans"""
        duplicates: List[Dict[str, Any]] = []
        seen: Dict[str, List[datetime]] = {}

        for event in events:
            event_type = event.get('scan_type')
            location = event.get('location', '')
            timestamp = event.get('timestamp', '')

            try:
                event_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                continue

            key = f"{event_type}:{location}"

            if key in seen:
                # Check if this is a duplicate (within 5 minutes)
                for prev_time in seen[key]:
                    if abs((event_time - prev_time).total_seconds()) < 300:
                        duplicates.append(event)
                        logger.warning(f"Duplicate scan detected: {key} at {timestamp}")
                        break

            if key not in seen:
                seen[key] = []
            seen[key].append(event_time)

        return duplicates

    def _calculate_confidence(
        self,
        anomalies: List[ScanAnomaly],
        missing_scans: List[ScanEventType]
    ) -> float:
        """Calculate confidence in validation result"""
        # Start with perfect confidence
        confidence = 1.0

        # Reduce confidence for each anomaly
        anomaly_penalties = {
            ScanAnomaly.OUT_OF_SEQUENCE: 0.3,
            ScanAnomaly.DUPLICATE_SCAN: 0.1,
            ScanAnomaly.MISSING_EXPECTED: 0.2,
            ScanAnomaly.UNEXPECTED_LOCATION: 0.1,
            ScanAnomaly.TIME_GAP: 0.15,
            ScanAnomaly.WRONG_FLIGHT: 0.25,
            ScanAnomaly.ALREADY_CLAIMED: 0.4
        }

        for anomaly in anomalies:
            penalty = anomaly_penalties.get(anomaly, 0.1)
            confidence -= penalty

        # Reduce confidence for missing scans
        confidence -= len(missing_scans) * 0.1

        # Ensure confidence stays in valid range
        return max(0.0, min(1.0, confidence))

    def _parse_event_type(self, scan_type: Optional[str]) -> Optional[ScanEventType]:
        """Parse scan type string to enum"""
        if not scan_type:
            return None

        try:
            # Try direct match
            return ScanEventType(scan_type.upper())
        except ValueError:
            # Try fuzzy match
            scan_type_upper = scan_type.upper()
            for event_type in ScanEventType:
                if event_type.value in scan_type_upper or scan_type_upper in event_type.value:
                    return event_type
            return None

    def get_next_expected_scans(
        self,
        last_event_type: ScanEventType
    ) -> List[Dict[str, Any]]:
        """Get expected next scans for a given event type"""
        definition = get_event_definition(last_event_type)
        if not definition:
            return []

        expected = []
        for next_scan in definition.semantic_enrichment.expected_next_scans:
            expected.append({
                "scan_type": next_scan.scan_type.value,
                "location_type": next_scan.location_type.value,
                "time_window_minutes": next_scan.time_window_minutes,
                "probability": next_scan.probability,
                "alternatives": [alt.value for alt in next_scan.alternative_scans]
            })

        return expected
