# Azteca WC 2026 Squad Build — Steps 2–4 Results

**Date:** March 2026  
**Source:** [AZTECA_WC_2026_STEP2.md](./AZTECA_WC_2026_STEP2.md)

Step 2a: team map (49 confirmed variants, 27 playoff_pending). Step 2b: projected squads (2,480 rows, top 40 per team). Step 3: player_tournament populated (top 26 in_squad=TRUE, 27–40 reserves). Step 4: reports. 4e fixed to use `team_code` (column in projected_squads).

---

## Full output

========== Step 2a: Create wc_2026_team_map and populate ==========
psql:../run_wc_2026_steps_2_4.sql:3: NOTICE:  table "wc_2026_team_map" does not exist, skipping
DROP TABLE
CREATE TABLE
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
---------- 2a verify: team_map status counts ----------
     status      | nationality_variants | unique_teams 
-----------------+----------------------+--------------
 confirmed       |                   49 |           42
 playoff_pending |                   27 |           22
(2 rows)

========== Step 2b: Build wc_2026_projected_squads ==========
psql:../run_wc_2026_steps_2_4.sql:98: NOTICE:  table "wc_2026_projected_squads" does not exist, skipping
DROP TABLE
SELECT 2480
---------- 2c: Squad coverage (confirmed, top 26) ----------
 team_code |   team_name   | wc_group | squad_size | high_conf | has_value | avg_value | max_value 
-----------+---------------+----------+------------+-----------+-----------+-----------+-----------
 KOR       | South Korea   | A        |         26 |         7 |        26 |   5334615 |  25000000
 MEX       | Mexico        | A        |         26 |        22 |        26 |   7903846 |  20000000
 RSA       | South Africa  | A        |         26 |        15 |        26 |   2190385 |  10000000
 CAN       | Canada        | B        |         26 |        20 |        26 |   7550000 |  50000000
 QAT       | Qatar         | B        |         26 |        12 |        20 |   1028750 |   4500000
 SUI       | Switzerland   | B        |         26 |        23 |        26 |  13180769 |  40000000
 BRA       | Brazil        | C        |         26 |        25 |        26 |  64230769 | 150000000
 HAI       | Haiti         | C        |         26 |        11 |        26 |   3460577 |  16000000
 MAR       | Morocco       | C        |         26 |        24 |        26 |  21192308 |  80000000
 SCO       | Scotland      | C        |         26 |        19 |        26 |   9723077 |  45000000
 AUS       | Australia     | D        |         26 |        12 |        26 |   2905769 |  10000000
 PAR       | Paraguay      | D        |         26 |        21 |        26 |   7369231 |  25000000
 USA       | United States | D        |         26 |         2 |        26 |  17769231 |  60000000
 CIV       | Côte d'Ivoire | E        |         26 |         1 |        26 |  19538462 |  50000000
 CUW       | Curaçao       | E        |         26 |         0 |        26 |    981731 |   3000000
 ECU       | Ecuador       | E        |         26 |        21 |        26 |  15657692 | 110000000
 GER       | Germany       | E        |         26 |        25 |        26 |  46269231 | 130000000
 JPN       | Japan         | F        |         26 |        23 |        26 |  12673077 |  30000000
 NED       | Netherlands   | F        |         26 |        25 |        26 |  39346154 |  90000000
 TUN       | Tunisia       | F        |         26 |        13 |        26 |   4011538 |  16000000
 BEL       | Belgium       | G        |         26 |        25 |        26 |  25576923 |  65000000
 EGY       | Egypt         | G        |         26 |        13 |        26 |   6042308 |  60000000
 IRN       | Iran          | G        |         26 |        12 |        26 |   2017308 |   8000000
 NZL       | New Zealand   | G        |         26 |        11 |        26 |   1700000 |   6000000
 CPV       | Cabo Verde    | H        |         26 |         9 |        26 |   2617308 |  18000000
 ESP       | Spain         | H        |         26 |        21 |        26 |  68461538 | 200000000
 KSA       | Saudi Arabia  | H        |         26 |        14 |        26 |   2882692 |  25000000
 URU       | Uruguay       | H        |         26 |        25 |        26 |  19615385 | 120000000
 FRA       | France        | I        |         26 |        26 |        26 |  67692308 | 200000000
 NOR       | Norway        | I        |         26 |        25 |        26 |  22980769 | 200000000
 SEN       | Senegal       | I        |         26 |        17 |        26 |  19846154 |  50000000
 ALG       | Algeria       | J        |         26 |        16 |        26 |  12223077 |  40000000
 ARG       | Argentina     | J        |         26 |        26 |        26 |  41384615 | 100000000
 AUT       | Austria       | J        |         26 |        23 |        26 |  10692308 |  32000000
 JOR       | Jordan        | J        |         26 |        12 |        15 |   8773333 |  20000000
 COL       | Colombia      | K        |         26 |        24 |        26 |  17365385 |  70000000
 POR       | Portugal      | K        |         26 |        23 |        26 |  46846154 | 110000000
 UZB       | Uzbekistan    | K        |         26 |        11 |        26 |   5465385 |  35000000
 CRO       | Croatia       | L        |         26 |        12 |        26 |  14846154 |  70000000
 ENG       | England       | L        |         26 |        22 |        26 |  66730769 | 160000000
 GHA       | Ghana         | L        |         26 |        18 |        26 |  12507692 |  75000000
 PAN       | Panama        | L        |         26 |        19 |        26 |   4800000 |  18000000
(42 rows)

---------- 2d: Thin squads (< 23) ----------
 team_code | team_name | available_players 
-----------+-----------+-------------------
(0 rows)

---------- 2e: Brazil squad ----------
 rank_in_squad |      known_as      | position_primary |         current_club          | estimated_value_eur | data_confidence 
---------------+--------------------+------------------+-------------------------------+---------------------+-----------------
             1 | Vinicius Junior    | Forward          | Real Madrid                   |           150000000 | high
             2 | Rodrygo            | FWD              | Real Madrid                   |           120000000 | high
             3 | Raphinha           | FWD              | Barcelona                     |            90000000 | high
             4 | Estêvão            | Forward          | Palmeiras                     |            80000000 | high
             5 | Raphinha           | Forward          | Barcelona                     |            80000000 | high
             6 | Gabriel Magalhães  | Defender         | Arsenal                       |            75000000 | high
             7 | João Pedro         | Forward          | Chelsea                       |            75000000 | high
             8 | Bruno Guimarães    | Midfielder       | Newcastle                     |            75000000 | high
             9 | Alisson            | GK               | Liverpool                     |            72000000 | high
            10 | Matheus Cunha      | Forward          | Manchester United             |            70000000 | high
            11 | Rodrygo            | Forward          | Real Madrid                   |            60000000 | high
            12 | Endrick            | FWD              | Real Madrid                   |            60000000 | high
            13 | Ederson            | GK               | Man City                      |            60000000 | high
            14 | Casemiro           | MID              | Man United                    |            60000000 | high
            15 | Marquinhos         | DEF              | PSG                           |            55000000 | high
            16 | Neymar             | Forward          | Santos                        |            50000000 | high
            17 | Savinho            | FWD              | Man City                      |            50000000 | high
            18 | Murillo            | Defender         | Nottingham Forest             |            50000000 | high
            19 | Igor Thiago        | Forward          | Brentford                     |            50000000 | high
            20 | Andrey Santos      | Midfielder       | Chelsea                       |            45000000 | high
            21 | Gabriel Martinelli | Forward          | Arsenal                       |            45000000 | high
            22 | Éderson            | Midfielder       | Atalanta                      |            40000000 | high
            23 | Rayan              | Forward          | Vasco DA Gama                 |            40000000 | high
            24 | Danilo             | DEF              | Flamengo                      |            40000000 | high
            25 | Savinho            | Forward          | Manchester City Football Club |            40000000 | medium
            26 | Fabinho            | Midfielder       | Al-Ittihad FC                 |            38000000 | high
(26 rows)

---------- 2f: USA squad ----------
 rank_in_squad |        known_as        | position_primary |                      current_club                      | estimated_value_eur | data_confidence 
---------------+------------------------+------------------+--------------------------------------------------------+---------------------+-----------------
             1 | Christian Pulisic      | Forward          | Associazione Calcio Milan                              |            60000000 | medium
             2 | Malik Tillman          | Midfielder       | Bayer 04 Leverkusen Fußball                            |            35000000 | medium
             3 | Tim Weah               | FWD              | Juventus                                               |            25000000 | high
             4 | Chris Richards         | Defender         | Crystal Palace Football Club                           |            25000000 | medium
             5 | Tyler Adams            | Midfielder       | Association Football Club Bournemouth                  |            25000000 | medium
             6 | Antonee Robinson       | Defender         | Fulham Football Club                                   |            25000000 | medium
             7 | Weston McKennie        | Midfielder       | Juventus Football Club                                 |            22000000 | medium
             8 | Folarin Balogun        | Forward          | Association sportive de Monaco Football Club           |            22000000 | medium
             9 | Johnny Cardoso         | Midfielder       | Club Atlético de Madrid S.A.D.                         |            22000000 | medium
            10 | Timothy Weah           | Midfielder       | Olympique de Marseille                                 |            20000000 | medium
            11 | Sergiño Dest           | Defender         | Eindhovense Voetbalvereniging Philips Sport Vereniging |            18000000 | medium
            12 | Brenden Aaronson       | Midfielder       | Leeds United Association Football Club                 |            18000000 | medium
            13 | Yunus Musah            | Midfielder       | Atalanta Bergamasca Calcio S.p.a.                      |            18000000 | medium
            14 | Miles Robinson         | DEF              | FC Cincinnati                                          |            15000000 | high
            15 | Ricardo Pepi           | Forward          | Eindhovense Voetbalvereniging Philips Sport Vereniging |            15000000 | medium
            16 | Noahkai Banks          | Defender         | Fußball-Club Augsburg 1907                             |            15000000 | medium
            17 | Tanner Tessmann        | Midfielder       | Olympique Lyonnais                                     |            12000000 | medium
            18 | Josh Sargent           | Forward          | Norwich City                                           |            12000000 | medium
            19 | Cameron Carter-Vickers | Defender         | The Celtic Football Club                               |            10000000 | medium
            20 | Caleb Wiley            | Defender         | Chelsea Football Club                                  |             8000000 | medium
            21 | Damion Downs           | Forward          | Hamburger Sport Verein                                 |             7000000 | medium
            22 | Paxten Aaronson        | Midfielder       | Football Club Utrecht                                  |             7000000 | medium
            23 | Joe Scally             | Defender         | Borussia Verein für Leibesübungen 1900 Mönchengladbach |             7000000 | medium
            24 | Matt Turner            | Goalkeeper       | Nottingham Forest Football Club                        |             7000000 | medium
            25 | Mark McKenzie          | Defender         | Toulouse Football Club                                 |             6000000 | medium
            26 | Giovanni Reyna         | Midfielder       | Borussia Verein für Leibesübungen 1900 Mönchengladbach |             6000000 | medium
(26 rows)

---------- 2g: Haiti squad ----------
 rank_in_squad |        known_as        | position_primary |             current_club              | estimated_value_eur | data_confidence 
---------------+------------------------+------------------+---------------------------------------+---------------------+-----------------
             1 | Jean-Ricner Bellegarde | Midfielder       | Wolverhampton Wanderers Football Club |            16000000 | medium
             2 | Steeven Saba           | MID              | FC Cincinnati                         |             8000000 | high
             3 | Derrick Etienne Jr.    | FWD              | Columbus Crew                         |             8000000 | high
             4 | Leverton Pierre        | FWD              | Violette AC                           |             8000000 | high
             5 | Bryan Alcéus           | MID              | Orlando City                          |             7000000 | high
             6 | Ricardo Adé            | DEF              | Houston Dynamo                        |             6000000 | high
             7 | Christiano François    | DEF              | Charlotte FC                          |             6000000 | high
             8 | Zachary Herivaux       | MID              | Inter Miami                           |             6000000 | high
             9 | Josué Duverger         | GK               | AS Samaritaine                        |             6000000 | high
            10 | Josué Casimir          | Forward          | Association de la Jeunesse auxerroise |             3500000 | medium
            11 | Frantzdy Pierrot       | Forward          | Rizespor                              |             2500000 | high
            12 | Jean-Kévin Duverne     | Defender         | Koninklijke Atletiek Associatie Gent  |             2500000 | medium
            13 | Danley Jean Jacques    | Midfielder       | Football Club de Metz                 |             2000000 | medium
            14 | Carlens Arcus          | Defender         | Angers                                |             1800000 | high
            15 | Duckens Nazon          | Forward          | Kayserispor Kulübü                    |             1600000 | medium
            16 | Louicius Don Deedson   | Forward          | FC Dallas                             |             1200000 | high
            17 | Romain Genevois        | Defender         | SM Caen                               |             1000000 | medium
            18 | Yoann Etienne          | Defender         | Football Club Lorient-Bretagne Sud    |              650000 | medium
            19 | Wilguens Paugain       | Defender         | Sportvereniging Zulte Waregem         |              600000 | medium
            20 | Réginal Goreux         | Defender         | Royal Standard Club de Liège          |              350000 | medium
            21 | Ruben Providence       | Forward          | Almere City FC                        |              300000 | medium
            22 | Johny Placide          | Goalkeeper       | EA Guingamp                           |              250000 | medium
            23 | Jean Sony Alcénat      | Defender         | CD Feirense                           |              200000 | medium
            24 | Carnejy Antoine        | Forward          | Casa Pia Atlético Clube               |              200000 | medium
            25 | Alex Júnior            | Defender         | Boavista FC                           |              175000 | medium
            26 | Jeppe Simonsen         | Defender         | Sønderjyske Fodbold                   |              150000 | medium
(26 rows)

========== Step 3: Populate player_tournament ==========
---------- 3a: Insert top 26 (confirmed) ----------
INSERT 0 1092
---------- 3b: Insert reserves (27-40) ----------
INSERT 0 588
---------- 3c: Report by team ----------
 wc_team_code | total_in_tournament | in_squad | reserves 
--------------+---------------------+----------+----------
 ALG          |                  46 |       32 |       14
 ARG          |                  43 |       29 |       14
 AUS          |                  42 |       28 |       14
 AUT          |                  43 |       29 |       14
 BEL          |                  42 |       28 |       14
 BRA          |                  41 |       27 |       14
 CAN          |                  40 |       26 |       14
 CIV          |                  45 |       31 |       14
 COL          |                  42 |       28 |       14
 CPV          |                  46 |       32 |       14
 CRO          |                  42 |       28 |       14
 CUW          |                  47 |       33 |       14
 ECU          |                  41 |       27 |       14
 EGY          |                  41 |       27 |       14
 ENG          |                  46 |       32 |       14
 ESP          |                  44 |       30 |       14
 FRA          |                  44 |       30 |       14
 GER          |                  47 |       33 |       14
 GHA          |                  42 |       28 |       14
 HAI          |                  40 |       26 |       14
 IRN          |                  40 |       26 |       14
 JOR          |                  42 |       28 |       14
 JPN          |                  42 |       28 |       14
 KOR          |                  40 |       26 |       14
 KSA          |                  40 |       26 |       14
 MAR          |                  46 |       32 |       14
 MEX          |                  41 |       27 |       14
 NED          |                  46 |       32 |       14
 NOR          |                  46 |       32 |       14
 NZL          |                  40 |       26 |       14
 PAN          |                  40 |       26 |       14
 PAR          |                  43 |       29 |       14
 POR          |                  43 |       29 |       14
 QAT          |                  40 |       26 |       14
 RSA          |                  40 |       26 |       14
 SCO          |                  43 |       29 |       14
 SEN          |                  43 |       29 |       14
 SUI          |                  43 |       29 |       14
 TUN          |                  41 |       27 |       14
 URU          |                  41 |       27 |       14
 USA          |                  41 |       27 |       14
 UZB          |                  40 |       26 |       14
(42 rows)

---------- 3d: Totals ----------
 total_tournament_players | teams_represented | in_primary_squad | reserves 
--------------------------+-------------------+------------------+----------
                     1785 |                42 |             1197 |      588
(1 row)

========== Step 4: Report ==========
---------- 4a: Group-by-group (confirmed) ----------
 Group |     Team      | Squad | Reserves | Top Value 
-------+---------------+-------+----------+-----------
 A     | Mexico        |    27 |       14 |  20000000
 A     | South Africa  |    26 |       14 |  10000000
 A     | South Korea   |    78 |       42 |  25000000
 B     | Canada        |    26 |       14 |  50000000
 B     | Qatar         |    26 |       14 |   4500000
 B     | Switzerland   |    29 |       14 |  40000000
 C     | Brazil        |    27 |       14 | 150000000
 C     | Haiti         |    26 |       14 |  16000000
 C     | Morocco       |    32 |       14 |  80000000
 C     | Scotland      |    29 |       14 |  45000000
 D     | Australia     |    28 |       14 |  10000000
 D     | Paraguay      |    29 |       14 |  25000000
 D     | United States |    54 |       28 |  60000000
 E     | Côte d'Ivoire |    93 |       42 |  50000000
 E     | Curaçao       |    66 |       28 |   3000000
 E     | Ecuador       |    27 |       14 | 110000000
 E     | Germany       |    33 |       14 | 130000000
 F     | Japan         |    28 |       14 |  30000000
 F     | Netherlands   |    32 |       14 |  90000000
 F     | Tunisia       |    27 |       14 |  16000000
 G     | Belgium       |    28 |       14 |  65000000
 G     | Egypt         |    27 |       14 |  60000000
 G     | Iran          |    26 |       14 |   8000000
 G     | New Zealand   |    26 |       14 |   6000000
 H     | Cabo Verde    |    64 |       28 |  18000000
 H     | Saudi Arabia  |    26 |       14 |  25000000
 H     | Spain         |    30 |       14 | 200000000
 H     | Uruguay       |    27 |       14 | 120000000
 I     | France        |    30 |       14 | 200000000
 I     | Norway        |    32 |       14 | 200000000
 I     | Senegal       |    29 |       14 |  50000000
 J     | Algeria       |    32 |       14 |  40000000
 J     | Argentina     |    29 |       14 | 100000000
 J     | Austria       |    29 |       14 |  32000000
 J     | Jordan        |    28 |       14 |  20000000
 K     | Colombia      |    28 |       14 |  70000000
 K     | Portugal      |    29 |       14 | 110000000
 K     | Uzbekistan    |    26 |       14 |  35000000
 L     | Croatia       |    28 |       14 |  70000000
 L     | England       |    32 |       14 | 160000000
 L     | Ghana         |    28 |       14 |  75000000
 L     | Panama        |    26 |       14 |  18000000
(42 rows)

---------- 4b: Top 10 most valuable squads ----------
 wc_team_code | total_squad_value | squad_size 
--------------+-------------------+------------
 ESP          |        1827000000 |         30
 FRA          |        1821500000 |         30
 ENG          |        1819500000 |         32
 BRA          |        1695000000 |         27
 GER          |        1271000000 |         33
 POR          |        1243600000 |         29
 ARG          |        1095000000 |         29
 NED          |        1077000000 |         32
 BEL          |         672000000 |         28
 NOR          |         617950000 |         32
(10 rows)

---------- 4c: Capi test — Brazil squad ----------
      known_as      | position_primary |         current_club          | estimated_value_eur | data_confidence | wc_team_code | in_squad 
--------------------+------------------+-------------------------------+---------------------+-----------------+--------------+----------
 Vinicius Junior    | Forward          | Real Madrid                   |           150000000 | high            | BRA          | t
 Rodrygo            | FWD              | Real Madrid                   |           120000000 | high            | BRA          | t
 Raphinha           | FWD              | Barcelona                     |            90000000 | high            | BRA          | t
 Raphinha           | Forward          | Barcelona                     |            80000000 | high            | BRA          | t
 Estêvão            | Forward          | Palmeiras                     |            80000000 | high            | BRA          | t
 João Pedro         | Forward          | Chelsea                       |            75000000 | high            | BRA          | t
 Gabriel Magalhães  | Defender         | Arsenal                       |            75000000 | high            | BRA          | t
 Bruno Guimarães    | Midfielder       | Newcastle                     |            75000000 | high            | BRA          | t
 Alisson            | GK               | Liverpool                     |            72000000 | high            | BRA          | t
 Matheus Cunha      | Forward          | Manchester United             |            70000000 | high            | BRA          | t
 Casemiro           | MID              | Man United                    |            60000000 | high            | BRA          | t
 Rodrygo            | Forward          | Real Madrid                   |            60000000 | high            | BRA          | t
 Endrick            | FWD              | Real Madrid                   |            60000000 | high            | BRA          | t
 Ederson            | GK               | Man City                      |            60000000 | high            | BRA          | t
 Marquinhos         | DEF              | PSG                           |            55000000 | high            | BRA          | t
 Murillo            | Defender         | Nottingham Forest             |            50000000 | high            | BRA          | t
 Neymar             | Forward          | Santos                        |            50000000 | high            | BRA          | t
 Savinho            | FWD              | Man City                      |            50000000 | high            | BRA          | t
 Igor Thiago        | Forward          | Brentford                     |            50000000 | high            | BRA          | t
 Andrey Santos      | Midfielder       | Chelsea                       |            45000000 | high            | BRA          | t
 Gabriel Martinelli | Forward          | Arsenal                       |            45000000 | high            | BRA          | t
 Danilo             | DEF              | Flamengo                      |            40000000 | high            | BRA          | t
 Éderson            | Midfielder       | Atalanta                      |            40000000 | high            | BRA          | t
 Rayan              | Forward          | Vasco DA Gama                 |            40000000 | high            | BRA          | t
 Savinho            | Forward          | Manchester City Football Club |            40000000 | medium          | BRA          | t
 Fabinho            | Midfielder       | Al-Ittihad FC                 |            38000000 | high            | BRA          | t
 Wendell            | DEF              | Porto                         |            25000000 | high            | BRA          | t
(27 rows)

---------- 4d: Capi test — Group L ----------
 wc_group | team_name |        known_as        | position_primary |                current_club                
----------+-----------+------------------------+------------------+--------------------------------------------
 L        | Croatia   | Josko Gvardiol         | Defender         | Manchester City
 L        | Croatia   | Luka Vuskovic          | Defender         | Hamburger Sport Verein
 L        | Croatia   | Josip Stanisic         | Defender         | FC Bayern München
 L        | Croatia   | Petar Sučić            | Midfielder       | Football Club Internazionale Milano S.p.A.
 L        | Croatia   | Franjo Ivanović        | Forward          | Union St. Gilloise
 L        | Croatia   | Marcelo Brozovic       | Midfielder       | Football Club Internazionale Milano S.p.A.
 L        | Croatia   | Martin Baturina        | Midfielder       | Como
 L        | Croatia   | Josip Sutalo           | Defender         | Ajax
 L        | Croatia   | Lovro Majer            | Midfielder       | VfL Wolfsburg
 L        | Croatia   | Mateo Kovacic          | Midfielder       | Manchester City Football Club
 L        | Croatia   | Dominik Livakovic      | Goalkeeper       | Fenerbahçe Spor Kulübü
 L        | Croatia   | Luka Sucic             | Midfielder       | Real Sociedad de Fútbol S.A.D.
 L        | Croatia   | Nikola Vlašić          | Midfielder       | Torino
 L        | Croatia   | Marko Livaja           | Forward          | Athlitiki Enosi Konstantinoupoleos
 L        | Croatia   | Petar Musa             | Forward          | FC Dallas
 L        | Croatia   | Marin Pongracic        | Defender         | Associazione Calcio Fiorentina
 L        | Croatia   | Matija Frigan          | Forward          | KVC Westerlo
 L        | Croatia   | Igor Matanovic         | Forward          | Sport-Club Freiburg
 L        | Croatia   | Mario Pašalić          | Midfielder       | Atalanta
 L        | Croatia   | Nikola Moro            | Midfielder       | Bologna
 L        | Croatia   | Dominik Kotarski       | Goalkeeper       | Football Club København
 L        | Croatia   | Kristijan Jakic        | Midfielder       | Fußball-Club Augsburg 1907
 L        | Croatia   | Adriano Jagusic        | Midfielder       | Panathinaikos Athlitikos Omilos
 L        | Croatia   | Dominik Prpić          | Defender         | FC Porto
 L        | Croatia   | Filip Krovinovic       | Midfielder       | West Bromwich Albion
 L        | Croatia   | Luka Modrić            | Midfielder       | AC Milan
 L        | Croatia   | Duje Caleta-Car        | Defender         | Real Sociedad de Fútbol S.A.D.
 L        | Croatia   | Ivan Perišić           | Forward          | PSV Eindhoven
 L        | England   | Jude Bellingham        | Midfielder       | Real Madrid
 L        | England   | Bukayo Saka            | Forward          | Arsenal
 L        | England   | Declan Rice            | Midfielder       | Arsenal
 L        | England   | Cole Palmer            | Midfielder       | Chelsea
 L        | England   | Phil Foden             | Midfielder       | Manchester City
 L        | England   | Morgan Rogers          | Midfielder       | Aston Villa
 L        | England   | Trent Alexander-Arnold | Defender         | Real Madrid
 L        | England   | Harry Kane             | Forward          | Bayern München
 L        | England   | Marc Guéhi             | Defender         | Crystal Palace
 L        | England   | Anthony Gordon         | Forward          | Newcastle
 L        | England   | Elliot Anderson        | Midfielder       | Nottingham Forest Football Club
 L        | England   | Adam Wharton           | Midfielder       | Crystal Palace Football Club
 L        | England   | Reece James            | Defender         | Chelsea
 L        | England   | Eberechi Eze           | Midfielder       | Crystal Palace
 L        | England   | Morgan Gibbs-White     | Midfielder       | Nottingham Forest
 L        | England   | Mason Greenwood        | Forward          | Marseille
 L        | England   | Nico O'Reilly          | Defender         | Manchester City Football Club
 L        | England   | Noni Madueke           | Forward          | Arsenal
 L        | England   | Kobbie Mainoo          | Midfielder       | Manchester United
 L        | England   | Ivan Toney             | Forward          | Al-Ahli Jeddah
 L        | England   | Levi Colwill           | Defender         | Chelsea Football Club
 L        | England   | Jarrad Branthwaite     | Defender         | Everton
 L        | England   | Trevoh Chalobah        | Defender         | Chelsea
 L        | England   | Jarell Quansah         | Defender         | Bayer Leverkusen
 L        | England   | Ezri Konsa             | Defender         | Aston Villa
 L        | England   | Marcus Rashford        | Forward          | Barcelona
 L        | England   | Ollie Watkins          | Forward          | Aston Villa
 L        | England   | Jordan Pickford        | Goalkeeper       | Everton
 L        | England   | John Stones            | Defender         | Manchester City
 L        | England   | Aaron Ramsdale         | Goalkeeper       | Newcastle
 L        | England   | Luke Shaw              | Defender         | Manchester United
 L        | England   | Kyle Walker            | Defender         | Burnley
 L        | Ghana     | Antoine Semenyo        | Forward          | Bournemouth
 L        | Ghana     | Mohammed Kudus         | Forward          | Tottenham
 L        | Ghana     | Abdul Fatawu           | Forward          | Leicester City
 L        | Ghana     | Lawrence Ati-Zigi      | GK               | St. Gallen
 L        | Ghana     | Kamaldeen Sulemana     | Forward          | Atalanta
 L        | Ghana     | Ernest Nuamah          | Forward          | Olympique Lyonnais
 L        | Ghana     | Ibrahim Osman          | Forward          | Auxerre
 L        | Ghana     | Mohammed Salisu        | Defender         | Monaco
 L        | Ghana     | Iñaki Williams         | Forward          | Athletic Club
 L        | Ghana     | Joseph Paintsil        | Forward          | Los Angeles Galaxy
 L        | Ghana     | Tariq Lamptey          | Defender         | Fiorentina
 L        | Ghana     | Jonas Adjetey          | Defender         | VfL Wolfsburg
 L        | Ghana     | Osman Bukari           | Forward          | Austin
 L        | Ghana     | Ibrahim Sulemana       | Midfielder       | Atalanta
 L        | Ghana     | Caleb Yirenkyi         | Midfielder       | Fodbold Club Nordsjælland
 L        | Ghana     | Alidu Seidu            | Defender         | Rennes
 L        | Ghana     | Bernard Tekpetey       | Forward          | Fortuna Düsseldorf
 L        | Ghana     | Prince Amoako Junior   | Forward          | Fodbold Club Nordsjælland
 L        | Ghana     | Thomas Partey          | Midfielder       | Villarreal
 L        | Ghana     | Daniel Amartey         | Defender         | Beşiktaş Jimnastik Kulübü
 L        | Ghana     | Jerome Opoku           | Defender         | İstanbul Başakşehir Futbol Kulübü
 L        | Ghana     | Salis Abdul Samed      | Midfielder       | Nice
 L        | Ghana     | Felix Afena-Gyan       | Forward          | Unione Sportiva Cremonese S.p.A.
 L        | Ghana     | Ransford Königsdörffer | Forward          | Hamburger SV
 L        | Ghana     | Kojo Peprah Oppong     | Defender         | Nice
 L        | Ghana     | Alexander Djiku        | Defender         | Spartak Moscow
 L        | Ghana     | Jordan Ayew            | Forward          | Crystal Palace Football Club
 L        | Ghana     | André Ayew             | Forward          | NAC Breda
 L        | Panama    | César Yanis            | FWD              | Wolverhampton
 L        | Panama    | Adalberto Carrasquilla | MID              | Houston Dynamo
 L        | Panama    | Orlando Mosquera       | GK               | Wolverhampton
 L        | Panama    | Jovani Welch           | MID              | Dnipro
 L        | Panama    | Édgar Bárcenas         | FWD              | Real Oviedo
 L        | Panama    | Michael Murillo        | DEF              | Portland Timbers
 L        | Panama    | Aníbal Godoy           | MID              | Nashville SC
 L        | Panama    | Amir Murillo           | Defender         | Beşiktaş
 L        | Panama    | Eric Davis             | DEF              | Ferencváros
 L        | Panama    | Harold Cummings        | DEF              | Morelia
 L        | Panama    | José Fajardo           | FWD              | Saprissa
 L        | Panama    | Fidel Escobar          | DEF              | Santos de Guápiles
 L        | Panama    | Freddy Góndola         | FWD              | Huachipato
 L        | Panama    | Luis Mejía             | GK               | Leganés
 L        | Panama    | Eduardo Guerrero       | Forward          | Futbolniy Klub Dynamo Kyiv
 L        | Panama    | Alberto Quintero       | FWD              | Universitario
 L        | Panama    | José Luis Rodríguez    | Forward          | FC Juarez
 L        | Panama    | Edgardo Fariña         | Defender         | FK Nizhny Novgorod
 L        | Panama    | Ismael Díaz            | Forward          | Leon
 L        | Panama    | Andrés Andrade         | Defender         | Arminia Bielefeld
 L        | Panama    | Eduardo Anderson       | Defender         | Baltika
 L        | Panama    | Alfredo Stephens       | Forward          | Shimizu S-pulse
 L        | Panama    | Jorman Aguilar         | Forward          | Grupo Desportivo Estoril Praia
 L        | Panama    | Abdiel Arroyo          | Forward          | Clube Desportivo Santa Clara
 L        | Panama    | Joseph Jones           | Defender         | FK Kryvbas Kryvyi Rig
 L        | Panama    | Reynaldiño Verley      | Forward          | FC Zorya Lugansk
(114 rows)

---------- 4e: Position balance ----------
 team_code | gk | def | mid | fwd | other 
-----------+----+-----+-----+-----+-------
 ALG       |  0 |   4 |  10 |  11 |     1
 ARG       |  0 |   5 |   8 |  12 |     1
 AUS       |  2 |   6 |   9 |   7 |     2
 AUT       |  0 |  13 |   9 |   4 |     0
 BEL       |  3 |   5 |  10 |   8 |     0
 BRA       |  0 |   2 |   4 |  11 |     9
 CAN       |  1 |   7 |   3 |  11 |     4
 CIV       |  0 |   7 |   7 |  11 |     1
 COL       |  0 |   6 |   6 |  11 |     3
 CPV       |  1 |   5 |   5 |  13 |     2
 CRO       |  2 |   6 |  13 |   5 |     0
 CUW       |  0 |  14 |   3 |   9 |     0
 ECU       |  0 |   8 |   4 |  10 |     4
 EGY       |  0 |   5 |   3 |  11 |     7
 ENG       |  0 |   9 |  10 |   7 |     0
 ESP       |  1 |   6 |  10 |   6 |     3
 FRA       |  0 |   8 |   8 |  10 |     0
 GER       |  0 |   6 |  11 |   9 |     0
 GHA       |  0 |   8 |   4 |  13 |     1
 HAI       |  1 |   9 |   2 |   6 |     8
 IRN       |  3 |   4 |   5 |  10 |     4
 JOR       |  1 |   3 |   6 |   5 |    11
 JPN       |  1 |   6 |   9 |  10 |     0
 KOR       |  0 |   2 |  10 |   7 |     7
 KSA       |  0 |   5 |   2 |   7 |    12
 MAR       |  0 |   9 |   5 |  10 |     2
 MEX       |  0 |   7 |   6 |   5 |     8
 NED       |  1 |  13 |   8 |   4 |     0
 NOR       |  0 |   9 |   6 |  11 |     0
 NZL       |  0 |   6 |   8 |   5 |     7
 PAN       |  0 |   5 |   0 |   7 |    14
 PAR       |  0 |   8 |   5 |   8 |     5
 POR       |  1 |   8 |   8 |   8 |     1
 QAT       |  1 |   8 |   2 |   3 |    12
 RSA       |  0 |   1 |   5 |   8 |    12
 SCO       |  0 |   9 |  11 |   6 |     0
 SEN       |  2 |  10 |   6 |   7 |     1
 SUI       |  1 |   9 |  10 |   6 |     0
 TUN       |  0 |   6 |  10 |   5 |     5
 URU       |  0 |   9 |   8 |   5 |     4
 USA       |  1 |   8 |  10 |   5 |     2
 UZB       |  0 |   4 |   6 |   9 |     7
(42 rows)

========== DONE ==========
