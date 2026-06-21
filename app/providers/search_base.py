from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import date
from app.models import NormalizedJob, compute_dedupe_hash

_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class SearchParams:
    query: str
    location: str = "United States"
    remote_only: bool = True
    date_posted: str = "all"   # all | today | 3days | week | month
    limit: int = 10            # results per source


def matches_keywords(text: str, query: str) -> bool:
    """Local keyword filter for providers without server-side search.

    Keeps a posting only if every whitespace token of the query appears as a
    whole word (case-insensitive) — so "ai" matches "AI", not "available". An
    empty query keeps everything.
    """
    low = (text or "").lower()
    return all(re.search(r"\b" + re.escape(tok) + r"\b", low) for tok in query.lower().split())


def strip_html(s: str) -> str:
    return _TAG_RE.sub(" ", s or "").replace("&amp;", "&").replace("&nbsp;", " ").strip()


def format_salary(lo, hi) -> str | None:
    try:
        lo = int(lo) if lo else None
        hi = int(hi) if hi else None
    except (TypeError, ValueError):
        return None
    if lo and hi:
        return f"${lo:,}–${hi:,}"
    if lo:
        return f"from ${lo:,}"
    if hi:
        return f"up to ${hi:,}"
    return None


def make_job(title, company, description, url=None, location=None, arrangement=None,
             salary=None, source="search") -> NormalizedJob:
    title = (title or "").strip()
    company = (company or "").strip()
    description = description or ""
    return NormalizedJob(
        title=title, company_name=company, description=description,
        application_url=(url or None), location_raw=(location or None),
        work_arrangement=(arrangement or None), salary_raw=(salary or None),
        source=source, date_found=date.today().isoformat(),
        dedupe_hash=compute_dedupe_hash(title, company, description))
