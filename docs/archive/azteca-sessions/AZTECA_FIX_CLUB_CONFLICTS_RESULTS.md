# Azteca Fix Club Conflicts — Part 1 + Part 2 Only (STOP before Part 3)

**Date:** March 2026  
**Source:** [AZTECA_FIX_CLUB_CONFLICTS.md](./AZTECA_FIX_CLUB_CONFLICTS.md)

---

## Summary for Pelé

**Part 1 (rollback):** 5,576 players had only `club_conflict_tm_apif` → cleared. 7 had composite reason → stripped club part. `remaining_club_flags = 0`. `total_needs_curation` back to **7,158**.

**Part 2 (smarter detection):** Containment rule applied. **2,680** rows in `_club_conflicts_v2` (down from 5,583). Top 50 and all high-value (>10M) listed below. Many remaining rows are still naming variants (e.g. "Paris Saint-Germain" vs "Paris Saint Germain" hyphen, "Atlético" accent). **Part 3 NOT run** — awaiting your confirm that these are real conflicts before flagging.

---

## Full output

========== PART 1: Rollback false flags ==========
---------- 1a: Clear players whose ONLY reason was club_conflict ----------
UPDATE 5576
---------- 1b: Strip club_conflict from composite curation_reason ----------
UPDATE 7
UPDATE 0
---------- 1c: Verify rollback — remaining club flags (expect 0) ----------
 remaining_club_flags 
----------------------
                    0
(1 row)

---------- 1d: Curation queue after rollback ----------
 total_needs_curation 
----------------------
                 7158
(1 row)

========== PART 2: Smarter club conflict detection ==========
---------- 2a: Build _club_conflicts_v2 (no containment = real conflict) ----------
psql:../run_fix_club_conflicts_p1_p2.sql:34: NOTICE:  table "_club_conflicts_v2" does not exist, skipping
DROP TABLE
SELECT 2680
---------- 2b: Real club conflicts count ----------
 real_club_conflicts 
---------------------
                2680
(1 row)

---------- 2c: All real conflicts (top 50 by value) ----------
  tm_id  |        tm_name        |   apif_id   |     apif_name      |                  tm_says                  |      apif_says      | tm_market_value 
---------+-----------------------+-------------+--------------------+-------------------------------------------+---------------------+-----------------
 487469  | Vitinha               | apif_128384 | Vitinha            | Paris Saint-Germain Football Club         | Paris Saint Germain |       110000000
 670681  | João Neves            | apif_335051 | João Neves         | Paris Saint-Germain Football Club         | Paris Saint Germain |       110000000
 576024  | Julián Alvarez        | apif_6009   | J. Álvarez         | Club Atlético de Madrid S.A.D.            | Atletico Madrid     |       100000000
 288230  | Ousmane Dembélé       | apif_153    | O. Dembélé         | Paris Saint-Germain Football Club         | Paris Saint Germain |       100000000
 502670  | Khvicha Kvaratskhelia | apif_483    | K. Kvaratskhelia   | Paris Saint-Germain Football Club         | Paris Saint Germain |        90000000
 914562  | Désiré Doué           | apif_343027 | D. Doué            | Paris Saint-Germain Football Club         | Paris Saint Germain |        90000000
 1056993 | Estêvão               | apif_425733 | Estêvão            | Chelsea Football Club                     | Palmeiras           |        80000000
 398073  | Achraf Hakimi         | apif_9      | A. Hakimi          | Paris Saint-Germain Football Club         | Paris Saint Germain |        80000000
 583255  | Antoine Semenyo       | apif_19281  | A. Semenyo         | Manchester City Football Club             | Bournemouth         |        75000000
 616341  | Nuno Mendes           | apif_263482 | Nuno Mendes        | Paris Saint-Germain Football Club         | Paris Saint Germain |        75000000
 357164  | Rafael Leão           | apif_22236  | Rafael Leão        | Associazione Calcio Milan                 | AC Milan            |        70000000
 708265  | Bradley Barcola       | apif_161904 | B. Barcola         | Paris Saint-Germain Football Club         | Paris Saint Germain |        70000000
 661171  | Willian Pacho         | apif_16367  | W. Pacho           | Paris Saint-Germain Football Club         | Paris Saint Germain |        70000000
 546543  | Darwin Núñez          | apif_51617  | D. Núñez           | Liverpool Football Club                   | Al-Hilal Saudi FC   |        70000000
 392757  | Marc Guéhi            | apif_67971  | M. Guéhi           | Manchester City Football Club             | Crystal Palace      |        65000000
 455661  | Nick Woltemade        | apif_158054 | N. Woltemade       | Newcastle United Football Club            | VfB Stuttgart       |        65000000
 339808  | Theo Hernández        | apif_47300  | T. Hernández       | Associazione Calcio Milan                 | Al-Hilal Saudi FC   |        60000000
 775605  | Pablo Barrios         | apif_336594 | Pablo Barrios      | Club Atlético de Madrid S.A.D.            | Atletico Madrid     |        60000000
 479999  | Eberechi Eze          | apif_19586  | E. Eze             | Arsenal Football Club                     | Crystal Palace      |        60000000
 395516  | Moussa Diaby          | apif_277    | M. Diaby           | Aston Villa Football Club                 | Al-Ittihad FC       |        55000000
 548111  | Álex Baena            | apif_182219 | Álex Baena         | Club Atlético de Madrid S.A.D.            | Atletico Madrid     |        55000000
 461496  | Morten Hjulmand       | apif_7712   | M. Hjulmand        | Sporting Clube de Portugal                | Sporting CP         |        50000000
 1057316 | Franco Mastantuono    | apif_449249 | Franco Mastantuono | Real Madrid Club de Fútbol                | River Plate         |        50000000
 251664  | Ivan Toney            | apif_19974  | I. Toney           | Brentford Football Club                   | Al-Ahli Jeddah      |        50000000
 659089  | Ilya Zabarnyi         | apif_161671 | I. Zabarnyi        | Paris Saint-Germain Football Club         | Paris Saint Germain |        50000000
 68290   | Neymar                | apif_276    | Neymar             | Paris Saint-Germain Football Club         | Santos              |        50000000
 566931  | Xavi Simons           | apif_162016 | X. Simons          | Tottenham Hotspur Football Club           | RB Leipzig          |        50000000
 624690  | Manu Koné             | apif_22147  | M. Koné            | Associazione Sportiva Roma                | AS Roma             |        50000000
 659813  | Piero Hincapié        | apif_127817 | P. Hincapié        | Arsenal Football Club                     | Bayer Leverkusen    |        50000000
 810092  | Warren Zaïre-Emery    | apif_336657 | W. Zaïre-Emery     | Paris Saint-Germain Football Club         | Paris Saint Germain |        50000000
 549006  | Gonçalo Inácio        | apif_265595 | Gonçalo Inácio     | Sporting Clube de Portugal                | Sporting CP         |        45000000
 618472  | Castello Lukeba       | apif_162761 | C. Lukeba          | RasenBallsport Leipzig                    | RB Leipzig          |        45000000
 443710  | Angelo Stiller        | apif_137210 | A. Stiller         | Verein für Bewegungsspiele Stuttgart 1893 | VfB Stuttgart       |        45000000
 315858  | Gianluigi Donnarumma  | apif_1622   | G. Donnarumma      | Manchester City Football Club             | Paris Saint Germain |        45000000
 429983  | Jørgen Strand Larsen  | apif_2032   | J. Strand Larsen   | Crystal Palace Football Club              | Wolves              |        45000000
 357153  | Diogo Costa           | apif_369    | Diogo Costa        | Futebol Clube do Porto                    | FC Porto            |        40000000
 554903  | Mateo Retegui         | apif_6420   | M. Retegui         | Atalanta Bergamasca Calcio S.p.a.         | Al-Qadisiyah FC     |        40000000
 350219  | Fabián Ruiz           | apif_328    | Fabián Ruiz        | Paris Saint-Germain Football Club         | Paris Saint Germain |        40000000
 225161  | Rúben Neves           | apif_2676   | Rúben Neves        | Wolverhampton Wanderers Football Club     | Al-Hilal Saudi FC   |        40000000
 1168219 | Said El Mala          | apif_432310 | S. El Mala         | 1. Fußball-Club Köln                      | 1. FC Köln          |        40000000
 368887  | Loïs Openda           | apif_86     | L. Openda          | Juventus Football Club                    | RB Leipzig          |        40000000
 903693  | Senny Mayulu          | apif_409216 | Senny Mayulu       | Paris Saint-Germain Football Club         | Paris Saint Germain |        40000000
 957653  | Rodrigo Mora          | apif_404097 | Rodrigo Mora       | Futebol Clube do Porto                    | FC Porto            |        40000000
 742201  | Giuliano Simeone      | apif_323935 | G. Simeone         | Club Atlético de Madrid S.A.D.            | Atletico Madrid     |        40000000
 632349  | Jarell Quansah        | apif_158698 | J. Quansah         | Bayer 04 Leverkusen Fußball               | Bayer Leverkusen    |        40000000
 1012564 | Rayan                 | apif_407806 | Rayan              | Association Football Club Bournemouth     | Vasco DA Gama       |        40000000
 225693  | Fabinho               | apif_299    | Fabinho            | Liverpool Football Club                   | Al-Ittihad FC       |        38000000
 463600  | Lucas Chevalier       | apif_162453 | L. Chevalier       | Paris Saint-Germain Football Club         | Paris Saint Germain |        35000000
 564545  | Edmond Tapsoba        | apif_41150  | E. Tapsoba         | Bayer 04 Leverkusen Fußball               | Bayer Leverkusen    |        35000000
 406040  | Ademola Lookman       | apif_18767  | A. Lookman         | Club Atlético de Madrid S.A.D.            | Atalanta            |        35000000
(50 rows)

---------- 2d: High-value real conflicts (>10M) spot check ----------
         tm_name          |                        tm_says                         |        apif_says         | tm_market_value 
--------------------------+--------------------------------------------------------+--------------------------+-----------------
 Vitinha                  | Paris Saint-Germain Football Club                      | Paris Saint Germain      |       110000000
 João Neves               | Paris Saint-Germain Football Club                      | Paris Saint Germain      |       110000000
 Ousmane Dembélé          | Paris Saint-Germain Football Club                      | Paris Saint Germain      |       100000000
 Julián Alvarez           | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |       100000000
 Khvicha Kvaratskhelia    | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        90000000
 Désiré Doué              | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        90000000
 Achraf Hakimi            | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        80000000
 Estêvão                  | Chelsea Football Club                                  | Palmeiras                |        80000000
 Nuno Mendes              | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        75000000
 Antoine Semenyo          | Manchester City Football Club                          | Bournemouth              |        75000000
 Darwin Núñez             | Liverpool Football Club                                | Al-Hilal Saudi FC        |        70000000
 Rafael Leão              | Associazione Calcio Milan                              | AC Milan                 |        70000000
 Willian Pacho            | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        70000000
 Bradley Barcola          | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        70000000
 Marc Guéhi               | Manchester City Football Club                          | Crystal Palace           |        65000000
 Nick Woltemade           | Newcastle United Football Club                         | VfB Stuttgart            |        65000000
 Pablo Barrios            | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        60000000
 Theo Hernández           | Associazione Calcio Milan                              | Al-Hilal Saudi FC        |        60000000
 Eberechi Eze             | Arsenal Football Club                                  | Crystal Palace           |        60000000
 Álex Baena               | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        55000000
 Moussa Diaby             | Aston Villa Football Club                              | Al-Ittihad FC            |        55000000
 Xavi Simons              | Tottenham Hotspur Football Club                        | RB Leipzig               |        50000000
 Piero Hincapié           | Arsenal Football Club                                  | Bayer Leverkusen         |        50000000
 Ilya Zabarnyi            | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        50000000
 Morten Hjulmand          | Sporting Clube de Portugal                             | Sporting CP              |        50000000
 Manu Koné                | Associazione Sportiva Roma                             | AS Roma                  |        50000000
 Warren Zaïre-Emery       | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        50000000
 Ivan Toney               | Brentford Football Club                                | Al-Ahli Jeddah           |        50000000
 Franco Mastantuono       | Real Madrid Club de Fútbol                             | River Plate              |        50000000
 Neymar                   | Paris Saint-Germain Football Club                      | Santos                   |        50000000
 Gonçalo Inácio           | Sporting Clube de Portugal                             | Sporting CP              |        45000000
 Jørgen Strand Larsen     | Crystal Palace Football Club                           | Wolves                   |        45000000
 Gianluigi Donnarumma     | Manchester City Football Club                          | Paris Saint Germain      |        45000000
 Angelo Stiller           | Verein für Bewegungsspiele Stuttgart 1893              | VfB Stuttgart            |        45000000
 Castello Lukeba          | RasenBallsport Leipzig                                 | RB Leipzig               |        45000000
 Rayan                    | Association Football Club Bournemouth                  | Vasco DA Gama            |        40000000
 Diogo Costa              | Futebol Clube do Porto                                 | FC Porto                 |        40000000
 Loïs Openda              | Juventus Football Club                                 | RB Leipzig               |        40000000
 Rúben Neves              | Wolverhampton Wanderers Football Club                  | Al-Hilal Saudi FC        |        40000000
 Jarell Quansah           | Bayer 04 Leverkusen Fußball                            | Bayer Leverkusen         |        40000000
 Rodrigo Mora             | Futebol Clube do Porto                                 | FC Porto                 |        40000000
 Giuliano Simeone         | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        40000000
 Mateo Retegui            | Atalanta Bergamasca Calcio S.p.a.                      | Al-Qadisiyah FC          |        40000000
 Fabián Ruiz              | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        40000000
 Said El Mala             | 1. Fußball-Club Köln                                   | 1. FC Köln               |        40000000
 Senny Mayulu             | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        40000000
 Fabinho                  | Liverpool Football Club                                | Al-Ittihad FC            |        38000000
 Ademola Lookman          | Club Atlético de Madrid S.A.D.                         | Atalanta                 |        35000000
 Brennan Johnson          | Crystal Palace Football Club                           | Tottenham                |        35000000
 Edmond Tapsoba           | Bayer 04 Leverkusen Fußball                            | Bayer Leverkusen         |        35000000
 Yéremy Pino              | Crystal Palace Football Club                           | Villarreal               |        35000000
 Lionel Messi             | Paris Saint-Germain Football Club                      | Inter Miami              |        35000000
 Vitor Roque              | Real Betis Balompié S.A.D.                             | Palmeiras                |        35000000
 Francisco Trincão        | Sporting Clube de Portugal                             | Sporting CP              |        35000000
 João Gomes               | Wolverhampton Wanderers Football Club                  | Wolves                   |        35000000
 Conor Gallagher          | Tottenham Hotspur Football Club                        | Atletico Madrid          |        35000000
 Gonçalo Ramos            | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        35000000
 Wesley                   | Associazione Sportiva Roma                             | Flamengo                 |        35000000
 Lucas Chevalier          | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        35000000
 Matías Soulé             | Associazione Sportiva Roma                             | AS Roma                  |        35000000
 Mile Svilar              | Associazione Sportiva Roma                             | AS Roma                  |        35000000
 Christopher Nkunku       | Associazione Calcio Milan                              | AC Milan                 |        32000000
 Bilal El Khannouss       | Verein für Bewegungsspiele Stuttgart 1893              | VfB Stuttgart            |        32000000
 Antonio Nusa             | RasenBallsport Leipzig                                 | RB Leipzig               |        32000000
 Ismael Saibari           | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven            |        32000000
 Ardon Jashari            | Associazione Calcio Milan                              | Club Brugge KV           |        32000000
 Mohamed Amoura           | Verein für Leibesübungen Wolfsburg                     | VfL Wolfsburg            |        32000000
 Alan Varela              | Futebol Clube do Porto                                 | FC Porto                 |        32000000
 Robin Le Normand         | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        30000000
 Johan Manzambi           | Sport-Club Freiburg                                    | SC Freiburg              |        30000000
 Exequiel Palacios        | Bayer 04 Leverkusen Fußball                            | Bayer Leverkusen         |        30000000
 Marquinhos               | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        30000000
 Senne Lammens            | Manchester United Football Club                        | Antwerp                  |        30000000
 Zeno Debast              | Sporting Clube de Portugal                             | Sporting CP              |        30000000
 Oscar Bobb               | Fulham Football Club                                   | Manchester City          |        30000000
 Rômulo                   | RasenBallsport Leipzig                                 | RB Leipzig               |        30000000
 Christos Tzolis          | Club Brugge Koninklijke Voetbalvereniging              | Club Brugge KV           |        30000000
 Victor Froholdt          | Futebol Clube do Porto                                 | FC Porto                 |        30000000
 Dávid Hancko             | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        30000000
 Youssouf Fofana          | Associazione Calcio Milan                              | AC Milan                 |        28000000
 Roger Ibañez             | Associazione Sportiva Roma                             | Al-Ahli Jeddah           |        28000000
 Taty Castellanos         | West Ham United Football Club                          | Lazio                    |        28000000
 Assan Ouédraogo          | RasenBallsport Leipzig                                 | RB Leipzig               |        28000000
 Joel Ordóñez             | Club Brugge Koninklijke Voetbalvereniging              | Club Brugge KV           |        28000000
 Aleksandar Mitrović      | Fulham Football Club                                   | Al-Hilal Saudi FC        |        28000000
 Loïc Badé                | Bayer 04 Leverkusen Fußball                            | Bayer Leverkusen         |        28000000
 Georges Mikautadze       | Villarreal Club de Fútbol S.A.D.                       | Lyon                     |        28000000
 Brajan Gruda             | RasenBallsport Leipzig                                 | RB Leipzig               |        28000000
 Malcom                   | AO FK Zenit Sankt-Peterburg                            | Al-Hilal Saudi FC        |        28000000
 Strahinja Pavlović       | Associazione Calcio Milan                              | AC Milan                 |        28000000
 Dilane Bakwa             | Nottingham Forest Football Club                        | Strasbourg               |        28000000
 Enzo Millot              | Verein für Bewegungsspiele Stuttgart 1893              | Al-Ahli Jeddah           |        28000000
 Joey Veerman             | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven            |        27000000
 Jakub Kiwior             | Futebol Clube do Porto                                 | FC Porto                 |        27000000
 Lorenzo Lucca            | Nottingham Forest Football Club                        | Napoli                   |        25000000
 Otávio                   | Futebol Clube do Porto                                 | Al-Qadisiyah FC          |        25000000
 Donyell Malen            | Associazione Sportiva Roma                             | AS Roma                  |        25000000
 Alexis Saelemaekers      | Associazione Calcio Milan                              | AC Milan                 |        25000000
 Kaishu Sano              | 1. Fußball- und Sportverein Mainz 05                   | FSV Mainz 05             |        25000000
 Arnaud Kalimuendo        | Eintracht Frankfurt Fußball AG                         | Rennes                   |        25000000
 Diego Gómez              | Brighton and Hove Albion Football Club                 | Inter Miami              |        25000000
 Aleksey Batrakov         | Футбольный клуб "Локомотив" Москва                     | Lokomotiv                |        25000000
 Samuele Ricci            | Associazione Calcio Milan                              | AC Milan                 |        25000000
 Sadio Mané               | FC Bayern München                                      | Al-Nassr                 |        25000000
 André                    | Wolverhampton Wanderers Football Club                  | Wolves                   |        25000000
 Mike Maignan             | Associazione Calcio Milan                              | AC Milan                 |        25000000
 João Félix               | Chelsea Football Club                                  | Al-Nassr                 |        25000000
 Johan Bakayoko           | RasenBallsport Leipzig                                 | RB Leipzig               |        25000000
 Equi Fernández           | Bayer 04 Leverkusen Fußball                            | Al-Qadisiyah FC          |        25000000
 Eduard Spertsyan         | FK Krasnodar                                           | FC Krasnodar             |        25000000
 Jamie Leweling           | Verein für Bewegungsspiele Stuttgart 1893              | VfB Stuttgart            |        25000000
 Finn Jeltsch             | Verein für Bewegungsspiele Stuttgart 1893              | VfB Stuttgart            |        25000000
 Brian Brobbey            | Sunderland Association Football Club                   | Ajax                     |        25000000
 Galeno                   | Futebol Clube do Porto                                 | Al-Ahli Jeddah           |        25000000
 Konstantinos Koulierakis | Verein für Leibesübungen Wolfsburg                     | VfL Wolfsburg            |        25000000
 Nico González            | Club Atlético de Madrid S.A.D.                         | Juventus                 |        24000000
 Conrad Harder            | RasenBallsport Leipzig                                 | Sporting CP              |        24000000
 Eliesse Ben Seghir       | Bayer 04 Leverkusen Fußball                            | Monaco                   |        24000000
 Alejandro Grimaldo       | Bayer 04 Leverkusen Fußball                            | Bayer Leverkusen         |        24000000
 Gabri Veiga              | Futebol Clube do Porto                                 | FC Porto                 |        23000000
 Kenneth Taylor           | Società Sportiva Lazio S.p.A.                          | Ajax                     |        23000000
 Roger Fernandes          | Sporting Clube de Braga                                | Al-Ittihad FC            |        22000000
 Igor Jesus               | Nottingham Forest Football Club                        | Botafogo                 |        22000000
 Kingsley Coman           | FC Bayern München                                      | Al-Nassr                 |        22000000
 Chrislain Matsima        | Fußball-Club Augsburg 1907                             | FC Augsburg              |        22000000
 Tyrique George           | Everton Football Club                                  | Chelsea                  |        22000000
 Luis Suárez              | Sporting Clube de Portugal                             | Sporting CP              |        22000000
 Maxi Araújo              | Sporting Clube de Portugal                             | Sporting CP              |        22000000
 Danilo                   | Nottingham Forest Football Club                        | Botafogo                 |        22000000
 Marcos Llorente          | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        22000000
 Jerdy Schouten           | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven            |        22000000
 Álex Jiménez             | Association Football Club Bournemouth                  | AC Milan                 |        22000000
 Christian Kofane         | Bayer 04 Leverkusen Fußball                            | Bayer Leverkusen         |        22000000
 Harvey Elliott           | Aston Villa Football Club                              | Liverpool                |        22000000
 Tolu Arokodare           | Wolverhampton Wanderers Football Club                  | Genk                     |        22000000
 Pedro                    | Associazione Calcio Fiorentina                         | Flamengo                 |        22000000
 Douglas Luiz             | Aston Villa Football Club                              | Nottingham Forest        |        20000000
 Adrien Rabiot            | Associazione Calcio Milan                              | Marseille                |        20000000
 Alexander Sørloth        | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        20000000
 Gabriel Barbosa          | Football Club Internazionale Milano S.p.A.             | Cruzeiro                 |        20000000
 Vanja Milinković-Savić   | Società Sportiva Calcio Napoli                         | Torino                   |        20000000
 Aleix García             | Bayer 04 Leverkusen Fußball                            | Bayer Leverkusen         |        20000000
 Noah Atubolu             | Sport-Club Freiburg                                    | SC Freiburg              |        20000000
 Lucas Hernández          | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        20000000
 Fikayo Tomori            | Associazione Calcio Milan                              | AC Milan                 |        20000000
 David Raum               | RasenBallsport Leipzig                                 | RB Leipzig               |        20000000
 Matteo Gabbia            | Associazione Calcio Milan                              | AC Milan                 |        20000000
 Christoph Baumgartner    | RasenBallsport Leipzig                                 | RB Leipzig               |        20000000
 Tammy Abraham            | Aston Villa Football Club                              | Beşiktaş                 |        20000000
 Deniz Undav              | Verein für Bewegungsspiele Stuttgart 1893              | VfB Stuttgart            |        20000000
 Artem Dovbyk             | Associazione Sportiva Roma                             | AS Roma                  |        20000000
 Florentino               | Burnley Football Club                                  | Benfica                  |        20000000
 Lutsharel Geertruida     | Sunderland Association Football Club                   | RB Leipzig               |        20000000
 Youssef En-Nesyri        | Sevilla Fútbol Club S.A.D.                             | Al-Ittihad FC            |        20000000
 Facundo Medina           | Olympique de Marseille                                 | Lens                     |        20000000
 Koni De Winter           | Associazione Calcio Milan                              | AC Milan                 |        20000000
 Edon Zhegrova            | Juventus Football Club                                 | Lille                    |        20000000
 Fotis Ioannidis          | Sporting Clube de Portugal                             | Sporting CP              |        20000000
 Franjo Ivanović          | Sport Lisboa e Benfica                                 | Union St. Gilloise       |        20000000
 Santiago Gimenez         | Associazione Calcio Milan                              | AC Milan                 |        20000000
 Thiago Almada            | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        20000000
 Rodrigo Zalazar          | Sporting Clube de Braga                                | SC Braga                 |        20000000
 Matvey Kislyak           | PFK CSKA Moskva                                        | CSKA Moscow              |        20000000
 Mohamed Simakan          | RasenBallsport Leipzig                                 | Al-Nassr                 |        20000000
 Marcos Leonardo          | Sport Lisboa e Benfica                                 | Al-Hilal Saudi FC        |        20000000
 Samuel Lino              | Club Atlético de Madrid S.A.D.                         | Flamengo                 |        20000000
 Raphael Onyedika         | Club Brugge Koninklijke Voetbalvereniging              | Club Brugge KV           |        20000000
 Ernest Poku              | Bayer 04 Leverkusen Fußball                            | AZ Alkmaar               |        20000000
 Lucas Beraldo            | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        20000000
 Neil El Aynaoui          | Associazione Sportiva Roma                             | AS Roma                  |        20000000
 Jérémy Jacquet           | Stade Rennais Football Club                            | Rennes                   |        20000000
 Jaydee Canvot            | Crystal Palace Football Club                           | Toulouse                 |        20000000
 Karl Etta Eyong          | Levante Unión Deportiva S.A.D.                         | Villarreal               |        20000000
 Mateus Mané              | Wolverhampton Wanderers Football Club                  | Wolves                   |        20000000
 Emerson Royal            | Tottenham Hotspur Football Club                        | Flamengo                 |        18000000
 Ismaël Doukouré          | Racing Club de Strasbourg Alsace                       | Argentinos JRS           |        18000000
 Cucho Hernández          | Real Betis Balompié S.A.D.                             | Columbus Crew            |        18000000
 Gedson Fernandes         | FK Spartak Moskva                                      | Spartak Moscow           |        18000000
 Maximilian Mittelstädt   | Verein für Bewegungsspiele Stuttgart 1893              | VfB Stuttgart            |        18000000
 Óscar Mingueza           | Real Club Celta de Vigo S. A. D.                       | Celta Vigo               |        18000000
 Renan Lodi               | Olympique de Marseille                                 | Al-Hilal Saudi FC        |        18000000
 Andy Diouf               | Football Club Internazionale Milano S.p.A.             | Lens                     |        18000000
 Nicolò Savona            | Nottingham Forest Football Club                        | Juventus                 |        18000000
 Nathan Zézé              | Football Club de Nantes                                | NEOM                     |        18000000
 Paul Nebel               | 1. Fußball- und Sportverein Mainz 05                   | FSV Mainz 05             |        18000000
 Fábio Vieira             | Hamburger Sport Verein                                 | Hamburger SV             |        18000000
 Nicolas Seiwald          | RasenBallsport Leipzig                                 | RB Leipzig               |        18000000
 Davide Bartesaghi        | Associazione Calcio Milan                              | AC Milan                 |        18000000
 Hamza Igamane            | Lille Olympique Sporting Club                          | Rangers                  |        18000000
 Ezechiel Banzuzi         | RasenBallsport Leipzig                                 | RB Leipzig               |        18000000
 João Palhinha            | Tottenham Hotspur Football Club                        | Bayern München           |        18000000
 Jan Oblak                | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        17000000
 Nadiem Amiri             | 1. Fußball- und Sportverein Mainz 05                   | FSV Mainz 05             |        17000000
 Mauro Júnior             | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven            |        17000000
 Angeliño                 | Associazione Sportiva Roma                             | AS Roma                  |        17000000
 Ryan Flamingo            | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven            |        17000000
 Soungoutou Magassa       | West Ham United Football Club                          | Monaco                   |        17000000
 Rocco Reitz              | Borussia Verein für Leibesübungen 1900 Mönchengladbach | Borussia Mönchengladbach |        17000000
 Timo Werner              | Tottenham Hotspur Football Club                        | RB Leipzig               |        17000000
 Nilson Angulo            | Sunderland Association Football Club                   | Anderlecht               |        17000000
 Merlin Röhl              | Everton Football Club                                  | SC Freiburg              |        16000000
 Yarek Gasiorowski        | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven            |        16000000
 Facundo Buonanotte       | Leeds United Association Football Club                 | Chelsea                  |        16000000
 Gustavo Sá               | Futebol Clube de Famalicão                             | Famalicao                |        16000000
 Yuri Alberto             | AO FK Zenit Sankt-Peterburg                            | Corinthians              |        16000000
 Leon Bailey              | Aston Villa Football Club                              | AS Roma                  |        16000000
 Jonathan Rowe            | Bologna Football Club 1909                             | Marseille                |        16000000
 Fer López                | Real Club Celta de Vigo S. A. D.                       | Celta Vigo               |        16000000
 Yusuf Akçiçek            | Fenerbahçe Spor Kulübü                                 | Al-Hilal Saudi FC        |        16000000
 Francisco Moura          | Futebol Clube do Porto                                 | FC Porto                 |        15000000
 Estéban Lepaul           | Stade Rennais Football Club                            | Angers                   |        15000000
 Nahuel Molina            | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        15000000
 Gastón Álvarez           | Getafe Club de Fútbol S. A. D. Team Dubai              | Al-Qadisiyah FC          |        15000000
 Samuel Chukwueze         | Fulham Football Club                                   | AC Milan                 |        15000000
 Cristiano Ronaldo        | Manchester United Football Club                        | Al-Nassr                 |        15000000
 Tiago Tomás              | Verein für Bewegungsspiele Stuttgart 1893              | VfB Stuttgart            |        15000000
 Matteo Ruggeri           | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        15000000
 Lovro Majer              | Verein für Leibesübungen Wolfsburg                     | VfL Wolfsburg            |        15000000
 Julen Agirrezabala       | Valencia Club de Fútbol S. A. D.                       | Athletic Club            |        15000000
 Guus Til                 | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven            |        15000000
 Rodrigo Gomes            | Wolverhampton Wanderers Football Club                  | Wolves                   |        15000000
 Anders Dreyer            | Royal Sporting Club Anderlecht                         | San Diego                |        15000000
 Aaron Ramsey             | Burnley Football Club                                  | Valencia                 |        15000000
 Francesco Camarda        | Unione Sportiva Lecce                                  | AC Milan                 |        15000000
 Yuito Suzuki             | Sport-Club Freiburg                                    | SC Freiburg              |        15000000
 Matvey Safonov           | Paris Saint-Germain Football Club                      | Paris Saint Germain      |        15000000
 Jeff Chabot              | Verein für Bewegungsspiele Stuttgart 1893              | VfB Stuttgart            |        15000000
 Geny Catamo              | Sporting Clube de Portugal                             | Sporting CP              |        15000000
 Marco Asensio            | Paris Saint-Germain Football Club                      | Fenerbahçe               |        15000000
 Sebastián Driussi        | AO FK Zenit Sankt-Peterburg                            | River Plate              |        15000000
 Carlos Romero            | Reial Club Deportiu Espanyol de Barcelona S.A.D.       | Villarreal               |        15000000
 Josh Brownhill           | Burnley Football Club                                  | Al Shabab                |        15000000
 Uğurcan Çakır            | Galatasaray Spor Kulübü                                | Trabzonspor              |        15000000
 Ludovic Blas             | Stade Rennais Football Club                            | Rennes                   |        15000000
 Carlos Forbs             | Club Brugge Koninklijke Voetbalvereniging              | Club Brugge KV           |        15000000
 Ângelo                   | Racing Club de Strasbourg Alsace                       | Al-Nassr                 |        15000000
 Aleksandar Stanković     | Club Brugge Koninklijke Voetbalvereniging              | Club Brugge KV           |        15000000
 El Chadaille Bitshiabu   | RasenBallsport Leipzig                                 | RB Leipzig               |        15000000
 Gianluca Mancini         | Associazione Sportiva Roma                             | AS Roma                  |        15000000
 Rodrigo De Paul          | Club Atlético de Madrid S.A.D.                         | Inter Miami              |        15000000
 Marc Pubill              | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        15000000
 Andreas Pereira          | Fulham Football Club                                   | Palmeiras                |        15000000
 Djaoui Cissé             | Stade Rennais Football Club                            | Rennes                   |        15000000
 João Simões              | Sporting Clube de Portugal                             | Sporting CP              |        15000000
 Rodrigo Mendoza          | Club Atlético de Madrid S.A.D.                         | Elche                    |        15000000
 Joaquin Seys             | Club Brugge Koninklijke Voetbalvereniging              | Club Brugge KV           |        15000000
 Claudio Echeverri        | Girona Fútbol Club S. A. D.                            | River Plate              |        15000000
 Konstantin Tyukavin      | FK Dinamo Moskva                                       | Dynamo                   |        15000000
 Patrick Wimmer           | Verein für Leibesübungen Wolfsburg                     | VfL Wolfsburg            |        15000000
 Eduardo Quaresma         | Sporting Clube de Portugal                             | Sporting CP              |        15000000
 Karim Benzema            | Real Madrid Club de Fútbol                             | Al-Ittihad FC            |        15000000
 Sven Mijnans             | Alkmaar Zaanstreek                                     | AZ Alkmaar               |        14000000
 Manfred Ugalde           | FK Spartak Moskva                                      | Spartak Moscow           |        14000000
 Esequiel Barco           | FK Spartak Moskva                                      | Spartak Moscow           |        14000000
 Yannick Carrasco         | Club Atlético de Madrid S.A.D.                         | Al Shabab                |        14000000
 José María Giménez       | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        14000000
 Pervis Estupiñán         | Associazione Calcio Milan                              | AC Milan                 |        14000000
 Paul Wanner              | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven            |        14000000
 Dennis Man               | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven            |        13000000
 Nicolò Zaniolo           | Udinese Calcio                                         | Galatasaray              |        13000000
 Sergio Canales           | Real Betis Balompié S.A.D.                             | Monterrey                |        13000000
 Emil Holm                | Juventus Football Club                                 | Bologna                  |        13000000
 Nehuén Pérez             | Futebol Clube do Porto                                 | FC Porto                 |        13000000
 Promise David            | Royale Union Saint-Gilloise                            | Union St. Gilloise       |        13000000
 Ibrahim Osman            | Fodbold Club Nordsjælland                              | Auxerre                  |        12000000
 Kalidou Koulibaly        | Chelsea Football Club                                  | Al-Hilal Saudi FC        |        12000000
 Wouter Goes              | Alkmaar Zaanstreek                                     | AZ Alkmaar               |        12000000
 Breel Embolo             | Stade Rennais Football Club                            | Rennes                   |        12000000
 Aarón Anselmino          | Racing Club de Strasbourg Alsace                       | Boca Juniors             |        12000000
 Alexis Claude-Maurice    | Fußball-Club Augsburg 1907                             | FC Augsburg              |        12000000
 Franck Honorat           | Borussia Verein für Leibesübungen 1900 Mönchengladbach | Borussia Mönchengladbach |        12000000
 Moussa Dembélé           | Olympique Lyonnais                                     | Al-Ettifaq               |        12000000
 Jeanuël Belocian         | Verein für Leibesübungen Wolfsburg                     | Bayer Leverkusen         |        12000000
 Philipp Lienhart         | Sport-Club Freiburg                                    | SC Freiburg              |        12000000
 Quentin Merlin           | Stade Rennais Football Club                            | Rennes                   |        12000000
 Benjamin Henrichs        | RasenBallsport Leipzig                                 | RB Leipzig               |        12000000
 Giovane                  | Società Sportiva Calcio Napoli                         | Hellas Verona            |        12000000
 Martim Fernandes         | Futebol Clube do Porto                                 | FC Porto                 |        12000000
 Alexander Nübel          | Verein für Bewegungsspiele Stuttgart 1893              | VfB Stuttgart            |        12000000
 Marc Guiu                | Chelsea Football Club                                  | Sunderland               |        12000000
 Tim Kleindienst          | Borussia Verein für Leibesübungen 1900 Mönchengladbach | Borussia Mönchengladbach |        12000000
 Anan Khalaili            | Royale Union Saint-Gilloise                            | Union St. Gilloise       |        12000000
 Iván Fresneda            | Sporting Clube de Portugal                             | Sporting CP              |        12000000
 Angel Gomes              | Wolverhampton Wanderers Football Club                  | Marseille                |        12000000
 Hany Mukhtar             | Brøndby Idrætsforening                                 | Nashville SC             |        12000000
 Martin Terrier           | Bayer 04 Leverkusen Fußball                            | Bayer Leverkusen         |        12000000
 Steven Bergwijn          | AFC Ajax Amsterdam                                     | Al-Ittihad FC            |        12000000
 Oskar Pietuszewski       | Futebol Clube do Porto                                 | FC Porto                 |        12000000
 Vini Souza               | Verein für Leibesübungen Wolfsburg                     | VfL Wolfsburg            |        12000000
 Nelson Weiper            | 1. Fußball- und Sportverein Mainz 05                   | FSV Mainz 05             |        12000000
 Mattias Svanberg         | Verein für Leibesübungen Wolfsburg                     | VfL Wolfsburg            |        12000000
 Jan-Carlo Simić          | Royal Sporting Club Anderlecht                         | Al-Ittihad FC            |        12000000
 Anass Salah-Eddine       | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven            |        12000000
 Marshall Munetsi         | Paris Football Club                                    | Paris FC                 |        12000000
 Finn Dahmen              | Fußball-Club Augsburg 1907                             | FC Augsburg              |        12000000
 Zeki Çelik               | Associazione Sportiva Roma                             | AS Roma                  |        12000000
 Niccolò Pisilli          | Associazione Sportiva Roma                             | AS Roma                  |        12000000
 Jackson Tchatchoua       | Wolverhampton Wanderers Football Club                  | Wolves                   |        12000000
 Kamil Grabara            | Verein für Leibesübungen Wolfsburg                     | VfL Wolfsburg            |        12000000
 Robin Hack               | Borussia Verein für Leibesübungen 1900 Mönchengladbach | Borussia Mönchengladbach |        12000000
 Luis Sinisterra          | Association Football Club Bournemouth                  | Cruzeiro                 |        12000000
 Souza                    | Tottenham Hotspur Football Club                        | Santos                   |        12000000
 Kasper Dolberg           | AFC Ajax Amsterdam                                     | Anderlecht               |        12000000
 Riqui Puig               | Futbol Club Barcelona                                  | Los Angeles Galaxy       |        12000000
 Ilias Akhomach           | Rayo Vallecano de Madrid S. A. D.                      | Villarreal               |        12000000
 Lorenz Assignon          | Verein für Bewegungsspiele Stuttgart 1893              | VfB Stuttgart            |        12000000
 Badredine Bouanani       | Verein für Bewegungsspiele Stuttgart 1893              | Nice                     |        12000000
 Yerson Mosquera          | Wolverhampton Wanderers Football Club                  | Wolves                   |        12000000
 Bitello                  | FK Dinamo Moskva                                       | Dynamo                   |        12000000
 Valentín Gómez           | Real Betis Balompié S.A.D.                             | Velez Sarsfield          |        12000000
 Patrick Osterhage        | Sport-Club Freiburg                                    | SC Freiburg              |        12000000
 Sofyan Amrabat           | Real Betis Balompié S.A.D.                             | Fenerbahçe               |        12000000
 Ruben van Bommel         | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven            |        12000000
 Ilan Kebbal              | Paris Football Club                                    | Paris FC                 |        12000000
 Mert Kömür               | Fußball-Club Augsburg 1907                             | FC Augsburg              |        12000000
 Jan Bednarek             | Futebol Clube do Porto                                 | FC Porto                 |        11000000
 Ramón Sosa               | Nottingham Forest Football Club                        | Palmeiras                |        11000000
 Georgios Vagiannidis     | Sporting Clube de Portugal                             | Sporting CP              |        11000000
 Stephen Eustaquio        | Futebol Clube do Porto                                 | FC Porto                 |        11000000
 Antoine Griezmann        | Club Atlético de Madrid S.A.D.                         | Atletico Madrid          |        11000000
(320 rows)

========== STOP — Part 3 only after Pelé confirms ==========
