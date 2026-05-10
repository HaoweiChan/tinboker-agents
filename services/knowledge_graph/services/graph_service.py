import logging
from datetime import datetime
from typing import Any

from graph.models import Edge, Entity, Evidence
from graph.store.base import GraphStore
from graph.store.neo4j_store import Neo4jStore
from graph.upsert import UpsertManager
from utils.config import get_neo4j_config

logger = logging.getLogger(__name__)


class GraphService:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._store: GraphStore | None = None
        self._upsert_manager: UpsertManager | None = None

    def get_store(self, store_type: str = "neo4j") -> GraphStore:
        if self._store is None:
            if store_type == "neo4j":
                # Priority: environment variables > YAML config > defaults
                env_config = get_neo4j_config()
                yaml_config = self.config.get("graph_store", {}).get("neo4j", {})

                uri = env_config.get("uri") or yaml_config.get("uri", "bolt://localhost:7687")
                user = env_config.get("user") or yaml_config.get("user", "neo4j")
                password = env_config.get("password") or yaml_config.get("password", "password")
                database = env_config.get("database") or yaml_config.get("database", "neo4j")

                logger.info(f"Connecting to Neo4j at: {uri} (user: {user})")

                self._store = Neo4jStore(
                    uri=uri,
                    user=user,
                    password=password,
                    database=database,
                )
                self._store.initialize_schema()
            else:
                raise ValueError(f"Store type {store_type} not yet implemented")

            self._upsert_manager = UpsertManager(self._store)

        return self._store

    def upsert(
        self,
        entities: list[Entity],
        edges: list[Edge],
        evidence: list[Evidence],
        extractor: str = "unknown",
        timestamp: datetime | None = None,
    ) -> None:
        store = self.get_store()
        if self._upsert_manager is None:
            self._upsert_manager = UpsertManager(store)
        self._upsert_manager.upsert_with_provenance(
            entities, edges, evidence, extractor=extractor, timestamp=timestamp
        )

    def query(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        store_type: str = "neo4j",
    ) -> list[dict[str, Any]]:
        store = self.get_store(store_type)
        return store.query(cypher, parameters)

    def get_neighbors(
        self,
        entity_id: str,
        hop: int = 2,
        store_type: str = "neo4j",
    ) -> list[dict[str, Any]]:
        cypher = f"""
        MATCH path = (e:Entity {{id: $entity_id}})-[*1..{hop}]-(connected)
        RETURN path, length(path) as distance
        ORDER BY distance
        LIMIT 100
        """
        return self.query(cypher, {"entity_id": entity_id}, store_type)

    def get_subgraph_for_ticker(
        self,
        ticker: str,
        hop: int = 1,
        store_type: str = "neo4j",
    ) -> tuple[list[Entity], list[Edge]]:
        """
        Retrieves the subgraph centered around a ticker (or name).
        Returns a tuple of (Entities, Edges).
        """
        # 1. Find the node first (match by id or name)
        cypher_query = f"""
        MATCH (center:Entity)
        WHERE center.id = $ticker OR center.name = $ticker
        CALL apoc.path.subgraphAll(center, {{
            maxLevel: {hop},
            relationshipFilter: '>'
        }})
        YIELD nodes, relationships
        RETURN nodes, relationships
        """
        # Fallback if APOC is not available or for simple expansion
        # Note: Using a simpler match for compatibility if APOC isn't guaranteed
        cypher_simple = f"""
        MATCH (center:Entity)
        WHERE toLower(center.id) = toLower($ticker) OR toLower(center.name) = toLower($ticker)
        OPTIONAL MATCH path = (center)-[*1..{hop}]-(connected)
        RETURN center, collect(path) as paths
        """
        
        store = self.get_store(store_type)
        
        # Try simple query to be safe (standard Neo4j)
        # We extract nodes and edges from paths
        results = store.query(cypher_simple, {"ticker": ticker})
        
        entities_map = {}
        edges_map = {}
        
        for record in results:
            center = record.get("center")
            if center:
                # Parse center node
                # Note: Neo4j driver returns Node objects, we need to map to our Entity model
                # However, store.query returns dicts if we used the default Neo4jStore.query implementation?
                # Let's check Neo4jStore.query implementation. It returns [dict(record) for record in result].
                # But 'record' contains Node objects which are not directly dicts compatible with Entity(**data).
                # We need a helper to map Neo4j Nodes to Entity models.
                pass

        # Actually, let's write a query that returns JSON-like structures or map them
        cypher_formatted = f"""
        MATCH (center:Entity)
        WHERE toLower(center.id) = toLower($ticker) OR toLower(center.name) = toLower($ticker)
        OPTIONAL MATCH (center)-[r*1..{hop}]-(neighbor)
        WITH center, collect(r) as rels, collect(neighbor) as neighbors
        UNWIND (neighbors + [center]) as node
        WITH DISTINCT node, rels
        UNWIND [x IN rels | x] as rel_list
        UNWIND rel_list as rel
        WITH DISTINCT node, rel
        RETURN 
            collect(DISTINCT {{
                id: node.id, 
                type: node.type, 
                props: node.props, 
                external_ids: node.external_ids 
            }}) as entities,
            collect(DISTINCT {{
                src: startNode(rel).id,
                dst: endNode(rel).id,
                rel: type(rel),
                props: rel.props,
                evidence_ids: rel.evidence_ids
            }}) as edges
        """
        
        results = store.query(cypher_formatted, {"ticker": ticker})
        
        entities = []
        edges = []
        
        if results:
            data = results[0]
            for e_data in data.get("entities", []):
                if e_data and e_data.get("id"):  # Filter nulls and ensure id exists
                    # Ensure required fields have defaults
                    if not e_data.get("type"):
                        e_data["type"] = "Entity"
                    if e_data.get("props") is None:
                        e_data["props"] = {}
                    if e_data.get("external_ids") is None:
                        e_data["external_ids"] = {}

                    # Fix props if it's a string (JSON)
                    if isinstance(e_data.get("props"), str):
                        import json
                        try:
                            e_data["props"] = json.loads(e_data["props"])
                        except Exception:
                            e_data["props"] = {}
                        if not isinstance(e_data["props"], dict):
                            e_data["props"] = {"value": e_data["props"]}

                    if isinstance(e_data.get("external_ids"), str):
                        import json
                        try:
                            e_data["external_ids"] = json.loads(e_data["external_ids"])
                        except Exception:
                            e_data["external_ids"] = {}
                        if not isinstance(e_data.get("external_ids"), dict):
                            e_data["external_ids"] = {}
                    
                    try:
                        entities.append(Entity(**e_data))
                    except Exception as parse_err:
                        logger.warning(f"Failed to parse entity {e_data.get('id')}: {parse_err}")
            
            for r_data in data.get("edges", []):
                if r_data: # Filter nulls
                    # Handle edge props similarly
                    if isinstance(r_data.get("props"), str):
                        import json
                        try:
                            r_data["props"] = json.loads(r_data["props"])
                        except:
                            pass
                        if not isinstance(r_data["props"], dict):
                            r_data["props"] = {"value": r_data["props"]}
                    
                    if not isinstance(r_data.get("props"), dict):
                        r_data["props"] = {}
                    if not isinstance(r_data.get("evidence_ids"), list):
                         r_data["evidence_ids"] = []

                    edges.append(Edge(**r_data))
                    
        return entities, edges

    def explain_edge(
        self,
        src_id: str,
        rel: str,
        dst_id: str,
        store_type: str = "neo4j",
    ) -> list[dict[str, Any]]:
        cypher = """
        MATCH (src:Entity {id: $src_id})-[r]->(dst:Entity {id: $dst_id})
        UNWIND r.evidence_ids as ev_id
        MATCH (e:Evidence {id: ev_id})
        RETURN e.snippet as snippet, e.source as source, e.confidence as confidence, e.extractor as extractor
        ORDER BY e.confidence DESC
        """
        return self.query(cypher, {"src_id": src_id, "dst_id": dst_id}, store_type)

    def close(self) -> None:
        if self._store:
            self._store.close()
            self._store = None
            self._upsert_manager = None

