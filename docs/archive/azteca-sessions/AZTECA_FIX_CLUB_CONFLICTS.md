# Azteca — Fix Club Conflict Detection (Step 8 redo)

**Priority:** Run now — the previous run flagged 5,583 false positives
**From:** Pelé
**Date:** March 14, 2026

## What went wrong

The previous Step 8 compared TM and APIF club names with exact string matching (`lower(trim(tm_club)) != lower(trim(apif_club))`). This treated "Real Madrid Club de Fútbol" vs "Real Madrid" as a conflict — but they're the same club. TM uses full legal names, APIF uses common short names. Almost all 5,583 "conflicts" are naming convention differences, not real transfer staleness.

## Fix: Rollback + smarter re-run

Run in order.

### Part 1: Rollback the false flags

```sql
-- 1a: Remove club_conflict_tm_apif from curation_reason
-- For players whose ONLY curation reason was club_conflict, clear everything
UPDATE players
SET
    needs_curation = FALSE,
    curation_reason = NULL
WHERE curation_reason = 'club_conflict_tm_apif';

-- 1b: For players who had OTHER curation reasons plus club_conflict, strip just the club part
UPDATE players
SET
    curation_reason = regexp_replace(curation_reason, ';\s*club_conflict_tm_apif', '')
WHERE curation_reason LIKE '%;%club_conflict_tm_apif%';

UPDATE players
SET
    curation_reason = regexp_replace(curation_reason, 'club_conflict_tm_apif;\s*', '')
WHERE curation_reason LIKE '%club_conflict_tm_apif;%';

-- 1c: Verify rollback — should be 0 club_conflict flags
SELECT COUNT(*) FILTER (WHERE curation_reason LIKE '%club_conflict%') AS remaining_club_flags
FROM players;

-- 1d: Curation queue after rollback
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS total_needs_curation
FROM players;
```

**Expected:** `remaining_club_flags = 0`. `total_needs_curation` should be back near 7,158 (the pre-Step-8 number).

---

### Part 2: Smarter club conflict detection

The key insight: if APIF's short name is **contained within** TM's long name (or vice versa), they're the same club. A real conflict is when NEITHER name contains the other.

Examples:
- TM "Real Madrid Club de Fútbol" contains APIF "Real Madrid" → SAME CLUB, no flag
- TM "Olympique Gymnaste Club Nice Côte d'Azur" does NOT contain APIF "U.N.A.M. - Pumas" → REAL CONFLICT, flag

Additional check: also compare the first significant word (after removing FC/Club/etc prefixes) to catch cases like "Inter" vs "Football Club Internazionale Milano S.p.A." where the short name isn't a literal substring.

```sql
-- 2a: Build smart club conflicts — only flag when names genuinely differ
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
  -- Exact match after normalization → not a conflict
  AND lower(trim(dp.tm_club)) != lower(trim(dp.apif_club))
  -- Containment check: if short name is inside long name → same club
  AND NOT (
      lower(trim(dp.tm_club)) LIKE '%' || lower(trim(dp.apif_club)) || '%'
      OR
      lower(trim(dp.apif_club)) LIKE '%' || lower(trim(dp.tm_club)) || '%'
  );

-- 2b: How many REAL conflicts?
SELECT COUNT(*) AS real_club_conflicts FROM _club_conflicts_v2;

-- 2c: Show them ALL (or top 50 if too many)
SELECT * FROM _club_conflicts_v2 ORDER BY tm_market_value DESC NULLS LAST LIMIT 50;

-- 2d: Spot check — show some high-value ones so Pelé can verify they're real
SELECT
    tm_name, tm_says, apif_says, tm_market_value
FROM _club_conflicts_v2
WHERE tm_market_value > 10000000
ORDER BY tm_market_value DESC;
```

**STOP HERE. Paste the output for Part 2 BEFORE running Part 3.** Pelé needs to verify the conflicts are real before we flag them.

---

### Part 3: Flag verified conflicts (ONLY after Pelé confirms)

```sql
-- 3a: Flag real club conflicts in the warehouse
UPDATE players p
SET
    needs_curation = TRUE,
    curation_reason = CASE
        WHEN p.curation_reason IS NOT NULL
        THEN p.curation_reason || '; club_conflict_tm_apif'
        ELSE 'club_conflict_tm_apif'
    END
FROM _club_conflicts_v2 cc
JOIN player_aliases pa
    ON pa.alias_type = 'transfermarkt_id' AND pa.alias_value = cc.tm_id
WHERE p.id = pa.player_id;

-- 3b: Report
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS total_needs_curation,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%club_conflict%') AS club_conflict,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%potential_duplicate%') AS post_load_dup,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%multi_match%') AS multi_match_ambiguous,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%missing_%') AS missing_fields,
    COUNT(*) FILTER (WHERE curation_reason = 'initial_only') AS orphan_initial_only
FROM players;
```

Save ALL output to **`AZTECA_FIX_CLUB_CONFLICTS_RESULTS.md`**.

---

## Important

- Run Part 1 and Part 2 together.
- **STOP after Part 2.** Paste results. Wait for Pelé to confirm before Part 3.
- The containment check won't catch every edge case (e.g., "Inter" vs "Internazionale" since "Inter" is a substring of "Internazionale" — that one actually DOES work). But it will eliminate the vast majority of false positives.
