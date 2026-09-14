"""
Extração do "Espelho de Ponto" (Senior Sistemas) em PDF para os modelos de
ponto_auditor.modelos.

STATUS: implementação inicial (v0), ainda **não calibrada** contra um PDF real
de espelho de ponto — só foi validada a lógica de regras/apuração (ver
tests/test_regras.py), que usa dados já estruturados. O layout de colunas do
Senior varia por cliente/versão, então este parser:

  1. assume um layout típico (ver âncoras abaixo), documentado em cada regex;
  2. se recusa a adivinhar em caso de ambiguidade — levanta ErroDeLeitura em
     vez de produzir números de jornada errados, o que é inaceitável num
     relatório usado para apurar conformidade com a CLT;
  3. deve ser recalibrado assim que houver um PDF real de amostra: rode com
     ``--debug`` para dumpar o texto bruto extraído de cada página e ajustar
     os padrões abaixo por comparação linha a linha.

Ver também ``modo_json`` no CLI: enquanto o parser não estiver calibrado, os
dados podem ser fornecidos já estruturados em JSON (mesmo formato usado nos
testes, em tests/fixtures/espelho_amostra.json) para não bloquear o uso do
motor de regras e do gerador de painel.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .modelos import Colaborador, DiaPonto, Periodo

DIAS_SEMANA = {"SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"}

# Cabeçalho de colaborador: "16447 - ABILIO MONTEIRO" ou "Matrícula: 16447  Nome: ABILIO MONTEIRO"
RE_CABECALHO_MAT_NOME = re.compile(
    r"(?:Matr[ií]cula[:\s]+)?(\d{3,8})\s*[-–]\s*([A-ZÀ-Ú][A-ZÀ-Ú\s'\.]{2,60})"
)

# Linha de dia: "21/08 SEX 18:01 00:00 01:00 06:59 ..." — data, dia da semana e até 4 marcações.
RE_LINHA_DIA = re.compile(
    r"^(?P<data>\d{2}/\d{2})\s+(?P<sem>SEG|TER|QUA|QUI|SEX|SAB|DOM)\s+(?P<resto>.*)$"
)
RE_HORA = re.compile(r"\b([0-2]\d:[0-5]\d)\b")

# Bloco de totais do relatório inteiro — precisa ser detectado e descartado,
# nunca absorvido pelo último colaborador da lista (ver nota da skill irmã
# relatorio-operacional-bi sobre o bug do "Total Geral").
RE_TOTAL_GERAL = re.compile(r"TOTAL\s+GERAL", re.IGNORECASE)


class ErroDeLeitura(Exception):
    """Levantado quando o PDF não corresponde ao layout esperado do espelho.

    Preferimos falhar alto a produzir uma apuração de jornada incorreta.
    """


@dataclass
class LinhaBruta:
    pagina: int
    texto: str


def extrair_linhas(caminho_pdf: str, debug: bool = False) -> list[LinhaBruta]:
    """Lê o PDF e devolve todas as linhas de texto, por página.

    Requer o pacote `pdfplumber` (não incluso em requirements.txt até este
    parser ser calibrado com um PDF real — instale com
    ``pip install pdfplumber`` para testar).
    """
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - depende de ambiente
        raise RuntimeError(
            "pdfplumber não instalado. Rode `pip install pdfplumber` para "
            "extrair PDFs do espelho de ponto."
        ) from exc

    linhas: list[LinhaBruta] = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for i, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text() or ""
            for linha in texto.splitlines():
                linha = linha.strip()
                if linha:
                    linhas.append(LinhaBruta(pagina=i, texto=linha))
    if debug:  # pragma: no cover - utilitário manual
        for l in linhas:
            print(f"[p{l.pagina}] {l.texto}")
    return linhas


def _fechar_colaborador(matricula, nome, dias, colaboradores):
    if matricula is None:
        return
    if not dias:
        # colaborador sem nenhum dia lido é sinal de que o layout não bateu
        raise ErroDeLeitura(
            f"Matrícula {matricula} ({nome}) não teve nenhum dia reconhecido — "
            "o layout de colunas provavelmente difere do esperado por este "
            "parser. Rode com --debug e ajuste RE_LINHA_DIA em parser_pdf.py."
        )
    colaboradores.append(
        Colaborador(matricula=matricula, nome=(nome or "").strip(), dias=list(dias))
    )


def parse_espelho_pdf(caminho_pdf: str, debug: bool = False) -> list[Colaborador]:
    """Extrai a lista de colaboradores (com seus dias) de um espelho de ponto.

    Não preenche encarregado/setor/função/mão-de-obra — esses vêm do cadastro
    de efetivo (ver ``efetivo.py``) e são cruzados por matrícula depois.
    """
    linhas = extrair_linhas(caminho_pdf, debug=debug)

    colaboradores: list[Colaborador] = []
    matricula_atual = nome_atual = None
    dias_atual: list[DiaPonto] = []
    dentro_total_geral = False

    for l in linhas:
        texto = l.texto

        if RE_TOTAL_GERAL.search(texto):
            # bloco de somatório do relatório inteiro: fecha o colaborador
            # corrente (se houver) e ignora tudo até o próximo cabeçalho.
            _fechar_colaborador(matricula_atual, nome_atual, dias_atual, colaboradores)
            matricula_atual = nome_atual = None
            dias_atual = []
            dentro_total_geral = True
            continue

        m_cab = RE_CABECALHO_MAT_NOME.match(texto)
        if m_cab:
            _fechar_colaborador(matricula_atual, nome_atual, dias_atual, colaboradores)
            matricula_atual, nome_atual = m_cab.group(1), m_cab.group(2)
            dias_atual = []
            dentro_total_geral = False
            continue

        if dentro_total_geral or matricula_atual is None:
            continue

        m_dia = RE_LINHA_DIA.match(texto)
        if not m_dia:
            continue

        horas = RE_HORA.findall(m_dia.group("resto"))
        dias_atual.append(
            DiaPonto(data=m_dia.group("data"), dia_semana=m_dia.group("sem"), marc=horas)
        )

    _fechar_colaborador(matricula_atual, nome_atual, dias_atual, colaboradores)

    if not colaboradores:
        raise ErroDeLeitura(
            "Nenhum colaborador reconhecido no PDF. Verifique se é de fato um "
            "espelho de ponto do Senior Sistemas e rode com --debug para "
            "inspecionar o texto extraído."
        )
    return colaboradores


def montar_periodo(colaboradores: list[Colaborador], **meta) -> Periodo:
    """Monta o Periodo a partir da lista de colaboradores e metadados do
    cabeçalho do relatório (obra, empresa, cnpj, datas...), fornecidos
    manualmente até o parser extrair esse bloco automaticamente."""
    return Periodo(colaboradores=colaboradores, **meta)
