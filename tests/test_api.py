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
