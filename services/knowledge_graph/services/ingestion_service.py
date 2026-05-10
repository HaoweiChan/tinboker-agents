import json
from pathlib import Path
from typing import Any

from ingest.connectors.base import Connector, FetchQuery
from ingest.connectors.gdelt import GDELTConnector
from ingest.connectors.tavily import TavilyConnector
from ingest.models import RawDoc


class IngestionService:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._connectors: dict[str, Connector] = {}

    def get_connector(self, source: str) -> Connector:
        if source not in self._connectors:
            if source == "gdelt":
                connector_config = self.config.get("connectors", {}).get("gdelt", {})
                self._connectors[source] = GDELTConnector(
                    timeout=connector_config.get("timeout", 30),
                    retry_count=connector_config.get("retry_count", 3),
                    retry_delay=connector_config.get("retry_delay", 1.0),
                )
            elif source == "tavily":
                connector_config = self.config.get("connectors", {}).get("tavily", {})
                # TavilyConnector needs 'config' dict with api_key
                search_config = self.config.get("search", {})
                # Merge or use specific config
                self._connectors[source] = TavilyConnector(config=search_config)
            else:
                raise ValueError(f"Unknown source: {source}")

        return self._connectors[source]

    def ingest(
        self,
        source: str,
        query: str,
        days: int = 7,
        language: str | None = None,
        limit: int | None = None,
    ) -> list[RawDoc]:
        connector = self.get_connector(source)
        fetch_query = FetchQuery(query=query, days=days, language=language, limit=limit)
        return list(connector.fetch(fetch_query))

    def save_docs(self, docs: list[RawDoc], output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        for i, doc in enumerate(docs):
            file_path = output_dir / f"doc_{i:06d}.json"
            with open(file_path, "w") as f:
                json.dump(doc.model_dump(), f, default=str, indent=2)

