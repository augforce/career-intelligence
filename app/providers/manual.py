from __future__ import annotations
from datetime import date
from app.models import NormalizedJob, compute_dedupe_hash


def manual_job(title: str, company: str, description: str, application_url: str | None = None,
               location_raw: str | None = None, work_arrangement: str | None = None) -> NormalizedJob:
    # Explicit fields only — nothing is fetched or scraped.
    return NormalizedJob(
        title=title.strip(), company_name=company.strip(), description=description,
        application_url=(application_url or None), location_raw=(location_raw or None),
        work_arrangement=(work_arrangement or None), source="manual",
        date_found=date.today().isoformat(),
        dedupe_hash=compute_dedupe_hash(title, company, description),
        arrangement_locked=bool(work_arrangement))
