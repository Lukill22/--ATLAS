"""Pruebas de las funciones puras de `atlas.main`.

No cubren `main()` (el loop interactivo con `input`/`print`) porque mezcla
E/S con lógica; eso queda para cuando valga la pena separarlo.
"""

from atlas.main import (
    detect_entry_type,
    format_money,
    normalize_list_type,
    parse_expense,
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

    def test_texto_libre_es_nota(self):
        assert detect_entry_type("cualquier cosa") == "nota"


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
