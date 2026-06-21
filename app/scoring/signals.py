from __future__ import annotations


def count_hits(text: str, keywords: list[str]) -> int:
    low = (text or "").lower()
    return sum(1 for kw in keywords if kw.lower() in low)


def present(text: str, keywords: list[str]) -> bool:
    return count_hits(text, keywords) > 0


def favorable_hits(text: str, profile) -> dict:
    return {dim: count_hits(text, kws) for dim, kws in profile.favorable_signals.items()}
