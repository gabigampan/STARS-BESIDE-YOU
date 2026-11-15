# Investigación 4: validación externa positiva de Placas solares y Base lunar

Investigación r4, 15-11-2026, entre las 11:33 y las 11:50 CET. Solo investigación y medición: no he tocado el motor, su configuración, las tablas, el bundle, la web ni los audios.

## 1. Resultado en dos líneas

- **Placas solares:** los sitios de referencia de alta irradiancia salen arriba. De 13 sitios, 11 pasan el embudo, 9 tienen gemelo y 8 están en el cuartil superior (mediana del percentil 14,9 %). Los 6 controles negativos (estaciones del Met Office con poco sol) quedan fuera por el filtro de irradiancia en superficie (≥ 2,5 kWh/m²/día). Separación: 0,923. Pero dentro de su propia fila de latitud los positivos solo quedan en la mediana del percentil 27,9 %: el orden dice algo más que la latitud, aunque poco. Los dos sitios desérticos de EE. UU. (36,6 N y 40,1 N) pasan el embudo pero no tienen gemelo, porque el gemelo depende solo de la latitud.
- **Base lunar:** los análogos polares y de alta montaña reconocidos quedan fuera casi todos. 10 de 13 positivos no pasan el embudo, y ninguna celda de la Tierra por encima de 51,5° de latitud pasa. La causa principal es el filtro de amplitud térmica diaria ≥ 15 K: Haughton tiene 2,5 K, Svalbard 1,2 K, Kangerlussuaq 6,6 K y Askja 7,4 K, y Concordia y los Valles Secos de McMurdo no tienen dato de amplitud (MODIS no cubre la Antártida). Los únicos que pasan son análogos desérticos de hábitat u operaciones (MDRS, Craters of the Moon, Black Point). La separación (0,615) se debe sobre todo a empates, porque el embudo deja fuera a la vez a casi todos los positivos y a todos los negativos.

## 2. Listas compiladas (archivos nuevos, no he editado el benchmark del equipo)

- `tierra luna/data/benchmark/validation_sites_solar.csv`: 13 positivos y 6 negativos.
- `tierra luna/data/benchmark/validation_sites_lunar_base.csv`: 13 positivos y 7 negativos.
- Columnas: `site_id, role, name, operator, country, lat, lon, coord_source, recognised_for, source_url, sentence_relied_on, date_accessed, space_tie, notes`. Cada archivo lleva una cabecera de comentarios `#` que explica las columnas. Los dos se regeneran con `tierra luna/research/r4_build_site_lists.py`.

**Solar, positivos.** Son estaciones de referencia de la red BSRN situadas en una clase climática árida según BSRN, o en cumbre de montaña (Izaña). Las coordenadas y la clase de Köppen salen de la tabla oficial de estaciones de BSRN (https://wiki.pangaea.de/wiki/BSRN, "Sortable Table of Stations", consultada hoy). Para su reconocimiento cito bsrn.awi.de: "The Baseline Surface Radiation Network (BSRN) has provided the world's highest-accuracy surface radiation measurements". Las estaciones son Tamanrasset, Gobabeb, De Aar, Sede Boqer, Solar Village, Gandhinagar, Gurgaon, Alice Springs, Desert Rock, Boulder Table Mountain, Petrolina, Izaña y Lampedusa: cinco continentes (falta la Antártida). No he encontrado ningún vínculo con el espacio en una fuente.

**Solar, negativos.** Son seis estaciones del Met Office: Lerwick, Eskdalemuir, Stornoway, Braemar, Dunstaffnage y Tiree. Las coordenadas salen de la línea "Location" de cada archivo de datos (https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/<estación>data.txt, licencia Open Government Licence v3.0). La insolación media anual de 1991-2020 es DERIVED: la calcula `research/r4_metoffice_sunshine.py` con los años completos. Sale entre 1.103 y 1.430 h/año, cuando la media del Reino Unido en 1991-2020 es de 1.402,6 h según el Met Office. Descarté Camborne porque tiene 1.612 h y no es un negativo claro. Limitación: los seis negativos están en un solo país.

**Base lunar, positivos.** Reutilizo 12 filas verificadas del benchmark: Concordia, Haughton, Valles Secos de McMurdo, Svalbard-Bockfjorden (AMASE), Kangerlussuaq, Mauna Kea PISCES, Teide (LUCID), MDRS, Askja, Black Point (Desert RATS), Craters of the Moon (FINESSE) y Timanfaya (PANGAEA). He añadido Neumayer III / EDEN ISS. La página del DLR (https://www.dlr.de/en/research-and-transfer/projects-and-missions/eden-iss) dice que el invernadero estaba "located in Antarctica, near the Neumayer III Antarctic station" y que fue "designed to explore future food production on the Moon and Mars". La página no da coordenadas, así que uso las de la estación BSRN de Neumayer (GVN: -70,65; -8,25).

**Base lunar, negativos.** Son estaciones BSRN de clima tropical húmedo según la columna de Köppen de BSRN: Paramaribo, Lanyu, Ishigakijima, Rolim de Moura, Selegua, Darwin y Reunión. Una oscilación térmica baja medida en una página oficial de clima **no está establecida**: solo tengo la clase climática.

**Sitios descartados por no tener fuente hoy:**
- Plataforma Solar de Almería: las páginas de CIEMAT, DLR y el Ministerio dan la dirección pero no coordenadas, y psa.es devuelve HTTP 503.
- NREL SRRL: midcdmz.nrel.gov no es accesible desde esta sesión (habría que permitir ese host).
- Filas del benchmark marcadas como no verificadas: HI-SEAS, Axel Heiberg, Aquarius/NEEMO, Death Valley, Meteor Crater, Cinder Lake, Sudbury, Mistastin, Pavilion Lake, entre otras.
- No he buscado más estaciones con página oficial que publique sus coordenadas (Halley, Amundsen-Scott como análogo, FMARS) por falta de tiempo.

## 3. Dónde salen hoy (bundle equivalente a 42d8bba)

**Qué bundle he usado.** El bundle no está en git, así que he copiado el del árbol de trabajo (construido a las 10:14 UTC) a `/tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/r4/bundle_snap`. Lo he contrastado así:
- `mission_scoring.json` es idéntico al de 42d8bba.
- Los cambios en `engine_config.json` y `datasets.json` desde 42d8bba son solo de textos.
- Coinciden 6.360 puntos emparejados de Placas solares y 450 de Base lunar.
- El número 1 de Placas solares es E38464, como en `docs/AUDIO_TOP5.json`.

**Definiciones.**
- Percentil = 100·rango/pasan (más bajo es mejor). Los que pasan sin gemelo van detrás, ordenados por idoneidad, como en el bundle.
- Separación = proporción de pares positivo-negativo en los que el positivo queda mejor. Los eliminados empatan en el peor rango y un empate cuenta 1/2.
- La tabla completa está en `tierra luna/research/out/r4_rank_sites_b42d8bba.csv` y `.json`. Incluye razones exactas, variables de diagnóstico, mejor rango en el bloque 3×3 y percentil dentro de la fila de latitud.

### Placas solares (pasan 18.777; con gemelo 6.360)

| sitio | celda | tierra | pasa / razón | idon. | gemelo | sim. | final | rango | pct | pct en fila lat. |
|---|---|---|---|---|---|---|---|---|---|---|
| Alice Springs | E40993 | 1,00 | sí | 94,33 | M22419 | 99,99 | 97,16 | 326 | 1,7 | 6,9 |
| Tamanrasset | E24305 | 1,00 | sí | 93,10 | M22885 | 99,95 | 96,53 | 1.008 | 5,4 | 27,9 |
| Gandhinagar | E24012 | 1,00 | sí | 91,17 | M22651 | 100,00 | 95,58 | 1.558 | 8,3 | 45,0 |
| Gobabeb | E40875 | 1,00 | sí | 88,48 | M42472 | 100,00 | 94,24 | 2.105 | 11,2 | 60,9 |
| Solar Village | E23626 | 1,00 | sí | 87,19 | M42741 | 99,93 | 93,56 | 2.460 | 13,1 | 66,2 |
| Gurgaon | E22217 | 1,00 | sí | 88,90 | M21759 | 96,91 | 92,90 | 2.793 | 14,9 | 33,1 |
| Petrolina | E35779 | 0,97 | sí | 85,64 | M25792 | 99,98 | 92,81 | 2.850 | 15,2 | 15,3 |
| De Aar | E43403 | 1,00 | sí | 90,49 | M21728 | 89,25 | 89,87 | 4.280 | 22,8 | 18,1 |
| Sede Boqer | E21454 | 1,00 | sí | 88,65 | M42998 | 89,25 | 88,95 | 4.705 | 25,1 | 25,9 |
| Desert Rock | E19143 | 1,00 | sí, sin gemelo (irradiancia TOA 8,21) | 81,92 | — | — | — | 6.490 | 34,6 | 8,5 |
| Boulder Table Mtn | E17714 | 0,99 | sí, sin gemelo (TOA 7,83) | 73,62 | — | — | — | 7.709 | 41,1 | 69,6 |
| Izaña | E22123 | 0,18 | no: mask_fraction < 0,3; thermal_inertia_class 'agua' | — | — | — | — | — | — | — |
| Lampedusa | E19632 | 0,002 | no: mask_fraction; slope sin dato; 'agua' | — | — | — | — | — | — | — |
| 6 negativos (Reino Unido) | | 0,13-0,99 | no: irradiance_kwh_m2_day < 2,5 en los 6 (2,21-2,42); además mask_fraction y 'agua' en las 3 islas | — | — | — | — | — | — | — |

**Resumen de Placas solares:**
- Positivos: mediana del percentil 14,9 %; 8 de 13 en el cuartil superior.
- Negativos: 0 pasan.
- Separación: 0,923 por celda y 0,910 por bloque 3×3.
- Mediana del percentil dentro de la fila de latitud de los 11 positivos que pasan: 27,9 % (el azar daría 50 %).

### Base lunar (pasan 2.419; con gemelo 450)

| sitio | celda | tierra | pasa / razón | idon. | gemelo | sim. | final | rango | pct |
|---|---|---|---|---|---|---|---|---|---|
| Craters of the Moon | E16626 | 1,00 | sí | 28,08 | M63832 | 95,21 | 61,64 | 170 | 7,0 |
| MDRS | E18429 | 1,00 | sí | 33,37 | M62134 | 76,83 | 55,10 | 356 | 14,7 |
| Black Point (Desert RATS) | E19508 | 1,00 | sí, sin gemelo | 35,58 | — | — | — | 1.629 | 67,3 (3×3: 6,3) |
| Concordia | E59703 | 1,00 | no: lst_diurnal_amp_k sin dato | — | | | | | |
| Valles Secos de McMurdo | E60462 | 0,99 | no: lst_diurnal_amp_k sin dato | — | | | | | |
| Haughton | E5130 | 0,76 | no: amplitud 2,5 K < 15 | — | | | | | |
| Svalbard-Bockfjorden | E3793 | 0,61 | no: amplitud 1,2 K; clase 'agua' | — | | | | | |
| Kangerlussuaq | E8049 | 0,79 | no: amplitud 6,6 K | — | | | | | |
| Askja | E8803 | 0,98 | no: amplitud 7,4 K | — | | | | | |
| Mauna Kea PISCES | E25224 | 0,75 | no: tmin_c 10,9 > 5 (elevación media de la celda: 1.345 m) | — | | | | | |
| Teide | E22123 | 0,18 | no: amplitud 14,35; tierra; 'agua'; tmin_c 10,6 | — | | | | | |
| Timanfaya | E22126 | 0,10 | no: tierra; 'agua'; tmin_c 13,4 | — | | | | | |
| Neumayer / EDEN ISS | E57771 | 0,001 | no: elevación < 1 m; amplitud sin dato; tierra; 'agua' | — | | | | | |
| 7 negativos tropicales | | 0,02-1,00 | no: los 7 por amplitud < 15 K (5,2-12,3) y tmin_c > 5 °C (7,8-22,2) | — | | | | | |

**Resumen de Base lunar:**
- Positivos: 3 de 13 pasan y 2 tienen gemelo; mediana del percentil de los que pasan 14,7 %; 2 en el cuartil superior (3 por bloque 3×3).
- Negativos: 0 de 7 pasan.
- Separación: 0,615. Es casi toda empate, porque se calcula como (3·7 + 10·7·½)/91.

**Hechos del embudo de Base lunar medidos en el bundle:**
- Las celdas que pasan van de 47,5 S a 51,5 N.
- 7.562 celdas de tierra fallan solo por la amplitud < 15 K, y 3.611 de ellas están por encima de 60° de latitud.
- Otras 6.060 fallan solo por falta de dato de amplitud (Antártida).
- Proporción de celdas con amplitud ≥ 15 K por franja: 50-60 N 1 %, 60-70 N 0 %, 70-80 N 0,1 %.
- Incluso tomando el máximo mensual (`lst_diurnal_amp_max_k`, que ya está en la tabla), Haughton tiene 5,8 K, Svalbard 3,0 K, Kangerlussuaq 14,3 K y Askja 16,9 K.

## 4. Script para los re-auditores

`python -I "tierra luna/research/r4_rank_sites.py" <carpeta del bundle> [etiqueta]`

Lee solo el bundle (manifest, `earth_base.bin`, `earth_<misión>.bin` y los `reason_codes` de `missions.json`) y las dos listas. No importa nada del motor. Escribe `research/out/r4_rank_sites_<etiqueta>.json` y `.csv`. Comprueba internamente que el rango reconstruido cubre exactamente las celdas que pasan.

## 5. Qué sugiere sobre los criterios (sin proponer cambios)

**Placas solares.**
- El filtro de irradiancia en superficie separa bien los positivos de los negativos. En cambio, el orden entre los positivos se parece mucho al de la latitud.
- La similitud (irradiancia en el techo de la atmósfera) deja sin gemelo a desiertos de referencia por encima de unos 33,5° (Desert Rock, Boulder).
- Gobabeb (Namib) y Solar Village quedan por debajo de la mediana de su propia fila de latitud. Eso indica que la idoneidad apenas recoge la irradiancia real en el suelo, lo que coincide con el 65 % de peso en latitud que señaló la auditoría.
- Las islas y las cumbres (Izaña, Lampedusa) caen por la proporción de tierra y por la clase 'agua', no por el sol.

**Base lunar.**
- El filtro de amplitud ≥ 15 K, medido como diferencia anual entre las pasadas de MODIS de ~10:30 y ~22:30, deja fuera todo el Ártico y todo lo que está por encima de 51,5°. En latitudes altas esa diferencia es pequeña por la noche y el día polares (lo advierte la propia procedencia de la variable). La oscilación grande de esos sitios es estacional, no diaria.
- La Antártida no tiene dato de amplitud, y la regla de variable obligatoria la elimina entera (Concordia, McMurdo, Neumayer).
- El filtro tmin_c ≤ 5 °C a 1° deja fuera las cumbres tropicales (Mauna Kea, Teide), porque la celda promedia altitudes bajas.
- Lo que hoy sale como "análogo de base" son desiertos fríos de altitud media del oeste de EE. UU., coherentes con MDRS y Desert RATS, pero no con las estaciones polares.
- Los otros dos investigadores deberían mirar el filtro de amplitud, la regla de variable obligatoria y la clase 'agua' en celdas costeras.

## 6. Qué necesitaría al jefe de equipo

Nada de zonas. Una posible cuestión de principio: si "Base lunar con análogos en la Tierra" debe incluir las estaciones polares, hoy no puede con el filtro de amplitud diaria. Opciones, que quedan para los investigadores de configuración:
- (a) mantener el filtro y decir en la web que los análogos polares quedan fuera, con estas cifras;
- (b) cambiar la medida de oscilación (máximo mensual o una oscilación estacional con fuente);
- (c) bajar el umbral con un argumento físico.

## 7. Qué no está establecido

- Una baja oscilación térmica medida con fuente oficial de clima para los negativos de Base lunar (solo tengo la clase de Köppen de BSRN).
- La irradiancia medida en los positivos solares: su condición de positivos se basa en ser estación de referencia BSRN en clima árido. No he descargado series de BSRN.
- Coordenadas oficiales de PSA, NREL SRRL, HI-SEAS, FMARS y Halley.
- Negativos solares fuera del Reino Unido.
- Una celda de 1° no es un sitio. Los sitios se eligen también por logística (acceso, apoyo). Las muestras son pequeñas (13+6 y 13+7) y algunos positivos comparten fila de latitud, así que las proporciones tienen mucha incertidumbre.
