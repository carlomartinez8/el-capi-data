# Azteca Recency Audit + Club Conflict Detection — Results

**Date:** March 2026  
**Source:** [AZTECA_RECENCY_AND_CONFLICTS.md](./AZTECA_RECENCY_AND_CONFLICTS.md) — Task 1 from [AZTECA_RECENCY_AUDIT.md](./AZTECA_RECENCY_AUDIT.md), Task 2 = Step 8.

---

## Summary

**Task 1 (read-only):** 5,840 VERIFIED pairs in dedup_pairs; **5,583 club conflicts** (TM vs APIF disagree on current_club). Top 25 by value use APIF-style names (Barcelona, Real Madrid, etc.). VERIFIED: 0 no-club; ORPHAN: 468 no-club.

**Task 2 (club conflict flagging):** 5,583 warehouse players flagged with `club_conflict_tm_apif`. Curation queue after run: total_needs_curation 12,734; club_conflict 5,583; post_load_dup 16; multi_match_ambiguous 67; missing_fields 2,793; orphan_initial_only 4,282.

---

## Full output

========== TASK 1: Recency Audit (from AZTECA_RECENCY_AUDIT.md) ==========
---------- 1: Club conflicts in VERIFIED (counts) ----------
 total_verified_pairs 
----------------------
                 5840
(1 row)

 club_conflicts 
----------------
           5583
(1 row)

---------- 2: Sample club conflicts (30) ----------
  tm_id  |        tm_name         |   apif_id   |      apif_name       |                  tm_says                  |    apif_says     | date_of_birth |   nationality    
---------+------------------------+-------------+----------------------+-------------------------------------------+------------------+---------------+------------------
 1145504 | Aarón Anselmino        | apif_422780 | A. Anselmino         | Racing Club de Strasbourg Alsace          | Boca Juniors     | 2005-04-29    | Argentina
 254249  | Aaron Appindangoyé     | apif_62018  | A. Appindangoyé      | Sivasspor                                 | Kocaelispor      | 1992-02-20    | Gabon
 987366  | Aaron Bouwman          | apif_453706 | A. Bouwman           | AFC Ajax Amsterdam                        | Ajax             | 2007-08-28    | Netherlands
 724108  | Aaron Ciammaglichella  | apif_343538 | A. Ciammaglichella   | Torino Calcio                             | Torino           | 2005-01-26    | Italy
 624243  | Aaron Donnelly         | apif_327606 | A. Donnelly          | Dundee Football Club                      | Dundee           | 2003-06-08    | Northern Ireland
 284430  | Aarón Escandell        | apif_46673  | Aarón Escandell      | Real Oviedo S.A.D.                        | Oviedo           | 1995-09-27    | Spain
 591949  | Aaron Hickey           | apif_44871  | A. Hickey            | Brentford Football Club                   | Brentford        | 2002-06-10    | Scotland
 251878  | Aarón Martín           | apif_25914  | Aarón Martín         | Genoa Cricket and Football Club           | Genoa            | 1997-04-22    | Spain
 56836   | Aaron Meijers          | apif_37923  | A. Meijers           | Football Club Volendam                    | FC Volendam      | 1987-10-28    | Netherlands
 427568  | Aaron Ramsdale         | apif_20355  | A. Ramsdale          | Newcastle United Football Club            | Newcastle        | 1998-05-14    | England
 50057   | Aaron Ramsey           | apif_1459   | A. Ramsey            | Olympique Gymnaste Club Nice Côte d'Azur  | U.N.A.M. - Pumas | 1990-12-26    | Wales
 646658  | Aaron Ramsey           | apif_278079 | A. Ramsey            | Burnley Football Club                     | Valencia         | 2003-01-21    | England
 730484  | Aaron Zehnter          | apif_323951 | A. Zehnter           | Verein für Leibesübungen Wolfsburg        | VfL Wolfsburg    | 2004-10-31    | Germany
 867082  | Abakar Gadzhiev        | apif_306154 | A. Gadzhiev          | RFK Akhmat Grozny                         | Akhmat           | 2003-12-31    | Russia
 754037  | Abbosbek Fayzullaev    | apif_263676 | A. Fayzullaev        | İstanbul Başakşehir Futbol Kulübü         | CSKA Moscow      | 2003-10-03    | Uzbekistan
 776798  | Abdallah Sima          | apif_277191 | A. Sima              | Racing Club de Lens                       | Lens             | 2001-06-17    | Senegal
 724520  | Abde Ezzalzouli        | apif_181421 | A. Ezzalzouli        | Real Betis Balompié S.A.D.                | Real Betis       | 2001-12-17    | Morocco
 718034  | Abde Rebbach           | apif_183751 | A. Rebbach           | Deportivo Alavés S. A. D.                 | Alaves           | 1998-08-11    | Algeria
 559979  | Abdel Abqar            | apif_46813  | A. Abqar             | Getafe Club de Fútbol S. A. D. Team Dubai | Getafe           | 1999-03-10    | Morocco
 1134251 | Abdelhamid Ait Boudlal | apif_417830 | A. Ait Boudlal       | Stade Rennais Football Club               | Rennes           | 2006-04-16    | Morocco
 340394  | Abdelhamid Sabiri      | apif_19053  | A. Sabiri            | Associazione Calcio Fiorentina            | Fiorentina       | 1996-11-28    | Morocco
 592400  | Abdelkahar Kadri       | apif_129867 | A. Kadri             | Koninklijke Atletiek Associatie Gent      | Gent             | 2000-06-24    | Algeria
 1086915 | Abdelraffie Benzzine   | apif_480311 | Abdelraffie Benzzine | Sportclub Telstar                         | Telstar          | 2006-04-04    | Netherlands
 1429895 | Abderrahmane Soumare   | apif_525383 | A. Soumare           | Futebol Clube de Alverca                  | Alverca          | 2006-11-11    | Mauritania
 177452  | Abdón Prats            | apif_46751  | Abdón Prats          | Real Club Deportivo Mallorca S.A.D.       | Mallorca         | 1992-12-07    | Spain
 1133732 | Abdou Aziz Fall        | apif_417860 | A. Fall              | Fenerbahçe Spor Kulübü                    | Fenerbahçe       | 2007-02-20    | Senegal
 416386  | Abdou Harroui          | apif_37437  | A. Harroui           | Verona Hellas Football Club               | Hellas Verona    | 1998-01-13    | Morocco
 1160184 | Abdoul Ayinde          | apif_436990 | A. Ayindé            | Koninklijke Atletiek Associatie Gent      | Gent             | 2005-07-17    | Burkina Faso
 1176433 | Abdoul Kader Ouattara  | apif_454418 | Abdoul Ouattara      | Cercle Brugge Koninklijke Sportvereniging | Cercle Brugge    | 2005-05-26    | Burkina Faso
 1284784 | Abdoul Karim Traoré    | apif_483115 | A. Traoré            | Oud-Heverlee Leuven                       | OH Leuven        | 2007-01-12    | Guinea
(30 rows)

---------- 3: High-value club conflicts (30) ----------
        tm_name        |                  tm_says                   |      apif_says      | tm_market_value 
-----------------------+--------------------------------------------+---------------------+-----------------
 Kylian Mbappé         | Real Madrid Club de Fútbol                 | Real Madrid         |       200000000
 Erling Haaland        | Manchester City Football Club              | Manchester City     |       200000000
 Lamine Yamal          | Futbol Club Barcelona                      | Barcelona           |       200000000
 Jude Bellingham       | Real Madrid Club de Fútbol                 | Real Madrid         |       160000000
 Vinicius Junior       | Real Madrid Club de Fútbol                 | Real Madrid         |       150000000
 Pedri                 | Futbol Club Barcelona                      | Barcelona           |       140000000
 Michael Olise         | FC Bayern München                          | Bayern München      |       130000000
 Jamal Musiala         | FC Bayern München                          | Bayern München      |       130000000
 Bukayo Saka           | Arsenal Football Club                      | Arsenal             |       120000000
 Declan Rice           | Arsenal Football Club                      | Arsenal             |       120000000
 Federico Valverde     | Real Madrid Club de Fútbol                 | Real Madrid         |       120000000
 Cole Palmer           | Chelsea Football Club                      | Chelsea             |       110000000
 Moisés Caicedo        | Chelsea Football Club                      | Chelsea             |       110000000
 Florian Wirtz         | Liverpool Football Club                    | Liverpool           |       110000000
 Vitinha               | Paris Saint-Germain Football Club          | Paris Saint Germain |       110000000
 João Neves            | Paris Saint-Germain Football Club          | Paris Saint Germain |       110000000
 Ousmane Dembélé       | Paris Saint-Germain Football Club          | Paris Saint Germain |       100000000
 Alexander Isak        | Liverpool Football Club                    | Liverpool           |       100000000
 Dominik Szoboszlai    | Liverpool Football Club                    | Liverpool           |       100000000
 Julián Alvarez        | Club Atlético de Madrid S.A.D.             | Atletico Madrid     |       100000000
 William Saliba        | Arsenal Football Club                      | Arsenal             |        90000000
 Khvicha Kvaratskhelia | Paris Saint-Germain Football Club          | Paris Saint Germain |        90000000
 Désiré Doué           | Paris Saint-Germain Football Club          | Paris Saint Germain |        90000000
 Hugo Ekitiké          | Liverpool Football Club                    | Liverpool           |        90000000
 Arda Güler            | Real Madrid Club de Fútbol                 | Real Madrid         |        90000000
 Enzo Fernández        | Chelsea Football Club                      | Chelsea             |        90000000
 Ryan Gravenberch      | Liverpool Football Club                    | Liverpool           |        90000000
 Lautaro Martínez      | Football Club Internazionale Milano S.p.A. | Inter               |        85000000
 Raphinha              | Futbol Club Barcelona                      | Barcelona           |        80000000
 Martín Zubimendi      | Arsenal Football Club                      | Arsenal             |        80000000
(30 rows)

---------- 4: Top 25 players by value — current_club in warehouse ----------
      known_as      |    current_club     | estimated_value_eur | data_confidence |        source_records        
--------------------+---------------------+---------------------+-----------------+------------------------------
 Erling Haaland     | Manchester City     |           200000000 | high            | TM:418560 + APIF:apif_1100
 Kylian Mbappé      | Real Madrid         |           200000000 | high            | TM:342229 + APIF:apif_278
 Lamine Yamal       | Barcelona           |           200000000 | high            | TM:937958 + APIF:apif_386828
 Jude Bellingham    | Real Madrid         |           160000000 | high            | TM:581678 + APIF:apif_129718
 Vinicius Junior    | Real Madrid         |           150000000 | high            | TM:371998 + APIF:apif_762
 Pedri              | Barcelona           |           140000000 | high            | TM:683840 + APIF:apif_133609
 Jamal Musiala      | Bayern München      |           130000000 | high            | TM:580195 + APIF:apif_181812
 Michael Olise      | Bayern München      |           130000000 | high            | TM:566723 + APIF:apif_19617
 Declan Rice        | Arsenal             |           120000000 | high            | TM:357662 + APIF:apif_2937
 Bukayo Saka        | Arsenal             |           120000000 | high            | TM:433177 + APIF:apif_1460
 Federico Valverde  | Real Madrid         |           120000000 | high            | TM:369081 + APIF:apif_756
 Rodrygo            | Real Madrid         |           120000000 | high            | 
 Rodri              | Man City            |           120000000 | high            | 
 João Neves         | Paris Saint Germain |           110000000 | high            | TM:670681 + APIF:apif_335051
 Cole Palmer        | Chelsea             |           110000000 | high            | TM:568177 + APIF:apif_152982
 Moisés Caicedo     | Chelsea             |           110000000 | high            | TM:687626 + APIF:apif_116117
 Vitinha            | Paris Saint Germain |           110000000 | high            | TM:487469 + APIF:apif_128384
 Florian Wirtz      | Liverpool           |           110000000 | high            | TM:598577 + APIF:apif_203224
 Ousmane Dembélé    | Paris Saint Germain |           100000000 | high            | TM:288230 + APIF:apif_153
 Julián Alvarez     | Atletico Madrid     |           100000000 | high            | TM:576024 + APIF:apif_6009
 Dominik Szoboszlai | Liverpool           |           100000000 | high            | TM:451276 + APIF:apif_1096
 Alexander Isak     | Liverpool           |           100000000 | high            | TM:349066 + APIF:apif_2864
 Pedri              | Barcelona           |           100000000 | high            | 
 Hugo Ekitiké       | Liverpool           |            90000000 | high            | TM:709726 + APIF:apif_174565
 Ryan Gravenberch   | Liverpool           |            90000000 | high            | TM:478573 + APIF:apif_542
(25 rows)

---------- 5: VERIFIED — which source club did we use? (top 25 by value) ----------
        tm_name        |              tm_club              |      apif_club      |    staging_chose    | tm_market_value 
-----------------------+-----------------------------------+---------------------+---------------------+-----------------
 Kylian Mbappé         | Real Madrid Club de Fútbol        | Real Madrid         | Real Madrid         |       200000000
 Erling Haaland        | Manchester City Football Club     | Manchester City     | Manchester City     |       200000000
 Lamine Yamal          | Futbol Club Barcelona             | Barcelona           | Barcelona           |       200000000
 Jude Bellingham       | Real Madrid Club de Fútbol        | Real Madrid         | Real Madrid         |       160000000
 Vinicius Junior       | Real Madrid Club de Fútbol        | Real Madrid         | Real Madrid         |       150000000
 Pedri                 | Futbol Club Barcelona             | Barcelona           | Barcelona           |       140000000
 Jamal Musiala         | FC Bayern München                 | Bayern München      | Bayern München      |       130000000
 Michael Olise         | FC Bayern München                 | Bayern München      | Bayern München      |       130000000
 Federico Valverde     | Real Madrid Club de Fútbol        | Real Madrid         | Real Madrid         |       120000000
 Declan Rice           | Arsenal Football Club             | Arsenal             | Arsenal             |       120000000
 Bukayo Saka           | Arsenal Football Club             | Arsenal             | Arsenal             |       120000000
 Vitinha               | Paris Saint-Germain Football Club | Paris Saint Germain | Paris Saint Germain |       110000000
 Florian Wirtz         | Liverpool Football Club           | Liverpool           | Liverpool           |       110000000
 Moisés Caicedo        | Chelsea Football Club             | Chelsea             | Chelsea             |       110000000
 João Neves            | Paris Saint-Germain Football Club | Paris Saint Germain | Paris Saint Germain |       110000000
 Cole Palmer           | Chelsea Football Club             | Chelsea             | Chelsea             |       110000000
 Dominik Szoboszlai    | Liverpool Football Club           | Liverpool           | Liverpool           |       100000000
 Ousmane Dembélé       | Paris Saint-Germain Football Club | Paris Saint Germain | Paris Saint Germain |       100000000
 Alexander Isak        | Liverpool Football Club           | Liverpool           | Liverpool           |       100000000
 Julián Alvarez        | Club Atlético de Madrid S.A.D.    | Atletico Madrid     | Atletico Madrid     |       100000000
 Hugo Ekitiké          | Liverpool Football Club           | Liverpool           | Liverpool           |        90000000
 Khvicha Kvaratskhelia | Paris Saint-Germain Football Club | Paris Saint Germain | Paris Saint Germain |        90000000
 Ryan Gravenberch      | Liverpool Football Club           | Liverpool           | Liverpool           |        90000000
 William Saliba        | Arsenal Football Club             | Arsenal             | Arsenal             |        90000000
 Arda Güler            | Real Madrid Club de Fútbol        | Real Madrid         | Real Madrid         |        90000000
(25 rows)

---------- 6: Profiles with NO club (by confidence) ----------
 data_confidence | no_club | total 
-----------------+---------+-------
 VERIFIED        |       0 |  5840
 PROJECTED       |      15 | 30515
 PARTIAL         |       0 |   400
 ORPHAN          |     468 |  6692
(4 rows)

========== TASK 2: Club Conflict Detection (Step 8) ==========
---------- 8a: Build _club_conflicts (TM vs APIF disagree) ----------
psql:../run_recency_and_conflicts.sql:83: NOTICE:  table "_club_conflicts" does not exist, skipping
DROP TABLE
SELECT 5583
---------- 8b: Club conflicts count ----------
 club_conflicts 
----------------
           5583
(1 row)

---------- 8c: Top conflicts by market value (30) ----------
 tm_id  |        tm_name        |   apif_id   |    apif_name     |                  tm_says                   |      apif_says      | tm_market_value 
--------+-----------------------+-------------+------------------+--------------------------------------------+---------------------+-----------------
 342229 | Kylian Mbappé         | apif_278    | Kylian Mbappé    | Real Madrid Club de Fútbol                 | Real Madrid         |       200000000
 418560 | Erling Haaland        | apif_1100   | E. Haaland       | Manchester City Football Club              | Manchester City     |       200000000
 937958 | Lamine Yamal          | apif_386828 | Lamine Yamal     | Futbol Club Barcelona                      | Barcelona           |       200000000
 581678 | Jude Bellingham       | apif_129718 | J. Bellingham    | Real Madrid Club de Fútbol                 | Real Madrid         |       160000000
 371998 | Vinicius Junior       | apif_762    | Vinícius Júnior  | Real Madrid Club de Fútbol                 | Real Madrid         |       150000000
 683840 | Pedri                 | apif_133609 | Pedri            | Futbol Club Barcelona                      | Barcelona           |       140000000
 566723 | Michael Olise         | apif_19617  | M. Olise         | FC Bayern München                          | Bayern München      |       130000000
 580195 | Jamal Musiala         | apif_181812 | J. Musiala       | FC Bayern München                          | Bayern München      |       130000000
 433177 | Bukayo Saka           | apif_1460   | B. Saka          | Arsenal Football Club                      | Arsenal             |       120000000
 357662 | Declan Rice           | apif_2937   | D. Rice          | Arsenal Football Club                      | Arsenal             |       120000000
 369081 | Federico Valverde     | apif_756    | F. Valverde      | Real Madrid Club de Fútbol                 | Real Madrid         |       120000000
 568177 | Cole Palmer           | apif_152982 | C. Palmer        | Chelsea Football Club                      | Chelsea             |       110000000
 687626 | Moisés Caicedo        | apif_116117 | M. Caicedo       | Chelsea Football Club                      | Chelsea             |       110000000
 598577 | Florian Wirtz         | apif_203224 | F. Wirtz         | Liverpool Football Club                    | Liverpool           |       110000000
 487469 | Vitinha               | apif_128384 | Vitinha          | Paris Saint-Germain Football Club          | Paris Saint Germain |       110000000
 670681 | João Neves            | apif_335051 | João Neves       | Paris Saint-Germain Football Club          | Paris Saint Germain |       110000000
 288230 | Ousmane Dembélé       | apif_153    | O. Dembélé       | Paris Saint-Germain Football Club          | Paris Saint Germain |       100000000
 349066 | Alexander Isak        | apif_2864   | A. Isak          | Liverpool Football Club                    | Liverpool           |       100000000
 451276 | Dominik Szoboszlai    | apif_1096   | D. Szoboszlai    | Liverpool Football Club                    | Liverpool           |       100000000
 576024 | Julián Alvarez        | apif_6009   | J. Álvarez       | Club Atlético de Madrid S.A.D.             | Atletico Madrid     |       100000000
 495666 | William Saliba        | apif_22090  | W. Saliba        | Arsenal Football Club                      | Arsenal             |        90000000
 502670 | Khvicha Kvaratskhelia | apif_483    | K. Kvaratskhelia | Paris Saint-Germain Football Club          | Paris Saint Germain |        90000000
 914562 | Désiré Doué           | apif_343027 | D. Doué          | Paris Saint-Germain Football Club          | Paris Saint Germain |        90000000
 709726 | Hugo Ekitiké          | apif_174565 | H. Ekitike       | Liverpool Football Club                    | Liverpool           |        90000000
 861410 | Arda Güler            | apif_291964 | A. Güler         | Real Madrid Club de Fútbol                 | Real Madrid         |        90000000
 648195 | Enzo Fernández        | apif_5996   | E. Fernández     | Chelsea Football Club                      | Chelsea             |        90000000
 478573 | Ryan Gravenberch      | apif_542    | R. Gravenberch   | Liverpool Football Club                    | Liverpool           |        90000000
 406625 | Lautaro Martínez      | apif_217    | Lautaro Martínez | Football Club Internazionale Milano S.p.A. | Inter               |        85000000
 411295 | Raphinha              | apif_1496   | Raphinha         | Futbol Club Barcelona                      | Barcelona           |        80000000
 423440 | Martín Zubimendi      | apif_47315  | Martín Zubimendi | Arsenal Football Club                      | Arsenal             |        80000000
(30 rows)

---------- 8d: Flag warehouse players for curation ----------
UPDATE 5583
---------- 8e: Flagged with club_conflict ----------
 flagged_club_conflict 
-----------------------
                  5583
(1 row)

---------- 8f: Curation queue breakdown ----------
 total_needs_curation | club_conflict | post_load_dup | multi_match_ambiguous | missing_fields | orphan_initial_only 
----------------------+---------------+---------------+-----------------------+----------------+---------------------
                12734 |          5583 |            16 |                    67 |           2793 |                4282
(1 row)

========== DONE ==========
