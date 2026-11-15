# Investigación 3 — Base lunar: doble conteo, permafrost y compuerta de amplitud térmica

Fecha: 2026-11-15, informe cerrado a las 12:08 CET. Solo investigación y medida: no he tocado el motor, la configuración, las tablas, el bundle, la web ni los audios.
Script: `tierra luna/research/r3_base_lunar.py` (determinista). Salida: `tierra luna/research/out/r3_base_lunar.json`.
Base de cálculo: copia en memoria de las entradas en el commit 42d8bba, extraída con `git archive` en el scratchpad, porque engine_config.json del árbol de trabajo ya cambió hoy. Uso la librería del auditor `audit/p5_common.py`, que reproduce el bundle exactamente (lunar_base: 2.419 pasan, 450 emparejados, 0 gemelos distintos, 0 rangos distintos, diferencia máxima 0,00 en idoneidad, similitud y nota final; también exacto en Rover y Placas).

## 1. Hallazgo (dos líneas)
El doble conteo es real (las dos utilidades tienen Spearman 0,893 entre los 2.419 puntos), y el permafrost no tiene fuente que lo ligue a una base: los dos se pueden corregir sin tocar la zona ni el principio, y el top 50 conserva 38 a 44 de los 50 puntos.
La compuerta de 15 K no es un artefacto: sin ella, el emparejamiento por percentil da como gemelo perfecto la isla de Ellesmere, con 1 K de amplitud. Los análogos polares no pasan porque en la Tierra no tienen ciclo diario medible (Haughton tiene 2,5 K de media anual y 5,8 K en su mes máximo) o porque no tienen LST (Antártida). Son análogos del frío, no del ciclado.

## 2. Qué mide cada lado (punto 3a)
- **Tierra**, `lst_diurnal_amp_k`: es la media anual de la diferencia entre la LST diurna y la nocturna de MODIS MOD11A2 (Terra, pasos hacia las 10:30 y las 22:30 hora local). Viene de la climatología OpenLandMap 2000-2017 a 1 km (Zenodo 1420115), es DERIVED y se promedia en la celda de 1 grado (`real_data/build_earth.py`, stage_lst). La misma tabla trae `lst_diurnal_amp_max_k`: la diferencia día-noche del mes en que es mayor (las 12 climatologías mensuales "daynight"). **No hay LST en la Antártida**: 6.198 celdas de tierra al sur de 60 S, 0 con LST, aunque 6.197 tienen tmin. `tmin_c` es la mínima diaria media del mes más frío, de WorldClim 2.1 (1970-2000).
- **Luna**, `lst_diurnal_amp_k`: la temperatura máxima menos la mínima del ciclo completo de Diviner (docs/REAL_DATA.md). En la zona de 280 celdas va de 144 K (p5) a 217 K (p95), mediana 178,5 K. La tmin va de 40 K (p5) a 71,5 K (p95).
- Por tanto la escala física no es comparable: la mediana terrestre, sin la compuerta, es 8,3 K. El emparejamiento compara posiciones dentro de cada población (diseño D4b), no valores.

## 3. Análogos reconocidos (punto 3b; benchmark `data/benchmark/analog_benchmark.csv`)
| id | sitio | celda (lat, lon) | amplitud anual K | amplitud del mes máximo K (mes) | tmin °C | LST | por qué falla hoy |
|---|---|---|---|---|---|---|---|
| MA06 | Haughton, isla Devon | 5130 (75.5, -89.5) | 2,50 | 5,76 (4) | -37,9 | sí | compuerta (2,5 < 15) |
| MA09 | Axel Heiberg | 3689 (79.5, -90.5) | 1,67 | 3,84 (4) | -42,8 | sí | compuerta |
| MA08 | Svalbard, Bockfjorden | 3793 (79.5, 13.5) | 1,23 | 2,99 (8) | -20,6 | sí | compuerta y clase dominante "agua" |
| MA19 | Kangerlussuaq | 8049 (67.5, -50.5) | 6,63 | 14,30 (7) | -22,9 | sí | compuerta |
| MA07 | Valles Secos de McMurdo | 60462 (-77.5, 162.5) | — | — | -33,8 | **no** | sin amplitud (obligatoria) |
| OP01 | Concordia (Domo C) | 59703 (-75.5, 123.5) | — | — | -49,3 | **no** | sin amplitud; además sin permafrost |
| OP02 / MO05 | HI-SEAS / Mauna Kea (misma celda) | 25224 (19.5, -155.5) | 16,80 | 18,37 | 10,9 | sí | **tmin > 5 °C** (la amplitud sí pasa) |

## 4. Opciones medidas (todas con la zona de 280 celdas y el principio intactos)
"ov50" es el solape del top 50 con el de hoy. "Idoneidad p5/p50/p95 (DE)" se calcula sobre los emparejados. Coordenadas de centro de celda; el lugar se da por país o región a partir de la coordenada (sin geocodificador).

| opción | pasan | emparejados | gemelos distintos | ov50 | idoneidad p5/p50/p95 (DE) | top 5 (id Tierra: final) |
|---|---|---|---|---|---|---|
| **Hoy** | 2.419 | 450 | 103 | — | 23,0 / 30,9 / 47,8 (7,8) | 17538: 72,29; 16830: 72,28; 15751: 71,73; 21054: 71,63; 17187: 71,28 |
| DC1: solo clase, peso 0,25 | 2.419 | 450 | 103 | 44 | 28,7 / 35,8 / 49,6 (6,4) | 16830, 15751, 42949, 16833, 17538 |
| DC2: solo fracción rock_or_bare, peso 0,25 | 2.419 | 450 | 103 | 39 | 14,2 / 23,4 / 46,2 (10,5) | 17538, 21054, 18254, 18627, 21412 |
| DC3: quitar rock_or_bare sin repartir | 2.419 | 450 | 103 | 41 | 25,2 / 32,4 / 45,1 (6,0) | 16830, 15751, 42949, 16833, 17187 |
| PF0: permafrost a peso 0 | 2.419 | 450 | 103 | 43 | 22,6 / 29,7 / 46,2 (7,6) | 21054, 21412, 42949, 16830, 17538 |
| **R (recomendada): DC2 + PF0, clase solo como compuerta "agua"** | 2.419 | 450 | 103 | **38** | 13,4 / 21,7 / 45,4 (10,5) | 21054: 72,00; 21412: 71,28; 17538: 70,23; 20695: 70,13; 21833: 69,87 |
| R alternativa: DC1 + PF0 | 2.419 | 450 | 103 | 42 | 28,6 / 34,7 / 47,7 (6,0) | 42949: 72,92; 16830: 72,34; 21054: 72,00; 15751: 71,71; 21832: 71,59 |
| Compuerta 10 K | 3.928 | 698 | 124 | 18 | 17,8 / 26,3 / 41,7 | 44030, 17898, 42949, 17538, 18254 |
| Compuerta 5 K | 8.564 | 1.786 | 150 | 5 | 15,3 / 27,1 / 40,5 | 7477, 7508, 7868, 7838, 7836 (Siberia, 68-70 N, amplitud ≈ 5,3 K) |
| Sin compuerta, utilidad de 15 a 35 K | 9.981 | 2.109 | 155 | 3 | 15,9 / 28,5 / 46,7 | 2973, 2971, 3334, 2972, 3692 (Ellesmere, 80-81 N, **amplitud 0,9-1,9 K**, similitud ≈ 99) |
| Sin compuerta, utilidad de 0 a 35 K | 9.981 | 2.109 | 155 | 5 | 24,2 / 35,4 / 50,2 | 15391, 15030, 15751, 15029, 7868 |
| Amplitud del mes máximo en compuerta e idoneidad (emparejamiento sin cambio) | 4.208 | 888 | 132 | 20 | 22,7 / 34,2 / 51,4 | 42950, 42590, 44030, 17897, 17898 |
| Amplitud del mes máximo también en el emparejamiento | 4.208 | 785 | 124 | 25 | 25,6 / 34,6 / 52,8 | 44030, 18627, 18628, 17897, 17187 |

Top 5 con detalle:
- **Hoy:** 17538 (41.5, 78.5; Tian Shan, Kirguistán/China), gemelo 63528, similitud 97,31, idoneidad 47,27, final 72,29, amplitud 15,6 K. 16830 (43.5, 90.5; Xinjiang oriental, China), gemelo 63841, 96,61 / 47,96 / 72,28, 18,0 K. 15751 (46.5, 91.5; Mongolia occidental), gemelo 64018, 96,86 / 46,60 / 71,73, 16,0 K. 21054 (31.5, -5.5; Marruecos, sur del Atlas), gemelo 62517, 99,36 / 43,91 / 71,63, 18,7 K. 17187 (42.5, 87.5; Tian Shan oriental, China), gemelo 62523, 95,03 / 47,54 / 71,28, 18,2 K.
- **R:** 21054 (Marruecos), gemelo 62517, 99,36 / 44,64 / 72,00, 18,7 K. 21412 (30.5, -7.5; Marruecos), gemelo 62516, 97,55 / 45,00 / 71,28, 19,3 K. 17538 (Tian Shan), gemelo 63528, 97,31 / 43,15 / 70,23, 15,6 K. 20695 (32.5, -4.5; Marruecos), gemelo 62135, 95,06 / 45,21 / 70,13, 19,3 K. 21833 (29.5, 53.5; Irán), gemelo 62515, 92,50 / 47,25 / 69,87, 20,0 K. Todos tienen como clase CCI dominante 200 (zona desnuda).
- **Distancia a la compuerta en R:** el top 5 queda entre 0,6 y 5,0 K por encima de 15 K, así que sigue cerca del umbral. En ninguna de las opciones con compuerta pasa un análogo reconocido. Sin compuerta, Axel Heiberg queda en el puesto 238 de 2.109, Kangerlussuaq en el 431 y Haughton en el 836.

## 5. Doble conteo (punto 1)
- Origen: `real_data/class_mappings.json` y `build_earth.py`. `thermal_inertia_class` es la categoría con más píxeles CCI de 300 m en la celda (MODELLED). La asignación es esta: 150-153 y 200 → "regolito"; 190 (**urbano**) y 201 → "roca"; 202 → "arena"; 210 → "agua"; 220 → "hielo"; el resto → "suelo". `rock_or_bare_frac` es la fracción de píxeles de tierra con códigos 150-153 y 200-202 (DERIVED, línea 501). Los mismos códigos (150-153, 200-202) puntúan dos veces. Spearman de las utilidades: 0,893.
- Urbano: 190 solo entra en la clase, nunca en la fracción. Hoy no domina en **ninguno** de los 2.419 puntos que pasan (dominantes: 200 → 802, 130 → 672, 120 → 402, 150 → 233), así que su efecto actual es 0. Con R desaparece del cálculo de idoneidad.
- Recomendación: **quedarse con `rock_or_bare_frac` (DC2) con el peso combinado de 0,25.** Motivos: es DERIVED y no MODELLED, es continua (DE de la idoneidad 10,5 frente a 6,4: discrimina más), y no mete lo urbano en "roca". La clase se mantiene solo como compuerta (excluye "agua"). Si el jefe prefiere conservar la categoría, la alternativa medida es DC1 con ov50 = 42, pero entonces 190 debe asignarse a "suelo" o al valor por defecto.

## 6. Permafrost (punto 2)
- Valor de la tabla: probabilidad media de permafrost de Obu et al., ESA CCI / UiO PEX PERPROB 5.0 (NH 2000-2016, ANT 2000-2017), a 1 km, clasificada con los umbrales de IPA / Brown 1997 (MODELLED). Entre los 2.419: ninguno 1.406, **sin valor 607**, esporádico 266, discontinuo 89, continuo 51. La utilidad es no monótona: puntúa más el esporádico (1,0) que el continuo (0,7), y su "why" ("ciclos congelación-deshielo") no tiene equivalente en la Luna, donde no hay agua líquida.
- Fuente oficial que ligue permafrost o suelo cementado por hielo a operaciones de excavación o construcción de una base polar lunar: **no establecida hoy** (no la he localizado ni citado dentro del plazo; no cito nada de memoria).
- Efecto de dejar el peso en 0: cambian 3 de los 5 primeros (entran 21412 y 42949; salen 15751 y 17187) y ov50 = 43.
- Recomendación: **peso 0**, por tres razones: no hay fuente que dé el vínculo físico, falta el valor en el 25 % de los puntos, y es MODELLED. El dato se puede seguir mostrando como información.

## 7. Compuerta de amplitud (puntos 3c a 3e)
- Argumento físico. Una base sufre tres esfuerzos térmicos: (1) el frío en sí, que ya mide tmin; (2) el tamaño del ciclo, es decir, la fatiga por dilatación diferencial; (3) el número de ciclos. En la Luna, un ciclo dura una lunación (unos 29,5 días terrestres), así que el máximo menos el mínimo de Diviner es la amplitud de un ciclo día-noche lento. Un año terrestre tiene unos 12 de esos ciclos: el número de ciclos no es el problema en ninguna de las dos variables. El equivalente honesto del tamaño de un ciclo lunar sería la amplitud de un día terrestre **completo**, y lo que tenemos es la diferencia entre dos pasos de satélite (10:30 y 22:30), que la subestima. La amplitud anual (máxima diurna del mes cálido menos mínima nocturna del mes frío) refleja el ciclo estacional, que en los polos también es un único ciclo luz-oscuridad. Es un candidato defendible para los sitios polares, pero cambia la definición de la variable clave.
- Dato alternativo: intenté descargar WorldClim 2.1 tmax de 10' (`https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_10m_tmax.zip`, CC BY 4.0) para calcular la amplitud anual (bio7, o el máximo de tmax menos el mínimo de tmin). **El proxy cortó la conexión 12 veces** (curl 35, "connection reset"). Además, la Antártida no tiene LST en nuestra fuente. Por eso **no he preparado tabla suplementaria** y la amplitud anual queda "no establecida hoy". La única alternativa con dato real a mano es `lst_diurnal_amp_max_k`, la del mes máximo, que ya está en la tabla y está medida en la tabla 4. Con ella pasan 4.208 puntos (ov50 = 20 o 25), pero **no entra ningún análogo polar**, porque su mes máximo es de 3 a 14,3 K.
- Por qué no quitar la compuerta: sin ella, el 75,8 % de los 9.981 candidatos queda por debajo de 15 K (mediana 8,3 K), y el percentil da similitud ≈ 99 a celdas de 1 K frente a la Luna. El principio "la amplitud es variable clave" se queda vacío. La compuerta es lo único que impone un ciclo **medible**.
- Recomendación: **mantener la compuerta en 15 K**, justificada con estas cifras. Hay que escribir en la web y en los textos que los análogos polares (Haughton, Axel Heiberg, Svalbard, McMurdo, Concordia) son análogos del **frío y del aislamiento**, no del ciclado, porque en la Tierra su ciclo día-noche medido es de 1 a 7 K (o no hay dato). HI-SEAS y Mauna Kea quedan fuera por tmin, no por la amplitud. Si se cambia la definición de la amplitud (a la anual o a la del mes máximo) **también en el emparejamiento**, se está cambiando cómo se mide la variable clave: es decisión del jefe (sección 9).

## 8. Cambios de configuración recomendados (overrides en engine_config; mission_scoring.json no se toca)
1. `lunar_base.soft.thermal_inertia_class`: peso 0,15 → **0**, quitado de soft. Se mantienen la compuerta `exclude: ["agua"]` y la obligatoriedad. Motivo: doble conteo (Spearman 0,893). Fuente: class_mappings.json.
2. `lunar_base.soft.rock_or_bare_frac`: peso 0,10 → **0,25**, con bad 0,1 y good 0,7 sin cambiar. Motivo: conserva el peso combinado de la superficie expuesta con la variable DERIVED. Fuente: ESA CCI LC 2020 v2.1.1.
3. `lunar_base.soft.permafrost_class`: peso 0,05 → **0**. Motivo: no hay fuente del vínculo con una base, falta en 607 de 2.419 puntos y es MODELLED.
4. `lunar_base.gates.lst_diurnal_amp_k.min`: **sin cambio, 15 K**. Justificación: la sección 7 y la opción "sin compuerta", que pone en cabeza celdas de 1 K con similitud 99.
Efecto conjunto (opción R): 2.419 / 450 / 103, ov50 = 38, idoneidad del top 5 entre 43,2 y 47,3.

## 9. Lo que necesita al jefe de equipo (principio)
Que los análogos polares entren por la amplitud exige cambiar **cómo se mide** la amplitud en la Tierra:
- (a) Amplitud anual (WorldClim bio7 o una climatología LST mensual de día y de noche) en la compuerta, la idoneidad y el emparejamiento. Hoy no hay dato descargable y la Antártida sigue sin LST.
- (b) Lo mismo, pero solo en la compuerta y la idoneidad, dejando el emparejamiento con la amplitud día-noche.
- (c) Mantenerlo como está y etiquetar los polares como análogos de frío.

Con el mes máximo, que es el único dato disponible hoy, (a) y (b) dan ov50 = 25 y 20 respectivamente, y siguen sin incluir ningún polar. Mi recomendación es (c).

## 10. No establecido
- La fuente oficial que liga permafrost o suelo cementado por hielo con la construcción de una base lunar.
- La amplitud anual terrestre (WorldClim tmax bloqueado por el proxy).
- La LST antártica.
- Las 200 simulaciones de incertidumbre con los criterios corregidos: no me cupieron en el plazo, quedan para otro agente. El auditor tiene la herramienta `audit/p3_montecarlo.py`.
- Los nombres de lugar de las celdas: se dan por coordenada y país.
