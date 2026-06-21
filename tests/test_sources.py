from app.providers import http, sources
from app.providers.search_base import SearchParams
from app import config

P = SearchParams(query="ai platform", limit=10)

REMOTEOK = [
    {"legal": "metadata element, no position"},
    {"position": "AI Platform Engineer", "company": "Acme",
     "description": "<p>Build AI platform tools</p>", "url": "https://remoteok.com/x",
     "apply_url": "https://acme.com/apply", "location": "Worldwide",
     "tags": ["ai", "platform"], "salary_min": 120000, "salary_max": 160000},
    {"position": "Frontend Dev", "company": "Beta", "description": "react",
     "url": "u", "tags": ["react"]},
]
REMOTIVE = {"jobs": [{"title": "AI Platform Specialist", "company_name": "Northstar",
                     "description": "<b>Administer AI platform</b>", "url": "https://remotive.com/x",
                     "candidate_required_location": "USA", "salary": "$120k"}]}
ARBEITNOW = {"data": [
    {"title": "AI Platform Engineer", "company_name": "Euro", "location": "Berlin", "url": "u1",
     "description": "build ai platform", "remote": True, "tags": ["ai"]},
    {"title": "AI Platform Onsite", "company_name": "X", "location": "NYC", "url": "u2",
     "description": "ai platform", "remote": False, "tags": []},
]}
ADZUNA = {"results": [{"title": "AI Platform Engineer", "company": {"display_name": "Acme"},
                      "location": {"display_name": "Remote, US"}, "redirect_url": "https://adzuna/x",
                      "description": "build ai platform", "salary_min": 120000, "salary_max": 160000}]}
JSEARCH = {"data": [{"job_title": "AI Platform Engineer", "employer_name": "Acme", "job_city": "Austin",
                    "job_state": "TX", "job_country": "US", "job_apply_link": "https://acme/apply",
                    "job_description": "build ai platform", "job_is_remote": True,
                    "job_min_salary": 120000, "job_max_salary": 160000}]}


def patch(monkeypatch, payload):
    monkeypatch.setattr(http, "get_json", lambda *a, **k: payload)


def test_remoteok_maps_and_filters_locally(monkeypatch):
    patch(monkeypatch, REMOTEOK)
    jobs = sources.RemoteOKProvider().search(P)
    assert len(jobs) == 1  # frontend dev filtered out by keywords; metadata skipped
    j = jobs[0]
    assert j.title == "AI Platform Engineer" and j.source == "remoteok"
    assert j.work_arrangement == "fully_remote" and j.application_url == "https://acme.com/apply"
    assert "120,000" in j.salary_raw and "<p>" not in j.description


def test_remotive_maps(monkeypatch):
    patch(monkeypatch, REMOTIVE)
    j = sources.RemotiveProvider().search(P)[0]
    assert j.title == "AI Platform Specialist" and j.source == "remotive"
    assert j.work_arrangement == "fully_remote" and "<b>" not in j.description


def test_arbeitnow_filters_remote_only(monkeypatch):
    patch(monkeypatch, ARBEITNOW)
    jobs = sources.ArbeitnowProvider().search(P)
    assert len(jobs) == 1 and jobs[0].company_name == "Euro"  # onsite one dropped


def test_adzuna_maps(monkeypatch):
    patch(monkeypatch, ADZUNA)
    j = sources.AdzunaProvider().search(P)[0]
    assert j.title == "AI Platform Engineer" and j.company_name == "Acme"
    assert j.source == "adzuna" and j.work_arrangement is None
    assert "120,000" in j.salary_raw


def test_jsearch_maps_location_and_remote(monkeypatch):
    patch(monkeypatch, JSEARCH)
    j = sources.JSearchProvider().search(P)[0]
    assert j.source == "jsearch" and j.location_raw == "Austin, TX, US"
    assert j.work_arrangement == "fully_remote" and j.application_url == "https://acme/apply"


def test_keyed_provider_availability(monkeypatch):
    monkeypatch.setattr(config, "JSEARCH_API_KEY", "")
    assert sources.JSearchProvider().available() is False
    monkeypatch.setattr(config, "JSEARCH_API_KEY", "abc")
    assert sources.JSearchProvider().available() is True
    monkeypatch.setattr(config, "ADZUNA_APP_ID", "")
    monkeypatch.setattr(config, "ADZUNA_APP_KEY", "")
    assert sources.AdzunaProvider().available() is False
    monkeypatch.setattr(config, "ADZUNA_APP_ID", "a")
    monkeypatch.setattr(config, "ADZUNA_APP_KEY", "b")
    assert sources.AdzunaProvider().available() is True
    # Free boards are always available
    assert sources.RemoteOKProvider().available() is True
