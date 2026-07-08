"""
Job-matching engine, exposed over MCP.

Wraps the existing rule-based scoring engine as MCP tools so any MCP client
(Claude Desktop, Claude Code) can call it in natural language.

Run locally:
    pip install fastmcp        # or: uv pip install fastmcp
    python server.py           # serves over stdio

Test before wiring into a client:
    fastmcp dev server.py      # opens the MCP Inspector

Register with Claude Desktop:
    fastmcp install claude-desktop server.py

This skeleton runs end-to-end on a STUB. Confirm the protocol works first,
then replace the one marked seam (`run_engine`) with a call into your real core.

Network disclosure:
    The MCP tools in this file (score_posting, batch_score) and the
    criteria:// resource are fully offline — they make no network calls and
    need no API key. The wider repository also ships a FastAPI web app
    (python -m app.main) whose opt-in keyword search contacts these job
    boards through the single seam app/providers/http.get_json:
    remotive.com, remoteok.com, www.arbeitnow.com (no key), api.adzuna.com
    and jsearch.p.rapidapi.com (only when keys are set in .env). Its optional
    Claude layer contacts api.anthropic.com only when ANTHROPIC_API_KEY is
    set. The full list also lives in manifest.json (permissions.network).
"""

from typing import Literal, Optional
from pathlib import Path

from pydantic import BaseModel, Field
from fastmcp import FastMCP

mcp = FastMCP("job-match")

DEFAULT_CONFIG = "config.yaml"

# The four buckets your engine already produces. Encoded as a type so the
# output schema is self-documenting to the calling model.
Bucket = Literal["Strong Match", "Bridge Role", "Stretch Role", "Poor Fit"]


class ScoreResult(BaseModel):
    """Structured result for a single posting. FastMCP turns this into the
    tool's output schema automatically."""
    bucket: Bucket
    score: float = Field(description="Numeric score from the rule-based core.")
    reasons: list[str] = Field(
        default_factory=list,
        description="Plain-language factors behind the verdict.",
    )


# ---------------------------------------------------------------------------
# INTEGRATION SEAM. Replace the body of this function with a call into your
# real engine. Everything above and below this block stays as-is.
#
# Your engine already: loads a single YAML config, scores against rules,
# returns one of four buckets. Import it and map its output onto ScoreResult.
#
#   from jobmatch.core import score        # <- your actual module
#   def run_engine(posting_text, config_path):
#       raw = score(posting_text, config=config_path)
#       return ScoreResult(bucket=raw.bucket, score=raw.score, reasons=raw.reasons)
# ---------------------------------------------------------------------------
def run_engine(posting_text: str, config_path: str) -> ScoreResult:
    """Score one posting with the real deterministic engine and map its
    Evaluation onto this server's ScoreResult (bucket / score / reasons).

    Fully offline: no network, no database, no API key — the same guarantee the
    deterministic core gives the web app.
    """
    # Imported lazily so the MCP protocol layer above stays importable even if
    # the engine package isn't on the path; the real core lives under app/.
    from app.profile import load_profile
    from app.evaluate import evaluate_job
    from app.providers.manual import manual_job
    from app.db import DEFAULT_SETTINGS

    # The engine's four internal categories -> this server's Bucket labels.
    category_to_bucket = {
        "strong_match": "Strong Match",
        "bridge_role": "Bridge Role",
        "stretch_role": "Stretch Role",
        "poor_fit": "Poor Fit",
    }

    # Use the given config only if it points at a real file; otherwise fall back
    # to the engine's own rubric (career_profile.yaml).
    profile = load_profile(config_path) if Path(config_path).exists() else load_profile()

    # Mirror the web app's /paste path: the whole blob is the description, and the
    # first non-empty line is the title. No scraping, no fetching.
    lines = [ln.strip() for ln in posting_text.splitlines() if ln.strip()]
    title = (lines[0] if lines else "Pasted role")[:160]
    job = manual_job(title, "Unknown", posting_text)

    ev = evaluate_job(job, profile, dict(DEFAULT_SETTINGS))

    # The engine's DeterministicExplainer already writes one plain-language line
    # per factor; split them into the reasons list.
    reasons = [ln for ln in ev.explanation_text.split("\n") if ln.strip()]

    return ScoreResult(
        bucket=category_to_bucket[ev.category],
        score=float(ev.score.final_score),  # engine's native 0-100 scale
        reasons=reasons,
    )
# ---------------------------------------------------------------------------


@mcp.tool
def score_posting(posting_text: str, config_path: Optional[str] = None) -> ScoreResult:
    """Score a single job posting against the configured criteria and return
    its match bucket, numeric score, and the reasons behind the verdict."""
    return run_engine(posting_text, config_path or DEFAULT_CONFIG)


@mcp.tool
def batch_score(
    postings: list[str], config_path: Optional[str] = None
) -> list[ScoreResult]:
    """Score many postings at once. Mirrors the engine's multi-board batch path.
    Returns one result per posting, in the same order."""
    cfg = config_path or DEFAULT_CONFIG
    return [run_engine(p, cfg) for p in postings]


@mcp.resource("criteria://current")
def criteria() -> str:
    """Read-only view of the active scoring rubric (career_profile.yaml) — the
    same file run_engine scores against — so the model can see what it is being
    matched against."""
    from app.config import PROFILE_PATH  # the engine's real, absolute rubric path
    path = Path(PROFILE_PATH)
    if not path.exists():
        return f"No rubric found at {path.resolve()}"
    return path.read_text()


if __name__ == "__main__":
    mcp.run()  # stdio transport
