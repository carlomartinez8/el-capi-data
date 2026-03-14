# Azteca Task: Full 100-Player Sample Extraction for Dedup Rule Building

**From:** Pelé (Strategy & PM)
**To:** Azteca (Infrastructure)
**Date:** March 13, 2026
**Priority:** HIGH — this blocks the entire pipeline rebuild

---

## Context

We're building the profile deduplication rules. We need the COMPLETE raw data for 100 random players, plus cross-source analysis to understand how the same person appears differently across TM and APIF. The previous sample showed the structure but truncated the rows. This time I need EVERYTHING.

**CRITICAL:** Use a FIXED seed so the sample is reproducible. Use `setseed(0.42)` before the random() call. Every query below must use the SAME 100 players.

---

## Part A — The Base Sample (save as the anchor for all other queries)

Run this FIRST. This creates the sample that all other queries reference.

```sql
-- Create a temp table so all subsequent queries use the SAME 100 players
SELECT setseed(0.42);

CREATE TEMP TABLE sample_100 AS
SELECT id, name, name_short, date_of_birth, nationality, nationality_secondary,
  position, sub_position, foot, height_cm, current_club_name, jersey_number,
  market_value_eur, photo_url, country_of_birth, city_of_birth, transfermarkt_url
FROM pipeline_players
ORDER BY random()
LIMIT 100;
```

Then dump the full 100 rows:

```sql
SELECT * FROM sample_100 ORDER BY name;
```

**I need ALL 100 rows. Do not truncate. Copy the full output.**

---

## Part B — Name Structure Analysis

This is the most important part for building parsing rules.

### B.1 — Name token counts (how many words in each name?)

```sql
SELECT
  id,
  name,
  name_short,
  array_length(string_to_array(trim(name), ' '), 1) AS name_tokens,
  array_length(string_to_array(trim(COALESCE(name_short, '')), ' '), 1) AS short_tokens,
  CASE
    WHEN id LIKE 'apif_%' THEN 'APIF'
    ELSE 'TM'
  END AS source
FROM sample_100
ORDER BY name_tokens DESC, name;
```

### B.2 — Single-name players (potential mononyms like Neymar, Hulk)

```sql
SELECT id, name, name_short, nationality, position
FROM sample_100
WHERE array_length(string_to_array(trim(name), ' '), 1) = 1;
```

### B.3 — Players with initials in name (APIF pattern: "A. Diallo")

```sql
SELECT id, name, name_short, nationality, date_of_birth
FROM sample_100
WHERE name ~ '^[A-Z]\. '
   OR name ~ ' [A-Z]\. '
   OR name ~ '^[A-Z]\.[A-Z]\.';
```

### B.4 — Players with name prefixes (de, van, von, dos, el, al, etc.)

```sql
SELECT id, name, nationality
FROM sample_100
WHERE name ~* '\y(de|di|da|do|dos|van|von|el|al|ben|bin|le|la|mc|mac|del|della|lo|las|los|san|saint|st)\y';
```

### B.5 — Compound/hyphenated last names

```sql
SELECT id, name, nationality
FROM sample_100
WHERE name LIKE '%-%';
```

---

## Part C — Cross-Source Duplicate Detection

This is where we find if any of the 100 sample players exist TWICE in pipeline_players (once as TM, once as APIF).

### C.1 — Find potential duplicates: same last-name-token + same DOB + same nationality

```sql
WITH sample_parsed AS (
  SELECT
    s.id,
    s.name,
    s.date_of_birth,
    s.nationality,
    -- Extract last token as approximate last name
    split_part(s.name, ' ', array_length(string_to_array(trim(s.name), ' '), 1)) AS last_token,
    CASE WHEN s.id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS source
  FROM sample_100 s
  WHERE s.date_of_birth IS NOT NULL
)
SELECT
  a.id AS id_a, a.name AS name_a, a.source AS source_a,
  b.id AS id_b, b.name AS name_b, b.source AS source_b,
  a.date_of_birth, a.nationality
FROM sample_parsed a
JOIN pipeline_players b
  ON b.date_of_birth = a.date_of_birth
  AND b.nationality = a.nationality
  AND b.id != a.id
  AND split_part(b.name, ' ', array_length(string_to_array(trim(b.name), ' '), 1)) = a.last_token
ORDER BY a.name;
```

### C.2 — Broader duplicate search: same DOB + same nationality (even if last name doesn't match exactly)

```sql
SELECT
  s.id AS sample_id, s.name AS sample_name,
  CASE WHEN s.id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS sample_source,
  p.id AS match_id, p.name AS match_name,
  CASE WHEN p.id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS match_source,
  s.date_of_birth, s.nationality
FROM sample_100 s
JOIN pipeline_players p
  ON p.date_of_birth = s.date_of_birth
  AND p.nationality = s.nationality
  AND p.id != s.id
ORDER BY s.name;
```

This will show ALL players in the full 49K table who share DOB + nationality with our sample. Some will be true duplicates (same person, different source), some will be coincidences (different people, same DOB + nationality). We need to see both to calibrate the rules.

### C.3 — How many of our 100 have a cross-source twin?

```sql
SELECT
  CASE WHEN s.id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS sample_source,
  COUNT(*) AS total_in_sample,
  COUNT(DISTINCT twin.id) AS has_cross_source_twin
FROM sample_100 s
LEFT JOIN pipeline_players twin
  ON twin.date_of_birth = s.date_of_birth
  AND twin.nationality = s.nationality
  AND twin.id != s.id
  AND (
    (s.id LIKE 'apif_%' AND twin.id NOT LIKE 'apif_%')
    OR (s.id NOT LIKE 'apif_%' AND twin.id LIKE 'apif_%')
  )
GROUP BY 1;
```

---

## Part D — Wikipedia Bio Linkage for Sample

### D.1 — Which of our 100 have Wikipedia bios, and what do they say?

```sql
SELECT
  s.id, s.name, s.nationality, s.date_of_birth,
  b.bio_source,
  LEFT(b.bio_summary, 200) AS bio_preview,
  b.wikipedia_url
FROM sample_100 s
JOIN player_bios b ON b.player_id = s.id
ORDER BY s.name;
```

---

## Part E — Field Completeness Matrix

### E.1 — Per-field null rates for the 100 players, split by source

```sql
SELECT
  CASE WHEN id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS source,
  COUNT(*) AS total,
  COUNT(name) AS has_name,
  COUNT(name_short) AS has_name_short,
  COUNT(date_of_birth) AS has_dob,
  COUNT(nationality) AS has_nationality,
  COUNT(nationality_secondary) AS has_nat2,
  COUNT(position) AS has_position,
  COUNT(sub_position) AS has_subpos,
  COUNT(foot) AS has_foot,
  COUNT(height_cm) AS has_height,
  COUNT(current_club_name) AS has_club,
  COUNT(jersey_number) AS has_jersey,
  COUNT(market_value_eur) AS has_market_value,
  COUNT(country_of_birth) AS has_birth_country,
  COUNT(city_of_birth) AS has_birth_city,
  COUNT(transfermarkt_url) AS has_tm_url
FROM sample_100
GROUP BY 1;
```

---

## Part F — Name Collision Check (Different People, Same Name)

### F.1 — Are there name collisions in the full 49K dataset?

```sql
SELECT name, COUNT(*) AS occurrences,
  COUNT(DISTINCT nationality) AS distinct_nationalities,
  COUNT(DISTINCT date_of_birth) AS distinct_dobs
FROM pipeline_players
GROUP BY name
HAVING COUNT(*) > 1
ORDER BY occurrences DESC
LIMIT 30;
```

This shows the most common duplicate names in the full database. Critical for understanding why name-only matching is dangerous.

### F.2 — Do any of our 100 sample players have name collisions?

```sql
SELECT s.name, s.id, s.nationality, s.date_of_birth,
  (SELECT COUNT(*) FROM pipeline_players p WHERE p.name = s.name AND p.id != s.id) AS name_twins
FROM sample_100 s
WHERE (SELECT COUNT(*) FROM pipeline_players p WHERE p.name = s.name AND p.id != s.id) > 0
ORDER BY name_twins DESC;
```

---

## Output Instructions

1. **Run Part A first** — create the temp table, then dump all 100 rows sorted by name.
2. **Run Parts B through F** in order. Each query is independent (they all reference sample_100).
3. **Paste FULL output for every query.** Do not summarize. Do not truncate. I need every row.
4. **If a query returns 0 rows, say so** — that's useful information (e.g., "no single-name players in sample").
5. **Label each result clearly** (e.g., "Query B.1 Result:").
6. **Save everything to** `AZTECA_SAMPLE_100_FULL_ANALYSIS.md` at the repo root (`/Users/carlomartinez/carlo-projects/el-capi/`).

Total queries: 14. Expected runtime: under 30 seconds total (all against indexed tables).

---

## What Pelé Will Build From This

- Name parsing algorithm (first / middle / last / prefix / nickname detection)
- Dedup matching rules (Tier 1: ID match, Tier 2: DOB+last+nationality, Tier 3: fuzzy)
- Anti-merge blockers (name collisions, different people same name)
- Field completeness expectations per source type
- Cross-source join success rate baseline

**This is the foundation work. Accuracy is everything. Take your time.**
