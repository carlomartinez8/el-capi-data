# Azteca Club Conflicts v3 (Word-Overlap Filter) — Results

**Date:** March 2026  
**Source:** [AZTECA_CLUB_CONFLICTS_V3.md](./AZTECA_CLUB_CONFLICTS_V3.md) — all three parts.

---

## Summary

| Metric | Value |
|--------|--------|
| Real club conflicts (zero word overlap) | **1,770** (down from 2,680 v2) |
| Warehouse players flagged (Part 2a) | 1,770 |
| total_needs_curation after run | 8,927 |
| club_conflict in curation_reason | 1,770 |

Part 1f (sanity): PSG, Atletico Madrid, AC Milan, AS Roma, Sporting CP, RB Leipzig, etc. correctly filtered as same-club naming variants. Part 3: `_extract_club_words` dropped.

---

## Full output

========== Part 1a: Create _extract_club_words ==========
CREATE FUNCTION
========== Part 1b: Build _club_conflicts_v3 (zero word overlap) ==========
psql:../run_club_conflicts_v3.sql:45: NOTICE:  table "_club_conflicts_v3" does not exist, skipping
DROP TABLE
SELECT 1770
========== Part 1c: Real club conflicts count ==========
 real_club_conflicts 
---------------------
                1770
(1 row)

========== Part 1d: High-value conflicts (>10M) ==========
        tm_name         |                        tm_says                         |      apif_says      | tm_market_value 
------------------------+--------------------------------------------------------+---------------------+-----------------
 Lautaro Martínez       | Football Club Internazionale Milano S.p.A.             | Inter               |        85000000
 Estêvão                | Chelsea Football Club                                  | Palmeiras           |        80000000
 Alessandro Bastoni     | Football Club Internazionale Milano S.p.A.             | Inter               |        80000000
 Antoine Semenyo        | Manchester City Football Club                          | Bournemouth         |        75000000
 Darwin Núñez           | Liverpool Football Club                                | Al-Hilal Saudi FC   |        70000000
 Marc Guéhi             | Manchester City Football Club                          | Crystal Palace      |        65000000
 Nick Woltemade         | Newcastle United Football Club                         | VfB Stuttgart       |        65000000
 Nicolò Barella         | Football Club Internazionale Milano S.p.A.             | Inter               |        60000000
 Eberechi Eze           | Arsenal Football Club                                  | Crystal Palace      |        60000000
 Marcus Thuram          | Football Club Internazionale Milano S.p.A.             | Inter               |        60000000
 Theo Hernández         | Associazione Calcio Milan                              | Al-Hilal Saudi FC   |        60000000
 Nico Williams          | Athletic Club Bilbao                                   | Athletic Club       |        60000000
 Moussa Diaby           | Aston Villa Football Club                              | Al-Ittihad FC       |        55000000
 Piero Hincapié         | Arsenal Football Club                                  | Bayer Leverkusen    |        50000000
 Xavi Simons            | Tottenham Hotspur Football Club                        | RB Leipzig          |        50000000
 Federico Dimarco       | Football Club Internazionale Milano S.p.A.             | Inter               |        50000000
 Franco Mastantuono     | Real Madrid Club de Fútbol                             | River Plate         |        50000000
 Ivan Toney             | Brentford Football Club                                | Al-Ahli Jeddah      |        50000000
 Neymar                 | Paris Saint-Germain Football Club                      | Santos              |        50000000
 Gianluigi Donnarumma   | Manchester City Football Club                          | Paris Saint Germain |        45000000
 Jørgen Strand Larsen   | Crystal Palace Football Club                           | Wolves              |        45000000
 Rúben Neves            | Wolverhampton Wanderers Football Club                  | Al-Hilal Saudi FC   |        40000000
 Mateo Retegui          | Atalanta Bergamasca Calcio S.p.a.                      | Al-Qadisiyah FC     |        40000000
 Loïs Openda            | Juventus Football Club                                 | RB Leipzig          |        40000000
 Rayan                  | Association Football Club Bournemouth                  | Vasco DA Gama       |        40000000
 Oihan Sancet           | Athletic Club Bilbao                                   | Athletic Club       |        40000000
 Fabinho                | Liverpool Football Club                                | Al-Ittihad FC       |        38000000
 Ange-Yoan Bonny        | Football Club Internazionale Milano S.p.A.             | Inter               |        35000000
 Lionel Messi           | Paris Saint-Germain Football Club                      | Inter Miami         |        35000000
 Vitor Roque            | Real Betis Balompié S.A.D.                             | Palmeiras           |        35000000
 Conor Gallagher        | Tottenham Hotspur Football Club                        | Atletico Madrid     |        35000000
 Ademola Lookman        | Club Atlético de Madrid S.A.D.                         | Atalanta            |        35000000
 Wesley                 | Associazione Sportiva Roma                             | Flamengo            |        35000000
 João Gomes             | Wolverhampton Wanderers Football Club                  | Wolves              |        35000000
 Yéremy Pino            | Crystal Palace Football Club                           | Villarreal          |        35000000
 Brennan Johnson        | Crystal Palace Football Club                           | Tottenham           |        35000000
 Pio Esposito           | Football Club Internazionale Milano S.p.A.             | Inter               |        35000000
 Yann Bisseck           | Football Club Internazionale Milano S.p.A.             | Inter               |        35000000
 Ardon Jashari          | Associazione Calcio Milan                              | Club Brugge KV      |        32000000
 Ismael Saibari         | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven       |        32000000
 Dani Vivian            | Athletic Club Bilbao                                   | Athletic Club       |        30000000
 Malick Fofana          | Olympique Lyonnais                                     | Lyon                |        30000000
 Mikel Jauregizar       | Athletic Club Bilbao                                   | Athletic Club       |        30000000
 Senne Lammens          | Manchester United Football Club                        | Antwerp             |        30000000
 Oscar Bobb             | Fulham Football Club                                   | Manchester City     |        30000000
 Roger Ibañez           | Associazione Sportiva Roma                             | Al-Ahli Jeddah      |        28000000
 Taty Castellanos       | West Ham United Football Club                          | Lazio               |        28000000
 Dilane Bakwa           | Nottingham Forest Football Club                        | Strasbourg          |        28000000
 Georges Mikautadze     | Villarreal Club de Fútbol S.A.D.                       | Lyon                |        28000000
 Malcom                 | AO FK Zenit Sankt-Peterburg                            | Al-Hilal Saudi FC   |        28000000
 Aleksandar Mitrović    | Fulham Football Club                                   | Al-Hilal Saudi FC   |        28000000
 Davide Frattesi        | Football Club Internazionale Milano S.p.A.             | Inter               |        28000000
 Enzo Millot            | Verein für Bewegungsspiele Stuttgart 1893              | Al-Ahli Jeddah      |        28000000
 Joey Veerman           | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven       |        27000000
 Carlos Augusto         | Football Club Internazionale Milano S.p.A.             | Inter               |        26000000
 Lorenzo Lucca          | Nottingham Forest Football Club                        | Napoli              |        25000000
 Sadio Mané             | FC Bayern München                                      | Al-Nassr            |        25000000
 João Félix             | Chelsea Football Club                                  | Al-Nassr            |        25000000
 Endrick                | Olympique Lyonnais                                     | Lyon                |        25000000
 Brian Brobbey          | Sunderland Association Football Club                   | Ajax                |        25000000
 Diego Gómez            | Brighton and Hove Albion Football Club                 | Inter Miami         |        25000000
 Equi Fernández         | Bayer 04 Leverkusen Fußball                            | Al-Qadisiyah FC     |        25000000
 Arnaud Kalimuendo      | Eintracht Frankfurt Fußball AG                         | Rennes              |        25000000
 Aleksey Batrakov       | Футбольный клуб "Локомотив" Москва                     | Lokomotiv           |        25000000
 Unai Simón             | Athletic Club Bilbao                                   | Athletic Club       |        25000000
 André                  | Wolverhampton Wanderers Football Club                  | Wolves              |        25000000
 Denzel Dumfries        | Football Club Internazionale Milano S.p.A.             | Inter               |        25000000
 Otávio                 | Futebol Clube do Porto                                 | Al-Qadisiyah FC     |        25000000
 Galeno                 | Futebol Clube do Porto                                 | Al-Ahli Jeddah      |        25000000
 Eliesse Ben Seghir     | Bayer 04 Leverkusen Fußball                            | Monaco              |        24000000
 Nico González          | Club Atlético de Madrid S.A.D.                         | Juventus            |        24000000
 Conrad Harder          | RasenBallsport Leipzig                                 | Sporting CP         |        24000000
 Luis Henrique          | Football Club Internazionale Milano S.p.A.             | Inter               |        23000000
 Kenneth Taylor         | Società Sportiva Lazio S.p.A.                          | Ajax                |        23000000
 Jerdy Schouten         | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven       |        22000000
 Álex Jiménez           | Association Football Club Bournemouth                  | AC Milan            |        22000000
 Harvey Elliott         | Aston Villa Football Club                              | Liverpool           |        22000000
 Manuel Akanji          | Football Club Internazionale Milano S.p.A.             | Inter               |        22000000
 Danilo                 | Nottingham Forest Football Club                        | Botafogo            |        22000000
 Roger Fernandes        | Sporting Clube de Braga                                | Al-Ittihad FC       |        22000000
 Igor Jesus             | Nottingham Forest Football Club                        | Botafogo            |        22000000
 Pedro                  | Associazione Calcio Fiorentina                         | Flamengo            |        22000000
 Kingsley Coman         | FC Bayern München                                      | Al-Nassr            |        22000000
 Hakan Çalhanoğlu       | Football Club Internazionale Milano S.p.A.             | Inter               |        22000000
 Tyrique George         | Everton Football Club                                  | Chelsea             |        22000000
 Tolu Arokodare         | Wolverhampton Wanderers Football Club                  | Genk                |        22000000
 Mateus Mané            | Wolverhampton Wanderers Football Club                  | Wolves              |        20000000
 Adrien Rabiot          | Associazione Calcio Milan                              | Marseille           |        20000000
 Gabriel Barbosa        | Football Club Internazionale Milano S.p.A.             | Cruzeiro            |        20000000
 Vanja Milinković-Savić | Società Sportiva Calcio Napoli                         | Torino              |        20000000
 Tammy Abraham          | Aston Villa Football Club                              | Beşiktaş            |        20000000
 Florentino             | Burnley Football Club                                  | Benfica             |        20000000
 Lutsharel Geertruida   | Sunderland Association Football Club                   | RB Leipzig          |        20000000
 Youssef En-Nesyri      | Sevilla Fútbol Club S.A.D.                             | Al-Ittihad FC       |        20000000
 Douglas Luiz           | Aston Villa Football Club                              | Nottingham Forest   |        20000000
 Facundo Medina         | Olympique de Marseille                                 | Lens                |        20000000
 Edon Zhegrova          | Juventus Football Club                                 | Lille               |        20000000
 Franjo Ivanović        | Sport Lisboa e Benfica                                 | Union St. Gilloise  |        20000000
 Mohamed Simakan        | RasenBallsport Leipzig                                 | Al-Nassr            |        20000000
 Marcos Leonardo        | Sport Lisboa e Benfica                                 | Al-Hilal Saudi FC   |        20000000
 Samuel Lino            | Club Atlético de Madrid S.A.D.                         | Flamengo            |        20000000
 Ernest Poku            | Bayer 04 Leverkusen Fußball                            | AZ Alkmaar          |        20000000
 Jérémy Jacquet         | Stade Rennais Football Club                            | Rennes              |        20000000
 Jaydee Canvot          | Crystal Palace Football Club                           | Toulouse            |        20000000
 Karl Etta Eyong        | Levante Unión Deportiva S.A.D.                         | Villarreal          |        20000000
 Hamza Igamane          | Lille Olympique Sporting Club                          | Rangers             |        18000000
 Nicolò Savona          | Nottingham Forest Football Club                        | Juventus            |        18000000
 Cucho Hernández        | Real Betis Balompié S.A.D.                             | Columbus Crew       |        18000000
 Andy Diouf             | Football Club Internazionale Milano S.p.A.             | Lens                |        18000000
 Emerson Royal          | Tottenham Hotspur Football Club                        | Flamengo            |        18000000
 Aitor Paredes          | Athletic Club Bilbao                                   | Athletic Club       |        18000000
 Nathan Zézé            | Football Club de Nantes                                | NEOM                |        18000000
 Renan Lodi             | Olympique de Marseille                                 | Al-Hilal Saudi FC   |        18000000
 Ismaël Doukouré        | Racing Club de Strasbourg Alsace                       | Argentinos JRS      |        18000000
 João Palhinha          | Tottenham Hotspur Football Club                        | Bayern München      |        18000000
 Tyler Morton           | Olympique Lyonnais                                     | Lyon                |        18000000
 Beñat Prados           | Athletic Club Bilbao                                   | Athletic Club       |        18000000
 Ryan Flamingo          | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven       |        17000000
 Mauro Júnior           | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven       |        17000000
 Timo Werner            | Tottenham Hotspur Football Club                        | RB Leipzig          |        17000000
 Soungoutou Magassa     | West Ham United Football Club                          | Monaco              |        17000000
 Nilson Angulo          | Sunderland Association Football Club                   | Anderlecht          |        17000000
 Leon Bailey            | Aston Villa Football Club                              | AS Roma             |        16000000
 Yarek Gasiorowski      | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven       |        16000000
 Facundo Buonanotte     | Leeds United Association Football Club                 | Chelsea             |        16000000
 Yuri Alberto           | AO FK Zenit Sankt-Peterburg                            | Corinthians         |        16000000
 Merlin Röhl            | Everton Football Club                                  | SC Freiburg         |        16000000
 Jonathan Rowe          | Bologna Football Club 1909                             | Marseille           |        16000000
 Yusuf Akçiçek          | Fenerbahçe Spor Kulübü                                 | Al-Hilal Saudi FC   |        16000000
 Marco Asensio          | Paris Saint-Germain Football Club                      | Fenerbahçe          |        15000000
 Guus Til               | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven       |        15000000
 Djaoui Cissé           | Stade Rennais Football Club                            | Rennes              |        15000000
 Rodrigo Gomes          | Wolverhampton Wanderers Football Club                  | Wolves              |        15000000
 Karim Benzema          | Real Madrid Club de Fútbol                             | Al-Ittihad FC       |        15000000
 Andreas Pereira        | Fulham Football Club                                   | Palmeiras           |        15000000
 Francesco Camarda      | Unione Sportiva Lecce                                  | AC Milan            |        15000000
 Rodrigo Mendoza        | Club Atlético de Madrid S.A.D.                         | Elche               |        15000000
 Anders Dreyer          | Royal Sporting Club Anderlecht                         | San Diego           |        15000000
 Claudio Echeverri      | Girona Fútbol Club S. A. D.                            | River Plate         |        15000000
 Aaron Ramsey           | Burnley Football Club                                  | Valencia            |        15000000
 Gastón Álvarez         | Getafe Club de Fútbol S. A. D. Team Dubai              | Al-Qadisiyah FC     |        15000000
 Cristiano Ronaldo      | Manchester United Football Club                        | Al-Nassr            |        15000000
 Konstantin Tyukavin    | FK Dinamo Moskva                                       | Dynamo              |        15000000
 Samuel Chukwueze       | Fulham Football Club                                   | AC Milan            |        15000000
 Carlos Romero          | Reial Club Deportiu Espanyol de Barcelona S.A.D.       | Villarreal          |        15000000
 Estéban Lepaul         | Stade Rennais Football Club                            | Angers              |        15000000
 Sebastián Driussi      | AO FK Zenit Sankt-Peterburg                            | River Plate         |        15000000
 Josh Brownhill         | Burnley Football Club                                  | Al Shabab           |        15000000
 Uğurcan Çakır          | Galatasaray Spor Kulübü                                | Trabzonspor         |        15000000
 Moussa Niakhaté        | Olympique Lyonnais                                     | Lyon                |        15000000
 Ângelo                 | Racing Club de Strasbourg Alsace                       | Al-Nassr            |        15000000
 Ludovic Blas           | Stade Rennais Football Club                            | Rennes              |        15000000
 Julen Agirrezabala     | Valencia Club de Fútbol S. A. D.                       | Athletic Club       |        15000000
 Rodrigo De Paul        | Club Atlético de Madrid S.A.D.                         | Inter Miami         |        15000000
 Paul Wanner            | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven       |        14000000
 Yannick Carrasco       | Club Atlético de Madrid S.A.D.                         | Al Shabab           |        14000000
 Dennis Man             | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven       |        13000000
 Emil Holm              | Juventus Football Club                                 | Bologna             |        13000000
 Sergio Canales         | Real Betis Balompié S.A.D.                             | Monterrey           |        13000000
 Nicolò Zaniolo         | Udinese Calcio                                         | Galatasaray         |        13000000
 Aarón Anselmino        | Racing Club de Strasbourg Alsace                       | Boca Juniors        |        12000000
 Angel Gomes            | Wolverhampton Wanderers Football Club                  | Marseille           |        12000000
 Souza                  | Tottenham Hotspur Football Club                        | Santos              |        12000000
 Riqui Puig             | Futbol Club Barcelona                                  | Los Angeles Galaxy  |        12000000
 Bitello                | FK Dinamo Moskva                                       | Dynamo              |        12000000
 Badredine Bouanani     | Verein für Bewegungsspiele Stuttgart 1893              | Nice                |        12000000
 Ilias Akhomach         | Rayo Vallecano de Madrid S. A. D.                      | Villarreal          |        12000000
 Yerson Mosquera        | Wolverhampton Wanderers Football Club                  | Wolves              |        12000000
 Ruben van Bommel       | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven       |        12000000
 Jan-Carlo Simić        | Royal Sporting Club Anderlecht                         | Al-Ittihad FC       |        12000000
 Sofyan Amrabat         | Real Betis Balompié S.A.D.                             | Fenerbahçe          |        12000000
 Steven Bergwijn        | AFC Ajax Amsterdam                                     | Al-Ittihad FC       |        12000000
 Kasper Dolberg         | AFC Ajax Amsterdam                                     | Anderlecht          |        12000000
 Jackson Tchatchoua     | Wolverhampton Wanderers Football Club                  | Wolves              |        12000000
 Jeanuël Belocian       | Verein für Leibesübungen Wolfsburg                     | Bayer Leverkusen    |        12000000
 Breel Embolo           | Stade Rennais Football Club                            | Rennes              |        12000000
 Moussa Dembélé         | Olympique Lyonnais                                     | Al-Ettifaq          |        12000000
 Marc Guiu              | Chelsea Football Club                                  | Sunderland          |        12000000
 Corentin Tolisso       | Olympique Lyonnais                                     | Lyon                |        12000000
 Hany Mukhtar           | Brøndby Idrætsforening                                 | Nashville SC        |        12000000
 Valentín Gómez         | Real Betis Balompié S.A.D.                             | Velez Sarsfield     |        12000000
 Ibrahim Osman          | Fodbold Club Nordsjælland                              | Auxerre             |        12000000
 Giovane                | Società Sportiva Calcio Napoli                         | Hellas Verona       |        12000000
 Kalidou Koulibaly      | Chelsea Football Club                                  | Al-Hilal Saudi FC   |        12000000
 Luis Sinisterra        | Association Football Club Bournemouth                  | Cruzeiro            |        12000000
 Quentin Merlin         | Stade Rennais Football Club                            | Rennes              |        12000000
 Anass Salah-Eddine     | Eindhovense Voetbalvereniging Philips Sport Vereniging | PSV Eindhoven       |        12000000
 Ramón Sosa             | Nottingham Forest Football Club                        | Palmeiras           |        11000000
(188 rows)

========== Part 1e: Sample lower-value conflicts (30) ==========
        tm_name         |                  tm_says                   |     apif_says     | tm_market_value 
------------------------+--------------------------------------------+-------------------+-----------------
 Christos Mandas        | Association Football Club Bournemouth      | Lazio             |        10000000
 Kévin Danois           | Association de la Jeunesse auxerroise      | Auxerre           |        10000000
 Santiago Bueno         | Wolverhampton Wanderers Football Club      | Wolves            |        10000000
 Cameron Puertas        | Sportverein Werder Bremen von 1899         | Al-Qadisiyah FC   |        10000000
 David Møller Wolfe     | Wolverhampton Wanderers Football Club      | Wolves            |        10000000
 Tommaso Baldanzi       | Genoa Cricket and Football Club            | AS Roma           |        10000000
 Batista Mendy          | Sevilla Fútbol Club S.A.D.                 | Trabzonspor       |        10000000
 Paulinho               | Bayer 04 Leverkusen Fußball                | Palmeiras         |        10000000
 Mahdi Camara           | Stade Rennais Football Club                | Rennes            |        10000000
 Edouard Mendy          | Chelsea Football Club                      | Al-Ahli Jeddah    |        10000000
 Sergey Pinyaev         | Футбольный клуб "Локомотив" Москва         | Lokomotiv         |        10000000
 Fernando               | FC Shakhtar Donetsk                        | RB Bragantino     |        10000000
 Orel Mangala           | Olympique Lyonnais                         | Lyon              |        10000000
 Giovanni Fabbian       | Associazione Calcio Fiorentina             | Bologna           |        10000000
 Memphis Depay          | Club Atlético de Madrid S.A.D.             | Corinthians       |        10000000
 Guilherme Arana        | Atalanta Bergamasca Calcio S.p.a.          | Atletico-MG       |        10000000
 Houssem Aouar          | Associazione Sportiva Roma                 | Al-Ittihad FC     |        10000000
 Hugo Cuypers           | Koninklijke Atletiek Associatie Gent       | Chicago Fire      |        10000000
 Allan Saint-Maximin    | Racing Club de Lens                        | Club America      |        10000000
 João Cancelo           | Futbol Club Barcelona                      | Al-Hilal Saudi FC |        10000000
 Piotr Zieliński        | Football Club Internazionale Milano S.p.A. | Inter             |        10000000
 Matías Viña            | Unione Sportiva Sassuolo Calcio            | Flamengo          |        10000000
 Lilian Brassier        | Stade Rennais Football Club                | Rennes            |        10000000
 Jesús Areso            | Athletic Club Bilbao                       | Athletic Club     |        10000000
 Predrag Rajković       | Real Club Deportivo Mallorca S.A.D.        | Al-Ittihad FC     |        10000000
 Brice Samba            | Stade Rennais Football Club                | Rennes            |        10000000
 Ainsley Maitland-Niles | Olympique Lyonnais                         | Lyon              |        10000000
 Iñaki Williams         | Athletic Club Bilbao                       | Athletic Club     |        10000000
 Berke Özer             | Lille Olympique Sporting Club              | Eyüpspor          |        10000000
 Valentín Carboni       | Olympique de Marseille                     | Inter             |        10000000
(30 rows)

========== Part 1f: Sanity — filtered out by word overlap (v2 had, v3 dropped) ==========
        tm_name        |                  tm_says                  |      apif_says      |            tm_words             |      apif_words       | tm_market_value 
-----------------------+-------------------------------------------+---------------------+---------------------------------+-----------------------+-----------------
 Vitinha               | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |       110000000
 João Neves            | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |       110000000
 Julián Alvarez        | Club Atlético de Madrid S.A.D.            | Atletico Madrid     | {atletico,madrid}               | {atletico,madrid}     |       100000000
 Ousmane Dembélé       | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |       100000000
 Désiré Doué           | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |        90000000
 Khvicha Kvaratskhelia | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |        90000000
 Achraf Hakimi         | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |        80000000
 Nuno Mendes           | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |        75000000
 Bradley Barcola       | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |        70000000
 Willian Pacho         | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |        70000000
 Rafael Leão           | Associazione Calcio Milan                 | AC Milan            | {milan}                         | {milan}               |        70000000
 Pablo Barrios         | Club Atlético de Madrid S.A.D.            | Atletico Madrid     | {atletico,madrid}               | {atletico,madrid}     |        60000000
 Álex Baena            | Club Atlético de Madrid S.A.D.            | Atletico Madrid     | {atletico,madrid}               | {atletico,madrid}     |        55000000
 Warren Zaïre-Emery    | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |        50000000
 Morten Hjulmand       | Sporting Clube de Portugal                | Sporting CP         | {sporting,clube,portugal}       | {sporting}            |        50000000
 Manu Koné             | Associazione Sportiva Roma                | AS Roma             | {roma}                          | {roma}                |        50000000
 Ilya Zabarnyi         | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |        50000000
 Castello Lukeba       | RasenBallsport Leipzig                    | RB Leipzig          | {rasenballsport,leipzig}        | {leipzig}             |        45000000
 Angelo Stiller        | Verein für Bewegungsspiele Stuttgart 1893 | VfB Stuttgart       | {fur,bewegungsspiele,stuttgart} | {vfb,stuttgart}       |        45000000
 Gonçalo Inácio        | Sporting Clube de Portugal                | Sporting CP         | {sporting,clube,portugal}       | {sporting}            |        45000000
 Giuliano Simeone      | Club Atlético de Madrid S.A.D.            | Atletico Madrid     | {atletico,madrid}               | {atletico,madrid}     |        40000000
 Jarell Quansah        | Bayer 04 Leverkusen Fußball               | Bayer Leverkusen    | {bayer,leverkusen}              | {bayer,leverkusen}    |        40000000
 Diogo Costa           | Futebol Clube do Porto                    | FC Porto            | {futebol,clube,porto}           | {porto}               |        40000000
 Rodrigo Mora          | Futebol Clube do Porto                    | FC Porto            | {futebol,clube,porto}           | {porto}               |        40000000
 Fabián Ruiz           | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |        40000000
 Senny Mayulu          | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |        40000000
 Said El Mala          | 1. Fußball-Club Köln                      | 1. FC Köln          | {koln}                          | {koln}                |        40000000
 Mile Svilar           | Associazione Sportiva Roma                | AS Roma             | {roma}                          | {roma}                |        35000000
 Edmond Tapsoba        | Bayer 04 Leverkusen Fußball               | Bayer Leverkusen    | {bayer,leverkusen}              | {bayer,leverkusen}    |        35000000
 Lucas Chevalier       | Paris Saint-Germain Football Club         | Paris Saint Germain | {paris,saint,germain}           | {paris,saint,germain} |        35000000
(30 rows)

========== Part 2a: Flag real conflicts in warehouse ==========
UPDATE 1770
========== Part 2b: Curation breakdown ==========
 total_needs_curation | club_conflict | post_load_dup | multi_match_ambiguous | missing_fields | orphan_initial_only 
----------------------+---------------+---------------+-----------------------+----------------+---------------------
                 8927 |          1770 |            16 |                    67 |           2793 |                4282
(1 row)

========== Part 3: Drop helper function ==========
DROP FUNCTION
========== DONE ==========
