"""
Golden Output Combiner — merges source-priority facts with GPT narratives
into the final canonical output that feeds the admin app and Supabase.

Reads:
  - players_merged.json      (field-level source-attributed FACTS)
  - players_narratives.json  (GPT narrative-only sections)
  - players_canonical_latest.json (flat source — for photo_url, foot, etc.)

Writes:
  - players_golden.json      (the ONE canonical output everything reads)

The golden output has the same NESTED structure the admin app and
to_supabase.py expect, but facts come from the merge (not GPT).
"""

import json
import uuid
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from pipeline.config import OUTPUT_DIR, POSITION_MAP


MERGED_PATH = OUTPUT_DIR / "players_merged.json"
NARRATIVES_PATH = OUTPUT_DIR / "players_narratives.json"
FLAT_CANONICAL_PATH = OUTPUT_DIR / "players_canonical_latest.json"
GOLDEN_OUTPUT = OUTPUT_DIR / "players_golden.json"


def normalize_name(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_only.lower()).strip()


def extract_surname(full_name: str) -> str:
    parts = normalize_name(full_name).split()
    return parts[-1] if parts else ""


def primary_key(name: str, dob: str | None, team: str) -> str | None:
    if not dob or not team or not name:
        return None
    surname = extract_surname(name)
    return f"{surname}|{dob}|{team.upper()}"


def fallback_key(name: str, team: str, club: str) -> str:
    norm = normalize_name(name)
    club_norm = normalize_name(club or "unknown")
    return f"{norm}|{team.upper()}|{club_norm}"


def run_combine() -> list[dict]:
    """
    Combine merged facts + GPT narratives into the golden canonical output.

    Returns the list of golden player records.
    """
    print("=" * 60)
    print("  GOLDEN OUTPUT COMBINER")
    print("=" * 60)

    # ── Load merged facts ──
    print(f"\n  Loading merged facts: {MERGED_PATH}")
    with open(MERGED_PATH) as f:
        merged_players = json.load(f)
    print(f"  Merged players: {len(merged_players)}")

    # ── Load flat canonical for supplementary fields ──
    print(f"  Loading flat canonical: {FLAT_CANONICAL_PATH}")
    with open(FLAT_CANONICAL_PATH) as f:
        flat_players = json.load(f)
    flat_by_source = {str(p.get("source_id", "")): p for p in flat_players}
    print(f"  Flat canonical: {len(flat_players):,} total")

    # ── Load GPT narratives (optional — may not exist yet) ──
    narratives_by_source: dict[str, dict] = {}
    if NARRATIVES_PATH.exists():
        print(f"  Loading narratives: {NARRATIVES_PATH}")
        with open(NARRATIVES_PATH) as f:
            narratives = json.load(f)
        narratives_by_source = {str(n.get("source_id", "")): n for n in narratives}
        print(f"  Narratives: {len(narratives_by_source)} players")
    else:
        print(f"  ⚠ No narratives file found — facts-only golden output")

    # ── Load existing enriched data for narrative fallback ──
    enriched_path = OUTPUT_DIR / "players_enriched.json"
    enriched_by_source: dict[str, dict] = {}
    if enriched_path.exists() and not NARRATIVES_PATH.exists():
        print(f"  Loading existing enriched data as narrative fallback: {enriched_path}")
        with open(enriched_path) as f:
            enriched = json.load(f)
        enriched_by_source = {str(e.get("source_id", "")): e for e in enriched}
        print(f"  Enriched fallback: {len(enriched_by_source)} players")

    # ── Build golden output ──
    golden: list[dict] = []
    canonical_map: dict[str, str] = {}  # dedup_key → canonical_id
    stats = {"total": 0, "with_narratives": 0, "with_enriched_fallback": 0, "facts_only": 0}

    for mp in merged_players:
        source_id = str(mp.get("source_id", ""))
        name = mp.get("name", "")
        team = mp.get("wc_team_code", "")
        fields = mp.get("fields", {})

        # Get fact values from merge
        def fv(field_name: str):
            """Get field value from merged data."""
            return fields.get(field_name, {}).get("value")

        dob = fv("date_of_birth")
        position = fv("position")
        club = fv("current_club")
        league = fv("current_league")
        market_val = fv("market_value_eur")
        height = fv("height_cm")
        jersey = fv("jersey_number")
        captain = fv("captain")
        nationality = fv("nationality")
        agent = fv("agent")
        contract = fv("contract_expires")
        caps = fv("international_caps")
        goals = fv("international_goals")
        photo = fv("photo_url")
        career_traj = fv("career_trajectory")
        trophies = fv("major_trophies")

        # Supplementary fields from flat canonical
        flat = flat_by_source.get(source_id, {})
        foot = flat.get("foot")
        birth_city = flat.get("city_of_birth")
        birth_country = flat.get("country_of_birth")
        first_name = flat.get("first_name")
        last_name = flat.get("last_name")
        sub_position = flat.get("sub_position")
        tm_url = flat.get("transfermarkt_url")

        # ── Canonical ID assignment (deterministic dedup) ──
        pk = primary_key(name, dob, team)
        if pk:
            dedup_key = pk
        else:
            dedup_key = fallback_key(name, team, club or "")

        if dedup_key in canonical_map:
            # Collision — skip duplicate
            continue

        canonical_id = str(uuid.uuid4())
        canonical_map[dedup_key] = canonical_id

        # ── Get narrative data ──
        narrative = narratives_by_source.get(source_id, {})
        enriched_fb = enriched_by_source.get(source_id, {})

        def get_narrative(section: str, field: str, default=None):
            """Get narrative field from narratives first, then enriched fallback."""
            val = narrative.get(section, {}).get(field)
            if val is not None:
                return val
            val = enriched_fb.get(section, {}).get(field)
            if val is not None:
                return val
            return default

        has_narrative = bool(narrative)
        has_enriched = bool(enriched_fb) and not has_narrative

        if has_narrative:
            stats["with_narratives"] += 1
        elif has_enriched:
            stats["with_enriched_fallback"] += 1
        else:
            stats["facts_only"] += 1

        # ── Parse career trajectory ──
        traj_parsed = []
        if career_traj:
            if isinstance(career_traj, str):
                try:
                    traj_parsed = json.loads(career_traj)
                except (json.JSONDecodeError, TypeError):
                    traj_parsed = []
            elif isinstance(career_traj, list):
                traj_parsed = career_traj

        # ── Parse major trophies ──
        trophies_parsed = []
        if trophies:
            if isinstance(trophies, list):
                trophies_parsed = trophies
            elif isinstance(trophies, str):
                try:
                    trophies_parsed = json.loads(trophies)
                except (json.JSONDecodeError, TypeError):
                    trophies_parsed = [trophies]

        # ── Build nested golden record ──
        # Identity section — FACTS from merge + flat
        identity = {
            "full_legal_name": f"{first_name} {last_name}".strip() if first_name and last_name else name,
            "known_as": name,
            "nicknames": get_narrative("identity", "nicknames", []),
            "date_of_birth": dob,
            "birth_city": birth_city,
            "birth_country": birth_country,
            "nationality_primary": nationality,
            "nationality_secondary": get_narrative("identity", "nationality_secondary"),
            "languages_spoken": get_narrative("identity", "languages_spoken", []),
            "height_cm": int(height) if height else None,
            "preferred_foot": foot or get_narrative("identity", "preferred_foot"),
            "photo_url": photo,
        }

        # Career section — FACTS from merge + flat
        career = {
            "current_club": club,
            "current_league": league,
            "current_jersey_number": int(jersey) if jersey else None,
            "position_primary": position or sub_position,
            "position_secondary": get_narrative("career", "position_secondary"),
            "career_trajectory": traj_parsed or get_narrative("career", "career_trajectory", []),
            "international_caps": int(caps) if caps else get_narrative("career", "international_caps"),
            "international_goals": int(goals) if goals else get_narrative("career", "international_goals"),
            "international_debut": get_narrative("career", "international_debut"),
            "records_held": get_narrative("career", "records_held", []),
            "major_trophies": trophies_parsed or get_narrative("career", "major_trophies", []),
            "contract_expires": contract,
            "agent": agent,
        }

        # Market section — FACTS from merge
        market = {
            "estimated_value_eur": int(market_val) if market_val else None,
            "endorsement_brands": get_narrative("market", "endorsement_brands", []),
            "agent": agent,
        }

        # Narrative sections — ALL from GPT
        playing_style = {
            "style_summary_en": get_narrative("playing_style", "style_summary_en"),
            "style_summary_es": get_narrative("playing_style", "style_summary_es"),
            "signature_moves": get_narrative("playing_style", "signature_moves", []),
            "strengths": get_narrative("playing_style", "strengths", []),
            "weaknesses": get_narrative("playing_style", "weaknesses", []),
            "comparable_to": get_narrative("playing_style", "comparable_to"),
            "best_partnership": get_narrative("playing_style", "best_partnership"),
        }

        story = {
            "origin_story_en": get_narrative("story", "origin_story_en"),
            "origin_story_es": get_narrative("story", "origin_story_es"),
            "breakthrough_moment": get_narrative("story", "breakthrough_moment"),
            "career_defining_quote_by_player": get_narrative("story", "career_defining_quote_by_player"),
            "famous_quote_about_player": get_narrative("story", "famous_quote_about_player"),
            "biggest_controversy": get_narrative("story", "biggest_controversy"),
            "career_summary_en": get_narrative("story", "career_summary_en"),
            "career_summary_es": get_narrative("story", "career_summary_es"),
        }

        personality = {
            "celebration_style": get_narrative("personality", "celebration_style"),
            "superstitions_rituals": get_narrative("personality", "superstitions_rituals", []),
            "off_field_interests": get_narrative("personality", "off_field_interests", []),
            "charitable_work": get_narrative("personality", "charitable_work"),
            "tattoo_meanings": get_narrative("personality", "tattoo_meanings", []),
            "social_media": get_narrative("personality", "social_media", {}),
            "fun_facts": get_narrative("personality", "fun_facts", []),
            "music_taste": get_narrative("personality", "music_taste"),
            "fashion_brands": get_narrative("personality", "fashion_brands"),
        }

        world_cup_2026 = {
            "previous_wc_appearances": get_narrative("world_cup_2026", "previous_wc_appearances", []),
            "wc_qualifying_contribution": get_narrative("world_cup_2026", "wc_qualifying_contribution"),
            "tournament_role_en": get_narrative("world_cup_2026", "tournament_role_en"),
            "tournament_role_es": get_narrative("world_cup_2026", "tournament_role_es"),
            "narrative_arc_en": get_narrative("world_cup_2026", "narrative_arc_en"),
            "narrative_arc_es": get_narrative("world_cup_2026", "narrative_arc_es"),
            "host_city_connection": get_narrative("world_cup_2026", "host_city_connection"),
            "injury_fitness_status": get_narrative("world_cup_2026", "injury_fitness_status"),
        }

        big_game_dna = {
            "world_cup_goals": get_narrative("big_game_dna", "world_cup_goals", 0),
            "champions_league_goals": get_narrative("big_game_dna", "champions_league_goals", 0),
            "derby_performances_en": get_narrative("big_game_dna", "derby_performances_en"),
            "derby_performances_es": get_narrative("big_game_dna", "derby_performances_es"),
            "clutch_moments": get_narrative("big_game_dna", "clutch_moments", []),
        }

        injury_history = {
            "notable_injuries": get_narrative("injury_history", "notable_injuries", []),
            "injury_prone": get_narrative("injury_history", "injury_prone", False),
        }

        # Source attribution
        source_summary = {}
        for field_name, field_data in fields.items():
            src = field_data.get("source")
            if src:
                source_summary[field_name] = src

        meta = {
            "data_confidence": "high" if dob and position and club else ("medium" if dob or position else "low"),
            "data_gaps": get_narrative("meta", "data_gaps", []),
            "primary_source": source_summary.get("date_of_birth", "none"),
            "source_attribution": source_summary,
        }

        golden_record = {
            "canonical_id": canonical_id,
            "source_id": source_id,
            "name": name,
            "wc_team_code": team,
            "in_wc_squad": True,
            "identity": identity,
            "career": career,
            "playing_style": playing_style,
            "story": story,
            "personality": personality,
            "world_cup_2026": world_cup_2026,
            "big_game_dna": big_game_dna,
            "market": market,
            "injury_history": injury_history,
            "meta": meta,
            "enriched_at": narrative.get("enriched_at") or enriched_fb.get("enriched_at") or datetime.now().isoformat(),
            "golden_at": datetime.now().isoformat(),
        }

        golden.append(golden_record)
        stats["total"] += 1

    # ── Write golden output ──
    print(f"\n  Writing golden output: {GOLDEN_OUTPUT}")
    with open(GOLDEN_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(golden, f, indent=2, ensure_ascii=False, default=str)

    # ── Also write to players_canonical.json for backward compat ──
    compat_path = OUTPUT_DIR / "players_canonical.json"
    print(f"  Writing backward-compatible canonical: {compat_path}")
    with open(compat_path, "w", encoding="utf-8") as f:
        json.dump(golden, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n  Stats:")
    print(f"    Total golden players:      {stats['total']}")
    print(f"    With GPT narratives:       {stats['with_narratives']}")
    print(f"    With enriched fallback:    {stats['with_enriched_fallback']}")
    print(f"    Facts only (no narrative): {stats['facts_only']}")

    return golden


if __name__ == "__main__":
    result = run_combine()
    # Quick sample
    for p in result[:2]:
        name = p["name"]
        dob = p["identity"]["date_of_birth"]
        pos = p["career"]["position_primary"]
        club = p["career"]["current_club"]
        src = p["meta"].get("primary_source", "?")
        has_story = bool(p["story"].get("origin_story_en"))
        print(f"  {name}: DOB={dob}, pos={pos}, club={club}, src={src}, story={'✓' if has_story else '✗'}")
