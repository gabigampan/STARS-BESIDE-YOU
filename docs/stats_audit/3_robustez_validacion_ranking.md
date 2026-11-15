# Auditoría 3: robustez (punto 5), validación externa (punto 6) y estadística del ranking (punto F)

Revisor independiente (no escribió el código revisado). Estado auditado: rama `final-integration`, motor en el commit `42d8bba`, bundle `app/public/data/v2` (contract revision 6, engine 3.2.0). Fecha: 2026-11-15. No se ha modificado nada del repositorio fuera de `tierra luna/audit/p3_*.py`, `tierra luna/audit/out/p3_*` y este fichero. No se ha generado, editado ni borrado ningún audio. No se ha consultado NASA POWER ni Google Earth Engine (no lo pedían estos puntos).

Todas las cifras salen de código propio (`tierra luna/audit/p3_common.py`): resolución de columnas, embudo, idoneidad, variables derivadas (elevación relativa con media cos-latitud, insolación en el techo de la atmósfera por integración numérica propia), percentiles mid-rank (`scipy.stats.rankdata`), filtro de pareja, puntuaciones gaussianas, búsqueda de gemelo, final y rango. No importa ningún módulo de `tierra luna/engine`, ni `mission_scoring.py`, ni scripts de otros auditores. Lee las tablas, `mission_scoring.json`, `engine_config.json`, `datasets.json`, `column_aliases.json` y el bundle (solo para las 280 celdas de la zona de Base lunar, columna `region` de `moon_base.bin`, y para comparar).

Cada script se relanza con una orden (desde `tierra luna/audit/`, con el Python del entorno):

| Script | Qué hace | Salida |
|---|---|---|
| `python p3_baseline.py` | reproduce el ranking publicado | `out/p3_baseline.json` |
| `python p3_robustness.py` | punto 5 (pesos ±10 %, quitar secundarias) | `out/p3_robustness.json`, `out/p3_robustness_runs.csv` |
| `python p3_validation.py` | punto 6 (sitios conocidos, parejas absurdas) | `out/p3_validation.json` |
| `python p3_ranking_stats.py` | F.1 y F.2 (dispersión, empates, saltos) | `out/p3_ranking_stats.json` |
| `python p3_percentile_unc.py` | F.3 (cuánto se mueven los percentiles) | `out/p3_percentile_unc.json` |
| `python p3_montecarlo.py MISIÓN [RUNS] [FACTOR] [SEMILLA] [SUBCONJUNTO]` | F.4 Monte Carlo (determinista por semilla) | `out/p3_mc_<misión>_f<factor>[...].json` |
| `python p3_mc_summary.py` | resumen de todos los Monte Carlo | `out/p3_mc_summary.json` |

Ejecuciones hechas: `p3_montecarlo.py rover 200 1.0`, `solar 200 1.0`, `lunar_base 200 1.0`, `lunar_base 200 0.5`, `lunar_base 100 2.0`, y las de descomposición `solar 60 1.0 20261115 only:EARTH:irradiance_kwh_m2_day`, `lunar_base 200 1.0 20261115 only:EARTH:lst_diurnal_amp_k`, `lunar_base 200 1.0 20261115 except:EARTH:lst_diurnal_amp_k`.

## 0. Base: reproducción independiente del ranking publicado

`out/p3_baseline.json`:

| Misión | Pasan el embudo (mío / bundle) | Con gemelo (mío / bundle) | Gemelo igual | Rango igual | Top 5 y gemelos del audio |
|---|---|---|---|---|---|
| Rover | 10.337 / 10.337 | 10.192 / 10.192 | 100 % | 99,90 % | 5/5 rango, gemelo y final |
| Placas solares | 18.777 / 18.777 | 6.360 / 6.360 | 100 % | 99,87 % | 5/5 |
| Base lunar | 2.419 / 2.419 | 450 / 450 | 100 % | 100 % | 5/5 |

Diferencias máximas: similitud y idoneidad ≤ 0,005 (el bundle publica 2 decimales), final publicado ≤ 0,01. Las 10 (Rover) y 8 (Solar) diferencias de rango están todas por debajo del rango 4.000 y son empates de redondeo a la segunda cifra (finales del tipo 79,40x que mi `np.round` y el `round` de Python del motor llevan a lados distintos de .xx5); no afectan a ningún top 50. La insolación en el techo de la atmósfera calculada por mí (integración numérica en tiempo y ángulo horario, Kepler por Newton) difiere de la columna publicada `d.irradiance_toa_kwh_m2_day` en 6,3e-6 kWh/m2/día como máximo (precisión float32), y da 9,974 / 8,765 / 7,367 / 5,672 a 0 / 30 / 45 / 60 grados frente a los valores de referencia 9,97 / 8,77 / 7,37 / 5,67 de `engine_config.json` `toa_insolation`.

Conclusión: las 15 parejas del audio son exactamente lo que el modelo, tal como está configurado, produce. Lo que sigue mide cuánto dependen de los pesos, de las variables y de la incertidumbre de los datos.

## Veredictos

| Punto | Veredicto | En una línea |
|---|---|---|
| 5 Robustez | **NOT YET** | Con pesos ±10 % sobreviven 13 de 15 parejas (todas las de Rover); con todas las perturbaciones, 7 de 15: el top 5 de Rover entero lo decide la secundaria `elevation_rel_m`, y los quintos de Solar y Base lunar son empates prácticos. Sin fallo de código; decisiones para el líder (Fallos 2 y 3). |
| 6 Validación externa | **NOT YET** | El filtro rechaza el 100 % de las parejas absurdas construidas y el 94-99 % de las aleatorias; los análogos de movilidad conocidos quedan arriba por el final (mediana percentil 9,2), pero Bardenas (BASEPROD) queda por debajo de la mediana, la similitud sola no los separa de los discordantes, y Solar y Base lunar no tienen validación externa positiva (Fallos 5 y 6). |
| F Estadística del ranking | **NOT YET** | El top 5 de Solar no se distingue de cientos de puntos (72 a ≤ 0,5 del quinto) y no sobrevive a la incertidumbre documentada (0 de 200 corridas); Base lunar tampoco (0 de 200); Rover sí en sus tres primeros. La frase grabada "the five best analogs on Earth" va más allá de lo que las cifras sostienen (Fallo 1). |

Regrabación de audio: ninguna pareja grabada es incorrecta para el modelo enviado (sección 0). Lo único que estos puntos señalan en el audio es la frase "the five best analogs (on Earth)" de 3 pistas (`m1_rover.mp3`, `m2_solar.mp3`, `m3_base.mp3`); regrabarlas o compensarlo en la web lo decide el líder (Fallo 1).

## 5. Robustez

### 5.1 Método

Para cada misión, una perturbación cada vez, todo recalculado desde cero (embudo, idoneidad, gemelos, similitud, final y rango):

* cada peso de idoneidad (`mission_scoring.json` `soft`) multiplicado por 1,1 y por 0,9, y todos los pesos de idoneidad renormalizados a su suma original;
* cada peso de similitud (`engine_config.json` `real_value_similarity.missions.<m>.variables`) multiplicado por 1,1 y por 0,9, y renormalizados a 1;
* cada variable secundaria de similitud eliminada, con dos tratamientos del filtro de pareja: **"both"** (la variable sale de la media ponderada **y** del filtro: la regla deja de conocerla) y **"sim_only"** (peso 0 pero su cota de 2 × tolerancia sigue aplicándose en el filtro). Los pesos restantes se renormalizan.

Rover: 6 + 6 + 2 = 14 perturbaciones; Placas solares: 12 + 6 + 4 = 22; Base lunar: 12 + 8 + 4 = 24. (Otros agentes midieron ±20 % para otro documento; esto es independiente.)

### 5.2 Resultados por pareja del audio (`out/p3_robustness.json`)

| Misión | Rango audio | Celda Tierra (lugar) | En top 5 | Mismo rango | Mismo gemelo | Peor rango y perturbación |
|---|---|---|---|---|---|---|
| Rover | 1 | E17566 (Bayinbaolige) | 12/14 | 12/14 | 13/14 | 394, quitar `elevation_rel_m` (both) |
| Rover | 2 | E23945 (Tamanrasset) | 12/14 | 12/14 | 13/14 | 452, ídem |
| Rover | 3 | E18282 (Ehen Hudag) | 12/14 | 12/14 | 13/14 | 357, ídem |
| Rover | 4 | E18280 (Banqiao) | 12/14 | 12/14 | 13/14 | 448, ídem |
| Rover | 5 | E15395 (Buga) | 12/14 | 12/14 | 13/14 | 447, ídem |
| Solar | 1 | E38464 (Derby) | 22/22 | 22/22 | 20/22 | 1 |
| Solar | 2 | E38105 (Derby) | 22/22 | 22/22 | 18/22 | 2 |
| Solar | 3 | E38744 (Maintirano) | 22/22 | 22/22 | 20/22 | 3 |
| Solar | 4 | E37746 (Kununurra) | 22/22 | 22/22 | 16/22 | 4 |
| Solar | 5 | E38465 (Derby) | 14/22 | 14/22 | 20/22 | 6 (8 perturbaciones de pesos de idoneidad) |
| Base lunar | 1 | E17538 (Aheqi) | 24/24 | 11/24 | 24/24 | 5, quitar `slope_deg` |
| Base lunar | 2 | E16830 (Mori) | 24/24 | 13/24 | 24/24 | 2 |
| Base lunar | 3 | E15751 (Burenhayrhan) | 24/24 | 14/24 | 22/24 | 5 |
| Base lunar | 4 | E21054 (Tinghir) | 20/24 | 14/24 | 24/24 | 7, quitar `slope_deg` |
| Base lunar | 5 | E17187 (Ewirgol) | 16/24 | 14/24 | 24/24 | 8, quitar `roughness_m` (both) |

**Sobreviven a todas las perturbaciones: 7 de 15** (Rover 0, Solar 4, Base lunar 3). **Si solo se cuentan los cambios de peso de ±10 %** (sin quitar variables): 13 de 15 (Rover 5/5 en sus 12; Solar 4/5; Base lunar 4/5).

Parejas que caen con facilidad y qué las tumba:

* **Rover, las cinco a la vez, al quitar la única secundaria (`elevation_rel_m`, 20 %).** Con "both" el top 5 entero pasa a ser E3872, E4037, E4042, E4742, E4750 y las cinco del audio bajan a los rangos 357-452; con "sim_only" pasa a E11627, E40874, E11626, E6385, E6408 (las del audio a 46-143). Es decir, el top 5 de Rover lo decide la elevación relativa (20 % del peso), no la pendiente y la rugosidad, que en el top 50 están casi saturadas. Con pesos ±10 % el top 5 de Rover no se mueve en ninguna de las 12 perturbaciones.
* **Solar, la quinta (E38465, 218 km al NE de Derby)**: baja al puesto 6 y entra E38385 en 8 de las 12 perturbaciones de pesos de idoneidad (`irradiance_kwh_m2_day` ×0,9, `sun_elev_max_deg` ×1,1 y ×0,9, `sun_low_frac_0_5deg` ×1,1, `slope_deg` ×1,1 y ×0,9, `lst_diurnal_amp_k` ×1,1, `roughness_m` ×1,1). La distancia entre el 5.º y el 6.º es 0,01 puntos de final (sección F.2).
* **Base lunar, la quinta (E17187, Ewirgol)**: sale en 8 de 24 (6 de ellas cambios de peso ±10 %: `lst_diurnal_amp_k` ×1,1, `tmin_c` ×0,9, `irradiance_kwh_m2_day` ×1,1, `permafrost_class` ×0,9 de idoneidad; `tmin_k` ×0,9 y `slope_deg` ×1,1 de similitud); la sustituye E42949. **La cuarta (E21054, Tinghir)** solo sale al quitar una secundaria (`slope_deg` o `roughness_m`). Los puestos 1 y 2 (72,29 y 72,28) se intercambian en 11 de 24 perturbaciones: el orden entre ellos no está determinado.

## 6. Validación externa

### 6.1 Sitios conocidos

Fuente: `tierra luna/data/benchmark/analog_benchmark.csv` (44 sitios con fuente). Regla de exclusión (coordenadas marcadas como no verificadas en el propio fichero): `coord_quality` contiene "from memory", o `source_status` empieza por "FROM MEMORY", o `source_status` dice que la ubicación es de memoria. **Quedan fuera 15**: ES01 Rio Tinto, MA03 Death Valley, MA04 Dumont Dunes, MA09 Axel Heiberg, MA12 Lambahraun, MA15 Erfoud, MA18 Pilbara, BO01 Lonar, MO02 Meteor Crater, MO03 Cinder Lake, MO08 Sudbury, MO09 Mistastin, MO10 Pavilion Lake, OP02 HI-SEAS, OP03 NEEMO. **Se usan 29.** Celda = fila floor(90 − lat), columna floor(lon + 180). Mauna Kea (MO05) y Kilauea (MO06) caen en la misma celda E25224.

Percentil de rango = 100 × (rango − 0,5) / N clasificados (0 = mejor). "Mejor sim. sin filtro" = la mayor similitud contra cualquier celda de la zona ignorando el filtro (solo diagnóstico).

**Rover** (N = 10.192). Positivos de `rover_preset.py` `MOBILITY_POSITIVES` con coordenadas verificadas:

| Sitio | Celda | Embudo | Similitud | Idoneidad | Final | Rango (percentil) |
|---|---|---|---|---|---|---|
| MA14 Qaidam (Lenghu) | E18633 | pasa | 96,51 | 99,02 | 97,77 | 25 (0,2 %) |
| MA06 Haughton | E5130 | pasa | 92,00 | 98,89 | 95,44 | 172 (1,7 %) |
| MA16 Makhtesh Ramon | E21454 | pasa | 85,75 | 99,43 | 92,59 | 629 (6,2 %) |
| MA01 Atacama Yungay | E41150 | pasa | 89,11 | 93,19 | 91,15 | 939 (9,2 %) |
| ES04 Tabernas | E18897 | pasa | 99,73 | 69,36 | 84,55 | 2.516 (24,7 %) |
| MA05 MDRS | E18429 | pasa | 90,45 | 77,38 | 83,92 | 2.949 (28,9 %) |
| ES06 Bardenas Reales (BASEPROD) | E17098 | pasa | 94,26 | 70,43 | 82,34 | 4.532 (44,5 %) |
| MA17 Dhofar (Marmul) | E25795 | **no pasa** | — | — | — | — |

Discordantes de `MOBILITY_MISMATCHES` con coordenadas verificadas: OP01 Concordia **no pasa** el embudo (bien); ES08 El Soplao pasa con similitud **98,57**, final 76,27, rango 9.126 (89,5 %, bien por el final). Otros positivos del CSV para movilidad: MA11 Holuhraun 16,3 %, MO07 Craters of the Moon 24,5 %, MO11 Etna (ARCHES) 42,6 %, MO04 Black Point 43,2 %, MO05/06 Mauna Kea/Kilauea 51,9 %.

Lectura: por el **final**, la mediana de los 7 positivos clasificados está en el percentil 9,2 y el discordante clasificado en el 89,5: el ranking ordena en la dirección correcta. Pero **Bardenas, el sitio de referencia BASEPROD, queda por debajo de la mediana de los positivos**, que es exactamente el aviso que `rover_preset.validate_rover_ranking` emite ("Bardenas scores below the median of mobility analogs; review before the pitch"). Y por la **similitud sola** la separación no existe: El Soplao (98,57, discordante) y McMurdo (99,75) tienen más similitud que Bardenas (94,26), MDRS (90,45) o Yungay (89,11). La mediana de similitud de todos los clasificados es 93,29. Quien separa positivos de discordantes es la idoneidad, no la similitud con la Luna.

**Placas solares** (N = 6.360). Ningún sitio del CSV se usó para energía solar, así que no hay positivos propiamente dichos. Desiertos de baja latitud con pareja: Dallol 96,64 (14,3 %), Makgadikgadi 96,39 (17,5 %), Dhofar 96,18 (19,6 %), Yungay 92,19 (50,0 %), Pajonales 88,76 (75,3 %), Mauna Kea 88,01 (79,5 %), Ramon 88,95 (74,0 %). Todos los sitios por encima de unos 37 grados de latitud que pasan el embudo (Tabernas, Bardenas, Jaroso, Tirez, MDRS, Qaidam, Ries, Black Point, Craters of the Moon, Etna, McMurdo, Concordia) **no tienen gemelo**: su insolación en el techo de la atmósfera es menor que la de cualquier celda de los mares ecuatoriales menos 0,6 (sección 6.2, B4).

**Base lunar** (N = 450). De 29 sitios, solo 2 tienen gemelo: MA05 MDRS (similitud 76,83, final 55,10, percentil 79,0) y MO07 Craters of the Moon (95,21, 61,64, percentil 37,7). **Los análogos fríos y polares del CSV (Haughton, McMurdo, Svalbard, Kangerlussuaq, Concordia, Askja, Holuhraun) no pasan el embudo de Base lunar.** Comprobado en la tabla: no tienen `lst_diurnal_amp_k` (MODIS sin Antártida, al sur de unos 62 S) o su amplitud está por debajo de la puerta `lst_diurnal_amp_k >= 15`. Atacama Yungay, Pajonales, Tirez, Tabernas, Qaidam, Ramon y Black Point pasan el embudo pero ninguna celda de las nueve regiones de la NASA pasa el filtro ("zone_cells_passing_filter" = 0). No hay, por tanto, validación externa positiva de Base lunar con este benchmark.

### 6.2 Parejas absurdas definidas a partir de los datos

`out/p3_validation.json`. Similitud sin filtro (puntuaciones sin redondear) y si el filtro la rechaza:

| Prueba | Rover | Placas solares | Base lunar |
|---|---|---|---|
| Parejas reales (todos los clasificados), similitud mediana [P05-P95] | 93,29 [76,45-99,58] | 99,93 [77,70-100,00] | 87,40 [71,92-97,34] |
| Parejas reales, top 50 | 97,40 [94,84-99,56] | 99,97 [99,90-100,00] | 93,84 [84,24-99,16] |
| B1 cada punto clasificado contra la celda de la zona en el extremo opuesto de cada variable clave | pendiente 10,24 [0,47-19,86]; rugosidad 10,17 [0,27-19,86]; **filtro rechaza 100 %** | irradiancia 33,90 [10,05-53,46]; **rechaza 100 %** | tmin 0,00 [0,00-8,91]; amplitud 0,04 [0,00-28,65]; **rechaza 100 %** |
| B2 20.000 parejas aleatorias Tierra (embudo) × toda la Luna | 19,92 [0,08-79,42]; rechaza 94,45 %; las 1.111 que pasan: 83,36 [68,66-97,36] | 4,92 [0,00-76,34]; rechaza 96,85 %; las 630 que pasan: 82,83 [65,60-97,91] | 19,47 [0,15-59,41]; rechaza 99,21 %; las 157 que pasan: 83,02 [70,04-95,13] |
| B3 el 1 % más empinado de la Tierra (≥ 7,6 grados, 248 celdas) contra la celda más llana de la zona | 0,00 [0,00-0,04]; rechaza 100 % (201 de esas celdas pasan el embudo de Rover) | 12,47 [0,00-76,37]; rechaza 100 % | 39,06 [2,84-73,62]; rechaza 100 % |
| B4 celdas en noche polar (|lat| > 66,56, 9.150) | — | techo de atmósfera 4,14-4,90 frente a 9,05-10,39 en la zona; **ninguna celda de la zona pasa el filtro**; similitud mediana sin filtro 12,84 (máx. 17,26). 6.293 de esas celdas pasan el embudo solar y quedan sin gemelo | — |

Lectura: las parejas absurdas salen bajas y, sobre todo, **el filtro de pareja las rechaza todas** (B1, B3, B4) o casi todas (B2: 94-99 %). Pero una pareja aleatoria que pasa el filtro tiene ya una similitud mediana de unos 83: la similitud, una vez pasado el filtro, discrimina poco; lo que lleva a los puntos reales a 93-100 es que el gemelo es el **máximo** sobre cientos o miles de celdas de la zona. En Solar la similitud sin filtro de una pendiente de 7,6 grados contra una celda llana llega a 79: la variable clave (80 %) domina y el filtro hace todo el trabajo de rechazo.

### 6.3 Límites honestos

* Celdas de 1 grado (unos 111 km en la Tierra, 30 km en la Luna): un sitio de ensayo concreto (Bardenas, Tabernas) es una mancha dentro de una celda cuyos valores son medias.
* 29 sitios utilizables, sin ninguno de energía solar y sin ningún análogo frío que pase el embudo de Base lunar: la validación externa solo informa algo para Rover.
* Saturación: en Solar, 1.126 de 6.360 puntos clasificados tienen similitud publicada ≥ 99,99 y 514 tienen 100,00 (cifras leídas del bundle y reproducidas); 3.921 tienen ≥ 99,9. En Rover, 248 puntos tienen idoneidad 100 (saturación de las utilidades lineales). Una similitud de 99,99 o 100 en Solar no significa "idéntico": significa que hay una celda de los mares a la misma latitud efectiva con pendiente y rugosidad parecidas.

## F. Estadística del ranking

### F.1 Dispersión sobre todos los puntos clasificados (`out/p3_ranking_stats.json`)

| Misión | Variable | n | P01 | P05 | P25 | Mediana | P75 | P95 | P99 | Máx |
|---|---|---|---|---|---|---|---|---|---|---|
| Rover | similitud | 10.192 | 71,07 | 76,46 | 85,34 | 93,29 | 98,07 | 99,58 | 99,86 | 100,00 |
| Rover | idoneidad | 10.192 | 41,17 | 54,62 | 68,06 | 74,07 | 75,43 | 97,64 | 100,00 | 100,00 |
| Rover | final | 10.192 | 68,41 | 74,02 | 79,18 | 81,76 | 84,48 | 93,12 | 96,16 | 99,39 |
| Solar | similitud | 6.360 | 70,96 | 77,70 | 99,68 | 99,94 | 99,97 | 100,00 | 100,00 | 100,00 |
| Solar | idoneidad | 6.360 | 61,45 | 71,11 | 80,66 | 85,92 | 91,56 | 94,40 | 95,71 | 96,90 |
| Solar | final | 6.360 | 72,05 | 78,72 | 88,80 | 92,18 | 95,48 | 97,17 | 97,84 | 98,45 |
| Base lunar | similitud | 450 | 66,48 | 71,92 | 81,06 | 87,40 | 92,91 | 97,34 | 99,16 | 99,48 |
| Base lunar | idoneidad | 450 | 21,77 | 23,03 | 26,80 | 30,87 | 38,01 | 47,80 | 51,39 | 57,84 |
| Base lunar | final | 450 | 48,02 | 50,64 | 56,19 | 59,81 | 63,05 | 68,95 | 71,26 | 72,29 |

Histograma por decenas (0-10, ..., 90-100), número de puntos:

| Misión | Variable | 40-50 | 50-60 | 60-70 | 70-80 | 80-90 | 90-100 |
|---|---|---|---|---|---|---|---|
| Rover | similitud | 0 | 3 | 62 | 812 | 3.169 | 6.146 |
| Rover | idoneidad | 225 | 659 | 2.183 | 5.261 | 754 | 1.023 |
| Rover | final | 1 | 13 | 128 | 3.236 | 5.657 | 1.157 |
| Solar | similitud | 0 | 0 | 2 | 405 | 459 | 5.494 |
| Solar | idoneidad | 2 | 41 | 226 | 1.167 | 2.940 | 1.984 |
| Solar | final | 0 | 0 | 29 | 380 | 1.726 | 4.225 |
| Base lunar | similitud | 0 | 1 | 13 | 78 | 182 | 176 |
| Base lunar | idoneidad (20-30: 209; 30-40: 146) | 88 | 7 | 0 | 0 | 0 | 0 |
| Base lunar | final | 17 | 216 | 204 | 13 | 0 | 0 |

(Rover idoneidad: además 1, 18 y 68 puntos en 10-20, 20-30 y 30-40. Base lunar final: 0 por debajo de 40.)

Puntos que pasan el embudo pero no tienen gemelo (no clasificados): Rover 145, Solar 12.417, Base lunar 1.969.

### F.2 ¿Se distingue el top 5 del resto?

| Misión | Final 1.º / 5.º | Puntos por debajo del 5.º a ≤ 0,1 / 0,5 / 1 / 2 puntos | Salto 4.º-5.º / 5.º-6.º | Mayor salto entre rangos 1-50 |
|---|---|---|---|---|
| Rover | 99,39 / 98,91 | 2 / 10 / 17 / 39 | 0,17 / 0,04 | 0,18 (entre 1.º y 2.º) |
| Solar | 98,45 / 98,24 | 6 / 72 / 267 / 1.212 | 0,06 / 0,01 | 0,06 |
| Base lunar | 72,29 / 71,28 | 1 / 5 / 7 / 16 | 0,35 / 0,04 | 0,58 (entre 32.º y 33.º) |

Saltos entre rangos consecutivos 1→50 (puntos de final publicado):

* Rover: 0,18 0,04 0,09 0,17 0,04 0,06 0,02 0,03 0,01 0,05 0,11 0,01 0,05 0,12 0,11 0,01 0,09 0,02 0,06 0,07 0,06 0,10 0,09 0,03 0,15 0,03 0,02 0,04 0,05 0,04 0,06 0,04 0,01 0,01 0,04 0,05 0,04 0,02 0,01 0,04 0,00 0,16 0,00 0,08 0,01 0,03 0,00 0,02 0,02 0,01 (3 empates exactos).
* Solar: 0,06 0,03 0,06 0,06 0,01 0,04 0,01 0,02 0,00 0,01 0,04 0,00 0,01 0,02 0,00 0,04 0,00 0,00 0,00 0,02 0,01 0,01 0,00 0,00 0,01 0,00 0,00 0,00 0,00 0,01 0,00 0,01 0,00 0,00 0,01 0,00 0,01 0,00 0,01 0,00 0,01 0,00 0,00 0,01 0,00 0,00 0,01 0,00 0,00 0,01 (24 empates exactos a 2 decimales).
* Base lunar: 0,01 0,55 0,10 0,35 0,04 0,09 0,16 0,08 0,01 0,34 0,28 0,13 0,40 0,19 0,03 0,08 0,01 0,11 0,02 0,02 0,04 0,15 0,34 0,30 0,12 0,03 0,12 0,04 0,01 0,01 0,25 0,58 0,08 0,07 0,06 0,02 0,02 0,01 0,08 0,19 0,03 0,04 0,15 0,03 0,11 0,04 0,23 0,17 0,00 0,02.

Lectura: en **Solar hay empates prácticos por centenares**: 72 puntos a menos de medio punto del quinto y 1.212 a menos de 2; los rangos 1 a 50 caben en 0,54 puntos. En Rover el top 5 está a 0,48 puntos del rango 1 y hay 17 puntos a menos de 1 punto del quinto. En Base lunar los puestos 1 y 2 están separados por 0,01 y el 5.º y el 6.º por 0,04. En Rover, 41 de los 50 primeros comparten el mismo gemelo M59895; en Solar los 50 primeros tienen 48 gemelos distintos; en Base lunar 36.

### F.3 Incertidumbre de cada valor derivado

Fuentes abiertas hoy (2026-11-15). Donde la documentación del producto no da una cifra por celda, se usa un error ilustrativo **etiquetado como tal**.

| Valor | Producto (según `real_data/provenance_*.csv` y `docs/REAL_DATA.md`) | Incertidumbre que se puede establecer | σ usada en el Monte Carlo |
|---|---|---|---|
| Elevación Tierra | ETOPO 2022 60" | MacFerrin et al. (2025), "The Earth Topography 2022 (ETOPO 2022) global DEM dataset", Earth Syst. Sci. Data 17, 1835-1849, publicado 08 May 2025, https://essd.copernicus.org/articles/17/1835/2025/ : "ETOPO 2022 measures a global RMSE of 7.17 m" (frente a ICESat-2). La página del producto https://www.ncei.noaa.gov/products/etopo-global-relief-model no da cifra de exactitud ni fecha. | 7,17 m (doc) |
| Pendiente y rugosidad Tierra (base 3,7 km y desfase 1,85 km) | derivadas de ETOPO 2022 | No documentada por celda. Una cota a mano: 7,17 m de error independiente por píxel darían √2·7,17/3.706 m ≈ 0,16 grados por píxel, que se promedian sobre miles de píxeles por celda; pero el error de un DEM está correlacionado en el espacio y eso no se puede establecer. | **ilustrativo 5 % relativo** |
| Elevación Luna | LOLA LDEM_16 V3.1 | Etiqueta PDS https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_16.lbl (PRODUCT_CREATION_TIME 2019-03-15): ninguna cifra de exactitud; dice que "GMT5.4.2 program 'surface' was used to compensate for incomplete coverage". Smith et al. (2010), GRL 37, L18204, resumen en https://dspace.mit.edu/handle/1721.1/74221 (Date issued: September 2010): la red geodésica lunar mejorada "to ∼10 m radial and ∼100 m spatial accuracy". | 10 m (doc; absoluta, por eso pesimista por celda) |
| Pendiente y rugosidad Luna | derivadas de LDEM_16 | No documentada por celda (la interpolación GMT suaviza donde faltan trazas). | **ilustrativo 5 % relativo** |
| Elevación relativa | elevación − media cos-latitud del cuerpo | La media de 25.497 (Tierra) o 64.800 (Luna) celdas apenas cambia; la incertidumbre es la de la elevación. | recalculada en cada corrida |
| Sol en el techo de la atmósfera (Tierra) | fórmula, S0 = 1.361 W/m2 | Geometría exacta (mi integración coincide a 6e-6). La misma S0 se usa en la irradiancia lunar, así que un error de S0 se cancela en la diferencia. | 0 (no se perturba) |
| Irradiancia en superficie (Tierra) | WorldClim 2.1 srad | Fick & Hijmans (2017), Int. J. Climatol. 37: 4302-4315, "Published online 15 May 2017", PDF del autor https://fickse.github.io/files/Fick_International_Journal_of_Climatology_2017.pdf , Tabla 3 (validación cruzada global): radiación solar RMSE 1,45 MJ m-2 (por día) = 0,403 kWh/m2/día | 0,403 kWh/m2/día (doc) |
| Temperatura mínima (Tierra) | WorldClim 2.1 tmin | misma Tabla 3: "Minimum temperature" RMSE 1,39 °C; texto: "an average RMSE between 1.1 and 1.4 °C" | 1,39 K (doc) |
| Amplitud diaria (Tierra) | MODIS MOD11A2 v006 (climatología de Hengl 2018) | MOD11 Collection 6.1 User Guide (Z. Wan, June 2019), https://lpdaac.usgs.gov/documents/715/MOD11_User_Guide_V61.pdf , bits de calidad de MOD11A2: "00=average LST error <= 1K", "01=average LST error <= 2K", "10=... <= 3K", "11=... > 3K". Día menos noche con 1 K en cada paso → √2 K. | 1,41 K (derivada de doc; es la mejor clase de calidad) |
| Temperatura mínima y amplitud (Luna) | Diviner GCP v1 | Hayne et al. (2017), JGR Planets, arXiv:1711.00977 (enviado 2 Nov 2017), p. 13: "Over the range of nighttime temperatures used in this study, ~60 – 120 K, Diviner has a noise-equivalent temperature difference (NETD) dT < 1 K (Paige et al., 2010a)". No se encontró cifra para el promedio estacional ni para el relleno de huecos del GCP. | 1 K mínima; √2 K amplitud (doc, ruido instrumental solamente) |
| Irradiancia Luna | geometría + fracción de iluminación LOLA | No documentada. | **ilustrativo 2 % relativo** |
| Fracción de suelo desnudo (Tierra) | ESA CCI LC 2020 | No establecida por celda (producto de clasificación). | **ilustrativo 0,05 absoluto** |
| Percentiles (Base lunar) | mid-rank con poblaciones 2.419 y 280 | Aritmética: un puesto vale 0,041 puntos en la Tierra y 0,357 en la Luna; la tolerancia de 10 puntos son ±242 puntos terrestres o ±28 celdas lunares. Propagando las σ anteriores (`out/p3_percentile_unc.json`, embudo fijo): **amplitud Tierra, desplazamiento mediano 7,57 puntos, P90 22,34, y el 39,8 % de los puntos se mueve más de 10 puntos (la tolerancia entera)**; tmin Tierra 2,67 (P90 8,27; 6,4 % > 10); tmin Luna 1,79 (1,2 % > 10); amplitud Luna 1,07 (0,2 % > 10). La amplitud terrestre de la población está comprimida (P05-P95 15,47-25,72 K), por eso 1,4 K mueven tanto el percentil. | consecuencia, no se perturba aparte |

No se perturban: `sun_elev_max_deg` y `sun_low_frac_0_5deg` (fórmulas exactas de la latitud), las clases (`thermal_inertia_class`, `permafrost_class`) ni `mask_fraction`.

### F.4 Monte Carlo (≥ 200 corridas por misión)

Ruido gaussiano independiente por celda con las σ de F.3 (las columnas que son alias de la misma fuente, `slope_deg`/`slope_300m_deg` y `roughness_m`/`rough_300m_m`, reciben el mismo sorteo); en cada corrida se recalcula todo desde cero: media del cuerpo y elevación relativa, percentiles en las poblaciones perturbadas, embudo, idoneidad, gemelos, similitud, final y rango. Semilla 20261115 (+ desplazamiento por misión y factor). `out/p3_mc_summary.json`.

**Por pareja del audio** (corrida principal, σ de F.3 × 1; Rover y Solar 200 corridas, Base lunar 200). "Sin rango" = sin gemelo o fuera del embudo en esa corrida; P95 "sin rango" significa que en más del 5 % de las corridas el punto no está clasificado.

| Misión | Rango audio | Celda | Top 5 | Top 20 | Top 50 | Mismo rango | Rango P05-P95 (mediana) | Sin rango | Gemelo cambia |
|---|---|---|---|---|---|---|---|---|---|
| Rover | 1 | E17566 | 88,0 % | 100 % | 100 % | 51,5 % | 1-8 (1) | 0 % | 0 % |
| Rover | 2 | E23945 | 78,5 % | 100 % | 100 % | 18,5 % | 1-9 (3) | 0 % | 0 % |
| Rover | 3 | E18282 | 74,0 % | 100 % | 100 % | 18,0 % | 1-14 (3) | 0 % | 0 % |
| Rover | 4 | E18280 | 39,0 % | 78,5 % | 97,0 % | 5,0 % | 1-45 (9) | 0 % | 0 % |
| Rover | 5 | E15395 | 22,0 % | 95,5 % | 100 % | 11,5 % | 4-20 (9) | 0 % | 0 % |
| Solar | 1 | E38464 | 0,5 % | 14,0 % | 41,5 % | 0 % | 12-1.408 (61,5) | 0 % | 98,5 % |
| Solar | 2 | E38105 | 0 % | 12,5 % | 43,0 % | 0 % | 16-1.769 (65,5) | 0 % | 96,5 % |
| Solar | 3 | E38744 | 0,5 % | 13,0 % | 46,0 % | 0 % | 11-1.993 (66) | 0 % | 96,0 % |
| Solar | 4 | E37746 | 1,5 % | 10,0 % | 34,5 % | 0 % | 16-1.514 (94,5) | 0 % | 97,5 % |
| Solar | 5 | E38465 | 0 % | 5,5 % | 32,0 % | 0 % | 20-1.634 (81) | 0 % | 100 % |
| Base lunar | 1 | E17538 | 43,5 % | 61,0 % | 64,5 % | 14,0 % | 1-sin rango (8) | 35,0 % (todo por el embudo) | 85,0 % |
| Base lunar | 2 | E16830 | 14,0 % | 42,5 % | 66,0 % | 3,0 % | 3-sin rango (26) | 16,5 % | 64,0 % |
| Base lunar | 3 | E15751 | 14,5 % | 45,0 % | 60,0 % | 4,0 % | 3-sin rango (27) | 31,0 % | 88,0 % |
| Base lunar | 4 | E21054 | 5,5 % | 34,5 % | 59,0 % | 2,0 % | 5-sin rango (37,5) | 13,5 % | 87,5 % |
| Base lunar | 5 | E17187 | 7,5 % | 39,5 % | 71,5 % | 2,5 % | 5-sin rango (26,5) | 12,0 % | 73,0 % |

**Estabilidad del top 5 en conjunto**:

| Corrida | Corridas | Top 5 idéntico (conjunto) | Idéntico y en orden | Coincidencias con el top 5 publicado (histograma 0/1/2/3/4/5) | Media | Celdas distintas que entran alguna vez en el top 5 |
|---|---|---|---|---|---|---|
| Rover, σ × 1 | 200 | 2,5 % | 0 % | 2 / 10 / 39 / 86 / 58 / 5 | 3,02 | 23 |
| Solar, σ × 1 | 200 | 0 % | 0 % | 195 / 5 / 0 / 0 / 0 / 0 | 0,03 | 267 |
| Base lunar, σ × 1 | 200 | 0 % | 0 % | 71 / 90 / 37 / 2 / 0 / 0 | 0,85 | 75 |
| Base lunar, σ × 0,5 | 200 | 0 % | 0 % | 24 / 106 / 59 / 11 / 0 / 0 | 1,28 | 44 |
| Base lunar, σ × 2 | 100 | 0 % | 0 % | 64 / 34 / 2 / 0 / 0 / 0 | 0,38 | 118 |

**Descomposición** (qué incertidumbre manda):

| Corrida | Corridas | Top 5 idéntico | Coincidencias medias | Lectura |
|---|---|---|---|---|
| Rover, solo pendiente y rugosidad (ilustrativas) | 60 | 5,0 % | 3,28 | casi toda la inestabilidad de Rover viene de los errores ilustrativos |
| Rover, todo menos pendiente y rugosidad (elevación ETOPO/LOLA y suelo desnudo) | 60 | 33,3 % | 4,15 | con solo errores documentados, rangos 1-3 siempre en top 5 (100 %), 4 y 5 en 60 % y 55 % |
| Solar, solo irradiancia en superficie (WorldClim, documentada) | 60 | 0 % | 0,00 | basta el RMSE documentado de WorldClim para vaciar el top 5; ninguna de las cinco entra en el top 5 en ninguna corrida; top 50 en el 45-80 % |
| Base lunar, solo amplitud Tierra (MODIS, derivada de doc.) | 200 | 0 % | 1,08 | el 1.º sale del embudo en el 33,5 % (amplitud 15,60 K frente a la puerta de 15 K) |
| Base lunar, todo menos amplitud Tierra | 200 | 0 % | 1,52 | incluso sin ella el top 5 nunca se repite; el 1.º sigue en top 5 el 56 % |

Otras cifras: en Solar el número de puntos con gemelo pasa de 6.360 a 7.042-7.547 bajo el ruido (el 2 % ilustrativo de la irradiancia lunar mueve el borde de qué latitudes terrestres encuentran gemelo); en Rover 9.788-10.272; en Base lunar 404-506 (embudo 2.378-2.501). El gemelo de Rover no cambia nunca (M59895 en las 200 corridas para las cinco); el de Solar cambia casi siempre porque hay muchas celdas de los mares con similitud prácticamente igual (saturación); el de Base lunar cambia en el 64-88 %.

Por qué las tres misiones se comportan distinto: en Rover la similitud del top 5 depende de valores que el ruido documentado apenas mueve y el primer puesto tiene el mayor salto de los 50 primeros (0,18). En Solar los rangos 1-50 caben en 0,54 puntos y un error de 0,40 kWh/m2/día en la irradiancia de superficie mueve la idoneidad unos 0,35 × 0,403 / 3,5 × 100 ≈ 4 puntos (peso 0,35, utilidad lineal entre 2,5 y 6,0): mucho más que todo el top 50. En Base lunar la población terrestre de amplitudes está comprimida (P05-P95 15,47-25,72 K) y la tolerancia es de 10 percentiles: 1,4 K mueven el percentil más que la tolerancia entera en el 40 % de los puntos (F.3); además los cinco primeros tienen amplitudes de 15,60-18,71 K, a menos de 4 K de la puerta de 15 K, y el 1.º a 0,60 K.

Límite de esta propagación: el ruido es independiente por celda y las σ de pendiente, rugosidad, irradiancia lunar y suelo desnudo son ilustrativas. Las σ documentadas de WorldClim son RMSE de validación cruzada en estaciones, no de una media de celda de 1 grado; para una media de 36 píxeles de 10' el error podría ser menor si fuera independiente, o igual si está correlado en el espacio (no establecido). La corrida σ × 0,5 de Base lunar muestra que, incluso con la mitad de error, el top 5 no se repite nunca.

### F.5 Qué puede y qué no puede concluir quien escucha "the five best"

Cifras de F.2 y F.4. Las tres pistas de misión dicen "Here are the five best analogs on Earth." (Rover, Solar; Base lunar: "Here are the five best analogs.", `app/public/audio/transcripts.json`, pistas `m1_rover.mp3`, `m2_solar.mp3`, `m3_base.mp3`).

Quien escucha **puede** concluir:

* que esos cinco puntos son los cinco de mayor puntuación final del modelo tal como está configurado y con estos datos (reproducido de forma independiente: 15 de 15 parejas, rangos y gemelos);
* que cada lugar terrestre y su gemelo lunar cumplen el filtro de pareja (todas sus variables clave dentro de su tolerancia) y que el filtro rechaza parejas absurdas (punto 6);
* en Rover, que los tres primeros están de forma estable entre los mejores: top 20 en el 100 % de las corridas y top 5 en el 74-88 %, con el mismo gemelo siempre. Con pesos ±10 % el top 5 no cambia.

Quien escucha **no puede** concluir:

* que sean "los cinco mejores lugares de la Tierra" en un sentido que sobreviva a la incertidumbre de los datos: en Solar, con el error documentado de WorldClim, las cinco no vuelven a salir juntas nunca (0 de 200), cada una de ellas queda en el top 5 en el 0-1,5 % de las corridas y su rango mediano está entre 61 y 95; hay 72 puntos a menos de 0,5 puntos del quinto. En Base lunar ninguna corrida repite el top 5 y el 1.º se queda fuera del embudo en el 35 % de ellas;
* el orden dentro del top 5 (Base lunar 1.º y 2.º: 0,01 puntos; Solar 4.º-5.º-6.º: 0,06 y 0,01);
* que Rover dependa de la pendiente y la rugosidad: su top 5 lo decide la elevación relativa (quitándola, las cinco caen a los rangos 357-452);
* que las cifras de similitud de 99,99 o 100 en Solar indiquen lugares idénticos: es saturación (1.126 puntos ≥ 99,99).

Frase que sí se sostiene con las cifras (propuesta, para el líder): "five of the highest-scoring analogs in our model" / "cinco de los análogos con mayor puntuación en nuestro modelo".

## Fallos y decisiones

Ningún fallo de código en lo que cubren estos puntos: la reproducción independiente coincide (sección 0). Lo que sigue son hallazgos para el líder.

1. **Afirmación "the five best analogs on Earth" (pistas `m1_rover.mp3`, `m2_solar.mp3`; "the five best analogs" en `m3_base.mp3`).** No cambia ningún criterio de diseño corregirla, pero exige volver a grabar 3 pistas (o, como alternativa sin regrabar, añadir en la web, junto a cada top 5, una nota con la cifra de F.2: "las diferencias entre estos puntos son menores que la incertidumbre de los datos"). Cifras: Solar 0 de 200 corridas repiten el top 5, 72 puntos a ≤ 0,5 del quinto; Base lunar 0 de 200; Rover 5 de 200 (2,5 %), aunque los tres primeros están siempre en el top 20. Opciones: (a) regrabar las 3 pistas con "five of the highest-scoring analogs in our model"; (b) mantener el audio y añadir la nota en la web; (c) mantener todo y aceptar el riesgo de que un jurado lo cuestione. Decide el líder.
2. **Rover: el top 5 depende de la variable secundaria `elevation_rel_m` (20 %).** Corregirlo cambiaría un peso o una variable comparada: no se corrige, se describe. Cifras: sin ella (quitándola de similitud y filtro) el top 5 pasa a E3872, E4037, E4042, E4742, E4750 y las cinco del audio a los rangos 357-452; quitándola solo de la similitud, a E11627, E40874, E11626, E6385, E6408 (las del audio a 46-143). Con su peso ±10 % el top 5 no cambia. Opciones: (a) mantener (el top 5 queda definido por "misma altura relativa que la zona polar"); (b) bajar su peso o sacarla de la similitud, lo que exige regrabar las 5 pistas de Rover y `m1_rover.mp3`.
3. **Solar: la 5.ª pareja (E38465, NE de Derby) es un empate práctico con E38385.** Diferencia 0,01 puntos; con 8 de 12 perturbaciones de ±10 % de los pesos de idoneidad entra E38385. Corregir el orden no es posible sin cambiar un criterio; no se toca. Opción: decirlo en la web ("empatada con otro punto vecino").
4. **Base lunar: el top 5 está en el borde de la puerta `lst_diurnal_amp_k >= 15` y depende de percentiles que el error de MODIS mueve más que la tolerancia.** Amplitudes del top 5: 15,60 (1.º), 18,01, 16,04, 18,71, 18,16 K. Con el error derivado de la documentación (√2 K) el 1.º sale del embudo en el 35 % de las corridas y el 39,8 % de los puntos terrestres mueve su percentil de amplitud más de 10 puntos. Corregirlo cambiaría una puerta o una tolerancia (decidido por el equipo): no se corrige. Opciones con su efecto medido: σ × 0,5 (datos el doble de buenos) sigue sin repetir nunca el top 5 (coincidencia media 1,28 de 5); sin perturbar la amplitud terrestre, coincidencia media 1,52. Una tolerancia mayor o una puerta más baja no se han medido aquí.
5. **Validación externa de Rover: Bardenas (sitio BASEPROD) queda por debajo de la mediana de los análogos de movilidad** (percentil 44,5 frente a mediana 9,2), el aviso que el propio `rover_preset.validate_rover_ranking` define como problema "review before the pitch". La similitud lunar no separa análogos de discordantes (El Soplao 98,57 frente a Bardenas 94,26). No es un fallo de código; corregirlo cambiaría pesos. Para el líder.
6. **Base lunar sin validación externa positiva**: ninguno de los análogos fríos o polares del benchmark pasa el embudo (amplitud MODIS 1,2-7,4 K o sin dato al sur de 62 S). Es una consecuencia de la puerta de 15 K y de la cobertura de MODIS; para el líder.

## No establecido

* La exactitud por celda de pendiente y rugosidad (ETOPO 2022 y LDEM_16) y de la irradiancia lunar: sin cifra en la documentación abierta; se usaron errores ilustrativos etiquetados. El resultado del Monte Carlo depende de ellos para Rover (sección F.4, descomposición).
* La exactitud de las estadísticas del GCP de Diviner (promedio estacional, relleno de huecos de hasta 3 h): solo se pudo citar el ruido instrumental (< 1 K).
* La exactitud por celda de la clasificación ESA CCI (fracción de suelo desnudo): no se abrió su documento de validación; valor ilustrativo.
* La correlación espacial de los errores: el Monte Carlo usa ruido independiente por celda. Un error sistemático común (por ejemplo, todo WorldClim 1 K demasiado frío) no cambiaría ningún percentil y apenas el ranking; un error espacialmente correlado a escala regional puede ser peor o mejor que el independiente. No se puede establecer con lo disponible.
* La página del producto MOD11A2 en earthdata.nasa.gov devolvió 403; se usó la guía de usuario del producto (LP DAAC) en su lugar.
