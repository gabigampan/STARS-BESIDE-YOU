# 11. Textos finales: punto 9 de la reauditoría (lector independiente, 15-11-2026)

Script: `tierra luna/audit/z_texts_final.py` → `tierra luna/audit/out/z_texts_final.json` (56 comprobaciones, todas leídas del bundle y de `9_reauditoria_*.json`).
Leídos: todos los textos de `missions.json` (cada misión: similarity, criteria_set, top5, known_limitations, external_validation, alternative), `similarity.json` (`texts` y bloques de reglas) y las frases de `explain.json` de los cinco análogos de cada misión.

**Los cinco análogos de cada misión están publicados**: los cinco ids de `top5.ids` están en `explain.json` y su rango en `earth_<misión>.bin` es el de `overall_ranks` (Rover 3, 254, 251, 241, 236; Placas solares 1, 2, 5, 7, 9; Base lunar 1, 3, 5, 6, 7).

## Rover — GO (con una repetición anotada)

| Clave | Veredicto | Cifra que decide |
|---|---|---|
| rover_tie, ties_at_top_rover, list_order_rover | OK | 254 puntos con final 100.00; 241 tras las exclusiones |
| rover_suitability_saturation | OK | 253 con idoneidad 100.00; 250 al máximo en los tres; 3.291 / 2.144 / 930; Bardenas nº 7.046 (70,43), Tabernas nº 7.390 (69,36), referencia nº 3 |
| rover_suitability_saturation (frase final) | CORREGIDO | decía "to be examined by the re-audit"; la reauditoría ya lo clasifica como debilidad de un criterio decidido (W1/W2) |
| top5_stability_rover = known_limitations[4] | OK | 52,5/72,5; 43,0/43,0; 65,0/88,5; 87,5/100,0; 67,0/74,0; 10,5 %; 60 cincos; gemelo 17,5–38 %; 89 % |
| rover_slope_minimum | OK | 7.847; 2.862; 26 de 50; 12→25; 16,4 % frente a 2,6 %; Qaidam 4,0→8,3, Haughton 4,2→8,4, Ramon 3,6→8,0, Yungay 8,1→11,6 |
| external_validation_rover | OK | porcentajes de `validation.corrected_pct` |
| known_limitations[2] | OK | mediana 149,0 K sobre 9.181 pares ("about 150 K") |
| similarity.score / score_by_mission.rover | CORREGIDO | sigma 0,265093° y 17,401661 m correctos, pero el texto remitía a `similarity.variables[].uncertainty_scale.sigma`, campo que no existe en el bundle; ahora remite a `engine_config.json real_value_similarity` |
| similarity_meaning_real_values | CORREGIDO | "each variable scores lower the further apart" es falso para Rover (s = 1 dentro de sigma); ahora "never scores higher when ... further apart" |
| not_used_by_engine.why (3 misiones) | CORREGIDO | decía que la similitud usa los pesos de idoneidad y que estaba "pending team confirmation"; los pesos de similitud son otros (Rover 0,5/0,5 frente a 0,45/0,30/0,25) |
| zone.name | CORREGIDO | "PSR" escrito en palabras (encargo del revisor UX) |
| known_limitations[3] + [7] + top5.rule | FALLO, no corregido | la frase "These are five of the 254 sites tied at the top of our model, chosen to be spread across the world" aparece 3 veces en la ficha (kl[3] = list_order_rover, kl[7] = rover_tie con {rule}, top5.rule) |
| E4037 (Gjoa Haven, 1.115,8 km) | OK | ningún texto usa el nombre; sólo dato en explain.json; la pantalla aplica la regla de 300 km |
| pesos, zona 5.400 celdas, gemelo mayor 2,6 %, top5_rule_parts | OK | bundle y `five_rule_exclusions` |

## Placas solares — GO

| Clave | Veredicto | Cifra que decide |
|---|---|---|
| solar_similarity_saturation = known_limitations[0] | OK | 78,0 % ≥ 99; 514 con 100.00; top 100 entre 99,00 y 100,00 |
| solar_suitability_clouds = known_limitations[6] | OK | cielo despejado 0,35 de 0,70 = 50 %; 18.777 pasan; 3 sin nube; 4,5 S 122,5 E nº 16, 96,23, fuera de los cinco |
| known_limitations[2] | OK | criterios 0,35 / 0,15 / 0,1 / 0,1 |
| known_limitations[3] | OK | 6.060 sin LST, todos a 64,5 S o más al sur, ninguno con gemelo |
| known_limitations[1] | OK | tolerancia 0,6; |lat| máxima emparejada 33,5° |
| top5_stability_solar = known_limitations[5] | OK | 9,5/40,0; 7,0/37,5; 13,0/31,5; 1,5/14,5; 0,5/12,5; 0 de 200; 14 de 14 |
| external_validation_solar | OK | 11 de 13 pasan, 0 de 6; rangos de cada estación = rango en earth_solar.bin; 8,3 frente a 14,9; 28,8 frente a 27,9 |
| pair_sentence de los cinco | OK | el % perdido coincide con los dos números impresos (5 de 5) |
| weights_why, list_order_solar | OK | 0,8/0,1/0,1; números 1, 2, 5, 7, 9 |

## Base lunar — GO

| Clave | Veredicto | Cifra que decide |
|---|---|---|
| lunar_base_criteria = known_limitations[7], deviations | OK | 0,35/0,25/0,25/0,10, suma 0,95 → 36,8/26,3/26,3/10,5; permafrost sin dato en 607 de 2.419 |
| top5_stability_lunar_base = known_limitations[5] | OK | 18,0/51,5; 23,0/52,5; 19,0/43,5; 18,0/38,0; 22,5/59,0; 0 de 200; 16, 16, 15, 15, 10 de 16 |
| external_validation_lunar_base | OK | 3 de 13 pasan; MDRS nº 335, Craters of the Moon nº 179 |
| known_limitations[1], pair_sentence | OK | en los 450 pares el gemelo es más frío y oscila más |
| twin_sharing_note, zone | OK | 103 gemelos, máximo 5,56 %; 280 celdas |
| weights_why, list_order_lunar_base | OK | 0,4/0,4/0,1/0,1; números 1, 3, 5, 6, 7 |

## Común

- Quedan 5 cadenas con "pending" (alpha 0,5, umbrales de Robotics 1): son preguntas abiertas, no cifras caducadas. No queda ningún "TO BE CONFIRMED".
- No hay vídeo ni audio citados en estos textos.
- `lunar_named_sites.json` todavía dice "PSR" en dos campos `why`/`site_note` (vienen de `real_data/lunar_named_sites.csv`); la web no los muestra (no aparecen en app/src). No se tocaron.

## Números sin cambios

Los 30 `.bin` son idénticos byte a byte a e28283a (antes de esta pasada), a 4624505 y a HEAD. explain.json, twins.json y validity.json son idénticos. En missions.json y similarity.json sólo cambian hojas de texto (0 hojas no textuales); top5 ids y overall_ranks iguales. Build: `validity: OK`.
