from __future__ import annotations
import hashlib
from pydantic import BaseModel

ARRANGEMENTS = ("fully_remote", "remote_with_restrictions", "remote_with_travel",
                "hybrid", "on_site", "unknown")
CATEGORIES = ("strong_match", "bridge_role", "stretch_role", "poor_fit")


def compute_dedupe_hash(title: str, company: str, description: str) -> str:
    norm = "|".join(s.strip().lower() for s in (title, company, description))
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


class NormalizedJob(BaseModel):
    title: str
    company_name: str
    description: str
    application_url: str | None = None
    location_raw: str | None = None
    work_arrangement: str | None = None
    salary_raw: str | None = None
    source: str = "manual"
    date_found: str = ""
    dedupe_hash: str = ""
    # True only for an explicit manual override; providers leave this False so the
    # description can overrule an unreliable "remote" hint from the source.
    arrangement_locked: bool = False


class Classification(BaseModel):
    work_arrangement: str
    remote_fit_points: int
    verify_remote: bool
    work_mix: dict[str, int]
    evidence_confidence: str


class GateResult(BaseModel):
    excluded: bool
    gates: list[str]
    reasons: list[str]


class ScoreResult(BaseModel):
    raw_score: int
    final_score: int
    breakdown: dict[str, int]
    penalties: dict[str, int]


class Evaluation(BaseModel):
    classification: Classification
    gate_result: GateResult
    score: ScoreResult
    category: str
    explanation_text: str
    profile_version: int
