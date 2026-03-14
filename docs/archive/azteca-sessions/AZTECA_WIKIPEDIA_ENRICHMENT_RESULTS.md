# Azteca Wikipedia Enrichment — Results

**Date:** March 2026  
**Script:** run_wikipedia_enrichment.sql ([AZTECA_WIKIPEDIA_ENRICHMENT.md](./AZTECA_WIKIPEDIA_ENRICHMENT.md))

---

## Summary

| Metric | Value |
|--------|--------|
| Total bios in player_bios | 1,841 |
| Bios matching staging | 1,841 (100%) |
| Profiles enriched (wikipedia_bio set) | 1,753 |
| Orphaned bios | 0 |
| VERIFIED with Wikipedia | 1,090 (18.7%) |
| PROJECTED with Wikipedia | 246 (0.8%) |
| ORPHAN with Wikipedia | 415 (6.2%) |
| Staging table size | 19 MB |

Enrichment only — no rows added or removed. Ready for staging → production promotion and curation queue build.

---

## Full output

========== Step 1: Add Wikipedia columns ==========
ALTER TABLE
========== Step 2a: Total bios ==========
 total_bios 
------------
       1841
(1 row)

========== Step 2b: Bios by source (TM vs APIF) ==========
 source | bio_count 
--------+-----------
 APIF   |       842
 TM     |       999
(2 rows)

========== Step 2c: Bios matching staging profiles ==========
 bios_matching_staging 
-----------------------
                  1841
(1 row)

========== Step 2d: Sample bios ==========
 player_id |                      wikipedia_url                      |                                                                                               bio_preview                                                                                                
-----------+---------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 937958    | https://en.wikipedia.org/wiki/Lamine_Yamal              | Lamine Yamal Nasraoui Ebana is a Spanish professional footballer who plays as a right winger or right midfielder for La Liga club Barcelona and the Spain national team. Known for his flair, chance cre
 342229    | https://en.wikipedia.org/wiki/Kylian_Mbapp%C3%A9        | Kylian Mbappé Lottin is a French professional footballer who plays as a forward for La Liga club Real Madrid and captains the France national team. He is widely regarded as one of the best players in 
 418560    | https://en.wikipedia.org/wiki/Erling_Haaland            | Erling Braut Haaland is a Norwegian professional footballer who plays as a striker for Premier League club Manchester City and the Norway national team. Considered one of the best players in the world
 581678    | https://en.wikipedia.org/wiki/Jude_Bellingham           | Jude Victor William Bellingham is an English professional footballer who plays as a midfielder for La Liga club Real Madrid and the England national team. Known for his exceptional work rate, playmaki
 371998    | https://en.wikipedia.org/wiki/Vin%C3%ADcius_J%C3%BAnior | Vinícius José Paixão de Oliveira Júnior, commonly known as Vinícius Júnior or Vini Jr., is a Brazilian professional footballer who plays as a forward for La Liga club Real Madrid and the Brazil nation
 683840    | https://en.wikipedia.org/wiki/Pedri                     | Pedro González López, more commonly known as Pedri, is a Spanish professional footballer who plays as a midfielder for La Liga club Barcelona and the Spain national team. Considered one of the best mi
 580195    | https://en.wikipedia.org/wiki/Jamal_Musiala             | Jamal Musiala is a German professional footballer who plays as an attacking midfielder for Bundesliga club Bayern Munich and the Germany national team. Widely regarded as one of the best attacking mid
 566723    | https://en.wikipedia.org/wiki/Michael_Olise             | Michael Akpovie Olise is a professional footballer who plays as a winger and attacking midfielder for Bundesliga club Bayern Munich. Born in England, he plays for the France national team. Regarded as
 357662    | https://en.wikipedia.org/wiki/Declan_Rice               | Declan Rice is an English professional footballer who plays as a defensive midfielder for Premier League club Arsenal and the England national team. Known for his versatility, stamina, ball-carrying a
 433177    | https://en.wikipedia.org/wiki/Bukayo_Saka               | Bukayo Ayoyinka Temidayo Moses Saka is an English professional footballer who plays as a right winger for Premier League club Arsenal and the England national team. Known for his creativity, dribbling
(10 rows)

========== Step 3a: Enrich by tm_id ==========
UPDATE 999
========== Step 3b: Enrich by apif_id (where not already set) ==========
UPDATE 754
========== Step 4a: Profiles with Wikipedia ==========
 profiles_with_wikipedia 
-------------------------
                    1753
(1 row)

========== Step 4b: Enrichment by confidence ==========
 data_confidence | has_wiki | total | wiki_pct 
-----------------+----------+-------+----------
 VERIFIED        |     1090 |  5840 |     18.7
 PROJECTED       |      246 | 30515 |      0.8
 PARTIAL         |        2 |   400 |      0.5
 ORPHAN          |      415 |  6692 |      6.2
(4 rows)

========== Step 4c: Sample enriched profiles ==========
 profile_id | tm_id |   apif_id   |    display_name     | data_confidence |                           wikipedia_url                            |                                                                      bio_preview                                                                       
------------+-------+-------------+---------------------+-----------------+--------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------
      38017 |       | apif_543038 | A. A. Asad Hajabi   | ORPHAN          | https://en.wikipedia.org/wiki/Ali_Hajabi                           | Ali Ahmad Asad Hajabi is a Jordanian professional footballer who plays as a defender for the Jordanian club Al-Hussein and the Jordan national team.
      37856 |       | apif_342740 | A. Abada            | ORPHAN          | https://en.wikipedia.org/wiki/Liel_Abada                           | Liel Abada is an Israeli professional footballer who plays as a winger or a forward for Major League Soccer side Charlotte FC and the Israel national 
      37711 |       | apif_532925 | A. Abdullayev       | ORPHAN          | https://en.wikipedia.org/wiki/Araz_Abdullayev                      | Araz Abdulla oğlu Abdullayev is an Azerbaijani footballer who plays as a winger for Azerbaijani club Karvan and the Azerbaijan national team.
      37957 |       | apif_73418  | A. Abdullayev       | ORPHAN          | https://en.wikipedia.org/wiki/Araz_Abdullayev                      | Araz Abdulla oğlu Abdullayev is an Azerbaijani footballer who plays as a winger for Azerbaijani club Karvan and the Azerbaijan national team.
      37726 |       | apif_29852  | A. Aghasi           | ORPHAN          | https://en.wikipedia.org/wiki/Aref_Aghasi                          | Aref Aghasi Kolahsorkhi is an Iranian footballer who plays as a Centre-Back for Iranian club Esteghlal in Persian Gulf Pro League.
      40111 |       | apif_6330   | A. Aguerre          | ORPHAN          | https://en.wikipedia.org/wiki/Washington_Aguerre                   | Washington Omar Aguerre Lima is a Uruguayan professional footballer who plays as a goalkeeper for Uruguayan Primera División club Peñarol.
      38181 |       | apif_362145 | A. Ahmed            | ORPHAN          | https://en.wikipedia.org/wiki/Ali_Ahmed_(soccer)                   | Ali Ahmed is a Canadian professional soccer player who plays as a wide midfielder or winger for EFL Championship club Norwich City and the Canada nati
      36984 |       | apif_323449 | A. Al Dakhil        | ORPHAN          | https://en.wikipedia.org/wiki/Ameen_Al-Dakhil                      | Ameen Al-Dakhil is a professional footballer who plays as a centre-back for Bundesliga club VfB Stuttgart. Born in Iraq, he plays for the Belgium nati
      37964 |       | apif_542542 | A. Al Hussain       | ORPHAN          | https://en.wikipedia.org/wiki/Hussain_Al-Qahtani                   | Hussain Al-Qahtani is a Saudi Arabian professional footballer who plays as a midfielder for Al-Diriyah. He has also played for the Saudi Arabia nation
      38270 |       | apif_42006  | A. Al Musrati       | PROJECTED       | https://en.wikipedia.org/wiki/Al-Musrati                           | Al-Mu'attasim Billah Ali Mohamed Al-Musrati, known simply as Al-Musrati, is a Libyan professional footballer who plays as a defensive midfielder for S
      37999 |       | apif_542548 | A. Al Oui           | ORPHAN          | https://en.wikipedia.org/wiki/Hafid_Derradji                       | Hafid Derradji is an Algerian sports commentator and former footballer.
      38041 |       | apif_542650 | A. Alaa             | ORPHAN          | https://en.wikipedia.org/wiki/Hamza_Alaa                           | Hamza Alaa Abdallah Hussein is an Egyptian professional footballer who plays as a goalkeeper for Egyptian Premier League club Al Ahly SC and the Egypt
      38207 |       | apif_546151 | A. Albarracin       | ORPHAN          | https://en.wikipedia.org/wiki/Agust%C3%ADn_Albarrac%C3%ADn         | Agustín Albarracín Basil is a Uruguayan professional footballer who plays as a forward for Italian Serie A club Cagliari.
      38043 |       | apif_297343 | A. Alcaraz          | ORPHAN          | https://en.wikipedia.org/wiki/Charly_Alcaraz                       | Carlos Jonas "Charly" Alcaraz Durán is an Argentine professional footballer who plays as an attacking midfielder for Premier League club Everton.
      37765 |       | apif_29720  | A. Alipour          | ORPHAN          | https://en.wikipedia.org/wiki/Ali_Alipour                          | Ali Alipour is an Iranian professional footballer who plays as a Striker for Persian Gulf Pro League club Persepolis.
      40533 |       | apif_566354 | A. Almaraz          | ORPHAN          | https://en.wikipedia.org/wiki/Almaraz_(surname)                    | Almaraz is a surname. Notable people with the surname include:Carlos Almaraz (1941–1989), Mexican-American artist                                     +
            |       |             |                     |                 |                                                                    | Bárbara Almaraz, Mexican women's int
      39176 |       | apif_271852 | A. Álvarez Bermúdez | ORPHAN          | https://en.wikipedia.org/wiki/Juli%C3%A1n_Alvarez                  | Julián Alvarez is an Argentine professional footballer who plays as a forward for La Liga club Atlético Madrid and the Argentina national team.
      38386 |       | apif_535046 | A. Amaimouni        | ORPHAN          | https://en.wikipedia.org/wiki/Ayoube_Amaimouni                     | Ayoube Amaimouni-Echghouyabe is a Spanish professional footballer who plays as a winger for German Bundesliga club Eintracht Frankfurt.
      37593 |       | apif_7197   | A. Andrade          | ORPHAN          | https://en.wikipedia.org/wiki/Leandro_Andrade_(footballer)         | Leandro Livramento Andrade is a professional footballer who plays as a midfielder for Azerbaijan Premier League club Qarabağ. Born in Portugal, he pla
      40228 |       | apif_425714 | A. Andrade Elias    | PROJECTED       | https://en.wikipedia.org/wiki/Allan_(footballer%2C_born_2004)      | Allan Andrade Elias, simply known as Allan, is a Brazilian professional footballer who plays as a midfielder for Palmeiras.
      38626 |       | apif_301465 | A. Anello           | ORPHAN          | https://en.wikipedia.org/wiki/Agustin_Anello                       | Agustín Anello Giaquinta is an American professional soccer player who plays as a winger for Major League Soccer club Philadelphia Union.
      37507 |       | apif_13729  | Á. Angulo Mosquera  | PROJECTED       | https://en.wikipedia.org/wiki/Guillermo_Mart%C3%ADnez_(footballer) | Guillermo Martínez Ayala, commonly known as "Memote", is a Mexican professional footballer who plays as a forward for Liga MX club UNAM and the Mexico
      37214 |       | apif_457731 | A. Annous           | ORPHAN          | https://en.wikipedia.org/wiki/Andre_Harriman-Annous                | Andre Ryan Harriman-Annous is an English professional footballer who plays as a striker for Premier League club Arsenal.
      39324 |       | apif_10239  | Á. Araos Llanos     | PROJECTED       | https://en.wikipedia.org/wiki/Willian_Ar%C3%A3o                    | Willian Souza Arão da Silva is a Brazilian professional footballer who plays for Santos. Mainly a defensive midfielder, he can also play as a centre-b
      38947 |       | apif_201908 | A. Aravena Guzmán   | ORPHAN          | https://en.wikipedia.org/wiki/Jorge_Aravena_(footballer)           |  Jorge Orlando "Mortero" Aravena Plaza is a Chilean former footballer. A left-footed attacking midfielder or deep-lying forward, he played for several
(25 rows)

========== Step 4d: Orphaned bios (no matching profile) ==========
 orphaned_bios 
---------------
             0
(1 row)

========== Step 4e: Staging table size ==========
 staging_table_size 
--------------------
 19 MB
(1 row)

========== DONE ==========
