# Arquitectura inicial de Atlas

La arquitectura inicial está basada en un proyecto Python modular y sencillo.

Componentes clave:

- `src/atlas`: paquete principal del proyecto. La lógica pura (la que no lee ni escribe archivos) está separada en tres módulos:
  - `parsing.py`: convierte el texto que escribe el usuario en datos (montos, recordatorios, comandos, errores de tipeo).
  - `calculations.py`: balances, totales, períodos, categorías y avisos pendientes, a partir de una lista de registros.
  - `formatting.py`: cómo se muestran montos, registros y resúmenes.
- `src/atlas/main.py`: todo lo que toca el archivo de datos (guardar, leer, borrar, respaldos), los comandos y la terminal. Importa los tres módulos de arriba y vuelve a exponer sus nombres, así `web.py`, `telegram_bot.py` y las pruebas siguen importando todo desde `atlas.main`.
- `src/atlas/web.py` y `src/atlas/telegram_bot.py`: los otros dos canales de entrada. Reusan la misma lógica.
- `docs/`: documentación de visión, arquitectura y decisiones.
- `tests/`: pruebas unitarias de las funciones puras del paquete.
- `data/`: espacio para datos locales del usuario. No se versiona (ver `.gitignore`).

El enfoque es mantener cada capa separada y evitar dependencias externas innecesarias hasta que exista una necesidad clara.
