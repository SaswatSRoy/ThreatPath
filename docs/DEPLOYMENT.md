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
              Host: falkordb.railway.internal / Port: 6379
                                   │
                                   ▼
                 ┌───────────────────────────────────┐
                 │       FalkorDB Graph Server       │
                 │   (Railway Service 2 — Private)   │
                 │ ───────────────────────────────── │
                 │ • Image: falkordb/falkordb-server │
                 │ • Pin: stable server-only release │
                 │ • Auth: REDIS_ARGS requirepass    │
                 │ • Graph: threatpath_demo          │
                 │ • Volume: /var/lib/falkordb/data  │
                 └───────────────────────────────────┘
```

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

To deploy ThreatPath on Railway, follow these exact steps in the Railway dashboard.

### Step 1: Create a New Empty Project
1. Log into your Railway account at [railway.com](https://railway.com).
2. Click **New Project** -> Select **Empty Project**.

### Step 2: Provision Service 2 — Dedicated FalkorDB Service
1. In the project canvas, click **+ Create** -> **Docker Image**.
2. Set the image repository:
   ```text
   falkordb/falkordb-server:latest
   ```
   *(Note: pin to a specific release tag such as `v0.5.2` / `6.0` if preferred).*
3. Name the service: `falkordb`.
4. In the service **Settings**:
   - **Networking:** Do **NOT** generate a public domain. Do **NOT** create a public TCP proxy.
   - Note the **Private Service Name** (typically `falkordb.railway.internal`).
5. In **Volumes**:
   - Click **Add Volume**.
   - Set the mount path to:
     ```text
     /var/lib/falkordb/data
     ```
6. In **Variables**:
   - Add platform-managed secret `FALKORDB_PASSWORD`:
     ```text
     FALKORDB_PASSWORD=<Generate a high-entropy 32+ character random string>
     ```
   - Add Redis password configuration:
     ```text
     REDIS_ARGS=--requirepass ${FALKORDB_PASSWORD}
     ```

### Step 3: Provision Service 1 — ThreatPath Web Application
1. In the project canvas, click **+ Create** -> **GitHub Repo**.
2. Select your repository `ThreatPath`.
3. Name the service: `threatpath-web`.
4. In **Settings**:
   - **Build:** Builder is automatically detected as `DOCKERFILE` via `railway.json`.
   - **Networking:** Click **Generate Domain** (e.g. `threatpath-production.up.railway.app`).
   - **Healthcheck Path:** Set to `/api/health`.
   - **Healthcheck Timeout:** Set to `120` seconds.
5. In **Variables**, enter the following environment configuration:

| Variable Name | Recommended Value | Description | Secret? |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `production` | Production runtime flag | No |
| `FALKORDB_HOST` | `falkordb.railway.internal` | Railway Private DNS name of Service 2 | No |
| `FALKORDB_PORT` | `6379` | FalkorDB standard port | No |
| `FALKORDB_PASSWORD` | `${{falkordb.FALKORDB_PASSWORD}}` | Reference to Service 2 secret password | **YES (Secret)** |
| `FALKORDB_GRAPH` | `threatpath_demo` | Dedicated remote demo graph | No |
| `LLM_PROVIDER` | `mock` | Deterministic fallback mode (zero external key required) | No |
| `ENABLE_SIMULATED_RESPONSES` | `true` | Allows simulated defensive response lifecycle | No |
| `AGENT_MAX_TOOL_ROUNDS` | `6` | Maximum graph traversal rounds per investigation | No |
| `AGENT_TOOL_TIMEOUT_SECONDS` | `10` | Bounded graph query timeout | No |

*(Optional LLM Integration: If external LLM narrative generation is desired, add `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o`, and `LLM_API_KEY=<secret>`. If omitted or unset, ThreatPath operates deterministically).*

---

## 4. Remote Graph Seeding Procedure

The remote database must be seeded once after deployment is established.

### Safety Safeguards
- Seeding **NEVER** runs automatically on application startup.
- Seeding requires the explicit `--confirm` CLI flag.
- Seeding is idempotent (`MERGE`-based) and will **never** drop or erase the graph.
- Seeding strictly rejects running against the `social` or local practice graphs.

### Seeding Command
You can run the seeding command locally with remote credentials or via Railway CLI:

```bash
# Using local CLI pointing to remote database:
FALKORDB_HOST="<railway-private-or-proxied-host>" \
FALKORDB_PORT=6379 \
FALKORDB_PASSWORD="<your-falkordb-password>" \
FALKORDB_GRAPH=threatpath_demo \
./venv/bin/python -m scripts.seed_remote --confirm
```

### Seeding Output Verification
The seed utility will verify and report:
1. `alert-sec-001` (Scenario A: Suspicious Interactive Logon & Beaconing Activity)
2. `alert-sec-002` (Scenario B: Single Inconclusive Beaconing Indicator)
3. `alert-sec-003` (Scenario C: High-Severity CVE on Exposed DMZ Host)
4. `alert-sec-004` (Scenario D: Distributed SSH Password-Spray Attempt)
5. 24 graph nodes and 20 directional relationships connecting identities, hosts, processes, MITRE ATT&CK techniques, vulnerabilities, and assets.

---

## 5. Public URL Verification Checklist

Once deployed and seeded, perform these checks against the public HTTPS URL:

1. **Health Endpoint:**
   ```bash
   curl -s https://<your-domain>.up.railway.app/api/health | jq .
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "falkordb_status": "connected",
     "active_graph": "threatpath_demo",
     "available_graphs": ["threatpath_demo"],
     "llm_mode": "deterministic",
     "simulated_responses_enabled": true
   }
   ```
2. **Frontend UI:** Open `https://<your-domain>.up.railway.app` in any modern browser. Verify:
   - Dark SOC visual identity with header status badge showing `Connected (threatpath_demo)`.
   - Alert queue displays all 4 synthetic scenarios.
   - Scenario A investigation loads Cytoscape.js interactive graph within 200ms.
   - Proposing, approving, and executing simulated Host Isolation succeeds with action-specific verification (`placed in isolated VLAN`).
3. **API 404 Guard:**
   ```bash
   curl -i https://<your-domain>.up.railway.app/api/nonexistent
   ```
   Must return HTTP 404 with JSON `{ "detail": "Endpoint not found" }` (not HTML).

---

## 6. Rollback, Redeployment & Operational Risks

- **Zero-Data Loss Redeployments:** Graph data resides on the mounted persistent volume at `/var/lib/falkordb/data`. Redeploying or updating the ThreatPath web container will **never** alter graph data.
- **Volume Unmounting during Redeployment:** Reconfiguring the FalkorDB service volume may incur brief database downtime (< 30 seconds). The web application handles transient database unreachability with graceful timeouts and informative degraded health status.
- **Deterministic Independence:** In the event that an external LLM provider encounters rate limits or outages, ThreatPath automatically falls back to its deterministic rule-grounded narrative engine with zero degradation of scoring accuracy or graph traversals.
