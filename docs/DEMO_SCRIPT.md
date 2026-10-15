# ThreatPath Demonstration Script (Graph Hacks 2026)

**Submission Track:** Track 01 — Agents That Act on Connected Data  
**Live Public Application:** [https://threatpath-production.up.railway.app](https://threatpath-production.up.railway.app)  
**Source Repository:** [https://github.com/SaswatSRoy/ThreatPath](https://github.com/SaswatSRoy/ThreatPath)  

> [!NOTE]
> **Reproducible Live Demonstration:**
> This demonstration is designed to be executed directly in your browser against the live production deployment. Every scenario is backed by real FalkorDB graph data in `threatpath_demo` and deterministic assessment rules. A local fallback workflow is also provided below in Part 3.

---

## Part 1: Live Public Application Walkthrough

### 1. Pre-Flight Verification (Optional CLI Check)
Before opening the browser, you can verify the public service health and loaded alerts:
```bash
# Check live production health
curl -s https://threatpath-production.up.railway.app/api/health | jq .

# Verify the 4 scenario alerts in threatpath_demo
curl -s https://threatpath-production.up.railway.app/api/alerts | jq '.[].id'
```

---

### Demo Walkthrough 1: Scenario A — Correlated Attack Path & Host Containment

1. **Open the Live Application:** Navigate to [https://threatpath-production.up.railway.app](https://threatpath-production.up.railway.app).
   - Verify the top-right status indicator shows **`Connected (threatpath_demo)`**.
2. **Select Alert:** In the left Alert Queue, click on:
   **`Scenario A: Suspicious Interactive Logon & Beaconing Activity (alert-sec-001)`**
3. **Trigger Investigation:** Click the primary action button: **"Run Graph Investigation"** (`#btn-run-investigation`).
4. **Inspect Cytoscape Evidence Graph:**
   - Observe the multi-hop attack chain traversed by the agent:
     `Alert (alert-sec-001)` $\rightarrow$ `Event (evt-101)` $\rightarrow$ `Host (jump-prod-01)` $\rightarrow$ `Process (powershell.exe)` $\rightarrow$ `Indicator (198.51.100.44)`
   - Observe the high-value asset exposure link:
     `Host (jump-prod-01)` $\rightarrow$ `Asset (Customer Records Database [CRITICAL])`
5. **Inspect Node & Relationship Properties:**
   - Click on node `proc-powershell-enc` in the graph. The slide-over inspection modal displays: PID `4892`, hash, and encoded command line.
   - Click on node `ind-c2-ip` to inspect the threat reputation score (`95`) and classification (`MALICIOUS`).
6. **Review Findings & Deterministic Assessment:**
   - **Classification:** `LIKELY COMPROMISE` (Red badge)
   - **Remediation Priority:** `CRITICAL`
   - **Score Factors:** Corroborating beaconing chain (`+0.40`), Malicious intel score (`+0.25`), ATT&CK alignment (`+0.15`), Privileged account (`+0.10`), Critical asset reachability (`+0.10`). Total raw score capped at `0.95`.
7. **Simulated Response Lifecycle (Human-in-the-Loop):**
   - Under the Response Action panel, note the proposed action: `SIMULATE_ISOLATE_HOST` for `host-jump-prod-01`.
   - Policy decision: `REQUIRE_APPROVAL` (Yellow badge). Unapproved execution is strictly rejected by the backend policy gate.
   - Click **"Approve Simulated Action"** (`#btn-approve-action`). State transitions to `APPROVED`.
   - Click **"Execute & Verify Simulation"** (`#btn-execute-action`).
   - Observe live telemetry verification: state transitions to `VERIFIED` with confirmed endpoint telemetry:
     `"Simulated telemetry check: Host 'jump-prod-01.corp.internal' network interface placed in isolated VLAN; traffic restricted."`

---

### Demo Walkthrough 2: Scenario B — Demonstrating Uncertainty & Preventing False Containment

1. **Select Alert:** In the Alert Queue, click on:
   **`Scenario B: Off-Hours Portal Access from Anomalous Geolocation (alert-sec-002)`**
2. **Trigger Investigation:** Click **"Run Graph Investigation"**.
3. **Observe Evidence & Assessment:**
   - Graph shows a single authentication event on `auth-gateway.corp.internal` with valid SSO credentials.
   - **Classification:** `INSUFFICIENT EVIDENCE` (Cyan badge)
   - **Remediation Priority:** `LOW`
   - **Missing Evidence Panel:** Explicitly highlights the absence of multi-hop corroboration:
     - *"No active network beaconing or C2 communication path detected."*
     - *"No suspicious child processes connected to the event."*
4. **Key Takeaway:** Demonstrates that ThreatPath respects topological boundaries and does **not** recommend aggressive containment when causal attack paths are absent.

---

### Demo Walkthrough 3: Scenario C — Distinguishing Vulnerability Exposure from Compromise

1. **Select Alert:** In the Alert Queue, click on:
   **`Scenario C: Vulnerability Disclosure: Critical RCE on External Gateway (alert-sec-003)`**
2. **Trigger Investigation:** Click **"Run Graph Investigation"**.
3. **Observe Evidence & Assessment:**
   - Host `api-gw-dmz-02.corp.internal` runs Apache Struts affected by `CVE-2023-50164` (CVSS 9.8, listed in CISA KEV catalog).
   - Host has access to high-value internal resource: `Payment Gateway Core`.
   - **Crucial Security Logic:** Despite the presence of a critical KEV vulnerability on an exposed DMZ host, the classification remains **`SUSPICIOUS`** (Exposure Only), **NOT** `LIKELY_COMPROMISE`!
   - Missing evidence panel explicitly documents:
     `"CRITICAL: Known vulnerability detected on host, but zero execution or exploitation telemetry observed."`
4. **Action-Specific Escalation:**
   - Recommended Action: **`SIMULATE_ESCALATE_INCIDENT`** (Security engineering ticketing & patch prioritization; strictly **NOT** host isolation).
   - Approve and execute the action: verification confirms high-priority incident dispatch without disrupting operational availability.

---

### Demo Walkthrough 4: Scenario D — Disconnected Entities (Preventing False Correlation)

1. **Select Alert:** In the Alert Queue, click on:
   **`Scenario D: Repeated Password Spray Failures on Staging Bastion (alert-sec-004)`**
2. **Trigger Investigation:** Click **"Run Graph Investigation"**.
3. **Observe Evidence & Assessment:**
   - Telemetry shows multiple failed SSH login attempts for invalid accounts on `bastion-stage.corp.internal`.
   - Event status is `BLOCKED`. Zero active sessions were established, zero child processes spawned.
   - An independent malicious scanner indicator exists in the FalkorDB database (`203.0.113.88`), but it is **disconnected** with zero graph edges.
   - **Classification:** `INSUFFICIENT EVIDENCE` (`0.05`), Remediation Priority `LOW`.
4. **Key Takeaway:** Demonstrates that ThreatPath follows genuine graph relationships and does **not** hallucinate connections between unassociated entities.

---

## Part 2: Why FalkorDB is Essential to the Results

1. **Sub-Millisecond Graph Traversal:** Multi-hop path queries across heterogeneous security entities (`Alert -> Event -> Host -> Process -> Indicator -> Asset`) resolve in under 1.2 milliseconds.
2. **Topological Grounding:** Security decisions are anchored in explicit graph paths rather than probabilistic LLM hallucinations.
3. **Mathematical Proof via Graph Ablation:** As verified in `tests/test_graph_ablation.py`, deleting a physical graph edge in FalkorDB directly alters the security assessment without altering any backend code or heuristics.

---

## Part 3: Local Fallback Instructions

In the event that the public internet or external PaaS is unavailable, ThreatPath can be run 100% locally:

### Option A: Running from Local Source Code
```bash
# 1. Start local FalkorDB container (listening on port 6379)
docker run -d --name falkordb-practice -p 6379:6379 -p 3000:3000 falkordb/falkordb:edge

# 2. Activate virtual environment and seed local database
source ./venv/bin/activate
python -m backend.seed

# 3. Run automated tests (all 38 tests must pass)
pytest tests/ -v

# 4. Start backend API server (terminal 1)
uvicorn backend.main:app --host 127.0.0.1 --port 8000

# 5. Start frontend dev server (terminal 2)
npm --prefix ./frontend run dev
```
Open **`http://localhost:5173`** in your browser.

### Option B: Running the Production Docker Container
```bash
# Build unified multi-stage container
docker build -t threatpath:prod .

# Run container on port 8080 connected to local FalkorDB
docker run --rm -p 8080:8000 \
  --add-host=host.docker.internal:host-gateway \
  -e FALKORDB_HOST=host.docker.internal \
  -e FALKORDB_PORT=6379 \
  -e FALKORDB_GRAPH=threatpath_dev \
  -e APP_ENV=production \
  threatpath:prod
```
Open **`http://localhost:8080`** in your browser.
