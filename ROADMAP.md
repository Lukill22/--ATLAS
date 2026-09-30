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

## Sprint 2.1 — Limpieza profesional (en desarrollo)

Objetivo: mejorar la calidad del proyecto sin agregar nuevas funciones.

Tareas:

- [x] Formatear `src/atlas/main.py` con Black.
- [x] Corregir los bugs del parser de gastos detectados en la revisión (mayúsculas, montos decimales ambiguos).
- [x] Agregar pruebas automatizadas para las funciones de `main.py`.
- [x] Unificar la carpeta de documentación a `docs/` (antes `Docs/`).
- [x] Limpiar el historial de Git para quitar `data/entries.jsonl`.
- [x] Revisar y limpiar `ROADMAP.md`.
- [x] Revisar y limpiar `CHANGELOG.md`.
- [ ] Verificar que Atlas siga funcionando después de todos los cambios.
- [ ] Subir los cambios a GitHub.

Criterio de terminado:

- El código está formateado correctamente y sin bugs conocidos.
- Existen pruebas automatizadas para la lógica principal.
- La documentación está ordenada y en UTF-8.
- Atlas sigue funcionando con gastos estructurados.
- GitHub refleja los cambios del sprint.

---

## Futuro de Atlas

Esta sección reúne posibles líneas de crecimiento para Atlas. No todas estas ideas se implementarán de inmediato. Cada una deberá ganarse su lugar en un sprint según tres criterios:

1. Qué problema real resuelve.
2. Qué valor aporta al proyecto.
3. Si es el momento adecuado para construirla.

La visión de Atlas es crecer de forma gradual, evitando agregar complejidad innecesaria antes de tiempo.

---

## Futuro cercano

### 1. Corregir y editar registros

**Qué cumpliría:**
Permitiría borrar o corregir una entrada guardada por error, y marcar una tarea como hecha.

**Por qué es importante:**
Hoy un error de tipeo o una tarea completada quedan para siempre. Sin esto, Atlas acumula ruido en vez de información útil.

---

### 2. Comandos de consulta con filtro de tiempo

**Qué cumpliría:**
Permitirá preguntas como `total gastos este mes` o `listar tareas de hoy`, en vez de solo totales acumulados de todo el tiempo.

**Por qué es importante:**
"Cuánto gasté este mes" es la pregunta más común de un registro de gastos personal, y hoy Atlas no la puede responder aunque ya guarda la fecha de cada entrada.

---

### 3. Memoria local simple

**Qué cumpliría:**
Permitirá que Atlas conserve información importante de manera persistente en la computadora, más allá del registro plano actual.

**Por qué es importante:**
La memoria es una de las bases del proyecto. Sin memoria, Atlas sería solo una herramienta momentánea. Con memoria, empieza a convertirse en un sistema que acumula contexto.

---

## Futuro medio

### 4. Asistente conversacional

**Qué cumpliría:**
Permitirá interactuar con Atlas de una manera más natural, no solo mediante comandos rígidos.

**Por qué es importante:**
Atlas no busca ser solo un programa de terminal. A largo plazo debe poder conversar, interpretar pedidos y ayudar a pensar mejor. Pero primero necesita una base sólida de datos y funciones simples.

---

### 5. Módulo de estudio

**Qué cumpliría:**
Ayudará a organizar temas de estudio, registrar avances, sugerir repasos y transformar objetivos grandes en tareas pequeñas.

**Por qué es importante:**
Uno de los objetivos principales de Atlas es potenciar el aprendizaje. Este módulo conecta directamente con la idea de usar el proyecto para crecer personal y profesionalmente.

---

### 6. Organización de archivos

**Qué cumpliría:**
Permitirá que Atlas ayude a ordenar carpetas, buscar documentos y clasificar archivos locales.

**Por qué es importante:**
Es una función alineada con el objetivo de organización. Sin embargo, debe implementarse con mucho cuidado para evitar riesgos como mover o borrar archivos importantes.

---

### 7. Integración con modelos de IA

**Qué cumpliría:**
Permitirá que Atlas use modelos como ChatGPT, Claude o modelos locales para interpretar texto, resumir información, clasificar notas y asistir en decisiones.

**Por qué es importante:**
La IA será una parte fundamental del proyecto, pero no debe ser lo primero. Antes de integrarla, Atlas necesita tener estructura, memoria y funciones propias.

---

### 8. Reportes simples

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

### 9. Automatizaciones controladas

**Qué cumpliría:**
Permitirá que Atlas ejecute acciones en la computadora, como crear carpetas, ordenar archivos o preparar documentos.

**Por qué es importante:**
Esta es una de las ideas más potentes del proyecto, pero también una de las más delicadas. Debe construirse recién cuando exista una lógica clara de permisos y seguridad.

---

### 10. Gestión de permisos y seguridad

**Qué cumpliría:**
Definirá qué puede hacer Atlas, qué no puede hacer y qué acciones necesitan autorización del usuario.

**Por qué es importante:**
Si Atlas va a interactuar con la computadora, necesita límites claros. Esta capa será clave para evitar errores, proteger datos personales y mantener el control humano.

---

### 11. Integración con herramientas externas

**Qué cumpliría:**
Permitirá conectar Atlas con herramientas como Obsidian, Notion, calendarios u otros sistemas de organización.

**Por qué es importante:**
Estas integraciones pueden hacer que Atlas sea mucho más útil, pero no deberían agregarse antes de que el sistema funcione bien por sí mismo.

---

### 12. Interacción por voz

**Qué cumpliría:**
Permitirá usar Atlas sin estar frente a la computadora, por ejemplo desde el auto o mientras se realizan otras actividades.

**Por qué es importante:**
La voz puede ser muy valiosa para capturar ideas rápidamente. Pero primero Atlas debe entender bien la lógica de texto antes de sumar una nueva forma de interacción.

---

### 13. Interfaz gráfica o aplicación propia

**Qué cumpliría:**
Permitirá usar Atlas de forma más cómoda que desde la terminal.

**Por qué es importante:**
Una interfaz visual puede mejorar mucho la experiencia, pero no debería ser prioridad hasta que las funciones principales estén claras y funcionando.

---

### 14. Sistema de agentes especializados

**Qué cumpliría:**
Permitirá dividir Atlas en agentes o módulos con responsabilidades específicas, por ejemplo:

* agente de estudio;
* agente financiero;
* agente de organización;
* agente de hábitos;
* agente de automatización.

**Por qué es importante:**
Esta idea puede hacer que Atlas crezca mucho, pero solo tiene sentido cuando ya existan suficientes funciones como para justificar esa separación.
