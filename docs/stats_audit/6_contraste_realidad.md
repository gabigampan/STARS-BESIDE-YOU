# Auditoría 6: contraste con la realidad (puntos B y C)

Auditor independiente (no escribió el código revisado). Fecha: 2026-11-15, todas las fuentes externas abiertas hoy.
Estado revisado: rama `final-integration`, motor en el commit `42d8bba` (tablas `tierra luna/output_real/*_real_1deg.csv`,
bundle `app/public/data/v2`, `docs/AUDIO_TOP5.json`). No se ha modificado nada fuera de `tierra luna/audit/p6_*.py`,
`tierra luna/audit/out/p6_*` y este fichero. No se ha generado, editado ni borrado ningún audio. Nada de lo externo se ha
copiado al modelo, a las tablas, al bundle ni a la web.

Veredictos: **punto 11 (B) NOT YET** (un valor lunar fuera de lo físicamente posible y dos cuestiones de definición con
efecto medido); **punto 12 (C) GO** (los 15 pares resisten el contraste externo; ningún audio necesita regrabarse por lo
encontrado aquí; quedan matices de redacción y una cuestión de diseño para el jefe de equipo).

## 0. Cómo se reproduce

Todos los scripts son deterministas y se lanzan con un solo comando cada uno (`PY` = el python del venv del equipo):

```
PY=/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/bin/python
$PY -I "tierra luna/audit/p6_ranges.py"                 # B: rangos de cada variable -> out/p6_ranges.csv, p6_ranges_checks.json
$PY -I "tierra luna/audit/p6_extremes.py"               # B: celdas extremas de tmin_c frente a estaciones GHCN -> out/p6_extremes.csv
$PY -I "tierra luna/audit/p6_lunar_ext.py"              # B/C: pendiente LOLA LDSM_16 como cota -> out/p6_lunar_ext.json
$PY -I "tierra luna/audit/p6_elev_mean_sensitivity.py"  # B: sensibilidad del Rover a la media de elevación -> out/p6_elev_mean_sensitivity.json
$PY -I "tierra luna/audit/p6_pairs.py"                  # C: top 5 frente al bundle, suelo firme, zonas, rasgos IAU -> out/p6_pairs.json
$PY -I "tierra luna/audit/p6_regions.py"                # C: parte de cada celda dentro de las 9 regiones NASA -> out/p6_regions.json
$PY -I "tierra luna/audit/p6_fetch_ext.py"              # C: NASADEM y estaciones GHCN-Daily -> out/p6_ext_dem.csv, p6_ext_stations.csv
$PY -I "tierra luna/audit/p6_power_gsa.py"              # C: Global Solar Atlas y NASA POWER frente a estación -> out/p6_power_gsa.json
```

Código propio (`p6_common.py`): lector del bundle por el índice del manifest, distancia de círculo máximo, cuantiles
ponderados por área e insolación TOA; no importa el motor. Las descargas externas (ficheros abiertos sueltos, sin cuenta
ni clave) se guardan en el scratchpad `.../7228bb30-.../scratchpad/ext/`, nunca en el repositorio. Los valores de NASA POWER
se obtuvieron con el conector NASA de solo lectura de la sesión (uso autorizado a las 10:36 solo para el punto C y solo
para lugares terrestres de los 15 pares) y se guardaron a mano, tal cual, en `ext/power/*.csv`.

## 1. Punto B (punto 11): cada variable frente a rangos publicados

### 1.1 Variables que usa alguna misión

Se toman de `mission_scoring.json` (puertas comunes, `require_present`, puertas, criterios blandos) y de
`engine_config.json` `real_value_similarity` (variables de similitud, zonas). En la Tierra `slope_deg` se lee de
`slope_iso_deg` (`datasets.json` `column_overrides`); la luz sobre la atmósfera de la Tierra es una fórmula
(`irradiance_toa_kwh_m2_day`); `elevation_rel_m` = elevación menos la media del cuerpo; `tmin_k` = `tmin_c` + 273.15.

### 1.2 Distribuciones (de `out/p6_ranges.csv`)

Columnas: n con valor; mínimo, P10, mediana, P90, máximo **sin ponderar**; la mediana ponderada (Tierra: cos(lat) x fracción
de tierra; Luna: cos(lat)) va entre corchetes. Todas son **medias de celda de 1 grado**, no valores puntuales.

| cuerpo | variable | n | mín (celda) | P10 | mediana [pond.] | P90 | máx (celda) |
|---|---|---|---|---|---|---|---|
| Tierra | elevation_m (m) | 25,245 | -2,569.9 (E38522, -17.5/-177.5) | 62.2 | 465.6 [445.8] | 2,889.9 | 5,420.3 (E20059, 34.5/79.5) |
| Tierra | slope_iso_deg (°) | 24,783 | 0.004 (E6812) | 0.101 | 0.480 [0.557] | 3.458 | 17.19 (E26795, 15.5/-24.5) |
| Tierra | roughness_m (m) | 25,121 | 0.01 (E33079) | 3.34 | 18.09 [21.92] | 129.8 | 559.1 (E40725) |
| Tierra | rock_or_bare_frac | 25,570 | 0 | 0 | 0.001 [0.003] | 0.773 | 1 |
| Tierra | irradiance_kwh_m2_day (suelo) | 25,484 | 1.412 (E7293, 69.5/-86.5) | 2.368 | 3.688 [4.335] | 5.484 | 6.440 (E28666, 10.5/46.5) |
| Tierra | irradiance_toa (fórmula) | 64,800 | 4.136 (89.5) | 4.258 | 7.366 | 9.851 | 9.973 (0.5) |
| Tierra | sun_elev_max_deg | 64,800 | 23.94 | 32.84 | 68.44 | 90 | 90 |
| Tierra | sun_low_frac_0_5deg | 64,800 | 0.058 | 0.059 | 0.087 | 0.182 | 0.211 |
| Tierra | lst_diurnal_amp_k (K) | 18,738 | -4.60 (E54133, -60.5/-46.5) | 3.58 | 8.54 [11.58] | 19.43 | 35.70 (E40430, -22.5/-69.5) |
| Tierra | tmin_c (°C) | 25,484 | -72.28 (E64663, -89.5/43.5) | -54.71 | -19.27 [0.66] | 17.21 | 26.29 (E31213, 3.5/73.5) |
| Tierra | temp_k (K, solo informativo) | 18,738 | 238.14 | 259.10 | 284.51 | 300.73 | 309.68 (E27580, Danakil) |
| Luna | elevation_m (m, esfera 1737.4 km) | 64,800 | -8,175.5 (M54391) | -2,780 | -776.3 [-629.5] | 2,388 | 9,101.9 (M30261) |
| Luna | slope_iso_deg (°) | 64,800 | 0.051 (M22156) | 0.895 | 4.910 [4.764] | 9.094 | 22.85 (M62113, -82.5/13.5) |
| Luna | roughness_m (m) | 64,800 | 1.57 | 35.74 | 159.7 [156.0] | 274.7 | 616.3 (M62113) |
| Luna | irradiance_kwh_m2_day | 64,800 | 0.000 (M63890, PSR) | 1.075 | 7.352 [9.003] | 10.256 | 10.395 (ecuador) |
| Luna | tmin_k (K) | 64,800 | 26.84 (M63564, -86.5/24.5) | 62.68 | 87.82 [91.36] | 94.17 | 114.04 |
| Luna | tmax_k (K) | 64,800 | 59.40 (M63895) | 251.65 | 353.58 [374.18] | 390.03 | **405.61 (M32647, -0.5/67.5)** |
| Luna | lst_diurnal_amp_k (K) | 64,800 | 30.68 | 188.87 | 265.56 [282.58] | 296.07 | **311.75 (M32647)** |
| Luna | temp_k (K, informativo) | 64,800 | 41.12 | 135.53 | 197.70 | 216.04 | 223.86 |

### 1.3 Contraste con lo publicado, variable a variable

Fuentes abiertas hoy (URL, fecha que muestra la página, frase o valor):

- **S1** WMO, nota "WMO verifies -69.6°C Greenland temperature as Northern hemisphere record",
  https://wmo.int/news/media-centre/wmo-verifies-696degc-greenland-temperature-northern-hemisphere-record (23-09-2020,
  actualizada 27-02-2023): "The world's coldest temperature record, of -89.2°C (-128.6°F) on 21 July 1983, is held by the
  high-altitude Vostok weather station in Antarctica."
- **S2** NASA Earth Observatory, "Where Is the Hottest Place on Earth?",
  https://science.nasa.gov/earth/earth-observatory/where-is-the-hottest-place-on-earth (05-04-2012, actualizada 08-12-2025):
  "The single highest LST recorded in any year, in any region, occurred there in 2005" / "when MODIS recorded a temperature
  of 70.7°C (159.3°F)" (Lut, Irán).
- **S3** Obu et al. 2019, Earth-Science Reviews 193:299-316, doi:10.1016/j.earscirev.2019.04.023 (PDF en
  https://par.nsf.gov/servlets/purl/10133773, página 1): "The modelled permafrost area (MAGT < 0 °C) covers 13.9 × 10^6 km2
  (ca. 15% of the exposed land area)" y "(permafrost probability > 0) is around 21 × 10^6 km2".
- **S4** Diviner (UCLA, equipo del instrumento), https://www.diviner.ucla.edu/science (copyright 2023): "At the lunar
  equator, mean surface temperatures reach almost 400K (260.6 ºF) at noon", "drop to below 100K ... during the night",
  "temperatures in these regions remain constant at around 220K" (bordes polares), "can fall as low as 25K" (PSR). Ya
  citada en `docs/sources/R3` F11-F13; R2 añade Williams et al. 2017 vía la página del equipo: "∼387–397 K ... at noon at
  the equator".
- **S5** Smith et al. 2017, "Summary of the Results from the Lunar Orbiter Laser Altimeter after Seven Years in Lunar
  Orbit", Icarus, doi:10.1016/j.icarus.2016.06.006 (manuscrito aceptado en NTRS,
  https://ntrs.nasa.gov/api/citations/20160008718/downloads/20160008718.pdf, aceptado 13-06-2016): "LOLA topographic
  extremes are about 19.92 km" ... "the deepest point, -9.129 km ... and the highest, 10.792 km"; y sobre pendientes:
  Rosenburg et al. (2011) midieron "over baselines ranging from ∼17 m to ∼2.7 km", exponente de Hurst "median value of
  0.95" en tierras altas y "0.76" en mares (pendiente decreciente con la base).
- **S6** Etiqueta PDS de LOLA `ldsm_16.lbl` (equipo LOLA, PRODUCT_CREATION_TIME 2012-06-15),
  https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldsm_16.lbl: "the
  slope baseline may vary from 30 to 120 meters"; el fichero `ldsm_16.img` (33,177,600 B) se descargó y se leyó.
- **S7** NSSDC, hojas de la Tierra y la Luna: "Solar irradiance (W/m2) 1361.0" (ya en R3 F1/F2).
- **S8** Global Solar Atlas (Banco Mundial / ESMAP, modelo Solargis 2.2.68, capa GHI "updated 2026-04-01", periodo hasta
  2025), consulta puntual abierta https://api.globalsolaratlas.info/data/lta?loc=LAT,LON.

| variable | publicado (fuente) | comparación | ¿coherente? |
|---|---|---|---|
| Tierra tmin_c | récord mínimo del aire -89.2 °C (S1) | mínimo de la tabla -72.28 °C (media mensual de mínimas, celda de 1°): por encima del récord, como debe | sí, como cota. **Pero** en la meseta antártica WorldClim se aparta de las estaciones (tabla 1.4) |
| Tierra temp_k / lst_diurnal_amp_k | LST máxima instantánea 70.7 °C (S2) | máximo de la tabla 309.68 K = 36.5 °C (media anual día/noche de celda): muy por debajo, como corresponde a una media | sí (cota; no hay rango oficial de amplitud LST, R3) |
| Tierra lst_diurnal_amp_k < 0 | físicamente posible solo sobre agua (el agua está más caliente de noche) | 9 celdas, todas con fracción de tierra <= 0.087 (lago Victoria E32972, Orcadas/Shetland del Sur); ninguna pasa ninguna misión | explicado, sin efecto |
| Tierra permafrost_area_frac | 13.9 x 10^6 km2 (MAGT < 0) y 21 x 10^6 km2 (probabilidad > 0) en el hemisferio norte (S3) | suma de probabilidad x fracción de tierra x área: 13.93 x 10^6 km2 en el HN | sí (la suma de probabilidades es el área esperada, cercana al 13.9 del modelo de origen) |
| Tierra irradiance (suelo) | no puede superar la TOA de su latitud; GSA en la celda máxima E28666: 2,308 kWh/m2/año = 6.32 kWh/m2/día (S8) | 0 celdas por encima de la TOA; cociente suelo/TOA mediana 0.54, máximo 0.92; E28666: 6.44 (+1.9 % sobre GSA) | sí, salvo la meseta antártica (cociente 0.90-0.92, ver fallo B3) |
| Tierra irradiance_toa (fórmula) | 1361 W/m2 (S7); POWER `TOA_SW_DWN` (CERES SYN1deg) en (-16.5, 124.5), 2020: 9.603 kWh/m2/día | fórmula propia 9.599; par del bundle 9.6005 (diferencia 0.04 %) | sí |
| Tierra elevation_m | (cota interna: la celda media no puede superar el punto más alto; REAL_DATA 6.2 halla Everest 8,157 m en el píxel ETOPO) | máximo 5,420 m (meseta del Tíbet). Mínimo -2,569.9 m en E38522 con fracción de tierra 0 y 1 píxel DEM: artefacto costero conocido (REAL_DATA 9) | sí, salvo E38522 (sin efecto en rankings, pero entra en la media del cuerpo: fallo B2) |
| Tierra slope_iso_deg, roughness_m | sin rango publicado a 3.7 km / 1.85 km; contraste independiente con NASADEM (SRTM, misión distinta de la Copernicus GLO-30 que usa ETOPO 2022, ver 2.2) | en las 15 celdas de los pares: pendiente |Δ| <= 0.13°, rugosidad |Δ| <= 1.4 m en interior (3.4 m en una costera) | sí |
| Luna elevation_m | extremos puntuales -9.129 y +10.792 km (S5) | medias de celda -8.18 a +9.10 km, dentro | sí |
| Luna slope_iso_deg | pendiente LOLA LDSM a 30-120 m de base (S6), cota superior porque la pendiente baja con la base (S5) | mediana LDSM 8.08° frente a 4.91° de la tabla; cociente P10/P50/P90 1.20/1.66/4.39; la tabla supera a LDSM en 824 de 64,800 celdas (1.3 %, mediana 77.5° de latitud: celdas polares estrechas) | sí, salvo 1.3 % de celdas polares sin explicar del todo (sin efecto medido) |
| Luna tmin_k | PSR "as low as 25K" (S4) | mínimo 26.84 K (M63564, -86.5) | sí |
| Luna tmax_k | "almost 400K" / ~387-397 K en el ecuador (S4) | mediana 0-10 N 391.4 K; 23 semiceldas de 0.5° entre 400 y 405 K; **una semicelda de 439.0 K** (lat -0.25, lon 67.25) lleva la celda M32647 a 405.61 K | **no**: 439 K está por encima del equilibrio radiativo de una superficie al Sol a 1 UA y de todo lo publicado (fallo B1) |
| Luna lst_diurnal_amp_k | ~295 K en el ecuador (R3 D6); ~0 en bordes polares a 220 K (S4) | P90 296.1 K; máximo 311.75 K en M32647 (mismo artefacto) | sí salvo M32647 |
| Luna irradiance | 1361/π x 24 h = 10.4 kWh/m2/día en el ecuador (R3 D4) | 10.395; en |lat| < 65 coincide con la fórmula plana propia a 0.0005; en los casquetes siempre por debajo (topografía) | sí |
| Luna/Tierra sun_elev_max, sun_low_frac | fórmulas exactas (REAL_DATA 6.1 ya las recomprobó con otro método) | rangos 23.94-90° (Tierra), 2.04-90° (Luna; 1.54° de oblicuidad + 0.5° de celda) | sí |

### 1.4 Celdas extremas de tmin_c frente a estaciones oficiales (NOAA NCEI GHCN-Daily)

Estaciones del inventario `ghcnd-stations.txt` / `ghcnd-inventory.txt` (https://www.ncei.noaa.gov/pub/data/ghcn/daily/,
descargados hoy) y ficheros de estación `.../global-historical-climatology-network-daily/access/<ID>.csv`; media del mes
más frío de las mínimas diarias, meses con >= 20 días, sin valores con marca de calidad (`out/p6_extremes.csv`):

| celda (tmin_c de la tabla) | estación (distancia) | periodo | media mín. mes más frío | diferencia tabla - estación |
|---|---|---|---|---|
| E64663 -89.5/43.5 (-72.28, la más fría) | AYW00090001 AMUNDSEN-SCOTT (55.6 km) | 1970-1996 | -63.86 | -8.4 K |
| celda de la estación (-89.5/-24.5): -59.24 | misma | 1970-1996 | -63.86 | +4.6 K |
| celda de Vostok (-78.5/106.5): -61.17 | AYM00089606 VOSTOK (9.9 km, 3,488 m) | 1990-2000 (incompleto) / 1990-2026 | -66.27 / -73.62 | +5.1 / +12.5 K |
| celda de Dome C (-75.5/123.5): -49.27 | AYM00089828 DOME C II (42.8 km) | solo 2025-2026 | -69.26 | +20 K |
| E31213 3.5/73.5 (26.29, la más cálida; celda sin elevación) | MV000043555 MALE (77.9 km) | 1981-1986 / 1981-2025 | 25.08 / 25.56 | +0.7 a +1.2 K |

WorldClim en la meseta antártica se aparta 5-20 K de las estaciones y cambia 13 K entre celdas vecinas del anillo de 89.5 S.
Está documentado (REAL_DATA 9: Dome C -49 frente a unos -70) y **no cambia ningún ranking**: Lunar base exige
`lst_diurnal_amp_k`, que no existe en la Antártida (0 celdas antárticas pasan Lunar base, `earth_lunar_base.bin`); Rover y
Solar no usan tmin_c. Sí se muestra en la ficha de cada celda (`earth_base.bin` `v.tmin_c`).

### 1.5 Fallos del punto B

**B1. Temperatura máxima lunar imposible en M32647 (no cambia ningún par).** En la reducción de Diviner GCP
(`.../realdata/moon/reduced/gcp_10s00s.npz`), la semicelda (-0.25, 67.25) tiene tmax = 439.0 K mientras sus vecinas dan
391.0-396.0 K (nvalid 53, hueco máximo 5 bins); de 259,200 semiceldas, ninguna otra pasa de 405.1 K. Lleva a la celda
M32647 a tmax 405.61 K y amplitud 311.75 K (máximos de la tabla) y a temp_k a su valor. 439 K es más de lo que publica
el equipo Diviner (S4: "almost 400K") y más que el equilibrio radiativo de una superficie al Sol a 1 UA. No afecta a ningún
par: M32647 (ecuador) no está en ninguna zona que use temperatura (la de Lunar base son las 280 celdas polares) y la
temperatura no entra en la similitud de Solar. Sí se muestra en el mapa lunar (`moon_base.bin` `v.lst_diurnal_amp_k`,
`v.temp_k`). Corrección sin tocar criterios: en `tierra luna/real_data/build_moon.py` (`_reduce_gcp_file` / paso
`step_diviner_gcp`), descartar como no válido un bin de tiempo local cuya tbol supere por más de un umbral fijo (por ejemplo
+20 K) la mediana de sus 8 vecinas, o el máximo físico de 400 K, recalcular M32647 y anotarlo en `validity.json`
(`engine_config.json` `on_invalid_value: report` ya prevé avisar de un valor fuera de rango). Es una corrección de dato,
no de diseño.

**B2. La media de elevación de la Tierra cuenta igual las celdas costeras casi sin tierra (decisión del jefe de equipo).**
`elevation_rel_m` resta la media cos(lat) de "every Earth cell with a value" = 695.92 m; entran 3,023 celdas con fracción de
tierra < 0.3 (entre ellas E38522, -2,569.9 m con fracción 0). La media del área de tierra (cos(lat) x fracción de tierra) es
810.71 m; la de las celdas que pasan las puertas comunes, 787.47 m (para orientación: una preimpresión arXiv 1810.08658
da 796 m a partir de ETOPO1 y enciclopedias citan 840 m; son pistas, no fuentes). Medido con mi propia implementación de
la regla del Rover, que reproduce el bundle con la media actual (10,192 pares, 0 gemelos distintos, |Δ similitud| <= 0.01;
`out/p6_elev_mean_sensitivity.json`): con 810.71 m el top 5 del Rover pasa a ser E15395, E16121, E20752, E18280, E16478;
de los cinco lugares grabados solo siguen E15395 (5.º -> 1.º) y E18280 (4.º -> 4.º); E17566 cae al 7.º. Cambiar la
ponderación cambia el criterio decidido ("relative to the area-weighted mean of every Earth cell with a value"), así que
**no se corrige**: opciones para el jefe de equipo: (a) mantener 695.92 m y decirlo así (el top 5 y los audios no cambian);
(b) ponderar por fracción de tierra (810.71 m: 3 de 5 audios del Rover cambiarían de lugar); (c) usar solo las celdas que
pasan las puertas comunes (787.47 m: no medido el top 5). La sensibilidad muestra que el orden del Rover depende de una
elección de ~115 m en una variable secundaria de tolerancia 500 m.

**B3. Luz en el suelo de la meseta antártica, no establecida.** El cociente suelo/TOA llega a 0.92 (E63337, -85.5/157.5:
3.845 frente a 4.163 kWh/m2/día) y es 0.90 en el polo. No supera la TOA (no es imposible), pero es alto para una media anual
y no encontré hoy una fuente oficial de la radiación anual medida en la estación South Pole (BSRN, PANGAEA requiere localizar
cada fichero mensual; Global Solar Atlas no cubre al sur de 60 S: sin GHI en E63337). Efecto: ninguno en rankings (Solar:
6,060 celdas antárticas pasan pero 0 tienen gemelo; Lunar base: 0), pero el valor se muestra como diferencia informativa en
los 1,101 pares antárticos del Rover. Propuesta: añadir a la ficha de variables que WorldClim srad en Antártida es
interpolación con muy pocas estaciones, o contrastarlo con BSRN SPO antes de mostrarlo.

**B4 (menor). LST mezcla agua.** `n_lst_px` = 14,400 en E32972 con fracción de tierra 0.008: la LST de una celda promedia
también píxeles de lago. Explica las 9 amplitudes negativas; ninguna pasa una misión. Documentarlo en `variables.json`.

## 2. Punto C (punto 12): los 15 pares frente a fuentes externas independientes

### 2.1 Los 15 pares son el top 5 actual del bundle

`out/p6_pairs.json` `top5_vs_bundle`: decodificando `earth_<misión>.bin` (rank 1-5, `twin`, `similarity`, `suitability`,
`final`) con el índice del manifest, los 15 pares de `docs/AUDIO_TOP5.json` son idénticos en las tres misiones (Tierra,
Luna y las tres puntuaciones a 0.01). Lugares distintos: 15 celdas terrestres; 11 lunares (los cinco pares del Rover
comparten M59895, Casatus). Cuatro celdas de Solar (E38464, E38105, E37746, E38465) están en el Kimberley (Australia
Occidental), a 1-2° unas de otras; cada una se comprueba por separado y POWER solo se consulta en E38464 como representante.

### 2.2 Independencia de cada contraste

| valor del modelo | origen del modelo | contraste usado | ¿independiente? |
|---|---|---|---|
| elevation_m, slope, roughness (Tierra) | ETOPO 2022, cuya topografía terrestre procede de Copernicus DEM GLO-30 y FABDEM (MacFerrin et al. 2025, ESSD 17:1835, https://essd.copernicus.org/articles/17/1835/2025/, publicado 08-05-2025, sección 3: "the Copernicus DEM 30 m global digital elevation model (GLO-30)") | NASADEM HGT v001 (NASA/JPL, reproceso de SRTM, febrero de 2000; copia COG abierta de Microsoft Planetary Computer, `nasademeuwest.blob.core.windows.net/nasadem-cog/v001/NASADEM_HGT_<tile>.tif`, leída a 1/12 de resolución), con las mismas definiciones de pendiente y rugosidad, código propio | sí (radar SRTM de 2000 frente a TanDEM-X) |
| tmin_c (Tierra) | WorldClim 2.1, interpolación de estaciones 1970-2000 con covariables MODIS (pista: resumen de Fick & Hijmans 2017, Int. J. Climatol. 37:4302, doi:10.1002/joc.5086, leído en buscador; ADS devolvió 405) | estación GHCN-Daily más cercana; tablas oficiales de la BoM (Australia) | **parcialmente no independiente**: la estación puede ser una de las que WorldClim interpoló. Lo que se pone a prueba es la interpolación y el paso a celda de 1°, no el dato de origen |
| tmin_c (Tierra) | WorldClim | NASA POWER `T2M_MIN` = MERRA-2 (cabecera del propio POWER y https://power.larc.nasa.gov/docs/methodology/: "Surface meteorological parameters (MERRA-2, GEOS-IT)") | sí |
| irradiance (suelo, Tierra) | WorldClim srad | NASA POWER `ALLSKY_SFC_SW_DWN` = CERES SYN1deg (cabecera POWER; página de metodología: "Solar and thermal-IR radiative fluxes (CERES SYN1deg, FLASHFlux, GEWEX SRB R4-IP)"); Global Solar Atlas (Solargis, satélites geoestacionarios) | sí (ninguna fuente de la tabla usa CERES ni Solargis, `provenance_earth.csv`) |
| irradiance_toa (Tierra, similitud Solar) | fórmula | POWER `TOA_SW_DWN` (CERES SYN1deg) | sí |
| lst_diurnal_amp_k (Tierra) | MODIS MOD11A2 10:30 - 22:30 | rango diario del aire de la estación (Tmax - Tmin) | magnitud distinta (aire frente a superficie; dos pasos frente a extremos): solo orden de magnitud |
| slope (Luna) | LOLA LDEM_16, base 3.79 km | LOLA LDSM_16, base 30-120 m (S6) | mismo altímetro, otro producto: cota, no igualdad |
| tmin/tmax lunar | Diviner GCP | Moon Trek: capas Diviner polares (p. ej. `polar_south_80_summer_avg`) solo como PNG con estirado de color sin escala publicada en la capa; Diviner PRP (604,800,210 B por polo) supera el presupuesto de descarga | **no establecido** cuantitativamente; solo cotas publicadas (S4) |

### 2.3 Lado terrestre: valores frente a fuentes externas (`out/p6_ext_dem.csv`, `p6_ext_stations.csv`, `p6_power_gsa.json`)

Elevación y relieve (tabla / NASADEM):

| celda | uso | elevación m | pendiente ° | rugosidad m |
|---|---|---|---|---|
| E17566 | Rover 1 | 1,433.4 / 1,433.5 | 1.038 / 1.029 | 43.53 / 42.95 |
| E23945 | Rover 2 | 1,457.8 / 1,457.9 | 1.215 / 1.249 | 43.37 / 43.33 |
| E18282 | Rover 3 | 1,443.6 / 1,444.8 | 0.908 / 0.915 | 38.75 / 38.65 |
| E18280 | Rover 4 | 1,547.4 / 1,548.0 | 1.131 / 1.080 | 48.91 / 47.49 |
| E15395 | Rover 5 | 1,658.4 / 1,658.3 | 1.236 / 1.224 | 41.33 / 41.18 |
| E38464 | Solar 1 | 137.3 / 113.7 (*) | 0.976 / 0.846 (*) | 39.20 / 35.83 (*) |
| E38105 | Solar 2 | 296.6 / 283.8 (*) | 1.132 / 1.150 | 42.53 / 42.54 |
| E38744 | Solar 3 | 143.6 / 137.6 | 0.706 / 0.694 | 29.64 / 29.19 |
| E37746 | Solar 4 | 159.4 / 144.2 (*) | 0.757 / 0.714 | 26.93 / 26.27 |
| E38465 | Solar 5 | 403.7 / 404.7 | 0.920 / 0.897 | 33.25 / 33.37 |
| E17538 | Base 1 | 3,502.9 / 3,500.5 | 6.652 / 6.670 | 238.81 / 239.14 |
| E16830 | Base 2 | 1,584.2 / 1,584.7 | 3.066 / 3.143 | 118.63 / 119.78 |
| E15751 | Base 3 | 2,261.0 / 2,259.2 | 4.673 / 4.773 | 164.12 / 164.90 |
| E21054 | Base 4 | 1,733.1 / 1,732.5 | 3.257 / 3.278 | 119.49 / 120.31 |
| E17187 | Base 5 | 2,007.2 / 1,987.7 | 4.665 / 4.663 | 173.53 / 173.01 |

(*) Celdas costeras: la tabla promedia solo píxeles de tierra y NASADEM pone el mar a 0 m; E38464 tiene 17.8 % de agua
(137.3 x 0.82 = 113 m, igual a NASADEM). En interior la elevación coincide a <= 2.4 m salvo E17187 (19.5 m, 0.97 % de su
superficie es agua/lago). Todas las diferencias caben en la escala; ninguna cambiaría un par (tolerancias 2°, 30 m, 500 m).

Temperatura mínima del mes más frío (tabla WorldClim 1970-2000 / estación GHCN, mismo periodo salvo lo dicho; elevación de la
estación frente a la media de celda):

| celda | tabla °C | estación (km, m de altitud) | estación °C (periodo) | diferencia | lectura |
|---|---|---|---|---|---|
| E17566 | -18.27 | CHM00053231 HAILS (11.2 km, 1,510 m) | -18.65 (1970-2000) | +0.4 | coincide |
| E23945 | 3.79 | AG000060680 TAMANRASSET (78.1 km, 1,362 m; celda 1,458 m) | 5.12 (1970-2000) | -1.3 | coherente con 96 m más de altura media |
| E18282 | -15.73 | CHM00052681 MINQIN (108.8 km, 1,367 m) | -15.11 (1970-2000) | -0.6 | coincide |
| E18280 | -17.25 | CHM00052533 JIUQUAN (175.3 km, 1,478 m) | -14.93 (1970-2000) | -2.3 | estación lejana y más baja: dentro de lo esperable |
| E15395 | -26.75 | MG000044272 ULIASTAI (104.9 km, 1,759 m); MGM00044277 ALTAI (134.9 km, 2,181 m) | -27.85; -26.34 (1975-2000) | +1.1; -0.4 | coincide |
| E38464 | 15.56 | ASN00001009 KURI BAY (112.6 km, 12 m) | 18.95 (1970-2000) | -3.4 | estación en la costa (el mar suaviza el mínimo); la BoM, Derby Aero 003032 (131.7 km): mínima media de julio 14.6 °C (1972-2026) -> +1.0 |
| E38105 | 13.24 | ASN00001025 DOONGAN (88.0 km, 385 m) | 10.92 (1988-2000) | +2.3 | periodo corto, interior |
| E38744 | 16.15 | MAM00067037 BESALAMPY (84.3 km); MAM00067073 MAINTIRANO (78.6 km, costa) | 16.11 (1980-1992); 18.40 (1977-2000) | 0.0; -2.3 | coincide con la de interior |
| E37746 | 13.71 | ASN00001021 KALUMBURU MISSION (27.4 km, 23 m) | 14.07 (1970-2000) | -0.4 | coincide; la BoM, Kalumburu 001019: julio 13.9 °C (1998-2026) -> -0.2 |
| E38465 | 11.74 | ASN00003051 MOUNT BARNETT (50.9 km, 401 m) | 8.49 (1983-1993) | +3.3 | periodo corto (11 años) fuera de 1970-2000; diferencia grande pero el par Solar no usa tmin |
| E17538 | -24.54 | KG000036982 TIAN-SHAN (48.0 km, 3,639 m; celda 3,503 m) | -29.23 (1970-2000) | +4.7 | estación 136 m más alta y en collado frío; el par Lunar base usa la posición de tmin (percentil 8.4): un error de 4.7 K movería el percentil, no establecido cuánto |
| E16830 | -18.86 | CHM00051379 QITAI (94.4 km, 794 m) | -23.00 (1970-2000) | +4.1 | estación 790 m más baja en una cuenca con inversión térmica (más fría abajo en invierno): no comparable directamente |
| E15751 | -25.85 | MGM00044265 BAITAG (42.7 km, 1,186 m); CHM00051087 FUYUN (160.4 km, 827 m) | -29.33 (1971-2000); -26.08 | +3.5; +0.2 | valles con inversión; coherente en orden |
| E21054 | -1.52 | MO000060265 OUARZAZATE (147.5 km, 1,139 m); MO000060195 MIDELT (149.9 km, 1,508 m) | 2.06 (1973-2000); 0.71 | -3.6; -2.2 | celda 225-594 m más alta: coherente con un gradiente de 6.5 K/km |
| E17187 | -18.35 | CHM00051463 URUMQI (145.1 km, 947 m); CHM00051656 KORLA (140.2 km, 933 m) | -16.71; -12.35 | -1.6; -6.0 | estaciones 1,060 m más bajas: coherente |

Rango diario: el aire de las estaciones da 10-17 K (p. ej. Hails 12.2 K, Kalumburu 13.7 K) frente a una amplitud LST de
11.3-24.8 K en la tabla. Son magnitudes distintas (superficie a las 10:30 y 22:30 frente a extremos del aire); en las zonas
áridas la LST de día supera a la del aire, así que una amplitud LST mayor que el rango del aire es lo esperable. No es una
contradicción.

Luz en el suelo (tabla WorldClim / Global Solar Atlas en el centro de la celda; el valor dicho en el audio Solar entre
paréntesis):

| celda | tabla kWh/m2/día | GSA | diferencia |
|---|---|---|---|
| E38464 (Solar 1, "6.2") | 6.177 | 6.105 | +1.2 % |
| E38105 (Solar 2, "6.1") | 6.110 | 6.024 | +1.4 % |
| E38744 (Solar 3, "6") | 5.967 | 5.802 | +2.8 % |
| E37746 (Solar 4, "6.1") | 6.071 | 6.002 | +1.1 % |
| E38465 (Solar 5, "6.1") | 6.140 | 6.057 | +1.4 % |
| Rover y Lunar base | | | entre -10.9 % (E15395) y +10.8 % (E17538, 3,503 m de media frente a 3,780 m en el punto GSA) |

Los cinco valores dichos en los audios de Solar coinciden con GSA a la décima salvo Solar 1 (6.2 frente a 6.1) y Solar 3
(6 frente a 5.8): diferencias del 1-3 %, dentro de lo que separa una celda de 1° de un punto y dos climatologías. Las
cifras "35-38 percent less" cambiarían como mucho un punto. No hace falta regrabar.

NASA POWER (segundo contraste, autorizado; producto POWER, versión no impresa en la cabecera del conector ni en la página de
metodología más allá de "Release 10"; comunidad RE, hora solar local):

| punto y periodo | parámetro (origen) | POWER | estación oficial, mismo periodo | modelo | lectura |
|---|---|---|---|---|---|
| E38464 (-16.5, 124.5), 2020-01-01..12-31 | ALLSKY_SFC_SW_DWN (CERES SYN1deg) | 6.107 kWh/m2/día | (BoM: la tabla principal de estadísticas no trae exposición solar; no establecido) | 6.177 (1970-2000) | coincide con POWER y con GSA (6.105) a 1.1-1.2 % |
| E38464, 2020 | TOA_SW_DWN (CERES SYN1deg) | 9.603 | - | fórmula 9.599 / bundle 9.6005 | coincide a 0.04 % |
| E38464, 2020 | T2M_MIN, mes más frío (MERRA-2; celda MERRA-2 de 0.5 x 0.625° a 74 m) | julio 16.94 °C | ASN00003032 DERBY AERO (131.7 km) julio 13.75; ASN00003080 CURTIN AERO (139.5 km) agosto 15.25 | 15.56 | POWER 1.7-3.2 K más templado que las estaciones de interior: explicable por la celda MERRA-2 casi costera; no es un desacuerdo fuera de escala |
| E38464, 2020 | T2M_RANGE (MERRA-2) | 11.46 K | Derby 13.42 K, Curtin 14.69 K | (LST 11.89) | MERRA-2 da 2-3 K menos de rango que las estaciones: sesgo conocido de los reanálisis; se señala, no afecta al modelo |
| E17566 (41.5, 106.5), enero 2020 | T2M_MIN (MERRA-2; celda a 1,336 m) | -13.61 °C | CHM00053231 HAILS (1,510 m) enero 2020: -15.46 | -18.27 (1970-2000) | POWER 1.9 K más templado que la estación en el mismo mes; 174 m de altura explican ~1.1 K; resto dentro de escala. La tabla es más fría que 2020 porque su climatología es 1970-2000 y la estación en 1970-2000 da -18.65 |

Solo se hicieron dos consultas a POWER (se cumplió "a handful" por lo bajo para no saturar el contexto con series diarias);
las demás celdas se contrastaron con estaciones y GSA.

Suelo firme (`out/p6_pairs.json` `earth`): fracción de tierra 0.82-1.00 en las 15 celdas; todas tienen el centro dentro de
la tierra de Natural Earth 1:110m. Las 10 de Rover y Lunar base están a 318-2,636 km de la costa, sin hielo (nieve/hielo CCI
220 <= 8.3 %, E17538 en el Tian Shan), sin agua (<= 0.23 %) y dominadas por suelo desnudo CCI 200 (36-100 %). Las 5 de
Solar están a 32-134 km de la costa (Natural Earth 110m, escala gruesa); su agua CCI 210 es 0-17.8 % (E38464, el estuario de
King Sound) y su cubierta dominante es matorral (122) o arbolado (110), no salar ni lago. Ninguna celda es un artefacto de
cuadrícula (el artefacto conocido de 1 píxel, E38522, no pasa ninguna puerta común).

### 2.4 Lado lunar (`out/p6_pairs.json` `moon`, `out/p6_regions.json`, `out/p6_lunar_ext.json`)

Regla de zona recalculada para las 11 celdas distintas: M59895 (Rover) lat -76.5 <= -75 sí; las 5 celdas de Solar |lat|
21.5-23.5 <= 30 y elevación -1,251 a -2,829 m <= -1,200 sí; las 5 de Lunar base intersecan una de las nueve regiones (mi
intersección propia en un plano estereográfico polar). Rasgo más cercano (gazetteer IAU del motor, primarios, distancia
propia): coincide en las 11 con el nombre y la distancia de `AUDIO_TOP5.json` y de los audios (Casatus 159.2 km "about 160";
Huxley 75.8 "76"; Struve 58.2; Thebit 61.3; Dziewulski 71.9; Rimae Pettit 82.5; Mons Malapert 25.1; Cartwright 15.5;
Slater 19.4; Wapowski 18.3; Oberbeck 15.9). Dos rasgos contrastados en la página oficial del gazetteer (USGS/IAU, abiertas hoy):
Mons Malapert https://planetarynames.wr.usgs.gov/Feature/16338 ("-85.98 °", "-1.67 °", "67.00 km", actualizada 04-08-2025)
y Casatus https://planetarynames.wr.usgs.gov/Feature/1040 ("-72.70 °", "-30.75 °", "102.85 km"): iguales al fichero del motor.
Nombres de región: la nota de NASA del 28-10-2024 (https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/)
lista "Haworth", "Malapert Massif", "Nobile Rim 2", "de Gerlache Rim 2", "Slater Plain" entre las nueve: los nombres son correctos.

Cuánto de cada celda de Lunar base está dentro de su región:

| par | celda (área km2) | región nombrada en el audio | parte de la celda dentro | centro a borde de región |
|---|---|---|---|---|
| Base 1 | M63528 (56.2) | Haworth | 0.43 % (0.24 km2) | 1.0 km fuera (Malapert Massif a 12.1 km) |
| Base 2 | M63841 (40.1) | de Gerlache Rim 2 | 7.8 % | 8.3 km fuera |
| Base 3 | M64018 (40.1) | Slater Plain | 33 % | 3.1 km fuera |
| Base 4 | M62517 (104.8) | Nobile Rim 2 | 44.5 % | 0.4 km fuera |
| Base 5 | M62523 (104.8) | Nobile Rim 2 | 0.32 % (0.34 km2) | 9.6 km fuera |

Ningún centro de celda está dentro de su región; la regla decidida ("the 1-degree cell square intersects the region
outline (an upper bound)") se cumple en las cinco. La frase de los audios "in NASA's ... candidate region" es exacta para la
regla pero generosa para Base 1 y Base 5 (menos del 0.5 % de la celda).

Pendiente lunar frente a LOLA LDSM (cota a 30-120 m): en las 11 celdas LDSM es mayor que la pendiente a km, como debe
(cociente 1.16-8.61). En M59895, el gemelo de los cinco Rover, la tabla da 1.15° y LDSM 4.42°: la frase "the ground slopes
gently, by about one degree" es cierta a la base de 3.8 km del modelo, no a la escala de una rueda (punto D de otro auditor).

Temperatura e iluminación lunar en el lugar: no establecido con una fuente independiente cuantitativa (2.2). Cotas
publicadas: las celdas de Lunar base tienen tmax 194-240 K y tmin 41-63 K, por debajo de los ~220 K constantes de los bordes
iluminados y por encima de los 25 K de las PSR (S4): coherentes con celdas que mezclan borde y sombra. Iluminación en las
celdas de Solar: geometría plana (`illum_frac_level` DERIVED_FLAT_GEOMETRY), igual a mi fórmula a 0.0005, sin contraste
independiente posible más allá de la constante solar (S7).

### 2.5 Fallos y matices del punto C

**C1 (redacción, decisión del jefe de equipo; no exige regrabar).** Base 1 (M63528, Haworth) y Base 5 (M62523, Nobile Rim 2):
solo 0.43 % y 0.32 % de la celda, centros a 1.0 y 9.6 km del borde. La región nombrada es la única que toca la celda (la
regla decidida). Opciones: (a) dejar el audio; (b) en la web (no en el audio) añadir "the cell touches the region's edge"
cuando la parte dentro sea < 5 %; (c) regrabar base_1 y base_5 con "at the edge of NASA's ... candidate region".

**C2 (dato mostrado, sin efecto en los pares).** E17538 (Base 1): WorldClim -24.54 °C frente a -29.23 °C en la estación
Tian-Shan (48 km, 136 m más alta). Como la similitud de Lunar base compara percentiles de tmin, un error de varios K en la
Tierra mueve la posición del lugar; no medido aquí (punto F). No se recomienda regrabar por esto.

## 3. Qué no se ha podido establecer

- Temperatura e iluminación lunares de las 11 celdas con un producto independiente cuantitativo (Moon Trek sirve PNG sin
  escala; Diviner PRP 605 MB por polo).
- Exposición solar media de la BoM en las estaciones del Kimberley (la tabla principal de estadísticas no la trae).
- Radiación anual medida en la estación South Pole (BSRN) para juzgar el cociente 0.92 de la meseta antártica (B3).
- Fuente oficial de la media de elevación de la tierra emergida (B2): solo pistas (arXiv 1810.08658, 796 m; enciclopedias, 840 m).
- Versión exacta de NASA POWER: el conector y la cabecera dicen "Source Native Resolution Daily Data" sin número de versión;
  la página de metodología habla de "Release 10".
- El resumen de Fick & Hijmans 2017 se leyó en un buscador (ADS devolvió 405): la afirmación sobre las covariables MODIS es una pista.
