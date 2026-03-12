#!/usr/bin/env python3
"""
El Capi Data Pipeline — ChatGPT Player Enrichment (Full Schema)

Takes the canonical player list and uses OpenAI to gather rich biographical,
career, personality, and World Cup data for each player.

Usage:
    python run_enrichment.py                           # enrich WC squad players
    python run_enrichment.py --all                     # enrich ALL players
    python run_enrichment.py --player "Lionel Messi"   # single player
    python run_enrichment.py --batch 50                # limit batch size
    python run_enrichment.py --resume                  # resume from checkpoint
"""

import sys
import json
import time
from datetime import datetime

from openai import OpenAI
from unidecode import unidecode
from pipeline.config import OPENAI_API_KEY, OUTPUT_DIR, INTERMEDIATE_DIR

client = OpenAI(api_key=OPENAI_API_KEY)

ENRICHMENT_OUTPUT = OUTPUT_DIR / "players_enriched.json"
CHECKPOINT_FILE = INTERMEDIATE_DIR / "enrichment_checkpoint.json"

WC_2026_HOST_CITIES = [
    "New York", "New Jersey", "Los Angeles", "Dallas", "Houston", "Atlanta",
    "Philadelphia", "Miami", "Seattle", "San Francisco", "Bay Area",
    "Kansas City", "Boston", "Guadalajara", "Mexico City", "Monterrey",
    "Vancouver", "Toronto",
]

SYSTEM_PROMPT = """\
You are an elite football (soccer) researcher and storyteller building the \
ultimate player database for an AI assistant called "El Capi" — the captain \
of World Cup 2026 knowledge. Your job is to make every player come alive with \
rich, accurate, fascinating data that fuels great conversations with fans.

Given a player's name and metadata, return a comprehensive JSON profile.

IMPORTANT RULES:
- Be ACCURATE. If you're unsure, use null — never fabricate stats or stories.
- Be SPECIFIC. "Scored a hat-trick vs Brazil in 2023 Copa America semifinal" \
  beats "scored important goals".
- Be BILINGUAL. Provide EN + ES for all narrative fields.
- Be a STORYTELLER. Origin stories, turning points, human moments.

Return ONLY valid JSON with this exact structure:

{
  "identity": {
    "full_legal_name": "Complete legal/birth name",
    "known_as": "Most common name fans use",
    "nicknames": [{"name": "La Pulga", "meaning": "The Flea — for his small stature and agility", "language": "es"}],
    "date_of_birth": "YYYY-MM-DD",
    "birth_city": "City",
    "birth_country": "Country",
    "nationality_primary": "Country",
    "nationality_secondary": "Country or null if not dual-national",
    "languages_spoken": ["Spanish", "English"],
    "height_cm": 170,
    "preferred_foot": "Left/Right/Both"
  },

  "career": {
    "current_club": "Club name",
    "current_league": "League name",
    "current_jersey_number": 10,
    "position_primary": "Centre-Forward",
    "position_secondary": "Right Winger or null",
    "career_trajectory": [
      {"club": "Club name", "years": "2004-2021", "note_en": "Brief note", "note_es": "Nota breve"}
    ],
    "international_caps": 178,
    "international_goals": 106,
    "international_debut": {"date": "2005-08-17", "opponent": "Hungary", "age": 18},
    "records_held": ["All-time top scorer for Argentina", "Most Ballon d'Or awards (8)"],
    "major_trophies": [
      {"trophy": "FIFA World Cup", "year": 2022, "team": "Argentina"},
      {"trophy": "Champions League", "year": 2015, "team": "FC Barcelona"}
    ]
  },

  "playing_style": {
    "style_summary_en": "2-3 sentences on how they play — be specific about what makes them unique",
    "style_summary_es": "Same in Spanish",
    "signature_moves": ["Inside-left cut from the right wing", "Low-driven free kicks"],
    "strengths": ["Close dribbling in tight spaces", "Vision and through-balls"],
    "weaknesses": ["Aerial duels", "Defensive work rate"],
    "comparable_to": {"player": "Diego Maradona", "reason_en": "Similar low center of gravity, dribbling genius, Argentine icon", "reason_es": "Similar centro de gravedad bajo, genio del regate, ícono argentino"},
    "best_partnership": {"player": "Neymar / Luis Suárez", "context_en": "MSN trident at Barcelona 2014-17 — one of the greatest attacking trios ever", "context_es": "Tridente MSN en el Barcelona 2014-17 — uno de los mejores tridentes ofensivos de la historia"}
  },

  "story": {
    "origin_story_en": "2-4 sentences about their path to football — childhood, family, hardships, discovery. Make it compelling.",
    "origin_story_es": "Same in Spanish",
    "breakthrough_moment": {
      "description_en": "The specific game/event that made them famous",
      "description_es": "Same in Spanish",
      "date": "YYYY-MM-DD or approximate",
      "context": "League match / World Cup / etc"
    },
    "career_defining_quote_by_player": {"quote_en": "What they said", "quote_es": "Lo que dijeron", "context": "When/where they said it"},
    "famous_quote_about_player": {"quote_en": "What someone said about them", "quote_es": "Lo que alguien dijo", "attributed_to": "Pep Guardiola"},
    "biggest_controversy": {"description_en": "Brief description or null", "description_es": "Descripción breve o null"},
    "career_summary_en": "3-4 sentence career narrative — arc, peaks, legacy",
    "career_summary_es": "Same in Spanish"
  },

  "personality": {
    "celebration_style": "Arms crossed / finger point to sky / knee slide — describe their iconic celebration",
    "superstitions_rituals": ["Always enters the pitch right foot first", "Touches the grass before kickoff"],
    "off_field_interests": ["Fashion", "Gaming", "Music production"],
    "charitable_work": "Foundation name and cause, or brief description, or null",
    "tattoo_meanings": ["Right arm: sleeve of family portraits", "Calf: World Cup trophy"],
    "social_media": {
      "instagram": "@handle or null",
      "twitter": "@handle or null",
      "tiktok": "@handle or null",
      "followers_approx": "500M across platforms"
    },
    "fun_facts": [
      "Was diagnosed with growth hormone deficiency at age 10 — Barcelona paid for his treatment",
      "His contract with Barcelona was first written on a napkin",
      "Holds the record for most goals in a calendar year (91 in 2012)"
    ],
    "music_taste": "Known to listen to cumbia and reggaeton, or null",
    "fashion_brands": "Nike athlete, has own clothing line with Adidas, or null"
  },

  "world_cup_2026": {
    "previous_wc_appearances": [
      {"year": 2022, "result": "Winner", "notable": "Scored twice in the final vs France"}
    ],
    "wc_qualifying_contribution": "5 goals and 3 assists in CONMEBOL qualifiers",
    "tournament_role_en": "Expected role and importance for their team",
    "tournament_role_es": "Same in Spanish",
    "narrative_arc_en": "Is this their last WC? First? Redemption? What's the story going in?",
    "narrative_arc_es": "Same in Spanish",
    "host_city_connection": "Any connection to the 16 host cities (US/Mexico/Canada) — played MLS, born nearby, etc. Null if none.",
    "injury_fitness_status": "Current fitness status heading into 2026, or null if healthy"
  },

  "big_game_dna": {
    "world_cup_goals": 13,
    "champions_league_goals": 129,
    "derby_performances_en": "Brief note on how they perform in big rivalries",
    "derby_performances_es": "Same in Spanish",
    "clutch_moments": [
      "92nd-minute winner vs Real Madrid in 2017 El Clásico",
      "Hat-trick in 2022 World Cup Final"
    ]
  },

  "market": {
    "estimated_value_eur": "€50M",
    "endorsement_brands": ["Adidas", "Pepsi", "Hard Rock Cafe"],
    "agent": "Jorge Messi / agency name or null"
  },

  "injury_history": {
    "notable_injuries": [
      {"injury": "Knee ligament tear", "date": "2020-11", "months_out": 3}
    ],
    "injury_prone": false
  },

  "meta": {
    "data_confidence": "high/medium/low",
    "data_gaps": ["Social media handles not confirmed", "Exact qualifying stats uncertain"]
  }
}

HOST CITIES for World Cup 2026 (check connections): """ + ", ".join(WC_2026_HOST_CITIES) + """

If you don't know a field, set it to null. For arrays, use empty [] if nothing known. \
ACCURACY over completeness — always.\
"""


def enrich_player(name: str, metadata: dict) -> dict | None:
    """Call ChatGPT to enrich a single player profile."""
    context_parts = [f"Player: {name}"]
    if metadata.get("current_club_name"):
        context_parts.append(f"Club: {metadata['current_club_name']}")
    if metadata.get("nationality"):
        context_parts.append(f"Nationality: {metadata['nationality']}")
    if metadata.get("position"):
        context_parts.append(f"Position: {metadata['position']}")
    if metadata.get("sub_position"):
        context_parts.append(f"Detailed position: {metadata['sub_position']}")
    if metadata.get("date_of_birth"):
        context_parts.append(f"DOB: {metadata['date_of_birth']}")
    if metadata.get("height_cm"):
        context_parts.append(f"Height: {metadata['height_cm']}cm")
    if metadata.get("market_value_eur"):
        context_parts.append(f"Market value: €{metadata['market_value_eur']:,}")
    if metadata.get("wc_team_code"):
        context_parts.append(f"World Cup 2026 national team: {metadata['wc_team_code']}")
    if metadata.get("foot"):
        context_parts.append(f"Preferred foot: {metadata['foot']}")
    if metadata.get("country_of_birth"):
        context_parts.append(f"Country of birth: {metadata['country_of_birth']}")
    if metadata.get("city_of_birth"):
        context_parts.append(f"City of birth: {metadata['city_of_birth']}")

    user_msg = "\n".join(context_parts)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=4000,
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
        print(f"JSON_PARSE_FAIL", end=" ")
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
):
    print("=" * 60)
    print("  EL CAPI — Full Player Enrichment (v2)")
    print("=" * 60)

    latest_path = OUTPUT_DIR / "players_canonical_latest.json"
    if not latest_path.exists():
        print(f"  ERROR: Run the pipeline first. Missing: {latest_path}")
        sys.exit(1)

    with open(latest_path) as f:
        players = json.load(f)

    print(f"  Loaded {len(players):,} players from canonical list")

    if single_player:
        query = unidecode(single_player).lower()
        players = [p for p in players if query in unidecode(p.get("name") or "").lower()]
        if not players:
            print(f"  Player '{single_player}' not found.")
            return
        print(f"  Enriching single player: {players[0]['name']}")
    elif wc_only:
        players = [p for p in players if p.get("in_wc_squad")]
        print(f"  Filtered to {len(players)} WC 2026 squad players")

    checkpoint = load_checkpoint() if resume else {"completed": [], "enriched_data": {}, "total_tokens": 0, "total_cost_usd": 0.0}
    completed_set = set(checkpoint["completed"])

    remaining = [p for p in players if p.get("source_id") not in completed_set]
    to_process = remaining[:batch_size]

    print(f"  Already enriched: {len(completed_set)}")
    print(f"  Remaining: {len(remaining)}")
    print(f"  Processing this batch: {len(to_process)}")
    print(f"  Estimated cost: ~${len(to_process) * 0.003:.2f}")
    print()

    start_time = time.time()
    success = 0
    failed = 0

    for i, player in enumerate(to_process):
        name = player.get("name", "Unknown")
        pid = player.get("source_id", "?")
        team = player.get("wc_team_code", "")
        team_tag = f" [{team}]" if team else ""
        print(f"  [{i+1}/{len(to_process)}] {name}{team_tag}...", end=" ", flush=True)

        enriched = enrich_player(name, player)
        if enriched:
            tokens = enriched.get("_tokens", {})
            total_tok = tokens.get("total", 0)
            cost = total_tok * 0.00000015 + tokens.get("completion", 0) * 0.0000006

            checkpoint["enriched_data"][pid] = {
                "source_id": pid,
                "name": name,
                "wc_team_code": player.get("wc_team_code"),
                **enriched,
                "enriched_at": datetime.now().isoformat(),
            }
            checkpoint["completed"].append(pid)
            checkpoint["total_tokens"] = checkpoint.get("total_tokens", 0) + total_tok
            checkpoint["total_cost_usd"] = checkpoint.get("total_cost_usd", 0.0) + cost

            confidence = enriched.get("meta", {}).get("data_confidence", "?")
            print(f"OK ({confidence}, {total_tok} tok)")
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

    with open(ENRICHMENT_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(list(checkpoint["enriched_data"].values()), f, ensure_ascii=False, indent=2, default=str)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  ENRICHMENT COMPLETE")
    print(f"  Players enriched: {success} ok, {failed} failed")
    print(f"  Total in database: {len(checkpoint['enriched_data'])}")
    print(f"  Tokens used: {checkpoint['total_tokens']:,}")
    print(f"  Cost: ${checkpoint['total_cost_usd']:.3f}")
    print(f"  Time: {elapsed/60:.1f} min")
    print(f"  Output: {ENRICHMENT_OUTPUT}")
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

    run_enrichment(wc_only=wc_only, single_player=single, batch_size=batch, resume=do_resume)
