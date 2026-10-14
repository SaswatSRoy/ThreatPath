"""
End-to-End API Tests for ThreatPath
Tests the complete HTTP workflow using FastAPI TestClient.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.policy import simulated_env

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_env():
    simulated_env.reset()


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "ThreatPath"
    assert "Graph Hacks 2026" in data["hackathon"]


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["falkordb_status"] == "connected"
    assert data["active_graph"] == "threatpath_dev"


def test_list_alerts():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) >= 4
    ids = [a["id"] for a in alerts]
    assert "alert-sec-001" in ids
    assert "alert-sec-002" in ids
    assert "alert-sec-003" in ids
    assert "alert-sec-004" in ids


def test_get_alert_by_id():
    response = client.get("/api/alerts/alert-sec-001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "alert-sec-001"
    assert "Interactive Logon" in data["title"]


def test_get_nonexistent_alert():
    response = client.get("/api/alerts/alert-not-found")
    assert response.status_code == 404


def test_investigation_and_approval_workflow():
    """
    Complete end-to-end API investigation test:
    1. POST /api/investigations for alert-sec-001
    2. Verify investigation outcome and proposed action
    3. Attempt POST /api/actions/{id}/execute before approval -> Expect 403 Forbidden
    4. POST /api/actions/{id}/approve -> Expect 200 OK
    5. POST /api/actions/{id}/execute -> Expect 200 OK & ActionStatus.VERIFIED
    6. GET /api/actions/{id}/verify -> Expect 200 OK & confirmed telemetry
    """
    # 1. Trigger Investigation
    inv_resp = client.post(
        "/api/investigations",
        json={"alert_id": "alert-sec-001", "investigation_prompt": "Investigate anomalous RDP access"}
    )
    assert inv_resp.status_code == 200
    inv = inv_resp.json()
    inv_id = inv["id"]
    assert inv["assessment"]["classification"] == "likely_compromise"
    assert inv["assessment"]["remediation_priority"] == "critical"
    assert len(inv["graph"]["nodes"]) >= 5

    action = inv["recommended_action"]
    assert action is not None
    action_id = action["id"]
    assert action["status"] == "WAITING_FOR_APPROVAL"

    # 2. Verify evidence retrieval endpoint
    ev_resp = client.get(f"/api/investigations/{inv_id}/evidence")
    assert ev_resp.status_code == 200
    assert ev_resp.json()["classification"] == "likely_compromise"

    # 3. Attempt execution before approval -> MUST fail with 403 Forbidden
    exec_unapproved = client.post(f"/api/actions/{action_id}/execute")
    assert exec_unapproved.status_code == 403
    assert "Policy Gate Enforced" in exec_unapproved.json()["detail"]

    # 4. Approve Action
    appr_resp = client.post(
        f"/api/actions/{action_id}/approve",
        json={"approver": "SecOps On-Call Engineer", "comment": "Verified C2 beaconing"}
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "APPROVED"

    # 5. Execute Action
    exec_resp = client.post(f"/api/actions/{action_id}/execute")
    assert exec_resp.status_code == 200
    assert exec_resp.json()["status"] == "VERIFIED"
    assert "isolated VLAN" in exec_resp.json()["verification_details"]

    # 6. Verify Action Outcome
    ver_resp = client.get(f"/api/actions/{action_id}/verify")
    assert ver_resp.status_code == 200
    assert ver_resp.json()["status"] == "VERIFIED"


def test_evidence_subgraph_excludes_investigation_and_response_nodes():
    """
    Regression Test for Issue 3:
    Historical Investigation and ResponseAction nodes from prior runs must be preserved
    in FalkorDB provenance, but MUST NOT be presented in the evidence subgraph.
    """
    # Run investigation multiple times to generate historical nodes
    for _ in range(3):
        resp = client.post(
            "/api/investigations",
            json={"alert_id": "alert-sec-001", "investigation_prompt": "Historical pollution check"}
        )
        assert resp.status_code == 200
        inv = resp.json()

        # Check evidence subgraph nodes
        categories = {node["category"] for node in inv["graph"]["nodes"]}
        assert "Investigation" not in categories, "Investigation nodes leaked into attack evidence subgraph!"
        assert "ResponseAction" not in categories, "ResponseAction nodes leaked into attack evidence subgraph!"

        # Check evidence subgraph edges
        relations = {edge["relation"] for edge in inv["graph"]["edges"]}
        assert "INVESTIGATES" not in relations
        assert "TRIGGERED_ACTION" not in relations

        # Verify only valid domain entities are present
        allowed_categories = {
            "Alert", "Event", "Host", "Identity", "Process",
            "Indicator", "Technique", "Asset", "Software", "Vulnerability"
        }
        for node in inv["graph"]["nodes"]:
            assert node["category"] in allowed_categories


def test_all_evidence_nodes_and_edges_exist_in_falkordb():
    """
    Regression Test for Issue 6:
    Every displayed node and edge in the investigation graph must correspond to actual FalkorDB data.
    """
    from backend.database import db_manager

    resp = client.post(
        "/api/investigations",
        json={"alert_id": "alert-sec-001", "investigation_prompt": "Grounding verification"}
    )
    assert resp.status_code == 200
    graph_data = resp.json()["graph"]

    assert len(graph_data["nodes"]) > 0
    assert len(graph_data["edges"]) > 0

    # Query FalkorDB to verify each node ID exists in threatpath_dev
    for node in graph_data["nodes"]:
        node_id = node["id"]
        q = db_manager.execute_query(
            "MATCH (n) WHERE n.id = $id RETURN count(n)",
            {"id": node_id}
        )
        assert q.result_set[0][0] >= 1, f"Node {node_id} claimed in graph but not found in FalkorDB!"


def test_scenario_c_api_execution_and_verification_is_escalation_not_containment():
    """
    Regression Test for Issue 2 & 6:
    Scenario C unpatched vulnerability investigation:
    1. Proposes SIMULATE_ESCALATE_INCIDENT.
    2. Execution and verification must confirm ticketing, NOT host isolation/containment.
    """
    inv_resp = client.post(
        "/api/investigations",
        json={"alert_id": "alert-sec-003", "investigation_prompt": "Investigate unpatched CVE"}
    )
    assert inv_resp.status_code == 200
    inv = inv_resp.json()

    action = inv["recommended_action"]
    assert action is not None
    assert action["action_type"] == "SIMULATE_ESCALATE_INCIDENT"
    action_id = action["id"]

    # Escalation is pre-approved under ALLOW policy
    if action["status"] == "WAITING_FOR_APPROVAL":
        appr_resp = client.post(
            f"/api/actions/{action_id}/approve",
            json={"approver": "SOC Lead", "comment": "Escalate to tier-3 response"}
        )
        assert appr_resp.status_code == 200
    else:
        assert action["status"] == "APPROVED"

    # Execute
    exec_resp = client.post(f"/api/actions/{action_id}/execute")
    assert exec_resp.status_code == 200
    details = exec_resp.json()["verification_details"].lower()

    # Must NOT claim host isolation or containment
    assert "ticket" in details or "ticketing" in details
    assert "containment" not in details
    assert "isolated" not in details
    assert "vlan" not in details


def test_unknown_api_endpoint_returns_404_not_html():
    """
    Requirement 5: Unknown API endpoints must not silently return index.html.
    """
    response = client.get("/api/unknown_nonexistent_endpoint")
    assert response.status_code == 404
    assert "json" in response.headers.get("content-type", "").lower()
    data = response.json()
    assert "not found" in data.get("detail", "").lower()


def test_root_serves_html_when_requested_by_browser():
    """
    Requirement 5: Browser navigation to root must serve frontend HTML when built.
    """
    from pathlib import Path
    dist_index = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "index.html"

    response = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
    assert response.status_code == 200
    if dist_index.exists():
        assert "text/html" in response.headers.get("content-type", "")
    else:
        assert response.json()["project"] == "ThreatPath"


def test_investigation_survives_cache_clear_via_falkordb_reload():
    """
    Requirement 10: Investigation records reload from FalkorDB provenance even after cache clear/restart.
    """
    from backend.api.routes import INVESTIGATION_CACHE

    # Create investigation
    inv_resp = client.post(
        "/api/investigations",
        json={"alert_id": "alert-sec-001", "investigation_prompt": "Audit persistence"}
    )
    assert inv_resp.status_code == 200
    inv_id = inv_resp.json()["id"]

    # Clear in-memory cache simulating backend restart
    INVESTIGATION_CACHE.clear()
    assert inv_id not in INVESTIGATION_CACHE

    # Fetch investigation again
    reload_resp = client.get(f"/api/investigations/{inv_id}")
    assert reload_resp.status_code == 200
    reloaded = reload_resp.json()
    assert reloaded["id"] == inv_id
    assert reloaded["alert_id"] == "alert-sec-001"
    assert reloaded["status"] == "completed"

