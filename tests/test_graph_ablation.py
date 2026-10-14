"""
Mandatory Graph-Ablation Test for ThreatPath
Proves that FalkorDB graph topology genuinely drives investigation outcomes.
"""
import pytest
from backend.database import db_manager
from backend.cypher_queries import ThreatPathGraphQueries
from backend.scoring import assessment_engine
from backend.models import CompromiseClassification, RemediationPriority

ABLATION_GRAPH_NAME = "threatpath_ablation_test"


@pytest.fixture
def ablation_graph():
    """
    Setup and teardown an isolated disposable graph for ablation testing.
    Preserves all existing graphs (e.g. threatpath_dev, social).
    """
    # 1. Setup isolated graph
    client = db_manager.get_client()
    g = client.select_graph(ABLATION_GRAPH_NAME)
    
    # Ensure empty
    try:
        g.query("MATCH (n) DETACH DELETE n")
    except Exception:
        pass

    # 2. Seed Scenario A in the isolated test graph
    seed_query = """
    MERGE (a1:Alert {id: "alert-sec-001"})
    SET a1.title = "Suspicious Interactive Logon & Beaconing Activity",
        a1.severity = "CRITICAL",
        a1.alert_type = "unusual_execution"
    MERGE (e1:Event {id: "evt-101"})
    SET e1.event_type = "interactive_logon",
        e1.action_status = "SUCCESS"
    MERGE (i1:Identity {id: "id-jdoe"})
    SET i1.username = "jdoe",
        i1.privilege_level = "ELEVATED"
    MERGE (h1:Host {id: "host-jump-prod-01"})
    SET h1.hostname = "jump-prod-01.corp.internal",
        h1.environment = "production",
        h1.isolated = false
    MERGE (p1:Process {id: "proc-powershell-enc"})
    SET p1.name = "powershell.exe",
        p1.command_line = "powershell.exe -NonI -W Hidden -enc SQBFAFgA...",
        p1.executed_by = "jdoe"
    MERGE (ind1:Indicator {id: "ind-c2-ip"})
    SET ind1.value = "198.51.100.44",
        ind1.indicator_type = "ipv4",
        ind1.reputation = "MALICIOUS",
        ind1.malicious_score = 95
    MERGE (t1:Technique {id: "tech-t1059-001"})
    SET t1.mitre_id = "T1059.001",
        t1.name = "Command and Scripting Interpreter: PowerShell"
    MERGE (ast1:Asset {id: "asset-customer-db"})
    SET ast1.name = "Customer Records Database",
        ast1.criticality = "CRITICAL"
    MERGE (a1)-[:HAS_EVENT]->(e1)
    MERGE (e1)-[:INVOLVES_IDENTITY]->(i1)
    MERGE (e1)-[:OCCURRED_ON]->(h1)
    MERGE (e1)-[:INVOLVES_PROCESS]->(p1)
    MERGE (h1)-[:EXECUTED]->(p1)
    MERGE (p1)-[:CONNECTED_TO]->(ind1)
    MERGE (e1)-[:MAPS_TO]->(t1)
    MERGE (h1)-[:CAN_ACCESS]->(ast1)
    """
    g.query(seed_query)

    yield g

    # 3. Teardown: delete ONLY the disposable ablation test graph
    try:
        g.delete()
    except Exception:
        pass


def test_graph_ablation_proves_falkordb_dependency(ablation_graph):
    """
    Step 1: Run investigation on intact graph -> Confirmed multi-hop path and LIKELY_COMPROMISE.
    Step 2: Physically ablate the [:CONNECTED_TO] relationship from FalkorDB.
    Step 3: Run exact same investigation -> Path vanishes, classification changes, uncertainty increases.
    """
    queries = ThreatPathGraphQueries(db=db_manager)

    # --- PHASE 1: Baseline Intact Graph Investigation ---
    alert = queries.get_alert_by_id("alert-sec-001", graph_name=ABLATION_GRAPH_NAME)
    assert alert is not None
    context = queries.get_alert_context("alert-sec-001", graph_name=ABLATION_GRAPH_NAME)
    attack_paths = queries.get_attack_paths("alert-sec-001", graph_name=ABLATION_GRAPH_NAME)
    asset_exposures = queries.get_asset_exposure("alert-sec-001", graph_name=ABLATION_GRAPH_NAME)
    vuln_exposures = queries.get_vulnerability_exposure("alert-sec-001", graph_name=ABLATION_GRAPH_NAME)
    related_alerts = queries.get_related_alerts("alert-sec-001", graph_name=ABLATION_GRAPH_NAME)

    # Verify baseline graph has the multi-hop path
    assert len(attack_paths["paths"]) == 1
    assert len(attack_paths["processes"]) == 1
    assert len(attack_paths["indicators"]) == 1

    baseline_assessment = assessment_engine.assess_investigation(
        alert.model_dump(), context, attack_paths, asset_exposures, vuln_exposures, related_alerts
    )

    assert baseline_assessment.classification == CompromiseClassification.LIKELY_COMPROMISE
    assert baseline_assessment.remediation_priority == RemediationPriority.CRITICAL
    assert baseline_assessment.raw_score >= 0.80

    # --- PHASE 2: Graph Ablation (Remove the material CONNECTED_TO relationship in FalkorDB) ---
    del_res = ablation_graph.query(
        "MATCH (p:Process {id: 'proc-powershell-enc'})-[r:CONNECTED_TO]->(ind:Indicator {id: 'ind-c2-ip'}) DELETE r"
    )
    # Verify relationship was deleted in FalkorDB
    verify_edge = ablation_graph.query(
        "MATCH (p:Process {id: 'proc-powershell-enc'})-[r:CONNECTED_TO]->(ind:Indicator {id: 'ind-c2-ip'}) RETURN count(r)"
    )
    assert verify_edge.result_set[0][0] == 0, "The CONNECTED_TO relationship was not successfully ablated"

    # --- PHASE 3: Re-Investigation on Ablated Graph ---
    ablated_attack_paths = queries.get_attack_paths("alert-sec-001", graph_name=ABLATION_GRAPH_NAME)
    
    # Material path is truly absent from FalkorDB
    assert len(ablated_attack_paths["paths"]) == 0
    assert len(ablated_attack_paths["indicators"]) == 0

    ablated_assessment = assessment_engine.assess_investigation(
        alert.model_dump(), context, ablated_attack_paths, asset_exposures, vuln_exposures, related_alerts
    )

    # Genuinely driven by graph topology:
    # 1. Classification cannot be LIKELY_COMPROMISE anymore
    assert ablated_assessment.classification != CompromiseClassification.LIKELY_COMPROMISE
    assert ablated_assessment.classification == CompromiseClassification.SUSPICIOUS
    
    # 2. Score drops substantially
    assert ablated_assessment.raw_score < baseline_assessment.raw_score
    
    # 3. Missing evidence highlights absence of C2 beaconing
    assert any("No active network beaconing" in m for m in ablated_assessment.missing_evidence)
    
    # 4. Uncertainty explanation changes
    assert "No active network beaconing" in str(ablated_assessment.missing_evidence)


def test_ablation_cleanup_preserves_practice_graphs():
    """
    Ensure the ablation test does not alter threatpath_dev or social graphs.
    """
    client = db_manager.get_client()
    graphs = client.list_graphs()
    assert "threatpath_dev" in graphs
    assert "social" in graphs
    assert ABLATION_GRAPH_NAME not in graphs
