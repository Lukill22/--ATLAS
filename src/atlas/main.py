from datetime import datetime
from pathlib import Path
import json


DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "entries.jsonl"


def save_entry(entry_type: str, text: str) -> dict:
    entry = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "type": entry_type,
        "text": text,
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with DATA_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def detect_entry_type(text: str) -> str:
    lowered_text = text.lower()

    if lowered_text.startswith("gasto:"):
        return "gasto"

    if lowered_text.startswith("tarea:"):
        return "tarea"

    if lowered_text.startswith("idea:"):
        return "idea"

    return "nota"


def main() -> None:
    print("Atlas v0.1 - Captura rápida")
    print("Podés escribir cosas como:")
    print("- gasto: 12000 nafta")
    print("- tarea: comprar arroz")
    print("- idea: crear módulo de estudio")
    print("- cualquier nota libre")
    print("Escribí 'salir' para terminar.\n")

    while True:
        user_input = input("Vos: ").strip()

        if user_input.lower() in ["salir", "exit", "q"]:
            print("Atlas: Listo. Guardé tus registros.")
            break

        if not user_input:
            continue

        entry_type = detect_entry_type(user_input)
        save_entry(entry_type, user_input)

        print(f"Atlas: Guardado como {entry_type}.")


if __name__ == "__main__":
    main()