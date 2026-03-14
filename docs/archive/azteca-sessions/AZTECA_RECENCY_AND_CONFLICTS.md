# Azteca — Recency Audit + Club Conflict Detection

**Priority:** Run now — last two steps before warehouse is fully production-ready
**From:** Pelé
**Date:** March 14, 2026

Two tasks, run in order. Both are read+flag operations on permanent tables (no temp table dependencies).

---

## Task 1: Recency Audit (read-only diagnostic)

Run every query from **`AZTECA_RECENCY_AUDIT.md`** and paste full output. This tells us how stale our club data is.

Quick reminder — those queries check:
1. Club conflicts in VERIFIED pairs (TM vs APIF disagree)
2. Sample conflicts
3. High-value conflicts (most visible to users)
4. Top 25 players by market value — what clubs are they showing?
5. Which source's club did we use for VERIFIED profiles?
6. Profiles with no club at all

Save output to **`AZTECA_RECENCY_AUDIT_RESULTS.md`**.

---

## Task 2: Club Conflict Detection (Step 8 from promotion pipeline)

This is Step 8 from `AZTECA_PROMOTE_STAGING.md`. It FLAGS warehouse records for curation where TM and APIF disagree on current_club. Zero cost, purely SQL.

Run these queries and paste full output:

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

-- 8c: Show top conflicts by market value (these are the most visible to users)
SELECT * FROM _club_conflicts ORDER BY tm_market_value DESC NULLS LAST LIMIT 30;

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

-- 8e: Report — how many flagged?
SELECT
    COUNT(*) FILTER (WHERE curation_reason LIKE '%club_conflict%') AS flagged_club_conflict
FROM players;

-- 8f: Updated curation queue total
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS total_needs_curation,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%club_conflict%') AS club_conflict,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%potential_duplicate%') AS post_load_dup,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%multi_match%') AS multi_match_ambiguous,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%missing_%') AS missing_fields,
    COUNT(*) FILTER (WHERE curation_reason = 'initial_only') AS orphan_initial_only
FROM players;
```

Save ALL output (both tasks) to **`AZTECA_RECENCY_AND_CONFLICTS_RESULTS.md`**.

---

## What this tells us

The recency audit shows us the **scale** of club data staleness. The club conflict detection **flags** the stale records so they enter the curation queue automatically on every future promotion.

After this, the warehouse curation breakdown will be:
- `club_conflict_tm_apif` — TM and APIF disagree on current club
- `potential_duplicate_post_load` — legacy player might be a dup of a newly loaded record
- `multi_match_ambiguous` — twins/brothers that dedup couldn't safely resolve
- `missing_dob`, `missing_nationality` — identity gaps
- `initial_only` — ORPHAN profiles with single source, no verification

This is the full picture Pelé needs to prioritize the admin curation queue build.
