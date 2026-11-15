# Audio: textos de las 19 pistas (cinco de cada misión, contrato revisión 8)

**Estado:** los 19 audios los volvió a grabar el equipo el 15-11-2026 hacia las 14:20 CET (voz Matilda, modelo eleven_multilingual_v2, según el equipo) con los textos de `0486ad9` y un único cambio decidido por el delegado del líder: rover_1 ya no nombra Gjoa Haven, a 1.116 km (regla general: más allá de 300 km no se nombra el lugar). ZIP SHA256 `cc9699eb9742cedc95f4161b60a0bf2aab9ad2013e25830392311e1922330c35`; subidos sin modificar a la rama `audio-assets` (commit `6650a13`). Nada pendiente: `app/public/audio/pending.json` está vacío y cada MP3 dice el texto «Ahora» de abajo (los hashes de los 19 coinciden con `SHA256SUMS.txt` del commit grabado).

Generado por `tierra luna/tools/make_audio_top5.py` desde el paquete `app/public/data/v2` (revisión 8, motor 3.4.0); hechos y comprobaciones en `docs/AUDIO_TOP5.json`. Texto antiguo = `transcripts.json` del commit `d24ebb3` (lo que decía la grabación anterior); texto grabado ahora = `transcripts.json` del commit `6650a13` (rama `audio-assets`). Ningún audio se ha generado, editado, renombrado ni borrado aquí; los MP3 y `SHA256SUMS.txt` son los del equipo, copiados byte a byte.

Las cifras se dicen como las imprime la web (`app/src/flow/dom.ts` `valueText`, `fixed`; números de la frase de cada pareja con `engine/display.py`); las distancias se redondean una sola vez desde el valor guardado. El script comprueba cada número de cada texto contra la pantalla, el número de palabras (55 a 105) y las frases prohibidas.

## Las 19 pistas

### 00_welcome.mp3

- **Antes:** Welcome to Stars Beside You, a planetary twin finder. Before a rover, a solar panel or a lunar base ever reaches the Moon, it can be tested here on Earth, if we find the right place. We compare lunar data from NASA missions with data from all over the Earth, and look for the places that match on what matters most for each mission. There are three missions. Press one for the Rover, where slope and roughness decide everything. Press two for Solar Panels, where sunlight is the key. Press three for the Lunar Base, where temperature and its daily swing matter most.
- **Ahora:** Welcome to Stars Beside You, a planetary twin finder. Before a rover, a solar panel or a lunar base ever reaches the Moon, it can be tested here on Earth, if we find the right place. We compare lunar data from NASA missions with data from all over the Earth, and look for a lunar twin for each Earth site. There are three missions. Press one for the Rover, matched on slope and roughness. Press two for Solar panels, matched mainly on sunlight. Press three for the Lunar base, matched mainly on the coldest temperature and the daily swing.
- **Motivo:** Base lunar se emparejaba por 'temperature'; ahora se dice lo que se compara: el frío y su oscilación diaria (posición térmica); cada misión con su criterio.
- Palabras: 99.

### m1_rover.mp3

- **Antes:** Rover. A rover's journey depends on the ground beneath its wheels, so we match places by slope and surface roughness. On the Moon, we search near the south pole, where NASA plans to look for water ice. All five analogs share the same lunar twin: gently sloping ground at 76.5 degrees south, about 160 kilometers from Casatus crater. Here are the five best analogs on Earth. Press a number from one to five to hear about each one, or press Escape to go back.
- **Ahora:** Rover. We match places on slope and roughness only. On the Moon we search the south polar region, from 75 degrees south to the pole, where NASA plans to look for water ice. Almost every site differs from its lunar twin by less than the elevation data can measure, so the likeness cannot tell them apart; 254 of them also get full marks, or nearly, on our Rover criteria. Here are five of the 254 sites tied at the top of our model, chosen to be spread across the world. Press one to five to hear each one, or Escape to go back.
- **Motivo:** Rover ya no comparte un único gemelo (Casatus) y decía 'the five best'; ahora: solo pendiente y rugosidad, empate de 254 sitios en lo más alto (los cinco, repartidos por el mundo, entre los 241 sin hielo ni agua).
- Palabras: 103.

### m2_solar.mp3

- **Antes:** Solar Panels. A solar panel lives on sunlight, so we match places by how much solar energy arrives each day at the top of the atmosphere, before the air absorbs any of it. On the Moon, we search the low, flat plains near the equator, called the maria, where the Sun climbs high. Here are the five best analogs on Earth. Press a number from one to five to hear about each one, or press Escape to go back.
- **Ahora:** Solar panels. A solar panel lives on sunlight, so we match mainly on the sunlight that arrives each day above the atmosphere. On the Moon we search the low, flat maria within 30 degrees of the equator, where the Sun stands high. Here are five of the highest-scoring analogs in our model, ordered by the final score: half likeness and half suitability. Almost every top site matches its twin's sunlight almost exactly, so the likeness is nearly the same for all of them, and suitability, led by clear skies, decides the order. Press one to five to hear each one, or Escape to go back.
- **Motivo:** Decía 'the five best'; ahora 'five of the highest-scoring analogs in our model', el orden por el final y la nota honesta: la similitud casi igual, decide la idoneidad (cielo despejado).
- Palabras: 105.

### m3_base.mp3

- **Antes:** Lunar Base. A base has to survive the cold, and the swing between day and night, so we match places by temperature and daily temperature range. Nowhere on Earth is as cold as the Moon, so we compare how each place ranks within its own world: the coldest, steadiest sites on Earth, against the coldest cells in NASA's nine candidate regions near the lunar south pole. Here are the five best analogs. Press a number from one to five to hear about each one, or press Escape to go back.
- **Ahora:** Lunar base. A base must endure the cold, so we match mainly on the coldest temperature and the daily swing. On the Moon we search NASA's nine candidate landing regions in the south polar region, where NASA plans crewed landings. The Moon is far colder than Earth, so we compare position, not temperature: how each site ranks among Earth's 2,419 candidates, and its twin among the 280 lunar cells of those regions. Here are five of the highest-scoring analogs in our model, ordered by the final score: half likeness and half suitability. Press one to five to hear each one, or Escape to go back.
- **Motivo:** Decía 'the five best' y comparaba 'temperature'; ahora posición, no temperatura, poblaciones de 2.419 y 280, y el orden por el final.
- Palabras: 105.

### rover_1.mp3

- **Antes:** Rover, analog one. About 66 kilometers northwest of Bayinbaolige, in Inner Mongolia, China. Like its lunar twin near Casatus crater, the ground slopes gently, by about one degree. The slope is 1.04 degrees on Earth and 1.15 degrees on the Moon, and the surface roughness is about 44 meters in both. Their height above each world's average level differs by 96 meters. Similarity: 99.57 percent.
- **Ahora:** Rover, analog one. A site in Canada, at 78.5 degrees north and 102.5 degrees west. Its lunar twin lies about 69 kilometers from the crater Sverdrup. The slope is 0.77 degrees on Earth and 0.793 on the Moon; the roughness is 29.34 meters on Earth and 29.5 on the Moon. Similarity: 100 out of 100. It is one of the 254 sites tied at the top: it matches its twin within what the elevation data can measure, and it gets full marks on our Rover criteria.
- **Motivo:** Los cinco de Rover son nuevos (regla de dispersión entre los empatados): lugar, gemelo, pendiente y rugosidad nuevos; sin elevación; dice que es uno de los 254 empatados en lo más alto.
- Palabras: 86.

### rover_2.mp3

- **Antes:** Rover, analog two. About 80 kilometers north of Tamanrasset, in Algeria. Like its lunar twin near Casatus crater, the ground slopes gently, by about one degree. The slope is 1.22 degrees on Earth and 1.15 degrees on the Moon, and the surface roughness is about 43 meters on Earth and 44 on the Moon. Their height above each world's average level differs by 71 meters. Similarity: 99.76 percent.
- **Ahora:** Rover, analog two. A site in Santa Cruz, Argentina, about 71 kilometers southwest of Comandante Luis Piedra Buena. Its lunar twin lies about 51 kilometers from the crater Zeeman. The slope is 0.722 degrees on Earth and 0.739 on the Moon; the roughness is 29.16 meters on Earth and 30.62 on the Moon. Similarity: 100 out of 100. It is one of the 254 sites tied at the top: it matches its twin within what the elevation data can measure, and it gets full marks on our Rover criteria.
- **Motivo:** Los cinco de Rover son nuevos (regla de dispersión entre los empatados): lugar, gemelo, pendiente y rugosidad nuevos; sin elevación; dice que es uno de los 254 empatados en lo más alto.
- Palabras: 89.

### rover_3.mp3

- **Antes:** Rover, analog three. About 78 kilometers northeast of Ehen Hudag, in Inner Mongolia, China. Like its lunar twin near Casatus crater, the ground slopes gently, by about one degree. The slope is 0.91 degrees on Earth and 1.15 degrees on the Moon, and the surface roughness is 39 meters on Earth and 44 on the Moon. Their height above each world's average level differs by 86 meters. Similarity: 98.77 percent.
- **Ahora:** Rover, analog three. A site in South Australia, Australia, about 81 kilometers northeast of Peterborough. Its lunar twin lies about 24 kilometers from the crater Schrodinger. The slope is 0.547 degrees on Earth and 0.547 on the Moon; the roughness is 18.18 meters on Earth and 15.66 on the Moon. Similarity: 100 out of 100. It is one of the 254 sites tied at the top: it matches its twin within what the elevation data can measure, and it gets full marks on our Rover criteria.
- **Motivo:** Los cinco de Rover son nuevos (regla de dispersión entre los empatados): lugar, gemelo, pendiente y rugosidad nuevos; sin elevación; dice que es uno de los 254 empatados en lo más alto.
- Palabras: 86.

### rover_4.mp3

- **Antes:** Rover, analog four. About 28 kilometers northeast of Banqiao, in Gansu, China. Like its lunar twin near Casatus crater, the ground slopes gently, by about one degree. The slope is 1.13 degrees on Earth and 1.15 degrees on the Moon, almost the same, and the surface roughness is 49 meters on Earth and 44 on the Moon. Their height above each world's average level differs by only 18 meters. Similarity: 99.5 percent.
- **Ahora:** Rover, analog four. A site in Al Mahrah, Yemen, about 90 kilometers north of Dahasuways. Its lunar twin lies about 68 kilometers from the crater Haynes. The slope is 0.643 degrees on Earth and 0.677 on the Moon; the roughness is 21.87 meters on Earth and 19.22 on the Moon. Similarity: 100 out of 100. It is one of the 254 sites tied at the top: it matches its twin within what the elevation data can measure, and it gets full marks on our Rover criteria.
- **Motivo:** Los cinco de Rover son nuevos (regla de dispersión entre los empatados): lugar, gemelo, pendiente y rugosidad nuevos; sin elevación; dice que es uno de los 254 empatados en lo más alto.
- Palabras: 86.

### rover_5.mp3

- **Antes:** Rover, analog five. About 41 kilometers southeast of Buga, in Govi-Altay, Mongolia. Like its lunar twin near Casatus crater, the ground slopes gently, by about one degree. The slope is 1.24 degrees on Earth and 1.15 degrees on the Moon, and the surface roughness is 41 meters on Earth and 44 on the Moon. Their height above each world's average level differs by 129 meters. Similarity: 99.12 percent.
- **Ahora:** Rover, analog five. A site in Assaba, Mauritania, about 96 kilometers north of Barkewol. Its lunar twin lies about 29 kilometers from the crater Drygalski. The slope is 0.523 degrees on Earth and 0.51 on the Moon; the roughness is 26.42 meters on Earth and 26.8 on the Moon. Similarity: 100 out of 100. It is one of the 254 sites tied at the top: it matches its twin within what the elevation data can measure, and it gets full marks on our Rover criteria.
- **Motivo:** Los cinco de Rover son nuevos (regla de dispersión entre los empatados): lugar, gemelo, pendiente y rugosidad nuevos; sin elevación; dice que es uno de los 254 empatados en lo más alto.
- Palabras: 85.

### solar_1.mp3

- **Antes:** Solar Panels, analog one. About 130 kilometers northeast of Derby, in Western Australia. Its lunar twin lies 76 kilometers from Huxley crater. Above the atmosphere, both receive 9.6 kilowatt-hours of sunlight per square meter each day, and their slope and roughness are almost the same. But on Earth the air takes its share: only 6.2 kilowatt-hours reach the ground, 35 percent less. Similarity: 99.99 percent.
- **Ahora:** Solar panels, analog one. A site in Menabe, Madagascar, about 19 kilometers southeast of Manja. Its lunar twin lies about 38 kilometers from the crater Timocharis. Above the atmosphere, the site gets 9.3 kilowatt hours per square meter a day, and its twin 9.4. But only 5.7 of them reach the ground here: 39 percent is lost in the air, and the Moon has no air. On average, satellites see about two thirds of the sky over the site clear of clouds, a clear-sky fraction of 0.675. Similarity: 99.83 out of 100.
- **Motivo:** Los cinco de Paneles solares son nuevos (idoneidad con cielo despejado ISCCP y regla de los cinco): lugar, gemelo, luz, suelo, parte perdida, cielo despejado y similitud nuevos.
- Palabras: 92.

### solar_2.mp3

- **Antes:** Solar Panels, analog two. About 280 kilometers northeast of Derby, in Western Australia. Its lunar twin lies 58 kilometers from Struve crater. Above the atmosphere, both receive about 9.6 kilowatt-hours of sunlight per square meter each day. But on Earth the air takes its share: only 6.1 kilowatt-hours reach the ground, 36 percent less. Similarity: 99.88 percent.
- **Ahora:** Solar panels, analog two. A site in Nugaal, Somalia, about 64 kilometers southwest of Eyl. Its lunar twin lies about 84 kilometers from the crater Bessarion. Above the atmosphere, both get 9.9 kilowatt hours per square meter a day. But only 6.2 of them reach the ground here: 37 percent is lost in the air, and the Moon has no air. On average, satellites see about seven tenths of the sky over the site clear of clouds, a clear-sky fraction of 0.705. Similarity: 99.97 out of 100.
- **Motivo:** Los cinco de Paneles solares son nuevos (idoneidad con cielo despejado ISCCP y regla de los cinco): lugar, gemelo, luz, suelo, parte perdida, cielo despejado y similitud nuevos.
- Palabras: 87.

### solar_3.mp3

- **Antes:** Solar Panels, analog three. About 80 kilometers northeast of Maintirano, in Madagascar. Its lunar twin lies 61 kilometers from Thebit crater. Above the atmosphere, both receive about 9.5 kilowatt-hours of sunlight per square meter each day. But on Earth the air takes its share: only 6 kilowatt-hours reach the ground, 38 percent less. Similarity: 99.95 percent.
- **Ahora:** Solar panels, analog three. A site in Sindh, Pakistan, about 29 kilometers northeast of Jati. Its lunar twin lies about 58 kilometers from the crater Banting. Above the atmosphere, the site gets 9.2 kilowatt hours per square meter a day, and its twin 9.1. But only 5.6 of them reach the ground here: 39 percent is lost in the air, and the Moon has no air. On average, satellites see about two thirds of the sky over the site clear of clouds, a clear-sky fraction of 0.662. Similarity: 99.93 out of 100.
- **Motivo:** Los cinco de Paneles solares son nuevos (idoneidad con cielo despejado ISCCP y regla de los cinco): lugar, gemelo, luz, suelo, parte perdida, cielo despejado y similitud nuevos.
- Palabras: 92.

### solar_4.mp3

- **Antes:** Solar Panels, analog four. About 280 kilometers northwest of Kununurra, in Western Australia. Its lunar twin lies 72 kilometers from Dziewulski crater. Above the atmosphere, both receive about 9.7 kilowatt-hours of sunlight per square meter each day. But on Earth the air takes its share: only 6.1 kilowatt-hours reach the ground, 37 percent less. Similarity: 99.98 percent.
- **Ahora:** Solar panels, analog four. A site in Ethiopia, at 7.5 degrees north and 46.5 degrees east, about 131 kilometers northwest of Gaalkacyo in Somalia. Its lunar twin lies about 179 kilometers from Rima Marius, a lunar rille. Above the atmosphere, both get 9.9 kilowatt hours per square meter a day. But only 6.1 of them reach the ground here: 38 percent is lost in the air, and the Moon has no air. On average, satellites see about two thirds of the sky over the site clear of clouds, a clear-sky fraction of 0.677. Similarity: 99.97 out of 100.
- **Motivo:** Los cinco de Paneles solares son nuevos (idoneidad con cielo despejado ISCCP y regla de los cinco): lugar, gemelo, luz, suelo, parte perdida, cielo despejado y similitud nuevos.
- Palabras: 98.

### solar_5.mp3

- **Antes:** Solar Panels, analog five. About 220 kilometers northeast of Derby, in Western Australia. Its lunar twin lies 83 kilometers from Rimae Pettit, a system of lunar fissures. Above the atmosphere, both receive 9.6 kilowatt-hours of sunlight per square meter each day. But on Earth the air takes its share: only 6.1 kilowatt-hours reach the ground, 36 percent less. Similarity: 100 percent.
- **Ahora:** Solar panels, analog five. A site in Bari, Somalia, about 38 kilometers northeast of Iskushuban. Its lunar twin lies about 95 kilometers from Catena Dziewulski, a chain of craters. Above the atmosphere, both get 9.8 kilowatt hours per square meter a day. But only 6.3 of them reach the ground here: 36 percent is lost in the air, and the Moon has no air. On average, satellites see about four fifths of the sky over the site clear of clouds, a clear-sky fraction of 0.792. Similarity: 99.94 out of 100.
- **Motivo:** Los cinco de Paneles solares son nuevos (idoneidad con cielo despejado ISCCP y regla de los cinco): lugar, gemelo, luz, suelo, parte perdida, cielo despejado y similitud nuevos.
- Palabras: 90.

### base_1.mp3

- **Antes:** Lunar Base, analog one. About 62 kilometers north of Aheqi, in Xinjiang, China. Its lunar twin lies 25 kilometers from Mons Malapert, in NASA's Haworth candidate region. They are not equally cold: the Moon's minimum is about 207 kelvin lower. What matches is their place in their own worlds: both rank near the 8th percentile for minimum temperature, their daily temperature swings rank close too, and the terrain is alike, with slopes of about 7 degrees. Similarity: 97.31 percent.
- **Ahora:** Lunar base, analog one. A site in Souss-Massa-Draa, Morocco, about 4 kilometers southeast of Tinghir. Its lunar twin lies about 18 kilometers from the crater Wapowski, at the edge of NASA's Nobile Rim 2 candidate region. The likeness is of position, not temperature: its twin's coldest temperature is 208.6 kelvin lower. Among the candidates of each world, the coldest temperature ranks at percentile 62.7 on Earth and 62.7 on the Moon, and the daily swings rank close, at 41.9 and 43.4. The slopes are close enough for our model: 3.257 degrees on Earth and 3.481 on the Moon. Similarity: 99.36 out of 100.
- **Motivo:** Los cinco de Base lunar son nuevos (idoneidad corregida y regla de los cinco): lugar, gemelo, frase de región de la NASA ('at the edge of'), kelvin, percentiles y similitud nuevos.
- Palabras: 103.

### base_2.mp3

- **Antes:** Lunar Base, analog two. About 44 kilometers southeast of Mori, in Xinjiang, China. Its lunar twin lies 16 kilometers from Cartwright crater, in NASA's de Gerlache Rim 2 candidate region. They are not equally cold: the Moon's minimum is about 208 kelvin lower. What matches is their place in their own worlds: for minimum temperature, they rank at the 21st and 19th percentile, and their daily temperature swings rank almost the same. Similarity: 96.61 percent.
- **Ahora:** Lunar base, analog two. A site in Xinjiang Uygur Zizhiqu, China, about 62 kilometers north of Aheqi. Its lunar twin lies about 25 kilometers from Mons Malapert, at the edge of NASA's Haworth candidate region. The likeness is of position, not temperature: its twin's coldest temperature is 207.4 kelvin lower. Among the candidates of each world, the coldest temperature ranks at percentile 8.4 on Earth and 8.0 on the Moon, and the daily swings rank close, at 6.7 and 10.2. The slopes are close enough for our model: 6.652 degrees on Earth and 7.179 on the Moon. Similarity: 97.31 out of 100.
- **Motivo:** Los cinco de Base lunar son nuevos (idoneidad corregida y regla de los cinco): lugar, gemelo, frase de región de la NASA ('at the edge of'), kelvin, percentiles y similitud nuevos.
- Palabras: 102.

### base_3.mp3

- **Antes:** Lunar Base, analog three. About 46 kilometers north of Burenhayrhan, in Hovd, Mongolia. Its lunar twin lies 19 kilometers from Slater crater, in NASA's Slater Plain candidate region. They are not equally cold: the Moon's minimum is about 207 kelvin lower. What matches is their place in their own worlds: both rank near the 6th and 7th percentile for minimum temperature, and their daily temperature swings rank close too. Similarity: 96.86 percent.
- **Ahora:** Lunar base, analog three. A site in Fars, Iran, about 18 kilometers east of Kherameh. Its lunar twin lies about 14 kilometers from the crater Wapowski, at the edge of NASA's Nobile Rim 2 candidate region. The likeness is of position, not temperature: its twin's coldest temperature is 208.2 kelvin lower. Among the candidates of each world, the coldest temperature ranks at percentile 62.9 on Earth and 64.1 on the Moon, and the daily swings rank close, at 59.5 and 54.8. The slopes are close enough for our model: 3.738 degrees on Earth and 5.053 on the Moon. Similarity: 92.50 out of 100.
- **Motivo:** Los cinco de Base lunar son nuevos (idoneidad corregida y regla de los cinco): lugar, gemelo, frase de región de la NASA ('at the edge of'), kelvin, percentiles y similitud nuevos.
- Palabras: 103.

### base_4.mp3

- **Antes:** Lunar Base, analog four. About 4 kilometers southeast of Tinghir, in Morocco. Its lunar twin lies 18 kilometers from Wapowski crater, in NASA's Nobile Rim 2 candidate region. They are not equally cold: the Moon's minimum is about 209 kelvin lower. What matches is their place in their own worlds: both rank at the 63rd percentile for minimum temperature, and their daily temperature swings rank close too. Similarity: 99.36 percent.
- **Ahora:** Lunar base, analog four. A site in Xinjiang Uygur Zizhiqu, China, about 27 kilometers southeast of Waxxari. Its lunar twin lies about 49 kilometers from Mons Mouton, at the edge of NASA's Mons Mouton Plateau candidate region. The likeness is of position, not temperature: its twin's coldest temperature is 202.9 kelvin lower. Among the candidates of each world, the coldest temperature ranks at percentile 27.8 on Earth and 34.1 on the Moon, and the daily swings rank close, at 80.1 and 77.7. Similarity: 83.98 out of 100.
- **Motivo:** Los cinco de Base lunar son nuevos (idoneidad corregida y regla de los cinco): lugar, gemelo, frase de región de la NASA ('at the edge of'), kelvin, percentiles y similitud nuevos.
- Palabras: 87.

### base_5.mp3

- **Antes:** Lunar Base, analog five. About 53 kilometers south of Ewirgol, in Xinjiang, China. Its lunar twin lies 16 kilometers from Oberbeck crater, in NASA's Nobile Rim 2 candidate region. They are not equally cold: the Moon's minimum is about 208 kelvin lower. What matches is their place in their own worlds: for minimum temperature, they rank at the 23rd and 22nd percentile, and their daily temperature swings rank close too. Similarity: 95.03 percent.
- **Ahora:** Lunar base, analog five. A site in Semnan, Iran, about 28 kilometers north of Aradan. Its lunar twin lies about 49 kilometers from the crater Slater, at the edge of NASA's Slater Plain candidate region. The likeness is of position, not temperature: its twin's coldest temperature is 207.4 kelvin lower. Among the candidates of each world, the coldest temperature ranks at percentile 53.0 on Earth and 54.8 on the Moon, and the daily swings rank close, at 55.1 and 51.3. The slopes are close enough for our model: 4.198 degrees on Earth and 5.547 on the Moon. Similarity: 93.33 out of 100.
- **Motivo:** Los cinco de Base lunar son nuevos (idoneidad corregida y regla de los cinco): lugar, gemelo, frase de región de la NASA ('at the edge of'), kelvin, percentiles y similitud nuevos.
- Palabras: 102.

## Los cinco de cada misión

Coordenadas = centro de la celda de 1°. Puesto = puesto en la clasificación completa. Distancias redondeadas una vez.

### Rover

Regla de los cinco (`spread_within_top_tie`): 254 ranked sites share the top published final score 100.00; 241 remain after the ice and water skips. The five are a farthest-point spread among those 241 (they all have the top score, so 'five of the highest-scoring' is not the wording: 'five of the 254 sites tied at the top of our model', as the bundle's list_order_rover text says; all five are also among the 241 left after the skips).

| # | Lugar | Coordenadas | Puesto | Gemelo (rasgo, km) | Pendiente T / L (°) | Rugosidad T / L (m) | Sim. | Final |
|---|---|---|---|---|---|---|---|---|
| 1 | Canada: 1,116 km north de Gjoa Haven (dato; el audio no lo dice: más de 300 km, da país y coordenadas) | 78.5° N, 102.5° W | 3 | Sverdrup, 69 km | 0.77 / 0.793 | 29.34 / 29.5 | 100.00 | 100.00 |
| 2 | Santa Cruz, Argentina: 71 km southwest de Comandante Luis Piedra Buena | 50.5° S, 69.5° W | 254 | Zeeman, 51 km | 0.722 / 0.739 | 29.16 / 30.62 | 100.00 | 100.00 |
| 3 | South Australia, Australia: 81 km northeast de Peterborough | 32.5° S, 139.5° E | 251 | Schrodinger, 24 km | 0.547 / 0.547 | 18.18 / 15.66 | 100.00 | 100.00 |
| 4 | Al Mahrah, Yemen: 90 km north de Dahasuways | 16.5° N, 50.5° E | 241 | Haynes, 68 km | 0.643 / 0.677 | 21.87 / 19.22 | 100.00 | 100.00 |
| 5 | Assaba, Mauritania: 96 km north de Barkewol | 17.5° N, 12.5° W | 236 | Drygalski, 29 km | 0.523 / 0.51 | 26.42 / 26.8 | 100.00 | 100.00 |

### Solar panels

Regla de los cinco (`rank_with_skips`): The five are ranks 1, 2, 5, 7, 9 of the full ranking; every rank above the fifth that is not among them is skipped by the rule (rank 3: within 2 degrees of arc of E40184 (1.36 degrees); rank 4: within 2 degrees of arc of E40184 (2.00 degrees); rank 6: within 2 degrees of arc of E29749 (1.98 degrees); rank 8: within 2 degrees of arc of E29746 (1.41 degrees)), so they are the highest-scoring five that the rule of the five allows.

| # | Lugar | Coordenadas | Puesto | Gemelo (rasgo, km) | Luz sobre la atmósfera T / L | Suelo T, perdida | Cielo despejado | Sim. | Final |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Menabe, Madagascar: 19 km southeast de Manja | 21.5° S, 44.5° E | 1 | Timocharis, 38 km | 9.3 / 9.4 | 5.7, 39 % | 0.675 | 99.83 | 98.88 |
| 2 | Nugaal, Somalia: 64 km southwest de Eyl | 7.5° N, 49.5° E | 2 | Bessarion, 84 km | 9.9 / 9.9 | 6.2, 37 % | 0.705 | 99.97 | 98.76 |
| 3 | Sindh, Pakistan: 29 km northeast de Jati | 24.5° N, 68.5° E | 5 | Banting, 58 km | 9.2 / 9.1 | 5.6, 39 % | 0.662 | 99.93 | 98.56 |
| 4 | Ethiopia: 131 km northwest de Gaalkacyo, Somalia | 7.5° N, 46.5° E | 7 | Rima Marius, 179 km | 9.9 / 9.9 | 6.1, 38 % | 0.677 | 99.97 | 98.52 |
| 5 | Bari, Somalia: 38 km northeast de Iskushuban | 10.5° N, 50.5° E | 9 | Catena Dziewulski, 95 km | 9.8 / 9.8 | 6.3, 36 % | 0.792 | 99.94 | 98.37 |

### Lunar base

Regla de los cinco (`rank_with_skips`): The five are ranks 1, 3, 5, 6, 7 of the full ranking; every rank above the fifth that is not among them is skipped by the rule (rank 2: within 2 degrees of arc of E21054 (1.98 degrees); rank 4: within 2 degrees of arc of E21054 (1.31 degrees)), so they are the highest-scoring five that the rule of the five allows.

| # | Lugar | Coordenadas | Puesto | Gemelo (rasgo, km), región | Diferencia de mínima (K) | Percentil mínima T / L | Percentil oscilación T / L | Sim. | Final |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Souss-Massa-Draa, Morocco: 4 km southeast de Tinghir | 31.5° N, 5.5° W | 1 | Wapowski, 18 km; at the edge of NASA's Nobile Rim 2 | 208.6 | 62.7 / 62.7 | 41.9 / 43.4 | 99.36 | 72.00 |
| 2 | Xinjiang Uygur Zizhiqu, China: 62 km north de Aheqi | 41.5° N, 78.5° E | 3 | Mons Malapert, 25 km; at the edge of NASA's Haworth | 207.4 | 8.4 / 8.0 | 6.7 / 10.2 | 97.31 | 70.23 |
| 3 | Fars, Iran: 18 km east de Kherameh | 29.5° N, 53.5° E | 5 | Wapowski, 14 km; at the edge of NASA's Nobile Rim 2 | 208.2 | 62.9 / 64.1 | 59.5 / 54.8 | 92.50 | 69.87 |
| 4 | Xinjiang Uygur Zizhiqu, China: 27 km southeast de Waxxari | 38.5° N, 87.5° E | 6 | Mons Mouton, 49 km; at the edge of NASA's Mons Mouton Plateau | 202.9 | 27.8 / 34.1 | 80.1 / 77.7 | 83.98 | 69.80 |
| 5 | Semnan, Iran: 28 km north de Aradan | 35.5° N, 52.5° E | 7 | Slater, 49 km; at the edge of NASA's Slater Plain | 207.4 | 53.0 / 54.8 | 55.1 / 51.3 | 93.33 | 69.73 |

## Ficheros que hay que grabar

Ninguno (0 de 19): `app/public/audio/pending.json` tiene la lista vacía y la web reproduce cada pista.
