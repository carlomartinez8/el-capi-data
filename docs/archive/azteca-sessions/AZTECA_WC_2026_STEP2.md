# Azteca — WC 2026 Squad Build: Steps 2–4

**Priority:** Run now
**From:** Pelé
**Date:** March 14, 2026
**Depends on:** Step 1 output (nationality mapping confirmed)

---

## Step 2a: Create and populate the team mapping table

```sql
-- Create the permanent reference table
DROP TABLE IF EXISTS wc_2026_team_map;

CREATE TABLE wc_2026_team_map (
    nationality_value TEXT NOT NULL,
    team_code TEXT NOT NULL,
    team_name TEXT NOT NULL,
    wc_group TEXT NOT NULL,
    confederation TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed',
    PRIMARY KEY (nationality_value)
);

-- ═══════════════════════════════════════
-- 42 CONFIRMED TEAMS (all nationality variants)
-- ═══════════════════════════════════════

-- Group A: Mexico, South Africa, South Korea, TBD UEFA-D
INSERT INTO wc_2026_team_map VALUES ('Mexico', 'MEX', 'Mexico', 'A', 'CONCACAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('South Africa', 'RSA', 'South Africa', 'A', 'CAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Korea Republic', 'KOR', 'South Korea', 'A', 'AFC', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Korea, South', 'KOR', 'South Korea', 'A', 'AFC', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('South Korea', 'KOR', 'South Korea', 'A', 'AFC', 'confirmed');

-- Group B: Canada, Switzerland, Qatar, TBD UEFA-A
INSERT INTO wc_2026_team_map VALUES ('Canada', 'CAN', 'Canada', 'B', 'CONCACAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Switzerland', 'SUI', 'Switzerland', 'B', 'UEFA', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Qatar', 'QAT', 'Qatar', 'B', 'AFC', 'confirmed');

-- Group C: Brazil, Morocco, Haiti, Scotland
INSERT INTO wc_2026_team_map VALUES ('Brazil', 'BRA', 'Brazil', 'C', 'CONMEBOL', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Morocco', 'MAR', 'Morocco', 'C', 'CAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Haiti', 'HAI', 'Haiti', 'C', 'CONCACAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Scotland', 'SCO', 'Scotland', 'C', 'UEFA', 'confirmed');

-- Group D: United States, Paraguay, Australia, TBD UEFA-C
INSERT INTO wc_2026_team_map VALUES ('USA', 'USA', 'United States', 'D', 'CONCACAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('United States', 'USA', 'United States', 'D', 'CONCACAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Paraguay', 'PAR', 'Paraguay', 'D', 'CONMEBOL', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Australia', 'AUS', 'Australia', 'D', 'AFC', 'confirmed');

-- Group E: Germany, Curaçao, Côte d'Ivoire, Ecuador
INSERT INTO wc_2026_team_map VALUES ('Germany', 'GER', 'Germany', 'E', 'UEFA', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Curacao', 'CUW', 'Curaçao', 'E', 'CONCACAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Curaçao', 'CUW', 'Curaçao', 'E', 'CONCACAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Cote d''Ivoire', 'CIV', 'Côte d''Ivoire', 'E', 'CAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Côte d''Ivoire', 'CIV', 'Côte d''Ivoire', 'E', 'CAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Ivory Coast', 'CIV', 'Côte d''Ivoire', 'E', 'CAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Ecuador', 'ECU', 'Ecuador', 'E', 'CONMEBOL', 'confirmed');

-- Group F: Netherlands, Japan, Tunisia, TBD UEFA-B
INSERT INTO wc_2026_team_map VALUES ('Netherlands', 'NED', 'Netherlands', 'F', 'UEFA', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Japan', 'JPN', 'Japan', 'F', 'AFC', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Tunisia', 'TUN', 'Tunisia', 'F', 'CAF', 'confirmed');

-- Group G: Belgium, Egypt, Iran, New Zealand
INSERT INTO wc_2026_team_map VALUES ('Belgium', 'BEL', 'Belgium', 'G', 'UEFA', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Egypt', 'EGY', 'Egypt', 'G', 'CAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Iran', 'IRN', 'Iran', 'G', 'AFC', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('New Zealand', 'NZL', 'New Zealand', 'G', 'OFC', 'confirmed');

-- Group H: Spain, Cabo Verde, Saudi Arabia, Uruguay
INSERT INTO wc_2026_team_map VALUES ('Spain', 'ESP', 'Spain', 'H', 'UEFA', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Cape Verde', 'CPV', 'Cabo Verde', 'H', 'CAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Cape Verde Islands', 'CPV', 'Cabo Verde', 'H', 'CAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Saudi Arabia', 'KSA', 'Saudi Arabia', 'H', 'AFC', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Uruguay', 'URU', 'Uruguay', 'H', 'CONMEBOL', 'confirmed');

-- Group I: France, Senegal, TBD IC-2, Norway
INSERT INTO wc_2026_team_map VALUES ('France', 'FRA', 'France', 'I', 'UEFA', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Senegal', 'SEN', 'Senegal', 'I', 'CAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Norway', 'NOR', 'Norway', 'I', 'UEFA', 'confirmed');

-- Group J: Argentina, Algeria, Austria, Jordan
INSERT INTO wc_2026_team_map VALUES ('Argentina', 'ARG', 'Argentina', 'J', 'CONMEBOL', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Algeria', 'ALG', 'Algeria', 'J', 'CAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Austria', 'AUT', 'Austria', 'J', 'UEFA', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Jordan', 'JOR', 'Jordan', 'J', 'AFC', 'confirmed');

-- Group K: Portugal, Colombia, TBD IC-1, Uzbekistan
INSERT INTO wc_2026_team_map VALUES ('Portugal', 'POR', 'Portugal', 'K', 'UEFA', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Colombia', 'COL', 'Colombia', 'K', 'CONMEBOL', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Uzbekistan', 'UZB', 'Uzbekistan', 'K', 'AFC', 'confirmed');

-- Group L: England, Croatia, Ghana, Panama
INSERT INTO wc_2026_team_map VALUES ('England', 'ENG', 'England', 'L', 'UEFA', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Croatia', 'CRO', 'Croatia', 'L', 'UEFA', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Ghana', 'GHA', 'Ghana', 'L', 'CAF', 'confirmed');
INSERT INTO wc_2026_team_map VALUES ('Panama', 'PAN', 'Panama', 'L', 'CONCACAF', 'confirmed');

-- ═══════════════════════════════════════
-- UEFA PLAYOFF CANDIDATES (status = 'playoff_pending')
-- Add all nationality variants so they're ready when winners are decided
-- The group and team_code will be updated after March 31
-- ═══════════════════════════════════════

-- Path A → Group B: Wales / Bosnia / Italy / Northern Ireland
INSERT INTO wc_2026_team_map VALUES ('Wales', 'WAL', 'Wales', 'B', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Bosnia-Herzegovina', 'BIH', 'Bosnia and Herzegovina', 'B', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Bosnia and Herzegovina', 'BIH', 'Bosnia and Herzegovina', 'B', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Italy', 'ITA', 'Italy', 'B', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Northern Ireland', 'NIR', 'Northern Ireland', 'B', 'UEFA', 'playoff_pending');

-- Path B → Group F: Ukraine / Sweden / Poland / Albania
INSERT INTO wc_2026_team_map VALUES ('Ukraine', 'UKR', 'Ukraine', 'F', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Sweden', 'SWE', 'Sweden', 'F', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Poland', 'POL', 'Poland', 'F', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Albania', 'ALB', 'Albania', 'F', 'UEFA', 'playoff_pending');

-- Path C → Group D: Slovakia / Kosovo / Turkey / Romania
INSERT INTO wc_2026_team_map VALUES ('Slovakia', 'SVK', 'Slovakia', 'D', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Kosovo', 'KOS', 'Kosovo', 'D', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Turkey', 'TUR', 'Turkey', 'D', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Türkiye', 'TUR', 'Turkey', 'D', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Romania', 'ROU', 'Romania', 'D', 'UEFA', 'playoff_pending');

-- Path D → Group A: Czech Republic / Ireland / Denmark / North Macedonia
INSERT INTO wc_2026_team_map VALUES ('Czech Republic', 'CZE', 'Czech Republic', 'A', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Czechia', 'CZE', 'Czech Republic', 'A', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Ireland', 'IRL', 'Republic of Ireland', 'A', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Republic of Ireland', 'IRL', 'Republic of Ireland', 'A', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Denmark', 'DEN', 'Denmark', 'A', 'UEFA', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('North Macedonia', 'MKD', 'North Macedonia', 'A', 'UEFA', 'playoff_pending');

-- ═══════════════════════════════════════
-- INTERCONTINENTAL PLAYOFF CANDIDATES
-- ═══════════════════════════════════════

-- IC Path 1 → Group K: DR Congo / Jamaica / New Caledonia
INSERT INTO wc_2026_team_map VALUES ('DR Congo', 'COD', 'DR Congo', 'K', 'CAF', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Congo DR', 'COD', 'DR Congo', 'K', 'CAF', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Jamaica', 'JAM', 'Jamaica', 'K', 'CONCACAF', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('New Caledonia', 'NCL', 'New Caledonia', 'K', 'OFC', 'playoff_pending');

-- IC Path 2 → Group I: Bolivia / Suriname / Iraq
INSERT INTO wc_2026_team_map VALUES ('Bolivia', 'BOL', 'Bolivia', 'I', 'CONMEBOL', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Suriname', 'SUR', 'Suriname', 'I', 'CONCACAF', 'playoff_pending');
INSERT INTO wc_2026_team_map VALUES ('Iraq', 'IRQ', 'Iraq', 'I', 'AFC', 'playoff_pending');

-- Verify
SELECT status, COUNT(*) AS nationality_variants, COUNT(DISTINCT team_code) AS unique_teams
FROM wc_2026_team_map
GROUP BY status;
```

---

## Step 2b: Build projected squads

```sql
-- Build projected squads — top 40 per nation by market value
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
        tm.status AS team_status,
        ROW_NUMBER() OVER (
            PARTITION BY tm.team_code
            ORDER BY pc.estimated_value_eur DESC NULLS LAST, p.data_confidence ASC
        ) AS rank_in_squad
    FROM players p
    JOIN player_career pc ON p.id = pc.player_id
    JOIN wc_2026_team_map tm ON p.nationality_primary = tm.nationality_value
)
SELECT * FROM ranked
WHERE rank_in_squad <= 40;

-- 2c: Squad coverage report (confirmed teams only, top 26)
SELECT
    team_code,
    team_name,
    wc_group,
    COUNT(*) AS squad_size,
    COUNT(*) FILTER (WHERE data_confidence = 'high') AS high_conf,
    COUNT(*) FILTER (WHERE estimated_value_eur IS NOT NULL) AS has_value,
    COALESCE(ROUND(AVG(estimated_value_eur) FILTER (WHERE estimated_value_eur IS NOT NULL)), 0) AS avg_value,
    MAX(estimated_value_eur) AS max_value
FROM wc_2026_projected_squads
WHERE rank_in_squad <= 26
  AND team_status = 'confirmed'
GROUP BY team_code, team_name, wc_group
ORDER BY wc_group, team_code;

-- 2d: Teams with thin squads (fewer than 23 players in top 26 window)
SELECT
    team_code, team_name, COUNT(*) AS available_players
FROM wc_2026_projected_squads
WHERE rank_in_squad <= 26 AND team_status = 'confirmed'
GROUP BY team_code, team_name
HAVING COUNT(*) < 23
ORDER BY COUNT(*);

-- 2e: Spot check — Brazil squad
SELECT
    rank_in_squad, known_as, position_primary, current_club,
    estimated_value_eur, data_confidence
FROM wc_2026_projected_squads
WHERE team_code = 'BRA' AND rank_in_squad <= 26
ORDER BY rank_in_squad;

-- 2f: Spot check — USA squad
SELECT
    rank_in_squad, known_as, position_primary, current_club,
    estimated_value_eur, data_confidence
FROM wc_2026_projected_squads
WHERE team_code = 'USA' AND rank_in_squad <= 26
ORDER BY rank_in_squad;

-- 2g: Spot check — small team (Haiti)
SELECT
    rank_in_squad, known_as, position_primary, current_club,
    estimated_value_eur, data_confidence
FROM wc_2026_projected_squads
WHERE team_code = 'HAI' AND rank_in_squad <= 26
ORDER BY rank_in_squad;
```

---

## Step 3: Populate player_tournament

```sql
-- 3a: Insert CONFIRMED team squads (top 26) into player_tournament
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
  AND team_status = 'confirmed'
ON CONFLICT (player_id) DO UPDATE SET
    wc_team_code = EXCLUDED.wc_team_code,
    in_squad = TRUE,
    updated_at = NOW();

-- 3b: Insert reserves (ranks 27-40, confirmed teams only)
INSERT INTO player_tournament (
    player_id,
    wc_team_code,
    in_squad,
    updated_at
)
SELECT
    player_id,
    team_code,
    FALSE,
    NOW()
FROM wc_2026_projected_squads
WHERE rank_in_squad > 26 AND rank_in_squad <= 40
  AND team_status = 'confirmed'
ON CONFLICT (player_id) DO UPDATE SET
    wc_team_code = EXCLUDED.wc_team_code,
    in_squad = FALSE,
    updated_at = NOW();

-- 3c: Report by team
SELECT
    pt.wc_team_code,
    COUNT(*) AS total_in_tournament,
    COUNT(*) FILTER (WHERE pt.in_squad = TRUE) AS in_squad,
    COUNT(*) FILTER (WHERE pt.in_squad = FALSE) AS reserves
FROM player_tournament pt
GROUP BY pt.wc_team_code
ORDER BY pt.wc_team_code;

-- 3d: Totals
SELECT
    COUNT(*) AS total_tournament_players,
    COUNT(DISTINCT wc_team_code) AS teams_represented,
    COUNT(*) FILTER (WHERE in_squad = TRUE) AS in_primary_squad,
    COUNT(*) FILTER (WHERE in_squad = FALSE) AS reserves
FROM player_tournament;
```

---

## Step 4: Report

```sql
-- 4a: Full group-by-group breakdown (confirmed teams only)
SELECT
    tm.wc_group AS "Group",
    tm.team_name AS "Team",
    COUNT(pt.player_id) FILTER (WHERE pt.in_squad = TRUE) AS "Squad",
    COUNT(pt.player_id) FILTER (WHERE pt.in_squad = FALSE) AS "Reserves",
    MAX(pc.estimated_value_eur) AS "Top Value"
FROM wc_2026_team_map tm
LEFT JOIN player_tournament pt ON pt.wc_team_code = tm.team_code
LEFT JOIN player_career pc ON pc.player_id = pt.player_id
WHERE tm.status = 'confirmed'
GROUP BY tm.wc_group, tm.team_name, tm.team_code
ORDER BY tm.wc_group, tm.team_name;

-- 4b: Top 10 most valuable squads
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

-- 4c: Capi test — "show me the Brazil squad"
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

-- 4d: Capi test — "who is in Group L?"
SELECT
    tm.wc_group,
    tm.team_name,
    p.known_as,
    pc.position_primary,
    pc.current_club
FROM wc_2026_team_map tm
JOIN player_tournament pt ON pt.wc_team_code = tm.team_code
JOIN players p ON p.id = pt.player_id
JOIN player_career pc ON pc.player_id = pt.player_id
WHERE tm.wc_group = 'L'
  AND pt.in_squad = TRUE
  AND tm.status = 'confirmed'
ORDER BY tm.team_name, pc.estimated_value_eur DESC NULLS LAST;

-- 4e: Position balance check — do squads have GK, DEF, MID, FWD coverage?
SELECT
    wc_team_code,
    COUNT(*) FILTER (WHERE position_primary = 'Goalkeeper') AS gk,
    COUNT(*) FILTER (WHERE position_primary = 'Defender') AS def,
    COUNT(*) FILTER (WHERE position_primary = 'Midfielder') AS mid,
    COUNT(*) FILTER (WHERE position_primary = 'Forward') AS fwd,
    COUNT(*) FILTER (WHERE position_primary NOT IN ('Goalkeeper','Defender','Midfielder','Forward')) AS other
FROM wc_2026_projected_squads
WHERE rank_in_squad <= 26 AND team_status = 'confirmed'
GROUP BY wc_team_code
ORDER BY wc_team_code;
```

Save ALL output to **`AZTECA_WC_2026_SQUAD_BUILD_RESULTS.md`** (append to existing file, or create new section).

---

## Notes

1. Only CONFIRMED teams get written to `player_tournament`. Playoff teams are in the mapping table but won't get squads until their status changes to 'confirmed' after March 31.
2. The `ON CONFLICT DO UPDATE` on player_tournament preserves any existing narrative fields (tournament_role, narrative_arc, etc.) from the original 638 enriched players — we only overwrite team code, in_squad, and timestamp.
3. Position balance (4e) may show some teams with "other" positions — those are un-normalized legacy values like "MID" or "FWD" from the old pipeline. Display-layer issue, not blocking.
4. After playoffs resolve (March 31), update the winning team's status to 'confirmed' and re-run Steps 2b-4 to add their squads.
