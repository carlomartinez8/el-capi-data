#!/usr/bin/env python3
"""
generate_players_ts.py — Warehouse → src/data/players.ts bridge
================================================================

Queries the Supabase warehouse (players + player_career + player_tournament)
and regenerates the static TypeScript file that powers the La Copa Mundo frontend.

This is the critical bridge between el-capi-data (warehouse) and la-copa-mundo (app).

Usage:
    python -m pipeline.generators.generate_players_ts [--dry-run] [--output PATH]

    --dry-run    Print stats but don't write the file
    --output     Override output path (default: ../la-copa-mundo/src/data/players.ts)

Requires:
    SUPABASE_URL and SUPABASE_SERVICE_KEY env vars (from .env or pipeline config)
"""

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# Add parent dirs to path for pipeline config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from supabase import create_client
except ImportError:
    print("ERROR: supabase-py not installed. Run: pip install supabase --break-system-packages")
    sys.exit(1)


# ── Configuration ────────────────────────────────────────────────────────

# Position mapping: warehouse full names → TypeScript short codes
POSITION_MAP = {
    "Goalkeeper": "GK",
    "Defender": "DEF",
    "Midfielder": "MID",
    "Forward": "FWD",
    "Missing": "MID",  # Fallback for 189 players with missing position
}

# WC 2026 kickoff date for age calculation
WC_DATE = date(2026, 6, 11)

# Playoff placeholder codes
PLAYOFF_CODES = ["PLA", "PLB", "PLC", "PLD", "PL1", "PL2"]

# Group ordering for readable output
GROUP_ORDER = [
    # Group A
    "MEX", "RSA", "KOR",
    # Group B
    "CAN", "SUI", "QAT",
    # Group C
    "BRA", "JPN", "CIV",
    # Group D
    "ITA", "COL", "ECU",
    # Group E
    "ARG", "PER", "EGY",
    # Group F
    "FRA", "AUS", "IDN",
    # Group G
    "GER", "URU", "NGA",
    # Group H
    "POR", "IRN", "CRC",
    # Group I
    "ESP", "PAR", "NZL",
    # Group J
    "ENG", "DEN", "CHN",
    # Group K
    "USA", "CHI", "SAU",
    # Group L
    "NED", "SEN", "GHA",
    # Playoff placeholders
    "PAN",  # Some confirmed teams may not have groups yet
]

# Group labels for comments
GROUP_LABELS = {
    "MEX": "A", "RSA": "A", "KOR": "A",
    "CAN": "B", "SUI": "B", "QAT": "B",
    "BRA": "C", "JPN": "C", "CIV": "C",
    "ITA": "D", "COL": "D", "ECU": "D",
    "ARG": "E", "PER": "E", "EGY": "E",
    "FRA": "F", "AUS": "F", "IDN": "F",
    "GER": "G", "URU": "G", "NGA": "G",
    "POR": "H", "IRN": "H", "CRC": "H",
    "ESP": "I", "PAR": "I", "NZL": "I",
    "ENG": "J", "DEN": "J", "CHN": "J",
    "USA": "K", "CHI": "K", "SAU": "K",
    "NED": "L", "SEN": "L", "GHA": "L",
}


# ── Helpers ──────────────────────────────────────────────────────────────

def compute_age(dob_str: str | None) -> int:
    """Compute age as of WC 2026 kickoff."""
    if not dob_str:
        return 0
    try:
        dob = datetime.strptime(dob_str[:10], "%Y-%m-%d").date()
        age = WC_DATE.year - dob.year
        if (WC_DATE.month, WC_DATE.day) < (dob.month, dob.day):
            age -= 1
        return age
    except (ValueError, TypeError):
        return 0


def escape_ts_string(s: str) -> str:
    """Escape a string for TypeScript single-quoted or double-quoted literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def map_position(pos: str | None) -> str:
    """Map warehouse position name to TypeScript code."""
    if not pos:
        return "MID"
    return POSITION_MAP.get(pos, "MID")


# ── Main Generator ───────────────────────────────────────────────────────

def fetch_squad_data(supabase) -> dict[str, list[dict]]:
    """
    Fetch all WC 2026 primary squad players from warehouse.
    Returns dict keyed by team code → list of player dicts.
    """
    # Query player_tournament (in_squad = TRUE) with player + career joins
    # Supabase JS uses nested selects; Python client uses select with !inner
    # We'll do it in two queries for reliability

    print("  Fetching player_tournament (in_squad=TRUE)...")
    # Supabase default limit is 1000; paginate to get all in_squad rows
    tournament_rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        chunk = supabase.table("player_tournament") \
            .select("player_id, wc_team_code, jersey_number, captain") \
            .eq("in_squad", True) \
            .range(offset, offset + page_size - 1) \
            .execute()
        data = chunk.data or []
        tournament_rows.extend(data)
        if len(data) < page_size:
            break
        offset += page_size
    print(f"  → {len(tournament_rows)} tournament entries")

    if not tournament_rows:
        print("ERROR: No in_squad=TRUE players found in player_tournament!")
        return {}

    # Collect all player IDs
    player_ids = list(set(r["player_id"] for r in tournament_rows))
    print(f"  → {len(player_ids)} unique player IDs")

    # Fetch player identity data in batches (Supabase .in() has limits)
    print("  Fetching player identity data...")
    players_map: dict[str, dict] = {}
    batch_size = 200
    for i in range(0, len(player_ids), batch_size):
        batch = player_ids[i:i + batch_size]
        resp = supabase.table("players") \
            .select("id, known_as, full_legal_name, date_of_birth, photo_url") \
            .in_("id", batch) \
            .execute()
        for p in (resp.data or []):
            players_map[p["id"]] = p

    print(f"  → {len(players_map)} player records fetched")

    # Fetch career data
    print("  Fetching player career data...")
    career_map: dict[str, dict] = {}
    for i in range(0, len(player_ids), batch_size):
        batch = player_ids[i:i + batch_size]
        resp = supabase.table("player_career") \
            .select("player_id, current_club, position_primary") \
            .in_("player_id", batch) \
            .execute()
        for c in (resp.data or []):
            career_map[c["player_id"]] = c

    print(f"  → {len(career_map)} career records fetched")

    # Assemble squads by team code
    squads: dict[str, list[dict]] = {}
    skipped = 0

    for t in tournament_rows:
        pid = t["player_id"]
        team = t["wc_team_code"]

        player = players_map.get(pid)
        career = career_map.get(pid)

        if not player:
            skipped += 1
            continue

        name = player.get("known_as") or player.get("full_legal_name") or "Unknown"
        club = (career.get("current_club") if career else None) or "Unknown"
        position = map_position(career.get("position_primary") if career else None)
        age = compute_age(player.get("date_of_birth"))
        jersey = t.get("jersey_number") or 0
        captain = t.get("captain") or False

        entry = {
            "name": name,
            "number": jersey,
            "position": position,
            "club": club,
            "age": age,
            "captain": captain,
            "warehouseId": pid,
        }

        if team not in squads:
            squads[team] = []
        squads[team].append(entry)

    if skipped:
        print(f"  ⚠ {skipped} tournament entries had no matching player record")

    # Sort each squad: captain first, then by jersey number
    for team in squads:
        squads[team].sort(key=lambda p: (not p["captain"], p["number"]))

    return squads


def generate_typescript(squads: dict[str, list[dict]]) -> str:
    """Generate the full players.ts TypeScript source."""

    lines: list[str] = []

    # Header
    lines.append('/**')
    lines.append(' * World Cup 2026 squads — AUTO-GENERATED from warehouse data.')
    lines.append(f' * Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append(f' * Source: Supabase warehouse (players + player_career + player_tournament)')
    lines.append(' * Teams: ' + str(len(squads)))
    lines.append(' * Players: ' + str(sum(len(s) for s in squads.values())))
    lines.append(' *')
    lines.append(' * DO NOT EDIT MANUALLY — regenerate with:')
    lines.append(' *   cd el-capi-data && python -m pipeline.generators.generate_players_ts')
    lines.append(' */')
    lines.append('')

    # Interfaces
    lines.append('export interface Player {')
    lines.append('  name: string;')
    lines.append('  number: number;')
    lines.append('  position: "GK" | "DEF" | "MID" | "FWD";')
    lines.append('  club: string;')
    lines.append('  age: number; // age as of June 2026')
    lines.append('  captain?: boolean;')
    lines.append('  warehouseId?: string; // UUID linking to warehouse players table')
    lines.append('}')
    lines.append('')

    lines.append('export interface PlayerBio {')
    lines.append('  height?: string;       // e.g. "1.81 m"')
    lines.append('  foot?: "Left" | "Right" | "Both";')
    lines.append('  intlCaps?: number;')
    lines.append('  intlGoals?: number;')
    lines.append('  marketValue?: string;  // e.g. "€80M"')
    lines.append('  birthDate?: string;    // YYYY-MM-DD')
    lines.append('  birthPlace?: string;')
    lines.append('  bio_en?: string;')
    lines.append('  bio_es?: string;')
    lines.append('  previousClubs?: string[];')
    lines.append('  achievements?: string[];')
    lines.append('}')
    lines.append('')

    lines.append('export interface TeamSquad {')
    lines.append('  code: string;')
    lines.append('  players: Player[];')
    lines.append('}')
    lines.append('')

    # Utility functions (same as original)
    lines.append('/** Generate a URL-safe slug from a player name */')
    lines.append('export function playerSlug(name: string): string {')
    lines.append('  return name')
    lines.append('    .normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")')
    lines.append('    .toLowerCase()')
    lines.append('    .replace(/[^a-z0-9]+/g, "-")')
    lines.append('    .replace(/(^-|-$)/g, "");')
    lines.append('}')
    lines.append('')

    lines.append('/** Find a player by slug across all teams. Returns [player, teamCode] or null */')
    lines.append('export function findPlayerBySlug(slug: string): [Player, string] | null {')
    lines.append('  for (const [code, players] of Object.entries(SQUADS)) {')
    lines.append('    for (const p of players) {')
    lines.append('      if (playerSlug(p.name) === slug) return [p, code];')
    lines.append('    }')
    lines.append('  }')
    lines.append('  return null;')
    lines.append('}')
    lines.append('')

    # SQUADS object
    lines.append('/** All teams keyed by FIFA code — generated from warehouse */')
    lines.append('export const SQUADS: Record<string, Player[]> = {')

    # Determine team order: known groups first, then remaining teams
    ordered_teams: list[str] = []
    seen = set()

    # Group by group letter
    groups: dict[str, list[str]] = {}
    for code, group in GROUP_LABELS.items():
        if code in squads:
            groups.setdefault(group, []).append(code)

    for group_letter in sorted(groups.keys()):
        for code in groups[group_letter]:
            if code not in seen:
                ordered_teams.append(code)
                seen.add(code)

    # Add any remaining teams not in GROUP_LABELS
    for code in sorted(squads.keys()):
        if code not in seen:
            ordered_teams.append(code)
            seen.add(code)

    current_group = None
    for code in ordered_teams:
        squad = squads[code]
        group = GROUP_LABELS.get(code)

        # Group separator comment
        if group and group != current_group:
            current_group = group
            lines.append(f'  // ── GROUP {group} {"─" * 50}')

        lines.append(f'  {code}: [')
        for p in squad:
            parts = []
            parts.append(f'name: "{escape_ts_string(p["name"])}"')
            parts.append(f'number: {p["number"]}')
            parts.append(f'position: "{p["position"]}"')
            parts.append(f'club: "{escape_ts_string(p["club"])}"')
            parts.append(f'age: {p["age"]}')
            if p.get("captain"):
                parts.append("captain: true")
            parts.append(f'warehouseId: "{p["warehouseId"]}"')
            lines.append(f'    {{ {", ".join(parts)} }},')
        lines.append('  ],')

    # Playoff placeholders
    lines.append('')
    lines.append('  // Playoff placeholder teams — will be updated when playoffs are resolved')
    for code in PLAYOFF_CODES:
        if code not in seen:
            lines.append(f'  {code}: [],')

    lines.append('};')
    lines.append('')

    # Helper functions
    lines.append('/** Helper: get squad for a team by FIFA code */')
    lines.append('export function getSquad(code: string): Player[] {')
    lines.append('  return SQUADS[code] ?? [];')
    lines.append('}')
    lines.append('')

    lines.append('/** Helper: get captain for a team */')
    lines.append('export function getCaptain(code: string): Player | undefined {')
    lines.append('  return SQUADS[code]?.find(p => p.captain);')
    lines.append('}')
    lines.append('')

    lines.append('/** Helper: group players by position */')
    lines.append('export function groupByPosition(players: Player[]): Record<string, Player[]> {')
    lines.append('  const groups: Record<string, Player[]> = { GK: [], DEF: [], MID: [], FWD: [] };')
    lines.append('  for (const p of players) {')
    lines.append('    groups[p.position]?.push(p);')
    lines.append('  }')
    lines.append('  return groups;')
    lines.append('}')
    lines.append('')

    return "\n".join(lines)


def print_stats(squads: dict[str, list[dict]]):
    """Print summary stats."""
    total = sum(len(s) for s in squads.values())
    teams_with_data = len([t for t in squads.values() if len(t) > 0])

    print(f"\n{'='*60}")
    print(f"  GENERATION SUMMARY")
    print(f"{'='*60}")
    print(f"  Teams:    {teams_with_data}")
    print(f"  Players:  {total}")
    print(f"  Avg/team: {total / max(teams_with_data, 1):.1f}")
    print()

    # Position breakdown
    positions = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}
    captains = 0
    with_warehouse_id = 0
    zero_age = 0
    unknown_club = 0

    for squad in squads.values():
        for p in squad:
            positions[p["position"]] = positions.get(p["position"], 0) + 1
            if p.get("captain"):
                captains += 1
            if p.get("warehouseId"):
                with_warehouse_id += 1
            if p["age"] == 0:
                zero_age += 1
            if p["club"] == "Unknown":
                unknown_club += 1

    print(f"  Positions: GK={positions['GK']} DEF={positions['DEF']} MID={positions['MID']} FWD={positions['FWD']}")
    print(f"  Captains:  {captains}")
    print(f"  With UUID: {with_warehouse_id}/{total}")

    if zero_age:
        print(f"  ⚠ Missing DOB (age=0): {zero_age}")
    if unknown_club:
        print(f"  ⚠ Unknown club: {unknown_club}")

    # Teams with fewer than 20 players
    small_teams = [(code, len(s)) for code, s in squads.items() if len(s) < 20]
    if small_teams:
        print(f"\n  ⚠ Teams with < 20 players:")
        for code, count in sorted(small_teams, key=lambda x: x[1]):
            print(f"    {code}: {count}")

    print(f"{'='*60}\n")


# ── CLI Entry Point ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate players.ts from warehouse")
    parser.add_argument("--dry-run", action="store_true", help="Print stats only, don't write file")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()

    # Resolve output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Default: sibling repo's data directory
        repo_root = Path(__file__).resolve().parent.parent.parent
        output_path = repo_root.parent / "la-copa-mundo" / "src" / "data" / "players.ts"

    # Load Supabase credentials
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        # Try loading from .env file
        env_paths = [
            Path(__file__).resolve().parent.parent.parent / ".env",
            Path(__file__).resolve().parent.parent.parent.parent / "la-copa-mundo" / ".env.local",
        ]
        for env_path in env_paths:
            if env_path.exists():
                print(f"  Loading env from {env_path}")
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k in ("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL") and not url:
                                url = v
                            elif k in ("SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY") and not key:
                                key = v

    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required.")
        print("  Set env vars or create .env file in el-capi-data/")
        sys.exit(1)

    print(f"Connecting to Supabase...")
    supabase = create_client(url, key)

    print(f"Fetching WC 2026 squad data from warehouse...")
    squads = fetch_squad_data(supabase)

    if not squads:
        print("ERROR: No squad data retrieved!")
        sys.exit(1)

    print_stats(squads)

    if args.dry_run:
        print("DRY RUN — no file written.")
        # Print first team as sample
        first_team = next(iter(squads.keys()))
        print(f"\nSample ({first_team}):")
        for p in squads[first_team][:3]:
            print(f"  {p['name']} | #{p['number']} | {p['position']} | {p['club']} | age {p['age']}")
        return

    # Generate TypeScript
    ts_source = generate_typescript(squads)

    # Write file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ts_source)

    print(f"✅ Written to {output_path}")
    print(f"   {len(ts_source)} chars, {ts_source.count(chr(10))} lines")


if __name__ == "__main__":
    main()
