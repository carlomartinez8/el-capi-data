# AZTECA: Wikipedia Bio Enrichment on profile_players_staging

**Priority:** MEDIUM — Execute after confirming staging is clean (7g passed)
**From:** Pelé (Strategy & PM)
**Date:** March 13, 2026
**Depends on:** `profile_players_staging` (43,447 profiles, 7g passed), `player_bios` table (1,841 Wikipedia bios)

---

## What we're doing

The `player_bios` table has ~1,841 Wikipedia biographical summaries linked to `pipeline_players` by `player_id`. We're going to:

1. Add `wikipedia_url` and `wikipedia_bio` columns to `profile_players_staging`
2. Match bios to profiles via `tm_id` or `apif_id`
3. Report coverage

This is a pure enrichment pass — no dedup, no risk to existing data.

---

## Step 1: Add Wikipedia columns to staging

```sql
ALTER TABLE profile_players_staging
ADD COLUMN IF NOT EXISTS wikipedia_url TEXT,
ADD COLUMN IF NOT EXISTS wikipedia_bio TEXT;
```

---

## Step 2: Understand what we're working with

```sql
-- 2a: How many bios exist?
SELECT COUNT(*) AS total_bios FROM player_bios;

-- 2b: How many are TM-linked vs APIF-linked?
SELECT
    CASE WHEN player_id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS source,
    COUNT(*) AS bio_count
FROM player_bios
GROUP BY 1;

-- 2c: How many bios match a profile in staging?
SELECT COUNT(*) AS bios_matching_staging
FROM player_bios pb
WHERE pb.player_id IN (SELECT tm_id FROM profile_players_staging WHERE tm_id IS NOT NULL)
   OR pb.player_id IN (SELECT apif_id FROM profile_players_staging WHERE apif_id IS NOT NULL);

-- 2d: Sample bios — what do they look like?
SELECT player_id, wikipedia_url, LEFT(bio_summary, 200) AS bio_preview
FROM player_bios
LIMIT 10;
```

**Report these numbers before proceeding.**

---

## Step 3: Enrich profiles with Wikipedia data

```sql
-- 3a: Update profiles where the TM ID matches a bio
UPDATE profile_players_staging pps
SET
    wikipedia_url = pb.wikipedia_url,
    wikipedia_bio = pb.bio_summary,
    updated_at = NOW()
FROM player_bios pb
WHERE pps.tm_id = pb.player_id
  AND pps.tm_id IS NOT NULL;

-- 3b: Update profiles where the APIF ID matches a bio (only if not already enriched via TM)
UPDATE profile_players_staging pps
SET
    wikipedia_url = COALESCE(pps.wikipedia_url, pb.wikipedia_url),
    wikipedia_bio = COALESCE(pps.wikipedia_bio, pb.bio_summary),
    updated_at = NOW()
FROM player_bios pb
WHERE pps.apif_id = pb.player_id
  AND pps.apif_id IS NOT NULL
  AND pps.wikipedia_bio IS NULL;
```

The COALESCE in 3b ensures that if a VERIFIED profile already got a bio via its TM ID, we don't overwrite it with a potentially different APIF-linked bio.

---

## Step 4: Report

```sql
-- 4a: How many profiles were enriched?
SELECT COUNT(*) AS profiles_with_wikipedia
FROM profile_players_staging
WHERE wikipedia_bio IS NOT NULL;

-- 4b: Enrichment by confidence level
SELECT
    data_confidence,
    COUNT(*) FILTER (WHERE wikipedia_bio IS NOT NULL) AS has_wiki,
    COUNT(*) AS total,
    ROUND(
        COUNT(*) FILTER (WHERE wikipedia_bio IS NOT NULL)::numeric / COUNT(*) * 100, 1
    ) AS wiki_pct
FROM profile_players_staging
GROUP BY data_confidence
ORDER BY
    CASE data_confidence
        WHEN 'VERIFIED' THEN 1
        WHEN 'PROJECTED' THEN 2
        WHEN 'PARTIAL' THEN 3
        WHEN 'ORPHAN' THEN 4
    END;

-- 4c: Sample enriched profiles
SELECT profile_id, tm_id, apif_id, display_name, data_confidence,
       wikipedia_url, LEFT(wikipedia_bio, 150) AS bio_preview
FROM profile_players_staging
WHERE wikipedia_bio IS NOT NULL
ORDER BY display_name
LIMIT 25;

-- 4d: Any bios that didn't match a profile? (orphaned bios)
SELECT COUNT(*) AS orphaned_bios
FROM player_bios pb
WHERE pb.player_id NOT IN (SELECT tm_id FROM profile_players_staging WHERE tm_id IS NOT NULL)
  AND pb.player_id NOT IN (SELECT apif_id FROM profile_players_staging WHERE apif_id IS NOT NULL);

-- 4e: Updated table size
SELECT pg_size_pretty(pg_total_relation_size('profile_players_staging')) AS staging_table_size;
```

---

## Expected results

| Metric | Expected |
|--------|----------|
| Total bios in player_bios | ~1,841 |
| Bios matching staging profiles | ~1,700–1,841 (most should match) |
| Orphaned bios (no matching profile) | ~0–140 (if any bios reference IDs not in pipeline_players) |
| VERIFIED profiles with Wikipedia | Higher % than PROJECTED (popular players more likely to have bios) |

---

## After this

Save output to **`AZTECA_WIKIPEDIA_ENRICHMENT_RESULTS.md`** in the el-capi repo root.

Once done, Pelé will:
1. Review coverage and sample quality
2. Plan the staging → production promotion
3. Build the admin curation queue

---

## IMPORTANT

1. **DO NOT** modify `player_bios` — it's source data, read-only
2. The ALTER TABLE adds nullable columns — no existing data is changed
3. If any step takes > 5 minutes, report the timeout
4. This is enrichment only — no rows are added or removed from staging
