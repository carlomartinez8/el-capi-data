"""
Push enriched player data directly to Supabase via REST API.
Bypasses SQL Editor size limits.

Usage: python push_to_supabase.py
"""

import json
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
CANONICAL = Path(__file__).parent / "data" / "output" / "players_canonical.json"

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required in .env")
    sys.exit(1)

try:
    from supabase import create_client
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"ERROR connecting to Supabase: {e}")
    sys.exit(1)


def parse_value_eur(market: dict):
    val = market.get("estimated_value_eur") or market.get("market_value")
    if not val:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).lower().replace("€", "").replace("$", "").replace(",", "").strip()
    multiplier = 1
    if "million" in s or s.endswith("m"):
        multiplier = 1_000_000
        s = re.sub(r"(million|m)", "", s).strip()
    elif "billion" in s or s.endswith("b"):
        multiplier = 1_000_000_000
        s = re.sub(r"(billion|b)", "", s).strip()
    elif "k" in s:
        multiplier = 1_000
        s = re.sub(r"k", "", s).strip()
    try:
        return int(float(s) * multiplier)
    except (ValueError, TypeError):
        return None


def safe_str(val):
    if val is None:
        return None
    if isinstance(val, list):
        return [str(v) if not isinstance(v, str) else v for v in val if v]
    return str(val) if not isinstance(val, str) else val


def safe_int(val):
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def parse_contract_date(val):
    """Convert 'June 2025' style strings to '2025-06-30' date format."""
    if not val or not isinstance(val, str):
        return None
    val = val.strip()
    import re as _re
    # Already ISO: 2025-06-30
    if _re.match(r"^\d{4}-\d{2}-\d{2}$", val):
        return val
    # Year only: 2025
    if _re.match(r"^\d{4}$", val):
        return f"{val}-06-30"
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    low = val.lower()
    for month_name, month_num in months.items():
        if month_name in low:
            year_match = _re.search(r"(\d{4})", val)
            if year_match:
                return f"{year_match.group(1)}-{month_num}-28"
    return None


def safe_list(val):
    if not val or not isinstance(val, list):
        return []
    result = []
    for v in val:
        if isinstance(v, str):
            result.append(v)
        elif isinstance(v, dict):
            result.append(json.dumps(v, ensure_ascii=False))
        else:
            result.append(str(v))
    return result


def build_player_row(p):
    ident = p.get("identity", {})
    story = p.get("story", {})
    personality = p.get("personality", {})
    injury = p.get("injury_history", {})
    meta = p.get("meta", {})

    social = personality.get("social_media")
    if isinstance(social, dict):
        social = json.dumps(social, ensure_ascii=False)
    elif social:
        social = str(social)
    else:
        social = None

    nicknames_raw = ident.get("nicknames", [])
    if isinstance(nicknames_raw, list):
        nicknames = []
        for n in nicknames_raw:
            if isinstance(n, str):
                nicknames.append(n)
            elif isinstance(n, dict):
                nicknames.append(n.get("nickname", str(n)))
            else:
                nicknames.append(str(n))
    else:
        nicknames = []

    notable_injuries_raw = injury.get("notable_injuries", [])
    if isinstance(notable_injuries_raw, list):
        notable_injuries = []
        for inj in notable_injuries_raw:
            if isinstance(inj, str):
                notable_injuries.append(inj)
            elif isinstance(inj, dict):
                notable_injuries.append(json.dumps(inj, ensure_ascii=False))
            else:
                notable_injuries.append(str(inj))
    else:
        notable_injuries = []

    return {
        "id": p["canonical_id"],
        "full_legal_name": safe_str(ident.get("full_legal_name") or p.get("name")),
        "known_as": safe_str(ident.get("known_as") or p.get("name")),
        "date_of_birth": safe_str(ident.get("date_of_birth")),
        "birth_city": safe_str(ident.get("birth_city")),
        "birth_country": safe_str(ident.get("birth_country")),
        "height_cm": safe_int(ident.get("height_cm")),
        "preferred_foot": safe_str(ident.get("preferred_foot")),
        "nationality_primary": safe_str(ident.get("nationality_primary")) or "Unknown",
        "nationality_secondary": safe_str(ident.get("nationality_secondary")),
        "languages_spoken": safe_list(ident.get("languages_spoken")),
        "nicknames": nicknames,
        "origin_story_en": safe_str(story.get("origin_story_en")),
        "origin_story_es": safe_str(story.get("origin_story_es")),
        "career_summary_en": safe_str(story.get("career_summary_en")),
        "career_summary_es": safe_str(story.get("career_summary_es")),
        "breakthrough_moment": safe_str(story.get("breakthrough_moment")),
        "career_defining_quote": safe_str(story.get("career_defining_quote_by_player") or story.get("career_defining_quote")),
        "famous_quote_about": safe_str(story.get("famous_quote_about_player") or story.get("famous_quote_about")),
        "biggest_controversy": safe_str(story.get("biggest_controversy")),
        "celebration_style": safe_str(personality.get("celebration_style")),
        "off_field_interests": safe_list(personality.get("off_field_interests")),
        "charitable_work": safe_str(personality.get("charitable_work")),
        "superstitions": safe_list(personality.get("superstitions_rituals") or personality.get("superstitions")),
        "tattoo_meanings": safe_list(personality.get("tattoo_meanings")),
        "fun_facts": safe_list(personality.get("fun_facts")),
        "social_media": social,
        "music_taste": safe_str(personality.get("music_taste")),
        "fashion_brands": safe_str(personality.get("fashion_brands")),
        "injury_prone": injury.get("injury_prone") if isinstance(injury.get("injury_prone"), bool) else None,
        "notable_injuries": notable_injuries,
        "data_confidence": safe_str(meta.get("data_confidence")),
        "data_gaps": safe_list(meta.get("data_gaps")),
        "enriched_at": safe_str(p.get("enriched_at")),
    }


def build_career_row(p):
    career = p.get("career", {})
    style = p.get("playing_style", {})
    market = p.get("market", {})

    career_traj = career.get("career_trajectory", [])
    if isinstance(career_traj, list):
        career_traj = json.dumps(career_traj, ensure_ascii=False)
    elif career_traj:
        career_traj = str(career_traj)
    else:
        career_traj = None

    return {
        "player_id": p["canonical_id"],
        "current_club": safe_str(career.get("current_club")),
        "current_league": safe_str(career.get("current_league")),
        "current_jersey_number": safe_str(career.get("current_jersey_number")),
        "position_primary": safe_str(career.get("position_primary")),
        "position_secondary": safe_str(career.get("position_secondary")),
        "contract_expires": parse_contract_date(career.get("contract_expires")),
        "agent": safe_str(career.get("agent")),
        "estimated_value_eur": parse_value_eur(market),
        "endorsement_brands": safe_list(market.get("endorsement_brands")),
        "career_trajectory": career_traj,
        "major_trophies": safe_list(career.get("major_trophies")),
        "records_held": safe_list(career.get("records_held")),
        "style_summary_en": safe_str(style.get("style_summary_en")),
        "style_summary_es": safe_str(style.get("style_summary_es")),
        "signature_moves": safe_list(style.get("signature_moves")),
        "strengths": safe_list(style.get("strengths")),
        "weaknesses": safe_list(style.get("weaknesses")),
        "comparable_to": safe_str(style.get("comparable_to")),
        "best_partnership": safe_str(style.get("best_partnership")),
        "refresh_source": "enrichment_v1",
    }


def build_tournament_row(p):
    wc = p.get("world_cup_2026", {})
    bgd = p.get("big_game_dna", {})
    career = p.get("career", {})

    clutch = bgd.get("clutch_moments", [])
    if isinstance(clutch, list):
        clutch = json.dumps(clutch, ensure_ascii=False)
    elif clutch:
        clutch = str(clutch)
    else:
        clutch = None

    prev_wc = wc.get("previous_wc_appearances", [])
    if isinstance(prev_wc, list):
        prev_wc = json.dumps(prev_wc, ensure_ascii=False)
    elif prev_wc:
        prev_wc = str(prev_wc)
    else:
        prev_wc = None

    return {
        "player_id": p["canonical_id"],
        "wc_team_code": safe_str(p.get("wc_team_code")),
        "jersey_number": safe_int(wc.get("jersey_number")),
        "captain": wc.get("captain", False) if isinstance(wc.get("captain"), bool) else False,
        "in_squad": True,
        "international_caps": safe_int(career.get("international_caps")),
        "international_goals": safe_int(career.get("international_goals")),
        "international_debut": safe_str(career.get("international_debut")),
        "tournament_role_en": safe_str(wc.get("tournament_role_en")),
        "tournament_role_es": safe_str(wc.get("tournament_role_es")),
        "narrative_arc_en": safe_str(wc.get("narrative_arc_en")),
        "narrative_arc_es": safe_str(wc.get("narrative_arc_es")),
        "injury_fitness_status": safe_str(wc.get("injury_fitness_status")),
        "wc_qualifying_contribution": safe_str(wc.get("wc_qualifying_contribution")),
        "world_cup_goals": safe_int(bgd.get("world_cup_goals", 0)),
        "champions_league_goals": safe_int(bgd.get("champions_league_goals", 0)),
        "derby_performances_en": safe_str(bgd.get("derby_performances_en")),
        "derby_performances_es": safe_str(bgd.get("derby_performances_es")),
        "clutch_moments": clutch,
        "previous_wc_appearances": prev_wc,
        "host_city_connection": safe_str(wc.get("host_city_connection")),
    }


def build_aliases(p):
    cid = p["canonical_id"]
    ident = p.get("identity", {})
    rows = []

    source_id = p.get("source_id")
    if source_id:
        rows.append({"player_id": cid, "alias_type": "transfermarkt_id", "alias_value": str(source_id)})

    known_as = ident.get("known_as", "")
    full_name = ident.get("full_legal_name", "")
    if known_as and known_as != full_name:
        rows.append({"player_id": cid, "alias_type": "alternate_name", "alias_value": known_as})

    for nick in ident.get("nicknames", []):
        nick_str = nick if isinstance(nick, str) else nick.get("nickname", "") if isinstance(nick, dict) else ""
        if nick_str:
            rows.append({"player_id": cid, "alias_type": "nickname", "alias_value": nick_str})

    return rows


def upsert_batch(table, rows, batch_size=50):
    total = len(rows)
    success = 0
    errors = 0
    for i in range(0, total, batch_size):
        batch = rows[i:i + batch_size]
        try:
            sb.table(table).upsert(batch, on_conflict="id" if table == "players" else "player_id" if table in ("player_career", "player_tournament") else "").execute()
            success += len(batch)
        except Exception as e:
            err_msg = str(e)
            if "duplicate" in err_msg.lower() or "conflict" in err_msg.lower():
                success += len(batch)
            else:
                errors += len(batch)
                print(f"    ERROR batch {i//batch_size}: {err_msg[:120]}")
        if i % 200 == 0 and i > 0:
            print(f"    {table}: {i}/{total}...")
            time.sleep(0.1)
    return success, errors


def insert_batch_no_conflict(table, rows, batch_size=50):
    total = len(rows)
    success = 0
    errors = 0
    for i in range(0, total, batch_size):
        batch = rows[i:i + batch_size]
        try:
            sb.table(table).insert(batch).execute()
            success += len(batch)
        except Exception as e:
            err_msg = str(e)
            if "duplicate" in err_msg.lower() or "conflict" in err_msg.lower() or "unique" in err_msg.lower():
                for row in batch:
                    try:
                        sb.table(table).insert(row).execute()
                        success += 1
                    except:
                        success += 1
            else:
                errors += len(batch)
                print(f"    ERROR batch {i//batch_size}: {err_msg[:120]}")
        if i % 200 == 0 and i > 0:
            print(f"    {table}: {i}/{total}...")
            time.sleep(0.1)
    return success, errors


RECONCILIATION_REPORT = Path(__file__).parent / "data" / "output" / "reconciliation_report.json"


def _load_blocked_ids() -> set[str]:
    """Load canonical IDs of players blocked by reconciliation."""
    if not RECONCILIATION_REPORT.exists():
        return set()
    with open(RECONCILIATION_REPORT) as f:
        report = json.load(f)
    blocked = set()
    for p in report.get("players", []):
        if p.get("blocked"):
            blocked.add(p["canonical_id"])
    return blocked


def main(skip_blocked: bool = True):
    print("=" * 60)
    print("  EL CAPI — Push to Supabase (REST API)")
    print("=" * 60)
    print(f"  URL: {SUPABASE_URL[:40]}...")
    print(f"  Source: {CANONICAL}")

    with open(CANONICAL) as f:
        players = json.load(f)
    print(f"  Total players in canonical: {len(players)}")

    blocked_ids = set()
    if skip_blocked:
        blocked_ids = _load_blocked_ids()
        if blocked_ids:
            original_count = len(players)
            players = [p for p in players if p["canonical_id"] not in blocked_ids]
            print(f"  Blocked by reconciliation: {original_count - len(players)}")
            print(f"  Players to push: {len(players)}")
        else:
            print("  No reconciliation report found or no blocked players — pushing all.")

    # Build all rows
    print("\n  Building rows...")
    player_rows = [build_player_row(p) for p in players]
    career_rows = [build_career_row(p) for p in players]
    tournament_rows = [build_tournament_row(p) for p in players]
    alias_rows = []
    for p in players:
        alias_rows.extend(build_aliases(p))

    print(f"    players:          {len(player_rows)}")
    print(f"    player_career:    {len(career_rows)}")
    print(f"    player_tournament:{len(tournament_rows)}")
    print(f"    player_aliases:   {len(alias_rows)}")

    # Push in order (players first — FK parent)
    print("\n  Pushing players...")
    s, e = upsert_batch("players", player_rows)
    print(f"    ✅ players: {s} ok, {e} errors")

    print("  Pushing player_career...")
    s, e = upsert_batch("player_career", career_rows)
    print(f"    ✅ player_career: {s} ok, {e} errors")

    print("  Pushing player_tournament...")
    s, e = upsert_batch("player_tournament", tournament_rows)
    print(f"    ✅ player_tournament: {s} ok, {e} errors")

    print("  Pushing player_aliases...")
    s, e = insert_batch_no_conflict("player_aliases", alias_rows)
    print(f"    ✅ player_aliases: {s} ok, {e} errors")

    print("\n" + "=" * 60)
    print("  DONE")
    print("=" * 60)


if __name__ == "__main__":
    skip = "--skip-blocked" not in sys.argv
    if "--no-skip-blocked" in sys.argv:
        skip = False
    main(skip_blocked=skip)
