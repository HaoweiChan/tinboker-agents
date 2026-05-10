from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, HttpUrl


class RawDoc(BaseModel):
    url: HttpUrl
    title: str
    text: str
    published_at: datetime
    source: str
    raw_data: dict[str, Any] = {}
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }

