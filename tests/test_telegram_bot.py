"""Pruebas del bot de Telegram (src/atlas/telegram_bot.py).

No hablan con la API real de Telegram: mockean send_message/_answer_callback
y usan el mismo archivo_temporal() de conftest.py, así nunca tocan
data/entries.jsonl real.
"""

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
