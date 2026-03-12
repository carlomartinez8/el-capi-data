"""
Ingest Transfermarkt CSV data into a normalized pandas DataFrame.

Source: https://github.com/dcaribou/transfermarkt-datasets
Files expected: players.csv, clubs.csv, competitions.csv, transfers.csv, player_valuations.csv
"""

import math
import pandas as pd
from pipeline.config import TRANSFERMARKT_DATA_DIR


def _clean(val):
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return val


def load_players() -> pd.DataFrame:
    """Load all Transfermarkt players, keeping only those with a current club."""
    path = TRANSFERMARKT_DATA_DIR / "players.csv"
    print(f"  Reading {path}")
    df = pd.read_csv(path)

    active = df[df["current_club_id"].notna()].copy()
    print(f"  {len(active):,} active players (of {len(df):,} total)")

    records = []
    for _, row in active.iterrows():
        records.append({
            "source": "transfermarkt",
            "source_id": str(row["player_id"]),
            "name": _clean(row.get("name")),
            "first_name": _clean(row.get("first_name")),
            "last_name": _clean(row.get("last_name")),
            "date_of_birth": str(row["date_of_birth"])[:10] if pd.notna(row.get("date_of_birth")) else None,
            "nationality": _clean(row.get("country_of_citizenship")),
            "country_of_birth": _clean(row.get("country_of_birth")),
            "city_of_birth": _clean(row.get("city_of_birth")),
            "position": _clean(row.get("position")),
            "sub_position": _clean(row.get("sub_position")),
            "foot": _clean(row.get("foot")),
            "height_cm": int(float(row["height_in_cm"])) if pd.notna(row.get("height_in_cm")) else None,
            "current_club_id": str(int(row["current_club_id"])) if pd.notna(row.get("current_club_id")) else None,
            "current_club_name": _clean(row.get("current_club_name")),
            "market_value_eur": int(float(row["market_value_in_eur"])) if pd.notna(row.get("market_value_in_eur")) else None,
            "highest_market_value_eur": int(float(row["highest_market_value_in_eur"])) if pd.notna(row.get("highest_market_value_in_eur")) else None,
            "photo_url": _clean(row.get("image_url")),
            "transfermarkt_url": _clean(row.get("url")),
            "agent": _clean(row.get("agent_name")),
            "contract_expires": str(row["contract_expiration_date"])[:10] if pd.notna(row.get("contract_expiration_date")) else None,
        })

    return pd.DataFrame(records)


def load_clubs() -> pd.DataFrame:
    path = TRANSFERMARKT_DATA_DIR / "clubs.csv"
    print(f"  Reading {path}")
    df = pd.read_csv(path)

    records = []
    for _, row in df.iterrows():
        records.append({
            "club_id": str(row["club_id"]),
            "name": _clean(row.get("name")),
            "country": _clean(row.get("domestic_competition_id")),
            "squad_size": int(float(row["squad_size"])) if pd.notna(row.get("squad_size")) else None,
            "avg_age": round(float(row["average_age"]), 1) if pd.notna(row.get("average_age")) else None,
            "total_market_value": int(float(row["total_market_value"])) if pd.notna(row.get("total_market_value")) else None,
        })

    return pd.DataFrame(records)


def load_transfers() -> pd.DataFrame:
    path = TRANSFERMARKT_DATA_DIR / "transfers.csv"
    print(f"  Reading {path}")
    return pd.read_csv(path)


def load_valuations() -> pd.DataFrame:
    path = TRANSFERMARKT_DATA_DIR / "player_valuations.csv"
    print(f"  Reading {path}")
    return pd.read_csv(path)
