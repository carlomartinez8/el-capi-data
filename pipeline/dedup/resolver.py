"""
Deduplication resolver — takes ingested DataFrames from multiple sources,
finds duplicates via matcher, and produces a single canonical player list.

Strategy:
  1. Start with Transfermarkt as the base (richest metadata).
  2. For each static_squad player, find best TM match → merge or add.
  3. Merge rules: TM wins for metadata (DOB, height, market value),
     static_squad wins for WC squad membership and jersey numbers.
  4. Unmatched static_squad players are added as new rows.
  5. Produce a QA report of uncertain matches for human review.
"""

import pandas as pd
from tqdm import tqdm
from pipeline.dedup.matcher import compute_match_score, normalize_name

AUTO_MERGE_THRESHOLD = 85
REVIEW_THRESHOLD = 70

# ── WC team → nationality plausibility ────────────────────────────
# Maps 3-letter WC team codes to accepted nationality strings (lowercase,
# unidecoded). Most teams only field citizens, but a few have dual-nationality
# edge cases. This is a safety net — if a TM player's nationality doesn't
# appear in the set for the static squad player's WC team, auto-merge is
# blocked and the match goes to review instead.
#
# We only need entries for the 48 WC teams. A missing team code means
# "skip the check" (fail-open), so we don't block legitimate merges for
# teams we forgot to add.

_WC_TEAM_NATIONALITIES: dict[str, set[str]] = {}  # populated lazily

def _load_team_nationalities() -> dict[str, set[str]]:
    """Build the team→nationalities map on first use."""
    if _WC_TEAM_NATIONALITIES:
        return _WC_TEAM_NATIONALITIES

    # Format: team_code → set of accepted nationality strings (lowercase)
    # Using broad matching: "cote divoire" covers "Ivory Coast" / "Côte d'Ivoire"
    _raw: dict[str, list[str]] = {
        "ARG": ["argentina"], "AUS": ["australia"], "BEL": ["belgium"],
        "BOL": ["bolivia"], "BRA": ["brazil"], "CAN": ["canada"],
        "CHI": ["chile"], "CHN": ["china", "china pr"],
        "CIV": ["cote divoire", "ivory coast", "cote d'ivoire"],
        "CMR": ["cameroon"], "COL": ["colombia"], "CRC": ["costa rica"],
        "CRO": ["croatia"], "DEN": ["denmark"], "ECU": ["ecuador"],
        "EGY": ["egypt"], "ENG": ["england"], "ESP": ["spain"],
        "FRA": ["france"], "GER": ["germany"], "GHA": ["ghana"],
        "HAI": ["haiti"], "HON": ["honduras"], "HUN": ["hungary"],
        "IDN": ["indonesia"], "IRN": ["iran"], "IRQ": ["iraq"],
        "ISR": ["israel"], "ITA": ["italy"], "JAM": ["jamaica"],
        "JPN": ["japan"], "KOR": ["korea republic", "south korea", "korea"],
        "KSA": ["saudi arabia"], "MAR": ["morocco"], "MEX": ["mexico"],
        "NED": ["netherlands", "holland"], "NGA": ["nigeria"],
        "NZL": ["new zealand"], "PAN": ["panama"], "PAR": ["paraguay"],
        "PER": ["peru"], "POL": ["poland"], "POR": ["portugal"],
        "QAT": ["qatar"], "RSA": ["south africa"],
        "SCO": ["scotland"], "SEN": ["senegal"], "SRB": ["serbia"],
        "SUI": ["switzerland"], "TUN": ["tunisia"],
        "URU": ["uruguay"], "USA": ["united states", "usa", "us"],
        "VEN": ["venezuela"], "WAL": ["wales"],
    }
    for code, nats in _raw.items():
        _WC_TEAM_NATIONALITIES[code] = {normalize_name(n) for n in nats}
    return _WC_TEAM_NATIONALITIES


def _nationality_plausible_for_team(nationality: str, wc_team_code: str) -> bool:
    """
    Check if a player's nationality is plausible for a WC team.
    Returns True if plausible or if we can't determine (fail-open).
    """
    if not nationality or not wc_team_code:
        return True  # can't check → fail-open

    teams = _load_team_nationalities()
    accepted = teams.get(wc_team_code.upper())
    if accepted is None:
        return True  # team not in our map → fail-open

    nat_norm = normalize_name(nationality)
    # Check if any accepted nationality is a substring match (handles
    # variations like "Korea Republic" matching "korea")
    for acc in accepted:
        if acc in nat_norm or nat_norm in acc:
            return True
    return False


def _build_lookup_index(df: pd.DataFrame) -> dict[str, list[int]]:
    """Build a name-token index for fast candidate retrieval."""
    index: dict[str, list[int]] = {}
    for idx, row in df.iterrows():
        name = normalize_name(row.get("name", ""))
        tokens = name.split()
        for token in tokens:
            if len(token) >= 3:
                index.setdefault(token, []).append(idx)
    return index


def _find_candidates(player: dict, base_df: pd.DataFrame, index: dict[str, list[int]], max_candidates: int = 20) -> list[int]:
    """Use the token index to find plausible match candidates without N^2 comparison."""
    name = normalize_name(player.get("name", ""))
    tokens = name.split()

    candidate_counts: dict[int, int] = {}
    for token in tokens:
        if len(token) < 3:
            continue
        for idx in index.get(token, []):
            candidate_counts[idx] = candidate_counts.get(idx, 0) + 1

    ranked = sorted(candidate_counts.items(), key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in ranked[:max_candidates]]


def deduplicate(
    tm_df: pd.DataFrame,
    static_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Merge Transfermarkt and static squad data into a single canonical list.

    Returns:
      canonical_df  — the deduplicated player list
      review_df     — uncertain matches (score 70-84) for human QA
    """
    print("\n=== DEDUPLICATION ===")

    canonical = tm_df.copy()
    canonical["wc_team_code"] = None
    canonical["jersey_number"] = None
    canonical["captain"] = False
    canonical["in_wc_squad"] = False
    canonical["match_score"] = None
    canonical["match_reason"] = None

    print(f"  Base: {len(canonical):,} Transfermarkt players")
    print(f"  Matching {len(static_df)} static squad players...")

    index = _build_lookup_index(canonical)
    review_rows = []
    auto_merged = 0
    added_new = 0
    flagged = 0

    for _, sq_player in tqdm(static_df.iterrows(), total=len(static_df), desc="Dedup"):
        sq_dict = sq_player.to_dict()
        candidates = _find_candidates(sq_dict, canonical, index)

        best_score = 0
        best_idx = None
        best_reason = ""

        for c_idx in candidates:
            c_row = canonical.iloc[c_idx].to_dict()
            score, reason = compute_match_score(sq_dict, c_row)
            if score > best_score:
                best_score = score
                best_idx = c_idx
                best_reason = reason

        if best_score >= AUTO_MERGE_THRESHOLD and best_idx is not None:
            # ── Nationality sanity check ──────────────────────────
            # Before auto-merging, verify the TM player's nationality is
            # plausible for the WC team. This catches "Maxwell (BRA)" being
            # merged into CIV's squad slot, or "Ricardo (POR)" into HAI.
            tm_nat = canonical.iloc[best_idx].get("nationality", "")
            sq_team = sq_dict.get("wc_team_code", "")
            if not _nationality_plausible_for_team(tm_nat, sq_team):
                # Downgrade to review — this is almost certainly a false match
                review_rows.append({
                    "static_name": sq_dict.get("name"),
                    "static_team": sq_team,
                    "static_club": sq_dict.get("current_club_name"),
                    "tm_name": canonical.iloc[best_idx]["name"],
                    "tm_source_id": canonical.iloc[best_idx]["source_id"],
                    "tm_club": canonical.iloc[best_idx].get("current_club_name"),
                    "tm_nationality": tm_nat,
                    "score": best_score,
                    "reason": f"nat_block|{best_reason}",
                })
                flagged += 1

                new_row = {
                    "source": "static_squad",
                    "source_id": sq_dict.get("source_id"),
                    "name": sq_dict.get("name"),
                    "position": sq_dict.get("position"),
                    "current_club_name": sq_dict.get("current_club_name"),
                    "wc_team_code": sq_team,
                    "jersey_number": sq_dict.get("jersey_number"),
                    "captain": sq_dict.get("captain", False),
                    "in_wc_squad": True,
                    "match_score": best_score,
                    "match_reason": f"nat_block|tm={canonical.iloc[best_idx]['name']}({tm_nat})|{best_reason}",
                }
                canonical = pd.concat([canonical, pd.DataFrame([new_row])], ignore_index=True)
                continue  # skip the merge, move to next player

            canonical.at[best_idx, "wc_team_code"] = sq_dict.get("wc_team_code")
            canonical.at[best_idx, "jersey_number"] = sq_dict.get("jersey_number")
            canonical.at[best_idx, "captain"] = sq_dict.get("captain", False)
            canonical.at[best_idx, "in_wc_squad"] = True
            canonical.at[best_idx, "match_score"] = best_score
            canonical.at[best_idx, "match_reason"] = best_reason

            if not canonical.at[best_idx, "current_club_name"] and sq_dict.get("current_club_name"):
                canonical.at[best_idx, "current_club_name"] = sq_dict["current_club_name"]

            auto_merged += 1

        elif best_score >= REVIEW_THRESHOLD and best_idx is not None:
            review_rows.append({
                "static_name": sq_dict.get("name"),
                "static_team": sq_dict.get("wc_team_code"),
                "static_club": sq_dict.get("current_club_name"),
                "tm_name": canonical.iloc[best_idx]["name"],
                "tm_source_id": canonical.iloc[best_idx]["source_id"],
                "tm_club": canonical.iloc[best_idx].get("current_club_name"),
                "tm_nationality": canonical.iloc[best_idx].get("nationality"),
                "score": best_score,
                "reason": best_reason,
            })
            flagged += 1

            # Do NOT merge review candidates — add as new and let humans decide
            new_row = {
                "source": "static_squad",
                "source_id": sq_dict.get("source_id"),
                "name": sq_dict.get("name"),
                "position": sq_dict.get("position"),
                "current_club_name": sq_dict.get("current_club_name"),
                "wc_team_code": sq_dict.get("wc_team_code"),
                "jersey_number": sq_dict.get("jersey_number"),
                "captain": sq_dict.get("captain", False),
                "in_wc_squad": True,
                "match_score": best_score,
                "match_reason": f"review|best_tm={canonical.iloc[best_idx]['name']}|{best_reason}",
            }
            canonical = pd.concat([canonical, pd.DataFrame([new_row])], ignore_index=True)

        else:
            new_row = {
                "source": "static_squad",
                "source_id": sq_dict.get("source_id"),
                "name": sq_dict.get("name"),
                "position": sq_dict.get("position"),
                "current_club_name": sq_dict.get("current_club_name"),
                "wc_team_code": sq_dict.get("wc_team_code"),
                "jersey_number": sq_dict.get("jersey_number"),
                "captain": sq_dict.get("captain", False),
                "in_wc_squad": True,
                "match_score": best_score,
                "match_reason": f"no_match|best={best_reason}" if best_reason else "no_candidates",
            }
            canonical = pd.concat([canonical, pd.DataFrame([new_row])], ignore_index=True)
            added_new += 1

    review_df = pd.DataFrame(review_rows) if review_rows else pd.DataFrame()

    nat_blocked = sum(1 for r in review_rows if "nat_block" in r.get("reason", ""))
    print(f"\n  Results:")
    print(f"    Auto-merged:     {auto_merged}")
    print(f"    Flagged review:  {flagged} ({nat_blocked} nationality blocks)")
    print(f"    Added new:       {added_new}")
    print(f"    Canonical total: {len(canonical):,}")

    return canonical, review_df
