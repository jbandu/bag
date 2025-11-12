"""
Agent 2: Risk Scoring Engine
Predictive mishandling detection using multiple factors
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from langchain_anthropic import ChatAnthropic
from loguru import logger

from models.baggage_models import RiskAssessment, RiskLevel
from config.settings import settings
from utils.database import neo4j_db, supabase_db, redis_cache


class BaggageRiskScoringAgent:
    """
    Agent responsible for:
    1. Analyzing multiple risk factors
    2. Predicting mishandling probability
    3. Recommending preventive actions
    4. Scoring bag routing complexity
    """
    
    def __init__(self):
        self.llm = ChatAnthropic(
            model=settings.model_name,
            temperature=settings.model_temperature,
            api_key=settings.anthropic_api_key
        )
        logger.info("BaggageRiskScoringAgent initialized")
    
    async def score_baggage_risk(self, bag_tag: str) -> RiskAssessment:
        """
        Main risk scoring pipeline
        Returns comprehensive risk assessment
        """
        try:
            # Step 1: Gather all risk context
            context = await self.gather_risk_context(bag_tag)
            
            # Step 2: AI-powered risk analysis
            risk_result = await self.analyze_risk(context)
            
            # Step 3: Create risk assessment object
            assessment = RiskAssessment(
                bag_tag=bag_tag,
                risk_score=risk_result['risk_score'],
                risk_level=self._determine_risk_level(risk_result['risk_score']),
                primary_factors=risk_result['primary_factors'],
                recommended_action=risk_result['recommended_action'],
                confidence=risk_result['confidence'],
                reasoning=risk_result['reasoning'],
                connection_time_minutes=context.get('connection_time_minutes'),
                mct_minutes=context.get('mct_minutes'),
                airport_performance_score=context.get('airport_performance_score'),
                weather_impact_score=context.get('weather_impact_score')
            )
            
            # Step 4: Store assessment
            await self.store_assessment(assessment)
            
            # Step 5: Update digital twin with risk score
            neo4j_db.update_risk_score(
                bag_tag,
                assessment.risk_score,
                assessment.primary_factors
            )
            
            # Step 6: Increment metrics
            redis_cache.increment_metric('risk_assessments_performed')
            if assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                redis_cache.increment_metric('high_risk_bags_detected')
            
            logger.info(
                f"Risk assessment complete for bag {bag_tag}: "
                f"Score={assessment.risk_score:.2f}, Level={assessment.risk_level}"
            )
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error in risk scoring for bag {bag_tag}: {str(e)}")
            raise
    
    async def gather_risk_context(self, bag_tag: str) -> Dict[str, Any]:
        """
        Gather all relevant context for risk assessment
        """
        # Get bag data
        bag_data = supabase_db.get_bag_data(bag_tag)
        if not bag_data:
            raise ValueError(f"No data found for bag {bag_tag}")
        
        # Get journey history
        journey = neo4j_db.get_bag_journey(bag_tag)
        
        # Calculate connection time if applicable
        connection_time = None
        mct = None
        if bag_data.get('next_flight'):
            connection_time = self._calculate_connection_time(bag_data)
            mct = self._get_mct(bag_data['current_location'], bag_data.get('connection_type'))
        
        # Get airport performance metrics
        airport_perf = await self._get_airport_performance(bag_data['current_location'])
        
        # Check for recent scans
        last_scan_time = journey[-1]['timestamp'] if journey else None
        time_since_last_scan = None
        if last_scan_time:
            if isinstance(last_scan_time, str):
                last_scan_time = datetime.fromisoformat(last_scan_time)
            time_since_last_scan = (datetime.utcnow() - last_scan_time).total_seconds() / 60
        
        # Historical mishandling rate for this route
        historical_rate = await self._get_historical_mishandling_rate(bag_data.get('routing', []))
        
        # Check for weather/IRROPS
        weather_impact = await self._assess_weather_impact(bag_data['current_location'])
        
        context = {
            'bag_data': bag_data,
            'journey': journey,
            'connection_time_minutes': connection_time,
            'mct_minutes': mct,
            'airport_performance_score': airport_perf,
            'time_since_last_scan_minutes': time_since_last_scan,
            'historical_mishandling_rate': historical_rate,
            'weather_impact_score': weather_impact,
            'routing_complexity': len(bag_data.get('routing', [])),
            'special_handling': bag_data.get('special_handling', [])
        }
        
        return context
    
    async def analyze_risk(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI-powered risk analysis
        """
        bag_data = context['bag_data']
        
        prompt = f"""Analyze baggage mishandling risk for this bag:

**Bag Information:**
- Tag: {bag_data['bag_tag']}
- Current Status: {bag_data['status']}
- Current Location: {bag_data['current_location']}
- Routing: {bag_data.get('routing', [])}
- Routing Complexity: {context['routing_complexity']} connections
- Special Handling: {context['special_handling']}

**Connection Analysis:**
- Connection Time: {context.get('connection_time_minutes', 'N/A')} minutes
- Minimum Connection Time (MCT): {context.get('mct_minutes', 'N/A')} minutes
- MCT Buffer: {(context.get('connection_time_minutes', 999) - context.get('mct_minutes', 0)) if context.get('connection_time_minutes') else 'N/A'} minutes

**Operational Context:**
- Airport Performance Score: {context['airport_performance_score']}/10
- Time Since Last Scan: {context.get('time_since_last_scan_minutes', 'N/A')} minutes
- Historical Mishandling Rate: {context['historical_mishandling_rate']}%
- Weather Impact Score: {context['weather_impact_score']}/10

**Journey History:**
{json.dumps(context['journey'][-5:], indent=2, default=str)}  # Last 5 scans

**Risk Factor Analysis:**

High Risk Indicators:
- Connection time < MCT + 15 minutes
- No scan for > 30 minutes when bag should be active
- Airport performance score < 6
- Historical mishandling rate > 10%
- Weather impact score > 7
- 3+ connections in routing
- Special handling requirements

Analyze and return JSON:
{{
    "risk_score": 0.0-1.0,  # Overall risk probability
    "confidence": 0.0-1.0,   # Confidence in assessment
    "primary_factors": [
        "factor 1 description",
        "factor 2 description",
        ...
    ],
    "recommended_action": "monitor|alert_team|auto_intervene|dispatch_courier",
    "reasoning": "concise explanation of risk assessment",
    "risk_breakdown": {{
        "connection_risk": 0.0-1.0,
        "scan_gap_risk": 0.0-1.0,
        "airport_risk": 0.0-1.0,
        "weather_risk": 0.0-1.0,
        "routing_complexity_risk": 0.0-1.0
    }}
}}

**Risk Score Guidelines:**
- 0.0-0.3: Low risk (normal operations)
- 0.3-0.7: Medium risk (monitor closely)
- 0.7-0.9: High risk (intervention likely needed)
- 0.9-1.0: Critical risk (immediate action required)

**Action Recommendations:**
- monitor: Continue normal tracking
- alert_team: Notify baggage operations team
- auto_intervene: System takes preventive action (e.g., hold bag, reroute)
- dispatch_courier: High probability of miss - prepare courier dispatch

Return ONLY valid JSON."""

        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        
        try:
            risk_analysis = json.loads(response.content)
            return risk_analysis
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse risk analysis response: {str(e)}")
            # Return safe default
            return {
                'risk_score': 0.5,
                'confidence': 0.3,
                'primary_factors': ['Unable to complete risk analysis'],
                'recommended_action': 'monitor',
                'reasoning': 'Analysis failed, defaulting to monitoring'
            }
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Convert risk score to risk level"""
        if risk_score >= settings.critical_risk_threshold:
            return RiskLevel.CRITICAL
        elif risk_score >= settings.high_risk_threshold:
            return RiskLevel.HIGH
        elif risk_score >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_connection_time(self, bag_data: Dict[str, Any]) -> Optional[int]:
        """Calculate connection time in minutes"""
        if not bag_data.get('next_flight_departure'):
            return None
        
        try:
            arrival = datetime.fromisoformat(bag_data.get('current_flight_arrival', ''))
            departure = datetime.fromisoformat(bag_data['next_flight_departure'])
            connection_time = (departure - arrival).total_seconds() / 60
            return int(connection_time)
        except Exception:
            return None
    
    def _get_mct(self, airport: str, connection_type: Optional[str] = None) -> int:
        """Get Minimum Connection Time for airport"""
        # Simplified MCT lookup
        # In production, would query actual MCT database by airport and connection type
        default_mct = {
            'domestic': 45,
            'international': 60,
            'international_to_domestic': 75,
            'domestic_to_international': 90
        }
        return default_mct.get(connection_type, 60)
    
    async def _get_airport_performance(self, airport_code: str) -> float:
        """Get historical airport performance score (0-10)"""
        # In production, would query historical data
        # For now, return mock data
        airport_scores = {
            'PTY': 8.5,  # Copa hub - excellent
            'MIA': 7.2,
            'JFK': 6.8,
            'EWR': 6.5,
            'ORD': 6.9,
            'LHR': 7.5,
            'default': 7.0
        }
        code = airport_code.split('-')[0]  # Extract airport code from location
        return airport_scores.get(code, airport_scores['default'])
    
    async def _get_historical_mishandling_rate(self, routing: list) -> float:
        """Get historical mishandling rate for this route"""
        # In production, would query historical data
        # For now, return mock data based on complexity
        complexity = len(routing)
        if complexity <= 2:
            return 3.5  # Direct flight - low rate
        elif complexity == 3:
            return 6.2  # One connection - moderate rate
        else:
            return 9.8  # Multiple connections - higher rate
    
    async def _assess_weather_impact(self, location: str) -> float:
        """Assess weather impact score (0-10)"""
        # In production, would integrate with weather API
        # For now, return mock score
        return 3.5  # Normal conditions
    
    async def store_assessment(self, assessment: RiskAssessment):
        """Store risk assessment in database"""
        assessment_data = {
            'bag_tag': assessment.bag_tag,
            'risk_score': assessment.risk_score,
            'risk_level': assessment.risk_level.value,
            'primary_factors': assessment.primary_factors,
            'recommended_action': assessment.recommended_action,
            'confidence': assessment.confidence,
            'reasoning': assessment.reasoning,
            'connection_time_minutes': assessment.connection_time_minutes,
            'mct_minutes': assessment.mct_minutes,
            'airport_performance_score': assessment.airport_performance_score,
            'weather_impact_score': assessment.weather_impact_score,
            'timestamp': assessment.timestamp.isoformat()
        }
        
        supabase_db.insert_risk_assessment(assessment_data)


# Agent instance
risk_scoring_agent = BaggageRiskScoringAgent()
