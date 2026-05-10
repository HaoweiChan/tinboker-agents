# Blog Post MCP Server

This document describes how to set up and use the Blog Post MCP (Model Context Protocol) server with Cursor IDE.

## Overview

The MCP server provides tools for managing supply chain blog posts:
- List existing blog posts
- Check for duplicate posts
- Suggest new perspectives for articles
- Save blog posts to GCS and track in Neo4j

## Setup

### Prerequisites

1. Python 3.11+
2. Project dependencies installed (`uv pip install -e ".[dev]"`)
3. Neo4j Aura database configured (`.env` file with credentials)
4. GCS bucket configured (`graphfolio-articles`)

### Environment Variables

Create a `.env` file in the project root:

```bash
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
GCS_BUCKET_NAME=graphfolio-articles
GCS_ENABLED=true
```

## Adding to Cursor

### Step 1: Create MCP Config

Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "blog-post-manager": {
      "command": "python",
      "args": ["-m", "mcp.servers.blog_mcp_server"],
      "cwd": "/path/to/Graph-Builder-Agent"
    }
  }
}
```

Replace `/path/to/Graph-Builder-Agent` with your actual project path.

### Step 2: Restart Cursor

After saving the config, restart Cursor to load the MCP server.

### Step 3: Verify

The MCP tools should now be available in Cursor. You can ask Cursor to:
- "Suggest new blog perspectives for Google"
- "Check if a supply chain article exists for TSMC"
- "Save the blog post I just created"

## Available Tools

| Tool | Description | Required Parameters |
|------|-------------|---------------------|
| `list_blog_posts` | List existing posts | `entity_id` (optional), `limit` |
| `check_duplicate` | Check if post exists | `entity_id`, `perspective`, `days` |
| `suggest_perspective` | Get suggestions | `entity_id` |
| `save_blog_post` | Save to GCS/Neo4j | `entity_id`, `entity_name`, `ticker`, `perspective`, `chart_type`, `title`, `svg_path`, `article_path` |
| `get_entity_summary` | Full entity summary | `entity_id` |

## Testing

### Test 1: List Available Tools

```bash
cd /path/to/Graph-Builder-Agent
source .venv/bin/activate

echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m mcp.servers.blog_mcp_server 2>/dev/null | jq
```

Expected output:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {"name": "list_blog_posts", ...},
      {"name": "check_duplicate", ...},
      ...
    ]
  }
}
```

### Test 2: Suggest Perspectives

```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"suggest_perspective","arguments":{"entity_id":"google"}}}' | python -m mcp.servers.blog_mcp_server 2>/dev/null | jq
```

Expected output:
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"status\": \"success\", \"used_perspectives\": [\"supply_chain\", \"ai_business\"], ...}"
    }]
  }
}
```

### Test 3: Check Duplicate

```bash
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"check_duplicate","arguments":{"entity_id":"google","perspective":"supply_chain"}}}' | python -m mcp.servers.blog_mcp_server 2>/dev/null | jq
```

### Test 4: Interactive Testing

For debugging, run the server with stderr visible:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python -m mcp.servers.blog_mcp_server
```

## Troubleshooting

### Server Not Starting

1. Check Python version: `python --version` (should be 3.11+)
2. Ensure virtual environment is activated
3. Check `.env` file exists with valid credentials

### Neo4j Connection Failed

1. Verify `NEO4J_URI` is correct
2. Check network connectivity to Neo4j Aura
3. Verify credentials in `.env`

### Tools Not Appearing in Cursor

1. Verify `~/.cursor/mcp.json` syntax is valid
2. Check the `cwd` path is correct
3. Restart Cursor completely (not just reload)
4. Check Cursor MCP logs for errors

### GCS Upload Failed

1. Ensure you're logged into GCS: `gcloud auth application-default login`
2. Verify bucket exists: `gsutil ls gs://graphfolio-articles/`
3. Check bucket permissions

## File Structure

```
mcp/
├── __init__.py
├── servers/
│   ├── __init__.py
│   └── blog_mcp_server.py  # Stdio-based MCP server
└── tools/
    ├── __init__.py
    ├── blog_post_tools.py  # Tool implementations
    └── example_mcp_tools.py
```

## Architecture

```
┌─────────────────┐      stdio       ┌──────────────────┐
│  Cursor IDE     │ ◄──────────────► │  blog_mcp_server │
└─────────────────┘                  └────────┬─────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │ blog_post_tools  │
                                    └────────┬─────────┘
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        ▼                     ▼                     ▼
               ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
               │   Neo4j Aura   │   │      GCS       │   │  Local Files   │
               │  (metadata)    │   │  (SVG/MD)      │   │  (generation)  │
               └────────────────┘   └────────────────┘   └────────────────┘
```

## Related Documentation

- [Supply Chain Content Generation Rules](../.cursor/rules/supply-chain-content-generation.mdc)
- [Cost Optimization](./cost-optimization.md)
- [Architecture](./architecture.md)

