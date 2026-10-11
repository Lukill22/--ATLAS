"""Pruebas de las funciones puras de `atlas.main`.

No cubren `main()` (el loop interactivo con `input`/`print`) porque mezcla
E/S con lógica; eso queda para cuando valga la pena separarlo.
"""

import json
import tempfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

import atlas.main as atlas_main
from atlas.main import (
    build_corrected_text,
    calculate_balance,
    calculate_monthly_balance,
    create_backup,
    delete_entry,
    detect_entry_type,
    detect_probable_typo,
    find_entry,
    format_money,
    load_entries,
    mark_task_done,
    normalize_list_type,
    parse_expense,
    parse_id_command,
    parse_income,
    save_entry,
)


@contextmanager
def archivo_temporal():
    """Redirige DATA_FILE a un archivo temporal durante la prueba.

    Así las pruebas de guardado y lectura nunca tocan `data/entries.jsonl`.
    """

    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "entries.jsonl"

        with patch.object(atlas_main, "DATA_FILE", ruta):
            yield ruta


class TestParseExpense:
    def test_monto_simple(self):
        assert parse_expense("gasto: 15000 nafta") == {
            "amount": 15000,
            "description": "nafta",
        }

    def test_monto_con_separador_de_miles(self):
        assert parse_expense("gasto: 1.500 pan") == {
            "amount": 1500,
            "description": "pan",
        }

    def test_sin_descripcion_usa_valor_por_defecto(self):
        resultado = parse_expense("gasto: 5000")
        assert resultado["description"] == "Sin descripción"

    def test_prefijo_en_mayusculas_tambien_parsea(self):
        # Bug real: detect_entry_type reconocía "Gasto:" como tipo "gasto",
        # pero parse_expense no le sacaba el prefijo por ser case-sensitive,
        # y terminaba devolviendo None con un error confuso para el usuario.
        assert parse_expense("Gasto: 15000 nafta") == {
            "amount": 15000,
            "description": "nafta",
        }

    def test_monto_ambiguo_tipo_decimal_se_rechaza(self):
        # Bug real: "15.5" se interpretaba como separador de miles y
        # corrompía el dato en silencio, guardando $15,50 como $15.500.
        # Ahora un monto con un solo dígito después del separador se
        # rechaza en vez de adivinar.
        assert parse_expense("gasto: 15.5 cafe") is None

    def test_monto_negativo_se_rechaza(self):
        assert parse_expense("gasto: -500 nafta") is None

    def test_monto_no_numerico_se_rechaza(self):
        assert parse_expense("gasto: abc nafta") is None

    def test_sin_contenido_se_rechaza(self):
        assert parse_expense("gasto:") is None

    def test_texto_sin_prefijo_se_rechaza(self):
        assert parse_expense("nafta 15000") is None


class TestDetectEntryType:
    def test_detecta_gasto(self):
        assert detect_entry_type("gasto: 15000 nafta") == "gasto"

    def test_detecta_gasto_sin_importar_mayusculas(self):
        assert detect_entry_type("Gasto: 15000 nafta") == "gasto"

    def test_detecta_tarea(self):
        assert detect_entry_type("tarea: comprar arroz") == "tarea"

    def test_detecta_idea(self):
        assert detect_entry_type("idea: crear módulo de estudio") == "idea"

    def test_texto_libre_es_nota(self):
        assert detect_entry_type("cualquier cosa") == "nota"


class TestDetectProbableTypo:
    # Bug real: "gastos: 400", "Gastos: 200", "listar gasto", etc. se
    # guardaban como nota sin ningún aviso porque no matcheaban el prefijo
    # exacto. detect_entry_type sigue exigiendo "gasto:" tal cual (eso no
    # cambia), pero ahora se puede avisar del probable error de tipeo.

    def test_sin_dos_puntos_sugiere_el_formato(self):
        assert detect_probable_typo("gasto 15000 nafta") == "gasto:"

    def test_en_plural_sugiere_el_formato(self):
        assert detect_probable_typo("gastos: 400") == "gasto:"

    def test_no_distingue_mayusculas(self):
        assert detect_probable_typo("Gastos 200") == "gasto:"

    def test_ingreso_sin_dos_puntos(self):
        assert detect_probable_typo("ingreso 5000 propina") == "ingreso:"

    def test_tarea_en_plural(self):
        assert detect_probable_typo("tareas comprar pan") == "tarea:"

    def test_texto_sin_relacion_no_sugiere_nada(self):
        assert detect_probable_typo("se me ocurrió algo") is None

    def test_prefijo_exacto_tambien_lo_reconoce(self):
        # No hace diferencia: si ya está bien escrito, detect_entry_type lo
        # toma como gasto de todos modos y este aviso nunca se usa.
        assert detect_probable_typo("gasto: 15000 nafta") == "gasto:"

    def test_typo_con_letras_invertidas(self):
        assert detect_probable_typo("gsato 15000 nafta") == "gasto:"

    def test_typo_con_letra_de_mas(self):
        assert detect_probable_typo("ingreeso 5000 propina") == "ingreso:"

    def test_typo_corto_en_tarea(self):
        assert detect_probable_typo("trea comprar pan") == "tarea:"

    def test_palabras_comunes_no_disparan_el_aviso(self):
        assert detect_probable_typo("hola como estas") is None
        assert detect_probable_typo("ayuda con esto") is None
        assert detect_probable_typo("nota para mi mismo") is None

    def test_limitacion_conocida_palabras_cortas_parecidas(self):
        # "área" se parece a "tarea" por pura casualidad de letras, y acá
        # da un falso positivo. Queda documentado a propósito: el costo es
        # bajo porque Atlas pregunta antes de guardar (un "no" lo resuelve),
        # y subir el umbral de similitud para evitarlo pierde typos reales
        # como "gsato" o "ingreeso" (ver tests de arriba).
        assert detect_probable_typo("area de estudio") == "tarea:"


class TestBuildCorrectedText:
    def test_reemplaza_la_primera_palabra_por_el_prefijo(self):
        assert (
            build_corrected_text("gasto 15000 nafta", "gasto:") == "gasto: 15000 nafta"
        )

    def test_reemplaza_aunque_la_palabra_original_tenga_dos_puntos(self):
        assert build_corrected_text("gastos: 400", "gasto:") == "gasto: 400"

    def test_sin_resto_no_deja_espacio_colgando(self):
        assert build_corrected_text("gasto", "gasto:") == "gasto:"


class TestNormalizeListType:
    def test_comando_valido(self):
        assert normalize_list_type("listar gastos") == "gasto"

    def test_comando_invalido(self):
        assert normalize_list_type("listar autos") is None


class TestFormatMoney:
    def test_formato_con_separador_de_miles(self):
        assert format_money(15000) == "$15.000"

    def test_formato_sin_separador(self):
        assert format_money(500) == "$500"

    def test_formato_cero(self):
        assert format_money(0) == "$0"


class TestParseIncome:
    def test_monto_simple(self):
        assert parse_income("ingreso: 100000 uber") == {
            "amount": 100000,
            "description": "uber",
        }

    def test_monto_con_separador_de_miles(self):
        assert parse_income("ingreso: 100.000 uber") == {
            "amount": 100000,
            "description": "uber",
        }

    def test_prefijo_en_mayusculas_tambien_parsea(self):
        assert parse_income("Ingreso: 5000 propina") == {
            "amount": 5000,
            "description": "propina",
        }

    def test_sin_descripcion_usa_valor_por_defecto(self):
        assert parse_income("ingreso: 5000")["description"] == "Sin descripción"

    def test_monto_ambiguo_tipo_decimal_se_rechaza(self):
        assert parse_income("ingreso: 15.5 propina") is None

    def test_monto_negativo_se_rechaza(self):
        assert parse_income("ingreso: -500 uber") is None

    def test_monto_no_numerico_se_rechaza(self):
        assert parse_income("ingreso: abc uber") is None

    def test_sin_contenido_se_rechaza(self):
        assert parse_income("ingreso:") is None

    def test_un_gasto_no_se_parsea_como_ingreso(self):
        assert parse_income("gasto: 15000 nafta") is None


class TestIngresosEnComandos:
    def test_detecta_ingreso(self):
        assert detect_entry_type("ingreso: 100000 uber") == "ingreso"

    def test_detecta_ingreso_sin_importar_mayusculas(self):
        assert detect_entry_type("Ingreso: 100000 uber") == "ingreso"

    def test_listar_ingresos(self):
        assert normalize_list_type("listar ingresos") == "ingreso"


class TestFormatMoneyNegativo:
    def test_balance_negativo_muestra_el_signo_adelante(self):
        assert format_money(-5000) == "-$5.000"

    def test_negativo_con_miles(self):
        assert format_money(-1500000) == "-$1.500.000"


class TestCalculateBalance:
    HOY = date(2026, 10, 11)

    def test_sin_registros_da_cero(self):
        assert calculate_balance([], self.HOY) == {
            "income": 0,
            "expenses": 0,
            "balance": 0,
        }

    def test_suma_ingresos_y_gastos_del_dia(self):
        entries = [
            {"created_at": "2026-10-11T09:00:00", "type": "ingreso", "amount": 100000},
            {"created_at": "2026-10-11T12:00:00", "type": "gasto", "amount": 30000},
            {"created_at": "2026-10-11T18:00:00", "type": "gasto", "amount": 5000},
        ]

        assert calculate_balance(entries, self.HOY) == {
            "income": 100000,
            "expenses": 35000,
            "balance": 65000,
        }

    def test_ignora_registros_de_otros_dias(self):
        entries = [
            {"created_at": "2026-10-10T23:59:00", "type": "ingreso", "amount": 90000},
            {"created_at": "2026-10-11T10:00:00", "type": "gasto", "amount": 1000},
            {"created_at": "2026-10-12T00:00:00", "type": "gasto", "amount": 7000},
        ]

        assert calculate_balance(entries, self.HOY) == {
            "income": 0,
            "expenses": 1000,
            "balance": -1000,
        }

    def test_balance_puede_ser_negativo(self):
        entries = [
            {"created_at": "2026-10-11T08:00:00", "type": "ingreso", "amount": 10000},
            {"created_at": "2026-10-11T09:00:00", "type": "gasto", "amount": 25000},
        ]

        assert calculate_balance(entries, self.HOY)["balance"] == -15000

    def test_ignora_tareas_notas_y_gastos_viejos_sin_monto(self):
        # Los gastos guardados antes del Sprint 2 no tienen "amount".
        entries = [
            {"created_at": "2026-10-11T08:00:00", "type": "tarea", "text": "tarea: x"},
            {"created_at": "2026-10-11T09:00:00", "type": "gasto", "text": "gasto: 5"},
            {"created_at": "2026-10-11T10:00:00", "type": "nota", "text": "hola"},
        ]

        assert calculate_balance(entries, self.HOY)["balance"] == 0

    def test_registro_sin_fecha_se_ignora(self):
        entries = [{"type": "ingreso", "amount": 5000}]

        assert calculate_balance(entries, self.HOY)["income"] == 0


class TestCalculateMonthlyBalance:
    HOY = date(2026, 10, 11)

    def test_suma_todo_el_mes_no_solo_el_dia(self):
        entries = [
            {"created_at": "2026-10-01T09:00:00", "type": "ingreso", "amount": 100000},
            {"created_at": "2026-10-11T12:00:00", "type": "gasto", "amount": 30000},
            {"created_at": "2026-10-30T18:00:00", "type": "gasto", "amount": 5000},
        ]

        assert calculate_monthly_balance(entries, self.HOY) == {
            "income": 100000,
            "expenses": 35000,
            "balance": 65000,
        }

    def test_ignora_meses_distintos(self):
        entries = [
            {"created_at": "2026-09-30T23:59:00", "type": "gasto", "amount": 50000},
            {"created_at": "2026-10-01T00:00:00", "type": "gasto", "amount": 1000},
            {"created_at": "2026-11-01T00:00:00", "type": "gasto", "amount": 7000},
        ]

        assert calculate_monthly_balance(entries, self.HOY)["expenses"] == 1000

    def test_no_confunde_octubre_con_octubre_del_otro_anio(self):
        # "2026-10" no debe matchear "2025-10-...": el prefijo incluye el año.
        entries = [
            {"created_at": "2025-10-11T09:00:00", "type": "gasto", "amount": 9999}
        ]

        assert calculate_monthly_balance(entries, self.HOY)["expenses"] == 0


class TestGuardadoYLectura:
    def test_guarda_un_gasto_con_monto_y_descripcion(self):
        with archivo_temporal() as ruta:
            entry = save_entry("gasto", "gasto: 15000 nafta")

            assert entry["amount"] == 15000
            assert entry["description"] == "nafta"
            assert json.loads(ruta.read_text(encoding="utf-8"))["amount"] == 15000

    def test_guarda_un_ingreso_con_monto_y_descripcion(self):
        with archivo_temporal():
            entry = save_entry("ingreso", "ingreso: 100000 uber")

            assert entry["type"] == "ingreso"
            assert entry["amount"] == 100000
            assert entry["description"] == "uber"

    def test_gasto_invalido_lanza_error_y_no_guarda_nada(self):
        with archivo_temporal() as ruta:
            with pytest.raises(ValueError):
                save_entry("gasto", "gasto: abc nafta")

            assert not ruta.exists()

    def test_ingreso_invalido_lanza_error_y_no_guarda_nada(self):
        with archivo_temporal() as ruta:
            with pytest.raises(ValueError):
                save_entry("ingreso", "ingreso: abc uber")

            assert not ruta.exists()

    def test_una_tarea_no_lleva_monto(self):
        with archivo_temporal():
            entry = save_entry("tarea", "tarea: comprar arroz")

            assert "amount" not in entry

    def test_lee_lo_que_se_guardo_en_orden(self):
        with archivo_temporal():
            save_entry("gasto", "gasto: 5000 pan")
            save_entry("ingreso", "ingreso: 20000 uber")

            tipos = [entry["type"] for entry in load_entries()]

            assert tipos == ["gasto", "ingreso"]

    def test_sin_archivo_devuelve_lista_vacia(self):
        with archivo_temporal():
            assert load_entries() == []

    def test_una_linea_corrupta_no_rompe_la_lectura(self):
        with archivo_temporal() as ruta:
            save_entry("gasto", "gasto: 5000 pan")

            with ruta.open("a", encoding="utf-8") as file:
                file.write("esto no es json\n")

            save_entry("gasto", "gasto: 3000 cafe")

            assert len(load_entries()) == 2

    def test_cada_registro_tiene_un_id_distinto_y_creciente(self):
        with archivo_temporal():
            primero = save_entry("gasto", "gasto: 5000 pan")
            segundo = save_entry("tarea", "tarea: comprar arroz")

            assert primero["id"] == 1
            assert segundo["id"] == 2

    def test_el_id_no_se_repite_despues_de_borrar(self):
        with archivo_temporal():
            primero = save_entry("gasto", "gasto: 5000 pan")
            save_entry("tarea", "tarea: comprar arroz")

            delete_entry(primero["id"])
            tercero = save_entry("idea", "idea: algo")

            # Si se usara "cantidad de registros + 1", tercero reusaría el
            # id 2 (quedarían dos registros, y 2+1=3 también, pero con
            # listas más largas el riesgo de colisión es real). max()
            # garantiza que nunca se repita un id ya usado.
            assert tercero["id"] == 3


class TestFindEntry:
    def test_encuentra_un_registro_existente(self):
        with archivo_temporal():
            entry = save_entry("gasto", "gasto: 5000 pan")

            assert find_entry(entry["id"]) == entry

    def test_devuelve_none_si_no_existe(self):
        with archivo_temporal():
            assert find_entry(999) is None


class TestDeleteEntry:
    def test_borra_el_registro_indicado(self):
        with archivo_temporal():
            entry = save_entry("gasto", "gasto: 5000 pan")

            assert delete_entry(entry["id"]) is True
            assert load_entries() == []

    def test_no_toca_los_demas_registros(self):
        with archivo_temporal():
            primero = save_entry("gasto", "gasto: 5000 pan")
            segundo = save_entry("tarea", "tarea: comprar arroz")

            delete_entry(primero["id"])

            restantes = load_entries()

            assert len(restantes) == 1
            assert restantes[0]["id"] == segundo["id"]

    def test_borrar_un_id_inexistente_devuelve_false(self):
        with archivo_temporal():
            save_entry("gasto", "gasto: 5000 pan")

            assert delete_entry(999) is False
            assert len(load_entries()) == 1


class TestMarkTaskDone:
    def test_marca_una_tarea_como_hecha(self):
        with archivo_temporal():
            tarea = save_entry("tarea", "tarea: comprar arroz")

            assert mark_task_done(tarea["id"]) == "ok"
            assert load_entries()[0]["done"] is True

    def test_no_es_tarea(self):
        with archivo_temporal():
            gasto = save_entry("gasto", "gasto: 5000 pan")

            assert mark_task_done(gasto["id"]) == "no_es_tarea"

    def test_id_inexistente(self):
        with archivo_temporal():
            assert mark_task_done(999) == "no_encontrado"


class TestParseIdCommand:
    def test_id_valido(self):
        assert parse_id_command("borrar 3", "borrar") == 3

    def test_la_palabra_clave_no_coincide(self):
        assert parse_id_command("hecha 3", "borrar") is None

    def test_sin_id_devuelve_none(self):
        assert parse_id_command("borrar", "borrar") is None

    def test_id_no_numerico_devuelve_none(self):
        assert parse_id_command("borrar abc", "borrar") is None


class TestReescrituraSegura:
    """Borrar o modificar un registro no puede perder ni dañar otros datos."""

    LINEA_1 = '{"id": 1, "created_at": "2026-10-01T10:00:00", "type": "tarea", "text": "tarea: a"}'
    LINEA_2 = (
        '{"id": 2, "created_at": "2026-10-01T11:00:00", "type": "nota", "text": "hola"}'
    )
    ILEGIBLE = '{"created_at": "2026-09-02T10:00:00", "type": "nota", "text": "cortada'

    def _escribir(self, ruta, *lineas):
        ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    def test_borrar_conserva_las_lineas_ilegibles(self):
        with archivo_temporal() as ruta:
            self._escribir(ruta, self.ILEGIBLE, self.LINEA_1, self.LINEA_2)

            assert delete_entry(1) is True

            assert ruta.read_text(encoding="utf-8").splitlines() == [
                self.ILEGIBLE,
                self.LINEA_2,
            ]

    def test_hecha_conserva_las_lineas_ilegibles_y_el_resto_intacto(self):
        with archivo_temporal() as ruta:
            self._escribir(ruta, self.ILEGIBLE, self.LINEA_1, self.LINEA_2)

            assert mark_task_done(1) == "ok"

            lineas = ruta.read_text(encoding="utf-8").splitlines()
            assert lineas[0] == self.ILEGIBLE
            assert lineas[2] == self.LINEA_2
            assert json.loads(lineas[1])["done"] is True

    def test_borrar_un_id_inexistente_no_toca_el_archivo(self):
        with archivo_temporal() as ruta:
            self._escribir(ruta, self.ILEGIBLE, self.LINEA_1)
            antes = ruta.read_bytes()

            assert delete_entry(99) is False
            assert ruta.read_bytes() == antes

    def test_hecha_sobre_algo_que_no_es_tarea_no_toca_el_archivo(self):
        with archivo_temporal() as ruta:
            self._escribir(ruta, self.LINEA_2)
            antes = ruta.read_bytes()

            assert mark_task_done(2) == "no_es_tarea"
            assert ruta.read_bytes() == antes

    def test_si_falla_el_reemplazo_el_original_queda_intacto(self):
        with archivo_temporal() as ruta:
            self._escribir(ruta, self.LINEA_1, self.LINEA_2)
            antes = ruta.read_bytes()

            with patch.object(atlas_main.os, "replace", side_effect=OSError("falla")):
                with pytest.raises(OSError):
                    delete_entry(1)

            assert ruta.read_bytes() == antes
            assert [p.name for p in ruta.parent.iterdir()] == ["entries.jsonl"]

    def test_no_queda_archivo_temporal_despues_de_borrar(self):
        with archivo_temporal() as ruta:
            self._escribir(ruta, self.LINEA_1, self.LINEA_2)

            delete_entry(1)

            assert [p.name for p in ruta.parent.iterdir()] == ["entries.jsonl"]


class TestCreateBackup:
    def test_sin_datos_devuelve_none(self):
        with archivo_temporal():
            assert create_backup() is None

    def test_copia_el_contenido_actual(self):
        with archivo_temporal():
            save_entry("gasto", "gasto: 5000 pan")

            backup_path = create_backup()

            assert backup_path is not None
            assert backup_path.read_text(encoding="utf-8") == backup_path.with_name(
                "entries.jsonl"
            ).read_text(encoding="utf-8")

    def test_no_modifica_el_archivo_original(self):
        with archivo_temporal() as ruta:
            save_entry("gasto", "gasto: 5000 pan")
            original_antes = ruta.read_bytes()

            create_backup()

            assert ruta.read_bytes() == original_antes

    def test_el_nombre_del_backup_incluye_bak_y_la_extension_original(self):
        with archivo_temporal():
            save_entry("gasto", "gasto: 5000 pan")

            backup_path = create_backup()

            assert backup_path.name.startswith("entries.")
            assert backup_path.name.endswith(".bak.jsonl")

    def test_conserva_lineas_ilegibles_igual_que_el_original(self):
        with archivo_temporal() as ruta:
            ilegible = '{"created_at": "2026-09-02T10:00:00", "cortada'
            save_entry("gasto", "gasto: 5000 pan")
            ruta.write_text(
                ruta.read_text(encoding="utf-8") + ilegible + "\n", encoding="utf-8"
            )

            backup_path = create_backup()

            assert ilegible in backup_path.read_text(encoding="utf-8")
