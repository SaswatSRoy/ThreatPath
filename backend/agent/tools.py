"""
Typed Domain Investigation & Response Tools for ThreatPath
Used by both the internal Agent Orchestrator and the external MCP Server.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.cypher_queries import graph_queries
from backend.policy import policy_engine, simulated_env
from backend.models import ResponseActionType


def tool_get_alert_context(alert_id: str, graph_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve immediate contextual envelope for an alert: target host, identity, event details, and techniques.
    """
    return graph_queries.get_alert_context(alert_id, graph_name=graph_name)


def tool_trace_attack_path(alert_id: str, graph_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Discover multi-hop causal paths from Alert to Host, executed Process, and external Indicator.
    """
    res = graph_queries.get_attack_paths(alert_id, graph_name=graph_name)
    serialized_paths = []
    for p in res.get("paths", []):
        serialized_paths.append([n.properties.get("id") for n in p.nodes()])
    return {
        "path_count": len(res.get("paths", [])),
        "paths": serialized_paths,
        "processes": res.get("processes", []),
        "indicators": res.get("indicators", [])
    }


def tool_find_related_alerts(alert_id: str, graph_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Find other security alerts connected through identical hosts or identities.
    """
    return graph_queries.get_related_alerts(alert_id, graph_name=graph_name)


def tool_check_asset_exposure(alert_id: str, graph_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Query whether hosts involved in the alert maintain access paths to critical data assets.
    """
    raw = graph_queries.get_asset_exposure(alert_id, graph_name=graph_name)
    return [
        {
            "hostname": r["hostname"],
            "asset_id": r["asset_id"],
            "asset_name": r["asset_name"],
            "criticality": r["criticality"],
            "classification": r["classification"]
        }
        for r in raw
    ]


def tool_get_indicator_context(alert_id: str, graph_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve intelligence context and reputation scores for network indicators connected to the alert.
    """
    res = graph_queries.get_attack_paths(alert_id, graph_name=graph_name)
    indicators = res.get("indicators", [])
    return indicators


def tool_record_investigation(
    investigation_id: str,
    alert_id: str,
    classification: str,
    priority: str,
    raw_score: float,
    narrative: str,
    graph_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Persist the investigation provenance and findings into FalkorDB.
    """
    now_str = datetime.now(timezone.utc).isoformat()
    graph_queries.persist_investigation(
        investigation_id=investigation_id,
        alert_id=alert_id,
        started_at=now_str,
        completed_at=now_str,
        classification=classification,
        priority=priority,
        raw_score=raw_score,
        narrative=narrative,
        graph_name=graph_name
    )
    return {
        "status": "persisted",
        "investigation_id": investigation_id,
        "alert_id": alert_id,
        "timestamp": now_str
    }


def tool_simulate_response(
    action_type: str,
    target_entity: str,
    target_type: str = "host",
    justification: str = "Automated remediation simulation"
) -> Dict[str, Any]:
    """
    Propose a simulated defensive response action through the policy gate.
    If approval is required, stays in WAITING_FOR_APPROVAL. If allowed, moves to APPROVED.
    """
    try:
        act_enum = ResponseActionType(action_type)
    except ValueError:
        raise ValueError(f"Invalid response action type: {action_type}. Allowed: {[e.value for e in ResponseActionType]}")

    record = policy_engine.propose_action(
        action_type=act_enum,
        target_entity=target_entity,
        target_type=target_type,
        justification=justification
    )
    return record.model_dump()


def tool_execute_response(action_id: str) -> Dict[str, Any]:
    """
    Execute an approved simulated defensive action, mutating the simulated state.
    """
    record = policy_engine.execute_simulation(action_id)
    return record.model_dump()


def tool_verify_response(action_id: str) -> Dict[str, Any]:
    """
    Inspect the simulated fleet state to verify that the defensive response action succeeded.
    """
    record = policy_engine.verify_simulation(action_id)
    return record.model_dump()
