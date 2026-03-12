"""
Build authoritative career_trajectory from Transfermarkt transfers.csv.

For each player identified by their TM player_id, extracts a chronological
list of transfers — ground-truth data that replaces GPT-hallucinated timelines.

Usage:
    python -m pipeline.reconcile.career_builder
"""

import math
import pandas as pd
from pipeline.config import TRANSFERMARKT_DATA_DIR


def _clean_fee(val) -> str | None:
    """Normalize transfer fee to a human-readable string."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    try:
        amount = float(val)
    except (ValueError, TypeError):
        return None
    if amount == 0:
        return "Free transfer"
    if amount >= 1_000_000:
        return f"€{amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"€{amount / 1_000:.0f}K"
    return f"€{amount:.0f}"


def build_career_trajectories() -> dict[str, list[dict]]:
    """
    Returns {tm_player_id: [{"season": ..., "from": ..., "to": ..., "fee": ...}, ...]}
    sorted chronologically per player.
    """
    path = TRANSFERMARKT_DATA_DIR / "transfers.csv"
    print(f"  Reading {path}")
    df = pd.read_csv(path)
    print(f"  {len(df):,} total transfer records")

    trajectories: dict[str, list[dict]] = {}

    for pid, group in df.groupby("player_id"):
        pid_str = str(int(pid))
        moves = []
        for _, row in group.sort_values("transfer_date").iterrows():
            moves.append({
                "season": str(row.get("transfer_season", "")),
                "date": str(row["transfer_date"])[:10] if pd.notna(row.get("transfer_date")) else None,
                "from": row.get("from_club_name"),
                "to": row.get("to_club_name"),
                "fee": _clean_fee(row.get("transfer_fee")),
            })
        if moves:
            trajectories[pid_str] = moves

    print(f"  Career trajectories built for {len(trajectories):,} players")
    return trajectories


def format_trajectory_text(moves: list[dict]) -> str:
    """Format a career trajectory as a human-readable timeline string."""
    parts = []
    for m in moves:
        fee_str = f" ({m['fee']})" if m.get("fee") else ""
        if m.get("from") and m.get("to"):
            parts.append(f"{m.get('date', '?')} — {m['from']} → {m['to']}{fee_str}")
        elif m.get("to"):
            parts.append(f"{m.get('date', '?')} — Joined {m['to']}{fee_str}")
    return " | ".join(parts) if parts else ""


if __name__ == "__main__":
    trajectories = build_career_trajectories()
    for pid, moves in list(trajectories.items())[:3]:
        print(f"\nPlayer {pid}: {len(moves)} transfers")
        for m in moves[:5]:
            fee = f" ({m['fee']})" if m.get('fee') else ""
            print(f"  {m.get('date', '?')}: {m.get('from','?')} → {m.get('to','?')}{fee}")
