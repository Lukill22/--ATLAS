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

    def test_filtro_por_tipo(self):
        with archivo_temporal():
            cliente().post("/agregar", data={"texto": "tarea: comprar arroz"})
            cliente().post("/agregar", data={"texto": "idea: mejorar atlas"})

            respuesta = cliente().get("/?tipo=tarea")

            assert b"comprar arroz" in respuesta.data
            assert b"mejorar atlas" not in respuesta.data

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
