from __future__ import annotations
from app.models import NormalizedJob, Evaluation
from app.scoring.classifier import classify_job
from app.scoring.filters import evaluate_gates
from app.scoring.rubric import score_job, classify_band
from app.analysis.explainer import get_explainer


def evaluate_job(job: NormalizedJob, profile, settings: dict,
                 explainer_name: str = "deterministic") -> Evaluation:
    cls = classify_job(job, profile)
    gate = evaluate_gates(job, cls, profile, settings)
    score = score_job(job, cls, profile)
    category = classify_band(score.final_score, gate, profile)
    text = get_explainer(explainer_name).explain(job, cls, gate, score, category)
    return Evaluation(classification=cls, gate_result=gate, score=score,
                      category=category, explanation_text=text, profile_version=profile.version)
