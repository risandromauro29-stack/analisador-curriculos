# Guia Rápido - Agente Analisador de Currículos

## 🚀 Como Usar

### Passo 1: Adicionar Currículos

Copie os currículos em PDF para a pasta `curriculos/`:

```bash
cp /caminho/do/curriculo.pdf /home/ubuntu/analisador_curriculos/curriculos/
```

### Passo 2: Executar a Análise

```bash
cd /home/ubuntu/analisador_curriculos
python3.11 analisador.py
```

### Passo 3: Visualizar os Resultados

Os resultados estarão disponíveis em:

- **📄 Relatório Completo:** `relatorio_analise.md`
- **📊 Dados JSON:** `resultados.json`

## 📁 Estrutura de Arquivos

```
analisador_curriculos/
├── analisador.py                    # Script principal
├── curriculos/                      # Pasta para currículos em PDF
│   ├── candidato1.pdf
│   ├── candidato2.pdf
│   └── ...
├── relatorio_analise.md            # Relatório gerado
├── resultados.json                 # Dados em JSON
├── README.md                       # Documentação completa
└── GUIA_RAPIDO.md                 # Este guia
```

## 🎯 O que o Sistema Avalia

| Critério | Peso Máximo | Descrição |
|:---------|:-----------:|:----------|
| **Habilidades Técnicas** | ~100 pontos | Linguagens, frameworks, ferramentas |
| **Experiência** | 30 pontos | 2 pontos por ano (máx. 15 anos) |
| **Formação** | 20 pontos | Doutorado > Mestrado > MBA > Graduação |
| **Idiomas** | ~30 pontos | Inglês, Espanhol, Francês, etc. |
| **Certificações** | 5 pontos cada | AWS, Azure, Google, Scrum, etc. |

## 💡 Dicas

1. **Formato dos Currículos:** Use PDFs com texto selecionável (não imagens escaneadas)
2. **Nomenclatura:** Nomeie os arquivos de forma descritiva (ex: `joao_silva_dev.pdf`)
3. **Quantidade:** Não há limite de currículos para análise
4. **Customização:** Edite `analisador.py` para ajustar os critérios de avaliação

## 📊 Exemplo de Resultado

```
🏆 Top 3 Candidatos:
   1º - Ana Paula Costa (295.0 pontos)
   2º - Carlos Eduardo Silva (262.0 pontos)
   3º - Rafael Souza Lima (186.0 pontos)
```

## ⚙️ Personalizar Critérios

Para customizar os critérios de avaliação, edite o arquivo `analisador.py`:

### Adicionar Nova Habilidade

```python
self.habilidades_valorizadas = {
    'python': 10,
    'java': 10,
    'sua_habilidade': 8,  # Adicione aqui
    # ...
}
```

### Ajustar Pontuação de Formação

```python
self.formacoes = {
    'doutorado': 20,
    'mestrado': 15,
    # Ajuste os valores conforme necessário
}
```

### Modificar Peso da Experiência

```python
# Linha ~145 - Altere o multiplicador (padrão: 2)
pontos_experiencia = min(candidato['anos_experiencia'] * 2, 30)
```

## 🔄 Executar Nova Análise

Para analisar novos currículos:

1. Adicione os novos PDFs na pasta `curriculos/`
2. Execute novamente: `python3.11 analisador.py`
3. Os resultados anteriores serão sobrescritos

## 📞 Suporte

Para dúvidas ou problemas, consulte o arquivo `README.md` para documentação completa.

---

**Desenvolvido por:** Manus AI
