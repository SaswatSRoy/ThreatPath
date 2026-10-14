"""
Unit and Integration Tests for ThreatPath MCP Tools
Validates that each MCP tool produces structured, verifiable results against FalkorDB.
"""
import pytest
from backend.agent.tools import (
    tool_get_alert_context,
    tool_trace_attack_path,
    tool_find_related_alerts,
    tool_check_asset_exposure,
    tool_get_indicator_context,
    tool_record_investigation,
    tool_simulate_response,
    tool_execute_response,
    tool_verify_response
)
from backend.policy import simulated_env


@pytest.fixture(autouse=True)
def reset_env():
    simulated_env.reset()


def test_mcp_tool_get_alert_context():
    context = tool_get_alert_context("alert-sec-001")
    assert "alert" in context
    assert context["alert"]["id"] == "alert-sec-001"
    assert context["host"]["hostname"] == "jump-prod-01.corp.internal"
    assert context["identity"]["username"] == "jdoe"
    assert len(context["techniques"]) >= 1


def test_mcp_tool_trace_attack_path():
    res = tool_trace_attack_path("alert-sec-001")
    assert res["path_count"] >= 1
    assert len(res["processes"]) >= 1
    assert res["processes"][0]["name"] == "powershell.exe"
    assert len(res["indicators"]) >= 1
    assert res["indicators"][0]["value"] == "198.51.100.44"


def test_mcp_tool_check_asset_exposure():
    exposures = tool_check_asset_exposure("alert-sec-001")
    assert len(exposures) >= 1
    exp = exposures[0]
    assert exp["asset_name"] == "Customer Records Database"
    assert exp["criticality"] == "CRITICAL"


def test_mcp_tool_get_indicator_context():
    indicators = tool_get_indicator_context("alert-sec-001")
    assert len(indicators) >= 1
    ind = indicators[0]
    assert ind["value"] == "198.51.100.44"
    assert ind["reputation"] == "MALICIOUS"
    assert ind["malicious_score"] == 95


def test_mcp_tool_record_investigation():
    result = tool_record_investigation(
        investigation_id="test-inv-001",
        alert_id="alert-sec-001",
        classification="likely_compromise",
        priority="critical",
        raw_score=0.90,
        narrative="Multi-hop graph traversal verified hostile C2 beaconing."
    )
    assert result["status"] == "persisted"
    assert result["investigation_id"] == "test-inv-001"


def test_mcp_tool_simulate_and_verify_response():
    # 1. Propose simulated action (ALLOW policy -> pre-approved)
    action = tool_simulate_response(
        action_type="SIMULATE_BLOCK_INDICATOR",
        target_entity="ind-c2-ip",
        target_type="indicator",
        justification="Block known malicious IP"
    )
    assert action["status"] == "APPROVED"

    # 2. Execute simulation (mutates state and automatically verifies)
    executed = tool_execute_response(action["id"])
    assert executed["status"] == "VERIFIED"
    assert "firewall rule applied" in executed["verification_details"]

    # 3. Direct verification tool confirms verified state
    verified = tool_verify_response(action["id"])
    assert verified["status"] == "VERIFIED"
