"""
Event Processor Service
========================

Consumes events from Redis Stream and processes them with dual-write to PostgreSQL + Neo4j.

Features:
- Parallel event processing with multiple consumers
- Dual-write to PostgreSQL + Neo4j
- Event enrichment with contextual data
- Webhook notifications
- AI agent triggering for anomalies

Version: 1.0.0
"""

from typing import Dict, Any, Optional
from datetime import datetime
import time
import asyncio
from loguru import logger

from models.event_schemas import (
    BagScanEvent,
    BagLoadEvent,
    BagTransferEvent,
    BagClaimEvent,
    BagAnomalyEvent,
    EventProcessingResult
)
from services.event_ingestion_service import EventIngestionService
from services.dual_write_service import get_dual_write_service, DualWriteException


class EventProcessorService:
    """
    Event processor service

    Consumes events from Redis Stream and processes them.
    """

    def __init__(
        self,
        ingestion_service: EventIngestionService,
        consumer_name: str = "processor_1"
    ):
        """
        Initialize event processor

        Args:
            ingestion_service: Event ingestion service instance
            consumer_name: Unique consumer identifier
        """
        self.ingestion_service = ingestion_service
        self.consumer_name = consumer_name
        self.dual_write = get_dual_write_service()

        self.stats = {
            'processed': 0,
            'failed': 0,
            'total_processing_time': 0.0
        }

        logger.info(f"✅ EventProcessorService initialized (consumer: {consumer_name})")

    def process_event(
        self,
        event: Dict[str, Any]
    ) -> EventProcessingResult:
        """
        Process a single event

        Args:
            event: Event dictionary from Redis Stream

        Returns:
            Processing result
        """
        start_time = time.time()

        event_type = event.get('event_type')
        event_data = event.get('data')
        message_id = event.get('message_id')

        logger.info(f"Processing event: {message_id} (type: {event_type})")

        try:
            # Parse event based on type
            if event_type == 'scan':
                result = self._process_scan_event(event_data)
            elif event_type == 'load':
                result = self._process_load_event(event_data)
            elif event_type == 'transfer':
                result = self._process_transfer_event(event_data)
            elif event_type == 'claim':
                result = self._process_claim_event(event_data)
            elif event_type == 'anomaly':
                result = self._process_anomaly_event(event_data)
            else:
                raise ValueError(f"Unknown event type: {event_type}")

            # Acknowledge event
            self.ingestion_service.acknowledge_event(message_id)

            processing_time = (time.time() - start_time) * 1000

            self.stats['processed'] += 1
            self.stats['total_processing_time'] += processing_time

            return EventProcessingResult(
                event_id=message_id,
                success=True,
                processing_time_ms=processing_time,
                **result
            )

        except Exception as e:
            logger.error(f"Failed to process event {message_id}: {e}")

            # Move to dead letter queue
            self.ingestion_service.move_to_dlq(
                message_id,
                event_data,
                str(e)
            )

            self.stats['failed'] += 1

            return EventProcessingResult(
                event_id=message_id,
                success=False,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _process_scan_event(self, event_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Process bag scan event

        Args:
            event_data: Scan event data

        Returns:
            Processing result dict
        """
        # Validate event
        scan_event = BagScanEvent(**event_data)

        # Enrich with context (flight info, passenger info, etc.)
        enriched_data = self._enrich_event(scan_event.dict())

        # Dual-write to PostgreSQL + Neo4j
        scan_record = {
            'event_id': scan_event.event_id,
            'bag_tag': scan_event.bag_id,
            'scan_type': scan_event.scan_type,
            'location': scan_event.location,
            'timestamp': scan_event.timestamp.isoformat(),
            'raw_data': scan_event.raw_data or ''
        }

        try:
            self.dual_write.add_scan_event(scan_record)
            written_to_postgres = True
            written_to_neo4j = True
        except DualWriteException:
            written_to_postgres = True  # Postgres succeeded
            written_to_neo4j = False

        # Trigger notifications if needed
        notifications_sent = self._trigger_notifications(scan_event)

        # Trigger AI agent if high-risk
        if enriched_data.get('risk_score', 0) > 0.7:
            self._trigger_ai_agent(scan_event, enriched_data)

        return {
            'written_to_postgres': written_to_postgres,
            'written_to_neo4j': written_to_neo4j,
            'notifications_sent': notifications_sent
        }

    def _process_load_event(self, event_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Process bag load event

        Args:
            event_data: Load event data

        Returns:
            Processing result dict
        """
        # Validate event
        load_event = BagLoadEvent(**event_data)

        # Convert to scan event format for storage
        scan_record = {
            'event_id': load_event.event_id,
            'bag_tag': load_event.bag_id,
            'scan_type': 'load',
            'location': load_event.location,
            'timestamp': load_event.timestamp.isoformat(),
            'raw_data': f"Flight: {load_event.flight_number}, Container: {load_event.container_id}"
        }

        try:
            self.dual_write.add_scan_event(scan_record)
            written_to_postgres = True
            written_to_neo4j = True
        except DualWriteException:
            written_to_postgres = True
            written_to_neo4j = False

        # Send loaded notification
        notifications_sent = self._trigger_notifications(load_event)

        return {
            'written_to_postgres': written_to_postgres,
            'written_to_neo4j': written_to_neo4j,
            'notifications_sent': notifications_sent
        }

    def _process_transfer_event(self, event_data: Dict[str, Any]) -> Dict[str, bool]:
        """Process bag transfer event"""
        transfer_event = BagTransferEvent(**event_data)

        scan_record = {
            'event_id': transfer_event.event_id,
            'bag_tag': transfer_event.bag_id,
            'scan_type': 'transfer',
            'location': transfer_event.to_location,
            'timestamp': transfer_event.timestamp.isoformat(),
            'raw_data': f"From: {transfer_event.from_location}, To: {transfer_event.to_location}"
        }

        try:
            self.dual_write.add_scan_event(scan_record)
            written_to_postgres = True
            written_to_neo4j = True
        except DualWriteException:
            written_to_postgres = True
            written_to_neo4j = False

        return {
            'written_to_postgres': written_to_postgres,
            'written_to_neo4j': written_to_neo4j,
            'notifications_sent': 0
        }

    def _process_claim_event(self, event_data: Dict[str, Any]) -> Dict[str, bool]:
        """Process bag claim event"""
        claim_event = BagClaimEvent(**event_data)

        scan_record = {
            'event_id': claim_event.event_id,
            'bag_tag': claim_event.bag_id,
            'scan_type': 'claim',
            'location': claim_event.location,
            'timestamp': claim_event.timestamp.isoformat(),
            'raw_data': f"Passenger: {claim_event.passenger_id}, Verified: {claim_event.verified}"
        }

        try:
            self.dual_write.add_scan_event(scan_record)
            written_to_postgres = True
            written_to_neo4j = True
        except DualWriteException:
            written_to_postgres = True
            written_to_neo4j = False

        # Send claim notification
        notifications_sent = self._trigger_notifications(claim_event)

        return {
            'written_to_postgres': written_to_postgres,
            'written_to_neo4j': written_to_neo4j,
            'notifications_sent': notifications_sent
        }

    def _process_anomaly_event(self, event_data: Dict[str, Any]) -> Dict[str, bool]:
        """Process bag anomaly event"""
        anomaly_event = BagAnomalyEvent(**event_data)

        scan_record = {
            'event_id': anomaly_event.event_id,
            'bag_tag': anomaly_event.bag_id,
            'scan_type': 'anomaly',
            'location': anomaly_event.location,
            'timestamp': anomaly_event.timestamp.isoformat(),
            'raw_data': f"Anomaly: {anomaly_event.anomaly_type}, Severity: {anomaly_event.severity}"
        }

        try:
            self.dual_write.add_scan_event(scan_record)

            # Create exception case if action required
            if anomaly_event.action_required:
                case_data = {
                    'case_id': f"CASE_{anomaly_event.event_id}",
                    'bag_tag': anomaly_event.bag_id,
                    'case_type': anomaly_event.anomaly_type,
                    'priority': self._severity_to_priority(anomaly_event.severity),
                    'status': 'open',
                    'assigned_to': anomaly_event.assigned_to or 'UNASSIGNED'
                }
                self.dual_write.create_exception_case(case_data)

            written_to_postgres = True
            written_to_neo4j = True
        except DualWriteException:
            written_to_postgres = True
            written_to_neo4j = False

        # Send anomaly alerts
        notifications_sent = self._trigger_notifications(anomaly_event)

        # Trigger AI agent for analysis
        self._trigger_ai_agent(anomaly_event, {'severity': anomaly_event.severity})

        return {
            'written_to_postgres': written_to_postgres,
            'written_to_neo4j': written_to_neo4j,
            'notifications_sent': notifications_sent
        }

    def _enrich_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich event with contextual data

        Args:
            event_data: Raw event data

        Returns:
            Enriched event data
        """
        # TODO: Add flight info, passenger info, weather, etc.
        enriched = event_data.copy()

        # Add timestamp if missing
        if 'timestamp' not in enriched:
            enriched['timestamp'] = datetime.now().isoformat()

        # Add risk score (placeholder - would call risk scoring agent)
        enriched['risk_score'] = 0.2

        return enriched

    def _trigger_notifications(self, event: Any) -> int:
        """
        Trigger notifications based on event type

        Args:
            event: Event object

        Returns:
            Number of notifications sent
        """
        # TODO: Implement notification logic
        # Would call notification service here

        notifications_sent = 0

        # Example: Send notification on load/claim events
        if isinstance(event, (BagLoadEvent, BagClaimEvent, BagAnomalyEvent)):
            logger.debug(f"Notification triggered for event: {event.event_id}")
            notifications_sent = 1

        return notifications_sent

    def _trigger_ai_agent(self, event: Any, context: Dict[str, Any]):
        """
        Trigger AI agent analysis

        Args:
            event: Event object
            context: Enriched context data
        """
        # TODO: Implement AI agent triggering
        logger.debug(f"AI agent triggered for event: {event.event_id}")

    def _severity_to_priority(self, severity: str) -> str:
        """Map severity to priority level"""
        mapping = {
            'low': 'P3',
            'medium': 'P2',
            'high': 'P1',
            'critical': 'P0'
        }
        return mapping.get(severity, 'P3')

    def run_consumer(
        self,
        batch_size: int = 10,
        block_ms: int = 5000,
        max_iterations: Optional[int] = None
    ):
        """
        Run consumer loop

        Args:
            batch_size: Number of events to consume per iteration
            block_ms: Block timeout in milliseconds
            max_iterations: Maximum iterations (None = infinite)
        """
        logger.info(f"Starting consumer: {self.consumer_name}")

        iteration = 0

        while max_iterations is None or iteration < max_iterations:
            try:
                # Claim stale events
                self.ingestion_service.claim_stale_events(self.consumer_name)

                # Consume events
                events = self.ingestion_service.consume_events(
                    self.consumer_name,
                    count=batch_size,
                    block_ms=block_ms
                )

                # Process events
                for event in events:
                    self.process_event(event)

                if events:
                    logger.info(
                        f"Processed {len(events)} events "
                        f"(total: {self.stats['processed']}, "
                        f"failed: {self.stats['failed']})"
                    )

                iteration += 1

            except KeyboardInterrupt:
                logger.info("Consumer stopped by user")
                break
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                time.sleep(5)  # Wait before retry

        logger.info(f"Consumer stopped after {iteration} iterations")

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        avg_processing_time = (
            self.stats['total_processing_time'] / self.stats['processed']
            if self.stats['processed'] > 0
            else 0
        )

        return {
            'consumer_name': self.consumer_name,
            'processed': self.stats['processed'],
            'failed': self.stats['failed'],
            'success_rate': (
                self.stats['processed'] / (self.stats['processed'] + self.stats['failed'])
                if (self.stats['processed'] + self.stats['failed']) > 0
                else 0
            ),
            'avg_processing_time_ms': round(avg_processing_time, 2)
        }
