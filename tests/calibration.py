"""Calibration harness: score the labeled set and compare to framework verdicts.

Run as a report:   python -m tests.calibration
Used by:           tests/test_calibration.py (asserts the hard invariants)

This is a regression instrument, not a tuner. It scores every posting in
tests/fixtures/labeled_jobs.py against the live deterministic engine and shows
where the engine's category disagrees with the framework-derived label.
"""
from __future__ import annotations
from app.profile import load_profile
from app.models import NormalizedJob
from app.scoring.classifier import classify_job
from app.scoring.filters import evaluate_gates
from app.scoring.rubric import score_job, classify_band
from tests.fixtures.labeled_jobs import LABELED, LabeledJob

_ORDER = {"strong_match": 3, "bridge_role": 2, "stretch_role": 1, "poor_fit": 0}
_SHORT = {"strong_match": "STRONG", "bridge_role": "bridge", "stretch_role": "stretch", "poor_fit": "POOR"}


def score_one(lj: LabeledJob, profile, settings):
    job = NormalizedJob(title=lj.title, company_name="C", description=lj.description)
    cls = classify_job(job, profile)
    gate = evaluate_gates(job, cls, profile, settings)
    score = score_job(job, cls, profile)
    category = classify_band(score.final_score, gate, profile)
    return score, category, cls


def run():
    profile = load_profile()
    settings = profile.location_defaults
    rows = []
    for lj in LABELED:
        score, category, cls = score_one(lj, profile, settings)
        rows.append({
            "key": lj.key, "adversarial": lj.adversarial,
            "expected": lj.expected, "actual": category,
            "final": score.final_score,
            "platform_pct": cls.work_mix.get("platform_admin", 0),
            "coding_penalty": score.penalties.get("independent_coding", 0),
            "exact": category == lj.expected,
            # "wrong direction" = scored at least one band ABOVE the label (the dangerous error)
            "over": _ORDER[category] > _ORDER[lj.expected],
        })
    return rows


def main():
    rows = run()
    print(f"\n{'key':<24}{'adv':<5}{'expected':<10}{'actual':<10}{'final':>6}{'plat%':>7}{'codePen':>8}  flag")
    print("-" * 82)
    for r in rows:
        flag = "OVER-RANKED" if r["over"] else ("" if r["exact"] else "off-by-band")
        adv = "yes" if r["adversarial"] else ""
        print(f"{r['key']:<24}{adv:<5}{_SHORT[r['expected']]:<10}{_SHORT[r['actual']]:<10}"
              f"{r['final']:>6}{r['platform_pct']:>6}%{r['coding_penalty']:>8}  {flag}")
    exact = sum(1 for r in rows if r["exact"])
    over = [r["key"] for r in rows if r["over"]]
    adv_over = [r["key"] for r in rows if r["over"] and r["adversarial"]]
    print("-" * 74)
    print(f"exact category match: {exact}/{len(rows)}")
    print(f"OVER-RANKED (scored above the framework label): {over or 'none'}")
    print(f"  of which adversarial near-misses: {adv_over or 'none'}")


if __name__ == "__main__":
    main()
