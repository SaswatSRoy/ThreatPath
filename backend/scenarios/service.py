"""
Custom Scenario Persistence Service for ThreatPath
Performs safe Cypher generation with server-side allowlists, session scoping, and idempotent MERGE operations.
"""
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.config import settings
from backend.database import db_manager
from backend.scenarios.schema import (
    CustomScenarioPayload,
    ScenarioSummary,
    ScenarioDetails,
    ALLOWED_NODE_LABELS,
    ALLOWED_RELATIONSHIPS
)
from backend.scenarios.validator import ScenarioValidator

logger = logging.getLogger(__name__)


class ScenarioService:
    def __init__(self, db=None):
        self.db = db or db_manager

    def save_scenario(
        self,
        raw_payload: Dict[str, Any],
        session_id: str = "demo_default",
        graph_name: Optional[str] = None
    ) -> ScenarioSummary:
        """
        Validate, create, and idempotently persist custom scenario nodes and edges into FalkorDB.
        Enforces strict server-side allowlists and session scoping.
        """
        sess = session_id or "demo_default"
        validation = ScenarioValidator.validate(raw_payload)
        if not validation.valid:
            error_details = "; ".join([f"{e.field}: {e.message}" for e in validation.errors])
            raise ValueError(f"Scenario validation failed: {error_details}")

        target_graph = graph_name or settings.FALKORDB_GRAPH
        logger.info(f"Persisting custom scenario in graph '{target_graph}' for session '{sess}'")

        payload = CustomScenarioPayload(**raw_payload)
        scenario_id = f"scen-{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).isoformat()
        alert = payload.alert

        # 1. Persist CustomScenario metadata node
        cs_query = """
        MERGE (cs:CustomScenario {id: $scenario_id, session_id: $session_id})
        SET cs.name = $name,
            cs.description = $description,
            cs.alert_id = $alert_id,
            cs.alert_title = $alert_title,
            cs.severity = $severity,
            cs.created_at = $created_at,
            cs.schema_version = $schema_version,
            cs.raw_json = $raw_json
        RETURN cs
        """
        cs_params = {
            "scenario_id": scenario_id,
            "session_id": sess,
            "name": payload.name,
            "description": payload.description or "",
            "alert_id": alert.id,
            "alert_title": alert.title,
            "severity": alert.severity.upper(),
            "created_at": created_at,
            "schema_version": payload.schema_version,
            "raw_json": json.dumps(raw_payload)
        }
        self.db.execute_query(cs_query, cs_params, graph_name=target_graph)

        # 2. Persist Alert node with session_id scoping
        alert_query = """
        MERGE (a:Alert {id: $id})
        SET a.title = $title,
            a.description = $description,
            a.severity = $severity,
            a.status = $status,
            a.timestamp = $timestamp,
            a.source = $source,
            a.alert_type = $alert_type,
            a.session_id = $session_id,
            a.scenario_id = $scenario_id,
            a.is_custom = true
        WITH a
        MATCH (cs:CustomScenario {id: $scenario_id, session_id: $session_id})
        MERGE (cs)-[:DEFINES_ALERT]->(a)
        """
        alert_params = {
            "id": alert.id,
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity.upper(),
            "status": alert.status.upper(),
            "timestamp": created_at,
            "source": alert.source or "CUSTOM_SCENARIO",
            "alert_type": alert.alert_type or "custom_synthetic",
            "session_id": sess,
            "scenario_id": scenario_id
        }
        self.db.execute_query(alert_query, alert_params, graph_name=target_graph)

        # 3. Persist Entities using safe allowlist templates
        for ent in payload.entities:
            label = ent.label
            if label not in ALLOWED_NODE_LABELS:
                raise ValueError(f"Disallowed node label: {label}")

            # Sanitized properties dictionary (scalars only)
            safe_props = {
                k: v for k, v in ent.properties.items()
                if isinstance(v, (str, int, float, bool))
            }
            safe_props["id"] = ent.id
            safe_props["session_id"] = sess
            safe_props["scenario_id"] = scenario_id

            # Node label template: label is strictly verified from allowlist set
            ent_query = f"""
            MERGE (n:{label} {{id: $id}})
            SET n += $props
            """
            self.db.execute_query(
                ent_query,
                {"id": ent.id, "props": safe_props},
                graph_name=target_graph
            )

        # 4. Persist Relationships using safe allowlist templates
        for rel in payload.relationships:
            rel_type = rel.type
            if rel_type not in ALLOWED_RELATIONSHIPS:
                raise ValueError(f"Disallowed relationship type: {rel_type}")

            rel_props = {
                k: v for k, v in rel.properties.items()
                if isinstance(v, (str, int, float, bool))
            }
            rel_props["session_id"] = sess
            rel_props["scenario_id"] = scenario_id

            rel_query = f"""
            MATCH (src {{id: $from_id}}), (tgt {{id: $to_id}})
            MERGE (src)-[r:{rel_type}]->(tgt)
            SET r += $props
            """
            self.db.execute_query(
                rel_query,
                {
                    "from_id": rel.from_,
                    "to_id": rel.to,
                    "props": rel_props
                },
                graph_name=target_graph
            )

        summary = ScenarioSummary(
            id=scenario_id,
            name=payload.name,
            description=payload.description or "",
            alert_id=alert.id,
            alert_title=alert.title,
            severity=alert.severity.upper(),
            created_at=created_at,
            node_count=1 + len(payload.entities),
            relationship_count=len(payload.relationships),
            session_id=sess
        )
        logger.info(f"Custom scenario '{scenario_id}' successfully persisted with {summary.node_count} nodes and {summary.relationship_count} edges.")
        return summary

    def list_scenarios(
        self,
        session_id: str = "demo_default",
        graph_name: Optional[str] = None
    ) -> List[ScenarioSummary]:
        """
        List custom scenarios created by the current session.
        Never returns scenarios belonging to other sessions.
        """
        sess = session_id or "demo_default"
        target_graph = graph_name or settings.FALKORDB_GRAPH

        query = """
        MATCH (cs:CustomScenario {session_id: $session_id})
        OPTIONAL MATCH (cs)-[:DEFINES_ALERT]->(a:Alert)
        RETURN cs.id AS id, cs.name AS name, cs.description AS description,
               cs.alert_id AS alert_id, cs.alert_title AS alert_title,
               cs.severity AS severity, cs.created_at AS created_at
        ORDER BY cs.created_at DESC
        """
        res = self.db.execute_query(query, {"session_id": sess}, graph_name=target_graph)
        scenarios: List[ScenarioSummary] = []

        for r in res.result_set:
            scenarios.append(ScenarioSummary(
                id=r[0],
                name=r[1] or "",
                description=r[2] or "",
                alert_id=r[3] or "",
                alert_title=r[4] or "",
                severity=r[5] or "HIGH",
                created_at=r[6] or "",
                node_count=0,
                relationship_count=0,
                session_id=sess
            ))
        return scenarios

    def get_scenario(
        self,
        scenario_id: str,
        session_id: str = "demo_default",
        graph_name: Optional[str] = None
    ) -> Optional[ScenarioDetails]:
        """
        Retrieve custom scenario details including raw JSON payload.
        Enforces session ownership: returns None if the scenario does not belong to the session.
        """
        sess = session_id or "demo_default"
        target_graph = graph_name or settings.FALKORDB_GRAPH

        query = """
        MATCH (cs:CustomScenario {id: $id, session_id: $session_id})
        RETURN cs.id AS id, cs.name AS name, cs.description AS description,
               cs.alert_id AS alert_id, cs.alert_title AS alert_title,
               cs.severity AS severity, cs.created_at AS created_at,
               cs.raw_json AS raw_json
        """
        res = self.db.execute_query(query, {"id": scenario_id, "session_id": sess}, graph_name=target_graph)
        if not res.result_set:
            return None

        r = res.result_set[0]
        try:
            raw_payload = json.loads(r[7]) if r[7] else {}
        except Exception:
            raw_payload = {}

        return ScenarioDetails(
            id=r[0],
            name=r[1] or "",
            description=r[2] or "",
            alert_id=r[3] or "",
            alert_title=r[4] or "",
            severity=r[5] or "HIGH",
            created_at=r[6] or "",
            node_count=len(raw_payload.get("entities", [])) + 1,
            relationship_count=len(raw_payload.get("relationships", [])),
            session_id=sess,
            payload=raw_payload
        )


scenario_service = ScenarioService()
