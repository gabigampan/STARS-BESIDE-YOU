# 15. Comprobación independiente de la integración de los audios (15-11-2026, después de las 14:30 CET)

Comprobador independiente que no hizo la integración. Rama `final-integration`, HEAD `0d87802` (commit del líder encima de la integración `e41af38`). Script: `tierra luna/audit/a2_audio_integration_check.py` (solo lee) → `tierra luna/audit/out/a2_audio_integration_check.json`. Ningún audio se ha editado, recodificado ni renombrado; nada se ha confirmado ni subido.

**Veredicto: GO para la integración** (textos y ficheros). No verificado: que las palabras dichas coincidan palabra por palabra con `transcripts.json` (nadie aquí ha escuchado ni transcrito el audio; el equipo dice que grabó desde el texto).

## Comprobaciones

| # | Qué | Resultado |
|---|---|---|
| 1 | Los 19 MP3 de `app/public/audio/` frente a la copia sin modificar de la entrega de las 14:20 CET | 19/19 idénticos byte a byte (`cmp`); 19/19 coinciden con su línea de `SHA256SUMS.txt` (19 líneas); `SHA256SUMS.txt` y `transcripts.json` idénticos a los del equipo; ningún otro MP3 en la carpeta |
| 2 | `transcripts.json` frente a `0486ad9` | mismas 19 claves; solo difiere `rover_1.mp3`, y solo por la cláusula quitada ", about 1,116 kilometers north of Gjoa Haven" |
| 3 | `pending.json` y `tracks.json` | `pending_rerecord: []`. En `app/src/a11y/audio.ts` un fichero de la lista pasa al estado `pending` ("Text only: new recording pending") y nunca se pide; con la lista vacía, con la guía activada, cada pista se reproduce cuando su paso o su pareja está en pantalla. `tracks.json`: la entrada n de cada misión es `<misión>_n` (`rover_n`, `solar_n`, `base_n`), con `rank` n y la celda de la Tierra igual al n-ésimo de `top5.ids` del bundle: 15/15 |
| 4 | Generador `tierra luna/tools/make_audio_top5.py` | ejecutado (código 0); el `transcripts.json` que escribe es idéntico byte a byte al del equipo (`cmp`); `docs/AUDIO_TOP5.json` y `docs/AUDIO_RERECORD.md` sin cambios en `git status`. La regla de los lugares lejanos es general: `NEAREST_PLACE_MAX_KM_ON_SCREEN = 300`, comprobado en ejecución contra `const NEAREST_PLACE_MAX_KM = 300` de `app/src/flow/detailPanel.ts`; un lugar a más de 300 km no se dice (`nearest_named_place_spoken`); Gjoa Haven/rover_1 solo aparece en el texto de una nota, no como caso especial. `audit/t_audio_texts.py`: **472 comprobaciones, 0 fallos**. pytest (`test_audit_corrections_1.py`, `test_texts_1210.py`, `test_texts_reaudit.py`): **39 passed, 1 skipped**; después, `presets.json` restaurado con `git checkout`. `npm run -s test:data`: **all data checks passed** |
| 5 | Medidas del integrador (`tierra luna/audit/out/a_audio_files.csv`, 19 filas) re-medidas aquí en tres ficheros con ffprobe y ffmpeg volumedetect | rover_4: 34,534 s, media −23,1 dB, pico −2,1 dB; base_3: 51,775 s, −22,9, −1,7; base_1: 50,939 s, −22,9, −1,5: las tres iguales al CSV |

Rango del CSV frente a lo que declaró el equipo: duración 34,534-51,775 s (equipo: 34,5 a 51,8 s); volumen medio −23,3 a −22,7 dB (igual); pico −3,2 a −1,5 dB (equipo: como mucho −1,5); las 19 se decodifican sin error; silencios de 1 s o más (−50 dB) solo dentro de dos pistas: 1,45 s en m1_rover y 1,00 s en m3_base ("sin silencios largos" se sostiene si una pausa de hasta 1,5 s no cuenta como larga).

## Despliegue

El primer intento, a las 14:09 CET, lo bloqueó Vercel (`TEAM_ACCESS_REQUIRED`: en un repositorio privado de un equipo Hobby el autor del commit desplegado tiene que ser el titular del equipo). El líder añadió su commit `0d87802` y el mismo script desplegó producción a las 14:30 CET: https://stars-beside-you.vercel.app. Comprobado desde aquí solo esto: el sitio sirve `audio/rover_1.mp3` y `audio/base_3.mp3` con el mismo SHA256 que el repositorio, y `audio/pending.json` con la lista vacía. La hora y el identificador del despliegue no se han comprobado aquí (no se consultó la cuenta de Vercel). La comprobación del sitio en vivo (que los audios suenen en el navegador, título, textos) la hace otro comprobador: `16_sitio_en_vivo.md`. Cualquier despliegue posterior necesita que el último commit vuelva a ser del titular de la cuenta.

## Documentos cerrados

`README.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/PR_DESCRIPTION.md`: el despliegue ya no figura como no hecho ni el sitio como ensayo; Lighthouse queda como medido en el ensayo de las 13:25 CET, no repetido. `docs/STATS_AUDIT.md`: punto 8 GO (audio no escuchado), punto F GO (sitio en vivo sin comprobar aquí), "Antes de publicar faltan" reescrito, filas `e41af38` y `0d87802`. `docs/DECISIONS.md`: entrada del despliegue. Las ediciones del integrador (voz, modelo, cambio de rover_1, decisiones del delegado de las 14:20 CET, medidas) se comprobaron contra los ficheros y se mantienen.
