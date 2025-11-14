"""
Episodic Memory Layer
=====================

Layer 2: Long-term episodic memory using Neo4j knowledge graph.

Stores:
- Complete journey of each bag
- All events and decisions
- Agent interactions and handoffs
- Workflow executions and outcomes
- Temporal relationships

Enables querying:
- "Show me the complete journey of bag X"
- "What decisions were made for this bag?"
- "Which agents worked on this bag?"
- "What was the outcome?"

Version: 1.0.0
Date: 2025-11-14
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from loguru import logger

try:
    from neo4j import AsyncGraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    logger.warning("Neo4j driver not available - using mock implementation")
    NEO4J_AVAILABLE = False


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class BagJourneyEvent:
    """Single event in a bag's journey"""
    event_id: str
    bag_tag: str
    event_type: str  # scan, decision, workflow_start, workflow_end, etc.
    timestamp: str
    location: Optional[str]
    agent_name: Optional[str]
    data: Dict[str, Any]
    outcome: Optional[str]


@dataclass
class AgentInteraction:
    """Interaction between agents"""
    interaction_id: str
    from_agent: str
    to_agent: str
    interaction_type: str  # handoff, collaboration, escalation
    bag_tag: str
    context: Dict[str, Any]
    timestamp: str


@dataclass
class WorkflowExecution:
    """Complete workflow execution record"""
    workflow_id: str
    workflow_type: str
    bag_tag: str
    status: str
    started_at: str
    completed_at: Optional[str]
    duration_ms: Optional[float]
    steps_executed: List[str]
    decisions_made: List[str]
    agents_involved: List[str]
    outcome: Optional[str]
    cost_usd: float


# ============================================================================
# EPISODIC MEMORY
# ============================================================================

class EpisodicMemory:
    """
    Long-term episodic memory using Neo4j knowledge graph.

    Stores complete history and enables temporal queries.
    """

    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password"):
        """Initialize episodic memory"""
        self.neo4j_uri = neo4j_uri
        self.user = user
        self.password = password
        self.driver = None

        # Mock storage for fallback
        self.mock_nodes: Dict[str, Any] = {}
        self.mock_relationships: List[Dict[str, Any]] = []

        logger.info("EpisodicMemory initialized")

    async def connect(self):
        """Connect to Neo4j"""
        if NEO4J_AVAILABLE:
            try:
                self.driver = AsyncGraphDatabase.driver(
                    self.neo4j_uri,
                    auth=(self.user, self.password)
                )
                # Test connection
                async with self.driver.session() as session:
                    await session.run("RETURN 1")
                logger.info("Connected to Neo4j")
            except Exception as e:
                logger.warning(f"Neo4j connection failed: {e}, using mock")
                self.driver = None
        else:
            logger.info("Using mock implementation for episodic memory")

    async def disconnect(self):
        """Disconnect from Neo4j"""
        if self.driver:
            await self.driver.close()
            logger.info("Disconnected from Neo4j")

    # ========================================================================
    # BAG JOURNEY
    # ========================================================================

    async def record_event(self, event: BagJourneyEvent):
        """
        Record an event in a bag's journey.

        Creates nodes and relationships in knowledge graph.
        """

        if self.driver:
            query = """
            MERGE (b:Bag {bag_tag: $bag_tag})
            CREATE (e:Event {
                event_id: $event_id,
                event_type: $event_type,
                timestamp: $timestamp,
                location: $location,
                agent_name: $agent_name,
                outcome: $outcome
            })
            SET e.data = $data
            CREATE (b)-[:HAD_EVENT {at: $timestamp}]->(e)

            // Link to agent if present
            WITH e
            WHERE $agent_name IS NOT NULL
            MERGE (a:Agent {name: $agent_name})
            CREATE (a)-[:PERFORMED]->(e)
            """

            async with self.driver.session() as session:
                await session.run(
                    query,
                    bag_tag=event.bag_tag,
                    event_id=event.event_id,
                    event_type=event.event_type,
                    timestamp=event.timestamp,
                    location=event.location,
                    agent_name=event.agent_name,
                    outcome=event.outcome,
                    data=event.data
                )
        else:
            # Mock implementation
            self.mock_nodes[event.event_id] = {
                "type": "Event",
                "data": event
            }
            self.mock_relationships.append({
                "from": event.bag_tag,
                "to": event.event_id,
                "type": "HAD_EVENT"
            })

        logger.debug(f"Recorded event {event.event_id} for bag {event.bag_tag}")

    async def get_bag_journey(self, bag_tag: str) -> List[BagJourneyEvent]:
        """
        Get complete journey of a bag.

        Returns all events in chronological order.
        """

        if self.driver:
            query = """
            MATCH (b:Bag {bag_tag: $bag_tag})-[r:HAD_EVENT]->(e:Event)
            RETURN e
            ORDER BY e.timestamp ASC
            """

            async with self.driver.session() as session:
                result = await session.run(query, bag_tag=bag_tag)
                records = await result.data()

                events = []
                for record in records:
                    event_data = record["e"]
                    events.append(BagJourneyEvent(
                        event_id=event_data["event_id"],
                        bag_tag=bag_tag,
                        event_type=event_data["event_type"],
                        timestamp=event_data["timestamp"],
                        location=event_data.get("location"),
                        agent_name=event_data.get("agent_name"),
                        data=event_data.get("data", {}),
                        outcome=event_data.get("outcome")
                    ))

                return events
        else:
            # Mock implementation
            events = [
                node["data"] for node in self.mock_nodes.values()
                if node["type"] == "Event" and node["data"].bag_tag == bag_tag
            ]
            return sorted(events, key=lambda e: e.timestamp)

    async def get_bags_by_pattern(self, pattern: Dict[str, Any]) -> List[str]:
        """
        Find bags matching a pattern.

        Example: Find all bags that went through LAX and had high risk
        """

        if self.driver:
            # Build dynamic query based on pattern
            conditions = []
            params = {}

            if "location" in pattern:
                conditions.append("e.location = $location")
                params["location"] = pattern["location"]

            if "event_type" in pattern:
                conditions.append("e.event_type = $event_type")
                params["event_type"] = pattern["event_type"]

            where_clause = " AND ".join(conditions) if conditions else "true"

            query = f"""
            MATCH (b:Bag)-[:HAD_EVENT]->(e:Event)
            WHERE {where_clause}
            RETURN DISTINCT b.bag_tag AS bag_tag
            """

            async with self.driver.session() as session:
                result = await session.run(query, **params)
                records = await result.data()
                return [record["bag_tag"] for record in records]
        else:
            # Mock implementation
            matching_bags = set()
            for rel in self.mock_relationships:
                if rel["type"] == "HAD_EVENT":
                    event_node = self.mock_nodes.get(rel["to"])
                    if event_node and event_node["type"] == "Event":
                        event = event_node["data"]
                        matches = all(
                            getattr(event, key, None) == value
                            for key, value in pattern.items()
                        )
                        if matches:
                            matching_bags.add(rel["from"])

            return list(matching_bags)

    # ========================================================================
    # AGENT INTERACTIONS
    # ========================================================================

    async def record_interaction(self, interaction: AgentInteraction):
        """Record interaction between agents"""

        if self.driver:
            query = """
            MERGE (a1:Agent {name: $from_agent})
            MERGE (a2:Agent {name: $to_agent})
            CREATE (a1)-[i:INTERACTED_WITH {
                interaction_id: $interaction_id,
                type: $interaction_type,
                bag_tag: $bag_tag,
                timestamp: $timestamp
            }]->(a2)
            SET i.context = $context
            """

            async with self.driver.session() as session:
                await session.run(
                    query,
                    from_agent=interaction.from_agent,
                    to_agent=interaction.to_agent,
                    interaction_id=interaction.interaction_id,
                    interaction_type=interaction.interaction_type,
                    bag_tag=interaction.bag_tag,
                    timestamp=interaction.timestamp,
                    context=interaction.context
                )
        else:
            # Mock implementation
            self.mock_relationships.append({
                "from": interaction.from_agent,
                "to": interaction.to_agent,
                "type": "INTERACTED_WITH",
                "data": interaction
            })

        logger.debug(f"Recorded interaction: {interaction.from_agent} → {interaction.to_agent}")

    async def get_agent_interactions(self, agent_name: str, limit: int = 10) -> List[AgentInteraction]:
        """Get recent interactions for an agent"""

        if self.driver:
            query = """
            MATCH (a:Agent {name: $agent_name})-[i:INTERACTED_WITH]->(a2:Agent)
            RETURN i, a2.name AS to_agent
            ORDER BY i.timestamp DESC
            LIMIT $limit
            """

            async with self.driver.session() as session:
                result = await session.run(query, agent_name=agent_name, limit=limit)
                records = await result.data()

                interactions = []
                for record in records:
                    i_data = record["i"]
                    interactions.append(AgentInteraction(
                        interaction_id=i_data["interaction_id"],
                        from_agent=agent_name,
                        to_agent=record["to_agent"],
                        interaction_type=i_data["type"],
                        bag_tag=i_data["bag_tag"],
                        context=i_data.get("context", {}),
                        timestamp=i_data["timestamp"]
                    ))

                return interactions
        else:
            # Mock implementation
            interactions = [
                rel["data"] for rel in self.mock_relationships
                if rel["type"] == "INTERACTED_WITH" and rel["from"] == agent_name
            ]
            return sorted(interactions, key=lambda i: i.timestamp, reverse=True)[:limit]

    # ========================================================================
    # WORKFLOW EXECUTIONS
    # ========================================================================

    async def record_workflow(self, workflow: WorkflowExecution):
        """Record complete workflow execution"""

        if self.driver:
            query = """
            MERGE (b:Bag {bag_tag: $bag_tag})
            CREATE (w:Workflow {
                workflow_id: $workflow_id,
                workflow_type: $workflow_type,
                status: $status,
                started_at: $started_at,
                completed_at: $completed_at,
                duration_ms: $duration_ms,
                outcome: $outcome,
                cost_usd: $cost_usd
            })
            SET w.steps_executed = $steps_executed,
                w.decisions_made = $decisions_made,
                w.agents_involved = $agents_involved
            CREATE (b)-[:EXECUTED_WORKFLOW]->(w)

            // Link to agents
            WITH w
            UNWIND $agents_involved AS agent_name
            MERGE (a:Agent {name: agent_name})
            CREATE (a)-[:PARTICIPATED_IN]->(w)
            """

            async with self.driver.session() as session:
                await session.run(
                    query,
                    bag_tag=workflow.bag_tag,
                    workflow_id=workflow.workflow_id,
                    workflow_type=workflow.workflow_type,
                    status=workflow.status,
                    started_at=workflow.started_at,
                    completed_at=workflow.completed_at,
                    duration_ms=workflow.duration_ms,
                    outcome=workflow.outcome,
                    cost_usd=workflow.cost_usd,
                    steps_executed=workflow.steps_executed,
                    decisions_made=workflow.decisions_made,
                    agents_involved=workflow.agents_involved
                )
        else:
            # Mock implementation
            self.mock_nodes[workflow.workflow_id] = {
                "type": "Workflow",
                "data": workflow
            }
            self.mock_relationships.append({
                "from": workflow.bag_tag,
                "to": workflow.workflow_id,
                "type": "EXECUTED_WORKFLOW"
            })

        logger.debug(f"Recorded workflow {workflow.workflow_id}")

    async def get_workflows_for_bag(self, bag_tag: str) -> List[WorkflowExecution]:
        """Get all workflows executed for a bag"""

        if self.driver:
            query = """
            MATCH (b:Bag {bag_tag: $bag_tag})-[:EXECUTED_WORKFLOW]->(w:Workflow)
            RETURN w
            ORDER BY w.started_at DESC
            """

            async with self.driver.session() as session:
                result = await session.run(query, bag_tag=bag_tag)
                records = await result.data()

                workflows = []
                for record in records:
                    w_data = record["w"]
                    workflows.append(WorkflowExecution(
                        workflow_id=w_data["workflow_id"],
                        workflow_type=w_data["workflow_type"],
                        bag_tag=bag_tag,
                        status=w_data["status"],
                        started_at=w_data["started_at"],
                        completed_at=w_data.get("completed_at"),
                        duration_ms=w_data.get("duration_ms"),
                        steps_executed=w_data.get("steps_executed", []),
                        decisions_made=w_data.get("decisions_made", []),
                        agents_involved=w_data.get("agents_involved", []),
                        outcome=w_data.get("outcome"),
                        cost_usd=w_data.get("cost_usd", 0.0)
                    ))

                return workflows
        else:
            # Mock implementation
            workflows = [
                node["data"] for node in self.mock_nodes.values()
                if node["type"] == "Workflow" and node["data"].bag_tag == bag_tag
            ]
            return sorted(workflows, key=lambda w: w.started_at, reverse=True)

    # ========================================================================
    # ANALYTICS
    # ========================================================================

    async def get_agent_performance(self, agent_name: str) -> Dict[str, Any]:
        """Get performance metrics for an agent"""

        if self.driver:
            query = """
            MATCH (a:Agent {name: $agent_name})-[:PERFORMED]->(e:Event)
            RETURN
                count(e) AS total_events,
                count(CASE WHEN e.outcome = 'success' THEN 1 END) AS successful_events,
                avg(CASE WHEN e.outcome = 'success' THEN 1.0 ELSE 0.0 END) AS success_rate
            """

            async with self.driver.session() as session:
                result = await session.run(query, agent_name=agent_name)
                record = await result.single()

                if record:
                    return {
                        "agent_name": agent_name,
                        "total_events": record["total_events"],
                        "successful_events": record["successful_events"],
                        "success_rate": record["success_rate"] or 0.0
                    }

        return {
            "agent_name": agent_name,
            "total_events": 0,
            "successful_events": 0,
            "success_rate": 0.0
        }

    async def find_similar_journeys(
        self,
        bag_tag: str,
        similarity_threshold: float = 0.7
    ) -> List[str]:
        """
        Find bags with similar journeys.

        Uses event sequence similarity.
        """

        # Get the journey pattern for the target bag
        journey = await self.get_bag_journey(bag_tag)
        event_types = [e.event_type for e in journey]

        if not event_types:
            return []

        if self.driver:
            # Find bags with similar event sequences
            query = """
            MATCH (b:Bag)-[:HAD_EVENT]->(e:Event)
            WHERE b.bag_tag <> $bag_tag
            WITH b, collect(e.event_type) AS event_sequence
            RETURN b.bag_tag AS bag_tag, event_sequence
            """

            async with self.driver.session() as session:
                result = await session.run(query, bag_tag=bag_tag)
                records = await result.data()

                similar_bags = []
                for record in records:
                    other_sequence = record["event_sequence"]
                    similarity = self._calculate_sequence_similarity(event_types, other_sequence)

                    if similarity >= similarity_threshold:
                        similar_bags.append((record["bag_tag"], similarity))

                # Sort by similarity descending
                similar_bags.sort(key=lambda x: x[1], reverse=True)

                return [bag for bag, _ in similar_bags[:10]]

        return []

    def _calculate_sequence_similarity(self, seq1: List[str], seq2: List[str]) -> float:
        """Calculate similarity between two event sequences"""
        if not seq1 or not seq2:
            return 0.0

        # Simple Jaccard similarity
        set1 = set(seq1)
        set2 = set(seq2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    # ========================================================================
    # STATISTICS
    # ========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get episodic memory statistics"""

        if self.driver:
            query = """
            MATCH (n)
            RETURN
                count(DISTINCT CASE WHEN 'Bag' IN labels(n) THEN n END) AS total_bags,
                count(DISTINCT CASE WHEN 'Event' IN labels(n) THEN n END) AS total_events,
                count(DISTINCT CASE WHEN 'Workflow' IN labels(n) THEN n END) AS total_workflows,
                count(DISTINCT CASE WHEN 'Agent' IN labels(n) THEN n END) AS total_agents
            """

            async with self.driver.session() as session:
                result = await session.run(query)
                record = await result.single()

                if record:
                    return {
                        "using_neo4j": True,
                        "total_bags": record["total_bags"],
                        "total_events": record["total_events"],
                        "total_workflows": record["total_workflows"],
                        "total_agents": record["total_agents"]
                    }

        return {
            "using_neo4j": False,
            "total_nodes": len(self.mock_nodes),
            "total_relationships": len(self.mock_relationships)
        }
