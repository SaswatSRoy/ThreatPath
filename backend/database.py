"""
FalkorDB Database Client and Graph Result Normalizer for ThreatPath
"""
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from falkordb import FalkorDB, Path as FalkorPath, Node as FalkorNode, Edge as FalkorEdge
from backend.config import settings
from backend.models import GraphData, GraphNode, GraphEdge

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, host: str = None, port: int = None, password: Optional[str] = None):
        self.host = host or settings.FALKORDB_HOST
        self.port = port or settings.FALKORDB_PORT
        self.password = password or settings.FALKORDB_PASSWORD
        self._client: Optional[FalkorDB] = None

    def get_client(self) -> FalkorDB:
        if self._client is None:
            self._client = FalkorDB(
                host=self.host,
                port=self.port,
                password=self.password if self.password else None,
                socket_timeout=5,
                socket_connect_timeout=3
            )
        return self._client

    def get_graph(self, graph_name: Optional[str] = None):
        client = self.get_client()
        name = graph_name or settings.FALKORDB_GRAPH
        return client.select_graph(name)

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        graph_name: Optional[str] = None
    ):
        """
        Execute a Cypher query with optional parameters on the specified graph.
        """
        g = self.get_graph(graph_name)
        try:
            return g.query(query, params or {})
        except Exception as e:
            logger.error(f"FalkorDB query failed on graph '{graph_name or settings.FALKORDB_GRAPH}': {e}. Query: {query}")
            raise

    def init_schema_indexes(self, graph_name: Optional[str] = None):
        """
        Ensure schema indexes exist on key entity types for rapid lookup.
        """
        target_graph = graph_name or settings.FALKORDB_GRAPH
        indexes = [
            "CREATE INDEX FOR (a:Alert) ON (a.id)",
            "CREATE INDEX FOR (e:Event) ON (e.id)",
            "CREATE INDEX FOR (i:Identity) ON (i.id)",
            "CREATE INDEX FOR (h:Host) ON (h.id)",
            "CREATE INDEX FOR (p:Process) ON (p.id)",
            "CREATE INDEX FOR (ind:Indicator) ON (ind.id)",
            "CREATE INDEX FOR (v:Vulnerability) ON (v.id)",
            "CREATE INDEX FOR (ast:Asset) ON (ast.id)",
            "CREATE INDEX FOR (inv:Investigation) ON (inv.id)",
            "CREATE INDEX FOR (ra:ResponseAction) ON (ra.id)",
            "CREATE INDEX FOR (sm:SimulatedState) ON (sm.key)"
        ]
        g = self.get_graph(target_graph)
        for idx_query in indexes:
            try:
                g.query(idx_query)
            except Exception as e:
                # FalkorDB may raise if index already exists
                logger.debug(f"Index query notice ({idx_query}): {e}")

    @staticmethod
    def normalize_graph_result(result_set) -> GraphData:
        """
        Normalize FalkorDB query results into a deduplicated GraphData model.
        Handles Path, Node, Edge, or tabular rows.
        """
        nodes_dict: Dict[str, GraphNode] = {}
        edges_dict: Dict[str, GraphEdge] = {}

        def process_node(node: FalkorNode) -> str:
            # Prefer domain 'id' property if present, else fallback to str(node.id)
            props = dict(node.properties)
            domain_id = str(props.get("id") or f"node_{node.id}")
            labels = node.labels if hasattr(node, "labels") and node.labels else ["Entity"]
            primary_label = labels[0] if labels else "Entity"
            display_name = props.get("name") or props.get("title") or props.get("hostname") or props.get("username") or domain_id

            if domain_id not in nodes_dict:
                nodes_dict[domain_id] = GraphNode(
                    id=domain_id,
                    label=str(display_name),
                    category=primary_label,
                    properties=props
                )
            return domain_id

        def process_edge(edge: FalkorEdge, src_override: Optional[str] = None, dst_override: Optional[str] = None):
            src_id = src_override or str(edge.src_node)
            dst_id = dst_override or str(edge.dest_node)
            rel_type = edge.relation or "CONNECTED_TO"
            props = dict(edge.properties)
            edge_id = f"{src_id}-{rel_type}->{dst_id}"

            if edge_id not in edges_dict:
                edges_dict[edge_id] = GraphEdge(
                    id=edge_id,
                    source=src_id,
                    target=dst_id,
                    relation=rel_type,
                    properties=props
                )

        if not result_set:
            return GraphData(nodes=[], edges=[])

        # Traverse result set
        for row in result_set:
            if not isinstance(row, (list, tuple)):
                row = [row]
            for item in row:
                if isinstance(item, FalkorPath):
                    path_nodes = item.nodes()
                    path_edges = item.edges()
                    node_id_map = {}
                    for fn in path_nodes:
                        dom_id = process_node(fn)
                        node_id_map[fn.id] = dom_id
                    
                    for fe in path_edges:
                        s_id = node_id_map.get(fe.src_node, str(fe.src_node))
                        d_id = node_id_map.get(fe.dest_node, str(fe.dest_node))
                        process_edge(fe, src_override=s_id, dst_override=d_id)
                elif isinstance(item, FalkorNode):
                    process_node(item)
                elif isinstance(item, FalkorEdge):
                    process_edge(item)

        return GraphData(
            nodes=list(nodes_dict.values()),
            edges=list(edges_dict.values())
        )


db_manager = DatabaseManager()
