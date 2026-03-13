# El Capi Data Pipeline — Technical Audit

> **Audience**: CTO / Engineering Leadership  
> **Last verified**: March 12, 2026  
> **Status**: DRAFT — under active review  
> **Author**: Azteca (pipeline agent), audited by Pelé (PM agent)

---

## Executive Summary

El Capi serves **677 FIFA World Cup 2026 players** across **48 national teams** through a multi-source data pipeline that ingests, deduplicates, enriches, cross-validates, and publishes player data to a Supabase PostgreSQL database. The AI chat assistant (Capi) queries this data in real-time.

The pipeline is functional and data is live, but this audit identifies **7 weaknesses** that require attention before production launch.

---

## 1. Data Sources

| # | Source | Type | What It Provides | Record Count |
|---|--------|------|------------------|-------------|
| 1 | **Transfermarkt CSVs** | Structured | Identity, club, market value, DOB, height, foot, agent, contract, transfers, valuations history | ~34,000 players (global), 632+ WC |
| 2 | **Static Squads** (`players.ts`) | Hand-curated TypeScript | Official WC 2026 rosters: name, position, club, jersey, captain flag, team code | 632 players across 48 teams |
| 3 | **Static Bios** (`player-bios.ts` + `bios/*.ts`) | Hand-curated TypeScript | Caps, goals, achievements, DOB, height, birthplace, previous clubs, bio narratives (EN/ES) | 636 bios |
| 4 | **GPT-4o-mini Enrichment** | AI-generated | ~100 fields per player: style analysis, personality, WC narrative, big-game DNA, trophies, records, fun facts | 677 players |
| 5 | **GPT-4o Verification** | AI-validated | Cross-checks 12 critical fields against model knowledge; applies corrections | 632 verified |
| 6 | **API-Football** | Structured API | Historical data; used during ingestion. Key configured but not actively polled. | Supplementary |

### Source Trustworthiness (as configured)

```
Transfermarkt  ▓▓▓▓▓▓▓▓▓▓  Highest priority — structured, large dataset
Static Bios    ▓▓▓▓▓▓▓▓░░  Hand-curated, high trust for caps/goals/achievements
Static Squads  ▓▓▓▓▓▓▓░░░  Official roster data, limited fields
GPT Enrichment ▓▓▓▓▓░░░░░  Lowest priority — known to hallucinate transfers
```

### Known Data Freshness Issues

| Issue | Severity | Detail |
|-------|----------|--------|
| **Transfermarkt CSVs are stale** | HIGH | The CSV dataset is a static snapshot. Players who transferred after the snapshot date (e.g., Luis Díaz to Bayern Munich, summer 2025) show incorrect clubs. Affects ~47 blocked players. |
| **GPT knowledge cutoff** | MEDIUM | GPT-4o-mini's training data may not include transfers or events past its cutoff. Both enrichment and verification share this limitation. |
| **No live data feed** | MEDIUM | No automated pull from Transfermarkt or API-Football. All updates require a manual pipeline run. |

---

## 2. Pipeline Flow

```
                     ┌─────────────────────────────────────────────────────┐
                     │                  DATA SOURCES                       │
                     │                                                     │
                     │  Transfermarkt CSVs    Static Squads (players.ts)   │
                     │  (34K players)         (632 WC players)             │
                     │                                                     │
                     │  Static Bios           API-Football                 │
                     │  (636 bios)            (supplementary)              │
                     └────────────┬────────────────────────────────────────┘
                                  │
                          ┌───────▼───────┐
                          │  1. INGEST    │  Parse CSVs + TypeScript → Python DataFrames
                          └───────┬───────┘
                                  │
                          ┌───────▼───────┐
                          │  2. DEDUP     │  Fuzzy match (thefuzz) → 632 canonical WC players
                          └───────┬───────┘  Auto-merge ≥85, Review 70–84, New <70
                                  │
                          ┌───────▼───────┐
                          │  3. QA        │  Missing fields, age anomalies, squad completeness
                          └───────┬───────┘
                                  │
                          ┌───────▼───────┐
                          │  4. EXPORT    │  players_canonical_latest.json (flat, 34K)
                          └───────┬───────┘
                                  │
                          ┌───────▼───────┐
                          │  5. ENRICH    │  GPT-4o-mini → 100 fields × 677 players
                          └───────┬───────┘  Cost: ~$3.50 per full run
                                  │
                          ┌───────▼───────┐
                          │  6. CANONICAL │  Assign UUID canonical_id
                          └───────┬───────┘  players_canonical.json (enriched, 677)
                                  │
                          ┌───────▼───────┐
                          │  7. RECONCILE │  Merge 4 sources → detect conflicts → auto-resolve
                          └───────┬───────┘  47 BLOCKED / 73 missing critical fields
                                  │
                          ┌───────▼───────┐
                          │  8. VERIFY    │  GPT-4o validates 12 critical fields
                          └───────┬───────┘  1,694 corrections applied. Cost: ~$2.35
                                  │
                          ┌───────▼──────────┐
                          │  9. PUSH         │  REST API upsert → 4 Supabase tables
                          │  (blocked skip)  │  Blocked players excluded by default
                          └──────────────────┘
                                  │
                          ┌───────▼───────┐
                          │  SUPABASE     │  players, player_career, player_tournament,
                          │  WAREHOUSE    │  player_aliases, schema_metadata
                          └───────┬───────┘
                                  │
                     ┌────────────▼────────────────────┐
                     │         EL CAPI (AI)            │
                     │                                  │
                     │  search_players     → warehouse  │
                     │  get_player_details → warehouse  │
                     │  get_squad          → warehouse  │
                     │  get_career_history → warehouse  │
                     │  run_analytics_query → SQL RPC   │
                     └─────────────────────────────────┘
```

---

## 3. Deduplication Strategy

**Problem**: Transfermarkt has ~34,000 players. Static squads define the official 632 WC roster. We need to match these datasets to create one canonical record per player.

**Algorithm**: Fuzzy name matching via `thefuzz` library with multi-signal scoring:

| Signal | Score Impact |
|--------|-------------|
| Name similarity (token_sort, token_set, partial) | Base score (0–100) |
| DOB exact match | +15 |
| DOB mismatch (both present) | -20 |
| Club name similarity ≥80% | +8 |
| Nationality match | +5 |
| Nationality mismatch | -10 to -35 |

**Thresholds:**

| Score | Action |
|-------|--------|
| ≥ 85 | Auto-merge |
| 70–84 | Review zone (manual decision) |
| < 70 | Treat as new player |

**Merge rules**: Transfermarkt wins for DOB, height, market value, nationality, agent, contract. Static squads wins for `wc_team_code`, `jersey_number`, `captain`, `in_wc_squad`.

---

## 4. Enrichment Schema

Each canonical player is enriched by GPT-4o-mini into ~100 fields across 10 sections:

| Section | Key Fields | Example |
|---------|-----------|---------|
| `identity` | full_legal_name, DOB, nationality, height, foot, languages, nicknames | "Lionel Andrés Messi Cuccittini" |
| `career` | current_club, league, position, trajectory, trophies, records, caps, goals | "Inter Miami CF", "MLS" |
| `playing_style` | style_summary (EN/ES), signature_moves, strengths, weaknesses, comparable_to | "Messi is a left-footed playmaker..." |
| `story` | origin_story (EN/ES), breakthrough_moment, career_defining_quote | Bilingual narratives |
| `personality` | celebrations, superstitions, interests, charity, tattoos, fun_facts | "Points to the sky after scoring" |
| `world_cup_2026` | previous_wc_appearances, qualifying_contribution, tournament_role (EN/ES) | WC narrative arcs |
| `big_game_dna` | wc_goals, UCL_goals, derby_performances, clutch_moments | Performance records |
| `market` | estimated_value_eur, endorsement_brands, agent | "€35,000,000" |
| `injury_history` | notable_injuries, injury_prone | Injury timeline |
| `meta` | data_confidence, data_gaps | "high", [] |

---

## 5. Source Reconciliation

### How It Works

After enrichment, data from all 4 sources is merged and cross-validated:

1. **Merge** (`merge.py`): For each canonical player, extract values for 16 critical fields from all available sources. Output: `players_merged.json` with source attribution.

2. **Detect** (`conflicts.py`): Compare normalized values. Smart normalization handles:
   - Club aliases ("Man United" = "Manchester United FC")
   - Position categories ("FWD" = "Centre-Forward")
   - Market value tolerance (within 3×)
   - Caps/goals tolerance (within ±10)
   - Height tolerance (within ±3cm)
   - Consensus detection (if 2+ sources agree, one outlier is dismissed)

3. **Severity assignment**:

| Severity | Fields | Policy |
|----------|--------|--------|
| **CRITICAL** | current_club, current_league, date_of_birth, nationality | **Blocks publish** — player excluded from Supabase push |
| **IMPORTANT** | position, market_value, contract, caps, goals, jersey, captain | Highest-priority source wins; flagged for review |
| **INFORMATIONAL** | career_trajectory, trophies, height, photo, agent | Auto-resolved; logged |

4. **Auto-resolve**: Two strategies run automatically:
   - **Consensus**: If GPT + static squads agree and Transfermarkt disagrees → accept GPT (stale TM data)
   - **Non-critical priority**: For IMPORTANT/INFORMATIONAL fields → accept highest-priority source

5. **Human review**: CRITICAL conflicts require manual resolution via admin panel (`/admin/reconciliation`) or CLI.

### Current Reconciliation State

| Metric | Count |
|--------|-------|
| Total players processed | 677 |
| Clean (no conflicts) | 522 |
| With conflicts | 155 |
| **Blocked** (CRITICAL unresolved) | **47** |
| Auto-resolved | 20 |
| Missing critical fields | 73 |

**Conflicts by field:**

| Field | Count | Severity |
|-------|-------|----------|
| international_caps | 56 | IMPORTANT |
| position | 54 | IMPORTANT |
| international_goals | 42 | IMPORTANT |
| jersey_number | 23 | IMPORTANT |
| current_league | 23 | CRITICAL |
| agent | 17 | INFORMATIONAL |
| current_club | 12 | CRITICAL |
| nationality | 12 | CRITICAL |
| market_value_eur | 5 | IMPORTANT |
| date_of_birth | 3 | CRITICAL |
| height_cm | 3 | INFORMATIONAL |

---

## 6. Verification System

**Purpose**: GPT-4o (not mini) validates 12 critical fields by checking each player's current values against its own knowledge.

**Tier system:**

| Tier | Name | Fields | Action on error |
|------|------|--------|-----------------|
| **T1 — Imperdonable** | "Fans don't forgive" | current_club, current_league, nationality, position, in_wc_squad | Auto-apply correction |
| **T2 — Muy Importante** | Should be right | date_of_birth, estimated_value_eur | Auto-apply correction |
| **T3 — Importante** | Nice to have right | jersey_number, caps, goals, injury status, contract_expires | Apply with review |

**Results**: 632/632 players verified. 1,694 corrections applied. Cost: ~$2.35.

**Limitation**: GPT-4o shares the same knowledge cutoff problem as GPT-4o-mini. It cannot catch errors on facts that changed after its training data — this is the exact scenario that caused the Luis Díaz incident (showed Liverpool when he'd transferred to Bayern Munich in summer 2025).

---

## 7. Production Database (Supabase)

### Warehouse Tables (PRODUCTION — Capi reads these)

| Table | PK | Rows | Purpose |
|-------|-----|------|---------|
| `players` | `id` (UUID) | 632 | Canonical identity, story, personality, photo |
| `player_career` | `player_id` (FK → players) | 632 | Club, league, position, style, market value, trajectory |
| `player_tournament` | `player_id` (FK → players) | 632 | WC 2026 squad data, caps, goals, narrative |
| `player_aliases` | `id` (serial) | 1,148 | Cross-source name mapping (source_id, slug, known_as) |
| `schema_metadata` | `id` (serial) | 63 | Column descriptions for Capi Analytics Mode |
| `pipeline_runs` | `id` (UUID) | — | Audit trail (not yet populated) |

### Legacy Tables (ARCHIVE — no longer queried by Capi)

| Table | Status | Notes |
|-------|--------|-------|
| `pipeline_players` | Archived | Flat schema, no longer matches enriched data |
| `clubs` | Archived | Superseded by `player_career.current_club` |
| `player_bios` | Archived | Superseded by `players` narrative fields |
| `player_valuations` | Archived | Historical market values; not in warehouse |
| `transfers` | Archived | Historical transfer records; career_trajectory JSONB in `player_career` |

### Active Tables (Non-player data, still in use)

| Table | Purpose |
|-------|---------|
| `active_matches` | Live match scores (polled by `get_live_matches` tool) |
| `teams` | 48 WC teams with FIFA codes, group assignments |
| `venues` | Stadium data for 16 host cities |
| `cities` | Host city information |
| `matches` | WC 2026 match schedule |
| `profiles` | User profiles with `is_admin`, `is_curator` flags |
| `player_corrections` | Curator-submitted corrections (slug-based) |

### How Data Gets Pushed

`push_to_supabase.py` uses the Supabase REST API with the **service role key**:

1. Reads `players_canonical.json` (677 enriched players)
2. Reads `reconciliation_report.json` → identifies blocked players
3. **Skips blocked players** (47 currently) — they don't reach the database
4. Transforms nested JSON → flat rows with proper types (dates, arrays, JSONB)
5. Upserts in batches of 50 into `players`, `player_career`, `player_tournament`
6. Inserts aliases with conflict-skip (no duplicates)

---

## 8. How El Capi Reads Data

### Tool Architecture

Capi has 6 tools, all **read-only**:

| Tool | Supabase Query | Returns |
|------|---------------|---------|
| `search_players` | RPC `search_players_by_name` → full-text + alias search → JOIN career + tournament | Name, club, position, team, jersey |
| `get_player_details` | 3 parallel queries: `players` + `player_career` + `player_tournament` | Full 100-field profile |
| `get_squad` | `teams` → code lookup → RPC `get_squad` | Full roster (GK → DEF → MID → FWD) |
| `get_career_history` | `player_career.career_trajectory` (JSONB) | Transfer history, trophies, records |
| `get_live_matches` | `active_matches` | Current/upcoming match scores |
| `run_analytics_query` | `execute_readonly_sql` RPC (premium only) | Custom SQL results |

### Analytics Mode (Premium)

For premium users, Capi can generate and execute read-only SQL:

1. System prompt Layer 5 injects full schema reference from `schema_metadata` (63 rows)
2. Capi generates SQL based on user question
3. `analytics.ts` validates: SELECT-only, whitelisted tables, no mutations, LIMIT ≤ 50
4. `execute_readonly_sql` RPC runs it with 5s timeout, service_role only
5. Results returned as JSON → Capi explains in natural language

**Whitelisted tables**: players, player_career, player_tournament, player_aliases, teams, matches, venues, cities, schema_metadata

---

## 9. Corrections System

### Two Correction Paths (Disconnected)

#### Path A: Curator Corrections (Static Data)

```
User/Curator → "Suggest a correction" button on player page
  → POST /api/player-corrections (player_slug, field, proposed_value)
  → Admin reviews in dashboard (/admin → Corrections tab)
  → Admin approves/rejects (PATCH /api/player-corrections/[id])
  → player-overrides.ts reads approved corrections at runtime
  → Static player pages (team roster, player detail) show corrected data
```

**Fields**: club, age, name, number, position (5 fields only)  
**Scope**: Applies to static TypeScript `Player` objects only  
**Storage**: `player_corrections` table in Supabase

#### Path B: Pipeline Reconciliation (Warehouse Data)

```
Pipeline detects conflict between 4 sources
  → reconciliation_report.json flags conflict
  → Admin reviews in /admin/reconciliation (or CLI)
  → Resolution saved to reconciliation_resolutions.json
  → "Apply to canonical" writes to players_canonical.json
  → push_to_supabase.py upserts to warehouse tables
  → Capi tools see updated data
```

**Fields**: All 16 critical fields  
**Scope**: Updates the warehouse (what Capi tools query)

---

## 10. Weaknesses and Open Issues

### WEAKNESS 1: Two Disconnected Correction Systems

**Impact**: HIGH  
**Detail**: Curator corrections (Path A) apply to static TypeScript player data shown on team/player pages. They do **not** update the warehouse tables that Capi tools query. A curator could approve "Luis Díaz → Bayern Munich" and the player page would show Bayern, but when a user asks Capi "Where does Luis Díaz play?", Capi's `get_player_details` would still return whatever is in the warehouse.

**Fix needed**: Approved curator corrections should either (a) feed into the reconciliation pipeline as a fifth source, or (b) directly update warehouse tables.

### WEAKNESS 2: Pipeline Runs Table Empty

**Impact**: MEDIUM  
**Detail**: `pipeline_runs` table exists in the schema but is never populated. There is no audit trail of when the pipeline was last run, what changed, or who triggered it.

**Fix needed**: `refresh.py` and `push_to_supabase.py` should log runs to this table.

### WEAKNESS 3: 47 Blocked Players

**Impact**: HIGH  
**Detail**: 47 players have unresolved CRITICAL conflicts and are **not in the database**. These are likely stale Transfermarkt data where the player's club or league changed after the CSV snapshot. They need human review via the admin panel.

**Breakdown**: 12 current_club conflicts, 23 current_league conflicts, 12 nationality conflicts, 3 date_of_birth conflicts.

**Fix needed**: Manual review of each blocked player in `/admin/reconciliation`.

### WEAKNESS 4: 172 Players Missing Date of Birth

**Impact**: MEDIUM  
**Detail**: 25% of canonical players (172/677) have no `date_of_birth`. This is likely because they were added from static squads without a Transfermarkt match, and GPT enrichment couldn't find the DOB. 95 players also missing `current_league`.

**Fix needed**: A targeted enrichment pass for missing critical fields, or sourcing DOB data from an API.

### WEAKNESS 5: No Live Data Refresh

**Impact**: HIGH  
**Detail**: There is no automated data refresh mechanism. Transfers, injuries, squad changes, and market value updates require a manual pipeline run (`python refresh.py`). During the tournament, real-time stats (goals, cards, minutes played) will not flow into the warehouse automatically.

**Fix needed**: Cron job for periodic refresh (`/api/cron/pipeline-sync` exists as a route but is not wired to the full pipeline). Live match data already flows via `active_matches` but player stats do not.

### WEAKNESS 6: 677 vs 632 Player Count Discrepancy

**Impact**: LOW  
**Detail**: The canonical JSON has 677 players, but only 632 are expected (48 teams × ~23 players + standby). The extra 45 may be review-zone matches that created duplicate entries, or standby/reserve players. The Supabase warehouse has 632 (because blocked players and extras were excluded during push).

**Fix needed**: Audit the 45 extra players. Determine if they are duplicates, reserves, or dedup errors.

### WEAKNESS 7: Verification Uses Same AI as Enrichment

**Impact**: MEDIUM  
**Detail**: Both enrichment (GPT-4o-mini) and verification (GPT-4o) draw from similar training data. When Transfermarkt is stale and the AI models don't have updated information, verification cannot catch the error. The Luis Díaz case proved this — GPT-4o verified "Liverpool" as correct because its training data pre-dated the Bayern transfer.

**Fix needed**: The reconciliation pipeline partially addresses this by cross-validating against non-AI sources. For truly current data, a structured API source (Transfermarkt API, API-Football real-time) would be needed.

---

## 11. Security

| Layer | Mechanism |
|-------|-----------|
| **Database** | Row-Level Security (RLS) on all tables. Service role key for admin/pipeline operations. Anon key for user-facing reads. |
| **Analytics RPC** | `execute_readonly_sql` restricted to `service_role` only. SELECT-only, 5s timeout, mutation keywords blocked. |
| **Admin Panel** | Proxy-level redirect for unauthenticated users. API-level `verifyAdmin()` / `verifyCuratorOrAdmin()` checks. |
| **Corrections** | RLS: users see own corrections only. Only admins can approve/reject. |
| **Pipeline** | Service role key in `.env.local` (never committed). Pipeline runs locally, not in CI. |
| **API Keys** | All secrets in `.env.local`, gitignored. GitHub push protection enabled. |

---

## 12. Cost Structure

| Operation | Model | Cost | Frequency |
|-----------|-------|------|-----------|
| Full enrichment (677 players) | GPT-4o-mini | ~$3.50 | One-time (incremental for new players) |
| Full verification (632 players) | GPT-4o | ~$2.35 | Per refresh cycle |
| Reconciliation | Local Python | Free | Per refresh cycle |
| Pipeline (ingest/dedup/QA/export) | Local Python | Free | Per refresh cycle |
| Supabase push | REST API | Free (within tier) | Per refresh cycle |
| **Total per refresh** | | **~$2.35** | Only verification (no new players) |
| **Total first run** | | **~$5.85** | Enrichment + verification |

---

## 13. File Inventory

### Pipeline (`el-capi-data/`)

| File | Role |
|------|------|
| `run_pipeline.py` | Orchestrator: ingest → dedup → QA → export |
| `run_enrichment.py` | GPT-4o-mini enrichment with checkpointing |
| `run_verification.py` | GPT-4o critical field verification |
| `refresh.py` | Safe refresh with backup/rollback/cost estimation |
| `push_to_supabase.py` | REST API push to warehouse tables |
| `pipeline/ingest/transfermarkt.py` | CSV parser |
| `pipeline/ingest/static_squads.py` | TypeScript players.ts parser |
| `pipeline/ingest/static_bios.py` | TypeScript bios parser |
| `pipeline/dedup/matcher.py` | Fuzzy matching engine |
| `pipeline/dedup/resolver.py` | Merge resolution rules |
| `pipeline/dedup/canonical.py` | UUID canonical_id assignment |
| `pipeline/qa/checks.py` | Validation rules |
| `pipeline/verify/critical_fields.py` | GPT-4o verification prompts |
| `pipeline/verify/apply_updates.py` | Correction applier |
| `pipeline/reconcile/merge.py` | 4-source field merger |
| `pipeline/reconcile/conflicts.py` | Conflict detection + severity |
| `pipeline/reconcile/review.py` | CLI review tool |
| `pipeline/reconcile/career_builder.py` | Transfer history builder |

### Critical Output Files (`el-capi-data/data/output/`)

| File | What | Size |
|------|------|------|
| `players_canonical.json` | **THE source of truth** — enriched + verified | 677 players |
| `reconciliation_report.json` | Conflict analysis | 5,138 lines |
| `reconciliation_resolutions.json` | Audit trail of resolved conflicts | Updated per resolution |
| `players_merged.json` | Per-player field map with source attribution | 677 players |
| `verification_applied.json` | Which corrections were applied by GPT-4o | 1,694 corrections |

---

## Appendix A: Migration History

22 Supabase migrations in chronological order:

| Date | File | Purpose |
|------|------|---------|
| — | `00001_initial_schema.sql` | Core tables: cities, venues, teams, matches |
| Mar 8 | `20260308_admin.sql` | `is_admin` flag on profiles |
| Mar 8 | `20260308_predictions.sql` | User predictions system |
| Mar 9 | `20260309_groups.sql` | User groups / social features |
| Mar 9 | `20260309_premium.sql` | Premium subscription support |
| Mar 9 | `20260309_player_corrections.sql` | Curator correction system + `is_curator` flag |
| Mar 10 | `20260310_api_keys.sql` | API key management |
| Mar 10 | `20260310_avatar_url.sql` | User avatar storage |
| Mar 10 | `20260310_capi_conversations.sql` | Chat conversation logging |
| Mar 10 | `20260310_capi_conversations_unique.sql` | Dedup constraint for conversations |
| Mar 10 | `20260310_feedback.sql` | User feedback table |
| Mar 10 | `20260310_fix_new_user_trigger.sql` | Profile creation trigger fix |
| Mar 10 | `20260310_profiles_service_role.sql` | Service role access to profiles |
| Mar 10 | `20260310_quiniela_schema.sql` | Betting pool schema |
| Mar 11 | `20260311_capi_knowledge.sql` | Capi knowledge base entries |
| Mar 11 | `20260311_legal_consent.sql` | User consent tracking |
| Mar 11 | `20260311_player_data_pipeline.sql` | Legacy pipeline tables (now archived) |
| Mar 11 | `20260311_quiniela_pool_types.sql` | Pool type variants |
| Mar 11 | `20260311_usage_controls.sql` | Rate limiting / usage quotas |
| Mar 12 | `20260312_analytics_rpc.sql` | `execute_readonly_sql` RPC function |
| Mar 12 | `20260312_player_warehouse.sql` | **Warehouse**: players, player_career, player_tournament, player_aliases, schema_metadata, pipeline_runs |
| Mar 12 | `20260312_unaccent_search.sql` | Accent-insensitive search extension |

---

## Appendix B: Reconciliation Decision Matrix

When sources disagree on a field, this is the resolution logic:

```
Is the field CRITICAL (club, league, DOB, nationality)?
  ├─ YES → Is there majority consensus (2+ sources agree)?
  │    ├─ YES, and Transfermarkt is in the majority → AUTO-RESOLVE (accept TM)
  │    ├─ YES, and GPT+Squads agree, TM is outlier → AUTO-RESOLVE (accept GPT, TM likely stale)
  │    └─ NO (all sources differ) → BLOCK PLAYER — requires human review
  └─ NO (IMPORTANT or INFORMATIONAL)
       └─ Accept highest-priority source (TM > Bios > Squads > GPT)
          └─ Log as flagged for review
```
