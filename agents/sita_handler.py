"""
Agent 4: SITA Type B Message Handler
Parses legacy Type B messages (BTM/BSM/BPM)
"""
import json
from datetime import datetime
from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from loguru import logger

from config.settings import settings


class SITAMessageAgent:
    """
    Agent responsible for:
    1. Parsing SITA Type B messages (character-optimized legacy format)
    2. BTM (Baggage Transfer Message)
    3. BSM (Baggage Source Message)
    4. BPM (Baggage Processing Message)
    """
    
    def __init__(self):
        self.llm = ChatAnthropic(
            model=settings.model_name,
            temperature=0.0,  # Need precision for parsing
            api_key=settings.anthropic_api_key
        )
        logger.info("SITAMessageAgent initialized")
    
    async def process_type_b_message(self, raw_message: str) -> Dict[str, Any]:
        """Parse SITA Type B message"""
        try:
            # Identify message type
            message_type = self._identify_message_type(raw_message)
            
            # Parse using AI
            parsed = await self._parse_with_ai(raw_message, message_type)
            
            logger.info(f"Parsed Type B message: {message_type}")
            return {
                'message_type': message_type,
                'parsed_data': parsed,
                'raw_message': raw_message,
                'processed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing Type B message: {str(e)}")
            raise
    
    def _identify_message_type(self, message: str) -> str:
        """Identify Type B message type"""
        if message.startswith('BTM'):
            return 'BTM'
        elif message.startswith('BSM'):
            return 'BSM'
        elif message.startswith('BPM'):
            return 'BPM'
        else:
            return 'UNKNOWN'
    
    async def _parse_with_ai(self, message: str, message_type: str) -> Dict[str, Any]:
        """Use AI to parse cryptic Type B format"""
        prompt = f"""Parse this SITA Type B {message_type} message:

{message}

Type B messages use character-optimized format with abbreviations to save costs.

Common abbreviations:
- FM/TO: From/To (airlines/airports)
- BTM: Baggage Transfer Message
- BSM: Baggage Source Message
- BPM: Baggage Processing Message
- PAX: Passengers
- BAG: Baggage count
- WT: Weight
- DEST: Destination

Extract and return JSON:
{{
    "from": "sending station",
    "to": "receiving station(s)",
    "flight_number": "flight number",
    "date": "date",
    "origin": "origin airport",
    "destination": "destination airport",
    "baggage_details": [
        {{
            "bag_tag": "tag number",
            "weight": weight_in_kg,
            "destination": "final destination",
            "passenger_name": "if available"
        }}
    ],
    "special_handling": ["any special codes"],
    "total_bags": count,
    "total_weight": weight_in_kg
}}

Return ONLY valid JSON."""

        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            logger.error("Failed to parse Type B message")
            return {'error': 'parse_failed', 'raw': message}


# Agent instance
sita_message_agent = SITAMessageAgent()
