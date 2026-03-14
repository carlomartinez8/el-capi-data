-- AZTECA_DEDUP_EXECUTE — Full pipeline run (Steps 1–7)
\echo '========== Step 1: Create profile_players_staging =========='
DROP TABLE IF EXISTS profile_players_staging;

CREATE TABLE profile_players_staging (
    profile_id          SERIAL PRIMARY KEY,
    tm_id               TEXT,
    apif_id             TEXT,
    display_name        TEXT NOT NULL,
    date_of_birth       DATE,
    birth_country       TEXT,
    birth_city          TEXT,
    nationality         TEXT,
    nationality_secondary TEXT,
    height_cm           INT,
    foot                TEXT,
    photo_url           TEXT,
    position            TEXT,
    sub_position        TEXT,
    current_club        TEXT,
    market_value_eur    BIGINT,
    tm_url              TEXT,
    data_confidence     TEXT NOT NULL DEFAULT 'PARTIAL',
    needs_curation      BOOLEAN NOT NULL DEFAULT TRUE,
    curation_reason     TEXT,
    curation_resolved_by TEXT,
    curation_resolved_at TIMESTAMPTZ,
    match_tier          TEXT,
    source_records      TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pps_tm_id ON profile_players_staging(tm_id);
CREATE INDEX idx_pps_apif_id ON profile_players_staging(apif_id);
CREATE INDEX idx_pps_curation ON profile_players_staging(needs_curation) WHERE needs_curation = TRUE;
CREATE INDEX idx_pps_confidence ON profile_players_staging(data_confidence);

\echo '========== Step 2: Create strip_accents =========='
CREATE OR REPLACE FUNCTION strip_accents(text) RETURNS text AS $$
    SELECT translate(
        $1,
        'àáâãäåæèéêëìíîïðòóôõöùúûüýÿñçšžőűÀÁÂÃÄÅÆÈÉÊËÌÍÎÏÐÒÓÔÕÖÙÚÛÜÝŸÑÇŠŽŐŰ',
        'aaaaaaaeeeeiiiidoooooouuuuyyncszouAAAAAAEEEEIIIIDOOOOOUUUUYYNCSZOU'
    );
$$ LANGUAGE sql IMMUTABLE;

\echo '========== Step 3: Create dedup_pairs (Tier 2) =========='
DROP TABLE IF EXISTS dedup_pairs;

CREATE TABLE dedup_pairs AS
WITH players_enriched AS (
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
        lower(strip_accents(
            split_part(name, ' ', array_length(string_to_array(name, ' '), 1))
        )) AS last_token_norm
    FROM pipeline_players
    WHERE name IS NOT NULL
      AND date_of_birth IS NOT NULL
      AND nationality IS NOT NULL
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
    apif.position AS apif_position,
    apif.height_cm AS apif_height_cm,
    apif.current_club_name AS apif_club,
    apif.photo_url AS apif_photo,
    apif.country_of_birth AS apif_birth_country,
    apif.city_of_birth AS apif_birth_city,
    apif.nationality_secondary AS apif_nat2
FROM players_enriched tm
JOIN players_enriched apif
    ON tm.last_token_norm = apif.last_token_norm
    AND tm.date_of_birth = apif.date_of_birth
    AND lower(tm.nationality) = lower(apif.nationality)
WHERE tm.source = 'TM'
  AND apif.source = 'APIF';

\echo '========== Step 3 report: total_tier2_pairs =========='
SELECT COUNT(*) AS total_tier2_pairs FROM dedup_pairs;

\echo '========== Step 3 check: TM/APIF in multiple pairs =========='
SELECT 'TM in multiple pairs' AS issue, tm_id, COUNT(*)
FROM dedup_pairs GROUP BY tm_id HAVING COUNT(*) > 1
UNION ALL
SELECT 'APIF in multiple pairs', apif_id, COUNT(*)
FROM dedup_pairs GROUP BY apif_id HAVING COUNT(*) > 1
LIMIT 20;

\echo '========== Step 4: Insert merged (Tier 2) =========='
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
    dp.tm_name,
    dp.date_of_birth,
    COALESCE(dp.tm_birth_country, dp.apif_birth_country),
    COALESCE(dp.tm_birth_city, dp.apif_birth_city),
    dp.nationality,
    COALESCE(dp.tm_nat2, dp.apif_nat2),
    COALESCE(dp.tm_height_cm, dp.apif_height_cm),
    dp.tm_foot,
    COALESCE(dp.tm_photo, dp.apif_photo),
    COALESCE(dp.tm_position, dp.apif_position),
    dp.tm_sub_position,
    COALESCE(dp.apif_club, dp.tm_club),
    dp.tm_market_value,
    dp.tm_url,
    'VERIFIED',
    FALSE,
    NULL,
    'Tier 2',
    'TM:' || dp.tm_id || ' + APIF:' || dp.apif_id
FROM dedup_pairs dp;

\echo '========== Step 5: Insert unmatched TM =========='
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
    pp.id,
    NULL,
    pp.name,
    pp.date_of_birth,
    pp.country_of_birth,
    pp.city_of_birth,
    pp.nationality,
    pp.nationality_secondary,
    pp.height_cm,
    pp.foot,
    pp.photo_url,
    pp.position,
    pp.sub_position,
    pp.current_club_name,
    pp.market_value_eur,
    pp.transfermarkt_url,
    CASE
        WHEN pp.date_of_birth IS NOT NULL AND pp.nationality IS NOT NULL
        THEN 'PROJECTED'
        ELSE 'PARTIAL'
    END,
    CASE
        WHEN pp.date_of_birth IS NULL OR pp.nationality IS NULL
        THEN TRUE
        ELSE FALSE
    END,
    CASE
        WHEN pp.date_of_birth IS NULL AND pp.nationality IS NULL THEN 'missing_dob; missing_nationality'
        WHEN pp.date_of_birth IS NULL THEN 'missing_dob'
        WHEN pp.nationality IS NULL THEN 'missing_nationality'
        ELSE NULL
    END,
    'Tier 4 (unique)',
    'TM:' || pp.id
FROM pipeline_players pp
WHERE pp.id NOT LIKE 'apif_%'
  AND pp.id NOT IN (SELECT tm_id FROM dedup_pairs);

\echo '========== Step 6: Insert unmatched APIF =========='
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
    NULL,
    pp.id,
    CASE
        WHEN pp.name_short IS NOT NULL
             AND array_length(string_to_array(pp.name_short, ' '), 1)
               > array_length(string_to_array(pp.name, ' '), 1)
        THEN pp.name_short
        ELSE pp.name
    END,
    pp.date_of_birth,
    pp.country_of_birth,
    pp.city_of_birth,
    pp.nationality,
    pp.nationality_secondary,
    pp.height_cm,
    pp.foot,
    pp.photo_url,
    pp.position,
    pp.sub_position,
    pp.current_club_name,
    pp.market_value_eur,
    NULL,
    CASE
        WHEN pp.date_of_birth IS NULL OR pp.nationality IS NULL OR pp.name ~ '^[A-Z]\. '
        THEN 'ORPHAN'
        ELSE 'PROJECTED'
    END,
    CASE
        WHEN pp.date_of_birth IS NULL OR pp.nationality IS NULL OR pp.name ~ '^[A-Z]\. '
        THEN TRUE
        ELSE FALSE
    END,
    CASE
        WHEN pp.date_of_birth IS NULL AND pp.nationality IS NULL AND pp.name ~ '^[A-Z]\. '
            THEN 'initial_only; missing_dob; missing_nationality'
        WHEN pp.date_of_birth IS NULL AND pp.name ~ '^[A-Z]\. '
            THEN 'initial_only; missing_dob'
        WHEN pp.nationality IS NULL AND pp.name ~ '^[A-Z]\. '
            THEN 'initial_only; missing_nationality'
        WHEN pp.date_of_birth IS NULL AND pp.nationality IS NULL
            THEN 'missing_dob; missing_nationality'
        WHEN pp.name ~ '^[A-Z]\. ' THEN 'initial_only'
        WHEN pp.date_of_birth IS NULL THEN 'missing_dob'
        WHEN pp.nationality IS NULL THEN 'missing_nationality'
        ELSE NULL
    END,
    'Tier 4 (unique)',
    'APIF:' || pp.id
FROM pipeline_players pp
WHERE pp.id LIKE 'apif_%'
  AND pp.id NOT IN (SELECT apif_id FROM dedup_pairs);

\echo '========== Step 7a: Total profiles =========='
SELECT COUNT(*) AS total_profiles FROM profile_players_staging;

\echo '========== Step 7b: Input vs output =========='
SELECT
    (SELECT COUNT(*) FROM pipeline_players) AS input_records,
    (SELECT COUNT(*) FROM profile_players_staging) AS output_profiles,
    (SELECT COUNT(*) FROM dedup_pairs) AS merged_pairs,
    (SELECT COUNT(*) FROM pipeline_players) - (SELECT COUNT(*) FROM profile_players_staging) AS records_deduped;

\echo '========== Step 7c: Confidence breakdown =========='
SELECT
    data_confidence,
    COUNT(*) AS count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM profile_players_staging) * 100, 1) AS pct,
    SUM(CASE WHEN needs_curation THEN 1 ELSE 0 END) AS flagged_for_curation
FROM profile_players_staging
GROUP BY data_confidence
ORDER BY
    CASE data_confidence
        WHEN 'VERIFIED' THEN 1
        WHEN 'PROJECTED' THEN 2
        WHEN 'PARTIAL' THEN 3
        WHEN 'ORPHAN' THEN 4
    END;

\echo '========== Step 7d: Match tier breakdown =========='
SELECT match_tier, COUNT(*) AS count
FROM profile_players_staging
GROUP BY match_tier
ORDER BY count DESC;

\echo '========== Step 7e: Curation reasons =========='
SELECT
    unnest(string_to_array(curation_reason, '; ')) AS reason,
    COUNT(*) AS count
FROM profile_players_staging
WHERE needs_curation = TRUE
GROUP BY reason
ORDER BY count DESC;

\echo '========== Step 7f: Curation queue size =========='
SELECT
    COUNT(*) AS total_needing_curation,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM profile_players_staging) * 100, 1) AS pct
FROM profile_players_staging
WHERE needs_curation = TRUE;

\echo '========== Step 7g: KILL SWITCH — Duplicate integrity =========='
SELECT 'DUPLICATE tm_id' AS issue, tm_id AS id, COUNT(*) AS occurrences
FROM profile_players_staging
WHERE tm_id IS NOT NULL
GROUP BY tm_id HAVING COUNT(*) > 1
UNION ALL
SELECT 'DUPLICATE apif_id', apif_id, COUNT(*)
FROM profile_players_staging
WHERE apif_id IS NOT NULL
GROUP BY apif_id HAVING COUNT(*) > 1
LIMIT 20;

\echo '========== Step 7h: Sample VERIFIED =========='
SELECT profile_id, tm_id, apif_id, display_name, date_of_birth, nationality, current_club
FROM profile_players_staging
WHERE data_confidence = 'VERIFIED'
ORDER BY display_name
LIMIT 25;

\echo '========== Step 7i: Sample ORPHAN =========='
SELECT profile_id, apif_id, display_name, date_of_birth, nationality, curation_reason
FROM profile_players_staging
WHERE data_confidence = 'ORPHAN'
ORDER BY display_name
LIMIT 25;

\echo '========== Step 7j: Table sizes =========='
SELECT
    pg_size_pretty(pg_total_relation_size('profile_players_staging')) AS staging_table_size,
    pg_size_pretty(pg_total_relation_size('dedup_pairs')) AS dedup_pairs_size;

\echo '========== Step 7k: Sample-100 spot check =========='
SELECT profile_id, tm_id, apif_id, display_name, data_confidence, match_tier
FROM profile_players_staging
WHERE tm_id IN ('296622', '670681', '584769', '578391', '148153')
   OR apif_id IN ('apif_746', 'apif_335051', 'apif_18929', 'apif_21138', 'apif_18963')
ORDER BY display_name;

\echo '========== DONE =========='
