import hashlib
from datetime import datetime
from typing import Any

from ingest.models import RawDoc


def compute_content_hash(doc: RawDoc) -> str:
    content = f"{doc.title}\n{doc.text}".encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def dedupe_docs(docs: list[RawDoc]) -> list[RawDoc]:
    seen_hashes: dict[str, RawDoc] = {}
    seen_urls: dict[str, RawDoc] = {}

    for doc in docs:
        content_hash = compute_content_hash(doc)
        url_str = str(doc.url)

        existing_by_hash = seen_hashes.get(content_hash)
        existing_by_url = seen_urls.get(url_str)

        if existing_by_hash:
            existing_by_hash.last_seen = datetime.utcnow()
            if not existing_by_hash.first_seen:
                existing_by_hash.first_seen = existing_by_hash.published_at
            continue

        if existing_by_url:
            existing_by_url.last_seen = datetime.utcnow()
            if not existing_by_url.first_seen:
                existing_by_url.first_seen = existing_by_url.published_at
            continue

        doc.first_seen = doc.published_at
        doc.last_seen = datetime.utcnow()
        seen_hashes[content_hash] = doc
        seen_urls[url_str] = doc

    return list(seen_hashes.values())

