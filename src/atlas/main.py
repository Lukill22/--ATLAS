from datetime import datetime
from pathlib import Path
import json


# Ruta del archivo donde Atlas guarda los registros.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_ROOT / "data" / "entries.jsonl"


def save_entry(entry_type: str, text: str) -> dict:
    """Crea y guarda un registro nuevo."""

    entry = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "type": entry_type,
        "text": text,
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with DATA_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def load_entries() -> list[dict]:
    """Lee todos los registros guardados."""

    if not DATA_FILE.exists():
        return []

    entries = []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                entry = json.loads(line)
                entries.append(entry)

            except json.JSONDecodeError:
                print(
                    f"Atlas: No pude leer el registro "
                    f"de la línea {line_number}."
                )

    return entries


def detect_entry_type(text: str) -> str:
    """Detecta el tipo de registro según el comienzo del texto."""

    lowered_text = text.lower()

    if lowered_text.startswith("gasto:"):
        return "gasto"

    if lowered_text.startswith("tarea:"):
        return "tarea"

    if lowered_text.startswith("idea:"):
        return "idea"

    return "nota"


def normalize_list_type(command: str) -> str | None:
    """Convierte el comando escrito al tipo de registro interno."""

    filters = {
        "listar gastos": "gasto",
        "listar tareas": "tarea",
        "listar ideas": "idea",
        "listar notas": "nota",
    }

    return filters.get(command)


def show_entries(entry_type: str | None = None) -> None:
    """Muestra los últimos registros, con filtro opcional."""

    entries = load_entries()

    if entry_type is not None:
        entries = [
            entry
            for entry in entries
            if entry.get("type") == entry_type
        ]

    if not entries:
        if entry_type:
            print(
                f"Atlas: No encontré registros "
                f"de tipo '{entry_type}'."
            )
        else:
            print("Atlas: Todavía no hay registros guardados.")

        return

    print("\nAtlas: Estos son tus últimos registros:\n")

    for index, entry in enumerate(entries[-10:], start=1):
        created_at = entry.get("created_at", "Fecha desconocida")
        category = entry.get("type", "nota")
        text = entry.get("text", "")

        print(f"{index}. [{category}] {text}")
        print(f"   Fecha: {created_at}")

    print()


def show_help() -> None:
    """Muestra los comandos disponibles."""

    print(
        """
Comandos disponibles:

  gasto: 15000 nafta
  tarea: comprar arroz
  idea: crear módulo de estudio
  cualquier otro texto se guarda como nota

  listar
  listar gastos
  listar tareas
  listar ideas
  listar notas

  ayuda
  salir
"""
    )


def main() -> None:
    """Ejecuta la interfaz principal de Atlas."""

    print("Atlas v0.1 - Captura rápida")
    print("Escribí 'ayuda' para ver los comandos.\n")

    while True:
        user_input = input("Vos: ").strip()
        command = user_input.lower()

        if not user_input:
            continue

        if command in {"salir", "exit", "q"}:
            print("Atlas: Tus registros quedaron guardados.")
            break

        if command == "ayuda":
            show_help()
            continue

        if command == "listar":
            show_entries()
            continue

        entry_type_filter = normalize_list_type(command)

        if entry_type_filter:
            show_entries(entry_type_filter)
            continue

        entry_type = detect_entry_type(user_input)
        save_entry(entry_type, user_input)

        print(f"Atlas: Guardado como {entry_type}.")


if __name__ == "__main__":
    main()