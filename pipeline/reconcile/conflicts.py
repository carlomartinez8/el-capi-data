"""
Conflict Detection — compares sources for each critical field, detects
disagreements, generates reconciliation_report.json and a review CSV.

Conflict severity levels:
  CRITICAL      — current_club, current_league, date_of_birth, nationality
                   Auto-blocks player from publishing until human resolves.
  IMPORTANT     — position, market_value, contract, intl_caps/goals
                   Highest-priority source wins provisionally; flagged for review.
  INFORMATIONAL — height, agent, trophies, photo
                   Auto-resolved to highest-priority source; logged for audit.

Usage:
    python -m pipeline.reconcile.conflicts
    python -m pipeline.reconcile.conflicts --summary
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import OUTPUT_DIR, RECONCILIATION_REPORT, RECONCILIATION_CSV


MERGED_PATH = OUTPUT_DIR / "players_merged.json"

FIELD_SEVERITY: dict[str, str] = {
    "current_club": "CRITICAL",
    "current_league": "CRITICAL",
    "date_of_birth": "CRITICAL",
    "nationality": "CRITICAL",
    "position": "IMPORTANT",
    "market_value_eur": "IMPORTANT",
    "contract_expires": "IMPORTANT",
    "international_caps": "IMPORTANT",
    "international_goals": "IMPORTANT",
    "jersey_number": "IMPORTANT",
    "captain": "IMPORTANT",
    "career_trajectory": "INFORMATIONAL",
    "major_trophies": "INFORMATIONAL",
    "height_cm": "INFORMATIONAL",
    "photo_url": "INFORMATIONAL",
    "agent": "INFORMATIONAL",
}


POSITION_BROAD_TO_SPECIFIC = {
    "fwd": {"centre-forward", "right winger", "left winger", "second striker",
            "attack", "forward", "striker", "fwd"},
    "mid": {"central midfield", "defensive midfield", "attacking midfield",
            "right midfield", "left midfield", "midfield", "mid"},
    "def": {"centre-back", "left-back", "right-back", "defender", "def"},
    "gk": {"goalkeeper", "gk"},
}

CLUB_ALIASES: dict[str, str] = {
    "man united": "manchester united",
    "man city": "manchester city",
    "spurs": "tottenham",
    "wolves": "wolverhampton",
    "hearts": "heart of midlothian",
    "west ham": "west ham united",
    "newcastle": "newcastle united",
    "nottm forest": "nottingham forest",
    "real sociedad": "real sociedad de futbol",
    "atletico madrid": "atletico de madrid",
    "bayern": "bayern munich",
    "inter": "internazionale",
    "ac milan": "associazione calcio milan",
    "psg": "paris saint-germain",
    "barca": "fc barcelona",
}


def _normalize_club(val) -> str | None:
    """Normalize club name for comparison."""
    if val is None:
        return None
    s = str(val).strip().lower()
    for suffix in (" fc", " f.c.", " football club", " s.p.a.", " s.a.",
                    " s.a.s.", " s.c.", " plc", " ltd"):
        s = s.removesuffix(suffix)
    s = s.strip()
    return CLUB_ALIASES.get(s, s) if s else None


def _normalize_position(val) -> str | None:
    """Normalize position to a broad category for comparison."""
    if val is None:
        return None
    s = str(val).strip().lower()
    for broad, specifics in POSITION_BROAD_TO_SPECIFIC.items():
        if s in specifics:
            return broad
    return s


def _normalize_for_comparison(field: str, value) -> str | None:
    """Normalize a field value for comparison."""
    if value is None:
        return None

    if field == "date_of_birth":
        s = str(value).strip()[:10]
        return s if len(s) >= 8 else None

    if field in ("market_value_eur", "height_cm", "international_caps",
                  "international_goals", "jersey_number"):
        try:
            return str(int(float(str(value).replace(",", ""))))
        except (ValueError, TypeError):
            return None

    if field == "captain":
        return str(bool(value)).lower()

    if field in ("career_trajectory", "major_trophies"):
        return None

    if field == "current_club":
        return _normalize_club(value)

    if field == "position":
        return _normalize_position(value)

    s = str(value).strip().lower()
    return s if s else None


def _values_conflict(field: str, val_a, val_b) -> bool:
    """Determine if two non-null values represent a real conflict."""
    norm_a = _normalize_for_comparison(field, val_a)
    norm_b = _normalize_for_comparison(field, val_b)

    if norm_a is None or norm_b is None:
        return False

    if norm_a == norm_b:
        return False

    if field == "current_club":
        if norm_a in norm_b or norm_b in norm_a:
            return False

    if field == "current_league":
        if norm_a in norm_b or norm_b in norm_a:
            return False

    if field in ("market_value_eur",):
        try:
            a, b = int(norm_a), int(norm_b)
            if min(a, b) > 0 and max(a, b) / min(a, b) < 3:
                return False
        except (ValueError, TypeError):
            pass

    if field in ("international_caps", "international_goals"):
        try:
            a, b = int(norm_a), int(norm_b)
            if abs(a - b) <= 10:
                return False
        except (ValueError, TypeError):
            pass

    if field == "height_cm":
        try:
            a, b = int(norm_a), int(norm_b)
            if abs(a - b) <= 3:
                return False
        except (ValueError, TypeError):
            pass

    return True


def detect_conflicts(merged_players: list[dict]) -> dict:
    """
    Analyze merged player data for conflicts.

    Returns the full reconciliation report dict.
    """
    print("=" * 60)
    print("  CONFLICT DETECTION")
    print("=" * 60)

    all_conflicts: list[dict] = []
    missing_critical: list[dict] = []
    stats = {
        "total_players": len(merged_players),
        "clean": 0,
        "with_conflicts": 0,
        "blocked": 0,
        "auto_resolved": 0,
        "by_severity": {"CRITICAL": 0, "IMPORTANT": 0, "INFORMATIONAL": 0},
        "by_field": {},
    }

    critical_fields_for_missing = [
        "current_club", "current_league", "date_of_birth", "nationality", "position",
    ]

    for player in merged_players:
        name = player["name"]
        cid = player["canonical_id"]
        fields = player["fields"]
        player_conflicts = []
        has_critical_conflict = False

        for field, info in fields.items():
            sources = info.get("all_sources", {})
            non_null = {s: v for s, v in sources.items() if v is not None}

            if len(non_null) < 2:
                continue

            norm_values = {}
            for src, val in non_null.items():
                nv = _normalize_for_comparison(field, val)
                if nv is not None:
                    norm_values[src] = nv

            if len(norm_values) < 2:
                continue

            unique_norms = set(norm_values.values())
            if len(unique_norms) <= 1:
                continue

            # Count how many sources agree on each normalized value
            from collections import Counter
            value_counts = Counter(norm_values.values())
            majority_val, majority_count = value_counts.most_common(1)[0]

            # If 2+ sources agree and only 1 disagrees, the dissenter is an
            # outlier — downgrade unless the dissenter is our top-priority source
            priority_order = ["transfermarkt", "static_bios", "static_squads", "gpt_enrichment"]
            top_source = None
            for src in priority_order:
                if src in norm_values:
                    top_source = src
                    break

            is_outlier_only = (majority_count >= 2 and len(norm_values) - majority_count <= 1)
            top_source_is_majority = top_source and norm_values.get(top_source) == majority_val

            if is_outlier_only and top_source_is_majority:
                continue

            # Real conflict detected
            nominal_severity = FIELD_SEVERITY.get(field, "INFORMATIONAL")

            # If the top priority source disagrees with the majority, that's
            # the most important signal — keep the original severity.
            # If the top priority agrees with majority but a lower source
            # disagrees, downgrade the conflict.
            if is_outlier_only and not top_source_is_majority:
                severity = nominal_severity
            elif top_source_is_majority and majority_count >= 2:
                severity = "INFORMATIONAL" if nominal_severity == "CRITICAL" else nominal_severity
            else:
                severity = nominal_severity

            conflict = {
                "field": field,
                "severity": severity,
                "sources": non_null,
                "recommendation": f"{info['value']} ({info['source']} — highest priority)",
                "status": "auto_resolved" if severity == "INFORMATIONAL" else "needs_review",
            }
            player_conflicts.append(conflict)
            stats["by_severity"][severity] += 1
            stats["by_field"][field] = stats["by_field"].get(field, 0) + 1
            if severity == "CRITICAL":
                has_critical_conflict = True
                conflict["status"] = "needs_review"
            elif severity == "INFORMATIONAL":
                stats["auto_resolved"] += 1

        # Missing critical fields
        missing = []
        total_fields = len(critical_fields_for_missing)
        covered = 0
        for field in critical_fields_for_missing:
            if fields.get(field, {}).get("value") is not None:
                covered += 1
            else:
                missing.append(field)
        coverage = covered / total_fields if total_fields > 0 else 0

        if missing:
            missing_critical.append({
                "player": name,
                "canonical_id": cid,
                "wc_team_code": player.get("wc_team_code", ""),
                "missing_critical_fields": missing,
                "coverage_score": round(coverage, 2),
            })

        if player_conflicts:
            stats["with_conflicts"] += 1
            if has_critical_conflict:
                stats["blocked"] += 1
            all_conflicts.append({
                "name": name,
                "canonical_id": cid,
                "wc_team_code": player.get("wc_team_code", ""),
                "source_id": player.get("source_id", ""),
                "blocked": has_critical_conflict,
                "conflicts": player_conflicts,
            })
        else:
            stats["clean"] += 1

    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total_players": stats["total_players"],
        "clean": stats["clean"],
        "with_conflicts": stats["with_conflicts"],
        "blocked": stats["blocked"],
        "auto_resolved": stats["auto_resolved"],
        "by_severity": stats["by_severity"],
        "by_field": stats["by_field"],
        "players": all_conflicts,
        "missing_critical_fields": missing_critical,
    }

    with open(RECONCILIATION_REPORT, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  Wrote report: {RECONCILIATION_REPORT}")

    _write_review_csv(all_conflicts)

    print(f"\n  RESULTS:")
    print(f"    Total players:        {stats['total_players']}")
    print(f"    Clean (no conflicts): {stats['clean']}")
    print(f"    With conflicts:       {stats['with_conflicts']}")
    print(f"    BLOCKED (critical):   {stats['blocked']}")
    print(f"    Auto-resolved:        {stats['auto_resolved']}")
    print(f"\n  By severity:")
    for sev, cnt in stats["by_severity"].items():
        print(f"    {sev:20s}: {cnt}")
    print(f"\n  By field:")
    for field, cnt in sorted(stats["by_field"].items(), key=lambda x: -x[1]):
        sev = FIELD_SEVERITY.get(field, "?")
        print(f"    {field:25s}: {cnt:4d} ({sev})")

    if missing_critical:
        low_coverage = [m for m in missing_critical if m["coverage_score"] < 0.6]
        print(f"\n  Players missing critical fields: {len(missing_critical)}")
        if low_coverage:
            print(f"  Players with <60% coverage: {len(low_coverage)}")
            for m in low_coverage[:5]:
                print(f"    {m['player']} ({m['wc_team_code']}): missing {m['missing_critical_fields']}")

    return report


def _write_review_csv(conflicts: list[dict]):
    """Write a flat CSV for quick human scanning."""
    rows = []
    for player in conflicts:
        for conflict in player["conflicts"]:
            sources_str = " | ".join(
                f"{src}={val}" for src, val in conflict.get("sources", {}).items()
            )
            rows.append({
                "player": player["name"],
                "team": player.get("wc_team_code", ""),
                "field": conflict["field"],
                "severity": conflict["severity"],
                "status": conflict["status"],
                "recommendation": conflict.get("recommendation", ""),
                "sources": sources_str,
                "canonical_id": player["canonical_id"],
            })

    with open(RECONCILIATION_CSV, "w", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    print(f"  Wrote CSV:    {RECONCILIATION_CSV}")


def print_summary():
    """Print a summary of the last reconciliation run."""
    if not RECONCILIATION_REPORT.exists():
        print("No reconciliation report found. Run the merge + conflicts first.")
        return

    with open(RECONCILIATION_REPORT) as f:
        report = json.load(f)

    print(f"\n{'='*60}")
    print(f"  RECONCILIATION SUMMARY (from {report['run_at']})")
    print(f"{'='*60}")
    print(f"  Total: {report['total_players']} | Clean: {report['clean']} | Conflicts: {report['with_conflicts']} | Blocked: {report['blocked']}")
    print(f"\n  CRITICAL conflicts (blocking publish):")
    for p in report.get("players", []):
        if p.get("blocked"):
            crits = [c for c in p["conflicts"] if c["severity"] == "CRITICAL"]
            fields = ", ".join(c["field"] for c in crits)
            print(f"    {p['name']} ({p.get('wc_team_code','')}): {fields}")

    print(f"\n  IMPORTANT conflicts (flagged, highest-priority wins provisionally):")
    count = 0
    for p in report.get("players", []):
        imps = [c for c in p["conflicts"] if c["severity"] == "IMPORTANT"]
        if imps:
            count += 1
            if count <= 10:
                fields = ", ".join(c["field"] for c in imps)
                print(f"    {p['name']} ({p.get('wc_team_code','')}): {fields}")
    if count > 10:
        print(f"    ... and {count - 10} more")


def run_conflicts():
    """Load merged data and run conflict detection."""
    if not MERGED_PATH.exists():
        print("ERROR: No merged data found. Run `python -m pipeline.reconcile.merge` first.")
        sys.exit(1)

    with open(MERGED_PATH) as f:
        merged = json.load(f)

    return detect_conflicts(merged)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--summary" in args:
        print_summary()
    else:
        run_conflicts()
