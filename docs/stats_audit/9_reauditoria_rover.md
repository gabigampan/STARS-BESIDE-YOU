# 9. Re-auditoría independiente de Rover (modelo corregido)

Auditor independiente (sesión propia, no escribió el código auditado). Commit auditado: **d24ebb3** (final-integration, "Engine, second step after the audit (contract revision 8)"), fusionado en `audit-rover`. Inicio: mensaje "AUDIT START d24ebb3" del director, 11:51:48 UTC. Ningún fichero del motor, configuración, tablas, paquete, web ni audio se ha tocado.

**Camino de código propio.** `tierra luna/audit/ra_rover_common.py`, construido sobre la reimplementación independiente de la primera auditoría (`audit/p5_common.py`: tablas, columnas, embudo, idoneidad) y adaptado a las reglas corregidas (puntuación con banda muerta σ, filtro del par, desempate del gemelo, regla de los cinco). No importa nada de `tierra luna/engine`. Antes de usarlo lo comprobé contra el paquete de esta mañana (a493514): igualdad celda a celda (punto 3). Scripts: `ra_rover_config.py` (1), `ra_rover_audit.py` (2, 3, 7, 8, saturación, pendiente mínima), `ra_rover_fallback.py` (3), `ra_rover_weights.py` (5), `ra_rover_mc.py` (6), `ra_rover_texts.py` (9), `ra_rover_summary.py` (JSON). Salidas en `tierra luna/audit/out/ra_rover_*`. Entorno: Python 3.13, numpy, pandas, scipy, geopandas, reverse_geocoder (solo su fichero GeoNames cities1000).

| Punto | Veredicto | Cifra que lo decide |
|---|---|---|
| 1 Configuración | **GO** | 22 de 22 comprobaciones; σ recalculadas 0,265093° y 17,401661 m; ninguna desviación de `mission_scoring.json` |
| 2 Recálculo | **GO** | 0 diferencias en 10.337 puntos (idoneidad, similitud, final, puesto, gemelo, puntuaciones, pares); cotas del filtro comprobadas en los 10.337 pares |
| 3 Vuelta atrás | **GO** | `audited_morning` = paquete a493514 sin una diferencia; cinco E17566, E23945, E18282, E18280, E15395 |
| 4 Datos nuevos | **GO** (no aplica) | ninguna columna suplementaria; `snow_ice_frac` y `mask_fraction` de la tabla principal, orientación correcta |
| 5 Pesos ±10 % | **GO** | 10/10 para cada uno de los cinco, con su gemelo (por saturación, no por robustez del orden) |
| 6 Monte Carlo | **GO** (debilidad de criterio) | entre los cinco 43-87,5 %; lista exacta 10,5 %; grupo empatado conserva 89 % (mediana); gemelo 17,5-38 %; 502 puntos a ≤ 1 del quinto. Menos estable que esta mañana en orden y gemelo |
| 7 Validación | **GO** (debilidad de criterio) | verificados: mediana 8,1 frente a 9,2, cuartil 5/8 = 5/8, separación 0,906 = 0,906 (igual); todos: 0,855 frente a 0,927 (peor); Bardenas 68,2 (44,5) y Tabernas 71,5 (24,7) peor por la idoneidad del equipo |
| 8 Los cinco | **GO** | tierra ≥ 69,7 %, hielo 0, gemelos en zona, nombres = GeoNames más cercano, separación mínima 60,0°; ningún análogo reconocido saltado |
| 9 Textos | **NOT YET** | T1 fórmula de puntuación antigua en `missions.json`; T2 la causa del empate omite la saturación de la idoneidad; T6 estabilidad "pending" (provisional: se relee tras la pasada de textos) |

---

## 1. Configuración frente a las decisiones

`engine_config.json`, conjunto de criterios `corrected` de Rover (bloque principal `real_value_similarity.missions.rover` + `top5_selection`/`criteria_sets`), contra DECISIONS.md (11:23 punto 1-2, 11:28/11:36, 11:51) y research_5 "Para implementar". 22 comprobaciones, **22 correctas** (`out/ra_rover_config.json`):

| Elemento | Configuración | Decidido |
|---|---|---|
| Variables de similitud | pendiente (`slope_deg` ← `slope_iso_deg`) y rugosidad, ambas clave | 11:23 punto 1 |
| Pesos | 0,5 + 0,5 = 1 | 11:23 punto 1 |
| Tolerancias / filtro | 2° y 30 m, multiplicador clave 1 | sin cambio (11:23) |
| Elevación relativa | fuera de similitud y filtro; fila informativa (`info_differences.rover`, `info_in_pairs_file.rover`) | 11:23 (lectura del director) |
| σ pendiente | 0,265093° | fórmula recalculada por mí: √((7,17/(√2·1853))² + (10/(√2·1895,2))²) rad = 0,265093° |
| σ rugosidad | 17,401661 m | √(2·7,17² + 2·10²) = 17,401661 m |
| Puntuación | exp(−½·max(0, \|d\|/σ − 1)²) | 11:51, research 5 |
| Zona | lat ≤ −75 (5.400 celdas), igual que la de esta mañana | sin cambio |
| Cinco | `spread_within_top_tie`, separación 2°, salto de hielo `snow_ice_frac ≥ 0,5`, salto de tierra `mask_fraction < 0,5` | 11:28/11:36; tierra confirmada por el líder a las 12:10 |
| Embudo e idoneidad | iguales a `mission_scoring.json` (puertas 0,5-15° y 5-650 m; pesos 0,45/0,30/0,25 que suman 1); `mission_scoring_deviations: []` | el fichero del equipo no se edita |
| Pendiente mínima 0,5° | se mantiene | 11:23, ver punto "Pendiente mínima" |

Comprobación de la fórmula de σ y de sus fuentes. Diferencia central g = (z₊ − z₋)/(2·dy) con error σz independiente por píxel: σg = √2·σz/(2·dy) = σz/(√2·dy); pendiente pequeña σθ ≈ σg rad. Rugosidad: una diferencia Δz = z(x+L) − z(x) tiene σ = √2·σz. La diferencia Tierra − Luna suma en cuadratura. Correcto. Tamaños de píxel: 1.853 m (60″ de ETOPO; con R = 6.371 km sale 1.853,2 m) y 1.895,2 m (LDEM_16, 1/16° con R = 1.737,4 km); con los valores exactos σ = 0,265080°, diferencia despreciable. Fuentes leídas hoy en su página: ESSD 17, 1835-1849 (MacFerrin et al. 2025): "ETOPO 2022 measures a global RMSE of 7.17 m" frente a ICESat-2 (matiz: es la **media de los RMSE de sub-teselas de 1° sobre tierra**, no un error por píxel); Smith et al. 2010 (GRL 37, L18204, resumen en dspace.mit.edu 1721.1/74221): "the lunar geodetic grid to ∼10 m radial and ∼100 m spatial accuracy with respect to the Moon's center of mass" (error **absoluto**, pesimista para pendiente y rugosidad, como dice research 5). Las cifras de la tabla de candidatos de research 5 (A, C-S1: 254 empatados, 317/422/497 a 0,1/0,5/1 del 5.º) las reproduzco exactamente.

Nada en la configuración sin decisión que lo cubra. Una nota de texto obsoleta: el `why` del salto de tierra dice "TO BE CONFIRMED by the team lead", y el líder lo confirmó a las 12:10 (punto 9).

## 2. Recálculo

Embudo (propio, sobre la tabla de 64.800 celdas): pasan **10.337**. Exclusiones entre celdas con elevación (no exclusivas): pendiente < 0,5°: 12.639; rugosidad < 5 m: 4.352; tierra < 30 %: 3.023; elevación < 1 m: 177; pendiente ausente 462, rugosidad ausente 124; pendiente > 15°: 1. Los bits de fallo del paquete coinciden (177, 12.639, 4.352, 1; tierra 3.275 = 3.023 + 252 celdas de tierra sin elevación; pendiente ausente 714 = 462 + 252; rugosidad ausente 376 = 124 + 252).

Comparación con `earth_rover.bin` y `earth_rover_pairs.bin`, celda a celda, a la precisión publicada (10.337 puntos): **0 diferencias** en idoneidad, similitud, final, puesto, gemelo, puntuaciones por variable (6 decimales) y en los valores Tierra / Luna / diferencia de pendiente y rugosidad de cada par. Emparejados 10.337 (todos), 1.144 gemelos distintos, mayor cuota M59712 con 271 puntos (2,6 %). Los cinco por la regla publicada: **E4037, E50510, E44239, E26510, E26087**, iguales a `missions.json` `top5.ids` (puestos 3, 254, 251, 241, 236).

Tabla de diferencias (10.337 pares, cotas comprobadas en **todos** los pares):

| Variable | Tolerancia = cota del filtro | σ | Mediana | P90 | Máximo | Dentro de σ |
|---|---|---|---|---|---|---|
| pendiente (°) | 2,0 | 0,265 | 0,016 | 0,044 | 0,280 | 99,98 % |
| rugosidad (m) | 30,0 | 17,40 | 1,09 | 2,84 | 16,89 | 100 % |
| elevación relativa (m, solo información) | — | — | 3.410,6 | 5.415,9 | 10.517,3 | — |

10.335 de 10.337 pares tienen las dos diferencias dentro de σ (similitud 100). Esta mañana: pendiente 0,41 / 0,85 / 1,97°, rugosidad 5,34 / 20,55 / 29,97 m, elevación relativa 247,9 / 798,9 / 1.000,0 m (cota 1.000).

## 3. Vuelta atrás ("audited_morning")

Con el conjunto `audited_morning` (parche de `criteria_sets`: pendiente 0,4, rugosidad 0,4, elevación relativa 0,2 secundaria con tolerancia 500 m, puntuación gaussiana, cinco por puesto) mi código reproduce el paquete de a493514 **sin una sola diferencia**: mismo conjunto de 10.337, 10.192 emparejados, 0 diferencias en idoneidad, similitud, final, puesto, gemelo, tres puntuaciones y nueve columnas de pares; cinco E17566, E23945, E18282, E18280, E15395 = puestos 1-5 del paquete (`out/ra_rover_fallback.json`). La vuelta atrás es posible y exacta.

## 4. Datos nuevos

Rover corregido **no usa ninguna columna suplementaria** (`real_data/supplement/`): similitud con `slope_iso_deg` y `roughness_m`, idoneidad con las tres columnas de siempre. Las dos columnas nuevas *en uso* son las de los saltos de los cinco, `snow_ice_frac` y `mask_fraction`, ambas de la tabla principal (`provenance_earth.csv`: ESA CCI / C3S Land Cover 2020 v2.1.1, 300 m, MEASURED). Rango 0-1; orientación comprobada: Groenlandia cumbre y Vostok 1,0 / 1,0 (clase 220), Tamanrasset tierra 1,0 / hielo 0 (clase 200), Amazonia 0,82 / 0 (clase 50), mar Caspio 0 / sin valor, E3872 (mar de Kara) 0,338 de tierra (clase 210). Valores ausentes: `snow_ice_frac` falta solo en celdas sin tierra (0 celdas con tierra sin valor); la regla trata un ausente como "no hielo", lo que no afecta a ningún punto que pase el embudo.

## 5. Robustez a los pesos (±10 %, uno a uno, renormalizados)

Diez perturbaciones en el modelo corregido (3 pesos de idoneidad y 2 de similitud, × 1,1 y × 0,9) y doce en el de esta mañana (3 + 3). Resultado (`out/ra_rover_weights.json`):

| Análogo (corregido) | Sigue entre los cinco | Y conserva su gemelo |
|---|---|---|
| E4037 | 10/10 | 10/10 |
| E50510 | 10/10 | 10/10 |
| E44239 | 10/10 | 10/10 |
| E26510 | 10/10 | 10/10 |
| E26087 | 10/10 | 10/10 |

Los cinco idénticos en 10 de 10 (esta mañana 12 de 12, cada uno 12/12 con su gemelo). El grupo empatado sigue en 254 en las 10. La razón no es robustez del orden sino saturación: los 254 tienen las tres utilidades a 1 (o casi) y similitud 100, de modo que ningún reparto de pesos los separa.

## 6. Estabilidad ante la incertidumbre de los datos (Monte Carlo)

200 ejecuciones (`out/ra_rover_mc_*_first_audit.json`), mismas perturbaciones para los dos modelos (semilla 20261115, ruido de la ejecución k = `default_rng([semilla, k])`), con las incertidumbres de la primera auditoría (`p3_montecarlo.py`, informe 3 F.3): elevación Tierra 7,17 m (doc., ETOPO 2022) y Luna 10 m (doc., LOLA); pendiente y rugosidad 5 % relativo en los dos cuerpos (**ilustrativo**, no hay cifra por celda); `rock_or_bare_frac` 0,05 (**ilustrativo**). Cada ejecución recalcula todo: embudo, idoneidad, gemelos, similitud, final, puesto y los cinco con la regla de su modelo. "Top 20/50 por empates" = menos de 20/50 puntos estrictamente mejores (en el corregido el orden dentro del empate es por id de celda, no por el dato).

| Análogo corregido | Entre los cinco | Top 20 (puesto publicado) | Top 20 (por empates) | Top 50 (por empates) | En el grupo empatado | Conserva gemelo | Pasa el embudo |
|---|---|---|---|---|---|---|---|
| E4037 | **52,5 %** | 72,5 % | 72,5 % | 72,5 % | 72,5 % | 29,5 % | 100 % |
| E50510 | **43,0 %** | 0 % | 43,0 % | 43,0 % | 43,0 % | 30,0 % | 100 % |
| E44239 | **65,0 %** | 0 % | 88,5 % | 88,5 % | 88,5 % | 38,0 % | 96,0 % |
| E26510 | **87,5 %** | 0 % | 100 % | 100 % | 100 % | 17,5 % | 100 % |
| E26087 | **67,0 %** | 0 % | 74,0 % | 74,0 % | 74,0 % | 25,0 % | 83,0 % |

| Análogo de esta mañana | Entre los cinco | Top 20 | Top 50 | Conserva gemelo |
|---|---|---|---|---|
| E17566 | 92,0 % | 100 % | 100 % | 100 % |
| E23945 | 80,5 % | 100 % | 100 % | 100 % |
| E18282 | 75,5 % | 99,5 % | 100 % | 100 % |
| E18280 | 43,0 % | 84,0 % | 97,5 % | 100 % |
| E15395 | 22,5 % | 95,0 % | 99,5 % | 100 % |

| | Corregido | Esta mañana |
|---|---|---|
| los cinco se repiten exactamente | **10,5 %** | 0,0 % |
| mismo conjunto de cinco (cualquier orden) | 10,5 % | 2,5 % |
| listas de cinco distintas en 200 ejecuciones | 60 | 191 |
| puntos a ≤ 0,1 / 0,5 / 1 punto del quinto (mediana; P5-P95) | **311 / 422 / 502** (301-322 / 411-432 / 491-513) | 6 / 13 / 20,5 (5-6 / 11-13 / 17-21) |
| tamaño del grupo empatado (mediana; P5-P95) | 256 (246-265); elegibles 242 (232-252) | — (empate en el máximo: 1) |
| de los 254 empatados, cuántos siguen empatados (mediana; P5-P95) | **89,0 %** (85,8-92,1 %); Jaccard 0,80 (0,76-0,83) | — |
| de los 241 elegibles, cuántos siguen elegibles y empatados | 88,6 % (85,5-91,7 %); Jaccard 0,79 (0,76-0,83) | — |

**Lectura.** El **grupo** empatado es estable (en la mediana se conserva el 89 % de sus miembros) y los cinco salen siempre de él; pero **cuáles cinco** se muestran es poco estable: cada uno sigue en la lista entre el 43 % y el 87,5 % de las veces, la lista exacta se repite el 10,5 % y los gemelos cambian en el 62-82,5 % de las ejecuciones (dentro de σ hay muchas celdas lunares equivalentes). E26087 y E44239 tienen pendiente 0,523° y 0,547°, junto al mínimo de 0,5°: con un 5 % de ruido salen del embudo el 17 % y el 4 % de las veces. Frente a esta mañana: la pertenencia de cada uno de los cinco es parecida (43-87,5 % frente a 22,5-92 %), la lista exacta se repite más (10,5 % frente a 0 %), pero el gemelo y el puesto son mucho menos estables (gemelo 17,5-38 % frente a 100 %) y hay unas 50 veces más puntos a menos de un punto del quinto. **Dicho llanamente: el modelo corregido es menos estable que el de esta mañana en el orden y en el gemelo, y comparable en qué sitios salen; la estabilidad que sí tiene es la del grupo empatado.** Es consecuencia del criterio decidido (empate por incertidumbre de medida + idoneidad saturada), no de la implementación.

Cifras para la web (frase `top5_stability`): número 1 (E4037) 52,5 % entre los cinco y 72,5 % en el top 20; número 2 (E50510) 43,0 % y 43,0 %; número 3 (E44239) 65,0 % y 88,5 %; número 4 (E26510) 87,5 % y 100 %; número 5 (E26087) 67,0 % y 74,0 % (top 20 "por empates"; por puesto publicado el 2-5 son 0 % porque el orden dentro del empate es por id); 200 simulaciones; ±10 % en un peso: 5 de 5 siguen; los cinco se repiten exactamente 10,5 %; el grupo empatado conserva una mediana del 89 % de sus miembros.

## 7. Validación externa

Sitios de `rover_preset.py` (positivos de movilidad y discordantes), en su celda de 1°, percentil del puesto publicado entre los emparejados (menor = mejor; entre paréntesis el percentil con empates a rango medio, que solo cambia en el grupo empatado). "Sin verificar" = coordenadas del benchmark marcadas como escritas de memoria (regla de la primera auditoría).

| Sitio | Papel | Celda | Corregido | Esta mañana |
|---|---|---|---|---|
| Ramon | + | E21454 | **3,6** | 6,2 |
| Qaidam | + | E18633 | 4,1 | **0,2** |
| Haughton | + | E5130 | 4,2 | **1,7** |
| Yungay | + | E41150 | **8,1** | 9,2 |
| MDRS | + | | **20,5** | 28,9 |
| Bardenas | + | E17098 | 68,2 | **44,5** |
| Tabernas | + | E18897 | 71,5 | **24,7** |
| Dhofar | + | | no pasa (rugosidad < 5 m) | no pasa |
| Erfoud (sin verificar) | + | | 3,7 | 2,6 |
| Dumont Dunes (sin verificar) | + | | 69,0 | 22,9 |
| Death Valley (sin verificar) | + | | 80,1 | 37,4 |
| El Soplao | − | | 95,4 | 89,5 |
| Concordia | − | | no pasa | no pasa |
| HI-SEAS (sin verificar) | − | | 83,7 | 51,9 |
| Rio Tinto (sin verificar) | − | | 42,4 | 44,6 |
| NEEMO (sin verificar) | − | | no pasa | no pasa |

| Resumen | Corregido | Esta mañana |
|---|---|---|
| Verificados: mediana de los 7 positivos clasificados | **8,1** | 9,2 |
| Verificados: positivos en el cuartil superior | 5 de 8 | 5 de 8 |
| Verificados: pares positivo-negativo con el positivo mejor | 0,906 | 0,906 |
| Todos: mediana de los 10 positivos clasificados | **14,3** | 16,0 |
| Todos: positivos en el cuartil superior | 6 de 11 | **7 de 11** |
| Todos: pares positivo-negativo con el positivo mejor | 0,855 | **0,927** |

**Lectura: igual con la lista verificada (la que la web publica), peor con la lista completa.** Mejoran Ramon, Yungay y MDRS; empeoran Qaidam y Haughton (siguen en el 4 %) y, sobre todo, Bardenas, Tabernas, Dumont Dunes y Death Valley. La causa es estructural: con 10.335 pares de similitud 100 el final es 50 + idoneidad/2 (Spearman final-idoneidad **1,000**; esta mañana 0,498), así que el ranking corregido **es** el ranking de idoneidad del equipo.

**Bardenas y Tabernas, criterio a criterio** (valor de la celda, utilidad, puntos de idoneidad perdidos = 100 × peso × (1 − utilidad)):

| Celda | Pendiente (bueno 1°, malo 15°; peso 0,45) | Rugosidad (bueno 30 m, malo 650 m; 0,30) | Suelo desnudo o vegetación rala (bueno 0,7; 0,25) | Idoneidad | Similitud | Final | Puesto |
|---|---|---|---|---|---|---|---|
| Bardenas E17098 | 1,911° → 0,935 (−2,93) | 77,0 m → 0,924 (−2,27) | **0,018 → 0,025 (−24,37)** | 70,43 | 100 | 85,21 | 7.043 de 10.337 (68,2 %) |
| Tabernas E18897 | 3,165° → 0,845 (−6,96) | 110,7 m → 0,870 (−3,91) | **0,146 → 0,209 (−19,78)** | 69,36 | 100 | 84,68 | 7.385 (71,5 %) |

Su terreno empareja perfectamente (gemelos: 1,90° / 74,1 m y 3,15° / 110,6 m; similitud 100). Pierden idoneidad en dos frentes a la vez: (a) el criterio de suelo, que solo da utilidad 1 desde 0,7 de fracción desnuda o rala, les quita 24,4 y 19,8 puntos (a 1°, ESA CCI clasifica sus celdas sobre todo como cultivo y matorral: 1,8 % y 14,6 %); (b) son más empinados y rugosos que las llanuras (utilidades 0,93-0,85). La mediana del embudo emparejado es tierra llana y vegetada (fracción desnuda o rala: mediana 0,008, P75 0,196; idoneidad mediana 74,16) que, con pendiente ≈ 1° y rugosidad ≈ 30 m, saca unos 75 puntos sin suelo desnudo: 7.042 puntos así quedan por delante de Bardenas. Esta mañana la similitud variaba (mediana 93) y los subía; ahora vale 100 para casi todos y no ordena. Es una debilidad de un **criterio decidido** (`rock_or_bare_frac` del equipo, sin cambiar, a 1°), no un fallo de implementación.

Otras filas utilizables del benchmark (coordenadas verificadas; informativas): Askja 6,2 %, Dallol 5,0 %, Holuhraun 21,0 %, Tírez 22,1 %, Ries 32,4 %, Black Point 58,9 %, Craters of the Moon 62,3 %, Etna 81,3 %, Mauna Kea/Kilauea 83,7 %, McMurdo 98,4 %; Timanfaya, La Corona, Teide y Makgadikgadi no pasan. Ningún sitio reconocido está en el grupo empatado de 254.

## 8. Los cinco lugares

| # | Celda | Lugar más cercano (GeoNames, círculo máximo; igual en el paquete) | Tierra | Hielo | Agua | Clase CCI | Desnudo/raro | A celda toda agua | Gemelo (lat) | Rasgo IAU | Pendiente T/L (°) | Rugosidad T/L (m) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E4037 (78,5; −102,5) | Gjoa Haven, Nunavut, **1.115,8 km** | 0,697 | 0 | 0,303 | 200 | 0,868 | 89 km | M63714 (−86,5) | Sverdrup (69 km) | 0,770 / 0,793 | 29,34 / 29,50 |
| 2 | E50510 (−50,5; −69,5) | Comandante Luis Piedra Buena, Santa Cruz, 70,8 km | 0,928 | 0 | 0,072 | 150 | 0,710 | 179 km | M59438 (−75,5) | Zeeman (51 km) | 0,722 / 0,739 | 29,16 / 30,62 |
| 3 | E44239 (−32,5; 139,5) | Peterborough, South Australia, 81,0 km | 1,000 | 0 | 0 | 150 | 0,758 | 454 km | M59712 (−75,5) | Schrödinger (24 km) | 0,547 / 0,547 | 18,18 / 15,66 |
| 4 | E26510 (16,5; 50,5) | Dahasuways, Al Mahrah (Yemen), 89,7 km | 1,000 | 0 | 0 | 200 | 1,000 | 247 km | M63711 (−86,5) | Haynes (68 km) | 0,643 / 0,677 | 21,87 / 19,22 |
| 5 | E26087 (17,5; −12,5) | Barkewol, Assaba (Mauritania), 95,6 km | 1,000 | 0 | 0 | 200 | 0,759 | 530 km | M61294 (−80,5) | Drygalski (29 km) | 0,523 / 0,510 | 26,42 / 26,80 |

Los cinco son tierra firme (≥ 69,7 % de tierra, 0 % de hielo, clase CCI suelo desnudo 200 o vegetación rala 150), los cinco gemelos están en la zona (lat ≤ −75), el nombre coincide con el lugar más cercano de verdad en los 5 casos, y la separación mínima entre ellos es **60,0°** (más de 6.600 km). "A celda toda agua" es una aproximación a 1° de la distancia a la costa (centro de la celda más cercana con 0 % de tierra). Aviso: E4037 (isla Ellef Ringnes / Amund Ringnes, Ártico canadiense) tiene el lugar poblado más cercano a 1.116 km; el nombre es correcto por la regla pero no localiza el sitio.

**Qué excluye cada regla** (punto 2 del líder, 12:10): de los 254 empatados, el salto de hielo **0**, el de tierra < 50 % **13** (E3872, E4035, E5114, E5309, E5824, E5825, E5832, E5833, E6191, E6923, E7263, E22128, E41234; los 13 de clase dominante agua, 210), ambos 0; la regla de 2° **no actúa** (la regla de dispersión ya los separa 60°; 5 empatados elegibles están a menos de 2° de alguno de los cinco). Sin el salto de tierra los cinco serían E3872 (mar de Kara, 33,8 % de tierra), E50509, E44239, E26087, E26151; sin el de hielo, los mismos cinco publicados; sin la regla de 2°, los mismos. En todo el ranking, el salto de hielo afectaría a 1.485 puntos y el de tierra a 671. Ningún análogo reconocido queda fuera por estas reglas (ninguno está en el grupo empatado).

## Saturación de la idoneidad (punto 1 del líder, 12:10)

La idoneidad también está saturada: **253 puntos publican idoneidad 100,00** (250 exactamente 100). Los 254 empatados en el final tienen **todos** la utilidad 1 de pendiente (≤ 1°; rango 0,50-0,96°) y la utilidad 1 de suelo desnudo o raro (≥ 0,7; rango 0,707-1,0); 250 de 254 tienen la utilidad 1 de rugosidad (≤ 30 m; rango 14,6-30,19 m: 4 están entre 30,0 y 30,2 m y su idoneidad 99,99x redondea el final a 100,00). En todo el embudo: pendiente con utilidad 1 en 3.291 puntos (31,8 %), rugosidad en 2.144 (20,7 %), suelo en 930 (9,0 %); las tres a la vez en 250. Por eso el empate no es "de medida" solamente: 10.335 pares están dentro de σ, y lo que deja 254 arriba es que **los tres criterios del equipo se saturan** en esos puntos (umbrales "bueno" de 1°, 30 m y 0,7). Debilidad de criterio decidido (los "bueno" del equipo, a 1° de resolución), no de implementación; hay que decirla en la web (punto 9).

## Pendiente mínima de 0,5° (punto 3 del líder)

Reproduzco **todas** las cifras de DECISIONS.md (medidas a las 11:23 con la puntuación de tolerancia, regla A) y las repito con la regla publicada (C, banda σ):

| | A con mínimo | A sin mínimo | C con mínimo (publicado) | C sin mínimo |
|---|---|---|---|---|
| pasan / emparejados | 10.337 / 10.337 | 18.184 / 18.184 | 10.337 / 10.337 | 18.184 / 18.184 |
| gemelos distintos | 1.166 | 1.181 | 1.144 | 1.161 |
| mayor cuota de un gemelo | 2,6 % (M63712, 265) | **13,9 %** (M62913, 2.522) | 2,6 % (M59712, 271) | **16,4 %** (M62913, 2.984) |
| top 5 del ranking | E3872, E4037, E4042, E4742, E4750 | E3675, E3872, E4037, E4042, E4044 | E3872, E4035, E4037, E4038, E4042 | E3675, E3676, E3872, E4028, E4035 |
| top 50: coinciden / añadidos (todos con pendiente < 0,5°) | — | 22 / 28 | — | 24 / 26 |
| agua (CCI 210) en el top 50 | 4 | 13 | 12 | 25 |
| empatados en el máximo | 74 | 412 | 254 | 1.321 |
| Qaidam / Haughton / Ramon / Yungay (%) | 4,0 / 4,2 / 3,6 / 8,1 | 8,3 / 8,4 / 8,0 / 11,6 | 4,1 / 4,2 / 3,6 / 8,1 | 8,3 / 8,4 / 8,0 / 11,6 |
| MDRS / Tabernas / Bardenas (%) | 20,5 / 71,3 / 68,2 | 22,2 / 83,7 / 81,9 | 20,5 / 71,5 / 68,2 | 22,2 / 83,8 / 81,9 |
| verificados: mediana de positivos | 8,1 | 11,6 | 8,1 | 11,6 |

De los 7.847 añadidos: 2.862 hielo o nieve (2.856 de clase 220), 373 agua, 777 suelo desnudo. Hielo (≥ 0,5) en el top 50: 0 en todos los casos. Con la regla publicada el efecto es el mismo o mayor: sin el mínimo los cuatro análogos de movilidad pierden 4-5 puntos de percentil, el empate en la cabeza pasa de 254 a 1.321 y un gemelo acumula el 16,4 %. **Mantenerlo está justificado por su efecto**; sigue sin fuente externa y así debe decirse.

## 9. Los textos

Leídos todos los textos de Rover del paquete (`out/ra_rover_texts.json`: `similarity.json` `texts` con su `show`, `missions.json` rover —incluidos `known_limitations`, `similarity`, `top5`, `external_validation`—, `explain.json`, `variables.json`). Cifras comprobadas con las mías:

| Texto | Cifra | Mía | |
|---|---|---|---|
| `rover_tie` / `ties_at_top_rover` | 254 de 10.337 empatados en 100,00; 241 tras los saltos; σ 0,27° y 17,4 m | 254; 241; 0,265 / 17,40 | correcto |
| `surface_classes_rover` | 1.506 hielo (≥ 0,5 o clase "hielo"), el mejor n.º 1.089, 0 en top 50; 1.145 agua CCI 210, el mejor n.º 1, 12 en top 50, 0 entre los cinco | 1.506; 1.089; 0; 1.145; 1; 12; 0 | correcto |
| `rover_suitability_one_criterion` | Spearman 0,97 | 0,9726 | correcto |
| `known_limitations` 2 | gemelos ≈ 150 K más fríos (mediana) | 148,98 K (9.181 pares con temperatura) | correcto |
| `external_validation_rover` | Bardenas 68,2, Tabernas 71,5, MDRS 20,5, Yungay 8,1, Ramon 3,6, Haughton 4,2, **Qaidam 4,0**, El Soplao 95,4; Dhofar y Concordia no pasan | 68,16; 71,49; 20,53; 8,13; 3,57; 4,16; **4,05 (puesto 419/10.337)**; 95,42 | correcto salvo el redondeo de Qaidam (4,05 → "4,0"; el director escribe 4,1): menor |
| `missions.json` `top5.ids` | E4037, E50510, E44239, E26510, E26087, puestos 3, 254, 251, 241, 236 | iguales | correcto |
| `top5_stability_rover` | "pending" | cifras del punto 6 | **por rellenar** |

Problemas (todos de texto; ninguno cambia un par o una puntuación):

* **T1 — fórmula antigua publicada.** `missions.json` `similarity.score` dice `s = exp(-0.5 * (|earth value - moon value| / tolerance)^2)`; la puntuación usada es la de banda muerta `exp(-0.5·max(0, |d|/σ − 1)²)` con σ 0,265093° y 17,401661 m (lo que dice `engine_config` `uncertainty_scale`). Y `similarity_meaning_real_values` ("each variable scores lower the further apart the two values are") no vale dentro de σ. Resto de la regla anterior.
* **T2 — la causa del empate está incompleta.** `rover_tie` y `top5.rule` dicen que los 254/241 empatan porque su diferencia con el gemelo está dentro del error de medida. Eso es verdad de **10.335** pares, no de 254. Lo que deja a 254 arriba es que además **su idoneidad está saturada**: los 254 tienen pendiente ≤ 1° y fracción desnuda o rala ≥ 0,7 (utilidad 1) y 250 rugosidad ≤ 30 m. Hay que decirlo (punto 1 del líder) y decir que el final es entonces 50 + idoneidad/2 (Spearman 1,000), es decir, que el orden de Rover es el de la idoneidad del equipo.
* **T3 — "241 sites tie at the top score"** en `top5.rule` (frase `spread_within_top_tie` con `{tied_n}` = 241). El paréntesis nuevo ("cells less than half ice and at least half land") lo hace correcto, pero junto a `rover_tie` ("254 ... share the top final score") se lee como dos cifras para lo mismo; mejor "254 sites tie ...; 241 of them are at least half land and less than half ice".
* **T4 — nota obsoleta en la configuración:** el `why` del salto de tierra dice "TO BE CONFIRMED by the team lead"; confirmado a las 12:10.
* **T5 — lugares lejanos.** El número 1 mostrado (E4037) se nombra por Gjoa Haven, a 1.116 km. Correcto por la regla, pero el texto del par debería decir la distancia (si la web no la muestra ya) para no sugerir que el sitio está en Gjoa Haven.
* **T6 —** `top5_stability_rover` sigue en "pending": rellenar con las cifras del punto 6 (en el JSON, `stability`).

**Pendiente:** el director avisa de que en final-integration corre una pasada solo de textos; vuelvo a fusionar al final y releo estas notas en el veredicto final.

## Veredicto

**Recomendación: publicar el Rover corregido** (con las correcciones de texto T1, T2 y T6 antes de publicar, que no cambian ningún número).

Por qué, en cuatro cifras:
1. La implementación es exacta: 0 diferencias en 10.337 puntos, y la vuelta atrás reproduce esta mañana sin una diferencia.
2. Quita artefactos de esta mañana: el mayor gemelo pasa del 19,9 % (M61116, 2.033 puntos) al 2,6 %; la elevación relativa sin sentido físico deja de decidir 1 de cada 5 puntos de similitud; ninguno de los cinco es agua ni hielo (esta mañana el 1 del ranking corregido sin salto sería E3872, 33,8 % de tierra).
3. La validación con la lista verificada queda igual (mediana 8,1 frente a 9,2; separación 0,906 en los dos) y Ramon 3,6, Qaidam 4,1, Haughton 4,2 y Yungay 8,1 siguen en el 10 % superior.
4. El grupo empatado es estable (89 % de sus miembros se conservan en la mediana de 200 simulaciones) y la web puede decir, con cifras, que los cinco son una muestra de él.

Debilidades que hay que publicar, y de quién son:
* **De criterios decididos (no de implementación):** similitud saturada (10.335 de 10.337 pares en 100) e idoneidad saturada en la cabeza (254 con las tres utilidades a 1 o casi): el orden de Rover es el de la idoneidad del equipo (Spearman 1,000); Bardenas y Tabernas caen al 68 y 71 % por el criterio de suelo desnudo a 1° (pierden 24,4 y 19,8 puntos) y por ser más empinados que las llanuras; los cinco concretos son poco estables (lista exacta 10,5 %, gemelo 17,5-38 %); la pendiente mínima de 0,5° sigue sin fuente, justificada por su efecto (sin ella: 1.321 empatados, un gemelo con el 16,4 %, los cuatro análogos 4-5 puntos de percentil peor) y deja a E26087 (0,523°) fuera del embudo en el 17 % de las simulaciones.
* **De implementación / textos:** T1-T6 del punto 9.
