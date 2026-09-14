"""
Gera tests/fixtures/cartao_ponto_amostra.pdf — um PDF sintético que reproduz
fielmente o layout do "Cartão Ponto" (Senior Sistemas) real mostrado pelo
usuário, usando dados de dias reais (nomes e matrículas trocados por
fictícios) extraídos do painel de referência.

Serve para testar parser_pdf.py+calculos.py de ponta a ponta sem depender de
um arquivo real: os valores de "Trabalho"/"Faltas"/"Atrasos"/percentuais de
hora extra/adicional noturno impressos aqui foram lidos do mesmo backend que
gerou o painel original, então o parser + calculos.py devem re-derivar
iv/intra/inter/jorn/apur/saidaPrev/atrSaida e os alertas de regras
IDÊNTICOS aos que já estavam no painel (ver tests/test_parser_pdf.py).

Rode `python tests/fixtures/gerar_pdf_amostra.py` para regenerar o PDF.
"""
import json
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

AQUI = Path(__file__).parent
FONTE_JSON = AQUI / "cartao_ponto_amostra_fonte.json"
DESTINO_PDF = AQUI / "cartao_ponto_amostra.pdf"

PAGE_W, PAGE_H = landscape(A4)
ML = 30  # margem esquerda

# --- posições de coluna da tabela diária (mesmo layout do PDF real) -------
COL = {
    "data": ML, "sem": ML + 34, "hor": ML + 64, "marc": ML + 98,
    "trab": ML + 380, "falt": ML + 425, "atr": ML + 470,
    "e50": ML + 525, "e60": ML + 565, "e70": ML + 605, "e80": ML + 645,
    "e100": ML + 690, "e110": ML + 735, "adnot": ML + 780,
}


def hm(minutos: int, largura: int = 2) -> str:
    sinal = "-" if minutos < 0 else ""
    minutos = abs(minutos)
    return f"{sinal}{minutos // 60:0{largura}d}:{minutos % 60:02d}"


def coluna_extra(obs: str) -> str:
    """Em que sub-coluna de percentual o valor de e_out cai, a julgar pelo obs."""
    for pct, col in (("110%", "e110"), ("100%", "e100"), ("80%", "e80"),
                      ("70%", "e70"), ("60%", "e60"), ("50%", "e50")):
        if pct in obs:
            return col
    return "e70"  # fallback neutro quando o obs não especifica percentual


def desenhar_pagina(c: canvas.Canvas, meta: dict, emp: dict, pagina: int):
    y = PAGE_H - 40
    c.setFont("Helvetica-Bold", 14)
    c.drawString(ML, y, "Cartão Ponto")
    c.setFont("Helvetica", 10)
    c.drawCentredString(PAGE_W / 2, y, f"Período : {meta['ini']}   a   {meta['fim']}")
    c.drawRightString(PAGE_W - ML, y, f"Pág.:    {pagina}")

    y -= 22
    c.setFont("Helvetica", 8.5)
    c.drawString(ML, y, f"Empregador: 0002   {meta['empresa']}")
    c.drawString(PAGE_W - 260, y, f"CNPJ: {meta['cnpj']}")
    y -= 14
    c.drawString(ML, y, "Endereço: TRES MARIAS                    868    Cidade: CURITIBA                    - PR")

    y -= 20
    c.setFont("Helvetica", 8.5)
    c.drawString(ML, y, f"Empregado:    {emp['mat']}   {emp['nome']}")
    c.drawString(PAGE_W - 260, y, "CTPS: 000098525   -0017  001")
    y -= 14
    c.drawString(ML, y, f"Cargo: {emp['cargo']}          Localização: 02.2.211.1          MOD EPR Duplicação Lote 02")

    y -= 18
    c.drawString(ML, y, "Horários:")
    for linha_hor in emp["hor"]:
        y -= 12
        c.drawString(ML + 55, y, linha_hor)

    y -= 20
    c.line(ML, y, PAGE_W - ML, y)
    y -= 12
    c.setFont("Helvetica-Bold", 7.5)
    for chave, rotulo in [("data", "Data"), ("sem", "Sem"), ("hor", "Hor"),
                           ("marc", "Marcações"), ("trab", "Trabalho"),
                           ("falt", "Faltas"), ("atr", "Atrasos")]:
        c.drawString(COL[chave], y, rotulo)
    c.drawCentredString((COL["e50"] + COL["e110"]) / 2, y + 9, "Horas Extras")
    for chave, rotulo in [("e50", "50%"), ("e60", "60%"), ("e70", "70%"),
                           ("e80", "80%"), ("e100", "100%"), ("e110", "110%")]:
        c.drawString(COL[chave], y, rotulo)
    c.drawString(COL["adnot"], y, "Adic. Not")
    y -= 4
    c.line(ML, y, PAGE_W - ML, y)
    y -= 12

    c.setFont("Helvetica", 7.5)
    tot = {"trab": 0, "falt": 0, "atr": 0, "e50": 0, "e60": 0, "e70": 0,
           "e80": 0, "e100": 0, "e110": 0, "adnot": 0}
    for d in emp["dias"]:
        c.drawString(COL["data"], y, d["data"])
        c.drawString(COL["sem"], y, d["sem"])
        c.drawString(COL["hor"], y, d["hcod"])

        marc_txt = " ".join(d["marc"])
        texto_marc = f"{marc_txt}  {d['obs']}".strip() if marc_txt else d["obs"]
        c.drawString(COL["marc"], y, texto_marc)

        if d["trab"]:
            c.drawString(COL["trab"], y, hm(d["trab"]))
            tot["trab"] += d["trab"]
        if d["falt"]:
            c.drawString(COL["falt"], y, hm(d["falt"]))
            tot["falt"] += d["falt"]
        if d["atr"]:
            c.drawString(COL["atr"], y, hm(d["atr"]))
            tot["atr"] += d["atr"]
        if d["e50"]:
            c.drawString(COL["e50"], y, hm(d["e50"]))
            tot["e50"] += d["e50"]
        if d.get("eOut"):
            col = coluna_extra(d["obs"])
            c.drawString(COL[col], y, hm(d["eOut"]))
            tot[col] += d["eOut"]
        if d["e110"]:
            c.drawString(COL["e110"], y, hm(d["e110"]))
            tot["e110"] += d["e110"]
        if d["adnot"]:
            c.drawString(COL["adnot"], y, hm(d["adnot"]))
            tot["adnot"] += d["adnot"]
        y -= 11
        if y < 90:
            break  # (amostra didática — sem paginação de continuação)

    y -= 8
    c.line(ML, y, PAGE_W - ML, y)
    y -= 12
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(ML, y, "Totais de Horas")
    c.drawString(COL["trab"], y, "Trabalho")
    c.drawString(COL["trab"] + 45, y, hm(tot["trab"], 3))
    c.drawString(COL["e50"], y, "Extras 50%")
    c.drawString(COL["e50"] + 55, y, hm(tot["e50"], 3))
    c.drawString(COL["e80"], y, "Extras 80%")
    c.drawString(COL["e80"] + 55, y, hm(tot["e80"], 3))
    c.drawString(COL["adnot"], y, "Adicional Noturno")
    c.drawString(COL["adnot"] + 85, y, hm(tot["adnot"], 3))
    y -= 12
    c.drawString(ML, y, "Faltas")
    c.drawString(COL["trab"] + 45, y, hm(tot["falt"], 3))
    c.drawString(COL["e60"] - 40, y, "Extras 60%")
    c.drawString(COL["e60"] + 15, y, hm(tot["e60"], 3))
    c.drawString(COL["e100"] - 40, y, "Extras 100%")
    c.drawString(COL["e100"] + 20, y, hm(tot["e100"], 3))
    y -= 12
    c.drawString(ML, y, "Atrasos")
    c.drawString(COL["trab"] + 45, y, hm(tot["atr"], 3))
    c.drawString(COL["e70"] - 40, y, "Extras 70%")
    c.drawString(COL["e70"] + 15, y, hm(tot["e70"], 3))
    c.drawString(COL["e110"] - 40, y, "Extras 110%")
    c.drawString(COL["e110"] + 25, y, hm(tot["e110"], 3))

    y -= 24
    c.setFont("Helvetica", 7.5)
    c.drawString(ML, y, "Estou de pleno acordo com o que demonstram as marcações acima, sendo que representam o ocorrido neste período.")


def main():
    fonte = json.loads(FONTE_JSON.read_text(encoding="utf-8"))
    meta = fonte["meta"]
    c = canvas.Canvas(str(DESTINO_PDF), pagesize=landscape(A4))
    for i, emp in enumerate(fonte["emp"], start=1):
        desenhar_pagina(c, meta, emp, pagina=i)
        c.showPage()
    c.save()
    print("gerado:", DESTINO_PDF)


if __name__ == "__main__":
    main()
