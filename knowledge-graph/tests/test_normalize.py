from datetime import datetime, timezone

import pytest
from pydantic import HttpUrl

from ingest.models import RawDoc
from ingest.normalize import canonicalize_url, dedupe_docs, normalize_doc_timezone


def test_canonicalize_url():
    url1 = "https://example.com/article?utm_source=test&id=123"
    url2 = "https://example.com/article?id=123"
    assert canonicalize_url(url1) == canonicalize_url(url2)


def test_dedupe_docs():
    doc1 = RawDoc(
        url=HttpUrl("https://example.com/1"),
        title="Test",
        text="Content",
        published_at=datetime.utcnow(),
        source="test",
    )
    doc2 = RawDoc(
        url=HttpUrl("https://example.com/1"),
        title="Test",
        text="Content",
        published_at=datetime.utcnow(),
        source="test",
    )
    docs = [doc1, doc2]
    deduped = dedupe_docs(docs)
    assert len(deduped) == 1


def test_normalize_doc_timezone():
    doc = RawDoc(
        url=HttpUrl("https://example.com"),
        title="Test",
        text="Content",
        published_at=datetime(2024, 1, 1, 12, 0, 0),
        source="test",
    )
    normalized = normalize_doc_timezone(doc)
    assert normalized.published_at.tzinfo == timezone.utc

