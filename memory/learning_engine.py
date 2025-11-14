"""
Learning Engine
===============

Implements feedback loop for continuous learning from outcomes.

Features:
- Track outcomes of decisions
- Update confidence scores based on success
- Adjust strategies based on results
- Share learnings across agents
- Pattern discovery and reinforcement

Version: 1.0.0
Date: 2025-11-14
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from loguru import logger
import uuid

from memory.working_memory import WorkingMemory, RecentDecision
from memory.episodic_memory import EpisodicMemory, BagJourneyEvent, WorkflowExecution
from memory.semantic_memory import (
    SemanticMemory,
    LearnedPattern,
    ResolutionStrategy
)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Outcome:
    """Outcome of a decision or workflow"""
    outcome_id: str
    entity_type: str  # decision, workflow, strategy
    entity_id: str
    success: bool
    duration_ms: float
    cost_usd: float
    metrics: Dict[str, Any]
    timestamp: str


@dataclass
class Learning:
    """A learning extracted from outcomes"""
    learning_id: str
    learning_type: str  # pattern, strategy, agent_skill
    description: str
    confidence: float
    evidence_count: int
    created_at: str


# ============================================================================
# LEARNING ENGINE
# ============================================================================

class LearningEngine:
    """
    Feedback loop for continuous learning.

    Tracks outcomes → Updates models → Improves future decisions
    """

    def __init__(
        self,
        working_memory: WorkingMemory,
        episodic_memory: EpisodicMemory,
        semantic_memory: SemanticMemory
    ):
        """Initialize learning engine"""
        self.working_memory = working_memory
        self.episodic_memory = episodic_memory
        self.semantic_memory = semantic_memory

        # Learning state
        self.outcomes_tracked: List[Outcome] = []
        self.learnings: Dict[str, Learning] = {}

        logger.info("LearningEngine initialized")

    # ========================================================================
    # OUTCOME TRACKING
    # ========================================================================

    async def record_outcome(self, outcome: Outcome):
        """
        Record an outcome for learning.

        Args:
            outcome: Outcome to record
        """

        self.outcomes_tracked.append(outcome)

        # Process outcome based on type
        if outcome.entity_type == "decision":
            await self._learn_from_decision(outcome)
        elif outcome.entity_type == "workflow":
            await self._learn_from_workflow(outcome)
        elif outcome.entity_type == "strategy":
            await self._learn_from_strategy(outcome)

        logger.info(
            f"Recorded outcome: {outcome.entity_type} {outcome.entity_id} "
            f"({'success' if outcome.success else 'failure'})"
        )

    async def _learn_from_decision(self, outcome: Outcome):
        """Learn from a decision outcome"""

        # Update decision confidence if it was recent
        decisions = await self.working_memory.get_recent_decisions(limit=100)

        for decision in decisions:
            if decision.decision_id == outcome.entity_id:
                # Adjust confidence based on outcome
                new_confidence = decision.confidence
                if outcome.success:
                    new_confidence = min(1.0, new_confidence * 1.1)
                else:
                    new_confidence = max(0.1, new_confidence * 0.9)

                logger.debug(
                    f"Updated decision confidence: {decision.confidence:.2f} → {new_confidence:.2f}"
                )
                break

    async def _learn_from_workflow(self, outcome: Outcome):
        """Learn from a workflow outcome"""

        # Extract features from workflow outcome
        workflow_type = outcome.metrics.get("workflow_type", "unknown")
        bag_tag = outcome.metrics.get("bag_tag")

        # Record in episodic memory
        if bag_tag:
            event = BagJourneyEvent(
                event_id=f"outcome_{outcome.outcome_id}",
                bag_tag=bag_tag,
                event_type="workflow_completed",
                timestamp=outcome.timestamp,
                location=None,
                agent_name="learning_engine",
                data={
                    "workflow_type": workflow_type,
                    "success": outcome.success,
                    "duration_ms": outcome.duration_ms,
                    "cost_usd": outcome.cost_usd
                },
                outcome="success" if outcome.success else "failure"
            )

            await self.episodic_memory.record_event(event)

        # Store as case in semantic memory
        if bag_tag and outcome.success:
            features = {
                "workflow_type": workflow_type,
                "duration_ms": outcome.duration_ms,
                "cost_usd": outcome.cost_usd,
                **outcome.metrics
            }

            await self.semantic_memory.store_case(
                bag_tag=bag_tag,
                features=features,
                outcome="success",
                resolution_strategy=workflow_type,
                duration_ms=outcome.duration_ms,
                cost_usd=outcome.cost_usd
            )

    async def _learn_from_strategy(self, outcome: Outcome):
        """Learn from a strategy outcome"""

        # Update strategy in semantic memory
        await self.semantic_memory.update_strategy(
            strategy_id=outcome.entity_id,
            success=outcome.success,
            duration_ms=outcome.duration_ms,
            cost_usd=outcome.cost_usd
        )

    # ========================================================================
    # PATTERN DISCOVERY
    # ========================================================================

    async def discover_patterns(self, min_occurrences: int = 5) -> List[LearnedPattern]:
        """
        Discover new patterns from recent outcomes.

        Args:
            min_occurrences: Minimum occurrences to consider a pattern

        Returns:
            List of discovered patterns
        """

        logger.info("Discovering patterns...")

        discovered = []

        # Analyze successful outcomes
        successful_outcomes = [o for o in self.outcomes_tracked if o.success]

        # Group by workflow type
        workflow_types: Dict[str, List[Outcome]] = {}
        for outcome in successful_outcomes:
            if outcome.entity_type == "workflow":
                wf_type = outcome.metrics.get("workflow_type", "unknown")
                if wf_type not in workflow_types:
                    workflow_types[wf_type] = []
                workflow_types[wf_type].append(outcome)

        # Create patterns for frequently successful workflows
        for wf_type, outcomes in workflow_types.items():
            if len(outcomes) >= min_occurrences:
                pattern = LearnedPattern(
                    pattern_id=f"pattern_{wf_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    pattern_type="successful_workflow",
                    description=f"{wf_type} workflow tends to succeed",
                    features={"workflow_type": wf_type},
                    occurrences=len(outcomes),
                    success_rate=1.0,  # All in this group were successful
                    confidence=min(1.0, len(outcomes) / 20.0),
                    examples=[o.metrics.get("bag_tag", "") for o in outcomes[:5]],
                    learned_at=datetime.now().isoformat(),
                    last_updated=datetime.now().isoformat()
                )

                await self.semantic_memory.learn_pattern(pattern)
                discovered.append(pattern)

        logger.info(f"Discovered {len(discovered)} patterns")
        return discovered

    # ========================================================================
    # STRATEGY OPTIMIZATION
    # ========================================================================

    async def optimize_strategies(self):
        """
        Optimize strategies based on outcomes.

        Promotes successful strategies, demotes failing ones.
        """

        logger.info("Optimizing strategies...")

        strategy_outcomes: Dict[str, List[Outcome]] = {}

        for outcome in self.outcomes_tracked:
            if outcome.entity_type == "strategy":
                strategy_id = outcome.entity_id
                if strategy_id not in strategy_outcomes:
                    strategy_outcomes[strategy_id] = []
                strategy_outcomes[strategy_id].append(outcome)

        # Analyze each strategy
        for strategy_id, outcomes in strategy_outcomes.items():
            if len(outcomes) < 3:  # Need at least 3 data points
                continue

            success_rate = sum(1 for o in outcomes if o.success) / len(outcomes)

            logger.info(
                f"Strategy {strategy_id}: {success_rate:.1%} success "
                f"over {len(outcomes)} uses"
            )

            # If strategy is consistently failing, mark it
            if success_rate < 0.3 and len(outcomes) >= 5:
                logger.warning(f"Strategy {strategy_id} has low success rate, consider revision")

    # ========================================================================
    # AGENT LEARNING SHARING
    # ========================================================================

    async def share_learning_across_agents(self, learning: Learning):
        """
        Share a learning across all agents.

        Args:
            learning: Learning to share
        """

        self.learnings[learning.learning_id] = learning

        logger.info(f"Shared learning: {learning.description} (confidence: {learning.confidence:.2f})")

    # ========================================================================
    # FEEDBACK SUMMARIES
    # ========================================================================

    async def get_feedback_summary(self, last_n_hours: int = 24) -> Dict[str, Any]:
        """
        Get summary of recent feedback and learning.

        Args:
            last_n_hours: Look back period in hours

        Returns:
            Summary dictionary
        """

        total_outcomes = len(self.outcomes_tracked)
        successful = sum(1 for o in self.outcomes_tracked if o.success)
        failed = total_outcomes - successful

        success_rate = successful / total_outcomes if total_outcomes > 0 else 0.0

        # Averages
        avg_duration = (
            sum(o.duration_ms for o in self.outcomes_tracked) / total_outcomes
            if total_outcomes > 0 else 0.0
        )

        avg_cost = (
            sum(o.cost_usd for o in self.outcomes_tracked) / total_outcomes
            if total_outcomes > 0 else 0.0
        )

        return {
            "period_hours": last_n_hours,
            "total_outcomes": total_outcomes,
            "successful": successful,
            "failed": failed,
            "success_rate": success_rate,
            "avg_duration_ms": avg_duration,
            "avg_cost_usd": avg_cost,
            "learnings_discovered": len(self.learnings),
            "patterns_learned": sum(
                1 for l in self.learnings.values()
                if l.learning_type == "pattern"
            )
        }
