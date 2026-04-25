import re
from typing import Any

from graph.models import Edge, Entity


class BackendMapper:
    EDGE_TYPE_MAPPING = {
        "SUPPLIES": "supplier",
        "SUPPLIER": "supplier",
        "INVESTS_IN": "investor",
        "PARTNERS_WITH": "partner",
        "PARTNER": "partner",
        "ANNOUNCED": "announcement",
        "COMPETES_WITH": "competitor",
        "COMPETITOR": "competitor",
        "ACQUIRES": "acquisition",
        "MERGES_WITH": "merger",
        "OWNS": "ownership",
        "WORKS_FOR": "employment",
    }

    def __init__(self, backend_client: Any):
        self.backend_client = backend_client

    def extract_stock_ids(self, entities: list[Entity]) -> list[str]:
        stock_ids = []
        for entity in entities:
            if entity.type == "Ticker":
                stock_id = self._normalize_stock_id(entity.id)
                if stock_id:
                    stock_ids.append(stock_id)
            elif entity.type == "Organization":
                ticker = entity.props.get("ticker") or entity.external_ids.get("ticker")
                if ticker:
                    stock_id = self._normalize_stock_id(ticker)
                    if stock_id:
                        stock_ids.append(stock_id)
        return list(set(stock_ids))

    def map_edges_to_backend_format(
        self,
        edges: list[Edge],
        entity_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        backend_edges = []
        for edge in edges:
            src_stock_id = entity_map.get(edge.src)
            dst_stock_id = entity_map.get(edge.dst)

            if src_stock_id and dst_stock_id:
                edge_type = self._map_edge_type(edge.rel)
                backend_edge = {
                    "source": src_stock_id,
                    "target": dst_stock_id,
                    "edge_type": edge_type,
                }

                if edge.props.get("description"):
                    backend_edge["description"] = edge.props["description"]
                elif edge.props.get("snippet"):
                    backend_edge["description"] = edge.props["snippet"]

                backend_edges.append(backend_edge)

        return backend_edges

    def build_entity_to_stock_map(self, entities: list[Entity]) -> dict[str, str]:
        entity_to_stock = {}
        for entity in entities:
            stock_id = None

            if entity.type == "Ticker":
                stock_id = self._normalize_stock_id(entity.id)
            elif entity.type == "Organization":
                ticker = entity.props.get("ticker") or entity.external_ids.get("ticker")
                if ticker:
                    stock_id = self._normalize_stock_id(ticker)

            if stock_id:
                entity_to_stock[entity.id] = stock_id

        return entity_to_stock

    def _normalize_stock_id(self, identifier: str) -> str | None:
        identifier = identifier.strip().upper()

        if not identifier:
            return None

        if identifier.startswith("ticker:") or identifier.startswith("entity:"):
            identifier = identifier.split(":", 1)[1]

        if re.match(r"^\d{4}$", identifier):
            return identifier
        elif re.match(r"^[A-Z]{1,5}$", identifier):
            return identifier
        else:
            return None

    def _map_edge_type(self, relation: str) -> str:
        relation_upper = relation.upper().replace(" ", "_")
        return self.EDGE_TYPE_MAPPING.get(relation_upper, "related")

