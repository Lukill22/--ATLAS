# ADR 0001: Arquitectura modular inicial

## Estado

Se necesita una base limpia para construir un asistente personal modular.

## Decisión

Adoptar una arquitectura modular mínima con un paquete Python principal (`src/atlas`) y documentación clara en `docs/`.

## Razonamiento

- Facilita la evolución del proyecto con nuevos módulos.
- Evita agrupar funcionalidades avanzadas en un solo componente.
- Permite comenzar con un prototipo ligero sin dependencias externas.

## Consecuencias

- Los nuevos desarrollos deberán incluir documentación y pruebas.
- El primer asistente debe construirse sobre este paquete base.
- No se implementarán memorias, agentes o integraciones de IA en Sprint 0.
