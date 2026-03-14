-- AZTECA_WC_2026_SQUAD_BUILD — Step 1 only (Discover nationality values)
\echo '========== Step 1a: Unique nationalities for WC 2026 confirmed teams =========='
SELECT
    nationality_primary,
    COUNT(*) AS player_count,
    COUNT(*) FILTER (WHERE data_confidence = 'high') AS high_conf,
    COUNT(*) FILTER (WHERE data_confidence = 'medium') AS medium_conf
FROM players
WHERE nationality_primary IN (
    'Mexico', 'South Africa', 'Korea Republic', 'South Korea', 'Korea, South',
    'Canada', 'Switzerland', 'Qatar',
    'Brazil', 'Morocco', 'Haiti', 'Scotland',
    'United States', 'USA', 'Paraguay', 'Australia',
    'Germany', 'Curaçao', 'Curacao', 'Côte d''Ivoire', 'Ivory Coast', 'Cote d''Ivoire',
    'Ecuador', 'Netherlands', 'Holland', 'Japan', 'Tunisia',
    'Belgium', 'Egypt', 'Iran', 'New Zealand',
    'Spain', 'Cabo Verde', 'Cape Verde', 'Saudi Arabia', 'Uruguay',
    'France', 'Senegal', 'Norway',
    'Argentina', 'Algeria', 'Austria', 'Jordan',
    'Portugal', 'Colombia', 'Uzbekistan',
    'England', 'Croatia', 'Ghana', 'Panama'
)
GROUP BY nationality_primary
ORDER BY player_count DESC;

\echo '========== Step 1b: Variant spellings (Korea, Ivory Coast, etc.) =========='
SELECT DISTINCT nationality_primary, COUNT(*) AS cnt
FROM players
WHERE lower(nationality_primary) LIKE ANY(ARRAY[
    '%korea%', '%ivory%', '%cote%', '%curacao%', '%curaçao%',
    '%cabo%', '%cape verde%', '%united states%', '%america%',
    '%holland%', '%netherlands%', '%türkiye%', '%turkey%',
    '%scotland%', '%england%', '%wales%', '%ireland%'
])
GROUP BY nationality_primary
ORDER BY nationality_primary;

\echo '========== Step 1c: UEFA playoff candidates + other TBD =========='
SELECT
    nationality_primary,
    COUNT(*) AS player_count
FROM players
WHERE nationality_primary IN (
    'Wales', 'Italy', 'Northern Ireland', 'Bosnia and Herzegovina', 'Bosnia-Herzegovina',
    'Ukraine', 'Sweden', 'Poland', 'Albania',
    'Slovakia', 'Kosovo', 'Turkey', 'Türkiye', 'Romania',
    'Czech Republic', 'Czechia', 'Republic of Ireland', 'Ireland',
    'Denmark', 'North Macedonia',
    'DR Congo', 'Congo DR', 'Jamaica', 'Bolivia', 'Suriname', 'Iraq', 'New Caledonia'
)
GROUP BY nationality_primary
ORDER BY player_count DESC;

\echo '========== Step 1 DONE — STOP (do not run Steps 2-4) =========='
