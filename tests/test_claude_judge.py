from app.analysis import claude_judge
from app import config


class _Job:
    title = "AI Systems Administrator"
    company_name = "Acme"
    location_raw = None
    description = "Administer enterprise AI platforms."


def test_available_reflects_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    assert claude_judge.available() is False
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-test")
    assert claude_judge.available() is True


def test_judge_returns_none_without_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    assert claude_judge.judge(_Job()) is None


def test_judge_schema_shape():
    s = claude_judge.JUDGE_SCHEMA
    assert s["required"] == ["remote", "fit", "score", "reason"]
    assert s["additionalProperties"] is False


def test_extract_returns_none_without_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    assert claude_judge.extract("some pasted posting text") is None
