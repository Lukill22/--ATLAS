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
