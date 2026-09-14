"""
CLI do auditor de ponto.

Uso típico:

    python -m ponto_auditor auditar espelho.pdf --efetivo EFETIVO.xlsx \\
        --obra "EPR Duplicação BR-153 · Lote 02 · PR" --empresa "TUCUMANN ENG EMPREEND LTDA" \\
        --inicio 21/08/2026 --fim 10/09/2026 -o saida/

Enquanto o parser de PDF (ponto_auditor/parser_pdf.py) não estiver calibrado
com um espelho real, use --json para apontar dados já estruturados no mesmo
formato de tests/fixtures/espelho_amostra.json:

    python -m ponto_auditor auditar --json dados.json -o saida/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .modelos import Periodo, db_para_periodo
from .relatorio import aplicar_regras, gerar_painel_html, resumo_auditoria, resumo_markdown


def _construir_periodo(args) -> Periodo:
    if args.json:
        db = json.loads(Path(args.json).read_text(encoding="utf-8"))
        return db_para_periodo(db)

    from .calculos import aplicar_calculos
    from .parser_pdf import ErroDeLeitura, parse_espelho_pdf

    try:
        periodo = parse_espelho_pdf(args.pdf, debug=args.debug)
    except ErroDeLeitura as e:
        print(f"Erro de leitura do PDF: {e}", file=sys.stderr)
        sys.exit(1)

    # sobrescreve metadados do cabeçalho do PDF só quando informados na CLI
    for campo, valor in (("inicio", args.inicio), ("fim", args.fim),
                          ("empresa", args.empresa), ("cnpj", args.cnpj),
                          ("obra", args.obra), ("gerado_em", args.gerado_em)):
        if valor:
            setattr(periodo, campo, valor)
    if args.ano:
        periodo.ano = args.ano

    if args.efetivo:
        from .efetivo import aplicar_efetivo, carregar_efetivo

        registros = carregar_efetivo(args.efetivo)
        periodo.sem_cadastro = aplicar_efetivo(periodo.colaboradores, registros)

    for colaborador in periodo.colaboradores:
        aplicar_calculos(colaborador)
    return periodo


def cmd_auditar(args) -> None:
    periodo = _construir_periodo(args)
    aplicar_regras(periodo)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    caminho_html = gerar_painel_html(periodo, outdir / "painel_ponto.html")
    resumo_md = resumo_markdown(periodo)
    caminho_md = outdir / "resumo_auditoria.md"
    caminho_md.write_text(resumo_md, encoding="utf-8")
    caminho_json = outdir / "resumo_auditoria.json"
    caminho_json.write_text(
        json.dumps(resumo_auditoria(periodo), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(resumo_md)
    print()
    print(f"Painel HTML: {caminho_html}")
    print(f"Resumo (md): {caminho_md}")
    print(f"Resumo (json): {caminho_json}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="ponto_auditor", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("auditar", help="Audita um espelho de ponto e gera o painel + resumo")
    fonte = p.add_mutually_exclusive_group(required=True)
    fonte.add_argument("pdf", nargs="?", help="Caminho do PDF do espelho de ponto (Senior Sistemas)")
    fonte.add_argument("--json", help="Caminho de um JSON já estruturado (bypassa o parser de PDF)")
    p.add_argument("--efetivo", help="Planilha xlsx com o cadastro de efetivo (encarregado, setor, função...)")
    p.add_argument("-o", "--outdir", default="saida", help="Diretório de saída (padrão: ./saida)")
    p.add_argument("--obra", help="Nome da obra/contrato (cabeçalho do painel)")
    p.add_argument("--empresa", help="Razão social da empresa")
    p.add_argument("--cnpj", default="")
    p.add_argument("--inicio", help="Data inicial do período, DD/MM/AAAA")
    p.add_argument("--fim", help="Data final do período, DD/MM/AAAA")
    p.add_argument("--ano", type=int, default=None)
    p.add_argument("--gerado-em", dest="gerado_em", default="")
    p.add_argument("--debug", action="store_true", help="Imprime o texto bruto extraído do PDF")
    p.set_defaults(func=cmd_auditar)

    args = parser.parse_args(argv)
    if args.ano is None:
        import datetime
        args.ano = datetime.date.today().year
    args.func(args)


if __name__ == "__main__":
    main()
