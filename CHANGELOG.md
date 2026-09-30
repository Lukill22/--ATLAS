# Changelog

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
