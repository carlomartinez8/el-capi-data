"""
Fuzzy matching engine for cross-source player deduplication.

Matching signals (in priority order):
  1. Exact name + DOB  → almost certain match
  2. Fuzzy name + DOB  → high confidence
  3. Fuzzy name + club + nationality → medium-high confidence
  4. Fuzzy name + position + nationality → lower confidence (flagged for review)
"""

import math
from unidecode import unidecode
from thefuzz import fuzz


def _safe_str(val) -> str:
    """Convert any value to a clean string, handling NaN/None gracefully."""
    if val is None:
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    return str(val)


def normalize_name(name) -> str:
    """Lowercase, strip accents, remove punctuation for comparison."""
    s = _safe_str(name)
    if not s:
        return ""
    return unidecode(s).lower().strip().replace("-", " ").replace("'", "")


def name_similarity(a: str, b: str) -> int:
    """Score 0-100 between two player names using multiple strategies."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0

    if na == nb:
        return 100

    token_sort = fuzz.token_sort_ratio(na, nb)
    token_set = fuzz.token_set_ratio(na, nb)
    partial = fuzz.partial_ratio(na, nb)

    return max(token_sort, token_set, partial)


def _is_generic_name(name: str) -> bool:
    """
    Detect 'generic' names that are high collision risk across nationalities.
    Single-token names (Maxwell, Ricardo, Neymar) or very short names (<=6 chars)
    are prone to false cross-nationality matches.
    """
    n = normalize_name(name)
    tokens = n.split()
    return len(tokens) <= 1 or len(n) <= 6


def compute_match_score(row_a: dict, row_b: dict) -> tuple[int, str]:
    """
    Compute a confidence score (0-100) and reason string for a candidate match.

    Returns (score, reason) where score >= 85 is auto-merge, 70-84 is flagged
    for review, and < 70 is not a match.
    """
    name_score = name_similarity(row_a.get("name", ""), row_b.get("name", ""))

    if name_score < 60:
        return 0, "name_too_different"

    score = name_score
    reasons = [f"name={name_score}"]

    # Check if either name is generic (single-token / very short) — higher
    # collision risk means we need stronger corroborating signals
    generic = _is_generic_name(row_a.get("name", "")) or _is_generic_name(row_b.get("name", ""))
    if generic:
        reasons.append("generic_name")

    dob_a = _safe_str(row_a.get("date_of_birth"))[:10]
    dob_b = _safe_str(row_b.get("date_of_birth"))[:10]
    if dob_a and dob_b:
        if dob_a == dob_b:
            score = min(100, score + 15)
            reasons.append("dob_exact")
        else:
            score = max(0, score - 20)
            reasons.append("dob_mismatch")

    club_a = normalize_name(row_a.get("current_club_name", ""))
    club_b = normalize_name(row_b.get("current_club_name", ""))
    if club_a and club_b:
        club_sim = fuzz.token_sort_ratio(club_a, club_b)
        if club_sim >= 80:
            score = min(100, score + 8)
            reasons.append(f"club={club_sim}")
        elif club_sim < 40:
            score = max(0, score - 5)

    nat_a = normalize_name(row_a.get("nationality", ""))
    nat_b = normalize_name(row_b.get("nationality", ""))
    if nat_a and nat_b:
        if nat_a == nat_b:
            score = min(100, score + 5)
            reasons.append("nat_match")
        else:
            # Nationality mismatch is a STRONG negative signal for generic names.
            # "Maxwell" (Brazil) ≠ "Maxwell" (Ivory Coast) — these are different people.
            # For multi-token names the old -10 was fine; for single-token names
            # a -10 still left scores at 90 which auto-merged. Now we hard-cap
            # generic name + nat mismatch below the auto-merge threshold.
            if generic:
                score = max(0, score - 35)
                reasons.append("nat_mismatch_generic")
            else:
                score = max(0, score - 10)
                reasons.append("nat_mismatch")

    # Safety net: generic names with NO corroborating evidence (no DOB match,
    # no club match, no nat match) should never auto-merge
    if generic and not any(r in reasons for r in ("dob_exact", "nat_match")):
        score = min(score, 75)  # force into review zone at best
        if "capped_generic" not in reasons:
            reasons.append("capped_generic")

    return score, "|".join(reasons)
