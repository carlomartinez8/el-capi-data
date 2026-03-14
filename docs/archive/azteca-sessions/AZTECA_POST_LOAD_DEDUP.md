# Azteca — Run Step 7: Post-load duplicate detection

**Priority:** Run now — the promotion is done but we skipped this step.
**From:** Pelé
**Date:** March 13, 2026

---

## Context

The promotion loaded 42,993 new players into the warehouse. 454 existing players were matched via alias and updated. But **184 existing players were NOT matched** — they didn't have a corresponding `tm_id` or `apif_id` in staging.

Some of those 184 are duplicates of newly loaded records (we already confirmed Pedri and Rodri appear twice with different UUIDs). We need to detect and flag these systematically.

**This is now Step 7 in AZTECA_PROMOTE_STAGING.md** — it runs every time we promote staging. We're running it retroactively since the promotion already happened.

---

## SQL — Run in order

The `_staging_warehouse_map` temp table from the promotion session is gone. We need to reconstruct which players are "legacy unmatched" by a different method: any player WITHOUT `source_records` (staging-loaded players always have this field set).

```sql
-- 7a: Find legacy players not matched to staging
-- Legacy players = no source_records field (they predate the staging load)
DROP TABLE IF EXISTS _unmatched_legacy;

CREATE TEMP TABLE _unmatched_legacy AS
SELECT p.id, p.known_as, p.date_of_birth, p.nationality_primary
FROM players p
WHERE p.source_records IS NULL;

-- 7b: How many?
SELECT COUNT(*) AS unmatched_legacy_players FROM _unmatched_legacy;

-- 7c: Find duplicates — legacy player shares name + DOB with a staging-loaded player
DROP TABLE IF EXISTS _post_load_duplicates;

CREATE TEMP TABLE _post_load_duplicates AS
SELECT
    legacy.id AS legacy_player_id,
    legacy.known_as AS legacy_name,
    new_p.id AS new_player_id,
    new_p.known_as AS new_name,
    new_p.data_confidence AS new_confidence,
    legacy.date_of_birth,
    legacy.nationality_primary
FROM _unmatched_legacy legacy
JOIN players new_p
    ON lower(legacy.known_as) = lower(new_p.known_as)
    AND legacy.date_of_birth = new_p.date_of_birth
    AND new_p.id != legacy.id
    AND new_p.source_records IS NOT NULL;

-- 7d: How many duplicate pairs?
SELECT COUNT(*) AS duplicate_pairs_found FROM _post_load_duplicates;

-- 7e: Show all duplicates
SELECT * FROM _post_load_duplicates ORDER BY legacy_name;

-- 7f: Flag BOTH sides for curation
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

-- 7g: Report
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS total_needs_curation,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%potential_duplicate_post_load%') AS flagged_post_load_dup
FROM players;

-- 7h: Confirm the known duplicates are flagged (spot check)
SELECT p.id, p.known_as, p.data_confidence, p.needs_curation, p.curation_reason, p.source_records
FROM players p
WHERE lower(p.known_as) IN ('pedri', 'rodri')
ORDER BY p.known_as, p.source_records NULLS FIRST;
```

---

Save full output to **`AZTECA_POST_LOAD_DEDUP_RESULTS.md`**.
