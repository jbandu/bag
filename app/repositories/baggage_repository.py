"""
Baggage Repository

Handles all PostgreSQL operations for baggage tracking:
- Bag creation and updates
- Scan event recording
- Risk assessments
- Exception cases
- WorldTracer PIRs

Features:
- Async operations with connection pooling
- Retry logic with exponential backoff
- Graceful error handling
- Query performance logging
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.database.postgres import PostgresManager
from models.baggage_models import (
    BagData,
    BagStatus,
    ScanEvent,
    ScanType,
    RiskAssessment,
    RiskLevel,
    ExceptionCase,
    WorldTracerPIR,
    PassengerInfo
)


class BaggageRepository:
    """
    Repository for baggage operations

    Encapsulates all database logic for baggage tracking.
    Uses connection pooling and async operations.
    """

    def __init__(self, db: PostgresManager):
        """
        Initialize baggage repository

        Args:
            db: PostgreSQL manager with connection pool
        """
        self.db = db

    # ========================================================================
    # RETRY DECORATOR
    # ========================================================================

    @staticmethod
    def _retry_on_db_error():
        """Retry decorator for transient database errors"""
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=5),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            before_sleep=before_sleep_log(logger, "WARNING"),
            reraise=True
        )

    # ========================================================================
    # BAG OPERATIONS
    # ========================================================================

    async def create_bag(self, bag_data: Dict[str, Any]) -> Optional[str]:
        """
        Create new bag record

        Args:
            bag_data: Bag information (bag_tag, passenger, routing, etc.)

        Returns:
            bag_tag if successful, None if failed
        """
        try:
            query = """
                INSERT INTO baggage (
                    bag_tag,
                    passenger_name,
                    pnr,
                    routing,
                    current_location,
                    status,
                    weight_kg,
                    risk_score,
                    risk_level,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (bag_tag)
                DO UPDATE SET
                    passenger_name = EXCLUDED.passenger_name,
                    pnr = EXCLUDED.pnr,
                    routing = EXCLUDED.routing,
                    current_location = EXCLUDED.current_location,
                    status = EXCLUDED.status,
                    weight_kg = EXCLUDED.weight_kg,
                    updated_at = EXCLUDED.updated_at
                RETURNING bag_tag
            """

            bag_tag = await self.db.fetchval(
                query,
                bag_data.get('bag_tag'),
                bag_data.get('passenger_name'),
                bag_data.get('pnr'),
                bag_data.get('routing', []),
                bag_data.get('current_location'),
                bag_data.get('status', BagStatus.IN_TRANSIT.value),
                bag_data.get('weight_kg', 0.0),
                bag_data.get('risk_score', 0.0),
                bag_data.get('risk_level', RiskLevel.LOW.value),
                bag_data.get('created_at', datetime.utcnow()),
                datetime.utcnow()
            )

            logger.info(f"Bag created/updated: {bag_tag}")
            return bag_tag

        except Exception as e:
            logger.error(f"Failed to create bag: {e}")
            return None

    async def get_bag(self, bag_tag: str) -> Optional[Dict[str, Any]]:
        """
        Get bag by bag tag

        Args:
            bag_tag: Bag tag number

        Returns:
            Bag data dict or None if not found
        """
        try:
            query = """
                SELECT
                    bag_tag,
                    passenger_name,
                    pnr,
                    routing,
                    current_location,
                    status,
                    weight_kg,
                    risk_score,
                    risk_level,
                    risk_factors,
                    created_at,
                    updated_at
                FROM baggage
                WHERE bag_tag = $1
            """

            row = await self.db.fetchrow(query, bag_tag)

            if not row:
                return None

            return dict(row)

        except Exception as e:
            logger.error(f"Failed to get bag {bag_tag}: {e}")
            return None

    async def update_bag_status(
        self,
        bag_tag: str,
        status: BagStatus,
        location: Optional[str] = None
    ) -> bool:
        """
        Update bag status and location

        Args:
            bag_tag: Bag tag number
            status: New status
            location: New location (optional)

        Returns:
            True if successful
        """
        try:
            if location:
                query = """
                    UPDATE baggage
                    SET status = $1,
                        current_location = $2,
                        updated_at = $3
                    WHERE bag_tag = $4
                """
                await self.db.execute(query, status.value, location, datetime.utcnow(), bag_tag)
            else:
                query = """
                    UPDATE baggage
                    SET status = $1,
                        updated_at = $2
                    WHERE bag_tag = $3
                """
                await self.db.execute(query, status.value, datetime.utcnow(), bag_tag)

            logger.info(f"Updated bag {bag_tag} status to {status.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to update bag status: {e}")
            return False

    async def update_risk_score(
        self,
        bag_tag: str,
        risk_score: float,
        risk_level: RiskLevel,
        risk_factors: List[str]
    ) -> bool:
        """
        Update bag risk assessment

        Args:
            bag_tag: Bag tag number
            risk_score: Risk score (0.0 - 1.0)
            risk_level: Risk level enum
            risk_factors: List of risk factors

        Returns:
            True if successful
        """
        try:
            query = """
                UPDATE baggage
                SET risk_score = $1,
                    risk_level = $2,
                    risk_factors = $3,
                    updated_at = $4
                WHERE bag_tag = $5
            """

            await self.db.execute(
                query,
                risk_score,
                risk_level.value,
                risk_factors,
                datetime.utcnow(),
                bag_tag
            )

            logger.info(f"Updated risk score for bag {bag_tag}: {risk_score} ({risk_level.value})")
            return True

        except Exception as e:
            logger.error(f"Failed to update risk score: {e}")
            return False

    # ========================================================================
    # SCAN EVENT OPERATIONS
    # ========================================================================

    async def add_scan_event(self, scan_event: Dict[str, Any]) -> Optional[str]:
        """
        Record scan event

        Args:
            scan_event: Scan event data

        Returns:
            event_id if successful
        """
        try:
            query = """
                INSERT INTO scan_events (
                    event_id,
                    bag_tag,
                    scan_type,
                    location,
                    timestamp,
                    scanner_id,
                    operator_id,
                    raw_data,
                    airline_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING event_id
            """

            event_id = await self.db.fetchval(
                query,
                scan_event.get('event_id'),
                scan_event.get('bag_tag'),
                scan_event.get('scan_type'),
                scan_event.get('location'),
                scan_event.get('timestamp', datetime.utcnow()),
                scan_event.get('scanner_id'),
                scan_event.get('operator_id'),
                scan_event.get('raw_data'),
                scan_event.get('airline_id')
            )

            logger.info(f"Scan event recorded: {event_id} for bag {scan_event.get('bag_tag')}")
            return event_id

        except Exception as e:
            logger.error(f"Failed to add scan event: {e}")
            return None

    async def get_bag_scan_history(
        self,
        bag_tag: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get scan history for bag

        Args:
            bag_tag: Bag tag number
            limit: Max number of events to return

        Returns:
            List of scan events
        """
        try:
            query = """
                SELECT
                    event_id,
                    bag_tag,
                    scan_type,
                    location,
                    timestamp,
                    scanner_id,
                    operator_id,
                    raw_data
                FROM scan_events
                WHERE bag_tag = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """

            rows = await self.db.fetch(query, bag_tag, limit)
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get scan history for {bag_tag}: {e}")
            return []

    async def get_recent_scans(
        self,
        airline_id: Optional[int] = None,
        hours: int = 24,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get recent scan events

        Args:
            airline_id: Filter by airline (optional)
            hours: Time window in hours
            limit: Max number of events

        Returns:
            List of recent scan events
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)

            if airline_id:
                query = """
                    SELECT
                        event_id,
                        bag_tag,
                        scan_type,
                        location,
                        timestamp,
                        airline_id
                    FROM scan_events
                    WHERE timestamp >= $1 AND airline_id = $2
                    ORDER BY timestamp DESC
                    LIMIT $3
                """
                rows = await self.db.fetch(query, since, airline_id, limit, readonly=True)
            else:
                query = """
                    SELECT
                        event_id,
                        bag_tag,
                        scan_type,
                        location,
                        timestamp,
                        airline_id
                    FROM scan_events
                    WHERE timestamp >= $1
                    ORDER BY timestamp DESC
                    LIMIT $2
                """
                rows = await self.db.fetch(query, since, limit, readonly=True)

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get recent scans: {e}")
            return []

    # ========================================================================
    # RISK ASSESSMENT OPERATIONS
    # ========================================================================

    async def save_risk_assessment(
        self,
        assessment: Dict[str, Any]
    ) -> Optional[int]:
        """
        Save risk assessment

        Args:
            assessment: Risk assessment data

        Returns:
            Assessment ID if successful
        """
        try:
            query = """
                INSERT INTO risk_assessments (
                    bag_tag,
                    risk_score,
                    risk_level,
                    primary_factors,
                    recommended_action,
                    confidence,
                    reasoning,
                    connection_time_minutes,
                    mct_minutes,
                    timestamp,
                    airline_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """

            assessment_id = await self.db.fetchval(
                query,
                assessment.get('bag_tag'),
                assessment.get('risk_score'),
                assessment.get('risk_level'),
                assessment.get('primary_factors', []),
                assessment.get('recommended_action'),
                assessment.get('confidence'),
                assessment.get('reasoning'),
                assessment.get('connection_time_minutes'),
                assessment.get('mct_minutes'),
                assessment.get('timestamp', datetime.utcnow()),
                assessment.get('airline_id')
            )

            logger.info(f"Risk assessment saved for bag {assessment.get('bag_tag')}")
            return assessment_id

        except Exception as e:
            logger.error(f"Failed to save risk assessment: {e}")
            return None

    async def get_high_risk_bags(
        self,
        airline_id: Optional[int] = None,
        threshold: float = 0.7,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get high-risk bags

        Args:
            airline_id: Filter by airline (optional)
            threshold: Minimum risk score
            limit: Max number of bags

        Returns:
            List of high-risk bags
        """
        try:
            if airline_id:
                query = """
                    SELECT
                        b.bag_tag,
                        b.passenger_name,
                        b.pnr,
                        b.current_location,
                        b.status,
                        b.risk_score,
                        b.risk_level,
                        b.risk_factors,
                        b.updated_at
                    FROM baggage b
                    WHERE b.risk_score >= $1
                      AND b.airline_id = $2
                      AND b.status NOT IN ('claimed', 'arrived')
                    ORDER BY b.risk_score DESC
                    LIMIT $3
                """
                rows = await self.db.fetch(query, threshold, airline_id, limit)
            else:
                query = """
                    SELECT
                        b.bag_tag,
                        b.passenger_name,
                        b.pnr,
                        b.current_location,
                        b.status,
                        b.risk_score,
                        b.risk_level,
                        b.risk_factors,
                        b.updated_at
                    FROM baggage b
                    WHERE b.risk_score >= $1
                      AND b.status NOT IN ('claimed', 'arrived')
                    ORDER BY b.risk_score DESC
                    LIMIT $2
                """
                rows = await self.db.fetch(query, threshold, limit)

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get high-risk bags: {e}")
            return []

    # ========================================================================
    # EXCEPTION CASE OPERATIONS
    # ========================================================================

    async def create_exception_case(
        self,
        case_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Create exception case

        Args:
            case_data: Exception case data

        Returns:
            case_id if successful
        """
        try:
            query = """
                INSERT INTO exception_cases (
                    case_id,
                    bag_tag,
                    priority,
                    status,
                    assigned_to,
                    risk_score,
                    sla_deadline,
                    airline_id,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING case_id
            """

            case_id = await self.db.fetchval(
                query,
                case_data.get('case_id'),
                case_data.get('bag_tag'),
                case_data.get('priority'),
                case_data.get('status', 'open'),
                case_data.get('assigned_to'),
                case_data.get('risk_score'),
                case_data.get('sla_deadline'),
                case_data.get('airline_id'),
                datetime.utcnow()
            )

            logger.info(f"Exception case created: {case_id}")
            return case_id

        except Exception as e:
            logger.error(f"Failed to create exception case: {e}")
            return None

    async def get_open_exception_cases(
        self,
        airline_id: Optional[int] = None,
        priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get open exception cases

        Args:
            airline_id: Filter by airline (optional)
            priority: Filter by priority (P0, P1, P2, P3)

        Returns:
            List of open exception cases
        """
        try:
            filters = ["status = 'open'"]
            params = []
            param_num = 1

            if airline_id:
                filters.append(f"airline_id = ${param_num}")
                params.append(airline_id)
                param_num += 1

            if priority:
                filters.append(f"priority = ${param_num}")
                params.append(priority)
                param_num += 1

            where_clause = " AND ".join(filters)

            query = f"""
                SELECT
                    case_id,
                    bag_tag,
                    priority,
                    status,
                    assigned_to,
                    risk_score,
                    sla_deadline,
                    created_at
                FROM exception_cases
                WHERE {where_clause}
                ORDER BY priority, created_at
            """

            rows = await self.db.fetch(query, *params)
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get open exception cases: {e}")
            return []

    # ========================================================================
    # WORLDTRACER PIR OPERATIONS
    # ========================================================================

    async def create_worldtracer_pir(
        self,
        pir_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Create WorldTracer PIR

        Args:
            pir_data: PIR data

        Returns:
            pir_number if successful
        """
        try:
            query = """
                INSERT INTO worldtracer_pirs (
                    pir_number,
                    pir_type,
                    bag_tag,
                    passenger_name,
                    pnr,
                    flight_number,
                    bag_description,
                    last_known_location,
                    expected_destination,
                    status,
                    airline_id,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING pir_number
            """

            pir_number = await self.db.fetchval(
                query,
                pir_data.get('pir_number'),
                pir_data.get('pir_type'),
                pir_data.get('bag_tag'),
                pir_data.get('passenger_name'),
                pir_data.get('pnr'),
                pir_data.get('flight_number'),
                pir_data.get('bag_description'),
                pir_data.get('last_known_location'),
                pir_data.get('expected_destination'),
                pir_data.get('status', 'open'),
                pir_data.get('airline_id'),
                datetime.utcnow()
            )

            logger.info(f"WorldTracer PIR created: {pir_number}")
            return pir_number

        except Exception as e:
            logger.error(f"Failed to create WorldTracer PIR: {e}")
            return None

    async def get_open_pirs(
        self,
        airline_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get open WorldTracer PIRs

        Args:
            airline_id: Filter by airline (optional)

        Returns:
            List of open PIRs
        """
        try:
            if airline_id:
                query = """
                    SELECT
                        pir_number,
                        pir_type,
                        bag_tag,
                        passenger_name,
                        pnr,
                        flight_number,
                        status,
                        created_at
                    FROM worldtracer_pirs
                    WHERE status = 'open' AND airline_id = $1
                    ORDER BY created_at DESC
                """
                rows = await self.db.fetch(query, airline_id)
            else:
                query = """
                    SELECT
                        pir_number,
                        pir_type,
                        bag_tag,
                        passenger_name,
                        pnr,
                        flight_number,
                        status,
                        created_at
                    FROM worldtracer_pirs
                    WHERE status = 'open'
                    ORDER BY created_at DESC
                """
                rows = await self.db.fetch(query)

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get open PIRs: {e}")
            return []
