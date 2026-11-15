# Auditoría, puntos 8 y 9: cifras de los audios y coherencia documentos-datos

Auditor independiente (no ha escrito nada del código revisado). 2026-11-15, rama `final-integration`, HEAD `a493514` (el motor está en `42d8bba`; el paquete `app/public/data/v2` es el de HEAD y no tiene cambios locales). No se ha tocado ningún audio, transcripción ni archivo del equipo.

**Cómo se repite** (cada orden es determinista; Python del entorno: `.../stars/venv/bin/python`):

```
PY=/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/bin/python
cd /home/user/stars-beside-you
$PY "tierra luna/audit/p4_audio_check.py"      # -> out/p4_audio_facts.json, out/p4_recompute_summary.json
$PY "tierra luna/audit/p4_regions.py"          # -> out/p4_regions.json
$PY "tierra luna/audit/p4_geodesy.py"          # -> out/p4_geodesy.json (necesita p4_audio_facts.json)
$PY "tierra luna/audit/p4_docs_coherence.py"   # -> out/p4_docs_hits.csv, out/p4_docs_summary.json
```

Código propio (`p4_common.py`): lector del paquete escrito a partir de `docs/DATA_CONTRACT.md` rev. 6 (índice de columnas del manifest), embudos, elevación relativa, insolación en el tope de la atmósfera (integral de Kepler propia, 36.500 pasos), percentiles de rango medio, regla del par (filtro, similitud, gemelo, empates), haversine y rumbo inicial. No importa el motor. Fuera del repositorio solo se ha abierto una página oficial (USGS, ver punto 8).

---

## Punto 8. Las cifras de los audios, una a una — veredicto: **NOT YET**

### 8.1 Base de la comprobación (recalculada, no tomada de AUDIO_TOP5.json)

| comprobación | resultado | evidencia |
|---|---|---|
| Embudo propio = embudo del paquete | Rover 10.337, Paneles 18.777, Base lunar 2.419; conjuntos idénticos | `out/p4_recompute_summary.json` `passing_sets_equal` |
| Gemelos propios = gemelos del paquete | 10.337/10.337, 18.777/18.777, 2.419/2.419 (incluidos los "sin gemelo") | `twins_equal_all` |
| Con par / sin par / gemelos distintos | 10.192/145/401; 6.360/12.417/1.704; 450/1.969/103 | `paired_own`, `unpaired_own`, `distinct_twins_own`; igual a `manifest.counts` |
| Similitud propia vs publicada | diferencia máxima 0,010 (redondeo a 2 decimales) en las tres misiones | `similarity_max_abs_diff` |
| Top 5 de cada misión | idéntico con el final propio y con el final publicado | `top5_own` = `top5_bundle` |
| Cada pista de par describe el par que hoy tiene ese puesto | sí, las 15 | `p4_audio_facts.json` `own_rank` = `rank` |
| SHA256 de los 19 MP3 | los 19 coinciden con `SHA256SUMS.txt` | `audio_sha256_ok` |
| Distancias/rumbos Tierra: esfera frente a WGS84 (pyproj) | ningún redondeo hablado ni rumbo de 8 puntos cambia con el modelo de Tierra | `out/p4_geodesy.json` |

Nota de ranking (para el punto F, no del audio): con el final sin redondear el puesto cambia en 4.767 pares del Rover (máx. 28 puestos), 2.808 de Paneles y 27 de Base lunar, porque el motor ordena por el final publicado a 2 decimales con empate por id; el top 5 no cambia.

### 8.2 Verificación pista a pista

Valores exactos del paquete / tablas reales (`p4_audio_facts.json`). "Pct" = percentil de rango medio.

**00_welcome — minor.** "slope and roughness decide everything": en el Rover pesan el 80 % de la similitud; la elevación relativa pesa el 20 % (`missions.json` rover `similarity.variables`) y el final es mitad similitud, mitad idoneidad. "sunlight is the key" (80 %) y "temperature and its daily swing matter most" (40 + 40 %): correctos. "lunar data from NASA missions": LOLA y Diviner (LRO), `docs/REAL_DATA.md` líneas 84-85. Teclas "Press one/two/three": no establecido (la guía de audio no está en `app/src`; segunda pasada).

**m1_rover — minor.** "we match places by slope and surface roughness": omite la elevación relativa (20 %). "near the south pole": zona lat ≤ −75° (5.400 celdas) ✓. "where NASA plans to look for water ice": respaldado por las fuentes de `MISSION_ZONES.md` (S15, VIPER). "All five analogs share the same lunar twin" ✓ (M59895 en los cinco). "gently sloping ground at 76.5 degrees south" ✓: centro −76,5°; pendiente 1,148°, pct 12,2 de la Luna y 1,8 de la zona. "about 160 kilometers from Casatus crater": 159,16 km ✓ (la satélite Casatus D está a 14,4 km, pero el motor solo nombra rasgos principales). Teclas: no establecido.

**m2_solar — minor.** "we match places by how much solar energy arrives ... at the top of the atmosphere" ✓ como variable clave (80 %), pero omite pendiente y rugosidad (10 + 10 %). "the low, flat plains near the equator": regla |lat| ≤ 30° y elevación ≤ −1.200 m; −1.200 m es el pct 38,9 de la elevación lunar, mediana de la zona −1.859 m; pendiente mediana de la zona 1,13° frente a 4,91° en toda la Luna ✓. "called the maria": es la etiqueta que eligió el equipo (`mission_zone_texts.json` D), no un dato. USGS define mare como "low albedo, relatively smooth plain" (https://planetarynames.wr.usgs.gov/DescriptorTerms, abierta 2026-11-15, sin fecha visible) y el repositorio no tiene ni albedo ni mapa de mares; 1.029 de las 6.686 celdas están en la cara oculta (`MISSION_ZONES.md` l. 70), y también dos de los cinco gemelos (M24761 a 101,5° E y M40406 a 93,5° O). "where the Sun climbs high" ✓: a |lat| ≤ 30° el Sol pasa de 60°.

**m3_base — RE-RECORD.** "the coldest, steadiest sites on Earth, against the coldest cells in NASA's nine candidate regions":
- *steadiest* va al revés del método: el embudo exige amplitud ≥ 15 K y la idoneidad premia más amplitud (bad 15, good 35, `mission_scoring.json` lunar_base.soft). La amplitud mediana de la población de la Tierra está en el pct 89,6 de toda la tierra firme. La palabra no aparece en ningún documento.
- *coldest sites on Earth*: los 2.419 sitios son algo más templados que la tierra firme típica (tmin mediana −6,6 °C frente a −19,3 °C, pct mediano 60,9). Los cinco números 1-5 están en los pct 42-65 de la tierra firme.
- *the coldest cells*: la población lunar son **todas** las 280 celdas de las nueve regiones, no las más frías; el gemelo de base_4 está en el pct 62,7 de la zona.
- Texto propuesto: "...so we compare how each place ranks within its own world: Earth sites with cold nights and strong daily swings, against all the cells of NASA's nine candidate regions near the lunar south pole."
- Lo demás es correcto. "Nowhere on Earth is as cold as the Moon": la tmin más fría de la tierra firme es 200,9 K y la celda más cálida de la zona 75,2 K; ninguna celda de la Tierra baja de ese valor (`out/p4_docs_summary.json` `thermal`). Las nueve regiones están en `artemis_iii_regions.geojson` (9 features).

**rover_1..rover_5 — minor (las cinco, por la misma frase; no hace falta regrabar).** "height above each world's average level": en la Tierra la media es la de las celdas de tierra firme (+695,9 m, 25.245 celdas, `ASSUMPTIONS.md` §0.12), no el nivel medio del planeta ni el del mar. La cifra es correcta con esa definición; la palabra "world's" es imprecisa. Todas las demás cifras son exactas:

| pista | lugar (exacto) | pendiente T / L (°) | rugosidad T / L (m) | Δ elev. rel. (m) | similitud |
|---|---|---|---|---|---|
| rover_1 | 65,6 km, 314° NO de Bayinbaolige, Inner Mongolia, CN ✓ "66 NW" | 1,038 / 1,148 ✓ "1.04/1.15" | 43,53 / 44,20 ✓ "about 44 in both" | 95,81 ✓ "96" | 99,57 ✓ |
| rover_2 | 79,5 km, 358° N de Tamanrasset, Argelia ✓ "80 N" | 1,215 / 1,148 ✓ "1.22" | 43,37 / 44,20 ✓ "43 / 44" | 71,41 ✓ "71" | 99,76 ✓ |
| rover_3 | 78,4 km, 65,5° NE de Ehen Hudag ✓ | 0,908 / 1,148 ✓ "0.91" | 38,75 / 44,20 ✓ "39 / 44" | 85,61 ✓ "86" | 98,77 ✓ |
| rover_4 | 27,8 km, 34,8° NE de Banqiao, Gansu ✓ "28 NE" | 1,131 / 1,148 ✓ ("almost the same": Δ 0,017°) | 48,91 / 44,20 ✓ "49 / 44" | 18,19 ✓ "only 18" | 99,50 ✓ "99.5" |
| rover_5 | 41,0 km, 113,8° SE de Buga, Govi-Altay, MN ✓ | 1,236 / 1,148 ✓ "1.24" | 41,33 / 44,20 ✓ "41 / 44" | 129,19 ✓ "129" | 99,12 ✓ |

"slopes gently, by about one degree": de 0,9° a 1,24° en grados absolutos ✓. En percentil, la Tierra está en los pct 63,7-69,9 de la tierra firme (27,6-40,5 de la población del Rover) y la Luna en el pct 12,2 de la Luna y el 1,8 de la zona. La palabra "gentle" se apoya en el valor absoluto, no en la regla de "mismo cuarto" de `AUDIO_TOP5.json` `how_to_read.percentile_words`.

**solar_1..solar_5.** "Above the atmosphere" = Tierra DERIVED (mi integral: 9,60046 frente a 9,6005 publicado), Luna = irradiancia en superficie de la tabla. El "% less" sigue la regla publicada `share_lost_of_displayed_tenths` (DATA_CONTRACT l. 16-21): se calcula con los décimos mostrados, así que concuerda con las cifras habladas. La pérdida sin redondear figura entre paréntesis.

| pista | veredicto | lugar | sol T / L tope | suelo, pérdida | similitud | observación |
|---|---|---|---|---|---|---|
| solar_1 | **exact** | 128,7 km, 46° NE de Derby (admin1 GeoNames Western Australia) ✓ "130"; Huxley (cráter) 75,8 ✓ "76" | 9,6005 / 9,604 ✓ "9.6" | 6,177 ✓ "6.2"; 35 por la regla (35,66 %) | 99,9921 ✓ "99.99" | "slope and roughness almost the same": Δ 0,071°, 0,17 m ✓ |
| solar_2 | **minor** | 282,9 km NE de Derby ✓ "280"; Struve 58,2 ✓ "58" | 9,644 / **9,672** | 6,110 ✓; 36 (36,64 %) | 99,8821 ✓ | "both receive about 9.6": la Luna da 9,7 con un decimal (la web mostrará 9,7) |
| solar_3 | **minor** | 80,1 km NE de Maintirano, Madagascar ✓; Thebit 61,3 ✓ | **9,554** / 9,534 | 5,967 ✓ "6"; 38 (37,55 %) | 99,9481 ✓ | "both receive about 9.5": la Tierra da 9,6 con un decimal, y el 38 % sale de 9,6 (con 9,5 serían 37) |
| solar_4 | **exact** | 279,7 km, 300° NO de Kununurra ✓; Dziewulski 71,9 ✓ "72" | 9,685 / 9,672 ✓ "9.7" | 6,071 ✓; 37 (37,32 %) | 99,9765 ✓ | — |
| solar_5 | **minor** | 218,2 km, 66° NE de Derby ✓ "220"; Rimae Pettit 82,52 ✓ "83" | 9,6005 / 9,604 ✓ | 6,140 ✓; 36 (36,04 %) | **99,9968** (publicado 100,00) | "Similarity: 100 percent" es un redondeo correcto a 2 decimales, pero da a entender un par idéntico (Δ 0,031°, 0,33 m, 0,0035 kWh); `AUDIO_TOP5.json` dice "100 (rounded)". "a system of lunar fissures": el tipo IAU es "Rima, rimae", que USGS define como "Fissure" (página citada arriba) ✓ |

**base_1..base_5.** Recordatorio para todo el bloque: la tmin de la Tierra es la media de las mínimas diarias del aire en el mes más frío (WorldClim) y la de la Luna es la temperatura mínima de superficie (Diviner) (`variables.json` tmin_c). Las pistas no lo dicen, pero tampoco afirman lo contrario.

Nuevo dato sobre "in NASA's X candidate region" (`out/p4_regions.json`): **ningún centro de los cinco gemelos cae dentro de su región**. La zona son las celdas que *tocan* una región (decisión del equipo). Fracción de cada celda dentro de la región nombrada: base_1 0,43 % (centro a 0,97 km del borde), base_2 7,8 %, base_3 33 %, base_4 45 %, base_5 0,32 %. En toda la zona, 113 de las 280 celdas tienen el centro dentro de una región y 34 tienen menos del 5 % de su superficie dentro.

| pista | veredicto | lugar T | rasgo L, región | Δ tmin (K) | pct tmin T / L | pct amplitud T / L | similitud | qué falla |
|---|---|---|---|---|---|---|---|---|
| base_1 | **minor** | 62,3 km, 4° N de Aheqi, Xinjiang ✓ | Mons Malapert 25,1 ✓; Haworth (0,43 % de la celda) | 207,38 ✓ "207" | 8,37 / 8,04 ✓ "near the 8th" | 6,72 / 10,18 ✓ "close" (Δ 3,5 de tolerancia 10) | 97,31 ✓ | "in NASA's Haworth candidate region": la celda solo toca el borde; mejor "at the edge of". "slopes of about 7 degrees": 6,652 / 7,179 ✓ |
| base_2 | **minor** | 43,6 km, 146° SE de Mori ✓ | **Cartwright 15,47 km**; de Gerlache Rim 2 (7,8 %) | 208,18 ✓ | 21,48 / 18,75 ✓ "21st and 19th" | 33,09 / 32,50 ✓ "almost the same" | 96,61 ✓ | "16 kilometers": el redondeo correcto es **15** (doble redondeo: 15,47 → 15,5 → 16) |
| base_3 | **minor** | **45,48 km** (WGS84 45,46), 355° N de Burenhayrhan, Hovd ✓ | Slater 19,4 ✓; Slater Plain (33 %) | 206,65 ✓ "207" | 5,85 / 6,61 ✓ "6th and 7th" | 11,64 / 10,54 ✓ | 96,86 ✓ | "46 kilometers": el redondeo correcto es **45** (45,48 → 45,5 → 46) |
| base_4 | **exact** | 3,51 km, 118° SE de Tinghir, Marruecos ✓ "4" | Wapowski 18,3 ✓; Nobile Rim 2 (45 %, centro a 0,38 km) | 208,60 ✓ "209" | 62,73 / 62,68 ✓ "63rd" | 41,86 / 43,39 ✓ | 99,36 ✓ | — (contradice la frase "coldest" de m3_base, ver arriba) |
| base_5 | **minor** | 53,3 km, 194° S de Ewirgol ✓ | Oberbeck 15,9 ✓ "16"; Nobile Rim 2 (0,32 %) | 207,80 ✓ "208" | 23,17 / 22,32 ✓ "23rd and 22nd" | 34,93 / 37,68 ✓ | 95,03 ✓ | "in NASA's Nobile Rim 2 candidate region": la celda solo roza la región |

Si el líder quiere el criterio geográfico estricto, base_1 y base_5 pasan a regrabar con "at the edge of NASA's ... candidate region". Por la definición de zona del modelo, la frase es cierta. Lo dejo como decisión suya.

### 8.3 Fallos del punto 8

1. **m3_base dice algo falso** ("coldest, steadiest sites on Earth, against the coldest cells"). Hay que regrabarla con el texto propuesto. El método no cambia.
2. **El generador de `docs/AUDIO_TOP5.json` redondea dos veces.** En `tierra luna/tools/make_audio_top5.py` las líneas 332, 724 y 726 aplican `int(round(x))` a distancias ya redondeadas a 1 decimal (`place.nearest_place_km`, `twin.feature_km`), y además con el redondeo al par de Python. Salen 16 (15,47), 46 (45,48) y, en su texto propio, 82 para Rimae Pettit (82,52). Arreglo: redondear el float32 sin redondear del paquete (`earth_place_detail.bin` `nearest_place_km`, `moon_base.bin` `feature_km`) con redondeo hacia arriba en el medio (`Decimal ... ROUND_HALF_UP`). No es un cambio de diseño. Las pistas base_2 y base_3 heredaron 16 y 46.
3. Imprecisiones de redacción (minor, sin regrabación obligatoria): welcome, m1_rover y m2_solar omiten las variables secundarias; "world's average level" (rover_1-5); "about 9.6/9.5" (solar_2, solar_3); "100 percent" (solar_5); "in ... region" (base_1, base_5).

---

## Punto 9. Coherencia entre documentos y datos (lado documental) — veredicto: **NOT YET**

Verdad de referencia, leída con mi lector (`out/p4_docs_summary.json` `truth`): misiones `rover`, `solar`, `lunar_base` (títulos del paquete "Rover mobility and trafficability", "Solar array placement", "Lunar base (thermal endurance)"). Reglas `real_value_tolerance` ×2 y `percentile_and_real_tolerance`. Rover pendiente 0,4/2°, rugosidad 0,4/30 m, elev. rel. 0,2/500 m (cota 1.000), zona lat ≤ −75 (5.400). Paneles sol en el tope 0,8/0,6, pendiente 0,1/2 (4), rugosidad 0,1/30 (60), zona |lat| ≤ 30 y ≤ −1.200 m (6.686). Base lunar tmin y amplitud 0,4/10 puntos de percentil, pendiente 0,1/2 (4°), rugosidad 0,1/30 (60 m), 280 celdas. Final 0,5/0,5. Celda de 1° (111,2 km N-S en la Tierra). Niveles MEASURED/DERIVED/MODELLED/UNDOCUMENTED/NO_DATA. Recuentos 10.337/10.192/145/401; 18.777/6.360/12.417/1.704; 2.419/450/1.969/103. Número 1: E17566–M59895 (Bayinbaolige/Casatus), E38464–M24296 (Derby/Huxley), E17538–M63528 (Aheqi/Mons Malapert). Artemis IV es el primer alunizaje tripulado (según las páginas de la NASA citadas en `MISSION_ZONES.md`; eso lo verifica el punto C, no este).

### 9.1 Tabla hecho × documento (valor que dice; archivo:línea). ✓ = coincide con la verdad

| hecho | DECISIONS.md | ASSUMPTIONS.md | DATA_CONTRACT.md | ANALOG_PRINCIPLE.md | LUNAR_BASE_PROPOSAL.md | MISSION_ZONES.md / mission_zone_texts.json | AUDIO_TOP5.json | transcripts.json | paquete (missions/similarity/variables/explain/mission_zones) | media (README/VTT) |
|---|---|---|---|---|---|---|---|---|---|---|
| nombres de las misiones | Rover / Paneles solares / Base lunar (l. 5) ✓ | Rover / Solar panels / Lunar base ✓ | rover/solar/lunar_base ✓ | ✓ | ✓ | Rover / Solar panels / Lunar base (l. 8-11) ✓ | "Rover mobility and trafficability"... (títulos del paquete) ✓ | "Rover" / "Solar Panels" / "Lunar Base" (variante de mayúsculas) | títulos largos `missions.json` `title` | "Rover/Solar/Lunar base mission video" ✓ |
| regla y variables Rover | ✓ l. 44-46 (mañana); **z-score sin marcar** en l. 9-15 (glosario), 84 y 94-109 | ✓ §0.12 l. 135-150; §0.4 fila "zone_twin (active since...)" l. 56 solo marcada por la nota general l. 3 | ✓ rev. 5-6; zone_twin solo para builds no publicados (l. 10, 323, 419, 546: marcado) | ✓ l. 337-360 (cabecera l. 5-7 marca A-E como registro) | — | ✓ l. 10 | ✓ l. 25-50 | parcial: "slope and roughness" (falta el 20 %) | ✓ `missions.json` similarity | — |
| regla y variables Paneles | ✓ l. 48 (mañana); **"se quedan en el polo sur"** l. 85 sin marca (sí marcado en l. 800-803) | ✓ §0.12; §0.10 punto 5 l. 124 "Solar stays on the south pole" sin marca en la línea (cubierto por l. 3 y por la lista "Superseded" de §0.12) | ✓ | ✓ | — | ✓ | ✓ | parcial: solo la variable clave | ✓ | **solar.en/es.vtt y README: par del método anterior** (E44120 Western Cape frente a M59479, 75,5 S, zona antigua del polo sur; hoy E44120 tiene el gemelo M21923, puesto 5.786) |
| regla y variables Base lunar | ✓ l. 25 (08:55) | ✓ §0.13 l. 166-192 | ✓ rev. 6 l. 27-38 | ✓ l. 408-420 | ✓ l. 28, 385-400; **"Artemis III" en la frase de la web l. 34/36** (corregido solo en l. 393) | ✓ | ✓ | m3_base: método ✓, población **mal descrita** (ver 8) | ✓ `similarity_meaning_lunar_base` | lunar-base README ✓ (M63528); **VTT del vídeo sustituido** (E19345/M62859, ninguno de los dos es hoy un par) |
| zonas | ✓ | ✓ (5.400 / 6.686 / 280) | ✓ l. 336-349 | ✓ | ✓ 280 | ✓ A 280, B 5.120, C 5.400, D 6.686, E 25.971, F 21.343 | ✓ | ✓ ("near the south pole", "maria", "nine candidate regions") | ✓ `mission_zones.json` | solar: zona antigua |
| recuentos (pasan/par/sin par/gemelos) | ✓ 10.337/10.192 l. 46; 6.360/12.417 l. 48; 450/103 l. 25 (marcado "esperadas", verificadas en ANALOG) | ✓ l. 148, 184 | ✓ l. 38, 127 | ✓ l. 346-348, 416 (401, 1.704, 103 ✓) | ✓ l. 28 | ✓ | ✓ | "five analogs", "nine regions" ✓ | ✓ `ranked_count`, `passing_without_similarity`, manifest | — |
| par número 1 | ✓ l. 25, 46 | ✓ l. 133 ("proposed", coincide), 184 | ✓ | ✓ l. 17-18, 418 | ✓ l. 21 | — | ✓ | ✓ rover_1, solar_1, base_1 | ✓ `explain.json` [0] | lunar-base README l. 8 ✓ |
| tamaño de celda | ✓ 1° (l. 11) | ✓ 1° en §0 y §10; "2-degree" en l. 209/341/356/391 (secciones 1-9, marcadas como legacy en l. 7 y 16) | ✓ | ✓ | ✓ | ✓ | ✓ caveat 1° | — | **`missions.json` `not_used_by_engine.why`: "*_300m_* columns are 2-degree copies"** (falso en real_1deg; `variables.json` dice que se leen de la pendiente isotrópica km) | — |
| niveles de dato | — | §1 (tabla legacy, "MEASURED: Moon elevation_m only") marcado; §10.2 ✓ | l. 244: cuatro niveles (falta UNDOCUMENTED) | — | — | — | MEASURED/DERIVED/MODELLED ✓ | — | 5 niveles; UNDOCUMENTED definido pero **ninguna variable lo usa** (18 DERIVED, 10 MODELLED, 4 MEASURED, 2 NO_DATA) | solar/lunar-base README: "measured/derived/modelled" ✓ |
| Artemis del primer alunizaje tripulado | Artemis IV l. 30 ✓ | Artemis IV l. 58 ✓ | Artemis IV l. 23 ✓ | — | **Artemis III** en l. 34/36 (sin marcar) | Artemis IV ✓ (Artemis III solo en citas de fuentes) | sin número ✓ | sin número ✓ | Artemis IV (`mission_zones.json` outside.lunar_base.B/D/F) ✓ | sin número ✓ |
| qué significa la similitud | **l. 14: definición z-score `100·exp(−0,45 d)`** en el glosario, sin marcar; l. 45 ✓ | §0.3 z-score (marcado l. 3); §0.12/0.13 ✓ | ✓ l. 479 (z-score marcado "none shipped") | ✓ l. 127 | ✓ l. 56 | — | ✓ `how_to_read.similarity` | — | ✓ `similarity_meaning_real_values` / `_lunar_base`; `similarity_meaning` antigua marcada "no longer applies" | — |
| pérdida atmosférica del número 1 de Paneles | **"36 % menos" l. 50** (era la regla anterior) | 35,7 % sin redondear l. 158 ✓ | 35 por la regla nueva l. 19 ✓ | — | — | — | 35 ✓ | 35 ✓ | regla `share_lost_of_displayed_tenths` ✓ | — |

Hay 1.976 coincidencias de patrón con archivo y línea en `out/p4_docs_hits.csv` (columna `marked` = hay una marca de sustitución en la línea o en su encabezado). Las 85 candidatas a restos sin marcar están en `p4_docs_summary.json` `unmarked_leftovers`. Las he revisado a mano: la mayoría están marcadas por un encabezado o una nota general; los fallos reales son los de 9.2.

### 9.2 Contradicciones y restos sin marcar (corregibles sin cambiar el diseño, salvo 9.2.7)

1. **DECISIONS.md, glosario (l. 9-15)**: define z y "Similitud = 100 × exp(−0,45 × d)" como vocabulario del documento, sin decir que es la regla anterior. Arreglo: añadir delante "(vocabulario de la regla de anoche, sustituida; método vigente en 'Decisiones tomadas' de la mañana y de las 08:55)".
2. **DECISIONS.md, "Decisiones tomadas (15-11-2026)" (l. 80-90) y "Decisión 1 / 1. Qué pasa ahora" (l. 92-141)**: zone_twin, z y "Paneles solares en el polo sur" sin marca (la Decisión 5 sí la tiene, l. 651). Arreglo: una línea "**Sustituido (15-11-2026, mañana y 08:55)**" bajo cada encabezado.
3. **DECISIONS.md l. 50**: "6,2 de 9,6, un 36 % menos en el número 1". Con la regla vigente es 35 % (DATA_CONTRACT l. 19, solar_1). Arreglo: "35 %" o una nota sobre el cambio de regla.
4. **LUNAR_BASE_PROPOSAL.md l. 34/36**: la "Frase para la web" dice "NASA's nine Artemis III candidate regions". Lo publicado dice "NASA's nine candidate landing regions near the lunar south pole" (l. 393). Arreglo: una nota en l. 32 que remita a l. 393.
5. **Paquete `missions.json` `not_used_by_engine.why`** (origen `tierra luna/engine/engine_config.json` l. 166): "the *_300m_* columns are 2-degree copies" está heredado de la tabla legacy y contradice `variables.json`. Arreglo: un cambio de texto en engine_config y reexportar.
6. **ASSUMPTIONS.md §0.4 l. 56** dice "zone_twin (active since the team decision of 2026-11-15)" y §0.10 l. 123-124 dice "Twin rule: zone_twin" y "Solar stays on the south pole", sin marca en la línea. Arreglo: añadir "(superseded, §0.12/§0.13)" en la fila y en los puntos 1 y 5.
7. **Vídeo Solar (`app/public/media/solar/solar.mp4`, `.en/.es.vtt`, `README.md`)**: muestra el par y la zona del método anterior (polo sur, E44120/M59479, paneles verticales, "tests there would not reproduce the low lunar Sun"), sin marca. No describe ningún par de hoy. Opciones para el líder: (a) retirarlo de la web; (b) mantenerlo con un rótulo "earlier method, not today's pairs"; (c) volver a renderizarlo sobre E38464/M24296. Ninguna cambia un criterio del modelo; (c) cuesta un render.
8. **`DATA_CONTRACT.md` l. 244** enumera cuatro niveles y `variables.json` cinco (UNDOCUMENTED, sin uso en real_1deg). Arreglo: alinear el texto, o decir que UNDOCUMENTED solo aparece en legacy_2deg.
9. Menores: el vídeo del Rover (simulación sin lugar declarado) muestra "Sun elevation 21.1°", y en la zona Rover el máximo de la tabla es 16,04° (`sun_elev_max_deg`, lat ≤ −75), así que no corresponde a la zona de la misión. Conviene decirlo en el README. `engine_config.json` `similarity_scale` (pooled_percentile_range) no dice que ninguna regla publicada lo usa.

### 9.3 Para la segunda pasada (web y vídeo final de Base lunar)

- Teclas de la guía de audio: "Press one/two/three", "Press a number from one to five", "Escape to go back". No hay guía de audio en `app/src` ni en el `dist` actual.
- La web debe mostrar los títulos de misión y que coincidan con el audio ("Solar Panels" frente a "Solar array placement").
- Lo que la web pinte por par: decimales de la similitud (¿100,00 en solar_5?), sol en el tope con un decimal (9,7 en solar_2 frente a "about 9.6" del audio), pérdida con la regla `share_lost_of_displayed_tenths`, distancias a lugares y rasgos (redondeo desde el float32, no desde 1 decimal), y "in/at the edge of" las regiones de la NASA.
- La frase `lunar_base_pair_sentence`, sin "Artemis III", y el aviso de aire frente a superficie.
- Solo la primera frase de `twin_sharing_note`; ninguna `similarity_meaning` z-score.
- Vídeo final de Base lunar: VTT y póster del par M63528/E17538 (los VTT actuales son del vídeo sustituido E19345/M62859); que la región se describa como en el README ("touches the edge of the Haworth region"); Artemis IV o sin número.
- El vídeo Solar, según la decisión de 9.2.7.
- Recuentos visibles en la web: 10.192/145, 6.360/12.417, 450/1.969, y los números 1 de 9.1.

### Lo que no se ha podido establecer

- Las teclas de la guía de audio (la interfaz no existe todavía).
- Si las celdas de la "zona D" son mares desde el punto de vista geológico (el repositorio no tiene albedo ni mapa de unidades).
- La región de primer nivel de las celdas australianas (el paquete da `region` nulo). El "Western Australia" de las pistas Solar se refiere al lugar nombrado (admin1 de GeoNames) y es correcto.
