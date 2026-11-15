# 14 · Comprobación independiente de los vídeos (Solar y Base lunar)

Fecha: 2026-11-15. Comprobador independiente; no edité ningún vídeo. Fotogramas en el scratchpad (video-check/).

## Codificación (ffprobe)
- solar.mp4 h264 / solar.webm vp9: 1920x1080, 30 fps, 44,000 s, 1320 fotogramas en ambos.
- lunar-base.mp4 h264 / lunar-base.webm vp9: 1920x1080, 30 fps, 46,000 s, 1380 fotogramas en ambos.

## Solar: GO provisional
Tarjeta (41,5 s, mp4) y explain.json coinciden: análogo 1 de 5 (top5.ids[0]=40184, puesto 1), E40184 Menabe, Madagascar, 21,5° S 44,5° E, 18,8 km de Manja; M23206 cerca de Timocharis, 25,5° N 13,5° W, 38,5 km; idoneidad 97,94, similitud 99,83, final 98,88; luz sobre la atmósfera 9,3437 / 9,383 (dif. 0,0393, tol. 0,6); suelo 5,745; 5,7 de 9,3 -> 39 % perdido (5,7/9,3 = 0,387); pendiente 0,753 / 0,757 (0,004); rugosidad 26,56 / 27,15 (0,59); T media 300,56 / 212,81 (87,75); oscilación 13,6 / 289,73 (276,13). Las cifras 1.840, 78 %, 6.360 y 514 salen de similarity.json. No dice "best". Fotograma 3D (25 s): "3D simulation ... Not real footage"; relieve real SLDEM2015, textura procedural, tamaño y ritmo del panel ilustrativos.

## Base lunar: GO provisional
Tarjeta (43 s, mp4) y bundle coinciden: análogo 2 de 5 (top5.ids[1]=17538, puesto 3), E17538 Xinjiang Uygur Zizhiqu, China, 41,5° N 78,5° E, 62,3 km de Aheqi; M63528 cerca de Mons Malapert, 86,5° S 11,5° W, 25,1 km; idoneidad 43,15, similitud 97,31, final 70,23; Tmin 248,61 / 41,23 K (207,38), percentiles 8,37 / 8,04 (0,34); oscilación 15,60 / 153,27 (137,67), percentiles 6,72 / 10,18 (3,46); pendiente 6,652 / 7,179 (0,527); rugosidad 238,81 / 238,49 (0,32); T media 272,06 / 77,49 (194,57); elevación relativa 2.807,0 / 680,7 (2.126,3). 2.419 y 280 están en el bundle. No dice "best" ni "pair number 1". Fotograma 3D (25 s): rótulo de simulación; relieve real LOLA LDEM_80S_20M; forma, tamaño y ritmo del hábitat ilustrativos.

## Subtítulos y README
Los .vtt en inglés y en español tienen el mismo número de señales (14 cada uno) y tiempos idénticos (mismo hash de las líneas de tiempo), y la última señal acaba en 44 s (Solar) y 46 s (Base lunar). La señal 13 repite la posición y las puntuaciones de la tarjeta. Cada README nombra el par correcto, da las URL de las fuentes (PDS, NSSDC, USGS) y dice que es una simulación y no imágenes reales.

## Lo que falta comprobar (por eso "provisional")
- Solo miré un fotograma de la tarjeta y uno 3D por vídeo. Faltan: la tarjeta a +1 s y al final, el segundo fotograma 3D y los fotogramas webm (ya extraídos, sin mirar).
- El "measured max 194.51 K" y la temperatura de superficie del panel 3D de la Base lunar no los comparé con el bundle.
- No ejecuté un analizador formal de los .vtt.
- No comparé con la tarjeta el texto completo de la señal 13 en español.
