from __future__ import annotations
from typing import Protocol
from app.models import NormalizedJob, Classification, GateResult, ScoreResult

_CATEGORY_LABEL = {"strong_match": "Strong Match", "bridge_role": "Bridge Role",
                   "stretch_role": "Stretch Role", "poor_fit": "Poor Fit / Exclude"}


class ExplanationProvider(Protocol):
    def explain(self, job: NormalizedJob, classification: Classification,
                gate_result: GateResult, score: ScoreResult, category: str) -> str: ...


class DeterministicExplainer:
    """Phase 1 explainer: composes prose from the structured evaluation. No network."""

    def explain(self, job, classification, gate_result, score, category) -> str:
        lines = []
        if gate_result.excluded:
            lines.append(f"Raw score {score.raw_score} — EXCLUDED ({_CATEGORY_LABEL[category]}).")
            lines.append("Disqualifying gate(s): " + "; ".join(gate_result.reasons))
        else:
            lines.append(f"{_CATEGORY_LABEL[category]} — fit score {score.final_score}/100.")
        # Top positive contributors
        top = sorted(score.breakdown.items(), key=lambda kv: kv[1], reverse=True)[:3]
        lines.append("Strongest fit: " + ", ".join(f"{k} ({v})" for k, v in top if v > 0) + ".")
        # Remote
        lines.append(f"Work arrangement: {classification.work_arrangement.replace('_', ' ')} "
                     f"(remote-fit {classification.remote_fit_points}/15).")
        if classification.verify_remote:
            lines.append("Verify remote status — arrangement not stated in the posting.")
        # Penalties / heaviness
        if score.penalties:
            lines.append("Concerns (penalties): " +
                         ", ".join(f"{k} (-{v})" for k, v in score.penalties.items()) + ".")
        # Work mix (always labeled estimate)
        wm = classification.work_mix
        lines.append("Estimated work mix — "
                     f"building {wm['building']}%, platform/admin {wm['platform_admin']}%, "
                     f"enablement {wm['enablement']}%, support {wm['support']}%.")
        # Trajectory
        advances = score.breakdown.get("career_progression", 0) > 0 and not gate_result.excluded
        lines.append("Moves you toward applied AI engineering: " + ("yes." if advances else "no/unclear."))
        lines.append(f"Evidence confidence: {classification.evidence_confidence}.")
        return "\n".join(lines)


def get_explainer(name: str = "deterministic") -> ExplanationProvider:
    if name == "deterministic":
        return DeterministicExplainer()
    raise ValueError(f"Unknown explanation provider: {name!r}")
