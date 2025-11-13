"""
Data Fusion Engine
==================

Intelligently combines baggage data from multiple sources:
- Resolves conflicts between sources
- Calculates confidence scores
- Tracks data lineage
- Applies source priority rules

Version: 1.0.0
Date: 2025-11-13
"""

from typing import List, Dict, Optional, Any, Callable
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from loguru import logger

from models.canonical_bag import (
    CanonicalBag,
    DataSource,
    DataQuality,
    BagState,
    RiskLevel
)


def make_aware(dt: datetime) -> datetime:
    """Make a datetime timezone-aware (UTC) if it's naive"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class SourcePriority:
    """Priority rules for data sources"""
    source: DataSource
    priority: int  # Higher = more authoritative
    trust_score: float  # 0.0-1.0
    staleness_tolerance_minutes: int  # How old data can be


@dataclass
class ConflictResolution:
    """How a conflict was resolved"""
    field: str
    sources: List[DataSource]
    values: List[Any]
    chosen_value: Any
    chosen_source: DataSource
    resolution_strategy: str
    confidence: float


class DataFusionEngine:
    """
    Fuses data from multiple sources into canonical bag model

    Resolution strategies:
    - Source Priority: Use most authoritative source
    - Recency: Use most recent data
    - Consensus: Use value agreed by multiple sources
    - Completeness: Prefer more complete data
    - Custom Rules: Field-specific logic
    """

    # Default source priorities (higher = more authoritative)
    DEFAULT_PRIORITIES = {
        DataSource.BHS: SourcePriority(
            source=DataSource.BHS,
            priority=10,
            trust_score=0.95,
            staleness_tolerance_minutes=5
        ),
        DataSource.DCS: SourcePriority(
            source=DataSource.DCS,
            priority=9,
            trust_score=0.90,
            staleness_tolerance_minutes=15
        ),
        DataSource.WORLDTRACER: SourcePriority(
            source=DataSource.WORLDTRACER,
            priority=8,
            trust_score=0.85,
            staleness_tolerance_minutes=60
        ),
        DataSource.TYPE_B: SourcePriority(
            source=DataSource.TYPE_B,
            priority=7,
            trust_score=0.80,
            staleness_tolerance_minutes=30
        ),
        DataSource.BAGGAGE_XML: SourcePriority(
            source=DataSource.BAGGAGE_XML,
            priority=6,
            trust_score=0.75,
            staleness_tolerance_minutes=30
        ),
        DataSource.AGENT: SourcePriority(
            source=DataSource.AGENT,
            priority=5,
            trust_score=0.70,
            staleness_tolerance_minutes=120
        ),
        DataSource.MANUAL_ENTRY: SourcePriority(
            source=DataSource.MANUAL_ENTRY,
            priority=4,
            trust_score=0.65,
            staleness_tolerance_minutes=240
        ),
    }

    # Field-specific authority (which source is most authoritative for each field)
    FIELD_AUTHORITY = {
        # BHS is authoritative for scan/location data
        "current_location": DataSource.BHS,
        "last_scan_at": DataSource.BHS,
        "last_scan_type": DataSource.BHS,
        "scan_count": DataSource.BHS,
        "license_plate": DataSource.BHS,

        # DCS is authoritative for passenger/booking data
        "passenger_name": DataSource.DCS,
        "pnr": DataSource.DCS,
        "ticket_number": DataSource.DCS,
        "contact": DataSource.DCS,
        "service_class": DataSource.DCS,
        "checked_in_at": DataSource.DCS,

        # WorldTracer is authoritative for exception/irregularity data
        "exception_status": DataSource.WORLDTRACER,
        "is_mishandled": DataSource.WORLDTRACER,

        # Type B messages for flight operational data
        "expected_departure": DataSource.TYPE_B,
        "actual_departure": DataSource.TYPE_B,
        "expected_arrival": DataSource.TYPE_B,
        "actual_arrival": DataSource.TYPE_B,
    }

    def __init__(self, custom_priorities: Optional[Dict[DataSource, SourcePriority]] = None):
        """
        Initialize fusion engine

        Args:
            custom_priorities: Override default source priorities
        """
        self.priorities = custom_priorities or self.DEFAULT_PRIORITIES
        self.conflict_log: List[ConflictResolution] = []
        logger.info("DataFusionEngine initialized")

    def fuse(
        self,
        bag_data_from_sources: Dict[DataSource, Dict[str, Any]],
        existing_bag: Optional[CanonicalBag] = None
    ) -> CanonicalBag:
        """
        Fuse data from multiple sources into canonical bag

        Args:
            bag_data_from_sources: Dict mapping DataSource to raw data dict
            existing_bag: Existing canonical bag to update (optional)

        Returns:
            Fused CanonicalBag instance
        """
        logger.info(
            f"Fusing data from {len(bag_data_from_sources)} sources: "
            f"{[s.value for s in bag_data_from_sources.keys()]}"
        )

        # Start with existing bag or create new
        if existing_bag:
            fused_data = existing_bag.model_dump()
        else:
            fused_data = {}

        # Track data quality
        data_quality = DataQuality(
            data_sources=list(bag_data_from_sources.keys()),
            source_timestamps={}
        )

        # Get timestamps for each source
        for source, data in bag_data_from_sources.items():
            timestamp = data.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
            # Ensure timestamp is timezone-aware
            data_quality.source_timestamps[source.value] = make_aware(timestamp)

        # Collect all field values from all sources
        field_values: Dict[str, List[tuple[DataSource, Any, datetime]]] = {}

        for source, data in bag_data_from_sources.items():
            timestamp = data_quality.source_timestamps[source.value]

            for field, value in data.items():
                if field == 'timestamp':
                    continue  # Skip timestamp field itself

                if value is not None and value != "":
                    if field not in field_values:
                        field_values[field] = []
                    field_values[field].append((source, value, timestamp))

        # Resolve conflicts and build fused data
        for field, values in field_values.items():
            if len(values) == 1:
                # No conflict - single source
                source, value, timestamp = values[0]
                fused_data[field] = value
            else:
                # Conflict - multiple sources have different values
                # Check if values are actually different
                unique_values = set(str(v[1]) for v in values)

                if len(unique_values) == 1:
                    # Same value from all sources - no real conflict
                    fused_data[field] = values[0][1]
                else:
                    # Real conflict - resolve it
                    resolved = self._resolve_conflict(field, values)
                    fused_data[field] = resolved.chosen_value

                    # Track conflict
                    data_quality.conflicts_detected.append(field)
                    data_quality.conflicts_resolved[field] = resolved.resolution_strategy
                    self.conflict_log.append(resolved)

        # Calculate data quality metrics
        data_quality = self._calculate_data_quality(
            fused_data,
            bag_data_from_sources,
            data_quality
        )

        # Create or update canonical bag
        fused_data['data_quality'] = data_quality.model_dump()

        # Store raw data from sources for debugging
        fused_data['raw_data'] = {
            source.value: data
            for source, data in bag_data_from_sources.items()
        }

        # Update timestamps
        fused_data['updated_at'] = datetime.now()

        try:
            if existing_bag:
                # Update existing bag
                for field, value in fused_data.items():
                    setattr(existing_bag, field, value)
                fused_bag = existing_bag
            else:
                # Create new bag
                fused_bag = CanonicalBag(**fused_data)

            logger.info(
                f"Data fusion complete for bag {fused_bag.bag_tag}: "
                f"confidence={fused_bag.data_quality.confidence:.2f}, "
                f"conflicts={len(data_quality.conflicts_detected)}"
            )

            return fused_bag

        except Exception as e:
            logger.error(f"Failed to create canonical bag: {e}")
            logger.debug(f"Fused data: {fused_data}")
            raise

    def _resolve_conflict(
        self,
        field: str,
        values: List[tuple[DataSource, Any, datetime]]
    ) -> ConflictResolution:
        """
        Resolve conflict between multiple source values

        Args:
            field: Field name with conflict
            values: List of (source, value, timestamp) tuples

        Returns:
            ConflictResolution with chosen value
        """
        sources = [v[0] for v in values]
        field_values = [v[1] for v in values]
        timestamps = [v[2] for v in values]

        # Strategy 1: Field-specific authority
        if field in self.FIELD_AUTHORITY:
            authoritative_source = self.FIELD_AUTHORITY[field]

            for i, source in enumerate(sources):
                if source == authoritative_source:
                    # Check if data is not too stale
                    priority = self.priorities.get(source)
                    if priority:
                        staleness = (make_aware(datetime.now()) - make_aware(timestamps[i])).total_seconds() / 60
                        if staleness <= priority.staleness_tolerance_minutes:
                            return ConflictResolution(
                                field=field,
                                sources=sources,
                                values=field_values,
                                chosen_value=field_values[i],
                                chosen_source=source,
                                resolution_strategy="field_authority",
                                confidence=priority.trust_score
                            )

        # Strategy 2: Source priority
        best_priority = -1
        best_index = 0

        for i, source in enumerate(sources):
            priority = self.priorities.get(source)
            if priority and priority.priority > best_priority:
                # Check staleness
                staleness = (make_aware(datetime.now()) - make_aware(timestamps[i])).total_seconds() / 60
                if staleness <= priority.staleness_tolerance_minutes:
                    best_priority = priority.priority
                    best_index = i

        if best_priority > -1:
            source = sources[best_index]
            priority = self.priorities[source]
            return ConflictResolution(
                field=field,
                sources=sources,
                values=field_values,
                chosen_value=field_values[best_index],
                chosen_source=source,
                resolution_strategy="source_priority",
                confidence=priority.trust_score
            )

        # Strategy 3: Most recent
        most_recent_index = timestamps.index(max(timestamps))

        return ConflictResolution(
            field=field,
            sources=sources,
            values=field_values,
            chosen_value=field_values[most_recent_index],
            chosen_source=sources[most_recent_index],
            resolution_strategy="most_recent",
            confidence=0.7
        )

    def _calculate_data_quality(
        self,
        fused_data: Dict[str, Any],
        source_data: Dict[DataSource, Dict[str, Any]],
        data_quality: DataQuality
    ) -> DataQuality:
        """Calculate data quality metrics"""

        # Count populated fields
        total_fields = len(CanonicalBag.model_fields)
        populated_fields = sum(1 for v in fused_data.values() if v is not None and v != "")
        data_quality.completeness = populated_fields / total_fields

        # Calculate confidence based on:
        # 1. Source trust scores
        # 2. Number of sources
        # 3. Conflict resolution confidence

        source_trust_scores = []
        for source in source_data.keys():
            if source in self.priorities:
                source_trust_scores.append(self.priorities[source].trust_score)

        if source_trust_scores:
            avg_trust = sum(source_trust_scores) / len(source_trust_scores)
        else:
            avg_trust = 0.5

        # Bonus for multiple sources
        source_bonus = min(0.1, len(source_data) * 0.02)

        # Penalty for conflicts
        conflict_penalty = len(data_quality.conflicts_detected) * 0.03

        # Penalty for low completeness
        completeness_factor = data_quality.completeness

        confidence = (avg_trust * 0.6 + completeness_factor * 0.3 + source_bonus) - conflict_penalty

        data_quality.confidence = max(0.0, min(1.0, confidence))
        data_quality.accuracy = avg_trust

        # Calculate timeliness
        if data_quality.source_timestamps:
            most_recent = max(data_quality.source_timestamps.values())
            staleness_minutes = (make_aware(datetime.now()) - make_aware(most_recent)).total_seconds() / 60

            # Timeliness decays with staleness
            if staleness_minutes < 5:
                timeliness = 1.0
            elif staleness_minutes < 30:
                timeliness = 0.9
            elif staleness_minutes < 60:
                timeliness = 0.7
            elif staleness_minutes < 240:
                timeliness = 0.5
            else:
                timeliness = 0.3

            data_quality.timeliness = timeliness
        else:
            data_quality.timeliness = 0.5

        return data_quality

    def merge_update(
        self,
        existing_bag: CanonicalBag,
        update_data: Dict[str, Any],
        source: DataSource
    ) -> CanonicalBag:
        """
        Merge an update from a single source into existing bag

        Args:
            existing_bag: Current canonical bag
            update_data: Update data from source
            source: Which source the update came from

        Returns:
            Updated canonical bag
        """
        # Convert existing bag to source data format
        sources_data = {
            DataSource.BHS: existing_bag.raw_data.get('BHS', {}),
            source: update_data
        }

        # Fuse with existing bag as base
        return self.fuse(sources_data, existing_bag)

    def get_conflict_summary(self) -> Dict[str, Any]:
        """Get summary of conflicts encountered"""
        if not self.conflict_log:
            return {"total_conflicts": 0}

        total = len(self.conflict_log)

        # Count by resolution strategy
        strategies = {}
        for conflict in self.conflict_log:
            strat = conflict.resolution_strategy
            strategies[strat] = strategies.get(strat, 0) + 1

        # Most conflicted fields
        field_conflicts = {}
        for conflict in self.conflict_log:
            field = conflict.field
            field_conflicts[field] = field_conflicts.get(field, 0) + 1

        most_conflicted = sorted(
            field_conflicts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "total_conflicts": total,
            "resolution_strategies": strategies,
            "most_conflicted_fields": dict(most_conflicted),
            "avg_confidence": sum(c.confidence for c in self.conflict_log) / total
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def enrich_with_defaults(data: Dict[str, Any], source: DataSource) -> Dict[str, Any]:
    """
    Enrich incomplete data with sensible defaults

    Args:
        data: Raw data from source
        source: Which source the data came from

    Returns:
        Enriched data dict
    """
    enriched = data.copy()

    # Add default bag type if missing
    if 'bag_type' not in enriched:
        enriched['bag_type'] = 'CHECKED'

    # Add default bag sequence if missing
    if 'bag_sequence' not in enriched:
        enriched['bag_sequence'] = 1

    if 'total_bags' not in enriched:
        enriched['total_bags'] = 1

    # Add default risk level if missing
    if 'risk_level' not in enriched:
        enriched['risk_level'] = 'NONE'

    # Add timestamp if missing
    if 'timestamp' not in enriched:
        enriched['timestamp'] = datetime.now()

    # Add is_tracked flag
    if 'is_tracked' not in enriched:
        enriched['is_tracked'] = True

    return enriched


def infer_missing_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Infer missing fields from available data

    Args:
        data: Partial bag data

    Returns:
        Data with inferred fields
    """
    inferred = data.copy()

    # Infer passenger first/last name from full name
    if 'passenger_name' in inferred and '/' in inferred['passenger_name']:
        parts = inferred['passenger_name'].split('/')
        if len(parts) >= 2:
            if 'passenger_last_name' not in inferred:
                inferred['passenger_last_name'] = parts[0].strip()
            if 'passenger_first_name' not in inferred:
                inferred['passenger_first_name'] = parts[1].strip()

    # Infer state from other indicators
    if 'current_state' not in inferred:
        if inferred.get('claimed_at'):
            inferred['current_state'] = 'CLAIMED'
        elif inferred.get('exception_status'):
            inferred['current_state'] = 'EXCEPTION'
        elif inferred.get('last_scan_type') == 'LOADING':
            inferred['current_state'] = 'LOADED'
        elif inferred.get('checked_in_at'):
            inferred['current_state'] = 'CHECKED_IN'

    # Infer is_transfer from inbound_flight presence
    if 'inbound_flight' in inferred and inferred['inbound_flight']:
        inferred['bag_type'] = 'TRANSFER'

    return inferred
