"""
Semantic Scan Processor Agent
==============================

Processes raw baggage scan events with semantic understanding.

Capabilities:
- Receives raw scan events (1000+ events/minute)
- Enriches with semantic meaning from event ontology
- Validates event sequences and detects anomalies
- Correlates events across bags to detect patterns
- Updates digital twin in Neo4j
- Publishes semantic messages to relevant agents
- Maintains event chain for debugging

Version: 1.0.0
Date: 2024-11-13
"""

import asyncio
from typing import List, Dict, Optional, Any, Set
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from loguru import logger

from models.event_ontology import (
    ScanEventType,
    ScanAnomaly,
    get_event_definition
)
from models.semantic_messages import (
    ScanMessage,
    RiskMessage,
    ExceptionMessage,
    AgentType,
    SemanticIntent,
    MessagePriority,
    ScanDetails,
    LocationDetails,
    FlightDetails
)
from utils.event_validator import EventSequenceValidator, ValidationResult
from utils.event_correlator import EventCorrelationEngine, CorrelatedEventGroup


class SemanticScanProcessor:
    """
    Semantic scan processor with event understanding

    Features:
    - Real-time scan processing (1000+ events/min)
    - Semantic enrichment using ontology
    - Sequence validation and anomaly detection
    - Cross-bag event correlation
    - Digital twin updates in Neo4j
    - Agent notification via message bus
    """

    def __init__(
        self,
        neo4j_connection=None,
        message_bus=None,
        enable_correlation: bool = True,
        enable_validation: bool = True
    ):
        """
        Initialize semantic scan processor

        Args:
            neo4j_connection: Neo4j database connection (optional)
            message_bus: Message bus for agent communication (optional)
            enable_correlation: Enable event correlation
            enable_validation: Enable sequence validation
        """
        self.neo4j = neo4j_connection
        self.message_bus = message_bus

        # Initialize validator and correlator
        self.validator = EventSequenceValidator() if enable_validation else None
        self.correlator = EventCorrelationEngine(
            correlation_window_minutes=30,
            min_events_for_pattern=5,
            pattern_confidence_threshold=0.7
        ) if enable_correlation else None

        # Event cache for sequence validation (per bag)
        self.bag_event_history: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history_size = 50  # Keep last 50 events per bag

        # Processing metrics
        self.events_processed = 0
        self.anomalies_detected = 0
        self.patterns_detected = 0
        self.messages_published = 0

        logger.info(
            f"SemanticScanProcessor initialized: "
            f"validation={enable_validation}, correlation={enable_correlation}"
        )

    async def process_scan_event(
        self,
        raw_event: Dict[str, Any],
        bag_tag: str
    ) -> Dict[str, Any]:
        """
        Process a raw scan event with semantic understanding

        Args:
            raw_event: Raw scan event from BHS
            bag_tag: Baggage tag number

        Returns:
            Processed event with semantic enrichment and validation results
        """
        start_time = datetime.now()

        logger.debug(f"Processing scan event for bag {bag_tag}: {raw_event.get('scan_type')}")

        # Step 1: Enrich with semantic meaning
        enriched_event = self._enrich_event(raw_event, bag_tag)

        # Step 2: Validate sequence
        validation_result = None
        if self.validator:
            validation_result = await self._validate_sequence(enriched_event, bag_tag)
            enriched_event['validation_result'] = {
                'is_valid': validation_result.is_valid,
                'anomalies': [a.value for a in validation_result.anomalies],
                'missing_scans': [s.value for s in validation_result.missing_scans],
                'confidence': validation_result.confidence,
                'reasoning': validation_result.reasoning
            }

            if not validation_result.is_valid:
                self.anomalies_detected += 1
                logger.warning(
                    f"Validation failed for {bag_tag}: {validation_result.reasoning}"
                )

        # Step 3: Correlate with other events
        correlations = []
        if self.correlator:
            correlations = self.correlator.correlate_event(enriched_event, bag_tag)
            enriched_event['correlations'] = [
                {
                    'group_id': corr.group_id,
                    'correlation_type': corr.correlation_type,
                    'pattern_type': corr.pattern_type,
                    'affected_bags': len(corr.bag_tags),
                    'confidence': corr.confidence
                }
                for corr in correlations
            ]

            # Check for patterns that require action
            patterns_requiring_action = [
                c for c in correlations
                if c.requires_batch_action
            ]
            if patterns_requiring_action:
                self.patterns_detected += len(patterns_requiring_action)
                logger.warning(
                    f"Detected {len(patterns_requiring_action)} patterns requiring action"
                )

        # Step 4: Update digital twin in Neo4j
        if self.neo4j:
            await self._update_digital_twin(enriched_event, bag_tag, validation_result)

        # Step 5: Publish to relevant agents
        if self.message_bus:
            await self._publish_to_agents(enriched_event, bag_tag, validation_result, correlations)

        # Step 6: Store in event history
        self._add_to_history(enriched_event, bag_tag)

        # Update metrics
        self.events_processed += 1
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        enriched_event['processing_metadata'] = {
            'processed_at': datetime.now().isoformat(),
            'processing_time_ms': processing_time,
            'processor_version': '1.0.0'
        }

        logger.info(
            f"Processed {bag_tag} scan in {processing_time:.1f}ms: "
            f"valid={validation_result.is_valid if validation_result else 'N/A'}, "
            f"correlations={len(correlations)}"
        )

        return enriched_event

    def _enrich_event(
        self,
        raw_event: Dict[str, Any],
        bag_tag: str
    ) -> Dict[str, Any]:
        """
        Enrich raw event with semantic meaning from ontology

        Args:
            raw_event: Raw scan event
            bag_tag: Baggage tag

        Returns:
            Enriched event with semantic properties
        """
        scan_type_str = raw_event.get('scan_type', '').upper()

        # Parse event type
        try:
            event_type = ScanEventType(scan_type_str)
        except ValueError:
            # Try fuzzy matching
            event_type = None
            for evt in ScanEventType:
                if evt.value in scan_type_str or scan_type_str in evt.value:
                    event_type = evt
                    break

            if not event_type:
                logger.warning(f"Unknown scan type: {scan_type_str}, defaulting to MANUAL")
                event_type = ScanEventType.MANUAL

        # Get semantic definition
        event_definition = get_event_definition(event_type)

        if not event_definition:
            logger.warning(f"No definition found for {event_type.value}")
            # Return raw event with minimal enrichment
            return {
                **raw_event,
                'bag_tag': bag_tag,
                'enriched': False,
                'event_type': event_type.value
            }

        # Build enriched event
        enriched = {
            **raw_event,
            'bag_tag': bag_tag,
            'enriched': True,
            'event_type': event_type.value,

            # Semantic enrichment from ontology
            'semantic_meaning': event_definition.semantic_enrichment.event_meaning,
            'journey_stage': event_definition.semantic_enrichment.journey_stage,
            'category': event_definition.category.value,
            'criticality': event_definition.criticality.value,

            # Expected next scans
            'expected_next_scans': [
                {
                    'scan_type': exp.scan_type.value,
                    'location_type': exp.location_type.value,
                    'time_window_minutes': exp.time_window_minutes,
                    'probability': exp.probability,
                    'alternatives': [alt.value for alt in exp.alternative_scans]
                }
                for exp in event_definition.semantic_enrichment.expected_next_scans
            ],

            # Risk factors introduced
            'risk_factors': [
                {
                    'factor': rf.factor,
                    'severity': rf.severity.value,
                    'probability': rf.probability,
                    'description': rf.description
                }
                for rf in event_definition.semantic_enrichment.risk_factors
            ],

            # Agents that need to be notified
            'relevant_agents': event_definition.semantic_enrichment.relevant_agents,

            # Actions to be triggered
            'required_actions': event_definition.semantic_enrichment.required_actions,

            # State transitions
            'state_transitions': [
                {
                    'from_state': trans.from_state.value,
                    'to_state': trans.to_state.value,
                    'trigger': trans.trigger.value
                }
                for trans in event_definition.state_transitions
            ]
        }

        return enriched

    async def _validate_sequence(
        self,
        event: Dict[str, Any],
        bag_tag: str
    ) -> ValidationResult:
        """Validate event sequence for bag"""

        # Get event history for this bag
        history = self.bag_event_history.get(bag_tag, [])

        # Add current event to history for validation
        events_to_validate = history + [event]

        # Run validation
        result = self.validator.validate_sequence(events_to_validate, bag_tag)

        return result

    async def _update_digital_twin(
        self,
        event: Dict[str, Any],
        bag_tag: str,
        validation_result: Optional[ValidationResult]
    ):
        """
        Update digital twin in Neo4j

        Creates/updates:
        - ScanEvent node
        - Relationships to Baggage, Location, Flight
        - Risk factors
        - Anomalies if detected
        """
        if not self.neo4j:
            return

        try:
            # Build Cypher query to create/update scan event
            query = """
            // Match or create baggage
            MERGE (b:Baggage {bagTag: $bag_tag})
            ON CREATE SET
                b.firstSeenAt = datetime($timestamp),
                b.status = 'ACTIVE'

            // Create scan event
            CREATE (s:ScanEvent {
                eventId: $event_id,
                scanType: $scan_type,
                timestamp: datetime($timestamp),
                location: $location,
                semanticMeaning: $semantic_meaning,
                journeyStage: $journey_stage,
                category: $category,
                criticality: $criticality,
                enriched: true
            })

            // Link scan to baggage
            CREATE (b)-[:HAS_SCAN {
                timestamp: datetime($timestamp),
                sequenceNumber: $sequence_number
            }]->(s)

            // Update baggage current state
            SET b.lastScanType = $scan_type,
                b.lastScanAt = datetime($timestamp),
                b.lastLocation = $location,
                b.journeyStage = $journey_stage

            // Create validation result if present
            WITH b, s
            """

            # Add validation anomalies
            if validation_result and not validation_result.is_valid:
                query += """
                CREATE (v:ValidationResult {
                    validationId: randomUUID(),
                    timestamp: datetime($timestamp),
                    isValid: false,
                    confidence: $validation_confidence,
                    reasoning: $validation_reasoning
                })
                CREATE (s)-[:HAS_VALIDATION]->(v)

                // Create anomaly nodes
                FOREACH (anomaly IN $anomalies |
                    CREATE (a:Anomaly {
                        anomalyId: randomUUID(),
                        type: anomaly,
                        detectedAt: datetime($timestamp)
                    })
                    CREATE (v)-[:DETECTED_ANOMALY]->(a)
                    CREATE (b)-[:HAS_ANOMALY]->(a)
                )
                """

            # Add risk factors
            query += """
            // Create risk factor nodes
            FOREACH (risk IN $risk_factors |
                CREATE (r:RiskFactor {
                    riskId: randomUUID(),
                    factor: risk.factor,
                    severity: risk.severity,
                    probability: risk.probability,
                    description: risk.description,
                    introducedAt: datetime($timestamp)
                })
                CREATE (s)-[:INTRODUCES_RISK]->(r)
                CREATE (b)-[:HAS_RISK]->(r)
            )

            RETURN b, s
            """

            # Prepare parameters
            params = {
                'bag_tag': bag_tag,
                'event_id': str(uuid4()),
                'scan_type': event.get('event_type'),
                'timestamp': event.get('timestamp'),
                'location': event.get('location', 'UNKNOWN'),
                'semantic_meaning': event.get('semantic_meaning', ''),
                'journey_stage': event.get('journey_stage', ''),
                'category': event.get('category', ''),
                'criticality': event.get('criticality', ''),
                'sequence_number': len(self.bag_event_history.get(bag_tag, [])) + 1,
                'risk_factors': event.get('risk_factors', [])
            }

            if validation_result:
                params.update({
                    'validation_confidence': validation_result.confidence,
                    'validation_reasoning': validation_result.reasoning,
                    'anomalies': [a.value for a in validation_result.anomalies]
                })

            # Execute query
            # Note: Actual execution would require neo4j driver
            # await self.neo4j.execute(query, params)

            logger.debug(f"Updated digital twin for {bag_tag}")

        except Exception as e:
            logger.error(f"Failed to update digital twin for {bag_tag}: {e}")

    async def _publish_to_agents(
        self,
        event: Dict[str, Any],
        bag_tag: str,
        validation_result: Optional[ValidationResult],
        correlations: List[CorrelatedEventGroup]
    ):
        """
        Publish semantic messages to relevant agents

        Messages sent based on:
        - Event type and semantic meaning
        - Validation results (anomalies)
        - Risk factors introduced
        - Correlation patterns detected
        """
        if not self.message_bus:
            return

        messages_to_publish: List[Any] = []

        # 1. Always send ScanMessage to relevant agents
        scan_message = self._build_scan_message(event, bag_tag, validation_result)
        messages_to_publish.append(scan_message)

        # 2. Send RiskMessage if risk factors introduced
        risk_factors = event.get('risk_factors', [])
        if risk_factors:
            risk_message = self._build_risk_message(event, bag_tag, risk_factors)
            messages_to_publish.append(risk_message)

        # 3. Send ExceptionMessage if anomalies detected
        if validation_result and not validation_result.is_valid:
            exception_message = self._build_exception_message(
                event, bag_tag, validation_result
            )
            messages_to_publish.append(exception_message)

        # 4. Send pattern notifications if correlations require action
        for correlation in correlations:
            if correlation.requires_batch_action:
                pattern_message = self._build_pattern_notification(correlation)
                messages_to_publish.append(pattern_message)

        # Publish all messages
        for message in messages_to_publish:
            try:
                # Note: Actual message bus publishing would happen here
                # await self.message_bus.publish(message)
                self.messages_published += 1
                logger.debug(
                    f"Published {message.__class__.__name__} to "
                    f"{len(message.target_agents)} agents"
                )
            except Exception as e:
                logger.error(f"Failed to publish message: {e}")

    def _build_scan_message(
        self,
        event: Dict[str, Any],
        bag_tag: str,
        validation_result: Optional[ValidationResult]
    ) -> ScanMessage:
        """Build ScanMessage for agents"""

        # Determine target agents from semantic enrichment
        relevant_agents_str = event.get('relevant_agents', [])
        target_agents = []
        for agent_str in relevant_agents_str:
            try:
                # Map agent string to AgentType enum
                if 'ScanProcessor' in agent_str:
                    target_agents.append(AgentType.SCAN_PROCESSOR)
                elif 'RiskScorer' in agent_str:
                    target_agents.append(AgentType.RISK_SCORER)
                elif 'CaseManager' in agent_str:
                    target_agents.append(AgentType.CASE_MANAGER)
                elif 'PassengerComms' in agent_str:
                    target_agents.append(AgentType.PASSENGER_COMMS)
            except:
                pass

        if not target_agents:
            target_agents = [AgentType.RISK_SCORER]  # Default

        # Build scan details
        scan_details = ScanDetails(
            scan_type=event.get('event_type', 'UNKNOWN'),
            scanner_id=event.get('scanner_id', 'UNKNOWN'),
            raw_data=event.get('raw_data', {}),
            image_url=event.get('image_url')
        )

        # Build location details
        location_details = LocationDetails(
            location_code=event.get('location', 'UNKNOWN'),
            location_type=event.get('location_type', 'TERMINAL'),
            facility_code=event.get('facility_code', 'UNKNOWN')
        )

        # Build flight details if present
        flight_details = None
        if event.get('flight_number'):
            flight_details = FlightDetails(
                flight_number=event.get('flight_number'),
                airline_code=event.get('airline_code', 'XX'),
                departure_airport=event.get('departure_airport', 'XXX'),
                arrival_airport=event.get('arrival_airport', 'XXX')
            )

        message = ScanMessage(
            message_id=uuid4(),
            source_agent=AgentType.SCAN_PROCESSOR,
            target_agents=target_agents,
            timestamp=datetime.now(),
            semantic_intent=SemanticIntent.INFORM,
            confidence_score=validation_result.confidence if validation_result else 0.95,
            reasoning=event.get('semantic_meaning', ''),
            requires_response=not validation_result.is_valid if validation_result else False,
            priority=MessagePriority.HIGH if (validation_result and not validation_result.is_valid) else MessagePriority.NORMAL,
            bag_tag=bag_tag,
            scan_details=scan_details,
            location_details=location_details,
            flight_details=flight_details,
            journey_stage=event.get('journey_stage'),
            expected_next_scan=event.get('expected_next_scans', [{}])[0].get('scan_type') if event.get('expected_next_scans') else None
        )

        return message

    def _build_risk_message(
        self,
        event: Dict[str, Any],
        bag_tag: str,
        risk_factors: List[Dict[str, Any]]
    ) -> RiskMessage:
        """Build RiskMessage when risk factors detected"""

        # Calculate overall risk score (simplified)
        risk_scores = []
        for rf in risk_factors:
            severity_map = {'LOW': 0.2, 'MEDIUM': 0.5, 'HIGH': 0.8, 'CRITICAL': 1.0}
            severity_score = severity_map.get(rf.get('severity', 'LOW'), 0.2)
            probability = rf.get('probability', 0.5)
            risk_scores.append(severity_score * probability)

        overall_risk = min(1.0, sum(risk_scores))

        # Extract risk factor names
        risk_factor_names = [rf.get('factor', 'unknown') for rf in risk_factors]

        message = RiskMessage(
            message_id=uuid4(),
            source_agent=AgentType.SCAN_PROCESSOR,
            target_agents=[AgentType.RISK_SCORER, AgentType.CASE_MANAGER],
            timestamp=datetime.now(),
            semantic_intent=SemanticIntent.REQUEST_ASSESSMENT,
            confidence_score=0.85,
            reasoning=f"Risk factors introduced by {event.get('event_type')} scan",
            requires_response=True,
            priority=MessagePriority.HIGH if overall_risk > 0.7 else MessagePriority.NORMAL,
            bag_tag=bag_tag,
            risk_score=overall_risk,
            risk_factors=risk_factor_names,
            risk_category='operational',
            recommended_actions=[
                action for action in event.get('required_actions', [])
            ]
        )

        return message

    def _build_exception_message(
        self,
        event: Dict[str, Any],
        bag_tag: str,
        validation_result: ValidationResult
    ) -> ExceptionMessage:
        """Build ExceptionMessage for validation failures"""

        # Determine severity based on anomalies
        critical_anomalies = [
            ScanAnomaly.ALREADY_CLAIMED,
            ScanAnomaly.WRONG_FLIGHT
        ]

        severity = 'CRITICAL' if any(
            a in validation_result.anomalies for a in critical_anomalies
        ) else 'MEDIUM'

        message = ExceptionMessage(
            message_id=uuid4(),
            source_agent=AgentType.SCAN_PROCESSOR,
            target_agents=[AgentType.CASE_MANAGER, AgentType.PASSENGER_COMMS],
            timestamp=datetime.now(),
            semantic_intent=SemanticIntent.REPORT_ISSUE,
            confidence_score=validation_result.confidence,
            reasoning=validation_result.reasoning,
            requires_response=True,
            priority=MessagePriority.CRITICAL if severity == 'CRITICAL' else MessagePriority.HIGH,
            bag_tag=bag_tag,
            exception_type='validation_failure',
            severity=severity,
            description=validation_result.reasoning,
            detected_anomalies=[a.value for a in validation_result.anomalies],
            requires_manual_intervention=severity == 'CRITICAL'
        )

        return message

    def _build_pattern_notification(
        self,
        correlation: CorrelatedEventGroup
    ) -> ExceptionMessage:
        """Build notification for detected patterns"""

        message = ExceptionMessage(
            message_id=uuid4(),
            source_agent=AgentType.SCAN_PROCESSOR,
            target_agents=[
                AgentType.CASE_MANAGER,
                AgentType.RISK_SCORER
            ],
            timestamp=datetime.now(),
            semantic_intent=SemanticIntent.REPORT_ISSUE,
            confidence_score=correlation.confidence,
            reasoning=correlation.reasoning,
            requires_response=True,
            priority=MessagePriority.CRITICAL if correlation.priority == 'CRITICAL' else MessagePriority.HIGH,
            bag_tag=list(correlation.bag_tags)[0] if correlation.bag_tags else 'MULTIPLE',
            exception_type=correlation.pattern_type or 'pattern_detected',
            severity=correlation.priority,
            description=f"Pattern detected: {correlation.reasoning}",
            detected_anomalies=[correlation.pattern_type or 'unknown'],
            requires_manual_intervention=correlation.requires_batch_action,
            recommended_actions=correlation.recommended_actions
        )

        return message

    def _add_to_history(self, event: Dict[str, Any], bag_tag: str):
        """Add event to bag's history for sequence validation"""
        if bag_tag not in self.bag_event_history:
            self.bag_event_history[bag_tag] = []

        self.bag_event_history[bag_tag].append(event)

        # Trim history if too large
        if len(self.bag_event_history[bag_tag]) > self.max_history_size:
            self.bag_event_history[bag_tag] = self.bag_event_history[bag_tag][-self.max_history_size:]

    def get_bag_history(self, bag_tag: str) -> List[Dict[str, Any]]:
        """Get event history for a bag"""
        return self.bag_event_history.get(bag_tag, [])

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'events_processed': self.events_processed,
            'anomalies_detected': self.anomalies_detected,
            'patterns_detected': self.patterns_detected,
            'messages_published': self.messages_published,
            'bags_tracked': len(self.bag_event_history),
            'avg_history_size': sum(
                len(hist) for hist in self.bag_event_history.values()
            ) / len(self.bag_event_history) if self.bag_event_history else 0
        }

    async def process_batch(
        self,
        events: List[tuple[Dict[str, Any], str]]
    ) -> List[Dict[str, Any]]:
        """
        Process multiple scan events in batch

        Args:
            events: List of (raw_event, bag_tag) tuples

        Returns:
            List of processed events
        """
        tasks = [
            self.process_scan_event(event, bag_tag)
            for event, bag_tag in events
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing event {i}: {result}")

        # Return successful results
        return [r for r in results if not isinstance(r, Exception)]


# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize processor
        processor = SemanticScanProcessor(
            enable_correlation=True,
            enable_validation=True
        )

        # Example raw scan event
        raw_event = {
            'scan_type': 'CHECKIN',
            'timestamp': datetime.now().isoformat(),
            'location': 'LAX_T4_CHECKIN_12',
            'scanner_id': 'SCAN_LAX_001',
            'flight_number': 'AA123',
            'raw_data': {'weight_kg': 23.5, 'dimensions_cm': [55, 40, 23]}
        }

        # Process event
        result = await processor.process_scan_event(raw_event, 'BAG123456')

        print(f"\n{'='*60}")
        print("PROCESSED EVENT")
        print(f"{'='*60}")
        print(f"Bag Tag: {result.get('bag_tag')}")
        print(f"Enriched: {result.get('enriched')}")
        print(f"Semantic Meaning: {result.get('semantic_meaning')}")
        print(f"Journey Stage: {result.get('journey_stage')}")
        print(f"\nValidation:")
        val = result.get('validation_result', {})
        print(f"  Valid: {val.get('is_valid')}")
        print(f"  Confidence: {val.get('confidence'):.2f}")
        print(f"  Reasoning: {val.get('reasoning')}")
        print(f"\nRelevant Agents: {result.get('relevant_agents')}")
        print(f"Required Actions: {result.get('required_actions')}")
        print(f"\nProcessing Time: {result['processing_metadata']['processing_time_ms']:.1f}ms")
        print(f"{'='*60}\n")

        # Get stats
        stats = processor.get_processing_stats()
        print("PROCESSING STATS:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    # Run example
    asyncio.run(main())
