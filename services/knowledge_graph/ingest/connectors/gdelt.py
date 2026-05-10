import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import requests
from pydantic import HttpUrl

from ingest.connectors.base import Connector, FetchQuery
from ingest.models import RawDoc


class GDELTConnector(Connector):
    name = "gdelt"
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self, timeout: int = 30, retry_count: int = 3, retry_delay: float = 1.0):
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.session = requests.Session()

    def fetch(self, query: FetchQuery) -> list[RawDoc]:
        docs = []
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=query.days)

        params = {
            "query": query.query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": query.limit or 250,
            "startdatetime": start_date.strftime("%Y%m%d%H%M%S"),
            "enddatetime": end_date.strftime("%Y%m%d%H%M%S"),
        }

        if query.language:
            params["sourcelang"] = query.language

        url = f"{self.base_url}?{urlencode(params)}"

        for attempt in range(self.retry_count):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                if "articles" in data:
                    for article in data["articles"]:
                        doc = self._parse_article(article)
                        if doc:
                            docs.append(doc)

                break

            except requests.exceptions.RequestException as e:
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(f"GDELT API request failed after {self.retry_count} attempts: {e}")

        return docs

    def _parse_article(self, article: dict[str, Any]) -> RawDoc | None:
        try:
            url_str = article.get("url", "")
            if not url_str:
                return None

            title = article.get("title", "")
            text = article.get("seendate", "") + " " + article.get("socialimage", "")
            text = article.get("snippet", "") or text

            published_str = article.get("seendate", "")
            if published_str:
                try:
                    published_at = datetime.strptime(published_str, "%Y%m%d%H%M%S")
                except ValueError:
                    published_at = datetime.utcnow()
            else:
                published_at = datetime.utcnow()

            return RawDoc(
                url=HttpUrl(url_str),
                title=title,
                text=text,
                published_at=published_at,
                source="gdelt",
                raw_data=article,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
            )

        except Exception as e:
            return None

