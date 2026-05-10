from abc import ABC, abstractmethod
from typing import Any

from graph.models import Edge, Entity, Evidence


class GraphStore(ABC):
    @abstractmethod
    def upsert(
        self,
        entities: list[Entity],
        edges: list[Edge],
        evidence: list[Evidence],
    ) -> None:
        pass

    @abstractmethod
    def upsert_infographic(
        self,
        entity_id: str,
        context: str,
        image_prompt: str,
        image_path: str,
        article_text: str,
        article_headline: str,
    ) -> None:
        pass

    @abstractmethod
    def query(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def initialize_schema(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

