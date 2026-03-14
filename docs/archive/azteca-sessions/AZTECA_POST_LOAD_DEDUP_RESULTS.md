# Azteca Post-Load Dedup (Step 7) — Results

**Date:** March 2026  
**Source:** [AZTECA_POST_LOAD_DEDUP.md](./AZTECA_POST_LOAD_DEDUP.md)

---

## Summary

| Metric | Value |
|--------|--------|
| Unmatched legacy players (no source_records) | 184 |
| Duplicate pairs (legacy + new, same name + DOB) | 8 |
| Players flagged (both sides) | 16 |
| Total needs_curation after run | 7,158 |
| Flagged with potential_duplicate_post_load | 16 |

**Duplicate pairs:** Alisson, Casemiro, Ederson, Endrick, Gavi, Marquinhos, Pedri, Rodrygo (legacy UUID + new UUID each). Both sides updated with `needs_curation = TRUE` and `curation_reason` including `potential_duplicate_post_load`. Spot check 7h: Pedri shows legacy (no source_records) and new (TM+APIF) both flagged; Rodri appears 3 times (two with source_records, one without) — only Pedri/Rodrygo were in the 8 pairs; the two “Rodri” rows have different DOB or weren’t matched as legacy+new pair.

---

## Full output

========== 7a: Create _unmatched_legacy (players without source_records) ==========
psql:../run_post_load_dedup.sql:3: NOTICE:  table "_unmatched_legacy" does not exist, skipping
DROP TABLE
SELECT 184
========== 7b: Unmatched legacy count ==========
 unmatched_legacy_players 
--------------------------
                      184
(1 row)

========== 7c: Find duplicate pairs (legacy + new, same name + DOB) ==========
psql:../run_post_load_dedup.sql:14: NOTICE:  table "_post_load_duplicates" does not exist, skipping
DROP TABLE
SELECT 8
========== 7d: Duplicate pairs count ==========
 duplicate_pairs_found 
-----------------------
                     8
(1 row)

========== 7e: All duplicate pairs ==========
           legacy_player_id           | legacy_name |            new_player_id             |  new_name  | new_confidence | date_of_birth | nationality_primary 
--------------------------------------+-------------+--------------------------------------+------------+----------------+---------------+---------------------
 121914ce-784f-4706-849a-787c040710cf | Alisson     | 5947ee1a-c176-4072-a15d-7bf0024a9e25 | Alisson    | medium         | 1992-10-02    | Brazil
 11739958-30b5-4a20-a11f-18ad8284a080 | Casemiro    | c70c4ff0-ff04-49c7-9650-9f8af0e8bcbe | Casemiro   | high           | 1992-02-23    | Brazil
 ff6b44a5-cbc6-4941-a891-272d13c822e2 | Ederson     | 2ddbf6ec-8609-4d69-ae37-68c2930594b3 | Ederson    | high           | 1993-08-17    | Brazil
 e51ee5d0-88a9-422b-b851-e7e7adc2e4f1 | Endrick     | 1c7da607-79c9-4a53-8498-68a96e88b116 | Endrick    | high           | 2006-07-21    | Brazil
 8c0ef05a-6515-47ef-839b-752e7fb4a4c0 | Gavi        | e917e793-599d-43ec-b411-ef1bf7da882c | Gavi       | high           | 2004-08-05    | Spain
 61b851d2-7738-49df-8354-e7be7e47b47c | Marquinhos  | 21409654-4eff-45e0-aef3-898b18cea57c | Marquinhos | high           | 1994-05-14    | Brazil
 bd3c0f4a-0ede-4123-a7aa-857deb20bb66 | Pedri       | 8e93c173-9394-46e3-9aff-c54ad10bab4b | Pedri      | high           | 2002-11-25    | Spain
 9d4dc5b8-f689-4f41-881f-7c894a100bb9 | Rodrygo     | c28f7334-9491-4529-a0e3-324dedb69ca1 | Rodrygo    | high           | 2001-01-09    | Brazil
(8 rows)

========== 7f: Flag BOTH sides for curation ==========
UPDATE 16
========== 7g: Report after flagging ==========
 total_needs_curation | flagged_post_load_dup 
----------------------+-----------------------
                 7158 |                    16
(1 row)

========== 7h: Spot check — Pedri / Rodri ==========
                  id                  | known_as | data_confidence | needs_curation |        curation_reason        |        source_records        
--------------------------------------+----------+-----------------+----------------+-------------------------------+------------------------------
 bd3c0f4a-0ede-4123-a7aa-857deb20bb66 | Pedri    | high            | t              | potential_duplicate_post_load | 
 8e93c173-9394-46e3-9aff-c54ad10bab4b | Pedri    | high            | t              | potential_duplicate_post_load | TM:683840 + APIF:apif_133609
 99a359b0-4ab9-41f8-82fa-ce5ca61afbbf | Rodri    | high            | f              |                               | 
 9546c31d-da4b-4ae5-80d6-9057af0632ab | Rodri    | high            | f              |                               | TM:357565 + APIF:apif_44
 fcaea4a6-d14e-49aa-8354-eae9def6112b | Rodri    | medium          | f              |                               | TM:8163
(5 rows)

========== DONE ==========
