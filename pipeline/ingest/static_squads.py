"""
Parse the hand-curated players.ts file from la-copa-mundo.

Extracts projected World Cup 2026 rosters — these are the "golden" WC squad
definitions, curated by humans. Used as a high-confidence signal during dedup.
"""

import re
import pandas as pd
from pipeline.config import STATIC_SQUADS_PATH


def _parse_player_object(obj_str: str) -> dict | None:
    """Parse a single TS player object like { name: "X", number: 1, ... }."""
    result = {}

    for key in ("name", "position", "club"):
        m = re.search(rf'{key}\s*:\s*"([^"]*)"', obj_str)
        if m:
            result[key] = m.group(1)

    for key in ("number", "age"):
        m = re.search(rf'{key}\s*:\s*(\d+)', obj_str)
        if m:
            result[key] = int(m.group(1))

    result["captain"] = "captain: true" in obj_str

    return result if result.get("name") else None


def load_static_squads() -> pd.DataFrame:
    """
    Parse players.ts and return a flat DataFrame with one row per player.
    Columns: source, source_id, name, position, current_club_name, age,
             jersey_number, captain, wc_team_code
    """
    print(f"  Reading {STATIC_SQUADS_PATH}")

    with open(STATIC_SQUADS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(r'//[^\n]*', '', content)

    squads_match = re.search(r'export const SQUADS.*?=\s*\{', content)
    if not squads_match:
        raise ValueError("Could not find SQUADS export in players.ts")

    body = content[squads_match.end():]

    team_pattern = re.compile(r'([A-Z]{3})\s*:\s*\[')
    player_pattern = re.compile(r'\{([^}]+)\}')

    records = []
    for team_match in team_pattern.finditer(body):
        team_code = team_match.group(1)
        start = team_match.end()

        bracket_depth = 1
        end = start
        for i in range(start, len(body)):
            if body[i] == '[':
                bracket_depth += 1
            elif body[i] == ']':
                bracket_depth -= 1
                if bracket_depth == 0:
                    end = i
                    break

        team_block = body[start:end]

        for pm in player_pattern.finditer(team_block):
            player = _parse_player_object(pm.group(0))
            if player:
                records.append({
                    "source": "static_squad",
                    "source_id": f"static_{team_code}_{player.get('number', 0)}",
                    "name": player["name"],
                    "position": player.get("position"),
                    "current_club_name": player.get("club"),
                    "age": player.get("age"),
                    "jersey_number": player.get("number"),
                    "captain": player.get("captain", False),
                    "wc_team_code": team_code,
                })

    df = pd.DataFrame(records)
    team_count = df["wc_team_code"].nunique() if not df.empty else 0
    print(f"  {len(df)} players across {team_count} teams")
    return df
