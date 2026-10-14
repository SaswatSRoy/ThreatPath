"""
Official FalkorDB-Native MCP Server for ThreatPath
Exposes domain-specific defensive investigation and simulation tools via MCP protocol.
"""
import sys
import logging
from typing import Dict, Any, List, Optional
from mcp.server.mcpserver import MCPServer
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

logger = logging.getLogger(__name__)

mcp = MCPServer("threatpath-mcp")


@mcp.tool()
def get_alert_context(alert_id: str) -> Dict[str, Any]:
    """
    Retrieve immediate contextual envelope for a security alert from FalkorDB:
    returns target host, identity, event details, and ATT&CK techniques.
    """
    return tool_get_alert_context(alert_id)


@mcp.tool()
def trace_attack_path(alert_id: str) -> Dict[str, Any]:
    """
    Trace multi-hop causal attack paths from Alert to Host, executed Process,
    and external C2 Indicator in FalkorDB.
    """
    return tool_trace_attack_path(alert_id)


@mcp.tool()
def find_related_alerts(alert_id: str) -> List[Dict[str, Any]]:
    """
    Find correlated alerts that share common Hosts, Identities, or Indicators in FalkorDB.
    """
    return tool_find_related_alerts(alert_id)


@mcp.tool()
def check_asset_exposure(alert_id: str) -> List[Dict[str, Any]]:
    """
    Identify whether any host involved in the incident has access paths to high-value assets.
    """
    return tool_check_asset_exposure(alert_id)


@mcp.tool()
def get_indicator_context(alert_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve threat intelligence scores, reputation, and indicator types for connected network IOCs.
    """
    return tool_get_indicator_context(alert_id)


@mcp.tool()
def record_investigation(
    investigation_id: str,
    alert_id: str,
    classification: str,
    priority: str,
    raw_score: float,
    narrative: str
) -> Dict[str, Any]:
    """
    Persist the completed investigation provenance, classification, and narrative into FalkorDB.
    """
    return tool_record_investigation(
        investigation_id=investigation_id,
        alert_id=alert_id,
        classification=classification,
        priority=priority,
        raw_score=raw_score,
        narrative=narrative
    )


@mcp.tool()
def simulate_response(
    action_type: str,
    target_entity: str,
    target_type: str = "host",
    justification: str = "Automated remediation simulation"
) -> Dict[str, Any]:
    """
    Propose a safe, simulated defensive response action (e.g. SIMULATE_ISOLATE_HOST)
    governed by the deterministic policy approval gate.
    """
    return tool_simulate_response(
        action_type=action_type,
        target_entity=target_entity,
        target_type=target_type,
        justification=justification
    )


@mcp.tool()
def execute_response(action_id: str) -> Dict[str, Any]:
    """
    Execute an approved simulated defensive action, mutating the simulated fleet state.
    """
    return tool_execute_response(action_id)


@mcp.tool()
def verify_response(action_id: str) -> Dict[str, Any]:
    """
    Inspect the simulated fleet state to cryptographically verify that the defensive action succeeded.
    """
    return tool_verify_response(action_id)


def start_server():
    """
    Run MCP server using stdio transport.
    """
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting ThreatPath MCP Server on stdio transport...")
    mcp.run("stdio")


if __name__ == "__main__":
    start_server()
