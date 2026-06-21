import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILE_PATH = BASE_DIR / "career_profile.yaml"
DATA_DIR = BASE_DIR / "data"
# Defaults to data/career_intelligence.db; override with CI_DB_PATH (handy for demos/tests).
DB_PATH = Path(os.environ.get("CI_DB_PATH", str(DATA_DIR / "career_intelligence.db")))

# Load a local .env (if present) so API keys can be set without exporting env vars.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

# Phase 1: deterministic only. No live API. Selects the explanation provider.
EXPLANATION_PROVIDER = "deterministic"

# Phase 2 keyword-search provider keys (optional). The three free boards need none.
JSEARCH_API_KEY = os.environ.get("JSEARCH_API_KEY", "")
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")

# Local server port. Override with CI_PORT in .env if it conflicts with another tool.
PORT = int(os.environ.get("CI_PORT", "8900"))

# Optional Claude analysis layer (Phase 3). When ANTHROPIC_API_KEY is set, Claude reads
# each surviving job and judges real remote status + skill-fit. Off = pure deterministic.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# Cheap, capable classification model by default; override for sharper (pricier) judgment.
CLAUDE_MODEL = os.environ.get("CI_CLAUDE_MODEL", "claude-haiku-4-5")
# Safety cap on how many jobs Claude judges per search (controls cost/latency).
CLAUDE_MAX_PER_SEARCH = int(os.environ.get("CI_CLAUDE_MAX_PER_SEARCH", "25"))
