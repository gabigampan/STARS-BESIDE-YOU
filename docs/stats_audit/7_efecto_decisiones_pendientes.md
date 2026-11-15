# 7. Efecto de las decisiones de diseño pendientes (calculado en memoria, NADA aplicado)

Solo se han creado `tierra luna/audit/w_*.py`, `tierra luna/audit/out/w_*` y este documento. No se tocó el motor, la configuración, las tablas, el bundle, la web ni los audios. La configuración se leyó una sola vez al empezar; sus hashes están en `out/w_config_snapshot.json`. La librería es la reimplementación independiente `p2_model.py`, a la que se añadieron cachés y parches temporales en `w_common.py`.

**Reproducción (w0).** Se reproducen 10.192 / 6.360 / 450 parejas (Rover / Paneles / Base). Los gemelos distintos son 401 / 1.704 / 103. Los top 5 de las tres misiones coinciden con `docs/AUDIO_TOP5.json` en celda, gemelo, similitud, idoneidad y final: **REPRODUCED**.

Notación. «Pista k rota» quiere decir que el audio k ya no describe la pareja que ocupa el puesto k (cambia la celda de la Tierra o su gemelo). Los nombres salen del bundle: `earth_place_detail.bin` para la Tierra y `moon_base.bin` con `iau_moon_features.json` para la Luna.

## P1. Zona de la Base lunar (`w1_zone.py`)
Las áreas se miden en una proyección acimutal equivalente de Lambert polar sur (R = 1737,4 km), sobre la huella formada por la unión de las nueve regiones.

| | (a) toca (actual) | (b) centro dentro | (c) ≥ 50 % del área | (d) ≥ 5 % del área |
|---|---|---|---|---|
| celdas de zona | 280 | 113 | 109 | 246 |
| pasan el embudo (Tierra) | 2.419 | 2.419 | 2.419 | 2.419 |
| emparejados | 450 | 271 | 284 | 435 |
| gemelos distintos | 103 | 49 | 49 | 87 |
| pistas rotas | — | 1, 2, 3, 4, 5 | 1, 2, 3, 4, 5 | 1, 2, 3, 4, 5 |

(a) Fracción de cada gemelo actual que cae dentro de su región:

| Puesto | Gemelo | Dentro |
|---|---|---|
| 1 | M63528 | Haworth 0,43 % |
| 2 | M63841 | de Gerlache Rim 2 7,8 % |
| 3 | M64018 | Slater Plain 32,9 % |
| 4 | M62517 | Nobile Rim 2 44,6 % |
| 5 | M62523 | Nobile Rim 2 0,32 % |

Ninguno de los cinco tiene su centro dentro de una región.

Top 5 de cada opción (Tierra | gemelo | sim / idon / final):

- **(b)**
  1. E16830 (43.5, 90.5) Mori, China | M62846 (−84.5, 26.5) Mons Mouton | 94,20 / 47,96 / 71,08
  2. E43309 (−30.5, −70.5) Monte Patria, Chile | M62841 (−84.5, 21.5) Mons Mouton | 96,11 / 45,53 / 70,82
  3. E15751 (46.5, 91.5) Burenhayrhan, Mongolia | M63522 (−86.5, −17.5) Haworth | 93,62 / 46,60 / 70,11
  4. E19697 (35.5, 77.5) Thang, Pakistán | M64021 (−87.5, 121.5) Slater | 92,16 / 48,03 / 70,10
  5. E15750 (46.5, 90.5) Qinghe, China | M64024 (−87.5, 124.5) Slater | 94,11 / 45,19 / 69,65

  Qué pasa con los pares actuales: el 1 baja al puesto 6 con el gemelo M63523; el 2 sube al 1 con otro gemelo; el 3 se queda en el 3 con otro gemelo; el 4 y el 5 se quedan sin gemelo.
- **(c)**
  1. E43309 Monte Patria | M62841 Mons Mouton | 96,66 / 45,53 / 71,10
  2. E17538 (41.5, 78.5) Aheqi | M64028 (−87.5, 128.5) Slater | 94,11 / 47,27 / 70,69
  3. E18255 (39.5, 75.5) Kashi | M62845 (−84.5, 25.5) Mons Mouton | 92,35 / 48,45 / 70,40
  4. E42233 (−27.5, −66.5) Andalgalá, Argentina | M62856 (−84.5, 36.5) Mons Mouton | 97,38 / 42,69 / 70,04
  5. E17898 (40.5, 78.5) Aheqi | M62845 Mons Mouton | 91,30 / 48,77 / 70,03

  Qué pasa con los pares actuales: el 1 pasa al puesto 2 con otro gemelo; el 2 cae al 13; el 3 cae al 6; el 4 y el 5 se quedan sin gemelo.
- **(d)**
  1. E16830 Mori | M63841 (−87.5, −58.5) Cartwright | 96,45 / 47,96 / 72,21
  2. E17538 Aheqi | M63867 (−87.5, −32.5) Cartwright | 96,50 / 47,27 / 71,89
  3. E16833 (43.5, 93.5) Barkol | M63841 Cartwright | 95,74 / 47,47 / 71,61
  4. E15751 Burenhayrhan | M64018 Slater | 96,34 / 46,60 / 71,47
  5. E18254 (39.5, 74.5) A'yi Take | M63875 (−87.5, −24.5) Haworth | 93,21 / 49,65 / 71,43

  Qué pasa con los pares actuales: el 1 baja al 2 con otro gemelo; el 2 sube al 1 con el mismo gemelo; el 3 baja al 4 con el mismo gemelo; el 4 baja al 6; el 5 baja al 29 con otro gemelo.

## P2. Separación mínima en el top 5 (`w2_separation.py`, voraz por puesto)
Las cinco celdas elegidas se dan con su puesto actual.

| Misión | 2° (222,4 km) | 500 km | 1.000 km |
|---|---|---|---|
| Rover | #1, 2, 3, 5, 7 (Urt) → pistas 4 y 5 rotas | #1, 2, 4, 5, 8 (Bayan Uula Sumu) → pistas 3, 4 y 5 rotas | #1, 2, 5, 11 (Najrán), 15 (Na'in) → pistas 3, 4 y 5 rotas |
| Paneles | #1, 3, 4, 7 (Katherine), 9 (Eyl) → pistas 2, 3, 4 y 5 rotas | #1, 3, 7, 9, 12 (Bol) → pistas 2, 3, 4 y 5 rotas | #1, 3, 9, 12, 22 (Katherine) → pistas 2, 3, 4 y 5 rotas |
| Base | sin cambio | #1, 2, 4, 6 (Vicuña), 9 (Waxxari) → pistas 3, 4 y 5 rotas | #1, 2, 4, 6, 17 (Shiraz) → pistas 3, 4 y 5 rotas |

Las puntuaciones son las actuales. Todos los gemelos de Rover son M59895. Las puntuaciones finales y los gemelos de cada celda están en `out/w2_separation.json`.

## P3. Rover: cinco pares, un solo gemelo (`w3_rover_one_twin.py`)
La zona tiene 5.400 celdas. Los límites del filtro son pendiente 2°, rugosidad 30 m y elevación relativa 1.000 m. En cada una de las cinco celdas de la Tierra **solo 1 celda de la zona pasa el filtro: M59895 (Casatus)**.

| Pista | Fallan por pendiente | Fallan por rugosidad | Fallan por elevación relativa | Fallan solo por rugosidad | Fallan solo por elevación relativa |
|---|---|---|---|---|---|
| 1 | 4.874 | 5.155 | 4.134 | 7 | 243 |
| 2 | 4.799 | 5.155 | 4.164 | 14 | 243 |
| 3 | 4.927 | 5.181 | 4.150 | 2 | 218 |
| 4 | 4.836 | 5.121 | 4.272 | 12 | 276 |
| 5 | 4.789 | 5.168 | 4.345 | 11 | 231 |

M59895 tiene pendiente 1,15°, rugosidad 44,2 m y elevación relativa +833 m. Es casi la única celda polar que es rugosa y está alta al mismo tiempo. Al ignorar el filtro, la segunda y la tercera mejor celda (Schrödinger, Slater, Ganswindt y otras) tienen similitud ≈ 80, porque su diferencia de elevación supera los 3.400 m. La rugosidad elimina casi toda la zona y la elevación relativa elimina el resto.

Opción (b), cada gemelo como máximo una vez en el top 5:

| Puesto nuevo | Puesto actual | Tierra | Gemelo | Final |
|---|---|---|---|---|
| 1 | 1 | E17566 Bayinbaolige | M59895 Casatus | 99,39 |
| 2 | 25 | E18633 (38.5, 93.5) Lenghu | M61037 Schomberger | 97,77 |
| 3 | 35 | E5680 (74.5, 100.5) Khatanga | M61116 Ganswindt | 97,32 |
| 4 | 45 | E4764 (76.5, −95.5) Gjoa Haven | M60992 Newton | 96,88 |
| 5 | 59 | E4769 (76.5, −90.5) Gjoa Haven | M61352 Mons Cabeus | 96,66 |

Pistas rotas: 2, 3, 4 y 5. Nota: los puestos 4 y 5 de esta opción vuelven a ser vecinos, en el Ártico canadiense.

## P4. Hielo en Rover (`w4_ice.py`)
Rover compara solo valores reales, así que quitar celdas de la Tierra no cambia ningún gemelo.

- Celdas ordenadas: 10.192. De ellas, 1.268 son «hielo» y 1.424 tienen snow_ice_frac ≥ 0,5; unidas son **1.445**, intersección 1.247.
- La mejor celda de hielo está en el puesto 870 y la mejor de nieve en el 722.
- (b) sin «hielo»: quedan 8.924 parejas y 389 gemelos.
- (c) sin nieve ≥ 0,5: quedan 8.768 parejas y 381 gemelos.
- En ambas opciones el **top 5 y el top 50 no cambian**. Ninguna pista se rompe.

## P5. Referencia de elevación relativa, Rover (`w5_elev_ref.py`)

| | (a) cos lat (+695,9 m) | (b) cos lat × fracción de tierra (+810,7 m) | (c) nivel del mar (0 m) |
|---|---|---|---|
| emparejados | 10.192 | 10.240 | 10.198 |
| gemelos distintos | 401 | 426 | 292 |
| top 5 | sin cambios | Buga, Bayan Uula Sumu, Na'in, Banqiao, Bulgan (todos con M59895) | Panjgur, Aozou, Alaghsas, Mohammadabad, Sawakin (todos con M59895) |
| pistas rotas | — | 1 (→ puesto 7), 2 (→ 9), 3 (→ 10), 5 (→ 1); la pista 4 conserva su puesto y su gemelo | las cinco: puestos 306, 401, 373, 325 y 365; las pistas 4 y 5 cambian además de gemelo a M61037 |

Puntuaciones finales: en (b) van de 99,23 a 98,86; en (c) van de 99,56 a 99,41.

## P6. Puerta común elevation_m ≥ 1 → «tiene valor» (`w6_gate_elev.py`)
Hay 177 celdas de tierra con elevación < 1 m. Solo 37 de ellas tienen fracción de tierra ≥ 0,3; las demás siguen fuera por esa otra puerta.

| | Rover | Paneles | Base |
|---|---|---|---|
| pasan de más | +1 | +28 | +18 |
| emparejadas de más | +1 (puesto 439) | +3 (puestos 1.667, 3.171 y 4.906) | 0 |
| total emparejados | 10.193 | 6.363 | 449 (−1) |
| entran en el top 50 | no | no | no |
| top 50 idéntico | sí | sí | no |

En la Base cambia la población de percentiles de la Tierra. Los mismos cinco pares siguen arriba, pero 3 y 4 se intercambian (Tinghir pasa al 3 y Burenhayrhan al 4), así que **las pistas 3 y 4 quedan rotas**. Las pistas 1, 2 y 5 conservan el par, pero sus cifras cambian hasta +0,5 de similitud.

## Cómo volver a ejecutar
Hay que lanzar los scripts desde la raíz del repositorio con `PY=/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/bin/python`. Cada uno tarda unos 1 a 3 minutos. Las salidas y los logs van a `tierra luna/audit/out/w*_*.json|.log|.csv`.

```
$PY "tierra luna/audit/w0_reproduce.py"
$PY "tierra luna/audit/w1_zone.py"
$PY "tierra luna/audit/w2_separation.py"
$PY "tierra luna/audit/w3_rover_one_twin.py"
$PY "tierra luna/audit/w4_ice.py"
$PY "tierra luna/audit/w5_elev_ref.py"
$PY "tierra luna/audit/w6_gate_elev.py"
```

## No terminado / límites
- P2 usa el orden del bundle, que es idéntico al recálculo según w0. Las tablas completas por opción solo están en los JSON.
- P4 no se recalculó con el motor. Se derivó del bundle, lo cual es válido porque Rover no usa percentiles. Por eso se da el top 50, pero no el número de puesto nuevo de cada celda.
- No se estudiaron combinaciones de opciones entre preguntas.
- En P1 el área se mide con la geometría de la huella tal como viene en el GeoJSON, sin tener en cuenta su incertidumbre.
