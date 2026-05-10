from abc import ABC, abstractmethod

from graph.models import Edge, Entity, Evidence
from ingest.models import RawDoc


class Extractor(ABC):
    name: str

    @abstractmethod
    def extract(self, doc: RawDoc) -> tuple[list[Entity], list[Edge], list[Evidence]]:
        pass

