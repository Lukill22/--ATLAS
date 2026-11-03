"""Parseo de texto: convierte lo que escribe el usuario en datos.

Son funciones puras: no leen ni escriben archivos, así que se pueden probar
solas. Antes vivían en main.py.
"""

import difflib
import re
from datetime import date, datetime

# Un monto es una secuencia de dígitos, opcionalmente agrupada de a 3 con
# "." o "," como separador de miles (ej. "15000", "15.000", "1.500.000").
_AMOUNT_PATTERN = re.compile(r"^\d{1,3}([.,]\d{3})*$|^\d+$")

# "#palabra" en cualquier lugar del texto; un "#" suelto cuenta como sin categoría.
_CATEGORY_PATTERN = re.compile(r"#(\S*)")

# "$" pegado o separado por espacios de un número: "$57000", "$ 57000".
_DOLLAR_PATTERN = re.compile(r"\$\s*(?=\d)")


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
    forma "<prefijo> monto desc", más una "#categoria" opcional.

    Lo comparten gastos e ingresos: ambos tienen el mismo formato. También
    acepta el orden invertido ("<prefijo> desc monto", ej. "gasto: nafta
    12000"): es un error real y repetido — así se habla en la vida real,
    diciendo primero de qué es el gasto y después cuánto fue.

    La categoría es opcional: la primera "#palabra" del texto, en cualquier
    lugar ("gasto: #tarjeta 57000 carrefour" vale igual que al final). Es
    una sola palabra a propósito: antes podía tener varias ("#gastos
    fijos"), pero entonces solo funcionaba al final, y escrita en el medio
    se comía la descripción sin avisar. Para varias palabras, con guion:
    "#gastos-fijos".

    El monto acepta un "$" adelante ("$57000" o "$ 57000"): es como se
    escribe un precio sin pensarlo.

    La categoría se guarda siempre en minúsculas: sin esto, "Nafta" y
    "nafta" quedan como dos categorías distintas sin ninguna forma de
    notar el error hasta que ya hay registros repartidos entre las dos.
    """

    if not text.lower().startswith(prefix):
        return None

    content = text[len(prefix) :].strip()

    if not content:
        return None

    category = None
    category_match = _CATEGORY_PATTERN.search(content)

    if category_match:
        category = category_match.group(1).lower() or None
        content = (
            content[: category_match.start()] + " " + content[category_match.end() :]
        )

    content = " ".join(_DOLLAR_PATTERN.sub("", content).split())

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
