"""
Graph Query Service
===================

Provides real-time graph queries against Neo4j for bag tracking and analytics.

Features:
- Full journey path reconstruction
- Real-time location tracking
- Connection risk analysis
- Flight bag manifest
- Bottleneck detection

Version: 1.0.0
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from neo4j import GraphDatabase

from config.settings import settings


class GraphQueryService:
    """
    Service for Neo4j graph queries

    Provides optimized Cypher queries for real-time bag tracking and analytics.
    """

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str
    ):
        """
        Initialize graph query service

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )

        logger.info("✅ GraphQueryService initialized")

    def close(self):
        """Close Neo4j driver"""
        if self.driver:
            self.driver.close()
            logger.info("GraphQueryService connection closed")

    def get_bag_journey(self, bag_id: str) -> Dict[str, Any]:
        """
        Get full journey path for a bag

        Args:
            bag_id: Bag tag identifier

        Returns:
            Complete journey with all scan events
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (b:Baggage {bag_tag: $bag_id})-[:SCANNED_AT]->(s:ScanEvent)
                WITH b, s
                ORDER BY s.timestamp

                RETURN b.bag_tag as bag_tag,
                       b.status as status,
                       b.current_location as current_location,
                       b.routing as routing,
                       b.risk_score as risk_score,
                       collect({
                           event_id: s.event_id,
                           scan_type: s.scan_type,
                           location: s.location,
                           timestamp: toString(s.timestamp)
                       }) as journey
            """, bag_id=bag_id)

            record = result.single()

            if not record:
                return {
                    "bag_tag": bag_id,
                    "found": False,
                    "error": "Bag not found in graph"
                }

            return {
                "bag_tag": record['bag_tag'],
                "status": record['status'],
                "current_location": record['current_location'],
                "routing": record['routing'],
                "risk_score": record['risk_score'],
                "journey": record['journey'],
                "total_scans": len(record['journey']),
                "found": True
            }

    def get_current_location(self, bag_id: str) -> Dict[str, Any]:
        """
        Get real-time current location of a bag

        Args:
            bag_id: Bag tag identifier

        Returns:
            Current location and latest scan event
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (b:Baggage {bag_tag: $bag_id})-[:SCANNED_AT]->(s:ScanEvent)
                WITH b, s
                ORDER BY s.timestamp DESC
                LIMIT 1

                RETURN b.bag_tag as bag_tag,
                       b.status as status,
                       b.current_location as current_location,
                       s.event_id as last_scan_id,
                       s.scan_type as last_scan_type,
                       s.location as last_scan_location,
                       s.timestamp as last_scan_timestamp
            """, bag_id=bag_id)

            record = result.single()

            if not record:
                return {
                    "bag_tag": bag_id,
                    "found": False,
                    "error": "Bag not found or no scan events"
                }

            return {
                "bag_tag": record['bag_tag'],
                "status": record['status'],
                "current_location": record['current_location'],
                "last_scan": {
                    "event_id": record['last_scan_id'],
                    "scan_type": record['last_scan_type'],
                    "location": record['last_scan_location'],
                    "timestamp": str(record['last_scan_timestamp'])
                },
                "found": True
            }

    def get_flight_bags(self, flight_id: str) -> Dict[str, Any]:
        """
        Get all bags for a specific flight

        Args:
            flight_id: Flight number (e.g., CM123)

        Returns:
            List of all bags on the flight
        """
        with self.driver.session() as session:
            result = session.run("""
                // Extract flight from routing
                MATCH (b:Baggage)
                WHERE b.routing CONTAINS $flight_id

                OPTIONAL MATCH (b)-[:SCANNED_AT]->(s:ScanEvent)
                WITH b, s
                ORDER BY s.timestamp DESC

                RETURN b.bag_tag as bag_tag,
                       b.passenger_name as passenger_name,
                       b.pnr as pnr,
                       b.routing as routing,
                       b.status as status,
                       b.current_location as current_location,
                       b.risk_score as risk_score,
                       collect(s.location)[0] as last_scan_location,
                       collect(s.timestamp)[0] as last_scan_time
            """, flight_id=flight_id)

            bags = []
            for record in result:
                bags.append({
                    "bag_tag": record['bag_tag'],
                    "passenger_name": record['passenger_name'],
                    "pnr": record['pnr'],
                    "routing": record['routing'],
                    "status": record['status'],
                    "current_location": record['current_location'],
                    "risk_score": record['risk_score'],
                    "last_scan_location": record['last_scan_location'],
                    "last_scan_time": str(record['last_scan_time']) if record['last_scan_time'] else None
                })

            return {
                "flight_id": flight_id,
                "total_bags": len(bags),
                "bags": bags
            }

    def analyze_connection_risk(
        self,
        bag_id: str,
        connecting_flight: str,
        connection_time_minutes: int
    ) -> Dict[str, Any]:
        """
        Analyze feasibility of making a connecting flight

        Args:
            bag_id: Bag tag identifier
            connecting_flight: Next flight number
            connection_time_minutes: Available connection time

        Returns:
            Risk analysis with recommendation
        """
        with self.driver.session() as session:
            # Get current bag status
            result = session.run("""
                MATCH (b:Baggage {bag_tag: $bag_id})-[:SCANNED_AT]->(s:ScanEvent)
                WITH b, s
                ORDER BY s.timestamp DESC
                LIMIT 1

                RETURN b.bag_tag as bag_tag,
                       b.status as status,
                       b.current_location as current_location,
                       b.risk_score as base_risk,
                       s.location as last_scan_location,
                       s.timestamp as last_scan_time
            """, bag_id=bag_id)

            record = result.single()

            if not record:
                return {
                    "bag_id": bag_id,
                    "found": False,
                    "error": "Bag not found"
                }

            # Calculate connection risk
            base_risk = record['base_risk'] or 0.0
            connection_risk = 0.0
            risk_factors = []

            # Time-based risk
            if connection_time_minutes < 30:
                connection_risk += 0.5
                risk_factors.append("Very short connection time (<30 min)")
            elif connection_time_minutes < 45:
                connection_risk += 0.3
                risk_factors.append("Short connection time (<45 min)")
            elif connection_time_minutes < 60:
                connection_risk += 0.1
                risk_factors.append("Tight connection time (<60 min)")

            # Status-based risk
            status = record['status']
            if status in ['mishandled', 'delayed', 'offloaded']:
                connection_risk += 0.4
                risk_factors.append(f"Bag status: {status}")

            # Location-based risk
            current_location = record['current_location']
            if 'sortation' not in current_location.lower() and 'loaded' not in status:
                connection_risk += 0.2
                risk_factors.append("Not yet in sortation/loading area")

            # Combined risk
            total_risk = min(base_risk + connection_risk, 1.0)

            # Recommendation
            if total_risk < 0.3:
                recommendation = "LOW_RISK"
                action = "Bag should make connection"
            elif total_risk < 0.6:
                recommendation = "MEDIUM_RISK"
                action = "Monitor closely, prepare contingency"
            elif total_risk < 0.8:
                recommendation = "HIGH_RISK"
                action = "Likely to misconnect, prepare offload/rebooking"
            else:
                recommendation = "CRITICAL_RISK"
                action = "Will not make connection, immediate intervention required"

            return {
                "bag_id": bag_id,
                "connecting_flight": connecting_flight,
                "connection_time_minutes": connection_time_minutes,
                "current_status": status,
                "current_location": current_location,
                "base_risk_score": base_risk,
                "connection_risk_score": connection_risk,
                "total_risk_score": total_risk,
                "risk_level": recommendation,
                "recommendation": action,
                "risk_factors": risk_factors,
                "found": True
            }

    def identify_bottlenecks(
        self,
        time_window_hours: int = 1,
        min_bags: int = 5
    ) -> Dict[str, Any]:
        """
        Identify system bottlenecks by analyzing scan patterns

        Args:
            time_window_hours: Time window to analyze (hours)
            min_bags: Minimum bags to consider a bottleneck

        Returns:
            List of identified bottlenecks
        """
        with self.driver.session() as session:
            # Calculate time threshold
            time_threshold = datetime.now() - timedelta(hours=time_window_hours)

            result = session.run("""
                // Find locations with many bags stuck
                MATCH (b:Baggage)-[:SCANNED_AT]->(s:ScanEvent)
                WHERE s.timestamp > datetime($time_threshold)
                  AND b.status IN ['in_transit', 'delayed']

                WITH s.location as location,
                     count(DISTINCT b) as bag_count,
                     avg(b.risk_score) as avg_risk,
                     collect(DISTINCT b.bag_tag) as bags

                WHERE bag_count >= $min_bags

                RETURN location,
                       bag_count,
                       avg_risk,
                       bags
                ORDER BY bag_count DESC
                LIMIT 10
            """,
                time_threshold=time_threshold.isoformat(),
                min_bags=min_bags
            )

            bottlenecks = []
            for record in result:
                bottleneck_severity = "LOW"
                if record['bag_count'] > 20:
                    bottleneck_severity = "CRITICAL"
                elif record['bag_count'] > 10:
                    bottleneck_severity = "HIGH"
                elif record['bag_count'] > 5:
                    bottleneck_severity = "MEDIUM"

                bottlenecks.append({
                    "location": record['location'],
                    "bag_count": record['bag_count'],
                    "average_risk_score": round(record['avg_risk'], 3),
                    "severity": bottleneck_severity,
                    "affected_bags": record['bags'][:10]  # Limit to first 10
                })

            return {
                "time_window_hours": time_window_hours,
                "analysis_timestamp": datetime.now().isoformat(),
                "total_bottlenecks": len(bottlenecks),
                "bottlenecks": bottlenecks
            }

    def get_bag_network(
        self,
        bag_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get network of related bags (same flight, same passenger, etc.)

        Args:
            bag_id: Bag tag identifier
            depth: Relationship depth to traverse

        Returns:
            Network graph of related bags
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH path = (b:Baggage {bag_tag: $bag_id})-[*1..$depth]-(related)
                WHERE related:Baggage OR related:Passenger OR related:Flight

                WITH b, related, path
                LIMIT 100

                RETURN b.bag_tag as center_bag,
                       collect(DISTINCT {
                           type: labels(related)[0],
                           id: CASE
                               WHEN related:Baggage THEN related.bag_tag
                               WHEN related:Passenger THEN related.pnr
                               WHEN related:Flight THEN related.flight_number
                               ELSE 'unknown'
                           END,
                           properties: properties(related)
                       }) as related_entities
            """, bag_id=bag_id, depth=depth)

            record = result.single()

            if not record:
                return {
                    "bag_id": bag_id,
                    "found": False
                }

            return {
                "bag_id": bag_id,
                "related_entities": record['related_entities'],
                "total_related": len(record['related_entities']),
                "found": True
            }


# Global instance
_graph_query_service: Optional[GraphQueryService] = None


def get_graph_query_service() -> GraphQueryService:
    """Get or create graph query service singleton"""
    global _graph_query_service

    if _graph_query_service is None:
        _graph_query_service = GraphQueryService(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password
        )

    return _graph_query_service


def close_graph_query_service():
    """Close graph query service connection"""
    global _graph_query_service

    if _graph_query_service:
        _graph_query_service.close()
        _graph_query_service = None
