# Investigación 1: Rover, ¿existe una variable de terreno independiente?

Fecha: 15-11-2026, 11:35-12:10 CET. Solo investigación y medida: no he cambiado nada en el motor, la configuración, las tablas, el bundle, la web ni los audios.
Scripts (deterministas, se pueden volver a ejecutar): `tierra luna/research/r1_dem_candidates.py` (earth | moon), `r1_measure.py`, `r1_write_supplement.py` y `r1_lola_fractal.py`. Salidas: `tierra luna/research/out/r1_measure.json`, `r1_dem_{earth,moon}.npz` y `r1_dem_earth.log`.

## 1. Hallazgo

**A 1 grado no existe ninguna variable de terreno que cumpla las cuatro condiciones a la vez:** tener sentido físico para la movilidad, estar medida en las dos superficies, definirse igual en ambas y no estar correlacionada con la pendiente y la rugosidad. La abundancia de rocas de Diviner tiene 0 valores en las 5.400 celdas de la zona del Rover. En la Tierra no hay ningún producto global *medido* que represente la misma magnitud física. Las dos variables que sí salen estadísticamente independientes de los DEM (el cociente p90/media de la pendiente y el exponente de Hurst) no aportan información física nueva, y su efecto se limita a reordenar empates dentro de un top saturado.
**Recomendación: no añadir ninguna variable a la similitud ni a la idoneidad del Rover.** Además, conviene declarar que la pendiente y la rugosidad miden prácticamente una sola magnitud: el relieve a escala kilométrica.

## 2. Medida del problema (paso 1)

Antes de medir comprobé que la biblioteca de los auditores (`audit/p5_common.py`) sigue reproduciendo el modelo. Con la regla de 42d8bba (pendiente 0,4, rugosidad 0,4 y elevación relativa 0,2) da 10.337 puntos que pasan, 10.192 emparejados, 401 gemelos y el mismo top 5 que `audit/out/w0_reproduce.json`. El árbol de trabajo ya contiene la regla decidida (0,5/0,5, sin elevación relativa). Es la opción A de la sección 4.

Correlación de Spearman (Pearson entre paréntesis) con la pendiente (`slope_iso_deg`) y con la rugosidad (`roughness_m`):

| variable | Tierra, tierra firme (24.783) | zona lunar ≤ 75 S (5.400) | puntos Rover rankeados (10.337) |
|---|---|---|---|
| rugosidad frente a pendiente | **0,989 (0,986)** | **0,943 (0,916)** | **0,981 (0,988)** |
| utilidades de idoneidad pendiente/rugosidad | | | 0,973 (0,986) |
| slope_iso_p90 frente a pendiente / rugosidad | 0,993 / 0,990 | 0,900 / 0,950 | 0,981 / 0,987 |
| slope_p90 (literal) | 0,974 / 0,971 | 0,850 / 0,936 | 0,979 / 0,985 |
| rugosidad con desfase de 2 píxeles (≈ 3,7-3,8 km) | 0,992 / 0,997 | 0,921 / 0,980 | 0,982 / 0,995 |
| fracción de la celda con más de 15° (a la base del modelo) | 0,498 / 0,508 | 0,797 / 0,849 | 0,648 / 0,677 |
| fracción de la celda con más de 10° | 0,674 / 0,690 | 0,934 / 0,920 | 0,812 / 0,853 |
| fracción de la celda con más de 5° | 0,830 / 0,846 | 0,933 / 0,828 | 0,931 / 0,964 |
| **cociente p90/media de la pendiente** | **0,189 / 0,254** | **−0,318 / −0,113** | **0,003 / 0,108** |
| **exponente de Hurst entre 1,9 y 3,8 km** | **−0,328 / −0,400** | **0,159 / 0,187** | **−0,134 / −0,193** |

Diferencias por par, con la regla decidida y 10.337 pares: Spearman entre Δpendiente y Δrugosidad = 0,046. Los dos criterios están muy correlados *entre celdas*, pero su error de emparejamiento no lo está, porque el buscador de gemelos ajusta ambos a la vez.

Criterio de independencia que he aplicado: |Spearman| < 0,5 con las dos variables en las tres poblaciones. Por encima de 0,5, más del 25 % de la ordenación de la variable ya lo explica la otra (ρ² > 0,25), y un tercer criterio con ese solapamiento aumenta el peso efectivo del relieve en lugar de añadir información. Solo cumplen el criterio el cociente p90/media y el exponente de Hurst. Las fracciones de celda empinada no lo cumplen: llegan a 0,93 en la zona lunar.

## 3. Abundancia de rocas y otros productos (paso 2)

### Luna

| producto | qué mide | cobertura | ¿útil en la zona ≤ 75 S? |
|---|---|---|---|
| Diviner rock abundance DGDR_RA_AVG_CYL_032 V4.0, LRO-L-DLRE-5-GDR-V1.0, 32 px/°, datos del 05-07-2009 al 30-11-2010 (Bandfield et al. 2011, JGR 116, E00H02). URL: https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_gdr_l3/cylindrical/img/dgdr_ra_avg_cyl_032_img.img. Licencia: datos públicos del PDS de la NASA, sin restricciones (no hay cadena de licencia) | fracción de la superficie cubierta por fragmentos de roca de tamaño métrico, deducida del enfriamiento nocturno | La etiqueta lo dice textualmente: "latitudes between 60N and 60S"; MINIMUM_LATITUDE = −60. En nuestra tabla hay valor entre −59,5 y 59,5 | **No: 0 de 5.400 celdas (0 %)** |
| Diviner Polar Resource Product (PRP) (página de ayuda de ODE: https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/DIVINER/PRP.htm) | estabilidad de volátiles a partir de ajustes de un modelo térmico | polos | No: no mide rocas |
| LROC NAC: abundancia de bloques en el polo sur (estudio de 2022 en Planetary Science Journal, ficha: https://openpolar.no/Record/ftunivbern:oai:boris.unibe.ch:179288/Description) | recuento de bloques en imágenes NAC | zonas concretas alrededor de Shackleton | **No establecido** que exista un fichero abierto con una malla que cubra las 5.400 celdas. No lo he localizado en el PDS |
| Mini-RF CPR, mosaicos polares MOSCDR (ODE: https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/Mini-RF/MOSCDR.htm) | cociente de polarización circular (rugosidad a la escala de la longitud de onda y rocas a escala de decímetros, mezcladas con posible hielo) | solo por encima de 80° (cuatro mosaicos por polo); datos anteriores al 26-12-2010 | Parcial: no cubre 75-80 S. No hay equivalente terrestre homogéneo. No descargado |
| LOLA EXTRAS/FRACTAL (Rosenburg et al. 2011, JGR 116, E2): MAS_57M_16 (pendiente mediana absoluta a lo largo de la traza con base de 57 m, 16 px/°, V1.0) y HE_8 (exponente de Hurst entre 57 m y 2,7 km, 8 px/°). https://imbrium.mit.edu/EXTRAS/FRACTAL/IMG/ (catálogo: https://pgda.gsfc.nasa.gov/products/70). Licencia: no se indica; el equipo pide citar a Rosenburg et al. (2011) y avisa de que el producto "unsupported by the LOLA Science Team" | rugosidad a escala de decenas a cientos de metros | global, de −90 a 90. **Descargado hoy** (MAS_57M_16 de 33 MB, sha256 1fa4ccfb…; HE_8 de 8 MB, sha256 b924a0bf…) | Sí cubre las 5.400 celdas, pero ρ = 0,818 con la pendiente y 0,829 con la rugosidad (MAS 57 m); ρ = 0,689 y 0,730 (Hurst). Correlado y sin equivalente terrestre |

### Tierra: ¿hay un equivalente medido a la abundancia de rocas de Diviner?

**No.** La abundancia de Diviner es la fracción de superficie cubierta por bloques de 1 m o más, obtenida por inversión térmica de medidas. Ningún producto terrestre global mide esa magnitud:
- **Fragmentos gruesos del suelo (ISRIC SoilGrids, `cfvo`):** fracción volumétrica de fragmentos de más de 2 mm *dentro* del perfil del suelo. Cambian tanto el tamaño (2 mm frente a 1 m) como la magnitud (volumen en profundidad frente a superficie cubierta). Es un producto MODELLED (predicción por aprendizaje automático a partir de perfiles). No es equivalente.
- **Clases de suelo desnudo o roca de la cobertura del suelo (ESA CCI LC, ESA WorldCover "bare/sparse vegetation"):** indican ausencia de vegetación, no rocas. Es la comparación que el equipo ya descartó anoche (`bare_frac` frente a la abundancia de rocas), así que no la propongo.
- **Retrodispersión radar (mosaicos de Copernicus Sentinel-1, banda C de 5,6 cm):** responde a la rugosidad centimétrica y a la humedad, no a la fracción de bloques métricos, y no es la misma longitud de onda ni geometría que el Mini-RF (banda S). No es equivalente.

No he descargado ninguno de estos tres productos porque ninguno es la misma magnitud física. Las afirmaciones sobre lo que mide cada uno proceden de su propia definición. Sus URL y versiones exactas **no están establecidas** en este informe por falta de tiempo.

## 4. Candidatas calculadas igual en los dos cuerpos (paso 3)

Se calculan desde ETOPO 2022 v1 60s y LOLA LDEM_16 V3.1 (los mismos ficheros y el mismo código de pendiente isotrópica y rugosidad que los constructores). Comprobación de alineación y orientación: el recálculo de `slope_iso_deg` y `roughness_m` coincide con la tabla en todas las celdas hasta el redondeo (diferencia máxima de 0,0005° y 0,005 m en ambos cuerpos).

| candidata | Tierra, tierra firme p5 / p50 / p95 | zona p5 / p50 / p95 | ¿se solapan? (p5-p95) | significado para un rover |
|---|---|---|---|---|
| steep_frac_gt15deg | 0 / 0 / 0,007 (89 % de ceros) | 0 / 0,008 / 0,38 (48 % de ceros) | casi no: 0-0,007 | parte de la celda por encima del límite VIPER, pero con pendiente medida sobre 3,7 km, no a la escala del rover |
| slope_p90_over_mean | 1,51 / 1,89 / 2,57 | 1,37 / 1,77 / 2,73 | sí (1,51-2,57) | indica si la pendiente está concentrada en pocas paredes que se pueden rodear (cociente alto) o repartida por toda la celda (bajo) |
| hurst_h_1to2lag | 0,42 / 0,66 / 0,93 | 0,60 / 0,88 / 1,07 | sí (0,60-0,93) | cómo crece la rugosidad con la distancia: H ≈ 1 significa terreno localmente plano a 2 km |

Por qué no las propongo:
- **Fracciones de celda empinada:** correladas (ρ de 0,65 a 0,93 entre los puntos rankeados y en la zona) y casi sin solape de valores.
- **p90/media:** es independiente, pero es una estadística de *la misma* imagen de pendientes. Mide la forma de la distribución, no una propiedad nueva del suelo. Ninguna fuente que haya encontrado la relaciona con la traficabilidad de un rover con umbrales, así que cualquier tolerancia sería ilustrativa.
- **Hurst entre 1 y 2 píxeles:** es independiente, pero con desfases de 1 y 2 píxeles queda dominado por el suavizado propio de cada DEM. LDEM_16 está interpolado en parte (GMT surface, según su procedencia) y ETOPO 60s combina fuentes de distinta resolución nativa. La mediana en la zona (0,88) frente a la de la Tierra (0,66) puede reflejar la resolución efectiva del producto y no el terreno. **No está establecido** que mida terreno.

### Opciones medidas en memoria (regla decidida: pendiente 0,5 + rugosidad 0,5; tercera variable como secundaria, límite 2 × tolerancia)

| opción | pasan | emparejados | gemelos distintos | top 50 en común con A |
|---|---|---|---|---|
| 42d8bba (enviada) | 10.337 | 10.192 | 401 | 1 con A |
| **A decidida** | 10.337 | 10.337 | 1.166 | n/a |
| B1: p90/media, peso 0,2, tolerancia 0,2 | 10.337 | 10.332 | 992 | 8 |
| B2: p90/media, peso 0,333, tolerancia 0,2 | 10.337 | 10.332 | 1.038 | 8 |
| B3: Hurst, peso 0,2, tolerancia 0,1 | 10.337 | 10.336 | 644 | 10 |

Las tolerancias son ilustrativas: unas 0,5 veces el rango intercuartílico de los puntos rankeados (p90/media: 1,82-2,20; Hurst: 0,55-0,70).

Top 5 con separación de 2° (id de la Tierra, lat, lon → id de la Luna, lat, lon; similitud, idoneidad, final). Los nombres de lugar **no están establecidos** aquí (no los he cruzado con el nomenclátor):
- **A:** E3872 (79,5; 92,5) → M61299 (−80,5; −80,5) 100/100/100; E4037 (78,5; −102,5) → M63714 (−86,5; 174,5) 100/100/100; E4742 (76,5; −117,5) → M63712 100/100/100; E5111 (75,5; −108,5) → M63714 100/100/100; E5318 (75,5; 98,5) → M59713 (−75,5; 133,5) 99,99/100/100.
- **B1:** E5111, E24340 (22,5; 40,5), E5309 (75,5; 89,5), E17204 (42,5; 104,5), E22128 (28,5; −11,5): todos con final entre 99,99 y 100.
- **B3:** E5125, E6212, E6381, E6548, E22489: todos con final de 99,99.

**Saturación (es la verdadera debilidad que esto deja ver):** con la regla A hay 10.258 de 10.337 puntos con similitud ≥ 99,5, 311 con final ≥ 99,9 y 74 con final exactamente 100,0. El top 5 lo decide el desempate (id más bajo) entre 74 puntos empatados. Una tercera variable solo reordena esos empates (en el top 50 coinciden 8-10 de 50) y no separa mejor.

Puesto de los análogos de movilidad de `rover_preset.py` (celda que contiene las coordenadas de `data/benchmark/analog_benchmark.csv`; puesto sobre 10.337):

| análogo | A | B1 | B3 |
|---|---|---|---|
| Ramon | 369 (3,6 %) | 332 | 242 |
| Erfoud | 387 (3,7 %) | 326 | 475 |
| Qaidam | 417 (4,0 %) | 470 | 425 |
| Haughton | 433 (4,2 %) | 417 | 495 |
| Yungay | 838 (8,1 %) | 800 | 816 |
| MDRS | 2.119 (20,5 %) | 2.086 | 2.108 |
| Bardenas | 7.055 (68,2 %) | 6.796 | 7.051 |
| Dumont Dunes | 7.128 (69,0 %) | 6.816 | 6.875 |
| Tabernas | 7.372 (71,3 %) | 7.231 | 7.235 |
| Death Valley | 8.274 (80,0 %) | 8.166 | 8.073 |
| Dhofar | no pasa el embudo | no pasa | no pasa |

Ninguna opción mueve los análogos de forma apreciable: los cambios son de unos pocos puntos porcentuales y van en ambos sentidos.

## 5. Recomendación (configuración exacta)

1. **Similitud del Rover: sin cambios** respecto a la regla decidida (slope_deg clave, peso 0,5, tolerancia 2,0°; roughness_m clave, peso 0,5, tolerancia 30 m). Lo justifican: la abundancia de rocas tiene cobertura del 0 % en la zona; no hay equivalente terrestre medido; las candidatas independientes no aportan información física nueva o miden la resolución del producto; y el efecto sobre los análogos es nulo (sección 4).
2. **Idoneidad: sin cambio de pesos.** Propuesta de texto, no de cifras: declarar en la ficha de la misión que slope_300m_deg (0,45) y rough_300m_m (0,30) son en la práctica un solo criterio de relieve kilométrico (ρ = 0,973 entre utilidades), de modo que el relieve pesa en efecto 0,75 y `rock_or_bare_frac` 0,25. Fusionarlas en un solo criterio supondría un override de mission_scoring.json; no lo he medido y lo dejo al responsable del equipo.
3. **Información (opcional, sin peso):** `lola_mas57_deg` (pendiente a 57 m de LOLA, Rosenburg et al. 2011) como columna informativa *solo lunar* por celda de la zona. Es la única medida de terreno a escala próxima a la del rover que cubre el polo sur. No sirve para emparejar porque no tiene equivalente terrestre.

## 6. Ficheros preparados

- `tierra luna/real_data/supplement/r1_terrain_earth.csv` y `r1_terrain_moon.csv`: una fila por celda (64.800, clave `cell_id`). Columnas: `slope_p90_over_mean`, `steep_frac_gt15deg`, `steep_frac_gt10deg`, `roughness_2lag_m`, `hurst_h_1to2lag`. Cobertura: en la Tierra, 24.783 celdas de tierra firme (24.781 en las dos últimas columnas); en la Luna, 64.800.
- `tierra luna/real_data/supplement/r1_terrain_provenance.csv`: nivel DERIVED, producto, versión, URL, licencia, agregación, fórmula y advertencias, en el formato de `provenance_earth.csv`.
- `tierra luna/real_data/supplement/r1_lola_fractal_moon.csv`: `lola_mas57_deg` y `lola_hurst` por celda lunar, con 64.800 celdas (cobertura completa del fichero). Es un dato MEASURED reducido como DERIVED: media ponderada por cos(lat) de los píxeles de 1/16° o 1/8°. Ojo: **no he añadido sus filas a r1_terrain_provenance.csv por falta de tiempo**. Los datos son los de la tabla de la sección 3 (producto LOLA EXTRAS/FRACTAL V1.0, URL https://imbrium.mit.edu/EXTRAS/FRACTAL/IMG/, consultado el 15-11-2026, datos hasta LRO_NO_13).

## 7. Qué necesitaría al responsable del equipo

- **Abundancia de rocas en el Rover:** solo sería posible cambiando de zona (lat ≤ −60 en lugar de ≤ −75, donde Diviner tiene datos). Eso cambia una zona fija. Opciones: (a) mantener la zona sin rocas (lo que recomiendo); (b) dar la abundancia de rocas como información en las celdas lunares por debajo de 60 S, sin que entre en el emparejamiento. Sigue sin haber dato terrestre para compararla.
- **Saturación del top:** 74 empates a 100 hacen que "best" no se pueda defender. Que la web y los audios digan "highest-scoring" no depende de esta investigación, pero queda respaldado por estas cifras.

## 8. No establecido

- Que exista un fichero abierto de bloques LROC NAC que cubra toda la zona ≤ 75 S.
- Las URL y versiones exactas de SoilGrids cfvo, ESA WorldCover y los mosaicos de Sentinel-1 (no los descargué porque no son la misma magnitud).
- Que el exponente de Hurst entre 1 y 2 píxeles mida terreno y no la resolución efectiva del DEM.
- El valor de "sin dato" de MAS_57M_16/HE_8: no lo he leído en la etiqueta. Todas las celdas de la zona tienen valor, con rangos verosímiles.
- Los nombres de lugar de los top 5.
