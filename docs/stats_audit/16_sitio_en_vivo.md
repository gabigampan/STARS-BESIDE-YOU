# 16. Comprobación del sitio en vivo (15 nov 2026)

Sitio: https://stars-beside-you.vercel.app (despliegue dpl_4RiDQ2poTvBEWnN1pTuym6R1dyfP, commit 0d87802). Script: `node app/tests/live.mjs <URL> [carpeta_capturas]`. Chromium headless, sin `--autoplay-policy`: el gesto en el interruptor "Audio guide" bastó.

**Veredicto: NOT YET.** Hay un fallo, y es de texto: en Solar panels y en Lunar base aparece "five best". El audio está correcto.

## Datos
- manifest.json, missions.json, transcripts.json, pending.json, tracks.json y SHA256SUMS.txt desplegados son idénticos byte a byte a los del repositorio (sha256).
- 19 de 19 MP3 desplegados coinciden con el SHA256SUMS.txt del equipo. Ese SHA256SUMS.txt y transcripts.json son idénticos a los del repositorio.
- Sin errores de consola y sin peticiones fallidas, ni a 1440x900 ni a 375x812. Solo hay abortos ERR_ABORTED de los .webm al cerrar el vídeo, que son normales.

## Encabezados (literales)
- Rover: "Five of the 254 sites tied at the top of our model"
- Solar panels: "Five of the highest-scoring analogs in our model"
- Lunar base: "Five of the highest-scoring analogs in our model"

Las cinco filas de cada misión siguen los top5.ids de missions.json, en orden, con los mismos puestos globales:
- Rover: 3, 254, 251, 241, 236
- Solar: 1, 2, 5, 7, 9
- Base: 1, 3, 5, 6, 7

La fila solo imprime "Ranked N overall" cuando N no coincide con su puesto entre las cinco.

## Fallo
- **"five best" en pantalla (Solar panels y Lunar base).** Aparece en el párrafo `p.bundle-note`, que es visible, y en dos `li` ocultos. El texto dice: "These are five of the highest-scoring analogs in our model, not a proven best: the five best final scores once a cell half or more snow and ice, ...". Viene de los datos del bundle (missions.json / similarity.json), no de `src/`. Rover no lo tiene.

## Audio
Nota: "suena" significa que el elemento de audio decodifica y su currentTime avanza. Un navegador headless no tiene tarjeta de sonido, así que nadie lo ha oído.

En cada pista se comprobó lo siguiente:
- Hay un solo elemento de audio reproduciéndose, nunca dos.
- El src es el archivo esperado.
- Avanza al menos 1,5 s en 1,5 s.
- La duración coincide con la de ffprobe con un margen de 0,2 s.
- El subtítulo coincide carácter a carácter con transcripts.json.

| archivo | suena | duración oída (s) | subtítulo igual |
|---|---|---|---|
| 00_welcome.mp3 | sí | 35.71 | sí |
| m1_rover.mp3 | sí | 39.57 | sí |
| m2_solar.mp3 | sí | 39.01 | sí |
| m3_base.mp3 | sí | 41.70 | sí |
| rover_1.mp3 | sí | 35.16 | sí |
| rover_2.mp3 | sí | 37.15 | sí |
| rover_3.mp3 | sí | 37.57 | sí |
| rover_4.mp3 | sí | 34.50 | sí |
| rover_5.mp3 | sí | 35.48 | sí |
| solar_1.mp3 | sí | 40.96 | sí |
| solar_2.mp3 | sí | 40.31 | sí |
| solar_3.mp3 | sí | 40.87 | sí |
| solar_4.mp3 | sí | 44.58 | sí |
| solar_5.mp3 | sí | 42.21 | sí |
| base_1.mp3 | sí | 50.90 | sí |
| base_2.mp3 | sí | 49.09 | sí |
| base_3.mp3 | sí | 51.73 | sí |
| base_4.mp3 | sí | 41.80 | sí |
| base_5.mp3 | sí | 51.22 | sí |

- R repite la introducción de cada misión.
- Con el móvil (toque) suenan welcome, m2_solar y solar_1.
- Con la guía apagada no suena nada y el subtítulo muestra el texto exacto.
- Un par fuera de los cinco (Solar, id 40543) no ofrece pista: el estado queda en "Text only".
- Observación menor: la pista del par sigue sonando cuando se abre el vídeo de la misión.

## Pares y vídeos
- Los 15 pares muestran los dos lados y ninguna etiqueta de confianza.
- En Lunar base, los 5 gemelos llevan "at the edge of NASA's ... candidate region".
- Vídeos (readyState 4):
  - rover.webm: 30 s
  - solar.webm: 44 s
  - lunar-base.webm: 46 s

## Interruptores y móvil
- El modo daltónico se activa y se mantiene tras recargar.
- Tab llega a los dos interruptores.
- A 375x812:
  - Los globos están apilados, con 181 px de alto cada uno.
  - El subtítulo no se recorta.
  - La primera tarjeta de misión se ve en la primera pantalla (bottom 727 px de 812).
  - No hay scroll horizontal.

## Capturas
Carpeta: /tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/live-check/
- Las dos citadas: `desktop_mission_solar.png` (muestra el texto "five best") y `phone_pair_solar1.png`.
- Por cómo está hecho el script, también las demás se tomaron con deviceScaleFactor 2, no 1.
