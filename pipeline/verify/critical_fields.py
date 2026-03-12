"""
Critical Fields Verifier — Daily accuracy pipeline for El Capi.

Uses gpt-4o (not mini) because fans DO NOT FORGIVE wrong data.
Capi's tiered priority system:

TIER 1 — IMPERDONABLE (zero tolerance, daily, gpt-4o):
  - current_club           → "¿Dónde juega X?" is THE most asked question
  - current_league         → follows club
  - nationality_primary    → identity. get this wrong = instant death
  - position_primary       → shows we don't know football if wrong
  - in_wc_2026_squad       → THE tournament. can't confuse who's in/out

TIER 2 — MUY IMPORTANTE (daily, tolerate minor drift):
  - date_of_birth          → for age calc. off by a year = visible but forgivable
  - estimated_value_eur    → approximate is fine, order of magnitude must be right

TIER 3 — IMPORTANTE (weekly is fine):
  - current_jersey_number  → changes per tournament, iconic numbers matter
  - international_caps     → changes every match, approximate is ok
  - international_goals    → same
  - injury_fitness_status  → pre-tournament becomes critical
  - contract_expires       → fan trivia, not critical

Cost: ~$0.003/player × 632 = ~$1.90/run (gpt-4o, still cheap for accuracy)
Time: ~5-8 minutes with 8 threads
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
from pipeline.config import OPENAI_API_KEY, OUTPUT_DIR

CANONICAL_PATH = OUTPUT_DIR / "players_canonical.json"
VERIFY_OUTPUT = OUTPUT_DIR / "verification_results.json"
VERIFY_DIFF = OUTPUT_DIR / "verification_diff.json"
VERIFY_LOG = OUTPUT_DIR / "verification_log.json"

MAX_WORKERS = 1          # single thread to guarantee no rate limits
RATE_LIMIT_DELAY = 3.0   # generous delay between API calls
MODEL = "gpt-4o"         # NOT mini — accuracy is worth the extra cost

# ─── Tiered field definitions ────────────────────────────────────────

TIER_1_IMPERDONABLE = [
    "current_club",
    "current_league",
    "nationality_for_wc",       # who they REPRESENT, not passport
    "position_primary",
    "in_wc_2026_squad",         # boolean — are they going or not
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

# ─── System prompt — tight, factual, zero bullshit ───────────────────

VERIFY_SYSTEM_PROMPT = """\
You are a football data verification system. Return ONLY current, verified facts \
as of {today}. No narratives, no opinions — pure data.

CONTEXT: This data powers El Capi, a World Cup 2026 AI assistant. Fans will \
immediately notice and lose trust if clubs, nationalities, or squad status are wrong. \
ACCURACY IS EVERYTHING.

RULES:
- Verify each field against your knowledge. Correct ANY errors.
- If a value is correct, return it unchanged.
- If you genuinely don't know the CURRENT value, return null — NEVER guess.
- "nationality_for_wc" = the NATIONAL TEAM they represent at WC 2026 (not passport nationality).
  Example: Laporte → Spain (not France), Musiala → Germany (not England).
- "in_wc_2026_squad" = true if their country QUALIFIED for WC 2026 AND they are likely \
  to be in the squad. false if their country didn't qualify OR they're retired from \
  international football. null if too early to know squad selection.
- "estimated_value_eur" = format as "€30M" or "€500K" (Transfermarkt-style estimate).
- "date_of_birth" = YYYY-MM-DD format.
- "contract_expires" = YYYY-MM-DD or "June 2027" format.
- "international_caps" and "international_goals" = career totals for national team.
- "injury_fitness_status" = current status or null if fully fit.

Return ONLY this JSON (no extra fields, no commentary):
{{
  "current_club": "Club Name",
  "current_league": "League Name",
  "nationality_for_wc": "Country Name",
  "position_primary": "Centre-Forward / Right Winger / etc",
  "in_wc_2026_squad": true,
  "date_of_birth": "YYYY-MM-DD",
  "estimated_value_eur": "€30M",
  "current_jersey_number": 10,
  "international_caps": 100,
  "international_goals": 50,
  "injury_fitness_status": null,
  "contract_expires": "2027-06-30"
}}
"""


def extract_current_values(player: dict) -> dict:
    """Pull current values of ALL critical fields from enriched data."""
    identity = player.get("identity", {})
    career = player.get("career", {})
    market = player.get("market", {})
    wc = player.get("world_cup_2026", {})

    return {
        # Tier 1 — Imperdonable
        "current_club": career.get("current_club"),
        "current_league": career.get("current_league"),
        "nationality_for_wc": identity.get("nationality_primary"),
        "position_primary": career.get("position_primary"),
        "in_wc_2026_squad": True,  # all 632 are currently assumed in-squad

        # Tier 2 — Muy importante
        "date_of_birth": identity.get("date_of_birth"),
        "estimated_value_eur": (market.get("estimated_value_eur")
                                or market.get("market_value")),

        # Tier 3 — Importante
        "current_jersey_number": career.get("current_jersey_number"),
        "international_caps": career.get("international_caps"),
        "international_goals": career.get("international_goals"),
        "injury_fitness_status": wc.get("injury_fitness_status"),
        "contract_expires": career.get("contract_expires"),
    }


def verify_player(client: OpenAI, player: dict) -> dict:
    """Verify critical fields for a single player via gpt-4o."""
    name = player.get("name", "Unknown")
    team = player.get("wc_team_code", "")
    identity = player.get("identity", {})
    current = extract_current_values(player)

    # Build concise user prompt — give AI enough context to verify
    lines = [
        f"Player: {identity.get('full_legal_name') or name}",
        f"Known as: {identity.get('known_as') or name}",
        f"WC 2026 national team code: {team}",
        f"DOB on file: {identity.get('date_of_birth', 'MISSING')}",
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
            temperature=0.0,   # ZERO — maximum factual determinism
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


def compute_diff(current: dict, verified: dict) -> list[dict]:
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

    for field in ALL_CRITICAL_FIELDS:
        old_val = current.get(field)
        new_val = verified.get(field)

        # Normalize for comparison
        old_norm = str(old_val).strip().lower() if old_val not in (None, "", "null") else None
        new_norm = str(new_val).strip().lower() if new_val not in (None, "", "null") else None

        # Detect meaningful changes
        if old_norm != new_norm:
            if old_norm is None and new_norm is None:
                continue
            # Normalize AI "null" strings
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

    # Sort by tier (imperdonables first)
    changes.sort(key=lambda c: c["tier"])
    return changes


def run_verification(
    batch_size: int = 0,
    single_player: str | None = None,
    dry_run: bool = False,
    retry_failed: bool = False,
):
    """Main verification loop — multithreaded across all players."""
    print("=" * 60)
    print("  EL CAPI — Critical Fields Verification (gpt-4o)")
    print("  'Los fans no perdonan datos incorrectos'")
    print("=" * 60)

    if not OPENAI_API_KEY:
        print("  ERROR: OPENAI_API_KEY not set in .env")
        sys.exit(1)

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Load canonical data
    print(f"  Loading from {CANONICAL_PATH}")
    with open(CANONICAL_PATH) as f:
        players = json.load(f)
    print(f"  Loaded {len(players)} players")

    # Retry mode: only re-verify previously failed players
    if retry_failed and VERIFY_OUTPUT.exists():
        with open(VERIFY_OUTPUT) as f:
            prev_results = json.load(f)
        failed_ids = {pid for pid, r in prev_results.items()
                      if r.get("status", "").startswith("error")}
        players = [p for p in players
                   if (p.get("canonical_id") or p.get("source_id", "")) in failed_ids]
        print(f"  RETRY MODE: {len(players)} previously failed players")

    # Filter if single player
    if single_player:
        from unidecode import unidecode
        query = unidecode(single_player).lower()
        players = [p for p in players if query in (p.get("name") or "").lower()
                    or query in (p.get("identity", {}).get("known_as") or "").lower()
                    or query in (p.get("identity", {}).get("full_legal_name") or "").lower()]
        if not players:
            print(f"  Player '{single_player}' not found.")
            return
        print(f"  Verifying: {players[0]['name']}")

    if batch_size > 0:
        players = players[:batch_size]
        print(f"  Batch limited to {batch_size} players")

    total = len(players)
    # gpt-4o pricing: $2.50/1M input, $10/1M output (~600 tok/player)
    est_cost = total * 0.003
    est_time = total * RATE_LIMIT_DELAY / MAX_WORKERS
    print(f"  Model: {MODEL}")
    print(f"  Threads: {MAX_WORKERS}")
    print(f"  Fields per player: {len(ALL_CRITICAL_FIELDS)} "
          f"({len(TIER_1_IMPERDONABLE)} imperdonable, "
          f"{len(TIER_2_MUY_IMPORTANTE)} muy importante, "
          f"{len(TIER_3_IMPORTANTE)} importante)")
    print(f"  Estimated cost: ~${est_cost:.2f}")
    print(f"  Estimated time: ~{est_time/60:.1f} min")
    print()

    if dry_run:
        print("  DRY RUN — showing what would be verified:")
        for p in players[:10]:
            name = p.get("name", "?")
            team = p.get("wc_team_code", "")
            current = extract_current_values(p)
            filled = sum(1 for v in current.values() if v not in (None, "", "null"))
            print(f"    {name} [{team}]: {filled}/{len(ALL_CRITICAL_FIELDS)} fields populated")
        if total > 10:
            print(f"    ... and {total - 10} more")
        return

    # ─── Run verification with thread pool ──────────────────────────
    results = {}
    all_diffs = []
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
    }

    start_time = time.time()
    completed = 0

    def verify_with_delay(player):
        time.sleep(RATE_LIMIT_DELAY)
        return player, verify_player(client, player)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(verify_with_delay, p): p for p in players}

        for future in as_completed(futures):
            player, result = future.result()
            completed += 1
            pid = player.get("canonical_id") or player.get("source_id", "?")
            name = player.get("name", "?")
            team = player.get("wc_team_code", "")

            if result["status"] == "ok":
                stats["verified"] += 1
                tokens = result["tokens"]
                stats["total_tokens"] += tokens.get("total", 0)
                # gpt-4o pricing
                cost = (tokens.get("prompt", 0) * 0.0000025
                        + tokens.get("completion", 0) * 0.00001)
                stats["total_cost_usd"] += cost

                current = extract_current_values(player)
                changes = compute_diff(current, result["verified"])

                if changes:
                    diff_entry = {
                        "player_id": pid,
                        "name": name,
                        "wc_team_code": team,
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

                    # Highlight tier 1 changes prominently
                    t1 = [c for c in changes if c["tier"] == 1]
                    t23 = [c for c in changes if c["tier"] > 1]
                    parts = []
                    if t1:
                        parts.append(f"🔴 T1: {', '.join(c['field'] for c in t1)}")
                    if t23:
                        parts.append(f"T{'/'.join(str(c['tier']) for c in t23)}: "
                                     f"{', '.join(c['field'] for c in t23)}")
                    print(f"  [{completed}/{total}] {name} [{team}] — {' | '.join(parts)}")
                else:
                    print(f"  [{completed}/{total}] {name} [{team}] — ✓")

                results[pid] = {
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "current": current,
                    "verified": result["verified"],
                    "changes": changes,
                    "tokens": tokens,
                }
            else:
                stats["failed"] += 1
                print(f"  [{completed}/{total}] {name} [{team}] — FAIL ({result['status']})")
                results[pid] = {
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "status": result["status"],
                }

            if completed % 50 == 0:
                elapsed = time.time() - start_time
                rate = completed / elapsed
                eta = (total - completed) / rate if rate > 0 else 0
                print(f"  --- {completed}/{total} | "
                      f"🔴 T1:{stats['tier1_changes']} 🟡 T2:{stats['tier2_changes']} "
                      f"🟢 T3:{stats['tier3_changes']} filled:{stats['fields_filled']} | "
                      f"${stats['total_cost_usd']:.3f} | ETA {eta/60:.1f}min ---")

    elapsed = time.time() - start_time

    # ─── Write outputs ──────────────────────────────────────────────
    log = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "threads": MAX_WORKERS,
        "elapsed_seconds": round(elapsed, 1),
        "stats": stats,
        "top_changes": sorted(all_diffs, key=lambda x: sum(1 for c in x["changes"] if c["tier"] == 1), reverse=True)[:20],
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
    print(f"  Players verified:    {stats['verified']}/{total}")
    print(f"  Failed:              {stats['failed']}")
    print(f"  🔴 Tier 1 changes:   {stats['tier1_changes']} (IMPERDONABLE)")
    print(f"  🟡 Tier 2 changes:   {stats['tier2_changes']} (muy importante)")
    print(f"  🟢 Tier 3 changes:   {stats['tier3_changes']} (importante)")
    print(f"  ⬜ Fields filled:     {stats['fields_filled']} (was null)")
    print(f"  Tokens:              {stats['total_tokens']:,}")
    print(f"  Cost:                ${stats['total_cost_usd']:.3f}")
    print(f"  Time:                {elapsed/60:.1f} min")
    print(f"{'=' * 60}")

    if all_diffs:
        print(f"\n  {len(all_diffs)} players with changes:")
        from collections import Counter
        field_counts = Counter()
        for d in all_diffs:
            for c in d["changes"]:
                tier_emoji = {1: "🔴", 2: "🟡", 3: "🟢"}.get(c["tier"], "⬜")
                field_counts[f"{tier_emoji} {c['field']}"] += 1
        for field, count in field_counts.most_common():
            print(f"    {field}: {count}")

    return results, all_diffs, log


if __name__ == "__main__":
    args = sys.argv[1:]

    single = None
    batch = 0
    dry = "--dry-run" in args

    if "--player" in args:
        idx = args.index("--player")
        if idx + 1 < len(args):
            single = args[idx + 1]

    if "--batch" in args:
        idx = args.index("--batch")
        if idx + 1 < len(args):
            batch = int(args[idx + 1])

    run_verification(batch_size=batch, single_player=single, dry_run=dry)
