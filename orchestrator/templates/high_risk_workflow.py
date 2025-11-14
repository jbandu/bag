"""
High Risk Bag Workflow Template
================================

Workflow for handling high-risk bags requiring special attention.

Triggered when: Risk score > 0.7

Workflow stages:
1. Assess risk
2. PARALLEL: Create case + Check PIR + Prepare notification
3. CONDITIONAL: If risk > 0.9 AND value > $500 → Human approval
4. SEQUENCE: Dispatch courier
5. FINALIZE: Notify passenger + Update twin + Log

Version: 1.0.0
Date: 2025-11-14
"""

from typing import Dict, Any, Callable
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
    request_approval_node,
    dispatch_courier_node,
    notify_passenger_node,
    update_twin_node,
    log_workflow_node,
    error_handler_node
)

from orchestrator.workflow_edges import (
    route_after_risk_assessment,
    route_after_parallel_checks,
    route_after_approval,
    route_after_courier_dispatch,
    route_to_finalization
)


def create_high_risk_workflow() -> Any:
    """
    Create the high-risk bag workflow.

    Flow:
    ┌─────────────┐
    │ assess_risk │
    └──────┬──────┘
           │
           ├──────────────┬────────────────┐
           │              │                │
    ┌──────▼─────┐ ┌─────▼────────┐ ┌─────▼─────┐
    │ create_case│ │  check_pir   │ │  (prepare)│
    └──────┬─────┘ └─────┬────────┘ └─────┬─────┘
           │              │                │
           └──────────────┴────────────────┘
                          │
                    ┌─────▼──────┐
                    │ route: high│
                    │ risk check │
                    └─────┬──────┘
                          │
              ┌───────────┴───────────┐
              │                       │
         risk>0.9 &              risk lower
         value>$500                  │
              │                       │
    ┌─────────▼──────────┐   ┌───────▼─────────┐
    │ request_approval    │   │ dispatch_courier│
    └─────────┬───────────┘   └───────┬─────────┘
              │                       │
         ┌────▼────┐                  │
         │ granted │                  │
         │ denied  │                  │
         └────┬────┘                  │
              │                       │
              └──────────┬────────────┘
                         │
                  ┌──────▼──────┐
                  │notify_      │
                  │passenger    │
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │update_twin  │
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │log_workflow │
                  └──────┬──────┘
                         │
                        END

    Returns:
        Compiled LangGraph workflow
    """

    logger.info("Creating high_risk_workflow")

    # Define nodes
    nodes = {
        "assess_risk": assess_risk_node,
        "create_case": create_case_node,
        "check_pir": check_pir_node,
        "request_approval": request_approval_node,
        "dispatch_courier": dispatch_courier_node,
        "notify_passenger": notify_passenger_node,
        "update_twin": update_twin_node,
        "log_workflow": log_workflow_node,
        "error_handler": error_handler_node
    }

    # Define direct edges
    # Note: In a real LangGraph with parallel support, we'd use parallel edges here
    # For now, we execute sequentially but mark as conceptually parallel
    edges = [
        ("assess_risk", "create_case"),  # Parallel block 1
        ("create_case", "check_pir"),     # Parallel block 2
        # After parallel checks, route based on risk
        # (conditional edge defined below)

        # After approval (if needed)
        # (conditional edge defined below)

        # Final sequence
        ("notify_passenger", "update_twin"),
        ("update_twin", "log_workflow"),
        ("log_workflow", END),

        # Error handling
        ("error_handler", END)
    ]

    # Define conditional edges
    conditional_edges = [
        # After check_pir (parallel checks complete), route based on risk level
        (
            "check_pir",
            route_after_parallel_checks,
            {
                "request_approval": "request_approval",  # High risk + high value
                "dispatch_courier": "dispatch_courier",   # Lower risk or value
                "error": "error_handler"
            }
        ),

        # After approval, route based on decision
        (
            "request_approval",
            route_after_approval,
            {
                "dispatch_courier": "dispatch_courier",  # Approved
                "notify_passenger": "notify_passenger",  # Denied (skip courier)
                "error": "error_handler"
            }
        ),

        # After courier dispatch, proceed to notification
        (
            "dispatch_courier",
            route_after_courier_dispatch,
            {
                "notify_passenger": "notify_passenger",  # Success
                "retry_courier": "dispatch_courier",     # Retry
                "error": "error_handler"
            }
        )
    ]

    # Build and compile workflow
    workflow = build_workflow_graph(
        workflow_type="high_risk",
        nodes=nodes,
        edges=edges,
        conditional_edges=conditional_edges,
        entry_point="assess_risk"
    )

    logger.info("high_risk_workflow created successfully")

    return workflow


# ============================================================================
# WORKFLOW METADATA
# ============================================================================

WORKFLOW_METADATA = {
    "name": "high_risk_bag",
    "version": "1.0.0",
    "description": "Handle high-risk bags requiring special attention",
    "triggers": [
        "Risk score > 0.7",
        "Tight connection time",
        "High-value baggage",
        "VIP passenger"
    ],
    "expected_duration_ms": 15000,  # 15 seconds
    "agents_involved": [
        "risk_scorer",
        "case_manager",
        "worldtracer",
        "courier_dispatch",
        "passenger_comms"
    ],
    "approval_gates": [
        "Human approval for risk > 0.9 AND value > $500"
    ],
    "success_criteria": [
        "Risk assessed",
        "Exception case created",
        "PIR checked/created",
        "Courier dispatched (if approved)",
        "Passenger notified",
        "Digital twin updated"
    ]
}
