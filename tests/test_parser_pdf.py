"""
Testa parser_pdf.py + calculos.py de ponta a ponta contra
tests/fixtures/cartao_ponto_amostra.pdf — um PDF sintético que reproduz o
layout real do Cartão Ponto (Senior Sistemas), gerado a partir de
tests/fixtures/cartao_ponto_amostra_fonte.json (dados de 6 colaboradores
reais, com nome/matrícula trocados por fictícios — ver
tests/fixtures/gerar_pdf_amostra.py).

Esse mesmo JSON-fonte guarda também os campos que NÃO são impressos no PDF
(iv, intra, inter, jorn, apur, saidaPrev, atrSaida, domFer, al) — que é
exatamente o que ponto_auditor.calculos e ponto_auditor.regras precisam
recalcular a partir do que o PDF traz. O teste extrai o PDF e confere,
dia a dia, se a extração bate com o que está impresso e se os campos
derivados batem com o que o backend original já havia calculado.
"""
import json
from pathlib import Path

import pytest

from ponto_auditor.calculos import aplicar_calculos
from ponto_auditor.parser_pdf import parse_espelho_pdf
from ponto_auditor.relatorio import aplicar_regras, gerar_painel_html

FIXTURES = Path(__file__).parent / "fixtures"
PDF = FIXTURES / "cartao_ponto_amostra.pdf"
FONTE = FIXTURES / "cartao_ponto_amostra_fonte.json"


@pytest.fixture(scope="module")
def gabarito():
    dados = json.loads(FONTE.read_text(encoding="utf-8"))
    return {e["mat"]: e for e in dados["emp"]}


@pytest.fixture(scope="module")
def periodo():
    if not PDF.exists():
        pytest.skip("cartao_ponto_amostra.pdf não gerado — rode gerar_pdf_amostra.py")
    p = parse_espelho_pdf(str(PDF))
    for c in p.colaboradores:
        aplicar_calculos(c)
    aplicar_regras(p)
    return p


def test_extrai_todos_os_colaboradores(periodo, gabarito):
    assert {c.matricula for c in periodo.colaboradores} == set(gabarito.keys())


def test_cabecalho_da_pagina(periodo):
    assert periodo.empresa == "TUCUMANN ENG EMPREEND LTDA"
    assert periodo.cnpj == "81.750.697/0001-10"
    assert periodo.obra == "EPR Duplicação Lote 02"
    assert periodo.inicio == "21/08/2026"
    assert periodo.fim == "10/09/2026"


def test_campos_lidos_diretamente_do_pdf(periodo, gabarito):
    """trab/falt/atr/e50/e110/eOut/adnot/marc/hcod/obs devem bater 1:1
    com o que está impresso — não passam por cálculo, só leitura."""
    for c in periodo.colaboradores:
        esperado = gabarito[c.matricula]
        assert len(c.dias) == len(esperado["dias"]), c.matricula
        for dia, dia_esp in zip(c.dias, esperado["dias"]):
            ctx = f"{c.matricula} {dia.data}"
            assert dia.data == dia_esp["data"], ctx
            assert dia.dia_semana == dia_esp["sem"], ctx
            assert dia.codigo_horario == dia_esp["hcod"], ctx
            assert dia.marc == dia_esp["marc"], ctx
            assert dia.trabalhado == dia_esp["trab"], ctx
            assert dia.falta == dia_esp["falt"], ctx
            assert dia.atraso == dia_esp["atr"], ctx
            assert dia.e50 == dia_esp["e50"], ctx
            assert dia.e110 == dia_esp["e110"], ctx
            assert dia.e_out == dia_esp["eOut"], ctx
            assert dia.adicional_noturno == dia_esp["adnot"], ctx


def test_campos_derivados_batem_com_o_backend_original(periodo, gabarito):
    """iv/intra/inter/jorn/apur/saidaPrev/atrSaida/domFer — calculados por
    ponto_auditor.calculos a partir do que o PDF trouxe — devem bater com
    os valores que o backend original já havia calculado para os mesmos
    colaboradores/dias reais."""
    for c in periodo.colaboradores:
        esperado = gabarito[c.matricula]
        for dia, dia_esp in zip(c.dias, esperado["dias"]):
            ctx = f"{c.matricula} {dia.data}"
            assert dia.intrajornada == dia_esp["intra"], ctx
            assert dia.interjornada == dia_esp["inter"], ctx
            assert dia.jornada == dia_esp["jorn"], ctx
            assert dia.apuracao == dia_esp["apur"], ctx
            assert dia.saida_prevista == dia_esp["saidaPrev"], ctx
            assert dia.atraso_saida == dia_esp["atrSaida"], ctx
            assert dia.domingo_feriado == dia_esp["domFer"], ctx


def test_alertas_de_regras_batem_com_o_backend_original(periodo, gabarito):
    for c in periodo.colaboradores:
        esperado = gabarito[c.matricula]
        for dia, dia_esp in zip(c.dias, esperado["dias"]):
            assert set(dia.alertas) == set(dia_esp["al"]), f"{c.matricula} {dia.data}"


def test_gera_painel_a_partir_do_pdf(periodo, tmp_path):
    destino = gerar_painel_html(periodo, tmp_path / "painel.html")
    assert destino.exists() and destino.stat().st_size > 500_000
