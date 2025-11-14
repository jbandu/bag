// ============================================================================
// AGENT COLLABORATION KNOWLEDGE GRAPH - NEO4J SCHEMA
// ============================================================================
// Purpose: Define agent collaboration patterns, dependencies, and orchestration
// Version: 1.0.0
// Date: 2024-11-13
//
// Collaboration Patterns:
// 1. Sequential: A completes → B starts
// 2. Parallel: A and B run simultaneously → merge results
// 3. Conditional: A evaluates → routes to B or C
// 4. Loop: A → B → C → back to A with feedback
// 5. Approval: A requests → Human approves → B executes
// ============================================================================

// ============================================================================
// PART 1: AGENT NODE ENHANCEMENTS
// ============================================================================

// Add collaboration-specific properties to existing :Agent nodes
/*
Additional properties for :Agent:

// Capabilities
capabilities: [
  {
    capability_id: "predict_mishandling",
    name: "Predict Mishandling",
    confidence: 0.92,
    avg_execution_time_ms: 145,
    success_rate: 0.947
  }
]

// Orchestration Metadata
max_parallelism: 5,
avg_execution_time_ms: 145,
success_rate: 0.95,

// Retry Policy
retry_policy: {
  max_attempts: 3,
  backoff_strategy: "exponential",
  initial_delay_seconds: 2,
  max_delay_seconds: 60
}

// Health
health_status: "healthy",
last_health_check: datetime("2024-11-13T14:00:00Z")
*/

// ============================================================================
// PART 2: WORKFLOW ORCHESTRATION NODES
// ============================================================================

// ----------------------------------------------------------------------------
// :Workflow - Orchestration workflow definition
// ----------------------------------------------------------------------------
/*
CREATE (w:Workflow {
  workflowId: "workflow-uuid-123",
  workflowName: "High Risk Bag Handling",
  description: "Handle high-risk baggage with potential missed connections",
  collaborationPattern: "sequential",  // sequential, parallel, conditional, loop, approval

  entryPoint: "ScanProcessorAgent",

  maxExecutionTimeSeconds: 300,
  isActive: true,

  createdAt: datetime("2024-11-13T14:00:00Z"),
  updatedAt: datetime("2024-11-13T14:00:00Z")
})
*/

// ----------------------------------------------------------------------------
// :Capability - Individual agent capability
// ----------------------------------------------------------------------------
/*
CREATE (c:Capability {
  capabilityId: "predict_mishandling",
  name: "Predict Mishandling",
  description: "Predict probability of baggage mishandling",

  confidence: 0.92,
  avgExecutionTimeMs: 145,
  successRate: 0.947,

  inputTypes: ["BaggageDigitalTwin", "Flight", "Airport"],
  outputTypes: ["RiskAssessment"],

  requiresCapabilities: []
})
*/

// ============================================================================
// PART 3: AGENT COLLABORATION RELATIONSHIPS
// ============================================================================

// ----------------------------------------------------------------------------
// [:DEPENDS_ON] - Dependency between agents
// ----------------------------------------------------------------------------
// (agent1:Agent)-[:DEPENDS_ON]->(agent2:Agent)
/*
Properties:
  dependencyType: string - must_complete, should_complete, can_parallel, conflicts, complements
  strength: float (0.0-1.0) - Strength of dependency
  reason: string - Why this dependency exists
  isOptional: boolean - Can workflow proceed without this?
  timeoutSeconds: integer - Timeout waiting for dependency

Sample:
MATCH (scan:Agent {agentType: "ScanProcessorAgent"}),
      (risk:Agent {agentType: "RiskScorerAgent"})
CREATE (scan)-[:DEPENDS_ON {
  dependencyType: "must_complete",
  strength: 1.0,
  reason: "Risk scorer needs updated digital twin from scan processor",
  isOptional: false,
  timeoutSeconds: 30
}]->(risk)
*/

// ----------------------------------------------------------------------------
// [:PARALLEL_WITH] - Agents that can run in parallel
// ----------------------------------------------------------------------------
// (agent1:Agent)-[:PARALLEL_WITH]->(agent2:Agent)
/*
Properties:
  syncPoint: string - Where results are synchronized
  mergeStrategy: string - wait_all, wait_first, wait_majority, best_confidence, aggregate
  timeoutSeconds: integer - Timeout for parallel execution
  minRequiredCompletions: integer - Minimum agents that must complete

Sample:
MATCH (courier:Agent {agentType: "CourierDispatchAgent"}),
      (comms:Agent {agentType: "PassengerCommsAgent"})
CREATE (courier)-[:PARALLEL_WITH {
  syncPoint: "exception_resolved",
  mergeStrategy: "wait_all",
  timeoutSeconds: 60,
  minRequiredCompletions: 2
}]->(comms)
*/

// ----------------------------------------------------------------------------
// [:ROUTES_TO] - Routing between agents based on conditions
// ----------------------------------------------------------------------------
// (agent1:Agent)-[:ROUTES_TO]->(agent2:Agent)
/*
Properties:
  condition: string - risk_threshold, elite_status, cost_benefit, sla_breach, etc.
  conditionValue: any - Value to evaluate condition against
  priority: integer (1-10) - Routing priority (1=highest)
  isActive: boolean - Is this routing rule active?
  routeWhen: string - When to apply this route

Sample:
MATCH (risk:Agent {agentType: "RiskScorerAgent"}),
      (case:Agent {agentType: "CaseManagerAgent"})
CREATE (risk)-[:ROUTES_TO {
  condition: "risk_threshold",
  conditionValue: 0.7,
  priority: 1,
  isActive: true,
  routeWhen: "risk_score >= threshold"
}]->(case)
*/

// ----------------------------------------------------------------------------
// [:REQUESTS_APPROVAL] - Agent requests human approval
// ----------------------------------------------------------------------------
// (agent:Agent)-[:REQUESTS_APPROVAL]->(human:Agent)
/*
Properties:
  approvalThreshold: float - Threshold that triggers approval
  approverRole: string - Role required for approval
  autoApproveConditions: string[] - Conditions for auto-approval
  approvalTimeoutSeconds: integer - Timeout waiting for approval
  escalationAfterSeconds: integer - Escalate to higher authority after this time

Sample:
MATCH (courier:Agent {agentType: "CourierDispatchAgent"}),
      (manager:Agent {agentId: "StationManager-MIA"})
CREATE (courier)-[:REQUESTS_APPROVAL {
  approvalThreshold: 100.0,
  approverRole: "StationManager",
  autoApproveConditions: ["elite_status >= Gold", "cost < 100"],
  approvalTimeoutSeconds: 1800,
  escalationAfterSeconds: 900
}]->(manager)
*/

// ----------------------------------------------------------------------------
// [:HAS_CAPABILITY] - Agent has specific capability
// ----------------------------------------------------------------------------
// (agent:Agent)-[:HAS_CAPABILITY]->(capability:Capability)
/*
Properties:
  enabledAt: datetime - When capability was enabled
  isActive: boolean - Is capability currently active?

Sample:
MATCH (risk:Agent {agentType: "RiskScorerAgent"}),
      (cap:Capability {capabilityId: "predict_mishandling"})
CREATE (risk)-[:HAS_CAPABILITY {
  enabledAt: datetime("2024-11-13T14:00:00Z"),
  isActive: true
}]->(cap)
*/

// ----------------------------------------------------------------------------
// [:REQUIRES_CAPABILITY] - Capability requires another capability
// ----------------------------------------------------------------------------
// (cap1:Capability)-[:REQUIRES_CAPABILITY]->(cap2:Capability)
/*
Properties:
  isOptional: boolean - Is this requirement optional?
  reason: string - Why this capability is required

Sample:
MATCH (agg:Capability {capabilityId: "calculate_aggregate_risk"}),
      (pred:Capability {capabilityId: "predict_mishandling"})
CREATE (agg)-[:REQUIRES_CAPABILITY {
  isOptional: false,
  reason: "Aggregate risk needs mishandling prediction as input"
}]->(pred)
*/

// ----------------------------------------------------------------------------
// [:PART_OF_WORKFLOW] - Agent is part of workflow
// ----------------------------------------------------------------------------
// (agent:Agent)-[:PART_OF_WORKFLOW]->(workflow:Workflow)
/*
Properties:
  sequence: integer - Sequence in workflow
  isEntryPoint: boolean - Is this the entry point?
  isExitPoint: boolean - Is this an exit point?

Sample:
MATCH (scan:Agent {agentType: "ScanProcessorAgent"}),
      (wf:Workflow {workflowId: "workflow-uuid-123"})
CREATE (scan)-[:PART_OF_WORKFLOW {
  sequence: 1,
  isEntryPoint: true,
  isExitPoint: false
}]->(wf)
*/

// ----------------------------------------------------------------------------
// [:EXECUTES] - Agent execution instance
// ----------------------------------------------------------------------------
// (agent:Agent)-[:EXECUTES]->(execution:Execution)
/*
Properties:
  startedAt: datetime - When execution started
  completedAt: datetime - When execution completed
  executionTimeMs: integer - Total execution time
  success: boolean - Was execution successful?
  errorMessage: string - Error message if failed
  retryAttempt: integer - Retry attempt number

Sample:
MATCH (risk:Agent {agentType: "RiskScorerAgent"}),
      (exec:Execution {executionId: "exec-uuid-456"})
CREATE (risk)-[:EXECUTES {
  startedAt: datetime("2024-11-13T14:30:00Z"),
  completedAt: datetime("2024-11-13T14:30:01Z"),
  executionTimeMs: 145,
  success: true,
  errorMessage: null,
  retryAttempt: 1
}]->(exec)
*/

// ============================================================================
// PART 4: COLLABORATION PATTERN QUERIES
// ============================================================================

// Pattern 1: Sequential execution chain
/*
MATCH path = (a1:Agent)-[:DEPENDS_ON {dependencyType: "must_complete"}*]->(a2:Agent)
WHERE a1.agentType = "ScanProcessorAgent"
RETURN path
*/

// Pattern 2: Parallel execution branches
/*
MATCH (a:Agent)-[:PARALLEL_WITH]->(b:Agent)
WHERE a.agentType IN ["CourierDispatchAgent", "PassengerCommsAgent"]
RETURN a, b
*/

// Pattern 3: Conditional routing
/*
MATCH (a:Agent)-[r:ROUTES_TO]->(b:Agent)
WHERE r.condition = "risk_threshold"
RETURN a.agentType, b.agentType, r.conditionValue, r.routeWhen
ORDER BY r.priority ASC
*/

// Pattern 4: Approval workflows
/*
MATCH (requester:Agent)-[r:REQUESTS_APPROVAL]->(approver:Agent)
WHERE r.approvalThreshold IS NOT NULL
RETURN requester.agentType, approver.agentId, r.approverRole, r.autoApproveConditions
*/

// Pattern 5: Agent capabilities graph
/*
MATCH (a:Agent)-[:HAS_CAPABILITY]->(c:Capability)
RETURN a.agentType, collect(c.name) as capabilities
ORDER BY a.agentType
*/

// Pattern 6: Capability dependencies
/*
MATCH path = (c1:Capability)-[:REQUIRES_CAPABILITY*]->(c2:Capability)
WHERE c1.capabilityId = "calculate_aggregate_risk"
RETURN path
*/

// ============================================================================
// PART 5: ORCHESTRATION QUERIES
// ============================================================================

// Query 1: Get complete workflow execution path
/*
MATCH (wf:Workflow {workflowName: "High Risk Bag Handling"})
MATCH (a:Agent)-[r:PART_OF_WORKFLOW]->(wf)
OPTIONAL MATCH (a)-[dep:DEPENDS_ON]->(next:Agent)
RETURN a, r, dep, next
ORDER BY r.sequence
*/

// Query 2: Find agents that can run in parallel
/*
MATCH (a1:Agent)-[p:PARALLEL_WITH]-(a2:Agent)
WHERE p.syncPoint = "exception_resolved"
RETURN a1.agentType, a2.agentType, p.mergeStrategy, p.timeoutSeconds
*/

// Query 3: Get agent health status
/*
MATCH (a:Agent)
WHERE a.healthStatus <> "healthy"
RETURN a.agentType, a.healthStatus, a.lastHealthCheck
ORDER BY a.lastHealthCheck ASC
*/

// Query 4: Find bottleneck agents
/*
MATCH (a:Agent)-[:DEPENDS_ON]->(b:Agent)
WITH b, count(a) as dependentCount
WHERE dependentCount > 2
RETURN b.agentType, dependentCount, b.avgExecutionTimeMs
ORDER BY dependentCount DESC, b.avgExecutionTimeMs DESC
*/

// Query 5: Calculate workflow critical path
/*
MATCH path = (entry:Agent)-[:DEPENDS_ON*]->(exit:Agent)
WHERE entry.agentType = "ScanProcessorAgent"
WITH path, reduce(time = 0, n IN nodes(path) | time + n.avgExecutionTimeMs) as totalTime
RETURN path, totalTime
ORDER BY totalTime DESC
LIMIT 1
*/

// Query 6: Find agents requiring approval
/*
MATCH (a:Agent)-[r:REQUESTS_APPROVAL]->(approver:Agent)
RETURN a.agentType, approver.agentId, r.approverRole, r.approvalTimeoutSeconds
*/

// ============================================================================
// PART 6: PERFORMANCE OPTIMIZATION QUERIES
// ============================================================================

// Query 1: Identify slow agents
/*
MATCH (a:Agent)
WHERE a.avgExecutionTimeMs > 200
RETURN a.agentType, a.avgExecutionTimeMs, a.successRate
ORDER BY a.avgExecutionTimeMs DESC
*/

// Query 2: Find agents with low success rate
/*
MATCH (a:Agent)
WHERE a.successRate < 0.95
RETURN a.agentType, a.successRate, a.healthStatus
ORDER BY a.successRate ASC
*/

// Query 3: Analyze parallel execution opportunities
/*
MATCH (a1:Agent)-[:DEPENDS_ON {dependencyType: "can_parallel"}]-(a2:Agent)
WHERE NOT exists((a1)-[:PARALLEL_WITH]-(a2))
RETURN a1.agentType, a2.agentType,
       "Potential for parallelization" as recommendation
*/

// Query 4: Find circular dependencies
/*
MATCH path = (a:Agent)-[:DEPENDS_ON*]->(a)
RETURN path, length(path) as cycleLength
ORDER BY cycleLength
*/

// ============================================================================
// PART 7: SAMPLE GRAPH CREATION
// ============================================================================

// Create 8 AI Agents
CREATE (scan:Agent {
  agentId: "ScanProcessorAgent-001",
  agentType: "ScanProcessorAgent",
  agentName: "Scan Event Processor",
  version: "2.1.0",
  maxParallelism: 10,
  avgExecutionTimeMs: 87,
  successRate: 0.998,
  healthStatus: "healthy",
  lastHealthCheck: datetime("2024-11-13T14:00:00Z")
})

CREATE (risk:Agent {
  agentId: "RiskScorerAgent-001",
  agentType: "RiskScorerAgent",
  agentName: "Risk Scoring Engine",
  version: "2.3.0",
  maxParallelism: 5,
  avgExecutionTimeMs: 145,
  successRate: 0.947,
  healthStatus: "healthy",
  lastHealthCheck: datetime("2024-11-13T14:00:00Z")
})

CREATE (case:Agent {
  agentId: "CaseManagerAgent-001",
  agentType: "CaseManagerAgent",
  agentName: "Exception Case Manager",
  version: "1.8.0",
  maxParallelism: 8,
  avgExecutionTimeMs: 112,
  successRate: 0.982,
  healthStatus: "healthy",
  lastHealthCheck: datetime("2024-11-13T14:00:00Z")
})

CREATE (courier:Agent {
  agentId: "CourierDispatchAgent-001",
  agentType: "CourierDispatchAgent",
  agentName: "Courier Dispatch Manager",
  version: "1.5.0",
  maxParallelism: 3,
  avgExecutionTimeMs: 156,
  successRate: 0.967,
  healthStatus: "healthy",
  lastHealthCheck: datetime("2024-11-13T14:00:00Z")
})

CREATE (comms:Agent {
  agentId: "PassengerCommsAgent-001",
  agentType: "PassengerCommsAgent",
  agentName: "Passenger Communications",
  version: "1.9.0",
  maxParallelism: 15,
  avgExecutionTimeMs: 345,
  successRate: 0.983,
  healthStatus: "healthy",
  lastHealthCheck: datetime("2024-11-13T14:00:00Z")
})

CREATE (wt:Agent {
  agentId: "WorldTracerAgent-001",
  agentType: "WorldTracerAgent",
  agentName: "WorldTracer Integration",
  version: "2.0.0",
  maxParallelism: 4,
  avgExecutionTimeMs: 567,
  successRate: 0.991,
  healthStatus: "healthy",
  lastHealthCheck: datetime("2024-11-13T14:00:00Z")
})

CREATE (sita:Agent {
  agentId: "SITAHandlerAgent-001",
  agentType: "SITAHandlerAgent",
  agentName: "SITA Message Handler",
  version: "1.7.0",
  maxParallelism: 12,
  avgExecutionTimeMs: 56,
  successRate: 0.997,
  healthStatus: "healthy",
  lastHealthCheck: datetime("2024-11-13T14:00:00Z")
})

CREATE (xml:Agent {
  agentId: "BaggageXMLAgent-001",
  agentType: "BaggageXMLAgent",
  agentName: "BaggageXML Handler",
  version: "1.4.0",
  maxParallelism: 6,
  avgExecutionTimeMs: 123,
  successRate: 0.989,
  healthStatus: "healthy",
  lastHealthCheck: datetime("2024-11-13T14:00:00Z")
})

// Create Workflow
CREATE (wf:Workflow {
  workflowId: "workflow-high-risk-001",
  workflowName: "High Risk Bag Handling",
  description: "Handle high-risk baggage with potential missed connections",
  collaborationPattern: "sequential",
  entryPoint: "ScanProcessorAgent",
  maxExecutionTimeSeconds: 300,
  isActive: true,
  createdAt: datetime("2024-11-13T14:00:00Z")
})

// Sequential Dependencies
MATCH (scan:Agent {agentType: "ScanProcessorAgent"}),
      (risk:Agent {agentType: "RiskScorerAgent"})
CREATE (scan)-[:DEPENDS_ON {
  dependencyType: "must_complete",
  strength: 1.0,
  reason: "Risk scorer needs updated digital twin from scan processor",
  isOptional: false,
  timeoutSeconds: 30
}]->(risk)

MATCH (risk:Agent {agentType: "RiskScorerAgent"}),
      (case:Agent {agentType: "CaseManagerAgent"})
CREATE (risk)-[:DEPENDS_ON {
  dependencyType: "must_complete",
  strength: 0.9,
  reason: "Case manager creates exception only for high-risk bags",
  isOptional: false,
  timeoutSeconds: 60
}]->(case)

// Conditional Routing
MATCH (risk:Agent {agentType: "RiskScorerAgent"}),
      (case:Agent {agentType: "CaseManagerAgent"})
CREATE (risk)-[:ROUTES_TO {
  condition: "risk_threshold",
  conditionValue: 0.7,
  priority: 1,
  isActive: true,
  routeWhen: "risk_score >= 0.7"
}]->(case)

MATCH (case:Agent {agentType: "CaseManagerAgent"}),
      (courier:Agent {agentType: "CourierDispatchAgent"})
CREATE (case)-[:ROUTES_TO {
  condition: "cost_benefit",
  conditionValue: 2.0,
  priority: 2,
  isActive: true,
  routeWhen: "cost_benefit_ratio >= 2.0"
}]->(courier)

// Parallel Execution
MATCH (courier:Agent {agentType: "CourierDispatchAgent"}),
      (comms:Agent {agentType: "PassengerCommsAgent"})
CREATE (courier)-[:PARALLEL_WITH {
  syncPoint: "exception_resolved",
  mergeStrategy: "wait_all",
  timeoutSeconds: 60,
  minRequiredCompletions: 2
}]->(comms)

// Approval Workflow
MATCH (courier:Agent {agentType: "CourierDispatchAgent"}),
      (manager:Agent {agentId: "StationManager-MIA"})
CREATE (courier)-[:REQUESTS_APPROVAL {
  approvalThreshold: 100.0,
  approverRole: "StationManager",
  autoApproveConditions: ["elite_status >= Gold", "cost < 100"],
  approvalTimeoutSeconds: 1800,
  escalationAfterSeconds: 900
}]->(manager)

// Workflow Membership
MATCH (scan:Agent {agentType: "ScanProcessorAgent"}),
      (wf:Workflow {workflowId: "workflow-high-risk-001"})
CREATE (scan)-[:PART_OF_WORKFLOW {
  sequence: 1,
  isEntryPoint: true,
  isExitPoint: false
}]->(wf)

MATCH (risk:Agent {agentType: "RiskScorerAgent"}),
      (wf:Workflow {workflowId: "workflow-high-risk-001"})
CREATE (risk)-[:PART_OF_WORKFLOW {
  sequence: 2,
  isEntryPoint: false,
  isExitPoint: false
}]->(wf)

MATCH (case:Agent {agentType: "CaseManagerAgent"}),
      (wf:Workflow {workflowId: "workflow-high-risk-001"})
CREATE (case)-[:PART_OF_WORKFLOW {
  sequence: 3,
  isEntryPoint: false,
  isExitPoint: false
}]->(wf)

MATCH (courier:Agent {agentType: "CourierDispatchAgent"}),
      (wf:Workflow {workflowId: "workflow-high-risk-001"})
CREATE (courier)-[:PART_OF_WORKFLOW {
  sequence: 4,
  isEntryPoint: false,
  isExitPoint: false
}]->(wf)

MATCH (comms:Agent {agentType: "PassengerCommsAgent"}),
      (wf:Workflow {workflowId: "workflow-high-risk-001"})
CREATE (comms)-[:PART_OF_WORKFLOW {
  sequence: 5,
  isEntryPoint: false,
  isExitPoint: true
}]->(wf)

// ============================================================================
// END OF AGENT COLLABORATION SCHEMA
// ============================================================================

// Usage Notes:
// 1. Agents have capabilities with confidence scores
// 2. Dependencies define execution order and constraints
// 3. Routing rules enable conditional branching
// 4. Parallel execution supports concurrent agent execution
// 5. Approval workflows require human intervention
// 6. Workflows tie everything together

// Key Patterns:
// - Sequential: A → B → C (DEPENDS_ON chain)
// - Parallel: A → (B, C) → D (PARALLEL_WITH + merge)
// - Conditional: A → B or C (ROUTES_TO with conditions)
// - Loop: A → B → C → A (circular DEPENDS_ON with feedback)
// - Approval: A → Human → B (REQUESTS_APPROVAL)

// This enables:
// - Dynamic workflow orchestration
// - Intelligent routing based on context
// - Parallel execution for performance
// - Human-in-the-loop for critical decisions
// - Capability-based agent selection
