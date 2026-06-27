from __future__ import annotations
from app.models import ScoreResult, NormalizedJob, Classification, GateResult
from app.scoring import signals

# Prominence weighting for favorable signals (centrality, not a flat bag of words).
# A favorable keyword in the title or the opening pitch (first LEAD_CHARS of the
# description) counts in full; one that appears ONLY buried deeper in the body is
# worth BODY_WEIGHT of a hit. This stops a long posting from saturating a heavy
# dimension off two incidental mentions in a single late sub-bullet, without any
# role-specific keyword list. Gates and penalties deliberately keep raw counts
# (signals.count_hits) — they screen on density, not prominence. These are scoring
# policy; they live here as named constants rather than in career_profile.yaml.
LEAD_CHARS = 400
BODY_WEIGHT = 0.5

# Composition / focus rule (framework §0, §2, §5): a role only earns full fit
# credit when AI-platform/build work is genuinely central, not "AI sprinkled onto"
# security, training, or generic admin. FOCUS_DIMS are the dimensions that make a
# role AI-platform/building work; when they are a small share of all favorable
# signal, the whole favorable score is derated toward FOCUS_FLOOR. This catches a
# role whose vocabulary is genuinely *prominent* but *off-target* (which prominence
# weighting alone cannot), using no role-specific keyword list. FOCUS_FULL_SHARE is
# set at the lower edge of genuine target roles (TARGET_ROLE and BRIDGE sit at
# 0.45), approximating §2's "at least half the work" without penalizing the
# candidate's legitimately admin-heavy ideal role. remote_fit is never derated —
# it is a location signal, orthogonal to AI-centrality.
FOCUS_DIMS = ("ai_platform_relevance", "build_intensity")
FOCUS_FULL_SHARE = 0.45
FOCUS_FLOOR = 0.30


def _dimension_points(hits: float, weight: int, saturation: int) -> int:
    return min(weight, round(weight * hits / saturation))


def _focus_factor(fav: dict) -> float:
    """How AI-platform/build-centered the role is, in [FOCUS_FLOOR, 1.0]."""
    total = sum(fav.values())
    if total <= 0:
        return 1.0  # nothing favorable matched; gates/penalties handle these roles
    core_share = sum(fav.get(d, 0.0) for d in FOCUS_DIMS) / total
    return max(FOCUS_FLOOR, min(1.0, core_share / FOCUS_FULL_SHARE))


def score_job(job: NormalizedJob, cls: Classification, profile) -> ScoreResult:
    text = job.description or ""
    fav = signals.favorable_weighted(job.title, text, profile, LEAD_CHARS, BODY_WEIGHT)
    sat = profile.signal_saturation
    focus = _focus_factor(fav)
    breakdown = {}
    for dim, weight in profile.weights.items():
        if dim == "remote_fit":
            breakdown[dim] = cls.remote_fit_points  # location signal, never derated
        else:
            breakdown[dim] = round(_dimension_points(fav.get(dim, 0), weight, sat) * focus)
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
