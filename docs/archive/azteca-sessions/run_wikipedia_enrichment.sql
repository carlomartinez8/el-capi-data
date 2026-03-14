-- AZTECA_WIKIPEDIA_ENRICHMENT — Add wikipedia_url and wikipedia_bio to staging
\echo '========== Step 1: Add Wikipedia columns =========='
ALTER TABLE profile_players_staging
ADD COLUMN IF NOT EXISTS wikipedia_url TEXT,
ADD COLUMN IF NOT EXISTS wikipedia_bio TEXT;

\echo '========== Step 2a: Total bios =========='
SELECT COUNT(*) AS total_bios FROM player_bios;

\echo '========== Step 2b: Bios by source (TM vs APIF) =========='
SELECT
    CASE WHEN player_id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS source,
    COUNT(*) AS bio_count
FROM player_bios
GROUP BY 1;

\echo '========== Step 2c: Bios matching staging profiles =========='
SELECT COUNT(*) AS bios_matching_staging
FROM player_bios pb
WHERE pb.player_id IN (SELECT tm_id FROM profile_players_staging WHERE tm_id IS NOT NULL)
   OR pb.player_id IN (SELECT apif_id FROM profile_players_staging WHERE apif_id IS NOT NULL);

\echo '========== Step 2d: Sample bios =========='
SELECT player_id, wikipedia_url, LEFT(bio_summary, 200) AS bio_preview
FROM player_bios
LIMIT 10;

\echo '========== Step 3a: Enrich by tm_id =========='
UPDATE profile_players_staging pps
SET
    wikipedia_url = pb.wikipedia_url,
    wikipedia_bio = pb.bio_summary,
    updated_at = NOW()
FROM player_bios pb
WHERE pps.tm_id = pb.player_id
  AND pps.tm_id IS NOT NULL;

\echo '========== Step 3b: Enrich by apif_id (where not already set) =========='
UPDATE profile_players_staging pps
SET
    wikipedia_url = COALESCE(pps.wikipedia_url, pb.wikipedia_url),
    wikipedia_bio = COALESCE(pps.wikipedia_bio, pb.bio_summary),
    updated_at = NOW()
FROM player_bios pb
WHERE pps.apif_id = pb.player_id
  AND pps.apif_id IS NOT NULL
  AND pps.wikipedia_bio IS NULL;

\echo '========== Step 4a: Profiles with Wikipedia =========='
SELECT COUNT(*) AS profiles_with_wikipedia
FROM profile_players_staging
WHERE wikipedia_bio IS NOT NULL;

\echo '========== Step 4b: Enrichment by confidence =========='
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

\echo '========== Step 4c: Sample enriched profiles =========='
SELECT profile_id, tm_id, apif_id, display_name, data_confidence,
       wikipedia_url, LEFT(wikipedia_bio, 150) AS bio_preview
FROM profile_players_staging
WHERE wikipedia_bio IS NOT NULL
ORDER BY display_name
LIMIT 25;

\echo '========== Step 4d: Orphaned bios (no matching profile) =========='
SELECT COUNT(*) AS orphaned_bios
FROM player_bios pb
WHERE pb.player_id NOT IN (SELECT tm_id FROM profile_players_staging WHERE tm_id IS NOT NULL)
  AND pb.player_id NOT IN (SELECT apif_id FROM profile_players_staging WHERE apif_id IS NOT NULL);

\echo '========== Step 4e: Staging table size =========='
SELECT pg_size_pretty(pg_total_relation_size('profile_players_staging')) AS staging_table_size;

\echo '========== DONE =========='
