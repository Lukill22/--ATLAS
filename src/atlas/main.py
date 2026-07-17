from datetime import datetime
from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_ROOT / "data" / "entries.jsonl"


def parse_expense(text: str) -> dict | None:
    """Extrae monto y descripción desde un texto de gasto.

    Formato esperado:
    gasto: 15000 nafta
    """

    content = text.removeprefix("gasto:").strip()

    if not content:
        return None

    parts = content.split(maxsplit=1)

    if len(parts) == 0:
        return None

    amount_text = parts[0].replace(".", "").replace(",", "")

    if not amount_text.isdigit():
        return None

    amount = int(amount_text)
    description = parts[1] if len(parts) > 1 else "Sin descripción"

    return {
        "amount": amount,
        "description": description,
    }


def save_entry(entry_type: str, text: str) -> dict:
    """Crea y guarda un registro nuevo."""

    entry = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "type": entry_type,
        "text": text,
    }

    if entry_type == "gasto":
        expense_data = parse_expense(text)

        if expense_data is None:
            raise ValueError(
                "No pude detectar el monto del gasto. "
                "Usá este formato: gasto: 15000 nafta"
            )

        entry.update(expense_data)

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


def format_money(amount: int) -> str:
    """Formatea un número como monto en pesos argentinos."""

    return f"${amount:,.0f}".replace(",", ".")


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

        if category == "gasto" and "amount" in entry:
            amount = format_money(entry["amount"])
            description = entry.get("description", "Sin descripción")
            print(f"{index}. [gasto] {amount} - {description}")
        else:
            print(f"{index}. [{category}] {text}")

        print(f"   Fecha: {created_at}")

    print()


def show_total_expenses() -> None:
    """Calcula y muestra el total de gastos registrados."""

    entries = load_entries()

    expenses = [
        entry
        for entry in entries
        if entry.get("type") == "gasto"
    ]

    total = 0

    for expense in expenses:
        amount = expense.get("amount")

        if isinstance(amount, int | float):
            total += amount

    print(f"Atlas: Gastaste {format_money(total)} en total.")


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

  total gastos

  ayuda
  salir
"""
    )


def main() -> None:
    """Ejecuta la interfaz principal de Atlas."""

    print("Atlas v0.2 - Gastos estructurados")
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

        if command == "total gastos":
            show_total_expenses()
            continue

        entry_type_filter = normalize_list_type(command)

        if entry_type_filter:
            show_entries(entry_type_filter)
            continue

        entry_type = detect_entry_type(user_input)

        try:
            save_entry(entry_type, user_input)
            print(f"Atlas: Guardado como {entry_type}.")

        except ValueError as error:
            print(f"Atlas: {error}")


if __name__ == "__main__":
    main()