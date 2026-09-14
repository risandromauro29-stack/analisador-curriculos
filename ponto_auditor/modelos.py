"""
Estruturas de dados do auditor de ponto e conversão para/do formato compacto
usado pelo painel HTML (chaves curtas: trab, falt, e50, e110...).
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields


@dataclass
class DiaPonto:
    data: str                       # "DD/MM"
    dia_semana: str                 # "SEG", "TER"...
    marc: list[str] = field(default_factory=list)   # marcações "HH:MM"
    obs: str = ""                   # observação do espelho (ex.: "ADICIONAL NOTURNO", "DSR")
    codigo_horario: str = ""        # código de escala/ocorrência (hcod no espelho)
    trabalhado: int = 0             # minutos trabalhados (lido do espelho)
    falta: int = 0                  # minutos de falta
    atraso: int = 0                 # minutos de atraso na entrada
    e50: int = 0                    # minutos extras a 50%
    e110: int = 0                   # minutos extras a 110% (domingo/feriado fora do 12x36)
    e_out: int = 0                  # minutos extras em outras faixas (60/70/80/100%)
    adicional_noturno: int = 0      # minutos com adicional noturno
    ajuste: int = 0                 # minutos de ajuste/abono lançados
    intervalo: int | None = None    # minutos de intervalo (registrado ou pré-assinalado)
    intervalo_registrado: bool = False
    intrajornada: int | None = None  # minutos de intervalo entre marcações intermediárias
    interjornada: int | None = None  # minutos de descanso até a jornada seguinte
    jornada: int = 0                # minutos brutos entre 1ª e última marcação
    apuracao: int = 0               # minutos = trabalhado + extras (base de comparação legal)
    saida_prevista: int | None = None  # minuto do dia previsto para a saída (escala)
    atraso_saida: int = 0           # minutos de saída após o previsto
    domingo_feriado: bool = False
    alertas: list[str] = field(default_factory=list)   # preenchido por regras.avaliar_dia
    informativos: list[str] = field(default_factory=list)


@dataclass
class Colaborador:
    matricula: str
    nome: str
    cargo: str = ""
    funcao: str = ""
    encarregado: str = ""
    setor: str = ""
    empresa: str = ""
    mao_de_obra: str = ""           # "DIRETA" | "INDIRETA"
    alojamento: str = ""
    republica: str = ""
    cidade: str = ""
    uf: str = ""
    admissao: str = ""
    experiencia: str = ""
    regime_12x36: bool = False
    cadastrado: bool = True         # False = sem correspondência no efetivo
    escala: list[str] = field(default_factory=list)
    noturno: bool = False
    onibus: bool = False
    pagina_espelho: int | None = None
    dias: list[DiaPonto] = field(default_factory=list)


@dataclass
class Periodo:
    inicio: str
    fim: str
    ano: int
    empresa: str
    cnpj: str
    obra: str
    gerado_em: str
    dias: list[str] = field(default_factory=list)          # ["21/08", "22/08", ...]
    dia_semana_por_data: dict[str, str] = field(default_factory=dict)
    colaboradores: list[Colaborador] = field(default_factory=list)
    sem_cadastro: int = 0


# ---------------------------------------------------------------------------
# Conversão para o formato compacto (DB) consumido pelo template do painel
# ---------------------------------------------------------------------------

def dia_para_db(d: DiaPonto) -> dict:
    return {
        "data": d.data, "sem": d.dia_semana, "marc": d.marc, "obs": d.obs,
        "hcod": d.codigo_horario, "trab": d.trabalhado, "falt": d.falta,
        "atr": d.atraso, "e50": d.e50, "e110": d.e110, "eOut": d.e_out,
        "adnot": d.adicional_noturno, "aj": d.ajuste, "iv": d.intervalo,
        "ivReg": d.intervalo_registrado, "intra": d.intrajornada,
        "inter": d.interjornada, "jorn": d.jornada, "apur": d.apuracao,
        "saidaPrev": d.saida_prevista, "atrSaida": d.atraso_saida,
        "domFer": d.domingo_feriado, "al": d.alertas, "inf": d.informativos,
    }


def colaborador_para_db(c: Colaborador) -> dict:
    dias = [dia_para_db(d) for d in c.dias]
    trab = sum(d["trab"] for d in dias)
    falt = sum(d["falt"] for d in dias)
    atr = sum(d["atr"] for d in dias)
    e50 = sum(d["e50"] for d in dias)
    e110 = sum(d["e110"] for d in dias)
    eOut = sum(d["eOut"] for d in dias)
    adnot = sum(d["adnot"] for d in dias)
    aj = sum(d["aj"] for d in dias)
    extra = e50 + e110 + eOut
    noites = sum(1 for d in dias if d["adnot"] > 0)
    return {
        "mat": c.matricula, "nome": c.nome, "cargo": c.cargo, "funcao": c.funcao,
        "enc": c.encarregado, "setor": c.setor, "empresa": c.empresa,
        "mo": c.mao_de_obra, "aloj": c.alojamento, "rep": c.republica,
        "cidade": c.cidade, "uf": c.uf, "adm": c.admissao, "exp": c.experiencia,
        "r12": c.regime_12x36, "cad": c.cadastrado, "hor": c.escala,
        "trab": trab, "falt": falt, "atr": atr, "e50": e50, "e110": e110,
        "eOut": eOut, "adnot": adnot, "extra": extra, "aj": aj,
        "trabSist": trab, "extraSist": extra, "not": c.noturno,
        "nNoites": noites, "viradas": noites, "entMed": 0, "bus": c.onibus,
        "pag": c.pagina_espelho, "dias": dias,
    }


def db_para_dia(d: dict) -> DiaPonto:
    return DiaPonto(
        data=d["data"], dia_semana=d["sem"], marc=list(d.get("marc") or []),
        obs=d.get("obs", ""), codigo_horario=d.get("hcod", ""),
        trabalhado=d.get("trab", 0), falta=d.get("falt", 0), atraso=d.get("atr", 0),
        e50=d.get("e50", 0), e110=d.get("e110", 0), e_out=d.get("eOut", 0),
        adicional_noturno=d.get("adnot", 0), ajuste=d.get("aj", 0),
        intervalo=d.get("iv"), intervalo_registrado=bool(d.get("ivReg")),
        intrajornada=d.get("intra"), interjornada=d.get("inter"),
        jornada=d.get("jorn") or 0, apuracao=d.get("apur") or 0,
        saida_prevista=d.get("saidaPrev"), atraso_saida=d.get("atrSaida", 0),
        domingo_feriado=bool(d.get("domFer")),
        alertas=list(d.get("al") or []), informativos=list(d.get("inf") or []),
    )


def db_para_colaborador(e: dict) -> Colaborador:
    return Colaborador(
        matricula=e["mat"], nome=e["nome"], cargo=e.get("cargo", ""),
        funcao=e.get("funcao", ""), encarregado=e.get("enc", ""),
        setor=e.get("setor", ""), empresa=e.get("empresa", ""),
        mao_de_obra=e.get("mo", ""), alojamento=e.get("aloj", ""),
        republica=e.get("rep", ""), cidade=e.get("cidade", ""), uf=e.get("uf", ""),
        admissao=e.get("adm", ""), experiencia=e.get("exp", ""),
        regime_12x36=bool(e.get("r12")), cadastrado=bool(e.get("cad", True)),
        escala=list(e.get("hor") or []), noturno=bool(e.get("not")),
        onibus=bool(e.get("bus")), pagina_espelho=e.get("pag"),
        dias=[db_para_dia(d) for d in e.get("dias", [])],
    )


def db_para_periodo(db: dict) -> Periodo:
    meta = db["meta"]
    return Periodo(
        inicio=meta["ini"], fim=meta["fim"], ano=meta["ano"], empresa=meta["empresa"],
        cnpj=meta.get("cnpj", ""), obra=meta.get("obra", ""), gerado_em=meta.get("gerado", ""),
        dias=list(meta.get("dias") or []), dia_semana_por_data=dict(meta.get("sem") or {}),
        sem_cadastro=meta.get("semcad", 0),
        colaboradores=[db_para_colaborador(e) for e in db.get("emp", [])],
    )


def periodo_para_db(p: Periodo) -> dict:
    meta = {
        "periodo": f"{p.inicio} a {p.fim}", "ini": p.inicio, "fim": p.fim,
        "ano": p.ano, "empresa": p.empresa, "cnpj": p.cnpj, "obra": p.obra,
        "total": len(p.colaboradores), "semcad": p.sem_cadastro,
        "gerado": p.gerado_em, "dias": p.dias, "sem": p.dia_semana_por_data,
    }
    return {"meta": meta, "emp": [colaborador_para_db(c) for c in p.colaboradores]}
