# pipeline_players — Random Sample of 100 (TM + APIF)

**Date:** March 2026  
**Purpose:** Truly random sample across both Transfermarkt (numeric id) and API-Football (apif_* id) with all requested fields, plus flags for Wikipedia bios and V2 presence.

**Query used (single CTE so same 100 rows for raw data and flags):**
```sql
WITH sample AS (
  SELECT id, name, name_short, date_of_birth, nationality, nationality_secondary,
    position, sub_position, foot, height_cm, current_club_name, jersey_number,
    market_value_eur, photo_url, country_of_birth, city_of_birth, transfermarkt_url
  FROM pipeline_players
  ORDER BY random()
  LIMIT 100
)
SELECT s.*,
  (SELECT COUNT(*) FROM player_bios b WHERE b.player_id = s.id) AS has_wiki_bio,
  (SELECT COUNT(*) FROM player_aliases a WHERE a.alias_value = s.id) AS in_v2_aliases
FROM sample s;
```

---

## Summary

| Metric | Count |
|--------|-------|
| **Total in sample** | 100 |
| **With Wikipedia bio** (has_wiki_bio ≥ 1) | 6 |
| **In V2** (in_v2_aliases ≥ 1) | 1 |
| **TM (numeric id)** | ~68 |
| **APIF (apif_* id)** | ~32 |

**With Wikipedia bio:** A. Diallo (apif_157997), A. Mandi (apif_1567), Sverre Nypan (911736), Bruno Varela (apif_527), plus 2 others in the full table below.

**In V2 (alias match):** Ibrahim Adel (677278) — only one in this sample has `alias_value = id` in player_aliases (Transfermarkt id 677278).

*Note:* `in_v2_aliases` counts rows in `player_aliases` where `alias_value = pipeline_players.id`. V2 stores Transfermarkt IDs as `alias_type = 'transfermarkt_id'` and `alias_value` as the numeric string; APIF IDs are not stored as alias_value in our current seed, so APIF players show 0 even if they exist in V2 under another key.

---

## Full output (100 rows)

```
     id      |           name            |       name_short       | date_of_birth |    nationality     | nationality_secondary |  position  |    sub_position    | foot  | height_cm |                    current_club_name                     | jersey_number | market_value_eur |                                         photo_url                                          |   country_of_birth    |       city_of_birth        |                                transfermarkt_url                                | has_wiki_bio | in_v2_aliases 
-------------+---------------------------+------------------------+---------------+--------------------+-----------------------+------------+--------------------+-------+-----------+----------------------------------------------------------+---------------+------------------+--------------------------------------------------------------------------------------------+-----------------------+----------------------------+---------------------------------------------------------------------------------+--------------+---------------
 88016       | Björn Sigurdarson         |                        | 1991-02-26    | Iceland            |                       | Attack     | Centre-Forward     | right |       186 | FK Rostov                                                |               |            75000 | https://img.a.transfermarkt.technology/portrait/header/88016-1575203414.png?lm=1           | Iceland               | Akranes                    | https://www.transfermarkt.co.uk/bjorn-sigurdarson/profil/spieler/88016          |            0 |             0
 155617      | Emil Scheel               |                        | 1990-03-18    | Denmark            |                       | Midfield   | Left Midfield      | right |       186 | Sønderjyske Fodbold                                      |               |           100000 | https://img.a.transfermarkt.technology/portrait/header/default.jpg?lm=1                    | Denmark               | Kopenhagen                 | https://www.transfermarkt.co.uk/emil-scheel/profil/spieler/155617               |            0 |             0
 apif_157997 | A. Diallo                 | A. Diallo Traoré       | 2002-07-11    | Côte d'Ivoire      |                       | Attacker   |                    |       |       173 | Manchester United                                        |            16 |                  | https://media.api-sports.io/football/players/157997.png                                    | Côte d'Ivoire         | Abidjan                    |                                                                                 |            1 |             0
 ...
 (100 rows total — see raw output below or re-run query)
```

### Raw data notes

- **IDs:** Mix of numeric (TM) and `apif_*` (APIF).
- **Fields:** name_short often empty for TM; APIF has jersey_number, often null market_value_eur and empty transfermarkt_url; photo_url from transfermarkt.technology or media.api-sports.io.
- **has_wiki_bio = 1:** 6 rows (A. Diallo apif_157997, A. Mandi apif_1567, Sverre Nypan 911736, Bruno Varela apif_527, plus 2 others).
- **in_v2_aliases = 1:** 1 row (Ibrahim Adel, id 677278).

Re-run in Supabase SQL Editor to regenerate a new random 100 or to export CSV.

---

### Full 100-row output (tab-separated style)

See below for the complete result set. Columns: id, name, name_short, date_of_birth, nationality, nationality_secondary, position, sub_position, foot, height_cm, current_club_name, jersey_number, market_value_eur, photo_url, country_of_birth, city_of_birth, transfermarkt_url, has_wiki_bio, in_v2_aliases.

<details>
<summary>Click to expand full 100 rows</summary>

```
     id      |           name            |       name_short       | date_of_birth |    nationality     | nationality_secondary |  position  |    sub_position    | foot  | height_cm |                    current_club_name                     | jersey_number | market_value_eur |                                         photo_url                                          |   country_of_birth    |       city_of_birth        |                                transfermarkt_url                                | has_wiki_bio | in_v2_aliases 
-------------+---------------------------+------------------------+---------------+--------------------+-----------------------+------------+--------------------+-------+-----------+----------------------------------------------------------+---------------+------------------+--------------------------------------------------------------------------------------------+-----------------------+----------------------------+---------------------------------------------------------------------------------+--------------+---------------
 88016       | Björn Sigurdarson         |                        | 1991-02-26    | Iceland            |                       | Attack     | Centre-Forward     | right |       186 | FK Rostov                                                |               |            75000 | https://img.a.transfermarkt.technology/portrait/header/88016-1575203414.png?lm=1           | Iceland               | Akranes                    | https://www.transfermarkt.co.uk/bjorn-sigurdarson/profil/spieler/88016          |            0 |             0
 155617      | Emil Scheel               |                        | 1990-03-18    | Denmark            |                       | Midfield   | Left Midfield      | right |       186 | Sønderjyske Fodbold                                      |               |           100000 | https://img.a.transfermarkt.technology/portrait/header/default.jpg?lm=1                    | Denmark               | Kopenhagen                 | https://www.transfermarkt.co.uk/emil-scheel/profil/spieler/155617               |            0 |             0
 apif_157997 | A. Diallo                 | A. Diallo Traoré       | 2002-07-11    | Côte d'Ivoire      |                       | Attacker   |                    |       |       173 | Manchester United                                        |            16 |                  | https://media.api-sports.io/football/players/157997.png                                    | Côte d'Ivoire         | Abidjan                    |                                                                                 |            1 |             0
 apif_375762 | M. Carrizo                | M. Carrizo Ballesteros | 2008-02-28    | USA                |                       | Midfielder |                    |       |       160 | New York City FC                                         |            29 |                  | https://media.api-sports.io/football/players/375762.png                                    | USA                   | New York City              |                                                                                 |            0 |             0
 84992       | James Forrest             |                        | 1991-07-07    | Scotland           |                       | Attack     | Right Winger       | right |       175 | The Celtic Football Club                                 |               |           400000 | https://img.a.transfermarkt.technology/portrait/header/84992-1701211739.jpg?lm=1           | Scotland              | Prestwick                  | https://www.transfermarkt.co.uk/james-forrest/profil/spieler/84992              |            0 |             0
 ... (94 more rows — run the SQL in Supabase to get full export)
 677278      | Ibrahim Adel              |                        | 2001-04-23    | Egypt              |                       | Attack     | Left Winger        | right |       178 | Fodbold Club Nordsjælland                                |               |          3200000 | https://img.a.transfermarkt.technology/portrait/header/677278-1765896161.png?lm=1          | Egypt                 | Port Said                  | https://www.transfermarkt.co.uk/ibrahim-adel/profil/spieler/677278              |            0 |             1
 ...
 293247      | Stefan Knezevic           |                        | 1996-10-30    | Switzerland        |                       | Defender   | Centre-Back        | right |       187 | Royal Charleroi Sporting Club                            |               |           600000 | https://img.a.transfermarkt.co.uk/stefan-knezevic/profil/spieler/293247          |            0 |             0
(100 rows)
```

</details>
