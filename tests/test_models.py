from app.models import NormalizedJob, compute_dedupe_hash, ARRANGEMENTS, CATEGORIES


def test_dedupe_hash_is_stable_and_case_insensitive():
    a = compute_dedupe_hash("AI Platform Engineer", "Acme", "Build tools")
    b = compute_dedupe_hash("ai platform engineer ", " acme", " build tools ")
    assert a == b and len(a) == 64


def test_normalized_job_defaults():
    j = NormalizedJob(title="T", company_name="C", description="D")
    assert j.work_arrangement is None and j.source == "manual"


def test_constants():
    assert "unknown" in ARRANGEMENTS and "poor_fit" in CATEGORIES
