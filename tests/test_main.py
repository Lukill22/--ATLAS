"""Pruebas de las funciones puras de `atlas.main`.

No cubren `main()` (el loop interactivo con `input`/`print`) porque mezcla
E/S con lógica; eso queda para cuando valga la pena separarlo.
"""

import json
from datetime import date, datetime
from unittest.mock import patch

import pytest

import atlas.main as atlas_main
from conftest import archivo_temporal
from atlas.main import (
    build_corrected_text,
    calculate_balance,
    calculate_monthly_balance,
    create_backup,
    delete_entry,
    detect_entry_type,
    detect_probable_typo,
    filter_by_period,
    find_entry,
    format_entry_summary,
    format_money,
    get_due_daily_balances,
    get_due_reminders,
    handle_command,
    load_entries,
    mark_daily_balance_sent,
    mark_reminder_notified,
    mark_task_done,
    parse_daily_balance_config,
    parse_expense,
    parse_id_command,
    parse_income,
    parse_list_command,
    parse_reminder,
    save_entry,
)


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

    def test_detecta_balance_diario(self):
        assert detect_entry_type("balance diario: 23:00") == "balance_diario"

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


class TestParseListCommand:
    def test_listar_solo(self):
        assert parse_list_command("listar") == {"entry_type": None, "period": None}

    def test_listar_con_tipo(self):
        assert parse_list_command("listar gastos") == {
            "entry_type": "gasto",
            "period": None,
        }

    def test_listar_con_periodo_sin_tipo(self):
        assert parse_list_command("listar hoy") == {"entry_type": None, "period": "hoy"}

    def test_listar_con_tipo_y_periodo(self):
        assert parse_list_command("listar tareas mes") == {
            "entry_type": "tarea",
            "period": "mes",
        }

    def test_palabra_no_reconocida_devuelve_none(self):
        assert parse_list_command("listar autos") is None

    def test_tipo_repetido_devuelve_none(self):
        assert parse_list_command("listar gastos ingresos") is None

    def test_demasiadas_palabras_devuelve_none(self):
        assert parse_list_command("listar gastos hoy ahora") is None

    def test_texto_sin_relacion_devuelve_none(self):
        assert parse_list_command("total gastos") is None

    def test_dos_puntos_de_mas_en_el_tipo(self):
        # Bug real reportado con el bot: agregar ":" por costumbre (el
        # resto de Atlas sí usa ":" para capturar) hacía que esto cayera
        # como nota en vez de listar.
        assert parse_list_command("listar gastos:") == {
            "entry_type": "gasto",
            "period": None,
        }

    def test_dos_puntos_de_mas_despues_de_listar_solo(self):
        assert parse_list_command("listar:") == {"entry_type": None, "period": None}


class TestFilterByPeriod:
    HOY = "2026-10-11T10:00:00"
    AYER = "2026-10-10T23:59:00"
    OTRO_MES = "2026-09-30T10:00:00"

    def _entries(self):
        return [
            {"created_at": self.HOY, "text": "de hoy"},
            {"created_at": self.AYER, "text": "de ayer"},
            {"created_at": self.OTRO_MES, "text": "de otro mes"},
        ]

    def test_sin_periodo_no_filtra(self):
        assert filter_by_period(self._entries(), None) == self._entries()

    def test_hoy_solo_deja_las_de_hoy(self):
        with patch.object(atlas_main, "date") as fecha_falsa:
            fecha_falsa.today.return_value = date(2026, 10, 11)
            resultado = filter_by_period(self._entries(), "hoy")

        assert [entry["text"] for entry in resultado] == ["de hoy"]

    def test_mes_deja_todo_el_mes(self):
        with patch.object(atlas_main, "date") as fecha_falsa:
            fecha_falsa.today.return_value = date(2026, 10, 11)
            resultado = filter_by_period(self._entries(), "mes")

        assert [entry["text"] for entry in resultado] == ["de hoy", "de ayer"]


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
        assert parse_list_command("listar ingresos") == {
            "entry_type": "ingreso",
            "period": None,
        }


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


class TestParseReminder:
    def test_formato_valido_sin_anio(self):
        assert parse_reminder("recordatorio: 19/10 08:00 sacar la basura") == {
            "due_at": f"{date.today().year}-10-19T08:00",
            "description": "sacar la basura",
            "notified": False,
        }

    def test_formato_valido_con_anio(self):
        assert parse_reminder("recordatorio: 19/10/2027 08:00 turno medico") == {
            "due_at": "2027-10-19T08:00",
            "description": "turno medico",
            "notified": False,
        }

    def test_no_distingue_mayusculas_en_el_prefijo(self):
        assert parse_reminder("Recordatorio: 19/10 08:00 algo") is not None

    def test_sin_prefijo_devuelve_none(self):
        assert parse_reminder("19/10 08:00 sacar la basura") is None

    def test_sin_hora_devuelve_none(self):
        assert parse_reminder("recordatorio: 19/10 sacar la basura") is None

    def test_sin_texto_devuelve_none(self):
        assert parse_reminder("recordatorio: 19/10 08:00") is None

    def test_fecha_invalida_devuelve_none(self):
        assert parse_reminder("recordatorio: 31/02 08:00 algo imposible") is None

    def test_sin_contenido_devuelve_none(self):
        assert parse_reminder("recordatorio:") is None


class TestGuardarRecordatorio:
    def test_guarda_con_chat_id(self):
        with archivo_temporal():
            entry = save_entry(
                "recordatorio",
                "recordatorio: 19/10 08:00 sacar la basura",
                chat_id=123,
            )

            assert entry["chat_id"] == 123
            assert entry["description"] == "sacar la basura"
            assert entry["notified"] is False

    def test_sin_chat_id_no_guarda_esa_clave(self):
        with archivo_temporal():
            entry = save_entry(
                "recordatorio", "recordatorio: 19/10 08:00 sacar la basura"
            )

            assert "chat_id" not in entry

    def test_formato_invalido_lanza_error_y_no_guarda(self):
        with archivo_temporal() as ruta:
            with pytest.raises(ValueError):
                save_entry("recordatorio", "recordatorio: mañana sacar la basura")

            assert not ruta.exists()


class TestGetDueReminders:
    AHORA = datetime(2026, 10, 19, 8, 0)

    def test_vencido_y_sin_avisar_aparece(self):
        entries = [
            {
                "id": 1,
                "type": "recordatorio",
                "due_at": "2026-10-19T07:59",
                "notified": False,
            }
        ]

        assert get_due_reminders(entries, self.AHORA) == entries

    def test_todavia_no_vencido_no_aparece(self):
        entries = [
            {
                "id": 1,
                "type": "recordatorio",
                "due_at": "2026-10-19T08:01",
                "notified": False,
            }
        ]

        assert get_due_reminders(entries, self.AHORA) == []

    def test_ya_avisado_no_aparece_de_nuevo(self):
        entries = [
            {
                "id": 1,
                "type": "recordatorio",
                "due_at": "2026-10-19T07:00",
                "notified": True,
            }
        ]

        assert get_due_reminders(entries, self.AHORA) == []

    def test_ignora_otros_tipos(self):
        entries = [{"id": 1, "type": "tarea", "text": "x"}]

        assert get_due_reminders(entries, self.AHORA) == []


class TestMarkReminderNotified:
    def test_marca_como_avisado(self):
        with archivo_temporal():
            entry = save_entry(
                "recordatorio",
                "recordatorio: 19/10 08:00 sacar la basura",
                chat_id=123,
            )

            assert mark_reminder_notified(entry["id"]) is True
            assert load_entries()[0]["notified"] is True

    def test_id_inexistente_devuelve_false(self):
        with archivo_temporal():
            assert mark_reminder_notified(999) is False

    def test_no_es_recordatorio_devuelve_false(self):
        with archivo_temporal():
            entry = save_entry("gasto", "gasto: 5000 pan")

            assert mark_reminder_notified(entry["id"]) is False


class TestFormatEntrySummaryRecordatorio:
    def test_pendiente_muestra_reloj(self):
        entry = {
            "type": "recordatorio",
            "due_at": "2026-10-19T08:00",
            "description": "sacar la basura",
            "notified": False,
        }

        assert (
            format_entry_summary(entry)
            == "⏰ [recordatorio] 19/10 08:00 - sacar la basura"
        )

    def test_avisado_muestra_check(self):
        entry = {
            "type": "recordatorio",
            "due_at": "2026-10-19T08:00",
            "description": "sacar la basura",
            "notified": True,
        }

        assert (
            format_entry_summary(entry)
            == "✅ [recordatorio] 19/10 08:00 - sacar la basura"
        )


class TestParseDailyBalanceConfig:
    def test_formato_valido(self):
        assert parse_daily_balance_config("balance diario: 23:00") == "23:00"

    def test_no_distingue_mayusculas_en_el_prefijo(self):
        assert parse_daily_balance_config("Balance diario: 23:00") == "23:00"

    def test_normaliza_hora_de_un_solo_digito(self):
        assert parse_daily_balance_config("balance diario: 9:05") == "09:05"

    def test_hora_invalida_devuelve_none(self):
        assert parse_daily_balance_config("balance diario: 25:00") is None

    def test_minuto_invalido_devuelve_none(self):
        assert parse_daily_balance_config("balance diario: 10:60") is None

    def test_sin_prefijo_devuelve_none(self):
        assert parse_daily_balance_config("23:00") is None

    def test_sin_contenido_devuelve_none(self):
        assert parse_daily_balance_config("balance diario:") is None

    def test_formato_de_hora_invalido_devuelve_none(self):
        assert parse_daily_balance_config("balance diario: a las 23") is None


class TestGuardarBalanceDiario:
    def test_crea_la_configuracion_con_chat_id(self):
        with archivo_temporal():
            entry = save_entry("balance_diario", "balance diario: 23:00", chat_id=123)

            assert entry["chat_id"] == 123
            assert entry["hora"] == "23:00"
            assert entry["last_sent_date"] is None

    def test_sin_chat_id_no_guarda_esa_clave(self):
        with archivo_temporal():
            entry = save_entry("balance_diario", "balance diario: 23:00")

            assert "chat_id" not in entry

    def test_formato_invalido_lanza_error_y_no_guarda(self):
        with archivo_temporal() as ruta:
            with pytest.raises(ValueError):
                save_entry("balance_diario", "balance diario: mas o menos a la noche")

            assert not ruta.exists()

    def test_configurar_de_nuevo_actualiza_en_vez_de_duplicar(self):
        # Volver a mandar "balance diario: ..." con otra hora actualiza la
        # configuración existente del mismo chat, no suma una segunda (si
        # no, se mandaría el balance dos veces por noche).
        with archivo_temporal():
            primera = save_entry("balance_diario", "balance diario: 23:00", chat_id=123)
            segunda = save_entry("balance_diario", "balance diario: 22:30", chat_id=123)

            entradas = load_entries()
            assert len(entradas) == 1
            assert primera["id"] == segunda["id"]
            assert entradas[0]["hora"] == "22:30"

    def test_chats_distintos_no_se_pisan(self):
        with archivo_temporal():
            save_entry("balance_diario", "balance diario: 23:00", chat_id=1)
            save_entry("balance_diario", "balance diario: 20:00", chat_id=2)

            assert len(load_entries()) == 2

    def test_reconfigurar_reinicia_last_sent_date(self):
        # Si ya se había mandado hoy y el usuario cambia la hora más tarde
        # en el día, tiene que poder volver a mandarse a la nueva hora.
        with archivo_temporal():
            entry = save_entry("balance_diario", "balance diario: 10:00", chat_id=123)
            mark_daily_balance_sent(entry["id"], date.today().isoformat())

            save_entry("balance_diario", "balance diario: 23:00", chat_id=123)

            assert load_entries()[0]["last_sent_date"] is None


class TestGetDueDailyBalances:
    AHORA = datetime(2026, 10, 19, 23, 0)

    def test_hora_pasada_y_no_enviado_hoy_aparece(self):
        entries = [
            {
                "id": 1,
                "type": "balance_diario",
                "hora": "22:59",
                "last_sent_date": None,
            }
        ]

        assert get_due_daily_balances(entries, self.AHORA) == entries

    def test_hora_todavia_no_llega_no_aparece(self):
        entries = [
            {
                "id": 1,
                "type": "balance_diario",
                "hora": "23:01",
                "last_sent_date": None,
            }
        ]

        assert get_due_daily_balances(entries, self.AHORA) == []

    def test_ya_enviado_hoy_no_aparece_de_nuevo(self):
        entries = [
            {
                "id": 1,
                "type": "balance_diario",
                "hora": "22:00",
                "last_sent_date": self.AHORA.date().isoformat(),
            }
        ]

        assert get_due_daily_balances(entries, self.AHORA) == []

    def test_enviado_un_dia_distinto_vuelve_a_aparecer(self):
        entries = [
            {
                "id": 1,
                "type": "balance_diario",
                "hora": "22:00",
                "last_sent_date": "2026-10-18",
            }
        ]

        assert get_due_daily_balances(entries, self.AHORA) == entries

    def test_ignora_otros_tipos(self):
        entries = [{"id": 1, "type": "recordatorio", "due_at": "2026-10-19T08:00"}]

        assert get_due_daily_balances(entries, self.AHORA) == []


class TestMarkDailyBalanceSent:
    def test_marca_la_fecha(self):
        with archivo_temporal():
            entry = save_entry("balance_diario", "balance diario: 23:00", chat_id=123)

            assert mark_daily_balance_sent(entry["id"], "2026-10-19") is True
            assert load_entries()[0]["last_sent_date"] == "2026-10-19"

    def test_id_inexistente_devuelve_false(self):
        with archivo_temporal():
            assert mark_daily_balance_sent(999, "2026-10-19") is False

    def test_no_es_balance_diario_devuelve_false(self):
        with archivo_temporal():
            entry = save_entry("gasto", "gasto: 5000 pan")

            assert mark_daily_balance_sent(entry["id"], "2026-10-19") is False


class TestFormatEntrySummaryBalanceDiario:
    def test_pendiente_muestra_reloj(self):
        entry = {
            "type": "balance_diario",
            "hora": "23:00",
            "last_sent_date": None,
        }

        assert format_entry_summary(entry) == "⏰ pendiente [balance diario] 23:00"

    def test_enviado_hoy_muestra_check(self):
        entry = {
            "type": "balance_diario",
            "hora": "23:00",
            "last_sent_date": date.today().isoformat(),
        }

        assert format_entry_summary(entry) == "✅ enviado hoy [balance diario] 23:00"


class TestHandleCommandTypeado:
    # Bug real: "total de gatos" (palabra de más + "gastos" mal escrito)
    # no matcheaba "total gastos" exacto, y terminaba guardándose como
    # nota sin que el usuario se enterara. handle_command ahora tolera
    # esto para los comandos fijos de solo lectura (y backup).

    def test_palabra_de_mas_y_typo(self):
        with archivo_temporal():
            resultado = handle_command("total de gatos")

            assert "Gastaste" in resultado["respuesta"]

    def test_typo_simple(self):
        with archivo_temporal():
            assert "Ingresos" in handle_command("balanse dia")["respuesta"]

    def test_palabra_de_mas_sin_typo(self):
        with archivo_temporal():
            assert "Ingresos" in handle_command("balance de dia")["respuesta"]

    def test_comando_corto_con_typo(self):
        with archivo_temporal():
            assert handle_command("ayud")["es_ayuda"] is True

    def test_backup_con_typo(self):
        with archivo_temporal():
            resultado = handle_command("backp")

            assert resultado == {
                "respuesta": "Todavía no hay nada guardado para respaldar."
            }

    def test_balance_diario_no_se_confunde_con_balance_dia(self):
        # "balance diario: 23:00" es una captura (configurar el aviso
        # automático), no el comando "balance dia": handle_command no debe
        # tratarlo como un typo de ese comando fijo.
        with archivo_temporal():
            assert handle_command("balance diario: 23:00") is None

    def test_dos_puntos_de_mas_en_comando_fijo(self):
        # Mismo bug real que "listar gastos:", pero en un comando fijo:
        # agregar ":" por costumbre no debería tirarlo como nota.
        with archivo_temporal():
            assert handle_command("ayuda:")["es_ayuda"] is True
            assert "Gastaste" in handle_command("total gastos:")["respuesta"]

    def test_no_confunde_listar_con_total(self):
        # "listar gastos" comparte la palabra "gastos" con "total gastos",
        # pero tiene su propio parser y no debe pasar por este atajo.
        with archivo_temporal():
            resultado = handle_command("listar gastos")

            assert resultado["respuesta"] == "No encontré registros para ese filtro."

    def test_listar_con_typo_no_se_confunde_con_total(self):
        with archivo_temporal():
            assert handle_command("listar gasto") is None

    def test_texto_sin_relacion_sigue_devolviendo_none(self):
        with archivo_temporal():
            assert handle_command("se me ocurrió una idea para el finde") is None
