from app.profile import load_profile
from app.models import NormalizedJob
from app.scoring.classifier import classify_job
from tests.fixtures.sample_jobs import STRONG, HELPDESK, UNKNOWN_ARR, THIN

P = load_profile()


def J(desc, **kw):
    return NormalizedJob(title=kw.pop("title", "Role"), company_name="C", description=desc, **kw)


def test_fully_remote_scores_15():
    c = classify_job(J(STRONG), P)
    assert c.work_arrangement == "fully_remote" and c.remote_fit_points == 15
    assert c.verify_remote is False


def test_on_site_scores_0():
    c = classify_job(J(HELPDESK), P)
    assert c.work_arrangement == "on_site" and c.remote_fit_points == 0


def test_unknown_arrangement_default_5_and_verify_flag():
    c = classify_job(J(UNKNOWN_ARR), P)
    assert c.work_arrangement == "unknown" and c.remote_fit_points == 5 and c.verify_remote is True


def test_locked_override_wins_over_text():
    # an explicit MANUAL override is authoritative even against on-site text
    c = classify_job(J(HELPDESK, work_arrangement="fully_remote", arrangement_locked=True), P)
    assert c.work_arrangement == "fully_remote" and c.remote_fit_points == 15


def test_provider_remote_hint_overridden_by_onsite_text():
    # an UNLOCKED provider "remote" hint loses to explicit on-site language
    c = classify_job(J(HELPDESK, work_arrangement="fully_remote"), P)
    assert c.work_arrangement == "on_site" and c.remote_fit_points == 0


def test_evidence_confidence_high_for_complete_posting():
    assert classify_job(J(STRONG), P).evidence_confidence == "High"


def test_evidence_confidence_low_for_thin_posting():
    assert classify_job(J(THIN), P).evidence_confidence == "Low"


def test_work_mix_sums_to_100_when_signals_present():
    c = classify_job(J(STRONG), P)
    assert sum(c.work_mix.values()) == 100
