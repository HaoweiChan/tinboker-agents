import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def load_env_file(env_path: Path | None = None) -> None:
    if env_path is None:
        env_path = Path(".env")

    if env_path.exists():
        # Don't override existing env vars (Cloud Run sets them directly)
        load_dotenv(env_path, override=False)


def get_backend_config() -> dict[str, Any]:
    load_env_file()
    return {
        "url": os.getenv("BACKEND_URL", "http://localhost:5174"),
        "api_token": os.getenv("BACKEND_API_TOKEN", ""),
    }


def get_neo4j_config() -> dict[str, Any]:
    load_env_file()
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password"),
        "database": os.getenv("NEO4J_DATABASE", "neo4j"),
    }


def get_llm_config() -> dict[str, Any]:
    load_env_file()
    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "google_api_key": os.getenv("GOOGLE_API_KEY", ""),
        "default_model": os.getenv("LLM_DEFAULT_MODEL", "gemini-2.5-flash"),
    }


def get_search_config() -> dict[str, Any]:
    load_env_file()
    return {
        "tavily_api_key": os.getenv("TAVILY_API_KEY", ""),
        "exa_api_key": os.getenv("EXA_API_KEY", ""),
    }

