from __future__ import annotations
from app.models import ScoreResult, NormalizedJob, Classification, GateResult
from app.scoring import signals


def _dimension_points(hits: int, weight: int, saturation: int) -> int:
    return min(weight, round(weight * hits / saturation))


def score_job(job: NormalizedJob, cls: Classification, profile) -> ScoreResult:
    text = job.description or ""
    fav = signals.favorable_hits(text, profile)
    sat = profile.signal_saturation
    breakdown = {}
    for dim, weight in profile.weights.items():
        if dim == "remote_fit":
            breakdown[dim] = cls.remote_fit_points
        else:
            breakdown[dim] = _dimension_points(fav.get(dim, 0), weight, sat)
    raw = sum(breakdown.values())

    penalties = {}
    for name, cfg in profile.penalty_signals.items():
        hits = signals.count_hits(text, cfg["keywords"])
        if hits:
            penalties[name] = min(cfg["max"], hits * cfg["per_hit"])
    final = max(0, min(100, raw - sum(penalties.values())))
    return ScoreResult(raw_score=raw, final_score=final, breakdown=breakdown, penalties=penalties)


def classify_band(final_score: int, gate_result: GateResult, profile) -> str:
    if gate_result.excluded:
        return "poor_fit"
    b = profile.bands
    if final_score >= b["strong_match"]:
        return "strong_match"
    if final_score >= b["bridge_role"]:
        return "bridge_role"
    if final_score >= b["stretch_role"]:
        return "stretch_role"
    return "poor_fit"
