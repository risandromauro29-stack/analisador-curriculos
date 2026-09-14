"""
Aplica o motor de regras a um Periodo já carregado e gera os entregáveis:
o painel HTML interativo (mesmo template do painel de referência) e um
resumo textual da auditoria (para leitura rápida, sem abrir o painel).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import regras
from .modelos import Periodo, periodo_para_db

TEMPLATE_PATH = Path(__file__).parent / "assets" / "template_painel_ponto.html"
PLACEHOLDER = "__PONTO_DB_JSON__"


def aplicar_regras(periodo: Periodo) -> None:
    """Preenche dia.alertas para cada dia de cada colaborador (in-place)."""
    for colaborador in periodo.colaboradores:
        for dia in colaborador.dias:
            dia.alertas = regras.avaliar_dia(colaborador, dia)


def gerar_painel_html(periodo: Periodo, caminho_saida: str | Path) -> Path:
    """Gera o painel HTML interativo (offline, arquivo único) a partir do Periodo."""
    db = periodo_para_db(periodo)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise RuntimeError(f"Placeholder {PLACEHOLDER!r} não encontrado no template.")
    html = template.replace(PLACEHOLDER, json.dumps(db, ensure_ascii=False))
    destino = Path(caminho_saida)
    destino.write_text(html, encoding="utf-8")
    return destino


def resumo_auditoria(periodo: Periodo) -> dict:
    """KPIs agregados do período — a mesma leitura mostrada na Visão Geral do painel."""
    colaboradores = periodo.colaboradores
    n = len(colaboradores) or 1

    total_trab = total_extra = total_e110 = total_adnot = total_falt = 0
    criticas = atencao = com_extra = com_ocorrencia = 0
    por_regra: dict[str, int] = {codigo: 0 for codigo in regras.REGRAS}
    top_extras: list[tuple[str, str, int]] = []  # (matricula, nome, minutos extras)

    for c in colaboradores:
        extra_colab = 0
        ocorrencias_colab = 0
        for d in c.dias:
            total_trab += d.trabalhado
            total_falt += d.falta
            total_adnot += d.adicional_noturno
            ex = regras.extras_do_dia(d)
            total_extra += ex
            total_e110 += d.e110
            extra_colab += ex
            for codigo in d.alertas:
                por_regra[codigo] = por_regra.get(codigo, 0) + 1
                ocorrencias_colab += 1
                if regras.REGRAS[codigo].severidade == "crit":
                    criticas += 1
                else:
                    atencao += 1
        if extra_colab > 0:
            com_extra += 1
        if ocorrencias_colab > 0:
            com_ocorrencia += 1
        top_extras.append((c.matricula, c.nome, extra_colab))

    top_extras.sort(key=lambda t: t[2], reverse=True)

    return {
        "colaboradores": len(colaboradores),
        "horas_trabalhadas": round(total_trab / 60, 1),
        "horas_extras": round(total_extra / 60, 1),
        "horas_extras_110": round(total_e110 / 60, 1),
        "horas_adicional_noturno": round(total_adnot / 60, 1),
        "horas_falta": round(total_falt / 60, 1),
        "colaboradores_com_extras": com_extra,
        "nao_conformidades_criticas": criticas,
        "nao_conformidades_atencao": atencao,
        "efetivo_com_ocorrencia": com_ocorrencia,
        "indice_nao_conformidade": round(
            regras.indice_nao_conformidade(criticas + atencao, len(colaboradores)), 2
        ),
        "ocorrencias_por_regra": {
            codigo: {"titulo": regras.REGRAS[codigo].titulo, "qtd": qtd}
            for codigo, qtd in por_regra.items() if qtd
        },
        "top10_horas_extras": [
            {"matricula": m, "nome": nome, "horas_extras": round(mins / 60, 1)}
            for m, nome, mins in top_extras[:10]
        ],
    }


def resumo_markdown(periodo: Periodo) -> str:
    r = resumo_auditoria(periodo)
    linhas = [
        f"# Auditoria de ponto — {periodo.obra}",
        f"Período: {periodo.inicio} a {periodo.fim} · {r['colaboradores']} colaboradores",
        "",
        "## Indicadores gerais",
        f"- Horas trabalhadas: **{r['horas_trabalhadas']} h**",
        f"- Horas extras: **{r['horas_extras']} h** ({r['colaboradores_com_extras']} colaboradores)",
        f"- Horas extras a 110% (domingo/feriado): {r['horas_extras_110']} h",
        f"- Adicional noturno: {r['horas_adicional_noturno']} h",
        f"- Faltas: {r['horas_falta']} h",
        "",
        "## Não conformidades (CLT)",
        f"- Críticas: **{r['nao_conformidades_criticas']}** · Atenção: {r['nao_conformidades_atencao']}",
        f"- Efetivo com ao menos uma ocorrência: {r['efetivo_com_ocorrencia']} de {r['colaboradores']}",
        f"- Índice de não conformidade (ocorrências/colaborador): {r['indice_nao_conformidade']}"
        " (abaixo de 1,0 é controlado; acima de 2,0 exige ação)",
        "",
    ]
    if r["ocorrencias_por_regra"]:
        linhas.append("### Por regra")
        for info in r["ocorrencias_por_regra"].values():
            linhas.append(f"- {info['titulo']}: {info['qtd']} ocorrências")
        linhas.append("")
    if r["top10_horas_extras"]:
        linhas.append("### Top 10 em horas extras")
        for i, item in enumerate(r["top10_horas_extras"], 1):
            linhas.append(f"{i}. {item['nome']} ({item['matricula']}) — {item['horas_extras']} h")
    return "\n".join(linhas)
