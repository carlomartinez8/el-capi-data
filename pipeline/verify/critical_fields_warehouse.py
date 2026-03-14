"""
Critical Fields Verifier — Warehouse Edition

Adapted from critical_fields.py to read/write directly from Supabase warehouse
tables (players + player_career) instead of players_canonical.json.

KEY DIFFERENCE FROM ORIGINAL:
- Reads from Supabase players + player_career (not JSON file)
- Writes detected changes as CURATION FLAGS (not direct updates)
- Scopes to top N players by market value (configurable)
- Designed to run on a schedule (daily for Tier 1, weekly for Tier 3)

Carlo's rule: "anything not 100% → curation"
GPT says club changed? → Flag for curation. Curator confirms, then update applies.

Uses gpt-4o (not mini) because fans DO NOT FORGIVE wrong data.

TIER 1 — IMPERDONABLE (zero tolerance, daily):
  - current_club, current_league, nationality_primary, position_primary

TIER 2 — MUY IMPORTANTE (daily, tolerate minor drift):
  - date_of_birth, estimated_value_eur

TIER 3 — IMPORTANTE (weekly is fine):
  - current_jersey_number, international_caps, international_goals,
    injury_fitness_status, contract_expires

Usage:
    python -m pipeline.verify.critical_fields_warehouse                         # verify top 500
    python -m pipeline.verify.critical_fields_warehouse --top 100               # top 100 only
    python -m pipeline.verify.critical_fields_warehouse --player "Mbappé"       # single player
    python -m pipeline.verify.critical_fields_warehouse --tier 1                # Tier 1 only (daily)
    python -m pipeline.verify.critical_fields_warehouse --tier 3                # Tier 3 only (weekly)
    python -m pipeline.verify.critical_fields_warehouse --dry-run               # preview
    python -m pipeline.verify.critical_fields_warehouse --batch 10              # test batch
"""

import json
import time
import sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from openai import OpenAI

# ─── Config ─────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.config import OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY, OUTPUT_DIR

MAX_WORKERS = 1          # single thread for safety
RATE_LIMIT_DELAY = 3.0
MODEL = "gpt-4o"
DEFAULT_TOP_N = 500      # verify top 500 by market value

VERIFY_OUTPUT = OUTPUT_DIR / "warehouse_verification_results.json"
VERIFY_DIFF = OUTPUT_DIR / "warehouse_verification_diff.json"
VERIFY_LOG = OUTPUT_DIR / "warehouse_verification_log.json"

# ─── Tiered field definitions ────────────────────────────────────────

TIER_1_IMPERDONABLE = [
    "current_club",
    "current_league",
    "nationality_primary",
    "position_primary",
]

TIER_2_MUY_IMPORTANTE = [
    "date_of_birth",
    "estimated_value_eur",
]

TIER_3_IMPORTANTE = [
    "current_jersey_number",
    "international_caps",
    "international_goals",
    "injury_fitness_status",
    "contract_expires",
]

ALL_CRITICAL_FIELDS = TIER_1_IMPERDONABLE + TIER_2_MUY_IMPORTANTE + TIER_3_IMPORTANTE

# ─── System prompt ───────────────────────────────────────────────────

VERIFY_SYSTEM_PROMPT = """\
You are a football data verification system. Return ONLY current, verified facts \
as of {today}. No narratives, no opinions — pure data.

CONTEXT: This data powers El Capi, a World Cup 2026 AI assistant. Fans will \
immediately notice and lose trust if clubs, nationalities, or positions are wrong. \
ACCURACY IS EVERYTHING.

RULES:
- Verify each field against your knowledge. Correct ANY errors.
- If a value is correct, return it unchanged.
- If you genuinely don't know the CURRENT value, return null — NEVER guess.
- "nationality_primary" = the NATIONAL TEAM they represent (not passport).
  Example: Laporte → Spain (not France), Musiala → Germany (not England).
- "estimated_value_eur" = format as "€30M" or "€500K" (Transfermarkt-style).
- "date_of_birth" = YYYY-MM-DD format.
- "contract_expires" = YYYY-MM-DD or "June 2027" format.
- "international_caps" and "international_goals" = career totals for national team.
- "injury_fitness_status" = current status or null if fully fit.

Return ONLY this JSON (no extra fields, no commentary):
{{
  "current_club": "Club Name",
  "current_league": "League Name",
  "nationality_primary": "Country Name",
  "position_primary": "Goalkeeper / Defender / Midfielder / Forward",
  "date_of_birth": "YYYY-MM-DD",
  "estimated_value_eur": "€30M",
  "current_jersey_number": 10,
  "international_caps": 100,
  "international_goals": 50,
  "injury_fitness_status": null,
  "contract_expires": "2027-06-30"
}}
"""


def get_supabase_client():
    """Initialize Supabase client."""
    from supabase import create_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("  ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in .env")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def load_players_from_warehouse(supabase, top_n: int = DEFAULT_TOP_N, single_player: str = None):
    """Load players + career data from Supabase warehouse."""
    # Build query: players joined with career data
    query = supabase.table("players").select(
        "id, known_as, full_legal_name, date_of_birth, nationality_primary, "
        "photo_url, data_confidence, needs_curation, source_records"
    )

    if single_player:
        # Search by name
        query = query.ilike("known_as", f"%{single_player}%")
        players_resp = query.execute()
    else:
        # Get top N by market value — need to go through player_career
        career_resp = supabase.table("player_career").select(
            "player_id, current_club, current_league, position_primary, "
            "position_secondary, current_jersey_number, estimated_value_eur, "
            "contract_expires"
        ).not_.is_("estimated_value_eur", "null") \
         .order("estimated_value_eur", desc=True) \
         .limit(top_n) \
         .execute()

        player_ids = [r["player_id"] for r in career_resp.data]
        if not player_ids:
            return []

        # Fetch player identity for those IDs
        players_resp = supabase.table("players").select(
            "id, known_as, full_legal_name, date_of_birth, nationality_primary, "
            "photo_url, data_confidence, needs_curation, source_records"
        ).in_("id", player_ids).execute()

        # Build career lookup
        career_by_id = {r["player_id"]: r for r in career_resp.data}

        # Merge
        merged = []
        for p in players_resp.data:
            career = career_by_id.get(p["id"], {})
            merged.append({**p, **career})
        return merged

    # Single player path — also fetch career
    results = []
    for p in players_resp.data:
        career_resp = supabase.table("player_career").select("*") \
            .eq("player_id", p["id"]).execute()
        career = career_resp.data[0] if career_resp.data else {}
        results.append({**p, **career})
    return results


def extract_current_values(player: dict) -> dict:
    """Pull current values of ALL critical fields from warehouse player."""
    return {
        "current_club": player.get("current_club"),
        "current_league": player.get("current_league"),
        "nationality_primary": player.get("nationality_primary"),
        "position_primary": player.get("position_primary"),
        "date_of_birth": player.get("date_of_birth"),
        "estimated_value_eur": player.get("estimated_value_eur"),
        "current_jersey_number": player.get("current_jersey_number"),
        "international_caps": player.get("international_caps"),
        "international_goals": player.get("international_goals"),
        "injury_fitness_status": player.get("injury_fitness_status"),
        "contract_expires": player.get("contract_expires"),
    }


def verify_player(client: OpenAI, player: dict) -> dict:
    """Verify critical fields for a single player via gpt-4o."""
    name = player.get("known_as") or player.get("full_legal_name") or "Unknown"
    current = extract_current_values(player)

    lines = [
        f"Player: {player.get('full_legal_name') or name}",
        f"Known as: {name}",
        f"DOB on file: {player.get('date_of_birth', 'MISSING')}",
        f"Nationality on file: {player.get('nationality_primary', 'MISSING')}",
        "",
        "Current data to verify — correct ANY errors:",
    ]
    for field, value in current.items():
        display = value if value is not None else "MISSING"
        lines.append(f"  {field}: {display}")

    user_msg = "\n".join(lines)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": VERIFY_SYSTEM_PROMPT.format(today=today)},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=400,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        verified = json.loads(content)
        usage = response.usage

        return {
            "status": "ok",
            "verified": verified,
            "tokens": {
                "prompt": usage.prompt_tokens if usage else 0,
                "completion": usage.completion_tokens if usage else 0,
                "total": usage.total_tokens if usage else 0,
            },
        }
    except json.JSONDecodeError:
        return {"status": "json_parse_error", "verified": None, "tokens": {"total": 0}}
    except Exception as e:
        return {"status": f"error:{type(e).__name__}", "verified": None, "tokens": {"total": 0}}


def compute_diff(current: dict, verified: dict, tier_filter: int = None) -> list[dict]:
    """Compare current vs verified values, return list of changes with tier tags."""
    changes = []
    if not verified:
        return changes

    tier_map = {}
    for f in TIER_1_IMPERDONABLE:
        tier_map[f] = 1
    for f in TIER_2_MUY_IMPORTANTE:
        tier_map[f] = 2
    for f in TIER_3_IMPORTANTE:
        tier_map[f] = 3

    fields_to_check = ALL_CRITICAL_FIELDS
    if tier_filter:
        fields_to_check = [f for f in fields_to_check if tier_map.get(f) == tier_filter]

    for field in fields_to_check:
        old_val = current.get(field)
        new_val = verified.get(field)

        old_norm = str(old_val).strip().lower() if old_val not in (None, "", "null") else None
        new_norm = str(new_val).strip().lower() if new_val not in (None, "", "null") else None

        if old_norm != new_norm:
            if old_norm is None and new_norm is None:
                continue
            if new_norm in ("null", "none", "n/a", "unknown"):
                new_val = None
                new_norm = None
            if old_norm != new_norm:
                changes.append({
                    "field": field,
                    "tier": tier_map.get(field, 3),
                    "old": old_val,
                    "new": new_val,
                    "was_missing": old_val in (None, "", "null"),
                })

    changes.sort(key=lambda c: c["tier"])
    return changes


def flag_for_curation(supabase, player_id: str, changes: list[dict]):
    """Write detected changes as curation flags on the player record."""
    # Build curation reason from changes
    change_descriptions = []
    for c in changes:
        tier_label = {1: "T1", 2: "T2", 3: "T3"}.get(c["tier"], "T?")
        old_display = c["old"] if c["old"] is not None else "NULL"
        new_display = c["new"] if c["new"] is not None else "NULL"
        change_descriptions.append(
            f"{tier_label}:{c['field']}:{old_display}->{new_display}"
        )

    reason_str = "recency_check: " + "; ".join(change_descriptions)

    # Update the player record
    supabase.table("players").update({
        "needs_curation": True,
        "curation_reason": reason_str,
    }).eq("id", player_id).execute()


def run_warehouse_verification(
    top_n: int = DEFAULT_TOP_N,
    single_player: str = None,
    batch_size: int = 0,
    tier_filter: int = None,
    dry_run: bool = False,
    flag_curation: bool = True,
):
    """Main verification loop — reads from warehouse, flags changes for curation."""
    print("=" * 60)
    print("  EL CAPI — Critical Fields Verification (Warehouse)")
    print("  'Los fans no perdonan datos incorrectos'")
    print("=" * 60)

    if not OPENAI_API_KEY:
        print("  ERROR: OPENAI_API_KEY not set in .env")
        sys.exit(1)

    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    supabase = get_supabase_client()

    # Load players from warehouse
    print(f"  Loading top {top_n} players by market value from warehouse...")
    players = load_players_from_warehouse(supabase, top_n=top_n, single_player=single_player)
    print(f"  Loaded {len(players)} players")

    if not players:
        print("  No players found.")
        return

    if batch_size > 0:
        players = players[:batch_size]
        print(f"  Batch limited to {batch_size} players")

    total = len(players)
    est_cost = total * 0.003
    est_time = total * RATE_LIMIT_DELAY / MAX_WORKERS

    tier_label = f" (Tier {tier_filter} only)" if tier_filter else ""
    print(f"  Model: {MODEL}")
    print(f"  Scope: Top {top_n} by market value{tier_label}")
    print(f"  Curation mode: {'flag for review' if flag_curation else 'report only'}")
    print(f"  Estimated cost: ~${est_cost:.2f}")
    print(f"  Estimated time: ~{est_time/60:.1f} min")
    print()

    if dry_run:
        print("  DRY RUN — showing what would be verified:")
        for p in players[:15]:
            name = p.get("known_as", "?")
            club = p.get("current_club", "?")
            value = p.get("estimated_value_eur", "?")
            conf = p.get("data_confidence", "?")
            print(f"    {name} | {club} | {value} | {conf}")
        if total > 15:
            print(f"    ... and {total - 15} more")
        return

    # ─── Run verification ──────────────────────────────────────────
    results = {}
    all_diffs = []
    flagged_count = 0
    stats = {
        "total": total,
        "verified": 0,
        "failed": 0,
        "tier1_changes": 0,
        "tier2_changes": 0,
        "tier3_changes": 0,
        "fields_filled": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "flagged_for_curation": 0,
    }

    start_time = time.time()
    completed = 0

    def verify_with_delay(player):
        time.sleep(RATE_LIMIT_DELAY)
        return player, verify_player(openai_client, player)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(verify_with_delay, p): p for p in players}

        for future in as_completed(futures):
            player, result = future.result()
            completed += 1
            pid = player.get("id", "?")
            name = player.get("known_as", "?")

            if result["status"] == "ok":
                stats["verified"] += 1
                tokens = result["tokens"]
                stats["total_tokens"] += tokens.get("total", 0)
                cost = (tokens.get("prompt", 0) * 0.0000025
                        + tokens.get("completion", 0) * 0.00001)
                stats["total_cost_usd"] += cost

                current = extract_current_values(player)
                changes = compute_diff(current, result["verified"], tier_filter=tier_filter)

                if changes:
                    diff_entry = {
                        "player_id": pid,
                        "name": name,
                        "changes": changes,
                    }
                    all_diffs.append(diff_entry)

                    for c in changes:
                        if c["was_missing"]:
                            stats["fields_filled"] += 1
                        elif c["tier"] == 1:
                            stats["tier1_changes"] += 1
                        elif c["tier"] == 2:
                            stats["tier2_changes"] += 1
                        else:
                            stats["tier3_changes"] += 1

                    # Flag for curation
                    if flag_curation:
                        try:
                            flag_for_curation(supabase, pid, changes)
                            stats["flagged_for_curation"] += 1
                        except Exception as e:
                            print(f"  WARNING: Failed to flag {name}: {e}")

                    t1 = [c for c in changes if c["tier"] == 1]
                    t23 = [c for c in changes if c["tier"] > 1]
                    parts = []
                    if t1:
                        parts.append(f"T1: {', '.join(c['field'] for c in t1)}")
                    if t23:
                        parts.append(f"T2/3: {', '.join(c['field'] for c in t23)}")
                    print(f"  [{completed}/{total}] {name} — {' | '.join(parts)}")
                else:
                    print(f"  [{completed}/{total}] {name} — OK")

                results[pid] = {
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "current": current,
                    "verified": result["verified"],
                    "changes": changes,
                    "tokens": tokens,
                }
            else:
                stats["failed"] += 1
                print(f"  [{completed}/{total}] {name} — FAIL ({result['status']})")
                results[pid] = {
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "status": result["status"],
                }

            if completed % 50 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (total - completed) / rate if rate > 0 else 0
                print(f"  --- {completed}/{total} | "
                      f"T1:{stats['tier1_changes']} T2:{stats['tier2_changes']} "
                      f"T3:{stats['tier3_changes']} filled:{stats['fields_filled']} | "
                      f"flagged:{stats['flagged_for_curation']} | "
                      f"${stats['total_cost_usd']:.3f} | ETA {eta/60:.1f}min ---")

    elapsed = time.time() - start_time

    # ─── Write outputs ──────────────────────────────────────────────
    log = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "source": "supabase_warehouse",
        "scope": f"top_{top_n}_by_market_value",
        "tier_filter": tier_filter,
        "elapsed_seconds": round(elapsed, 1),
        "stats": stats,
    }

    with open(VERIFY_OUTPUT, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    with open(VERIFY_DIFF, "w") as f:
        json.dump(all_diffs, f, indent=2, ensure_ascii=False, default=str)
    with open(VERIFY_LOG, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False, default=str)

    # ─── Summary ────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  VERIFICATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Players verified:      {stats['verified']}/{total}")
    print(f"  Failed:                {stats['failed']}")
    print(f"  T1 changes (club etc): {stats['tier1_changes']}")
    print(f"  T2 changes (DOB/val):  {stats['tier2_changes']}")
    print(f"  T3 changes (caps etc): {stats['tier3_changes']}")
    print(f"  Fields filled (null):  {stats['fields_filled']}")
    print(f"  Flagged for curation:  {stats['flagged_for_curation']}")
    print(f"  Tokens:                {stats['total_tokens']:,}")
    print(f"  Cost:                  ${stats['total_cost_usd']:.3f}")
    print(f"  Time:                  {elapsed/60:.1f} min")
    print(f"{'=' * 60}")

    if all_diffs:
        print(f"\n  {len(all_diffs)} players with changes:")
        from collections import Counter
        field_counts = Counter()
        for d in all_diffs:
            for c in d["changes"]:
                tier_label = {1: "T1", 2: "T2", 3: "T3"}.get(c["tier"], "T?")
                field_counts[f"{tier_label} {c['field']}"] += 1
        for field, count in field_counts.most_common():
            print(f"    {field}: {count}")

    return results, all_diffs, log


if __name__ == "__main__":
    args = sys.argv[1:]

    single = None
    batch = 0
    top = DEFAULT_TOP_N
    tier = None
    dry = "--dry-run" in args
    no_flag = "--no-flag" in args

    if "--player" in args:
        idx = args.index("--player")
        if idx + 1 < len(args):
            single = args[idx + 1]

    if "--batch" in args:
        idx = args.index("--batch")
        if idx + 1 < len(args):
            batch = int(args[idx + 1])

    if "--top" in args:
        idx = args.index("--top")
        if idx + 1 < len(args):
            top = int(args[idx + 1])

    if "--tier" in args:
        idx = args.index("--tier")
        if idx + 1 < len(args):
            tier = int(args[idx + 1])

    run_warehouse_verification(
        top_n=top,
        single_player=single,
        batch_size=batch,
        tier_filter=tier,
        dry_run=dry,
        flag_curation=not no_flag,
    )
