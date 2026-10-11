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

## Sprint 4 — Memoria local simple (terminado)

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
