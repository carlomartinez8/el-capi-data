"""
Sync canonical enriched players → Supabase warehouse tables.

Reads:  data/output/players_canonical.json
Writes: data/output/supabase_seed/
          ├── players.sql
          ├── player_aliases.sql
          ├── player_career.sql
          ├── player_tournament.sql
          └── schema_metadata.sql

Generates INSERT statements ready for Supabase migration or CLI.
Handles all field mapping from nested enriched JSON → flat relational tables.
"""

import json
import math
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT = ROOT / "data" / "output" / "players_canonical.json"
OUTPUT_DIR = ROOT / "data" / "output" / "supabase_seed"


def esc(val) -> str:
    """Escape a value for SQL. Returns 'NULL' for None/empty/NaN/inf."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, list):
        if not val:
            return "'{}'"
        # Array of strings
        items = []
        for v in val:
            if isinstance(v, dict):
                items.append(json.dumps(v, ensure_ascii=False).replace("'", "''"))
            else:
                items.append(str(v).replace("'", "''"))
        return "ARRAY[" + ",".join(f"'{i}'" for i in items) + "]"
    if isinstance(val, dict):
        return "'" + json.dumps(val, ensure_ascii=False).replace("'", "''") + "'::jsonb"
    s = str(val).replace("'", "''")
    if not s.strip() or s.strip().lower() in ("nan", "inf", "-inf"):
        return "NULL"
    return f"'{s}'"


def esc_text_array(val) -> str:
    """Escape a TEXT[] value."""
    if not val or not isinstance(val, list):
        return "'{}'"
    items = [str(v).replace("'", "''") if isinstance(v, str) else json.dumps(v, ensure_ascii=False).replace("'", "''") for v in val]
    return "ARRAY[" + ",".join(f"'{i}'" for i in items) + "]::text[]"


def esc_jsonb(val) -> str:
    """Escape a value for JSONB column (list or dict → jsonb)."""
    if val is None:
        return "NULL"
    if isinstance(val, list) or isinstance(val, dict):
        return "'" + json.dumps(val, ensure_ascii=False).replace("'", "''") + "'::jsonb"
    return "'" + json.dumps(val, ensure_ascii=False).replace("'", "''") + "'::jsonb"


def parse_value_eur(market: dict) -> str:
    """Parse market value to bigint EUR."""
    val = market.get("estimated_value_eur") or market.get("market_value")
    if not val:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(int(val))
    # Try to parse strings like "€30M", "30 million", etc.
    s = str(val).lower().replace("€", "").replace("$", "").replace(",", "").strip()
    multiplier = 1
    if "million" in s or "m" in s:
        multiplier = 1_000_000
        s = re.sub(r"(million|m)", "", s).strip()
    elif "billion" in s or "b" in s:
        multiplier = 1_000_000_000
        s = re.sub(r"(billion|b)", "", s).strip()
    try:
        return str(int(float(s) * multiplier))
    except (ValueError, TypeError):
        return "NULL"


NATIONALITY_NORMALIZE = {
    "Curacao": "Curaçao",
    "Cote d'Ivoire": "Côte d'Ivoire",
    "Cote d\u2019Ivoire": "Côte d'Ivoire",
    "Ivory Coast": "Côte d'Ivoire",
    "USA": "United States",
    "United States of America": "United States",
}


def normalize_nationality(val):
    """Normalize nationality variants to a single canonical form."""
    if not val or not isinstance(val, str):
        return val
    return NATIONALITY_NORMALIZE.get(val, val)


def normalize_preferred_foot(val):
    """Normalize to DB constraint: 'Left', 'Right', 'Both'."""
    if val is None:
        return None
    s = str(val).strip().lower()
    if s == "left":
        return "Left"
    if s == "right":
        return "Right"
    if s == "both":
        return "Both"
    return None


def generate_sql():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading canonical data from {INPUT}")
    with open(INPUT) as f:
        players = json.load(f)
    print(f"Loaded {len(players)} canonical players")

    players_sql = []
    aliases_sql = []
    career_sql = []
    tournament_sql = []

    for p in players:
        cid = p["canonical_id"]
        ident = p.get("identity", {})

        # Normalize nationality and birth_country before SQL generation
        if ident.get("nationality_primary"):
            ident["nationality_primary"] = normalize_nationality(ident["nationality_primary"])
        if ident.get("nationality_secondary"):
            ident["nationality_secondary"] = normalize_nationality(ident["nationality_secondary"])
        if ident.get("birth_country"):
            ident["birth_country"] = normalize_nationality(ident["birth_country"])
        story = p.get("story", {})
        personality = p.get("personality", {})
        career = p.get("career", {})
        style = p.get("playing_style", {})
        wc = p.get("world_cup_2026", {})
        bgd = p.get("big_game_dna", {})
        market = p.get("market", {})
        meta = p.get("meta", {})
        injury = p.get("injury_history", {})

        # ─── PLAYERS TABLE ────────────────────────────────────
        players_sql.append(f"""INSERT INTO players (
    id, full_legal_name, known_as, date_of_birth, birth_city, birth_country,
    height_cm, preferred_foot, nationality_primary, nationality_secondary,
    languages_spoken, nicknames,
    origin_story_en, origin_story_es, career_summary_en, career_summary_es,
    breakthrough_moment, career_defining_quote, famous_quote_about, biggest_controversy,
    celebration_style, off_field_interests, charitable_work, superstitions,
    tattoo_meanings, fun_facts, social_media, music_taste, fashion_brands,
    injury_prone, notable_injuries, photo_url,
    data_confidence, data_gaps, enriched_at
) VALUES (
    '{cid}', {esc(ident.get('full_legal_name') or p.get('name'))}, {esc(ident.get('known_as') or p.get('name'))},
    {esc(ident.get('date_of_birth'))}, {esc(ident.get('birth_city'))}, {esc(ident.get('birth_country'))},
    {esc(ident.get('height_cm'))}, {esc(normalize_preferred_foot(ident.get('preferred_foot') or ident.get('foot')))},
    {esc(ident.get('nationality_primary') or 'Unknown')}, {esc(ident.get('nationality_secondary'))},
    {esc_text_array(ident.get('languages_spoken'))}, {esc_jsonb(ident.get('nicknames', []))},
    {esc(story.get('origin_story_en'))}, {esc(story.get('origin_story_es'))},
    {esc(story.get('career_summary_en'))}, {esc(story.get('career_summary_es'))},
    {esc(story.get('breakthrough_moment'))}, {esc(story.get('career_defining_quote_by_player') or story.get('career_defining_quote'))},
    {esc(story.get('famous_quote_about_player') or story.get('famous_quote_about'))}, {esc(story.get('biggest_controversy'))},
    {esc(personality.get('celebration_style'))},
    {esc_text_array(personality.get('off_field_interests'))},
    {esc(personality.get('charitable_work'))},
    {esc_text_array(personality.get('superstitions_rituals') or personality.get('superstitions'))},
    {esc_text_array(personality.get('tattoo_meanings'))},
    {esc_text_array(personality.get('fun_facts'))},
    {esc(personality.get('social_media', {}))},
    {esc(personality.get('music_taste'))}, {esc(personality.get('fashion_brands'))},
    {esc(injury.get('injury_prone'))}, {esc_jsonb(injury.get('notable_injuries', []))},
    {esc(ident.get('photo_url'))},
    {esc(meta.get('data_confidence'))}, {esc_text_array(meta.get('data_gaps'))},
    {esc(p.get('enriched_at'))}
) ON CONFLICT (id) DO NOTHING;""")

        # ─── ALIASES ─────────────────────────────────────────
        source_id = p.get("source_id")
        if source_id:
            aliases_sql.append(
                f"INSERT INTO player_aliases (player_id, alias_type, alias_value) "
                f"VALUES ('{cid}', 'transfermarkt_id', '{source_id}') ON CONFLICT DO NOTHING;"
            )
        known_as = ident.get("known_as", "")
        full_name = ident.get("full_legal_name", "")
        if known_as and known_as != full_name:
            aliases_sql.append(
                f"INSERT INTO player_aliases (player_id, alias_type, alias_value) "
                f"VALUES ('{cid}', 'alternate_name', {esc(known_as)}) ON CONFLICT DO NOTHING;"
            )
        for nick in ident.get("nicknames", []):
            nick_str = nick if isinstance(nick, str) else nick.get("nickname", "") if isinstance(nick, dict) else ""
            if nick_str:
                aliases_sql.append(
                    f"INSERT INTO player_aliases (player_id, alias_type, alias_value) "
                    f"VALUES ('{cid}', 'nickname', {esc(nick_str)}) ON CONFLICT DO NOTHING;"
                )

        # ─── CAREER TABLE ─────────────────────────────────────
        career_sql.append(f"""INSERT INTO player_career (
    player_id, current_club, current_league, current_jersey_number,
    position_primary, position_secondary, contract_expires, agent,
    estimated_value_eur, endorsement_brands,
    career_trajectory, major_trophies, records_held,
    style_summary_en, style_summary_es, signature_moves,
    strengths, weaknesses, comparable_to, best_partnership,
    refresh_source
) VALUES (
    '{cid}', {esc(career.get('current_club'))}, {esc(career.get('current_league'))},
    {esc(career.get('current_jersey_number'))},
    {esc(career.get('position_primary'))}, {esc(career.get('position_secondary'))},
    {esc(career.get('contract_expires'))}, {esc(career.get('agent'))},
    {parse_value_eur(market)}, {esc_text_array(market.get('endorsement_brands'))},
    {esc_jsonb(career.get('career_trajectory', []))},
    {esc_text_array(career.get('major_trophies'))}, {esc_text_array(career.get('records_held'))},
    {esc(style.get('style_summary_en'))}, {esc(style.get('style_summary_es'))},
    {esc_text_array(style.get('signature_moves'))},
    {esc_text_array(style.get('strengths'))}, {esc_text_array(style.get('weaknesses'))},
    {esc(style.get('comparable_to'))}, {esc(style.get('best_partnership'))},
    'enrichment_v1'
) ON CONFLICT (player_id) DO NOTHING;""")

        # ─── TOURNAMENT TABLE ─────────────────────────────────
        tournament_sql.append(f"""INSERT INTO player_tournament (
    player_id, wc_team_code, jersey_number, captain, in_squad,
    international_caps, international_goals, international_debut,
    tournament_role_en, tournament_role_es,
    narrative_arc_en, narrative_arc_es,
    injury_fitness_status, wc_qualifying_contribution,
    world_cup_goals, champions_league_goals,
    derby_performances_en, derby_performances_es,
    clutch_moments, previous_wc_appearances, host_city_connection
) VALUES (
    '{cid}', {esc(p.get('wc_team_code'))},
    {esc(wc.get('jersey_number'))}, {esc(wc.get('captain', False))}, TRUE,
    {esc(career.get('international_caps'))}, {esc(career.get('international_goals'))},
    {esc(career.get('international_debut'))},
    {esc(wc.get('tournament_role_en'))}, {esc(wc.get('tournament_role_es'))},
    {esc(wc.get('narrative_arc_en'))}, {esc(wc.get('narrative_arc_es'))},
    {esc(wc.get('injury_fitness_status'))}, {esc(wc.get('wc_qualifying_contribution'))},
    {esc(bgd.get('world_cup_goals', 0))}, {esc(bgd.get('champions_league_goals', 0))},
    {esc(bgd.get('derby_performances_en'))}, {esc(bgd.get('derby_performances_es'))},
    {esc_jsonb(bgd.get('clutch_moments', []))},
    {esc_jsonb(wc.get('previous_wc_appearances', []))}, {esc(wc.get('host_city_connection'))}
) ON CONFLICT (player_id) DO NOTHING;""")

    # ─── Write SQL files ──────────────────────────────────────────
    write_sql(OUTPUT_DIR / "players.sql", players_sql, "players")
    write_sql(OUTPUT_DIR / "player_aliases.sql", aliases_sql, "player_aliases")
    write_sql(OUTPUT_DIR / "player_career.sql", career_sql, "player_career")
    write_sql(OUTPUT_DIR / "player_tournament.sql", tournament_sql, "player_tournament")

    # ─── Schema Metadata ──────────────────────────────────────────
    generate_schema_metadata(OUTPUT_DIR / "schema_metadata.sql")

    print(f"\n{'='*50}")
    print("SYNC SQL GENERATED")
    print(f"{'='*50}")
    print(f"Players:    {len(players_sql)} inserts")
    print(f"Aliases:    {len(aliases_sql)} inserts")
    print(f"Career:     {len(career_sql)} inserts")
    print(f"Tournament: {len(tournament_sql)} inserts")
    print(f"Output dir: {OUTPUT_DIR}")


def write_sql(path: Path, statements: list[str], table_name: str):
    """Write SQL seed file with TRUNCATE to ensure clean slate."""
    with open(path, "w") as f:
        f.write(f"-- {table_name} seed data (pipeline v2 — clean replace)\n")
        f.write(f"-- Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"-- Records: {len(statements)}\n")
        f.write(f"-- NOTE: TRUNCATE ensures old data is removed before insert.\n\n")
        f.write("BEGIN;\n\n")

        # ── TRUNCATE old data first ──
        # Order matters for FK constraints: child tables must be truncated
        # before parent tables, or use CASCADE.
        if table_name == "players":
            # Players is the parent — CASCADE removes dependent rows in
            # player_career, player_tournament, player_aliases.
            # So players.sql MUST be loaded FIRST.
            f.write(f"TRUNCATE TABLE {table_name} CASCADE;\n\n")
        else:
            f.write(f"TRUNCATE TABLE {table_name};\n\n")

        for stmt in statements:
            f.write(stmt + "\n\n")
        f.write("COMMIT;\n")
    print(f"  Wrote {path.name} ({len(statements)} records)")


def generate_schema_metadata(path: Path):
    """Seed schema_metadata with field descriptions for Capi Analytics Mode."""
    rows = [
        # ── PLAYERS TABLE (static identity) ──
        ("players", "full_legal_name", "Player's full legal name", "Nombre legal completo del jugador", "text", "Lionel Andrés Messi Cuccittini", True, True, False, None, None, "identity", "static"),
        ("players", "known_as", "How the player is commonly known", "Nombre por el que se conoce al jugador", "text", "Messi", True, True, False, None, None, "identity", "static"),
        ("players", "date_of_birth", "Date of birth", "Fecha de nacimiento", "date", "1987-06-24", True, True, True, "Calculate age, compare generations", "date", "identity", "static"),
        ("players", "height_cm", "Height in centimeters", "Altura en centímetros", "integer", "170", True, True, True, "Compare across teams/positions, average by team", "cm", "identity", "static"),
        ("players", "preferred_foot", "Dominant foot", "Pie dominante", "text", "Left", True, False, True, "Count left vs right footers by team", None, "identity", "static"),
        ("players", "nationality_primary", "Primary nationality", "Nacionalidad principal", "text", "Argentina", True, True, True, "Count players by nationality, multi-national squads", None, "identity", "static"),
        ("players", "data_confidence", "Data quality level (high/medium/low)", "Nivel de calidad de datos (alto/medio/bajo)", "text", "high", True, False, True, "Filter by data reliability", None, "identity", "static"),
        # ── PLAYER_CAREER TABLE (semi-static) ──
        ("player_career", "current_club", "Current club team", "Equipo actual", "text", "Inter Miami CF", True, True, True, "Count WC players per club, club representation", None, "career", "semi_static"),
        ("player_career", "current_league", "Current domestic league", "Liga doméstica actual", "text", "MLS", True, True, True, "Which leagues produce most WC players", None, "career", "semi_static"),
        ("player_career", "position_primary", "Primary playing position", "Posición principal", "text", "Forward", True, True, True, "Position distribution per team, compare by position", None, "career", "semi_static"),
        ("player_career", "estimated_value_eur", "Estimated market value in EUR", "Valor de mercado estimado en EUR", "bigint", "50000000", True, True, True, "Compare squad values, most/least expensive players, value by position", "EUR", "market", "semi_static"),
        ("player_career", "major_trophies", "List of major career trophies", "Lista de trofeos importantes", "text[]", "Champions League 2023", False, False, True, "Count trophies per player, most decorated squads", None, "career", "semi_static"),
        ("player_career", "strengths", "Playing strengths", "Fortalezas de juego", "text[]", "Dribbling", True, False, False, None, None, "style", "semi_static"),
        ("player_career", "weaknesses", "Playing weaknesses", "Debilidades de juego", "text[]", "Aerial duels", True, False, False, None, None, "style", "semi_static"),
        ("player_career", "comparable_to", "Comparable playing style to another player", "Estilo de juego comparable a otro jugador", "text", "Zinedine Zidane", True, False, False, None, None, "style", "semi_static"),
        # ── PLAYER_TOURNAMENT TABLE (dynamic) ──
        ("player_tournament", "wc_team_code", "World Cup team FIFA code", "Código FIFA del equipo", "text", "ARG", True, True, True, "Group by team, cross-team comparisons", None, "tournament", "dynamic"),
        ("player_tournament", "jersey_number", "Squad jersey number", "Número de camiseta", "integer", "10", True, True, False, None, None, "tournament", "dynamic"),
        ("player_tournament", "captain", "Is team captain", "Es capitán del equipo", "boolean", "true", True, False, True, "Find all captains", None, "tournament", "dynamic"),
        ("player_tournament", "international_caps", "Total international appearances", "Total de partidos internacionales", "integer", "180", True, True, True, "Most experienced players, experience by team", "caps", "tournament", "dynamic"),
        ("player_tournament", "international_goals", "Total international goals", "Total de goles internacionales", "integer", "106", True, True, True, "Top scorers, goals-per-cap ratio", "goals", "tournament", "dynamic"),
        ("player_tournament", "world_cup_goals", "Career World Cup goals", "Goles en Copa del Mundo", "integer", "13", True, True, True, "All-time WC scorers, team WC goal potential", "goals", "tournament", "dynamic"),
        ("player_tournament", "champions_league_goals", "Career Champions League goals", "Goles en Champions League", "integer", "129", True, True, True, "Big-game pedigree, CL experience", "goals", "tournament", "dynamic"),
    ]

    with open(path, "w") as f:
        f.write("-- schema_metadata seed data for Capi Analytics Mode\n")
        f.write(f"-- Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"-- Records: {len(rows)}\n\n")
        f.write("BEGIN;\n\n")
        for (tbl, col, desc_en, desc_es, dtype, example, filt, sort, agg, hint, unit, cat, vol) in rows:
            f.write(f"""INSERT INTO schema_metadata (
    table_name, column_name, description_en, description_es,
    data_type, example_value, is_filterable, is_sortable, is_aggregatable,
    analytics_hint, unit, category, volatility
) VALUES (
    '{tbl}', '{col}', {esc(desc_en)}, {esc(desc_es)},
    '{dtype}', {esc(example)}, {str(filt).upper()}, {str(sort).upper()}, {str(agg).upper()},
    {esc(hint)}, {esc(unit)}, '{cat}', '{vol}'
) ON CONFLICT (table_name, column_name) DO NOTHING;\n\n""")
        f.write("COMMIT;\n")

    print(f"  Wrote schema_metadata.sql ({len(rows)} records)")


if __name__ == "__main__":
    generate_sql()
