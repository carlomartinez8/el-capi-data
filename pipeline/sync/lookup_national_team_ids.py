#!/usr/bin/env python3
"""One-off: call API-Football /teams?country=X for missing FIFA codes and print id. Run with API_FOOTBALL_KEY set."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import requests

missing = [
    ("ALG", "Algeria"), ("AUT", "Austria"), ("CPV", "Cape Verde"), ("CRO", "Croatia"),
    ("CUW", "Curaçao"), ("IRN", "Iran"), ("JOR", "Jordan"), ("KSA", "Saudi Arabia"),
    ("NOR", "Norway"), ("NZL", "New Zealand"), ("QAT", "Qatar"), ("RSA", "South Africa"),
    ("SCO", "Scotland"), ("SUI", "Switzerland"), ("TUN", "Tunisia"), ("UZB", "Uzbekistan"),
]
key = os.environ.get("API_FOOTBALL_KEY")
if not key:
    print("Set API_FOOTBALL_KEY", file=sys.stderr)
    sys.exit(1)
for code, name in missing:
    r = requests.get(
        "https://v3.football.api-sports.io/teams",
        params={"country": name},
        headers={"x-apisports-key": key},
        timeout=10,
    )
    d = r.json()
    teams = d.get("response", [])
    tid = None
    for t in teams:
        tn = (t.get("team") or {}).get("name") or ""
        if name.lower() in tn.lower() or (code == "RSA" and "South Africa" in tn) or (code == "SCO" and "Scotland" in tn):
            tid = t["team"]["id"]
            break
    if not tid and teams:
        tid = teams[0]["team"]["id"]
    print(f'    "{code}": {tid or "?"},   # {name}')
