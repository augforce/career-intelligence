from __future__ import annotations
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app import db, config
from app.profile import load_profile
from app.evaluate import evaluate_job
from app.providers.manual import manual_job
from app.providers.mock import MockProvider
from app.providers import aggregate
from app.providers.search_base import SearchParams
from app.analysis import claude_judge

BASE = Path(__file__).parent
app = FastAPI(title="Career Intelligence")
app.mount("/static", StaticFiles(directory=BASE / "web" / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE / "web" / "templates"))
PROFILE = load_profile()
CATEGORY_LABEL = {"strong_match": "Strong Match", "bridge_role": "Bridge Role",
                  "stretch_role": "Stretch Role", "poor_fit": "Poor Fit / Exclude"}
_FIT_TO_CAT = {"strong": "strong_match", "bridge": "bridge_role",
               "stretch": "stretch_role", "poor": "poor_fit"}


def _ingest(conn, job):
    ev = evaluate_job(job, PROFILE, db.get_settings(conn))
    # Store the classifier's corrected arrangement so the card shows the truth,
    # not an unreliable "remote" hint from the source.
    job.work_arrangement = ev.classification.work_arrangement
    jid = db.insert_job(conn, job)
    db.insert_evaluation(conn, jid, ev)
    return jid, ev


def _claude_pass(conn, jid, job):
    """Run Claude's verdict on a single job (no drop) and record it."""
    if not claude_judge.available():
        return
    v = claude_judge.judge(job)
    if v:
        db.save_claude_verdict(conn, jid, v["remote"], v["fit"], v["score"], v["reason"], config.CLAUDE_MODEL)
        db.set_eval_category(conn, jid, _FIT_TO_CAT[v["fit"]])


@app.get("/")
def index(request: Request):
    conn = db.connect()
    jobs = db.get_jobs_with_eval(conn)
    return templates.TemplateResponse(request, "index.html",
        {"jobs": jobs, "labels": CATEGORY_LABEL,
         "jsearch_quota": db.get_usage(conn, "jsearch", aggregate.current_period())})


@app.post("/search")
def search(request: Request, query: str = Form(...), location: str = Form("United States"),
           remote_only: str = Form(""), date_posted: str = Form("all"), limit: int = Form(10)):
    conn = db.connect()
    remote = (remote_only == "on")
    params = SearchParams(query=query, location=location, remote_only=remote,
                          date_posted=date_posted, limit=max(1, min(50, limit)))
    db.clear_jobs(conn)  # each search returns a fresh result set
    found, statuses = aggregate.search_all(params, db.get_settings(conn), conn)
    settings = db.get_settings(conn)
    use_claude = claude_judge.available()
    stored, claude_calls, claude_dropped, hidden_poor = 0, 0, 0, 0
    for job in found:
        ev = evaluate_job(job, PROFILE, settings)
        # Remote-only: drop roles the description reveals as hybrid/on-site.
        if remote and ev.classification.work_arrangement in ("hybrid", "on_site"):
            continue
        # Search surfaces only real matches — not flagged junk.
        if ev.category == "poor_fit":
            hidden_poor += 1
            continue
        job.work_arrangement = ev.classification.work_arrangement
        jid = db.insert_job(conn, job)
        db.insert_evaluation(conn, jid, ev)
        stored += 1
        # Optional Claude pass: verify real remote status + skill-fit on survivors.
        if use_claude and claude_calls < config.CLAUDE_MAX_PER_SEARCH:
            v = claude_judge.judge(job)
            claude_calls += 1
            if v:
                if remote and v["remote"] in ("onsite", "hybrid"):
                    db.delete_job(conn, jid)  # Claude caught an on-site the keywords missed
                    stored -= 1
                    claude_dropped += 1
                    continue
                if v["fit"] == "poor":
                    db.delete_job(conn, jid)  # Claude judged it not a real fit
                    stored -= 1
                    hidden_poor += 1
                    continue
                db.save_claude_verdict(conn, jid, v["remote"], v["fit"], v["score"], v["reason"], config.CLAUDE_MODEL)
                db.set_eval_category(conn, jid, _FIT_TO_CAT[v["fit"]])
    db.record_scan(conn, "search", stored, stored)
    return templates.TemplateResponse(request, "index.html",
        {"jobs": db.get_jobs_with_eval(conn), "labels": CATEGORY_LABEL,
         "search_status": statuses, "query": query,
         "claude_dropped": claude_dropped, "hidden_poor": hidden_poor, "claude_on": use_claude,
         "jsearch_quota": db.get_usage(conn, "jsearch", aggregate.current_period())})


@app.post("/import")
def import_job(title: str = Form(...), company: str = Form(...), description: str = Form(...),
               application_url: str = Form(""), location: str = Form(""),
               work_arrangement: str = Form("")):
    conn = db.connect()
    db.clear_jobs(conn)  # each evaluation replaces the prior one; nothing piles up
    job = manual_job(title, company, description, application_url or None,
                     location or None, work_arrangement or None)
    jid, ev = _ingest(conn, job)
    _claude_pass(conn, jid, job)
    db.record_scan(conn, "manual", 1, 0 if ev.gate_result.excluded else 1)
    return RedirectResponse(f"/job/{jid}", status_code=303)


@app.post("/paste")
def paste(posting: str = Form(...)):
    """Paste a whole job posting; Claude extracts the fields, then we evaluate it."""
    conn = db.connect()
    db.clear_jobs(conn)  # each evaluation replaces the prior one; nothing piles up
    text = posting.strip()
    fields = claude_judge.extract(text) or {}
    title = (fields.get("title") or "").strip()
    if not title:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        title = (lines[0] if lines else "Pasted role")[:160]
    job = manual_job(title, fields.get("company") or "Unknown", text,
                     location_raw=(fields.get("location") or None))
    jid, ev = _ingest(conn, job)
    _claude_pass(conn, jid, job)
    db.record_scan(conn, "paste", 1, 0 if ev.gate_result.excluded else 1)
    return RedirectResponse(f"/job/{jid}", status_code=303)


@app.post("/scan/mock")
def scan_mock():
    conn = db.connect()
    db.clear_jobs(conn)  # fresh result set each scan
    evs = [_ingest(conn, job)[1] for job in MockProvider().fetch()]
    db.record_scan(conn, "mock", len(evs), sum(1 for e in evs if not e.gate_result.excluded))
    return RedirectResponse("/", status_code=303)


@app.post("/clear")
def clear():
    """Wipe the jobs list and scan History on demand (Filters/Watchlist stay)."""
    conn = db.connect()
    db.clear_jobs(conn)
    db.clear_scans(conn)
    return RedirectResponse("/", status_code=303)


@app.get("/job/{job_id}")
def job_detail(request: Request, job_id: int):
    conn = db.connect()
    job = db.get_job_detail(conn, job_id)
    return templates.TemplateResponse(request, "job_detail.html",
        {"job": job, "labels": CATEGORY_LABEL})


@app.post("/job/{job_id}/decision")
def decision(job_id: int, status: str = Form(...), notes: str = Form("")):
    db.upsert_decision(db.connect(), job_id, status, notes)
    return RedirectResponse(f"/job/{job_id}", status_code=303)


@app.get("/settings")
def settings_get(request: Request):
    conn = db.connect()
    return templates.TemplateResponse(request, "settings.html", {
        "s": db.get_settings(conn),
        "jsearch_key": bool(config.JSEARCH_API_KEY),
        "adzuna_key": bool(config.ADZUNA_APP_ID and config.ADZUNA_APP_KEY),
        "claude_key": bool(config.ANTHROPIC_API_KEY),
        "claude_model": config.CLAUDE_MODEL,
        "jsearch_quota": db.get_usage(conn, "jsearch", aggregate.current_period())})


@app.post("/settings")
def settings_post(include_travel: str = Form(""), include_hybrid: str = Form(""),
                  include_on_site: str = Form(""), max_travel_pct: int = Form(0),
                  eligible_states: str = Form("ALL_US"),
                  src_jsearch: str = Form(""), src_adzuna: str = Form(""),
                  src_remotive: str = Form(""), src_remoteok: str = Form(""),
                  src_arbeitnow: str = Form("")):
    db.save_settings(db.connect(), {
        "include_travel": include_travel == "on", "include_hybrid": include_hybrid == "on",
        "include_on_site": include_on_site == "on", "max_travel_pct": max_travel_pct,
        "eligible_states": [s.strip() for s in eligible_states.split(",") if s.strip()],
        "sources": {"jsearch": src_jsearch == "on", "adzuna": src_adzuna == "on",
                    "remotive": src_remotive == "on", "remoteok": src_remoteok == "on",
                    "arbeitnow": src_arbeitnow == "on"}})
    return RedirectResponse("/settings", status_code=303)


@app.get("/watchlist")
def watchlist_get(request: Request):
    return templates.TemplateResponse(request, "watchlist.html",
        {"companies": db.list_companies(db.connect())})


@app.post("/watchlist/add")
def watchlist_add(name: str = Form(...), ats_type: str = Form("unknown"),
                  careers_url: str = Form(""), notes: str = Form("")):
    db.add_company(db.connect(), name, ats_type, careers_url, notes, True)
    return RedirectResponse("/watchlist", status_code=303)


@app.post("/watchlist/{cid}/toggle")
def watchlist_toggle(cid: int):
    conn = db.connect()
    cur = next((c for c in db.list_companies(conn) if c["id"] == cid), None)
    if cur:
        db.update_company(conn, cid, active=not bool(cur["active"]))
    return RedirectResponse("/watchlist", status_code=303)


@app.post("/watchlist/{cid}/delete")
def watchlist_delete(cid: int):
    db.delete_company(db.connect(), cid)
    return RedirectResponse("/watchlist", status_code=303)


@app.get("/history")
def history(request: Request):
    return templates.TemplateResponse(request, "history.html",
        {"scans": db.list_scans(db.connect())})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=config.PORT, reload=True)
