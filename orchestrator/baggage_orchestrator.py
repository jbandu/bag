"""
Baggage Orchestrator
====================

LangGraph-based semantic agent orchestration for baggage handling workflows.

Coordinates 8 specialized agents in complex workflows with:
- Parallel execution (concurrent operations)
- Conditional routing (decision-based paths)
- Loop/retry logic (fault tolerance)
- Human-in-the-loop (approval gates)
- Error handling & rollback
- Semantic annotations (why decisions were made)

Version: 1.0.0
Date: 2025-11-14
"""

from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from loguru import logger
import uuid
import time
import asyncio

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    logger.warning("LangGraph not installed - using mock implementation")
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = "END"

from orchestrator.workflow_state import (
    BaggageWorkflowState,
    WorkflowStatus,
    create_workflow_state,
    update_workflow_status,
    check_rollback_needed
)

from orchestrator.workflow_nodes import (
    assess_risk_node,
    create_case_node,
    check_pir_node,
    request_approval_node,
    dispatch_courier_node,
    notify_passenger_node,
    update_twin_node,
    log_workflow_node,
    error_handler_node
)

from orchestrator.workflow_edges import (
    route_after_risk_assessment,
    route_after_parallel_checks,
    route_after_approval,
    route_after_courier_dispatch,
    route_to_finalization,
    should_rollback,
    is_workflow_complete,
    calculate_workflow_success_rate
)


# ============================================================================
# MOCK LANGGRAPH IMPLEMENTATION (if not installed)
# ============================================================================

class MockStateGraph:
    """Mock StateGraph for when LangGraph is not installed"""

    def __init__(self, state_schema):
        self.state_schema = state_schema
        self.nodes: Dict[str, Callable] = {}
        self.edges: List[tuple] = []
        self.conditional_edges: List[tuple] = []
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, func: Callable):
        """Add a node to the graph"""
        self.nodes[name] = func

    def add_edge(self, from_node: str, to_node: str):
        """Add a direct edge"""
        self.edges.append((from_node, to_node))

    def add_conditional_edges(self, from_node: str, condition_func: Callable, path_map: Optional[Dict] = None):
        """Add conditional edges"""
        self.conditional_edges.append((from_node, condition_func, path_map))

    def set_entry_point(self, node: str):
        """Set the entry point"""
        self.entry_point = node

    def compile(self):
        """Compile the graph - returns self for mock"""
        return self

    def invoke(self, state: Dict) -> Dict:
        """Execute the graph (simplified mock execution)"""
        logger.info("[MockStateGraph] Executing workflow (simplified)")

        current_node = self.entry_point
        max_steps = 50  # Prevent infinite loops

        for step_num in range(max_steps):
            if current_node == END or current_node is None:
                break

            # Execute current node
            if current_node in self.nodes:
                logger.info(f"[MockStateGraph] Executing node: {current_node}")
                state = self.nodes[current_node](state)

            # Find next node
            next_node = None

            # Check conditional edges first
            for from_node, condition_func, path_map in self.conditional_edges:
                if from_node == current_node:
                    condition_result = condition_func(state)
                    if path_map and condition_result in path_map:
                        next_node = path_map[condition_result]
                    else:
                        next_node = condition_result
                    break

            # Check direct edges
            if not next_node:
                for from_node, to_node in self.edges:
                    if from_node == current_node:
                        next_node = to_node
                        break

            current_node = next_node

        return state


if not LANGGRAPH_AVAILABLE:
    StateGraph = MockStateGraph


# ============================================================================
# BAGGAGE ORCHESTRATOR
# ============================================================================

class BaggageOrchestrator:
    """
    Semantic agent orchestrator using LangGraph.

    Coordinates complex multi-agent workflows with semantic reasoning.
    """

    def __init__(self):
        """Initialize orchestrator"""

        self.workflows: Dict[str, Any] = {}  # Compiled workflow graphs
        self.execution_history: List[Dict[str, Any]] = []

        # Statistics
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.start_time = datetime.now()

        logger.info("BaggageOrchestrator initialized")

    def register_workflow(self, workflow_type: str, workflow_graph: Any):
        """
        Register a workflow template.

        Args:
            workflow_type: Type of workflow (high_risk, transfer, irrops, etc.)
            workflow_graph: Compiled LangGraph StateGraph
        """
        self.workflows[workflow_type] = workflow_graph
        logger.info(f"Registered workflow: {workflow_type}")

    def execute_workflow(
        self,
        workflow_type: str,
        bag_tag: str,
        context: Optional[Dict[str, Any]] = None,
        triggered_by: str = "system"
    ) -> BaggageWorkflowState:
        """
        Execute a workflow.

        Args:
            workflow_type: Type of workflow to execute
            bag_tag: Bag tag number
            context: Additional context data
            triggered_by: Who/what triggered this workflow

        Returns:
            Final workflow state
        """

        if workflow_type not in self.workflows:
            raise ValueError(f"Workflow type '{workflow_type}' not registered")

        workflow_id = f"WF{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"

        logger.info(f"Starting workflow: {workflow_id} (type: {workflow_type}, bag: {bag_tag})")

        # Create initial state
        initial_state = create_workflow_state(
            workflow_id=workflow_id,
            bag_tag=bag_tag,
            workflow_type=workflow_type,
            triggered_by=triggered_by,
            trigger_reason=context.get("trigger_reason", "Automated trigger") if context else "Automated trigger",
            context=context
        )

        # Update status to in progress
        update_workflow_status(initial_state, WorkflowStatus.IN_PROGRESS)

        start_time = time.time()
        self.total_executions += 1

        try:
            # Execute workflow graph
            workflow_graph = self.workflows[workflow_type]
            final_state = workflow_graph.invoke(initial_state)

            # Check if successful
            if len(final_state.get("errors", [])) == 0:
                update_workflow_status(final_state, WorkflowStatus.COMPLETED)
                self.successful_executions += 1
                logger.info(f"Workflow {workflow_id} COMPLETED successfully")
            else:
                update_workflow_status(final_state, WorkflowStatus.FAILED)
                self.failed_executions += 1
                logger.error(f"Workflow {workflow_id} FAILED with errors: {final_state['errors']}")

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            final_state["metadata"].duration_ms = duration_ms

            # Record execution
            self.execution_history.append({
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "bag_tag": bag_tag,
                "status": final_state["metadata"].status.value,
                "duration_ms": duration_ms,
                "steps_executed": len(final_state.get("workflow_history", [])),
                "success_rate": calculate_workflow_success_rate(final_state),
                "executed_at": datetime.now().isoformat()
            })

            return final_state

        except Exception as e:
            logger.error(f"Workflow {workflow_id} crashed: {e}")
            self.failed_executions += 1

            # Create error state
            initial_state["errors"].append(f"Workflow crash: {str(e)}")
            update_workflow_status(initial_state, WorkflowStatus.FAILED)

            return initial_state

    async def execute_workflow_async(
        self,
        workflow_type: str,
        bag_tag: str,
        context: Optional[Dict[str, Any]] = None,
        triggered_by: str = "system"
    ) -> BaggageWorkflowState:
        """
        Execute workflow asynchronously.

        Args:
            workflow_type: Type of workflow to execute
            bag_tag: Bag tag number
            context: Additional context data
            triggered_by: Who/what triggered this workflow

        Returns:
            Final workflow state
        """

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.execute_workflow,
            workflow_type,
            bag_tag,
            context,
            triggered_by
        )

        return result

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a workflow execution.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow status or None if not found
        """

        for execution in self.execution_history:
            if execution["workflow_id"] == workflow_id:
                return execution

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get orchestrator statistics.

        Returns:
            Statistics dictionary
        """

        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        success_rate = (
            self.successful_executions / self.total_executions
            if self.total_executions > 0 else 0.0
        )

        return {
            "uptime_seconds": uptime_seconds,
            "total_executions": self.total_executions,
            "successful": self.successful_executions,
            "failed": self.failed_executions,
            "success_rate": success_rate,
            "workflows_registered": len(self.workflows),
            "avg_duration_ms": (
                sum(e["duration_ms"] for e in self.execution_history) / len(self.execution_history)
                if self.execution_history else 0
            )
        }

    def get_workflow_history(
        self,
        workflow_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get workflow execution history.

        Args:
            workflow_type: Filter by workflow type (optional)
            limit: Maximum number of results

        Returns:
            List of workflow executions
        """

        history = self.execution_history

        if workflow_type:
            history = [e for e in history if e["workflow_type"] == workflow_type]

        return history[-limit:]


# ============================================================================
# WORKFLOW BUILDER HELPERS
# ============================================================================

def build_workflow_graph(
    workflow_type: str,
    nodes: Dict[str, Callable],
    edges: List[tuple],
    conditional_edges: List[tuple],
    entry_point: str
) -> Any:
    """
    Build a LangGraph workflow.

    Args:
        workflow_type: Type of workflow
        nodes: Dictionary of node name -> function
        edges: List of (from_node, to_node) tuples
        conditional_edges: List of (from_node, condition_func, path_map) tuples
        entry_point: Starting node

    Returns:
        Compiled LangGraph StateGraph
    """

    logger.info(f"Building workflow graph: {workflow_type}")

    # Create graph
    graph = StateGraph(BaggageWorkflowState)

    # Add nodes
    for node_name, node_func in nodes.items():
        graph.add_node(node_name, node_func)
        logger.debug(f"  Added node: {node_name}")

    # Add direct edges
    for from_node, to_node in edges:
        graph.add_edge(from_node, to_node)
        logger.debug(f"  Added edge: {from_node} → {to_node}")

    # Add conditional edges
    for from_node, condition_func, path_map in conditional_edges:
        graph.add_conditional_edges(from_node, condition_func, path_map)
        logger.debug(f"  Added conditional edge: {from_node} (condition)")

    # Set entry point
    graph.set_entry_point(entry_point)

    # Compile
    compiled_graph = graph.compile()

    logger.info(f"Workflow graph built: {workflow_type}")

    return compiled_graph


def create_simple_workflow(workflow_type: str, node_sequence: List[str]) -> Any:
    """
    Create a simple linear workflow.

    Args:
        workflow_type: Type of workflow
        node_sequence: List of node names in order

    Returns:
        Compiled workflow graph
    """

    # Map node names to functions
    node_map = {
        "assess_risk": assess_risk_node,
        "create_case": create_case_node,
        "check_pir": check_pir_node,
        "request_approval": request_approval_node,
        "dispatch_courier": dispatch_courier_node,
        "notify_passenger": notify_passenger_node,
        "update_twin": update_twin_node,
        "log_workflow": log_workflow_node,
        "error_handler": error_handler_node
    }

    nodes = {name: node_map[name] for name in node_sequence}

    # Create linear edges
    edges = [(node_sequence[i], node_sequence[i+1]) for i in range(len(node_sequence) - 1)]

    # Add final edge to END
    edges.append((node_sequence[-1], END))

    return build_workflow_graph(
        workflow_type=workflow_type,
        nodes=nodes,
        edges=edges,
        conditional_edges=[],
        entry_point=node_sequence[0]
    )
