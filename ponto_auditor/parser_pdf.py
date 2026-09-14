"""
Extração do "Cartão Ponto" / espelho de ponto (Senior Sistemas) em PDF.

Layout confirmado contra um PDF real cedido pelo usuário (uma página por
colaborador, tabela diária com Data/Sem/Hor/Marcações + Trabalho/Faltas/
Atrasos + Extras 50/60/70/80/100/110% + Adic. Not, fechando com um bloco
"Totais de Horas"). A extração usa a POSIÇÃO horizontal de cada palavra
(via pdfplumber), não a ordem do texto plano: colunas de tabela em PDF não
garantem que o texto saia na ordem visual quando lido em uma única string,
então cada palavra é classificada pela banda de coluna em que seu x0 cai.

As bandas de coluna são detectadas dinamicamente a partir da própria linha
de cabeçalho da tabela ("Data Sem Hor Marcações Trabalho Faltas Atrasos
50% 60% 70% 80% 100% 110% Adic. Not") em vez de fixadas em pontos, para
tolerar pequenas variações de margem entre exportações.

Ver tests/test_parser_pdf.py: reproduz esse layout sinteticamente (mesmos
nomes de coluna, dados de 6 colaboradores reais com nomes trocados) e
confere a extração + ponto_auditor.calculos contra os valores originais.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .modelos import Colaborador, DiaPonto, Periodo

DIAS_SEMANA = ("SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM")

RE_DATA = re.compile(r"^\d{2}/\d{2}$")
RE_HORA = re.compile(r"^-?\d{1,3}:\d{2}$")
RE_HCOD = re.compile(r"^\d{4}$")

RE_PERIODO = re.compile(r"Per[ií]odo\s*:\s*(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})")
RE_PAGINA = re.compile(r"P[áa]g\.?:\s*(\d+)")
RE_EMPREGADOR = re.compile(r"Empregador:\s*\d+\s+(.+?)(?:\s{2,}|\s+CNPJ:|$)")
RE_CNPJ = re.compile(r"CNPJ:\s*([\d./-]+)")
RE_EMPREGADO = re.compile(r"Emprega?do:\s*(\d{2,8})\s+(.+?)(?:\s{2,}|\s+CTPS:|$)")
RE_CARGO = re.compile(r"Cargo:\s*(.+?)\s{2,}Localiza")
RE_MOD = re.compile(r"MOD\s+(.+)$")

# Nomes de coluna esperados no cabeçalho da tabela — usados para achar as
# bandas horizontais (não a posição em si, que varia por exportação).
COLUNAS_TABELA = {
    "Data": "data", "Sem": "sem", "Hor": "hor", "Marcações": "marc",
    "Trabalho": "trab", "Faltas": "falt", "Atrasos": "atr",
    "50%": "e50", "60%": "e60", "70%": "e70", "80%": "e80",
    "100%": "e100", "110%": "e110",
}


class ErroDeLeitura(Exception):
    """Levantado quando o PDF não corresponde ao layout esperado do espelho.

    Preferimos falhar alto a produzir uma apuração de jornada incorreta.
    """


@dataclass
class _Pagina:
    numero: int
    palavras: list[dict] = field(default_factory=list)
    linhas_texto: list[str] = field(default_factory=list)


def _extrair_paginas(caminho_pdf: str) -> list[_Pagina]:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise RuntimeError(
            "pdfplumber não instalado. Rode `pip install pdfplumber`."
        ) from exc

    paginas = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for i, pagina in enumerate(pdf.pages, start=1):
            palavras = pagina.extract_words(keep_blank_chars=False, use_text_flow=False)
            texto = pagina.extract_text() or ""
            paginas.append(_Pagina(numero=i, palavras=palavras, linhas_texto=texto.splitlines()))
    return paginas


def _agrupar_em_linhas(palavras: list[dict], tolerancia: float = 2.5) -> list[list[dict]]:
    """Agrupa palavras na mesma linha visual (mesmo 'top', com tolerância),
    ordenadas da esquerda para a direita."""
    ordenadas = sorted(palavras, key=lambda w: (w["top"], w["x0"]))
    linhas: list[list[dict]] = []
    for w in ordenadas:
        if linhas and abs(w["top"] - linhas[-1][0]["top"]) <= tolerancia:
            linhas[-1].append(w)
        else:
            linhas.append([w])
    for linha in linhas:
        linha.sort(key=lambda w: w["x0"])
    return linhas


def _detectar_bandas(linhas: list[list[dict]]) -> tuple[int, dict[str, tuple[float, float]]] | None:
    """Acha a linha de cabeçalho da tabela e devolve (índice_da_linha,
    {campo: (x_inicio, x_fim)}). x_fim da última banda é +inf."""
    for idx, linha in enumerate(linhas):
        textos = {w["text"] for w in linha}
        if {"Data", "Marcações", "Trabalho"} <= textos:
            achadas: dict[str, float] = {}
            for w in linha:
                campo = COLUNAS_TABELA.get(w["text"])
                if campo and campo not in achadas:
                    achadas[campo] = w["x0"]
            # "Adic." e "Not" podem estar em palavras separadas
            adic = next((w for w in linha if w["text"].startswith("Adic")), None)
            if adic:
                achadas["adnot"] = adic["x0"]
            if len(achadas) < 8:
                continue
            ordenadas = sorted(achadas.items(), key=lambda kv: kv[1])
            bandas = {}
            for i, (campo, x0) in enumerate(ordenadas):
                x_fim = ordenadas[i + 1][1] if i + 1 < len(ordenadas) else float("inf")
                bandas[campo] = (x0 - 4, x_fim - 4)  # -4: tolerância p/ largura do rótulo
            return idx, bandas
    return None


def _campo_da_banda(x0: float, bandas: dict[str, tuple[float, float]]) -> str | None:
    for campo, (ini, fim) in bandas.items():
        if ini <= x0 < fim:
            return campo
    return None


def _hm_para_minutos(txt: str) -> int:
    neg = txt.startswith("-")
    txt = txt.lstrip("-")
    h, m = txt.split(":")
    valor = int(h) * 60 + int(m)
    return -valor if neg else valor


def _parse_cabecalho_pagina(linhas_texto: list[str]) -> dict:
    info: dict = {}
    for linha in linhas_texto:
        if m := RE_PERIODO.search(linha):
            info["ini"], info["fim"] = m.group(1), m.group(2)
        if m := RE_PAGINA.search(linha):
            info["pagina"] = int(m.group(1))
        if m := RE_EMPREGADOR.search(linha):
            info["empresa"] = m.group(1).strip()
        if m := RE_CNPJ.search(linha):
            info["cnpj"] = m.group(1).strip()
        if m := RE_EMPREGADO.search(linha):
            info["matricula"], info["nome"] = m.group(1).strip(), m.group(2).strip()
        if m := RE_CARGO.search(linha):
            info["cargo"] = m.group(1).strip()
        if m := RE_MOD.search(linha):
            info["obra"] = m.group(1).strip()
    return info


def _parse_escala(linhas_texto: list[str]) -> list[str]:
    escala = []
    dentro = False
    for linha in linhas_texto:
        if linha.strip().startswith("Horários"):
            dentro = True
            continue
        if dentro:
            if re.match(r"^\d{4}\s+\d{2}:\d{2}", linha.strip()):
                escala.append(linha.strip())
            else:
                break
    return escala


def _parse_dias_da_pagina(pagina: _Pagina) -> list[DiaPonto]:
    linhas = _agrupar_em_linhas(pagina.palavras)
    achou = _detectar_bandas(linhas)
    if achou is None:
        return []
    idx_cabecalho, bandas = achou

    dias: list[DiaPonto] = []
    for linha in linhas[idx_cabecalho + 1:]:
        primeiro_texto = linha[0]["text"]
        if primeiro_texto.startswith("Totais"):
            break
        if not RE_DATA.match(primeiro_texto):
            continue  # linha de rodapé/assinatura ou continuação — ignora

        valores: dict[str, list[str]] = {}
        for w in linha:
            campo = _campo_da_banda(w["x0"], bandas)
            if campo:
                valores.setdefault(campo, []).append(w["text"])

        data = valores.get("data", [""])[0]
        sem = valores.get("sem", [""])[0]
        hcod = valores.get("hor", [""])[0]
        tokens_marc = valores.get("marc", [])
        marc = [t for t in tokens_marc if re.match(r"^\d{2}:\d{2}$", t)]
        obs = " ".join(t for t in tokens_marc if not re.match(r"^\d{2}:\d{2}$", t))

        def hm(campo: str) -> int:
            vals = [v for v in valores.get(campo, []) if RE_HORA.match(v)]
            return _hm_para_minutos(vals[0]) if vals else 0

        dias.append(DiaPonto(
            data=data, dia_semana=sem, marc=marc, obs=obs, codigo_horario=hcod,
            trabalhado=hm("trab"), falta=hm("falt"), atraso=hm("atr"),
            e50=hm("e50"), e110=hm("e110"),
            e_out=hm("e60") + hm("e70") + hm("e80") + hm("e100"),
            adicional_noturno=hm("adnot"),
        ))
    return dias


def parse_espelho_pdf(caminho_pdf: str, debug: bool = False) -> Periodo:
    paginas = _extrair_paginas(caminho_pdf)
    if debug:  # pragma: no cover - utilitário manual
        for p in paginas:
            print(f"--- página {p.numero} ---")
            for l in p.linhas_texto:
                print(l)

    colaboradores: list[Colaborador] = []
    meta_geral: dict = {}

    for pagina in paginas:
        info = _parse_cabecalho_pagina(pagina.linhas_texto)
        if "matricula" not in info:
            continue  # página sem cabeçalho de colaborador (ex.: capa, resumo)

        for chave in ("ini", "fim", "empresa", "cnpj"):
            if chave in info and chave not in meta_geral:
                meta_geral[chave] = info[chave]
        if "obra" in info and "obra" not in meta_geral:
            meta_geral["obra"] = info["obra"]

        dias = _parse_dias_da_pagina(pagina)
        if not dias:
            raise ErroDeLeitura(
                f"Página {pagina.numero}: colaborador {info['matricula']} "
                f"({info.get('nome','?')}) sem nenhum dia reconhecido na tabela — "
                "o layout de colunas pode diferir do esperado. Rode com --debug."
            )

        colaboradores.append(Colaborador(
            matricula=info["matricula"], nome=info.get("nome", ""),
            cargo=info.get("cargo", ""), escala=_parse_escala(pagina.linhas_texto),
            dias=dias,
        ))

    if not colaboradores:
        raise ErroDeLeitura(
            "Nenhum colaborador reconhecido no PDF. Verifique se é de fato um "
            "Cartão Ponto/espelho do Senior Sistemas e rode com --debug."
        )

    dias_periodo = sorted({d.data for c in colaboradores for d in c.dias})
    dia_semana_por_data = {d.data: d.dia_semana for c in colaboradores for d in c.dias}
    ano = 0
    if meta_geral.get("ini"):
        ano = int(meta_geral["ini"].split("/")[-1])

    return Periodo(
        inicio=meta_geral.get("ini", ""), fim=meta_geral.get("fim", ""), ano=ano,
        empresa=meta_geral.get("empresa", ""), cnpj=meta_geral.get("cnpj", ""),
        obra=meta_geral.get("obra", ""), gerado_em="",
        dias=dias_periodo, dia_semana_por_data=dia_semana_por_data,
        colaboradores=colaboradores,
    )
