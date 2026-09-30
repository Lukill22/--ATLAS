"""Configuración compartida de pytest.

Agrega `src/` al path para poder importar `atlas.main` sin instalar el
paquete (Atlas todavía no tiene pyproject.toml/setup.py).
"""

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
