"""
Source Priority Merge — loads all 4 data sources and builds a per-player
field map with source attribution for every critical field.

Sources (highest → lowest priority):
  1. Transfermarkt CSV  (ground-truth for clubs, DOB, position, value, contracts)
  2. Static bios        (hand-curated caps, goals, achievements, DOB)
  3. Static squads      (jersey number, captain, position)
  4. GPT enrichment     (narrative fields, fills gaps)

Usage:
    python -m pipeline.reconcile.merge
"""

import json
import math
import re
import unicodedata
from pathlib import Path

import pandas as pd

from pipeline.config import (
    TRANSFERMARKT_DATA_DIR,
    COMPETITION_ID_TO_LEAGUE,
    OUTPUT_DIR,
)
from pipeline.ingest.static_bios import load_static_bios
from pipeline.ingest.static_squads import load_static_squads
from pipeline.reconcile.career_builder import build_career_trajectories, format_trajectory_text


CANONICAL_PATH = OUTPUT_DIR / "players_canonical.json"
MERGED_OUTPUT = OUTPUT_DIR / "players_merged.json"

CRITICAL_FIELDS = [
    "current_club",
    "current_league",
    "date_of_birth",
    "position",
    "market_value_eur",
    "contract_expires",
    "agent",
    "international_caps",
    "international_goals",
    "career_trajectory",
    "jersey_number",
    "captain",
    "major_trophies",
    "height_cm",
    "photo_url",
    "nationality",
]


def _to_slug(name: str) -> str:
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    return slug


def _clean(val):
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    if isinstance(val, str) and val.strip() in ("", "None", "null", "N/A", "Unknown"):
        return None
    return val


def _parse_market_value(val) -> int | None:
    """Normalize market value strings to integer EUR."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        v = int(val)
        return v if v > 0 else None
    s = str(val).lower().replace("€", "").replace("$", "").replace(",", "").strip()
    mult = 1
    if "million" in s or s.endswith("m"):
        mult = 1_000_000
        s = re.sub(r"(million|m)", "", s).strip()
    elif "billion" in s or s.endswith("b"):
        mult = 1_000_000_000
        s = re.sub(r"(billion|b)", "", s).strip()
    elif "k" in s:
        mult = 1_000
        s = re.sub(r"k", "", s).strip()
    try:
        return int(float(s) * mult)
    except (ValueError, TypeError):
        return None


def _parse_height(val) -> int | None:
    """Normalize height to cm integer."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val) if val > 0 else None
    s = str(val).strip()
    m = re.match(r"(\d+)[.,](\d+)\s*m", s)
    if m:
        return int(m.group(1)) * 100 + int(m.group(2))
    m2 = re.match(r"(\d+)\s*cm", s)
    if m2:
        return int(m2.group(1))
    try:
        v = int(float(s))
        return v if 100 < v < 250 else None
    except (ValueError, TypeError):
        return None


def load_transfermarkt_lookup() -> dict[str, dict]:
    """Load TM players.csv into a dict keyed by player_id (string)."""
    path = TRANSFERMARKT_DATA_DIR / "players.csv"
    print(f"  Loading Transfermarkt: {path}")
    df = pd.read_csv(path)
    lookup: dict[str, dict] = {}
    for _, row in df.iterrows():
        pid = str(int(row["player_id"])) if pd.notna(row.get("player_id")) else None
        if not pid:
            continue
        lookup[pid] = {
            "current_club": _clean(row.get("current_club_name")),
            "current_league_id": _clean(row.get("current_club_domestic_competition_id")),
            "date_of_birth": str(row["date_of_birth"])[:10] if pd.notna(row.get("date_of_birth")) else None,
            "position": _clean(row.get("sub_position")) or _clean(row.get("position")),
            "market_value_eur": int(float(row["market_value_in_eur"])) if pd.notna(row.get("market_value_in_eur")) else None,
            "contract_expires": str(row["contract_expiration_date"])[:10] if pd.notna(row.get("contract_expiration_date")) else None,
            "agent": _clean(row.get("agent_name")),
            "height_cm": int(float(row["height_in_cm"])) if pd.notna(row.get("height_in_cm")) else None,
            "photo_url": _clean(row.get("image_url")),
            "nationality": _clean(row.get("country_of_citizenship")),
            "foot": _clean(row.get("foot")),
        }
    print(f"  Transfermarkt: {len(lookup):,} players indexed")
    return lookup


def load_squads_lookup() -> dict[str, dict]:
    """Load static squads into a dict keyed by slug."""
    df = load_static_squads()
    lookup: dict[str, dict] = {}
    for _, row in df.iterrows():
        slug = _to_slug(row.get("name", ""))
        if slug:
            lookup[slug] = {
                "position": _clean(row.get("position")),
                "current_club": _clean(row.get("current_club_name")),
                "jersey_number": int(row["jersey_number"]) if pd.notna(row.get("jersey_number")) else None,
                "captain": row.get("captain", False),
                "wc_team_code": row.get("wc_team_code"),
            }
    return lookup


def _extract_gpt_fields(player: dict) -> dict:
    """Pull critical fields from the GPT-enriched canonical player record."""
    ident = player.get("identity", {})
    career = player.get("career", {})
    market = player.get("market", {})

    traj = career.get("career_trajectory", [])
    if isinstance(traj, list):
        traj_text = json.dumps(traj, ensure_ascii=False) if traj else None
    elif traj:
        traj_text = str(traj)
    else:
        traj_text = None

    return {
        "current_club": _clean(career.get("current_club")),
        "current_league": _clean(career.get("current_league")),
        "date_of_birth": _clean(ident.get("date_of_birth")),
        "position": _clean(career.get("position_primary")),
        "market_value_eur": _parse_market_value(market.get("estimated_value_eur")),
        "contract_expires": _clean(career.get("contract_expires")),
        "agent": _clean(market.get("agent") or career.get("agent")),
        "international_caps": int(career["international_caps"]) if career.get("international_caps") else None,
        "international_goals": int(career["international_goals"]) if career.get("international_goals") else None,
        "career_trajectory": traj_text,
        "jersey_number": int(career["current_jersey_number"]) if career.get("current_jersey_number") else None,
        "captain": None,
        "major_trophies": career.get("major_trophies"),
        "height_cm": int(ident["height_cm"]) if ident.get("height_cm") else None,
        "photo_url": None,
        "nationality": _clean(ident.get("nationality_primary")),
    }


def run_merge() -> list[dict]:
    """
    Build a merged field map for every canonical player.

    Returns a list of dicts, each with:
      - player metadata (canonical_id, name, wc_team_code)
      - per-field: {"value": ..., "source": ..., "all_sources": {src: val}}
    """
    print("=" * 60)
    print("  SOURCE PRIORITY MERGE")
    print("=" * 60)

    with open(CANONICAL_PATH) as f:
        canonical = json.load(f)
    print(f"  Canonical players: {len(canonical)}")

    tm_lookup = load_transfermarkt_lookup()
    bios = load_static_bios()
    squads = load_squads_lookup()
    trajectories = build_career_trajectories()

    merged_players: list[dict] = []
    stats = {"total": len(canonical), "tm_matched": 0, "bios_matched": 0, "squads_matched": 0}

    for player in canonical:
        cid = player["canonical_id"]
        name = player.get("name", "")
        source_id = str(player.get("source_id", ""))
        slug = _to_slug(name)
        known_as = player.get("identity", {}).get("known_as", "")
        slug_alt = _to_slug(known_as) if known_as else ""

        tm_data = tm_lookup.get(source_id, {})
        if tm_data:
            stats["tm_matched"] += 1

        bio_data = bios.get(slug) or bios.get(slug_alt) or {}
        if bio_data:
            stats["bios_matched"] += 1

        squad_data = squads.get(slug) or squads.get(slug_alt) or {}
        if squad_data:
            stats["squads_matched"] += 1

        gpt_data = _extract_gpt_fields(player)

        tm_league_id = tm_data.get("current_league_id")
        tm_league = COMPETITION_ID_TO_LEAGUE.get(tm_league_id, "") if tm_league_id else None

        tm_career = trajectories.get(source_id)
        tm_career_text = json.dumps(tm_career, ensure_ascii=False) if tm_career else None

        source_map: dict[str, dict[str, dict]] = {}
        for field in CRITICAL_FIELDS:
            sources: dict[str, any] = {}

            # TM values
            if field == "current_league":
                if tm_league:
                    sources["transfermarkt"] = tm_league
            elif field == "career_trajectory":
                if tm_career_text:
                    sources["transfermarkt"] = tm_career_text
            elif field == "international_caps":
                pass
            elif field == "international_goals":
                pass
            elif field == "jersey_number":
                pass
            elif field == "captain":
                pass
            elif field == "major_trophies":
                pass
            else:
                tm_val = _clean(tm_data.get(field))
                if tm_val is not None:
                    sources["transfermarkt"] = tm_val

            # Static bios values
            bio_field_map = {
                "date_of_birth": "birthDate",
                "height_cm": "height",
                "market_value_eur": "marketValue",
                "international_caps": "intlCaps",
                "international_goals": "intlGoals",
                "major_trophies": "achievements",
            }
            if field in bio_field_map:
                raw = bio_data.get(bio_field_map[field])
                if raw is not None:
                    if field == "height_cm":
                        raw = _parse_height(raw)
                    elif field == "market_value_eur":
                        raw = _parse_market_value(raw)
                    if raw is not None:
                        sources["static_bios"] = raw

            # Static squads values
            if field in ("position", "jersey_number", "captain", "current_club"):
                sq_val = _clean(squad_data.get(field))
                if sq_val is not None:
                    sources["static_squads"] = sq_val

            # GPT enrichment values
            gpt_val = _clean(gpt_data.get(field))
            if gpt_val is not None:
                sources["gpt_enrichment"] = gpt_val

            source_map[field] = sources

        # Determine winning value per field using priority order
        priority_order = ["transfermarkt", "static_bios", "static_squads", "gpt_enrichment"]
        resolved: dict[str, dict] = {}
        for field in CRITICAL_FIELDS:
            sources = source_map[field]
            winner_source = None
            winner_value = None
            for src in priority_order:
                if src in sources and sources[src] is not None:
                    winner_source = src
                    winner_value = sources[src]
                    break
            resolved[field] = {
                "value": winner_value,
                "source": winner_source,
                "all_sources": sources,
            }

        merged_players.append({
            "canonical_id": cid,
            "source_id": source_id,
            "name": name,
            "wc_team_code": player.get("wc_team_code", ""),
            "slug": slug,
            "fields": resolved,
        })

    print(f"\n  Match rates:")
    print(f"    Transfermarkt:  {stats['tm_matched']}/{stats['total']}")
    print(f"    Static bios:    {stats['bios_matched']}/{stats['total']}")
    print(f"    Static squads:  {stats['squads_matched']}/{stats['total']}")

    with open(MERGED_OUTPUT, "w") as f:
        json.dump(merged_players, f, indent=2, ensure_ascii=False)
    print(f"\n  Wrote merged data to {MERGED_OUTPUT}")

    return merged_players


if __name__ == "__main__":
    result = run_merge()
    print(f"\n  Sample (first 3 players):")
    for p in result[:3]:
        print(f"\n  {p['name']} ({p['wc_team_code']}):")
        for field, info in p["fields"].items():
            if info["value"] is not None:
                src_count = len(info["all_sources"])
                val = info["value"]
                if isinstance(val, str) and len(val) > 60:
                    val = val[:60] + "..."
                print(f"    {field:25s} = {val!s:40s} [{info['source']}] ({src_count} sources)")
