-- AZTECA_FIX_CLUB_CONFLICTS — Part 1 (rollback) + Part 2 (smarter detection). STOP before Part 3.
\echo '========== PART 1: Rollback false flags =========='

\echo '---------- 1a: Clear players whose ONLY reason was club_conflict ----------'
UPDATE players
SET
    needs_curation = FALSE,
    curation_reason = NULL
WHERE curation_reason = 'club_conflict_tm_apif';

\echo '---------- 1b: Strip club_conflict from composite curation_reason ----------'
UPDATE players
SET
    curation_reason = regexp_replace(curation_reason, ';\s*club_conflict_tm_apif', '')
WHERE curation_reason LIKE '%;%club_conflict_tm_apif%';

UPDATE players
SET
    curation_reason = regexp_replace(curation_reason, 'club_conflict_tm_apif;\s*', '')
WHERE curation_reason LIKE '%club_conflict_tm_apif;%';

\echo '---------- 1c: Verify rollback — remaining club flags (expect 0) ----------'
SELECT COUNT(*) FILTER (WHERE curation_reason LIKE '%club_conflict%') AS remaining_club_flags
FROM players;

\echo '---------- 1d: Curation queue after rollback ----------'
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS total_needs_curation
FROM players;

\echo '========== PART 2: Smarter club conflict detection =========='

\echo '---------- 2a: Build _club_conflicts_v2 (no containment = real conflict) ----------'
DROP TABLE IF EXISTS _club_conflicts_v2;

CREATE TEMP TABLE _club_conflicts_v2 AS
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
  AND lower(trim(dp.tm_club)) != lower(trim(dp.apif_club))
  AND NOT (
      lower(trim(dp.tm_club)) LIKE '%' || lower(trim(dp.apif_club)) || '%'
      OR
      lower(trim(dp.apif_club)) LIKE '%' || lower(trim(dp.tm_club)) || '%'
  );

\echo '---------- 2b: Real club conflicts count ----------'
SELECT COUNT(*) AS real_club_conflicts FROM _club_conflicts_v2;

\echo '---------- 2c: All real conflicts (top 50 by value) ----------'
SELECT * FROM _club_conflicts_v2 ORDER BY tm_market_value DESC NULLS LAST LIMIT 50;

\echo '---------- 2d: High-value real conflicts (>10M) spot check ----------'
SELECT
    tm_name, tm_says, apif_says, tm_market_value
FROM _club_conflicts_v2
WHERE tm_market_value > 10000000
ORDER BY tm_market_value DESC;

\echo '========== STOP — Part 3 only after Pelé confirms =========='
