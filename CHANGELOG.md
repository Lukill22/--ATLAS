# Changelog

## 0.3.0

- Se agregaron ingresos: `ingreso: 100000 uber` (mismo parser seguro que los gastos).
- Se agregó el comando `listar ingresos`.
- Se agregó el comando `balance dia` (ingresos, gastos y balance de hoy).
- `format_money` ahora muestra bien los montos negativos (`-$5.000`).
- Si escribís un comando casi bien (`gasto 15000 nafta` sin los dos puntos, `gastos:` en plural, o incluso con un error de tipeo como `gsato`), Atlas pregunta a qué te referías antes de guardar nada; si confirmás, lo guarda bien tipado (con monto y descripción), y si no, lo guarda tal cual como nota.
- Se agregaron 62 pruebas: ingresos, balance, guardado/lectura (con archivo temporal) y la detección/corrección de formato (incluye un caso documentado de falso positivo: "área" se confunde con "tarea:", y el costo es solo una pregunta de más).

## 0.2.1

- Se corrigieron dos bugs del parser de gastos: no reconocía "Gasto:" en mayúscula y "15.5" se guardaba en silencio como $15.500.
- Se agregaron pruebas automatizadas para las funciones de `main.py`.
- Se formateó `src/atlas/main.py` con Black.
- Se agregó `requirements-dev.txt` para las dependencias de desarrollo.
- Se unificó la carpeta de documentación a `docs/` (antes `Docs/`).
- Se limpió el historial de Git para quitar `data/entries.jsonl`.

## 0.2.0

- Se agregaron gastos estructurados.
- Se agregó el comando "total gastos".
- Se mejoró la forma en la que Atlas guarda el monto y la descripción de cada gasto.

## 0.1.0

- Se agregó la captura rápida de notas, ideas, tareas y gastos.
- Se agregaron comandos para listar registros.
- Se protegió `data/entries.jsonl` para evitar subir datos personales a GitHub.
