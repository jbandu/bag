"""
IRROPs Recovery Workflow Template
==================================

Workflow for handling irregular operations (flight cancellations, delays, diversions).

Triggered when: Flight disruption detected

Workflow stages:
1. Detect disruption (cancelled, delayed >2hrs, diverted)
2. PARALLEL: Identify affected bags + Find alternative routes + Check inventory
3. CONDITIONAL: Reroute vs. Deliver vs. Hold
4. SEQUENCE: Update PIRs + Rebook bags + Notify passengers
5. FINALIZE: Monitor recovery + Update digital twin

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
    create_case_node,
    check_pir_node,
    dispatch_courier_node,
    notify_passenger_node,
    update_twin_node,
    log_workflow_node,
    error_handler_node
)

from orchestrator.workflow_edges import route_after_parallel_checks


def create_irrops_workflow() -> Any:
    """
    Create the IRROPs recovery workflow.

    Handles flight disruptions and bag recovery.

    Flow:
    1. Detect disruption
    2. Identify affected bags + routes + capacity (parallel)
    3. Determine recovery strategy
    4. Execute recovery
    5. Monitor and update

    Returns:
        Compiled LangGraph workflow
    """

    logger.info("Creating irrops_workflow")

    nodes = {
        "assess_risk": assess_risk_node,  # Repurposed for disruption analysis
        "create_case": create_case_node,  # Create IRROPs case
        "check_pir": check_pir_node,      # Update existing PIRs
        "dispatch_courier": dispatch_courier_node,  # Deliver if reroute not feasible
        "notify_passenger": notify_passenger_node,
        "update_twin": update_twin_node,
        "log_workflow": log_workflow_node,
        "error_handler": error_handler_node
    }

    edges = [
        ("assess_risk", "create_case"),
        ("create_case", "check_pir"),
        ("notify_passenger", "update_twin"),
        ("update_twin", "log_workflow"),
        ("log_workflow", END),
        ("error_handler", END)
    ]

    conditional_edges = [
        (
            "check_pir",
            route_after_parallel_checks,
            {
                "dispatch_courier": "dispatch_courier",  # Deliver to destination
                "notify_passenger": "notify_passenger",  # Rebooked on next flight
                "error": "error_handler"
            }
        ),
        (
            "dispatch_courier",
            lambda state: "notify_passenger",
            None
        )
    ]

    workflow = build_workflow_graph(
        workflow_type="irrops",
        nodes=nodes,
        edges=edges,
        conditional_edges=conditional_edges,
        entry_point="assess_risk"
    )

    logger.info("irrops_workflow created successfully")

    return workflow


WORKFLOW_METADATA = {
    "name": "irrops_recovery",
    "version": "1.0.0",
    "description": "Handle irregular operations and recover affected baggage",
    "triggers": [
        "Flight cancelled",
        "Flight delayed > 2 hours",
        "Flight diverted",
        "Aircraft swap",
        "Weather event"
    ],
    "expected_duration_ms": 30000,  # 30 seconds (can affect many bags)
    "agents_involved": [
        "risk_scorer",
        "case_manager",
        "worldtracer",
        "dcs_query",
        "bhs_tracker",
        "courier_dispatch",
        "passenger_comms"
    ],
    "success_criteria": [
        "Disruption assessed",
        "Affected bags identified",
        "Recovery strategy determined",
        "PIRs updated",
        "Passengers notified",
        "Bags rerouted or delivered"
    ]
}
