from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, HttpUrl, Field


class Entity(BaseModel):
    id: str
    type: str
    props: dict[str, Any] = Field(default_factory=dict)
    external_ids: dict[str, str] = Field(default_factory=dict)

    def __toon__(self) -> str:
        from utils.toon import model_to_toon
        return model_to_toon(self.model_dump())

    @classmethod
    def from_toon(cls, toon_str: str) -> "Entity":
        from utils.toon import toon_to_json
        data = toon_to_json(toon_str)
        return cls(**data)


class Edge(BaseModel):
    src: str
    dst: str
    rel: str
    props: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: List[str] = Field(default_factory=list)

    def __toon__(self) -> str:
        from utils.toon import model_to_toon
        return model_to_toon(self.model_dump())

    @classmethod
    def from_toon(cls, toon_str: str) -> "Edge":
        from utils.toon import toon_to_json
        data = toon_to_json(toon_str)
        return cls(**data)


class Event(BaseModel):
    id: str
    type: str
    when: Optional[datetime] = None
    where: Optional[str] = None
    headline: str
    props: dict[str, Any] = Field(default_factory=dict)

    def __toon__(self) -> str:
        from utils.toon import model_to_toon
        return model_to_toon(self.model_dump())

    @classmethod
    def from_toon(cls, toon_str: str) -> "Event":
        from utils.toon import toon_to_json
        data = toon_to_json(toon_str)
        return cls(**data)


class Evidence(BaseModel):
    id: str
    source: HttpUrl
    published_at: datetime
    snippet: str
    extractor: str
    confidence: float = 0.0
    hash: Optional[str] = None
    sentence_span: Optional[tuple[int, int]] = None

    def __toon__(self) -> str:
        from utils.toon import model_to_toon
        return model_to_toon(self.model_dump())

    @classmethod
    def from_toon(cls, toon_str: str) -> "Evidence":
        from utils.toon import toon_to_json
        data = toon_to_json(toon_str)
        return cls(**data)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }

