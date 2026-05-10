"""
Blog Post Storage - Saves blog posts (SVG + Article) to GCS and tracks in Neo4j.
"""

import logging
import os
from datetime import datetime
from typing import Any

from google.cloud import storage
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


class BlogPostStorage:
    """Stores blog posts (SVG + Markdown) in GCS and tracks metadata in Neo4j."""

    def __init__(self, gcs_config: dict[str, Any] | None = None, neo4j_store=None):
        self.gcs_config = gcs_config or {}
        self.bucket_name = self.gcs_config.get("bucket_name", "graphfolio-articles")
        self.svg_prefix = self.gcs_config.get("svg_prefix", "blog/svg/")
        self.md_prefix = self.gcs_config.get("md_prefix", "blog/md/")
        self.store = neo4j_store
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

    def save_blog_post(
        self,
        entity_id: str,
        entity_name: str,
        ticker: str,
        perspective: str,
        chart_type: str,
        title: str,
        svg_path: str,
        article_path: str,
        related_tickers: list[str] | None = None,
        subtitle: str = "",
    ) -> dict[str, str]:
        """
        Save blog post to GCS and create tracking record in Neo4j.
        
        Args:
            entity_id: Entity ID (e.g., 'google')
            entity_name: Display name (e.g., 'Google')
            ticker: Stock ticker (e.g., 'GOOGL')
            perspective: Article perspective (e.g., 'supply_chain')
            chart_type: Chart type used (e.g., 'N_TIER_NODE_MAP')
            title: Article title in Chinese
            svg_path: Local path to SVG file
            article_path: Local path to Markdown file
            related_tickers: List of related stock tickers
            subtitle: Optional subtitle
            
        Returns:
            Dict with GCS paths and blog post ID
        """
        blog_id = f"{entity_id}_{perspective}_{datetime.utcnow().strftime('%Y%m')}"
        svg_gcs_key = f"{self.svg_prefix}{entity_id}_{perspective}.svg"
        md_gcs_key = f"{self.md_prefix}{entity_id}_{perspective}.md"

        # Upload SVG to GCS
        svg_gcs_path = None
        if os.path.exists(svg_path):
            try:
                blob = self.bucket.blob(svg_gcs_key)
                blob.upload_from_filename(svg_path, content_type="image/svg+xml")
                svg_gcs_path = f"gs://{self.bucket_name}/{svg_gcs_key}"
                logger.info(f"Uploaded SVG to GCS: {svg_gcs_path}")
            except Exception as e:
                logger.error(f"Failed to upload SVG: {e}")

        # Upload Markdown to GCS
        md_gcs_path = None
        if os.path.exists(article_path):
            try:
                blob = self.bucket.blob(md_gcs_key)
                blob.upload_from_filename(article_path, content_type="text/markdown")
                md_gcs_path = f"gs://{self.bucket_name}/{md_gcs_key}"
                logger.info(f"Uploaded article to GCS: {md_gcs_path}")
            except Exception as e:
                logger.error(f"Failed to upload article: {e}")

        # Count words in article
        word_count = 0
        if os.path.exists(article_path):
            with open(article_path, "r", encoding="utf-8") as f:
                word_count = len(f.read())

        # Save metadata to Neo4j
        if self.store:
            try:
                self.store.query(
                    """
                    MERGE (b:BlogPost {id: $id})
                    SET b.entity_id = $entity_id,
                        b.entity_name = $entity_name,
                        b.ticker = $ticker,
                        b.perspective = $perspective,
                        b.chart_type = $chart_type,
                        b.title = $title,
                        b.subtitle = $subtitle,
                        b.svg_local_path = $svg_local,
                        b.svg_gcs_path = $svg_gcs,
                        b.article_local_path = $md_local,
                        b.article_gcs_path = $md_gcs,
                        b.word_count = $word_count,
                        b.related_tickers = $related,
                        b.created_at = datetime(),
                        b.status = 'published'
                    """,
                    {
                        "id": blog_id,
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "ticker": ticker,
                        "perspective": perspective,
                        "chart_type": chart_type,
                        "title": title,
                        "subtitle": subtitle,
                        "svg_local": svg_path,
                        "svg_gcs": svg_gcs_path,
                        "md_local": article_path,
                        "md_gcs": md_gcs_path,
                        "word_count": word_count,
                        "related": related_tickers or [],
                    }
                )
                logger.info(f"Saved blog post metadata to Neo4j: {blog_id}")
            except Exception as e:
                logger.error(f"Failed to save to Neo4j: {e}")

        return {
            "blog_id": blog_id,
            "svg_gcs_path": svg_gcs_path,
            "article_gcs_path": md_gcs_path,
        }

    def get_blog_posts_for_entity(self, entity_id: str) -> list[dict]:
        """Get all blog posts for an entity."""
        if not self.store:
            return []
        
        results = self.store.query(
            """
            MATCH (b:BlogPost {entity_id: $entity_id})
            RETURN b.id as id, b.entity_id as entity_id, b.perspective as perspective, 
                   b.chart_type as chart_type, b.title as title, 
                   b.svg_gcs_path as svg_gcs_path, b.article_gcs_path as article_gcs_path, 
                   b.created_at as created_at
            ORDER BY b.created_at DESC
            """,
            {"entity_id": entity_id}
        )
        return results

    def get_all_blog_posts(self, limit: int = 100) -> list[dict]:
        """Get all blog posts."""
        if not self.store:
            return []
        
        results = self.store.query(
            """
            MATCH (b:BlogPost)
            RETURN b.id as id, b.entity_id as entity_id, b.entity_name as entity_name, 
                   b.ticker as ticker, b.perspective as perspective, 
                   b.chart_type as chart_type, b.title as title, 
                   b.svg_gcs_path as svg_gcs_path, b.article_gcs_path as article_gcs_path, 
                   b.created_at as created_at
            ORDER BY b.created_at DESC
            LIMIT $limit
            """,
            {"limit": limit}
        )
        return results

    def get_used_chart_types(self, entity_id: str) -> list[str]:
        """Get chart types already used for an entity."""
        if not self.store:
            return []
        
        results = self.store.query(
            """
            MATCH (b:BlogPost {entity_id: $entity_id})
            RETURN DISTINCT b.chart_type as chart_type
            """,
            {"entity_id": entity_id}
        )
        return [r["chart_type"] for r in results if r.get("chart_type")]

    def get_used_perspectives(self, entity_id: str) -> list[str]:
        """Get perspectives already used for an entity."""
        if not self.store:
            return []
        
        results = self.store.query(
            """
            MATCH (b:BlogPost {entity_id: $entity_id})
            RETURN DISTINCT b.perspective as perspective
            """,
            {"entity_id": entity_id}
        )
        return [r["perspective"] for r in results if r.get("perspective")]

    def blog_post_exists(self, entity_id: str, perspective: str, days: int = 30) -> bool:
        """Check if a recent blog post exists for entity+perspective."""
        if not self.store:
            return False
        
        results = self.store.query(
            """
            MATCH (b:BlogPost {entity_id: $entity_id, perspective: $perspective})
            WHERE b.created_at > datetime() - duration({days: $days})
            RETURN count(b) as count
            """,
            {"entity_id": entity_id, "perspective": perspective, "days": days}
        )
        return results[0]["count"] > 0 if results else False

    def download_svg(self, gcs_path: str) -> str | None:
        """Download SVG content from GCS."""
        if not gcs_path or not gcs_path.startswith("gs://"):
            return None
        
        # Parse gs:// path
        path = gcs_path.replace(f"gs://{self.bucket_name}/", "")
        blob = self.bucket.blob(path)
        try:
            return blob.download_as_text()
        except NotFound:
            return None

    def download_article(self, gcs_path: str) -> str | None:
        """Download article content from GCS."""
        if not gcs_path or not gcs_path.startswith("gs://"):
            return None
        
        path = gcs_path.replace(f"gs://{self.bucket_name}/", "")
        blob = self.bucket.blob(path)
        try:
            return blob.download_as_text()
        except NotFound:
            return None

