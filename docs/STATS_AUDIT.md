# Auditoría estadística del 15-11-2026: documento final

Equipo Stars Beside You, NASA Space Apps Challenge 2026 (Málaga), reto "Earth analogs for Permanent Moon Base and Mars". Ensamblado el 15-11-2026 entre las 13:15 y las 14:00 CET por un auditor independiente que no escribió el código, ni las partes anteriores de la auditoría, ni las correcciones. Rama `final-integration`, HEAD `691af33` (actualizado hacia las 14:05 CET sobre HEAD `3ed19b2` por otro agente independiente: primera página, §3, §5, §8 y la tabla de commits). Este documento no cambia nada: solo reúne, comprueba contra su fichero y resume lo que está en `docs/stats_audit/`, `docs/DECISIONS.md`, `docs/DATA_CONTRACT.md` y el paquete `app/public/data/v2`. Las horas de las decisiones son CET; las de los commits, UTC (CET − 1 h).

Commits en los que se apoya (comprobados con `git log`):

| commit | hora (UTC) | qué es |
|---|---|---|
| `42d8bba` / `a493514` | 09:37 / 09:44 | estado auditado por la mañana (motor / paquete que leyeron los seis auditores) |
| `dcca774` | 10:17 | entrega de los seis auditores (puntos 1-9 y A-F) |
| `007a244` | 10:33 | primera ronda de correcciones (`correcciones_1.md`), sin cambiar ningún criterio |
| `0bd9e85`, `de610fc` | 10:42, 10:44 | investigación de las debilidades (`research_1` a `research_5`), nada aplicado |
| `9c07ee1` | 10:52 | primer paso del motor: decisiones de las 11:23 CET (contrato revisión 7) |
| `d24ebb3` | 11:51 | segundo paso del motor: decisiones de las 11:28, 11:36 y 11:51 CET (contrato revisión 8) |
| `4c0abc3` | 12:00 | re-auditoría de Base lunar (`9_reauditoria_base.md/.json`) |
| `1209af2` | 12:03 | re-auditoría de Rover (`9_reauditoria_rover.md/.json`), primer veredicto |
| `c5f1f6c`, `691af33` | 12:08, 12:14 | pasada de textos del motor (puntos del líder de las 12:10) y vídeo de Base lunar |
| `89a5c52` (rama `audit-solar`) | — | re-auditoría de Paneles solares, **veredicto final** (`9_reauditoria_solar.md/.json`) |
| `956d55b` (rama `audit-base`), `6c3750c` (rama `audit-rover`) | — | re-auditorías finales de Base lunar (los nueve puntos GO, `9_reauditoria_base.json`) y de Rover |
| `0486ad9` | — | textos finales de las 19 pistas de audio (`app/public/audio/transcripts.json`), comprobados por un revisor independiente (`10_textos_audio.md`) |
| `cd14aea` | — | documentos de entrega, primera pasada de textos del motor, despliegue (`scripts/deploy_vercel.sh`, `app/vercel.json`) |
| `e28283a` | — | validación (fase 3, `docs/VALIDATION.md`, `tierra luna/validation/`) con su comprobación independiente (`13_comprobacion_validacion.md`); contraste externo de los 15 pares publicados (`12_contraste_realidad_nuevos.md`) |
| `4624505` | — | segunda pasada de textos del motor: Rover T1, T4, T6, T7, T8; Paneles F1, F2, F4, nota de validación dentro de la fila, estabilidad; ningún número cambia |
| `e42a43a` | — | vídeo de Paneles re-renderizado para el primer análogo del modelo corregido (E40184 con M23206) |
| `efe1081` | — | DECISIONS: texto aprobado `similarity_meaning_real_values` modificado tras la reauditoría, con antes y después (pendiente de confirmación del líder) |
| `0c5203d`, `407fdfe` | — | fusión de la web (`web-accessibility` `43f69d3` y `5a6c4b3`: sin "best" en la ayuda de teclado y los créditos) |
| `3ed19b2` | — | relectura independiente de todos los textos publicados (`11_textos_finales.md`: GO en las tres misiones) y comprobación de los vídeos (`14_comprobacion_videos.md`, provisional) |

Aviso de estado (14:05 CET): los informes de re-auditoría de las tres misiones están en `final-integration` (commit `0486ad9`); sus versiones finales están en las ramas `audit-base` (`956d55b`), `audit-rover` (`6c3750c`) y `audit-solar` (`89a5c52`). En las dos últimas el punto 9 (textos) era AÚN NO solo por las frases que `4624505` corrige.

---

## 1. Primera página: estado de cada punto ahora

Leyenda: **GO** = el punto se sostiene con el modelo publicado; **AÚN NO** = queda algo que corregir o que no se ha comprobado. "Solo textos" quiere decir que ningún par, gemelo, puntuación ni puesto cambia al corregirlo.

| # | Punto | Primera auditoría | Ahora | Por qué, en una línea | Commit |
|---|---|---|---|---|---|
| 1 | Datos de entrada | AÚN NO | **GO** | las 1.445 celdas de hielo del Rover ya se dicen (y la regla de los cinco salta el hielo y el agua); textos de procedencia corregidos; la puerta `elevation_m ≥ 1` se mantiene y se dice (decisión 11:23) | `007a244`, `d24ebb3` |
| 2 | Rejilla | GO | **GO** | celdas de 1° comparables; la frase falsa "*_300m_* are 2-degree copies" corregida | `42d8bba`, `007a244` |
| 3 | Normalización y similitud | GO | **GO** | el cálculo se reproduce sin una diferencia en las tres misiones; `missions.json` y `similarity.json` publican para Rover la banda muerta `exp(-0.5·max(0, \|d\|/sigma - 1)^2)` con sigma 0,265093° y 17,4017 m (T1 corregido; `11_textos_finales.md`) | `d24ebb3`, `4624505` |
| 4 | Top 5 | GO | **GO** | los cinco de cada misión salen de la regla publicada, reproducidos por código independiente; separación 60,0° (Rover), 2,97° (Paneles), 6,06° (Base); ningún sitio reconocido saltado | `d24ebb3`, `4c0abc3`, `1209af2`, `89a5c52` |
| 5 | Robustez (pesos ±10 %) | AÚN NO | **GO** | la elevación relativa ya no decide Rover; con ±10 % siguen los cinco: Rover 10/10, Paneles 14/14, Base 16/16 con su gemelo (el 5.º de Base 10/16) | `9c07ee1`, `d24ebb3` |
| 6 | Validación externa | AÚN NO | **GO, sin mejora** | ahora existe para las tres misiones; Rover igual con la lista verificada (mediana 8,1 frente a 9,2) y peor con la completa; Paneles igual dentro de la fila de latitud (28,8 % frente a 27,9 %); Base igual (separación 0,615) | `d24ebb3`, `c5f1f6c` |
| 7 | Nombres de lugar | AÚN NO | **GO** | lugar más cercano por círculo máximo (antes, grados euclídeos: 8.284 celdas mal); nombres de los 15 pares = vecino más cercano en 15/15 | `007a244` |
| 8 | Cifras de los audios | AÚN NO | **AÚN NO (solo grabaciones)** | los textos finales de las 19 pistas están en `transcripts.json` y comprobados por un revisor independiente (`10_textos_audio.md`); las 19 grabaciones siguen en `app/public/audio/pending.json` (el equipo anunció grabarlas hacia las 14:35 CET); hasta que lleguen la web muestra el texto de cada pista y no reproduce nada | `0486ad9` |
| 9 | Coherencia documentos-datos | AÚN NO | **GO (una repetición anotada)** | relectura independiente de todos los textos publicados: GO en las tres misiones; T1, T6, T7 (Rover) y F1, F4, estabilidad (Paneles) corregidos; queda una repetición en la ficha del Rover (la frase de los 254 empatados aparece 3 veces), pasada a la web (`11_textos_finales.md`) | `4624505`, `3ed19b2` |
| A | Inventario de números | AÚN NO | **AÚN NO** | confianza eliminada, constantes dobles documentadas, pendiente mínima justificada por su efecto; queda sin mover la configuración muerta (DECISIONS 11:28 §6 y 12:10 "No hecho") | `d24ebb3` |
| B | Rangos físicos | AÚN NO | **AÚN NO** | la temperatura lunar imposible de M32647 (439 K en una semicelda) no se ha corregido; la irradiancia antártica sigue sin contraste; B2 (media de elevación) ya no afecta a Rover | sin commit |
| C | Pares frente a fuentes externas | GO | **GO, con matices declarados** | los 15 sitios publicados ahora, contrastados con fuentes externas; cerrados los dos huecos (alias "300 m" documentado; E4037 libre de hielo permanente según Natural Earth y ESA WorldCover); seis matices que decir (base kilométrica, E17538 ~4 K más templada, E19672, irradiancia ±12 %, rugosidad de E4037, ~30 % de agua en E4037, despejado de E28670 +0,08) (`12_contraste_realidad_nuevos.md`, "Cierre de los dos huecos") | `e28283a` |
| D | Sentido físico | AÚN NO | **GO, con debilidades declaradas** | fuera la elevación relativa del Rover, la geometría de latitud y la irradiancia modelada de Paneles, la clase térmica duplicada y el permafrost de Base; quedan debilidades de criterio dichas en la web | `9c07ee1`, `d24ebb3` |
| E | Unidades y saturación | AÚN NO | **GO** | la saturación de Paneles y la de la idoneidad de Rover se dicen; el texto de Paneles dice ahora "half of the suitability (50 %: its weight 0.35 out of the 0.70 ...)" (F1 corregido, `missions.json`) | `007a244`, `4624505` |
| F | Estadística del ranking | AÚN NO | **AÚN NO (solo grabaciones)** | "the five best" fuera de los textos del motor y de los textos de audio; la estabilidad medida se publica en las tres misiones con las cifras de la re-auditoría (`top5_stability_*`, `11_textos_finales.md`); faltan las grabaciones de audio (`pending.json`); el título de la web "The five best analogs" está sustituido en la web fusionada (`68bf081`, `5a6c4b3`: título según el número de empatados o "Five of the highest-scoring analogs in our model"), pero el sitio publicado sigue siendo el ensayo con el título antiguo (despliegue final no hecho) | `4624505`, `407fdfe` |

**Veredicto de los re-auditores del modelo corregido (contrato revisión 8):** Rover **GO** ("publicar el Rover corregido", con T1, T6 y T7 antes), Base lunar **GO** ("publicar la Base lunar corregida"; sus dos correcciones de texto ya están en el paquete), Paneles solares **GO** ("publish the corrected Solar panels", con F1, F4 y la estabilidad antes). Estado final: la re-auditoría de Base lunar es definitiva con los nueve puntos GO (`9_reauditoria_base.json`, "all nine items GO"; rama `audit-base` `956d55b`); las de Rover (`6c3750c`) y Paneles (`89a5c52`) daban AÚN NO en el punto 9 solo por las frases que `4624505` corrige, y la relectura independiente posterior da GO a los textos de las tres misiones (`11_textos_finales.md`). Los cinco análogos de cada misión están publicados: los cinco ids de `top5.ids` están en `explain.json` con su puesto (Rover 3, 254, 251, 241, 236; Paneles 1, 2, 5, 7, 9; Base 1, 3, 5, 6, 7). Ninguno encontró un fallo de implementación: 0 diferencias en 10.337, 18.777 y 2.419 puntos, y la vuelta atrás al estado de la mañana es exacta en las tres.

**Lo que sigue débil, dicho claramente:**
- **Rover:** el orden es la idoneidad del equipo (Spearman final-idoneidad 1,000), porque 10.335 de 10.337 pares están dentro de la incertidumbre de medida (similitud 100); 254 sitios empatan arriba y los cinco son una muestra de ellos (lista exacta en el 10,5 % de 200 simulaciones). Bardenas y Tabernas caen al 68,2 % y 71,5 %.
- **Paneles solares:** dentro de la misma fila de latitud la validación no mejoró (28,8 % frente a 27,9 %); los cinco nunca se repiten en 200 simulaciones; un punto sin dato de nubes (Sulawesi) queda 16.º (las tres cosas ya dichas en la web).
- **Contraste externo (punto C):** GO con seis matices que se dicen al visitante (`12_contraste_realidad_nuevos.md`).
- **Base lunar:** los cinco son frágiles (0 de 200 simulaciones los repiten; ninguno pasa del 23 %), y solo 3 de los 13 análogos reconocidos pasan su embudo (2 con gemelo).

**Antes de publicar faltan:** las 19 grabaciones de audio (`app/public/audio/pending.json`; anunciadas para las 14:35 CET; si no llegan, la web muestra el texto y no reproduce nada, y hay que decirlo); la confirmación del líder de la redacción nueva de `similarity_meaning_real_values`, texto aprobado modificado tras la reauditoría (antes y después en `docs/DECISIONS.md`, sección "Texto aprobado modificado tras la reauditoría (15-11-2026)"); el despliegue final: **no se ha hecho**. La rama web `web-accessibility` ya está fusionada en `final-integration` (commits de fusión `0c5203d` y `407fdfe`; `npm run build` y `npm run test:data` pasan sobre el paquete final), pero el intento de despliegue de las 14:09 CET lo bloqueó Vercel (`TEAM_ACCESS_REQUIRED`: el autor del último commit es una identidad de automatización que no es miembro del equipo de la cuenta; no se cambió nada en la cuenta). https://stars-beside-you.vercel.app sigue sirviendo el ensayo de las 13:25 CET (web `70cac01`, con el título "The five best analogs"): no es el sitio final; cómo desplegar lo decide el titular de la cuenta. Siguen abiertas, sin aplicar, las decisiones de diseño de §6 (entre ellas la temperatura lunar imposible de M32647 y la configuración muerta, punto A).

---

## 2. Qué encontró la auditoría y qué se hizo

Cada fila: hallazgo con su cifra (fichero), decisión (quién y cuándo), qué se aplicó y el antes y el después. "Líder" = Facundo, líder del equipo; casi todas las decisiones las comunicó su delegado "en nombre del líder" (así lo dice `DECISIONS.md`).

### 2.1 Errores corregibles sin cambiar un criterio (corrección 1, `correcciones_1.md`, `007a244`)

| Hallazgo (auditor) | Cifra | Aplicado | Antes → después | Prueba |
|---|---|---|---|---|
| Lugar "más cercano" calculado en grados (punto 7, `1_datos_rejilla_nombres.md` §7.5) | 8.284 de 25.497 celdas de tierra con otro lugar; 1.754 de 16.098 mostradas fuera de la Antártida; 0 en los 15 pares de audio | k-d tree sobre vectores unitarios + haversine en `engine/places.py` | 8.281 celdas cambian de nombre (`correcciones_1.md`; el auditor contó 8.284 celdas con otro lugar: 3 cambian de fila pero no de nombre) | `test_nearest_place_is_the_great_circle_nearest_on_every_land_cell` |
| Hielo en el ranking de Rover sin decirlo (punto 1) | 1.445 de 10.192 (1.101 Antártida; Groenlandia 217 por caja de coordenadas según el auditor, **201** por etiqueta de país según la corrección) | nota en `known_limitations`; desde las 11:23 la nota es `surface_classes_rover`, calculada en cada build, y desde las 11:28 la regla de los cinco salta hielo ≥ 0,5 | ahora: 1.506 puntos de hielo, el mejor n.º 1.089, 0 en el top 50, 0 entre los cinco (re-auditoría Rover §9) | test de correcciones 1 |
| Frase falsa "*_300m_* columns are 2-degree copies" (punto 9.2.5) | — | texto de `engine_config.json` | corregida | `test_not_used_by_engine_why_is_true_for_the_real_table` |
| Similitud de Paneles saturada sin decirlo (punto E) | 78 % de 6.360 pares ≥ 99; 514 en 100,00; mediana 1.843,5 candidatos por punto | texto nuevo `solar_similarity_saturation` | dicho en cada par y en la tarjeta | `test_solar_saturation_text_with_recomputed_figures` |
| Doble redondeo de distancias en el generador de audio (punto 8.3.2) | 15,47 → 16; 45,48 → 46; 82,52 → 82 | `make_audio_top5.py` redondea una vez | 15, 45, 83 | `test_audio_top5_is_regenerated_and_rounds_once` |
| "in NASA's X candidate region" con el centro fuera (puntos 7 y C) | parte de la celda dentro: 0,43 / 7,8 / 33 / 45 / 0,32 % | regla "in" si ≥ 50 % de la celda, "at the edge of" si no (confirmada a las 11:23) | hoy 69 de 103 gemelos de Base lunar tienen < 50 % dentro (DECISIONS 11:23 §3) | idem |
| Amplitud MODIS llamada "modelled" (punto 1) | — | aviso del audio corregido | "derived from MODIS land-surface temperature" | idem |
| Redondeo de la frase de Base lunar distinto del contrato (punto 3) | 8 valores de 8 pares | `toFixed` exacto en `engine/display.py` | `explain.json` no cambia | `test_to_fixed_matches_javascript` |
| Restos sin marcar en DECISIONS, ASSUMPTIONS, LUNAR_BASE_PROPOSAL, REAL_DATA, DATA_CONTRACT (punto 9.2) | glosario z-score, "36 %", "Artemis III", permafrost "vacío", 4 niveles frente a 5 | marcas "SUSTITUIDO" y textos alineados | "35 %" por la regla `share_lost_of_displayed_tenths` (100 × (9,6 − 6,2)/9,6 = 35,4) | `test_levels_of_the_bundle_and_the_contract_agree` |
| Vídeos | Paneles: par del método anterior (E44120/M59479, polo sur); Rover: "Sun elevation 21.1°" imposible a ≤ 75 S (máximo 16,04°) | avisos en los README; después el vídeo de Paneles se volvió a renderizar para el primer análogo del modelo corregido, E40184 con M23206 (`e42a43a`), y la tarjeta final del vídeo de Base lunar se volvió a renderizar con los criterios corregidos (`691af33`) | — | comprobación independiente provisional `14_comprobacion_videos.md` (`3ed19b2`) |

Resultado: 185 tests pasan (171 + 14 nuevos), paquete reconstruido dos veces idéntico byte a byte, y **ningún `.bin` de puntuaciones o pares cambia** (`correcciones_1.md`, "Paquetes reconstruidos").

### 2.2 Debilidades que cambiaban un criterio: decisiones del líder

| Debilidad (auditor, cifra) | Efecto medido de las opciones (`7_efecto_decisiones_pendientes.md`, `research_*`) | Decisión (quién, cuándo) | Aplicado | Antes → después |
|---|---|---|---|---|
| **Rover: el top 5 lo decide la elevación relativa** (secundaria 20 %; sin ella las cinco del audio caen a los puestos 357-452; parte de la dispersión de la similitud 52,8 %; `3_robustez` Fallo 2, `5_inventario` D.1) | quitarla: top 5 0/5, top 50 2/50 (`5_inventario` A.2) | elevación relativa a peso 0; pendiente 50 % + rugosidad 50 %; también fuera del filtro, fila informativa (delegado del líder, **11:23**; lectura del director comunicada al líder) | `9c07ee1`, contrato rev. 7 | emparejados 10.192 → 10.337; gemelos distintos 401 → 1.166 (rev. 7; 1.144 con la rev. 8 publicada); mayor cuota de un gemelo 19,9 % (M61116) → 2,6 % |
| **Rover: escala de las diferencias** (con la tolerancia, 74 empates en 100,00 a las 11:23) | `research_5_rover_escala.md`: candidatos A y C-S1 (254 empatados) | banda muerta σ: σ pendiente 0,265093°, σ rugosidad 17,401661 m (ETOPO 2022 RMSE 7,17 m; LOLA ~10 m) (aprobado **11:51**) | `d24ebb3`, rev. 8 | 254 empatados en 100,00; 241 tras los saltos |
| **Rover: los cinco pares comparten un gemelo** (M59895 en los cinco; `2_metodo` §4.4, `7_efecto` P3) | opción "cada gemelo una vez": rompe las pistas 2-5 | resuelto por el cambio de variables: hoy 1.144 gemelos distintos, el mayor con 2,6 % | rev. 7 y 8 | 5 pares con 1 gemelo → 5 gemelos distintos |
| **Casi duplicados en los cinco** (Paneles: tres celdas de Derby a 0,96-1,39°; `2_metodo` §4.3) | `7_efecto` P2: separación de 2° rompe las pistas 2-5 de Paneles y 4-5 de Rover | separación mínima de 2° para elegir los cinco (11:23); a las 11:28/11:36, regla `rank_with_skips` (hielo ≥ 0,5, tierra < 0,5, 2°) para Paneles y Base, `spread_within_top_tie` para Rover; la regla de tierra la confirmó el líder a las 12:10 | `9c07ee1`, `d24ebb3` | el ranking completo no cambia; solo cómo se eligen los cinco |
| **Rover: pendiente mínima 0,5° sin fuente** (el filtro más influyente: +7.847 puntos sin él; `5_inventario` A.2) | sin el mínimo (regla de las 11:23): mayor cuota de un gemelo 13,9 %, agua en top 50 4 → 13, análogos conocidos peor | se mantiene, justificada por su efecto, sin fuente y así se dice (11:23; 12:10 §4) | ninguna anulación | con la regla publicada (banda σ) el efecto es igual o mayor: 16,4 %, agua 12 → 25, 1.321 empatados (re-auditoría Rover) |
| **Paneles: la idoneidad repite la latitud** (Sol máximo y Sol rasante, funciones de la latitud; Spearman idoneidad-\|lat\| −0,857; `5_inventario` D.2) | `research_2_solar_idoneidad.md` opción E2 | fuera irradiancia WorldClim (0,35), `sun_elev_max_deg` (0,15), `sun_low_frac_0_5deg` (0,15); dentro `clear_frac_isccp` 0,35 (malo 0,308, bueno 0,671 = P10/P90) (11:28/11:36, E2 aprobada **11:51**) | `d24ebb3` | Spearman idoneidad-\|lat\| −0,857 → +0,337; 7 de los 50 primeros coinciden con la mañana |
| **Paneles: validación externa ausente** (`3_robustez` Fallo 6) | `research_4_validacion_externa.md`: 13 BSRN + 6 Met Office | lista `validation_sites_solar.csv`, texto calculado en cada build | `d24ebb3`, `c5f1f6c` | ver §3.2 |
| **Base lunar: dos criterios de las mismas clases CCI y permafrost sin sentido** (correlación de utilidades 0,893; permafrost falta en 607 de 2.419; `5_inventario` D.3) | `research_3_base_lunar.md` opción R | `thermal_inertia_class` 0,15 → 0 (sigue requerida y excluye agua), `rock_or_bare_frac` 0,10 → 0,25, `permafrost_class` 0,05 → 0 (aprobada **11:51**) | `d24ebb3` | gemelos y similitudes idénticos (0 de 450 cambian); idoneidad cambia en 2.222 puntos, rango en 437; top 50 conserva 38 |
| **Base lunar: zona "toca la región"** (centros fuera; `7_efecto` P1) | (b) centro dentro: 271 pares; (c) ≥ 50 %: 284; (d) ≥ 5 %: 435 (frente a 450) | se mantiene la zona de 280 celdas; el texto dice "at the edge of" (11:23 §3) | rev. 7 | sin cambio en pares |
| **Confianza por par sin origen y uniforme** (`5_inventario` A.3) | Rover y Paneles "medium", Base "low" en todos | eliminada; en su lugar `top5_stability_<misión>` (11:28 §6) | `d24ebb3` | columnas vacías |
| **"the five best analogs on Earth"** en audio (`3_robustez` F.5) | Paneles 0/200, Base 0/200, Rover 2,5 % de corridas repiten el top 5 | "five of the highest-scoring analogs in our model" (11:23 §5); Rover: "five of the 254 sites tied at the top of our model, chosen to be spread across the world" (12:10 §5); regrabar una vez | textos (`0486ad9`, comprobados en `10_textos_audio.md`) | grabaciones pendientes (`pending.json`) |
| **Hielo, puerta `elevation_m ≥ 1`, saturación, números sin efecto** | `7_efecto` P4 (hielo no toca top 5 ni top 50), P6 (+1 / +28 / +18 puntos; pistas 3-4 de Base se intercambiaban) | mantener y decirlo (11:23 §4); `mission_scoring.json` no se edita | textos `limit_texts` | — |
| **Constantes con dos valores** (oblicuidad 23,44° / 23,4393°; radio 6.371,0 / 6.371,0088 km) | efecto ≤ 0,00012 kWh/m²/día; 0,3 m en 2° | documentadas, texto `constants_two_values` (11:28 §6) | `d24ebb3` | sin cambio de número |

---

## 3. Estado por misión tras la re-auditoría

Todas las cifras de esta sección son de los informes de re-auditoría (`9_reauditoria_<misión>.md` y `.json`), que recalculan con código propio (`tierra luna/audit/ra_<misión>_*.py`, sobre la reimplementación `p5_common.py` de la primera auditoría; no importan `tierra luna/engine`). Donde cito "mañana" es el estado `audited_morning` (= `42d8bba`/`a493514`).

### 3.1 Rover (`9_reauditoria_rover.md`; veredicto **GO**)

**Regla ahora.** Embudo e idoneidad del equipo sin cambio (`mission_scoring.json`: puertas pendiente 0,5-15° y rugosidad 5-650 m; idoneidad pendiente 0,45, rugosidad 0,30, fracción desnuda o rala 0,25; `mission_scoring_deviations: []`). Similitud: pendiente (`slope_iso_deg`) y rugosidad, clave las dos, 0,5 + 0,5; puntuación `exp(−½·max(0, |d|/σ − 1)²)` con σ 0,265093° y 17,401661 m; filtro 2° y 30 m; zona lat ≤ −75 (5.400 celdas); elevación relativa solo informativa. Final = 0,5 × similitud + 0,5 × idoneidad.

**Pares y gemelos.** Pasan 10.337; emparejados 10.337; gemelos distintos 1.144; mayor cuota M59712 con 271 puntos (2,6 %) (mañana: 10.192, 401, M61116 19,9 %).

**Los cinco y cómo se eligen.** Regla `spread_within_top_tie`: entre los 254 empatados con final 100,00, quitar hielo (≥ 0,5: 0 quitados) y celdas con menos de la mitad de tierra (13 quitados, todos de clase agua 210), y elegir los cinco más separados (la regla de 2° no actúa). Resultado: **E4037** (Gjoa Haven, Nunavut, 1.115,8 km; gemelo M63714, Sverdrup), **E50510** (Comandante Luis Piedra Buena, Santa Cruz; M59438, Zeeman), **E44239** (Peterborough, South Australia; M59712, Schrödinger), **E26510** (Dahasuways, Al Mahrah, Yemen; M63711, Haynes), **E26087** (Barkewol, Assaba, Mauritania; M61294, Drygalski); puestos 3, 254, 251, 241, 236. Tierra ≥ 69,7 %, hielo 0, separación mínima 60,0°. Alternativa publicada (`rank_with_skips`): E4037, E4742, E4751, E4962, E5125.

**Tabla de diferencias (10.337 pares; cotas comprobadas en todos):**

| Variable | Mediana | P90 | Máximo | Tolerancia = cota del filtro | σ | Mañana (mediana / P90 / máx.) |
|---|---|---|---|---|---|---|
| pendiente (°) | 0,016 | 0,044 | 0,280 | 2,0 | 0,265 | 0,41 / 0,85 / 1,97 |
| rugosidad (m) | 1,09 | 2,84 | 16,89 | 30,0 | 17,40 | 5,34 / 20,55 / 29,97 |
| elevación relativa (m, solo información) | 3.410,6 | 5.415,9 | 10.517,3 | — | — | 247,9 / 798,9 / 1.000,0 (cota 1.000) |

10.335 de 10.337 pares tienen las dos diferencias dentro de σ (similitud 100). Nota: `DECISIONS.md` (11:23) da para la regla de tolerancia de las 11:23 0,03 / 0,09 / 0,60° y 0,53 / 1,38 / 9,43 m; son las de un estado intermedio (rev. 7), no las publicadas.

**Estabilidad ante la incertidumbre de entrada (200 simulaciones, semilla 20261115):**

| Análogo | Entre los cinco | Top 20 (por empates) | En el grupo empatado | Conserva gemelo | Pasa el embudo |
|---|---|---|---|---|---|
| E4037 | 52,5 % | 72,5 % | 72,5 % | 29,5 % | 100 % |
| E50510 | 43,0 % | 43,0 % | 43,0 % | 30,0 % | 100 % |
| E44239 | 65,0 % | 88,5 % | 88,5 % | 38,0 % | 96,0 % |
| E26510 | 87,5 % | 100 % | 100 % | 17,5 % | 100 % |
| E26087 | 67,0 % | 74,0 % | 74,0 % | 25,0 % | 83,0 % |

Los cinco: lista exacta 10,5 % (mañana 0,0 %); 60 listas distintas (mañana 191); 502 puntos a ≤ 1 del quinto (mañana 20,5); de los 254 empatados siguen empatados el 89,0 % (mediana). Lectura del re-auditor: menos estable que la mañana en orden y gemelo (gemelo 17,5-38 % frente a 100 %), comparable en qué sitios salen; lo estable es el grupo empatado. Incertidumbres: ETOPO 7,17 m y LOLA 10 m documentadas; pendiente y rugosidad 5 % y fracción desnuda 0,05 **ilustrativas**.

**Pesos ±10 %:** los cinco siguen, con su gemelo, en 10/10 perturbaciones (por saturación, no por robustez del orden; mañana 12/12).

**Validación externa (percentil del puesto, menor = mejor):** lista verificada: mediana de 7 positivos 8,1 (mañana 9,2), cuartil superior 5/8 (5/8), separación positivo-negativo 0,906 (0,906): **igual**. Lista completa: mediana 14,3 (16,0), cuartil 6/11 (7/11), separación 0,855 (0,927): **peor**. Mejoran Ramon 3,6 (6,2), Yungay 8,1 (9,2), MDRS 20,5 (28,9); empeoran Qaidam 4,1 (0,2), Haughton 4,2 (1,7), Bardenas 68,2 (44,5), Tabernas 71,5 (24,7).

**Lo que queda débil (del criterio decidido, no de la implementación):**
- El orden de Rover es la idoneidad del equipo: Spearman final-idoneidad 1,000 (mañana 0,498). 254 sitios empatan arriba porque la similitud vale 100 y además los tres criterios de idoneidad se saturan (umbrales "bueno" 1°, 30 m y 0,7): 250 de los 254 tienen las tres utilidades al máximo; 253 puntos publican idoneidad 100,00.
- Bardenas y Tabernas pierden 24,4 y 19,8 puntos de idoneidad por la fracción desnuda a 1° (ESA CCI: 1,8 % y 14,6 %); 7.042 puntos quedan por delante de Bardenas.
- E26087 (0,523°) y E44239 (0,547°) están junto al mínimo de 0,5° y salen del embudo en el 17 % y el 4 % de las simulaciones.
- E4037 se nombra por un lugar a 1.116 km (correcto por la regla, no localiza el sitio; T5).

**Textos (corregidos en `4624505`, releídos en `11_textos_finales.md`):** T1 la fórmula publicada es la banda σ; T6 `top5_stability_rover` lleva las cifras de la re-auditoría (52,5/72,5 … 10,5 %, 60 cincos, gemelo 17,5-38 %, 89 %); T7 `rover_slope_minimum` dice 26 de 50, 12 → 25 y 16,4 %; T4 sin "TO BE CONFIRMED"; T8 corregido. Queda la repetición anotada de la frase de los 254 empatados (tres veces en la ficha), pasada a la web.

**Discrepancias entre ficheros:** el puesto de Bardenas es 7.043 en `9_reauditoria_rover.md` de `1209af2` y **7.046** en la versión final del índice y en `DECISIONS.md` 12:10 §2 (7.042 estrictamente mejores); Tabernas 7.385 frente a 7.390. Qaidam: 4,05 exacto (puesto 419); la web dice "4,0" y `DECISIONS.md` 11:28 §4 "4,1".

### 3.2 Paneles solares (`9_reauditoria_solar.md`, `89a5c52`; veredicto **GO**)

**Regla ahora.** Puertas del equipo sin cambio (irradiancia en suelo ≥ 2,5, pendiente ≤ 15, Sol ≥ 10°, Sol rasante ≤ 0,25, no sobre agua). Idoneidad: pendiente 0,15, amplitud 0,10, rugosidad 0,10, fracción despejada ISCCP-H 0,35 (0,308 → 0,671). Los pesos suman **0,70**; el motor divide por la suma, así que el peso efectivo del despejado es **50 %** (pendiente 21,4 %, amplitud 14,3 %, rugosidad 14,3 %). Similitud sin cambio: luz sobre la atmósfera 0,8 clave (τ 0,6 kWh/m²/día), pendiente 0,1 (τ 2°), rugosidad 0,1 (τ 30 m), secundarias con cota 2τ; zona |lat| ≤ 30° y elevación ≤ −1.200 m.

**Pares y gemelos.** Pasan 18.777; emparejados 6.360; gemelos distintos 1.704 (igual que la mañana: el emparejamiento no cambia).

**Los cinco y cómo se eligen.** `rank_with_skips` sobre la clasificación completa (hielo ≥ 0,5, tierra < 0,5, 2°). **E40184** (Manja, Madagascar; M23206, Timocharis), **E29749** (Eyl, Somalia; M26063), **E23648** (Jati, Pakistán; M22156), **E29746** (Gaalkacyo, Somalia; M26056), **E28670** (Iskushuban, Somalia; M25483); puestos 1, 2, 5, 7, 9; saltados por la separación E40543 (3), E40904 (4), E29747 (6), E30105 (8). Avisos: E29749 tiene un tercio de mar (clase dominante agua, 66 % de tierra) y pasa la regla; E23648 es regadío del Sind; tres de los cinco están en Somalia a 3-5° entre sí.

Cinco "antes": dos listas según el estado. `audited_morning` (vuelta atrás, `42d8bba`): E38464, E38105, E38744, E37746, E38465 (puestos 1-5). Estado de las 11:23 con separación de 2° (`DECISIONS.md` 11:28 §2): E38464, E38744, E37746, E37750, E29749. Las dos son correctas para su estado; si Paneles vuelve atrás, vuelve a la primera.

**Tabla de diferencias (6.360 pares; ninguno sobre su cota):**

| Variable | Papel | Mediana | P90 | Máximo | Cota |
|---|---|---|---|---|---|
| luz sobre la atmósfera (kWh/m²/día) | clave | 0,0208 | 0,3222 | 0,5696 | 0,6 |
| pendiente (°) | secundaria | 0,034 | 0,146 | 1,941 | 4 |
| rugosidad (m) | secundaria | 0,50 | 2,36 | 58,14 | 60 |

Idénticas a la mañana. Saturación: 78 % de los pares con similitud ≥ 99; 514 en 100,00.

**Estabilidad (200 simulaciones; despejado con 0,05 absoluto ILUSTRATIVO):** entre los cinco 9,5 / 7,0 / 13,0 / 1,5 / 0,5 % (mañana 0,0 / 0,0 / 2,0 / 0,5 / 0,0 %); top 20 40,0 / 37,5 / 31,5 / 14,5 / 12,5 % (mañana 6,5-19,5 %); conserva gemelo 0,5-8 %; los cinco se repiten 0 de 200 en los dos estados; puntos a ≤ 0,5 del quinto 26 (mañana 76). Más estable que la mañana, frágil en absoluto.

**Pesos ±10 %:** 14/14 para los cinco con su gemelo, orden idéntico 12/14 (mañana E38465 10/18).

**Validación externa (13 BSRN positivos, 6 Met Office negativos):**

| | corregido | mañana |
|---|---|---|
| mediana de los positivos, clasificación completa | 8,3 % | 14,9 % |
| positivos en el cuartil superior (de 11 que pasan) | 9 | 8 |
| mediana dentro de su fila de latitud | **28,8 %** | **27,9 %** |
| separación positivo-negativo | 0,923 | 0,923 (la deciden las puertas) |

Mejor en la clasificación completa; **igual dentro de la fila de latitud** (con 11 sitios la diferencia no es interpretable): no se demuestra que la idoneidad diga más que la latitud sobre estas estaciones.

**Dato nuevo ISCCP-H:** reducción rehecha desde los 60 ficheros NCEI 2012-2016: 64.778 celdas, diferencia máxima 5·10⁻⁵, orientación correcta en 10 de 10 lugares; hielo tan "despejado" como un desierto (mediana 0,588) pero sin efecto en pares (0 puntos con hielo ≥ 0,5 tienen gemelo).

**Lo que queda débil:** F2: 3 puntos sin dato de nubes; E34142 (Sulawesi) queda **16.º** solo por la renormalización (consecuencia del criterio "no requerido; se renormaliza"). F5: validación dentro de la fila igual. F6: despejado y amplitud térmica correlacionados (ρ +0,67), la amplitud resta. Los cinco nunca se repiten.

**Textos (corregidos en `4624505`, releídos en `11_textos_finales.md`):** F1 `solar_suitability_clouds` dice "half of the suitability (50 %: its weight 0.35 out of the 0.70 ...)"; F4 `known_limitations[2]` da los criterios 0,35 / 0,15 / 0,1 / 0,1; F2 dice que el punto de Sulawesi queda 16.º, fuera de los cinco; `top5_stability_solar` lleva las cifras (0 de 200, 14 de 14); la nota de validación dentro de la fila de latitud (28,8 % frente a 27,9 %) está publicada. F3 corregido en `c5f1f6c`.

### 3.3 Base lunar (`9_reauditoria_base.md`, `4c0abc3`; veredicto **GO**)

**Regla ahora.** Puertas sin cambio (amplitud ≥ 15 K, tmin ≤ 5 °C, no agua, tierra ≥ 0,3). Idoneidad: amplitud 0,35, tmin 0,25, fracción desnuda 0,25 (0,1 → 0,7), irradiancia 0,10; suman **0,95** (efectivos 36,8 / 26,3 / 26,3 / 10,5 %, ahora dicho en `lunar_base_criteria`). Similitud sin cambio: tmin y amplitud como percentil dentro de su población, 40 % + 40 %, tolerancia 10 puntos; pendiente y rugosidad en valor real, 10 % + 10 %, filtro 4° y 60 m; zona: 280 celdas que tocan las nueve regiones de la NASA.

**Pares y gemelos.** Pasan 2.419; emparejados 450; gemelos 103 (igual que la mañana; 0 de 450 gemelos cambian).

**Los cinco.** `rank_with_skips`: **E21054** (Tinghir, Marruecos; M62517), **E17538** (Aheqi, Xinjiang; M63528), **E21833** (Kherameh, Fars; M62515), **E18627** (Waxxari, Xinjiang; M62479), **E19672** (Aradan, Irán; M63657); puestos 1, 3, 5, 6, 7; saltados E21412 (2) y E20695 (4) por la separación (junto a Tinghir). Tierra 0,958-1,000, hielo 0-0,083, clase CCI 200 en los cinco, separación mínima 6,06°. Mañana: E17538, E16830, E15751, E21054, E17187.

**Tabla de diferencias (450 pares, iguales en los dos estados):**

| Variable | Escala | Mediana | P90 | Máximo | Cota |
|---|---|---|---|---|---|
| tmin | percentil | 3,17 | 7,72 | 9,79 | 10 |
| amplitud diaria | percentil | 2,99 | 7,67 | 9,95 | 10 |
| pendiente (°) | real | 1,51 | 2,69 | 3,92 | 4 |
| rugosidad (m) | real | 27,26 | 54,43 | 59,81 | 60 |

En valor real (primera auditoría, `2_metodo_top5_unidades.md`, sin cambio): tmin 207,88 / 210,55 / 211,94 K; amplitud 153,76 / 161,28 / 179,40 K (la Luna siempre mucho más fría: el parecido es de posición térmica, no de temperatura). La primera auditoría da la mediana de rugosidad como 27,27 y la re-auditoría como 27,26 (redondeo).

**Estabilidad (200 simulaciones):** entre los cinco / top 20: Tinghir 18,0 / 51,5 %; Aheqi 23,0 / 52,5 %; Kherameh 19,0 / 43,5 %; Waxxari 18,0 / 38,0 %; Aradan 22,5 / 59,0 %. Los cinco se repiten 0 de 200 (también la mañana). Medias: entre los cinco 0,20 (mañana 0,145), top 50 0,69 (0,62). E17538 está a +0,60 K de la puerta de 15 K y sale del embudo en el 36,5 % de las simulaciones. Algo más estable que la mañana; frágil.

**Pesos ±10 %:** los cinco conservan su gemelo 16/16; siguen entre los cinco 16, 16, 15, 15 y **10**/16 (E19672, a 0,07 del siguiente elegible); cinco idénticos 4/16 (mañana 8/20).

**Validación externa (13 positivos fríos o polares, 7 negativos):** pasan el embudo 3 de 13; con gemelo 2: Craters of the Moon puesto 179 (7,4 %; mañana 7,0 %) y MDRS 335 (13,8 %; mañana 14,7 %); Black Point pasa sin gemelo. Separación positivo-negativo 0,615 en los dos estados. **Igual.** Ningún análogo polar pasa: Haughton 2,50 K, Svalbard 1,23 K, Kangerlussuaq 6,63 K de amplitud; McMurdo y Concordia sin LST. Sin la puerta de 15 K encabezarían celdas de Ellesmere con 0,94-1,91 K y similitud 97,65-99,83.

**Textos:** los dos fallos que bloqueaban (`external_validation_lunar_base` falso; estabilidad "pending") están corregidos en el paquete actual (DECISIONS 12:10, "Correcciones de texto de la re-auditoría de Base lunar"; comprobado hoy: el texto cita MDRS 335 y Craters of the Moon 179, y la estabilidad tiene cifras). Corregidos también los menores (pesos 0,95, MEASURED, `also_in_similarity`).

### 3.4 Mediana y P90 de cada variable (antes y después)

| Misión | Variable | Tolerancia / cota | Mañana: mediana / P90 / máx. | Ahora: mediana / P90 / máx. |
|---|---|---|---|---|
| Rover | pendiente (°) | 2 / 2 (σ 0,265) | 0,408 / 0,851 / 1,971 | 0,016 / 0,044 / 0,280 |
| Rover | rugosidad (m) | 30 / 30 (σ 17,40) | 5,34 / 20,55 / 29,97 | 1,09 / 2,84 / 16,89 |
| Rover | elevación relativa (m) | 500 / 1.000 → solo información | 247,9 / 798,9 / 999,99 | 3.410,6 / 5.415,9 / 10.517,3 |
| Paneles | luz sobre la atmósfera (kWh/m²/día) | 0,6 / 0,6 | 0,0208 / 0,322 / 0,570 | igual |
| Paneles | pendiente (°) | 2 / 4 | 0,034 / 0,146 / 1,941 | igual |
| Paneles | rugosidad (m) | 30 / 60 | 0,50 / 2,36 / 58,14 | igual |
| Base | tmin (percentil) | 10 / 10 | 3,17 / 7,72 / 9,79 | igual |
| Base | amplitud (percentil) | 10 / 10 | 2,99 / 7,67 / 9,95 | igual |
| Base | pendiente (°) | 2 / 4 | 1,51 / 2,69 / 3,92 | igual |
| Base | rugosidad (m) | 30 / 60 | 27,27 / 54,43 / 59,81 | igual (27,26 en la re-auditoría) |

Fuentes: mañana, `2_metodo_top5_unidades.md` "La tabla" (`out/p2_table.csv`); ahora, las tres re-auditorías. Ningún máximo supera su cota en ningún estado.

---

## 4. Valores eliminados o justificados

Del inventario (punto A, `5_inventario_sentido_fisico.md` A.2-A.5) y de las decisiones.

**Quitados del modelo del motor** (el fichero del equipo `mission_scoring.json` no se edita; cada desviación está en `engine_config.json` `criteria_sets` con valor del equipo, el nuestro, razón y fuente; tabla `DECISIONS.md` 11:28 §7, publicada como `deviations_from_team`):
- Rover, similitud: peso de la elevación relativa 0,2 → 0, fuera del filtro (11:23).
- Paneles, idoneidad: `irradiance_kwh_m2_day` 0,35 → 0; `sun_elev_max_deg` 0,15 → 0; `sun_low_frac_0_5deg` 0,15 → 0 (sus puertas siguen) (11:51).
- Base, idoneidad: `thermal_inertia_class` 0,15 → 0 (sigue como puerta); `permafrost_class` 0,05 → 0 (11:51).
- Confianza por par (puntuaciones 1 / 0,7 / 0,3 / 0,2; umbrales 0,8 / 0,5; 1 km): eliminada del paquete (11:28 §6).

**Añadidos o cambiados, con fuente:**
- Paneles: `clear_frac_isccp` 0,35 (0,308-0,671 = P10/P90 de los 18.777; ISCCP-H HGM, NOAA NCEI, Rossow y Schiffer 1999).
- Base: `rock_or_bare_frac` 0,10 → 0,25.
- Rover: σ 0,265093° y 17,401661 m (MacFerrin et al. 2025, ESSD 17, 1835-1849; Smith et al. 2010, GRL 37, L18204; matiz: 7,17 m es la media de los RMSE de subteselas de 1° y 10 m es exactitud absoluta, cota pesimista).

**Justificados por su efecto medido, sin fuente externa (y así se dice en la web):**
- Rover pendiente mínima 0,5°: sin ella +7.847 puntos (2.862 hielo), 1.321 empatados, un gemelo con el 16,4 %, análogos 4-5 puntos de percentil peor (regla publicada; ver la discrepancia T7 de §3.1).
- Base puerta de amplitud ≥ 15 K: sin ella encabezan celdas de Ellesmere con ~1 K y similitud ~99.
- Puerta común `elevation_m ≥ 1`: se mantiene; su razón escrita ("océano a −250 m") ya no vale en la tabla real; quita 177 celdas de tierra por debajo de 1 m (37 con ≥ 30 % de tierra) (11:23 §4).

**Listados y dejados en el fichero del equipo, sin efecto** (texto `numbers_without_effect`): Rover rugosidad 5-650 m (0 celdas excluidas, cita no encontrada); Rover pendiente máxima 15° (fuente VIPER, inerte a 3,7 km de base); Paneles pendiente ≤ 15°, Sol ≥ 10°, Sol rasante ≤ 0,25 (0 puntos excluidos); `require_present` de las tres misiones; `mask_fraction` en Base; `default` de las tablas de clases; 273,15 K en la similitud.

**Configuración muerta, sin mover** (no hecho: DECISIONS 11:28 §6 y 12:10 "No hecho en este paso"): pesos por dominio de `mission_scoring.json` (no los lee ni el motor ni la web), tolerancias y `workable_days` del Rover, `similarity_zones.solar` (−75°, de la regla anterior), tolerancias de referencia sin uso, escala por rango agregado. La nota "Use Weights" del fichero del equipo sigue siendo falsa.

**Ilustrativos o no validados (rotulados así):** tolerancias 2° y 30 m ("ILUSTRATIVO - set by Robotics 1"), el bloque de idoneidad del Rover ("provisional"), los umbrales de Paneles y Base ("valores de diseño NO validados").

**Dos valores de una constante:** documentados, no unificados (efecto despreciable, §2.2).

---

## 5. Audios, pista por pista

Primer veredicto (`4_audios_coherencia.md` §8.2, sobre los MP3 grabados; los SHA256 de las 19 pistas coincidían con `SHA256SUMS.txt`):

| Pista | Primer veredicto | Motivo |
|---|---|---|
| 00_welcome | minor | "slope and roughness decide everything": omitía la elevación relativa (entonces 20 %) |
| m1_rover | minor | omitía la elevación relativa; "the five best analogs on Earth" (punto F) |
| m2_solar | minor | omitía pendiente y rugosidad; "the maria" es etiqueta del equipo; "the five best" (F) |
| m3_base | **RE-RECORD** | "coldest, steadiest sites on Earth, against the coldest cells" es falso; "the five best analogs" (F) |
| rover_1 a rover_5 | minor (las cinco) | "height above each world's average level" impreciso; cifras exactas |
| solar_1 | exact | — |
| solar_2 | minor | "both receive about 9.6": la Luna da 9,7 |
| solar_3 | minor | "about 9.5": la Tierra da 9,6 |
| solar_4 | exact | — |
| solar_5 | minor | "Similarity: 100 percent" (99,9968) sugiere par idéntico |
| base_1 | minor | "in NASA's Haworth candidate region": 0,43 % de la celda dentro |
| base_2 | minor | "16 kilometers" (15,47, doble redondeo) |
| base_3 | minor | "46 kilometers" (45,48, doble redondeo) |
| base_4 | exact | — |
| base_5 | minor | "in ... Nobile Rim 2": 0,32 % de la celda dentro |

**Ahora:** las **19 pistas se vuelven a grabar** desde textos nuevos, porque los cinco pares de cada misión cambiaron (Rover, Paneles y Base) y las introducciones cambian de criterio y de redacción (decisión 11:23 §5: "el equipo vuelve a grabar una vez"). Los textos finales están en `app/public/audio/transcripts.json` (commit `0486ad9`; antes, ahora y motivo de cada pista en `docs/AUDIO_RERECORD.md`, generados por `tierra luna/tools/make_audio_top5.py`) y los comprobó un revisor independiente con código propio (`docs/stats_audit/10_textos_audio.md`, 470 comprobaciones). Las grabaciones **no existen todavía**: `app/public/audio/pending.json` lista las 19 pistas a la espera de la nueva grabación del equipo (anunciada para las 14:35 CET); hasta que lleguen la web muestra el texto de cada pista y no reproduce nada. Ningún audio se ha generado ni editado en este paso.

---

## 6. Decisiones de diseño que siguen abiertas

Cada una con su cifra y las opciones; ninguna está aplicada.

1. **Rover: el orden es la idoneidad del equipo.** 10.335 de 10.337 pares en similitud 100; 254 empatados; Spearman final-idoneidad 1,000; Bardenas 68,2 % y Tabernas 71,5 %. Opciones: (a) mantener y decirlo (estado actual: texto `rover_suitability_saturation`); (b) revisar los umbrales "bueno" del equipo (1°, 30 m, 0,7) o el criterio de suelo desnudo a 1°: efecto **no medido**; (c) usar la alternativa publicada `rank_with_skips` (E4037, E4742, E4751, E4962, E5125), que no cambia el empate.
2. **Rover: pendiente mínima 0,5° sin fuente.** Mantener (decidido) o buscar fuente; cifras de §4. Además E26087 sale del embudo en el 17 % de las simulaciones.
3. **Rover: zona del polo sur por los planes de la NASA, no por datos** (08:55 §2): en el polo norte el gemelo es más parecido en el 87,3 % de los 9.790 puntos con par en los dos (cifra con la regla de la mañana; no recalculada con la banda σ).
4. **Paneles: pesos que suman 0,70.** Aplicada la opción (a): el texto dice "half of the suitability (weight 0.35 of 0.70)" (`4624505`). Sigue abierta (b): renormalizar los pesos escritos para que sumen 1 (mismo resultado numérico).
5. **Paneles: punto sin dato de nubes en el puesto 16** (E34142, Sulawesi, idoneidad 96,23). Opciones: (a) mantener la renormalización y decirlo; (b) exigir el dato (`require_present`): efecto **no medido** (3 puntos afectados).
6. **Paneles: la validación dentro de la fila de latitud no mejoró** (28,8 % frente a 27,9 %). Sin opción medida; ya se dice en la web (`4624505`).
7. **Base lunar: puerta de 15 K y fragilidad.** E17538 a +0,60 K (sale el 36,5 %); 0/200 repeticiones; ningún análogo polar pasa. Medido: sin la puerta encabezan celdas de ~1 K; con la mitad de error (σ × 0,5, mañana) el top 5 tampoco se repite (coincidencia media 1,28). Una puerta más baja o una tolerancia mayor: **no medidas**.
8. **Base lunar: qué celdas cuentan como dentro de las regiones de la NASA.** 69 de 103 gemelos con < 50 % dentro. Opciones medidas (`7_efecto` P1; el emparejamiento de Base no cambió después, así que los recuentos de pares valen hoy; las listas de cinco eran las de la mañana): centro dentro 113 celdas y 271 pares; ≥ 50 % 109 y 284; ≥ 5 % 246 y 435; hoy 280 y 450.
9. **Puerta común `elevation_m ≥ 1`.** Quitarla (o "tiene valor"): Rover +1 punto, Paneles +28 (+3 pares), Base +18 (cambiaba el orden de dos de los cinco de la mañana) (`7_efecto` P6, estado de la mañana; no recalculado con el modelo corregido).
10. **Temperatura lunar imposible en M32647** (punto B1: semicelda a 439 K, celda a 405,61 K y amplitud 311,75 K; no afecta a ningún par, se ve en el mapa lunar). Opción del auditor: descartar en `build_moon.py` un bin que supere en más de 20 K la mediana de sus vecinas o 400 K. Es corrección de dato; no aplicada.
11. **Configuración muerta** (§4): moverla a un bloque `legacy` (exige cambiar lecturas de código; aplazado).

---

## 7. Cómo volver a ejecutar cada script

Todos son deterministas; semilla 20261115 en los Monte Carlo. La primera auditoría usaba el Python del entorno `PY=/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/bin/python` (ruta del entorno de los auditores; en otra máquina, cualquier Python 3.13 con numpy, pandas, scipy, shapely/geopandas y reverse_geocoder). Desde la raíz del repositorio, salvo donde se indica:

```
# Punto 1, 2, 7 (1_datos_rejilla_nombres.md)
$PY "tierra luna/audit/p1_raw_cells.py"; $PY "tierra luna/audit/p1_inputs.py"; $PY "tierra luna/audit/p1_grid.py"
$PY "tierra luna/audit/p1_names.py";     $PY "tierra luna/audit/p1_regions.py"
# Puntos 3, 4, E (2_metodo_top5_unidades.md)
$PY "tierra luna/audit/p2_recompute.py"; $PY "tierra luna/audit/p2_contract_sum.py"
$PY "tierra luna/audit/p2_top5.py";      $PY "tierra luna/audit/p2_units.py"
# Puntos 5, 6, F (3_robustez_validacion_ranking.md), desde "tierra luna/audit"
python p3_baseline.py; python p3_robustness.py; python p3_validation.py; python p3_ranking_stats.py
python p3_percentile_unc.py; python p3_montecarlo.py rover 200 1.0; python p3_montecarlo.py solar 200 1.0
python p3_montecarlo.py lunar_base 200 1.0; python p3_mc_summary.py
# Puntos 8, 9 (4_audios_coherencia.md)
$PY "tierra luna/audit/p4_audio_check.py"; $PY "tierra luna/audit/p4_regions.py"
$PY "tierra luna/audit/p4_geodesy.py";     $PY "tierra luna/audit/p4_docs_coherence.py"
# Puntos A, D (5_inventario_sentido_fisico.md); p5_sensitivity.py tarda 30-60 min
$PY "tierra luna/audit/p5_baseline.py"; $PY "tierra luna/audit/p5_sensitivity.py"; $PY "tierra luna/audit/p5_physical.py"
$PY "tierra luna/audit/p5_shown_numbers.py"; $PY "tierra luna/audit/p5_inventory.py"
# Puntos B, C (6_contraste_realidad.md); p6_fetch_ext.py y p6_power_gsa.py descargan fuentes abiertas
$PY -I "tierra luna/audit/p6_ranges.py"; $PY -I "tierra luna/audit/p6_extremes.py"; $PY -I "tierra luna/audit/p6_lunar_ext.py"
$PY -I "tierra luna/audit/p6_elev_mean_sensitivity.py"; $PY -I "tierra luna/audit/p6_pairs.py"; $PY -I "tierra luna/audit/p6_regions.py"
$PY -I "tierra luna/audit/p6_fetch_ext.py"; $PY -I "tierra luna/audit/p6_power_gsa.py"
# Efecto de las opciones (7_efecto_decisiones_pendientes.md)
$PY "tierra luna/audit/w0_reproduce.py" ... "tierra luna/audit/w6_gate_elev.py"   # w0 a w6, 1-3 min cada uno
# Re-auditoría de Rover: ra_rover_config.py, ra_rover_audit.py, ra_rover_fallback.py, ra_rover_weights.py,
#   ra_rover_mc.py, ra_rover_texts.py, ra_rover_summary.py (salidas tierra luna/audit/out/ra_rover_*)
# Re-auditoría de Base lunar: ra_base_recompute.py, ra_base_robustness.py, ra_base_montecarlo.py,
#   ra_base_validation.py, ra_base_places.py, ra_base_gate.py, ra_base_texts.py (salidas out/ra_base_*)
# Re-auditoría de Paneles solares, desde "tierra luna/audit":
python ra_solar_recompute.py corrected ../../app/public/data/v2 final_corrected
python ra_solar_recompute.py audited_morning <paquete de a493514> final_morning
python ra_solar_config.py; python ra_solar_data_layer.py <carpeta con los 60 ficheros ISCCP-Basic.HGM 2012-2016>
python ra_solar_robustness.py corrected; python ra_solar_robustness.py audited_morning
python ra_solar_montecarlo.py corrected 200 20261115; python ra_solar_montecarlo.py audited_morning 200 20261115
python ra_solar_validation.py; python ra_solar_five.py corrected
# Tests del motor (desde "tierra luna"): python -m pytest -q   (185 passed en 007a244; incluye
#   test_audit_corrections_1.py, test_decisions_1123.py, test_decisions_1128.py, test_texts_1210.py)
# Paquete: python -m engine build   (dos construcciones idénticas byte a byte, comprobado en cada paso)
```

Los nombres de los scripts de la re-auditoría de Rover y de Base están en sus informes y en `tierra luna/audit/`; esos dos informes no traen la línea de orden exacta de cada uno.

---

## 8. Lo que no se ha podido establecer

- **Contraste externo de los 15 pares publicados ahora** (punto C): hecho (`12_contraste_realidad_nuevos.md`, GO con matices); en E4037 no se intentó RGI 7.0 / GLIMS (Natural Earth y WorldCover ya concordaban) y el recuento de WorldCover es una muestra (overview ×8).
- **Incertidumbre por celda** de la pendiente y la rugosidad (ETOPO 2022, LDEM_16), de la irradiancia lunar, de la fracción desnuda (ESA CCI) y de la fracción despejada ISCCP-H: no documentada; los Monte Carlo usan valores **ilustrativos** (5 %, 2 %, 0,05, 0,05). Las conclusiones de estabilidad dependen de ellos, sobre todo en Rover.
- **Correlación espacial de los errores:** todos los Monte Carlo usan ruido independiente por celda.
- Diviner GCP: solo el ruido instrumental (< 1 K), no el error del promedio estacional ni del relleno de huecos.
- Efecto de las constantes de los constructores de tablas (`GCP_MIN_VALID`, `GCP_MAX_GAP`, `SUN_SEMIDIAMETER_DEG`, `RA_MIN_VALID_FRAC`): exige reconstruir las tablas.
- Irradiancia anual medida en la estación South Pole (B3): no encontrada.
- Fuente oficial de la media de elevación de la tierra emergida (B2): solo pistas (ya no afecta a Rover).
- Efecto de quitar la puerta `elevation_m ≥ 1`, de una puerta de amplitud menor o de exigir el dato de nubes en el modelo corregido: no recalculado.
- Teclas de la guía de audio ("Press one/two/three"): la web las tiene en la rama `web-accessibility`, ya fusionada en `final-integration` (`0c5203d`, `407fdfe`); no comprobado aquí. La revisión UX independiente del commit web `70cac01` (rama `ux-review`, `218b96d`) da 39 puntos GO sin bloqueos; la tasa de fotogramas no es medible en un contenedor sin GPU (~1 fps con WebGL por software) y queda como no medida.
- Vídeos: el de Paneles re-renderizado para E40184 con M23206 (`e42a43a`) y la tarjeta final del de Base lunar (`691af33`) tienen una comprobación independiente **provisional** (`14_comprobacion_videos.md`: un fotograma de tarjeta y uno 3D por vídeo; faltan el resto de fotogramas, los webm y el texto completo de la señal 13 en español).
- Este documento no ha recalculado ninguna cifra con código propio: cada cifra se ha comprobado contra el fichero del que sale (informes de auditoría, `DECISIONS.md`, `correcciones_1.md` y, para el estado de los textos, `app/public/data/v2/similarity.json` y `missions.json` leídos el 15-11-2026 a las 13:20 CET). Donde dos ficheros discrepan se dan las dos cifras (Groenlandia 217/201; Bardenas 7.043/7.046; Qaidam 4,0/4,05/4,1; cinco "antes" de Paneles; rugosidad de Base 27,27/27,26; pendiente mínima 28/26 de 50, 13,9/16,4 %).
