# Azteca — Squad Data Cleanup

**Priority:** Run now — last cleanup before pipeline is complete
**From:** Pelé
**Date:** March 14, 2026

Three issues to fix after the WC 2026 squad build.

---

## Issue 1: Duplicate players in squads

The post-load duplicates (Pedri, Rodrygo, Raphinha, Savinho, Alisson, Casemiro, Ederson, Endrick, Marquinhos, etc.) each have 2 records in `players`. The squad builder ranked both copies independently, so some squads have the same human twice. We need to remove duplicate entries from `player_tournament`.

```sql
-- 1a: Find duplicate humans in player_tournament
-- Same known_as + same wc_team_code = duplicate
DROP TABLE IF EXISTS _squad_duplicates;

CREATE TEMP TABLE _squad_duplicates AS
WITH dupes AS (
    SELECT
        p.known_as,
        pt.wc_team_code,
        p.id AS player_id,
        pc.estimated_value_eur,
        p.source_records,
        p.data_confidence,
        ROW_NUMBER() OVER (
            PARTITION BY lower(p.known_as), pt.wc_team_code
            ORDER BY
                -- Keep the record with source_records (from staging), drop legacy
                CASE WHEN p.source_records IS NOT NULL THEN 0 ELSE 1 END,
                pc.estimated_value_eur DESC NULLS LAST
        ) AS keep_rank
    FROM player_tournament pt
    JOIN players p ON p.id = pt.player_id
    JOIN player_career pc ON pc.player_id = pt.player_id
)
SELECT * FROM dupes WHERE keep_rank > 1;

-- 1b: How many duplicates?
SELECT COUNT(*) AS duplicate_tournament_entries FROM _squad_duplicates;

-- 1c: Show them
SELECT known_as, wc_team_code, estimated_value_eur, source_records, data_confidence
FROM _squad_duplicates
ORDER BY wc_team_code, known_as;

-- 1d: Remove duplicate entries from player_tournament
DELETE FROM player_tournament
WHERE player_id IN (SELECT player_id FROM _squad_duplicates);

-- 1e: Verify — no duplicate names per team
SELECT p.known_as, pt.wc_team_code, COUNT(*) AS appearances
FROM player_tournament pt
JOIN players p ON p.id = pt.player_id
GROUP BY p.known_as, pt.wc_team_code
HAVING COUNT(*) > 1
ORDER BY appearances DESC;
-- Should return 0 rows
```

---

## Issue 2: Position normalization

Legacy records use abbreviated positions (MID, FWD, DEF, GK) while staging records use full names (Midfielder, Forward, Defender, Goalkeeper). This affects squad composition reports and the app display.

```sql
-- 2a: How many un-normalized positions exist?
SELECT position_primary, COUNT(*) AS cnt
FROM player_career
WHERE position_primary IN ('MID', 'FWD', 'DEF', 'GK', 'ATT')
GROUP BY position_primary
ORDER BY cnt DESC;

-- 2b: Normalize them
UPDATE player_career
SET position_primary = CASE position_primary
    WHEN 'GK' THEN 'Goalkeeper'
    WHEN 'DEF' THEN 'Defender'
    WHEN 'MID' THEN 'Midfielder'
    WHEN 'FWD' THEN 'Forward'
    WHEN 'ATT' THEN 'Forward'
    ELSE position_primary
END
WHERE position_primary IN ('GK', 'DEF', 'MID', 'FWD', 'ATT');

-- 2c: Verify — only standard position names remain
SELECT position_primary, COUNT(*) AS cnt
FROM player_career
GROUP BY position_primary
ORDER BY cnt DESC;
```

---

## Issue 3: Rebuild projected squads (after dedup + position fix)

The `wc_2026_projected_squads` table needs to be rebuilt now that duplicates are cleaned and positions are normalized. Then re-check position balance.

```sql
-- 3a: Rebuild projected squads
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
    -- Exclude known duplicate legacy records (no source_records = legacy)
    WHERE NOT (
        p.source_records IS NULL
        AND EXISTS (
            SELECT 1 FROM players p2
            WHERE lower(p2.known_as) = lower(p.known_as)
              AND p2.date_of_birth = p.date_of_birth
              AND p2.id != p.id
              AND p2.source_records IS NOT NULL
        )
    )
)
SELECT * FROM ranked
WHERE rank_in_squad <= 40;

-- 3b: Re-check position balance (confirmed teams, top 26)
SELECT
    team_code,
    COUNT(*) FILTER (WHERE position_primary = 'Goalkeeper') AS gk,
    COUNT(*) FILTER (WHERE position_primary = 'Defender') AS def,
    COUNT(*) FILTER (WHERE position_primary = 'Midfielder') AS mid,
    COUNT(*) FILTER (WHERE position_primary = 'Forward') AS fwd,
    COUNT(*) FILTER (WHERE position_primary NOT IN ('Goalkeeper','Defender','Midfielder','Forward')) AS other
FROM wc_2026_projected_squads
WHERE rank_in_squad <= 26 AND team_status = 'confirmed'
GROUP BY team_code
ORDER BY team_code;

-- 3c: Spot check — Brazil (should have no duplicates now)
SELECT
    rank_in_squad, known_as, position_primary, current_club,
    estimated_value_eur, data_confidence
FROM wc_2026_projected_squads
WHERE team_code = 'BRA' AND rank_in_squad <= 26
ORDER BY rank_in_squad;

-- 3d: Final totals
SELECT
    COUNT(*) AS total_tournament_players,
    COUNT(DISTINCT wc_team_code) AS teams_represented,
    COUNT(*) FILTER (WHERE in_squad = TRUE) AS in_primary_squad,
    COUNT(*) FILTER (WHERE in_squad = FALSE) AS reserves
FROM player_tournament;
```

Save ALL output to **`AZTECA_SQUAD_CLEANUP_RESULTS.md`**.
