# Contexto del proyecto Atlas

## Propósito

Atlas es un proyecto personal y técnico de largo plazo para construir un asistente
inteligente que potencie las capacidades de su creador. No busca pensar por la
persona, sino ayudarla a pensar mejor, organizar información y convertir ideas en
acciones concretas.

El proyecto también es un camino de aprendizaje práctico de Python, Git, GitHub,
arquitectura de software, inteligencia artificial, automatización, documentación y
gestión de proyectos.

## Principios

- Construir versiones pequeñas, funcionales y verificables.
- Incorporar una función únicamente si resuelve un problema real.
- Preferir la solución más simple que permita seguir creciendo.
- No defender una decisión técnica si aparece una alternativa mejor.
- Evitar dependencias e integraciones antes de que sean necesarias.
- Mantener el control humano sobre automatizaciones y datos personales.
- Evaluar las decisiones según aumenten la probabilidad de que Atlas exista,
  funcione y pueda evolucionar.

Método de trabajo:

```text
Observar -> entender -> construir -> probar -> ajustar
```

Antes de implementar una función se debe responder:

1. ¿Qué problema concreto resuelve?
2. ¿Por qué es importante ahora?
3. ¿Cuál es su versión mínima?
4. ¿Qué complejidad agrega?
5. ¿Cómo se comprobará que funciona?

## Forma de colaboración

El usuario es el fundador: define la visión, aporta necesidades reales, prueba el
sistema y toma las decisiones finales.

El asistente actúa como mentor, arquitecto técnico, compañero de desarrollo y
crítico constructivo. Debe explicar qué hace y por qué, proponer alternativas,
marcar riesgos y cuestionar decisiones cuando beneficie al proyecto. El objetivo
es que el usuario aprenda mientras construye, no hacer todo en su lugar sin que lo
entienda.

## Arquitectura y decisiones vigentes

- Python es el lenguaje inicial.
- La interfaz principal es la terminal; existe además una interfaz web local
  opcional (Flask, `src/atlas/web.py`), que reutiliza la misma lógica y corre
  solo en `127.0.0.1`.
- Los registros se almacenan inicialmente en `data/entries.jsonl`.
- `data/entries.jsonl` contiene información personal y no debe versionarse.
- SQLite puede reemplazar JSONL cuando las consultas lo justifiquen.
- Atlas será modular, pero `main.py` no se dividirá hasta que exista una necesidad
  real de mantenimiento.
- No se integrarán todavía modelos de IA, voz, Notion ni automatizaciones.
- Black es el formateador elegido para Python.
- VS Code es el entorno de desarrollo, GitHub conserva el repositorio y Obsidian
  puede utilizarse como espacio personal de notas del fundador.

## Estado funcional

### Sprint 0: fundación — terminado

Se creó el repositorio, su estructura inicial, la documentación base y el entorno
de trabajo con Git y GitHub.

### Sprint 1: captura rápida — terminado

Atlas registra notas, ideas, tareas y gastos; persiste entradas localmente y
permite listarlas o filtrarlas por tipo.

### Sprint 2: gastos estructurados — funcional

Atlas separa monto y descripción, muestra gastos con un formato legible y calcula
el total mediante `total gastos`.

### Sprint 2.1: limpieza profesional — terminado

Se formateó `main.py` con Black, se corrigieron dos bugs del parser de gastos
(mayúsculas y montos decimales ambiguos), se agregaron 19 pruebas automatizadas,
se unificó la documentación a `docs/` en UTF-8, y se limpió el historial de Git
para quitar `data/entries.jsonl`.

### Sprint 3: ingresos y balance diario — implementado, pendiente de prueba real

Atlas registra ingresos (`ingreso: 100000 uber`), los lista y calcula el balance de
hoy con `balance dia`. Falta probarlo en el día a día con datos reales.

### Sprint 3.1: corregir y borrar registros — terminado

Cada registro tiene un id estable. `borrar <id>` pide confirmación explícita
(`confirmar borrado`) antes de borrar de verdad; `hecha <id>` marca una tarea como
completada. Atlas también detecta errores de tipeo en los prefijos (sin ":", en
plural, o con typos como "gsato") y pregunta antes de guardar nada.

### Sprint 3.2: reescritura segura y balance mensual — terminado

`borrar`/`hecha` ya no pueden perder una línea dañada del archivo al reescribirlo
(antes se iba en silencio), y la escritura es atómica (archivo temporal +
reemplazo). Nuevo comando `balance mes`, con la misma lógica que `balance dia`
pero agrupando todo el mes.

### Sprint 3.3: backup — terminado

Comando `backup`: copia el archivo de datos a uno con fecha y hora, sin
sobrescribir backups anteriores. Resuelve un riesgo que ya se concretó una vez
durante el desarrollo (datos reales perdidos sin ninguna copia).

### Sprint 3.4: filtro de tiempo para `listar` — terminado

`listar hoy`, `listar mes`, `listar tareas hoy`, `listar gastos mes`, etc. Se
sacó `normalize_list_type` (quedó redundante con `parse_list_command`).

### Sprint 4: memoria local simple — revertido (ver Sprint 7)

`recordar`/`que recordás`/`olvidar` se construyeron sin un problema validado
por uso real. Tal como la nota original anticipaba, nunca se usaron en la
práctica — se sacaron por completo en el Sprint 7, reemplazados por
recordatorios con alarma de verdad.

### Sprint 5: interfaz web local — terminado

`src/atlas/web.py` (Flask) reutiliza las mismas funciones que la terminal;
cubre capturar, listar con filtros, balance y borrar/marcar tareas (con
confirmación antes de borrar). A diferencia del Sprint 4, esto no vino de un
problema de uso real sino de una decisión explícita de adelantar algo que
estaba en "Futuro lejano".

### Sprint 5.1: ajustes de uso real en la interfaz web — terminado

Esta vuelta sí vino de usarla de verdad: faltaba la detección de errores de
tipeo (todo se guardaba como nota sin preguntar), la interfaz se sentía
básica, y en el celular se veía en miniatura y ni siquiera se podía abrir.
Se agregó la misma pregunta "¿quisiste escribir...?" que la terminal
(resuelta en `/agregar/confirmar`), un rediseño tipo chat (composer
redondeado, tarjetas en vez de tabla), el `viewport` que faltaba, CSS
responsive, y el servidor ahora escucha en la red local para poder abrirse
desde el celular (sin contraseña todavía, decisión explícita).

### Sprint 5.2: composer universal y pestañas por tipo — terminado

El composer web ahora entiende los mismos comandos que la terminal (`ayuda`,
`listar`, `balance`, `backup`, `recordar`/`que recordás`/`olvidar`, etc.), no
solo capturas. Las secciones por tipo pasan de estar apiladas a ser pestañas
(CSS puro, sin JavaScript). La respuesta de `ayuda` queda colapsada por
defecto (`<details>`); el resto de las respuestas quedan abiertas.

### Sprint 6: bot de Telegram — terminado

Atlas se puede usar desde un chat de Telegram (`src/atlas/telegram_bot.py`),
sin abrir ninguna app dedicada — resuelve la fricción real de tener que
cambiar de app para anotar algo. Se evaluaron Facebook Messenger y WhatsApp
primero; se descartaron porque necesitan un servidor público expuesto a
internet y cuenta de Meta Developer. Telegram no, porque consulta
("polling") en vez de recibir llamadas. Reusa toda la lógica existente
(`handle_command`, que se movió a `main.py` para compartirla entre
terminal, web y bot); confirmaciones con botones inline reales; sin
dependencias nuevas (`urllib`). Probado en vivo con un bot real; se
encontraron y corrigieron cuatro bugs (un corte de conexión tiraba abajo
el proceso, el `/start` automático se guardaba como nota, "total de
gatos" no se reconocía como `total gastos`, y `listar gastos:` con los
dos puntos de más tampoco).

### Sprint 7: recordatorios con alarma, reemplazando la memoria — terminado

Se sacó `recordar`/`que recordás`/`olvidar` (nunca se usaron) y se
reemplazaron por `recordatorio: 19/10 08:00 texto`. Se guarda como
cualquier otro registro (no un archivo separado). Solo el bot de Telegram
puede avisar de verdad — revisa recordatorios vencidos en el mismo loop
que ya consulta mensajes, sin procesos nuevos; si no estaba corriendo a
esa hora, avisa tarde en vez de perderlo. La terminal y la web pueden
crear/listar recordatorios, pero no pueden sonar una alarma (limitación
conocida). 176 pruebas automatizadas en total.

### Sprint 8: balance diario automático — terminado

Nuevo tipo de captura `balance diario: 23:00`, que configura un aviso
automático todas las noches con el balance de hoy. Reusa el mismo cálculo
que `balance dia`. A diferencia de un recordatorio (un evento puntual), es
una configuración: una por chat, y volver a mandarlo con otra hora
actualiza la existente en vez de duplicarla. Mismo mecanismo que los
recordatorios — solo el bot de Telegram puede avisar de verdad, revisando
en el mismo loop si ya llegó la hora y todavía no se mandó hoy; si no
estaba corriendo a esa hora, avisa tarde en vez de perderlo. La terminal y
la web pueden crear la configuración, pero no pueden avisar (misma
limitación conocida que los recordatorios). 207 pruebas automatizadas en
total.

### Sprint 9: total de ingresos y balance de toda la vida — terminado

Nuevos comandos `total ingresos` (simétrico a `total gastos`) y `balance
total` (ingresos, gastos y balance sin filtrar por fecha, a diferencia de
`balance dia`/`balance mes`). Reusan la lógica existente, disponibles en
los tres canales. 218 pruebas automatizadas en total.

### Sprint 10: ajustes de uso real en la web, y arranque sin terminal — terminado

Usando la web de nuevo aparecieron olvidos reales de los Sprints 7-9:
recordatorios y balance diario sin pestaña propia, el resumen sin el
balance total nuevo, un mensaje con el nombre interno de un tipo
(`balance_diario`) a la vista. Se corrigieron los tres. Además, a pedido
explícito: rediseño visual (color por tipo en vez de un celeste genérico,
resumen como chips) y listas colapsables por pestaña (los registros ya no
se muestran directo, hay que desplegar "Ver registros"). Por separado, el
bot puede arrancar solo al iniciar sesión en Windows (Tarea Programada
oculta, con reintento), sin depender de abrir una terminal a mano — una
solución provisoria mientras sigue pendiente un equipo dedicado siempre
encendido. 222 pruebas automatizadas en total.

### Sprint 11: tres arreglos encontrados revisando los datos reales — terminado

En vez de inventar funciones, se revisó (con cuidado) el archivo de datos
real para ver qué fallaba de verdad. Aparecieron tres patrones repetidos:
`listar tarea`/`listar gasto` en singular no se reconocía (pasó 4 veces,
terminaba como nota suelta); escribir la descripción antes del monto
("gasto: nafta 12000") tampoco (pasó varias veces, mismo resultado); y dos
tareas creadas a mano ("hacer el resumen semanal", "hacer los números de
la semana") mostraban que faltaba un `balance semana`, ya que el usuario
lo estaba haciendo manualmente. Se agregaron los tres: `_LIST_TYPE_WORDS`
acepta singular y plural, `_parse_amount_entry` acepta los dos órdenes, y
`calculate_weekly_balance` sigue el mismo patrón que `balance mes`/`total`
pero compara fechas en vez de un prefijo (una semana puede cruzar dos
meses). El resumen de la web suma el chip "Esta semana". 238 pruebas
automatizadas en total.

### Sprint 12: categorías opcionales en gastos e ingresos — terminado

A pedido: poder diferenciar, dentro de una misma sección (ej. Gastos),
comida/nafta/gastos fijos/etc. Se agregó una categoría opcional al final
de la captura con `#` (`gasto: 5000 nafta #auto`, admite varias palabras),
compartida entre gasto e ingreso vía `_parse_amount_entry`. Sin categoría,
el comportamiento es idéntico al de antes. Se muestra al final del
resumen del registro en los tres canales. Filtrar/totalizar por categoría
y agrupar visualmente dentro de una pestaña quedan afuera por ahora,
pendientes de ver si hacen falta con el uso. 248 pruebas automatizadas en
total.

## Funciones actuales

```text
gasto: 15000 nafta
gasto: 15000 nafta #auto (categoría opcional)
ingreso: 100000 uber
tarea: comprar arroz
idea: crear módulo de estudio
recordatorio: 19/10 08:00 sacar la basura
balance diario: 23:00
listar
listar gastos
listar ingresos
listar tareas
listar ideas
listar notas
listar recordatorios
listar hoy
listar mes
listar <tipo> hoy
listar <tipo> mes
total gastos
total ingresos
balance dia
balance semana
balance mes
balance total
borrar <id>
hecha <id>
backup
ayuda
salir
```

## Prioridades pendientes

### Futuro cercano

- Probar Atlas con uso real, varios días (terminal, web, memoria, y ahora el bot de Telegram).
- Solución provisoria ya implementada: el bot arranca solo al iniciar sesión en Windows (Tarea Programada, oculta, ver README). Sigue dependiendo de que la computadora esté encendida; no reemplaza un equipo dedicado.
- Correr el bot en un equipo propio siempre encendido (Raspberry Pi o laptop vieja, con Linux y systemd) sigue pendiente — la solución de Windows es un parche mientras tanto, no la solución final.

### Futuro medio

- Organización de tareas y módulo de estudio.
- Reportes básicos y posible integración con Obsidian.
- Comandos de lenguaje más natural.

### Futuro lejano

- Integración con modelos de IA.
- Automatizaciones con permisos explícitos.
- Voz. El acceso móvil ya existe (interfaz web expuesta a la red local); falta contraseña/login si algún día se expone más allá de esa red.
- Agentes especializados e integraciones externas.

## Decisiones abiertas

- El nombre operativo sigue siendo Atlas; Uma permanece como alternativa futura.
- No se ha definido cuándo ni con qué proveedor integrar IA.
- La evolución de la memoria puede usar SQLite, Markdown, Obsidian u otra solución.
- Falta diseñar formalmente el sistema de permisos y confirmaciones.
- Falta decidir cómo capturar información desde el celular o mediante voz.
- La división de `main.py` ocurrirá solo cuando el crecimiento lo justifique.

## Fuente y mantenimiento

Este documento resume la conversación histórica en la que se definió Atlas. Debe
actualizarse cuando cambie una decisión importante; no debe convertirse en un
registro cronológico ni reemplazar `ROADMAP.md`, `CHANGELOG.md` o los ADR.

