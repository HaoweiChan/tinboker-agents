"""
MCP Server for Blog Post Management.

Run with:
    python -m mcp.servers.blog_post_server

This server exposes tools for managing supply chain blog posts:
- list_blog_posts: List existing blog posts
- check_duplicate: Check if a post exists
- suggest_perspective: Get suggestions for new posts
- save_blog_post: Save a post to GCS/Neo4j
- get_entity_summary: Get summary for an entity
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.tools.blog_post_tools import MCPBlogPostTools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "configs/dev.yaml") -> dict:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f)
    return {}


class BlogPostMCPServer:
    """MCP Server for blog post management."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or load_config()
        self.tools = MCPBlogPostTools(self.config)

    def get_tool_definitions(self) -> list[dict]:
        """Return MCP tool definitions."""
        return [
            {
                "name": "list_blog_posts",
                "description": "List existing blog posts. Optionally filter by entity_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Optional entity ID to filter by (e.g., 'google')",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of posts to return (default: 50)",
                            "default": 50,
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "check_duplicate",
                "description": "Check if a recent blog post exists for an entity+perspective combination.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID (e.g., 'google', 'tsmc')",
                        },
                        "perspective": {
                            "type": "string",
                            "description": "Perspective (e.g., 'supply_chain', 'ai_business')",
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days to check (default: 30)",
                            "default": 30,
                        },
                    },
                    "required": ["entity_id", "perspective"],
                },
            },
            {
                "name": "suggest_perspective",
                "description": "Suggest unused perspectives and chart types for an entity.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID to get suggestions for",
                        },
                    },
                    "required": ["entity_id"],
                },
            },
            {
                "name": "save_blog_post",
                "description": "Save a blog post (SVG + Article) to GCS and track in Neo4j.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID (e.g., 'google')",
                        },
                        "entity_name": {
                            "type": "string",
                            "description": "Display name (e.g., 'Google')",
                        },
                        "ticker": {
                            "type": "string",
                            "description": "Stock ticker (e.g., 'GOOGL')",
                        },
                        "perspective": {
                            "type": "string",
                            "description": "Article perspective (e.g., 'supply_chain')",
                        },
                        "chart_type": {
                            "type": "string",
                            "description": "Chart type used (e.g., 'N_TIER_NODE_MAP')",
                        },
                        "title": {
                            "type": "string",
                            "description": "Article title in Chinese",
                        },
                        "svg_path": {
                            "type": "string",
                            "description": "Local path to SVG file",
                        },
                        "article_path": {
                            "type": "string",
                            "description": "Local path to Markdown article file",
                        },
                        "related_tickers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of related stock tickers",
                        },
                        "subtitle": {
                            "type": "string",
                            "description": "Optional subtitle",
                        },
                    },
                    "required": [
                        "entity_id", "entity_name", "ticker", "perspective",
                        "chart_type", "title", "svg_path", "article_path"
                    ],
                },
            },
            {
                "name": "get_entity_summary",
                "description": "Get a summary of all blog posts for an entity.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Entity ID to get summary for",
                        },
                    },
                    "required": ["entity_id"],
                },
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and return the result."""
        try:
            if name == "list_blog_posts":
                return self.tools.list_blog_posts(
                    entity_id=arguments.get("entity_id"),
                    limit=arguments.get("limit", 50),
                )
            elif name == "check_duplicate":
                return self.tools.check_duplicate(
                    entity_id=arguments["entity_id"],
                    perspective=arguments["perspective"],
                    days=arguments.get("days", 30),
                )
            elif name == "suggest_perspective":
                return self.tools.suggest_perspective(
                    entity_id=arguments["entity_id"],
                )
            elif name == "save_blog_post":
                return self.tools.save_blog_post(
                    entity_id=arguments["entity_id"],
                    entity_name=arguments["entity_name"],
                    ticker=arguments["ticker"],
                    perspective=arguments["perspective"],
                    chart_type=arguments["chart_type"],
                    title=arguments["title"],
                    svg_path=arguments["svg_path"],
                    article_path=arguments["article_path"],
                    related_tickers=arguments.get("related_tickers"),
                    subtitle=arguments.get("subtitle", ""),
                )
            elif name == "get_entity_summary":
                return self.tools.get_entity_blog_summary(
                    entity_id=arguments["entity_id"],
                )
            else:
                return {"status": "error", "message": f"Unknown tool: {name}"}
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {"status": "error", "message": str(e)}

    def close(self):
        """Close connections."""
        self.tools.close()


def main():
    """Run the MCP server in stdio mode."""
    server = BlogPostMCPServer()

    print("Blog Post MCP Server started", file=sys.stderr)
    print(f"Available tools: {[t['name'] for t in server.get_tool_definitions()]}", file=sys.stderr)

    try:
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                method = request.get("method", "")
                params = request.get("params", {})

                if method == "tools/list":
                    response = {"tools": server.get_tool_definitions()}
                elif method == "tools/call":
                    tool_name = params.get("name", "")
                    arguments = params.get("arguments", {})
                    result = server.call_tool(tool_name, arguments)
                    response = {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
                else:
                    response = {"error": f"Unknown method: {method}"}

                print(json.dumps({"jsonrpc": "2.0", "id": request.get("id"), "result": response}))
                sys.stdout.flush()

            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(json.dumps({"jsonrpc": "2.0", "error": {"message": str(e)}}))
                sys.stdout.flush()

    except KeyboardInterrupt:
        pass
    finally:
        server.close()


if __name__ == "__main__":
    main()




