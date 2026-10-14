"""
Parameterized Cypher Query Wrappers for ThreatPath
"""
import logging
from typing import Dict, Any, List, Optional
from backend.database import db_manager
from backend.models import GraphData, AlertSummary

logger = logging.getLogger(__name__)


class ThreatPathGraphQueries:
    def __init__(self, db=None):
        self.db = db or db_manager

    def get_all_alerts(self, graph_name: Optional[str] = None) -> List[AlertSummary]:
        """
        Retrieve all alerts currently registered in the graph.
        """
        query = """
        MATCH (a:Alert)
        OPTIONAL MATCH (a)-[:HAS_EVENT]->(e:Event)-[:OCCURRED_ON]->(h:Host)
        OPTIONAL MATCH (e)-[:INVOLVES_IDENTITY]->(i:Identity)
        RETURN a.id AS id, a.title AS title, a.description AS description,
               a.severity AS severity, a.status AS status, a.timestamp AS timestamp,
               a.source AS source, a.alert_type AS alert_type,
               h.hostname AS target_host, i.username AS target_identity
        ORDER BY a.timestamp DESC
        """
        res = self.db.execute_query(query, graph_name=graph_name)
        alerts = []
        for r in res.result_set:
            alerts.append(AlertSummary(
                id=r[0],
                title=r[1] or "",
                description=r[2] or "",
                severity=r[3] or "LOW",
                status=r[4] or "NEW",
                timestamp=r[5] or "",
                source=r[6] or "",
                alert_type=r[7] or "",
                target_host=r[8],
                target_identity=r[9]
            ))
        return alerts

    def get_alert_by_id(self, alert_id: str, graph_name: Optional[str] = None) -> Optional[AlertSummary]:
        """
        Retrieve an individual alert by ID.
        """
        query = """
        MATCH (a:Alert)
        WHERE a.id = $alert_id
        OPTIONAL MATCH (a)-[:HAS_EVENT]->(e:Event)-[:OCCURRED_ON]->(h:Host)
        OPTIONAL MATCH (e)-[:INVOLVES_IDENTITY]->(i:Identity)
        RETURN a.id AS id, a.title AS title, a.description AS description,
               a.severity AS severity, a.status AS status, a.timestamp AS timestamp,
               a.source AS source, a.alert_type AS alert_type,
               h.hostname AS target_host, i.username AS target_identity
        """
        res = self.db.execute_query(query, {"alert_id": alert_id}, graph_name=graph_name)
        if not res.result_set:
            return None
        r = res.result_set[0]
        return AlertSummary(
            id=r[0],
            title=r[1] or "",
            description=r[2] or "",
            severity=r[3] or "LOW",
            status=r[4] or "NEW",
            timestamp=r[5] or "",
            source=r[6] or "",
            alert_type=r[7] or "",
            target_host=r[8],
            target_identity=r[9]
        )

    def get_alert_context(self, alert_id: str, graph_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve immediate contextual envelope: alert, event, host, identity, techniques.
        """
        query = """
        MATCH (a:Alert)
        WHERE a.id = $alert_id
        OPTIONAL MATCH (a)-[:HAS_EVENT]->(e:Event)
        OPTIONAL MATCH (e)-[:OCCURRED_ON]->(h:Host)
        OPTIONAL MATCH (e)-[:INVOLVES_IDENTITY]->(i:Identity)
        OPTIONAL MATCH (e)-[:MAPS_TO]->(t:Technique)
        RETURN a, e, h, i, collect(t) AS techniques
        """
        res = self.db.execute_query(query, {"alert_id": alert_id}, graph_name=graph_name)
        if not res.result_set:
            return {}
        r = res.result_set[0]
        alert_node = r[0]
        event_node = r[1]
        host_node = r[2]
        identity_node = r[3]
        techniques_list = r[4] if len(r) > 4 else []

        return {
            "alert": dict(alert_node.properties) if alert_node else {},
            "event": dict(event_node.properties) if event_node else {},
            "host": dict(host_node.properties) if host_node else {},
            "identity": dict(identity_node.properties) if identity_node else {},
            "techniques": [dict(t.properties) for t in techniques_list if hasattr(t, "properties")]
        }

    def get_attack_paths(self, alert_id: str, graph_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Trace multi-hop path: Alert -> Event -> Host -> Process -> Indicator.
        """
        query = """
        MATCH p = (a:Alert)-[:HAS_EVENT]->(e:Event)-[:OCCURRED_ON]->(h:Host)-[:EXECUTED]->(pr:Process)-[:CONNECTED_TO]->(ind:Indicator)
        WHERE a.id = $alert_id
        RETURN p, pr, ind, h
        """
        res = self.db.execute_query(query, {"alert_id": alert_id}, graph_name=graph_name)
        paths = []
        processes = []
        indicators = []
        hosts = []

        for r in res.result_set:
            p = r[0]
            pr = r[1]
            ind = r[2]
            h = r[3]
            paths.append(p)
            if pr and dict(pr.properties) not in processes:
                processes.append(dict(pr.properties))
            if ind and dict(ind.properties) not in indicators:
                indicators.append(dict(ind.properties))
            if h and dict(h.properties) not in hosts:
                hosts.append(dict(h.properties))

        return {
            "paths": paths,
            "processes": processes,
            "indicators": indicators,
            "hosts": hosts
        }

    def get_asset_exposure(self, alert_id: str, graph_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Identify high-value assets accessible from hosts in the incident envelope.
        """
        query = """
        MATCH p = (a:Alert)-[:HAS_EVENT]->(e:Event)-[:OCCURRED_ON]->(h:Host)-[:CAN_ACCESS]->(ast:Asset)
        WHERE a.id = $alert_id
        RETURN p, h.hostname AS hostname, ast.id AS asset_id, ast.name AS asset_name,
               ast.criticality AS criticality, ast.data_classification AS classification
        """
        res = self.db.execute_query(query, {"alert_id": alert_id}, graph_name=graph_name)
        exposures = []
        for r in res.result_set:
            exposures.append({
                "path": r[0],
                "hostname": r[1],
                "asset_id": r[2],
                "asset_name": r[3],
                "criticality": r[4] or "MEDIUM",
                "classification": r[5] or "Internal"
            })
        return exposures

    def get_vulnerability_exposure(self, alert_id: str, graph_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Identify software vulnerabilities and CISA KEV status on involved hosts.
        """
        query = """
        MATCH p = (a:Alert)-[:HAS_EVENT]->(e:Event)-[:OCCURRED_ON]->(h:Host)-[:RUNS]->(s:Software)-[:AFFECTED_BY]->(v:Vulnerability)
        WHERE a.id = $alert_id
        RETURN p, h.hostname AS hostname, s.name AS software, s.version AS version,
               v.cve_id AS cve_id, v.cvss_score AS cvss_score, v.cisa_kev AS cisa_kev,
               v.description AS description
        """
        res = self.db.execute_query(query, {"alert_id": alert_id}, graph_name=graph_name)
        vulns = []
        for r in res.result_set:
            vulns.append({
                "path": r[0],
                "hostname": r[1],
                "software": r[2],
                "version": r[3],
                "cve_id": r[4],
                "cvss_score": float(r[5]) if r[5] is not None else 0.0,
                "cisa_kev": bool(r[6]),
                "description": r[7] or ""
            })
        return vulns

    def get_related_alerts(self, alert_id: str, graph_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find related alerts correlated through shared Host, Identity, or Indicator.
        """
        query = """
        MATCH (a1:Alert)-[:HAS_EVENT]->(e1:Event)
        WHERE a1.id = $alert_id
        OPTIONAL MATCH (e1)-[:OCCURRED_ON]->(h:Host)<-[:OCCURRED_ON]-(e2:Event)<-[:HAS_EVENT]-(a2:Alert)
        WHERE a1.id <> a2.id
        OPTIONAL MATCH (e1)-[:INVOLVES_IDENTITY]->(i:Identity)<-[:INVOLVES_IDENTITY]-(e3:Event)<-[:HAS_EVENT]-(a3:Alert)
        WHERE a1.id <> a3.id
        RETURN a2.id AS host_related_alert, h.hostname AS shared_host,
               a3.id AS identity_related_alert, i.username AS shared_identity
        """
        res = self.db.execute_query(query, {"alert_id": alert_id}, graph_name=graph_name)
        related = []
        for r in res.result_set:
            if r[0]:
                related.append({"alert_id": r[0], "relation_type": "shared_host", "pivot": r[1]})
            if r[2]:
                related.append({"alert_id": r[2], "relation_type": "shared_identity", "pivot": r[3]})
        return related

    def get_full_investigation_graph(self, alert_id: str, graph_name: Optional[str] = None) -> GraphData:
        """
        Collect bounded subgraph paths centered on the alert up to 4 hops.
        """
        query = """
        MATCH p = (a:Alert)-[*1..4]-(target)
        WHERE a.id = $alert_id
        RETURN p
        LIMIT 30
        """
        res = self.db.execute_query(query, {"alert_id": alert_id}, graph_name=graph_name)
        return self.db.normalize_graph_result(res.result_set)

    def persist_investigation(
        self,
        investigation_id: str,
        alert_id: str,
        started_at: str,
        completed_at: str,
        classification: str,
        priority: str,
        raw_score: float,
        narrative: str,
        graph_name: Optional[str] = None
    ):
        """
        Persist investigation entity and connect it to the Alert.
        """
        query = """
        MATCH (a:Alert)
        WHERE a.id = $alert_id
        MERGE (inv:Investigation {id: $inv_id})
        SET inv.alert_id = $alert_id,
            inv.started_at = $started_at,
            inv.completed_at = $completed_at,
            inv.classification = $classification,
            inv.priority = $priority,
            inv.raw_score = $raw_score,
            inv.narrative = $narrative
        MERGE (inv)-[:INVESTIGATES]->(a)
        RETURN inv
        """
        params = {
            "inv_id": investigation_id,
            "alert_id": alert_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "classification": classification,
            "priority": priority,
            "raw_score": raw_score,
            "narrative": narrative
        }
        self.db.execute_query(query, params, graph_name=graph_name)

    def persist_response_action(
        self,
        action_id: str,
        investigation_id: str,
        action_type: str,
        target_entity: str,
        status: str,
        policy_decision: str,
        justification: str,
        proposed_at: str,
        graph_name: Optional[str] = None
    ):
        """
        Persist ResponseAction entity and connect it to the Investigation and Target.
        """
        query = """
        MATCH (inv:Investigation)
        WHERE inv.id = $inv_id
        MERGE (ra:ResponseAction {id: $action_id})
        SET ra.action_type = $action_type,
            ra.target_entity = $target_entity,
            ra.status = $status,
            ra.policy_decision = $policy_decision,
            ra.justification = $justification,
            ra.proposed_at = $proposed_at
        MERGE (inv)-[:RECOMMENDED_ACTION]->(ra)
        RETURN ra
        """
        params = {
            "inv_id": investigation_id,
            "action_id": action_id,
            "action_type": action_type,
            "target_entity": target_entity,
            "status": status,
            "policy_decision": policy_decision,
            "justification": justification,
            "proposed_at": proposed_at
        }
        self.db.execute_query(query, params, graph_name=graph_name)


graph_queries = ThreatPathGraphQueries()
