-- AZTECA_SAMPLE_100_TASK — all parts in one session so sample_100 persists
\echo '========== Part A: setseed + create sample_100 =========='
SELECT setseed(0.42);

CREATE TEMP TABLE sample_100 AS
SELECT id, name, name_short, date_of_birth, nationality, nationality_secondary,
  position, sub_position, foot, height_cm, current_club_name, jersey_number,
  market_value_eur, photo_url, country_of_birth, city_of_birth, transfermarkt_url
FROM pipeline_players
ORDER BY random()
LIMIT 100;

\echo '========== Part A: Full 100 rows ORDER BY name =========='
SELECT * FROM sample_100 ORDER BY name;

\echo '========== Part B.1 — Name token counts =========='
SELECT
  id, name, name_short,
  array_length(string_to_array(trim(name), ' '), 1) AS name_tokens,
  array_length(string_to_array(trim(COALESCE(name_short, '')), ' '), 1) AS short_tokens,
  CASE WHEN id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS source
FROM sample_100
ORDER BY name_tokens DESC, name;

\echo '========== Part B.2 — Single-name players (mononyms) =========='
SELECT id, name, name_short, nationality, position
FROM sample_100
WHERE array_length(string_to_array(trim(name), ' '), 1) = 1;

\echo '========== Part B.3 — Players with initials (A. Diallo) =========='
SELECT id, name, name_short, nationality, date_of_birth
FROM sample_100
WHERE name ~ '^[A-Z]\. '
   OR name ~ ' [A-Z]\. '
   OR name ~ '^[A-Z]\.[A-Z]\.';

\echo '========== Part B.4 — Name prefixes (van, dos, etc.) =========='
SELECT id, name, nationality
FROM sample_100
WHERE name ~* '\y(de|di|da|do|dos|van|von|el|al|ben|bin|le|la|mc|mac|del|della|lo|las|los|san|saint|st)\y';

\echo '========== Part B.5 — Hyphenated names =========='
SELECT id, name, nationality
FROM sample_100
WHERE name LIKE '%-%';

\echo '========== Part C.1 — Duplicates: last_token + DOB + nationality =========='
WITH sample_parsed AS (
  SELECT
    s.id, s.name, s.date_of_birth, s.nationality,
    split_part(s.name, ' ', array_length(string_to_array(trim(s.name), ' '), 1)) AS last_token,
    CASE WHEN s.id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS source
  FROM sample_100 s
  WHERE s.date_of_birth IS NOT NULL
)
SELECT
  a.id AS id_a, a.name AS name_a, a.source AS source_a,
  b.id AS id_b, b.name AS name_b,
  CASE WHEN b.id LIKE 'apif_%' THEN 'APIF' ELSE 'TM' END AS source_b,
  a.date_of_birth, a.nationality
FROM sample_parsed a
JOIN pipeline_players b
  ON b.date_of_birth = a.date_of_birth
  AND b.nationality = a.nationality
  AND b.id != a.id
  AND split_part(b.name, ' ', array_length(string_to_array(trim(b.name), ' '), 1)) = a.last_token
ORDER BY a.name;

\echo '========== Part C.2 — Broader: same DOB + nationality (all matches) =========='
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

\echo '========== Part C.3 — Cross-source twin counts =========='
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

\echo '========== Part D.1 — Wikipedia bios for sample =========='
SELECT
  s.id, s.name, s.nationality, s.date_of_birth,
  b.bio_source,
  LEFT(b.bio_summary, 200) AS bio_preview,
  b.wikipedia_url
FROM sample_100 s
JOIN player_bios b ON b.player_id = s.id
ORDER BY s.name;

\echo '========== Part E.1 — Field completeness by source =========='
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

\echo '========== Part F.1 — Top 30 duplicate names in full 49K =========='
SELECT name, COUNT(*) AS occurrences,
  COUNT(DISTINCT nationality) AS distinct_nationalities,
  COUNT(DISTINCT date_of_birth) AS distinct_dobs
FROM pipeline_players
GROUP BY name
HAVING COUNT(*) > 1
ORDER BY occurrences DESC
LIMIT 30;

\echo '========== Part F.2 — Sample players who have name twins =========='
SELECT s.name, s.id, s.nationality, s.date_of_birth,
  (SELECT COUNT(*) FROM pipeline_players p WHERE p.name = s.name AND p.id != s.id) AS name_twins
FROM sample_100 s
WHERE (SELECT COUNT(*) FROM pipeline_players p WHERE p.name = s.name AND p.id != s.id) > 0
ORDER BY name_twins DESC;
