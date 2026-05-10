# MCP Integration

This directory is reserved for future Model Context Protocol (MCP) integration.

## Planned Components

- `mcp/servers/neo4j_proxy/`: Configuration and glue code for Neo4j MCP server
- `mcp/servers/memgraph_proxy/`: Configuration for Memgraph MCP server
- `mcp/tools/`: Custom MCP tools (e.g., summarize, upsert)

## Integration Path

When ready to add MCP support:

1. Install official Neo4j MCP server or Memgraph/FalkorDB variants
2. Configure MCP servers in `mcp/servers/`
3. Expose high-level tools via MCP layer:
   - `get_neighbors(entity, hop=2)`
   - `explain_edge(src, rel, dst) -> evidence passages`
   - `upsert_fact(text, schema_hint)`

## References

- Model Context Protocol specification
- Neo4j MCP tooling and guides
- Smithery community registry for MCP servers

