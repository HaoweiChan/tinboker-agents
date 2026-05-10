from datetime import datetime
from typing import Any

from graph.models import Edge, Entity, Evidence
from services.backend_client import BackendAPIClient
from services.backend_mapper import BackendMapper


class BackendGraphService:
    def __init__(self, base_url: str | None = None, api_token: str | None = None, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.client = BackendAPIClient(base_url=base_url, api_token=api_token)
        self.mapper = BackendMapper(self.client)

    def create_graph_from_entities_and_edges(
        self,
        graph_name: str,
        entities: list[Entity],
        edges: list[Edge],
        description: str = "",
        tags: list[str] | None = None,
        visibility: str = "private",
    ) -> dict[str, Any]:
        stock_ids = self.mapper.extract_stock_ids(entities)
        entity_map = self.mapper.build_entity_to_stock_map(entities)
        backend_edges = self.mapper.map_edges_to_backend_format(edges, entity_map)

        if not stock_ids:
            raise ValueError("No valid stock IDs found in entities")

        return self.client.create_graph(
            graph_name=graph_name,
            nodes=stock_ids,
            edges=backend_edges,
            description=description,
            tags=tags or [],
            visibility=visibility,
        )

    def upsert_to_existing_graph(
        self,
        graph_id: str,
        entities: list[Entity],
        edges: list[Edge],
    ) -> dict[str, Any]:
        stock_ids = self.mapper.extract_stock_ids(entities)
        entity_map = self.mapper.build_entity_to_stock_map(entities)
        backend_edges = self.mapper.map_edges_to_backend_format(edges, entity_map)

        result = {}

        if stock_ids:
            result["nodes"] = self.client.add_nodes(graph_id, stock_ids)

        if backend_edges:
            result["edges"] = self.client.add_edges(graph_id, backend_edges)

        return result

    def get_graph(self, graph_id: str) -> dict[str, Any]:
        return self.client.get_graph(graph_id)

    def list_graphs(self) -> list[dict[str, Any]]:
        return self.client.list_graphs()

    def verify_stock_exists(self, stock_id: str) -> bool:
        try:
            self.client.get_company(stock_id)
            return True
        except Exception:
            return False

