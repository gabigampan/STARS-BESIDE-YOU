# Auditoría independiente: puntos 1 (datos de entrada), 2 (rejilla) y 7 (nombres de lugar)

Auditor independiente (no ha escrito código del motor ni de los constructores). Fecha: 2026-11-15. Estado auditado:
rama `final-integration`, motor en el commit `42d8bba`, bundle `app/public/data/v2` (contrato rev. 6),
`docs/AUDIO_TOP5.json` y `app/public/audio/transcripts.json` tal como están en disco. No se ha modificado nada del
repositorio salvo los scripts de `tierra luna/audit/p1_*.py`, sus salidas en `tierra luna/audit/out/p1_*` y este
fichero. No se ha generado, editado ni borrado ningún audio. No se ha consultado NASA POWER ni ningún servicio externo:
estos tres puntos se resuelven con el repositorio y las descargas brutas de `stars/realdata/`.
`docs/VALIDATION.md` se ha leído solo como pista; ninguna cifra de este informe sale de él.

## Cómo repetirlo

Con `PY=/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/bin/python`,
desde la raíz del repositorio (cada uno es determinista, tarda de 1 a 25 s):

    $PY "tierra luna/audit/p1_raw_cells.py"   # celdas recalculadas desde ETOPO, CCI y LDEM_16; lugares conocidos; convención de rejilla
    $PY "tierra luna/audit/p1_inputs.py"      # niveles y fuentes, unidades, océano/hielo/huecos en los rankings
    $PY "tierra luna/audit/p1_grid.py"        # tamaños de celda y bases; grep de toda frase de tamaño o resolución
    $PY "tierra luna/audit/p1_names.py"       # punto 7: 15 pares + muestra de 60 (semilla 20261115)
    $PY "tierra luna/audit/p1_regions.py"     # punto 7: solape de los gemelos de Base lunar con las regiones NASA (área real)

Código propio (no el del motor) en todo lo que se confirma: lector de los binarios del bundle, fórmula de id a
coordenada, distancia de gran círculo (forma vectorial atan2, no la haversine del motor), rumbo inicial y brújula de 8
puntos, vecino más cercano por fuerza bruta sobre todas las filas, percentil de rango medio, pendiente, rugosidad y
media ponderada recalculadas píxel a píxel desde los ficheros brutos, insolación por integración numérica (no la fórmula
cerrada del motor), intersección celda-región en proyección equivalente sobre la esfera lunar.

---

## Punto 1. Datos de entrada — **NOT YET**

Los datos que deciden los 15 pares son correctos: se reproducen desde los ficheros brutos al redondeo del CSV, las
unidades no se mezclan en ninguna fórmula y ningún punto en ranking es océano o le falta un valor requerido. Queda
**un hueco que no está explicado al usuario** (Rover pone en ranking 1.445 celdas de hielo) y hay textos de
procedencia desactualizados.

### 1.1 Fuente, nivel y unidad de cada variable usada (embudo o emparejamiento)

Comprobado leyendo `tierra luna/real_data/provenance_earth.csv`, `provenance_moon.csv` y
`app/public/data/v2/variables.json` (salida `out/p1_variables.csv`): **los 34 pares variable-cuerpo tienen el mismo
nivel en la procedencia y en el bundle** (`p1_inputs.json` → `level_disagreements: []`).

| variable (columna real) | Tierra: producto, versión, resolución nativa, periodo — nivel | Luna: producto — nivel | unidad |
|---|---|---|---|
| elevation_m | ETOPO 2022 v1, 60" (1,853 km), sobre geoide EGM2008, tierra solo — MEDIDO | LOLA LDEM_16 V3.1, 16 px/° (1,895 km), sobre esfera de 1737,4 km — MEDIDO | m |
| mask_fraction | ESA CCI LC 2020 v2.1.1, 1/360° (300 m) — MEDIDO | 1 por definición — MODELADO | 0-1 |
| slope (`slope_iso_deg`, por `column_overrides`) | derivada de ETOPO, base 3,706 km — DERIVADO | derivada de LDEM_16, base 3,790 km — DERIVADO | ° |
| roughness_m | deviograma ETOPO, desfase 1,853 km — DERIVADO | deviograma LDEM_16, desfase 1,895 km — DERIVADO | m |
| rock_or_bare_frac | CCI LC 2020 (clases 200-202, 150-153) — MEDIDO (clasificación) | 1 por definición — MODELADO | 0-1 |
| thermal_inertia_class | mapeo supuesto de CCI — MODELADO | "regolito" en todo — MODELADO | clase |
| lst_diurnal_amp_k | OpenLandMap MOD11A2 v006, 1 km, 2000-2017 (día−noche) — DERIVADO | Diviner GCP tbol *_002, 0,5° × 0,25 h, tmax−tmin — DERIVADO | K |
| tmin_c → `tmin_k` | WorldClim 2.1, 10', 1970-2000, aire 2 m — MODELADO | Diviner tmin_k superficie — MEDIDO (el CSV lo guarda en °C, DERIVADO solo por la conversión) | °C → K |
| irradiance_kwh_m2_day (embudo) | WorldClim 2.1 srad, en superficie — MODELADO | S0 = 1361 W/m² + geometría (+ AVGVISIB en los polos) — DERIVADO | kWh/m²/día |
| irradiance_toa (par Paneles) | fórmula de latitud (Kepler) — DERIVADO | la columna anterior — DERIVADO | kWh/m²/día |
| elevation_rel_m (par Rover) | elevation_m − media de tierra 695,924 m — DERIVADO | elevation_m − media lunar −248,389 m — DERIVADO | m |
| sun_elev_max_deg, sun_low_frac_0_5deg | fórmula, ε IAU 2006 — DERIVADO | fórmula, ε 1,54° — DERIVADO | °, 0-1 |
| permafrost_class (soft Base lunar) | Obu et al. PERPROB v5.0, 926,6 m — MODELADO | "ninguno" en todo — MODELADO | clase |

URL de cada producto: columna `url` de los dos CSV de procedencia (copiada en `out/p1_variables.csv`).

### 1.2 Recalculado desde los ficheros brutos (14 celdas)

`p1_raw_cells.py` lee directamente `ETOPO_2022_v1_60s_N90W180_surface.nc`, los `cci_lc_2020_*.tif` (para la máscara
de tierra: píxel de 60" con ≥ 18 de sus 36 píxeles CCI distintos de 210 y de 0) y `ldem_16.img` + `.lbl` (DN × 0,5,
longitud 0-360 este, muestra j centrada en (j+0,5)/16), y recalcula con código propio la elevación media ponderada por
cos(lat), la pendiente literal, la isotrópica y la rugosidad. Celdas: el nº 1 de cada misión en los dos cuerpos y otras
(`out/p1_raw_cells.csv`).

| celda | por qué | elevación propia / tabla (m) | pendiente iso propia / tabla (°) | rugosidad propia / tabla (m) |
|---|---|---|---|---|
| E17566 | Rover nº 1 | 1433,38 / 1433,4 | 1,0376 / 1,038 | 43,53 / 43,53 |
| E38464 | Paneles nº 1 (costera, tierra 0,82) | 137,33 / 137,3 | 0,9764 / 0,976 | 39,20 / 39,20 |
| E17538 | Base lunar nº 1 | 3502,89 / 3502,9 | 6,6524 / 6,652 | 238,81 / 238,81 |
| E23945, E18280, E21054, E38465 | Rover 2 y 4, Base 4, Paneles 5 | dif. ≤ 0,035 | ≤ 0,0004 | ≤ 0,003 |
| M59895 | gemelo Rover 1-5 | 584,87 / 584,9 | 1,1477 / 1,148 | 44,21 / 44,20 |
| M24296 | gemelo Paneles 1 | −1842,71 / −1842,7 | 1,0471 / 1,047 | 39,03 / 39,03 |
| M63528 | gemelo Base 1 (86,5 S) | 432,32 / 432,3 | 7,1791 / 7,179 | 238,49 / 238,49 |
| M63841, M40854, M24761 | gemelos Base 2, Paneles 3 y 4 | dif. ≤ 0,045 | ≤ 0,0005 | ≤ 0,004 |
| M32040 | prueba del antimeridiano (0,5 N, 179,5 O) | 2228,90 / 2228,9 | 5,2082 / 5,208 | 167,32 / 167,32 |

Diferencia máxima en las 14 celdas: elevación 0,045 m, pendiente literal 0,0005°, isotrópica 0,0005°, rugosidad
0,005 m: todo es el redondeo del CSV (1 decimal en m, 3 en °, 2 en m). La pendiente literal (`slope_deg`) también
coincide.

### 1.3 Unidades en cada paso (`out/p1_inputs.json`, bloque `units`)

- **Temperaturas.** Luna: `tmin_c − (tmin_k − 273,15)` máximo 6e-14 en 64.800 celdas; `lst_diurnal_amp_k − (tmax_k −
  tmin_k)` máximo 0,01 K (redondeo). Tierra: `tmin_k.earth` del bundle − (`v.tmin_c` + 273,15) máximo 1,5e-5 K en los
  2.419 puntos de Base lunar; `tmin_k.moon` − `tmin_k` de la tabla del gemelo máximo 3,7e-6 K. Las diferencias de
  temperatura (p. ej. "207 kelvin" de base_1) son K − K: tabla 248,61 − 41,23 = 207,4 (y 208,2 / 206,6 / 208,6 / 207,8
  para base_2..5, redondeados igual en las grabaciones). Ninguna fórmula mezcla °C con K. Lo que sí se comparan son
  magnitudes físicas distintas (aire a 2 m en la Tierra, superficie en la Luna); está escrito en `missions.json`
  `similarity.variables[].sides` y en AUDIO_TOP5, no en los audios (ver 7.3).
- **Irradiancia.** Tierra arriba de la atmósfera: mi integración numérica (3.653 días × 1.440 ángulos horarios, Kepler
  por Newton) difiere del bundle `d.irradiance_toa_kwh_m2_day` en ≤ 2,2e-6 kWh/m²/día en las 180 filas; a 0/30/45/60°
  da 9,974 / 8,765 / 7,367 / 5,672 (referencias del config 9,97 / 8,77 / 7,37 / 5,67). Luna: la columna de la tabla en
  |lat| < 65,5 difiere de mi integración con ε = 1,54° en ≤ 0,0019 kWh/m²/día. **Las dos son la misma magnitud**: media
  anual por 24 h sobre superficie horizontal sin atmósfera, con S0 = 1361 W/m². La de superficie terrestre (WorldClim
  srad, 1,412-6,44 kWh/m²/día sobre tierra) es otra magnitud y solo entra en el embudo; su cociente con la de arriba no
  pasa de 0,923 en ninguna celda (físicamente posible).
- **Bases de pendiente y desfases de rugosidad** (de los constructores, `build_earth.py` 169-292 y `build_moon.py`
  206-276, y reproducidos en 1.2): pendiente isotrópica con base 2 × 1,8533 = 3,7065 km (Tierra, R = 6371,0088 km) y
  2 × 1,8952 = 3,7904 km (Luna); rugosidad a 1,8533 / 1,8952 km en N-S y E-O. Cociente 1,023. Misma definición.
- **Elevación relativa.** Media propia ponderada por cos(lat): Tierra 695,924 m sobre 25.245 celdas con valor (solo
  tierra), Luna −248,389 m sobre 64.800; los valores `elevation_rel_m` del bundle se reproducen con ≤ 0,0004 m.

### 1.4 Océano, hielo y celdas sin dato

- El bundle guarda 25.497 celdas con algo de tierra (`mask_fraction > 0`); las 39.303 de océano puro no entran en
  ningún fichero Earth. Puertas comunes sobre esas 25.497: `mask_fraction < 0,3` elimina 3.275; `elevation_m` sin dato
  252; `elevation_m < 1` 177; pasan las dos 22.185. Huecos: LST 6.761 (la Antártida entera, OpenLandMap llega a ~62 S),
  tmin 49, pendiente isotrópica 714, rugosidad 376.
- **Puntos en ranking (`rank` finito) por misión** (`ranked_integrity`):

| misión | en ranking | océano (mask 0) | mask < 0,3 | sin elevación | sin un valor del par | hielo (snow_ice_frac ≥ 0,5 o clase "hielo") | Antártida (≤ 60 S) |
|---|---|---|---|---|---|---|---|
| Rover | 10.192 | 0 | 0 | 0 | 0 | **1.445** (1.101 antárticas, 217 en Groenlandia) | 1.101 |
| Paneles | 6.360 | 0 | 0 | 0 | 0 | 0 | 0 |
| Base lunar | 450 | 0 | 0 | 0 | 0 | 0 | 0 |

  En Rover el hielo no llega a lo alto: 0 en los 500 primeros, 6 en 501-1.000 (el primero en el puesto 722, E3467,
  80,5 N 47,5 E), 89 en 1.001-2.000, 315 en 2.001-5.000, 1.035 por debajo. Además 816 celdas de Rover en ranking tienen
  clase dominante "agua" con ≥ 30 % de tierra; sus valores salen solo de los píxeles de tierra (es correcto).

### 1.5 Convención de coordenadas

Las dos tablas: 64.800 ids únicos, `cell_id` = inicial + `row·360+col`, `lat = 89,5 − row`, `lon = −179,5 + col`
(centro de celda), longitudes −179,5..179,5 este-positivas, latitud norte positiva (`p1_raw_cells.json` → `grid`).
El bundle (`manifest.json` `grid`) y la web (`app/src/data/store.ts` 744-756 y 985-993) usan la misma fórmula. LDEM_16
viene en 0-360 E (`WESTERNMOST_LONGITUDE = 0`, `POSITIVE_LONGITUDE_DIRECTION = EAST`) y la celda del antimeridiano
M32040 cuadra con la lectura directa; el gacetero IAU es 0-360 E y se convierte con `lon − 360` si `lon > 180`
(comparado contra el shapefile bruto del zip: 2.023 rasgos no satélite, 0 sin emparejar, diferencia 0,0 en lat y lon).
La Tierra usa latitud geodésica WGS84 (hasta 0,19° de la geocéntrica), declarado en `datasets.json` `grid`.

**Lugares conocidos en su celda** (`out/p1_named_places.csv`): Tycho (−43,30; −11,22) → M48048, Copernicus → M28959,
Plato → M13850, Aristarchus → M23892, Shackleton → M64749, Casatus → M58469, Huxley → M25015, Mons Malapert → M63178:
los 8 caen dentro de la celda cuyas coordenadas da la tabla, y los 3 que figuran en `real_data/lunar_named_sites.csv`
(Tycho, Shackleton, Mons Malapert) tienen la misma celda. Prueba física: el centro de los cráteres de más de 60 km está
más bajo que el anillo de celdas a 0,8-1,2 radios (Tycho −3.079 m frente a +65 m; Copernicus −3.359 frente a −472;
Plato −2.514 frente a −1.520; Casatus −2.911 frente a −61). Tierra, con las coordenadas de GeoNames del fichero del
motor: Tamanrasset → E24305, Tinghir → E21054, Derby → E38823, Kununurra → E38108, Maintirano → E39104, Aheqi → E17898;
los 6 caen dentro de su celda y el bundle nombra a ese mismo lugar como el más cercano de su celda, a la distancia que
recalculo (p. ej. Tinghir 3,5123 km).

### 1.6 Fallos

1. **Rover pone en ranking 1.445 celdas de hielo sin decirlo al usuario.** Dónde: `missions.json`
   `missions[rover].known_limitations` (desde `datasets.json` real_1deg `mission_notes.rover`) solo dice "polar
   deserts, ice-free Arctic plateaus and steppe score alike"; nada sobre casquetes de hielo. Corrección de texto (no
   cambia ningún criterio): añadir a esa nota "1,445 of the 10,192 ranked Rover points are ice-sheet or snow-and-ice
   cells (1,101 in Antarctica, 217 in Greenland); none ranks in the top 500 and the best is 722; the funnel has no
   surface-type gate". **Cuestión de diseño** (para el jefe de equipo, no se corrige): excluirlas o no. Opciones: (a)
   dejarlo y explicarlo (efecto nulo en el top 500 y en los audios); (b) puerta `thermal_inertia_class` excluye
   "hielo" como ya hacen Paneles con "agua" (quitaría 1.268 puntos); (c) puerta `snow_ice_frac < 0,5` (quitaría
   1.424). Ninguna toca los 5 pares de Rover (no hay hielo en los 500 primeros); el orden de los puestos > 722 sí cambia.
2. **`docs/REAL_DATA.md` dice que el permafrost lunar está vacío y en la tabla vale "ninguno" en las 64.800 celdas.**
   Líneas 138 ("no data … empty, not 0"), 200 ("permafrost, rain and wind are empty in all 64,800 cells") y 250;
   también `tierra luna/real_data/README.md` 59 y 75. La tabla, `provenance_moon.csv` (fila permafrost_class:
   MODELLED, decisión del 2026-11-14) y `variables.json` dicen "ninguno"/MODELLED. Corrección: alinear esas 5 líneas
   con la procedencia. Además ese valor **no tiene efecto** en ningún resultado (las celdas lunares no pasan por el
   embudo; `permafrost_class` solo es criterio blando en la Tierra): propuesta, justificarlo como etiqueta de
   presentación o dejar de exportarlo en `moon_base.bin`.
3. **`docs/REAL_DATA.md` línea 282 llama a la irradiancia terrestre "measured-climatology surface radiation"**; está
   etiquetada MODELLED (WorldClim interpolado) en la procedencia y el bundle. Corrección: "modelled (WorldClim)
   surface radiation".
4. **`docs/AUDIO_TOP5.json` `caveats[1]`** mete la amplitud de MODIS entre las "modelled climatologies"; en la
   procedencia es DERIVED de LST medida. Corrección: "WorldClim air temperature and ground sunlight are modelled;
   the daily swing is derived from MODIS land-surface temperature".
5. **Cuestión de diseño, puerta común `elevation_m ≥ 1`.** Su porqué ("descarta océano, que el modelo fija en
   −250 m", `mission_scoring.json` `common_gates`) era para el relleno de océano de la tabla antigua; la tabla real no
   tiene relleno (el océano está vacío). Hoy elimina 177 celdas de tierra reales bajo el nivel del mar, 37 con
   ≥ 30 % de tierra y 22 con ≥ 90 % (la más baja, E21807, 29,5 N 27,5 E, −45,8 m, clase desnuda 200; varias en la
   depresión al norte del Caspio, 46-48 N 46-54 E). Opciones: mantenerla (estas 37 nunca pueden ser análogo) o
   sustituirla por "elevation_m con valor". El efecto sobre los rankings no está establecido (no recalculado).

---

## Punto 2. Rejilla — **GO** (con dos correcciones de texto)

### 2.1 Tamaño real de las celdas

1° en los dos cuerpos. N-S: 111,195 km en la Tierra (esfera de 6371,0 km; la columna `cell_km` da el arco WGS84,
110,574-111,694 km) y 30,323 km en la Luna (1737,4 km). E-O = N-S × cos(lat). En los 15 pares
(`out/p1_grid_sizes.csv`, `p1_grid.json`):

| misión | Tierra: lat, E-O, área | Luna: lat, E-O, área | área Tierra / Luna |
|---|---|---|---|
| Rover 1-5 | 23,5-47,5 N; 75-102 km; 8.353-11.339 km² | 76,5 S; 7,08 km; 214,7 km² | 38,9-52,8 |
| Paneles 1-5 | 14,5-17,5 S; 106-108 km; 11.792-11.970 km² | 21,5-23,5; 27,8-28,2 km; 843-856 km² | 13,9-14,0 |
| Base lunar 1-5 | 31,5-46,5 N; 77-95 km; 8.511-10.542 km² | 83,5-87,5 S; **1,32-3,43 km**; 40-104 km² | **87,6-223,6** |

En los gemelos de Base lunar a 87,5 S la celda lunar mide 30,3 × 1,32 km: más estrecha que la base de la pendiente
(3,79 km) y que el desfase de la rugosidad (1,90 km), así que sus diferencias E-O usan terreno fuera de la celda.

### 2.2 ¿Se comparan cosas medidas igual?

Sí en la métrica, no en el área. La pendiente y la rugosidad se calculan a la misma base física en los dos cuerpos
(3,71 frente a 3,79 km; 1,85 frente a 1,90 km; 1.2 y 1.3), de modo que el valor de un píxel significa lo mismo. Lo que
cambia es sobre cuánto terreno se promedia: 3.600 píxeles de 60" en la Tierra (solo los de tierra) frente a 256 de
LDEM_16 en la Luna; en área, de 14 a 224 veces más en la Tierra. Las temperaturas terrestres promedian ~36 píxeles de
WorldClim (10') o ~14.400 de MODIS (1 km); las lunares, 4 celdas Diviner de 0,5°. Es una propiedad del diseño (rejilla
común en grados) y se puede decir con honestidad en un texto: **no es una cuestión de diseño**.

### 2.3 Lo que dicen los textos

`p1_grid.py` busca en la web, el bundle, los documentos y el motor toda frase de tamaño o resolución: 631 apariciones
en `out/p1_grid_statements.csv` (fichero, línea, contexto). Las que ve el usuario están bien:
`app/src/flow/dataDialog.ts:24` ("about 111 km north-south on Earth and 30 km on the Moon (narrower east-west towards
the poles)"), `app/src/flow/app.ts:572`, `app/src/flow/detailPanel.ts:357` y `:406` (cada lado con su N-S × E-O real,
p. ej. "30 km north-south x 1.3 km east-west" para el gemelo de base_2), `detailPanel.ts:75`, `similarity.json`
("1-degree lunar cell"), `docs/DATA_CONTRACT.md:77`, `docs/DECISIONS.md:11`, `docs/REAL_DATA.md` §2 y §9 (que ya
describe la franja polar), `docs/AUDIO_TOP5.json:27`. Ningún texto dice que los valores sean de un sitio.

Fallos:

1. **Frase falsa en el bundle**: `tierra luna/engine/engine_config.json:166` (`not_used_by_engine_why`), exportada tres
   veces en `app/public/data/v2/missions.json` (`not_used_by_engine.why`): "the *_300m_* columns are 2-degree copies".
   En la tabla real son columnas de 1° con base de km (`slope_iso_deg`, `roughness_m`). Hoy la web no la muestra
   (`not_used_by_engine` no aparece en `app/src`). Corrección: "the *_300m_* variables are read from km-baseline
   columns (slope_iso_deg, roughness_m; true_baseline in variables.json)", y regenerar el bundle.
2. **Falta en lo que se dio al equipo y en los audios**: `docs/AUDIO_TOP5.json` `caveats[0]` dice "about 111 km
   north-south on Earth (about 30 km on the Moon)", pero no que los gemelos de Base lunar son franjas de 1,3-3,4 km de
   ancho ni que la celda terrestre abarca 14-224 veces más área. Corrección (generador
   `tierra luna/tools/make_audio_top5.py`): añadir "east-west the lunar twin of a Lunar base pair is only 1.3-3.4 km
   wide, so each Earth cell averages 90-220 times more ground than its twin (14 times for Solar panels, about 45 for
   Rover)". En la web la limitación está a la vista (2.3); no hace falta regrabar nada por esto.

---

## Punto 7. Nombres de lugar — **NOT YET**

### 7.1 Fuentes

- **Lugares de la Tierra**: `rg_cities1000.csv` del paquete `reverse_geocoder` 1.5.1 (licencia del paquete "lgpl";
  datos GeoNames cities1000, que el repositorio acredita como CC BY 4.0), 144.563 filas, sha256 `1de56dc3…5f9b65bf`; el
  paquete no dice la fecha del volcado de GeoNames (**no establecido**). Radio 6371,0 km.
- **Rasgos lunares**: `tierra luna/engine/data/iau_moon_nomenclature.csv` (9.087 filas, sha256 `4c650af9…6dce`),
  extraído de `MOON_nomenclature_center_pts.zip` del USGS/IAU Gazetteer of Planetary Nomenclature (descargado el
  2026-11-14 según `iau_source.json`; aprobación más reciente en el fichero 2026/07/15), sin los 7.064 "Satellite
  Feature" (`lunar_feature_exclude_types`). Comprobado contra el zip bruto: idénticos. Radio 1737,4 km.
- **Países**: Natural Earth 1:110m admin-0 (`ne_110m_admin_0_countries.geojson`, 177 polígonos). **Regiones de primer
  nivel**: el motor no tiene polígonos; es el `admin1` de GeoNames del lugar más cercano si está a ≤ 111,2 km y en el
  mismo país. **Regiones NASA**: `engine/data/artemis_iii_regions.geojson` (unión de cuadrículas USGS de 1 km, cota
  superior).

### 7.2 Los 15 pares de AUDIO_TOP5 (`out/p1_names_pairs.csv`)

Para los 15: el lugar del bundle y de AUDIO_TOP5 **es el más cercano por gran círculo** (por fuerza bruta sobre las
144.563 filas), la distancia coincide (≤ 1e-5 km), el rumbo de 8 puntos desde el lugar al centro de la celda coincide
con `direction_from_place` y con la grabación, el país coincide con el polígono NE que contiene el centro, y el rasgo
lunar y su distancia coinciden con mi búsqueda (`f_km`). Valores: Rover 1 Bayinbaolige 65,6 km NO; 2 Tamanrasset
79,5 N; 3 Ehen Hudag 78,4 NE; 4 Banqiao 27,8 NE; 5 Buga 41,0 SE; gemelo común Casatus 159,16 km. Paneles 1 Derby
128,7 NE (Huxley 75,8); 2 Derby 282,9 NE (Struve 58,2); 3 Maintirano 80,1 NE (Thebit 61,3); 4 Kununurra 279,7 NO
(Dziewulski 71,9); 5 Derby 218,2 NE (Rimae Pettit 82,5, tipo "Rima, rimae"). Base 1 Aheqi 62,28 N (Mons Malapert 25,1);
2 Mori 43,6 SE (Cartwright 15,47); 3 Burenhayrhan 45,5 N (Slater 19,4); 4 Tinghir 3,5 SE (Wapowski 18,3); 5 Ewirgol
53,3 S (Oberbeck 15,9). Margen más justo: Base 1, Aheqi a 62,28 km y Yamansu a 62,52 km (0,24 km); correcto, pero
frágil ante cualquier cambio de coordenadas.

Regiones NASA de los gemelos de Base lunar, con área real (proyección azimutal equivalente sobre 1737,4 km,
`out/p1_regions.csv`; la regla del motor de "la celda toca la región" da exactamente 280 celdas también con mi código):

| par | celda | región que nombra el audio | parte de la celda dentro | centro dentro | centro al borde |
|---|---|---|---|---|---|
| base_1 | M63528 (86,5 S 11,5 O) | Haworth | 0,24 de 56,1 km² (**0,43 %**) | no | 0,97 km |
| base_2 | M63841 (87,5 S 58,5 O) | de Gerlache Rim 2 | 3,13 de 40,1 km² (7,8 %) | no | 8,3 km |
| base_3 | M64018 (87,5 S 118,5 E) | Slater Plain | 13,2 de 40,1 km² (33 %) | no | 3,1 km |
| base_4 | M62517 (83,5 S 57,5 E) | Nobile Rim 2 | 46,4 de 104,1 km² (45 %) | no | 0,38 km |
| base_5 | M62523 (83,5 S 63,5 E) | Nobile Rim 2 | 0,33 de 104,1 km² (**0,32 %**) | no | 9,5 km |

Cada celda toca solo la región que se nombra (base_1 queda a 12,1 km de Malapert Massif). El nombre de la región es
correcto; la preposición no (7.3).

### 7.3 Lo que se dice frente a lo recalculado (`out/p1_names_mismatches.csv` y revisión a mano)

| pista | dicho | recalculado | juicio |
|---|---|---|---|
| base_1..5 | "in NASA's Haworth / de Gerlache Rim 2 / Slater Plain / Nobile Rim 2 candidate region" | el centro de las 5 celdas queda fuera; dentro 0,43 %, 7,8 %, 33 %, 45 %, 0,32 % del área, y de una huella que es cota superior | **falso para base_1 y base_5**, discutible para las demás |
| base_2 | "16 kilometers from Cartwright crater" | 15,47 km (AUDIO_TOP5 15,5: doble redondeo) | menor (0,53 km); no hace falta regrabar |
| solar_1, _2, _5 | "About 130 / 280 / 220 kilometers" | 128,7 / 282,9 / 218,2 (AUDIO_TOP5 "about 129 / 283 / 218") | redondeo a decenas con "about": correcto |
| solar_1, _2, _4, _5 | "in Western Australia" | el bundle no da región (lugar a más de 111,2 km); es el `admin1` de GeoNames de Derby y Kununurra | coherente con GeoNames; sin polígonos en el repositorio no se puede confirmar |
| rover_1..5 | "Like its lunar twin near Casatus crater" | a 159 km del centro de un cráter de 103 km (`m1_rover` dice bien "about 160 kilometers from Casatus") | "near" es laxo; no hace falta regrabar |
| rover_2, solar_3, base_4 | sin región | Tamanghasset / Melaky / Souss-Massa-Draa | omisión, no error |
| rover_4, base_1/2/5 | "Gansu", "Xinjiang" | "Gansu Sheng", "Xinjiang Uygur Zizhiqu" | forma corta: correcto |

Todo lo demás de las 19 transcripciones (lugar, distancia redondeada, dirección, país, nombre y tipo de rasgo) coincide.

### 7.4 Muestra de 60 puntos más (20 por misión, puestos > 5, semilla 20261115; `out/p1_names_sample.csv`)

Rasgo lunar más cercano y distancia: 60/60 correctos (y 64.800/64.800 en todas las celdas lunares). País: 60/60 del
mismo polígono (11 diferencias de nombre por la tabla ISO: "United States" frente a "United States of America",
"Congo (Rep.)" frente a "Republic of the Congo"; 1 celda antártica etiquetada AQ por la regla de latitud). La
distancia del bundle al lugar que nombra es correcta (≤ 1e-4 km). **Pero en 7 de los 60 el lugar nombrado no es el más
cercano**: Rover 888 Anadyr 421 km (el más cercano es Pevek, 280 km); Rover 1705 Anadyr 311 (Egvekinot 167); Rover
1237 Askiz 40,96 (otra fila Askiz a 40,62); Rover 5224 Abudula 74,6 (Tughyl 58,6, KZ); Rover 6854 Mill City 28,3
(Sweet Home 21,9); Rover 8736 Grytviken 2.919 (McMurdo Station 2.374); Paneles 5865 Lake Cargelligo 89,6 (Condobolin
88,9).

### 7.5 Fallos

1. **El lugar "más cercano" no es el más cercano en el 32 % de las celdas de tierra.** Causa:
   `tierra luna/engine/places.py` línea 192 llama a `rg.search(pts, mode=1)`; `reverse_geocoder` 1.5.1 construye su
   cKDTree sobre los pares (lat, lon) en grados (`reverse_geocoder/__init__.py`: `self.tree = KDTree(coordinates)`,
   con `coordinates` = `(row['lat'], row['lon'])`; la función `geodetic_in_ecef` existe pero no se usa), así que busca
   el más cercano en distancia euclídea en grados y no en distancia real. Comprobado llamando a la librería: devuelve
   Anadyr, Abudula, Mill City y Lake Cargelligo en las celdas de 7.4. Alcance (`p1_names_summary.json`): 8.284 de
   25.497 celdas de tierra; 5.009 están al sur de 60 S y 3.275 fuera de ahí; de las que la web enseña (≤ 300 km,
   `detailPanel.ts:15`) fuera de la Antártida, 1.754 de 16.098 (10,9 %), con una mediana de 6,3 km más lejos (P90
   50 km, máximo 165 km). En ranking: Rover 2.242 (916 mostradas fuera de la Antártida), Paneles 191, Base lunar 50;
   en los 100 primeros, 12, 1 y 10. **En los 15 pares de los audios: 0** (nada que regrabar por esto). La región
   (`admin1`) sale del mismo lugar, así que también puede estar mal en esas celdas. Lo que dicen los textos ("Labels
   are the nearest populated place to the cell centre", `datasets.json` credits → `manifest.json`; "Nearest populated
   place" en `detailPanel.ts:358`; docstring de `places.py`) es falso para esas celdas. Corrección sin cambiar ningún
   criterio: en `earth_places` sustituir `rg.search` por un `cKDTree` sobre `to_unit_vectors(lat, lon)` (función que
   `places.py` ya tiene) de las mismas filas de `rg_cities1000.csv`, conservando `name`, `admin1` y `cc`; regenerar
   el bundle y AUDIO_TOP5 y comprobar que los 15 pares no cambian (hoy coinciden las dos reglas en los 15).
2. **"in NASA's … candidate region" en base_1..base_5** (7.2, 7.3). Sin cambiar la zona (las 280 celdas que tocan
   las regiones siguen siendo la zona, decisión del equipo), el texto honesto es "in a cell that touches NASA's …
   candidate region" o "on the edge of NASA's … candidate region". Para **base_1 (0,43 %)** y **base_5 (0,32 %)** lo
   dicho no se sostiene: **recomiendo regrabar esas dos pistas** con esa frase; base_2, base_3 y base_4 (7,8-45 % y el
   centro fuera) quedan a juicio del jefe de equipo. Corregir también la frase de las que salga
   (`make_audio_top5.py` / textos de la web, si dicen "in").
3. Menor: base_2 "16 kilometers" frente a 15,47 km por doble redondeo (15,47 → 15,5 → 16): en el generador, redondear
   desde el valor sin redondear. No hace falta regrabar.

---

## Lo que no se ha podido establecer

- La fecha del volcado de GeoNames dentro de `reverse_geocoder` 1.5.1 (el paquete no la dice).
- Las regiones de primer nivel frente a polígonos (el motor no tiene polígonos admin-1): "Western Australia" y las
  demás solo son coherentes con el `admin1` de GeoNames del lugar.
- Si los gemelos de base_1 y base_5 tocan la región real o solo su huella de cota superior (el contorno exacto no
  está publicado, `artemis.py`).
- El efecto en los rankings de quitar o cambiar la puerta `elevation_m ≥ 1` o de excluir el hielo en Rover (no
  recalculado, porque sería cambiar un criterio del equipo).
- Las variables de LST, WorldClim y Diviner no se recalcularon desde los brutos en este punto (los ficheros mensuales
  de LST y las tablas GCP se borraron tras reducirlos); solo se comprobaron sus unidades y conversiones.
