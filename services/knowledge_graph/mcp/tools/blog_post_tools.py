"""
MCP Tools for Blog Post Management.

This module provides MCP-compatible tools for managing supply chain blog posts:
- List existing blog posts
- Save new blog posts to GCS and Neo4j
- Check for duplicate posts
- Suggest unused perspectives for entities
"""

from typing import Any

from services.blog_post_storage import BlogPostStorage
from services.graph_service import GraphService


class MCPBlogPostTools:
    """MCP tools for blog post management."""

    PERSPECTIVE_CHART_MAP = {
        "supply_chain": ["N_TIER_NODE_MAP", "FORCE_DIRECTED", "VALUE_STREAM"],
        "ai_business": ["STACK_PYRAMID", "BOM_TREE", "N_TIER_NODE_MAP"],
        "financial": ["SANKEY", "COMPARISON_DASHBOARD", "STACK_PYRAMID"],
        "strategy": ["RADAR_CONSTELLATION", "COMPARISON_DASHBOARD", "FORCE_DIRECTED"],
        "product_line": ["BOM_TREE", "STACK_PYRAMID", "ORG_CHART"],
        "risk": ["HEATMAP_RISK", "RADAR_CONSTELLATION", "FORCE_DIRECTED"],
        "esg": ["COMPARISON_DASHBOARD", "RADAR_CONSTELLATION", "HEATMAP_RISK"],
        "tech_roadmap": ["SWIMLANE", "VALUE_STREAM", "BOM_TREE"],
        "value_chain": ["VALUE_STREAM", "SANKEY", "SWIMLANE"],
        "network": ["FORCE_DIRECTED", "N_TIER_NODE_MAP", "RADAR_CONSTELLATION"],
        "geo_distribution": ["GEO_MAP", "HEATMAP_RISK", "FORCE_DIRECTED"],
        "org_structure": ["ORG_CHART", "BOM_TREE", "STACK_PYRAMID"],
    }

    ALL_PERSPECTIVES = list(PERSPECTIVE_CHART_MAP.keys())

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.graph_service = GraphService(config)
        self.store = self.graph_service.get_store()
        gcs_config = self.config.get("cost_optimization", {}).get("caching", {}).get("gcs", {})
        self.storage = BlogPostStorage(gcs_config=gcs_config, neo4j_store=self.store)

    def list_blog_posts(self, entity_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        """
        List existing blog posts.
        
        Args:
            entity_id: Optional entity ID to filter by
            limit: Maximum number of posts to return
            
        Returns:
            Dict with list of blog posts
        """
        if entity_id:
            posts = self.storage.get_blog_posts_for_entity(entity_id)
        else:
            posts = self.storage.get_all_blog_posts(limit=limit)

        return {
            "status": "success",
            "count": len(posts),
            "posts": posts,
        }

    def check_duplicate(
        self, 
        entity_id: str, 
        perspective: str, 
        days: int = 30
    ) -> dict[str, Any]:
        """
        Check if a recent blog post exists for entity+perspective.
        
        Args:
            entity_id: Entity ID (e.g., 'google')
            perspective: Perspective (e.g., 'supply_chain')
            days: Number of days to look back
            
        Returns:
            Dict with exists flag and details
        """
        exists = self.storage.blog_post_exists(entity_id, perspective, days=days)
        used_perspectives = self.storage.get_used_perspectives(entity_id)
        used_charts = self.storage.get_used_chart_types(entity_id)

        return {
            "status": "success",
            "entity_id": entity_id,
            "perspective": perspective,
            "exists_within_days": exists,
            "days_checked": days,
            "used_perspectives": used_perspectives,
            "used_chart_types": used_charts,
        }

    def suggest_perspective(self, entity_id: str) -> dict[str, Any]:
        """
        Suggest unused perspectives and chart types for an entity.
        
        Args:
            entity_id: Entity ID (e.g., 'google')
            
        Returns:
            Dict with available perspectives and recommended chart types
        """
        used_perspectives = set(self.storage.get_used_perspectives(entity_id))
        used_charts = set(self.storage.get_used_chart_types(entity_id))

        available_perspectives = [p for p in self.ALL_PERSPECTIVES if p not in used_perspectives]

        suggestions = []
        for perspective in available_perspectives:
            charts = self.PERSPECTIVE_CHART_MAP.get(perspective, [])
            # Find first unused chart for this perspective
            recommended_chart = None
            for chart in charts:
                if chart not in used_charts:
                    recommended_chart = chart
                    break
            if recommended_chart is None and charts:
                recommended_chart = charts[0]  # Fallback to primary even if used
            
            suggestions.append({
                "perspective": perspective,
                "recommended_chart": recommended_chart,
                "available_charts": [c for c in charts if c not in used_charts],
            })

        return {
            "status": "success",
            "entity_id": entity_id,
            "used_perspectives": list(used_perspectives),
            "used_chart_types": list(used_charts),
            "available_count": len(available_perspectives),
            "suggestions": suggestions,
        }

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
    ) -> dict[str, Any]:
        """
        Save a blog post to GCS and track in Neo4j.
        
        Args:
            entity_id: Entity ID (e.g., 'google')
            entity_name: Display name (e.g., 'Google')
            ticker: Stock ticker (e.g., 'GOOGL')
            perspective: Article perspective (e.g., 'supply_chain')
            chart_type: Chart type used (e.g., 'N_TIER_NODE_MAP')
            title: Article title in Chinese
            svg_path: Local path to SVG file
            article_path: Local path to Markdown file
            related_tickers: Optional list of related tickers
            subtitle: Optional subtitle
            
        Returns:
            Dict with GCS paths and blog post ID
        """
        result = self.storage.save_blog_post(
            entity_id=entity_id,
            entity_name=entity_name,
            ticker=ticker,
            perspective=perspective,
            chart_type=chart_type,
            title=title,
            svg_path=svg_path,
            article_path=article_path,
            related_tickers=related_tickers,
            subtitle=subtitle,
        )

        return {
            "status": "success",
            "blog_id": result.get("blog_id"),
            "svg_gcs_path": result.get("svg_gcs_path"),
            "article_gcs_path": result.get("article_gcs_path"),
        }

    def get_entity_blog_summary(self, entity_id: str) -> dict[str, Any]:
        """
        Get a summary of all blog posts for an entity.
        
        Args:
            entity_id: Entity ID (e.g., 'google')
            
        Returns:
            Dict with entity blog post summary
        """
        posts = self.storage.get_blog_posts_for_entity(entity_id)
        used_perspectives = self.storage.get_used_perspectives(entity_id)
        used_charts = self.storage.get_used_chart_types(entity_id)
        available = [p for p in self.ALL_PERSPECTIVES if p not in used_perspectives]

        return {
            "status": "success",
            "entity_id": entity_id,
            "total_posts": len(posts),
            "perspectives_used": used_perspectives,
            "chart_types_used": used_charts,
            "perspectives_available": available,
            "posts": posts,
        }

    def close(self):
        """Close database connections."""
        self.graph_service.close()




