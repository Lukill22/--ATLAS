"""Formato de salida: cómo se muestran montos, registros y resúmenes.

Son funciones puras: devuelven texto, no imprimen ni leen archivos. Antes
vivían en main.py.
"""

from datetime import date, datetime


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


HELP_TEXT = """Comandos disponibles:

  listar  (o: listar gastos / ingresos / tareas / notas / recordatorios)
  listar hoy / mes
  total gastos / ingresos
  balance dia / semana / mes / total
  borrar <id>
  hecha <id>
  backup

Para anotar:

  comida 7000
  gasto: 5000 nafta #auto
  ingreso: 30000 uber
  tarea: comprar pan"""


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
