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
    calculate_total_balance,
    calculate_weekly_balance,
    delete_entry,
    detect_entry_type,
    detect_probable_typo,
    filter_by_period,
    find_entry,
    format_entry_summary,
    format_money,
    format_saved_message,
    group_by_category,
    handle_command,
    load_entries,
    mark_task_done,
    merge_categories,
    save_entry,
    set_entry_category,
)

# Paleta categórica validada (contraste y daltonismo) para los colores de
# identidad de cada categoría real. "Sin categoría" y "Otras" usan grises
# reservados en vez de un color de identidad: no son categorías de
# verdad, son un "no sé"/"junté el resto".
_PALETA_CATEGORIAS = [
    "#2a78d6",  # azul
    "#eb6834",  # naranja
    "#1baf7a",  # aqua
    "#eda100",  # amarillo
    "#e87ba4",  # magenta
    "#008300",  # verde
    "#6250d6",  # violeta
    "#e34948",  # rojo
]
_GRIS_SIN_CATEGORIA = "#aba99f"
_GRIS_OTRAS = "#7a7870"


def _texto_legible_sobre(color_hex: str) -> str:
    """Blanco o gris oscuro, el que mejor se lea sobre ese color de
    fondo (luminancia aproximada, alcanza para una paleta chica y fija
    como esta — no hace falta un cálculo de contraste WCAG completo).
    """

    color_hex = color_hex.lstrip("#")
    r, g, b = (int(color_hex[i : i + 2], 16) for i in (0, 2, 4))
    luminancia = 0.299 * r + 0.587 * g + 0.114 * b

    return "#1a1a1a" if luminancia > 150 else "white"


def _con_color_y_porcentaje(items: list[dict]) -> list[dict]:
    """Agrega color, color de texto y porcentaje a cada item de
    group_by_category, listos para la barra apilada, su leyenda, y la
    pastilla de categoría de cada tarjeta.

    El color de cada categoría real se asigna en orden alfabético (no por
    monto): así una categoría no cambia de color solo porque este mes
    pasó a ser más chica que otra. "Sin categoría" y "Otras" siempre usan
    el mismo gris reservado.
    """

    categorias_reales = sorted(
        {item["categoria"] for item in items} - {"Sin categoría", "Otras"}
    )
    color_por_categoria = {
        categoria: _PALETA_CATEGORIAS[indice]
        for indice, categoria in enumerate(categorias_reales)
    }
    color_por_categoria["Sin categoría"] = _GRIS_SIN_CATEGORIA
    color_por_categoria["Otras"] = _GRIS_OTRAS

    total = sum(item["total"] for item in items)

    return [
        {
            **item,
            "color": color_por_categoria[item["categoria"]],
            "texto": _texto_legible_sobre(color_por_categoria[item["categoria"]]),
            "pct": round(item["total"] / total * 100) if total else 0,
        }
        for item in items
    ]


def _categorias_existentes(entry_type: str) -> list[str]:
    """Todas las categorías ya usadas alguna vez para ese tipo (gasto o
    ingreso), sin importar el filtro de período actual — unir o elegir
    una categoría debe poder usar cualquiera que exista, no solo las que
    aparecen en lo que se está viendo ahora.
    """

    return sorted(
        {
            entry["categoria"]
            for entry in load_entries()
            if entry.get("type") == entry_type and entry.get("categoria")
        }
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

    categorias_gasto = _con_color_y_porcentaje(group_by_category(entries, "gasto"))
    categorias_ingreso = _con_color_y_porcentaje(group_by_category(entries, "ingreso"))

    # Mismo color en la tarjeta que en la barra apilada: una misma
    # categoría se ve igual en todas partes de la página. Si una
    # categoría puntual quedó plegada en "Otras" (más de 8 categorías
    # reales), usa el gris de "Otras" como respaldo en vez de romper.
    _gris_otras = (_GRIS_OTRAS, _texto_legible_sobre(_GRIS_OTRAS))
    color_por_tipo = {
        "gasto": {
            item["categoria"]: (item["color"], item["texto"])
            for item in categorias_gasto
        },
        "ingreso": {
            item["categoria"]: (item["color"], item["texto"])
            for item in categorias_ingreso
        },
    }

    categorias_existentes = {
        "gasto": _categorias_existentes("gasto"),
        "ingreso": _categorias_existentes("ingreso"),
    }

    for entry in entries:
        if entry.get("type") not in ("gasto", "ingreso"):
            continue

        categoria = entry.get("categoria") or "Sin categoría"
        color, texto = color_por_tipo[entry["type"]].get(categoria, _gris_otras)
        entry["categoria_color"] = color
        entry["categoria_texto"] = texto
        entry["categorias_existentes"] = categorias_existentes[entry["type"]]

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
        balance_semana=calculate_weekly_balance(load_entries(), date.today()),
        balance_mes=calculate_monthly_balance(load_entries(), date.today()),
        balance_total=calculate_total_balance(load_entries()),
        categorias_gasto=categorias_gasto,
        categorias_ingreso=categorias_ingreso,
        categorias_existentes_gasto=categorias_existentes["gasto"],
        categorias_existentes_ingreso=categorias_existentes["ingreso"],
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
        entry = save_entry(entry_type, texto)
        flash(format_saved_message(entry_type, entry), "ok")

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


@app.route("/categoria/<int:entry_id>", methods=["POST"])
def cambiar_categoria(entry_id):
    """Cambia la categoría de un gasto o ingreso ya guardado.

    El formulario tiene un <select> con las categorías ya existentes y
    un campo de texto para escribir una nueva; si se escribió algo en el
    campo de texto, gana por sobre lo elegido en el <select>. Dejar los
    dos vacíos borra la categoría en vez de rechazar el pedido.
    """

    categoria_nueva = request.form.get("categoria_nueva", "").strip()
    categoria = categoria_nueva or request.form.get("categoria_existente", "")
    resultado = set_entry_category(entry_id, categoria)

    if resultado == "ok":
        flash(f"Categoría actualizada para el registro #{entry_id}.", "ok")
    elif resultado == "no_es_gasto_ni_ingreso":
        flash(f"El registro #{entry_id} no es un gasto ni un ingreso.", "error")
    else:
        flash(f"No encontré ningún registro con id #{entry_id}.", "error")

    return redirect(url_for("index"))


@app.route("/categorias/unir", methods=["POST"])
def unir_categorias():
    """Une dos categorías existentes de un mismo tipo (gasto o ingreso)
    en una sola — pensado para arreglar duplicados como "Nafta"/"nafta".
    """

    tipo = request.form.get("tipo", "")
    desde = request.form.get("desde", "")
    hacia = request.form.get("hacia", "")

    if tipo not in ("gasto", "ingreso"):
        flash("No pude unir: tipo inválido.", "error")
        return redirect(url_for("index"))

    cambiados = merge_categories(tipo, desde, hacia)

    if cambiados:
        flash(
            f'Unidas: {cambiados} registro(s) ahora son "{hacia.strip().lower()}".',
            "ok",
        )
    else:
        flash("No encontré registros para unir con esas categorías.", "error")

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
