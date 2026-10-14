"""
ThreatPath Autonomous Agent Orchestrator
Coordinates graph tool queries, deterministic assessment, explanation, policy gating, and persistence.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from backend.config import settings
from backend.models import (
    InvestigationRecord,
    ResponseActionType,
    CompromiseClassification,
    ActionStatus
)
from backend.cypher_queries import graph_queries
from backend.scoring import assessment_engine
from backend.policy import policy_engine
from backend.agent.llm_provider import llm_provider

logger = logging.getLogger(__name__)


class InvestigationOrchestrator:
    """
    Agent workflow:
    Investigation Request
      -> Input Validation & Alert Resolution
      -> FalkorDB Graph Tool Traversals (Alert Context, Attack Paths, Assets, Vulnerabilities, Related Alerts)
      -> Deterministic Assessment Engine (Rules & Heuristic Factors)
      -> Evidence-Grounded Explanation (Distinguishing Observed, Correlated, Inferred, Unknown)
      -> Response Policy & Approval Gating
      -> FalkorDB Provenance Persistence
      -> Return Investigation Record
    """

    def __init__(self, queries=None):
        self.queries = queries or graph_queries

    def investigate_alert(
        self,
        alert_id: str,
        user_prompt: Optional[str] = None,
        graph_name: Optional[str] = None,
        session_id: str = "demo_default"
    ) -> InvestigationRecord:
        investigation_id = f"inv-{uuid.uuid4().hex[:8]}"
        started_at = datetime.now(timezone.utc).isoformat()
        target_graph = graph_name or settings.FALKORDB_GRAPH

        logger.info(f"Starting investigation '{investigation_id}' for alert '{alert_id}' on graph '{target_graph}'")

        # 1. Resolve Alert
        alert_summary = self.queries.get_alert_by_id(alert_id, graph_name=target_graph)
        if not alert_summary:
            raise ValueError(f"Alert with ID '{alert_id}' not found in graph '{target_graph}'.")

        alert_dict = alert_summary.model_dump()

        # 2. Execute Graph Investigation Queries
        context = self.queries.get_alert_context(alert_id, graph_name=target_graph)
        attack_paths = self.queries.get_attack_paths(alert_id, graph_name=target_graph)
        asset_exposures = self.queries.get_asset_exposure(alert_id, graph_name=target_graph)
        vuln_exposures = self.queries.get_vulnerability_exposure(alert_id, graph_name=target_graph)
        related_alerts = self.queries.get_related_alerts(alert_id, graph_name=target_graph)

        # 3. Retrieve Full Subgraph for Cytoscape.js Visualization
        subgraph = self.queries.get_full_investigation_graph(alert_id, graph_name=target_graph)

        # 4. Deterministic Assessment
        assessment = assessment_engine.assess_investigation(
            alert=alert_dict,
            context=context,
            attack_paths=attack_paths,
            asset_exposures=asset_exposures,
            vuln_exposures=vuln_exposures,
            related_alerts=related_alerts
        )

        # 5. Evidence-Grounded Narrative Explanation
        explanation_result = llm_provider.generate_investigation_narrative(
            alert=alert_dict,
            context=context,
            assessment=assessment,
            user_prompt=user_prompt
        )
        narrative = explanation_result["narrative"]
        operating_mode = explanation_result["mode"]

        # 6. Response Policy & Proposed Simulation
        recommended_action = None
        target_host = context.get("host", {}).get("id") or context.get("host", {}).get("hostname")

        if assessment.classification == CompromiseClassification.LIKELY_COMPROMISE and target_host:
            # High-impact containment requires approval
            recommended_action = policy_engine.propose_action(
                action_type=ResponseActionType.SIMULATE_ISOLATE_HOST,
                target_entity=target_host,
                target_type="host",
                justification=f"Immediate host isolation proposed to sever active C2 connection and protect critical assets.",
                investigation_id=investigation_id,
                session_id=session_id
            )
        elif assessment.classification == CompromiseClassification.SUSPICIOUS:
            # Perimeter block or escalate
            if attack_paths.get("indicators"):
                ind_id = attack_paths["indicators"][0].get("id")
                recommended_action = policy_engine.propose_action(
                    action_type=ResponseActionType.SIMULATE_BLOCK_INDICATOR,
                    target_entity=ind_id,
                    target_type="indicator",
                    justification="Propose perimeter block for suspicious external IP.",
                    investigation_id=investigation_id,
                    session_id=session_id
                )
            else:
                recommended_action = policy_engine.propose_action(
                    action_type=ResponseActionType.SIMULATE_ESCALATE_INCIDENT,
                    target_entity=alert_id,
                    target_type="incident",
                    justification="Vulnerable host exposure requires prioritized patch remediation ticket.",
                    investigation_id=investigation_id,
                    session_id=session_id
                )

        completed_at = datetime.now(timezone.utc).isoformat()

        # 7. Persist Provenance in FalkorDB
        try:
            self.queries.persist_investigation(
                investigation_id=investigation_id,
                alert_id=alert_id,
                started_at=started_at,
                completed_at=completed_at,
                classification=assessment.classification.value,
                priority=assessment.remediation_priority.value,
                raw_score=assessment.raw_score,
                narrative=narrative[:1000],  # Bound text in graph property
                graph_name=target_graph
            )
            if recommended_action:
                self.queries.persist_response_action(
                    action_id=recommended_action.id,
                    investigation_id=investigation_id,
                    action_type=recommended_action.action_type.value,
                    target_entity=recommended_action.target_entity,
                    status=recommended_action.status.value,
                    policy_decision=recommended_action.policy_decision.value,
                    justification=recommended_action.justification,
                    proposed_at=recommended_action.proposed_at,
                    graph_name=target_graph
                )
        except Exception as e:
            logger.warning(f"Could not persist investigation provenance to FalkorDB: {e}")

        # Assemble Investigation Record
        record = InvestigationRecord(
            id=investigation_id,
            alert_id=alert_id,
            started_at=started_at,
            completed_at=completed_at,
            status="completed",
            mode=operating_mode,
            assessment=assessment,
            narrative=narrative,
            graph=subgraph,
            recommended_action=recommended_action,
            provenance_path_count=len(subgraph.edges)
        )

        return record


orchestrator = InvestigationOrchestrator()
