import difflib
import json
import os
import sys
from contextlib import suppress
from datetime import date, datetime
from pathlib import Path

# Si se ejecuta como script (`python src/atlas/main.py`) en vez de módulo, el
# paquete `atlas` todavía no está en sys.path. Se agrega antes de importar los
# módulos hermanos (parsing, calculations, formatting). Mismo truco que web.py.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from atlas.calculations import (  # noqa: E402, F401
    calculate_balance,
    calculate_monthly_balance,
    calculate_total_balance,
    calculate_total_expenses,
    calculate_total_income,
    calculate_weekly_balance,
    filter_by_period,
    get_due_daily_balances,
    get_due_reminders,
    group_by_category,
)
from atlas.formatting import (  # noqa: E402, F401
    HELP_TEXT,
    format_balance_summary,
    format_entry_summary,
    format_money,
    format_saved_message,
)
from atlas.parsing import (  # noqa: E402, F401
    build_corrected_text,
    detect_entry_type,
    detect_probable_typo,
    parse_daily_balance_config,
    parse_expense,
    parse_id_command,
    parse_income,
    parse_list_command,
    parse_reminder,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ATLAS_DATA_FILE permite redirigir el archivo de datos (para pruebas o
# smoke tests) sin tocar los registros reales del usuario.
DATA_FILE = Path(
    os.environ.get("ATLAS_DATA_FILE", PROJECT_ROOT / "data" / "entries.jsonl")
)


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


# Al inferir una categoría sin "#categoria" explícito, estas palabras no
# cuentan como señal: aparecen por igual en descripciones de categorías
# completamente distintas ("en nafta", "en comida") y causarían
# categorizaciones cruzadas falsas si se las tuviera en cuenta.
_CATEGORY_STOPWORDS = {
    "en",
    "el",
    "la",
    "los",
    "las",
    "de",
    "del",
    "un",
    "una",
    "con",
    "y",
}


def _infer_category(description: str, entry_type: str) -> str | None:
    """Busca, entre los gastos o ingresos ya guardados, si alguna palabra
    de "description" ya se había asociado antes a una categoría (puesta a
    mano con "#categoria"), y devuelve la más reciente que coincida.

    Así, después de etiquetar "nafta" como "#auto" una sola vez, los
    próximos gastos que digan "nafta" se categorizan solos. Separado por
    entry_type para que gastos e ingresos nunca se mezclen entre sí.
    """

    palabras_nuevas = {
        palabra
        for palabra in description.lower().split()
        if palabra not in _CATEGORY_STOPWORDS
    }

    if not palabras_nuevas:
        return None

    for entry in reversed(load_entries()):
        if entry.get("type") != entry_type:
            continue

        categoria = entry.get("categoria")

        if not categoria:
            continue

        palabras_viejas = {
            palabra
            for palabra in entry.get("description", "").lower().split()
            if palabra not in _CATEGORY_STOPWORDS
        }

        if palabras_nuevas & palabras_viejas:
            return categoria

    return None


def create_backup() -> Path | None:
    """Copia el archivo de datos actual a uno con fecha y hora en el nombre.

    None si todavía no hay nada guardado. Cada backup tiene su propio
    timestamp y nunca sobrescribe uno anterior: si se borrara algo por
    error entre dos backups, el más viejo todavía lo conserva.
    """

    if not DATA_FILE.exists():
        return None

    marca = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    backup_path = DATA_FILE.with_name(f"{DATA_FILE.stem}.{marca}.bak{DATA_FILE.suffix}")

    with backup_path.open("w", encoding="utf-8") as file:
        for line in _read_lines():
            file.write(line + "\n")

    return backup_path


def save_entry(entry_type: str, text: str, chat_id: int | None = None) -> dict:
    """Crea y guarda un registro nuevo.

    chat_id identifica a quién avisarle si entry_type es "recordatorio" o
    "balance_diario" (solo el bot de Telegram puede avisar de verdad; la
    terminal y la web lo pasan en None, así que ese recordatorio o balance
    diario queda sin nadie a quien avisar, pero se puede seguir listando).
    """

    if entry_type == "balance_diario":
        hora = parse_daily_balance_config(text)

        if hora is None:
            raise ValueError(
                "No pude detectar la hora. Usá este formato: balance diario: 23:00"
            )

        return set_daily_balance_config(hora, chat_id)

    entry = {
        "id": _next_id(load_entries()),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "type": entry_type,
        "text": text,
    }

    if chat_id is not None:
        entry["chat_id"] = chat_id

    if entry_type == "gasto":
        expense_data = parse_expense(text)

        if expense_data is None:
            raise ValueError(
                "No pude detectar el monto del gasto. "
                "Usá este formato: gasto: 15000 nafta"
            )

        entry.update(expense_data)

        if "categoria" not in entry and entry["description"] != "Sin descripción":
            categoria = _infer_category(entry["description"], "gasto")

            if categoria:
                entry["categoria"] = categoria

    if entry_type == "ingreso":
        income_data = parse_income(text)

        if income_data is None:
            raise ValueError(
                "No pude detectar el monto del ingreso. "
                "Usá este formato: ingreso: 100000 uber"
            )

        entry.update(income_data)

        if "categoria" not in entry and entry["description"] != "Sin descripción":
            categoria = _infer_category(entry["description"], "ingreso")

            if categoria:
                entry["categoria"] = categoria

    if entry_type == "recordatorio":
        reminder_data = parse_reminder(text)

        if reminder_data is None:
            raise ValueError(
                "No pude detectar la fecha del recordatorio. "
                "Usá este formato: recordatorio: 19/10 08:00 sacar la basura"
            )

        entry.update(reminder_data)

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


def set_entry_category(entry_id: int, categoria: str) -> str:
    """Cambia a mano la categoría de un gasto o ingreso ya guardado.

    Un "categoria" vacío (tras strip) borra la categoría en vez de
    dejarla puesta a propósito: es la forma de "no quiero esta
    categoría" sin tener que inventar un valor.

    Devuelve "ok", "no_es_gasto_ni_ingreso" (el id existe pero no es de
    un tipo con categoría) o "no_encontrado".
    """

    lines = _read_lines()

    for index, line in enumerate(lines):
        entry = _parse_line(line)

        if entry is None or entry.get("id") != entry_id:
            continue

        if entry.get("type") not in {"gasto", "ingreso"}:
            return "no_es_gasto_ni_ingreso"

        categoria = categoria.strip().lower()

        if categoria:
            entry["categoria"] = categoria
        else:
            entry.pop("categoria", None)

        lines[index] = json.dumps(entry, ensure_ascii=False)
        _write_lines(lines)

        return "ok"

    return "no_encontrado"


def merge_categories(entry_type: str, desde: str, hacia: str) -> int:
    """Une dos categorías existentes de un mismo tipo (gasto o ingreso):
    todo registro con categoría "desde" pasa a tener "hacia".

    Compara sin importar mayúsculas/minúsculas (para poder unir justo el
    caso típico: "Nafta" y "nafta" quedaron separadas antes de empezar a
    normalizar todo a minúsculas). Devuelve cuántos registros cambiaron;
    0 si "desde"/"hacia" están vacíos o no había nada para unir.
    """

    desde = desde.strip().lower()
    hacia = hacia.strip().lower()

    if not desde or not hacia:
        return 0

    lines = _read_lines()
    cambiados = 0

    for index, line in enumerate(lines):
        entry = _parse_line(line)

        if entry is None or entry.get("type") != entry_type:
            continue

        if (entry.get("categoria") or "").lower() != desde:
            continue

        entry["categoria"] = hacia
        lines[index] = json.dumps(entry, ensure_ascii=False)
        cambiados += 1

    if cambiados:
        _write_lines(lines)

    return cambiados


def mark_reminder_notified(entry_id: int) -> bool:
    """Marca un recordatorio como ya avisado. True si lo encontró."""

    lines = _read_lines()

    for index, line in enumerate(lines):
        entry = _parse_line(line)

        if entry is None or entry.get("id") != entry_id:
            continue

        if entry.get("type") != "recordatorio":
            return False

        entry["notified"] = True
        lines[index] = json.dumps(entry, ensure_ascii=False)
        _write_lines(lines)

        return True

    return False


def set_daily_balance_config(hora: str, chat_id: int | None) -> dict:
    """Crea o actualiza la configuración de balance diario automático.

    Solo tiene sentido una por chat: configurarla de nuevo con otra hora
    actualiza la que ya existía (y reinicia "last_sent_date") en vez de
    sumar una segunda, lo que mandaría el balance dos veces por noche.
    """

    lines = _read_lines()

    for index, line in enumerate(lines):
        entry = _parse_line(line)

        if (
            entry is not None
            and entry.get("type") == "balance_diario"
            and entry.get("chat_id") == chat_id
        ):
            entry["hora"] = hora
            entry["last_sent_date"] = None
            lines[index] = json.dumps(entry, ensure_ascii=False)
            _write_lines(lines)

            return entry

    entry = {
        "id": _next_id(load_entries()),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "type": "balance_diario",
        "text": f"balance diario: {hora}",
        "hora": hora,
        "last_sent_date": None,
    }

    if chat_id is not None:
        entry["chat_id"] = chat_id

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with DATA_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def mark_daily_balance_sent(entry_id: int, fecha: str) -> bool:
    """Marca un balance diario como ya enviado hoy (fecha ISO). True si lo
    encontró.
    """

    lines = _read_lines()

    for index, line in enumerate(lines):
        entry = _parse_line(line)

        if entry is None or entry.get("id") != entry_id:
            continue

        if entry.get("type") != "balance_diario":
            return False

        entry["last_sent_date"] = fecha
        lines[index] = json.dumps(entry, ensure_ascii=False)
        _write_lines(lines)

        return True

    return False


def show_entries(entry_type: str | None = None, period: str | None = None) -> None:
    """Muestra los últimos registros, con filtro opcional de tipo y/o período."""

    entries = load_entries()

    if entry_type is not None:
        entries = [entry for entry in entries if entry.get("type") == entry_type]

    entries = filter_by_period(entries, period)

    if not entries:
        if entry_type or period:
            descripcion = " ".join(parte for parte in (entry_type, period) if parte)
            print(f"Atlas: No encontré registros para '{descripcion}'.")
        else:
            print("Atlas: Todavía no hay registros guardados.")

        return

    print("\nAtlas: Estos son tus últimos registros:\n")

    for entry in entries[-10:]:
        entry_id = entry.get("id", "?")
        created_at = entry.get("created_at", "Fecha desconocida")
        print(f"#{entry_id} {format_entry_summary(entry)}")
        print(f"   Fecha: {created_at}")

    print()


def show_total_expenses() -> None:
    """Calcula y muestra el total de gastos registrados."""

    total = calculate_total_expenses(load_entries())

    print(f"Atlas: Gastaste {format_money(total)} en total.")


def show_total_income() -> None:
    """Calcula y muestra el total de ingresos registrados."""

    total = calculate_total_income(load_entries())

    print(f"Atlas: Ingresaste {format_money(total)} en total.")


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


def show_weekly_balance() -> None:
    """Muestra ingresos, gastos y balance de la semana actual (lunes a domingo)."""

    result = calculate_weekly_balance(load_entries(), date.today())

    print("\nAtlas: Balance de la semana\n")
    print(f"  Ingresos: {format_money(result['income'])}")
    print(f"  Gastos:   {format_money(result['expenses'])}")
    print(f"  Balance:  {format_money(result['balance'])}")
    print()


def show_total_balance() -> None:
    """Muestra ingresos, gastos y balance de toda la vida."""

    result = calculate_total_balance(load_entries())

    print("\nAtlas: Balance total\n")
    print(f"  Ingresos: {format_money(result['income'])}")
    print(f"  Gastos:   {format_money(result['expenses'])}")
    print(f"  Balance:  {format_money(result['balance'])}")
    print()


# La terminal, la web y el bot de Telegram muestran este mismo texto (la
# web y el bot no tienen "salir": cerrar la pestaña/chat alcanza), para que
# la ayuda nunca se desincronice entre los tres. No incluye cómo capturar
# gasto:/tarea:/etc. (una vez que se sabe usar, esa parte sobra acá), pero
# sí el formato de "recordatorio:" y el de "#categoria" porque ninguno de
# los dos es adivinable.


def show_help() -> None:
    """Muestra los comandos disponibles."""

    print(f"\n{HELP_TEXT}\n")


def show_backup() -> None:
    """Crea una copia de seguridad del archivo de datos y avisa dónde quedó."""

    backup_path = create_backup()

    if backup_path is None:
        print("Atlas: Todavía no hay nada guardado para respaldar.")
    else:
        print(f"Atlas: Copia de seguridad guardada en {backup_path.name}.")


# Comandos de una sola forma fija (sin parámetros variables como <id> o
# [tipo]), para los que vale la pena tolerar errores de tipeo o palabras
# de más (ej. "total de gatos" -> "total gastos"). Ejecutarlos directo sin
# confirmar es seguro: son de solo lectura, o backup, que nunca destruye
# nada.
_FIXED_COMMANDS = [
    "ayuda",
    "total gastos",
    "total ingresos",
    "balance dia",
    "balance semana",
    "balance mes",
    "balance total",
    "backup",
]

# Palabras de relleno que se ignoran al comparar (así "total DE gatos"
# compara como "total gatos").
_COMMAND_STOPWORDS = {"de", "del", "la", "el", "los", "las", "un", "una"}

# Más alto que _TYPO_SIMILARITY_CUTOFF porque acá se comparan frases
# completas, no una sola palabra: con un umbral más bajo, "listar gastos"
# termina pareciéndose a "total gastos" (comparten la palabra "gastos") y
# se ejecutaría el comando equivocado. 0.75 evita esa confusión sin perder
# los casos reales ("total de gatos", "balanse dia", "backp", "ayud").
_COMMAND_SIMILARITY_CUTOFF = 0.75


def _match_fixed_command(comando: str) -> str | None:
    """Si comando se parece bastante a uno de los _FIXED_COMMANDS, lo
    devuelve corregido. None si no se parece a ninguno, o si empieza con
    "listar" o "balance diario" (esos ya tienen su propia captura/parser,
    no deben competir con esto: "balance diario: 23:00" comparte la
    palabra "balance" con "balance dia"/"balance mes").
    """

    if comando.startswith("listar") or comando.startswith("balance diario"):
        return None

    normalizado = " ".join(
        palabra for palabra in comando.split() if palabra not in _COMMAND_STOPWORDS
    )

    cercanos = difflib.get_close_matches(
        normalizado, _FIXED_COMMANDS, n=1, cutoff=_COMMAND_SIMILARITY_CUTOFF
    )

    return cercanos[0] if cercanos else None


def handle_command(texto: str) -> dict | None:
    """Interpreta un comando de texto (ayuda, listar, balance, borrar,
    hecha, backup) fuera de la terminal: lo usan tanto la interfaz web
    como el bot de Telegram, para no duplicar esta lógica en cada canal
    de entrada nuevo.

    Devuelve {"respuesta": texto} para mostrar como respuesta, o
    {"redirect_borrar": id} cuando hace falta confirmar un borrado antes
    de ejecutarlo (cada canal decide cómo pedir esa confirmación).

    None si texto no es ninguno de estos comandos (se trata como una
    captura normal: gasto/ingreso/tarea/idea/recordatorio/nota).
    """

    # Se tolera un ":" de más al final (ej. "ayuda:", "backup:"): es un
    # error natural de cometer porque el resto de Atlas sí usa ":" para
    # capturar (gasto:, tarea:, recordatorio:). Solo afecta esta copia
    # usada para comparar comandos, nunca al "texto" original que se usa
    # para capturas.
    comando = texto.strip().lower().rstrip(":")

    if comando == "ayuda":
        return {"respuesta": HELP_TEXT, "es_ayuda": True}

    if comando == "total gastos":
        total = calculate_total_expenses(load_entries())
        return {"respuesta": f"Gastaste {format_money(total)} en total."}

    if comando == "total ingresos":
        total = calculate_total_income(load_entries())
        return {"respuesta": f"Ingresaste {format_money(total)} en total."}

    if comando == "balance dia":
        return {
            "respuesta": format_balance_summary(
                calculate_balance(load_entries(), date.today())
            )
        }

    if comando == "balance semana":
        return {
            "respuesta": format_balance_summary(
                calculate_weekly_balance(load_entries(), date.today())
            )
        }

    if comando == "balance mes":
        return {
            "respuesta": format_balance_summary(
                calculate_monthly_balance(load_entries(), date.today())
            )
        }

    if comando == "balance total":
        return {
            "respuesta": format_balance_summary(calculate_total_balance(load_entries()))
        }

    if comando == "backup":
        backup_path = create_backup()

        if backup_path is None:
            return {"respuesta": "Todavía no hay nada guardado para respaldar."}

        return {"respuesta": f"Copia de seguridad guardada en {backup_path.name}."}

    delete_id = parse_id_command(comando, "borrar")

    if delete_id is not None:
        return {"redirect_borrar": delete_id}

    done_id = parse_id_command(comando, "hecha")

    if done_id is not None:
        resultado = mark_task_done(done_id)

        if resultado == "ok":
            return {"respuesta": f"Marqué la tarea #{done_id} como hecha."}

        if resultado == "no_es_tarea":
            return {"respuesta": f"El registro #{done_id} no es una tarea."}

        return {"respuesta": f"No encontré ninguna tarea con id #{done_id}."}

    lista = parse_list_command(comando)

    if lista is not None:
        entries = load_entries()

        if lista["entry_type"]:
            entries = [e for e in entries if e.get("type") == lista["entry_type"]]

        entries = filter_by_period(entries, lista["period"])
        entries = entries[-10:]

        if not entries:
            return {"respuesta": "No encontré registros para ese filtro."}

        lineas = [
            f"#{entry.get('id', '?')} {format_entry_summary(entry)}"
            for entry in reversed(entries)
        ]
        return {"respuesta": "\n".join(lineas)}

    # Nada matcheó exacto. Probamos si se parece bastante a uno de los
    # comandos fijos (ej. "total de gatos" -> "total gastos") antes de
    # darnos por vencidos y tratarlo como una nota.
    comando_corregido = _match_fixed_command(comando)

    if comando_corregido is not None:
        return handle_command(comando_corregido)

    return None


def _save_and_report(entry_type: str, text: str) -> None:
    """Guarda un registro y muestra el resultado (guardado u error)."""

    try:
        entry = save_entry(entry_type, text)
        print(f"Atlas: {format_saved_message(entry_type, entry)}")

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

        list_command = parse_list_command(command)

        if list_command is not None:
            show_entries(list_command["entry_type"], list_command["period"])
            continue

        if command == "total gastos":
            show_total_expenses()
            continue

        if command == "total ingresos":
            show_total_income()
            continue

        if command == "balance dia":
            show_daily_balance()
            continue

        if command == "balance semana":
            show_weekly_balance()
            continue

        if command == "balance mes":
            show_monthly_balance()
            continue

        if command == "balance total":
            show_total_balance()
            continue

        if command == "backup":
            show_backup()
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
