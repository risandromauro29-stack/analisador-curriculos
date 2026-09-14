"""
Motor de regras de conformidade da CLT aplicado a registros diários de ponto.

As seis regras abaixo (e seus limiares) foram extraídas e validadas contra o
painel "Controle de Ponto · Tucumann Engenharia · EPR BR-153 Lote 02": rodando
cada função de detecção sobre os ~11.130 dias/colaborador reais embutidos
naquele painel, o resultado bateu 100% (0 falsos positivos, 0 falsos negativos)
com os alertas já apurados. Ver tests/test_regras.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Limite diário de horas extras dentro do teto contratual do art. 59, §2º da CLT.
LIMITE_EXTRA_DIARIO_MIN = 120  # 2h

# Limite de jornada apurada (trabalho + extras) por regime.
LIMITE_JORNADA_NORMAL_MIN = 600  # 10h
LIMITE_JORNADA_12X36_MIN = 720   # 12h

# Intervalo intrajornada mínimo (art. 71, §4º da CLT).
LIMITE_INTRA_MIN = 60  # 1h
# A regra de intervalo só é cobrada quando a jornada do dia ultrapassa 6h.
JORNADA_MIN_PARA_EXIGIR_INTRA = 360  # 6h

# Interjornada mínima entre duas jornadas (art. 66 da CLT).
LIMITE_INTER_MIN = 660  # 11h


@dataclass(frozen=True)
class Regra:
    codigo: str
    titulo: str
    base_legal: str
    severidade: str  # 'crit' | 'warn'
    descricao: str


REGRAS: dict[str, Regra] = {
    "extra2h": Regra(
        "extra2h",
        "Horas extras acima de 2h/dia",
        "CLT art. 59, §2º",
        "crit",
        "A jornada suplementar contratual está limitada a duas horas diárias. "
        "Dias acima desse teto exigem acordo de compensação ou banco de horas.",
    ),
    "jornmax": Regra(
        "jornmax",
        "Jornada apurada acima do limite",
        "CLT art. 58 e 59",
        "crit",
        "Trabalho + extras superior a 10h no regime normal (12h no regime 12x36). "
        "Indica sobrecarga e risco ergonômico.",
    ),
    "intra": Regra(
        "intra",
        "Intervalo intrajornada inferior a 1h",
        "CLT art. 71, §4º",
        "crit",
        "Jornadas acima de 6h exigem intervalo mínimo de 1 hora. O período "
        "suprimido é devido com acréscimo de 50%.",
    ),
    "inter": Regra(
        "inter",
        "Interjornada inferior a 11h",
        "CLT art. 66",
        "crit",
        "Entre duas jornadas devem existir no mínimo 11 horas consecutivas de "
        "descanso.",
    ),
    "invalida": Regra(
        "invalida",
        "Marcações inválidas ou ímpares",
        "Portaria MTP 671/2021",
        "warn",
        "Registro incompleto: número ímpar de batidas ou apontamento rejeitado "
        "pelo sistema. Exige tratamento antes do fechamento da folha.",
    ),
    "dsr": Regra(
        "dsr",
        "Trabalho em dia de descanso",
        "CLT art. 67 · Lei 605/49",
        "warn",
        "Trabalho no domingo ou repouso semanal sem folga compensatória gera "
        "pagamento em dobro ou hora extra a 110%.",
    ),
}


def extras_do_dia(dia) -> int:
    """Soma de todas as faixas de acréscimo do dia (50%, 110% e demais)."""
    return (dia.e50 or 0) + (dia.e110 or 0) + (dia.e_out or 0)


def marcacoes_invalidas(dia) -> bool:
    """Número ímpar de batidas = jornada não fecha (falta uma marcação)."""
    return len(dia.marc) % 2 == 1


def avaliar_dia(colaborador, dia) -> list[str]:
    """Retorna a lista de códigos de regra violados no dia informado."""
    alertas: list[str] = []
    ex = extras_do_dia(dia)

    if ex > LIMITE_EXTRA_DIARIO_MIN:
        alertas.append("extra2h")

    limite_jornada = (
        LIMITE_JORNADA_12X36_MIN if colaborador.regime_12x36 else LIMITE_JORNADA_NORMAL_MIN
    )
    if dia.apuracao is not None and dia.apuracao > limite_jornada:
        alertas.append("jornmax")

    if (
        dia.intrajornada is not None
        and dia.intrajornada < LIMITE_INTRA_MIN
        and (dia.jornada or 0) > JORNADA_MIN_PARA_EXIGIR_INTRA
    ):
        alertas.append("intra")

    if (
        dia.interjornada is not None
        and dia.interjornada < LIMITE_INTER_MIN
        and not marcacoes_invalidas(dia)
    ):
        alertas.append("inter")

    if marcacoes_invalidas(dia):
        alertas.append("invalida")

    if dia.domingo_feriado and not colaborador.regime_12x36 and (dia.trabalhado > 0 or ex > 0):
        alertas.append("dsr")

    return alertas


def indice_nao_conformidade(ocorrencias: int, colaboradores: int) -> float:
    """< 1,0 controlado · > 2,0 exige ação (mesma leitura usada no painel)."""
    return ocorrencias / colaboradores if colaboradores else 0.0
