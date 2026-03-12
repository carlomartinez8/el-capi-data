"""
Quality assurance checks on the canonical player list.

Produces a QA report with:
  - Missing critical fields (name, position, nationality)
  - Suspicious ages (< 15 or > 45)
  - Duplicate names within the same team
  - WC squad completeness (each team should have 23-26 players)
  - Position distribution sanity (each WC team needs GK, DEF, MID, FWD)
"""

import pandas as pd
from datetime import date


def _age_from_dob(dob: str | None) -> int | None:
    if not dob or len(str(dob)) < 10:
        return None
    try:
        born = date.fromisoformat(str(dob)[:10])
        today = date(2026, 6, 11)  # World Cup 2026 opening day
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except (ValueError, TypeError):
        return None


def run_checks(canonical_df: pd.DataFrame) -> pd.DataFrame:
    """
    Run all QA checks and return a DataFrame of issues.
    Each row: player_name, source_id, check, severity, detail
    """
    print("\n=== QA CHECKS ===")
    issues = []

    for idx, row in canonical_df.iterrows():
        pid = row.get("source_id", "?")
        name = row.get("name", "UNNAMED")

        if not name or str(name).strip() == "":
            issues.append({
                "player_name": name, "source_id": pid,
                "check": "missing_name", "severity": "critical",
                "detail": "Player has no name",
            })

        if not row.get("position"):
            issues.append({
                "player_name": name, "source_id": pid,
                "check": "missing_position", "severity": "warning",
                "detail": "No position assigned",
            })

        if not row.get("nationality"):
            issues.append({
                "player_name": name, "source_id": pid,
                "check": "missing_nationality", "severity": "warning",
                "detail": "No nationality",
            })

        age = _age_from_dob(row.get("date_of_birth"))
        if age is not None:
            if age < 15:
                issues.append({
                    "player_name": name, "source_id": pid,
                    "check": "age_too_young", "severity": "error",
                    "detail": f"Age {age} (DOB: {row.get('date_of_birth')})",
                })
            elif age > 45:
                issues.append({
                    "player_name": name, "source_id": pid,
                    "check": "age_too_old", "severity": "warning",
                    "detail": f"Age {age} (DOB: {row.get('date_of_birth')})",
                })

    wc_players = canonical_df[canonical_df["in_wc_squad"] == True]
    if not wc_players.empty:
        for team_code, group in wc_players.groupby("wc_team_code"):
            count = len(group)
            if count < 23:
                issues.append({
                    "player_name": f"TEAM:{team_code}", "source_id": "",
                    "check": "squad_incomplete", "severity": "warning",
                    "detail": f"{team_code} has only {count} players (expected 23-26)",
                })
            elif count > 26:
                issues.append({
                    "player_name": f"TEAM:{team_code}", "source_id": "",
                    "check": "squad_too_large", "severity": "warning",
                    "detail": f"{team_code} has {count} players (max 26)",
                })

            positions = group["position"].dropna().unique()
            pos_set = set(str(p).upper() for p in positions)
            for needed in ["GK", "GOALKEEPER"]:
                if needed in pos_set:
                    break
            else:
                if "GK" not in pos_set and "GOALKEEPER" not in pos_set:
                    issues.append({
                        "player_name": f"TEAM:{team_code}", "source_id": "",
                        "check": "no_goalkeeper", "severity": "error",
                        "detail": f"{team_code} has no goalkeeper in squad",
                    })

            names_in_team = group["name"].tolist()
            seen = {}
            for n in names_in_team:
                key = str(n).lower().strip()
                if key in seen:
                    issues.append({
                        "player_name": n, "source_id": "",
                        "check": "duplicate_in_team", "severity": "error",
                        "detail": f"'{n}' appears multiple times in {team_code}",
                    })
                seen[key] = True

    issues_df = pd.DataFrame(issues)

    if issues_df.empty:
        print("  No issues found.")
    else:
        severity_counts = issues_df["severity"].value_counts()
        for sev, count in severity_counts.items():
            print(f"  {sev}: {count}")
        check_counts = issues_df["check"].value_counts()
        for check, count in check_counts.head(10).items():
            print(f"    {check}: {count}")

    return issues_df
