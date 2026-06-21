from __future__ import annotations
from app.models import Classification, NormalizedJob
from app.scoring import signals

# Priority order: more specific arrangements first.
_PRIORITY = ["fully_remote", "remote_with_travel", "hybrid", "on_site", "remote_with_restrictions"]


def _detect_arrangement(text: str, profile) -> str:
    kws = profile.arrangement_keywords
    for label in _PRIORITY:
        if signals.present(text, kws.get(label, [])):
            return label
    return "unknown"


def _remote_fit_points(label: str, text: str, profile) -> int:
    rf = profile.remote_fit
    if label == "unknown":
        return rf["unknown_default"]
    if label == "remote_with_restrictions" and signals.present(text, rf["limited_states_keywords"]):
        return rf["limited_states_points"]
    return rf["bands"].get(label, 0)


def _evidence_confidence(text: str, arrangement_known: bool, profile) -> str:
    facets = profile.evidence_facets
    covered = 0
    covered += 1 if (arrangement_known or signals.present(text, facets["work_arrangement"])) else 0
    covered += 1 if signals.present(text, facets["responsibilities"]) else 0
    covered += 1 if signals.present(text, facets["requirements"]) else 0
    covered += 1 if signals.present(text, facets["team_context"]) else 0
    return "High" if covered == 4 else "Medium" if covered >= 2 else "Low"


def _work_mix(text: str, profile) -> dict:
    fav = signals.favorable_hits(text, profile)
    support_kws = profile.penalty_signals["support_burden"]["keywords"]
    bucket = {}
    for bkt, dims in profile.work_mix_map.items():
        total = 0
        for dim in dims:
            total += signals.count_hits(text, support_kws) if dim == "__support_penalty__" else fav.get(dim, 0)
        bucket[bkt] = total
    grand = sum(bucket.values())
    if grand == 0:
        return {k: 0 for k in bucket}
    pct = {k: round(v * 100 / grand) for k, v in bucket.items()}
    # fix rounding drift so it sums to 100
    drift = 100 - sum(pct.values())
    if drift and pct:
        top = max(pct, key=pct.get)
        pct[top] += drift
    return pct


_REMOTE_CLAIMS = ("fully_remote", "remote_with_restrictions", "remote_with_travel")


def classify_job(job: NormalizedJob, profile) -> Classification:
    text = job.description or ""
    detected = _detect_arrangement(text, profile)
    claim = job.work_arrangement
    locked = getattr(job, "arrangement_locked", False)

    if claim and locked:
        # Explicit manual override is authoritative.
        arrangement = claim
    elif claim:
        # Provider hint: trust it UNLESS the description plainly says on-site/hybrid.
        if claim in _REMOTE_CLAIMS and detected in ("hybrid", "on_site"):
            arrangement = detected
        else:
            arrangement = claim
    else:
        arrangement = detected
    arrangement_known = arrangement != "unknown"
    pts = _remote_fit_points(arrangement, text, profile)
    return Classification(
        work_arrangement=arrangement,
        remote_fit_points=pts,
        verify_remote=(arrangement == "unknown"),
        work_mix=_work_mix(text, profile),
        evidence_confidence=_evidence_confidence(text, arrangement_known, profile))
