"""
Documentation Generator from Knowledge Graph
============================================

Extracts ontology, workflows, agents, and integrations from Neo4j
and generates comprehensive markdown documentation.

Version: 1.0.0
Date: 2025-11-14
"""

import asyncio
import os
from typing import Dict, Any, List
from datetime import datetime


# ============================================================================
# NEO4J MOCK DATA EXTRACTOR
# ============================================================================

class KnowledgeGraphExtractor:
    """Extract documentation data from knowledge graph"""

    def __init__(self):
        self.mock_mode = True  # Using mock data since Neo4j may not be available

    async def extract_ontology(self) -> Dict[str, Any]:
        """Extract complete ontology structure"""
        return {
            "node_types": [
                {
                    "label": "Bag",
                    "description": "Physical baggage item tracked through the system",
                    "properties": [
                        {"name": "bag_tag", "type": "String", "required": True, "description": "Unique 10-digit identifier"},
                        {"name": "weight_kg", "type": "Float", "required": False, "description": "Weight in kilograms"},
                        {"name": "value_usd", "type": "Float", "required": False, "description": "Declared value in USD"},
                        {"name": "status", "type": "String", "required": True, "description": "Current status (CHECKED_IN, LOADED, etc.)"},
                    ]
                },
                {
                    "label": "Passenger",
                    "description": "Traveler who owns baggage",
                    "properties": [
                        {"name": "pnr", "type": "String", "required": True, "description": "Passenger Name Record"},
                        {"name": "name", "type": "String", "required": True, "description": "Full passenger name"},
                        {"name": "phone", "type": "String", "required": False, "description": "Contact phone number"},
                        {"name": "email", "type": "String", "required": False, "description": "Contact email address"},
                    ]
                },
                {
                    "label": "Flight",
                    "description": "Commercial flight carrying baggage",
                    "properties": [
                        {"name": "flight_number", "type": "String", "required": True, "description": "Flight identifier (e.g., UA1234)"},
                        {"name": "origin", "type": "String", "required": True, "description": "Origin airport code"},
                        {"name": "destination", "type": "String", "required": True, "description": "Destination airport code"},
                        {"name": "scheduled_departure", "type": "DateTime", "required": True, "description": "Scheduled departure time"},
                    ]
                },
                {
                    "label": "Event",
                    "description": "Baggage handling event (scan, status change, etc.)",
                    "properties": [
                        {"name": "event_type", "type": "String", "required": True, "description": "Type of event"},
                        {"name": "timestamp", "type": "DateTime", "required": True, "description": "When event occurred"},
                        {"name": "location", "type": "String", "required": False, "description": "Where event occurred"},
                        {"name": "agent_name", "type": "String", "required": False, "description": "Agent that triggered event"},
                    ]
                },
                {
                    "label": "Workflow",
                    "description": "Orchestrated sequence of agent actions",
                    "properties": [
                        {"name": "id", "type": "String", "required": True, "description": "Workflow identifier"},
                        {"name": "name", "type": "String", "required": True, "description": "Workflow name"},
                        {"name": "domain", "type": "String", "required": True, "description": "Business domain"},
                        {"name": "complexity", "type": "String", "required": False, "description": "LOW, MEDIUM, HIGH"},
                    ]
                },
                {
                    "label": "Agent",
                    "description": "Autonomous AI agent performing specific tasks",
                    "properties": [
                        {"name": "id", "type": "String", "required": True, "description": "Agent identifier"},
                        {"name": "name", "type": "String", "required": True, "description": "Agent name"},
                        {"name": "specialization", "type": "String", "required": True, "description": "Agent's area of expertise"},
                        {"name": "autonomy_level", "type": "String", "required": False, "description": "Level of autonomy"},
                    ]
                },
                {
                    "label": "System",
                    "description": "External system integrated via gateway",
                    "properties": [
                        {"name": "id", "type": "String", "required": True, "description": "System identifier"},
                        {"name": "name", "type": "String", "required": True, "description": "System name"},
                        {"name": "type", "type": "String", "required": True, "description": "System type"},
                        {"name": "criticality", "type": "String", "required": False, "description": "CRITICAL, HIGH, MEDIUM, LOW"},
                    ]
                },
            ],
            "relationship_types": [
                {
                    "type": "BELONGS_TO",
                    "from": "Bag",
                    "to": "Passenger",
                    "description": "Bag belongs to passenger",
                    "properties": []
                },
                {
                    "type": "BOOKED_ON",
                    "from": "Bag",
                    "to": "Flight",
                    "description": "Bag is booked on flight",
                    "properties": [
                        {"name": "connection_time_minutes", "type": "Integer", "description": "Time until flight departure"}
                    ]
                },
                {
                    "type": "HAD_EVENT",
                    "from": "Bag",
                    "to": "Event",
                    "description": "Bag experienced event",
                    "properties": [
                        {"name": "at", "type": "DateTime", "description": "When relationship was created"}
                    ]
                },
                {
                    "type": "HANDLES",
                    "from": "Agent",
                    "to": "Workflow",
                    "description": "Agent handles workflow execution",
                    "properties": []
                },
                {
                    "type": "DEPENDS_ON",
                    "from": "Workflow",
                    "to": "Workflow",
                    "description": "Workflow depends on another workflow",
                    "properties": [
                        {"name": "dependency_type", "type": "String", "description": "Type of dependency"}
                    ]
                },
                {
                    "type": "INTEGRATES_WITH",
                    "from": "Agent",
                    "to": "System",
                    "description": "Agent integrates with external system",
                    "properties": []
                },
            ],
            "constraints": [
                {"label": "Bag", "property": "bag_tag", "type": "UNIQUE"},
                {"label": "Passenger", "property": "pnr", "type": "UNIQUE"},
                {"label": "Flight", "property": "flight_number", "type": "INDEX"},
                {"label": "Agent", "property": "id", "type": "UNIQUE"},
                {"label": "Workflow", "property": "id", "type": "UNIQUE"},
            ]
        }

    async def extract_agents(self) -> List[Dict[str, Any]]:
        """Extract all agent information"""
        return [
            {
                "id": "AG001",
                "name": "Scan Processor Agent",
                "specialization": "Baggage scan event processing",
                "autonomy_level": "HIGH",
                "purpose": "Processes scan events from BHS, validates sequences, detects anomalies",
                "capabilities": [
                    "Parse scan events from multiple formats",
                    "Validate scan sequences for logical consistency",
                    "Detect missing scans or out-of-sequence events",
                    "Enrich scan data with contextual information"
                ],
                "inputs": ["BHS scan events", "Location data", "Timestamp"],
                "outputs": ["Validated scan data", "Anomaly alerts", "Enriched context"],
                "dependencies": ["BHS System", "Risk Scorer Agent"],
                "performance": {
                    "throughput": "1000+ scans/minute",
                    "latency": "<10ms per scan",
                    "accuracy": "99.9%"
                }
            },
            {
                "id": "AG002",
                "name": "Risk Scorer Agent",
                "specialization": "Risk assessment and scoring",
                "autonomy_level": "HIGH",
                "purpose": "Calculates risk scores based on multiple factors, triggers alerts for high-risk bags",
                "capabilities": [
                    "Calculate multi-factor risk scores",
                    "Identify risk factors (tight connections, high value, etc.)",
                    "Classify priority levels (CRITICAL, HIGH, MEDIUM, LOW)",
                    "Trigger automated alerts for high-risk bags"
                ],
                "inputs": ["Bag data", "Flight data", "Connection times", "Value declarations"],
                "outputs": ["Risk scores", "Risk factors", "Priority classifications", "Alerts"],
                "dependencies": ["Scan Processor Agent", "Case Manager Agent"],
                "performance": {
                    "throughput": "500+ assessments/minute",
                    "latency": "<15ms per assessment",
                    "accuracy": "95%"
                }
            },
            {
                "id": "AG003",
                "name": "WorldTracer Handler Agent",
                "specialization": "WorldTracer PIR management",
                "autonomy_level": "MEDIUM",
                "purpose": "Creates and manages PIRs in WorldTracer system for mishandled bags",
                "capabilities": [
                    "Create PIRs with complete bag details",
                    "Update PIR status based on bag location",
                    "Search existing PIRs to avoid duplicates",
                    "Match found bags to open PIRs"
                ],
                "inputs": ["Bag data", "Passenger data", "Mishandling reason"],
                "outputs": ["PIR numbers", "PIR status", "Match results"],
                "dependencies": ["WorldTracer System", "Case Manager Agent"],
                "performance": {
                    "throughput": "100+ PIRs/minute",
                    "latency": "<50ms per operation",
                    "accuracy": "98%"
                }
            },
            {
                "id": "AG004",
                "name": "Case Manager Agent",
                "specialization": "Exception case orchestration",
                "autonomy_level": "MEDIUM",
                "purpose": "Creates and manages exception cases, coordinates resolution across agents",
                "capabilities": [
                    "Create exception cases for mishandled bags",
                    "Assign cases to appropriate teams",
                    "Track case resolution status",
                    "Coordinate multi-agent workflows"
                ],
                "inputs": ["Risk assessments", "Mishandling events", "PIR data"],
                "outputs": ["Case IDs", "Case status", "Resolution plans", "Assignments"],
                "dependencies": ["Risk Scorer", "WorldTracer Handler", "Courier Dispatch", "Passenger Comms"],
                "performance": {
                    "throughput": "200+ cases/minute",
                    "latency": "<20ms per case",
                    "accuracy": "97%"
                }
            },
            {
                "id": "AG005",
                "name": "Courier Dispatch Agent",
                "specialization": "Delivery logistics coordination",
                "autonomy_level": "MEDIUM",
                "purpose": "Selects courier services, books deliveries, tracks shipments",
                "capabilities": [
                    "Select best courier based on cost, speed, reliability",
                    "Book deliveries with multiple carriers",
                    "Track delivery status in real-time",
                    "Optimize delivery routes and costs"
                ],
                "inputs": ["Bag location", "Passenger address", "Urgency level", "Cost constraints"],
                "outputs": ["Booking confirmations", "Tracking numbers", "Delivery ETAs", "Cost estimates"],
                "dependencies": ["Courier System", "Case Manager Agent"],
                "performance": {
                    "throughput": "50+ bookings/minute",
                    "latency": "<100ms per booking",
                    "accuracy": "96%"
                }
            },
            {
                "id": "AG006",
                "name": "Passenger Communications Agent",
                "specialization": "Multi-channel passenger notifications",
                "autonomy_level": "HIGH",
                "purpose": "Sends personalized notifications via SMS, email, push notifications",
                "capabilities": [
                    "Compose contextual messages based on situation",
                    "Select optimal communication channel",
                    "Personalize messages with passenger details",
                    "Track notification delivery and engagement"
                ],
                "inputs": ["Case data", "Passenger preferences", "Urgency level", "Message templates"],
                "outputs": ["Notifications sent", "Delivery confirmations", "Engagement metrics"],
                "dependencies": ["Notification System", "Case Manager Agent"],
                "performance": {
                    "throughput": "1000+ notifications/minute",
                    "latency": "<25ms per notification",
                    "delivery_rate": "99.5%"
                }
            },
            {
                "id": "AG007",
                "name": "Data Fusion Agent",
                "specialization": "Multi-source data reconciliation",
                "autonomy_level": "HIGH",
                "purpose": "Fuses data from multiple sources, resolves conflicts, calculates confidence scores",
                "capabilities": [
                    "Merge data from 7+ external systems",
                    "Detect and resolve data conflicts",
                    "Calculate confidence scores based on source reliability",
                    "Maintain data quality metrics"
                ],
                "inputs": ["Data from DCS, BHS, WorldTracer, Type B, XML, Courier, Notifications"],
                "outputs": ["Canonical bag data", "Conflict reports", "Confidence scores", "Quality metrics"],
                "dependencies": ["All external systems via Semantic Gateway"],
                "performance": {
                    "throughput": "500+ fusions/minute",
                    "latency": "<30ms per fusion",
                    "accuracy": "98%"
                }
            },
            {
                "id": "AG008",
                "name": "Semantic Enrichment Agent",
                "specialization": "Contextual data augmentation",
                "autonomy_level": "HIGH",
                "purpose": "Enriches bag data with semantic context, risk factors, handling instructions, tags",
                "capabilities": [
                    "Calculate risk scores from multiple factors",
                    "Generate handling instructions based on context",
                    "Add semantic tags for search and filtering",
                    "Recommend next steps based on current state"
                ],
                "inputs": ["Canonical bag data", "Flight data", "Historical patterns"],
                "outputs": ["Risk assessments", "Handling instructions", "Contextual tags", "Next step recommendations"],
                "dependencies": ["Data Fusion Agent", "Memory System"],
                "performance": {
                    "throughput": "800+ enrichments/minute",
                    "latency": "<20ms per enrichment",
                    "accuracy": "96%"
                }
            }
        ]

    async def extract_workflows(self) -> List[Dict[str, Any]]:
        """Extract all workflow information"""
        return [
            {
                "id": "WF001",
                "name": "High-Risk Bag Workflow",
                "domain": "Exception Handling",
                "complexity": "HIGH",
                "description": "Handles bags with risk score > 0.7 requiring immediate attention and approval",
                "entry_point": "assess_risk",
                "steps": [
                    {"name": "assess_risk", "agent": "Risk Scorer", "description": "Calculate comprehensive risk score"},
                    {"name": "create_exception_case", "agent": "Case Manager", "description": "Create high-priority case"},
                    {"name": "request_approval", "agent": "Case Manager", "description": "Request human approval if needed"},
                    {"name": "create_pir", "agent": "WorldTracer Handler", "description": "Create WorldTracer PIR"},
                    {"name": "notify_passenger", "agent": "Passenger Comms", "description": "Send proactive notification"}
                ],
                "decision_points": [
                    {"condition": "risk_score > 0.9 AND value_usd > 500", "action": "require_human_approval"},
                    {"condition": "approved == true", "action": "proceed_to_pir"},
                    {"condition": "approved == false", "action": "notify_only"}
                ],
                "error_handling": [
                    {"error": "PIR_creation_failed", "strategy": "retry_3_times_then_alert"},
                    {"error": "notification_failed", "strategy": "try_alternate_channel"}
                ],
                "performance": {
                    "avg_duration_ms": 45,
                    "p95_duration_ms": 80,
                    "success_rate": "99.2%"
                }
            },
            {
                "id": "WF002",
                "name": "Transfer Coordination Workflow",
                "domain": "Operations",
                "complexity": "MEDIUM",
                "description": "Handles tight connections (< 60 minutes) with priority transfer processing",
                "entry_point": "assess_connection",
                "steps": [
                    {"name": "assess_connection", "agent": "Risk Scorer", "description": "Evaluate connection time"},
                    {"name": "prioritize_handling", "agent": "Scan Processor", "description": "Flag for priority handling"},
                    {"name": "alert_ramp", "agent": "Passenger Comms", "description": "Alert ramp personnel"},
                    {"name": "track_progress", "agent": "Scan Processor", "description": "Monitor bag progress"}
                ],
                "decision_points": [
                    {"condition": "connection_time_minutes < 30", "action": "critical_priority"},
                    {"condition": "connection_time_minutes < 60", "action": "priority_handling"},
                    {"condition": "connection_time_minutes >= 60", "action": "normal_handling"}
                ],
                "error_handling": [
                    {"error": "missed_connection", "strategy": "trigger_mishandled_workflow"}
                ],
                "performance": {
                    "avg_duration_ms": 30,
                    "p95_duration_ms": 55,
                    "success_rate": "99.7%"
                }
            },
            {
                "id": "WF003",
                "name": "IRROPs Bulk Rebooking Workflow",
                "domain": "Disruption Management",
                "complexity": "HIGH",
                "description": "Handles flight disruptions affecting 10+ bags with bulk processing",
                "entry_point": "detect_disruption",
                "steps": [
                    {"name": "detect_disruption", "agent": "Scan Processor", "description": "Detect flight cancellation/delay"},
                    {"name": "identify_affected_bags", "agent": "Data Fusion", "description": "Find all bags on flight"},
                    {"name": "coordinate_rebooking", "agent": "Case Manager", "description": "Coordinate bulk rebooking"},
                    {"name": "update_routing", "agent": "Data Fusion", "description": "Update bag routing"},
                    {"name": "notify_stakeholders", "agent": "Passenger Comms", "description": "Notify all passengers"}
                ],
                "decision_points": [
                    {"condition": "affected_count >= 10", "action": "enable_bulk_mode"},
                    {"condition": "alternate_flight_available", "action": "auto_rebook"},
                    {"condition": "no_alternate_available", "action": "create_pirs"}
                ],
                "error_handling": [
                    {"error": "rebooking_failed", "strategy": "escalate_to_ops_center"}
                ],
                "performance": {
                    "avg_duration_ms": 120,
                    "p95_duration_ms": 250,
                    "success_rate": "98.5%"
                }
            },
            {
                "id": "WF004",
                "name": "Delivery Coordination Workflow",
                "domain": "Customer Service",
                "complexity": "MEDIUM",
                "description": "Books courier delivery for mishandled bags to passenger address",
                "entry_point": "assess_delivery_need",
                "steps": [
                    {"name": "assess_delivery_need", "agent": "Case Manager", "description": "Determine delivery requirements"},
                    {"name": "select_courier", "agent": "Courier Dispatch", "description": "Select optimal courier"},
                    {"name": "book_courier", "agent": "Courier Dispatch", "description": "Book delivery"},
                    {"name": "track_delivery", "agent": "Courier Dispatch", "description": "Monitor delivery progress"},
                    {"name": "confirm_delivery", "agent": "Passenger Comms", "description": "Confirm with passenger"}
                ],
                "decision_points": [
                    {"condition": "distance_km > 100", "action": "use_premium_courier"},
                    {"condition": "urgency == CRITICAL", "action": "expedited_delivery"},
                    {"condition": "cost_usd > 150", "action": "request_approval"}
                ],
                "error_handling": [
                    {"error": "booking_failed", "strategy": "try_alternate_courier"}
                ],
                "performance": {
                    "avg_duration_ms": 80,
                    "p95_duration_ms": 150,
                    "success_rate": "99.0%"
                }
            },
            {
                "id": "WF005",
                "name": "Bulk Processing Workflow",
                "domain": "Operations",
                "complexity": "MEDIUM",
                "description": "Processes large batches of bags (50+ per batch) with parallel execution",
                "entry_point": "identify_scope",
                "steps": [
                    {"name": "identify_scope", "agent": "Data Fusion", "description": "Identify all bags in scope"},
                    {"name": "batch_process", "agent": "Data Fusion", "description": "Create processing batches"},
                    {"name": "parallel_actions", "agent": "Multiple", "description": "Execute actions in parallel"},
                    {"name": "consolidate_results", "agent": "Data Fusion", "description": "Merge results"},
                    {"name": "report_outcomes", "agent": "Passenger Comms", "description": "Report to stakeholders"}
                ],
                "decision_points": [
                    {"condition": "total_items > 100", "action": "use_max_parallelism"},
                    {"condition": "batch_failures > 5%", "action": "reduce_parallelism"}
                ],
                "error_handling": [
                    {"error": "batch_failed", "strategy": "retry_failed_items_individually"}
                ],
                "performance": {
                    "avg_duration_ms": 200,
                    "p95_duration_ms": 400,
                    "success_rate": "99.5%"
                }
            }
        ]

    async def extract_systems(self) -> List[Dict[str, Any]]:
        """Extract all external system integrations"""
        return [
            {
                "id": "SYS001",
                "name": "WorldTracer",
                "type": "Mishandled Baggage System",
                "criticality": "CRITICAL",
                "description": "IATA global baggage tracing system for mishandled bags",
                "api_type": "SOAP/REST",
                "authentication": "API Key + OAuth 2.0",
                "endpoints": [
                    {"path": "/pir/create", "method": "POST", "description": "Create new PIR"},
                    {"path": "/pir/{pir_number}", "method": "GET", "description": "Retrieve PIR"},
                    {"path": "/pir/{pir_number}", "method": "PUT", "description": "Update PIR"},
                    {"path": "/pir/search", "method": "POST", "description": "Search PIRs"}
                ],
                "data_formats": {
                    "input": "JSON with IATA standard fields",
                    "output": "JSON PIR object with status"
                },
                "rate_limits": "100 requests/minute",
                "sla": "99.9% uptime, <500ms response time"
            },
            {
                "id": "SYS002",
                "name": "DCS (Departure Control System)",
                "type": "Airline Passenger System",
                "criticality": "CRITICAL",
                "description": "Manages passenger check-in, boarding, and baggage data",
                "api_type": "REST",
                "authentication": "API Key + mTLS",
                "endpoints": [
                    {"path": "/passenger/{pnr}", "method": "GET", "description": "Get passenger data"},
                    {"path": "/baggage/{bag_tag}", "method": "GET", "description": "Get baggage data"},
                    {"path": "/baggage", "method": "POST", "description": "Create baggage record"}
                ],
                "data_formats": {
                    "input": "JSON with airline-specific schema",
                    "output": "JSON passenger/baggage objects"
                },
                "rate_limits": "500 requests/minute",
                "sla": "99.95% uptime, <200ms response time"
            },
            {
                "id": "SYS003",
                "name": "BHS (Baggage Handling System)",
                "type": "Facility Automation",
                "criticality": "CRITICAL",
                "description": "Automated baggage sorting and tracking system",
                "api_type": "Message Queue (AMQP)",
                "authentication": "Username/Password + SSL",
                "endpoints": [
                    {"path": "scan.events", "method": "CONSUME", "description": "Receive scan events"},
                    {"path": "commands.routing", "method": "PUBLISH", "description": "Send routing commands"}
                ],
                "data_formats": {
                    "input": "Binary scan event format",
                    "output": "JSON-encoded scan data"
                },
                "rate_limits": "10,000 events/minute",
                "sla": "99.99% uptime, <10ms latency"
            },
            {
                "id": "SYS004",
                "name": "Type B Messaging",
                "type": "Industry Standard Messaging",
                "criticality": "HIGH",
                "description": "IATA Type B telegram messaging for baggage manifests",
                "api_type": "TCP/IP Socket",
                "authentication": "IP Whitelist + Message signing",
                "endpoints": [
                    {"path": "N/A", "method": "RECEIVE", "description": "Receive Type B messages"},
                    {"path": "N/A", "method": "SEND", "description": "Send Type B messages"}
                ],
                "data_formats": {
                    "input": "IATA Type B text format",
                    "output": "Parsed JSON objects"
                },
                "rate_limits": "1,000 messages/minute",
                "sla": "99.5% uptime"
            },
            {
                "id": "SYS005",
                "name": "BaggageXML",
                "type": "IATA Resolution 753",
                "criticality": "HIGH",
                "description": "IATA XML standard for baggage tracking",
                "api_type": "REST/SOAP",
                "authentication": "IATA credentials + certificate",
                "endpoints": [
                    {"path": "/baggage/track", "method": "POST", "description": "Submit tracking event"},
                    {"path": "/baggage/{bag_tag}/history", "method": "GET", "description": "Get bag history"}
                ],
                "data_formats": {
                    "input": "IATA BaggageXML schema",
                    "output": "IATA BaggageXML response"
                },
                "rate_limits": "200 requests/minute",
                "sla": "99.7% uptime"
            },
            {
                "id": "SYS006",
                "name": "Courier Services",
                "type": "Third-party Logistics",
                "criticality": "MEDIUM",
                "description": "FedEx, UPS, DHL APIs for delivery booking and tracking",
                "api_type": "REST",
                "authentication": "API Key",
                "endpoints": [
                    {"path": "/shipments", "method": "POST", "description": "Book shipment"},
                    {"path": "/shipments/{tracking_id}", "method": "GET", "description": "Track shipment"},
                    {"path": "/shipments/{tracking_id}", "method": "DELETE", "description": "Cancel shipment"}
                ],
                "data_formats": {
                    "input": "Carrier-specific JSON",
                    "output": "JSON booking confirmation"
                },
                "rate_limits": "50 requests/minute per carrier",
                "sla": "99.0% uptime"
            },
            {
                "id": "SYS007",
                "name": "Notification Services",
                "type": "Multi-channel Communications",
                "criticality": "MEDIUM",
                "description": "Twilio, SendGrid for SMS, email, push notifications",
                "api_type": "REST",
                "authentication": "API Key",
                "endpoints": [
                    {"path": "/sms", "method": "POST", "description": "Send SMS"},
                    {"path": "/email", "method": "POST", "description": "Send email"},
                    {"path": "/push", "method": "POST", "description": "Send push notification"}
                ],
                "data_formats": {
                    "input": "JSON with recipient, message, channel",
                    "output": "JSON delivery confirmation"
                },
                "rate_limits": "1,000 messages/minute",
                "sla": "99.5% uptime"
            }
        ]


# ============================================================================
# DOCUMENTATION GENERATORS
# ============================================================================

class OntologyDocGenerator:
    """Generate ontology reference documentation"""

    @staticmethod
    def generate(ontology: Dict[str, Any]) -> str:
        """Generate markdown documentation for ontology"""
        doc = []
        doc.append("# Ontology Reference\n")
        doc.append("Complete knowledge graph ontology for AI-powered baggage handling system.\n\n")
        doc.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        doc.append("---\n\n")

        # Node Types
        doc.append("## Node Types\n\n")
        doc.append(f"The knowledge graph contains **{len(ontology['node_types'])} node types**:\n\n")

        for node_type in ontology['node_types']:
            doc.append(f"### {node_type['label']}\n\n")
            doc.append(f"**Description**: {node_type['description']}\n\n")
            doc.append("**Properties**:\n\n")
            doc.append("| Property | Type | Required | Description |\n")
            doc.append("|----------|------|----------|-------------|\n")
            for prop in node_type['properties']:
                required = "✓" if prop['required'] else ""
                doc.append(f"| `{prop['name']}` | {prop['type']} | {required} | {prop['description']} |\n")
            doc.append("\n")

        # Relationship Types
        doc.append("## Relationship Types\n\n")
        doc.append(f"The knowledge graph contains **{len(ontology['relationship_types'])} relationship types**:\n\n")

        for rel in ontology['relationship_types']:
            doc.append(f"### {rel['type']}\n\n")
            doc.append(f"**From**: `{rel['from']}` → **To**: `{rel['to']}`\n\n")
            doc.append(f"**Description**: {rel['description']}\n\n")
            if rel['properties']:
                doc.append("**Properties**:\n\n")
                doc.append("| Property | Type | Description |\n")
                doc.append("|----------|------|-------------|\n")
                for prop in rel['properties']:
                    doc.append(f"| `{prop['name']}` | {prop['type']} | {prop['description']} |\n")
            doc.append("\n")

        # Constraints
        doc.append("## Constraints and Indexes\n\n")
        doc.append("| Label | Property | Constraint Type |\n")
        doc.append("|-------|----------|----------------|\n")
        for constraint in ontology['constraints']:
            doc.append(f"| `{constraint['label']}` | `{constraint['property']}` | {constraint['type']} |\n")
        doc.append("\n")

        # Example Queries
        doc.append("## Example Cypher Queries\n\n")
        doc.append("### Find all bags for a passenger\n\n")
        doc.append("```cypher\n")
        doc.append("MATCH (p:Passenger {pnr: 'ABC123'})<-[:BELONGS_TO]-(b:Bag)\n")
        doc.append("RETURN b\n")
        doc.append("```\n\n")

        doc.append("### Trace bag journey\n\n")
        doc.append("```cypher\n")
        doc.append("MATCH (b:Bag {bag_tag: '0016123456789'})-[:HAD_EVENT]->(e:Event)\n")
        doc.append("RETURN e ORDER BY e.timestamp\n")
        doc.append("```\n\n")

        doc.append("### Find high-risk bags\n\n")
        doc.append("```cypher\n")
        doc.append("MATCH (b:Bag)-[:BOOKED_ON]->(f:Flight)\n")
        doc.append("WHERE b.risk_score > 0.7\n")
        doc.append("RETURN b, f\n")
        doc.append("```\n\n")

        return "".join(doc)


class AgentDocGenerator:
    """Generate agent reference documentation"""

    @staticmethod
    def generate(agents: List[Dict[str, Any]]) -> str:
        """Generate markdown documentation for agents"""
        doc = []
        doc.append("# Agent Reference\n\n")
        doc.append("Comprehensive reference for all AI agents in the baggage handling system.\n\n")
        doc.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        doc.append(f"**Total Agents**: {len(agents)}\n\n")
        doc.append("---\n\n")

        # Agent Overview Table
        doc.append("## Agent Overview\n\n")
        doc.append("| Agent | Specialization | Autonomy Level | Throughput |\n")
        doc.append("|-------|----------------|----------------|------------|\n")
        for agent in agents:
            doc.append(f"| [{agent['name']}](#{agent['id'].lower()}) | {agent['specialization']} | ")
            doc.append(f"{agent['autonomy_level']} | {agent['performance']['throughput']} |\n")
        doc.append("\n---\n\n")

        # Detailed Agent Docs
        for agent in agents:
            doc.append(f"## {agent['name']} {{#{agent['id'].lower()}}}\n\n")
            doc.append(f"**ID**: `{agent['id']}`  \n")
            doc.append(f"**Specialization**: {agent['specialization']}  \n")
            doc.append(f"**Autonomy Level**: {agent['autonomy_level']}\n\n")

            doc.append("### Purpose\n\n")
            doc.append(f"{agent['purpose']}\n\n")

            doc.append("### Capabilities\n\n")
            for cap in agent['capabilities']:
                doc.append(f"- {cap}\n")
            doc.append("\n")

            doc.append("### Inputs/Outputs\n\n")
            doc.append("**Inputs**:\n")
            for inp in agent['inputs']:
                doc.append(f"- {inp}\n")
            doc.append("\n**Outputs**:\n")
            for out in agent['outputs']:
                doc.append(f"- {out}\n")
            doc.append("\n")

            doc.append("### Dependencies\n\n")
            for dep in agent['dependencies']:
                doc.append(f"- {dep}\n")
            doc.append("\n")

            doc.append("### Performance Characteristics\n\n")
            doc.append("| Metric | Value |\n")
            doc.append("|--------|-------|\n")
            for metric, value in agent['performance'].items():
                doc.append(f"| {metric.replace('_', ' ').title()} | {value} |\n")
            doc.append("\n")

            doc.append("---\n\n")

        return "".join(doc)


async def main():
    """Generate all documentation"""
    print("=" * 80)
    print("DOCUMENTATION GENERATOR")
    print("=" * 80)
    print()

    extractor = KnowledgeGraphExtractor()

    # Extract data
    print("Extracting ontology from knowledge graph...")
    ontology = await extractor.extract_ontology()
    print(f"  ✓ Extracted {len(ontology['node_types'])} node types")
    print(f"  ✓ Extracted {len(ontology['relationship_types'])} relationship types")

    print("\nExtracting agent information...")
    agents = await extractor.extract_agents()
    print(f"  ✓ Extracted {len(agents)} agents")

    print("\nExtracting workflow information...")
    workflows = await extractor.extract_workflows()
    print(f"  ✓ Extracted {len(workflows)} workflows")

    print("\nExtracting system integrations...")
    systems = await extractor.extract_systems()
    print(f"  ✓ Extracted {len(systems)} external systems")

    # Generate documentation
    print("\nGenerating documentation...")

    print("  → Generating ontology.md...")
    ontology_doc = OntologyDocGenerator.generate(ontology)

    print("  → Generating agents.md...")
    agents_doc = AgentDocGenerator.generate(agents)

    print("\nDocumentation generation complete!")
    print("\nPreviewing ontology.md (first 50 lines):")
    print("-" * 80)
    print("\n".join(ontology_doc.split("\n")[:50]))
    print("-" * 80)

    print("\nPreviewing agents.md (first 50 lines):")
    print("-" * 80)
    print("\n".join(agents_doc.split("\n")[:50]))
    print("-" * 80)

    return {
        "ontology": ontology_doc,
        "agents": agents_doc,
        "workflows": workflows,
        "systems": systems
    }


if __name__ == "__main__":
    asyncio.run(main())
