import json
import re
import logging
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from graph.models import Edge, Entity, Evidence
from graph.store.base import GraphStore

logger = logging.getLogger(__name__)


class Neo4jStore(GraphStore):
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        # Configure driver with better settings for cloud (Aura)
        self.driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_lifetime=300,  # 5 minutes
            max_connection_pool_size=50,
            connection_acquisition_timeout=60,
            connection_timeout=30,
        )
        self.database = database
        self._max_retries = 3

    def upsert(
        self,
        entities: list[Entity],
        edges: list[Edge],
        evidence: list[Evidence],
    ) -> None:
        with self.driver.session(database=self.database) as session:
            for entity in entities:
                session.execute_write(self._upsert_entity, entity)

            for edge in edges:
                session.execute_write(self._upsert_edge, edge)

            for ev in evidence:
                session.execute_write(self._upsert_evidence, ev)

    def _upsert_entity(self, tx, entity: Entity) -> None:
        # Extract name/ticker for display
        name = entity.props.get("ticker") or entity.props.get("name")
        if not name:
            if entity.id.startswith("ticker:"):
                name = entity.id.split(":", 1)[1]
            elif entity.id.isupper() and len(entity.id) <= 5:
                name = entity.id
            else:
                name = entity.id

        query = """
        MERGE (e:Entity {id: $id})
        ON CREATE SET e.created_at = datetime()
        SET e.type = $type,
            e.name = $name,
            e.props = $props,
            e.external_ids = $external_ids,
            e.updated_at = datetime()
        """
        tx.run(
            query,
            id=entity.id,
            type=entity.type,
            name=name,
            props=json.dumps(entity.props),
            external_ids=json.dumps(entity.external_ids),
        )

    def _upsert_edge(self, tx, edge: Edge) -> None:
        edge_id = f"{edge.src}:{edge.rel}:{edge.dst}"
        # Sanitize relationship type: replace non-alphanumeric with _ and upper case
        rel_type = re.sub(r"[^A-Z0-9_]", "_", edge.rel.upper())
        # Collapse multiple underscores
        rel_type = re.sub(r"_+", "_", rel_type).strip("_")
        
        query = f"""
        MATCH (src:Entity {{id: $src_id}})
        MATCH (dst:Entity {{id: $dst_id}})
        MERGE (src)-[r:{rel_type} {{id: $edge_id}}]->(dst)
        ON CREATE SET r.created_at = datetime()
        SET r.props = $props,
            r.evidence_ids = $evidence_ids,
            r.updated_at = datetime()
        """
        tx.run(
            query,
            src_id=edge.src,
            dst_id=edge.dst,
            edge_id=edge_id,
            props=json.dumps(edge.props),
            evidence_ids=edge.evidence_ids,
        )

    def _upsert_evidence(self, tx, evidence: Evidence) -> None:
        query = """
        MERGE (e:Evidence {id: $id})
        ON CREATE SET e.created_at = datetime()
        SET e.source = $source,
            e.published_at = $published_at,
            e.snippet = $snippet,
            e.extractor = $extractor,
            e.confidence = $confidence,
            e.hash = $hash,
            e.updated_at = datetime()
        """
        tx.run(
            query,
            id=evidence.id,
            source=str(evidence.source),
            published_at=evidence.published_at.isoformat(),
            snippet=evidence.snippet,
            extractor=evidence.extractor,
            confidence=evidence.confidence,
            hash=evidence.hash,
        )

    def _link_evidence_to_edge(self, tx, edge: Edge, evidence: Evidence) -> None:
        query = """
        MATCH (src:Entity {id: $src_id})-[r]->(dst:Entity {id: $dst_id})
        MATCH (e:Evidence {id: $evidence_id})
        MERGE (r)-[:SUPPORTED_BY]->(e)
        """
        tx.run(
            query,
            src_id=edge.src,
            dst_id=edge.dst,
            evidence_id=evidence.id,
        )

    def upsert_infographic(
        self,
        entity_id: str,
        context: str,
        image_prompt: str,
        image_path: str,
        article_text: str,
        article_headline: str,
    ) -> None:
        with self.driver.session(database=self.database) as session:
            session.execute_write(
                self._upsert_infographic_tx,
                entity_id,
                context,
                image_prompt,
                image_path,
                article_text,
                article_headline,
            )

    def _upsert_infographic_tx(
        self, tx, entity_id, context, image_prompt, image_path, article_text, article_headline
    ):
        query = """
        MATCH (e:Entity {id: $entity_id})
        MERGE (i:Infographic {id: $context_id})
        ON CREATE SET i.created_at = datetime()
        SET i.context = $context,
            i.image_prompt = $image_prompt,
            i.image_path = $image_path,
            i.article_text = $article_text,
            i.article_headline = $article_headline,
            i.updated_at = datetime()
        MERGE (e)-[:HAS_INFOGRAPHIC]->(i)
        """
        context_id = f"{entity_id}_{context.replace(' ', '_')}"
        tx.run(
            query,
            entity_id=entity_id,
            context_id=context_id,
            context=context,
            image_prompt=image_prompt,
            image_path=image_path,
            article_text=article_text,
            article_headline=article_headline,
        )

    def query(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a query with retry logic for transient errors."""
        import time
        last_error = None
        for attempt in range(self._max_retries):
            try:
                with self.driver.session(database=self.database) as session:
                    result = session.run(cypher, parameters or {})
                    return [dict(record) for record in result]
            except (ServiceUnavailable, SessionExpired) as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Neo4j connection error (attempt {attempt + 1}/{self._max_retries}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
        raise last_error if last_error else RuntimeError("Query failed")

    def initialize_schema(self) -> None:
        constraints = [
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT evidence_id IF NOT EXISTS FOR (e:Evidence) REQUIRE e.id IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX evidence_extractor IF NOT EXISTS FOR (e:Evidence) ON (e.extractor)",
        ]

        with self.driver.session(database=self.database) as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    pass

            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    pass

    def close(self) -> None:
        self.driver.close()

