# Azteca — Data Recency Audit

**Priority:** HIGH — Run before we go live
**From:** Pelé
**Date:** March 13, 2026

We need to understand how stale our club data is before the app shows it to users. Run these queries and paste full output.

```sql
-- 1: Club conflicts in VERIFIED profiles (TM vs APIF disagree)
SELECT COUNT(*) AS total_verified_pairs FROM dedup_pairs;

SELECT COUNT(*) AS club_conflicts
FROM dedup_pairs
WHERE tm_club IS NOT NULL
  AND apif_club IS NOT NULL
  AND lower(trim(tm_club)) != lower(trim(apif_club));

-- 2: Sample club conflicts — show both clubs so we can see the pattern
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

-- 3: Club conflicts among HIGH-VALUE players (most visible to users)
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

-- 4: What does the current club look like for the top 25 players by market value?
-- These are the players users WILL search for.
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

-- 5: For VERIFIED profiles, which source's club did we use?
-- (Rule MG-3: APIF wins for current_club via COALESCE(apif_club, tm_club))
-- Show the top 25 by value with both source clubs for comparison
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

-- 6: How many profiles have NO club at all?
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
```

Save full output to **`AZTECA_RECENCY_AUDIT_RESULTS.md`**.
