"""
Apply Verified Updates — Merges verified critical field changes back into canonical data.

Reads:  data/output/verification_diff.json   (changes to apply)
        data/output/players_canonical.json    (current canonical data)
Writes: data/output/players_canonical.json    (updated in-place)
        data/output/verification_applied.json (audit trail of what was applied)

Usage:
    python -m pipeline.verify.apply_updates                          # preview ALL changes
    python -m pipeline.verify.apply_updates --apply                  # apply ALL changes
    python -m pipeline.verify.apply_updates --tier 1                 # preview IMPERDONABLE only
    python -m pipeline.verify.apply_updates --tier 1 --apply         # apply IMPERDONABLE only
    python -m pipeline.verify.apply_updates --field current_club     # only current_club changes
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.config import OUTPUT_DIR

CANONICAL_PATH = OUTPUT_DIR / "players_canonical.json"
DIFF_PATH = OUTPUT_DIR / "verification_diff.json"
APPLIED_LOG = OUTPUT_DIR / "verification_applied.json"

# ─── Map critical fields → their location in the enriched JSON ─────────
# Must match the fields verified in critical_fields.py
FIELD_PATHS = {
    # Tier 1 — Imperdonable
    "current_club":            ("career", "current_club"),
    "current_league":          ("career", "current_league"),
    "nationality_for_wc":      ("identity", "nationality_primary"),   # WC team, not passport
    "position_primary":        ("career", "position_primary"),
    "in_wc_2026_squad":        ("world_cup_2026", "in_squad"),        # new boolean field

    # Tier 2 — Muy importante
    "date_of_birth":           ("identity", "date_of_birth"),
    "estimated_value_eur":     ("market", "estimated_value_eur"),

    # Tier 3 — Importante
    "current_jersey_number":   ("career", "current_jersey_number"),
    "international_caps":      ("career", "international_caps"),
    "international_goals":     ("career", "international_goals"),
    "injury_fitness_status":   ("world_cup_2026", "injury_fitness_status"),
    "contract_expires":        ("career", "contract_expires"),
}

TIER_EMOJI = {1: "🔴", 2: "🟡", 3: "🟢"}
TIER_LABEL = {1: "IMPERDONABLE", 2: "MUY IMPORTANTE", 3: "IMPORTANTE"}


def run_apply(
    do_apply: bool = False,
    field_filter: str | None = None,
    tier_filter: int | None = None,
):
    print("=" * 60)
    print("  EL CAPI — Apply Verified Updates")
    print("=" * 60)

    if not DIFF_PATH.exists():
        print(f"  No diff file found at {DIFF_PATH}")
        print("  Run the verification pipeline first.")
        return

    with open(DIFF_PATH) as f:
        diffs = json.load(f)

    if not diffs:
        print("  No changes to apply — all data verified correct.")
        return

    # Filter by tier if requested
    if tier_filter:
        for d in diffs:
            d["changes"] = [c for c in d["changes"] if c.get("tier") == tier_filter]
        diffs = [d for d in diffs if d["changes"]]
        emoji = TIER_EMOJI.get(tier_filter, "")
        label = TIER_LABEL.get(tier_filter, f"Tier {tier_filter}")
        print(f"  {emoji} Filtered to tier {tier_filter}: {label}")

    # Filter by field if requested
    if field_filter:
        for d in diffs:
            d["changes"] = [c for c in d["changes"] if c["field"] == field_filter]
        diffs = [d for d in diffs if d["changes"]]
        print(f"  Filtered to field: {field_filter}")

    total_changes = sum(len(d["changes"]) for d in diffs)
    t1 = sum(1 for d in diffs for c in d["changes"] if c.get("tier") == 1)
    t2 = sum(1 for d in diffs for c in d["changes"] if c.get("tier") == 2)
    t3 = sum(1 for d in diffs for c in d["changes"] if c.get("tier") == 3)
    fills = sum(1 for d in diffs for c in d["changes"] if c.get("was_missing"))

    print(f"  Players with changes: {len(diffs)}")
    print(f"  Total field changes:  {total_changes}")
    print(f"    🔴 Tier 1 (imperdonable): {t1}")
    print(f"    🟡 Tier 2 (muy importante): {t2}")
    print(f"    🟢 Tier 3 (importante): {t3}")
    print(f"    ⬜ Fields filled (was null): {fills}")
    print()

    # Preview — sorted: tier 1 first
    sorted_diffs = sorted(
        diffs,
        key=lambda d: min((c.get("tier", 3) for c in d["changes"]), default=3),
    )

    shown = 0
    for d in sorted_diffs:
        if shown >= 25:
            break
        name = d.get("name", "?")
        team = d.get("wc_team_code", "")
        for c in d["changes"]:
            tier = c.get("tier", 3)
            emoji = TIER_EMOJI.get(tier, "⬜")
            old = c["old"] if c["old"] not in (None, "") else "NULL"
            new = c["new"] if c["new"] not in (None, "") else "NULL"
            tag = "FILL" if c.get("was_missing") else "UPDATE"
            print(f"  {emoji} [{tag}] {name} [{team}]: {c['field']}: {old} → {new}")
        shown += 1

    remaining = len(sorted_diffs) - shown
    if remaining > 0:
        print(f"  ... and {remaining} more players")

    if not do_apply:
        print(f"\n  PREVIEW ONLY — run with --apply to commit changes")
        if t1 > 0:
            print(f"  💡 Tip: Apply only imperdonables first: --tier 1 --apply")
        return

    # ─── Apply changes to canonical data ────────────────────────────
    print(f"\n  Applying {total_changes} changes to {CANONICAL_PATH}...")

    with open(CANONICAL_PATH) as f:
        players = json.load(f)

    # Index by canonical_id for fast lookup
    player_index = {}
    for p in players:
        cid = p.get("canonical_id") or p.get("source_id")
        player_index[cid] = p

    applied = []
    not_found = []

    for d in diffs:
        pid = d["player_id"]
        player = player_index.get(pid)
        if not player:
            not_found.append(pid)
            continue

        for c in d["changes"]:
            field = c["field"]
            new_val = c["new"]
            path = FIELD_PATHS.get(field)
            if not path:
                continue

            section, key = path
            if section not in player:
                player[section] = {}
            player[section][key] = new_val

            applied.append({
                "player_id": pid,
                "name": d.get("name"),
                "field": field,
                "tier": c.get("tier", 3),
                "old": c["old"],
                "new": new_val,
                "was_missing": c.get("was_missing", False),
            })

    # Write updated canonical
    with open(CANONICAL_PATH, "w") as f:
        json.dump(players, f, indent=2, ensure_ascii=False, default=str)

    # Write audit trail
    audit = {
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "total_changes": len(applied),
        "tier_breakdown": {
            "tier_1_imperdonable": sum(1 for a in applied if a["tier"] == 1),
            "tier_2_muy_importante": sum(1 for a in applied if a["tier"] == 2),
            "tier_3_importante": sum(1 for a in applied if a["tier"] == 3),
        },
        "fields_filled": sum(1 for a in applied if a["was_missing"]),
        "not_found": not_found,
        "changes": applied,
    }
    with open(APPLIED_LOG, "w") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False, default=str)

    print(f"  ✅ Applied {len(applied)} changes to {len(set(a['player_id'] for a in applied))} players")
    if not_found:
        print(f"  ⚠️  {len(not_found)} player IDs not found in canonical data")
    print(f"  Audit trail: {APPLIED_LOG}")
    print("  Done!")


if __name__ == "__main__":
    args = sys.argv[1:]
    do_apply = "--apply" in args

    field = None
    if "--field" in args:
        idx = args.index("--field")
        if idx + 1 < len(args):
            field = args[idx + 1]

    tier = None
    if "--tier" in args:
        idx = args.index("--tier")
        if idx + 1 < len(args):
            tier = int(args[idx + 1])

    run_apply(do_apply=do_apply, field_filter=field, tier_filter=tier)
