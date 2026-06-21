from app.profile import load_profile
from app.scoring import signals
from tests.fixtures.sample_jobs import STRONG, THIN

P = load_profile()


def test_count_hits_distinct_and_case_insensitive():
    assert signals.count_hits("Build BUILD build", ["build"]) == 1
    assert signals.count_hits("ticket queue triage", ["ticket", "triage"]) == 2


def test_favorable_hits_for_strong_job():
    hits = signals.favorable_hits(STRONG, P)
    assert hits["ai_platform_relevance"] >= 3
    assert hits["build_intensity"] >= 1


def test_thin_job_has_few_hits():
    assert sum(signals.favorable_hits(THIN, P).values()) == 0
