"""
Context Builder
===============

Builds rich context for agents by querying all memory layers.

Provides agents with:
- Current state (working memory)
- Historical context (episodic memory)
- Learned patterns (semantic memory)

Example queries:
- "Have we seen bags with similar risk factors?"
- "What happened to similar bags in the past?"
- "What strategies worked for similar exceptions?"
- "Which couriers were reliable for similar deliveries?"

Version: 1.0.0
Date: 2025-11-14
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from memory.working_memory import WorkingMemory
from memory.episodic_memory import EpisodicMemory
from memory.semantic_memory import SemanticMemory


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AgentContext:
    """Rich context for an agent"""
    bag_tag: str
    current_state: Optional[Dict[str, Any]]
    active_workflows: List[Dict[str, Any]]
    recent_decisions: List[Dict[str, Any]]
    historical_journey: List[Dict[str, Any]]
    similar_cases: List[Dict[str, Any]]
    relevant_patterns: List[Dict[str, Any]]
    recommended_strategies: List[Dict[str, Any]]
    agent_performance: Dict[str, Any]
    built_at: str


# ============================================================================
# CONTEXT BUILDER
# ============================================================================

class ContextBuilder:
    """
    Builds rich context for agents by querying all memory layers.

    Aggregates information from:
    - Working memory (current state)
    - Episodic memory (history)
    - Semantic memory (patterns and strategies)
    """

    def __init__(
        self,
        working_memory: WorkingMemory,
        episodic_memory: EpisodicMemory,
        semantic_memory: SemanticMemory
    ):
        """Initialize context builder"""
        self.working_memory = working_memory
        self.episodic_memory = episodic_memory
        self.semantic_memory = semantic_memory

        logger.info("ContextBuilder initialized")

    # ========================================================================
    # MAIN CONTEXT BUILDING
    # ========================================================================

    async def build_context_for_bag(
        self,
        bag_tag: str,
        agent_name: Optional[str] = None,
        include_similar_cases: bool = True,
        include_patterns: bool = True,
        include_strategies: bool = False
    ) -> AgentContext:
        """
        Build complete context for a bag.

        Args:
            bag_tag: Bag tag to build context for
            agent_name: Optional agent name for agent-specific context
            include_similar_cases: Include similar historical cases
            include_patterns: Include learned patterns
            include_strategies: Include resolution strategies

        Returns:
            AgentContext with all relevant information
        """

        logger.info(f"Building context for bag {bag_tag}")

        # Layer 1: Current state from working memory
        current_state = None
        bag_state = await self.working_memory.get_bag_state(bag_tag)
        if bag_state:
            current_state = {
                "status": bag_state.current_status,
                "location": bag_state.current_location,
                "risk_score": bag_state.risk_score,
                "assigned_agents": bag_state.assigned_agents,
                "workflow_id": bag_state.workflow_id,
                "last_updated": bag_state.last_updated,
                "next_action": bag_state.next_action
            }

        # Active workflows
        active_workflows = []
        workflows = await self.working_memory.get_workflows_by_bag(bag_tag)
        for workflow in workflows:
            active_workflows.append({
                "workflow_id": workflow.workflow_id,
                "type": workflow.workflow_type,
                "status": workflow.status,
                "current_step": workflow.current_step,
                "progress": workflow.progress_pct
            })

        # Recent decisions
        recent_decisions = []
        decisions = await self.working_memory.get_recent_decisions(bag_tag=bag_tag, limit=5)
        for decision in decisions:
            recent_decisions.append({
                "agent": decision.agent_name,
                "type": decision.decision_type,
                "decision": decision.decision,
                "reasoning": decision.reasoning,
                "confidence": decision.confidence,
                "timestamp": decision.timestamp
            })

        # Layer 2: Historical journey from episodic memory
        historical_journey = []
        journey = await self.episodic_memory.get_bag_journey(bag_tag)
        for event in journey:
            historical_journey.append({
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "location": event.location,
                "agent": event.agent_name,
                "outcome": event.outcome
            })

        # Layer 3: Semantic memory - patterns and similar cases
        similar_cases = []
        relevant_patterns = []
        recommended_strategies = []

        if bag_state and (include_similar_cases or include_patterns or include_strategies):
            # Build feature set from current bag
            features = {
                "risk_score": bag_state.risk_score,
                "status": bag_state.current_status,
                "location": bag_state.current_location
            }

            # Similar cases
            if include_similar_cases:
                cases = await self.semantic_memory.find_similar_cases(features, top_k=5)
                similar_cases = [
                    {
                        "bag_tag": case.bag_tag,
                        "similarity": case.similarity_score,
                        "outcome": case.outcome,
                        "resolution": case.resolution_strategy,
                        "duration_ms": case.duration_ms,
                        "cost_usd": case.cost_usd
                    }
                    for case in cases
                ]

            # Patterns
            if include_patterns:
                patterns = await self.semantic_memory.find_similar_patterns(features, top_k=3)
                relevant_patterns = [
                    {
                        "type": pattern.pattern_type,
                        "description": pattern.description,
                        "similarity": similarity,
                        "success_rate": pattern.success_rate,
                        "confidence": pattern.confidence,
                        "occurrences": pattern.occurrences
                    }
                    for pattern, similarity in patterns
                ]

            # Strategies (if exception type known)
            if include_strategies and current_state:
                exception_type = current_state.get("status", "UNKNOWN")
                strategies = await self.semantic_memory.find_strategies(
                    exception_type=exception_type,
                    context=features,
                    top_k=3
                )
                recommended_strategies = [
                    {
                        "name": strategy.strategy_name,
                        "description": strategy.description,
                        "relevance": relevance,
                        "success_rate": strategy.success_rate,
                        "avg_duration_ms": strategy.avg_duration_ms,
                        "avg_cost_usd": strategy.avg_cost_usd,
                        "confidence": strategy.confidence
                    }
                    for strategy, relevance in strategies
                ]

        # Agent performance (if agent specified)
        agent_performance = {}
        if agent_name:
            agent_performance = await self.episodic_memory.get_agent_performance(agent_name)

        # Build context
        context = AgentContext(
            bag_tag=bag_tag,
            current_state=current_state,
            active_workflows=active_workflows,
            recent_decisions=recent_decisions,
            historical_journey=historical_journey,
            similar_cases=similar_cases,
            relevant_patterns=relevant_patterns,
            recommended_strategies=recommended_strategies,
            agent_performance=agent_performance,
            built_at=datetime.now().isoformat()
        )

        logger.info(
            f"Context built: {len(similar_cases)} similar cases, "
            f"{len(relevant_patterns)} patterns, "
            f"{len(recommended_strategies)} strategies"
        )

        return context

    # ========================================================================
    # SPECIFIC QUERIES
    # ========================================================================

    async def has_similar_risk_factors(
        self,
        bag_tag: str,
        risk_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Query: "Have we seen bags with similar risk factors?"

        Args:
            bag_tag: Current bag
            risk_features: Risk factors to compare

        Returns:
            Dictionary with similar bags and their outcomes
        """

        similar_cases = await self.semantic_memory.find_similar_cases(
            risk_features,
            top_k=10
        )

        return {
            "found_similar": len(similar_cases) > 0,
            "count": len(similar_cases),
            "cases": [
                {
                    "bag_tag": case.bag_tag,
                    "similarity": case.similarity_score,
                    "outcome": case.outcome,
                    "what_happened": f"Resolved via {case.resolution_strategy}" if case.resolution_strategy else "Unknown resolution"
                }
                for case in similar_cases
            ],
            "avg_success_rate": (
                sum(1 for c in similar_cases if c.outcome == "success") / len(similar_cases)
                if similar_cases else 0.0
            )
        }

    async def what_worked_for_similar_bags(
        self,
        exception_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Query: "What strategies worked for similar exceptions?"

        Args:
            exception_type: Type of exception
            context: Current context

        Returns:
            Dictionary with successful strategies
        """

        strategies = await self.semantic_memory.find_strategies(
            exception_type=exception_type,
            context=context,
            min_success_rate=0.7,
            top_k=5
        )

        return {
            "found_strategies": len(strategies) > 0,
            "count": len(strategies),
            "strategies": [
                {
                    "name": strategy.strategy_name,
                    "description": strategy.description,
                    "relevance": relevance,
                    "success_rate": strategy.success_rate,
                    "used_times": strategy.success_count + strategy.failure_count,
                    "avg_cost": strategy.avg_cost_usd,
                    "avg_duration_ms": strategy.avg_duration_ms
                }
                for strategy, relevance in strategies
            ]
        }

    async def find_similar_journeys(
        self,
        bag_tag: str,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Query: "What happened to bags with similar journeys?"

        Args:
            bag_tag: Bag to find similar journeys for
            similarity_threshold: Minimum similarity score

        Returns:
            Dictionary with similar journeys
        """

        similar_bags = await self.episodic_memory.find_similar_journeys(
            bag_tag,
            similarity_threshold
        )

        # Get journey details for each
        journeys = []
        for similar_bag in similar_bags[:5]:  # Limit to 5
            journey = await self.episodic_memory.get_bag_journey(similar_bag)
            workflows = await self.episodic_memory.get_workflows_for_bag(similar_bag)

            journeys.append({
                "bag_tag": similar_bag,
                "events": len(journey),
                "workflows": len(workflows),
                "final_outcome": workflows[-1].outcome if workflows else "unknown"
            })

        return {
            "found_similar": len(journeys) > 0,
            "count": len(journeys),
            "journeys": journeys
        }

    async def get_agent_track_record(
        self,
        agent_name: str,
        task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query: "How well has this agent performed on similar tasks?"

        Args:
            agent_name: Agent name
            task_type: Optional task type filter

        Returns:
            Dictionary with agent performance
        """

        performance = await self.episodic_memory.get_agent_performance(agent_name)

        interactions = await self.episodic_memory.get_agent_interactions(
            agent_name,
            limit=10
        )

        return {
            "agent_name": agent_name,
            "total_events": performance.get("total_events", 0),
            "success_rate": performance.get("success_rate", 0.0),
            "recent_interactions": len(interactions),
            "collaboration_partners": list(set(
                i.to_agent for i in interactions
            ))
        }

    # ========================================================================
    # CONTEXT SUMMARY
    # ========================================================================

    def summarize_context(self, context: AgentContext) -> str:
        """
        Create human-readable summary of context.

        Args:
            context: Agent context

        Returns:
            Text summary
        """

        summary_lines = [
            f"Context for bag {context.bag_tag}:",
            ""
        ]

        if context.current_state:
            summary_lines.extend([
                "Current State:",
                f"  Status: {context.current_state.get('status')}",
                f"  Location: {context.current_state.get('location')}",
                f"  Risk Score: {context.current_state.get('risk_score', 0):.2f}",
                ""
            ])

        if context.similar_cases:
            summary_lines.extend([
                f"Found {len(context.similar_cases)} similar cases:",
            ])
            for case in context.similar_cases[:3]:
                summary_lines.append(
                    f"  - {case['bag_tag']}: {case['outcome']} "
                    f"(similarity: {case['similarity']:.2f})"
                )
            summary_lines.append("")

        if context.relevant_patterns:
            summary_lines.extend([
                f"Relevant patterns:",
            ])
            for pattern in context.relevant_patterns:
                summary_lines.append(
                    f"  - {pattern['description']} "
                    f"(success rate: {pattern['success_rate']:.1%})"
                )
            summary_lines.append("")

        if context.recommended_strategies:
            summary_lines.extend([
                f"Recommended strategies:",
            ])
            for strategy in context.recommended_strategies:
                summary_lines.append(
                    f"  - {strategy['name']}: {strategy['description']} "
                    f"(success: {strategy['success_rate']:.1%})"
                )

        return "\n".join(summary_lines)
