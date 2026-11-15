# Investigación 2 — Placas solares: una idoneidad que no dependa de la latitud

Fecha: 2026-11-15, 11:35–12:00 CET. Papel: investigación y medición; no se ha tocado motor, configuración, tablas, bundle, web ni audio.
Scripts: `tierra luna/research/r2_build_cloud.py` (tabla suplementaria) y `tierra luna/research/r2_solar_options.py` (opciones en memoria con `audit/p5_common.py`). Salidas: `tierra luna/research/out/r2_solar_options.json`, `r2_spearman_matrix.csv`.
Reproducción: `p5_common` con la configuración actual reproduce el bundle de Placas solares (18.777 filas, `final` idéntico, diferencia máxima 0,00; gemelos idénticos al 100 %). La configuración de Solar no ha cambiado desde 42d8bba (solo textos).

## 1. Hallazgo (dos líneas)
Hoy el 65 % del peso de la idoneidad son criterios ligados a la latitud (ρ con |lat|: sun_elev_max −0,995; sun_low_frac +0,878; irradiancia WorldClim −0,673) y explican el 95 % de su dispersión; la similitud ya compara la luz sobre la atmósfera (pura latitud), así que hay doble conteo.
Sustituir esos tres criterios por la fracción despejada de nubes ISCCP‑H (dato satelital oficial, NOAA NCEI) deja 0 % de peso ligado a la latitud, ρ(idoneidad,|lat|) = +0,34 (de origen climático, no geométrico), y no cambia emparejados ni gemelos.

## 2. Descomposición de la idoneidad actual (paso 1)
Puntos que pasan el embudo: 18.777; emparejados: 6.360; gemelos distintos: 1.704.

| criterio | peso | malo | bueno | ρ con \|lat\| | parte de la dispersión | top 50 que se conserva al quitarlo |
|---|---|---|---|---|---|---|
| irradiance_kwh_m2_day (WorldClim, MODELLED) | 0,35 | 2,5 | 6,0 | −0,673 | 0,554 | 0 / 50 |
| sun_elev_max_deg | 0,15 | 10 | 70 | −0,995 | 0,218 | 49 / 50 |
| sun_low_frac_0_5deg | 0,15 | 0,25 | 0,03 | +0,878 | 0,180 | 46 / 50 |
| slope_deg | 0,15 | 12 | 1 | −0,289 | 0,011 | 50 / 50 |
| lst_diurnal_amp_k | 0,10 | 35 | 10 | −0,291 | 0,129 | 19 / 50 |
| roughness_m | 0,10 | 400 | 30 | −0,351 | 0,007 | 47 / 50 |

ρ(idoneidad, |lat|) entre los que pasan = −0,857; entre los emparejados = +0,092 (la tolerancia de la similitud ya restringe a |lat| ≲ 40°, por eso dentro de los emparejados la latitud decide poco y lo que decide es la irradiancia WorldClim). Correlaciones entre criterios (Spearman, pasan el embudo; matriz completa en `r2_spearman_matrix.csv`): sun_elev_max–sun_low_frac −0,87; irradiancia–sun_elev_max 0,69; irradiancia–sun_low_frac −0,76; irradiancia–amplitud térmica 0,71; pendiente–rugosidad 0,99 (doble conteo de terreno también, 25 % del peso, pero aporta solo 2 % de la dispersión). Coincide con las cifras de los auditores (p5_physical.json: 0,69 irradiancia–latitud).

## 3. Datos nuevos (paso 2)

**(b) Nubosidad: conseguido.** ISCCP H‑series Basic HGM (NOAA NCEI CDR), versión v01r00, variable `cldamt` "Mean cloud amount" (%), mensual, rejilla 1° equiángulo idéntica a la nuestra. URL: https://www.ncei.noaa.gov/data/international-satellite-cloud-climate-project-isccp-h-series-data/access/isccp-basic/hgm/ ; 60 ficheros (2012‑01 a 2016‑12, ~4,2 MB cada uno, 248 MB en total, en scratchpad/research-raw/isccp_hgm, fuera del repositorio). Licencia (atributo del fichero): "No constraints on data access or use"; citar Rossow y Schiffer (1999), BAMS 80:2261. Accedido 2026‑11‑15.
Reducción: la celda nativa es nuestra celda (sin ponderación por área necesaria); filas invertidas a norte‑primero, longitudes rotadas 180; media de las medias mensuales con ≥ 48 de 60 meses válidos; `cldamt` es día+noche (IR), así que la noche polar no requiere tratamiento. Cobertura: 64.778 de 64.800 celdas; 3 de los 18.777 puntos que pasan sin valor (el motor renormaliza los pesos, como hoy con cualquier dato ausente).
Orientación comprobada: Libia 24,5N 25,5E nubosidad 0,28; Atacama 23,5S 69,5W 0,20; Rub al Jali 19,5N 50,5E 0,22 (despejados); ZCIT Pacífico 6,5N 139,5W 0,76; Océano Austral 58,5S 0,5E 0,86; Congo 0,5S 20,5E 0,71; Amazonía 3,5S 59,5W 0,68 (nubosos). Correcto.

**(a) Irradiancia superficial satelital: NO conseguida hoy.** NASA Earth Observations (neo.gsfc.nasa.gov/archive/csv/…) redirige (301) a science.nasa.gov: la ruta de ficheros planos ya no sirve. CERES EBAF/SYN1deg en ASDC (asdc.larc.nasa.gov/data/CERES/…) y su OPeNDAP redirigen a Earthdata (requiere cuenta); la herramienta de pedidos CERES no es un fichero abierto. NASA POWER solo está autorizado como comprobación. Por tanto la opción D (irradiancia satelital en vez de WorldClim) y la comparación satélite–WorldClim quedan **no establecidas**. Sustituto medido: ρ(fracción despejada ISCCP, irradiancia WorldClim) = 0,42 en 25.462 celdas de tierra.

**Índice de claridad con WorldClim (Kt = irradiancia WorldClim / irradiancia sobre la atmósfera):** se calculó y se **rechaza**: ρ con |lat| = +0,65 (no elimina la latitud) y valores físicamente implausibles a latitudes altas (mediana 0,83 y P95 0,91 por encima de 75°, cuando un cielo despejado da ~0,7–0,8), señal de un artefacto de la interpolación WorldClim. ρ(Kt WorldClim, fracción despejada) = 0,79: si se usara, serían la misma información y no deben ir juntos.

## 4. Opciones medidas (paso 3)
En todas: pasan 18.777, emparejados 6.360, gemelos distintos 1.704 — **sin cambio por construcción** (la idoneidad no interviene en el embudo ni en la búsqueda del gemelo; los filtros duros no se tocan). Top 5 con separación ≥ 2° (gran círculo). "Peso ligado a latitud" = peso de criterios con |ρ| ≥ 0,5 con |lat|. Artefactos en el top 50: ninguna celda con hielo/nieve (snow_ice_frac > 0, CCI 220) en ninguna opción; "agua" = celdas con cobertura dominante CCI 210; "costa" = mask_fraction < 0,999 (ninguna < 0,5).

| opción | ρ idon.–\|lat\| (pasan / emparejados) | peso ligado a latitud | solape top 50 con hoy | top 100 en trópicos | top 50: agua / costa |
|---|---|---|---|---|---|
| A hoy | −0,857 / +0,092 | 0,65 | 50 | 1,00 | 4 / 22 |
| B quitar sun_elev_max y sun_low_frac | −0,688 / +0,126 | 0,50 | 46 | 0,99 | 4 / 22 |
| C1 B + despejado ISCCP 0,30 | −0,165 / +0,343 | 0,35 | 9 | 0,78 | 2 / 8 |
| C2 B + Kt WorldClim 0,30 (rechazada) | +0,089 / +0,305 | 0,65 | 1 | 0,51 | 0 / 5 |
| D irradiancia satelital | no establecida (sin dato abierto hoy) | | | | |
| E despejado ISCCP 0,65 sustituye irradiancia y geometría | +0,325 / +0,415 | 0,00 | 6 | 0,65 | 2 / 15 |
| **E2 despejado ISCCP 0,35 en el hueco de la irradiancia; geometría fuera** | +0,337 / +0,382 | 0,00 | 7 | 0,63 | 3 / 21 |
| E2 con malo/bueno P5/P95 (0,278/0,698) | +0,333 / +0,378 | 0,00 | 2 | 0,64 | 3 / 14 |

Parte de la dispersión en E2: despejado 0,895; amplitud térmica −0,206 (va en contra: cielo despejado ⇒ más amplitud, ρ 0,67, y la amplitud alta está penalizada); pendiente 0,063; rugosidad 0,049.

Top 5 (id Tierra, lat, lon, lugar aproximado por coordenadas, gemelo id lat/lon, similitud, idoneidad, final):
- **A hoy:** E38464 −16,5 124,5 (Kimberley, Australia) → M24296 22,5/−3,5, 99,99, 96,90, 98,45 · E38744 −17,5 44,5 (Madagascar oeste) → M40854 −23,5/−5,5, 99,95, 96,77, 98,36 · E37746 −14,5 126,5 (Kimberley) → M24761, 99,98, 96,62, 98,30 · E37750 −14,5 130,5 (Territorio del Norte) → M24688, 99,98, 96,40, 98,19 · E29749 7,5 49,5 (Somalia) → M26063 17,5/−36,5, 99,97, 96,35, 98,16.
- **B:** E38464 (99,28) · E38744 (99,18) · E37746 (99,04) · E38109 −15,5 129,5 (99,89 sim., 97,88, 98,89) · E38027 −15,5 47,5 (98,80).
- **C1:** E29749 7,5 49,5 Somalia → M26063, 99,97, 98,29, 99,13 · E29746 7,5 46,5 Somalia/Etiopía → M26056, 99,97, 97,96, 98,96 · E28670 10,5 50,5 Somalia (cuerno) → M25483, 99,94, 97,76, 98,85 · E23972 23,5 32,5 Egipto (Asuán) → M22476, 100,00, 97,32, 98,66 · E25758 18,5 18,5 Chad (Sáhara) → M23951, 99,91, 97,40, 98,65.
- **E2 (recomendada):** E40184 −21,5 44,5 Madagascar suroeste → M23206 25,5/−13,5, 99,83, 97,94, 98,88 · E29749 7,5 49,5 Somalia → M26063, 99,97, 97,56, 98,76 · E23648 24,5 68,5 Pakistán (Sind) → M22156 28,5/16,5, 99,93, 97,20, 98,56 · E29746 7,5 46,5 → M26056, 99,97, 97,08, 98,52 · E28670 10,5 50,5 → M25483, 99,94, 96,81, 98,37.
- **E2 P5/P95:** E29749 · E40543 −22,5 43,5 · E28670 · E25758 · E34142 −4,5 122,5 (Sulawesi; señal de que P5/P95 es menos estable: mismo diseño, solape top 50 entre variantes bajo).

Los nombres de lugar son orientativos (región por coordenadas), no un geocodificado verificado.

**Sitios de investigación solar reconocidos:** no establecido. No pude obtener hoy coordenadas de una página oficial (psa.es devolvió 503; midcdmz.nrel.gov no es accesible desde esta sesión). No se dan coordenadas de memoria; otro investigador compila la lista. El script admite la comprobación en cuanto se añadan coordenadas con fuente (bloque `sites`).

## 5. Recomendación (paso 4): opción E2, como sobrescritura en la configuración del motor
Razón: elimina el doble conteo (la luz sobre la atmósfera, función de la latitud, ya está en la similitud; la irradiancia en el suelo = luz sobre la atmósfera × transparencia, así que lo que el sitio añade es la transparencia), deja 0 % del peso en criterios ligados a la latitud, sustituye un dato MODELLED (WorldClim) por uno satelital DERIVED, y no toca zona, principio, embudo ni gemelos. Peso de despejado = 0,35, el hueco que deja la irradiancia (decisión de diseño; con 0,65 —opción E— el top 50 apenas cambia frente a E2 pero un solo criterio llevaría el 96 % de la dispersión).

Cambios exactos (override en `engine/engine_config.json`; `mission_scoring.json` no se edita):
1. `solar.soft.sun_elev_max_deg.weight` 0,15 → 0 (quitar). Razón: ρ −0,995 con |lat|, geometría pura ya contenida en la similitud. Fuente: este informe §2; auditoría 5 §D.
2. `solar.soft.sun_low_frac_0_5deg.weight` 0,15 → 0 (quitar). Razón: ρ +0,878, misma información que el anterior (ρ −0,87). Fuente: ídem.
3. `solar.soft.irradiance_kwh_m2_day.weight` 0,35 → 0 (quitar del soft; **el filtro duro ≥ 2,5 kWh/m²/día se mantiene**). Razón: doble conteo con la similitud y dato MODELLED; ρ −0,673.
4. Nuevo `solar.soft.clear_frac_isccp`: weight 0,35, bad 0,308, good 0,671 (percentiles 10 y 90 de los 18.777 puntos que pasan; **valores de diseño del equipo** derivados de la distribución, no de la literatura), "why": "fracción del tiempo sin nubes (ISCCP-H HGM v01r00, NOAA NCEI, 2012-2016): lo que la atmósfera del sitio deja pasar, independiente de la latitud". Columna de `real_data/supplement/earth_cloud_isccp_1deg.csv`, unida por `cell_id`. No añadir a `require_present` (3 puntos sin dato se renormalizan como hoy).
5. Sin cambio: pendiente 0,15 (12→1), amplitud térmica 0,10 (35→10), rugosidad 0,10 (400→30), filtros duros. Nota: pendiente y rugosidad están correladas 0,99 (doble conteo de terreno, 25 % del peso, pero solo ~11 % de la dispersión en E2); queda para el equipo si fundirlos.
Consecuencia a comunicar: el top 50 cambia casi entero (solape 7/50); la proporción del top 100 en los trópicos baja de 1,00 a 0,63. La similitud sigue saturada (99,8–100 en la cabeza), así que el orden sigue lo decide la idoneidad: hablar de "highest-scoring", no de "best".

## 6. Ficheros preparados
- `tierra luna/real_data/supplement/earth_cloud_isccp_1deg.csv`: columnas `cell_id, row, col, lat_deg, lon_deg, cloud_frac_isccp, clear_frac_isccp, n_months_isccp`; 64.800 filas (una por celda), 64.778 con valor.
- `tierra luna/real_data/supplement/provenance_earth_cloud_isccp.csv`: formato de provenance_earth.csv más `period` y `date_accessed`.
- Reconstruible con `python3 "tierra luna/research/r2_build_cloud.py" <dir_raw>` (descarga: lista de URL en research-raw/isccp_hgm/urls.txt).

## 7. Lo que necesitaría al jefe de equipo
Nada de zona ni de principio: la recomendación no los toca. Decisiones de diseño suyas: (a) peso 0,35 frente a 0,65 (E) del despejado; (b) aceptar que el top cambia (solape 7/50); (c) si se mantiene la irradiancia WorldClim como criterio blando (C1: 35 % ligado a latitud, solape 9/50) en lugar de E2 (0 %).

## 8. No establecido
- Irradiancia superficial satelital abierta sin cuenta (CERES EBAF/SYN1deg requieren Earthdata; NEO retirado): opción D y comparación satélite–WorldClim (correlación, sesgo, mayores discrepancias).
- Coordenadas oficiales de sitios solares de referencia y dónde caerían.
- Fiabilidad de ISCCP sobre desiertos brillantes y costas a 1° (no validada hoy con otra fuente).
- Kt sin artefacto (necesita la irradiancia satelital).
