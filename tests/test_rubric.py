from app.profile import load_profile
from app.models import NormalizedJob, GateResult
from app.scoring.classifier import classify_job
from app.scoring.rubric import score_job, classify_band
from tests.fixtures.sample_jobs import STRONG, HELPDESK

P = load_profile()


def J(desc):
    return NormalizedJob(title="Role", company_name="C", description=desc)


def test_breakdown_keys_match_weights_and_within_caps():
    s = score_job(J(STRONG), classify_job(J(STRONG), P), P)
    assert set(s.breakdown) == set(P.weights)
    for dim, pts in s.breakdown.items():
        assert 0 <= pts <= P.weights[dim]


def test_remote_fit_dimension_uses_classification_points():
    job = J(STRONG)
    s = score_job(job, classify_job(job, P), P)
    assert s.breakdown["remote_fit"] == 15


def test_final_score_clamped_and_penalties_applied():
    job = J(HELPDESK)
    s = score_job(job, classify_job(job, P), P)
    assert 0 <= s.final_score <= 100
    assert s.penalties.get("support_burden", 0) > 0


def test_band_mapping_and_gate_overrides_to_poor_fit():
    assert classify_band(80, GateResult(excluded=False, gates=[], reasons=[]), P) == "strong_match"
    assert classify_band(65, GateResult(excluded=False, gates=[], reasons=[]), P) == "bridge_role"
    assert classify_band(50, GateResult(excluded=False, gates=[], reasons=[]), P) == "stretch_role"
    assert classify_band(30, GateResult(excluded=False, gates=[], reasons=[]), P) == "poor_fit"
    assert classify_band(90, GateResult(excluded=True, gates=["support"], reasons=[]), P) == "poor_fit"
