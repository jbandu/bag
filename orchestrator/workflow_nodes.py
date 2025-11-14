"""
Workflow Nodes
==============

Node definitions for LangGraph orchestrator.

Each node represents an agent invocation or workflow action.
Nodes receive state, perform action, update state, and return.

Version: 1.0.0
Date: 2025-11-14
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
import uuid
import time

from orchestrator.workflow_state import (
    BaggageWorkflowState,
    WorkflowStep,
    NodeStatus,
    RiskAssessment,
    RiskLevel,
    ExceptionCase,
    PIRInfo,
    PIRStatus,
    CourierBooking,
    HumanApproval,
    Notification,
    add_workflow_step,
    update_workflow_status,
    WorkflowStatus
)


# ============================================================================
# NODE HELPERS
# ============================================================================

def create_step(
    node_name: str,
    status: NodeStatus,
    reasoning: Optional[str] = None,
    expected_outcome: Optional[str] = None,
    input_data: Optional[Dict[str, Any]] = None
) -> WorkflowStep:
    """Create a workflow step"""
    return WorkflowStep(
        step_id=f"{node_name}_{uuid.uuid4().hex[:8]}",
        node_name=node_name,
        status=status,
        started_at=datetime.now().isoformat(),
        reasoning=reasoning,
        expected_outcome=expected_outcome,
        input_data=input_data
    )


def complete_step(
    step: WorkflowStep,
    status: NodeStatus,
    output_data: Optional[Dict[str, Any]] = None,
    actual_outcome: Optional[str] = None,
    error: Optional[str] = None
) -> WorkflowStep:
    """Complete a workflow step"""
    step.completed_at = datetime.now().isoformat()
    step.status = status
    step.output_data = output_data
    step.actual_outcome = actual_outcome
    step.error = error

    if step.started_at and step.completed_at:
        started = datetime.fromisoformat(step.started_at)
        completed = datetime.fromisoformat(step.completed_at)
        step.duration_ms = (completed - started).total_seconds() * 1000

    return step


# ============================================================================
# WORKFLOW NODES
# ============================================================================

def assess_risk_node(state: BaggageWorkflowState) -> BaggageWorkflowState:
    """
    Node: Assess bag risk using Risk Scorer agent

    Invokes Risk Scorer agent to analyze bag risk based on:
    - Flight patterns
    - Transfer times
    - Historical data
    - Passenger tier
    - Baggage value
    """
    step = create_step(
        node_name="assess_risk",
        status=NodeStatus.RUNNING,
        reasoning="Assess bag risk to determine handling priority and actions needed",
        expected_outcome="Risk score and level with confidence rating",
        input_data={"bag_tag": state["bag_tag"]}
    )

    try:
        logger.info(f"[assess_risk_node] Assessing risk for bag {state['bag_tag']}")

        # MOCK: In production, this would call the actual Risk Scorer agent
        # risk_result = risk_scorer_agent.assess_bag(state["bag_tag"])

        # Mock risk assessment
        bag_tag = state["bag_tag"]
        context = state.get("context", {})

        # Simulate risk scoring
        risk_score = context.get("risk_score", 0.75)  # Default medium-high risk
        value = context.get("bag_value", 350.0)
        passenger_tier = context.get("passenger_tier", "SILVER")

        # Determine risk level
        if risk_score >= 0.9:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 0.7:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.4:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        risk_assessment = RiskAssessment(
            bag_tag=bag_tag,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=[
                "Tight connection time",
                "High mishandling rate at origin",
                "Weather delays possible"
            ],
            confidence=0.85,
            assessed_at=datetime.now().isoformat(),
            value_estimate=value,
            passenger_tier=passenger_tier,
            flight_importance=context.get("flight_importance", "REGULAR")
        )

        # Update state
        state["risk_data"] = risk_assessment
        state["current_step"] = "assess_risk"

        # Complete step
        complete_step(
            step,
            status=NodeStatus.SUCCESS,
            output_data={"risk_score": risk_score, "risk_level": risk_level.value},
            actual_outcome=f"Risk assessed: {risk_level.value} ({risk_score:.2f})"
        )

        logger.info(f"[assess_risk_node] Risk: {risk_level.value} ({risk_score:.2f})")

    except Exception as e:
        logger.error(f"[assess_risk_node] Failed: {e}")
        complete_step(step, status=NodeStatus.FAILED, error=str(e))
        state["errors"].append(f"assess_risk: {str(e)}")

    # Add step to history
    add_workflow_step(state, step)

    return state


def create_case_node(state: BaggageWorkflowState) -> BaggageWorkflowState:
    """
    Node: Create exception case using Case Manager agent

    Creates exception case for bags requiring special handling.
    """
    step = create_step(
        node_name="create_case",
        status=NodeStatus.RUNNING,
        reasoning="Create exception case to track resolution and assign responsibility",
        expected_outcome="Exception case created with ID and status"
    )

    try:
        logger.info(f"[create_case_node] Creating case for bag {state['bag_tag']}")

        risk_data = state.get("risk_data")
        bag_tag = state["bag_tag"]

        # MOCK: In production, call Case Manager agent
        # case = case_manager_agent.create_case(bag_tag, risk_data)

        case = ExceptionCase(
            case_id=f"CASE{datetime.now().strftime('%Y%m%d%H%M%S')}",
            bag_tag=bag_tag,
            exception_type="HIGH_RISK_BAG",
            severity=risk_data.risk_level.value if risk_data else "MEDIUM",
            status="OPEN",
            created_at=datetime.now().isoformat(),
            description=f"High risk bag requiring special handling",
            assigned_to="ops_team",
            resolution_eta=None
        )

        state["exception_case"] = case

        complete_step(
            step,
            status=NodeStatus.SUCCESS,
            output_data={"case_id": case.case_id},
            actual_outcome=f"Case created: {case.case_id}"
        )

        logger.info(f"[create_case_node] Case created: {case.case_id}")

    except Exception as e:
        logger.error(f"[create_case_node] Failed: {e}")
        complete_step(step, status=NodeStatus.FAILED, error=str(e))
        state["errors"].append(f"create_case: {str(e)}")

    add_workflow_step(state, step)
    return state


def check_pir_node(state: BaggageWorkflowState) -> BaggageWorkflowState:
    """
    Node: Check if PIR exists in WorldTracer

    Queries WorldTracer to check if PIR already exists for this bag.
    """
    step = create_step(
        node_name="check_pir",
        status=NodeStatus.RUNNING,
        reasoning="Check if PIR already exists to avoid duplicate reporting",
        expected_outcome="PIR status (exists or not)"
    )

    try:
        logger.info(f"[check_pir_node] Checking PIR for bag {state['bag_tag']}")

        bag_tag = state["bag_tag"]
        context = state.get("context", {})

        # MOCK: In production, query WorldTracer
        # pir_status = worldtracer_agent.check_pir(bag_tag)

        pir_exists = context.get("pir_exists", False)

        if pir_exists:
            pir_info = PIRInfo(
                ohd_reference=f"LAXAA{datetime.now().strftime('%H%M%S')}",
                status=PIRStatus.CREATED,
                exists=True,
                created_at=datetime.now().isoformat(),
                station="LAX",
                irregularity_type="DELAYED"
            )
        else:
            pir_info = PIRInfo(
                status=PIRStatus.NOT_FOUND,
                exists=False
            )

        state["pir_status"] = pir_info

        complete_step(
            step,
            status=NodeStatus.SUCCESS,
            output_data={"pir_exists": pir_exists},
            actual_outcome=f"PIR {'found' if pir_exists else 'not found'}"
        )

        logger.info(f"[check_pir_node] PIR: {pir_info.status.value}")

    except Exception as e:
        logger.error(f"[check_pir_node] Failed: {e}")
        complete_step(step, status=NodeStatus.FAILED, error=str(e))
        state["errors"].append(f"check_pir: {str(e)}")

    add_workflow_step(state, step)
    return state


def request_approval_node(state: BaggageWorkflowState) -> BaggageWorkflowState:
    """
    Node: Request human approval for high-risk actions

    Human-in-the-loop for critical decisions.
    """
    step = create_step(
        node_name="request_approval",
        status=NodeStatus.RUNNING,
        reasoning="High-risk bag with high value requires human approval before courier dispatch",
        expected_outcome="Approval granted or denied"
    )

    try:
        logger.info(f"[request_approval_node] Requesting approval for bag {state['bag_tag']}")

        risk_data = state.get("risk_data")
        context = state.get("context", {})

        # MOCK: In production, create approval request in UI/notification system
        # approval_request = approval_system.create_request(...)

        approval = HumanApproval(
            approval_id=f"APPR{datetime.now().strftime('%Y%m%d%H%M%S')}",
            workflow_id=state["workflow_id"],
            request_type="COURIER_DISPATCH",
            requested_at=datetime.now().isoformat(),
            requested_by="orchestrator",
            risk_score=risk_data.risk_score if risk_data else None,
            estimated_cost=context.get("estimated_courier_cost", 150.0),
            passenger_tier=risk_data.passenger_tier if risk_data else None,
            reasoning="High risk (>0.9) and high value (>$500) requires approval"
        )

        # MOCK: Auto-approve for demo (in production, wait for human)
        approval.approved = context.get("approval_granted", True)
        approval.approved_by = "ops_manager"
        approval.approved_at = datetime.now().isoformat()
        approval.comments = "Approved - customer is platinum tier"

        state["human_approval"] = approval
        state["metadata"].status = WorkflowStatus.IN_PROGRESS  # Resume from waiting

        complete_step(
            step,
            status=NodeStatus.SUCCESS,
            output_data={"approved": approval.approved},
            actual_outcome=f"Approval {'granted' if approval.approved else 'denied'}"
        )

        logger.info(f"[request_approval_node] Approval: {approval.approved}")

    except Exception as e:
        logger.error(f"[request_approval_node] Failed: {e}")
        complete_step(step, status=NodeStatus.FAILED, error=str(e))
        state["errors"].append(f"request_approval: {str(e)}")

    add_workflow_step(state, step)
    return state


def dispatch_courier_node(state: BaggageWorkflowState) -> BaggageWorkflowState:
    """
    Node: Dispatch courier using Courier Dispatch agent

    Books courier shipment for bag delivery.
    """
    step = create_step(
        node_name="dispatch_courier",
        status=NodeStatus.RUNNING,
        reasoning="Book courier to deliver bag to passenger destination",
        expected_outcome="Courier booked with tracking number"
    )

    try:
        logger.info(f"[dispatch_courier_node] Dispatching courier for bag {state['bag_tag']}")

        bag_tag = state["bag_tag"]
        context = state.get("context", {})

        # MOCK: In production, call Courier Dispatch agent
        # booking = courier_agent.book_shipment(bag_tag, destination)

        booking = CourierBooking(
            booking_id=f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}",
            courier=context.get("courier", "fedex"),
            tracking_number=f"FEDEX{datetime.now().strftime('%Y%m%d%H%M%S')}",
            origin=context.get("origin", "LAX"),
            destination=context.get("destination", "123 Main St, New York, NY"),
            estimated_delivery=context.get("estimated_delivery", "2025-11-15T18:00:00Z"),
            label_url="https://fedex.com/labels/FEDEX20251114120000.pdf",
            cost_usd=context.get("courier_cost", 89.50),
            status="BOOKED",
            booked_at=datetime.now().isoformat()
        )

        state["courier_booking"] = booking
        state["metadata"].total_cost_usd += booking.cost_usd

        complete_step(
            step,
            status=NodeStatus.SUCCESS,
            output_data={
                "tracking_number": booking.tracking_number,
                "cost": booking.cost_usd
            },
            actual_outcome=f"Courier booked: {booking.tracking_number}"
        )

        logger.info(f"[dispatch_courier_node] Booked: {booking.tracking_number}")

    except Exception as e:
        logger.error(f"[dispatch_courier_node] Failed: {e}")
        complete_step(step, status=NodeStatus.FAILED, error=str(e))
        state["errors"].append(f"dispatch_courier: {str(e)}")

    add_workflow_step(state, step)
    return state


def notify_passenger_node(state: BaggageWorkflowState) -> BaggageWorkflowState:
    """
    Node: Send notification to passenger using Passenger Comms agent

    Sends SMS/email to passenger with status update.
    """
    step = create_step(
        node_name="notify_passenger",
        status=NodeStatus.RUNNING,
        reasoning="Inform passenger about bag status and resolution",
        expected_outcome="Notification sent successfully"
    )

    try:
        logger.info(f"[notify_passenger_node] Notifying passenger for bag {state['bag_tag']}")

        context = state.get("context", {})
        courier_booking = state.get("courier_booking")

        # MOCK: In production, call Passenger Comms agent
        # notification = passenger_comms_agent.send_notification(...)

        message = "Your bag is delayed but we've arranged courier delivery"
        if courier_booking:
            message += f" via {courier_booking.courier.upper()}. Tracking: {courier_booking.tracking_number}"

        notification = Notification(
            notification_id=f"NOT{datetime.now().strftime('%Y%m%d%H%M%S')}",
            channel=context.get("notification_channel", "sms"),
            recipient=context.get("passenger_phone", "+12025551234"),
            message=message,
            status="SENT",
            sent_at=datetime.now().isoformat(),
            delivery_status="DELIVERED"
        )

        state["notifications_sent"].append(notification)

        complete_step(
            step,
            status=NodeStatus.SUCCESS,
            output_data={"notification_id": notification.notification_id},
            actual_outcome=f"Notification sent via {notification.channel}"
        )

        logger.info(f"[notify_passenger_node] Sent: {notification.notification_id}")

    except Exception as e:
        logger.error(f"[notify_passenger_node] Failed: {e}")
        complete_step(step, status=NodeStatus.FAILED, error=str(e))
        state["errors"].append(f"notify_passenger: {str(e)}")

    add_workflow_step(state, step)
    return state


def update_twin_node(state: BaggageWorkflowState) -> BaggageWorkflowState:
    """
    Node: Update digital twin in Neo4j knowledge graph

    Records all workflow actions in knowledge graph for learning.
    """
    step = create_step(
        node_name="update_twin",
        status=NodeStatus.RUNNING,
        reasoning="Update digital twin with all workflow actions for future learning",
        expected_outcome="Digital twin updated with workflow trace"
    )

    try:
        logger.info(f"[update_twin_node] Updating digital twin for bag {state['bag_tag']}")

        # MOCK: In production, update Neo4j knowledge graph
        # twin_updater.update(state)

        # Record workflow execution
        twin_update = {
            "bag_tag": state["bag_tag"],
            "workflow_id": state["workflow_id"],
            "workflow_type": state["metadata"].workflow_type,
            "risk_score": state["risk_data"].risk_score if state.get("risk_data") else None,
            "case_id": state["exception_case"].case_id if state.get("exception_case") else None,
            "courier_tracking": state["courier_booking"].tracking_number if state.get("courier_booking") else None,
            "total_cost": state["metadata"].total_cost_usd,
            "workflow_duration_ms": state["metadata"].duration_ms,
            "steps_executed": len(state["workflow_history"]),
            "updated_at": datetime.now().isoformat()
        }

        complete_step(
            step,
            status=NodeStatus.SUCCESS,
            output_data=twin_update,
            actual_outcome="Digital twin updated successfully"
        )

        logger.info(f"[update_twin_node] Twin updated")

    except Exception as e:
        logger.error(f"[update_twin_node] Failed: {e}")
        complete_step(step, status=NodeStatus.FAILED, error=str(e))
        state["errors"].append(f"update_twin: {str(e)}")

    add_workflow_step(state, step)
    return state


def log_workflow_node(state: BaggageWorkflowState) -> BaggageWorkflowState:
    """
    Node: Log complete workflow execution

    Final logging and audit trail.
    """
    step = create_step(
        node_name="log_workflow",
        status=NodeStatus.RUNNING,
        reasoning="Create complete audit trail of workflow execution",
        expected_outcome="Workflow logged to audit system"
    )

    try:
        logger.info(f"[log_workflow_node] Logging workflow {state['workflow_id']}")

        # MOCK: In production, log to audit system
        # audit_logger.log_workflow(state)

        workflow_summary = {
            "workflow_id": state["workflow_id"],
            "bag_tag": state["bag_tag"],
            "workflow_type": state["metadata"].workflow_type,
            "status": state["metadata"].status.value,
            "duration_ms": state["metadata"].duration_ms,
            "total_steps": len(state["workflow_history"]),
            "successful_steps": state["metadata"].completed_steps,
            "failed_steps": state["metadata"].failed_steps,
            "total_cost_usd": state["metadata"].total_cost_usd,
            "errors": state.get("errors", [])
        }

        logger.info(f"[log_workflow_node] Summary: {workflow_summary}")

        complete_step(
            step,
            status=NodeStatus.SUCCESS,
            output_data=workflow_summary,
            actual_outcome="Workflow logged successfully"
        )

    except Exception as e:
        logger.error(f"[log_workflow_node] Failed: {e}")
        complete_step(step, status=NodeStatus.FAILED, error=str(e))

    add_workflow_step(state, step)
    return state


def error_handler_node(state: BaggageWorkflowState) -> BaggageWorkflowState:
    """
    Node: Handle workflow errors

    Manages errors and initiates rollback if needed.
    """
    step = create_step(
        node_name="error_handler",
        status=NodeStatus.RUNNING,
        reasoning="Handle workflow errors and determine rollback strategy",
        expected_outcome="Errors handled, rollback initiated if needed"
    )

    try:
        logger.error(f"[error_handler_node] Handling errors for workflow {state['workflow_id']}")

        errors = state.get("errors", [])
        logger.error(f"Errors encountered: {errors}")

        # Determine if rollback is needed
        critical_errors = [e for e in errors if "critical" in e.lower()]

        if critical_errors:
            state["rollback_required"] = True
            logger.error("Critical errors detected - rollback required")

        complete_step(
            step,
            status=NodeStatus.SUCCESS,
            output_data={"errors": errors, "rollback_required": state.get("rollback_required", False)},
            actual_outcome=f"Handled {len(errors)} errors"
        )

    except Exception as e:
        logger.error(f"[error_handler_node] Failed: {e}")
        complete_step(step, status=NodeStatus.FAILED, error=str(e))

    add_workflow_step(state, step)
    return state
