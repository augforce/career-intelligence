import sqlite3
from app import db, config
from app.providers import sources, aggregate
from app.providers.search_base import SearchParams, make_job

P = SearchParams(query="ai platform")


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    db.init_db(c)
    return c


def _no_keys(monkeypatch):
    monkeypatch.setattr(config, "JSEARCH_API_KEY", "")
    monkeypatch.setattr(config, "ADZUNA_APP_ID", "")
    monkeypatch.setattr(config, "ADZUNA_APP_KEY", "")


def test_dedup_across_sources_and_statuses(monkeypatch):
    _no_keys(monkeypatch)
    monkeypatch.setattr(sources.RemoteOKProvider, "search",
                        lambda self, p: [make_job("AI Platform Eng", "Acme", "desc", source="remoteok")])
    monkeypatch.setattr(sources.RemotiveProvider, "search",
                        lambda self, p: [make_job("AI Platform Eng", "Acme", "desc", source="remotive")])  # dup hash
    monkeypatch.setattr(sources.ArbeitnowProvider, "search",
                        lambda self, p: [make_job("Other Role", "Beta", "d2", source="arbeitnow")])
    jobs, statuses = aggregate.search_all(P, dict(db.DEFAULT_SETTINGS), _conn())
    assert len(jobs) == 2  # duplicate collapsed
    by = {s["name"]: s for s in statuses}
    assert by["jsearch"]["status"] == "no key" and by["adzuna"]["status"] == "no key"
    assert by["remoteok"]["status"] == "ok"


def test_jsearch_quota_increments(monkeypatch):
    monkeypatch.setattr(config, "JSEARCH_API_KEY", "abc")
    monkeypatch.setattr(config, "ADZUNA_APP_ID", "")
    monkeypatch.setattr(config, "ADZUNA_APP_KEY", "")
    monkeypatch.setattr(sources.JSearchProvider, "search",
                        lambda self, p: [make_job("X", "Y", "z", source="jsearch")])
    for cls in (sources.RemotiveProvider, sources.RemoteOKProvider, sources.ArbeitnowProvider):
        monkeypatch.setattr(cls, "search", lambda self, p: [])
    c = _conn()
    aggregate.search_all(P, dict(db.DEFAULT_SETTINGS), c)
    assert db.get_usage(c, "jsearch", aggregate.current_period()) == 1


def test_one_source_error_does_not_break_search(monkeypatch):
    _no_keys(monkeypatch)

    def boom(self, p):
        raise RuntimeError("network down")
    monkeypatch.setattr(sources.RemoteOKProvider, "search", boom)
    monkeypatch.setattr(sources.RemotiveProvider, "search",
                        lambda self, p: [make_job("ok role", "co", "d", source="remotive")])
    monkeypatch.setattr(sources.ArbeitnowProvider, "search", lambda self, p: [])
    jobs, statuses = aggregate.search_all(P, dict(db.DEFAULT_SETTINGS), _conn())
    by = {s["name"]: s for s in statuses}
    assert by["remoteok"]["status"] == "error" and len(jobs) == 1


def test_toggled_off_source_is_skipped(monkeypatch):
    _no_keys(monkeypatch)
    monkeypatch.setattr(sources.RemoteOKProvider, "search",
                        lambda self, p: [make_job("a", "b", "c", source="remoteok")])
    settings = dict(db.DEFAULT_SETTINGS)
    settings["sources"] = {**settings["sources"], "remoteok": False}
    jobs, statuses = aggregate.search_all(P, settings, _conn())
    by = {s["name"]: s for s in statuses}
    assert by["remoteok"]["status"] == "off"
