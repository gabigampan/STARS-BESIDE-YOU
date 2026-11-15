# 9 — Re-auditoría independiente de Paneles solares (modelo corregido, contrato rev. 8)

Fecha: 2026-11-15, inicio 11:52 UTC (mensaje "AUDIT START d24ebb3"). Commit auditado: **d24ebb3** (fusionado en `audit-solar`). Auditor independiente: no he escrito ni cambiado nada del motor, la configuración, las tablas, el paquete ni la web.
Camino de cálculo propio: `tierra luna/audit/ra_solar_common.py` reutiliza la implementación independiente de los primeros auditores (`audit/p5_common.py`: embudo, idoneidad, similitud en valores reales, filtro del par, búsqueda del gemelo, final, rango) y le añade lo nuevo: los conjuntos de criterios de `engine_config.json` `criteria_sets` (parche por ruta + desviaciones sobre `mission_scoring.json`), la columna suplementaria `clear_frac_isccp` unida por id de celda y las reglas de los cinco (`by_rank`, `min_separation`, `rank_with_skips`). No importa nada de `tierra luna/engine`. Scripts `audit/ra_solar_*.py`, salidas `audit/out/ra_solar_*`.

## Veredicto por punto

| # | Punto | Veredicto | Cifra que decide |
|---|---|---|---|
| 1 | Configuración frente a decisiones | **GO** | 4 desviaciones de `mission_scoring.json`, las 4 listadas con razón y fuente; puertas, `require_present`, zona, variables y tolerancias de similitud idénticas a la mañana; malo/bueno 0,308/0,671 = P10/P90 recalculados (0,3079/0,6711). Nota: los pesos blandos suman **0,70**, no 1 (ver fallo F1) |
| 2 | Recálculo | **GO** | 18.777 puntos: 0 diferencias en pasa/no pasa, en las 10 razones de exclusión, idoneidad, similitud, final, rango, gemelo y puntuaciones por variable (diferencia máxima 0,00); 6.360 pares, 1.704 gemelos; 0 pares fuera de su cota; los cinco iguales |
| 3 | Vuelta atrás (`audited_morning`) | **GO** | motor construido con `selected.solar = audited_morning`: `suitability, similarity, final, rank, twin, fail_bits`, `earth_solar_pairs.bin` y `moon_solar.bin` idénticos a a493514 (los dos .bin byte a byte); solo `confidence`/`confidence_score` vacías (decisión 6 de las 11:28); cinco = rangos 1-5 = E38464, E38105, E38744, E37746, E38465 |
| 4 | Dato nuevo (ISCCP-H) | **GO con límites** | reducción propia desde los 60 ficheros NCEI: 64.778 celdas, diferencia máxima 5·10⁻⁵ (redondeo), meses válidos idénticos en 64.800; orientación 10 de 10 lugares; pero 3 puntos sin valor, uno de ellos (E34142, Sulawesi) en el **puesto 16** solo por la renormalización (F2) |
| 5 | Pesos ±10 % | **GO** | corregido: los cinco siguen entre los cinco y con su gemelo en **14 de 14** perturbaciones (orden idéntico 12/14); mañana: E38465 10/18, E37746 conserva gemelo 16/18 |
| 6 | Monte Carlo | **GO (más estable que la mañana; frágil en absoluto)** | entre los cinco: 9,5 / 7,0 / 13,0 / 1,5 / 0,5 % frente a 0,0 / 0,0 / 2,0 / 0,5 / 0,0 % de la mañana; top 20: 40 / 37,5 / 31,5 / 14,5 / 12,5 % frente a 6,5–19,5 %; cinco idénticos 0/200 en los dos |
| 7 | Validación externa | **GO (igual, no mejor, dentro de la fila)** | positivos BSRN dentro de su fila de latitud: mediana **28,8 %** frente a **27,9 %** de la mañana; en la clasificación completa 8,3 % frente a 14,9 %; cuartil superior 9/11 frente a 8/11 |
| 8 | Los cinco lugares | **GO** | 5/5 tierra ≥ 0,66, hielo 0; nombre = vecino más cercano por círculo máximo 5/5 (mismo nombre y km); gemelos en la zona 5/5; separación mínima 2,97°; ningún sitio reconocido saltado |
| 9 | Textos | **NOT YET** | quedan 2 frases falsas o caducadas (F1 "35 %", F4 "sun geometry … are suitability criteria") y la estabilidad "pendiente"; F3 corregida en c5f1f6c y comprobada |

**Recomendación global:** **publicar Paneles solares corregido** ("publish the corrected Solar panels"), con la condición de corregir antes dos frases (F1 "35 %" → 50 % efectivo; F4 frase caducada sobre criterios de idoneidad) y rellenar `top5_stability_solar` con las cifras de §6. Cifras: (1) recálculo independiente idéntico en las 18.777 celdas y vuelta atrás exacta a a493514; (2) idoneidad sin latitud: Spearman con \|lat\| +0,337 (mañana −0,857), peso ligado a la latitud 0; (3) más estable: cada análogo de los cinco está entre los cinco en 0,5–13 % de 200 corridas y en el top 20 en 12,5–40 % (mañana 0–2 % y 6,5–19,5 %), 14/14 con pesos ±10 % (mañana E38465 10/18); (4) validación BSRN mejor en la clasificación completa (mediana 8,3 % frente a 14,9 %) e **igual** dentro de la fila de latitud (28,8 % frente a 27,9 %): no se demuestra que diga más que la latitud sobre estas estaciones, pero no es peor. Las debilidades F2, F5 y F6 salen de criterios decididos, no de la implementación.

## 1. Configuración frente a decisiones

Leído: `engine_config.json` `criteria_sets.missions.solar.sets.corrected` (seleccionado en `selected.solar`), DECISIONS.md "Decisiones de las 11:28 y 11:36" §2, §5, §7, DATA_CONTRACT rev. 8, `mission_scoring.json`. Configuración efectiva reconstruida por mi lector (`ra_solar_config.py`, `out/ra_solar_config.json`):

| | Equipo (`mission_scoring.json`) | Corregido | Decisión |
|---|---|---|---|
| irradiancia WorldClim (blando) | 0,35 (2,5→6,0) | fuera | §2 / §7 ✔ |
| sun_elev_max_deg (blando) | 0,15 (10→70) | fuera | ✔ |
| sun_low_frac_0_5deg (blando) | 0,15 (0,25→0,03) | fuera | ✔ |
| clear_frac_isccp | — | 0,35 (0,308→0,671) | ✔ (P10/P90 recalculados: 0,3079 / 0,6711) |
| pendiente / amplitud / rugosidad | 0,15 / 0,10 / 0,10 | iguales | ✔ |
| puertas (irradiancia ≥ 2,5, pendiente ≤ 15, sol ≥ 10°, sol bajo ≤ 0,25, sin agua) y `require_present` | | idénticas | ✔ |
| similitud: luz sobre la atmósfera 0,8 clave τ 0,6; pendiente 0,1 τ 2; rugosidad 0,1 τ 30; cota secundaria 2τ | | idéntica a la mañana | ✔ "emparejamiento sin cambio" |
| zona: \|lat\| ≤ 30°, elevación ≤ −1.200 m | | idéntica | ✔ |
| cinco | mañana `by_rank` | `rank_with_skips`: hielo ≥ 0,5, tierra < 0,5, 2° | §5 ✔ |

Las 4 diferencias blandas están en `mission_scoring_deviations` con valor del equipo, el nuestro, razón y fuente; ninguna diferencia sin decisión. Observaciones:
- **Los pesos blandos suman 0,70** (0,15 + 0,10 + 0,10 + 0,35). El motor divide por la suma, así que el peso **efectivo** del despejado es **0,50**, y pendiente 0,214, amplitud 0,143, rugosidad 0,143 (`explain.json` lo confirma: el despejado aporta 50,0 puntos al número 1). Es lo que se decidió (investigación 2 E2: "0,35, el hueco que deja la irradiancia" con el resto sin tocar), así que no es un fallo de implementación; pero "pesos que suman 1" no se cumple tal como están escritos y el texto publicado dice "35 %" (F1).
- El "why" del salto de agua en la configuración sigue diciendo "TO BE CONFIRMED by the team lead" mientras DECISIONS §5 lo da por publicado; texto interno, no se publica.
- DECISIONS §2 escribe "Cinco antes (11:23): E38464, E38744, E37746, E37750, E29749" (los cinco con separación de 2°), pero el estado de vuelta atrás `audited_morning` (42d8bba / a493514) son los rangos 1-5 sin separación: E38464, E38105, E38744, E37746, E38465 (tres celdas de Derby a 0,96–1,39° entre sí). Si Paneles vuelve atrás, vuelve también a esa lista.

## 2. Recálculo (`ra_solar_recompute.py corrected`, `out/ra_solar_recompute_final_corrected.json`)

Embudo: pasan 18.777 de las celdas de tierra; las 10 razones de exclusión (bits de `missions.json` `reason_codes`) coinciden celda a celda con mi evaluación de cada puerta (0 discrepancias). Con gemelo 6.360, gemelos distintos 1.704. Idoneidad, similitud, final (2 decimales), rango, gemelo y las tres puntuaciones `s.*`: 0 diferencias en 18.777 filas (diferencia máxima 0,00).

Tabla de diferencias en los 6.360 pares (valores reales; cota = τ para la clave, 2τ para las secundarias; comprobado en cada par):

| variable | papel | peso | τ | cota | mediana | P90 | máximo | pares sobre la cota |
|---|---|---|---|---|---|---|---|---|
| luz sobre la atmósfera (kWh/m²/día) | clave | 0,8 | 0,6 | 0,6 | 0,0208 | 0,3222 | 0,5696 | 0 |
| pendiente (°) | secundaria | 0,1 | 2 | 4 | 0,034 | 0,146 | 1,941 | 0 |
| rugosidad (m) | secundaria | 0,1 | 30 | 60 | 0,50 | 2,36 | 58,14 | 0 |

Iguales a las del fichero de pares del paquete. Los cinco, por la regla publicada:

| # | Tierra | lugar (GeoNames más cercano) | rango | gemelo | similitud | idoneidad | final |
|---|---|---|---|---|---|---|---|
| 1 | E40184 (−21,5; 44,5) | Manja, Madagascar, 18,8 km | 1 | M23206 (25,5; −13,5) Timocharis | 99,83 | 97,94 | 98,88 |
| 2 | E29749 (7,5; 49,5) | Eyl, Somalia, 63,8 km | 2 | M26063 (17,5; −36,5) | 99,97 | 97,56 | 98,76 |
| 3 | E23648 (24,5; 68,5) | Jati, Pakistán (Sind), 28,6 km | 5 | M22156 (28,5; 16,5) | 99,93 | 97,20 | 98,56 |
| 4 | E29746 (7,5; 46,5) | Gaalkacyo, Somalia, 130,9 km | 7 | M26056 (17,5; −43,5) | 99,97 | 97,08 | 98,52 |
| 5 | E28670 (10,5; 50,5) | Iskushuban, Somalia, 38,1 km | 9 | M25483 (19,5; 103,5) | 99,94 | 96,81 | 98,37 |

Saltados antes del quinto (todos por la separación de 2°, ninguno por hielo o agua): E40543 (3), E40904 (4), E29747 (6), E30105 (8). Coincide con lo que comunica el implementador.

Otras cifras comprobadas: Spearman idoneidad–|lat| entre los que pasan **+0,337** (mañana −0,857); entre los emparejados +0,382 (mañana +0,092); top 50 en común con la mañana 7; top 100 en los trópicos 0,63 (mañana 1,00).

## 3. Vuelta atrás

Copia del árbol en el scratchpad con `criteria_sets.selected.solar = "audited_morning"` y `python -m engine build` (el código bajo prueba, solo para obtener el paquete); además mi propio recálculo con ese conjunto contra a493514 (`out/ra_solar_recompute_final_morning.json`: PASS, 0 diferencias). Resultado del motor frente a `git show a493514:app/public/data/v2`: `earth_solar_pairs.bin` y `moon_solar.bin` **idénticos byte a byte**; en `earth_solar.bin` todas las columnas iguales salvo `confidence` y `confidence_score`, que la revisión 8 deja vacías en todos los estados (decisión 6). `missions.json` declara `criteria_set: audited_morning`, `top5.rule_id: by_rank`, ids E38464, E38105, E38744, E37746, E38465 = rangos 1-5 de a493514.

## 4. El dato nuevo: fracción despejada ISCCP-H

- **Procedencia comprobada en la fuente:** índice NCEI `…/isccp-h-series-data/access/isccp-basic/hgm/` accesible (408 ficheros, 1983-…); descargué los 60 de 2012-01 a 2016-12 (248 MB, fuera del repositorio). Atributos del fichero: título "International Satellite Cloud Climatology Project Gridded Monthly Mean data -- ISCCP HGM Basic", variable `cldamt` "Mean cloud amount", unidades "percent", factor de escala 0,1, licencia "No constraints on data access or use.", rejilla 180×360 con centros −89,5…89,5 y 0,5…359,5. Coincide con `provenance_earth_cloud_isccp.csv`.
- **Reducción rehecha por mi cuenta** (`ra_solar_data_layer.py`), asignando cada celda por las coordenadas de su centro leídas del fichero (no por un volteo supuesto), media de las medias mensuales con ≥ 48 meses: 64.778 celdas con valor en los dos, 0 solo en uno, diferencia máxima 5·10⁻⁵ (el redondeo a 4 decimales), número de meses igual en 64.800. **Orientación y alineación correctas.**
- **Rango:** 0,059–0,830 en todas las celdas; entre los que pasan P0 0,119, P50 0,466, P100 0,830. Plausible para una fracción despejada anual.
- **Lugares conocidos (signo esperado, 10/10):** Sáhara-Libia 0,724; Atacama 0,798; Rub al Jali 0,784; desierto de Australia Occidental 0,591; Mojave 0,651 (despejados) · Congo 0,289; Amazonía 0,323; Borneo 0,191; Escocia 0,256; Océano Austral 0,142 (nubosos). Los seis negativos del Met Office tienen 0,21–0,28, todos por debajo del "malo" 0,308.
- **Desiertos brillantes:** celdas con suelo desnudo ≥ 0,8: mediana 0,652 (0,677 a \|lat\| ≤ 35°): no se ve el artefacto típico (desierto brillante leído como nube).
- **Nieve y hielo:** celdas con hielo ≥ 0,5: mediana 0,588, P90 0,684, tan "despejadas" como un desierto: es la debilidad conocida de la detección de nubes sobre hielo (la nota de procedencia lo dice). **Sin efecto en los pares:** 6.086 puntos que pasan tienen hielo ≥ 0,5 pero **0** tienen gemelo, y la regla de los cinco los salta.
- **Costas:** a igual latitud, las celdas costeras que pasan son más nubosas que las interiores (0–15°: 0,335 frente a 0,432; 15–30°: 0,508 frente a 0,615; 30–45°: 0,398 frente a 0,475). Es en parte real y en parte mezcla de nubes oceánicas en una celda de 1°; empuja la costa hacia abajo, no la sube.
- **Valores ausentes (F2):** 3 puntos que pasan sin valor (0 meses válidos en E34142 y E35577; 45 en E11565). Con la renormalización decidida su idoneidad sale solo de pendiente, amplitud y rugosidad: **E34142 (−4,5; 122,5, Sulawesi, una de las zonas más nubosas del planeta) obtiene idoneidad 96,23 y el puesto 16** de la clasificación completa; E35577 (Lombok/Sumbawa) puesto 1.693. No entra en los cinco, pero es un artefacto en la cabeza. Consecuencia de un criterio decidido ("no requerido; se renormaliza"), no un fallo de implementación; el texto publicado dice que esos 3 puntos reparten el peso, pero no que uno queda 16.º.
- **Correlaciones (Spearman, puntos que pasan / emparejados):** con \|lat\| +0,30 / +0,47; con la irradiancia WorldClim +0,35 / +0,80; con la amplitud térmica (criterio que queda) +0,67 / +0,79 (va en contra: cielo despejado ⇒ más amplitud, penalizada); con la lluvia −0,70 / −0,83; con pendiente −0,39 y rugosidad −0,42. Parte de la dispersión de la idoneidad: despejado 0,895, amplitud −0,206, pendiente 0,063, rugosidad 0,049. **No duplica** ningún criterio que queda en la idoneidad; entre los emparejados lleva mucha de la información de la irradiancia WorldClim retirada (0,80), que es lo esperable (irradiancia en suelo ≈ luz sobre la atmósfera × transparencia).
- **Incertidumbre:** no encontré en esta sesión una incertidumbre por celda documentada para la media 2012-2016 de `cldamt`; en el Monte Carlo uso **0,05 absoluto, ILUSTRATIVO**, así etiquetado.

## 5. Pesos ±10 % (uno a uno, renormalizados)

Corregido: 4 pesos de idoneidad + 3 de similitud × 2 = 14 perturbaciones. Mañana: 6 + 3 → 18.

| análogo (corregido) | entre los cinco | con su gemelo | peor rango |
|---|---|---|---|
| E40184 | 14/14 | 14/14 | 1 |
| E29749 | 14/14 | 14/14 | 2 |
| E23648 | 14/14 | 14/14 | 7 |
| E29746 | 14/14 | 14/14 | 7 |
| E28670 | 14/14 | 14/14 | 9 |

Orden idéntico en 12/14. Mañana: E38464, E38105, E38744 18/18; E37746 18/18 pero conserva su gemelo 16/18; E38465 **10/18**; orden idéntico 8/18.

## 6. Monte Carlo de la incertidumbre de entrada

`ra_solar_montecarlo.py`, 200 corridas por estado, semilla 20261115, mismas incertidumbres de la primera auditoría (`p3_montecarlo.py` SIGMA, con sus fuentes: ETOPO 7,17 m; pendiente y rugosidad 5 % ilustrativo; irradiancia WorldClim 0,403 kWh/m²/día; amplitud √2 K; LOLA 10 m; irradiancia lunar 2 % ilustrativo) y, para la columna nueva, **0,05 absoluto ILUSTRATIVO** (sin cifra documentada encontrada). Cada corrida recalcula embudo, idoneidad, gemelos, similitud, final, rango y los cinco por la regla publicada de cada estado. Salidas `out/ra_solar_mc_corrected.json` y `out/ra_solar_mc_audited_morning.json`.

| análogo | gemelo | entre los cinco | top 20 | top 50 | conserva gemelo | rango mediano |
|---|---|---|---|---|---|---|
| **corregido** E40184 | M23206 | **9,5 %** | 40,0 % | 57,5 % | 3,5 % | 30 |
| E29749 | M26063 | **7,0 %** | 37,5 % | 74,0 % | 0,5 % | 25,5 |
| E23648 | M22156 | **13,0 %** | 31,5 % | 38,0 % | 8,0 % | 540,5 |
| E29746 | M26056 | **1,5 %** | 14,5 % | 45,0 % | 1,5 % | 62,5 |
| E28670 | M25483 | **0,5 %** | 12,5 % | 51,5 % | 2,5 % | 49,5 |
| **mañana** E38464 | M24296 | 0,0 % | 16,5 % | 53,5 % | 0,5 % | 46,5 |
| E38105 | M24583 | 0,0 % | 15,0 % | 44,5 % | 0,5 % | 57 |
| E38744 | M40854 | 2,0 % | 19,5 % | 44,0 % | 4,0 % | 65,5 |
| E37746 | M24761 | 0,5 % | 7,5 % | 34,0 % | 5,0 % | 91 |
| E38465 | M40406 | 0,0 % | 6,5 % | 27,0 % | 4,5 % | 81 |

| | corregido | mañana |
|---|---|---|
| los cinco se repiten exactamente (mismo orden) | 0 de 200 | 0 de 200 |
| mismo conjunto de cinco | 0 de 200 | 0 de 200 |
| puntos a ≤ 0,1 / 0,5 / 1 punto del quinto (modelo sin perturbar) | 2 / 26 / 116 | 7 / 76 / 271 |
| ídem, mediana de las corridas | 2 / 17 / 51 | 8 / 32 / 112 |
| más frecuentes entre los cinco | E21492 17,5 %, E22217 (Gurgaon) 15 %, E39464 15 %, E23648 13 % | E29420 23,5 %, E30077 12,5 % |

**Dicho claramente: el modelo corregido es más estable que el de la mañana** en cada cifra por análogo (entre los cinco 0,5–13 % frente a 0–2 %; top 20 12,5–40 % frente a 6,5–19,5 %) y tiene menos puntos pegados al quinto (26 frente a 76 a ≤ 0,5); **pero sigue siendo frágil en términos absolutos**: los cinco no se repiten nunca, ningún análogo está entre los cinco en más del 13 % de las corridas, y el gemelo cambia casi siempre (se conserva en 0,5–8 %), porque con la similitud saturada hay ~1.840 celdas lunares casi equivalentes. "Five of the highest-scoring analogs in our model, not a proven best" es la frase correcta. Nota de método: la irradiancia lunar con 2 % de ruido (ilustrativo, de la primera auditoría) amplía el rango de la clave y hace que se emparejen 7.021–7.561 puntos en vez de 6.360 en los dos estados por igual; la comparación entre estados no depende de ello.

## 7. Validación externa (`ra_solar_validation.py`, `out/ra_solar_validation.json`)

Lista `data/benchmark/validation_sites_solar.csv`: 13 positivos (estaciones BSRN áridas o de montaña) y 6 negativos (estaciones del Met Office con poco sol). Percentil del rango = 100·rango/18.777 (menor = mejor); dentro de la fila = porcentaje de los puntos que pasan en la misma fila de 1° de latitud que quedan por delante (la latitud es constante dentro de la fila: 50 = no dice nada más que la latitud).

| sitio | celda | corregido: total | corregido: en su fila | mañana: total | mañana: en su fila | despejado |
|---|---|---|---|---|---|---|
| Tamanrasset | E24305 | 4,7 | 44,2 | 5,4 | 27,9 | 0,642 |
| Gobabeb | E40875 | 3,1 | 4,6 | 11,2 | 60,9 | 0,779 |
| De Aar | E43403 | 15,2 | 19,4 | 22,8 | 18,1 | 0,577 |
| Sede Boqer | E21454 | 10,4 | 33,3 | 25,1 | 25,9 | 0,641 |
| Solar Village | E23626 | 0,3 | 1,5 | 13,1 | 66,2 | 0,670 |
| Gandhinagar | E24012 | 0,2 | 1,5 | 8,3 | 45,0 | 0,663 |
| Gurgaon | E22217 | 4,7 | 33,1 | 14,9 | 33,1 | 0,625 |
| Alice Springs | E40993 | 8,3 | 57,5 | 1,7 | 6,9 | 0,590 |
| Desert Rock (sin gemelo) | E19143 | 63,6 | 28,8 | 34,6 | 8,5 | 0,540 |
| Boulder (sin gemelo) | E17714 | 95,8 | 94,0 | 41,1 | 69,6 | 0,350 |
| Petrolina | E35779 | 11,0 | 4,2 | 15,2 | 15,3 | 0,520 |
| Izaña | E22123 | no pasa (tierra 0,18) | | no pasa | | 0,447 |
| Lampedusa | E19632 | no pasa (tierra 0,002) | | no pasa | | 0,553 |
| 6 negativos UK | | no pasan (irradiancia < 2,5) | | no pasan | | 0,21–0,28 |

| | corregido | mañana |
|---|---|---|
| mediana de los positivos que pasan, clasificación completa | **8,3 %** | 14,9 % |
| positivos en el cuartil superior (de 11 que pasan) | 9 | 8 |
| **mediana dentro de su fila de latitud** | **28,8 %** | **27,9 %** |
| positivos en el cuartil superior dentro de su fila | 5 | 4 |
| positivos en la mitad mejor de su fila | 9/11 | 8/11 |
| separación positivo-negativo | 0,923 | 0,923 |

Dicho claramente: **en la clasificación completa, mejor; dentro de la fila de latitud, igual** (28,8 frente a 27,9; con 11 sitios la diferencia no es interpretable). La corrección no empeora; tampoco demuestra que la idoneidad diga ahora más que la latitud sobre estas estaciones: cambia qué estaciones quedan bien (Solar Village, Gandhinagar, Gobabeb suben al 1,5–4,6 % de su fila; Alice Springs, Tamanrasset y Boulder bajan). La separación 0,923 no informa de la idoneidad: los seis negativos ya los quita la puerta de irradiancia ≥ 2,5 en los dos estados. Los dos sitios sin gemelo (Desert Rock 36,6 N, Boulder 40,1 N) quedan por detrás de los emparejados por construcción.

## 8. Los cinco lugares (`ra_solar_five.py`, `out/ra_solar_five_corrected.json`)

| | tierra | hielo | clase CCI dominante | suelo desnudo | distancia a celda de mar (1°, aprox.) | despejado | gemelo: lat, elev. | en zona |
|---|---|---|---|---|---|---|---|---|
| E40184 | 0,993 | 0 | 110 (mosaico herbáceo) | 0,005 | 207 km | 0,675 | 25,5; −2.187 m | sí |
| E29749 | 0,664 | 0 | **210 (agua)** | 0,020 | 110 km | 0,705 | 17,5; −1.360 m | sí |
| E23648 | 0,926 | 0 | 20 (cultivo regado) | 0,001 | 232 km | 0,662 | 28,5; −2.557 m | sí |
| E29746 | 1,000 | 0 | 120 (matorral) | 0 | 399 km | 0,677 | 17,5; −1.556 m | sí |
| E28670 | 0,964 | 0 | 120 | 0,203 | 156 km | 0,792 | 19,5; −1.320 m | sí |

Lugar: el vecino más cercano por haversine sobre todo `rg_cities1000.csv` (fuerza bruta propia) coincide en nombre y km con `earth_place_detail.bin` en 5/5. Separaciones: mínima 2,97° (E29749–E29746), luego 3,16° y 4,96°; las demás > 22°. Ningún sitio reconocido (bloque 3×3 de la lista BSRN) estuvo entre los saltados. Aviso: E29749 (Eyl) tiene un tercio de mar y su clase más frecuente es agua; pasa la regla (tierra ≥ 0,5). E23648 es cultivo de regadío del Sind, no desierto. Tres de los cinco están en Somalia, a 3–5° entre sí.

## 9. Textos (paquete en final-integration c5f1f6c (fusionado al final; pares y puntuaciones idénticos: recálculo PASS))

Leídos: `similarity.json` `texts` de Paneles (con su `show`), `missions.json` (entrada solar: `known_limitations`, `criteria_set`, `top5`, `weighted_variables`, `reason_codes`), `explain.json` (`missions.solar`) y `variables.json` (incluida la nueva `clear_frac_isccp`). Comprobados contra mis cifras: saturación (1.840 candidatos no recalculado; 78 % ≥ 99 ✔; 514 en 100,00 ✔; similitud del top 100 de 99,00 a 100,00 ✔), P10/P90 0,308/0,671 ✔, 18.777 ✔, 3 sin valor ✔, regla de los cinco ✔, desviaciones ✔, `variables.json` de la nube ✔ (licencia y periodo como en la fuente).

- **F1 (sigue)** `texts.solar_suitability_clouds` (tarjeta de misión y Datos y límites) = `known_limitations[6]`: "35 % of the suitability is the clear-sky fraction". Falso tal como se lee: los pesos suman 0,70 y el peso efectivo es **50 %** (`explain.json`: 50,0 de 100 puntos en el n.º 1). Corrección propuesta: "half of the suitability (weight 0.35 of 0.70)".
- **F3 (corregido en c5f1f6c)** `texts.external_validation_solar`: en d24ebb3 decía "No external validation exists"; ahora describe las 13 + 6 estaciones y sus puestos (Tamanrasset 880, Gobabeb 587, De Aar 2.858, Sede Boqer 1.956, Solar Village 57, Gandhinagar 36, Gurgaon 879, Alice Springs 1.551, Petrolina 2.073): **los nueve coinciden con mi recálculo**; Desert Rock y Boulder sin gemelo, Izaña y Lampedusa sin pasar, 0 de 6 negativos pasan ✔. No dice que dentro de la fila de latitud el resultado es igual que la mañana (28,8 % frente a 27,9 %); recomiendo añadirlo.
- **F4 (sigue)** `missions.json` solar `known_limitations[2]`: "Earth irradiance at the ground, sun geometry and the diurnal amplitude are suitability criteria." Caducado: irradiancia y geometría ya no pesan (solo filtran).
- **Pendiente** `texts.top5_stability_solar` = `known_limitations[5]`: "Stability figures pending the independent re-audit." → cifras de §6 (en el JSON, `stability.corrected`).
- Comprobado correcto: `known_limitations[3]` (6.060 puntos sin temperatura de superficie, todos en la Antártida, ninguno con gemelo ✔), `[4]` (puestos 1, 2, 5, 7 y 9 ✔), saturación ✔.

## Fallos y debilidades

| id | tipo | cifra |
|---|---|---|
| F1 | texto, implementación | "35 %" publicado; peso efectivo 50 % |
| F2 | debilidad de un criterio decidido (renormalización) | E34142 Sulawesi sin dato ISCCP: idoneidad 96,23, puesto 16 |
| F3 | texto caducado en d24ebb3 | corregido en c5f1f6c, cifras comprobadas |
| F4 | texto caducado | known_limitations[2] |
| F5 | debilidad de un criterio decidido | dentro de la fila de latitud, 28,8 % frente a 27,9 %: no mejor que la latitud sobre las BSRN |
| F6 | debilidad de un criterio decidido | despejado y amplitud térmica ρ +0,67: la amplitud resta (−0,206 de la dispersión) |
| — | límite | los cinco nunca se repiten en 200 corridas (ninguno > 13 %); E29749 (Eyl) con clase dominante agua y 66 % de tierra; tres de los cinco en Somalia |

## Reproducción

```
cd "tierra luna/audit"
python ra_solar_recompute.py corrected ../../app/public/data/v2 final_corrected
python ra_solar_recompute.py audited_morning <a493514 bundle> final_morning
python ra_solar_config.py
python ra_solar_data_layer.py <carpeta con los 60 ficheros ISCCP-Basic.HGM 2012-2016>
python ra_solar_robustness.py corrected ; python ra_solar_robustness.py audited_morning
python ra_solar_montecarlo.py corrected 200 20261115 ; python ra_solar_montecarlo.py audited_morning 200 20261115
python ra_solar_validation.py ; python ra_solar_five.py corrected
```
