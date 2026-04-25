"""
Example MCP tools using the same service layer as CLI and API.

This demonstrates how MCP server tools would use the same services.
"""

from typing import Any

from services.extraction_service import ExtractionService
from services.graph_service import GraphService
from services.ingestion_service import IngestionService


class MCPGraphTools:
    def __init__(self, config: dict[str, Any] | None = None):
        self.graph_service = GraphService(config)
        self.ingestion_service = IngestionService(config)
        self.extraction_service = ExtractionService(config)

    def get_neighbors(self, entity_id: str, hop: int = 2) -> list[dict[str, Any]]:
        return self.graph_service.get_neighbors(entity_id, hop=hop)

    def explain_edge(self, src_id: str, rel: str, dst_id: str) -> list[dict[str, Any]]:
        return self.graph_service.explain_edge(src_id, rel, dst_id)

    def upsert_fact(self, text: str, schema_hint: str | None = None) -> dict[str, Any]:
        from ingest.models import RawDoc
        from pydantic import HttpUrl
        from datetime import datetime

        doc = RawDoc(
            url=HttpUrl("https://mcp-agent"),
            title="Agent-added fact",
            text=text,
            published_at=datetime.utcnow(),
            source="mcp_agent",
        )

        entities, edges, evidence = self.extraction_service.extract([doc], pipeline="rules+openie")
        self.graph_service.upsert(entities, edges, evidence, extractor="mcp_agent")

        return {
            "status": "success",
            "entities_added": len(entities),
            "edges_added": len(edges),
            "evidence_added": len(evidence),
        }

    def query_graph(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return self.graph_service.query(cypher, parameters)

