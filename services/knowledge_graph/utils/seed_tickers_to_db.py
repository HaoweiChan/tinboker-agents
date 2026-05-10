import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from graph.store.neo4j_store import Neo4jStore
from utils.config import get_neo4j_config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def seed_tickers():
    config = get_neo4j_config()
    store = Neo4jStore(
        uri=config["uri"],
        user=config["user"],
        password=config["password"],
        database=config["database"]
    )

    # Seed TW Tickers
    tw_path = Path("data/seeds/ticker_map_tw.json")
    if tw_path.exists():
        logger.info("Seeding TW tickers...")
        with open(tw_path) as f:
            data = json.load(f)
        
        companies = []
        for ticker, info in data.items():
            company = {
                "id": ticker,
                "ticker": ticker,
                "market": "TW",
                "type": "Company"
            }
            if isinstance(info, dict):
                company["name"] = info.get("name_en") or info.get("name_zh")
                company["name_zh"] = info.get("name_zh")
                company["name_en"] = info.get("name_en")
                company["alias"] = info.get("alias")
            else:
                company["name"] = info
                company["name_zh"] = info
            
            companies.append(company)
            
        _batch_upsert(store, companies)

    # Seed US Tickers
    us_path = Path("data/seeds/ticker_map_us.json")
    if us_path.exists():
        logger.info("Seeding US tickers...")
        with open(us_path) as f:
            data = json.load(f)
            
        companies = []
        for ticker, name in data.items():
            companies.append({
                "id": ticker,
                "ticker": ticker,
                "market": "US",
                "type": "Company",
                "name": name,
                "name_en": name
            })
            
        _batch_upsert(store, companies)
        
    store.close()
    logger.info("Seeding complete.")

def _batch_upsert(store: Neo4jStore, companies: List[Dict[str, Any]], batch_size: int = 1000):
    query = """
    UNWIND $batch as row
    MERGE (c:Entity {id: row.id})
    SET c:Company,
        c.ticker = row.ticker,
        c.name = row.name,
        c.name_zh = row.name_zh,
        c.name_en = row.name_en,
        c.alias = row.alias,
        c.market = row.market,
        c.updated_at = datetime()
    """
    
    total = len(companies)
    for i in range(0, total, batch_size):
        batch = companies[i:i+batch_size]
        with store.driver.session(database=store.database) as session:
            session.run(query, batch=batch)
        logger.info(f"Upserted batch {i}-{min(i+batch_size, total)} / {total}")

if __name__ == "__main__":
    seed_tickers()

