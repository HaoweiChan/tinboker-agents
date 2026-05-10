# Graph-Builder-Agent

API-first knowledge graph pipeline that ingests news/data sources, extracts entities/relations/events, and stores them in a graph database with full provenance. Built with TOON format support for LLM efficiency and structured for future MCP agent integration.

## Features

- **Tiered Processing**: Cost-optimized ingestion with 3 tiers (50/500/all stocks)
- **Hybrid Storage**: GCS for raw articles, Neo4j for graph data (96% Neo4j cost reduction)
- **Article Caching**: Prevents duplicate API calls across runs
- **Re-extraction**: Retry failed extractions without re-fetching from Tavily
- **Multi-Market Support**: US and Taiwan stock markets
- **API-First Architecture**: Start with rule-based extraction, upgrade to LLM extractors seamlessly
- **Event-Centric Schema**: Provenance-first design with evidence linking
- **Storage Abstraction**: Swap between Neo4j, Kùzu, or Memgraph easily

## Quick Start

### Installation

```bash
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```bash
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
GOOGLE_API_KEY=your_gemini_key
TAVILY_API_KEY=your_tavily_key
```

## Storage Architecture

Raw articles are stored in **Google Cloud Storage** (cheap), while graph data stays in **Neo4j**:

```
┌─────────────┐     ┌───────────────┐     ┌─────────────┐
│ Tavily API  │────▶│ ArticleCache  │────▶│     GCS     │  Raw text
└─────────────┘     │               │     │ ~$0.02/GB   │
                    │               │     └─────────────┘
                    │               │     ┌─────────────┐
                    │               │────▶│   Neo4j     │  Entities, Edges
                    └───────────────┘     │  Metadata   │
                                          └─────────────┘
```

| Data Type | Storage | Cost |
|-----------|---------|------|
| Raw article text | GCS | ~$0.02/GB/month |
| Article metadata (URL, status) | Neo4j | Minimal |
| Entities & Relationships | Neo4j | Graph queries |

### GCS Setup (Optional, for production)

```bash
# Create bucket
gcloud storage buckets create gs://graphfolio-articles --location=us-central1

# Enable in config (configs/dev.yaml)
cost_optimization:
  caching:
    gcs:
      enabled: true
      bucket_name: "graphfolio-articles"
```

If GCS is disabled, articles are stored in Neo4j (fallback for local dev).

## Ingestion Workflow

### Tier-Based Processing

Stocks are categorized into 3 tiers for cost-optimized processing:

| Tier | Stocks | Processing | Est. Cost |
|------|--------|------------|-----------|
| 1 | 50 | Full LLM planning, 5 queries, 5 docs | ~$0.15/ticker |
| 2 | 365 | Template queries, 2 queries, 3 docs | ~$0.05/ticker |
| 3 | 11,000+ | Template queries, 1 query, 2 docs | ~$0.02/ticker |

Tier lists are defined in `data/seeds/tier_1_tickers.txt` and `data/seeds/tier_2_tickers.txt`.

### Run Ingestion by Tier

```bash
# Process all Tier 1 stocks (top 50 US + TW)
python -m apps.cli.main ingest-batch --tier 1

# Process with a limit (for testing)
python -m apps.cli.main ingest-batch --tier 1 --limit 5

# Process Tier 2 stocks
python -m apps.cli.main ingest-batch --tier 2

# Process specific tickers
python -m apps.cli.main ingest-batch --tickers TSLA,AAPL,NVDA
```

### Run Single Ticker with Visualization

```bash
# Search and extract for a single ticker
python -m apps.cli.main search-agent --ticker TSLA

# Generate visualization from graph data
python -m apps.cli.main generate-content --ticker TSLA
```

### Re-extract Failed Articles

Articles are saved before LLM extraction. If extraction fails, you can retry without re-fetching from Tavily:

```bash
# View article cache statistics
python -m apps.cli.main article-stats

# Re-extract failed articles (no API cost!)
python -m apps.cli.main re-extract --status failed

# Re-extract pending articles for a specific ticker
python -m apps.cli.main re-extract --status pending --ticker TSLA --limit 50
```

### Workflow Architecture

```
[Local Machine]                         [Cloud]
     |                                     |
     |-- ingest-batch --tier 1 ---------> Neo4j Aura (stores data)
     |                                     ^
     |                                     |
[GCP Cloud Run API] ---- query -----------+
     |
     +-- /api/v1/pipeline/tier  (trigger ingestion)
     +-- /api/v1/query          (query graph)
     +-- /api/v1/neighbors      (explore connections)
```

**Recommended**: Run ingestion locally to save API costs. Data goes directly to cloud Neo4j.

## API Endpoints (GCP Cloud Run)

After deployment, the following endpoints are available:

```bash
# Check service health
curl https://YOUR_CLOUD_RUN_URL/

# Get tier information
curl https://YOUR_CLOUD_RUN_URL/api/v1/pipeline/tiers

# Run pipeline by tier (background)
curl -X POST https://YOUR_CLOUD_RUN_URL/api/v1/pipeline/tier \
  -H "Content-Type: application/json" \
  -d '{"tier": 1, "limit": 10}'

# Query the graph
curl -X POST https://YOUR_CLOUD_RUN_URL/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"cypher": "MATCH (n:Entity) RETURN n.id, n.type LIMIT 10"}'
```

## Deployment

### Local Development
```bash
docker-compose up -d  # Starts Neo4j + API
```

### Google Cloud Run
```bash
./scripts/deploy_gcp.sh
```

See [Deployment Documentation](docs/deployment.md) for details.

## Architecture

```
Graph-Builder-Agent/
├─ apps/
│  ├─ cli/              # CLI commands
│  └─ api/              # FastAPI endpoints
├─ services/            # Shared business logic
│  ├─ graph_service.py
│  ├─ tier_manager.py   # Tier-based processing
│  ├─ article_cache.py  # Duplicate prevention + metadata
│  └─ article_storage.py # GCS raw article storage
├─ pipelines/
│  ├─ agentic_pipeline.py      # Main ingestion
│  └─ content_gen_pipeline.py  # Visualization
├─ data/seeds/          # Tier ticker lists
└─ configs/             # YAML configuration
```

See [Architecture Documentation](docs/architecture.md) for details.

## Backend Integration

The agent can create graphs in the Graphfolio Backend API from news articles. See [Backend Integration Documentation](docs/backend_integration.md) for details.

**Configuration**: Set `BACKEND_URL` and `BACKEND_API_TOKEN` in `.env` file (see `.env.example`).

```bash
# Create graph from news
ng backend create-graph-from-news \
  --source gdelt \
  --q "NVIDIA TSMC supply chain" \
  --name "Semiconductor Network" \
  --days 7

# Update existing graph with new news
ng backend update-graph-from-news \
  --graph-id <uuid> \
  --source gdelt \
  --q "NVIDIA earnings" \
  --days 3
```

## Core Interfaces

- **Connector**: `fetch(query: FetchQuery) -> Iterable[RawDoc]`
- **Extractor**: `extract(doc: RawDoc) -> tuple[list[Entity], list[Edge], list[Evidence]]`
- **GraphStore**: `upsert(entities, edges, evidence)` and `query(cypher: str)`
- **BackendGraphService**: Create/update graphs in Graphfolio Backend API

## License

MIT

