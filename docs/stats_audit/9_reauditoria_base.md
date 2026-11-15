# Re-auditoría independiente — Base lunar (modelo corregido, contrato rev. 8)

Fecha: 15-11-2026. Commit auditado: **d24ebb3** (`final-integration`, fusionado en `audit-base`). Auditor independiente: no he escrito ni cambiado nada del motor, la configuración, las tablas ni el paquete.

**Camino de código.** Todas las cifras confirmadas salen de `tierra luna/audit/ra_base_*.py`, que usan la implementación independiente del primer auditor (`audit/p5_common.py`: embudo, idoneidad, percentiles mid-rank, filtro del par, gemelo, final, rango; no importa ningún módulo de `tierra luna/engine`). Encima, `ra_base_common.py` aplica por su cuenta los conjuntos de criterios de `engine_config.json` `criteria_sets` (parches y desviaciones; no usa `engine/criteria.py`) y reimplementa la elección de los cinco (`by_rank`, `rank_with_skips`). Salidas en `tierra luna/audit/out/ra_base_*.json`. Paquete de la mañana: `git show a493514:app/public/data/v2/...`.

## Veredicto por punto

| # | Punto | Veredicto | Cifra que decide |
|---|---|---|---|
| 1 | Configuración frente a decisiones | **GO** | Las 3 desviaciones (0,15→0; 0,10→0,25 con 0,1/0,7; 0,05→0) = DECISIONS 11:28/11:36 §3 y §7; su valor "team" = `mission_scoring.json` (y el componente `thermal` sigue siendo copia exacta); zona, tolerancias, filtro y pesos de similitud idénticos a `audited_morning`. Observaciones abajo (pesos suman 0,95). |
| 2 | Recálculo | **GO** | 2.419 pasan, 450 emparejados, 103 gemelos; 0 gemelos y 0 rangos distintos; diferencia máxima 0,00 en idoneidad, similitud y final; cinco = E21054, E17538, E21833, E18627, E19672 (puestos 1, 3, 5, 6, 7) = paquete. Todas las cotas se cumplen en los 450 pares. |
| 3 | Vuelta atrás (`audited_morning`) | **GO** | Contra el paquete de a493514: 0 gemelos, 0 rangos, 0,00 en las tres puntuaciones; cinco = E17538, E16830, E15751, E21054, E17187. |
| 4 | Datos nuevos | **GO (no aplica)** | Base lunar no usa columna suplementaria. `snow_ice_frac` y `mask_fraction` (tabla principal, ESA CCI LC 2020, MEASURED) solo entran en los saltos de los cinco, y en Base lunar no saltan a nadie (tierra ≥ 0,958 e hielo ≤ 0,083 en los 7 primeros). |
| 5 | Robustez ±10 % | **GO** | 16 perturbaciones: los 5 conservan su gemelo en 16/16; siguen entre los cinco 16, 16, 15, 15 y **10**/16 (el quinto, E19672, a 0,07 del octavo). Cinco idénticos en 4/16 (mañana: 8/20). |
| 6 | Estabilidad (Monte Carlo 200) | **GO** (frágil, como por la mañana) | Cinco idénticos 0/200 en los dos modelos. Cuota media entre los cinco 0,20 (mañana 0,145), top 20 0,49 (0,43), top 50 0,69 (0,62). El corregido es **algo más estable**, no estable. |
| 7 | Validación externa | **GO (igual)** | Separación 0,615 en los dos; 3 de 13 positivos pasan, 2 en el cuartil superior en los dos; MDRS 14,7→13,8 %, Craters of the Moon 7,0→7,4 %, Black Point 67,3→70,4 % (sin gemelo). |
| 8 | Los cinco lugares | **GO** | Tierra 0,958-1,000; hielo 0-0,083; clase CCI 200 (suelo desnudo) en los cinco; 223-1.385 km a la celda dominada por agua más próxima; nombre = el más cercano por círculo máximo en los 5; gemelos dentro de las 280 celdas; separación mínima 6,06°. Saltados E21412 (2) y E20695 (4), ninguno es un sitio reconocido. |
| 9 | Textos | **NOT YET** | `external_validation_lunar_base` dice que los sitios del benchmark que pasan el embudo "have no twin": falso (MDRS y Craters of the Moon pasan y tienen gemelo, puestos 335 y 179); `top5_stability_lunar_base` sigue "pending". Resto comprobado (abajo). |

**Recomendación global: publicar la Base lunar corregida**, con dos correcciones de texto (punto 9), que no tocan pares ni puntuaciones. Los cinco y sus puntuaciones son seguros para imprimir (reproducidos exactamente), con la frase "five of the highest-scoring analogs in our model" y las cifras de estabilidad de abajo.

Cifras que lo justifican:
1. Reproducción exacta con código independiente de los dos estados (0 diferencias en 2.419 puntos), y gemelos y similitudes idénticos entre mañana y corregido (0 de 450 gemelos cambian; solo cambian idoneidad en 2.222 puntos, rango en 437, top 50 conserva 38).
2. Estabilidad no peor que la de la mañana en ninguna medida agregada (entre los cinco 0,20 frente a 0,145; top 50 0,69 frente a 0,62); los cinco quedan más lejos de la compuerta (mediana +4,3 K frente a +3,0 K; en el top 50, 6 a menos de 2 K frente a 13).
3. Validación externa idéntica (0,615), y la compuerta de 15 K queda justificada por mis propias cifras: sin ella encabezan cinco celdas de Ellesmere con 0,94-1,91 K de amplitud y similitud 97,65-99,83.
4. Ningún fallo de implementación; las debilidades (cinco que nunca se repiten, ningún análogo polar) vienen de criterios decididos.

## 1. Configuración frente a decisiones

- Conjunto `corrected` de `lunar_base` (`engine_config.json` `criteria_sets`): desviaciones `thermal_inertia_class` peso 0,15 → fuera (sigue en `require_present` y en la puerta `exclude: ["agua"]`, comprobado en `missions.json` `gates`), `rock_or_bare_frac` 0,10 → 0,25 (malo 0,1, bueno 0,7), `permafrost_class` 0,05 → fuera. Coinciden número a número con DECISIONS.md "Decisiones de las 11:28 y 11:36" §3 y la tabla §7, y con `research_3` §8. Cada una lleva valor del equipo, el nuestro, razón y fuente; el valor "team" citado es igual al de `mission_scoring.json` para `lunar_base` y para `thermal` (el motor aplica las mismas desviaciones al componente `thermal`, `engine/criteria.py` líneas 80-93, y `lunar_base` sigue siendo copia exacta).
- Similitud: el conjunto `corrected` no parchea `real_value_similarity.missions.lunar_base`, y el bloque principal es **idéntico** al parche `audited_morning` (zona de 280 celdas, tmin_k y amplitud en percentil 40 % + 40 %, tolerancia 10; pendiente y rugosidad 10 % + 10 %, 2° y 30 m, filtro 4° y 60 m).
- Cinco: `rank_with_skips`, hielo `snow_ice_frac ≥ 0,5`, agua `mask_fraction < 0,5`, separación 2° (DECISIONS §5).
- Puerta de amplitud ≥ 15 K y tmin ≤ 5 °C: sin cambio.

Observaciones (no fallos del resultado):
- **Los pesos de idoneidad suman 0,95** (0,35 + 0,25 + 0,25 + 0,10). La idoneidad es media ponderada dividida por la suma, así que los pesos efectivos son 36,8 / 26,3 / 26,3 / 10,5 %. Ningún documento lo dice; `missions.json` `weighted_variables` publica 0,35/0,25/0,25/0,10. Conviene una frase o renormalizar en la presentación.
- El salto de agua lleva en su "why" "TO BE CONFIRMED by the team lead"; DECISIONS §5 lo da por aplicado. En Base lunar no tiene efecto hoy.
- La razón de la desviación de `rock_or_bare_frac` dice "the fraction is DERIVED"; `provenance_earth.csv` y `weighted_variables` dicen MEASURED (EARTH). Incoherencia de etiqueta.
- No he encontrado en la configuración de Base lunar nada que no cubra una decisión, ni una decisión sin implementar.

## 2. Recálculo y tabla de diferencias

Embudo (cada puerta por sí sola, celdas de la Tierra que excluye): amplitud ausente 46.062, tmin ausente 39.316; elevación ≥ 1 m 39.732; tierra ≥ 0,3 42.578; amplitud ≥ 15 K 60.252; tmin ≤ 5 °C 46.183; clase "agua" 43.724. Pasan 2.419 = paquete (mismo conjunto).

Comparación celda a celda con el paquete de d24ebb3 a su precisión publicada (2 decimales): 0 gemelos distintos, 0 rangos distintos, diferencia máxima 0,00 en idoneidad, similitud y final, 0 discrepancias de ausencia.

Diferencias de los 450 pares (iguales en los dos conjuntos, porque el emparejamiento no cambia):

| Variable | Escala | Tolerancia | Cota | Mediana | P90 | Máximo | Cota en todos |
|---|---|---|---|---|---|---|---|
| tmin_k | percentil | 10 | 10 | 3,17 | 7,72 | 9,79 | sí |
| lst_diurnal_amp_k | percentil | 10 | 10 | 2,99 | 7,67 | 9,95 | sí |
| slope_deg | real (°) | 2 | 4 | 1,51 | 2,69 | 3,92 | sí |
| roughness_m | real (m) | 30 | 60 | 27,26 | 54,43 | 59,81 | sí |

Cabeza del ranking corregido: 1 E21054 (72,00), 2 E21412 (71,28), 3 E17538 (70,23), 4 E20695 (70,13), 5 E21833 (69,87), 6 E18627 (69,80), 7 E19672 (69,73), 8 E18254 (69,66). La regla de separación salta E21412 (a menos de 2° de E21054) y E20695 (ídem). Los cinco: E21054, E17538, E21833, E18627, E19672 = `missions.json` `top5.ids`, puestos 1, 3, 5, 6, 7.

Mañana frente a corregido (mismos 2.419): gemelos distintos 0, diferencia máxima de similitud 0,0; idoneidad cambia en 2.222 puntos, rango en 437; top 50 compartido 38 (= investigación y DECISIONS).

## 3. Vuelta atrás

`audited_morning` reconstruido con mi código: 2.419 / 450 / 103, igual al paquete de a493514 celda a celda (0 gemelos, 0 rangos, 0,00). Cinco por rango: E17538 (72,29), E16830 (72,28), E15751 (71,73), E21054 (71,63), E17187 (71,28) = investigación 3 "Hoy" y `docs/AUDIO_TOP5`. La vuelta atrás funciona.

## 4. Datos nuevos

No aplica: Base lunar no lee ninguna columna de `real_data/supplement/` (la de ISCCP es de Paneles solares). Las columnas de los saltos (`snow_ice_frac`, `mask_fraction`) son de la tabla principal, ESA CCI LC 2020 v2.1.1 (`provenance_earth.csv` líneas 6 y 14), y no saltan ningún punto de Base lunar.

## 5. Robustez (pesos ±10 %, renormalizados, uno a uno)

Corregido: 4 pesos de idoneidad + 4 de similitud × 2 = 16 perturbaciones.

| Análogo | Sigue entre los cinco | Conserva gemelo | Peor puesto |
|---|---|---|---|
| E21054 (Tinghir, Marruecos) | 16/16 | 16/16 | 1 |
| E17538 (Aheqi, Tian Shan) | 16/16 | 16/16 | 6 |
| E21833 (Kherameh, Fars, Irán) | 15/16 | 16/16 | 8 |
| E18627 (Waxxari, Xinjiang) | 15/16 | 16/16 | 8 |
| E19672 (Aradan, Irán) | 10/16 | 16/16 | 9 |

Cinco idénticos en 4 de 16. Mañana (20 perturbaciones): 20, 20, 20, 20 y 14/20, idénticos en 8/20. El quinto corregido es un empate práctico (69,73 frente a 69,66 del siguiente elegible). Debilidad del criterio decidido, no de la implementación.

## 6. Estabilidad (Monte Carlo, 200 corridas, semilla 20261115)

Incertidumbres de `audit/p3_montecarlo.py` `SIGMA` (fuentes en `3_robustez_validacion_ranking.md` F.3): ETOPO 7,17 m, LOLA 10 m, pendiente y rugosidad 5 % (ilustrativo), tmin Tierra 1,39 K (WorldClim), tmin Luna 1 K (Diviner), amplitud √2 K en los dos cuerpos, irradiancia 0,403 kWh/m²/día, `rock_or_bare_frac` 0,05 (ilustrativo). Cada corrida rehace todo (embudo, percentiles de las poblaciones perturbadas, gemelos, final, rango y cinco por la regla del conjunto).

| Análogo (corregido) | Entre los cinco | Top 20 | Top 50 | Conserva gemelo | Falla el embudo |
|---|---|---|---|---|---|
| E21054 | 18,0 % | 51,5 % | 72,5 % | 16,5 % | 0 % |
| E17538 | 23,0 % | 52,5 % | 62,0 % | 12,0 % | 36,5 % |
| E21833 | 19,0 % | 43,5 % | 66,5 % | 12,0 % | 0 % |
| E18627 | 18,0 % | 38,0 % | 54,0 % | 44,5 % | 0 % |
| E19672 | 22,5 % | 59,0 % | 88,5 % | 5,5 % | 0 % |

| Análogo (mañana) | Entre los cinco | Top 20 | Top 50 | Conserva gemelo | Falla el embudo |
|---|---|---|---|---|---|
| E17538 | 38,0 % | 59,5 % | 62,0 % | 12,0 % | 36,5 % |
| E16830 | 10,5 % | 38,0 % | 59,0 % | 33,5 % | 1,5 % |
| E15751 | 8,5 % | 42,5 % | 57,0 % | 11,0 % | 22,0 % |
| E21054 | 3,5 % | 35,0 % | 59,0 % | 16,5 % | 0 % |
| E17187 | 12,0 % | 41,5 % | 73,0 % | 25,5 % | 0,5 % |

- Los cinco se repiten exactamente (como conjunto o en orden): **0 de 200** en los dos modelos (el primer auditor también midió 0/200 por la mañana).
- Puntos a ≤ 0,1 / 0,5 / 1 punto de final del quinto: corregido 2 / 7 / 10 (mediana en las corridas 1 / 3 / 6); mañana 1 / 7 / 10 (1 / 3 / 6,5).
- Medias de los cinco: entre los cinco 0,201 frente a 0,145; top 20 0,489 frente a 0,433; top 50 0,687 frente a 0,620.
- **El modelo corregido es algo más estable que el de la mañana, y sigue siendo frágil**: ningún análogo queda entre los cinco en más del 23 % de las corridas, y los gemelos cambian casi siempre (la posición en percentil se mueve con la población perturbada).
- **Compuerta:** amplitud de los cinco por encima de 15 K: +3,71, **+0,60** (E17538), +5,03, +7,12, +4,67 K (mediana +4,3; mañana +3,0). E17538 sale del embudo en el 36,5 % de las corridas, solo por la compuerta (σ = 1,41 K). En el top 50, 6 puntos a menos de 2 K de la compuerta (mañana 13). La compuerta pesa sobre E17538 igual que pesaba por la mañana, cuando era el número 1.

## 7. Validación externa (`validation_sites_lunar_base.csv`, convención de r4)

| Sitio | Mañana: puesto / percentil | Corregido: puesto / percentil |
|---|---|---|
| Craters of the Moon (LP11) | 170 / 7,0 % | 179 / 7,4 % |
| MDRS (LP08) | 356 / 14,7 % | 335 / 13,8 % |
| Black Point (LP10, sin gemelo) | 1.629 / 67,3 % | 1.704 / 70,4 % |
| Los otros 10 positivos y los 7 negativos | no pasan el embudo | no pasan el embudo |

Positivos en el cuartil superior 2 de 13 en los dos; separación positivo-negativo 0,615 en los dos; mediana del percentil de los positivos que pasan 14,7 → 13,8 %. Mi cifra de la mañana reproduce exactamente `research_4`. **Igual.** Que ningún análogo polar pase es consecuencia de la compuerta decidida (ver punto 9 y `ra_base_gate.json`), no de la implementación.

## 8. Los cinco lugares

| # | Celda | Lugar (paquete = mío, km) | Tierra | Hielo | CCI | km a celda de agua | Amplitud / tmin | Gemelo (en zona) |
|---|---|---|---|---|---|---|---|---|
| 1 | E21054 (31,5; −5,5) | Tinghir, 3,5 | 1,000 | 0,000 | 200 | 358,6 | 18,71 K / −1,52 °C | M62517 sí |
| 2 | E17538 (41,5; 78,5) | Aheqi, 62,3 | 0,998 | 0,083 | 200 | 641,3 | 15,60 K / −24,54 °C | M63528 sí |
| 3 | E21833 (29,5; 53,5) | Kherameh, 18,2 | 0,958 | 0,000 | 200 | 242,9 | 20,03 K / −1,49 °C | M62515 sí |
| 4 | E18627 (38,5; 87,5) | Waxxari, 27,4 | 1,000 | 0,000 | 200 | 1.385,1 | 22,12 K / −16,84 °C | M62479 sí |
| 5 | E19672 (35,5; 52,5) | Aradan, 27,9 | 1,000 | 0,000 | 200 | 222,4 | 19,67 K / −5,19 °C | M63657 sí |

"km a celda de agua" = distancia de círculo máximo al centro de la celda más próxima con `mask_fraction` < 0,5 (sustituto de la distancia a la costa con las columnas de la tabla). Ninguno es artefacto. Separación mínima entre los cinco: 6,06°. Nombre: mi búsqueda por círculo máximo sobre `rg_cities1000.csv` da el mismo lugar y la misma distancia en los cinco. Los saltados (E21412, E20695, junto a Tinghir) no son sitios reconocidos; ningún sitio reconocido está por encima del puesto 179, así que la regla no saltó ninguno.

## 9. Textos

Comprobados contra mis cifras (correctos): `lunar_base_swing_gate` (Haughton E5130 2,50 K, Svalbard E3793 1,23 K, Kangerlussuaq E8049 6,63 K; McMurdo E60462 y Concordia E59703 sin LST; sin compuerta encabezan celdas de Ellesmere de 0,94-1,91 K con similitud 97,65-99,83: "about 99" vale); `lunar_base_criteria` (607 de 2.419 sin permafrost: correcto; 25 %); `twin_sharing_note` ("at most 5.6 %": 25/450 = 5,56 %); `zone_edge_lunar_base` (280 celdas, 103 gemelos); `list_order_lunar_base`; las frases por par de `explain.json` de los cinco (tmin −1,5 / −24,5 / −1,5 / −16,8 / −5,2 °C = tabla); los textos de la regla z-score están marcados "no longer applies" y con `missions: []`.

Fallos de texto (NOT YET):
1. **`external_validation_lunar_base`** (show: data_and_limits): "the benchmark sites that pass it have no twin among the cells of NASA's nine candidate regions". Falso: con su propia fuente (`3_robustez` §6.1: MDRS y Craters of the Moon tienen gemelo) y con la lista de `research_4`, MDRS (puesto 335, 13,8 %) y Craters of the Moon (179, 7,4 %) pasan y tienen gemelo; además `missions.json` `external_validation` es `null` para Base lunar. Debe decir: 3 de 13 sitios reconocidos pasan el embudo, 2 tienen gemelo y quedan en el cuartil superior (7,4 % y 13,8 %), los polares no pasan por la compuerta o por falta de LST; separación 0,615.
2. **`top5_stability_lunar_base`**: "Stability figures pending the independent re-audit." Rellenar con las cifras del punto 6 (JSON `stability`).
3. Menor: `missions.json` `weighted_variables` marca `tmin_c` `also_in_similarity: false`, cuando la temperatura mínima (como `tmin_k`, en percentil) es variable clave de la similitud; y publica los pesos 0,35/0,25/0,25/0,10 sin decir que suman 0,95.
4. Menor: la razón de la desviación de `rock_or_bare_frac` dice DERIVED y la procedencia dice MEASURED.

Nota: hay un pase de solo texto en marcha en `final-integration`; este punto se revisa otra vez tras fusionarlo (sección final).

## Qué es debilidad del criterio y qué es fallo

- Fallos de implementación: **ninguno** (puntos 1-3, 8).
- Fallos de texto: punto 9, 1 y 2 (bloquean), 3 y 4 (menores).
- Debilidades de criterios decididos (se informan, no se cuentan como fallo): cinco que nunca se repiten bajo la incertidumbre documentada (0/200, igual que por la mañana); E17538 a 0,6 K de la compuerta (sale del embudo en el 36,5 % de las corridas); ningún análogo polar pasa (compuerta de 15 K y falta de LST antártica); quinto en empate práctico (10/16 en ±10 %).

## Revisión final del punto 9 (tras el pase de textos, final-integration 0486ad9)

Fusionado `origin/final-integration` (0486ad9). El paquete solo cambia en textos (`similarity.json`, `missions.json`, `manifest.json`): mi recálculo sigue dando 0 gemelos, 0 rangos y 0,00 de diferencia en los dos conjuntos (corregido y vuelta atrás). Comprobación con `tierra luna/audit/ra_base_texts.py` (salida `out/ra_base_texts.json`):

- `external_validation_lunar_base`: ya no dice que los sitios que pasan no tienen gemelo; dice 13 sitios, 3 pasan, 2 con gemelo (MDRS número 335, Craters of the Moon número 179), Black Point pasa sin gemelo, los demás no pasan con su razón (= mis cifras y las de la tabla), 0 de 7 tropicales pasan. Correcto.
- `top5_stability_lunar_base`: no pendiente; entre los cinco / top 20 = 18,0/51,5, 23,0/52,5, 19,0/43,5, 18,0/38,0, 22,5/59,0 %; 0 de 200; ±10 %: 16, 16, 15, 15, 10 de 16. Idéntico a mis cifras.
- Pesos que suman 0,95: dicho en `lunar_base_criteria` y en `deviations_from_team` (efectivos 36,8 / 26,3 / 26,3 / 10,5 %). Correcto.
- `weighted_variables` `tmin_c` `also_in_similarity`: ahora `true`. Correcto.
- `rock_or_bare_frac`: la razón dice ahora MEASURED en la procedencia (con la matización de que es una clasificación). Coherente.

**Punto 9: GO.** Los nueve puntos quedan en GO. **Recomendación final: publicar la Base lunar corregida.**
