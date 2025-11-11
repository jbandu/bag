"""
Agent 5: BaggageXML API Handler
Agent 6: Exception Case Manager
Agent 7: Courier Dispatch Agent
Agent 8: Passenger Communication Agent
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from langchain_anthropic import ChatAnthropic
from loguru import logger
import httpx
import xmltodict

from models.baggage_models import ExceptionCase, CourierDispatch, PassengerNotification, RiskLevel
from config.settings import settings
from utils.database import supabase_db, redis_cache


# ============================================================================
# AGENT 5: BaggageXML API Handler
# ============================================================================

class BaggageXMLAgent:
    """
    Modern XML-based baggage messaging for interline transfers
    """
    
    def __init__(self):
        self.llm = ChatAnthropic(
            model=settings.model_name,
            temperature=0.1,
            api_key=settings.anthropic_api_key
        )
        logger.info("BaggageXMLAgent initialized")
    
    async def send_baggage_manifest(self, flight_id: str, bags: List[Dict]) -> Dict[str, Any]:
        """Send BaggageXML manifest to downline airline"""
        try:
            # Generate compliant XML
            xml_manifest = await self._generate_baggage_xml(flight_id, bags)
            
            # Send to downline DCS
            response = await self._send_to_downline(xml_manifest)
            
            logger.info(f"Baggage manifest sent for flight {flight_id}: {len(bags)} bags")
            return {
                'status': 'sent',
                'flight_id': flight_id,
                'bags_count': len(bags),
                'sent_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending baggage manifest: {str(e)}")
            raise
    
    async def _generate_baggage_xml(self, flight_id: str, bags: List[Dict]) -> str:
        """Generate IATA-compliant BaggageXML"""
        prompt = f"""Generate IATA BaggageXML manifest:

Flight: {flight_id}
Transfer Bags: {len(bags)}

Bags:
{json.dumps(bags, indent=2)}

Create complete XML with all required IATA elements:
- Flight details
- Bag tag numbers, weights, destinations
- Special handling codes
- Passenger information
- Validation checksums

Return valid BaggageXML."""

        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        return response.content
    
    async def _send_to_downline(self, xml_content: str) -> Dict:
        """Send XML to downline airline"""
        # In production, would send to actual DCS endpoint
        return {'status': 'accepted'}


# ============================================================================
# AGENT 6: Exception Case Manager
# ============================================================================

class ExceptionCaseAgent:
    """
    Manages exception cases for mishandled baggage
    """
    
    def __init__(self):
        self.llm = ChatAnthropic(
            model=settings.model_name,
            temperature=0.2,
            api_key=settings.anthropic_api_key
        )
        logger.info("ExceptionCaseAgent initialized")
    
    async def create_exception_case(self, risk_assessment: Dict[str, Any], bag_data: Dict[str, Any]) -> ExceptionCase:
        """Create and route exception case"""
        try:
            # Determine case details using AI
            case_details = await self._determine_case_details(risk_assessment, bag_data)
            
            # Create case
            case = ExceptionCase(
                bag_tag=bag_data['bag_tag'],
                priority=case_details['priority'],
                assigned_to=case_details['assigned_to'],
                risk_assessment=risk_assessment,
                sla_deadline=datetime.utcnow() + timedelta(hours=case_details['sla_hours'])
            )
            
            # Store in database
            await self._store_case(case)
            
            # Alert assigned team
            await self._alert_team(case)
            
            logger.info(f"Exception case created: {case.case_id} (Priority: {case.priority})")
            return case
            
        except Exception as e:
            logger.error(f"Error creating exception case: {str(e)}")
            raise
    
    async def _determine_case_details(self, risk_assessment: Dict, bag_data: Dict) -> Dict[str, Any]:
        """AI determines case priority and routing"""
        prompt = f"""Determine exception case details:

Risk Assessment:
- Score: {risk_assessment['risk_score']}
- Factors: {risk_assessment['primary_factors']}

Bag Data:
- Passenger Elite Status: {bag_data.get('passenger', {}).get('elite_status', 'None')}
- Connection Time: {risk_assessment.get('connection_time_minutes', 'N/A')} min
- Special Handling: {bag_data.get('special_handling', [])}

Return JSON:
{{
    "priority": "P0|P1|P2|P3",
    "assigned_to": "team name",
    "sla_hours": hours_until_deadline,
    "recommended_actions": ["action1", "action2"],
    "escalation_path": ["team1", "team2"]
}}

Priority Guidelines:
- P0 (Critical): Risk > 0.9, elite passenger, imminent departure
- P1 (High): Risk > 0.7, premium passenger, <2hr to departure
- P2 (Medium): Risk > 0.5, <6hr to departure
- P3 (Low): Risk < 0.5, >6hr to departure

Teams:
- Baggage Operations: Normal cases
- Customer Service: Elite passengers
- Ground Handling: Time-critical transfers
- Station Manager: Critical escalations

Return ONLY valid JSON."""

        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        return json.loads(response.content)
    
    async def _store_case(self, case: ExceptionCase):
        """Store case in database"""
        case_data = {
            'case_id': case.case_id,
            'bag_tag': case.bag_tag,
            'priority': case.priority,
            'assigned_to': case.assigned_to,
            'status': case.status,
            'risk_score': case.risk_assessment.get('risk_score'),
            'created_at': case.created_at.isoformat(),
            'sla_deadline': case.sla_deadline.isoformat() if case.sla_deadline else None
        }
        supabase_db.create_exception_case(case_data)
    
    async def _alert_team(self, case: ExceptionCase):
        """Alert assigned team about new case"""
        # In production, would send to team's communication channel
        logger.info(f"Alert sent to {case.assigned_to} for case {case.case_id}")


# ============================================================================
# AGENT 7: Courier Dispatch Agent
# ============================================================================

class CourierDispatchAgent:
    """
    Automates courier dispatch decisions with human-in-the-loop for high value
    """
    
    def __init__(self):
        self.llm = ChatAnthropic(
            model=settings.model_name,
            temperature=0.2,
            api_key=settings.anthropic_api_key
        )
        logger.info("CourierDispatchAgent initialized")
    
    async def evaluate_courier_dispatch(self, bag_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decide if courier dispatch is cost-effective"""
        try:
            # Calculate costs
            airline_credit = self._calculate_montreal_convention_cost(bag_data)
            courier_cost = await self._get_courier_quote(bag_data)
            
            # AI recommendation
            decision = await self._make_dispatch_decision(bag_data, airline_credit, courier_cost)
            
            if decision['requires_approval']:
                # Human-in-the-loop for high-value cases
                logger.info(f"Courier dispatch for bag {bag_data['bag_tag']} requires approval")
                return {
                    'status': 'pending_approval',
                    'decision': decision,
                    'courier_cost': courier_cost,
                    'potential_claim_cost': airline_credit
                }
            else:
                # Auto-dispatch
                return await self._dispatch_courier(bag_data, decision, courier_cost, airline_credit)
                
        except Exception as e:
            logger.error(f"Error evaluating courier dispatch: {str(e)}")
            raise
    
    def _calculate_montreal_convention_cost(self, bag_data: Dict) -> float:
        """Calculate potential liability under Montreal Convention"""
        # Montreal Convention: ~$1,500 USD max
        base_cost = settings.montreal_convention_max_usd
        
        # Adjust for passenger status
        if bag_data.get('passenger', {}).get('elite_status') in ['Gold', 'Platinum', 'Diamond']:
            # Add goodwill cost for elite passengers
            base_cost += 500
        
        return base_cost
    
    async def _get_courier_quote(self, bag_data: Dict) -> float:
        """Get courier quote for delivery"""
        # In production, would call courier API
        # Mock pricing based on distance/urgency
        base_rate = 75.0
        if bag_data.get('delivery_urgency') == 'same_day':
            base_rate *= 1.5
        return base_rate
    
    async def _make_dispatch_decision(self, bag_data: Dict, airline_credit: float, courier_cost: float) -> Dict:
        """AI-powered dispatch decision"""
        prompt = f"""Should we dispatch courier for this bag?

Financial:
- Montreal Convention potential cost: ${airline_credit:.2f}
- Courier delivery cost: ${courier_cost:.2f}
- Passenger lifetime value: ${bag_data.get('passenger', {}).get('lifetime_value', 1000):.2f}
- Cost-benefit ratio: {courier_cost/airline_credit:.2f}

Context:
- Passenger status: {bag_data.get('passenger', {}).get('elite_status', 'None')}
- Bag contents value: ${bag_data.get('contents_value', 0):.2f}
- Delivery urgency: {bag_data.get('delivery_urgency', 'normal')}

Decision Framework:
- If courier_cost < 0.5 * airline_credit: auto-approve
- If passenger is elite: prioritize customer experience
- If contents value > $1000: require human approval
- If cost-benefit ratio > 0.8: require approval

Return JSON:
{{
    "approve_dispatch": true/false,
    "requires_approval": true/false,
    "reasoning": "explanation",
    "courier_vendor": "preferred vendor",
    "delivery_priority": "standard|same_day|urgent"
}}

Return ONLY valid JSON."""

        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        return json.loads(response.content)
    
    async def _dispatch_courier(self, bag_data: Dict, decision: Dict, courier_cost: float, potential_claim: float) -> Dict:
        """Execute courier dispatch"""
        dispatch = CourierDispatch(
            bag_tag=bag_data['bag_tag'],
            courier_vendor=decision['courier_vendor'],
            pickup_location=bag_data['current_location'],
            delivery_address=bag_data.get('delivery_address', 'TBD'),
            estimated_delivery=datetime.utcnow() + timedelta(hours=4),
            courier_cost=courier_cost,
            potential_claim_cost=potential_claim,
            cost_benefit_ratio=courier_cost / potential_claim,
            status='dispatched'
        )
        
        # Store dispatch record
        dispatch_data = {
            'dispatch_id': dispatch.dispatch_id,
            'bag_tag': dispatch.bag_tag,
            'courier_vendor': dispatch.courier_vendor,
            'pickup_location': dispatch.pickup_location,
            'delivery_address': dispatch.delivery_address,
            'estimated_delivery': dispatch.estimated_delivery.isoformat(),
            'courier_cost': dispatch.courier_cost,
            'potential_claim_cost': dispatch.potential_claim_cost,
            'status': dispatch.status,
            'created_at': dispatch.created_at.isoformat()
        }
        supabase_db.create_courier_dispatch(dispatch_data)
        
        logger.info(f"Courier dispatched for bag {bag_data['bag_tag']}")
        return {'status': 'dispatched', 'dispatch_id': dispatch.dispatch_id}


# ============================================================================
# AGENT 8: Passenger Communication Agent
# ============================================================================

class PassengerCommunicationAgent:
    """
    Multi-channel passenger notifications
    """
    
    def __init__(self):
        self.llm = ChatAnthropic(
            model=settings.model_name,
            temperature=0.7,  # More creative for messaging
            api_key=settings.anthropic_api_key
        )
        logger.info("PassengerCommunicationAgent initialized")
    
    async def send_proactive_notification(self, bag_data: Dict, risk_data: Dict) -> Dict[str, Any]:
        """Send proactive notification before passenger knows there's an issue"""
        try:
            # Generate empathetic messages
            messages = await self._craft_messages(bag_data, risk_data)
            
            # Send via multiple channels
            delivery_status = await self._send_multi_channel(
                bag_data['passenger'],
                messages
            )
            
            # Log notification
            await self._log_notification(bag_data, messages, delivery_status)
            
            logger.info(f"Proactive notification sent for bag {bag_data['bag_tag']}")
            return {
                'status': 'sent',
                'channels': list(delivery_status.keys()),
                'delivery_status': delivery_status
            }
            
        except Exception as e:
            logger.error(f"Error sending passenger notification: {str(e)}")
            raise
    
    async def _craft_messages(self, bag_data: Dict, risk_data: Dict) -> Dict[str, str]:
        """AI crafts empathetic, solution-focused messages"""
        prompt = f"""Craft passenger notification for delayed bag:

Passenger: {bag_data['passenger']['name']}
Elite Status: {bag_data['passenger'].get('elite_status', 'None')}
Situation: {risk_data.get('situation_summary', 'Bag delayed')}
Expected Resolution: {risk_data.get('expected_resolution', 'Within 24 hours')}

Tone: Empathetic, proactive, solution-focused
Audience: {bag_data['passenger'].get('elite_status', 'Standard')} passenger

Create 3 versions:

1. SMS (max 160 characters):
   - What happened (very brief)
   - What we're doing
   - When they'll get bag

2. Email (200-300 words):
   - Acknowledge inconvenience
   - Explain situation clearly
   - Detail our actions
   - Provide tracking link
   - Offer compensation
   - Contact information

3. Push notification (50 characters):
   - Ultra-brief status update

Return JSON:
{{
    "sms": "message",
    "email_subject": "subject line",
    "email_body": "email content",
    "push": "push notification"
}}

Return ONLY valid JSON."""

        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        return json.loads(response.content)
    
    async def _send_multi_channel(self, passenger: Dict, messages: Dict) -> Dict[str, str]:
        """Send via SMS, Email, Push"""
        delivery_status = {}
        
        # SMS
        if passenger.get('phone'):
            try:
                await self._send_sms(passenger['phone'], messages['sms'])
                delivery_status['sms'] = 'delivered'
            except Exception as e:
                logger.error(f"SMS delivery failed: {str(e)}")
                delivery_status['sms'] = 'failed'
        
        # Email
        if passenger.get('email'):
            try:
                await self._send_email(
                    passenger['email'],
                    messages['email_subject'],
                    messages['email_body']
                )
                delivery_status['email'] = 'delivered'
            except Exception as e:
                logger.error(f"Email delivery failed: {str(e)}")
                delivery_status['email'] = 'failed'
        
        # Push notification
        if passenger.get('user_id'):
            try:
                await self._send_push(passenger['user_id'], messages['push'])
                delivery_status['push'] = 'delivered'
            except Exception as e:
                logger.error(f"Push notification failed: {str(e)}")
                delivery_status['push'] = 'failed'
        
        return delivery_status
    
    async def _send_sms(self, phone: str, message: str):
        """Send SMS via Twilio"""
        # In production, would use Twilio API
        logger.info(f"SMS sent to {phone}: {message[:50]}...")
    
    async def _send_email(self, email: str, subject: str, body: str):
        """Send email via SendGrid"""
        # In production, would use SendGrid API
        logger.info(f"Email sent to {email}: {subject}")
    
    async def _send_push(self, user_id: str, message: str):
        """Send push notification via Firebase"""
        # In production, would use Firebase API
        logger.info(f"Push notification sent to user {user_id}")
    
    async def _log_notification(self, bag_data: Dict, messages: Dict, delivery_status: Dict):
        """Log notification in database"""
        notification_data = {
            'bag_tag': bag_data['bag_tag'],
            'passenger_name': bag_data['passenger']['name'],
            'message_type': 'proactive',
            'channels': list(delivery_status.keys()),
            'sms_content': messages.get('sms'),
            'email_content': messages.get('email_body'),
            'push_content': messages.get('push'),
            'sent_at': datetime.utcnow().isoformat(),
            'delivery_status': delivery_status
        }
        supabase_db.log_notification(notification_data)


# Agent instances
baggage_xml_agent = BaggageXMLAgent()
case_manager_agent = ExceptionCaseAgent()
courier_dispatch_agent = CourierDispatchAgent()
passenger_comms_agent = PassengerCommunicationAgent()
