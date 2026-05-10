import json
import logging
import time
from pathlib import Path
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from utils.config import get_llm_config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MAPPING_FILE = Path("data/mappings/ticker_map_tw.json")

def load_mapping() -> Dict[str, Any]:
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE) as f:
            return json.load(f)
    return {}

def save_mapping(mapping: Dict[str, Any]):
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

def enrich_tickers(limit: int = 20):
    """
    Enriches TW tickers with English names and abbreviations using Gemini.
    """
    mapping = load_mapping()
    llm_config = get_llm_config()
    
    if not llm_config.get("google_api_key"):
        logger.error("Google API Key not found.")
        return

    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro-preview-03-25",
        google_api_key=llm_config["google_api_key"],
        temperature=0.0
    )

    # Filter for stocks that are likely tech/supply chain related or just take the first N
    # For this demo, we'll process items that are still just strings (not enriched yet)
    candidates = {k: v for k, v in mapping.items() if isinstance(v, str)}
    
    # Prioritize common tech stocks if possible (simple heuristic or list)
    priority_list = ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "6669.TW", "3231.TW", "2303.TW"]
    
    to_process = []
    for ticker in priority_list:
        if ticker in candidates:
            to_process.append(ticker)
    
    # Fill the rest up to limit
    for ticker in candidates:
        if len(to_process) >= limit:
            break
        if ticker not in to_process:
            to_process.append(ticker)

    logger.info(f"Enriching {len(to_process)} tickers...")

    batch_size = 10
    for i in range(0, len(to_process), batch_size):
        batch = to_process[i:i+batch_size]
        batch_data = {t: mapping[t] for t in batch}
        
        prompt = ChatPromptTemplate.from_template(
            """
            You are a financial data assistant.
            For the following Taiwanese stocks (Ticker: Chinese Name), provide their standard English Name and a common Abbreviation/Alias used in English reports.
            
            Input:
            {data}
            
            Output JSON format:
            {{
                "TICKER": {{
                    "name_zh": "Chinese Name",
                    "name_en": "English Name",
                    "alias": "Abbreviation"
                }}
            }}
            Return ONLY valid JSON.
            """
        )
        
        try:
            chain = prompt | model
            result = chain.invoke({"data": json.dumps(batch_data, ensure_ascii=False)})
            content = result.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            enriched_data = json.loads(content)
            
            # Update mapping
            for ticker, info in enriched_data.items():
                if ticker in mapping:
                    mapping[ticker] = info
            
            logger.info(f"Processed batch {i//batch_size + 1}")
            
        except Exception as e:
            logger.error(f"Batch failed: {e}")
            time.sleep(2)
            
        # Save incrementally
        save_mapping(mapping)
        time.sleep(1)

if __name__ == "__main__":
    enrich_tickers()

