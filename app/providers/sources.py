"""Keyword-search source adapters. Each maps a provider's JSON to NormalizedJob.

Free boards (RemoteOK, Remotive, Arbeitnow) need no key. JSearch and Adzuna read
their keys from app.config (set via .env). All network goes through http.get_json,
which tests monkeypatch — no test hits the live network.
"""
from __future__ import annotations
from app import config
from app.providers import http
from app.providers.search_base import (
    SearchParams, make_job, matches_keywords, strip_html, format_salary)

_DATE_DAYS = {"today": 1, "3days": 3, "week": 7, "month": 30}


class RemoteOKProvider:
    name = "remoteok"
    requires_key = False
    URL = "https://remoteok.com/api"

    def available(self) -> bool:
        return True

    def search(self, params: SearchParams) -> list:
        data = http.get_json(self.URL)
        out = []
        for d in data:
            if not isinstance(d, dict) or not d.get("position"):
                continue  # first element is board metadata
            text = " ".join([d.get("position", ""), d.get("description", ""),
                             " ".join(d.get("tags") or [])])
            if not matches_keywords(text, params.query):
                continue
            out.append(make_job(
                d.get("position"), d.get("company"), strip_html(d.get("description", "")),
                url=d.get("apply_url") or d.get("url"), location=d.get("location") or "Remote",
                arrangement="fully_remote",
                salary=format_salary(d.get("salary_min"), d.get("salary_max")), source=self.name))
            if len(out) >= params.limit:
                break
        return out


class RemotiveProvider:
    name = "remotive"
    requires_key = False
    URL = "https://remotive.com/api/remote-jobs"

    def available(self) -> bool:
        return True

    def search(self, params: SearchParams) -> list:
        data = http.get_json(self.URL, params={"search": params.query, "limit": params.limit})
        out = []
        for j in (data.get("jobs") or [])[:params.limit]:
            out.append(make_job(
                j.get("title"), j.get("company_name"), strip_html(j.get("description", "")),
                url=j.get("url"), location=j.get("candidate_required_location") or "Remote",
                arrangement="fully_remote", salary=(j.get("salary") or None), source=self.name))
        return out


class ArbeitnowProvider:
    name = "arbeitnow"
    requires_key = False
    URL = "https://www.arbeitnow.com/api/job-board-api"

    def available(self) -> bool:
        return True

    def search(self, params: SearchParams) -> list:
        data = http.get_json(self.URL)
        out = []
        for j in (data.get("data") or []):
            text = " ".join([j.get("title", ""), j.get("description", ""),
                             " ".join(j.get("tags") or [])])
            if not matches_keywords(text, params.query):
                continue
            if params.remote_only and not j.get("remote"):
                continue
            out.append(make_job(
                j.get("title"), j.get("company_name"), strip_html(j.get("description", "")),
                url=j.get("url"), location=j.get("location"),
                arrangement="fully_remote" if j.get("remote") else None, source=self.name))
            if len(out) >= params.limit:
                break
        return out


class AdzunaProvider:
    name = "adzuna"
    requires_key = True
    URL = "https://api.adzuna.com/v1/api/jobs/us/search/1"

    def available(self) -> bool:
        return bool(config.ADZUNA_APP_ID and config.ADZUNA_APP_KEY)

    def search(self, params: SearchParams) -> list:
        q = {"app_id": config.ADZUNA_APP_ID, "app_key": config.ADZUNA_APP_KEY,
             "what": params.query, "results_per_page": params.limit, "content-type": "application/json"}
        if params.remote_only:
            q["what"] = params.query + " remote"  # Adzuna has no remote flag; bias the query
        if params.location:
            q["where"] = params.location
        days = _DATE_DAYS.get(params.date_posted)
        if days:
            q["max_days_old"] = days
        data = http.get_json(self.URL, params=q)
        out = []
        for r in (data.get("results") or [])[:params.limit]:
            out.append(make_job(
                r.get("title"), (r.get("company") or {}).get("display_name"),
                strip_html(r.get("description", "")), url=r.get("redirect_url"),
                location=(r.get("location") or {}).get("display_name"), arrangement=None,
                salary=format_salary(r.get("salary_min"), r.get("salary_max")), source=self.name))
        return out


class JSearchProvider:
    name = "jsearch"
    requires_key = True
    URL = "https://jsearch.p.rapidapi.com/search"
    HOST = "jsearch.p.rapidapi.com"

    def available(self) -> bool:
        return bool(config.JSEARCH_API_KEY)

    def search(self, params: SearchParams) -> list:
        query = params.query + (f" in {params.location}" if params.location else "")
        q = {"query": query.strip(), "page": 1, "num_pages": 1}
        if params.remote_only:
            q["remote_jobs_only"] = "true"
        if params.date_posted and params.date_posted != "all":
            q["date_posted"] = params.date_posted
        headers = {"X-RapidAPI-Key": config.JSEARCH_API_KEY, "X-RapidAPI-Host": self.HOST}
        data = http.get_json(self.URL, params=q, headers=headers)
        out = []
        for j in (data.get("data") or [])[:params.limit]:
            loc = ", ".join(x for x in [j.get("job_city"), j.get("job_state"),
                                        j.get("job_country")] if x)
            out.append(make_job(
                j.get("job_title"), j.get("employer_name"), strip_html(j.get("job_description", "")),
                url=j.get("job_apply_link"), location=(loc or None),
                # We asked JSearch for remote-only; trust that (its per-job remote flag is
                # unreliable). The classifier still downgrades if the text says on-site.
                arrangement="fully_remote" if (params.remote_only or j.get("job_is_remote")) else None,
                salary=format_salary(j.get("job_min_salary"), j.get("job_max_salary")), source=self.name))
        return out


# Order matters for display; keyed broad sources first, then free boards.
ALL_PROVIDERS = [JSearchProvider(), AdzunaProvider(), RemotiveProvider(),
                 RemoteOKProvider(), ArbeitnowProvider()]
