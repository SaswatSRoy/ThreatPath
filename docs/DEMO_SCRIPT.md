# ThreatPath Demonstration Script (Graph Hacks 2026)

Follow this end-to-end script to evaluate ThreatPath for **Track 01: Agents That Act on Connected Data**.

---

## Part 1: Quickstart & Environment Verification

### 1. Verify FalkorDB Container
Ensure the local FalkorDB Docker container is active:
```bash
docker ps --filter "ancestor=falkordb/falkordb:edge"
```
*Note*: FalkorDB listens on port `6379` (database) and port `3000` (FalkorDB Browser).

### 2. Activate Virtual Environment & Seed Graph
```bash
source ./venv/bin/activate
python3 -m backend.seed
```
*Expected Output*:
```
Summary: 24 nodes, 20 relationships, 4 alerts seeded into dedicated graph 'threatpath_dev'.
```

### 3. Start Backend API Server
In terminal 1:
```bash
source ./venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Verify health:
```bash
curl -s http://127.0.0.1:8000/api/health | jq .
```

### 4. Start Frontend Workspace
In terminal 2:
```bash
npm --prefix ./frontend run dev
```
Open your browser to: **`http://localhost:5173`**

---

## Part 2: Live UI Demonstration

### Demo Walkthrough 1: Scenario A — Correlated Attack Path & Host Containment
1. **Select Alert**: In the left Alert Queue, click on:
   `Scenario A: Suspicious Interactive Logon & Beaconing Activity (alert-sec-001)`
2. **Review Prompt**: The objective auto-fills:
   `"Investigate anomalous off-hours RDP logon, trace child process execution, identify outbound C2 indicators, and assess critical asset exposure."`
3. **Run Investigation**: Click **"Run Graph Investigation"** (`#btn-run-investigation`).
4. **Inspect Cytoscape Evidence Graph**:
   - Observe the multi-hop attack chain:
     `Alert -> Event -> Host (jump-prod-01) -> Process (powershell.exe) -> Indicator (198.51.100.44)`
   - Observe the asset exposure path:
     `Host (jump-prod-01) -> Asset (Customer Records Database [CRITICAL])`
5. **Inspect Node Properties**: Click on node `proc-powershell-enc` or `ind-c2-ip`.
   - The interactive drawer reveals full telemetry: PID `4892`, base64 command line, malicious score `95`.
6. **Review Findings Panel**:
   - **Classification**: `LIKELY COMPROMISE` (Red badge)
   - **Remediation Priority**: `CRITICAL`
   - **Score Factors**: Corroborating beaconing chain (+0.40), Malicious intel score (+0.25), ATT&CK alignment (+0.15), Privileged account (+0.10), Critical asset reachability (+0.10).
7. **Simulated Response & Approval Gate**:
   - Under Response Action, note: `SIMULATE_ISOLATE_HOST` for `host-jump-prod-01`.
   - Policy decision: `REQUIRE_APPROVAL` (Yellow badge).
   - Click **"Approve Simulated Action"** (`#btn-approve-action`).
   - State transitions to `APPROVED`.
   - Click **"Execute & Verify Simulation"** (`#btn-execute-action`).
   - Observe live verification: `OUTCOME VERIFIED` with confirmed telemetry:
     `"Simulated telemetry check: Host 'jump-prod-01.corp.internal' network interface placed in isolated VLAN; traffic restricted."`

---

### Demo Walkthrough 2: Scenario B — Insufficient Evidence (Preventing False Containment)
1. In the Alert Queue, select:
   `Scenario B: Off-Hours Portal Access from Anomalous Geolocation (alert-sec-002)`
2. Click **"Run Graph Investigation"**.
3. **Observe Findings**:
   - Classification: `INSUFFICIENT EVIDENCE` (Cyan badge).
   - Priority: `LOW`.
   - Missing Evidence tab highlights:
     - `"No active network beaconing or C2 communication path detected."`
     - `"No suspicious child processes connected to the event."`
   - Demonstrates that the agent does NOT recommend aggressive containment when multi-hop evidence is absent.

---

### Demo Walkthrough 3: Scenario C — Distinguishing Vulnerability from Compromise
1. In the Alert Queue, select:
   `Scenario C: Vulnerability Disclosure: Critical RCE on External Gateway (alert-sec-003)`
2. Click **"Run Graph Investigation"**.
3. **Observe Findings**:
   - Host runs Apache Struts with `CVE-2023-50164` (CVSS 9.8, CISA KEV).
   - Remediation Priority is elevated to `HIGH` due to high-value Payment Gateway asset.
   - **Classification remains `SUSPICIOUS` (NOT `likely_compromise`)**!
   - Missing Evidence explicitly notes:
     `"CRITICAL: Known vulnerability detected on host, but zero execution or exploitation telemetry observed."`
   - Proves the system strictly distinguishes exposure from active compromise.

---

## Part 3: Automated Test Suite & Graph Ablation Verification

Run the full automated test suite to prove that FalkorDB graph topology drives the investigation results:

```bash
./venv/bin/pytest tests/ -v
```

To run the mandatory graph ablation test in isolation:
```bash
./venv/bin/pytest tests/test_graph_ablation.py -v
```
Notice how deleting the `CONNECTED_TO` edge in FalkorDB directly alters the classification from `likely_compromise` to `suspicious` without hardcoded shortcuts!
