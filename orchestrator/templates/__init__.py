"""
Workflow Templates
==================

Pre-built workflow templates for common baggage handling scenarios.

Available workflows:
- high_risk: High-risk bag handling
- transfer: Transfer coordination
- irrops: Irregular operations recovery
- bulk: Bulk mishandling
- delivery: Courier delivery coordination

Version: 1.0.0
Date: 2025-11-14
"""

from orchestrator.templates.high_risk_workflow import (
    create_high_risk_workflow,
    WORKFLOW_METADATA as HIGH_RISK_METADATA
)

from orchestrator.templates.transfer_workflow import (
    create_transfer_workflow,
    WORKFLOW_METADATA as TRANSFER_METADATA
)

from orchestrator.templates.irrops_workflow import (
    create_irrops_workflow,
    WORKFLOW_METADATA as IRROPS_METADATA
)

from orchestrator.templates.bulk_workflow import (
    create_bulk_workflow,
    WORKFLOW_METADATA as BULK_METADATA
)

from orchestrator.templates.delivery_workflow import (
    create_delivery_workflow,
    WORKFLOW_METADATA as DELIVERY_METADATA
)


__all__ = [
    "create_high_risk_workflow",
    "create_transfer_workflow",
    "create_irrops_workflow",
    "create_bulk_workflow",
    "create_delivery_workflow",
    "HIGH_RISK_METADATA",
    "TRANSFER_METADATA",
    "IRROPS_METADATA",
    "BULK_METADATA",
    "DELIVERY_METADATA"
]


# Metadata registry
WORKFLOW_REGISTRY = {
    "high_risk": {
        "factory": create_high_risk_workflow,
        "metadata": HIGH_RISK_METADATA
    },
    "transfer": {
        "factory": create_transfer_workflow,
        "metadata": TRANSFER_METADATA
    },
    "irrops": {
        "factory": create_irrops_workflow,
        "metadata": IRROPS_METADATA
    },
    "bulk": {
        "factory": create_bulk_workflow,
        "metadata": BULK_METADATA
    },
    "delivery": {
        "factory": create_delivery_workflow,
        "metadata": DELIVERY_METADATA
    }
}


def get_workflow_metadata(workflow_type: str) -> dict:
    """Get metadata for a workflow type"""
    if workflow_type in WORKFLOW_REGISTRY:
        return WORKFLOW_REGISTRY[workflow_type]["metadata"]
    return None


def list_available_workflows() -> list[str]:
    """List all available workflow types"""
    return list(WORKFLOW_REGISTRY.keys())
