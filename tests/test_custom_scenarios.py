"""
Comprehensive Tests for ThreatPath Custom Scenario Lab
Covers validation rules, endpoint type checking, safe persistence, session isolation, and investigation integration.
"""
import copy
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.scenarios.templates import CANONICAL_ENDPOINT_SCENARIO
from backend.scenarios.validator import ScenarioValidator
from backend.policy import simulated_env

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_policy_env():
    simulated_env.reset()


def test_validate_canonical_endpoint_scenario():
    """
    Validation succeeds for the canonical endpoint scenario fixture.
    Produces valid: True, zero fatal errors, and an offline Cytoscape graph preview.
    """
    res = client.post("/api/scenarios/validate", json=CANONICAL_ENDPOINT_SCENARIO)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert len(data["errors"]) == 0
    assert data["preview"] is not None
    assert len(data["preview"]["nodes"]) == 6  # 1 Alert + 5 Entities
    assert len(data["preview"]["edges"]) == 6


def test_validate_rejects_non_dict_root():
    """Validation rejects payloads that are not JSON objects."""
    res = client.post("/api/scenarios/validate", json=["not", "an", "object"])
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert any(e["code"] == "INVALID_ROOT_TYPE" for e in data["errors"])


def test_validate_rejects_unsupported_schema_version():
    """Validation rejects unsupported schema versions."""
    bad_payload = copy.deepcopy(CANONICAL_ENDPOINT_SCENARIO)
    bad_payload["schema_version"] = "9.9"
    res = client.post("/api/scenarios/validate", json=bad_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert any(e["code"] == "UNSUPPORTED_SCHEMA_VERSION" for e in data["errors"])


def test_validate_rejects_empty_name_or_alert_title():
    """Validation requires non-empty scenario name and alert title."""
    bad_payload = copy.deepcopy(CANONICAL_ENDPOINT_SCENARIO)
    bad_payload["name"] = "   "
    bad_payload["alert"]["title"] = ""
    res = client.post("/api/scenarios/validate", json=bad_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    codes = [e["code"] for e in data["errors"]]
    assert "EMPTY_SCENARIO_NAME" in codes
    assert "MISSING_ALERT_TITLE" in codes


def test_validate_rejects_invalid_severity_and_status():
    """Validation enforces allowlisted severity and status values."""
    bad_payload = copy.deepcopy(CANONICAL_ENDPOINT_SCENARIO)
    bad_payload["alert"]["severity"] = "SUPER_CRITICAL_OMG"
    bad_payload["alert"]["status"] = "PENDING_REVIEW"
    res = client.post("/api/scenarios/validate", json=bad_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    codes = [e["code"] for e in data["errors"]]
    assert "INVALID_SEVERITY" in codes
    assert "INVALID_STATUS" in codes


def test_validate_rejects_duplicate_entity_ids():
    """Validation rejects duplicate entity IDs within the payload."""
    bad_payload = copy.deepcopy(CANONICAL_ENDPOINT_SCENARIO)
    # Add a duplicate host ID
    bad_payload["entities"].append({
        "id": "host-custom-001",
        "label": "Host",
        "properties": {"hostname": "duplicate-host"}
    })
    res = client.post("/api/scenarios/validate", json=bad_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert any(e["code"] == "DUPLICATE_ENTITY_ID" for e in data["errors"])


def test_validate_rejects_unsupported_node_labels():
    """Validation rejects node labels that are not in the server allowlist."""
    bad_payload = copy.deepcopy(CANONICAL_ENDPOINT_SCENARIO)
    bad_payload["entities"].append({
        "id": "arbitrary-001",
        "label": "ArbitraryCloudBucket",
        "properties": {}
    })
    res = client.post("/api/scenarios/validate", json=bad_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert any(e["code"] == "UNSUPPORTED_NODE_LABEL" for e in data["errors"])


def test_validate_rejects_unsupported_relationship_types():
    """Validation rejects relationship types that are not in the server allowlist."""
    bad_payload = copy.deepcopy(CANONICAL_ENDPOINT_SCENARIO)
    bad_payload["relationships"].append({
        "from": "host-custom-001",
        "type": "DOWNLOADED_PAYLOAD_FROM",
        "to": "event-custom-001"
    })
    res = client.post("/api/scenarios/validate", json=bad_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert any(e["code"] == "UNSUPPORTED_RELATIONSHIP_TYPE" for e in data["errors"])


def test_validate_rejects_undeclared_relationship_endpoints():
    """Validation rejects relationships referencing undeclared entity IDs."""
    bad_payload = copy.deepcopy(CANONICAL_ENDPOINT_SCENARIO)
    bad_payload["relationships"].append({
        "from": "event-custom-001",
        "type": "OCCURRED_ON",
        "to": "host-ghost-nonexistent"
    })
    res = client.post("/api/scenarios/validate", json=bad_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert any(e["code"] == "UNDECLARED_RELATIONSHIP_TARGET" for e in data["errors"])


def test_validate_rejects_invalid_relationship_endpoint_types():
    """
    Validation enforces domain directionality and endpoint label types.
    OCCURRED_ON must be Event -> Host; reversing it or connecting Host -> Process fails.
    """
    bad_payload = copy.deepcopy(CANONICAL_ENDPOINT_SCENARIO)
    # Erroneous relationship: OCCURRED_ON from Host to Event (reversed)
    bad_payload["relationships"].append({
        "from": "host-custom-001",
        "type": "OCCURRED_ON",
        "to": "event-custom-001"
    })
    res = client.post("/api/scenarios/validate", json=bad_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert any(e["code"] == "INVALID_RELATIONSHIP_SOURCE_TYPE" for e in data["errors"])


def test_validate_rejects_nested_property_objects():
    """Validation rejects complex nested JSON structures in entity properties."""
    bad_payload = copy.deepcopy(CANONICAL_ENDPOINT_SCENARIO)
    bad_payload["entities"][0]["properties"]["nested_injected"] = {"cypher": "DROP ALL"}
    res = client.post("/api/scenarios/validate", json=bad_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert any(e["code"] == "NESTED_PROPERTY_NOT_ALLOWED" for e in data["errors"])


def test_validate_reports_actionable_warnings():
    """Validation reports non-fatal warnings when scenario lacks Host or Indicator."""
    payload = {
        "schema_version": "1.0",
        "name": "Minimal Event Alert",
        "alert": {
            "id": "alert-minimal-001",
            "title": "Minimal Alert",
            "severity": "LOW",
            "status": "NEW"
        },
        "entities": [
            {
                "id": "event-min-001",
                "label": "Event",
                "properties": {"event_type": "audit_log"}
            }
        ],
        "relationships": [
            {
                "from": "alert-minimal-001",
                "type": "HAS_EVENT",
                "to": "event-min-001"
            }
        ]
    }
    res = client.post("/api/scenarios/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert len(data["errors"]) == 0
    assert len(data["warnings"]) >= 2
    warn_text = " ".join(data["warnings"])
    assert "Host" in warn_text
    assert "Indicator" in warn_text


def test_scenario_persistence_and_session_isolation():
    """
    Tests saving a custom scenario and verifies strict session isolation:
    - Session A creates custom scenario.
    - Session A can list and retrieve it.
    - Session B CANNOT list or retrieve Session A's scenario (returns 404).
    - Session B's alert queue does NOT display Session A's custom scenario.
    """
    session_a = "session-alice-123"
    session_b = "session-bob-456"

    payload = copy.deepcopy(CANONICAL_ENDPOINT_SCENARIO)
    payload["name"] = "Alice Private Scenario"
    payload["alert"]["id"] = "alert-alice-001"
    payload["alert"]["title"] = "Alice Security Event"
    payload["relationships"][0]["from"] = "alert-alice-001"

    # 1. Session A saves scenario
    save_res = client.post(
        "/api/scenarios",
        json=payload,
        headers={"X-Session-ID": session_a}
    )
    assert save_res.status_code == 201
    summary = save_res.json()
    scen_id = summary["id"]
    assert summary["name"] == "Alice Private Scenario"
    assert summary["alert_id"] == "alert-alice-001"

    # 2. Session A lists scenarios -> finds it
    list_a = client.get("/api/scenarios", headers={"X-Session-ID": session_a}).json()
    assert any(s["id"] == scen_id for s in list_a)

    # 3. Session B lists scenarios -> does NOT find it
    list_b = client.get("/api/scenarios", headers={"X-Session-ID": session_b}).json()
    assert not any(s["id"] == scen_id for s in list_b)

    # 4. Session A retrieves specific scenario by ID -> 200 OK
    get_a = client.get(f"/api/scenarios/{scen_id}", headers={"X-Session-ID": session_a})
    assert get_a.status_code == 200
    assert get_a.json()["id"] == scen_id

    # 5. Session B attempts to retrieve Session A's scenario -> 404 NOT FOUND
    get_b = client.get(f"/api/scenarios/{scen_id}", headers={"X-Session-ID": session_b})
    assert get_b.status_code == 404

    # 6. Session A lists alerts -> includes alert-alice-001
    alerts_a = client.get("/api/alerts", headers={"X-Session-ID": session_a}).json()
    assert any(a["id"] == "alert-alice-001" for a in alerts_a)

    # 7. Session B lists alerts -> alert-alice-001 is completely excluded
    alerts_b = client.get("/api/alerts", headers={"X-Session-ID": session_b}).json()
    assert not any(a["id"] == "alert-alice-001" for a in alerts_b)

    # 8. Unauthenticated / global alerts list excludes alert-alice-001
    alerts_global = client.get("/api/alerts").json()
    assert not any(a["id"] == "alert-alice-001" for a in alerts_global)


def test_investigation_on_custom_scenario():
    """
    End-to-end investigation workflow on a saved custom scenario:
    - Investigates alert-alice-001 under Session A.
    - Verifies graph traversal collects custom entities.
    - Verifies deterministic scoring identifies ATT&CK technique and missing C2 beacon.
    - Proves the investigation does not invent relationships or false compromise.
    - Verifies Session B cannot trigger investigation on Session A's alert.
    """
    session_a = "session-alice-123"
    session_b = "session-bob-456"

    # 1. Session B attempts to investigate Session A's alert -> 404 NOT FOUND
    inv_b = client.post(
        "/api/investigations",
        json={"alert_id": "alert-alice-001", "investigation_prompt": "Attempt unauthorized investigation"},
        headers={"X-Session-ID": session_b}
    )
    assert inv_b.status_code == 404

    # 2. Session A triggers investigation
    inv_a = client.post(
        "/api/investigations",
        json={"alert_id": "alert-alice-001", "investigation_prompt": "Investigate PowerShell bypass"},
        headers={"X-Session-ID": session_a}
    )
    assert inv_a.status_code == 200
    record = inv_a.json()

    # 3. Verify graph evidence
    graph_nodes = record["graph"]["nodes"]
    node_ids = [n["id"] for n in graph_nodes]
    assert "alert-alice-001" in node_ids
    assert "workstation-17.corp.internal" in [n["label"] for n in graph_nodes]
    assert "powershell.exe" in [n["label"] for n in graph_nodes]

    # Historical CustomScenario metadata node must NOT be in evidence graph
    for n in graph_nodes:
        assert n["category"] != "CustomScenario"

    # 4. Verify assessment: observed suspicious command, but no confirmed C2 beacon
    assessment = record["assessment"]
    # Classification must NOT be likely_compromise because there is no external C2 beacon
    assert assessment["classification"] in ["suspicious", "insufficient_evidence"]
    assert assessment["classification"] != "likely_compromise"
    assert any("beaconing" in m.lower() for m in assessment["missing_evidence"])

    # 5. Verify ATT&CK alignment score factor was detected
    factor_names = [f["factor_name"] for f in assessment["score_factors"]]
    assert "MITRE ATT&CK Alignment" in factor_names


def test_get_scenario_template_endpoint():
    """GET /api/scenarios/template returns the canonical fixture."""
    res = client.get("/api/scenarios/template")
    assert res.status_code == 200
    data = res.json()
    assert data["schema_version"] == "1.0"
    assert "PowerShell" in data["name"]
    assert data["alert"]["id"] == "alert-custom-001"
