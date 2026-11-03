"""Bot de Telegram para Atlas (opcional).

Deja capturar y consultar Atlas desde un chat de Telegram, sin abrir ninguna
app dedicada. Reusa exactamente la misma lógica que la terminal y la web
(save_entry, detect_entry_type, handle_command, etc.) — no duplica nada,
solo agrega un canal de entrada nuevo.

Usa "long polling": este script le pregunta a Telegram cada tanto si hay
mensajes nuevos, en vez de que Telegram le avise a un servidor público. Por
eso no necesita ningún servidor expuesto a internet ni configuración de
red — alcanza con tener este script corriendo (en la PC, o en el celular
con Termux).

El token del bot se lee de ATLAS_TELEGRAM_TOKEN (variable de entorno).
Nunca se versiona ni se hardcodea. Se crea gratis hablándole a @BotFather
en Telegram.

No usa ninguna librería nueva: la API de Telegram es HTTP + JSON simple,
alcanza con `urllib` de la librería estándar.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from atlas.main import (  # noqa: E402
    build_corrected_text,
    calculate_balance,
    delete_entry,
    detect_entry_type,
    detect_probable_typo,
    find_entry,
    format_balance_summary,
    format_entry_summary,
    format_saved_message,
    get_due_daily_balances,
    get_due_reminders,
    handle_command,
    infer_amount_type,
    load_entries,
    mark_daily_balance_sent,
    mark_reminder_notified,
    parse_untyped_amount,
    save_entry,
)

TOKEN = os.environ.get("ATLAS_TELEGRAM_TOKEN")


def _log(mensaje: str) -> None:
    """Escribe una línea en el log con fecha y hora.

    Sin la hora no se podía saber cuándo pasó un error, ni relacionarlo con
    un mensaje que no se guardó.
    """

    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {mensaje}")


# Confirmaciones pendientes por chat (típicamente un solo chat: el del
# usuario). Vive en memoria mientras el script corre, igual que
# pending_typo en el loop de la terminal.
_pending_typo_by_chat: dict[int, tuple[str, str]] = {}

# Montos sin prefijo con palabras que Atlas todavía no conoce ("tarjeta
# 57000"): se pregunta una vez si es gasto, ingreso o nota, y desde ahí
# infer_amount_type ya lo reconoce solo.
_pending_amount_by_chat: dict[int, str] = {}

_AMOUNT_TYPE_ANSWERS = {"gasto": "gasto", "ingreso": "ingreso", "nota": "nota"}


# Chats autorizados a usar el bot. Telegram deja que CUALQUIER persona le
# escriba a un bot si conoce su @usuario, así que sin esto cualquiera podría
# ver los gastos o borrar registros. Se configura con la variable de entorno
# ATLAS_TELEGRAM_CHAT_ID (el id numérico del chat del dueño). Si falta o no
# es un número, el bot NO le responde a nadie: es más seguro fallar cerrado.
_unauthorized_logged: set[int] = set()


def _allowed_chat_id() -> int | None:
    """Lee el chat autorizado desde el entorno, o None si no está bien configurado."""

    value = os.environ.get("ATLAS_TELEGRAM_CHAT_ID", "").strip()

    try:
        return int(value)

    except ValueError:
        return None


def is_authorized(chat_id: int) -> bool:
    """True solo si el chat es exactamente el configurado como autorizado."""

    allowed = _allowed_chat_id()

    return allowed is not None and chat_id == allowed


def _log_unauthorized(chat_id: int) -> None:
    """Deja constancia (una sola vez por chat) de un mensaje ignorado.

    Muestra solo el id del chat, nunca el contenido del mensaje, y es la
    forma de averiguar tu propio chat_id la primera vez que lo configurás.
    """

    if chat_id in _unauthorized_logged:
        return

    _unauthorized_logged.add(chat_id)
    _log(
        f"Atlas: ignoré un mensaje del chat {chat_id}, que no está autorizado. "
        f"Si es tu chat, configurá ATLAS_TELEGRAM_CHAT_ID={chat_id} y reiniciá el bot."
    )


def _chat_id_of(update: dict) -> int | None:
    """Id del chat de una novedad de Telegram (mensaje o toque de botón)."""

    if "callback_query" in update:
        return update["callback_query"].get("message", {}).get("chat", {}).get("id")

    if "message" in update:
        return update["message"].get("chat", {}).get("id")

    return None


def handle_update(update: dict) -> None:
    """Procesa una novedad de Telegram, pero solo si viene del chat autorizado.

    Es el único camino por el que entran mensajes y botones al bot: una
    novedad de un chat no autorizado se descarta sin responder nada.
    """

    chat_id = _chat_id_of(update)

    if chat_id is None:
        return

    if not is_authorized(chat_id):
        _log_unauthorized(chat_id)
        return

    if "callback_query" in update:
        process_callback(update["callback_query"])
    elif "text" in update.get("message", {}):
        process_text(chat_id, update["message"]["text"])


def _api_url(metodo: str) -> str:
    return f"https://api.telegram.org/bot{TOKEN}/{metodo}"


def _call(metodo: str, payload: dict | None = None, params: dict | None = None) -> dict:
    """Llama a un método de la API de Telegram. GET si no hay payload, POST si hay."""

    url = _api_url(metodo)

    if params:
        url += "?" + urllib.parse.urlencode(params)

    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    # Telegram mantiene la conexión abierta hasta este tiempo esperando
    # mensajes nuevos (long polling); el timeout de urlopen tiene que ser
    # mayor al "timeout" que le pedimos a Telegram en los params.
    request = urllib.request.Request(url, data=data, headers=headers)

    with urllib.request.urlopen(request, timeout=35) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def send_message(
    chat_id: int, texto: str, botones: list[tuple[str, str]] | None = None
) -> None:
    """Manda un mensaje de texto, opcionalmente con botones inline.

    botones: lista de (texto_del_boton, callback_data).
    """

    payload = {"chat_id": chat_id, "text": texto}

    if botones:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": texto_b, "callback_data": data}] for texto_b, data in botones
            ]
        }

    _call("sendMessage", payload=payload)


def _answer_callback(callback_query_id: str) -> None:
    """Confirma a Telegram que el toque del botón se procesó (saca el relojito).

    Telegram rechaza con 400 un botón tocado mucho después (ej. después de
    un reinicio). Es solo cosmético, así que no debe frenar el resto: antes
    cortaba el procesamiento del botón y no se guardaba ni respondía nada.
    """

    try:
        _call("answerCallbackQuery", payload={"callback_query_id": callback_query_id})

    except urllib.error.HTTPError as error:
        _log(f"Telegram rechazó confirmar un botón ({error}); sigo igual.")


def _guardar_y_avisar(chat_id: int, entry_type: str, texto: str) -> None:
    try:
        # chat_id siempre se guarda, aunque solo lo usen "recordatorio" y
        # "balance_diario": son los únicos tipos que necesitan saber a
        # quién avisarle después.
        entry = save_entry(entry_type, texto, chat_id=chat_id)

        if entry_type == "balance_diario":
            send_message(
                chat_id,
                f"Listo, te mando el balance todos los días a las {entry['hora']}.",
            )
        else:
            send_message(chat_id, format_saved_message(entry_type, entry))

    except ValueError as error:
        send_message(chat_id, str(error))


def process_text(chat_id: int, texto: str) -> None:
    """Procesa un mensaje de texto: resuelve una confirmación pendiente,
    ejecuta un comando, o lo trata como una captura nueva.
    """

    texto = texto.strip()

    if not texto:
        return

    if texto == "/start":
        # Telegram manda esto solo, la primera vez que se abre el chat con
        # el bot. No es algo que el usuario quiso anotar.
        send_message(
            chat_id,
            '¡Hola! Soy Atlas. Escribime algo como "gasto: 15000 nafta" '
            'o "tarea: comprar pan", o mandá "ayuda" para ver todos los '
            "comandos.",
        )
        return

    if chat_id in _pending_typo_by_chat:
        original, corregido = _pending_typo_by_chat.pop(chat_id)

        if texto.lower() in {"si", "sí", "s"}:
            _guardar_y_avisar(chat_id, detect_entry_type(corregido), corregido)
            return

        if texto.lower() in {"no", "n"}:
            _guardar_y_avisar(chat_id, "nota", original)
            return

        # Cualquier otra cosa es un mensaje nuevo, no una respuesta. Antes
        # se guardaba el original como nota y este mensaje se perdía sin
        # aviso; caso real: en vez de contestar, se reescribe bien el gasto.
        send_message(chat_id, f'No guardé "{original}" (quedó sin respuesta).')

    if chat_id in _pending_amount_by_chat:
        original = _pending_amount_by_chat.pop(chat_id)
        tipo = _AMOUNT_TYPE_ANSWERS.get(texto.lower())

        if tipo is not None:
            _guardar_como(chat_id, tipo, original)
            return

        # Igual que con la pregunta de arriba: es un mensaje nuevo.
        send_message(chat_id, f'No guardé "{original}" (quedó sin respuesta).')

    resultado = handle_command(texto)

    if resultado is not None:
        if "redirect_borrar" in resultado:
            _preguntar_borrado(chat_id, resultado["redirect_borrar"])
        else:
            send_message(chat_id, resultado["respuesta"])

        return

    entry_type = detect_entry_type(texto)

    if entry_type == "nota":
        formato_sugerido = detect_probable_typo(texto)

        if formato_sugerido is not None:
            corregido = build_corrected_text(texto, formato_sugerido)
            _pending_typo_by_chat[chat_id] = (texto, corregido)
            send_message(
                chat_id,
                f'¿Quisiste escribir "{corregido}"?',
                botones=[("Sí", "typo_si"), ("No, es una nota", "typo_no")],
            )
            return

        tipo_inferido = infer_amount_type(texto)

        if tipo_inferido is not None:
            _guardar_como(chat_id, tipo_inferido, texto)
            return

        if parse_untyped_amount(texto) is not None:
            _pending_amount_by_chat[chat_id] = texto
            send_message(
                chat_id,
                f'¿"{texto}" es un gasto o un ingreso?',
                botones=[
                    ("Gasto", "tipo_gasto"),
                    ("Ingreso", "tipo_ingreso"),
                    ("Es una nota", "tipo_nota"),
                ],
            )
            return

    _guardar_y_avisar(chat_id, entry_type, texto)


def _guardar_como(chat_id: int, tipo: str, texto: str) -> None:
    """Guarda un texto sin prefijo como gasto, ingreso o nota."""

    if tipo == "nota":
        _guardar_y_avisar(chat_id, "nota", texto)
    else:
        _guardar_y_avisar(chat_id, tipo, f"{tipo}: {texto}")


def _preguntar_borrado(chat_id: int, entry_id: int) -> None:
    entry = find_entry(entry_id)

    if entry is None:
        send_message(chat_id, f"No encontré ningún registro con id #{entry_id}.")
        return

    send_message(
        chat_id,
        f"¿Borrar #{entry_id} — {format_entry_summary(entry)}?",
        botones=[("Sí, borrar", f"borrar_si:{entry_id}"), ("Cancelar", "borrar_no")],
    )


def process_callback(callback_query: dict) -> None:
    """Procesa el toque de un botón inline."""

    chat_id = callback_query["message"]["chat"]["id"]
    data = callback_query["data"]
    _answer_callback(callback_query["id"])

    pregunta_vencida = (
        data in {"typo_si", "typo_no"} and chat_id not in _pending_typo_by_chat
    ) or (data.startswith("tipo_") and chat_id not in _pending_amount_by_chat)

    if pregunta_vencida:
        # Las preguntas viven en memoria: si el bot se reinició en el medio,
        # o ya se respondió, no hay nada que guardar. Antes no pasaba nada y
        # no avisaba.
        send_message(
            chat_id, "Esa pregunta ya no está vigente. Mandá el mensaje de nuevo."
        )
        return

    if data.startswith("tipo_"):
        texto = _pending_amount_by_chat.pop(chat_id)
        _guardar_como(chat_id, data.removeprefix("tipo_"), texto)
        return

    if data == "typo_si":
        _original, corregido = _pending_typo_by_chat.pop(chat_id)
        _guardar_y_avisar(chat_id, detect_entry_type(corregido), corregido)
        return

    if data == "typo_no":
        original, _corregido = _pending_typo_by_chat.pop(chat_id)
        _guardar_y_avisar(chat_id, "nota", original)
        return

    if data.startswith("borrar_si:"):
        entry_id = int(data.split(":", 1)[1])

        if delete_entry(entry_id):
            send_message(chat_id, f"Borré el registro #{entry_id}.")
        else:
            send_message(chat_id, f"El registro #{entry_id} ya no existía.")
        return

    if data == "borrar_no":
        send_message(chat_id, "Borrado cancelado.")


def avisar_recordatorios_vencidos() -> None:
    """Revisa si hay recordatorios vencidos y, si hay, avisa por Telegram.

    Se llama una vez por vuelta del loop de polling (cada ~30 segundos, o
    antes si hay mensajes nuevos) — no hace falta un hilo ni un proceso
    aparte, alcanza con sumarlo al loop que ya existe.
    """

    for entry in get_due_reminders(load_entries(), datetime.now()):
        chat_id = entry.get("chat_id")

        if chat_id is not None:
            send_message(chat_id, f"⏰ Recordatorio: {entry.get('description', '')}")

        # Se marca avisado igual sin chat_id (se creó desde la terminal o
        # la web): nadie a quien avisarle, pero tampoco hay que seguir
        # revisándolo en cada vuelta del loop para siempre.
        mark_reminder_notified(entry["id"])


def avisar_balances_diarios() -> None:
    """Revisa si hay algún balance diario automático pendiente de hoy y,
    si hay, lo manda. Mismo mecanismo que avisar_recordatorios_vencidos():
    se llama una vez por vuelta del loop de polling.
    """

    ahora = datetime.now()
    hoy = ahora.date().isoformat()

    for entry in get_due_daily_balances(load_entries(), ahora):
        chat_id = entry.get("chat_id")

        if chat_id is not None:
            balance = calculate_balance(load_entries(), date.today())
            send_message(chat_id, f"Balance de hoy:\n{format_balance_summary(balance)}")

        # Igual que con los recordatorios: se marca enviado aunque no haya
        # chat_id (creado desde la terminal o la web), para no seguir
        # revisándolo en cada vuelta del loop para siempre.
        mark_daily_balance_sent(entry["id"], hoy)


def run() -> None:
    """Arranca el loop de polling. Bloquea hasta Ctrl+C."""

    if not TOKEN:
        _log(
            "Atlas: falta ATLAS_TELEGRAM_TOKEN. Creá un bot hablándole a "
            "@BotFather en Telegram, y exportá el token que te da antes de "
            "correr esto."
        )
        return

    if _allowed_chat_id() is None:
        _log(
            "Atlas: ATENCIÓN: falta ATLAS_TELEGRAM_CHAT_ID (o no es un número). "
            "Por seguridad el bot NO le va a responder a nadie hasta que lo "
            "configures. Escribile algo al bot desde tu Telegram: acá en el log "
            "va a aparecer tu chat_id y qué variable configurar."
        )

    _log("Atlas: bot de Telegram escuchando. Ctrl+C para salir.")
    offset = 0

    while True:
        try:
            respuesta = _call("getUpdates", params={"offset": offset, "timeout": 30})

        except (urllib.error.URLError, OSError) as error:
            # OSError cubre tambien los cortes de conexion a nivel red
            # (ej. ConnectionResetError) que no son URLError/TimeoutError
            # pero igual pueden pasar en una conexion de larga duracion
            # como esta. Sin este catch, un corte de conexion comun
            # mataba todo el proceso.
            _log(
                f"Atlas: no pude consultar Telegram ({error}); reintento en unos segundos."
            )
            time.sleep(3)
            continue

        for update in respuesta.get("result", []):
            offset = update["update_id"] + 1

            try:
                handle_update(update)

            except Exception as error:  # noqa: BLE001 - no tirar abajo el bot
                # Un error procesando ESTE mensaje (ej. un fallo de red
                # mandando la respuesta) no debe matar el proceso entero:
                # ya avanzamos "offset", así que el próximo mensaje se
                # procesa normal en la siguiente vuelta.
                _log(f"Atlas: error procesando un mensaje ({error}); sigo.")

        try:
            avisar_recordatorios_vencidos()

        except Exception as error:  # noqa: BLE001 - no tirar abajo el bot
            _log(f"Atlas: error revisando recordatorios ({error}); sigo.")

        try:
            avisar_balances_diarios()

        except Exception as error:  # noqa: BLE001 - no tirar abajo el bot
            _log(f"Atlas: error revisando el balance diario ({error}); sigo.")


if __name__ == "__main__":
    run()
