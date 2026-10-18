# Changelog

## 0.7.2

- `handle_command` ahora tolera errores de tipeo y palabras de más en los comandos fijos de solo lectura (`ayuda`, `total gastos`, `balance dia`/`mes`, `backup`, `que recordás`): por ejemplo "total de gatos" ya se reconoce como `total gastos`, en vez de guardarse como nota. Caso real reportado usando el bot.
- No se confunde con `listar` (que tiene su propio parser): "listar gastos" nunca se interpreta como "total gastos", aunque comparten la palabra "gastos".
- 8 pruebas nuevas (163 en total).

## 0.7.1

- Se corrigió un bug real que tiraba abajo el bot de Telegram entero: un corte de conexión (`ConnectionResetError`) no estaba entre los errores que el loop sabe absorber. Ahora cualquier error de red (no solo timeout) se absorbe y reintenta, con una pequeña espera antes de reintentar.
- El `/start` automático de Telegram (se manda solo al abrir el chat la primera vez) ya no se guarda como nota: el bot responde con un saludo.
- `HELP_TEXT` (compartido entre terminal, web y bot) se achicó: se sacó el bloque de "cómo capturar" (una vez que se sabe usar, sobra) y se condensaron las variantes de `listar`/`balance`.
- 2 pruebas nuevas (155 en total).

## 0.7.0

- Nuevo bot de Telegram opcional (`src/atlas/telegram_bot.py`): deja capturar y consultar Atlas desde un chat, sin abrir ninguna app dedicada. Reusa exactamente la misma lógica que la terminal y la web (`save_entry`, `detect_entry_type`, `handle_command`, etc.), no duplica nada.
- Usa "long polling" (el bot le pregunta a Telegram, no al revés): no necesita ningún servidor público ni configuración de red, a diferencia de WhatsApp/Messenger. Corre con el token en `ATLAS_TELEGRAM_TOKEN` (nunca versionado).
- La confirmación de errores de tipeo y de borrado usan botones inline reales de Telegram, no texto.
- `handle_command()` se movió de `web.py` a `main.py` para que la terminal, la web y el bot compartan la misma interpretación de comandos sin duplicarla.
- No se agregó ninguna dependencia nueva: la API de Telegram se habla con `urllib` de la librería estándar.
- 13 pruebas nuevas del bot (153 en total).

## 0.6.5

- La respuesta de `ayuda` en la web ya no aparece desplegada de una: queda colapsada (`<details>`/`<summary>`, sin JavaScript) con un "Ver comandos disponibles" para abrirla cuando quieras. El resto de las respuestas (balance, listar, etc.) siguen abiertas, como antes.
- 2 pruebas nuevas (140 en total).

## 0.6.4

- Las secciones por tipo (Gastos, Ingresos, Tareas, Ideas, Notas) pasan de estar todas apiladas a ser **pestañas**: se ve una a la vez, con la cantidad de registros en la etiqueta. Hecho con CSS puro (radios ocultos + `:checked`), sin JavaScript.

## 0.6.3

- El composer de la web ahora entiende los mismos comandos que la terminal, no solo capturas nuevas: `ayuda`, `listar [tipo] [período]`, `total gastos`, `balance dia`/`mes`, `backup`, `borrar <id>`, `hecha <id>`, `recordar/que recordás/olvidar`. La respuesta aparece como una burbuja de chat.
- El panel principal pasa de un feed mezclado con filtro de tipo a **secciones divididas por tipo** (Gastos, Ingresos, Tareas, Ideas, Notas), cada una con sus últimos registros. El filtro de período (hoy/mes/todo) sigue existiendo, ahora como pestañas simples.
- Se extrajeron `HELP_TEXT` y `calculate_total_expenses()` en `main.py` para que la terminal y la web muestren exactamente lo mismo sin duplicar el texto ni el cálculo.
- Se agregaron 10 pruebas del nuevo intérprete de comandos y las secciones (138 en total).

## 0.6.2

- Se corrigió un bug real que rompía la interfaz web por completo (500 en todas las páginas): los registros guardados antes de que existiera el campo `id` (de versiones viejas de Atlas) hacían explotar la plantilla al intentar armar los botones "Hecha"/"Borrar" con un id inexistente. Confirmado y verificado directamente contra una copia del archivo de datos real.
- Esos registros viejos ahora se muestran igual que en la terminal, sin botones de acción (no se pueden borrar/marcar por id porque nunca tuvieron uno).
- Se agregó una prueba que reproduce exactamente este caso (una tarea sin `id`).

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
