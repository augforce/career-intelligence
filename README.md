# Career Intelligence

A job-fit analysis tool. Give it a job posting — paste the whole thing, import it by hand, or pull
results from job-board search — and it scores how well the role matches a **configurable target-role
profile**, sorts it into **Strong Match / Bridge Role / Stretch Role / Poor Fit**, and explains every
verdict in plain English.

The scoring engine is **fully deterministic and runs with no API key**: it reads keyword signals from
the posting, applies hard gates and a weighted rubric defined entirely in `career_profile.yaml`, and
returns a transparent 0–100 score with a breakdown. An **optional Claude layer** (active only when an
Anthropic API key is present) reads the posting in context and produces a headline fit verdict.

This repository ships **calibrated to a sample "AI Systems Administrator" target profile** as a worked
example — a profile that favors administering and operating enterprise AI platforms (identity/access,
provisioning, integrations, enablement, operational support) over building them as a software
engineer. Re-point the tool at any role by editing `career_profile.yaml`; no code changes are needed.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python -m app.main          # serves on http://127.0.0.1:8900
```

The port defaults to **8900**. To change it, set `CI_PORT` in a local `.env` (e.g. `CI_PORT=8901`).
Starting with a bare `uvicorn app.main:app` instead would fall back to port 8000 — use the launcher
above so the configured port is honored.

## How scoring works

### Deterministic baseline (always on, no key required)

1. **Hard gates** (separate from scoring) exclude roles *dominated* by on-site/hybrid arrangements,
   helpdesk/ticket support, CRM/SaaS-admin, sales/customer-success, or traditional senior-SWE work.
   A gated role is **Poor Fit regardless of its raw score**, and the card states why. Gates fire only
   on documented dominance thresholds — never on a mere mention of a term.
2. **Weighted score (0–100)** across seven dimensions — AI-platform relevance 26, current strengths
   20, enablement fit 16, remote fit 15, build intensity 13, developer proximity 5, career
   progression 5 — minus transparent penalties, clamped to 0–100.
3. **Bands:** Strong ≥75, Bridge ≥60, Stretch ≥45, else Poor Fit.

All of these rules live in `career_profile.yaml` — edit the weights (which must sum to 100),
`signal_saturation`, keyword lists, penalties, gates, and bands there.

### Optional Claude layer (set `ANTHROPIC_API_KEY`)

When an Anthropic API key is configured, postings are also read by Claude, which judges the role's
real remote status and skill-fit. **Claude's fit verdict becomes the headline score**; the
deterministic keyword score is kept alongside it as a footnote so both are visible. The layer is
strictly additive: with no key, the deterministic result stands and the app behaves identically.
Set the model with `CI_CLAUDE_MODEL` (default `claude-haiku-4-5`).

## Adding a job

- **Paste a posting** — drop an entire job description into the box on the home page. With the Claude
  layer on, it extracts the title/company/location and returns a fit verdict in a few seconds.
- **Import by hand** — explicit fields (title, company, description required; URL / location / work
  arrangement optional). A provided application URL is stored as a link and **never fetched**.
- **Search job boards** — keyword + location search fans out across every enabled source,
  de-duplicates, scores each result, and hides poor-fit roles. A per-source status line reports what
  each board returned.
- **Run mock scan** loads bundled sample jobs for a quick offline demo.

The jobs list always shows just the latest evaluation — each paste, import, or search replaces the
previous results, so nothing piles up. A **Clear** button on the home page wipes the list and the
scan History whenever you want (your Filters and Watchlist are kept).

Open any job for the full **score breakdown**, estimated work mix, evidence confidence, the Claude
verdict (if present), and any **EXCLUDED** reason. Mark save / reject / applied and add notes;
**History** records each scan and how many jobs survived the hard filters.

## Search sources & API keys

Three sources are **free and need no key**: Remotive, RemoteOK, Arbeitnow. Two broader sources use
free keys you add to a local `.env` (gitignored — copy `.env.example` to `.env`):

- **JSearch** — Google for Jobs (covers LinkedIn / Indeed / Glassdoor / ZipRecruiter indirectly). Free
  tier is 200 searches/month; set `JSEARCH_API_KEY`. The search page shows usage as you approach 200.
- **Adzuna** — broad US listings + salary. Free registration; set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.

LinkedIn and Indeed have no open search API; their listings are reached only indirectly through
JSearch (Google for Jobs), never by scraping.

## Calibrating to a different role

Everything that defines "a good match" lives in `career_profile.yaml`:

- `weights` — the seven scoring dimensions (must sum to 100).
- `favorable_signals` — keyword lists that raise each dimension; `signal_saturation` sets how many
  distinct hits max a dimension out (lower = more generous).
- `penalty_signals` and `gates` — push wrong-lane roles down or exclude them outright.
- `bands` — the Strong / Bridge / Stretch cutoffs.

When the Claude layer is enabled, its targeting lives in the `SYSTEM` prompt in
`app/analysis/claude_judge.py`.

## Test & troubleshoot

- `pytest -q` runs the full suite. No test touches the network or makes a live Claude call (providers
  are mocked; an autouse fixture clears the API key).
- Weights in `career_profile.yaml` must sum to 100 (validated on load).
- **Too few roles clear into Bridge/Strong?** Broaden `favorable_signals`, or lower
  `signal_saturation` / the `bands` thresholds.
- **Too many off-target roles ranking high?** Tighten `penalty_signals` (e.g. `web_dev`,
  `sales_customer`) or the gate keyword lists.
- Reset all data by deleting `data/career_intelligence.db` (recreated on next run).
