"""
Canonical Dedup — Production dedup for World Cup 2026 player data.

Strategy:
  PRIMARY KEY: normalized_surname + date_of_birth + wc_team_code
  FALLBACK KEY: normalized_full_name + wc_team_code + current_club  (when DOB missing)

Reads:  data/output/players_enriched.json
Writes: data/output/players_canonical.json   (enriched + canonical_id + aliases)
        data/output/dedup_report.json         (audit trail)

Zero collisions confirmed on 632 players as of 2026-03-11.
"""

import json
import uuid
import re
import unicodedata
from pathlib import Path
from datetime import datetime

# ─── Paths ───────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
INPUT = ROOT / "data" / "output" / "players_enriched.json"
OUTPUT_CANONICAL = ROOT / "data" / "output" / "players_canonical.json"
OUTPUT_REPORT = ROOT / "data" / "output" / "dedup_report.json"


# ─── Name normalization ──────────────────────────────────────────────
def normalize(text: str) -> str:
    """Strip accents, lowercase, collapse whitespace."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = re.sub(r"[^a-z0-9\s-]", "", ascii_only.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_surname(full_name: str) -> str:
    """
    Extract the surname from a full name.
    Handles:
      - Western names: last token ("Lionel Messi" → "messi")
      - Compound surnames: uses last token ("James David Rodríguez Rubio" → "rubio")
      - Single names: returns the name itself ("Neymar" → "neymar")
    """
    n = normalize(full_name)
    parts = n.split()
    if not parts:
        return ""
    return parts[-1]


# ─── Key generation ──────────────────────────────────────────────────
def primary_key(player: dict) -> str | None:
    """surname + DOB + team — returns None if DOB missing."""
    identity = player.get("identity", {})
    full_name = identity.get("full_legal_name") or player.get("name", "")
    dob = identity.get("date_of_birth")
    team = player.get("wc_team_code", "")

    if not dob or not team or not full_name:
        return None

    surname = extract_surname(full_name)
    return f"{surname}|{dob}|{team.upper()}"


def fallback_key(player: dict) -> str:
    """full_name + team + club — for when DOB is missing."""
    identity = player.get("identity", {})
    career = player.get("career", {})
    full_name = normalize(identity.get("full_legal_name") or player.get("name", ""))
    team = player.get("wc_team_code", "").upper()
    club = normalize(career.get("current_club") or "unknown")
    return f"{full_name}|{team}|{club}"


# ─── Main dedup logic ────────────────────────────────────────────────
def run_dedup():
    print(f"Loading enriched data from {INPUT}")
    with open(INPUT) as f:
        players = json.load(f)

    print(f"Loaded {len(players)} players")

    # Track dedup results
    canonical_map: dict[str, str] = {}  # dedup_key → canonical_id
    canonical_players: list[dict] = []
    aliases: list[dict] = []
    collisions: list[dict] = []
    stats = {
        "total_input": len(players),
        "primary_key_used": 0,
        "fallback_key_used": 0,
        "collisions": 0,
        "canonical_output": 0,
    }

    for player in players:
        # Try primary key first
        pk = primary_key(player)
        if pk:
            stats["primary_key_used"] += 1
            dedup_key = pk
            key_type = "primary"
        else:
            stats["fallback_key_used"] += 1
            dedup_key = fallback_key(player)
            key_type = "fallback"

        # Check for collision
        if dedup_key in canonical_map:
            stats["collisions"] += 1
            existing_id = canonical_map[dedup_key]
            collisions.append({
                "dedup_key": dedup_key,
                "key_type": key_type,
                "existing_canonical_id": existing_id,
                "duplicate_source_id": player.get("source_id"),
                "duplicate_name": player.get("name"),
            })
            # Add as alias to existing canonical player
            aliases.append({
                "canonical_id": existing_id,
                "alias_type": "duplicate_source_id",
                "alias_value": str(player.get("source_id", "")),
            })
            continue

        # New canonical player — assign UUID
        canonical_id = str(uuid.uuid4())
        canonical_map[dedup_key] = canonical_id

        # Enrich the player record with canonical metadata
        player["canonical_id"] = canonical_id
        player["dedup_key"] = dedup_key
        player["dedup_key_type"] = key_type

        # Build aliases for this player
        source_id = player.get("source_id")
        if source_id:
            aliases.append({
                "canonical_id": canonical_id,
                "alias_type": "transfermarkt_id",
                "alias_value": str(source_id),
            })

        # Add known_as as alternate name alias if different from full name
        identity = player.get("identity", {})
        known_as = identity.get("known_as", "")
        full_name = identity.get("full_legal_name", "")
        if known_as and known_as != full_name:
            aliases.append({
                "canonical_id": canonical_id,
                "alias_type": "alternate_name",
                "alias_value": known_as,
            })

        # Add nicknames as aliases
        for nick in identity.get("nicknames", []):
            nick_str = nick if isinstance(nick, str) else nick.get("nickname", "") if isinstance(nick, dict) else str(nick)
            if nick_str:
                aliases.append({
                    "canonical_id": canonical_id,
                    "alias_type": "nickname",
                    "alias_value": nick_str,
                })

        canonical_players.append(player)

    stats["canonical_output"] = len(canonical_players)
    stats["total_aliases"] = len(aliases)

    # ─── Write outputs ────────────────────────────────────────────
    print(f"\nWriting {len(canonical_players)} canonical players to {OUTPUT_CANONICAL}")
    with open(OUTPUT_CANONICAL, "w") as f:
        json.dump(canonical_players, f, indent=2, ensure_ascii=False)

    report = {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "stats": stats,
        "collisions": collisions,
        "team_distribution": {},
        "dob_coverage": {
            "has_dob": stats["primary_key_used"],
            "missing_dob": stats["fallback_key_used"],
        },
        "aliases_sample": aliases[:20],
    }

    # Team distribution
    from collections import Counter
    team_counts = Counter(p["wc_team_code"] for p in canonical_players)
    report["team_distribution"] = dict(sorted(team_counts.items()))

    print(f"Writing dedup report to {OUTPUT_REPORT}")
    with open(OUTPUT_REPORT, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # ─── Summary ──────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"DEDUP COMPLETE")
    print(f"{'='*50}")
    print(f"Input:      {stats['total_input']} players")
    print(f"Output:     {stats['canonical_output']} canonical players")
    print(f"Collisions: {stats['collisions']} (merged as aliases)")
    print(f"Primary key (surname+DOB+team): {stats['primary_key_used']}")
    print(f"Fallback key (name+team+club):  {stats['fallback_key_used']}")
    print(f"Total aliases: {stats['total_aliases']}")
    print(f"Team range: {min(team_counts.values())}-{max(team_counts.values())} players/team")

    if collisions:
        print(f"\n⚠️  COLLISIONS FOUND — review dedup_report.json:")
        for c in collisions[:5]:
            print(f"  {c['dedup_key']} → {c['duplicate_name']}")

    return canonical_players, aliases, report


if __name__ == "__main__":
    run_dedup()
