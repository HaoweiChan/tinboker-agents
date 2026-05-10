# Cost Optimization Strategy

This document outlines strategies to reduce operational costs when running the agent at scale (thousands of US + TW stocks).

## Quick Start

```bash
# Run Tier 1 (50 stocks, full processing)
python -m apps.cli.main ingest-batch --tier 1

# Run with limit for testing
python -m apps.cli.main ingest-batch --tier 1 --limit 5

# Run Tier 2 (365 stocks, template queries)
python -m apps.cli.main ingest-batch --tier 2
```

## Current Cost Model

| Component | API/Model | Cost Per Ticker | Notes |
|-----------|-----------|-----------------|-------|
| Planning | Gemini 2.5 Pro | ~$0.01-0.05 | 1 LLM call to generate queries |
| Search | Tavily API | ~$0.02-0.10 | 3-5 queries × credits per search |
| Extraction | Gemini 2.5 Flash | ~$0.01-0.05 | 15-25 docs × tokens |
| **Total** | | **~$0.05-0.20** | Per ticker, per run |

For 3,000 stocks: **$150-600 per full run**

## Implemented: Tiered Processing

Stocks are automatically categorized into 3 tiers via `TierManager`:

| Tier | Count | Source | Processing |
|------|-------|--------|------------|
| 1 | 50 | `data/seeds/tier_1_tickers.txt` | Full LLM planning |
| 2 | 365 | `data/seeds/tier_2_tickers.txt` | Template queries |
| 3 | 11,000+ | All remaining tickers | Minimal processing |

### Tier Settings (configs/dev.yaml)

```yaml
cost_optimization:
  enabled: true
  tiers:
    tier_1_file: "data/seeds/tier_1_tickers.txt"
    tier_2_file: "data/seeds/tier_2_tickers.txt"
  tier_settings:
    tier_1:
      planning: "llm"
      queries_per_ticker: 5
      docs_per_query: 5
    tier_2:
      planning: "template"
      queries_per_ticker: 2
      docs_per_query: 3
    tier_3:
      planning: "template"
      queries_per_ticker: 1
      docs_per_query: 2
```

### Template Queries (Skip LLM Planning)

For Tier 2/3, use predefined templates instead of calling the LLM:

```python
TEMPLATE_QUERIES = {
    "default": [
        "{ticker} supply chain news {year}",
        "{ticker} financial guidance",
    ],
    "manufacturing": [
        "{ticker} production disruption",
        "{ticker} supplier partnership",
    ],
    "tech": [
        "{ticker} chip shortage",
        "{ticker} AI infrastructure",
    ],
}
```

**Savings**: Eliminates ~3,000 Pro LLM calls = ~$30-150

## Implemented: Article Caching

The `ArticleCache` service (`services/article_cache.py`) prevents duplicate processing:

### How It Works

1. **URL-Based Cache**: Before processing, checks if article URL was recently processed
2. **Content Hash**: Detects duplicate content across different URLs
3. **TTL**: Configurable cache expiry (default: 24 hours)

### Configuration

```yaml
cost_optimization:
  caching:
    enabled: true
    ttl_hours: 24
```

### Cache Statistics

The pipeline reports cache hits in output:
```json
{
  "docs_found": 20,
  "docs_cached": 5,
  "docs_processed": 15
}
```

**Savings**: 30-50% reduction in extraction calls for overlapping news

## Strategy 3: Incremental Updates

Only fetch news published since last run.

### Track Last Processed Time

```python
# Store in graph
graph.upsert_node(
    "TickerMeta",
    {"ticker": "TSLA", "last_processed_at": datetime.utcnow()}
)

# Query for next run
meta = graph.query("MATCH (t:TickerMeta {ticker: $ticker}) RETURN t.last_processed_at")
```

### Tavily Date Filter

Tavily supports date filtering (if available in API):

```python
payload = {
    "query": query,
    "search_depth": "advanced",
    "days": 7,  # Only last 7 days
    # Or use published_date filter if supported
}
```

**Savings**: 50-80% reduction after initial run

## Strategy 4: Cheaper Model Selection

### Planning Service

Switch from `gemini-2.5-pro` to `gemini-2.5-flash`:

```yaml
# configs/dev.yaml
visualization:
  planning_model: "gemini-2.5-flash"  # Was: gemini-2.5-pro
```

Flash is ~10x cheaper than Pro with similar results for simple query generation.

### Extraction

Already using Flash. Consider using an even cheaper model for Tier 3:

```yaml
extraction:
  tier_3_model: "gemini-1.5-flash-8b"  # Cheapest option
```

## Strategy 5: Reduce API Calls Per Ticker

### Reduce Queries Per Ticker

```yaml
# configs/dev.yaml
connectors:
  tavily:
    max_results: 3  # Was: 5
```

### Reduce Docs Per Query

Limit to top 2-3 most relevant results.

## Strategy 6: Batch Processing by Sector

Process related stocks together to share news:

```python
sectors = {
    "EV": ["TSLA", "RIVN", "LCID", "NIO"],
    "Semiconductors": ["NVDA", "AMD", "INTC", "TSM"],
}

# Fetch once for sector keywords, distribute to all tickers
sector_news = fetch("EV supply chain disruptions 2024")
for ticker in sectors["EV"]:
    process_with_shared_news(ticker, sector_news)
```

**Savings**: 60-70% reduction in Tavily calls

## Recommended Implementation Priority

1. **Tiered Processing** - Biggest impact, define tiers first
2. **Template Queries** - Easy to implement, saves Pro LLM costs
3. **Incremental Updates** - Critical for recurring runs
4. **Article Caching** - Prevents duplicate extraction
5. **Model Downgrade** - Switch planning to Flash
6. **Sector Batching** - Advanced optimization

## Estimated Cost After Optimization

| Tier | Stocks | Cost/Run | Frequency | Monthly Cost |
|------|--------|----------|-----------|--------------|
| Tier 1 | 50 | $0.15/ea | Daily | ~$225 |
| Tier 2 | 450 | $0.05/ea | Every 2 days | ~$337 |
| Tier 3 | 2,500 | $0.02/ea | Weekly | ~$200 |
| **Total** | | | | **~$762/month** |

With incremental updates after first run: **~$300-400/month**

## Configuration Example

```yaml
# configs/prod.yaml
cost_optimization:
  enabled: true
  
  tiers:
    tier_1_file: "data/seeds/tier_1_tickers.txt"  # Top 50
    tier_2_file: "data/seeds/tier_2_tickers.txt"  # Top 500
    # Rest = Tier 3
    
  planning:
    tier_1: "llm"
    tier_2: "template"
    tier_3: "template"
    
  extraction:
    tier_1_model: "gemini-2.5-flash"
    tier_2_model: "gemini-2.5-flash"
    tier_3_model: "gemini-1.5-flash-8b"
    
  caching:
    enabled: true
    ttl_hours: 24
    
  incremental:
    enabled: true
    lookback_days: 7
```

## Recommended Workflow

### Local Development (Saves Costs)

Run ingestion locally - data goes directly to cloud Neo4j Aura:

```bash
# Set environment to use cloud database
source .env

# Run Tier 1 locally
python -m apps.cli.main ingest-batch --tier 1

# Data is now in cloud Neo4j, accessible via GCP API
curl https://YOUR_CLOUD_RUN_URL/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"cypher": "MATCH (n:Entity) RETURN count(n)"}'
```

### GCP Cloud Run (Production)

Trigger via API for automated/scheduled runs:

```bash
# Trigger Tier 1 ingestion
curl -X POST https://YOUR_CLOUD_RUN_URL/api/v1/pipeline/tier \
  -H "Content-Type: application/json" \
  -d '{"tier": 1}'
```

### GitHub Actions (Scheduled)

Configure `.github/workflows/scheduled-graph-update.yaml`:

```yaml
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:
    inputs:
      tier:
        description: 'Tier level (1, 2, or 3)'
        default: '1'
```

## Monitoring Costs

Track costs per run:

```python
# Log at end of pipeline
logger.info(f"Pipeline stats: {stats}")
# stats = {
#     "llm_calls": 150,
#     "tavily_calls": 45,
#     "estimated_cost": "$12.50"
# }
```

