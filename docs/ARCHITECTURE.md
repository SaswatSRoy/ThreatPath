# ThreatPath Architecture Specification

## 1. Executive Summary & Problem Statement

In modern Enterprise Security Operations Centers (SOCs), analysts face thousands of disconnected security alerts daily. Traditional Security Information and Event Management (SIEM) systems treat alerts as isolated textual logs. When an alert fires (such as an off-hours login or an encoded execution command), determining whether it represents an active intrusion requires manual multi-hop correlation across hosts, process trees, network indicators, vulnerability scans, and critical asset databases.

**ThreatPath** is a graph-native defensive security investigation agent engineered for **Graph Hacks 2026 (Track 01: Agents That Act on Connected Data)**. Built directly on **FalkorDB**, ThreatPath traverses multi-hop causal chains to differentiate between true compromises, benign anomalies, and unexploited vulnerabilities. It couples FalkorDB graph traversals with deterministic scoring, evidence-grounded reasoning, human-in-the-loop approval gates, and verified simulated response actions.

---

## 2. Architectural Blueprint

ThreatPath is implemented as a cohesive, high-performance modular monolith:

```
+-----------------------------------------------------------------------------------------+
|                                    THREATPATH WORKSPACE                                  |
|                                                                                         |
|  +--------------------+         +-----------------------+         +-------------------+ |
|  |   Alert Queue &    |         | Interactive Evidence  |         |   Deterministic   | |
|  | Scenario Selector  | ------> |     Graph Canvas      | ------> | Assessment Engine | |
|  |  (A, B, C, D)      |         |    (Cytoscape.js)     |         |    & Scoring      | |
|  +--------------------+         +-----------------------+         +-------------------+ |
|                                                                             |           |
|                                                                             v           |
|  +--------------------+         +-----------------------+         +-------------------+ |
|  | Verification Check | <------ |  Simulated Execution  | <------ | Human-in-the-Loop | |
|  | (Host Isolated)    |         |   (Sandboxed Fleet)   |         |   Approval Gate   | |
|  +--------------------+         +-----------------------+         +-------------------+ |
+-----------------------------------------------------------------------------|-----------+
                                                                              |
                                     FastAPI REST API / MCP Protocol          |
                                     (127.0.0.1:8000 / stdio)                 |
                                                                              v
+-----------------------------------------------------------------------------------------+
|                                   BACKEND ENGINE                                        |
|                                                                                         |
|   +-----------------------+   +------------------------+   +------------------------+   |
|   |  Autonomous Agent     |   | FalkorDB-Native Tools  |   | Response Policy Engine |   |
|   |  Orchestrator         |   | & Official MCP Server  |   | (ALLOW / APPROVE / BLK)|   |
|   +-----------------------+   +------------------------+   +------------------------+   |
|               |                           |                                             |
|               +---------------------------+                                             |
|                                           |                                             |
|                                           v                                             |
|                      +-----------------------------------------+                        |
|                      | Parameterized Cypher Traversal Engine   |                        |
|                      +-----------------------------------------+                        |
+-------------------------------------------|---------------------------------------------+
                                            |
                                            | falkordb-py client
                                            | Production: tcp falkordb-server.railway.internal:6379
                                            | Local Dev:   tcp 127.0.0.1:6379
                                            v
+-----------------------------------------------------------------------------------------+
|                                  FALKORDB ENGINE                                        |
|                                                                                         |
|      Dedicated Database Graphs:                                                         |
|        • [ threatpath_demo ] : Production demonstration graph on Railway                |
|        • [ threatpath_dev  ] : Local development environment                            |
|                                                                                         |
|      (Alert) --> [:HAS_EVENT] --> (Event) --> [:OCCURRED_ON] --> (Host)                 |
|                                     |                             |                     |
|                                     v                             v                     |
|                               (Technique)                     (Process)                 |
|                                                                   |                     |
|                                                                   v                     |
|                                                              (Indicator)                |
|                                                                                         |
|      Preserved Practice Data: [ social ] (Untouched on local container)                 |
+-----------------------------------------------------------------------------------------+
```

**Live Deployed Application:** [https://threatpath-production.up.railway.app](https://threatpath-production.up.railway.app)  
**Source Repository:** [https://github.com/SaswatSRoy/ThreatPath](https://github.com/SaswatSRoy/ThreatPath)

---

## 3. Core Component Responsibilities

### 3.1 Autonomous Agent Orchestrator (`backend/agent/orchestrator.py`)
- **Input Validation**: Sanitizes and resolves requested `alert_id`.
- **Tool-Based Traversal**: Dispatches domain-specific FalkorDB queries (`get_alert_context`, `trace_attack_path`, `check_asset_exposure`, `get_vulnerability_exposure`, `get_related_alerts`).
- **Graph Normalization**: Compiles discovered subgraphs into deduplicated nodes and edges for Cytoscape.js visualization.
- **Deterministic Assessment**: Evaluates heuristic factor weights without LLM hallucination.
- **Provenance Persistence**: Persists `Investigation` and `ResponseAction` nodes directly into FalkorDB.

### 3.2 FalkorDB Query Engine (`backend/cypher_queries.py` & `cypher/`)
- All Cypher statements are stored in `cypher/` and executed with parameterization.
- Traversal depth is strictly bounded (`[*1..4]`) with sub-millisecond execution times.
- Result sets are converted from FalkorDB `Path`, `Node`, and `Edge` objects into structured domain models.

### 3.3 Deterministic Assessment & Scoring Engine (`backend/scoring.py`)
- Eliminates non-deterministic LLM scoring.
- Classifies incidents into `likely_compromise`, `suspicious`, or `insufficient_evidence`.
- Determines `remediation_priority` (`critical`, `high`, `medium`, `low`) by correlating host access paths to high-value assets (`asset-customer-db`).
- Crucial Security Rule: **Distinguishes vulnerability from exploitation**. The presence of a known vulnerability (e.g. CVE-2023-50164, CISA KEV) elevates remediation priority but remains `suspicious` unless corroborating execution/beaconing paths exist.

### 3.4 Response Policy, Approval Gate & Simulation Verifier (`backend/policy.py`)
- **Safety Boundary**: Never interacts with production infrastructure; mutates a sandboxed fleet simulation.
- **Policy Engine**: High-consequence actions (`SIMULATE_ISOLATE_HOST`, `SIMULATE_DISABLE_ACCOUNT`) return `REQUIRE_APPROVAL` and enter `WAITING_FOR_APPROVAL`.
- **Enforcement**: Any unapproved execution attempt raises `PermissionError` (HTTP 403).
- **Verification Engine**: After execution, inspects the simulated host telemetry to verify `network_state == "isolated"`. Transitions to `VERIFIED` only upon successful inspection.

### 3.5 Model Context Protocol (MCP) Integration (`backend/agent/mcp_server.py`)
- Genuine MCP server implementation using the official `mcp` SDK (`mcp.server.mcpserver.MCPServer`).
- Exposes 8 domain-specific defensive tools over standard stdio / SSE transport.
- Tested and verified without requiring an active external LLM.

### 3.6 Frontend Investigation Workspace (`frontend/`)
- Built with React, Vite, TypeScript, and Cytoscape.js.
- Cyber dark-mode aesthetics with real-time graph visualization, interactive node inspector, multi-hop proof path inspection, and one-click approval controls.

### 3.7 Persistence Architecture & State Durability
- **Investigation Provenance**: Completed investigations and recommended actions are persisted into FalkorDB via `cypher/provenance.cypher` as `(inv:Investigation)-[:INVESTIGATES]->(a:Alert)` and `(inv)-[:RECOMMENDED_ACTION]->(ra:ResponseAction)`. If the web container restarts or memory cache clears, past investigations reload reliably from FalkorDB.
- **Evidence Subgraph Cleanliness**: Historical `Investigation` and `ResponseAction` nodes are preserved for provenance, but are strictly excluded from the active evidence topology displayed in the frontend graph canvas.
- **Simulated Fleet Durability**: Defensive actions update simulated host telemetry (e.g. `network_state: isolated`). Simulation state is persisted in FalkorDB and synchronized to `/app/data/simulated_state.json`. On container restarts, simulated containment states survive intact.
- **Multi-Judge Session Isolation**: HTTP endpoints support `X-Session-ID` headers to isolate in-memory simulation state across distinct user sessions, preventing judges from colliding during evaluations.

### 3.8 Custom Scenario Lab & Safe Ingestion Engine (`backend/scenarios/`)
- **Offline Schema & Domain Validator (`backend/scenarios/validator.py`)**: Pure validator that strictly checks schema version `1.0`, mandatory fields, ID uniqueness, allowed node labels (`ALLOWED_NODE_LABELS`), allowed relationship types (`ALLOWED_RELATIONSHIPS`), and relationship endpoint constraints (`RELATIONSHIP_ENDPOINT_CONSTRAINTS`). Generates actionable error and warning lists without touching the database.
- **Client-Side Graph Preview Generation**: Converts validated entities and relationships into normalized Cytoscape `GraphData` during validation, allowing the frontend to render the proposed topology without mutating the live FalkorDB graph.
- **Safe Parameterized Persistence (`backend/scenarios/service.py`)**: Persists custom scenarios idempotently using server-side allowlists for labels and relationship types. All property values and identifiers are passed as query parameters (`$props`, `$alert_id`, `$session_id`), eliminating Cypher injection risks.
- **Session-Scoped Scenario Ownership**: Custom alerts and scenarios are tagged with the author's `session_id` (derived from `X-Session-ID`). Seeded alerts remain global (`session_id IS NULL`), while custom scenarios are strictly scoped to the authoring session during scenario listing, alert selection, and graph traversal.
- **Investigation Pipeline Integration**: Custom scenarios are investigated through the existing `Orchestrator` and deterministic scoring engine, ensuring custom alerts follow the identical multi-hop causal reasoning pipeline.

