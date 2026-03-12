# Pipeline Migration Strategy — Static vs Dynamic Data Architecture

**Author:** Carlo + Claude
**Date:** March 11, 2026
**Status:** DRAFT — awaiting review before implementation

---

## 1. Current State Assessment

### What We Have

**632 enriched players** across 42 World Cup teams, with a rich nested schema produced by the AI enrichment pipeline. The data lives in `data/output/players_enriched.json` and has never been synced to Supabase.

**Supabase already has** a legacy `pipeline_players` table (flat structure from Transfermarkt/API-Football ingestion) plus supporting tables (`player_bios`, `transfers`, `player_valuations`, `appearances`, `active_matches`). Capi's tools currently query these legacy tables.

### Problems to Solve

**Dedup logic is flawed in two places:**

1. **Python pipeline dedup** (`pipeline/dedup/resolver.py`): Merges Transfermarkt + static_squad via fuzzy name matching with thresholds (85 auto-merge, 70 review). The result? Every team has only 12-19 players instead of the expected 23-26. Either the source data was incomplete or the matching was too aggressive — players in the review zone (70-84) get added as NEW rows rather than merged, inflating count while leaving the real player unlinked.

2. **Runtime dedup in Capi's tools** (`src/lib/capi/tools.ts`): Uses `first-initial + surname` as a dedup key at query time. This is dangerously fragile — "L. Martínez" from Argentina and "L. Martínez" from Mexico would incorrectly merge. It also does three separate Supabase queries per search (exact, broad, APIF-targeted) and deduplicates client-side, which is wasteful.

**Schema mismatch:** The enriched JSON has a deeply nested bilingual structure (`identity.full_legal_name`, `story.origin_story_en`, `playing_style.style_summary_es`), while `pipeline_players` is a flat single-language table from web scraping. These are fundamentally different data models.

**No canonical identity:** Players are identified by `source_id` (Transfermarkt ID) with no stable UUID. Cross-source linking relies entirely on runtime fuzzy matching.

---

## 2. Dedup Strategy — Getting to a Production Canonical Dataset

### Step 1: Define the Canonical Identity

Each player gets a **stable UUID** (`canonical_id`) that never changes. The identity is established by a composite key:

```
DEDUP KEY = normalized_surname + date_of_birth + wc_team_code
```

Why this triple:
- **Surname + DOB** eliminates 99% of ambiguity (there won't be two "Martínez" born on the same day on the same WC team)
- **wc_team_code** is the partition — we only care about WC players for this app
- If DOB is missing, fall back to: `normalized_full_name + wc_team_code + current_club`

### Step 2: Dedup Profiles to Validate

Before coding, manually verify the dedup logic against these edge-case profiles:

| Profile | Challenge | Expected Resolution |
|---------|-----------|-------------------|
| **James Rodríguez** (COL) | Known as "James", full name "James David Rodríguez Rubio" | Match on surname "rodriguez" + DOB |
| **Son Heung-min** (KOR) | East Asian name order (family name first) | Normalize: detect + handle name order |
| **Neymar Jr** (BRA) | Single-name player with suffix | Strip "Jr", match on "neymar" + DOB |
| **Two L. Martínez** (ARG) | Lisandro Martínez & Lautaro Martínez, same team | DOB differentiates them |
| **Alphonso Davies** (CAN) | May appear with different club mid-transfer | Club is NOT part of primary key |
| **Players with no DOB** | ~133 low-confidence players missing DOB | Fall back to full_name + team + club |
| **Name transliteration** | Arabic/Japanese names with multiple romanizations | Normalize with unidecode + manual alias table |

### Step 3: Build the Alias Table

```
player_aliases:
  canonical_id  UUID  FK → players.id
  alias_type    TEXT  ('transfermarkt_id', 'apif_id', 'wikipedia_slug', 'alternate_name')
  alias_value   TEXT
  UNIQUE(alias_type, alias_value)
```

This lets us link any source to any player without re-running dedup. When a new source says "J. Rodríguez", we check aliases first, fuzzy match second.

---

## 3. Static vs Dynamic Field Taxonomy

### STATIC — Set once, immutable forever

These fields describe WHO a player IS. They don't change during the tournament (or ever). Written once during enrichment, never updated by recurring pipelines.

```
identity:
  canonical_id          UUID (PK, generated)
  full_legal_name       TEXT
  known_as              TEXT
  date_of_birth         DATE
  birth_city            TEXT
  birth_country         TEXT
  height_cm             INT
  preferred_foot        TEXT ('Left', 'Right', 'Both')
  nationality_primary   TEXT
  nationality_secondary TEXT
  languages_spoken      TEXT[]

story:
  origin_story_en       TEXT
  origin_story_es       TEXT
  breakthrough_moment   JSONB  {description_en, description_es, date}
  career_defining_quote JSONB  {quote_en, quote_es, context}
  famous_quote_about    JSONB  {quote_en, quote_es, attributed_to}
  biggest_controversy   JSONB  {description_en, description_es}

personality:
  celebration_style     TEXT
  off_field_interests   TEXT[]
  charitable_work       TEXT
  superstitions         TEXT[]
  tattoo_meanings       TEXT[]
  fun_facts             TEXT[]
  social_media          JSONB  {instagram, twitter, tiktok}
```

**Coverage from enrichment:**
- identity fields: 79-99%
- story fields: 77-78%
- personality: 45-55% (lower for lesser-known players)

### SEMI-STATIC — Changes per transfer window (~2x/year)

These fields change when players transfer clubs or their market value updates. Updated by a **seasonal refresh pipeline** (January + August windows, or on-demand).

```
career_current:
  current_club          TEXT
  current_league        TEXT
  current_jersey_number INT
  position_primary      TEXT
  position_secondary    TEXT
  contract_expires      DATE
  agent                 TEXT

market:
  estimated_value_eur   BIGINT
  endorsement_brands    TEXT[]

playing_style:
  style_summary_en      TEXT
  style_summary_es      TEXT
  signature_moves       TEXT[]
  strengths             TEXT[]
  weaknesses            TEXT[]
  comparable_to         TEXT
  best_partnership      TEXT
```

### DYNAMIC — Changes during tournament (daily/hourly)

These fields update as matches happen. Fed by **recurring pipelines** during the World Cup.

```
tournament_live:
  wc_team_code             TEXT
  jersey_number            INT
  captain                  BOOLEAN
  international_caps       INT
  international_goals      INT
  tournament_role_en       TEXT
  tournament_role_es       TEXT
  narrative_arc_en         TEXT
  narrative_arc_es         TEXT
  injury_fitness_status    TEXT
  world_cup_goals          INT
  group_stage_performance  JSONB
  knockout_performances    JSONB[]

career_stats:
  career_trajectory     JSONB[]  (historical, grows over time)
  major_trophies        TEXT[]
  records_held          TEXT[]
```

---

## 4. Target Supabase Schema

### Core Tables

```sql
-- ═══════════════════════════════════════════════════
-- PLAYERS (canonical identity — STATIC)
-- Written once. Never updated by pipelines.
-- ═══════════════════════════════════════════════════
CREATE TABLE players (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Identity
    full_legal_name       TEXT NOT NULL,
    known_as              TEXT NOT NULL,
    date_of_birth         DATE,
    birth_city            TEXT,
    birth_country         TEXT,
    height_cm             INT,
    preferred_foot        TEXT CHECK (preferred_foot IN ('Left', 'Right', 'Both')),
    nationality_primary   TEXT NOT NULL,
    nationality_secondary TEXT,
    languages_spoken      TEXT[],
    -- Story (bilingual)
    origin_story_en       TEXT,
    origin_story_es       TEXT,
    career_summary_en     TEXT,
    career_summary_es     TEXT,
    breakthrough_moment   JSONB,
    career_defining_quote JSONB,
    famous_quote_about    JSONB,
    biggest_controversy   JSONB,
    -- Personality
    celebration_style     TEXT,
    off_field_interests   TEXT[],
    charitable_work       TEXT,
    superstitions         TEXT[],
    tattoo_meanings       TEXT[],
    fun_facts             TEXT[],
    social_media          JSONB,
    -- Photo
    photo_url             TEXT,
    -- Search
    name_search           TEXT GENERATED ALWAYS AS (
      lower(unaccent(full_legal_name || ' ' || known_as))
    ) STORED,
    -- Meta
    data_confidence       TEXT CHECK (data_confidence IN ('high', 'medium', 'low')),
    data_gaps             TEXT[],
    enriched_at           TIMESTAMPTZ,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

-- Full-text search index
CREATE INDEX idx_players_name_search ON players USING gin(to_tsvector('simple', name_search));
CREATE INDEX idx_players_nationality ON players(nationality_primary);

-- ═══════════════════════════════════════════════════
-- PLAYER_ALIASES (cross-source linking)
-- ═══════════════════════════════════════════════════
CREATE TABLE player_aliases (
    id            BIGSERIAL PRIMARY KEY,
    player_id     UUID NOT NULL REFERENCES players(id),
    alias_type    TEXT NOT NULL,
    alias_value   TEXT NOT NULL,
    UNIQUE(alias_type, alias_value)
);

CREATE INDEX idx_aliases_player ON player_aliases(player_id);
CREATE INDEX idx_aliases_lookup ON player_aliases(alias_type, alias_value);

-- ═══════════════════════════════════════════════════
-- PLAYER_CAREER (semi-static — updated per window)
-- ═══════════════════════════════════════════════════
CREATE TABLE player_career (
    player_id             UUID PRIMARY KEY REFERENCES players(id),
    current_club          TEXT,
    current_league        TEXT,
    current_jersey_number INT,
    position_primary      TEXT,
    position_secondary    TEXT,
    contract_expires      DATE,
    agent                 TEXT,
    estimated_value_eur   BIGINT,
    endorsement_brands    TEXT[],
    career_trajectory     JSONB,
    major_trophies        TEXT[],
    records_held          TEXT[],
    -- Playing style
    style_summary_en      TEXT,
    style_summary_es      TEXT,
    signature_moves       TEXT[],
    strengths             TEXT[],
    weaknesses            TEXT[],
    comparable_to         TEXT,
    best_partnership      TEXT,
    -- Refresh tracking
    updated_at            TIMESTAMPTZ DEFAULT NOW(),
    refresh_source        TEXT
);

-- ═══════════════════════════════════════════════════
-- PLAYER_TOURNAMENT (dynamic — updated during WC)
-- ═══════════════════════════════════════════════════
CREATE TABLE player_tournament (
    player_id                UUID PRIMARY KEY REFERENCES players(id),
    wc_team_code             TEXT NOT NULL,
    jersey_number            INT,
    captain                  BOOLEAN DEFAULT FALSE,
    in_squad                 BOOLEAN DEFAULT TRUE,
    -- International stats
    international_caps       INT,
    international_goals      INT,
    international_debut      TEXT,
    -- WC 2026 specific
    tournament_role_en       TEXT,
    tournament_role_es       TEXT,
    narrative_arc_en         TEXT,
    narrative_arc_es         TEXT,
    injury_fitness_status    TEXT,
    wc_qualifying_contribution TEXT,
    -- Big game DNA
    world_cup_goals          INT,
    champions_league_goals   INT,
    derby_performances_en    TEXT,
    derby_performances_es    TEXT,
    clutch_moments           JSONB,
    -- WC history
    previous_wc_appearances  JSONB,
    host_city_connection     TEXT,
    -- Live during tournament
    group_stage_stats        JSONB,
    knockout_stats           JSONB,
    -- Refresh tracking
    updated_at               TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tournament_team ON player_tournament(wc_team_code);
```

### Metadata Tables (for Capi Analytics Mode)

```sql
-- ═══════════════════════════════════════════════════
-- SCHEMA_METADATA — Capi reads this to know what it
-- can query and how to describe each field to users
-- ═══════════════════════════════════════════════════
CREATE TABLE schema_metadata (
    id              BIGSERIAL PRIMARY KEY,
    table_name      TEXT NOT NULL,
    column_name     TEXT NOT NULL,
    -- For Capi's understanding
    description_en  TEXT NOT NULL,
    description_es  TEXT NOT NULL,
    data_type       TEXT NOT NULL,
    example_value   TEXT,
    -- Queryability
    is_filterable   BOOLEAN DEFAULT FALSE,
    is_sortable     BOOLEAN DEFAULT FALSE,
    is_aggregatable BOOLEAN DEFAULT FALSE,
    -- Analytics hints
    analytics_hint  TEXT,  -- e.g., "compare across teams", "correlate with value"
    unit            TEXT,  -- e.g., "EUR", "cm", "years"
    -- Grouping
    category        TEXT NOT NULL,  -- 'identity', 'career', 'style', 'tournament', 'market'
    volatility      TEXT NOT NULL CHECK (volatility IN ('static', 'semi_static', 'dynamic')),
    UNIQUE(table_name, column_name)
);

-- ═══════════════════════════════════════════════════
-- PIPELINE_RUNS — audit trail for every pipeline run
-- ═══════════════════════════════════════════════════
CREATE TABLE pipeline_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name   TEXT NOT NULL,
    run_type        TEXT CHECK (run_type IN ('full', 'incremental', 'enrichment', 'refresh')),
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          TEXT DEFAULT 'running',
    records_in      INT,
    records_out     INT,
    records_updated INT,
    error_message   TEXT,
    cost_usd        NUMERIC(8,4),
    tokens_used     INT,
    metadata        JSONB
);
```

---

## 5. Capi Analytics Mode (Premium)

With `schema_metadata` in place, Capi can dynamically discover what's queryable and build SQL on the fly.

### How It Works

1. **User asks:** "Which teams have the tallest average squad?"
2. **Capi reads** `schema_metadata` WHERE `is_aggregatable = true` — finds `height_cm` with hint "compare across teams"
3. **Capi builds query:**
   ```sql
   SELECT pt.wc_team_code, AVG(p.height_cm) as avg_height
   FROM players p
   JOIN player_tournament pt ON p.id = pt.player_id
   WHERE p.height_cm IS NOT NULL
   GROUP BY pt.wc_team_code
   ORDER BY avg_height DESC
   ```
4. **Capi formats** the result conversationally (with Capi personality)

### New Tool: `analyze_players`

```typescript
{
  name: 'analyze_players',
  description: 'Run analytical queries on World Cup player data. Premium only. Can compare teams, find patterns, rank players by any metric, and discover insights.',
  input_schema: {
    type: 'object',
    properties: {
      question: { type: 'string', description: 'The analytical question in natural language' },
      group_by: { type: 'string', description: 'Optional: group results by team, position, league, etc.' },
      limit: { type: 'number', description: 'Max results (default 10)' },
    },
    required: ['question'],
  },
}
```

### Example Analytics Capi Could Answer

- "¿Qué equipo tiene los jugadores más jóvenes?" → AVG(age) GROUP BY team
- "Show me left-footed forwards worth over €50M" → filter + sort
- "Which league produces the most World Cup players?" → COUNT GROUP BY current_league
- "Compare Argentina vs France squad market values" → side-by-side aggregation
- "Who are the most experienced players by caps?" → sort by international_caps
- "Correlation between height and position?" → cross-tab analysis

---

## 6. Pipeline Architecture — What Runs When

```
┌──────────────────────────────────────────────────────┐
│                    ONE-TIME PIPELINES                  │
│              (run once → data is permanent)            │
├──────────────────────────────────────────────────────┤
│                                                        │
│  1. INGEST        Sources → raw JSON files            │
│     (done)        TM scrape, static squads            │
│                                                        │
│  2. DEDUP         Raw → canonical player list         │
│     (needs redo)  Produces canonical_id + aliases      │
│                                                        │
│  3. ENRICH        Canonical → enriched profiles       │
│     (80% done)    AI-powered, $0.70 for 632 players   │
│                                                        │
│  4. SYNC STATIC   Enriched → Supabase players table   │
│     (not started) One-time write of static fields      │
│                                                        │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                  RECURRING PIPELINES                   │
│           (scheduled, update dynamic fields)           │
├──────────────────────────────────────────────────────┤
│                                                        │
│  5. TRANSFER REFRESH     Every 12 hours               │
│     (not started)        Updates player_career table   │
│                          Club, league, jersey, value   │
│                                                        │
│  6. TOURNAMENT LIVE      Every 6 hours during WC      │
│     (not started)        Updates player_tournament     │
│                          Caps, goals, fitness status   │
│                                                        │
│  7. MATCH FEED           Every 60 seconds during WC   │
│     (schema exists)      Updates active_matches        │
│                          Live scores, events           │
│                                                        │
└──────────────────────────────────────────────────────┘
```

---

## 7. Migration Sequence

### Phase A: Fix Dedup + Sync Static (this week)

1. **Rebuild dedup** with the canonical identity strategy (surname + DOB + team)
2. **Validate** against the 7 edge-case profiles in Section 2
3. **Generate canonical_ids** and alias table
4. **Wait for enrichment to finish** (currently 500/632, ~20 min)
5. **Re-export** enriched data with canonical_ids injected
6. **Create new Supabase migration** with the schema from Section 4
7. **Sync static fields** — one-time write of `players` table
8. **Sync career + tournament** — initial write from enriched data
9. **Seed schema_metadata** — descriptions for every field
10. **Update Capi tools** — point at new tables, kill runtime dedup

### Phase B: Recurring Pipelines (next week)

11. Build transfer refresh pipeline (API-Football squad data)
12. Build tournament live pipeline (caps/goals/fitness during WC)
13. Set up cron schedules
14. Add `pipeline_runs` audit logging

### Phase C: Capi Analytics Mode (week after)

15. Build `analyze_players` tool with schema_metadata integration
16. Add premium gate check
17. Test with 20+ example analytics questions
18. Ship

---

## 8. Open Questions

1. **Should we keep the legacy `pipeline_players` table** during transition, or drop it immediately?
   - Recommendation: Keep it read-only for 1 week, then drop after verifying Capi tools work on new schema.

2. **Photo URLs** — the enriched data doesn't have photos. Should we pull from API-Football during the transfer refresh pipeline?
   - Recommendation: Yes. API-Football has current headshots. Store in `players.photo_url`.

3. **Historical market values** — the existing `player_valuations` table has time-series data from TM. Keep it?
   - Recommendation: Yes. It's already static (historical). Link to new `players.id` via alias table.

4. **How aggressive should Capi analytics be?** — Should Capi be able to write arbitrary SQL, or only use predefined query templates?
   - Recommendation: Start with templates (safer, faster). Graduate to dynamic SQL once we trust the metadata layer.

5. **Enrichment re-runs** — if we re-enrich a player (e.g., after a major event), do we overwrite static fields?
   - Recommendation: No. Static means static. Create a `player_updates` table for addendums that Capi can reference alongside the original profile.
