#!/usr/bin/env python3
"""
El Capi Data Pipeline — GPT Narrative Enrichment (v3 — Narrative-Only)

Takes the merged player facts and uses OpenAI to generate NARRATIVE content only.
Facts (DOB, height, position, club, market value, etc.) come from the merge step,
NOT from GPT. This module only produces stories, playing style, personality, etc.

Usage:
    python run_enrichment.py                           # enrich WC squad players
    python run_enrichment.py --all                     # enrich ALL players
    python run_enrichment.py --player "Lionel Messi"   # single player
    python run_enrichment.py --batch 50                # limit batch size
    python run_enrichment.py --resume                  # resume from checkpoint
    python run_enrichment.py --legacy                  # use old full-schema mode
"""

import sys
import json
import time
from datetime import datetime

from openai import OpenAI
from unidecode import unidecode
from pipeline.config import OPENAI_API_KEY, OUTPUT_DIR, INTERMEDIATE_DIR

client = OpenAI(api_key=OPENAI_API_KEY)

NARRATIVES_OUTPUT = OUTPUT_DIR / "players_narratives.json"
ENRICHMENT_OUTPUT = OUTPUT_DIR / "players_enriched.json"  # backward compat
CHECKPOINT_FILE = INTERMEDIATE_DIR / "enrichment_checkpoint.json"
MERGED_PATH = OUTPUT_DIR / "players_merged.json"

WC_2026_HOST_CITIES = [
    "New York", "New Jersey", "Los Angeles", "Dallas", "Houston", "Atlanta",
    "Philadelphia", "Miami", "Seattle", "San Francisco", "Bay Area",
    "Kansas City", "Boston", "Guadalajara", "Mexico City", "Monterrey",
    "Vancouver", "Toronto",
]

# ─── Narrative-Only System Prompt ────────────────────────────────────────
# GPT receives player facts as CONTEXT but only returns narrative content.
# This prevents GPT from overwriting verified factual data.

NARRATIVE_SYSTEM_PROMPT = """\
You are an elite football (soccer) storyteller building narrative content for \
an AI assistant called "El Capi" — the captain of World Cup 2026 knowledge.

You will receive a player's VERIFIED FACTS (name, DOB, club, position, etc.) \
as context. Your job is to write compelling narrative content ONLY — do NOT \
repeat or modify the factual fields.

IMPORTANT RULES:
- Be ACCURATE. If you're unsure, use null — never fabricate stories or stats.
- Be SPECIFIC. "Scored a hat-trick vs Brazil in 2023 Copa America semifinal" \
  beats "scored important goals".
- Be BILINGUAL. Provide EN + ES for all narrative fields.
- Be a STORYTELLER. Origin stories, turning points, human moments.
- Do NOT return identity facts (DOB, height, nationality, etc.) — we already have those.
- Do NOT return career facts (club, position, market value, etc.) — we already have those.

Return ONLY valid JSON with these NARRATIVE sections:

{
  "playing_style": {
    "style_summary_en": "2-3 sentences on how they play — specific about what makes them unique",
    "style_summary_es": "Same in Spanish",
    "signature_moves": ["Inside-left cut from the right wing", "Low-driven free kicks"],
    "strengths": ["Close dribbling in tight spaces", "Vision and through-balls"],
    "weaknesses": ["Aerial duels", "Defensive work rate"],
    "comparable_to": {"player": "Diego Maradona", "reason_en": "...", "reason_es": "..."},
    "best_partnership": {"player": "Neymar / Luis Suárez", "context_en": "...", "context_es": "..."}
  },

  "story": {
    "origin_story_en": "2-4 sentences about their path to football — childhood, family, hardships. Make it compelling.",
    "origin_story_es": "Same in Spanish",
    "breakthrough_moment": {
      "description_en": "The specific game/event that made them famous",
      "description_es": "Same in Spanish",
      "date": "YYYY-MM-DD or approximate",
      "context": "League match / World Cup / etc"
    },
    "career_defining_quote_by_player": {"quote_en": "...", "quote_es": "...", "context": "When/where"},
    "famous_quote_about_player": {"quote_en": "...", "quote_es": "...", "attributed_to": "Person"},
    "biggest_controversy": {"description_en": "Brief or null", "description_es": "Same or null"},
    "career_summary_en": "3-4 sentence career narrative — arc, peaks, legacy",
    "career_summary_es": "Same in Spanish"
  },

  "personality": {
    "celebration_style": "Describe their iconic celebration",
    "superstitions_rituals": ["Always enters right foot first"],
    "off_field_interests": ["Fashion", "Gaming"],
    "charitable_work": "Foundation/cause or null",
    "tattoo_meanings": ["Right arm: family portraits"],
    "social_media": {"instagram": "@handle", "twitter": "@handle", "tiktok": "@handle", "followers_approx": "500M"},
    "fun_facts": ["Specific interesting facts about the player"],
    "music_taste": "Known musical preferences or null",
    "fashion_brands": "Endorsements or null"
  },

  "world_cup_2026": {
    "previous_wc_appearances": [{"year": 2022, "result": "Winner", "notable": "Scored in final"}],
    "wc_qualifying_contribution": "Goals and assists in qualifiers",
    "tournament_role_en": "Expected role for their team",
    "tournament_role_es": "Same in Spanish",
    "narrative_arc_en": "Last WC? First? Redemption? What's the story?",
    "narrative_arc_es": "Same in Spanish",
    "host_city_connection": "Connection to host cities or null",
    "injury_fitness_status": "Current fitness or null if healthy"
  },

  "big_game_dna": {
    "world_cup_goals": 13,
    "champions_league_goals": 129,
    "derby_performances_en": "How they perform in rivalries",
    "derby_performances_es": "Same in Spanish",
    "clutch_moments": ["92nd-minute winner vs Real Madrid in 2017"]
  },

  "injury_history": {
    "notable_injuries": [{"injury": "Knee ligament tear", "date": "2020-11", "months_out": 3}],
    "injury_prone": false
  },

  "identity_extras": {
    "nicknames": [{"name": "La Pulga", "meaning": "The Flea", "language": "es"}],
    "nationality_secondary": "Dual nationality country or null",
    "languages_spoken": ["Spanish", "English"]
  },

  "career_extras": {
    "position_secondary": "Second position or null",
    "international_debut": {"date": "2005-08-17", "opponent": "Hungary", "age": 18},
    "records_held": ["Record description"],
    "endorsement_brands": ["Adidas", "Pepsi"]
  }
}

HOST CITIES for World Cup 2026 (check connections): """ + ", ".join(WC_2026_HOST_CITIES) + """

If you don't know a field, set it to null. For arrays, use empty []. \
ACCURACY over completeness — always.\
"""


def build_fact_context(player_facts: dict) -> str:
    """Build a context message from merged facts so GPT has accurate info to base narratives on."""
    parts = [f"Player: {player_facts.get('name', 'Unknown')}"]

    fields = player_facts.get("fields", {})

    def fv(field_name: str):
        return fields.get(field_name, {}).get("value")

    if fv("date_of_birth"):
        parts.append(f"DOB: {fv('date_of_birth')}")
    if fv("nationality"):
        parts.append(f"Nationality: {fv('nationality')}")
    if fv("position"):
        parts.append(f"Position: {fv('position')}")
    if fv("current_club"):
        parts.append(f"Club: {fv('current_club')}")
    if fv("current_league"):
        parts.append(f"League: {fv('current_league')}")
    if fv("height_cm"):
        parts.append(f"Height: {fv('height_cm')}cm")
    if fv("market_value_eur"):
        parts.append(f"Market value: €{fv('market_value_eur'):,}")
    if fv("jersey_number"):
        parts.append(f"Jersey: #{fv('jersey_number')}")
    if player_facts.get("wc_team_code"):
        parts.append(f"World Cup 2026 team: {player_facts['wc_team_code']}")
    if fv("international_caps"):
        parts.append(f"International caps: {fv('international_caps')}")
    if fv("international_goals"):
        parts.append(f"International goals: {fv('international_goals')}")
    if fv("career_trajectory"):
        traj = fv("career_trajectory")
        if isinstance(traj, list) and traj:
            clubs = [t.get("club", "?") for t in traj[:5]]
            parts.append(f"Career clubs: {' → '.join(clubs)}")
    if fv("major_trophies"):
        trophies = fv("major_trophies")
        if isinstance(trophies, list) and trophies:
            parts.append(f"Notable trophies: {len(trophies)} total")

    parts.append("")
    parts.append("Write NARRATIVE content only. Do NOT repeat facts above — they're already stored.")

    return "\n".join(parts)


def build_flat_context(player: dict) -> str:
    """Build context from flat canonical player (fallback when merged data not available)."""
    parts = [f"Player: {player.get('name', 'Unknown')}"]
    if player.get("current_club_name"):
        parts.append(f"Club: {player['current_club_name']}")
    if player.get("nationality"):
        parts.append(f"Nationality: {player['nationality']}")
    if player.get("position"):
        parts.append(f"Position: {player['position']}")
    if player.get("sub_position"):
        parts.append(f"Detailed position: {player['sub_position']}")
    if player.get("date_of_birth"):
        parts.append(f"DOB: {player['date_of_birth']}")
    if player.get("height_cm"):
        parts.append(f"Height: {player['height_cm']}cm")
    if player.get("market_value_eur"):
        parts.append(f"Market value: €{player['market_value_eur']:,}")
    if player.get("wc_team_code"):
        parts.append(f"World Cup 2026 team: {player['wc_team_code']}")
    if player.get("foot"):
        parts.append(f"Preferred foot: {player['foot']}")

    parts.append("")
    parts.append("Write NARRATIVE content only. Do NOT repeat facts above — they're already stored.")

    return "\n".join(parts)


def enrich_player_narrative(context_msg: str) -> dict | None:
    """Call GPT to generate narrative content for a player."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": NARRATIVE_SYSTEM_PROMPT},
                {"role": "user", "content": context_msg},
            ],
            temperature=0.3,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        usage = response.usage
        if usage:
            parsed["_tokens"] = {
                "prompt": usage.prompt_tokens,
                "completion": usage.completion_tokens,
                "total": usage.total_tokens,
            }

        return parsed

    except json.JSONDecodeError:
        print("JSON_PARSE_FAIL", end=" ")
        return None
    except Exception as e:
        print(f"ERROR({type(e).__name__})", end=" ")
        return None


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"completed": [], "enriched_data": {}, "total_tokens": 0, "total_cost_usd": 0.0}


def save_checkpoint(checkpoint: dict):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2, default=str)


def run_enrichment(
    wc_only: bool = True,
    single_player: str | None = None,
    batch_size: int = 700,
    resume: bool = False,
    use_merged: bool = True,
):
    """
    Run narrative enrichment.

    Args:
        use_merged: If True, reads from players_merged.json (preferred — richer context).
                    If False, reads from players_canonical_latest.json (flat fallback).
    """
    print("=" * 60)
    print("  EL CAPI — Narrative Enrichment (v3 — Narrative-Only)")
    print("=" * 60)
    print("  Mode: NARRATIVE-ONLY (facts come from merge step)")
    print()

    # ── Load player data ──
    merged_players: list[dict] = []
    flat_players: list[dict] = []

    if use_merged and MERGED_PATH.exists():
        print(f"  Loading merged facts: {MERGED_PATH}")
        with open(MERGED_PATH) as f:
            merged_players = json.load(f)
        print(f"  Merged players: {len(merged_players)}")
    else:
        print(f"  Merged data not available — using flat canonical")
        use_merged = False

    if not use_merged:
        latest_path = OUTPUT_DIR / "players_canonical_latest.json"
        if not latest_path.exists():
            print(f"  ERROR: Run the pipeline first. Missing: {latest_path}")
            sys.exit(1)
        with open(latest_path) as f:
            flat_players = json.load(f)
        if wc_only:
            flat_players = [p for p in flat_players if p.get("in_wc_squad")]
        print(f"  Flat canonical players: {len(flat_players)}")

    players_to_process = merged_players if use_merged else flat_players

    # ── Filter ──
    if single_player:
        query = unidecode(single_player).lower()
        players_to_process = [
            p for p in players_to_process
            if query in unidecode(p.get("name") or "").lower()
        ]
        if not players_to_process:
            print(f"  Player '{single_player}' not found.")
            return
        print(f"  Enriching single player: {players_to_process[0]['name']}")

    print(f"  Players to enrich: {len(players_to_process)}")

    # ── Resume support ──
    checkpoint = load_checkpoint() if resume else {
        "completed": [], "enriched_data": {}, "total_tokens": 0, "total_cost_usd": 0.0
    }
    completed_set = set(checkpoint["completed"])

    remaining = [
        p for p in players_to_process
        if str(p.get("source_id", "")) not in completed_set
    ]
    to_process = remaining[:batch_size]

    print(f"  Already enriched: {len(completed_set)}")
    print(f"  Remaining: {len(remaining)}")
    print(f"  Processing this batch: {len(to_process)}")
    print(f"  Estimated cost: ~${len(to_process) * 0.002:.2f}")
    print()

    start_time = time.time()
    success = 0
    failed = 0

    for i, player in enumerate(to_process):
        name = player.get("name", "Unknown")
        pid = str(player.get("source_id", "?"))
        team = player.get("wc_team_code", "")
        team_tag = f" [{team}]" if team else ""
        print(f"  [{i+1}/{len(to_process)}] {name}{team_tag}...", end=" ", flush=True)

        # Build context from merged or flat data
        if use_merged:
            context = build_fact_context(player)
        else:
            context = build_flat_context(player)

        narrative = enrich_player_narrative(context)
        if narrative:
            tokens = narrative.get("_tokens", {})
            total_tok = tokens.get("total", 0)
            cost = total_tok * 0.00000015 + tokens.get("completion", 0) * 0.0000006

            checkpoint["enriched_data"][pid] = {
                "source_id": pid,
                "name": name,
                "wc_team_code": team,
                **narrative,
                "enriched_at": datetime.now().isoformat(),
            }
            checkpoint["completed"].append(pid)
            checkpoint["total_tokens"] = checkpoint.get("total_tokens", 0) + total_tok
            checkpoint["total_cost_usd"] = checkpoint.get("total_cost_usd", 0.0) + cost

            print(f"OK ({total_tok} tok)")
            success += 1
        else:
            print("FAILED")
            failed += 1

        if (i + 1) % 10 == 0:
            save_checkpoint(checkpoint)
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            eta = (len(to_process) - i - 1) / rate if rate > 0 else 0
            print(f"  --- checkpoint: {success} ok, {failed} fail, ${checkpoint['total_cost_usd']:.3f} spent, ETA {eta/60:.1f}min ---")

        time.sleep(0.3)

    save_checkpoint(checkpoint)

    # ── Write narrative output ──
    narratives = list(checkpoint["enriched_data"].values())

    print(f"\n  Writing narratives: {NARRATIVES_OUTPUT}")
    with open(NARRATIVES_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(narratives, f, ensure_ascii=False, indent=2, default=str)

    # ── Also write backward-compatible enriched format ──
    # The combine step can read either file; this ensures old workflows still work.
    print(f"  Writing backward-compat enriched: {ENRICHMENT_OUTPUT}")
    with open(ENRICHMENT_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(narratives, f, ensure_ascii=False, indent=2, default=str)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  NARRATIVE ENRICHMENT COMPLETE")
    print(f"  Players enriched: {success} ok, {failed} failed")
    print(f"  Total in database: {len(checkpoint['enriched_data'])}")
    print(f"  Tokens used: {checkpoint['total_tokens']:,}")
    print(f"  Cost: ${checkpoint['total_cost_usd']:.3f}")
    print(f"  Time: {elapsed/60:.1f} min")
    print(f"  Output: {NARRATIVES_OUTPUT}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    args = sys.argv[1:]

    wc_only = "--all" not in args
    single = None
    batch = 700
    do_resume = "--resume" in args

    if "--player" in args:
        idx = args.index("--player")
        if idx + 1 < len(args):
            single = args[idx + 1]

    if "--batch" in args:
        idx = args.index("--batch")
        if idx + 1 < len(args):
            batch = int(args[idx + 1])

    run_enrichment(
        wc_only=wc_only,
        single_player=single,
        batch_size=batch,
        resume=do_resume,
    )
