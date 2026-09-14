# Ponto Auditor

Sistema de auditoria de espelhos de ponto frente à CLT: recebe o espelho de
ponto de uma obra/período e devolve um painel BI interativo (HTML, offline)
mais um resumo textual, apontando horas extras, adicional noturno, faltas e
**não conformidades legais** (jornada acima do limite, intervalo intrajornada
e interjornada insuficientes, marcações inválidas, trabalho em dia de
descanso).

## Status

| Peça | Status |
|---|---|
| Motor de regras CLT (`regras.py`) | ✅ Validado — recalculado sobre 11.130 dias/colaborador reais, bateu 100% com os alertas já publicados (ver `tests/test_regras.py`) |
| Cálculo de campos derivados — intervalo, interjornada, jornada apurada, saída prevista (`calculos.py`) | ✅ Validado contra o backend original, dia a dia (ver `tests/test_parser_pdf.py`) |
| Extração do PDF do Cartão Ponto / espelho (`parser_pdf.py`) | ✅ Calibrada contra um PDF real cedido pelo usuário (layout Senior Sistemas) e validada ponta a ponta com um PDF sintético de 6 colaboradores × 21 dias reais |
| Modelos e conversão para o painel (`modelos.py`) | ✅ Testado (round-trip) |
| Gerador do painel HTML (`relatorio.py`) | ✅ Testado — reaproveita o template completo (mesmo CSS/JS/gráficos) |
| Resumo textual/JSON da auditoria (`relatorio.py`) | ✅ Testado |
| Cadastro de efetivo — encarregado/setor/função (`efetivo.py`) | ✅ Implementado (xlsx) |

Todas as peças passam em `pytest` (10 testes) rodando com dados reais (anonimizados). O único ponto ainda não coberto por um teste automático é uma segunda exportação do Senior com layout diferente do observado — se aparecer um PDF que o parser rejeite, rode com `--debug` e ajuste `parser_pdf.py` (a lógica de bandas de coluna é dinâmica, então pequenas variações de margem já são toleradas; mudanças de rótulo de coluna ou de ordem não são).

## Uso

```bash
pip install -r requirements.txt

# via PDF do espelho de ponto (Senior Sistemas) + cadastro de efetivo
python -m ponto_auditor auditar espelho.pdf --efetivo EFETIVO.xlsx \
  --obra "EPR Duplicação BR-153 · Lote 02 · PR" \
  --empresa "TUCUMANN ENG EMPREEND LTDA" \
  --inicio 21/08/2026 --fim 10/09/2026 \
  -o saida/

# via dados já estruturados em JSON (bypassa o parser de PDF)
python -m ponto_auditor auditar --json dados.json -o saida/
```

Gera em `saida/`:
- `painel_ponto.html` — painel interativo (visão geral, conformidade, horas
  extras, interjornada, dia a dia, colaboradores, relatório A4 para
  impressão/PDF, metodologia)
- `resumo_auditoria.md` — leitura rápida dos KPIs sem abrir o painel
- `resumo_auditoria.json` — os mesmos indicadores, estruturados

## Como o parser foi calibrado e validado

O layout do "Cartão Ponto" (Senior Sistemas) foi obtido de um PDF real
cedido pelo usuário: uma página por colaborador, com cabeçalho
(empregador/CNPJ/empregado/cargo/escala) e uma tabela diária de
Data/Sem/Hor/Marcações + Trabalho/Faltas/Atrasos + Extras 50–110% +
Adicional Noturno, fechando com um bloco "Totais de Horas". A extração
usa a **posição horizontal** de cada palavra (via `pdfplumber`), com as
bandas de coluna detectadas dinamicamente a partir do próprio cabeçalho
da tabela — não fixadas em pontos — para tolerar pequenas variações de
margem entre exportações.

Os campos que o PDF não traz prontos (intervalo, interjornada, jornada
apurada, saída prevista, atraso de saída, regime 12x36) são derivados em
`calculos.py` com fórmulas decifradas comparando esse PDF real com os
valores já calculados para o mesmo colaborador/período no painel de
referência (ver os comentários de `calculos.py` e `parser_pdf.py`).

`tests/fixtures/gerar_pdf_amostra.py` gera um PDF sintético que reproduz
esse layout com dados de 6 colaboradores reais (nomes/matrículas
trocados por fictícios, valores de dias mantidos) — cobrindo as 6 regras
de conformidade, regime 12x36 com virada de meia-noite, marcações
ímpares/inválidas, DSR e feriado. `tests/test_parser_pdf.py` roda o PDF
pelo parser + `calculos.py` + `regras.py` e confere, dia a dia, os 126
registros contra o que o backend original já havia calculado — bateu
100%.

Se aparecer uma exportação do Senior com layout diferente (rótulos de
coluna diferentes, mais páginas por colaborador etc.), rode
`python -m ponto_auditor auditar arquivo.pdf --debug` para inspecionar o
texto extraído e ajustar `parser_pdf.py`.

Alternativamente, o pipeline completo (regras → painel → resumo) também
aceita dados já estruturados com `--json`, no formato de
`tests/fixtures/espelho_amostra.json`.

## Regras de conformidade aplicadas

| Regra | Base legal | Severidade |
|---|---|---|
| Horas extras acima de 2h/dia | CLT art. 59, §2º | crítica |
| Jornada apurada acima do limite (10h normal / 12h no 12x36) | CLT art. 58 e 59 | crítica |
| Intervalo intrajornada inferior a 1h | CLT art. 71, §4º | crítica |
| Interjornada inferior a 11h | CLT art. 66 | crítica |
| Marcações inválidas ou ímpares | Portaria MTP 671/2021 | atenção |
| Trabalho em dia de descanso (domingo/feriado, fora do 12x36) | CLT art. 67 · Lei 605/49 | atenção |

Este painel apoia a gestão da jornada e **não substitui a análise jurídica**
de cada caso.
