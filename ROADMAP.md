# ROADMAP de Atlas

## Sprint 0  Base inicial

- Establecer estructura de proyecto.
- Crear documentacion base en español.
- Definir la primera decisio   n arquitectural (ADR).
- Preparar espacio para pruebas y modulos futuros.

## Sprint 1  Primer asistente basico

- Definir y construir un nucleo de asistente ligero.
- Permitir entrantes simples de usuario y respuestas basicas.
- Mantener la arquitectura modular para añadir memoria, automatizacion y agentes despues.
- Validar la experiencia de desarrollo con un prototipo minimo.

## Futuro

- Memoria personal.
- Asistente conversacional.
- Organizacion de archivos.
- Integracion con modelos de IA.
- Automatizaciones controladas.
- Gestion de permisos y seguridad.
## Futuro de Atlas

Esta sección reúne posibles líneas de crecimiento para Atlas. No todas estas ideas se implementarán de inmediato. Cada una deberá ganarse su lugar en un sprint según tres criterios:

1. Qué problema real resuelve.
2. Qué valor aporta al proyecto.
3. Si es el momento adecuado para construirla.

La visión de Atlas es crecer de forma gradual, evitando agregar complejidad innecesaria antes de tiempo.

---

## Futuro cercano

### 1. Mejorar la captura rápida

**Qué cumpliría:**
Permitiría que Atlas sea más útil como anotador diario, registrando ideas, gastos, tareas y notas de forma simple.

**Por qué es importante:**
La captura rápida es la primera función real de Atlas. Si esta base funciona bien, después se puede usar para memoria, organización, análisis y automatización.

---

### 2. Gastos estructurados

**Qué cumpliría:**
Permitirá que Atlas no solo guarde un gasto como texto, sino que entienda el monto y la descripción.

Ejemplo:

```text
gasto: 15000 nafta
```

Debería convertirse en:

```text
Monto: 15000
Descripción: nafta
```

**Por qué es importante:**
Es una función concreta y útil para el día a día. Ayuda a resolver un problema real de organización financiera sin construir todavía un sistema financiero complejo.

---

### 3. Comandos de consulta

**Qué cumpliría:**
Permitirá pedirle a Atlas información que ya fue guardada.

Ejemplos:

```text
listar gastos
total gastos
listar tareas
```

**Por qué es importante:**
Guardar información no alcanza. Atlas también debe poder recuperarla y mostrarla de forma útil. Esta función empieza a convertirlo en una memoria práctica.

---

### 4. Memoria local simple

**Qué cumpliría:**
Permitirá que Atlas conserve información importante de manera persistente en la computadora.

**Por qué es importante:**
La memoria es una de las bases del proyecto. Sin memoria, Atlas sería solo una herramienta momentánea. Con memoria, empieza a convertirse en un sistema que acumula contexto.

---

## Futuro medio

### 5. Asistente conversacional

**Qué cumpliría:**
Permitirá interactuar con Atlas de una manera más natural, no solo mediante comandos rígidos.

**Por qué es importante:**
Atlas no busca ser solo un programa de terminal. A largo plazo debe poder conversar, interpretar pedidos y ayudar a pensar mejor. Pero primero necesita una base sólida de datos y funciones simples.

---

### 6. Módulo de estudio

**Qué cumpliría:**
Ayudará a organizar temas de estudio, registrar avances, sugerir repasos y transformar objetivos grandes en tareas pequeñas.

**Por qué es importante:**
Uno de los objetivos principales de Atlas es potenciar el aprendizaje. Este módulo conecta directamente con la idea de usar el proyecto para crecer personal y profesionalmente.

---

### 7. Organización de archivos

**Qué cumpliría:**
Permitirá que Atlas ayude a ordenar carpetas, buscar documentos y clasificar archivos locales.

**Por qué es importante:**
Es una función alineada con el objetivo de organización. Sin embargo, debe implementarse con mucho cuidado para evitar riesgos como mover o borrar archivos importantes.

---

### 8. Integración con modelos de IA

**Qué cumpliría:**
Permitirá que Atlas use modelos como ChatGPT, Claude o modelos locales para interpretar texto, resumir información, clasificar notas y asistir en decisiones.

**Por qué es importante:**
La IA será una parte fundamental del proyecto, pero no debe ser lo primero. Antes de integrarla, Atlas necesita tener estructura, memoria y funciones propias.

---

### 9. Reportes simples

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

### 10. Automatizaciones controladas

**Qué cumpliría:**
Permitirá que Atlas ejecute acciones en la computadora, como crear carpetas, ordenar archivos o preparar documentos.

**Por qué es importante:**
Esta es una de las ideas más potentes del proyecto, pero también una de las más delicadas. Debe construirse recién cuando exista una lógica clara de permisos y seguridad.

---

### 11. Gestión de permisos y seguridad

**Qué cumpliría:**
Definirá qué puede hacer Atlas, qué no puede hacer y qué acciones necesitan autorización del usuario.

**Por qué es importante:**
Si Atlas va a interactuar con la computadora, necesita límites claros. Esta capa será clave para evitar errores, proteger datos personales y mantener el control humano.

---

### 12. Integración con herramientas externas

**Qué cumpliría:**
Permitirá conectar Atlas con herramientas como Obsidian, Notion, calendarios u otros sistemas de organización.

**Por qué es importante:**
Estas integraciones pueden hacer que Atlas sea mucho más útil, pero no deberían agregarse antes de que el sistema funcione bien por sí mismo.

---

### 13. Interacción por voz

**Qué cumpliría:**
Permitirá usar Atlas sin estar frente a la computadora, por ejemplo desde el auto o mientras se realizan otras actividades.

**Por qué es importante:**
La voz puede ser muy valiosa para capturar ideas rápidamente. Pero primero Atlas debe entender bien la lógica de texto antes de sumar una nueva forma de interacción.

---

### 14. Interfaz gráfica o aplicación propia

**Qué cumpliría:**
Permitirá usar Atlas de forma más cómoda que desde la terminal.

**Por qué es importante:**
Una interfaz visual puede mejorar mucho la experiencia, pero no debería ser prioridad hasta que las funciones principales estén claras y funcionando.

---

### 15. Sistema de agentes especializados

**Qué cumpliría:**
Permitirá dividir Atlas en agentes o módulos con responsabilidades específicas, por ejemplo:

* agente de estudio;
* agente financiero;
* agente de organización;
* agente de hábitos;
* agente de automatización.

**Por qué es importante:**
Esta idea puede hacer que Atlas crezca mucho, pero solo tiene sentido cuando ya existan suficientes funciones como para justificar esa separación.

