# 10. Comprobación independiente de los textos de audio (19 pistas)

Fecha: 2026-11-15. Revisor independiente: no escribió ninguno de los textos. Objeto: `app/public/audio/transcripts.json`, generado por `tierra luna/tools/make_audio_top5.py`. El jefe de equipo grabará **una sola vez** con estos textos.

## Método

- Script propio: `tierra luna/audit/t_audio_texts.py`. No importa el generador. Salida: `tierra luna/audit/out/t_audio_texts.json`, con los hechos y las 470 comprobaciones.
- Fuentes: el paquete `app/public/data/v2` leído según `docs/DATA_CONTRACT.md` (revisión 8, motor 3.4.0); `output_real/earth_real_1deg.csv` (`snow_ice_frac`); la tabla ISCCP; GeoNames cities1000 (la copia de `reverse_geocoder`); `engine/data/iau_moon_nomenclature.csv`; `artemis_iii_regions.geojson`.
- Formato de pantalla: el de `app/src/flow/dom.ts`:
  - `valueText`: 3 decimales por debajo de 10, 2 por debajo de 100, 1 a partir de 100; los ceros finales no se escriben; fracción, 3 decimales; percentil, 1 decimal fijo.
  - `fixed(…, 2)` para las puntuaciones.
  - Redondeo hacia arriba en el medio, sobre el valor binario exacto.
  - Frase solar: la regla `share_lost_of_displayed_tenths` del contrato.
- Distancias: se redondean una sola vez desde el float32 guardado. Además se recalculan:
  - en la Tierra, por gran círculo hasta la coordenada GeoNames del lugar;
  - en la Luna, hasta el rasgo IAU primario más cercano.
- Rumbo: brújula de 8 puntos, desde el lugar hacia el centro de la celda.

## Lo que se verificó, y salió exacto

1. **Los cinco de cada misión** (regla recalculada por mí):
   - Solar: puestos 1, 2, 5, 7 y 9. Los puestos 3, 4, 6 y 8 se saltan por estar a menos de 2°.
   - Base lunar: puestos 1, 3, 5, 6 y 7. Los puestos 2 y 4 se saltan por estar a menos de 2°.
   - Por tanto "five of the highest-scoring analogs" es correcto en las dos.
   - Rover: hay 254 empatados en 100.00. Se descartan 13 por agua y 0 por hielo, y quedan 241. La dispersión (primero la similitud más alta, luego el punto más lejano) da los cinco ids del paquete, en el mismo orden. Los dos más cercanos están a 59.96° (60.0 en pantalla).
2. **Lugares**:
   - Los 15 lugares son el lugar de cities1000 más cercano a la celda.
   - La distancia recalculada coincide con la guardada (diferencia < 0.01 km).
   - Los 15 rumbos coinciden.
   - Gaalkacyo está en Somalia (cc SO, Mudug).
   - Dos celdas no tienen región en el paquete: Canadá (Rover 1) y Etiopía (Solar 4). Por eso el texto da coordenadas.
3. **Rasgos lunares**: los 15 son el rasgo primario más cercano, con la distancia recalculada. Los nombres se escriben como en el fichero IAU del motor ("Schrodinger", "Mons Malapert", "Mons Mouton").
4. **Cifras de pantalla**:
   - pendiente y rugosidad;
   - luz sobre la atmósfera, luz en el suelo y porcentaje perdido (39, 37, 39, 38, 36), iguales a la `pair_sentence` del paquete;
   - fracción de cielo despejado, igual a la tabla ISCCP;
   - diferencia de mínima en K (208.6, 207.4, 208.2, 202.9, 207.4);
   - percentiles;
   - similitudes.
5. **Frase de región**: "at the edge of" en los cinco gemelos. Recalculé, por muestreo de área, la parte de cada celda que cae dentro de la región: 0.446, 0.004, 0.136, 0.177 y 0.0003. Todas son menores de 0.5.
6. **Longitud**: entre 85 y 105 palabras.
7. **Audio**: ningún MP3 ha cambiado, `SHA256SUMS.txt` sigue igual y `sha256sum -c` pasa.

## Correcciones (hechas en el generador y aplicadas al volver a ejecutarlo)

| Pista | Antes | Ahora | Qué lo decidió |
|---|---|---|---|
| 00_welcome | "pair each Earth site with a lunar twin" | "look for a lunar twin for each Earth site" | 12,417 puntos de Solar y 1,969 de Base lunar pasan el embudo y no tienen gemelo |
| 00_welcome | "matched on sunlight"; "matched on the cold and its daily swing" | "matched mainly on sunlight"; "matched mainly on the coldest temperature and the daily swing" | La similitud incluye también pendiente y rugosidad (peso 0.1 + 0.1). "its" hacía de la oscilación algo propio de la temperatura mínima |
| m1_rover | "near the south pole" | "the south polar region, from 75 degrees south to the pole" | La zona es lat ≤ -75 y los gemelos llegan a 440 km del polo (regla 2) |
| m1_rover | "Many sites differ … so they tie at the top score"; "All five share the same final score…" | "Almost every site differs … so the likeness cannot tell them apart; 254 of them also get full marks, or nearly, on our Rover criteria" | 10,335 de los 10,337 pares de Rover tienen similitud exactamente 100. Lo que separa a los 254 empatados es la idoneidad: 250 tienen la nota máxima en todo y 4 tienen 99.99. Lo apoya el texto del paquete "The Rover suitability is saturated too" |
| rover_1..5 | "within what the elevation data can measure, they all match their twins equally well" | "it matches its twin within what the elevation data can measure, and it gets full marks on our Rover criteria" | Lo mismo: emparejar igual de bien no es propio de los 254. Los cinco tienen utilidad 1 en los tres criterios (fichero de detalle) |
| m2_solar | "match places on the sunlight"; "maria near the equator" | "match mainly on the sunlight"; "maria within 30 degrees of the equator" | Peso de la clave 0.8 de 1.0. La zona es \|lat\| ≤ 30 (regla 2) |
| m3_base | "match on the coldest temperature and its daily swing"; "regions near the south pole" | "match mainly on the coldest temperature and the daily swing"; "regions in the south polar region" | Pesos 0.4 + 0.4 de 1.0. Las regiones llegan a unos 227 km del polo (regla 2) |
| base_1..5 | "the Moon's coldest temperature is … kelvin lower" | "its twin's coldest temperature is … kelvin lower" | La cifra es la de la celda gemela (`tmin_k.diff`), no la mínima de la Luna |
| base_1,2,3,5 | "The slope is alike: …" | "The slopes are close enough for our model: …" | En la base 3 (3.738 frente a 5.053) y en la 5 (4.198 frente a 5.547) la diferencia pasa de 1.3°. Solo cumplen la tolerancia de 2°, así que "alike" decía más de lo que hay |

Pistas solar_1 a solar_5: sin cambios. Son exactas.

## Dudas que quedan (no son errores)

- **Rover 1.** Gjoa Haven está a 1,116 km. Es el lugar más cercano en cities1000 (Resolute y Grise Fiord no aparecen, porque tienen menos de 1000 habitantes), pero la pantalla no lo muestra, porque pasa de 300 km. Se dice con la distancia, así que es correcto, aunque sea poco útil.
- **El número 254.** El texto de Rover usa 254, como pide el jefe y como dicen `top_tie_n` y `rover_tie`. Los cinco salen de los 241 que quedan sin las celdas de agua. Esto no se dice en audio.
- **Estado del paquete.** Rover y Solar siguen en reauditoría, y otros agentes estaban modificando el paquete mientras yo trabajaba (`missions.json` cambió a las 12:07). Si cambian los cinco, el empate o las puntuaciones, hay que volver a ejecutar el generador y `t_audio_texts.py` antes de grabar.
- **"The slopes are close enough for our model".** Significa dentro de la tolerancia de 2°. En la base 4 la diferencia es de 2.129°, y por eso no lleva la frase.
- **HEAD no es la grabación.** `git show HEAD:app/public/audio/transcripts.json` ya no es el texto de lo grabado: un commit de control (1f502f5) guardó el texto del redactor. El texto que corresponde a los MP3 es el de a567950 (= d24ebb3, la última vez que cambiaron los MP3 y `SHA256SUMS.txt`). Comparando con ese, cambian las 19 pistas, y `pending.json` lista exactamente esas 19.
