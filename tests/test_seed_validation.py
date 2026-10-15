"""
Regression Tests for Remote Seeding Validation
Tests canonical MAPS_TO validation, semantic connectivity, directionality, and idempotency.
"""
import pytest
from unittest.mock import MagicMock
from backend.database import db_manager
from backend.seed import seed_graph
from scripts.seed_remote import validate_seeded_graph, REQUIRED_ALERTS

SEED_TEST_GRAPH = "threatpath_seed_val_test"


@pytest.fixture(scope="module")
def seeded_test_graph():
    """
    Creates an isolated disposable graph and seeds it once for validation tests.
    Cleans up completely on teardown, strictly preserving social and threatpath_dev.
    """
    client = db_manager.get_client()
    g = client.select_graph(SEED_TEST_GRAPH)
    try:
        g.query("MATCH (n) DETACH DELETE n")
    except Exception:
        pass

    # Seed the test graph
    seed_graph(graph_name=SEED_TEST_GRAPH)

    yield g

    # Teardown: delete all test nodes
    try:
        g.query("MATCH (n) DETACH DELETE n")
        client.delete_graph(SEED_TEST_GRAPH)
    except Exception:
        pass


def test_validation_passes_on_intact_seeded_graph(seeded_test_graph):
    """
    1. Canonical MAPS_TO technique relationship and all 4 alerts are present -> validation passes.
    """
    assert validate_seeded_graph(graph_name=SEED_TEST_GRAPH, graph_obj=seeded_test_graph) is True


def test_validation_fails_when_technique_relationship_is_missing():
    """
    2. Missing technique relationship -> validation fails with clear error.
    Tested using an isolated mock graph.
    """
    mock_graph = MagicMock()
    
    # 1. Alerts query returns all 4 required alerts
    alert_result = MagicMock()
    alert_result.result_set = [(aid, aname) for aid, aname in REQUIRED_ALERTS]

    # 2. Relationship types query MISSING 'MAPS_TO'
    rel_result = MagicMock()
    rel_result.result_set = [("HAS_EVENT",), ("OCCURRED_ON",), ("INVOLVES_IDENTITY",)]

    def mock_query(q, *args, **kwargs):
        if "MATCH (a:Alert)" in q:
            return alert_result
        if "RETURN DISTINCT type(r)" in q:
            return rel_result
        return MagicMock(result_set=[])

    mock_graph.query.side_effect = mock_query

    assert validate_seeded_graph(graph_obj=mock_graph) is False


def test_validation_fails_when_technique_rel_has_wrong_direction_or_endpoints():
    """
    3. MAPS_TO exists somewhere, but NOT connecting (Event)-[:MAPS_TO]->(Technique).
    Validation must fail because semantic connectivity is absent.
    """
    mock_graph = MagicMock()

    alert_result = MagicMock(result_set=[(aid, aname) for aid, aname in REQUIRED_ALERTS])
    # MAPS_TO is listed in types
    rel_result = MagicMock(result_set=[("HAS_EVENT",), ("OCCURRED_ON",), ("INVOLVES_IDENTITY",), ("MAPS_TO",)])
    # But semantic check for (Event)-[:MAPS_TO]->(Technique) returns 0!
    technique_conn_result = MagicMock(result_set=[[0]])

    def mock_query(q, *args, **kwargs):
        if "MATCH (a:Alert)" in q:
            return alert_result
        if "RETURN DISTINCT type(r)" in q:
            return rel_result
        if "(e:Event)-[r:MAPS_TO]->(t:Technique)" in q:
            return technique_conn_result
        return MagicMock(result_set=[[10]])

    mock_graph.query.side_effect = mock_query

    assert validate_seeded_graph(graph_obj=mock_graph) is False


def test_validation_fails_when_required_alert_missing():
    """
    5. Missing any of the 4 required sample alerts fails validation.
    """
    mock_graph = MagicMock()
    # Missing alert-sec-004
    alert_result = MagicMock(result_set=[(aid, aname) for aid, aname in REQUIRED_ALERTS[:3]])

    def mock_query(q, *args, **kwargs):
        if "MATCH (a:Alert)" in q:
            return alert_result
        return MagicMock(result_set=[])

    mock_graph.query.side_effect = mock_query

    assert validate_seeded_graph(graph_obj=mock_graph) is False


def test_validation_fails_when_alert_lacks_connected_event():
    """
    6. All alerts exist, but one is disconnected from its Event node.
    """
    mock_graph = MagicMock()
    alert_result = MagicMock(result_set=[(aid, aname) for aid, aname in REQUIRED_ALERTS])
    rel_result = MagicMock(result_set=[("HAS_EVENT",), ("OCCURRED_ON",), ("INVOLVES_IDENTITY",), ("MAPS_TO",)])
    technique_conn_result = MagicMock(result_set=[[2]])
    # Only 3 alerts have connected events instead of 4
    alert_event_result = MagicMock(result_set=[[3, 3]])

    def mock_query(q, *args, **kwargs):
        if "(a:Alert)-[r:HAS_EVENT]->(e:Event)" in q:
            return alert_event_result
        if "(e:Event)-[r:MAPS_TO]->(t:Technique)" in q:
            return technique_conn_result
        if "MATCH (a:Alert) RETURN a.id" in q:
            return alert_result
        if "RETURN DISTINCT type(r)" in q:
            return rel_result
        return MagicMock(result_set=[[10]])

    mock_graph.query.side_effect = mock_query

    assert validate_seeded_graph(graph_obj=mock_graph) is False


def test_seed_operation_is_idempotent():
    """
    4. Running the seed twice on the same graph remains idempotent and produces valid state.
    """
    # Run seed again on the test graph
    res2 = seed_graph(graph_name=SEED_TEST_GRAPH)
    assert res2["nodes"] == 24
    assert res2["relationships"] == 20
    assert len(res2["alerts"]) == 4

    # Validation must still pass
    assert validate_seeded_graph(graph_name=SEED_TEST_GRAPH) is True
