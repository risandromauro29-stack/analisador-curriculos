# Agente Analisador de Currículos

Sistema inteligente para análise automatizada de currículos em PDF com ranking técnico e destaque dos melhores candidatos.

## 📋 Funcionalidades

- ✅ **Importação de Currículos em PDF** - Processa múltiplos currículos automaticamente
- ✅ **Extração Inteligente de Informações** - Identifica habilidades, experiência, formação, idiomas e certificações
- ✅ **Sistema de Ranking Técnico** - Pontuação objetiva baseada em critérios customizáveis
- ✅ **Top 3 Candidatos** - Destaque automático dos três melhores perfis
- ✅ **Relatórios Detalhados** - Geração de relatórios em Markdown e exportação em JSON

## 🚀 Como Usar

### 1. Preparar os Currículos

Adicione os currículos em formato PDF na pasta `curriculos/`:

```bash
cp seu_curriculo.pdf /home/ubuntu/analisador_curriculos/curriculos/
```

### 2. Executar a Análise

```bash
cd /home/ubuntu/analisador_curriculos
python3.11 analisador.py
```

### 3. Visualizar os Resultados

Os resultados serão gerados em:
- **Relatório Markdown:** `relatorio_analise.md` - Relatório completo com top 3 e ranking
- **Dados JSON:** `resultados.json` - Dados estruturados para integração

## 🎯 Critérios de Avaliação

O sistema avalia os candidatos com base nos seguintes critérios:

### Habilidades Técnicas (até ~100 pontos)
- Linguagens de programação (Python, Java, JavaScript, etc.)
- Frameworks e bibliotecas (React, Django, Spring, etc.)
- DevOps e Cloud (Docker, Kubernetes, AWS, Azure, etc.)
- Banco de dados (PostgreSQL, MongoDB, Redis, etc.)
- Machine Learning e Data Science
- Metodologias e práticas (Agile, TDD, Microservices, etc.)

### Experiência Profissional (até 30 pontos)
- 2 pontos por ano de experiência (máximo 30 pontos)

### Formação Acadêmica (até 20 pontos)
- Doutorado/PhD: 20 pontos
- Mestrado: 15 pontos
- MBA: 12 pontos
- Pós-graduação/Especialização: 10 pontos
- Bacharelado/Graduação: 8 pontos
- Tecnólogo: 6 pontos
- Técnico: 4 pontos

### Idiomas (até ~30 pontos)
- Inglês: 10 pontos
- Mandarim: 6 pontos
- Espanhol: 5 pontos
- Outros idiomas: 4-5 pontos cada

### Certificações (5 pontos cada)
- AWS Certified, Azure Certified, GCP Certified
- PMP, Scrum Master, CISSP, CEH, CompTIA
- Oracle Certified, Microsoft Certified, Google Certified

## 🔧 Personalização

Para customizar os critérios de avaliação, edite o arquivo `analisador.py` e ajuste os dicionários:

- `self.habilidades_valorizadas` - Habilidades técnicas e suas pontuações
- `self.formacoes` - Níveis de formação e pontuações
- `self.idiomas_valorizados` - Idiomas e suas pontuações

## 📊 Exemplo de Saída

```
🏆 Top 3 Candidatos:
   1º - João Silva (87.5 pontos)
   2º - Maria Santos (76.0 pontos)
   3º - Pedro Oliveira (68.5 pontos)
```

## 📦 Dependências

- Python 3.11+
- PyPDF2 (para extração de texto de PDFs)

## 🛠️ Instalação de Dependências

```bash
pip3 install PyPDF2
```

## 📝 Notas

- O sistema utiliza processamento de linguagem natural baseado em padrões e regex
- A extração de informações pode variar dependendo do formato do currículo
- Recomenda-se revisar manualmente os top candidatos antes de decisões finais
- Os critérios podem ser ajustados conforme as necessidades específicas da vaga

---

## 🕒 Ponto Auditor (novo)

Este repositório também inclui o **`ponto_auditor/`**, um sistema separado de
auditoria de espelhos de ponto frente à CLT (horas extras, jornada máxima,
intervalos, marcações inválidas, trabalho em dia de descanso). Veja
[`ponto_auditor/README.md`](ponto_auditor/README.md) para uso e status.

---

**Desenvolvido por:** Manus AI  
**Versão:** 1.0.0
