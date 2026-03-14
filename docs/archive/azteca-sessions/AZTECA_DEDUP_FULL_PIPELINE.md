# AZTECA TASK: Full Pipeline Dedup — 49K Players

**Priority:** HIGH — Execute immediately
**From:** Pelé (Strategy & PM)
**Context:** The dedup rules have been validated on a 100-player sample with 100% precision and 100% recall. Now we run against the full `pipeline_players` table (49,287 records).

---

## What This Does

Creates `profile_players_staging` — a new table containing deduplicated player profiles with structured name fields, confidence scores, and curation flags. This is the foundation for all player identity going forward.

---

## STEP 1: Create the staging table

```sql
-- Drop if exists from previous runs
DROP TABLE IF EXISTS profile_players_staging;

CREATE TABLE profile_players_staging (
    profile_id      SERIAL PRIMARY KEY,
    tm_id           TEXT,
    apif_id         TEXT,
    first_initial   CHAR(1),
    first_name      TEXT,
    middle_name     TEXT,
    last_name       TEXT,
    name_prefix     TEXT,
    nickname        TEXT,
    display_name    TEXT NOT NULL,
    date_of_birth   DATE,
    birth_country   TEXT,
    birth_city      TEXT,
    nationality     TEXT,
    nationality_secondary TEXT,
    height_cm       INT,
    foot            TEXT,
    photo_url       TEXT,
    position        TEXT,
    sub_position    TEXT,
    current_club    TEXT,
    market_value_eur BIGINT,
    tm_url          TEXT,
    data_confidence TEXT NOT NULL DEFAULT 'PARTIAL',
    needs_curation  BOOLEAN NOT NULL DEFAULT TRUE,
    curation_reason TEXT,
    curation_resolved_by TEXT,
    curation_resolved_at TIMESTAMPTZ,
    match_tier      TEXT,
    source_records  TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast lookup
CREATE INDEX idx_profile_tm_id ON profile_players_staging(tm_id);
CREATE INDEX idx_profile_apif_id ON profile_players_staging(apif_id);
CREATE INDEX idx_profile_curation ON profile_players_staging(needs_curation) WHERE needs_curation = TRUE;
CREATE INDEX idx_profile_confidence ON profile_players_staging(data_confidence);
CREATE INDEX idx_profile_nationality ON profile_players_staging(nationality);
CREATE INDEX idx_profile_dob ON profile_players_staging(date_of_birth);
```

---

## STEP 2: Run Tier 2 Dedup — Find all cross-source pairs

This is the core dedup query. It matches TM ↔ APIF records using:
- Normalized last name token (last whitespace-delimited word, lowercased, accent-stripped)
- Exact DOB match (both non-null)
- Exact nationality match (both non-null)

```sql
-- Create a helper function for accent stripping if not exists
CREATE OR REPLACE FUNCTION strip_accents(text) RETURNS text AS $$
    SELECT translate(
        $1,
        'àáâãäåèéêëìíîïòóôõöùúûüýÿñçšžÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÝŸÑÇŠŽ',
        'aaaaaaeeeeiiiioooooouuuuyyncszAAAAAAEEEEIIIIOOOOOUUUUYYNCSZ'
    );
$$ LANGUAGE sql IMMUTABLE;

-- Find all cross-source duplicate pairs
DROP TABLE IF EXISTS dedup_pairs;

CREATE TABLE dedup_pairs AS
WITH players_with_tokens AS (
    SELECT
        id,
        name,
        name_short,
        date_of_birth,
        nationality,
        nationality_secondary,
        position,
        sub_position,
        foot,
        height_cm,
        current_club_name,
        jersey_number,
        market_value_eur,
        photo_url,
        country_of_birth,
        city_of_birth,
        transfermarkt_url,
        CASE WHEN id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS source,
        -- Last token normalized: lowercase + strip accents
        lower(strip_accents(
            CASE
                WHEN name LIKE '%.%' AND position(' ' in reverse(name)) > 0
                THEN substring(name from length(name) - position(' ' in reverse(name)) + 2)
                ELSE split_part(name, ' ', array_length(string_to_array(name, ' '), 1))
            END
        )) AS last_token_norm
    FROM pipeline_players
    WHERE date_of_birth IS NOT NULL
      AND nationality IS NOT NULL
      AND name IS NOT NULL
)
SELECT
    tm.id AS tm_id,
    tm.name AS tm_name,
    tm.name_short AS tm_name_short,
    apif.id AS apif_id,
    apif.name AS apif_name,
    apif.name_short AS apif_name_short,
    tm.date_of_birth,
    tm.nationality,
    tm.last_token_norm,
    -- TM fields (higher priority for most)
    tm.position AS tm_position,
    tm.sub_position AS tm_sub_position,
    tm.foot AS tm_foot,
    tm.height_cm AS tm_height_cm,
    tm.current_club_name AS tm_club,
    tm.market_value_eur AS tm_market_value,
    tm.photo_url AS tm_photo,
    tm.country_of_birth AS tm_birth_country,
    tm.city_of_birth AS tm_birth_city,
    tm.transfermarkt_url AS tm_url,
    tm.nationality_secondary AS tm_nat2,
    -- APIF fields (higher priority for current club)
    apif.position AS apif_position,
    apif.height_cm AS apif_height_cm,
    apif.current_club_name AS apif_club,
    apif.photo_url AS apif_photo,
    apif.country_of_birth AS apif_birth_country,
    apif.city_of_birth AS apif_birth_city,
    apif.nationality_secondary AS apif_nat2
FROM players_with_tokens tm
JOIN players_with_tokens apif
    ON tm.last_token_norm = apif.last_token_norm
    AND tm.date_of_birth = apif.date_of_birth
    AND lower(tm.nationality) = lower(apif.nationality)
WHERE tm.source = 'TM'
  AND apif.source = 'APIF';
```

**Report the count:**
```sql
SELECT COUNT(*) AS total_pairs FROM dedup_pairs;
```

---

## STEP 3: Insert merged profiles (Tier 2 pairs)

```sql
-- Insert merged profiles from Tier 2 pairs
INSERT INTO profile_players_staging (
    tm_id, apif_id, display_name,
    date_of_birth, birth_country, birth_city,
    nationality, nationality_secondary,
    height_cm, foot, photo_url, position, sub_position,
    current_club, market_value_eur, tm_url,
    data_confidence, needs_curation, curation_reason,
    match_tier, source_records
)
SELECT
    dp.tm_id,
    dp.apif_id,
    -- Display name: prefer TM (it's fuller)
    dp.tm_name AS display_name,
    dp.date_of_birth,
    -- TM > APIF for most fields
    COALESCE(dp.tm_birth_country, dp.apif_birth_country) AS birth_country,
    COALESCE(dp.tm_birth_city, dp.apif_birth_city) AS birth_city,
    dp.nationality,
    COALESCE(dp.tm_nat2, dp.apif_nat2) AS nationality_secondary,
    COALESCE(dp.tm_height_cm, dp.apif_height_cm) AS height_cm,
    dp.tm_foot AS foot,  -- APIF never has foot
    COALESCE(dp.tm_photo, dp.apif_photo) AS photo_url,
    COALESCE(dp.tm_position, dp.apif_position) AS position,
    dp.tm_sub_position AS sub_position,  -- APIF never has sub_position
    -- Rule MG-3: APIF overrides TM for current club
    COALESCE(dp.apif_club, dp.tm_club) AS current_club,
    dp.tm_market_value AS market_value_eur,
    dp.tm_url,
    -- Confidence: VERIFIED for dual-source matches
    'VERIFIED' AS data_confidence,
    -- Check if name is initial-only (needs curation for first_name resolution)
    CASE WHEN dp.tm_name ~ '^[A-Z]\. ' THEN TRUE ELSE FALSE END AS needs_curation,
    CASE WHEN dp.tm_name ~ '^[A-Z]\. ' THEN 'initial_only' ELSE NULL END AS curation_reason,
    'Tier 2' AS match_tier,
    'TM:' || dp.tm_id || ' + APIF:' || dp.apif_id AS source_records
FROM dedup_pairs dp;
```

**Report:**
```sql
SELECT COUNT(*) AS merged_profiles FROM profile_players_staging WHERE match_tier = 'Tier 2';
```

---

## STEP 4: Insert unmatched TM records

```sql
-- TM records that were NOT part of any Tier 2 pair
INSERT INTO profile_players_staging (
    tm_id, apif_id, display_name,
    date_of_birth, birth_country, birth_city,
    nationality, nationality_secondary,
    height_cm, foot, photo_url, position, sub_position,
    current_club, market_value_eur, tm_url,
    data_confidence, needs_curation, curation_reason,
    match_tier, source_records
)
SELECT
    pp.id AS tm_id,
    NULL AS apif_id,
    pp.name AS display_name,
    pp.date_of_birth,
    pp.country_of_birth AS birth_country,
    pp.city_of_birth AS birth_city,
    pp.nationality,
    pp.nationality_secondary,
    pp.height_cm,
    pp.foot,
    pp.photo_url,
    pp.position,
    pp.sub_position,
    pp.current_club_name AS current_club,
    pp.market_value_eur,
    pp.transfermarkt_url AS tm_url,
    -- Confidence: PROJECTED if has DOB + nationality + full name, else PARTIAL
    CASE
        WHEN pp.date_of_birth IS NOT NULL AND pp.nationality IS NOT NULL
             AND pp.name NOT LIKE '_. %'
        THEN 'PROJECTED'
        ELSE 'PARTIAL'
    END AS data_confidence,
    -- Needs curation if missing key identity fields
    CASE
        WHEN pp.date_of_birth IS NULL OR pp.nationality IS NULL OR pp.name LIKE '_. %'
        THEN TRUE
        ELSE FALSE
    END AS needs_curation,
    CASE
        WHEN pp.date_of_birth IS NULL AND pp.nationality IS NULL THEN 'missing_dob; missing_nationality'
        WHEN pp.date_of_birth IS NULL THEN 'missing_dob'
        WHEN pp.nationality IS NULL THEN 'missing_nationality'
        WHEN pp.name LIKE '_. %' THEN 'initial_only'
        ELSE NULL
    END AS curation_reason,
    'Tier 4 (unique)' AS match_tier,
    'TM:' || pp.id AS source_records
FROM pipeline_players pp
WHERE pp.id NOT LIKE 'apif_%'  -- TM records only
  AND pp.id NOT IN (SELECT tm_id FROM dedup_pairs);
```

---

## STEP 5: Insert unmatched APIF records

```sql
-- APIF records that were NOT part of any Tier 2 pair
INSERT INTO profile_players_staging (
    tm_id, apif_id, display_name,
    date_of_birth, birth_country, birth_city,
    nationality, nationality_secondary,
    height_cm, foot, photo_url, position, sub_position,
    current_club, market_value_eur, tm_url,
    data_confidence, needs_curation, curation_reason,
    match_tier, source_records
)
SELECT
    NULL AS tm_id,
    pp.id AS apif_id,
    -- Use name_short if it has more tokens than name
    CASE
        WHEN pp.name_short IS NOT NULL
             AND array_length(string_to_array(pp.name_short, ' '), 1) > array_length(string_to_array(pp.name, ' '), 1)
        THEN pp.name_short
        ELSE pp.name
    END AS display_name,
    pp.date_of_birth,
    pp.country_of_birth AS birth_country,
    pp.city_of_birth AS birth_city,
    pp.nationality,
    pp.nationality_secondary,
    pp.height_cm,
    pp.foot,
    pp.photo_url,
    pp.position,
    pp.sub_position,
    pp.current_club_name AS current_club,
    pp.market_value_eur,
    NULL AS tm_url,
    -- APIF-only records: ORPHAN if missing key fields, else PROJECTED
    CASE
        WHEN pp.date_of_birth IS NULL OR pp.nationality IS NULL OR pp.name ~ '^[A-Z]\. '
        THEN 'ORPHAN'
        ELSE 'PROJECTED'
    END AS data_confidence,
    -- Most APIF-only records need curation
    CASE
        WHEN pp.date_of_birth IS NULL OR pp.nationality IS NULL OR pp.name ~ '^[A-Z]\. '
        THEN TRUE
        ELSE FALSE
    END AS needs_curation,
    -- Build curation reason
    CASE
        WHEN pp.date_of_birth IS NULL AND pp.nationality IS NULL AND pp.name ~ '^[A-Z]\. '
        THEN 'initial_only; missing_dob; missing_nationality'
        WHEN pp.date_of_birth IS NULL AND pp.name ~ '^[A-Z]\. '
        THEN 'initial_only; missing_dob'
        WHEN pp.nationality IS NULL AND pp.name ~ '^[A-Z]\. '
        THEN 'initial_only; missing_nationality'
        WHEN pp.date_of_birth IS NULL AND pp.nationality IS NULL
        THEN 'missing_dob; missing_nationality'
        WHEN pp.date_of_birth IS NULL THEN 'missing_dob'
        WHEN pp.nationality IS NULL THEN 'missing_nationality'
        WHEN pp.name ~ '^[A-Z]\. ' THEN 'initial_only'
        ELSE NULL
    END AS curation_reason,
    'Tier 4 (unique)' AS match_tier,
    'APIF:' || pp.id AS source_records
FROM pipeline_players pp
WHERE pp.id LIKE 'apif_%'  -- APIF records only
  AND pp.id NOT IN (SELECT apif_id FROM dedup_pairs);
```

---

## STEP 6: Enrich with Wikipedia bios

```sql
-- Update profiles that have Wikipedia bios
-- Join via player_bios (which has 1,841 bios)
-- First try matching by tm_id
UPDATE profile_players_staging pps
SET
    display_name = COALESCE(
        -- Extract full name from first sentence of bio
        substring(pb.bio_preview FROM '^([^(]+?)\s+(?:is|was)\s'),
        pps.display_name
    ),
    curation_reason = CASE
        WHEN pps.needs_curation AND pps.curation_reason LIKE '%initial_only%'
        THEN replace(pps.curation_reason, 'initial_only', 'initial_only_wiki_available')
        ELSE pps.curation_reason
    END
FROM v1.player_bios pb
WHERE pps.tm_id IS NOT NULL
  AND pb.player_id = pps.tm_id::text;

-- Count Wikipedia enrichments
SELECT COUNT(*) AS wiki_enriched
FROM profile_players_staging
WHERE curation_reason LIKE '%wiki_available%';
```

---

## STEP 7: Report results

Run ALL of these and paste the full output:

```sql
-- 7a: Total profiles created
SELECT COUNT(*) AS total_profiles FROM profile_players_staging;

-- 7b: Confidence breakdown
SELECT
    data_confidence,
    COUNT(*) AS count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM profile_players_staging) * 100, 1) AS pct,
    SUM(CASE WHEN needs_curation THEN 1 ELSE 0 END) AS needs_curation_count
FROM profile_players_staging
GROUP BY data_confidence
ORDER BY
    CASE data_confidence
        WHEN 'VERIFIED' THEN 1
        WHEN 'PROJECTED' THEN 2
        WHEN 'PARTIAL' THEN 3
        WHEN 'ORPHAN' THEN 4
        WHEN 'UNRESOLVED' THEN 5
    END;

-- 7c: Match tier breakdown
SELECT match_tier, COUNT(*) AS count
FROM profile_players_staging
GROUP BY match_tier
ORDER BY count DESC;

-- 7d: Curation reasons
SELECT
    unnest(string_to_array(curation_reason, '; ')) AS reason,
    COUNT(*) AS count
FROM profile_players_staging
WHERE needs_curation = TRUE
GROUP BY reason
ORDER BY count DESC;

-- 7e: Curation queue size
SELECT
    COUNT(*) AS total_needing_curation,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM profile_players_staging) * 100, 1) AS pct
FROM profile_players_staging
WHERE needs_curation = TRUE;

-- 7f: Sample of VERIFIED profiles (spot check)
SELECT profile_id, tm_id, apif_id, display_name, date_of_birth, nationality, data_confidence
FROM profile_players_staging
WHERE data_confidence = 'VERIFIED'
ORDER BY display_name
LIMIT 20;

-- 7g: Sample of ORPHAN profiles (spot check curation queue)
SELECT profile_id, apif_id, display_name, date_of_birth, nationality, curation_reason
FROM profile_players_staging
WHERE data_confidence = 'ORPHAN'
ORDER BY curation_reason, display_name
LIMIT 20;

-- 7h: Duplicate check — make sure no player appears in more than one profile
SELECT 'TM duplicates' AS check_type, tm_id, COUNT(*)
FROM profile_players_staging
WHERE tm_id IS NOT NULL
GROUP BY tm_id HAVING COUNT(*) > 1
UNION ALL
SELECT 'APIF duplicates', apif_id, COUNT(*)
FROM profile_players_staging
WHERE apif_id IS NOT NULL
GROUP BY apif_id HAVING COUNT(*) > 1;

-- 7i: Table size
SELECT pg_size_pretty(pg_total_relation_size('profile_players_staging')) AS table_size;
```

---

## Expected Results (based on sample validation)

| Metric | Expected Range |
|--------|---------------|
| Total profiles | ~39,000-42,000 (49K minus cross-source pairs) |
| Tier 2 pairs | ~7,000-10,000 |
| VERIFIED | ~15-20% |
| PROJECTED | ~55-65% |
| PARTIAL + ORPHAN | ~15-25% |
| Needs curation | ~15-25% |
| Duplicate check | ZERO — any duplicates = bug |

---

## IMPORTANT NOTES

1. **Do NOT drop pipeline_players** — it's the source data, we only read from it
2. The staging table is safe to drop and recreate — it's derived data
3. If any query takes >5 min, report the timeout and we'll optimize
4. If the duplicate check (7h) returns ANY rows, STOP and report — that's a data integrity issue
5. Save all output to `AZTECA_DEDUP_FULL_RESULTS.md` in the repo
