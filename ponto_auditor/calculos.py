"""
Deriva os campos que o espelho de ponto NÃO traz prontos — intervalo
(iv/intra), interjornada (inter), jornada bruta (jorn), jornada apurada
(apur), saída prevista (saidaPrev) e atraso de saída (atrSaida) — a partir
das marcações e da escala cadastrada de cada colaborador.

As fórmulas abaixo foram decifradas comparando um PDF real do "Cartão
Ponto" (Senior Sistemas) com os valores já calculados para o mesmo
colaborador/período no painel de referência: para cada campo, testei a
hipótese contra os dias reais até bater exatamente. Ver
tests/test_parser_pdf.py, que reproduz esse PDF sinteticamente (com nomes
trocados) e confere os 21 dias de 6 colaboradores contra os valores
originais.
"""
from __future__ import annotations

from .modelos import Colaborador, DiaPonto
from .regras import extras_do_dia

FERIADO_HCOD = "9997"


def _minutos(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _ajustar_meia_noite(marc: list[str]) -> list[int]:
    """Converte marcações 'HH:MM' em minutos corridos, empurrando +24h toda
    vez que uma marcação aparenta "voltar no tempo" — mesma lógica usada
    no painel de referência (função adjm) para jornadas que cruzam a
    meia-noite (turnos noturnos, 12x36)."""
    brutos = [_minutos(t) for t in marc]
    ajustadas: list[int] = []
    base = 0
    for i, v in enumerate(brutos):
        vv = v + base
        if i > 0 and vv < ajustadas[i - 1]:
            base += 1440
            vv = v + base
        ajustadas.append(vv)
    return ajustadas


def _escala_por_codigo(colaborador: Colaborador) -> dict[str, list[int]]:
    """{codigo_horario: [minutos_do_token1, minutos_do_token2, ...]} a
    partir das linhas 'hor' do cadastro, ex.: '0205  07:00 11:00 12:00 16:00'."""
    escalas: dict[str, list[int]] = {}
    for linha in colaborador.escala:
        partes = linha.split()
        if not partes:
            continue
        codigo, tokens = partes[0], partes[1:]
        try:
            escalas[codigo] = [_minutos(t) for t in tokens]
        except ValueError:
            continue
    return escalas


def _tem_escala_12h_ou_mais(escalas: dict[str, list[int]]) -> bool:
    """Regime 12x36 identificado automaticamente quando alguma escala
    cadastrada cobre 11h ou mais entre o primeiro e o último horário."""
    for tokens in escalas.values():
        if len(tokens) < 2:
            continue
        ajustados: list[int] = []
        base = 0
        for i, v in enumerate(tokens):
            vv = v + base
            if i > 0 and vv < ajustados[i - 1]:
                base += 1440
                vv = v + base
            ajustados.append(vv)
        if ajustados[-1] - ajustados[0] >= 11 * 60:
            return True
    return False


def aplicar_calculos(colaborador: Colaborador) -> None:
    """Preenche in-place iv/ivReg/intra/inter/jorn/apur/saidaPrev/atrSaida/
    domingo_feriado/regime_12x36 de cada dia. `colaborador.dias` deve estar
    em ordem cronológica (é a ordem natural das linhas do espelho de
    ponto)."""
    escalas = _escala_por_codigo(colaborador)
    colaborador.regime_12x36 = _tem_escala_12h_ou_mais(escalas)
    ultimo_fim_absoluto: int | None = None

    for indice_dia, dia in enumerate(colaborador.dias):
        dia.domingo_feriado = (
            dia.dia_semana == "DOM"
            or dia.codigo_horario == FERIADO_HCOD
            or "feriado" in dia.obs.lower()
        )

        escala_tokens = escalas.get(dia.codigo_horario)
        dia.saida_prevista = escala_tokens[-1] if escala_tokens else None

        if not dia.marc:
            dia.iv = dia.intrajornada = dia.interjornada = None
            dia.intervalo_registrado = False
            dia.jornada = 0
            dia.apuracao = 0
            dia.atraso_saida = 0
            continue

        ajustadas = _ajustar_meia_noite(dia.marc)
        dia.jornada = ajustadas[-1] - ajustadas[0]
        dia.apuracao = dia.trabalhado + extras_do_dia(dia)

        # intervalo / intrajornada
        if len(dia.marc) >= 4 and len(dia.marc) % 2 == 0:
            gaps = [ajustadas[i + 1] - ajustadas[i] for i in range(1, len(ajustadas) - 1, 2)]
            dia.intrajornada = sum(gaps)
            dia.intervalo = dia.intrajornada
            dia.intervalo_registrado = True
        elif len(dia.marc) == 2:
            dia.intrajornada = None
            dia.intervalo_registrado = False
            dia.intervalo = (
                escala_tokens[2] - escala_tokens[1]
                if escala_tokens and len(escala_tokens) >= 4
                else None
            )
        else:
            dia.intrajornada = None
            dia.intervalo = None
            dia.intervalo_registrado = False

        # atraso de saída: comparação simples no relógio de 24h (sem ajuste
        # de virada — confirmado contra dias de regime 12x36 no PDF real)
        ultima_marcacao_raw = _minutos(dia.marc[-1])
        dia.atraso_saida = (
            max(0, ultima_marcacao_raw - dia.saida_prevista)
            if dia.saida_prevista is not None
            else 0
        )

        # interjornada: usa uma linha do tempo absoluta (dia * 1440 +
        # minuto). Precisa de ao menos 2 marcações para estabelecer início
        # e fim de jornada — um dia com uma única batida solta não serve
        # nem como origem nem como destino do cálculo. Fora essa exigência
        # mínima, o valor é calculado mesmo em dias com número ímpar de
        # batidas (a regra de conformidade "inter" é que ignora esses dias
        # — ver regras.avaliar_dia — o campo em si continua preenchido,
        # como confirmado contra o backend original).
        if len(dia.marc) >= 2:
            primeira_absoluta = indice_dia * 1440 + ajustadas[0]
            dia.interjornada = (
                primeira_absoluta - ultimo_fim_absoluto
                if ultimo_fim_absoluto is not None
                else None
            )
            ultimo_fim_absoluto = indice_dia * 1440 + ajustadas[-1]
        else:
            dia.interjornada = None
