from typing import Any

import requests

from utils.config import get_backend_config


class BackendAPIClient:
    def __init__(self, base_url: str | None = None, api_token: str | None = None):
        config = get_backend_config()
        self.base_url = (base_url or config["url"]).rstrip("/")
        self.api_token = api_token or config.get("api_token", "")
        self.session = requests.Session()

        if self.api_token:
            self.session.headers.update({"Authorization": f"Bearer {self.api_token}"})

    def create_graph(
        self,
        graph_name: str,
        nodes: list[str],
        edges: list[dict[str, Any]],
        description: str = "",
        tags: list[str] | None = None,
        visibility: str = "private",
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/graph"
        payload = {
            "graph_name": graph_name,
            "nodes": nodes,
            "edges": edges,
            "description": description,
            "tags": tags or [],
            "visibility": visibility,
        }
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def get_graph(self, graph_id: str) -> dict[str, Any]:
        url = f"{self.base_url}/api/graph/{graph_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def list_graphs(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/graph/list"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def add_nodes(self, graph_id: str, nodes: list[str]) -> dict[str, Any]:
        url = f"{self.base_url}/api/graph/{graph_id}/nodes"
        payload = {"nodes": nodes}
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def add_edges(self, graph_id: str, edges: list[dict[str, Any]]) -> dict[str, Any]:
        url = f"{self.base_url}/api/graph/{graph_id}/edges"
        payload = {"edges": edges}
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def get_company(self, stock_id: str) -> dict[str, Any]:
        url = f"{self.base_url}/api/company/{stock_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_company_list(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/company_list"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

