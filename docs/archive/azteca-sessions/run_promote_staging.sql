-- AZTECA_PROMOTE_STAGING — Load staging into production players, aliases, career
-- Run in single session (temp tables). Step 2 overwrites identity, preserves GPT enrichment.
\echo '========== Step 0: Add curation columns to players =========='
ALTER TABLE players
ADD COLUMN IF NOT EXISTS needs_curation BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS curation_reason TEXT,
ADD COLUMN IF NOT EXISTS curation_resolved_by TEXT,
ADD COLUMN IF NOT EXISTS curation_resolved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS wikipedia_url TEXT,
ADD COLUMN IF NOT EXISTS wikipedia_bio TEXT,
ADD COLUMN IF NOT EXISTS match_tier TEXT,
ADD COLUMN IF NOT EXISTS source_records TEXT;

CREATE INDEX IF NOT EXISTS idx_players_curation ON players(needs_curation) WHERE needs_curation = TRUE;

\echo '========== Step 1a: Existing warehouse players =========='
SELECT COUNT(*) AS existing_warehouse_players FROM players;

\echo '========== Step 1b: Alias counts =========='
SELECT alias_type, COUNT(*) AS alias_count
FROM player_aliases
GROUP BY alias_type;

\echo '========== Step 1c: Build staging–warehouse map (aliases) =========='
DROP TABLE IF EXISTS _staging_warehouse_map;

CREATE TEMP TABLE _staging_warehouse_map AS
SELECT DISTINCT
    pps.profile_id AS staging_profile_id,
    pps.tm_id,
    pps.apif_id,
    p.id AS existing_player_id,
    pa.alias_type AS matched_via
FROM profile_players_staging pps
JOIN player_aliases pa
    ON (pa.alias_type = 'transfermarkt_id' AND pa.alias_value = pps.tm_id)
    OR (pa.alias_type = 'apif_id' AND pa.alias_value = pps.apif_id)
JOIN players p ON p.id = pa.player_id;

\echo '========== Step 1c report: staging profiles matching existing =========='
SELECT COUNT(*) AS staging_profiles_matching_existing FROM _staging_warehouse_map;

\echo '========== Step 1d: New vs already in warehouse =========='
SELECT
    (SELECT COUNT(*) FROM profile_players_staging) AS total_staging,
    (SELECT COUNT(DISTINCT staging_profile_id) FROM _staging_warehouse_map) AS already_in_warehouse,
    (SELECT COUNT(*) FROM profile_players_staging) -
    (SELECT COUNT(DISTINCT staging_profile_id) FROM _staging_warehouse_map) AS new_profiles;

\echo '========== Step 1e: Fallback name+DOB matches (diagnostic) =========='
SELECT COUNT(*) AS name_dob_matches
FROM profile_players_staging pps
JOIN players p
    ON lower(pps.display_name) = lower(p.known_as)
    AND pps.date_of_birth = p.date_of_birth;

\echo '========== Step 2a: Update existing players (identity from staging) =========='
UPDATE players p
SET
    full_legal_name = pps.display_name,
    known_as = pps.display_name,
    date_of_birth = pps.date_of_birth,
    birth_city = pps.birth_city,
    birth_country = pps.birth_country,
    height_cm = pps.height_cm,
    preferred_foot = CASE lower(pps.foot)
        WHEN 'left' THEN 'Left'
        WHEN 'right' THEN 'Right'
        WHEN 'both' THEN 'Both'
        ELSE p.preferred_foot
    END,
    nationality_primary = COALESCE(pps.nationality, p.nationality_primary),
    nationality_secondary = COALESCE(pps.nationality_secondary, p.nationality_secondary),
    photo_url = COALESCE(pps.photo_url, p.photo_url),
    wikipedia_url = pps.wikipedia_url,
    wikipedia_bio = pps.wikipedia_bio,
    match_tier = pps.match_tier,
    source_records = pps.source_records,
    data_confidence = CASE pps.data_confidence
        WHEN 'VERIFIED' THEN 'high'
        WHEN 'PROJECTED' THEN 'medium'
        WHEN 'PARTIAL' THEN 'low'
        WHEN 'ORPHAN' THEN 'low'
    END,
    needs_curation = pps.needs_curation,
    curation_reason = pps.curation_reason
FROM _staging_warehouse_map m
JOIN profile_players_staging pps ON pps.profile_id = m.staging_profile_id
WHERE p.id = m.existing_player_id;

\echo '========== Step 3: Insert NEW players from staging =========='
INSERT INTO players (
    id,
    full_legal_name,
    known_as,
    date_of_birth,
    birth_city,
    birth_country,
    height_cm,
    preferred_foot,
    nationality_primary,
    nationality_secondary,
    photo_url,
    data_confidence,
    needs_curation,
    curation_reason,
    wikipedia_url,
    wikipedia_bio,
    match_tier,
    source_records,
    created_at
)
SELECT
    gen_random_uuid(),
    pps.display_name,
    pps.display_name,
    pps.date_of_birth,
    pps.birth_city,
    pps.birth_country,
    pps.height_cm,
    CASE lower(pps.foot)
        WHEN 'left' THEN 'Left'
        WHEN 'right' THEN 'Right'
        WHEN 'both' THEN 'Both'
        ELSE NULL
    END,
    COALESCE(pps.nationality, 'Unknown'),
    pps.nationality_secondary,
    pps.photo_url,
    CASE pps.data_confidence
        WHEN 'VERIFIED' THEN 'high'
        WHEN 'PROJECTED' THEN 'medium'
        WHEN 'PARTIAL' THEN 'low'
        WHEN 'ORPHAN' THEN 'low'
    END,
    pps.needs_curation,
    pps.curation_reason,
    pps.wikipedia_url,
    pps.wikipedia_bio,
    pps.match_tier,
    pps.source_records,
    NOW()
FROM profile_players_staging pps
WHERE pps.profile_id NOT IN (
    SELECT staging_profile_id FROM _staging_warehouse_map
);

\echo '========== Step 4a: Build full player map =========='
DROP TABLE IF EXISTS _full_player_map;

CREATE TEMP TABLE _full_player_map AS
SELECT m.staging_profile_id, m.existing_player_id AS player_uuid
FROM _staging_warehouse_map m
UNION
SELECT pps.profile_id, p.id
FROM profile_players_staging pps
JOIN players p ON p.source_records = pps.source_records
WHERE pps.profile_id NOT IN (SELECT staging_profile_id FROM _staging_warehouse_map);

\echo '========== Step 4b–4d: Insert aliases =========='
INSERT INTO player_aliases (player_id, alias_type, alias_value)
SELECT m.player_uuid, 'transfermarkt_id', pps.tm_id
FROM _full_player_map m
JOIN profile_players_staging pps ON pps.profile_id = m.staging_profile_id
WHERE pps.tm_id IS NOT NULL
ON CONFLICT (alias_type, alias_value) DO NOTHING;

INSERT INTO player_aliases (player_id, alias_type, alias_value)
SELECT m.player_uuid, 'apif_id', pps.apif_id
FROM _full_player_map m
JOIN profile_players_staging pps ON pps.profile_id = m.staging_profile_id
WHERE pps.apif_id IS NOT NULL
ON CONFLICT (alias_type, alias_value) DO NOTHING;

INSERT INTO player_aliases (player_id, alias_type, alias_value)
SELECT m.player_uuid, 'transfermarkt_url', pps.tm_url
FROM _full_player_map m
JOIN profile_players_staging pps ON pps.profile_id = m.staging_profile_id
WHERE pps.tm_url IS NOT NULL
ON CONFLICT (alias_type, alias_value) DO NOTHING;

\echo '========== Step 4e: Alias counts after load =========='
SELECT alias_type, COUNT(*) AS count
FROM player_aliases
GROUP BY alias_type
ORDER BY count DESC;

\echo '========== Step 5: Upsert player_career =========='
INSERT INTO player_career (
    player_id,
    current_club,
    position_primary,
    position_secondary,
    estimated_value_eur,
    updated_at,
    refresh_source
)
SELECT
    m.player_uuid,
    pps.current_club,
    CASE
        WHEN pps.position ILIKE '%goal%' THEN 'Goalkeeper'
        WHEN pps.position ILIKE '%defend%' OR pps.position ILIKE '%back%' THEN 'Defender'
        WHEN pps.position ILIKE '%midfield%' THEN 'Midfielder'
        WHEN pps.position ILIKE '%attack%' OR pps.position ILIKE '%forward%' OR pps.position ILIKE '%wing%' THEN 'Forward'
        ELSE pps.position
    END,
    pps.sub_position,
    pps.market_value_eur,
    NOW(),
    'dedup_pipeline_v1'
FROM _full_player_map m
JOIN profile_players_staging pps ON pps.profile_id = m.staging_profile_id
ON CONFLICT (player_id) DO UPDATE SET
    current_club = COALESCE(EXCLUDED.current_club, player_career.current_club),
    position_primary = COALESCE(EXCLUDED.position_primary, player_career.position_primary),
    position_secondary = COALESCE(EXCLUDED.position_secondary, player_career.position_secondary),
    estimated_value_eur = COALESCE(EXCLUDED.estimated_value_eur, player_career.estimated_value_eur),
    updated_at = NOW(),
    refresh_source = 'dedup_pipeline_v1';

\echo '========== Step 6a: Total warehouse players =========='
SELECT COUNT(*) AS total_warehouse_players FROM players;

\echo '========== Step 6b: Confidence breakdown =========='
SELECT
    data_confidence,
    COUNT(*) AS count,
    ROUND(COUNT(*)::numeric / (SELECT COUNT(*) FROM players) * 100, 1) AS pct
FROM players
GROUP BY data_confidence
ORDER BY
    CASE data_confidence WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END;

\echo '========== Step 6c: Curation queue =========='
SELECT
    COUNT(*) FILTER (WHERE needs_curation = TRUE) AS needs_curation,
    COUNT(*) FILTER (WHERE needs_curation = FALSE OR needs_curation IS NULL) AS clean,
    ROUND(COUNT(*) FILTER (WHERE needs_curation = TRUE)::numeric / COUNT(*) * 100, 1) AS curation_pct
FROM players;

\echo '========== Step 6d: Alias coverage =========='
SELECT alias_type, COUNT(*) FROM player_aliases GROUP BY alias_type;

\echo '========== Step 6e: Career coverage =========='
SELECT
    COUNT(*) AS total_career_records,
    COUNT(*) FILTER (WHERE current_club IS NOT NULL) AS has_club,
    COUNT(*) FILTER (WHERE position_primary IS NOT NULL) AS has_position,
    COUNT(*) FILTER (WHERE estimated_value_eur IS NOT NULL) AS has_market_value
FROM player_career;

\echo '========== Step 6f: Wikipedia coverage =========='
SELECT
    COUNT(*) FILTER (WHERE wikipedia_url IS NOT NULL) AS has_wikipedia,
    COUNT(*) AS total
FROM players;

\echo '========== Step 6g: Sample high-confidence (25) =========='
SELECT
    p.id, p.known_as, p.data_confidence, p.nationality_primary,
    pc.position_primary, pc.current_club, pc.estimated_value_eur
FROM players p
LEFT JOIN player_career pc ON p.id = pc.player_id
WHERE p.data_confidence = 'high'
ORDER BY pc.estimated_value_eur DESC NULLS LAST
LIMIT 25;

\echo '========== Step 6h: Sample curation queue (25) =========='
SELECT
    p.known_as, p.data_confidence, p.needs_curation, p.curation_reason,
    p.source_records
FROM players p
WHERE p.needs_curation = TRUE
ORDER BY p.known_as
LIMIT 25;

\echo '========== Step 6i: Enriched players (stories intact) =========='
SELECT
    COUNT(*) AS enriched_players_with_stories,
    COUNT(*) FILTER (WHERE origin_story_en IS NOT NULL) AS has_origin_story,
    COUNT(*) FILTER (WHERE career_summary_en IS NOT NULL) AS has_career_summary
FROM players
WHERE enriched_at IS NOT NULL;

\echo '========== Step 6j: Table sizes =========='
SELECT
    pg_size_pretty(pg_total_relation_size('players')) AS players_size,
    pg_size_pretty(pg_total_relation_size('player_aliases')) AS aliases_size,
    pg_size_pretty(pg_total_relation_size('player_career')) AS career_size;

\echo '========== Step 6k: KILL SWITCH — duplicate aliases (MUST be 0 rows) =========='
SELECT 'DUPLICATE alias' AS issue, alias_type, alias_value, COUNT(*)
FROM player_aliases
GROUP BY alias_type, alias_value
HAVING COUNT(*) > 1
LIMIT 20;

\echo '========== DONE =========='
