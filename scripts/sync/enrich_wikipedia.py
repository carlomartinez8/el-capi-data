#!/usr/bin/env python3
"""
La Copa Mundo — Wikipedia Bio Enrichment (Historical Enrichment Pipeline)

Fetches Wikipedia biographical summaries for top players and stores them
in the player_bios table. Targets players by market value for best coverage.

Run frequency: Weekly (Sunday at 3am)
"""

import os
import time
import requests
from supabase import create_client
from dotenv import load_dotenv
from tqdm import tqdm
from datetime import datetime, timezone

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env.local"))

client = create_client(
    os.environ["NEXT_PUBLIC_SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
SLEEP_BETWEEN_CALLS = 0.3


FOOTBALL_KEYWORDS = [
    "football", "soccer", "footballer", "midfielder",
    "striker", "goalkeeper", "defender", "winger",
    "forward", "centre-back", "full-back", "playmaker",
    "national team", "cap", "liga", "premier league",
    "serie a", "bundesliga", "ligue 1", "world cup",
]

WIKIPEDIA_SEARCH_API = "https://en.wikipedia.org/w/api.php"


def _try_summary(title: str) -> dict | None:
    """Fetch a Wikipedia summary by exact title. Returns bio dict or None."""
    url = WIKIPEDIA_API.format(title.replace(" ", "_"))
    try:
        resp = requests.get(url, timeout=5, headers={"User-Agent": "LaCopaMundo/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            if data.get("type") == "standard" and data.get("extract"):
                extract = data["extract"].lower()
                if any(kw in extract for kw in FOOTBALL_KEYWORDS):
                    return {
                        "bio_summary": data["extract"],
                        "wikipedia_url": data.get("content_urls", {}).get("desktop", {}).get("page")
                    }
    except Exception:
        pass
    return None


def _search_wikipedia_titles(query: str, limit: int = 3) -> list[str]:
    """Use Wikipedia search API to find candidate article titles."""
    try:
        resp = requests.get(WIKIPEDIA_SEARCH_API, timeout=5, params={
            "action": "query",
            "list": "search",
            "srsearch": f"{query} footballer",
            "srlimit": limit,
            "format": "json",
        }, headers={"User-Agent": "LaCopaMundo/1.0"})
        if resp.status_code == 200:
            results = resp.json().get("query", {}).get("search", [])
            return [r["title"] for r in results]
    except Exception:
        pass
    return []


def search_wikipedia(player_name: str) -> dict | None:
    """
    Try to find a Wikipedia page for a player.
    Strategy:
      1. Direct title lookup (fastest, works for most players)
      2. Fallback to Wikipedia search API with "footballer" hint
    """
    # Attempt 1: Direct title match
    result = _try_summary(player_name)
    if result:
        return result

    # Attempt 2: Search API fallback — handles accents, disambiguations, name variants
    titles = _search_wikipedia_titles(player_name)
    for title in titles:
        result = _try_summary(title)
        if result:
            return result

    return None


def enrich_bios(limit: int = None, min_market_value: int = 5_000_000, apif_only: bool = False):
    """
    Fetch Wikipedia bios for players.
    - Default: targets players above a market value threshold (Transfermarkt data).
    - apif_only=True: targets API-Football players (apif_* IDs) regardless of market value.
      These are current World Cup / league squad members who may lack TM valuations.
    """
    if apif_only:
        print("\n→ Fetching API-Football players (current squad members)...")
        query = client.table("pipeline_players")\
            .select("id, name, market_value_eur")\
            .like("id", "apif_%")\
            .order("name")
    else:
        print(f"\n→ Fetching players with market value ≥ €{min_market_value:,}...")
        query = client.table("pipeline_players")\
            .select("id, name, market_value_eur")\
            .gte("market_value_eur", min_market_value)\
            .order("market_value_eur", desc=True)

    if limit:
        query = query.limit(limit)

    result = query.execute()
    players = result.data
    print(f"  Found {len(players)} players to enrich")

    # Filter out players who already have bios
    existing = client.table("player_bios").select("player_id").execute()
    existing_ids = {r["player_id"] for r in existing.data}
    players = [p for p in players if p["id"] not in existing_ids]
    print(f"  {len(players)} players still need bios")

    if not players:
        print("  All players already have bios!")
        return 0

    found = 0
    not_found = 0

    for player in tqdm(players, desc="Wikipedia bios"):
        bio_data = search_wikipedia(player["name"])

        if bio_data:
            client.table("player_bios").upsert({
                "player_id": player["id"],
                "bio_summary": bio_data["bio_summary"],
                "wikipedia_url": bio_data["wikipedia_url"],
                "bio_source": "wikipedia",
            }, on_conflict="player_id").execute()
            found += 1
        else:
            not_found += 1

        time.sleep(SLEEP_BETWEEN_CALLS)

    total = found + not_found
    pct = (found / total * 100) if total > 0 else 0
    print(f"\n✅ Done. Found: {found} | Not found: {not_found}")
    print(f"   Wikipedia coverage: {pct:.1f}%")

    # Update freshness
    client.table("pipeline_freshness").upsert({
        "data_type": "wikipedia_bios",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "records_updated": found,
        "status": "OK"
    }, on_conflict="data_type").execute()

    return found


if __name__ == "__main__":
    print("=" * 50)
    print("La Copa Mundo — Wikipedia Bio Enrichment")
    print("=" * 50)

    # Phase 1: Top players by market value (€20M+) — best Wikipedia hit rate
    enrich_bios(min_market_value=20_000_000)

    # Phase 2: Broader Transfermarkt set (€5M+)
    enrich_bios(min_market_value=5_000_000)

    # Phase 3: API-Football squad players — current WC/league rosters
    # These often have NULL market_value_eur so Phase 1-2 misses them
    enrich_bios(apif_only=True)
