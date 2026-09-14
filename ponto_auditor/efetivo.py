"""
Lê a planilha de "efetivo ativo" (cadastro de colaboradores) e cruza por
matrícula com os colaboradores extraídos do espelho de ponto, preenchendo
encarregado, setor/frente, função, mão de obra e demais dados cadastrais —
o PDF do espelho traz apenas matrícula, nome e códigos de horário.
"""
from __future__ import annotations

from .modelos import Colaborador

# nome de coluna (minúsculo, sem acento/espaço) -> atributo de Colaborador
MAPA_COLUNAS = {
    "matricula": "matricula", "matrícula": "matricula", "mat": "matricula",
    "nome": "nome",
    "cargo": "cargo",
    "funcao": "funcao", "função": "funcao",
    "encarregado": "encarregado", "enc": "encarregado",
    "setor": "setor", "setorfrente": "setor", "frente": "setor",
    "empresa": "empresa",
    "maodeobra": "mao_de_obra", "mo": "mao_de_obra",
    "alojamento": "alojamento", "aloj": "alojamento",
    "republica": "republica", "rep": "republica",
    "cidade": "cidade",
    "uf": "uf",
    "admissao": "admissao", "admissão": "admissao", "adm": "admissao",
    "experiencia": "experiencia", "experiência": "experiencia", "exp": "experiencia",
}


def _norm(s) -> str:
    s = str(s or "").strip().lower()
    for a, b in (("á", "a"), ("â", "a"), ("ã", "a"), ("é", "e"), ("ê", "e"),
                 ("í", "i"), ("ó", "o"), ("ô", "o"), ("õ", "o"), ("ú", "u"), ("ç", "c")):
        s = s.replace(a, b)
    return s.replace(" ", "").replace("_", "").replace("-", "").replace("/", "")


def carregar_efetivo(caminho_xlsx: str, aba: str | None = None) -> dict[str, dict]:
    """Retorna {matricula: {atributo: valor}} lido da planilha de efetivo."""
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("openpyxl não instalado. Rode `pip install openpyxl`.") from exc

    wb = openpyxl.load_workbook(caminho_xlsx, data_only=True, read_only=True)
    ws = wb[aba] if aba else wb.active

    linhas = ws.iter_rows(values_only=True)
    cabecalho = next(linhas)
    colunas = [MAPA_COLUNAS.get(_norm(c)) for c in cabecalho]

    registros: dict[str, dict] = {}
    for linha in linhas:
        registro = {}
        for campo, valor in zip(colunas, linha):
            if campo and valor is not None:
                registro[campo] = str(valor).strip() if not isinstance(valor, bool) else valor
        matricula = registro.get("matricula")
        if matricula:
            registros[matricula] = registro
    return registros


def aplicar_efetivo(colaboradores: list[Colaborador], registros: dict[str, dict]) -> int:
    """Preenche in-place os campos cadastrais de cada colaborador a partir do
    dicionário {matricula: {...}} de carregar_efetivo(). Retorna a
    quantidade de colaboradores SEM correspondência (cad=False)."""
    sem_cadastro = 0
    for c in colaboradores:
        dados = registros.get(c.matricula)
        if not dados:
            c.cadastrado = False
            sem_cadastro += 1
            continue
        for campo, valor in dados.items():
            if campo == "matricula" or not valor:
                continue
            if campo == "mao_de_obra":
                valor = str(valor).strip().upper()
            setattr(c, campo, valor)
    return sem_cadastro
