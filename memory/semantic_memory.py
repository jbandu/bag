"""
Semantic Memory Layer
=====================

Layer 3: Learned patterns and strategies using Vector Database.

Stores:
- Learned patterns from past exceptions
- Successful resolution strategies
- Common failure modes
- Contextual knowledge for similar situations

Enables:
- Finding bags with similar risk characteristics
- Finding strategies that worked in similar contexts
- Learning from past outcomes
- Semantic search ("bags like this one")

Version: 1.0.0
Date: 2025-11-14
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import hashlib
from loguru import logger

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    logger.warning("NumPy not available")
    NUMPY_AVAILABLE = False
    # Create placeholder for type hints
    class np:
        ndarray = Any


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class LearnedPattern:
    """A learned pattern from past experiences"""
    pattern_id: str
    pattern_type: str  # risk, exception, resolution, etc.
    description: str
    features: Dict[str, Any]
    occurrences: int
    success_rate: float
    confidence: float
    examples: List[str]  # Bag tags
    learned_at: str
    last_updated: str


@dataclass
class ResolutionStrategy:
    """A strategy for resolving exceptions"""
    strategy_id: str
    exception_type: str
    strategy_name: str
    description: str
    steps: List[str]
    success_count: int
    failure_count: int
    success_rate: float
    avg_duration_ms: float
    avg_cost_usd: float
    confidence: float
    applicable_contexts: List[str]
    created_at: str
    last_used: Optional[str]


@dataclass
class SimilarCase:
    """A similar case from the past"""
    bag_tag: str
    similarity_score: float
    features: Dict[str, Any]
    outcome: str
    resolution_strategy: Optional[str]
    duration_ms: float
    cost_usd: float


# ============================================================================
# SEMANTIC MEMORY
# ============================================================================

class SemanticMemory:
    """
    Long-term semantic memory using vector embeddings.

    Enables semantic search and pattern learning.
    """

    def __init__(self, embedding_dim: int = 128):
        """Initialize semantic memory"""
        self.embedding_dim = embedding_dim

        # In-memory storage (in production, use Pinecone/Weaviate/Qdrant)
        self.patterns: Dict[str, LearnedPattern] = {}
        self.strategies: Dict[str, ResolutionStrategy] = {}
        self.embeddings: Dict[str, np.ndarray] = {}  # ID -> embedding
        self.metadata: Dict[str, Dict[str, Any]] = {}  # ID -> metadata

        logger.info("SemanticMemory initialized")

    # ========================================================================
    # EMBEDDINGS
    # ========================================================================

    def _create_embedding(self, features: Dict[str, Any]) -> np.ndarray:
        """
        Create embedding vector from features.

        In production, use a pre-trained model or sentence transformers.
        For demo, use feature hashing.
        """
        if not NUMPY_AVAILABLE:
            return None

        # Simple feature hashing for demo
        feature_str = json.dumps(features, sort_keys=True)
        hash_bytes = hashlib.sha256(feature_str.encode()).digest()

        # Convert to float array
        embedding = np.frombuffer(hash_bytes[:self.embedding_dim * 4], dtype=np.float32)

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        if vec1 is None or vec2 is None:
            return 0.0

        dot_product = np.dot(vec1, vec2)
        return float(dot_product)  # Already normalized

    # ========================================================================
    # PATTERN LEARNING
    # ========================================================================

    async def learn_pattern(self, pattern: LearnedPattern):
        """
        Learn a new pattern from observations.

        Args:
            pattern: Pattern to learn
        """
        # Create embedding from features
        embedding = self._create_embedding(pattern.features)

        # Store pattern
        self.patterns[pattern.pattern_id] = pattern
        if embedding is not None:
            self.embeddings[pattern.pattern_id] = embedding
        self.metadata[pattern.pattern_id] = {
            "type": "pattern",
            "pattern_type": pattern.pattern_type,
            "features": pattern.features
        }

        logger.info(f"Learned pattern: {pattern.pattern_id} ({pattern.pattern_type})")

    async def find_similar_patterns(
        self,
        features: Dict[str, Any],
        pattern_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Tuple[LearnedPattern, float]]:
        """
        Find similar patterns based on features.

        Args:
            features: Feature set to match
            pattern_type: Optional filter by pattern type
            top_k: Number of results to return

        Returns:
            List of (pattern, similarity_score) tuples
        """

        query_embedding = self._create_embedding(features)
        if query_embedding is None:
            return []

        # Calculate similarities
        similarities = []
        for pattern_id, pattern in self.patterns.items():
            # Filter by type if specified
            if pattern_type and pattern.pattern_type != pattern_type:
                continue

            pattern_embedding = self.embeddings.get(pattern_id)
            if pattern_embedding is not None:
                similarity = self._cosine_similarity(query_embedding, pattern_embedding)
                similarities.append((pattern, similarity))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    async def update_pattern(
        self,
        pattern_id: str,
        new_example: str,
        success: bool
    ):
        """
        Update a pattern with new evidence.

        Args:
            pattern_id: Pattern to update
            new_example: New example (bag tag)
            success: Whether this instance was successful
        """

        if pattern_id not in self.patterns:
            logger.warning(f"Pattern {pattern_id} not found")
            return

        pattern = self.patterns[pattern_id]

        # Update occurrences
        pattern.occurrences += 1

        # Update success rate
        total_successes = pattern.success_rate * (pattern.occurrences - 1)
        if success:
            total_successes += 1

        pattern.success_rate = total_successes / pattern.occurrences

        # Add example
        if new_example not in pattern.examples:
            pattern.examples.append(new_example)

        # Update confidence (more occurrences = higher confidence)
        pattern.confidence = min(1.0, pattern.occurrences / 100.0)

        pattern.last_updated = datetime.now().isoformat()

        logger.debug(f"Updated pattern {pattern_id}: {pattern.occurrences} occurrences, {pattern.success_rate:.1%} success")

    # ========================================================================
    # RESOLUTION STRATEGIES
    # ========================================================================

    async def learn_strategy(self, strategy: ResolutionStrategy):
        """
        Learn a new resolution strategy.

        Args:
            strategy: Strategy to learn
        """

        self.strategies[strategy.strategy_id] = strategy

        # Create embedding from strategy description + steps
        features = {
            "exception_type": strategy.exception_type,
            "description": strategy.description,
            "steps": " ".join(strategy.steps)
        }

        embedding = self._create_embedding(features)
        if embedding is not None:
            self.embeddings[strategy.strategy_id] = embedding

        self.metadata[strategy.strategy_id] = {
            "type": "strategy",
            "exception_type": strategy.exception_type,
            "success_rate": strategy.success_rate
        }

        logger.info(f"Learned strategy: {strategy.strategy_id} for {strategy.exception_type}")

    async def find_strategies(
        self,
        exception_type: str,
        context: Dict[str, Any],
        min_success_rate: float = 0.7,
        top_k: int = 3
    ) -> List[Tuple[ResolutionStrategy, float]]:
        """
        Find strategies for an exception type and context.

        Args:
            exception_type: Type of exception
            context: Current context
            min_success_rate: Minimum success rate filter
            top_k: Number of strategies to return

        Returns:
            List of (strategy, relevance_score) tuples
        """

        query_embedding = self._create_embedding(context)
        if query_embedding is None:
            # Fallback to simple filtering
            matching = [
                (s, s.success_rate) for s in self.strategies.values()
                if s.exception_type == exception_type and s.success_rate >= min_success_rate
            ]
            matching.sort(key=lambda x: x[1], reverse=True)
            return matching[:top_k]

        # Find similar strategies
        candidates = []
        for strategy_id, strategy in self.strategies.items():
            # Filter by exception type and success rate
            if strategy.exception_type != exception_type:
                continue
            if strategy.success_rate < min_success_rate:
                continue

            # Calculate relevance
            strategy_embedding = self.embeddings.get(strategy_id)
            if strategy_embedding is not None:
                similarity = self._cosine_similarity(query_embedding, strategy_embedding)

                # Combine similarity with success rate
                relevance = (similarity * 0.6) + (strategy.success_rate * 0.4)

                candidates.append((strategy, relevance))

        # Sort by relevance
        candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates[:top_k]

    async def update_strategy(
        self,
        strategy_id: str,
        success: bool,
        duration_ms: float,
        cost_usd: float
    ):
        """
        Update strategy with outcome.

        Args:
            strategy_id: Strategy to update
            success: Whether it succeeded
            duration_ms: Duration taken
            cost_usd: Cost incurred
        """

        if strategy_id not in self.strategies:
            logger.warning(f"Strategy {strategy_id} not found")
            return

        strategy = self.strategies[strategy_id]

        # Update counts
        if success:
            strategy.success_count += 1
        else:
            strategy.failure_count += 1

        total = strategy.success_count + strategy.failure_count
        strategy.success_rate = strategy.success_count / total if total > 0 else 0.0

        # Update averages
        total_uses = strategy.success_count + strategy.failure_count
        strategy.avg_duration_ms = (
            (strategy.avg_duration_ms * (total_uses - 1) + duration_ms) / total_uses
        )
        strategy.avg_cost_usd = (
            (strategy.avg_cost_usd * (total_uses - 1) + cost_usd) / total_uses
        )

        # Update confidence
        strategy.confidence = min(1.0, total_uses / 50.0)

        strategy.last_used = datetime.now().isoformat()

        logger.debug(
            f"Updated strategy {strategy_id}: "
            f"{strategy.success_rate:.1%} success over {total} uses"
        )

    # ========================================================================
    # SIMILARITY SEARCH
    # ========================================================================

    async def find_similar_cases(
        self,
        features: Dict[str, Any],
        top_k: int = 5
    ) -> List[SimilarCase]:
        """
        Find similar cases from the past.

        Args:
            features: Feature set describing current case
            top_k: Number of similar cases to return

        Returns:
            List of similar cases with similarity scores
        """

        query_embedding = self._create_embedding(features)
        if query_embedding is None:
            return []

        similar_cases = []

        # Search through all stored embeddings
        for item_id, embedding in self.embeddings.items():
            metadata = self.metadata.get(item_id, {})

            # Only look at historical case embeddings (would be stored separately)
            if metadata.get("type") != "case":
                continue

            similarity = self._cosine_similarity(query_embedding, embedding)

            similar_cases.append(SimilarCase(
                bag_tag=metadata.get("bag_tag", "unknown"),
                similarity_score=similarity,
                features=metadata.get("features", {}),
                outcome=metadata.get("outcome", "unknown"),
                resolution_strategy=metadata.get("resolution_strategy"),
                duration_ms=metadata.get("duration_ms", 0.0),
                cost_usd=metadata.get("cost_usd", 0.0)
            ))

        # Sort by similarity
        similar_cases.sort(key=lambda c: c.similarity_score, reverse=True)

        return similar_cases[:top_k]

    async def store_case(
        self,
        bag_tag: str,
        features: Dict[str, Any],
        outcome: str,
        resolution_strategy: Optional[str],
        duration_ms: float,
        cost_usd: float
    ):
        """
        Store a completed case for future similarity search.

        Args:
            bag_tag: Bag tag
            features: Feature set
            outcome: Outcome (success/failure)
            resolution_strategy: Strategy used
            duration_ms: Duration
            cost_usd: Cost
        """

        case_id = f"case:{bag_tag}"

        # Create embedding
        embedding = self._create_embedding(features)
        if embedding is not None:
            self.embeddings[case_id] = embedding

        # Store metadata
        self.metadata[case_id] = {
            "type": "case",
            "bag_tag": bag_tag,
            "features": features,
            "outcome": outcome,
            "resolution_strategy": resolution_strategy,
            "duration_ms": duration_ms,
            "cost_usd": cost_usd,
            "stored_at": datetime.now().isoformat()
        }

        logger.debug(f"Stored case: {bag_tag}")

    # ========================================================================
    # CONTEXT BUILDING
    # ========================================================================

    async def build_context_for_bag(
        self,
        bag_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build rich context for a bag by finding similar cases and patterns.

        Args:
            bag_features: Features of current bag

        Returns:
            Context dictionary with similar cases, patterns, and strategies
        """

        context = {
            "similar_cases": [],
            "relevant_patterns": [],
            "recommended_strategies": []
        }

        # Find similar cases
        similar_cases = await self.find_similar_cases(bag_features, top_k=5)
        context["similar_cases"] = [
            {
                "bag_tag": case.bag_tag,
                "similarity": case.similarity_score,
                "outcome": case.outcome,
                "resolution": case.resolution_strategy,
                "duration_ms": case.duration_ms,
                "cost_usd": case.cost_usd
            }
            for case in similar_cases
        ]

        # Find relevant patterns
        patterns = await self.find_similar_patterns(bag_features, top_k=3)
        context["relevant_patterns"] = [
            {
                "pattern_type": pattern.pattern_type,
                "description": pattern.description,
                "similarity": similarity,
                "success_rate": pattern.success_rate,
                "confidence": pattern.confidence
            }
            for pattern, similarity in patterns
        ]

        return context

    # ========================================================================
    # STATISTICS
    # ========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get semantic memory statistics"""

        total_strategies = len(self.strategies)
        avg_success_rate = (
            sum(s.success_rate for s in self.strategies.values()) / total_strategies
            if total_strategies > 0 else 0.0
        )

        return {
            "total_patterns": len(self.patterns),
            "total_strategies": total_strategies,
            "total_embeddings": len(self.embeddings),
            "avg_strategy_success_rate": avg_success_rate,
            "embedding_dim": self.embedding_dim
        }
