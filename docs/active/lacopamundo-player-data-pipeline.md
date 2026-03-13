# La Copa Mundo — Player Data Pipeline
## Engineering Implementation Guide

**Project:** lacopamundo.com  
**Prepared by:** Carlo  
**Target:** Engineering team — execute end to end  
**Goal:** Populate Supabase with rich player bio data from three sources, wired to Capi

---

## Overview

This document gives you everything you need to get player data flowing into Supabase for La Copa Mundo. By the end of this, Capi will have access to rich player profiles — bios, career history, transfers, youth clubs, market values — pulled from three complementary free/low-cost sources.

**The three sources:**

| Source | What It Provides | Cost | Method |
|---|---|---|---|
| **Transfermarkt Dataset** (GitHub) | 30k+ players, full transfer history, market value, youth clubs | Free | Download CSV → load to Supabase |
| **Wikipedia REST API** | Narrative biography text for top players | Free | API call per player |
| **API-Football** | Current club, live stats, match events, injuries | Free tier (100 req/day) / ~$15/mo paid | API polling |

These three together give Capi richer player profiles than most commercial sports apps.

---

## Prerequisites

Before starting, make sure you have the following:

- Python 3.10+
- A Supabase project created at [supabase.com](https://supabase.com) (free tier is fine)
- Your `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from the Supabase dashboard → Settings → API
- An API-Football key from [api-football.com](https://www.api-football.com) (free tier to start)
- `pip`, `git`, and basic terminal access

Install Python dependencies:

```bash
pip install supabase requests pandas python-dotenv tqdm
```

Create a `.env` file in your project root:

```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
API_FOOTBALL_KEY=your-api-football-key
```

> **Note:** Use the `SERVICE_ROLE_KEY` (not the anon key) for backend scripts — it bypasses Row Level Security and can write to all tables.

---

## Step 1 — Set Up Supabase Schema

Go to your Supabase project → SQL Editor and run the following. This creates all the tables Capi will query.

```sql
-- ============================================================
-- CLUBS
-- ============================================================
CREATE TABLE IF NOT EXISTS clubs (
    id                  TEXT PRIMARY KEY,         -- Transfermarkt club ID
    name                TEXT NOT NULL,
    name_short          TEXT,
    country             TEXT,
    domestic_league     TEXT,
    squad_size          INTEGER,
    avg_age             NUMERIC(4,1),
    total_market_value  BIGINT,                   -- in EUR
    logo_url            TEXT,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COMPETITIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS competitions (
    id                  TEXT PRIMARY KEY,         -- Transfermarkt competition ID
    name                TEXT NOT NULL,
    country             TEXT,
    confederation       TEXT,                     -- UEFA, CONMEBOL, CONCACAF, etc.
    is_active           BOOLEAN DEFAULT TRUE,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PLAYERS (core bio + current status)
-- ============================================================
CREATE TABLE IF NOT EXISTS players (
    id                      TEXT PRIMARY KEY,     -- Transfermarkt player ID
    name                    TEXT NOT NULL,
    name_short              TEXT,
    date_of_birth           DATE,
    age                     INTEGER,
    nationality             TEXT,
    nationality_secondary   TEXT,
    position                TEXT,
    sub_position            TEXT,
    foot                    TEXT,
    height_cm               INTEGER,
    current_club_id         TEXT REFERENCES clubs(id),
    current_club_name       TEXT,                 -- denormalized for fast Capi queries
    jersey_number           INTEGER,
    market_value_eur        BIGINT,
    highest_market_value    BIGINT,
    contract_expires        DATE,
    agent                   TEXT,
    photo_url               TEXT,
    transfermarkt_url       TEXT,
    country_of_birth        TEXT,
    city_of_birth           TEXT,
    is_active               BOOLEAN DEFAULT TRUE,
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_players_nationality ON players(nationality);
CREATE INDEX IF NOT EXISTS idx_players_current_club ON players(current_club_id);
CREATE INDEX IF NOT EXISTS idx_players_position ON players(position);

-- ============================================================
-- PLAYER BIOS (Wikipedia narrative text)
-- ============================================================
CREATE TABLE IF NOT EXISTS player_bios (
    player_id           TEXT PRIMARY KEY REFERENCES players(id),
    bio_summary         TEXT,                     -- Wikipedia extract (2-3 paragraphs)
    bio_source          TEXT DEFAULT 'wikipedia',
    wikipedia_url       TEXT,
    last_fetched        TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TRANSFER HISTORY
-- ============================================================
CREATE TABLE IF NOT EXISTS transfers (
    id                  TEXT PRIMARY KEY,         -- transfermarkt_playerid_season_clubto
    player_id           TEXT REFERENCES players(id),
    from_club_id        TEXT,
    from_club_name      TEXT,
    to_club_id          TEXT,
    to_club_name        TEXT,
    transfer_date       DATE,
    season              TEXT,                     -- "2023" = 2023/24
    transfer_fee_eur    BIGINT,
    transfer_type       TEXT,                     -- Transfer, Loan, Free Transfer, End of loan
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transfers_player ON transfers(player_id);

-- ============================================================
-- PLAYER VALUATIONS (market value history)
-- ============================================================
CREATE TABLE IF NOT EXISTS player_valuations (
    id                  BIGSERIAL PRIMARY KEY,
    player_id           TEXT REFERENCES players(id),
    market_value_eur    BIGINT,
    valuation_date      DATE,
    club_id             TEXT,
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(player_id, valuation_date)
);

-- ============================================================
-- MATCH APPEARANCES
-- ============================================================
CREATE TABLE IF NOT EXISTS appearances (
    id                  TEXT PRIMARY KEY,         -- Transfermarkt appearance ID
    player_id           TEXT REFERENCES players(id),
    competition_id      TEXT,
    competition_name    TEXT,
    club_id             TEXT,
    season              TEXT,
    match_date          DATE,
    home_club           TEXT,
    away_club           TEXT,
    goals               INTEGER DEFAULT 0,
    assists             INTEGER DEFAULT 0,
    yellow_cards        INTEGER DEFAULT 0,
    red_cards           INTEGER DEFAULT 0,
    minutes_played      INTEGER,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appearances_player ON appearances(player_id);
CREATE INDEX IF NOT EXISTS idx_appearances_season ON appearances(season);

-- ============================================================
-- LIVE MATCHES (active match cache — refreshed every 60s)
-- ============================================================
CREATE TABLE IF NOT EXISTS active_matches (
    id                  TEXT PRIMARY KEY,
    competition         TEXT,
    home_club           TEXT,
    away_club           TEXT,
    home_score          INTEGER DEFAULT 0,
    away_score          INTEGER DEFAULT 0,
    minute              INTEGER,
    status              TEXT,                     -- 1H, HT, 2H, ET, P, FT
    last_event          TEXT,
    venue               TEXT,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PIPELINE FRESHNESS (metadata — helps Capi tell users data age)
-- ============================================================
CREATE TABLE IF NOT EXISTS pipeline_freshness (
    data_type           TEXT PRIMARY KEY,
    last_updated        TIMESTAMPTZ,
    next_update         TIMESTAMPTZ,
    records_updated     INTEGER,
    status              TEXT DEFAULT 'OK'         -- OK, STALE, FAILING
);

INSERT INTO pipeline_freshness (data_type, status) VALUES
    ('transfermarkt_players', 'PENDING'),
    ('transfermarkt_transfers', 'PENDING'),
    ('wikipedia_bios', 'PENDING'),
    ('api_football_live', 'PENDING')
ON CONFLICT (data_type) DO NOTHING;
```

Verify in Supabase → Table Editor that all 8 tables appear before moving on.

---

## Step 2 — Load Transfermarkt Base Dataset

This is the fastest win. A pre-built, clean dataset of 30k+ players sourced from Transfermarkt is available on GitHub, updated weekly. We download it and load it directly into Supabase.

### 2.1 Download the Dataset

```bash
# Create a working directory
mkdir lacopamundo-pipeline && cd lacopamundo-pipeline

# Download the Transfermarkt dataset CSVs directly
curl -L "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/players.csv.gz" -o players.csv.gz
curl -L "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/clubs.csv.gz" -o clubs.csv.gz
curl -L "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfers.csv.gz" -o transfers.csv.gz
curl -L "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/player_valuations.csv.gz" -o player_valuations.csv.gz
curl -L "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/appearances.csv.gz" -o appearances.csv.gz
curl -L "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/competitions.csv.gz" -o competitions.csv.gz

# Decompress
gunzip *.csv.gz
```

You should now have 6 CSV files in your directory.

### 2.2 Load Script

Create `load_transfermarkt.py`:

```python
import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from tqdm import tqdm
import math

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

client = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH_SIZE = 500  # Supabase upsert limit per call


def upsert_in_batches(table: str, records: list, desc: str):
    """Upsert records into Supabase in batches."""
    total_batches = math.ceil(len(records) / BATCH_SIZE)
    for i in tqdm(range(total_batches), desc=desc):
        batch = records[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        client.table(table).upsert(batch, on_conflict="id").execute()


def clean(val):
    """Convert NaN/None to None for JSON serialization."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return val


def load_competitions():
    print("\n→ Loading competitions...")
    df = pd.read_csv("competitions.csv")
    records = []
    for _, row in df.iterrows():
        records.append({
            "id": str(row["competition_id"]),
            "name": clean(row.get("name")),
            "country": clean(row.get("country_id")),
            "confederation": clean(row.get("confederation")),
        })
    upsert_in_batches("competitions", records, "competitions")
    print(f"  ✓ {len(records)} competitions loaded")


def load_clubs():
    print("\n→ Loading clubs...")
    df = pd.read_csv("clubs.csv")
    records = []
    for _, row in df.iterrows():
        records.append({
            "id": str(row["club_id"]),
            "name": clean(row.get("name")),
            "country": clean(row.get("domestic_competition_id")),  # country code via competition
            "domestic_league": clean(row.get("domestic_competition_id")),
            "squad_size": clean(row.get("squad_size")),
            "avg_age": clean(row.get("average_age")),
            "total_market_value": clean(row.get("total_market_value")),
        })
    upsert_in_batches("clubs", records, "clubs")
    print(f"  ✓ {len(records)} clubs loaded")


def load_players():
    print("\n→ Loading players...")
    df = pd.read_csv("players.csv")

    # Focus on active players with a current club — reduces noise
    # Remove this filter if you want the full 30k+ historical set
    active = df[df["current_club_id"].notna()].copy()
    print(f"  Active players with current club: {len(active):,}")

    records = []
    for _, row in active.iterrows():
        records.append({
            "id": str(row["player_id"]),
            "name": clean(row.get("name")),
            "date_of_birth": clean(str(row["date_of_birth"])[:10]) if pd.notna(row.get("date_of_birth")) else None,
            "nationality": clean(row.get("country_of_citizenship")),
            "position": clean(row.get("position")),
            "sub_position": clean(row.get("sub_position")),
            "foot": clean(row.get("foot")),
            "height_cm": clean(row.get("height_in_cm")),
            "current_club_id": str(int(row["current_club_id"])) if pd.notna(row.get("current_club_id")) else None,
            "current_club_name": clean(row.get("current_club_name")),
            "market_value_eur": clean(row.get("market_value_in_eur")),
            "highest_market_value": clean(row.get("highest_market_value_in_eur")),
            "country_of_birth": clean(row.get("country_of_birth")),
            "city_of_birth": clean(row.get("city_of_birth")),
            "photo_url": clean(row.get("image_url")),
            "transfermarkt_url": clean(row.get("url")),
            "agent": clean(row.get("agent_name")),
            "contract_expires": clean(str(row["contract_expiration_date"])[:10]) if pd.notna(row.get("contract_expiration_date")) else None,
        })

    upsert_in_batches("players", records, "players")
    print(f"  ✓ {len(records)} players loaded")


def load_transfers():
    print("\n→ Loading transfers...")
    df = pd.read_csv("transfers.csv")
    records = []
    for _, row in df.iterrows():
        player_id = str(row["player_id"])
        season = str(clean(row.get("transfer_season")) or "")
        to_club = str(clean(row.get("to_club_id")) or "")
        record_id = f"{player_id}_{season}_{to_club}"

        records.append({
            "id": record_id,
            "player_id": player_id,
            "from_club_id": str(int(row["from_club_id"])) if pd.notna(row.get("from_club_id")) else None,
            "from_club_name": clean(row.get("from_club_name")),
            "to_club_id": str(int(row["to_club_id"])) if pd.notna(row.get("to_club_id")) else None,
            "to_club_name": clean(row.get("to_club_name")),
            "transfer_date": clean(str(row["transfer_date"])[:10]) if pd.notna(row.get("transfer_date")) else None,
            "season": season,
            "transfer_fee_eur": clean(row.get("transfer_fee")),
            "transfer_type": clean(row.get("transfer_type")),
        })

    upsert_in_batches("transfers", records, "transfers")
    print(f"  ✓ {len(records)} transfers loaded")


def load_player_valuations():
    print("\n→ Loading player valuations...")
    df = pd.read_csv("player_valuations.csv")
    records = []
    for _, row in df.iterrows():
        records.append({
            "player_id": str(row["player_id"]),
            "market_value_eur": clean(row.get("market_value_in_eur")),
            "valuation_date": clean(str(row["date"])[:10]) if pd.notna(row.get("date")) else None,
            "club_id": str(int(row["current_club_id"])) if pd.notna(row.get("current_club_id")) else None,
        })
    upsert_in_batches("player_valuations", records, "valuations")
    print(f"  ✓ {len(records)} valuation records loaded")


def mark_freshness(data_type: str, count: int):
    from datetime import datetime, timezone
    client.table("pipeline_freshness").upsert({
        "data_type": data_type,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "records_updated": count,
        "status": "OK"
    }, on_conflict="data_type").execute()


if __name__ == "__main__":
    print("=" * 50)
    print("La Copa Mundo — Transfermarkt Data Loader")
    print("=" * 50)

    load_competitions()
    load_clubs()
    load_players()
    load_transfers()
    load_player_valuations()

    print("\n✅ Transfermarkt base load complete.")
    print("Check your Supabase table editor to verify row counts.")
```

Run it:

```bash
python load_transfermarkt.py
```

**Expected output:**
```
→ Loading competitions... ✓ ~40 competitions
→ Loading clubs...        ✓ ~400 clubs
→ Loading players...      ✓ ~18,000–22,000 active players
→ Loading transfers...    ✓ ~100,000+ transfers
→ Loading valuations...   ✓ ~400,000+ valuation records
```

This will take 5–15 minutes depending on your connection. The valuations table is the biggest — be patient.

---

## Step 3 — Enrich with Wikipedia Bios

Wikipedia has free, well-written biographical summaries for the top ~2,000 professional players. The REST API returns a clean extract with no authentication required.

### 3.1 How the Wikipedia API Works

```
GET https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}
```

Returns a JSON object with a `extract` field containing a 2–4 paragraph plain-text bio. No API key, no rate limits (just be reasonable — add a small sleep between calls).

### 3.2 Wikipedia Bio Enrichment Script

Create `enrich_wikipedia.py`:

```python
import os
import time
import requests
from supabase import create_client
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
SLEEP_BETWEEN_CALLS = 0.3  # seconds — be respectful to Wikipedia


def search_wikipedia(player_name: str) -> dict | None:
    """
    Try to find a Wikipedia page for a player.
    Wikipedia page titles are usually "Firstname Lastname" — try direct match first,
    then try with underscore formatting.
    """
    # Normalize: "L. Messi" won't work; we need full names from Transfermarkt
    title = player_name.replace(" ", "_")
    url = WIKIPEDIA_API.format(title)

    try:
        resp = requests.get(url, timeout=5, headers={"User-Agent": "LaCopasMundo/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            # Confirm it's actually a footballer, not a disambiguation page
            if data.get("type") == "standard" and data.get("extract"):
                extract = data["extract"].lower()
                # Basic relevance check — confirm it's about a footballer
                if any(kw in extract for kw in ["football", "soccer", "footballer", "midfielder", "striker", "goalkeeper", "defender", "winger"]):
                    return {
                        "bio_summary": data["extract"],
                        "wikipedia_url": data.get("content_urls", {}).get("desktop", {}).get("page")
                    }
    except Exception as e:
        pass

    return None


def enrich_bios(limit: int = None, min_market_value: int = 5_000_000):
    """
    Fetch Wikipedia bios for players above a market value threshold.
    Start with top players (high market value) for best Wikipedia coverage.
    
    Args:
        limit: Max number of players to process (None = all)
        min_market_value: Only target players with market value above this (EUR)
    """
    print(f"\n→ Fetching players with market value ≥ €{min_market_value:,}...")

    # Get players who don't have a bio yet, ordered by market value
    query = client.table("players")\
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

    print(f"\n✅ Done. Found: {found} | Not found: {not_found}")
    print(f"   Wikipedia coverage: {found / len(players) * 100:.1f}%")

    # Update freshness
    from datetime import datetime, timezone
    client.table("pipeline_freshness").upsert({
        "data_type": "wikipedia_bios",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "records_updated": found,
        "status": "OK"
    }, on_conflict="data_type").execute()


if __name__ == "__main__":
    print("=" * 50)
    print("La Copa Mundo — Wikipedia Bio Enrichment")
    print("=" * 50)

    # Phase 1: Top 500 players (market value ≥ €20M) — run first, fastest
    enrich_bios(min_market_value=20_000_000)

    # Uncomment to expand to more players after verifying Phase 1 works:
    # enrich_bios(min_market_value=5_000_000)
```

Run it:

```bash
python enrich_wikipedia.py
```

**Expected results:** ~70–80% hit rate for players with market value ≥ €20M. The top 500 players in the world almost all have Wikipedia pages. This will take ~3–5 minutes for 500 players.

---

## Step 4 — Layer in API-Football (Current Club + Live Stats)

API-Football fills the gaps Transfermarkt doesn't cover — live match events, current injuries, and confirmed squad data refreshed in real time.

### 4.1 API-Football Setup

Sign up at [api-football.com](https://www.api-football.com) → get your API key → add to `.env`.

The base URL for all calls:
```
https://v3.football.api-sports.io/
```

All requests need this header:
```
x-apisports-key: YOUR_KEY
```

Free tier: **100 requests/day**. Paid tier (recommended): $15/mo for 7,500 requests/day.

### 4.2 Sync Current Club Data

API-Football uses its own player IDs — not Transfermarkt IDs. The sync script matches by player name + nationality. It's not perfect, but gets ~85% coverage for top players.

Create `sync_api_football.py`:

```python
import os
import time
import requests
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)

API_KEY = os.environ["API_FOOTBALL_KEY"]
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Competition IDs for World Cup 2026 relevant competitions
# Full list: https://www.api-football.com/documentation-v3#tag/Leagues
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

CURRENT_SEASON = 2024  # API-Football uses the start year


def api_get(endpoint: str, params: dict) -> dict:
    """Make an API-Football GET request."""
    resp = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers=HEADERS,
        params=params,
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def check_rate_limit(response_data: dict):
    """Log API credit usage."""
    remaining = response_data.get("parameters", {})
    # API-Football returns rate limit info in headers — check console
    pass


def sync_league_squads(league_id: int, league_name: str, season: int = CURRENT_SEASON):
    """
    Fetch all squads for a given league and upsert into clubs + players tables.
    This is the most API-credit-efficient way to get current squad data.
    """
    print(f"\n  → {league_name} (league_id={league_id})")

    # Step 1: Get all teams in the league
    teams_data = api_get("teams", {"league": league_id, "season": season})
    teams = teams_data.get("response", [])
    print(f"    Found {len(teams)} teams")

    for team in teams:
        team_id = team["team"]["id"]
        team_name = team["team"]["name"]

        # Upsert club
        client.table("clubs").upsert({
            "id": f"apif_{team_id}",  # prefix to avoid collision with TM IDs
            "name": team_name,
            "logo_url": team["team"].get("logo"),
            "country": team["team"].get("country"),
        }, on_conflict="id").execute()

        time.sleep(0.5)  # Respect rate limits

        # Step 2: Get squad for this team
        squad_data = api_get("players/squads", {"team": team_id})
        squad = squad_data.get("response", [])

        if not squad:
            continue

        players = squad[0].get("players", [])

        for p in players:
            client.table("players").upsert({
                "id": f"apif_{p['id']}",  # prefix to avoid collision
                "name": p["name"],
                "age": p.get("age"),
                "position": p.get("position"),
                "jersey_number": p.get("number"),
                "photo_url": p.get("photo"),
                "current_club_id": f"apif_{team_id}",
                "current_club_name": team_name,
            }, on_conflict="id").execute()

        time.sleep(1)  # Respect rate limits

    print(f"    ✓ {league_name} squads synced")


def sync_live_matches():
    """
    Fetch all currently live matches and populate active_matches table.
    Call this every 60 seconds during match windows.
    """
    data = api_get("fixtures", {"live": "all"})
    matches = data.get("response", [])

    # Clear old live data
    client.table("active_matches").delete().neq("id", "placeholder").execute()

    if not matches:
        print("  No live matches right now.")
        return

    rows = []
    for m in matches:
        fixture = m["fixture"]
        teams = m["teams"]
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
            "home_club": teams["home"]["name"],
            "away_club": teams["away"]["name"],
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


if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("La Copa Mundo — API-Football Sync")
    print("=" * 50)

    mode = sys.argv[1] if len(sys.argv) > 1 else "squads"

    if mode == "live":
        # Run this every 60s during match windows
        print("\n→ Syncing live matches...")
        sync_live_matches()

    elif mode == "squads":
        # Run this daily — syncs all squads for priority leagues
        # WARNING: Uses ~50–100 API credits per league. Start with 1–2 leagues.
        print("\n→ Syncing league squads...")
        print("  (Running Premier League + La Liga first to test)")

        sync_league_squads(39, "Premier League")
        sync_league_squads(140, "La Liga")

        # Uncomment to add more leagues (each uses ~30–50 API credits):
        # sync_league_squads(135, "Serie A")
        # sync_league_squads(78, "Bundesliga")
        # sync_league_squads(128, "Argentine Primera")
        # sync_league_squads(71, "Brazilian Série A")
```

Run squad sync (do this once to start, then daily via cron):

```bash
python sync_api_football.py squads
```

Run live match sync (during match days):

```bash
python sync_api_football.py live
```

---

## Step 5 — Automate with Cron Jobs

Once the scripts are verified working, automate them.

### On a Mac/Linux machine (simple setup for testing):

```bash
crontab -e
```

Add these lines:

```cron
# Squad sync — every day at 6am UTC
0 6 * * * cd /path/to/lacopamundo-pipeline && python sync_api_football.py squads >> logs/squads.log 2>&1

# Wikipedia bio enrichment — every Sunday at 3am
0 3 * * 0 cd /path/to/lacopamundo-pipeline && python enrich_wikipedia.py >> logs/wiki.log 2>&1

# Live scores — every 60s (only meaningful on match days, but safe to run always)
* * * * * cd /path/to/lacopamundo-pipeline && python sync_api_football.py live >> logs/live.log 2>&1
```

### On a server / EC2 (recommended for production):

Use a simple systemd service or a GitHub Actions scheduled workflow. If you're already using AWS, an EventBridge + Lambda is the cleanest setup — but a $5/mo EC2 t3.micro with cron is perfectly fine for this stage.

---

## Step 6 — Verify Data in Supabase

Run these queries in Supabase → SQL Editor to confirm everything loaded correctly:

```sql
-- Check record counts across all tables
SELECT 'players' as table_name, COUNT(*) as rows FROM players
UNION ALL SELECT 'clubs', COUNT(*) FROM clubs
UNION ALL SELECT 'competitions', COUNT(*) FROM competitions
UNION ALL SELECT 'transfers', COUNT(*) FROM transfers
UNION ALL SELECT 'player_valuations', COUNT(*) FROM player_valuations
UNION ALL SELECT 'player_bios', COUNT(*) FROM player_bios
UNION ALL SELECT 'active_matches', COUNT(*) FROM active_matches;

-- Spot check: top players by market value
SELECT name, nationality, position, current_club_name,
       market_value_eur / 1000000 as value_millions_eur
FROM players
ORDER BY market_value_eur DESC
LIMIT 20;

-- Check Wikipedia bio coverage
SELECT
    COUNT(*) as total_players,
    COUNT(pb.player_id) as players_with_bios,
    ROUND(COUNT(pb.player_id)::numeric / COUNT(*)::numeric * 100, 1) as coverage_pct
FROM players p
LEFT JOIN player_bios pb ON p.id = pb.player_id
WHERE p.market_value_eur >= 10000000;

-- Sample a bio
SELECT p.name, p.nationality, p.current_club_name, pb.bio_summary
FROM players p
JOIN player_bios pb ON p.id = pb.player_id
WHERE p.name ILIKE '%Messi%'
LIMIT 1;

-- Check pipeline freshness
SELECT data_type, last_updated, records_updated, status
FROM pipeline_freshness
ORDER BY last_updated DESC;
```

**Expected healthy counts (approximate):**

| Table | Expected Rows |
|---|---|
| players | 18,000 – 22,000 |
| clubs | 300 – 500 |
| competitions | 30 – 50 |
| transfers | 80,000 – 120,000 |
| player_valuations | 350,000 – 500,000 |
| player_bios | 400 – 800 (after Wikipedia enrichment) |

---

## Step 7 — Wire Capi to Query Supabase (Anthropic Tool Use)

Capi now queries the pipeline tables dynamically at runtime using **Anthropic tool use** (function calling). Instead of baking all player/match data into the system prompt, Capi has 5 tools that query Supabase on demand.

### Architecture Overview

```
User asks "Who is Haaland?"
  → POST /api/capi/chat
    → anthropic.messages.create({ tools: CAPI_TOOLS, ... })
      → Claude responds with tool_use: search_players({ query: "Haaland" })
        → executeCapiTool("search_players", { query: "Haaland" })
          → Supabase query on pipeline_players table
        → Result fed back to Claude
      → Claude responds with final text answer
    → SSE stream to client
```

### Key Files

| File | Purpose |
|---|---|
| `src/lib/capi/tools.ts` | Tool definitions (5 tools) + Supabase execution handlers |
| `src/app/api/capi/chat/route.ts` | Agentic loop: calls Claude → executes tools → feeds results back |
| `src/lib/capi/system-prompt.ts` | LIVE_DATA_TOOLS_NOTE layer tells Capi when to use tools vs. built-in knowledge |

### The 5 Tools

| Tool | Trigger | Supabase Table |
|---|---|---|
| `search_players` | User asks about a player by name | `pipeline_players` (ilike search, ordered by market value) |
| `get_player_details` | Need bio, value history, full profile | `pipeline_players` + `player_bios` + `player_valuations` (parallel) |
| `get_squad` | User asks about a club's roster | `clubs` (name lookup) → `pipeline_players` (by club_id) |
| `get_live_matches` | User asks about live scores | `active_matches` + `pipeline_freshness` fallback |
| `get_transfer_history` | User asks about career moves | `transfers` (by player_id, date desc) |

### Agentic Loop (`runToolUseLoop`)

The chat route uses a non-streaming loop pattern:

1. Call `anthropic.messages.create()` with `tools: CAPI_TOOLS`
2. If `stop_reason === 'tool_use'`, execute all tool_use blocks in parallel via `Promise.all()`
3. Feed tool results back as a `user` message with `tool_result` content blocks
4. Repeat (max 3 rounds) until Claude produces a final text response
5. Chunk the final text into 12-char SSE events for simulated streaming

This trades ~1-2s of latency (for tool execution) for accurate, fresh data. Most conversations don't trigger tool use — only factual player/match queries do.

### System Prompt Integration

The `LIVE_DATA_TOOLS_NOTE` layer (added to system-prompt.ts) tells Capi:

- **Use tools** for current factual data: player's current club, market value, squad rosters, live scores, transfer history
- **Use built-in knowledge** for opinions, predictions, historical context, cultural discussion
- **Fall back gracefully** if tools return no results — mention that live data isn't available

### Example Tool Queries (What Supabase Sees)

```sql
-- search_players("Messi")
SELECT id, name, position, age, nationality, current_club_name, market_value_eur, jersey_number
FROM pipeline_players
WHERE name ILIKE '%Messi%'
ORDER BY market_value_eur DESC NULLS LAST
LIMIT 5;

-- get_squad("Barcelona")
SELECT id, name FROM clubs WHERE name ILIKE '%Barcelona%' LIMIT 3;
SELECT id, name, position, age, jersey_number, nationality, market_value_eur
FROM pipeline_players
WHERE current_club_id = 'apif_529'
ORDER BY position, name;

-- get_live_matches()
SELECT * FROM active_matches ORDER BY updated_at DESC;

-- get_transfer_history(player_id)
SELECT from_club_name, to_club_name, transfer_fee_eur, transfer_date, season
FROM transfers
WHERE player_id = '...'
ORDER BY transfer_date DESC;
```

---

## Troubleshooting

### "Row violates row-level security policy"
You're using the anon key instead of the service role key. Switch to `SUPABASE_SERVICE_ROLE_KEY` in your `.env` for all backend scripts. Never use the service role key in frontend code.

### Wikipedia returning 404 or disambiguation pages
The player name from Transfermarkt may not match the Wikipedia article title exactly. Common issues:
- Players known by one name (e.g. "Neymar" vs "Neymar Jr.")
- Accented characters (try both with and without accents)
- Middle names included in Transfermarkt but not Wikipedia

The script already does a basic relevance check — players with no Wikipedia article just get skipped. Bio coverage of ~70% for top players is normal and expected.

### API-Football "Too many requests" error
You've hit your daily credit limit. The free tier is 100 requests/day. Each squad sync call costs ~1 request per team. For a full league (20 teams), that's ~20–40 requests. Upgrade to a paid plan or stagger your syncs across multiple days.

### Supabase upsert conflict errors
Check that the `id` column values are consistent between runs. For Transfermarkt data, the IDs come from the CSV. For API-Football, we prefix with `apif_` to avoid collision. If you see conflict errors, run `SELECT id FROM players LIMIT 10` to check the format.

### Large CSV taking too long
The player_valuations table is large (~400k rows). If the load is timing out, reduce `BATCH_SIZE` to 100 and run overnight. Alternatively, skip the valuations table initially — it's nice to have but not required for Capi to function.

---

## What's Next (Handed back to Carlo)

Once the pipeline is running and Capi is querying Supabase successfully, the next phase is the Steppingblocks data fabric integration:

- Migrate the Supabase schema to Snowflake (same DDL, minor type adjustments)
- Add the Steppingblocks education + career layer on top of the player profiles
- Build the Athlete Intelligence API as the unified endpoint Capi consumes
- Set up Airflow DAGs to replace the cron scripts

The Supabase setup you build here is the proof of concept. Everything maps cleanly to the production Snowflake architecture.

---

## Quick Reference — Key Files

### Pipeline Scripts

| File | Purpose | Run Frequency |
|---|---|---|
| `scripts/pipeline/load_transfermarkt.py` | One-time base load + weekly refresh | Weekly (re-run to catch dataset updates) |
| `scripts/pipeline/enrich_wikipedia.py` | Bio enrichment for top players | Weekly |
| `scripts/pipeline/sync_api_football.py squads` | Current squad sync | Daily at 6am |
| `scripts/pipeline/sync_api_football.py live` | Live match scores | Every 60s (via cron) |

### Capi Integration

| File | Purpose |
|---|---|
| `src/lib/capi/tools.ts` | 5 Anthropic tool definitions + Supabase execution handlers |
| `src/app/api/capi/chat/route.ts` | Chat endpoint with agentic tool use loop |
| `src/lib/capi/system-prompt.ts` | System prompt layers (includes LIVE_DATA_TOOLS_NOTE for tool guidance) |

### API Routes

| Route | Purpose | Auth |
|---|---|---|
| `POST /api/capi/chat` | Capi chat endpoint (tool use + SSE streaming) | Rate limit + usage tracking |
| `GET /api/cron/pipeline-sync?mode=live` | Sync live match scores | CRON_SECRET bearer token |
| `GET /api/cron/pipeline-sync?mode=squads` | Sync league squads | CRON_SECRET bearer token |
| `GET /api/cron/pipeline-sync?mode=freshness` | Check pipeline data freshness | CRON_SECRET bearer token |

### Database

| File | Purpose |
|---|---|
| `supabase/migrations/20260311_player_data_pipeline.sql` | Creates 8 pipeline tables + indexes + RLS |

---

*Document prepared by Carlo for the La Copa Mundo engineering team.*
*Questions → slack Carlo or refer to the companion architecture documents.*
