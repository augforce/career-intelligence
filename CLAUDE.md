# Career Intelligence — Working Notes for Claude Code

**Purpose:** Local job-fit analyzer. Takes a job posting (pasted, manually imported, or pulled from
keyword search), scores it against `career_profile.yaml` (a configurable target-role profile), sorts
it into Strong / Bridge / Stretch / Poor, and explains every verdict in plain English. An optional
Claude layer adds a headline fit verdict when an Anthropic API key is present.

## Hard constraints (do not violate)

- **The deterministic scorer is the baseline and must run with no API key and no network.** Mock,
  manual import, paste (field fallback), and all keyword scoring work fully offline.
- **The Claude layer is strictly optional and additive.** It activates only when `ANTHROPIC_API_KEY`
  is set (`claude_judge.available()`); every failure path returns `None` so the deterministic result
  stands and the app never breaks. When present, Claude's fit verdict becomes the **headline score**
  and the deterministic keyword score is shown as a footnote.
- **Keyword search is the only board-networked feature**, and all board network goes through one seam
  (`app/providers/http.get_json`). Tests monkeypatch it — no test hits the live network. Manual
  import and paste never fetch the application URL. Every reachable endpoint is disclosed in
  `manifest.json` (`permissions.network`) — any new host must be added there.
- **The MCP server (`server.py`) is fully offline.** Its tools (`score_posting`, `batch_score`) wrap
  only the deterministic core: no network, no database, no API key.
- **Search-source API keys live in `.env`** (gitignored), read via `app/config.py`. The three free
  boards (Remotive, RemoteOK, Arbeitnow) need no key; JSearch/Adzuna activate only when keys are set.
- **Hard gates are separate from scoring** and fire only on documented dominance thresholds in
  `career_profile.yaml` — never on mere mention of Python/engineering/support/admin/enablement.
- **Unknown work arrangement is never gated;** remote-fit = 5/15 + a "Verify remote status" flag.
- **Scoring weights are fixed and sum to 100** (validated on profile load).
- **Tests never make a live Claude call:** an autouse fixture in `conftest.py` clears the key.

## Architecture

FastAPI + Jinja2 + SQLite. Pure-function scoring layer (no DB/web imports):

```
providers/manual, providers/mock                         -> NormalizedJob (offline)
providers/sources (5 adapters) + http.get_json
  + aggregate.search_all (fan-out, dedup, quota)         -> NormalizedJob (network, opt-in)
scoring/signals -> classifier -> filters -> rubric
analysis/explainer (DeterministicExplainer)              # structured eval -> prose
analysis/claude_judge (optional)                         # posting -> {remote, fit, score, reason}
app/evaluate.py   orchestrates deterministic scoring per job
app/db.py         only module that touches SQLite (jobs, evaluations, claude_verdicts, ...)
app/main.py       routes: / /search /import /paste /scan/mock /clear /settings /watchlist /history
server.py         MCP server (FastMCP, stdio): score_posting / batch_score — offline, engine-only
manifest.json     MCP manifest; discloses every reachable endpoint (permissions.network)
```

**Scoring layers (`scoring/rubric.py`).** Two prominence/composition adjustments sit on top of raw
keyword counts, with no role-specific keyword lists: (1) **prominence weighting** — a favorable keyword
in the title or opening pitch (first `LEAD_CHARS`) counts in full, one only buried deep in the body
counts `BODY_WEIGHT` (`signals.weighted_hits`); (2) a **focus factor** — when AI-platform + build work
is a small share of the role's total favorable signal, the whole favorable score is derated toward
`FOCUS_FLOOR` (`_focus_factor`), so a role that only brushes the target work cannot reach the top
bands. Gates and penalties keep raw counts by design.

`_ingest()` runs deterministic scoring + stores the job. `_claude_pass()` runs `claude_judge.judge()`
on top, saves the verdict (incl. `score`) to `claude_verdicts`, and re-categorizes via `_FIT_TO_CAT`.
Both `/import` and `/paste` first wipe the existing jobs (each evaluation replaces the prior one — the
list never piles up), then ingest, Claude-pass, and redirect to `/job/{id}`. `/clear` wipes the jobs
list and scan history on demand (Filters/Watchlist stay); `clear_jobs()` also drops `claude_verdicts`
since row ids are reused after a wipe.

`/paste` is the centerpiece: `claude_judge.extract()` pulls title/company/location out of a pasted
blob (falling back to the first line when Claude is off), then the normal pipeline runs. `/search`
fans one query out to every enabled source, de-dupes by `dedupe_hash`, drops on-site and keyword
poor-fit roles, then runs the Claude pass on the survivors to refine and re-rank them. That pass is
additive: it drops a genuinely on-site role for a remote-only search, but never deletes a vetted role
just for a low fit score. JSearch usage is metered.

`analysis/claude_judge.py` is where the Claude targeting lives (the `SYSTEM` prompt). It uses
structured outputs (`output_config.format`); numeric fields are clamped in code, not the schema.
`analysis/explainer.py` (deterministic prose) remains a swappable interface.

## Commands

- Run: `python -m app.main`  (http://127.0.0.1:8900; override with CI_PORT in .env)
- Test: `pytest -q`
- Enable the Claude layer: set `ANTHROPIC_API_KEY` in `.env` (and optionally `CI_CLAUDE_MODEL`,
  default `claude-haiku-4-5`; `CI_CLAUDE_MAX_PER_SEARCH`, default 25).
- Tune matching: edit `career_profile.yaml` (weights must sum to 100). `signal_saturation` and
  `bands` control generosity; `favorable_signals` add recognized terms; `penalty_signals` (incl.
  `web_dev`, `sales_customer`, and `independent_coding` for from-scratch / solo-authorship coding
  requirements) and `gates` push roles down / exclude them. To retarget the Claude verdict, edit the
  `SYSTEM` prompt in `app/analysis/claude_judge.py`.
- Reset state: delete `data/career_intelligence.db`.

## Testing expectations

Scoring, gates, provider mappings, the aggregator, the Claude judge (mocked), and the web routes are
covered by unit tests; keep them green. The deterministic scorer rewards keyword density, so
calibration lives in `career_profile.yaml`, not in Python. A labeled regression set
(`tests/fixtures/labeled_jobs.py`) with a harness (`python -m tests.calibration`) and category
invariants (`tests/test_calibration.py`) guards the global prominence/focus layers — run it before and
after any tuning. Prefer small vertical slices and frequent commits. Build transparently, not by
vibe-coding; don't add features beyond what's asked.

## Roadmap (not built)

- ATS watchlist provider (Greenhouse/Lever/Ashby) pulling roles from active companies on a watchlist.
