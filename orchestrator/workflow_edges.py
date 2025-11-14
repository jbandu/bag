"""
Workflow Edges
==============

Edge conditions and routing logic for LangGraph orchestrator.

Edges define transitions between nodes:
- Conditional edges: Route based on state
- Parallel edges: Execute multiple nodes concurrently
- Loop edges: Retry logic
- Error edges: Exception handling

Version: 1.0.0
Date: 2025-11-14
"""

from typing import Literal, Optional
from datetime import datetime
from loguru import logger

from orchestrator.workflow_state import (
    BaggageWorkflowState,
    EdgeDecision,
    RiskLevel
)


# ============================================================================
# EDGE CONDITION FUNCTIONS
# ============================================================================

def route_after_risk_assessment(
    state: BaggageWorkflowState
) -> Literal["create_case", "skip_case", "error"]:
    """
    Route after risk assessment.

    Conditions:
    - If risk >= HIGH → create_case
    - If risk < HIGH → skip_case
    - If error → error
    """

    risk_data = state.get("risk_data")

    if not risk_data:
        logger.warning("[route_after_risk_assessment] No risk data - routing to error")
        return "error"

    # Decision logic
    if risk_data.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
        logger.info(f"[route_after_risk_assessment] High risk ({risk_data.risk_level.value}) → create_case")
        return "create_case"
    else:
        logger.info(f"[route_after_risk_assessment] Low/Medium risk ({risk_data.risk_level.value}) → skip_case")
        return "skip_case"


def route_after_parallel_checks(
    state: BaggageWorkflowState
) -> Literal["request_approval", "dispatch_courier", "error"]:
    """
    Route after parallel checks (case creation + PIR check).

    Conditions:
    - If risk > 0.9 AND value > $500 → request_approval (human-in-loop)
    - Else → dispatch_courier (auto-dispatch)
    - If errors → error
    """

    risk_data = state.get("risk_data")
    errors = state.get("errors", [])

    if errors:
        logger.warning(f"[route_after_parallel_checks] Errors detected → error handler")
        return "error"

    if not risk_data:
        logger.warning("[route_after_parallel_checks] No risk data → error")
        return "error"

    # Check if human approval needed
    if risk_data.requires_human_approval():
        logger.info(
            f"[route_after_parallel_checks] High risk ({risk_data.risk_score:.2f}) "
            f"+ high value (${risk_data.value_estimate}) → request_approval"
        )
        return "request_approval"
    else:
        logger.info(
            f"[route_after_parallel_checks] Auto-dispatch criteria met → dispatch_courier"
        )
        return "dispatch_courier"


def route_after_approval(
    state: BaggageWorkflowState
) -> Literal["dispatch_courier", "notify_passenger", "error"]:
    """
    Route after human approval.

    Conditions:
    - If approved → dispatch_courier
    - If denied → notify_passenger (skip courier)
    - If error → error
    """

    approval = state.get("human_approval")

    if not approval:
        logger.warning("[route_after_approval] No approval data → error")
        return "error"

    if approval.approved:
        logger.info("[route_after_approval] Approval granted → dispatch_courier")
        return "dispatch_courier"
    else:
        logger.info("[route_after_approval] Approval denied → notify_passenger (no courier)")
        return "notify_passenger"


def route_after_courier_dispatch(
    state: BaggageWorkflowState
) -> Literal["notify_passenger", "retry_courier", "error"]:
    """
    Route after courier dispatch attempt.

    Conditions:
    - If successful → notify_passenger
    - If failed but retries available → retry_courier
    - If failed and no retries → error
    """

    courier_booking = state.get("courier_booking")
    errors = state.get("errors", [])

    courier_errors = [e for e in errors if "dispatch_courier" in e]

    if courier_booking and courier_booking.status == "BOOKED":
        logger.info("[route_after_courier_dispatch] Courier booked successfully → notify_passenger")
        return "notify_passenger"

    if courier_errors:
        # Check retry count
        courier_steps = [
            step for step in state.get("workflow_history", [])
            if step.node_name == "dispatch_courier"
        ]

        if len(courier_steps) < 3:  # Max 3 retries
            logger.warning(
                f"[route_after_courier_dispatch] Courier failed (attempt {len(courier_steps)}) → retry_courier"
            )
            return "retry_courier"
        else:
            logger.error("[route_after_courier_dispatch] Courier failed after max retries → error")
            return "error"

    logger.info("[route_after_courier_dispatch] Proceeding to notification")
    return "notify_passenger"


def route_to_finalization(
    state: BaggageWorkflowState
) -> Literal["update_twin", "error"]:
    """
    Route to finalization phase.

    Always update digital twin unless critical errors occurred.
    """

    errors = state.get("errors", [])
    critical_errors = [e for e in errors if "critical" in e.lower()]

    if critical_errors:
        logger.error("[route_to_finalization] Critical errors → error handler")
        return "error"

    logger.info("[route_to_finalization] Proceeding to update digital twin")
    return "update_twin"


def should_rollback(state: BaggageWorkflowState) -> bool:
    """
    Check if workflow should rollback.

    Returns:
        True if rollback needed, False otherwise
    """

    if state.get("rollback_required", False):
        return True

    # Check for critical failures
    critical_failures = [
        step for step in state.get("workflow_history", [])
        if step.status == "FAILED" and "critical" in step.node_name.lower()
    ]

    return len(critical_failures) > 0


def route_on_error(
    state: BaggageWorkflowState
) -> Literal["error_handler", "continue"]:
    """
    Route when errors detected.

    Conditions:
    - If errors exist → error_handler
    - Else → continue
    """

    errors = state.get("errors", [])

    if errors:
        logger.warning(f"[route_on_error] {len(errors)} errors detected → error_handler")
        return "error_handler"

    return "continue"


# ============================================================================
# EDGE DECISION RECORDING
# ============================================================================

def record_edge_decision(
    state: BaggageWorkflowState,
    edge_name: str,
    conditions_evaluated: list[str],
    condition_met: str,
    next_node: str,
    reasoning: str,
    confidence: float = 1.0,
    alternatives: Optional[list[str]] = None
) -> EdgeDecision:
    """
    Record an edge decision for observability.

    This provides semantic annotations for why a particular path was taken.
    """

    decision = EdgeDecision(
        edge_name=edge_name,
        conditions_evaluated=conditions_evaluated,
        condition_met=condition_met,
        next_node=next_node,
        reasoning=reasoning,
        confidence=confidence,
        alternatives=alternatives or [],
        decided_at=datetime.now().isoformat()
    )

    # Store in state context for audit trail
    if "edge_decisions" not in state.get("context", {}):
        state["context"]["edge_decisions"] = []

    state["context"]["edge_decisions"].append(decision)

    logger.info(
        f"[Edge Decision] {edge_name}: {condition_met} → {next_node} "
        f"(confidence: {confidence:.2f})"
    )

    return decision


# ============================================================================
# PARALLEL EXECUTION HELPERS
# ============================================================================

def get_parallel_nodes(workflow_type: str, current_node: str) -> list[str]:
    """
    Get nodes that should execute in parallel after current node.

    This enables concurrent execution of independent operations.
    """

    parallel_map = {
        "high_risk": {
            "assess_risk": ["create_case", "check_pir"],  # Both can run in parallel
        },
        "transfer": {
            "analyze_transfer": ["check_bhs", "check_dcs"],  # Parallel checks
        },
        "irrops": {
            "detect_disruption": ["fetch_affected_bags", "check_capacity"],  # Parallel data gathering
        }
    }

    return parallel_map.get(workflow_type, {}).get(current_node, [])


def all_parallel_nodes_complete(
    state: BaggageWorkflowState,
    parallel_nodes: list[str]
) -> bool:
    """
    Check if all parallel nodes have completed.

    Used to synchronize before continuing workflow.
    """

    completed_nodes = {
        step.node_name for step in state.get("workflow_history", [])
        if step.status in ["SUCCESS", "FAILED", "SKIPPED"]
    }

    return all(node in completed_nodes for node in parallel_nodes)


# ============================================================================
# LOOP/RETRY HELPERS
# ============================================================================

def should_retry_node(state: BaggageWorkflowState, node_name: str, max_retries: int = 3) -> bool:
    """
    Determine if a failed node should be retried.

    Args:
        state: Current workflow state
        node_name: Name of the node that failed
        max_retries: Maximum number of retry attempts

    Returns:
        True if should retry, False otherwise
    """

    # Count how many times this node has been attempted
    attempts = [
        step for step in state.get("workflow_history", [])
        if step.node_name == node_name
    ]

    if len(attempts) >= max_retries:
        logger.warning(f"[should_retry_node] {node_name} reached max retries ({max_retries})")
        return False

    # Check if last attempt failed
    if attempts and attempts[-1].status == "FAILED":
        logger.info(f"[should_retry_node] {node_name} failed (attempt {len(attempts)}/{max_retries}) → retry")
        return True

    return False


def get_retry_delay(attempt: int, base_delay_ms: int = 1000) -> int:
    """
    Calculate exponential backoff delay for retries.

    Args:
        attempt: Retry attempt number (0-indexed)
        base_delay_ms: Base delay in milliseconds

    Returns:
        Delay in milliseconds
    """

    delay = base_delay_ms * (2 ** attempt)
    max_delay = 30000  # 30 seconds max

    return min(delay, max_delay)


# ============================================================================
# WORKFLOW COMPLETION CHECKS
# ============================================================================

def is_workflow_complete(state: BaggageWorkflowState) -> bool:
    """
    Check if workflow has completed (successfully or with errors).

    Returns:
        True if workflow is complete, False if still in progress
    """

    status = state.get("metadata", {}).get("status")

    return status in [
        "COMPLETED",
        "FAILED",
        "ROLLED_BACK"
    ]


def calculate_workflow_success_rate(state: BaggageWorkflowState) -> float:
    """
    Calculate success rate of workflow execution.

    Returns:
        Success rate (0.0 - 1.0)
    """

    history = state.get("workflow_history", [])

    if not history:
        return 0.0

    successful = sum(1 for step in history if step.status == "SUCCESS")
    total = len(history)

    return successful / total if total > 0 else 0.0
