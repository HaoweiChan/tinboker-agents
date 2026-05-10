from datetime import datetime
from typing import Any

from graph.models import Edge, Entity, Evidence
from services.backend_graph_service import BackendGraphService
from services.extraction_service import ExtractionService
from services.ingestion_service import IngestionService


class ProposalStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"


class GraphProposalService:
    def __init__(self, backend_url: str | None = None, backend_token: str | None = None, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.ingestion_service = IngestionService(config)
        self.extraction_service = ExtractionService(config)
        self.backend_graph_service = BackendGraphService(base_url=backend_url, api_token=backend_token, config=config)

    def create_proposal_from_news(
        self,
        source: str,
        query: str,
        graph_name: str,
        days: int = 7,
        pipeline: str = "rules+openie",
        description: str = "",
        tags: list[str] | None = None,
        created_by: str = "agent",
    ) -> dict[str, Any]:
        docs = self.ingestion_service.ingest(source=source, query=query, days=days)
        entities, edges, evidence = self.extraction_service.extract(docs, pipeline=pipeline)

        if not entities or not edges:
            return {
                "status": "warning",
                "message": "No entities or edges extracted from news",
                "entities_count": len(entities),
                "edges_count": len(edges),
            }

        stock_ids = self.backend_graph_service.mapper.extract_stock_ids(entities)
        entity_map = self.backend_graph_service.mapper.build_entity_to_stock_map(entities)
        backend_edges = self.backend_graph_service.mapper.map_edges_to_backend_format(edges, entity_map)

        proposal = {
            "proposal_id": f"prop_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hash(query) % 10000}",
            "status": ProposalStatus.PENDING,
            "graph_name": graph_name,
            "description": description or f"Graph generated from news query: {query}",
            "tags": tags or [source, pipeline, "news-generated", "pending-review"],
            "visibility": "private",
            "nodes": stock_ids,
            "edges": backend_edges,
            "metadata": {
                "source": source,
                "query": query,
                "days": days,
                "pipeline": pipeline,
                "created_by": created_by,
                "created_at": datetime.utcnow().isoformat(),
                "entities_extracted": len(entities),
                "edges_extracted": len(edges),
                "stock_ids_found": len(stock_ids),
                "docs_processed": len(docs),
                "evidence_count": len(evidence),
            },
            "raw_entities": [e.model_dump() for e in entities],
            "raw_edges": [e.model_dump() for e in edges],
            "evidence": [ev.model_dump() for ev in evidence],
        }

        return {
            "status": "success",
            "proposal": proposal,
        }

    def save_proposal(self, proposal: dict[str, Any]) -> dict[str, Any]:
        return self.backend_graph_service.client.create_graph(
            graph_name=f"[PROPOSAL] {proposal['graph_name']}",
            nodes=proposal["nodes"],
            edges=proposal["edges"],
            description=f"{proposal['description']}\n\n[PROPOSAL ID: {proposal['proposal_id']}]",
            tags=proposal["tags"],
            visibility="private",
        )

    def approve_proposal(self, proposal_id: str, reviewer: str, notes: str = "") -> dict[str, Any]:
        return {
            "status": "approved",
            "proposal_id": proposal_id,
            "reviewer": reviewer,
            "reviewed_at": datetime.utcnow().isoformat(),
            "notes": notes,
        }

    def reject_proposal(self, proposal_id: str, reviewer: str, reason: str) -> dict[str, Any]:
        return {
            "status": "rejected",
            "proposal_id": proposal_id,
            "reviewer": reviewer,
            "reviewed_at": datetime.utcnow().isoformat(),
            "reason": reason,
        }

