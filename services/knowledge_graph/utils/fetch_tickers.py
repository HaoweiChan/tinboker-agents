import json
import logging
from pathlib import Path
import requests

logger = logging.getLogger(__name__)

def fetch_us_tickers(output_path: Path) -> int:
    """
    Fetches US tickers from SEC official JSON.
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {
        "User-Agent": "GraphBuilderAgent/1.0 (contact@example.com)"  # SEC requires a User-Agent
    }
    
    logger.info(f"Fetching US tickers from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # SEC data is dict of dicts: "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        tickers = []
        mapping = {}
        for entry in data.values():
            ticker = entry["ticker"]
            title = entry["title"]
            tickers.append(ticker)
            mapping[ticker] = title
            
        tickers.sort()
        
        with open(output_path, "w") as f:
            f.write("\n".join(tickers))
            
        # Save mapping
        map_path = output_path.parent / "data/mappings/ticker_map_us.json"
        # Ensure dir exists
        map_path.parent.mkdir(parents=True, exist_ok=True)
        with open(map_path, "w") as f:
            json.dump(mapping, f, indent=2)
            
        logger.info(f"Saved {len(tickers)} US tickers to {output_path}")
        logger.info(f"Saved US ticker mapping to {map_path}")
        return len(tickers)
    except Exception as e:
        logger.error(f"Failed to fetch US tickers: {e}")
        return 0

def fetch_tw_tickers(output_path: Path) -> int:
    """
    Fetches Taiwan tickers from TWSE Open Data.
    """
    # TWSE Open Data: Daily Stock Info
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    
    logger.info(f"Fetching Taiwan tickers from {url}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Data is list of dicts: [{"Code": "2330", "Name": "台積電", ...}, ...]
        tickers = []
        mapping = {}
        for item in data:
            code = item.get("Code")
            name = item.get("Name")
            if code:
                # Append .TW for compatibility
                ticker = f"{code}.TW"
                tickers.append(ticker)
                if name:
                    mapping[ticker] = name
        
        tickers.sort()
        
        with open(output_path, "w") as f:
            f.write("\n".join(tickers))
            
        # Save mapping
        map_path = output_path.parent / "data/mappings/ticker_map_tw.json"
        # Ensure dir exists
        map_path.parent.mkdir(parents=True, exist_ok=True)
        with open(map_path, "w") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Saved {len(tickers)} Taiwan tickers to {output_path}")
        logger.info(f"Saved TW ticker mapping to {map_path}")
        return len(tickers)
    except Exception as e:
        logger.error(f"Failed to fetch Taiwan tickers: {e}")
        return 0

def fetch_all_tickers(us_path: Path = Path("tickers_us_full.txt"), tw_path: Path = Path("tickers_tw_full.txt")) -> dict[str, int]:
    us_count = fetch_us_tickers(us_path)
    tw_count = fetch_tw_tickers(tw_path)
    return {"us": us_count, "tw": tw_count}

