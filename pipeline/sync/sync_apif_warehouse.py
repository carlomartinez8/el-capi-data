#!/usr/bin/env python3
"""
sync_apif_warehouse.py — API-Football → Warehouse Direct Sync
==============================================================

Queries API-Football for current player data and updates the warehouse
tables (player_career) directly. This is the data freshness layer that
keeps club assignments, photos, and biographical data current.

Modes:
    team <CODE>     — Sync all players for a WC 2026 team (e.g., COL, ARG)
    player <UUID>   — Sync a single player by warehouse UUID
    all             — Sync all WC 2026 squad players (~1,200 players)
    stale           — Sync only players with low/medium confidence

Usage:
    python -m pipeline.sync.sync_apif_warehouse team COL
    python -m pipeline.sync.sync_apif_warehouse player 47184c5c-44dd-4743-b132-c0faadb10331
    python -m pipeline.sync.sync_apif_warehouse all
    python -m pipeline.sync.sync_apif_warehouse stale

Requires:
    API_FOOTBALL_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY env vars

API Budget:
    ~1 credit per player lookup. Pro plan = 7,500/day.
    Team sync (~28 players) = ~28 credits.
    Full sync (~1,200 players) = ~1,200 credits.
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from supabase import create_client
except ImportError:
    print("ERROR: supabase-py not installed. Run: pip install supabase --break-system-packages")
    sys.exit(1)


# ── Configuration ────────────────────────────────────────────────────────

API_BASE = "https://v3.football.api-sports.io"
THROTTLE_SECONDS = 1.5
THROTTLE_BATCH = 3.0  # extra pause every 25 requests
BATCH_PAUSE_EVERY = 25

# API-Football national team IDs (from /teams?country=... or dashboard)
# Colombia = 8 (national team); 1132 is club "Chico"
NATIONAL_TEAM_APIF_IDS = {
    "COL": 8,      # Colombia
    "ARG": 2,      # Argentina
    "BRA": 5,      # Brazil
    "USA": 1,      # United States
    "MEX": 14,     # Mexico
    "FRA": 9,      # France
    "ESP": 6,      # Spain
    "GER": 4,      # Germany
    "ENG": 10,     # England
    "POR": 38,     # Portugal
    "BEL": 3,      # Belgium
    "NED": 15,     # Netherlands
    "URU": 7,      # Uruguay
    "ECU": 1131,   # Ecuador
    "PER": 1133,   # Peru
    "CHI": 1134,   # Chile
    "JPN": 116,    # Japan
    "KOR": 117,    # South Korea
    "EGY": 1135,   # Egypt
    "MAR": 66,     # Morocco
    "SEN": 1136,   # Senegal
    "CIV": 1137,   # Ivory Coast
    "GHA": 1138,   # Ghana
    "NGA": 1140,   # Nigeria
    "AUS": 1,      # Australia (may need verification)
    "CAN": 161,    # Canada
    "CRC": 1139,   # Costa Rica
    "PAN": 1141,   # Panama
    "JAM": 1142,   # Jamaica
    "HAI": 1143,   # Haiti
    "PAR": 1144,   # Paraguay
    "BOL": 1145,   # Bolivia
    "VEN": 1146,   # Venezuela
}


# ── API-Football Client ─────────────────────────────────────────────────

class ApiFootball:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"x-apisports-key": api_key}
        self.calls = 0

    def get(self, endpoint: str, params: dict) -> dict:
        resp = requests.get(
            f"{API_BASE}/{endpoint}",
            headers=self.headers,
            params=params,
            timeout=15
        )
        resp.raise_for_status()
        self.calls += 1
        data = resp.json()
        errors = data.get("errors")
        if errors and isinstance(errors, dict) and len(errors) > 0:
            print(f"    API warning: {errors}")
        return data

    def search_player(self, name: str, team_id: int | None = None) -> list[dict]:
        """Search for a player by name. Returns list of player profiles."""
        params = {"search": name}
        if team_id:
            params["team"] = team_id
        data = self.get("players", params)
        return data.get("response", [])

    def get_player_by_id(self, apif_id: int, season: int = 2025) -> dict | None:
        """Get full player profile by API-Football numeric ID."""
        data = self.get("players", {"id": apif_id, "season": season})
        results = data.get("response", [])
        return results[0] if results else None

    def get_team_squad(self, team_id: int) -> list[dict]:
        """Get current squad for a team (e.g. national team). Returns list of player entries with id, name, etc."""
        data = self.get("players/squads", {"team": team_id})
        # Response shape: {"response": [{"team": {...}, "players": [{id, name, ...}, ...]}]}
        raw = data.get("response", [])
        if not raw:
            return []
        first = raw[0]
        if isinstance(first, dict) and "players" in first:
            return first["players"]
        if isinstance(first, list):
            return first
        return raw

    def search_player_by_name(self, name: str, season: int = 2025, team_id: int | None = None) -> list[dict]:
        """Search players by name. API requires team or league with search; pass team_id for national team scope."""
        params = {"search": name, "season": season}
        if team_id:
            params["team"] = team_id
        data = self.get("players", params)
        return data.get("response", [])

    def throttle(self):
        """Rate limit protection."""
        time.sleep(THROTTLE_SECONDS)
        if self.calls % BATCH_PAUSE_EVERY == 0:
            time.sleep(THROTTLE_BATCH)


# ── Name Matching ────────────────────────────────────────────────────────

def normalize(name: str) -> str:
    """Strip diacritics and lowercase."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def sanitize_search_name(name: str) -> str:
    """API requires search: only alphanumeric and spaces, min 4 chars."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Keep only letters, digits, spaces
    clean = "".join(c for c in ascii_name if c.isalnum() or c.isspace()).strip()
    if len(clean) >= 4:
        return clean
    # Use full name or pad: API min 4 chars
    return clean if len(clean) >= 4 else (clean + " " * (4 - len(clean))).strip() or "abcd"


def names_match(warehouse_name: str, apif_name: str) -> bool:
    """Check if warehouse and APIF names refer to the same player."""
    wn = normalize(warehouse_name)
    an = normalize(apif_name)

    if wn == an:
        return True

    # Last name match
    w_last = wn.split()[-1] if wn.split() else wn
    a_last = an.split()[-1] if an.split() else an
    if w_last == a_last and len(w_last) > 2:
        return True

    # Containment
    if wn in an or an in wn:
        return True

    return False


# ── Warehouse Operations ────────────────────────────────────────────────

def fetch_wc_players(supabase, team_code: str | None = None, confidence: str | None = None) -> list[dict]:
    """
    Fetch WC 2026 players from warehouse for syncing.
    Returns list of dicts with player_id, name, current_club, wc_team_code, etc.
    """
    # Get player_tournament entries
    query = supabase.table("player_tournament") \
        .select("player_id, wc_team_code") \
        .eq("in_squad", True)

    if team_code:
        query = query.eq("wc_team_code", team_code)

    # Paginate
    rows = []
    page_size = 1000
    offset = 0
    while True:
        chunk = query.range(offset, offset + page_size - 1).execute()
        data = chunk.data or []
        rows.extend(data)
        if len(data) < page_size:
            break
        offset += page_size

    if not rows:
        return []

    # Fetch player details
    player_ids = list(set(r["player_id"] for r in rows))
    team_map = {r["player_id"]: r["wc_team_code"] for r in rows}

    players = []
    batch_size = 200
    for i in range(0, len(player_ids), batch_size):
        batch = player_ids[i:i + batch_size]

        # Get player identity
        p_resp = supabase.table("players") \
            .select("id, known_as, full_legal_name, data_confidence") \
            .in_("id", batch) \
            .execute()

        # Get career data
        c_resp = supabase.table("player_career") \
            .select("player_id, current_club, current_league, position_primary") \
            .in_("player_id", batch) \
            .execute()

        # Get aliases (for APIF ID mapping — warehouse uses alias_type/alias_value)
        a_resp = supabase.table("player_aliases") \
            .select("player_id, alias_type, alias_value") \
            .in_("player_id", batch) \
            .eq("alias_type", "apif_id") \
            .execute()

        p_map = {p["id"]: p for p in (p_resp.data or [])}
        c_map = {c["player_id"]: c for c in (c_resp.data or [])}
        a_map = {a["player_id"]: a["alias_value"] for a in (a_resp.data or [])}

        for pid in batch:
            p = p_map.get(pid)
            c = c_map.get(pid)
            if not p:
                continue

            if confidence and p.get("data_confidence") != confidence:
                continue

            players.append({
                "player_id": pid,
                "name": p.get("known_as") or p.get("full_legal_name") or "Unknown",
                "full_name": p.get("full_legal_name") or "",
                "current_club": c.get("current_club") if c else None,
                "current_league": c.get("current_league") if c else None,
                "position": c.get("position_primary") if c else None,
                "confidence": p.get("data_confidence"),
                "wc_team_code": team_map.get(pid),
                "apif_id": a_map.get(pid),
            })

    return players


def update_player_career(supabase, player_id: str, updates: dict) -> bool:
    """Update player_career record in warehouse."""
    try:
        supabase.table("player_career") \
            .update(updates) \
            .eq("player_id", player_id) \
            .execute()
        return True
    except Exception as e:
        print(f"    DB error for {player_id}: {e}")
        return False


def update_player_identity(supabase, player_id: str, updates: dict) -> bool:
    """Update players record in warehouse."""
    try:
        supabase.table("players") \
            .update(updates) \
            .eq("id", player_id) \
            .execute()
        return True
    except Exception as e:
        print(f"    DB error for {player_id}: {e}")
        return False


def save_alias(supabase, player_id: str, apif_id: int):
    """Save API-Football ID as a player alias for future lookups (alias_type=apif_id)."""
    try:
        supabase.table("player_aliases").upsert({
            "player_id": player_id,
            "alias_type": "apif_id",
            "alias_value": str(apif_id),
        }, on_conflict="alias_type,alias_value").execute()
    except Exception:
        pass  # OK if alias already exists with different constraint


# ── Sync Logic ───────────────────────────────────────────────────────────

def sync_player(api: ApiFootball, supabase, player: dict) -> dict:
    """
    Sync a single player from API-Football to warehouse.
    Returns dict with sync result.
    """
    name = player["name"]
    full_name = player["full_name"]
    pid = player["player_id"]

    result = {
        "player_id": pid,
        "name": name,
        "status": "skipped",
        "changes": [],
    }

    # Strategy 1: Use known APIF ID if we have one
    apif_data = None
    if player.get("apif_id"):
        try:
            apif_id = int(player["apif_id"])
            apif_data = api.get_player_by_id(apif_id)
            api.throttle()
        except (ValueError, Exception):
            pass

    # Strategy 1.5: Match from pre-fetched team squad (avoids search API validation issues)
    if not apif_data and player.get("squad_list"):
        for entry in player["squad_list"]:
            p_entry = entry.get("player", entry)
            apif_id_val = p_entry.get("id")
            apif_name = p_entry.get("name") or (p_entry.get("firstname", "") + " " + p_entry.get("lastname", "")).strip()
            if not apif_id_val or not apif_name:
                continue
            # Squad names are often abbreviated ("J. Rodríguez"); match full name or last name
            if names_match(name, apif_name) or (full_name and names_match(full_name, apif_name)):
                matched = True
            else:
                w_last = name.split()[-1] if name else ""
                a_last = apif_name.split()[-1] if apif_name else ""
                matched = w_last and a_last and names_match(w_last, a_last)
            if matched:
                try:
                    apif_data = api.get_player_by_id(int(apif_id_val))
                    api.throttle()
                except (ValueError, Exception):
                    continue
                if apif_data:
                    break

    # Strategy 2: Search by name (API requires team or league with search for team-scoped sync)
    apif_team_id = player.get("apif_team_id")
    if not apif_data:
        # Prefer last name (often more unique); sanitize for API: alphanumeric + spaces, min 4 chars
        search_name = sanitize_search_name(name if len(name.split()) <= 3 else name.split()[-1])
        if len(search_name) < 4 and full_name:
            search_name = sanitize_search_name(full_name.split()[-1] if full_name else name)
        try:
            results = api.search_player_by_name(search_name, team_id=apif_team_id)
            api.throttle()
        except Exception as e:
            result["status"] = "api_error"
            result["error"] = str(e)
            return result

        if not results and full_name and full_name != name:
            search_name2 = sanitize_search_name(full_name.split()[-1])
            try:
                results = api.search_player_by_name(search_name2, team_id=apif_team_id)
                api.throttle()
            except Exception:
                pass

        if not results:
            result["status"] = "not_found"
            return result

        # Find best match by name
        for r in results:
            p_data = r.get("player", {})
            apif_name = p_data.get("name", "")
            apif_first = p_data.get("firstname", "")
            apif_last = p_data.get("lastname", "")

            if names_match(name, apif_name) or names_match(name, f"{apif_first} {apif_last}"):
                apif_data = r
                break

        if not apif_data:
            # Try matching against full_name
            for r in results:
                p_data = r.get("player", {})
                apif_name = p_data.get("name", "")
                if names_match(full_name, apif_name):
                    apif_data = r
                    break

    if not apif_data:
        result["status"] = "no_match"
        return result

    # Extract fresh data from APIF response
    p_info = apif_data.get("player", {})
    stats_list = apif_data.get("statistics", [])

    # Get most recent statistics entry (current club)
    current_stats = stats_list[0] if stats_list else {}
    team_info = current_stats.get("team", {})
    league_info = current_stats.get("league", {})
    games_info = current_stats.get("games", {})

    apif_club = team_info.get("name")
    apif_league = league_info.get("name")
    apif_position = games_info.get("position")
    apif_photo = p_info.get("photo")
    apif_id_num = p_info.get("id")
    apif_dob = (p_info.get("birth") or {}).get("date")
    apif_nationality = p_info.get("nationality")
    apif_height = p_info.get("height")
    apif_birth_country = (p_info.get("birth") or {}).get("country")
    apif_birth_city = (p_info.get("birth") or {}).get("place")

    # Build career updates
    career_updates = {}
    identity_updates = {}

    if apif_club and apif_club != player.get("current_club"):
        career_updates["current_club"] = apif_club
        result["changes"].append(f"club: {player.get('current_club')} → {apif_club}")

    if apif_league and apif_league != player.get("current_league"):
        career_updates["current_league"] = apif_league
        result["changes"].append(f"league: {player.get('current_league')} → {apif_league}")

    if apif_photo:
        identity_updates["photo_url"] = apif_photo

    if apif_dob:
        identity_updates["date_of_birth"] = apif_dob

    if apif_nationality:
        identity_updates["nationality_primary"] = apif_nationality

    if apif_height:
        try:
            h = int(str(apif_height).replace(" cm", "").strip())
            if 100 < h < 230:
                identity_updates["height_cm"] = h
        except ValueError:
            pass

    if apif_birth_country:
        identity_updates["birth_country"] = apif_birth_country

    if apif_birth_city:
        identity_updates["birth_city"] = apif_birth_city

    # Apply updates
    if career_updates:
        career_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_player_career(supabase, pid, career_updates)

    if identity_updates:
        # players table has no updated_at; only player_career has it
        update_player_identity(supabase, pid, identity_updates)

    # Save APIF alias for future direct lookups
    if apif_id_num:
        save_alias(supabase, pid, apif_id_num)

    if career_updates or identity_updates:
        result["status"] = "updated"
    else:
        result["status"] = "no_changes"

    return result


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="API-Football → Warehouse sync")
    parser.add_argument("mode", choices=["team", "player", "all", "stale"],
                        help="Sync mode")
    parser.add_argument("target", nargs="?", default=None,
                        help="Team code (for 'team' mode) or player UUID (for 'player' mode)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be synced without making changes")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max players to sync (0 = all)")
    args = parser.parse_args()

    # Load credentials
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    api_key = os.environ.get("API_FOOTBALL_KEY")

    if not url or not key:
        env_paths = [
            Path(__file__).resolve().parent.parent.parent / ".env",
            Path(__file__).resolve().parent.parent.parent.parent / "la-copa-mundo" / ".env.local",
        ]
        for env_path in env_paths:
            if env_path.exists():
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
                            elif k == "API_FOOTBALL_KEY" and not api_key:
                                api_key = v

    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required.")
        sys.exit(1)
    if not api_key:
        print("ERROR: API_FOOTBALL_KEY required.")
        sys.exit(1)

    supabase = create_client(url, key)
    api = ApiFootball(api_key)

    print("=" * 60)
    print("  API-Football → Warehouse Sync")
    print("=" * 60)

    # Fetch players to sync
    if args.mode == "team":
        if not args.target:
            print("ERROR: team mode requires a team code (e.g., COL)")
            sys.exit(1)
        team_code = args.target.upper()
        print(f"\n  Mode: team sync ({team_code})")
        players = fetch_wc_players(supabase, team_code=team_code)
        apif_team_id = NATIONAL_TEAM_APIF_IDS.get(team_code)
        if apif_team_id:
            for p in players:
                p["apif_team_id"] = apif_team_id
        else:
            print(f"  WARNING: No API-Football team ID for {team_code}; search may fail (API requires team/league with search).")

    elif args.mode == "player":
        if not args.target:
            print("ERROR: player mode requires a warehouse UUID")
            sys.exit(1)
        # Fetch single player
        p_resp = supabase.table("players") \
            .select("id, known_as, full_legal_name, data_confidence") \
            .eq("id", args.target) \
            .single() \
            .execute()
        c_resp = supabase.table("player_career") \
            .select("player_id, current_club, current_league, position_primary") \
            .eq("player_id", args.target) \
            .single() \
            .execute()
        t_resp = supabase.table("player_tournament") \
            .select("player_id, wc_team_code") \
            .eq("player_id", args.target) \
            .single() \
            .execute()
        a_resp = supabase.table("player_aliases") \
            .select("alias_value") \
            .eq("player_id", args.target) \
            .eq("alias_type", "apif_id") \
            .execute()

        p = p_resp.data
        c = c_resp.data if c_resp.data else {}
        t = t_resp.data if t_resp.data else {}
        a_data = a_resp.data

        players = [{
            "player_id": p["id"],
            "name": p.get("known_as") or p.get("full_legal_name"),
            "full_name": p.get("full_legal_name") or "",
            "current_club": c.get("current_club"),
            "current_league": c.get("current_league"),
            "position": c.get("position_primary"),
            "confidence": p.get("data_confidence"),
            "wc_team_code": t.get("wc_team_code"),
            "apif_id": a_data[0]["alias_value"] if a_data else None,
        }]
        print(f"\n  Mode: single player ({players[0]['name']})")

    elif args.mode == "all":
        print(f"\n  Mode: all WC 2026 squad players")
        players = fetch_wc_players(supabase)
        for p in players:
            p["apif_team_id"] = NATIONAL_TEAM_APIF_IDS.get(p.get("wc_team_code") or "")

    elif args.mode == "stale":
        print(f"\n  Mode: stale players (low + medium confidence)")
        low = fetch_wc_players(supabase, confidence="low")
        med = fetch_wc_players(supabase, confidence="medium")
        players = low + med

    else:
        print(f"Unknown mode: {args.mode}")
        sys.exit(1)

    if args.limit and args.limit > 0:
        players = players[:args.limit]

    print(f"  Players to sync: {len(players)}")
    print(f"  Estimated API credits: ~{len(players) * 1.5:.0f}")

    if args.dry_run:
        print("\n  DRY RUN — showing players that would be synced:")
        for p in players[:20]:
            print(f"    {p['wc_team_code'] or '???'} | {p['name']} | {p['current_club']} | confidence={p['confidence']}")
        if len(players) > 20:
            print(f"    ... and {len(players) - 20} more")
        print(f"\n  Total API credits needed: ~{len(players) * 1.5:.0f}")
        return

    # Pre-fetch squads for team-scoped matching (team mode: one squad; all mode: one per team)
    if players and (args.mode == "team" or args.mode == "all"):
        if args.mode == "team" and players[0].get("apif_team_id"):
            apif_team_id = players[0]["apif_team_id"]
            try:
                squad_list = api.get_team_squad(apif_team_id)
                api.throttle()
                if squad_list:
                    for p in players:
                        p["squad_list"] = squad_list
            except Exception as e:
                print(f"  WARNING: Could not fetch team squad ({e}); will try search per player.")
        elif args.mode == "all":
            # Fetch squad per unique team and attach to players of that team
            teams_done = set()
            for p in players:
                tid = p.get("apif_team_id")
                if not tid or tid in teams_done:
                    continue
                teams_done.add(tid)
                try:
                    squad_list = api.get_team_squad(tid)
                    api.throttle()
                    if squad_list:
                        for q in players:
                            if q.get("apif_team_id") == tid:
                                q["squad_list"] = squad_list
                except Exception:
                    pass

    # Run sync
    stats = {"updated": 0, "no_changes": 0, "not_found": 0, "no_match": 0, "api_error": 0, "skipped": 0}
    changes_log = []

    for i, player in enumerate(players):
        result = sync_player(api, supabase, player)
        stats[result["status"]] = stats.get(result["status"], 0) + 1

        if result["changes"]:
            changes_log.append(result)
            for change in result["changes"]:
                print(f"  ✓ {player['name']}: {change}")

        if (i + 1) % 10 == 0:
            print(f"  ... {i + 1}/{len(players)} processed ({stats['updated']} updated)")

    # Summary
    print(f"\n{'='*60}")
    print(f"  SYNC COMPLETE")
    print(f"{'='*60}")
    print(f"  Players processed: {len(players)}")
    print(f"  Updated:           {stats['updated']}")
    print(f"  No changes:        {stats['no_changes']}")
    print(f"  Not found:         {stats['not_found']}")
    print(f"  No match:          {stats['no_match']}")
    print(f"  API errors:        {stats['api_error']}")
    print(f"  API calls made:    {api.calls}")
    print()

    if changes_log:
        print("  CHANGES MADE:")
        for r in changes_log:
            for c in r["changes"]:
                print(f"    {r['name']}: {c}")

    # Update freshness
    supabase.table("pipeline_freshness").upsert({
        "data_type": "apif_warehouse_sync",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "records_updated": stats["updated"],
        "status": "OK"
    }, on_conflict="data_type").execute()

    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
