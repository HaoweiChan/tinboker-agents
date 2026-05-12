"""Ingest episode and supply-chain content into a :class:`WikiRepository`.

Entry points:
  - :func:`ingest_episode` — podcast episode data (used by ``services/podcast``)
  - :func:`ingest_supply_chain` — entity/edge data (knowledge-graph follow-up)

These build :class:`WikiPage` records and persist them via the repository; they
do not touch the filesystem.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..tickers import canonical_symbol, lookup_ticker
from .factory import get_repository
from .models import WikiPage
from .records import (
    render_entity_page,
    render_episode_page,
    render_supply_chain_page,
    render_topic_page,
)
from .repository import WikiRepository
from .slugify import slugify, ticker_slug


def _canonical_tickers(tickers: list[str]) -> list[str]:
    """Canonicalize + de-duplicate a ticker list, preserving first-seen order."""
    seen: dict[str, None] = {}
    for t in tickers:
        sym = canonical_symbol(t)
        if sym:
            seen.setdefault(sym, None)
    return list(seen)


def _append_line_to_section(body: str, marker: str, line: str) -> str:
    """Insert ``line`` once as the first item under ``marker``.

    Creates the section (with a blank line after the heading) if it is missing.
    """
    if line in body:
        return body
    idx = body.find(marker)
    if idx == -1:
        return body.rstrip() + f"\n\n{marker}\n\n{line}\n"
    nl = body.find("\n", idx)
    insert_at = len(body) if nl == -1 else nl + 1
    if body[insert_at : insert_at + 1] == "\n":  # keep one blank line after the heading
        insert_at += 1
    return body[:insert_at] + line + "\n" + body[insert_at:]


def _append_ticker_history(
    page: WikiPage, *, date: str, sentiment: str, score: Any, thesis: str
) -> None:
    row = f"| {date} | {sentiment} | {score} | {str(thesis).replace('|', '—')} |"
    body = page.body
    if row in body:
        return
    marker = "## Ticker History"
    if marker not in body:
        page.body = body.rstrip() + (
            "\n\n## Ticker History\n\n"
            "| Date | Sentiment | Score | Thesis |\n"
            "|------|-----------|-------|--------|\n"
            f"{row}\n"
        )
        return
    lines = body.split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.strip() == marker)
    last_table_row = start
    for i in range(start + 1, len(lines)):
        if lines[i].lstrip().startswith("|"):
            last_table_row = i
        elif lines[i].strip().startswith("#"):
            break
    lines.insert(last_table_row + 1, row)
    page.body = "\n".join(lines)


def ingest_episode(
    podcast_name: str,
    episode_number: int | None,
    title: str,
    date: str | None,
    tickers: list[str],
    tags: list[str],
    summary_text: str,
    events_markdown: str | None = None,
    ticker_recommendations: dict[str, Any] | None = None,
    source_urls: dict[str, str] | None = None,
    repository: WikiRepository | None = None,
) -> WikiPage:
    """Persist episode data: the episode page plus referenced entity/topic pages.

    Returns the (persisted) episode :class:`WikiPage`.
    """
    repo = repository or get_repository()
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    tickers = _canonical_tickers(tickers)  # registry-canonical symbols (e.g. "2330.TW" -> "2330")

    episode_page = render_episode_page(
        podcast_name=podcast_name,
        episode_number=episode_number,
        title=title,
        date=date,
        tickers=tickers,
        tags=tags,
        summary_text=summary_text,
        events_markdown=events_markdown,
        ticker_recommendations=ticker_recommendations,
        source_urls=source_urls,
    )
    ep_link = f"episodes/{episode_page.slug}"
    episode_page = repo.upsert_page(episode_page)

    recs = (ticker_recommendations or {}).get("ticker_recommendations", [])
    recs_by_ticker = {canonical_symbol(r["ticker"]): r for r in recs if r.get("ticker")}

    for ticker in tickers:
        t_slug = ticker_slug(ticker)
        page = repo.get_page("entity", t_slug)
        if page is None:
            info = lookup_ticker(ticker)
            page = render_entity_page(
                entity_id=t_slug,
                name=info.name if info else ticker,
                entity_type=info.type if info else "company",
                tickers=[ticker],
                mentions=[{"episode_link": ep_link, "context": title}],
                ticker_history=[],
                market=info.market if info else None,
                sector=info.sector if info else None,
            )
        else:
            page.body = _append_line_to_section(
                page.body, "## Episode Mentions", f"- [[{ep_link}]] — {title}"
            )
        rec = recs_by_ticker.get(ticker)
        if rec:
            _append_ticker_history(
                page,
                date=date,
                sentiment=rec.get("sentiment", ""),
                score=rec.get("sentiment_score", ""),
                thesis=rec.get("bluf_thesis", ""),
            )
        repo.upsert_page(page)

    for tag in tags:
        tg_slug = slugify(tag)
        page = repo.get_page("topic", tg_slug)
        if page is None:
            page = render_topic_page(
                topic_id=tg_slug,
                name=tag,
                episodes=[{"link": ep_link, "context": title}],
                entities=[ticker_slug(t) for t in tickers],
            )
        else:
            page.body = _append_line_to_section(
                page.body, "## Episodes", f"- [[{ep_link}]] — {title}"
            )
        repo.upsert_page(page)

    return episode_page


def ingest_supply_chain(
    entities: list[dict],
    edges: list[dict],
    evidence: list[dict] | None = None,
    repository: WikiRepository | None = None,
) -> int:
    """Persist supply-chain data (entity pages + per-source supply-chain pages).

    Returns the number of pages created/updated.
    """
    repo = repository or get_repository()
    count = 0
    entity_map = {e["id"]: e for e in entities}

    for edge in edges:
        src_id = edge.get("src", "")
        dst_id = edge.get("dst", "")
        rel = edge.get("rel", "RELATED_TO")
        status = edge.get("props", {}).get("status", "active")

        src_name = entity_map.get(src_id, {}).get("props", {}).get("name", src_id)
        dst_name = entity_map.get(dst_id, {}).get("props", {}).get("name", dst_id)
        src_slug = slugify(src_name)
        dst_slug = slugify(dst_name)

        for eid, ename, eslug in ((src_id, src_name, src_slug), (dst_id, dst_name, dst_slug)):
            if repo.get_page("entity", eslug) is None:
                etype = entity_map.get(eid, {}).get("type", "company")
                repo.upsert_page(
                    render_entity_page(
                        entity_id=eslug, name=ename, entity_type=etype, tickers=[]
                    )
                )
                count += 1

        sc_page = repo.get_page("supply_chain", src_slug) or render_supply_chain_page(
            src_slug, src_name
        )
        rel_line = f"- [[entities/{dst_slug}]] — {rel} ({status})"
        if rel_line not in sc_page.body:
            sc_page.body = _append_line_to_section(
                sc_page.body, "## Downstream (Customers)", rel_line
            )
            repo.upsert_page(sc_page)
            count += 1

    return count
