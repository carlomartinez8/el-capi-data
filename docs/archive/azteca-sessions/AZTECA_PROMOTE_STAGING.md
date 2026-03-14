# AZTECA: Promote Staging to Production Warehouse

**Priority:** HIGH — Execute now
**From:** Pelé (Strategy & PM)
**Date:** March 13, 2026
**Depends on:** `profile_players_staging` (43,447 profiles, 7g passed, Wikipedia enriched)

---

## What we're doing

Loading 43,447 deduped player profiles from `profile_players_staging` into the production warehouse tables:

- **`players`** — canonical identity (currently 677 enriched players)
- **`player_aliases`** — cross-source ID mapping (tm_id, apif_id)
- **`player_career`** — position, club, market value

**Critical rule:** The existing 677 enriched players have bilingual narratives, personality data, and tournament data from GPT enrichment. Their **identity fields** (name, DOB, nationality, photo, etc.) came from the old pipeline and are suspect — staging data OVERWRITES those. Their **enrichment fields** (stories, personality, tournament narratives) don't exist in staging and are expensive to reproduce — those stay untouched.

---

## SQL Execution Order

| Step | Action |
|------|--------|
| 0 | Add curation columns to `players` |
| 1 | Discover overlap between staging and existing warehouse |
| 2 | Update existing players (fill NULL identity gaps only) |
| 3 | Insert new players from staging |
| 4 | Insert player_aliases for all staging profiles |
| 5 | Insert/update player_career |
| 6 | Report |
| **7** | **Post-load duplicate detection** — flag pre-existing players not matched to staging that may be duplicates of newly loaded records |

---

### Step 0: Add curation columns to players table

The warehouse doesn't have curation fields yet. We need them for the curation queue.

```sql
ALTER TABLE players
ADD COLUMN IF NOT EXISTS needs_curation BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS curation_reason TEXT,
ADD COLUMN IF NOT EXISTS curation_resolved_by TEXT,
ADD COLUMN IF NOT EXISTS curation_resolved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS wikipedia_url TEXT,
ADD COLUMN IF NOT EXISTS wikipedia_bio TEXT,
ADD COLUMN IF NOT EXISTS match_tier TEXT,
ADD COLUMN IF NOT EXISTS source_records TEXT;

CREATE INDEX IF NOT EXISTS idx_players_curation ON players(needs_curation) WHERE needs_curation = TRUE;
```

---

### Step 1: Discover overlap

First, find which staging profiles correspond to existing warehouse players.

```sql
-- 1a: How many players are currently in the warehouse?
SELECT COUNT(*) AS existing_warehouse_players FROM players;

-- 1b: How many existing players have aliases?
SELECT alias_type, COUNT(*) AS alias_count
FROM player_aliases
GROUP BY alias_type;

-- 1c: Match existing players to staging profiles via aliases
-- This tells us how many of the 677 are already represented in staging
DROP TABLE IF EXISTS _staging_warehouse_map;

CREATE TEMP TABLE _staging_warehouse_map AS
SELECT DISTINCT
    pps.profile_id AS staging_profile_id,
    pps.tm_id,
    pps.apif_id,
    p.id AS existing_player_id,
    pa.alias_type AS matched_via
FROM profile_players_staging pps
JOIN player_aliases pa
    ON (pa.alias_type = 'transfermarkt_id' AND pa.alias_value = pps.tm_id)
    OR (pa.alias_type = 'apif_id' AND pa.alias_value = pps.apif_id)
JOIN players p ON p.id = pa.player_id;

SELECT COUNT(*) AS staging_profiles_matching_existing FROM _staging_warehouse_map;

-- 1d: How many staging profiles are NEW (not in warehouse)?
SELECT
    (SELECT COUNT(*) FROM profile_players_staging) AS total_staging,
    (SELECT COUNT(DISTINCT staging_profile_id) FROM _staging_warehouse_map) AS already_in_warehouse,
    (SELECT COUNT(*) FROM profile_players_staging) -
    (SELECT COUNT(DISTINCT staging_profile_id) FROM _staging_warehouse_map) AS new_profiles;
```

**Report these numbers before proceeding.**

If the alias match finds 0 rows, it's possible the existing 677 players don't have `transfermarkt_id` / `apif_id` aliases yet. In that case, try a name+DOB match:

```sql
-- 1e: Fallback — match by name + DOB if aliases didn't work
-- Only run this if 1c returned 0 rows
SELECT COUNT(*) AS name_dob_matches
FROM profile_players_staging pps
JOIN players p
    ON lower(pps.display_name) = lower(p.known_as)
    AND pps.date_of_birth = p.date_of_birth;
```

---

### Step 2: Update existing players — OVERWRITE identity, PRESERVE enrichment

The 677 existing players went through the old pipeline without our dedup/validation work. Their **identity fields are suspect** and must be replaced with staging data (our new source of truth). But their **enrichment fields** (bilingual stories, personality, tournament data) are expensive GPT outputs that don't exist in staging — those we keep.

**Rule: Staging OVERWRITES identity. Enrichment stays untouched.**

```sql
-- 2a: Overwrite identity fields from staging (the validated source of truth)
UPDATE players p
SET
    full_legal_name = pps.display_name,
    known_as = pps.display_name,
    date_of_birth = pps.date_of_birth,
    birth_city = pps.birth_city,
    birth_country = pps.birth_country,
    height_cm = pps.height_cm,
    preferred_foot = CASE lower(pps.foot)
        WHEN 'left' THEN 'Left'
        WHEN 'right' THEN 'Right'
        WHEN 'both' THEN 'Both'
        ELSE p.preferred_foot  -- keep existing if staging has no foot data
    END,
    nationality_primary = COALESCE(pps.nationality, p.nationality_primary),
    nationality_secondary = COALESCE(pps.nationality_secondary, p.nationality_secondary),
    photo_url = COALESCE(pps.photo_url, p.photo_url),
    -- New fields from staging
    wikipedia_url = pps.wikipedia_url,
    wikipedia_bio = pps.wikipedia_bio,
    match_tier = pps.match_tier,
    source_records = pps.source_records,
    -- Update confidence from staging (our validated assessment)
    data_confidence = CASE pps.data_confidence
        WHEN 'VERIFIED' THEN 'high'
        WHEN 'PROJECTED' THEN 'medium'
        WHEN 'PARTIAL' THEN 'low'
        WHEN 'ORPHAN' THEN 'low'
    END,
    needs_curation = pps.needs_curation,
    curation_reason = pps.curation_reason
    -- NOTE: We are NOT touching any enrichment fields:
    --   origin_story_en/es, career_summary_en/es, breakthrough_moment,
    --   career_defining_quote, famous_quote_about, biggest_controversy,
    --   celebration_style, off_field_interests, charitable_work,
    --   superstitions, tattoo_meanings, fun_facts, social_media,
    --   music_taste, fashion_brands, injury_prone, notable_injuries,
    --   nicknames, languages_spoken, enriched_at
    -- Those are GPT-generated and stay as-is.
FROM _staging_warehouse_map m
JOIN profile_players_staging pps ON pps.profile_id = m.staging_profile_id
WHERE p.id = m.existing_player_id;

-- 2b: Report how many were updated
-- (PostgreSQL returns the count from UPDATE)
```

---

### Step 3: Insert NEW players from staging

All staging profiles that don't match an existing warehouse player get inserted as new records.

```sql
-- 3: Insert new players
INSERT INTO players (
    id,
    full_legal_name,
    known_as,
    date_of_birth,
    birth_city,
    birth_country,
    height_cm,
    preferred_foot,
    nationality_primary,
    nationality_secondary,
    photo_url,
    data_confidence,
    needs_curation,
    curation_reason,
    wikipedia_url,
    wikipedia_bio,
    match_tier,
    source_records,
    created_at
)
SELECT
    gen_random_uuid(),
    pps.display_name,  -- full_legal_name = display_name for now
    pps.display_name,  -- known_as = display_name
    pps.date_of_birth,
    pps.birth_city,
    pps.birth_country,
    pps.height_cm,
    CASE lower(pps.foot)
        WHEN 'left' THEN 'Left'
        WHEN 'right' THEN 'Right'
        WHEN 'both' THEN 'Both'
        ELSE NULL
    END,
    COALESCE(pps.nationality, 'Unknown'),  -- NOT NULL constraint
    pps.nationality_secondary,
    pps.photo_url,
    -- Map staging confidence → warehouse confidence
    CASE pps.data_confidence
        WHEN 'VERIFIED' THEN 'high'
        WHEN 'PROJECTED' THEN 'medium'
        WHEN 'PARTIAL' THEN 'low'
        WHEN 'ORPHAN' THEN 'low'
    END,
    pps.needs_curation,
    pps.curation_reason,
    pps.wikipedia_url,
    pps.wikipedia_bio,
    pps.match_tier,
    pps.source_records,
    NOW()
FROM profile_players_staging pps
WHERE pps.profile_id NOT IN (
    SELECT staging_profile_id FROM _staging_warehouse_map
);
```

**Report:** How many rows inserted?

---

### Step 4: Insert player_aliases

Create alias records for ALL staging profiles (both existing and new players) so we can always trace back to source IDs.

```sql
-- 4a: Build a complete mapping of staging profile → warehouse player UUID
DROP TABLE IF EXISTS _full_player_map;

CREATE TEMP TABLE _full_player_map AS
-- Existing players (from Step 2)
SELECT m.staging_profile_id, m.existing_player_id AS player_uuid
FROM _staging_warehouse_map m
UNION
-- New players (from Step 3) — match by source_records since we just inserted them
SELECT pps.profile_id, p.id
FROM profile_players_staging pps
JOIN players p ON p.source_records = pps.source_records
WHERE pps.profile_id NOT IN (SELECT staging_profile_id FROM _staging_warehouse_map);

-- 4b: Insert TM aliases (skip if already exists)
INSERT INTO player_aliases (player_id, alias_type, alias_value)
SELECT m.player_uuid, 'transfermarkt_id', pps.tm_id
FROM _full_player_map m
JOIN profile_players_staging pps ON pps.profile_id = m.staging_profile_id
WHERE pps.tm_id IS NOT NULL
ON CONFLICT (alias_type, alias_value) DO NOTHING;

-- 4c: Insert APIF aliases (skip if already exists)
INSERT INTO player_aliases (player_id, alias_type, alias_value)
SELECT m.player_uuid, 'apif_id', pps.apif_id
FROM _full_player_map m
JOIN profile_players_staging pps ON pps.profile_id = m.staging_profile_id
WHERE pps.apif_id IS NOT NULL
ON CONFLICT (alias_type, alias_value) DO NOTHING;

-- 4d: Insert TM URL aliases
INSERT INTO player_aliases (player_id, alias_type, alias_value)
SELECT m.player_uuid, 'transfermarkt_url', pps.tm_url
FROM _full_player_map m
JOIN profile_players_staging pps ON pps.profile_id = m.staging_profile_id
WHERE pps.tm_url IS NOT NULL
ON CONFLICT (alias_type, alias_value) DO NOTHING;

-- 4e: Report alias counts
SELECT alias_type, COUNT(*) AS count
FROM player_aliases
GROUP BY alias_type
ORDER BY count DESC;
```

---

### Step 5: Insert/update player_career

```sql
-- 5: Upsert career data from staging
INSERT INTO player_career (
    player_id,
    current_club,
    position_primary,
    position_secondary,
    estimated_value_eur,
    updated_at,
    refresh_source
)
SELECT
    m.player_uuid,
    pps.current_club,
    -- Normalize position to match warehouse convention
    CASE
        WHEN pps.position ILIKE '%goal%' THEN 'Goalkeeper'
        WHEN pps.position ILIKE '%defend%' OR pps.position ILIKE '%back%' THEN 'Defender'
        WHEN pps.position ILIKE '%midfield%' THEN 'Midfielder'
        WHEN pps.position ILIKE '%attack%' OR pps.position ILIKE '%forward%' OR pps.position ILIKE '%wing%' THEN 'Forward'
        ELSE pps.position
    END,
    pps.sub_position,
    pps.market_value_eur,
    NOW(),
    'dedup_pipeline_v1'
FROM _full_player_map m
JOIN profile_players_staging pps ON pps.profile_id = m.staging_profile_id
ON CONFLICT (player_id) DO UPDATE SET
    current_club = COALESCE(EXCLUDED.current_club, player_career.current_club),
    position_primary = COALESCE(EXCLUDED.position_primary, player_career.position_primary),
    position_secondary = COALESCE(EXCLUDED.position_secondary, player_career.position_secondary),
    estimated_value_eur = COALESCE(EXCLUDED.estimated_value_eur, player_career.estimated_value_eur),
    updated_at = NOW(),
    refresh_source = 'dedup_pipeline_v1';
```

---

### Step 6: Full Report

```sql
-- 6a: Warehouse player counts
SELECT COUNT(*) AS total_warehouse_players FROM players;

-- 6b: Confidence breakdown
SELECT
    data_confidence,
    COUNT(*) AS count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM players) * 100, 1) AS pct
FROM players
GROUP BY data_confidence
ORDER BY
    CASE data_confidence WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END;

-- 6c: Curation queue
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS needs_curation,
    COUNT(*) FILTER (WHERE needs_curation = FALSE OR needs_curation IS NULL) AS clean,
    ROUND(COUNT(*) FILTER (WHERE needs_curation = TRUE)::numeric / COUNT(*) * 100, 1) AS curation_pct
FROM players;

-- 6d: Alias coverage
SELECT alias_type, COUNT(*) FROM player_aliases GROUP BY alias_type;

-- 6e: Career data coverage
SELECT
    COUNT(*) AS total_career_records,
    COUNT(*) FILTER (WHERE current_club IS NOT NULL) AS has_club,
    COUNT(*) FILTER (WHERE position_primary IS NOT NULL) AS has_position,
    COUNT(*) FILTER (WHERE estimated_value_eur IS NOT NULL) AS has_market_value
FROM player_career;

-- 6f: Wikipedia coverage
SELECT
    COUNT(*) FILTER (WHERE wikipedia_url IS NOT NULL) AS has_wikipedia,
    COUNT(*) AS total
FROM players;

-- 6g: Sample high-confidence players (spot check)
SELECT
    p.id, p.known_as, p.data_confidence, p.nationality_primary,
    pc.position_primary, pc.current_club, pc.estimated_value_eur
FROM players p
LEFT JOIN player_career pc ON p.id = pc.player_id
WHERE p.data_confidence = 'high'
ORDER BY pc.estimated_value_eur DESC NULLS LAST
LIMIT 25;

-- 6h: Sample curation queue entries
SELECT
    p.known_as, p.data_confidence, p.needs_curation, p.curation_reason,
    p.source_records
FROM players p
WHERE p.needs_curation = TRUE
ORDER BY p.known_as
LIMIT 25;

-- 6i: Verify existing enriched players are intact
-- Check that bilingual fields weren't wiped
SELECT
    COUNT(*) AS enriched_players_with_stories,
    COUNT(*) FILTER (WHERE origin_story_en IS NOT NULL) AS has_origin_story,
    COUNT(*) FILTER (WHERE career_summary_en IS NOT NULL) AS has_career_summary
FROM players
WHERE enriched_at IS NOT NULL;

-- 6j: Table sizes
SELECT
    pg_size_pretty(pg_total_relation_size('players')) AS players_size,
    pg_size_pretty(pg_total_relation_size('player_aliases')) AS aliases_size,
    pg_size_pretty(pg_total_relation_size('player_career')) AS career_size;

-- 6k: KILL SWITCH — verify no duplicate aliases
SELECT 'DUPLICATE alias' AS issue, alias_type, alias_value, COUNT(*)
FROM player_aliases
GROUP BY alias_type, alias_value
HAVING COUNT(*) > 1
LIMIT 20;
-- ^^^ MUST return 0 rows. UNIQUE constraint should prevent this, but verify.
```

---

### Step 7: Post-load duplicate detection

**This step runs every time we promote staging.** It catches pre-existing players that weren't matched via alias in Step 1 but might be duplicates of newly loaded records. Without this step, the warehouse accumulates ghost duplicates that are invisible until someone notices Pedri showing up twice.

**How it works:** Find every player that existed before this load and wasn't in the staging-warehouse map. For each one, check if a newly-inserted player shares the same name + DOB. If yes, flag both with `potential_duplicate_post_load`. If no match, they're clean — they came from a source not in staging.

```sql
-- 7a: Identify pre-existing players that were NOT matched to staging
-- These are the ones at risk of being duplicates
DROP TABLE IF EXISTS _unmatched_legacy;

CREATE TEMP TABLE _unmatched_legacy AS
SELECT p.id, p.known_as, p.date_of_birth, p.nationality_primary
FROM players p
WHERE p.created_at < (
    -- Anything created before this load started
    SELECT MIN(created_at) FROM players
    WHERE source_records IS NOT NULL
    AND source_records LIKE 'TM:%' OR source_records LIKE 'APIF:%'
)
AND p.id NOT IN (SELECT existing_player_id FROM _staging_warehouse_map);

-- 7b: How many unmatched legacy players?
SELECT COUNT(*) AS unmatched_legacy_players FROM _unmatched_legacy;

-- 7c: Find duplicates — legacy player has same name + DOB as a newly loaded player
DROP TABLE IF EXISTS _post_load_duplicates;

CREATE TEMP TABLE _post_load_duplicates AS
SELECT
    legacy.id AS legacy_player_id,
    legacy.known_as AS legacy_name,
    new_p.id AS new_player_id,
    new_p.known_as AS new_name,
    legacy.date_of_birth,
    legacy.nationality_primary
FROM _unmatched_legacy legacy
JOIN players new_p
    ON lower(legacy.known_as) = lower(new_p.known_as)
    AND legacy.date_of_birth = new_p.date_of_birth
    AND new_p.id != legacy.id
    AND new_p.source_records IS NOT NULL;  -- newly loaded records have source_records

-- 7d: How many duplicates found?
SELECT COUNT(*) AS duplicate_pairs_found FROM _post_load_duplicates;

-- 7e: Show them
SELECT * FROM _post_load_duplicates ORDER BY legacy_name;

-- 7f: Flag BOTH sides of each duplicate for curation
UPDATE players
SET
    needs_curation = TRUE,
    curation_reason = CASE
        WHEN curation_reason IS NOT NULL THEN curation_reason || '; potential_duplicate_post_load'
        ELSE 'potential_duplicate_post_load'
    END
WHERE id IN (
    SELECT legacy_player_id FROM _post_load_duplicates
    UNION
    SELECT new_player_id FROM _post_load_duplicates
);

-- 7g: Report total curation queue after duplicate detection
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS total_needs_curation,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%potential_duplicate_post_load%') AS flagged_as_post_load_dup
FROM players;
```

**Expected:** The 184 unmatched legacy players get scanned. Some will match newly loaded records by name + DOB (like Pedri, Rodri). Both sides get flagged. The rest are clean.

**Why this is a pipeline step, not a patch:** Every future staging promotion will produce the same class of problem — existing players whose aliases don't match the new load. This step systematically catches them every time. No one has to remember it happened.

---

### Step 8: Club conflict detection (automated recency check)

**This step runs every time we promote staging.** For VERIFIED profiles (dual-source), TM and APIF may disagree on current_club — a direct signal that one source has stale transfer data. This catches transfers that happened between when TM and APIF were last synced. Zero cost (no GPT), purely SQL.

```sql
-- 8a: Find VERIFIED profiles where TM and APIF clubs disagree
DROP TABLE IF EXISTS _club_conflicts;

CREATE TEMP TABLE _club_conflicts AS
SELECT
    dp.tm_id,
    dp.tm_name,
    dp.apif_id,
    dp.apif_name,
    dp.tm_club AS tm_says,
    dp.apif_club AS apif_says,
    dp.tm_market_value
FROM dedup_pairs dp
WHERE dp.tm_club IS NOT NULL
  AND dp.apif_club IS NOT NULL
  AND lower(trim(dp.tm_club)) != lower(trim(dp.apif_club));

-- 8b: How many conflicts?
SELECT COUNT(*) AS club_conflicts FROM _club_conflicts;

-- 8c: Show top conflicts by market value
SELECT * FROM _club_conflicts ORDER BY tm_market_value DESC NULLS LAST LIMIT 25;

-- 8d: Flag these profiles in the warehouse for curation
-- Join through player_aliases to get the warehouse player UUID
UPDATE players p
SET
    needs_curation = TRUE,
    curation_reason = CASE
        WHEN p.curation_reason IS NOT NULL
        THEN p.curation_reason || '; club_conflict_tm_apif'
        ELSE 'club_conflict_tm_apif'
    END
FROM _club_conflicts cc
JOIN player_aliases pa
    ON pa.alias_type = 'transfermarkt_id' AND pa.alias_value = cc.tm_id
WHERE p.id = pa.player_id
  AND (p.curation_reason IS NULL OR p.curation_reason NOT LIKE '%club_conflict%');

-- 8e: Report
SELECT
    COUNT(*) FILTER (WHERE curation_reason LIKE '%club_conflict%') AS flagged_club_conflict
FROM players;
```

**Expected:** Some percentage of VERIFIED profiles will have club conflicts — these are recent transfers. The higher the market value, the more visible and urgent the conflict.

**Why this matters:** APIF wins for current_club in our merge (Rule MG-3), but if APIF is also stale, we're showing wrong data. The conflict flag tells curators "these two sources disagree — go check." Combined with the GPT verification pipeline (daily on top 500), this creates two independent layers of recency detection.

---

## Expected Results

| Metric | Expected |
|--------|----------|
| Total warehouse players after load | ~43,500–44,000 (43,447 staging + ~677 existing - overlap) |
| Existing players updated (Step 2) | 0–677 (depends on alias coverage) |
| New players inserted (Step 3) | ~42,770–43,447 |
| data_confidence = 'high' | ~5,840 (VERIFIED) + existing enriched |
| data_confidence = 'medium' | ~30,515 (PROJECTED) |
| data_confidence = 'low' | ~7,092 (PARTIAL + ORPHAN) |
| Alias records | ~43,000+ TM + ~15,000+ APIF |
| Enriched players with stories intact (6i) | 677 (unchanged) |
| Duplicate aliases (6k) | 0 rows |

---

## After This

Save ALL output to **`AZTECA_PROMOTE_STAGING_RESULTS.md`** in the el-capi repo root.

If 6k returns 0 rows and 6i confirms enriched players are intact → the warehouse is production-ready.

Pelé will then:
1. Verify the app can query the expanded player set
2. Build the admin curation queue UI
3. Plan the `player_tournament` data load for WC 2026 squads

---

## IMPORTANT

1. **DO NOT** drop or modify `profile_players_staging` — keep it as the dedup audit trail
2. **DO NOT** modify existing `player_tournament` records — those are separate
3. The `_staging_warehouse_map` and `_full_player_map` are TEMP tables — they disappear when the session ends
4. If Step 3 INSERT fails on NOT NULL constraints, report which field is NULL — we'll add COALESCE handling
5. If Step 4 produces UNIQUE constraint violations, the `ON CONFLICT DO NOTHING` handles it silently — that's expected
