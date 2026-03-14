# El Capi Data — Architecture, Lineage & Lessons Learned

**Last updated:** March 14, 2026
**Authors:** Carlo, Azteca (pipeline agent), Pelé (PM agent)
**Status:** Living document — update after every significant pipeline change

---

## 1. What This Document Covers

This is the single source of truth for how player data flows from raw sources into the production Supabase warehouse and ultimately into Capi's hands. It consolidates learnings from 9 days of pipeline development (March 6–14, 2026) across multiple working documents into one canonical reference.

For implementation details, see: `PIPELINE.md` (stage-by-stage code reference), `DATA_SCHEMA.md` (field definitions), `DATA-SOURCES.md` (source inventory).

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Transfermarkt │  │ Static       │  │ Static       │             │
│  │ CSVs         │  │ Squads       │  │ Bios         │             │
│  │ 34K players  │  │ players.ts   │  │ player-bios  │             │
│  │ Priority: 1  │  │ Priority: 3  │  │ Priority: 2  │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
│         │                  │                  │                     │
│  ┌──────┴──────────────────┴──────────────────┘                    │
│  │                                                                  │
│  │  ┌──────────────┐  ┌──────────────┐                             │
│  │  │ API-Football │  │ GPT-4o-mini  │                             │
│  │  │ Live squads  │  │ Narratives   │                             │
│  │  │ Priority: 1* │  │ Priority: 4  │                             │
│  │  └──────┬───────┘  └──────┬───────┘                             │
│  │         │                  │                                     │
└──┼─────────┼──────────────────┼─────────────────────────────────────┘
   │         │                  │
   ▼         │                  │
┌──────────────────┐            │
│  1. INGEST       │ Parse CSVs + TypeScript → DataFrames
└────────┬─────────┘            │
         │                      │
┌────────▼─────────┐            │
│  2. DEDUP        │ Fuzzy match (thefuzz) → canonical WC players
│  Auto ≥85        │ Nationality guard prevents cross-team merges
│  Review 70-84    │
└────────┬─────────┘            │
         │                      │
┌────────▼─────────┐            │
│  3. QA + EXPORT  │ Assertion gates → players_canonical_latest.json
└────────┬─────────┘            │
         │                      │
┌────────▼─────────┐            │
│  4. MERGE        │ 4-source priority merge with field attribution
│  TM > Bios >    │ → players_merged.json (facts only)
│  Squads > GPT   │
└────────┬─────────┘◄───────────┘
         │                     GPT enrichment feeds into merge
┌────────▼─────────┐
│  5. COMBINE      │ Facts (merge) + Narratives (GPT) → golden output
└────────┬─────────┘
         │
┌────────▼─────────┐
│  6. VERIFY       │ GPT-4o validates 12 critical fields (3 tiers)
│  Cost: ~$2.35    │ 1,694 corrections applied
└────────┬─────────┘
         │
┌────────▼─────────┐
│  7. DEPLOY       │ Generate SQL seeds OR REST API upsert
└────────┬─────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│           SUPABASE WAREHOUSE               │
│                                            │
│  players (1,176)                           │
│    ├── player_career (1,176)    FK →       │
│    ├── player_tournament (1,176) FK →      │
│    └── player_aliases (1,221+)  FK →       │
│                                            │
│  capi_knowledge (dynamic)                  │
│  schema_metadata (63)                      │
└──────────────┬─────────────────────────────┘
               │
    ┌──────────┼──────────────────────┐
    │          │                      │
    ▼          ▼                      ▼
┌────────┐ ┌────────────┐  ┌──────────────────┐
│  CAPI  │ │ Admin Dash │  │ Public Player    │
│  AI    │ │ /admin/    │  │ Profiles         │
│        │ │ players    │  │ (static TS +     │
│ Tools: │ │            │  │  curator overlay) │
│ search │ │ Warehouse  │  │                  │
│ detail │ │ queries +  │  │ players.ts +     │
│ squad  │ │ pagination │  │ player-overrides  │
│ web    │ │ + filters  │  │                  │
└────────┘ └────────────┘  └──────────────────┘
```

### Data Flow Summary

Raw sources (TM CSVs, TypeScript files, API-Football, GPT) are ingested, deduplicated via fuzzy matching, merged with source-priority attribution, enriched with AI narratives, verified by a second AI pass, and published to a normalized Supabase warehouse. Capi queries the warehouse in real-time via 6 tools + web search. The admin dashboard also queries the warehouse directly with pagination and data quality filters.

---

## 3. Source Priority & Trust Matrix

| Priority | Source | Trust Level | Provides | Limitations |
|----------|--------|-------------|----------|-------------|
| **1** | Transfermarkt CSVs | Highest for facts | 34K players, DOB, club, height, market value, nationality, transfers | Stale snapshot — no live updates |
| **1*** | API-Football | Highest for current club | Live squad data, photos, positions | Stale for some transfers (James at León, not Minnesota) |
| **2** | Static Bios | High | Caps, goals, achievements, narrative bios (EN/ES) | 636 bios only, manually maintained |
| **3** | Static Squads | Medium | WC roster composition, jersey, captain, team code | 6 fields only, manually maintained |
| **4** | GPT-4o-mini Enrichment | Lowest for facts, only source for narratives | 100+ fields per player: style, personality, story, WC role | Hallucination risk, knowledge cutoff |

### Field-Level Authority (Who Wins Per Field)

| Field | Primary Source | Fallback | Why |
|-------|---------------|----------|-----|
| `date_of_birth` | Transfermarkt | Static Bios | Structured, reliable |
| `nationality` | Transfermarkt | — | Official records |
| `current_club` | API-Football / TM | GPT (last resort) | TM stale, APIF most current |
| `current_league` | Derived from club | GPT | Should be computed, not stored |
| `position` | Static Squads | Transfermarkt | Squads have WC-specific position |
| `jersey_number` | Static Squads | API-Football | Squad source is authoritative |
| `height_cm` | Transfermarkt | Static Bios | TM has structured measurements |
| `market_value_eur` | Transfermarkt | — | TM is the gold standard for valuations |
| `international_caps/goals` | Static Bios | GPT | Hand-curated, verified |
| `career_trajectory` | TM transfers.csv | — | Ground-truth transfer history |
| `bio narratives (EN/ES)` | GPT-4o-mini | — | Only source for stories/personality |

---

## 4. Warehouse Schema (Final State)

The normalized warehouse in Supabase consists of 4 core tables plus supporting tables:

### Core Tables

**`players`** (1,176 rows) — Identity & static attributes
- PK: `id` (UUID, stable canonical ID)
- Key fields: `full_legal_name`, `known_as`, `date_of_birth`, `nationality_primary`, `height_cm`, `photo_url`, `data_confidence` (high/medium/low)
- Narrative fields: `origin_story_en/es`, `career_summary_en/es`, `personality` (JSONB)

**`player_career`** (1,176 rows) — Club & career data (semi-static)
- FK: `player_id` → `players.id`
- Key fields: `current_club`, `current_league`, `position_primary`, `position_secondary`, `estimated_value_eur`, `contract_expires`
- JSONB: `career_trajectory` (array of {club, from, to, fee}), `major_trophies`, `strengths`, `weaknesses`
- Narrative: `style_summary_en/es`, `signature_moves`, `comparable_to`

**`player_tournament`** (1,176 rows) — WC 2026 specific (dynamic)
- FK: `player_id` → `players.id`
- Key fields: `wc_team_code`, `jersey_number`, `captain`, `in_squad`, `international_caps`, `international_goals`
- Narrative: `tournament_role_en/es`, `narrative_arc_en/es`
- JSONB: `previous_wc_appearances`, `clutch_moments`

**`player_aliases`** (1,221+ rows) — Cross-source name linking
- FK: `player_id` → `players.id`
- Key fields: `alias_type` (transfermarkt_id, alternate_name, nickname, slug), `alias_value`

### Supporting Tables

**`capi_knowledge`** — Dynamic knowledge entries loaded into Capi's system prompt at runtime. Allows updating Capi's knowledge without redeploying code.

**`schema_metadata`** (63 rows) — Column descriptions for Capi's Analytics Mode SQL generation.

### Key Relationships

```
players (1)
  ├── player_career (1)     ON player_career.player_id = players.id
  ├── player_tournament (1)  ON player_tournament.player_id = players.id
  └── player_aliases (N)     ON player_aliases.player_id = players.id
```

All FKs point inward to `players.id`. Queries must start from `players` and join outward — not the reverse. This was a hard-learned lesson (see §6).

---

## 5. How It Maps to the App

### Capi AI (claude-sonnet-4-6)

Capi queries the warehouse in real-time via 6 tools + web search:

| Tool | Query Pattern | Tables |
|------|---------------|--------|
| `search_players` | `ilike` on known_as + nationality | `players` JOIN `player_career` JOIN `player_tournament` |
| `get_player_details` | Exact ID lookup | All 3 tables + `player_aliases` |
| `get_squad` | Filter by `wc_team_code` | `player_tournament` JOIN `players` JOIN `player_career` |
| `get_live_matches` | Active match lookup | `active_matches` table |
| `get_career_history` | Career trajectory JSONB | `player_career.career_trajectory` |
| `run_analytics_query` | Arbitrary read-only SQL | Any warehouse table (validated, LIMIT 50, 5s timeout) |

Additionally, Capi has Anthropic's server-side **web search** tool (max 3 uses/message) as a safety net for facts that may be stale in the warehouse.

### Admin Dashboard (`/admin/players`)

Queries warehouse directly with:
- Server-side pagination (50/page)
- Status filters by `data_confidence` (All / High / Medium / Low / Incomplete)
- Search by name, club, or team code
- Missing fields tracking (count + names of null critical fields)

### Public Player Profiles (`/players/[slug]`)

Uses the **static TypeScript** layer (`src/data/players.ts`) for fast page loads, with curator corrections from `player_corrections` table overlaid at runtime via `player-overrides.ts`. This is a separate read path from the warehouse — a known gap that will be unified later.

---

## 6. Lessons Learned (Do's and Don'ts)

### Architecture

**DO: Start from `players` table and join outward.** All foreign keys point inward to `players.id`. Starting from child tables (player_career, player_tournament) and trying to join to each other fails because there's no FK between siblings — they independently reference the parent.

**DO: Use `data_confidence` instead of binary conflict flags.** The old model (has_conflicts/blocked/clean) was a pipeline artifact. The warehouse model uses a quality gradient (high/medium/low) which is more useful for triage and filtering.

**DON'T: Trust GPT for factual fields.** GPT-4o-mini gets clubs wrong for ~15% of players who transferred recently. The knowledge cutoff is the same for both enrichment and verification, so using GPT-4o to verify GPT-4o-mini doesn't catch stale data. GPT is only trustworthy for narratives (stories, personality, style descriptions).

**DON'T: Use GPT enrichment for club/league/nationality.** These must come from structured sources (Transfermarkt, API-Football, static squads). Early pipeline versions had 100% of clubs from GPT — this caused the "all clean" false confidence problem.

### Deduplication

**DO: Use nationality guards.** Without them, common names like "Ben Williams" get merged across completely different national teams. The nationality plausibility map prevents this.

**DO: Cap generic name scores.** Single-token names (e.g., "Neymar", "Vinicius") without corroborating signals (DOB match, club match) can't auto-merge — capped at score 75 to force manual review.

**DO: Quarantine ambiguous pairs.** When an ID appears in multiple Tier 2 pairs (~40 of 5,890, under 1%), don't guess — remove all ambiguous pairs, save them in `dedup_pairs_ambiguous` for manual curation, and let affected IDs fall through as unmatched. This keeps Tier 2 precision at 100%.

**DON'T: Trust name similarity alone.** A 92% name match between "Carlos Vela" (Mexico) and "Carlos Vela" (totally different person) means nothing without nationality/DOB/club corroboration.

**DON'T: Trust APIF initials for first-name inference.** APIF often uses initials (e.g., "A. Özcan") that don't match the actual first name (actually "F. Özcan"). Wikipedia is the best source for resolving abbreviated names.

### Data Quality

**DO: Use assertion gates between pipeline stages.** Every stage has contracts (minimum player counts, field coverage thresholds, no cross-team duplicates). If assertions fail in strict mode, the pipeline halts before bad data propagates.

**DO: Track source attribution per field.** `players_merged.json` stores which source provided each field value. This is essential for debugging ("why does Ospina show as retired?" → "came from GPT, not APIF").

**DO: Overwrite identity but preserve enrichment on staging promotion.** When loading staging data into a warehouse with existing enriched players, overwrite identity fields (name, DOB, nationality, photo — suspect from old pipeline) but preserve GPT-generated enrichment fields (narratives, personality, tournament role) that are expensive to reproduce.

**DON'T: Assume API-Football is always current.** APIF returned James Rodríguez at Club León (his previous club) instead of Minnesota United (signed Feb 6, 2026). Always cross-check with web search for high-profile transfers.

**DON'T: Use "last competition played" as the league.** API-Football's `statistics[0].league.name` returns the last competition the player appeared in (could be "Super Cup", "Friendlies", "Copa América"), not their domestic league. League must be derived from club → league mapping.

### Operations

**DO: Use incremental enrichment with checkpointing.** GPT enrichment supports `--resume` mode with per-player checkpointing. This means a failed run at player 400 doesn't waste the first 399 calls (~$2 saved).

**DO: Generate SQL seed files, not just REST API pushes.** SQL files in `supabase_seed/` can be reviewed, diffed, and loaded manually via the Supabase SQL Editor. The REST API push (`push_to_supabase.py`) is faster but harder to audit.

**DON'T: Run Supabase operations from sandboxed VMs.** Outbound HTTP to Supabase is blocked (403 via proxy) in sandboxed environments like Cowork. All Supabase scripts must run from Carlo's actual machine.

**DON'T: Forget `TRUNCATE CASCADE` ordering.** The `players.sql` seed truncates CASCADE, wiping all child tables. Load order: players → player_career → player_tournament → player_aliases.

### Curator System

**DO: Keep curator corrections as a separate overlay.** The `player_corrections` table + `player-overrides.ts` runtime merge is elegant — corrections take effect immediately without a pipeline re-run or redeploy.

**DON'T: Assume curator corrections update the warehouse.** Currently, curator corrections only patch the static TypeScript player data on the public-facing pages. They don't flow back into the warehouse tables. This is a known gap — the two correction paths (curator → static overlay, admin → warehouse update) need to be unified.

---

## 7. Current State (March 14, 2026)

### What Works

- 1,176 players across 42 confirmed WC 2026 squads in warehouse
- Capi queries warehouse in real-time via 6 tools + web search
- Admin dashboard shows data quality with confidence levels and missing field counts
- Pipeline runs end-to-end: ingest → dedup → merge → enrich → combine → verify → deploy
- API-Football sync operational for individual teams (Colombia done, 28 players)
- Curator correction system operational on public player profiles

### What Needs Work

| Issue | Priority | Detail |
|-------|----------|--------|
| Full APIF sync for all 42 teams | P0 | Only Colombia synced so far. Need to run `all` mode. |
| Curator corrections → warehouse sync | P1 | Corrections only patch static TS, not warehouse. Two systems out of sync. |
| League field quality | P1 | APIF returns "last competition" not domestic league. Need club → league mapping. |
| 6 remaining teams (42 vs 48) | P2 | 6 teams not yet in warehouse (likely unconfirmed squads). |
| Pipeline audit trail | P2 | `pipeline_runs` table exists but is empty. Should log every run. |
| Automated refresh schedule | P3 | No cron/scheduled sync. All updates are manual pipeline runs. |

### Cost Per Refresh

| Operation | Model | Cost | Notes |
|-----------|-------|------|-------|
| Full enrichment (new players only) | GPT-4o-mini | ~$3.50 | One-time; incremental via --resume |
| Full verification | GPT-4o | ~$2.35 | Per cycle; validates 12 fields |
| Reconciliation + merge + deploy | Local Python | Free | ~30s runtime |
| APIF sync (all teams) | API-Football | Free tier | Rate-limited to 100 req/day on free plan |
| **Typical refresh (no new players)** | | **~$2.35** | Verification only |

---

## 8. File Index

### Canonical Outputs (data/output/)

| File | What | Used By |
|------|------|---------|
| `players_golden.json` | Pipeline canonical output (638 enriched players — merged facts + narratives). **Note:** warehouse has 1,176 players; the extra 538 came from squad build + APIF sync flows | Seed generator |
| `players_merged.json` | Per-player field map with source attribution | Combiner, debugging |
| `players_enriched.json` | GPT narratives (100 fields × players) | Combiner |
| `players_canonical_latest.json` | Flat dedup output (34K+ players) | Merge step |
| `reconciliation_report.json` | Conflict analysis + blocked players | Admin panel (legacy) |
| `supabase_seed/*.sql` | SQL INSERT files (4 tables) | Manual Supabase load |

### Pipeline Entry Points

| Script | What | Usage |
|--------|------|-------|
| `run_full_pipeline.py` | 7-stage orchestrator | `python run_full_pipeline.py [--all] [--from stage]` |
| `run_enrichment.py` | GPT-4o-mini narratives | `python run_enrichment.py [--resume]` |
| `run_verification.py` | GPT-4o fact-checking | `python run_verification.py [--apply]` |
| `push_to_supabase.py` | REST API push to warehouse | `python push_to_supabase.py` |
| `pipeline.sync.sync_apif_warehouse` | API-Football sync | `python -m pipeline.sync.sync_apif_warehouse all` |
| `pipeline.generators.generate_players_ts` | Generate static TS | `python -m pipeline.generators.generate_players_ts` |

### Documentation Map

| Document | Location | Purpose |
|----------|----------|---------|
| **This file** | `docs/production/DATA_LINEAGE.md` | Architecture, lineage, lessons learned |
| PIPELINE.md | `docs/production/PIPELINE.md` | Stage-by-stage code reference |
| DATA_SCHEMA.md | `docs/production/DATA_SCHEMA.md` | Full JSON schema + Supabase tables |
| DATA-SOURCES.md | `docs/production/DATA-SOURCES.md` | Source inventory + env vars |
| DATA_DICTIONARY.md | `docs/production/DATA_DICTIONARY.md` | Supabase column-level docs |
| DATA-PIPELINE-AUDIT.md | `docs/active/DATA-PIPELINE-AUDIT.md` | Technical audit (7 weaknesses) |

### Archived Working Documents

These were used during development and are kept for historical reference:

| Document | Original Location | Now At |
|----------|-------------------|--------|
| Pipeline migration strategy | `docs/active/` | `docs/archive/2026-03-PIPELINE_MIGRATION_STRATEGY.md` |
| La Copa Mundo pipeline spec | `docs/active/` | `docs/archive/2026-03-lacopamundo-player-data-pipeline.md` |
| AZTECA_TM_INGEST_PLAN.docx | `docs/active/` | Still active (TM fix plan) |
| ARCHITECTURE_BLUEPRINT.docx | `docs/active/` | Still active (future-state Prefect/dbt) |
| 35 Azteca session logs | `~/el-capi/` root | `docs/archive/azteca-sessions/` |
| BUSINESS_RULES.docx | `~/el-capi/` root | `docs/archive/azteca-sessions/` |
| DEDUP_RULES.docx | `~/el-capi/` root | `docs/archive/azteca-sessions/` |
| SOURCE_DATA_PROFILE_REPORT.docx | `~/el-capi/` root | `docs/archive/azteca-sessions/` |

The `azteca-sessions/` archive contains all task descriptions (AZTECA_*.md), their results (*_RESULTS.md), data samples, and reference .docx files from the March 2026 pipeline development sprint. Key learnings from these sessions have been consolidated into this DATA_LINEAGE.md document.

---

*This document should be updated after any significant pipeline change, new data source integration, or architectural decision. It replaces the scattered working documents used during initial development.*
