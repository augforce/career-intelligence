from __future__ import annotations
import json, sqlite3
from app import config
from app.models import NormalizedJob, Evaluation

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, ats_type TEXT, careers_url TEXT,
  notes TEXT, active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS scans(
  id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP, source TEXT,
  params_json TEXT, job_count INTEGER DEFAULT 0, surviving_count INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS jobs(
  id INTEGER PRIMARY KEY, scan_id INTEGER, company_id INTEGER, title TEXT, company_name TEXT,
  location_raw TEXT, work_arrangement TEXT, salary_raw TEXT, description TEXT,
  application_url TEXT, source TEXT, date_found TEXT, dedupe_hash TEXT UNIQUE,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS evaluations(
  id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL, raw_score INTEGER, final_score INTEGER,
  category TEXT, breakdown_json TEXT, work_mix_json TEXT, remote_fit_band INTEGER,
  evidence_confidence TEXT, penalties_json TEXT, gates_json TEXT, excluded INTEGER,
  exclusion_reason TEXT, verify_flags_json TEXT, explanation_text TEXT,
  profile_version INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS decisions(
  job_id INTEGER PRIMARY KEY, status TEXT DEFAULT 'new', notes TEXT DEFAULT '',
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK (id=1), json TEXT);
CREATE TABLE IF NOT EXISTS api_usage(
  provider TEXT, period TEXT, count INTEGER DEFAULT 0, PRIMARY KEY(provider, period));
CREATE TABLE IF NOT EXISTS claude_verdicts(
  job_id INTEGER PRIMARY KEY, remote TEXT, fit TEXT, score INTEGER, reason TEXT, model TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""


def connect(path=None) -> sqlite3.Connection:
    # Read paths from the config module at call time (not import time) so tests
    # can redirect DB_PATH to a temp file via monkeypatch.
    config.DATA_DIR.mkdir(exist_ok=True)
    c = sqlite3.connect(str(path or config.DB_PATH))
    c.row_factory = sqlite3.Row
    init_db(c)
    return c


def init_db(conn) -> None:
    conn.executescript(SCHEMA)
    # Migrate older claude_verdicts tables that predate the score column.
    try:
        conn.execute("ALTER TABLE claude_verdicts ADD COLUMN score INTEGER")
    except Exception:
        pass
    conn.commit()


def insert_job(conn, job: NormalizedJob) -> int:
    cur = conn.execute(
        """INSERT OR IGNORE INTO jobs(scan_id,company_id,title,company_name,location_raw,
           work_arrangement,salary_raw,description,application_url,source,date_found,dedupe_hash)
           VALUES(NULL,NULL,?,?,?,?,?,?,?,?,?,?)""",
        (job.title, job.company_name, job.location_raw, job.work_arrangement, job.salary_raw,
         job.description, job.application_url, job.source, job.date_found, job.dedupe_hash))
    conn.commit()
    if cur.lastrowid:
        conn.execute("INSERT OR IGNORE INTO decisions(job_id) VALUES(?)", (cur.lastrowid,))
        conn.commit()
        return cur.lastrowid
    row = conn.execute("SELECT id FROM jobs WHERE dedupe_hash=?", (job.dedupe_hash,)).fetchone()
    return row["id"]


def record_scan(conn, source: str, job_count: int, surviving_count: int) -> int:
    cur = conn.execute("INSERT INTO scans(source,job_count,surviving_count) VALUES(?,?,?)",
                       (source, job_count, surviving_count))
    conn.commit()
    return cur.lastrowid


def list_scans(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM scans ORDER BY id DESC").fetchall()]


def insert_evaluation(conn, job_id: int, ev: Evaluation) -> int:
    c = ev.classification
    cur = conn.execute(
        """INSERT INTO evaluations(job_id,raw_score,final_score,category,breakdown_json,
           work_mix_json,remote_fit_band,evidence_confidence,penalties_json,gates_json,
           excluded,exclusion_reason,verify_flags_json,explanation_text,profile_version)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (job_id, ev.score.raw_score, ev.score.final_score, ev.category,
         json.dumps(ev.score.breakdown), json.dumps(c.work_mix), c.remote_fit_points,
         c.evidence_confidence, json.dumps(ev.score.penalties), json.dumps(ev.gate_result.gates),
         int(ev.gate_result.excluded), "; ".join(ev.gate_result.reasons),
         json.dumps(["verify_remote"] if c.verify_remote else []),
         ev.explanation_text, ev.profile_version))
    conn.commit()
    return cur.lastrowid


def _latest_eval_subquery() -> str:
    return ("SELECT e.* FROM evaluations e JOIN "
            "(SELECT job_id, MAX(id) mid FROM evaluations GROUP BY job_id) m "
            "ON e.id=m.mid")


def get_jobs_with_eval(conn) -> list[dict]:
    rows = conn.execute(
        f"""SELECT j.*, e.final_score, e.category, e.evidence_confidence, e.excluded,
                   e.exclusion_reason, e.remote_fit_band, d.status, d.notes,
                   cv.reason AS claude_reason, cv.fit AS claude_fit, cv.remote AS claude_remote,
                   cv.score AS claude_score
            FROM jobs j LEFT JOIN ({_latest_eval_subquery()}) e ON e.job_id=j.id
            LEFT JOIN decisions d ON d.job_id=j.id
            LEFT JOIN claude_verdicts cv ON cv.job_id=j.id ORDER BY e.final_score DESC""").fetchall()
    return [dict(r) for r in rows]


def get_job_detail(conn, job_id: int) -> dict:
    row = conn.execute(
        f"""SELECT j.*, e.*, d.status, d.notes,
                   cv.reason AS claude_reason, cv.fit AS claude_fit, cv.remote AS claude_remote,
                   cv.score AS claude_score
            FROM jobs j LEFT JOIN ({_latest_eval_subquery()}) e ON e.job_id=j.id
            LEFT JOIN decisions d ON d.job_id=j.id
            LEFT JOIN claude_verdicts cv ON cv.job_id=j.id WHERE j.id=?""", (job_id,)).fetchone()
    return dict(row) if row else {}


def clear_jobs(conn) -> None:
    """Wipe all jobs, evaluations, and decisions (scan history and settings stay)."""
    conn.execute("DELETE FROM evaluations")
    conn.execute("DELETE FROM decisions")
    conn.execute("DELETE FROM jobs")
    conn.commit()


def update_job_arrangement(conn, job_id, arrangement) -> None:
    conn.execute("UPDATE jobs SET work_arrangement=? WHERE id=?", (arrangement, job_id))
    conn.commit()


def delete_job(conn, job_id) -> None:
    for t in ("evaluations", "decisions", "claude_verdicts"):
        conn.execute(f"DELETE FROM {t} WHERE job_id=?", (job_id,))
    conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    conn.commit()


def save_claude_verdict(conn, job_id, remote, fit, score, reason, model) -> None:
    conn.execute(
        """INSERT INTO claude_verdicts(job_id,remote,fit,score,reason,model) VALUES(?,?,?,?,?,?)
           ON CONFLICT(job_id) DO UPDATE SET remote=excluded.remote, fit=excluded.fit,
           score=excluded.score, reason=excluded.reason, model=excluded.model""",
        (job_id, remote, fit, score, reason, model))
    conn.commit()


def set_eval_category(conn, job_id, category) -> None:
    conn.execute("UPDATE evaluations SET category=? WHERE id=(SELECT MAX(id) FROM evaluations WHERE job_id=?)",
                 (category, job_id))
    conn.commit()


def upsert_decision(conn, job_id, status, notes) -> None:
    conn.execute(
        """INSERT INTO decisions(job_id,status,notes,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP)
           ON CONFLICT(job_id) DO UPDATE SET status=excluded.status, notes=excluded.notes,
           updated_at=CURRENT_TIMESTAMP""", (job_id, status, notes))
    conn.commit()


def add_company(conn, name, ats_type, careers_url, notes, active) -> int:
    cur = conn.execute("INSERT INTO companies(name,ats_type,careers_url,notes,active) VALUES(?,?,?,?,?)",
                       (name, ats_type, careers_url, notes, int(active)))
    conn.commit()
    return cur.lastrowid


def list_companies(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM companies ORDER BY name").fetchall()]


def update_company(conn, cid, **fields) -> None:
    if not fields:
        return
    if "active" in fields:
        fields["active"] = int(fields["active"])
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE companies SET {sets} WHERE id=?", (*fields.values(), cid))
    conn.commit()


def delete_company(conn, cid) -> None:
    conn.execute("DELETE FROM companies WHERE id=?", (cid,))
    conn.commit()


DEFAULT_SETTINGS = {"eligible_states": ["ALL_US"], "include_travel": False,
                    "include_hybrid": False, "include_on_site": False, "max_travel_pct": 0,
                    "sources": {"jsearch": True, "adzuna": True, "remotive": True,
                                "remoteok": True, "arbeitnow": True}}


def increment_usage(conn, provider: str, period: str, n: int = 1) -> None:
    conn.execute(
        """INSERT INTO api_usage(provider,period,count) VALUES(?,?,?)
           ON CONFLICT(provider,period) DO UPDATE SET count=count+?""", (provider, period, n, n))
    conn.commit()


def get_usage(conn, provider: str, period: str) -> int:
    row = conn.execute("SELECT count FROM api_usage WHERE provider=? AND period=?",
                       (provider, period)).fetchone()
    return row["count"] if row else 0


def get_settings(conn) -> dict:
    # Merge stored settings over defaults so newly-added keys (e.g. "sources")
    # are always present, even for rows saved by an older version.
    row = conn.execute("SELECT json FROM settings WHERE id=1").fetchone()
    stored = json.loads(row["json"]) if row else {}
    merged = {**DEFAULT_SETTINGS, **stored}
    merged["sources"] = {**DEFAULT_SETTINGS["sources"], **(stored.get("sources") or {})}
    return merged


def save_settings(conn, settings: dict) -> None:
    merged = {**DEFAULT_SETTINGS, **settings}
    conn.execute("INSERT INTO settings(id,json) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET json=excluded.json",
                 (json.dumps(merged),))
    conn.commit()
