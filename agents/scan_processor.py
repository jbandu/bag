"""
Agent 1: Scan Event Processor
Processes scan events from BRS, BHS, and DCS
Creates/updates digital twins in Neo4j
"""
import json
from datetime import datetime
from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from loguru import logger

from models.baggage_models import ScanEvent, BagData, ScanType, BagStatus
from config.settings import settings
from utils.database import neo4j_db, supabase_db, redis_cache


class ScanEventProcessorAgent:
    """
    Agent responsible for:
    1. Ingesting scan events from multiple sources (BRS, BHS, DCS)
    2. Parsing various scan formats
    3. Validating scan sequences
    4. Updating digital twin in Neo4j
    5. Detecting anomalies
    """
    
    def __init__(self):
        self.llm = ChatAnthropic(
            model=settings.model_name,
            temperature=settings.model_temperature,
            api_key=settings.anthropic_api_key
        )
        logger.info("ScanEventProcessorAgent initialized")
    
    async def process_scan(self, raw_scan: str) -> Dict[str, Any]:
        """Main processing pipeline for scan events"""
        try:
            # Step 1: Parse the raw scan data
            parsed_event = await self.parse_scan_event(raw_scan)
            
            # Step 2: Validate scan sequence
            is_valid, anomalies = await self.validate_scan_sequence(parsed_event)
            
            # Step 3: Update digital twin
            await self.update_digital_twin(parsed_event)
            
            # Step 4: Store in Supabase
            scan_record = await self.store_scan_event(parsed_event)
            
            # Step 5: Update cache
            redis_cache.cache_bag_status(
                parsed_event['bag_tag'],
                {
                    'status': parsed_event['status'],
                    'location': parsed_event['location'],
                    'timestamp': parsed_event['timestamp'].isoformat()
                }
            )
            
            # Step 6: Increment metrics
            redis_cache.increment_metric('scans_processed')
            if not is_valid:
                redis_cache.increment_metric('scan_anomalies')
            
            result = {
                'parsed_event': parsed_event,
                'is_valid_sequence': is_valid,
                'anomalies': anomalies,
                'scan_record_id': scan_record.get('id'),
                'processed_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Scan processed successfully for bag {parsed_event['bag_tag']}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing scan: {str(e)}")
            raise
    
    async def parse_scan_event(self, raw_scan: str) -> Dict[str, Any]:
        """
        Use AI to parse various scan formats
        Handles BRS, BHS, DCS formats
        """
        prompt = f"""Parse this baggage scan event from airport systems:

{raw_scan}

This could be from:
- BRS (Airport Baggage Reconciliation System)
- BHS (Baggage Handling System) 
- DCS (Departure Control System)
- Manual scan

Extract and return JSON with:
{{
    "bag_tag": "bag tag number (format: CM123456)",
    "scan_type": "check_in|sortation|load|offload|arrival|claim|manual|btm|bsm|bpm",
    "location": "3-letter airport code or specific area (e.g., PTY-T1-BHS-01)",
    "timestamp": "ISO 8601 timestamp",
    "scanner_id": "scanner identifier if available",
    "operator_id": "operator ID if manual scan",
    "flight_number": "flight number if applicable",
    "status": "checked_in|in_transit|loaded|offloaded|arrived|claimed",
    "error_codes": ["any error codes present"],
    "raw_data": {{additional metadata}}
}}

Be precise with the scan_type based on the context:
- Check-in scans happen at ticket counter
- Sortation scans happen in BHS
- Load scans confirm bag on aircraft
- BTM/BSM/BPM are specific IATA message types

Return ONLY valid JSON, no explanation."""

        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        
        # Parse LLM response
        try:
            parsed = json.loads(response.content)
            
            # Convert timestamp string to datetime
            parsed['timestamp'] = datetime.fromisoformat(
                parsed['timestamp'].replace('Z', '+00:00')
            )
            
            # Generate event ID
            parsed['event_id'] = f"scan_{parsed['bag_tag']}_{int(parsed['timestamp'].timestamp())}"
            
            logger.debug(f"Parsed scan event: {parsed['event_id']}")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            logger.error(f"LLM response was: {response.content}")
            raise
    
    async def validate_scan_sequence(self, scan_event: Dict[str, Any]) -> tuple[bool, list]:
        """
        Validate if this scan makes sense in the bag's journey
        Returns (is_valid, list_of_anomalies)
        """
        bag_tag = scan_event['bag_tag']
        current_location = scan_event['location']
        scan_type = scan_event['scan_type']
        
        # Get bag's journey history from Neo4j
        journey = neo4j_db.get_bag_journey(bag_tag)
        
        if not journey:
            # First scan for this bag - always valid
            return True, []
        
        # AI validates the sequence
        prompt = f"""Validate this baggage scan sequence:

**New Scan:**
- Type: {scan_type}
- Location: {current_location}
- Timestamp: {scan_event['timestamp']}

**Previous Journey (chronological):**
{json.dumps(journey, indent=2, default=str)}

Analyze if this scan makes logical sense:

1. **Location continuity**: Can a bag physically move from last location to current location?
2. **Timing**: Is the time gap reasonable?
3. **Scan sequence**: Does the scan type follow logically?
4. **Status progression**: Does status change make sense?

Common anomalies to detect:
- Bag scanned at two distant airports within impossible timeframe
- Duplicate scans at same location/time
- Backward progression (e.g., arrival scan followed by check-in scan)
- Large time gaps (>30 min) between scans in same airport
- Scan at wrong airport (not in routing)

Return JSON:
{{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "anomalies": [
        {{"type": "impossible_transit", "severity": "high", "description": "..."}},
        ...
    ],
    "reasoning": "brief explanation"
}}

Return ONLY valid JSON."""

        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        
        try:
            validation = json.loads(response.content)
            is_valid = validation['is_valid']
            anomalies = validation.get('anomalies', [])
            
            if not is_valid:
                logger.warning(
                    f"Scan sequence anomaly detected for bag {bag_tag}: "
                    f"{validation.get('reasoning', 'Unknown reason')}"
                )
            
            return is_valid, anomalies
            
        except json.JSONDecodeError:
            logger.error("Failed to parse validation response")
            # Default to valid if we can't parse
            return True, []
    
    async def update_digital_twin(self, scan_event: Dict[str, Any]):
        """Update or create digital twin in Neo4j"""
        bag_tag = scan_event['bag_tag']
        
        # Check if digital twin exists
        existing_bag = supabase_db.get_bag_data(bag_tag)
        
        if not existing_bag:
            # Create new digital twin
            logger.info(f"Creating new digital twin for bag {bag_tag}")
            # In production, this would pull full bag data from DCS
            # For now, create minimal record
            bag_data = {
                'bag_tag': bag_tag,
                'status': scan_event['status'],
                'current_location': scan_event['location'],
                'passenger_name': 'Unknown',  # Would come from DCS
                'pnr': 'Unknown',  # Would come from DCS
                'routing': [scan_event['location'].split('-')[0]],  # Extract airport code
                'risk_score': 0.0,
                'created_at': scan_event['timestamp']
            }
            neo4j_db.create_digital_twin(bag_data)
        else:
            # Update existing twin
            neo4j_db.update_bag_location(
                bag_tag,
                scan_event['location'],
                scan_event['status']
            )
        
        # Add scan event to journey
        neo4j_db.add_scan_event(bag_tag, scan_event)
        
        logger.info(f"Digital twin updated for bag {bag_tag}")
    
    async def store_scan_event(self, scan_event: Dict[str, Any]) -> Dict[str, Any]:
        """Store scan event in Supabase"""
        event_data = {
            'event_id': scan_event['event_id'],
            'bag_tag': scan_event['bag_tag'],
            'scan_type': scan_event['scan_type'],
            'location': scan_event['location'],
            'timestamp': scan_event['timestamp'].isoformat(),
            'scanner_id': scan_event.get('scanner_id'),
            'operator_id': scan_event.get('operator_id'),
            'flight_number': scan_event.get('flight_number'),
            'status': scan_event['status'],
            'error_codes': scan_event.get('error_codes', []),
            'raw_data': scan_event.get('raw_data')
        }
        
        return supabase_db.insert_scan_event(event_data)


# Agent instance
scan_processor_agent = ScanEventProcessorAgent()
