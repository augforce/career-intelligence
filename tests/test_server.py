"""The MCP seam (server.run_engine) must call the real deterministic engine and
map its Evaluation onto the server's ScoreResult shape (bucket / score / reasons).

These are offline: no API key, no network, no database — the same guarantee the
deterministic core gives the web app."""
import pytest

pytest.importorskip("fastmcp")  # server.py builds a FastMCP app at import time
from server import run_engine, ScoreResult
from tests.fixtures.sample_jobs import STRONG, HELPDESK


def test_run_engine_maps_strong_posting_to_strong_match():
    # A posting is pasted title-first, like the app's /paste path.
    result = run_engine("AI Platform Operations Specialist\n" + STRONG, "config.yaml")
    assert isinstance(result, ScoreResult)
    assert result.bucket == "Strong Match"
    assert 0 < result.score <= 100          # engine's native 0-100 scale
    assert result.reasons                    # real plain-language factors, not empty
    assert not any("stub result" in r for r in result.reasons)


def test_run_engine_maps_helpdesk_posting_to_poor_fit():
    result = run_engine("Help Desk Technician\n" + HELPDESK, "config.yaml")
    assert result.bucket == "Poor Fit"
