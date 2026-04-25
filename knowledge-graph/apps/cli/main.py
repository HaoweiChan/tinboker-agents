import json
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.table import Table

from pipelines.agentic_pipeline import AgenticSearchPipeline
from pipelines.content_gen_pipeline import ContentGenerationPipeline
from services.extraction_service import ExtractionService
from services.graph_service import GraphService
from services.ingestion_service import IngestionService

app = typer.Typer()
console = Console()


def load_config(config_path: Path = Path("configs/dev.yaml")) -> dict:
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}


@app.command()
def fetch_tickers(
    region: Annotated[str, typer.Option("--region", "-r", help="Region to fetch (us, tw, all)")] = "all",
    output_dir: Annotated[str, typer.Option("--output-dir", "-o", help="Output directory")] = ".",
):
    """
    Fetch full ticker lists for US (SEC) and Taiwan (TWSE) markets.
    """
    from utils.fetch_tickers import fetch_us_tickers, fetch_tw_tickers
    
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    if region in ["us", "all"]:
        fetch_us_tickers(out / "tickers_us_full.txt")
    if region in ["tw", "all"]:
        fetch_tw_tickers(out / "tickers_tw_full.txt")
    
    console.print(f"[green]Ticker lists updated in {output_dir}[/green]")


@app.command()
def ingest_batch(
    tier: Annotated[int | None, typer.Option("--tier", help="Process all tickers in a tier (1, 2, or 3)")] = None,
    topics: Annotated[str | None, typer.Option("--topics", "-t", help="Comma-separated topics")] = None,
    tickers: Annotated[str | None, typer.Option("--tickers", "-k", help="Comma-separated tickers (e.g. TSLA,AAPL)")] = None,
    file: Annotated[str | None, typer.Option("--file", "-f", help="File containing list of tickers (one per line)")] = None,
    config: Annotated[str, typer.Option("--config", "-c", help="Config file path")] = "configs/dev.yaml",
    limit: Annotated[int | None, typer.Option("--limit", "-l", help="Limit number of tickers to process")] = None,
):
    """
    Run Batch Ingestion: Ingests data for multiple tickers/topics and saves to Graph DB.

    Examples:
        python -m apps.cli.main ingest-batch --tier 1
        python -m apps.cli.main ingest-batch --tier 1 --limit 5
        python -m apps.cli.main ingest-batch --tickers TSLA,AAPL
    """
    from services.tier_manager import TierManager

    config_data = load_config(Path(config))
    targets = []

    # Priority: --tier > --tickers > --topics > --file
    if tier is not None:
        if tier not in [1, 2, 3]:
            console.print("[red]Error: Tier must be 1, 2, or 3[/red]")
            raise typer.Exit(1)
        tier_manager = TierManager(config=config_data.get("cost_optimization", {}))
        targets = tier_manager.get_tickers_by_tier(tier)
        tier_settings = tier_manager.get_tier_settings(targets[0] if targets else "")
        console.print(f"[bold]Tier {tier} selected: {len(targets)} tickers[/bold]")
        console.print(f"Settings: {tier_settings}")
    elif tickers:
        targets.extend([t.strip() for t in tickers.split(",") if t.strip()])
    elif topics:
        targets.extend([t.strip() for t in topics.split(",") if t.strip()])
    elif file:
        path = Path(file)
        if path.exists():
            with open(path) as f:
                targets.extend([line.strip() for line in f if line.strip() and not line.startswith("#")])
        else:
            console.print(f"[red]File not found: {file}[/red]")
            raise typer.Exit(1)

    if not targets:
        console.print("[red]No targets provided. Use --tier, --tickers, --topics, or --file.[/red]")
        raise typer.Exit(1)

    # Apply limit if specified
    if limit and limit > 0:
        console.print(f"[yellow]Limiting to {limit} tickers[/yellow]")
        targets = targets[:limit]

    console.print(f"[bold]Starting Batch Ingestion for {len(targets)} targets...[/bold]")
    
    # Initialize Graph Service
    graph_service = GraphService(config_data)
    store = graph_service.get_store()
    
    try:
        pipeline = AgenticSearchPipeline(graph_store=store, config=config_data)
        stats = pipeline.run_batch_ingestion(tickers=targets)
        
        console.print("\n[bold]Batch Ingestion Completed[/bold]")
        console.print(f"Processed: {stats['processed']}, Failed: {stats['failed']}")
        
        if stats['failed'] > 0:
            console.print("[red]Failures occurred:[/red]")
            for item in stats['details']:
                if item['status'] == 'failed':
                    console.print(f"- {item['ticker']}: {item.get('error')}")
            
    except Exception as e:
        console.print(f"[red]Batch Ingestion failed: {e}[/red]")
    finally:
        graph_service.close()


@app.command()
def generate_content(
    ticker: Annotated[str, typer.Option("--ticker", "-k", help="Ticker to generate content for")],
    config: Annotated[str, typer.Option("--config", "-c", help="Config file path")] = "configs/dev.yaml",
):
    """
    Generate Content (Article + Infographic) for a specific ticker using data from Graph DB.
    """
    console.print(f"[bold]Generating content for: {ticker}[/bold]")
    config_data = load_config(Path(config))
    
    graph_service = GraphService(config_data)
    store = graph_service.get_store()
    
    try:
        pipeline = ContentGenerationPipeline(graph_store=store, config=config_data)
        stats = pipeline.run(ticker=ticker)
        
        if stats.get("error"):
            console.print(f"[red]Generation failed: {stats['error']}[/red]")
        else:
            console.print("[green]Content generated successfully![/green]")
            console.print(f"Entities used: {stats['entities_found']}")
            console.print(f"Edges used: {stats['edges_found']}")
            if stats.get("visualization_path"):
                console.print(f"Infographic: {stats['visualization_path']}")

    except Exception as e:
        console.print(f"[red]Command failed: {e}[/red]")
    finally:
        graph_service.close()


@app.command()
def save_blog_post(
    entity_id: Annotated[str, typer.Option("--entity", "-e", help="Entity ID (e.g., google)")],
    perspective: Annotated[str, typer.Option("--perspective", "-p", help="Article perspective (e.g., supply_chain)")],
    chart_type: Annotated[str, typer.Option("--chart-type", "-ct", help="Chart type used (e.g., N_TIER_NODE_MAP)")],
    title: Annotated[str, typer.Option("--title", "-t", help="Article title in Chinese")],
    svg_path: Annotated[str, typer.Option("--svg", help="Path to SVG file")],
    article_path: Annotated[str, typer.Option("--article", help="Path to Markdown article")],
    ticker: Annotated[str, typer.Option("--ticker", "-k", help="Stock ticker")] = "",
    config: Annotated[str, typer.Option("--config", "-c", help="Config file path")] = "configs/dev.yaml",
):
    """
    Save a blog post (SVG + Article) to GCS and track in Neo4j.
    """
    from services.blog_post_storage import BlogPostStorage

    config_data = load_config(Path(config))
    graph_service = GraphService(config_data)
    store = graph_service.get_store()

    try:
        gcs_config = config_data.get("cost_optimization", {}).get("caching", {}).get("gcs", {})
        storage = BlogPostStorage(gcs_config=gcs_config, neo4j_store=store)

        result = storage.save_blog_post(
            entity_id=entity_id,
            entity_name=entity_id.title(),
            ticker=ticker or entity_id.upper(),
            perspective=perspective,
            chart_type=chart_type,
            title=title,
            svg_path=svg_path,
            article_path=article_path,
        )

        console.print(f"[green]Blog post saved![/green]")
        console.print(f"  ID: {result['blog_id']}")
        console.print(f"  SVG: {result.get('svg_gcs_path', 'N/A')}")
        console.print(f"  Article: {result.get('article_gcs_path', 'N/A')}")

    except Exception as e:
        console.print(f"[red]Failed to save blog post: {e}[/red]")
    finally:
        graph_service.close()


@app.command()
def list_blog_posts(
    entity_id: Annotated[str | None, typer.Option("--entity", "-e", help="Filter by entity ID")] = None,
    config: Annotated[str, typer.Option("--config", "-c", help="Config file path")] = "configs/dev.yaml",
):
    """
    List all saved blog posts.
    """
    from services.blog_post_storage import BlogPostStorage

    config_data = load_config(Path(config))
    graph_service = GraphService(config_data)
    store = graph_service.get_store()

    try:
        gcs_config = config_data.get("cost_optimization", {}).get("caching", {}).get("gcs", {})
        storage = BlogPostStorage(gcs_config=gcs_config, neo4j_store=store)

        if entity_id:
            posts = storage.get_blog_posts_for_entity(entity_id)
        else:
            posts = storage.get_all_blog_posts()

        if not posts:
            console.print("[yellow]No blog posts found.[/yellow]")
            return

        table = Table(title="Blog Posts")
        table.add_column("ID", style="cyan")
        table.add_column("Entity", style="green")
        table.add_column("Perspective", style="blue")
        table.add_column("Chart Type", style="magenta")
        table.add_column("Title", style="white")

        for post in posts:
            table.add_row(
                post.get("id", ""),
                post.get("entity_id", ""),
                post.get("perspective", ""),
                post.get("chart_type", ""),
                (post.get("title", "")[:30] + "...") if len(post.get("title", "")) > 30 else post.get("title", ""),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Failed to list blog posts: {e}[/red]")
    finally:
        graph_service.close()


@app.command()
def search_agent(
    topic: Annotated[str | None, typer.Option("--topic", "-t", help="Topic to search for")] = None,
    ticker: Annotated[str | None, typer.Option("--ticker", "-k", help="Ticker symbol to analyze (e.g. TSLA)")] = None,
    visualize: Annotated[bool, typer.Option("--visualize", "-v", help="Generate infographic")] = False,
    config: Annotated[str, typer.Option("--config", "-c", help="Config file path")] = "configs/dev.yaml",
):
    """
    Run the Agentic Search Pipeline: Search -> Extract -> Store -> (Visualize).
    Provide either --topic or --ticker.
    """
    if not topic and not ticker:
        console.print("[red]Error: You must provide either --topic or --ticker.[/red]")
        raise typer.Exit(code=1)

    target = ticker if ticker else topic
    console.print(f"[bold]Running Agentic Search for: {target}[/bold]")
    config_data = load_config(Path(config))
    
    # Initialize Graph Service to get the store
    graph_service = GraphService(config_data)
    store = graph_service.get_store()
    
    try:
        pipeline = AgenticSearchPipeline(graph_store=store, config=config_data)
        stats = pipeline.run(topic=topic, ticker=ticker, generate_visual=visualize)
        
        if stats.get("errors"):
            console.print(f"[red]Pipeline Completed with {len(stats['errors'])} Errors[/red]")
            for err in stats["errors"]:
                console.print(f"[red]- {err}[/red]")
        elif stats.get("docs_found", 0) == 0:
            console.print("[yellow]Pipeline Completed but No Documents Found[/yellow]")
            console.print("[yellow]Check your API keys or search queries.[/yellow]")
        else:
            console.print("[green]Pipeline Completed Successfully[/green]")
            
        console.print(json.dumps(stats, default=str, indent=2))
        
        if stats.get("visualization_url"):
            console.print(f"[bold cyan]Infographic generated:[/bold cyan] {stats['visualization_url']}")
            
    except Exception as e:
        console.print(f"[red]Pipeline failed: {e}[/red]")
    finally:
        graph_service.close()


@app.command()
def ingest(
    source: Annotated[str, typer.Option("--source", "-s", help="Data source (gdelt, newscatcher, rss)")] = "gdelt",
    q: Annotated[str, typer.Option("--q", help="Query string")] = "",
    days: Annotated[int, typer.Option("--days", "-d", help="Number of days to look back")] = 7,
    output_dir: Annotated[str | None, typer.Option("--output-dir", "-o", help="Output directory for raw docs")] = None,
    config: Annotated[str, typer.Option("--config", "-c", help="Config file path")] = "configs/dev.yaml",
):
    console.print(f"[bold]Ingesting from {source}[/bold]")
    config_data = load_config(Path(config))

    ingestion_service = IngestionService(config_data)
    docs = ingestion_service.ingest(source=source, query=q, days=days)

    console.print(f"[green]Fetched {len(docs)} documents[/green]")

    if output_dir:
        ingestion_service.save_docs(docs, Path(output_dir))
        console.print(f"[green]Saved {len(docs)} documents to {output_dir}[/green]")


@app.command()
def extract(
    pipeline: Annotated[str, typer.Option("--pipeline", "-p", help="Extraction pipeline (rules, openie, rules+openie)")] = "rules+openie",
    input_dir: Annotated[str | None, typer.Option("--input-dir", "-i", help="Input directory for raw docs")] = None,
    output_format: Annotated[str, typer.Option("--output-format", "-f", help="Output format (json, toon)")] = "json",
    config: Annotated[str, typer.Option("--config", "-c", help="Config file path")] = "configs/dev.yaml",
):
    console.print(f"[bold]Extracting with pipeline: {pipeline}[/bold]")
    config_data = load_config(Path(config))

    extraction_service = ExtractionService(config_data)

    if input_dir:
        docs = extraction_service.load_docs_from_dir(Path(input_dir))
        entities, edges, evidence = extraction_service.extract(docs, pipeline=pipeline)

        console.print(f"[green]Extracted {len(entities)} entities, {len(edges)} edges, {len(evidence)} evidence[/green]")

        output = extraction_service.format_output(entities, edges, evidence, output_format)
        if isinstance(output, str):
            console.print(output)
        else:
            console.print(json.dumps(output, default=str, indent=2))


@app.command()
def upsert(
    store: Annotated[str, typer.Option("--store", "-s", help="Graph store (neo4j, kuzu, memgraph)")] = "neo4j",
    batch_size: Annotated[int, typer.Option("--batch-size", "-b", help="Batch size")] = 100,
    config: Annotated[str, typer.Option("--config", "-c", help="Config file path")] = "configs/dev.yaml",
):
    console.print(f"[bold]Upserting to {store}[/bold]")
    config_data = load_config(Path(config))

    graph_service = GraphService(config_data)
    graph_service.get_store(store_type=store)
    console.print(f"[green]{store.capitalize()} schema initialized[/green]")


@app.command()
def query(
    cypher: Annotated[str, typer.Option("--cypher", "-c", help="Cypher query")] = "",
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (table, json, toon)")] = "table",
    config: Annotated[str, typer.Option("--config", help="Config file path")] = "configs/dev.yaml",
):
    console.print(f"[bold]Executing query[/bold]")
    config_data = load_config(Path(config))

    graph_service = GraphService(config_data)

    try:
        results = graph_service.query(cypher)

        if format == "table" and results:
            table = Table()
            for key in results[0].keys():
                table.add_column(key)
            for row in results:
                table.add_row(*[str(v) for v in row.values()])
            console.print(table)
        elif format == "json":
            console.print(json.dumps(results, default=str, indent=2))
        else:
            console.print(results)

    finally:
        graph_service.close()


@app.command()
def re_extract(
    status: Annotated[str, typer.Option("--status", "-s", help="Article status to process (pending, failed)")] = "failed",
    ticker: Annotated[str | None, typer.Option("--ticker", "-k", help="Filter by ticker")] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max articles to process")] = 100,
    config: Annotated[str, typer.Option("--config", "-c", help="Config file path")] = "configs/dev.yaml",
):
    """
    Re-run LLM extraction on cached articles (pending or failed).
    Raw articles are saved to Neo4j during ingestion, allowing re-extraction without re-fetching from Tavily.
    """
    from datetime import datetime
    from extract.llm.structure_extractor import LLMStructureExtractor
    from extract.pipeline import ExtractionPipeline
    from graph.upsert import UpsertManager
    from services.article_cache import ArticleCache

    config_data = load_config(Path(config))
    graph_service = GraphService(config_data)
    store = graph_service.get_store()

    try:
        article_cache = ArticleCache(store, config=config_data.get("cost_optimization", {}).get("caching", {}))

        # Get extraction stats first
        stats = article_cache.get_extraction_stats()
        console.print(f"[bold]Current article status:[/bold]")
        console.print(f"  Pending: {stats.get('pending', 0)}")
        console.print(f"  Completed: {stats.get('completed', 0)}")
        console.print(f"  Failed: {stats.get('failed', 0)}")

        # Get articles to process
        if status == "pending":
            articles = article_cache.get_pending_articles(ticker=ticker, limit=limit)
        elif status == "failed":
            articles = article_cache.get_failed_articles(ticker=ticker, limit=limit)
        else:
            console.print(f"[red]Invalid status: {status}. Use 'pending' or 'failed'.[/red]")
            raise typer.Exit(1)

        if not articles:
            console.print(f"[yellow]No {status} articles found to process.[/yellow]")
            return

        console.print(f"\n[bold]Re-extracting {len(articles)} {status} articles...[/bold]")

        # Initialize extractor
        llm_extractor = LLMStructureExtractor(config=config_data.get("extraction", {}))
        extractor_pipeline = ExtractionPipeline([llm_extractor])
        upsert_manager = UpsertManager(store)

        processed = 0
        failed = 0
        all_entities = []
        all_edges = []
        all_evidence = []

        for article in articles:
            url = article.get("url", "unknown")
            try:
                doc = article_cache.article_to_rawdoc(article)
                entities, edges, evidence = extractor_pipeline.extract(doc)
                all_entities.extend(entities)
                all_edges.extend(edges)
                all_evidence.extend(evidence)

                article_cache.mark_extraction_completed(
                    url=url,
                    entities_count=len(entities),
                    edges_count=len(edges),
                )
                processed += 1
                console.print(f"  [green]OK[/green] {url[:60]}... ({len(entities)} entities, {len(edges)} edges)")

            except Exception as e:
                article_cache.mark_extraction_failed(url, str(e))
                failed += 1
                console.print(f"  [red]FAIL[/red] {url[:60]}... ({str(e)[:50]})")

        # Upsert all extracted data
        if all_entities:
            upsert_manager.upsert_with_provenance(
                all_entities,
                all_edges,
                all_evidence,
                extractor="re_extract",
                timestamp=datetime.utcnow(),
            )
            console.print(f"\n[green]Upserted {len(all_entities)} entities, {len(all_edges)} edges[/green]")

        console.print(f"\n[bold]Re-extraction completed:[/bold] {processed} success, {failed} failed")

    except Exception as e:
        console.print(f"[red]Re-extraction failed: {e}[/red]")
    finally:
        graph_service.close()


@app.command()
def article_stats(
    config: Annotated[str, typer.Option("--config", "-c", help="Config file path")] = "configs/dev.yaml",
):
    """
    Show article cache statistics (pending/completed/failed counts).
    """
    from services.article_cache import ArticleCache

    config_data = load_config(Path(config))
    graph_service = GraphService(config_data)
    store = graph_service.get_store()

    try:
        article_cache = ArticleCache(store, config=config_data.get("cost_optimization", {}).get("caching", {}))
        stats = article_cache.get_extraction_stats()
        cache_stats = article_cache.get_cache_stats()

        console.print("[bold]Article Cache Statistics[/bold]")
        table = Table()
        table.add_column("Status")
        table.add_column("Count", justify="right")
        table.add_row("Pending", str(stats.get("pending", 0)))
        table.add_row("Completed", str(stats.get("completed", 0)))
        table.add_row("Failed", str(stats.get("failed", 0)))
        table.add_row("---", "---")
        table.add_row("Total", str(cache_stats.get("total_articles", 0)))
        table.add_row("Recent (within TTL)", str(cache_stats.get("recent_articles", 0)))
        console.print(table)

    except Exception as e:
        console.print(f"[red]Failed to get stats: {e}[/red]")
    finally:
        graph_service.close()


@app.command()
def migrate_to_gcs(
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max articles to migrate")] = 500,
    config: Annotated[str, typer.Option("--config", "-c", help="Config file path")] = "configs/dev.yaml",
):
    """
    Migrate articles from Neo4j to GCS.
    Moves raw text from Neo4j to GCS bucket, keeping only metadata in Neo4j.
    """
    from services.article_storage import GCSArticleStorage
    from ingest.models import RawDoc

    config_data = load_config(Path(config))
    graph_service = GraphService(config_data)
    store = graph_service.get_store()

    try:
        # Initialize GCS storage
        gcs_config = config_data.get("cost_optimization", {}).get("caching", {}).get("gcs", {})
        if not gcs_config.get("enabled", False):
            console.print("[red]GCS is not enabled in config. Enable it first in configs/dev.yaml[/red]")
            raise typer.Exit(1)

        gcs_storage = GCSArticleStorage(config=gcs_config)
        console.print(f"[bold]Migrating articles to GCS bucket: {gcs_config.get('bucket_name')}[/bold]")

        # Find articles with text in Neo4j but no gcs_path
        result = store.query(
            """
            MATCH (a:Article)
            WHERE a.text IS NOT NULL AND a.gcs_path IS NULL
            RETURN a.url as url, a.title as title, a.text as text, 
                   a.published_at as published_at, a.ticker as ticker
            LIMIT $limit
            """,
            {"limit": limit}
        )

        if not result:
            console.print("[green]No articles to migrate. All articles already in GCS or no text stored.[/green]")
            return

        console.print(f"Found {len(result)} articles to migrate...")
        migrated = 0
        failed = 0

        for row in result:
            url = row["url"]
            try:
                # Create RawDoc
                published_at = None
                if row.get("published_at"):
                    from datetime import datetime
                    try:
                        published_at = datetime.fromisoformat(row["published_at"])
                    except Exception:
                        pass

                doc = RawDoc(
                    url=url,
                    title=row.get("title", ""),
                    text=row.get("text", ""),
                    published_at=published_at,
                    source="neo4j_migration",
                )

                # Save to GCS
                gcs_path = gcs_storage.save_article(doc, ticker=row.get("ticker"))

                # Update Neo4j: add gcs_path, remove text
                store.query(
                    """
                    MATCH (a:Article {url: $url})
                    SET a.gcs_path = $gcs_path
                    REMOVE a.text
                    """,
                    {"url": url, "gcs_path": gcs_path}
                )
                migrated += 1
                if migrated % 50 == 0:
                    console.print(f"  Migrated {migrated} articles...")

            except Exception as e:
                console.print(f"  [red]Failed to migrate {url[:50]}...: {e}[/red]")
                failed += 1

        console.print(f"\n[bold]Migration complete:[/bold] {migrated} migrated, {failed} failed")

    except Exception as e:
        console.print(f"[red]Migration failed: {e}[/red]")
    finally:
        graph_service.close()


from apps.cli.backend_commands import app as backend_app
from apps.cli.proposal_commands import app as proposal_app

app.add_typer(backend_app, name="backend", help="Backend API integration commands")
app.add_typer(proposal_app, name="proposal", help="Graph proposal commands (for review workflow)")

if __name__ == "__main__":
    app()

