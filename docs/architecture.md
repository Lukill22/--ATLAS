# Arquitectura inicial de Atlas

La arquitectura inicial está basada en un proyecto Python modular y sencillo.

Componentes clave:

- `src/atlas`: paquete principal del proyecto. Por ahora toda la lógica vive en `main.py`; se dividirá en módulos cuando exista una razón concreta de mantenimiento (ver ADR-0001).
- `docs/`: documentación de visión, arquitectura y decisiones.
- `tests/`: pruebas unitarias de las funciones puras del paquete.
- `data/`: espacio para datos locales del usuario. No se versiona (ver `.gitignore`).

El enfoque es mantener cada capa separada y evitar dependencias externas innecesarias hasta que exista una necesidad clara.
