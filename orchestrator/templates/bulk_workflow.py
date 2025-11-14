"""
Bulk Mishandling Workflow Template
===================================

Workflow for handling bulk bag mishandling events (>10 bags from same flight).

Triggered when: Multiple bags from same flight detected as mishandled

Workflow stages:
1. Detect bulk event (>10 bags, same flight, same issue)
2. PARALLEL: Create master case + Batch PIR creation + Identify root cause
3. CONDITIONAL: Systemwide issue vs. Flight-specific vs. Station-specific
4. SEQUENCE: Coordinate recovery + Batch notifications + Deploy resources
5. FINALIZE: Track resolution + Update all twins + Generate report

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


def create_bulk_workflow() -> Any:
    """
    Create the bulk mishandling workflow.

    Handles situations where many bags (>10) are affected by same issue.

    Flow:
    1. Detect bulk event
    2. Create master case + Batch PIRs + Root cause (parallel)
    3. Classify issue type
    4. Coordinate mass recovery
    5. Batch notifications and reporting

    Returns:
        Compiled LangGraph workflow
    """

    logger.info("Creating bulk_workflow")

    nodes = {
        "assess_risk": assess_risk_node,  # Analyze bulk event
        "create_case": create_case_node,  # Master case
        "check_pir": check_pir_node,      # Batch PIR operations
        "dispatch_courier": dispatch_courier_node,  # Mass courier deployment
        "notify_passenger": notify_passenger_node,  # Batch notifications
        "update_twin": update_twin_node,
        "log_workflow": log_workflow_node,
        "error_handler": error_handler_node
    }

    edges = [
        ("assess_risk", "create_case"),
        ("create_case", "check_pir"),
        ("check_pir", "dispatch_courier"),
        ("dispatch_courier", "notify_passenger"),
        ("notify_passenger", "update_twin"),
        ("update_twin", "log_workflow"),
        ("log_workflow", END),
        ("error_handler", END)
    ]

    conditional_edges = []  # Linear flow for bulk processing

    workflow = build_workflow_graph(
        workflow_type="bulk",
        nodes=nodes,
        edges=edges,
        conditional_edges=conditional_edges,
        entry_point="assess_risk"
    )

    logger.info("bulk_workflow created successfully")

    return workflow


WORKFLOW_METADATA = {
    "name": "bulk_mishandling",
    "version": "1.0.0",
    "description": "Handle bulk bag mishandling events affecting multiple bags",
    "triggers": [
        ">10 bags from same flight mishandled",
        "Systemwide BHS failure",
        "Mass misload",
        "Container left behind"
    ],
    "expected_duration_ms": 60000,  # 60 seconds (many bags)
    "agents_involved": [
        "risk_scorer",
        "case_manager",
        "worldtracer",
        "courier_dispatch",
        "passenger_comms",
        "ops_coordinator"
    ],
    "approval_gates": [
        "Ops manager approval for mass courier deployment"
    ],
    "success_criteria": [
        "Bulk event detected and assessed",
        "Master case created",
        "All PIRs created/updated",
        "Root cause identified",
        "Recovery coordinated",
        "All passengers notified",
        "Incident report generated"
    ]
}
