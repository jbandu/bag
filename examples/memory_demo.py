"""
Memory System Demo
==================

Demonstrates the complete 3-layer semantic memory system.

Shows:
- Layer 1: Working memory (current state, recent decisions)
- Layer 2: Episodic memory (complete journey history)
- Layer 3: Semantic memory (patterns and learning)
- Context building for agents
- Learning from outcomes

Version: 1.0.0
Date: 2025-11-14
"""

import sys
sys.path.insert(0, '/home/user/bag')

import asyncio
from datetime import datetime
from memory import AgentMemory
from memory.working_memory import BagProcessingState, ActiveWorkflow
from memory.semantic_memory import LearnedPattern, ResolutionStrategy


async def main():
    print("=" * 80)
    print("SEMANTIC MEMORY SYSTEM - 3-LAYER ARCHITECTURE")
    print("=" * 80)
    print()

    # ========================================================================
    # 1. INITIALIZE MEMORY SYSTEM
    # ========================================================================

    print("1. INITIALIZING MEMORY SYSTEM")
    print("-" * 80)

    memory = AgentMemory()
    await memory.connect()

    print("✓ Connected to all memory layers")
    print("  - Working memory (Redis/fallback)")
    print("  - Episodic memory (Neo4j/mock)")
    print("  - Semantic memory (Vector DB/mock)")
    print()

    # ========================================================================
    # 2. LAYER 1: WORKING MEMORY (Current State)
    # ========================================================================

    print("=" * 80)
    print("2. LAYER 1: WORKING MEMORY (Current State)")
    print("=" * 80)
    print()

    # Store bag processing state
    bag_tag = "0291234567"
    bag_state = BagProcessingState(
        bag_tag=bag_tag,
        current_status="DELAYED",
        current_location="LAX",
        risk_score=0.85,
        assigned_agents=["risk_scorer", "case_manager"],
        workflow_id="WF20251114120000",
        last_updated=datetime.now().isoformat(),
        next_action="dispatch_courier"
    )

    await memory.working_memory.set_bag_state(bag_tag, bag_state)
    print(f"✓ Stored current state for bag {bag_tag}")
    print(f"  Status: {bag_state.current_status}")
    print(f"  Risk Score: {bag_state.risk_score}")
    print(f"  Location: {bag_state.current_location}")
    print()

    # Store active workflow
    workflow = ActiveWorkflow(
        workflow_id="WF20251114120000",
        workflow_type="high_risk",
        bag_tag=bag_tag,
        status="IN_PROGRESS",
        started_at=datetime.now().isoformat(),
        current_step="dispatch_courier",
        progress_pct=65.0,
        agent_assignments={"risk_scorer": "completed", "case_manager": "in_progress"}
    )

    await memory.working_memory.set_active_workflow(workflow.workflow_id, workflow)
    print(f"✓ Stored active workflow {workflow.workflow_id}")
    print(f"  Type: {workflow.workflow_type}")
    print(f"  Progress: {workflow.progress_pct}%")
    print()

    # Store a recent decision
    await memory.remember(
        event_type="decision",
        bag_tag=bag_tag,
        agent_name="risk_scorer",
        context={
            "decision_type": "risk_assessment",
            "decision": "HIGH_RISK",
            "reasoning": "Tight connection + high value + VIP passenger",
            "confidence": 0.92
        },
        outcome="success"
    )

    print(f"✓ Remembered decision by risk_scorer")
    print(f"  Decision: HIGH_RISK")
    print(f"  Confidence: 0.92")
    print()

    # ========================================================================
    # 3. LAYER 2: EPISODIC MEMORY (History)
    # ========================================================================

    print("=" * 80)
    print("3. LAYER 2: EPISODIC MEMORY (Complete Journey)")
    print("=" * 80)
    print()

    # Record journey events
    await memory.remember(
        event_type="scan",
        bag_tag=bag_tag,
        agent_name="scan_processor",
        context={"location": "LAX", "scan_type": "check_in"},
        outcome="success"
    )

    await memory.remember(
        event_type="scan",
        bag_tag=bag_tag,
        agent_name="scan_processor",
        context={"location": "LAX_T4_SORT", "scan_type": "sort"},
        outcome="success"
    )

    await memory.remember(
        event_type="risk_assessment",
        bag_tag=bag_tag,
        agent_name="risk_scorer",
        context={"risk_score": 0.85, "risk_level": "HIGH"},
        outcome="success"
    )

    print(f"✓ Recorded journey events for bag {bag_tag}")
    print()

    # Get complete journey
    journey = await memory.episodic_memory.get_bag_journey(bag_tag)
    print(f"Complete journey ({len(journey)} events):")
    for event in journey:
        print(f"  - {event.event_type} at {event.location} by {event.agent_name}")
    print()

    # ========================================================================
    # 4. LAYER 3: SEMANTIC MEMORY (Patterns & Learning)
    # ========================================================================

    print("=" * 80)
    print("4. LAYER 3: SEMANTIC MEMORY (Learned Patterns)")
    print("=" * 80)
    print()

    # Learn a pattern
    pattern = LearnedPattern(
        pattern_id="pattern_001",
        pattern_type="high_risk_bag",
        description="Bags with risk > 0.8 at LAX often delayed",
        features={"location": "LAX", "risk_score_min": 0.8},
        occurrences=15,
        success_rate=0.87,
        confidence=0.75,
        examples=[bag_tag, "0291234568", "0291234569"],
        learned_at=datetime.now().isoformat(),
        last_updated=datetime.now().isoformat()
    )

    await memory.learn_pattern(pattern)
    print(f"✓ Learned pattern: {pattern.description}")
    print(f"  Occurrences: {pattern.occurrences}")
    print(f"  Success rate: {pattern.success_rate:.1%}")
    print(f"  Confidence: {pattern.confidence:.2f}")
    print()

    # Learn a strategy
    strategy = ResolutionStrategy(
        strategy_id="strategy_001",
        exception_type="DELAYED",
        strategy_name="Express Courier Delivery",
        description="Book FedEx priority for high-value bags",
        steps=["assess_value", "book_fedex", "notify_passenger"],
        success_count=28,
        failure_count=3,
        success_rate=0.90,
        avg_duration_ms=12000.0,
        avg_cost_usd=125.0,
        confidence=0.88,
        applicable_contexts=["HIGH_RISK", "VIP_PASSENGER"],
        created_at=datetime.now().isoformat(),
        last_used=None
    )

    await memory.learn_strategy(strategy)
    print(f"✓ Learned strategy: {strategy.strategy_name}")
    print(f"  Exception type: {strategy.exception_type}")
    print(f"  Success rate: {strategy.success_rate:.1%}")
    print(f"  Avg cost: ${strategy.avg_cost_usd:.2f}")
    print()

    # Store some similar cases for semantic search
    await memory.semantic_memory.store_case(
        bag_tag="0291234568",
        features={"risk_score": 0.82, "location": "LAX", "status": "DELAYED"},
        outcome="success",
        resolution_strategy="Express Courier Delivery",
        duration_ms=11500.0,
        cost_usd=120.0
    )

    await memory.semantic_memory.store_case(
        bag_tag="0291234569",
        features={"risk_score": 0.88, "location": "LAX", "status": "DELAYED"},
        outcome="success",
        resolution_strategy="Express Courier Delivery",
        duration_ms=13200.0,
        cost_usd=130.0
    )

    print("✓ Stored similar historical cases for semantic search")
    print()

    # ========================================================================
    # 5. CONTEXT BUILDING
    # ========================================================================

    print("=" * 80)
    print("5. CONTEXT BUILDING FOR AGENTS")
    print("=" * 80)
    print()

    context = await memory.build_context(bag_tag, agent_name="courier_dispatch")

    print(f"Built context for bag {bag_tag}:")
    print()
    print(f"Current State:")
    print(f"  - Status: {context.current_state['status']}")
    print(f"  - Location: {context.current_state['location']}")
    print(f"  - Risk Score: {context.current_state['risk_score']:.2f}")
    print()

    print(f"Similar Cases: {len(context.similar_cases)}")
    for case in context.similar_cases[:3]:
        print(f"  - {case['bag_tag']}: {case['outcome']} (similarity: {case['similarity']:.2f})")
    print()

    print(f"Relevant Patterns: {len(context.relevant_patterns)}")
    for pattern in context.relevant_patterns:
        print(f"  - {pattern['description']} (confidence: {pattern['confidence']:.2f})")
    print()

    if context.recommended_strategies:
        print(f"Recommended Strategies:")
        for strat in context.recommended_strategies:
            print(f"  - {strat['name']}: {strat['description']}")
            print(f"    Success rate: {strat['success_rate']:.1%}, Avg cost: ${strat['avg_cost_usd']:.2f}")
    print()

    # ========================================================================
    # 6. SEMANTIC QUERIES
    # ========================================================================

    print("=" * 80)
    print("6. SEMANTIC QUERIES")
    print("=" * 80)
    print()

    # Query 1: Similar risk factors
    print("Query: 'Have we seen bags with similar risk factors?'")
    similar_risk = await memory.query_similar_risk_factors(
        bag_tag,
        {"risk_score": 0.85, "location": "LAX"}
    )

    print(f"Found {similar_risk['count']} similar cases:")
    for case in similar_risk['cases'][:3]:
        print(f"  - {case['bag_tag']}: {case['outcome']} (similarity: {case['similarity']:.2f})")
    print(f"Average success rate: {similar_risk['avg_success_rate']:.1%}")
    print()

    # Query 2: Successful strategies
    print("Query: 'What strategies worked for DELAYED bags?'")
    strategies = await memory.query_successful_strategies(
        "DELAYED",
        {"risk_score": 0.85}
    )

    print(f"Found {strategies['count']} strategies:")
    for strat in strategies['strategies']:
        print(f"  - {strat['name']}: {strat['success_rate']:.1%} success")
        print(f"    Used {strat['used_times']} times, avg cost: ${strat['avg_cost']:.2f}")
    print()

    # Query 3: Agent performance
    print("Query: 'How well has courier_dispatch performed?'")
    agent_perf = await memory.query_agent_performance("courier_dispatch")

    print(f"Agent: {agent_perf['agent_name']}")
    print(f"  Total events: {agent_perf['total_events']}")
    print(f"  Success rate: {agent_perf['success_rate']:.1%}")
    print()

    # ========================================================================
    # 7. LEARNING FROM OUTCOMES
    # ========================================================================

    print("=" * 80)
    print("7. LEARNING FROM OUTCOMES (Feedback Loop)")
    print("=" * 80)
    print()

    # Simulate workflow completion and learning
    await memory.learn_from_outcome(
        entity_type="workflow",
        entity_id="WF20251114120000",
        success=True,
        duration_ms=15000.0,
        cost_usd=125.0,
        metrics={
            "workflow_type": "high_risk",
            "bag_tag": bag_tag,
            "strategy_used": "Express Courier Delivery"
        }
    )

    print("✓ Learned from workflow outcome")
    print("  - Workflow completed successfully")
    print("  - Duration: 15,000ms")
    print("  - Cost: $125.00")
    print()

    # Update strategy based on this outcome
    await memory.semantic_memory.update_strategy(
        strategy_id="strategy_001",
        success=True,
        duration_ms=15000.0,
        cost_usd=125.0
    )

    print("✓ Updated strategy confidence")
    print("  - Success count increased")
    print("  - Average duration updated")
    print()

    # Discover patterns
    patterns = await memory.learning_engine.discover_patterns(min_occurrences=1)
    print(f"✓ Discovered {len(patterns)} new patterns from outcomes")
    print()

    # ========================================================================
    # 8. MEMORY STATISTICS
    # ========================================================================

    print("=" * 80)
    print("8. MEMORY STATISTICS")
    print("=" * 80)

    stats = await memory.get_stats()

    print(f"Working Memory:")
    print(f"  - Active bags: {stats['working_memory']['active_bags']}")
    print(f"  - Using Redis: {stats['working_memory']['using_redis']}")
    print()

    print(f"Episodic Memory:")
    print(f"  - Using Neo4j: {stats['episodic_memory']['using_neo4j']}")
    if not stats['episodic_memory']['using_neo4j']:
        print(f"  - Mock nodes: {stats['episodic_memory']['total_nodes']}")
        print(f"  - Mock relationships: {stats['episodic_memory']['total_relationships']}")
    print()

    print(f"Semantic Memory:")
    print(f"  - Patterns learned: {stats['semantic_memory']['total_patterns']}")
    print(f"  - Strategies learned: {stats['semantic_memory']['total_strategies']}")
    print(f"  - Embeddings stored: {stats['semantic_memory']['total_embeddings']}")
    print()

    print(f"Learning Engine:")
    print(f"  - Outcomes tracked: {stats['learning']['total_outcomes']}")
    print(f"  - Success rate: {stats['learning']['success_rate']:.1%}")
    print(f"  - Avg duration: {stats['learning']['avg_duration_ms']:.0f}ms")
    print(f"  - Learnings discovered: {stats['learning']['learnings_discovered']}")
    print()

    # ========================================================================
    # 9. CLEANUP
    # ========================================================================

    await memory.disconnect()

    # ========================================================================
    # 10. SUMMARY
    # ========================================================================

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("✓ 3-Layer Memory Architecture Demonstrated:")
    print()
    print("  LAYER 1: Working Memory (Fast, Volatile)")
    print("    - Current bag states")
    print("    - Active workflows")
    print("    - Recent decisions (last hour)")
    print("    - Query cache")
    print()
    print("  LAYER 2: Episodic Memory (Complete History)")
    print("    - Complete bag journeys")
    print("    - Agent interactions")
    print("    - Workflow executions")
    print("    - Temporal relationships")
    print()
    print("  LAYER 3: Semantic Memory (Learned Knowledge)")
    print("    - Patterns discovered from data")
    print("    - Resolution strategies with success rates")
    print("    - Similar case lookup")
    print("    - Contextual recommendations")
    print()
    print("✓ Features Demonstrated:")
    print("  - Remember events across all layers")
    print("  - Recall with natural language queries")
    print("  - Find similar cases via semantic search")
    print("  - Build rich context for agents")
    print("  - Learn from outcomes (feedback loop)")
    print("  - Pattern discovery")
    print("  - Strategy optimization")
    print()
    print("Agents now have MEMORY and can LEARN!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
