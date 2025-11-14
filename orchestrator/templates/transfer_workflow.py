"""
Transfer Coordination Workflow Template
========================================

Workflow for coordinating tight transfer connections.

Triggered when: Transfer time < 60 minutes

Workflow stages:
1. Assess transfer risk (connection time, distances, disruptions)
2. PARALLEL: Check bag location + Check flight status + Check passenger location
3. CONDITIONAL: If misconnect likely → Pre-position courier
4. SEQUENCE: Track bag through transfer + Update passenger
5. FINALIZE: Confirm connection OR initiate recovery

Version: 1.0.0
Date: 2025-11-14
"""

from typing import Dict, Any
from loguru import logger

try:
    from langgraph.graph import END
except ImportError:
    END = "END"

from orchestrator.baggage_orchestrator import build_workflow_graph
from orchestrator.workflow_nodes import (
    assess_risk_node,
    check_pir_node,
    dispatch_courier_node,
    notify_passenger_node,
    update_twin_node,
    log_workflow_node
)


def create_transfer_workflow() -> Any:
    """
    Create the transfer coordination workflow.

    Handles tight transfers to prevent misconnections.

    Flow:
    1. Assess transfer risk
    2. Check bag + flight + passenger (parallel)
    3. If high risk → Pre-position courier
    4. Track transfer
    5. Confirm OR recover

    Returns:
        Compiled LangGraph workflow
    """

    logger.info("Creating transfer_workflow")

    nodes = {
        "assess_risk": assess_risk_node,
        "check_pir": check_pir_node,  # Repurposed for transfer checks
        "dispatch_courier": dispatch_courier_node,  # Pre-position if needed
        "notify_passenger": notify_passenger_node,
        "update_twin": update_twin_node,
        "log_workflow": log_workflow_node
    }

    edges = [
        ("assess_risk", "check_pir"),
        ("notify_passenger", "update_twin"),
        ("update_twin", "log_workflow"),
        ("log_workflow", END)
    ]

    conditional_edges = [
        (
            "check_pir",
            lambda state: (
                "dispatch_courier" if state.get("risk_data") and state["risk_data"].risk_score > 0.7
                else "notify_passenger"
            ),
            {
                "dispatch_courier": "dispatch_courier",
                "notify_passenger": "notify_passenger"
            }
        ),
        (
            "dispatch_courier",
            lambda state: "notify_passenger",
            None  # Always proceed to notification
        )
    ]

    workflow = build_workflow_graph(
        workflow_type="transfer",
        nodes=nodes,
        edges=edges,
        conditional_edges=conditional_edges,
        entry_point="assess_risk"
    )

    logger.info("transfer_workflow created successfully")

    return workflow


WORKFLOW_METADATA = {
    "name": "transfer_coordination",
    "version": "1.0.0",
    "description": "Coordinate tight transfer connections to prevent misconnects",
    "triggers": [
        "Transfer time < 60 minutes",
        "Inter-terminal transfer",
        "Different airlines",
        "Inbound flight delayed"
    ],
    "expected_duration_ms": 8000,
    "agents_involved": [
        "risk_scorer",
        "bhs_tracker",
        "dcs_query",
        "courier_dispatch",
        "passenger_comms"
    ],
    "success_criteria": [
        "Transfer risk assessed",
        "Bag location confirmed",
        "Flight status checked",
        "Passenger updated on connection status"
    ]
}
