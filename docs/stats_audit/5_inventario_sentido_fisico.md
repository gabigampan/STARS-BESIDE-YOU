# Auditoría 5: inventario de cada número (punto A) y sentido físico de cada variable (punto D)

Revisor independiente nº 5 (no he escrito nada del código revisado). Rama `final-integration`, motor en el commit `42d8bba` (`engine_version` 3.2.0, contrato revisión 6). Fecha: 15-11-2026. No he modificado nada del repositorio fuera de mis ficheros (`tierra luna/audit/p5_*.py`, `tierra luna/audit/out/p5_*`, `tierra luna/audit/out/inventory.csv` y este documento). No he consultado NASA POWER ni ninguna fuente externa: los puntos A y D se resuelven con el repositorio (`docs/sources/R1` a `R4`, ficheros de procedencia) y con cálculo propio. `docs/VALIDATION.md` no se ha usado como prueba.

## 0. Cómo se ha medido (y por qué las cifras son de un camino de código independiente)

- **Implementación propia** (`tierra luna/audit/p5_common.py`): embudo, utilidades, idoneidad, similitud sobre valores reales, filtro del par, percentiles de rango medio, gemelo, final y rango, escritos desde cero. No importa ningún módulo de `tierra luna/engine/` ni `mission_scoring.py`; lee solo las tablas reales, `mission_scoring.json`, `engine_config.json`, `datasets.json`, `real_data/column_aliases.json` y `engine/data/artemis_iii_regions.geojson`. La insolación sin atmósfera la integro por otra vía (anomalía verdadera con peso r², 20.000 pasos) que la del motor (anomalía media, Kepler iterado).
- **Comprobación contra el paquete publicado** (`p5_baseline.py` → `out/p5_baseline.json`): en las tres misiones mi conjunto de puntos que pasan el embudo es idéntico (Rover 10.337, Paneles 18.777, Base 2.419), los gemelos coinciden en el 100 % (0 diferencias: 10.192, 6.360 y 450 pares), el rango coincide en todos los puntos (0 diferencias) y la diferencia máxima con lo publicado es 0,00 en idoneidad, similitud y final. Zonas: 5.400, 6.686 y 280 celdas lunares. Medias de elevación de cada cuerpo (cos lat): Tierra 695,92 m, Luna −248,39 m. La vía con caché que usa `p5_sensitivity.py` (gemelo guardado por celda de la Tierra en las misiones de valores reales, por población en Base lunar) da también 0 diferencias de gemelo con el paquete (Rover y Base lunar comprobados) y el mismo resultado en dos llamadas.
- **Efecto de cada número** (`p5_sensitivity.py` → `out/p5_sensitivity_<misión>*.csv`): se ejecuta mi implementación con UN número quitado o perturbado cada vez (peso a cero; variable fuera de la similitud y del filtro; filtro duro quitado; umbral ×0,9 y ×1,1; tolerancia ×0,9 y ×1,1; multiplicador del filtro ×0,9 y ×1,1; límites de zona ×0,9 y ×1,1 y ±1°; constantes ×1,01; regla de percentil; α; redondeos) y se cuenta frente a la ejecución sin tocar: puntos que entran o salen del embudo, pares ganados, perdidos y con otro gemelo, y cuántos de los 5 y 50 primeros pares (punto de la Tierra, gemelo) se conservan y si el orden es el mismo. 79 perturbaciones en Rover, 108 en Paneles, 103 en Base lunar.
- **Inventario** (`p5_inventory.py` → `out/inventory.csv`): una fila por número. Parte anotada (cada número que puede actuar sobre un resultado o que ve el usuario: valor, unidad, clase de origen, origen registrado, dónde se lee en el código, efecto medido, bandera y propuesta) y parte automática (cada hoja numérica de los tres ficheros de configuración no cubierta por la anotada, con las líneas del código que leen su clave y la regla que la clasifica) y las constantes de módulo de los constructores de tablas.
- **Números mostrados** (`p5_shown_numbers.py` → `out/p5_shown_numbers.csv` y `_summary.json`): cada número de los textos del paquete, de los subtítulos de los tres vídeos y de las 19 transcripciones, y si se puede trazar a un número del fichero del que salió.
- **Sentido físico** (`p5_physical.py` → `out/p5_physical.json`): saturación de cada utilidad, correlaciones entre utilidades y con la latitud, parte de la dispersión de la idoneidad y de la similitud que aporta cada variable, distribución de |diferencia|/tolerancia y rango de valores de cada cuerpo.

**Volver a ejecutar** (desde `/home/user/stars-beside-you`, con `PY=/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/bin/python`; deterministas):

```
$PY "tierra luna/audit/p5_baseline.py"          # ~1 min
$PY "tierra luna/audit/p5_sensitivity.py"       # las tres misiones; 30-60 min con la máquina compartida
$PY "tierra luna/audit/p5_physical.py"          # ~3 min
$PY "tierra luna/audit/p5_shown_numbers.py"     # segundos
$PY "tierra luna/audit/p5_inventory.py"         # segundos (lee las salidas anteriores)
```

`p5_sensitivity.py <misión> --part INICIO FIN` reparte una misión entre procesos (así se ha ejecutado Paneles solares, en seis partes); `p5_inventory.py` lee todas las partes.

---

## Punto A (10). Inventario completo de cada número

### A.1 Qué hay en `inventory.csv`

**278 filas**: 127 anotadas con efecto medido, 136 hojas numéricas de configuración clasificadas por regla (ninguna queda sin clasificar) y 15 constantes de los constructores de tablas (`real_data/build_moon.py`, `build_earth.py`). 93 filas llevan bandera (la mayoría, el rótulo "provisional / no validado" que el propio repositorio pone); 20 son configuración muerta. Columnas: `id`, `value`, `unit`, `category`, `origin_class` (dato medido / cálculo / literatura / decisión de diseño), `origin`, `defined_in`, `used_at` (fichero:línea), `effect_measured`, `flag`, `proposal`, `correction_changes_design`.

### A.2 Los números que deciden los pares, con su efecto medido

Formato del efecto: entran/salen del embudo; pares +ganados/−perdidos; puntos con otro gemelo; top 5 conservados (de 5); top 50 conservados (de 50). "Sin cambio" = 0 en todo y top 5 y 50 idénticos y en el mismo orden.

**Embudo común**

| número | valor | origen | efecto si se quita / perturba |
|---|---|---|---|
| `elevation_m ≥ 1` (solo Tierra) | 1 m | diseño: "descarta océano, que el modelo fija en −250 m" | quitarlo: Rover +1 punto; Base lunar +18 puntos, +1/−2 pares, 23 gemelos cambian, top 5 conservado pero con otro orden, top 50 45/50; Paneles: +28 puntos y +3 pares, top 5 y 50 iguales. ×0,9 y ×1,1: sin cambio. **La razón escrita no vale en la tabla real**: allí el océano está vacío (NaN), no a −250 m; el filtro solo quita tierra firme por debajo de 1 m (depresiones) que `mask_fraction` ya acepta como tierra. |
| `mask_fraction ≥ 0,3` | 0,3 | diseño sin fuente (`docs/sources/R3` línea 17) | quitarlo: Rover +1.794 puntos y +1.793 pares, top 5 igual, top 50 37/50; Paneles sin cambio (el filtro "no sobre agua", clase mayoritaria, ya quita esas celdas); Base lunar sin cambio (ningún candidato de Base lunar tiene menos de 30 % de tierra). ×0,9: Rover +118; ×1,1: Rover −112. En la Luna vale 1 en todas las celdas: no actúa. |

**Rover** (similitud sobre valores reales; zona latitud ≤ −75°)

| número | valor | origen | efecto |
|---|---|---|---|
| filtro pendiente mínima | 0,5° | **ninguno** (R3 línea 75: "Removes flat terrain, which is unusual for a rover gate; ask why") | **el número más influyente del embudo**: quitarlo añade 7.847 puntos y 3.723 pares (top 5 y 50 iguales); ×0,9: +604 puntos; ×1,1: −483 |
| filtro pendiente máxima | 15° | literatura: VIPER "Slopes up to 15 deg (reqt)", NTRS 20240013903 p. 4 (R1 línea 42) | **no actúa**: quitarlo no cambia nada; ×1,1 nada; ×0,9 saca 1 punto. La pendiente de la Tierra a 3,7 km de base llega como mucho a 13,7° en el embudo |
| filtro rugosidad 5-650 m (mín. y máx.) | 5 m, 650 m | el texto cita "LRO LOLA & CNSA Yutu/VIPER topographic hazard envelope", pero R3 línea 74 dice "None found ... Design choice" y `rover_preset.py` línea 215 "no gate until Robotics 1 sets one" | **no excluye ninguna celda**: quitarlo entero, o cada extremo, o ×0,9 / ×1,1: sin cambio (la rugosidad del embudo va de 12,2 a 478 m) |
| `require_present` (pendiente, rugosidad) | — | diseño | sin cambio (redundante con los filtros) |
| idoneidad: peso pendiente | 0,45 | provisional ("aproximación lineal de la fórmula antigua") | a cero: top 5 3/5, top 50 39/50; ±10 %: top 50 49/50 |
| idoneidad: peso rugosidad | 0,30 | provisional | a cero: top 5 4/5, top 50 47/50 |
| idoneidad: peso fracción desnuda | 0,25 | provisional | **a cero: top 5 1/5, top 50 10/50** |
| utilidades bad/good (15/1°, 650/30 m, 0/0,7) | | provisional | ±10 %: top 5 entre 3/5 y 5/5, top 50 46-50/50 |
| similitud: peso pendiente (clave) | 0,4 | decisión 15-11 mañana | a cero: 3.912 gemelos cambian, top 5 4/5, top 50 27/50 |
| similitud: peso rugosidad (clave) | 0,4 | ídem | a cero: 5.243 cambian, top 5 0/5, top 50 28/50 |
| similitud: peso elevación relativa (secundaria) | 0,2 | ídem | **a cero: 5.476 gemelos cambian, top 5 0/5, top 50 2/50; fuera también del filtro: +145 pares, 10.101 gemelos cambian, top 50 0/50** |
| tolerancia pendiente | 2° | **ilustrativa** (`rover_preset.py` líneas 196-205, "ILUSTRATIVO - set by Robotics 1") | ±10 %: 368 / 299 gemelos cambian, top 5 igual, top 50 48-49/50 |
| tolerancia rugosidad | 30 m | **ilustrativa** (ídem) | ×0,9: −220 pares; ×1,1: +78 pares; top 5 5/5 y 4/5 |
| tolerancia elevación relativa | 500 m | la persona delegada, 15-11 mañana ("mitad de la escala robusta de la Tierra, 1.007 m, redondeada") | ×0,9: −78 pares, 739 cambian; ×1,1: +92, 555 cambian; top 5 igual |
| zona: latitud ≤ −75° | −75° | `analog_finder` + decisión (DECISIONS.md línea 26: por los planes de la NASA, no por los datos) | −74°: 641 gemelos cambian, top 5 y 50 iguales; −76°: 407 gemelos cambian, top 5 y 50 iguales; −67,5° (×0,9): +117 pares, 8.434 cambian, top 5 0/5; −82,5° (×1,1): −2.729 pares, top 5 0/5 |
| media de elevación de cada cuerpo | 695,9 / −248,4 m | cálculo (cos lat; DECISIONS.md línea 47) | Tierra ×1,01: +1 par, 206 gemelos cambian, top 5 igual, top 50 49/50; Luna ×1,01: 62 cambian, top 5 y 50 iguales; sin peso cos lat: +120/−57 pares, 7.058 gemelos cambian, top 5 0/5, top 50 0/50 (la regla de ponderación por área importa mucho; está decidida y escrita en DECISIONS.md línea 47) |

**Paneles solares** (zona |lat| ≤ 30° y elevación ≤ −1.200 m)

| número | valor | origen | efecto |
|---|---|---|---|
| filtro irradiancia en el suelo ≥ | 2,5 kWh/m²/día | diseño ("por debajo, la generación no compensa"; R3 línea 63) | quitarlo: +2.271 puntos y **0 pares**; ×0,9: +1.312 puntos; ×1,1: −1.316; top 5 y 50 iguales |
| filtro pendiente ≤ | 15° | diseño (R3 línea 65: contradicho para paneles en la Tierra, 5 % = 2,9°) | **no actúa**: quitarlo, 0 cambios; ×0,9: 1 punto |
| filtro Sol máximo ≥ | 10° | diseño | **no excluye ningún punto** (quitarlo o ±10 %: 0) |
| filtro Sol rasante ≤ | 0,25 | diseño (R3 línea 17) | **no excluye ningún punto** (quitarlo o ±10 %: 0) |
| filtro clase térmica ≠ agua | — | diseño ("no se instala sobre agua") | quitarlo: +740 puntos, +304 pares, **top 5 0/5**, top 50 42/50 |
| `require_present` (4 variables) | — | diseño | sin cambio |
| idoneidad: irradiancia en el suelo | 0,35; bad 2,5, good 6,0 | diseño no validado | **a cero: top 5 0/5 y top 50 0/50; good ×0,9 (5,4): top 5 0/5, top 50 0/50; good ×1,1: top 5 1/5, top 50 11/50** (el top 5 tiene utilidad 1: está en la saturación) |
| idoneidad: Sol máximo | 0,15; 10 / 70° | diseño | a cero: top 5 5/5, top 50 49/50; bad/good ±10 %: sin cambio |
| idoneidad: Sol rasante | 0,15; 0,25 / 0,03 | diseño | a cero: top 5 5/5, top 50 46/50 |
| idoneidad: pendiente | 0,15; 12 / 1° | diseño | a cero: top 5 5/5 (otro orden), top 50 50/50 |
| idoneidad: amplitud térmica | 0,10; 35 / 10 K | diseño | **a cero: top 5 0/5, top 50 19/50** (falta en 6.060 de 18.777 puntos) |
| idoneidad: rugosidad | 0,10; 400 / 30 m | diseño | a cero: top 5 5/5, top 50 47/50 |
| similitud: insolación sin atmósfera (clave) | 0,8; tolerancia 0,6 kWh/m²/día | la persona delegada, 15-11 mañana (de "la mitad de la escala robusta de la irradiancia en el suelo, 1,22") | a cero: 5.491 gemelos cambian, top 5 0/5, top 50 3/50; fuera también del filtro: +12.416 pares; tolerancia ×0,9: −197 pares; ×1,1: +186 pares; top 5 igual |
| similitud: pendiente (secundaria) | 0,1; 2° | **ilustrativa** | a cero (o fuera): 4.135 gemelos cambian, top 5 3/5, top 50 24/50; tolerancia ±10 %: 258 / 243 cambian |
| similitud: rugosidad (secundaria) | 0,1; 30 m | **ilustrativa** | a cero: 5.349 cambian, **top 5 0/5, top 50 6/50**; fuera: +1 par |
| zona: \|lat\| ≤ | 30° | `analog_finder` + decisión 15-11 mañana | 27°: −627 pares, 1.770 cambian; 33°: +540 pares, 1.528 cambian; top 5 y 50 iguales |
| zona: elevación ≤ | −1.200 m | ídem | −1.080 m: 258 cambian, top 50 48/50; −1.320 m: 412 cambian, top 5 3/5, top 50 46/50 |

**Base lunar** (temperatura mínima y amplitud como percentiles; zona 280 celdas)

| número | valor | origen | efecto |
|---|---|---|---|
| filtro amplitud diaria ≥ | 15 K | diseño ("sin ciclo térmico fuerte no hay ensayo útil"; R3 línea 70) | **el más influyente**: quitarlo añade 7.562 puntos, +2.014/−355 pares, top 5 0/5, top 50 0/50; ×0,9: +407 puntos, top 50 9/50; ×1,1: −421, top 50 3/50 |
| filtro temperatura mínima ≤ | 5 °C | diseño (R3 línea 17) | quitarlo: +1.920 puntos, +158/−111 pares, top 5 0/5, top 50 8/50; ×0,9: −164 puntos, top 5 2/5; ×1,1: +151, top 5 3/5 |
| filtro clase térmica ≠ agua | — | diseño | quitarlo: +4 puntos, 1 gemelo cambia, top 50 48/50 |
| `require_present` (3 variables) | — | diseño | sin cambio (redundante con los filtros) |
| `mask_fraction` | 0,3 | diseño | **no excluye ningún candidato de Base lunar** |
| idoneidad: pesos 0,35 / 0,25 / 0,15 / 0,10 / 0,10 / 0,05 | | "valores de diseño NO validados" (nota de `mission_scoring.json`) | a cero, top 5 conservados: amplitud 3/5, mínima 1/5, clase térmica 3/5, fracción desnuda 3/5, irradiancia 4/5, permafrost 3/5 (top 50: 42, 33, 42, 41, 46, 43) |
| tablas de clases (roca 1, regolito 1, arena 0,9, suelo 0,6, hielo 0,4; permafrost 1/1/0,7/0,3) y `default` 0,5 | | diseño | −0,1 en una clase: top 5 4-5/5; `default` 0,4: sin cambio (ninguna clase del embudo cae fuera de la tabla) |
| similitud: peso mínima (clave, percentil) | 0,4 | decisión 08:55 (D4b) | a cero: 117 cambian, top 5 1/5, top 50 25/50; fuera también del filtro: +315 pares, top 50 5/50 |
| similitud: peso amplitud (clave, percentil) | 0,4 | ídem | a cero: 152 cambian, top 5 2/5, top 50 27/50; fuera del filtro: +573 pares, top 50 0/50 |
| similitud: peso pendiente (secundaria) | 0,1 | ídem | a cero: 57 cambian, top 5 4/5, top 50 37/50; fuera: +6 pares |
| similitud: peso rugosidad (secundaria) | 0,1 | ídem | a cero: 85 cambian, top 5 2/5, top 50 32/50; **fuera del filtro: +549 pares** (es, con la amplitud, el filtro que más pares quita) |
| tolerancias percentil | 10 puntos | la persona delegada, 08:55 | ±10 %: −11/+9 pares (mínima) y −15/+13 (amplitud); top 5 4-5/5 |
| tolerancias pendiente / rugosidad | 2° / 30 m | **ilustrativas** (`rover_preset.py`) | ±10 %: −3/+1 pares (pendiente), −31/+39 (rugosidad) |
| regla de percentil de rango medio | 100 (r − 0,5)/n | `LUNAR_BASE_PROPOSAL.md` | r/n: 12 cambian, top 5 4/5; r/(n+1): 1 cambia, top 5 en otro orden |
| huella de 280 celdas | 280 | USGS (McClernan 2024) + regla "el cuadrado toca la región" | sustituida por su `fallback` (lat ≤ −75): +1.340/−4 pares, top 5 0/5 |
| desplazamiento 273,15 K | 273,15 | definición del kelvin | **sin efecto por construcción** (mismo desplazamiento en los dos lados y percentiles invariantes); hace falta solo para mostrar K |

**Comunes a las tres misiones**

| número | valor | origen | efecto |
|---|---|---|---|
| multiplicador del filtro, clave | 1 | decisión 15-11 | ×0,9: Rover −220 pares, Base −25; ×1,1: Rover +78, Base +22; Paneles ×0,9 −197 pares, ×1,1 +186; top 5 igual en todas |
| multiplicador del filtro, secundaria | 2 | decisión 15-11 | ×0,9: Rover −78, Base −33; ×1,1: Rover +92, Base +40; Paneles ×0,9 0 pares (1 gemelo cambia), ×1,1 +1 |
| α (`mix_factor`) | 0,5 | valor por defecto de `combine_with_similarity` (`mission_scoring.py` línea 207), "pending team confirmation" (ASSUMPTIONS.md 0.2); aplicado por la decisión del 15-11 | 0,45 / 0,55: Rover top 5 4/5 y 5/5 (mismo orden), top 50 47/50 y 46/50; Base lunar top 5 3/5 y 5/5 (otro orden), top 50 47/50; Paneles top 5 4/5 y 4/5, top 50 49/50 y 50/50. α = 0 (solo idoneidad) conserva el top 5 de Paneles (5/5, otro orden): **en Paneles el top 5 lo eligen la idoneidad y la saturación de la similitud**; en Rover α = 0 o 1 sustituye el top 5 entero |
| decimales de las utilidades (6), de las puntuaciones por variable (6) y del final (2) | | diseño (`export_decimals`) | utilidades y puntuaciones sin redondear: sin cambio en las tres misiones; final a 12 decimales: sin cambio en las tres (ningún empate a 2 decimales en el top 50) |

### A.3 Constantes, redondeos, confianza, máscaras

- **Insolación sin atmósfera (clave de Paneles, lado Tierra)**: S0 = 1.361 W/m² (ficha lunar del NSSDC, `provenance_moon.csv`), oblicuidad 23,44°, excentricidad 0,0167, longitud solar del perihelio 282,9° (= 102,9 + 180; ASSUMPTIONS.md línea 152), 24 h/día, 3.650 pasos de tiempo, 20 iteraciones de Kepler. Mi integración propia da 9,9739 / 8,7651 / 7,3667 / 5,6717 kWh/m²/día a 0 / 30 / 45 / 60° (referencias del motor 9,97 / 8,77 / 7,37 / 5,67; ASSUMPTIONS da 9,9743 para 0°): los dos parámetros numéricos no influyen en el resultado. Efecto ×1,01 de cada constante (solo en el lado de la Tierra): S0 y 24 h: +186 pares, 4.815 gemelos cambian, **top 5 0/5 y top 50 0/50**; oblicuidad: 677 cambian, top 5 3/5, top 50 38/50; excentricidad: 4 cambian; perihelio: ninguno. **S0 ×1,01 en los dos lados a la vez** (la tabla lunar usa el mismo 1.361 W/m²): 6 gemelos cambian, top 5 y 50 iguales. Conclusión: el par de Paneles depende de diferencias de centésimas de kWh/m²/día entre los dos lados, así que **la misma S0 en los dos lados es imprescindible**; lo es (1.361,0 en `toa_insolation` y en `build_moon.py` línea 57, misma fuente NSSDC). Un sesgo relativo del 1 % entre la Tierra y la Luna sustituiría el top 5 entero. Polos: 4,1368 kWh/m²/día en los dos hemisferios (segunda ley de Kepler; físicamente correcto).
- **Dos valores para una constante** (fallo menor, corregible sin cambiar diseño): la oblicuidad de la Tierra es 23,44° en `engine_config.json` `toa_insolation` y 84381,406″/3600 = 23,4393° en `real_data/build_earth.py` línea 50 (para `sun_elev_max_deg` y `sun_low_frac_0_5deg`); el radio terrestre es 6.371,0 km en `body_radius_km` y 6.371,0088 km en `build_earth.py` línea 48. Diferencias de 0,003 % y 0,0001 %: efecto inferior a 0,001 kWh/m²/día y a 1 m en las distancias. Propuesta: una sola cifra por constante, con su fuente.
- **Irradiancia lunar** (clave de Paneles, lado Luna): `build_moon.py` líneas 476-507, 1.361 W/m² × media temporal de max(0, sen h) × 24/1000, órbita circular, oblicuidad 1,54° (PIA13720). Ecuador: 10,395 en la tabla frente a 1361/π × 24/1000 = 10,397 (comprobado). Efecto ×1,01 (solo la Luna): −197 pares, 4.587 gemelos cambian, top 5 0/5, top 50 0/50 (la misma sensibilidad). La Luna usa órbita circular y la Tierra excéntrica: el sesgo que eso introduce en la media anual es (1 − e²)^−½ − 1 = 0,014 %, muy por debajo del 1 % que cambia el top 5.
- **Constantes de los constructores sin efecto medible aquí**: `GCP_MIN_VALID` 40 de 96 franjas y `GCP_MAX_GAP` 12 (Diviner; deciden qué celdas lunares tienen mínima y amplitud), `SUN_SEMIDIAMETER_DEG` 0,2666, `RA_MIN_VALID_FRAC` 0,5 (solo la columna informativa de abundancia de roca; sin origen escrito). Medir su efecto exige reconstruir las tablas desde las descargas: **no establecido**.
- **Día lunar 29,53** (NSSDC): solo texto (`{lunar_day}` → 29,5). **Radios 6.371 / 1.737,4 km**: solo las distancias en km a lugares y accidentes; no tocan pares ni rango.
- **Redondeos**: utilidades y puntuaciones a 6 decimales con `round` de Python sobre binario (`engine/suitability.py` 57-79, `real_similarity.py` 223); el rango ordena el final redondeado a 2 decimales y desempata por id de la Tierra (`pipeline.py` 164), no por el final sin redondear; lo que se muestra se redondea "half up" sobre el decimal más corto del float32 (`engine/display.py` 1-64, contrato revisión 6), salvo la frase por par de Base lunar, que usa `toFixed`/`f"{x:.{d}f}"` (DATA_CONTRACT línea 314: coinciden salvo empate binario exacto; en 30 de 450 pares el último dígito sigue al float32). Saturación: una puntuación por variable vale 1,000000 cuando la diferencia es menor que 0,001 × tolerancia (Paneles: 0,0006 kWh/m²/día). Los huecos del texto "sin par" se redondean hacia arriba (DATA_CONTRACT línea 484). Todo documentado; ninguno cambia un par.
- **Confianza** (`engine_config.json` `confidence`: puntuaciones por nivel 1 / 0,7 / 0,3 / 0,2, `high_min` 0,8, `medium_min` 0,5, `high_max_cell_km` 1,0): **sin origen registrado** y **sin información por par**: los 10.192 pares de Rover son "medium", los 6.360 de Paneles "medium" y los 450 de Base lunar "low" (`missions.json` `confidence_counts`); "high" es imposible con celdas de 1° (30-111 km > 1 km). La web la enseña en cada par (`app/src/flow/detailPanel.ts` líneas 586-596). No cambia pares ni rango.
- **Máscara de tierra y cobertura**: `datasets.json` `earth_land_cells` = `mask_fraction` > 0; filtro `mask_fraction` ≥ 0,3; una variable ponderada sin dato se ignora y se renormalizan los pesos (en Paneles, la amplitud falta en 6.060 de los 18.777 puntos: `p5_physical.json`).

### A.4 Valores que ve el usuario

`out/p5_shown_numbers_summary.json`:

| fuente | números | trazados al fichero de origen | sin trazar |
|---|---|---|---|
| textos del paquete (`missions.json`, `similarity.json`, `explain.json`) | 325 + 441 + 300 cifras | todas | 0 |
| `mission_zones.json` | 199 | 179 | 20: son las cifras de contraste de zonas calculadas fuera del motor; cada una tiene su `how_computed` en el propio fichero (p. ej. 9.888 pares del polo norte, 2,45 kWh/m²/día, 18.776) |
| 19 transcripciones | 98 cifras + 38 en palabras | 96 | 2, redondeos "about": 160 km (159,2 en AUDIO_TOP5) y 220 km (218,2) |
| subtítulos de Base lunar (en, es) | 81 + 81 | 18 + 18 | 63 + 63: valores que el render calcula fotograma a fotograma (Sol, potencia, temperatura del modelo de curva entre 41,23 y 194,51 K); el escenario declara el modelo |
| subtítulos de Paneles (en, es) | 104 + 104 | 41 + 41 | 63 + 63: ídem (potencia ≤ 1.342 W/m², por debajo de 1.361) |
| subtítulos de Rover (en, es) | 67 + 67 | — | no hay escenario (`app/video-sim/scenarios/` solo tiene `solar.json` y `lunar-base.json`): vídeo del equipo; el README dice que los valores se transcribieron de los fotogramas |

Limitación: "trazado" quiere decir que la cifra aparece (redondeada a 0-4 decimales) entre las cifras del fichero de origen, no que su significado sea el correcto; el significado de las 15 frases de audio es del punto C/p4.

**Fallo encontrado en lo que ve el usuario: el vídeo de Paneles solares enseña un par que el modelo ya no produce.** `app/video-sim/scenarios/solar.json` (escrito el 15-11 a las 00:58, antes de la decisión de la mañana) y `app/public/media/solar/solar.*.vtt` (01:03) muestran el par E44120 (Western Cape, Sudáfrica) – **M59479 (75,5° S 100,5° O, cerca de Boltzmann, polo sur)**: "Dawn over the real LOLA relief at 75.5° S 100.5° W". Desde la decisión del 15-11 (mañana) la zona de Paneles son los mares ecuatoriales (|lat| ≤ 30°, elevación ≤ −1.200 m) y M59479 está fuera de ella; en el paquete publicado E44120 tiene hoy como gemelo M21923 y rango 5.786 (similitud 77,70, final 82,26). La web ofrece "Start mission" para cada carpeta de `public/media/` (`app/src/flow/media.ts` líneas 1-2, `app/scripts/mediaIndex.ts`), y la compilación de hoy lo incluye: `app/dist/media-index.json` (09:34) lista `lunar-base`, `rover` y `solar`. Corrección (no cambia ningún criterio): volver a renderizar el vídeo de Paneles con el par número 1 actual (E38464 – M24296) con `app/video-sim`, o sacarlo del índice de vídeos hasta entonces; ningún documento lo recoge (`grep` en DECISIONS, ASSUMPTIONS, ANALOG_PRINCIPLE y UX_REPORT). El vídeo de Base lunar sí coincide con el número 1 actual (E17538 – M63528, idoneidad 47,27, similitud 97,31, final 72,29: `lunar-base.json` `pair_values`).

**Observación menor**: el panel del vídeo de Rover enseña "Sun elevation 21.1°" fijo. En la zona del Rover (≤ 75° S) el Sol no puede pasar de 90 − (75 − 1,54) = 16,5° sobre un horizonte plano; el vídeo no dice dónde está ni dice ser el gemelo, así que no es un error del modelo, pero es una cifra sin origen. Propuesta: decir en el subtítulo que el vídeo es una simulación sin lugar concreto, o poner un valor posible en la zona.

### A.5 Banderas

**(i) Números que no cambian nada**

| número | prueba | propuesta |
|---|---|---|
| filtro de rugosidad 5-650 m del Rover | quitarlo (o cada extremo, o ±10 %): 0 cambios | pregunta de diseño: quitarlo (efecto 0) o decir de dónde sale |
| pendiente máxima 15° del Rover | quitarla: 0 cambios; ×0,9: 1 punto | justificado (VIPER), pero inerte a 3,7 km de base: decirlo en la web o quitarlo (efecto 0) |
| Paneles: pendiente ≤ 15°, Sol máximo ≥ 10°, Sol rasante ≤ 0,25 | quitar cada uno: 0 cambios (pendiente ×0,9: 1 punto) | pregunta de diseño: quitarlos (efecto 0) o decir que son un seguro que hoy no actúa |
| `require_present` de las tres misiones | quitar cada una: 0 cambios (los filtros ya exigen el dato) | dejar (seguro de datos) o quitar; efecto 0 |
| `mask_fraction` en Base lunar y en la Luna | 0 cambios | — |
| `default` de las tablas de clases | 0 cambios (ninguna clase sin entrada en el embudo) | — |
| desplazamiento 273,15 K en la similitud | 0 por construcción | solo unidad mostrada |
| pesos por dominio (`weights`: relieve/material/termico/luz/agua) de las 5 misiones | no los lee el motor (`not_used_by_engine_why`) **ni la web** (`app/src`: 0 apariciones de `relieve`/`luz`), aunque la nota de `mission_scoring.json` diga que los usa el botón "Use Weights" | **configuración muerta: corregible** (quitarla o moverla a un bloque "no usado" y corregir la nota) |
| `tolerances` del Rover en `mission_scoring.json` (5°, 10 m) y `workable_days` (1 mm, 12 m/s, −10 °C) | no los lee ningún código (`not_used_by_engine_why`) | **configuración muerta: corregible** |
| `reference_tolerances_not_used` (10 K, 5 K) | rotuladas "no mission uses them" | quitar o dejar con su rótulo |
| `similarity_zones.solar` (−75°) | la regla publicada lee la zona de `real_value_similarity` (mares); esta entrada quedó de la regla anterior y contradice la decidida | **corregible**: marcarla como de la regla `zone_twin` o quitarla |
| `repo_similarity` (decaimiento 0,45, 1e-6, decimales de z), `similarity_scale` (percentiles 5/95) | solo reglas alternativas (`--similarity-rule`); ninguna misión publicada las usa | dejar como alternativa documentada |
| bloques `thermal` e `ice` | `thermal` es la copia de la que sale `lunar_base` (lo vigila `engine/config.py`); `ice` se muestra por punto como información y nunca cambia el orden | dejar (documentado) |

**(ii) Números sin origen defendible** (ni fuente ni decisión registrada que diga por qué ese valor)

| número | lo que hay | efecto | clase |
|---|---|---|---|
| pendiente mínima 0,5° del Rover | nada (R3 línea 75) | **+7.847 puntos y +3.723 pares si se quita** | pregunta de diseño |
| rugosidad 5-650 m del Rover | cita no encontrada (R3 línea 74) | 0 | pregunta de diseño |
| confianza (1 / 0,7 / 0,3 / 0,2; 0,8; 0,5; 1 km) | nada | ninguno en pares; etiqueta constante por misión | corregible (presentación) |
| `mask_fraction` 0,3, `sun_low_frac` 0,25, mínima 5 °C, amplitud "good" 35 K y todos los pesos de idoneidad | R3 línea 17: "pure design choices" | ver A.2 | decididos y rotulados como diseño no validado: se dejan con su rótulo |
| `RA_MIN_VALID_FRAC` 0,5 (`build_moon.py` línea 380) | sin comentario | solo columna informativa | corregible (añadir el porqué) |
| "Sun elevation 21.1°" del vídeo de Rover | sin escenario | ninguno en el modelo | corregible (texto) |

**(iii) Ilustrativos o no validados (rotulados así en el repositorio)**: tolerancias 2° y 30 m (las de Rover, Paneles y Base lunar: `rover_preset.py` "ILUSTRATIVO - set by Robotics 1", y así lo dicen DECISIONS.md línea 46 y `tolerance_set_by`); todo el bloque `soft` del Rover ("provisional"); umbrales de Paneles y Base lunar ("valores de diseño NO validados con fuente externa"). Están rotulados en el paquete (`missions.json` `threshold_status`). No es un fallo: es un estado que el jurado debe ver, y la web lo enseña.

**(iv) Razón escrita que ya no se cumple**: `elevation_m ≥ 1` ("descarta océano, que el modelo fija en −250 m") en la tabla real (A.2). Pregunta de diseño.

### A.6 Veredicto del punto A: **NOT YET**

Todo número que decide un par tiene valor, unidad, uso en el código y efecto medido, y mi implementación reproduce el paquete al 100 %. No es GO por: (1) el vídeo de Paneles solares muestra un par de la zona antigua del polo sur que el modelo ya no produce (corregible: re-render o retirada); (2) configuración muerta en el fichero que se entrega (pesos por dominio, tolerancias y `workable_days` del Rover, `similarity_zones.solar`), con una nota falsa sobre el botón "Use Weights" (corregible); (3) dos filtros del Rover sin origen defendible, uno de ellos sin ningún efecto (rugosidad 5-650 m) y otro con el mayor efecto del embudo (pendiente ≥ 0,5°): decide el líder del equipo; (4) la etiqueta de confianza sin origen y sin información por par (corregible en la presentación); (5) dos valores para la oblicuidad y el radio de la Tierra (corregible, efecto despreciable).

---

## Punto D (13). Sentido físico de cada variable en su misión

Cifras de `out/p5_physical.json` (embudo y pares de la ejecución propia) y de A.2. "Parte de la dispersión" = varianza de peso × utilidad (o × puntuación) entre la varianza de la suma: qué parte de lo que distingue a unos puntos de otros aporta cada variable.

### D.1 Rover

**Filtros duros.**
- *Pendiente 0,5-15°*. El máximo tiene sentido y fuente (un rover tipo VIPER está especificado para pendientes de hasta 15°: R1 línea 42), pero la pendiente de la tabla es una media a 3,7 km de base, mucho más suave que la que ve la rueda (R1 línea 87): por eso no actúa (máximo del embudo 13,7°). El mínimo de 0,5° no tiene razón física para un rover (lo llano no impide circular) y es el filtro que más puntos quita (7.847). **Pregunta de diseño.**
- *Rugosidad 5-650 m*. Sin fuente y sin efecto. **Relleno**: pregunta de diseño (quitarlo no cambia nada).

**Idoneidad.**
- *Pendiente (0,45) y rugosidad (0,30)*: menos pendiente y menos rugosidad = terreno más transitable, que es lo que limita a un rover (R1: pendiente de requisito y obstáculos de 15-20 cm). Trabajan (parte de la dispersión 23,5 % y 7,3 %), pero **son casi la misma variable**: correlación de rangos de sus utilidades 0,973 en el embudo. El relieve pesa 0,75 por duplicado.
- *Fracción desnuda (0,25)*: suelo sin vegetación como sustituto de regolito expuesto. Es la que más distingue (53,4 % de la dispersión; a cero el top 50 conserva 10 de 50). Sentido físico plausible para un ensayo de movilidad sobre material suelto, pero es una clasificación de cubierta (CCI 150-153 y 200-202), no un dato de suelo; hielo y nieve no cuentan como desnudo en la tabla real.

**Similitud.**
- *Pendiente y rugosidad (claves, 40 % + 40 %)*: lo que de verdad hay que reproducir para probar un rover. Las diferencias de los pares son pequeñas (mediana 0,20 y 0,18 tolerancias). Trabajan, pero entre los pares aportan solo el 4,7 % y el 22,7 % de la dispersión de la similitud.
- *Elevación relativa (secundaria, 20 %, tolerancia 500 m)*: **no tiene sentido de movilidad**: la altura sobre la media de cada cuerpo no cambia la tracción, la pendiente ni los obstáculos (en la Luna no hay aire; en la Tierra la altura cambia la presión y el clima, que no se comparan). Y es la variable que más ordena: 52,8 % de la dispersión de la similitud; con peso cero cambian 5.476 de 10.192 gemelos, el top 5 se sustituye entero (0/5) y del top 50 quedan 2; fuera también del filtro, +145 pares y top 50 0/50. Los cinco primeros pares comparten gemelo (M59895) y se ordenan sobre todo por esa diferencia (96, 71, 86, 18 y 129 m). La razón registrada es la escala ("mitad de la escala robusta de la Tierra"), no la física de la misión. **Pregunta de diseño**: dejarla a 0, justificarla (p. ej. como sustituto de "terreno de meseta frente a cuenca") o bajarla; con 0 el par número 1 deja de ser E17566.
- *Zona ≤ −75°*: decisión por los planes de la NASA (VIPER, cráteres en sombra), no por los datos (DECISIONS.md línea 26). Tiene sentido de misión.

### D.2 Paneles solares

**Filtros duros.** Irradiancia en el suelo ≥ 2,5 kWh/m²/día (energía mínima que compensa), pendiente ≤ 15° (montaje), Sol máximo ≥ 10° y fracción de Sol rasante ≤ 0,25 (sombras), no sobre agua: todos con sentido para un campo de paneles en la Tierra; la pendiente de 15° es mucho más laxa que la práctica en la Tierra (5 % = 2,9°, R3 línea 65). Efectos medidos: irradiancia ≥ 2,5: quitarla añade 2.271 puntos y **0 pares** (son puntos de latitud alta sin gemelo posible), ×0,9 +1.312 puntos, ×1,1 −1.316, sin cambio en pares ni top 5/50; **pendiente ≤ 15°, Sol máximo ≥ 10° y Sol rasante ≤ 0,25 no excluyen ningún punto** (quitarlos: 0 cambios; pendiente ×0,9: 1 punto): con horizonte plano el Sol máximo y el Sol rasante son funciones de la latitud y el filtro de irradiancia ya quita esas latitudes (mínimo del embudo 23,9° de Sol máximo y máximo 0,211 de Sol rasante); **"no sobre agua" sí trabaja: quitarlo añade 740 puntos y 304 pares y cambia el top 5 entero (0/5, top 50 42/50)**. Los tres filtros inertes van a A.5 (i).

**Idoneidad.**
- *Irradiancia en el suelo (0,35)*: es la energía que recibe de verdad un panel en la Tierra. Trabaja (30,6 % de la dispersión).
- *Sol máximo (0,15) y fracción de Sol rasante (0,15)*: con horizonte plano son **funciones puras de la latitud** (correlación con |lat| −0,96 y −0,88) y están correlacionadas con la irradiancia (0,69 y 0,76). El Sol máximo vale 1 para el 42,4 % del embudo (todo |lat| ≤ 43,4°). Aportan 5,8 % y 3,4 % de la dispersión. No son falsas (un Sol alto ilumina mejor un panel horizontal), pero repiten la latitud que ya está en la irradiancia: tres variables, 0,65 del peso, sobre una misma causa.
- *Pendiente (0,15) y rugosidad (0,10)*: menos obra de tierras; saturadas (utilidad 1 en el 71,7 % y el 66,4 %), 1,0 % y 0,6 % de la dispersión; correlación entre ellas 0,938.
- *Amplitud térmica (0,10)*: menos ciclos térmicos en los paneles; falta en 6.060 de 18.777 puntos (se renormaliza); 1,1 % de la dispersión.

**Similitud.**
- *Insolación sin atmósfera (clave, 80 %, 0,6 kWh/m²/día)*: compara la luz que llega a cada cuerpo antes de cualquier atmósfera; en la Tierra es **solo función de la latitud** (4,14 a 9,97), así que el par se decide por la latitud del punto de la Tierra frente a la irradiancia de la celda lunar (9,05 a 10,40 en los mares). Aporta el 99 % de la dispersión de la similitud. Tiene sentido como "mismo Sol" pero no es la energía del panel en la Tierra (se pierde un 35-38 % en el aire en el top 5); el equipo lo sabe y lo exige en cada par (DECISIONS.md línea 50). Decidido.
- *Pendiente y rugosidad (secundarias, 10 % + 10 %)*: un campo de paneles necesita terreno llano, así que tiene sentido que el gemelo lunar sea también llano. No separan unos pares de otros en el valor de la similitud (puntuación ≥ 0,999 en el 79,4 % y el 77,9 % de los pares; 0,0 % y 0,1 % de su dispersión), pero **sí eligen el gemelo y el orden**: como la insolación de la Tierra solo depende de la latitud, muchas celdas lunares empatan casi en la clave y las secundarias deciden entre ellas. Sin la pendiente: 4.135 gemelos cambian, top 5 3/5, top 50 24/50; sin la rugosidad: 5.349 cambian, top 5 0/5, top 50 6/50. Trabajan como desempate; no son relleno. Saturación: el 13,9 % de los pares tiene similitud ≥ 99,99 (punto E), y con α = 0 el top 5 es el mismo (A.2): la similitud de Paneles casi no ordena el top.

### D.3 Base lunar

**Filtros duros.** Amplitud ≥ 15 K (sin ciclo fuerte no hay ensayo térmico) y mínima ≤ 5 °C (hace falta frío): con sentido para un ensayo de resistencia térmica; son los que más deciden quién entra (A.2). No sobre agua: 4 puntos.

**Idoneidad.**
- *Amplitud (0,35) y mínima (0,25)*: el estrés térmico de un hábitat (ciclos de dilatación y frío extremo). Trabajan (21,4 % y 15,7 % de la dispersión) y son independientes entre sí (correlación 0,05). Ojo: la mínima de la Tierra es temperatura del aire (WorldClim, MODELLED) y la amplitud es la diferencia de dos pasadas de MODIS (~10:30 menos ~22:30), que subestima la amplitud real (`column_aliases.json`).
- *Clase térmica (0,15) y fracción desnuda (0,10)*: **las dos salen de las mismas clases de cubierta de ESA CCI** (regolito = CCI 150-153 y 200; fracción desnuda = CCI 150-153 y 200-202): correlación de sus utilidades 0,893. Una superficie desnuda de baja inercia se parece más al regolito: tiene sentido, pero cuenta dos veces. Además "roca" (utilidad 1) incluye la clase CCI 190, **zonas urbanas** (`real_data/class_mappings.json`): un sinsentido físico que hoy afecta a 1 punto del embudo.
- *Irradiancia en el suelo (0,10)*: "más carga solar = más calentamiento diurno": físicamente es la amplitud la que lo mide; correlación con la utilidad de la mínima −0,79 (las dos siguen la latitud); 3,0 % de la dispersión.
- *Permafrost (0,05)*: premia ciclos de congelación (esporádico y discontinuo 1, continuo 0,7, ninguno 0,3). En la Luna no hay permafrost (la tabla pone "ninguno" en todas las celdas, MODELLED, ASSUMPTIONS 0.6) y una base lunar no sufre ciclos de hielo-deshielo: **sentido físico débil**. Falta en 607 de 2.419 puntos; 1,3 % de la dispersión; a cero el top 5 conserva 3 de 5 y el top 50 43 de 50 (lo mueve porque los finales están muy juntos). **Pregunta de diseño** (peso a cero o explicarlo).

**Similitud.**
- *Mínima y amplitud como percentiles (claves, 40 % + 40 %, 10 puntos)*: la posición térmica dentro de cada mundo, no la temperatura (decidido, D4b): en el número 1 la Luna está 207,38 K más fría y oscila 137,67 K más. Las dos trabajan (24,8 % y 24,6 % de la dispersión) y son las que dan sentido a la misión.
- *Pendiente y rugosidad (secundarias, 10 % + 10 %, filtro 4° y 60 m)*: un hábitat necesita suelo practicable; aportan 7,4 % y 13,7 % de la dispersión, y **el filtro de rugosidad es el que más pares quita** (sin él, +549 pares): las celdas de las nueve regiones son rugosas (90-569 m) y los candidatos de la Tierra lisos (mediana 36 m), así que solo emparejan las montañas. Trabajan.
- **Tensión física entre idoneidad y similitud** (pregunta de diseño, no se cambia nada): los cinco primeros tienen la amplitud casi en el mínimo que admite el filtro (utilidad de amplitud 0,03 a 0,19, es decir 15,6 a 18,7 K, por debajo de la mediana del embudo, 19,3 K) y por eso una idoneidad de solo 43,9 a 48,0 sobre 100: el par sube por la similitud (95-99) aunque la misión, por sus propios criterios, considera esos sitios poco aptos para ensayar ciclos térmicos. El audio m3_base lo dice ("the coldest, steadiest sites on Earth"): es cierto para esos pares, pero contradice el criterio "más amplitud es mejor" del bloque `soft`.

### D.4 Veredicto del punto D: **NOT YET**

Las variables clave de las tres misiones tienen sentido físico y trabajan (pendiente y rugosidad para el Rover; luz antes de la atmósfera para Paneles, con su limitación declarada; posición térmica para la Base). Quedan para que decida el líder del equipo, con las cifras de arriba y sin cambiar ningún peso: (1) la elevación relativa del Rover, secundaria sin sentido de movilidad que decide el orden (top 5 0/5 sin ella); (2) en Paneles, la similitud saturada (≥ 99,99 en el 13,9 % de los pares; α = 0 deja el mismo top 5), de modo que el top 5 lo deciden la idoneidad (irradiancia en el suelo en su extremo 'good', amplitud térmica que falta en un tercio de los puntos) y las secundarias como desempate, y tres de los seis criterios de idoneidad (0,65 del peso) son la latitud; (3) en Base lunar, el permafrost (sentido débil) y la doble cuenta clase térmica + fracción desnuda (correlación 0,89), y la tensión idoneidad-similitud del top 5; (4) en el Rover, el doble relieve de la idoneidad (0,973) y el filtro de pendiente mínima sin razón física. Corregible sin tocar el diseño: la clase "roca" que incluye zonas urbanas debería al menos decirse (cambiarla sí cambiaría una tabla de clases decidida: pregunta de diseño).

## No establecido

- El efecto de las constantes de los constructores (`GCP_MIN_VALID`, `GCP_MAX_GAP`, `SUN_SEMIDIAMETER_DEG`, `RA_MIN_VALID_FRAC`, los códigos CCI): exige reconstruir las tablas desde las descargas.
- El efecto de una huella de Base lunar distinta de "el cuadrado toca la región" (p. ej. "el centro cae dentro"): el contorno exacto no está publicado (ASSUMPTIONS 0.5); solo se ha medido el `fallback`.
- Si los valores calculados fotograma a fotograma en los subtítulos de los vídeos (Sol, potencia, temperatura) son los del render: no hay registro por fotograma; solo se ha comprobado que son físicamente posibles (potencia ≤ 1.361 W/m², temperatura entre la mínima y la máxima Diviner de la celda).
