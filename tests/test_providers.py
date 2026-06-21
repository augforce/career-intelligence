from app.providers.manual import manual_job
from app.providers.mock import MockProvider


def test_manual_job_sets_hash_and_date_no_fetch():
    j = manual_job("AI Platform Eng", "Acme", "Build internal tools", application_url="https://x/apply")
    assert j.dedupe_hash and j.date_found and j.source == "manual"
    assert j.application_url == "https://x/apply"


def test_manual_job_accepts_arrangement_override():
    j = manual_job("R", "C", "desc", work_arrangement="fully_remote")
    assert j.work_arrangement == "fully_remote"


def test_mock_provider_returns_varied_jobs():
    jobs = MockProvider().fetch()
    assert len(jobs) >= 4 and all(j.dedupe_hash for j in jobs)
