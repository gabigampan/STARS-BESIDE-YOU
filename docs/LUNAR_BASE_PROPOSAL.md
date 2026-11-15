# Base lunar: cómo darle pares sin llamar parecidas a temperaturas que no lo son

Documento interno del equipo Stars Beside You (NASA Space Apps Challenge 2026), rama `final-integration`, 15-11-2026. **Confirmada el 15-11-2026 a las 08:55 CET (la persona delegada, en nombre del líder del equipo: diseño recomendado D4b, no la alternativa sin terreno) e implementada el mismo día** (regla `percentile_and_real_tolerance`, motor 3.2.0, contrato revisión 6; ver la sección "Implementación (15-11-2026)" al final y `docs/ANALOG_PRINCIPLE.md`, "Resultado tras implementar: Base lunar (15-11-2026)"). Las secciones 1-8 y la comprobación quedan como registro de la propuesta; las diferencias de temperatura mínima se han pasado a K (ver el final).

Responde al mensaje de Facundo de las 07:55 CET: Base lunar tiene que tener análogos en la Tierra; se permite medir la temperatura y la amplitud en relativo a cada cuerpo (percentil o z) o reajustar los pesos, pero hay que enseñar antes la propuesta con variables, pesos, normalización, tolerancia, supervivientes, número 1 con su gemelo y la diferencia en valores reales. Rover y Paneles solares no se tocan (siguen como en `docs/ANALOG_PRINCIPLE.md`).

**De dónde salen los números.** Todo calculado hoy sobre las tablas reales de 1 grado (`tierra luna/output_real/earth_real_1deg.csv` y `moon_real_1deg.csv`) con los scripts de `scratchpad/stars/lunarbase/` (`lb.py` motor de diseños, `extra.py`, `why.py`, `d5.py`, `d5sev.py`, `today.py`, `mdtab.py`; resultados en `res_*.json`, `res5_D5_sev_terr.json`, `pairs_*.csv`, `top10.md`). Reutilizan la carga de tablas, zonas y paquete publicado de `scratchpad/stars/principle-check/ctx.py`. Candidatos de la Tierra: los 2.419 puntos que pasan el embudo `lunar_base` (amplitud ≥ 15 K, mínima ≤ 5 °C, no agua), leídos del paquete publicado `app/public/data/v2` junto con sus pares de hoy. Zona lunar: las 280 celdas de las nueve regiones de la NASA (`proposal-verify/out/regions.json`); al lado, el polo sur (latitud ≤ −75°, 5.400 celdas) y la Luna entera (64.800). Pendiente = `slope_iso_deg`; elevación relativa = elevación menos la media ponderada por área de cada cuerpo (definición de `ANALOG_PRINCIPLE.md`, no la del motor). Los pares de hoy reproducen la sección A de `ANALOG_PRINCIPLE.md` (diferencia de temperatura media 142,3 / 160,8 K; 48 gemelos; 27,7 % en M62515).

## Resumen

**Lo que dicen los datos.** En valor absoluto no hay nada que emparejar (candidato más frío 264,1 K; celda más cálida de las regiones 167,5 K). Medir "en relativo a cada cuerpo" tampoco lo arregla: con z o percentil sobre todo el cuerpo (D1, D2) siguen saliendo **0 pares** en las regiones y en el polo sur, también al doble de tolerancia, porque **la amplitud está en extremos opuestos**: los candidatos tienen la amplitud más grande de la Tierra (percentil 75,6-100 de la tierra firme; z +0,97 a +4) y las regiones la más pequeña de la Luna (percentil 0-29,8; z −3,72 a −0,67). Solo da pares comparar la **posición dentro de lo que cada cuerpo ofrece para esta misión** (D3, D4, D5): percentil entre los 2.419 candidatos de un lado y entre las 280 celdas de las regiones del otro. Eso siempre encuentra pares porque compara puestos dentro de dos poblaciones elegidas; **no acerca los valores**: en todos los diseños que dan pares en las regiones, la diferencia real mediana es de unos 160 K en temperatura media, 208 K en mínima y 152-159 K en amplitud.

| diseño | normalización | pesos | tolerancia del filtro | pares que sobreviven (de 2.419) | gemelos distintos | mayor cuota de un gemelo | número 1 y gemelo | dif. real T media: mediana / P90 | dif. real amplitud: mediana / P90 |
|---|---|---|---|---|---|---|---|---|---|
| hoy (motor) | z por cuerpo, 4 variables | pend. 33,3, rug. 26,7, elev. 20, T 20 | sin filtro | 2.419 | 48 | 27,7 % | E19345 (36,5 N 85,5 E) – M62859 (Floss) | 142,3 / 160,8 K | 164,5 / 191,1 K |
| D1 | z por cuerpo (Tierra firme / Luna entera), como `normalize_planetary_features` | T 50, A 50 | 0,5 z | **0** (0 al doble) | — | — | ninguno | — | — |
| D2 | percentil por cuerpo | T 50, A 50 | 10 puntos | **0** (0 al doble) | — | — | ninguno | — | — |
| D3 | percentil dentro de candidatos / dentro de las 280 celdas | T 50, A 50 | 10 puntos | 2.186 | 254 | 2,9 % | E40790 (23,5 S 69,5 O, Atacama) – M62393 (Peak Near Cabeus B) | 160,2 / 180,5 K | 159,0 / 176,6 K |
| D3z | z robusto dentro de cada población | T 50, A 50 | 0,5 z | 2.270 | 221 | 5,7 % | E15758 (46,5 N 98,5 E, Mongolia central) – M62522 (Nobile Rim 2) | 158,5 / 175,9 K | 158,4 / 174,3 K |
| D4a | D3 + terreno en valor real | T 40, A 40, pend. 10, rug. 10 | 10 puntos; 4° y 60 m | 457 | 96 | 4,6 % | E18254 (39,5 N 74,5 E) – M64020 (Slater Plain) | 167,9 / 185,7 K | 152,8 / 161,6 K |
| **D4b (recomendado)** | **percentil dentro de cada población para mínima y amplitud; terreno en valor real** | **mín. 40, A 40, pend. 10, rug. 10** | **10 puntos; 4° y 60 m** | **450** | **103** | **5,6 %** | **E17538 (41,5 N 78,5 E, Tian Shan) – M63528 (Haworth, junto a Mons Malapert)** | **162,7 / 181,2 K** | **153,8 / 161,3 K** |
| D4c | como D4b + T media | A 35, mín. 25, T 20, pend. 10, rug. 10 | 10 puntos; 4° y 60 m | 338 | 82 | 5,0 % | E17538 – M63528 (igual que D4b) | 166,6 / 185,9 K | 152,3 / 160,9 K |
| D4d | mínima y amplitud, sin terreno | mín. 50, A 50 | 10 puntos | 1.986 | 246 | 3,6 % | E41150 (24,5 S 69,5 O, Yungay) – M62501 (Mons Mouton Plateau) | 162,2 / 182,6 K | 159,4 / 174,6 K |
| D5 (propio) | un índice de severidad (amplitud + frío) en percentil dentro de cada población; terreno real | sev. 80, pend. 10, rug. 10 | 10 puntos; 4° y 60 m | 971 | 98 | 15,3 % | E40071 (21,5 S 68,5 O, Altiplano) – M63837 (de Gerlache Rim 2) | 169,8 / 194,4 K | 153,0 / 161,8 K |

T = temperatura media; A = amplitud térmica diaria; mín. = temperatura mínima; "puntos" = puntos de percentil. Las diferencias son |Tierra − gemelo| sobre los pares que sobreviven, en las nueve regiones.

**Recomendación: D4b.** Variables clave las dos que usa la propia misión en sus filtros duros y en sus pesos (amplitud 0,35 y mínima 0,25 del bloque `soft`): **temperatura mínima y amplitud diaria, cada una en percentil dentro de su población** (Tierra: los 2.419 candidatos; Luna: las 280 celdas de las regiones), peso 40 + 40, tolerancia ±10 puntos de percentil, filtro en las dos. Terreno en valor real como secundario: pendiente 10 (τ 2°, filtro 4°) y rugosidad 10 (τ 30 m, filtro 60 m). **Sobreviven 450 de 2.419 (18,6 %)**, 103 gemelos distintos, el más compartido con 25 puntos (5,6 %). **Número 1: E17538 (41,5 N 78,5 E, Tian Shan) con M63528 (86,5 S 11,5 O, región Haworth, a 25 km de Mons Malapert)**, similitud 97,3, final 72,3. Diferencia real en los 450 pares (mediana / P90): temperatura media 162,7 / 181,2 K; mínima 207,9 / 210,6 K; amplitud 153,8 / 161,3 K; pendiente 1,51 / 2,69°; rugosidad 27,3 / 54,4 m; elevación relativa 2.497 / 4.654 m; irradiancia 4,08 / 4,63 kWh/m²/día. Con D4a, D4c y D5 comparte que el par se parece de verdad en algo medible en valor real (el terreno: pendiente y rugosidad a menos de 4° y 60 m). Con D4c comparte además que las dos variables de la misión, mínima y amplitud, caen cada una en la misma posición relativa (diferencia de percentil mediana 3,2 en mínima y 3,0 en amplitud; P90 7,7 y 7,7). Frente a D4c conserva más pares (450 frente a 338) y usa solo las dos variables de la misión.

**Lo que hay que aceptar si se confirma.** 1.969 candidatos se quedan sin par (siguen en el embudo con su idoneidad). Desglose: 943 solo fallan por terreno (ninguna celda de las regiones a menos de 4° y 60 m; la rugosidad mínima de las regiones es 90,9 m y 1.139 de los que pierden el par tienen menos de 31 m), 237 solo por lo térmico, 196 por las dos cosas y 593 tienen celdas que cumplen el terreno y celdas que cumplen lo térmico, pero no la misma. **Los diez primeros de hoy pierden el par**, y solo 3 de los 100 primeros lo conservan: son los candidatos más fríos y de más amplitud a la vez (nueve en Xinjiang y el Tíbet occidental, con mínima en el percentil 1,8-9,9 y amplitud en el 81-98; el décimo, E41871 en la Puna, con mínima en el 47 y amplitud en el 99), y en las regiones lo frío va con amplitud pequeña (Spearman mínima-amplitud +0,78 en las regiones, −0,05 en los candidatos): **no hay ninguna celda** con amplitud en el percentil ≥ 85 y mínima en el ≤ 30. Los mejores sitios de la misión no tienen gemelo; los que lo tienen son de idoneidad media (mediana 30,9 frente a 38,2 de todos los candidatos; solo 27 del cuartil superior de idoneidad). Si el equipo prefiere cobertura y conservar los mejores sitios, la alternativa es **D4d** (1.986 pares, número 1 Yungay), a costa de que el terreno no se parezca (pendiente 7,8 / 12,2°, rugosidad 206 / 320 m, el síntoma de P7).

**Frase para la web, junto a cada par de Base lunar** (los números, por par; aquí los del número 1):

> "This pair matches by relative thermal position, not by equal temperatures: this site's coldest temperature and daily swing rank among Earth's lunar-base candidates where its twin's rank among the cells of NASA's nine Artemis III candidate regions. In real values the twin is 195 K colder on average (minimum −232 °C at the surface against −24.5 °C air temperature here) and its day-night swing is 138 K larger; slope differs by 0.5° and roughness by 0.3 m."

*Traducción:* "Este par coincide por posición térmica relativa, no por temperaturas iguales: entre los candidatos de la Tierra para la base lunar, la temperatura más fría y la amplitud diaria de este sitio ocupan el mismo puesto que las de su gemelo entre las celdas de las nueve regiones Artemis III de la NASA. En valores reales el gemelo es 195 K más frío de media (mínima de −232 °C en la superficie frente a −24,5 °C de aire aquí) y su ciclo día-noche es 138 K mayor; la pendiente difiere en 0,5° y la rugosidad en 0,3 m." Cifras del número 1 (272,1 / 77,5 K; −24,5 / −231,9 °C; 15,6 / 153,3 K; 6,7 / 7,2°; 238,8 / 238,5 m). En el par mediano serían 163 K, 208 K y 154 K.

---

## 1. Poblaciones y por qué el valor absoluto no da nada

| variable (unidad) | candidatos de la Tierra: mín / p5 / mediana / p95 / máx | regiones de la NASA: mín / p5 / mediana / p95 / máx |
|---|---|---|
| temperatura media (K) | 264,1 / 273,6 / 288,7 / 300,2 / 305,1 | 53,6 / 79,2 / 128,9 / 155,0 / 167,5 |
| amplitud diaria (K) | 15,0 / 15,5 / 19,3 / 25,7 / 35,7 | 87,6 / 144,1 / 178,5 / 217,0 / 233,6 |
| temperatura mínima (°C) | −35,5 / −26,4 / −6,6 / 4,6 / 5,0 (aire, mes más frío) | −240,3 / −233,2 / −214,3 / −201,7 / −197,9 (superficie) |
| pendiente (°) | 0,02 / 0,10 / 0,93 / 4,99 / 10,22 | 3,07 / 3,60 / 9,54 / 16,01 / 21,43 |
| rugosidad (m) | 0,6 / 4,1 / 36,0 / 178,3 / 342,6 | 90,9 / 118,1 / 261,6 / 420,9 / 568,8 |
| elevación relativa (m) | −693 / −570 / 380 / 3.981 / 4.724 | −1.967 / −1.540 / 848 / 5.358 / 6.345 |
| irradiancia (kWh/m²/día) | 3,27 / 3,81 / 4,68 / 5,98 / 6,27 | 0,01 / 0,10 / 0,40 / 0,91 / 1,03 |

Correlación de Spearman entre variables térmicas: temperatura media-amplitud +0,16 en los candidatos y +0,81 en las regiones; mínima-amplitud −0,05 y +0,78; media-mínima +0,91 y +0,93. En las regiones lo más frío es lo que menos oscila (sombra); en los candidatos la amplitud no depende del frío. Esto decide qué pares pueden existir en cualquier diseño que exija las dos variables.

**Una magnitud física relativa tampoco solapa** (comprobado antes de añadir el diseño propio): amplitud / temperatura media, 0,051-0,122 en los candidatos frente a 1,154-2,416 en las regiones (0,725 como mínimo en toda la Luna); amplitud / mínima en K, 0,054-0,130 frente a 2,572-4,360; amplitud del mes de mayor amplitud de la Tierra, 17,4-44,7 K frente a 87,6-233,6 K. Ninguna magnitud física de las tablas acerca los dos cuerpos; solo lo hacen los puestos.

**Forma de la similitud en todos los diseños** (la de `ANALOG_PRINCIPLE.md` §C, con las diferencias en la unidad de cada diseño): `s_v = exp(−0,5 (Δ_v / τ_v)²)`, similitud = `100 × Σ w_v s_v / Σ w_v`; filtro: cada clave con |Δ| ≤ τ, cada secundaria con |Δ| ≤ 2τ; gemelo = la celda de la zona que pasa el filtro con la similitud más alta (empate: id más bajo); final = 0,5 × similitud + 0,5 × idoneidad. "×0,5" y "×2" = supervivientes con la tolerancia de las claves a la mitad y al doble (entre paréntesis, todas las tolerancias escaladas).

## 2. D1. z por cuerpo (como el motor)

**Normalización:** `z = (valor − mediana) / (rango intercuartílico / 1,349)`, recortado a ±4, sobre la población de cada cuerpo: Tierra = tierra firme (`elevation_m > 0`, 25.095 celdas; sin temperatura en la Antártida), Luna = las 64.800 celdas; es `analog_finder.normalize_planetary_features`. Escalas: temperatura media 284,27 / 21,49 K (Tierra) y 197,70 / 32,29 K (Luna); amplitud 8,59 / 6,60 K y 265,56 / 47,84 K. **Variables y pesos:** temperatura media 50, amplitud 50. **Tolerancia:** 0,5 z (media desviación típica robusta, la regla de `ANALOG_PRINCIPLE.md`).

| zona | sobreviven | ×0,5 | ×2 | hueco mínimo |
|---|---|---|---|---|
| nueve regiones | **0** | 0 | 0 | temperatura 0,003 z (los extremos se tocan: candidato más frío −0,94, celda más cálida −0,94); **amplitud 1,64 z** (candidatos +0,97 a +4; regiones −3,72 a −0,67) |
| polo sur | 0 | 0 | 0 | amplitud 1,45 z |
| Luna entera | 518 | 86 | 1.818 | — |

Con la Luna entera los gemelos son celdas ecuatoriales, no de las regiones: 9 gemelos distintos, el primero (M34470, Bandfield a 9 km) con 258 puntos (49,8 %), los tres primeros con el 95,2 %; similitud mín / p10 / mediana / p90 / máx 61,3 / 66,6 / 81,4 / 94,2 / 99,8; Spearman similitud-idoneidad −0,55. Diferencia real (mediana / P90): temperatura media 75,4 / 79,5 K; mínima 181,9 / 187,5 K; **amplitud 289,6 / 295,1 K**; pendiente 2,84 / 3,61°; rugosidad 95,8 / 137,0 m; elevación relativa 2.195 / 3.554 m; irradiancia 5,61 / 6,35 kWh/m²/día. (Con similitud ≥ 90, 108 pares: amplitud 294,7 / 296,2 K.)

**Qué se le puede decir al jurado:** nada en las regiones de la NASA: ni siquiera en posición relativa son parecidas, porque la Tierra aporta sus sitios de mayor amplitud y la NASA eligió los de menor amplitud de la Luna. Con la Luna entera, "misma posición relativa en su cuerpo", con un hueco real de unos 75 K de media y 290 K de amplitud, y el gemelo fuera de las regiones.

| # | Tierra | idon. | sim. | final | puesto hoy | gemelo | región NASA | T media (K) | T mín (°C) | amplitud (K) | pendiente (°) | rugosidad (m) | elev. rel. (m) | irradiancia | posición relativa T / L (unidad del diseño) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E20703 (32,5 N 3,5 E) | 37,7 | 95,9 | 66,8 | 1.748 | M32647 (0,5 S 67,5 E, Pomortsev a 42 km) | — | 297,2 / 219,1 | 3,7 / -179,3 | 16,3 / 311,8 | 0,5 / 3,2 | 17,9 / 139,5 | -97,2 / -1.410,4 | 5,52 / 10,39 | temp_k: 0,6 / 0,7; amp: 1,2 / 1,0 |
| 2 | E43519 (30,5 S 139,5 E) | 38,3 | 93,8 | 66,1 | 1.683 | M32647 (0,5 S 67,5 E, Pomortsev a 42 km) | — | 296,3 / 219,1 | 4,6 / -179,3 | 16,5 / 311,8 | 0,7 / 3,2 | 34,5 / 139,5 | -518,2 / -1.410,4 | 5,59 / 10,39 | temp_k: 0,6 / 0,7; amp: 1,2 / 1,0 |
| 3 | E19984 (34,5 N 4,5 E) | 37,3 | 93,3 | 65,3 | 1.723 | M32647 (0,5 S 67,5 E, Pomortsev a 42 km) | — | 295,3 / 219,1 | 2,7 / -179,3 | 16,4 / 311,8 | 1,0 / 3,2 | 37,5 / 139,5 | -115,6 / -1.410,4 | 5,20 / 10,39 | temp_k: 0,5 / 0,7; amp: 1,2 / 1,0 |
| 4 | E22890 (26,5 N 30,5 E) | 41,3 | 89,1 | 65,2 | 1.638 | M32647 (0,5 S 67,5 E, Pomortsev a 42 km) | — | 298,6 / 219,1 | 4,5 / -179,3 | 17,3 / 311,8 | 0,3 / 3,2 | 13,0 / 139,5 | -414,2 / -1.410,4 | 6,06 / 10,39 | temp_k: 0,7 / 0,7; amp: 1,3 / 1,0 |
| 5 | E20748 (32,5 N 48,5 E) | 32,2 | 97,3 | 64,7 | 1.825 | M32647 (0,5 S 67,5 E, Pomortsev a 42 km) | — | 298,9 / 219,1 | 4,4 / -179,3 | 16,1 / 311,8 | 2,6 / 3,2 | 128,7 / 139,5 | -200,5 / -1.410,4 | 4,99 / 10,39 | temp_k: 0,7 / 0,7; amp: 1,1 / 1,0 |
| 6 | E20344 (33,5 N 4,5 E) | 39,0 | 90,2 | 64,6 | 1.678 | M32647 (0,5 S 67,5 E, Pomortsev a 42 km) | — | 297,1 / 219,1 | 3,1 / -179,3 | 17,1 / 311,8 | 0,3 / 3,2 | 9,6 / 139,5 | -214,0 / -1.410,4 | 5,38 / 10,39 | temp_k: 0,6 / 0,7; amp: 1,3 / 1,0 |
| 7 | E17517 (41,5 N 57,5 E) | 37,8 | 91,3 | 64,5 | 1.612 | M34470 (5,5 S 90,5 E, Bandfield a 9 km) | — | 290,6 / 212,0 | -6,4 / -186,0 | 15,8 / 305,1 | 0,1 / 3,6 | 6,2 / 107,3 | -648,2 / -2.817,6 | 4,42 / 10,35 | temp_k: 0,3 / 0,4; amp: 1,1 / 0,8 |
| 8 | E20383 (33,5 N 43,5 E) | 38,4 | 90,5 | 64,4 | 1.842 | M32647 (0,5 S 67,5 E, Pomortsev a 42 km) | — | 298,8 / 219,1 | 3,7 / -179,3 | 17,1 / 311,8 | 0,1 / 3,2 | 5,0 / 139,5 | -633,3 / -1.410,4 | 5,28 / 10,39 | temp_k: 0,7 / 0,7; amp: 1,3 / 1,0 |
| 9 | E20704 (32,5 N 4,5 E) | 39,1 | 89,6 | 64,4 | 1.735 | M32647 (0,5 S 67,5 E, Pomortsev a 42 km) | — | 298,1 / 219,1 | 4,2 / -179,3 | 17,2 / 311,8 | 0,2 / 3,2 | 8,4 / 139,5 | -366,2 / -1.410,4 | 5,53 / 10,39 | temp_k: 0,6 / 0,7; amp: 1,3 / 1,0 |
| 10 | E16440 (44,5 N 60,5 E) | 39,5 | 89,1 | 64,3 | 1.458 | M34470 (5,5 S 90,5 E, Bandfield a 9 km) | — | 287,9 / 212,0 | -11,8 / -186,0 | 15,4 / 305,1 | 0,0 / 3,6 | 0,9 / 107,3 | -656,8 / -2.817,6 | 4,40 / 10,35 | temp_k: 0,2 / 0,4; amp: 1,0 / 0,8 |

## 3. D2. Percentil por cuerpo

**Normalización:** percentil de rango medio `100 × (n.º de valores menores + n.º de iguales / 2) / n` dentro de la misma población que D1 (tierra firme; Luna entera). **Pesos:** temperatura media 50, amplitud 50. **Tolerancia:** 10 puntos de percentil (una banda del 20 % de cada cuerpo).

| zona | sobreviven | ×0,5 | ×2 | hueco mínimo |
|---|---|---|---|---|
| nueve regiones | **0** | 0 | 0 | temperatura 0,004 puntos (candidatos 18,3-98,9; regiones 0,05-24,3); **amplitud 45,8 puntos** (candidatos 75,6-100; regiones 0,04-29,8); mediana del hueco conjunto por punto 60,5 |
| polo sur | 0 | 0 | 0 | amplitud 41,0 puntos |
| Luna entera | 1.287 | 788 | 2.173 | — |

Luna entera: 436 gemelos, el primero (M42828, Zelinskiy a 44 km) con 126 (9,8 %); similitud 61,8 / 71,5 / 96,2 / 100 / 100; Spearman +0,33. Diferencia real: temperatura media 84,3 / 85,8 K; mínima 182,6 / 185,8 K; amplitud 275,4 / 276,7 K; pendiente 7,7 / 11,2°; rugosidad 214,5 / 328,7 m; elevación relativa 1.152 / 3.120 m; irradiancia 4,7 / 5,3 kWh/m²/día.

**Jurado:** igual que D1. En las regiones no hay pares; en la Luna entera, "mismo percentil de su mundo", con 84 K y 275 K de hueco real.

| # | Tierra | idon. | sim. | final | puesto hoy | gemelo | región NASA | T media (K) | T mín (°C) | amplitud (K) | pendiente (°) | rugosidad (m) | elev. rel. (m) | irradiancia | posición relativa T / L (unidad del diseño) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E40430 (22,5 S 69,5 O) | 74,3 | 100,0 | 87,1 | 72 | M33052 (1,5 S 112,5 E, Buisson a 14 km) | — | 299,7 / 215,4 | 3,8 / -181,9 | 35,7 / 303,5 | 1,6 / 7,8 | 50,8 / 222,7 | 957,1 / 115,2 | 6,03 / 10,39 | temp_k: 86,7 / 86,8; amp: 100,0 / 100,0 |
| 2 | E40790 (23,5 S 69,5 O) | 74,2 | 99,9 | 87,1 | 38 | M30166 (6,5 N 106,5 E, Al Khwarizmi a 22 km) | — | 298,8 / 214,6 | 3,9 / -181,7 | 35,3 / 300,8 | 2,2 / 10,7 | 67,8 / 294,6 | 981,5 / -1.201,7 | 6,05 / 10,33 | temp_k: 83,0 / 82,9; amp: 100,0 / 99,5 |
| 3 | E39710 (20,5 S 69,5 O) | 71,0 | 100,0 | 85,5 | 70 | M33811 (3,5 S 151,5 E, Chaplygin a 79 km) | — | 299,4 / 215,2 | 4,8 / -186,2 | 33,8 / 304,6 | 2,4 / 6,2 | 84,3 / 210,6 | 899,9 / 3.264,1 | 5,86 / 10,38 | temp_k: 85,6 / 85,8; amp: 100,0 / 100,0 |
| 4 | E41150 (24,5 S 69,5 O) | 73,7 | 91,2 | 82,5 | 41 | M34470 (5,5 S 90,5 E, Bandfield a 9 km) | — | 296,0 / 212,0 | 2,6 / -186,0 | 34,4 / 305,1 | 2,4 / 3,6 | 76,8 / 107,3 | 1.509,8 / -2.817,6 | 5,99 / 10,35 | temp_k: 68,2 / 74,4; amp: 100,0 / 100,0 |
| 5 | E21479 (30,5 N 59,5 E) | 59,9 | 100,0 | 79,9 | 640 | M30808 (4,5 N 28,5 E, Maskelyne a 85 km) | — | 305,1 / 219,3 | 2,8 / -179,3 | 29,1 / 301,5 | 0,9 / 0,5 | 39,1 / 13,1 | 184,3 / -1.477,3 | 5,32 / 10,36 | temp_k: 98,9 / 98,9; amp: 99,8 / 99,8 |
| 6 | E21474 (30,5 N 54,5 E) | 60,0 | 99,7 | 79,8 | 389 | M34110 (4,5 S 90,5 E, Hume a 5 km) | — | 297,7 / 212,9 | -3,1 / -183,4 | 27,5 / 302,9 | 1,3 / 1,9 | 48,7 / 79,0 | 1.127,2 / -3.441,3 | 5,36 / 10,36 | temp_k: 76,3 / 77,3; amp: 99,7 / 100,0 |
| 7 | E21118 (31,5 N 58,5 E) | 59,2 | 100,0 | 79,6 | 658 | M33355 (2,5 S 55,5 E, Dorsa Andrusov a 48 km) | — | 304,0 / 218,4 | 2,5 / -179,9 | 28,6 / 301,6 | 0,6 / 0,9 | 19,6 / 28,3 | 35,0 / -2.170,8 | 5,30 / 10,39 | temp_k: 97,6 / 97,7; amp: 99,8 / 99,8 |
| 8 | E21485 (30,5 N 65,5 E) | 58,7 | 100,0 | 79,4 | 624 | M30849 (4,5 N 69,5 E, Dubyago a 14 km) | — | 300,9 / 216,2 | 1,1 / -180,8 | 27,9 / 301,4 | 0,3 / 6,3 | 18,6 / 218,1 | 411,2 / -1.475,6 | 5,39 / 10,36 | temp_k: 90,3 / 90,6; amp: 99,7 / 99,8 |
| 9 | E21475 (30,5 N 55,5 E) | 57,6 | 99,8 | 78,7 | 409 | M34470 (5,5 S 90,5 E, Bandfield a 9 km) | — | 297,3 / 212,0 | -2,7 / -186,0 | 26,3 / 305,1 | 1,7 / 3,6 | 62,1 / 107,3 | 1.121,8 / -2.817,6 | 5,34 / 10,35 | temp_k: 73,8 / 74,4; amp: 99,4 / 100,0 |
| 10 | E20758 (32,5 N 58,5 E) | 56,7 | 100,0 | 78,3 | 644 | M35546 (8,5 S 86,5 E, Houtermans a 38 km) | — | 300,5 / 216,0 | -0,2 / -181,6 | 26,6 / 300,7 | 0,9 / 6,4 | 33,2 / 213,2 | 416,3 / -1.049,9 | 5,23 / 10,28 | temp_k: 89,4 / 89,7; amp: 99,5 / 99,4 |

## 4. D3. Posición dentro de lo que cada cuerpo ofrece para esta misión

**Normalización:** percentil de rango medio `100 × (rango − 0,5) / n` (empates promediados) dentro de dos poblaciones elegidas: los 2.419 candidatos de la Tierra por un lado y las celdas de la zona por otro (280 en las regiones). Variante D3z: z robusto (mediana, rango intercuartílico / 1,349, sin recorte) dentro de esas mismas poblaciones. **Pesos:** temperatura media 50, amplitud 50. **Tolerancia:** 10 puntos (D3z: 0,5 z).

**Qué hace, dicho claro:** empareja "los candidatos más fríos de la Tierra con las celdas más frías de la zona" y "los de más amplitud con los de más amplitud". Siempre da pares porque compara puestos dentro de dos listas que nosotros elegimos; si se cambia la lista (otro embudo, otra zona), cambian los puestos. No dice nada de cuánto se parecen los valores: el hueco real es el mismo que sin método.

| diseño, zona | sobreviven | ×0,5 | ×2 | gemelos distintos | mayor cuota | similitud mín / p10 / mediana / p90 / máx | Spearman sim-idoneidad |
|---|---|---|---|---|---|---|---|
| D3, regiones | **2.186** | 1.739 | 2.419 | 254 | M63222 (Masina a 25 km, Nobile Rim 1): 64, 2,9 % | 64,3 / 87,1 / 97,7 / 99,7 / 100 | −0,08 |
| D3, polo sur | 2.384 | 2.256 | 2.419 | 1.284 | M64326 (Tooley a 20 km): 76, 3,2 % | 67,6 / 96,2 / 99,8 / 100 / 100 | −0,09 |
| D3, Luna entera | 1.730 | 1.440 | 2.115 | 734 | M47689 (Tycho a 29 km): 57, 3,3 % | 61,1 / 86,0 / 99,6 / 100 / 100 | +0,18 |
| D3z, regiones | 2.270 | 2.011 | 2.378 | 221 | M63517 (Haworth a 40 km): 130, 5,7 % | 65,0 / 91,8 / 98,7 / 99,9 / 100 | −0,01 |
| D3z, polo sur | 2.315 | 2.256 | 2.389 | 1.199 | M63173 (Lhamu a 17 km): 31, 1,3 % | 68,0 / 98,3 / 99,9 / 100 / 100 | −0,17 |
| D3z, Luna entera | 1.911 | 1.414 | 2.174 | 506 | M34503 (Necho a 11 km): 107, 5,6 % | 62,4 / 82,8 / 98,8 / 100 / 100 | −0,20 |

**Diferencia real en los pares que sobreviven** (mediana / P90):

| variable | D3 regiones | D3 polo sur | D3 Luna entera | D3z regiones |
|---|---|---|---|---|
| temperatura media (K) | 160,2 / 180,5 | 158,6 / 185,6 | 85,7 / 124,0 | 158,5 / 175,9 |
| temperatura mínima (K) | 207,6 / 215,1 | 206,7 / 213,7 | 177,0 / 186,4 | 206,9 / 215,2 |
| amplitud (K) | 159,0 / 176,6 | 167,6 / 184,9 | 233,5 / 268,5 | 158,4 / 174,3 |
| pendiente (°) | 7,71 / 12,74 | 6,1 / 11,7 | 7,0 / 10,9 | 7,45 / 12,03 |
| rugosidad (m) | 209,1 / 363,2 | 171,8 / 336,9 | 212,9 / 322,3 | 202,6 / 358,1 |
| elevación relativa (m) | 1.585 / 5.737 | 1.813 / 5.397 | 1.624 / 4.011 | 1.715 / 5.947 |
| irradiancia (kWh/m²/día) | 4,27 / 5,19 | 4,0 / 5,0 | 3,3 / 4,6 | 4,27 / 5,19 |

Con similitud ≥ 90 (1.859 pares en D3, regiones) las diferencias son las mismas (160,0 / 180,8 K; 158,8 / 175,6 K; pendiente 7,7 / 12,5°): la similitud alta no acerca los valores. 233 candidatos se quedan sin par en las regiones; 9 de los 10 primeros de hoy entre ellos (el otro, E18986, pasa al puesto 269).

**Jurado:** "el par ocupa el mismo puesto térmico relativo dentro de los candidatos de la Tierra y dentro de las regiones de la NASA; la diferencia real es de unos 160 K de temperatura media y 159 K de amplitud". No se puede decir que el terreno se parezca: pendiente unas 8° distinta y rugosidad unos 200 m.

| # | Tierra | idon. | sim. | final | puesto hoy | gemelo | región NASA | T media (K) | T mín (°C) | amplitud (K) | pendiente (°) | rugosidad (m) | elev. rel. (m) | irradiancia | posición relativa T / L (unidad del diseño) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E40790 (23,5 S 69,5 O) | 74,2 | 99,6 | 86,9 | 38 | M62393 (83,5 S 66,5 O, Ibn Bajja a 88 km) | Peak Near Cabeus B | 298,8 / 150,7 | 3,9 / -209,0 | 35,3 / 227,5 | 2,2 / 20,7 | 67,8 / 536,1 | 981,5 / 1.994,8 | 6,05 / 0,84 | temp_k: 89,5 / 89,1; amp: 99,9 / 98,8 |
| 2 | E40430 (22,5 S 69,5 O) | 74,3 | 98,3 | 86,3 | 72 | M62499 (83,5 S 39,5 E, Floss a 25 km) | Mons Mouton Plateau | 299,7 / 158,8 | 3,8 / -201,9 | 35,7 / 229,1 | 1,6 / 13,8 | 50,8 / 399,9 | 957,1 / 3.039,4 | 6,03 / 1,01 | temp_k: 93,6 / 96,2; amp: 100,0 / 99,5 |
| 3 | E41150 (24,5 S 69,5 O) | 73,7 | 96,8 | 85,3 | 41 | M63184 (85,5 S 4,5 E, Lhamu a 19 km) | Malapert Massif | 296,0 / 145,4 | 2,6 / -203,6 | 34,4 / 222,2 | 2,4 / 16,1 | 76,8 / 484,4 | 1.509,8 / 1.328,2 | 5,99 / 0,52 | temp_k: 77,3 / 80,2; amp: 99,9 / 97,7 |
| 4 | E39710 (20,5 S 69,5 O) | 71,0 | 97,3 | 84,2 | 70 | M62393 (83,5 S 66,5 O, Ibn Bajja a 88 km) | Peak Near Cabeus B | 299,4 / 150,7 | 4,8 / -209,0 | 33,8 / 227,5 | 2,4 / 20,7 | 84,3 / 536,1 | 899,9 / 1.994,8 | 5,86 / 0,84 | temp_k: 92,2 / 89,1; amp: 99,8 / 98,8 |
| 5 | E39350 (19,5 S 69,5 O) | 67,0 | 94,4 | 80,7 | 79 | M63184 (85,5 S 4,5 E, Lhamu a 19 km) | Malapert Massif | 295,7 / 145,4 | 1,2 / -203,6 | 30,9 / 222,2 | 3,4 / 16,1 | 119,0 / 484,4 | 1.727,2 / 1.328,2 | 5,71 / 0,52 | temp_k: 75,6 / 80,2; amp: 99,3 / 97,7 |
| 6 | E21479 (30,5 N 59,5 E) | 59,9 | 99,4 | 79,6 | 640 | M62502 (83,5 S 42,5 E, Floss a 24 km) | Mons Mouton Plateau | 305,1 / 161,6 | 2,8 / -197,9 | 29,1 / 228,4 | 0,9 / 14,2 | 39,1 / 390,7 | 184,3 / 1.813,2 | 5,32 / 1,03 | temp_k: 100,0 / 98,4; amp: 98,8 / 99,1 |
| 7 | E21474 (30,5 N 54,5 E) | 60,0 | 99,0 | 79,5 | 389 | M62392 (83,5 S 67,5 O, Ibn Bajja a 87 km) | Peak Near Cabeus B | 297,7 / 148,2 | -3,1 / -209,5 | 27,5 / 217,4 | 1,3 / 17,6 | 48,7 / 490,6 | 1.127,2 / 2.785,5 | 5,36 / 0,89 | temp_k: 84,8 / 84,6; amp: 97,9 / 95,9 |
| 8 | E16118 (45,5 N 98,5 E) | 59,6 | 99,2 | 79,4 | 69 | M62522 (83,5 S 62,5 E, Oberbeck a 19 km) | Nobile Rim 2 | 279,4 / 98,2 | -23,9 / -223,5 | 22,0 / 196,5 | 1,9 / 10,5 | 68,2 / 246,8 | 1.264,7 / -663,9 | 4,23 / 0,37 | temp_k: 17,8 / 16,6; amp: 79,6 / 80,9 |
| 9 | E21485 (30,5 N 65,5 E) | 58,7 | 100,0 | 79,4 | 624 | M62500 (83,5 S 40,5 E, Floss a 24 km) | Mons Mouton Plateau | 300,9 / 159,2 | 1,1 / -200,9 | 27,9 / 226,7 | 0,3 / 14,5 | 18,6 / 405,8 | 411,2 / 2.514,3 | 5,39 / 0,94 | temp_k: 96,9 / 97,0; amp: 98,3 / 98,4 |
| 10 | E40791 (23,5 S 68,5 O) | 68,9 | 89,8 | 79,3 | 94 | M63184 (85,5 S 4,5 E, Lhamu a 19 km) | Malapert Massif | 295,1 / 145,4 | -0,6 / -203,6 | 30,9 / 222,2 | 2,0 / 16,1 | 69,4 / 484,4 | 1.931,0 / 1.328,2 | 6,03 / 0,52 | temp_k: 73,6 / 80,2; amp: 99,3 / 97,7 |

D3z, regiones:

| # | Tierra | idon. | sim. | final | puesto hoy | gemelo | región NASA | T media (K) | T mín (°C) | amplitud (K) | pendiente (°) | rugosidad (m) | elev. rel. (m) | irradiancia | posición relativa T / L (unidad del diseño) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E15758 (46,5 N 98,5 E) | 62,0 | 98,4 | 80,2 | 43 | M62522 (83,5 S 62,5 E, Oberbeck a 19 km) | Nobile Rim 2 | 275,0 / 98,2 | -28,4 / -223,5 | 22,6 / 196,5 | 1,6 / 10,5 | 57,2 / 246,8 | 1.506,4 / -663,9 | 4,05 / 0,37 | temp_k: -1,4 / -1,2; amp: 1,1 / 1,1 |
| 2 | E16477 (44,5 N 97,5 E) | 60,5 | 99,4 | 80,0 | 120 | M62521 (83,5 S 61,5 E, Oberbeck a 23 km) | Nobile Rim 2 | 283,4 / 114,3 | -22,8 / -215,0 | 22,5 / 196,9 | 1,5 / 13,1 | 53,8 / 317,1 | 865,6 / 4,6 | 4,41 / 0,54 | temp_k: -0,5 / -0,6; amp: 1,0 / 1,1 |
| 3 | E21474 (30,5 N 54,5 E) | 60,0 | 99,7 | 79,9 | 389 | M62495 (83,5 S 35,5 E, Floss a 32 km) | Mons Mouton Plateau | 297,7 / 150,6 | -3,1 / -199,2 | 27,5 / 222,5 | 1,3 / 15,2 | 48,7 / 413,1 | 1.127,2 / 2.795,3 | 5,36 / 0,80 | temp_k: 0,9 / 0,9; amp: 2,7 / 2,6 |
| 4 | E16478 (44,5 N 98,5 E) | 60,4 | 98,9 | 79,7 | 111 | M62521 (83,5 S 61,5 E, Oberbeck a 23 km) | Nobile Rim 2 | 282,0 / 114,3 | -21,6 / -215,0 | 22,9 / 196,9 | 1,3 / 13,1 | 40,9 / 317,1 | 1.063,6 / 4,6 | 4,38 / 0,54 | temp_k: -0,7 / -0,6; amp: 1,1 / 1,1 |
| 5 | E18986 (37,5 N 86,5 E) | 60,3 | 98,4 | 79,4 | 5 | M62522 (83,5 S 62,5 E, Oberbeck a 19 km) | Nobile Rim 2 | 275,9 / 98,2 | -23,8 / -223,5 | 22,2 / 196,5 | 5,1 / 10,5 | 186,2 / 246,8 | 3.187,6 / -663,9 | 4,46 / 0,37 | temp_k: -1,3 / -1,2; amp: 0,9 / 1,1 |
| 6 | E16474 (44,5 N 94,5 E) | 59,0 | 99,2 | 79,1 | 197 | M62479 (83,5 S 19,5 E, Mons Mouton a 49 km) | Mons Mouton Plateau | 286,9 / 123,3 | -19,4 / -219,8 | 22,4 / 193,9 | 1,4 / 5,3 | 53,0 / 172,7 | 349,3 / 1.394,5 | 4,49 / 0,54 | temp_k: -0,2 / -0,2; amp: 1,0 / 0,9 |
| 7 | E17193 (42,5 N 93,5 E) | 58,3 | 99,7 | 79,0 | 510 | M63222 (85,5 S 42,5 E, Masina a 25 km) | Nobile Rim 1 | 290,1 / 133,4 | -16,4 / -205,0 | 24,5 / 207,1 | 0,7 / 18,6 | 25,9 / 445,6 | 19,2 / 2.306,4 | 4,67 / 0,42 | temp_k: 0,1 / 0,2; amp: 1,7 / 1,7 |
| 8 | E15393 (47,5 N 93,5 E) | 58,9 | 99,2 | 79,0 | 119 | M63536 (86,5 S 3,5 O, Mons Malapert a 16 km) | Malapert Massif | 278,3 / 103,2 | -29,1 / -230,5 | 20,7 / 184,6 | 1,3 / 12,9 | 51,4 / 340,6 | 722,7 / 1.641,9 | 4,00 / 0,21 | temp_k: -1,0 / -1,0; amp: 0,5 / 0,4 |
| 9 | E17191 (42,5 N 91,5 E) | 58,6 | 99,3 | 79,0 | 516 | M63222 (85,5 S 42,5 E, Masina a 25 km) | Nobile Rim 1 | 291,3 / 133,4 | -16,4 / -205,0 | 24,7 / 207,1 | 0,8 / 18,6 | 24,8 / 445,6 | -26,0 / 2.306,4 | 4,65 / 0,42 | temp_k: 0,3 / 0,2; amp: 1,7 / 1,7 |
| 10 | E16120 (45,5 N 100,5 E) | 58,5 | 99,4 | 79,0 | 137 | M63535 (86,5 S 4,5 O, Mons Malapert a 17 km) | Malapert Massif | 280,3 / 107,7 | -23,4 / -229,7 | 21,6 / 189,6 | 1,2 / 12,9 | 58,1 / 336,5 | 843,8 / 1.541,3 | 4,23 / 0,21 | temp_k: -0,8 / -0,9; amp: 0,7 / 0,7 |

## 5. D4. Reponderación: térmico relativo 80 %, terreno real 20 %

**Normalización:** las variables térmicas como en D3 (percentil dentro de los 2.419 candidatos y dentro de las celdas de la zona), tolerancia 10 puntos, filtro en cada una. Terreno en valor real con las tolerancias del equipo (`rover_preset.py`, 5 km): pendiente `slope_iso_deg` τ 2° (filtro 4°), rugosidad τ 30 m (filtro 60 m).

| variante | pesos |
|---|---|
| D4a | temperatura media 40, amplitud 40, pendiente 10, rugosidad 10 |
| **D4b** | **mínima 40, amplitud 40, pendiente 10, rugosidad 10** (la mínima sustituye a la media) |
| D4c | amplitud 35, mínima 25, media 20, pendiente 10, rugosidad 10 (amplitud y mínima con sus pesos del bloque `soft`; la media completa el 80 %) |
| D4d | mínima 50, amplitud 50, sin terreno (para ver qué quita el terreno) |

| variante, zona | sobreviven | ×0,5 claves (todas) | ×2 claves (todas) | sin filtro de terreno | gemelos distintos | mayor cuota | similitud mín / p10 / mediana / p90 / máx | Spearman sim-idoneidad |
|---|---|---|---|---|---|---|---|---|
| D4a, regiones | 457 | 265 (133) | 724 (1.788) | 2.186 | 96 | M62515 (Wapowski a 14 km, Nobile Rim 2): 21, 4,6 % | 59,1 / 74,8 / 87,5 / 96,8 / 99,3 | −0,07 |
| **D4b, regiones** | **450** | 276 (128) | 717 (1.669) | 1.986 | **103** | M62848 (Mons Mouton a 8 km, Mons Mouton Plateau): 25, 5,6 % | 54,1 / 75,4 / 87,4 / 96,0 / 99,5 | −0,02 |
| D4c, regiones | 338 | 114 (53) | 641 (1.521) | 1.789 | 82 | M63659 (Slater a 49 km, Slater Plain): 17, 5,0 % | 54,6 / 75,5 / 85,3 / 94,7 / 99,4 | +0,03 |
| D4d, regiones | 1.986 | 1.590 | 2.348 | — | 246 | M62522 (Oberbeck a 19 km, Nobile Rim 2): 72, 3,6 % | 62,1 / 86,4 / 97,8 / 99,7 / 100 | −0,10 |
| D4a, polo sur | 1.860 | 1.367 (1.040) | 2.248 (2.411) | 2.384 | 523 | M60076 (Schrödinger a 60 km): 43, 2,3 % | 58,5 / 77,9 / 93,4 / 98,8 / 99,9 | −0,21 |
| D4b, polo sur | 1.786 | 1.427 (1.071) | 2.212 (2.388) | 2.374 | 548 | M60430 (Schrödinger a 86 km): 48, 2,7 % | 56,8 / 80,2 / 94,2 / 98,9 / 100 | −0,19 |
| D4c, polo sur | 1.606 | 945 (615) | 2.166 (2.376) | 2.305 | 523 | M60430: 44, 2,7 % | 58,3 / 78,8 / 91,0 / 97,6 / 99,8 | −0,24 |
| D4d, polo sur | 2.374 | 2.298 | 2.419 | — | 1.356 | M64469 (Spudis a 16 km): 30, 1,3 % | 62,8 / 97,6 / 99,8 / 100 / 100 | +0,02 |
| D4a, Luna entera | 1.328 | 933 (879) | 1.932 (1.999) | 1.730 | 680 | M41900 (Puiseux a 41 km): 47, 3,5 % | 56,7 / 78,1 / 96,6 / 99,9 / 100 | +0,20 |
| D4b, Luna entera | 1.545 | 1.247 (1.146) | 1.932 (2.059) | 1.905 | 754 | M44455 (Deslandres a 40 km): 52, 3,4 % | 59,5 / 84,0 / 97,8 / 99,9 / 100 | +0,21 |
| D4c, Luna entera | 1.199 | 723 (676) | 1.779 (1.896) | 1.453 | 684 | M7009 (Anaxagoras a 90 km): 19, 1,6 % | 58,8 / 80,3 / 94,5 / 99,2 / 100 | +0,10 |
| D4d, Luna entera | 1.905 | 1.687 | 2.167 | — | 986 | M10311 (Thales a 19 km): 47, 2,5 % | 65,2 / 91,2 / 99,8 / 100 / 100 | +0,24 |

**Diferencia real en los pares que sobreviven, regiones** (mediana / P90; entre corchetes, solo similitud ≥ 90):

| variable | D4a (457; [160]) | **D4b (450; [176])** | D4c (338; [90]) | D4d (1.986; [1.678]) |
|---|---|---|---|---|
| temperatura media (K) | 167,9 / 185,7 [171,4 / 186,9] | **162,7 / 181,2** [164,6 / 185,9] | 166,6 / 185,9 [175,8 / 192,7] | 162,2 / 182,6 [162,2 / 182,3] |
| temperatura mínima (K) | 208,3 / 216,0 | **207,9 / 210,6** [207,5 / 209,4] | 207,8 / 210,2 | 207,8 / 209,9 |
| amplitud (K) | 152,8 / 161,6 [151,6 / 160,0] | **153,8 / 161,3** [152,7 / 159,4] | 152,3 / 160,9 | 159,4 / 174,6 |
| pendiente (°) | 1,44 / 2,69 [0,80 / 1,59] | **1,51 / 2,69** [0,92 / 1,89] | 1,46 / 2,75 | 7,82 / 12,22 |
| rugosidad (m) | 28,0 / 55,4 [13,5 / 30,7] | **27,3 / 54,4** [13,3 / 32,6] | 26,9 / 54,7 | 205,8 / 319,7 |
| elevación relativa (m) | 2.409 / 4.814 | **2.497 / 4.654** | 2.542 / 4.497 | 1.340 / 4.495 |
| irradiancia (kWh/m²/día) | 4,10 / 4,60 | **4,08 / 4,63** | 4,09 / 4,62 | 4,28 / 5,23 |

Polo sur (D4b): temperatura media 158,6 / 182,7 K; mínima 206,6 / 208,8 K; amplitud 167,0 / 180,2 K; pendiente 0,7 / 1,8°; rugosidad 15,6 / 51,5 m. Luna entera (D4b): 91,7 / 126,4 K; 181,1 / 183,3 K; 246,9 / 270,6 K; 0,2 / 1,0°; 6,0 / 33,1 m.

**Por qué la tolerancia de 10 puntos.** Es una banda de ±10 % de cada población: con 280 celdas, unas 56 celdas por variable. A la mitad (5 puntos) D4b se queda en 276; al doble (20), 717, y con 20 puntos un candidato del percentil 50 puede emparejarse con una celda del 30 o del 70, que ya no es "el mismo puesto". Con el terreno también escalado: 128 y 1.669. El terreno es lo que más filtra: sin su filtro sobreviven 1.986; solo 1.280 candidatos tienen alguna celda de las regiones a menos de 4° y 60 m, y 1.139 de los 1.969 que pierden el par tienen rugosidad < 31 m.

**Diferencia de percentil en los pares** (lo que sí garantiza el método): D4b, mínima 3,2 / 7,7 puntos (mediana / P90) y amplitud 3,0 / 7,7.

**Jurado (D4b):** "el par ocupa el mismo puesto en frío mínimo y en amplitud diaria dentro de los candidatos de la Tierra y dentro de las regiones de la NASA, y su pendiente y rugosidad están a menos de 4° y 60 m (mediana 1,5° y 27 m); la diferencia real es de unos 163 K de temperatura media, 208 K de mínima y 154 K de amplitud". No se puede decir que el ambiente térmico se parezca ni que el sitio de la Tierra reproduzca el frío lunar.

D4b, regiones (recomendado). Lugares aproximados de la Tierra: 1 Tian Shan central (frontera Kirguistán-China); 2, 5 y 7 Tian Shan oriental (Xinjiang); 3 Altái mongol; 4 Alto Atlas (Marruecos); 6 Andes de Coquimbo (Chile); 8 Pamir-Kashgar; 9 Altun Shan (Xinjiang); 10 Anti-Atlas (Marruecos).

| # | Tierra | idon. | sim. | final | puesto hoy | gemelo | región NASA | T media (K) | T mín (°C) | amplitud (K) | pendiente (°) | rugosidad (m) | elev. rel. (m) | irradiancia | posición relativa T / L (unidad del diseño) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E17538 (41,5 N 78,5 E) | 47,3 | 97,3 | 72,3 | 67 | M63528 (86,5 S 11,5 O, Mons Malapert a 25 km) | Haworth | 272,1 / 77,5 | -24,5 / -231,9 | 15,6 / 153,3 | 6,7 / 7,2 | 238,8 / 238,5 | 2.807,0 / 680,7 | 4,09 / 0,10 | tmin_c: 8,4 / 8,0; amp: 6,7 / 10,2 |
| 2 | E16830 (43,5 N 90,5 E) | 48,0 | 96,6 | 72,3 | 207 | M63841 (87,5 S 58,5 O, Cartwright a 15 km) | de Gerlache Rim 2 | 282,4 / 98,7 | -18,9 / -227,0 | 18,0 / 172,6 | 3,1 / 4,2 | 118,6 / 128,2 | 888,3 / -1.254,7 | 4,37 / 0,17 | tmin_c: 21,5 / 18,8; amp: 33,1 / 32,5 |
| 3 | E15751 (46,5 N 91,5 E) | 46,6 | 96,9 | 71,7 | 246 | M64018 (87,5 S 118,5 E, Slater a 19 km) | Slater Plain | 273,8 / 79,7 | -25,9 / -232,5 | 16,0 / 153,3 | 4,7 / 6,3 | 164,1 / 167,9 | 1.565,1 / -571,8 | 4,01 / 0,09 | tmin_c: 5,8 / 6,6; amp: 11,6 / 10,5 |
| 4 | E21054 (31,5 N 5,5 O) | 43,9 | 99,4 | 71,6 | 627 | M62517 (83,5 S 57,5 E, Wapowski a 18 km) | Nobile Rim 2 | 293,2 / 130,4 | -1,5 / -210,1 | 18,7 / 176,9 | 3,3 / 3,5 | 119,5 / 115,0 | 1.037,2 / 886,4 | 5,39 / 0,84 | tmin_c: 62,7 / 62,7; amp: 41,9 / 43,4 |
| 5 | E17187 (42,5 N 87,5 E) | 47,5 | 95,0 | 71,3 | 446 | M62523 (83,5 S 63,5 E, Oberbeck a 16 km) | Nobile Rim 2 | 281,9 / 89,6 | -18,4 / -226,2 | 18,2 / 174,6 | 4,7 / 6,2 | 173,5 / 161,6 | 1.311,3 / -995,4 | 4,25 / 0,31 | tmin_c: 23,2 / 22,3; amp: 34,9 / 37,7 |
| 6 | E42949 (29,5 S 70,5 O) | 49,1 | 93,4 | 71,2 | 404 | M62477 (83,5 S 17,5 E, Malapert a 49 km) | Mons Mouton Plateau | 288,0 / 135,1 | -2,5 / -212,1 | 21,9 / 191,6 | 7,6 / 8,3 | 263,9 / 261,3 | 1.908,6 / 1.591,2 | 5,78 / 0,69 | tmin_c: 59,8 / 55,9; amp: 79,2 / 75,2 |
| 7 | E16833 (43,5 N 93,5 E) | 47,5 | 94,8 | 71,1 | 317 | M63841 (87,5 S 58,5 O, Cartwright a 15 km) | de Gerlache Rim 2 | 279,1 / 98,7 | -20,2 / -227,0 | 17,6 / 172,6 | 4,3 / 4,2 | 148,8 / 128,2 | 1.392,9 / -1.254,7 | 4,39 / 0,17 | tmin_c: 17,4 / 18,8; amp: 28,8 / 32,5 |
| 8 | E18254 (39,5 N 74,5 E) | 49,6 | 92,3 | 71,0 | 77 | M63875 (87,5 S 24,5 O, Haworth a 26 km) | Haworth | 275,9 / 113,8 | -20,9 / -226,5 | 17,3 / 170,2 | 6,7 / 7,2 | 237,7 / 231,2 | 2.838,5 / 550,1 | 4,16 / 0,23 | tmin_c: 15,5 / 20,9; amp: 25,3 / 28,4 |
| 9 | E18627 (38,5 N 87,5 E) | 57,8 | 84,0 | 70,9 | 128 | M62479 (83,5 S 19,5 E, Mons Mouton a 49 km) | Mons Mouton Plateau | 286,2 / 123,3 | -16,8 / -219,8 | 22,1 / 193,9 | 3,2 / 5,3 | 146,3 / 172,7 | 1.169,2 / 1.394,5 | 4,64 / 0,54 | tmin_c: 27,8 / 34,1; amp: 80,1 / 77,7 |
| 10 | E21412 (30,5 N 7,5 O) | 44,2 | 97,6 | 70,9 | 664 | M62516 (83,5 S 56,5 E, Wapowski a 16 km) | Nobile Rim 2 | 294,5 / 133,4 | 0,3 / -209,1 | 19,3 / 178,5 | 2,6 / 3,5 | 94,2 / 109,0 | 871,9 / 886,5 | 5,43 / 0,94 | tmin_c: 68,6 / 69,8; amp: 49,6 / 48,8 |

D4a, regiones:

| # | Tierra | idon. | sim. | final | puesto hoy | gemelo | región NASA | T media (K) | T mín (°C) | amplitud (K) | pendiente (°) | rugosidad (m) | elev. rel. (m) | irradiancia | posición relativa T / L (unidad del diseño) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E18254 (39,5 N 74,5 E) | 49,6 | 98,9 | 74,3 | 77 | M64020 (87,5 S 120,5 E, Slater a 21 km) | Slater Plain | 275,9 / 88,1 | -20,9 / -231,9 | 17,3 / 166,8 | 6,7 / 7,3 | 237,7 / 231,8 | 2.838,5 / -495,0 | 4,16 / 0,12 | temp_k: 9,0 / 9,5; amp: 25,3 / 23,8 |
| 2 | E40794 (23,5 S 65,5 O) | 49,6 | 97,2 | 73,4 | 208 | M62479 (83,5 S 19,5 E, Mons Mouton a 49 km) | Mons Mouton Plateau | 287,7 / 123,3 | -4,1 / -219,8 | 21,6 / 193,9 | 5,4 / 5,3 | 191,3 / 172,7 | 2.684,6 / 1.394,5 | 5,27 / 0,54 | temp_k: 46,1 / 44,1; amp: 76,6 / 77,7 |
| 3 | E18627 (38,5 N 87,5 E) | 57,8 | 88,5 | 73,2 | 128 | M62479 (83,5 S 19,5 E, Mons Mouton a 49 km) | Mons Mouton Plateau | 286,2 / 123,3 | -16,8 / -219,8 | 22,1 / 193,9 | 3,2 / 5,3 | 146,3 / 172,7 | 1.169,2 / 1.394,5 | 4,64 / 0,54 | temp_k: 40,3 / 44,1; amp: 80,1 / 77,7 |
| 4 | E42591 (28,5 S 68,5 O) | 52,4 | 93,7 | 73,1 | 411 | M62479 (83,5 S 19,5 E, Mons Mouton a 49 km) | Mons Mouton Plateau | 287,0 / 123,3 | -3,3 / -219,8 | 22,2 / 193,9 | 4,5 / 5,3 | 143,6 / 172,7 | 2.460,7 / 1.394,5 | 5,62 / 0,54 | temp_k: 43,6 / 44,1; amp: 80,6 / 77,7 |
| 5 | E17538 (41,5 N 78,5 E) | 47,3 | 98,0 | 72,6 | 67 | M63867 (87,5 S 32,5 O, Cartwright a 19 km) | Haworth | 272,1 / 77,7 | -24,5 / -233,8 | 15,6 / 146,5 | 6,7 / 7,1 | 238,8 / 225,2 | 2.807,0 / -344,1 | 4,09 / 0,07 | temp_k: 2,7 / 4,5; amp: 6,7 / 5,9 |
| 6 | E16834 (43,5 N 94,5 E) | 54,1 | 91,1 | 72,6 | 117 | M62134 (82,5 S 34,5 E, Scott a 56 km) | Mons Mouton Plateau | 283,1 / 114,3 | -19,4 / -213,9 | 19,6 / 179,2 | 3,2 / 4,1 | 109,3 / 130,8 | 942,2 / -1.002,4 | 4,50 / 0,70 | temp_k: 29,1 / 34,5; amp: 53,8 / 52,3 |
| 7 | E15750 (46,5 N 90,5 E) | 45,2 | 98,7 | 71,9 | 175 | M63834 (87,5 S 65,5 O, Cartwright a 24 km) | de Gerlache Rim 2 | 276,6 / 91,5 | -25,2 / -224,4 | 15,5 / 146,1 | 3,1 / 3,8 | 112,3 / 116,6 | 920,0 / -1.620,0 | 4,09 / 0,20 | temp_k: 10,9 / 12,7; amp: 5,9 / 5,5 |
| 8 | E15751 (46,5 N 91,5 E) | 46,6 | 97,0 | 71,8 | 246 | M64018 (87,5 S 118,5 E, Slater a 19 km) | Slater Plain | 273,8 / 79,7 | -25,9 / -232,5 | 16,0 / 153,3 | 4,7 / 6,3 | 164,1 / 167,9 | 1.565,1 / -571,8 | 4,01 / 0,09 | temp_k: 5,4 / 5,5; amp: 11,6 / 10,5 |
| 9 | E17897 (40,5 N 77,5 E) | 49,8 | 93,7 | 71,7 | 283 | M63841 (87,5 S 58,5 O, Cartwright a 15 km) | de Gerlache Rim 2 | 280,4 / 98,7 | -17,6 / -227,0 | 18,0 / 172,6 | 4,2 / 4,2 | 158,2 / 128,2 | 1.849,9 / -1.254,7 | 4,28 / 0,17 | temp_k: 20,8 / 17,3; amp: 33,1 / 32,5 |
| 10 | E41513 (25,5 S 66,5 O) | 54,5 | 88,5 | 71,5 | 123 | M62479 (83,5 S 19,5 E, Mons Mouton a 49 km) | Mons Mouton Plateau | 287,1 / 123,3 | -4,4 / -219,8 | 23,0 / 193,9 | 5,3 / 5,3 | 173,8 / 172,7 | 2.883,8 / 1.394,5 | 5,52 / 0,54 | temp_k: 43,7 / 44,1; amp: 85,9 / 77,7 |

D4c, regiones:

| # | Tierra | idon. | sim. | final | puesto hoy | gemelo | región NASA | T media (K) | T mín (°C) | amplitud (K) | pendiente (°) | rugosidad (m) | elev. rel. (m) | irradiancia | posición relativa T / L (unidad del diseño) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E17538 (41,5 N 78,5 E) | 47,3 | 97,5 | 72,4 | 67 | M63528 (86,5 S 11,5 O, Mons Malapert a 25 km) | Haworth | 272,1 / 77,5 | -24,5 / -231,9 | 15,6 / 153,3 | 6,7 / 7,2 | 238,8 / 238,5 | 2.807,0 / 680,7 | 4,09 / 0,10 | amp: 6,7 / 10,2; tmin_c: 8,4 / 8,0; temp_k: 2,7 / 3,8 |
| 2 | E15751 (46,5 N 91,5 E) | 46,6 | 96,9 | 71,8 | 246 | M64018 (87,5 S 118,5 E, Slater a 19 km) | Slater Plain | 273,8 / 79,7 | -25,9 / -232,5 | 16,0 / 153,3 | 4,7 / 6,3 | 164,1 / 167,9 | 1.565,1 / -571,8 | 4,01 / 0,09 | amp: 11,6 / 10,5; tmin_c: 5,8 / 6,6; temp_k: 5,4 / 5,5 |
| 3 | E18627 (38,5 N 87,5 E) | 57,8 | 85,5 | 71,7 | 128 | M62479 (83,5 S 19,5 E, Mons Mouton a 49 km) | Mons Mouton Plateau | 286,2 / 123,3 | -16,8 / -219,8 | 22,1 / 193,9 | 3,2 / 5,3 | 146,3 / 172,7 | 1.169,2 / 1.394,5 | 4,64 / 0,54 | amp: 80,1 / 77,7; tmin_c: 27,8 / 34,1; temp_k: 40,3 / 44,1 |
| 4 | E18254 (39,5 N 74,5 E) | 49,6 | 93,3 | 71,5 | 77 | M64020 (87,5 S 120,5 E, Slater a 21 km) | Slater Plain | 275,9 / 88,1 | -20,9 / -231,9 | 17,3 / 166,8 | 6,7 / 7,3 | 237,7 / 231,8 | 2.838,5 / -495,0 | 4,16 / 0,12 | amp: 25,3 / 23,8; tmin_c: 15,5 / 8,4; temp_k: 9,0 / 9,5 |
| 5 | E16833 (43,5 N 93,5 E) | 47,5 | 95,3 | 71,4 | 317 | M63841 (87,5 S 58,5 O, Cartwright a 15 km) | de Gerlache Rim 2 | 279,1 / 98,7 | -20,2 / -227,0 | 17,6 / 172,6 | 4,3 / 4,2 | 148,8 / 128,2 | 1.392,9 / -1.254,7 | 4,39 / 0,17 | amp: 28,8 / 32,5; tmin_c: 17,4 / 18,8; temp_k: 17,2 / 17,3 |
| 6 | E17897 (40,5 N 77,5 E) | 49,8 | 90,3 | 70,1 | 283 | M63841 (87,5 S 58,5 O, Cartwright a 15 km) | de Gerlache Rim 2 | 280,4 / 98,7 | -17,6 / -227,0 | 18,0 / 172,6 | 4,2 / 4,2 | 158,2 / 128,2 | 1.849,9 / -1.254,7 | 4,28 / 0,17 | amp: 33,1 / 32,5; tmin_c: 25,1 / 18,8; temp_k: 20,8 / 17,3 |
| 7 | E21833 (29,5 N 53,5 E) | 46,4 | 92,7 | 69,5 | 611 | M62515 (83,5 S 55,5 E, Wapowski a 14 km) | Nobile Rim 2 | 294,3 / 138,1 | -1,5 / -209,7 | 20,0 / 181,0 | 3,7 / 5,1 | 138,8 / 123,7 | 1.137,3 / 849,5 | 5,44 / 0,92 | amp: 59,5 / 54,8; tmin_c: 62,9 / 64,1; temp_k: 70,3 / 72,3 |
| 8 | E15750 (46,5 N 90,5 E) | 45,2 | 93,6 | 69,4 | 175 | M63843 (87,5 S 56,5 O, Cartwright a 13 km) | de Gerlache Rim 2 | 276,6 / 81,2 | -25,2 / -232,0 | 15,5 / 152,1 | 3,1 / 4,1 | 112,3 / 131,7 | 920,0 / -1.325,2 | 4,09 / 0,12 | amp: 5,9 / 8,8; tmin_c: 7,4 / 7,7; temp_k: 10,9 / 6,2 |
| 9 | E19672 (35,5 N 52,5 E) | 45,3 | 93,1 | 69,2 | 659 | M63657 (86,5 S 117,5 E, Slater a 49 km) | Slater Plain | 289,0 / 127,4 | -5,2 / -212,6 | 19,7 / 178,9 | 4,2 / 5,5 | 163,1 / 177,5 | 1.130,6 / -1.664,3 | 4,80 / 0,47 | amp: 55,1 / 51,2; tmin_c: 53,0 / 54,8; temp_k: 50,9 / 48,0 |
| 10 | E16830 (43,5 N 90,5 E) | 48,0 | 90,1 | 69,0 | 207 | M63841 (87,5 S 58,5 O, Cartwright a 15 km) | de Gerlache Rim 2 | 282,4 / 98,7 | -18,9 / -227,0 | 18,0 / 172,6 | 3,1 / 4,2 | 118,6 / 128,2 | 888,3 / -1.254,7 | 4,37 / 0,17 | amp: 33,1 / 32,5; tmin_c: 21,5 / 18,8; temp_k: 26,7 / 17,3 |

D4d, regiones:

| # | Tierra | idon. | sim. | final | puesto hoy | gemelo | región NASA | T media (K) | T mín (°C) | amplitud (K) | pendiente (°) | rugosidad (m) | elev. rel. (m) | irradiancia | posición relativa T / L (unidad del diseño) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E41150 (24,5 S 69,5 O) | 73,7 | 99,9 | 86,8 | 41 | M62501 (83,5 S 41,5 E, Floss a 24 km) | Mons Mouton Plateau | 296,0 / 159,6 | 2,6 / -207,6 | 34,4 / 233,6 | 2,4 / 14,2 | 76,8 / 387,6 | 1.509,8 / 2.136,4 | 5,99 / 1,00 | tmin_c: 78,1 / 78,8; amp: 99,9 / 99,8 |
| 2 | E40431 (22,5 S 68,5 O) | 75,5 | 97,2 | 86,3 | 23 | M62390 (83,5 S 69,5 O, Ibn Bajja a 86 km) | Peak Near Cabeus B | 292,9 / 150,5 | -4,0 / -212,6 | 33,7 / 219,5 | 2,8 / 16,7 | 94,6 / 442,6 | 2.411,0 / 2.417,2 | 5,97 / 0,82 | tmin_c: 55,6 / 53,8; amp: 99,8 / 97,0 |
| 3 | E41151 (24,5 S 68,5 O) | 74,1 | 98,2 | 86,2 | 21 | M62390 (83,5 S 69,5 O, Ibn Bajja a 86 km) | Peak Near Cabeus B | 287,5 / 150,5 | -5,1 / -212,6 | 32,9 / 219,5 | 4,3 / 16,7 | 142,5 / 442,6 | 3.134,8 / 2.417,2 | 5,88 / 0,82 | tmin_c: 53,2 / 53,8; amp: 99,6 / 97,0 |
| 4 | E40790 (23,5 S 69,5 O) | 74,2 | 97,6 | 85,9 | 38 | M63184 (85,5 S 4,5 E, Lhamu a 19 km) | Malapert Massif | 298,8 / 145,4 | 3,9 / -203,6 | 35,3 / 222,2 | 2,2 / 16,1 | 67,8 / 484,4 | 981,5 / 1.328,2 | 6,05 / 0,52 | tmin_c: 86,6 / 88,8; amp: 99,9 / 97,7 |
| 5 | E40430 (22,5 S 69,5 O) | 74,3 | 96,5 | 85,4 | 72 | M62490 (83,5 S 30,5 E, Mons Mouton a 33 km) | Mons Mouton Plateau | 299,7 / 151,6 | 3,8 / -204,2 | 35,7 / 218,1 | 1,6 / 11,8 | 50,8 / 328,8 | 957,1 / 1.857,0 | 6,03 / 0,82 | tmin_c: 85,6 / 87,3; amp: 100,0 / 96,6 |
| 6 | E39710 (20,5 S 69,5 O) | 71,0 | 99,5 | 85,2 | 70 | M62500 (83,5 S 40,5 E, Floss a 24 km) | Mons Mouton Plateau | 299,4 / 159,2 | 4,8 / -200,9 | 33,8 / 226,7 | 2,4 / 14,5 | 84,3 / 405,8 | 899,9 / 2.514,3 | 5,86 / 0,94 | tmin_c: 97,0 / 96,6; amp: 99,8 / 98,4 |
| 7 | E41510 (25,5 S 69,5 O) | 71,5 | 97,9 | 84,7 | 51 | M62393 (83,5 S 66,5 O, Ibn Bajja a 88 km) | Peak Near Cabeus B | 292,6 / 150,7 | 1,4 / -209,0 | 33,0 / 227,5 | 2,6 / 20,7 | 80,7 / 536,1 | 2.090,6 / 1.994,8 | 5,92 / 0,84 | tmin_c: 72,9 / 70,2; amp: 99,7 / 98,8 |
| 8 | E41152 (24,5 S 67,5 O) | 69,8 | 98,0 | 83,9 | 53 | M62390 (83,5 S 69,5 O, Ibn Bajja a 86 km) | Peak Near Cabeus B | 287,5 / 150,5 | -5,8 / -212,6 | 30,8 / 219,5 | 3,3 / 16,7 | 126,6 / 442,6 | 3.161,8 / 2.417,2 | 5,63 / 0,82 | tmin_c: 52,0 / 53,8; amp: 99,2 / 97,0 |
| 9 | E41512 (25,5 S 67,5 O) | 72,1 | 95,3 | 83,7 | 35 | M62390 (83,5 S 69,5 O, Ibn Bajja a 86 km) | Peak Near Cabeus B | 285,9 / 150,5 | -6,6 / -212,6 | 31,5 / 219,5 | 4,4 / 16,7 | 138,8 / 442,6 | 3.465,0 / 2.417,2 | 5,81 / 0,82 | tmin_c: 50,1 / 53,8; amp: 99,4 / 97,0 |
| 10 | E39350 (19,5 S 69,5 O) | 67,0 | 99,1 | 83,1 | 79 | M62393 (83,5 S 66,5 O, Ibn Bajja a 88 km) | Peak Near Cabeus B | 295,7 / 150,7 | 1,2 / -209,0 | 30,9 / 227,5 | 3,4 / 20,7 | 119,0 / 536,1 | 1.727,2 / 1.994,8 | 5,71 / 0,84 | tmin_c: 72,0 / 70,2; amp: 99,3 / 98,8 |

D4b, polo sur (solo comparación):

| # | Tierra | idon. | sim. | final | puesto hoy | gemelo | región NASA | T media (K) | T mín (°C) | amplitud (K) | pendiente (°) | rugosidad (m) | elev. rel. (m) | irradiancia | posición relativa T / L (unidad del diseño) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E40071 (21,5 S 68,5 O) | 73,7 | 96,5 | 85,1 | 11 | M59924 (76,5 S 15,5 O, Newton a 14 km) | — | 287,9 / 130,0 | -8,4 / -214,5 | 32,6 / 223,7 | 4,5 / 5,2 | 150,4 / 175,1 | 3.286,1 / -2.968,8 | 5,74 / 1,28 | tmin_c: 45,1 / 45,3; amp: 99,6 / 99,0 |
| 2 | E40431 (22,5 S 68,5 O) | 75,5 | 93,1 | 84,3 | 23 | M60527 (78,5 S 132,5 O, Zeeman a 106 km) | — | 292,9 / 141,9 | -4,0 / -211,0 | 33,7 / 213,5 | 2,8 / 3,2 | 94,6 / 99,0 | 2.411,0 / -1.815,4 | 5,97 / 1,66 | tmin_c: 55,6 / 58,5; amp: 99,8 / 94,6 |
| 3 | E41871 (26,5 S 68,5 O) | 69,6 | 98,2 | 83,9 | 9 | M59924 (76,5 S 15,5 O, Newton a 14 km) | — | 280,6 / 130,0 | -7,5 / -214,5 | 31,6 / 223,7 | 5,0 / 5,2 | 162,4 / 175,1 | 3.861,6 / -2.968,8 | 5,75 / 1,28 | tmin_c: 47,3 / 45,3; amp: 99,4 / 99,0 |
| 4 | E41151 (24,5 S 68,5 O) | 74,1 | 93,5 | 83,8 | 21 | M62189 (82,5 S 89,5 E, Hedervari a 27 km) | — | 287,5 / 141,3 | -5,1 / -213,1 | 32,9 / 217,3 | 4,3 / 4,8 | 142,5 / 168,8 | 3.134,8 / -538,1 | 5,88 / 1,01 | tmin_c: 53,2 / 50,3; amp: 99,6 / 97,1 |
| 5 | E41512 (25,5 S 67,5 O) | 72,1 | 94,8 | 83,5 | 35 | M62189 (82,5 S 89,5 E, Hedervari a 27 km) | — | 285,9 / 141,3 | -6,6 / -213,1 | 31,5 / 217,3 | 4,4 / 4,8 | 138,8 / 168,8 | 3.465,0 / -538,1 | 5,81 / 1,01 | tmin_c: 50,1 / 50,3; amp: 99,4 / 97,1 |
| 6 | E41153 (24,5 S 66,5 O) | 66,1 | 99,2 | 82,6 | 18 | M59924 (76,5 S 15,5 O, Newton a 14 km) | — | 285,2 / 130,0 | -7,7 / -214,5 | 28,3 / 223,7 | 5,0 / 5,2 | 170,3 / 175,1 | 3.481,1 / -2.968,8 | 5,60 / 1,28 | tmin_c: 47,0 / 45,3; amp: 98,6 / 99,0 |
| 7 | E40432 (22,5 S 67,5 O) | 77,0 | 87,6 | 82,3 | 32 | M62187 (82,5 S 87,5 E, Hedervari a 23 km) | — | 282,7 / 139,2 | -11,3 / -217,3 | 33,4 / 223,9 | 3,8 / 5,9 | 128,9 / 171,3 | 3.990,6 / -459,3 | 5,59 / 0,95 | tmin_c: 40,2 / 37,2; amp: 99,7 / 99,1 |
| 8 | E41511 (25,5 S 68,5 O) | 67,1 | 97,0 | 82,1 | 34 | M62189 (82,5 S 89,5 E, Hedervari a 27 km) | — | 284,2 / 141,3 | -6,1 / -213,1 | 34,7 / 217,3 | 4,6 / 4,8 | 152,8 / 168,8 | 3.534,0 / -538,1 | 5,83 / 1,01 | tmin_c: 51,0 / 50,3; amp: 99,9 / 97,1 |
| 9 | E40792 (23,5 S 67,5 O) | 73,5 | 90,3 | 81,9 | 48 | M59924 (76,5 S 15,5 O, Newton a 14 km) | — | 284,8 / 130,0 | -8,6 / -214,5 | 31,9 / 223,7 | 3,7 / 5,2 | 127,3 / 175,1 | 3.579,7 / -2.968,8 | 5,75 / 1,28 | tmin_c: 44,7 / 45,3; amp: 99,5 / 99,0 |
| 10 | E42231 (27,5 S 68,5 O) | 64,4 | 99,2 | 81,8 | 22 | M59924 (76,5 S 15,5 O, Newton a 14 km) | — | 279,3 / 130,0 | -8,2 / -214,5 | 27,1 / 223,7 | 5,3 / 5,2 | 168,4 / 175,1 | 3.880,8 / -2.968,8 | 5,68 / 1,28 | tmin_c: 46,0 / 45,3; amp: 97,5 / 99,0 |

## 6. D5 (propio). Un índice de severidad térmica en percentil

**Qué mide exactamente:** en cada población (candidatos; celdas de las regiones), `sev = percentil dentro de la población de (percentil de amplitud + (100 − percentil de mínima)) / 2`: el puesto del sitio en una escala que sube con la amplitud y con el frío de la mínima. Clave `sev` peso 80, τ 10 puntos; pendiente 10 y rugosidad 10 como en D4.

Resultado en las regiones: **971 pares** (×0,5: 833; ×2: 1.104; sin filtro de terreno, los 2.419), 98 gemelos, el primero (M62846, Mons Mouton a 13 km) con 149 (15,3 %), los tres primeros con el 30,7 %; similitud 54,3 / 75,4 / 91,8 / 98,6 / 99,9; Spearman −0,16. Conserva a 4 de los 10 primeros de hoy (E41871 en el puesto 6, E19699 en el 9, E19698 en el 20 y E18986 en el 30) y a 191 del cuartil superior de idoneidad (D4b: 27). Diferencia real: temperatura media 169,8 / 194,4 K; mínima 213,6 / 223,8 K; amplitud 153,0 / 161,8 K; pendiente 1,6 / 2,6°; rugosidad 26,2 / 55,0 m.

**Por qué no lo recomiendo:** cumple P2 sobre una variable inventada, no sobre las dos de la misión. Dentro de los pares, la diferencia de percentil de cada variable es grande: mínima 22,8 / 45,3 puntos (mediana / P90) y amplitud 19,8 / 48,8 (D4b: 3,2 / 7,7 y 3,0 / 7,7). Un sitio de amplitud muy alta puede emparejarse con una celda muy fría y de poca amplitud porque las dos "suman" lo mismo. Y concentra más (15,3 %). Además, sus cifras dependen del redondeo: la suma de dos percentiles da empates que el redondeo de coma flotante rompe de una forma u otra. Según cómo se escriba la suma salen de 970 a 973 pares y de 98 a 100 gemelos (ver "Comprobación").

| # | Tierra | idon. | sim. | final | puesto hoy | gemelo | región NASA | T media (K) | T mín (°C) | amplitud (K) | pendiente (°) | rugosidad (m) | elev. rel. (m) | irradiancia | posición relativa T / L (unidad del diseño) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E40071 (21,5 S 68,5 O) | 73,7 | 98,3 | 86,0 | 11 | M63837 (87,5 S 62,5 O, Cartwright a 20 km) | de Gerlache Rim 2 | 287,9 / 105,7 | -8,4 / -219,7 | 32,6 / 180,1 | 4,5 / 5,5 | 150,4 / 147,2 | 3.286,1 / -1.461,0 | 5,74 / 0,23 |  |
| 2 | E40432 (22,5 S 67,5 O) | 77,0 | 94,2 | 85,6 | 32 | M63837 (87,5 S 62,5 O, Cartwright a 20 km) | de Gerlache Rim 2 | 282,7 / 105,7 | -11,3 / -219,7 | 33,4 / 180,1 | 3,8 / 5,5 | 128,9 / 147,2 | 3.990,6 / -1.461,0 | 5,59 / 0,23 |  |
| 3 | E40792 (23,5 S 67,5 O) | 73,5 | 94,4 | 84,0 | 48 | M63837 (87,5 S 62,5 O, Cartwright a 20 km) | de Gerlache Rim 2 | 284,8 / 105,7 | -8,6 / -219,7 | 31,9 / 180,1 | 3,7 / 5,5 | 127,3 / 147,2 | 3.579,7 / -1.461,0 | 5,75 / 0,23 |  |
| 4 | E41151 (24,5 S 68,5 O) | 74,1 | 93,7 | 83,9 | 21 | M62523 (83,5 S 63,5 E, Oberbeck a 16 km) | Nobile Rim 2 | 287,5 / 89,6 | -5,1 / -226,2 | 32,9 / 174,6 | 4,3 / 6,2 | 142,5 / 161,6 | 3.134,8 / -995,4 | 5,88 / 0,31 |  |
| 5 | E41512 (25,5 S 67,5 O) | 72,1 | 95,5 | 83,8 | 35 | M63837 (87,5 S 62,5 O, Cartwright a 20 km) | de Gerlache Rim 2 | 285,9 / 105,7 | -6,6 / -219,7 | 31,5 / 180,1 | 4,4 / 5,5 | 138,8 / 147,2 | 3.465,0 / -1.461,0 | 5,81 / 0,23 |  |
| 6 | E41871 (26,5 S 68,5 O) | 69,6 | 97,4 | 83,5 | 9 | M63837 (87,5 S 62,5 O, Cartwright a 20 km) | de Gerlache Rim 2 | 280,6 / 105,7 | -7,5 / -219,7 | 31,6 / 180,1 | 5,0 / 5,5 | 162,4 / 147,2 | 3.861,6 / -1.461,0 | 5,75 / 0,23 |  |
| 7 | E40431 (22,5 S 68,5 O) | 75,5 | 88,7 | 82,1 | 23 | M63841 (87,5 S 58,5 O, Cartwright a 15 km) | de Gerlache Rim 2 | 292,9 / 98,7 | -4,0 / -227,0 | 33,7 / 172,6 | 2,8 / 4,2 | 94,6 / 128,2 | 2.411,0 / -1.254,7 | 5,97 / 0,17 |  |
| 8 | E38990 (18,5 S 69,5 O) | 66,8 | 97,4 | 82,1 | 45 | M62523 (83,5 S 63,5 E, Oberbeck a 16 km) | Nobile Rim 2 | 289,7 / 89,6 | -4,1 / -226,2 | 30,0 / 174,6 | 4,7 / 6,2 | 158,9 / 161,6 | 2.815,7 / -995,4 | 5,41 / 0,31 |  |
| 9 | E19699 (35,5 N 79,5 E) | 67,4 | 96,8 | 82,1 | 3 | M62479 (83,5 S 19,5 E, Mons Mouton a 49 km) | Mons Mouton Plateau | 271,8 / 123,3 | -27,9 / -219,8 | 26,5 / 193,9 | 4,4 / 5,3 | 174,8 / 172,7 | 4.500,2 / 1.394,5 | 4,31 / 0,54 |  |
| 10 | E41153 (24,5 S 66,5 O) | 66,1 | 97,1 | 81,6 | 18 | M63821 (87,5 S 78,5 O, Lacus Tenebrarum a 28 km) | de Gerlache Rim 2 | 285,2 / 118,9 | -7,7 / -217,8 | 28,3 / 185,6 | 5,0 / 4,9 | 170,3 / 175,9 | 3.481,1 / -1.185,0 | 5,60 / 0,29 |  |

## 7. Qué cambiaría en el motor y en los pares de hoy (D4b)

**Hoy** (`engine/repo_similarity.py`, `zone_twin`): z por cuerpo (Tierra firme / Luna entera) de pendiente, rugosidad, elevación relativa y temperatura media con pesos 33,3 / 26,7 / 20 / 20 %, `similitud = 100 × exp(−0,45 × d)` con `d = √(Σ w Δz²)`, sin filtro, gemelo entre las 280 celdas. No entra la amplitud.

**Con D4b, solo para `lunar_base`:**

1. Variables clave nuevas: `tmin_c` y `lst_diurnal_amp_k`, en percentil de rango medio **dentro de los puntos que pasan el embudo** (Tierra) y **dentro de las celdas de la zona** (Luna). El percentil de la Tierra se calcula después del embudo, así que depende de él: si cambia un filtro duro, cambian los puestos.
2. Pendiente (`slope_iso_deg`) y rugosidad en valor real.
3. Similitud gaussiana con pesos 40 / 40 / 10 / 10 y τ 10 puntos, 10 puntos, 2°, 30 m (la función que propone `ANALOG_PRINCIPLE.md` §C con una normalización distinta para las dos claves).
4. Filtro: las dos claves a ≤ 10 puntos, pendiente ≤ 4°, rugosidad ≤ 60 m. Sin celda que lo cumpla, el punto no tiene par y no se enseña (sigue en el embudo con su idoneidad).
5. Salen de la similitud la temperatura media y la elevación relativa (se enseñan como diferencia). Final = 0,5 × similitud + 0,5 × idoneidad, igual que hoy.

**Cómo cambian los pares:**

| | hoy | D4b |
|---|---|---|
| puntos con gemelo | 2.419 | 450 (pierden el par 1.969) |
| gemelos que cambian | — | los 450 (ninguno conserva el de hoy) |
| gemelos distintos | 48 | 103 |
| gemelo más compartido | M62515 (Wapowski, Nobile Rim 2), 671 (27,7 %) | M62848 (Mons Mouton Plateau), 25 (5,6 %) |
| tres más compartidos | 54,1 % | 15,3 % |
| número 1 | E19345 (36,5 N 85,5 E) – M62859 (Floss, Mons Mouton Plateau); final 76,7 | E17538 (41,5 N 78,5 E) – M63528 (Haworth); final 72,3 (hoy puesto 67) |
| top 10 de hoy | — | los 10 sin par; de los 100 primeros de hoy conservan par 3 |
| top 10 nuevo, puesto de hoy | — | 67, 207, 246, 627, 446, 404, 317, 77, 128, 664 |
| Spearman del final con el de hoy (supervivientes) | — | 0,69 |
| Spearman similitud-idoneidad | +0,04 | −0,02 |
| dif. real T media (mediana / P90) | 142,3 / 160,8 K | 162,7 / 181,2 K |
| dif. real amplitud | 164,5 / 191,1 K | 153,8 / 161,3 K |
| dif. real mínima | 198,7 / 213,3 K | 207,9 / 210,6 K |
| dif. real pendiente | 6,57 / 10,87° | 1,51 / 2,69° |
| dif. real rugosidad | 171,7 / 276,1 m | 27,3 / 54,4 m |
| dif. real elevación relativa | 845 / 1.759 m | 2.497 / 4.654 m |
| dif. real irradiancia | 4,03 / 5,05 kWh/m²/día | 4,08 / 4,63 kWh/m²/día |

Por qué pierden el par los diez primeros de hoy: todos tienen alguna celda de las regiones dentro del filtro de terreno (entre 1 y 103), pero ninguna dentro del filtro térmico salvo E41871 (2 celdas, ninguna con terreno compatible). Son los candidatos de mínima más fría (percentil 1,8-9,9) y amplitud alta (81-98); E41871 (26,5 S 68,5 O), mínima en el percentil 47 y amplitud en el 99.

**Texto que habría que retirar o cambiar:** la frase de concentración de la decisión 4 (`DECISIONS.md` §8: "shared by N Earth points… a few gentle cells…") sigue valiendo en forma, pero con 103 gemelos y un 5,6 % máximo; el párrafo de `ASSUMPTIONS.md` §0.7 sobre los 48 gemelos y el 54,1 % quedaría obsoleto.

## 8. Lo que este documento no demuestra

- Que un sitio de la Tierra reproduzca el ambiente térmico lunar: no lo hace en ningún diseño (al menos 158 K de diferencia mediana de temperatura media en las regiones; 158,5 K en D3z). Los diseños con pares comparan puestos, no condiciones.
- Que las dos definiciones de amplitud y de mínima sean comparables: en la Tierra la amplitud es LST 10:30 − 22:30 (la subestima) y la mínima es del aire en el mes más frío (WorldClim, modelada); en la Luna son de la superficie (máximo − mínimo del ciclo). En percentil esto pesa menos, pero no desaparece.
- Que los resultados sean estables frente al embudo: el percentil de la Tierra se calcula sobre los 2.419 candidatos; con otro embudo, otros puestos.
- La elevación relativa usa la definición centrada de `ANALOG_PRINCIPLE.md`; la del motor (`elevation_rel_m` = `elevation_m`) cambia solo esa fila de diferencias, no los pares de D4b (no entra).
- Los nombres de lugar de la Tierra son aproximaciones por latitud y longitud; los lunares son el rasgo IAU más cercano del paquete publicado.
- No se ha ejecutado el motor ni se ha mirado la web. Un segundo agente ha comprobado las cifras con código propio: ver "Comprobación".

## Comprobación

Comprobación independiente hecha el 15-11-2026 por un segundo agente. Su código no importa nada de `lunarbase/` ni de `principle-check/ctx.py`: tiene su propio lector del paquete `app/public/data/v2` y su propio embudo, que lee `mission_scoring.json`. Scripts y salidas en `scratchpad/stars/lunarbase-check/`: `chk.py` reproduce todos los diseños y las tres zonas; `det.py` da el detalle de D4b; `d5b.py`, `ex.py` y `ex2.py` comprueban los demás datos. Las salidas están en `res.json`, `det.out` y `pairs_*.csv`. Hay una copia del documento antes de corregirlo en `LUNAR_BASE_PROPOSAL.before.md`.

**Qué se ha comprobado y coincide:**

- **Poblaciones.** El embudo `lunar_base`, aplicado de forma independiente, da 2.419 puntos: tierra firme (elevación ≥ 1 m, máscara ≥ 0,3), amplitud ≥ 15 K, mínima ≤ 5 °C, no agua y las tres variables presentes. Es exactamente el mismo conjunto que tiene gemelo en el paquete publicado. Las regiones suman 280 celdas (`cells["1"]["intersects"]`) y el polo sur 5.400. La tabla de la §1 coincide (mín / p5 / mediana / p95 / máx) y también los Spearman y las razones amplitud / temperatura media.
- **D4b tal como está escrito.** Percentil de rango medio `100·(rango − 0,5)/n`, con empates promediados, dentro de los 2.419 candidatos y dentro de las 280 celdas. Gaussiana 40/40/10/10 con τ de 10 puntos, 10 puntos, 2° y 30 m. Filtro en ±10, ±10, 4° y 60 m. El gemelo es la mejor celda que cumple el filtro (en empate, el id más bajo), y final = 0,5·sim + 0,5·idoneidad. Resultado: **450 pares, 103 gemelos distintos y M62848 con 25 (5,6 %)**; los tres primeros suman el 15,3 %. Número 1: E17538 – M63528, con similitud 97,3 y final 72,3. M63528 está en la región Haworth y a 25,1 km de Mons Malapert. El top 10 coincide en ids, gemelos, regiones, similitud, final, puesto de hoy y valores reales. Sensibilidad: 276 y 717 pares con las claves a ×0,5 y ×2; 128 y 1.669 con todas las tolerancias escaladas; 1.986 sin filtro de terreno.
- **Diferencias reales de D4b** (mediana / P90): temperatura media 162,70 / 181,19 K, mínima 207,88 / 210,55 K, amplitud 153,76 / 161,28 K, pendiente 1,51 / 2,69°, rugosidad 27,26 / 54,43 m, elevación relativa 2.497 / 4.654 m e irradiancia 4,08 / 4,63 kWh/m²/día. Con similitud ≥ 90 hay 176 pares. La diferencia de percentil es de 3,17 / 7,72 en mínima y 2,99 / 7,67 en amplitud.
- **Comparación con hoy.** Ningún gemelo se mantiene. Ninguno del top 10 de hoy conserva par, y del top 100 lo conservan 3. El top 10 nuevo ocupaba hoy los puestos 67, 207, 246, 627, 446, 404, 317, 77, 128 y 664. Spearman entre el final nuevo y el de hoy: 0,69. Spearman similitud-idoneidad: +0,04 hoy y −0,02 con D4b. Hoy hay 48 gemelos; el más compartido es M62515 con 671 y los tres primeros suman el 54,1 %. Las diferencias reales de hoy coinciden. Desglose de los 1.969 que pierden el par: 943, 237, 196 y 593. Rugosidad < 31 m: 1.139. Con alguna celda que cumple el terreno: 1.280. Celdas con amplitud ≥ p85 y mínima ≤ p30: 0. Del top 10 de hoy, ninguno tiene una celda que cumpla las dos condiciones a la vez, y E41871 tiene 2 celdas que cumplen la parte térmica. Idoneidad mediana: 30,9 en los que conservan par y 38,2 en todos; del cuartil superior conservan par 27.
- **Supervivientes de los demás diseños**, todos iguales a los del documento. Regiones: D1 0, D2 0, D3 2.186, D3z 2.270, D4a 457, D4c 338 y D4d 1.986. Las cifras ×0,5 y ×2, los gemelos distintos, la mayor cuota, el número 1, el Spearman y las diferencias reales también coinciden. Polo sur: D1 0, D2 0, D3 2.384, D3z 2.315, D4a 1.860, D4b 1.786, D4c 1.606 y D4d 2.374. Luna entera: D1 518, D2 1.287, D3 1.730, D3z 1.911, D4a 1.328, D4b 1.545, D4c 1.199 y D4d 1.905. En D1, la población de la Tierra es la de `normalize_planetary_features` (`elevation_m > 0`, 25.095 celdas, de las que 18.517 tienen temperatura). Las escalas también coinciden: 284,27 / 21,49 K, 197,70 / 32,29 K, 8,59 / 6,60 K y 265,56 / 47,84 K. Los rangos de z y de percentil de la tabla de la §2 coinciden.
- Lo que se dice de no llamar parecidas a las temperaturas y de no presentar la propuesta como decidida se cumple: el documento dice en la cabecera que la propuesta está pendiente de confirmación y no describe ningún valor térmico como parecido.

**Errores corregidos en este documento:**

1. **Frase de la web.** Decía "slope and roughness are within 0.5° and 0.3 m". La diferencia de pendiente del número 1 es de 0,53° (6,65 frente a 7,18°), así que no está "within 0.5°". Ahora dice "slope differs by 0.5° and roughness by 0.3 m", y la traducción se ha corregido igual. La mínima de la Tierra pasa de "−24 °C" a "−24.5 °C", su valor exacto. Las cifras de 195 K, −232 °C y 138 K están bien (194,6 K, −231,9 °C y 137,7 K). También se ha ordenado la sintaxis de la primera frase.
2. **Recomendación.** Decía que D4b era "el único diseño" con terreno parecido en valor real y con cada variable térmica en el mismo puesto. No es así: D4a, D4c y D5 también filtran el terreno en valor real, y D4c también exige que la mínima y la amplitud estén cada una a ≤ 10 puntos. Se ha reescrito para decir en qué se distingue D4b: tiene más pares que D4c (450 frente a 338) y usa solo las dos variables de la misión.
3. **Resumen.** El rango de la diferencia mediana de amplitud en los diseños con pares en las regiones era "153-159 K", pero D4c da 152,3 y D4a 152,8. Ahora dice "152-159 K".
4. **§8.** Decía "mínimo 160 K de diferencia mediana de temperatura media", pero D3z da 158,5 K. Ahora dice "al menos 158 K".
5. **§8.** Decía que la propuesta no la había comprobado un segundo agente. Se ha actualizado.

**Matiz añadido (D5):** el índice de severidad suma dos percentiles, y eso crea muchos empates exactos que la aritmética de coma flotante rompe según el orden de las operaciones. Con `(pA + (100 − pN))/2`, la forma del autor, salen 971 pares, 98 gemelos y 149 en el más compartido (15,3 %). Con `(pA + 100 − pN)/2` salen 970, 100 y 150 (15,5 %). Redondeando antes de ordenar salen 973 y 99. El número 1 (E40071 – M63837) y las diferencias reales (≈ 170 / 194 K y 214 / 224 K) apenas cambian. No afecta a la recomendación, pero si D5 se usara habría que fijar el redondeo. Las cifras del documento son las de la forma del autor, y se han reproducido: 971; 833 y 1.104; 98; 191 del cuartil superior; los puestos 6, 9, 20 y 30 para los cuatro del top 10 de hoy; y diferencias de percentil de 22,8 / 45,3 y 19,8 / 48,8.

**Qué no se ha comprobado:** la idoneidad y los pares de hoy se leen del paquete publicado y no se recalculan con el motor. Tampoco se han comprobado los nombres aproximados de lugares de la Tierra (Tian Shan, Atlas, etc.) ni las cifras de D1 y D2 en el polo sur salvo el número de supervivientes (0 con las tres tolerancias; los huecos de 1,45 z y 41,0 puntos no se han recalculado). No se ha ejecutado el motor ni se ha mirado la web.

## Implementación (15-11-2026)

Implementado tras la decisión de las 08:55 CET (motor 3.2.0, `tierra luna/engine/real_similarity.py` y `pipeline.py`, regla `percentile_and_real_tolerance`; variables, pesos, escalas, tolerancias, poblaciones y zona en `engine_config.json` `real_value_similarity.missions.lunar_base`). Paquete reconstruido en `app/public/data/v2` (contrato revisión 6).

**Unidades corregidas en este documento.** Las tablas y el texto escribían la diferencia de temperatura mínima en °C (por ejemplo 207,9 / 210,6 °C en D4b). Comprobado: las dos tablas guardan `tmin_c` en °C (la lunar es `tmin_k − 273,15`, igual hasta 6·10⁻¹⁴), así que la resta se hizo entre dos valores en °C y la cifra es correcta; solo estaba mal la unidad, porque una diferencia de temperatura vale lo mismo en K que en °C. Se han cambiado a K todas las diferencias (resumen, recomendación, secciones 2, 3, 4, 5, 6 y 7 y la comprobación). Los valores absolutos (la columna "T mín (°C)" de las tablas de pares, la tabla de poblaciones de la §1 y la frase de la web) siguen en °C, como permite la decisión. El paquete guarda la mínima en K en los dos lados (`tmin_k`, = `tmin_c` + 273,15).

**Cifras implementadas frente a las de este documento.** Coinciden: 450 pares de 2.419; 103 gemelos distintos; M62848 con 25 puntos (5,6 %); número 1 E17538 (41,5 N 78,5 E) con M63528 (86,5 S 11,5 O), similitud 97,31 y final 72,29 (72,3); sin gemelo 237 por posición térmica, 943 por terreno, 196 por las dos y 593 sin una celda que cumpla las dos; los 450 gemelos son, uno a uno, los de `lunarbase-check/pairs_D4b.csv`; diferencias reales (mediana / P90) 162,7 / 181,2 K, 207,9 / 210,6 K, 153,8 / 161,3 K, 1,51 / 2,69°, 27,3 / 54,4 m, 2.497 / 4.654 m; diferencia de percentil 3,17 / 7,72 y 2,99 / 7,67. Difiere solo el puesto de 56 de los 450 pares: el motor ordena por el final publicado (redondeado a 2 decimales, empates por id, como en Rover y Paneles solares) y el comprobador por el final sin redondear; el top 10 es el mismo.

**Frase de la web.** Se publica como plantilla por par (`similarity.json` `texts.lunar_base_pair_sentence`, rellenada por la web desde `earth_lunar_base_pairs.bin`), con la zona nombrada "NASA's nine candidate landing regions near the lunar south pole", sin número de misión, en lugar de "NASA's nine Artemis III candidate regions". El número 1 da exactamente la frase de arriba con esa zona (en `explain.json`, con el signo menos ASCII).

