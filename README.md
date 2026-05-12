# tinboker-agents

The **content / infrastructure backend** for **TinBoker「聽播客」** (a financial-podcast-summary
product): it ingests podcast episodes (Spotify) and financial news (Tavily), derives structured
content (transcripts, summaries, ticker sentiment, an entity/topic/supply-chain knowledge graph,
slides, infographics), and serves it over HTTP (`/api/podcast/*`, `/api/wiki/*` on port 8003) and
a Postgres store.

**The TinBoker webui (the React/Traditional-Chinese site) is built and run from a separate
"platform" repo — not here.** This repo contains no UI; it's functional/infra-only. Users,
follows, saved episodes, comments, and live market quotes are the platform repo's concern. Wiki
*content* lives in Postgres on the VPS, not in git (see [docs/wiki-schema.md](docs/wiki-schema.md)).
What the webui needs from this backend, and the plan to deliver it, is in
[docs/content-api-roadmap.md](docs/content-api-roadmap.md).

## Quickstart

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync all workspace dependencies
uv sync

# Run podcast pipeline
cd services/podcast && python main.py --config podcasts_to_download.json

# Run knowledge-graph pipeline
cd services/knowledge_graph && python -m apps.cli.main search-agent --ticker TSLA
```

## Repository Structure

```
tinboker-agents/
├── pyproject.toml                    # uv workspace root
├── README.md
├── CLAUDE.md                         # agent development guide
├── docs/
│   ├── MIGRATION.md                  # deployment runbook
│   ├── wiki-schema.md                # wiki Postgres schema + /api/wiki API
│   ├── content/                      # content/feature notes (was content/docs/)
│   └── legacy/dify_config/           # archived legacy Dify workflow configs
├── libs/
│   └── shared/                       # shared library (secrets, GCS, wiki_builder)
│       ├── pyproject.toml
│       ├── src/shared/
│       │   ├── secrets.py            # unified GSM + dotenv bootstrap
│       │   ├── gcs.py                # GCS client factory
│       │   ├── config.py             # YAML + env config loading
│       │   └── wiki_builder/         # WikiRepository (Postgres) + ingest + markdown views
│       └── tests/
├── services/
│   ├── podcast/                      # podcast download → transcribe → summarize → upload; serves /api/wiki
│   │   ├── pyproject.toml
│   │   ├── main.py                   # entry point
│   │   ├── app.py                    # FastAPI app (episode, podcast, wiki routers)
│   │   ├── podcasts_to_download.json
│   │   ├── src/
│   │   │   ├── podcast/
│   │   │   │   ├── cli.py            # argparse CLI
│   │   │   │   ├── orchestrator.py   # pipeline coordination
│   │   │   │   ├── firestore_reprocessor.py
│   │   │   │   ├── content_builder/  # LangGraph content pipeline
│   │   │   │   └── marp_service/     # Marp Flask converter
│   │   │   ├── pipeline/             # step-based episode processor (incl. wiki ingest step)
│   │   │   ├── routers/              # FastAPI routers — episode, podcast, wiki
│   │   │   ├── service/              # download, GCS, Firebase services
│   │   │   ├── summarize/            # summary generation
│   │   │   └── models/               # data models
│   │   └── tests/
│   └── knowledge_graph/              # news → entity extraction → graph
│       ├── pyproject.toml
│       ├── Dockerfile
│       ├── apps/cli/                 # typer CLI
│       ├── pipelines/                # agentic + content gen pipelines
│       ├── services/                 # graph, extraction, ingestion services
│       ├── extract/                  # rule-based + LLM extraction
│       ├── graph/                    # JSON-backed graph store (wiki-graph/kg_store.json)
│       ├── mcp/                      # MCP server tools
│       └── tests/
```

Wiki content (episodes / entities / topics / supply-chain pages) is **not** in this repo — it
lives in Postgres on the VPS, written via `shared.wiki_builder` and the `/api/wiki` routes.

## Architecture

### Data Flow

```
       ┌─────────────┐                 ┌─────────────┐
       │  Spotify RSS │                 │ Tavily News │
       └──────┬──────┘                  └──────┬──────┘
              │                                │
       ┌──────▼──────┐                  ┌──────▼──────────┐
       │   podcast/  │                  │ knowledge_graph/ │
       │ download →  │                  │  extract → graph │
       │ transcribe →│                  │  → visualize     │
       │ summarize → │                  └──────┬──────────┘
       │   upload    │                         │ kg_store.json (+ TODO: /api/wiki)
       └──────┬──────┘                         ▼
              │ ingest_episode()        ┌──────────────┐
              ▼                         │  GCS (SVGs)  │
   ┌─────────────────────┐              └──────────────┘
   │ Postgres on the VPS │  ◀── /api/wiki (read/write) ── future UI / external readers
   │  wiki_pages / links │
   └─────────────────────┘
```

### Shared Concerns

| Concern | Implementation |
|---------|---------------|
| Secrets | `libs/shared/secrets.py` — GSM + dotenv (`WIKI_DATABASE_URL` optional) |
| GCS | `libs/shared/gcs.py` — client factory |
| Wiki store | `libs/shared/wiki_builder/` — `WikiRepository` (Postgres) + `/api/wiki` routes |
| Config | `libs/shared/config.py` — YAML + env |

### Deployment Targets

| Service | Platform | Details |
|---------|----------|---------|
| podcast/ | Netcup VPS | systemd unit, port 8003; also runs Postgres for the wiki |
| knowledge_graph/ | Google Cloud Run | Docker, triggered by GH Actions |
| Wiki content | Postgres on the VPS | `WIKI_DATABASE_URL`; `scripts/wiki_migrate.sh` creates the schema |
| marp_service/ | Docker (co-deployed with podcast) | Flask, port 5004 |

## Development

Each workspace member has its own virtual environment managed by uv:

```bash
# Install deps for a specific service
uv sync --package tinboker-podcast

# Run tests for a service
uv run --package tinboker-podcast pytest

# Run tests for shared lib
uv run --package tinboker-shared pytest
```

## Related Docs

- [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md) — purpose, scope, and how to work in this repo
- [docs/content-api-roadmap.md](docs/content-api-roadmap.md) — what the TinBoker webui needs from this backend, and the delivery plan
- [docs/wiki-schema.md](docs/wiki-schema.md) — wiki Postgres schema + `/api/wiki` API
- [docs/MIGRATION.md](docs/MIGRATION.md) — production deployment runbook
