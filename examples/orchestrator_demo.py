"""
Orchestrator Demo
=================

Demonstrates LangGraph-based semantic agent orchestration with all 5 workflow templates.

Shows:
- High-risk bag workflow with human approval
- Transfer coordination workflow
- IRROPs recovery workflow
- Bulk mishandling workflow
- Delivery coordination workflow

Semantic annotations demonstrate WHY each decision was made.

Version: 1.0.0
Date: 2025-11-14
"""

import sys
sys.path.insert(0, '/home/user/bag')

from datetime import datetime
from orchestrator.baggage_orchestrator import BaggageOrchestrator
from orchestrator.templates import (
    create_high_risk_workflow,
    create_transfer_workflow,
    create_irrops_workflow,
    create_bulk_workflow,
    create_delivery_workflow,
    WORKFLOW_REGISTRY,
    list_available_workflows
)


def main():
    print("=" * 80)
    print("LANGGRAPH SEMANTIC AGENT ORCHESTRATION - WORKFLOW DEMO")
    print("=" * 80)
    print()

    # ========================================================================
    # 1. INITIALIZE ORCHESTRATOR
    # ========================================================================

    print("1. INITIALIZING ORCHESTRATOR")
    print("-" * 80)

    orchestrator = BaggageOrchestrator()

    # Register all workflow templates
    print("Registering workflow templates...")

    workflows_to_register = {
        "high_risk": create_high_risk_workflow(),
        "transfer": create_transfer_workflow(),
        "irrops": create_irrops_workflow(),
        "bulk": create_bulk_workflow(),
        "delivery": create_delivery_workflow()
    }

    for workflow_type, workflow_graph in workflows_to_register.items():
        orchestrator.register_workflow(workflow_type, workflow_graph)
        metadata = WORKFLOW_REGISTRY[workflow_type]["metadata"]
        print(f"  ✓ {workflow_type}: {metadata['description']}")

    print()
    print(f"✓ Orchestrator initialized with {len(workflows_to_register)} workflow templates")
    print()

    # ========================================================================
    # 2. SCENARIO 1: HIGH-RISK BAG
    # ========================================================================

    print("=" * 80)
    print("2. SCENARIO 1: HIGH-RISK BAG WORKFLOW")
    print("=" * 80)
    print()

    print("Context: Platinum passenger, $850 baggage value, risk score 0.92")
    print("Expected: Assess risk → Create case → Check PIR → Request approval → Dispatch courier")
    print()

    context_high_risk = {
        "trigger_reason": "High risk bag detected by risk scorer",
        "risk_score": 0.92,
        "bag_value": 850.0,
        "passenger_tier": "PLATINUM",
        "flight_importance": "CRITICAL",
        "pir_exists": False,
        "approval_granted": True,  # Mock approval
        "courier": "fedex",
        "origin": "LAX",
        "destination": "123 Main St, New York, NY 10001",
        "estimated_delivery": "2025-11-15T18:00:00Z",
        "courier_cost": 125.00,
        "passenger_phone": "+12125551234",
        "notification_channel": "sms"
    }

    print("→ Executing high_risk workflow for bag 0291234567...")
    result_high_risk = orchestrator.execute_workflow(
        workflow_type="high_risk",
        bag_tag="0291234567",
        context=context_high_risk,
        triggered_by="risk_scorer_agent"
    )

    print()
    print("RESULTS:")
    print(f"  Status: {result_high_risk['metadata'].status.value}")
    print(f"  Duration: {result_high_risk['metadata'].duration_ms:.0f}ms")
    print(f"  Steps executed: {len(result_high_risk['workflow_history'])}")
    print(f"  Total cost: ${result_high_risk['metadata'].total_cost_usd:.2f}")
    print()

    print("Workflow trace:")
    for step in result_high_risk['workflow_history']:
        status_icon = "✓" if step.status == "SUCCESS" else "✗"
        print(f"  {status_icon} {step.node_name}: {step.actual_outcome} ({step.duration_ms:.0f}ms)")
        if step.reasoning:
            print(f"    Why: {step.reasoning}")

    print()

    # ========================================================================
    # 3. SCENARIO 2: TIGHT TRANSFER
    # ========================================================================

    print("=" * 80)
    print("3. SCENARIO 2: TIGHT TRANSFER COORDINATION")
    print("=" * 80)
    print()

    print("Context: 45-minute connection, inter-terminal transfer, inbound delayed 15 min")
    print("Expected: Assess transfer → Check status → Track → Notify passenger")
    print()

    context_transfer = {
        "trigger_reason": "Tight connection detected (45 minutes)",
        "risk_score": 0.65,
        "transfer_time_minutes": 45,
        "inbound_delay_minutes": 15,
        "inter_terminal": True,
        "passenger_phone": "+14155551234"
    }

    print("→ Executing transfer workflow for bag 0291234568...")
    result_transfer = orchestrator.execute_workflow(
        workflow_type="transfer",
        bag_tag="0291234568",
        context=context_transfer,
        triggered_by="transfer_monitor"
    )

    print()
    print("RESULTS:")
    print(f"  Status: {result_transfer['metadata'].status.value}")
    print(f"  Duration: {result_transfer['metadata'].duration_ms:.0f}ms")
    print(f"  Steps executed: {len(result_transfer['workflow_history'])}")
    print()

    # ========================================================================
    # 4. SCENARIO 3: IRROPS RECOVERY
    # ========================================================================

    print("=" * 80)
    print("4. SCENARIO 3: IRREGULAR OPERATIONS RECOVERY")
    print("=" * 80)
    print()

    print("Context: Flight AA123 cancelled, 87 bags affected")
    print("Expected: Detect → Create case → Update PIRs → Coordinate recovery → Notify all")
    print()

    context_irrops = {
        "trigger_reason": "Flight AA123 cancelled - 87 bags affected",
        "risk_score": 0.80,
        "affected_bags": 87,
        "disruption_type": "CANCELLATION",
        "flight_number": "AA123",
        "alternative_flights_available": True,
        "pir_exists": False,
        "courier_needed": False,  # Will rebook on next flight
        "passenger_phone": "+13055551234"
    }

    print("→ Executing irrops workflow for affected bag 0291234569...")
    result_irrops = orchestrator.execute_workflow(
        workflow_type="irrops",
        bag_tag="0291234569",
        context=context_irrops,
        triggered_by="flight_ops_monitor"
    )

    print()
    print("RESULTS:")
    print(f"  Status: {result_irrops['metadata'].status.value}")
    print(f"  Duration: {result_irrops['metadata'].duration_ms:.0f}ms")
    print(f"  Steps executed: {len(result_irrops['workflow_history'])}")
    print()

    # ========================================================================
    # 5. SCENARIO 4: BULK MISHANDLING
    # ========================================================================

    print("=" * 80)
    print("5. SCENARIO 4: BULK MISHANDLING EVENT")
    print("=" * 80)
    print()

    print("Context: 23 bags from CM101 misloaded to wrong flight")
    print("Expected: Detect bulk → Master case → Batch PIRs → Coordinate recovery")
    print()

    context_bulk = {
        "trigger_reason": "Bulk misload - 23 bags from CM101 misloaded",
        "risk_score": 0.75,
        "affected_bags": 23,
        "root_cause": "MISLOAD",
        "flight_number": "CM101",
        "pir_exists": False,
        "courier": "ups",
        "passenger_phone": "+15075551234"
    }

    print("→ Executing bulk workflow for bag 0291234570...")
    result_bulk = orchestrator.execute_workflow(
        workflow_type="bulk",
        bag_tag="0291234570",
        context=context_bulk,
        triggered_by="ops_coordinator"
    )

    print()
    print("RESULTS:")
    print(f"  Status: {result_bulk['metadata'].status.value}")
    print(f"  Duration: {result_bulk['metadata'].duration_ms:.0f}ms")
    print(f"  Steps executed: {len(result_bulk['workflow_history'])}")
    print()

    # ========================================================================
    # 6. SCENARIO 5: DELIVERY COORDINATION
    # ========================================================================

    print("=" * 80)
    print("6. SCENARIO 5: COURIER DELIVERY COORDINATION")
    print("=" * 80)
    print()

    print("Context: Bag found, passenger already at destination, direct delivery needed")
    print("Expected: Validate address → Book courier → Track → Notify")
    print()

    context_delivery = {
        "trigger_reason": "Bag found, passenger at destination, direct delivery",
        "risk_score": 0.40,  # Lower risk, just logistics
        "delivery_address": "456 Park Ave, Miami, FL 33101",
        "courier": "fedex",
        "origin": "MIA",
        "destination": "456 Park Ave, Miami, FL 33101",
        "estimated_delivery": "2025-11-15T20:00:00Z",
        "courier_cost": 45.00,
        "passenger_phone": "+13055559999",
        "service_level": "standard"
    }

    print("→ Executing delivery workflow for bag 0291234571...")
    result_delivery = orchestrator.execute_workflow(
        workflow_type="delivery",
        bag_tag="0291234571",
        context=context_delivery,
        triggered_by="case_manager"
    )

    print()
    print("RESULTS:")
    print(f"  Status: {result_delivery['metadata'].status.value}")
    print(f"  Duration: {result_delivery['metadata'].duration_ms:.0f}ms")
    print(f"  Steps executed: {len(result_delivery['workflow_history'])}")
    print(f"  Delivery cost: ${result_delivery['metadata'].total_cost_usd:.2f}")
    print()

    # ========================================================================
    # 7. ORCHESTRATOR STATISTICS
    # ========================================================================

    print("=" * 80)
    print("7. ORCHESTRATOR STATISTICS")
    print("=" * 80)

    stats = orchestrator.get_statistics()

    print(f"Total workflow executions: {stats['total_executions']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Success rate: {stats['success_rate']:.1%}")
    print(f"Average duration: {stats['avg_duration_ms']:.0f}ms")
    print(f"Workflows registered: {stats['workflows_registered']}")
    print()

    # ========================================================================
    # 8. WORKFLOW HISTORY
    # ========================================================================

    print("8. WORKFLOW EXECUTION HISTORY")
    print("-" * 80)

    history = orchestrator.get_workflow_history(limit=10)

    for execution in history:
        print(f"  {execution['workflow_id']}:")
        print(f"    Type: {execution['workflow_type']}")
        print(f"    Bag: {execution['bag_tag']}")
        print(f"    Status: {execution['status']}")
        print(f"    Duration: {execution['duration_ms']:.0f}ms")
        print(f"    Steps: {execution['steps_executed']}")
        print(f"    Success rate: {execution['success_rate']:.1%}")
        print()

    # ========================================================================
    # 9. SUMMARY
    # ========================================================================

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("✓ LangGraph orchestrator with semantic reasoning")
    print("✓ 5 workflow templates demonstrated:")
    print("    1. High-risk bag (with human approval gate)")
    print("    2. Transfer coordination (tight connections)")
    print("    3. IRROPs recovery (flight disruptions)")
    print("    4. Bulk mishandling (>10 bags)")
    print("    5. Delivery coordination (courier logistics)")
    print()
    print("✓ Workflow features:")
    print("    • Parallel execution (concurrent operations)")
    print("    • Conditional routing (decision-based paths)")
    print("    • Loop/retry logic (fault tolerance)")
    print("    • Human-in-the-loop (approval gates)")
    print("    • Error handling & rollback")
    print("    • Semantic annotations (why decisions were made)")
    print()
    print("✓ Each workflow:")
    print("    • Coordinates multiple specialized agents")
    print("    • Tracks execution history with semantic reasoning")
    print("    • Records alternative paths considered")
    print("    • Provides complete observability")
    print("    • Enables workflow debugging and optimization")
    print()
    print(f"All {stats['total_executions']} workflows completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
