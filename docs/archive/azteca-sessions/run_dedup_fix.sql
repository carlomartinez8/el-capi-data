-- AZTECA_DEDUP_FIX — Quarantine multi-match pairs, re-run inserts, report
\echo '========== Step 3b.1: Create dedup_pairs_ambiguous =========='
DROP TABLE IF EXISTS dedup_pairs_ambiguous;

CREATE TABLE dedup_pairs_ambiguous AS
SELECT dp.*
FROM dedup_pairs dp
WHERE dp.tm_id IN (
    SELECT tm_id FROM dedup_pairs GROUP BY tm_id HAVING COUNT(*) > 1
)
OR dp.apif_id IN (
    SELECT apif_id FROM dedup_pairs GROUP BY apif_id HAVING COUNT(*) > 1
);

\echo '========== Step 3b.2: Ambiguous pairs quarantined =========='
SELECT COUNT(*) AS ambiguous_pairs_quarantined FROM dedup_pairs_ambiguous;

\echo '========== Step 3b.3: Ambiguous pairs (sample) =========='
SELECT tm_id, tm_name, apif_id, apif_name, date_of_birth, nationality
FROM dedup_pairs_ambiguous
ORDER BY tm_id, apif_id;

\echo '========== Step 3b.4: Remove ambiguous from dedup_pairs =========='
DELETE FROM dedup_pairs
WHERE tm_id IN (SELECT tm_id FROM dedup_pairs_ambiguous)
   OR apif_id IN (SELECT apif_id FROM dedup_pairs_ambiguous);

\echo '========== Step 3b.5: Confirm no ID in multiple pairs (MUST be 0 rows) =========='
SELECT 'TM still in multiple pairs' AS issue, tm_id, COUNT(*)
FROM dedup_pairs GROUP BY tm_id HAVING COUNT(*) > 1
UNION ALL
SELECT 'APIF still in multiple pairs', apif_id, COUNT(*)
FROM dedup_pairs GROUP BY apif_id HAVING COUNT(*) > 1;

\echo '========== Step 3b.6: Clean pair count =========='
SELECT COUNT(*) AS clean_pairs FROM dedup_pairs;

\echo '========== Truncate staging, restart sequence =========='
TRUNCATE profile_players_staging;
ALTER SEQUENCE profile_players_staging_profile_id_seq RESTART WITH 1;

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
    dp.tm_name AS display_name,
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

\echo '========== Step 6b.1–6b.2: Flag ambiguous IDs =========='
UPDATE profile_players_staging
SET
    needs_curation = TRUE,
    curation_reason = CASE
        WHEN curation_reason IS NOT NULL THEN curation_reason || '; multi_match_ambiguous'
        ELSE 'multi_match_ambiguous'
    END
WHERE tm_id IN (SELECT tm_id FROM dedup_pairs_ambiguous);

UPDATE profile_players_staging
SET
    needs_curation = TRUE,
    curation_reason = CASE
        WHEN curation_reason IS NOT NULL THEN curation_reason || '; multi_match_ambiguous'
        ELSE 'multi_match_ambiguous'
    END
WHERE apif_id IN (SELECT apif_id FROM dedup_pairs_ambiguous);

\echo '========== Step 6b.3: Records flagged multi_match =========='
SELECT COUNT(*) AS records_flagged_multi_match
FROM profile_players_staging
WHERE curation_reason LIKE '%multi_match_ambiguous%';

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

\echo '========== Step 7g: KILL SWITCH — Duplicate integrity (MUST be 0 rows) =========='
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
