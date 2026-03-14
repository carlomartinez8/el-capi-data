# Azteca Promote Staging to Production — Results

**Date:** March 2026  
**Source:** [AZTECA_PROMOTE_STAGING.md](./AZTECA_PROMOTE_STAGING.md)

---

## Summary

| Metric | Value |
|--------|--------|
| Existing warehouse players (before) | 638 |
| Staging profiles matching existing (alias map) | 454 |
| **Step 2: Existing players updated (identity from staging)** | **454** |
| **Step 3: New players inserted** | **42,993** |
| **Total warehouse players (after)** | **43,631** |
| high / medium / low confidence | 6,024 / 30,515 / 7,092 |
| Needs curation | 7,142 (16.4%) |
| Aliases: TM id / TM url / APIF | 34,554 / 34,370 / 14,917 |
| Career records | 43,631 (club 43,148, position 43,631, value 32,802) |
| Wikipedia coverage | 1,753 |
| **6i: Enriched players with stories intact** | **638** (475 origin_story, 472 career_summary) |
| **6k: Duplicate aliases** | **0 rows** — pass |

Identity overwritten from staging for 454 existing players; GPT enrichment (stories, personality) preserved. Warehouse production-ready.

---

## Full output

========== Step 0: Add curation columns to players ==========
ALTER TABLE
CREATE INDEX
========== Step 1a: Existing warehouse players ==========
 existing_warehouse_players 
----------------------------
                        638
(1 row)

========== Step 1b: Alias counts ==========
    alias_type    | alias_count 
------------------+-------------
 alternate_name   |         190
 transfermarkt_id |         638
(2 rows)

========== Step 1c: Build staging–warehouse map (aliases) ==========
psql:../run_promote_staging.sql:25: NOTICE:  table "_staging_warehouse_map" does not exist, skipping
DROP TABLE
SELECT 454
========== Step 1c report: staging profiles matching existing ==========
 staging_profiles_matching_existing 
------------------------------------
                                454
(1 row)

========== Step 1d: New vs already in warehouse ==========
 total_staging | already_in_warehouse | new_profiles 
---------------+----------------------+--------------
         43447 |                  454 |        42993
(1 row)

========== Step 1e: Fallback name+DOB matches (diagnostic) ==========
 name_dob_matches 
------------------
              462
(1 row)

========== Step 2a: Update existing players (identity from staging) ==========
UPDATE 454
========== Step 3: Insert NEW players from staging ==========
INSERT 0 42993
========== Step 4a: Build full player map ==========
psql:../run_promote_staging.sql:149: NOTICE:  table "_full_player_map" does not exist, skipping
DROP TABLE
SELECT 43447
========== Step 4b–4d: Insert aliases ==========
INSERT 0 33916
INSERT 0 14917
INSERT 0 34370
========== Step 4e: Alias counts after load ==========
    alias_type     | count 
-------------------+-------
 transfermarkt_id  | 34554
 transfermarkt_url | 34370
 apif_id           | 14917
 alternate_name    |   190
(4 rows)

========== Step 5: Upsert player_career ==========
INSERT 0 43447
========== Step 6a: Total warehouse players ==========
 total_warehouse_players 
-------------------------
                   43631
(1 row)

========== Step 6b: Confidence breakdown ==========
 data_confidence | count | pct  
-----------------+-------+------
 high            |  6024 | 13.8
 medium          | 30515 | 69.9
 low             |  7092 | 16.3
(3 rows)

========== Step 6c: Curation queue ==========
 needs_curation | clean | curation_pct 
----------------+-------+--------------
           7142 | 36489 |         16.4
(1 row)

========== Step 6d: Alias coverage ==========
    alias_type     | count 
-------------------+-------
 apif_id           | 14917
 transfermarkt_id  | 34554
 transfermarkt_url | 34370
 alternate_name    |   190
(4 rows)

========== Step 6e: Career coverage ==========
 total_career_records | has_club | has_position | has_market_value 
----------------------+----------+--------------+------------------
                43631 |    43148 |        43631 |            32802
(1 row)

========== Step 6f: Wikipedia coverage ==========
 has_wikipedia | total 
---------------+-------
          1753 | 43631
(1 row)

========== Step 6g: Sample high-confidence (25) ==========
                  id                  |      known_as      | data_confidence | nationality_primary | position_primary |    current_club     | estimated_value_eur 
--------------------------------------+--------------------+-----------------+---------------------+------------------+---------------------+---------------------
 fae81256-c2bc-4656-9e0c-cb8f1d19514e | Kylian Mbappé      | high            | France              | Forward          | Real Madrid         |           200000000
 9b7cded6-d1bc-4744-b53c-990dbedea7d1 | Erling Haaland     | high            | Norway              | Forward          | Manchester City     |           200000000
 3384761a-323c-4f00-b77f-060341476369 | Lamine Yamal       | high            | Spain               | Forward          | Barcelona           |           200000000
 df4ec613-04bc-4895-bac6-2f38c6fb267b | Jude Bellingham    | high            | England             | Midfielder       | Real Madrid         |           160000000
 e9d92c36-ff1b-431f-a7fc-ca3ae00527cd | Vinicius Junior    | high            | Brazil              | Forward          | Real Madrid         |           150000000
 8e93c173-9394-46e3-9aff-c54ad10bab4b | Pedri              | high            | Spain               | Midfielder       | Barcelona           |           140000000
 4a4ec165-9b17-45a6-b0b8-96cbb96cd9ae | Jamal Musiala      | high            | Germany             | Midfielder       | Bayern München      |           130000000
 d0f2a459-51cc-4941-8ca3-91a8efa4f413 | Michael Olise      | high            | France              | Forward          | Bayern München      |           130000000
 f21b1bc8-2e82-412a-8e1e-c01ac6d57eed | Federico Valverde  | high            | Uruguay             | Midfielder       | Real Madrid         |           120000000
 4ce3ae6d-332f-415e-abc7-10ed912232dc | Declan Rice        | high            | England             | Midfielder       | Arsenal             |           120000000
 99a359b0-4ab9-41f8-82fa-ce5ca61afbbf | Rodri              | high            | Spain               | MID              | Man City            |           120000000
 c11b73be-b508-42f3-9ff2-e90c39a1242d | Bukayo Saka        | high            | England             | Forward          | Arsenal             |           120000000
 9d4dc5b8-f689-4f41-881f-7c894a100bb9 | Rodrygo            | high            | Brazil              | FWD              | Real Madrid         |           120000000
 99eeb0c4-56c6-4947-a27d-c33303f478e8 | Vitinha            | high            | Portugal            | Midfielder       | Paris Saint Germain |           110000000
 103dff23-4f30-4ee0-bb19-6fc1271fb579 | Cole Palmer        | high            | England             | Midfielder       | Chelsea             |           110000000
 90c42638-7e47-426e-a94d-d4560cfe36d3 | João Neves         | high            | Portugal            | Midfielder       | Paris Saint Germain |           110000000
 e6fe57f0-9079-4a5a-94d1-5cf8cc29d603 | Moisés Caicedo     | high            | Ecuador             | Midfielder       | Chelsea             |           110000000
 c29d4fd7-1534-45c4-b3ea-aacaa1d396e6 | Florian Wirtz      | high            | Germany             | Midfielder       | Liverpool           |           110000000
 65fb583d-0cb4-4bad-bd08-0c34388e7eec | Julián Alvarez     | high            | Argentina           | Forward          | Atletico Madrid     |           100000000
 111df563-c81d-4a84-abb9-e4d3aa40fde0 | Alexander Isak     | high            | Sweden              | Forward          | Liverpool           |           100000000
 ec9b6769-1216-453f-94e9-8e7624e6450f | Ousmane Dembélé    | high            | France              | Forward          | Paris Saint Germain |           100000000
 bd3c0f4a-0ede-4123-a7aa-857deb20bb66 | Pedri              | high            | Spain               | MID              | Barcelona           |           100000000
 caa5a9d5-cf53-41f1-bbdc-d8b1569f42c3 | Dominik Szoboszlai | high            | Hungary             | Midfielder       | Liverpool           |           100000000
 864a7fe2-01cb-41c5-b306-d7f3f9ebb6fe | Ryan Gravenberch   | high            | Netherlands         | Midfielder       | Liverpool           |            90000000
 aa4a9084-a353-498d-8a15-0b2c443ab71a | Arda Güler         | high            | Türkiye             | Midfielder       | Real Madrid         |            90000000
(25 rows)

========== Step 6h: Sample curation queue (25) ==========
        known_as        | data_confidence | needs_curation |                curation_reason                 |  source_records  
------------------------+-----------------+----------------+------------------------------------------------+------------------
 A.  Bamba              | low             | t              | initial_only                                   | APIF:apif_437483
 A. A. Asad Hajabi      | low             | t              | initial_only; missing_dob                      | APIF:apif_543038
 A. A. Saavedra Nevarez | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_552399
 A. Abada               | low             | t              | initial_only; missing_dob                      | APIF:apif_342740
 A. Abdoulraouf         | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_576170
 A. Abdu                | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_576187
 A. Abdullayev          | low             | t              | initial_only; missing_dob                      | APIF:apif_532925
 A. Abdullayev          | low             | t              | initial_only; missing_dob                      | APIF:apif_73418
 A. Aghasi              | low             | t              | initial_only; missing_dob                      | APIF:apif_29852
 A. Aguerre             | low             | t              | initial_only                                   | APIF:apif_6330
 A. Agyeman             | low             | t              | initial_only                                   | APIF:apif_141109
 A. Ahmed               | low             | t              | initial_only                                   | APIF:apif_362145
 A. Ahmedhodžić         | low             | t              | initial_only                                   | APIF:apif_1949
 A. Akaev               | low             | t              | initial_only                                   | APIF:apif_427893
 A. Al Anazi            | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_578902
 A. Al Dakheel          | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_576185
 A. Al Dakhil           | low             | t              | initial_only                                   | APIF:apif_323449
 A. Al Harbi            | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_576294
 A. Al Harbi            | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_531454
 A. Al Hassan           | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_542712
 A. Al Hussain          | low             | t              | initial_only; missing_dob                      | APIF:apif_542542
 A. Al Jouei            | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_576194
 A. Al Khaibari         | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_576195
 A. Al Khaibary         | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_576297
 A. Al Khanani          | low             | t              | initial_only; missing_dob; missing_nationality | APIF:apif_630624
(25 rows)

========== Step 6i: Enriched players (stories intact) ==========
 enriched_players_with_stories | has_origin_story | has_career_summary 
-------------------------------+------------------+--------------------
                           638 |              475 |                472
(1 row)

========== Step 6j: Table sizes ==========
 players_size | aliases_size | career_size 
--------------+--------------+-------------
 21 MB        | 28 MB        | 14 MB
(1 row)

========== Step 6k: KILL SWITCH — duplicate aliases (MUST be 0 rows) ==========
 issue | alias_type | alias_value | count 
-------+------------+-------------+-------
(0 rows)

========== DONE ==========
