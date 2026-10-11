from contextlib import suppress
from datetime import date, datetime
from pathlib import Path
import difflib
import json
import os
import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ATLAS_DATA_FILE permite redirigir el archivo de datos (para pruebas o
# smoke tests) sin tocar los registros reales del usuario.
DATA_FILE = Path(
    os.environ.get("ATLAS_DATA_FILE", PROJECT_ROOT / "data" / "entries.jsonl")
)

# Un monto es una secuencia de dígitos, opcionalmente agrupada de a 3 con
# "." o "," como separador de miles (ej. "15000", "15.000", "1.500.000").
_AMOUNT_PATTERN = re.compile(r"^\d{1,3}([.,]\d{3})*$|^\d+$")


def _parse_amount(amount_text: str) -> int | None:
    """Convierte un texto de monto a entero, o None si no es válido.

    Solo acepta "." o "," como separador de miles. Un número como "15.5"
    no se acepta: es ambiguo (¿mil quinientos truncado? ¿15 con 5 decimales?)
    y Atlas trabaja siempre en pesos enteros.
    """

    if not _AMOUNT_PATTERN.match(amount_text):
        return None

    return int(amount_text.replace(".", "").replace(",", ""))


def _parse_amount_entry(text: str, prefix: str) -> dict | None:
    """Extrae monto y descripción de un texto con la forma "<prefijo> monto desc".

    Lo comparten gastos e ingresos: ambos tienen el mismo formato.
    """

    if not text.lower().startswith(prefix):
        return None

    content = text[len(prefix) :].strip()

    if not content:
        return None

    parts = content.split(maxsplit=1)

    amount = _parse_amount(parts[0])

    if amount is None:
        return None

    description = parts[1] if len(parts) > 1 else "Sin descripción"

    return {
        "amount": amount,
        "description": description,
    }


def parse_expense(text: str) -> dict | None:
    """Extrae monto y descripción desde un texto de gasto.

    Formato esperado:
    gasto: 15000 nafta
    """

    return _parse_amount_entry(text, "gasto:")


def parse_income(text: str) -> dict | None:
    """Extrae monto y descripción desde un texto de ingreso.

    Formato esperado:
    ingreso: 100000 uber
    """

    return _parse_amount_entry(text, "ingreso:")


def _next_id(entries: list[dict]) -> int:
    """Calcula el próximo id disponible a partir de los ids existentes.

    Usa el máximo en vez de "cantidad de registros + 1" para no repetir un
    id después de borrar un registro.
    """

    existing_ids = [
        entry["id"] for entry in entries if isinstance(entry.get("id"), int)
    ]

    return max(existing_ids, default=0) + 1


def _read_lines() -> list[str]:
    """Lee las líneas no vacías del archivo de datos, tal cual están escritas.

    Incluye las líneas que Atlas no puede interpretar como JSON: así, al
    reescribir el archivo, nunca se pierde una línea que Atlas no entendió.
    """

    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


def _parse_line(line: str) -> dict | None:
    """Interpreta una línea como registro, o None si no es un registro válido."""

    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        return None

    return entry if isinstance(entry, dict) else None


def _write_lines(lines: list[str]) -> None:
    """Reemplaza el archivo de datos por las líneas dadas, de forma segura.

    Primero escribe todo en un archivo temporal y recién al final lo
    reemplaza por el real (os.replace). Si algo falla a mitad de camino, el
    archivo original queda intacto en vez de quedar vacío o a medio escribir.
    """

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = DATA_FILE.with_name(DATA_FILE.name + ".tmp")

    try:
        with temp_file.open("w", encoding="utf-8") as file:
            for line in lines:
                file.write(line + "\n")

            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_file, DATA_FILE)

    except BaseException:
        with suppress(OSError):
            temp_file.unlink()

        raise


def save_entry(entry_type: str, text: str) -> dict:
    """Crea y guarda un registro nuevo."""

    entry = {
        "id": _next_id(load_entries()),
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

    if entry_type == "ingreso":
        income_data = parse_income(text)

        if income_data is None:
            raise ValueError(
                "No pude detectar el monto del ingreso. "
                "Usá este formato: ingreso: 100000 uber"
            )

        entry.update(income_data)

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
                print(f"Atlas: No pude leer el registro " f"de la línea {line_number}.")

    return entries


def find_entry(entry_id: int) -> dict | None:
    """Busca un registro guardado por id. None si no existe."""

    for entry in load_entries():
        if entry.get("id") == entry_id:
            return entry

    return None


def delete_entry(entry_id: int) -> bool:
    """Borra el registro con el id dado. Devuelve True si existía.

    Las líneas que Atlas no puede leer se conservan tal cual: borrar un
    registro nunca debe llevarse puesto otro.
    """

    lines = _read_lines()
    remaining = []

    for line in lines:
        entry = _parse_line(line)

        if entry is not None and entry.get("id") == entry_id:
            continue

        remaining.append(line)

    if len(remaining) == len(lines):
        return False

    _write_lines(remaining)

    return True


def mark_task_done(entry_id: int) -> str:
    """Marca una tarea como hecha.

    Devuelve "ok", "no_es_tarea" (el id existe pero no es una tarea) o
    "no_encontrado" (no hay ningún registro con ese id). Solo cambia la
    línea de esa tarea; el resto del archivo queda exactamente igual.
    """

    lines = _read_lines()

    for index, line in enumerate(lines):
        entry = _parse_line(line)

        if entry is None or entry.get("id") != entry_id:
            continue

        if entry.get("type") != "tarea":
            return "no_es_tarea"

        entry["done"] = True
        lines[index] = json.dumps(entry, ensure_ascii=False)
        _write_lines(lines)

        return "ok"

    return "no_encontrado"


def parse_id_command(command: str, keyword: str) -> int | None:
    """Extrae un id numérico de un comando tipo "borrar 3".

    None si el comando no empieza con esa palabra o lo que sigue no es un
    número entero.
    """

    prefix = f"{keyword} "

    if not command.startswith(prefix):
        return None

    id_text = command[len(prefix) :].strip()

    if not id_text.isdigit():
        return None

    return int(id_text)


def detect_entry_type(text: str) -> str:
    """Detecta el tipo de registro según el comienzo del texto."""

    lowered_text = text.lower()

    if lowered_text.startswith("gasto:"):
        return "gasto"

    if lowered_text.startswith("ingreso:"):
        return "ingreso"

    if lowered_text.startswith("tarea:"):
        return "tarea"

    if lowered_text.startswith("idea:"):
        return "idea"

    return "nota"


# Variantes sin ":" o en plural de cada prefijo conocido. Se usan solo para
# avisar de un probable error de tipeo, nunca para decidir el tipo real:
# "gasto:" sigue siendo el único formato válido.
_PROBABLE_PREFIX = {
    "gasto": "gasto:",
    "gastos": "gasto:",
    "ingreso": "ingreso:",
    "ingresos": "ingreso:",
    "tarea": "tarea:",
    "tareas": "tarea:",
    "idea": "idea:",
    "ideas": "idea:",
}

# Palabra base de cada prefijo, para buscar errores de tipeo más sueltos
# (ej. "gsato", "trea") con similitud de texto.
_KNOWN_KEYWORDS = {
    "gasto": "gasto:",
    "ingreso": "ingreso:",
    "tarea": "tarea:",
    "idea": "idea:",
}

# Por debajo de esto empiezan a aparecer falsos positivos con palabras
# reales cortas ("área" se parece a "tarea", "vida" a "idea"). El costo de
# un falso positivo es bajo: Atlas pregunta antes de guardar, así que un
# "no" lo resuelve sin perder nada.
_TYPO_SIMILARITY_CUTOFF = 0.8


def detect_probable_typo(text: str) -> str | None:
    """Si el texto parece un intento fallido de usar un prefijo conocido
    (sin ":", en plural, con algún error de tipeo), devuelve el formato
    correcto sugerido.

    Devuelve None si no hay ningún prefijo conocido parecido.
    """

    first_word = text.strip().split(maxsplit=1)[0].lower().rstrip(":")

    exact_match = _PROBABLE_PREFIX.get(first_word)

    if exact_match is not None:
        return exact_match

    close_matches = difflib.get_close_matches(
        first_word, _KNOWN_KEYWORDS.keys(), n=1, cutoff=_TYPO_SIMILARITY_CUTOFF
    )

    if close_matches:
        return _KNOWN_KEYWORDS[close_matches[0]]

    return None


def build_corrected_text(text: str, correct_prefix: str) -> str:
    """Reconstruye el texto reemplazando la primera palabra por el prefijo
    correcto (ej. "gasto 15000 nafta" + "gasto:" -> "gasto: 15000 nafta").
    """

    parts = text.strip().split(maxsplit=1)
    rest = parts[1] if len(parts) > 1 else ""

    return f"{correct_prefix} {rest}".strip()


def normalize_list_type(command: str) -> str | None:
    """Convierte el comando escrito al tipo de registro interno."""

    filters = {
        "listar gastos": "gasto",
        "listar ingresos": "ingreso",
        "listar tareas": "tarea",
        "listar ideas": "idea",
        "listar notas": "nota",
    }

    return filters.get(command)


def format_money(amount: int) -> str:
    """Formatea un número como monto en pesos argentinos."""

    sign = "-" if amount < 0 else ""

    return f"{sign}${abs(amount):,.0f}".replace(",", ".")


def show_entries(entry_type: str | None = None) -> None:
    """Muestra los últimos registros, con filtro opcional."""

    entries = load_entries()

    if entry_type is not None:
        entries = [entry for entry in entries if entry.get("type") == entry_type]

    if not entries:
        if entry_type:
            print(f"Atlas: No encontré registros " f"de tipo '{entry_type}'.")
        else:
            print("Atlas: Todavía no hay registros guardados.")

        return

    print("\nAtlas: Estos son tus últimos registros:\n")

    for entry in entries[-10:]:
        entry_id = entry.get("id", "?")
        created_at = entry.get("created_at", "Fecha desconocida")
        category = entry.get("type", "nota")
        text = entry.get("text", "")

        if category in {"gasto", "ingreso"} and "amount" in entry:
            amount = format_money(entry["amount"])
            description = entry.get("description", "Sin descripción")
            print(f"#{entry_id} [{category}] {amount} - {description}")
        elif category == "tarea":
            estado = "[x]" if entry.get("done") else "[ ]"
            print(f"#{entry_id} {estado} [tarea] {text}")
        else:
            print(f"#{entry_id} [{category}] {text}")

        print(f"   Fecha: {created_at}")

    print()


def show_total_expenses() -> None:
    """Calcula y muestra el total de gastos registrados."""

    entries = load_entries()

    expenses = [entry for entry in entries if entry.get("type") == "gasto"]

    total = 0

    for expense in expenses:
        amount = expense.get("amount")

        if isinstance(amount, int | float):
            total += amount

    print(f"Atlas: Gastaste {format_money(total)} en total.")


def _sum_income_and_expenses(entries: list[dict], period_prefix: str) -> dict:
    """Suma ingresos y gastos cuyo "created_at" empiece con el prefijo dado
    y calcula el balance. Es una función pura (no lee archivos ni imprime)
    para poder probarla.

    El prefijo define el período: un día completo ("2026-10-11") o un mes
    entero ("2026-10"), ya que created_at siempre arranca con esa fecha.
    Los registros sin "amount" numérico se ignoran, igual que en "total gastos".
    """

    income = 0
    expenses = 0

    for entry in entries:
        if not str(entry.get("created_at", "")).startswith(period_prefix):
            continue

        amount = entry.get("amount")

        if not isinstance(amount, int | float):
            continue

        if entry.get("type") == "ingreso":
            income += amount
        elif entry.get("type") == "gasto":
            expenses += amount

    return {
        "income": income,
        "expenses": expenses,
        "balance": income - expenses,
    }


def calculate_balance(entries: list[dict], day: date) -> dict:
    """Suma ingresos y gastos de un día y calcula el balance."""

    return _sum_income_and_expenses(entries, day.isoformat())


def calculate_monthly_balance(entries: list[dict], day: date) -> dict:
    """Igual que calculate_balance, pero agrupa por mes en vez de por día.

    El mes se toma de "day" (normalmente date.today()), no del registro.
    """

    return _sum_income_and_expenses(entries, day.strftime("%Y-%m"))


def show_daily_balance() -> None:
    """Muestra ingresos, gastos y balance de hoy."""

    result = calculate_balance(load_entries(), date.today())

    print("\nAtlas: Balance de hoy\n")
    print(f"  Ingresos: {format_money(result['income'])}")
    print(f"  Gastos:   {format_money(result['expenses'])}")
    print(f"  Balance:  {format_money(result['balance'])}")
    print()


def show_monthly_balance() -> None:
    """Muestra ingresos, gastos y balance del mes actual."""

    result = calculate_monthly_balance(load_entries(), date.today())

    print("\nAtlas: Balance del mes\n")
    print(f"  Ingresos: {format_money(result['income'])}")
    print(f"  Gastos:   {format_money(result['expenses'])}")
    print(f"  Balance:  {format_money(result['balance'])}")
    print()


def show_help() -> None:
    """Muestra los comandos disponibles."""

    print("""
Comandos disponibles:

  gasto: 15000 nafta
  ingreso: 100000 uber
  tarea: comprar arroz
  idea: crear módulo de estudio
  cualquier otro texto se guarda como nota

  listar
  listar gastos
  listar ingresos
  listar tareas
  listar ideas
  listar notas

  total gastos
  balance dia
  balance mes

  borrar <id>
  hecha <id>

  ayuda
  salir
""")


def _save_and_report(entry_type: str, text: str) -> None:
    """Guarda un registro y muestra el resultado (guardado u error)."""

    try:
        save_entry(entry_type, text)
        print(f"Atlas: Guardado como {entry_type}.")

    except ValueError as error:
        print(f"Atlas: {error}")


def main() -> None:
    """Ejecuta la interfaz principal de Atlas."""

    print("Atlas v0.4 - Corregir y borrar registros")
    print("Escribí 'ayuda' para ver los comandos.\n")

    # Cuando Atlas sospecha un error de tipeo (ej. "gasto" sin ":"), guarda
    # acá el texto original y el corregido, y espera la confirmación del
    # usuario en la próxima vuelta del loop antes de guardar nada.
    pending_typo: tuple[str, str] | None = None

    # Igual que pending_typo, pero para confirmar un borrado. Son estados
    # separados porque solo puede haber uno pendiente a la vez: cada uno
    # se resuelve (o cancela) antes de poder iniciar el otro.
    pending_delete_id: int | None = None

    while True:
        user_input = input("Vos: ").strip()
        command = user_input.lower()

        if not user_input:
            continue

        if pending_typo is not None:
            original_text, corrected_text = pending_typo
            pending_typo = None

            if command in {"si", "sí", "s"}:
                _save_and_report(detect_entry_type(corrected_text), corrected_text)
            else:
                _save_and_report("nota", original_text)

            continue

        if pending_delete_id is not None:
            delete_id = pending_delete_id
            pending_delete_id = None

            if command == "confirmar borrado":
                if delete_entry(delete_id):
                    print(f"Atlas: Borré el registro #{delete_id}.")
                else:
                    print(f"Atlas: El registro #{delete_id} ya no existía.")
            else:
                print("Atlas: Borrado cancelado.")

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

        if command == "balance dia":
            show_daily_balance()
            continue

        if command == "balance mes":
            show_monthly_balance()
            continue

        entry_type_filter = normalize_list_type(command)

        if entry_type_filter:
            show_entries(entry_type_filter)
            continue

        delete_id = parse_id_command(command, "borrar")

        if delete_id is not None:
            entry = find_entry(delete_id)

            if entry is None:
                print(f"Atlas: No encontré ningún registro con id #{delete_id}.")
            else:
                print(
                    f"Atlas: Vas a borrar #{delete_id} [{entry.get('type')}] "
                    f"{entry.get('text')}"
                )
                print("Atlas: Escribí 'confirmar borrado' para confirmar.")
                pending_delete_id = delete_id

            continue

        done_id = parse_id_command(command, "hecha")

        if done_id is not None:
            resultado = mark_task_done(done_id)

            if resultado == "ok":
                print(f"Atlas: Marqué la tarea #{done_id} como hecha.")
            elif resultado == "no_es_tarea":
                print(f"Atlas: El registro #{done_id} no es una tarea.")
            else:
                print(f"Atlas: No encontré ninguna tarea con id #{done_id}.")

            continue

        entry_type = detect_entry_type(user_input)

        if entry_type == "nota":
            formato_sugerido = detect_probable_typo(user_input)

            if formato_sugerido is not None:
                corrected_text = build_corrected_text(user_input, formato_sugerido)
                print(f"Atlas: ¿Quisiste escribir '{corrected_text}'? (si/no)")
                pending_typo = (user_input, corrected_text)
                continue

        _save_and_report(entry_type, user_input)


if __name__ == "__main__":
    main()
