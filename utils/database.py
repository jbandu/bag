"""
Database connection utilities
"""
from neo4j import GraphDatabase, AsyncGraphDatabase
from supabase import create_client, Client
from redis import Redis
import asyncio
from typing import Optional, Dict, Any, List
from loguru import logger

from config.settings import settings


class Neo4jConnection:
    """Neo4j database connection manager for Digital Twin"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        logger.info("Neo4j connection established")
    
    def close(self):
        """Close the connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def create_digital_twin(self, bag_data: Dict[str, Any]) -> str:
        """Create a digital twin node for a bag"""
        with self.driver.session() as session:
            result = session.run("""
                CREATE (b:Baggage {
                    bag_tag: $bag_tag,
                    status: $status,
                    current_location: $current_location,
                    passenger_name: $passenger_name,
                    pnr: $pnr,
                    routing: $routing,
                    risk_score: $risk_score,
                    created_at: datetime($created_at),
                    updated_at: datetime()
                })
                RETURN b.bag_tag as bag_tag
            """,
                bag_tag=bag_data['bag_tag'],
                status=bag_data['status'],
                current_location=bag_data['current_location'],
                passenger_name=bag_data['passenger_name'],
                pnr=bag_data['pnr'],
                routing=bag_data['routing'],
                risk_score=bag_data.get('risk_score', 0.0),
                created_at=bag_data['created_at'].isoformat()
            )
            record = result.single()
            logger.info(f"Digital twin created for bag: {record['bag_tag']}")
            return record['bag_tag']
    
    def update_bag_location(self, bag_tag: str, location: str, status: str):
        """Update bag location and status"""
        with self.driver.session() as session:
            session.run("""
                MATCH (b:Baggage {bag_tag: $bag_tag})
                SET b.current_location = $location,
                    b.status = $status,
                    b.updated_at = datetime()
                RETURN b
            """, bag_tag=bag_tag, location=location, status=status)
            logger.info(f"Updated bag {bag_tag} location to {location}")
    
    def add_scan_event(self, bag_tag: str, scan_data: Dict[str, Any]):
        """Add scan event and create relationship"""
        with self.driver.session() as session:
            session.run("""
                MATCH (b:Baggage {bag_tag: $bag_tag})
                CREATE (s:ScanEvent {
                    event_id: $event_id,
                    scan_type: $scan_type,
                    location: $location,
                    timestamp: datetime($timestamp)
                })
                CREATE (b)-[:SCANNED_AT]->(s)
                RETURN s
            """,
                bag_tag=bag_tag,
                event_id=scan_data['event_id'],
                scan_type=scan_data['scan_type'],
                location=scan_data['location'],
                timestamp=scan_data['timestamp'].isoformat()
            )
    
    def get_bag_journey(self, bag_tag: str) -> List[Dict[str, Any]]:
        """Get complete journey history for a bag"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (b:Baggage {bag_tag: $bag_tag})-[:SCANNED_AT]->(s:ScanEvent)
                RETURN s.location as location, 
                       s.scan_type as scan_type,
                       s.timestamp as timestamp
                ORDER BY s.timestamp
            """, bag_tag=bag_tag)
            
            return [dict(record) for record in result]
    
    def update_risk_score(self, bag_tag: str, risk_score: float, risk_factors: List[str]):
        """Update risk assessment"""
        with self.driver.session() as session:
            session.run("""
                MATCH (b:Baggage {bag_tag: $bag_tag})
                SET b.risk_score = $risk_score,
                    b.risk_factors = $risk_factors,
                    b.updated_at = datetime()
            """, bag_tag=bag_tag, risk_score=risk_score, risk_factors=risk_factors)


class SupabaseConnection:
    """Supabase connection for operational data"""
    
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        logger.info("Supabase connection established")
    
    def insert_scan_event(self, scan_event: Dict[str, Any]) -> Dict[str, Any]:
        """Insert scan event into database"""
        result = self.client.table('scan_events').insert(scan_event).execute()
        logger.info(f"Scan event inserted: {scan_event['event_id']}")
        return result.data[0] if result.data else {}
    
    def insert_risk_assessment(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Insert risk assessment"""
        result = self.client.table('risk_assessments').insert(assessment).execute()
        logger.info(f"Risk assessment created for bag: {assessment['bag_tag']}")
        return result.data[0] if result.data else {}
    
    def create_exception_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create exception case"""
        result = self.client.table('exception_cases').insert(case_data).execute()
        logger.info(f"Exception case created: {case_data['case_id']}")
        return result.data[0] if result.data else {}
    
    def get_bag_data(self, bag_tag: str) -> Optional[Dict[str, Any]]:
        """Get bag data from database"""
        result = self.client.table('baggage').select('*').eq('bag_tag', bag_tag).execute()
        return result.data[0] if result.data else None
    
    def insert_worldtracer_pir(self, pir_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert WorldTracer PIR"""
        result = self.client.table('worldtracer_pirs').insert(pir_data).execute()
        logger.info(f"WorldTracer PIR created: {pir_data['pir_number']}")
        return result.data[0] if result.data else {}
    
    def create_courier_dispatch(self, dispatch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create courier dispatch record"""
        result = self.client.table('courier_dispatches').insert(dispatch_data).execute()
        logger.info(f"Courier dispatch created: {dispatch_data['dispatch_id']}")
        return result.data[0] if result.data else {}
    
    def log_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log passenger notification"""
        result = self.client.table('passenger_notifications').insert(notification_data).execute()
        return result.data[0] if result.data else {}


class RedisCache:
    """Redis cache for real-time operations"""
    
    def __init__(self):
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)
        logger.info("Redis connection established")
    
    def cache_bag_status(self, bag_tag: str, status_data: Dict[str, Any], ttl: int = 3600):
        """Cache bag status for quick lookup"""
        import json
        self.client.setex(
            f"bag:{bag_tag}",
            ttl,
            json.dumps(status_data)
        )
    
    def get_bag_status(self, bag_tag: str) -> Optional[Dict[str, Any]]:
        """Get cached bag status"""
        import json
        data = self.client.get(f"bag:{bag_tag}")
        return json.loads(data) if data else None
    
    def increment_metric(self, metric_name: str):
        """Increment operational metric"""
        self.client.incr(f"metric:{metric_name}")
    
    def get_metric(self, metric_name: str) -> int:
        """Get metric value"""
        value = self.client.get(f"metric:{metric_name}")
        return int(value) if value else 0


# Global instances
neo4j_db = Neo4jConnection()
supabase_db = SupabaseConnection()
redis_cache = RedisCache()
