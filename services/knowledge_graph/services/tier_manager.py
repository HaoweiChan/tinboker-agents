"""
Tier Manager - Categorizes tickers into processing tiers for cost optimization.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default tier 1 tickers (highest market cap, most important)
DEFAULT_TIER_1 = [
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "BRK-B",
    "LLY", "WMT", "JPM", "V", "ORCL", "XOM", "JNJ", "MA", "NFLX",
    "COST", "BAC", "AMD", "HD", "UNH", "CAT", "GS", "QCOM",
    # Taiwan Top
    "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW",
    "2412.TW", "2881.TW", "2882.TW", "2891.TW", "1301.TW",
]

# Template queries for non-LLM planning
TEMPLATE_QUERIES = {
    "default": [
        "{ticker} supply chain news",
        "{ticker} production updates",
    ],
    "semiconductor": [
        "{ticker} chip production news",
        "{ticker} semiconductor supply chain",
    ],
    "ev": [
        "{ticker} EV battery supply chain",
        "{ticker} electric vehicle production",
    ],
    "finance": [
        "{ticker} financial outlook",
        "{ticker} market position",
    ],
}

# Sector mapping for template selection
SECTOR_KEYWORDS = {
    "semiconductor": ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "TSM", "ASML", "2330.TW", "2454.TW"],
    "ev": ["TSLA", "RIVN", "LCID", "NIO", "GM", "F", "2317.TW"],
    "finance": ["JPM", "BAC", "GS", "MS", "WFC", "C", "2881.TW", "2882.TW"],
}


class TierManager:
    """Manages ticker tiers and processing settings."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._tier_1: set[str] = set()
        self._tier_2: set[str] = set()
        self._all_tickers: set[str] = set()
        self._load_tiers()

    def _load_tiers(self):
        """Load tier definitions from config or defaults."""
        tier_config = self.config.get("tiers", {})

        # Load tier 1
        tier_1_file = tier_config.get("tier_1_file")
        if tier_1_file and Path(tier_1_file).exists():
            with open(tier_1_file) as f:
                self._tier_1 = {
                    line.strip() for line in f
                    if line.strip() and not line.strip().startswith("#")
                }
        else:
            self._tier_1 = set(DEFAULT_TIER_1)

        # Load tier 2 (exclusive - does not include tier 1)
        tier_2_file = tier_config.get("tier_2_file")
        if tier_2_file and Path(tier_2_file).exists():
            with open(tier_2_file) as f:
                raw_tier_2 = {
                    line.strip() for line in f
                    if line.strip() and not line.strip().startswith("#")
                }
                # Remove any tier 1 tickers that might be in the file
                self._tier_2 = raw_tier_2 - self._tier_1
        else:
            # Default: Load top 500 from ticker maps, excluding tier 1
            self._tier_2 = self._load_top_n_from_maps(500) - self._tier_1

        # Load all tickers for reference
        self._all_tickers = self._load_all_from_maps()
        logger.info(f"Loaded tiers: T1={len(self._tier_1)}, T2={len(self._tier_2)}, Total={len(self._all_tickers)}")

    def _load_top_n_from_maps(self, n: int) -> set[str]:
        """Load top N tickers from seed files (assumed sorted by market cap)."""
        tickers = []
        for map_file in ["data/seeds/ticker_map_us.json", "data/seeds/ticker_map_tw.json"]:
            path = Path(map_file)
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    tickers.extend(list(data.keys())[:n // 2])
        return set(tickers[:n])

    def _load_all_from_maps(self) -> set[str]:
        """Load all tickers from seed files."""
        tickers = set()
        for map_file in ["data/seeds/ticker_map_us.json", "data/seeds/ticker_map_tw.json"]:
            path = Path(map_file)
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    tickers.update(data.keys())
        return tickers

    def get_tier(self, ticker: str) -> int:
        """Get the tier for a ticker (1, 2, or 3)."""
        ticker_upper = ticker.upper()
        if ticker_upper in self._tier_1:
            return 1
        elif ticker_upper in self._tier_2:
            return 2
        return 3

    def get_tier_settings(self, ticker: str) -> dict[str, Any]:
        """Get processing settings for a ticker based on its tier."""
        tier = self.get_tier(ticker)
        tier_settings = self.config.get("tier_settings", {})

        defaults = {
            1: {
                "planning": "llm",
                "queries_per_ticker": 5,
                "docs_per_query": 5,
                "extraction_model": "gemini-2.5-flash",
            },
            2: {
                "planning": "template",
                "queries_per_ticker": 2,
                "docs_per_query": 3,
                "extraction_model": "gemini-2.5-flash",
            },
            3: {
                "planning": "template",
                "queries_per_ticker": 1,
                "docs_per_query": 2,
                "extraction_model": "gemini-1.5-flash-8b",
            },
        }

        return tier_settings.get(f"tier_{tier}", defaults[tier])

    def get_template_queries(self, ticker: str) -> list[str]:
        """Get template-based queries for a ticker."""
        sector = self._detect_sector(ticker)
        templates = TEMPLATE_QUERIES.get(sector, TEMPLATE_QUERIES["default"])
        return [t.format(ticker=ticker) for t in templates]

    def _detect_sector(self, ticker: str) -> str:
        """Detect sector for a ticker to select appropriate templates."""
        ticker_upper = ticker.upper()
        for sector, tickers in SECTOR_KEYWORDS.items():
            if ticker_upper in tickers:
                return sector
        return "default"

    def get_tickers_by_tier(self, tier: int) -> list[str]:
        """Get all tickers for a specific tier (exclusive, no overlap)."""
        if tier == 1:
            return list(self._tier_1)
        elif tier == 2:
            return list(self._tier_2)  # Already exclusive (tier 1 removed in _load_tiers)
        else:
            return list(self._all_tickers - self._tier_1 - self._tier_2)

    def categorize_tickers(self, tickers: list[str]) -> dict[int, list[str]]:
        """Categorize a list of tickers by tier."""
        result = {1: [], 2: [], 3: []}
        for ticker in tickers:
            tier = self.get_tier(ticker)
            result[tier].append(ticker)
        return result

