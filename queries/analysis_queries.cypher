// ============================================================================
// KNOWLEDGE GRAPH ANALYSIS QUERIES
// ============================================================================
// Version: 1.0.0
// Date: 2025-11-14
//
// Analytical queries for insights and metrics
// ============================================================================


// ----------------------------------------------------------------------------
// 1. AUTOMATION READINESS SCORE
// ----------------------------------------------------------------------------
// Calculate overall automation readiness for each workflow

MATCH (w:Workflow)
OPTIONAL MATCH (w)<-[:HANDLES]-(a:Agent)
WITH w,
     w.automation_potential AS potential,
     count(a) AS agent_count,
     CASE
       WHEN w.complexity = 'LOW' THEN 1.0
       WHEN w.complexity = 'MEDIUM' THEN 0.8
       WHEN w.complexity = 'HIGH' THEN 0.6
       WHEN w.complexity = 'CRITICAL' THEN 0.4
       ELSE 0.5
     END AS complexity_factor
RETURN w.name AS workflow,
       w.complexity AS complexity,
       potential AS automation_potential,
       agent_count,
       (potential * 0.6 + complexity_factor * 0.2 + CASE WHEN agent_count > 0 THEN 0.2 ELSE 0 END) AS readiness_score
ORDER BY readiness_score DESC


// ----------------------------------------------------------------------------
// 2. AGENT COLLABORATION PATTERNS
// ----------------------------------------------------------------------------
// Find which agents frequently collaborate

MATCH (a1:Agent)-[:HANDLES]->(w:Workflow)<-[:HANDLES]-(a2:Agent)
WHERE id(a1) < id(a2)
WITH a1, a2, count(w) AS shared_workflows
WHERE shared_workflows > 0
RETURN a1.name AS agent1,
       a2.name AS agent2,
       shared_workflows,
       collect(w.name) AS workflows
ORDER BY shared_workflows DESC


// ----------------------------------------------------------------------------
// 3. SYSTEM INTEGRATION BOTTLENECKS
// ----------------------------------------------------------------------------
// Identify systems that are critical integration points

MATCH (s:System)<-[:INTEGRATES_WITH]-(a:Agent)-[:HANDLES]->(w:Workflow)
WITH s, count(DISTINCT a) AS agent_count, count(DISTINCT w) AS workflow_count
RETURN s.name AS system,
       s.vendor AS vendor,
       agent_count,
       workflow_count,
       (agent_count * workflow_count) AS criticality_score
ORDER BY criticality_score DESC


// ----------------------------------------------------------------------------
// 4. WORKFLOW DEPENDENCY DEPTH
// ----------------------------------------------------------------------------
// Calculate dependency depth for each workflow

MATCH (w:Workflow)
OPTIONAL MATCH path = (w)-[:DEPENDS_ON*]->(dep:Workflow)
WITH w, max(length(path)) AS max_depth
RETURN w.name AS workflow,
       w.complexity AS complexity,
       COALESCE(max_depth, 0) AS dependency_depth
ORDER BY dependency_depth DESC


// ----------------------------------------------------------------------------
// 5. AGENT CAPABILITY GAP ANALYSIS
// ----------------------------------------------------------------------------
// Find workflows with insufficient agent coverage

MATCH (w:Workflow)
OPTIONAL MATCH (w)<-[:HANDLES]-(a:Agent)
WITH w, count(a) AS agent_count
WHERE agent_count < 2 AND w.complexity IN ['HIGH', 'CRITICAL']
RETURN w.name AS workflow,
       w.complexity AS complexity,
       agent_count,
       'NEEDS MORE AGENTS' AS recommendation
ORDER BY agent_count ASC


// ----------------------------------------------------------------------------
// 6. REGULATORY COMPLIANCE COVERAGE
// ----------------------------------------------------------------------------
// Check which workflows need regulatory mappings

MATCH (w:Workflow)
OPTIONAL MATCH (w)-[:COMPLIES_WITH]->(r:Regulation)
WITH w, count(r) AS regulation_count
RETURN w.name AS workflow,
       w.complexity AS complexity,
       regulation_count,
       CASE
         WHEN regulation_count = 0 THEN 'NEEDS COMPLIANCE REVIEW'
         WHEN regulation_count >= 1 THEN 'COMPLIANT'
       END AS status
ORDER BY regulation_count ASC


// ----------------------------------------------------------------------------
// 7. STAKEHOLDER IMPACT ANALYSIS
// ----------------------------------------------------------------------------
// Measure stakeholder coverage across workflows

MATCH (s:Stakeholder)
OPTIONAL MATCH (s)<-[:SERVES]-(w:Workflow)
WITH s, count(w) AS workflow_count
RETURN s.name AS stakeholder,
       s.type AS type,
       s.priority AS priority,
       workflow_count
ORDER BY s.priority DESC, workflow_count ASC


// ----------------------------------------------------------------------------
// 8. AGENT TYPE DISTRIBUTION
// ----------------------------------------------------------------------------
// Analyze agent type distribution

MATCH (a:Agent)
RETURN a.type AS agent_type,
       count(a) AS count,
       collect(a.name) AS agents
ORDER BY count DESC


// ----------------------------------------------------------------------------
// 9. CRITICAL PATH IDENTIFICATION
// ----------------------------------------------------------------------------
// Find the longest dependency chains

MATCH path = (start:Workflow)-[:DEPENDS_ON*]->(end:Workflow)
WHERE NOT (start)-[:DEPENDS_ON]->()  // start has no incoming dependencies
  AND NOT ()-[:DEPENDS_ON]->(end)    // end has no outgoing dependencies
WITH path, length(path) AS path_length
ORDER BY path_length DESC
LIMIT 5
RETURN [n IN nodes(path) | n.name] AS workflow_chain,
       path_length


// ----------------------------------------------------------------------------
// 10. SYSTEM VENDOR ANALYSIS
// ----------------------------------------------------------------------------
// Analyze vendor distribution and dependencies

MATCH (s:System)
RETURN s.vendor AS vendor,
       count(s) AS system_count,
       collect(s.name) AS systems
ORDER BY system_count DESC


// ----------------------------------------------------------------------------
// 11. WORKFLOW COMPLEXITY DISTRIBUTION
// ----------------------------------------------------------------------------
// Analyze workflow complexity distribution

MATCH (w:Workflow)
RETURN w.complexity AS complexity,
       count(w) AS count,
       avg(w.automation_potential) AS avg_automation_potential
ORDER BY
  CASE w.complexity
    WHEN 'LOW' THEN 1
    WHEN 'MEDIUM' THEN 2
    WHEN 'HIGH' THEN 3
    WHEN 'CRITICAL' THEN 4
  END


// ----------------------------------------------------------------------------
// 12. AGENT EFFICIENCY SCORE
// ----------------------------------------------------------------------------
// Calculate efficiency score based on workflow coverage

MATCH (a:Agent)-[:HANDLES]->(w:Workflow)
WITH a, count(w) AS workflow_count, collect(w.complexity) AS complexities
RETURN a.name AS agent,
       a.type AS type,
       workflow_count,
       size([c IN complexities WHERE c IN ['HIGH', 'CRITICAL']]) AS critical_workflows,
       (workflow_count * 10 + size([c IN complexities WHERE c IN ['HIGH', 'CRITICAL']]) * 5) AS efficiency_score
ORDER BY efficiency_score DESC


// ----------------------------------------------------------------------------
// 13. INTEGRATION COMPLEXITY MATRIX
// ----------------------------------------------------------------------------
// Show integration complexity per agent-system pair

MATCH (a:Agent)-[:INTEGRATES_WITH]->(s:System)
MATCH (a)-[:HANDLES]->(w:Workflow)
WITH a, s, count(DISTINCT w) AS workflow_count
RETURN a.name AS agent,
       s.name AS system,
       workflow_count,
       workflow_count * 2 AS integration_complexity
ORDER BY integration_complexity DESC


// ----------------------------------------------------------------------------
// 14. ORPHANED NODE DETECTION
// ----------------------------------------------------------------------------
// Find nodes with no relationships

MATCH (n)
WHERE NOT (n)--()
RETURN labels(n)[0] AS node_type,
       n.name AS name,
       n.id AS id


// ----------------------------------------------------------------------------
// 15. GRAPH DENSITY METRICS
// ----------------------------------------------------------------------------
// Calculate graph density and connectivity

MATCH (n)
WITH count(n) AS node_count
MATCH ()-[r]->()
WITH node_count, count(r) AS rel_count
RETURN node_count AS total_nodes,
       rel_count AS total_relationships,
       toFloat(rel_count) / (node_count * (node_count - 1)) AS graph_density,
       toFloat(rel_count) / node_count AS avg_degree


// ----------------------------------------------------------------------------
// 16. WORKFLOW PRIORITIZATION
// ----------------------------------------------------------------------------
// Prioritize workflows for automation investment

MATCH (w:Workflow)
OPTIONAL MATCH (w)-[:SERVES]->(s:Stakeholder)
OPTIONAL MATCH (w)<-[:HANDLES]-(a:Agent)
WITH w,
     count(DISTINCT s) AS stakeholder_count,
     count(DISTINCT a) AS agent_count,
     max(CASE s.priority WHEN 'HIGH' THEN 3 WHEN 'MEDIUM' THEN 2 ELSE 1 END) AS max_priority
RETURN w.name AS workflow,
       w.complexity AS complexity,
       w.automation_potential AS automation_potential,
       stakeholder_count,
       agent_count,
       (w.automation_potential * 0.4 + stakeholder_count * 0.3 + max_priority * 0.3) AS investment_priority
ORDER BY investment_priority DESC


// ----------------------------------------------------------------------------
// 17. TECHNOLOGY STACK ANALYSIS
// ----------------------------------------------------------------------------
// Analyze technology vendor dependencies

MATCH (s:System)
OPTIONAL MATCH (s)<-[:INTEGRATES_WITH]-(a:Agent)
WITH s.vendor AS vendor, count(DISTINCT s) AS systems, count(DISTINCT a) AS agents
RETURN vendor,
       systems,
       agents,
       systems + agents AS total_dependencies
ORDER BY total_dependencies DESC


// ----------------------------------------------------------------------------
// 18. SINGLE POINT OF FAILURE ANALYSIS
// ----------------------------------------------------------------------------
// Identify critical single points of failure

MATCH (a:Agent)-[:HANDLES]->(w:Workflow)
WHERE w.complexity IN ['HIGH', 'CRITICAL']
WITH w, count(a) AS agent_count
WHERE agent_count = 1
MATCH (w)<-[:HANDLES]-(a:Agent)
RETURN w.name AS workflow,
       w.complexity AS complexity,
       a.name AS single_agent,
       'SINGLE POINT OF FAILURE' AS risk
ORDER BY w.complexity DESC


// ----------------------------------------------------------------------------
// 19. COMPLIANCE GAP ANALYSIS
// ----------------------------------------------------------------------------
// Find compliance gaps by regulation authority

MATCH (r:Regulation)
OPTIONAL MATCH (r)<-[:COMPLIES_WITH]-(w:Workflow)
WITH r, count(w) AS workflow_count
RETURN r.authority AS authority,
       count(r) AS total_regulations,
       sum(workflow_count) AS compliant_workflows,
       CASE WHEN sum(workflow_count) = 0 THEN 'CRITICAL GAP' ELSE 'PARTIAL COVERAGE' END AS status
ORDER BY sum(workflow_count) ASC


// ----------------------------------------------------------------------------
// 20. AGENT WORKLOAD BALANCE
// ----------------------------------------------------------------------------
// Analyze workload balance across agents

MATCH (a:Agent)-[:HANDLES]->(w:Workflow)
WITH count(w) AS workflow_count
WITH avg(workflow_count) AS avg_workload, stdev(workflow_count) AS workload_stdev
MATCH (a:Agent)-[:HANDLES]->(w:Workflow)
WITH a, count(w) AS agent_workload, avg_workload, workload_stdev
RETURN a.name AS agent,
       a.type AS type,
       agent_workload,
       round(avg_workload, 2) AS avg_workload,
       CASE
         WHEN agent_workload > avg_workload + workload_stdev THEN 'OVERLOADED'
         WHEN agent_workload < avg_workload - workload_stdev THEN 'UNDERUTILIZED'
         ELSE 'BALANCED'
       END AS workload_status
ORDER BY agent_workload DESC
