# Changelog

## 0.6.1

- La interfaz web detecta errores de tipeo (igual que la terminal: sin ":", en plural, o con un typo real) y pregunta antes de guardar, con una burbuja tipo chat en vez de guardar directo como nota. `/agregar/confirmar` resuelve la respuesta.
- Rediseño visual: el composer pasa a ser un cajón de texto redondeado con botón de enviar (sin la palabra "Guardar"), y el listado pasa de tabla a tarjetas. El balance y los filtros bajan de prioridad visual.
- Se agregó `<meta name="viewport">` a las dos plantillas: sin esto, el celular mostraba la página en miniatura (bug real, detectado probando desde el celular).
- CSS responsive (el formulario y el resumen de balance se apilan en pantallas chicas).
- El servidor ahora escucha en la red local (`0.0.0.0`), no solo en `127.0.0.1`, para poder abrirlo desde el celular en la misma wifi — decisión explícita, no hay contraseña todavía. Al arrancar, imprime la URL para el celular y una advertencia.
- Se agregaron 4 pruebas (127 en total).

## 0.6.0

- Nueva interfaz web local opcional (`src/atlas/web.py`), con Flask. Usa las mismas funciones que la terminal (`save_entry`, `load_entries`, `calculate_balance`, etc.); no duplica lógica, solo cambia cómo se muestra.
- Cubre: capturar, listar con filtro de tipo/período, balance de hoy y del mes, borrar (con página de confirmación antes de borrar de verdad) y marcar tareas como hechas.
- Corre solo en `127.0.0.1`, nunca expuesta a la red.
- Quedan afuera de esta versión (se siguen usando por terminal): la detección de errores de tipeo, `recordar`/`que recordás`/`olvidar` y `backup`.
- Se extrajo `format_entry_summary()` de `show_entries()` para que la terminal y la web compartan la misma lógica de formato.
- Flask se agrega como dependencia de runtime (antes Atlas no tenía ninguna); la terminal sigue sin necesitar nada.
- Se agregaron 11 pruebas de las rutas web (123 en total).

## 0.5.0

- Memoria local simple: `recordar <algo>: <valor>` guarda un hecho (clave -> valor) en `data/memory.json`, separado de `entries.jsonl` porque no es un registro cronológico, es información que se actualiza (recordar de nuevo pisa el valor anterior, no lo duplica).
- `que recordas` lista todo lo guardado; `olvidar <algo>` borra un hecho puntual.
- La escritura de memoria es atómica, igual que `entries.jsonl` (archivo temporal + reemplazo).
- `data/memory.json` queda afuera de Git.
- Se agregaron 13 pruebas (112 en total).

## 0.4.4

- `listar` ahora acepta un filtro de período: `listar hoy`, `listar mes`, `listar tareas hoy`, `listar gastos mes`, etc.
- Se quitó `normalize_list_type` (quedó redundante): `parse_list_command` ya cubre lo mismo y además el período.
- Se agregaron 11 pruebas (parseo del comando y filtro por período).

## 0.4.3

- Nuevo comando `backup`: copia `data/entries.jsonl` a un archivo con fecha y hora (`entries.<timestamp>.bak.jsonl`), sin tocar el original. Nunca sobrescribe un backup anterior.
- Los backups quedan afuera de Git (`.gitignore`), igual que el archivo de datos real.
- Se agregaron 5 pruebas.

## 0.4.2

- Nuevo comando `balance mes`: igual que `balance dia`, pero agrupa ingresos y gastos de todo el mes actual en vez de solo el día de hoy.
- `calculate_balance` y `calculate_monthly_balance` ahora comparten la misma lógica de suma (`_sum_income_and_expenses`), solo cambia el prefijo de fecha que se usa para filtrar.
- Se agregaron 3 pruebas para el balance mensual.

## 0.4.1

- `borrar <id>` y `hecha <id>` ya no pierden líneas que Atlas no puede leer: antes, al reescribir el archivo, esas líneas se eliminaban sin avisar.
- La reescritura del archivo de datos ahora es segura: se escribe a un archivo temporal y se reemplaza al final, así una falla a mitad de camino no deja el archivo vacío.
- Se agregaron 6 pruebas de reescritura segura.

## 0.4.0

- Cada registro ahora tiene un `id` estable (antes `listar` numeraba 1..10 de nuevo cada vez, sin forma de referirse a un registro puntual).
- Nuevo comando `borrar <id>`: pide confirmar con `confirmar borrado` antes de borrar de verdad. Cualquier otra respuesta cancela sin tocar nada.
- Nuevo comando `hecha <id>`: marca una tarea como completada (`listar` la muestra con `[x]`).
- `listar` muestra el `#id` real de cada registro en vez de una posición que cambiaba en cada llamada.
- Se agregaron 14 pruebas: ids, borrado, marcado de tareas y el parseo de `<comando> <id>`.

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
