# 17. Simplificación de la web para un juez: comprobación independiente

URL comprobada: https://stars-beside-you.vercel.app (en vivo, desplegada desde final-integration 589f73f según el equipo; no se redesplegó). Script: `app/tests/simplify_check.mjs <url> <dirCapturas>`. Chromium de Playwright, WebGL por software, esperas fijas (1,5 a 4 s).

| Punto | Veredicto | Medida |
|---|---|---|
| 1 Guía sin transcripción, audio apagado, una línea | GO | switch Audio guide aria-checked=false; encendido: "Audio guide: Welcome / Playing / Text" (57 px en 1440, 85 px en 375); 00_welcome.mp3 avanza 1,53 a 3,03 s |
| 2 Subtítulos de vídeo apagados | SIN COMPROBAR | no se encontró el botón de vídeo con el selector usado |
| 3 Nombre en texto una vez | GO | 1 aparición en las 6 medidas |
| 4 Sin leyendas de fuente sobre los globos | NOT YET | visibles en pantalla "NASA GIBS" (Tierra) y "NASA Moon Trek: LRO WAC global mosaic (NASA/GSFC/Arizona State University)" (Luna); créditos sí presentes en "Data, limits and credits" |
| 5 Icono de reinicio | GO | 2 botones 44 px, sin texto, "Reset the Earth/Moon view" |
| 6 Frase de introducción una vez | GO | 1 vez |
| 7 Sin duplicados | GO (casi) | ninguna cadena prohibida; queda "(done)" en la fila de pasos |
| 8 Switches | GO | 3 role=switch con aria-checked, etiquetas sin estado |
| 9 Sin letra pequeña de método | GO | ninguna cadena prohibida en el inicio |
| 10 Carga y sin WebGL | GO (2,0 a 3,5 s) | tarjetas visibles a 2,0 a 2,4 s (3,5 s en 320x568); sin WebGL: gl=null, 0 paneles de error, un mensaje, 5 análogos, par abierto, Escape vuelve a "pick" |
| 11 "five best" | GO | 0 en páginas, aria-label y missions/similarity/explain.json |
| 12 Sin scroll horizontal | GO | scrollWidth = clientWidth en 6 tamaños x inicio/misión/par |
| 13 Sin scroll vertical en escritorio | GO | scrollHeight = altura en todos; 5 análogos visibles |
| 14 Sin opciones de luz solar | GO | "Sunlight" solo como nombre de variable en la tarjeta de Solar panels |
| 15 Nada sobre los globos | NOT YET | mismos créditos que el punto 4 |
| 16 Altura de cámara | NOT YET parcial | 550/350 km en todos salvo Rover en escritorio (9000/1239 km a 4 s, las 3 medidas) |
| 17 Tarjeta corta | GO | 15, 15 y 17 líneas; "More details" es details cerrado |
| 18 Textos llanos y cifras | NOT YET (jerga) / GO (cifras) | jerga: "NASA GIBS", "LRO WAC", "kWh/m²/day", "K", "(position)", "relative thermal position", "Similarity/Suitability" sin explicar; cifras iguales a explain.json |
| A Barras en móvil | NOT YET parcial | barra 48 px, Options aria-expanded, 3 switches + Keys + créditos, Escape pliega; asa: el clic no respondía (timeout) salvo una vez (globos 154 a 357 px en 375x812) |
| B Logo | GO | cabecera 36 px (escritorio) / 28 px (móvil), inicio 112 / 72 px, favicon PNG de 32 px, naturalWidth > 0 |
| C Sin solapes | NOT YET | 375x812: 1 (inicio); 812x375: 1 (inicio) + 4 / 2 (pares Rover/Solar: puntuación x "Back to the ranking"); 320x568: 2 (par Solar); texto cortado: etiquetas de pasos en 320x568 |

Errores de consola y peticiones fallidas: ninguno en 1440x900 ni en 375x812.
