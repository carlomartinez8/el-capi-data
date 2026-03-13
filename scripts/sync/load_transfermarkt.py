#!/usr/bin/env python3
"""
La Copa Mundo — Transfermarkt Data Loader (Historical Enrichment Pipeline)

Downloads the open Transfermarkt dataset from GitHub and loads it into Supabase.
This is the base layer: 30k+ players, clubs, transfers, valuations.

Run frequency: Weekly (to catch dataset updates)
"""

import os
import math
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from tqdm import tqdm
from datetime import datetime, timezone

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env.local"))

SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

client = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH_SIZE = 500


def upsert_in_batches(table: str, records: list, desc: str, on_conflict: str = "id"):
    """Upsert records into Supabase in batches."""
    total_batches = math.ceil(len(records) / BATCH_SIZE)
    failed = 0
    for i in tqdm(range(total_batches), desc=desc):
        batch = records[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        try:
            client.table(table).upsert(batch, on_conflict=on_conflict).execute()
        except Exception as e:
            failed += 1
            if failed <= 3:
                tqdm.write(f"  ⚠ batch {i} failed: {str(e)[:120]}")
    if failed:
        tqdm.write(f"  ⚠ {failed}/{total_batches} batches failed (FK or constraint issues — skipped)")


def clean(val):
    """Convert NaN/None to None for JSON serialization."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return val


def load_competitions(data_dir: str):
    print("\n→ Loading competitions...")
    df = pd.read_csv(os.path.join(data_dir, "competitions.csv"))
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
    return len(records)


def load_clubs(data_dir: str):
    print("\n→ Loading clubs...")
    df = pd.read_csv(os.path.join(data_dir, "clubs.csv"))
    records = []
    for _, row in df.iterrows():
        records.append({
            "id": str(row["club_id"]),
            "name": clean(row.get("name")),
            "country": clean(row.get("domestic_competition_id")),
            "domestic_league": clean(row.get("domestic_competition_id")),
            "squad_size": int(float(row["squad_size"])) if pd.notna(row.get("squad_size")) else None,
            "avg_age": round(float(row["average_age"]), 1) if pd.notna(row.get("average_age")) else None,
            "total_market_value": int(float(row["total_market_value"])) if pd.notna(row.get("total_market_value")) else None,
        })
    upsert_in_batches("clubs", records, "clubs")
    print(f"  ✓ {len(records)} clubs loaded")
    return len(records)


def load_players(data_dir: str):
    print("\n→ Loading players...")
    df = pd.read_csv(os.path.join(data_dir, "players.csv"))

    # Focus on active players with a current club
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
            "height_cm": int(float(row["height_in_cm"])) if pd.notna(row.get("height_in_cm")) else None,
            "current_club_id": str(int(row["current_club_id"])) if pd.notna(row.get("current_club_id")) else None,
            "current_club_name": clean(row.get("current_club_name")),
            "market_value_eur": int(float(row["market_value_in_eur"])) if pd.notna(row.get("market_value_in_eur")) else None,
            "highest_market_value": int(float(row["highest_market_value_in_eur"])) if pd.notna(row.get("highest_market_value_in_eur")) else None,
            "country_of_birth": clean(row.get("country_of_birth")),
            "city_of_birth": clean(row.get("city_of_birth")),
            "photo_url": clean(row.get("image_url")),
            "transfermarkt_url": clean(row.get("url")),
            "agent": clean(row.get("agent_name")),
            "contract_expires": clean(str(row["contract_expiration_date"])[:10]) if pd.notna(row.get("contract_expiration_date")) else None,
        })

    upsert_in_batches("pipeline_players", records, "players")
    player_ids = {r["id"] for r in records}
    print(f"  ✓ {len(records)} players loaded")
    return len(records), player_ids


def load_transfers(data_dir: str, valid_player_ids: set):
    print("\n→ Loading transfers...")
    df = pd.read_csv(os.path.join(data_dir, "transfers.csv"))
    seen_ids = {}
    records = []
    skipped = 0
    for _, row in df.iterrows():
        player_id = str(row["player_id"])
        if player_id not in valid_player_ids:
            skipped += 1
            continue
        season = str(clean(row.get("transfer_season")) or "")
        to_club = str(clean(row.get("to_club_id")) or "")
        base_id = f"{player_id}_{season}_{to_club}"
        seen_ids[base_id] = seen_ids.get(base_id, 0) + 1
        record_id = base_id if seen_ids[base_id] == 1 else f"{base_id}_{seen_ids[base_id]}"

        records.append({
            "id": record_id,
            "player_id": player_id,
            "from_club_id": str(int(row["from_club_id"])) if pd.notna(row.get("from_club_id")) else None,
            "from_club_name": clean(row.get("from_club_name")),
            "to_club_id": str(int(row["to_club_id"])) if pd.notna(row.get("to_club_id")) else None,
            "to_club_name": clean(row.get("to_club_name")),
            "transfer_date": clean(str(row["transfer_date"])[:10]) if pd.notna(row.get("transfer_date")) else None,
            "season": season,
            "transfer_fee_eur": int(float(row["transfer_fee"])) if pd.notna(row.get("transfer_fee")) else None,
            "transfer_type": clean(row.get("transfer_type")),
        })

    if skipped:
        print(f"  Skipped {skipped:,} rows (player not in pipeline_players)")
    upsert_in_batches("transfers", records, "transfers")
    print(f"  ✓ {len(records):,} transfers loaded")
    return len(records)


def load_player_valuations(data_dir: str, valid_player_ids: set):
    print("\n→ Loading player valuations...")
    df = pd.read_csv(os.path.join(data_dir, "player_valuations.csv"))
    records = []
    seen = set()
    skipped = 0
    for _, row in df.iterrows():
        pid = str(row["player_id"])
        if pid not in valid_player_ids:
            skipped += 1
            continue
        vdate = clean(str(row["date"])[:10]) if pd.notna(row.get("date")) else None
        dedup_key = (pid, vdate)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        records.append({
            "player_id": pid,
            "market_value_eur": int(float(row["market_value_in_eur"])) if pd.notna(row.get("market_value_in_eur")) else None,
            "valuation_date": vdate,
            "club_id": str(int(row["current_club_id"])) if pd.notna(row.get("current_club_id")) else None,
        })
    if skipped:
        print(f"  Skipped {skipped:,} rows (player not in pipeline_players)")
    upsert_in_batches("player_valuations", records, "valuations", on_conflict="player_id,valuation_date")
    print(f"  ✓ {len(records):,} valuation records loaded")
    return len(records)


def mark_freshness(data_type: str, count: int):
    client.table("pipeline_freshness").upsert({
        "data_type": data_type,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "records_updated": count,
        "status": "OK"
    }, on_conflict="data_type").execute()


if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("La Copa Mundo — Transfermarkt Data Loader")
    print("=" * 50)

    # Data directory — pass as arg or use default
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    n_comp = load_competitions(data_dir)
    mark_freshness("transfermarkt_competitions", n_comp)

    n_clubs = load_clubs(data_dir)
    mark_freshness("transfermarkt_clubs", n_clubs)

    n_players, player_ids = load_players(data_dir)
    mark_freshness("transfermarkt_players", n_players)

    n_transfers = load_transfers(data_dir, player_ids)
    mark_freshness("transfermarkt_transfers", n_transfers)

    n_vals = load_player_valuations(data_dir, player_ids)
    mark_freshness("transfermarkt_valuations", n_vals)

    print("\n✅ Transfermarkt base load complete.")
    print("Check your Supabase table editor to verify row counts.")
