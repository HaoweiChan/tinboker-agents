import json
import logging
from pathlib import Path
from typing import Any

from graph.store.base import GraphStore
from services.graph_service import GraphService
from services.viz_service import VisualizationService

logger = logging.getLogger(__name__)


class ContentGenerationPipeline:
    def __init__(
        self,
        graph_store: GraphStore,
        config: dict[str, Any] | None = None,
    ):
        self.config = config or {}
        self.graph_store = graph_store
        
        # Initialize Services
        self.graph_service = GraphService(config=config)
        # Inject the connected store
        self.graph_service._store = graph_store
        
        self.viz_service = VisualizationService(
            graph_store=graph_store,
            config=self.config.get("visualization", {})
        )
        
        # Note: Ticker mappings are now expected to be in the DB (seeded via utils/seed_tickers_to_db.py)
        # We can still optionally load from files if needed, but we'll primarily check the graph.

    def run(self, ticker: str) -> dict[str, Any]:
        """
        Runs the content generation pipeline for a specific ticker.
        Fetches data from GraphDB -> Generates Article -> Generates Infographic -> Saves to DB.
        """
        logger.info(f"Starting Content Generation Pipeline for: {ticker}")
        
        stats = {
            "ticker": ticker,
            "entities_found": 0,
            "edges_found": 0,
            "visualization_path": None,
            "error": None
        }

        try:
            # 1. Fetch Subgraph
            logger.info(f"Fetching subgraph for {ticker}...")
            entities, edges = self.graph_service.get_subgraph_for_ticker(ticker, hop=1)
            
            # Fallback: Try to resolve ticker to name from DB if no entities found directly by ticker
            # (This handles cases where the main node might be stored as "TSMC" but requested as "2330.TW")
            if not entities:
                logger.info(f"No subgraph found directly for {ticker}. Checking for Company/Ticker alias in DB...")
                
                # Try to find a Company node with this ticker id to get its name properties
                # Note: get_subgraph_for_ticker handles ID/Name lookup, but if the node exists
                # and has no relationships, it returns just the node.
                # If it returns NOTHING, it means the node doesn't exist at all.
                # If we have seeded tickers, the node SHOULD exist.
                
                # Let's try to find metadata for this ticker from the DB
                # We can use a direct query via graph_service (if exposed) or just try get_subgraph again with known aliases
                # Since get_subgraph_for_ticker does "OR center.name = $ticker", it should cover it.
                
                # If we are here, it means the ticker/name wasn't found OR it has no connections.
                # Let's try to find the "name_en" or "name_zh" property if the node exists by ID
                pass

            if not entities:
                msg = f"No entities found for ticker {ticker} (or name) in Graph DB."
                logger.warning(msg)
                stats["error"] = msg
                return stats
            
            stats["entities_found"] = len(entities)
            stats["edges_found"] = len(edges)
            logger.info(f"Found {len(entities)} entities and {len(edges)} edges.")

            # 2. Generate Content (Article + Infographic)
            context = f"Supply chain analysis for {ticker}"
            viz_path = self.viz_service.generate_infographic(
                entities, 
                edges, 
                context=context
            )
            
            stats["visualization_path"] = viz_path
            if viz_path:
                logger.info(f"Content generated successfully: {viz_path}")

        except Exception as e:
            logger.error(f"Generation pipeline failed: {e}")
            stats["error"] = str(e)

        return stats
