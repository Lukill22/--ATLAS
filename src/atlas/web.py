"""Interfaz web local de Atlas (opcional).

No reemplaza la terminal: usa las mismas funciones de atlas.main, solo
cambia cómo se piden y se muestran los datos. main.py sigue funcionando
igual que siempre, en paralelo.

Escucha en la red local (no solo en esta computadora) para poder abrirla
desde el celular. Esto fue una decisión explícita, no un descuido: hoy NO
hay ningún login ni contraseña, así que cualquier otro dispositivo en la
misma red podría ver y borrar los datos mientras el servidor esté
corriendo. Si se expone a internet (no solo a la red de casa), hay que
resolver autenticación antes.
"""

import socket
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
    build_corrected_text,
    calculate_balance,
    calculate_monthly_balance,
    delete_entry,
    detect_entry_type,
    detect_probable_typo,
    filter_by_period,
    find_entry,
    format_entry_summary,
    format_money,
    handle_command,
    load_entries,
    mark_task_done,
    save_entry,
)

app = Flask(__name__)
# Esta clave firma las cookies de sesión (flash messages), no autentica a
# nadie: no hay login. No protege los datos de otros dispositivos en la
# misma red; eso queda pendiente si hace falta en el futuro.
app.secret_key = "atlas-local-dev"


# Orden y etiqueta de cada sección. Mismo orden que HELP_TEXT.
_SECCIONES = [
    ("gasto", "Gastos"),
    ("ingreso", "Ingresos"),
    ("tarea", "Tareas"),
    ("idea", "Ideas"),
    ("nota", "Notas"),
    ("recordatorio", "Recordatorios"),
    ("balance_diario", "Balance diario"),
]

_MAX_POR_SECCION = 10


def _render_index(pendiente=None, respuesta=None, respuesta_es_ayuda=False):
    """Arma el panel principal, dividido en una sección por tipo.

    pendiente: dict {"original": ..., "corregido": ...} que hace aparecer
    la burbuja de confirmación de typo en vez de guardar directo.
    respuesta: texto de respuesta a un comando (ayuda, listar, balance,
    etc.), para mostrar como una burbuja de "dijo Atlas".
    respuesta_es_ayuda: la lista de comandos es larga y no aporta nada
    verla siempre desplegada, así que se muestra colapsada por defecto
    (el resto de las respuestas, como un balance, se muestran abiertas).
    """

    periodo = request.args.get("periodo") or None

    entries = filter_by_period(load_entries(), periodo)

    # Registros guardados antes de que existieran los ids no tienen "id".
    # Garantizamos que la clave siempre exista (en None si no estaba) para
    # que la plantilla pueda chequear "entry.id is not none" de forma
    # confiable, en vez de que Jinja2 trate el atributo como indefinido.
    entries = [dict(entry, id=entry.get("id")) for entry in entries]

    secciones = []

    for tipo, etiqueta in _SECCIONES:
        de_este_tipo = [entry for entry in entries if entry.get("type") == tipo]
        secciones.append(
            {
                "tipo": tipo,
                "etiqueta": etiqueta,
                "entries": list(reversed(de_este_tipo[-_MAX_POR_SECCION:])),
            }
        )

    return render_template(
        "index.html",
        secciones=secciones,
        periodo=periodo,
        pendiente=pendiente,
        respuesta=respuesta,
        respuesta_es_ayuda=respuesta_es_ayuda,
        balance_hoy=calculate_balance(load_entries(), date.today()),
        balance_mes=calculate_monthly_balance(load_entries(), date.today()),
        format_money=format_money,
        format_entry_summary=format_entry_summary,
    )


@app.route("/")
def index():
    """Panel principal: captura, filtros, listado y balance."""

    return _render_index()


def _guardar_y_avisar(entry_type: str, texto: str) -> None:
    """Guarda un registro y deja el resultado como mensaje flash."""

    try:
        save_entry(entry_type, texto)
        # "balance_diario" se guarda así por ser el mismo nombre que usa
        # el resto del código (save_entry, _SECCIONES, etc.), pero no es
        # un texto pensado para mostrar: reemplazamos el "_" por un
        # espacio para que el mensaje se lea natural.
        flash(f"Guardado como {entry_type.replace('_', ' ')}.", "ok")

    except ValueError as error:
        flash(str(error), "error")


@app.route("/agregar", methods=["POST"])
def agregar():
    """Procesa lo que se escribió en el composer: un comando (ayuda,
    listar, balance, borrar, etc.) o una captura nueva.

    Si el texto parece un error de tipeo de un prefijo conocido (sin ":",
    en plural, o con un typo real), no guarda nada todavía: muestra la
    misma pregunta que haría la terminal, y la respuesta se resuelve en
    /agregar/confirmar.
    """

    texto = request.form.get("texto", "").strip()

    if not texto:
        return redirect(url_for("index"))

    resultado_comando = handle_command(texto)

    if resultado_comando is not None:
        if "redirect_borrar" in resultado_comando:
            return redirect(
                url_for(
                    "confirmar_borrado", entry_id=resultado_comando["redirect_borrar"]
                )
            )

        return _render_index(
            respuesta=resultado_comando["respuesta"],
            respuesta_es_ayuda=resultado_comando.get("es_ayuda", False),
        )

    entry_type = detect_entry_type(texto)

    if entry_type == "nota":
        formato_sugerido = detect_probable_typo(texto)

        if formato_sugerido is not None:
            texto_corregido = build_corrected_text(texto, formato_sugerido)
            return _render_index(
                pendiente={"original": texto, "corregido": texto_corregido}
            )

    _guardar_y_avisar(entry_type, texto)

    return redirect(url_for("index"))


@app.route("/agregar/confirmar", methods=["POST"])
def confirmar_agregar():
    """Resuelve la pregunta "¿quisiste decir...?" del composer."""

    texto_original = request.form.get("texto_original", "")
    texto_corregido = request.form.get("texto_corregido", "")
    respuesta = request.form.get("respuesta", "")

    if respuesta == "si":
        _guardar_y_avisar(detect_entry_type(texto_corregido), texto_corregido)
    else:
        _guardar_y_avisar("nota", texto_original)

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


def _lan_ip() -> str | None:
    """Intenta averiguar la IP de esta computadora en la red local.

    No manda ningún dato: abre un socket UDP hacia una IP pública para que
    el sistema operativo elija qué interfaz de red usaría, y lee esa IP.
    None si no se puede determinar (ej. sin red).
    """

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]

    except OSError:
        return None


def main() -> None:
    """Arranca el servidor web, accesible desde esta computadora y desde
    cualquier otro dispositivo en la misma red local (ver advertencia
    arriba: no hay contraseña).
    """

    puerto = 5000
    ip_red_local = _lan_ip()

    print("Atlas: interfaz web arrancando.")
    print(f"  En esta computadora: http://127.0.0.1:{puerto}/")

    if ip_red_local:
        print(f"  Desde el celular (misma wifi): http://{ip_red_local}:{puerto}/")

    print(
        "  Atención: no hay contraseña. Cualquiera en esta red podría "
        "ver y borrar los datos mientras esto esté corriendo.\n"
    )

    app.run(host="0.0.0.0", port=puerto, debug=True)


if __name__ == "__main__":
    main()
