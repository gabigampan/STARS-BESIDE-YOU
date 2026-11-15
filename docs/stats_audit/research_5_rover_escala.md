# Research 5: Rover, escala de medida y desaturación de la similitud

Script: `tierra luna/research/r5_scale.py` (determinista, 45 s). Salida: `tierra luna/research/out/r5_scale.json`. Todo en memoria sobre `tierra luna/audit/p5_common.py` con la regla Rover decidida (pendiente 0,5 + rugosidad 0,5, ambas clave, filtro 2 grados y 30 m, sin elevación relativa). Comprobación: el candidato A reproduce exactamente el motor de p5 (final publicado, gemelos y top 20 idénticos; 74 empatados en 100,00, como research_1). No se ha tocado motor, configuración, tablas, bundle, web ni audio.

## 1. La escala

Fuentes ya registradas (docs/stats_audit/3_robustez_validacion_ranking.md, F.3): ETOPO 2022, RMSE global 7,17 m (MacFerrin et al. 2025); LOLA, red geodésica a ~10 m radial (Smith et al. 2010; absoluta, pesimista). Bases (docs/REAL_DATA.md): un píxel = 1.853 m (Tierra, base de pendiente 3,706 km) y 1.895,2 m (Luna, 3,790 km); rugosidad = RMS de diferencias a un píxel.

Fórmulas (error vertical σz independiente entre píxeles vecinos):
* Pendiente, diferencia central g = (z+ − z−)/(2·dy): σg = √2·σz/(2·dy) = σz/(√2·dy); pendiente pequeña: σθ ≈ σg rad. Tierra 0,157°, Luna 0,214°. Diferencia Tierra−Luna: √(0,157² + 0,214²) = **0,265°**.
* Rugosidad, cada par Δz = z(x+L) − z(x): σΔz = √2·σz. Tierra 10,14 m, Luna 14,14 m. Diferencia: **17,40 m**.
* Efectos de nivel de ruido (no son la escala, pero acotan): una celda plana mide por ruido una pendiente media de σθ·√(π/2) = 0,20° (Tierra) y 0,27° (Luna) (sesgo de Rayleigh); a 30 m de rugosidad verdadera el ruido suma +1,7 m (Tierra) y +3,2 m (Luna) de sesgo.

Candidatas:

| Escala | Pendiente (°) | Rugosidad (m) | Qué supone |
|---|---|---|---|
| S1 por píxel | 0,265 | 17,40 | error de cada píxel, sin promediar |
| S2 por celda, errores independientes | 0,0136 (÷60 Tierra, ÷16 Luna) | 0,64 (÷√7200, ÷√512 pares) | 3.600 píxeles ETOPO y 256 LDEM_16 por celda, errores independientes |
| S3 dos definiciones de pendiente en las tablas | 1,46 (RMS |slope_deg − slope_iso_deg|: Luna zona 1,36, Tierra emparejada 0,55) | no hay segunda columna de la misma rugosidad | diferencia de definición (base este-oeste), no de medida |

Por qué no se confía en S2: las fuentes registradas no dan longitud de correlación del error (F.3 lo deja "no se puede establecer"); la etiqueta de LDEM_16 dice que se usó GMT `surface` "to compensate for incomplete coverage", es decir, parte de los píxeles lunares son interpolados y no medidas independientes; y S2 de rugosidad (0,64 m) es menor que el propio sesgo de ruido (1,7 y 3,2 m), así que es incoherente. Por qué S1 es la defendible: no supone independencia entre celdas ni promedia; es pesimista porque los 7,17 y 10 m son errores absolutos (una parte es desplazamiento común que no afecta a la pendiente ni a la rugosidad), pero esto solo se puede cuantificar con una correlación espacial que no tenemos. S3 no mide incertidumbre: se descarta como escala (solo indica que la definición importa más que el ruido).

## 2. La puntuación (filtro sin cambios: 2° y 30 m)

A: exp(−½(d/tol)²), tol 2° y 30 m. B: igual con σ en lugar de tol. C: exp(−½·max(0, d/σ − 1)²). Gemelo = máximo de la puntuación; empates de puntuación: menor Σ(d/σ)², luego menor índice. Emparejados: 10.337 en todos.

| Candidato | similitud p50 / p25 / p5 | ≥99 / ≥99,5 / ≥99,9 | muestran 100,00 | empatados en el máximo final | a 0,1 / 0,5 / 1 del 5.º | Spearman final–idoneidad |
|---|---|---|---|---|---|---|
| A (tol) | 99,9997 / 99,9985 / 99,9909 | 99,9 % / 99,2 % / … | 1.500 | 74 | 311 / 418 / 492 | 0,999 |
| B-S1 | 99,9962 / 99,9786 / 99,882 | … / 67,5 % / … | 131 | 5 | 122 / 380 / 467 | 0,989 |
| C-S1 | 100 / 100 / 100 | 100 % | 10.335 | 254 | 317 / 422 / 497 | 1,000 |
| B-S2 | 97,88 / 89,88 / 59,82 | … / 0,2 % / … | 0 | 1 | 5 / 7 / 10 | 0,677 |
| C-S2 | 100 / 100 / 96,18 | … / 17,5 % / … | 1.441 | 44 | 62 / 92 / 113 | 0,477 |

(Cuantiles completos y top 20 de cada candidato en el JSON, clave `candidates.*`.)

Lectura: con S1, 10.335 de 10.337 parejas tienen las dos diferencias dentro de la incertidumbre de medida. La "casi igualdad" no es saturación numérica que se pueda deshacer: es que la diferencia no se puede medir. B-S1 reduce el empate en el máximo a 5, pero los separa con diferencias de 0,01-0,05° y décimas de metro, muy por debajo de 0,265° y 17,4 m: es orden por ruido. Solo S2 desempata de verdad, y S2 no es defendible.

## 3. Los cinco

(a) orden de rango, sin hielo (snow_ice_frac ≥ 0,5) y a ≥ 2° de arco; (b) si hay más de cinco empatados en el máximo: selección del punto más lejano entre los empatados sin hielo, empezando por el de mayor similitud a precisión completa (empate: menor id).

A, regla (a): E3872 (79,5 N 92,5 E, Rusia), E4037 (78,5 N −102,5, Canadá), E4742 (76,5 N −117,5, Canadá), E5111 (75,5 N −108,5, Canadá), E5318 (75,5 N 98,5, Rusia): todos Ártico, gemelos a 80-86 S. A, regla (b) sobre 74 empatados: E17199 China, E50509 Argentina, E26087 Mauritania, E5846 Canadá, E41958 Namibia.

C-S1, regla (b) sobre 254 empatados (recomendado):

| id | lat, lon | lugar | gemelo (lat, lon) | rasgo IAU más cercano | pendiente T / L (°) | rugosidad T / L (m) | sim | idon. | final |
|---|---|---|---|---|---|---|---|---|---|
| E3872 | 79,5, 92,5 | Rusia | M61299 (−80,5, −80,5) | Drygalski (45 km) | 0,571 / 0,544 | 26,68 / 26,72 | 100 | 100 | 100,00 |
| E50509 | −50,5, −70,5 | Argentina | M59447 (−75,5, −132,5) | Zeeman (24 km) | 0,617 / 0,609 | 28,08 / 26,86 | 100 | 100 | 100,00 |
| E44239 | −32,5, 139,5 | South Australia, Australia | M59712 (−75,5, 132,5) | Schrodinger (24 km) | 0,547 / 0,547 | 18,18 / 15,66 | 100 | 100 | 100,00 |
| E26087 | 17,5, −12,5 | Assaba, Mauritania | M61294 (−80,5, −85,5) | Drygalski (29 km) | 0,523 / 0,510 | 26,42 / 26,80 | 100 | 100 | 100,00 |
| E26151 | 17,5, 51,5 | Al Mahrah, Yemen | M59712 (−75,5, 132,5) | Schrodinger (24 km) | 0,547 / 0,547 | 18,36 / 15,66 | 100 | 100 | 100,00 |

Distancias entre ellos (km): mínima 6.751 (Mauritania–Yemen), máxima 16.753; matriz completa en `candidates.C_S1_per_pixel.five_b_dist_km`. Nota: E44239 y E26151 comparten gemelo (M59712). Las cinco de A, B y C con regla (a) están en el JSON.

## 4. Validación (percentil de rango entre emparejados; menor = mejor)

| Sitio | 42d8bba | A | B-S1 | C-S1 | B-S2 | C-S2 |
|---|---|---|---|---|---|---|
| Ramon | 6,2 | 3,6 | 3,0 | 3,6 | 15,1 | 1,2 |
| Qaidam | 0,2 | 4,0 | 3,8 | 4,1 | 11,7 | 1,6 |
| Haughton | 1,7 | 4,2 | 4,9 | 4,2 | 17,8 | 46,7 |
| Yungay | 9,2 | 8,1 | 7,9 | 8,1 | 2,7 | 2,2 |
| Erfoud | 2,6 | 3,7 | 3,1 | 3,7 | 1,6 | 0,9 |
| MDRS | 28,9 | 20,5 | 19,9 | 20,5 | 1,4 | 7,2 |
| Bardenas | 44,5 | 68,2 | 68,4 | 68,2 | 75,0 | 86,9 |
| Tabernas | 24,7 | 71,3 | 69,8 | 71,5 | 22,2 | 22,8 |
| Death Valley | 37,4 | 80,0 | 79,3 | 80,1 | 85,3 | 68,1 |
| Dumont | 22,9 | 69,0 | 68,2 | 68,9 | 76,4 | 83,5 |
| HI-SEAS (neg.) | 51,9 | 83,6 | 82,8 | 83,7 | 87,1 | 43,2 |
| Rio Tinto (neg.) | 44,6 | 42,2 | 42,5 | 42,4 | 56,4 | 59,9 |
| El Soplao (neg.) | 89,5 | 95,4 | 94,9 | 95,4 | 14,4 | 40,9 |

Dhofar, Concordia y NEEMO no pasan el embudo Rover o no tienen celda emparejada.

Bardenas (E17098): pendiente 1,91°, rugosidad 77,0 m; gemelo con 1,90° y 74,1 m (C-S1). Tabernas (E18897): 3,17° y 110,7 m; gemelo 3,15° y 110,6 m. Ambos están dentro del rango de la zona lunar (pendiente p5-p95 2,26-13,08°, rugosidad 75-387 m; Bardenas en el borde bajo, Tabernas en el cuartil bajo), y su similitud es 99,9-100 en todos los candidatos salvo S2. Su posición la decide la idoneidad: 70,43 y 69,36, frente a una mediana de 74,16 entre emparejados y un máximo de 100 (254 puntos). No es el terreno: es la idoneidad Rover. Bajo B-S2/C-S2 Tabernas sube a 22 % porque su gemelo casi exacto cuenta, mientras Bardenas baja, pero esa escala no es defendible.

## 5. Recomendación

Candidato C con escala S1. Es defendible porque la escala sale de las cifras documentadas de las dos fuentes, sin suponer independencia que no está establecida, y C dice exactamente lo que las cifras permiten: una diferencia por debajo de la incertidumbre no se puede medir. Consecuencia honesta: con S1, 10.335 de 10.337 parejas son indistinguibles en terreno; la similitud no discrimina y el final queda en 50 + idoneidad/2 (Spearman 1,000). La validación no cambia respecto a A (diferencias ≤ 0,2 puntos de percentil). Empatan 254 puntos en el máximo (final 100,00, sin hielo); se eligen los cinco por dispersión geográfica (regla b). B-S1 deja 5 empatados, pero los separa por diferencias muy por debajo de σ: eso es ruido, no un orden.

Texto para la web: "254 sites are tied within the measurement uncertainty of the elevation models (slope ±0.27°, roughness ±17 m); the five shown are the most geographically spread of them, without ice and at least 2° apart."

## Para implementar

* Filtro de pareja: sin cambios, |Δpendiente| ≤ 2,0° y |Δrugosidad| ≤ 30,0 m (ambas clave).
* σ por variable: pendiente σ = √((7,17/(√2·1853))² + (10/(√2·1895,2))²) rad = 0,265093° ; rugosidad σ = √(2·7,17² + 2·10²) = 17,401661 m. Fuentes: ETOPO 2022 RMSE 7,17 m (MacFerrin et al. 2025, ESSD 17, 1835-1849); LOLA ~10 m radial (Smith et al. 2010, GRL 37, L18204), según docs/stats_audit/3_robustez_validacion_ranking.md F.3.
* Puntuación por variable: s = exp(−0,5·max(0, |d|/σ − 1)²), redondeo a 6 decimales como hoy; similitud = 100·(0,5·s_pend + 0,5·s_rug); final = 0,5·similitud + 0,5·idoneidad, publicado a 2 decimales.
* Gemelo: máximo de la puntuación; empates: menor (d_pend/σ_pend)² + (d_rug/σ_rug)², luego menor índice.
* Empate: final publicado igual al máximo (hoy 254 puntos, final 100,00; sin hielo: 254).
* Cinco: entre los empatados con snow_ice_frac < 0,5, empezar por el de mayor similitud a precisión completa (empate: menor id; hoy E3872), después añadir repetidamente el empatado cuya menor distancia de círculo máximo a los ya elegidos sea la mayor (empate: menor id). Resultado esperado: E3872, E50509, E44239, E26087, E26151. Si hubiera ≤ 5 empatados: orden de rango con los dos saltos (hielo; < 2° de arco de uno ya elegido).
* N en la web = número de empatados sin hielo (254).

## Qué no está establecido

* La correlación espacial del error de ETOPO 2022 y de LOLA: sin ella no se sabe cuánto reduce el promedio por celda (entre S1 y S2, un factor de hasta 20 en pendiente). S1 es pesimista porque usa errores absolutos.
* σ para pendientes no pequeñas (se usa la aproximación de pendiente pequeña; con pendientes de ≤ 1° en los empatados el error es despreciable).
* Que los 254 empatados sean igual de buenos: solo que no se distinguen con estos datos y esta idoneidad.
