# Correcciones 1: fallos de las auditorías 1, 2 y 4

Agente de correcciones (no auditor). 15-11-2026, rama `final-integration`. Lista de trabajo: `1_datos_rejilla_nombres.md`
(puntos 1, 2, 7), `2_metodo_top5_unidades.md` (3, 4, E) y `4_audios_coherencia.md` (8, 9). Solo se corrige lo que no
cambia un criterio decidido por el equipo. **No se ha cambiado ningún peso, tolerancia, umbral, puerta, zona, regla,
orden, población, variable comparada ni par.** No se ha tocado ningún audio, transcripción, vídeo, subtítulo, nada de
`app/src` ni `app/tests`, `docs/MISSION_ZONES.md`, `validation/`, `mission_scoring.json`, `engine/mission_zone_texts.json`
ni los ficheros de los auditores. No se ha hecho ningún commit.

Test nuevo: `tierra luna/tests/test_audit_corrections_1.py` (14 tests, escritos para fallar con el estado anterior de cada fallo).

## Correcciones (una línea por fallo: fichero, antes, después, test)

| # | fallo (confirmado) | fichero | antes | después | test |
|---|---|---|---|---|---|
| 1 | Lugar "más cercano" por distancia euclídea en grados | `tierra luna/engine/places.py` (`earth_places`, nuevas `load_geonames_places`, `nearest_geonames_rows`) | `reverse_geocoder.search(mode=1)`: k-d tree sobre (lat, lon) en grados; el lugar no era el más cercano en 8.284 de 25.497 celdas de tierra | k-d tree sobre vectores unitarios (orden de cuerda = orden de gran círculo) con las mismas 144.563 filas de `rg_cities1000.csv`, 8 candidatos, decide la haversine (R = 6.371 km) y, en empate exacto, la fila más baja; la distancia, la región (`admin1` solo si ≤ `region_max_place_km` y mismo país), el país de reserva (`nearest_geonames_place`) y el código de los polígonos sin ISO salen ya del lugar correcto | `test_nearest_place_is_the_great_circle_nearest_on_every_land_cell` (fuerza bruta sobre las 25.497 celdas × 144.563 filas), `test_great_circle_nearest_differs_from_the_nearest_in_degrees`, `test_region_follows_the_corrected_nearest_place`, `test_audio_top5_places_are_unchanged` |
| 2a | Frase falsa "the *_300m_* columns are 2-degree copies" | `engine/engine_config.json` `not_used_by_engine_why` (exportada 3 veces en `missions.json` `not_used_by_engine.why`) | "tolerances: defined for 300 m baselines while the *_300m_* columns are 2-degree copies" | "no table has 300 m values: on the real 1-degree tables the *_300m_* variables are read from km-baseline columns (slope_iso_deg, about 3.7-3.8 km, and roughness_m, lag about 1.9 km; true_baseline in variables.json), and on the legacy 2-degree table they were copies of 2-degree-cell values" (misma corrección en el `why` de `similarity_scale`) | `test_not_used_by_engine_why_is_true_for_the_real_table` |
| 2b | Rover pone en ranking celdas de hielo sin decirlo | `engine/datasets.json` real_1deg `mission_notes.rover` (4.º elemento de `known_limitations`) | "The soft criteria have no surface-type term: polar deserts, ice-free Arctic plateaus and steppe score alike..." | añade: "the funnel has no surface-type gate ... ice sheets are not excluded. 1,445 of the 10,192 ranked Rover points are ice-sheet or snow-and-ice cells (snow and ice cover at least half of the cell, or the thermal class is 'hielo'): 1,101 in Antarctica and 201 in Greenland. None of them ranks in the top 500; the best is number 722." | `test_rover_limitation_states_the_ice_cells_with_recomputed_figures` (recalcula desde `output_real/earth_real_1deg.csv` y el paquete) |
| 2c | Nadie dice que la similitud de Paneles está saturada | `engine/engine_config.json` `approved_texts.solar_similarity_saturation` (nuevo) → `similarity.json` `texts.solar_similarity_saturation` y 1.er elemento de `missions[solar].known_limitations` | ningún texto | texto nuevo con `where` "on EVERY solar pair ... and on the Solar panels mission card" (cifras abajo); `decision` dice que no es decisión del equipo | `test_solar_saturation_text_with_recomputed_figures`; `test_real_data.py::test_approved_texts_are_in_the_bundle_verbatim` (conjunto de claves ampliado) |
| 2d | `similarity_scale` no decía que no lo usa ninguna regla publicada | `engine/engine_config.json` `similarity_scale.why` | sin marca | "USED BY NO SHIPPED RULE: only the physical_pooled similarity rule ... reads this setting ... the bundle does not export it" | `test_similarity_scale_is_marked_unused_by_the_shipped_rules` |
| 2e | `variables.json` cinco niveles, contrato cuatro | `engine/export_v2.py` (`levels_in_use`), `docs/DATA_CONTRACT.md` paso 5 de la ficha | `levels.UNDOCUMENTED` sin aviso; el contrato nombraba MEASURED, DERIVED, MODELLED, NO_DATA | el texto de todo nivel que ninguna variable del conjunto usa termina en "No variable of this dataset has this level (defined for other tables only)." (hoy solo UNDOCUMENTED); el contrato nombra los cinco y dice que UNDOCUMENTED no lo tiene ninguna variable del conjunto publicado | `test_levels_of_the_bundle_and_the_contract_agree` |
| 3 | El motor rellenaba la frase de Base lunar con otro redondeo que la regla del contrato | `engine/display.py` (`to_fixed`, `to_fixed_of_stored`, `fill_placeholder(display_rule=False)`), `engine/export_v2.py` `fill_pair_sentence`, `engine/bundle_v2.py` `_check_pair_sentences` | `f"{x:.{d}f}"` de Python: una mitad binaria exacta va al par | `toFixed` exacto (ECMA-262: valor binario exacto, empate al n mayor, signo aparte) sobre el float32 guardado menos `subtract`; la regla del contrato para la web no cambia (solo la frase del motor en el contrato, línea "Per-pair sentence") | `test_to_fixed_matches_javascript`, `test_lunar_base_pair_sentence_follows_the_contract_rule_on_all_450_pairs` (450 pares, implementación propia de `toFixed` desde la especificación, y `explain.json`) |
| 4a | Doble redondeo de distancias | `tierra luna/tools/make_audio_top5.py` (`spoken_km`) | `int(round(x))` sobre la distancia ya redondeada a 1 decimal (y al par): 15,47 → 16; 45,48 → 46; 82,52 → 82 | una sola vez, a la unidad, hacia arriba en la mitad, desde el float32 guardado (`engine/display.py displayed`): 15, 45, 83; campos nuevos `distance_km_spoken` | `test_audio_top5_is_regenerated_and_rounds_once` |
| 4b | "modelled climatologies (WorldClim, MODIS-based amplitude...)" | `make_audio_top5.py` `caveats` | la amplitud de MODIS entre lo modelado | "Earth coldest air temperature and ground sunlight are modelled climatologies (WorldClim); the daily temperature swing is derived from MODIS land-surface temperature (daytime minus night-time overpass); none of them is a site measurement." | mismo test |
| 4c | Falta el aviso del ancho de celda | `make_audio_top5.py` (`cell_area_km2`, `cell_east_west_km`, nuevo `caveats[1]` y `cell_area_km2` por par) | solo "about 111 km north-south ... about 30 km on the Moon" | calculado de los 15 pares: el gemelo de Base lunar mide 1.3 a 3.4 km de este a oeste; la celda de la Tierra promedia 88 a 224 veces más terreno (Paneles 14, Rover 39 a 53; la tarea decía "about 45" para Rover: son 39-53 según la latitud de cada punto) | `test_cell_area_caveat_is_recomputed` |
| 4d | "in NASA's X candidate region" para gemelos cuyo centro está fuera | `make_audio_top5.py` (`region_share_of_cell`, proyección azimutal equivalente polar escrita en el script; campos y `say`) | `say`: "in one of NASA's nine candidate landing regions near the lunar south pole"; `zone`: igual | "in NASA's X candidate region" solo si ≥ 50 % de la celda está dentro; si no, "at the edge of NASA's X candidate region (N % of the cell lies inside it; its centre is outside)". Cuotas recalculadas: base_1 Haworth 0,4 %, base_2 de Gerlache Rim 2 7,8 %, base_3 Slater Plain 33 %, base_4 Nobile Rim 2 45 %, base_5 Nobile Rim 2 0,3 % (= auditor); los cinco quedan "at the edge of" | `test_audio_top5_is_regenerated_and_rounds_once` |
| 5a | Glosario de DECISIONS con la fórmula z sin marca; secciones antiguas sin marca; "36 %" | `docs/DECISIONS.md` | z, Similitud `100 × exp(−0,45 d)` y Gemelo sin filtro como vocabulario vigente; "Decisiones tomadas (15-11-2026)", "Decisión 1" (y su "1. Qué pasa ahora") y "Decisión 5" sin marca; Base lunar `zone_twin` en la sección de la mañana; "un 36 % menos" | marca "**[SUSTITUIDO el 15-11-2026 por <sección>]**" en cada una (nada borrado); glosario con la regla vigente (`s = exp(−0,5 (d/τ)²)`, media ponderada, filtro τ / 2τ, gemelo que pasa el filtro, percentiles de Base lunar); "35 %" con la razón (antes 100 × `atm.lost_share` = 35,66 → 36; con la regla `share_lost_of_displayed_tenths` 100 × (9,6 − 6,2) / 9,6 = 35,4 → 35) | `test_real_data.py::test_approved_texts_are_in_the_bundle_verbatim` (las citas aprobadas siguen literales) |
| 5b | "Artemis III" en la frase propuesta | `docs/LUNAR_BASE_PROPOSAL.md` | sin nota | nota encima de la frase: la publicada no nombra misión ("NASA's nine candidate landing regions near the lunar south pole"); la propuesta queda como historia | — (texto) |
| 5c | Filas de ASSUMPTIONS con `zone_twin` y Paneles en el polo sur como vigentes | `ASSUMPTIONS.md` §0.4 (fila `zone_twin`, fila `similarity_zones`, párrafos de las líneas 61, 63, 88, 96, 117), §0.10 puntos 1 y 5 | "active since the team decision of 2026-11-15", "Solar stays on the south pole" sin marca en la línea | marca "superseded on 2026-11-15 by section 0.12 ... and section 0.13 ..." en cada una | — (texto) |
| 5d | Dos frases de redondeo contradictorias | `docs/DATA_CONTRACT.md` (lista tras el bloque de fórmulas) | "stored suitability and final use Python's `round`; similarity uses `numpy.round` as analog_finder does" | una regla: `round(float(x), 2)` en todo lo publicado (idoneidad, similitud, final, y el rango sobre el final guardado), con el caso de la mitad (2,675 → 2,67; `numpy.round` y `round(np.float64)` dan 2,68); `numpy.round` solo en la similitud z de las reglas no publicadas. La implementación ya la seguía (`round_like_export`, `_round_array` convierten con `float()`) | `test_stored_scores_round_with_python_round_on_a_float_not_numpy_round` |
| 5e | Permafrost lunar "vacío"; irradiancia "measured-climatology" | `docs/REAL_DATA.md` (tabla lunar, §6.3, lista de huecos, §9) y `tierra luna/real_data/README.md` (tabla y huecos) | "empty in all 64,800 cells"; "measured-climatology surface radiation" | `permafrost_class` = etiqueta MODELLED "ninguno" en las 64.800 celdas (lluvia y viento sí vacíos); irradiancia de la Tierra MODELLED (WorldClim 2.1 srad) | — (texto) |
| 6a | Vídeo Solar del método anterior sin aviso | `app/public/media/solar/README.md` | sin aviso | aviso al principio: polo sur y regla z anteriores; E44120 hoy es el puesto 5.786 con gemelo M21923 y M59479 está fuera de la zona actual; no presentarlo como un par de hoy; re-render aparte | — (texto) |
| 6b | Sol a 21,1° en el vídeo del Rover | `app/public/media/rover/README.md` | sin nota | nota: en las 5.400 celdas a 75 S o más al sur `sun_elev_max_deg` va de 2,04° a 16,04° (recalculado de `moon_real_1deg.csv`); el 21,1° es un ajuste de la simulación | — (texto) |

Cifras de 2c, recalculadas con código propio desde el paquete (test): 78 % de los 6.360 pares con similitud ≥ 99; 514
publicados como 100,00; candidatos que pasan el filtro por punto, mediana 1.843,5 sobre los valores float32 (el texto
dice "about 1,840"; el auditor, a doble precisión, 1.844); en los 100 primeros la similitud va de 99,88 a 100,00 y la
idoneidad de 95,18 a 96,90; Spearman del final con la idoneidad 0,995 y con la similitud 0,146. Cifras de 2b: 1.445 de
10.192 (1.424 por `snow_ice_frac ≥ 0,5`, 1.268 por la clase "hielo"); 1.101 con etiqueta Antarctica y **201 con
etiqueta Greenland** (el auditor dio 217 con una caja de coordenadas, que incluye celdas de Svalbard, Islandia y
Canadá); 0 en los 500 primeros; la mejor, el puesto 722.

### Cuántas celdas cambian de nombre (corrección 1)

- 8.281 celdas de tierra cambian de nombre de lugar (5.009 al sur de 60 S, 3.272 fuera); en 3 más cambia la fila de
  GeoNames pero no el nombre (otro lugar homónimo más cerca), así que la distancia cambia en 8.283 (siempre baja; como
  máximo 5.837,8 km, en la Antártida). De las que cambian fuera de la Antártida, 2.065 quedan a ≤ 300 km (las que la web
  enseña).
- Región (`admin1`) distinta: 288 celdas. País distinto: 172, todas de la regla de reserva `nearest_geonames_place`
  (centro fuera de todo polígono NE 110m), p. ej. 55 Canada → Greenland, 27 + 24 + 22 + 8 Russia / Norway / Iceland /
  Greenland → Svalbard & Jan Mayen, 7 Wallis & Futuna → Fiji. Ninguna celda cambia de `label_rule`.
- En ranking cambian de nombre: Rover 2.239 (100 primeros: 11), Paneles 190 (1), Base lunar 50 (10). En los 25 de
  `explain.json`: Paneles puesto 6 (Mahabe 67,2 km → Sitampiky 66,6 km, región Melaky → Boeny), Base lunar puesto 12
  (Qinghe 20,8 → Qagan Gol 18,9) y puesto 20 (Aheqi 49,3 → Kalpin 47,9). **En los top 5, y por tanto en los 15 pares de
  los audios: 0.** En `docs/AUDIO_TOP5.json` el nombre, la distancia (1 decimal), la dirección, la región y el país de
  los 15 pares son idénticos antes y después (comparación campo a campo).

### Paquetes reconstruidos

- `python -m engine build` (en `app/public/data/v2`) y otra vez en una carpeta aparte: **idénticos byte a byte**. Lo
  mismo para el de control sin gemelo (`--similarity-rule repo_global_mean --out .../stars/bundle_global_mean`).
- Ficheros que cambian frente a los publicados antes (iguales en los dos paquetes): `earth_base.bin` (solo columnas
  `country`, 172 filas, y `region`: 288 celdas con otro valor, el resto son índices renumerados porque la lista de
  regiones cambia), `earth_place_detail.bin` (`nearest_place`: índices a la lista de nombres, que cambia;
  `nearest_place_km`: 8.283 filas), `place_detail.json`, `places.json`, `explain.json` (solo los 3 lugares de arriba),
  `missions.json` (`not_used_by_engine.why`, limitación del Rover, primer elemento nuevo de las limitaciones de
  Paneles), `similarity.json` (`texts.solar_similarity_saturation`), `variables.json` (texto de `levels.UNDOCUMENTED`),
  `manifest.json` (tamaños, sha256, sha256 de la configuración).
- **Todos los demás ficheros son byte a byte los de antes**: `earth_rover.bin`, `earth_solar.bin`,
  `earth_lunar_base.bin`, los tres `*_pairs.bin`, `moon_*.bin`, `moon_base.bin`, las teselas, `twins.json`,
  `mission_zones.json`, `iau_moon_features.json`. Ningún par, gemelo, puntuación, similitud, final ni puesto cambia.
  Las frases por par de `explain.json` (Paneles y Base lunar) no cambian: los 8 valores en que el redondeo antiguo
  difería de `toFixed` no están en los 25 primeros.

### Tests

Suite completa: ver el final de este documento.

## Fallos que no lo eran (o no del todo)

- **3, redondeo del motor:** el contrato ya decía "idéntico salvo en un empate binario exacto", y era cierto. Con la
  regla corregida el motor difiere de la anterior en 8 valores de 8 de los 450 pares (diferencias de temperatura de
  exactamente 154,5 / 162,5 / 192,5 K; pendiente 1,25°; rugosidad 2,25 / 16,25 / 18,25 / 39,25 m); ninguno está en los
  25 de `explain.json`, así que **el `explain.json` publicado no cambia**. El fallo estaba en la función, no en el
  fichero. Ver además "La web" (punto 2): la web no aplica esa regla.
- **2b, "217 en Groenlandia":** no es un error del auditor sino otra definición (caja de coordenadas); con la etiqueta
  de país del paquete son 201, que es lo que dice el texto.
- **4, "about 45 for Rover":** con las latitudes de los 5 pares la razón de áreas va de 39 a 53; el aviso da el rango.
- **4, Rimae Pettit "82":** era el texto del generador (82,52 → 82,5 → 82 con redondeo al par); la grabación ya decía 83.
  Ahora el generador dice 83.

## Lo que necesita al jefe de equipo (no aplicado)

1. Cuestiones de diseño de los auditores, intactas: casi duplicados en un top 5; los cinco pares del Rover con un solo
   gemelo; celdas de hielo en el ranking del Rover (solo se ha escrito la limitación); la puerta común
   `elevation_m ≥ 1`; la referencia de la Tierra de la elevación relativa; la saturación de Paneles (solo se ha escrito
   el texto); qué celdas lunares cuentan como dentro de las regiones de la NASA (la zona sigue siendo las 280 celdas que
   tocan las regiones; solo cambian las palabras del generador).
2. **Frase por par de Base lunar** (aprobada, no reescrita). Propuesta de redacción:
   "... In real values the twin is {temp_diff_k} K colder on average (minimum {tmin_moon_c} °C at the surface against
   {tmin_earth_c} °C air temperature here) and its day-night swing is {amp_diff_k} K larger (on Earth the swing is a
   satellite's daytime minus night-time land-surface temperature, which understates the daily range); slope differs by
   {slope_diff}° and roughness by {rough_diff} m." y, cuando una diferencia se muestre como 0.0, escribir "less than
   0.1" en su lugar ("slope differs by less than 0.1°"): hoy 4 de los 450 pares dicen "slope differs by 0.0°".
   Además, 2 pares muestran "-0.0 °C" como temperatura de la Tierra (−0,04 °C con `toFixed(1)`); propuesta: "0.0".
3. **Regla de la frase de Base lunar en la web:** el contrato dice `toFixed` del float32 guardado; la web aplica la regla
   de Paneles (decimal más corto del float32 y `Intl.NumberFormat`). Difieren en 26 valores de 26 pares (10 de
   `tmin_earth_c`, 16 de `rough_diff`), uno de ellos en `explain.json`: el **puesto 7** (E16833), donde `explain.json`
   dice "-20.3 °C" (valor guardado 252,89999 K, es decir −20,2500061 °C) y la web imprime "-20.2". O la web sigue el
   contrato (lo pedido aquí), o el equipo decide unificar las dos frases con la regla de Paneles (cambiaría el contrato y
   el motor; decisión del líder).
4. **Audios a regrabar por los valores que cambian en `AUDIO_TOP5.json`** (la lista completa está abajo): base_2
   "16 kilometers from Cartwright" → 15; base_3 "46 kilometers" → 45; base_1 y base_5 "in NASA's ... candidate region"
   → "at the edge of" (0,4 % y 0,3 % de la celda dentro); base_2, base_3 y base_4 (7,8 %, 33 %, 45 %, centro fuera)
   también quedan "at the edge of" con la regla del 50 %: a juicio del jefe de equipo. No se ha tocado ninguna
   transcripción.
5. Vídeo Solar: retirarlo, rotularlo o re-renderizarlo (el README ya lo avisa).

## Lo que la WEB debe cambiar (otra sesión)

1. **Texto nuevo `similarity.json` `texts.solar_similarity_saturation`**: enseñarlo en **cada par de Paneles**, junto a
   la similitud y las diferencias reales (`earth_solar_pairs.bin` `<v>.earth/.moon/.diff`), y en la **tarjeta de la
   misión** (es ya el primer elemento de `missions.json` `missions[solar].known_limitations`). No tiene placeholders,
   así que `pairSentencesAt` (`app/src/data/store.ts`) no lo recoge solo: hay que mostrarlo por su clave.
2. **Frase de Base lunar con la regla del contrato** (`texts.lunar_base_pair_sentence`, plantilla sin `display_rule`):
   `(raw float32 − subtract).toFixed(decimals)` sobre el valor leído del `Float32Array`, sin `f32Decimal` ni
   `Intl.NumberFormat`. Hoy `pairSentencesAt` usa la regla de Paneles para todas las plantillas; para las que no tienen
   `display_rule` debe usar `toFixed` (26 pares cambian, entre ellos el puesto 7). Así la web imprime lo mismo que
   `explain.json`. (O lo que decida el jefe de equipo, punto 3 de arriba.)
3. Las limitaciones del Rover (`known_limitations[3]`) y `not_used_by_engine.why` tienen texto nuevo; si la web los
   enseña, se actualizan solos. `variables.json` `levels.UNDOCUMENTED` dice ahora que ninguna variable lo tiene: no
   ofrecerlo en leyendas.
4. Nombres de lugar: "Nearest populated place" (`detailPanel.ts`) es ahora cierto en todas las celdas; no hay que cambiar
   código, pero cualquier captura o texto con nombres de celdas fuera del top 5 puede haber cambiado (8.281 celdas).
5. Los gemelos de Base lunar: si la web dice "in NASA's X region", usar "at the edge of" cuando menos de la mitad de la
   celda esté dentro (cuotas por celda en `docs/AUDIO_TOP5.json` `nasa_candidate_region_share_of_cell` para los 5; la
   web no tiene polígonos, así que lo más seguro es "a cell that touches NASA's X region").
6. Distancias habladas o escritas: redondear una vez desde el float32 (`nearest_place_km`, `feature_km`), no desde un
   valor de 1 decimal.

## Campos de `docs/AUDIO_TOP5.json` que cambian (los audios se grabaron con los valores anteriores)

Valores cambiados:

- `caveats`: nuevo `caveats[1]` (ancho de celda: "East-west a cell narrows towards the poles: the lunar twin of a Lunar
  base pair is only 1.3 to 3.4 km wide east-west (30 km north-south), so each Earth cell averages 88 to 224 times more
  ground than its twin (14 times for Solar panels, 39 to 53 for Rover)..."); el antiguo `caveats[1]` (ahora `[2]`) pasa
  de "Earth temperatures and ground sunlight are modelled climatologies (WorldClim, MODIS-based amplitude, modelled
  irradiance), not site measurements." a "Earth coldest air temperature and ground sunlight are modelled climatologies
  (WorldClim); the daily temperature swing is derived from MODIS land-surface temperature (daytime minus night-time
  overpass); none of them is a site measurement." Los demás avisos, iguales.
- `missions.lunar_base.zone`: "one of NASA's nine candidate landing regions near the lunar south pole" → "the 280 lunar
  cells that overlap NASA's nine candidate landing regions near the lunar south pole (the engine's zone: the 1-degree
  cell square intersects a region outline)".
- `missions.lunar_base.pairs[0..4].moon_place.zone`: el mismo cambio.
- `missions.lunar_base.pairs[0..4].common_traits[0].basis.populations.MOON`: "280 lunar cells of NASA's nine candidate
  regions" → "280 lunar cells overlapping NASA's nine candidate regions".
- `missions.lunar_base.pairs[0..4].say`: "in one of NASA's nine candidate landing regions near the lunar south pole" →
  "at the edge of NASA's <región> candidate region (<N> % of the cell lies inside it; its centre is outside), near the
  lunar south pole" (base_1 Haworth 0.4 %, base_2 de Gerlache Rim 2 7.8 %, base_3 Slater Plain 33 %, base_4 Nobile Rim 2
  45 %, base_5 Nobile Rim 2 0.3 %); además base_2 "about 16 kilometres from the crater Cartwright" → "about 15" y base_3
  "about 46 kilometres north of Burenhayrhan" → "about 45".
- `missions.lunar_base.pairs[2].earth_place.speakable` (base_3): "about 46 km north of Burenhayrhan, Hovd, Mongolia" →
  "about 45 km ...".
- `missions.solar.pairs[4].say` (solar_5): "about 82 kilometres from Rimae Pettit" → "about 83".

Campos nuevos (no había valor antes): en los 15 pares `earth_place.distance_km_spoken`, `earth_place.distance_rounding`,
`moon_place.distance_km_spoken`, `moon_place.cell_east_west_km`, `cell_area_km2` (`earth`, `moon`, `earth_over_moon`,
`earth_east_west_km`, `moon_east_west_km`, `rule`); en los 5 de Base lunar `moon_place.nasa_candidate_region_share_of_cell`,
`nasa_candidate_region_share_method`, `nasa_candidate_region_wording`, `nasa_candidate_region_wording_rule`,
`cell_centre_inside_nasa_candidate_region` (false en los 5).

Sin cambio: todos los ids, puntuaciones, variables, lugares, distancias a 1 decimal, direcciones, regiones, países y
rasgos lunares de los 15 pares, y el resto de `say` (Rover 1-5 y Paneles 1-4 idénticos).
