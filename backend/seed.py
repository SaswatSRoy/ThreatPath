"""
ThreatPath Graph Seeding Module
Idempotently seeds scenarios A, B, C, and D into the dedicated FalkorDB graph.
"""
import sys
import logging
from pathlib import Path
from typing import Optional
from backend.config import settings
from backend.database import db_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CYPHER_SEED_FILE = Path(__file__).resolve().parent.parent / "cypher" / "seed_scenarios.cypher"


def load_scenario_blocks(file_path: Path):
    """
    Parse Cypher seed file into cohesive scenario blocks.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Cypher file not found at {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = []
    raw_blocks = content.split("// --- SCENARIO_")
    for block in raw_blocks:
        if not block.strip():
            continue
        lines = block.splitlines()
        content_lines = []
        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("//") or "---" in line_str:
                continue
            content_lines.append(line)
        cleaned = "\n".join(content_lines).strip()
        if cleaned.endswith(";"):
            cleaned = cleaned[:-1].strip()
        if cleaned:
            blocks.append(cleaned)
    return blocks


def seed_graph(graph_name: Optional[str] = None) -> dict:
    """
    Seed the specified graph (defaults to threatpath_dev) with synthetic scenarios.
    """
    target_graph = graph_name or settings.FALKORDB_GRAPH
    logger.info(f"Starting seed process for dedicated graph: '{target_graph}'")

    # 1. Initialize schema indexes
    logger.info("Initializing schema indexes...")
    db_manager.init_schema_indexes(target_graph)

    # 2. Parse scenario blocks
    blocks = load_scenario_blocks(CYPHER_SEED_FILE)
    logger.info(f"Executing {len(blocks)} cohesive scenario Cypher blocks...")

    g = db_manager.get_graph(target_graph)
    for i, block_query in enumerate(blocks, 1):
        try:
            g.query(block_query)
        except Exception as e:
            logger.error(f"Failed to execute scenario block {i}: {e}\nQuery:\n{block_query}")
            raise

    # 3. Verify graph population
    node_res = g.query("MATCH (n) RETURN count(n) AS cnt")
    edge_res = g.query("MATCH ()-[r]->() RETURN count(r) AS cnt")
    alert_res = g.query("MATCH (a:Alert) RETURN a.id AS id, a.title AS title")

    node_count = node_res.result_set[0][0] if node_res.result_set else 0
    edge_count = edge_res.result_set[0][0] if edge_res.result_set else 0
    alerts = [{"id": r[0], "title": r[1]} for r in alert_res.result_set]

    logger.info(f"Seeding completed successfully on '{target_graph}'.")
    logger.info(f"Summary: {node_count} nodes, {edge_count} relationships, {len(alerts)} alerts.")

    # 4. Re-apply any active persisted simulated fleet states so seed does not wipe actions
    try:
        from backend.policy import simulated_env
        simulated_env.reapply_persisted_state(target_graph)
    except Exception as e:
        logger.debug(f"Notice: could not reapply simulated state after seed: {e}")

    return {
        "graph_name": target_graph,
        "nodes": node_count,
        "relationships": edge_count,
        "alerts": alerts
    }


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    result = seed_graph(target)
    print(f"Seed Output: {result}")
