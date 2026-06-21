"""Fan one keyword query out to every enabled source, merge, and de-duplicate.

A source is used when it is available (free, or its key is set) AND not toggled
off in settings. One failing source never breaks the search — its error is
captured in the per-source status list. JSearch usage is metered for cost control.
"""
from __future__ import annotations
from datetime import date
from app import db
from app.providers.sources import ALL_PROVIDERS
from app.providers.search_base import SearchParams


def current_period() -> str:
    d = date.today()
    return f"{d.year:04d}{d.month:02d}"


def enabled_providers(settings: dict) -> list:
    toggles = settings.get("sources", {})
    return [p for p in ALL_PROVIDERS if p.available() and toggles.get(p.name, True)]


def search_all(params: SearchParams, settings: dict, conn=None):
    """Returns (deduped_jobs, statuses). statuses has one entry per source."""
    toggles = settings.get("sources", {})
    jobs, seen, statuses = [], set(), []
    for p in ALL_PROVIDERS:
        st = {"name": p.name, "requires_key": p.requires_key,
              "available": p.available(), "enabled": toggles.get(p.name, True)}
        if not st["available"]:
            st["status"] = "no key" if p.requires_key else "unavailable"
            statuses.append(st)
            continue
        if not st["enabled"]:
            st["status"] = "off"
            statuses.append(st)
            continue
        try:
            found = p.search(params)
            if p.name == "jsearch" and conn is not None:
                db.increment_usage(conn, "jsearch", current_period(), 1)
            added = 0
            for j in found:
                if j.dedupe_hash in seen:
                    continue
                seen.add(j.dedupe_hash)
                jobs.append(j)
                added += 1
            st["status"] = "ok"
            st["count"] = added
        except Exception as e:  # one bad source must not break the whole search
            st["status"] = "error"
            st["error"] = str(e)[:200]
        statuses.append(st)
    return jobs, statuses
