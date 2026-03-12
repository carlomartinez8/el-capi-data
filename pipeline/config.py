"""
Shared configuration — loads .env once, exposes paths and constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

TRANSFERMARKT_DATA_DIR = Path(
    os.getenv("TRANSFERMARKT_DATA_DIR", PROJECT_ROOT / ".." / "la-copa-mundo" / "scripts" / "pipeline" / "data")
).resolve()

STATIC_SQUADS_PATH = Path(
    os.getenv("STATIC_SQUADS_PATH", PROJECT_ROOT / ".." / "la-copa-mundo" / "src" / "data" / "players.ts")
).resolve()

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
OUTPUT_DIR = DATA_DIR / "output"

for d in (RAW_DIR, INTERMEDIATE_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)


STATIC_BIOS_PATH = Path(
    os.getenv("STATIC_BIOS_PATH", PROJECT_ROOT / ".." / "la-copa-mundo" / "src" / "data" / "player-bios.ts")
).resolve()

BIOS_DIR = Path(
    os.getenv("BIOS_DIR", PROJECT_ROOT / ".." / "la-copa-mundo" / "src" / "data" / "bios")
).resolve()

RECONCILIATION_REPORT = OUTPUT_DIR / "reconciliation_report.json"
RECONCILIATION_CSV = OUTPUT_DIR / "reconciliation_review.csv"

POSITION_MAP = {
    "Attack": "FWD",
    "Midfield": "MID",
    "Defender": "DEF",
    "Goalkeeper": "GK",
}

COMPETITION_ID_TO_LEAGUE: dict[str, str] = {
    "GB1": "Premier League",
    "ES1": "La Liga",
    "L1": "Bundesliga",
    "IT1": "Serie A",
    "FR1": "Ligue 1",
    "PO1": "Primeira Liga",
    "NL1": "Eredivisie",
    "TR1": "Süper Lig",
    "BE1": "Belgian Pro League",
    "SC1": "Scottish Premiership",
    "DK1": "Danish Superliga",
    "GR1": "Super League Greece",
    "RU1": "Russian Premier League",
    "UKR1": "Ukrainian Premier League",
    "SA1": "Saudi Pro League",
    "MLS1": "Major League Soccer",
    "AR1N": "Argentine Primera División",
    "BRA1": "Campeonato Brasileiro Série A",
    "MX1": "Liga MX",
    "CO1": "Liga BetPlay",
    "CL1": "Chilean Primera División",
    "PE1": "Liga 1",
    "EC1": "LigaPro",
    "UY1": "Uruguayan Primera División",
    "A1": "A-League",
    "J1": "J1 League",
    "K1": "K League 1",
    "C1": "Chinese Super League",
    "QSL": "Qatar Stars League",
    "UAE1": "UAE Pro League",
    "EG1": "Egyptian Premier League",
    "RSA1": "Premier Soccer League",
    "IR1": "Persian Gulf Pro League",
    "PL1": "Ekstraklasa",
    "RO1": "Liga I",
    "SER1": "Serbian SuperLiga",
    "CRO1": "Prva HNL",
    "SLO1": "Slovenian PrvaLiga",
    "HUN1": "Nemzeti Bajnokság I",
    "CZ1": "Czech First League",
    "A1BU": "Austrian Bundesliga",
    "SE1": "Allsvenskan",
    "NO1": "Eliteserien",
    "FI1": "Veikkausliiga",
    "IS1": "Úrvalsdeild",
    "UZ1": "Uzbekistan Super League",
}
