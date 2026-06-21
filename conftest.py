# Empty root conftest so pytest puts the project root on sys.path,
# making `import app` and `import tests.fixtures...` resolve reliably.
import pytest


@pytest.fixture(autouse=True)
def _no_live_claude(monkeypatch):
    # Keep the suite hermetic: never make a real Anthropic API call even if the
    # developer's shell has ANTHROPIC_API_KEY set. Tests that exercise the Claude
    # path opt in explicitly by monkeypatching the key and the judge.
    import app.config as config
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "", raising=False)
