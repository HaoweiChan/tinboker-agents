"""
Article Cache - Manages article metadata in Neo4j and raw content in GCS.
Neo4j stores only metadata (URL, status, ticker) - keeps the graph lean.
GCS stores raw article text - cheap blob storage for re-extraction.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any

from graph.store.base import GraphStore
from ingest.models import RawDoc

logger = logging.getLogger(__name__)

# Extraction status constants
STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class ArticleCache:
    """
    Cache layer for articles.
    - Neo4j: metadata only (URL, status, ticker, timestamps)
    - GCS: raw article content (text, title)
    """

    def __init__(self, graph_store: GraphStore, config: dict[str, Any] | None = None):
        self.store = graph_store
        self.config = config or {}
        self.ttl_hours = self.config.get("ttl_hours", 24)
        self._gcs_storage = None
        self._ensure_schema()

    @property
    def gcs_storage(self):
        """Lazy-load GCS storage to avoid import errors if not configured."""
        if self._gcs_storage is None:
            gcs_config = self.config.get("gcs", {})
            if gcs_config.get("enabled", False):
                from services.article_storage import GCSArticleStorage
                self._gcs_storage = GCSArticleStorage(config=gcs_config)
                logger.info(f"GCS storage enabled: bucket={gcs_config.get('bucket_name')}")
            else:
                logger.debug("GCS storage not enabled, using Neo4j for full article storage")
        return self._gcs_storage

    def _ensure_schema(self):
        """Ensure cache-related schema exists in the graph."""
        try:
            self.store.query(
                "CREATE CONSTRAINT article_url_unique IF NOT EXISTS FOR (a:Article) REQUIRE a.url IS UNIQUE"
            )
        except Exception as e:
            # Constraint might already exist or DB doesn't support it
            logger.debug(f"Schema setup note: {e}")

    def get_content_hash(self, text: str) -> str:
        """Generate a hash for article content."""
        return hashlib.md5(text.encode()).hexdigest()

    def url_exists(self, url: str) -> bool:
        """Check if an article URL has already been processed."""
        result = self.store.query(
            "MATCH (a:Article {url: $url}) RETURN a.url LIMIT 1",
            {"url": str(url)}
        )
        return len(result) > 0

    def is_recently_processed(self, url: str) -> bool:
        """Check if article was processed within TTL window."""
        cutoff = datetime.utcnow() - timedelta(hours=self.ttl_hours)
        result = self.store.query(
            """
            MATCH (a:Article {url: $url})
            WHERE a.processed_at > $cutoff
            RETURN a.url LIMIT 1
            """,
            {"url": str(url), "cutoff": cutoff.isoformat()}
        )
        return len(result) > 0

    def content_hash_exists(self, content_hash: str) -> bool:
        """Check if article content (by hash) has already been processed."""
        result = self.store.query(
            "MATCH (a:Article {content_hash: $hash}) RETURN a.url LIMIT 1",
            {"hash": content_hash}
        )
        return len(result) > 0

    def save_raw_article(self, doc: RawDoc, ticker: str | None = None) -> str:
        """
        Save raw article: text to GCS (required), metadata to Neo4j.
        Returns the content hash.
        Raises RuntimeError if GCS storage is not configured or save fails.
        """
        content_hash = self.get_content_hash(doc.text or "")

        if not self.gcs_storage:
            raise RuntimeError("GCS storage is required but not configured")

        # Save raw content to GCS (no fallback - fail if GCS fails)
        gcs_path = self.gcs_storage.save_article(doc, ticker=ticker)
        logger.debug(f"Saved article to GCS: {gcs_path}")

        # Save metadata to Neo4j (text stored in GCS only)
        self.store.query(
            """
            MERGE (a:Article {url: $url})
            SET a.content_hash = $hash,
                a.title = $title,
                a.gcs_path = $gcs_path,
                a.published_at = $published_at,
                a.fetched_at = $fetched_at,
                a.ticker = $ticker,
                a.extraction_status = $status
            """,
            {
                "url": str(doc.url),
                "hash": content_hash,
                "title": doc.title,
                "gcs_path": gcs_path,
                "published_at": doc.published_at.isoformat() if doc.published_at else None,
                "fetched_at": datetime.utcnow().isoformat(),
                "ticker": ticker,
                "status": STATUS_PENDING,
            }
        )

        logger.debug(f"Saved raw article: {doc.url}")
        return content_hash

    def mark_extraction_completed(self, url: str, entities_count: int = 0, edges_count: int = 0):
        """Mark article extraction as completed."""
        self.store.query(
            """
            MATCH (a:Article {url: $url})
            SET a.extraction_status = $status,
                a.processed_at = $processed_at,
                a.entities_extracted = $entities,
                a.edges_extracted = $edges
            """,
            {
                "url": str(url),
                "status": STATUS_COMPLETED,
                "processed_at": datetime.utcnow().isoformat(),
                "entities": entities_count,
                "edges": edges_count,
            }
        )

    def mark_extraction_failed(self, url: str, error: str):
        """Mark article extraction as failed."""
        self.store.query(
            """
            MATCH (a:Article {url: $url})
            SET a.extraction_status = $status,
                a.extraction_error = $error,
                a.failed_at = $failed_at
            """,
            {
                "url": str(url),
                "status": STATUS_FAILED,
                "error": str(error)[:500],  # Truncate long errors
                "failed_at": datetime.utcnow().isoformat(),
            }
        )

    def mark_processed(
        self,
        url: str,
        content_hash: str,
        ticker: str | None = None,
        title: str | None = None,
    ):
        """Mark an article as processed in the cache (legacy method)."""
        self.store.query(
            """
            MERGE (a:Article {url: $url})
            SET a.content_hash = $hash,
                a.processed_at = $processed_at,
                a.ticker = $ticker,
                a.title = $title,
                a.extraction_status = $status
            """,
            {
                "url": str(url),
                "hash": content_hash,
                "processed_at": datetime.utcnow().isoformat(),
                "ticker": ticker,
                "title": title,
                "status": STATUS_COMPLETED,
            }
        )

    def filter_unprocessed(self, urls: list[str]) -> list[str]:
        """Filter a list of URLs to only include unprocessed ones."""
        unprocessed = []
        for url in urls:
            if not self.is_recently_processed(url):
                unprocessed.append(url)
            else:
                logger.debug(f"Skipping recently processed URL: {url}")
        return unprocessed

    def get_last_processed_time(self, ticker: str) -> datetime | None:
        """Get the last time a ticker was processed."""
        result = self.store.query(
            """
            MATCH (t:TickerMeta {ticker: $ticker})
            RETURN t.last_processed_at
            """,
            {"ticker": ticker.upper()}
        )
        if result and result[0].get("t.last_processed_at"):
            try:
                return datetime.fromisoformat(result[0]["t.last_processed_at"])
            except Exception:
                return None
        return None

    def update_ticker_processed_time(self, ticker: str):
        """Update the last processed time for a ticker."""
        self.store.query(
            """
            MERGE (t:TickerMeta {ticker: $ticker})
            SET t.last_processed_at = $processed_at
            """,
            {
                "ticker": ticker.upper(),
                "processed_at": datetime.utcnow().isoformat(),
            }
        )

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        try:
            result = self.store.query(
                """
                MATCH (a:Article)
                RETURN count(a) as total_articles
                """
            )
            total = result[0]["total_articles"] if result else 0

            recent_cutoff = datetime.utcnow() - timedelta(hours=self.ttl_hours)
            result = self.store.query(
                """
                MATCH (a:Article)
                WHERE a.processed_at > $cutoff
                RETURN count(a) as recent_articles
                """,
                {"cutoff": recent_cutoff.isoformat()}
            )
            recent = result[0]["recent_articles"] if result else 0

            return {"total_articles": total, "recent_articles": recent}
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"total_articles": 0, "recent_articles": 0}

    def get_pending_articles(self, ticker: str | None = None, limit: int = 100) -> list[dict]:
        """Get articles with pending extraction status."""
        # Query allows articles with text in Neo4j OR gcs_path
        query = """
            MATCH (a:Article)
            WHERE a.extraction_status = $status AND (a.text IS NOT NULL OR a.gcs_path IS NOT NULL)
        """
        params: dict[str, Any] = {"status": STATUS_PENDING, "limit": limit}
        if ticker:
            query += " AND a.ticker = $ticker"
            params["ticker"] = ticker
        query += " RETURN properties(a) as article ORDER BY a.fetched_at DESC LIMIT $limit"
        result = self.store.query(query, params)
        articles = [r["article"] for r in result] if result else []
        # Hydrate articles from GCS if needed
        return self._hydrate_articles(articles)

    def get_failed_articles(self, ticker: str | None = None, limit: int = 100) -> list[dict]:
        """Get articles with failed extraction status for retry."""
        query = """
            MATCH (a:Article)
            WHERE a.extraction_status = $status AND (a.text IS NOT NULL OR a.gcs_path IS NOT NULL)
        """
        params: dict[str, Any] = {"status": STATUS_FAILED, "limit": limit}
        if ticker:
            query += " AND a.ticker = $ticker"
            params["ticker"] = ticker
        query += " RETURN properties(a) as article ORDER BY a.failed_at DESC LIMIT $limit"
        result = self.store.query(query, params)
        articles = [r["article"] for r in result] if result else []
        return self._hydrate_articles(articles)

    def _hydrate_articles(self, articles: list[dict]) -> list[dict]:
        """Fetch article text from GCS if stored there."""
        if not self.gcs_storage:
            return articles
        hydrated = []
        for article in articles:
            if article.get("gcs_path") and not article.get("text"):
                # Fetch from GCS
                gcs_data = self.gcs_storage.get_article(article["url"])
                if gcs_data:
                    article["text"] = gcs_data.get("text", "")
                    article["title"] = gcs_data.get("title", article.get("title", ""))
            hydrated.append(article)
        return hydrated

    def get_extraction_stats(self) -> dict[str, int]:
        """Get extraction statistics by status."""
        try:
            result = self.store.query(
                """
                MATCH (a:Article)
                RETURN a.extraction_status as status, count(*) as count
                """
            )
            stats = {STATUS_PENDING: 0, STATUS_COMPLETED: 0, STATUS_FAILED: 0}
            for r in result:
                status = r.get("status") or "unknown"
                stats[status] = r["count"]
            return stats
        except Exception as e:
            logger.error(f"Failed to get extraction stats: {e}")
            return {STATUS_PENDING: 0, STATUS_COMPLETED: 0, STATUS_FAILED: 0}

    def article_to_rawdoc(self, article: dict) -> RawDoc:
        """Convert a stored Article back to a RawDoc for re-extraction."""
        from datetime import datetime
        published_at = None
        if article.get("published_at"):
            try:
                published_at = datetime.fromisoformat(article["published_at"])
            except Exception:
                pass
        return RawDoc(
            url=article["url"],
            title=article.get("title", ""),
            text=article.get("text", ""),
            published_at=published_at,
            source="cache",
        )

