# Data Schema Reference

Complete field reference for the enriched player data and Supabase warehouse tables.

---

## Enriched Player JSON Schema

Each player in `players_canonical.json` has the following structure. This is what gpt-4o-mini generates during enrichment and what gpt-4o verifies.

### Top-Level Fields

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `canonical_id` | UUID | canonical.py | Stable unique ID across pipeline runs |
| `source_id` | string | Pipeline | Transfermarkt player ID or static squad ID |
| `name` | string | Pipeline | Display name |
| `wc_team_code` | string | Static squads | 3-letter FIFA team code (e.g. `ARG`, `USA`) |
| `enriched_at` | ISO datetime | Enrichment | When this player was enriched |
| `dedup_key` | string | canonical.py | Key used for deduplication |
| `dedup_key_type` | string | canonical.py | `"primary"` (surname+DOB+team) or `"fallback"` (name+team+club) |

### `identity` — Who They Are

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `full_legal_name` | string | `"Lionel Andrés Messi Cuccittini"` | Full legal name as on passport |
| `known_as` | string | `"Lionel Messi"` | Common name used in media |
| `nicknames` | string[] | `["La Pulga", "The GOAT"]` | Popular nicknames |
| `date_of_birth` | string | `"1987-06-24"` | ISO date format |
| `birth_city` | string | `"Rosario"` | City of birth |
| `birth_country` | string | `"Argentina"` | Country of birth |
| `nationality_primary` | string | `"Argentina"` | Primary nationality (for WC) |
| `nationality_secondary` | string | `"Spain"` | Secondary nationality (if dual) |
| `languages_spoken` | string[] | `["Spanish", "Catalan"]` | Languages |
| `height_cm` | integer | `170` | Height in centimeters |
| `preferred_foot` | string | `"Left"` | `"Left"`, `"Right"`, or `"Both"` |

### `career` — What They Do

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `current_club` | string | `"Inter Miami CF"` | Current club team |
| `current_league` | string | `"MLS"` | Current domestic league |
| `current_jersey_number` | string/int | `10` | Current jersey number |
| `position_primary` | string | `"Right Winger"` | Primary position |
| `position_secondary` | string | `"Attacking Midfielder"` | Secondary position |
| `career_trajectory` | object[] | `[{"year": "2004-2021", "club": "FC Barcelona", ...}]` | Career timeline |
| `international_caps` | integer | `180` | Total international appearances |
| `international_goals` | integer | `106` | Total international goals |
| `international_debut` | string | `"2005-08-17"` | Date of international debut |
| `records_held` | string[] | `["All-time top scorer for Argentina"]` | Records |
| `major_trophies` | string[] | `["World Cup 2022", "Copa América 2021"]` | Trophy list |
| `contract_expires` | string | `"December 2025"` | Contract expiration |

### `playing_style` — How They Play

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `style_summary_en` | string | `"A creative genius who..."` | English narrative (~100 words) |
| `style_summary_es` | string | `"Un genio creativo que..."` | Spanish narrative (~100 words) |
| `signature_moves` | string[] | `["La croqueta", "Nutmeg"]` | Trademark moves |
| `strengths` | string[] | `["Dribbling", "Vision", "Free kicks"]` | Key strengths |
| `weaknesses` | string[] | `["Aerial duels", "Defensive work rate"]` | Known weaknesses |
| `comparable_to` | string | `"Diego Maradona"` | Style comparison |
| `best_partnership` | string | `"Neymar at Barcelona (2014-2017)"` | Best partnership in career |

### `story` — Their Journey

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `origin_story_en` | string | `"Born in Rosario, diagnosed with..."` | English origin story (~150 words) |
| `origin_story_es` | string | `"Nacido en Rosario, diagnosticado con..."` | Spanish origin story (~150 words) |
| `career_summary_en` | string | `"The greatest player of..."` | English career summary |
| `career_summary_es` | string | `"El mejor jugador de..."` | Spanish career summary |
| `breakthrough_moment` | string | `"His debut goal vs Albacete in 2005..."` | Defining early career moment |
| `career_defining_quote_by_player` | string | `"You have to fight to reach your dream."` | Quote by the player |
| `famous_quote_about_player` | string | `"I have seen the player who will inherit my place." — Maradona` | Quote about them |
| `biggest_controversy` | string | `"Tax fraud conviction in Spain (2017)"` | Most notable controversy |

### `personality` — Who They Are Off the Pitch

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `celebration_style` | string | `"Points to the sky, dedicated to grandmother"` | Goal celebration |
| `superstitions_rituals` | string[] | `["Always enters pitch right foot first"]` | Pre-match rituals |
| `off_field_interests` | string[] | `["Fashion", "Mate drinking", "Dogs"]` | Hobbies/interests |
| `charitable_work` | string | `"Leo Messi Foundation — children's healthcare"` | Charity involvement |
| `tattoo_meanings` | string[] | `["Son's name on calf", "Rose window on arm"]` | Tattoo descriptions |
| `fun_facts` | string[] | `["Ate asado before every match at Barcelona"]` | Interesting trivia |
| `social_media` | object | `{"instagram": "@leomessi", "followers": "500M"}` | Social media presence |
| `music_taste` | string | `"Cumbia and reggaeton"` | Music preferences |
| `fashion_brands` | string | `"Adidas, The Messi Brand"` | Fashion affiliations |

### `world_cup_2026` — Tournament-Specific

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `previous_wc_appearances` | object[] | `[{"year": 2022, "result": "Winner"}]` | Past WC participation |
| `wc_qualifying_contribution` | string | `"7 goals in CONMEBOL qualifying"` | Qualifying stats |
| `tournament_role_en` | string | `"The talisman seeking a farewell trophy"` | English role narrative |
| `tournament_role_es` | string | `"El talismán que busca un trofeo de despedida"` | Spanish role narrative |
| `narrative_arc_en` | string | `"His last dance — can he defend the title?"` | English story arc |
| `narrative_arc_es` | string | `"Su última danza — ¿puede defender el título?"` | Spanish story arc |
| `host_city_connection` | string | `"Played in Miami since 2023"` | Connection to host cities |
| `injury_fitness_status` | string | `"Fully fit, managing minutes carefully"` | Current fitness |
| `jersey_number` | integer | `10` | WC squad number |
| `captain` | boolean | `true` | Team captain status |

### `big_game_dna` — Performance Under Pressure

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `world_cup_goals` | integer | `13` | Career WC goals |
| `champions_league_goals` | integer | `129` | Career UCL goals |
| `derby_performances_en` | string | `"26 goals in El Clásico"` | English derby stats |
| `derby_performances_es` | string | `"26 goles en El Clásico"` | Spanish derby stats |
| `clutch_moments` | object[] | `[{"match": "WC Final 2022", "moment": "Two goals in 97 seconds"}]` | Defining big-game moments |

### `market` — Business Side

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `estimated_value_eur` | string | `"€30M"` | Current market value |
| `endorsement_brands` | string[] | `["Adidas", "Pepsi", "Budweiser"]` | Brand deals |
| `agent` | string | `"Jorge Messi (father)"` | Agent/representative |

### `injury_history` — Physical Record

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `notable_injuries` | string[]/object[] | `["Knee ligament (2006)"]` | Major injuries |
| `injury_prone` | boolean | `false` | Generally injury prone? |

### `meta` — Data Quality

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `data_confidence` | string | `"high"` | `"high"`, `"medium"`, or `"low"` |
| `data_gaps` | string[] | `["endorsement_brands may be incomplete"]` | Known gaps |

---

## Supabase Warehouse Tables

The enriched JSON is flattened into 4 normalized PostgreSQL tables. Schema defined in `la-copa-mundo/supabase/migrations/20260312_player_warehouse.sql`.

### `players` — Identity & Story (Static)

Core identity data that rarely changes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | uuid | PK | = canonical_id from pipeline |
| `full_legal_name` | text | no | Full legal name |
| `known_as` | text | no | Common display name |
| `date_of_birth` | date | yes | ISO date |
| `birth_city` | text | yes | City of birth |
| `birth_country` | text | yes | Country of birth |
| `height_cm` | integer | yes | Height in cm |
| `preferred_foot` | text | yes | Left/Right/Both |
| `nationality_primary` | text | no (default 'Unknown') | Primary nationality |
| `nationality_secondary` | text | yes | Dual nationality |
| `languages_spoken` | text[] | yes | Languages spoken |
| `nicknames` | text[] | yes | Nicknames |
| `origin_story_en` | text | yes | English origin story |
| `origin_story_es` | text | yes | Spanish origin story |
| `career_summary_en` | text | yes | English career summary |
| `career_summary_es` | text | yes | Spanish career summary |
| `breakthrough_moment` | text | yes | Defining early moment |
| `career_defining_quote` | text | yes | Quote by player |
| `famous_quote_about` | text | yes | Quote about player |
| `biggest_controversy` | text | yes | Notable controversy |
| `celebration_style` | text | yes | Goal celebration |
| `off_field_interests` | text[] | yes | Hobbies |
| `charitable_work` | text | yes | Charity work |
| `superstitions` | text[] | yes | Pre-match rituals |
| `tattoo_meanings` | text[] | yes | Tattoo descriptions |
| `fun_facts` | text[] | yes | Trivia |
| `social_media` | text | yes | JSON string of social accounts |
| `music_taste` | text | yes | Music preferences |
| `fashion_brands` | text | yes | Fashion affiliations |
| `injury_prone` | boolean | yes | Injury prone flag |
| `notable_injuries` | text[] | yes | Major injuries |
| `photo_url` | text | yes | Player photo URL |
| `name_search` | text | generated | Lowercase search index |
| `data_confidence` | text | yes | high/medium/low |
| `data_gaps` | text[] | yes | Known data gaps |
| `enriched_at` | timestamptz | yes | When enriched |
| `created_at` | timestamptz | auto | Row creation time |
| `updated_at` | timestamptz | auto | Last update time |

**Indexes**: `name_search` (GIN trigram)

### `player_career` — Club & Style (Semi-Static)

Career data that changes when players transfer or evolve.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | uuid | PK (auto) | Row ID |
| `player_id` | uuid | FK → players.id | Player reference |
| `current_club` | text | yes | Current club |
| `current_league` | text | yes | Current league |
| `current_jersey_number` | text | yes | Jersey number |
| `position_primary` | text | yes | Primary position |
| `position_secondary` | text | yes | Secondary position |
| `contract_expires` | date | yes | Contract end date |
| `agent` | text | yes | Agent name |
| `estimated_value_eur` | bigint | yes | Market value in EUR |
| `endorsement_brands` | text[] | yes | Brand deals |
| `career_trajectory` | jsonb | yes | Career timeline |
| `major_trophies` | text[] | yes | Trophy list |
| `records_held` | text[] | yes | Records held |
| `style_summary_en` | text | yes | English style narrative |
| `style_summary_es` | text | yes | Spanish style narrative |
| `signature_moves` | text[] | yes | Trademark moves |
| `strengths` | text[] | yes | Playing strengths |
| `weaknesses` | text[] | yes | Playing weaknesses |
| `comparable_to` | text | yes | Style comparison |
| `best_partnership` | text | yes | Best partnership |
| `refresh_source` | text | yes | Last data source |
| `refreshed_at` | timestamptz | auto | Last refresh |

**Unique constraint**: `player_id`

### `player_tournament` — WC 2026 (Dynamic)

World Cup-specific data that changes during the tournament.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | uuid | PK (auto) | Row ID |
| `player_id` | uuid | FK → players.id | Player reference |
| `wc_team_code` | text | yes | 3-letter FIFA code |
| `jersey_number` | integer | yes | Squad number |
| `captain` | boolean | default false | Captain flag |
| `in_squad` | boolean | default true | In final squad |
| `international_caps` | integer | yes | Total caps |
| `international_goals` | integer | yes | Total goals |
| `international_debut` | text | yes | Debut date |
| `tournament_role_en` | text | yes | English role narrative |
| `tournament_role_es` | text | yes | Spanish role narrative |
| `narrative_arc_en` | text | yes | English story arc |
| `narrative_arc_es` | text | yes | Spanish story arc |
| `injury_fitness_status` | text | yes | Current fitness |
| `wc_qualifying_contribution` | text | yes | Qualifying stats |
| `world_cup_goals` | integer | default 0 | Career WC goals |
| `champions_league_goals` | integer | default 0 | Career UCL goals |
| `derby_performances_en` | text | yes | English derby stats |
| `derby_performances_es` | text | yes | Spanish derby stats |
| `clutch_moments` | jsonb | yes | Big-game moments |
| `previous_wc_appearances` | jsonb | yes | Past WC record |
| `host_city_connection` | text | yes | Host city ties |

**Unique constraint**: `player_id`

### `player_aliases` — Cross-Source Linking

Maps players to external IDs and alternate names.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | uuid | PK (auto) | Row ID |
| `player_id` | uuid | FK → players.id | Player reference |
| `alias_type` | text | no | `transfermarkt_id`, `alternate_name`, `nickname` |
| `alias_value` | text | no | The alias value |
| `created_at` | timestamptz | auto | Row creation time |

**Unique constraint**: `(player_id, alias_type, alias_value)`

### `schema_metadata` — Capi Analytics Discovery

Describes queryable columns for Capi's Analytics Mode SQL generation.

| Column | Type | Description |
|--------|------|-------------|
| `table_name` | text | Table this column belongs to |
| `column_name` | text | Column name |
| `description_en` | text | English description |
| `description_es` | text | Spanish description |
| `data_type` | text | PostgreSQL type |
| `example_value` | text | Example value |
| `is_filterable` | boolean | Can use in WHERE |
| `is_sortable` | boolean | Can use in ORDER BY |
| `is_aggregatable` | boolean | Can use in COUNT/AVG/SUM |
| `analytics_hint` | text | Hint for AI on how to use |
| `unit` | text | Unit (cm, EUR, caps, etc.) |
| `category` | text | Grouping (identity, career, market, tournament, style) |
| `volatility` | text | How often it changes (static, semi_static, dynamic) |

**Unique constraint**: `(table_name, column_name)`

---

## Table Relationships

```
players (id)
  ├── player_career (player_id → players.id)     1:1
  ├── player_tournament (player_id → players.id)  1:1
  └── player_aliases (player_id → players.id)     1:many

teams (id)
  └── player_tournament.wc_team_code → teams.code (logical, not FK)
```

### Common Queries

```sql
-- Full player profile
SELECT p.*, pc.*, pt.*
FROM players p
JOIN player_career pc ON pc.player_id = p.id
JOIN player_tournament pt ON pt.player_id = p.id
WHERE p.known_as ILIKE '%messi%';

-- Most valuable squad
SELECT pt.wc_team_code, SUM(pc.estimated_value_eur) as total_value
FROM player_tournament pt
JOIN player_career pc ON pc.player_id = pt.player_id
GROUP BY pt.wc_team_code
ORDER BY total_value DESC;

-- Players by league
SELECT pc.current_league, COUNT(*) as player_count
FROM player_career pc
JOIN player_tournament pt ON pt.player_id = pc.player_id
GROUP BY pc.current_league
ORDER BY player_count DESC;

-- Team roster with details
SELECT p.known_as, pc.position_primary, pc.current_club, pt.jersey_number, pt.captain
FROM players p
JOIN player_career pc ON pc.player_id = p.id
JOIN player_tournament pt ON pt.player_id = p.id
WHERE pt.wc_team_code = 'ARG'
ORDER BY pt.jersey_number;
```

---

## Data Flow Summary

```
Source Data                  Enriched JSON                 Supabase Tables
─────────────               ──────────────                ───────────────
name, DOB, nationality  →   identity.*              →     players
club, position, value   →   career.*, playing_style.*  →  player_career
team, jersey, caps      →   world_cup_2026.*, big_game_dna.*  →  player_tournament
source_id, nicknames    →   (derived)               →     player_aliases
```
