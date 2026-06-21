import io
import json
from app.providers import http
from app.providers.search_base import SearchParams, matches_keywords


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_get_json_encodes_params_and_parses(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["ua"] = req.headers.get("User-agent")
        return _Resp(json.dumps({"ok": True}).encode())

    monkeypatch.setattr(http.urllib.request, "urlopen", fake_urlopen)
    out = http.get_json("https://example.com/api", params={"q": "ai platform", "n": 2})
    assert out == {"ok": True}
    assert "q=ai+platform" in captured["url"] and "n=2" in captured["url"]
    assert captured["ua"]  # User-Agent header set


def test_matches_keywords_whole_word_and_all_tokens():
    assert matches_keywords("Senior AI Platform Engineer", "ai platform") is True
    assert matches_keywords("Frontend Developer", "ai platform") is False
    assert matches_keywords("anything", "") is True
    # whole-word: "ai" must not match inside "available"/"maintain"
    assert matches_keywords("Position available to maintain systems", "ai") is False
    assert matches_keywords("We use AI heavily", "ai") is True


def test_search_params_defaults():
    p = SearchParams(query="ai platform")
    assert p.location == "United States" and p.remote_only is True and p.limit == 10
