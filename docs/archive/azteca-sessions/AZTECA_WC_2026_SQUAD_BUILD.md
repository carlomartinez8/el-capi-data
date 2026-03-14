# Azteca — WC 2026 Squad Build Pipeline

**Priority:** HIGH — Core feature for La Copa Mundo
**From:** Pelé
**Date:** March 14, 2026

## What we're doing

Building the World Cup 2026 team/squad data from scratch using verified sources. The reference file `el-capi-data/data/reference/wc_2026_teams.json` has the 42 confirmed teams with group assignments from the December 5, 2025 draw. 6 playoff spots are TBD (March 26-31 playoffs).

This pipeline has 4 steps:
1. **Discover** what nationality values exist in our warehouse
2. **Map** nationalities to WC team codes
3. **Build projected squads** — top players per nationality by market value
4. **Populate player_tournament** — write to the warehouse

---

## Step 1: Discover nationality values in the warehouse

We need to know the exact strings in `nationality_primary` so we can map them correctly.

```sql
-- 1a: All unique nationalities for WC 2026 confirmed teams
-- These are the 42 confirmed nations — what do they look like in our data?
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

-- 1b: Check for nationalities we might be missing (variant spellings)
-- Look for anything close to WC nations that didn't match
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

-- 1c: Nationalities for UEFA playoff candidates (may qualify March 26-31)
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
```

**Paste full output.** Pelé needs to see exact nationality strings before building the mapping.

---

## Step 2: Build the squad candidates view

For each confirmed WC nation, pull the top 40 players by market value. (Official squads are 26 players, but we want a broader pool — some nations may have fewer than 26 in our DB.)

**DO NOT RUN THIS YET.** Wait for Pelé to confirm the nationality mapping from Step 1.

```sql
-- 2a: Create a nationality-to-team mapping table
-- Pelé will provide the exact mapping after reviewing Step 1 output
DROP TABLE IF EXISTS wc_2026_team_map;

CREATE TABLE wc_2026_team_map (
    nationality_value TEXT NOT NULL,  -- exact value from players.nationality_primary
    team_code TEXT NOT NULL,          -- FIFA 3-letter code
    team_name TEXT NOT NULL,          -- display name
    wc_group TEXT NOT NULL,           -- A through L
    confederation TEXT NOT NULL,      -- UEFA, CONMEBOL, etc.
    status TEXT NOT NULL DEFAULT 'confirmed',  -- confirmed / playoff_pending
    PRIMARY KEY (nationality_value)
);

-- INSERT mapping here after Pelé confirms (Step 1 output)
-- Example:
-- INSERT INTO wc_2026_team_map VALUES ('Brazil', 'BRA', 'Brazil', 'C', 'CONMEBOL', 'confirmed');
-- INSERT INTO wc_2026_team_map VALUES ('England', 'ENG', 'England', 'L', 'UEFA', 'confirmed');

-- 2b: Build projected squads — top 40 per nation by market value
DROP TABLE IF EXISTS wc_2026_projected_squads;

CREATE TABLE wc_2026_projected_squads AS
WITH ranked AS (
    SELECT
        p.id AS player_id,
        p.known_as,
        p.full_legal_name,
        p.date_of_birth,
        p.nationality_primary,
        p.data_confidence,
        pc.current_club,
        pc.position_primary,
        pc.estimated_value_eur,
        tm.team_code,
        tm.team_name,
        tm.wc_group,
        ROW_NUMBER() OVER (
            PARTITION BY tm.team_code
            ORDER BY pc.estimated_value_eur DESC NULLS LAST
        ) AS rank_in_squad
    FROM players p
    JOIN player_career pc ON p.id = pc.player_id
    JOIN wc_2026_team_map tm ON p.nationality_primary = tm.nationality_value
    WHERE tm.status = 'confirmed'
)
SELECT * FROM ranked
WHERE rank_in_squad <= 40;

-- 2c: Squad coverage report
SELECT
    team_code,
    team_name,
    wc_group,
    COUNT(*) AS squad_size,
    COUNT(*) FILTER (WHERE data_confidence = 'high') AS high_conf,
    COUNT(*) FILTER (WHERE estimated_value_eur IS NOT NULL) AS has_value,
    ROUND(AVG(estimated_value_eur) FILTER (WHERE estimated_value_eur IS NOT NULL)) AS avg_value,
    MAX(estimated_value_eur) AS max_value
FROM wc_2026_projected_squads
WHERE rank_in_squad <= 26  -- official squad size
GROUP BY team_code, team_name, wc_group
ORDER BY wc_group, team_code;

-- 2d: Teams with thin squads (fewer than 23 players)
SELECT
    team_code, team_name, COUNT(*) AS available_players
FROM wc_2026_projected_squads
WHERE rank_in_squad <= 26
GROUP BY team_code, team_name
HAVING COUNT(*) < 23
ORDER BY COUNT(*);

-- 2e: Spot check — show squad for a major team (Brazil)
SELECT
    rank_in_squad, known_as, position_primary, current_club,
    estimated_value_eur, data_confidence
FROM wc_2026_projected_squads
WHERE team_code = 'BRA' AND rank_in_squad <= 26
ORDER BY rank_in_squad;
```

---

## Step 3: Populate player_tournament

```sql
-- 3a: Insert into player_tournament for all projected squad members (top 26 per team)
INSERT INTO player_tournament (
    player_id,
    wc_team_code,
    in_squad,
    updated_at
)
SELECT
    player_id,
    team_code,
    TRUE,
    NOW()
FROM wc_2026_projected_squads
WHERE rank_in_squad <= 26
ON CONFLICT (player_id) DO UPDATE SET
    wc_team_code = EXCLUDED.wc_team_code,
    in_squad = TRUE,
    updated_at = NOW();

-- 3b: Also insert extended squad (ranks 27-40) as reserves
INSERT INTO player_tournament (
    player_id,
    wc_team_code,
    in_squad,
    updated_at
)
SELECT
    player_id,
    team_code,
    FALSE,  -- not in primary squad, but in extended pool
    NOW()
FROM wc_2026_projected_squads
WHERE rank_in_squad > 26 AND rank_in_squad <= 40
ON CONFLICT (player_id) DO UPDATE SET
    wc_team_code = EXCLUDED.wc_team_code,
    in_squad = FALSE,
    updated_at = NOW();

-- 3c: Final report
SELECT
    pt.wc_team_code,
    COUNT(*) AS total_in_tournament,
    COUNT(*) FILTER (WHERE pt.in_squad = TRUE) AS in_squad,
    COUNT(*) FILTER (WHERE pt.in_squad = FALSE) AS reserves
FROM player_tournament pt
GROUP BY pt.wc_team_code
ORDER BY pt.wc_team_code;

-- 3d: Total
SELECT
    COUNT(*) AS total_tournament_players,
    COUNT(DISTINCT wc_team_code) AS teams_represented
FROM player_tournament;
```

---

## Step 4: Report

```sql
-- 4a: Full group-by-group breakdown
SELECT
    tm.wc_group AS "Group",
    tm.team_name AS "Team",
    COUNT(pt.player_id) FILTER (WHERE pt.in_squad = TRUE) AS "Squad",
    COUNT(pt.player_id) FILTER (WHERE pt.in_squad = FALSE) AS "Reserves",
    MAX(pc.estimated_value_eur) AS "Top Player Value"
FROM wc_2026_team_map tm
LEFT JOIN player_tournament pt ON pt.wc_team_code = tm.team_code
LEFT JOIN player_career pc ON pc.player_id = pt.player_id
GROUP BY tm.wc_group, tm.team_name
ORDER BY tm.wc_group, tm.team_name;

-- 4b: Top 5 most valuable squads
SELECT
    pt.wc_team_code,
    SUM(pc.estimated_value_eur) AS total_squad_value,
    COUNT(*) AS squad_size
FROM player_tournament pt
JOIN player_career pc ON pc.player_id = pt.player_id
WHERE pt.in_squad = TRUE
GROUP BY pt.wc_team_code
ORDER BY total_squad_value DESC NULLS LAST
LIMIT 10;

-- 4c: Sample — can Capi now answer "show me the Brazil squad"?
SELECT
    p.known_as,
    pc.position_primary,
    pc.current_club,
    pc.estimated_value_eur,
    p.data_confidence,
    pt.wc_team_code,
    pt.in_squad
FROM player_tournament pt
JOIN players p ON p.id = pt.player_id
JOIN player_career pc ON pc.player_id = pt.player_id
WHERE pt.wc_team_code = 'BRA' AND pt.in_squad = TRUE
ORDER BY pc.estimated_value_eur DESC NULLS LAST;
```

Save ALL output to **`AZTECA_WC_2026_SQUAD_BUILD_RESULTS.md`**.

---

## Important notes

1. **Run ONLY Step 1 first.** Stop and paste output. Pelé needs to verify the nationality mapping before Steps 2-4.
2. The `wc_2026_team_map` table is a **permanent reference table** — it stays in the database and will be updated when playoff winners are decided (March 26-31).
3. The `wc_2026_projected_squads` table is intermediate — it can be rebuilt any time nationalities or market values change.
4. Official squads will be announced by federations closer to the tournament (May/June 2026). When that happens, we update `player_tournament.in_squad` based on the official lists. The projected squads are our best guess until then.
5. **Do not touch** existing `player_tournament` rows for the original 638 players — those may have enriched narrative data (tournament_role, narrative_arc, etc.) that we don't want to overwrite. The `ON CONFLICT DO UPDATE` preserves those fields since we only set `wc_team_code`, `in_squad`, and `updated_at`.
