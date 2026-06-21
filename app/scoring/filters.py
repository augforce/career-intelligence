from __future__ import annotations
from app.models import GateResult, NormalizedJob, Classification
from app.scoring import signals

_ROLE_GATES = ("support", "admin", "sales_customer", "traditional_swe")


def _role_gate_fires(title: str, body: str, cfg: dict) -> bool:
    if cfg.get("title_triggers") and signals.present(title, cfg["title_keywords"]):
        return True
    return signals.count_hits(body, cfg["body_keywords"]) >= cfg["body_density_min"]


def evaluate_gates(job: NormalizedJob, cls: Classification, profile, settings: dict) -> GateResult:
    gates, reasons = [], []
    title, body = job.title or "", job.description or ""

    # --- Role dominance gates ---
    for name in _ROLE_GATES:
        if _role_gate_fires(title, body, profile.gates[name]):
            gates.append(name)
            reasons.append(f"Role appears dominated by {name.replace('_', ' ')}.")

    # --- Location gate (unknown is never gated) ---
    loc = profile.gates["location"]
    arr = cls.work_arrangement
    if arr in loc["gated_arrangements"]:
        toggle = {"hybrid": "include_hybrid", "on_site": "include_on_site"}[arr]
        if not settings.get(toggle, False):
            gates.append(f"location:{arr}")
            reasons.append(f"{arr.replace('_', '-')} role; excluded by default (toggle to include).")
    if signals.present(body, loc["relocation_keywords"]):
        gates.append("location:relocation")
        reasons.append("Relocation required.")
    if not settings.get("include_travel", False) and signals.present(body, loc["frequent_travel_keywords"]):
        gates.append("location:frequent_travel")
        reasons.append("Frequent travel required.")

    return GateResult(excluded=bool(gates), gates=gates, reasons=reasons)
