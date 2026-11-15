# Auditoría 2: normalización y similitud (punto 3), top 5 (punto 4), unidades y saturación (punto E)

Auditor independiente (no ha escrito nada del motor ni del paquete). 15-11-2026. Rama `final-integration`, motor en el commit `42d8bba`, paquete `app/public/data/v2` (contrato revisión 6). No se ha cambiado nada del repositorio fuera de `tierra luna/audit/p2_*.py`, `tierra luna/audit/out/p2_*` y este documento. Ningún audio tocado. Sin red.

**Cómo repetirlo** (cada uno es determinista; el segundo y el tercero leen la salida del primero):

```
PY=/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/bin/python
$PY "tierra luna/audit/p2_recompute.py"     # punto 3: ~2 min  -> out/p2_recompute.json, out/p2_pairs_<misión>.csv
$PY "tierra luna/audit/p2_contract_sum.py"  # punto 3: similitud desde s.<v> con la fórmula del contrato -> out/p2_contract_sum.json
$PY "tierra luna/audit/p2_top5.py"          # punto 4 -> out/p2_top5.json
$PY "tierra luna/audit/p2_units.py"         # punto E y tabla -> out/p2_units.json, out/p2_table.csv
```

**Independencia.** `p2_common.py` decodifica los binarios del paquete con su propio lector (offsets del `manifest.json`, `q / divisor`). `p2_model.py` reimplementa embudo, idoneidad, variables derivadas, zonas, percentiles, filtro, gemelo, similitud, final y rango **sin importar el motor**, con métodos distintos a propósito: percentiles con `scipy.stats.rankdata(method="average")` (el motor usa su propio bucle); irradiancia sobre la atmósfera por integración numérica en el ángulo horario con Kepler resuelto por Newton (el motor usa la fórmula cerrada y punto fijo); zona de Base lunar por intersección de cada cuadrado de 1° con los nueve polígonos (shapely); gemelo como "máximo y, entre los empatados a 1e-12, el id más bajo" (el motor usa `argmax`). Distancias: haversine propia, R = 6.371 km.

---

## Punto 3. Normalización y similitud — **GO**

### 3.1 Fórmulas, término a término

| término | implementado (fichero:línea) | documentado | ¿coinciden? |
|---|---|---|---|
| puntuación por variable | `s = exp(-0.5 (d/τ)²)`, `d = |Tierra − Luna|` (`engine/real_similarity.py:229-231`, y a precisión completa para elegir gemelo en `:293`) | DECISIONS.md:45; ASSUMPTIONS.md:142; DATA_CONTRACT.md:273 y :541-544; `similarity.json` `real_value.score` y `percentile_and_real.score` | sí |
| similitud | `100 · Σ w·s / Σ w` sobre variables con valor en los dos lados, en el orden de la lista (`real_similarity.py:234-243`) | DATA_CONTRACT.md:544; `similarity.json` `percentile_and_real.similarity` | sí |
| filtro | clave `d ≤ 1·τ` (falta → falla), secundaria `d ≤ 2·τ` (falta → fuera y renormaliza) (`real_similarity.py:246-253`, multiplicadores en `engine_config.json` `real_value_similarity.filter_bound_multiplier`) | DECISIONS.md:45; ASSUMPTIONS.md:143, :178 | sí |
| gemelo | celda de la zona que pasa el filtro con la similitud más alta a precisión doble; empate → id más bajo (`real_similarity.py:295-299`, `argmax` = primer máximo sobre ids crecientes, comprobado en `:275`) | ASSUMPTIONS.md:144; DECISIONS.md:45 | sí |
| puntuaciones publicadas | `rint(s·1e6)/1e6` (`real_similarity.py:223-226`); la similitud publicada sale de ellas (`:327-330`) | DATA_CONTRACT.md:273, :562 | sí |
| percentil (Base lunar) | `100 (rango − 0,5)/n`, rangos 1..n ascendentes, empates promediados (`real_similarity.py:65-86`); Tierra = los que pasan el embudo, Luna = celdas de la zona (`engine/pipeline.py:331-338`) | ASSUMPTIONS.md:173-174; DATA_CONTRACT.md:30, :300; `similarity.json` `percentile_and_real.why` | sí |
| final | `α·similitud + (1−α)·idoneidad`, α = 0,5, con similitud sin redondear (desde `s` de 6 decimales) e idoneidad sin redondear (desde utilidades de 6 decimales) (`tierra luna/mission_scoring.py:207-211`, llamado en `pipeline.py:367-370`; `engine_config.json` `mix_factor`) | DECISIONS.md:16, :45; ASSUMPTIONS.md:145; DATA_CONTRACT.md:554; `missions.json` `alpha_why` | sí |
| rango | `round(final, 2)` con `round` de Python, descendente, empate → id de la Tierra ascendente (`pipeline.py:79-87`, `:371-372`; `engine/suitability.py:57-61`) | DATA_CONTRACT.md:555 | sí |

**Pesos.** Suman 1 en las tres misiones y la parte clave es 0,8 en las tres (`out/p2_recompute.json` `weights`): Rover 0,4 / 0,4 / 0,2; Paneles 0,8 / 0,1 / 0,1; Base lunar 0,4 / 0,4 / 0,1 / 0,1. Iguales en `engine_config.json`, en `missions.json` (`bundle_weights`, con tolerancia, cota y escala) y en DECISIONS.md:25, :46, :48. Tolerancias y cotas del paquete: Rover 2° / 30 m / 500 m (cotas 2, 30, 1.000); Paneles 0,6 kWh/m²/día / 2° / 30 m (cotas 0,6, 4, 60); Base lunar 10 / 10 puntos de percentil / 2° / 30 m (cotas 10, 10, 4°, 60 m).

### 3.2 Recalculado con código propio, todos los puntos

`out/p2_recompute.json` (por punto: `out/p2_pairs_<misión>.csv`):

| | Rover | Paneles | Base lunar |
|---|---|---|---|
| puntos que pasan el embudo (propio = paquete, mismo conjunto) | 10.337 | 18.777 | 2.419 |
| celdas de la zona (propio = regiones de `moon_base.bin`) | 5.400 | 6.686 | 280 (las 280 con área de solape > 0; ninguna solo "toca") |
| puntos con gemelo (propio = paquete) | 10.192 | 6.360 | 450 |
| gemelo recalculado desde cero, distinto del paquete | **0** | **0** | **0** |
| gemelo fuera de la zona | 0 | 0 | 0 |
| pares que violan el filtro (clave / secundaria) | 0 / 0 | 0 / 0 | 0 / 0 |
| máximo de diferencia / cota en los pares | pendiente 0,986; rugosidad 0,999; elev. rel. 0,99999 | irradiancia 0,949; pendiente 0,485; rugosidad 0,969 | tmin 0,979; amplitud 0,995 (puntos de percentil); pendiente 0,979; rugosidad 0,997 |
| `s.<v>` distinto (tolerancia 5e-7) | 0 | 244 en la irradiancia, todos de 1e-6 (ver nota) | 0 |
| similitud, idoneidad, final (2 decimales) y rango | ver 3.3 | ver 3.3 | ver 3.3 |
| valores reales Tierra / Luna / diferencia de `*_pairs.bin` | iguales | iguales (≤ 1e-6 kWh) | iguales; percentiles a ≤ 4e-6 puntos |

Nota de Paneles: mi integral numérica de la irradiancia sobre la atmósfera difiere de la fórmula cerrada del motor en 9,4e-7 kWh/m²/día como máximo (`toa_formula_vs_bundle_rows`); eso mueve el sexto decimal de la puntuación en 244 filas. No es un fallo: es la precisión de mi método. Ecuador (fila 0,5°): 9,97393 propio frente a 9,97393 del paquete.

Base lunar, poblaciones: Tierra 2.419 puntos (todos con valor de las dos variables), Luna 280 celdas (todas con valor). Empates: en la Tierra 800 filas repiten un valor de `tmin` ya visto y 1.435 de amplitud (WorldClim y MODIS se guardan con 2 decimales); en la zona lunar 15 y 7. La regla de rango medio los promedia (comprobado con `rankdata`, que es otra implementación). El percentil lunar sale idéntico desde `tmin_c + 273,15` y desde la columna `tmin_k` de la tabla lunar (0 celdas distintas). Pendiente y rugosidad entran en valores reales (`scale: real`, comprobado en los pares: `slope_deg.diff`, `roughness_m.diff` en grados y metros).

Empates del gemelo: Rover y Base lunar no tienen ninguno exacto; Paneles tiene 3 filas con dos celdas exactamente empatadas en la mejor similitud (las resuelve el id más bajo, como dice la regla) y 1 fila en la que las puntuaciones publicadas de 6 decimales preferirían otra celda (el motor elige a precisión completa, como está documentado). Diferencia entre la mejor y la segunda celda, mediana: Rover 1,59 puntos, Paneles **0,0042**, Base lunar 4,04 (ver punto E, saturación).

### 3.3 Redondeo a 2 decimales

El paquete reproduce **exactamente** su similitud almacenada desde sus propias `s.<v>` con la fórmula del contrato (suma en el orden de `similarity.variables`, `round` de Python): 0 diferencias en 10.192 + 6.360 + 450 pares (`p2_contract_sum.py`). Una primera pasada mía daba diferencias de 0,01 en mitades exactas porque `round()` sobre un `numpy.float64` redondea como `numpy.round`; corregido en mis scripts (`round(float(x), 2)`). Resultado tras la corrección (`out/p2_recompute.json`, `similarity_2dp`, `suitability_2dp`, `final_2dp`, `rank`, comparados a la precisión publicada):

| | Rover | Paneles | Base lunar |
|---|---|---|---|
| similitud distinta (de puntos que pasan) | 0 de 10.337 | 6 de 18.777 | 0 de 2.419 |
| idoneidad distinta | 0 | 0 | 0 |
| final distinto | 0 | 1 | 0 |
| rango distinto | 0 | 6 | 0 |

Los 6 + 1 de Paneles son la precisión de mi irradiancia (nota de 3.2): son valores a menos de 1e-4 de una mitad del segundo decimal (p. ej. 89,25496 que el paquete publica 89,26), y el final distinto (E21426, 90,144975) cae en un grupo de seis puntos empatados a 90,15 en los rangos 4.147-4.152, que es donde se reordenan los 6 rangos. Ningún punto de los 100 primeros de ninguna misión cambia. Con mi idoneidad, mi similitud y mi final, el top 5 de las tres misiones es idéntico al del paquete.

### 3.4 Fallos (documentación; no cambian ningún criterio)

1. **DECISIONS.md:14-15 ("Vocabulario mínimo") sigue definiendo la similitud con la fórmula z antigua**: `100 × exp(−0,45 × d)` con `d = √(Σ peso × (z Tierra − z Luna)²)` y "Gemelo: la celda lunar ... con la similitud más alta" (sin filtro). Ninguna misión usa ya esa fórmula. Corrección: sustituir esas dos líneas por la fórmula vigente (`s = exp(−0,5 (d/τ)²)`, similitud = 100 × media ponderada, filtro clave ≤ τ y secundaria ≤ 2τ, gemelo = la mejor celda de la zona que pasa el filtro; Base lunar: claves en percentil dentro de su población) y dejar la z como histórica.
2. **DATA_CONTRACT.md:562-563** dice en dos frases seguidas que la similitud se guarda con `round` de Python (correcto para las tres misiones enviadas: `engine/export_v2.py:97-100`, `:1292`) y que "similarity uses numpy.round as analog_finder does" (solo vale para las reglas z, que no se envían). Corrección: añadir "(reglas z: zone_twin, repo_global_mean)" a la segunda frase. Para quien reimplemente en Python: `round(np.float64(x), 2)` no es `round(float(x), 2)`.

---

## Punto 4. El top 5 — **GO** para los lugares (son los que da la regla decidida), con una corrección de texto y dos cuestiones de diseño

### 4.1 Por qué cantidad se ordena

- Implementado: por el **final** publicado (2 decimales), desempate por id (`pipeline.py:79-87`, `:371-372`). Comprobado en el paquete: el rango almacenado es exactamente el orden de `final` descendente con desempate por id, 1..n sin huecos, en las tres misiones (`out/p2_top5.json` `rank_follows_final_desc_then_id: true`).
- Dicho al usuario: `AUDIO_TOP5.json` `how_to_read.final`: "The ranking score: half similarity and half suitability"; `missions.json` `similarity.list_rule`: "paired points by rank ...". Los audios de misión (`m1_rover.mp3`, `m2_solar.mp3`, `m3_base.mp3`) dicen "Here are the five best analogs" y cada audio de par cita **solo la similitud**; ninguno dice que el orden mezcla similitud e idoneidad.
- Consecuencia: el orden que oye el usuario no es el de la similitud que se le cita. Rover: 99,57 / 99,76 / **98,77** / 99,50 / 99,12; Paneles: 99,99 / **99,88** / 99,95 / 99,98 / **100**; Base lunar: 97,31 / 96,61 / 96,86 / **99,36** / 95,03. Si se ordenara por similitud, el top 5 sería otro en las tres misiones: Rover E9520 (similitud 100,0) está en el puesto 1.112; Paneles tiene 514 pares con similitud publicada 100,00 y el primero por id está en el 4.129; Base lunar E18430 (99,48) está en el 100 (`top5_by_similarity_instead`).
- Los cinco pares de cada misión de `AUDIO_TOP5.json` son exactamente los rangos 1-5 del paquete (Tierra y gemelo, 15 de 15), y las similitudes citadas en las 15 transcripciones son las del paquete.

**Fallo (texto, sin cambio de criterio):** decir qué significa "best". Propuesta: en la web, junto a la lista y al reproductor, "Ordered by overall score: half how alike the two places are, half how well the Earth site suits the mission"; en `AUDIO_TOP5.json` y los textos de la web, "five best-ranked analogs". **No exige volver a grabar** si la web lo dice al lado del audio; si se quiere que el audio sea autosuficiente, bastaría regrabar las tres pistas de introducción (`m1_rover`, `m2_solar`, `m3_base`), no las 15 de pares. Decisión del líder.

### 4.2 Empates

| | Rover | Paneles | Base lunar |
|---|---|---|---|
| filas del top 5 que comparten su final publicado con otra | 0 | 0 | 0 |
| grupos de empate en el top 20 (rangos) | ninguno | 9-10, 12-13, 15-16, 17-20 | ninguno |
| final del 5.º / 6.º (publicado) | 98,91 / 98,87 | **98,24 / 98,23** | 71,28 / 71,24 |
| final del 5.º / 6.º sin redondear | 98,9077 / 98,8684 | 98,2365 / 98,2328 | 71,2832 / 71,2383 |

La regla de desempate no decide ningún miembro de ningún top 5. En Paneles el 5.º y el 6.º están a 0,0038 puntos sin redondear (0,01 publicado): el 6.º (E38385, Madagascar) entraría con cualquier cambio mínimo de entrada (punto F de otro auditor). El redondeo crea empates (Paneles: 5.735 de 6.360 finales publicados comparten valor con otro, frente a 10 a precisión completa; Rover 9.512 frente a 14; Base lunar 98 frente a 0) y los resuelve el id; en el top 5 no hay ninguno.

### 4.3 Duplicados y casi duplicados

Ninguna misión repite celda en su top 5. Distancias entre los cinco (km, círculo máximo sobre la Tierra, `top5_distance_km`):

**Rover** (1 E17566 Mongolia Interior, 2 E23945 Argelia, 3 E18282 y 4 E18280 Gansu, 5 E15395 Mongolia):

| | 2 | 3 | 4 | 5 |
|---|---|---|---|---|
| 1 | 9.157 | 405 | 554 | 1.097 |
| 2 | | 8.936 | 8.777 | 8.106 |
| 3 | | | **172** | 1.053 |
| 4 | | | | 976 |

El 3.º y el 4.º están a dos celdas (39,5 N 102,5 E y 100,5 E) y la celda que hay entre ellos, E18281, es el 6.º.

**Paneles** (1 E38464, 2 E38105, 4 E37746, 5 E38465: Kimberley, Australia; 3 E38744 Madagascar):

| | 2 | 3 | 4 | 5 |
|---|---|---|---|---|
| 1 | 154 | 8.436 | 309 | **107** |
| 2 | | 8.567 | **155** | **111** |
| 3 | | | 8.700 | 8.539 |
| 4 | | | | 247 |

Cuatro de los cinco están en un bloque de 3 × 3 celdas (14,5-16,5 S, 124,5-126,5 E) del noroeste de Australia; son celdas vecinas (comparten lado o esquina): 1-2, 1-5, 2-4 y 2-5. En la práctica es una sola región contada cuatro veces (tres nombradas "de Derby" y una "de Kununurra").

**Base lunar** (1 E17538, 2 E16830, 5 E17187 Xinjiang; 3 E15751 Mongolia; 4 E21054 Marruecos): mínimo 268 km (2-5), sin celdas vecinas.

**Cuestión de diseño (no aplicada): separación mínima entre los cinco.** Lista voraz por rango saltando todo punto a menos de la distancia dada de uno ya elegido (`min_separation_alternatives`):

| misión | regla | top 5 (rangos) | miembros que cambian | final perdido por el 5.º | suma de finales perdida |
|---|---|---|---|---|---|
| Rover | ≥ 2° (222 km) | 1, 2, 3, 5, 7 | 1 | 0,10 | 0,27 |
| Rover | ≥ 500 km | 1, 2, 4, 5, 8 | 1 | 0,12 | 0,38 |
| Rover | ≥ 1.000 km | 1, 2, 5, 11, 15 | 2 | 0,50 | 1,14 |
| Paneles | ≥ 2° (222 km) | 1, 3, 4, 7, 9 | 2 | 0,08 | 0,28 |
| Paneles | ≥ 500 km | 1, 3, 7, 9, 12 | 3 | 0,13 | 0,47 |
| Paneles | ≥ 1.000 km | 1, 3, 9, 12, 22 | 3 | 0,23 | 0,65 |
| Base lunar | ≥ 2° (222 km) | 1, 2, 3, 4, 5 | 0 | 0 | 0 |
| Base lunar | ≥ 500 km | 1, 2, 4, 6, 9 | 2 | 0,37 | 0,86 |
| Base lunar | ≥ 1.000 km | 1, 2, 4, 6, 17 | 2 | 1,83 | 2,32 |

Con 2° se pierde menos de 0,3 puntos de final en total en cualquier misión. Cambiarlo cambia el orden del ranking que se enseña: lo decide el líder. Si se aplicara a Paneles o Rover, cambiarían pistas de audio (Paneles 2 y 5, Rover 4 con 2°).

### 4.4 Los cinco pares del Rover comparten gemelo (M59895, 76,5 S 44,5 O)

Para cada uno de los cinco, con mi implementación (`rover_one_twin.per_point`):

| rango | Tierra (pend., rug., elev. rel.) | celdas de la zona con pend. y rug. dentro de tolerancia | celdas que pasan el filtro completo | 1.ª celda | 2.ª y 3.ª celda por similitud (no pasan) |
|---|---|---|---|---|---|
| 1 E17566 | 1,04°, 43,5 m, +737 m | 244 | **1** | M59895 99,57 (s = 0,998 / 1,000 / 0,982) | M59717 79,99 (elev. rel. a 5.186 m); M63305 79,97 (3.689 m) |
| 2 E23945 | 1,22°, 43,4 m, +762 m | 244 | **1** | M59895 99,76 | M60062 79,99 (4.581 m); M60059 79,96 (4.483 m) |
| 3 E18282 | 0,91°, 38,8 m, +748 m | 219 | **1** | M59895 98,77 | M60064 79,93 (4.592 m); M59699 79,93 (4.618 m) |
| 4 E18280 | 1,13°, 48,9 m, +851 m | 277 | **1** | M59895 99,50 | M60793 79,99 (4.802 m); M63360 79,98 (3.475 m) |
| 5 E15395 | 1,24°, 41,3 m, +962 m | 232 | **1** | M59895 99,12 | M63455 79,98 (3.172 m); M60574 79,96 (5.438 m) |

Por qué: el Rover premia en la idoneidad el terreno llano y poco rugoso (`mission_scoring.json` rover soft: pendiente a 300 m peso 0,45, bueno 1°; rugosidad a 300 m peso 0,30), así que su cabeza son mesetas suaves y altas (top 100: pendiente mediana 1,24°, rugosidad 47,7 m, elevación relativa mediana +506 m). En el polo sur lunar las celdas tan suaves son raras (M59895 está en el percentil 1,8 de pendiente y 1,9 de rugosidad de las 5.400 celdas; mediana de la zona 6,4° y 198 m; solo 159 celdas con pendiente ≤ 2° y rugosidad ≤ 60 m) y casi todas son fondos de cráter, 3-5 km por debajo de la media lunar. M59895 es la única de ellas alta (+833 m, percentil 84 de elevación). La elevación relativa es secundaria con cota 1.000 m: las otras ~240 celdas suaves quedan a 3.200-5.400 m y no pasan. Sin la cota, el segundo mejor tendría 79,9-80,0 (las dos claves casi perfectas y la elevación con puntuación 0).

Es consecuencia de la regla decidida (secundaria ≤ 2τ = 1.000 m), **no de un fallo**. El Rover tiene 401 gemelos distintos; el más usado es M61116 (79,5 S 96,5 E) con 2.033 puntos (19,9 %); M59895 es el segundo, con 1.873 (18,4 %), y es el gemelo de los 20 primeros y de 59 de los 100 primeros (`twins`). Cinco gemelos distintos exigirían bajar hasta los rangos 1, 25, 35, 45 y 59 (7,74 puntos de final perdidos en suma): cuestión de diseño, no recomendada sin decisión. Paneles y Base lunar ya tienen cinco gemelos distintos en su top 5 (1.704 y 103 gemelos distintos; máximo 2,5 % y 5,6 %).

El audio `m1_rover.mp3` lo dice ("All five analogs share the same lunar twin"). Correcto.

---

## Punto E. Unidades, escalas, fórmulas y saturación — **NOT YET** (falta decir al usuario que la similitud de Paneles está saturada; el resto, correcto)

### E.1 De la columna cruda al número mostrado

| magnitud | Tierra | Luna | conversión y comprobación |
|---|---|---|---|
| temperatura mínima | WorldClim 2.1 `tmin`: mínimo de los 12 meses de la media mensual de las mínimas diarias, °C, media de celda (`real_data/build_earth.py:387-396`, `:540`) → `+273,15` (`engine_config.json` `real_value_similarity.variables.tmin_k`) | Diviner GCP: mínimo del ciclo diurno, K (`build_moon.py:604-621`), guardado también como `tmin_c = tmin_k − 273,15` y devuelto a K por el motor | en los 450 pares `tmin_k.earth = tmin_c + 273,15` (máx. 1,5e-5 K, float32) y `tmin_k.moon = tmin_k` de la tabla lunar (máx. 3,7e-6 K). Toda resta se hace en K. La frase de cada par da las dos mínimas en °C (`tmin_k.* − 273,15`, `similarity.json` `lunar_base_pair_sentence.placeholders`) y las diferencias en K: coherente |
| amplitud térmica | MODIS MOD11A2: media anual de LST día (≈10:30) − noche (≈22:30), K (`build_earth.py:300-332`) | Diviner: máximo − mínimo del ciclo, K | resta en K; diferencias en K |
| irradiancia (Paneles) | sobre la atmósfera: fórmula de latitud, media anual de la media diaria sobre superficie horizontal, W/m² × 24/1000 → kWh/m²/día (`real_similarity.py:90-119`) | superficie (= sobre la superficie, sin atmósfera), `S0 · <max(0, sen h)> · 24/1000`, horizontal, por día terrestre de 24 h, a 1 ua (`build_moon.py:594-598`) | **las dos son la misma magnitud**: media diaria (no pico) sobre horizontal sin atmósfera. 1 kWh/m²/día = 41,67 W/m² de media; la tolerancia 0,6 = 25 W/m². Ecuador: Luna 10,395 (= S0/π · 0,024 = 10,397, menos la oblicuidad de 1,54°); Tierra 9,974 (menor por la oblicuidad de 23,44°). Rango en los pares: Tierra 8,48-9,97, Luna 9,05-10,02 |
| irradiancia en el suelo (solo informativa) | WorldClim `srad` kJ/m²/día × días del mes / 365,25 / 3.600 → kWh/m²/día (`build_earth.py:395`) | — | `atm.lost_share = 1 − suelo/tope` comprobado (máx. 7e-8); mediana 45,3 % |
| pendiente | `slope_iso_deg`, grados, ETOPO, base E-O igual a N-S | `slope_iso_deg`, grados, LOLA | grados en todo: tablas, tolerancias (2°, cota 4°), puertas e idoneidad de `mission_scoring.json` (`*_deg`). Ninguna fuente usa porcentaje (2° = 3,49 %; 4° = 6,99 %) |
| rugosidad | RMS de diferencia de altura a un desfase de ~1,9 km, m | ídem (LDEM_16) | metros en los dos; misma definición (`variables[].sides`) |
| elevación relativa (Rover) | `elevation_m` − media cos(lat) de las 25.245 celdas con valor (tierra): **+695,9 m** | `elevation_m` − media cos(lat) de las 64.800 celdas: **−248,4 m** | coincide con `missions.json` `sides.body_mean` |

### E.2 ¿Se comparan magnitudes que no son lo mismo? ¿Se dice donde se muestra?

1. **Base lunar, temperatura mínima: aire (Tierra, modelado) frente a superficie (Luna, medida), y además dos estadísticos distintos** (media mensual de mínimas diarias del mes más frío frente a mínimo del ciclo). La comparación es de posición (percentil), no de valor, y el paquete lo dice donde se muestra: `missions.json` `similarity.variables[tmin_k].sides` ("modelled AIR temperature ... Diviner SURFACE temperature") y la frase de cada par ("minimum ... °C at the surface against ... °C air temperature here"). **Dicho.**
2. **Base lunar, amplitud: 10:30 − 22:30 (Tierra) frente a máximo − mínimo (Luna).** La Tierra queda infravalorada; el paquete lo dice en `sides` ("understates the daily range"). La frase de cada par dice solo "its day-night swing is X K larger" (en los 450 pares la lunar es mayor: 123-202 K frente a 15-25 K; comprobado). Sugerencia de texto (sin cambio de criterio): añadir "(Earth: satellite day minus night)" en la frase.
3. **Paneles: tope de la atmósfera frente a superficie lunar sin atmósfera.** Es la misma magnitud (ver E.1); la pérdida en la atmósfera de la Tierra se enseña par a par (`texts.solar_limitation`) y en los audios ("only 6.2 kilowatt-hours reach the ground, 35 percent less"). **Dicho.**
4. **Rover, elevación relativa: referencias distintas.** En la Tierra la "media del cuerpo" es la media de las celdas de tierra firme (+695,9 m), no del planeta ni el nivel del mar; en la Luna, de todo el cuerpo. Los audios dicen "height above each world's average level", que para la Tierra se entenderá como el nivel del mar. Además la media de la Tierra pesa por cos(lat) y no por fracción de tierra: entran 3.023 celdas con menos de un 30 % de tierra, una de ellas con −2.569,9 m (17,5 S 177,5 O, fracción de tierra 0,0002, físicamente no es un valor de tierra firme). Pesando por fracción de tierra la media sería +810,7 m (115 m más); con solo las celdas con fracción ≥ 0,3, +785,8 m. La regla escrita ("every Earth cell with a value") es la que se aplica, así que **no es un fallo de código**: cambiar la referencia es un cambio de diseño (variable secundaria, tolerancia 500 m; no se ha medido su efecto en los gemelos). Corrección de texto sin cambio de criterio: en la web, "height above the average land level (Earth) / the average level of the whole Moon".

### E.3 Percentiles

En la población declarada, sobre la variable declarada y con la regla declarada (punto 3.2). Qué haría otra población (`out/p2_units.json` `units.lunar_base`): si el percentil de la Tierra se calculara sobre todas las celdas de tierra con valor (25.484 para `tmin`, 18.738 para la amplitud) en vez de los 2.419 candidatos, la posición de los 450 puntos emparejados se movería una mediana de +14,4 puntos en `tmin` (el 63 % más de 10 puntos, la tolerancia) y +52,3 en amplitud (el 99,6 % más de 10): los pares cambiarían casi todos. En la Luna, con todo el polo sur (5.400 celdas) en vez de las 280, la posición de los gemelos se movería una mediana de −3,3 puntos. El parecido de Base lunar es por tanto "posición entre los candidatos del embudo", y así lo dicen `similarity_meaning_lunar_base` ("where the point ranks among Earth's lunar-base candidates") y la frase de cada par. **Dicho.**

### E.4 Saturación: ¿99,99 y 100 son parecido real?

Distribución de la similitud publicada sobre todos los pares (`saturation`):

| | Rover (10.192) | Paneles (6.360) | Base lunar (450) |
|---|---|---|---|
| P10 / mediana / P90 / máx. | 81,12 / 93,29 / 99,24 / 100,00 | 88,04 / **99,93** / 99,99 / 100,00 | 75,42 / 87,40 / 96,00 / 99,48 |
| ≥ 99 | 14,1 % (1.432) | **78,0 %** (4.960) | 1,6 % (7) |
| ≥ 99,9 | 0,6 % | **61,7 %** | 0 |
| ≥ 99,99 | 0,04 % | **17,7 %** | 0 |
| publicada 100,00 | 1 | **514 (8,1 %)** | 0 |
| se vería "100.0" con un decimal (≥ 99,95) | 0,2 % | **39,9 %** | 0 |
| valores distintos a 2 decimales / a precisión completa | 2.519 / 10.125 | **247** / 5.249 | 414 / 450 |
| celdas de la zona que pasan el filtro por punto (mediana; P90) | 21; 243 | **1.844; 3.648** | 4; 11 |
| celdas con similitud ≥ 99 por punto (mediana; P90) | 0; 1 | **76; 235** | 0; 0 |
| similitud mediana de las celdas que pasan (mediana por punto) | 78,7 | 86,1 | 80,8 |
| mejor − segunda (mediana) | 1,59 | **0,0042** | 4,04 |

Diferencia real que corresponde a una similitud de 99 / 99,9 / 99,99, (a) si solo difiere esa variable, (b) si todas difieren la misma fracción r de su tolerancia (r = 0,142 / 0,045 / 0,014):

| variable (τ) | (a) 99 | (a) 99,9 | (a) 99,99 | (b) 99 | (b) 99,9 | (b) 99,99 |
|---|---|---|---|---|---|---|
| Rover pendiente (2°) | 0,45° | 0,14° | 0,045° | 0,28° | 0,089° | 0,028° |
| Rover rugosidad (30 m) | 6,8 m | 2,1 m | 0,67 m | 4,3 m | 1,3 m | 0,42 m |
| Rover elev. rel. (500 m) | 160 m | 50 m | 16 m | 71 m | 22 m | 7,1 m |
| Paneles irradiancia (0,6) | 0,095 | 0,030 | 0,0095 kWh/m²/día | 0,085 | 0,027 | 0,0085 |
| Paneles / Base lunar pendiente (2°) | 0,92° | 0,28° | 0,090° | 0,28° | 0,089° | 0,028° |
| Paneles / Base lunar rugosidad (30 m) | 13,8 m | 4,4 m | 1,4 m | 4,3 m | 1,3 m | 0,42 m |
| Base lunar tmin y amplitud (10 puntos) | 2,25 | 0,71 | 0,22 puntos | 1,42 | 0,45 | 0,14 puntos |

Lectura:

- **Paneles está saturada, y conviene decirlo así.** La variable clave depende solo de la latitud en los dos cuerpos: 90 valores distintos en los 18.777 puntos de la Tierra (34 en los 6.360 emparejados) y 30 en las 6.686 celdas de los mares (`units.solar`). Cada punto tiene una mediana de 1.844 celdas que pasan el filtro y 76 con similitud ≥ 99; el máximo sobre miles de celdas casi siempre encuentra una de la misma banda de sol con un terreno llano igual al de la Tierra. Un 99,99 significa diferencias reales de centésimas de kWh/m²/día, de centésimas de grado y de menos de 1,5 m: diferencias reales pequeñas, sí, pero conseguidas eligiendo la mejor de miles; no distinguen un lugar de otro. En la cabeza del ranking la similitud no ordena: top 100 con similitud 99,88-100,00 e idoneidad 95,18-96,90; Spearman del final con la idoneidad 0,995 y con la similitud 0,15; la similitud explica el 0,7 % de la varianza del final en el top 100 (`what_orders_the_top`). El top 5 de Paneles es, en la práctica, el top 5 de idoneidad entre los puntos con gemelo.
- **Rover no está saturada en general** (mediana 93,3; 14 % ≥ 99) pero la cabeza sí está alta (top 5 entre 98,77 y 99,76): ahí el orden lo reparten similitud e idoneidad (top 20: Spearman 0,72 con la similitud y 0,03 con la idoneidad; top 100: 0,38 y 0,45).
- **Base lunar no está saturada** (máximo 99,48; la mejor celda supera a la segunda en 4 puntos de mediana; solo 4 celdas por punto pasan el filtro).
- **Redondeo a 2 decimales:** crea empates, no los esconde. Paneles: 6.237 de 6.360 similitudes publicadas comparten valor con otra (247 valores distintos) frente a 1.983 a precisión completa. Ningún empate decide un miembro del top 5 (punto 4.2).

**Fallo de presentación (corregible sin cambiar el método).** Ningún texto del paquete ni de la web dice que la similitud de Paneles está saturada (búsqueda en `similarity.json`, `missions.json`, `explain.json`, `app/src`: nada); lo saben los documentos internos (`docs/ZONE_CONTRAST.md:54`, `:163`, `:272`; `docs/ANALOG_PRINCIPLE.md:295`). Los audios dicen "Similarity: 100 percent" (Paneles 5, similitud sin redondear 99,9968) y "99.99 percent". Propuesta, por orden:

1. En cada par, las diferencias reales primero y la similitud después (los ficheros `*_pairs.bin` ya las tienen).
2. Una frase fija en Paneles, por ejemplo: "Sunlight above the atmosphere depends on latitude only, so most Earth points find many maria cells that match almost exactly: 78 % of the Solar panels pairs score 99 or more and 514 score 100.00. Here the similarity tells you the match passed the tolerances; the ranking among them comes from suitability." (cifras de `out/p2_units.json`).
3. No mostrar "100" cuando el valor sin redondear es menor que 100 (mostrar "> 99.99" o dos decimales).
4. Para los audios: basta el texto de la web al lado; regrabar no es imprescindible. Si el líder quiere que el audio sea autosuficiente, la pista `m2_solar.mp3` es la candidata (una frase sobre la saturación).

Cambiar la fórmula, la tolerancia o la zona para que la similitud discrimine en Paneles es una **cuestión de diseño** (opciones ya medidas por el equipo en `docs/ZONE_CONTRAST.md` y `docs/ANALOG_PRINCIPLE.md`); no se ha tocado.

---

## La tabla: diferencias en los pares que sobreviven

`out/p2_table.csv` (desde `earth_<misión>_pairs.bin`, pares con gemelo):

| misión | variable | papel | unidad | tolerancia | cota | mediana | P90 | máximo |
|---|---|---|---|---|---|---|---|---|
| Rover (10.192) | pendiente | clave | ° | 2 | 2 | 0,408 | 0,851 | 1,971 |
| Rover | rugosidad | clave | m | 30 | 30 | 5,34 | 20,55 | 29,97 |
| Rover | elevación relativa | secundaria | m | 500 | 1.000 | 247,9 | 798,9 | 999,99 |
| Paneles (6.360) | irradiancia sobre la atmósfera | clave | kWh/m²/día | 0,6 | 0,6 | 0,0208 | 0,322 | 0,570 |
| Paneles | pendiente | secundaria | ° | 2 | 4 | 0,034 | 0,146 | 1,941 |
| Paneles | rugosidad | secundaria | m | 30 | 60 | 0,50 | 2,36 | 58,14 |
| Base lunar (450) | temperatura mínima | clave | puntos de percentil | 10 | 10 | 3,17 | 7,72 | 9,79 |
| Base lunar | temperatura mínima, real | (clave) | K | — | — | 207,88 | 210,55 | 211,94 |
| Base lunar | amplitud térmica | clave | puntos de percentil | 10 | 10 | 2,99 | 7,67 | 9,95 |
| Base lunar | amplitud térmica, real | (clave) | K | — | — | 153,76 | 161,28 | 179,40 |
| Base lunar | pendiente | secundaria | ° | 2 | 4 | 1,51 | 2,69 | 3,92 |
| Base lunar | rugosidad | secundaria | m | 30 | 60 | 27,27 | 54,43 | 59,81 |

Coinciden con las cifras de ASSUMPTIONS.md §0.13 para Base lunar (3,17 / 7,72; 2,99 / 7,67; 207,9 / 210,6 K; 153,8 / 161,3 K; 1,51 / 2,69°; 27,3 / 54,4 m; máximos 9,79, 9,95, 3,92, 59,81). Ningún máximo supera su cota.

## Lo que no he podido establecer

- El efecto en los gemelos del Rover de cambiar la referencia de la elevación relativa de la Tierra (media pesada por fracción de tierra): no medido.
- La regla de redondeo de la web en el navegador (`Math.round`): no revisada en `app/src`; el contrato avisa de que puede diferir en mitades exactas.
