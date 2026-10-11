"""Interfaz web local de Atlas (opcional).

No reemplaza la terminal: usa las mismas funciones de atlas.main, solo
cambia cómo se piden y se muestran los datos. main.py sigue funcionando
igual que siempre, en paralelo.

Corre solo en 127.0.0.1 (esta misma computadora). No tiene usuarios ni
login porque es de una sola persona, local, sin exponerse a una red. Si
algún día se expone a la red local o a internet, hay que revisar esto
primero (autenticación, secret_key, debug).
"""

import sys
from pathlib import Path

# Si se ejecuta como script (`python src/atlas/web.py`) en vez de módulo
# (`python -m atlas.web`), el paquete `atlas` todavía no está en sys.path.
# Lo agregamos antes de importar nada de atlas.*, para que arranque igual
# que main.py sin necesidad de un paso extra.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import date  # noqa: E402

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)  # noqa: E402

from atlas.main import (  # noqa: E402
    calculate_balance,
    calculate_monthly_balance,
    delete_entry,
    detect_entry_type,
    filter_by_period,
    find_entry,
    format_entry_summary,
    format_money,
    load_entries,
    mark_task_done,
    save_entry,
)

app = Flask(__name__)
# No hay nada que proteger más allá de lo que ya protege correr en
# localhost sin exponerse a la red, así que una clave fija alcanza.
app.secret_key = "atlas-local-dev"


@app.route("/")
def index():
    """Panel principal: captura, filtros, listado y balance."""

    tipo = request.args.get("tipo") or None
    periodo = request.args.get("periodo") or None

    entries = load_entries()

    if tipo:
        entries = [entry for entry in entries if entry.get("type") == tipo]

    entries = filter_by_period(entries, periodo)
    entries = list(reversed(entries[-20:]))

    return render_template(
        "index.html",
        entries=entries,
        tipo=tipo,
        periodo=periodo,
        balance_hoy=calculate_balance(load_entries(), date.today()),
        balance_mes=calculate_monthly_balance(load_entries(), date.today()),
        format_money=format_money,
        format_entry_summary=format_entry_summary,
    )


@app.route("/agregar", methods=["POST"])
def agregar():
    """Guarda un registro nuevo, igual que escribir algo en la terminal."""

    texto = request.form.get("texto", "").strip()

    if texto:
        entry_type = detect_entry_type(texto)

        try:
            save_entry(entry_type, texto)
            flash(f"Guardado como {entry_type}.", "ok")

        except ValueError as error:
            flash(str(error), "error")

    return redirect(url_for("index"))


@app.route("/borrar/<int:entry_id>")
def confirmar_borrado(entry_id):
    """Pantalla de confirmación antes de borrar de verdad.

    Un GET nunca borra nada por sí solo; hace falta el POST del formulario
    de esta misma página para que el borrado sea real.
    """

    entry = find_entry(entry_id)

    if entry is None:
        flash(f"No encontré ningún registro con id #{entry_id}.", "error")
        return redirect(url_for("index"))

    return render_template(
        "confirmar_borrado.html",
        entry=entry,
        format_entry_summary=format_entry_summary,
    )


@app.route("/borrar/<int:entry_id>", methods=["POST"])
def borrar(entry_id):
    """Borra de verdad, solo llega acá después de confirmar."""

    if delete_entry(entry_id):
        flash(f"Borré el registro #{entry_id}.", "ok")
    else:
        flash(f"El registro #{entry_id} ya no existía.", "error")

    return redirect(url_for("index"))


@app.route("/tareas/<int:entry_id>/hecha", methods=["POST"])
def hecha(entry_id):
    """Marca una tarea como completada."""

    resultado = mark_task_done(entry_id)

    if resultado == "ok":
        flash(f"Marqué la tarea #{entry_id} como hecha.", "ok")
    elif resultado == "no_es_tarea":
        flash(f"El registro #{entry_id} no es una tarea.", "error")
    else:
        flash(f"No encontré ninguna tarea con id #{entry_id}.", "error")

    return redirect(url_for("index"))


def main() -> None:
    """Arranca el servidor web local, solo accesible desde esta computadora."""

    app.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    main()
