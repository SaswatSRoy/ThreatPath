"""
ThreatPath Remote Graph Seeding Utility
Safely and idempotently seeds the production/remote FalkorDB database with Scenarios A, B, C, and D.
Requires explicit --confirm flag before running.
"""
import sys
import argparse
import logging
from backend.config import settings
from backend.database import db_manager
from backend.seed import seed_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_remote")

REQUIRED_ALERTS = [
    ("alert-sec-001", "Scenario A: Suspicious Interactive Logon & Beaconing Activity"),
    ("alert-sec-002", "Scenario B: Single Inconclusive Beaconing Indicator"),
    ("alert-sec-003", "Scenario C: High-Severity CVE on Exposed DMZ Host"),
    ("alert-sec-004", "Scenario D: Distributed SSH Password-Spray Attempt")
]


def validate_seeded_graph(graph_name: str) -> bool:
    """
    Validate that all required synthetic entities and relationships exist in the target graph.
    """
    logger.info(f"Validating seeded topology on graph '{graph_name}'...")
    g = db_manager.get_graph(graph_name)

    # 1. Verify alerts
    alert_res = g.query("MATCH (a:Alert) RETURN a.id, a.title")
    seeded_alerts = {r[0]: r[1] for r in alert_res.result_set}
    logger.info(f"Discovered {len(seeded_alerts)} alerts in '{graph_name}'")

    for req_id, req_name in REQUIRED_ALERTS:
        if req_id not in seeded_alerts:
            logger.error(f"Validation FAILED: Missing required alert '{req_id}' ({req_name})")
            return False
        logger.info(f"  ✓ {req_id}: {seeded_alerts[req_id]}")

    # 2. Verify key relationship types
    rel_res = g.query("MATCH ()-[r]->() RETURN DISTINCT type(r) AS rel_type")
    rel_types = {r[0] for r in rel_res.result_set}
    required_rels = {"HAS_EVENT", "OCCURRED_ON", "INVOLVES_IDENTITY", "HAS_TECHNIQUE"}
    missing_rels = required_rels - rel_types
    if missing_rels:
        logger.error(f"Validation FAILED: Missing relationship types: {missing_rels}")
        return False

    # 3. Verify total node and edge counts
    node_cnt = g.query("MATCH (n) RETURN count(n)").result_set[0][0]
    edge_cnt = g.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]

    logger.info("Validation PASSED successfully.")
    logger.info(f"Target Graph Summary: {node_cnt} total nodes, {edge_cnt} total edges, 4 scenario alerts.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Idempotently seed the remote ThreatPath FalkorDB graph (threatpath_demo)."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Mandatory confirmation flag to execute remote graph seeding."
    )
    parser.add_argument(
        "--graph",
        type=str,
        default="threatpath_demo",
        help="Target remote graph name (defaults strictly to 'threatpath_demo')"
    )

    args = parser.parse_args()

    # Explicitly enforce threatpath_demo unless specifically passed
    target_graph = args.graph or "threatpath_demo"

    # Safeguard 1: Explicit confirmation required
    if not args.confirm:
        logger.error("Seeding aborted. You must supply the '--confirm' flag to seed the remote graph.")
        logger.info("Usage: python -m scripts.seed_remote --confirm")
        sys.exit(1)

    # Safeguard 2: Strictly protect local practice graphs (social and threatpath_dev)
    if target_graph in ["social", "threatpath_dev"]:
        logger.error(
            f"SAFETY ABORT: Refusing to seed protected graph '{target_graph}'. "
            f"Remote seeding strictly targets 'threatpath_demo' to safeguard local development and practice graphs."
        )
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("THREATPATH REMOTE GRAPH SEEDING")
    logger.info(f"Target Host:     {settings.FALKORDB_HOST}:{settings.FALKORDB_PORT}")
    logger.info(f"Target Graph:    {target_graph}")
    logger.info(f"Auth Enabled:    {'Yes' if settings.FALKORDB_PASSWORD else 'No'}")
    logger.info("=" * 60)

    try:
        # Seed graph using cohesive scenario blocks
        seed_result = seed_graph(graph_name=target_graph)
        logger.info(f"Seed execution completed: {seed_result}")

        # Validate graph topology
        valid = validate_seeded_graph(target_graph)
        if not valid:
            logger.error("Seeding validation failed.")
            sys.exit(1)

        logger.info("Remote database successfully initialized and verified for demonstration.")
    except Exception as e:
        logger.error(f"Seeding process encountered an error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
