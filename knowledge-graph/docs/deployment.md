# Deployment Architecture & Low-Cost Strategy

This document describes how to deploy the Graph-Builder-Agent with a focus on minimizing costs while maintaining functionality.

## Recommended Low-Cost Stack

For a cost-effective deployment (often **<$5/month** or Free for low volume), we recommend:

1.  **Compute**: **Google Cloud Run** (Serverless) or **Railway/Render** (PaaS).
    *   *Why*: Pay only for what you use (Cloud Run) or low fixed monthly caps (Railway).
    *   *Cost*: Free tier often covers low-volume scheduled runs.

2.  **Database**: **Neo4j Aura Free Tier** OR **KuzuDB (Embedded)**.
    *   *Neo4j Aura Free*: Managed Service. Always free.
        *   *Limits*: 1 Instance, 200k Nodes, 400k Relationships. Pauses after 3 days inactivity (auto-resume available).
        *   *Best for*: Persistent, accessible graph database without server maintenance.
    *   *KuzuDB*: Embedded in Python app.
        *   *Limits*: Disk space of the host.
        *   *Best for*: Zero cost, high performance local analysis. Requires a persistent volume if using Serverless.

3.  **LLM**: **Google Gemini 1.5 Flash / Pro**.
    *   *Why*: Large free tier (Tier 1). Low cost per token if paid.
    *   *Alternative*: OpenAI GPT-4o-mini (very cheap).

## Docker Deployment

We provide a standard `Dockerfile` and `docker-compose.yaml` for containerized deployment.

### 1. Build and Run Locally (with Neo4j)

```bash
docker-compose up --build -d
```

This starts:
-   **Graph Agent**: The Python application.
-   **Neo4j**: Local Neo4j instance with APOC/GDS plugins.

### 2. Deploy to Google Cloud Run (Serverless)

1.  **Build Image**:
    ```bash
    gcloud builds submit --tag gcr.io/YOUR_PROJECT/graph-agent
    ```

2.  **Deploy**:
    ```bash
    gcloud run deploy graph-agent \
      --image gcr.io/YOUR_PROJECT/graph-agent \
      --platform managed \
      --region us-central1 \
      --set-env-vars "NEO4J_URI=bolt+s://<your-aura-uri>,NEO4J_USER=neo4j,NEO4J_PASSWORD=<password>"
    ```
    *Note: Use `bolt+s` for Aura.*

### 3. Deploy to a $5 VPS (DigitalOcean/Hetzner/Linode)

If you prefer a fixed-cost server:

1.  Provision a generic Ubuntu VPS (~$4-6/mo).
2.  Install Docker & Docker Compose.
3.  Clone repository.
4.  Run `docker-compose up -d`.

This gives you a full Neo4j instance + Agent running 24/7.

## Configuration for Low Cost

In `configs/dev.yaml`:

```yaml
graph_store:
  type: neo4j  # or 'kuzu' if using persistent disk
  neo4j:
    uri: "${NEO4J_URI}" # Use env var
    user: "${NEO4J_USER}"
    password: "${NEO4J_PASSWORD}"

api_tier: "free" # Enforces strict rate limits (e.g. 2-10 RPM for Gemini Free)
```

## Scheduled Runs

To minimize compute time, run the agent on a schedule rather than as a long-running service.

-   **Cloud Run Jobs**: Trigger via Cloud Scheduler (e.g., every 6 hours).
-   **GitHub Actions**: You can run the agent directly in a GitHub Action workflow (Free for public repos, limited minutes for private) if the job completes quickly (<6h).

### Example GitHub Action (Free Scheduler)

```yaml
name: Scheduled Graph Update
on:
  schedule:
    - cron: '0 */6 * * *' # Every 6 hours

jobs:
  update-graph:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: python -m apps.cli.main update-graph --ticker TSLA
        env:
          NEO4J_URI: ${{ secrets.NEO4J_URI }}
          NEO4J_USER: ${{ secrets.NEO4J_USER }}
          NEO4J_PASSWORD: ${{ secrets.NEO4J_PASSWORD }}
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
```
