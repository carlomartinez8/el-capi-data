# AZTECA: Execute Full Dedup Pipeline on pipeline_players

**Priority:** HIGH — Execute now  
**From:** Pelé (Strategy & PM), approved by Carlo  
**Date:** March 13, 2026  
**Handoff to:** Azteca — full picture, SQL in order, expected results, and when to STOP vs proceed.

---

## Kill switch (Step 7g) — read this first

**Duplicate integrity check (7g) is the kill switch.**

- After Step 7 you will run query **7g**: it checks that every `tm_id` and every `apif_id` appears **at most once** in `profile_players_staging`.
- **If 7g returns ANY rows** → **STOP.** Do not build on this output. You have a data integrity bug (same ID in multiple profiles). Report to Pelé and wait.
- **If 7g returns ZERO rows** → OK to proceed; the staging table is safe to use for the next steps.

---

## Context — What happened while you were away

After you delivered the sample-100 analysis ([AZTECA_SAMPLE_100_RAW_OUTPUT.txt](./AZTECA_SAMPLE_100_RAW_OUTPUT.txt)), Pelé used that data to:

1. **Built DEDUP_RULES.docx** — A comprehensive 10-section rules document defining how to parse names, deduplicate cross-source records, merge profiles, and flag uncertain data for manual curation. Carlo approved it.

2. **Ran a dev test in Python** — Processed all 100 sample players + the 30 cross-source counterparts you found in C.1. Results:
   - **30/30 Tier 2 pairs matched** (last_token + DOB + nationality)
   - **29/29 validated** against your C.1 known pairs — 100% recall, 0 false positives
   - **100 unique profiles** produced: 30 VERIFIED, 56 PROJECTED, 1 PARTIAL, 13 ORPHAN
   - **14 flagged NEEDS_CURATION** (14%) — all for legitimate reasons (missing DOB, initial-only name, missing nationality)

3. **Carlo's directive:** "Anything not 100% certain gets flagged for manual curation." Zero auto-decisions on uncertain data. The pipeline produces clean data plus a curation queue.

Now we need you to run this at full scale against the entire `pipeline_players` table (49,287 records).

---

## Why the rules work — sample evidence (your 100-player run)

Evidence comes from the same 100-player sample (seed 0.42) and [AZTECA_SAMPLE_100_RAW_OUTPUT.txt](./AZTECA_SAMPLE_100_RAW_OUTPUT.txt).

| What | Evidence |
|------|----------|
| **Tier 2 rule (last token + DOB + nationality)** | **C.1** returned **30 pairs** — same person, different source. Examples: "Dwight McNeil" (TM) ↔ "D. McNeil" (APIF), "Karl Toko Ekambi" ↔ "K. Toko Ekambi", "Maxim Dal" ↔ "Maxim Bora Dal", "R. Aït-Nouri" ↔ "Rayan Aït-Nouri". Last token + DOB + nationality matches despite initials/full-name differences. |
| **Why we need last token, not just DOB+nation** | **C.2** returned **49 rows** (DOB + nationality only). That includes false positives: e.g. "L. Gamba" vs "L. Messi" (same DOB+nation, different people). Tier 2 adds last token, so those are correctly not merged. |
| **Cross-source twin counts** | **C.3**: 14 of 28 APIF in sample have a TM twin; 21 of 75 TM have an APIF twin. Confirms Tier 2 is finding real cross-source pairs at scale. |
| **Why name-only matching is dangerous** | **F.1**: In the full 49K, "Paulinho" appears 16 times, "João Pedro" 15, "Gabriel Silva" multiple. **F.2**: 13 of our 100 have name twins. DOB + nationality are required as tiebreakers. |

So: Tier 2 (last token + DOB + nationality) is validated on the sample; 7g ensures no ID is duplicated in the output.

---

## SQL execution order (checklist)

Run in this order only. Do not reorder.

| Step | Action | Output to check |
|------|--------|------------------|
| 1 | Create `profile_players_staging` + indexes | Table created |
| 2 | Create `strip_accents()` function | Function created |
| 3 | Create `dedup_pairs` (Tier 2 join) | Report pair count; run "TM/APIF in multiple pairs" check — report if any rows |
| 4 | Insert merged profiles from `dedup_pairs` | — |
| 5 | Insert unmatched TM records | — |
| 6 | Insert unmatched APIF records | — |
| 7 | Run report queries **7a–7k** | **7g = kill switch: 0 rows required** |

---

## What you're building

A new staging table called `profile_players_staging` that contains one row per unique real-world player. It deduplicates TM and APIF records that refer to the same person, merges their data with TM taking priority (except current club where APIF wins), and flags anything uncertain.

---

## The Dedup Rule (Tier 2 — validated)

Two records from different sources are the **same person** if ALL THREE match:
1. **Last whitespace-delimited token of the name**, lowercased and accent-stripped
2. **Exact date_of_birth** (both non-null)
3. **Exact nationality** (both non-null, case-insensitive)

This was validated at 100% precision and 100% recall on the sample. It catches patterns like:
- "Dwight McNeil" (TM) ↔ "D. McNeil" (APIF) — last token "mcneil" matches
- "Karl Toko Ekambi" (TM) ↔ "K. Toko Ekambi" (APIF) — last token "ekambi" matches
- "Maxim Dal" (TM) ↔ "Maxim Bora Dal" (APIF) — last token "dal" matches

**Anti-merge blockers (hard rules):**
- Same source (both TM or both APIF) = NEVER merge (each source has unique IDs internally)
- Different DOB = NEVER merge
- Different nationality = NEVER merge

---

## EXECUTE THESE STEPS IN ORDER

### Step 1: Create the staging table

```sql
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
```

---

### Step 2: Create accent-stripping helper

```sql
CREATE OR REPLACE FUNCTION strip_accents(text) RETURNS text AS $$
    SELECT translate(
        $1,
        'àáâãäåæèéêëìíîïðòóôõöùúûüýÿñçšžőűÀÁÂÃÄÅÆÈÉÊËÌÍÎÏÐÒÓÔÕÖÙÚÛÜÝŸÑÇŠŽŐŰ',
        'aaaaaaaeeeeiiiidoooooouuuuyyncszouAAAAAAEEEEIIIIDOOOOOUUUUYYNCSZOU'
    );
$$ LANGUAGE sql IMMUTABLE;
```

---

### Step 3: Find all cross-source duplicate pairs (Tier 2)

This is the core dedup. It joins TM records against APIF records on last_token + DOB + nationality.

```sql
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
        -- Extract last token: split by space, take last element, lowercase, strip accents
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
    -- TM fields (higher priority)
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
    -- APIF fields
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
```

**Report immediately:**
```sql
SELECT COUNT(*) AS total_tier2_pairs FROM dedup_pairs;
```

**Also check for any TM or APIF ID appearing in more than one pair (would indicate a problem):**
```sql
SELECT 'TM in multiple pairs' AS issue, tm_id, COUNT(*)
FROM dedup_pairs GROUP BY tm_id HAVING COUNT(*) > 1
UNION ALL
SELECT 'APIF in multiple pairs', apif_id, COUNT(*)
FROM dedup_pairs GROUP BY apif_id HAVING COUNT(*) > 1
LIMIT 20;
```

If any player appears in multiple pairs, report it — we may need to pick the best match. If none, that's clean.

---

### Step 4: Insert merged profiles (Tier 2 pairs → VERIFIED)

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
    dp.tm_name AS display_name,  -- TM has the fuller name
    dp.date_of_birth,
    COALESCE(dp.tm_birth_country, dp.apif_birth_country),
    COALESCE(dp.tm_birth_city, dp.apif_birth_city),
    dp.nationality,
    COALESCE(dp.tm_nat2, dp.apif_nat2),
    COALESCE(dp.tm_height_cm, dp.apif_height_cm),
    dp.tm_foot,  -- APIF never has foot data
    COALESCE(dp.tm_photo, dp.apif_photo),
    COALESCE(dp.tm_position, dp.apif_position),
    dp.tm_sub_position,  -- APIF never has sub_position
    COALESCE(dp.apif_club, dp.tm_club),  -- Rule MG-3: APIF wins for current club
    dp.tm_market_value,
    dp.tm_url,
    'VERIFIED',
    FALSE,  -- Dual-source match = clean
    NULL,
    'Tier 2',
    'TM:' || dp.tm_id || ' + APIF:' || dp.apif_id
FROM dedup_pairs dp;
```

---

### Step 5: Insert unmatched TM records

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
    -- Confidence
    CASE
        WHEN pp.date_of_birth IS NOT NULL AND pp.nationality IS NOT NULL
        THEN 'PROJECTED'
        ELSE 'PARTIAL'
    END,
    -- Needs curation?
    CASE
        WHEN pp.date_of_birth IS NULL OR pp.nationality IS NULL
        THEN TRUE
        ELSE FALSE
    END,
    -- Curation reason
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

---

### Step 6: Insert unmatched APIF records

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
    -- Use name_short if it has more tokens (Rule NP-4)
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
    NULL,  -- No TM URL for APIF-only
    -- Confidence: ORPHAN if missing critical identity fields or initial-only name
    CASE
        WHEN pp.date_of_birth IS NULL OR pp.nationality IS NULL OR pp.name ~ '^[A-Z]\. '
        THEN 'ORPHAN'
        ELSE 'PROJECTED'
    END,
    -- Needs curation
    CASE
        WHEN pp.date_of_birth IS NULL OR pp.nationality IS NULL OR pp.name ~ '^[A-Z]\. '
        THEN TRUE
        ELSE FALSE
    END,
    -- Curation reason
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

### Step 7: Full Report — Run ALL of these queries and paste complete output

```sql
-- 7a: Total profiles
SELECT COUNT(*) AS total_profiles FROM profile_players_staging;

-- 7b: How many we started with vs ended with
SELECT
    (SELECT COUNT(*) FROM pipeline_players) AS input_records,
    (SELECT COUNT(*) FROM profile_players_staging) AS output_profiles,
    (SELECT COUNT(*) FROM dedup_pairs) AS merged_pairs,
    (SELECT COUNT(*) FROM pipeline_players) - (SELECT COUNT(*) FROM profile_players_staging) AS records_deduped;

-- 7c: Confidence breakdown
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

-- 7d: Match tier breakdown
SELECT match_tier, COUNT(*) AS count
FROM profile_players_staging
GROUP BY match_tier
ORDER BY count DESC;

-- 7e: Curation queue breakdown by reason
SELECT
    unnest(string_to_array(curation_reason, '; ')) AS reason,
    COUNT(*) AS count
FROM profile_players_staging
WHERE needs_curation = TRUE
GROUP BY reason
ORDER BY count DESC;

-- 7f: Total curation queue size
SELECT
    COUNT(*) AS total_needing_curation,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM profile_players_staging) * 100, 1) AS pct
FROM profile_players_staging
WHERE needs_curation = TRUE;

-- 7g: KILL SWITCH — Duplicate integrity check
-- Every tm_id and apif_id must appear AT MOST ONCE in profile_players_staging.
-- If this returns ANY rows → STOP. Do not use this run; report to Pelé.
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

-- 7h: Sample VERIFIED profiles (spot check the merges look right)
SELECT profile_id, tm_id, apif_id, display_name, date_of_birth, nationality, current_club
FROM profile_players_staging
WHERE data_confidence = 'VERIFIED'
ORDER BY display_name
LIMIT 25;

-- 7i: Sample ORPHAN profiles (spot check the curation flags)
SELECT profile_id, apif_id, display_name, date_of_birth, nationality, curation_reason
FROM profile_players_staging
WHERE data_confidence = 'ORPHAN'
ORDER BY display_name
LIMIT 25;

-- 7j: Table size
SELECT
    pg_size_pretty(pg_total_relation_size('profile_players_staging')) AS staging_table_size,
    pg_size_pretty(pg_total_relation_size('dedup_pairs')) AS dedup_pairs_size;

-- 7k: Spot check — find our sample-100 known players to verify they merged correctly
SELECT profile_id, tm_id, apif_id, display_name, data_confidence, match_tier
FROM profile_players_staging
WHERE tm_id IN ('296622', '670681', '584769', '578391', '148153')
   OR apif_id IN ('apif_746', 'apif_335051', 'apif_18929', 'apif_21138', 'apif_18963')
ORDER BY display_name;
```

---

## Expected results and alarm thresholds

Use this to decide **proceed** vs **flag** vs **stop**.

| Metric | Expected (OK) | FLAG — report but can proceed | STOP — do not proceed |
|--------|----------------|-------------------------------|------------------------|
| **7g: Duplicate check** | **0 rows** (no duplicate tm_id or apif_id) | — | **Any rows** → data integrity bug; stop and report |
| Total profiles | ~39,000–42,000 | < 35,000 or > 45,000 | — |
| Tier 2 pairs (dedup_pairs count) | ~5,000–10,000 | < 1,000 or > 15,000 | — |
| VERIFIED % | ~15–25% | < 5% or > 40% | — |
| PROJECTED % | ~55–70% | < 40% | — |
| Needs curation % | ~10–25% | > 40% | — |
| Step 3: TM or APIF in multiple pairs | 0 rows | Any rows → one ID matched to multiple; report for human review | — |

**Summary:** If **7g returns any rows, STOP** before building on this data. All other alarms are "flag and report" so Pelé can decide; only 7g is a hard stop.

---

## IMPORTANT WARNINGS

1. **DO NOT drop or modify `pipeline_players`** — it's source data, read-only
2. `profile_players_staging` and `dedup_pairs` are safe to drop/recreate — they're derived
3. If any query takes > 5 minutes, report the timeout and we'll optimize with indexes
4. If the duplicate check (7g) returns ANY rows, **STOP and report before continuing** — that's a data integrity issue we need to fix before trusting the output
5. If any APIF ID appears in multiple dedup_pairs (Step 3 check), report it — means our Tier 2 rule matched one APIF player to multiple TM players, which needs human review
6. Save **ALL** output (every query 7a–7k) to **`AZTECA_DEDUP_FULL_RESULTS.md`** in the el-capi repo root. Do not truncate.

---

## After Execution

Once you've reported the results, Pelé will:
1. Review the confidence breakdown against our sample predictions
2. Spot-check the merged profiles for correctness
3. Inspect any duplicate integrity issues
4. Plan the Wikipedia bio enrichment pass
5. Build the admin curation queue for NEEDS_CURATION records

Let's go.
