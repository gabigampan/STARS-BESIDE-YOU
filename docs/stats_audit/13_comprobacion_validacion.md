# 13. Comprobación independiente de docs/VALIDATION.md

Fecha 2026-11-15. Revisor independiente (no escribió el documento ni sus scripts). Script propio: `tierra luna/audit/v_check_validation.py` (lee los `.bin` del bundle según `docs/DATA_CONTRACT.md` rev. 8, sin importar el motor); salida `tierra luna/audit/out/v_check_validation.json`. No se re-ejecutó `validation/run_all.py`.

**Veredicto: GO.**

## Recalculado desde el bundle

| misión | pasan el embudo | emparejados (rango 1..N) | gemelos distintos | top5 dentro de su celda | gemelo del top5 en la zona |
|---|---|---|---|---|---|
| Rover | 10,337 | 10,337 | 1,144 (= twins.json) | 5 de 5 | 5 de 5 (región B; zona A+B) |
| Placas solares | 18,777 | 6,360 | 1,704 | 5 de 5 | 5 de 5 (región D) |
| Base lunar | 2,419 | 450 | 103 | 5 de 5 | 5 de 5 (región A) |

Además, todos los gemelos de cada misión caen en su zona lunar y la suma de `twin_count` en `moon_<misión>.bin` es igual al número de emparejados.

## Cifras comprobadas

Resumen y titulares de las secciones 1-7: cobertura por misión (m1), validez 251,420 de 251,430 (m2, suma de las 7 tablas), recall y precisión de las cuatro listas (m9, m3), solar dentro de la fila de latitud 28.8 % frente a 27.9 % (9_reauditoria_solar.json), base lunar 0 de 13 y 3 de 13 pasan el embudo (m9), sensibilidad (m4: Rover top-50 >= 42, 604 / 483; solar >= 45, 1,312 celdas, 0 pares cambiados; base lunar >= 47 con pesos, 4 de 4 cambios del número 1, top-50 29-40, 100-306 gemelos), reproducción 5,192 / 2,613 / 1,986 y 18,777 / 2,419 / 2,419 (m5), coordenadas 17,147 puntos, 99.52 %, gemelos 1,144 / 1,704 / 103 (m6 y bundle), cifras globales 86.5 / 83.7 / 68.1 (m7). Todas coinciden con su fuente.

## Corrección hecha

- Resumen, fila 5: "18,777 / 2,419 / 2,419" estaba en la columna Rover y podía leerse como Rover / Solar / Base. El orden es solar / thermal (= base lunar) / ambos (`out/m5_reproduction.csv`, `missions.json`: Rover 10,337, solar 18,777, base lunar 2,419). No era una cifra mal calculada; se añadieron las etiquetas.

## Redacción

La cifra global se presenta como resumen de comprobaciones y "not a probability" (resumen y sección 7); no aparece "validated" ni "accuracy" salvo para decir que no se da ningún porcentaje de acierto; la frase de latitud de las placas solares está en la sección 3.

## Nota aparte (fuera del documento)

`docs/DATA_CONTRACT.md` (rev. 7, punto 1) dice que `twins.json` Rover tiene 1,166 gemelos; el bundle tiene 1,144. Es el documento de validación el que tiene razón. Se señala, pero no se cambió (fuera de mi encargo).
