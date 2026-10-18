"""Configuración compartida de pytest.

Agrega `src/` al path para poder importar `atlas.main` sin instalar el
paquete (Atlas todavía no tiene pyproject.toml/setup.py).
"""

import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

SRC_PATH = Path(__file__).resolve().parents[1] / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import atlas.main as atlas_main  # noqa: E402


@contextmanager
def archivo_temporal():
    """Redirige DATA_FILE a un directorio temporal durante la prueba. Así
    las pruebas de guardado y lectura nunca tocan el archivo real de
    `data/`. Lo usan test_main.py, test_web.py y test_telegram_bot.py.
    """

    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "entries.jsonl"

        with patch.object(atlas_main, "DATA_FILE", ruta):
            yield ruta
