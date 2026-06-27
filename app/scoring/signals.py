from __future__ import annotations


def count_hits(text: str, keywords: list[str]) -> int:
    low = (text or "").lower()
    return sum(1 for kw in keywords if kw.lower() in low)


def present(text: str, keywords: list[str]) -> bool:
    return count_hits(text, keywords) > 0


def favorable_hits(text: str, profile) -> dict:
    return {dim: count_hits(text, kws) for dim, kws in profile.favorable_signals.items()}


def _keyword_weight(kw: str, title_low: str, lead_low: str, body_low: str, body_weight: float) -> float:
    """Credit a keyword by where it lands: full in the title/opening pitch, reduced
    if it only appears buried deep in the body. A keyword present in several zones
    takes its best (highest) zone — prominence is the *most* prominent mention."""
    kw = kw.lower()
    if kw in title_low or kw in lead_low:
        return 1.0
    if kw in body_low:
        return body_weight
    return 0.0


def weighted_hits(title: str, description: str, keywords: list[str],
                  lead_chars: int, body_weight: float) -> float:
    """Prominence-weighted analogue of count_hits for favorable scoring. Distinct
    keywords still each count at most once, but a buried-only mention is worth
    `body_weight` of a prominent one instead of a flat 1. So a long posting that
    merely brushes a dimension in one late sub-bullet no longer saturates it."""
    title_low = (title or "").lower()
    desc_low = (description or "").lower()
    lead_low, body_low = desc_low[:lead_chars], desc_low[lead_chars:]
    return sum(_keyword_weight(kw, title_low, lead_low, body_low, body_weight) for kw in keywords)


def favorable_weighted(title: str, description: str, profile,
                       lead_chars: int, body_weight: float) -> dict:
    return {dim: weighted_hits(title, description, kws, lead_chars, body_weight)
            for dim, kws in profile.favorable_signals.items()}
