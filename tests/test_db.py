import sqlite3
from app import db
from app.models import NormalizedJob, Evaluation, Classification, GateResult, ScoreResult


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    db.init_db(c)
    return c


def _eval():
    return Evaluation(
        classification=Classification(work_arrangement="fully_remote", remote_fit_points=15,
            verify_remote=False, work_mix={"building": 50, "platform_admin": 30, "enablement": 20, "support": 0},
            evidence_confidence="High"),
        gate_result=GateResult(excluded=False, gates=[], reasons=[]),
        score=ScoreResult(raw_score=80, final_score=80, breakdown={"build_intensity": 22}, penalties={}),
        category="strong_match", explanation_text="Fits well.", profile_version=1)


def test_insert_job_and_eval_then_read_back():
    c = _conn()
    jid = db.insert_job(c, NormalizedJob(title="AI Platform Eng", company_name="Acme",
                                         description="d", dedupe_hash="h1"))
    db.insert_evaluation(c, jid, _eval())
    rows = db.get_jobs_with_eval(c)
    assert len(rows) == 1 and rows[0]["category"] == "strong_match"
    assert rows[0]["final_score"] == 80


def test_decision_upsert_overwrites():
    c = _conn()
    jid = db.insert_job(c, NormalizedJob(title="t", company_name="c", description="d", dedupe_hash="h2"))
    db.upsert_decision(c, jid, "saved", "note A")
    db.upsert_decision(c, jid, "applied", "note B")
    detail = db.get_job_detail(c, jid)
    assert detail["status"] == "applied" and detail["notes"] == "note B"


def test_company_crud_and_settings_roundtrip():
    c = _conn()
    cid = db.add_company(c, "Acme", "greenhouse", "https://acme.com/careers", "watch", True)
    assert db.list_companies(c)[0]["name"] == "Acme"
    db.update_company(c, cid, active=False)
    assert db.list_companies(c)[0]["active"] == 0
    db.save_settings(c, {"include_hybrid": True, "max_travel_pct": 10})
    assert db.get_settings(c)["include_hybrid"] is True


def test_clear_jobs_wipes_jobs_evals_decisions():
    c = _conn()
    jid = db.insert_job(c, NormalizedJob(title="t", company_name="c", description="d", dedupe_hash="h9"))
    db.insert_evaluation(c, jid, _eval())
    db.upsert_decision(c, jid, "saved", "n")
    db.clear_jobs(c)
    assert db.get_jobs_with_eval(c) == []


def test_clear_jobs_also_wipes_claude_verdicts():
    # Row IDs get reused after a wipe, so a stale verdict must not survive to
    # attach itself to a future job that happens to land on the same id.
    c = _conn()
    jid = db.insert_job(c, NormalizedJob(title="t", company_name="c", description="d", dedupe_hash="h10"))
    db.insert_evaluation(c, jid, _eval())
    db.save_claude_verdict(c, jid, "remote", "bridge", 68, "reason", "claude-haiku-4-5")
    db.clear_jobs(c)
    assert c.execute("SELECT COUNT(*) FROM claude_verdicts").fetchone()[0] == 0


def test_clear_scans_wipes_history():
    c = _conn()
    db.record_scan(c, "mock", 5, 2)
    assert len(db.list_scans(c)) == 1
    db.clear_scans(c)
    assert db.list_scans(c) == []


def test_get_settings_backfills_new_keys():
    import json as _j
    c = _conn()
    # An old settings row saved before "sources" existed must still get sources.
    c.execute("INSERT INTO settings(id,json) VALUES(1,?)", (_j.dumps({"include_hybrid": True}),))
    c.commit()
    s = db.get_settings(c)
    assert s["include_hybrid"] is True
    assert s["sources"]["jsearch"] is True and s["sources"]["remoteok"] is True
