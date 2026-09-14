"""
Valida o motor de regras (ponto_auditor.regras) contra uma amostra real de
dados já apurados: os alertas recalculados devem bater exatamente com os
alertas originalmente publicados no painel de referência
"Controle de Ponto · Tucumann Engenharia · EPR BR-153 Lote 02".
"""
import json
from pathlib import Path

from ponto_auditor import regras
from ponto_auditor.modelos import db_para_periodo
from ponto_auditor.relatorio import aplicar_regras, gerar_painel_html, resumo_auditoria

FIXTURE = Path(__file__).parent / "fixtures" / "espelho_amostra.json"


def carregar_periodo():
    db = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return db_para_periodo(db), db


def test_alertas_batem_com_dados_reais():
    periodo, db_original = carregar_periodo()

    # guarda os alertas originais antes de zerá-los
    originais = {}
    for e in db_original["emp"]:
        for d in e["dias"]:
            originais[(e["mat"], d["data"])] = set(d["al"])

    aplicar_regras(periodo)

    total_dias = 0
    for c in periodo.colaboradores:
        for d in c.dias:
            total_dias += 1
            esperado = originais[(c.matricula, d.data)]
            obtido = set(d.alertas)
            assert obtido == esperado, (
                f"{c.matricula} {d.data}: esperado {esperado}, obtido {obtido}"
            )
    assert total_dias > 200  # amostra tem volume suficiente para ser um teste real


def test_todas_as_regras_sao_exercitadas_na_amostra():
    periodo, _ = carregar_periodo()
    aplicar_regras(periodo)
    codigos_vistos = {a for c in periodo.colaboradores for d in c.dias for a in d.alertas}
    assert codigos_vistos == set(regras.REGRAS.keys())


def test_gerar_painel_html_roundtrip(tmp_path):
    periodo, _ = carregar_periodo()
    aplicar_regras(periodo)
    destino = gerar_painel_html(periodo, tmp_path / "painel.html")
    conteudo = destino.read_text(encoding="utf-8")
    assert "__PONTO_DB_JSON__" not in conteudo
    assert "const DB=" in conteudo
    assert periodo.obra in conteudo
    assert conteudo.count("<script>") >= 2


def test_resumo_auditoria_tem_indicadores_essenciais():
    periodo, _ = carregar_periodo()
    aplicar_regras(periodo)
    r = resumo_auditoria(periodo)
    assert r["colaboradores"] == len(periodo.colaboradores)
    assert r["nao_conformidades_criticas"] > 0
    assert r["ocorrencias_por_regra"]
    assert r["top10_horas_extras"]
