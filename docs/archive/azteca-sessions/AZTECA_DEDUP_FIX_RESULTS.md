# Azteca Dedup Fix — Results

**Date:** March 2026  
**Script:** run_dedup_fix.sql ([AZTECA_DEDUP_FIX.md](./AZTECA_DEDUP_FIX.md))

---

## 7g passed — safe to proceed

**Duplicate integrity check (7g) returned 0 rows.** Staging table is clean.

| Metric | Value |
|--------|--------|
| Ambiguous pairs quarantined | 50 → `dedup_pairs_ambiguous` |
| Clean Tier 2 pairs | 5,840 |
| 3b.5 (ID in multiple pairs) | 0 rows |
| Total profiles | 43,447 |
| VERIFIED | 5,840 (13.4%) |
| Records flagged `multi_match_ambiguous` | 67 |
| Sample-100 spot check | McNeil, Neves, Dunk, Asensio, Aït-Nouri all VERIFIED Tier 2 |

---

## Full output

========== Step 3b.1: Create dedup_pairs_ambiguous ==========
psql:../run_dedup_fix.sql:3: NOTICE:  table "dedup_pairs_ambiguous" does not exist, skipping
DROP TABLE
SELECT 50
========== Step 3b.2: Ambiguous pairs quarantined ==========
 ambiguous_pairs_quarantined 
-----------------------------
                          50
(1 row)

========== Step 3b.3: Ambiguous pairs (sample) ==========
  tm_id  |         tm_name         |   apif_id   |    apif_name     | date_of_birth | nationality 
---------+-------------------------+-------------+------------------+---------------+-------------
 1196804 | Anass Bouziane          | apif_443587 | W. Bouziane      | 2006-12-22    | Netherlands
 1196804 | Anass Bouziane          | apif_489932 | Anass Bouziane   | 2006-12-22    | Netherlands
 1209519 | Victor Ntino-Emo Gidado | apif_451178 | V. Gidado        | 2004-07-14    | Nigeria
 1209519 | Victor Ntino-Emo Gidado | apif_554140 | V. Gidado        | 2004-07-14    | Nigeria
 158863  | Iñigo Martínez          | apif_2670   | Íñigo Martínez   | 1991-05-17    | Spain
 199527  | Jacob Murphy            | apif_19163  | J. Murphy        | 1995-02-24    | England
 199528  | Josh Murphy             | apif_19163  | J. Murphy        | 1995-02-24    | England
 217886  | Óscar Romero            | apif_2515   | Ó. Romero        | 1992-07-04    | Paraguay
 217886  | Óscar Romero            | apif_2521   | Á. Romero        | 1992-07-04    | Paraguay
 236748  | Luís Aurélio            | apif_41119  | João Aurélio     | 1988-08-17    | Portugal
 244260  | Robby McCrorie          | apif_45177  | R. McCrorie      | 1998-03-18    | Scotland
 255450  | Aleksey Miranchuk       | apif_484    | A. Miranchuk     | 1995-10-17    | Russia
 255450  | Aleksey Miranchuk       | apif_485    | A. Miranchuk     | 1995-10-17    | Russia
 255451  | Anton Miranchuk         | apif_484    | A. Miranchuk     | 1995-10-17    | Russia
 255451  | Anton Miranchuk         | apif_485    | A. Miranchuk     | 1995-10-17    | Russia
 255473  | Samuel Gustafson        | apif_30931  | Samuel Gustafson | 1995-01-11    | Sweden
 255474  | Simon Gustafson         | apif_30931  | Samuel Gustafson | 1995-01-11    | Sweden
 277782  | Chris Cadden            | apif_44921  | C. Cadden        | 1996-09-19    | Scotland
 277782  | Chris Cadden            | apif_45162  | N. Cadden        | 1996-09-19    | Scotland
 291177  | Nicky Cadden            | apif_44921  | C. Cadden        | 1996-09-19    | Scotland
 291177  | Nicky Cadden            | apif_45162  | N. Cadden        | 1996-09-19    | Scotland
 293746  | Ross McCrorie           | apif_45177  | R. McCrorie      | 1998-03-18    | Scotland
 298976  | Borja Mayoral           | apif_47472  | Borja Mayoral    | 1997-04-05    | Spain
 327251  | Ridle Baku              | apif_25917  | R. Baku          | 1998-04-08    | Germany
 336974  | Makana Baku             | apif_25917  | R. Baku          | 1998-04-08    | Germany
 355629  | David Mayoral           | apif_47472  | Borja Mayoral    | 1997-04-05    | Spain
 420213  | Quinten Timber          | apif_38746  | J. Timber        | 2001-06-17    | Netherlands
 420213  | Quinten Timber          | apif_38747  | Q. Timber        | 2001-06-17    | Netherlands
 420243  | Jurriën Timber          | apif_38746  | J. Timber        | 2001-06-17    | Netherlands
 420243  | Jurriën Timber          | apif_38747  | Q. Timber        | 2001-06-17    | Netherlands
 466783  | Arnau Tenas             | apif_162473 | Arnau Tenas      | 2001-05-30    | Spain
 495963  | Richie Musaba           | apif_37380  | A. Musaba        | 2000-12-06    | Netherlands
 511401  | Anthony Musaba          | apif_37380  | A. Musaba        | 2000-12-06    | Netherlands
 516749  | Vladislav Shitov        | apif_271664 | V. Shitov        | 2003-05-07    | Russia
 516750  | Vitaliy Shitov          | apif_271664 | V. Shitov        | 2003-05-07    | Russia
 531065  | Oussama El Azzouzi      | apif_319919 | O. El Azzouzi    | 2001-05-29    | Morocco
 593774  | Anouar El Azzouzi       | apif_319919 | O. El Azzouzi    | 2001-05-29    | Morocco
 628472  | Marc Tenas              | apif_162473 | Arnau Tenas      | 2001-05-30    | Spain
 646739  | Ángel Alarcón           | apif_294797 | Ángel Alarcón    | 2004-05-15    | Spain
 646739  | Ángel Alarcón           | apif_386827 | Ángel Alarcón    | 2004-05-15    | Spain
 66117   | Ángel Martínez          | apif_2670   | Íñigo Martínez   | 1991-05-17    | Spain
 698678  | Hugo Bueno              | apif_280687 | Hugo Bueno       | 2002-09-18    | Spain
 742063  | Pedrinho                | apif_182072 | Pedrinho         | 1996-12-19    | Brazil
 742063  | Pedrinho                | apif_550861 | Pedrinho         | 1996-12-19    | Brazil
 746642  | Isaac James             | apif_402225 | I. James         | 2004-08-28    | Nigeria
 746642  | Isaac James             | apif_458508 | I. James         | 2004-08-28    | Nigeria
 84711   | João Aurélio            | apif_41119  | João Aurélio     | 1988-08-17    | Portugal
 854079  | Guille Bueno            | apif_280687 | Hugo Bueno       | 2002-09-18    | Spain
 990008  | Wassim Bouziane         | apif_443587 | W. Bouziane      | 2006-12-22    | Netherlands
 990008  | Wassim Bouziane         | apif_489932 | Anass Bouziane   | 2006-12-22    | Netherlands
(50 rows)

========== Step 3b.4: Remove ambiguous from dedup_pairs ==========
DELETE 50
========== Step 3b.5: Confirm no ID in multiple pairs (MUST be 0 rows) ==========
 issue | tm_id | count 
-------+-------+-------
(0 rows)

========== Step 3b.6: Clean pair count ==========
 clean_pairs 
-------------
        5840
(1 row)

========== Truncate staging, restart sequence ==========
TRUNCATE TABLE
ALTER SEQUENCE
========== Step 4: Insert merged (Tier 2) ==========
INSERT 0 5840
========== Step 5: Insert unmatched TM ==========
INSERT 0 28530
========== Step 6: Insert unmatched APIF ==========
INSERT 0 9077
========== Step 6b.1–6b.2: Flag ambiguous IDs ==========
UPDATE 37
UPDATE 30
========== Step 6b.3: Records flagged multi_match ==========
 records_flagged_multi_match 
-----------------------------
                          67
(1 row)

========== Step 7a: Total profiles ==========
 total_profiles 
----------------
          43447
(1 row)

========== Step 7b: Input vs output ==========
 input_records | output_profiles | merged_pairs | records_deduped 
---------------+-----------------+--------------+-----------------
         49287 |           43447 |         5840 |            5840
(1 row)

========== Step 7c: Confidence breakdown ==========
 data_confidence | count | pct  | flagged_for_curation 
-----------------+-------+------+----------------------
 VERIFIED        |  5840 | 13.4 |                    0
 PROJECTED       | 30515 | 70.2 |                   50
 PARTIAL         |   400 |  0.9 |                  400
 ORPHAN          |  6692 | 15.4 |                 6692
(4 rows)

========== Step 7d: Match tier breakdown ==========
   match_tier    | count 
-----------------+-------
 Tier 4 (unique) | 37607
 Tier 2          |  5840
(2 rows)

========== Step 7e: Curation reasons ==========
        reason         | count 
-----------------------+-------
 initial_only          |  5799
 missing_dob           |  2442
 missing_nationality   |  2275
 multi_match_ambiguous |    67
(4 rows)

========== Step 7f: Curation queue size ==========
 total_needing_curation | pct  
------------------------+------
                   7142 | 16.4
(1 row)

========== Step 7g: KILL SWITCH — Duplicate integrity (MUST be 0 rows) ==========
 issue | id | occurrences 
-------+----+-------------
(0 rows)

========== Step 7h: Sample VERIFIED ==========
 profile_id |  tm_id  |   apif_id   |      display_name      | date_of_birth |   nationality    |   current_club   
------------+---------+-------------+------------------------+---------------+------------------+------------------
       5672 | 1145504 | apif_422780 | Aarón Anselmino        | 2005-04-29    | Argentina        | Boca Juniors
       1273 | 254249  | apif_62018  | Aaron Appindangoyé     | 1992-02-20    | Gabon            | Kocaelispor
       5307 | 987366  | apif_453706 | Aaron Bouwman          | 2007-08-28    | Netherlands      | Ajax
       4368 | 724108  | apif_343538 | Aaron Ciammaglichella  | 2005-01-26    | Italy            | Torino
       3777 | 624243  | apif_327606 | Aaron Donnelly         | 2003-06-08    | Northern Ireland | Dundee
       1494 | 284430  | apif_46673  | Aarón Escandell        | 1995-09-27    | Spain            | Oviedo
       3584 | 591949  | apif_44871  | Aaron Hickey           | 2002-06-10    | Scotland         | Brentford
       1264 | 251878  | apif_25914  | Aarón Martín           | 1997-04-22    | Spain            | Genoa
        172 | 56836   | apif_37923  | Aaron Meijers          | 1987-10-28    | Netherlands      | FC Volendam
       2593 | 427568  | apif_20355  | Aaron Ramsdale         | 1998-05-14    | England          | Newcastle
        132 | 50057   | apif_1459   | Aaron Ramsey           | 1990-12-26    | Wales            | U.N.A.M. - Pumas
       1857 | 646658  | apif_278079 | Aaron Ramsey           | 2003-01-21    | England          | Valencia
       4406 | 730484  | apif_323951 | Aaron Zehnter          | 2004-10-31    | Germany          | VfL Wolfsburg
       4845 | 867082  | apif_306154 | Abakar Gadzhiev        | 2003-12-31    | Russia           | Akhmat
       4526 | 754037  | apif_263676 | Abbosbek Fayzullaev    | 2003-10-03    | Uzbekistan       | CSKA Moscow
       4555 | 776798  | apif_277191 | Abdallah Sima          | 2001-06-17    | Senegal          | Lens
       4370 | 724520  | apif_181421 | Abde Ezzalzouli        | 2001-12-17    | Morocco          | Real Betis
       4330 | 718034  | apif_183751 | Abde Rebbach           | 1998-08-11    | Algeria          | Alaves
       3369 | 559979  | apif_46813  | Abdel Abqar            | 1999-03-10    | Morocco          | Getafe
       5658 | 1134251 | apif_417830 | Abdelhamid Ait Boudlal | 2006-04-16    | Morocco          | Rennes
       1886 | 340394  | apif_19053  | Abdelhamid Sabiri      | 1996-11-28    | Morocco          | Fiorentina
       3588 | 592400  | apif_129867 | Abdelkahar Kadri       | 2000-06-24    | Algeria          | Gent
       5579 | 1086915 | apif_480311 | Abdelraffie Benzzine   | 2006-04-04    | Netherlands      | Telstar
       5837 | 1429895 | apif_525383 | Abderrahmane Soumare   | 2006-11-11    | Mauritania       | Alverca
        767 | 177452  | apif_46751  | Abdón Prats            | 1992-12-07    | Spain            | Mallorca
(25 rows)

========== Step 7i: Sample ORPHAN ==========
 profile_id |   apif_id   |      display_name      | date_of_birth |      nationality       |                curation_reason                 
------------+-------------+------------------------+---------------+------------------------+------------------------------------------------
      34705 | apif_437483 | A.  Bamba              | 2004-10-08    | Côte d'Ivoire          | initial_only
      38017 | apif_543038 | A. A. Asad Hajabi      |               | Jordan                 | initial_only; missing_dob
      39480 | apif_552399 | A. A. Saavedra Nevarez |               |                        | initial_only; missing_dob; missing_nationality
      37856 | apif_342740 | A. Abada               |               | Algeria                | initial_only; missing_dob
      35485 | apif_576170 | A. Abdoulraouf         |               |                        | initial_only; missing_dob; missing_nationality
      35871 | apif_576187 | A. Abdu                |               |                        | initial_only; missing_dob; missing_nationality
      37957 | apif_73418  | A. Abdullayev          |               | Uzbekistan             | initial_only; missing_dob
      37711 | apif_532925 | A. Abdullayev          |               | Iran                   | initial_only; missing_dob
      37726 | apif_29852  | A. Aghasi              |               | Iran                   | initial_only; missing_dob
      40111 | apif_6330   | A. Aguerre             | 1990-08-23    | Argentina              | initial_only
      42989 | apif_141109 | A. Agyeman             | 2000-03-15    | Italy                  | initial_only
      38181 | apif_362145 | A. Ahmed               | 2000-10-10    | Canada                 | initial_only
      42727 | apif_1949   | A. Ahmedhodžić         | 1999-03-26    | Bosnia and Herzegovina | initial_only
      43064 | apif_427893 | A. Akaev               | 2004-08-01    | Russia                 | initial_only
      35628 | apif_578902 | A. Al Anazi            |               |                        | initial_only; missing_dob; missing_nationality
      35658 | apif_576185 | A. Al Dakheel          |               |                        | initial_only; missing_dob; missing_nationality
      36984 | apif_323449 | A. Al Dakhil           | 2002-03-06    | Belgium                | initial_only
      35718 | apif_576294 | A. Al Harbi            |               |                        | initial_only; missing_dob; missing_nationality
      35569 | apif_531454 | A. Al Harbi            |               |                        | initial_only; missing_dob; missing_nationality
      35841 | apif_542712 | A. Al Hassan           |               |                        | initial_only; missing_dob; missing_nationality
      37964 | apif_542542 | A. Al Hussain          |               | Qatar                  | initial_only; missing_dob
      35629 | apif_576194 | A. Al Jouei            |               |                        | initial_only; missing_dob; missing_nationality
      35742 | apif_576195 | A. Al Khaibari         |               |                        | initial_only; missing_dob; missing_nationality
      35687 | apif_576297 | A. Al Khaibary         |               |                        | initial_only; missing_dob; missing_nationality
      35909 | apif_630624 | A. Al Khanani          |               |                        | initial_only; missing_dob; missing_nationality
(25 rows)

========== Step 7j: Table sizes ==========
 staging_table_size | dedup_pairs_size 
--------------------+------------------
 18 MB              | 2688 kB
(1 row)

========== Step 7k: Sample-100 spot check ==========
 profile_id | tm_id  |   apif_id   |  display_name   | data_confidence | match_tier 
------------+--------+-------------+-----------------+-----------------+------------
       3545 | 584769 | apif_18929  | Dwight McNeil   | VERIFIED        | Tier 2
       4086 | 670681 | apif_335051 | João Neves      | VERIFIED        | Tier 2
        612 | 148153 | apif_18963  | Lewis Dunk      | VERIFIED        | Tier 2
       1602 | 296622 | apif_746    | Marco Asensio   | VERIFIED        | Tier 2
       3496 | 578391 | apif_21138  | Rayan Aït-Nouri | VERIFIED        | Tier 2
(5 rows)

========== DONE ==========
