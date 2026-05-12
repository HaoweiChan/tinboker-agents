"""Shared wiki builder.

Persists episode/entity/topic/supply-chain *content* into a pluggable
:class:`WikiRepository` (Postgres in production). Markdown is a *view*
(see :mod:`.views`), never the storage format — so this repo stays
infra-only and content-agnostic.
"""

from .factory import get_repository
from .ingest import ingest_episode, ingest_supply_chain
from .models import KINDS, WikiLink, WikiPage
from .records import (
    render_entity_page,
    render_episode_page,
    render_supply_chain_page,
    render_topic_page,
)
from .repository import InMemoryWikiRepository, NullWikiRepository, WikiRepository
from .slugify import episode_slug, slugify, ticker_slug
from .views import build_index_markdown, page_to_markdown

__all__ = [
    "KINDS",
    "WikiPage",
    "WikiLink",
    "WikiRepository",
    "InMemoryWikiRepository",
    "NullWikiRepository",
    "get_repository",
    "ingest_episode",
    "ingest_supply_chain",
    "render_episode_page",
    "render_entity_page",
    "render_topic_page",
    "render_supply_chain_page",
    "page_to_markdown",
    "build_index_markdown",
    "slugify",
    "ticker_slug",
    "episode_slug",
]
