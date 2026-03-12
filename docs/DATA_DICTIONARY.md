# La Copa Mundo — Data Dictionary

> Comprehensive reference for every table, column, relationship, and JSONB structure
> in the La Copa Mundo database. This document serves two audiences:
>
> 1. **Developers** — understanding the schema for feature work
> 2. **Capi Analytics Mode** — the machine-readable `schema_metadata` table is derived from this document

**Last updated:** 2026-03-11
**Database:** Supabase (PostgreSQL 15)
**Migration count:** 21 files in `la-copa-mundo/supabase/migrations/`

---

## Table of Contents

1. [Core Tournament Tables](#1-core-tournament-tables)
2. [Player Warehouse](#2-player-warehouse)
3. [User & Profile Tables](#3-user--profile-tables)
4. [Capi AI System](#4-capi-ai-system)
5. [Social Layer (Groups)](#5-social-layer-groups)
6. [Quiniela Prediction Game](#6-quiniela-prediction-game)
7. [Predictions (Simple)](#7-predictions-simple)
8. [Premium & Billing](#8-premium--billing)
9. [API Access](#9-api-access)
10. [Analytics & Feedback](#10-analytics--feedback)
11. [Admin & Config](#11-admin--config)
12. [Legal & Compliance](#12-legal--compliance)
13. [Legacy / Pipeline Tables](#13-legacy--pipeline-tables)
14. [Custom Enums](#14-custom-enums)
15. [Helper Functions](#15-helper-functions)
16. [JSONB Field Structures](#16-jsonb-field-structures)
17. [Data Lineage](#17-data-lineage)

---

## 1. Core Tournament Tables

### `cities`
**16 host cities across US, Mexico, and Canada.**
Seeded from FIFA official data. Static after initial load.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Auto-generated |
| `slug` | TEXT | NOT NULL, UNIQUE | URL-safe identifier (e.g., `mexico-city`) |
| `name_en` | TEXT | NOT NULL | English name |
| `name_es` | TEXT | NOT NULL | Spanish name |
| `country` | TEXT | NOT NULL | `'US'`, `'MX'`, or `'CA'` |
| `state` | TEXT | NOT NULL | State/province |
| `timezone` | TEXT | NOT NULL | IANA timezone (e.g., `America/Mexico_City`) |
| `lat` | DOUBLE PRECISION | NOT NULL | Latitude |
| `lng` | DOUBLE PRECISION | NOT NULL | Longitude |
| `airport_code` | TEXT | NOT NULL | IATA code (e.g., `MEX`) |
| `description_en` | TEXT | nullable | City description (EN) |
| `description_es` | TEXT | nullable | City description (ES) |
| `hero_image` | TEXT | nullable | URL to hero image |
| `created_at` | TIMESTAMPTZ | default NOW() | Row creation timestamp |

**RLS:** Public read. No user writes.
**Indexes:** None beyond PK + UNIQUE slug.

---

### `venues`
**Stadiums hosting World Cup matches.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Auto-generated |
| `slug` | TEXT | NOT NULL, UNIQUE | URL-safe identifier |
| `name` | TEXT | NOT NULL | Stadium name (single language) |
| `city_id` | UUID | NOT NULL, FK → cities | Host city |
| `capacity` | INTEGER | NOT NULL | Seating capacity |
| `address` | TEXT | NOT NULL | Street address |
| `lat` | DOUBLE PRECISION | NOT NULL | Latitude |
| `lng` | DOUBLE PRECISION | NOT NULL | Longitude |
| `image` | TEXT | nullable | Stadium image URL |
| `description_en` | TEXT | nullable | Description (EN) |
| `description_es` | TEXT | nullable | Description (ES) |
| `created_at` | TIMESTAMPTZ | default NOW() | |

**RLS:** Public read.
**FK:** `city_id` → `cities(id)` CASCADE

---

### `teams`
**48 national teams in the 2026 World Cup.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `slug` | TEXT | NOT NULL, UNIQUE | URL-safe (e.g., `argentina`) |
| `name_en` | TEXT | NOT NULL | English name |
| `name_es` | TEXT | NOT NULL | Spanish name |
| `code` | TEXT | NOT NULL, UNIQUE | FIFA 3-letter code (e.g., `ARG`) |
| `group_letter` | TEXT | NOT NULL | `'A'` through `'L'` (12 groups) |
| `fifa_ranking` | INTEGER | nullable | Current FIFA ranking |
| `confederation` | TEXT | NOT NULL | `UEFA`, `CONMEBOL`, `CONCACAF`, etc. |
| `flag_url` | TEXT | nullable | Flag image URL |
| `description_en` | TEXT | nullable | Team description (EN) |
| `description_es` | TEXT | nullable | Team description (ES) |
| `created_at` | TIMESTAMPTZ | default NOW() | |

**RLS:** Public read.
**Key relationship:** `teams.code` links to `player_tournament.wc_team_code`

---

### `matches`
**104 matches: 48 group stage + 56 knockout.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `match_number` | INTEGER | NOT NULL, UNIQUE | Sequential match number (1–104) |
| `stage` | match_stage (enum) | NOT NULL | `GROUP`, `ROUND_OF_32`, `ROUND_OF_16`, `QUARTER_FINAL`, `SEMI_FINAL`, `THIRD_PLACE`, `FINAL` |
| `group_letter` | TEXT | nullable | Only for group stage matches |
| `home_team_id` | UUID | nullable, FK → teams | NULL until knockout draw |
| `away_team_id` | UUID | nullable, FK → teams | NULL until knockout draw |
| `venue_id` | UUID | NOT NULL, FK → venues | Stadium |
| `kickoff_utc` | TIMESTAMPTZ | NOT NULL | UTC kickoff time |
| `status` | match_status (enum) | NOT NULL, default `SCHEDULED` | `SCHEDULED`, `LIVE`, `COMPLETED`, `POSTPONED`, `CANCELLED` |
| `home_score` | INTEGER | nullable | NULL until match starts |
| `away_score` | INTEGER | nullable | NULL until match starts |
| `created_at` | TIMESTAMPTZ | default NOW() | |
| `updated_at` | TIMESTAMPTZ | auto-updated | Via trigger |

**RLS:** Public read.
**Triggers:** `matches_updated_at` — auto-updates `updated_at` on any change.

---

## 2. Player Warehouse

The player warehouse uses a **static/semi-static/dynamic** architecture to separate data by volatility. This enables efficient refresh strategies and clear ownership.

### `players`
**Canonical player identity. Written once during enrichment. Never updated by pipelines.**
Volatility: **STATIC**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | Canonical player ID |
| `full_legal_name` | TEXT | NOT NULL | Full legal name (e.g., `Lionel Andrés Messi Cuccittini`) |
| `known_as` | TEXT | NOT NULL | Common name (e.g., `Messi`) |
| `date_of_birth` | DATE | nullable | |
| `birth_city` | TEXT | nullable | |
| `birth_country` | TEXT | nullable | |
| `height_cm` | INT | nullable | Height in centimeters |
| `preferred_foot` | TEXT | nullable | `'Left'`, `'Right'`, or `'Both'` (CHECK constraint) |
| `nationality_primary` | TEXT | NOT NULL | Primary nationality |
| `nationality_secondary` | TEXT | nullable | Dual nationality |
| `languages_spoken` | TEXT[] | default `'{}'` | Array of languages |
| `nicknames` | JSONB | default `'[]'` | See [JSONB: nicknames](#playersnicknames) |
| `origin_story_en` | TEXT | nullable | Bilingual origin story |
| `origin_story_es` | TEXT | nullable | |
| `career_summary_en` | TEXT | nullable | Bilingual career summary |
| `career_summary_es` | TEXT | nullable | |
| `breakthrough_moment` | JSONB | nullable | See [JSONB: breakthrough_moment](#playersbreakthrough_moment) |
| `career_defining_quote` | JSONB | nullable | See [JSONB: career_defining_quote](#playerscareer_defining_quote) |
| `famous_quote_about` | JSONB | nullable | See [JSONB: famous_quote_about](#playersfamous_quote_about) |
| `biggest_controversy` | JSONB | nullable | See [JSONB: biggest_controversy](#playersbiggest_controversy) |
| `celebration_style` | TEXT | nullable | Signature celebration |
| `off_field_interests` | TEXT[] | default `'{}'` | Hobbies, interests |
| `charitable_work` | TEXT | nullable | Philanthropy |
| `superstitions` | TEXT[] | default `'{}'` | |
| `tattoo_meanings` | TEXT[] | default `'{}'` | |
| `fun_facts` | TEXT[] | default `'{}'` | |
| `social_media` | JSONB | default `'{}'` | See [JSONB: social_media](#playerssocial_media) |
| `music_taste` | TEXT | nullable | |
| `fashion_brands` | TEXT | nullable | |
| `injury_prone` | BOOLEAN | nullable | |
| `notable_injuries` | JSONB | default `'[]'` | See [JSONB: notable_injuries](#playersnotable_injuries) |
| `photo_url` | TEXT | nullable | Player photo URL |
| `name_search` | TEXT | GENERATED | `lower(unaccent(full_legal_name || ' ' || known_as))` — for full-text search |
| `data_confidence` | TEXT | nullable | `'high'`, `'medium'`, or `'low'` |
| `data_gaps` | TEXT[] | default `'{}'` | Missing data fields |
| `enriched_at` | TIMESTAMPTZ | nullable | When enrichment pipeline ran |
| `created_at` | TIMESTAMPTZ | default NOW() | |

**Indexes:** GIN on `name_search` (full-text), `nationality_primary`, `data_confidence`
**RLS:** Public read, service role write.

---

### `player_aliases`
**Cross-source linking. Maps external IDs and alternate names to canonical players.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | BIGSERIAL | PK | |
| `player_id` | UUID | NOT NULL, FK → players | Canonical player |
| `alias_type` | TEXT | NOT NULL | `'transfermarkt_id'`, `'apif_id'`, `'alternate_name'`, `'nickname'`, etc. |
| `alias_value` | TEXT | NOT NULL | The external ID or alternate name |

**UNIQUE:** `(alias_type, alias_value)` — each external ID maps to exactly one canonical player.
**Indexes:** `player_id`, `(alias_type, alias_value)`

---

### `player_career`
**Semi-static career data. Updated per transfer window (~2x/year).**
Volatility: **SEMI-STATIC**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `player_id` | UUID | PK, FK → players | 1:1 with players |
| `current_club` | TEXT | nullable | Current club team name |
| `current_league` | TEXT | nullable | Current domestic league |
| `current_jersey_number` | INT | nullable | Club jersey number |
| `position_primary` | TEXT | nullable | `'Goalkeeper'`, `'Defender'`, `'Midfielder'`, `'Forward'` |
| `position_secondary` | TEXT | nullable | Secondary position |
| `contract_expires` | DATE | nullable | |
| `agent` | TEXT | nullable | Agent/agency name |
| `estimated_value_eur` | BIGINT | nullable | Market value in EUR |
| `endorsement_brands` | TEXT[] | default `'{}'` | Sponsor brands |
| `career_trajectory` | JSONB | default `'[]'` | See [JSONB: career_trajectory](#player_careercareer_trajectory) |
| `major_trophies` | TEXT[] | default `'{}'` | Trophy names |
| `records_held` | TEXT[] | default `'{}'` | Records held |
| `style_summary_en` | TEXT | nullable | Playing style (EN) |
| `style_summary_es` | TEXT | nullable | Playing style (ES) |
| `signature_moves` | TEXT[] | default `'{}'` | |
| `strengths` | TEXT[] | default `'{}'` | Playing strengths |
| `weaknesses` | TEXT[] | default `'{}'` | Playing weaknesses |
| `comparable_to` | TEXT | nullable | Style comparison player |
| `best_partnership` | TEXT | nullable | Best on-field partner |
| `updated_at` | TIMESTAMPTZ | default NOW() | Last refresh |
| `refresh_source` | TEXT | nullable | Which pipeline refreshed this |

**Indexes:** `current_club`, `current_league`, `position_primary`, `estimated_value_eur`

---

### `player_tournament`
**Dynamic World Cup 2026 data. Updated during tournament (daily/hourly).**
Volatility: **DYNAMIC**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `player_id` | UUID | PK, FK → players | 1:1 with players |
| `wc_team_code` | TEXT | NOT NULL | FIFA 3-letter code (links to `teams.code`) |
| `jersey_number` | INT | nullable | WC squad jersey number |
| `captain` | BOOLEAN | default FALSE | Is team captain |
| `in_squad` | BOOLEAN | default TRUE | Currently in squad |
| `international_caps` | INT | nullable | Total international appearances |
| `international_goals` | INT | nullable | Total international goals |
| `international_debut` | TEXT | nullable | Debut description |
| `tournament_role_en` | TEXT | nullable | Role narrative (EN) |
| `tournament_role_es` | TEXT | nullable | Role narrative (ES) |
| `narrative_arc_en` | TEXT | nullable | Story arc (EN) |
| `narrative_arc_es` | TEXT | nullable | Story arc (ES) |
| `injury_fitness_status` | TEXT | nullable | Current fitness |
| `wc_qualifying_contribution` | TEXT | nullable | Qualifying stats |
| `world_cup_goals` | INT | default 0 | Career WC goals |
| `champions_league_goals` | INT | default 0 | Career CL goals |
| `derby_performances_en` | TEXT | nullable | Big derby record (EN) |
| `derby_performances_es` | TEXT | nullable | Big derby record (ES) |
| `clutch_moments` | JSONB | default `'[]'` | See [JSONB: clutch_moments](#player_tournamentclutch_moments) |
| `previous_wc_appearances` | JSONB | default `'[]'` | See [JSONB: previous_wc_appearances](#player_tournamentprevious_wc_appearances) |
| `host_city_connection` | TEXT | nullable | Connection to a host city |
| `group_stage_stats` | JSONB | nullable | Live group stage stats |
| `knockout_stats` | JSONB | nullable | Live knockout stats |
| `updated_at` | TIMESTAMPTZ | default NOW() | |

**Indexes:** `wc_team_code`, `in_squad` (partial, WHERE TRUE)

---

### `schema_metadata`
**Machine-readable data dictionary for Capi Analytics Mode.**
Capi reads this table to discover which fields exist, what they mean, and how to query them.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | BIGSERIAL | PK | |
| `table_name` | TEXT | NOT NULL | Source table |
| `column_name` | TEXT | NOT NULL | Column name |
| `description_en` | TEXT | NOT NULL | Human-readable description (EN) |
| `description_es` | TEXT | NOT NULL | Human-readable description (ES) |
| `data_type` | TEXT | NOT NULL | PostgreSQL type |
| `example_value` | TEXT | nullable | Example value for context |
| `is_filterable` | BOOLEAN | default FALSE | Can be used in WHERE clauses |
| `is_sortable` | BOOLEAN | default FALSE | Can be used in ORDER BY |
| `is_aggregatable` | BOOLEAN | default FALSE | Can be used in GROUP BY / COUNT / SUM / AVG |
| `analytics_hint` | TEXT | nullable | Guidance for Capi on how to use this field |
| `unit` | TEXT | nullable | Measurement unit (`'EUR'`, `'cm'`, `'goals'`, etc.) |
| `category` | TEXT | NOT NULL | Grouping: `'identity'`, `'career'`, `'style'`, `'tournament'`, `'market'`, `'story'`, `'core'` |
| `volatility` | TEXT | NOT NULL | `'static'`, `'semi_static'`, `'dynamic'` |

**UNIQUE:** `(table_name, column_name)`

---

### `pipeline_runs`
**Audit trail for every pipeline execution.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `pipeline_name` | TEXT | NOT NULL | e.g., `'enrichment'`, `'dedup'`, `'sync'` |
| `run_type` | TEXT | nullable | `'full'`, `'incremental'`, `'enrichment'`, `'refresh'`, `'dedup'`, `'sync'` |
| `started_at` | TIMESTAMPTZ | default NOW() | |
| `completed_at` | TIMESTAMPTZ | nullable | |
| `status` | TEXT | default `'running'` | `'running'`, `'completed'`, `'failed'` |
| `records_in` | INT | nullable | Input record count |
| `records_out` | INT | nullable | Output record count |
| `records_updated` | INT | nullable | Updated records |
| `error_message` | TEXT | nullable | Error details on failure |
| `cost_usd` | NUMERIC(8,4) | nullable | API cost in USD |
| `tokens_used` | INT | nullable | Total tokens consumed |
| `metadata` | JSONB | default `'{}'` | Arbitrary pipeline metadata |

---

## 3. User & Profile Tables

### `profiles`
**Extends Supabase Auth. Auto-created via `handle_new_user()` trigger.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK, FK → auth.users | Same as Supabase auth user ID |
| `first_name` | TEXT | nullable | From auth metadata |
| `last_name` | TEXT | nullable | From auth metadata |
| `display_name` | TEXT | nullable | Shown in UI |
| `avatar_url` | TEXT | nullable | Profile picture (Supabase Storage) |
| `gender` | TEXT | nullable | `'male'`, `'female'`, `'non-binary'`, `'prefer-not-to-say'` |
| `favorite_team_id` | UUID | nullable, FK → teams | User's favorite WC team |
| `preferred_locale` | TEXT | default `'en'` | `'en'` or `'es'` |
| `onboarding_completed` | BOOLEAN | default FALSE | |
| `is_premium` | BOOLEAN | default FALSE | Premium subscription flag |
| `is_admin` | BOOLEAN | default FALSE | Admin access flag |
| `is_curator` | BOOLEAN | default FALSE | Curator role flag |
| `stripe_customer_id` | TEXT | nullable, UNIQUE | Stripe customer ID |
| `free_questions_today` | INTEGER | default 0 | Daily free Capi question counter |
| `last_question_date` | DATE | nullable | For daily reset logic |
| `terms_accepted_at` | TIMESTAMPTZ | nullable | Legal consent timestamp |
| `age_confirmed` | BOOLEAN | default FALSE | Age verification |
| `privacy_accepted_at` | TIMESTAMPTZ | nullable | Privacy policy consent |
| `created_at` | TIMESTAMPTZ | default NOW() | |
| `updated_at` | TIMESTAMPTZ | auto-updated | Via trigger |

**RLS:** Users can read/update own profile. Admins have broader access via service role.
**Triggers:** `profiles_updated_at`, `trg_record_signup_consent`

---

### `email_subscribers`
**Pre-launch email collection.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `email` | TEXT | NOT NULL, UNIQUE | Subscriber email |
| `locale` | TEXT | default `'en'` | `'en'` or `'es'` |
| `source` | TEXT | default `'coming_soon'` | Signup source |
| `subscribed_at` | TIMESTAMPTZ | default NOW() | |
| `unsubscribed_at` | TIMESTAMPTZ | nullable | NULL = still subscribed |

---

## 4. Capi AI System

### `chat_messages`
**Individual chat messages between users and Capi.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | nullable, FK → auth.users | NULL for anonymous |
| `session_id` | TEXT | NOT NULL | Groups messages in a conversation |
| `role` | TEXT | NOT NULL | `'user'` or `'assistant'` |
| `content` | TEXT | NOT NULL | Message text |
| `model_used` | TEXT | nullable | AI model used (e.g., `claude-sonnet-4-5-20250929`) |
| `tokens_used` | INTEGER | nullable | Tokens consumed |
| `created_at` | TIMESTAMPTZ | default NOW() | |

---

### `capi_conversations`
**Session-level conversation logs with intelligence signals.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | nullable, FK → auth.users | |
| `session_id` | TEXT | NOT NULL | |
| `messages` | JSONB | NOT NULL | Full conversation messages |
| `topics` | TEXT[] | nullable | Extracted topic tags |
| `language` | TEXT | nullable | Detected language |
| `city_interest` | TEXT[] | nullable | Cities mentioned/interested in |
| `team_interest` | TEXT[] | nullable | Teams mentioned/interested in |
| `spending_signals` | TEXT[] | nullable | Purchase intent signals |
| `message_count` | INT | nullable | Messages in session |
| `duration_seconds` | INT | nullable | Session duration |
| `user_agent` | TEXT | nullable | Browser user agent |
| `ip_hash` | TEXT | nullable | Hashed IP for anonymous |
| `input_tokens` | INTEGER | default 0 | Total input tokens |
| `output_tokens` | INTEGER | default 0 | Total output tokens |
| `created_at` | TIMESTAMPTZ | default NOW() | |

**Indexes:** GIN on `topics`, `city_interest`, `team_interest`; `language`, `created_at DESC`

---

### `capi_knowledge`
**Curated knowledge snippets that power Capi's system prompt.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `category` | TEXT | NOT NULL | `'groups'`, `'venues'`, `'schedule'`, `'facts'`, `'predictions'`, `'cities'`, `'rules'` |
| `key` | TEXT | NOT NULL | Unique within category (e.g., `'group_a'`) |
| `content` | TEXT | NOT NULL | The knowledge snippet |
| `source` | TEXT | nullable | Source URL or reference |
| `is_active` | BOOLEAN | default TRUE | Soft-disable toggle |
| `updated_by` | UUID | nullable, FK → auth.users | Last editor |
| `created_at` | TIMESTAMPTZ | default NOW() | |
| `updated_at` | TIMESTAMPTZ | auto-updated | |

**UNIQUE:** `(category, key)`

---

### `capi_knowledge_history`
**Audit trail for every knowledge change.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `knowledge_id` | UUID | NOT NULL, FK → capi_knowledge | |
| `old_content` | TEXT | nullable | Previous content |
| `new_content` | TEXT | NOT NULL | New content |
| `changed_by` | UUID | nullable, FK → auth.users | |
| `reason` | TEXT | nullable | Change reason |
| `created_at` | TIMESTAMPTZ | default NOW() | |

---

### `capi_knowledge_corrections`
**Curator-proposed corrections to Capi's knowledge. Pending admin review.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `knowledge_id` | UUID | nullable, FK → capi_knowledge | NULL for proposed new entries |
| `category` | TEXT | NOT NULL | |
| `key` | TEXT | NOT NULL | |
| `current_content` | TEXT | nullable | Existing content |
| `proposed_content` | TEXT | NOT NULL | Proposed replacement |
| `reason` | TEXT | nullable | |
| `source` | TEXT | nullable | Source reference |
| `status` | TEXT | NOT NULL, default `'pending'` | `'pending'`, `'approved'`, `'rejected'` |
| `proposed_by` | UUID | NOT NULL, FK → auth.users | |
| `reviewed_by` | UUID | nullable, FK → auth.users | |
| `review_note` | TEXT | nullable | |
| `created_at` | TIMESTAMPTZ | default NOW() | |
| `reviewed_at` | TIMESTAMPTZ | nullable | |

---

## 5. Social Layer (Groups)

### `groups`
**User-created social groups for watching matches together.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `name` | TEXT | NOT NULL | 2–60 characters |
| `slug` | TEXT | NOT NULL, UNIQUE | URL-safe, auto-generated |
| `description` | TEXT | default `''` | |
| `avatar_emoji` | TEXT | default `'⚽'` | Group icon |
| `owner_id` | UUID | NOT NULL, FK → auth.users | Creator |
| `is_public` | BOOLEAN | default TRUE | Discoverable in search |
| `max_members` | INTEGER | default 50 | |
| `created_at` | TIMESTAMPTZ | default NOW() | |
| `updated_at` | TIMESTAMPTZ | auto-updated | |

---

### `group_members`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `group_id` | UUID | NOT NULL, FK → groups | |
| `user_id` | UUID | NOT NULL, FK → auth.users | |
| `role` | group_role (enum) | NOT NULL, default `'member'` | `'owner'`, `'admin'`, `'member'` |
| `joined_at` | TIMESTAMPTZ | default NOW() | |

**UNIQUE:** `(group_id, user_id)`

---

### `group_invites`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `group_id` | UUID | NOT NULL, FK → groups | |
| `invited_by` | UUID | NOT NULL, FK → auth.users | |
| `invited_user_id` | UUID | nullable, FK → auth.users | NULL for link-based invites |
| `invite_code` | TEXT | NOT NULL, UNIQUE | Random hex code |
| `status` | invite_status (enum) | NOT NULL, default `'pending'` | `'pending'`, `'accepted'`, `'declined'`, `'expired'` |
| `expires_at` | TIMESTAMPTZ | default NOW() + 7 days | |
| `created_at` | TIMESTAMPTZ | default NOW() | |

---

### `group_messages`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `group_id` | UUID | NOT NULL, FK → groups | |
| `user_id` | UUID | NOT NULL, FK → auth.users | |
| `content` | TEXT | NOT NULL | 1–2000 characters |
| `is_capi` | BOOLEAN | default FALSE | TRUE when sent by Capi AI |
| `created_at` | TIMESTAMPTZ | default NOW() | |

---

## 6. Quiniela Prediction Game

### `quiniela_pools`
**Private prediction pools. Three types: single_match, round, tournament_winner.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `name` | TEXT | NOT NULL | Pool name (max 50 chars) |
| `description` | TEXT | nullable | Max 200 chars |
| `invite_code` | TEXT | UNIQUE, NOT NULL | Random hex for sharing |
| `creator_id` | UUID | NOT NULL, FK → auth.users | |
| `pool_type` | TEXT | NOT NULL, default `'round'` | `'single_match'`, `'round'`, `'tournament_winner'` |
| `target_match_id` | UUID | nullable, FK → matches | Required for `single_match` pools |
| `round_stages` | TEXT[] | nullable | Required for `round` pools (e.g., `{'GROUP','ROUND_OF_16'}`) |
| `entry_amount` | NUMERIC(10,2) | default 0 | Buy-in amount |
| `currency` | TEXT | default `'USD'` | `'USD'`, `'MXN'`, `'CAD'`, `'EUR'` |
| `max_members` | INT | default 50 | 1–200 |
| `is_active` | BOOLEAN | default TRUE | |
| `scoring_rules` | JSONB | default `'{}'` | Custom scoring overrides |
| `created_at` | TIMESTAMPTZ | default NOW() | |
| `updated_at` | TIMESTAMPTZ | default NOW() | |

**Check constraints:** `single_match` requires `target_match_id`; `round` requires `round_stages`; `tournament_winner` requires both NULL.

---

### `quiniela_pool_members`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `pool_id` | UUID | NOT NULL, FK → quiniela_pools | |
| `user_id` | UUID | NOT NULL, FK → auth.users | |
| `role` | TEXT | default `'member'` | `'admin'` or `'member'` |
| `display_name` | TEXT | nullable | Max 30 chars |
| `joined_at` | TIMESTAMPTZ | default NOW() | |

**UNIQUE:** `(pool_id, user_id)`

---

### `quiniela_bet_types`
**Prediction categories. Seeded with 4 types.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | TEXT | PK | `'match_winner'`, `'exact_score'`, `'group_winner'`, `'tournament_winner'` |
| `name_en` | TEXT | NOT NULL | |
| `name_es` | TEXT | NOT NULL | |
| `description_en` | TEXT | nullable | |
| `description_es` | TEXT | nullable | |
| `points_correct` | INT | NOT NULL | Points for correct prediction |
| `points_partial` | INT | default 0 | Points for partial match |
| `scope` | TEXT | NOT NULL | `'match'`, `'group'`, `'tournament'` |
| `available_from` | match_stage | default `'GROUP'` | When this bet type becomes available |

---

### `quiniela_bets`
**Individual user predictions.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `pool_id` | UUID | NOT NULL, FK → quiniela_pools | |
| `user_id` | UUID | NOT NULL, FK → auth.users | |
| `bet_type_id` | TEXT | NOT NULL, FK → quiniela_bet_types | |
| `match_id` | UUID | nullable, FK → matches | NULL for tournament-level bets |
| `group_letter` | TEXT | nullable | `'A'` through `'L'` |
| `prediction` | JSONB | NOT NULL | See [JSONB: prediction](#quiniela_betsprediction) |
| `points_awarded` | INT | default 0 | |
| `is_scored` | BOOLEAN | default FALSE | |
| `created_at` | TIMESTAMPTZ | default NOW() | |
| `updated_at` | TIMESTAMPTZ | default NOW() | |

**UNIQUE:** `(pool_id, user_id, bet_type_id, match_id)`

---

### `quiniela_settlements`
**End-of-pool payment ledger.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `pool_id` | UUID | NOT NULL, FK → quiniela_pools | |
| `from_user_id` | UUID | NOT NULL, FK → auth.users | |
| `to_user_id` | UUID | NOT NULL, FK → auth.users | |
| `amount` | NUMERIC(10,2) | NOT NULL | Must be > 0 |
| `currency` | TEXT | NOT NULL | `'USD'`, `'MXN'`, `'CAD'`, `'EUR'` |
| `is_paid` | BOOLEAN | default FALSE | |
| `paid_at` | TIMESTAMPTZ | nullable | |
| `created_at` | TIMESTAMPTZ | default NOW() | |

---

### `quiniela_crowd_analytics`
**La Tribuna — aggregate prediction data (public).**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `match_id` | UUID | nullable, FK → matches | |
| `group_letter` | TEXT | nullable | |
| `bet_type_id` | TEXT | NOT NULL, FK → quiniela_bet_types | |
| `total_predictions` | INT | default 0 | |
| `prediction_breakdown` | JSONB | default `'{}'` | See [JSONB: prediction_breakdown](#quiniela_crowd_analyticsprediction_breakdown) |
| `updated_at` | TIMESTAMPTZ | default NOW() | |

**UNIQUE:** `(match_id, bet_type_id)`
**RLS:** Public read (anonymous aggregated data).

---

## 7. Predictions (Simple)

### `predictions`
**Simple match score predictions (separate from Quiniela).**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | NOT NULL, FK → auth.users | |
| `match_id` | UUID | NOT NULL, FK → matches | |
| `home_score` | INTEGER | NOT NULL | 0–20 |
| `away_score` | INTEGER | NOT NULL | 0–20 |
| `points_earned` | INTEGER | nullable | NULL until scored. 3=exact, 1=correct result, 0=wrong |
| `created_at` | TIMESTAMPTZ | default NOW() | |
| `updated_at` | TIMESTAMPTZ | auto-updated | |

**UNIQUE:** `(user_id, match_id)`
**Scoring function:** `score_predictions_for_match(match_id)` — called when match completes.

---

## 8. Premium & Billing

### `subscriptions`
**Stripe-backed subscription management.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | NOT NULL, FK → auth.users | One subscription per user |
| `stripe_subscription_id` | TEXT | nullable, UNIQUE | Stripe sub ID |
| `stripe_price_id` | TEXT | nullable | Stripe price ID |
| `plan` | TEXT | NOT NULL, default `'free'` | `'free'` or `'premium'` |
| `status` | TEXT | NOT NULL, default `'active'` | `'active'`, `'trialing'`, `'past_due'`, `'canceled'`, `'unpaid'`, `'incomplete'` |
| `current_period_start` | TIMESTAMPTZ | nullable | |
| `current_period_end` | TIMESTAMPTZ | nullable | |
| `cancel_at_period_end` | BOOLEAN | default FALSE | |
| `created_at` | TIMESTAMPTZ | default NOW() | |
| `updated_at` | TIMESTAMPTZ | default NOW() | |

---

### `capi_usage`
**Daily Capi message counters for rate limiting.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | nullable, FK → auth.users | NULL for anonymous |
| `ip_hash` | TEXT | nullable | For anonymous rate limiting |
| `date` | DATE | NOT NULL, default CURRENT_DATE | |
| `message_count` | INTEGER | NOT NULL, default 0 | Messages sent today |
| `created_at` | TIMESTAMPTZ | default NOW() | |
| `updated_at` | TIMESTAMPTZ | default NOW() | |

**UNIQUE constraints:** `(user_id, date)`, `(ip_hash, date)`
**Function:** `increment_capi_usage(user_id, ip_hash)` returns daily + monthly counts.

---

## 9. API Access

### `api_keys`
**Premium data API keys. One active key per user.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | NOT NULL, FK → auth.users | UNIQUE (one per user) |
| `key_hash` | TEXT | NOT NULL | SHA-256 hash (plaintext never stored) |
| `key_prefix` | TEXT | NOT NULL | First 8 chars for display (`lcm_ab12...`) |
| `name` | TEXT | NOT NULL, default `'Default'` | Key label |
| `created_at` | TIMESTAMPTZ | NOT NULL, default NOW() | |
| `last_used` | TIMESTAMPTZ | nullable | |
| `revoked_at` | TIMESTAMPTZ | nullable | NULL = active |

---

### `api_usage`
**Daily API request counters.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | NOT NULL, FK → auth.users | |
| `date` | DATE | NOT NULL, default CURRENT_DATE | |
| `requests` | INT | NOT NULL, default 0 | |

**UNIQUE:** `(user_id, date)`
**Function:** `increment_api_usage(user_id, daily_limit)` returns boolean (under limit?).

---

## 10. Analytics & Feedback

### `affiliate_clicks`
**Tracks clicks on partner affiliate links.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | nullable, FK → auth.users | |
| `city_slug` | TEXT | nullable | Related city |
| `partner` | TEXT | NOT NULL | Partner name |
| `link_url` | TEXT | NOT NULL | Destination URL |
| `utm_source` | TEXT | nullable | |
| `utm_medium` | TEXT | nullable | |
| `utm_campaign` | TEXT | nullable | |
| `created_at` | TIMESTAMPTZ | default NOW() | |

---

### `feedback`
**User feedback with NPS scoring.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | NOT NULL, FK → auth.users | |
| `nps_score` | INT | nullable | 0–10 Net Promoter Score |
| `categories` | TEXT[] | default `'{}'` | Feedback category tags |
| `free_form` | TEXT | nullable | Open text feedback |
| `type` | TEXT | NOT NULL, default `'general'` | `'general'` or `'theme'` |
| `metadata` | JSONB | default `'{}'` | |
| `created_at` | TIMESTAMPTZ | NOT NULL, default NOW() | |

---

## 11. Admin & Config

### `app_settings`
**Admin-configurable key-value settings.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `key` | TEXT | PK | Setting key (e.g., `'capi_limits'`) |
| `value` | JSONB | NOT NULL | Setting value |
| `updated_at` | TIMESTAMPTZ | default NOW() | |
| `updated_by` | UUID | nullable, FK → profiles | |

**Seed values:**
- `capi_limits`: `{"free_daily": 20, "free_monthly": 100}`
- `capi_cost_rates`: `{"input_per_1m": 3.00, "output_per_1m": 15.00, "model": "claude-sonnet-4-5-20250929"}`

---

### `player_corrections`
**Curator-to-admin workflow for player data fixes.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `player_slug` | TEXT | NOT NULL | Player identifier |
| `team_code` | TEXT | NOT NULL | Team code |
| `field` | TEXT | NOT NULL | `'club'`, `'age'`, `'name'`, `'number'`, `'position'` |
| `current_value` | TEXT | nullable | |
| `proposed_value` | TEXT | NOT NULL | |
| `reason` | TEXT | nullable | |
| `status` | TEXT | NOT NULL, default `'pending'` | `'pending'`, `'approved'`, `'rejected'` |
| `proposed_by` | UUID | NOT NULL, FK → auth.users | |
| `reviewed_by` | UUID | nullable, FK → auth.users | |
| `review_note` | TEXT | nullable | |
| `created_at` | TIMESTAMPTZ | default NOW() | |
| `reviewed_at` | TIMESTAMPTZ | nullable | |

---

## 12. Legal & Compliance

### `consent_log`
**Immutable audit log for legal consent events.**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | PK | |
| `user_id` | UUID | nullable, FK → auth.users | |
| `action` | TEXT | NOT NULL | `'terms_accepted'`, `'privacy_accepted'`, `'age_confirmed'`, `'terms_updated'`, `'account_deleted'` |
| `ip_hash` | TEXT | nullable | |
| `user_agent` | TEXT | nullable | |
| `metadata` | JSONB | default `'{}'` | Includes `terms_version`, timestamps |
| `created_at` | TIMESTAMPTZ | default NOW() | |

**Trigger:** `trg_record_signup_consent` auto-logs when profiles are created with consent flags.

---

## 13. Legacy / Pipeline Tables

These tables exist from the initial data pipeline and may be superseded by the player warehouse.

### `pipeline_players`
**Flat player table from the initial scraping pipeline. Being replaced by the normalized player warehouse (players + player_career + player_tournament).**

### `clubs`
**Club reference data populated by the pipeline.**

### `competitions`
**Competition reference data.**

> These tables are documented in `20260311_player_data_pipeline.sql`. As the warehouse migration completes, these tables will be deprecated.

---

## 14. Custom Enums

| Enum | Values | Used By |
|------|--------|---------|
| `match_stage` | `GROUP`, `ROUND_OF_32`, `ROUND_OF_16`, `QUARTER_FINAL`, `SEMI_FINAL`, `THIRD_PLACE`, `FINAL` | `matches.stage`, `quiniela_bet_types.available_from` |
| `match_status` | `SCHEDULED`, `LIVE`, `COMPLETED`, `POSTPONED`, `CANCELLED` | `matches.status` |
| `group_role` | `owner`, `admin`, `member` | `group_members.role` |
| `invite_status` | `pending`, `accepted`, `declined`, `expired` | `group_invites.status` |

---

## 15. Helper Functions

| Function | Returns | Description |
|----------|---------|-------------|
| `search_players_by_name(search_term, max_results)` | TABLE | Full-text + alias search across players. Used by Capi tools. |
| `get_squad(team_code)` | TABLE | Returns full squad for a WC team, ordered by position. |
| `score_predictions_for_match(match_id)` | INTEGER | Scores all predictions for a completed match. 3=exact, 1=correct result, 0=wrong. |
| `increment_capi_usage(user_id, ip_hash)` | TABLE(daily, monthly) | Upserts daily usage counter, returns daily + monthly totals. |
| `increment_api_usage(user_id, daily_limit)` | BOOLEAN | Increments API counter, returns TRUE if under limit. |
| `handle_new_user()` | TRIGGER | Auto-creates profile row on Supabase auth signup. |
| `generate_group_slug(name)` | TEXT | Generates unique URL-safe slug from group name. |
| `record_signup_consent()` | TRIGGER | Auto-logs consent events when profiles are created. |
| `update_updated_at()` | TRIGGER | Generic auto-update timestamp trigger. |

---

## 16. JSONB Field Structures

### `players.nicknames`
```json
[
  {
    "nickname": "La Pulga",
    "meaning_en": "The Flea",
    "meaning_es": "La Pulga"
  }
]
```

### `players.breakthrough_moment`
```json
{
  "description_en": "Hat-trick on debut vs Villarreal, aged 17",
  "description_es": "Hat-trick en su debut contra Villarreal, a los 17 años",
  "date": "2005-05-01"
}
```

### `players.career_defining_quote`
```json
{
  "quote_en": "I start early, and I stay late...",
  "quote_es": "Empiezo temprano y me quedo tarde...",
  "context": "Post-match interview after 2022 WC Final"
}
```

### `players.famous_quote_about`
```json
{
  "quote_en": "He is the best player I have ever seen",
  "quote_es": "Es el mejor jugador que he visto",
  "attributed_to": "Pep Guardiola"
}
```

### `players.biggest_controversy`
```json
{
  "description_en": "Tax fraud conviction in Spain, 2017",
  "description_es": "Condena por fraude fiscal en España, 2017"
}
```

### `players.social_media`
```json
{
  "instagram": "@leomessi",
  "twitter": "@TeamMessi",
  "tiktok": "@leomessi"
}
```

### `players.notable_injuries`
```json
[
  {
    "injury": "ACL tear",
    "date": "2023-11-15",
    "months_out": 8
  }
]
```

### `player_career.career_trajectory`
```json
[
  {
    "club": "FC Barcelona",
    "years": "2004-2021",
    "appearances": 778,
    "goals": 672
  },
  {
    "club": "Paris Saint-Germain",
    "years": "2021-2023",
    "appearances": 75,
    "goals": 32
  }
]
```

### `player_tournament.clutch_moments`
```json
[
  {
    "description_en": "Last-minute equalizer vs France in 2022 WC Final",
    "description_es": "Gol de empate en el último minuto contra Francia en la final del Mundial 2022",
    "competition": "World Cup 2022",
    "date": "2022-12-18"
  }
]
```

### `player_tournament.previous_wc_appearances`
```json
[
  {
    "year": 2022,
    "host": "Qatar",
    "result": "Champion",
    "goals": 7,
    "appearances": 7
  },
  {
    "year": 2018,
    "host": "Russia",
    "result": "Round of 16",
    "goals": 1,
    "appearances": 4
  }
]
```

### `quiniela_bets.prediction`
Varies by `bet_type_id`:
- **match_winner:** `{"winner": "home" | "away" | "draw"}`
- **exact_score:** `{"home_score": 2, "away_score": 1}`
- **group_winner:** `{"team_id": "uuid-here"}`
- **tournament_winner:** `{"team_id": "uuid-here"}`

### `quiniela_crowd_analytics.prediction_breakdown`
```json
{
  "home": 45,
  "away": 30,
  "draw": 25
}
```
Values are percentages or counts of total predictions.

---

## 17. Data Lineage

```
External Sources
  ├── Transfermarkt (scraping) ──→ pipeline_players (flat)
  ├── API-Football (API) ────────→ pipeline_players (flat)
  └── Claude enrichment ─────────→ enrichment JSONs
                                       │
                                       ▼
                              ┌─── Dedup Pipeline ───┐
                              │   matcher.py          │
                              │   resolver.py         │
                              └───────────────────────┘
                                       │
                                       ▼
                              ┌─── Sync to Supabase ──┐
                              │   sync_to_supabase.py  │
                              │                        │
                              │   players (static)     │
                              │   player_aliases       │
                              │   player_career        │
                              │   player_tournament    │
                              │   schema_metadata      │
                              └────────────────────────┘
                                       │
                                       ▼
                              ┌─── Capi reads via ─────┐
                              │   Supabase client       │
                              │   search_players_by_name│
                              │   get_squad             │
                              │   schema_metadata       │ ← Analytics Mode
                              └────────────────────────┘
```

**Refresh cadence:**
- `players` — Written once during enrichment. Static.
- `player_career` — Transfer windows (~January, ~August) or on-demand.
- `player_tournament` — Daily during World Cup, weekly pre-tournament.
- `teams`, `matches`, `cities`, `venues` — Seeded from FIFA data, updated as draws/schedule change.
- `schema_metadata` — Updated when schema changes. Deployed via seed SQL.
