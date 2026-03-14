# Azteca — Club Conflict Detection v3 (Word-Overlap Filter)

**Priority:** Run now
**From:** Pelé
**Date:** March 14, 2026

The v2 containment check cut false positives from 5,583 to 2,680, but abbreviation patterns survived (PSG vs "Paris Saint Germain", AC Milan vs "Associazione Calcio Milan", etc.). This version adds a word-overlap heuristic: if the two club names share significant words, they're the same club.

Run in order. **All parts this time — no checkpoint needed.**

---

### Part 1: Build the real conflict set with word-overlap filter

The logic: strip common filler words (Football, Club, FC, S.A.D., etc.), normalize accents/hyphens, then check if the two names share ANY significant word. If they share a word → same club, skip. If zero shared words → real conflict, flag.

```sql
-- 1a: Create a function to extract significant words from a club name
-- Returns an array of lowercased words, stripped of generic terms
CREATE OR REPLACE FUNCTION _extract_club_words(club_name TEXT)
RETURNS TEXT[] AS $$
DECLARE
    normalized TEXT;
    words TEXT[];
    significant TEXT[];
    w TEXT;
    -- Generic words that don't help distinguish clubs
    stopwords TEXT[] := ARRAY[
        'football', 'club', 'fc', 'fk', 'sc', 'sv', 'fußball', 'futbol',
        'calcio', 'sportiva', 'associazione', 'società', 'sportvereniging',
        'voetbalvereniging', 'koninklijke', 'vereniging', 'sport',
        'sad', 's.a.d.', 's.a.d', 'spa', 's.p.a.', 's.p.a',
        'de', 'do', 'da', 'das', 'del', 'der', 'die', 'des', 'du',
        'le', 'la', 'los', 'las', 'les', 'el', 'al', 'e',
        'the', 'and', 'of', 'for', 'und', 'für', 'von',
        'athletic', 'atletik', 'athletics',
        'real', -- careful: "Real Madrid" and "Real Sociedad" are different
        'verein', 'vereniging', 'sportverein',
        'association', 'athletic',
        'limited', 'ltd', 'plc', 'ag', 'gmbh',
        'team', 'dubai', '1893', '1907', '1899', '1904', '1905', '1909', '04', '05'
    ];
BEGIN
    -- Normalize: remove accents, hyphens, dots, lowercase
    normalized := lower(club_name);
    normalized := translate(normalized, 'áàâãäéèêëíìîïóòôõöúùûüñçřšžýčůōūāēīöü', 'aaaaaeeeeiiiioooooauuuuncrszyculoaieoeu');
    normalized := replace(normalized, '-', ' ');
    normalized := replace(normalized, '.', ' ');
    normalized := replace(normalized, '''', '');
    normalized := regexp_replace(normalized, '\s+', ' ', 'g');
    normalized := trim(normalized);

    -- Split into words
    words := string_to_array(normalized, ' ');

    -- Filter out stopwords and very short words (1-2 chars)
    significant := ARRAY[]::TEXT[];
    FOREACH w IN ARRAY words LOOP
        IF length(w) > 2 AND NOT (w = ANY(stopwords)) THEN
            significant := array_append(significant, w);
        END IF;
    END LOOP;

    RETURN significant;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 1b: Build conflicts — only where clubs share ZERO significant words
DROP TABLE IF EXISTS _club_conflicts_v3;

CREATE TEMP TABLE _club_conflicts_v3 AS
WITH conflict_candidates AS (
    SELECT
        dp.tm_id,
        dp.tm_name,
        dp.apif_id,
        dp.apif_name,
        dp.tm_club AS tm_says,
        dp.apif_club AS apif_says,
        dp.tm_market_value,
        _extract_club_words(dp.tm_club) AS tm_words,
        _extract_club_words(dp.apif_club) AS apif_words
    FROM dedup_pairs dp
    WHERE dp.tm_club IS NOT NULL
      AND dp.apif_club IS NOT NULL
      AND lower(trim(dp.tm_club)) != lower(trim(dp.apif_club))
)
SELECT
    tm_id, tm_name, apif_id, apif_name,
    tm_says, apif_says, tm_market_value,
    tm_words, apif_words
FROM conflict_candidates
WHERE NOT (tm_words && apif_words);  -- && is array overlap operator: TRUE if any element in common

-- 1c: How many REAL conflicts survived?
SELECT COUNT(*) AS real_club_conflicts FROM _club_conflicts_v3;

-- 1d: Show all high-value conflicts (> €10M) — these are the ones Capi would get wrong
SELECT
    tm_name, tm_says, apif_says, tm_market_value
FROM _club_conflicts_v3
WHERE tm_market_value > 10000000
ORDER BY tm_market_value DESC;

-- 1e: Show a sample of lower-value conflicts to verify quality
SELECT
    tm_name, tm_says, apif_says, tm_market_value
FROM _club_conflicts_v3
WHERE tm_market_value IS NOT NULL AND tm_market_value <= 10000000
ORDER BY tm_market_value DESC
LIMIT 30;

-- 1f: Sanity check — show what got FILTERED OUT that v2 would have kept
-- (These should all be same-club naming variants)
SELECT
    dp.tm_name, dp.tm_club AS tm_says, dp.apif_club AS apif_says,
    _extract_club_words(dp.tm_club) AS tm_words,
    _extract_club_words(dp.apif_club) AS apif_words,
    dp.tm_market_value
FROM dedup_pairs dp
WHERE dp.tm_club IS NOT NULL
  AND dp.apif_club IS NOT NULL
  AND lower(trim(dp.tm_club)) != lower(trim(dp.apif_club))
  AND NOT (
      lower(trim(dp.tm_club)) LIKE '%' || lower(trim(dp.apif_club)) || '%'
      OR lower(trim(dp.apif_club)) LIKE '%' || lower(trim(dp.tm_club)) || '%'
  )
  -- These WERE in v2 but NOT in v3 (filtered by word overlap)
  AND (_extract_club_words(dp.tm_club) && _extract_club_words(dp.apif_club))
  AND dp.tm_market_value > 20000000
ORDER BY dp.tm_market_value DESC
LIMIT 30;
```

---

### Part 2: Flag the real conflicts in the warehouse

```sql
-- 2a: Flag real club conflicts
UPDATE players p
SET
    needs_curation = TRUE,
    curation_reason = CASE
        WHEN p.curation_reason IS NOT NULL
        THEN p.curation_reason || '; club_conflict_tm_apif'
        ELSE 'club_conflict_tm_apif'
    END
FROM _club_conflicts_v3 cc
JOIN player_aliases pa
    ON pa.alias_type = 'transfermarkt_id' AND pa.alias_value = cc.tm_id
WHERE p.id = pa.player_id;

-- 2b: Full curation breakdown
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS total_needs_curation,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%club_conflict%') AS club_conflict,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%potential_duplicate%') AS post_load_dup,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%multi_match%') AS multi_match_ambiguous,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%missing_%') AS missing_fields,
    COUNT(*) FILTER (WHERE curation_reason = 'initial_only') AS orphan_initial_only
FROM players;
```

---

### Part 3: Cleanup

```sql
-- Drop the helper function (it was just for this analysis)
DROP FUNCTION IF EXISTS _extract_club_words(TEXT);
```

Save ALL output to **`AZTECA_CLUB_CONFLICTS_V3_RESULTS.md`**.

---

## What we expect

The word-overlap filter should eliminate the abbreviation false positives (PSG, AC Milan, AS Roma, RB Leipzig, Sporting CP, etc.) while keeping genuine transfer conflicts (Darwin Núñez Liverpool→Al-Hilal, Xavi Simons Leipzig→Tottenham, etc.).

The sanity check (1f) shows what got filtered — these should all be obvious same-club pairs. If any real conflicts got filtered, we'll see them there.
