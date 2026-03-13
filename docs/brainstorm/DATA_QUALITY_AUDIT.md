# El Capi — Data Quality Audit Report

**Date:** March 12, 2026
**Auditor:** Pelé (AI Agent)
**Scope:** Full pipeline (`el-capi-data`) + Admin Panel API (`la-copa-mundo`)
**Pipeline Run Audited:** 2026-03-11

---

## Executive Summary

The 9-stage data pipeline produces **677 canonical players across 42 teams**. Of those, **632 are pushed to Supabase** (47 blocked by critical conflicts, minus a few edge cases). The pipeline architecture is sound — 4-source merge with priority resolution, dedup scoring, GPT enrichment, and conflict detection all work. But several data quality issues need fixing before we can stand behind this data publicly.

**Top-line numbers:**

| Metric | Value |
|--------|-------|
| Canonical players | 677 |
| Clean (no conflicts) | 522 (77%) |
| With conflicts | 155 (23%) |
| Blocked (critical conflicts) | 47 (7%) |
| Pushed to Supabase | ~632 |
| Teams | 42 of 48 |
| Duplicate groups | 11 |
| Verification coverage | 5 of 677 (0.7%) |

---

## Finding 1: Admin Players Page Shows Only Conflicted Players

**Severity:** 🔴 HIGH — This is what Carlo saw (4 Colombia players instead of 18+)

**Root cause:** `src/app/api/admin/reconciliation/route.ts` reads from `reconciliation_report.json`, which only contains the 155 players *with conflicts*. The 522 clean players aren't in this file at all.

When the Players page requests `?filter=all`, it gets all 155 conflicted players — not all 677. Colombia has 18 players in the pipeline but only 4 have conflicts (James Rodríguez, Jefferson Lerma, Yerry Mina, Camilo), so that's all that shows up.

**Fix:** The Players page API needs to read from `players_merged.json` or `players_canonical.json` (which have all 677) instead of `reconciliation_report.json`. The reconciliation report should only be used for the Reconciliation page.

**Files to change:**
- `src/app/api/admin/players/route.ts` (create — doesn't exist yet)
- Or modify `src/app/api/admin/reconciliation/route.ts` to serve two data sources depending on context

---

## Finding 2: 11 Duplicate Player Groups

**Severity:** 🔴 HIGH — Same person appears twice under same team

**Duplicates found (name × team appearing 2+ times):**

| # | Player | Team | Root Cause |
|---|--------|------|------------|
| 1 | Endrick | BRA | Mononym, no DOB match across sources |
| 2 | Raphinha | BRA | Mononym, no DOB match |
| 3 | Savinho | BRA | Mononym, no DOB match |
| 4 | Ederson | BRA | Mononym, no DOB match |
| 5 | Wendell | BRA | Mononym, no DOB match |
| 6 | Estêvão | BRA | Mononym, no DOB match |
| 7 | Diego Gómez | PAR | Fallback key collision |
| 8 | Formose Mendy | SEN | Fallback key collision |
| 9 | John Yeboah | ECU | Fallback key collision |
| 10 | Jorge Sánchez | MEX | Fallback key collision |
| 11 | Trezeguet | EGY | Mononym, no DOB match |

**Root cause (code-level):**

1. **`pipeline/dedup/matcher.py` (lines 49–126):** The scoring system has a "generic name penalty" — single-token names or names ≤6 characters are capped at score 75 without a DOB match. This means Brazilian mononyms like "Endrick" from Source A and "Endrick" from Source B score 75 even when they share the same team.

2. **`pipeline/dedup/resolver.py` (line 243):** Review candidates (score 70–84) are explicitly NOT merged — they're added as new entries. So "Endrick" from static squads and "Endrick" from GPT enrichment both survive as separate players.

**DOB coverage gap:** 512 of 684 input players have DOB (75%). The 172 without DOB are exactly the fallback-key players (from static sources that don't include birth dates). This is why Brazilian mononyms collide — static squads don't have DOB data.

**Fix options:**
- **Quick fix:** Add a same-team-same-exact-name override in `matcher.py` that auto-merges at 90+ when team matches, regardless of name length
- **Better fix:** Run a dedup pass specifically for same-name-same-team entries in `resolver.py` before the "add as new" step
- **Manual fix:** Resolve the 11 duplicates by hand in the admin panel (if the merge tooling exists)

---

## Finding 3: Stale Transfermarkt Data

**Severity:** 🔴 HIGH — Star players show wrong clubs from 2+ years ago

**Examples found:**

| Player | Pipeline Says | Reality (2026) | Stale By |
|--------|--------------|----------------|----------|
| Lionel Messi | PSG | Inter Miami | ~3 years |
| Cristiano Ronaldo | Manchester United | Al Nassr | ~3.5 years |

**Root cause:** The Transfermarkt CSVs in `la-copa-mundo/scripts/pipeline/data/` (dated 2026-03-10 on disk, but the *content* appears to be from a much older Kaggle dataset). The GPT enrichment stage sometimes corrects these (it knows Messi is at Inter Miami), but Transfermarkt has highest source priority, so the stale club data wins in reconciliation.

**Impact:** `current_club` and `current_league` are CRITICAL conflict fields. When GPT enrichment disagrees with Transfermarkt on club, it creates a CRITICAL conflict that blocks the player from publishing.

**Fix:** Either refresh the Transfermarkt CSVs with current data, or downgrade Transfermarkt's priority for `current_club`/`current_league` fields specifically when the data is clearly stale (e.g., player no longer at that club per multiple other sources).

---

## Finding 4: Wrong Player Resolution — Vinicius (BRA)

**Severity:** 🔴 HIGH — Wrong human being in the dataset

**Details:** The canonical player "Vinicius" for BRA resolves to a player from Moreirense FC (Portuguese league), NOT Vinicius Jr at Real Madrid. This is a dedup/matching error where the wrong "Vinicius" was selected as the canonical entry.

**Fix:** Manual correction needed. The canonical entry for Vinicius (BRA) should map to Vinicius José de Oliveira Junior (Real Madrid, DOB: 2000-07-12). This likely requires fixing the source data or the dedup merge decision.

---

## Finding 5: Massive Data Completeness Gaps

**Severity:** 🟡 MEDIUM — Key fields missing for significant % of players

**From reconciliation report conflict analysis + canonical data inspection:**

| Field | Conflict Count | Estimated Gap |
|-------|---------------|---------------|
| `international_caps` | 56 conflicts | ~9.2% missing entirely |
| `position` | 54 conflicts | Conflicting across sources |
| `international_goals` | 42 conflicts | ~7.1% missing entirely |
| `jersey_number` | 23 conflicts | ~5.5% missing |
| `current_league` | 23 conflicts | Stale data, not missing |
| `date_of_birth` | — | 172 players (25%) missing DOB |

**The DOB gap is particularly damaging** because it's the root cause of the dedup failures (Finding 2). Players without DOB fall back to name-only matching keys, which are weaker.

**Fix:** Prioritize DOB enrichment. A targeted GPT enrichment pass focused solely on filling DOB for the 172 players without it would dramatically improve dedup accuracy.

---

## Finding 6: Only 42 Teams (Should Be 48)

**Severity:** 🟡 MEDIUM — 6 World Cup 2026 slots not represented

**Teams present:** 42 unique `wc_team_code` values in `players_canonical.json`.

**Context:** FIFA World Cup 2026 has 48 slots. As of March 2026, qualification is still ongoing for some confederations. Some missing teams may simply not have qualified yet or their squads haven't been announced. However, notably absent teams like Italy suggest possible data gaps rather than just qualification timing.

**Fix:** Verify which 6 slots are missing and determine if they're genuinely unqualified or if the static squad source (`pipeline/ingest/static_squads.py`) needs updating. The static squads file defines exactly which teams are included.

---

## Finding 7: "Sumeet" Not Found in Pipeline

**Severity:** 🟡 MEDIUM — Mystery data in production Supabase

**Investigation:** Searched all pipeline output files — `players_canonical.json`, `players_merged.json`, `supabase_seed/players.sql`, enriched data. "Sumeet" does not appear anywhere in the data pipeline.

**Likely explanations:**
1. Direct INSERT into Supabase (testing or manual entry)
2. A different data loading process outside the pipeline
3. A previous pipeline run that has since been superseded

**Fix:** Carlo needs to check Supabase directly: `SELECT * FROM players WHERE full_name ILIKE '%sumeet%' OR slug ILIKE '%sumeet%';` to find the source. The Supabase seed uses `ON CONFLICT (id) DO NOTHING`, so old data from previous runs would persist.

---

## Finding 8: Suspicious Entries

**Severity:** 🟡 MEDIUM

### 8a: "N" as a Player Name
A single-character name `'N'` appears in `supabase_seed/players.sql`. This is clearly corrupt data that slipped through — likely a parsing failure in one of the ingest stages.

### 8b: "Camilo" (COL) — Nationality Conflict
Player "Camilo" under Colombia has a nationality conflict: Brazil vs Colombia across sources. This suggests the wrong "Camilo" was matched — there are multiple professional footballers named Camilo, and the Brazilian one was likely pulled in by GPT enrichment while the Colombian one came from static squads.

**Fix:** Both need manual review. "N" should be deleted. "Camilo" needs source disambiguation.

---

## Finding 9: Verification Stage Is Ineffective

**Severity:** 🟡 MEDIUM — Stage 8 (Verify) barely ran

**Details:** `verification_results.json` contains only 5 players verified by GPT-4o. All 5 changes were setting `in_wc_2026_squad` from `true` to `null`. That's 0.7% coverage of the 677-player dataset.

**Impact:** The verification stage is supposed to be a quality gate — an independent GPT-4o check on the data before pushing to Supabase. At 5 players, it provides essentially no coverage.

**Fix:** Either run verification across a meaningful sample (at least 100 players, focusing on star players and players with conflicts), or accept that this stage doesn't exist in practice and remove it from the pipeline description.

---

## Finding 10: Admin API — Apply Route Field Mapping Gaps

**Severity:** 🟡 MEDIUM — Silent data loss risk

**Details:** `src/app/api/admin/reconciliation/apply/route.ts` has a `FIELD_TO_PATH` mapping that translates field names to JSON paths in the canonical player object. Two enrichment fields are NOT mapped:
- `career_trajectory`
- `major_trophies`

If a curator manually resolves a conflict for either of these fields and clicks "Apply", the resolution is silently skipped — no error, no feedback.

**Current state:** No active resolutions use these fields, so no data has been lost yet. But it's a latent bug.

**Fix:** Add mappings for `career_trajectory` → `story.career_trajectory` and `major_trophies` → `story.major_trophies` in the `FIELD_TO_PATH` constant.

---

## Finding 11: Admin API — Flagged Filter Non-Functional

**Severity:** 🟢 LOW

**Details:** The `filter=flagged` parameter on the reconciliation GET endpoint always returns empty results. This is because only CRITICAL-severity conflicts get `status: "needs_review"`, and all players with CRITICAL conflicts are blocked. Non-blocked players only have `"auto_resolved"` or `"resolved"` status.

The filter was likely intended to show players needing manual attention but the data model doesn't support that distinction correctly.

---

## Finding 12: Team-to-Nationality Map Mismatch

**Severity:** 🟢 LOW

**Details:** `pipeline/dedup/resolver.py` defines a team-to-nationality mapping with 54 teams, but `pipeline/ingest/static_squads.py` only defines 42 teams. Seven static squad teams (ALG, AUT, CPV, CUW, JOR, NOR, UZB) aren't in the resolver's nationality map, causing nationality checks to fail-open (no validation).

**Fix:** Sync the two team lists.

---

## Finding 13: Field Naming Inconsistency

**Severity:** 🟢 LOW

**Details:** The reconciliation conflicts reference a field called `nationality`, but the canonical player schema uses `nationality_primary` (under `identity`). The sync-to-Supabase script (`pipeline/sync/to_supabase.py`) maps `identity.nationality_primary` → `players.nationality_primary`. This inconsistency could cause confusion when resolving nationality conflicts via the admin panel.

---

## Priority Fix Order

Based on impact and effort:

| Priority | Finding | Effort | Impact |
|----------|---------|--------|--------|
| **P0** | #1 Admin Players page bug | Small (new API route) | Unblocks admin workflow |
| **P0** | #4 Wrong Vinicius | Manual fix | Star player wrong identity |
| **P0** | #8a "N" corrupt entry | Manual delete | Corrupt data in production |
| **P1** | #2 11 duplicate groups | Medium (dedup logic) | Data integrity |
| **P1** | #3 Stale Transfermarkt data | Large (data refresh) | 47 blocked players, wrong clubs |
| **P1** | #5 DOB gaps (172 players) | Medium (enrichment pass) | Enables better dedup |
| **P1** | #7 "Sumeet" investigation | Manual (Supabase query) | Mystery data |
| **P2** | #6 42 vs 48 teams | Medium (squad update) | Completeness |
| **P2** | #9 Verification coverage | Medium (re-run stage) | Quality assurance |
| **P2** | #10 Apply field mapping | Small (2 lines) | Prevent future bugs |
| **P3** | #8b Camilo disambiguation | Manual review | One player |
| **P3** | #11 Flagged filter | Small | UX improvement |
| **P3** | #12 Team map sync | Small | Consistency |
| **P3** | #13 Field naming | Small | Developer clarity |

---

## Supabase Production Check (Pending)

The audit VM cannot reach Supabase directly (DNS blocked). Carlo needs to run these queries to complete the production-side audit:

```sql
-- 1. Check for "Sumeet"
SELECT * FROM players WHERE full_name ILIKE '%sumeet%' OR slug ILIKE '%sumeet%';

-- 2. Total player count (should be ~632)
SELECT COUNT(*) FROM players;

-- 3. Check for "N" corrupt entry
SELECT * FROM players WHERE LENGTH(full_name) <= 1;

-- 4. Check for duplicates in production
SELECT full_name, nationality_primary, COUNT(*)
FROM players
GROUP BY full_name, nationality_primary
HAVING COUNT(*) > 1;

-- 5. Check Vinicius entries for Brazil
SELECT id, full_name, slug FROM players
WHERE nationality_primary = 'Brazilian' AND full_name ILIKE '%vinicius%';

-- 6. Team distribution
SELECT nationality_primary, COUNT(*) as player_count
FROM players
GROUP BY nationality_primary
ORDER BY player_count DESC;

-- 7. Check for stale club data
SELECT full_name, current_club FROM player_career
WHERE full_name IN ('Lionel Messi', 'Cristiano Ronaldo');
```

---

## Pipeline Architecture Reference

For context, the 9-stage pipeline:

```
Stage 1: Ingest (4 sources: Transfermarkt CSV, Static Bios, Static Squads, GPT Enrichment)
Stage 2: Dedup (score-based matching, 85+ auto-merge, 70-84 review, <70 new entry)
Stage 3: QA (field validation)
Stage 4: Export (intermediate output)
Stage 5: Enrich (GPT-4o-mini fills gaps)
Stage 6: Canonical IDs (assign stable UUIDs)
Stage 7: Reconcile (4-source merge with priority, conflict detection)
Stage 8: Verify (GPT-4o independent check — currently minimal)
Stage 9: Push to Supabase (SQL seed generation)
```

**Source priority order:** Transfermarkt CSV > Static Bios > Static Squads > GPT Enrichment

---

*End of audit. All findings based on pipeline output data from 2026-03-11 and codebase as of 2026-03-12.*
