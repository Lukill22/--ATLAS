"""Pruebas de las rutas de la interfaz web (src/atlas/web.py).

Usan el test client de Flask (no levantan un servidor real) y el mismo
archivo_temporal() de conftest.py, así nunca tocan data/entries.jsonl ni
data/memory.json reales.
"""

from conftest import archivo_temporal

from atlas.main import load_entries
from atlas.web import app


def cliente():
    app.testing = True
    return app.test_client()


class TestIndex:
    def test_pagina_principal_carga(self):
        with archivo_temporal():
            respuesta = cliente().get("/")

            assert respuesta.status_code == 200
            assert b"Atlas" in respuesta.data

    def test_muestra_un_registro_guardado(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "gasto: 5000 pan"})

            respuesta = cliente().get("/")

            assert b"pan" in respuesta.data
            assert "$5.000".encode("utf-8") in respuesta.data

    def test_las_secciones_estan_divididas_por_tipo(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "tarea: comprar arroz"})
            cliente().post("/agregar", data={"texto": "idea: mejorar atlas"})

            html = cliente().get("/").data.decode("utf-8")

            # Cada registro aparece dentro del panel de pestaña de su
            # propio tipo, no en el de otro tipo. Se busca el div real
            # (class="tab-panel panel-X"), no la regla de CSS del mismo
            # nombre que aparece antes, en el <style>.
            panel_tarea = html.split('class="tab-panel panel-tarea"')[1].split(
                'class="tab-panel panel-idea"'
            )[0]
            panel_idea = html.split('class="tab-panel panel-idea"')[1].split(
                'class="tab-panel panel-nota"'
            )[0]

            assert "comprar arroz" in panel_tarea
            assert "mejorar atlas" not in panel_tarea
            assert "mejorar atlas" in panel_idea
            assert "comprar arroz" not in panel_idea

    def test_filtro_por_periodo(self):
        with archivo_temporal() as ruta:
            ruta.write_text(
                '{"id": 1, "created_at": "2020-01-01T10:00:00", "type": '
                '"tarea", "text": "tarea: vieja"}\n',
                encoding="utf-8",
            )
            cliente().post("/agregar", data={"texto": "tarea: de hoy"})

            respuesta = cliente().get("/?periodo=hoy")

            assert b"de hoy" in respuesta.data
            assert b"vieja" not in respuesta.data

    def test_no_rompe_con_una_tarea_vieja_sin_id(self):
        # Bug real: entradas guardadas antes de que existiera el id (de
        # cuando se guardaba solo con append, sin pasar por save_entry
        # actual) rompían la página entera con un 500 al intentar armar el
        # botón "Hecha" con un id inexistente.
        with archivo_temporal() as ruta:
            ruta.write_text(
                '{"created_at": "2026-10-11T17:57:11", "type": "tarea", '
                '"text": "tarea: tomar mates"}\n',
                encoding="utf-8",
            )

            respuesta = cliente().get("/")

            assert respuesta.status_code == 200
            assert b"tomar mates" in respuesta.data
            assert b"Hecha" not in respuesta.data


class TestAgregar:
    def test_guarda_un_gasto_valido(self):
        with archivo_temporal():
            respuesta = cliente().post(
                "/agregar", data={"texto": "gasto: 5000 pan"}, follow_redirects=True
            )

            assert respuesta.status_code == 200
            assert len(load_entries()) == 1
            assert load_entries()[0]["amount"] == 5000

    def test_gasto_invalido_no_guarda_nada_y_muestra_error(self):
        with archivo_temporal():
            respuesta = cliente().post(
                "/agregar", data={"texto": "gasto: abc nafta"}, follow_redirects=True
            )

            assert load_entries() == []
            assert b"No pude detectar el monto" in respuesta.data

    def test_texto_vacio_no_guarda_nada(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "   "})

            assert load_entries() == []

    def test_probable_typo_no_guarda_nada_todavia_y_pregunta(self):
        with archivo_temporal():
            respuesta = cliente().post("/agregar", data={"texto": "gasto 5000 pan"})

            assert load_entries() == []
            assert b"gasto: 5000 pan" in respuesta.data

    def test_texto_sin_relacion_se_guarda_directo_como_nota(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "se me ocurrió algo"})

            assert load_entries()[0]["type"] == "nota"


class TestConfirmarAgregar:
    def test_responder_si_guarda_bien_tipado(self):
        with archivo_temporal():
            cliente().post(
                "/agregar/confirmar",
                data={
                    "texto_original": "gasto 5000 pan",
                    "texto_corregido": "gasto: 5000 pan",
                    "respuesta": "si",
                },
            )

            entradas = load_entries()
            assert entradas[0]["type"] == "gasto"
            assert entradas[0]["amount"] == 5000

    def test_responder_no_guarda_el_original_como_nota(self):
        with archivo_temporal():
            cliente().post(
                "/agregar/confirmar",
                data={
                    "texto_original": "gasto 5000 pan",
                    "texto_corregido": "gasto: 5000 pan",
                    "respuesta": "no",
                },
            )

            entradas = load_entries()
            assert entradas[0]["type"] == "nota"
            assert entradas[0]["text"] == "gasto 5000 pan"


class TestBorrar:
    def test_la_pagina_de_confirmacion_no_borra_nada(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "gasto: 5000 pan"})
            entry_id = load_entries()[0]["id"]

            respuesta = cliente().get(f"/borrar/{entry_id}")

            assert respuesta.status_code == 200
            assert len(load_entries()) == 1
            assert b"Borrar" in respuesta.data or b"borrar" in respuesta.data

    def test_el_post_borra_de_verdad(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "gasto: 5000 pan"})
            entry_id = load_entries()[0]["id"]

            cliente().post(f"/borrar/{entry_id}")

            assert load_entries() == []

    def test_borrar_un_id_inexistente_no_rompe_nada(self):
        with archivo_temporal():
            respuesta = cliente().post("/borrar/999", follow_redirects=True)

            assert respuesta.status_code == 200


class TestComandosEnElComposer:
    """El composer entiende los mismos comandos que la terminal, no solo
    capturas nuevas (gasto/tarea/idea/nota)."""

    def test_ayuda_no_guarda_nada_y_responde(self):
        with archivo_temporal():
            respuesta = cliente().post("/agregar", data={"texto": "ayuda"})

            assert load_entries() == []
            assert b"Comandos disponibles" in respuesta.data

    def test_ayuda_aparece_colapsada_por_defecto(self):
        # La lista de comandos es larga; se muestra colapsada (sin "open")
        # para no abrirse siempre expandida, a diferencia de respuestas
        # cortas como un balance.
        with archivo_temporal():
            html = (
                cliente().post("/agregar", data={"texto": "ayuda"}).data.decode("utf-8")
            )

            assert '<details class="respuesta" >' in html

    def test_total_gastos(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "gasto: 5000 pan"})

            respuesta = cliente().post("/agregar", data={"texto": "total gastos"})

            assert "$5.000".encode("utf-8") in respuesta.data
            assert len(load_entries()) == 1  # no agregó un segundo registro

    def test_balance_dia_aparece_abierto(self):
        with archivo_temporal():
            html = (
                cliente()
                .post("/agregar", data={"texto": "balance dia"})
                .data.decode("utf-8")
            )

            assert '<details class="respuesta" open>' in html

    def test_balance_dia(self):
        with archivo_temporal():
            respuesta = cliente().post("/agregar", data={"texto": "balance dia"})

            assert b"Balance" in respuesta.data

    def test_backup_crea_copia(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "gasto: 5000 pan"})

            respuesta = cliente().post("/agregar", data={"texto": "backup"})

            assert b"Copia de seguridad guardada" in respuesta.data

    def test_crear_recordatorio_y_listarlo(self):
        with archivo_temporal():
            cliente().post(
                "/agregar",
                data={"texto": "recordatorio: 19/10 08:00 sacar la basura"},
            )

            respuesta = cliente().post(
                "/agregar", data={"texto": "listar recordatorios"}
            )

            assert b"sacar la basura" in respuesta.data
            assert load_entries()[0]["type"] == "recordatorio"
            # Creado desde la web, sin chat_id: no hay a quien avisarle.
            assert "chat_id" not in load_entries()[0]

    def test_crear_balance_diario_y_listarlo(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "balance diario: 23:00"})

            respuesta = cliente().post("/agregar", data={"texto": "listar"})

            assert b"23:00" in respuesta.data
            assert load_entries()[0]["type"] == "balance_diario"
            # Creado desde la web, sin chat_id: no hay a quien avisarle.
            assert "chat_id" not in load_entries()[0]

    def test_listar_tareas(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "tarea: comprar arroz"})

            respuesta = cliente().post("/agregar", data={"texto": "listar tareas"})

            assert b"comprar arroz" in respuesta.data

    def test_hecha_por_id_desde_el_composer(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "tarea: comprar arroz"})
            entry_id = load_entries()[0]["id"]

            respuesta = cliente().post("/agregar", data={"texto": f"hecha {entry_id}"})

            assert load_entries()[0]["done"] is True
            assert b"Marqu" in respuesta.data

    def test_borrar_por_id_desde_el_composer_manda_a_confirmar(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "gasto: 5000 pan"})
            entry_id = load_entries()[0]["id"]

            respuesta = cliente().post("/agregar", data={"texto": f"borrar {entry_id}"})

            assert respuesta.status_code == 302
            assert f"/borrar/{entry_id}" in respuesta.headers["Location"]
            assert len(load_entries()) == 1  # todavía no se borró


class TestHecha:
    def test_marca_una_tarea_como_hecha(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "tarea: comprar arroz"})
            entry_id = load_entries()[0]["id"]

            cliente().post(f"/tareas/{entry_id}/hecha")

            assert load_entries()[0]["done"] is True

    def test_marcar_un_gasto_como_hecha_no_lo_modifica(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "gasto: 5000 pan"})
            entry_id = load_entries()[0]["id"]

            respuesta = cliente().post(
                f"/tareas/{entry_id}/hecha", follow_redirects=True
            )

            assert "done" not in load_entries()[0]
            assert b"no es una tarea" in respuesta.data
