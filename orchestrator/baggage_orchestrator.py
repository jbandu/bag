"""
Baggage Operations Orchestrator
Coordinates all 8 agents using LangGraph multi-agent pattern
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from loguru import logger

from models.baggage_models import BaggageOperationsState, RiskLevel
from config.settings import settings

# Import all agents
from agents.scan_processor import scan_processor_agent
from agents.risk_scorer import risk_scoring_agent
from agents.worldtracer import worldtracer_agent
from agents.sita_handler import sita_message_agent
from agents.agents_5_to_8 import (
    baggage_xml_agent,
    case_manager_agent,
    courier_dispatch_agent,
    passenger_comms_agent
)


class BaggageOperationsOrchestrator:
    """
    Master orchestrator coordinating all 8 specialized agents
    
    Workflow:
    1. Scan Event → Process → Risk Assessment
    2. If High Risk → Exception Handling Flow
    3. Exception Flow: WorldTracer + Case + Courier + Communications
    4. If Normal Risk → Continue Monitoring
    """
    
    def __init__(self):
        self.graph = self.build_orchestration_graph()
        logger.info("BaggageOperationsOrchestrator initialized")
    
    def build_orchestration_graph(self) -> StateGraph:
        """
        Build the agent coordination workflow using LangGraph
        """
        workflow = StateGraph(BaggageOperationsState)
        
        # Add nodes (agent actions)
        workflow.add_node("process_scan", self.process_scan_node)
        workflow.add_node("assess_risk", self.assess_risk_node)
        workflow.add_node("handle_exception", self.handle_exception_node)
        workflow.add_node("normal_monitoring", self.normal_monitoring_node)
        workflow.add_node("update_metrics", self.update_metrics_node)
        
        # Set entry point
        workflow.set_entry_point("process_scan")
        
        # Add edges
        workflow.add_edge("process_scan", "assess_risk")
        workflow.add_conditional_edges(
            "assess_risk",
            self.risk_routing_decision,
            {
                "high_risk": "handle_exception",
                "normal": "normal_monitoring"
            }
        )
        workflow.add_edge("handle_exception", "update_metrics")
        workflow.add_edge("normal_monitoring", "update_metrics")
        workflow.add_edge("update_metrics", END)
        
        return workflow.compile()
    
    async def process_scan_node(self, state: BaggageOperationsState) -> Dict[str, Any]:
        """
        Node 1: Process scan event
        Uses: Agent 1 (Scan Processor), Agent 4 (SITA Handler)
        """
        logger.info("=== Processing Scan Event ===")
        
        try:
            # Check if this is a Type B message
            if state.raw_scan and state.raw_scan.startswith(('BTM', 'BSM', 'BPM')):
                logger.info("Type B message detected, using SITA handler")
                type_b_result = await sita_message_agent.process_type_b_message(state.raw_scan)
                # Extract bag tags and process each
                # For now, just log
                logger.info(f"Type B message processed: {type_b_result['message_type']}")
            
            # Process scan with Agent 1
            scan_result = await scan_processor_agent.process_scan(state.raw_scan)
            
            # Update state
            return {
                "parsed_event": scan_result['parsed_event'],
                "scan_event": scan_result['parsed_event'],
                "is_valid_sequence": scan_result['is_valid_sequence'],
                "actions_completed": state.actions_completed + ["scan_processed"]
            }
            
        except Exception as e:
            logger.error(f"Error in process_scan_node: {str(e)}")
            return {"is_valid_sequence": False}
    
    async def assess_risk_node(self, state: BaggageOperationsState) -> Dict[str, Any]:
        """
        Node 2: Assess baggage risk
        Uses: Agent 2 (Risk Scorer)
        """
        logger.info("=== Assessing Risk ===")
        
        try:
            bag_tag = state.parsed_event['bag_tag']
            
            # Get risk assessment from Agent 2
            risk_assessment = await risk_scoring_agent.score_baggage_risk(bag_tag)
            
            # Determine if exception handling needed
            requires_exception = risk_assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            
            logger.info(
                f"Risk assessed: Score={risk_assessment.risk_score:.2f}, "
                f"Level={risk_assessment.risk_level}, "
                f"Exception Required={requires_exception}"
            )
            
            return {
                "risk_assessment": risk_assessment,
                "requires_exception_handling": requires_exception,
                "actions_completed": state.actions_completed + ["risk_assessed"]
            }
            
        except Exception as e:
            logger.error(f"Error in assess_risk_node: {str(e)}")
            return {"requires_exception_handling": False}
    
    def risk_routing_decision(self, state: BaggageOperationsState) -> Literal["high_risk", "normal"]:
        """
        Conditional edge: Route based on risk level
        """
        if state.requires_exception_handling:
            logger.info("→ Routing to exception handling")
            return "high_risk"
        else:
            logger.info("→ Routing to normal monitoring")
            return "normal"
    
    async def handle_exception_node(self, state: BaggageOperationsState) -> Dict[str, Any]:
        """
        Node 3: Handle exception with multiple agents
        Uses: Agent 3 (WorldTracer), Agent 6 (Case Manager), 
              Agent 7 (Courier Dispatch), Agent 8 (Communications)
        """
        logger.info("=== Handling Exception ===")
        
        try:
            bag_tag = state.parsed_event['bag_tag']
            risk_assessment = state.risk_assessment
            
            # Prepare bag data (in production, would fetch from DCS/database)
            bag_data = await self._prepare_bag_data(state)
            
            # Execute agents in parallel where possible
            results = await asyncio.gather(
                # Agent 3: Create WorldTracer PIR
                self._create_worldtracer_pir(bag_data),
                
                # Agent 6: Create exception case
                self._create_exception_case(risk_assessment, bag_data),
                
                # Agent 7: Evaluate courier dispatch
                self._evaluate_courier(bag_data),
                
                # Agent 8: Notify passenger
                self._notify_passenger(bag_data, risk_assessment),
                
                return_exceptions=True
            )
            
            worldtracer_result, case_result, courier_result, comms_result = results
            
            logger.info("Exception handling complete")
            
            return {
                "worldtracer_pir": worldtracer_result if not isinstance(worldtracer_result, Exception) else None,
                "exception_case": case_result if not isinstance(case_result, Exception) else None,
                "courier_dispatch": courier_result if not isinstance(courier_result, Exception) else None,
                "notifications_sent": [comms_result] if not isinstance(comms_result, Exception) else [],
                "actions_completed": state.actions_completed + ["exception_handled"],
                "processing_completed_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error in handle_exception_node: {str(e)}")
            return {"actions_completed": state.actions_completed + ["exception_handling_failed"]}
    
    async def normal_monitoring_node(self, state: BaggageOperationsState) -> Dict[str, Any]:
        """
        Node 4: Normal monitoring (no exceptions)
        """
        logger.info("=== Normal Monitoring ===")
        
        # Just log and continue tracking
        logger.info(
            f"Bag {state.parsed_event['bag_tag']} tracking normally. "
            f"Risk: {state.risk_assessment.risk_level}"
        )
        
        return {
            "actions_completed": state.actions_completed + ["monitoring_active"],
            "processing_completed_at": datetime.utcnow()
        }
    
    async def update_metrics_node(self, state: BaggageOperationsState) -> Dict[str, Any]:
        """
        Node 5: Update operational metrics
        """
        logger.info("=== Updating Metrics ===")
        
        from utils.database import redis_cache
        
        # Update metrics
        redis_cache.increment_metric('bags_processed')
        
        if state.requires_exception_handling:
            redis_cache.increment_metric('exceptions_handled')
        
        if state.worldtracer_pir:
            redis_cache.increment_metric('pirs_created')
        
        if state.courier_dispatch:
            redis_cache.increment_metric('couriers_dispatched')
        
        logger.info("Metrics updated")
        return {}
    
    # Helper methods
    
    async def _prepare_bag_data(self, state: BaggageOperationsState) -> Dict[str, Any]:
        """Prepare comprehensive bag data for agents"""
        # In production, would fetch from DCS/database
        # For now, use available data
        return {
            'bag_tag': state.parsed_event['bag_tag'],
            'current_location': state.parsed_event['location'],
            'status': state.parsed_event['status'],
            'passenger': {
                'name': 'John Smith',  # Would come from DCS
                'pnr': 'ABC123',
                'email': 'john.smith@example.com',
                'phone': '+1234567890',
                'elite_status': 'Gold',
                'lifetime_value': 5000.0
            },
            'flight': {
                'flight_number': state.parsed_event.get('flight_number', 'CM101'),
                'origin': 'PTY',
                'destination': 'MIA',
                'scheduled_departure': datetime.utcnow().isoformat(),
                'scheduled_arrival': datetime.utcnow().isoformat(),
                'aircraft_type': 'B738',
                'status': 'active'
            },
            'routing': ['PTY', 'MIA'],
            'weight_kg': 23.0,
            'contents_value': 500.0,
            'special_handling': []
        }
    
    async def _create_worldtracer_pir(self, bag_data: Dict) -> Any:
        """Create WorldTracer PIR"""
        try:
            return await worldtracer_agent.handle_mishandled_bag(bag_data)
        except Exception as e:
            logger.error(f"WorldTracer PIR creation failed: {str(e)}")
            return None
    
    async def _create_exception_case(self, risk_assessment: Any, bag_data: Dict) -> Any:
        """Create exception case"""
        try:
            # Convert risk_assessment to dict if needed
            risk_dict = (
                risk_assessment.dict() 
                if hasattr(risk_assessment, 'dict') 
                else risk_assessment
            )
            return await case_manager_agent.create_exception_case(risk_dict, bag_data)
        except Exception as e:
            logger.error(f"Exception case creation failed: {str(e)}")
            return None
    
    async def _evaluate_courier(self, bag_data: Dict) -> Any:
        """Evaluate courier dispatch"""
        try:
            return await courier_dispatch_agent.evaluate_courier_dispatch(bag_data)
        except Exception as e:
            logger.error(f"Courier evaluation failed: {str(e)}")
            return None
    
    async def _notify_passenger(self, bag_data: Dict, risk_assessment: Any) -> Any:
        """Send passenger notification"""
        try:
            risk_dict = (
                risk_assessment.dict() 
                if hasattr(risk_assessment, 'dict') 
                else risk_assessment
            )
            risk_dict['situation_summary'] = f"Bag at risk: {risk_dict.get('reasoning', 'Unknown')}"
            risk_dict['expected_resolution'] = "Within 24 hours"
            return await passenger_comms_agent.send_proactive_notification(bag_data, risk_dict)
        except Exception as e:
            logger.error(f"Passenger notification failed: {str(e)}")
            return None
    
    # Main execution method
    
    async def process_baggage_event(self, raw_scan: str) -> Dict[str, Any]:
        """
        Main entry point: Process a baggage event through the entire pipeline
        """
        logger.info("=" * 60)
        logger.info("BAGGAGE EVENT PROCESSING STARTED")
        logger.info("=" * 60)
        
        # Create initial state
        initial_state = BaggageOperationsState(
            raw_scan=raw_scan,
            actions_completed=[],
            processing_started_at=datetime.utcnow()
        )
        
        try:
            # Run the graph
            result_state = await self.graph.ainvoke(initial_state)
            
            logger.info("=" * 60)
            logger.info("BAGGAGE EVENT PROCESSING COMPLETED")
            logger.info(f"Actions completed: {result_state.get('actions_completed', [])}")
            logger.info("=" * 60)
            
            return {
                'status': 'success',
                'bag_tag': result_state.get('parsed_event', {}).get('bag_tag'),
                'risk_level': str(result_state.get('risk_assessment', {}).get('risk_level')),
                'actions_completed': result_state.get('actions_completed', []),
                'processing_time': (
                    result_state.get('processing_completed_at', datetime.utcnow()) -
                    initial_state.processing_started_at
                ).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Error in baggage event processing: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }


# Global orchestrator instance
orchestrator = BaggageOperationsOrchestrator()
