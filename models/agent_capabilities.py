"""
Agent Capabilities and Collaboration Patterns
==============================================

This module defines the capabilities of each of the 8 AI agents and their
collaboration patterns for coordinated workflows.

Version: 1.0.0
Date: 2024-11-13
"""

from typing import List, Dict, Optional, Literal, Any
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, validator, confloat, conint


# ============================================================================
# ENUMERATIONS
# ============================================================================

class CollaborationPattern(str, Enum):
    """Types of agent collaboration patterns"""
    SEQUENTIAL = "sequential"  # A completes → B starts
    PARALLEL = "parallel"  # A and B run simultaneously
    CONDITIONAL = "conditional"  # A evaluates → routes to B or C
    LOOP = "loop"  # A → B → C → back to A with feedback
    APPROVAL = "approval"  # A requests → Human approves → B executes
    FAN_OUT = "fan_out"  # A → B, C, D simultaneously
    FAN_IN = "fan_in"  # A, B, C → merge into D


class DependencyType(str, Enum):
    """Types of agent dependencies"""
    MUST_COMPLETE = "must_complete"  # Agent A must complete before B starts
    SHOULD_COMPLETE = "should_complete"  # Agent A should complete, but B can start
    CAN_PARALLEL = "can_parallel"  # A and B can run in parallel
    CONFLICTS = "conflicts"  # A and B cannot run simultaneously
    COMPLEMENTS = "complements"  # A and B work better together


class RoutingCondition(str, Enum):
    """Conditions for routing between agents"""
    RISK_THRESHOLD = "risk_threshold"  # Route based on risk score
    ELITE_STATUS = "elite_status"  # Route based on passenger status
    COST_BENEFIT = "cost_benefit"  # Route based on cost analysis
    SLA_BREACH = "sla_breach"  # Route if SLA is at risk
    MANUAL_REVIEW = "manual_review"  # Route to human review
    EXCEPTION_TYPE = "exception_type"  # Route based on exception type
    ALWAYS = "always"  # Always route
    NEVER = "never"  # Never route


class MergeStrategy(str, Enum):
    """Strategies for merging parallel agent results"""
    WAIT_ALL = "wait_all"  # Wait for all agents to complete
    WAIT_FIRST = "wait_first"  # Use result from first agent
    WAIT_MAJORITY = "wait_majority"  # Wait for majority consensus
    BEST_CONFIDENCE = "best_confidence"  # Use result with highest confidence
    AGGREGATE = "aggregate"  # Combine all results


class BackoffStrategy(str, Enum):
    """Retry backoff strategies"""
    EXPONENTIAL = "exponential"  # 2^n seconds
    LINEAR = "linear"  # n seconds
    CONSTANT = "constant"  # Fixed delay
    FIBONACCI = "fibonacci"  # Fibonacci sequence


class AgentType(str, Enum):
    """8 specialized AI agents"""
    SCAN_PROCESSOR = "ScanProcessorAgent"
    RISK_SCORER = "RiskScorerAgent"
    WORLDTRACER = "WorldTracerAgent"
    SITA_HANDLER = "SITAHandlerAgent"
    BAGGAGE_XML = "BaggageXMLAgent"
    CASE_MANAGER = "CaseManagerAgent"
    COURIER_DISPATCH = "CourierDispatchAgent"
    PASSENGER_COMMS = "PassengerCommsAgent"


# ============================================================================
# AGENT CAPABILITY MODELS
# ============================================================================

class Capability(BaseModel):
    """Individual capability with confidence score"""

    capability_id: str = Field(
        ...,
        description="Unique capability identifier"
    )

    name: str = Field(
        ...,
        min_length=3,
        description="Capability name"
    )

    description: str = Field(
        ...,
        description="What this capability does"
    )

    confidence: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Agent's confidence in this capability (0.0-1.0)"
    )

    avg_execution_time_ms: conint(gt=0) = Field(
        ...,
        description="Average execution time in milliseconds"
    )

    success_rate: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Historical success rate (0.0-1.0)"
    )

    requires_capabilities: List[str] = Field(
        default_factory=list,
        description="Other capabilities required for this to work"
    )

    input_types: List[str] = Field(
        default_factory=list,
        description="Input data types required"
    )

    output_types: List[str] = Field(
        default_factory=list,
        description="Output data types produced"
    )


class AgentCapabilities(BaseModel):
    """Complete capability profile for an agent"""

    agent_id: str = Field(
        ...,
        description="Unique agent identifier"
    )

    agent_type: AgentType = Field(
        ...,
        description="Type of agent"
    )

    agent_name: str = Field(
        ...,
        description="Human-readable agent name"
    )

    version: str = Field(
        ...,
        description="Agent version"
    )

    capabilities: List[Capability] = Field(
        ...,
        min_items=1,
        description="List of agent capabilities"
    )

    max_parallelism: conint(ge=1, le=100) = Field(
        1,
        description="Maximum number of parallel instances"
    )

    is_active: bool = Field(
        True,
        description="Is this agent currently active?"
    )

    health_status: Literal["healthy", "degraded", "unhealthy", "offline"] = Field(
        "healthy",
        description="Current health status"
    )

    last_health_check: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last health check timestamp"
    )


# ============================================================================
# COLLABORATION PATTERN MODELS
# ============================================================================

class RetryPolicy(BaseModel):
    """Retry policy for agent execution"""

    max_attempts: conint(ge=1, le=10) = Field(
        3,
        description="Maximum retry attempts"
    )

    backoff_strategy: BackoffStrategy = Field(
        BackoffStrategy.EXPONENTIAL,
        description="Backoff strategy for retries"
    )

    initial_delay_seconds: conint(ge=1, le=60) = Field(
        2,
        description="Initial delay before first retry"
    )

    max_delay_seconds: conint(ge=1, le=300) = Field(
        60,
        description="Maximum delay between retries"
    )

    retry_on_errors: List[str] = Field(
        default_factory=lambda: ["timeout", "network_error", "rate_limit"],
        description="Error types that trigger retry"
    )


class AgentDependency(BaseModel):
    """Dependency relationship between agents"""

    from_agent: AgentType = Field(
        ...,
        description="Source agent"
    )

    to_agent: AgentType = Field(
        ...,
        description="Target agent"
    )

    dependency_type: DependencyType = Field(
        ...,
        description="Type of dependency"
    )

    strength: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Strength of dependency (0.0=weak, 1.0=strong)"
    )

    reason: str = Field(
        ...,
        description="Why this dependency exists"
    )

    is_optional: bool = Field(
        False,
        description="Can the workflow proceed without this dependency?"
    )

    timeout_seconds: Optional[conint(gt=0)] = Field(
        None,
        description="Timeout waiting for dependency"
    )


class RoutingRule(BaseModel):
    """Rule for routing between agents"""

    from_agent: AgentType = Field(
        ...,
        description="Source agent"
    )

    to_agent: AgentType = Field(
        ...,
        description="Target agent"
    )

    condition: RoutingCondition = Field(
        ...,
        description="Routing condition"
    )

    condition_value: Optional[Any] = Field(
        None,
        description="Value to evaluate condition against"
    )

    priority: conint(ge=1, le=10) = Field(
        5,
        description="Routing priority (1=highest, 10=lowest)"
    )

    is_active: bool = Field(
        True,
        description="Is this routing rule active?"
    )


class ParallelExecution(BaseModel):
    """Parallel execution configuration"""

    agents: List[AgentType] = Field(
        ...,
        min_items=2,
        description="Agents to execute in parallel"
    )

    sync_point: str = Field(
        ...,
        description="Where results are synchronized"
    )

    merge_strategy: MergeStrategy = Field(
        MergeStrategy.WAIT_ALL,
        description="How to merge parallel results"
    )

    timeout_seconds: conint(gt=0) = Field(
        30,
        description="Timeout for all parallel executions"
    )

    min_required_completions: conint(ge=1) = Field(
        1,
        description="Minimum agents that must complete successfully"
    )

    @validator('min_required_completions')
    def validate_min_completions(cls, v, values):
        if 'agents' in values and v > len(values['agents']):
            raise ValueError('min_required_completions cannot exceed number of agents')
        return v


class ApprovalWorkflow(BaseModel):
    """Approval workflow configuration"""

    requesting_agent: AgentType = Field(
        ...,
        description="Agent requesting approval"
    )

    executing_agent: AgentType = Field(
        ...,
        description="Agent that executes after approval"
    )

    approval_threshold: confloat(ge=0.0) = Field(
        ...,
        description="Threshold that triggers approval requirement"
    )

    approver_role: str = Field(
        ...,
        description="Role required for approval (e.g., StationManager)"
    )

    auto_approve_conditions: List[str] = Field(
        default_factory=list,
        description="Conditions for automatic approval"
    )

    approval_timeout_seconds: conint(gt=0) = Field(
        3600,
        description="Timeout waiting for approval"
    )

    escalation_after_seconds: Optional[conint(gt=0)] = Field(
        None,
        description="Escalate to higher authority after this time"
    )


class WorkflowOrchestration(BaseModel):
    """Complete workflow orchestration configuration"""

    workflow_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique workflow identifier"
    )

    workflow_name: str = Field(
        ...,
        description="Workflow name"
    )

    description: str = Field(
        ...,
        description="Workflow description"
    )

    collaboration_pattern: CollaborationPattern = Field(
        ...,
        description="Primary collaboration pattern"
    )

    entry_point: AgentType = Field(
        ...,
        description="Agent that starts the workflow"
    )

    dependencies: List[AgentDependency] = Field(
        default_factory=list,
        description="Agent dependencies"
    )

    routing_rules: List[RoutingRule] = Field(
        default_factory=list,
        description="Routing rules between agents"
    )

    parallel_executions: List[ParallelExecution] = Field(
        default_factory=list,
        description="Parallel execution configurations"
    )

    approval_workflows: List[ApprovalWorkflow] = Field(
        default_factory=list,
        description="Approval workflow configurations"
    )

    retry_policy: RetryPolicy = Field(
        default_factory=RetryPolicy,
        description="Default retry policy"
    )

    max_execution_time_seconds: conint(gt=0) = Field(
        300,
        description="Maximum workflow execution time"
    )

    is_active: bool = Field(
        True,
        description="Is this workflow active?"
    )


# ============================================================================
# PREDEFINED AGENT CAPABILITIES
# ============================================================================

SCAN_PROCESSOR_CAPABILITIES = AgentCapabilities(
    agent_id="ScanProcessorAgent-001",
    agent_type=AgentType.SCAN_PROCESSOR,
    agent_name="Scan Event Processor",
    version="2.1.0",
    max_parallelism=10,
    capabilities=[
        Capability(
            capability_id="process_bhs_scan",
            name="Process BHS Scan",
            description="Process baggage handling system scan events",
            confidence=0.99,
            avg_execution_time_ms=87,
            success_rate=0.998,
            input_types=["BPM", "BSM", "BTM"],
            output_types=["ScanEvent", "BaggageUpdate"]
        ),
        Capability(
            capability_id="validate_scan_sequence",
            name="Validate Scan Sequence",
            description="Ensure scans are in correct sequence",
            confidence=0.95,
            avg_execution_time_ms=45,
            success_rate=0.993,
            input_types=["ScanEvent[]"],
            output_types=["ValidationResult"]
        ),
        Capability(
            capability_id="detect_scan_gaps",
            name="Detect Scan Gaps",
            description="Identify missing scans in journey",
            confidence=0.92,
            avg_execution_time_ms=65,
            success_rate=0.989,
            input_types=["ScanEvent[]", "ExpectedRoute"],
            output_types=["ScanGapAlert"]
        ),
        Capability(
            capability_id="update_digital_twin",
            name="Update Digital Twin",
            description="Update baggage digital twin with scan data",
            confidence=0.98,
            avg_execution_time_ms=120,
            success_rate=0.997,
            input_types=["ScanEvent", "BaggageDigitalTwin"],
            output_types=["BaggageDigitalTwin"]
        )
    ]
)

RISK_SCORER_CAPABILITIES = AgentCapabilities(
    agent_id="RiskScorerAgent-001",
    agent_type=AgentType.RISK_SCORER,
    agent_name="Risk Scoring Engine",
    version="2.3.0",
    max_parallelism=5,
    capabilities=[
        Capability(
            capability_id="predict_mishandling",
            name="Predict Mishandling",
            description="Predict probability of baggage mishandling",
            confidence=0.92,
            avg_execution_time_ms=145,
            success_rate=0.947,
            input_types=["BaggageDigitalTwin", "Flight", "Airport"],
            output_types=["RiskAssessment"]
        ),
        Capability(
            capability_id="calculate_mct_risk",
            name="Calculate MCT Risk",
            description="Assess risk of missing minimum connection time",
            confidence=0.95,
            avg_execution_time_ms=98,
            success_rate=0.965,
            input_types=["Flight[]", "Airport"],
            output_types=["MCTRiskScore"]
        ),
        Capability(
            capability_id="detect_irrops_impact",
            name="Detect IRROPS Impact",
            description="Assess impact of irregular operations",
            confidence=0.88,
            avg_execution_time_ms=178,
            success_rate=0.912,
            input_types=["Flight", "Weather", "Airport"],
            output_types=["IRROPSImpact"]
        ),
        Capability(
            capability_id="assess_weather_risk",
            name="Assess Weather Risk",
            description="Evaluate weather impact on baggage delivery",
            confidence=0.85,
            avg_execution_time_ms=134,
            success_rate=0.891,
            input_types=["Weather", "Airport", "Flight"],
            output_types=["WeatherRisk"]
        ),
        Capability(
            capability_id="calculate_aggregate_risk",
            name="Calculate Aggregate Risk",
            description="Combine multiple risk factors into overall score",
            confidence=0.94,
            avg_execution_time_ms=89,
            success_rate=0.978,
            requires_capabilities=["predict_mishandling", "calculate_mct_risk"],
            input_types=["RiskFactor[]"],
            output_types=["RiskAssessment"]
        )
    ]
)

CASE_MANAGER_CAPABILITIES = AgentCapabilities(
    agent_id="CaseManagerAgent-001",
    agent_type=AgentType.CASE_MANAGER,
    agent_name="Exception Case Manager",
    version="1.8.0",
    max_parallelism=8,
    capabilities=[
        Capability(
            capability_id="create_exception_case",
            name="Create Exception Case",
            description="Create exception case from risk assessment",
            confidence=0.96,
            avg_execution_time_ms=112,
            success_rate=0.982,
            input_types=["RiskAssessment", "Baggage"],
            output_types=["ExceptionCase"]
        ),
        Capability(
            capability_id="route_to_team",
            name="Route to Team",
            description="Route exception to appropriate team",
            confidence=0.93,
            avg_execution_time_ms=67,
            success_rate=0.971,
            input_types=["ExceptionCase", "RoutingRules"],
            output_types=["Assignment"]
        ),
        Capability(
            capability_id="orchestrate_agents",
            name="Orchestrate Agents",
            description="Coordinate multiple agents for exception resolution",
            confidence=0.91,
            avg_execution_time_ms=234,
            success_rate=0.955,
            input_types=["ExceptionCase", "AgentGraph"],
            output_types=["OrchestrationPlan"]
        ),
        Capability(
            capability_id="track_sla",
            name="Track SLA",
            description="Monitor and enforce SLA deadlines",
            confidence=0.98,
            avg_execution_time_ms=45,
            success_rate=0.995,
            input_types=["ExceptionCase", "SLAPolicy"],
            output_types=["SLAStatus"]
        )
    ]
)

COURIER_DISPATCH_CAPABILITIES = AgentCapabilities(
    agent_id="CourierDispatchAgent-001",
    agent_type=AgentType.COURIER_DISPATCH,
    agent_name="Courier Dispatch Manager",
    version="1.5.0",
    max_parallelism=3,
    capabilities=[
        Capability(
            capability_id="cost_benefit_analysis",
            name="Cost-Benefit Analysis",
            description="Analyze courier dispatch cost vs claim cost",
            confidence=0.94,
            avg_execution_time_ms=156,
            success_rate=0.967,
            input_types=["Baggage", "Passenger", "CourierQuotes"],
            output_types=["CostBenefitAnalysis"]
        ),
        Capability(
            capability_id="select_courier",
            name="Select Courier",
            description="Select optimal courier vendor and service level",
            confidence=0.91,
            avg_execution_time_ms=189,
            success_rate=0.943,
            input_types=["DeliveryRequirements", "CourierVendors"],
            output_types=["CourierSelection"]
        ),
        Capability(
            capability_id="book_courier",
            name="Book Courier",
            description="Book courier pickup and delivery",
            confidence=0.89,
            avg_execution_time_ms=456,
            success_rate=0.921,
            input_types=["CourierSelection", "PickupDetails", "DeliveryAddress"],
            output_types=["CourierBooking"]
        ),
        Capability(
            capability_id="track_delivery",
            name="Track Delivery",
            description="Track courier delivery status",
            confidence=0.95,
            avg_execution_time_ms=234,
            success_rate=0.976,
            input_types=["TrackingNumber", "CourierVendor"],
            output_types=["DeliveryStatus"]
        )
    ]
)

PASSENGER_COMMS_CAPABILITIES = AgentCapabilities(
    agent_id="PassengerCommsAgent-001",
    agent_type=AgentType.PASSENGER_COMMS,
    agent_name="Passenger Communications",
    version="1.9.0",
    max_parallelism=15,
    capabilities=[
        Capability(
            capability_id="send_proactive_notification",
            name="Send Proactive Notification",
            description="Send proactive notifications to passengers",
            confidence=0.97,
            avg_execution_time_ms=345,
            success_rate=0.983,
            input_types=["Passenger", "NotificationTemplate", "Channel"],
            output_types=["NotificationStatus"]
        ),
        Capability(
            capability_id="select_channel",
            name="Select Channel",
            description="Select optimal notification channel",
            confidence=0.93,
            avg_execution_time_ms=78,
            success_rate=0.968,
            input_types=["Passenger", "NotificationType", "Urgency"],
            output_types=["ChannelSelection"]
        ),
        Capability(
            capability_id="personalize_message",
            name="Personalize Message",
            description="Personalize message for passenger",
            confidence=0.90,
            avg_execution_time_ms=123,
            success_rate=0.951,
            input_types=["Template", "Passenger", "Context"],
            output_types=["PersonalizedMessage"]
        ),
        Capability(
            capability_id="track_delivery_status",
            name="Track Delivery Status",
            description="Track notification delivery and engagement",
            confidence=0.96,
            avg_execution_time_ms=67,
            success_rate=0.988,
            input_types=["NotificationId", "Channel"],
            output_types=["DeliveryMetrics"]
        )
    ]
)

# Remaining agent capabilities (WorldTracer, SITA, BaggageXML)
WORLDTRACER_CAPABILITIES = AgentCapabilities(
    agent_id="WorldTracerAgent-001",
    agent_type=AgentType.WORLDTRACER,
    agent_name="WorldTracer Integration",
    version="2.0.0",
    max_parallelism=4,
    capabilities=[
        Capability(
            capability_id="file_pir",
            name="File PIR",
            description="File Property Irregularity Report with WorldTracer",
            confidence=0.98,
            avg_execution_time_ms=567,
            success_rate=0.991,
            input_types=["Baggage", "Passenger", "IrregularityType"],
            output_types=["PIR"]
        ),
        Capability(
            capability_id="update_pir_status",
            name="Update PIR Status",
            description="Update PIR status in WorldTracer",
            confidence=0.97,
            avg_execution_time_ms=234,
            success_rate=0.986,
            input_types=["PIRNumber", "Status", "Location"],
            output_types=["PIRUpdateResult"]
        )
    ]
)

SITA_HANDLER_CAPABILITIES = AgentCapabilities(
    agent_id="SITAHandlerAgent-001",
    agent_type=AgentType.SITA_HANDLER,
    agent_name="SITA Message Handler",
    version="1.7.0",
    max_parallelism=12,
    capabilities=[
        Capability(
            capability_id="parse_type_b",
            name="Parse Type B Message",
            description="Parse IATA Type B messages",
            confidence=0.99,
            avg_execution_time_ms=56,
            success_rate=0.997,
            input_types=["TypeBMessage"],
            output_types=["ParsedMessage"]
        ),
        Capability(
            capability_id="route_message",
            name="Route Message",
            description="Route messages to appropriate agents",
            confidence=0.96,
            avg_execution_time_ms=34,
            success_rate=0.993,
            input_types=["ParsedMessage", "RoutingRules"],
            output_types=["RoutingDecision"]
        )
    ]
)

BAGGAGE_XML_CAPABILITIES = AgentCapabilities(
    agent_id="BaggageXMLAgent-001",
    agent_type=AgentType.BAGGAGE_XML,
    agent_name="BaggageXML Handler",
    version="1.4.0",
    max_parallelism=6,
    capabilities=[
        Capability(
            capability_id="parse_baggage_xml",
            name="Parse BaggageXML",
            description="Parse BaggageXML interline messages",
            confidence=0.98,
            avg_execution_time_ms=123,
            success_rate=0.989,
            input_types=["XMLMessage"],
            output_types=["ParsedManifest"]
        ),
        Capability(
            capability_id="validate_schema",
            name="Validate Schema",
            description="Validate XML against BaggageXML schema",
            confidence=0.99,
            avg_execution_time_ms=89,
            success_rate=0.996,
            input_types=["XMLMessage", "SchemaVersion"],
            output_types=["ValidationResult"]
        )
    ]
)


# ============================================================================
# PREDEFINED WORKFLOWS
# ============================================================================

HIGH_RISK_BAG_WORKFLOW = WorkflowOrchestration(
    workflow_name="High Risk Bag Handling",
    description="Workflow for handling high-risk baggage with potential missed connections",
    collaboration_pattern=CollaborationPattern.SEQUENTIAL,
    entry_point=AgentType.SCAN_PROCESSOR,
    dependencies=[
        AgentDependency(
            from_agent=AgentType.SCAN_PROCESSOR,
            to_agent=AgentType.RISK_SCORER,
            dependency_type=DependencyType.MUST_COMPLETE,
            strength=1.0,
            reason="Risk scorer needs updated digital twin from scan processor"
        ),
        AgentDependency(
            from_agent=AgentType.RISK_SCORER,
            to_agent=AgentType.CASE_MANAGER,
            dependency_type=DependencyType.MUST_COMPLETE,
            strength=0.9,
            reason="Case manager creates exception only for high-risk bags"
        ),
        AgentDependency(
            from_agent=AgentType.CASE_MANAGER,
            to_agent=AgentType.COURIER_DISPATCH,
            dependency_type=DependencyType.SHOULD_COMPLETE,
            strength=0.7,
            reason="Courier dispatch may be needed based on case manager decision"
        ),
        AgentDependency(
            from_agent=AgentType.CASE_MANAGER,
            to_agent=AgentType.PASSENGER_COMMS,
            dependency_type=DependencyType.CAN_PARALLEL,
            strength=0.8,
            reason="Passenger communications can run in parallel with courier dispatch"
        )
    ],
    routing_rules=[
        RoutingRule(
            from_agent=AgentType.RISK_SCORER,
            to_agent=AgentType.CASE_MANAGER,
            condition=RoutingCondition.RISK_THRESHOLD,
            condition_value=0.7,
            priority=1
        ),
        RoutingRule(
            from_agent=AgentType.CASE_MANAGER,
            to_agent=AgentType.COURIER_DISPATCH,
            condition=RoutingCondition.COST_BENEFIT,
            condition_value=2.0,
            priority=2
        )
    ],
    parallel_executions=[
        ParallelExecution(
            agents=[AgentType.COURIER_DISPATCH, AgentType.PASSENGER_COMMS],
            sync_point="exception_resolved",
            merge_strategy=MergeStrategy.WAIT_ALL,
            timeout_seconds=60,
            min_required_completions=2
        )
    ],
    approval_workflows=[
        ApprovalWorkflow(
            requesting_agent=AgentType.COURIER_DISPATCH,
            executing_agent=AgentType.COURIER_DISPATCH,
            approval_threshold=100.0,
            approver_role="StationManager",
            auto_approve_conditions=["elite_status >= Gold", "cost < 100"],
            approval_timeout_seconds=1800,
            escalation_after_seconds=900
        )
    ],
    max_execution_time_seconds=300
)
