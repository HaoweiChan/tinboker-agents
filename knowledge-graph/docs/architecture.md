# Architecture: Service Layer Pattern

## Overview

This project uses a **service layer pattern** to ensure that CLI commands, API endpoints, and MCP servers all share the same business logic. This prevents code duplication and ensures consistency across all interfaces.

## Architecture Layers

```
┌──────────────────────────────────────────-─┐
│  Presentation Layer (apps/)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   CLI    │  │   API    │  │   MCP    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
└───────┼─────────────┼─────────────┼─-───-──┘
        │             │             │
        └─────────────┴─────────────┘
                    │
        ┌───────────▼────────────┐
        │  Service Layer         │
        │  (services/)           │
        │  ┌─────────────────-┐  │
        │  │ IngestionService │  │
        │  │ ExtractionService│  │
        │  │ GraphService     │  │
        │  │ ArticleCache     │  │
        │  │ ArticleStorage   │  │
        │  │ TierManager      │  │
        │  └─────────────────-┘  │
        └───────────┬────────────┘
                    │
        ┌───────────▼────────────┐
        │  Domain Layer          │
        │  (ingest/, extract/,   │
        │   graph/, pipelines/)  │
        └────────────────────────┘
```

## Storage Architecture

The system uses a **hybrid storage strategy** to optimize costs:

```
┌─────────────────┐     ┌──────────────────────────────────┐
│   Tavily API    │────▶│         ArticleCache             │
│   (fetch news)  │     │  (services/article_cache.py)     │
└─────────────────┘     └────────────────┬─────────────────┘
                                         │
                        ┌────────────────┴────────────────┐
                        ▼                                 ▼
              ┌─────────────────┐               ┌─────────────────┐
              │  Google Cloud   │               │     Neo4j       │
              │    Storage      │               │  (Graph DB)     │
              │                 │               │                 │
              │  Raw article    │               │  - Metadata     │
              │  text content   │               │    (URL, status │
              │                 │               │     ticker)     │
              │  ~$0.02/GB/mo   │               │  - Entities     │
              │                 │               │  - Edges        │
              └─────────────────┘               │  - Evidence     │
                                                └─────────────────┘
```

### Why Hybrid Storage?

| Data Type | Storage | Reason |
|-----------|---------|--------|
| Raw articles | GCS | Cheap blob storage, rarely queried |
| Article metadata | Neo4j | Quick lookups for cache checks |
| Entities/Edges | Neo4j | Graph queries, relationships |
| Evidence | Neo4j | Linked to edges |

### Cost Comparison

| Scenario | Neo4j Only | Hybrid (GCS + Neo4j) |
|----------|------------|---------------------|
| 10k articles | ~500MB | ~10MB (metadata) |
| Monthly cost | High | ~$0.01 (GCS) + minimal Neo4j |
| Query speed | Same | Same (metadata in Neo4j) |

### Configuration

```yaml
# configs/dev.yaml
cost_optimization:
  caching:
    enabled: true
    ttl_hours: 24
    gcs:
      enabled: true
      bucket_name: "graphfolio-articles"
      prefix: "articles/"
```

## Service Layer Components

### `IngestionService`
- Handles data ingestion from various sources (GDELT, Newscatcher, RSS)
- Manages connector lifecycle
- Provides unified interface for fetching documents

**Used by:**
- CLI: `ng ingest` command
- API: `/api/v1/ingest` endpoint
- MCP: `ingest_fact` tool

### `ExtractionService`
- Manages extraction pipelines (rules, openie, llm)
- Handles document loading and formatting
- Provides output formatting (JSON, TOON)

**Used by:**
- CLI: `ng extract` command
- API: `/api/v1/extract` endpoint
- MCP: `extract_from_text` tool

### `GraphService`
- Manages graph store connections
- Provides high-level graph operations:
  - `upsert()` - Add entities/edges/evidence
  - `query()` - Execute Cypher queries
  - `get_neighbors()` - Find connected entities
  - `explain_edge()` - Get evidence for relationships

**Used by:**
- CLI: `ng upsert` and `ng query` commands
- API: `/api/v1/query`, `/api/v1/neighbors`, `/api/v1/explain-edge` endpoints
- MCP: `get_neighbors`, `explain_edge`, `upsert_fact` tools

### `PipelineService`
- Orchestrates full pipeline: ingest → extract → upsert
- Combines multiple services for end-to-end workflows

**Used by:**
- CLI: Full pipeline execution
- API: `/api/v1/pipeline` endpoint
- MCP: `run_pipeline` tool

## Benefits

1. **DRY Principle**: Business logic exists in one place
2. **Consistency**: All interfaces behave identically
3. **Testability**: Services can be tested independently
4. **Maintainability**: Changes to business logic only need to be made once
5. **Flexibility**: Easy to add new interfaces (gRPC, GraphQL, etc.)

## Example Usage

### CLI
```python
from services.ingestion_service import IngestionService

service = IngestionService(config)
docs = service.ingest(source="gdelt", query="NVIDIA", days=7)
```

### API
```python
from services.ingestion_service import IngestionService

@app.post("/api/v1/ingest")
async def ingest(request: IngestRequest):
    service = IngestionService()
    docs = service.ingest(source=request.source, query=request.query, days=request.days)
    return {"docs": [doc.model_dump() for doc in docs]}
```

### MCP Server
```python
from services.graph_service import GraphService

class MCPTools:
    def __init__(self):
        self.graph_service = GraphService()
    
    def get_neighbors(self, entity_id: str, hop: int = 2):
        return self.graph_service.get_neighbors(entity_id, hop=hop)
```

## Adding New Interfaces

To add a new interface (e.g., gRPC, GraphQL):

1. Create new directory: `apps/grpc/` or `apps/graphql/`
2. Import services from `services/`
3. Map service methods to your interface's protocol
4. No need to duplicate business logic!

## Configuration

All services accept a `config` dictionary parameter, allowing them to be configured consistently across all interfaces. Configuration is typically loaded from `configs/dev.yaml`.

