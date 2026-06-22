import importlib
import app.config as config
from app import db
from fastapi.testclient import TestClient


def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    import app.main as m
    importlib.reload(m)
    return TestClient(m.app)


def test_import_then_appears_in_list(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    r = c.post("/import", data={"title": "AI Platform Operations Specialist",
        "company": "Acme", "description": "Fully remote, United States. Administer Microsoft Foundry "
        "and Azure AI: model deployment, RBAC, content filter, model evaluation, AI governance. Build "
        "internal tools and automation, and own applied AI implementation alongside AI engineers on "
        "the platform team. Requirements: REST API, BigQuery, monitoring, troubleshooting. Help with "
        "documentation and onboarding. Report to the platform team.",
        "application_url": "https://x/apply"}, follow_redirects=True)
    assert r.status_code == 200
    assert "AI Platform Operations Specialist" in r.text
    assert "Strong Match" in r.text or "Bridge Role" in r.text


def test_mock_scan_populates_list(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    r = c.post("/scan/mock", follow_redirects=True)
    assert "Help Desk Technician" in r.text and "Poor Fit" in r.text


def test_decision_updates_status(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    c.post("/import", data={"title": "R", "company": "C", "description": "Remote. Build automation."},
           follow_redirects=True)
    conn = db.connect()
    jid = db.get_jobs_with_eval(conn)[0]["id"]
    r = c.post(f"/job/{jid}/decision", data={"status": "applied", "notes": "sent"},
               follow_redirects=True)
    assert r.status_code == 200
    assert db.get_job_detail(db.connect(), jid)["status"] == "applied"


def test_settings_toggle_persists_and_unlocks_onsite(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    c.post("/settings", data={"include_on_site": "on", "max_travel_pct": "0"}, follow_redirects=True)
    c.post("/scan/mock", follow_redirects=True)
    rows = {r["title"]: r for r in db.get_jobs_with_eval(db.connect())}
    assert rows["AI Platform Engineer"]["excluded"] == 0  # on-site now allowed


def test_watchlist_add_and_toggle(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    c.post("/watchlist/add", data={"name": "Northstar AI", "ats_type": "greenhouse",
        "careers_url": "https://northstar/careers", "notes": "target"}, follow_redirects=True)
    conn = db.connect()
    comp = db.list_companies(conn)[0]
    assert comp["name"] == "Northstar AI" and comp["active"] == 1
    c.post(f"/watchlist/{comp['id']}/toggle", follow_redirects=True)
    assert db.list_companies(db.connect())[0]["active"] == 0


def test_search_ingests_results_and_shows_sources(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    from app.providers import aggregate
    from app.providers.search_base import make_job

    def fake(params, settings, conn=None):
        job = make_job("AI Platform Engineer", "Acme",
                       "Fully remote, United States. Administer Azure AI, model deployment, RBAC. "
                       "Build internal tools and automation. Requirements: APIs. Report to platform team.",
                       arrangement="fully_remote", source="remotive")
        return ([job], [
            {"name": "remotive", "status": "ok", "count": 1, "available": True, "enabled": True, "requires_key": False},
            {"name": "jsearch", "status": "no key", "available": False, "enabled": True, "requires_key": True}])

    monkeypatch.setattr(aggregate, "search_all", fake)
    r = c.post("/search", data={"query": "ai platform", "remote_only": "on"}, follow_redirects=True)
    assert r.status_code == 200
    assert "AI Platform Engineer" in r.text
    assert "remotive" in r.text and "jsearch" in r.text  # per-source status banner


def test_search_clears_previous_results(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    c.post("/scan/mock", follow_redirects=True)  # populate prior results
    from app.providers import aggregate
    from app.providers.search_base import make_job

    def fake(params, settings, conn=None):
        return ([make_job("Only Result", "Acme",
                          "Fully remote, United States. Administer Azure AI and model deployment.",
                          arrangement="fully_remote", source="remotive")], [])

    monkeypatch.setattr(aggregate, "search_all", fake)
    r = c.post("/search", data={"query": "ai", "remote_only": "on"}, follow_redirects=True)
    assert "Only Result" in r.text
    assert "Help Desk Technician" not in r.text  # prior mock results cleared
    assert len(db.get_jobs_with_eval(db.connect())) == 1


def test_search_remote_only_drops_onsite(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    from app.providers import aggregate
    from app.providers.search_base import make_job

    def fake(params, settings, conn=None):
        remote = make_job("Remote Role", "A", "Fully remote, United States. Administer Azure AI.",
                          arrangement="fully_remote", source="remotive")
        # provider WRONGLY flags this on-site role as remote:
        onsite = make_job("Onsite Role", "B", "On-site in Austin. Administer Azure AI.",
                          arrangement="fully_remote", source="jsearch")
        return ([remote, onsite], [])

    monkeypatch.setattr(aggregate, "search_all", fake)
    r = c.post("/search", data={"query": "ai", "remote_only": "on"}, follow_redirects=True)
    assert "Remote Role" in r.text
    assert "Onsite Role" not in r.text  # on-site dropped despite the remote claim


def test_search_claude_recategorizes_and_shows_reason(tmp_path, monkeypatch):
    import app.config as cfg
    c = client(tmp_path, monkeypatch)
    monkeypatch.setattr(cfg, "ANTHROPIC_API_KEY", "sk-test")
    from app.providers import aggregate
    from app.providers.search_base import make_job
    from app.analysis import claude_judge

    def fake_search(params, settings, conn=None):
        return ([make_job("AI Platform Operations Specialist", "Acme",
                          "Fully remote, United States. Administer Azure AI, model deployment, RBAC. "
                          "Build internal tools and automation. Requirements: APIs. Report to platform team.",
                          arrangement="fully_remote", source="remotive")], [])

    monkeypatch.setattr(aggregate, "search_all", fake_search)
    monkeypatch.setattr(claude_judge, "judge",
                        lambda job: {"remote": "remote", "fit": "bridge", "score": 68,
                                     "reason": "Adjacent platform-ops role; a reachable bridge."})
    r = c.post("/search", data={"query": "ai", "remote_only": "on"}, follow_redirects=True)
    assert "AI Platform Operations Specialist" in r.text
    assert "Bridge Role" in r.text  # Claude set the fit category
    assert "68/100" in r.text  # Claude's score is the headline, not the keyword count
    assert "reachable bridge" in r.text  # Claude's reason is shown


def test_search_hides_poor_fit(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    from app.providers import aggregate
    from app.providers.search_base import make_job

    def fake_search(params, settings, conn=None):
        return ([make_job("Office Assistant", "X",
                          "Remote office assistant. Answer phones, schedule meetings, basic bookkeeping.",
                          arrangement="fully_remote", source="remotive")], [])

    monkeypatch.setattr(aggregate, "search_all", fake_search)
    r = c.post("/search", data={"query": "ai", "remote_only": "on"}, follow_redirects=True)
    assert "Office Assistant" not in r.text  # poor-fit junk hidden from search results
    assert len(db.get_jobs_with_eval(db.connect())) == 0


def test_paste_evaluates_and_lands_on_verdict(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    # Claude off (hermetic) -> extract returns None -> title comes from the first line.
    blob = ("AI Systems Administrator\nAcme Corp\nFully remote, United States. Administer Azure AI and "
            "Microsoft 365, manage SSO and user provisioning, support enterprise AI platforms.")
    r = c.post("/paste", data={"posting": blob}, follow_redirects=True)
    assert r.status_code == 200
    assert "AI Systems Administrator" in r.text  # landed on the job's verdict page
    assert len(db.get_jobs_with_eval(db.connect())) == 1


def test_search_claude_drops_onsite(tmp_path, monkeypatch):
    import app.config as cfg
    c = client(tmp_path, monkeypatch)
    monkeypatch.setattr(cfg, "ANTHROPIC_API_KEY", "sk-test")
    from app.providers import aggregate
    from app.providers.search_base import make_job
    from app.analysis import claude_judge

    def fake_search(params, settings, conn=None):
        return ([make_job("Sneaky Onsite Role", "X", "Fully remote! Administer Azure AI.",
                          arrangement="fully_remote", source="jsearch")], [])

    monkeypatch.setattr(aggregate, "search_all", fake_search)
    monkeypatch.setattr(claude_judge, "judge",
                        lambda job: {"remote": "onsite", "fit": "poor", "score": 20, "reason": "Requires on-site in Austin."})
    r = c.post("/search", data={"query": "ai", "remote_only": "on"}, follow_redirects=True)
    assert "Sneaky Onsite Role" not in r.text  # Claude removed the on-site role the keywords missed
    assert len(db.get_jobs_with_eval(db.connect())) == 0


def test_search_keeps_claude_poor_remote_role(tmp_path, monkeypatch):
    # A keyword-vetted remote role that Claude rates "poor" must STILL be shown -
    # the deterministic stage already removed true junk, and the Claude layer is
    # additive: it annotates, it does not delete a survivor just for a low score.
    import app.config as cfg
    c = client(tmp_path, monkeypatch)
    monkeypatch.setattr(cfg, "ANTHROPIC_API_KEY", "sk-test")
    from app.providers import aggregate
    from app.providers.search_base import make_job
    from app.analysis import claude_judge

    def fake_search(params, settings, conn=None):
        return ([make_job("AI Platform Operations Specialist", "Acme",
                          "Fully remote, United States. Administer Azure AI, model deployment, RBAC. "
                          "Build internal tools and automation. Requirements: APIs. Report to platform team.",
                          arrangement="fully_remote", source="remotive")], [])

    monkeypatch.setattr(aggregate, "search_all", fake_search)
    monkeypatch.setattr(claude_judge, "judge",
                        lambda job: {"remote": "remote", "fit": "poor", "score": 30,
                                     "reason": "Borderline; leans engineering."})
    r = c.post("/search", data={"query": "ai", "remote_only": "on"}, follow_redirects=True)
    assert "AI Platform Operations Specialist" in r.text       # kept, not deleted
    assert len(db.get_jobs_with_eval(db.connect())) == 1
    assert "leans engineering" in r.text                       # Claude's read still shown


def test_settings_source_toggle_persists(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    # full settings form with remoteok unchecked (omitted)
    c.post("/settings", data={"src_jsearch": "on", "src_adzuna": "on", "src_remotive": "on",
                              "src_arbeitnow": "on"}, follow_redirects=True)
    s = db.get_settings(db.connect())
    assert s["sources"]["remoteok"] is False and s["sources"]["remotive"] is True


def test_clear_route_wipes_jobs_and_history(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    c.post("/scan/mock", follow_redirects=True)  # populates jobs + records a scan
    assert len(db.get_jobs_with_eval(db.connect())) > 0
    assert len(db.list_scans(db.connect())) > 0
    r = c.post("/clear", follow_redirects=True)
    assert r.status_code == 200
    assert db.get_jobs_with_eval(db.connect()) == []  # jobs gone
    assert db.list_scans(db.connect()) == []          # History gone too


def test_paste_replaces_previous_job(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    # Claude off -> title comes from the first line of each blob.
    blob1 = "First Role\nAcme\nFully remote, United States. Administer Azure AI and model deployment."
    blob2 = "Second Role\nBeta\nFully remote, United States. Administer Azure AI and model deployment."
    c.post("/paste", data={"posting": blob1}, follow_redirects=True)
    r = c.post("/paste", data={"posting": blob2}, follow_redirects=True)
    jobs = db.get_jobs_with_eval(db.connect())
    assert len(jobs) == 1 and jobs[0]["title"] == "Second Role"  # only the latest paste remains
    assert "First Role" not in r.text


def test_clear_button_shown_only_when_jobs_exist(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert 'action="/clear"' not in c.get("/").text  # empty list -> no Clear button
    c.post("/scan/mock", follow_redirects=True)
    assert 'action="/clear"' in c.get("/").text       # jobs present -> Clear button shows


def test_scan_history_records_mock_scan(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    c.post("/scan/mock", follow_redirects=True)
    scans = db.list_scans(db.connect())
    assert len(scans) == 1 and scans[0]["source"] == "mock"
    assert scans[0]["job_count"] == 5 and scans[0]["surviving_count"] == 2  # 3 of 5 gated by default
    r = c.get("/history")
    assert "mock" in r.text and "History" in r.text
