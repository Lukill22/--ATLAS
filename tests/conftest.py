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
    """Redirige DATA_FILE y MEMORY_FILE a un directorio temporal durante la
    prueba. Así las pruebas de guardado y lectura nunca tocan los archivos
    reales de `data/`. Lo usan test_main.py y test_web.py.
    """

    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "entries.jsonl"
        ruta_memoria = Path(carpeta) / "memory.json"

        with patch.object(atlas_main, "DATA_FILE", ruta), patch.object(
            atlas_main, "MEMORY_FILE", ruta_memoria
        ):
            yield ruta
