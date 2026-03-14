-- AZTECA_CLUB_CONFLICTS_V3 — Word-overlap filter, all three parts
\echo '========== Part 1a: Create _extract_club_words =========='
CREATE OR REPLACE FUNCTION _extract_club_words(club_name TEXT)
RETURNS TEXT[] AS $$
DECLARE
    normalized TEXT;
    words TEXT[];
    significant TEXT[];
    w TEXT;
    stopwords TEXT[] := ARRAY[
        'football', 'club', 'fc', 'fk', 'sc', 'sv', 'fußball', 'futbol',
        'calcio', 'sportiva', 'associazione', 'società', 'sportvereniging',
        'voetbalvereniging', 'koninklijke', 'vereniging', 'sport',
        'sad', 's.a.d.', 's.a.d', 'spa', 's.p.a.', 's.p.a',
        'de', 'do', 'da', 'das', 'del', 'der', 'die', 'des', 'du',
        'le', 'la', 'los', 'las', 'les', 'el', 'al', 'e',
        'the', 'and', 'of', 'for', 'und', 'für', 'von',
        'athletic', 'atletik', 'athletics',
        'real',
        'verein', 'vereniging', 'sportverein',
        'association', 'athletic',
        'limited', 'ltd', 'plc', 'ag', 'gmbh',
        'team', 'dubai', '1893', '1907', '1899', '1904', '1905', '1909', '04', '05'
    ];
BEGIN
    normalized := lower(club_name);
    normalized := translate(normalized, 'áàâãäéèêëíìîïóòôõöúùûüñçřšžýčůōūāēīöü', 'aaaaaeeeeiiiioooooauuuuncrszyculoaieoeu');
    normalized := replace(normalized, '-', ' ');
    normalized := replace(normalized, '.', ' ');
    normalized := replace(normalized, '''', '');
    normalized := regexp_replace(normalized, '\s+', ' ', 'g');
    normalized := trim(normalized);
    words := string_to_array(normalized, ' ');
    significant := ARRAY[]::TEXT[];
    FOREACH w IN ARRAY words LOOP
        IF length(w) > 2 AND NOT (w = ANY(stopwords)) THEN
            significant := array_append(significant, w);
        END IF;
    END LOOP;
    RETURN significant;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

\echo '========== Part 1b: Build _club_conflicts_v3 (zero word overlap) =========='
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
WHERE NOT (tm_words && apif_words);

\echo '========== Part 1c: Real club conflicts count =========='
SELECT COUNT(*) AS real_club_conflicts FROM _club_conflicts_v3;

\echo '========== Part 1d: High-value conflicts (>10M) =========='
SELECT
    tm_name, tm_says, apif_says, tm_market_value
FROM _club_conflicts_v3
WHERE tm_market_value > 10000000
ORDER BY tm_market_value DESC;

\echo '========== Part 1e: Sample lower-value conflicts (30) =========='
SELECT
    tm_name, tm_says, apif_says, tm_market_value
FROM _club_conflicts_v3
WHERE tm_market_value IS NOT NULL AND tm_market_value <= 10000000
ORDER BY tm_market_value DESC
LIMIT 30;

\echo '========== Part 1f: Sanity — filtered out by word overlap (v2 had, v3 dropped) =========='
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
  AND (_extract_club_words(dp.tm_club) && _extract_club_words(dp.apif_club))
  AND dp.tm_market_value > 20000000
ORDER BY dp.tm_market_value DESC
LIMIT 30;

\echo '========== Part 2a: Flag real conflicts in warehouse =========='
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

\echo '========== Part 2b: Curation breakdown =========='
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS total_needs_curation,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%club_conflict%') AS club_conflict,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%potential_duplicate%') AS post_load_dup,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%multi_match%') AS multi_match_ambiguous,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%missing_%') AS missing_fields,
    COUNT(*) FILTER (WHERE curation_reason = 'initial_only') AS orphan_initial_only
FROM players;

\echo '========== Part 3: Drop helper function =========='
DROP FUNCTION IF EXISTS _extract_club_words(TEXT);

\echo '========== DONE =========='
