"""Cálculos sobre listas de registros: balances, totales, períodos y avisos.

Son funciones puras: reciben los registros ya leídos y devuelven un resultado,
sin leer ni escribir archivos. Antes vivían en main.py.
"""

from datetime import date, datetime, timedelta


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


# La paleta de colores validada (contraste y daltonismo) solo tiene 8
# colores de identidad; más categorías reales que esto no tiene sentido
# visualmente (se volverían indistinguibles), así que las más chicas se
# juntan en "Otras" en vez de inventar un noveno color.
_MAX_CATEGORIAS_CON_COLOR_PROPIO = 8


def group_by_category(entries: list[dict], entry_type: str) -> list[dict]:
    """Agrupa los gastos o ingresos por categoría y suma los montos.

    Los registros sin categoría se agrupan en "Sin categoría". Si hay más
    de 8 categorías reales, las más chicas (por monto) se juntan en
    "Otras". Devuelve una lista de {"categoria": ..., "total": ...},
    ordenada de mayor a menor monto.
    """

    totales: dict[str, int] = {}

    for entry in entries:
        if entry.get("type") != entry_type:
            continue

        amount = entry.get("amount")

        if not isinstance(amount, int | float):
            continue

        categoria = entry.get("categoria") or "Sin categoría"
        totales[categoria] = totales.get(categoria, 0) + amount

    items = sorted(
        (
            {"categoria": categoria, "total": total}
            for categoria, total in totales.items()
        ),
        key=lambda item: item["total"],
        reverse=True,
    )

    categorias_reales = [item for item in items if item["categoria"] != "Sin categoría"]

    if len(categorias_reales) <= _MAX_CATEGORIAS_CON_COLOR_PROPIO:
        return items

    principales = categorias_reales[:_MAX_CATEGORIAS_CON_COLOR_PROPIO]
    resto = categorias_reales[_MAX_CATEGORIAS_CON_COLOR_PROPIO:]
    sin_categoria = [item for item in items if item["categoria"] == "Sin categoría"]

    resultado = (
        principales
        + [{"categoria": "Otras", "total": sum(item["total"] for item in resto)}]
        + sin_categoria
    )

    return sorted(resultado, key=lambda item: item["total"], reverse=True)


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
