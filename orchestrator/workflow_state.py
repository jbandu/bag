"""
Workflow State Definitions
===========================

State machine definitions for LangGraph orchestrator.

Defines:
- BaggageWorkflowState: Main state container
- Supporting data models (RiskAssessment, ExceptionCase, etc.)
- Workflow metadata and annotations
- State transitions and history

Version: 1.0.0
Date: 2025-11-14
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class NodeStatus(str, Enum):
    """Individual node execution status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PIRStatus(str, Enum):
    """WorldTracer PIR status"""
    NOT_FOUND = "NOT_FOUND"
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    CLOSED = "CLOSED"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class RiskAssessment:
    """Risk assessment result from Risk Scorer agent"""
    bag_tag: str
    risk_score: float  # 0.0 - 1.0
    risk_level: RiskLevel
    risk_factors: List[str]
    confidence: float
    assessed_at: str
    assessor: str = "risk_scorer_agent"

    # Additional context
    value_estimate: Optional[float] = None  # USD
    passenger_tier: Optional[str] = None  # BASIC, SILVER, GOLD, PLATINUM
    flight_importance: Optional[str] = None  # REGULAR, CRITICAL

    def requires_human_approval(self) -> bool:
        """Check if this risk requires human approval"""
        return (self.risk_score > 0.9 and
                (self.value_estimate or 0) > 500)


@dataclass
class ExceptionCase:
    """Exception case from Case Manager"""
    case_id: str
    bag_tag: str
    exception_type: str
    severity: str
    status: str
    created_at: str
    created_by: str = "case_manager_agent"
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_eta: Optional[str] = None


@dataclass
class PIRInfo:
    """WorldTracer PIR information"""
    ohd_reference: Optional[str] = None
    status: PIRStatus = PIRStatus.NOT_FOUND
    exists: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    station: Optional[str] = None
    irregularity_type: Optional[str] = None


@dataclass
class CourierBooking:
    """Courier dispatch booking"""
    booking_id: str
    courier: str  # fedex, ups, dhl
    tracking_number: str
    origin: str
    destination: str
    estimated_delivery: str
    label_url: str
    cost_usd: float
    status: str
    booked_at: str
    booked_by: str = "courier_dispatch_agent"


@dataclass
class HumanApproval:
    """Human approval for high-risk actions"""
    approval_id: str
    workflow_id: str
    request_type: str
    requested_at: str
    requested_by: str

    # Approval decision
    approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    comments: Optional[str] = None

    # Context for approver
    risk_score: Optional[float] = None
    estimated_cost: Optional[float] = None
    passenger_tier: Optional[str] = None
    reasoning: Optional[str] = None


@dataclass
class Notification:
    """Notification sent to passenger"""
    notification_id: str
    channel: str  # sms, email, push
    recipient: str
    message: str
    status: str
    sent_at: str
    sent_by: str = "passenger_comms_agent"
    delivery_status: Optional[str] = None


@dataclass
class WorkflowStep:
    """Single step in workflow execution"""
    step_id: str
    node_name: str
    status: NodeStatus
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None

    # Semantic annotations
    reasoning: Optional[str] = None  # Why this step was taken
    confidence: float = 1.0  # Confidence in this decision
    alternatives_considered: List[str] = field(default_factory=list)
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None

    # Execution details
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class WorkflowMetadata:
    """Workflow execution metadata"""
    workflow_id: str
    workflow_type: str  # high_risk, transfer, irrops, bulk, delivery
    status: WorkflowStatus
    started_at: str
    triggered_by: str  # system, agent, human, event
    trigger_reason: str
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None

    # Statistics
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0

    # Cost tracking
    total_cost_usd: float = 0.0
    api_calls: int = 0


# ============================================================================
# MAIN WORKFLOW STATE
# ============================================================================

class BaggageWorkflowState(TypedDict, total=False):
    """
    Main workflow state for LangGraph orchestrator.

    This state flows through the entire workflow, being updated by each node.
    LangGraph manages state transitions automatically.
    """

    # Core identifiers
    workflow_id: str
    bag_tag: str

    # Agent results (populated as workflow progresses)
    risk_data: Optional[RiskAssessment]
    exception_case: Optional[ExceptionCase]
    pir_status: Optional[PIRInfo]
    courier_booking: Optional[CourierBooking]
    human_approval: Optional[HumanApproval]
    notifications_sent: List[Notification]

    # Workflow execution
    metadata: WorkflowMetadata
    workflow_history: List[WorkflowStep]
    current_step: Optional[str]

    # Error handling
    errors: List[str]
    rollback_required: bool
    rollback_completed: bool

    # Additional context (varies by workflow type)
    context: Dict[str, Any]


# ============================================================================
# EDGE CONDITIONS
# ============================================================================

@dataclass
class EdgeCondition:
    """Condition for workflow edge transition"""
    name: str
    description: str
    condition_func: str  # Name of the condition function
    reasoning: str  # Why this condition exists
    next_node: str  # Where to go if condition is True


@dataclass
class EdgeDecision:
    """Decision made at a conditional edge"""
    edge_name: str
    conditions_evaluated: List[str]
    condition_met: str
    next_node: str
    reasoning: str
    confidence: float
    alternatives: List[str]
    decided_at: str


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_workflow_state(
    workflow_id: str,
    bag_tag: str,
    workflow_type: str,
    triggered_by: str,
    trigger_reason: str,
    context: Optional[Dict[str, Any]] = None
) -> BaggageWorkflowState:
    """Create initial workflow state"""

    now = datetime.now().isoformat()

    return BaggageWorkflowState(
        workflow_id=workflow_id,
        bag_tag=bag_tag,
        risk_data=None,
        exception_case=None,
        pir_status=None,
        courier_booking=None,
        human_approval=None,
        notifications_sent=[],
        metadata=WorkflowMetadata(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            status=WorkflowStatus.PENDING,
            started_at=now,
            triggered_by=triggered_by,
            trigger_reason=trigger_reason
        ),
        workflow_history=[],
        current_step=None,
        errors=[],
        rollback_required=False,
        rollback_completed=False,
        context=context or {}
    )


def add_workflow_step(
    state: BaggageWorkflowState,
    step: WorkflowStep
) -> BaggageWorkflowState:
    """Add a step to workflow history"""
    state["workflow_history"].append(step)
    state["metadata"].total_steps += 1

    if step.status == NodeStatus.SUCCESS:
        state["metadata"].completed_steps += 1
    elif step.status == NodeStatus.FAILED:
        state["metadata"].failed_steps += 1
    elif step.status == NodeStatus.SKIPPED:
        state["metadata"].skipped_steps += 1

    return state


def update_workflow_status(
    state: BaggageWorkflowState,
    status: WorkflowStatus
) -> BaggageWorkflowState:
    """Update workflow status"""
    state["metadata"].status = status

    if status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.ROLLED_BACK]:
        state["metadata"].completed_at = datetime.now().isoformat()

        if state["metadata"].started_at:
            started = datetime.fromisoformat(state["metadata"].started_at)
            completed = datetime.now()
            state["metadata"].duration_ms = (completed - started).total_seconds() * 1000

    return state


def check_rollback_needed(state: BaggageWorkflowState) -> bool:
    """Check if workflow needs rollback"""
    # Rollback if critical steps failed
    critical_failures = [
        step for step in state["workflow_history"]
        if step.status == NodeStatus.FAILED and "critical" in step.node_name
    ]

    return len(critical_failures) > 0 or state.get("rollback_required", False)
