"""Pick a :class:`WikiRepository` implementation from the environment.

``WIKI_DATABASE_URL`` set  -> :class:`PostgresWikiRepository`
``WIKI_DATABASE_URL`` unset -> :class:`NullWikiRepository` (no-op, warns once)
"""

from __future__ import annotations

import os

from .repository import NullWikiRepository, WikiRepository


def get_repository(database_url: str | None = None) -> WikiRepository:
    url = database_url if database_url is not None else os.environ.get("WIKI_DATABASE_URL")
    if not url:
        return NullWikiRepository()
    from .postgres_repo import PostgresWikiRepository

    return PostgresWikiRepository(url)
