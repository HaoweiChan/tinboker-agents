import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from tqdm import tqdm

from extract.llm.structure_extractor import LLMStructureExtractor
from extract.pipeline import ExtractionPipeline
from graph.store.base import GraphStore
from graph.upsert import UpsertManager
from ingest.connectors.base import FetchQuery
from ingest.normalize import dedupe_docs
from services.article_cache import ArticleCache
from services.ingestion_service import IngestionService
from services.planning_service import PlanningService
from services.tier_manager import TierManager

logger = logging.getLogger(__name__)


class AgenticSearchPipeline:
    def __init__(
        self,
        graph_store: GraphStore,
        config: dict[str, Any] | None = None,
    ):
        self.config = config or {}
        self.graph_store = graph_store
        self.ingestion_service = IngestionService(config=config)

        # Initialize Services
        self.planning_service = PlanningService(config=self.config.get("visualization", {}))
        self.tier_manager = TierManager(config=self.config.get("cost_optimization", {}))
        self.article_cache = ArticleCache(
            graph_store,
            config=self.config.get("cost_optimization", {}).get("caching", {})
        )

        llm_extractor = LLMStructureExtractor(config=self.config.get("extraction", {}))
        self.extractor_pipeline = ExtractionPipeline([llm_extractor])

        self.upsert_manager = UpsertManager(graph_store)

    def run(
        self, 
        topic: str | None = None, 
        ticker: str | None = None, 
        generate_visual: bool = False
    ) -> dict[str, Any]:
        """
        Legacy run method. Wrapper around run_ingestion.
        Ignores generate_visual as visualization is now a separate stage.
        """
        if generate_visual:
            logger.warning("generate_visual flag is deprecated. Use ContentGenerationPipeline for visualization.")
        
        return self.run_ingestion(topic=topic, ticker=ticker)

    def run_ingestion(
        self,
        topic: str | None = None,
        ticker: str | None = None,
    ) -> dict[str, Any]:
        """
        Runs the ingestion pipeline for a single target (topic or ticker).
        Uses tiered processing and article caching for cost optimization.
        """
        target = ticker if ticker else topic
        if not target:
            raise ValueError("Either 'topic' or 'ticker' must be provided.")

        # Get tier settings for this ticker
        tier = self.tier_manager.get_tier(ticker) if ticker else 3
        tier_settings = self.tier_manager.get_tier_settings(ticker) if ticker else {}
        logger.info(f"Starting Agentic Ingestion for: {target} (Tier {tier})")

        stats = {
            "tier": tier,
            "queries_generated": [],
            "docs_found": 0,
            "docs_cached": 0,
            "docs_processed": 0,
            "entities_extracted": 0,
            "edges_extracted": 0,
            "errors": [],
        }

        try:
            # 1. Planning (Generate Queries) - Use LLM for Tier 1, templates for others
            if ticker:
                planning_mode = tier_settings.get("planning", "template")
                if planning_mode == "llm":
                    queries = self.planning_service.generate_research_questions(ticker)
                    logger.info(f"LLM-generated queries for {ticker}: {queries}")
                else:
                    queries = self.tier_manager.get_template_queries(ticker)
                    logger.info(f"Template queries for {ticker}: {queries}")

                # Limit queries based on tier
                max_queries = tier_settings.get("queries_per_ticker", 3)
                queries = queries[:max_queries]
            else:
                queries = [topic]

            stats["queries_generated"] = queries
            all_docs = []

            # 2. Search (Ingestion) - Loop through queries
            docs_per_query = tier_settings.get("docs_per_query", 3)
            for q_str in queries:
                try:
                    docs = self.ingestion_service.ingest(
                        source="tavily",
                        query=q_str,
                        limit=docs_per_query
                    )
                    all_docs.extend(docs)
                except Exception as e:
                    logger.error(f"Search failed for query '{q_str}': {e}")
                    stats["errors"].append(f"Search error: {e}")

            unique_docs = dedupe_docs(all_docs)
            stats["docs_found"] = len(unique_docs)

            # 3. Filter out cached/recently processed articles
            docs_to_process = []
            for doc in unique_docs:
                url_str = str(doc.url)
                if self.article_cache.is_recently_processed(url_str):
                    logger.debug(f"Skipping cached article: {url_str}")
                    stats["docs_cached"] += 1
                else:
                    docs_to_process.append(doc)

            logger.info(f"Found {len(unique_docs)} docs, {stats['docs_cached']} cached, {len(docs_to_process)} to process")

            # 3.5. Save raw articles to Neo4j BEFORE extraction
            for doc in docs_to_process:
                self.article_cache.save_raw_article(doc, ticker=ticker)
            logger.info(f"Saved {len(docs_to_process)} raw articles to cache")

            all_entities = []
            all_edges = []
            all_evidence = []

            # 4. Extraction (Reasoning)
            doc_iter = tqdm(docs_to_process, desc=f"  Extracting [{target}]", unit="doc", leave=False)
            for doc in doc_iter:
                url_str = str(doc.url)
                try:
                    entities, edges, evidence = self.extractor_pipeline.extract(doc)
                    all_entities.extend(entities)
                    all_edges.extend(edges)
                    all_evidence.extend(evidence)

                    # Mark article extraction as completed
                    self.article_cache.mark_extraction_completed(
                        url=url_str,
                        entities_count=len(entities),
                        edges_count=len(edges),
                    )
                    stats["docs_processed"] += 1
                    doc_iter.set_postfix(entities=len(all_entities), edges=len(all_edges))

                    # Rate Limit Handling
                    api_tier = self.config.get("api_tier", "free").lower()
                    if api_tier == "free":
                        time.sleep(10)
                    elif api_tier.startswith("tier_") or api_tier == "paid":
                        time.sleep(0.5)
                    else:
                        time.sleep(2.0)

                except Exception as e:
                    logger.error(f"Extraction error for {doc.url}: {e}")
                    self.article_cache.mark_extraction_failed(url_str, str(e))
                    stats["errors"].append(str(e))

            stats["entities_extracted"] = len(all_entities)
            stats["edges_extracted"] = len(all_edges)

            # 5. Storage (Knowledge Graph)
            if all_entities:
                self.upsert_manager.upsert_with_provenance(
                    all_entities,
                    all_edges,
                    all_evidence,
                    extractor="llm_agent",
                    timestamp=datetime.utcnow(),
                )
                logger.info("Graph data upserted successfully.")

            # 6. Update ticker processed time
            if ticker:
                self.article_cache.update_ticker_processed_time(ticker)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            stats["errors"].append(str(e))

        return stats

    def run_batch_ingestion(self, tickers: list[str], show_progress: bool = True) -> dict[str, Any]:
        """
        Runs ingestion for a list of tickers with tiered processing.
        """
        # Categorize tickers by tier for logging
        tiers = self.tier_manager.categorize_tickers(tickers)
        logger.info(
            f"Batch ingestion: {len(tickers)} tickers "
            f"(T1: {len(tiers[1])}, T2: {len(tiers[2])}, T3: {len(tiers[3])})"
        )

        batch_stats = {
            "processed": 0,
            "failed": 0,
            "cached": 0,
            "tier_breakdown": {1: 0, 2: 0, 3: 0},
            "details": []
        }

        # Use tqdm for progress bar
        ticker_iter = tqdm(tickers, desc="Ingesting tickers", unit="ticker") if show_progress else tickers

        for ticker in ticker_iter:
            try:
                if show_progress:
                    ticker_iter.set_postfix(ticker=ticker, processed=batch_stats["processed"], failed=batch_stats["failed"])

                stats = self.run_ingestion(ticker=ticker)
                batch_stats["processed"] += 1
                batch_stats["cached"] += stats.get("docs_cached", 0)
                batch_stats["tier_breakdown"][stats.get("tier", 3)] += 1
                batch_stats["details"].append({
                    "ticker": ticker,
                    "status": "success",
                    "tier": stats.get("tier"),
                    "docs_found": stats["docs_found"],
                    "docs_cached": stats.get("docs_cached", 0),
                    "docs_processed": stats.get("docs_processed", 0),
                    "entities": stats["entities_extracted"]
                })
            except Exception as e:
                logger.error(f"Failed to ingest ticker {ticker}: {e}")
                batch_stats["failed"] += 1
                batch_stats["details"].append({
                    "ticker": ticker,
                    "status": "failed",
                    "error": str(e)
                })

        # Add cache stats
        batch_stats["cache_stats"] = self.article_cache.get_cache_stats()

        return batch_stats
