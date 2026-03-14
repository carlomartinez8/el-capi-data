# Azteca Sample 100 — Full Analysis

**Task:** [AZTECA_SAMPLE_100_TASK.md](./AZTECA_SAMPLE_100_TASK.md)  
**Date:** March 2026  
**Executor:** Azteca  
**Seed:** `setseed(0.42)` — reproducible 100-player sample from `pipeline_players`

All 14 queries run in a single psql session so `sample_100` temp table persists. Full output below; no truncation.

---

## Fix applied

- **Part C.1:** Query referenced `b.source` but `pipeline_players` has no `source` column. Replaced with `CASE WHEN b.id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS source_b`.

---

## Headline numbers

| Part | Result |
|------|--------|
| **Part A** | 100 rows (74 TM, 26 APIF by id prefix), all fields, sorted by name |
| **Part B.2** | 1 mononym: Cryzan (Brazil) |
| **Part B.3** | 19 players with initials (e.g. A. Bouzat, I. Diveev) — mostly APIF |
| **Part B.4** | 5 with name prefixes (Van den Buijs, El Akchaoui, Al Johani, De Luca, Ben Brannan) |
| **Part B.5** | 3 hyphenated (Porsan-Clémente, Aït-Nouri, Alfa-Ruprecht) |
| **Part C.1** | 30 pairs match Tier 2 rule (last token + DOB + nationality) — true cross-source duplicates |
| **Part C.2** | 49 rows: all DOB+nationality matches (includes same-person and coincidences, e.g. L. Gamba / Lionel Messi same DOB+nation) |
| **Part C.3** | APIF: 28 in sample, 14 have cross-source twin. TM: 75 in sample, 21 have cross-source twin |
| **Part D.1** | 6 of 100 have Wikipedia bios (A. Bouzat, A. Sandez, Aílson Tavares, Dwight McNeil, João Neves, Marco Asensio) |
| **Part E.1** | TM: 74/74 DOB, 72/74 market_value, 74/74 tm_url; APIF: 20/26 DOB, 0/26 market_value, 0/26 tm_url, 20/26 name_short |
| **Part F.1** | Top duplicate names in 49K: Paulinho (16), João Pedro (15), Vitinho (14), … |
| **Part F.2** | 13 of our 100 have name twins; Gabriel Silva has 3 twins |

---

## Full output (all 14 queries)

Full raw output (all 14 parts, no truncation) is in:

**[AZTECA_SAMPLE_100_RAW_OUTPUT.txt](./AZTECA_SAMPLE_100_RAW_OUTPUT.txt)**

To re-run the analysis (same seed):

```bash
cd el-capi-data && source .env && psql "$SUPABASE_DATABASE_URI" -f ../run_sample_100_analysis.sql
```

Script: [run_sample_100_analysis.sql](./run_sample_100_analysis.sql)
