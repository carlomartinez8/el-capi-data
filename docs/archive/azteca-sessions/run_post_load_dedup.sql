-- AZTECA_POST_LOAD_DEDUP — Step 7: Detect legacy vs new duplicates, flag both
\echo '========== 7a: Create _unmatched_legacy (players without source_records) =========='
DROP TABLE IF EXISTS _unmatched_legacy;

CREATE TEMP TABLE _unmatched_legacy AS
SELECT p.id, p.known_as, p.date_of_birth, p.nationality_primary
FROM players p
WHERE p.source_records IS NULL;

\echo '========== 7b: Unmatched legacy count =========='
SELECT COUNT(*) AS unmatched_legacy_players FROM _unmatched_legacy;

\echo '========== 7c: Find duplicate pairs (legacy + new, same name + DOB) =========='
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

\echo '========== 7d: Duplicate pairs count =========='
SELECT COUNT(*) AS duplicate_pairs_found FROM _post_load_duplicates;

\echo '========== 7e: All duplicate pairs =========='
SELECT * FROM _post_load_duplicates ORDER BY legacy_name;

\echo '========== 7f: Flag BOTH sides for curation =========='
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

\echo '========== 7g: Report after flagging =========='
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS total_needs_curation,
    COUNT(*) FILTER (WHERE curation_reason LIKE '%potential_duplicate_post_load%') AS flagged_post_load_dup
FROM players;

\echo '========== 7h: Spot check — Pedri / Rodri =========='
SELECT p.id, p.known_as, p.data_confidence, p.needs_curation, p.curation_reason, p.source_records
FROM players p
WHERE lower(p.known_as) IN ('pedri', 'rodri')
ORDER BY p.known_as, p.source_records NULLS FIRST;

\echo '========== DONE =========='
