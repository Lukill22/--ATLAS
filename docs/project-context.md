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
- La interfaz actual funciona en la terminal.
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
para quitar `data/entries.jsonl`. El próximo paso es definir el alcance del
Sprint 3.

## Funciones actuales

```text
gasto: 15000 nafta
tarea: comprar arroz
idea: crear módulo de estudio
listar
listar gastos
listar tareas
listar ideas
listar notas
total gastos
ayuda
salir
```

## Prioridades pendientes

### Futuro cercano

- Terminar la limpieza de `ROADMAP.md`, `CHANGELOG.md` y demás documentación.
- Agregar pruebas automatizadas y verificar el comportamiento existente.
- Definir oficialmente el Sprint 3.
- Evaluar ingresos, balance diario y mejoras en el registro de gastos.

### Futuro medio

- Memoria local simple y resúmenes diarios.
- Organización de tareas y módulo de estudio.
- Reportes básicos y posible integración con Obsidian.
- Comandos de lenguaje más natural.

### Futuro lejano

- Integración con modelos de IA.
- Automatizaciones con permisos explícitos.
- Voz e interfaz gráfica o móvil.
- Agentes especializados e integraciones externas.

## Decisiones abiertas

- El nombre operativo sigue siendo Atlas; Uma permanece como alternativa futura.
- No se ha elegido el alcance del Sprint 3.
- No se ha definido cuándo ni con qué proveedor integrar IA.
- La evolución de la memoria puede usar SQLite, Markdown, Obsidian u otra solución.
- Falta diseñar formalmente el sistema de permisos y confirmaciones.
- Falta decidir cómo capturar información desde el celular o mediante voz.
- La división de `main.py` ocurrirá solo cuando el crecimiento lo justifique.

## Fuente y mantenimiento

Este documento resume la conversación histórica en la que se definió Atlas. Debe
actualizarse cuando cambie una decisión importante; no debe convertirse en un
registro cronológico ni reemplazar `ROADMAP.md`, `CHANGELOG.md` o los ADR.

