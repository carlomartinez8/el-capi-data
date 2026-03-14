# AZTECA: Fix 7g Kill Switch — Quarantine Multi-Match Pairs

**Priority:** HIGH — Execute now
**From:** Pelé (Strategy & PM)
**Date:** March 13, 2026
**Depends on:** Previous run left `dedup_pairs` and `profile_players_staging` in place. We'll rebuild from Step 3b.

---

## What happened

The pipeline ran successfully and found 5,890 Tier 2 pairs. But **7g triggered** because some IDs appear in more than one pair:

- **13 TM IDs** each matched to 2 different APIF partners
- **7+ APIF IDs** each matched to 2 different TM partners

**Root cause:** Multiple real, different people share the same last token + DOB + nationality across sources. For example, two different "J. Silva" players from Brazil born on the same day — Tier 2 can't tell which is the real cross-source twin.

**Scale:** ~40 ambiguous pairs out of 5,890 total (under 1%).

---

## The Fix: Step 3b — Quarantine Ambiguous Pairs

Per Carlo's directive: "anything not 100% → curation." We don't guess. We:

1. **Remove** all pairs where either ID appears more than once from `dedup_pairs`
2. **Save** them in `dedup_pairs_ambiguous` for the manual curation queue
3. **Let the affected IDs fall through** to Steps 5/6 as unmatched records
4. **Flag them** with `curation_reason = 'multi_match_ambiguous'` so curators know exactly why

This keeps Tier 2 precision at 100% — we only auto-merge pairs we're certain about.

---

## SQL Execution Order

Run these steps **in this exact order**. Steps 1-3 from the original pipeline are already done — do NOT re-run them.

| Step | Action | Status |
|------|--------|--------|
| 1 | Create `profile_players_staging` | ✅ Already done |
| 2 | Create `strip_accents()` | ✅ Already done |
| 3 | Create `dedup_pairs` | ✅ Already done (5,890 pairs) |
| **3b** | **Quarantine ambiguous pairs** | **NEW — run this** |
| 4 | Insert merged profiles (from cleaned `dedup_pairs`) | **Re-run** |
| 5 | Insert unmatched TM records | **Re-run** |
| 6 | Insert unmatched APIF records | **Re-run** |
| **6b** | **Flag ambiguous IDs for curation** | **NEW — run this** |
| 7 | Run report queries 7a–7k | **Re-run** |

---

### Step 3b: Quarantine ambiguous pairs (NEW)

```sql
-- 3b.1: Save ambiguous pairs to a separate table for curation queue
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

-- 3b.2: Report how many pairs were quarantined
SELECT COUNT(*) AS ambiguous_pairs_quarantined FROM dedup_pairs_ambiguous;

-- 3b.3: Show the ambiguous pairs so we can see what's going on
SELECT tm_id, tm_name, apif_id, apif_name, date_of_birth, nationality
FROM dedup_pairs_ambiguous
ORDER BY tm_id, apif_id;

-- 3b.4: Remove ambiguous pairs from dedup_pairs
DELETE FROM dedup_pairs
WHERE tm_id IN (SELECT tm_id FROM dedup_pairs_ambiguous)
   OR apif_id IN (SELECT apif_id FROM dedup_pairs_ambiguous);

-- 3b.5: Confirm dedup_pairs is now clean
SELECT 'TM still in multiple pairs' AS issue, tm_id, COUNT(*)
FROM dedup_pairs GROUP BY tm_id HAVING COUNT(*) > 1
UNION ALL
SELECT 'APIF still in multiple pairs', apif_id, COUNT(*)
FROM dedup_pairs GROUP BY apif_id HAVING COUNT(*) > 1;
-- ^^^ This MUST return 0 rows. If not, STOP.

-- 3b.6: Report cleaned pair count
SELECT COUNT(*) AS clean_pairs FROM dedup_pairs;
```

**Expected results:**
- 3b.2: ~30–50 ambiguous pairs quarantined
- 3b.5: 0 rows (all ambiguity removed)
- 3b.6: ~5,840–5,860 clean pairs remaining

---

### Steps 4–6: Re-run with cleaned dedup_pairs

**IMPORTANT:** First, truncate the staging table to start fresh:

```sql
TRUNCATE profile_players_staging;
ALTER SEQUENCE profile_players_staging_profile_id_seq RESTART WITH 1;
```

Now re-run **Steps 4, 5, and 6 exactly as written in AZTECA_DEDUP_EXECUTE.md** — no changes needed. The SQL already uses `dedup_pairs` (which is now clean) and `NOT IN (SELECT tm_id FROM dedup_pairs)` / `NOT IN (SELECT apif_id FROM dedup_pairs)` — so ambiguous IDs will correctly fall through as unmatched.

For convenience, here are the three inserts again (copy-paste from the original):

**Step 4: Insert merged profiles (Tier 2 pairs → VERIFIED)**

```sql
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
```

**Step 5: Insert unmatched TM records**

```sql
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
```

**Step 6: Insert unmatched APIF records**

```sql
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
```

---

### Step 6b: Flag ambiguous IDs for curation (NEW)

After Steps 4-6, the ambiguous IDs are now in the staging table as unmatched records (Tier 4). We need to flag them so curators know these players likely have a cross-source match that couldn't be auto-resolved.

```sql
-- 6b.1: Flag TM records that were in ambiguous pairs
UPDATE profile_players_staging
SET
    needs_curation = TRUE,
    curation_reason = CASE
        WHEN curation_reason IS NOT NULL THEN curation_reason || '; multi_match_ambiguous'
        ELSE 'multi_match_ambiguous'
    END
WHERE tm_id IN (SELECT tm_id FROM dedup_pairs_ambiguous);

-- 6b.2: Flag APIF records that were in ambiguous pairs
UPDATE profile_players_staging
SET
    needs_curation = TRUE,
    curation_reason = CASE
        WHEN curation_reason IS NOT NULL THEN curation_reason || '; multi_match_ambiguous'
        ELSE 'multi_match_ambiguous'
    END
WHERE apif_id IN (SELECT apif_id FROM dedup_pairs_ambiguous);

-- 6b.3: Report how many records were flagged
SELECT COUNT(*) AS records_flagged_multi_match
FROM profile_players_staging
WHERE curation_reason LIKE '%multi_match_ambiguous%';
```

**Expected:** ~30–60 records flagged (the IDs from both sides of the ambiguous pairs).

---

### Step 7: Re-run ALL report queries

Re-run **every query from Step 7 in AZTECA_DEDUP_EXECUTE.md** (7a through 7k) exactly as written.

**Critical: 7g MUST return 0 rows this time.** If it still returns rows, STOP and report — there's a deeper issue.

---

## Expected Results After Fix

| Metric | Previous (broken) | Expected (fixed) |
|--------|-------------------|-------------------|
| Total profiles | 43,430 | ~43,450–43,480 (slightly more, since ambiguous pairs become separate records) |
| Tier 2 pairs | 5,890 | ~5,840–5,860 |
| VERIFIED % | 13.6% | ~13.4–13.5% (tiny drop) |
| PROJECTED % | 70.1% | ~70.1% (unchanged) |
| Needs curation % | 16.3% | ~16.4–16.5% (tiny increase from multi_match flags) |
| **7g duplicate check** | **FAILED (13+ rows)** | **0 rows** |
| multi_match_ambiguous flags | N/A | ~30–60 records |

The impact is minimal — less than 1% of pairs affected. All the good data from the first run (McNeil, Neves, Dunk, Asensio, Aït-Nouri, etc.) will still be VERIFIED.

---

## After This Fix

Save ALL output to **`AZTECA_DEDUP_FIX_RESULTS.md`** in the el-capi repo root.

If 7g returns 0 rows → the staging table is safe. Pelé will proceed with:
1. Wikipedia bio enrichment (1,841 bios to merge in)
2. Admin curation queue build
3. `dedup_pairs_ambiguous` review — curators will manually resolve which pairs are real

---

## IMPORTANT

1. **DO NOT** re-run Steps 1–3. The `dedup_pairs` table from the first run is correct — we're just cleaning it.
2. **DO** truncate `profile_players_staging` before re-running Steps 4–6.
3. The `dedup_pairs_ambiguous` table is a keeper — it feeds the curation queue.
4. If 3b.5 returns any rows, STOP — the quarantine didn't catch everything.
