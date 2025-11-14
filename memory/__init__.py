"""
Agent Memory System
===================

Multi-layer memory architecture for intelligent agents.

Layers:
1. Working Memory (Redis): Current state, recent decisions
2. Episodic Memory (Neo4j): Complete journey history
3. Semantic Memory (Vector DB): Learned patterns and strategies

Usage:
    from memory import AgentMemory

    memory = AgentMemory()
    await memory.connect()

    # Remember an event
    await memory.remember(event_type, bag_tag, agent_name, context)

    # Recall similar situations
    similar = await memory.find_similar(bag_tag)

    # Build rich context
    context = await memory.build_context(bag_tag)

    # Learn from outcome
    await memory.learn_from_outcome(outcome)

Version: 1.0.0
Date: 2025-11-14
"""

from memory.agent_memory import AgentMemory
from memory.working_memory import WorkingMemory
from memory.episodic_memory import EpisodicMemory
from memory.semantic_memory import SemanticMemory
from memory.context_builder import ContextBuilder
from memory.learning_engine import LearningEngine

__all__ = [
    "AgentMemory",
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "ContextBuilder",
    "LearningEngine"
]
