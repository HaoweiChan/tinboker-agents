# tinboker-agents — Development Guide

## Purpose & scope

`tinboker-agents` is the **content / infrastructure backend** for **TinBoker「聽播客」** —
a financial-podcast-summary product. It does three things:

1. **Ingest** — pull podcast episodes (Spotify RSS) and financial news (Tavily).
2. **Derive structured content** — transcribe, summarize, extract tickers + sentiment, build
   the entity / topic / supply-chain knowledge graph, generate slides + infographics.
3. **Serve it** — expose that content (and content-derived aggregates) over HTTP
   (`/api/podcast/*`, `/api/wiki/*` on the podcast service, port 8003) and a Postgres store, so
   the **TinBoker webui** can render it.

**The TinBoker webui (the React/Traditional-Chinese site) lives in a SEPARATE "platform" repo —
not here.** Do not build UI in this repo. User accounts, follows, saved episodes, comments,
notification preferences, and live market quotes (prices / `change` %) are the platform repo's
concern, not ours. When a frontend mockup is referenced, treat it as a spec for the data
contracts this repo must expose, and build/extend API endpoints — never React components.
Keep this repo functional/infra-only and content-agnostic.

## Repo overview

This monorepo uses **uv workspaces** to manage three Python packages:
- `services/podcast/` — podcast processing pipeline + the HTTP API (`/api/podcast`, `/api/wiki`)
- `services/knowledge_graph/` — news ingestion + entity/relation extraction + graph + infographics
- `libs/shared/` — shared utilities (secrets, GCS, config, `wiki_builder`)

**Wiki content lives in a Postgres database on the VPS, not in this repo.** The `wiki_builder`
library (`libs/shared`) and the `/api/wiki` routes on the podcast service are content-agnostic
infra — see [docs/wiki-schema.md](docs/wiki-schema.md). A `wiki/` dir may exist locally as a
one-time migration source; it is gitignored and never committed.

## Module map

| Path | Purpose | Entry point | Key files |
|------|---------|-------------|-----------|
| [services/podcast/](services/podcast/) | Download → transcribe → summarize → Firestore; serves `/api/wiki` | [main.py](services/podcast/main.py) | [podcasts_to_download.json](services/podcast/podcasts_to_download.json) |
| [services/knowledge_graph/](services/knowledge_graph/) | News → entity extraction → graph + SVG | [apps/cli/main.py](services/knowledge_graph/apps/cli/main.py) | [pipelines/](services/knowledge_graph/pipelines/) |
| [libs/shared/](libs/shared/) | Secrets, GCS, config, wiki_builder (Postgres-backed) | N/A (library) | [src/shared/](libs/shared/src/shared/) |
| Wiki content | Postgres DB on the VPS (`WIKI_DATABASE_URL`) | `/api/wiki` (podcast service) | [docs/wiki-schema.md](docs/wiki-schema.md) |

## Decision tree — which module to touch?

**Adding a new podcast source or tweaking download:**
- Modify [services/podcast/podcasts_to_download.json](services/podcast/podcasts_to_download.json)

**Tweaking summary/extraction prompts:**
- Content prompts: [services/podcast/src/podcast/content_builder/prompts/](services/podcast/src/podcast/content_builder/prompts/)
- KG prompts: [services/knowledge_graph/extract/llm/](services/knowledge_graph/extract/llm/)

**Adding entity extraction rules:**
- [services/knowledge_graph/extract/rules/](services/knowledge_graph/extract/rules/)
- [services/knowledge_graph/extract/llm/](services/knowledge_graph/extract/llm/)

**Working on the wiki (content store):**
- Schema + API: [docs/wiki-schema.md](docs/wiki-schema.md)
- Library: [libs/shared/src/shared/wiki_builder/](libs/shared/src/shared/wiki_builder/) (`WikiRepository`, `ingest_episode`)
- HTTP routes: [services/podcast/src/routers/wiki.py](services/podcast/src/routers/wiki.py)
- Keep this layer content-agnostic — content metadata is opaque JSONB `frontmatter`

**Deploying to production:**
- See [docs/MIGRATION.md](docs/MIGRATION.md)
- podcast/ runs on Netcup VPS via systemd
- knowledge_graph/ runs on Google Cloud Run

## Conventions

**Dependencies:**
- Managed via uv workspaces; root `pyproject.toml` defines members
- Each service has its own `pyproject.toml`
- Shared library is a workspace dependency (`tinboker-shared`)
- Run `uv sync` from repo root to install all deps

**Testing:**
- Add tests in each module's `tests/` directory
- Run `pytest` from within the module directory, or use `uv run`
- Use mocks for external APIs (Spotify, Tavily, Gemini, Firestore, GCS)

**Commits:**
- Keep module changes atomic; PR per feature or fix
- No generated artifacts in commits (infographics, cache, logs)

**Code organization:**
- Podcast pipeline: `services/podcast/src/podcast/` — cli, orchestrator, firestore_reprocessor
- Podcast internals: `services/podcast/src/pipeline/`, `src/service/`, `src/summarize/`
- Content builder: `services/podcast/src/podcast/content_builder/` — LangGraph pipeline
- Knowledge graph: `services/knowledge_graph/` — apps/, pipelines/, services/, extract/, graph/
- Shared: `libs/shared/src/shared/` — secrets, gcs, config, wiki_builder

## Don't

- **Do not build UI here.** The TinBoker webui is a separate platform repo. This repo serves data, not React.
- **Do not run `pip install` from repo root.** Use `uv sync` instead.
- **Do not put generated artifacts under git.** Infographics, cached articles, logs go in `.gitignore`.
- **Do not commit wiki content.** The wiki lives in Postgres on the VPS; `wiki_builder` is infra only.
- **Do not own users/follows/comments/quotes.** Those belong to the platform repo; here, just expose stable IDs (episode/entity/topic slug, show name).
- **Do not bypass `secrets.bootstrap()`.** Always call it before reading env vars.

## Pipelines at a glance

### Podcast pipeline
```
Spotify RSS → services/podcast/download → transcribe → summarize
  → content_builder.run_pipeline() → markdown + slides
  → wiki_builder.ingest_episode() → Postgres (via WikiRepository)
  → Upload MP3, transcript, summary → GCS + Firestore
```

### Knowledge-graph pipeline
```
Tavily news → services/knowledge_graph/agentic_pipeline → Gemini extraction
  → extract/llm or /rules → graph_service.upsert()
  → WikiStore (JSON: wiki-graph/kg_store.json)   [TODO: push entities to /api/wiki]
  → Generate SVG infographics → GCS
```

## Related docs

- **[README.md](README.md)** — repo overview, architecture, quickstart
- **[AGENTS.md](AGENTS.md)** — short purpose statement (cross-tool agents entry point)
- **[docs/wiki-schema.md](docs/wiki-schema.md)** — wiki Postgres schema + `/api/wiki` API
- **[docs/content-api-roadmap.md](docs/content-api-roadmap.md)** — what the TinBoker webui needs from this backend, and the plan to deliver it
- **[docs/MIGRATION.md](docs/MIGRATION.md)** — production deployment runbook
- **[docs/content/](docs/content/)** — content/feature notes; **[docs/legacy/](docs/legacy/)** — archived Dify configs
