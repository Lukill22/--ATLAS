from contextlib import suppress
from datetime import date, datetime, timedelta
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
    """Extrae monto, descripción y categoría opcional de un texto con la
    forma "<prefijo> monto desc #categoria".

    Lo comparten gastos e ingresos: ambos tienen el mismo formato. También
    acepta el orden invertido ("<prefijo> desc monto", ej. "gasto: nafta
    12000"): es un error real y repetido — así se habla en la vida real,
    diciendo primero de qué es el gasto y después cuánto fue.

    La categoría es opcional, va al final separada por "#" (puede tener
    varias palabras, ej. "#gastos fijos"), y es la única parte de este
    formato donde "#" tiene un significado especial: en cualquier otro
    lugar del texto, "#" es un caracter común.
    """

    if not text.lower().startswith(prefix):
        return None

    content = text[len(prefix) :].strip()

    if not content:
        return None

    category = None

    if "#" in content:
        content, _, category_text = content.partition("#")
        content = content.strip()
        category = category_text.strip() or None

        if not content:
            return None

    parts = content.split(maxsplit=1)
    amount = _parse_amount(parts[0])

    if amount is not None:
        description = parts[1] if len(parts) > 1 else "Sin descripción"
        result = {"amount": amount, "description": description}

        if category:
            result["categoria"] = category

        return result

    palabras = content.split()

    if len(palabras) < 2:
        return None

    amount = _parse_amount(palabras[-1])

    if amount is None:
        return None

    result = {
        "amount": amount,
        "description": " ".join(palabras[:-1]),
    }

    if category:
        result["categoria"] = category

    return result


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


# "19/10 08:00 texto" o "19/10/2026 08:00 texto" (año opcional, usa el
# actual si falta). Fecha y hora con formato fijo, sin adivinar, igual
# que el resto de Atlas.
_REMINDER_PATTERN = re.compile(
    r"^(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s+(\d{1,2}):(\d{2})\s+(.+)$"
)


def parse_reminder(text: str) -> dict | None:
    """Extrae fecha, hora y descripción desde un texto de recordatorio.

    Formato esperado:
    recordatorio: 19/10 08:00 sacar la basura
    """

    if not text.lower().startswith("recordatorio:"):
        return None

    content = text[len("recordatorio:") :].strip()

    if not content:
        return None

    match = _REMINDER_PATTERN.match(content)

    if match is None:
        return None

    dia, mes, anio, hora, minuto, descripcion = match.groups()

    try:
        due_at = datetime(
            int(anio) if anio else date.today().year,
            int(mes),
            int(dia),
            int(hora),
            int(minuto),
        )
    except ValueError:
        return None

    return {
        "due_at": due_at.isoformat(timespec="minutes"),
        "description": descripcion.strip(),
        "notified": False,
    }


# "23:00" (hora y minuto con 2 dígitos). Formato fijo, igual que el resto
# de Atlas: no intenta adivinar "a las 11 de la noche" ni variantes así.
_DAILY_BALANCE_PATTERN = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_daily_balance_config(text: str) -> str | None:
    """Extrae la hora desde un texto de configuración de balance diario.

    Formato esperado:
    balance diario: 23:00

    Devuelve la hora normalizada ("23:00"), o None si no matchea o la hora
    no es válida (ej. "25:00").
    """

    if not text.lower().startswith("balance diario:"):
        return None

    content = text[len("balance diario:") :].strip()
    match = _DAILY_BALANCE_PATTERN.match(content)

    if match is None:
        return None

    hora, minuto = match.groups()

    if not (0 <= int(hora) <= 23 and 0 <= int(minuto) <= 59):
        return None

    return f"{int(hora):02d}:{minuto}"


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


def get_due_reminders(entries: list[dict], ahora: datetime) -> list[dict]:
    """Devuelve los recordatorios vencidos (due_at <= ahora) que todavía no
    se avisaron. Función pura (no lee archivos), para poder probarla con
    una fecha fija en vez de datetime.now().
    """

    vencidos = []

    for entry in entries:
        if entry.get("type") != "recordatorio" or entry.get("notified"):
            continue

        due_at = entry.get("due_at")

        if not due_at:
            continue

        try:
            due = datetime.fromisoformat(due_at)
        except ValueError:
            continue

        if due <= ahora:
            vencidos.append(entry)

    return vencidos


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


def get_due_daily_balances(entries: list[dict], ahora: datetime) -> list[dict]:
    """Devuelve las configuraciones de balance diario a las que ya les toca
    avisar: la hora configurada ya pasó hoy y todavía no se mandó hoy.
    Función pura, para poder probarla con una fecha fija.
    """

    pendientes = []
    hoy = ahora.date().isoformat()

    for entry in entries:
        if entry.get("type") != "balance_diario":
            continue

        if entry.get("last_sent_date") == hoy:
            continue

        hora_texto = entry.get("hora")

        if not hora_texto:
            continue

        try:
            hora_objetivo = datetime.strptime(hora_texto, "%H:%M").time()
        except ValueError:
            continue

        if ahora.time() >= hora_objetivo:
            pendientes.append(entry)

    return pendientes


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

    if lowered_text.startswith("recordatorio:"):
        return "recordatorio"

    if lowered_text.startswith("balance diario:"):
        return "balance_diario"

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
    "recordatorio": "recordatorio:",
    "recordatorios": "recordatorio:",
}

# Palabra base de cada prefijo, para buscar errores de tipeo más sueltos
# (ej. "gsato", "trea") con similitud de texto.
_KNOWN_KEYWORDS = {
    "gasto": "gasto:",
    "ingreso": "ingreso:",
    "tarea": "tarea:",
    "idea": "idea:",
    "recordatorio": "recordatorio:",
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


# Palabra tal como se escribe -> tipo interno, para parse_list_command.
# Acepta tanto el plural ("listar gastos") como el singular ("listar
# gasto"): caso real repetido, se escribe en singular sin pensarlo.
_LIST_TYPE_WORDS = {
    "gasto": "gasto",
    "gastos": "gasto",
    "ingreso": "ingreso",
    "ingresos": "ingreso",
    "tarea": "tarea",
    "tareas": "tarea",
    "idea": "idea",
    "ideas": "idea",
    "nota": "nota",
    "notas": "nota",
    "recordatorio": "recordatorio",
    "recordatorios": "recordatorio",
}

_PERIOD_WORDS = {"hoy", "mes"}


def parse_list_command(command: str) -> dict | None:
    """Interpreta un comando "listar [tipo] [período]".

    Ejemplos válidos: "listar", "listar gastos", "listar hoy",
    "listar tareas mes" (el orden tipo-período es fijo). Devuelve None si
    command no empieza con "listar" o tiene alguna palabra que no es ni un
    tipo ni un período conocido.

    Tolera ":" de más al final de "listar" o de cualquier palabra (ej.
    "listar gastos:"), porque es un error natural de cometer: el resto de
    Atlas sí usa ":" (gasto:, tarea:), así que es fácil escribirlo de más
    por costumbre.
    """

    command = command.rstrip(":")

    if command != "listar" and not command.startswith("listar "):
        return None

    palabras = command[len("listar") :].split()

    if len(palabras) > 2:
        return None

    entry_type: str | None = None
    period: str | None = None

    for palabra in palabras:
        palabra = palabra.rstrip(":")

        if palabra in _LIST_TYPE_WORDS and entry_type is None:
            entry_type = _LIST_TYPE_WORDS[palabra]
        elif palabra in _PERIOD_WORDS and period is None:
            period = palabra
        else:
            return None

    return {"entry_type": entry_type, "period": period}


def filter_by_period(entries: list[dict], period: str | None) -> list[dict]:
    """Filtra registros cuyo "created_at" caiga en el período dado.

    period es "hoy", "mes", o None (no filtra nada). Usa la fecha actual,
    igual que calculate_balance/calculate_monthly_balance.
    """

    if period is None:
        return entries

    today = date.today()
    prefix = today.isoformat() if period == "hoy" else today.strftime("%Y-%m")

    return [
        entry
        for entry in entries
        if str(entry.get("created_at", "")).startswith(prefix)
    ]


def format_money(amount: int) -> str:
    """Formatea un número como monto en pesos argentinos."""

    sign = "-" if amount < 0 else ""

    return f"{sign}${abs(amount):,.0f}".replace(",", ".")


def format_entry_summary(entry: dict) -> str:
    """Describe un registro en una línea legible (sin id ni fecha).

    Lo usan tanto show_entries() (terminal) como la interfaz web, para que
    las dos muestren exactamente lo mismo sin duplicar esta lógica.
    """

    category = entry.get("type", "nota")
    text = entry.get("text", "")

    if category in {"gasto", "ingreso"} and "amount" in entry:
        amount = format_money(entry["amount"])
        description = entry.get("description", "Sin descripción")
        resumen = f"[{category}] {amount} - {description}"

        if entry.get("categoria"):
            resumen += f" #{entry['categoria']}"

        return resumen

    if category == "tarea":
        estado = "[x]" if entry.get("done") else "[ ]"
        return f"{estado} [tarea] {text}"

    if category == "recordatorio" and "due_at" in entry:
        try:
            fecha_legible = datetime.fromisoformat(entry["due_at"]).strftime(
                "%d/%m %H:%M"
            )
        except ValueError:
            fecha_legible = entry["due_at"]

        estado = "✅" if entry.get("notified") else "⏰"
        descripcion = entry.get("description", text)
        return f"{estado} [recordatorio] {fecha_legible} - {descripcion}"

    if category == "balance_diario" and "hora" in entry:
        enviado_hoy = entry.get("last_sent_date") == date.today().isoformat()
        estado = "✅ enviado hoy" if enviado_hoy else "⏰ pendiente"
        return f"{estado} [balance diario] {entry['hora']}"

    return f"[{category}] {text}"


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


def calculate_total_expenses(entries: list[dict]) -> int:
    """Suma todos los gastos de la lista dada. Función pura, sin I/O."""

    total = 0

    for entry in entries:
        if entry.get("type") != "gasto":
            continue

        amount = entry.get("amount")

        if isinstance(amount, int | float):
            total += amount

    return total


def show_total_expenses() -> None:
    """Calcula y muestra el total de gastos registrados."""

    total = calculate_total_expenses(load_entries())

    print(f"Atlas: Gastaste {format_money(total)} en total.")


def calculate_total_income(entries: list[dict]) -> int:
    """Suma todos los ingresos de la lista dada. Función pura, sin I/O."""

    total = 0

    for entry in entries:
        if entry.get("type") != "ingreso":
            continue

        amount = entry.get("amount")

        if isinstance(amount, int | float):
            total += amount

    return total


def show_total_income() -> None:
    """Calcula y muestra el total de ingresos registrados."""

    total = calculate_total_income(load_entries())

    print(f"Atlas: Ingresaste {format_money(total)} en total.")


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


def calculate_weekly_balance(entries: list[dict], day: date) -> dict:
    """Igual que calculate_balance, pero agrupa de lunes a domingo (la
    semana que contiene a "day") en vez de por día o mes.

    A diferencia de calculate_balance/calculate_monthly_balance, una
    semana puede cruzar dos meses (ej. 29/10 a 4/11), así que no alcanza
    con comparar un prefijo del string de fecha: hay que parsear la fecha
    de cada registro y compararla contra el rango real de la semana.
    """

    inicio_semana = day - timedelta(days=day.weekday())
    fin_semana = inicio_semana + timedelta(days=7)

    income = 0
    expenses = 0

    for entry in entries:
        created_at = entry.get("created_at")

        if not created_at:
            continue

        try:
            fecha = datetime.fromisoformat(created_at).date()
        except ValueError:
            continue

        if not (inicio_semana <= fecha < fin_semana):
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


def calculate_total_balance(entries: list[dict]) -> dict:
    """Igual que calculate_balance, pero de toda la vida (sin filtrar por
    fecha): todo string de fecha empieza con el prefijo vacío.
    """

    return _sum_income_and_expenses(entries, "")


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


HELP_TEXT = """Comandos disponibles:

  listar / listar gastos / ingresos / tareas / ideas / notas / recordatorios
  listar hoy / mes

  total gastos / ingresos
  balance dia / semana / mes / total

  borrar <id>
  hecha <id>
  backup

  recordatorio: 19/10 08:00 sacar la basura
  balance diario: 23:00
  gasto:/ingreso: ... #categoria (opcional, ej. gasto: 5000 nafta #auto)

  ayuda
  salir"""
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


def format_saved_message(entry_type: str, entry: dict) -> str:
    """Mensaje de confirmación al guardar un registro nuevo, compartido
    por terminal, web y bot para que los tres digan lo mismo.

    Muestra la categoría si hay una (puesta a mano con "#categoria" o
    detectada sola de un registro anterior), para que quede claro que
    Atlas la categorizó sin que haga falta volver a escribirla.
    """

    etiqueta = entry_type.replace("_", " ")

    if entry.get("categoria"):
        return f"Guardado como {etiqueta} (#{entry['categoria']})."

    return f"Guardado como {etiqueta}."


def format_balance_summary(resultado: dict) -> str:
    """Una línea con ingresos, gastos y balance, para mostrar fuera de la
    terminal (web, Telegram), donde el formato de 3 líneas de
    show_daily_balance/show_monthly_balance no hace falta.
    """

    return (
        f"Ingresos: {format_money(resultado['income'])} · "
        f"Gastos: {format_money(resultado['expenses'])} · "
        f"Balance: {format_money(resultado['balance'])}"
    )


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
