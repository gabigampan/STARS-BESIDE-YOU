# 18. Revisión independiente del rediseño "Mission Control" (redesign-hud, 37a11c4)

Build: `VITE_USE_ION=0 VITE_CESIUM_ION_TOKEN= npm run -s build`; dist servido con el servidor estático del repo (tests/lib/serve.mjs, equivalente a vite preview). Chromium de Playwright, WebGL por software. Script: `app/tests/hud_review.mjs` (secciones con `ONLY=audit,r3,motion,r10,r9`). Capturas y JSON: `scratchpad/hud-review/`. Referencia de contenido: https://stars-beside-you.vercel.app (versión anterior).

| Regla | Veredicto | Medida |
|---|---|---|
| R1 una pantalla, sin scroll | GO | scrollWidth=clientWidth y scrollHeight=alto del viewport en inicio, misión y par de las 3 misiones a 1440x900 y 1366x768 (1440/1440/900/900; 1366/1366/768/768). |
| R2 móvil sin desbordes, plegables | GO | 375x812 y 812x375: 0 elementos fuera de los bordes, sin scroll. #mf-options: aria-expanded false→true→false, alturas de globo sin cambio (154/154 a 375; es una capa). #mf-handle: true→false; a 375 los globos pasan de 154 a 357 px y el panel de 406 a 0; al volver, 154/406. A 812x375 el panel pasa de 278 a 0 pero los globos se quedan en 327 (no ganan alto). |
| R3 mismo texto, mismas cifras | GO | innerText (sin espacios) idéntico al sitio en vivo en inicio, misión 1-3 y par 1-3. Única diferencia: "Loading the Moon…" en el par 1 del rediseño (palabra de carga transitoria, permitida). Cifras: Rover 100.00/100.00/100.00, Solar 98.88/99.83/97.94, igual que en vivo; Base también igual. |
| R4 contraste ≥ 4.5:1 | GO | Ningún texto bajo 4.5:1 en ambas paletas y los cuatro viewports. Único aviso: `dd.hud-counting` con color transparente (ratio 1) mientras cuenta: es intencionado (la cifra la pinta un ::after), falso positivo. Ningún texto DOM "sobre imagen" sin fondo (las etiquetas "Earth"/"Moon" tienen fondo propio). Las etiquetas de lugar sobre el globo son de Cesium (canvas, fuera del DOM): no medibles aquí. |
| R5 texto ≥ 14 px | GO | 0 elementos bajo 14 px a 1440x900, 1366x768, 375x812 y 812x375. |
| R6 controles ≥ 44 px | GO | Ninguno bajo 44 px salvo el enlace del logo de Cesium (77x28, crédito de terceros, aparte). |
| R7 foco visible y teclado | GO | Tab x25 en inicio y x30 en par: todos los enfocados con anillo (outline ≥2 px o box-shadow). Teclas: 1 abre misión, 1 abre análogo, Escape vuelve a ranking y a inicio. Nota: los dos logos de Cesium entran en el orden de Tab sin nombre accesible ("a:" vacío). |
| R8 quieto cuando no pasa nada | GO | 3 s tras cada paso: getAnimations() vacío (salvo spinner). drawCount del haz 1,1,1 (muestreado a 0, 3 y 5 s): no se redibuja. Ningún backdrop-filter solapa un globo. Keyframes vistos en arranque, misión y par: spin (transform), hud-on (opacity), hud-draw (transform), hud-scan (opacity, transform). Nada más. |
| R9 sin WebGL | GO | getContext('webgl') y 'webgl2' null. Un solo mensaje: "This browser cannot show the 3D globes (WebGL is off). The missions, the five analogs, the pair details, the videos and the audio guide still work." Tecla 1 abre Rover con su lista, se abre un par, Escape vuelve. Sin panel de error de Cesium, sin errores de página. |
| R10 movimiento reducido | GO | getAnimations() vacío tras carga, misión y par; clases vistas en body durante toda la sesión: solo `flow`, `has-twins` (nunca hud-boot, hud-scan ni hud-counting). |
| T1 arranque | GO (con reserva) | Una vez por carga (marks presentes; no se repite al cambiar de paso). Duración declarada máx. 940 ms de animación + clase 1300 ms. Pared aquí: marks 3103 ms porque el temporizador se retrasa con WebGL por software (no representativo). Clic real en la tarjeta Rover a ~1.1 s con hud-boot activo y pointer-events auto: la misión se abre. |
| T2 escaneo | GO (con reserva) | body.hud-scan aparece al elegir misión; animación declarada 450 ms; la clase se quitó a 3.26 s de pared por el mismo retraso de temporizadores (ya sin animación en curso tras 700 ms en tests/hud.mjs). |
| T3 haz y retículas | GO | 1440x900: línea cian fina de Canadá (Tierra) a near Sverdrup (Luna) con retículas ámbar en los dos extremos (pair_1440.png, pair_375.png). Tras arrastrar el globo terrestre 80 px, el extremo de la Tierra pasa de (241,509) a (321,539) y el de la Luna queda en (715,509); drawCount 8→18: el haz sigue a la cámara (T3_pair_dragged_1440.png). |
| T4 recuento de cifras | GO (por código) | COUNT_MS = 500 (≤ 0.6 s); el recuento solo escribe data-count y un ::after: textContent del dd nunca se toca (hud.ts countUp). Cifras finales iguales a las del sitio en vivo (R3). El muestreo por fotograma de mi script no capturó muestras en este entorno (rAF/setInterval ahogados por WebGL software); tests/hud.mjs del equipo hace esa comprobación. |

## Listas

- Bajo 4.5:1: ninguno (solo el falso positivo `dd.hud-counting`, transparente a propósito).
- Bajo 14 px: ninguno.
- Bajo 44 px: ninguno; aparte, logo de Cesium 77x28 (crédito de terceros).
- Sin anillo de foco: ninguno. Aviso: logos de Cesium enfocables sin nombre.
- Diferencias de texto: solo "Loading the Moon…" (transitorio).

## Crítica (jefe de diseño)

1. Funciona: azul noche, un acento ámbar y un secundario cian; esquinas en escuadra de visor en los paneles y globos; nada de degradado violeta ni tarjetas redondeadas genéricas. Parece consola.
2. Los globos mandan en escritorio (dos tercios de la pantalla) y el haz cian con retículas ámbar es el gesto con intención del par: el mejor momento del rediseño.
3. Las transiciones son pocas, cortas y se apagan en reposo y con movimiento reducido: bien.
4. Sigue oliendo a interfaz anterior la fila de interruptores en cajas (Place names / Audio guide / Colour-blind mode / Keys / Credits): cinco cajas iguales pesan tanto como el título.
5. Los pasos 1-4 en cajas con borde repiten el mismo lenguaje de caja; parecen pestañas de dashboard, no una secuencia de misión.
6. Tarjeta del par apretada: "Similarity / likeness to its twin" parte en tres líneas y su 100.00 queda más bajo que los otros dos: las tres cifras no se alinean (pair_1440.png).
7. Debajo de Slope/Roughness el panel de detalle queda medio vacío hasta los botones; desequilibrio visible a 1440x900.
8. En móvil (start_375.png) las tarjetas de misión con barra ámbar a la izquierda y chevrón son correctas, pero el bloque de introducción en negrita blanca de 5 líneas es pesado.
9. Etiquetas de lugar de Cesium sobre la imagen (p. ej. "Canada", "Wiechert") sin halo suficiente: legibles a duras penas sobre zonas claras.
10. Tres arreglos de menos de 10 minutos: (a) alinear las cifras de la tarjeta (etiqueta en una sola línea o `align-items:end` en la rejilla de .figs); (b) aligerar la fila de interruptores (quitar el borde de caja, dejar separadores); (c) sacar los logos de Cesium del orden de Tab o darles nombre ("Cesium ion, credits").

## Recomendación

Fusionar. Todas las reglas duras pasan; los tres arreglos de la crítica (alinear cifras del par, aligerar interruptores, logos de Cesium en el Tab) son mejoras, no bloqueos.
