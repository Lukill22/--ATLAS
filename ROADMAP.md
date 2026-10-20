# ROADMAP de Atlas

## Sprint 0 — Base inicial (terminado)

- Establecer estructura de proyecto.
- Crear documentación base en español.
- Definir la primera decisión arquitectural (ADR).
- Preparar espacio para pruebas y módulos futuros.

## Sprint 1 — Primer asistente básico (terminado)

- Definir y construir un núcleo de asistente ligero.
- Permitir entradas simples de usuario y respuestas básicas.
- Mantener la arquitectura modular para añadir memoria, automatización y agentes después.
- Validar la experiencia de desarrollo con un prototipo mínimo.

## Sprint 2 — Gastos estructurados (terminado)

- Separar monto y descripción al registrar un gasto (`gasto: 15000 nafta`).
- Agregar el comando `total gastos`.
- Mostrar los gastos con un formato legible ($15.000 en vez del texto crudo).

## Sprint 2.1 — Limpieza profesional (terminado)

Objetivo: mejorar la calidad del proyecto sin agregar nuevas funciones.

Tareas:

- [x] Formatear `src/atlas/main.py` con Black.
- [x] Corregir los bugs del parser de gastos detectados en la revisión (mayúsculas, montos decimales ambiguos).
- [x] Agregar pruebas automatizadas para las funciones de `main.py`.
- [x] Unificar la carpeta de documentación a `docs/` (antes `Docs/`).
- [x] Limpiar el historial de Git para quitar `data/entries.jsonl`.
- [x] Revisar y limpiar `ROADMAP.md`.
- [x] Revisar y limpiar `CHANGELOG.md`.
- [x] Verificar que Atlas siga funcionando después de todos los cambios.
- [x] Subir los cambios a GitHub.

Criterio de terminado:

- El código está formateado correctamente y sin bugs conocidos.
- Existen pruebas automatizadas para la lógica principal.
- La documentación está ordenada y en UTF-8.
- Atlas sigue funcionando con gastos estructurados.
- GitHub refleja los cambios del sprint.

## Sprint 3 — Ingresos y balance diario (implementado, pendiente de prueba real)

Problema que resuelve: Atlas registra gastos, pero no permite saber cuánto se ganó
(Uber y trabajos extra) ni cuánto quedó en el día.

Versión mínima:

- [x] Registrar ingresos: `ingreso: 100000 uber`.
- [x] Listar ingresos: `listar ingresos`.
- [x] Balance de hoy: `balance dia`.
- [x] Pruebas automatizadas para lo nuevo (incluye guardado y lectura con archivo temporal).
- [ ] Probarlo en el día a día con datos reales y ajustar.

Fuera de alcance (a propósito): balance semanal o mensual, editar o borrar registros,
decimales y categorías.

## Sprint 3.1 — Corregir y borrar registros (terminado)

Problema que resuelve: un error de tipeo o una tarea ya hecha quedaban para
siempre, sin forma de sacarlos ni de marcarlos.

Versión mínima:

- [x] Id estable por registro (`listar` ya no numera 1..10 de nuevo cada vez).
- [x] `borrar <id>`, con confirmación explícita (`confirmar borrado`) antes de borrar de verdad.
- [x] `hecha <id>` para marcar una tarea como completada.
- [x] Detección de errores de tipeo en los prefijos (`gasto` sin ":", `gastos:` en plural, e incluso typos como `gsato`), con confirmación antes de guardar.
- [x] Pruebas automatizadas para todo lo anterior.

Fuera de alcance (a propósito): editar el texto libre de un registro ya guardado
(hoy la única forma de "corregir" un texto es borrarlo y volver a crearlo).

## Sprint 3.2 — Reescritura segura y balance mensual (terminado)

Problema que resuelve: `borrar`/`hecha` reescribían el archivo entero a partir de
`load_entries()`, que descarta cualquier línea que no pueda leerse como JSON — un
borrado podía llevarse puesto, en silencio, una línea dañada sin relación alguna.
Además, `total gastos`/`balance dia` no tenían forma de responder "¿cuánto gasté
este mes?".

Versión mínima:

- [x] `_read_lines`/`_write_lines` operan sobre el archivo línea por línea, conservando intactas las que Atlas no puede interpretar.
- [x] La escritura es atómica (archivo temporal + reemplazo): si algo falla a mitad de camino, el archivo original queda intacto.
- [x] `balance mes`: igual que `balance dia`, pero agrupa todo el mes actual.
- [x] Pruebas automatizadas para ambas cosas.

## Sprint 3.3 — Backup (terminado)

Problema que resuelve: no había ninguna forma de recuperar un dato borrado por
error (ni un comando del usuario, ni un accidente externo). Esto no es
hipotético: durante el desarrollo se perdieron registros reales por un `rm`
mal pensado, sin ningún backup para recuperarlos.

Versión mínima:

- [x] Comando `backup`: copia `data/entries.jsonl` a un archivo con fecha y hora, sin tocar el original.
- [x] Nunca sobrescribe un backup anterior (cada uno con su propio timestamp).
- [x] Los backups quedan afuera de Git, igual que el archivo de datos real.
- [x] Pruebas automatizadas.

Fuera de alcance (a propósito): backups automáticos/periódicos, límite de
cantidad de backups viejos, restaurar desde un backup (hoy se restaura a mano
copiando el archivo).

## Sprint 3.4 — Filtro de tiempo para `listar` (terminado)

Problema que resuelve: `listar tareas`/`listar notas` siempre mezclaba todo lo
guardado desde el principio; no había forma de ver solo lo de hoy o lo del mes,
aunque `balance mes` ya probó que la idea funciona para los montos.

Versión mínima:

- [x] `listar hoy` / `listar mes`: filtran por período sin filtrar por tipo.
- [x] `listar <tipo> hoy` / `listar <tipo> mes`: combinan ambos filtros (ej. `listar tareas hoy`).
- [x] Se sacó `normalize_list_type`, que quedó redundante.
- [x] Pruebas automatizadas.

Fuera de alcance (a propósito): "esta semana" (necesita calcular el inicio de
semana, no es solo un prefijo de fecha como "hoy"/"mes").

## Sprint 4 — Memoria local simple (revertido, ver Sprint 7)

Problema que resuelve: Atlas solo tenía un registro cronológico
(`entries.jsonl`). No había forma de guardar un hecho que se actualiza con el
tiempo ("mi presupuesto mensual es X") sin que quedara enterrado entre notas y
gastos, ni de corregirlo sin buscar y borrar la entrada vieja.

Nota: este sprint no tenía un problema validado por uso real todavía (a
diferencia de los anteriores) — se construyó con la mejor interpretación
disponible de "memoria", no a partir de una necesidad ya confirmada. Vale la
pena revisarlo después de usarlo.

Versión mínima:

- [x] `recordar <algo>: <valor>`: guarda o actualiza un hecho en `data/memory.json` (separado de `entries.jsonl` a propósito: es información que se pisa, no un registro que crece).
- [x] `que recordas`: lista todo lo guardado.
- [x] `olvidar <algo>`: borra un hecho puntual.
- [x] Escritura atómica, igual que el resto de los archivos de datos.
- [x] Pruebas automatizadas.

Fuera de alcance (a propósito): que Atlas use estos hechos automáticamente
(por ejemplo, avisar si un gasto supera el presupuesto recordado) — eso ya
empieza a ser lógica de asistente, no solo de almacenamiento.

**Actualización — Sprint 7:** la nota de arriba se cumplió. Después de usar
Atlas un tiempo, nunca se usó `recordar`/`olvidar` para nada real — lo que
el usuario quería era un recordatorio con alarma, no un dato fijo. Se sacó
por completo (ver Sprint 7) en vez de mantenerlo sin uso. Queda documentado
acá como ejemplo de una función construida sin validar primero, y lo que
pasó después: exactamente lo que la nota original anticipaba.

## Sprint 5 — Interfaz web local (terminado)

Problema que resuelve: usar Atlas por comandos de texto exactos es poco
visual. Esto no venía de un problema de uso real todavía (como el Sprint 4) —
fue una decisión consciente de adelantar algo que estaba anotado como "Futuro
lejano", a pedido explícito y sabiendo que se pausaban funciones nuevas para
probar Atlas en uso real.

Versión mínima:

- [x] Página local (`src/atlas/web.py`, Flask) que reutiliza las mismas funciones que la terminal (`save_entry`, `load_entries`, `calculate_balance`, etc.) — no duplica lógica.
- [x] Capturar, listar con filtro de tipo/período, balance de hoy y del mes.
- [x] Borrar con página de confirmación intermedia (un GET nunca borra; hace falta el POST de esa página).
- [x] Marcar tareas como hechas.
- [x] Corre solo en `127.0.0.1`, nunca expuesta a la red.
- [x] `format_entry_summary()` extraída de `show_entries()` para que la terminal y la web no se desincronicen.
- [x] Pruebas automatizadas (rutas Flask con el test client).

Fuera de alcance (a propósito): la detección de errores de tipeo con
confirmación, `recordar`/`que recordás`/`olvidar`, `backup`, acceso desde el
celular en la misma red (necesitaría pensar autenticación primero).

## Sprint 5.1 — Ajustes de uso real en la interfaz web (terminado)

Problema que resuelve: a diferencia del Sprint 5 (que fue una decisión
adelantada, no un problema validado), esta vuelta sí vino de usarla de
verdad: todo se guardaba como nota sin preguntar nada (la detección de
typos no existía en la web), la interfaz se sentía básica, y en el celular
se veía en miniatura — y además no se podía ni abrir desde el celular.

Versión mínima:

- [x] Detección de errores de tipeo con la misma pregunta "¿quisiste escribir...?" que la terminal, resuelta en `/agregar/confirmar` (sin guardar nada hasta confirmar).
- [x] Rediseño del composer como un chat (cajón redondeado + botón de enviar, sin la palabra "Guardar") y el listado como tarjetas en vez de tabla.
- [x] `<meta name="viewport">` en las plantillas (faltaba; el celular mostraba todo en miniatura).
- [x] CSS responsive para pantallas chicas.
- [x] El servidor escucha en la red local (`0.0.0.0`), no solo en `127.0.0.1`, e imprime la URL para el celular al arrancar — decisión explícita, sin contraseña todavía.
- [x] Pruebas automatizadas del nuevo flujo de confirmación.
- [x] Bug real encontrado al probarla con datos reales: registros guardados antes de que existiera el `id` rompían toda la página (500) al armar los botones de acción. Corregido; esos registros viejos ahora se muestran sin botones, igual que en la terminal.

Fuera de alcance (a propósito): contraseña o login (necesario si esto se
expone más allá de la red de casa), acceso desde fuera de la red local.

## Sprint 5.2 — Composer como comando universal y pestañas por tipo (terminado)

Problema que resuelve: usándola de verdad aparecieron dos límites más —
escribir `ayuda` (o cualquier comando que no fuera una captura) se guardaba
como nota en vez de hacer lo que hace en la terminal, y tener las 5
secciones apiladas una debajo de la otra se sentía desordenado.

Versión mínima:

- [x] El composer entiende los mismos comandos que la terminal: `ayuda`, `listar [tipo] [período]`, `total gastos`, `balance dia`/`mes`, `backup`, `borrar <id>`, `hecha <id>`, `recordar`/`que recordás`/`olvidar`. La respuesta aparece como una burbuja.
- [x] `HELP_TEXT` y `calculate_total_expenses()` extraídos en `main.py` para que la terminal y la web nunca muestren cosas distintas.
- [x] Las secciones (Gastos, Ingresos, Tareas, Ideas, Notas) pasan de estar apiladas a ser pestañas (una visible a la vez, con la cantidad en la etiqueta), con CSS puro, sin JavaScript.
- [x] Pruebas automatizadas de los comandos nuevos y de que cada registro aparece en la pestaña correcta.
- [x] La respuesta de `ayuda` (larga) queda colapsada por defecto (`<details>`, sin JavaScript); el resto de las respuestas (balance, listar) siguen abiertas.

## Sprint 6 — Bot de Telegram (terminado)

Problema que resuelve: abrir una app dedicada (Termux, el navegador) cada
vez que se quiere anotar algo es suficiente fricción como para no hacerlo.
El problema real no era "botones vs. escribir" sino el costo de cambiar de
app — hacía falta capturar desde una que ya se usa todo el día.

Se evaluó Facebook Messenger y WhatsApp primero; ambos necesitan un
servidor público expuesto a internet (webhook) y cuenta de Meta Developer.
Telegram no: su bot consulta a Telegram ("long polling") en vez de que
Telegram le avise a un servidor, así que no hace falta exponer nada a la
red.

Versión mínima:

- [x] `src/atlas/telegram_bot.py`: reusa `save_entry`, `detect_entry_type`, `handle_command`, etc. — ninguna lógica nueva, solo un canal de entrada nuevo.
- [x] Entiende captura (`gasto:`, `tarea:`, etc.), todos los comandos (`ayuda`, `listar`, `balance`, `backup`, `recordar`/`que recordás`/`olvidar`), y pide confirmación de typos y de borrado con botones inline reales.
- [x] Sin dependencias nuevas: la API de Telegram se habla con `urllib` (librería estándar).
- [x] Token en `ATLAS_TELEGRAM_TOKEN`, nunca versionado.
- [x] `handle_command()` se extrajo de `web.py` a `main.py` para compartirla entre los tres canales (terminal, web, bot).
- [x] Pruebas automatizadas mockeando el envío a Telegram.
- [x] Bug real encontrado probándolo en vivo: un corte de conexión (`ConnectionResetError`) no estaba absorbido y tiraba abajo todo el bot. Corregido, con una espera antes de reintentar.
- [x] El `/start` automático de Telegram ya no se guarda como nota; el bot saluda en su lugar.
- [x] `HELP_TEXT` (compartido con terminal y web) se achicó: sin el bloque de "cómo capturar", enfocado en qué se puede consultar.
- [x] Caso real reportado: "total de gatos" (typo + palabra de más) se guardaba como nota. Los comandos fijos de solo lectura (`total gastos`, `balance dia`/`mes`, `ayuda`, `backup`, `que recordás`) ahora toleran esto, sin confundirse con `listar` aunque comparta palabras.
- [x] Otro caso real: `listar gastos:` (con los dos puntos de más, un hábito lógico porque el resto de Atlas sí usa `:`) también se guardaba como nota. Tolerado para `listar` y para cualquier comando fijo, sin afectar `recordar <algo>: <valor>`.

Fuera de alcance (a propósito): correrlo como servicio que arranque solo
(systemd, Termux:Boot); por ahora se arranca a mano cuando se lo quiere
usar. WhatsApp sigue descartado por la complejidad de Meta Developer.

## Sprint 7 — Recordatorios con alarma, reemplazando la memoria (terminado)

Problema que resuelve: lo que el usuario quería de `recordar` en realidad
era un recordatorio con alarma para una tarea o evento futuro, no un dato
fijo para consultar. La memoria (Sprint 4) nunca se usó en la práctica —
confirmado después de usar Atlas un tiempo, tal como esa misma nota
anticipaba. Se sacó por completo en vez de mantener algo sin uso.

Versión mínima:

- [x] `recordatorio: 19/10 08:00 sacar la basura`: nuevo tipo de captura, fecha y hora en formato fijo (sin adivinar).
- [x] Se guarda como cualquier otro registro en `entries.jsonl` (id, se puede listar y borrar) — no un archivo separado como la memoria vieja.
- [x] Solo el bot de Telegram puede avisar de verdad: revisa recordatorios vencidos en el mismo loop que ya consulta mensajes, sin hilos ni procesos nuevos. Si el bot no estaba corriendo, avisa tarde en vez de perderlo.
- [x] La terminal y la web pueden crear/listar recordatorios, pero no pueden avisar (limitación conocida, documentada).
- [x] Se sacaron `recordar`/`que recordás`/`olvidar` y `data/memory.json` por completo.
- [x] Pruebas automatizadas (parseo de fecha, detección de vencidos, aviso con y sin chat_id).

Fuera de alcance (a propósito): recordatorios repetitivos (todos los días,
cada semana), avisar por web/terminal de alguna forma.

## Sprint 8 — Balance diario automático (terminado)

Problema que resuelve: después de usar los recordatorios, surgió un pedido
natural parecido pero distinto — no un evento puntual, sino un aviso que se
repite todas las noches con el balance de hoy, sin tener que pedirlo. Los
recordatorios (Sprint 7) explícitamente dejaron "recordatorios repetitivos"
fuera de alcance; esto no generaliza esa idea, resuelve un caso puntual y
acotado (balance, una vez por día) con su propio mecanismo más simple.

Versión mínima:

- [x] `balance diario: 23:00`: nuevo tipo de captura que configura la hora del aviso automático.
- [x] Se guarda en `entries.jsonl` como un registro más, pero es una configuración (una por chat): volver a mandarlo con otra hora actualiza el registro existente en vez de duplicarlo.
- [x] Solo el bot de Telegram puede avisar de verdad: en el mismo loop que ya revisa mensajes y recordatorios, también revisa si ya llegó la hora y todavía no se mandó hoy. Si el bot no estaba corriendo a esa hora, avisa tarde en vez de perderlo.
- [x] La terminal y la web pueden crear la configuración, pero no pueden avisar (misma limitación conocida que los recordatorios).
- [x] Reusa `calculate_balance`/`format_balance_summary`, ya usados por `balance dia`.
- [x] Pruebas automatizadas (parseo de hora, actualización en vez de duplicado, detección de "ya toca avisar", aviso con y sin chat_id).

Fuera de alcance (a propósito): elegir qué incluye el mensaje (hoy es
siempre "balance de hoy", igual que `balance dia`), otros avisos repetitivos
de propósito general, horarios distintos por día de la semana.

## Sprint 9 — Total de ingresos y balance de toda la vida (terminado)

Problema que resuelve: `total gastos` existía desde el Sprint 2, pero nunca
se agregó su equivalente para ingresos; y `balance dia`/`balance mes` no
tenían forma de responder "¿cómo estoy en total, desde que empecé a usar
Atlas?" sin sumarlo a mano.

Versión mínima:

- [x] `total ingresos`: igual que `total gastos`, pero para ingresos.
- [x] `balance total`: ingresos, gastos y balance sin filtrar por fecha, reusando `_sum_income_and_expenses` con un prefijo vacío.
- [x] Disponible en los tres canales (terminal, web, bot), con la misma tolerancia a typos que el resto de los comandos fijos.
- [x] Pruebas automatizadas.

## Sprint 10 — Ajustes de uso real en la web, y arranque sin depender de la terminal (terminado)

Problema que resuelve: usando la web de nuevo con los tipos agregados en
los Sprints 7-9, aparecieron olvidos reales — recordatorios y balance
diario no tenían pestaña propia, el resumen no mostraba el balance total
nuevo, un mensaje mostraba el nombre interno de un tipo con guion bajo. Y
por separado: pedido explícito de dejar de abrir una terminal a mano cada
vez que se quiere usar el bot, y de que la interfaz se sienta menos
genérica.

Versión mínima:

- [x] Pestañas de Recordatorios y Balance diario en la web (antes invisibles fuera de `listar`).
- [x] Rediseño visual: color de acento por tipo, marca simple, resumen como chips en vez de texto plano.
- [x] Los registros de cada pestaña quedan colapsados detrás de "Ver registros" en vez de mostrarse directo.
- [x] Chip "Siempre" (balance total) en el resumen, que se había quedado afuera del Sprint 9.
- [x] Corregido el mensaje "Guardado como balance_diario." (guion bajo visible).
- [x] El bot puede arrancar solo al iniciar sesión en Windows (Tarea Programada oculta, con reintento), sin escribir el token en ningún archivo.
- [x] Pruebas automatizadas para los cambios de la web.

Fuera de alcance (a propósito): equipo dedicado siempre encendido
(Raspberry Pi/laptop vieja, sigue pendiente — esto es un parche
mientras tanto), autenticación/login para la web.

## Sprint 11 — Tres arreglos encontrados revisando los datos reales (terminado)

Problema que resuelve: en vez de seguir agregando funciones nuevas sin un
problema validado, se revisó el archivo de datos real (con cuidado, sin
tocar nada) buscando patrones repetidos de uso real que no funcionaran
como se esperaba. Aparecieron tres.

Versión mínima:

- [x] `listar tarea`/`listar gasto` (singular) — pasó 4 veces en el historial real, siempre terminó como nota suelta.
- [x] `gasto:`/`ingreso:` aceptan la descripción antes del monto ("gasto: nafta 12000") — pasó varias veces, es como se habla en la vida real.
- [x] `balance semana` (lunes a domingo) en los tres canales, más el chip "Esta semana" en la web — motivado por dos tareas reales que el usuario se creó a sí mismo para acordarse de calcularlo a mano.
- [x] Pruebas automatizadas para los tres.

Fuera de alcance (a propósito): adivinar el tipo cuando no hay ningún
prefijo (`gasto:`/`ingreso:`) presente — eso ya no es tolerar un error de
tipeo, es adivinar sin ninguna señal, y rompería la regla explícita del
propio usuario ("lo que no tenga la indicación, va a notas").

## Sprint 12 — Categorías opcionales en gastos e ingresos (terminado)

Problema que resuelve: dentro de una misma sección (ej. Gastos) no había
forma de diferenciar comida, nafta, gastos fijos, etc. — todo se veía
igual salvo por la descripción libre.

Versión mínima:

- [x] Categoría opcional al final de la captura, con `#` (ej. `gasto: 5000 nafta #auto`), compartida entre gasto e ingreso.
- [x] Puede tener varias palabras (`#gastos fijos`).
- [x] Si no se pone categoría, el comportamiento es exactamente el mismo que antes (no rompe nada existente).
- [x] Se muestra al final del resumen del registro en los tres canales.
- [x] Pruebas automatizadas.

Fuera de alcance (a propósito, por ahora): filtrar/totalizar por
categoría (ej. `listar gastos #auto`, `total gastos #auto`) — se agrega
después si usarla un tiempo muestra que hace falta. Agrupar visualmente
por categoría dentro de una pestaña de la web (hoy se distingue por el
tag al final de cada tarjeta, no con subtítulos separados).

**Actualización:** el usuario probó esto y no quedó conforme con tener
que escribir `#categoria` cada vez — lo que quería era que Atlas
categorice solo después de la primera vez. Ver Sprint 13.

## Sprint 13 — Categorización automática por repetición (terminado)

Problema que resuelve: el Sprint 12 dejó la categoría como algo que hay
que escribir cada vez; lo que el usuario pedía de verdad era no tener que
repetirla. Sin usar IA ni listas de palabras predefinidas (esas palabras
las elige el usuario, no Atlas).

Versión mínima:

- [x] Después de etiquetar una palabra con `#categoria` una sola vez, los próximos gastos/ingresos que mencionen esa palabra se categorizan solos.
- [x] Separado por tipo: gasto e ingreso nunca se contaminan entre sí (varias fuentes de ingreso quedan cubiertas sin trabajo extra).
- [x] Palabras de relleno ("en", "el", "la", "de", etc.) no cuentan como señal — evita categorizar mal solo porque dos descripciones comparten una preposición.
- [x] La categorización explícita con `#categoria` sigue teniendo prioridad sobre la inferida.
- [x] El mensaje de confirmación ("Guardado como gasto...") muestra la categoría cuando hay una, para que se note cuándo Atlas la detectó sola. De paso, se unificó en una sola función compartida por los tres canales (antes solo la web lo mostraba, y a veces con el nombre interno del tipo con guion bajo).
- [x] Pruebas automatizadas.

Fuera de alcance (a propósito, por ahora): editar o corregir una
categorización que salió mal (hoy se corrige escribiendo `#categoria`
de nuevo en un registro nuevo, no hay forma de recategorizar uno viejo).

---

## Futuro de Atlas

Esta sección reúne posibles líneas de crecimiento para Atlas. No todas estas ideas se implementarán de inmediato. Cada una deberá ganarse su lugar en un sprint según tres criterios:

1. Qué problema real resuelve.
2. Qué valor aporta al proyecto.
3. Si es el momento adecuado para construirla.

La visión de Atlas es crecer de forma gradual, evitando agregar complejidad innecesaria antes de tiempo.

---

## Futuro cercano

No queda ninguna función anotada todavía. Lo único pendiente es usar Atlas con
datos reales y dejar que el próximo problema real aparezca solo, en vez de
adivinarlo (ver Sprint 4 para la excepción que confirma esta regla).

---

## Futuro medio

### 1. Asistente conversacional

**Qué cumpliría:**
Permitirá interactuar con Atlas de una manera más natural, no solo mediante comandos rígidos.

**Por qué es importante:**
Atlas no busca ser solo un programa de terminal. A largo plazo debe poder conversar, interpretar pedidos y ayudar a pensar mejor. Pero primero necesita una base sólida de datos y funciones simples.

---

### 2. Módulo de estudio

**Qué cumpliría:**
Ayudará a organizar temas de estudio, registrar avances, sugerir repasos y transformar objetivos grandes en tareas pequeñas.

**Por qué es importante:**
Uno de los objetivos principales de Atlas es potenciar el aprendizaje. Este módulo conecta directamente con la idea de usar el proyecto para crecer personal y profesionalmente.

---

### 3. Organización de archivos

**Qué cumpliría:**
Permitirá que Atlas ayude a ordenar carpetas, buscar documentos y clasificar archivos locales.

**Por qué es importante:**
Es una función alineada con el objetivo de organización. Sin embargo, debe implementarse con mucho cuidado para evitar riesgos como mover o borrar archivos importantes.

---

### 4. Integración con modelos de IA

**Qué cumpliría:**
Permitirá que Atlas use modelos como ChatGPT, Claude o modelos locales para interpretar texto, resumir información, clasificar notas y asistir en decisiones.

**Por qué es importante:**
La IA será una parte fundamental del proyecto, pero no debe ser lo primero. Antes de integrarla, Atlas necesita tener estructura, memoria y funciones propias.

---

### 5. Reportes simples

**Qué cumpliría:**
Permitirá generar resúmenes sobre gastos, tareas, ideas o hábitos registrados.

Ejemplo:

```text
Resumen del día:
- Gastos registrados: 3
- Total gastado: $25.000
- Tareas pendientes: 2
- Ideas nuevas: 1
```

**Por qué es importante:**
Los reportes convierten datos sueltos en información útil. Esta función ayudaría a que Atlas no solo guarde cosas, sino que ayude a entenderlas.

---

## Futuro lejano

### 6. Automatizaciones controladas

**Qué cumpliría:**
Permitirá que Atlas ejecute acciones en la computadora, como crear carpetas, ordenar archivos o preparar documentos.

**Por qué es importante:**
Esta es una de las ideas más potentes del proyecto, pero también una de las más delicadas. Debe construirse recién cuando exista una lógica clara de permisos y seguridad.

---

### 7. Gestión de permisos y seguridad

**Qué cumpliría:**
Definirá qué puede hacer Atlas, qué no puede hacer y qué acciones necesitan autorización del usuario.

**Por qué es importante:**
Si Atlas va a interactuar con la computadora, necesita límites claros. Esta capa será clave para evitar errores, proteger datos personales y mantener el control humano.

---

### 8. Integración con herramientas externas

**Qué cumpliría:**
Permitirá conectar Atlas con herramientas como Obsidian, Notion, calendarios u otros sistemas de organización.

**Por qué es importante:**
Estas integraciones pueden hacer que Atlas sea mucho más útil, pero no deberían agregarse antes de que el sistema funcione bien por sí mismo.

---

### 9. Interacción por voz

**Qué cumpliría:**
Permitirá usar Atlas sin estar frente a la computadora, por ejemplo desde el auto o mientras se realizan otras actividades.

**Por qué es importante:**
La voz puede ser muy valiosa para capturar ideas rápidamente. Pero primero Atlas debe entender bien la lógica de texto antes de sumar una nueva forma de interacción.

---

### 10. Sistema de agentes especializados

**Qué cumpliría:**
Permitirá dividir Atlas en agentes o módulos con responsabilidades específicas, por ejemplo:

* agente de estudio;
* agente financiero;
* agente de organización;
* agente de hábitos;
* agente de automatización.

**Por qué es importante:**
Esta idea puede hacer que Atlas crezca mucho, pero solo tiene sentido cuando ya existan suficientes funciones como para justificar esa separación.
