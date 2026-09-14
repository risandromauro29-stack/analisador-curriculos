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
| Modelos e conversão para o painel (`modelos.py`) | ✅ Testado (round-trip) |
| Gerador do painel HTML (`relatorio.py`) | ✅ Testado — reaproveita o template completo (mesmo CSS/JS/gráficos) |
| Resumo textual/JSON da auditoria (`relatorio.py`) | ✅ Testado |
| Cadastro de efetivo — encarregado/setor/função (`efetivo.py`) | ✅ Implementado (xlsx) |
| **Extração do PDF do espelho de ponto (`parser_pdf.py`)** | ⚠️ **v0, não calibrado** — precisa de um PDF real de amostra (ver abaixo) |

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

## Por que o parser de PDF ainda não está pronto

O espelho de ponto do Senior Sistemas varia de layout conforme a
configuração de cada empresa (colunas, códigos de horário, formatação da
tabela). O motor de regras foi validado com precisão contra dados **já
extraídos** — o que falta é calibrar a extração do texto bruto do PDF para
esse formato específico. Isso exige um PDF real (ou fictício, mas com a
mesma estrutura de colunas) para ajustar as expressões regulares em
`parser_pdf.py` (rode com `--debug` para inspecionar o texto extraído
página a página).

Até lá, o pipeline completo (regras → painel → resumo) pode ser usado com
`--json`, no mesmo formato de `tests/fixtures/espelho_amostra.json`.

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
