from datetime import datetime, timezone

from ingest.models import RawDoc


def normalize_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_doc_timezone(doc: RawDoc) -> RawDoc:
    doc.published_at = normalize_to_utc(doc.published_at)
    if doc.first_seen:
        doc.first_seen = normalize_to_utc(doc.first_seen)
    if doc.last_seen:
        doc.last_seen = normalize_to_utc(doc.last_seen)
    return doc

