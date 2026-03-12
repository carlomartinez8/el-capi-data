"""
Conflict Review CLI — resolve conflicts interactively or in batch.

Usage:
    # Show summary of unresolved conflicts
    python -m pipeline.reconcile.review --summary

    # Review all critical (blocking) conflicts interactively
    python -m pipeline.reconcile.review --critical

    # Review a specific player
    python -m pipeline.reconcile.review --player "Luis Díaz"

    # Accept TM value for a specific player
    python -m pipeline.reconcile.review --player "Luis Díaz" --accept-tm

    # Accept GPT value for a specific player
    python -m pipeline.reconcile.review --player "Lionel Messi" --accept-gpt

    # Auto-resolve where GPT + squads agree (TM is stale)
    python -m pipeline.reconcile.review --auto-resolve-agreement

    # Auto-resolve all IMPORTANT/INFORMATIONAL (keep highest priority)
    python -m pipeline.reconcile.review --auto-resolve-non-critical

    # Apply resolutions to canonical JSON
    python -m pipeline.reconcile.review --apply
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import OUTPUT_DIR, RECONCILIATION_REPORT


CANONICAL_PATH = OUTPUT_DIR / "players_canonical.json"
RESOLUTIONS_PATH = OUTPUT_DIR / "reconciliation_resolutions.json"


def _load_report() -> dict:
    if not RECONCILIATION_REPORT.exists():
        print("ERROR: No reconciliation report found.")
        print("Run: python -m pipeline.reconcile.merge && python -m pipeline.reconcile.conflicts")
        sys.exit(1)
    with open(RECONCILIATION_REPORT) as f:
        return json.load(f)


def _save_report(report: dict):
    with open(RECONCILIATION_REPORT, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def _load_resolutions() -> dict:
    if RESOLUTIONS_PATH.exists():
        with open(RESOLUTIONS_PATH) as f:
            return json.load(f)
    return {"resolved_at": None, "resolutions": {}}


def _save_resolutions(resolutions: dict):
    resolutions["resolved_at"] = datetime.now(timezone.utc).isoformat()
    with open(RESOLUTIONS_PATH, "w") as f:
        json.dump(resolutions, f, indent=2, ensure_ascii=False)


def show_summary():
    """Print summary of unresolved conflicts."""
    report = _load_report()
    total = report["total_players"]
    blocked_players = [p for p in report.get("players", []) if p.get("blocked")]
    unresolved = [p for p in report.get("players", [])
                  if any(c["status"] == "needs_review" for c in p.get("conflicts", []))]

    print(f"\n{'='*60}")
    print(f"  RECONCILIATION REVIEW SUMMARY")
    print(f"{'='*60}")
    print(f"  Total players: {total}")
    print(f"  Clean: {report.get('clean', 0)}")
    print(f"  Blocked (CRITICAL unresolved): {len(blocked_players)}")
    print(f"  Needing review: {len(unresolved)}")
    print(f"  Auto-resolved: {report.get('auto_resolved', 0)}")

    if blocked_players:
        print(f"\n  BLOCKED PLAYERS (top 20):")
        for p in blocked_players[:20]:
            crits = [c for c in p["conflicts"] if c["severity"] == "CRITICAL" and c["status"] == "needs_review"]
            fields_str = ", ".join(c["field"] for c in crits)
            print(f"    {p['name']:30s} ({p.get('wc_team_code',''):3s}) — {fields_str}")
        if len(blocked_players) > 20:
            print(f"    ... and {len(blocked_players) - 20} more")


def review_player(report: dict, player_name: str, accept_source: str | None = None) -> bool:
    """Review/resolve conflicts for a specific player."""
    found = None
    for p in report.get("players", []):
        if p["name"].lower() == player_name.lower():
            found = p
            break
    if not found:
        for p in report.get("players", []):
            if player_name.lower() in p["name"].lower():
                found = p
                break
    if not found:
        print(f"  Player '{player_name}' not found in conflict report.")
        return False

    print(f"\n  {found['name']} ({found.get('wc_team_code', '')}) — {'BLOCKED' if found.get('blocked') else 'flagged'}")

    resolutions = _load_resolutions()
    cid = found["canonical_id"]

    for conflict in found.get("conflicts", []):
        if conflict["status"] == "auto_resolved":
            continue

        field = conflict["field"]
        severity = conflict["severity"]
        sources = conflict.get("sources", {})

        print(f"\n    [{severity}] {field}:")
        for src, val in sources.items():
            marker = " ◀ RECOMMENDED" if src == conflict.get("recommendation", "").split("(")[-1].replace(")", "").strip().split(" — ")[0] else ""
            val_display = str(val)[:80] + "..." if isinstance(val, str) and len(str(val)) > 80 else str(val)
            print(f"      {src:20s}: {val_display}{marker}")

        if accept_source:
            source_key = {
                "tm": "transfermarkt",
                "transfermarkt": "transfermarkt",
                "gpt": "gpt_enrichment",
                "gpt_enrichment": "gpt_enrichment",
                "bios": "static_bios",
                "static_bios": "static_bios",
                "squads": "static_squads",
                "static_squads": "static_squads",
            }.get(accept_source.lower())

            if source_key and source_key in sources:
                conflict["status"] = "resolved"
                conflict["resolved_value"] = sources[source_key]
                conflict["resolved_source"] = source_key
                conflict["resolved_at"] = datetime.now(timezone.utc).isoformat()
                if cid not in resolutions["resolutions"]:
                    resolutions["resolutions"][cid] = {}
                resolutions["resolutions"][cid][field] = {
                    "value": sources[source_key],
                    "source": source_key,
                }
                print(f"      → Resolved: {source_key} = {sources[source_key]}")
            else:
                print(f"      Source '{accept_source}' not available for this field.")
        else:
            print(f"      Recommendation: {conflict.get('recommendation', 'N/A')}")

    # Update blocked status
    still_blocked = any(
        c["severity"] == "CRITICAL" and c["status"] == "needs_review"
        for c in found.get("conflicts", [])
    )
    found["blocked"] = still_blocked

    _save_report(report)
    _save_resolutions(resolutions)
    return True


def auto_resolve_agreement(report: dict) -> int:
    """
    Auto-resolve conflicts where GPT + squads agree but TM disagrees.
    In these cases, TM data is likely stale and the consensus is correct.
    """
    resolved_count = 0
    resolutions = _load_resolutions()

    for player in report.get("players", []):
        cid = player["canonical_id"]
        for conflict in player.get("conflicts", []):
            if conflict["status"] != "needs_review":
                continue

            sources = conflict.get("sources", {})
            gpt_val = sources.get("gpt_enrichment")
            sq_val = sources.get("static_squads")
            tm_val = sources.get("transfermarkt")

            if not gpt_val or not tm_val:
                continue

            gpt_norm = str(gpt_val).strip().lower()
            sq_norm = str(sq_val).strip().lower() if sq_val else ""
            tm_norm = str(tm_val).strip().lower()

            gpt_sq_agree = sq_val and (gpt_norm in sq_norm or sq_norm in gpt_norm or gpt_norm == sq_norm)

            if gpt_sq_agree and gpt_norm != tm_norm and tm_norm not in gpt_norm:
                conflict["status"] = "resolved"
                conflict["resolved_value"] = gpt_val
                conflict["resolved_source"] = "gpt_enrichment (consensus with static_squads)"
                conflict["resolved_at"] = datetime.now(timezone.utc).isoformat()
                if cid not in resolutions["resolutions"]:
                    resolutions["resolutions"][cid] = {}
                resolutions["resolutions"][cid][conflict["field"]] = {
                    "value": gpt_val,
                    "source": "gpt_enrichment",
                    "reason": "GPT + static_squads consensus over stale TM",
                }
                resolved_count += 1

    # Update blocked status
    for player in report.get("players", []):
        player["blocked"] = any(
            c["severity"] == "CRITICAL" and c["status"] == "needs_review"
            for c in player.get("conflicts", [])
        )

    _save_report(report)
    _save_resolutions(resolutions)
    print(f"  Auto-resolved {resolved_count} conflicts (GPT+squads consensus)")
    return resolved_count


def auto_resolve_non_critical(report: dict) -> int:
    """Auto-resolve all IMPORTANT and INFORMATIONAL conflicts using highest-priority source."""
    resolved_count = 0
    resolutions = _load_resolutions()

    for player in report.get("players", []):
        cid = player["canonical_id"]
        for conflict in player.get("conflicts", []):
            if conflict["status"] != "needs_review":
                continue
            if conflict["severity"] == "CRITICAL":
                continue

            sources = conflict.get("sources", {})
            priority_order = ["transfermarkt", "static_bios", "static_squads", "gpt_enrichment"]
            winner_source = None
            winner_value = None
            for src in priority_order:
                if src in sources and sources[src] is not None:
                    winner_source = src
                    winner_value = sources[src]
                    break

            if winner_source:
                conflict["status"] = "resolved"
                conflict["resolved_value"] = winner_value
                conflict["resolved_source"] = winner_source
                conflict["resolved_at"] = datetime.now(timezone.utc).isoformat()
                if cid not in resolutions["resolutions"]:
                    resolutions["resolutions"][cid] = {}
                resolutions["resolutions"][cid][conflict["field"]] = {
                    "value": winner_value,
                    "source": winner_source,
                    "reason": "auto-resolved: highest priority for non-critical field",
                }
                resolved_count += 1

    _save_report(report)
    _save_resolutions(resolutions)
    print(f"  Auto-resolved {resolved_count} non-critical conflicts (highest priority wins)")
    return resolved_count


def apply_resolutions():
    """
    Apply all resolutions to the canonical JSON file.

    Reads reconciliation_resolutions.json and players_merged.json,
    updates the corresponding fields in players_canonical.json.
    """
    if not RESOLUTIONS_PATH.exists():
        print("ERROR: No resolutions file found. Resolve conflicts first.")
        return

    with open(CANONICAL_PATH) as f:
        canonical = json.load(f)

    resolutions = _load_resolutions()
    res_map = resolutions.get("resolutions", {})

    if not res_map:
        print("  No resolutions to apply.")
        return

    # Build canonical lookup
    canonical_by_id = {p["canonical_id"]: p for p in canonical}

    applied = 0
    for cid, field_resolutions in res_map.items():
        player = canonical_by_id.get(cid)
        if not player:
            continue

        for field, resolution in field_resolutions.items():
            value = resolution["value"]
            _apply_field_to_player(player, field, value)
            applied += 1

    with open(CANONICAL_PATH, "w") as f:
        json.dump(canonical, f, indent=2, ensure_ascii=False)
    print(f"  Applied {applied} field resolutions to {CANONICAL_PATH}")
    print(f"  Affected players: {len(res_map)}")


def _apply_field_to_player(player: dict, field: str, value):
    """Apply a resolved field value to a canonical player record."""
    identity = player.setdefault("identity", {})
    career = player.setdefault("career", {})
    market = player.setdefault("market", {})

    field_to_path = {
        "current_club": (career, "current_club"),
        "current_league": (career, "current_league"),
        "date_of_birth": (identity, "date_of_birth"),
        "nationality": (identity, "nationality_primary"),
        "position": (career, "position_primary"),
        "market_value_eur": (market, "estimated_value_eur"),
        "contract_expires": (career, "contract_expires"),
        "agent": (market, "agent"),
        "international_caps": (career, "international_caps"),
        "international_goals": (career, "international_goals"),
        "jersey_number": (career, "current_jersey_number"),
        "captain": (None, None),
        "major_trophies": (career, "major_trophies"),
        "height_cm": (identity, "height_cm"),
        "photo_url": (identity, "photo_url"),
    }

    target, key = field_to_path.get(field, (None, None))
    if target is not None and key:
        target[key] = value


def main():
    args = sys.argv[1:]
    report = _load_report()

    if "--summary" in args:
        show_summary()
        return

    if "--auto-resolve-agreement" in args:
        auto_resolve_agreement(report)
        show_summary()
        return

    if "--auto-resolve-non-critical" in args:
        auto_resolve_non_critical(report)
        show_summary()
        return

    if "--apply" in args:
        apply_resolutions()
        return

    if "--critical" in args:
        blocked = [p for p in report.get("players", []) if p.get("blocked")]
        print(f"\n  {len(blocked)} blocked players with CRITICAL conflicts:")
        for p in blocked:
            review_player(report, p["name"])
        return

    player_name = None
    accept_source = None
    for i, arg in enumerate(args):
        if arg == "--player" and i + 1 < len(args):
            player_name = args[i + 1]
        if arg == "--accept-tm":
            accept_source = "tm"
        if arg == "--accept-gpt":
            accept_source = "gpt"
        if arg == "--accept-bios":
            accept_source = "bios"
        if arg == "--accept-squads":
            accept_source = "squads"

    if player_name:
        review_player(report, player_name, accept_source)
    else:
        show_summary()


if __name__ == "__main__":
    main()
