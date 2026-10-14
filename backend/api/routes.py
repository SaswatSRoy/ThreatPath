"""
ThreatPath REST API Endpoints
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Header
from backend.config import settings
from backend.database import db_manager
from backend.cypher_queries import graph_queries
from backend.agent.orchestrator import orchestrator
from backend.policy import policy_engine, simulated_env
from backend.models import (
    AlertSummary,
    InvestigationRecord,
    InvestigationRequest,
    ResponseActionRecord,
    ActionApprovalRequest,
    ActionDenialRequest,
    GraphData,
    Assessment,
    CompromiseClassification,
    RemediationPriority
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# In-memory investigation registry for active session retrieval
INVESTIGATION_CACHE: Dict[str, InvestigationRecord] = {}


@router.get("/health")
def get_health() -> Dict[str, Any]:
    """
    Healthcheck endpoint verifying FalkorDB reachability and operational mode.
    """
    try:
        client = db_manager.get_client()
        graphs = client.list_graphs()
        db_ok = settings.FALKORDB_GRAPH in graphs
    except Exception as e:
        logger.error(f"Healthcheck database connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"FalkorDB unreachable at {settings.FALKORDB_HOST}:{settings.FALKORDB_PORT}"
        )

    return {
        "status": "healthy",
        "falkordb_status": "connected" if db_ok else "graph_missing",
        "active_graph": settings.FALKORDB_GRAPH,
        "available_graphs": graphs,
        "llm_mode": "deterministic" if settings.LLM_PROVIDER in ["mock", "deterministic"] else "external",
        "simulated_responses_enabled": settings.ENABLE_SIMULATED_RESPONSES
    }


@router.get("/alerts", response_model=List[AlertSummary])
def list_alerts() -> List[AlertSummary]:
    """
    Retrieve all security alerts available in the FalkorDB graph.
    """
    try:
        return graph_queries.get_all_alerts()
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/alerts/{alert_id}", response_model=AlertSummary)
def get_alert(alert_id: str) -> AlertSummary:
    """
    Retrieve specific alert by ID.
    """
    alert = graph_queries.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found")
    return alert


@router.post("/investigations", response_model=InvestigationRecord)
def create_investigation(
    request: InvestigationRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> InvestigationRecord:
    """
    Trigger autonomous graph-native investigation for the requested alert.
    Queries FalkorDB, executes deterministic scoring, generates narrative, and persists provenance.
    """
    try:
        record = orchestrator.investigate_alert(
            alert_id=request.alert_id,
            user_prompt=request.investigation_prompt,
            session_id=x_session_id or "demo_default"
        )
        INVESTIGATION_CACHE[record.id] = record
        return record
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Investigation execution failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/investigations/{investigation_id}", response_model=InvestigationRecord)
def get_investigation(investigation_id: str) -> InvestigationRecord:
    """
    Retrieve cached or persisted investigation record.
    """
    if investigation_id in INVESTIGATION_CACHE:
        return INVESTIGATION_CACHE[investigation_id]

    # Attempt to reload from FalkorDB provenance
    try:
        query = """
        MATCH (inv:Investigation {id: $id})-[:INVESTIGATES]->(a:Alert)
        OPTIONAL MATCH (inv)-[:RECOMMENDED_ACTION]->(ra:ResponseAction)
        RETURN inv.id, inv.alert_id, inv.started_at, inv.completed_at,
               inv.classification, inv.priority, inv.raw_score, inv.narrative,
               ra.id
        """
        res = db_manager.execute_query(query, {"id": investigation_id})
        if res.result_set:
            row = res.result_set[0]
            alert_id = row[1]
            subgraph = graph_queries.get_full_investigation_graph(alert_id)
            ra_id = row[8]
            rec_action = simulated_env.get_action(ra_id) if ra_id else None

            assessment = Assessment(
                classification=CompromiseClassification(row[4]),
                raw_score=float(row[6]) if row[6] is not None else 0.5,
                remediation_priority=RemediationPriority(row[5]),
                uncertainty_explanation=""
            )
            record = InvestigationRecord(
                id=row[0],
                alert_id=alert_id,
                started_at=row[2],
                completed_at=row[3],
                status="completed",
                mode="deterministic",
                assessment=assessment,
                narrative=row[7] or "",
                graph=subgraph,
                recommended_action=rec_action,
                provenance_path_count=len(subgraph.edges)
            )
            INVESTIGATION_CACHE[investigation_id] = record
            return record
    except Exception as e:
        logger.debug(f"Could not load investigation {investigation_id} from FalkorDB: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Investigation '{investigation_id}' not found in current session cache"
    )


@router.get("/investigations/{investigation_id}/evidence")
def get_investigation_evidence(investigation_id: str) -> Dict[str, Any]:
    """
    Retrieve structured evidence items, score factors, and graph representation.
    """
    record = get_investigation(investigation_id)
    return {
        "investigation_id": record.id,
        "alert_id": record.alert_id,
        "classification": record.assessment.classification,
        "priority": record.assessment.remediation_priority,
        "raw_score": record.assessment.raw_score,
        "score_factors": record.assessment.score_factors,
        "supporting_evidence_ids": record.assessment.supporting_evidence_ids,
        "contradictory_evidence_ids": record.assessment.contradictory_evidence_ids,
        "missing_evidence": record.assessment.missing_evidence,
        "graph": record.graph
    }


@router.post("/actions/{action_id}/approve", response_model=ResponseActionRecord)
def approve_action(action_id: str, payload: ActionApprovalRequest) -> ResponseActionRecord:
    """
    Analyst approval gate: Approves a proposed simulated action.
    """
    try:
        updated = policy_engine.approve_action(action_id, approver=payload.approver)
        # Update cached investigation action if linked
        if updated.investigation_id and updated.investigation_id in INVESTIGATION_CACHE:
            INVESTIGATION_CACHE[updated.investigation_id].recommended_action = updated
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/actions/{action_id}/deny", response_model=ResponseActionRecord)
def deny_action(action_id: str, payload: ActionDenialRequest) -> ResponseActionRecord:
    """
    Analyst approval gate: Denies a proposed simulated action.
    """
    try:
        updated = policy_engine.deny_action(action_id, reason=payload.reason, approver=payload.approver)
        if updated.investigation_id and updated.investigation_id in INVESTIGATION_CACHE:
            INVESTIGATION_CACHE[updated.investigation_id].recommended_action = updated
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/actions/{action_id}/execute", response_model=ResponseActionRecord)
def execute_action(action_id: str) -> ResponseActionRecord:
    """
    Execute simulated defensive action against the simulated fleet.
    Enforces approval gate: will reject unapproved high-consequence actions.
    """
    try:
        updated = policy_engine.execute_simulation(action_id)
        if updated.investigation_id and updated.investigation_id in INVESTIGATION_CACHE:
            INVESTIGATION_CACHE[updated.investigation_id].recommended_action = updated
        return updated
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/actions/{action_id}/verify", response_model=ResponseActionRecord)
def verify_action(action_id: str) -> ResponseActionRecord:
    """
    Inspect simulated state to verify action outcome.
    """
    try:
        updated = policy_engine.verify_simulation(action_id)
        if updated.investigation_id and updated.investigation_id in INVESTIGATION_CACHE:
            INVESTIGATION_CACHE[updated.investigation_id].recommended_action = updated
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
