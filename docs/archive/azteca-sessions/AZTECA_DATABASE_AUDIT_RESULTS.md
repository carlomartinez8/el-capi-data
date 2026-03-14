# Azteca Database Audit — Results

**Date:** March 2026  
**Source:** AZTECA_DATABASE_AUDIT.docx (Pelé)  
**Executor:** Azteca — all queries run via psql against Supabase; full output below.

---

## Section 1 — Full Table Inventory

### Query 1.1 — All Tables with Row Counts (pg_stat estimates)

| schemaname | table_name | estimated_rows |
|------------|------------|----------------|
| auth | audit_log_entries | 0 |
| auth | flow_state | 55 |
| auth | identities | 18 |
| auth | mfa_amr_claims | 11 |
| auth | refresh_tokens | 41 |
| auth | schema_migrations | 75 |
| auth | sessions | 11 |
| auth | users | 18 |
| public | active_matches | 7 |
| public | api_keys | 2 |
| public | app_settings | 2 |
| public | capi_conversations | 52 |
| public | capi_knowledge | 0 |
| public | chat_messages | 568 |
| public | cities | 16 |
| public | clubs | 837 |
| public | competitions | 44 |
| public | email_subscribers | 3 |
| public | feedback | 2 |
| public | group_invites | 35 |
| public | group_members | 13 |
| public | group_messages | 181 |
| public | groups | 4 |
| public | matches | 72 |
| public | pipeline_freshness | 11 |
| public | pipeline_players | 65917 |
| public | pipeline_runs | 0 |
| public | player_aliases | 828 |
| public | player_bios | 1841 |
| public | player_career | 638 |
| public | player_corrections | 9 |
| public | player_tournament | 638 |
| public | player_valuations | 525308 |
| public | players | 638 |
| public | predictions | 28 |
| public | profiles | 17 |
| public | quiniela_bet_types | 4 |
| public | quiniela_bets | 39 |
| public | quiniela_pool_members | 7 |
| public | quiniela_pools | 4 |
| public | schema_metadata | 63 |
| public | subscriptions | 2 |
| public | teams | 48 |
| public | transfers | 102381 |
| public | venues | 16 |

*(Plus realtime, storage, vault schemas with migrations/objects. affiliate_clicks, appearances, consent_log, api_usage, quiniela_crowd_analytics, quiniela_settlements = 0.)*

### Query 1.2 — All Schemas

Present: **auth**, **extensions**, **graphql**, **graphql_public**, **public**, **realtime**, **storage**, **vault**, **pgbouncer**. Plus transient **pg_temp_*** and **pg_toast_temp_***. No unexpected schemas (e.g. no raw/staging medallion).

---

## Section 2 — V1 Pipeline Tables

### Query 2.1 — V1 Table Existence and Row Counts (exact COUNT)

| table_name | rows |
|------------|------|
| pipeline_players | 49,287 |
| player_bios | 1,841 |
| clubs | 837 |
| competitions | 44 |
| transfers | 102,381 |
| player_valuations | 525,308 |
| active_matches | 7 |
| pipeline_freshness | 11 |

**All 8 tables exist.** None dropped. *(pg_stat had pipeline_players ~65,917; exact COUNT is 49,287.)*

### Query 2.2 — Wikipedia Bios

- **total_bios:** 1,841  
- **bio_source:** wikipedia 1,841  
- **Sample 5:** Lamine Yamal, Mbappé, Haaland, Bellingham, Vinícius Júnior — all have bio_preview, wikipedia_url, last_fetched 2026-03-11.  
- **Coverage:** total 1,841, has_url 1,841, has_bio 1,841 (100%).

### Query 2.3 — Pipeline Players (V1)

- **Total:** 49,287  
- **Source breakdown:** other 34,370 (Transfermarkt numeric IDs), api_football 14,917.  
- **Null rates (key fields):** total 49,287; has_name 49,287; has_dob 46,845; has_position 49,287; has_club 48,798; has_market_value 32,618; has_nationality 47,012; has_height 43,046; has_photo 49,287.  
- **Column list:** id, name, name_short, date_of_birth, age, nationality, nationality_secondary, position, sub_position, foot, height_cm, current_club_id, current_club_name, jersey_number, market_value_eur, highest_market_value, contract_expires, agent, photo_url, transfermarkt_url, country_of_birth, city_of_birth, is_active, updated_at, name_search (25 columns).

### Query 2.4 — Pipeline Freshness

11 rows. Last updated 2026-03-11; all status OK. Types: api_football_enrichment, api_football_squads, apif_name_resolution, api_football_transfers, wikipedia_bios, api_football_live, transfermarkt_valuations, transfermarkt_transfers, transfermarkt_players, transfermarkt_clubs, transfermarkt_competitions.

### Query 2.5 — Transfers & Valuations

- **total_transfers:** 102,381  
- **total_valuations:** 525,308  
- **latest_transfer:** 2030-06-30  
- **Valuation date range:** earliest 2000-01-20, latest 2026-03-09  
*(Audit doc used `date`; actual column is `valuation_date`.)*

---

## Section 3 — V2 Warehouse Tables

### Query 3.1 — V2 Table Counts

| table_name | rows |
|------------|------|
| players | 638 |
| player_career | 638 |
| player_tournament | 638 |
| player_aliases | 828 |
| schema_metadata | 63 |

### Query 3.2 — V2 Players Column Schema

37 columns: id (uuid), full_legal_name, known_as, date_of_birth, birth_city, birth_country, height_cm, preferred_foot, nationality_primary, nationality_secondary, languages_spoken, nicknames, origin_story_en, origin_story_es, career_summary_en, career_summary_es, breakthrough_moment, career_defining_quote, famous_quote_about, biggest_controversy, celebration_style, off_field_interests, charitable_work, superstitions, tattoo_meanings, fun_facts, social_media, music_taste, fashion_brands, injury_prone, notable_injuries, photo_url, name_search, data_confidence, data_gaps, enriched_at, created_at.

### Query 3.3 — V2 Player Data Quality

**players:** total 638; has_name 638; has_dob 638; has_height 638; has_nationality 638; has_bio_en 475; has_bio_es 475; has_celebration 346; has_fun_facts 286.  
**player_career:** total 638; has_club 638; has_league 565; has_position 638; has_value 638.  
**player_aliases:** alias_type alternate_name 190, transfermarkt_id 638.

### Query 3.4 — V2 Sample Player (Messi)

| known_as | date_of_birth | nationality_primary | height_cm | current_club | current_league | position_primary | estimated_value_eur | international_caps |
|----------|---------------|---------------------|-----------|--------------|----------------|------------------|---------------------|--------------------|
| Lionel Messi | 1987-06-24 | Argentina | 170 | Paris Saint-Germain Football Club | Ligue 1 | Right Winger | 35000000 | 190 |

**Finding:** V2 club is **Paris Saint-Germain** — stale (Messi is at Inter Miami). Confirms club freshness issue.

---

## Section 4 — Application Tables

### Query 4.1 — App Table Row Counts

| table_name | rows |
|------------|------|
| profiles | 17 |
| player_corrections | 9 |
| capi_conversations | 52 |
| predictions | 28 |
| feedback | 2 |
| api_keys | 2 |
| quiniela_pools | 4 |
| capi_knowledge | 0 |

*(Audit doc referenced capi_knowledge_base and capi_team_corrections; ran capi_knowledge only. capi_team_corrections does not exist.)*

### Query 4.2 — Player Corrections

- **By status/field:** approved club 7, pending club 2.  
- **Bad club corrections (market-value-looking proposed_value):** 2 rows — camilo-vargas “€1M to €2M” (approved), david-ospina “€0.5M to €1M” (approved). *(Table uses player_slug, not player_id.)*

---

## Section 5 — Cross-Reference & Integrity

### Query 5.1 — V1 Bios to V2 Players

- **player_bios.player_id sample:** 937958, 342229, 418560, 581678, 371998, … (numeric = Transfermarkt IDs).  
- **player_aliases sample:** UUID player_id, alias_type transfermarkt_id / alternate_name, alias_value numeric or name.  
- **Matchable bios (alias_value = player_id where alias_type in transfermarkt_id/source_id):** 196.  
- **Name matches (bios → pipeline_players → players by known_as = name):** 225.

### Query 5.2 — V1 APIF vs V2

- **apif_players in V1:** 14,917.  
- **V2 players found in V1 by name:** 588 of 638.

### Query 5.3 — Club Freshness Check

**V2 (warehouse) current clubs for big names:**

| known_as | current_club | current_league |
|----------|--------------|----------------|
| Cristiano Ronaldo | Manchester United Football Club | Premier League |
| David Ospina | Società Sportiva Calcio Napoli | Serie A |
| James Rodríguez | Olympiakos… | Super League Greece |
| Lionel Messi | Paris Saint-Germain Football Club | Ligue 1 |
| Luis Díaz | FC Bayern München | Bundesliga |
| Luka Modrić | Associazione Calcio Milan | Serie A |

**V1 pipeline_players (same names):** Ronaldo appears twice — 8198 (Manchester United), apif_874 (Al-Nassr). Others: Messi PSG, Luis Díaz FC Bayern, etc. V1 APIF has fresher club for Ronaldo (Al-Nassr); V2 is stale (Manchester United).

---

## Section 6 — Schema Metadata

### Query 6.1 — All Columns (public)

*(Full output is long; first 80 rows captured. Tables include active_matches, affiliate_clicks, api_keys, api_usage, app_settings, appearances, capi_conversations, capi_knowledge, capi_knowledge_corrections, …)*

### Query 6.2 — Foreign Keys

28 FKs in public. Examples: pipeline_players.current_club_id → clubs.id; player_bios.player_id → pipeline_players.id; player_aliases.player_id → players.id; player_career.player_id → players.id; player_tournament.player_id → players.id; player_valuations.player_id → pipeline_players.id; transfers.player_id → pipeline_players.id; matches home_team_id, away_team_id → teams.id, venue_id → venues.id; venues.city_id → cities.id; quiniela_* → quiniela_pools, matches, quiniela_bet_types; etc.

### Query 6.3 — Indexes

Full list run; includes PKs, idx_pipeline_players_*, idx_career_*, idx_aliases_*, idx_players_*, idx_tournament_*, GIN name search, etc.

### Query 6.4 — RLS Policies

All public tables have RLS; mix of “Anyone can read”, “Users can view own”, “Admins can …”, “Service role full access” where appropriate.

---

## Section 7 — Storage

### Query 7.1 — Table Sizes (public, by total size DESC)

| table_name | total_size | data_size |
|------------|------------|-----------|
| player_valuations | 69 MB | 36 MB |
| pipeline_players | 38 MB | 26 MB |
| transfers | 19 MB | 12 MB |
| players | 1440 kB | 1008 kB |
| player_career | 1120 kB | 904 kB |
| capi_conversations | 720 kB | 72 kB |
| player_bios | 712 kB | 568 kB |
| chat_messages | 656 kB | 360 kB |
| player_tournament | 472 kB | 360 kB |
| player_aliases | 360 kB | 72 kB |
| … (46 tables total) | | |

### Query 7.2 — Database Total Size

**db_size:** 146 MB

---

## Corrections to Audit Doc

- **player_valuations:** date column is `valuation_date`, not `date`.  
- **player_career:** no `international_caps`; that lives in `player_tournament`. Query 3.4 run with JOIN to player_tournament for caps.  
- **pipeline_players:** null-rate query uses `height_cm` and `photo_url` (not height_in_cm / image_url).  
- **player_corrections:** table has `player_slug`, not `player_id`.  
- **capi_team_corrections:** table does not exist; only `capi_knowledge` used in 4.1.

---

## Summary for Pelé

- **V1 data is present and large:** 49,287 pipeline_players (34,370 TM + 14,917 APIF), 1,841 Wikipedia bios (100% URL/bio), 102K transfers, 525K valuations, 837 clubs.  
- **V2 warehouse is current production:** 638 players, 638 career, 638 tournament, 828 aliases, 63 schema_metadata.  
- **Stale clubs confirmed:** Messi PSG in V2; Ronaldo Manchester United in V2 while V1 APIF has Al-Nassr.  
- **Bad corrections:** 2 approved club corrections with market-value strings (camilo-vargas, david-ospina).  
- **Cross-reference:** 196 bios matchable to V2 via transfermarkt_id alias; 225 name matches; 588 V2 players found in V1 by name.  
- **Storage:** 146 MB total; largest tables player_valuations (69 MB), pipeline_players (38 MB), transfers (19 MB).

End of report.
