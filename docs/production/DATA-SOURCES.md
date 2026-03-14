# El Capi — Data Sources

> **Audience**: Engineering / Data Team
> **Last verified**: March 12, 2026
> **Purpose**: Complete reference for every data source feeding El Capi — where it comes from, how we connect, what fields we use, where the data lands, and what's missing.

> **Note (March 14, 2026):** The "632 players" counts in this document reflect the classic pipeline output (`players_golden.json`). The production warehouse now has **1,176 players** across 42 WC squads — the additional 538 came from squad build + APIF sync operations that bypass the enrichment pipeline. Warehouse table counts are in `DATA_LINEAGE.md`.

---

## Table of Contents

1. [Transfermarkt CSVs](#1-transfermarkt-csvs)
2. [Static Squads (players.ts)](#2-static-squads-playersts)
3. [Static Bios (player-bios.ts + bios/*.ts)](#3-static-bios-player-biosts--biosts)
4. [GPT-4o-mini Enrichment](#4-gpt-4o-mini-enrichment)
5. [GPT-4o Verification](#5-gpt-4o-verification)
6. [Supabase (PostgreSQL)](#6-supabase-postgresql)
7. [API-Football](#7-api-football)
8. [Anthropic Claude (Capi Chat)](#8-anthropic-claude-capi-chat)
9. [OpenAI (Pipeline Only)](#9-openai-pipeline-only)
10. [ElevenLabs (Voice)](#10-elevenlabs-voice)
11. [Stripe (Payments)](#11-stripe-payments)
12. [Plausible (Analytics)](#12-plausible-analytics)
13. [Resend (Email)](#13-resend-email)
14. [Source Priority Matrix](#source-priority-matrix)
15. [Environment Variables Reference](#environment-variables-reference)

---

## 1. Transfermarkt CSVs

### Overview

| Item | Detail |
|------|--------|
| **What** | Structured player, club, transfer, and valuation data from [Transfermarkt](https://www.transfermarkt.com/) |
| **Format** | CSV files from the [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) open-source project |
| **Location** | `la-copa-mundo/scripts/pipeline/data/` |
| **Used by** | `el-capi-data/pipeline/ingest/transfermarkt.py`, `el-capi-data/pipeline/reconcile/career_builder.py` |
| **Priority** | **Highest** — most trusted source for structured player identity data |

### Files and Record Counts

| File | Records | Size | Status |
|------|---------|------|--------|
| `players.csv` | 34,370 players | — | **Active** — main ingestion source |
| `clubs.csv` | 451 clubs | — | Loaded but not directly used in pipeline |
| `transfers.csv` | 100,216 transfer records | — | **Active** — used by `career_builder.py` for transfer histories |
| `player_valuations.csv` | 525,308 valuation snapshots | — | Loaded but not used in pipeline |
| `competitions.csv` | 44 competitions | — | Not used |

### Column Schema — `players.csv`

| Column | Type | Used | Maps to |
|--------|------|------|---------|
| `player_id` | int | Yes | `source_id` |
| `first_name` | string | Yes | `first_name` |
| `last_name` | string | Yes | `last_name` |
| `name` | string | Yes | `name` |
| `date_of_birth` | date | Yes | `date_of_birth` (truncated to YYYY-MM-DD) |
| `country_of_citizenship` | string | Yes | `nationality` |
| `country_of_birth` | string | Yes | `country_of_birth` |
| `city_of_birth` | string | Yes | `city_of_birth` |
| `position` | string | Yes | `position` (via `POSITION_MAP`: Attack→FWD, etc.) |
| `sub_position` | string | Yes | `sub_position` |
| `foot` | string | Yes | `foot` |
| `height_in_cm` | float | Yes | `height_cm` (cast to int) |
| `current_club_id` | int | Yes | Filter: `notna()` = active players only |
| `current_club_name` | string | Yes | `current_club_name` |
| `current_club_domestic_competition_id` | string | Yes | Maps to league via `COMPETITION_ID_TO_LEAGUE` |
| `market_value_in_eur` | float | Yes | `market_value_eur` (cast to int) |
| `highest_market_value_in_eur` | float | Yes | `highest_market_value_eur` (cast to int) |
| `image_url` | string | Yes | `photo_url` |
| `url` | string | Yes | `transfermarkt_url` |
| `agent_name` | string | Yes | `agent` |
| `contract_expiration_date` | date | Yes | `contract_expires` (truncated to YYYY-MM-DD) |
| `last_season` | int | No | — |
| `player_code` | string | No | — |

### Column Schema — `transfers.csv` (used by career_builder)

| Column | Used | Purpose |
|--------|------|---------|
| `player_id` | Yes | Join key to match players |
| `transfer_date` | Yes | Chronological ordering |
| `transfer_season` | Yes | Display in career trajectory |
| `from_club_name` | Yes | Transfer origin |
| `to_club_name` | Yes | Transfer destination |
| `transfer_fee` | Yes | Formatted as "€30M", "Free transfer", etc. |
| `player_name` | No | — |
| `from_club_id` / `to_club_id` | No | — |
| `market_value_in_eur` | No | — |

### Connection Method

```python
# el-capi-data/pipeline/config.py
TRANSFERMARKT_DATA_DIR = Path(os.getenv(
    "TRANSFERMARKT_DATA_DIR",
    PROJECT_ROOT / ".." / "la-copa-mundo" / "scripts" / "pipeline" / "data"
))
```

Direct file read via `pandas.read_csv()`. No API connection — static CSV snapshot.

### Data Flow

```
players.csv → transfermarkt.py → DataFrame (34K) → dedup/matcher.py → 632 WC players
transfers.csv → career_builder.py → career_trajectory JSONB per player
                                  ↓
                        players_canonical.json → push_to_supabase.py → player_career.career_trajectory
```

### Known Issues

- **Stale data**: CSVs are a point-in-time snapshot from the transfermarkt-datasets project. Players who transferred after the snapshot date show incorrect clubs (e.g., Luis Díaz showed Liverpool instead of Bayern Munich).
- **No automated refresh**: CSVs must be manually re-downloaded from the source.
- **Source URL**: https://github.com/dcaribou/transfermarkt-datasets — updated periodically by the community.

---

## 2. Static Squads (`players.ts`)

### Overview

| Item | Detail |
|------|--------|
| **What** | Hand-curated official FIFA World Cup 2026 rosters for all 48 national teams |
| **Format** | TypeScript file exporting a `SQUADS` constant |
| **Location** | `la-copa-mundo/src/data/players.ts` (826 lines) |
| **Used by** | `el-capi-data/pipeline/ingest/static_squads.py`, Next.js app (team pages, player pages) |
| **Priority** | 3rd highest — trusted for roster composition but limited field coverage |

### Fields Extracted

| Field | Type | Source in TS | Notes |
|-------|------|-------------|-------|
| `name` | string | `name: "..."` | Full display name |
| `position` | string | `position: "..."` | GK / DEF / MID / FWD |
| `club` | string | `club: "..."` | Current club at time of curation |
| `number` | int | `number: N` | Jersey number |
| `age` | int | `age: N` | Age at time of curation |
| `captain` | bool | `captain: true` | Only present for captain |
| `wc_team_code` | string | Object key (e.g., `ARG`) | 3-letter FIFA country code |

### Connection Method

```python
# el-capi-data/pipeline/ingest/static_squads.py
# Regex-based TypeScript parsing (no full TS parser)
# Pattern: { name: "...", position: "...", club: "...", number: N, age: N }
```

### Data Flow

```
players.ts → static_squads.py → DataFrame (632 WC players)
                                ↓
                     dedup/matcher.py (matched against Transfermarkt)
                                ↓
                     players_canonical.json
```

Also used directly by the Next.js app for team roster pages and player pages (with corrections applied via `player-overrides.ts`).

### Known Issues

- **Manual maintenance**: Requires hand-editing when squads change (injuries, replacements).
- **Limited fields**: Only 6 fields per player — no DOB, no market value, no career history.

---

## 3. Static Bios (`player-bios.ts` + `bios/*.ts`)

### Overview

| Item | Detail |
|------|--------|
| **What** | Hand-curated biographical data for WC 2026 players |
| **Format** | TypeScript files with slug-keyed bio objects |
| **Location** | `la-copa-mundo/src/data/player-bios.ts` (325 lines) + `la-copa-mundo/src/data/bios/` (6 group files) |
| **Used by** | `el-capi-data/pipeline/ingest/static_bios.py`, Next.js app (player detail pages) |
| **Priority** | 2nd highest — hand-curated, high trust for caps/goals/achievements |
| **Total bios** | 636 across all files |

### Bios Directory Structure

| File | Coverage |
|------|----------|
| `player-bios.ts` | Notable players (main file) |
| `bios/groups-a-b.ts` | Groups A & B |
| `bios/groups-c-d.ts` | Groups C & D |
| `bios/groups-e-f.ts` | Groups E & F |
| `bios/groups-g-h.ts` | Groups G & H |
| `bios/groups-i-j.ts` | Groups I & J |
| `bios/groups-k-l.ts` | Groups K & L |

### Fields Extracted

| Field | Type | Regex Pattern | Example |
|-------|------|---------------|---------|
| `height` | string | `height: "..."` | `"1.70 m"` |
| `foot` | string | `foot: "..."` | `"Left"` |
| `birthDate` | string | `birthDate: "..."` | `"1987-06-24"` |
| `birthPlace` | string | `birthPlace: "..."` | `"Rosario, Argentina"` |
| `marketValue` | string | `marketValue: "..."` | `"€35M"` |
| `intlCaps` | int | `intlCaps: N` | `186` |
| `intlGoals` | int | `intlGoals: N` | `109` |
| `previousClubs` | string[] | `previousClubs: [...]` | `["Barcelona", "PSG"]` |
| `achievements` | string[] | `achievements: [...]` | `["7× Ballon d'Or"]` |
| `bio_en` | string | `bio_en: "..."` | English biography text |
| `bio_es` | string | `bio_es: "..."` | Spanish biography text |

### Connection Method

```python
# el-capi-data/pipeline/ingest/static_bios.py
# Regex-based TS parsing: finds "slug": { ... } blocks via brace-counting
# Strips // comments before parsing
```

### Data Flow

```
player-bios.ts + bios/*.ts → static_bios.py → dict[slug] → { height, foot, caps, goals, ... }
                                                ↓
                                     reconcile/merge.py (matched by slug)
                                                ↓
                                     reconciliation_report.json (cross-validated)
```

### Known Issues

- **Slug matching**: Bios are keyed by slug (e.g., `lionel-messi`). Matching to canonical players requires name normalization, which can fail for unusual names.
- **Manual maintenance**: Same as static squads — requires hand-editing.

---

## 4. GPT-4o-mini Enrichment

### Overview

| Item | Detail |
|------|--------|
| **What** | AI-generated rich player profiles with ~100 fields per player |
| **Model** | `gpt-4o-mini` (OpenAI) |
| **Script** | `el-capi-data/run_enrichment.py` |
| **Cost** | ~$0.0055/player → ~$3.50 for 677 players |
| **Priority** | Lowest — known to hallucinate, especially for transfers and recent events |

### Configuration

| Parameter | Value |
|-----------|-------|
| Model | `gpt-4o-mini` |
| Temperature | 0.3 |
| Max tokens | 4,000 |
| Response format | `json_object` |
| Batch delay | 0.3s between requests |
| Checkpoint | `data/intermediate/enrichment_checkpoint.json` |

### Input (per player)

The prompt includes whatever metadata exists from prior pipeline stages:

- Player name, club, nationality, position
- DOB, height, market value, WC team code
- Preferred foot, birth place

### Output Schema (10 sections, ~100 fields)

| Section | Key Fields |
|---------|-----------|
| `identity` | full_legal_name, known_as, nicknames, DOB, birth_city, birth_country, nationality_primary/secondary, languages, height_cm, preferred_foot |
| `career` | current_club, current_league, jersey_number, position_primary/secondary, contract_expires, agent, career_trajectory, international_caps/goals, major_trophies, records_held |
| `playing_style` | style_summary_en/es, signature_moves, strengths, weaknesses, comparable_to, best_partnership |
| `story` | origin_story_en/es, breakthrough_moment, career_defining_quote, famous_quote_about, biggest_controversy |
| `personality` | celebration_style, superstitions, off_field_interests, charitable_work, tattoo_meanings, fun_facts, social_media, music_taste, fashion_brands |
| `world_cup_2026` | previous_wc_appearances, qualifying_contribution, tournament_role_en/es, narrative_arc_en/es, host_city_connection |
| `big_game_dna` | wc_goals, champions_league_goals, derby_performances_en/es, clutch_moments |
| `market` | estimated_value_eur, endorsement_brands, agent |
| `injury_history` | notable_injuries, injury_prone, injury_fitness_status |
| `meta` | data_confidence (high/medium/low), data_gaps |

### Connection Method

```python
# el-capi-data/run_enrichment.py
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[...],
    response_format={"type": "json_object"},
    temperature=0.3,
    max_tokens=4000,
)
```

### Data Flow

```
players_canonical_latest.json (632 WC players)
    → run_enrichment.py → gpt-4o-mini API
    → players_enriched.json (677 enriched players)
    → canonical.py (UUID assignment)
    → players_canonical.json
```

### Known Issues

- **Hallucination risk**: GPT-4o-mini can invent transfer histories, incorrect clubs, wrong statistics. The Luis Díaz incident (showed Liverpool instead of Bayern Munich) was caused by this.
- **Knowledge cutoff**: The model's training data has a cutoff date. Events after that date are unknown to the model.
- **Cost per re-run**: ~$3.50 for a full run (incremental via `--resume` for new players only).

---

## 5. GPT-4o Verification

### Overview

| Item | Detail |
|------|--------|
| **What** | AI-powered fact-checking of 12 critical fields per player |
| **Model** | `gpt-4o` (OpenAI) — higher capability than mini |
| **Script** | `el-capi-data/run_verification.py` + `pipeline/verify/critical_fields.py` |
| **Cost** | ~$0.0037/player → ~$2.35 for 632 players |
| **Results** | 632/632 verified, 1,694 corrections applied |

### Configuration

| Parameter | Value |
|-----------|-------|
| Model | `gpt-4o` |
| Temperature | 0.0 (deterministic) |
| Max tokens | 400 |
| Threads | 1 (rate-limited) |
| Delay | 3.0s between requests |

### Verification Tiers

| Tier | Name | Fields | Auto-apply? |
|------|------|--------|-------------|
| **T1 — Imperdonable** | "Fans don't forgive" | current_club, current_league, nationality_for_wc, position_primary, in_wc_2026_squad | Yes |
| **T2 — Muy Importante** | Should be accurate | date_of_birth, estimated_value_eur | Yes |
| **T3 — Importante** | Nice to have | current_jersey_number, international_caps, international_goals, injury_fitness_status, contract_expires | Yes (with flag) |

### Connection Method

Same OpenAI Python SDK as enrichment, but using `gpt-4o` model.

### Data Flow

```
players_canonical.json → run_verification.py → gpt-4o API
    → verification_results.json (raw responses)
    → verification_diff.json (detected changes)
    → apply_updates.py → players_canonical.json (corrections applied)
    → verification_applied.json (audit trail)
```

### Known Issues

- **Same knowledge cutoff as enrichment**: GPT-4o shares training data limitations with GPT-4o-mini. Cannot verify facts that changed after the cutoff.
- **Rate limiting**: `gpt-4o` has strict rate limits. Must use 1 thread with 3s delay.

---

## 6. Supabase (PostgreSQL)

### Overview

| Item | Detail |
|------|--------|
| **What** | PostgreSQL database hosting all production data |
| **Provider** | [Supabase](https://supabase.com/) |
| **Project URL** | `https://gbtmxqjnnpnileknhrtz.supabase.co` |
| **Used by** | Next.js app (Capi tools, auth, user data), pipeline (`push_to_supabase.py`) |

### Connection Methods

| Context | Client | Key |
|---------|--------|-----|
| Browser (user-facing) | `createBrowserClient()` | `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| Server components | `createServerClient()` + cookies | `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| Admin API routes | `createClient()` | `SUPABASE_SERVICE_ROLE_KEY` |
| Pipeline push | `supabase-py` | `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` |
| Analytics RPC | `execute_readonly_sql` | `service_role` only |

### Production Tables (Warehouse — Capi reads these)

| Table | Records | PK | Purpose |
|-------|---------|-----|---------|
| `players` | 1,176 | `id` (UUID) | Canonical identity, story, personality, `data_confidence` |
| `player_career` | 1,176 | `player_id` (FK) | Club, league, position, style, market value |
| `player_tournament` | 1,176 | `player_id` (FK) | WC 2026 squad data, caps, goals, narrative |
| `player_aliases` | 1,221+ | `id` (serial) | Cross-source name mapping |
| `schema_metadata` | 63 | `id` (serial) | Column descriptions for Analytics Mode |
| `pipeline_runs` | 0 | `id` (UUID) | Audit trail (not yet populated) |

### Application Tables

| Table | Purpose |
|-------|---------|
| `teams` | 48 WC teams with FIFA codes |
| `matches` | WC 2026 match schedule |
| `venues` / `cities` | 16 host cities and stadiums |
| `active_matches` | Live match data (polled by Capi) |
| `profiles` | User accounts with `is_admin`, `is_curator` flags |
| `capi_conversations` | Chat session logging |
| `player_corrections` | Curator-submitted corrections |
| `capi_knowledge` | Knowledge base entries |
| `email_subscribers` | Newsletter signups |
| `predictions` | User match predictions |

### Legacy Tables (Archived — no longer queried)

| Table | Replaced by |
|-------|------------|
| `pipeline_players` | `players` + `player_career` + `player_tournament` |
| `clubs` | `player_career.current_club` |
| `player_bios` | `players` narrative fields |
| `player_valuations` | Not migrated (historical data) |
| `transfers` | `player_career.career_trajectory` (JSONB) |

### Push Logic (`push_to_supabase.py`)

```
players_canonical.json → push_to_supabase.py
    → Filter: skip blocked players (from reconciliation_report.json)
    → Transform: nested JSON → flat rows (dates, arrays, JSONB)
    → Upsert: players (on id), player_career (on player_id), player_tournament (on player_id)
    → Insert: player_aliases (skip on conflict)
    → Batch size: 50 rows
```

### RPC Functions

| Function | Access | Purpose |
|----------|--------|---------|
| `execute_readonly_sql(query_text)` | `service_role` only | Run validated SELECT queries (Analytics Mode) |
| `search_players_by_name(search_term, max_results)` | Public | Full-text + alias search |
| `get_squad(team_code)` | Public | Full roster ordered by position |

### Security

- Row-Level Security (RLS) on all tables
- `execute_readonly_sql`: 5s timeout, 2s lock timeout, SELECT-only, mutation keywords blocked
- Analytics: whitelist of 9 tables, LIMIT ≤ 50 enforced client-side

---

## 7. API-Football

### Overview

| Item | Detail |
|------|--------|
| **What** | Real-time football data API (fixtures, squads, player stats) |
| **Provider** | [API-Sports / API-Football](https://www.api-football.com/) |
| **Base URL** | `https://v3.football.api-sports.io` |
| **Auth** | Header: `x-apisports-key: {API_FOOTBALL_KEY}` |
| **Status** | **Key configured, partially integrated** |

### Where It's Used

| Location | Endpoints Called | Status |
|----------|----------------|--------|
| `la-copa-mundo/src/app/api/cron/pipeline-sync/route.ts` | `fixtures?live=all`, `teams`, `players/squads`, `players` | **Exists** — wired for live match sync and squad enrichment |
| `la-copa-mundo/scripts/pipeline/sync_api_football.py` | Squad sync, transfers | **Exists** — standalone script |
| `la-copa-mundo/src/lib/player-photos.ts` | — | Uses `pipeline_players` table (which API-Football can populate) |

### Where It's NOT Used

| Location | Notes |
|----------|-------|
| `el-capi-data/` pipeline | Key in config (`API_FOOTBALL_KEY`) but **zero pipeline code calls it**. Not used for ingestion, enrichment, verification, or reconciliation. |

### What Data Is Available

| Endpoint | Data | Potential Use |
|----------|------|---------------|
| `fixtures` | Live match events, scores, lineups | Live match updates during WC |
| `players` | Current season stats, team, photo | **Could solve stale Transfermarkt problem** |
| `players/squads` | Full squad rosters by team | Squad verification |
| `transfers` | Transfer history | Career trajectory updates |
| `teams` | Team info, logos | Team metadata |

### Known Issues

- **Rate limits**: Free tier allows 100 requests/day. Paid plans scale.
- **Not wired to el-capi-data**: Despite having the key configured, the data pipeline does not use API-Football. This is a missed opportunity — real-time player data from this API could resolve the stale Transfermarkt CSV problem.
- **Cron route exists but untested**: `pipeline-sync/route.ts` has the integration code but it's unclear if the cron job is active.

---

## 8. Anthropic Claude (Capi Chat)

### Overview

| Item | Detail |
|------|--------|
| **What** | LLM powering El Capi — the AI chat assistant |
| **Provider** | [Anthropic](https://www.anthropic.com/) |
| **Model** | Claude (via Anthropic SDK) |
| **Key** | `ANTHROPIC_API_KEY` in `.env.local` |
| **Used by** | `la-copa-mundo/src/app/api/capi/chat/route.ts` |

### How It's Used

- Capi receives user messages and responds via streaming SSE
- System prompt includes player knowledge, personality, language rules, and (for premium) schema reference for Analytics Mode
- Has access to 6 tools (search_players, get_player_details, get_squad, get_live_matches, get_career_history, run_analytics_query)
- All tools are **read-only** — Capi cannot modify any data

### Data Flow

```
User message → /api/capi/chat → Anthropic Claude API (streaming)
    → Tool calls → Supabase warehouse queries → Results
    → Claude formats response → SSE stream to user
    → Conversation logged to capi_conversations table
```

---

## 9. OpenAI (Pipeline Only)

### Overview

| Item | Detail |
|------|--------|
| **What** | GPT models for data enrichment and verification |
| **Provider** | [OpenAI](https://platform.openai.com/) |
| **Key** | `OPENAI_API_KEY` in both `.env` (el-capi-data) and `.env.local` (la-copa-mundo) |
| **Models used** | `gpt-4o-mini` (enrichment), `gpt-4o` (verification) |
| **Used by** | `el-capi-data/run_enrichment.py`, `el-capi-data/run_verification.py` |

Not used for the Capi chat experience — that's Anthropic Claude. OpenAI is used exclusively in the offline data pipeline.

---

## 10. ElevenLabs (Voice)

### Overview

| Item | Detail |
|------|--------|
| **What** | Text-to-speech and speech-to-text for Capi voice features |
| **Provider** | [ElevenLabs](https://elevenlabs.io/) |
| **Keys** | `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` in `.env.local` |
| **Used by** | `la-copa-mundo/src/app/api/voice/tts/`, `la-copa-mundo/src/app/api/voice/stt/` |

### Data Flow

```
User speaks → /api/voice/stt → ElevenLabs STT → text → Capi chat → response text
    → /api/voice/tts → ElevenLabs TTS → audio → user hears Capi speak
```

---

## 11. Stripe (Payments)

### Overview

| Item | Detail |
|------|--------|
| **What** | Payment processing for La Copa Mundo Premium subscriptions |
| **Provider** | [Stripe](https://stripe.com/) |
| **Keys** | `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_PREMIUM_PRICE_ID`, `STRIPE_WEBHOOK_SECRET` |
| **Used by** | `/api/checkout/`, `/api/webhooks/stripe/`, `/api/portal/` |

### Data Flow

```
User → /premium → Stripe Checkout → payment → Stripe webhook
    → /api/webhooks/stripe → update profiles.is_premium = true
    → User gets Analytics Mode, priority access
```

---

## 12. Plausible (Analytics)

### Overview

| Item | Detail |
|------|--------|
| **What** | Privacy-friendly website analytics |
| **Provider** | [Plausible](https://plausible.io/) |
| **Key** | `NEXT_PUBLIC_PLAUSIBLE_DOMAIN=lacopamundo.com` |
| **Used by** | Script tag in root layout |

No data flows from Plausible into the app — it's outbound-only page view tracking.

---

## 13. Resend (Email)

### Overview

| Item | Detail |
|------|--------|
| **What** | Transactional email service |
| **Provider** | [Resend](https://resend.com/) |
| **Key** | `RESEND_API_KEY` |
| **Used by** | `/api/subscribe/` (email capture) |

---

## Source Priority Matrix

When multiple sources provide conflicting values for the same field, this is the trust order:

| Priority | Source | Trust Level | Strengths | Weaknesses |
|----------|--------|-------------|-----------|------------|
| **1** | Transfermarkt CSVs | Highest | Large dataset, structured, real player IDs | Stale (static snapshot), no real-time updates |
| **2** | Static Bios | High | Hand-curated, accurate for caps/goals/achievements | Limited coverage (636 bios), manual maintenance |
| **3** | Static Squads | Medium | Official roster composition | Only 6 fields, manual maintenance |
| **4** | GPT Enrichment | Lowest | Rich narratives, 100+ fields, bilingual | Hallucination risk, knowledge cutoff, no real-time |

### Field-Level Source Authority

| Field | Best Source | Why |
|-------|-----------|-----|
| `date_of_birth` | Transfermarkt | Structured, reliable |
| `nationality` | Transfermarkt | Official citizenship data |
| `current_club` | Transfermarkt (if fresh) / GPT (if TM stale) | TM is structured but can be outdated |
| `current_league` | Derived from club via `COMPETITION_ID_TO_LEAGUE` | Computed, not stored directly |
| `position` | Static Squads → Transfermarkt | Squads use simplified positions (GK/DEF/MID/FWD) |
| `jersey_number` | Static Squads | WC-specific jersey numbers |
| `international_caps/goals` | Static Bios | Hand-curated, most current |
| `career_trajectory` | Transfermarkt `transfers.csv` | Ground truth for transfer history |
| `market_value_eur` | Transfermarkt | Professional valuations |
| `bio narratives` | GPT Enrichment | Only source for rich bilingual narratives |
| `personality, style, fun_facts` | GPT Enrichment | Only source for these fields |

---

## Environment Variables Reference

### `el-capi-data/.env`

| Variable | Service | Required |
|----------|---------|----------|
| `SUPABASE_URL` | Supabase | Yes (for push) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase | Yes (for push) |
| `OPENAI_API_KEY` | OpenAI | Yes (enrichment + verification) |
| `API_FOOTBALL_KEY` | API-Football | Configured but unused by pipeline |
| `TRANSFERMARKT_DATA_DIR` | Local filesystem | Optional (has default) |
| `STATIC_SQUADS_PATH` | Local filesystem | Optional (has default) |

### `la-copa-mundo/.env.local`

| Variable | Service | Required |
|----------|---------|----------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase | Yes |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase | Yes (admin routes) |
| `ANTHROPIC_API_KEY` | Anthropic | Yes (Capi chat) |
| `OPENAI_API_KEY` | OpenAI | Yes (shared with pipeline) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe | Yes (payments) |
| `STRIPE_SECRET_KEY` | Stripe | Yes (payments) |
| `STRIPE_PREMIUM_PRICE_ID` | Stripe | Yes (payments) |
| `STRIPE_WEBHOOK_SECRET` | Stripe | Yes (payments) |
| `RESEND_API_KEY` | Resend | Yes (email) |
| `ELEVENLABS_API_KEY` | ElevenLabs | Yes (voice) |
| `ELEVENLABS_VOICE_ID` | ElevenLabs | Yes (voice) |
| `API_FOOTBALL_KEY` | API-Football | Used by cron/pipeline-sync |
| `CRON_SECRET` | Internal | Yes (cron auth) |
| `NEXT_PUBLIC_PLAUSIBLE_DOMAIN` | Plausible | Yes (analytics) |
| `NEXT_PUBLIC_SITE_URL` | — | Yes (canonical URL) |
| `NEXT_PUBLIC_DEFAULT_LOCALE` | — | Yes (i18n) |
| `GOOGLE_CLIENT_ID` | Google OAuth | Empty (not configured) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth | Empty (not configured) |
