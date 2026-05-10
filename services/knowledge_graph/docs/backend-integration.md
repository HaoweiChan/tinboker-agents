# Backend API Integration

This document describes how the Graph-Builder-Agent integrates with the Graphfolio Backend API to create graphs from news data.

## Overview

The agent extracts entities and relationships from news articles and creates graphs in the backend API. The integration maps agent terminology to backend API terminology:

- **Agent Entities** → **Backend Nodes** (stock IDs)
- **Agent Edges** → **Backend Edges** (with edge_type mapping)
- **Agent Graphs** → **Backend Graphs** (with metadata)

## Terminology Mapping

### Entity Types

The agent extracts various entity types, but only certain types map to backend stock IDs:

- **Ticker** entities → Stock IDs (e.g., "2330", "AAPL")
- **Organization** entities with ticker property → Stock IDs
- Other entity types (Person, Place, Product) → Not directly mapped (can be stored as metadata)

### Edge Types

Agent relation types are mapped to backend edge types:

| Agent Relation | Backend edge_type |
|----------------|-------------------|
| SUPPLIES, SUPPLIER | supplier |
| INVESTS_IN | investor |
| PARTNERS_WITH, PARTNER | partner |
| ANNOUNCED | announcement |
| COMPETES_WITH, COMPETITOR | competitor |
| ACQUIRES | acquisition |
| MERGES_WITH | merger |
| OWNS | ownership |
| WORKS_FOR | employment |
| Other | related (default) |

## Architecture

```
News Articles
    ↓
IngestionService (fetch from GDELT)
    ↓
ExtractionService (extract entities/edges)
    ↓
BackendMapper (map to backend format)
    ↓
BackendGraphService (create/update graphs)
    ↓
Backend API (Graphfolio Backend)
```

## Services

### `BackendAPIClient`

Low-level HTTP client for backend API endpoints:

- `create_graph()` - Create new graph
- `get_graph()` - Get graph by ID
- `list_graphs()` - List all graphs
- `add_nodes()` - Add nodes to existing graph
- `add_edges()` - Add edges to existing graph
- `get_company()` - Get company data

### `BackendMapper`

Maps agent entities/edges to backend format:

- `extract_stock_ids()` - Extract valid stock IDs from entities
- `build_entity_to_stock_map()` - Map entity IDs to stock IDs
- `map_edges_to_backend_format()` - Convert agent edges to backend format
- `_normalize_stock_id()` - Normalize stock ID format (numeric → Taiwan, alphabetic → US)

### `BackendGraphService`

High-level service for graph operations:

- `create_graph_from_entities_and_edges()` - Create graph from extracted data
- `upsert_to_existing_graph()` - Add nodes/edges to existing graph
- `get_graph()` - Retrieve graph data
- `list_graphs()` - List all graphs
- `verify_stock_exists()` - Check if stock ID exists in backend

### `NewsToGraphService`

Orchestrates the full pipeline:

- `create_graph_from_news()` - End-to-end: ingest → extract → create graph
- `update_graph_from_news()` - End-to-end: ingest → extract → update graph

## Usage Examples

### CLI Commands

```bash
# Create graph from news
ng backend create-graph-from-news \
  --source gdelt \
  --q "NVIDIA TSMC supply chain" \
  --name "Semiconductor Supply Chain" \
  --days 7 \
  --pipeline rules+openie \
  --tags "semiconductors,supply-chain" \
  --backend http://localhost:5174

# Update existing graph with new news
ng backend update-graph-from-news \
  --graph-id <uuid> \
  --source gdelt \
  --q "NVIDIA earnings" \
  --days 3

# List all graphs in backend
ng backend list-backend-graphs
```

### Python API

```python
from services.news_to_graph_service import NewsToGraphService

service = NewsToGraphService(backend_url="http://localhost:5174")

# Create graph from news
result = service.create_graph_from_news(
    source="gdelt",
    query="NVIDIA TSMC supply chain",
    graph_name="Semiconductor Network",
    days=7,
    pipeline="rules+openie",
    tags=["semiconductors", "supply-chain"],
)

print(f"Graph ID: {result['graph_id']}")
print(f"Stock IDs found: {result['stock_ids_found']}")

# Update existing graph
update_result = service.update_graph_from_news(
    graph_id=result['graph_id'],
    source="gdelt",
    query="NVIDIA earnings",
    days=3,
)
```

## Stock ID Detection

The mapper extracts stock IDs from entities using these rules:

1. **Ticker entities**: Entity ID is normalized to stock ID
   - `ticker:2330` → `2330` (Taiwan stock)
   - `ticker:AAPL` → `AAPL` (US stock)

2. **Organization entities**: Checks for ticker in props or external_ids
   - `props.ticker = "2330"` → `2330`
   - `external_ids.ticker = "AAPL"` → `AAPL`

3. **Stock ID format validation**:
   - Numeric 4-digit → Taiwan stock (e.g., "2330", "2317")
   - Alphabetic 1-5 chars → US stock (e.g., "AAPL", "MSFT")

## Edge Mapping

Edges are mapped only if both source and target entities have valid stock IDs:

```python
# Agent edge
Edge(src="entity:nvidia", dst="entity:tsmc", rel="SUPPLIES")

# Backend edge
{
    "source": "NVDA",
    "target": "2330",
    "edge_type": "supplier",
    "description": "NVIDIA supplies GPUs to TSMC"
}
```

## Error Handling

- **No stock IDs found**: Returns warning, doesn't create graph
- **Invalid stock IDs**: Filtered out during mapping
- **Backend API errors**: Propagated with clear error messages
- **Network errors**: Handled with retry logic (future enhancement)

## Configuration

Backend URL can be configured:

1. **CLI parameter**: `--backend http://localhost:5174`
2. **Config file**: `configs/dev.yaml` (future)
3. **Environment variable**: `GRAPH_BACKEND_URL` (future)

## Future Enhancements

- [ ] Batch processing for large news datasets
- [ ] Incremental updates (only new edges)
- [ ] Entity disambiguation (same company, different names)
- [ ] Confidence scoring for edges
- [ ] Evidence linking (store news snippets as edge metadata)
- [ ] Graph merging (combine multiple news-generated graphs)
- [ ] Real-time updates via WebSocket

