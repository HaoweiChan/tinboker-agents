from abc import ABC, abstractmethod
from collections.abc import Iterable

from ingest.models import RawDoc


class FetchQuery:
    def __init__(
        self,
        query: str,
        days: int = 7,
        language: str | None = None,
        limit: int | None = None,
    ):
        self.query = query
        self.days = days
        self.language = language
        self.limit = limit


class Connector(ABC):
    name: str

    @abstractmethod
    def fetch(self, query: FetchQuery) -> Iterable[RawDoc]:
        pass

