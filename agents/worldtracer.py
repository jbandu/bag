"""
Agent 3: WorldTracer Integration
Manages WorldTracer PIR creation and bag matching
"""
import json
from datetime import datetime
from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from loguru import logger
import httpx

from models.baggage_models import WorldTracerPIR, PIRType, PassengerInfo, FlightInfo
from config.settings import settings
from utils.database import supabase_db


class WorldTracerAgent:
    """
    Agent responsible for:
    1. Creating PIRs for mishandled bags
    2. Matching found bags with open PIRs
    3. Updating PIR status
    4. Routing bags to correct destinations
    """
    
    def __init__(self):
        self.llm = ChatAnthropic(
            model=settings.model_name,
            temperature=settings.model_temperature,
            api_key=settings.anthropic_api_key
        )
        self.worldtracer_url = settings.worldtracer_api_url
        self.api_key = settings.worldtracer_api_key
        self.airline_code = settings.worldtracer_airline_code
        logger.info("WorldTracerAgent initialized")
    
    async def handle_mishandled_bag(self, bag_data: Dict[str, Any]) -> WorldTracerPIR:
        """
        Main entry point for mishandled bag processing
        """
        try:
            # Determine PIR type
            pir_type = await self.classify_mishandling(bag_data)
            
            # Generate PIR details using AI
            pir_details = await self.generate_pir_details(bag_data, pir_type)
            
            # Create PIR in WorldTracer
            pir_number = await self.submit_to_worldtracer(pir_details)
            
            # Create PIR object
            pir = WorldTracerPIR(
                pir_number=pir_number,
                pir_type=pir_type,
                bag_tag=bag_data['bag_tag'],
                passenger=PassengerInfo(**bag_data['passenger']),
                flight=FlightInfo(**bag_data['flight']),
                bag_description=pir_details['bag_description'],
                contents_description=pir_details.get('contents_description'),
                last_known_location=pir_details['last_known_location'],
                expected_destination=pir_details['expected_destination']
            )
            
            # Store in database
            await self.store_pir(pir)
            
            logger.info(f"WorldTracer PIR created: {pir_number} for bag {bag_data['bag_tag']}")
            return pir
            
        except Exception as e:
            logger.error(f"Error handling mishandled bag: {str(e)}")
            raise
    
    async def classify_mishandling(self, bag_data: Dict[str, Any]) -> PIRType:
        """Classify type of mishandling"""
        status = bag_data.get('status', '')
        
        if status == 'offloaded':
            return PIRType.OHD
        elif status == 'delayed':
            return PIRType.DELAYED
        elif status == 'unclaimed':
            return PIRType.AHL
        else:
            return PIRType.PIR
    
    async def generate_pir_details(self, bag_data: Dict[str, Any], pir_type: PIRType) -> Dict[str, Any]:
        """
        AI generates comprehensive PIR details
        """
        prompt = f"""Generate WorldTracer PIR details for mishandled baggage:

**Passenger Information:**
- Name: {bag_data['passenger']['name']}
- PNR: {bag_data['passenger']['pnr']}
- Contact: {bag_data['passenger'].get('email', 'N/A')} / {bag_data['passenger'].get('phone', 'N/A')}
- Elite Status: {bag_data['passenger'].get('elite_status', 'None')}

**Bag Information:**
- Tag: {bag_data['bag_tag']}
- Weight: {bag_data.get('weight_kg', 'Unknown')} kg
- Special Handling: {bag_data.get('special_handling', [])}

**Flight Information:**
- Flight: {bag_data['flight']['flight_number']}
- Route: {bag_data.get('routing', [])}
- Current Location: {bag_data['current_location']}
- Expected Destination: {bag_data['flight']['destination']}

**Mishandling Type:** {pir_type}

**Reason:**
{bag_data.get('mishandling_reason', 'Unknown')}

Generate complete PIR details in JSON:
{{
    "pir_type": "{pir_type}",
    "bag_description": "detailed physical description (color, type, brand, size, condition)",
    "contents_description": "general contents if declared (no specific valuables)",
    "last_known_location": "specific location with timestamp",
    "expected_destination": "destination airport and address if available",
    "priority": "normal|high|urgent",
    "delivery_instructions": "special delivery notes",
    "contact_preferences": "preferred contact method and times"
}}

**Important:**
- Bag description should help identify the bag visually
- Do not include specific valuables in contents (security/privacy)
- Priority should be 'urgent' for elite passengers or time-sensitive
- Include delivery address from passenger data if available

Return ONLY valid JSON."""

        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        
        try:
            pir_details = json.loads(response.content)
            return pir_details
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse PIR details: {str(e)}")
            # Return minimal safe defaults
            return {
                'bag_description': 'Standard suitcase',
                'last_known_location': bag_data['current_location'],
                'expected_destination': bag_data['flight']['destination'],
                'priority': 'normal'
            }
    
    async def submit_to_worldtracer(self, pir_details: Dict[str, Any]) -> str:
        """
        Submit PIR to WorldTracer API
        Returns PIR number
        """
        # Generate PIR number (in production, WorldTracer generates this)
        pir_number = f"{self.airline_code}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.worldtracer_url}/pir/create",
                    json={
                        'airline_code': self.airline_code,
                        'pir_details': pir_details
                    },
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json'
                    },
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    result = response.json()
                    pir_number = result.get('pir_number', pir_number)
                    logger.info(f"PIR submitted to WorldTracer: {pir_number}")
                else:
                    logger.warning(f"WorldTracer API returned {response.status_code}, using generated PIR number")
                    
        except Exception as e:
            logger.error(f"Error submitting to WorldTracer API: {str(e)}")
            logger.info(f"Using locally generated PIR number: {pir_number}")
        
        return pir_number
    
    async def store_pir(self, pir: WorldTracerPIR):
        """Store PIR in database"""
        pir_data = {
            'pir_number': pir.pir_number,
            'pir_type': pir.pir_type.value,
            'bag_tag': pir.bag_tag,
            'passenger_name': pir.passenger.name,
            'passenger_pnr': pir.passenger.pnr,
            'flight_number': pir.flight.flight_number,
            'bag_description': pir.bag_description,
            'contents_description': pir.contents_description,
            'last_known_location': pir.last_known_location,
            'expected_destination': pir.expected_destination,
            'status': pir.status,
            'created_at': pir.created_at.isoformat()
        }
        
        supabase_db.insert_worldtracer_pir(pir_data)
    
    async def match_found_bag(self, bag_tag: str) -> Dict[str, Any]:
        """
        Match a found bag with open PIRs
        """
        # Query open PIRs
        # In production, would search WorldTracer
        result = {
            'match_found': False,
            'pir_number': None,
            'action': 'forward_to_destination'
        }
        
        logger.info(f"Checking for PIR match for found bag {bag_tag}")
        return result


# Agent instance
worldtracer_agent = WorldTracerAgent()
