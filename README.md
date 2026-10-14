# ThreatPath: Graph-Native Defensive Security Investigation Agent

[![Graph Hacks 2026](https://img.shields.io/badge/Graph_Hacks_2026-Track_01:_Agents_That_Act_on_Connected_Data-0284c7?style=for-the-badge)](https://graphhacks.devpost.com/)
[![Database: FalkorDB](https://img.shields.io/badge/Database-FalkorDB_Edge-c084fc?style=for-the-badge&logo=redis)](https://docs.falkordb.com/)
[![Tests: 24 Passed](https://img.shields.io/badge/Tests-24_Passed_(100%25)-10b981?style=for-the-badge)](tests/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge)](LICENSE)

> **ThreatPath** is an autonomous defensive security investigation agent built natively on **FalkorDB** for **Graph Hacks 2026 (Track 01 — Agents That Act on Connected Data)**. It investigates suspicious security alerts by traversing multi-hop causal paths across identities, events, hosts, process trees, network indicators, MITRE ATT&CK techniques, known exploited vulnerabilities (CISA KEV), and critical business assets.

---

## 1. Primary Track Declaration
- **Track**: **Track 01 — Agents That Act on Connected Data**
- **Core Proof**: ThreatPath proves that FalkorDB graph traversals directly dictate the investigation outcome, classification, and defensive response. The system includes a mandatory **Graph-Ablation Test** proving that removing a physical graph edge in FalkorDB directly alters the security assessment.

---

## 2. Key Features

- **Multi-Hop Evidence Traversal**: Automatically follows causal relationships from alerts through events, hosts, process executions, and external C2 indicators.
- **Deterministic Heuristic Assessment**: Uses transparent, testable rules to classify compromise (`likely_compromise`, `suspicious`, `insufficient_evidence`) and prioritize remediation (`critical`, `high`, `medium`, `low`) independently of LLM hallucinations.
- **Vulnerability vs. Exploitation Distinction**: Strictly distinguishes between vulnerable software exposure (e.g. Apache Struts CVE-2023-50164 / CISA KEV) and verified compromise.
- **Human-in-the-Loop Approval Gate**: Consequential actions (e.g., isolating production jump boxes or disabling accounts) enforce strict human authorization before simulated execution.
- **Simulated Fleet Verification**: Simulates containment actions against a verified sandbox fleet and validates resulting state telemetry before confirming success.
- **Official Model Context Protocol (MCP) Server**: Exposes 8 domain-specific investigation tools via the official Python MCP SDK (`mcp 2.x`).
- **Interactive Cytoscape.js Workspace**: Real-time visual graph representation with node property inspection, layout switching, and responsive telemetry panels.
- **Complete Test Suite & Provenance Persistence**: 24 automated unit and integration tests passing against live FalkorDB queries.

---

## 3. Architecture Overview

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
+-------------------------------------------|---------------------------------------------+
                                            | falkordb-py client (tcp 127.0.0.1:6379)
                                            v
+-----------------------------------------------------------------------------------------+
|                                  FALKORDB ENGINE                                        |
|                                                                                         |
|      Dedicated Database Graph: [ threatpath_dev ]                                       |
|      (Alert) --> [:HAS_EVENT] --> (Event) --> [:OCCURRED_ON] --> (Host)                 |
|                                     |                             |                     |
|                                     v                             v                     |
|                               (Technique)                     (Process)                 |
|                                                                   |                     |
|                                                                   v                     |
|                                                              (Indicator)                |
|      Preserved Practice Data: [ social ] (Untouched)                                    |
+-----------------------------------------------------------------------------------------+
```

---

## 4. FalkorDB Graph Schema & Semantics

ThreatPath uses a dedicated graph named **`threatpath_dev`**, preserving all existing database graphs.

### Schema Relationships:
```
(Alert)-[:HAS_EVENT]->(Event)
(Event)-[:INVOLVES_IDENTITY]->(Identity)
(Event)-[:OCCURRED_ON]->(Host)
(Event)-[:INVOLVES_PROCESS]->(Process)
(Host)-[:EXECUTED]->(Process)
(Process)-[:CONNECTED_TO]->(Indicator)
(Event)-[:MAPS_TO]->(Technique)
(Host)-[:RUNS]->(Software)
(Software)-[:AFFECTED_BY]->(Vulnerability)
(Host)-[:CAN_ACCESS]->(Asset)
(Investigation)-[:INVESTIGATES]->(Alert)
(Investigation)-[:RECOMMENDED_ACTION]->(ResponseAction)
```

See [docs/GRAPH_MODEL.md](docs/GRAPH_MODEL.md) for full node property schemas and relationship semantics.

---

## 5. Why FalkorDB is Essential

1. **Sub-Millisecond Graph Traversal**: Relational databases require expensive 5-way SQL joins to connect an alert to its external C2 IP. In FalkorDB, path traversals (`Alert -> Event -> Host -> Process -> Indicator`) execute in under 1.2 milliseconds.
2. **First-Class Cypher Path Matching**: Cypher's `MATCH p = (a:Alert)-[*1..4]-(target)` pattern matching enables rapid bounded graph expansion for incident root-cause analysis.
3. **Graph Ablation Demonstrability**: Because the topology directly drives the assessment, deleting a single edge in FalkorDB changes the deterministic classification from `likely_compromise` to `suspicious`.

---

## 6. Primary Cypher Queries

### Multi-Hop Attack Path Traversal
```cypher
MATCH p = (a:Alert)-[:HAS_EVENT]->(e:Event)-[:OCCURRED_ON]->(h:Host)-[:EXECUTED]->(pr:Process)-[:CONNECTED_TO]->(ind:Indicator)
WHERE a.id = $alert_id
RETURN p, pr, ind, h;
```

### High-Value Asset Reachability
```cypher
MATCH p = (a:Alert)-[:HAS_EVENT]->(e:Event)-[:OCCURRED_ON]->(h:Host)-[:CAN_ACCESS]->(ast:Asset)
WHERE a.id = $alert_id
RETURN p, h.hostname AS hostname, ast.id AS asset_id, ast.name AS asset_name,
       ast.criticality AS criticality, ast.data_classification AS classification;
```

### Software & CISA KEV Vulnerability Exposure
```cypher
MATCH p = (a:Alert)-[:HAS_EVENT]->(e:Event)-[:OCCURRED_ON]->(h:Host)-[:RUNS]->(s:Software)-[:AFFECTED_BY]->(v:Vulnerability)
WHERE a.id = $alert_id
RETURN p, s.name AS software, s.version AS version, v.cve_id AS cve_id,
       v.cvss_score AS cvss_score, v.cisa_kev AS cisa_kev, v.description AS description;
```

See [docs/CYPHER_QUERIES.md](docs/CYPHER_QUERIES.md) for complete parameterized query specifications.

---

## 7. Model Context Protocol (MCP) Integration

ThreatPath implements a genuine MCP server (`backend/agent/mcp_server.py`) using the official Python MCP SDK (`mcp 2.x`).

### Registered MCP Tools:
- `get_alert_context(alert_id: str)`: Resolves immediate alert envelope.
- `trace_attack_path(alert_id: str)`: Discovers multi-hop execution and C2 paths.
- `check_asset_exposure(alert_id: str)`: Identifies reachability to high-value assets.
- `get_indicator_context(alert_id: str)`: Retrieves threat intel and reputation scores.
- `find_related_alerts(alert_id: str)`: Correlates alerts sharing hosts or identities.
- `record_investigation(...)`: Persists investigation provenance into FalkorDB.
- `simulate_response(action_type, target_entity)`: Proposes simulated defensive containment.
- `execute_response(action_id)`: Executes containment against simulated fleet.
- `verify_response(action_id)`: Verifies resulting telemetry on simulated endpoints.

---

## 8. Four Synthetic Scenarios

| Scenario | Alert ID | Description | FalkorDB Ground Truth | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **Scenario A** | `alert-sec-001` | Suspicious Interactive Logon & Beaconing | RDP Logon -> Jump Host -> Encoded PowerShell -> C2 IP (198.51.100.44) -> Access to Customer DB | **Likely Compromise** (Critical Priority, Host Isolation Proposed) |
| **Scenario B** | `alert-sec-002` | Off-Hours Login from Anomalous Geolocation | Single SSO auth on Auth Gateway. Zero child processes, zero external IOCs | **Insufficient Evidence** (Low Priority, Missing Evidence Flagged) |
| **Scenario C** | `alert-sec-003` | Critical RCE Disclosure (Struts CVE-2023-50164) | Host runs vulnerable software with access to Payment API, but zero malicious executions | **Suspicious (Exposure Only)** (High Priority, Not Compromised) |
| **Scenario D** | `alert-sec-004` | Repeated Password Spray Failures | Failed SSH logins on Staging Bastion. Independent scanner IOC in DB is disconnected | **Insufficient Evidence** (Disconnected Entities Not Correlated) |

---

## 9. Quickstart & Setup Instructions

### Prerequisites
- Linux / macOS
- Docker (with local FalkorDB running: `docker ps`)
- Python 3.12+
- Node.js v20+ & npm

### Step 1: Environment Setup & Dependencies
```bash
# Initialize Python virtual environment
python3 -m venv venv
source ./venv/bin/activate

# Install backend dependencies
pip install --upgrade pip
pip install falkordb fastapi uvicorn pydantic pydantic-settings python-dotenv pytest httpx mcp

# Install frontend dependencies
npm --prefix ./frontend install
```

### Step 2: Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration connects to local FalkorDB at `127.0.0.1:6379` using dedicated graph `threatpath_dev`.

### Step 3: Seed Synthetic Scenarios into FalkorDB
```bash
python3 -m backend.seed
```

### Step 4: Run the Test Suite (Including Graph Ablation Test)
```bash
pytest tests/ -v
```

### Step 5: Start the Backend Server
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Step 6: Start the Frontend Workspace
```bash
npm --prefix ./frontend run dev
```
Open **`http://localhost:5173`** in your browser.

---

## 10. REST API Endpoints

- `GET /api/health` — Verifies FalkorDB connectivity and operational mode.
- `GET /api/alerts` — Lists all registered security alerts in FalkorDB.
- `GET /api/alerts/{alert_id}` — Retrieves an individual alert.
- `POST /api/investigations` — Triggers graph-native autonomous investigation.
- `GET /api/investigations/{id}` — Retrieves investigation record.
- `GET /api/investigations/{id}/evidence` — Retrieves structured evidence & Cytoscape graph.
- `POST /api/actions/{id}/approve` — Analyst approval gate.
- `POST /api/actions/{id}/deny` — Analyst denial gate.
- `POST /api/actions/{id}/execute` — Executes containment on simulated fleet.
- `GET /api/actions/{id}/verify` — Verifies simulated endpoint telemetry.

---

## 11. Security & Safety Boundaries

- **Zero Production Risk**: All containment actions are strictly simulated. ThreatPath never isolates real endpoints, modifies real network controls, or executes arbitrary shell commands.
- **Strict Parameterization**: All Cypher queries use parameterized inputs to prevent injection.
- **Credential Protection**: Database passwords and API keys are never exposed in tool arguments or logged.
- **Localhost Binding**: All services bind exclusively to `127.0.0.1` by default.

---

## 12. AI-Assisted Development Disclosure

In accordance with Graph Hacks 2026 rules:
- ThreatPath was designed and engineered with assistance from **Google Antigravity**.
- All FalkorDB Cypher queries, graph schemas, deterministic scoring rules, approval gates, and simulation verifiers were designed for this project, audited against a live local FalkorDB container, and verified through 24 automated unit and integration tests.
