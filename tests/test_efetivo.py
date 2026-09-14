from ponto_auditor.efetivo import aplicar_efetivo, carregar_efetivo
from ponto_auditor.modelos import Colaborador


def _criar_planilha(tmp_path):
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Matrícula", "Nome", "Encarregado", "Setor", "Função", "Mão de obra"])
    ws.append(["80101", "JOAO CARLOS DA SILVA", "PEDRO ENCARREGADO", "TERRAPLENAGEM", "CARPINTEIRO", "direta"])
    caminho = tmp_path / "efetivo.xlsx"
    wb.save(caminho)
    return caminho


def test_carrega_e_cruza_por_matricula(tmp_path):
    caminho = _criar_planilha(tmp_path)
    registros = carregar_efetivo(str(caminho))
    assert registros["80101"]["encarregado"] == "PEDRO ENCARREGADO"

    colaboradores = [
        Colaborador(matricula="80101", nome="JOAO CARLOS DA SILVA"),
        Colaborador(matricula="99999", nome="SEM CADASTRO NA PLANILHA"),
    ]
    sem_cadastro = aplicar_efetivo(colaboradores, registros)

    achado, nao_achado = colaboradores
    assert achado.encarregado == "PEDRO ENCARREGADO"
    assert achado.setor == "TERRAPLENAGEM"
    assert achado.mao_de_obra == "DIRETA"  # normalizado para maiúsculas
    assert achado.cadastrado is True

    assert nao_achado.cadastrado is False
    assert sem_cadastro == 1
