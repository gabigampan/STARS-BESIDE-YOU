# El principio del análogo aplicado a los datos reales

Documento interno del equipo Stars Beside You (NASA Space Apps Challenge 2026), rama `final-integration`, 15-11-2026. **Propuesta de método pendiente de respuesta de Facundo; no se ha tocado motor, configuración ni datos, y no se ha reconstruido nada. Nada de lo que sigue está decidido ni implementado.**

**Actualización (15-11-2026, mañana): decidido y aplicado para Rover y Paneles solares; Base lunar sin cambios y pendiente.** Ver la última sección, "Resultado tras implementar (15-11-2026)". **Actualización (15-11-2026, 08:55 CET): Base lunar decidida y aplicada** (diseño D4b de `docs/LUNAR_BASE_PROPOSAL.md`: posición térmica en percentil dentro de cada población y terreno en valor real); ver la sección "Resultado tras implementar: Base lunar (15-11-2026)". Las frases de la sección anterior que dicen que Base lunar no cambia valen solo para la revisión 5. Las secciones A-E y la comprobación quedan como el registro de la propuesta.

Responde al principio del análogo que fijó Facundo el 15-11-2026 entre las 04:47 y las 04:49 CET (P1-P9, texto completo en `docs/DECISIONS.md`, sección "Principio del análogo"; resumen en inglés en `ASSUMPTIONS.md` §0.11). **Comprobado por un segundo agente con código propio** (sección "Comprobación" al final): las cifras de Paneles solares con la irradiancia sin atmósfera, las de la opción "solo amplitud" de Base lunar y varias de hoy se han corregido en este texto.

**De dónde salen los números.** Todo calculado hoy sobre las tablas reales de 1 grado (`tierra luna/output_real/earth_real_1deg.csv` y `moon_real_1deg.csv`) con los scripts de `scratchpad/stars/principle/` (`ctx2.py`, `a_today.py`, `b_compare.py`, `cd_method.py`, `e_today_bench.py`, `extra.py`; salidas `*.json` y `out_*.csv`). Los pares de hoy salen de la reimplementación independiente de `decisions-check/cctx.py` con el tratamiento del motor para la temperatura que falta; **coinciden con el paquete publicado** `app/public/data/v2`: el número de puntos de cada gemelo de `twins.json` es idéntico en las tres misiones (744, 721 y 48 gemelos distintos) y los gemelos del top 25 de `explain.json` también (similitud a menos de 0,005, redondeo). Los puntos candidatos de la Tierra son siempre los que pasan el embudo de cada misión, sin cambios (Rover 10.337, Paneles 18.777, Base lunar 2.419).

## Resumen

Hoy **una similitud alta no significa valores parecidos**. En el Rover, ningún par (0 de 10.337) tiene la pendiente a menos de 2° ni la rugosidad a menos de 30 m de su gemelo; entre los 3.286 pares con similitud ≥ 90 la pendiente de la Tierra es una mediana de 0,17 veces la de la Luna (seis veces menor) y la rugosidad 0,22 veces. La causa está en la raíz: cada cuerpo se normaliza por separado (z), así que "parecido" es "misma posición relativa", no "mismo valor". La propuesta sustituye la distancia en z por una puntuación gaussiana sobre la **diferencia absoluta** con una tolerancia en la unidad de la variable (la forma que ya usa `analog_finder.py`), da peso dominante a la variable clave de cada misión y **descarta el par** si la variable clave no está dentro de la tolerancia.

| misión | variable(s) clave | peso | tolerancia (unidad; z Tierra / z Luna) | zona propuesta | pares que sobreviven | número 1 resultante y su gemelo (valores reales de la variable clave) |
|---|---|---|---|---|---|---|
| Rover | pendiente y rugosidad | 40 % + 40 % (elevación relativa 20 %) | pendiente 2° (1,92 / 0,62); rugosidad 30 m (0,71 / 0,33) | polo sur (≤ 75 S), sin cambio | **10.192 de 10.337** (98,6 %) | E17566, 41,5 N 106,5 E (Mongolia Interior, China): 1,04° y 43,5 m. Gemelo M59895, 76,5 S 44,5 O (Casatus a 159 km): 1,15° y 44,2 m. Similitud 99,6 |
| Paneles solares | irradiancia sin atmósfera (Tierra: tope de la atmósfera; Luna: superficie) | 80 % (pendiente 10 %, rugosidad 10 %) | 0,6 kWh/m²/día (0,18 sobre la escala de la Tierra en el tope de la atmósfera, 0,49 sobre la de superficie / 0,13) | Luna entera | **18.776 de 18.777** | E38464, 16,5 S 124,5 E (Kimberley, Australia): 9,60 kWh/m²/día sobre la atmósfera, 6,18 en el suelo. Gemelo M24296, 22,5 N 3,5 O (Huxley a 76 km): 9,60 en el suelo. Similitud 99,99, final 98,45 |
| Base lunar | temperatura media y amplitud térmica diaria | 40 % + 40 % (pendiente 10 %, rugosidad 10 %) | temperatura 10 K (0,47 / 0,31); amplitud 5 K (0,76 / 0,10) | ninguna zona da pares | **0 de 2.419** en las nueve regiones, en el polo sur y en la Luna entera | ninguno. La aproximación más cercana: 40,2 K de diferencia de temperatura media (Luna entera; 96,6 K en las regiones de Artemis) |

Lo esencial en cifras:

- **Rover**: la zona del polo sur aguanta el principio. Con las tolerancias del propio equipo (`rover_preset.py`, base de 5 km) sobrevive el 98,6 % y, entre los 6.146 pares con similitud ≥ 90, la diferencia mediana es 0,36° de pendiente y 3,7 m de rugosidad (percentil 90: 0,84° y 10 m). Hoy esas medianas son 6,4° y 181 m.
- **Paneles solares**: el polo sur queda descartado con números (0 pares: ninguna celda polar llega a la energía de ningún candidato; el hueco mínimo es 1,66 kWh/m²/día). Los mares ecuatoriales solo dan gemelo al 33,9 % (6.360) porque su sol (9,05-10,40 kWh/m²/día) es el de las latitudes tropicales de la Tierra; la Luna entera da gemelo al 99,99 % y la similitud pasa a ir a favor de la idoneidad (Spearman +0,62; hoy −0,92 con el paquete publicado).
- **Base lunar**: ninguna celda de la Tierra reproduce el ambiente térmico lunar a esta escala. La celda terrestre más fría (238,1 K) es más cálida que la lunar más cálida (223,9 K), y la amplitud solo se solapa en 30,7-35,7 K, que en la Luna son 11 celdas en sombra permanente a 41-43 K. Las opciones están en la sección D.3; no se elige por el equipo.

---

## A. Los pares de hoy, juzgados con valores reales

Regla actual (`zone_twin`, pesos 20 / 33,3 / 26,7 / 20 %, z por cuerpo). Diferencia absoluta Tierra − gemelo: mediana y percentil 90; razón Tierra / Luna (mediana) donde tiene sentido. "Sim ≥ 90" = solo los pares con similitud de 90 o más.

**Rover** (10.337 pares; 3.286 con similitud ≥ 90). Medianas de los valores: Tierra 1,57°, 63,6 m, 281,0 K; gemelo 8,51°, 253,8 m, 160,8 K.

| variable | todos: mediana / p90 | razón T/L | sim ≥ 90: mediana / p90 | razón T/L |
|---|---|---|---|---|
| pendiente (°) | 7,01 / 11,96 | 0,18 | 6,37 / 10,65 | 0,17 |
| rugosidad (m) | 187,7 / 289,4 | 0,25 | 181,3 / 265,0 | 0,22 |
| elevación relativa (m) | 505 / 1.241 | — | 380 / 907 | — |
| temperatura media (K) | 118,5 / 137,3 | 1,73 | 103,6 / 108,0 | 1,66 |
| amplitud térmica diaria (K) | 206,3 / 220,4 | 0,041 | 206,7 / 220,7 | 0,027 |
| temperatura mínima (K) | 186,6 / 214,0 | — | 168,7 / 188,4 | — |
| irradiancia (kWh/m²/día) | 1,94 / 3,38 | 2,00 | 0,97 / 2,82 | 1,53 |
| altura máxima del Sol (°) | 50,9 / 74,0 | — | 30,9 / 40,9 | — |
| fracción de Sol rasante | 0,16 / 0,60 | — | 0,10 / 0,79 | — |
| fracción desnuda | 0,99 / 1,00 | — | 0,99 / 1,00 | — |

**Paneles solares** (18.777; 7.474 con similitud ≥ 90).

| variable | todos: mediana / p90 | razón T/L | sim ≥ 90: mediana / p90 | razón T/L |
|---|---|---|---|---|
| pendiente (°) | 4,36 / 9,74 | 0,08 | 4,26 / 6,85 | 0,06 |
| rugosidad (m) | 131,7 / 232,9 | 0,10 | 127,3 / 192,9 | 0,06 |
| elevación relativa (m) | 753 / 1.488 | — | 988 / 2.165 | — |
| temperatura media (K) | 126,3 / 141,2 | 1,78 | 104,7 / 108,4 | 1,66 |
| amplitud (K) | 195,8 / 216,1 | 0,054 | 202,2 / 217,6 | 0,033 |
| temperatura mínima (K) | 182,7 / 214,7 | — | 159,5 / 176,5 | — |
| irradiancia (kWh/m²/día) | 2,10 / 3,52 | 2,14 | 1,98 / 2,99 | 2,16 |
| altura máxima del Sol (°) | 47,9 / 74,0 | — | 24,9 / 36,9 | — |
| fracción de Sol rasante | 0,16 / 0,58 | — | 0,15 / 0,60 | — |
| fracción desnuda | 1,00 / 1,00 | — | 1,00 / 1,00 | — |

**Base lunar** (2.419; solo 5 con similitud ≥ 90).

| variable | todos: mediana / p90 | razón T/L | sim ≥ 90: mediana / p90 | razón T/L |
|---|---|---|---|---|
| pendiente (°) | 6,57 / 10,87 | 0,13 | 12,71 / 14,78 | 0,33 |
| rugosidad (m) | 171,7 / 276,1 | 0,18 | 306,8 / 331,8 | 0,44 |
| elevación relativa (m) | 845 / 1.759 | — | 2.031 / 2.291 | — |
| temperatura media (K) | 142,3 / 160,8 | 2,00 | 106,1 / 106,6 | 1,63 |
| amplitud (K) | 164,5 / 191,1 | 0,10 | 183,8 / 196,2 | 0,08 |
| temperatura mínima (K) | 198,7 / 213,3 | — | 179,4 / 182,2 | — |
| irradiancia (kWh/m²/día) | 4,03 / 5,05 | 6,52 | 3,53 / 3,53 | 6,60 |
| altura máxima del Sol (°) | 70,9 / 79,9 | — | 67,9 / 69,5 | — |
| fracción de Sol rasante | 0,67 / 0,93 | — | 0,79 / 0,79 | — |
| fracción desnuda | 0,67 / 1,00 | — | 0,70 / 0,72 | — |

**Pares dentro de una tolerancia razonable hoy** (las de la sección C):

| variable (tolerancia) | Rover: todos / sim ≥ 90 | Paneles | Base lunar |
|---|---|---|---|
| pendiente (2°) | 0 % / 0 % | 0 % / 0 % | 0 % / 0 % |
| rugosidad (30 m) | 0 % / 0 % | 0 % / 0 % | 0 % / 0 % |
| pendiente y rugosidad a la vez (P5) | 0 % / 0 % | — | — |
| elevación relativa (500 m) | 49,6 % / 65,0 % | 28,1 % / 27,3 % | 18,8 % / 0 % |
| temperatura media (10 K) | 0 % / 0 % | 0 % / 0 % | 0 % / 0 % |
| amplitud (5 K) | 0 % / 0 % | 0 % / 0 % | 0 % / 0 % |
| irradiancia en el suelo (0,6 kWh/m²/día) | 14,8 % / 31,4 % | 5,4 % / 8,4 % | 0 % / 0 % |

**Respuesta clara:** hoy una similitud alta no significa valores parecidos. Entre los pares de Rover con similitud ≥ 90, la pendiente de la Tierra es entre 0,11 y 0,24 veces la del gemelo (percentiles 10 y 90; mediana 0,17) y la rugosidad entre 0,13 y 0,33 (mediana 0,22). En Paneles, 0,057 y 0,057 de mediana: sitios unas 17 veces más llanos y lisos que su gemelo. Es exactamente el síntoma de P7 ("98 %" con una pendiente siete veces menor): el número 1 del Rover de hoy (E5128, isla Devon, similitud 98,4) tiene 0,88° y 34,5 m; su gemelo (M60952, Drygalski), 6,19° y 198,7 m.

## B. Qué se puede comparar en valor absoluto

Población: Tierra, las 25.095 celdas de tierra firme del motor (`elevation_m > 0`; temperatura y amplitud sin la Antártida); Luna, las 64.800 celdas. "Solape" = intervalo común de los dos rangos y % de cada cuerpo dentro; OVL = área común de los dos histogramas (0 = nada en común, 1 = iguales).

| variable | misma magnitud en los dos cuerpos | Tierra p5 / p50 / p95 (mín-máx) | Luna p5 / p50 / p95 (mín-máx) | solape | OVL | escala robusta T / L |
|---|---|---|---|---|---|---|
| pendiente (°) | sí: misma definición, base 3,7 / 3,8 km | 0,07 / 0,48 / 4,70 (0,004-17,2) | 0,45 / 4,91 / 10,33 (0,05-22,8) | 0,05-17,2: 97,5 % T, 99,9 % L | 0,39 | 1,04 / 3,25 |
| rugosidad (m) | sí: RMS a 1,85 / 1,90 km | 2,3 / 18,1 / 174,5 (0,01-559) | 16,3 / 159,7 / 306,9 (1,6-616) | 1,6-559: 98,0 % T, 100 % L | 0,40 | 42,3 / 92,0 |
| elevación relativa (m) | sí (altura sobre la media del cuerpo) | −665 / −225 / 2.542 | −3.486 / −528 / 3.694 | −696 a 4.724: 100 % T, 51,9 % L | 0,51 | 1.007 / 1.769 |
| temperatura media (K) | casi (T: LST MODIS de cielo despejado, media 10:30/22:30; L: temperatura bolométrica, media del ciclo) | 255,2 / 284,3 / 302,6 (238,1-309,7) | 114,8 / 197,7 / 217,3 (41,1-223,9) | **ninguno: hueco de 14,3 K** | 0 | 21,5 / 32,3 |
| amplitud diaria (K) | no del todo (T: 10:30 − 22:30, la subestima; L: máx − mín) | 2,4 / 8,6 / 21,1 (−4,6-35,7) | 168,3 / 265,6 / 297,9 (30,7-311,8) | 30,7-35,7: 0,1 % T (21 celdas), 11 celdas L | 0 | 6,6 / 47,8 |
| temperatura mínima (°C) | no (T: aire, mes más frío; L: superficie) | −62,2 / −19,9 / 20,0 | −219,9 / −185,3 / −178,5 (máx −159,1) | **ninguno: hueco de 86,8 K** | 0 | 32,1 / 11,1 |
| irradiancia en el suelo (kWh/m²/día) | misma unidad y definición (energía diaria sobre horizontal), con atmósfera en la Tierra y sin ella en la Luna | 2,20 / 3,68 / 5,86 (1,41-6,44) | 0,39 / 7,35 / 10,36 (0-10,40) | 1,41-6,44: 100 % T, 30,0 % L | 0,27 | 1,22 / 4,56 |
| irradiancia sin atmósfera (Tierra: tope de la atmósfera, media anual) | sí: la misma geometría, constante solar 1.361 W/m² | 4,15 / 6,19 / 9,93 (4,14-9,97) | igual que arriba | 4,14-9,97: 100 % T, 54,5 % L | 0,50 | 3,32 / 4,56 |
| altura máxima del Sol (°) | sí (fórmula de la latitud) | 26,9 / 57,9 / 90 | 6,0 / 46,5 / 87,0 | 23,9-90: 100 % T, 75,6 % L | 0,66 | — |
| fracción de Sol rasante (0-5°) | sí (fórmula) | 0,058 / 0,117 / 0,208 | 0,056 / 0,079 / 0,866 | 100 % T, 64,4 % L | 0,64 | — |
| fracción desnuda | no: en la Luna vale 1 por definición | mediana 0,001 | 1 en todas | — | — | — |

**Comparables en valor absoluto:** pendiente, rugosidad, elevación relativa (y la geometría solar). Sus rangos se solapan casi por completo; que las medianas difieran (0,48° frente a 4,91°) no impide encontrar celdas lunares con el mismo valor: lo impide la zona.

**Irradiancia (P3, P8).** La Luna en el suelo recibe `1.361 × 24 / π × cos(lat)` = 10,40 kWh/m²/día en el ecuador (la tabla lo cumple con un error máximo de 0,002 por debajo de 60°). La Tierra en el tope de la atmósfera recibe casi lo mismo en la misma latitud (media anual, igual en los dos hemisferios: 9,97 en el ecuador, 8,77 a 30°, 7,37 a 45°, 5,67 a 60°; la Luna, 10,40 / 9,00 / 7,35 / 5,20). La diferencia de magnitud es **la atmósfera**: el suelo de la Tierra recibe una mediana del 54,0 % de su tope de atmósfera (percentiles 5-95: 42,4-88,5 %; en los candidatos solares, 57,7 %). Por eso, en el suelo, la energía de un candidato solar (2,5-6,44) solo se repite en la Luna entre 52,5° y 74,5° de latitud (14.975 celdas, **ninguna en los mares ecuatoriales**, cuyo suelo recibe 9,05-10,40); y en el polo sur (≤ 75 S) nunca (máximo 2,475). **Comparación honesta propuesta:** emparejar con la energía sin atmósfera (la misma magnitud en los dos cuerpos: geometría + constante solar) y decir aparte la pérdida atmosférica en kWh/m²/día. En el par número 1 propuesto (E38464 y M24296): 9,60 sobre la atmósfera en los dos; 6,18 en el suelo de la Tierra frente a 9,60 en el de la Luna (la Tierra recibe el 64 %; la mediana de los candidatos solares es el 58 %). La otra diferencia física que no desaparece: en la Luna el día dura 14,75 días terrestres y la noche otros tantos.

**Temperatura (P8).** Las distribuciones no se tocan: la celda de la Tierra más fría con dato (E6261, 72,5 N 38,5 O, Groenlandia) está a 238,1 K y la lunar más cálida (M29262, 8,5 N 77,5 O) a 223,9 K. Máximo por zona lunar: polo sur 172,2 K, regiones de Artemis 167,5 K, mares 223,9 K. La amplitud diaria de la Tierra no pasa de 35,7 K (E40430, 22,5 S 69,5 O, Atacama; 44,7 K si se toma el mes de mayor amplitud) y la lunar no baja de 30,7 K; las 11 celdas lunares por debajo de 35,7 K están todas a 87,5 S, a 41-43 K, en sombra permanente (ninguna en las regiones de Artemis). La temperatura mínima tampoco se solapa (hueco de 86,8 K). **Comparación honesta propuesta:** no llamar "parecida" a ninguna temperatura; enseñar los dos valores y la diferencia en K, y si se quiere un número relativo, decir "la celda de la Tierra es la n-ésima más fría de su mundo" sin convertirlo en similitud.

## C. Una similitud que funciona con valores reales

**Raíz del fallo (P7).** El z por cuerpo (`analog_finder.normalize_planetary_features`) mide la posición dentro de cada mundo. Como las escalas son distintas (pendiente: 1,04° en la Tierra, 3,25° en la Luna; rugosidad: 42 m y 92 m), z iguales significan valores distintos. No se arregla con un parche sobre la similitud: hay que comparar valores.

**Fórmula propuesta** (implementable en una hora; mismo motor de pares, otra distancia):

1. Para cada variable v del par: `s_v = exp(−0,5 × ((valor Tierra − valor Luna) / τ_v)²)`. Es la forma que el repositorio ya usa para la calidad antigua del Rover, `tierra luna/analog_finder.py`, líneas 285-286:
   ```python
   slope_q = np.exp(-0.5 * ((s300 - t_slope) / max(slope_tol, 0.5)) ** 2)
   rough_q = np.exp(-0.5 * ((r300 - t_rough) / max(rough_tol * 12.0, 5.0)) ** 2)
   ```
2. Similitud = `100 × Σ w_v s_v / Σ w_v` (media ponderada; una variable secundaria sin dato se quita y se renormaliza, como hoy).
3. **Filtro del par (P2, P9):** cada variable clave con `|Δ| ≤ τ` (s ≥ 0,61); cada secundaria con `|Δ| ≤ 2τ` (s ≥ 0,14). Si ninguna celda de la zona lo cumple, el punto **no tiene análogo y no se enseña** (sigue en el embudo con su idoneidad, sin par).
4. Gemelo = la celda de la zona que cumple el filtro con la similitud más alta (empate: id más bajo). Final = 0,5 × similitud + 0,5 × idoneidad, como hoy.

**Tolerancias.** Las del equipo donde existen: `tierra luna/rover_preset.py` (versión 3), `tolerances_by_baseline`, líneas 196-205: 300 m → pendiente 5°, rugosidad 10 m; 5 km → pendiente 2°, rugosidad 30 m. Nuestras pendientes tienen base de 3,7 km y la rugosidad un desfase de 1,9 km: en escala logarítmica las dos están más cerca de 5 km que de 300 m, así que se usan **2° y 30 m**. Las demás salen de los datos con una regla única: **la mitad de la escala robusta de la Tierra (rango intercuartílico / 1,349), redondeada**, es decir, media "desviación típica" terrestre.

| variable | τ (unidad) | origen | z Tierra | z Luna | filtro |
|---|---|---|---|---|---|
| pendiente | 2° | equipo (5 km) | 1,92 | 0,62 | clave en Rover; secundaria (≤ 4°) en las otras |
| rugosidad | 30 m | equipo (5 km) | 0,71 | 0,33 | clave en Rover; secundaria (≤ 60 m) en las otras |
| elevación relativa | 500 m | datos (escala T 1.007 m) | 0,50 | 0,28 | secundaria en Rover (≤ 1.000 m) |
| irradiancia sin atmósfera | 0,6 kWh/m²/día | datos (escala T en el suelo 1,22) | 0,18 (tope de atmósfera, escala 3,32; 0,49 en el suelo) | 0,13 | clave en Paneles |
| temperatura media | 10 K | datos (escala T 21,5 K) | 0,47 | 0,31 | clave en Base lunar |
| amplitud diaria | 5 K | datos (escala T 6,6 K; la regla daría 3,3 → 3 K, se tomó 5 K) | 0,76 | 0,10 | clave en Base lunar |

**Dos excepciones a la regla, a decidir por el equipo** (añadido en la comprobación): (1) la amplitud: la mitad de 6,6 K es 3,3 K, no 5 K; con 3,3 K y solo la amplitud como clave, el número de candidatos de Base lunar con alguna celda del polo sur a menos de la tolerancia baja de 126 a 55. (2) La irradiancia: la tolerancia sale de la escala de la Tierra **en el suelo** (1,22) aunque la variable comparada es la del **tope de la atmósfera** (escala 3,32, que con la misma regla daría 1,7). Con 0,6 la similitud ya satura en la Luna entera (sección D.2), así que 1,7 la saturaría más.

**Definición de la elevación relativa** (añadido en la comprobación; hay que fijarla antes de implementar): en este documento es la elevación menos la media de la celda ponderada por el área (cos lat) de las celdas con dato de cada cuerpo (Tierra, solo tierra firme: +695,9 m; Luna: −248,4 m). El motor **no** exporta eso: su `elevation_rel_m` es `elevation_m` tal cual (Tierra sobre el geoide, Luna sobre la esfera de 1.737,4 km; `engine/datasets.json`, nota de `elevation_rel_m`), porque al motor le da igual para el z. En valor absoluto sí importa: con la definición del motor, el Rover en el polo sur deja 10.145 supervivientes (no 10.192), 281 gemelos distintos (no 401), el gemelo más compartido sube a M59895 con 4.934 puntos (48,6 %) y el número 1 pasa a ser E49069 (46,5 S 70,5 O, Patagonia). Las cifras de este documento usan la definición centrada.

**Pesos.** Variables clave 80 % en total, secundarias 20 %. Rover: pendiente 40, rugosidad 40, elevación relativa 20. Paneles: irradiancia 80, pendiente 10, rugosidad 10. Base lunar: temperatura 40, amplitud 40, pendiente 10, rugosidad 10. La temperatura sale de la similitud del Rover y de Paneles: no puede coincidir (sección B) y se enseña como diferencia.

**Qué significa "dominante" en números.** Con 80 %: claves perfectas y secundarias en el borde (2τ) → 82,7; claves en el borde (τ) y secundarias perfectas → 68,5. Llegar a 90 exige que la puntuación media de las claves sea ≥ 0,875, es decir, `|Δ| ≤ 0,52 τ` en cada clave (1,0° y 15,5 m en el Rover). **Alternativa:** claves 2/3, secundarias 1/3 → 71,2 y 73,8 en los mismos dos casos; 90 exige claves ≥ 0,85. Con la alternativa cambian 2.224 gemelos de 10.192 en el Rover (polo sur, la zona propuesta), 1.775 de 10.337 en el Rover (Luna entera), 1.352 de 18.776 en Paneles (Luna entera) y 112 de 6.360 en Paneles (mares); los supervivientes no cambian (el filtro es el mismo).

**Sensibilidad: pares que sobreviven a la mitad, a la tolerancia y al doble** (todas las tolerancias escaladas a la vez; entre paréntesis, solo las claves escaladas).

| misión, zona | ×0,5 | ×1 | ×2 |
|---|---|---|---|
| Rover, polo sur | 6.070 (8.662) | 10.192 | 10.337 (10.337) |
| Rover, Luna entera | 10.333 (10.335) | 10.337 | 10.337 |
| Rover, mares | 1.703 (6.002) | 6.006 | 9.155 (6.007) |
| Paneles, Luna entera | 18.775 (18.776) | 18.776 | 18.777 |
| Paneles, mares | 5.498 (5.501) | 6.360 | 7.425 (7.424) |
| Paneles, polo sur | 0 | 0 | 0 |
| Base lunar (temperatura + amplitud), cualquier zona | 0 | 0 | 0 |
| Base lunar (solo amplitud), polo sur o Luna entera | 23 (30) | 74 | 779 (367) |
| Base lunar (solo amplitud), regiones de Artemis | 0 | 0 | 0 |

En el Rover, polo sur, escalar solo la pendiente a ×0,5 deja 10.146 y solo la rugosidad 8.750: lo que más filtra es la rugosidad.

**Comprobación de la propiedad pedida (similitud ≥ 90 ⇒ valores parecidos).**

| misión, zona | pares con sim ≥ 90 | pendiente: mediana / p90 | rugosidad | elevación relativa | variable clave de luz o calor | lo que no se parece (se enseña como diferencia) |
|---|---|---|---|---|---|---|
| Rover, polo sur | 6.146 | 0,36° / 0,84° | 3,7 / 10,0 m | 105 / 360 m | — | temperatura 150 / 182 K; irradiancia 2,49 / 4,15 |
| Rover, Luna entera | 10.334 | 0,06° / 0,16° | 0,9 / 2,5 m | 20 / 62 m | — | temperatura 84 / 139 K |
| Paneles, Luna entera | 18.775 | 0,05° / 0,31° | 0,9 / 11,1 m | 1.970 / 4.450 m (no entra) | sin atmósfera: 0,027 / 0,085 kWh/m²/día | en el suelo 3,13 / 4,95 (la Tierra recibe el 58 %); temperatura 84 / 89 K |
| Paneles, mares | 5.494 | 0,03° / 0,14° | 0,5 / 2,3 m | 1.670 / 2.830 m (no entra) | 0,019 / 0,095 | en el suelo 4,37 / 5,68; temperatura 85 / 90 K |
| Base lunar, solo amplitud, polo sur | 22 | 0,39° / 1,60° | 11,6 / 34,7 m | 6.280 / 6.800 m | amplitud 0,38 / 1,67 K | **temperatura media 246 / 253 K** |

Con el método propuesto la propiedad se cumple por construcción en las variables que entran.

## D. Las zonas bajo el principio

Columnas: supervivientes (de los candidatos), gemelos distintos, mayor cuota de un gemelo, similitud (mín / p10 / mediana / p90 / máx), Spearman similitud-idoneidad entre supervivientes.

### D.1 Rover (10.337 candidatos)

| zona | celdas | sobreviven | gemelos distintos | mayor cuota | similitud | Spearman |
|---|---|---|---|---|---|---|
| **polo sur (≤ 75 S)** | 5.400 | **10.192 (98,6 %)** | 401 | M61116 (Ganswindt, 79,5 S 96,5 E): 2.033, 19,9 % | 56,1 / 81,1 / 93,3 / 99,2 / 100 | −0,53 |
| Luna entera | 64.800 | 10.337 (100 %) | 3.647 | M49436 (Wargentin a 87 km): 140, 1,4 % | 68,9 / 99,5 / 99,9 / 100 / 100 | +0,11 |
| mares ecuatoriales (referencia) | 6.686 | 6.006 (58,1 %) | 145 | M30462: 669, 11,1 % | 66,7 / 83,6 / 89,1 / 94,4 / 97,3 | +0,27 |

Con la Luna entera casi todos los puntos encuentran un gemelo prácticamente idéntico (mediana 99,9): la similitud deja de distinguir y el orden lo pone la idoneidad. En el polo sur la similitud sí distingue y va contra la idoneidad (−0,53): los sitios más llanos de la Tierra (0,5°, 15 m) apenas tienen equivalente en el polo sur, cuya celda más suave tiene 0,23° pero cuyo percentil 5 ya es 2,25° y 75 m.

**Top 10, polo sur** (pendiente y rugosidad Tierra | gemelo):

| # | celda Tierra | lat, lon | idoneidad | similitud | final | gemelo | pendiente T / L (°) | rugosidad T / L (m) |
|---|---|---|---|---|---|---|---|---|
| 1 | E17566 | 41,5 N 106,5 E | 99,2 | 99,6 | 99,4 | M59895 (76,5 S 44,5 O, Casatus a 159 km) | 1,04 / 1,15 | 43,5 / 44,2 |
| 2 | E23945 | 23,5 N 5,5 E | 98,7 | 99,8 | 99,2 | M59895 | 1,22 / 1,15 | 43,4 / 44,2 |
| 3 | E18282 | 39,5 N 102,5 E | 99,6 | 98,8 | 99,2 | M59895 | 0,91 / 1,15 | 38,8 / 44,2 |
| 4 | E18280 | 39,5 N 100,5 E | 98,7 | 99,5 | 99,1 | M59895 | 1,13 / 1,15 | 48,9 / 44,2 |
| 5 | E15395 | 47,5 N 95,5 E | 98,7 | 99,1 | 98,9 | M59895 | 1,24 / 1,15 | 41,3 / 44,2 |
| 6 | E18281 | 39,5 N 101,5 E | 99,7 | 98,1 | 98,9 | M59895 | 0,86 / 1,15 | 36,7 / 44,2 |
| 7 | E16841 | 43,5 N 101,5 E | 98,0 | 99,6 | 98,8 | M59895 | 1,39 / 1,15 | 45,8 / 44,2 |
| 8 | E16121 | 45,5 N 101,5 E | 98,6 | 99,0 | 98,8 | M59895 | 1,26 / 1,15 | 41,1 / 44,2 |
| 9 | E15034 | 48,5 N 94,5 E | 99,2 | 98,3 | 98,8 | M59895 | 1,16 / 1,15 | 35,3 / 44,2 |
| 10 | E16482 | 44,5 N 102,5 E | 97,9 | 99,5 | 98,7 | M59895 | 1,39 / 1,15 | 46,4 / 44,2 |

Gobi, Alashan y Mongolia (y el Ahaggar, puesto 2), todos con el mismo gemelo: una de las celdas más suaves del polo sur. **Top 10, Luna entera**: Ártico canadiense (73,5-78,5 N), Taimyr (72,5 N) y Chubut, todos con similitud 100,0 y gemelos en mares y llanuras (p. ej. E5832 73,5 N 107,5 O: 0,647° / 21,8 m frente a M7334, 69,5 N 45,5 O, Carpenter: 0,645° / 21,9 m).

### D.2 Paneles solares (18.777 candidatos)

| zona | clave | celdas | sobreviven | gemelos distintos | mayor cuota | similitud | Spearman |
|---|---|---|---|---|---|---|---|
| **Luna entera** | sin atmósfera | 64.800 | **18.776 (99,99 %)** | 5.811 | M8436 (66,5 N 23,5 O, Fontenelle a 110 km): 1.524, 8,1 % | 87,5 / 98,6 / 99,8 / 100 / 100 | **+0,62** |
| mares ecuatoriales | sin atmósfera | 6.686 | 6.360 (33,9 %) | 1.704 | M21795 (Banting a 92 km): 159, 2,5 % | 69,0 / 88,0 / 99,9 / 100 / 100 | +0,16 |
| polo sur | sin atmósfera | 5.400 | 0 | — | — | — | — |
| Luna entera | en el suelo | 64.800 | 18.776 | 3.156 | M8075: 2.096, 11,2 % | 85,0 / 99,2 / 99,8 / 100 / 100 | −0,01 |
| mares | en el suelo | 6.686 | 0 (hueco mínimo 2,61) | — | — | — | — |
| polo sur | en el suelo | 5.400 | 2.841 (15,1 %) | 16 | M59715 (Schrödinger): 1.662, 58,5 % | 55,7 / 70,6 / 87,4 / 98,0 / 99,9 | −0,25 |

El único punto sin gemelo con la Luna entera es E19334 (36,5 N 74,5 E, Karakórum: 13,7° y 478 m). Polo sur con la clave sin atmósfera: hueco mínimo 1,66 kWh/m²/día, mediana 4,29. **Mares:** sobreviven solo puntos a 33,5° o menos del ecuador (ninguno más allá); el hueco mediano sobre todos los candidatos es 2,29. **En el suelo** los gemelos son celdas de 52-75° de latitud con Sol rasante y la similitud no sigue a la idoneidad (−0,01); con la clave sin atmósfera, sí (+0,62).

**Top 10, Luna entera, clave sin atmósfera** (irradiancia sobre la atmósfera de la Tierra | suelo lunar; la de suelo de la Tierra entre paréntesis):

| # | celda Tierra | lat, lon | idoneidad | similitud | final | gemelo | irradiancia T / L (kWh/m²/día) | pendiente T / L | rugosidad T / L |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E38464 | 16,5 S 124,5 E | 96,9 | 99,99 | 98,45 | M24296 (22,5 N 3,5 O, Huxley a 76 km) | 9,60 (6,18) / 9,60 | 0,98 / 1,05 | 39,2 / 39,0 |
| 2 | E38105 | 15,5 S 125,5 E | 96,9 | 99,89 | 98,40 | M24769 (21,5 N 109,5 E, Deutsch a 95 km) | 9,64 (6,11) / 9,67 | 1,13 / 1,02 | 42,5 / 42,0 |
| 3 | E38744 | 17,5 S 44,5 E | 96,77 | 99,95 | 98,36 | M40854 (23,5 S 5,5 O, Thebit a 61 km) | 9,55 (5,97) / 9,53 | 0,71 / 0,65 | 29,6 / 29,0 |
| 4 | E37746 | 14,5 S 126,5 E | 96,62 | 99,98 | 98,30 | M24761 (21,5 N 101,5 E, Dziewulski a 72 km) | 9,69 (6,07) / 9,67 | 0,76 / 0,71 | 26,9 / 27,6 |
| 5 | E38465 | 16,5 S 125,5 E | 96,48 | 100,0 | 98,24 | M40406 (22,5 S 93,5 O, Rimae Pettit a 83 km) | 9,60 (6,14) / 9,60 | 0,92 / 0,95 | 33,3 / 32,9 |
| 6 | E38385 | 16,5 S 45,5 E | 96,47 | 100,0 | 98,23 | M24227 (22,5 N 72,5 O, Eddington a 33 km) | 9,60 (5,93) / 9,60 | 0,54 / 0,51 | 20,3 / 20,2 |
| 7 | E37750 | 14,5 S 130,5 E | 96,4 | 99,98 | 98,19 | M24688 (21,5 N 28,5 E, Clerke a 37 km) | 9,69 (5,96) / 9,67 | 0,75 / 0,76 | 29,4 / 28,8 |
| 8 | E38109 | 15,5 S 129,5 E | 96,44 | 99,91 | 98,17 | M40186 (21,5 S 46,5 E, Santbech a 71 km) | 9,64 (6,08) / 9,67 | 0,81 / 0,80 | 35,4 / 34,5 |
| 9 | E29749 | 7,5 N 49,5 E | 96,35 | 99,97 | 98,16 | M26063 (17,5 N 36,5 O, Bessarion a 84 km) | 9,90 (6,20) / 9,91 | 0,36 / 0,38 | 10,9 / 10,9 |
| 10 | E30468 | 5,5 N 48,5 E | 96,35 | 99,96 | 98,16 | M26087 (17,5 N 12,5 O, Eratosthenes a 98 km) | 9,93 (6,12) / 9,91 | 0,39 / 0,40 | 13,7 / 13,8 |

Kimberley (Australia), Madagascar y Somalia. Con los mares el top 10 son los mismos 10 puntos en el mismo orden; solo cambia el gemelo del número 2 (E38105: M24583, 21,5 N 76,5 O, Struve a 58 km, también 9,67). (Corregido en la comprobación: la versión anterior usaba una irradiancia de la Tierra en el tope de la atmósfera con un error de hasta ±0,10 kWh/m²/día según el hemisferio; ver "Comprobación".)

### D.3 Base lunar (2.419 candidatos) y la respuesta a P4

| zona | celdas | sobreviven (temperatura 10 K + amplitud 5 K) | al doble (20 K + 10 K) | hueco mínimo de temperatura (mín / mediana de los puntos) | hueco de amplitud (mín / mediana) |
|---|---|---|---|---|---|
| nueve regiones de Artemis | 280 | **0** | 0 | 96,6 / 121,3 K | 51,9 / 68,3 K |
| polo sur entero | 5.400 | **0** | 0 | 91,8 / 116,5 K | 0,01 / 11,4 K |
| Luna entera | 64.800 | **0** | 0 | 40,2 / 64,9 K | 0,01 / 11,4 K |

**Respuesta a P4.** La zona actual no aguanta el principio: con temperatura y amplitud exigidas parecidas en valor no sobrevive ningún par, en ninguna zona, ni con el doble de tolerancia. El 99,96 % de P4 es la cifra en z (decisión 4); en valor absoluto es el 100 %: el candidato más frío de Base lunar está a 264,1 K y la celda más cálida de las regiones de Artemis a 167,5 K (96,6 K de diferencia). Hoy la diferencia mediana de temperatura con su gemelo es 142,3 K. **Los datos dicen que ninguna celda de la Tierra reproduce el ambiente térmico lunar a esta escala.** La aproximación más cercana:

- **Temperatura media**: imposible de igualar; el hueco más pequeño entre un candidato y cualquier celda de la Luna es 40,2 K (mediana 64,9 K); en las regiones de Artemis, 96,6 K.
- **Amplitud diaria**: 126 candidatos (5,2 %) tienen alguna celda lunar a menos de 5 K de amplitud; con el filtro de las secundarias (pendiente ≤ 4°, rugosidad ≤ 60 m) quedan **74 pares (3,1 %)**: 37 en los Andes centrales (Puna, Altiplano y Atacama, 17,5-27,5 S) y 37 en Asia (Tíbet y Qaidam, 28,5-38,5 N 80-97,5 E, e Irán, 29,5-31,5 N 53-59 E), con amplitudes de 25,7-35,3 K. Tienen 7 gemelos, todos junto a Haworth (87,5 S, fuera de las regiones de Artemis), celdas en sombra permanente a 41-43 K; el más compartido (M63895) reúne 54 puntos (73 %). El número 1 sería E40432 (22,5 S 67,5 O): amplitud 33,36 K frente a 33,69 K, pero temperatura media 282,7 K frente a 41,5 K (diferencia de 241 K). Es una coincidencia numérica en un régimen físico distinto (un cráter que nunca ve el Sol), no un análogo.
- **Temperatura mínima**: hueco de 86,8 K entre la mínima más fría de la Tierra (aire) y la más cálida de la Luna (superficie).

**Opciones para el equipo (sin elegir):**

1. **Base lunar juzgada solo por la amplitud donde los rangos se solapan**: 74 pares (37 en los Andes centrales, 37 en el Tíbet, Qaidam e Irán), todos con gemelo junto a Haworth (polo sur, no Artemis); 0 en las regiones de Artemis. Hay que decir que el gemelo está a ~41 K.
2. **"Lo más cercano disponible" con el hueco a la vista**: mantener un gemelo (por ejemplo, la celda de las regiones de Artemis más cálida y de amplitud más baja) sin llamarlo similar, enseñando "la Tierra está X K más caliente y su ciclo diario es Y K menor". Sin porcentaje de similitud.
3. **Redefinir la variable clave**: Base lunar pasa a juzgarse por el terreno del emplazamiento (pendiente y rugosidad, como el Rover, en las regiones de Artemis) y el calor se enseña como diferencia. Con las tolerancias del Rover se puede calcular en minutos; no está calculado aquí.
4. **Quitar el par de Base lunar** y dejar solo la idoneidad terrestre (el embudo térmico), explicando por qué.

### D.4 Dónde caen los sitios análogos conocidos

Celdas de 1° de `/home/user/NASA/docs/research/02_analog_benchmark.csv`. Black Point y Meteor Crater caen en la misma celda (E19508). Valores clave Tierra / gemelo.

**Rover** (hoy: polo sur con z; propuesto: polo sur con valores):

| sitio | celda | hoy: puesto, similitud, pendiente T/L, rugosidad T/L | propuesto: puesto (de 10.192), similitud, gemelo, pendiente T/L, rugosidad T/L |
|---|---|---|---|
| Haughton | E5130 | 79, 96,1; 1,01 / 6,80°; 52 / 243 m | 172, 92,0; M61116 Ganswindt; 1,01 / 1,45°; 52,2 / 50,2 m |
| Bardenas | E17098 | 6.048, 80,4; 1,91 / 10,29; 77 / 276 | 4.525, 94,3; M61352 Mons Cabeus; 1,91 / 2,49; 77,0 / 79,7 |
| Tabernas | E18897 | 7.103, 76,0; 3,17 / 13,09; 111 / 348 | 2.518, 99,7; M64032 Slater; 3,17 / 3,32; 110,7 / 112,0 |
| MDRS | E18429 | 5.197, 78,4; 1,90 / 9,48; 74 / 254 | 2.954, 90,5; M59619 Boguslawsky; 1,90 / 3,07; 74,1 / 86,0 |
| Yungay | E41150 | 3.461, 71,3; 2,41 / 10,22; 77 / 308 | 939, 89,1; M61036 Schomberger; 2,41 / 1,79; 76,8 / 82,1 |
| Black Point / Meteor Crater | E19508 | 6.263, 76,8; 1,45 / 8,51; 58 / 225 | 4.401, 92,3; M59895 Casatus; 1,45 / 1,15; 57,8 / 44,2 |
| Mauna Kea | E25224 | 9.663, 69,6; 5,11 / 16,21; 136 / 456 | 5.280, 98,7; M62160 von Baeyer; 5,11 / 4,83; 135,6 / 137,3 |
| Craters of the Moon | E16626 | 5.823, 80,3; 2,53 / 11,95; 109 / 390 | 2.489, 97,3; M59580 Short; 2,53 / 3,09; 108,9 / 105,2 |

**Paneles solares** (propuesto: Luna entera, clave sin atmósfera; irradiancia sobre la atmósfera de la Tierra / suelo lunar; corregido en la comprobación): Bardenas 7,63 / 7,67 (gemelo junto a Schickard, 42,5 S; puesto 7.500 de 18.776); Tabernas 8,12 / 8,14 (Gadomski, 38,5 N; 6.263); MDRS 8,03 / 8,02 (Alexander, 39,5 N; 5.474); Yungay 9,16 / 9,14 (Piccolomini, 28,5 S; 3.643); Black Point 8,30 / 8,25 (Riccius, 37,5 S; 4.203); Mauna Kea 9,45 / 9,46 (Blanchinus, 24,5 S; 6.492); Craters of the Moon 7,53 / 7,54 (Jenner, 43,5 S; 7.656); Concordia 4,43 / 4,48 (Sommerfeld, 64,5 N; 11.721). Haughton no pasa el embudo solar. Con los mares solo sobreviven Yungay (Milne; 3.177 de 6.360) y Mauna Kea (Humboldt; 5.054). Hoy todos tienen gemelo en el polo sur con 0,20-2,38 kWh/m²/día en el gemelo (0,20 Craters of the Moon, 0,74 Concordia, 1,80-2,38 los demás) frente a 3,7-6,0 en el suelo de la Tierra.

**Base lunar**: Tabernas, MDRS, Black Point y Craters of the Moon no sobreviven en ninguna zona (hueco de amplitud mínimo 8,8-15,1 K, de temperatura > 40 K); Yungay sobrevive solo con la opción 1 (amplitud 34,44 / 33,69 K, gemelo junto a Haworth, puesto 17 de 74). Haughton, Bardenas, Mauna Kea y Concordia no pasan el embudo de Base lunar.

## E. Recomendación por misión y consecuencias

**Rover: aplicar el método con la zona del polo sur.** Cumple P1, P2, P5 y P6 con las tolerancias del propio equipo y mantiene el relato de Artemis. Consecuencias: 145 puntos (1,4 %) se quedan sin par (los más lisos: pendiente mediana 0,56°, rugosidad 18,6 m); cambia el número 1 (de E5128, isla Devon, a E17566, Mongolia Interior; E5128 pasa al puesto 345); ninguno del top 10 de hoy sigue en el top 10 (pasan a los puestos 140-1.040); Spearman del final con el de hoy 0,47. El gemelo más compartido reúne el 19,9 % (hoy 8,7 %). La web diría: "Pendiente y rugosidad del gemelo a menos de 2° y 30 m de las del punto (medidas a escala de kilómetros); la temperatura no se parece y se enseña la diferencia." La Luna entera también cumple, pero da similitud ~100 a casi todos y saca el gemelo del polo sur.

**Paneles solares: Luna entera con la irradiancia sin atmósfera como clave.** Es la única opción con casi todos los puntos emparejados (18.776 de 18.777) y similitud a favor de la idoneidad (+0,62). Los mares ecuatoriales solo emparejan un tercio (6.360); el polo sur, ninguno. Consecuencias: 1 punto sin par; cambian los gemelos de los 18.776 que lo conservan; número 1 de E44120 (Western Cape) a E38464 (Kimberley, Australia), y E44120 pasa al puesto 2.905; 0 de 10 del top 10 de hoy se mantienen (pasan a los puestos 936-2.905); Spearman del final con hoy 0,77; Spearman similitud-idoneidad de −0,92 (paquete publicado) a +0,62. **El texto de limitación de anoche se sustituye por**: "For solar arrays the twin is the lunar place that receives the same sunlight above the atmosphere: the same daily energy on a level surface (here 9.6 kWh/m²/day). On Earth the atmosphere lets only part of it through (6.2 kWh/m²/day at this site, 64 %; about 58 % at the median solar site); on the Moon all of it reaches the ground, in a 14.75-day day followed by a 14.75-day night. Temperatures do not match and are shown as a difference." (*Traducción:* "Para los paneles, el gemelo es el lugar lunar que recibe la misma luz por encima de la atmósfera: la misma energía diaria sobre una superficie horizontal (aquí 9,6 kWh/m²/día). En la Tierra la atmósfera solo deja pasar una parte (6,2 kWh/m²/día en este sitio, el 64 %; alrededor del 58 % en el sitio solar mediano); en la Luna llega toda al suelo, en un día de 14,75 días seguido de una noche igual. Las temperaturas no coinciden y se enseñan como diferencia.") Las cifras del ejemplo son las del número 1 (E38464); la web debe ponerlas por par. La versión anterior decía "about 58 % of it (6.1 at this site)", que no cuadra: 6,1 de 9,67 es el 63 %. La alternativa de mares (si el equipo prefiere una zona con nombre) deja sin par a 12.417 puntos.

**Base lunar: decisión del equipo entre las opciones 1-4 de D.3.** Con el principio tal cual, los 2.419 pares desaparecen. Ninguna opción conserva "similitud térmica" con valores parecidos en las regiones de Artemis.

**Coste**: una función de similitud nueva en `engine/repo_similarity.py` (o junto a ella) y tres bloques de configuración (variables, τ, pesos, zona); rehacer `similarity.json`/`twins.json` y los textos. Estimación: 1-2 h más la reconstrucción; Base lunar depende de la opción.

## Puntos abiertos

- Las tolerancias que no son del equipo (elevación 500 m, irradiancia 0,6, temperatura 10 K, amplitud 5 K) siguen una regla propia (media escala robusta de la Tierra); son una decisión del equipo. Las del Rover son las de `rover_preset.py`, marcadas allí "ILUSTRATIVO".
- La irradiancia de la Tierra sobre la atmósfera se calcula con una fórmula (latitud, oblicuidad 23,44°, excentricidad 0,0167 con la órbita de Kepler, 1.361 W/m²; la media anual sale igual en los dos hemisferios), no es un dato medido; en la Luna por encima de 65,5° la tabla usa la iluminación topográfica de LOLA.
- Con la Luna entera la similitud satura (mediana 99,8-99,9): ordena casi solo la idoneidad. Si se quiere que la similitud distinga, hay que estrechar las tolerancias o restringir la zona.
- La concentración del Rover en el polo sur sube (M61116, 19,9 %); la regla de no limitar por gemelo (decisión 4) seguiría valiendo.
- Opción 3 de Base lunar (terreno en Artemis) no calculada.
- No se ha ejecutado el motor ni se ha comprobado nada en `app/`.

## Comprobación

Segundo agente, 15-11-2026, con código propio en `scratchpad/stars/principle-check/` (`ctx.py`, `a_check.py`, `b_check.py`, `method.py`, `e_check.py`, `gaps.py`, `rover_extra.py`, `altw.py`, `solar_wtoa.py`; salidas `*.json`, `m_*.csv`, `log_*.txt`). No importa nada de `principle/`. Los pares de hoy se han leído **directamente del paquete publicado** (`app/public/data/v2`, columnas `twin`, `similarity`, `suitability`, `final` y `rank` de `earth_<misión>.bin` según `manifest.json`), no de una reimplementación; el método propuesto se ha programado a partir del texto de la sección C.

**Recalculado y correcto tal como estaba:**

- Sección A completa (medianas, percentiles 90, razones y porcentajes dentro de tolerancia, también con similitud ≥ 90), en las tres misiones; P5: 0 % de pares de Rover con pendiente y rugosidad a la vez dentro de 2° y 30 m. El número 1 de hoy (E5128 con M60952: 0,88° / 34,5 m frente a 6,19° / 198,7 m). Nota: con la similitud redondeada a 0,01 del paquete salen 7.480 pares de Paneles con similitud ≥ 90; los 7.474 del texto son con la similitud sin redondear (11 pares están entre 89,99 y 90,01).
- Sección B: pendiente, rugosidad, elevación relativa, temperatura media (hueco de 14,3 K; E6261 a 238,1 K y M29262 a 223,9 K; máximos por zona), amplitud (solape 30,7-35,7 K; 21 celdas de la Tierra, 11 lunares, todas a 87,5 S y 41-43 K, ninguna en Artemis), temperatura mínima (hueco de 86,8 K), irradiancia en el suelo (rango, OVL, banda lunar de 52,5-74,5° con 14.975 celdas, ninguna en los mares ni en el polo sur; mares 9,05-10,40; polo sur máximo 2,475), la fórmula lunar (error máximo 0,0023 por debajo de 60°) y la geometría solar.
- Las equivalencias en z de todas las tolerancias (escalas robustas: pendiente 1,041 / 3,248; rugosidad 42,28 / 92,01; elevación 1.007 / 1.769; temperatura 21,49 / 32,29; amplitud 6,60 / 47,84; irradiancia en el suelo 1,22 / 4,56), salvo la del tope de la atmósfera (corregida abajo).
- Las líneas citadas: `analog_finder.py` 285-286 (texto idéntico) y `rover_preset.py` (versión 3) 196-205, `tolerances_by_baseline` con 5° / 10 m a 300 m y 2° / 30 m a 5 km, marcadas "ILUSTRATIVO".
- Las cifras de "dominante" (82,7; 68,5; 0,875 → |Δ| ≤ 0,517 τ; alternativa 71,2 / 73,8 / 0,85).
- Rover, las tres zonas, exactamente: supervivientes (10.192 / 10.337 / 6.006), gemelos distintos (401 / 3.647 / 145), mayor cuota, similitud (salvo el p10 de la Luna entera, 99,5 y no 99,6), Spearman, top 10 con sus valores, sensibilidad a ×0,5 y ×2 (también solo claves; solo pendiente 10.146, solo rugosidad 8.750), similitud ≥ 90 (6.146; 0,36 / 0,84°, 3,7 / 10,0 m, 105 / 360 m) y los sitios conocidos en la propuesta. Consecuencias: 145 puntos sin par (0,56°, 18,6 m), E5128 al puesto 345, top 10 de hoy a 140-1.040, Spearman 0,47 con el final de hoy, cuota 19,9 % frente a 8,66 % hoy.
- Paneles con la irradiancia **en el suelo** (las tres zonas) y el punto sin par E19334; Paneles en el polo sur con la clave sin atmósfera (0).
- Base lunar con temperatura y amplitud: 0 pares en Artemis, polo sur y Luna entera, también al doble (y a la mitad); huecos mínimos y medianos de temperatura (96,6 / 121,3; 91,8 / 116,5; 40,2 / 64,9 K) y de amplitud. Solo amplitud: 74 pares en el polo sur y en la Luna entera, 0 en Artemis, 7 gemelos, 73 %, Spearman +0,66, sensibilidad 23 (30) / 74 / 779 (367), los 22 pares con similitud ≥ 90 y Yungay (puesto 17, 34,44 / 33,69 K). Los sitios que no pasan el embudo y los huecos de amplitud de Tabernas, MDRS, Black Point y Craters of the Moon (15,1 / 11,1 / 8,8 / 13,2 K).
- La respuesta a P4 se sigue de los números: con temperatura exigida parecida no hay ningún par en ninguna zona porque ningún candidato está a menos de 40,2 K de ninguna celda lunar (y la tolerancia es 10 K, o 20 K al doble).
- En `docs/DECISIONS.md` P1-P9 están completos y fieles al texto de Facundo; ningún texto presenta el método como decidido o implementado.

**Corregido:**

1. **Irradiancia de la Tierra en el tope de la atmósfera** (afecta a toda la propuesta de Paneles). La fórmula usada tomaba la longitud solar uniforme en el tiempo pero la distancia al Sol según el perihelio de enero; eso crea una asimetría falsa entre hemisferios de hasta ±0,10 kWh/m²/día (más baja en el norte, más alta en el sur: 5,52 frente a 5,71 a ±60,5°; Concordia 4,54 en lugar de 4,43). Con la órbita de Kepler la media anual es igual en los dos hemisferios (comprobado también con una integración hora a hora: 9,974 / 9,644 / 8,765 / 7,367 / 5,672 / 4,137 a 0 / 15,5 / 30 / 45 / 60 / 89,5°). Con la fórmula antigua reproduzco las cifras anteriores del texto (5.756 gemelos, M9016 con 1.776, el mismo top 10), así que la diferencia es solo esta fórmula. Cambios: número 1 de Paneles E38464 con M24296 (antes E38105 con M24769, ahora número 2); gemelos distintos 5.811 (antes 5.758); mayor cuota M8436, 8,1 % (antes M9016, 9,5 %); similitud mínima / p10 87,5 / 98,6 (antes 93,0 / 98,1); mares 6.360 supervivientes (antes 6.251), 1.704 gemelos, M21795 159 (2,5 %), Spearman +0,16, sin par 12.417 (antes 12.526); sensibilidad de los mares 5.498 / 6.360 / 7.425; hueco en el polo sur 1,66 / 4,29 (antes 1,77 / 4,21); diferencias con similitud ≥ 90; E44120 al puesto 2.905 (antes 2.983); top 10 de hoy a los puestos 936-2.905; alternativa de pesos 1.352 de 18.776 y 112 de 6.360 (antes 1.185 y 130); en la sección B, percentiles del tope de la atmósfera (4,15 / 6,19 / 9,93), valores por latitud (8,77 / 7,37 / 5,67 en lugar de 8,71 / 7,29 / 5,58), fracción que llega al suelo (54,0 %, 42,4-88,5 %; candidatos 57,7 %), escala 3,32 y z 0,18 (antes 0,19); los valores de los sitios conocidos. No cambian los supervivientes de la Luna entera (18.776) ni su Spearman (+0,62).
2. **Correlación similitud-idoneidad de hoy en Paneles**: −0,92 con el paquete publicado (y con los pares de hoy del propio autor), no −0,68; el −0,68 venía de la decisión 5, calculado antes del tratamiento definitivo de la temperatura que falta. (Las secciones de la decisión 5 en `DECISIONS.md` y el texto de limitación citado allí siguen diciendo −0,68; no las he tocado porque son el registro de anoche, pero el número no es el del paquete publicado.)
3. **Base lunar, solo amplitud**: los 74 pares no están "todos en la Puna y el Altiplano" con amplitudes de 30,8-34,4 K: 37 están en los Andes centrales y 37 en el Tíbet, Qaidam e Irán, con amplitudes de 25,7-35,3 K (la tolerancia es 5 K). La amplitud sola se iguala en 126 candidatos; las secundarias dejan 74.
4. **P4**: el 99,96 % es la cifra en z; en valor absoluto el 100 % de los candidatos es más cálido que cualquier celda de Artemis (264,1 K frente a 167,5 K).
5. **Puestos de hoy de los sitios conocidos en Rover**: los del paquete publicado son 79, 6.048, 7.103, 5.197, 3.461, 6.263 y 9.663 (Haughton, Bardenas, Tabernas, MDRS, Yungay, Black Point, Mauna Kea), no 80, 6.049, 7.107, 5.192, 3.462, 6.264 y 9.662. Gemelos de hoy de Paneles en esos sitios: 0,20-2,38 kWh/m²/día (Craters of the Moon 0,20; Concordia 0,74), no 1,79-2,38.
6. **Texto de limitación de Paneles**: decía "about 58 % of it (6.1 at this site)", cuando 6,1 de 9,67 es el 63 %; reescrito con el par número 1 corregido (6,2 de 9,6, el 64 %; 58 % en el sitio mediano).
7. Menores: "15 a 17 veces" → unas 17 veces (razón mediana 0,057); p10 del Rover en la Luna entera 99,5; mares, supervivientes a 33,5° o menos del ecuador (no 34,5°); cuota de M59715 en el suelo 1.662; alternativa de pesos del Rover en la Luna entera 1.775 (no 1.776; empate numérico).
8. **Añadido** (no era un error de cifras, pero cambia la implementación): la elevación relativa del documento no es la que exporta el motor (sección C); con la del motor el Rover en el polo sur cambia (10.145 supervivientes, 281 gemelos, 48,6 % en M59895, otro número 1). Y dos tolerancias no siguen la regla declarada (amplitud 5 K en lugar de 3,3 K; irradiancia con la escala del suelo para una variable del tope de la atmósfera). Las dos cosas son decisiones del equipo.
9. Fecha y hora del principio: en `DECISIONS.md` decía solo 04:47; ahora 04:47-04:49 CET. En `ASSUMPTIONS.md` §0.11 se añade el resumen de P1-P9 punto por punto y las cifras corregidas.

**No he podido comprobar:**

- La opción 3 de Base lunar (terreno en las regiones de Artemis): tampoco la calculó el autor.
- Que el motor, con el método implementado, dé estas cifras: no se ha implementado ni ejecutado nada, y no he mirado `app/`.
- Las regiones de Artemis: uso la misma lista de 280 celdas (`proposal-verify/out/regions.json`) que el autor; no he vuelto a cruzar las huellas de NASA con la malla.
- El OVL depende del número de clases del histograma (con 50 clases coincide; con 200 la irradiancia en el suelo baja a 0,23 y la del tope de la atmósfera a 0,33).
- Que la definición de amplitud de la Tierra (10:30 − 22:30) y la de la Luna (máximo − mínimo) sean comparables: solo se repite la advertencia del autor.

## Resultado tras implementar (15-11-2026)

**Decidido y aplicado** (respuesta de la persona delegada en nombre del líder del equipo, 15-11-2026 por la mañana; registro en `docs/DECISIONS.md`, "Decisiones tomadas (15-11-2026, mañana)"): Rover y Paneles solares usan la similitud sobre valores reales de la sección C (regla `real_value_tolerance`, motor 3.1.0, `tierra luna/engine/real_similarity.py`; variables, pesos, tolerancias y zonas en `engine_config.json` `real_value_similarity`). **Base lunar no cambia** (regla `zone_twin` en z sobre las nueve regiones de la NASA; sus archivos son idénticos a los del paquete anterior) y queda **pendiente** de una propuesta nueva que el equipo tiene que confirmar antes de reconstruirla. Paquete reconstruido: `app/public/data/v2` (revisión 5 del contrato). Todas las cifras de esta sección salen del motor (`compute()` del paquete publicado), no de los scripts de la propuesta; coinciden con la propuesta comprobada.

Cambios respecto a la propuesta de la sección C: la zona de Paneles solares es la de los **mares ecuatoriales** (decisión del equipo; la propuesta recomendaba la Luna entera); la elevación relativa es la centrada (definición de la comprobación); la irradiancia de la Tierra en el tope de la atmósfera es la de la fórmula corregida (9,97 / 8,77 / 7,37 / 5,67 kWh/m²/día a 0 / 30 / 45 / 60°; el motor da 9,9743 / 8,7651 / 7,3667 / 5,6717).

**Recuentos.**

| misión | zona (celdas) | puntos que pasan el embudo | con gemelo | sin gemelo (motivo más común) | gemelos distintos | gemelo más compartido |
|---|---|---|---|---|---|---|
| Rover | polo sur, latitud ≤ −75° (5.400) | 10.337 | **10.192** (98,6 %) | 145: 76 sin ninguna celda que cumpla a la vez las dos claves y la secundaria, bloqueados por la rugosidad (la más cercana a 30,0-51,1 m), y 69 bloqueados por la elevación relativa (a 1.003-1.267 m); cada variable por separado sí encuentra celda | 401 | M61116 (79,5 S 96,5 E, Ganswindt a 81 km): 2.033 puntos, 19,9 % |
| Paneles solares | mares ecuatoriales, \|latitud\| ≤ 30° y elevación ≤ −1.200 m (6.686) | 18.777 | **6.360** (33,9 %) | 12.417: 12.416 porque ninguna celda de los mares tiene la irradiancia sin atmósfera a menos de 0,6 kWh/m²/día (hueco mínimo 0,66, mediano 4,15); 1 por la rugosidad a la vez (60,4 m frente a 60) | 1.704 | M21795 (29,5 N 15,5 E, Banting a 92 km): 159 puntos, 2,5 % |
| Base lunar (sin cambios) | las nueve regiones candidatas de la NASA (280) | 2.419 | 2.419 | 0 | 48 | M62515: 671 puntos, 27,7 % |

**La comprobación que pidió Facundo a las 04:48** (P5, P6): diferencia absoluta en valores reales entre cada punto de la Tierra y su gemelo, solo en los pares que sobreviven. Ninguna variable clave pasa de su tolerancia y ninguna secundaria del doble de la suya (columna "máximo", con los decimales necesarios para que no parezca redondeado a la cota); lo comprueba un test en cada par (`tests/test_real_value_similarity.py::test_every_surviving_pair_is_within_its_bounds`, en el motor en doble precisión y en el paquete).

**Rover** (10.192 pares; temperatura y amplitud solo donde la Tierra tiene dato: 9.091 pares, sin la Antártida):

| variable | papel | tolerancia | cota del filtro | n | mediana | P90 | máximo | ¿máximo ≤ cota? |
|---|---|---|---|---|---|---|---|---|
| pendiente (°) | clave | 2,0 ° | 2,0 ° | 10.192 | 0,41 | 0,85 | 1,97 | sí |
| rugosidad (m) | clave | 30 m | 30 m | 10.192 | 5,3 | 20,5 | 29,97 | sí |
| elevación relativa (m) | secundaria | 500 m | 1.000 m | 10.192 | 248 | 799 | 999,99 | sí |
| temperatura media (K) | información (no entra) | — | — | 9.091 | 148,7 | 175,6 | 233,0 | — |
| amplitud térmica diaria (K) | información (no entra) | — | — | 9.091 | 176,3 | 187,1 | 228,0 | — |
| irradiancia en el suelo (Tierra) / superficie (Luna) (kWh/m²/día) | información (no entra) | — | — | 10.191 | 2,36 | 4,03 | 6,05 | — |

**Paneles solares** (6.360 pares):

| variable | papel | tolerancia | cota del filtro | n | mediana | P90 | máximo | ¿máximo ≤ cota? |
|---|---|---|---|---|---|---|---|---|
| irradiancia sin atmósfera (kWh/m²/día) | clave | 0,6 kWh/m²/día | 0,6 kWh/m²/día | 6.360 | 0,021 | 0,322 | 0,570 | sí |
| pendiente (°) | secundaria | 2,0 ° | 4,0 ° | 6.360 | 0,03 | 0,15 | 1,94 | sí |
| rugosidad (m) | secundaria | 30 m | 60 m | 6.360 | 0,5 | 2,4 | 58,1 | sí |
| temperatura media (K) | información (no entra) | — | — | 6.360 | 84,7 | 89,9 | 100,2 | — |
| amplitud térmica diaria (K) | información (no entra) | — | — | 6.360 | 275,8 | 287,3 | 293,1 | — |

En Paneles solares, la luz que llega al suelo en la Tierra (no entra en la similitud; va en cada par): mediana 5,14 kWh/m²/día de 9,45 sobre la atmósfera; se pierde en la atmósfera una mediana del 45,3 % (P90 57,4 %, máximo 67,5 %). La temperatura y la amplitud no se parecen y no se presentan como parecidas: se enseñan como diferencia.

**Top 5 por misión** (valores reales Tierra / gemelo).

Rover (pendiente en °, rugosidad en m, elevación relativa en m):

| # | punto de la Tierra | idoneidad | similitud | final | gemelo | pendiente T / L | rugosidad T / L | elevación relativa T / L |
|---|---|---|---|---|---|---|---|---|
| 1 | E17566, 41,5 N 106,5 E (Mongolia Interior, China) | 99,22 | 99,57 | 99,39 | M59895, 76,5 S 44,5 O (Casatus a 159 km) | 1,038 / 1,148 | 43,53 / 44,20 | 737,5 / 833,3 |
| 2 | E23945, 23,5 N 5,5 E (Tamanrasset, Argelia) | 98,66 | 99,76 | 99,21 | M59895 | 1,215 / 1,148 | 43,37 / 44,20 | 761,9 / 833,3 |
| 3 | E18282, 39,5 N 102,5 E (Mongolia Interior, China) | 99,58 | 98,77 | 99,17 | M59895 | 0,908 / 1,148 | 38,75 / 44,20 | 747,7 / 833,3 |
| 4 | E18280, 39,5 N 100,5 E (Gansu, China) | 98,66 | 99,50 | 99,08 | M59895 | 1,131 / 1,148 | 48,91 / 44,20 | 851,5 / 833,3 |
| 5 | E15395, 47,5 N 95,5 E (Govi-Altái, Mongolia) | 98,69 | 99,12 | 98,91 | M59895 | 1,236 / 1,148 | 41,33 / 44,20 | 962,5 / 833,3 |

Información, no entra en la similitud (número 1): temperatura 284,7 K frente a 142,5 K; amplitud diaria 20,6 K frente a 196,6 K; irradiancia en el suelo 4,58 frente a 1,77 kWh/m²/día.

Paneles solares (irradiancia sin atmósfera en kWh/m²/día, entre paréntesis la que llega al suelo en la Tierra y la parte perdida; pendiente en °, rugosidad en m):

| # | punto de la Tierra | idoneidad | similitud | final | gemelo | irradiancia sin atmósfera T / L | pendiente T / L | rugosidad T / L |
|---|---|---|---|---|---|---|---|---|
| 1 | E38464, 16,5 S 124,5 E (Kimberley, Australia) | 96,90 | 99,99 | 98,45 | M24296, 22,5 N 3,5 O (Huxley a 76 km) | 9,600 (suelo 6,18; −35,7 %) / 9,604 | 0,976 / 1,047 | 39,20 / 39,03 |
| 2 | E38105, 15,5 S 125,5 E (Kimberley, Australia) | 96,90 | 99,88 | 98,39 | M24583, 21,5 N 76,5 O (Struve a 58 km) | 9,644 (suelo 6,11; −36,6 %) / 9,672 | 1,132 / 1,038 | 42,53 / 44,43 |
| 3 | E38744, 17,5 S 44,5 E (Melaky, Madagascar) | 96,77 | 99,95 | 98,36 | M40854, 23,5 S 5,5 O (Thebit a 61 km) | 9,554 (suelo 5,97; −37,5 %) / 9,534 | 0,706 / 0,649 | 29,64 / 29,00 |
| 4 | E37746, 14,5 S 126,5 E (Kimberley, Australia) | 96,62 | 99,98 | 98,30 | M24761, 21,5 N 101,5 E (Dziewulski a 72 km) | 9,685 (suelo 6,07; −37,3 %) / 9,672 | 0,757 / 0,711 | 26,93 / 27,55 |
| 5 | E38465, 16,5 S 125,5 E (Kimberley, Australia) | 96,48 | 100,00 | 98,24 | M40406, 22,5 S 93,5 O (Rimae Pettit a 83 km) | 9,600 (suelo 6,14; −36,0 %) / 9,604 | 0,920 / 0,951 | 33,25 / 32,92 |

Información (número 1): temperatura 302,4 K frente a 213,4 K; amplitud diaria 11,9 K frente a 293,4 K. Con la zona de los mares el top 5 coincide con el de la Luna entera de la sección D.2 salvo el gemelo del número 2 (Struve en lugar de Deutsch), como ya decía la propuesta.

**Base lunar sin cambios** (comprobado): `earth_lunar_base.bin` y `moon_lunar_base.bin` tienen el mismo sha256 que en el paquete anterior y la parte de Base lunar de `twins.json`, `explain.json` y `missions.json` es idéntica (`tests/test_real_value_similarity.py::test_lunar_base_is_unchanged_from_the_previous_bundle`). Facundo pidió a las 07:55 que Base lunar tenga análogos en la Tierra y que antes de reconstruirla se le mande una propuesta (variables, pesos y normalización, tolerancia, pares que sobreviven, número 1 y su gemelo, diferencias reales); esa propuesta se prepara aparte (`docs/LUNAR_BASE_PROPOSAL.md`) y no se ha aplicado nada.

**Tests:** `cd "tierra luna" && python -m pytest -q`: **140 passed** (123 antes + 17 nuevos en `tests/test_real_value_similarity.py`: regla por misión, nada tecleado en el código, fórmula del tope de la atmósfera, elevación relativa, zona de los mares, casos a mano del filtro, del empate y de los valores que faltan, orden de la lista, recuentos y número 1 de Rover y Paneles solares, cotas en cada par, Base lunar sin cambios, contenido del paquete, irradiancia en el suelo y texto de Paneles solares, recálculo exacto con otros pesos). Paquete `app/public/data/v2` y paquete de comparación `bundle_global_mean` construidos dos veces cada uno, idénticos byte a byte.

**Verificación independiente de la implementación (15-11-2026, tercer agente, código propio sin importar el motor: `scratchpad/verify5/indep.py`).** Desde las tablas reales y `mission_scoring.json` he recalculado para Rover y Paneles solares el embudo, las zonas (polo sur 5.400 celdas; mares 6.686 con la definición de `analog_finder`), la irradiancia sin atmósfera con un método propio (integral sobre la longitud solar con el peso de tiempo de Kepler: 9,9743 / 8,7651 / 7,3667 / 5,6717; diferencia con `d.irradiance_toa_kwh_m2_day` < 5·10⁻⁷), las medias de elevación (+695,9244 / −248,3894 m), el filtro, el gemelo, las puntuaciones, similitud, final, puesto, orden de la lista y el motivo de cada punto sin par; y he leído el paquete con numpy siguiendo solo `docs/DATA_CONTRACT.md`. **Coincide celda a celda** en `earth_<misión>.bin`, `earth_<misión>_pairs.bin` (incluido `atm.*`), `moon_<misión>.bin` `twin_count`, `twins.json`, `explain.json`, `lunar_named_sites.json` y los recuentos de `missions.json` y del manifiesto, y gemelo por gemelo con los CSV del comprobador en las dos misiones (también Paneles solares, que el autor no había comparado). La tabla de diferencias reales de arriba es correcta tal cual. Base lunar: idéntica al paquete anterior también en las columnas de las teselas (z y `lunar_base.*`), en la parte en z de `similarity.json`, en su zona, en `lunar_named_sites.json` y en los recuentos (2.419, 48 gemelos, M62515 con 671, número 1 E19345 con M62859, final 76,71). Corregido: (1) `variables.json` decía que la irradiancia de la Tierra en el suelo (nivel MODELLED, WorldClim) "is measured"; ahora dice que es una climatología modelada (`engine/datasets.json`); (2) la instrucción del hueco en `texts.no_twin_note` ("mismos decimales que la cota") hacía que 30,02 m se leyera "30,0 m, cota 30,0 m"; ahora: 2 decimales redondeados hacia arriba. Un test por cada corrección y otro que amplía la prueba de Base lunar sin cambios.

## Resultado tras implementar: Base lunar (15-11-2026)

**Decidido y aplicado** (la persona delegada, en nombre del líder del equipo, 15-11-2026 08:55 CET; registro en `docs/DECISIONS.md`): Base lunar usa la regla `percentile_and_real_tolerance` (motor 3.2.0; `tierra luna/engine/real_similarity.py`, `pipeline.py`; todo en `engine_config.json` `real_value_similarity.missions.lunar_base`). Claves: temperatura mínima (`tmin_k`) 40 % y amplitud térmica diaria (`lst_diurnal_amp_k`) 40 %, cada una en **percentil de rango medio dentro de su población** (Tierra: los 2.419 puntos que pasan el embudo de Base lunar; Luna: las 280 celdas de las nueve regiones de la NASA), tolerancia 10 puntos de percentil. Secundarias en **valor real**: pendiente 10 % (tolerancia 2°, cota 4°) y rugosidad 10 % (30 m, cota 60 m), los valores ilustrativos del equipo de `rover_preset.py`. Puntuación `exp(−0,5 (Δ/τ)²)`, similitud = 100 × media ponderada, filtro del par en las cuatro, gemelo = la celda que pasa el filtro con la similitud más alta (empate: id más bajo), final = 0,5 × similitud + 0,5 × idoneidad. La temperatura media y la elevación relativa salen de la similitud y se enseñan como diferencia. El embudo no cambia. **Es un parecido de posición térmica, no de temperatura**: cada par lleva su frase con la diferencia real (`similarity.json` `texts.lunar_base_pair_sentence`). En la Tierra la mínima es la temperatura del **aire modelada** por WorldClim (mes más frío); en la Luna, la temperatura de **superficie medida** por Diviner (mínimo nocturno). Rover y Paneles solares no cambian: sus archivos son idénticos byte a byte a los de la revisión 5 (`tests/test_real_value_similarity.py::test_rover_and_solar_are_byte_identical_to_revision_5`). Todas las cifras de esta sección salen del motor y del paquete publicado.

**Recuentos.**

| misión | zona (celdas) | puntos que pasan el embudo | con gemelo | sin gemelo, por motivo | gemelos distintos | gemelo más compartido |
|---|---|---|---|---|---|---|
| Base lunar | nueve regiones de la NASA cerca del polo sur (280) | 2.419 | **450** (18,6 %) | 1.969: 943 por terreno (ninguna celda con pendiente a ≤ 4° y rugosidad a ≤ 60 m), 237 por posición térmica (ninguna celda con las dos claves a ≤ 10 puntos), 196 por las dos cosas y 593 porque ninguna celda cumple las dos a la vez; 0 sin dato | **103** | M62848 (84,5 S 28,5 E, Mons Mouton a 7,8 km, región Mons Mouton Plateau): 25 puntos, **5,6 %** |

Esperado (propuesta comprobada) frente a obtenido: 450 / 450 pares; 103 / 103 gemelos; M62848 con 25 (5,6 %) / igual; número 1 E17538 – M63528, similitud 97,3 y final 72,3 / 97,31 y 72,29; motivos 943 / 237 / 196 / 593 / iguales. Los 450 gemelos son los del CSV del comprobador uno a uno; el puesto difiere en 56 pares porque el motor ordena por el final publicado (2 decimales, empates por id).

**La comprobación pedida tras cada cambio de método** (diferencia absoluta Tierra − gemelo en los 450 pares que sobreviven). Ninguna clave pasa de su tolerancia y ninguna secundaria de su cota en ningún par (columna "máximo"; test `tests/test_lunar_base_position.py::test_every_pair_is_within_its_tolerance_or_bound`, en el motor en doble precisión y en el paquete).

| variable | papel | tolerancia | cota del filtro | n | mediana | P90 | máximo | ¿máximo ≤ cota? |
|---|---|---|---|---|---|---|---|---|
| temperatura mínima, posición (puntos de percentil) | clave | 10 | 10 | 450 | 3,17 | 7,72 | 9,79 | sí |
| temperatura mínima, valor real (K) | (clave en posición) | — | — | 450 | 207,88 | 210,55 | 211,94 | — |
| amplitud diaria, posición (puntos de percentil) | clave | 10 | 10 | 450 | 2,99 | 7,67 | 9,95 | sí |
| amplitud diaria, valor real (K) | (clave en posición) | — | — | 450 | 153,77 | 161,28 | 179,40 | — |
| pendiente (°) | secundaria | 2 ° | 4 ° | 450 | 1,51 | 2,69 | 3,92 | sí |
| rugosidad (m) | secundaria | 30 m | 60 m | 450 | 27,27 | 54,43 | 59,81 | sí |
| temperatura media (K) | información (no entra) | — | — | 450 | 162,71 | 181,19 | 200,65 | — |
| elevación relativa (m) | información (no entra) | — | — | 450 | 2.497 | 4.654 | 6.163 | — |
| irradiancia en el suelo (kWh/m²/día) | información (no entra) | — | — | 450 | 4,08 | 4,63 | 5,38 | — |

Las dos claves coinciden en **posición**, no en valor: en valor real el gemelo está unos 208 K más frío en la mínima y su amplitud es unos 154 K mayor (en todos los pares el gemelo es más frío de media y oscila más; comprobado por un test). Lo que sí se parece en valor real es el terreno.

**Top 5** (valores reales Tierra / gemelo; mínima en K, entre paréntesis en °C; percentil Tierra / gemelo).

| # | punto de la Tierra | idoneidad | similitud | final | gemelo (región NASA) | mínima T / L | percentil mínima | amplitud T / L (K) | percentil amplitud | pendiente T / L (°) | rugosidad T / L (m) | T media T / L (K) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E17538, 41,5 N 78,5 E (Xinjiang, China; Tian Shan) | 47,27 | 97,31 | 72,29 | M63528, 86,5 S 11,5 O, Mons Malapert a 25 km (Haworth) | 248,61 / 41,23 (−24,5 / −231,9 °C) | 8,37 / 8,04 | 15,60 / 153,27 | 6,72 / 10,18 | 6,652 / 7,179 | 238,81 / 238,49 | 272,06 / 77,49 |
| 2 | E16830, 43,5 N 90,5 E (Xinjiang, China) | 47,96 | 96,61 | 72,28 | M63841, 87,5 S 58,5 O, Cartwright a 16 km (de Gerlache Rim 2) | 254,29 / 46,11 (−18,9 / −227,0 °C) | 21,48 / 18,75 | 18,01 / 172,62 | 33,09 / 32,50 | 3,066 / 4,151 | 118,63 / 128,19 | 282,43 / 98,73 |
| 3 | E15751, 46,5 N 91,5 E (Hovd, Mongolia) | 46,60 | 96,86 | 71,73 | M64018, 87,5 S 118,5 E, Slater a 19 km (Slater Plain) | 247,30 / 40,65 (−25,9 / −232,5 °C) | 5,85 / 6,61 | 16,04 / 153,31 | 11,64 / 10,54 | 4,673 / 6,260 | 164,12 / 167,90 | 273,78 / 79,66 |
| 4 | E21054, 31,5 N 5,5 O (Souss-Massa-Draa, Marruecos; Alto Atlas) | 43,91 | 99,36 | 71,63 | M62517, 83,5 S 57,5 E, Wapowski a 18 km (Nobile Rim 2) | 271,63 / 63,03 (−1,5 / −210,1 °C) | 62,73 / 62,68 | 18,71 / 176,89 | 41,86 / 43,39 | 3,257 / 3,481 | 119,49 / 115,01 | 293,19 / 130,40 |
| 5 | E17187, 42,5 N 87,5 E (Xinjiang, China) | 47,54 | 95,03 | 71,28 | M62523, 83,5 S 63,5 E, Oberbeck a 16 km (Nobile Rim 2) | 254,80 / 47,00 (−18,4 / −226,2 °C) | 23,17 / 22,32 | 18,16 / 174,60 | 34,93 / 37,68 | 4,665 / 6,214 | 173,53 / 161,62 | 281,89 / 89,59 |

Frase del número 1 en la web (plantilla rellenada; `explain.json`): "This pair matches by relative thermal position, not by equal temperatures: this site's coldest temperature and daily swing rank among Earth's lunar-base candidates where its twin's rank among the cells of NASA's nine candidate landing regions near the lunar south pole. In real values the twin is 195 K colder on average (minimum -232 °C at the surface against -24.5 °C air temperature here) and its day-night swing is 138 K larger; slope differs by 0.5° and roughness by 0.3 m."

**Regiones lunares (nuevo en la revisión 6).** Cada celda lunar lleva su región (`moon_base.bin` `region`; `mission_zones.json`): A las nueve regiones de la NASA 280, B resto del polo sur 5.120, C polo norte 5.400, D llanuras ecuatoriales bajas 6.686, E cara oculta 25.971, F resto 21.343; las zonas de las misiones son exactamente Rover = A + B, Paneles solares = D, Base lunar = A (test). Los textos "por qué aquí no" se copian tal cual de `tierra luna/engine/mission_zone_texts.json` (agente de textos de zonas); cuando se construyó este paquete el archivo ya existía y estaba completo, así que `mission_zones.json` lleva los textos (el manifiesto lo dice en `mission_zone_texts`); si el agente lo cambia, basta reconstruir.

**Tests:** `cd "tierra luna" && python -m pytest -q`: **168 passed** tras la verificación independiente (164 antes de ella, 144 antes de Base lunar; la verificación añadió 4 tests; nuevos `tests/test_lunar_base_position.py`, 14, y los de `tests/test_mission_zone_texts.py` del agente de textos; adaptados a la revisión 6 `test_real_value_similarity.py`, `test_real_data.py` y `test_verification_fixes.py`). Paquete `app/public/data/v2` y paquete de comparación `bundle_global_mean` construidos dos veces cada uno, idénticos byte a byte.



## Resultado tras las decisiones de las 11:23

Decisiones de la persona delegada en nombre del líder del equipo, 2026-11-15 11:23 CET (registro completo en `docs/DECISIONS.md`): Rover compara solo pendiente y rugosidad, 50 % cada una, las dos clave (tolerancias 2° y 30 m); la elevación relativa sale de la similitud y del filtro del par y queda como fila informativa; los cinco mostrados de Rover y Paneles solares se eligen con una separación de 2° de arco (unos 222,4 km); la pendiente mínima de 0,5° de Rover se mantiene (justificada con datos en `DECISIONS.md`). Motor 3.3.0, revisión 7 del contrato. Cifras del motor y del paquete publicado.

### Rover antes y después

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

Lectura: con solo pendiente y rugosidad, el polo sur lunar tiene casi siempre una celda que iguala a cada punto de la Tierra (diferencia mediana 0,03° y 0,5 m), así que **la similitud de Rover también queda saturada**: 74 puntos llegan a un final de 100,00 y la cabeza del ranking la decide la idoneidad (los cinco mostrados tienen idoneidad 100) y, dentro del empate, el id de celda. Los cinco mostrados son ahora altas latitudes del Ártico (Taimyr y el archipiélago canadiense) con gemelos variados (Drygalski, Sverdrup, Haynes, Schrödinger) en lugar de cinco puntos de Asia central y del Sáhara con el mismo gemelo (Casatus). Los análogos conocidos de movilidad caen en el percentil 3,6 a 8,1 % (Ramon 3,6, Qaidam 4,0, Haughton 4,2, Yungay 8,1), frente a 0,2 a 9,2 % antes.

## Resultado tras las decisiones de las 11:28, 11:36 y 11:51 (15-11-2026)

Paquete publicado (revisión 8). Coordenadas = centro de celda; final = 50 % similitud + 50 % idoneidad.

| Misión | Pasan | Emparejados | Gemelos distintos | Regla de los cinco |
|---|---|---|---|---|
| Rover | 10.337 | 10.337 | 1.144 | dispersión entre los 254 empatados (241 sin hielo ni agua) |
| Paneles solares | 18.777 | 6.360 | 1.704 | rango con saltos y 2° |
| Base lunar | 2.419 | 450 | 103 | rango con saltos y 2° |

**Rover** (pendiente y rugosidad Tierra / Luna y diferencias en `earth_rover_pairs.bin`; todos con similitud 100,00, idoneidad 100,00, final 100,00): E4037 (78,5, −102,5) gemelo M63714; E50510 (−50,5, −69,5) M59438; E44239 (−32,5, 139,5) M59712; E26510 (16,5, 50,5) M63711; E26087 (17,5, −12,5) M61294. Alternativa por rango con saltos: E4037, E4742, E4751, E4962, E5125 (todos 100,00, rangos 3, 6, 9, 10, 15).

**Paneles solares**: E40184 (−21,5, 44,5) M23206 sim 99,83 id 97,94 final 98,88; E29749 (7,5, 49,5) M26063 99,97 / 97,56 / 98,76; E23648 (24,5, 68,5) M22156 99,93 / 97,20 / 98,56; E29746 (7,5, 46,5) M26056 99,97 / 97,08 / 98,52; E28670 (10,5, 50,5) M25483 99,94 / 96,81 / 98,37.

**Base lunar**: E21054 (31,5, −5,5) M62517 sim 99,36 id 44,64 final 72,00; E17538 (41,5, 78,5) M63528 97,31 / 43,15 / 70,23; E21833 (29,5, 53,5) M62515 92,50 / 47,25 / 69,87; E18627 (38,5, 87,5) M62479 83,98 / 55,63 / 69,80; E19672 (35,5, 52,5) M63657 93,33 / 46,12 / 69,73.

Los valores reales lado a lado y las diferencias de cada pareja están en `earth_<misión>_pairs.bin` y en `explain.json`; no se repiten aquí. No calculado aquí: la estabilidad de los cinco (pendiente de la re-auditoría).

Veredictos de la reauditoría independiente del modelo corregido (15-11-2026): Rover GO final, Paneles solares GO final, Base lunar GO en los números; textos corregidos después (`docs/stats_audit/9_reauditoria_rover.md`, `9_reauditoria_solar.md`, `9_reauditoria_base.md` y sus `.json`; resumen en `docs/DECISIONS.md`, "Reauditoría independiente del modelo corregido"). La puntuación de Rover es la banda muerta (s = 1 dentro de la incertidumbre de los modelos de elevación, sigma 0,265093° y 17,401661 m); en Paneles solares la fracción de cielo despejado pesa la mitad de la idoneidad (0,35 de 0,70).
