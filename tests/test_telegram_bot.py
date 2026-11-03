"""Pruebas del bot de Telegram (src/atlas/telegram_bot.py).

No hablan con la API real de Telegram: mockean send_message/_answer_callback
y usan el mismo archivo_temporal() de conftest.py, así nunca tocan
data/entries.jsonl real.
"""

import contextlib
import io
import os
import re
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import patch

import pytest
from conftest import archivo_temporal

import atlas.telegram_bot as bot
from atlas.main import load_entries, save_entry


@pytest.fixture(autouse=True)
def _sin_confirmaciones_pendientes():
    """_pending_typo_by_chat es un diccionario global del módulo (vive
    mientras el bot corre, igual que pending_typo en la terminal). Sin
    esto, una confirmación sin resolver en un test se filtra al siguiente.
    """

    bot._pending_typo_by_chat.clear()
    yield
    bot._pending_typo_by_chat.clear()


class TestProcessTextStart:
    def test_start_no_se_guarda_y_saluda(self):
        # Bug real: Telegram manda "/start" solo al abrir el chat por
        # primera vez, y antes de este fix quedaba guardado como una nota.
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            bot.process_text(123, "/start")

            assert load_entries() == []
            assert "Atlas" in enviar.call_args[0][1]


class TestProcessTextCaptura:
    def test_gasto_valido_se_guarda_y_responde(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            bot.process_text(123, "gasto: 5000 pan")

            assert load_entries()[0]["amount"] == 5000
            enviar.assert_called_once_with(123, "Guardado como gasto.")

    def test_gasto_con_categoria_la_muestra_en_la_confirmacion(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            bot.process_text(123, "gasto: 5000 nafta #auto")

            enviar.assert_called_once_with(123, "Guardado como gasto (#auto).")

    def test_gasto_invalido_no_guarda_y_avisa_el_error(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            bot.process_text(123, "gasto: abc nafta")

            assert load_entries() == []
            assert "No pude detectar el monto" in enviar.call_args[0][1]

    def test_texto_vacio_no_hace_nada(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            bot.process_text(123, "   ")

            assert load_entries() == []
            enviar.assert_not_called()


class TestProcessTextTypo:
    def test_typo_no_guarda_nada_y_pregunta_con_botones(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            bot.process_text(123, "gasto 5000 pan")

            assert load_entries() == []
            chat_id, texto = enviar.call_args[0]
            assert chat_id == 123
            assert "gasto: 5000 pan" in texto
            botones = enviar.call_args[1]["botones"]
            assert botones == [("Sí", "typo_si"), ("No, es una nota", "typo_no")]

    def test_responder_si_como_texto_guarda_bien_tipado(self):
        with archivo_temporal(), patch.object(bot, "send_message"):
            bot.process_text(123, "gasto 5000 pan")
            bot.process_text(123, "si")

            entradas = load_entries()
            assert entradas[0]["type"] == "gasto"
            assert entradas[0]["amount"] == 5000

    def test_responder_no_como_texto_guarda_el_original_como_nota(self):
        with archivo_temporal(), patch.object(bot, "send_message"):
            bot.process_text(123, "gasto 5000 pan")
            bot.process_text(123, "no")

            entradas = load_entries()
            assert entradas[0]["type"] == "nota"
            assert entradas[0]["text"] == "gasto 5000 pan"

    def test_confirmar_con_boton_typo_si(self):
        with archivo_temporal(), patch.object(bot, "send_message"), patch.object(
            bot, "_answer_callback"
        ):
            bot.process_text(123, "gasto 5000 pan")
            bot.process_callback(
                {"id": "cb1", "message": {"chat": {"id": 123}}, "data": "typo_si"}
            )

            assert load_entries()[0]["type"] == "gasto"

    def test_rechazar_con_boton_typo_no(self):
        with archivo_temporal(), patch.object(bot, "send_message"), patch.object(
            bot, "_answer_callback"
        ):
            bot.process_text(123, "gasto 5000 pan")
            bot.process_callback(
                {"id": "cb1", "message": {"chat": {"id": 123}}, "data": "typo_no"}
            )

            assert load_entries()[0]["type"] == "nota"

    def test_otro_mensaje_en_vez_de_responder_se_procesa_y_no_se_pierde(self):
        # Caso real: en vez de contestar la pregunta, se reescribe bien el
        # gasto. Antes el original quedaba como nota y el gasto se perdía.
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            bot.process_text(123, "gasto 5000 pan")
            bot.process_text(123, "gasto: 5000 pan")

            entradas = load_entries()
            assert [entrada["type"] for entrada in entradas] == ["gasto"]
            avisos = [llamada[0][1] for llamada in enviar.call_args_list]
            assert 'No guardé "gasto 5000 pan" (quedó sin respuesta).' in avisos
            assert avisos[-1] == "Guardado como gasto."

    def test_boton_de_una_pregunta_vencida_avisa_en_vez_de_no_hacer_nada(self):
        # Caso real: el bot se reinició entre la pregunta y el toque del
        # botón, y tocar "Sí" no guardaba ni respondía nada.
        with archivo_temporal(), patch.object(
            bot, "send_message"
        ) as enviar, patch.object(bot, "_answer_callback"):
            bot.process_callback(
                {"id": "cb1", "message": {"chat": {"id": 123}}, "data": "typo_si"}
            )

            assert load_entries() == []
            assert "ya no está vigente" in enviar.call_args[0][1]

    def test_telegram_rechaza_confirmar_el_boton_y_igual_se_guarda(self):
        import urllib.error

        rechazo = urllib.error.HTTPError(
            "url", 400, "Bad Request: query is too old", None, None
        )

        with archivo_temporal(), patch.object(bot, "send_message"), patch.object(
            bot, "_call", side_effect=rechazo
        ), contextlib.redirect_stdout(io.StringIO()):
            bot.process_text(123, "gasto 5000 pan")
            bot.process_callback(
                {"id": "cb1", "message": {"chat": {"id": 123}}, "data": "typo_si"}
            )

            assert load_entries()[0]["type"] == "gasto"


class TestLog:
    def test_cada_linea_tiene_fecha_y_hora(self):
        salida = io.StringIO()

        with contextlib.redirect_stdout(salida):
            bot._log("Atlas: algo pasó")

        assert re.match(
            r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d Atlas: algo pasó$", salida.getvalue()
        )


class TestProcessTextComandos:
    def test_ayuda(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            bot.process_text(123, "ayuda")

            assert load_entries() == []
            assert "Comandos disponibles" in enviar.call_args[0][1]

    def test_balance_dia(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            bot.process_text(123, "balance dia")

            assert "Balance" in enviar.call_args[0][1]

    def test_borrar_pide_confirmacion_con_botones_y_no_borra_todavia(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            bot.process_text(123, "gasto: 5000 pan")
            entry_id = load_entries()[0]["id"]

            enviar.reset_mock()
            bot.process_text(123, f"borrar {entry_id}")

            assert len(load_entries()) == 1  # todavía no se borró
            botones = enviar.call_args[1]["botones"]
            assert botones == [
                ("Sí, borrar", f"borrar_si:{entry_id}"),
                ("Cancelar", "borrar_no"),
            ]


class TestProcessCallbackBorrar:
    def test_confirmar_borra_de_verdad(self):
        with archivo_temporal(), patch.object(bot, "send_message"), patch.object(
            bot, "_answer_callback"
        ):
            bot.process_text(123, "gasto: 5000 pan")
            entry_id = load_entries()[0]["id"]

            bot.process_callback(
                {
                    "id": "cb1",
                    "message": {"chat": {"id": 123}},
                    "data": f"borrar_si:{entry_id}",
                }
            )

            assert load_entries() == []

    def test_cancelar_no_borra_nada(self):
        with archivo_temporal(), patch.object(bot, "send_message"), patch.object(
            bot, "_answer_callback"
        ):
            bot.process_text(123, "gasto: 5000 pan")

            bot.process_callback(
                {"id": "cb1", "message": {"chat": {"id": 123}}, "data": "borrar_no"}
            )

            assert len(load_entries()) == 1


class TestRunResiliencia:
    def test_un_corte_de_conexion_no_mata_el_loop(self):
        # Bug real: ConnectionResetError no estaba en la lista de errores
        # absorbidos, así que un corte de conexión tiraba abajo todo el
        # bot. Ahora se absorbe como cualquier otro problema de red, y el
        # loop sigue a la siguiente vuelta.
        intentos = {"n": 0}

        def falso_call(metodo, params=None, payload=None):
            intentos["n"] += 1

            if intentos["n"] == 1:
                raise ConnectionResetError("corte simulado")

            raise RuntimeError("siguió a la segunda vuelta")

        with patch.object(bot, "TOKEN", "fake-token"), patch.object(
            bot, "_call", side_effect=falso_call
        ), patch.object(bot, "time"):
            with pytest.raises(RuntimeError, match="siguió a la segunda vuelta"):
                bot.run()

        assert intentos["n"] == 2


class TestRecordatorios:
    def test_crear_recordatorio_guarda_el_chat_id(self):
        with archivo_temporal(), patch.object(bot, "send_message"):
            bot.process_text(123, "recordatorio: 19/10 08:00 sacar la basura")

            entry = load_entries()[0]
            assert entry["type"] == "recordatorio"
            assert entry["chat_id"] == 123

    def test_avisar_recordatorios_vencidos_manda_el_mensaje(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            entry = save_entry(
                "recordatorio",
                "recordatorio: 19/10 08:00 sacar la basura",
                chat_id=123,
            )
            with patch.object(bot, "datetime") as fecha_falsa:
                fecha_falsa.now.return_value = datetime(2026, 10, 19, 8, 1)
                bot.avisar_recordatorios_vencidos()

            enviar.assert_called_once_with(123, "⏰ Recordatorio: sacar la basura")
            assert load_entries()[0]["notified"] is True
            assert load_entries()[0]["id"] == entry["id"]

    def test_no_vencido_todavia_no_avisa(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            save_entry(
                "recordatorio",
                "recordatorio: 19/10 08:00 sacar la basura",
                chat_id=123,
            )
            with patch.object(bot, "datetime") as fecha_falsa:
                fecha_falsa.now.return_value = datetime(2026, 10, 19, 7, 59)
                bot.avisar_recordatorios_vencidos()

            enviar.assert_not_called()
            assert load_entries()[0]["notified"] is False

    def test_recordatorio_sin_chat_id_se_marca_avisado_sin_mandar_nada(self):
        # Creado desde la terminal o la web: nadie a quien avisarle, pero
        # tampoco hay que seguir revisándolo para siempre.
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            save_entry("recordatorio", "recordatorio: 19/10 08:00 sacar la basura")

            with patch.object(bot, "datetime") as fecha_falsa:
                fecha_falsa.now.return_value = datetime(2026, 10, 19, 8, 1)
                bot.avisar_recordatorios_vencidos()

            enviar.assert_not_called()
            assert load_entries()[0]["notified"] is True


class TestBalanceDiario:
    def test_configurarlo_guarda_el_chat_id_y_confirma_la_hora(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            bot.process_text(123, "balance diario: 23:00")

            entry = load_entries()[0]
            assert entry["type"] == "balance_diario"
            assert entry["chat_id"] == 123
            assert "23:00" in enviar.call_args[0][1]

    def test_avisar_balances_diarios_manda_el_mensaje(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            save_entry("gasto", "gasto: 5000 pan")
            save_entry("balance_diario", "balance diario: 23:00", chat_id=123)

            with patch.object(bot, "datetime") as fecha_falsa:
                fecha_falsa.now.return_value = datetime(2026, 10, 19, 23, 1)
                bot.avisar_balances_diarios()

            chat_id, texto = enviar.call_args[0]
            assert chat_id == 123
            assert "Balance de hoy" in texto
            assert load_entries()[1]["last_sent_date"] == "2026-10-19"

    def test_no_llego_la_hora_todavia_no_avisa(self):
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            save_entry("balance_diario", "balance diario: 23:00", chat_id=123)

            with patch.object(bot, "datetime") as fecha_falsa:
                fecha_falsa.now.return_value = datetime(2026, 10, 19, 22, 59)
                bot.avisar_balances_diarios()

            enviar.assert_not_called()
            assert load_entries()[0]["last_sent_date"] is None

    def test_sin_chat_id_se_marca_enviado_sin_mandar_nada(self):
        # Creado desde la terminal o la web: nadie a quien avisarle, pero
        # tampoco hay que seguir revisándolo cada noche para siempre.
        with archivo_temporal(), patch.object(bot, "send_message") as enviar:
            save_entry("balance_diario", "balance diario: 23:00")

            with patch.object(bot, "datetime") as fecha_falsa:
                fecha_falsa.now.return_value = datetime(2026, 10, 19, 23, 1)
                bot.avisar_balances_diarios()

            enviar.assert_not_called()
            assert load_entries()[0]["last_sent_date"] == "2026-10-19"


@contextmanager
def chat_autorizado(valor):
    """Fija ATLAS_TELEGRAM_CHAT_ID durante la prueba (None = sin configurar)."""

    entorno = {} if valor is None else {"ATLAS_TELEGRAM_CHAT_ID": str(valor)}

    with patch.dict(os.environ, entorno):
        if valor is None:
            os.environ.pop("ATLAS_TELEGRAM_CHAT_ID", None)

        bot._unauthorized_logged.clear()
        yield
        bot._unauthorized_logged.clear()


def novedad_mensaje(chat_id, texto):
    return {"update_id": 1, "message": {"chat": {"id": chat_id}, "text": texto}}


def novedad_boton(chat_id, data):
    return {
        "update_id": 2,
        "callback_query": {
            "id": "abc",
            "data": data,
            "message": {"chat": {"id": chat_id}},
        },
    }


class TestAutorizacion:
    """Solo el chat configurado puede usar el bot; los demás se ignoran."""

    def test_mensaje_del_chat_autorizado_se_procesa(self):
        with chat_autorizado(123), patch.object(bot, "process_text") as procesar:
            bot.handle_update(novedad_mensaje(123, "balance dia"))

            procesar.assert_called_once_with(123, "balance dia")

    def test_mensaje_de_otro_chat_se_ignora_sin_responder(self):
        with chat_autorizado(123), patch.object(bot, "process_text") as procesar:
            with patch.object(bot, "send_message") as enviar:
                bot.handle_update(novedad_mensaje(999, "total gastos"))

            procesar.assert_not_called()
            enviar.assert_not_called()

    def test_sin_configurar_no_le_responde_a_nadie(self):
        with chat_autorizado(None), patch.object(bot, "process_text") as procesar:
            bot.handle_update(novedad_mensaje(123, "listar"))

            procesar.assert_not_called()

    def test_configuracion_invalida_cuenta_como_sin_configurar(self):
        with chat_autorizado("no-es-un-numero"), patch.object(bot, "process_text") as p:
            bot.handle_update(novedad_mensaje(123, "listar"))

            p.assert_not_called()

    def test_boton_de_otro_chat_no_borra_nada(self):
        # El caso más peligroso: un toque de "Sí, borrar" de un chat ajeno.
        with archivo_temporal(), chat_autorizado(123):
            entry = save_entry("nota", "no me borres")

            with patch.object(bot, "send_message"), patch.object(bot, "_call"):
                bot.handle_update(novedad_boton(999, f"borrar_si:{entry['id']}"))

            assert len(load_entries()) == 1

    def test_boton_del_chat_autorizado_se_procesa(self):
        with chat_autorizado(123), patch.object(bot, "process_callback") as procesar:
            novedad = novedad_boton(123, "borrar_no")
            bot.handle_update(novedad)

            procesar.assert_called_once_with(novedad["callback_query"])

    def test_novedad_sin_chat_se_ignora(self):
        with chat_autorizado(123), patch.object(bot, "process_text") as procesar:
            bot.handle_update({"update_id": 3, "edited_message": {}})

            procesar.assert_not_called()

    def test_el_aviso_muestra_el_chat_id_pero_no_el_contenido_y_una_sola_vez(self):
        with chat_autorizado(123):
            salida = io.StringIO()

            with contextlib.redirect_stdout(salida):
                bot.handle_update(novedad_mensaje(999, "mi clave es hunter2"))
                bot.handle_update(novedad_mensaje(999, "otra vez"))

            texto = salida.getvalue()
            assert "999" in texto
            assert "ATLAS_TELEGRAM_CHAT_ID=999" in texto
            assert "hunter2" not in texto
            assert texto.count("ignoré un mensaje") == 1
