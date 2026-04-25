#!/usr/bin/env python3
"""
Blog Post MCP Server for Cursor.

This is a stdio-based MCP server that works with Cursor's MCP integration.
It uses the Model Context Protocol (MCP) standard.

Run with:
    python -m mcp.servers.blog_mcp_server

Or via uvx (if published as a package):
    uvx blog-post-mcp
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import yaml

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # MCP servers log to stderr, communicate on stdout
)
logger = logging.getLogger("blog-mcp-server")


def load_config() -> dict:
    """Load configuration from environment or config file."""
    # Check environment variables first (for production)
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        return {
            "graph_store": {
                "type": "neo4j",
                "neo4j": {
                    "uri": neo4j_uri,
                    "user": os.getenv("NEO4J_USER", "neo4j"),
                    "password": os.getenv("NEO4J_PASSWORD", ""),
                    "database": os.getenv("NEO4J_DATABASE", "neo4j"),
                }
            },
            "cost_optimization": {
                "caching": {
                    "gcs": {
                        "enabled": os.getenv("GCS_ENABLED", "true").lower() == "true",
                        "bucket_name": os.getenv("GCS_BUCKET_NAME", "graphfolio-articles"),
                    }
                }
            }
        }

    # Load .env file if it exists
    env_file = project_root / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

    # Check again after loading .env
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        return {
            "graph_store": {
                "type": "neo4j",
                "neo4j": {
                    "uri": neo4j_uri,
                    "user": os.getenv("NEO4J_USER", "neo4j"),
                    "password": os.getenv("NEO4J_PASSWORD", ""),
                    "database": os.getenv("NEO4J_DATABASE", "neo4j"),
                }
            },
            "cost_optimization": {
                "caching": {
                    "gcs": {
                        "enabled": os.getenv("GCS_ENABLED", "true").lower() == "true",
                        "bucket_name": os.getenv("GCS_BUCKET_NAME", "graphfolio-articles"),
                    }
                }
            }
        }

    # Fallback to YAML config
    config_path = project_root / "configs" / "dev.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)

    return {}


# MCP Tool Definitions
TOOLS = [
    {
        "name": "list_blog_posts",
        "description": "List existing blog posts. Optionally filter by entity_id to see what articles exist for a specific company.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Optional entity ID to filter by (e.g., 'google', 'tsmc')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of posts to return",
                    "default": 50,
                },
            },
            "required": [],
        },
    },
    {
        "name": "check_duplicate",
        "description": "Check if a recent blog post exists for an entity+perspective combination. Use this before generating to avoid duplicates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Entity ID (e.g., 'google', 'tsmc')",
                },
                "perspective": {
                    "type": "string",
                    "description": "Perspective (e.g., 'supply_chain', 'ai_business', 'financial')",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to check for existing posts",
                    "default": 30,
                },
            },
            "required": ["entity_id", "perspective"],
        },
    },
    {
        "name": "suggest_perspective",
        "description": "Suggest unused perspectives and chart types for an entity. Use this to find what new articles can be generated.",
        "inputSchema": {
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
        "description": "Save a blog post (SVG + Article) to GCS and track in Neo4j. Call this after generating the SVG and article files.",
        "inputSchema": {
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
                    "description": "Chart type used (e.g., 'N_TIER_NODE_MAP', 'STACK_PYRAMID')",
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
            },
            "required": [
                "entity_id", "entity_name", "ticker", "perspective",
                "chart_type", "title", "svg_path", "article_path"
            ],
        },
    },
    {
        "name": "get_entity_summary",
        "description": "Get a complete summary of all blog posts for an entity, including what perspectives are used and available.",
        "inputSchema": {
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


class BlogMCPServer:
    """MCP Server for blog post management."""

    def __init__(self):
        self.config = load_config()
        self._tools = None

    @property
    def tools(self):
        """Lazy-load tools to avoid connection at startup."""
        if self._tools is None:
            from mcp.tools.blog_post_tools import MCPBlogPostTools
            self._tools = MCPBlogPostTools(self.config)
        return self._tools

    def handle_request(self, request: dict) -> dict:
        """Handle an MCP JSON-RPC request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "blog-post-mcp",
                        "version": "1.0.0",
                    },
                    "capabilities": {
                        "tools": {},
                    },
                }
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                result = self.call_tool(tool_name, arguments)
            elif method == "notifications/initialized":
                # Client notification, no response needed
                return None
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)},
            }

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict:
        """Execute a tool and return the result."""
        logger.info(f"Calling tool: {name} with args: {arguments}")

        try:
            if name == "list_blog_posts":
                result = self.tools.list_blog_posts(
                    entity_id=arguments.get("entity_id"),
                    limit=arguments.get("limit", 50),
                )
            elif name == "check_duplicate":
                result = self.tools.check_duplicate(
                    entity_id=arguments["entity_id"],
                    perspective=arguments["perspective"],
                    days=arguments.get("days", 30),
                )
            elif name == "suggest_perspective":
                result = self.tools.suggest_perspective(
                    entity_id=arguments["entity_id"],
                )
            elif name == "save_blog_post":
                result = self.tools.save_blog_post(
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
                result = self.tools.get_entity_blog_summary(
                    entity_id=arguments["entity_id"],
                )
            else:
                return {
                    "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                    "isError": True,
                }

            # Format result as MCP content
            return {
                "content": [
                    {"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}
                ],
            }

        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True,
            }

    def run(self):
        """Run the MCP server in stdio mode."""
        logger.info("Blog Post MCP Server starting...")

        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                    logger.debug(f"Received: {request}")

                    response = self.handle_request(request)
                    if response:
                        response_str = json.dumps(response, ensure_ascii=False)
                        print(response_str, flush=True)
                        logger.debug(f"Sent: {response_str[:200]}...")

                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error"},
                    }
                    print(json.dumps(error_response), flush=True)

        except KeyboardInterrupt:
            logger.info("Server shutting down...")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            if self._tools:
                self._tools.close()


def main():
    """Entry point for the MCP server."""
    server = BlogMCPServer()
    server.run()


if __name__ == "__main__":
    main()




