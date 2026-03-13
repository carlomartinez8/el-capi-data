#!/usr/bin/env python3
"""
La Copa Mundo — API-Football Sync (Live Pipeline)

Two modes:
  squads  — Sync current squad rosters for priority leagues (daily at 6am)
  live    — Sync live match scores (every 60s via cron during match windows)

API Docs: https://www.api-football.com/documentation-v3
"""

import os
import sys
import time
import requests
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env.local"))

client = create_client(
    os.environ["NEXT_PUBLIC_SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)

API_KEY = os.environ["API_FOOTBALL_KEY"]
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Priority leagues for World Cup 2026 squad tracking
PRIORITY_LEAGUES = {
    "FIFA World Cup 2026": 1,
    "Premier League": 39,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
    "MLS": 253,
    "Liga MX": 262,
    "Argentine Primera": 128,
    "Brazilian Série A": 71,
    "CONMEBOL Qualifiers": 31,
    "UEFA Qualifiers": 32,
}

CURRENT_SEASON = 2025  # API-Football uses the start year


def api_get(endpoint: str, params: dict) -> dict:
    """Make an API-Football GET request with error handling."""
    resp = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers=HEADERS,
        params=params,
        timeout=15
    )
    resp.raise_for_status()
    data = resp.json()

    # Log remaining credits
    remaining = data.get("errors", {})
    if remaining:
        print(f"    ⚠️ API errors: {remaining}")

    return data


def sync_league_squads(league_id: int, league_name: str, season: int = CURRENT_SEASON):
    """
    Fetch all squads for a league and upsert into clubs + pipeline_players.
    Uses ~30-50 API credits per league.
    """
    print(f"\n  → {league_name} (league_id={league_id})")

    # Get all teams in the league
    teams_data = api_get("teams", {"league": league_id, "season": season})
    teams = teams_data.get("response", [])
    print(f"    Found {len(teams)} teams")

    total_players = 0

    for team_entry in teams:
        team = team_entry["team"]
        team_id = team["id"]
        team_name = team["name"]

        # Upsert club (prefix with apif_ to avoid ID collision with Transfermarkt)
        client.table("clubs").upsert({
            "id": f"apif_{team_id}",
            "name": team_name,
            "logo_url": team.get("logo"),
            "country": team.get("country"),
        }, on_conflict="id").execute()

        time.sleep(0.5)

        # Get squad for this team
        squad_data = api_get("players/squads", {"team": team_id})
        squad = squad_data.get("response", [])

        if not squad:
            continue

        players = squad[0].get("players", [])

        for p in players:
            client.table("pipeline_players").upsert({
                "id": f"apif_{p['id']}",
                "name": p["name"],
                "age": p.get("age"),
                "position": p.get("position"),
                "jersey_number": p.get("number"),
                "photo_url": p.get("photo"),
                "current_club_id": f"apif_{team_id}",
                "current_club_name": team_name,
            }, on_conflict="id").execute()

        total_players += len(players)
        time.sleep(1)

    print(f"    ✓ {league_name}: {len(teams)} teams, {total_players} players synced")
    return total_players


def sync_live_matches():
    """
    Fetch all currently live matches and populate active_matches table.
    """
    data = api_get("fixtures", {"live": "all"})
    matches = data.get("response", [])

    # Clear old live data
    client.table("active_matches").delete().neq("id", "placeholder").execute()

    if not matches:
        print("  No live matches right now.")
        # Update freshness even if no matches
        client.table("pipeline_freshness").upsert({
            "data_type": "api_football_live",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "records_updated": 0,
            "status": "OK"
        }, on_conflict="data_type").execute()
        return 0

    rows = []
    for m in matches:
        fixture = m["fixture"]
        teams_data = m["teams"]
        goals = m["goals"]
        league = m["league"]

        # Get last event if available
        events = m.get("events", [])
        last_event = None
        if events:
            e = events[-1]
            last_event = f"{e['type']} - {e['player']['name']} ({e['time']['elapsed']}')"

        rows.append({
            "id": str(fixture["id"]),
            "competition": league["name"],
            "home_club": teams_data["home"]["name"],
            "away_club": teams_data["away"]["name"],
            "home_score": goals["home"] or 0,
            "away_score": goals["away"] or 0,
            "minute": fixture["status"]["elapsed"],
            "status": fixture["status"]["short"],
            "last_event": last_event,
            "venue": fixture.get("venue", {}).get("name"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })

    if rows:
        client.table("active_matches").insert(rows).execute()

    # Update freshness
    client.table("pipeline_freshness").upsert({
        "data_type": "api_football_live",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "records_updated": len(rows),
        "status": "OK"
    }, on_conflict="data_type").execute()

    print(f"  ✓ {len(rows)} live matches updated")
    return len(rows)


def sync_wc_squads():
    """
    Sync national team squads for all 48 World Cup 2026 qualified nations.
    This is the most important dataset for Capi — the actual WC rosters.
    """
    print("\n→ Syncing World Cup 2026 national squads...")

    # World Cup 2026 league_id = 1, season = 2026
    wc_data = api_get("teams", {"league": 1, "season": 2026})
    teams = wc_data.get("response", [])

    if not teams:
        # Fallback: try current qualifiers season
        print("  World Cup 2026 data not yet available, trying qualifiers...")
        return 0

    total_players = 0
    for team_entry in teams:
        team = team_entry["team"]
        team_id = team["id"]
        team_name = team["name"]

        client.table("clubs").upsert({
            "id": f"apif_nt_{team_id}",
            "name": f"{team_name} (National Team)",
            "logo_url": team.get("logo"),
            "country": team_name,
        }, on_conflict="id").execute()

        time.sleep(0.5)

        squad_data = api_get("players/squads", {"team": team_id})
        squad = squad_data.get("response", [])

        if squad:
            players = squad[0].get("players", [])
            for p in players:
                client.table("pipeline_players").upsert({
                    "id": f"apif_{p['id']}",
                    "name": p["name"],
                    "age": p.get("age"),
                    "position": p.get("position"),
                    "jersey_number": p.get("number"),
                    "photo_url": p.get("photo"),
                    "nationality": team_name,
                }, on_conflict="id").execute()
            total_players += len(players)

        time.sleep(1)

    print(f"  ✓ {len(teams)} national teams, {total_players} players synced")
    return total_players


def sync_transfers(batch_size: int = 200):
    """
    Fetch transfer history from API-Football for APIF players who have
    zero transfers in the database. Fills the gap left by Transfermarkt CSVs
    (e.g. Messi, Neymar have 0 TM transfer rows).

    API endpoint: GET /transfers?player={apif_player_id}
    Cost: 1 credit per player. With 7,500/day Pro budget, batch_size caps usage.
    """
    print("\n→ Syncing transfer history for APIF players with missing transfers...")

    # Find APIF players who have no transfers at all
    # Step 1: get all APIF player IDs
    all_apif = client.table("pipeline_players")\
        .select("id, name")\
        .like("id", "apif_%")\
        .execute()

    if not all_apif.data:
        print("  No APIF players found.")
        return 0

    apif_ids = {p["id"] for p in all_apif.data}
    apif_lookup = {p["id"]: p["name"] for p in all_apif.data}

    # Step 2: get player_ids that already have transfers
    existing = client.table("transfers")\
        .select("player_id")\
        .like("player_id", "apif_%")\
        .execute()

    has_transfers = {r["player_id"] for r in (existing.data or [])}

    # Step 3: players that need transfers fetched
    missing = apif_ids - has_transfers
    print(f"  {len(apif_ids)} APIF players total, {len(has_transfers)} already have transfers")
    print(f"  {len(missing)} players need transfer history")

    # Limit batch to conserve API credits
    to_fetch = sorted(missing)[:batch_size]
    print(f"  Fetching transfers for {len(to_fetch)} players (batch_size={batch_size})")

    total_transfers = 0
    players_with_data = 0

    for i, apif_id in enumerate(to_fetch):
        # Extract numeric ID from "apif_154" → 154
        numeric_id = apif_id.replace("apif_", "")

        try:
            data = api_get("transfers", {"player": numeric_id})
            transfers = data.get("response", [])

            if transfers and len(transfers) > 0:
                # API returns nested: response[0].transfers = [...]
                player_transfers = transfers[0].get("transfers", [])

                for t in player_transfers:
                    teams = t.get("teams", {})
                    from_team = teams.get("out", {})
                    to_team = teams.get("in", {})
                    transfer_date = t.get("date")
                    transfer_type = t.get("type")  # e.g. "Loan", "Free", "N/A"

                    # Build a unique transfer ID
                    tid = f"apif_t_{numeric_id}_{transfer_date}_{from_team.get('id', 'unk')}"

                    client.table("transfers").upsert({
                        "id": tid,
                        "player_id": apif_id,
                        "from_club_id": f"apif_{from_team.get('id', '')}" if from_team.get("id") else None,
                        "from_club_name": from_team.get("name"),
                        "to_club_id": f"apif_{to_team.get('id', '')}" if to_team.get("id") else None,
                        "to_club_name": to_team.get("name"),
                        "transfer_date": transfer_date,
                        "transfer_type": transfer_type,
                    }, on_conflict="id").execute()

                    total_transfers += 1

                players_with_data += 1

        except Exception as e:
            print(f"    ⚠️ Failed for {apif_lookup.get(apif_id, apif_id)}: {e}")

        time.sleep(1.5)  # Throttle: protect production Supabase

        if (i + 1) % 25 == 0:
            time.sleep(3)

    print(f"  ✓ Fetched {total_transfers} transfers for {players_with_data} players")

    # Update freshness
    client.table("pipeline_freshness").upsert({
        "data_type": "api_football_transfers",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "records_updated": total_transfers,
        "status": "OK"
    }, on_conflict="data_type").execute()

    return total_transfers


def resolve_names(batch_size: int = 200, enrich_all: bool = False):
    """
    Enrich APIF player profiles using the /players/profiles endpoint.

    Resolves abbreviated names (e.g. "L. Messi" → "Lionel Messi") and
    fills/overwrites fields with APIF data (most current source):
    date_of_birth, height_cm, nationality, country_of_birth, city_of_birth.

    Modes:
      default  — only targets abbreviated names ("X. Surname" pattern)
      --all    — enriches ALL APIF players (DOB, height, nationality, birth place)

    Cost: 1 credit per player.
    """
    import re

    mode_label = "all APIF players" if enrich_all else "abbreviated names only"
    print(f"\n→ Enriching APIF player profiles ({mode_label})...")

    result = client.table("pipeline_players")\
        .select("id, name, date_of_birth, height_cm, nationality, country_of_birth, city_of_birth")\
        .like("id", "apif_%")\
        .execute()

    if not result.data:
        print("  No APIF players found.")
        return 0

    if enrich_all:
        # Target all APIF players that are missing any enrichable field
        targets = [
            p for p in result.data
            if not p.get("date_of_birth")
            or not p.get("height_cm")
            or not p.get("nationality")
            or not p.get("country_of_birth")
            or re.match(r'^.{1,2}\.\s', p["name"])
        ]
    else:
        # Only abbreviated names
        targets = [
            p for p in result.data
            if re.match(r'^.{1,2}\.\s', p["name"])
        ]

    print(f"  {len(targets)} players to enrich (out of {len(result.data)} total APIF)")

    if not targets:
        return 0

    # Process in batches
    resolved = 0
    enriched = 0
    skipped = 0
    errors = 0

    for i, p in enumerate(targets[:batch_size]):
        apif_id = p["id"].replace("apif_", "")

        try:
            data = api_get("players/profiles", {"player": apif_id})
            profiles = data.get("response", [])

            if not profiles:
                skipped += 1
                continue

            player_data = profiles[0].get("player", {})
            firstname = (player_data.get("firstname") or "").strip()
            lastname = (player_data.get("lastname") or "").strip()
            birth = player_data.get("birth") or {}
            nationality = (player_data.get("nationality") or "").strip()
            height_str = (player_data.get("height") or "").strip()  # e.g. "170"

            # Build update payload — only set fields we can improve
            updates = {}

            # --- Name resolution ---
            if firstname and lastname:
                # Use first word of firstname + first word of lastname
                # "Lionel Andrés" → "Lionel", "Messi Cuccittini" → "Messi"
                first = firstname.split()[0]
                last = lastname.split()[0]
                full_name = f"{first} {last}".strip()
                if full_name and full_name != p["name"]:
                    updates["name"] = full_name

            # --- Date of birth (APIF always wins — most current source) ---
            dob = (birth.get("date") or "").strip()  # "1987-06-24"
            if dob:
                updates["date_of_birth"] = dob

            # --- Birth place (APIF always wins) ---
            birth_country = (birth.get("country") or "").strip()
            birth_city = (birth.get("place") or "").strip()
            if birth_country:
                updates["country_of_birth"] = birth_country
            if birth_city:
                updates["city_of_birth"] = birth_city

            # --- Nationality (APIF always wins) ---
            if nationality:
                updates["nationality"] = nationality

            # --- Height (APIF always wins) ---
            if height_str:
                try:
                    h = int(height_str.replace(" cm", "").strip())
                    if 100 < h < 230:  # sanity check
                        updates["height_cm"] = h
                except ValueError:
                    pass

            if not updates:
                skipped += 1
                continue

            # Apply update
            client.table("pipeline_players").update(updates)\
                .eq("id", p["id"]).execute()

            if "name" in updates:
                resolved += 1
            enriched += 1

            if enriched % 25 == 0:
                print(f"    ... {enriched} enriched, {resolved} names resolved ({i+1}/{min(batch_size, len(targets))})")

        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"    ❌ Error for {p['id']} ({p['name']}): {e}")

        time.sleep(1.5)  # Throttle: protect production Supabase from connection saturation

        # Extra pause every 25 records to let the connection pool breathe
        if (i + 1) % 25 == 0:
            time.sleep(3)

    print(f"  ✓ {enriched} enriched, {resolved} names resolved, {skipped} skipped, {errors} errors")

    # Update freshness
    client.table("pipeline_freshness").upsert({
        "data_type": "apif_name_resolution",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "records_updated": resolved,
        "status": "OK"
    }, on_conflict="data_type").execute()

    return resolved


if __name__ == "__main__":
    print("=" * 50)
    print("La Copa Mundo — API-Football Sync")
    print("=" * 50)

    mode = sys.argv[1] if len(sys.argv) > 1 else "squads"

    if mode == "live":
        print("\n→ Syncing live matches...")
        sync_live_matches()

    elif mode == "wc":
        sync_wc_squads()

    elif mode == "squads":
        print("\n→ Syncing league squads...")

        total = 0
        for league_name, league_id in PRIORITY_LEAGUES.items():
            if league_id in (1, 31, 32):
                continue  # WC / qualifiers handled by 'wc' mode
            try:
                total += sync_league_squads(league_id, league_name)
            except Exception as e:
                print(f"    ❌ Failed for {league_name}: {e}")

        # Update freshness
        client.table("pipeline_freshness").upsert({
            "data_type": "api_football_squads",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "records_updated": total,
            "status": "OK"
        }, on_conflict="data_type").execute()

    elif mode == "transfers":
        # Backfill transfer history for APIF players missing from TM data
        batch = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        sync_transfers(batch_size=batch)

    elif mode == "names":
        # Enrich APIF profiles (names + DOB + height + nationality + birth place)
        # --all flag enriches ALL APIF players, not just abbreviated names
        all_flag = "--all" in sys.argv
        remaining_args = [a for a in sys.argv[2:] if a != "--all"]
        batch = int(remaining_args[0]) if remaining_args else 200
        resolve_names(batch_size=batch, enrich_all=all_flag)

    elif mode == "all":
        # Full sync: WC squads + top leagues + transfers + live
        sync_wc_squads()
        for league_name, league_id in PRIORITY_LEAGUES.items():
            try:
                sync_league_squads(league_id, league_name)
            except Exception as e:
                print(f"    ❌ Failed for {league_name}: {e}")
        sync_transfers(batch_size=200)
        sync_live_matches()

    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python sync_api_football.py [squads|live|wc|transfers|all]")
        print("  transfers [batch_size]  — backfill transfer history (default 200 players)")
        print("  names [batch_size] [--all] — enrich APIF profiles (--all = all players, not just abbreviated)")
        sys.exit(1)

    print("\n✅ API-Football sync complete.")
