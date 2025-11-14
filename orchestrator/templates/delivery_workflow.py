"""
Delivery Coordination Workflow Template
========================================

Workflow for coordinating courier delivery of delayed/mishandled bags.

Triggered when: Courier delivery decision made

Workflow stages:
1. Validate delivery address and passenger contact
2. PARALLEL: Select best courier + Calculate cost + Check delivery window
3. CONDITIONAL: Standard delivery vs. Priority delivery vs. White glove service
4. SEQUENCE: Book courier + Generate label + Track shipment
5. FINALIZE: Monitor delivery + Update passenger + Close case

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
    dispatch_courier_node,
    notify_passenger_node,
    update_twin_node,
    log_workflow_node,
    error_handler_node
)

from orchestrator.workflow_edges import route_after_courier_dispatch


def create_delivery_workflow() -> Any:
    """
    Create the delivery coordination workflow.

    Manages end-to-end courier delivery process.

    Flow:
    1. Validate delivery details
    2. Select courier + cost + timing (parallel)
    3. Determine service level
    4. Book and track
    5. Monitor to delivery

    Returns:
        Compiled LangGraph workflow
    """

    logger.info("Creating delivery_workflow")

    nodes = {
        "assess_risk": assess_risk_node,  # Validate delivery feasibility
        "dispatch_courier": dispatch_courier_node,
        "notify_passenger": notify_passenger_node,  # Delivery confirmation
        "update_twin": update_twin_node,
        "log_workflow": log_workflow_node,
        "error_handler": error_handler_node
    }

    edges = [
        ("assess_risk", "dispatch_courier"),
        ("notify_passenger", "update_twin"),
        ("update_twin", "log_workflow"),
        ("log_workflow", END),
        ("error_handler", END)
    ]

    conditional_edges = [
        (
            "dispatch_courier",
            route_after_courier_dispatch,
            {
                "notify_passenger": "notify_passenger",  # Success
                "retry_courier": "dispatch_courier",     # Retry booking
                "error": "error_handler"                 # Failed
            }
        )
    ]

    workflow = build_workflow_graph(
        workflow_type="delivery",
        nodes=nodes,
        edges=edges,
        conditional_edges=conditional_edges,
        entry_point="assess_risk"
    )

    logger.info("delivery_workflow created successfully")

    return workflow


WORKFLOW_METADATA = {
    "name": "delivery_coordination",
    "version": "1.0.0",
    "description": "Coordinate courier delivery of delayed/mishandled bags",
    "triggers": [
        "Bag recovery via delivery needed",
        "Passenger destination changed",
        "Bag found after passenger departed",
        "Direct delivery requested"
    ],
    "expected_duration_ms": 10000,  # 10 seconds
    "agents_involved": [
        "courier_dispatch",
        "passenger_comms",
        "case_manager"
    ],
    "success_criteria": [
        "Delivery address validated",
        "Courier selected and booked",
        "Tracking number obtained",
        "Label generated",
        "Passenger notified with tracking",
        "Delivery monitored",
        "Case closed upon delivery"
    ],
    "cost_thresholds": {
        "standard": {"max_usd": 100, "eta_hours": 48},
        "priority": {"max_usd": 200, "eta_hours": 24},
        "white_glove": {"max_usd": 500, "eta_hours": 12}
    }
}
