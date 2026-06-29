# Atlas

Atlas es un proyecto personal y modular cuyo objetivo es ayudarme a potenciar mis capacidades.
No se busca crear solo un chatbot, sino una base gradual y mantenible para evolucionar a un asistente inteligente.

## Objetivo del Sprint 0

- Crear una estructura inicial limpia.
- Generar documentación base en español.
- Establecer un README, ROADMAP, CHANGELOG y decisiones arquitecturales.
- Preparar el proyecto para el Sprint 1 sin agregar funcionalidades avanzadas.

## Principios de diseño

- Mantener la solución simple.
- No crear módulos innecesarios.
- No agregar dependencias sin razón clara.
- Documentar en español.
- El código puede usar nombres técnicos en inglés cuando sea útil.

## Estructura inicial

```
Atlas/
+-- docs/
¦   +-- vision.md
¦   +-- architecture.md
¦   +-- decisions/
¦   ¦   +-- ADR-0001-modular-architecture.md
¦   +-- journal/
+-- src/
¦   +-- atlas/
¦       +-- __init__.py
+-- tests/
+-- data/
¦   +-- .gitkeep
+-- README.md
+-- ROADMAP.md
+-- CHANGELOG.md
+-- requirements.txt
+-- .gitignore
```

## Qué sigue después de Sprint 0

En Sprint 1 se puede comenzar a desarrollar el primer asistente funcional con una base modular y simple.
