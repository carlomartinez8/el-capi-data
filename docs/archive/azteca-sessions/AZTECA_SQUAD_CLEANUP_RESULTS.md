# Azteca — Squad Cleanup Results

**Run:** AZTECA_SQUAD_CLEANUP.md (all three issues)  
**Date:** 2026-03-11

---

========== Issue 1: Duplicate players in squads ==========
---------- 1a: Build _squad_duplicates ----------
psql:../run_squad_cleanup.sql:5: NOTICE:  table "_squad_duplicates" does not exist, skipping
DROP TABLE
SELECT 24
---------- 1b: Duplicate count ----------
 duplicate_tournament_entries 
------------------------------
                           24
(1 row)

---------- 1c: Duplicate entries ----------
     known_as     | wc_team_code | estimated_value_eur |       source_records       | data_confidence 
------------------+--------------+---------------------+----------------------------+-----------------
 Estêvão          | BRA          |            38000000 |                            | high
 Marquinhos       | BRA          |            55000000 |                            | high
 Raphinha         | BRA          |            90000000 |                            | high
 Rodrygo          | BRA          |           120000000 |                            | high
 Savinho          | BRA          |            50000000 |                            | high
 Odilon Kossounou | CIV          |            20000000 |                            | high
 Trezeguet        | EGY          |            12000000 |                            | high
 Gavi             | ESP          |            75000000 |                            | high
 Pedri            | ESP          |           100000000 |                            | high
 Rodri            | ESP          |           120000000 |                            | high
 Nizar Al Rashdan | JOR          |            10000000 |                            | high
 Ayman Yahya      | KSA          |             3000000 |                            | high
 Jorge Sánchez    | MEX          |             8000000 |                            | high
 Marcus Pedersen  | NOR          |              100000 | TM:41609                   | medium
 Diego Gómez      | PAR          |            10000000 |                            | high
 Vitinha          | POR          |            65000000 |                            | high
 Abdulaziz Hatem  | QAT          |             1000000 |                            | high
 Akram Afif       | QAT          |                     | APIF:apif_2544             | low
 Assim Madibo     | QAT          |                     | APIF:apif_2535             | low
 Homam Ahmed      | QAT          |                     | APIF:apif_175439           | low
 Meshaal Barsham  | QAT          |             1000000 |                            | high
 Mohammed Muntari | QAT          |             1000000 |                            | high
 Formose Mendy    | SEN          |            20000000 |                            | high
 Idrissa Gueye    | SEN          |             1000000 | TM:126665 + APIF:apif_2990 | high
(24 rows)

---------- 1d: DELETE duplicates from player_tournament ----------
DELETE 24
---------- 1e: Verify no duplicate names per team (expect 0 rows) ----------
 known_as | wc_team_code | appearances 
----------+--------------+-------------
(0 rows)

========== Issue 2: Position normalization ==========
---------- 2a: Un-normalized position counts ----------
 position_primary | cnt 
------------------+-----
 MID              |  52
 DEF              |  51
 FWD              |  48
 GK               |  33
(4 rows)

---------- 2b: UPDATE position_primary ----------
UPDATE 184
---------- 2c: Position counts after normalize ----------
 position_primary |  cnt  
------------------+-------
 Defender         | 13773
 Midfielder       | 13019
 Forward          | 11654
 Goalkeeper       |  4996
 Missing          |   189
(5 rows)

========== Issue 3: Rebuild projected squads ==========
---------- 3a: Rebuild wc_2026_projected_squads ----------
DROP TABLE
SELECT 2480
---------- 3b: Position balance (confirmed, top 26) ----------
 team_code | gk | def | mid | fwd | other 
-----------+----+-----+-----+-----+-------
 ALG       |  0 |   5 |  10 |  11 |     0
 ARG       |  0 |   5 |   8 |  13 |     0
 AUS       |  2 |   6 |  10 |   8 |     0
 AUT       |  0 |  13 |  10 |   3 |     0
 BEL       |  3 |   5 |  10 |   8 |     0
 BRA       |  0 |   4 |   6 |  16 |     0
 CAN       |  2 |   8 |   4 |  12 |     0
 CIV       |  0 |   8 |   7 |  11 |     0
 COL       |  0 |   6 |   6 |  14 |     0
 CPV       |  1 |   6 |   5 |  14 |     0
 CRO       |  2 |   6 |  13 |   5 |     0
 CUW       |  0 |  14 |   3 |   9 |     0
 ECU       |  0 |   9 |   6 |  11 |     0
 EGY       |  2 |   8 |   5 |  11 |     0
 ENG       |  0 |   8 |  11 |   7 |     0
 ESP       |  1 |   8 |  11 |   6 |     0
 FRA       |  0 |   8 |   8 |  10 |     0
 GER       |  0 |   6 |  11 |   9 |     0
 GHA       |  2 |   7 |   4 |  13 |     0
 HAI       |  2 |  11 |   5 |   8 |     0
 IRN       |  3 |   7 |   6 |  10 |     0
 JOR       |  1 |   6 |   9 |  10 |     0
 JPN       |  1 |   6 |   9 |  10 |     0
 KOR       |  1 |   5 |  13 |   7 |     0
 KSA       |  2 |  10 |   5 |   9 |     0
 MAR       |  1 |   9 |   5 |  11 |     0
 MEX       |  0 |   9 |  10 |   7 |     0
 NED       |  2 |  11 |   7 |   6 |     0
 NOR       |  0 |   9 |   6 |  11 |     0
 NZL       |  2 |   9 |   9 |   6 |     0
 PAN       |  2 |   9 |   4 |  11 |     0
 PAR       |  2 |   9 |   6 |   9 |     0
 POR       |  1 |   7 |   9 |   9 |     0
 QAT       |  2 |   9 |  10 |   5 |     0
 RSA       |  1 |   5 |  10 |  10 |     0
 SCO       |  0 |   9 |  11 |   6 |     0
 SEN       |  2 |  10 |   7 |   7 |     0
 SUI       |  1 |   9 |  10 |   6 |     0
 TUN       |  1 |   6 |  12 |   7 |     0
 URU       |  0 |  10 |   9 |   7 |     0
 USA       |  1 |   9 |  10 |   6 |     0
 UZB       |  2 |   7 |   8 |   9 |     0
(42 rows)

---------- 3c: Brazil spot check ----------
 rank_in_squad |      known_as      | position_primary |         current_club          | estimated_value_eur | data_confidence 
---------------+--------------------+------------------+-------------------------------+---------------------+-----------------
             1 | Vinicius Junior    | Forward          | Real Madrid                   |           150000000 | high
             2 | Raphinha           | Forward          | Barcelona                     |            90000000 | high
             3 | Raphinha           | Forward          | Barcelona                     |            80000000 | high
             4 | Estêvão            | Forward          | Palmeiras                     |            80000000 | high
             5 | João Pedro         | Forward          | Chelsea                       |            75000000 | high
             6 | Bruno Guimarães    | Midfielder       | Newcastle                     |            75000000 | high
             7 | Gabriel Magalhães  | Defender         | Arsenal                       |            75000000 | high
             8 | Matheus Cunha      | Forward          | Manchester United             |            70000000 | high
             9 | Rodrygo            | Forward          | Real Madrid                   |            60000000 | high
            10 | Igor Thiago        | Forward          | Brentford                     |            50000000 | high
            11 | Savinho            | Forward          | Man City                      |            50000000 | high
            12 | Murillo            | Defender         | Nottingham Forest             |            50000000 | high
            13 | Neymar             | Forward          | Santos                        |            50000000 | high
            14 | Andrey Santos      | Midfielder       | Chelsea                       |            45000000 | high
            15 | Gabriel Martinelli | Forward          | Arsenal                       |            45000000 | high
            16 | Rayan              | Forward          | Vasco DA Gama                 |            40000000 | high
            17 | Danilo             | Defender         | Flamengo                      |            40000000 | high
            18 | Éderson            | Midfielder       | Atalanta                      |            40000000 | high
            19 | Savinho            | Forward          | Manchester City Football Club |            40000000 | medium
            20 | Estêvão            | Forward          | Chelsea                       |            38000000 | high
            21 | Fabinho            | Midfielder       | Al-Ittihad FC                 |            38000000 | high
            22 | Bremer             | Defender         | Juventus                      |            35000000 | high
            23 | Lucas Paquetá      | Midfielder       | West Ham                      |            35000000 | high
            24 | Evanilson          | Forward          | Bournemouth                   |            35000000 | high
            25 | João Gomes         | Midfielder       | Wolves                        |            35000000 | high
            26 | Igor Paixão        | Forward          | Marseille                     |            35000000 | high
(26 rows)

---------- 3d: player_tournament totals ----------
 total_tournament_players | teams_represented | in_primary_squad | reserves 
--------------------------+-------------------+------------------+----------
                     1761 |                42 |             1176 |      585
(1 row)

========== DONE ==========
