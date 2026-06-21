"""Optional Claude analysis layer: reads a job posting and judges real remote status
and skill-fit. Activates only when ANTHROPIC_API_KEY is set; every failure path returns
None so the deterministic result stands and the app never breaks."""
from __future__ import annotations
import json
from app import config

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "remote": {"type": "string", "enum": ["remote", "hybrid", "onsite", "unclear"]},
        "fit": {"type": "string", "enum": ["strong", "bridge", "stretch", "poor"]},
        "score": {"type": "integer"},
        "reason": {"type": "string"},
    },
    "required": ["remote", "fit", "score", "reason"],
    "additionalProperties": False,
}

SYSTEM = (
    "You screen job postings for the candidate, who targets AI Systems Administrator / AI platform "
    "operations & enablement roles. Their lane: administering and operating enterprise AI platforms "
    "(Microsoft Foundry, Azure AI, ChatGPT Enterprise, Copilot), identity/access/SSO/provisioning, "
    "integrations (Microsoft 365, Google Workspace, Okta, Slack), technical enablement, and "
    "operational support, plus some building/automation. They have 15+ years of IT/systems "
    "administration.\n\n"
    "CRITICAL: The candidate is NOT a software engineer. A role whose CORE is software engineering — "
    "writing production code, requiring 'X years of software development', building the product as an "
    "engineer, or depth in algorithms/data structures/distributed systems — is a POOR fit and a LOW "
    "score, EVEN IF it name-drops Azure AI, RBAC, model deployment, or other AI-platform terms. "
    "Titles like 'AI Platform Engineer', 'ML Engineer', 'Software Engineer', 'Backend/Full-Stack "
    "Engineer', or 'Data Scientist' that require building/coding are poor fits. Generic helpdesk/"
    "ticket support, sales/customer-success, and unrelated roles are also poor. Years of SYSTEMS / "
    "SaaS / cloud ADMINISTRATION experience are fine — the candidate has them; only software-"
    "engineering requirements disqualify.\n\n"
    "The candidate wants U.S.-based fully-remote roles only.\n\n"
    "Return only the structured fields:\n"
    "- remote: 'remote' (fully remote, US-eligible), 'hybrid', 'onsite', or 'unclear'. Read the real "
    "text — a specific city with no remote language usually means onsite.\n"
    "- fit: 'strong' (squarely his admin/ops/enablement lane), 'bridge' (adjacent, reachable), "
    "'stretch' (a reach), or 'poor' (engineering/coding-core, helpdesk, sales, or unrelated).\n"
    "- score: 0-100 consistent with fit — strong 80-100, bridge 60-79, stretch 45-59, poor 0-44.\n"
    "- reason: one specific sentence."
)


EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "company": {"type": "string"},
        "location": {"type": "string"},
    },
    "required": ["title", "company", "location"],
    "additionalProperties": False,
}


def available() -> bool:
    return bool(config.ANTHROPIC_API_KEY)


def extract(text: str) -> dict | None:
    """Pull title/company/location out of a pasted job posting. None if unavailable."""
    if not available():
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=300,
            system=("Extract the job title, hiring company, and location from this pasted job "
                    "posting. Use an empty string for any field that isn't present."),
            messages=[{"role": "user", "content": (text or "")[:12000]}],
            output_config={"format": {"type": "json_schema", "schema": EXTRACT_SCHEMA}},
        )
        data = json.loads(next(b.text for b in resp.content if b.type == "text"))
        return data if data.get("title") else None
    except Exception:
        return None


def judge(job) -> dict | None:
    """Return {'remote','fit','reason'} or None (no key, error, or invalid output)."""
    if not available():
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        prompt = (
            f"Title: {job.title}\nCompany: {job.company_name}\n"
            f"Location: {job.location_raw or 'not stated'}\n\n"
            f"Description:\n{(job.description or '')[:6000]}"
        )
        resp = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=400,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
        )
        text = next(b.text for b in resp.content if b.type == "text")
        data = json.loads(text)
        if data.get("remote") not in ("remote", "hybrid", "onsite", "unclear") or \
                data.get("fit") not in ("strong", "bridge", "stretch", "poor"):
            return None
        data["score"] = max(0, min(100, int(data["score"])))
        return data
    except Exception:
        return None
