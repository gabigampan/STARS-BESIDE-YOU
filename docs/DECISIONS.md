# Cinco decisiones sobre los pares Tierra-Luna

Documento interno del equipo Stars Beside You (NASA Space Apps Challenge 2026). Escrito el 15 de noviembre de 2026 en la rama `final-integration`. Entrega: hoy, 23:59 CET.

**La pregunta de fondo:** ¿podemos defender ante el jurado los pares que enseña el producto (un punto de la Tierra y su gemelo lunar) para las tres misiones: Rover, Paneles solares y Base lunar?

**De dónde salen los números.** Todo se ha calculado hoy, sin tocar el repositorio, con los scripts de `scratchpad/stars/decisions/` (`ctx.py`, `d1.py` a `d5.py`, `d5ex.py`, `gen_tables.py`; resultados en `decisions/out/d1.json` a `d5.json`). Esos scripts reutilizan el código de la propuesta verificada (`proposal2/scripts_v3/analysis_v3.py`): la regla A1 recalculada hoy reproduce la de la propuesta celda a celda (mismos 31.533 gemelos, diferencia de similitud 0). Lo que viene de la propuesta lleva la cita "propuesta, §x" (`docs/SIMILARITY_PROPOSAL.md`). Datos: tablas reales de 1 grado (`tierra luna/output_real/earth_real_1deg.csv` y `moon_real_1deg.csv`). Las horas de trabajo son estimaciones, no medidas.

**Vocabulario mínimo.**

- **Celda**: un cuadrado de 1 grado × 1 grado. En la Tierra mide unos 111 km de norte a sur; en la Luna, unos 30 km.
- **Idoneidad** (0-100): lo bien que una celda de la Tierra cumple los criterios de la misión (`mission_scoring.json`). Solo la reciben las celdas que pasan los filtros duros.
> **Marca de la corrección de la auditoría estadística (15-11-2026, `docs/stats_audit/correcciones_1.md`):** las tres definiciones siguientes marcadas "SUSTITUIDO" (z, Similitud, Gemelo) son el vocabulario de la regla de la noche del 14 al 15 (z-score, `zone_twin`), que ya no usa ninguna misión. Se conservan como historia para leer las decisiones 1 a 5. La regla vigente está justo debajo, en "Similitud (regla vigente)" y "Gemelo (regla vigente)".

- **[SUSTITUIDO el 15-11-2026 por "Decisiones tomadas (15-11-2026, mañana)" (Rover, Paneles solares) y "Decisiones tomadas (15-11-2026, 08:55 CET)" (Base lunar)]** **z (puntuación típica robusta)**: dónde está un valor dentro de su propio cuerpo. `z = (valor − mediana del cuerpo) / escala`, con escala = rango intercuartílico / 1,349, recortado a ±4. z = 0 es "justo en la mediana"; z = +1 es "una desviación típica por encima". La Tierra y la Luna se normalizan **cada una por separado**.
- **[SUSTITUIDO el 15-11-2026 por las mismas dos secciones]** **Similitud** (0-100, regla anterior): `100 × exp(−0,45 × d)`, donde `d = √(Σ peso × (z Tierra − z Luna)²)`. 100 = misma posición relativa en las cuatro variables.
- **[SUSTITUIDO el 15-11-2026 por las mismas dos secciones]** **Gemelo** (regla anterior): la celda lunar, dentro de la zona de la misión, con la similitud más alta.
- **Similitud (regla vigente, las tres misiones)**: para cada variable, puntuación `s = exp(−0,5 × (d / τ)²)`, con `d` = diferencia absoluta entre el punto de la Tierra y la celda lunar y `τ` = su tolerancia; similitud = 100 × media ponderada de las `s` (las variables clave pesan el 80 %; en Rover, desde las 11:23 CET, el 100 %: pendiente y rugosidad, 50 % cada una). En Rover y Paneles solares `d` se toma en valores reales; en Base lunar las dos claves (temperatura mínima y amplitud térmica diaria) se comparan como **percentil dentro de su población** (Tierra: los 2.419 candidatos del embudo; Luna: las 280 celdas de la zona) y la pendiente y la rugosidad en valores reales.
- **Gemelo (regla vigente)**: la celda lunar de la zona de la misión que **pasa el filtro del par** (cada clave a menos de `τ`, cada secundaria a menos de `2τ`) con la similitud más alta; empate, el id más bajo. Si ninguna celda pasa el filtro, el punto no tiene gemelo (conserva su idoneidad, sin similitud ni final).
- **Final** = 0,5 × similitud + 0,5 × idoneidad. El ranking ordena por el final.
- **Spearman**: correlación de rangos, de −1 (orden inverso) a +1 (mismo orden).

---

## Decisiones de las 11:28 y 11:36 (15-11-2026)

Órdenes del líder del equipo (11:23, 11:28 y 11:36 CET, a través de su delegado; opciones E2 y R y escala de Rover aprobadas a las 11:51 CET). Motor 3.4.0, **revisión 8 del contrato**. Especificación: `docs/stats_audit/research_2_solar_idoneidad.md` (E2), `research_3_base_lunar.md` (R), `research_5_rover_escala.md` ("Para implementar"), `research_1_rover_terreno.md`, `research_4_validacion_externa.md`. Todas las cifras salen del paquete reconstruido (dos veces, idéntico byte a byte) o de `engine/limits.py` en cada construcción. **Esta sección sustituye, para los criterios listados en la tabla de desviaciones, la regla de ayer "los filtros del repositorio exactamente como están escritos"**: `tierra luna/mission_scoring.json` no se edita; cada desviación es una entrada de `engine_config.json` `criteria_sets` con el valor del equipo citado, el nuestro, la razón y la fuente (el motor comprueba al construir que el valor citado sigue siendo el del fichero del equipo).

### 1. Conjuntos de criterios por misión (orden de las 11:28)
- Encontrado: había que poder volver al estado auditado por la mañana (commit 42d8bba) misión a misión sin deshacer código.
- Aplicado: `engine_config.json` `criteria_sets`: por misión `audited_morning` (regla, pesos, puertas, filtro y elección de los cinco de 42d8bba; en Rover la elevación relativa al 20 % con su cota de 500 m y los rangos 1 a 5) y `corrected`; interruptor `selected` (publicado: `corrected` en las tres). Código: `engine/criteria.py`. El paquete lo declara en `missions.json` `missions[].criteria_set`.
- Comprobado: `tests/test_decisions_1128.py::test_audited_morning_reproduces_42d8bba_bundle` construye las tres misiones con `audited_morning` y obtiene columnas `suitability`, `similarity`, `final`, `rank`, `twin` y las del fichero de parejas idénticas byte a byte a las del paquete de 42d8bba, y los cinco = rangos 1 a 5.

### 2. Idoneidad de Paneles solares (opción E2, aprobada 11:51)
- Fuera de la suma ponderada: `sun_elev_max_deg` (0,15) y `sun_low_frac_0_5deg` (0,15), geometría de la latitud; `irradiance_kwh_m2_day` (0,35), MODELADA (WorldClim) y repite lo que ya compara la similitud. Sus puertas siguen (incluida irradiancia en suelo ≥ 2,5). La irradiancia en suelo, la luz sobre la atmósfera y la parte perdida siguen en la frase de cada pareja.
- Dentro: `clear_frac_isccp`, peso 0,35 (los pesos suman 0,70 y la idoneidad se divide por esa suma: en la práctica es la mitad de la idoneidad, 0,35 de 0,70), malo 0,308 y bueno 0,671 = percentiles 10 y 90 entre los 18.777 puntos que pasan el embudo (recalculados: 0,3079 y 0,6711; 3 puntos sin valor, con su peso renormalizado). Fuente: ISCCP-H HGM v01r00, NOAA NCEI, 2012-2016, DERIVADO; Rossow y Schiffer 1999. Leída de `real_data/supplement/earth_cloud_isccp_1deg.csv` por el nuevo mecanismo de columnas suplementarias (`datasets.json` `supplements`, `engine/dataset.py` `load_supplements`).
- Antes / después: pasan 18.777 / 18.777; emparejados 6.360 / 6.360; gemelos distintos 1.704 / 1.704; Spearman idoneidad-|latitud| entre los que pasan +0,337 (investigación: ~+0,34); 7 de los 50 primeros coinciden con la mañana (investigación: 7). Cinco antes (11:23): E38464, E38744, E37746, E37750, E29749; después: E40184, E29749, E23648, E29746, E28670.

### 3. Idoneidad de Base lunar (opción R, aprobada 11:51)
- `thermal_inertia_class` 0,15 → 0 (sigue requerida y sigue excluyendo "agua"); `rock_or_bare_frac` 0,10 → 0,25 (malo 0,1 y bueno 0,7 sin cambio); `permafrost_class` 0,05 → 0. La puerta "amplitud térmica diaria ≥ 15 K" se mantiene: sin ella, celdas con ~1 K (p. ej. isla de Ellesmere) se parecerían a la Luna con similitud ~99 y la variable clave quedaría vacía. Estaciones polares (recalculado de la tabla): Haughton 2,5 K, Svalbard 1,2 K, Kangerlussuaq 6,6 K; McMurdo y Concordia sin temperatura de superficie. Son análogos de frío y aislamiento, no de ciclado térmico.
- Antes / después: pasan 2.419 / 2.419; emparejados 450 / 450; gemelos 103 / 103; 38 de los 50 primeros coinciden con la mañana (investigación: 38); cinco antes de la separación: E21054, E21412, E17538, E20695, E21833 (= investigación). Cinco publicados (con la regla del punto 5): E21054, E17538, E21833, E18627, E19672 (antes: E17538, E16830, E15751, E21054, E17187).

### 4. Rover
- (i) Sin variable nueva: ninguna se mide en los dos cuerpos, se define igual, tiene sentido para la movilidad y es independiente (la abundancia de rocas de Diviner tiene valor en 0 de las 5.400 celdas de la zona; no hay equivalente en la Tierra). Texto `rover_no_new_variable`.
- (ii) Escala: aplicado exactamente "Para implementar" de `research_5_rover_escala.md`: σ pendiente 0,265093°, σ rugosidad 17,401661 m (ETOPO 2022 RMSE 7,17 m, MacFerrin et al. 2025; LOLA ~10 m, Smith et al. 2010); `s = exp(−0,5·max(0, |d|/σ − 1)²)`; filtro sin cambio (2° y 30 m); gemelo: máxima puntuación, empate por menor Σ(d/σ)², luego menor id. Empatados con final 100,00: **254** (= investigación), 241 tras quitar hielo y agua. Validación (percentil de rango, menor = mejor; = columna C-S1 de la investigación): Ramon 3,6; Qaidam 4,1; Haughton 4,2; Yungay 8,1; Bardenas 68,2; Tabernas 71,5.
- Cinco: regla publicada `spread_within_top_tie` (dispersión geográfica entre los empatados). Con el salto de agua activado (publicado): E4037, E50510, E44239, E26510, E26087. **Diferencia con la investigación**: la investigación solo salta el hielo y da E3872, E50509, E44239, E26087, E26151 (reproducido exactamente con `skips.water.enabled = false`); E3872 tiene 33,8 % de tierra y el salto de agua (pendiente de confirmar por el líder) lo excluye. Regla alternativa (`rank_with_skips`): E4037, E4742, E4751, E4962, E5125.
- (iii) En la idoneidad, pendiente (45 %) y rugosidad (30 %) son casi un criterio (Spearman calculado en cada construcción, texto `rover_suitability_one_criterion`); pesos sin cambio.

### 5. Regla de los cinco (las tres misiones)
`top5_selection.missions.<m>`: `rank_with_skips` (bajando por la clasificación completa: salto `ice` = `snow_ice_frac` ≥ 0,5; salto `water` = `mask_fraction` < 0,5, interruptor propio; separación de 2° de arco, 222,4 km) para Paneles solares y Base lunar; `spread_within_top_tie` (con `rank_with_skips` como alternativa publicada en `top5.alternative`) para Rover. La clasificación completa no cambia. Ninguno de los análogos conocidos de Rover (Haughton: hielo 0, tierra 0,76; Qaidam 0 / 0,98; Ramon 0 / 1,00; Yungay 0 / 1,00) sería saltado por el hielo o el agua; la separación solo los saltaría si estuvieran a menos de 222,4 km de uno ya elegido.

### 6. Números sin efecto y confianza
- Confianza por pareja eliminada del paquete (era uniforme: Rover y Paneles "media", Base lunar "baja"): columnas `confidence` y `confidence_score` presentes pero todas ausentes (lectura compatible), campos de `explain.json` y `missions.json` `confidence_counts` / `distributions.confidence_score` eliminados. En su lugar `top5_stability_<m>` (`show`: tarjeta de misión y "Datos y límites"), con marcadores y tabla en `engine_config.json` `top5_stability`; hasta que la re-auditoría rellene las cifras se publica "Stability figures pending the independent re-audit." (probado en los dos estados).
- Constantes con dos valores: radio 6.371,0 km (motor) frente a 6.371,0088 km (constructor de la tabla): arco de 2° 222,390 km en ambos (0,3 m); oblicuidad 23,44° (motor) frente a 23,4393° (constructor): luz sobre la atmósfera cambia como máximo 0,00012 kWh/m²/día (mueve el 4.º decimal publicado en 68 de 180 latitudes, nunca el 3.º). No se ha cambiado ningún número que entre en un resultado. Texto `constants_two_values`.
- Números del fichero del equipo sin efecto: texto `numbers_without_effect` (ya existente, recalculado).
- **No hecho**: mover a `legacy_rules` los bloques muertos de `engine_config.json` / `datasets.json` (entrada Solar obsoleta de `similarity_zones`, tolerancias de referencia no usadas, escala combinada): siguen en su sitio.

### 7. Tabla de desviaciones respecto de mission_scoring.json

| Misión | Criterio | Equipo | Nuestro | Razón | Fuente |
|---|---|---|---|---|---|
| Paneles solares | irradiance_kwh_m2_day | peso 0,35 (2,5–6,0) | 0 | MODELADA, duplica la similitud | research_2 E2, 11:51 |
| Paneles solares | sun_elev_max_deg | peso 0,15 (10–70) | 0 | geometría de la latitud | research_2 E2, 11:51 |
| Paneles solares | sun_low_frac_0_5deg | peso 0,15 (0,25–0,03) | 0 | geometría de la latitud | research_2 E2, 11:51 |
| Paneles solares | clear_frac_isccp | — | peso 0,35 (0,308–0,671) | nubes medidas por satélite | ISCCP-H, Rossow y Schiffer 1999 |
| Base lunar | thermal_inertia_class | peso 0,15 | 0 (sigue requerida, puerta "agua") | mismas clases que rock_or_bare_frac | research_3 R, 11:51 |
| Base lunar | rock_or_bare_frac | peso 0,10 (0,1–0,7) | peso 0,25 (0,1–0,7) | un criterio para el suelo | research_3 R, 11:51 |
| Base lunar | permafrost_class | peso 0,05 | 0 | sin vínculo, 607 de 2.419 sin valor, MODELADA | research_3 R, 11:51 |

La misma tabla se publica como texto `deviations_from_team` ("Datos y límites").

## Decisiones tomadas (15-11-2026, 11:23 CET): Rover, top 5, zona de Base lunar, límites y audio

Decisiones tomadas **por la persona delegada en nombre del líder del equipo, 2026-11-15 11:23 CET**, en respuesta a la auditoría estadística (`docs/stats_audit/`, en particular `7_efecto_decisiones_pendientes.md`). Aplicadas en el motor 3.3.0 y en el paquete publicado `app/public/data/v2` (**revisión 7 del contrato**, `docs/DATA_CONTRACT.md`). Todas las cifras de esta sección salen del motor (paquete reconstruido dos veces, idéntico byte a byte) o de las mediciones con el motor `scratchpad/measure_slope_min.py` / `measure_old.py` (salidas `measure_slope_min.json`, `measure_old.json`).

1. **Rover: la elevación relativa pasa a peso cero.** No tiene sentido físico para un rover y choca con el principio de las 04:47 (Rover = pendiente y rugosidad). Su peso se reparte entre las variables de terreno, sin variable nueva: **pendiente 50 % y rugosidad 50 %, las dos clave, tolerancias sin cambio (2° y 30 m)**. **Lectura del director, comunicada al líder:** la elevación relativa sale **también del filtro del par** (una variable de peso cero no debe decidir qué pares existen) y queda como **fila informativa** con sus dos valores y su diferencia (`earth_rover_pairs.bin` `info.elevation_rel_m.earth/.moon/.diff`). En `engine_config.json`: `real_value_similarity.missions.rover` (pesos con `weight_set_by`), `info_differences.rover`, `info_in_pairs_file.rover`.
2. **Top 5: separación mínima de 2° entre los análogos del top 5 de Rover y de Paneles solares**, para que celdas vecinas de un mismo sitio no llenen la lista. **Lectura del director:** es una regla para **elegir los CINCO** (voraz por puesto: se conserva el mejor y se salta cualquiera cuyo centro de celda esté a menos de 2° de arco, círculo máximo sobre la esfera de 6.371,0 km, unos 222,4 km, de uno ya conservado); **el ranking completo sigue ordenado por el final**. Base lunar conserva los puestos 1 a 5 (la regla hoy no cambiaría nada). `engine_config.json` `top5_selection`; `missions.json` `missions[].top5`.
3. **Zona de Base lunar: se mantiene** (las 280 celdas que tocan la huella de las nueve regiones candidatas de la NASA). Los textos dicen "at the edge of NASA's ... candidate region" cuando poca parte de la celda del gemelo cae dentro de su región: regla "in" con ≥ 50 % de la celda dentro, "at the edge of" por debajo (`engine_config.json` `twin_zone_regions`; `twins.json` `nasa_region` de cada gemelo). Hoy **69 de los 103 gemelos** de Base lunar tienen menos del 50 % de su celda dentro de una región.
4. **Mantener y decirlo con honestidad**, en "Data and limits" de la web y en `docs/STATS_AUDIT.md`: las celdas de hielo en el ranking de Rover, la puerta común `elevation_m >= 1` (quita 177 celdas de tierra real por debajo de 1 m, 37 de ellas con al menos 30 % de tierra), la saturación de la similitud de Paneles solares, la fragilidad de cada top 5 con sus porcentajes de estabilidad y los números sin efecto. **`mission_scoring.json` no se edita**: esos números solo se listan. Textos en `similarity.json` `texts` con el campo nuevo `show` (`engine_config.json` `limit_texts`, `top5_stability`, `external_validation`, `limit_facts`).
5. **Audio:** las tres introducciones de misión dirán "five of the highest-scoring analogs in our model" y que el orden es por el final. El equipo vuelve a grabar una vez, cuando los nuevos top 5 sean definitivos (no lo hace este paso; ningún audio se ha generado, editado ni borrado).

**Queda sustituido:** en "Decisiones tomadas (15-11-2026, mañana)", el reparto de pesos de Rover (pendiente 40 %, rugosidad 40 %, elevación relativa 20 % secundaria con tolerancia 500 m y filtro 1.000 m) y, por tanto, la frase "las variables clave pesan el 80 %" del vocabulario para Rover (en Rover pesan el 100 %); la nota de hielo con cifras escritas a mano de `datasets.json` `mission_notes.rover` (ahora `texts.surface_classes_rover`, calculada en cada build).

### Rover antes y después (motor, tablas reales de 1°)

| | Antes (mañana, hasta 11:23) | Después (11:23) |
|---|---|---|
| pasan el embudo | 10.337 | 10.337 |
| emparejados | 10.192 | **10.337** (todos) |
| gemelos distintos | 401 | **1.166** |
| mayor cuota de un gemelo | M61116: 2.033 puntos (19,9 %) | M63712: 265 puntos (2,6 %) |
| puntos con final publicado 100,00 | 0 | **74** (empate: el orden entre ellos es por id de celda) |

Top 5 **antes** (puestos 1-5; todos con el gemelo M59895, Casatus; pendiente y rugosidad Tierra / Luna):

| # | Tierra | Lugar | Gemelo | Sim. / idon. / final | Pendiente (°) | Rugosidad (m) |
|---|---|---|---|---|---|---|
| 1 | E17566 (41,5; 106,5) | Bayinbaolige, China | M59895 Casatus | 99,57 / 99,22 / 99,39 | 1,038 / 1,148 | 43,53 / 44,20 |
| 2 | E23945 (23,5; 5,5) | Tamanrasset, Argelia | M59895 | 99,76 / 98,66 / 99,21 | 1,215 / 1,148 | 43,37 / 44,20 |
| 3 | E18282 (39,5; 102,5) | Ehen Hudag, China | M59895 | 98,77 / 99,58 / 99,17 | 0,908 / 1,148 | 38,75 / 44,20 |
| 4 | E18280 (39,5; 100,5) | Banqiao, China | M59895 | 99,50 / 98,66 / 99,08 | 1,131 / 1,148 | 48,91 / 44,20 |
| 5 | E15395 (47,5; 95,5) | Buga, Mongolia | M59895 | 99,12 / 98,69 / 98,91 | 1,236 / 1,148 | 41,33 / 44,20 |

Top 5 **después** (los cinco mostrados con la separación de 2°; puesto en el ranking completo entre paréntesis):

| # (puesto) | Tierra | Lugar | Gemelo | Sim. / idon. / final | Pendiente (°) | Rugosidad (m) |
|---|---|---|---|---|---|---|
| 1 (1) | E3872 (79,5; 92,5) | Dikson, Rusia | M61299 Drygalski | 100,00 / 100,00 / 100,00 | 0,571 / 0,544 | 26,68 / 26,72 |
| 2 (2) | E4037 (78,5; −102,5) | Gjoa Haven, Canadá | M63714 Sverdrup | 100,00 / 100,00 / 100,00 | 0,770 / 0,793 | 29,34 / 29,50 |
| 3 (4) | E4742 (76,5; −117,5) | Kugluktuk, Canadá | M63712 Haynes | 100,00 / 100,00 / 100,00 | 0,557 / 0,582 | 20,82 / 20,64 |
| 4 (6) | E5111 (75,5; −108,5) | Gjoa Haven, Canadá | M63714 Sverdrup | 100,00 / 100,00 / 100,00 | 0,783 / 0,793 | 29,44 / 29,50 |
| 5 (8) | E5318 (75,5; 98,5) | Khatanga, Rusia | M59713 Schrödinger | 99,99 / 100,00 / 100,00 | 0,708 / 0,719 | 26,21 / 25,76 |

**Aviso:** el número 1, **E3872, es una celda cuya clase de cobertura más frecuente es agua** (ESA CCI 210; solo 33,8 % de tierra, clase térmica del equipo "agua"): costa del mar de Kara. Ninguna regla de Rover excluye el agua. Ninguno de los cinco es hielo. Con el puesto 1 a 74 empatados en 100,00, el orden de los cinco lo decide el id de celda, no el dato (`texts.ties_at_top_rover`).

Diferencias reales de los pares (mediana / P90 / máximo, todos los emparejados):

| Variable | Antes | Después |
|---|---|---|
| pendiente (°) | 0,41 / 0,85 / 1,97 | 0,03 / 0,09 / 0,60 |
| rugosidad (m) | 5,34 / 20,55 / 29,97 | 0,53 / 1,38 / 9,43 |
| elevación relativa (m) | 247,9 / 798,9 / 1.000,0 (comparada) | 3.350 / 5.455 / 10.517 (solo información) |
| temperatura media (K, información) | 148,7 / 175,6 / 233,0 | 149,4 / 191,3 / 257,2 |

Paneles solares: los cinco mostrados pasan de los puestos 1-5 (E38464 Derby, E38105 Derby, E38744 Maintirano, E37746 Kununurra, E38465 Derby) a los puestos **1, 3, 4, 7 y 9**: E38464 Derby (98,45), E38744 Maintirano (98,36), E37746 Kununurra (98,30), E37750 Katherine (98,19) y E29749 Eyl, Somalia (98,16; su clase de cobertura más frecuente es agua, ESA CCI 210, aunque tiene 66 % de tierra). Coincide con la auditoría (`7_efecto_decisiones_pendientes.md` P2). Los ficheros `.bin` de Paneles solares y Base lunar son **idénticos byte a byte** a los del paquete anterior (`tests/test_decisions_1123.py`).

### Pendiente mínima de Rover (0,5°): se mantiene, justificada con datos

Fuente buscada otra vez: `docs/sources/` (R3 línea 17 la clasifica como "pure design choice"; línea 75: "Removes flat terrain, which is unusual for a rover gate; ask why"), `docs/FILTERS.md` (líneas 305 y 349: "n.s.f.", sin fuente), `docs/AUDIT.md` (línea 445: "mark 0.5 deg ... 'no official source'"), `docs/LOCAL_ZIP_COMPARISON.md` (el zip y `rover_preset.py` v3 ponen `min: null`), `rover_preset.py` (línea 214: `"min": None`), comentarios de `mission_scoring.json` (ninguno). **No hay fuente.** Medido con la regla nueva de Rover, con y sin el mínimo:

| | Con mínimo 0,5° | Sin mínimo |
|---|---|---|
| pasan el embudo | 10.337 | 18.184 (+7.847) |
| emparejados | 10.337 | 18.184 |
| gemelos distintos | 1.166 | 1.181 |
| mayor cuota de un gemelo | 2,6 % (265, M63712) | **13,9 %** (2.522, M62913) |
| top 5 del ranking completo | E3872, E4037, E4042, E4742, E4750 | E3675 (pendiente 0,27°), E3872, E4037, E4042, E4044 (0,39°): 2 de 5 nuevos |
| top 50 | — | 28 de 50 son puntos añadidos (todos con pendiente < 0,5°); coinciden 22 de 50 |
| celdas de agua (CCI 210 la más frecuente) en el top 50 | 4 | 13 |
| hielo en el top 50 | 0 | 0 |
| de los 7.847 añadidos | — | 2.862 hielo o nieve (2.856 de clase CCI 220 "hielo permanente"), 373 de agua, 777 de suelo desnudo (200-202) |
| Qaidam / Haughton / Ramon / Yungay (percentil del puesto) | 4,0 / 4,2 / 3,6 / 8,1 % | 8,3 / 8,4 / 8,0 / 11,6 % |
| MDRS / Tabernas / Bardenas | 20,5 / 71,3 / 68,2 % | 22,2 / 83,7 / 81,9 % |
| Dhofar; discordantes Concordia / El Soplao | no pasa (rugosidad < 5 m); Concordia no pasa; El Soplao 95,4 % | igual (rugosidad); El Soplao 97,4 % |

**Regla del líder:** sin fuente, se quita o se justifica con datos; se quita solo si la cabeza del ranking y los análogos conocidos quedan igual o mejor y no entra ningún artefacto en el top 50. **Sin el mínimo** los cuatro análogos de movilidad pierden puesto (su percentil casi se duplica), entran 28 llanuras sin relieve en el top 50 (9 más de agua) y casi 2.900 celdas de hielo permanente en el ranking, y un solo gemelo acumula el 13,9 % de los pares. **Decisión: la pendiente mínima de 0,5° se mantiene**, tal como la escribió el equipo, porque hace trabajo útil: deja fuera de la cabeza del ranking las llanuras sin relieve (agua costera, hielo y planicies con pendiente < 0,5° a 3,7 km de base). Sigue sin fuente externa y así se dice; no hay ninguna anulación en `engine_config.json` y `mission_scoring.json` no se ha tocado.

---

## Decisiones tomadas (15-11-2026, 08:55 CET): Base lunar, zonas y texto de la web

Respuestas dadas el 15-11-2026 a las 08:55 CET por la persona en quien el líder del equipo delegó, **en nombre del líder del equipo** (mensaje de Hark de parte de Facundo), a `docs/LUNAR_BASE_PROPOSAL.md`, `docs/ZONE_CONTRAST.md` y la sección 4 de `docs/MISSION_ZONES.md`. Las cifras de los puntos 2 a 4 se han recalculado hoy con código propio desde las tablas reales y el paquete publicado `app/public/data/v2` (`scratchpad/zonetexts/figures.py`, salida `figures.json`; las zonas del equipo reproducen el paquete gemelo a gemelo) y coinciden con `ZONE_CONTRAST.md`; las medianas por región son ponderadas por área (coseno de la latitud), como en `MISSION_ZONES.md` §2.

1. **Base lunar: confirmado el diseño recomendado (D4b de `docs/LUNAR_BASE_PROPOSAL.md`), no la alternativa sin terreno.** Variables clave: temperatura mínima y amplitud térmica diaria, cada una como **percentil dentro de su población** (Tierra: los 2.419 candidatos del embudo; Luna: las celdas de la zona), 40 % + 40 %, con filtro de **10 puntos de percentil** en las dos. Secundarias en valor real: pendiente y rugosidad, 10 % + 10 %, tolerancias 2° y 30 m y filtro de **4° y 60 m**. **Zona: las nueve regiones candidatas que la NASA anunció el 28-10-2024 (las 280 celdas de 1° que tocan sus cuadrículas USGS), con ese filtro de terreno.** Condiciones: (a) en cada par la web dice que es un parecido de **posición térmica, no de temperatura**, y escribe la diferencia real (vale la frase propuesta en `LUNAR_BASE_PROPOSAL.md`); (b) en la tabla de diferencias la temperatura mínima sale en °C (207,9 °C de mediana): se pide revisar la unidad, debería ser K (una diferencia vale lo mismo en K que en °C, así que es la etiqueta lo que hay que corregir). Lo implementa otro agente: reconstruir, tests y un solo render del vídeo de Base lunar con el rótulo corregido. **Cifras esperadas según la propuesta comprobada (no son las implementadas):** 450 de 2.419 puntos con gemelo, 103 gemelos distintos, número 1 E17538 (Tian Shan) con M63528 (región Haworth). Las cifras finales, las del motor, están en `docs/ANALOG_PRINCIPLE.md` (tabla de resultados de Base lunar): en la comprobación del 15-11-2026 coinciden con las esperadas (450 pares, 103 gemelos, número 1 E17538 – M63528, similitud 97,31, final 72,29; diferencia real mediana de la mínima 207,88 K).
2. **Rover: se mantiene el polo sur (latitud ≤ −75°).** La zona se justifica por los **planes de la NASA** (VIPER, hielo de agua en cráteres en sombra permanente: "The rover can venture into permanently shadowed craters", página de VIPER, consultada hoy), **no por los datos**: por terreno el polo norte (≥ 75 N) sale igual o más parecido. Con el método publicado: emparejan 9.888 de 10.337 puntos en el polo norte frente a 10.192 en el polo sur; similitud mediana 99,7 frente a 93,3; diferencia real mediana de pendiente 0,10° frente a 0,41° y de rugosidad 1,6 m frente a 5,3 m; de los 9.790 puntos con par en los dos, el gemelo del polo norte es más parecido en el 87,3 % (+4,3 puntos de mediana). La web lo dice con la cifra y ningún texto presenta el polo sur como el mejor por datos.
3. **Paneles solares: se mantienen los mares ecuatoriales** (|latitud| ≤ 30° y elevación ≤ −1.200 m). Dos frases honestas en la web: (a) los puntos sin par en los mares sí lo tendrían en las tierras altas de latitud media: de los 12.417 sin gemelo en los mares, 12.416 lo encuentran en la cara oculta (E) y 12.416 en la cara visible (F) (cada una empareja 18.776 de 18.777; el que queda, E19334, no empareja en ninguna parte); (b) los polos quedan fuera para un panel horizontal: la irradiancia máxima en una celda a 75° o más es 2,475 kWh/m²/día (polo sur; 2,451 en el norte), y la celda lunar necesita al menos 3,537 (≈ 3,54) para estar dentro de la tolerancia (0,6) del punto de la Tierra con menos sol de la lista (4,137 sobre la atmósfera).
4. **Motivo de los mares, como objetivo de diseño del equipo:** Sol alto y la irradiancia más alta de nuestros datos sobre las llanuras más bajas y más llanas, con precedente de aterrizajes (Apolo 11, 12, 15 y 17; Luna 9, 13, 16, 20, 21, 23 y 24; Surveyor 1, 3 y 5; Blue Ghost 1: `MISSION_ZONES.md` §1). Cifras (medianas ponderadas por área): irradiancia 10,02 kWh/m²/día en los mares frente a 8,96 en las tierras altas de la cara oculta y 8,25 en las de la visible (la frase "≈10 frente a ≈8" vale para la cara visible; para la oculta es ≈9, y la web dice "8 a 9"); elevación −1.855 m frente a +959 y −851 m (la más baja de las seis regiones); pendiente (`slope_deg`) 1,13° frente a 6,23° y 3,92° (la más baja de las seis regiones; con `slope_iso_deg`, la del motor, 1,12 / 6,07 / 3,75°); rugosidad 46 m frente a 191 y 129 m. **"Más llanas" está respaldado por el dato y se mantiene.** **Matiz de la comprobación independiente (15-11-2026) sobre "la irradiancia más alta":** la mediana de los mares (10,02) es la más alta de las seis regiones y el máximo de la tabla (10,395) está en los mares, pero el suelo ecuatorial fuera de los mares (|latitud| ≤ 30°, 14.914 celdas) recibe lo mismo (mediana 10,11): la ventaja de luz es de la latitud (Sol alto), no del mar, y el "8 a 9" de las tierras altas es la mediana de regiones que llegan a 75° de latitud. Por eso la web dice "sunlight as high as anywhere in our data" y "more sunlight on average", no "the most sunlight".
5. **Texto de la web (`MISSION_ZONES.md` §4): aprobado, con las correcciones aplicadas** (detalle y fuentes en `MISSION_ZONES.md`, "Corrections of 2026-11-15 (after approval)"; textos en `tierra luna/engine/mission_zone_texts.json`, comprobados por `tierra luna/tests/test_mission_zone_texts.py`):
   - **Artemis:** según las páginas de la NASA consultadas hoy, el primer alunizaje tripulado es **Artemis IV** (página de Artemis III, actualizada el 19-10-2026: "Crewed Demonstration" en órbita baja, "before Americans return to the Moon on Artemis IV"; blog del 23-10-2026: "Artemis IV, the first Artemis mission on the lunar surface"). Todas las frases nombran solo Artemis IV y las nueve regiones como las que "NASA named in October 2024" (el comunicado RELEASE24-136 sigue diciendo Artemis III y no se ha actualizado). No había "as of June 2025" en el documento; todas las páginas llevan la fecha de consulta, 15-11-2026.
   - **Misiones 2025-2026:** ispace Resilience: aterrizaje duro el 5-6-2025 en Mare Frigoris (región F, fuera de todas las zonas); Chang'e 7 sin lanzar (CNSA, 23-08-2026; nada nuevo hasta el 09-11-2026); IM-3, Blue Ghost Mission 2, Griffin-1 y Blue Moon Mark 1 previstos, sin lanzar. No se ha encontrado en páginas oficiales ningún aterrizaje ni intento posterior a junio de 2025 ("no encontrado", no "no ocurrió"); se añaden como planes sin sitio Argonaut (ESA, 2030, región polar sur) y el módulo coreano (KASA, 2032). Ninguna frase cambia por ello.
   - **Rover, polo sur:** ninguna frase decía "Rovers have not driven at the south pole". No se afirma que ningún rover haya circulado más allá de 75° S: el rover MAPP de IM-2 no se desplegó (Lunar Outpost), y NASA solo dice que el saltador cumplió "some objectives"; el operador de Yaoki (Dymon, 27-07-2026) habla de una imagen del interior de un cráter "tomada en la superficie lunar" por Yaoki, sin decir si se desplazó. Por eso no se afirma nada en ningún sentido. La frase de Pragyan añade que la India llama al de Chandrayaan-3 un alunizaje en el polo sur.
   - **Añadidas** tres frases "why this zone" (Rover, Paneles solares, Base lunar), mostradas al elegir la misión, con las cifras de los puntos 2 a 4; las frases polares de Paneles citan ahora el máximo (2,48 / 2,45) y los 3,54 en lugar de las medianas.

**Queda sustituido:** el punto 9 de "Decisiones tomadas (15-11-2026, mañana)" (Base lunar sin cambios y pendiente) y el estado "Base lunar: pendiente" de "Principio del análogo".

---

## Decisiones tomadas (15-11-2026, mañana)

Respuestas dadas el 15-11-2026 por la mañana por la persona en quien el líder del equipo delegó, **en nombre del líder del equipo**, a la propuesta de `docs/ANALOG_PRINCIPLE.md` (principio P1-P9 de Facundo, 15-11-2026, 04:47-04:49 CET). Aplicadas en el motor 3.1.0 (`tierra luna/engine/real_similarity.py`, `engine_config.json` `similarity_rule`, `real_value_similarity`, `toa_insolation`) y en el paquete publicado `app/public/data/v2` (revisión 5 del contrato). Los resultados están en `docs/ANALOG_PRINCIPLE.md`, sección "Resultado tras implementar (15-11-2026)".

**[SUSTITUIDO el 15-11-2026 para Base lunar** por "Decisiones tomadas (15-11-2026, 08:55 CET)", punto 1: Base lunar ya no usa `zone_twin` sino `percentile_and_real_tolerance`. Lo de Rover y Paneles solares sigue vigente.] **La regla de similitud pasa a ser un ajuste por misión** (`engine_config.json` `similarity_rule`): Rover y Paneles solares, `real_value_tolerance`; Base lunar, `zone_twin` sin ningún cambio. Las reglas anteriores (`zone_twin`, `repo_global_mean`, `physical_pooled`) siguen disponibles con `--similarity-rule` y probadas.

1. **Método para Rover y Paneles solares: similitud sobre valores reales.** Para cada variable, puntuación `s = exp(−0,5 × (diferencia / tolerancia)²)` sobre la diferencia absoluta entre la celda de la Tierra y la lunar; similitud = 100 × media ponderada de las puntuaciones; las variables clave llevan el 80 % del peso. **Filtro del par:** cada variable clave a menos de su tolerancia y cada secundaria a menos del doble de la suya; si no, el par no es análogo y no se enseña. **Gemelo:** la celda lunar de la zona de la misión que pasa el filtro con la similitud más alta (empate: el id más bajo). **Final** = 0,5 × similitud + 0,5 × idoneidad para los puntos con par. El embudo (filtros duros e idoneidad de `mission_scoring.json`) no cambia. Una variable clave sin dato en un lado hace fallar el filtro; una secundaria sin dato se deja fuera del filtro y de la similitud y se renormalizan los pesos.
2. **Rover.** Claves: pendiente y rugosidad (40 % + 40 %), tolerancias 2° y 30 m: los valores del propio equipo en `tierra luna/rover_preset.py` (versión 3, `tolerances_by_baseline`, base de 5 km, líneas 196-205), marcados allí como ilustrativos: **"valores ilustrativos del equipo"**. Secundaria: elevación relativa (20 %), tolerancia 500 m. Zona: polo sur (latitud ≤ −75°), sin cambio. Resultado: 10.192 de 10.337 puntos con gemelo; número 1 E17566 (41,5 N 106,5 E) con M59895 (76,5 S 44,5 O), como en la propuesta comprobada.
3. **Elevación relativa:** la elevación menos la media de la elevación del propio cuerpo ponderada por el área (cos de la latitud), sobre todas las celdas con dato: Tierra +695,9 m (las celdas con `elevation_m`, es decir, tierra firme), Luna −248,4 m. Sustituye a la elevación sin centrar que exportaba el motor (`elevation_m` tal cual).
4. **Paneles solares.** Clave: **irradiancia sin atmósfera** (80 %): en la Tierra, la luz solar diaria media anual sobre una superficie horizontal en el tope de la atmósfera, calculada a partir de la latitud con una órbita de Kepler y la constante solar ya citada en la procedencia (1.361 W/m², `real_data/provenance_moon.csv`, fila `irradiance_kwh_m2_day`, ficha lunar del NSSDC); oblicuidad 23,44° y excentricidad 0,0167 de la ficha de la Tierra del NSSDC. Es un valor **DERIVADO** nuevo (`irradiance_toa_kwh_m2_day`), con la fórmula corregida del comprobador (`docs/ANALOG_PRINCIPLE.md`, "Comprobación", punto 1): 9,97 / 8,77 / 7,37 / 5,67 kWh/m²/día a 0 / 30 / 45 / 60° (lo comprueba un test). En la Luna, la irradiancia de superficie de la tabla lunar (sin atmósfera). Tolerancia 0,6 kWh/m²/día. Secundarias: pendiente y rugosidad (10 % + 10 %) con las tolerancias del Rover. Zona: los mares ecuatoriales tal como los define `analog_finder.build_lunar_reference_zones`: `(np.abs(lat) <= 30.0) & (moon_norm_df["elevation_m"] <= -1200.0)`, aplicada a la tabla lunar real: 6.686 celdas. Resultado: 6.360 de 18.777 puntos con gemelo; 12.417 sin gemelo.
5. **Puntos sin gemelo** (Paneles solares sobre todo): se siguen enseñando, **sin gemelo**: conservan su resultado del embudo y su idoneidad, no tienen similitud ni final, se listan después de los puntos con par por idoneidad (empate: id) y llevan el motivo: qué variable no tiene ninguna celda lunar dentro de la tolerancia y la diferencia más pequeña encontrada (`earth_<misión>_pairs.bin` `nopair_kind`, `nopair_var`, `nopair_gap`; resumen en `missions.json` `similarity.unpaired_reasons`).
6. **Condición del equipo para Paneles solares:** cada par lleva también la irradiancia en el suelo de la celda de la Tierra y la parte que se pierde en la atmósfera (por ejemplo 6,2 de 9,6, un 35 % menos en el número 1; **corregido el 15-11-2026: antes decía "36 %"**, que era 100 × `atm.lost_share`, la parte perdida calculada con los valores sin redondear (35,66 %, redondeado a 36); desde la regla de redondeo de la web de ese día (`docs/DATA_CONTRACT.md`, `share_lost_of_displayed_tenths`) el porcentaje se calcula con los dos números que se enseñan, 6,2 y 9,6: 100 × (9,6 − 6,2) / 9,6 = 35,4 → **35**, que es lo que dicen la web, `docs/AUDIO_TOP5.json` y el audio solar_1), y ningún texto dice ni da a entender que los paneles cargan lo mismo en los dos sitios. El texto de limitación de anoche se **sustituye** por esta plantilla, que la web rellena por par (`similarity.json` `texts.solar_limitation`, con el nombre y el archivo de cada valor en `placeholders`; `{lunar_day}` lo rellena el motor con 29,5):

> "This pair is matched on sunlight above the atmosphere: {toa_earth} kWh/m²/day at the top of Earth's atmosphere here and {toa_moon} kWh/m²/day on the lunar surface. At the Earth site only {ground_earth} of those {toa_earth} kWh/m²/day reach the ground ({loss_pct} % is lost in the atmosphere), while the Moon has no atmosphere and its day lasts {lunar_day} Earth days, about half of them in darkness. Terrain (slope and roughness) is a secondary criterion."

*Traducción:* "Este par se empareja por la luz del Sol por encima de la atmósfera: {toa_earth} kWh/m²/día en el tope de la atmósfera de la Tierra aquí y {toa_moon} kWh/m²/día en la superficie lunar. En el sitio de la Tierra solo llegan al suelo {ground_earth} de esos {toa_earth} kWh/m²/día (se pierde un {loss_pct} % en la atmósfera), mientras que la Luna no tiene atmósfera y su día dura 29,5 días terrestres, la mitad de ellos a oscuras. El terreno (pendiente y rugosidad) es un criterio secundario."

7. **Tolerancias y quién las fijó** (todas en `engine_config.json` `real_value_similarity`, con su porqué): irradiancia 0,6 kWh/m²/día y elevación relativa 500 m, **fijadas por la persona delegada en nombre del líder del equipo el 15-11-2026**; pendiente 2° y rugosidad 30 m, **valores ilustrativos del equipo** (`rover_preset.py`); temperatura 10 K y amplitud térmica 5 K quedan **solo como referencia**: ninguna misión las usa ahora.
8. **Significado de la similitud.** Para Rover y Paneles solares la web enseña este texto (`similarity.json` `texts.similarity_meaning_real_values`):

> "Each Earth point is paired with its lunar twin: the 1-degree lunar cell, inside the mission's target zone, whose real values are closest. Similarity is computed on real values within stated tolerances: every key variable of the twin is within its tolerance of the Earth point and every secondary variable within twice its tolerance, and each variable scores lower the further apart the two values are. Both values and their difference are shown side by side."

*Traducción:* "Cada punto de la Tierra se empareja con su gemelo lunar: la celda lunar de 1 grado, dentro de la zona objetivo de la misión, cuyos valores reales son los más cercanos. La similitud se calcula sobre valores reales dentro de tolerancias declaradas: cada variable clave del gemelo está a menos de su tolerancia del punto de la Tierra y cada variable secundaria a menos del doble de la suya, y cada variable puntúa menos cuanto más se separan los dos valores. Los dos valores y su diferencia se enseñan uno al lado del otro."

   Y en los puntos sin gemelo (`texts.no_twin_note`; hay una variante para `no_joint_match`):

> "No lunar analog: no cell of the mission's lunar zone has {variable} within {bound} {unit} of this point (closest: {gap} {unit} away). The point keeps its suitability; it has no similarity and no final score."

*Traducción:* "Sin análogo lunar: ninguna celda de la zona lunar de la misión tiene {variable} a menos de {bound} {unit} de este punto (la más cercana está a {gap} {unit}). El punto conserva su idoneidad; no tiene similitud ni puntuación final."

9. *(Sustituido para Base lunar por "Decisiones tomadas (15-11-2026, 08:55 CET)", punto 1.)* **Base lunar: sin cambios y pendiente.** Su regla (`zone_twin` en z sobre las nueve regiones de la NASA), su zona, sus gemelos y cada número exportado siguen exactamente como en el paquete anterior (lo prueba `tests/test_real_value_similarity.py::test_lunar_base_is_unchanged_from_the_previous_bundle`: `earth_lunar_base.bin`, `moon_lunar_base.bin`, la parte de Base lunar de `twins.json`, `explain.json` y `missions.json`, idénticos). La frase de significado de anoche (decisión 1) sigue valiendo **solo para Base lunar**. Mensaje de Facundo (07:55, vía Hark): Base lunar tiene que tener análogos en la Tierra y no vale dejarla como "no análoga"; antes de reconstruirla quiere confirmar una propuesta (variables, pesos y normalización, tolerancia, pares que sobreviven, número 1 y su gemelo, diferencias reales). Esa propuesta se prepara aparte (`docs/LUNAR_BASE_PROPOSAL.md`); **Base lunar no se ha reconstruido**.

**Queda sustituido para Rover y Paneles solares** (sigue valiendo para Base lunar donde se indica):

- Decisión 1: la regla `zone_twin` en z y su frase de significado ("misma posición dentro del rango de cada mundo") ya no se aplican a Rover ni a Paneles solares; para Base lunar sí.
- Decisión 5: Paneles solares deja el polo sur (pasa a los mares ecuatoriales) y el texto de limitación de anoche ("Limitation: for solar arrays, the lunar twin is chosen by terrain shape and surface temperature, not by sunlight...") se retira del paquete; lo sustituye la plantilla del punto 6. El párrafo de `ASSUMPTIONS.md` de anoche sobre la anticorrelación queda como histórico.
- Decisión 3: la marca "sin dato de temperatura" ya no afecta a Rover ni a Paneles solares (la temperatura no entra en su similitud); sigue en Base lunar.
- Decisión 4 (concentración de gemelos): sigue igual; para Rover y Paneles solares la web enseña solo la primera frase del texto.

---

## Decisiones tomadas (15-11-2026)

**[SUSTITUIDO el 15-11-2026** por "Decisiones tomadas (15-11-2026, mañana)" (Rover y Paneles solares: `real_value_tolerance`; Paneles solares pasan del polo sur a los mares ecuatoriales) y por "Decisiones tomadas (15-11-2026, 08:55 CET)" (Base lunar: `percentile_and_real_tolerance`). Ninguna misión usa ya `zone_twin` ni los z; la marca "sin dato de temperatura" (punto 3) no se enseña. Se conserva como historia.]

Respuestas del equipo dadas el 15-11-2026 por la persona en quien el líder del equipo delegó el seguimiento esa noche, en el orden 1, 5, 3, 2, 4:

1. **Regla del gemelo: sí.** Se activa `zone_twin` (A1) con los `DEFAULT_WEIGHTS` del repositorio sin radar ni roca (pendiente 33,3 %, rugosidad 26,7 %, elevación relativa 20 %, temperatura 20 %), no los pesos por dominio. Zonas: Rover y Paneles solares en el polo sur (latitud ≤ −75°, versión de la rama, commit `ff6f1ae`; no Tycho); Base lunar en las nueve regiones de la NASA. Junto al parecido se enseñan siempre los valores absolutos de cada variable en la Tierra y en la Luna, con una frase que dice que el parecido es posición relativa dentro de cada cuerpo.
5. **Paneles solares: se quedan en el polo sur**, sin cambio de zona esta noche. Se publica el texto de limitación tal cual en la ficha de la misión y el párrafo en `ASSUMPTIONS.md` §0.7, antes de grabar vídeo o capturas. Los mares ecuatoriales no se implementan: quedan como alternativa para que el líder del equipo la valore por la mañana (ver la nota al final de la decisión 5).
3. **Antártida sin temperatura: ignorar y renormalizar**, como ya hace el motor. La web marca los pares a los que les falta la temperatura ("sin dato de temperatura: parecido calculado con 3 variables") y la marca se ve también en el ranking. No se usa NASA POWER ni ninguna otra fuente nueva.
2. **Roca: retirada definitiva del parecido** con reparto proporcional. La web la enseña como dato informativo marcado "no entra en el parecido".
4. **Concentración en Base lunar: se acepta** y el panel enseña cuántos puntos comparten cada gemelo, con el texto de la sección 8. Sin límites por gemelo.

---

## Decisión 1. La regla del gemelo

**[SUSTITUIDO el 15-11-2026** por "Decisiones tomadas (15-11-2026, mañana)" y "Decisiones tomadas (15-11-2026, 08:55 CET)". Toda esta decisión (secciones 1 a 8) describe la regla `zone_twin` en z como la de "hoy" (la noche del 14 al 15): ya no la usa ninguna misión. Se conserva como historia; la regla vigente está en el vocabulario del principio.]

### 1. Qué pasa ahora

**[SUSTITUIDO el 15-11-2026** (ver el principio de la Decisión 1): "hoy" en esta sección es la noche del 14 al 15 de noviembre; la regla de abajo ya no es la del producto.]

**Cómo se elige hoy el gemelo, paso a paso (regla A1 de la propuesta):**

1. La celda de la Tierra pasa el embudo de la misión sin cambios (puertas comunes, variables obligatorias, filtros duros y la idoneidad de `mission_scoring.json`; Base lunar = copia del bloque `thermal`). Las celdas de la Luna no se filtran.
2. Cada cuerpo se normaliza por separado con `normalize_planetary_features` (`tierra luna/analog_finder.py`, líneas 143-181; la fórmula de z está en las líneas 160-167). En la Tierra la población son las celdas con `elevation_m > 0` (línea 463); en la Luna, todas.
3. Variables y pesos: `DEFAULT_WEIGHTS` (líneas 68-75): elevación relativa 0,15; pendiente 0,25; rugosidad 0,20; temperatura 0,15; roca 0,15; radar 0,10. En las tablas reales no hay radar y la roca se ha quitado (decisión 2), así que los pesos se reparten en proporción entre las cuatro que quedan: **pendiente 33,33 %, rugosidad 26,67 %, elevación relativa 20,00 %, temperatura 20,00 %**.
4. Distancia y similitud: la de `compute_analog_ranking` (línea 489: `similarity_pct = 100.0 * np.exp(-0.45 * rms_dist)`).
5. El gemelo es la celda lunar **de la zona de la misión** con la distancia más pequeña; si hay empate, la de identificador más bajo.

**Zona lunar de cada misión y número de celdas** (cálculo de hoy y propuesta, §3):

| misión | zona lunar | celdas, tabla real 1° | celdas, tabla antigua 2° |
|---|---|---|---|
| Rover | Polo sur, latitud ≤ 75 S (`analog_finder.py` línea 189: `lat <= -75.0`) | 5.400 | 1.440 |
| Paneles solares | la misma zona del polo sur | 5.400 | 1.440 |
| Base lunar | las nueve regiones candidatas de aterrizaje de Artemis que NASA anunció el 28-10-2024 (rejillas USGS, McClernan 2024, doi:10.5066/P1MEQ6UK, CC0) | 280 | 114 |
| (referencia) Tycho, la zona del Rover en `main` | caja 35 S-55 S, 30 O-5 E (`analog_finder.py` líneas 193-195) | 700 | 198 |
| (referencia) Luna entera | todas | 64.800 | 16.200 |

**Qué versión de `analog_finder.py` está en uso.** En `main` el Rover apunta a Tycho (`git show main:"tierra luna/analog_finder.py"`, línea 259: `"rover": rocky_target,`). En `final-integration` está la decisión posterior del equipo, que lo manda al polo sur. Entró en el **commit `ff6f1ae`** (14-11-2026, 23:46 UTC, "Checkpoint: rover v3 integration and web interaction modules in progress"; `git log -S"Plan decision 2"` devuelve solo ese commit). Líneas 259-261 de `compute_mission_optimality_scores`:

```python
        # [AI-assisted] Plan decision 2: the lunar target is the Shackleton
        # region (the only Moon Base site NASA has named), not Tycho.
        "rover": polar_target,
```

El fichero de trabajo no tiene cambios respecto a ese commit (`git diff HEAD` vacío).

**Pero el gemelo todavía no está encendido.** El producto se construye con el motor `tierra luna/engine/`, y su ajuste `similarity_rule` vale hoy `"repo_global_mean"` (`engine/engine_config.json`, línea 218): cada punto de la Tierra se compara con el **perfil medio de toda la Luna**, no hay gemelo y la similitud es la misma para las tres misiones. Ojo: el motor de hoy **ya quita la roca** y ya ignora la temperatura que falta (decisiones 2 y 3), así que lo que enseña hoy la web (llamémoslo **E0**) no es lo mismo que daría `analog_finder.py` tal cual, con roca y con z = 0 para lo que falta (**A0**, la línea base de la propuesta). He comprobado E0 contra el paquete publicado en `app/public/data/v2` (`similarity.json` dice `rule: repo_global_mean`): mi cálculo reproduce su similitud en los 31.533 puntos (diferencia 0) y sus tres top 10 en el mismo orden. La regla del gemelo es el valor `"zone_twin"` del mismo ajuste (línea 224), con las zonas de `similarity_zones` (líneas 246-274). Encenderla es cambiar ese valor y volver a construir (`python -m engine build`), según `ASSUMPTIONS.md` §0.4.

**Pesos fijos frente a pesos por misión.** Con `DEFAULT_WEIGHTS` las tres misiones usan los mismos cuatro pesos. La otra posibilidad es convertir los pesos por dominio de cada misión (relieve, material, térmico, luz, agua; `mission_scoring.json`) en pesos por variable:

- **A2** = la función que ya existe, `map_domain_weights_to_features` (`analog_finder.py` líneas 225-240, la del botón "Use Weights" de la web). Reparte "luz" y "agua", que no tienen variable propia, entre temperatura y elevación.
- **A3a** = cada dominio gasta su peso solo en sus variables; "luz" y "agua" se descartan.

Pesos efectivos en la tabla real (propuesta, §4.1), en % de la similitud:

| misión | variante | pendiente | rugosidad | elevación relativa | temperatura |
|---|---|---|---|---|---|
| las tres | A1 (fijos) | 33,33 | 26,67 | 20,00 | 20,00 |
| Rover | A2 | 25,65 | 27,14 | 20,07 | 27,14 |
| Rover | A3a | 32,41 | 25,93 | 19,44 | 22,22 |
| Paneles solares | A2 | 17,36 | 9,32 | 26,69 | 46,62 |
| Paneles solares | A3a | 17,86 | 14,29 | 10,71 | 57,14 |
| Base lunar | A2 | 12,18 | 15,13 | 11,07 | 61,62 |
| Base lunar | A3a | 10,42 | 8,33 | 6,25 | 75,00 |

### 2. El problema

Hoy no hay pares: la web enseña una similitud contra una "Luna media" que no existe en ningún sitio, la misma para las tres misiones. Eso no responde a la promesa del producto ("este sitio de la Tierra se parece a este sitio de la Luna").

Además, la elección de pesos cambia mucho los gemelos de Paneles solares y Base lunar. Gemelos que cambian respecto a A1 (cálculo de hoy sobre las salidas por celda de la propuesta):

| misión | puntos | cambian de gemelo con A2 | con A3a | Spearman del final A1 vs A2 / A3a (propuesta §3) | top 10 compartido A1 vs A2 / A3a |
|---|---|---|---|---|---|
| Rover | 10.337 | 2.106 (20,4 %) | 632 (6,1 %) | 0,997 / 1,000 | 8/10 / 10/10 |
| Paneles solares | 18.777 | 7.732 (41,2 %) | 10.885 (58,0 %) | 0,933 / 0,887 | 0/10 / 0/10 |
| Base lunar | 2.419 | 2.041 (84,4 %) | 2.137 (88,3 %) | 0,987 / 0,980 | 5/10 / 4/10 |

Con A2 o A3a la temperatura pesa entre el 47 % y el 75 % en Paneles y Base lunar, y en Base lunar una sola celda lunar (M64190, de Gerlache) se lleva el 66,1 % (A2) o el 63,9 % (A3a) de todos los puntos (propuesta, §3.3).

### 3. Un ejemplo concreto

El cráter de Haughton (isla Devon, Nunavut, Canadá), un análogo lunar real, cae en la celda **E5130 (75,5 N 89,5 O)**. Rover, idoneidad 98,9. Valores de la celda: pendiente 1,01°, rugosidad 52 m, elevación relativa −432 m, temperatura de superficie 253,0 K.

| regla | similitud | final | puesto (de 10.337) | gemelo lunar |
|---|---|---|---|---|
| Hoy en la web (motor, Luna media sin roca, E0) | 72,8 | 85,8 | 625 | ninguno |
| `analog_finder` tal cual (Luna media con roca, A0; la línea base de la propuesta) | 45,4 | 72,1 | 4.224 | ninguno |
| A1 (pesos fijos, polo sur) | 96,1 | 97,5 | 80 | M59910, 76,5 S 29,5 O, cráter Newton a 85 km |
| A2 (pesos "Use Weights") | 96,0 | 97,5 | 81 | el mismo |
| A3a (sin diluir) | 96,1 | 97,5 | 78 | el mismo |
| A1 con la zona de `main` (Tycho) | 80,1 | 89,5 | 919 | M50930, 51,5 S 9,5 O, Maginus a 81 km |

El gemelo polar (Newton) tiene pendiente 6,8°, rugosidad 243 m, elevación relativa −1.027 m y 154,1 K. Los valores absolutos no se parecen; las posiciones relativas sí (z de la pendiente +0,51 en la Tierra y +0,58 en la Luna; z de la temperatura −1,45 y −1,35).

### 4. Las opciones

| opción | a favor | en contra |
|---|---|---|
| **A. Encender A1 con pesos fijos** (`similarity_rule = zone_twin`) | Da un par real con nombre, coordenadas y enlace al nomenclátor de la IAU. Mismos pesos para las tres misiones: fácil de explicar. Para el Rover da casi lo mismo que A3a (Spearman 1,000). Ya está implementado y verificado. | Los pesos no dependen de la misión. Los gemelos se concentran (decisión 4). Paneles solares sigue siendo indefendible (decisión 5). |
| B. A1 con pesos A2 ("Use Weights") | Usa los pesos que el equipo escribió por misión. | "Luz" y "agua" no tienen variable y se cuelan en temperatura y elevación: en Base lunar la temperatura pesa el 61,62 % y el 66,1 % de los puntos acaba en una celda. |
| C. A1 con pesos A3a | Respeta los dominios sin filtraciones. | Base lunar: 75 % temperatura, el 63,9 % de los puntos en una celda. Habría que explicar una regla nueva de reparto. |
| D. Seguir con la Luna media (hoy) | No hay que tocar nada. | No hay par. La similitud es la misma para las tres misiones. Se compara con una "Luna media" que no es ningún sitio: el top 10 del Rover es estepa de Mongolia, Mongolia Interior y Xinjiang, más una celda de Chubut (Argentina). |
| E. Rover a Tycho (como en `main`) | Tycho es un cráter conocido. | Contradice la decisión del equipo ya en la rama (`ff6f1ae`). El top 10 pasa a ser estepa de Mongolia y Kazajistán; una sola celda (M49851, 48,5 S 8,5 O, cerca de Maginus) se lleva el 25,5 % de los puntos (2.633). |

### 5. Recomendación y por qué

**Encender A1 tal como está propuesta, con los pesos fijos `DEFAULT_WEIGHTS`, polo sur para Rover y Paneles y las nueve regiones de Artemis para Base lunar.** Los números lo apoyan: A3a da el mismo Rover que A1; A2 y A3a, en las otras dos misiones, convierten la similitud en una comparación casi solo de temperatura y concentran Base lunar en una celda. No hay ningún número que contradiga la recomendación del director.

### 6. Qué cambia en los resultados si se acepta

Todos los puntos clasificados pasan de "sin gemelo" a "con gemelo": **31.533 pares** (10.337 + 18.777 + 2.419). Ningún punto del top 10 actual sigue en el top 10 en ninguna misión (0/10 en las tres, tanto frente a lo que enseña hoy la web, E0, como frente a A0). Spearman del final, antes frente a después: frente a la web de hoy (E0, ambos con el tratamiento del motor para la temperatura que falta), Rover 0,578; Paneles 0,646; Base lunar 0,117. Frente a A0 (propuesta, §1): 0,334; 0,567; −0,159.

*Matiz:* el motor trata los puntos antárticos sin temperatura de forma distinta a la propuesta (decisión 3). Eso no cambia ningún top 10 de "después".

Los "antes" de abajo son los que enseña hoy la web (E0, leídos del paquete `app/public/data/v2` y recalculados). Los top 10 de A0 (con roca) están en la propuesta, §5; el del Rover eran praderas de Canadá, Montana y Kazajistán.

**Rover, antes (web de hoy, E0):**

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final |
|---|---|---|---|---|---|---|
| 1 | E15056 | 48,5 N 116,5 E | China / Inner Mongolia | 100,0 | 98,8 | 99,4 |
| 2 | E15055 | 48,5 N 115,5 E | Mongolia | 100,0 | 97,2 | 98,6 |
| 3 | E15054 | 48,5 N 114,5 E | Mongolia / East Aimak | 100,0 | 96,7 | 98,4 |
| 4 | E15748 | 46,5 N 88,5 E | China / Xinjiang Uygur Zizhiqu | 100,0 | 95,8 | 97,9 |
| 5 | E15053 | 48,5 N 113,5 E | Mongolia / East Aimak | 100,0 | 94,9 | 97,4 |
| 6 | E15414 | 47,5 N 114,5 E | Mongolia / East Aimak | 100,0 | 94,8 | 97,4 |
| 7 | E15747 | 46,5 N 87,5 E | China / Xinjiang Uygur Zizhiqu | 100,0 | 94,8 | 97,4 |
| 8 | E15776 | 46,5 N 116,5 E | Mongolia | 97,7 | 96,1 | 96,9 |
| 9 | E48709 | 45,5 S 70,5 O | Argentina / Chubut | 100,0 | 93,8 | 96,9 |
| 10 | E16137 | 45,5 N 117,5 E | China / Inner Mongolia | 100,0 | 93,2 | 96,6 |

**Rover, después (A1):**

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final | gemela lunar (IAU más cercano) |
|---|---|---|---|---|---|---|---|
| 1 | E5128 | 75,5 N 91,5 O | Canada | 99,8 | 98,4 | 99,1 | M60952, 79,5 S 67,5 O, Drygalski a 108 km |
| 2 | E6903 | 70,5 N 116,5 O | Canada | 100,0 | 98,1 | 99,0 | M60093, 76,5 S 153,5 E, Schrodinger a 163 km |
| 3 | E5485 | 74,5 N 94,5 O | Canada | 99,8 | 97,9 | 98,9 | M60536, 78,5 S 123,5 O, Ashbrook a 105 km |
| 4 | E6904 | 70,5 N 115,5 O | Canada | 100,0 | 97,6 | 98,8 | M60093, 76,5 S 153,5 E, Schrodinger a 163 km |
| 5 | E5845 | 73,5 N 94,5 O | Canada | 99,8 | 97,7 | 98,8 | M59507, 75,5 S 72,5 O, Le Gentil a 46 km |
| 6 | E4036 | 78,5 N 103,5 O | Canada | 100,0 | 97,5 | 98,8 | M59545, 75,5 S 34,5 O, Casatus a 91 km |
| 7 | E5129 | 75,5 N 90,5 O | Canada | 99,8 | 97,7 | 98,7 | M60536, 78,5 S 123,5 O, Ashbrook a 105 km |
| 8 | E5118 | 75,5 N 101,5 O | Canada | 99,6 | 97,9 | 98,7 | M61164, 79,5 S 144,5 E, Nefed ev a 65 km |
| 9 | E4037 | 78,5 N 102,5 O | Canada | 100,0 | 97,3 | 98,6 | M59545, 75,5 S 34,5 O, Casatus a 91 km |
| 10 | E6538 | 71,5 N 121,5 O | Canada | 100,0 | 97,3 | 98,6 | M60093, 76,5 S 153,5 E, Schrodinger a 163 km |

**Paneles solares, antes (web de hoy, E0):**

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final |
|---|---|---|---|---|---|---|
| 1 | E42680 | 28,5 S 20,5 E | South Africa / Northern Cape | 94,0 | 81,2 | 87,7 |
| 2 | E30079 | 6,5 N 19,5 E | Central African Rep. / Nana-Grebizi | 92,9 | 82,1 | 87,5 |
| 3 | E30078 | 6,5 N 18,5 E | Central African Rep. / Ouham | 93,2 | 81,8 | 87,5 |
| 4 | E39563 | 19,5 S 143,5 E | Australia | 94,9 | 80,0 | 87,4 |
| 5 | E43039 | 29,5 S 19,5 E | South Africa / Northern Cape | 92,4 | 82,4 | 87,4 |
| 6 | E30077 | 6,5 N 17,5 E | Central African Rep. / Ouham | 93,3 | 81,5 | 87,4 |
| 7 | E41352 | 24,5 S 132,5 E | Australia | 94,5 | 80,3 | 87,4 |
| 8 | E42072 | 26,5 S 132,5 E | Australia | 93,4 | 81,4 | 87,4 |
| 9 | E42681 | 28,5 S 21,5 E | South Africa / Northern Cape | 93,5 | 81,2 | 87,4 |
| 10 | E43138 | 29,5 S 118,5 E | Australia | 92,6 | 82,2 | 87,4 |

**Paneles solares, después:**

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final | gemela lunar (IAU más cercano) |
|---|---|---|---|---|---|---|---|
| 1 | E44120 | 32,5 S 20,5 E | South Africa / Western Cape | 86,8 | 78,0 | 82,4 | M59479, 75,5 S 100,5 O, Boltzmann a 81 km |
| 2 | E40517 | 22,5 S 17,5 E | Namibia / Khomas | 93,3 | 71,4 | 82,4 | M60006, 76,5 S 66,5 E, Demonax a 68 km |
| 3 | E37308 | 13,5 S 48,5 E | Madagascar / Diana | 92,1 | 72,7 | 82,4 | M59478, 75,5 S 101,5 O, Boltzmann a 88 km |
| 4 | E27615 | 13,5 N 75,5 E | India / Karnataka | 90,9 | 73,6 | 82,3 | M59479, 75,5 S 100,5 O, Boltzmann a 81 km |
| 5 | E42682 | 28,5 S 22,5 E | South Africa / Northern Cape | 93,0 | 71,4 | 82,2 | M59636, 75,5 S 56,5 E, Demonax a 81 km |
| 6 | E42323 | 27,5 S 23,5 E | South Africa / Northern Cape | 92,9 | 71,3 | 82,1 | M59539, 75,5 S 40,5 O, Casatus a 117 km |
| 7 | E42683 | 28,5 S 23,5 E | South Africa / Northern Cape | 92,4 | 71,9 | 82,1 | M59539, 75,5 S 40,5 O, Casatus a 117 km |
| 8 | E27814 | 12,5 N 85,5 O | Nicaragua / Boaco | 91,2 | 73,1 | 82,1 | M59479, 75,5 S 100,5 O, Boltzmann a 81 km |
| 9 | E41606 | 25,5 S 26,5 E | South Africa / North-West | 91,6 | 72,6 | 82,1 | M59636, 75,5 S 56,5 E, Demonax a 81 km |
| 10 | E43042 | 29,5 S 22,5 E | South Africa / Northern Cape | 93,0 | 71,2 | 82,1 | M59636, 75,5 S 56,5 E, Demonax a 81 km |

**Base lunar, antes (web de hoy, E0):**

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final |
|---|---|---|---|---|---|---|
| 1 | E15055 | 48,5 N 115,5 E | Mongolia | 53,0 | 97,2 | 75,1 |
| 2 | E15056 | 48,5 N 116,5 E | China / Inner Mongolia | 49,0 | 98,8 | 73,9 |
| 3 | E17553 | 41,5 N 93,5 E | China | 62,6 | 84,9 | 73,8 |
| 4 | E17200 | 42,5 N 100,5 E | China / Inner Mongolia | 60,7 | 86,5 | 73,6 |
| 5 | E15054 | 48,5 N 114,5 E | Mongolia / East Aimak | 50,3 | 96,7 | 73,5 |
| 6 | E17921 | 40,5 N 101,5 E | China / Inner Mongolia | 63,2 | 83,8 | 73,5 |
| 7 | E18266 | 39,5 N 86,5 E | China | 62,0 | 84,8 | 73,4 |
| 8 | E15415 | 47,5 N 115,5 E | Mongolia / East Aimak | 50,2 | 96,6 | 73,4 |
| 9 | E14695 | 49,5 N 115,5 E | Mongolia / East Aimak | 51,0 | 95,6 | 73,3 |
| 10 | E17201 | 42,5 N 101,5 E | China / Inner Mongolia | 60,6 | 85,9 | 73,3 |

**Base lunar, después:**

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final | gemela lunar (IAU más cercano) |
|---|---|---|---|---|---|---|---|
| 1 | E19345 | 36,5 N 85,5 E | China / Xinjiang Uygur Zizhiqu | 69,6 | 83,8 | 76,7 | M62859, 84,5 S 39,5 E, Floss a 11 km [Mons Mouton Plateau] |
| 2 | E19704 | 35,5 N 84,5 E | China | 71,6 | 80,8 | 76,2 | M62858, 84,5 S 38,5 E, Floss a 13 km [Mons Mouton Plateau, Nobile Rim 1] |
| 3 | E19699 | 35,5 N 79,5 E | China | 67,4 | 84,2 | 75,8 | M63218, 85,5 S 38,5 E, Masina a 15 km [Mons Mouton Plateau, Nobile Rim 1] |
| 4 | E19703 | 35,5 N 83,5 E | China | 69,6 | 81,9 | 75,7 | M62858, 84,5 S 38,5 E, Floss a 13 km [Mons Mouton Plateau, Nobile Rim 1] |
| 5 | E18986 | 37,5 N 86,5 E | China / Xinjiang Uygur Zizhiqu | 60,3 | 89,5 | 74,9 | M63218, 85,5 S 38,5 E, Masina a 15 km [Mons Mouton Plateau, Nobile Rim 1] |
| 6 | E19346 | 36,5 N 86,5 E | China | 66,4 | 83,2 | 74,8 | M62859, 84,5 S 39,5 E, Floss a 11 km [Mons Mouton Plateau] |
| 7 | E19705 | 35,5 N 85,5 E | China | 66,0 | 83,1 | 74,6 | M62858, 84,5 S 38,5 E, Floss a 13 km [Mons Mouton Plateau, Nobile Rim 1] |
| 8 | E19698 | 35,5 N 78,5 E | China | 62,3 | 86,0 | 74,1 | M63218, 85,5 S 38,5 E, Masina a 15 km [Mons Mouton Plateau, Nobile Rim 1] |
| 9 | E41871 | 26,5 S 68,5 O | Argentina | 69,6 | 78,7 | 74,1 | M63218, 85,5 S 38,5 E, Masina a 15 km [Mons Mouton Plateau, Nobile Rim 1] |
| 10 | E19702 | 35,5 N 82,5 E | China | 64,4 | 83,3 | 73,9 | M63217, 85,5 S 37,5 E, Masina a 13 km [Mons Mouton Plateau, Nobile Rim 1] |

Como comparación, si el Rover se mandara a Tycho (opción E), el top 10 sería este (Spearman 0,543 con A1; 0/10 en común):

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final | gemela lunar (IAU más cercano) |
|---|---|---|---|---|---|---|---|
| 1 | E15768 | 46,5 N 108,5 E | Mongolia / Govi-Sumber | 100,0 | 99,2 | 99,6 | M51296, 52,5 S 3,5 O, Deluc a 77 km |
| 2 | E15033 | 48,5 N 93,5 E | Mongolia / Uvs | 100,0 | 99,1 | 99,5 | M50923, 51,5 S 16,5 O, Longomontanus a 119 km |
| 3 | E16131 | 45,5 N 111,5 E | Mongolia / East Gobi Aymag | 100,0 | 99,1 | 99,5 | M52001, 54,5 S 18,5 O, Clavius a 140 km |
| 4 | E15767 | 46,5 N 107,5 E | Mongolia / Middle Govi | 100,0 | 98,8 | 99,4 | M51296, 52,5 S 3,5 O, Deluc a 77 km |
| 5 | E15770 | 46,5 N 110,5 E | Mongolia / Hentiy | 100,0 | 98,7 | 99,4 | M50923, 51,5 S 16,5 O, Longomontanus a 119 km |
| 6 | E16126 | 45,5 N 106,5 E | Mongolia / Middle Govi | 100,0 | 98,7 | 99,4 | M51296, 52,5 S 3,5 O, Deluc a 77 km |
| 7 | E15771 | 46,5 N 111,5 E | Mongolia / Suhbaatar | 100,0 | 98,5 | 99,3 | M50923, 51,5 S 16,5 O, Longomontanus a 119 km |
| 8 | E16132 | 45,5 N 112,5 E | Mongolia / Suhbaatar | 100,0 | 98,3 | 99,2 | M52001, 54,5 S 18,5 O, Clavius a 140 km |
| 9 | E16431 | 44,5 N 51,5 E | Kazakhstan / Mangghystau | 100,0 | 98,3 | 99,1 | M46241, 38,5 S 18,5 O, Heinsius a 34 km |
| 10 | E16122 | 45,5 N 102,5 E | Mongolia / OEvoerhangay | 100,0 | 98,3 | 99,1 | M50921, 51,5 S 18,5 O, Longomontanus a 88 km |

### 7. Riesgo ante el jurado

- *"¿Cómo va a parecerse una celda con 0,9° de pendiente a una con 6,2°?"* Respuesta: la similitud compara posiciones relativas dentro de cada cuerpo, no valores. Ambas celdas son un poco más empinadas que la mediana de su cuerpo y de las más frías de su cuerpo. Por eso el panel enseña los valores absolutos de los dos puntos al lado de la similitud.
- *"¿Por qué el Rover va al polo sur y no a Tycho?"* Respuesta: porque las misiones Artemis van al polo sur; es la decisión del equipo (commit `ff6f1ae`).
- *"¿Por qué los mismos pesos para las tres misiones?"* Respuesta: los pesos por misión del equipo están escritos por dominios, no por variables. Al traducirlos, la temperatura pasa a pesar entre el 47 % y el 75 % y Base lunar acaba con dos tercios de los puntos en un único gemelo. Lo hemos medido y lo hemos descartado.

### 8. Qué se escribe en ASSUMPTIONS.md y qué se enseña en la web

**ASSUMPTIONS.md** (en inglés, como el resto del fichero), en §0.4:

> "Team lead decision (2026-11-15): `similarity_rule` is set to `zone_twin`. The twin of an Earth point is the single lunar cell of the mission's zone with the smallest weighted z-distance, with the repository's `DEFAULT_WEIGHTS` renormalised over elevation, slope, roughness and temperature (20.00 / 33.33 / 26.67 / 20.00 %), the same for the three missions. Zones: rover and solar, the south-pole zone (lat <= -75, 5,400 one-degree cells; analog_finder.py commit ff6f1ae moved the rover there from Tycho); lunar_base, the 280 one-degree cells touching NASA's nine Artemis candidate landing regions. Mission domain weights (A2, A3a) were evaluated and rejected: they make temperature 47-75 % of the similarity for solar and lunar_base and put 64-66 % of lunar_base points on one twin (docs/SIMILARITY_PROPOSAL.md §3, §4.1)."

**Web** (en inglés):

> "Each Earth point is paired with its lunar twin: the single 1-degree lunar cell, inside the mission's target zone, that holds the most similar relative position on the Moon as the Earth point holds on Earth (slope, roughness, relative elevation and surface temperature, each compared within its own world). A high similarity means 'same place in each world's range', not 'same values': both sets of values are shown side by side."

*Traducción:* "Cada punto de la Tierra se empareja con su gemelo lunar: la celda lunar de 1 grado, dentro de la zona objetivo de la misión, que ocupa en la Luna la posición relativa más parecida a la que el punto ocupa en la Tierra (pendiente, rugosidad, elevación relativa y temperatura de superficie, cada una comparada dentro de su propio mundo). Una similitud alta significa 'mismo lugar dentro del rango de cada mundo', no 'mismos valores': se enseñan los valores de los dos lados."

---

## Decisión 2. Quitar la variable de roca de la similitud

### 1. Qué pasa ahora

- En `analog_finder.py` la variable `rock_or_bare_frac` (fracción de suelo desnudo o roca) está en `DEFAULT_WEIGHTS` con 0,15 (línea 73) y entra en la similitud siempre que tenga algún valor en los dos cuerpos (línea 476).
- En la tabla lunar real vale **1 en las 64.800 celdas**. Es una definición, no una medida: `real_data/provenance_moon.csv` dice "1 for every cell: the team's variable means exposed (unvegetated) ground; the Moon has none".
- `normalize_planetary_features` (línea 162) no encuentra variación (rango intercuartílico 0, desviación típica 0), usa escala 1 y da a toda la Luna **z = (1 − 1)/1 = 0**. La variable sigue marcada como válida (línea 178) y conserva su peso: 16,67 % de la similitud cuando el radar falta.
- En la Tierra es la fracción de suelo desnudo o con vegetación escasa según ESA CCI Land Cover 2020 (clases 200-202 y 150-153). Es una clasificación de cubierta del suelo, no una medida de rocas.
- El motor ya la quita en las tablas reales: `engine/datasets.json`, `similarity_excluded` (líneas 487-489). La propuesta (A1) también. Por eso la web de hoy ya no tiene este sesgo: lo tiene `analog_finder.py` usado tal cual (A0). Lo que falta es que el equipo confirme que la retirada es definitiva.

### 2. El problema

**Cómo produce el sesgo, paso a paso.**

1. Fracción desnuda en las 25.095 celdas de tierra firme: **mediana 0,001**. El 41,2 % de las celdas tiene exactamente el mínimo (0). El 61,3 % tiene 0,01 o menos. Percentil 75: 0,123. Percentil 90: 0,751. Solo el 14,6 % llega a 0,5 o más (el 7,2 % a 0,9 o más).
2. Escala robusta en la Tierra: 0,0914. Eso da estas z:

| fracción desnuda en la Tierra | z en la Tierra | z de cualquier celda lunar | aporte a la distancia (peso 1/6 × diferencia²) |
|---|---|---|---|
| 0 (bosque o cultivo) | −0,01 | 0 | 0,00002 |
| 0,001 (la mediana) | 0,00 | 0 | 0 |
| 0,05 | +0,54 | 0 | 0,05 |
| 0,10 | +1,08 | 0 | 0,20 |
| 0,30 | +3,27 | 0 | 1,78 |
| 0,5 o más (desierto) | +4,00 (recortado) | 0 | 2,67 |

3. Como la Luna está en z = 0, la similitud premia a las celdas de la Tierra que están en la mediana terrestre, es decir, **con vegetación**. Una celda desértica (z = +4) no puede pasar de una similitud de **47,96** aunque las otras cuatro variables coincidan exactamente. El 17,4 % de la tierra firme está recortada en z = +4.
4. **Lo que no hace:** no cambia ningún gemelo. Como todas las celdas lunares tienen el mismo z = 0, el término de roca suma la misma cantidad a todos los candidatos y el más cercano sigue siendo el mismo. Cálculo de hoy: **0 gemelos cambian** en las tres misiones si se deja la roca. Lo que cambia es la similitud y, con ella, el ranking.

Similitud mediana de los puntos del Rover según su fracción desnuda (cálculo de hoy):

| fracción desnuda | puntos | similitud mediana con roca | sin roca (A1) |
|---|---|---|---|
| < 0,01 | 5.332 | 79,1 | 77,4 |
| 0,01-0,1 | 1.766 | 83,5 | 86,2 |
| 0,1-0,5 | 1.793 | 59,8 | 87,9 |
| ≥ 0,5 | 1.446 | 46,7 | 80,1 |

Con la roca dentro, el suelo más desnudo, que es el más lunar, es el que peor puntúa. Es lo contrario de lo que se busca.

### 3. Un ejemplo concreto

Desierto de Atacama, núcleo de Yungay, celda **E41150 (24,5 S 69,5 O, Chile)**: fracción desnuda 0,988, z = +4.

| misión | con roca: similitud / puesto | sin roca (A1): similitud / puesto | sin roca, reparto a partes iguales: similitud / puesto | gemelo (el mismo en los tres casos) |
|---|---|---|---|---|
| Rover | 45,1 / 7.822 de 10.337 | 71,3 / 2.529 | 70,8 / 2.572 | M60256, 77,5 S 43,5 O, Casatus a 176 km |
| Paneles solares | 45,1 / 15.418 de 18.777 | 71,3 / 3.535 | 70,8 / 3.568 | el mismo |
| Base lunar | 44,2 / 109 de 2.419 | 67,7 / 41 | 67,2 / 46 | M62486, 83,5 S 26,5 E, Mons Mouton a 36 km (región Mons Mouton Plateau) |

En el otro extremo, una pradera de Alberta (E12303, 55,5 N 116,5 O, fracción desnuda 0,0009) es el número 1 del Rover con `analog_finder` tal cual (A0, Luna media con roca). En la web de hoy (E0, ya sin roca) Atacama tiene similitud 50,8 y puesto 4.871 en el Rover.

### 4. Las opciones

**Mantener o quitar:**

| opción | a favor | en contra |
|---|---|---|
| **Quitarla (decidido, falta confirmar)** | Elimina un sesgo hacia la vegetación demostrado con números. Los gemelos no cambian. | La similitud tiene una variable menos: no queda ninguna de material. |
| Mantenerla | Ninguno defendible. | Castiga los desiertos. El top 10 del Rover con roca son celdas de la capa de hielo de Groenlandia con fracción desnuda 0-0,006 (hielo permanente, clase CCI 220, que no cuenta como desnudo). |
| Sustituirla por la abundancia de rocas de Diviner (`rock_abundance_frac`) | Es una medida real de rocas en la Luna. | Es otra magnitud y solo cubre de 60 S a 60 N: no hay dato en ninguna de las dos zonas objetivo (propuesta, §2.2). |

**Cómo repartir su 0,15:**

| reparto | pendiente | rugosidad | elevación relativa | temperatura | gemelos que cambian frente al proporcional (Rover / Paneles / Base) | top 10 compartido |
|---|---|---|---|---|---|---|
| **Proporcional (el del motor y A1)** | 33,33 % | 26,67 % | 20,00 % | 20,00 % | referencia | referencia |
| A partes iguales (0,0375 a cada una) | 31,94 % | 26,39 % | 20,83 % | 20,83 % | 327 / 422 / 81 (3,2 % / 2,2 % / 3,3 %) | 10/10, 9/10, 10/10 |
| Todo al relieve (proporcional entre pendiente, rugosidad y elevación) | 34,72 % | 27,78 % | 20,83 % | 16,67 % | 1.194 / 1.607 / 314 | 9/10, 8/10, 9/10 |

Recuerda que en las tablas reales tampoco hay radar: su 0,10 también se reparte, en proporción, en los tres casos.

### 5. Recomendación y por qué

**La retirada es definitiva; el reparto, proporcional.** Mantenerla castiga justo el terreno que más se parece a la Luna. El reparto proporcional es el que ya usan el motor y la propuesta, conserva el orden de los pesos del equipo y difiere del reparto a partes iguales en el 2,2-3,3 % de los gemelos, sin tocar el top 10 del Rover ni el de Base lunar. **Sí se sigue enseñando como dato informativo:** el motor la exporta fuera de la similitud: en el resumen lunar marcada `"part_of_similarity": False` (`engine/export_v2.py`, `lunar_info_summary`, líneas 573-585 del fichero de trabajo de hoy, que otros agentes están editando) y, para cada gemelo, en `not_part_of_similarity` de `twins.json` (líneas 614-619). `datasets.json` la declara excluida en `similarity_excluded` (líneas 487-489). En la Luna ese dato vale siempre 1. Lo que no he podido confirmar es que el panel de la web la pinte: en `app/src` no encuentro ninguna referencia a la variable. Hay que comprobarlo en la web.

### 6. Qué cambia en los resultados si se acepta

Frente a "dejarla dentro": **0 gemelos cambian** en las tres misiones. Lo que cambia es el orden. Spearman del final con roca frente a sin roca: Rover 0,362, Paneles 0,666, Base lunar 0,550. Top 10 en común: Rover 0/10, Paneles 8/10, Base lunar 0/10. El "después" son los top 10 A1 de la decisión 1. El "antes" (con roca) es este:

**Rover con roca** (fracción desnuda del top 10: 0-0,006; sin roca: 0,72-1,00):

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final | gemela lunar (IAU más cercano) |
|---|---|---|---|---|---|---|---|
| 1 | E4474 | 77,5 N 25,5 O | Greenland | 75,1 | 99,1 | 87,1 | M60586, 78,5 S 73,5 O, Drygalski a 85 km |
| 2 | E3362 | 80,5 N 57,5 O | Greenland | 75,0 | 99,0 | 87,0 | M60275, 77,5 S 24,5 O, Newton a 56 km |
| 3 | E4111 | 78,5 N 28,5 O | Greenland | 75,0 | 98,5 | 86,7 | M59861, 76,5 S 78,5 O, Le Gentil a 70 km |
| 4 | E9137 | 64,5 N 42,5 O | Greenland | 75,0 | 98,4 | 86,7 | M60295, 77,5 S 4,5 O, Short a 93 km |
| 5 | E4803 | 76,5 N 56,5 O | Greenland | 75,0 | 98,3 | 86,7 | M61054, 79,5 S 34,5 E, Schomberger a 106 km |
| 6 | E7332 | 69,5 N 47,5 O | Greenland | 75,0 | 98,2 | 86,6 | M61054, 79,5 S 34,5 E, Schomberger a 106 km |
| 7 | E5163 | 75,5 N 56,5 O | Greenland | 75,0 | 98,2 | 86,6 | M60384, 77,5 S 84,5 E, Hale a 115 km |
| 8 | E3017 | 81,5 N 42,5 O | Greenland | 75,0 | 97,9 | 86,4 | M60690, 78,5 S 30,5 E, Schomberger a 68 km |
| 9 | E4075 | 78,5 N 64,5 O | Greenland | 75,0 | 97,9 | 86,4 | M59861, 76,5 S 78,5 O, Le Gentil a 70 km |
| 10 | E9496 | 63,5 N 43,5 O | Greenland | 74,8 | 97,8 | 86,3 | M60260, 77,5 S 39,5 O, Newton a 152 km |

**Paneles solares con roca:**

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final | gemela lunar (IAU más cercano) |
|---|---|---|---|---|---|---|---|
| 1 | E40517 | 22,5 S 17,5 E | Namibia / Khomas | 93,3 | 73,6 | 83,4 | M60006, 76,5 S 66,5 E, Demonax a 68 km |
| 2 | E37308 | 13,5 S 48,5 E | Madagascar / Diana | 92,1 | 74,7 | 83,4 | M59478, 75,5 S 101,5 O, Boltzmann a 88 km |
| 3 | E42682 | 28,5 S 22,5 E | South Africa / Northern Cape | 93,0 | 73,6 | 83,3 | M59636, 75,5 S 56,5 E, Demonax a 81 km |
| 4 | E27615 | 13,5 N 75,5 E | India / Karnataka | 90,9 | 75,6 | 83,3 | M59479, 75,5 S 100,5 O, Boltzmann a 81 km |
| 5 | E42323 | 27,5 S 23,5 E | South Africa / Northern Cape | 92,9 | 73,5 | 83,2 | M59539, 75,5 S 40,5 O, Casatus a 117 km |
| 6 | E38385 | 16,5 S 45,5 E | Madagascar / Melaky | 96,5 | 69,9 | 83,2 | M59736, 75,5 S 156,5 E, Schrodinger a 184 km |
| 7 | E42683 | 28,5 S 23,5 E | South Africa / Northern Cape | 92,4 | 74,0 | 83,2 | M59539, 75,5 S 40,5 O, Casatus a 117 km |
| 8 | E41606 | 25,5 S 26,5 E | South Africa / North-West | 91,6 | 74,7 | 83,1 | M59636, 75,5 S 56,5 E, Demonax a 81 km |
| 9 | E27814 | 12,5 N 85,5 O | Nicaragua / Boaco | 91,2 | 75,1 | 83,1 | M59479, 75,5 S 100,5 O, Boltzmann a 81 km |
| 10 | E42322 | 27,5 S 22,5 E | South Africa / Northern Cape | 93,6 | 72,6 | 83,1 | M59636, 75,5 S 56,5 E, Demonax a 81 km |

**Base lunar con roca** (fracción desnuda del top 10: 0,003-0,024; sin roca: 0,50-0,93):

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final | gemela lunar (IAU más cercano) |
|---|---|---|---|---|---|---|---|
| 1 | E18639 | 38,5 N 99,5 E | China / Qinghai Sheng | 42,0 | 90,4 | 66,2 | M63218, 85,5 S 38,5 E, Masina a 15 km [Mons Mouton Plateau, Nobile Rim 1] |
| 2 | E21509 | 30,5 N 89,5 E | China / Tibet Autonomous Region | 49,5 | 81,2 | 65,3 | M63217, 85,5 S 37,5 E, Masina a 13 km [Mons Mouton Plateau, Nobile Rim 1] |
| 3 | E20432 | 33,5 N 92,5 E | China | 47,9 | 82,2 | 65,1 | M62859, 84,5 S 39,5 E, Floss a 11 km [Mons Mouton Plateau] |
| 4 | E20433 | 33,5 N 93,5 E | China | 49,0 | 80,4 | 64,7 | M62858, 84,5 S 38,5 E, Floss a 13 km [Mons Mouton Plateau, Nobile Rim 1] |
| 5 | E20072 | 34,5 N 92,5 E | China | 48,1 | 81,2 | 64,6 | M62858, 84,5 S 38,5 E, Floss a 13 km [Mons Mouton Plateau, Nobile Rim 1] |
| 6 | E22231 | 28,5 N 91,5 E | China / Tibet Autonomous Region | 44,0 | 85,2 | 64,6 | M63218, 85,5 S 38,5 E, Masina a 15 km [Mons Mouton Plateau, Nobile Rim 1] |
| 7 | E21151 | 31,5 N 91,5 E | China / Tibet Autonomous Region | 48,2 | 81,0 | 64,6 | M62859, 84,5 S 39,5 E, Floss a 11 km [Mons Mouton Plateau] |
| 8 | E20791 | 32,5 N 91,5 E | China / Tibet Autonomous Region | 48,4 | 80,4 | 64,4 | M62858, 84,5 S 38,5 E, Floss a 13 km [Mons Mouton Plateau, Nobile Rim 1] |
| 9 | E20076 | 34,5 N 96,5 E | China / Qinghai Sheng | 44,9 | 83,9 | 64,4 | M62859, 84,5 S 39,5 E, Floss a 11 km [Mons Mouton Plateau] |
| 10 | E20075 | 34,5 N 95,5 E | China / Qinghai Sheng | 47,8 | 80,8 | 64,3 | M63217, 85,5 S 37,5 E, Masina a 13 km [Mons Mouton Plateau, Nobile Rim 1] |

### 7. Riesgo ante el jurado

- *"¿Por qué no usáis la composición del suelo?"* Respuesta: en la Luna no tenemos una variable de material comparable con la de la Tierra. La que había era 1 en toda la Luna por definición y, normalizada, premiaba la vegetación. La quitamos y la seguimos enseñando como dato.
- *"Entonces vuestra similitud es solo relieve y temperatura."* Correcto, y lo decimos.

### 8. Qué se escribe en ASSUMPTIONS.md y qué se enseña en la web

**ASSUMPTIONS.md**, en §0.3, al final del párrafo "The rock variable on the real tables":

> "Confirmed by the team lead on 2026-11-15 as final. With the variable kept, every lunar cell has z = 0 and an Earth cell with bare fraction >= 0.5 gets z = +4, so no desert cell could exceed a similarity of 47.96; the twins would not change (the term is the same for every lunar candidate), only the ranking. The weight is redistributed in proportion (an equal split changes 2.2-3.3 % of twins and no rover or lunar_base top-10 cell)."

**Web:**

> "Bare-ground fraction is shown for information only. It is not part of the similarity: on the Moon it is 1 everywhere by definition, so it cannot tell lunar places apart."

*Traducción:* "La fracción de suelo desnudo se muestra solo como información. No forma parte de la similitud: en la Luna vale 1 en todas partes por definición, así que no distingue unos lugares lunares de otros."

---

## Decisión 3. Celdas antárticas sin temperatura

### 1. Qué pasa ahora

**Por qué no tienen temperatura.** La temperatura de la Tierra (`temp_k`) es la temperatura media anual de la **superficie terrestre** con cielo despejado (media de día y noche) de la climatología MODIS de OpenLandMap (Hengl 2018, doi:10.5281/zenodo.1420115, derivada de MOD11A2 v006, 2000-2017, 1 km). Según `real_data/provenance_earth.csv`, cubre de **87,37 N a unos 62 S: no incluye la Antártida**.

**Qué hace el código con el hueco.** Hay dos comportamientos distintos en el repositorio:

- `analog_finder.py`, línea 166: `z = np.where(np.isfinite(vals), (vals - med) / scale, 0.0)`. Un valor que falta recibe z = 0, es decir, **la mediana de la Tierra: 284,27 K** (unos 11 °C; escala 21,49 K). La propuesta calculó sus cifras así.
- El motor (`engine/repo_similarity.py`, docstring de las líneas 31-36 y función `sq_distance`, líneas 153-175) ya hace otra cosa: si falta un valor, quita esa variable de la distancia de ese par y renormaliza el resto ("ignorar y renormalizar"). Comprobación cruzada: con este tratamiento salen hoy 744 gemelos distintos en el Rover (el más compartido, 895 puntos) y 721 en Paneles (3.047). Son exactamente las cifras de la vista previa `zone_twin` del motor en `ASSUMPTIONS.md` §0.7. No he ejecutado el motor; la coincidencia sale de comparar mis resultados con esas cifras.

**Cuántas celdas son.** De las 25.095 celdas de tierra firme, **6.578** no tienen temperatura. 6.558 están al sur de 60 S. De las 6.565 celdas de tierra al sur de 60 S, solo 7 tienen dato. Las otras 20 son tiras costeras o islotes con menos del 2 % de tierra, que no pasan la puerta `mask_fraction >= 0,3` (propuesta, §2.2).

**Puntos clasificados afectados, por misión:**

| misión | puntos clasificados | sin temperatura | % |
|---|---|---|---|
| Rover | 10.337 | 1.156 (todos al sur de 60 S) | 11,2 % |
| Paneles solares | 18.777 | 6.060 (todos al sur de 60 S) | 32,3 % |
| Base lunar | 2.419 | 0 | 0 % |

**Por qué Base lunar no se ve afectada:** su bloque (copia de `thermal`) exige `lst_diurnal_amp_k` (`require_present`), la amplitud térmica diaria. Sale del mismo producto MODIS, así que tampoco existe en la Antártida. El 99,9 % de las celdas antárticas de tierra falla con "lst_diurnal_amp_k sin dato" y ninguna pasa.

### 2. El problema

Con z = 0, una celda del interior antártico se compara con la Luna como si estuviera a 284 K, una temperatura templada. En el Rover, los 1.156 puntos afectados reciben una similitud de 72,3 a 83,8 (mediana 78,3) y gemelos elegidos para una temperatura falsa.

**Cuántas están hoy en un top 10: ninguna.** Ninguna de estas celdas está en el top 10, ni en el top 100, de ninguna misión, ni con la regla de hoy en el motor (E0; la mejor está en el puesto 542 del Rover) ni con A1. Solo con `analog_finder` tal cual (A0, z = 0 y con roca) entrarían 14 en el top 100 del Rover (la mejor, puesto 73), ninguna en el top 10. El daño está en los paneles de esos puntos (su gemelo y su similitud), no en lo que se ve primero.

### 3. Un ejemplo concreto

Estación Concordia (Dome C), celda **E59703 (75,5 S 123,5 E, Antártida)**, Paneles solares, idoneidad 55,7. Valores: elevación relativa +2.544 m, pendiente 0,04°, rugosidad 1,1 m, sin temperatura.

| tratamiento | z de la temperatura | similitud | puesto (de 18.777) | gemelo |
|---|---|---|---|---|
| z = 0 (como `analog_finder`; cifras de la propuesta) | 0 (= 284,3 K) | 74,9 | 14.587 | M59522, 75,5 S 57,5 O, Le Gentil a 150 km (158,9 K) |
| Ignorar y renormalizar (como el motor) | no se usa | 90,2 | 14.949 | M62845, 84,5 S 25,5 E, Mons Mouton a 16 km, región Mons Mouton Plateau (129,3 K) |
| Excluir la celda | — | — | fuera del ranking | — |
| Otra fuente: NASA POWER, temperatura de piel anual en Dome C (solo este punto) | −3,10 (217,7 K) | 81,5 | no calculado (habría que rellenar las 6.558 celdas) | M62850, 84,5 S 30,5 E, Mons Mouton a 3 km (124,7 K) |

El puesto baja aunque la similitud suba, porque los otros 6.059 puntos antárticos también suben.

### 4. Las opciones

**"Ignorar y renormalizar"** significa: en esas celdas la distancia se calcula solo con pendiente, rugosidad y elevación relativa, y sus pesos se reescalan para que sumen 1: **pendiente 41,67 %, rugosidad 33,33 %, elevación relativa 25,00 %**. Es lo mismo que hace `mission_scoring.apply_soft` (`tierra luna/mission_scoring.py`, líneas 117-134) cuando falta un criterio de la idoneidad: suma peso × utilidad solo de las variables con dato (líneas 131-132) y divide entre el peso con dato (línea 134).

| opción | qué pasa (cálculo de hoy) | a favor | en contra |
|---|---|---|---|
| Dejar z = 0 | Lo de la propuesta. | Es la fórmula literal del repositorio. | Trata la Antártida como templada. No se puede defender. |
| **Ignorar y renormalizar** | Cambian de gemelo 1.123 de los 1.156 puntos del Rover y 6.023 de los 6.060 de Paneles. Su similitud mediana sube de 78,3 a 98,0 (Rover) y de 77,1 a 96,1 (Paneles). El mejor puesto pasa de 4.222 a 888 (Rover) y de 12.459 a 3.881 (Paneles). Top 10 igual (10/10); ninguno entra en el top 100. Spearman del final con z = 0: 0,908 (Rover), 0,784 (Paneles). Gemelos distintos: 305 → 744 (Rover) y 186 → 721 (Paneles). | Mismo trato que la idoneidad. Ya está en el motor: cero trabajo. No inventa ningún valor. | Con tres variables es más fácil parecerse: su similitud sale **inflada** (mediana 98,0, frente a 80,1 de los puntos del Rover que sí tienen temperatura; en Paneles 96,1 frente a 74,8). Hay que marcarlo. |
| Excluir esas celdas | Quedan 9.181 puntos en el Rover y 12.717 en Paneles. Top 10 igual. | Sencillo y honesto. | Quita la Antártida, que es el análogo polar más evidente, y el 32,3 % de los puntos de Paneles. Concordia desaparece. |
| Otra fuente de temperatura | Ver abajo. Solo probada en 5 puntos. | Rellenaría el hueco con un dato real. | Es otra magnitud. Unas 6.558 consultas. No cabe antes de la entrega. |
| Marcarlas en la web | Se combina con cualquiera de las anteriores. | Transparente. | Por sí sola no arregla el número. |

**Otra fuente sin cuenta: NASA POWER.** Lo he comprobado hoy.

- API de climatología por punto, sin clave: `https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=TS&community=RE&longitude=123.35&latitude=-75.10&format=JSON`
- Variable `TS`, "Earth Skin Temperature", en °C. Fuente MERRA-2. Climatología 2001-2025 (lo dice la cabecera de la respuesta, versión de la API v2.10.1). Resolución: la nativa de MERRA-2, 0,5° × 0,625° (la cabecera dice "Source Native Resolution"; la cifra no la he podido leer en la documentación de POWER, que solo se carga con JavaScript). Licencia: datos de NASA; no he encontrado el texto de la licencia en una página legible sin JavaScript, así que está sin confirmar.
- En Dome C devuelve −55,45 °C (217,7 K). La temperatura del aire a 2 m (`T2M`) en el mismo punto: −51,18 °C.
- **No es la misma magnitud** que la que usamos en el resto del mundo. Nuestra temperatura es la de superficie medida por satélite MODIS con cielo despejado. `TS` es la temperatura de piel de un reanálisis (un modelo), con todo tipo de cielo. Comparadas en tres celdas que tienen las dos:

| celda | NASA POWER TS | nuestra temperatura | diferencia |
|---|---|---|---|
| 75,5 N 91,5 O (Ártico canadiense) | 258,7 K | 253,5 K | +5,2 K |
| 24,5 S 69,5 O (Atacama) | 288,9 K | 296,0 K | −7,1 K |
| 62,5 N 129,5 E (Yakutia) | 263,6 K | 262,3 K | +1,3 K |

  Tres puntos no son una calibración. Mezclar las dos fuentes metería un sesgo de varios kelvin solo en la Antártida.
- Con cuenta: MODIS MOD11C3 o MOD11A2 (LP DAAC; la descarga pide una cuenta Earthdata Login) cubre la Antártida y sí es la misma magnitud. ERA5 (temperatura de piel, Copernicus Climate Data Store) pide una cuenta CDS. No los he descargado hoy. Comprobado para MOD11C3 v061: el enlace de descarga de un fichero (LP DAAC, `lp-prod-protected`) redirige a `urs.earthdata.nasa.gov`, el inicio de sesión de Earthdata. Lo de ERA5 no está comprobado.

### 5. Recomendación y por qué

**Ignorar la variable en esas celdas y renormalizar** (lo del director), **y marcar esos puntos en la web.** Es el mismo trato que da `mission_scoring` a un dato que falta, no inventa nada, ya está en el motor y no mueve ningún top 10. Mis números añaden un matiz: con tres variables la similitud de esos puntos sale más alta (en el Rover, mediana 98,0 frente a 80,1 de los puntos con temperatura), así que la marca en el panel no es opcional.

### 6. Qué cambia en los resultados si se acepta

Frente a las cifras de la propuesta (z = 0): cambian de gemelo **1.123 pares del Rover y 6.023 de Paneles**; Base lunar, 0. **El top 10 de las tres misiones no cambia** (10/10 en común) y ningún punto antártico entra en el top 100. Las cifras de reparto de gemelos de la propuesta pasan a ser: Rover 744 gemelos distintos (el mayor, M59479 Boltzmann, 895 puntos, 8,7 %; la mitad de los puntos en 12 gemelos); Paneles 721 (M59734 Schrödinger, 3.047, 16,2 %; la mitad en 7). Estas son las cifras que hay que citar, porque son las del motor.

### 7. Riesgo ante el jurado

- *"¿Qué temperatura usáis en la Antártida?"* Respuesta: ninguna; el producto de satélite que usamos no la cubre. En esos puntos el gemelo se elige solo por relieve, y el panel lo dice.
- *"Entonces esos pares se parecen demasiado."* Sí: con una variable menos es más fácil parecerse. Por eso los marcamos, y ninguno está entre los 100 primeros.

### 8. Qué se escribe en ASSUMPTIONS.md y qué se enseña en la web

**ASSUMPTIONS.md**, en §0.3, a continuación de "One departure..." (o como punto nuevo):

> "Earth temp_k is missing on 6,578 of the 25,095 land cells (6,558 south of 60 S: the OpenLandMap MODIS LST climatology stops at about 62 S). Team lead decision (2026-11-15): for those cells temperature is left out of the distance and the remaining weights are renormalised (slope 41.67 %, roughness 33.33 %, relative elevation 25.00 %), the same rule mission_scoring.apply_soft applies to a missing soft criterion; the repository's analog_finder would set z = 0 (the Earth median, 284.27 K). It affects 1,156 rover and 6,060 solar ranked points and no lunar_base point (its required diurnal amplitude is also missing there); none is in any top 100. Their similarity is computed on three variables and is therefore higher (rover median 98.0 against 80.1 for rover points with temperature); the app marks them. NASA POWER skin temperature (MERRA-2, keyless) covers Antarctica but is a different quantity (all-sky reanalysis skin temperature, not clear-sky MODIS LST) and was not used."

**Web**, en el panel de esos puntos:

> "No surface temperature here: the satellite climatology we use does not cover Antarctica. This twin was chosen on relief only (slope, roughness, relative elevation), so its similarity is not comparable with points that include temperature."

*Traducción:* "Aquí no hay temperatura de superficie: la climatología de satélite que usamos no cubre la Antártida. Este gemelo se ha elegido solo por el relieve (pendiente, rugosidad, elevación relativa), así que su similitud no es comparable con la de los puntos que incluyen temperatura."

---

## Decisión 4. Concentración de gemelos en Base lunar

### 1. Qué pasa ahora

La regla da a cada punto su gemelo más cercano, sin límite de cuántos puntos pueden compartir uno (`engine/repo_similarity.py`, `best_twins`, líneas 185-210; propuesta, regla A1). En Base lunar hay 2.419 puntos y 280 celdas candidatas, pero solo se usan 48. **Tres celdas se llevan el 54,1 % de los puntos (1.308):**

| celda lunar | lat, lon | nombre IAU más cercano | región NASA | puntos | % |
|---|---|---|---|---|---|
| M62515 | 83,5 S 55,5 E | Wapowski, a 14 km | Nobile Rim 2 | 671 | 27,7 % |
| M63665 | 86,5 S 125,5 E | Slater, a 52 km | Slater Plain | 332 | 13,7 % |
| M64191 | 88,5 S 68,5 O | de Gerlache, a 16 km | de Gerlache Rim 2 | 305 | 12,6 % |

### 2. El problema

**Por qué pasa.** No es solo que la zona sea pequeña, y no es una celda pegada al borde del rango en todas las variables. Es una combinación de dos cosas:

1. **Los puntos de la Tierra están fuera de la zona en temperatura.** El 99,96 % de los puntos de Base lunar tiene un z de temperatura mayor que la celda más cálida de la zona (z máximo de la zona −0,94; mediana de los puntos de la Tierra +0,21). La temperatura empuja a todos en la misma dirección: hacia las celdas menos frías.
2. **La zona es abrupta y la Tierra no.** Medianas de z en las 280 celdas: pendiente +1,43, rugosidad +1,11. Medianas de los puntos de la Tierra: +0,43 y +0,42. Muy pocas celdas de la zona tienen un relieve "normal" y además no son de las más frías. Esas pocas ganan siempre.

Valores y posición de las tres celdas dentro de la zona (percentil 100 = el valor más alto de las 280):

| celda | elevación relativa | pendiente | rugosidad | temperatura | z (elev / pend / rug / temp) | percentil en la zona (elev / pend / rug / temp) |
|---|---|---|---|---|---|---|
| M62515 Wapowski | +849 m | 5,1° | 124 m | 138,1 K | +0,78 / +0,04 / −0,39 / −1,84 | 50 / 17 / 7 / 73 |
| M63665 Slater | −1.302 m | 5,8° | 155 m | 134,6 K | −0,44 / +0,28 / −0,05 / −1,96 | 10 / 23 / 16 / 64 |
| M64191 de Gerlache | +1.047 m | 9,8° | 279 m | 155,2 K | +0,89 / +1,51 / +1,29 / −1,32 | 54 / 52 / 54 / 95 |

M62515 es de las celdas más suaves de la zona (rugosidad en el percentil 7) con una altura media y una temperatura de las menos frías: es el mejor compromiso para un punto de la Tierra "normal". En Rover y Paneles sí hay una celda en el borde: M59479 (Boltzmann, 75,5 S 100,5 O) es **la celda más cálida** de toda la zona del polo sur (z −0,79 = máximo de la zona), y el 73,3 % de los puntos del Rover y el 88,3 % de los de Paneles que tienen temperatura son más cálidos que ella (76,3 % y 92,1 % si se cuentan los antárticos con z = 0, que no son un dato real).

**¿Pasa también en Rover y Paneles?** Sí, en menor medida (regla A1 con z = 0; propuesta §3 y cálculo de hoy):

| misión | puntos | gemelos distintos | % del primero | de los 3 primeros | de los 10 primeros | gemelos que reúnen la mitad |
|---|---|---|---|---|---|---|
| Rover | 10.337 | 305 | 9,2 % | 24,1 % | 52,4 % | 10 |
| Paneles solares | 18.777 | 186 | 16,8 % | 37,8 % | 67,9 % | 6 |
| Base lunar | 2.419 | 48 | 27,7 % | 54,1 % | 76,5 % | 3 |
| Rover, como el motor (decisión 3) | 10.337 | 744 | 8,7 % | 22,4 % | 47,0 % | 12 |
| Paneles, como el motor | 18.777 | 721 | 16,2 % | 34,5 % | 57,2 % | 7 |

### 3. Un ejemplo concreto

Atacama, núcleo de Yungay (E41150, 24,5 S 69,5 O), Base lunar, idoneidad 73,7. Sus tres gemelos más parecidos:

| orden | celda | lugar | región NASA | similitud |
|---|---|---|---|---|
| 1 | M62486 | 83,5 S 26,5 E, Mons Mouton a 36 km | Mons Mouton Plateau | 67,7 |
| 2 | M62488 | 83,5 S 28,5 E, Mons Mouton a 34 km | Mons Mouton Plateau | 67,0 |
| 3 | M64189 | 88,5 S 70,5 O, de Gerlache a 14 km | de Gerlache Rim 2 | 67,0 |

Para el número 1 de Base lunar (E19345, 36,5 N 85,5 E, Xinjiang): Floss 83,8, Floss (la celda vecina) 77,8, Masina 76,0, todas en Mons Mouton Plateau.

### 4. Las opciones

| opción | qué produce (cálculo de hoy, Base lunar) | a favor | en contra |
|---|---|---|---|
| **Aceptarlo y enseñar cuántos puntos comparten cada gemelo** | Nada cambia. | Honesto. El motor ya exporta los puntos de cada gemelo (`twins.json`, `ASSUMPTIONS.md` §0.4). | El usuario ve el mismo gemelo muchas veces. |
| Límite del 5 % por gemelo (121 puntos) | Reasignados 1.021 puntos (42,2 %). Pierden una mediana de 1,26 puntos de similitud (máximo 2,68). 55 gemelos; la mitad de los puntos en 11. Top 10 igual. | Reparte. | El gemelo deja de ser "el más parecido" para el 42 % de los puntos, y el resultado depende del orden de asignación. Hay que explicar una regla artificial. |
| Límite del 10 % (242 puntos) | Reasignados 624 (25,8 %). Pérdida mediana 1,00 (máximo 2,35). 52 gemelos; la mitad en 6. Top 10 igual. | Menos intrusivo. | Mismos problemas, algo menores. |
| Enseñar los tres gemelos más parecidos | El 2.º está a una mediana de 0,78 puntos de similitud del 1.º y el 3.º a 1,27 (percentil 90: 3,75). El 2.º está a una mediana de 13,7 km del 1.º (el 58,5 % a 45 km o menos) y el 3.º a 33,0 km. Entre los tres primeros de todos los puntos aparecen 75 celdas distintas. | Muestra que el gemelo no es único. | En Base lunar el 2.º y el 3.º suelen ser la celda de al lado: aportan poco. Más trabajo en la web. |

En Rover y Paneles los tres primeros están más separados: el 2.º, a una mediana de 250 km (Rover) y 121 km (Paneles) del 1.º; el 3.º, a 344 y 431 km. Las diferencias de similitud son parecidas: 0,63 y 1,18 (Rover), 0,60 y 1,14 (Paneles).

### 5. Recomendación y por qué

**Aceptarlo y enseñar cuántos puntos comparten cada gemelo** (lo del director). Un límite cambia el gemelo de entre el 26 % y el 42 % de los puntos para ganar poco (no toca el top 10) y añade una regla difícil de defender. Los tres gemelos de Base lunar suelen ser celdas vecinas, así que enseñarlos no cambia el mensaje. La concentración es una consecuencia real de comparar la Tierra con una zona pequeña, fría y abrupta, y se puede contar tal cual.

### 6. Qué cambia en los resultados si se acepta

Nada: 0 gemelos cambian y los tres top 10 son los de la decisión 1. Solo se añade el recuento en el panel.

### 7. Riesgo ante el jurado

- *"¿Por qué 671 puntos de la Tierra tienen el mismo gemelo?"* Respuesta: porque la zona de Base lunar son 280 celdas de un terreno muy abrupto y frío; casi todos los puntos de la Tierra son más cálidos que cualquiera de ellas, y la celda cerca de Wapowski (Nobile Rim 2) es de las pocas suaves y de las menos frías. Lo enseñamos con su recuento.
- *"¿No es el gemelo arbitrario?"* La segunda opción suele estar a menos de un punto de similitud y a unos 14 km: el mensaje ("tu sitio se parece a esta zona de Mons Mouton / Nobile") no depende de esa elección.

### 8. Qué se escribe en ASSUMPTIONS.md y qué se enseña en la web

**ASSUMPTIONS.md**, en §0.7:

> "Twin concentration is accepted (team lead decision, 2026-11-15) and shown in the app. lunar_base: 48 of the 280 zone cells are used; three hold 54.1 % of the 2,419 points (M62515 near Wapowski, Nobile Rim 2, 27.7 %; M63665 near Slater, Slater Plain, 13.7 %; M64191 near de Gerlache, de Gerlache Rim 2, 12.6 %). Cause: 99.96 % of the Earth points are warmer than the warmest zone cell, and the zone is rugged (median slope z +1.43 against +0.43 on Earth), so the few gentle, least-cold cells win. A cap of 5 % per twin would reassign 1,021 points for a median loss of 1.26 similarity points and change no top-10 cell; it was rejected."

**Web**, junto al gemelo:

> "This lunar twin is shared by N Earth points (X % of the ranked points for this mission). The lunar base zone is small (280 cells), cold and rugged, so a few gentle cells are the best match for most places on Earth."

*Traducción:* "Este gemelo lunar lo comparten N puntos de la Tierra (X % de los puntos clasificados de esta misión). La zona de la base lunar es pequeña (280 celdas), fría y abrupta, así que unas pocas celdas suaves son la mejor coincidencia para la mayoría de los lugares de la Tierra."

---

## Decisión 5. Paneles solares frente al polo sur

**[SUSTITUIDO el 15-11-2026** por "Decisiones tomadas (15-11-2026, mañana)", puntos 4 y 6: Paneles solares ya no están en el polo sur sino en los mares ecuatoriales, el gemelo se elige por la luz sobre la atmósfera y el texto de limitación de esta decisión se ha retirado. Se conserva como historia.]

### 1. Qué pasa ahora

- **La idoneidad** (`mission_scoring.json`, bloque `solar`) premia el sol: irradiancia (35 %, de 2,5 a 6 kWh/m²/día), Sol alto (15 %), poco tiempo de Sol rasante (15 %), poca pendiente (15 %), poca amplitud térmica (10 %) y poca rugosidad (10 %). Filtros duros: irradiancia ≥ 2,5, pendiente ≤ 15°, altura máxima del Sol ≥ 10°, Sol rasante ≤ 25 % del día, no sobre agua.
- **La similitud** compara el punto con la zona lunar del polo sur (latitud ≤ 75 S) usando solo relieve y temperatura. **No hay ninguna variable de iluminación en la similitud.**
- El gemelo, por tanto, se elige por relieve y temperatura. Y la zona del polo sur es la parte más fría de la Luna.

### 2. El problema

**Por qué la correlación es −0,68** (Spearman entre similitud e idoneidad de los 18.777 puntos; cálculo de hoy: −0,681). Correlación de cada variable de la Tierra con una y con otra:

| variable de la Tierra | con la idoneidad | con la similitud |
|---|---|---|
| temperatura | +0,929 | **−0,980** |
| irradiancia | +0,874 | −0,812 |
| latitud (en valor absoluto) | −0,857 | +0,537 |
| elevación relativa | −0,390 | +0,046 |
| pendiente | +0,019 | +0,240 |
| rugosidad | +0,078 | +0,209 |

La idoneidad sube con el calor y el sol. La similitud baja con el calor, porque los gemelos son celdas polares frías. Por tercios de idoneidad: temperatura mediana 263,3 / 278,7 / 298,2 K; similitud mediana 77,7 / 79,9 / 68,9. Los mejores sitios para paneles son los que peor se parecen a su gemelo. En el top 10 la diferencia de temperatura con el gemelo es de 120-135 K (propuesta, §3.2); la mediana de todos los pares, 126,3 K.

**¿Hay variables de iluminación lunar en nuestros datos?** Sí, en la tabla lunar real, pero ninguna tiene una pareja medida en la Tierra:

| variable | qué es | nivel | cobertura | en la zona del polo sur (5.400 celdas) |
|---|---|---|---|---|
| `illum_frac` | fracción media del tiempo en que el Sol ilumina el suelo, de los mapas de iluminación de LOLA (Mazarico et al. 2011, AVGVISIB, 240 m), promediada sobre la celda | DERIVED_LOLA_TOPOGRAPHY desde 65° hacia el polo (18.000 celdas); en el resto, DERIVED_FLAT_GEOMETRY (geometría con horizonte plano, 46.800 celdas) | 64.800 celdas | mediana 0,315; percentil 90: 0,409; máximo 0,474. El promedio por celda diluye los picos casi siempre iluminados |
| `irradiance_kwh_m2_day` | energía solar diaria sobre superficie horizontal (constante solar 1.361 W/m² × geometría; con `illum_frac` de LOLA donde existe) | DERIVED | 64.800 | mediana 0,84; máximo 2,475. **Ninguna celda del polo sur llega al filtro solar de 2,5** |
| `sun_elev_max_deg` | altura máxima del Sol, fórmula de la latitud con horizonte plano | DERIVED | 64.800 | solo 15 valores distintos (2,04-16,04°): es la latitud |
| `sun_low_frac_0_5deg` | fracción del día con el Sol entre 0 y 5° | DERIVED | 64.800 | 13 valores (0,227-1): también es la latitud |

En la Tierra solo hay irradiancia (WorldClim, bajo la atmósfera) y las dos fórmulas de latitud. No hay `illum_frac`.

**Los gemelos actuales ya son de las celdas mejor iluminadas de la zona:** `illum_frac` mediana 0,436 (la mediana de la zona es 0,315 y su percentil 90, 0,409); con el tratamiento del motor para la Antártida, 0,417. El 79 % de los pares (54 % con el tratamiento del motor) tiene el gemelo en la fila de latitud 75,5 S, el borde norte y cálido de la zona; los 10 gemelos del top 10 están en 75,5 S o 76,5 S. El problema no es qué celda polar se elige; es que ninguna celda polar se parece a un sitio soleado y cálido de la Tierra.

### 3. Un ejemplo concreto

Número 1 de Paneles con A1: **E44120 (32,5 S 20,5 E, Western Cape, Sudáfrica)**, idoneidad 86,8, 293,1 K, irradiancia 5,52 kWh/m²/día.

| opción | gemelo | temperatura del gemelo | `illum_frac` del gemelo | similitud | final | puesto (de 18.777) |
|---|---|---|---|---|---|---|
| A1 (hoy) | M59479, 75,5 S 100,5 O, Boltzmann a 81 km | 172,2 K | 0,454 | 78,0 | 82,4 | 1 |
| Luna entera | M41526, 25,5 S 53,5 O, Cavendish a 28 km | 210,2 K | 0,502 | 98,4 | 92,6 | 2.484 |
| Mares ecuatoriales | M27590, 13,5 N 50,5 E, Glaisher a 36 km | 212,9 K | 0,502 | 83,1 | 85,0 | 5.449 |
| Polo sur, solo `illum_frac` ≥ 0,44 | el mismo Boltzmann | 172,2 K | 0,454 | 78,0 | 82,4 | 1 |
| Irradiancia añadida a la similitud | el mismo Boltzmann | 172,2 K | 0,454 | 59,0 | 72,9 | 2.975 |
| Una sola celda, la mejor iluminada | M59715, 75,5 S 135,5 E, Schrödinger a 31 km | 153,7 K | 0,474 | 29,7 | 58,3 | 6.610 |

### 4. Las opciones

Todas calculadas sobre los datos reales, con los pesos A1 salvo donde se dice.

| opción | celdas candidatas | gemelos que cambian (de 18.777) | Spearman similitud-idoneidad | diferencia mediana de temperatura Tierra-gemelo | gemelos distintos; el más compartido | top 10 en común con A1 | trabajo y si cabe hoy |
|---|---|---|---|---|---|---|---|
| A1 actual (polo sur) | 5.400 | — | −0,681 | 126,3 K | 186; 16,8 % | — | — |
| **Otra zona: Luna entera** | 64.800 | 18.508 | −0,059 | 85,3 K | 4.595; 2,3 % | 0/10 | 2-3 h (nuevo tipo de zona en `similarity_zones`, pruebas, reconstrucción, textos). Cabe con riesgo. |
| **Otra zona: mares ecuatoriales** (ya definida en `build_lunar_reference_zones`, líneas 196-198: latitud ≤ 30°, elevación ≤ −1.200 m) | 6.686 | 18.777 | **+0,620** | 79,5 K | 374; 21,7 % (M22063, 28,5 N 76,5 O, cerca de Russell) | 0/10 | igual que la anterior |
| Polo sur, `illum_frac` ≥ 0,30 | 2.932 | 19 | −0,681 | 126,3 K | 180; 16,8 % | 10/10 | 1 h. No cambia nada. |
| Polo sur, `illum_frac` ≥ 0,40 | 761 | 2.032 | −0,601 | 126,6 K | 108; 16,8 % | 10/10 | 1 h. Casi nada. |
| Polo sur, `illum_frac` ≥ 0,44 (87 celdas, el 1,6 % mejor iluminado) | 87 | 15.669 | −0,581 | 127,3 K | 30; 12,4 % | 3/10 | 1 h. Sigue siendo indefendible. |
| Irradiancia añadida a la similitud (1/6 = 16,67 % para la irradiancia; las otras cuatro, los pesos A1 × 5/6: pendiente 27,78 %, rugosidad 22,22 %, elevación 16,67 %, temperatura 16,67 %) | 5.400 | 2.791 | **−0,826** (peor) | 125,7 K | 136; 19,6 % | 0/10 | 1-2 h. Empeora: el top 10 pasa a Canadá y China (idoneidad 63,5-70,3). |
| Gemelo único = la celda mejor iluminada (M59715, Schrödinger, `illum_frac` 0,474) | 1 | 18.777 | +0,202 | 136,3 K | 1; 100 % | 0/10 | 1 h. Similitud mediana 40,2: no es un par. |
| Elegir el gemelo por idoneidad solar | 0 | — | — | — | — | — | No se puede con los filtros del equipo: ninguna celda del polo sur pasa el filtro de irradiancia (máximo 2,475 < 2,5), y la altura del Sol ≥ 10° elimina todo lo que está por encima de unos 81,5° (FILTERS.md, §g). |

Cualquier umbral de iluminación es una decisión del equipo. Lo que enseñan los números es que ningún umbral dentro del polo sur arregla la contradicción: los gemelos ya están en las celdas mejor iluminadas. Solo cambiar de zona la quita (−0,68 → −0,06 con la Luna entera, +0,62 con los mares). Pero eso cambia el relato: los paneles dejan de ir "al polo sur de Artemis". Otras fuentes oficiales de iluminación (los mapas LOLA a 20-60 m de PGDA, https://pgda.gsfc.nasa.gov/products/69) solo afinarían la iluminación dentro del polo sur, que, como se ha visto, no es el problema.

**Top 10 de Paneles con los mares ecuatoriales:**

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final | gemela lunar (IAU más cercano) |
|---|---|---|---|---|---|---|---|
| 1 | E42435 | 27,5 S 135,5 E | Australia | 94,2 | 99,3 | 96,8 | M36499, 11,5 S 40,5 O, Dorsa Ewing a 66 km |
| 2 | E38744 | 17,5 S 44,5 E | Madagascar / Melaky | 96,8 | 96,6 | 96,7 | M33959, 4,5 S 60,5 O, Damoiseau a 25 km |
| 3 | E39104 | 18,5 S 44,5 E | Madagascar / Melaky | 95,9 | 97,4 | 96,7 | M35159, 7,5 S 59,5 E, Acosta a 59 km |
| 4 | E42075 | 26,5 S 135,5 E | Australia | 94,5 | 98,8 | 96,7 | M36499, 11,5 S 40,5 O, Dorsa Ewing a 66 km |
| 5 | E39464 | 19,5 S 44,5 E | Madagascar / Menabe | 95,9 | 97,3 | 96,6 | M31198, 3,5 N 58,5 E, Cartan a 33 km |
| 6 | E27554 | 13,5 N 14,5 E | Chad / Lac | 96,3 | 96,8 | 96,5 | M32260, 0,5 N 40,5 E, Mount Marilyn a 24 km |
| 7 | E37390 | 13,5 S 130,5 E | Australia | 96,1 | 96,9 | 96,5 | M33004, 1,5 S 64,5 E, Hargreaves a 24 km |
| 8 | E29420 | 8,5 N 80,5 E | Sri Lanka / North Central | 94,9 | 98,1 | 96,5 | M36499, 11,5 S 40,5 O, Dorsa Ewing a 66 km |
| 9 | E38385 | 16,5 S 45,5 E | Madagascar / Melaky | 96,5 | 96,4 | 96,4 | M29777, 7,5 N 77,5 E, Wildt a 68 km |
| 10 | E42436 | 27,5 S 136,5 E | Australia | 94,0 | 98,7 | 96,4 | M31563, 2,5 N 63,5 E, Petit a 6 km |

**Top 10 con la Luna entera** (5 de 10 puntos coinciden con los mares):

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final | gemela lunar (IAU más cercano) |
|---|---|---|---|---|---|---|---|
| 1 | E42435 | 27,5 S 135,5 E | Australia | 94,2 | 99,3 | 96,8 | M36499, 11,5 S 40,5 O, Dorsa Ewing a 66 km |
| 2 | E39799 | 20,5 S 19,5 E | Namibia | 94,1 | 99,4 | 96,7 | M32867, 1,5 S 72,5 O, Rimae Riccioli a 17 km |
| 3 | E38744 | 17,5 S 44,5 E | Madagascar / Melaky | 96,8 | 96,6 | 96,7 | M33959, 4,5 S 60,5 O, Damoiseau a 25 km |
| 4 | E39104 | 18,5 S 44,5 E | Madagascar / Melaky | 95,9 | 97,4 | 96,7 | M35159, 7,5 S 59,5 E, Acosta a 59 km |
| 5 | E42075 | 26,5 S 135,5 E | Australia | 94,5 | 98,8 | 96,7 | M36499, 11,5 S 40,5 O, Dorsa Ewing a 66 km |
| 6 | E22885 | 26,5 N 25,5 E | Egypt | 94,0 | 99,3 | 96,6 | M23893, 23,5 N 46,5 O, Aristarchus a 28 km |
| 7 | E22886 | 26,5 N 26,5 E | Egypt | 94,1 | 99,1 | 96,6 | M23893, 23,5 N 46,5 O, Aristarchus a 28 km |
| 8 | E22891 | 26,5 N 31,5 E | Egypt / Suhaj | 94,8 | 98,3 | 96,6 | M31576, 2,5 N 76,5 E, Nobili a 73 km |
| 9 | E39464 | 19,5 S 44,5 E | Madagascar / Menabe | 95,9 | 97,3 | 96,6 | M31198, 3,5 N 58,5 E, Cartan a 33 km |
| 10 | E40158 | 21,5 S 18,5 E | Namibia | 93,9 | 99,2 | 96,5 | M28795, 10,5 N 175,5 E, Safarik a 36 km |

**Top 10 con el polo sur restringido a `illum_frac` ≥ 0,44:**

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final | gemela lunar (IAU más cercano) |
|---|---|---|---|---|---|---|---|
| 1 | E44120 | 32,5 S 20,5 E | South Africa / Western Cape | 86,8 | 78,0 | 82,4 | M59479, 75,5 S 100,5 O, Boltzmann a 81 km |
| 2 | E27615 | 13,5 N 75,5 E | India / Karnataka | 90,9 | 73,6 | 82,3 | M59479, 75,5 S 100,5 O, Boltzmann a 81 km |
| 3 | E27814 | 12,5 N 85,5 O | Nicaragua / Boaco | 91,2 | 73,1 | 82,1 | M59479, 75,5 S 100,5 O, Boltzmann a 81 km |
| 4 | E29738 | 7,5 N 38,5 E | Ethiopia / Oromiya | 89,7 | 74,5 | 82,1 | M59679, 75,5 S 99,5 E, Rittenhouse a 71 km |
| 5 | E43759 | 31,5 S 19,5 E | South Africa / Northern Cape | 87,8 | 76,3 | 82,1 | M59479, 75,5 S 100,5 O, Boltzmann a 81 km |
| 6 | E40516 | 22,5 S 16,5 E | Namibia / Erongo | 92,3 | 71,7 | 82,0 | M59676, 75,5 S 96,5 E, Hale a 56 km |
| 7 | E41247 | 24,5 S 27,5 E | South Africa / Limpopo | 91,7 | 72,1 | 81,9 | M59676, 75,5 S 96,5 E, Hale a 56 km |
| 8 | E42318 | 27,5 S 18,5 E | Namibia / Karas | 92,9 | 70,8 | 81,8 | M59676, 75,5 S 96,5 E, Hale a 56 km |
| 9 | E30460 | 5,5 N 40,5 E | Ethiopia | 89,9 | 73,7 | 81,8 | M59479, 75,5 S 100,5 O, Boltzmann a 81 km |
| 10 | E41609 | 25,5 S 29,5 E | South Africa / Mpumalanga | 88,7 | 74,9 | 81,8 | M59676, 75,5 S 96,5 E, Hale a 56 km |

**Top 10 con irradiancia en la similitud:**

| # | celda Tierra | lat, lon | lugar | idoneidad | similitud | final | gemela lunar (IAU más cercano) |
|---|---|---|---|---|---|---|---|
| 1 | E17228 | 42,5 N 128,5 E | China / Jilin Sheng | 70,3 | 80,2 | 75,2 | M59479, 75,5 S 100,5 O, Boltzmann a 81 km |
| 2 | E14141 | 50,5 N 78,5 O | Canada / Quebec | 66,2 | 83,5 | 74,8 | M59734, 75,5 S 154,5 E, Schrodinger a 169 km |
| 3 | E14139 | 50,5 N 80,5 O | Canada | 66,2 | 83,4 | 74,8 | M59734, 75,5 S 154,5 E, Schrodinger a 169 km |
| 4 | E14140 | 50,5 N 79,5 O | Canada | 66,1 | 83,4 | 74,8 | M59734, 75,5 S 154,5 E, Schrodinger a 169 km |
| 5 | E14137 | 50,5 N 82,5 O | Canada | 66,4 | 83,2 | 74,8 | M59734, 75,5 S 154,5 E, Schrodinger a 169 km |
| 6 | E14138 | 50,5 N 81,5 O | Canada | 66,4 | 83,2 | 74,8 | M59734, 75,5 S 154,5 E, Schrodinger a 169 km |
| 7 | E13431 | 52,5 N 68,5 O | Canada / Quebec | 63,5 | 86,1 | 74,8 | M59481, 75,5 S 98,5 O, Boltzmann a 66 km |
| 8 | E14136 | 50,5 N 83,5 O | Canada / Ontario | 66,5 | 83,1 | 74,8 | M59734, 75,5 S 154,5 E, Schrodinger a 169 km |
| 9 | E14499 | 49,5 N 80,5 O | Canada / Ontario | 67,1 | 82,4 | 74,7 | M59734, 75,5 S 154,5 E, Schrodinger a 169 km |
| 10 | E14498 | 49,5 N 81,5 O | Canada / Ontario | 67,1 | 82,4 | 74,7 | M59734, 75,5 S 154,5 E, Schrodinger a 169 km |

### 5. Recomendación y por qué

**Ningún cambio en la integración sin una decisión del equipo** (lo del director), **y si se deja así, publicar la limitación.** Mis números no lo contradicen. Las opciones "baratas" (umbral de iluminación, irradiancia en la similitud, gemelo único) no arreglan nada o lo empeoran. La única que quita la contradicción (cambiar de zona) cambia la historia de la misión y cuesta 2-3 h en un día de entrega. Si el equipo quiere cambiar, la opción con mejor resultado es la de los mares ecuatoriales: es una zona que ya existe en el código, sus gemelos están a pleno sol (`illum_frac` 0,50) y la similitud pasa a ir a favor de la idoneidad (+0,62).

### 6. Qué cambia en los resultados si se acepta

Si se deja como está: 0 cambios; el top 10 es el A1 de la decisión 1 y solo se añade el texto. Si el equipo eligiera los mares: cambian de gemelo los 18.777 pares y el top 10 pasa a ser el de la tabla de arriba (0/10 en común con A1).

### 7. Riesgo ante el jurado

- *"¿Por qué el mejor sitio para paneles de la Tierra se empareja con un cráter polar casi a oscuras?"* Esta es la pregunta más probable y la más dañina. Respuesta honesta: el gemelo se elige por relieve y temperatura, no por la luz. Para los paneles el par dice "este terreno tiene una forma parecida a este del polo sur", no "aquí hay la misma luz". La diferencia de temperatura es de unos 126 K y lo decimos.
- *"¿No tenéis datos de iluminación?"* En la Luna sí (LOLA), pero en la Tierra no hay una magnitud equivalente medida igual, así que no puede entrar en una comparación entre los dos cuerpos.

### 8. Qué se escribe en ASSUMPTIONS.md y qué se enseña en la web

**ASSUMPTIONS.md**, nuevo punto en §0.7:

> "Known limitation, solar (left unchanged pending a team decision, 2026-11-15): solar suitability rewards warm, sunny places while the twin comes from the coldest part of the Moon and is chosen on relief and temperature only; similarity and suitability are anti-correlated (Spearman -0.68; Earth temperature correlates +0.93 with suitability and -0.98 with similarity). The twins already are the best-lit polar cells (LOLA illum_frac median 0.436 against 0.315 for the zone); restricting candidates to illum_frac >= 0.30 / 0.40 / 0.44 changes 19 / 2,032 / 15,669 of 18,777 twins and leaves the anti-correlation at -0.58 to -0.68. Only another target zone removes it (whole Moon -0.06; equatorial maria +0.62). No south-pole cell passes the solar irradiance gate (maximum 2.475 < 2.5 kWh/m2/day)."

**Web**, en la ficha de la misión de Paneles solares (texto de limitación):

> "Limitation: for solar arrays, the lunar twin is chosen by terrain shape and surface temperature, not by sunlight. The twin lies in the lunar south-polar zone, where Artemis plans to land; it is the best match in relief, but it is about 126 K colder than the Earth point and receives far less energy. Read the pair as 'similar terrain', not 'similar sunlight'."

*Traducción:* "Limitación: para los paneles solares, el gemelo lunar se elige por la forma del terreno y la temperatura de superficie, no por la luz del Sol. El gemelo está en la zona del polo sur lunar, donde Artemis prevé aterrizar; es el más parecido en relieve, pero está unos 126 K más frío que el punto de la Tierra y recibe mucha menos energía. Lee el par como 'terreno parecido', no como 'luz parecida'."

**Sustituido (15-11-2026, mañana):** Paneles solares pasa a los mares ecuatoriales con la irradiancia sin atmósfera como variable clave y este texto de limitación se retira del paquete (ver "Decisiones tomadas (15-11-2026, mañana)", punto 6). Lo que sigue es el registro de anoche.

**Nota (15-11-2026).** Decidido: Paneles solares se queda en el polo sur y se publica la limitación. Los mares ecuatoriales (opción de la sección 4, la de mejor resultado) quedan como **alternativa no implementada**, para que el líder del equipo la valore por la mañana; no se ha tocado el motor para ello.

---

## Resumen

| decisión | recomendación | impacto en los resultados | tiempo de trabajo (estimado) | ¿bloquea la entrega? |
|---|---|---|---|---|
| 1. Regla del gemelo | Encender A1 (`zone_twin`) con `DEFAULT_WEIGHTS` | 31.533 pares nuevos; ningún top 10 actual se mantiene (0/10 en las tres misiones) | 1 h: cambiar el ajuste, reconstruir, revisar, textos | **Sí**: sin ella no hay pares |
| 2. Quitar la roca | Retirada definitiva; reparto proporcional; se enseña como dato | 0 gemelos cambian; el orden sí (top 10 frente a "con roca": 0/10, 8/10, 0/10) | 0 h en el motor (ya hecho); 15 min de textos; comprobar que la web la pinta | No |
| 3. Antártida sin temperatura | Ignorar y renormalizar, y marcar en la web | 1.123 (Rover) y 6.023 (Paneles) gemelos cambian frente a la propuesta; ningún top 10 cambia; Base lunar no se ve afectada | 0 h en el motor (ya lo hace); 30-60 min para la marca en el panel | No, pero el texto y las cifras citadas dependen de ella |
| 4. Concentración en Base lunar | Aceptar y enseñar cuántos puntos comparten cada gemelo | Ninguno | 30-60 min si el panel aún no muestra el recuento | No |
| 5. Paneles frente al polo sur | Sin cambios sin decisión del equipo; publicar la limitación | Ninguno si se deja; 18.777 gemelos si se cambia a mares | 15 min el texto; 2-3 h cambiar de zona | No si se publica la limitación |

**Orden en que conviene responder:**

1. **Decisión 1**, porque todo lo demás describe pares que solo existen si se enciende `zone_twin`, y el motor tiene que reconstruirse.
2. **Decisión 5**, porque es la única que puede pedir trabajo de código (cambio de zona) y necesita al equipo; si la respuesta es "se deja", el texto de limitación tiene que estar en la web antes de grabar el vídeo y las capturas.
3. **Decisión 3**, porque fija qué cifras de gemelos se citan (las del motor: 744 y 721 gemelos distintos, no 305 y 186) y el texto del panel antártico.
4. **Decisión 2**, que ya está hecha; solo hay que confirmarla y comprobar que la web enseña la variable.
5. **Decisión 4**, que solo afecta al texto y al recuento del panel.

## Lo que no se ha podido calcular hoy

- La temperatura de NASA POWER para las 6.558 celdas antárticas (solo se probó en 5 puntos) y el efecto que tendría en los pares.
- Si el panel de la web pinta hoy la fracción de suelo desnudo y el recuento de puntos por gemelo: `app/` lo están editando otros agentes y solo se buscó en `app/src`, sin resultado.
- No se ejecutó el motor: las cifras "como el motor" salen de reimplementar su tratamiento de los datos que faltan, y coinciden con las que publica `ASSUMPTIONS.md` §0.7.

## Comprobación

Revisión independiente hecha el 15-11-2026 con scripts propios (`scratchpad/stars/decisions-check/`: `cctx.py`, `c1.py`, `c1b.py`, `c1c.py`, `c2.py` a `c5.py`; salidas `*.out`), que parten solo de la reimplementación independiente de `proposal-verify/` (no del código del autor). Mis gemelos A1 coinciden celda a celda con los de esa reimplementación en las tres misiones (diferencia de similitud 0).

**Recalculado y correcto tal como estaba:** el commit `ff6f1ae` (14-11-2026 23:46:05 UTC, único resultado de `git log -S"Plan decision 2"`) y las líneas 259-261 citadas, más la línea 259 de `main`; las líneas de `analog_finder.py` (68-75, 143-181, 166, 189, 193-198, 225-240, 463, 476, 489), de `engine_config.json` (218, 224, 246-274), de `repo_similarity.py` (31-36, 153-175, 185-210) y de `mission_scoring.py` (117-134); las celdas por zona (5.400 / 1.440, 280 / 114, 700, 64.800 / 16.200); los pesos (A1 33,33 / 26,67 / 20,00 / 20,00 %; A2 y A3a por misión; renormalizados sin temperatura 41,67 / 33,33 / 25,00 %; reparto a partes iguales y "todo al relieve"); los cambios de gemelo, Spearman y top 10 de A2 y A3a; el ejemplo de Haughton en A1, A2, A3a y Tycho; los top 10 "después" de las tres misiones y el de Tycho (Spearman 0,543; M49851 con 2.633 puntos, 25,5 %); toda la decisión 2 (estadísticos de la fracción desnuda, z, tope de 47,96, 0 gemelos cambiados, Spearman 0,362 / 0,666 / 0,550, solapes 0/10, 8/10, 0/10, medianas por tramo, ejemplo de Atacama, top 10 "con roca", clase CCI 220 en Groenlandia); en la decisión 3, las 6.578 / 6.558 / 7 celdas, la mediana de 284,27 K, los 1.156 / 6.060 / 0 puntos afectados, el motivo de Base lunar, los 1.123 / 6.023 cambios, las medianas 78,3 → 98,0 y 77,1 → 96,1, los mejores puestos 4.222 → 888 y 12.459 → 3.881, los Spearman 0,908 / 0,784, la exclusión (9.181 / 12.717), las cifras del motor (744 / 895 y 721 / 3.047, que coinciden con `ASSUMPTIONS.md` §0.7) y el ejemplo de Dome C; en la decisión 4, las tres celdas (puntos, coordenadas, nombre IAU, distancia y región), la distribución de gemelos de las tres misiones, los límites del 5 % (121 puntos) y del 10 % (242) y los tres gemelos más parecidos; en la decisión 5, la correlación −0,681 y las de cada variable, los tercios, el salto de 126,3 K, los datos de iluminación y todas las opciones (celdas, gemelos que cambian, Spearman, salto, solapes, ejemplo E44120, top 10 de los mares, de la Luna entera y de `illum_frac` ≥ 0,44). NASA POWER: he repetido la consulta en Dome C (TS −55,45 °C, T2M −51,18 °C, MERRA-2, 2001-2025, sin clave) y en las tres celdas de comparación (+5,2 / −7,1 / +1,3 K).

**Corregido:**

1. **Lo que enseña hoy la web no era lo que el documento llamaba "hoy".** El motor de hoy ya quita la roca y ya ignora la temperatura que falta, así que su Luna media (E0) no es la A0 de la propuesta (con roca). Lo he comprobado contra el paquete publicado `app/public/data/v2`: mi E0 reproduce su similitud en los 31.533 puntos y sus top 10. He cambiado los tres top 10 "antes" de la decisión 1 (ahora estepa de Mongolia, Mongolia Interior y Xinjiang en Rover y Base lunar; Northern Cape, República Centroafricana y Australia en Paneles), los Spearman antes/después (0,578 / 0,646 / 0,117 frente a E0; los de A0 se mantienen como referencia), la fila "hoy" del ejemplo de Haughton (similitud 72,8, puesto 625, no 45,4 y 4.224, que son de A0), la opción D de la decisión 1 y la frase sobre la pradera de Alberta en la decisión 2 (es el número 1 de A0, no de la web de hoy).
2. Decisión 3: "ninguna en el top 100 con la regla de hoy" es cierto para la web de hoy (mejor puesto 542), pero con `analog_finder` tal cual (A0) entrarían 14 en el top 100 del Rover; añadido.
3. Decisión 3: la comparación de la similitud inflada usaba la mediana de todos los puntos (79,1), que incluye a los propios antárticos; ahora se compara con los puntos con temperatura (Rover 80,1; Paneles 74,8), también en el texto para `ASSUMPTIONS.md`.
4. Decisión 3: la fila de NASA POWER del ejemplo de Dome C ya tiene similitud y gemelo (81,5; M62850, Mons Mouton a 3 km); el puesto sigue sin calcular. La resolución y la licencia de POWER no se pueden leer en su documentación sin JavaScript: quedan marcadas como no confirmadas. Que MOD11C3 pide cuenta Earthdata está ahora comprobado (redirección a `urs.earthdata.nasa.gov`).
5. Decisión 4: los porcentajes de puntos más cálidos que Boltzmann (76,3 % y 92,1 %) contaban como "más cálidos" los antárticos con z = 0; con los puntos que tienen temperatura son 73,3 % y 88,3 %.
6. Decisión 5: no "todos" los gemelos están en 75,5 S: lo están el 79 % (54 % con el tratamiento del motor). La Luna entera y los mares comparten 5 de 10 puntos del top 10, no 8. La opción "irradiancia añadida" no reparte 16,67 % a cada variable: da 1/6 a la irradiancia y escala las otras cuatro (27,78 / 22,22 / 16,67 / 16,67 %). Idoneidad de ese top 10: 63,5-70,3.
7. Decisión 2: el reparto a partes iguales cambia el 2,2-3,3 % de los gemelos (no "menos del 3,3 %" ni "2-3 %"); las líneas de `export_v2.py` eran imprecisas (la marca `part_of_similarity` está en 580 y 585, dentro de `lunar_info_summary`, 573-585, y la exportación por gemelo en 614-619 del fichero de trabajo, que otros agentes están editando).
8. Tycho en la tabla antigua de 2 grados: 198 celdas (antes "no calculado").

**No verificado:**

- Que el panel de la web enseñe la fracción desnuda del punto de la Tierra y el recuento por gemelo (no he leído `app/src`, que están editando otros agentes). Sí he visto que el motor exporta el recuento por gemelo (`earth_cells` en `twins.json`).
- La resolución (0,5° × 0,625°) y la licencia de NASA POWER en su documentación; el acceso a ERA5; si MOD11C3 cubre de verdad la Antártida en nuestras celdas (no descargado).
- Los percentiles dentro de la zona de la tabla de la decisión 4 dependen de cómo se defina el percentil: a mí me salen 72 (temperatura de M62515) y 22 (pendiente de M63665) en lugar de 73 y 23. No cambia la lectura.
- El límite por gemelo depende del orden de asignación; con mi orden (de más a menos parecido) reproduzco las cifras del documento con 121 y 242 puntos de tope.
- Las horas de trabajo son estimaciones del autor; no se pueden comprobar.
- No he ejecutado el motor; E0 lo he comparado con el paquete ya publicado, y la regla `zone_twin` con la reimplementación de su tratamiento de los datos que faltan.

---

## Principio del análogo (decisión de Facundo, 15-11-2026, 04:47-04:49 CET)

*(Base lunar: diseño confirmado el 15-11-2026 a las 08:55 CET; ver "Decisiones tomadas (15-11-2026, 08:55 CET)", punto 1.)* **Estado (actualizado el 15-11-2026 por la mañana): decidido y aplicado para Rover y Paneles solares** (sección "Decisiones tomadas (15-11-2026, mañana)" al principio de este documento; resultados en `docs/ANALOG_PRINCIPLE.md`, "Resultado tras implementar (15-11-2026)"). **Base lunar: pendiente**, sin cambios hasta que el equipo confirme una propuesta nueva. Texto original del estado: propuesta de método pendiente de respuesta de Facundo; nada decidido sobre el método, nada implementado ni reconstruido. El análisis con números y la propuesta están en `docs/ANALOG_PRINCIPLE.md`. Este principio prevalece sobre la elección de zonas y pesos de anoche donde choquen; el resto de lo decidido anoche se mantiene.

- **P1.** Un par es un análogo solo si la variable que determina el rendimiento de la misión es parecida. Variables clave: Paneles solares = iluminación / irradiancia; Rover = pendiente y rugosidad (transitabilidad); Base lunar = temperatura y amplitud térmica. Si alguna no encaja, se justifica con datos.
- **P2.** La variable clave debe (a) entrar en la similitud con peso dominante y (b) actuar como filtro del par: si la variable clave del gemelo no está dentro de una tolerancia, el par no es análogo y no se enseña. Proponer la tolerancia con números (en z de cada cuerpo y en valor absoluto) y cuántos pares sobreviven.
- **P3.** Paneles solares: con este principio se descarta el polo sur. Pasar a la zona donde la luz es parecida (la de mares ecuatoriales ya definida en `analog_finder.build_lunar_reference_zones`, o la Luna entera si, con la irradiancia dentro de la similitud, da mejor resultado). Usar `irradiance_kwh_m2_day` lunar y la irradiancia de la Tierra; explicar la diferencia de magnitud (con y sin atmósfera). El texto de limitación de anoche para Paneles solares se sustituye.
- **P4.** Base lunar: el 99,96 % de los puntos de la Tierra es más cálido que cualquier celda de la zona. Decir con números si la zona actual se sostiene con el principio, o cuáles son las alternativas, antes de cambiarla.
- **P5.** Rover: comprobar que la pendiente y la rugosidad de cada par están dentro de la tolerancia.
- **P6.** En un par análogo los datos de los dos cuerpos tienen que ser de verdad bastante parecidos; si no lo son, el método está mal. Para cada misión y cada variable, comparar los valores REALES del punto de la Tierra y de su gemelo (no solo los z): mediana de la diferencia, percentil 90 por variable y porcentaje de pares dentro de una tolerancia razonable propuesta.
- **P7.** Si pares con "98 % de similitud" resultan tener valores muy distintos (una pendiente siete veces menor; sitios diez veces más llanos que la referencia lunar), no se parchea: se arregla la estadística en la raíz (normalización, escala, fórmula de similitud o zona) para que una similitud alta signifique valores parecidos.
- **P8.** Separar las variables que se pueden comparar físicamente en valor absoluto (pendiente, rugosidad, elevación relativa) de las que no pueden coincidir entre los dos cuerpos (temperatura; irradiancia con y sin atmósfera). Para estas, proponer cómo compararlas con honestidad, y decirlo con números.
- **P9.** En las variables secundarias los valores pueden diferir, siempre que no sea exagerado (tolerancias razonables). En las variables que llevan el peso de cada misión no: ahí tienen que ser de verdad parecidas, y si no lo son el par se descarta.

**Resultado del análisis (resumen; detalle en `docs/ANALOG_PRINCIPLE.md`):** con la regla de hoy ningún par del Rover tiene la pendiente a menos de 2° ni la rugosidad a menos de 30 m de su gemelo, también entre los de similitud ≥ 90. Propuesta: similitud gaussiana sobre diferencias absolutas con filtro por la variable clave. Rover: polo sur, sobreviven 10.192 de 10.337. Paneles solares: Luna entera con irradiancia sin atmósfera, 18.776 de 18.777 (mares ecuatoriales 6.360; polo sur 0). Base lunar: 0 de 2.419 en cualquier zona; opciones para el equipo en la sección D.3 de ese documento. Cifras comprobadas por un segundo agente con código propio el 15-11-2026 (sección "Comprobación" de `docs/ANALOG_PRINCIPLE.md`); se corrigieron las de Paneles solares sin atmósfera (fórmula del tope de la atmósfera), las de la opción "solo amplitud" de Base lunar y la correlación de hoy en Paneles (−0,92 con el paquete publicado, no −0,68).

## Puntos del líder de las 12:10 (15-11-2026, a través de su delegado)

Solo textos del bundle y documentos: ningún emparejamiento, puntuación, rango, gemelo, peso, tolerancia, filtro ni regla cambia. Comprobado: todos los `.bin` del bundle reconstruido son idénticos byte a byte a los de antes de este paso, y en los JSON solo difieren campos de texto, con una excepción declarada (punto d de la re-auditoría, abajo). Todas las cifras de esta sección salen del bundle reconstruido y las congela `tierra luna/tests/test_texts_1210.py`.

### 1. Escala de Rover: fuentes exactas (comprobadas hoy, 15-11-2026, en la fuente)

- **ETOPO 2022, 7,17 m.** MacFerrin, M., Amante, C., Carignan, K., Love, M. y Lim, E. (2025), "The Earth Topography 2022 (ETOPO 2022) global DEM dataset", *Earth System Science Data* 17(5), 1835-1849, versión publicada el 08-05-2025. https://doi.org/10.5194/essd-17-1835-2025 . Resumen: "ETOPO 2022 measures a global RMSE of 7.17 m." Sección 6 ("Validation results"): "we find that ETOPO has a mean RMSE over land of 7.17 m" (media de los RMSE de las subteselas de 1x1 grado sobre tierra, frente a ICESat-2). Pie de la figura 6: "The mean RMSE of the dataset is 7.17 m." **Confirmado.**
- **LOLA, unos 10 m.** Smith, D. E., Zuber, M. T., Neumann, G. A., Lemoine, F. G., Mazarico, E., Torrence, M. H., McGarry, J. F., Rowlands, D. D., Head, J. W., Duxbury, T. H. et al. (2010), "Initial observations from the Lunar Orbiter Laser Altimeter (LOLA)", *Geophysical Research Letters* 37(18), L18204, septiembre de 2010. https://doi.org/10.1029/2010GL043751 (la página del editor devolvió 403 hoy; confirmado en la copia abierta del MIT, http://hdl.handle.net/1721.1/74221). Resumen: "have been used to improve the lunar geodetic grid to ∼10 m radial and ∼100 m spatial accuracy" (con respecto al centro de masas de la Luna). **Confirmado**, con una salvedad que ya estaba escrita: es la exactitud absoluta de la red geodésica, no el ruido de un píxel; para una celda es una cota pesimista.
- Escala resultante: pendiente sqrt((7,17/(√2·1853))² + (10/(√2·1895,2))²) rad = 0,265093°; rugosidad sqrt(2·7,17² + 2·10²) = 17,40 m (fórmula: `docs/stats_audit/research_5_rover_escala.md`, "Para implementar"). La misma referencia está en el campo `source` de la escala en `engine_config.json` (`real_value_similarity`), que el bundle exporta para que la web la enseñe.

### 2. La idoneidad de Rover también está saturada (texto `rover_suitability_saturation`, ficha de Rover y "Data and limits")

Criterios del equipo para Rover (sin cambios): pendiente 45 % (nota máxima a 1° o menos), rugosidad 30 % (nota máxima a 30 m o menos), fracción de suelo desnudo 25 % (nota máxima a 0,7 o más). De los 254 sitios empatados arriba, 250 tienen la nota máxima en los tres criterios; 253 de los 10.337 puntos clasificados muestran idoneidad 100,00. Entre los 10.337 clasificados alcanzan el máximo: pendiente 3.291, rugosidad 2.144, suelo desnudo 930; los tres a la vez, 250. Entre los 254 empatados: pendiente 0,500 a 0,961°, rugosidad 14,61 a 30,19 m, suelo desnudo 0,707 a 1,000.

Ejemplo trabajado: **Bardenas Reales** (número 7.046, similitud 100,00, idoneidad 70,43): pendiente 1,91° (utilidad 0,93, pierde 2,9 puntos), rugosidad 77 m (0,92, pierde 2,3), suelo desnudo 0,018 (0,03, pierde 24,4). **Tabernas** (número 7.390, similitud 100,00, idoneidad 69,36): pendiente 3,17° (0,85, pierde 7,0), rugosidad 111 m (0,87, pierde 3,9), suelo desnudo 0,146 (0,21, pierde 19,8). Frente al primer empatado (idoneidad 100,00: pendiente 0,571°, rugosidad 26,7 m, suelo desnudo 0,824; no pierde nada). Los dos análogos reconocidos pierden casi todo en el suelo desnudo: el mapa ESA CCI los clasifica como matorral o mosaico (ver la nota de `provenance_earth.csv`). **Es una debilidad de los criterios de idoneidad tal como los escribió el equipo**: premian el terreno más suave y más desnudo y no dicen nada más de la movilidad. No se toca; queda para la re-auditoría.

### 3. La regla de tierra (confirmada por el líder)

Al elegir los cinco se salta una celda con menos de la mitad de tierra (pendiente y rugosidad solo significan algo en suelo firme); es una parte de la regla con nombre propio y su propio interruptor (`top5_selection.missions.*.skips.water`, separado de `skips.ice`). Lo que hace cada parte (texto `top5_rule_parts`, "Data and limits"):

| parte | Rover: empatados arriba (254) | Rover: clasificados (10.337) | Paneles solares (6.360) | Base lunar (450) |
|---|---|---|---|---|
| hielo (≥ 50 % nieve y hielo) | 0 | 1.485 | 0 | 0 |
| tierra (< 50 % tierra) | 13 | 671 | 0 | 0 |
| 2 grados | ninguno (los cinco se eligen lo más separados posible; los dos más cercanos están a 60,0°) | — | 4 puntos por encima del quinto mostrado | 2 puntos por encima del quinto mostrado |

Quedan 241 empatados de Rover tras las dos exclusiones.

### 4. Pendiente mínima de Rover de 0,5°

Se mantiene y se dice qué es (texto `rover_slope_minimum`, ficha de Rover y "Data and limits"): un criterio del equipo **sin fuente oficial**, conservado por su efecto medido (sección "Pendiente mínima de Rover (0,5°)" de arriba): sin él pasan 7.847 puntos más (2.862 de hielo o nieve), 28 de los 50 primeros pasan a ser llanos con menos de 0,5°, las celdas de agua en el top 50 pasan de 4 a 13, un gemelo lunar se lleva el 13,9 % de los pares en vez del 2,6 %, y los análogos conocidos bajan (Qaidam del 4,0 % al 8,3 %, Haughton del 4,2 % al 8,4 %, Ramon del 3,6 % al 8,0 %, Yungay del 8,1 % al 11,6 %).

### 5. Redacción de los cinco

- Rover (`missions.json` `top5.rule`, `list_order_rover`, `rover_tie`): "These are five of the 254 sites tied at the top of our model, chosen to be spread across the world", y después cómo (sin celdas de hielo mayoritario, al menos la mitad de tierra, al menos 2° de separación, los más separados entre los empatados) y que el empate está dentro de la incertidumbre de los modelos de elevación (0,27° y 17,4 m). Ya no dice "five of the highest-scoring analogs".
- Paneles solares y Base lunar conservan "five of the highest-scoring analogs in our model" porque es cierto de los cinco que elige la regla: la regla recorre la clasificación por nota final y se queda con cada punto permitido, así que son las cinco notas finales más altas entre los puntos que la regla permite (números 1, 2, 5, 7 y 9 en Paneles solares; 1, 3, 5, 6 y 7 en Base lunar). El texto lo dice así.

### 6. Sin referencias técnicas en los textos que lee el usuario

Reescritos `zone_edge_lunar_base` (la frase que se imprime junto a cada gemelo), `external_validation_*`, `numbers_without_effect`, `deviations_from_team` (criterios con nombre en palabras; "the team's scoring file" una vez; fuentes fuera del texto mostrado), `constants_two_values`, `surface_classes_rover`, `lunar_base_swing_gate` (sin identificadores de celda) y el `no_twin_reason` del fixture sin gemelo (sin nombres de reglas). Un test recorre todos los textos que la web imprime y falla si aparece un nombre de fichero, de columna o un código interno (`tests/test_texts_1210.py`).

### Correcciones de texto de la re-auditoría de Base lunar (`docs/stats_audit/9_reauditoria_base.md`)

- (a) `external_validation_lunar_base` decía que los sitios del benchmark que pasan el embudo "no tienen gemelo": falso. Ahora se calcula en cada build con las listas de r4 (mismas cifras que `research/r4_rank_sites.py` sobre el bundle): de 13 sitios fríos o polares pasan 3 y 2 tienen gemelo, MDRS (número 335) y Craters of the Moon (número 179); Black Point pasa sin gemelo. Lo mismo para Paneles solares (13 estaciones BSRN soleadas: pasan 11, 9 con gemelo; 0 de las 6 nubladas pasan) y Rover (ya se calculaba en cada build).
- (b) Los pesos de Base lunar suman 0,95 y la idoneidad divide por esa suma (en la práctica 36,8 %, 26,3 %, 26,3 % y 10,5 %): dicho en `lunar_base_criteria` y en `deviations_from_team`.
- (c) `rock_or_bare_frac`: el texto decía DERIVED; ahora dice MEASURED, como `real_data/provenance_earth.csv`, con la salvedad de que es un recuento de píxeles de una clasificación.
- (d) `weighted_variables[].also_in_similarity` de `tmin_c` en Base lunar pasa de `false` a `true` (la similitud compara `tmin_k`, leído de `tmin_c`). Es un campo descriptivo de `missions.json` que no entra en ningún cálculo ni en ningún `.bin`; es el **único** valor no textual que cambia en este paso. En Rover los criterios de idoneidad se leen de columnas de 300 m y la similitud de las de km, así que allí sigue `false`.
- (e) Estabilidad de Base lunar (texto `top5_stability_lunar_base`), del JSON del auditor (`stability.corrected`, 200 simulaciones): sigue entre los cinco / en el top 20 — Tinghir 18,0 % / 51,5 %; Aheqi 23,0 % / 52,5 %; Kherameh 19,0 % / 43,5 %; Waxxari 18,0 % / 38,0 %; Aradan 22,5 % / 59,0 %; los mismos cinco salen juntos en 0 de 200. Rover y Paneles solares siguen "pending the independent re-audit".

### No hecho en este paso

Mover la configuración muerta del motor (la entrada de zona solar "latitude <= -75", las tolerancias de referencia sin uso, la escala por rango agregado) a un bloque `legacy`: exige cambiar las lecturas del código y no cabía en el tiempo sin riesgo; queda pendiente.

## Reauditoría independiente del modelo corregido (15-11-2026)

Un auditor por misión, sobre el modelo d24ebb3 y los textos de final-integration. Cifras leídas de `docs/stats_audit/9_reauditoria_rover.json`, `9_reauditoria_solar.json` y `9_reauditoria_base.json` (y sus `.md`).

### Veredictos

| Misión | Veredicto | Commit | Números | Textos (antes de esta pasada) |
|---|---|---|---|---|
| Rover | **GO final** | rama audit-rover, 6c3750c | GO (0 diferencias en 10.337 puntos; vuelta atrás exacta) | NOT YET: T1, T4, T5, T6, T7, T8 |
| Paneles solares | **GO final** | rama audit-solar, 89a5c52 | GO (0 diferencias en 18.777 puntos; vuelta atrás exacta) | NOT YET: F1, F4, estabilidad pendiente |
| Base lunar | **GO** | 57ab46a y posteriores | GO (2.419 / 450 / 103; 0 diferencias) | GO tras la primera pasada de textos (0486ad9) |

### Estabilidad y validación externa (como las dan los informes)

- **Rover** (200 simulaciones): cada uno de los cinco está entre los cinco mostrados en el 52,5 / 43,0 / 65,0 / 87,5 / 67,0 % de las corridas y sigue en el grupo empatado arriba en el 72,5 / 43,0 / 88,5 / 100,0 / 74,0 %; los mismos cinco exactos salen en el 10,5 % (60 quintetos distintos); el grupo empatado conserva un 89 % de sus miembros (mediana); el gemelo de cada uno se conserva en el 17,5 a 38 %; con pesos ±10 %, 10 de 10. Validación verificada: mediana 8,1 % frente a 9,2 % por la mañana, separación 0,906 en ambos.
- **Paneles solares** (200 simulaciones): entre los cinco 9,5 / 7,0 / 13,0 / 1,5 / 0,5 %; en el top 20 40,0 / 37,5 / 31,5 / 14,5 / 12,5 %; los mismos cinco nunca se repiten (0 de 200); con pesos ±10 %, 14 de 14 con el mismo gemelo. Validación BSRN: clasificación completa 8,3 % frente a 14,9 % (mejor); dentro de la fila de latitud 28,8 % frente a 27,9 % (igual); 9 de 11 en el cuartil superior.
- **Base lunar** (200 simulaciones): entre los cinco 18,0 / 23,0 / 19,0 / 18,0 / 22,5 %; en el top 20 51,5 / 52,5 / 43,5 / 38,0 / 59,0 %; los mismos cinco 0 de 200. Validación: separación 0,615 (igual que por la mañana); MDRS 13,8 % (número 335) y Craters of the Moon 7,4 % (número 179).

### Lo que sigue débil (criterios decididos, no fallos de implementación)

- **Rover:** qué cinco se muestran es inestable (empate de 254 en la cabeza); Bardenas y Tabernas caen a un 68,2 % y un 71,5 % por la fracción de suelo desnudo.
- **Paneles solares:** dentro de la fila de latitud no es mejor que la latitud sobre las estaciones BSRN; una celda sin dato de nubes (E34142, Sulawesi) es la 16.ª por la renormalización de su peso.
- **Base lunar:** los cinco nunca se repiten en 200 corridas; E17538 falla el embudo en el 36,5 % de las corridas.

### Correcciones de texto de esta pasada (ningún número cambia)

Todas en el origen (`engine/engine_config.json`, `engine/datasets.json`, `engine/limits.py`, `engine/export_v2.py`); cifras leídas por script de los JSON de la reauditoría o de la configuración:

- **T1** Puntuación de Rover: `missions.json` `similarity.score` de Rover, `similarity.json` `real_value.score_by_mission` (nuevo, por misión), `real_value.meaning`, `rule_options.real_value_tolerance`, `texts.similarity_meaning_real_values`, el texto del embudo y la descripción de `s.slope_deg` / `s.roughness_m` en `manifest.json` describen ahora la banda muerta: s = 1 si |d| ≤ sigma y exp(-0,5·max(0, |d|/sigma − 1)²) fuera de ella, sigma 0,265093° y 17,401661 m. Paneles solares y Base lunar conservan su gaussiana sobre la tolerancia.
- **T7** `rover_slope_minimum`: cifras de la regla publicada (`slope_min_study_corrected`): 26 de los 50 primeros serían puntos añadidos, todos con pendiente < 0,5°; celdas de agua en el top 50 de 12 a 25; un gemelo con el 16,4 % frente al 2,6 %.
- **T6** `top5_stability_rover` rellenado (cifras de arriba) y dicho en palabras: qué cinco se muestran no es estable; la pertenencia al grupo empatado, en su mayoría, sí.
- **T4** Nota de la regla de agua: "confirmada por el líder a las 12:10 CET del 15-11-2026" (los tres conjuntos de criterios).
- **T5** Lugares lejanos: la pantalla solo nombra el lugar poblado más cercano a 300 km o menos (si no, país o región y coordenadas); ningún texto del bundle presenta un lugar más lejano como nombre de una celda (comprobado por test sobre todos los textos). Celdas clasificadas con el lugar más cercano a más de 300 km: Rover 2.073 de 10.337, Paneles solares 256 de 6.360, Base lunar 0 de 450. `explain.json` conserva el nombre con su distancia (`nearest_place_km`), sin cambio de campo.
- **T8** `rover_tie` ya no repite la frase de la incertidumbre; la nota de saturación toma como referencia el primer análogo mostrado (número 3 del ranking) y no E3872.
- **F1** `solar_suitability_clouds` (= `known_limitations[6]`): la fracción de cielo despejado es **la mitad** de la idoneidad (peso 0,35 de 0,70, 50 %), no "35 %".
- **F2** La misma nota dice que una de las 3 celdas sin dato (Sulawesi, 4,5 S 122,5 E) es la número 16 con idoneidad 96,23 solo por la renormalización, y que no está entre los cinco.
- **F4** `known_limitations[2]` de Paneles solares reescrita: la irradiancia en el suelo y la geometría solar ya no pesan (la irradiancia solo filtra, ≥ 2,5 kWh/m²/día); criterios: cielo despejado 0,35, pendiente 0,15, amplitud térmica 0,10, rugosidad 0,10.
- **Nota bajo F3** `external_validation_solar`: dentro de la fila de latitud las estaciones no salen mejor (28,8 % frente a 27,9 %); en la clasificación completa sí (8,3 % frente a 14,9 %): no se demuestra que la idoneidad corregida diga más que la latitud sobre estas estaciones.
- `top5_stability_solar` rellenado (cifras de arriba).
- Base lunar: `audit/ra_base_texts.py` sobre el bundle actual; todos los fallos de texto del JSON constan como resueltos en 0486ad9; nada que corregir.
- Tests: `tierra luna/tests/test_texts_reaudit.py` (nuevo); reparados `test_audit_corrections_1.py::test_audio_top5_places_are_unchanged` y `::test_cell_area_caveat_is_recomputed` para comprobar `docs/AUDIO_TOP5.json` actual contra el bundle (lugar más cercano por círculo máximo, distancia redondeada una vez, áreas de celda recalculadas), sin nombres congelados.

### Vídeo de Base lunar (decisión del líder de las 12:26 CET)

15-11-2026: la tarjeta de cierre del vídeo de Base lunar (40-46 s) se volvió a renderizar después de que se corrigieran los criterios de Base lunar y de que la reauditoría independiente los confirmara. El par no cambia (E17538 con M63528, similitud 97,31), pero ahora es el análogo 2 de los cinco mostrados (puesto 3 en el ranking completo, `missions.json` `top5`), con idoneidad 43,15 y final 70,23, en lugar de "par número 1", 47,27 y 72,29. La parte 3D (0-40 s) no se volvió a renderizar, y `prepare.py` rechaza ahora el vídeo si la posición, el puesto o las puntuaciones de la tarjeta difieren del bundle publicado.

### Punto abierto (punto A de la auditoría)

La configuración muerta que la primera pasada no pudo mover con seguridad (la entrada de zona solar "latitude <= -75", las tolerancias de referencia sin uso, la escala por rango agregado) sigue donde está; moverla a un bloque `legacy` exige cambiar lecturas del código y se deja abierta, sin tocar en esta pasada.

## Textos finales: punto 9 de la reauditoría, lector independiente (15-11-2026)

Detalle en `docs/stats_audit/11_textos_finales.md` (script `tierra luna/audit/z_texts_final.py`). Veredicto de textos: Rover, Placas solares y Base lunar GO. Los cinco análogos de cada misión están publicados y en `explain.json`. Corregido en origen, sin cambiar ningún número: la etiqueta de zona "PSR" se escribe en palabras; la fórmula de Rover remitía a un campo inexistente del bundle; "each variable scores lower the further apart" era falso para Rover; `not_used_by_engine.why` decía que la similitud usa los pesos de idoneidad y que estaba pendiente; la nota de saturación de Rover seguía remitiendo "a la reauditoría". Queda anotado, sin corregir: en la ficha de Rover la frase "These are five of the 254 sites tied at the top..." aparece tres veces (known_limitations[3], [7] y top5.rule). Los 30 `.bin` son idénticos a e28283a y a HEAD.


## Texto aprobado modificado tras la reauditoría (15-11-2026): similarity_meaning_real_values

Por qué cambió: el líder decidió a las 11:51 y a las 12:10 CET del 15-11-2026 que Rover puntúa con 1 una diferencia que queda dentro de la incertidumbre de medida de los modelos de elevación (banda muerta: pendiente 0,27°, rugosidad 17,4 m). Con esa decisión, la frase aprobada "each variable scores lower the further apart the two values are" dejaba de ser cierta para Rover (fallo T1 de la reauditoría, `docs/stats_audit/9_reauditoria_rover.json`; relectura independiente en `docs/stats_audit/11_textos_finales.md`). El texto se corrigió en origen (`tierra luna/engine/engine_config.json` `approved_texts.similarity_meaning_real_values`) en las pasadas de texto posteriores a la reauditoría: 4624505 (textos del motor tras la reauditoría, T1) y 3ed19b2 (relectura independiente; es el commit que cambia la frase en `engine_config.json`).

Texto ANTES (aprobado por el líder, punto 8 de arriba; `engine_config.json` en cd14aea):

> "Each Earth point is paired with its lunar twin: the 1-degree lunar cell, inside the mission's target zone, whose real values are closest. Similarity is computed on real values within stated tolerances: every key variable of the twin is within its tolerance of the Earth point and every secondary variable within twice its tolerance, and each variable scores lower the further apart the two values are. Both values and their difference are shown side by side."

Texto DESPUÉS (vigente en `engine_config.json` y en `similarity.json` `texts`):

> "Each Earth point is paired with its lunar twin: the 1-degree lunar cell, inside the mission's target zone, whose real values are closest. Similarity is computed on real values within stated tolerances: every key variable of the twin is within its tolerance of the Earth point and every secondary variable within twice its tolerance, and a variable never scores higher when the two values are further apart. Each mission has its own score rule. Solar panels: the score falls from 1 with the first difference, as exp(-0.5 (difference / tolerance)^2). Rover: a difference within the measurement uncertainty of the elevation models (slope 0.27 degrees, roughness 17.4 m) scores 1, and beyond it the score falls as exp(-0.5 max(0, difference / uncertainty - 1)^2). Both values and their difference are shown side by side."

Ningún número del modelo cambia: solo cambia la redacción; la regla de puntuación descrita es la que ya publica el bundle.

**PENDIENTE DE CONFIRMACIÓN DEL LÍDER.** El líder aprobó la redacción anterior; el cambio de significado (la banda muerta de Rover) es decisión suya, pero la frase nueva la escribió la pasada de textos del motor y la comprobó un lector independiente. El líder aún no ha confirmado esta redacción.

## Audios regrabados (15-11-2026, 14:20 CET, el delegado en nombre del líder)

**Entrega.** A las 14:20 CET el delegado del líder entregó, en nombre del líder, un ZIP con las 19 pistas de la guía de audio que el equipo volvió a grabar (voz Matilda, modelo eleven_multilingual_v2, según él), su `transcripts.json` y su `SHA256SUMS.txt`. SHA256 del ZIP: `cc9699eb9742cedc95f4161b60a0bf2aab9ad2013e25830392311e1922330c35` (comprobado por el director; `sha256sum -c` 19/19 dentro del ZIP). Los ficheros se subieron sin modificar a la rama `audio-assets`, commit `6650a13`, y se copiaron byte a byte a `app/public/audio/` de `final-integration` (`cmp` idéntico en los 19 MP3, `SHA256SUMS.txt` y `transcripts.json`; `sha256sum -c` 19/19 en `app/public/audio/`). Ningún audio se generó, editó, recodificó, recortó, normalizó ni renombró.

**Textos.** Grabados desde los textos finales de `0486ad9` con un único cambio, decidido por el delegado: rover_1 queda "A site in Canada, at 78.5 degrees north and 102.5 degrees west." (antes seguía ", about 1,116 kilometers north of Gjoa Haven"). Comprobado con un script: el `transcripts.json` del equipo solo difiere del del repositorio en esa pista.

**Regla general que sale de ese cambio** (no es un caso especial de una pista): si el lugar poblado más cercano de una celda de la Tierra está más lejos que la distancia a partir de la cual la pantalla no lo nombra (`NEAREST_PLACE_MAX_KM = 300` en `app/src/flow/detailPanel.ts`), la pista da el país (y la región si la celda la tiene) y las coordenadas, y no menciona el lugar. El generador `tierra luna/tools/make_audio_top5.py` lleva ese valor en su configuración con esa fuente y comprueba al ejecutarse que coincide con el de la web; su `transcripts.json` es idéntico byte a byte al del equipo. `docs/AUDIO_TOP5.json` conserva el lugar y su distancia como dato, con `"nearest_named_place_spoken": false`. De las 15 pistas de pareja solo rover_1 (Gjoa Haven, 1.115,8 km) cae fuera; la siguiente más lejana, solar_4 (Gaalkacyo, 131 km), se sigue diciendo. La comprobación independiente `tierra luna/audit/t_audio_texts.py` lee el mismo límite de la web y comprueba la regla (472 comprobaciones, 0 fallos).

**Lo que decidió además el delegado.** Los textos se quedan sin "the five best" (en Rover empatan 254 sitios en lo más alto); "Schrodinger" se queda sin diéresis.

**Comprobaciones del delegado frente a las medidas de aquí** (`tierra luna/audit/a_audio_files.py` → `tierra luna/audit/out/a_audio_files.csv`; ffprobe, ffmpeg volumedetect y silencedetect noise=-50dB:d=1.0):

| | Delegado (según él) | Medido aquí |
|---|---|---|
| Duración | 34,5 a 51,8 s | 34,534 (rover_4) a 51,775 s (base_3) |
| Volumen medio | −22,7 a −23,3 dB | −23,3 a −22,7 dB |
| Pico | ≤ −1,5 dB | −3,2 a −1,5 dB (−1,5 en base_1) |
| Silencios | sin silencios largos | ninguno de 1 s o más al principio ni al final; dentro, dos pausas: 1,45 s en m1_rover (20,15 s) y 1,00 s en m3_base (15,12 s) |
| Formato | — | MP3, 44.100 Hz, mono, 128 kb/s en las 19 |
| Decodificación | — | las 19 se decodifican enteras sin un mensaje de error |

Coinciden en duración, volumen medio y pico; "sin silencios largos" coincide si una pausa de hasta 1,5 s no cuenta como larga. No se ha verificado que las palabras dichas coincidan palabra por palabra con el texto: nadie aquí ha escuchado ni transcrito el audio; el equipo grabó desde el texto y así lo dice.

**Estado.** `app/public/audio/pending.json` tiene la lista vacía (la web reproduce cada pista con la guía activada; una pista en la lista solo mostraría su texto). Nada pendiente de grabar (`docs/AUDIO_RERECORD.md`).

**Despliegue (14:30 CET).** El primer intento, a las 14:09 CET, lo bloqueó Vercel (`TEAM_ACCESS_REQUIRED`: en un repositorio privado de un equipo Hobby el autor del commit desplegado tiene que ser el titular del equipo). El líder añadió su propio commit `0d87802` encima de `e41af38` (una línea en blanco en `app/README.md`) y `scripts/deploy_vercel.sh`, sin cambios, desplegó producción a las 14:30 CET: https://stars-beside-you.vercel.app. Cualquier despliegue posterior necesita que el último commit vuelva a ser del titular de la cuenta. Comprobación independiente de la integración: `docs/stats_audit/15_audios_integrados.md`.


## Frases del par en lenguaje llano (15-11-2026, 19:50 CET, el delegado en nombre del líder)

**Orden.** El líder, a través de su delegado (opción (a); su punto 18: sin jerga), manda reescribir en lenguaje llano las dos frases del par que salen en la tarjeta del par de la web: la de Placas solares (`approved_texts.solar_limitation`) tal como se propuso, y la de Base lunar con sus propias palabras, sin «kelvin»: una diferencia en kelvin es la misma en grados Celsius, así que las dos cifras que antes se escribían «K colder» y «K larger» se escriben ahora en °C. Mismas cifras; nada más cambia.

**Placas solares (`solar_limitation`), plantilla por par.** Antes:

> "This pair is matched on sunlight above the atmosphere: {toa_earth} kWh/m²/day at the top of Earth's atmosphere here and {toa_moon} kWh/m²/day on the lunar surface. At the Earth site only {ground_earth} of those {toa_earth} kWh/m²/day reach the ground ({loss_pct} % is lost in the atmosphere), while the Moon has no atmosphere and its day lasts {lunar_day} Earth days, about half of them in darkness. Terrain (slope and roughness) is a secondary criterion."

Después:

> "Both places get about the same sunlight before it passes through any air: {toa_earth} here and {toa_moon} on the Moon, in kilowatt-hours per square metre each day. Here only {ground_earth} of those {toa_earth} reach the ground: the air takes {loss_pct} %. The Moon has no air, but its day lasts {lunar_day} Earth days, about half of them dark. How sloped and rough the ground is counts less."

Mismos marcadores y misma regla de presentación: `{toa_earth}`, `{toa_moon}` y `{ground_earth}` con 1 decimal; `{loss_pct}` calculado de los dos números impresos (regla `share_lost_of_displayed_tenths`); `{lunar_day}` = 29.5 al construir. La plantilla no tiene variantes. Primera analogía de la web (E40184): "Both places get about the same sunlight before it passes through any air: 9.3 here and 9.4 on the Moon, in kilowatt-hours per square metre each day. Here only 5.7 of those 9.3 reach the ground: the air takes 39 %. The Moon has no air, but its day lasts 29.5 Earth days, about half of them dark. How sloped and rough the ground is counts less." «About the same» es cierto en los 6.360 pares: la diferencia guardada es como mucho 0,57 kWh/m²/día (tolerancia de la misión: 0,6) y la impresa como mucho 0,5.

**Base lunar (`lunar_base_pair_sentence`), plantilla por par.** Antes:

> "This pair matches by relative thermal position, not by equal temperatures: this site's coldest temperature and daily swing rank among Earth's lunar-base candidates where its twin's rank among the cells of NASA's nine candidate landing regions near the lunar south pole. In real values the twin is {temp_diff_k} K colder on average (minimum {tmin_moon_c} °C at the surface against {tmin_earth_c} °C air temperature here) and its day-night swing is {amp_diff_k} K larger; slope differs by {slope_diff}° and roughness by {rough_diff} m."

Después:

> "These two places are not equally cold. They match because each holds a similar place in its own world's ranking, from mildest to coldest and from steadiest to most changeable. The twin is {temp_diff_k} °C colder, and its temperature swings {amp_diff_k} °C more between day and night."

`{temp_diff_k}` y `{amp_diff_k}` son las mismas columnas (`info.temp_k.diff`, `lst_diurnal_amp_k.diff`) con el mismo redondeo (0 decimales, `toFixed` del float32 guardado). Las demás cifras de la frase anterior (mínimo de la gemela y del punto, diferencias de pendiente y de rugosidad) ya no se imprimen en la frase: siguen en las líneas clave de la tarjeta y en «More details»; sus marcadores siguen declarados en la plantilla, sin usarse en el texto, para no tocar ningún número del paquete. La plantilla no tiene variantes. «Colder» y «more» son ciertos en los 450 pares: en todos la gemela es más fría (diferencia mínima 143 K) y su oscilación diaria es mayor (diferencia mínima 107 K). Primera analogía de la web (E21054): "These two places are not equally cold. They match because each holds a similar place in its own world's ranking, from mildest to coldest and from steadiest to most changeable. The twin is 163 °C colder, and its temperature swings 158 °C more between day and night."

**Qué no cambia.** Ningún número del modelo: los 30 `.bin` del paquete tienen el mismo sha256 que en `d3a4862`; en `explain.json` solo cambian las 50 frases `pair_sentence` (25 por misión), en `similarity.json` solo esos dos textos y en `manifest.json` solo los sha256 y tamaños de esos dos ficheros, los totales de tamaño y el sha256 de `engine_config.json`. Las cifras de las cinco primeras analogías de cada misión son las mismas que en la frase anterior (en Base lunar, las dos que siguen impresas).

**Consecuencia.** Las tarjetas finales de los VÍDEOS de Placas solares y de Base lunar citan la redacción anterior de la frase del par: los vídeos se renderizaron antes de este cambio y no se vuelven a renderizar. Sus cifras son las mismas.
