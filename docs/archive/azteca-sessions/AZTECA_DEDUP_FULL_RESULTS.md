# Azteca Dedup Pipeline — Full Run Results

**Date:** March 2026  
**Script:** run_dedup_pipeline.sql (AZTECA_DEDUP_EXECUTE.md)

---

## STOP — 7g kill switch triggered

**Duplicate integrity check (7g) returned rows.** Per AZTECA_DEDUP_EXECUTE.md: do not build on this output.

- **Cause:** Some TM and APIF IDs appear in **more than one** Tier 2 pair (same person matched to multiple partners). Step 3 "TM/APIF in multiple pairs" already showed 13 TM IDs and 7 APIF IDs (limit 20). Inserting one row per pair then produced duplicate `tm_id` / `apif_id` in `profile_players_staging`.
- **7g:** 13 duplicate `tm_id`s and 7+ duplicate `apif_id`s (output truncated at 20).
- **Action:** Resolve multi-pair IDs (e.g. pick one pair per ID or flag for manual review) before re-running; then re-run and confirm 7g returns 0 rows.

---

## Run metrics (for reference once 7g is fixed)

| Metric | Value |
|--------|--------|
| Input records (pipeline_players) | 49,287 |
| Tier 2 pairs (dedup_pairs) | 5,890 |
| Output profiles (staging) | 43,430 |
| Records deduped | 5,857 |
| VERIFIED | 5,890 (13.6%) |
| PROJECTED | 30,465 (70.1%) |
| PARTIAL | 400 (0.9%) |
| ORPHAN | 6,675 (15.4%) |
| Needs curation | 7,075 (16.3%) |

Sample-100 spot check (7k): Dwight McNeil, João Neves, Lewis Dunk, Marco Asensio, Rayan Aït-Nouri all VERIFIED Tier 2 as expected.

---

## Full output (all steps)

========== Step 1: Create profile_players_staging ==========
psql:../run_dedup_pipeline.sql:3: NOTICE:  table "profile_players_staging" does not exist, skipping
DROP TABLE
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
========== Step 2: Create strip_accents ==========
CREATE FUNCTION
========== Step 3: Create dedup_pairs (Tier 2) ==========
psql:../run_dedup_pipeline.sql:49: NOTICE:  table "dedup_pairs" does not exist, skipping
DROP TABLE
SELECT 5890
========== Step 3 report: total_tier2_pairs ==========
 total_tier2_pairs 
-------------------
              5890
(1 row)

========== Step 3 check: TM/APIF in multiple pairs ==========
         issue          |    tm_id    | count 
------------------------+-------------+-------
 TM in multiple pairs   | 420243      |     2
 TM in multiple pairs   | 646739      |     2
 TM in multiple pairs   | 255451      |     2
 TM in multiple pairs   | 291177      |     2
 TM in multiple pairs   | 990008      |     2
 TM in multiple pairs   | 255450      |     2
 TM in multiple pairs   | 420213      |     2
 TM in multiple pairs   | 217886      |     2
 TM in multiple pairs   | 742063      |     2
 TM in multiple pairs   | 746642      |     2
 TM in multiple pairs   | 277782      |     2
 TM in multiple pairs   | 1196804     |     2
 TM in multiple pairs   | 1209519     |     2
 APIF in multiple pairs | apif_319919 |     2
 APIF in multiple pairs | apif_2670   |     2
 APIF in multiple pairs | apif_271664 |     2
 APIF in multiple pairs | apif_44921  |     2
 APIF in multiple pairs | apif_37380  |     2
 APIF in multiple pairs | apif_485    |     2
 APIF in multiple pairs | apif_19163  |     2
(20 rows)

========== Step 4: Insert merged (Tier 2) ==========
INSERT 0 5890
========== Step 5: Insert unmatched TM ==========
INSERT 0 28493
========== Step 6: Insert unmatched APIF ==========
INSERT 0 9047
========== Step 7a: Total profiles ==========
 total_profiles 
----------------
          43430
(1 row)

========== Step 7b: Input vs output ==========
 input_records | output_profiles | merged_pairs | records_deduped 
---------------+-----------------+--------------+-----------------
         49287 |           43430 |         5890 |            5857
(1 row)

========== Step 7c: Confidence breakdown ==========
 data_confidence | count | pct  | flagged_for_curation 
-----------------+-------+------+----------------------
 VERIFIED        |  5890 | 13.6 |                    0
 PROJECTED       | 30465 | 70.1 |                    0
 PARTIAL         |   400 |  0.9 |                  400
 ORPHAN          |  6675 | 15.4 |                 6675
(4 rows)

========== Step 7d: Match tier breakdown ==========
   match_tier    | count 
-----------------+-------
 Tier 4 (unique) | 37540
 Tier 2          |  5890
(2 rows)

========== Step 7e: Curation reasons ==========
       reason        | count 
---------------------+-------
 initial_only        |  5782
 missing_dob         |  2442
 missing_nationality |  2275
(3 rows)

========== Step 7f: Curation queue size ==========
 total_needing_curation | pct  
------------------------+------
                   7075 | 16.3
(1 row)

========== Step 7g: KILL SWITCH — Duplicate integrity ==========
       issue       |     id      | occurrences 
-------------------+-------------+-------------
 DUPLICATE tm_id   | 1196804     |           2
 DUPLICATE tm_id   | 1209519     |           2
 DUPLICATE tm_id   | 217886      |           2
 DUPLICATE tm_id   | 255450      |           2
 DUPLICATE tm_id   | 255451      |           2
 DUPLICATE tm_id   | 277782      |           2
 DUPLICATE tm_id   | 291177      |           2
 DUPLICATE tm_id   | 420213      |           2
 DUPLICATE tm_id   | 420243      |           2
 DUPLICATE tm_id   | 646739      |           2
 DUPLICATE tm_id   | 742063      |           2
 DUPLICATE tm_id   | 746642      |           2
 DUPLICATE tm_id   | 990008      |           2
 DUPLICATE apif_id | apif_162473 |           2
 DUPLICATE apif_id | apif_19163  |           2
 DUPLICATE apif_id | apif_25917  |           2
 DUPLICATE apif_id | apif_2670   |           2
 DUPLICATE apif_id | apif_271664 |           2
 DUPLICATE apif_id | apif_280687 |           2
 DUPLICATE apif_id | apif_30931  |           2
(20 rows)

========== Step 7h: Sample VERIFIED ==========
 profile_id |  tm_id  |   apif_id   |      display_name      | date_of_birth |   nationality    |   current_club   
------------+---------+-------------+------------------------+---------------+------------------+------------------
       5718 | 1145504 | apif_422780 | Aarón Anselmino        | 2005-04-29    | Argentina        | Boca Juniors
       1282 | 254249  | apif_62018  | Aaron Appindangoyé     | 1992-02-20    | Gabon            | Kocaelispor
       5351 | 987366  | apif_453706 | Aaron Bouwman          | 2007-08-28    | Netherlands      | Ajax
       4407 | 724108  | apif_343538 | Aaron Ciammaglichella  | 2005-01-26    | Italy            | Torino
       3812 | 624243  | apif_327606 | Aaron Donnelly         | 2003-06-08    | Northern Ireland | Dundee
       1511 | 284430  | apif_46673  | Aarón Escandell        | 1995-09-27    | Spain            | Oviedo
       3618 | 591949  | apif_44871  | Aaron Hickey           | 2002-06-10    | Scotland         | Brentford
       1273 | 251878  | apif_25914  | Aarón Martín           | 1997-04-22    | Spain            | Genoa
        172 | 56836   | apif_37923  | Aaron Meijers          | 1987-10-28    | Netherlands      | FC Volendam
       2621 | 427568  | apif_20355  | Aaron Ramsdale         | 1998-05-14    | England          | Newcastle
       1880 | 646658  | apif_278079 | Aaron Ramsey           | 2003-01-21    | England          | Valencia
        132 | 50057   | apif_1459   | Aaron Ramsey           | 1990-12-26    | Wales            | U.N.A.M. - Pumas
       4445 | 730484  | apif_323951 | Aaron Zehnter          | 2004-10-31    | Germany          | VfL Wolfsburg
       4889 | 867082  | apif_306154 | Abakar Gadzhiev        | 2003-12-31    | Russia           | Akhmat
       4569 | 754037  | apif_263676 | Abbosbek Fayzullaev    | 2003-10-03    | Uzbekistan       | CSKA Moscow
       4598 | 776798  | apif_277191 | Abdallah Sima          | 2001-06-17    | Senegal          | Lens
       4409 | 724520  | apif_181421 | Abde Ezzalzouli        | 2001-12-17    | Morocco          | Real Betis
       4369 | 718034  | apif_183751 | Abde Rebbach           | 1998-08-11    | Algeria          | Alaves
       3403 | 559979  | apif_46813  | Abdel Abqar            | 1999-03-10    | Morocco          | Getafe
       5704 | 1134251 | apif_417830 | Abdelhamid Ait Boudlal | 2006-04-16    | Morocco          | Rennes
       1909 | 340394  | apif_19053  | Abdelhamid Sabiri      | 1996-11-28    | Morocco          | Fiorentina
       3622 | 592400  | apif_129867 | Abdelkahar Kadri       | 2000-06-24    | Algeria          | Gent
       5625 | 1086915 | apif_480311 | Abdelraffie Benzzine   | 2006-04-04    | Netherlands      | Telstar
       5887 | 1429895 | apif_525383 | Abderrahmane Soumare   | 2006-11-11    | Mauritania       | Alverca
        770 | 177452  | apif_46751  | Abdón Prats            | 1992-12-07    | Spain            | Mallorca
(25 rows)

========== Step 7i: Sample ORPHAN ==========
 profile_id |   apif_id   |      display_name      | date_of_birth |      nationality       |                curation_reason                 
------------+-------------+------------------------+---------------+------------------------+------------------------------------------------
      34717 | apif_437483 | A.  Bamba              | 2004-10-08    | Côte d'Ivoire          | initial_only
      38015 | apif_543038 | A. A. Asad Hajabi      |               | Jordan                 | initial_only; missing_dob
      39475 | apif_552399 | A. A. Saavedra Nevarez |               |                        | initial_only; missing_dob; missing_nationality
      37854 | apif_342740 | A. Abada               |               | Algeria                | initial_only; missing_dob
      35491 | apif_576170 | A. Abdoulraouf         |               |                        | initial_only; missing_dob; missing_nationality
      35876 | apif_576187 | A. Abdu                |               |                        | initial_only; missing_dob; missing_nationality
      37955 | apif_73418  | A. Abdullayev          |               | Uzbekistan             | initial_only; missing_dob
      37711 | apif_532925 | A. Abdullayev          |               | Iran                   | initial_only; missing_dob
      37726 | apif_29852  | A. Aghasi              |               | Iran                   | initial_only; missing_dob
      40105 | apif_6330   | A. Aguerre             | 1990-08-23    | Argentina              | initial_only
      42975 | apif_141109 | A. Agyeman             | 2000-03-15    | Italy                  | initial_only
      38177 | apif_362145 | A. Ahmed               | 2000-10-10    | Canada                 | initial_only
      42718 | apif_1949   | A. Ahmedhodžić         | 1999-03-26    | Bosnia and Herzegovina | initial_only
      43047 | apif_427893 | A. Akaev               | 2004-08-01    | Russia                 | initial_only
      35633 | apif_578902 | A. Al Anazi            |               |                        | initial_only; missing_dob; missing_nationality
      35663 | apif_576185 | A. Al Dakheel          |               |                        | initial_only; missing_dob; missing_nationality
      36987 | apif_323449 | A. Al Dakhil           | 2002-03-06    | Belgium                | initial_only
      35723 | apif_576294 | A. Al Harbi            |               |                        | initial_only; missing_dob; missing_nationality
      35575 | apif_531454 | A. Al Harbi            |               |                        | initial_only; missing_dob; missing_nationality
      35846 | apif_542712 | A. Al Hassan           |               |                        | initial_only; missing_dob; missing_nationality
      37962 | apif_542542 | A. Al Hussain          |               | Qatar                  | initial_only; missing_dob
      35634 | apif_576194 | A. Al Jouei            |               |                        | initial_only; missing_dob; missing_nationality
      35747 | apif_576195 | A. Al Khaibari         |               |                        | initial_only; missing_dob; missing_nationality
      35692 | apif_576297 | A. Al Khaibary         |               |                        | initial_only; missing_dob; missing_nationality
      35914 | apif_630624 | A. Al Khanani          |               |                        | initial_only; missing_dob; missing_nationality
(25 rows)

========== Step 7j: Table sizes ==========
 staging_table_size | dedup_pairs_size 
--------------------+------------------
 18 MB              | 3080 kB
(1 row)

========== Step 7k: Sample-100 spot check ==========
 profile_id | tm_id  |   apif_id   |  display_name   | data_confidence | match_tier 
------------+--------+-------------+-----------------+-----------------+------------
       3579 | 584769 | apif_18929  | Dwight McNeil   | VERIFIED        | Tier 2
       4124 | 670681 | apif_335051 | João Neves      | VERIFIED        | Tier 2
        614 | 148153 | apif_18963  | Lewis Dunk      | VERIFIED        | Tier 2
       1622 | 296622 | apif_746    | Marco Asensio   | VERIFIED        | Tier 2
       3530 | 578391 | apif_21138  | Rayan Aït-Nouri | VERIFIED        | Tier 2
(5 rows)

========== DONE ==========
