# Auditoría 12: contraste con la realidad de los 15 sitios NUEVOS (punto C)

Auditor independiente, 2026-11-15. Sitios: `app/public/data/v2/missions.json` (`top5.ids`), valores de `explain.json`.
Scripts: `tierra luna/audit/c2_fetch.py` (reutiliza `p6_fetch_ext.nasadem/stations/station_stats`, la consulta GSA de
`p6_power_gsa` y la mezcla CCI / Natural Earth de `p6_pairs`) y `c2_power.py`. Salidas: `out/c2_sites.csv`,
`out/c2_stations.csv`, `out/c2_gsa.csv`, `out/c2_power.json`. Nada externo se ha copiado al modelo, al bundle ni a la web.

Fuentes alcanzadas: NASADEM HGT v001 (COG de Planetary Computer, leído a 12", celda de 1° centrada); Copernicus DEM
GLO-30 (bucket público AWS, tesela N78 W103, solo para E4037); ESA CCI LC 2020 (teselas crudas locales: MISMO origen que
el motor, no independiente); Natural Earth 110m; GHCN-Daily (NOAA NCEI, 2 estaciones ≤250 km, 1970-2000); Global
Solar Atlas (Solargis v2.2.68, GHI de largo plazo hasta 2025); NASA POWER API climatología v2.10.1, comunidad RE, en el
centro de celda (solo como control): ALLSKY_SFC_SW_DWN y CLOUD_AMT = CERES SYN1deg; T2M_MIN, T2M_RANGE = MERRA-2.
No alcanzado: una fuente independiente de hielo permanente para E4037 (RGI/GLIMS no consultado por tiempo); el origen
exacto del `irradiance_kwh_m2_day` del modelo no se verificó en esta pasada (si es CERES SYN1deg, el contraste con
POWER ALLSKY no es independiente). Pendiente: `slope_300m`/`rough_300m` del Rover son idénticos a `slope_deg`/`roughness_m`.

Pendiente y rugosidad DEM: «60"» = mismo método que la parte 6 (bloques de 60", definición de las tablas); «12"» = a
~370 m, la escala más cercana a los 300 m que anuncian las variables del Rover. Rugosidad = RMS de diferencias entre vecinos.

## Rover

| Sitio | Tierra (frac. motor / CCI agua / CCI hielo) | Pend. modelo ° | DEM 60" ° | DEM 12" ° | Rug. modelo m | DEM 60" m | Relieve m | Veredicto |
|---|---|---|---|---|---|---|---|---|
| E4037 78.5N 102.5W | 0.70 / 0.30 / 0.00 (CCI 56 % desnudo) | 0.770 | 0.908 (Cop. GLO-30) | 2.08 | 29.34 | 17.8 | 254 | pendiente concuerda (+0.14°), rugosidad −11.6 m; hielo: solo CCI (no independiente) |
| E50510 50.5S 69.5W | 0.93 / 0.07 / 0 | 0.722 | 0.755 | 1.36 | 29.16 | 25.7 | 521 | concuerda |
| E44239 32.5S 139.5E | 1.00 / 0 / 0 | 0.547 | 0.571 | 1.07 | 18.18 | 17.6 | 529 | concuerda |
| E26510 16.5N 50.5E | 1.00 / 0 / 0 (desnudo 99.95 %) | 0.643 | 0.646 | 1.64 | 21.87 | 21.6 | 746 | concuerda |
| E26087 17.5N 12.5W | 1.00 / 0 / 0 | 0.523 | 0.543 | 1.13 | 26.42 | 26.5 | 402 | concuerda |

## Paneles solares

GHI: Global Solar Atlas (independiente). Despejado: 1 − CLOUD_AMT anual de POWER (CERES/MODIS, independiente de ISCCP-H).

| Sitio | Tierra (motor / CCI agua) | Suelo modelo kWh/m²/d | GSA | dif. % | POWER ALLSKY (control) | Despejado ISCCP | POWER 1−nub. | dif. | Pend. modelo / DEM 60" ° | Veredicto |
|---|---|---|---|---|---|---|---|---|---|---|
| E40184 21.5S 44.5E | 0.99 / 0.01 | 5.745 | 6.021 | −4.6 | 6.128 | 0.675 | 0.657 | +0.018 | 0.753 / 0.771 | concuerda |
| E29749 7.5N 49.5E | 0.66 / 0.34 (costero) | 6.202 | 6.211 | −0.1 | 6.297 | 0.705 | 0.711 | −0.005 | 0.356 / 0.278 | concuerda |
| E23648 24.5N 68.5E | 0.93 / 0.07 | 5.614 | 5.534 | +1.5 | 5.553 | 0.662 | 0.714 | −0.051 | 0.016 / 0.018 | concuerda |
| E29746 7.5N 46.5E | 1.00 / 0 | 6.102 | 6.073 | +0.5 | 6.391 | 0.677 | 0.695 | −0.018 | 0.219 / 0.221 | concuerda |
| E28670 10.5N 50.5E | 0.96 / 0.04 | 6.311 | 6.398 | −1.4 | 6.496 | 0.792 | 0.713 | +0.080 | 0.860 / 0.856 | concuerda (despejado +0.08 sobre CERES) |

## Base lunar

Estaciones GHCN-Daily 1970-2000, media de la Tmin del mes más frío; «ajust.» = llevada a la cota media NASADEM de la
celda con 6.5 K/km (gradiente supuesto por el auditor). POWER = MERRA-2, mes más frío (control; MERRA-2 independiente de
la fuente de `tmin_c` solo si ésta no es MERRA-2). La oscilación del modelo es de temperatura de superficie (LST), la de
estación es del aire: magnitudes distintas, solo se comprueba el orden (LST > aire).

| Sitio | Cota DEM m | tmin modelo °C | Estaciones (cota, km): Tmin → ajust. | POWER T2M_MIN | Osc. LST modelo K / aire estación K | GHI modelo / GSA (dif.) | Pend. modelo / DEM 60" ° | Veredicto |
|---|---|---|---|---|---|---|---|---|
| E21054 31.5N 5.5W | 1734 | −1.52 | Ouarzazate 1139 m, 148 km: 2.06 → −1.8; Midelt 1508 m: 0.71 → −0.8 | −9.97 | 18.7 / 13.3-14.4 | 5.39 / 5.80 (−7.1 %) | 3.26 / 3.41 | concuerda con estaciones; POWER −8.5 K |
| E17538 41.5N 78.5E | 3502 | −24.54 | Tian-Shan 3639 m, 48 km: −29.23 → −28.3; Bachu 1117 m: −12.25 → −27.8 | −31.87 | 15.6 / 14.2-14.5 | 4.09 / 3.69 (+10.8 %) | 6.65 / 7.31 | modelo ~4 K más templado; GHI +11 % |
| E21833 29.5N 53.5E | 1823 | −1.49 | Shiraz 1481 m, 94 km: 0.16 → −2.1; Yasoge (solo 2000) | −10.53 | 20.0 / 14.6-15.7 | 5.44 / 5.99 (−9.1 %) | 3.74 / 3.61 | concuerda con estación |
| E18627 38.5N 87.5E | 1862 | −16.84 | Ruoqiang 889 m, 83 km: −12.97 → −19.3; Qiemo 1248 m: −13.89 → −17.9 | −18.30 | 22.1 / 15.7-15.9 | 4.64 / 4.13 (+12.2 %) | 3.17 / 3.42 | tmin concuerda; GHI +12 % |
| E19672 35.5N 52.5E | 1831 | −5.19 | Semnan 1117 m, 91 km: 5.52 → 0.9; Teherán-Mehrabad 1191 m: −5.30 → −9.5 | −20.52 | 19.7 / 11.0-12.3 | 4.80 / 5.39 (−10.8 %) | 4.20 / 4.42 | entre las dos estaciones (dispares); GHI −11 % |

## Veredicto: punto C sobre los 15 nuevos, **AÚN NO**

1. Rover: los 15 son tierra (centro dentro de Natural Earth en los 15) y la pendiente/rugosidad de la tabla se reproduce con un DEM independiente a 60" (±0.14°, ±4 m salvo E4037, −11.6 m). Pero `slope_300m_deg`/`rough_300m_m` valen exactamente lo mismo que `slope_deg`/`roughness_m`, y a ~370 m el DEM independiente da 1.1-2.1°, del orden de 2 veces más: la etiqueta «300 m» no corresponde a esa escala.
2. E4037 (78.5N 102.5W): es tierra (Copernicus DEM la cubre al 100 %, cota media 64 m, relieve 254 m; 30 % agua según CCI) y CCI 2020 no le da hielo, pero CCI es la misma fuente que el motor: el «libre de hielo permanente» por una fuente independiente queda **sin verificar**.
3. Paneles solares: concuerdan los 5 (GSA a ±5 %, despejado a ±0.05 de CERES salvo E28670, +0.08). Si el suelo del modelo es CERES SYN1deg, el control con POWER ALLSKY no es independiente; con GSA sí lo es.
4. Base lunar: la Tmin concuerda con las estaciones ajustadas por cota en 3 de 5; E17538 sale ~4 K más templada y E19672 tiene estaciones contradictorias. POWER/MERRA-2 es 1.5-15 K más frío en las 5 (control, no decide). La irradiancia de la base lunar se aparta del GSA entre −11 % y +12 % en 3 de 5.
5. Para pasar a GO: aclarar el nombre o la escala de las variables «300 m» del Rover y comprobar el hielo de E4037 con una fuente independiente (p. ej. RGI 7.0); el resto puede quedar como matices documentados.

## Cierre de los dos huecos

Segundo auditor independiente (2026-11-15). Script `tierra luna/audit/c3_hielo_E4037.py`, salida
`tierra luna/audit/out/c3_hielo_E4037.json`. No se tocó motor, bundle, web ni audio.

### Hueco 1: etiqueta «300 m» del Rover — **cerrado** (alias documentado; la pantalla da la base real)

- Lo que dice el proyecto: `real_data/column_aliases.json` mapea `slope_300m_deg` → `slope_deg` (en el motor, `slope_iso_deg` por `column_overrides`) con `true_baseline_km` «3.706 km N-S…» y `rough_300m_m` → `roughness_m` con «lag … 1.853 km … same definition as the Moon (1.895 km)», y advierte que no son valores a 300 m. `ASSUMPTIONS.md` (tabla de alias, l. 429-430; comparabilidad, l. 465-466: 3.706 / 3.79 km y 1.853 / 1.895 km; l. 499: «the interface never says "300 m"»). Que `slope_300m_deg` = `slope_deg` es, pues, un alias declarado, no un error; la diferencia ×2 con NASADEM a ~370 m es la esperada al cambiar de escala.
- Lo que ve el visitante: `variables.json` y `missions.json` `weighted_variables[].label` = «Slope (rover)» / «Roughness (rover)» (sin «300 m»); `true_baseline` = «3.706 km in both directions» (Tierra) / «3.79 km» (Luna) y 1.853 / 1.895 km. `app/src/flow/detailPanel.ts` imprime «True baseline: …» bajo cada valor y una sección «Slope and roughness» («computed over kilometre baselines, not rover-scale values»). Los motivos de descarte se escriben con la etiqueta (`reasonWords`, `gateWords`); el texto codificado `reason_codes[].text` («slope_300m_deg outside [0.5, 15.0]») queda solo en el atributo DOM `data-engine-reason`, no visible; `lunar_named_sites.json` `fail_text` no lo usa ninguna vista (`grep` en `app/src`). `explain.json` contiene `slope_300m_deg`/`rough_300m_m` solo como claves.
- Cadenas visibles que mencionan 300 m: todas lo hacen para decir que el valor **no** es a 300 m o que los umbrales se escribieron para 300 m (`missions.json` `missions[0].known_limitations[0]`, `not_used_by_engine.why`, `similarity.variables[].why`; `variables.json` `variables[2|3].description`, `bodies.*.caveat`, `provenance_caveat`). Ninguna cadena visible afirma ni da a entender que un valor de base kilométrica es de 300 m. **No hay cadenas que cambiar.** (Opcional, cosmético: `reason_codes[].text`/`team_text` y `fail_text` llevan el nombre interno; no se muestran.)

### Hueco 2: hielo permanente en E4037 (78-79 N, 103-102 W) — **cerrado: libre de hielo permanente según 2 fuentes independientes de CCI**

| Fuente | Producto / versión / URL | Resultado en la celda |
|---|---|---|
| (a) Natural Earth | 1:10m Physical `ne_10m_glaciated_areas`, VERSION del repositorio «5.2.0-pre», https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_glaciated_areas.geojson (1886 polígonos) | 0 % de la celda; ningún polígono a menos de 1° |
| (b) ESA WorldCover | 10 m 2021 v200 (Sentinel-1/2), tesela N78W105, https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N78W105_Map.tif, overview ×8 (~0.000667°, 1500×1500 píxeles) | clase 70 nieve/hielo **0.16 %**; 80 agua 30.5 %; 60 desnudo/escaso 54.5 %; 100 musgo/liquen 10.5 %; 90 humedal 2.5 %; 30 pastizal 1.8 % |
| (c) RGI 7.0 / GLIMS | no intentado: (a) y (b) ya concuerdan | — |

WorldCover es un producto distinto de CCI LC (sensores y método propios). Su 0.16 % de clase 70 puede ser nieve estacional del compuesto (problema conocido en latitudes altas) o manchas por debajo de la escala de Natural Earth; en todo caso es despreciable. El 30.5 % de agua concuerda con el 30 % de CCI. Límite: Natural Earth 1:10m no resuelve manchas de hielo pequeñas; el overview ×8 es una muestra del mapa de 10 m, no un recuento completo.

### Veredicto final del punto C sobre los 15 sitios: **GO con matices declarados**

Cerrados los dos huecos —las variables «300 m» son alias documentados y la pantalla muestra la base kilométrica real sin afirmar 300 m en ningún sitio, y E4037 está libre de hielo permanente según Natural Earth (0 %) y ESA WorldCover 2021 (0.16 % nieve/hielo), ambas independientes de CCI— los 15 sitios publicados concuerdan con la realidad dentro de lo comprobable. Matices que deben decirse al visitante: (1) pendiente y rugosidad son medias de celda a bases de ~3.7-3.8 km y ~1.85-1.9 km, no valores a escala de rover, y los umbrales del Rover se escribieron para 300 m (ya en pantalla); (2) en la base lunar, E17538 (41.5N 78.5E) sale ~4 K más templada que las estaciones ajustadas por cota, y E19672 tiene estaciones contradictorias; (3) la irradiancia en el suelo de los sitios de base lunar queda a ±12 % del Global Solar Atlas (−11 % a +12 %); (4) la rugosidad de E4037 es 11.6 m menor en el DEM independiente; (5) E4037 es tierra con ~30 % de agua en la celda; (6) en paneles solares, E28670 tiene una fracción despejada +0.08 sobre CERES.
