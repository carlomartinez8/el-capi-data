# Azteca Photo Audit — Results

**Date:** March 2026  
**Source:** [AZTECA_PHOTO_AUDIT.md](./AZTECA_PHOTO_AUDIT.md) — read-only.

---

## Full output

========== 1: Overall photo coverage ==========
 total_profiles | has_photo | no_photo | photo_pct 
----------------+-----------+----------+-----------
          43447 |     43447 |        0 |     100.0
(1 row)

========== 2: Photo coverage by confidence ==========
 data_confidence | total | has_photo | no_photo | photo_pct 
-----------------+-------+-----------+----------+-----------
 VERIFIED        |  5840 |      5840 |        0 |     100.0
 PROJECTED       | 30515 |     30515 |        0 |     100.0
 PARTIAL         |   400 |       400 |        0 |     100.0
 ORPHAN          |  6692 |      6692 |        0 |     100.0
(4 rows)

========== 3: Photo source breakdown ==========
 photo_source | count 
--------------+-------
 TM           | 34370
 APIF         |  9077
(2 rows)

========== 4: TM default placeholder count ==========
 tm_default_placeholder_photos 
-------------------------------
                          5710
(1 row)

========== 5: VERIFIED photo status ==========
 photo_status | count 
--------------+-------
 TM photo     |  5840
(1 row)

========== 6: Sample NO photo (25) ==========
 profile_id | tm_id | apif_id | display_name | data_confidence | match_tier 
------------+-------+---------+--------------+-----------------+------------
(0 rows)

========== 7: Sample VERIFIED with APIF photo fallback (15) ==========
 profile_id | tm_id | apif_id | display_name | photo_url 
------------+-------+---------+--------------+-----------
(0 rows)

========== DONE ==========
