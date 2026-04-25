"""
Article Storage - Stores raw article content in Google Cloud Storage.
Keeps Neo4j lean by only storing graph data (entities, edges) and article metadata.
"""

import json
import hashlib
import logging
from datetime import datetime
from typing import Any

from google.cloud import storage
from google.cloud.exceptions import NotFound

from ingest.models import RawDoc

logger = logging.getLogger(__name__)


class GCSArticleStorage:
    """Stores raw article content in Google Cloud Storage."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.bucket_name = self.config.get("bucket_name", "graphfolio-articles")
        self.prefix = self.config.get("prefix", "articles/")
        self._client = None
        self._bucket = None

    @property
    def client(self) -> storage.Client:
        if self._client is None:
            self._client = storage.Client()
        return self._client

    @property
    def bucket(self) -> storage.Bucket:
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def _url_to_key(self, url: str) -> str:
        """Convert URL to a safe storage key."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"{self.prefix}{url_hash}.json"

    def save_article(self, doc: RawDoc, ticker: str | None = None) -> str:
        """
        Save raw article to GCS.
        Returns the GCS path.
        """
        key = self._url_to_key(str(doc.url))
        article_data = {
            "url": str(doc.url),
            "title": doc.title,
            "text": doc.text,
            "published_at": doc.published_at.isoformat() if doc.published_at else None,
            "source": getattr(doc, "source", "unknown"),
            "ticker": ticker,
            "stored_at": datetime.utcnow().isoformat(),
        }
        blob = self.bucket.blob(key)
        blob.upload_from_string(
            json.dumps(article_data, ensure_ascii=False),
            content_type="application/json"
        )
        logger.debug(f"Saved article to GCS: {key}")
        return f"gs://{self.bucket_name}/{key}"

    def get_article(self, url: str) -> dict | None:
        """Retrieve article from GCS by URL."""
        key = self._url_to_key(url)
        blob = self.bucket.blob(key)
        try:
            content = blob.download_as_string()
            return json.loads(content)
        except NotFound:
            logger.debug(f"Article not found in GCS: {key}")
            return None

    def article_exists(self, url: str) -> bool:
        """Check if article exists in GCS."""
        key = self._url_to_key(url)
        blob = self.bucket.blob(key)
        return blob.exists()

    def delete_article(self, url: str) -> bool:
        """Delete article from GCS."""
        key = self._url_to_key(url)
        blob = self.bucket.blob(key)
        try:
            blob.delete()
            return True
        except NotFound:
            return False

    def list_articles(self, prefix: str | None = None, limit: int = 100) -> list[str]:
        """List article keys in GCS."""
        search_prefix = prefix or self.prefix
        blobs = self.bucket.list_blobs(prefix=search_prefix, max_results=limit)
        return [blob.name for blob in blobs]

    def get_article_by_key(self, key: str) -> dict | None:
        """Retrieve article by GCS key (for re-extraction)."""
        blob = self.bucket.blob(key)
        try:
            content = blob.download_as_string()
            return json.loads(content)
        except NotFound:
            return None

    def article_to_rawdoc(self, article_data: dict) -> RawDoc:
        """Convert stored article back to RawDoc for re-extraction."""
        published_at = None
        if article_data.get("published_at"):
            try:
                published_at = datetime.fromisoformat(article_data["published_at"])
            except Exception:
                pass
        return RawDoc(
            url=article_data["url"],
            title=article_data.get("title", ""),
            text=article_data.get("text", ""),
            published_at=published_at,
            source=article_data.get("source", "gcs_cache"),
        )