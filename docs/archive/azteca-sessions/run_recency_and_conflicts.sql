-- AZTECA_RECENCY_AND_CONFLICTS — Task 1: Recency audit (read-only) + Task 2: Club conflict detection
\echo '========== TASK 1: Recency Audit (from AZTECA_RECENCY_AUDIT.md) =========='

\echo '---------- 1: Club conflicts in VERIFIED (counts) ----------'
SELECT COUNT(*) AS total_verified_pairs FROM dedup_pairs;

SELECT COUNT(*) AS club_conflicts
FROM dedup_pairs
WHERE tm_club IS NOT NULL
  AND apif_club IS NOT NULL
  AND lower(trim(tm_club)) != lower(trim(apif_club));

\echo '---------- 2: Sample club conflicts (30) ----------'
SELECT
    tm_id, tm_name, apif_id, apif_name,
    tm_club AS tm_says,
    apif_club AS apif_says,
    date_of_birth, nationality
FROM dedup_pairs
WHERE tm_club IS NOT NULL
  AND apif_club IS NOT NULL
  AND lower(trim(tm_club)) != lower(trim(apif_club))
ORDER BY tm_name
LIMIT 30;

\echo '---------- 3: High-value club conflicts (30) ----------'
SELECT
    tm_name, tm_club AS tm_says, apif_club AS apif_says,
    tm_market_value
FROM dedup_pairs
WHERE tm_club IS NOT NULL
  AND apif_club IS NOT NULL
  AND lower(trim(tm_club)) != lower(trim(apif_club))
  AND tm_market_value IS NOT NULL
ORDER BY tm_market_value DESC
LIMIT 30;

\echo '---------- 4: Top 25 players by value — current_club in warehouse ----------'
SELECT
    p.known_as,
    pc.current_club,
    pc.estimated_value_eur,
    p.data_confidence,
    p.source_records
FROM players p
JOIN player_career pc ON p.id = pc.player_id
WHERE pc.estimated_value_eur IS NOT NULL
ORDER BY pc.estimated_value_eur DESC
LIMIT 25;

\echo '---------- 5: VERIFIED — which source club did we use? (top 25 by value) ----------'
SELECT
    dp.tm_name,
    dp.tm_club,
    dp.apif_club,
    pps.current_club AS staging_chose,
    dp.tm_market_value
FROM dedup_pairs dp
JOIN profile_players_staging pps
    ON pps.tm_id = dp.tm_id AND pps.apif_id = dp.apif_id
WHERE dp.tm_market_value IS NOT NULL
ORDER BY dp.tm_market_value DESC
LIMIT 25;

\echo '---------- 6: Profiles with NO club (by confidence) ----------'
SELECT
    data_confidence,
    COUNT(*) FILTER (WHERE current_club IS NULL OR current_club = '') AS no_club,
    COUNT(*) AS total
FROM profile_players_staging
GROUP BY data_confidence
ORDER BY
    CASE data_confidence
        WHEN 'VERIFIED' THEN 1
        WHEN 'PROJECTED' THEN 2
        WHEN 'PARTIAL' THEN 3
        WHEN 'ORPHAN' THEN 4
    END;

\echo '========== TASK 2: Club Conflict Detection (Step 8) =========='

\echo '---------- 8a: Build _club_conflicts (TM vs APIF disagree) ----------'
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

\echo '---------- 8b: Club conflicts count ----------'
SELECT COUNT(*) AS club_conflicts FROM _club_conflicts;

\echo '---------- 8c: Top conflicts by market value (30) ----------'
SELECT * FROM _club_conflicts ORDER BY tm_market_value DESC NULLS LAST LIMIT 30;

\echo '---------- 8d: Flag warehouse players for curation ----------'
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

\echo '---------- 8e: Flagged with club_conflict ----------'
SELECT
    COUNT(*) FILTER (WHERE curation_reason LIKE '%club_conflict%') AS flagged_club_conflict
FROM players;

\echo '---------- 8f: Curation queue breakdown ----------'
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS total_needs_curation,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%club_conflict%') AS club_conflict,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%potential_duplicate%') AS post_load_dup,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%multi_match%') AS multi_match_ambiguous,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%missing_%') AS missing_fields,
    COUNT(*) FILTER (WHERE curation_reason = 'initial_only') AS orphan_initial_only
FROM players;

\echo '========== DONE =========='
