// ============================================================================
// KNOWLEDGE GRAPH VISUALIZATION QUERIES
// ============================================================================
// Version: 1.0.0
// Date: 2025-11-14
//
// These queries can be run in Neo4j Browser for visualization
// ============================================================================


// ----------------------------------------------------------------------------
// 1. COMPLETE WORKFLOW GRAPH
// ----------------------------------------------------------------------------
// Show all workflows and their dependencies

MATCH (w1:Workflow)-[r:DEPENDS_ON]->(w2:Workflow)
RETURN w1, r, w2


// ----------------------------------------------------------------------------
// 2. AGENT COLLABORATION NETWORK
// ----------------------------------------------------------------------------
// Show which agents work together on workflows

MATCH (a1:Agent)-[:HANDLES]->(w:Workflow)<-[:HANDLES]-(a2:Agent)
WHERE id(a1) < id(a2)  // Avoid duplicates
RETURN a1, w, a2


// ----------------------------------------------------------------------------
// 3. SYSTEM INTEGRATION MAP
// ----------------------------------------------------------------------------
// Show how agents integrate with external systems

MATCH (a:Agent)-[r:INTEGRATES_WITH]->(s:System)
RETURN a, r, s


// ----------------------------------------------------------------------------
// 4. COMPLETE ECOSYSTEM VIEW
// ----------------------------------------------------------------------------
// Show workflows, agents, systems, and stakeholders

MATCH path = (w:Workflow)<-[:HANDLES]-(a:Agent)-[:INTEGRATES_WITH]->(s:System)
OPTIONAL MATCH (w)-[:SERVES]->(st:Stakeholder)
RETURN w, a, s, st
LIMIT 50


// ----------------------------------------------------------------------------
// 5. EXCEPTION HANDLING WORKFLOW
// ----------------------------------------------------------------------------
// Focus on exception handling with all connected entities

MATCH (w:Workflow {name: 'Exception Handling'})
OPTIONAL MATCH (w)<-[:HANDLES]-(a:Agent)
OPTIONAL MATCH (a)-[:INTEGRATES_WITH]->(s:System)
OPTIONAL MATCH (w)-[:SERVES]->(st:Stakeholder)
OPTIONAL MATCH (w)-[:COMPLIES_WITH]->(r:Regulation)
RETURN w, a, s, st, r


// ----------------------------------------------------------------------------
// 6. CRITICAL PATH ANALYSIS
// ----------------------------------------------------------------------------
// Show high and critical complexity workflows

MATCH (w:Workflow)
WHERE w.complexity IN ['HIGH', 'CRITICAL']
OPTIONAL MATCH (w)<-[:HANDLES]-(a:Agent)
OPTIONAL MATCH (w)-[dep:DEPENDS_ON]->(w2:Workflow)
RETURN w, a, dep, w2


// ----------------------------------------------------------------------------
// 7. AGENT CAPABILITY MAP
// ----------------------------------------------------------------------------
// Show agents grouped by type with their workflows

MATCH (a:Agent)-[:HANDLES]->(w:Workflow)
RETURN a.type AS agent_type,
       collect(DISTINCT a.name) AS agents,
       collect(DISTINCT w.name) AS workflows
ORDER BY agent_type


// ----------------------------------------------------------------------------
// 8. REGULATORY COMPLIANCE VIEW
// ----------------------------------------------------------------------------
// Show which workflows comply with which regulations

MATCH (w:Workflow)-[r:COMPLIES_WITH]->(reg:Regulation)
RETURN w, r, reg


// ----------------------------------------------------------------------------
// 9. AUTOMATION OPPORTUNITY HEATMAP
// ----------------------------------------------------------------------------
// Show workflows colored by automation potential

MATCH (w:Workflow)
RETURN w.name AS workflow,
       w.complexity AS complexity,
       w.automation_potential AS automation_potential,
       w.agent_coverage AS agent_coverage
ORDER BY w.automation_potential DESC


// ----------------------------------------------------------------------------
// 10. STAKEHOLDER IMPACT MAP
// ----------------------------------------------------------------------------
// Show which workflows serve which stakeholders

MATCH (w:Workflow)-[r:SERVES]->(s:Stakeholder)
RETURN w, r, s


// ============================================================================
// ADVANCED VISUALIZATIONS
// ============================================================================


// ----------------------------------------------------------------------------
// 11. SHORTEST PATH BETWEEN WORKFLOWS
// ----------------------------------------------------------------------------
// Find shortest dependency path between two workflows

MATCH path = shortestPath(
  (start:Workflow {id: 'WF001'})-[:DEPENDS_ON*]-(end:Workflow {id: 'WF005'})
)
RETURN path


// ----------------------------------------------------------------------------
// 12. AGENT WORKLOAD DISTRIBUTION
// ----------------------------------------------------------------------------
// Show how many workflows each agent handles

MATCH (a:Agent)-[:HANDLES]->(w:Workflow)
WITH a, count(w) AS workflow_count
RETURN a.name AS agent,
       a.type AS type,
       workflow_count
ORDER BY workflow_count DESC


// ----------------------------------------------------------------------------
// 13. SYSTEM INTEGRATION COMPLEXITY
// ----------------------------------------------------------------------------
// Show which systems are integrated with most agents

MATCH (s:System)<-[:INTEGRATES_WITH]-(a:Agent)
WITH s, count(a) AS agent_count
RETURN s.name AS system,
       s.vendor AS vendor,
       agent_count
ORDER BY agent_count DESC


// ----------------------------------------------------------------------------
// 14. WORKFLOW DEPENDENCY TREE
// ----------------------------------------------------------------------------
// Show dependency tree starting from check-in

MATCH path = (start:Workflow {id: 'WF001'})<-[:DEPENDS_ON*0..5]-(dependent:Workflow)
RETURN path


// ----------------------------------------------------------------------------
// 15. HIGH-PRIORITY STAKEHOLDER WORKFLOWS
// ----------------------------------------------------------------------------
// Show workflows serving high-priority stakeholders

MATCH (w:Workflow)-[:SERVES]->(s:Stakeholder {priority: 'HIGH'})
OPTIONAL MATCH (w)<-[:HANDLES]-(a:Agent)
RETURN w, s, a
