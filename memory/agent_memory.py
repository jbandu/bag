"""
Agent Memory
============

Unified memory interface for agents.

Provides simple API to access all three memory layers:
- Layer 1: Working memory (current state)
- Layer 2: Episodic memory (history)
- Layer 3: Semantic memory (patterns and learning)

Example usage:
    memory = AgentMemory()
    await memory.connect()

    # Store current decision
    await memory.remember(event, context)

    # Recall similar situations
    similar = await memory.recall("bags with high risk at LAX")

    # Find similar cases
    cases = await memory.find_similar(current_bag)

    # Learn from outcome
    await memory.learn_from_outcome(outcome)

Version: 1.0.0
Date: 2025-11-14
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger
import uuid

from memory.working_memory import (
    WorkingMemory,
    BagProcessingState,
    ActiveWorkflow,
    RecentDecision
)
from memory.episodic_memory import (
    EpisodicMemory,
    BagJourneyEvent,
    AgentInteraction,
    WorkflowExecution
)
from memory.semantic_memory import (
    SemanticMemory,
    LearnedPattern,
    ResolutionStrategy,
    SimilarCase
)
from memory.context_builder import ContextBuilder, AgentContext
from memory.learning_engine import LearningEngine, Outcome


# ============================================================================
# UNIFIED AGENT MEMORY
# ============================================================================

class AgentMemory:
    """
    Unified memory interface for all agents.

    Simplifies access to all three memory layers.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password"
    ):
        """Initialize agent memory"""

        # Initialize all layers
        self.working_memory = WorkingMemory(redis_url)
        self.episodic_memory = EpisodicMemory(neo4j_uri, neo4j_user, neo4j_password)
        self.semantic_memory = SemanticMemory()

        # Initialize helpers
        self.context_builder = ContextBuilder(
            self.working_memory,
            self.episodic_memory,
            self.semantic_memory
        )

        self.learning_engine = LearningEngine(
            self.working_memory,
            self.episodic_memory,
            self.semantic_memory
        )

        logger.info("AgentMemory initialized")

    async def connect(self):
        """Connect to all memory backends"""
        await self.working_memory.connect()
        await self.episodic_memory.connect()
        logger.info("Agent memory connected")

    async def disconnect(self):
        """Disconnect from all memory backends"""
        await self.working_memory.disconnect()
        await self.episodic_memory.disconnect()
        logger.info("Agent memory disconnected")

    # ========================================================================
    # REMEMBER (Store)
    # ========================================================================

    async def remember(
        self,
        event_type: str,
        bag_tag: str,
        agent_name: str,
        context: Dict[str, Any],
        outcome: Optional[str] = None
    ):
        """
        Remember an event.

        Stores in appropriate memory layers based on event type.

        Args:
            event_type: Type of event
            bag_tag: Bag tag
            agent_name: Agent that performed action
            context: Event context
            outcome: Optional outcome
        """

        # Create event
        event = BagJourneyEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            bag_tag=bag_tag,
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            location=context.get("location"),
            agent_name=agent_name,
            data=context,
            outcome=outcome
        )

        # Store in episodic memory (always)
        await self.episodic_memory.record_event(event)

        # If it's a decision, also store in working memory
        if event_type == "decision":
            decision = RecentDecision(
                decision_id=event.event_id,
                agent_name=agent_name,
                bag_tag=bag_tag,
                decision_type=context.get("decision_type", "unknown"),
                decision=context.get("decision", ""),
                reasoning=context.get("reasoning", ""),
                confidence=context.get("confidence", 0.5),
                timestamp=event.timestamp,
                context=context
            )

            await self.working_memory.store_decision(decision)

        logger.debug(f"Remembered: {event_type} for {bag_tag} by {agent_name}")

    # ========================================================================
    # RECALL (Retrieve)
    # ========================================================================

    async def recall(
        self,
        query: str,
        bag_tag: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recall memories matching a query.

        Natural language queries like:
        - "recent decisions for this bag"
        - "similar bags"
        - "what happened at LAX"

        Args:
            query: Natural language query
            bag_tag: Optional bag tag filter
            limit: Maximum results

        Returns:
            List of matching memories
        """

        results = []

        # Parse query (simple keyword matching for demo)
        query_lower = query.lower()

        # "recent decisions"
        if "recent" in query_lower and "decision" in query_lower:
            decisions = await self.working_memory.get_recent_decisions(
                bag_tag=bag_tag,
                limit=limit
            )

            results = [
                {
                    "type": "decision",
                    "agent": d.agent_name,
                    "decision": d.decision,
                    "reasoning": d.reasoning,
                    "confidence": d.confidence,
                    "timestamp": d.timestamp
                }
                for d in decisions
            ]

        # "journey" or "history"
        elif ("journey" in query_lower or "history" in query_lower) and bag_tag:
            journey = await self.episodic_memory.get_bag_journey(bag_tag)

            results = [
                {
                    "type": "event",
                    "event_type": e.event_type,
                    "location": e.location,
                    "agent": e.agent_name,
                    "timestamp": e.timestamp,
                    "outcome": e.outcome
                }
                for e in journey
            ]

        # "similar"
        elif "similar" in query_lower and bag_tag:
            # Get current bag state
            bag_state = await self.working_memory.get_bag_state(bag_tag)
            if bag_state:
                features = {
                    "risk_score": bag_state.risk_score,
                    "status": bag_state.current_status
                }

                similar_cases = await self.semantic_memory.find_similar_cases(
                    features,
                    top_k=limit
                )

                results = [
                    {
                        "type": "similar_case",
                        "bag_tag": c.bag_tag,
                        "similarity": c.similarity_score,
                        "outcome": c.outcome,
                        "resolution": c.resolution_strategy
                    }
                    for c in similar_cases
                ]

        return results

    async def find_similar(
        self,
        bag_tag: str,
        top_k: int = 5
    ) -> List[SimilarCase]:
        """
        Find similar cases to a bag.

        Args:
            bag_tag: Bag to find similar cases for
            top_k: Number of results

        Returns:
            List of similar cases
        """

        # Get current bag features
        bag_state = await self.working_memory.get_bag_state(bag_tag)

        if not bag_state:
            return []

        features = {
            "risk_score": bag_state.risk_score,
            "status": bag_state.current_status,
            "location": bag_state.current_location
        }

        return await self.semantic_memory.find_similar_cases(features, top_k)

    # ========================================================================
    # LEARN
    # ========================================================================

    async def learn_pattern(self, pattern: LearnedPattern):
        """Learn a new pattern"""
        await self.semantic_memory.learn_pattern(pattern)

    async def learn_strategy(self, strategy: ResolutionStrategy):
        """Learn a new resolution strategy"""
        await self.semantic_memory.learn_strategy(strategy)

    async def learn_from_outcome(
        self,
        entity_type: str,
        entity_id: str,
        success: bool,
        duration_ms: float,
        cost_usd: float,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Learn from an outcome.

        Updates strategies and patterns based on results.

        Args:
            entity_type: Type (decision, workflow, strategy)
            entity_id: ID of entity
            success: Whether it succeeded
            duration_ms: Duration
            cost_usd: Cost
            metrics: Additional metrics
        """

        outcome = Outcome(
            outcome_id=f"out_{uuid.uuid4().hex[:12]}",
            entity_type=entity_type,
            entity_id=entity_id,
            success=success,
            duration_ms=duration_ms,
            cost_usd=cost_usd,
            metrics=metrics or {},
            timestamp=datetime.now().isoformat()
        )

        await self.learning_engine.record_outcome(outcome)

    # ========================================================================
    # FORGET (Archive)
    # ========================================================================

    async def archive_old(self, older_than: timedelta):
        """
        Archive old working memory entries.

        Args:
            older_than: Archive entries older than this
        """

        # Working memory auto-expires via TTL
        # For explicit archiving, we'd move to episodic memory
        logger.info(f"Archiving entries older than {older_than}")

    # ========================================================================
    # CONTEXT BUILDING
    # ========================================================================

    async def build_context(
        self,
        bag_tag: str,
        agent_name: Optional[str] = None
    ) -> AgentContext:
        """
        Build rich context for a bag.

        Args:
            bag_tag: Bag tag
            agent_name: Optional agent name

        Returns:
            Complete context with all memory layers
        """

        return await self.context_builder.build_context_for_bag(
            bag_tag,
            agent_name,
            include_similar_cases=True,
            include_patterns=True,
            include_strategies=True
        )

    # ========================================================================
    # QUERIES
    # ========================================================================

    async def query_similar_risk_factors(
        self,
        bag_tag: str,
        risk_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query: Have we seen bags with similar risk factors?"""
        return await self.context_builder.has_similar_risk_factors(bag_tag, risk_features)

    async def query_successful_strategies(
        self,
        exception_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query: What strategies worked for similar exceptions?"""
        return await self.context_builder.what_worked_for_similar_bags(exception_type, context)

    async def query_agent_performance(
        self,
        agent_name: str
    ) -> Dict[str, Any]:
        """Query: How well has this agent performed?"""
        return await self.context_builder.get_agent_track_record(agent_name)

    # ========================================================================
    # STATISTICS
    # ========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""

        stats = {
            "working_memory": await self.working_memory.get_stats(),
            "episodic_memory": await self.episodic_memory.get_stats(),
            "semantic_memory": await self.semantic_memory.get_stats(),
            "learning": await self.learning_engine.get_feedback_summary()
        }

        return stats
