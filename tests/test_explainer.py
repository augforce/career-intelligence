from app.profile import load_profile
from app.models import NormalizedJob
from app.scoring.classifier import classify_job
from app.scoring.filters import evaluate_gates
from app.scoring.rubric import score_job, classify_band
from app.analysis.explainer import get_explainer
from app.db import DEFAULT_SETTINGS
from tests.fixtures.sample_jobs import STRONG, HIGH_BUT_ONSITE

P = load_profile()


def build(desc, title="Role"):
    job = NormalizedJob(title=title, company_name="C", description=desc)
    cls = classify_job(job, P)
    gr = evaluate_gates(job, cls, P, dict(DEFAULT_SETTINGS))
    sc = score_job(job, cls, P)
    cat = classify_band(sc.final_score, gr, P)
    return job, cls, gr, sc, cat


def test_explains_strong_match_mentions_score_and_remote():
    job, cls, gr, sc, cat = build(STRONG)
    text = get_explainer("deterministic").explain(job, cls, gr, sc, cat)
    assert str(sc.final_score) in text and "remote" in text.lower()
    assert "estimate" in text.lower()  # work-mix labeled as estimate


def test_explains_exclusion_loudly_for_high_score_but_gated():
    job, cls, gr, sc, cat = build(HIGH_BUT_ONSITE, title="AI Platform Engineer")
    text = get_explainer("deterministic").explain(job, cls, gr, sc, cat)
    assert "EXCLUDED" in text and str(sc.raw_score) in text
