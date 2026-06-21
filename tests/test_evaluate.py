from app.profile import load_profile
from app.models import NormalizedJob
from app.evaluate import evaluate_job
from app.db import DEFAULT_SETTINGS
from tests.fixtures.sample_jobs import STRONG, HELPDESK, HIGH_BUT_ONSITE, TARGET_ROLE

P = load_profile()
S = dict(DEFAULT_SETTINGS)


def J(d, t="Role"):
    return NormalizedJob(title=t, company_name="C", description=d)


def test_strong_job_is_strong_match():
    ev = evaluate_job(J(STRONG, "AI Platform Operations Specialist"), P, S)
    assert ev.category == "strong_match" and ev.gate_result.excluded is False


def test_helpdesk_is_poor_fit():
    ev = evaluate_job(J(HELPDESK, "Help Desk Technician"), P, S)
    assert ev.category == "poor_fit" and "support" in ev.gate_result.gates


def test_target_ai_sysadmin_role_scores_high_and_not_gated():
    # The user's stated ideal role must land in the top bands and not be gated,
    # even though it requires "5+ years of Systems Administration" (which he has).
    ev = evaluate_job(J(TARGET_ROLE, "AI Systems Administrator"), P, S)
    assert ev.category in ("strong_match", "bridge_role")
    assert ev.gate_result.excluded is False
    assert ev.classification.work_arrangement not in ("hybrid", "on_site")


def test_high_but_onsite_excluded_despite_high_raw():
    ev = evaluate_job(J(HIGH_BUT_ONSITE, "AI Platform Engineer"), P, S)
    assert ev.category == "poor_fit" and ev.score.raw_score >= 45
    assert any(g.startswith("location") for g in ev.gate_result.gates)
