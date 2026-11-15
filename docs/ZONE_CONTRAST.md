# Contraste de zonas en toda la Luna

Documento interno del equipo Stars Beside You (NASA Space Apps Challenge 2026), rama `final-integration`, 15-11-2026. Responde al encargo de Facundo de las 08:12 CET: contrastar cada misión en **toda la Luna**, salvo donde la misión sea imposible con un dato o una fuente; comprobar si la zona elegida es de verdad la mejor; y respaldar con datos el texto de la web que explica por qué no se va a las demás zonas. **Es un análisis: no se ha tocado motor, configuración, datos ni web, y no se ha cambiado ninguna zona.** Los avisos de abajo son para que Facundo decida; no recomiendan nada más.

**Método de Base lunar: provisional.** Cuando se calculó, `docs/LUNAR_BASE_PROPOSAL.md` no existía, así que Base lunar usa la regla del paquete publicado (z por cuerpo sobre elevación relativa, pendiente, rugosidad y temperatura, pesos 20 / 33,3 / 26,7 / 20 %, `ASSUMPTIONS.md` §0) y, al lado, la comparación en valores reales de temperatura media y amplitud diaria. **Esa parte hay que rehacerla cuando se confirme el método de Base lunar.** Tampoco existía `docs/MISSION_ZONES.md`, así que las regiones son las de la regla de respaldo (sección 1).

**Nota del comprobador (ver "Comprobación"):** los dos documentos aparecieron después (`MISSION_ZONES.md` a las 08:29 CET, `LUNAR_BASE_PROPOSAL.md` a las 08:36; este documento es de las 08:22). Las seis regiones A-F de `MISSION_ZONES.md` coinciden celda a celda con las de aquí (su D = los mares de las dos caras, aquí partidos en dos), así que **las cifras por región valen tal cual**; se añaden las filas de D completo. Para Base lunar se añade, al lado y sin sustituir nada, el diseño recomendado D4b de `LUNAR_BASE_PROPOSAL.md` (aviso 4), también sin confirmar.

## Resumen

Candidatos de la Tierra: los que pasan el embudo de cada misión (Rover 10.337, Paneles 18.777, Base lunar 2.419). "Parecido mediano" = similitud mediana de los candidatos emparejados con su mejor gemelo dentro de esa región. "Diferencia real" = |Tierra − gemelo| en la variable clave, mediana / percentil 90 de los pares. En **negrita**, la zona del equipo.

**Rover** (claves pendiente y rugosidad; tolerancias 2° y 30 m)

| región | celdas | emparejados | parecido mediano | diferencia real: pendiente; rugosidad | veredicto |
|---|---|---|---|---|---|
| **polo sur ≤ 75 S (zona)** | 5.400 | 10.192 (98,6 %) | 93,3 | 0,41 / 0,85°; 5,3 / 20,5 m | zona del equipo; no es la mejor por números |
| · de ella, las nueve regiones de NASA | 280 | 4.275 (41,4 %) | 89,8 | 0,78 / 1,54°; 9,5 / 24,5 m | solas emparejan menos de la mitad |
| · de ella, resto del polo sur | 5.120 | 10.161 | 93,3 | 0,41 / 0,85°; 5,4 / 20,5 m | — |
| polo norte ≥ 75 N | 5.400 | 9.888 (95,7 %) | 99,7 | 0,10 / 0,39°; 1,6 / 6,3 m | **AVISO 1**: más parecida y con sentido |
| mares, cara visible | 5.657 | 6.006 (58,1 %) | 89,1 | 0,09 / 0,24°; 1,5 / 3,8 m | peor: falla la elevación relativa (619 m de mediana) |
| mares, cara oculta | 1.029 | 5.955 (57,6 %) | 87,9 | 0,15 / 0,36°; 3,1 / 7,4 m | peor, misma causa (649 m) |
| latitudes medias y tierras altas, cara visible | 21.343 | 10.287 (99,5 %) | 99,9 | 0,07 / 0,21°; 1,0 / 3,2 m | **AVISO 1**, pero saturada |
| latitudes medias y tierras altas, cara oculta | 25.971 | 10.336 (99,99 %) | 99,7 | 0,10 / 0,27°; 1,5 / 4,5 m | **AVISO 1**, pero saturada |

**Paneles solares** (clave irradiancia sin atmósfera; tolerancia 0,6 kWh/m²/día)

| región | celdas | emparejados | parecido mediano | diferencia real en la irradiancia (kWh/m²/día) | veredicto |
|---|---|---|---|---|---|
| **mares, las dos caras (zona)** | 6.686 | 6.360 (33,9 %) | 99,9 | 0,021 / 0,322 | zona del equipo; empareja un tercio |
| · mares, cara visible | 5.657 | 6.356 | 99,9 | 0,021 / 0,322 | — |
| · mares, cara oculta | 1.029 | 6.360 | 99,7 | 0,028 / 0,322 | — |
| nueve regiones de NASA | 280 | 0 | — | — | imposible emparejar (dato) |
| resto del polo sur | 5.120 (15 en sombra permanente) | 0 | — | — | imposible emparejar; 15 celdas imposibles para la misión |
| polo norte | 5.400 | 0 | — | — | imposible emparejar (dato) |
| latitudes medias y tierras altas, cara visible | 21.343 | 18.776 (99,99 %) | 99,7 | 0,036 / 0,093 | **AVISO 2**: empareja casi todo, con sentido |
| latitudes medias y tierras altas, cara oculta | 25.971 | 18.776 | 99,4 | 0,037 / 0,088 | **AVISO 2** |

**Base lunar** (provisional; regla del paquete en z; la variable clave real es la térmica)

| región | celdas | emparejados (z, sin filtro) | parecido mediano (z) | diferencia real: temperatura media; amplitud diaria (K) | pares reales (≤ 10 K y ≤ 5 K) | veredicto |
|---|---|---|---|---|---|---|
| **nueve regiones de NASA (zona)** | 280 | 2.419 | 67,5 | 142,3 / 160,8; 164,5 / 191,1 | 0 | zona del equipo |
| resto del polo sur | 5.120 | 2.419 | 74,1 | 126,2 / 138,3; 193,4 / 208,8 | 0 (126 solo en amplitud) | los datos no la descartan |
| polo norte | 5.400 | 2.419 | 72,3 | 128,1 / 139,3; 189,1 / 202,1 | 0 | los datos no la descartan |
| mares, cara visible | 5.657 | 2.419 | 82,8 | 78,4 / 83,6; 271,6 / 279,4 | 0 | mejor en z, **no informativo** |
| mares, cara oculta | 1.029 | 2.419 | 82,7 | 79,3 / 85,3; 267,3 / 275,2 | 0 | ídem |
| latitudes medias y tierras altas, cara visible | 21.343 | 2.419 | 97,6 | 84,7 / 100,0; 254,8 / 277,6 | 0 | mejor en z, **no informativo** |
| latitudes medias y tierras altas, cara oculta | 25.971 | 2.419 | 97,7 | 83,9 / 91,0; 260,8 / 276,9 | 0 | ídem |

**Avisos (con números, antes de cambiar nada):**

1. **Rover: el polo norte (≥ 75 N) sale más parecido que la zona del equipo y tiene sentido** (es la otra región polar: temperatura media mediana 129,9 K frente a 130,6 K del polo sur fuera de las regiones de NASA; irradiancia mediana 0,80 frente a 0,89 kWh/m²/día). Empareja 9.888 candidatos (frente a 10.192), con parecido mediano 99,7 (frente a 93,3) y diferencias reales tres o cuatro veces menores (pendiente 0,10° frente a 0,41°; rugosidad 1,6 m frente a 5,3 m). Entre los 9.790 candidatos con par en las dos, el polo norte da un gemelo más parecido al 87,3 %, con 4,3 puntos más de mediana. Las tierras altas y latitudes medias salen aún mejor (10.287 y 10.336 emparejados, mediana 99,9 y 99,7), pero **por saturación**: tienen tantas celdas que casi todo candidato encuentra un gemelo casi idéntico y la similitud deja de distinguir (Spearman con la idoneidad +0,17 y −0,18). Buscando en toda la Luna, solo el 0,9 % de los candidatos (91) tiene su mejor gemelo dentro de la zona del equipo. **Los datos del terreno no favorecen el polo sur; lo justifican los planes de NASA** (Artemis IV, primer alunizaje tripulado, "near the South Pole of the Moon"; las nueve regiones candidatas están todas allí).
2. **Paneles solares: las latitudes medias y tierras altas emparejan a 18.776 de 18.777 candidatos, frente a 6.360 de los mares, y tiene sentido**: la luz sin atmósfera depende de la latitud, y estas regiones cubren de 1,0-1,2 a 10,40 kWh/m²/día, todo el rango de la Tierra sobre la atmósfera (4,14-9,97). Los mares solo reciben 9,05-10,40, el sol de los trópicos: solo emparejan candidatos a 33,5° o menos del ecuador. El parecido mediano está saturado en todas las regiones que emparejan (99,4-99,9), así que lo que discrimina es cuántos candidatos emparejan. Para los 6.360 candidatos que emparejan en los mares, la mejor alternativa fuera da la misma similitud de mediana (diferencia 0,0; fuera es mejor en el 37,8 %). Buscando en toda la Luna, el 21,1 % (3.958) tiene su mejor gemelo en los mares. Es la misma conclusión que `ANALOG_PRINCIPLE.md` (sección E, Luna entera).
3. **Base lunar (provisional): en la regla del paquete las tierras altas y los mares salen mucho más "parecidos" (97,6-97,7 y 82,7-82,8 frente a 67,5), pero la comparación no es informativa**: z compara la posición relativa en cada cuerpo. En valores reales ninguna región da un solo par térmico (0 de 2.419 con 10 K y 5 K, y 0 con el doble), y esas regiones están más cerca en temperatura media (diferencia mediana 78-85 K frente a 142 K) pero mucho más lejos en amplitud diaria (255-272 K frente a 165 K), que es lo que estresa el embudo de Base lunar (amplitud ≥ 15 K). Por amplitud, lo más cercano son las regiones polares: el resto del polo sur (126 candidatos con alguna celda a menos de 5 K en amplitud: 20 celdas junto a Haworth a 87,5 S, a 41-45 K de media, 15 nunca iluminadas y 5 iluminadas como mucho el 0,33 % del tiempo; los 126 coinciden con al menos una nunca iluminada) y el polo norte (hueco mínimo 43,7 K frente a 51,9 K de las nueve regiones). **Ninguna región es térmicamente mejor con sentido; los datos tampoco descartan las otras regiones polares, y la zona se justifica por los planes de NASA.**
4. **Base lunar con el diseño D4b que recomienda `LUNAR_BASE_PROPOSAL.md` (añadido por el comprobador; tampoco confirmado): las nueve regiones de NASA son la región que menos empareja.** D4b (percentil de mínima y amplitud dentro de cada población, 40 + 40, filtro 10 puntos; pendiente y rugosidad reales, 10 + 10, filtro 4° y 60 m), reproducido exactamente en las nueve regiones (450 pares, 103 gemelos, M62848 con 25, n.º 1 E17538-M63528 con 97,3) y en el polo sur entero (1.786) y la Luna entera (1.545). Por región: nueve regiones 450; resto del polo sur 1.787; polo norte 1.730; mares visibles 2.419, ocultos 2.340 (D completo 2.419); tierras altas visibles 1.620, ocultas 1.590. **No es una zona mejor con sentido:** con percentiles dentro de cada región la parte térmica siempre encuentra pareja por construcción, así que el recuento mide solo el terreno (las nueve regiones son las más rugosas: rugosidad mínima 91 m, mediana 262 m), y en valores reales los mares y las tierras altas están más cerca en temperatura media (73-93 K de diferencia mediana frente a 163 K) pero más lejos en amplitud (245-275 K frente a 154 K). Si se confirma D4b, la web no debe presentar "más pares fuera" como "mejor fuera".

**Imposibilidad probada** (lo demás se ha contrastado entero):

- **Paneles, 15 celdas del polo sur** (fuera de las regiones de NASA) con `illum_frac` = 0: ningún píxel de 240 m de la celda ve el Sol en 18,6 años de simulación sobre la topografía LOLA (Mazarico et al. 2011, `AVGVISIB_65S_240M_201608`; definición: "areas that never receive direct solar illumination"). Sin luz directa no hay ensayo de paneles. Excluidas de la búsqueda.
- **Paneles, emparejar es imposible por dato en 16.496 celdas**: toda celda con irradiancia < 3,537 kWh/m²/día (el candidato con menos sol recibe 4,137 sobre la atmósfera; menos la tolerancia de 0,6). Son las 10.800 celdas polares (≥ 75°; máximo 2,475) y 5.696 de las 7.200 celdas de 65,5-74,5° de latitud. Las polares están además por debajo del umbral del propio embudo solar (2,5 kWh/m²/día; valor de diseño del equipo, no validado). **Ojo:** es imposible a esta escala y con panel horizontal, no imposible para la energía solar en el polo: a 1° (unos 30 km) la celda promedia crestas iluminadas con cráteres oscuros, y los mejores puntos (Shackleton, "sunlit for more than 90 % of the year") no aparecen (`provenance_moon.csv`, nota de `illum_frac`).
- **Rover y Base lunar: ninguna región es imposible con un dato o una fuente.** En el Rover hay 158 celdas (96 del resto del polo sur, 27 del polo norte, 18 de las regiones de NASA, 13 de las tierras altas ocultas y 4 de las visibles) fuera del alcance de cualquier candidato (pendiente > 15,7° o rugosidad > 508 m) y 142 con pendiente media > 15°, el límite operativo de VIPER que usa el embudo; no prueba que sean intransitables (es la pendiente a 3,7 km de base de una celda de 30 km). Se han contrastado.

---

## 1. Regiones

Cada celda de 1° cae en exactamente una región; el orden de la regla decide (las regiones de NASA mandan sobre el polo sur, los polos sobre los mares y las tierras altas):

| región | regla | celdas |
|---|---|---|
| nueve regiones de NASA | las 280 celdas que tocan las nueve regiones candidatas anunciadas el 28-10-2024 (`proposal-verify/out/regions.json`; latitudes 82,5-88,5 S) | 280 |
| resto del polo sur | latitud ≤ −75 fuera de las anteriores | 5.120 |
| polo norte | latitud ≥ 75 | 5.400 |
| mares, cara visible | \|latitud\| ≤ 30, elevación ≤ −1.200 m, longitud entre −90 y 90 | 5.657 |
| mares, cara oculta | la misma regla de latitud y elevación, fuera de esas longitudes | 1.029 |
| latitudes medias y tierras altas, cara visible | el resto con longitud entre −90 y 90 | 21.343 |
| latitudes medias y tierras altas, cara oculta | el resto | 25.971 |
| total | | 64.800 |

Zonas del equipo: Rover = nueve regiones + resto del polo sur (5.400); Paneles = mares de las dos caras (6.686); Base lunar = nueve regiones (280).

Equivalencia con `docs/MISSION_ZONES.md` §2 (comprobada celda a celda; no hay celdas en longitud exactamente ±90): A = nueve regiones de NASA, B = resto del polo sur, C = polo norte, D = mares de las dos caras (5.657 + 1.029), E = tierras altas de la cara oculta (25.971), F = tierras altas de la cara visible (21.343).

## 2. Método y comprobación

- **Rover y Paneles**: el método decidido esta mañana, con el código del comprobador de `ANALOG_PRINCIPLE.md` (`scratchpad/stars/principle-check/ctx.py` y la lógica de `method.py`): por variable `exp(−0,5 (Δ/τ)²)`, claves 80 %, filtro del par (claves ≤ τ, secundarias ≤ 2τ), gemelo = la celda de la región que pasa el filtro con la similitud más alta (empate: id más bajo). Rover: pendiente 40 % (2°), rugosidad 40 % (30 m), elevación relativa 20 % (500 m; elevación menos la media ponderada por área de cada cuerpo). Paneles: irradiancia sin atmósfera 80 % (0,6; Tierra en el tope de la atmósfera con órbita de Kepler, Luna en la superficie), pendiente 10 %, rugosidad 10 %.
- **Base lunar** (provisional): regla del paquete (z por cuerpo, recortado a ±4 y redondeado a 4 decimales; población de la Tierra = tierra firme; similitud `100 exp(−0,45 d)`; sin filtro, así que todo candidato tiene gemelo en cualquier región) y, al lado, comparación en valores reales de temperatura media (10 K) y amplitud diaria (5 K).
- **Comprobación**: con estas regiones se reproducen las cifras de `ANALOG_PRINCIPLE.md`: Rover en el polo sur 10.192 emparejados, 401 gemelos, M61116 con el 19,9 %, mediana 93,3, Spearman −0,53; Paneles en los mares 6.360, 1.704 gemelos, M21795 con 159; Paneles en la Luna entera 18.776, 5.811 gemelos, M8436 con 1.524, Spearman +0,62. Base lunar en las nueve regiones reproduce **el paquete publicado**: los 2.419 gemelos idénticos y la similitud a menos de 0,005 (redondeo).
- Scripts y salidas: `scratchpad/stars/contrast/` (`regions.py`, `contrast.py`, `lunar_base.py`, `physics.py`, `cmp.py`; `res_*.json`, `pairs_*.csv`, `physics.json`, `log_*.txt`).

## 3. Rover (10.337 candidatos)

### 3.1 Búsqueda dentro de cada región

| región | emparejados | similitud mediana / p90 / máx | gemelos distintos | mayor cuota | Spearman similitud-idoneidad | pendiente (°) | rugosidad (m) | elevación relativa (m) | temperatura media (K, no entra) |
|---|---|---|---|---|---|---|---|---|---|
| nueve regiones de NASA | 4.275 | 89,8 / 97,8 / 99,95 | 85 | M64031 (Slater a 29 km): 1.270, 29,7 % | −0,30 | 0,78 / 1,54 | 9,5 / 24,5 | 275 / 669 | 166 / 193 |
| resto del polo sur | 10.161 | 93,3 / 99,2 / 100 | 375 | M61116 (Ganswindt a 81 km): 2.033, 20,0 % | −0,53 | 0,41 / 0,85 | 5,4 / 20,5 | 250 / 798 | 148 / 175 |
| **zona (≤ 75 S)** | 10.192 | 93,3 / 99,2 / 100 | 401 | M61116: 2.033, 19,9 % | −0,53 | 0,41 / 0,85 | 5,3 / 20,5 | 248 / 799 | 149 / 176 |
| polo norte | 9.888 | 99,7 / 99,95 / 100 | 1.002 | M4549 (De Sitter a 95 km): 579, 5,9 % | +0,04 | 0,10 / 0,39 | 1,6 / 6,3 | 44 / 317 | 142 / 164 |
| mares, cara visible | 6.006 | 89,1 / 94,4 / 97,3 | 140 | M30462 (Lawrence a 61 km): 669, 11,1 % | +0,27 | 0,09 / 0,24 | 1,5 / 3,8 | 619 / 911 | 62 / 85 |
| mares, cara oculta | 5.955 | 87,9 / 93,3 / 96,5 | 75 | M29838 (Catena Mendeleev a 34 km): 1.587, 26,6 % | +0,30 | 0,15 / 0,36 | 3,1 / 7,4 | 649 / 938 | 64 / 85 |
| mares, las dos caras (región D de `MISSION_ZONES.md`; añadido por el comprobador) | 6.006 | 89,1 / 94,4 / 97,3 | 145 | M30462: 669, 11,1 % | +0,27 | 0,09 / 0,23 | 1,4 / 3,7 | 619 / 910 | 62 / 85 |
| tierras altas, cara visible | 10.287 | 99,9 / 99,98 / 100 | 2.610 | M49436 (Wargentin a 87 km): 140, 1,4 % | +0,17 | 0,07 / 0,21 | 1,0 / 3,2 | 24 / 77 | 80 / 109 |
| tierras altas, cara oculta | 10.336 | 99,7 / 99,93 / 100 | 1.939 | M48874 (Mare Australe a 86 km): 347, 3,4 % | −0,18 | 0,10 / 0,27 | 1,5 / 4,5 | 39 / 114 | 83 / 112 |
| Luna entera | 10.337 | 99,9 / 99,98 / 100 | 3.647 | M49436: 140, 1,4 % | +0,11 | 0,06 / 0,16 | 0,9 / 2,5 | 20 / 62 | 84 / 139 |

Diferencias: mediana / percentil 90 de |Tierra − gemelo| sobre los pares que sobreviven.

**Top 3 por región** (final = 0,5 similitud + 0,5 idoneidad; pendiente y rugosidad Tierra / gemelo):

- Nueve regiones de NASA: E49428 (47,5 S 71,5 O, Patagonia) con M64032 (87,5 S 132,5 E, Slater a 30 km): 2,93 / 3,32°, 109,0 / 112,0 m, similitud 99,0; E27228 (14,5 N 48,5 E, Yemen) con M64032: 3,03 / 3,32°, 114,0 / 112,0 m; E16834 (43,5 N 94,5 E) con M62516 (Wapowski a 16 km): 3,24 / 3,48°, 109,3 / 109,0 m.
- Zona y resto del polo sur: E17566 (41,5 N 106,5 E, Mongolia Interior), E23945 (23,5 N 5,5 E, Ahaggar) y E18282 (39,5 N 102,5 E), los tres con M59895 (76,5 S 44,5 O, Casatus a 159 km): 1,04 / 1,15°, 43,5 / 44,2 m (similitud 99,6); 1,22 / 1,15°, 43,4 / 44,2 m; 0,91 / 1,15°, 38,8 / 44,2 m.
- Polo norte: E6903 (70,5 N 116,5 O) con M3437 (80,5 N 17,5 E, Main a 37 km): 0,95 / 0,95°, 30,1 / 30,4 m, similitud 99,99; E9078 (64,5 N 101,5 O) con M3438: 0,59 / 0,60°, 19,5 / 18,8 m; E11626 (57,5 N 73,5 O) con M4135 (Challis a 85 km): 0,50 / 0,45°, 18,7 / 18,3 m.
- Mares, cara visible: E16791 (43,5 N 51,5 E) con M30462 (5,5 N 42,5 E): 0,58 / 0,51°, 23,2 / 23,1 m, pero elevación relativa −687 / −953 m (similitud 97,3); E4035 y E4750 (Ártico canadiense) con el mismo gemelo.
- Mares, cara oculta: E16791, E6191 y E4035 con M29838 (7,5 N 138,5 E): 0,58 / 0,76°, 23,2 / 27,7 m (similitud 96,5).
- Tierras altas, cara visible: E5832 (73,5 N 107,5 O) con M7334 (69,5 N 45,5 O, Carpenter a 61 km): 0,65 / 0,65°, 21,8 / 21,9 m, similitud 100,0; E4742 con M30099 (6,5 N 39,5 E): 0,56 / 0,55°, 20,8 / 20,9 m; E4038 con M30775: 0,68 / 0,69°, 26,1 / 26,3 m.
- Tierras altas, cara oculta: E21096 (31,5 N 36,5 E) con M49240 (46,5 S 100,5 E): 0,51 / 0,46°, 15,7 / 15,5 m; E3872 con M48874: 0,57 / 0,62°; E23973 con M51764: 0,52 / 0,45°.

### 3.2 Búsqueda en toda la Luna

- Región del mejor gemelo de cada candidato: tierras altas, cara visible 6.186 (59,8 %); tierras altas, cara oculta 2.379 (23,0 %); polo norte 1.681 (16,3 %); resto del polo sur 79; nueve regiones de NASA 12. **Dentro de la zona del equipo: 91 (0,9 %).** Mares: 0.
- 10.191 candidatos tienen par dentro de la zona y fuera: similitud en la zona 93,3 de mediana frente a 99,9 de la mejor de fuera; diferencia mediana 6,5 puntos (percentil 90: 18,6); fuera es mejor en el 99,1 %. 145 candidatos solo tienen par fuera (los más lisos de la Tierra).
- Comparación por pares de regiones con la zona (candidatos con par en las dos): polo norte mejor en el 87,3 % de 9.790 (+4,3 de mediana); tierras altas visibles en el 97,1 % (+6,2); ocultas en el 97,6 % (+6,2); mares visibles en el 43,2 % (−1,3); mares ocultos en el 39,4 % (−2,3).

### 3.3 Veredicto Rover

La zona del polo sur **no es la mejor por los números del terreno**: el polo norte y las tierras altas emparejan igual o más con diferencias reales menores. Las tierras altas puntúan alto por saturación (mediana 99,7-99,9; la similitud ya no ordena). El polo norte es la alternativa con sentido físico (otra región polar con Sol rasante y frío) y no está saturado del todo (p90 99,95). La razón para el polo sur no está en estos datos: son los planes de NASA. Las nueve regiones de NASA solas emparejan solo el 41,4 %: son la región más abrupta de las siete (pendiente mediana 9,5°).

## 4. Paneles solares (18.777 candidatos)

### 4.1 Búsqueda dentro de cada región

Celdas en sombra permanente excluidas (15, todas en el resto del polo sur). Diferencias: mediana / percentil 90.

| región | emparejados | similitud mediana / p90 / máx (mín) | gemelos distintos | mayor cuota | Spearman | irradiancia sin atmósfera | pendiente (°) | rugosidad (m) | irradiancia en el suelo (no entra) | temperatura (no entra, K) |
|---|---|---|---|---|---|---|---|---|---|---|
| nueve regiones, resto del polo sur, polo norte | 0 | — | — | — | — | — | — | — | — | — |
| mares, cara visible | 6.356 | 99,93 / 99,99 / 100 (58,0) | 1.535 | M21795 (Banting a 92 km): 159, 2,5 % | +0,18 | 0,021 / 0,322 | 0,04 / 0,18 | 0,5 / 2,6 | 4,31 / 5,61 | 85 / 90 |
| mares, cara oculta | 6.360 | 99,72 / 99,96 / 100 (68,9) | 467 | M43180 (O'Day a 89 km): 921, 14,5 % | +0,11 | 0,028 / 0,322 | 0,15 / 0,37 | 3,0 / 11,0 | 4,31 / 5,60 | 85 / 90 |
| **zona (mares, las dos caras)** | 6.360 | 99,93 / 99,99 / 100 (69,0) | 1.704 | M21795: 159, 2,5 % | +0,16 | 0,021 / 0,322 | 0,03 / 0,15 | 0,5 / 2,4 | 4,31 / 5,60 | 85 / 90 |
| tierras altas, cara visible | 18.776 | 99,73 / 99,97 / 100 (87,5) | 4.115 | M8436 (Fontenelle a 110 km): 1.524, 8,1 % | +0,40 | 0,036 / 0,093 | 0,09 / 0,41 | 1,8 / 14,5 | 3,13 / 4,95 | 84 / 90 |
| tierras altas, cara oculta | 18.776 | 99,43 / 99,93 / 100 (87,3) | 2.522 | M56093 (Vallis Schrödinger a 111 km): 3.198, 17,0 % | +0,14 | 0,037 / 0,088 | 0,22 / 0,61 | 5,5 / 19,7 | 3,12 / 4,95 | 84 / 91 |
| Luna entera (celdas con luz) | 18.776 | 99,83 / 99,99 / 100 (87,5) | 5.811 | M8436: 1.524, 8,1 % | +0,62 | 0,027 / 0,085 | 0,05 / 0,31 | 0,9 / 11,1 | 3,13 / 4,95 | 84 / 89 |

Los mares solo emparejan candidatos a 33,5° o menos del ecuador. El único candidato sin par en ninguna región es E19334 (36,5 N 74,5 E, Karakórum).

**Top 3 por región** (irradiancia sin atmósfera Tierra / Luna; en todas el mismo trío de la Tierra, que es lo que manda la idoneidad):

- Zona y mares visibles: E38464 (16,5 S 124,5 E, Kimberley) con M24296 (22,5 N 3,5 O, Huxley a 76 km): 9,60 / 9,60, pendiente 0,98 / 1,05°, rugosidad 39,2 / 39,0 m, similitud 99,99; E38105 con M24583 (21,5 N 76,5 O): 9,64 / 9,67; E38744 (17,5 S 44,5 E, Madagascar) con M40854 (23,5 S 5,5 O): 9,55 / 9,53.
- Mares ocultos: E38464 con M40404 (22,5 S 95,5 O, Mare Orientale a 83 km): 9,60 / 9,60, 0,98 / 0,87°; E38105 con M40048; E37746 con M24761.
- Tierras altas visibles: E38464 con M40567 (22,5 S 67,5 E, Balmer a 102 km): 9,60 / 9,60, 0,98 / 1,06°, 39,2 / 41,4 m; E38105 con M40206; E38744 con M40912.
- Tierras altas ocultas: E38464 con M24401 (22,5 N 101,5 E, Dziewulski a 84 km): 9,60 / 9,60; E38105 con M24769; E38465 con M24401.

### 4.2 Búsqueda en toda la Luna

- Región del mejor gemelo: tierras altas visibles 9.987 (53,2 %), ocultas 4.831 (25,7 %), mares visibles 3.610 (19,2 %), mares ocultos 348 (1,9 %). **Dentro de la zona del equipo: 3.958 (21,1 %).** Polos y regiones de NASA: 0.
- Los 6.360 candidatos con par en la zona también lo tienen fuera: diferencia mediana entre el mejor de toda la Luna y el de la zona 0,0 puntos (percentil 90: 11,5); fuera es mejor en el 37,8 %. Frente a las tierras altas visibles, la zona es igual o mejor en el 65 % (diferencia mediana −0,03). 12.416 candidatos solo tienen par fuera de la zona.

### 4.3 Veredicto Paneles

La zona de los mares **es tan buena como cualquier otra para los candidatos tropicales, pero solo empareja a un tercio**; las latitudes medias y tierras altas emparejan a todos menos uno con diferencias reales igual de pequeñas (0,04 kWh/m²/día de mediana). La similitud está saturada en todas las regiones que emparejan; la cifra que discrimina es el número de emparejados. Los polos y las regiones de NASA quedan descartados por dato: su sol (máximo 2,475) está a más de la tolerancia del candidato con menos sol (4,137). La fracción de iluminación no ayuda a elegir entre mares y tierras altas: por debajo de 65° es geometría de suelo plano (0,50 en todas las celdas).

## 5. Base lunar (2.419 candidatos; provisional)

### 5.1 Regla del paquete (z por cuerpo) dentro de cada región

| región | similitud mediana / p90 / máx (mín) | gemelos distintos | mayor cuota | Spearman | temperatura media (K) | amplitud (K) | pendiente (°) | rugosidad (m) | elevación relativa (m) |
|---|---|---|---|---|---|---|---|---|---|
| **nueve regiones de NASA** | 67,5 / 79,6 / 94,3 (55,9) | 48 | M62515 (Wapowski a 14 km): 671, 27,7 % | +0,04 | 142,3 / 160,8 | 164,5 / 191,1 | 6,6 / 10,9 | 172 / 276 | 845 / 1.759 |
| resto del polo sur | 74,1 / 82,0 / 93,2 (62,7) | 65 | M59734 (Schrödinger a 169 km): 379, 15,7 % | −0,15 | 126,2 / 138,3 | 193,4 / 208,8 | 5,8 / 11,0 | 159 / 266 | 626 / 1.115 |
| polo norte | 72,3 / 80,9 / 88,8 (49,2) | 45 | M5254 (Baillaud a 35 km): 520, 21,5 % | −0,22 | 128,1 / 139,3 | 189,1 / 202,1 | 5,5 / 9,8 | 167 / 264 | 266 / 1.264 |
| mares, cara visible | 82,8 / 97,0 / 99,6 (34,9) | 156 | M29044 (van Albada a 6 km): 361, 14,9 % | −0,22 | 78,4 / 83,6 | 271,6 / 279,4 | 5,2 / 8,8 | 157 / 251 | 1.368 / 4.130 |
| mares, cara oculta | 82,7 / 96,2 / 99,7 (34,6) | 99 | M42827 (Zelinskiy a 18 km): 301, 12,4 % | −0,23 | 79,3 / 85,3 | 267,3 / 275,2 | 5,0 / 8,8 | 156 / 241 | 1.357 / 4.001 |
| mares, las dos caras (región D; añadido por el comprobador) | 82,9 / 97,1 / 99,7 | 184 | M29044: 246, 10,2 % | — | 79,1 / 83,8 | 268,8 / 278,6 | — | — | — |
| tierras altas, cara visible | 97,6 / 98,8 / 99,6 (61,7) | 1.138 | M55897 (Hausen a 77 km): 197, 8,1 % | −0,20 | 84,7 / 100,0 | 254,8 / 277,6 | 5,4 / 10,0 | 161 / 253 | 362 / 926 |
| tierras altas, cara oculta | 97,7 / 98,8 / 99,7 (66,2) | 1.246 | M39979 (Walker a 137 km): 100, 4,1 % | −0,23 | 83,9 / 91,0 | 260,8 / 276,9 | 5,3 / 10,7 | 163 / 261 | 382 / 1.212 |
| Luna entera | 98,2 / 99,1 / 99,7 (76,8) | 1.493 | M63218 (Masina a 15 km): 87, 3,6 % | −0,24 | 84,1 / 93,9 | 258,0 / 277,5 | 5,4 / 11,2 | 162 / 276 | 417 / 1.333 |

Top 3: nueve regiones de NASA: E19345 (36,5 N 85,5 E, borde del Tíbet) con M62859 (84,5 S 39,5 E, Floss a 11 km), similitud 83,8, temperatura 271,7 / 152,5 K, amplitud 27,1 / 187,1 K; E19704 con M62858 (272,8 / 150,1 K); E19699 con M63218 (271,8 / 167,5 K). Tierras altas ocultas (y Luna entera): E40431 (22,5 S 68,5 O, Atacama) con M38175 (16,5 S 164,5 O, Mohorovičić a 68 km), similitud 97,2, temperatura 292,9 / 212,0 K, amplitud 33,7 / 290,2 K; E41150 (Yungay) con M33817; E40790 con M31299. Mares visibles: E17190 (42,5 N 90,5 E) con M43095, 291,6 / 205,8 K y 26,5 / 282,8 K. Polo norte: E18992 (37,5 N 92,5 E) con M5041, 283,5 / 157,2 K y 31,6 / 205,4 K. Resto del polo sur: E18634 (38,5 N 94,5 E) con M59931, 281,5 / 159,7 K y 29,2 / 206,7 K.

### 5.2 Comparación en valores reales (temperatura media y amplitud diaria)

Candidatos de la Tierra: temperatura 264,1-305,1 K (mediana 288,7), amplitud 15,0-35,7 K (mediana 19,3).

| región | temperatura máxima de la región (K) | hueco de temperatura: mínimo / mediana de los candidatos (K) | hueco de amplitud: mínimo / mediana (K) | candidatos con temperatura ≤ 10 K y amplitud ≤ 5 K | con 20 K y 10 K | solo amplitud ≤ 5 K |
|---|---|---|---|---|---|---|
| nueve regiones de NASA | 167,5 | 96,6 / 121,3 | 51,9 / 68,3 | 0 | 0 | 0 |
| resto del polo sur | 172,2 | 91,8 / 116,5 | 0,01 / 11,4 | 0 | 0 | 126 |
| polo norte | 164,8 | 99,3 / 123,9 | 43,7 / 60,1 | 0 | 0 | 0 |
| mares, cara visible | 223,9 | 40,2 / 64,9 | 226,2 / 242,5 | 0 | 0 | 0 |
| mares, cara oculta | 220,5 | 43,6 / 68,3 | 242,3 / 258,7 | 0 | 0 | 0 |
| tierras altas, cara visible | 222,0 | 42,1 / 66,8 | 150,3 / 166,6 | 0 | 0 | 0 |
| tierras altas, cara oculta | 223,6 | 40,5 / 65,2 | 140,7 / 157,1 | 0 | 0 | 0 |

Los 126 candidatos del resto del polo sur solo coinciden en amplitud con 20 celdas junto a Haworth a 87,5 S (41-45 K; 15 nunca iluminadas y 5 con fracción de iluminación ≤ 0,0033; los 126 tienen al menos una nunca iluminada), como ya dice `ANALOG_PRINCIPLE.md` D.3: un régimen físico distinto, no un análogo.

### 5.3 Búsqueda en toda la Luna (regla del paquete)

Región del mejor gemelo: tierras altas ocultas 1.301 (53,8 %), visibles 889 (36,8 %), **nueve regiones de NASA 99 (4,1 %)**, mares visibles 83, ocultos 47. Diferencia mediana entre el mejor de toda la Luna y el de las nueve regiones: 30,7 puntos (percentil 90: 39,3); fuera es mejor en el 95,9 %.

### 5.4 Veredicto Base lunar (provisional)

Con la regla del paquete, las nueve regiones **no** son las mejores (67,5 frente a 97,6-97,7 en las tierras altas), pero esa ventaja es de posición relativa en z y no se sostiene en valores reales: ninguna región da un par térmico, y las regiones que ganan en z están más lejos en amplitud diaria. Por los datos reales, las tres regiones polares son equivalentes (temperatura máxima 165-172 K, huecos parecidos); ninguna lo es por sentido físico frente a las otras. La zona se justifica por los planes de NASA. **Repetir con el método que se confirme.**

## 6. Valores físicos por región (para citar en la web)

Mediana (mínimo-máximo) de las celdas de cada región, **sin ponderar por área** y con la pendiente `slope_iso_deg`. `MISSION_ZONES.md` §2 da medianas **ponderadas por área** (cos latitud) y con `slope_deg`, y salen distintas en los polos (irradiancia mediana: nueve regiones 0,53 frente a 0,40 aquí, resto del polo sur 1,32 frente a 0,89, polo norte 1,38 frente a 0,80; pendiente de las nueve regiones 10,6° frente a 9,5°): las dos son correctas para su definición, pero la web debe citar una sola. Los máximos y mínimos que usan las frases no dependen de la ponderación. Irradiancia en kWh/m²/día sobre superficie horizontal sin atmósfera; elevación relativa a la media lunar ponderada por área (−248,4 m sobre la esfera de 1.737,4 km).

| región | pendiente (°) | rugosidad (m) | elevación relativa (m) | irradiancia | fracción de iluminación | temperatura media (K) | amplitud diaria (K) | temperatura mínima (K) |
|---|---|---|---|---|---|---|---|---|
| nueve regiones de NASA | 9,5 (3,1-21,4) | 262 (91-569) | 848 (−1.967 a 6.345) | 0,40 (0,01-1,03) | 0,29 (0,01-0,43) | 128,9 (53,6-167,5) | 178,5 (87,6-233,6) | 58,8 (32,9-75,2) |
| resto del polo sur | 6,3 (0,2-22,8) | 196 (7-616) | −1.208 (−6.151 a 4.783) | 0,89 (0-2,48) | 0,32 (0-0,47) | 130,6 (41,1-172,2) | 186,8 (30,7-242,9) | 60,1 (26,8-84,7) |
| polo norte | 4,5 (0,3-19,1) | 153 (9-565) | −565 (−4.070 a 2.510) | 0,80 (0,02-2,45) | 0,31 (0,03-0,47) | 129,9 (58,1-164,8) | 180,3 (79,4-232,5) | 60,2 (34,4-89,1) |
| mares, cara visible | 0,9 (0,05-13,5) | 35 (2-401) | −1.594 (−4.583 a −952) | 10,02 (9,05-10,40) | 0,50 | 216,0 (203,1-223,9) | 295,1 (261,9-311,8) | 93,9 (89,4-111,7) |
| mares, cara oculta | 4,2 (0,1-12,7) | 146 (4-385) | −1.819 (−5.076 a −952) | 9,60 (9,05-10,40) | 0,50 | 212,4 (202,3-220,5) | 290,1 (278,0-305,1) | 92,4 (87,1-102,7) |
| mares, las dos caras | 1,1 (0,05-13,5) | 46 (2-401) | −1.611 (−5.076 a −952) | 9,97 (9,05-10,40) | 0,50 | 215,4 (202,3-223,9) | 294,4 (261,9-311,8) | 93,7 (87,1-111,7) |
| tierras altas, cara visible | 3,9 (0,1-17,0) | 132 (2-504) | −649 (−4.499 a 5.256) | 7,29 (1,18-10,40) | 0,50 (0,21-0,50) | 197,5 (130,3-222,0) | 264,8 (186,0-302,7) | 88,0 (56,6-114,0) |
| tierras altas, cara oculta | 6,0 (0,2-22,0) | 188 (4-574) | 693 (−7.927 a 9.350) | 8,14 (1,01-10,40) | 0,50 (0,18-0,50) | 202,6 (122,9-223,6) | 273,3 (176,4-304,6) | 89,3 (57,9-110,1) |

Fracción de iluminación: LOLA con topografía en \|latitud\| ≥ 65,5° (las tres regiones polares y 3.600 celdas de cada región de tierras altas); por debajo, geometría de suelo plano (≈ 0,50). Celdas con fracción 0: 15, todas en el resto del polo sur. Temperaturas de Diviner; pendiente y rugosidad de LOLA.

Para comparar, candidatos de la Tierra: Rover pendiente 0,50-13,7° (mediana 1,57), rugosidad 12-478 m (63,6); Paneles irradiancia sobre la atmósfera 4,14-9,97 (6,76), en el suelo 2,50-6,44 (3,75); Base lunar temperatura 264-305 K, amplitud 15-36 K.

## 7. Frases para la web (inglés, con traducción)

Una por misión y región; como mucho 40 palabras, con la cifra.

**Rover**

| región | frase | traducción |
|---|---|---|
| zona (polo sur) | Rover twins are searched south of 75° S, where NASA plans the first crewed Artemis landing; 10,192 of 10,337 Earth sites find a twin with slope within 2° and roughness within 30 m. | Los gemelos del Rover se buscan al sur de 75° S, donde NASA planea el primer alunizaje tripulado de Artemis; 10.192 de 10.337 sitios encuentran gemelo con la pendiente a menos de 2° y la rugosidad a menos de 30 m. |
| nueve regiones de NASA | NASA's nine candidate landing regions are part of the rover zone; alone they are too rugged (median slope 9.5°) to pair more than 4,275 of 10,337 Earth sites. | Las nueve regiones candidatas de NASA forman parte de la zona del Rover; solas son demasiado abruptas (pendiente mediana 9,5°) para emparejar más de 4.275 de 10.337 sitios. |
| polo norte | The data do not rule the north pole out: 9,888 of 10,337 Earth sites find a terrain twin there. The team chose the south pole because NASA's Artemis landings are planned there. | Los datos no descartan el polo norte: 9.888 de 10.337 sitios encuentran allí un gemelo de terreno. El equipo eligió el polo sur porque NASA planea allí los alunizajes de Artemis. |
| mares, cara visible | Only 6,006 of 10,337 Earth sites find a twin in the near-side maria: these plains lie 950 to 4,600 m below the lunar mean, far lower than the Earth sites. | Solo 6.006 de 10.337 sitios encuentran gemelo en los mares de la cara visible: estas llanuras están entre 950 y 4.600 m por debajo de la media lunar, mucho más bajas que los sitios de la Tierra. |
| mares, cara oculta | Only 5,955 of 10,337 Earth sites find a twin in the far-side maria, low plains 950 to 5,100 m below the lunar mean. | Solo 5.955 de 10.337 sitios encuentran gemelo en los mares de la cara oculta, llanuras entre 950 y 5.100 m por debajo de la media lunar. |
| tierras altas, cara visible | The data do not rule this region out: 10,287 of 10,337 Earth sites find a near-identical terrain twin (median slope difference 0.07°). The team chose the south pole because NASA's Artemis landings are planned there. | Los datos no descartan esta región: 10.287 de 10.337 sitios encuentran un gemelo de terreno casi idéntico (diferencia mediana de pendiente 0,07°). El equipo eligió el polo sur porque NASA planea allí los alunizajes de Artemis. |
| tierras altas, cara oculta | The data do not rule this region out: 10,336 of 10,337 Earth sites find a terrain twin (median slope difference 0.10°). The team chose the south pole because NASA's Artemis landings are planned there. | Los datos no descartan esta región: 10.336 de 10.337 sitios encuentran gemelo de terreno (diferencia mediana de pendiente 0,10°). El equipo eligió el polo sur porque NASA planea allí los alunizajes de Artemis. |

**Paneles solares**

| región | frase | traducción |
|---|---|---|
| zona (mares) | Solar twins are searched in the equatorial maria, flat lava plains (median slope 1.1°) receiving 9.0–10.4 kWh/m²/day; 6,360 of 18,777 Earth sites, those within 33.5° of the equator, find one. | Los gemelos solares se buscan en los mares ecuatoriales, llanuras de lava (pendiente mediana 1,1°) que reciben 9,0-10,4 kWh/m²/día; 6.360 de 18.777 sitios, los que están a 33,5° o menos del ecuador, encuentran uno. |
| nueve regiones de NASA | NASA's south-polar landing regions receive only 0.40 kWh/m²/day on a level surface (at most 1.03); every Earth solar site gets at least 4.1 above the atmosphere, so no pair is possible at this scale. | Las regiones de alunizaje de NASA en el polo sur reciben solo 0,40 kWh/m²/día sobre superficie horizontal (como mucho 1,03); todo sitio solar de la Tierra recibe al menos 4,1 sobre la atmósfera, así que a esta escala no hay par posible. |
| resto del polo sur | South of 75° S a level surface receives at most 2.48 kWh/m²/day, and 15 cells never see the Sun; no Earth solar site (at least 4.1 above the atmosphere) can pair here. | Al sur de 75° S una superficie horizontal recibe como mucho 2,48 kWh/m²/día, y 15 celdas nunca ven el Sol; ningún sitio solar de la Tierra (al menos 4,1 sobre la atmósfera) puede emparejarse aquí. |
| polo norte | North of 75° N a level surface receives at most 2.45 kWh/m²/day, below the 4.1 that even the least sunny Earth solar site gets above the atmosphere. | Al norte de 75° N una superficie horizontal recibe como mucho 2,45 kWh/m²/día, menos de los 4,1 que recibe sobre la atmósfera hasta el sitio solar menos soleado de la Tierra. |
| tierras altas, cara visible | The data do not rule this region out: 18,776 of 18,777 Earth sites find a sunlight twin here. The team chose the equatorial maria, flatter plains (median slope 1.1° against 3.9° here). | Los datos no descartan esta región: 18.776 de 18.777 sitios encuentran aquí un gemelo de luz. El equipo eligió los mares ecuatoriales, llanuras más planas (pendiente mediana 1,1° frente a 3,9° aquí). |
| tierras altas, cara oculta | The data do not rule this region out: 18,776 of 18,777 Earth sites find a sunlight twin here. The team chose the equatorial maria, flatter plains (median slope 1.1° against 6.0° here). | Los datos no descartan esta región: 18.776 de 18.777 sitios encuentran aquí un gemelo de luz. El equipo eligió los mares ecuatoriales, más planos (pendiente mediana 1,1° frente a 6,0° aquí). |

(Los mares de cada cara son parte de la zona: no llevan frase de "por qué no".) **Pendiente de Facundo:** el motivo de elegir los mares no figura en `DECISIONS.md`; si no es la llanura, hay que cambiar la segunda frase de las dos filas de tierras altas.

**Base lunar** (provisional: las cifras térmicas son reales y no dependen del método de similitud)

| región | frase | traducción |
|---|---|---|
| zona (nueve regiones de NASA) | Lunar base twins are searched in the nine south-polar regions NASA announced in October 2024 for the first crewed landing; no Earth site matches their cold (warmest cell 167 K), so the twin is the closest available. | Los gemelos de la base se buscan en las nueve regiones del polo sur que NASA anunció en octubre de 2024 para el primer alunizaje tripulado; ningún sitio de la Tierra iguala su frío (celda más cálida, 167 K), así que el gemelo es el más cercano disponible. |
| resto del polo sur | The data do not rule this region out: it is as cold as NASA's regions (warmest cell 172 K against 167 K). The team chose NASA's nine candidate landing regions because the first crewed landing is planned there. | Los datos no descartan esta región: es tan fría como las de NASA (celda más cálida 172 K frente a 167 K). El equipo eligió las nueve regiones candidatas porque allí se planea el primer alunizaje tripulado. |
| polo norte | The data do not rule this region out: it is as cold as NASA's regions (warmest cell 165 K against 167 K). The team chose NASA's nine candidate landing regions because the first crewed landing is planned there. | Los datos no descartan esta región: es tan fría como las de NASA (celda más cálida 165 K frente a 167 K). El equipo eligió las nueve regiones porque allí se planea el primer alunizaje tripulado. |
| mares, cara visible | Near-side maria swing 262–312 K between day and night, against 88–234 K in NASA's regions and at most 36 K at the Earth test sites; no lunar region matches Earth, so the team follows NASA's nine candidate landing regions. | Los mares de la cara visible oscilan 262-312 K entre el día y la noche, frente a 88-234 K en las regiones de NASA y 36 K como mucho en los sitios de ensayo de la Tierra; ninguna región lunar iguala a la Tierra, así que el equipo sigue las nueve regiones candidatas de NASA. |
| mares, cara oculta | Far-side maria swing 278–305 K between day and night, against 88–234 K in NASA's regions and at most 36 K at the Earth test sites; no lunar region matches Earth, so the team follows NASA's nine candidate landing regions. | Los mares de la cara oculta oscilan 278-305 K entre día y noche, frente a 88-234 K en las regiones de NASA y 36 K como mucho en la Tierra; ninguna región lunar iguala a la Tierra, así que el equipo sigue las nueve regiones de NASA. |
| tierras altas, cara visible | These highlands swing 186–303 K between day and night, against 88–234 K in NASA's regions and at most 36 K at the Earth test sites; no lunar region matches Earth, so the team follows NASA's nine candidate landing regions. | Estas tierras altas oscilan 186-303 K entre día y noche, frente a 88-234 K en las regiones de NASA y 36 K como mucho en la Tierra; ninguna región lunar iguala a la Tierra, así que el equipo sigue las nueve regiones de NASA. |
| tierras altas, cara oculta | These highlands swing 176–305 K between day and night, against 88–234 K in NASA's regions and at most 36 K at the Earth test sites; no lunar region matches Earth, so the team follows NASA's nine candidate landing regions. | Estas tierras altas oscilan 176-305 K entre día y noche, frente a 88-234 K en las regiones de NASA y 36 K como mucho en la Tierra; ninguna región lunar iguala a la Tierra, así que el equipo sigue las nueve regiones de NASA. |

Nota de fuentes para las frases de NASA: comunicado 24-136 (28-10-2024, las nueve regiones) y página de Artemis IV ("near the South Pole of the Moon", aterrizaje a principios de 2028), citados en `docs/SIMILARITY_PROPOSAL.md` §1.1; si la web dice "Artemis III", debe aclarar el cambio de nombre como allí.

## 8. Límites

- Escala de 1° (unos 30 km): una celda promedia crestas y cráteres; la imposibilidad solar en los polos es de esta escala y del panel horizontal.
- La similitud satura en las regiones grandes (medianas ≥ 99,4): ahí el número de emparejados y las diferencias reales dicen más que el porcentaje.
- La temperatura no entra en la similitud del Rover ni de Paneles; se da como diferencia (62-166 K de mediana según misión y región).
- Base lunar depende de un método aún no confirmado; la comparación real de temperatura y amplitud sí es definitiva para estos datos.
- Las regiones son las de respaldo; si `docs/MISSION_ZONES.md` fija otras, hay que recalcular (los scripts aceptan otra columna de región).

## Comprobación

Comprobador independiente, 15-11-2026. Código propio en `scratchpad/stars/contrast-check/` (`check.py`, `d4b.py`, `lbD.py`; salidas `check.json`, `d4b.json`, `log.txt`), escrito sin mirar el del redactor; reutiliza solo la carga de tablas y la función de similitud en valores reales de `scratchpad/stars/principle-check/` (`ctx.py`, `method.run`). Los candidatos de la Tierra son los del embudo de cada misión (Rover 10.337, Paneles 18.777, Base lunar 2.419).

**Regiones.** Máscaras recalculadas con la regla de la sección 1: 280 / 5.120 / 5.400 / 5.657 / 1.029 / 21.343 / 25.971, total 64.800, cada celda en una sola región. Coinciden con las seis de `docs/MISSION_ZONES.md` (A-F, D = mares de las dos caras), que se escribió después de este documento: no hace falta recalcular.

**Rover y Paneles: todo confirmado.** Por región, emparejados, similitud mediana / p90 / máx, gemelos distintos, mayor cuota, Spearman, diferencias reales (mediana / p90) y top 3 coinciden con las tablas 3.1 y 4.1 (diferencias solo de redondeo en la última cifra). Luna entera: región del mejor gemelo Rover 6.186 / 2.379 / 1.681 / 79 / 12 (91 en la zona, 0,9 %), 10.191 con par dentro y fuera, mejor fuera +6,51 de mediana (p90 18,63), fuera mejor en el 99,1 %, 145 solo fuera (pendiente mediana 0,56° y rugosidad 18,6 m frente a 1,57° y 63,6 m de todos); Paneles 9.987 / 4.831 / 3.610 / 348 (3.958 en la zona, 21,1 %), mejor de toda la Luna menos zona 0,0 (p90 11,54), fuera mejor en el 37,8 %, 12.416 solo fuera, único sin par E19334. Comparaciones por pares de regiones frente a la zona (87,3 % y +4,29 en el polo norte, etc.): confirmadas.

**Imposibilidad: confirmada.** 15 celdas con `illum_frac` = 0, todas en el resto del polo sur. Candidato solar con menos sol sobre la atmósfera 4,137 (máx 9,974); celdas por debajo de 3,537: 16.496 = 280 + 5.120 + 5.400 polares + 2.763 + 2.933 de tierras altas en 65,5-74,5° (5.696 de 7.200); máximo polar 2,475 (sur) y 2,451 (norte); nueve regiones mediana 0,40, máximo 1,03. Rover: alcance 13,72° + 2 y 478 m + 30; 158 celdas fuera de alcance y 142 con pendiente > 15°.

**Avisos: confirmados, y no falta ninguno en Rover ni en Paneles.** Buscando regiones con más candidatos emparejados y diferencias reales iguales o menores que la zona: Rover, tierras altas visibles (10.287) y ocultas (10.336), las dos ya avisadas; el polo norte empareja menos (9.888) pero con diferencias menores, también avisado. Paneles: las dos tierras altas (18.776), avisadas. Base lunar: con la regla del paquete todas las regiones emparejan a los 2.419 (sin filtro); con D4b emparejan más todas las demás (aviso 4), por terreno y no por lo térmico.

**Base lunar.** El método usado es el declarado (regla del paquete: z por cuerpo con mediana e IQR/1,349, recorte ±4, 4 decimales, población de la Tierra `elevation_m > 0`, Luna entera, elevación / `slope_iso_deg` / rugosidad / temperatura con 20 / 33,3 / 26,7 / 20 %, `100 exp(−0,45 d)`): reproduce el paquete publicado en las nueve regiones (2.419 de 2.419 gemelos iguales, diferencia máxima de similitud < 1e-13). Cifras de las tablas 5.1-5.3 confirmadas (similitud por región, gemelos, cuotas, diferencias reales, 0 pares reales en todas las regiones también al doble, huecos mínimos 51,9 / 43,7 K, mejor gemelo en la Luna entera 1.301 / 889 / 99 / 83 / 47, +30,7 de mediana, 95,9 %). `LUNAR_BASE_PROPOSAL.md` apareció después: su diseño D4b se ha reproducido y aplicado por región (aviso 4). **La parte de Base lunar sigue siendo provisional hasta que Facundo confirme el método.**

**Frases para la web.** Todas tienen 40 palabras o menos y sus cifras se han comprobado contra los datos (rangos de elevación relativa de los mares −952 a −4.583 / −5.076 m; irradiancia de los mares 9,05-10,40; pendiente mediana 1,1° / 3,9° / 6,0°; celda más cálida 167,5 / 172,2 / 164,8 K; amplitud 261,9-311,8, 278,0-305,1, 186,0-302,7, 176,4-304,6 K; amplitud máxima de los candidatos 35,7 K).

**Errores corregidos en este documento:**

1. Aviso 3 y sección 5.2: los 126 candidatos del resto del polo sur que coinciden en amplitud lo hacen con 20 celdas a 41-45 K, de las que 15 nunca se iluminan y 5 se iluminan como mucho el 0,33 % del tiempo; no "todas en sombra permanente a 41-43 K".
2. Imposibilidad del Rover: el desglose de las 158 celdas fuera de alcance omitía 13 de las tierras altas ocultas y 4 de las visibles.
3. Frases de Base lunar para mares y tierras altas: comparaban su amplitud solo con la de la Tierra (36 K), lo que sugería que la amplitud las descarta frente a las nueve regiones; las nueve regiones también oscilan 88-234 K y tampoco tienen ningún par real. Se añade esa cifra y "no lunar region matches Earth".

**Añadido:** filas de la región D completa (Rover y Base lunar), equivalencia con `MISSION_ZONES.md`, aviso 4 (Base lunar con D4b) y la nota de la sección 6 sobre medianas sin ponderar frente a las ponderadas por área de `MISSION_ZONES.md`, que en los polos no coinciden (irradiancia de las nueve regiones 0,40 frente a 0,53): la web debe usar una sola.

**No comprobado:** los nombres de cráteres junto a cada celda (vienen del redactor) y las citas de fuentes (Mazarico et al. 2011, Artemis IV, comunicado 24-136), que se toman de `R2_lunar_reference_sources.md` y `SIMILARITY_PROPOSAL.md` sin volver a abrirlas. El motivo de elegir los mares para Paneles (llanura) sigue pendiente de Facundo.

No se ha tocado motor, configuración, datos ni web; ninguna zona cambia sin confirmación de Facundo. Sin commit.
