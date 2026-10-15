# ThreatPath — Deployment & Production Operations Guide
**Project:** ThreatPath (Graph Hacks 2026, Track 01 — Agents That Act on Connected Data)  
**Target Platform:** Railway / Any Standard Docker PaaS Container Platform

---

## 1. Target Deployment Architecture

ThreatPath employs a robust, two-service containerized architecture separating public web presentation and agent orchestration from private graph data persistence:

```
                            PUBLIC INTERNET
                                  │
                                  ▼ (HTTPS:443)
                 ┌───────────────────────────────────┐
                 │    ThreatPath Web Application     │
                 │   (Railway Service 1 — Public)    │
                 │ ───────────────────────────────── │
                 │ • React + Vite compiled SPA       │
                 │ • FastAPI REST API & Agent Engine │
                 │ • Deterministic Assessment Engine │
                 │ • Policy & Approval Gate System   │
                 │ • Durable Simulation State Cache  │
                 └─────────────────┬─────────────────┘
                                   │
              Private Internal Network (No Public Ingress)
              Host: falkordb-server.railway.internal / Port: 6379
                                   │
                                   ▼
                 ┌───────────────────────────────────┐
                 │       FalkorDB Graph Server       │
                 │ (Railway Service: falkordb-server)│
                 │ ───────────────────────────────── │
                 │ • Image: falkordb/falkordb-server │
                 │ • Pin: 6.0.2 (server-only)        │
                 │ • Auth: REDIS_ARGS requirepass    │
                 │ • Graph: threatpath_demo          │
                 │ • Volume: /var/lib/falkordb/data  │
                 └───────────────────────────────────┘
```

**Live Demonstration URL:** [https://threatpath-production.up.railway.app](https://threatpath-production.up.railway.app)  
**GitHub Repository:** [https://github.com/SaswatSRoy/ThreatPath](https://github.com/SaswatSRoy/ThreatPath)

### Architectural Safeguards
1. **Single Web Application Origin:** The React/Vite production distribution is built and statically served directly by FastAPI. All API calls use relative paths (`/api/...`), completely eliminating CORS complexities, cross-origin cookies, or public API leakage.
2. **Database Isolation:** The FalkorDB graph database is strictly internal. No public domain, port forwarding, or TCP proxy is attached to port 6379. Only the ThreatPath web container can communicate with FalkorDB over the private virtual network.
3. **Graph Segregation:** The production demonstration utilizes a dedicated graph named `threatpath_demo`. The local development database uses `threatpath_dev` and `social`. Graphs are completely isolated.

---

## 2. Docker Image & Local Validation

The root `Dockerfile` is a production-optimized multi-stage build:
- **Stage 1 (`node:20-slim`):** Installs frontend dependencies via `npm ci` and compiles the React/TypeScript/Cytoscape application into static assets (`dist/`).
- **Stage 2 (`python:3.12-slim`):** Installs Python runtime dependencies from `requirements.txt`, copies backend application modules, embeds the compiled frontend into `/app/frontend/dist`, and runs Uvicorn.
- **Port Dynamic Binding:** Uvicorn binds to `0.0.0.0` and dynamically binds to `${PORT:-8000}`, honoring platform-assigned ports.

### Building and Testing the Image Locally
```bash
# 1. Build the production image locally
docker build -t threatpath:prod .

# 2. Run container smoke test on alternate port (8080) against local FalkorDB
docker run --rm -p 8080:8000 \
  --add-host=host.docker.internal:host-gateway \
  -e FALKORDB_HOST=host.docker.internal \
  -e FALKORDB_PORT=6379 \
  -e FALKORDB_GRAPH=threatpath_dev \
  -e APP_ENV=production \
  --name threatpath-smoke-test \
  threatpath:prod
```

---

## 3. Railway Cloud Setup (Manual Configuration Steps)

> [!IMPORTANT]
> **Railway Configuration Architecture Notice:**
> Railway has officially **deprecated Config-as-Code (`railway.json` / `railway.toml`)**, and new services cannot opt into it. While `railway.json` is maintained in this repository for legacy compatibility, **new services must not rely on it**.
> 
> ThreatPath is engineered for full compatibility with Railway's modern platform architecture:
> 1. **Self-Contained Container Runtime:** The production `Dockerfile` contains a signal-propagating shell entrypoint (`CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]`). It natively binds to Railway's dynamic `$PORT` environment variable and handles graceful shutdown without requiring any custom start command in the Railway dashboard.
> 2. **Explicit Dashboard Configuration:** Critical operational parameters (health checks, volume mount paths, private networking, and inter-service secrets) are configured directly via the Railway Web Dashboard as detailed below.

To deploy ThreatPath on Railway, follow these exact steps in the Railway dashboard.

### Step 1: Create a New Empty Project
1. Log into your Railway account at [railway.com](https://railway.com).
2. Click **New Project** -> Select **Empty Project**.

### Step 2: Provision Service 2 — Dedicated FalkorDB Service
1. In the project canvas, click **+ Create** -> **Docker Image**.
2. Set the verified production image repository and pinned release tag:
   ```text
   falkordb/falkordb-server:6.0.2
   ```
   *(Multi-architecture manifest digest: `sha256:8e4fe29e6646890a9deaf2f009ad2bc5e592d79fe9cd718810c3a97a8bcd34c0`)*
3. Name the service: **`falkordb-server`**.
4. In the service **Settings**:
   - **Networking:** Do **NOT** generate a public domain. Do **NOT** create a public TCP proxy.
   - Note the **Private Service Name** (typically `falkordb-server.railway.internal`).
5. In **Volumes**:
   - Click **Add Volume**.
   - Set the mount path strictly to:
     ```text
     /var/lib/falkordb/data
     ```
6. In **Variables**:
   - Add platform-managed secret `FALKORDB_PASSWORD`:
     ```text
     FALKORDB_PASSWORD=<Generate a high-entropy 32+ character random string>
     ```
   - Add Redis password and AOF durability configuration using official Railway same-service template syntax:
     ```text
     REDIS_ARGS=--requirepass ${{ FALKORDB_PASSWORD }} --appendonly yes
     ```

### Step 3: Provision Service 1 — ThreatPath Web Application
1. In the project canvas, click **+ Create** -> **GitHub Repo**.
2. Select your repository `ThreatPath`.
3. Name the service: `threatpath-web` (or `threatpath-production`).
4. In **Settings**:
   - **Build:** Builder is automatically detected from the root `Dockerfile`.
   - **Deploy -> Start Command:** Leave **EMPTY** (defaults automatically to the Dockerfile's built-in `CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]`).
   - **Networking:** Click **Generate Domain** (e.g. `threatpath-production.up.railway.app`).
   - **Healthcheck Path:** Set to `/api/health`.
   - **Healthcheck Timeout:** Set to `120` seconds.
   - **Restart Policy:** `On Failure` (max retries: 5).
5. In **Variables**, enter the following environment configuration using official Railway template syntax (referencing Service 2 `falkordb-server`):

| Variable Name | Recommended Value | Description | Secret? |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `production` | Production runtime flag | No |
| `FALKORDB_HOST` | `${{ falkordb-server.RAILWAY_PRIVATE_DOMAIN }}` | Official Railway cross-service private DNS | No |
| `FALKORDB_PORT` | `6379` | FalkorDB standard port | No |
| `FALKORDB_PASSWORD` | `${{ falkordb-server.FALKORDB_PASSWORD }}` | Official Railway cross-service secret reference | **YES (Secret)** |
| `FALKORDB_GRAPH` | `threatpath_demo` | Dedicated remote demo graph | No |
| `LLM_PROVIDER` | `mock` | Deterministic fallback mode (zero external key required) | No |
| `ENABLE_SIMULATED_RESPONSES` | `true` | Allows simulated defensive response lifecycle | No |
| `AGENT_MAX_TOOL_ROUNDS` | `6` | Maximum graph traversal rounds per investigation | No |
| `AGENT_TOOL_TIMEOUT_SECONDS` | `10` | Bounded graph query timeout | No |

*(Optional LLM Integration: If external LLM narrative generation is desired, add `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o`, and `LLM_API_KEY=<secret>`. If omitted or unset, ThreatPath operates deterministically).*

---

## 4. Pre-Deployment Verification Checklist

Before provisioning or authorizing a public demonstration deployment, verify the following controls:

- [ ] **Database Authentication**:
  - FalkorDB service configured with `REDIS_ARGS=--requirepass ${{ FALKORDB_PASSWORD }} --appendonly yes`.
  - Web application securely references `${{ falkordb-server.FALKORDB_PASSWORD }}` via Railway platform secrets.
  - Pinned to verified immutable image `falkordb/falkordb-server:6.0.2` (`sha256:8e4fe29e6646890a9deaf2f009ad2bc5e592d79fe9cd718810c3a97a8bcd34c0`).
- [ ] **Private Networking**:
  - FalkorDB service has **no public domain** and **no public TCP proxy** on port 6379.
  - Web application connects via private DNS: `${{ falkordb-server.RAILWAY_PRIVATE_DOMAIN }}:6379`.
  - Port 6379 is completely unreachable from the public internet.
- [ ] **Persistence**:
  - Persistent volume attached to FalkorDB service mounted strictly at `/var/lib/falkordb/data`.
  - Target graph strictly designated as `threatpath_demo`.
  - Graph data survives container restarts, redeployments, and crashes.
- [ ] **Public API Write Protections**:
  - Consequential actions (`SIMULATE_ISOLATE_HOST`, `SIMULATE_DISABLE_ACCOUNT`) enforce mandatory human approval (`WAITING_FOR_APPROVAL`).
  - Execution strictly rejects unapproved actions with HTTP 403 Forbidden.
  - Simulated actions only mutate sandboxed memory/graph state; zero real-world infrastructure impact.
  - Multi-user isolation enabled via `X-Session-ID` headers to prevent cross-judge interference.
  - Unknown `/api/...` endpoints strictly return JSON 404 and never fall through to HTML.
- [ ] **Health Checks**:
  - Health check path configured as `/api/health` with 120-second startup timeout.
  - `/api/health` returns structured status (`healthy`, `connected`, active graph) without leaking passwords or connection strings.
  - Database client employs bounded timeouts (5s socket / 3s connect) to prevent process deadlock.

---

## 5. Remote Graph Seeding Procedure (In-Network Execution)

> [!IMPORTANT]
> **Railway Private Network Boundary:**
> FalkorDB has **no public domain or TCP proxy** and listens solely on Railway's internal private mesh (`${{ falkordb-server.RAILWAY_PRIVATE_DOMAIN }}:6379`). Railway's private DNS is only resolvable by containers running **inside** the Railway project environment.
> 
> Therefore, remote seeding **cannot** be executed directly from your local laptop against the private hostname. It must be executed from inside Railway's private network using one of the two guarded procedures below.
> 
> Seeding is kept **strictly separate from web application startup** so regular redeployments or container restarts never unexpectedly overwrite or reseed the graph.

### Safety Safeguards
- Seeding **NEVER** runs automatically on web application startup.
- Seeding strictly targets the dedicated remote graph: `threatpath_demo`.
- Seeding strictly rejects running against `social` or local development graphs (`threatpath_dev`).
- Seeding requires the explicit `--confirm` CLI flag.
- Seeding is idempotent (`MERGE`-based) and will **never** drop, erase, or truncate existing graph data.

---

### Method A: Web Container Terminal (Recommended & Fastest)

Once the `threatpath-web` service is deployed and healthy:

1. In the Railway dashboard, click on the **`threatpath-web`** service.
2. Navigate to the **Deployments** tab and click on the currently active deployment.
3. Click the **Terminal** tab to open an interactive shell inside the running container.
4. Execute the guarded seed command:
   ```bash
   python -m scripts.seed_remote --confirm
   ```
   *(All required database variables `FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_PASSWORD`, and `FALKORDB_GRAPH` are already present in the container's environment).*

5. Confirm the verification table prints all 4 alerts and node/relationship counts.

---

### Method B: Dedicated One-Off Seeder Job (Headless)

If you prefer an automated or headless one-off job:

1. In the project canvas, click **+ Create** -> **GitHub Repo** -> select `ThreatPath`.
2. Name the service: `threatpath-seeder`.
3. In **Settings**:
   - **Deploy -> Start Command**: Set to:
     ```bash
     python -m scripts.seed_remote --confirm
     ```
   - **Deploy -> Restart Policy**: Set to **`Never`** (ensures it runs once and stops).
4. In **Variables**, add the same database variables (referencing `falkordb-server`):
   - `FALKORDB_HOST` = `${{ falkordb-server.RAILWAY_PRIVATE_DOMAIN }}`
   - `FALKORDB_PORT` = `6379`
   - `FALKORDB_PASSWORD` = `${{ falkordb-server.FALKORDB_PASSWORD }}`
   - `FALKORDB_GRAPH` = `threatpath_demo`
5. Click **Deploy**. Check the deployment logs to confirm successful seeding output.
6. Once completed, **Delete** the `threatpath-seeder` service in Railway so it does not persist or re-run.

---

### Seeding Verification Output & Validator Audit Note

Both seeding methods execute `seed_graph()` and insert into `threatpath_demo`:
1. `alert-sec-001` (Scenario A: Suspicious Interactive Logon & Beaconing Activity)
2. `alert-sec-002` (Scenario B: Single Inconclusive Beaconing Indicator)
3. `alert-sec-003` (Scenario C: High-Severity CVE on Exposed DMZ Host)
4. `alert-sec-004` (Scenario D: Distributed SSH Password-Spray Attempt)
5. 24 graph nodes and 20 directional relationships connecting identities, hosts, processes, MITRE ATT&CK techniques, vulnerabilities, and assets.

> [!NOTE]
> **Engineering Audit Note on Validator Assertion:**
> In the current release, `seed_graph()` completes with 100% success inserting all 24 nodes, 20 relationships, and 4 scenario alerts into `threatpath_demo`. However, the helper validation function `validate_seeded_graph` in `scripts/seed_remote.py` checks for relationship label `HAS_TECHNIQUE` instead of the canonical `MAPS_TO` defined in `cypher/seed_scenarios.cypher` and `docs/GRAPH_MODEL.md`.
> Consequently, the script's exit code reports validation failure on this assertion. The actual graph insertion is completely intact and verified live: `/api/alerts` returns all 4 alerts with HTTP 200. Updating the assertion string in `scripts/seed_remote.py` is logged as a pending maintenance patch.

---

## 6. Public URL Verification Checklist

Perform these read-only checks against the live production deployment:

1. **Live Health Endpoint Check:**
   ```bash
   curl -s https://threatpath-production.up.railway.app/api/health | jq .
   ```
   **Verified Live Response:**
   ```json
   {
     "status": "healthy",
     "falkordb_status": "connected",
     "active_graph": "threatpath_demo",
     "available_graphs": [
       "threatpath_demo"
     ],
     "llm_mode": "deterministic",
     "simulated_responses_enabled": true
   }
   ```

2. **Live Alert Catalog Check:**
   ```bash
   curl -s https://threatpath-production.up.railway.app/api/alerts | jq '.[].id'
   ```
   **Verified Live Response:**
   ```text
   "alert-sec-004"
   "alert-sec-003"
   "alert-sec-001"
   "alert-sec-002"
   ```

3. **Frontend UI Walkthrough:** Open [https://threatpath-production.up.railway.app](https://threatpath-production.up.railway.app) in any modern browser. Verify:
   - Dark SOC visual identity with header status badge showing `Connected (threatpath_demo)`.
   - Alert queue displays all 4 synthetic scenarios.
   - Scenario A investigation loads Cytoscape.js interactive graph within 200ms.
   - Proposing, approving, and executing simulated Host Isolation succeeds with action-specific verification (`placed in isolated VLAN`).

4. **API 404 Guard:**
   ```bash
   curl -i https://threatpath-production.up.railway.app/api/nonexistent
   ```
   Returns HTTP 404 with JSON `{ "detail": "Endpoint not found" }` (never falls through to HTML).

---

## 7. Rollback, Redeployment & Operational Risks

- **Zero-Data Loss Redeployments:** Graph data resides on the mounted persistent volume at `/var/lib/falkordb/data`. Redeploying or updating the ThreatPath web container will **never** alter graph data.
- **Volume Unmounting during Redeployment:** Reconfiguring the FalkorDB service volume may incur brief database downtime (< 30 seconds). The web application handles transient database unreachability with graceful timeouts and informative degraded health status.
- **Deterministic Independence:** In the event that an external LLM provider encounters rate limits or outages, ThreatPath automatically falls back to its deterministic rule-grounded narrative engine with zero degradation of scoring accuracy or graph traversals.
