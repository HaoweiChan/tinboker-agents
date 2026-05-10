import time
import logging
from datetime import datetime
from typing import Any, Iterable

import requests
from pydantic import HttpUrl

from ingest.connectors.base import Connector, FetchQuery
from ingest.models import RawDoc
from utils.config import get_search_config

logger = logging.getLogger(__name__)


class TavilyConnector(Connector):
    name = "tavily"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.api_key = get_search_config().get("tavily_api_key")
        self.base_url = "https://api.tavily.com/search"
        self.timeout = self.config.get("timeout", 120)
        self.retry_count = self.config.get("retry_count", 3)
        self.retry_delay = self.config.get("retry_delay", 2.0)

    def fetch(self, query: FetchQuery) -> Iterable[RawDoc]:
        if not self.api_key:
            logger.warning("Tavily API key not found. Skipping fetch.")
            return []

        payload = {
            "api_key": self.api_key,
            "query": query.query,
            "search_depth": "advanced",
            "include_raw_content": self.config.get("include_raw_content", True),
            "max_results": query.limit or self.config.get("max_results", 5),
        }

        for attempt in range(self.retry_count):
            try:
                response = requests.post(self.base_url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                logger.info(f"Fetched {len(results)} results from Tavily for query: {query.query}")

                for result in results:
                    try:
                        yield self._map_to_raw_doc(result)
                    except Exception as e:
                        logger.error(f"Failed to map Tavily result to RawDoc: {e}")
                        continue
                return  # Success, exit retry loop

            except requests.exceptions.RequestException as e:
                if attempt < self.retry_count - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.warning(f"Tavily API request failed (attempt {attempt + 1}/{self.retry_count}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                logger.error(f"Tavily API request failed after {self.retry_count} attempts: {e}")
                return []

    def _map_to_raw_doc(self, result: dict[str, Any]) -> RawDoc:
        # Tavily results don't always have a published date, use now() if missing
        # Result keys: title, url, content, raw_content, published_date (sometimes)
        
        published_at = datetime.utcnow()
        if result.get("published_date"):
            try:
                # Try parsing common formats if needed, but Tavily often returns string
                # For now, just use current time as fallback logic might be complex
                # or implement basic parsing
                pass 
            except Exception:
                pass

        # Use raw_content if available and requested, else content (summary)
        text_content = result.get("raw_content") if self.config.get("include_raw_content") and result.get("raw_content") else result.get("content", "")
        
        return RawDoc(
            url=HttpUrl(result["url"]),
            title=result.get("title", "Unknown Title"),
            text=text_content,
            published_at=published_at,
            source="tavily",
            raw_data=result,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )




