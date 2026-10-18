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
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from atlas.main import (  # noqa: E402
    build_corrected_text,
    delete_entry,
    detect_entry_type,
    detect_probable_typo,
    find_entry,
    format_entry_summary,
    handle_command,
    save_entry,
)

TOKEN = os.environ.get("ATLAS_TELEGRAM_TOKEN")

# Confirmaciones pendientes por chat (típicamente un solo chat: el del
# usuario). Vive en memoria mientras el script corre, igual que
# pending_typo en el loop de la terminal.
_pending_typo_by_chat: dict[int, tuple[str, str]] = {}


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
    """Confirma a Telegram que el toque del botón se procesó (saca el relojito)."""

    _call("answerCallbackQuery", payload={"callback_query_id": callback_query_id})


def _guardar_y_avisar(chat_id: int, entry_type: str, texto: str) -> None:
    try:
        save_entry(entry_type, texto)
        send_message(chat_id, f"Guardado como {entry_type}.")

    except ValueError as error:
        send_message(chat_id, str(error))


def process_text(chat_id: int, texto: str) -> None:
    """Procesa un mensaje de texto: resuelve una confirmación pendiente,
    ejecuta un comando, o lo trata como una captura nueva.
    """

    texto = texto.strip()

    if not texto:
        return

    if chat_id in _pending_typo_by_chat:
        original, corregido = _pending_typo_by_chat.pop(chat_id)

        if texto.lower() in {"si", "sí", "s"}:
            _guardar_y_avisar(chat_id, detect_entry_type(corregido), corregido)
        else:
            _guardar_y_avisar(chat_id, "nota", original)

        return

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

    _guardar_y_avisar(chat_id, entry_type, texto)


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

    if data == "typo_si":
        if chat_id in _pending_typo_by_chat:
            _original, corregido = _pending_typo_by_chat.pop(chat_id)
            _guardar_y_avisar(chat_id, detect_entry_type(corregido), corregido)
        return

    if data == "typo_no":
        if chat_id in _pending_typo_by_chat:
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


def run() -> None:
    """Arranca el loop de polling. Bloquea hasta Ctrl+C."""

    if not TOKEN:
        print(
            "Atlas: falta ATLAS_TELEGRAM_TOKEN. Creá un bot hablándole a "
            "@BotFather en Telegram, y exportá el token que te da antes de "
            "correr esto."
        )
        return

    print("Atlas: bot de Telegram escuchando. Ctrl+C para salir.")
    offset = 0

    while True:
        try:
            respuesta = _call("getUpdates", params={"offset": offset, "timeout": 30})

        except (urllib.error.URLError, TimeoutError) as error:
            print(
                f"Atlas: no pude consultar Telegram ({error}); reintento en unos segundos."
            )
            continue

        for update in respuesta.get("result", []):
            offset = update["update_id"] + 1

            try:
                if "callback_query" in update:
                    process_callback(update["callback_query"])
                elif "message" in update and "text" in update["message"]:
                    process_text(
                        update["message"]["chat"]["id"], update["message"]["text"]
                    )

            except Exception as error:  # noqa: BLE001 - no tirar abajo el bot
                # Un error procesando ESTE mensaje (ej. un fallo de red
                # mandando la respuesta) no debe matar el proceso entero:
                # ya avanzamos "offset", así que el próximo mensaje se
                # procesa normal en la siguiente vuelta.
                print(f"Atlas: error procesando un mensaje ({error}); sigo.")


if __name__ == "__main__":
    run()
