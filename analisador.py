#!/usr/bin/env python3
"""
Agente Analisador de Currículos
Analisa currículos em PDF, extrai informações e ranqueia candidatos
"""

import os
import re
import json
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import PyPDF2


@dataclass
class Candidato:
    """Representa um candidato com suas informações extraídas"""
    nome: str
    arquivo: str
    habilidades_tecnicas: List[str]
    anos_experiencia: float
    formacao: str
    idiomas: List[str]
    certificacoes: List[str]
    pontuacao_total: float
    detalhes: Dict[str, Any]


class AnalisadorCurriculos:
    """Classe principal para análise de currículos"""
    
    def __init__(self):
        # Critérios de avaliação técnica
        self.habilidades_valorizadas = {
            # Linguagens de Programação
            'python': 10, 'java': 10, 'javascript': 9, 'typescript': 9,
            'c++': 8, 'c#': 8, 'go': 8, 'rust': 8, 'kotlin': 7,
            'swift': 7, 'php': 6, 'ruby': 6, 'scala': 7,
            
            # Frameworks e Bibliotecas
            'react': 9, 'angular': 8, 'vue': 8, 'node.js': 9, 'nodejs': 9,
            'django': 8, 'flask': 7, 'spring': 8, 'fastapi': 7,
            '.net': 8, 'express': 7, 'next.js': 8, 'nextjs': 8,
            
            # DevOps e Cloud
            'docker': 9, 'kubernetes': 10, 'aws': 10, 'azure': 9,
            'gcp': 9, 'terraform': 8, 'jenkins': 7, 'gitlab ci': 7,
            'github actions': 7, 'ansible': 7, 'ci/cd': 8,
            
            # Banco de Dados
            'postgresql': 8, 'mysql': 7, 'mongodb': 8, 'redis': 7,
            'elasticsearch': 7, 'sql': 7, 'nosql': 7, 'oracle': 7,
            
            # Machine Learning e Data Science
            'machine learning': 10, 'deep learning': 10, 'tensorflow': 9,
            'pytorch': 9, 'scikit-learn': 8, 'pandas': 7, 'numpy': 7,
            'data science': 9, 'ai': 9, 'nlp': 9,
            
            # Metodologias e Práticas
            'agile': 6, 'scrum': 6, 'tdd': 7, 'microservices': 8,
            'rest api': 7, 'graphql': 8, 'git': 6, 'linux': 6,
        }
        
        self.formacoes = {
            'doutorado': 20, 'phd': 20, 'mestrado': 15, 'mba': 12,
            'pós-graduação': 10, 'especialização': 10,
            'bacharelado': 8, 'graduação': 8, 'superior': 8,
            'tecnólogo': 6, 'técnico': 4
        }
        
        self.idiomas_valorizados = {
            'inglês': 10, 'espanhol': 5, 'francês': 4,
            'alemão': 4, 'mandarim': 6, 'japonês': 5
        }
        
    def extrair_texto_pdf(self, caminho_pdf: str) -> str:
        """Extrai texto de um arquivo PDF"""
        try:
            texto = ""
            with open(caminho_pdf, 'rb') as arquivo:
                leitor = PyPDF2.PdfReader(arquivo)
                for pagina in leitor.pages:
                    texto += pagina.extract_text() + "\n"
            return texto
        except Exception as e:
            print(f"Erro ao extrair texto de {caminho_pdf}: {e}")
            return ""
    
    def extrair_nome(self, texto: str, nome_arquivo: str) -> str:
        """Tenta extrair o nome do candidato"""
        # Primeira linha geralmente contém o nome
        linhas = [l.strip() for l in texto.split('\n') if l.strip()]
        if linhas:
            # Pega a primeira linha não vazia
            primeira_linha = linhas[0]
            # Se parece com um nome (2-5 palavras, sem números)
            if 2 <= len(primeira_linha.split()) <= 5 and not re.search(r'\d', primeira_linha):
                return primeira_linha
        
        # Fallback: usa o nome do arquivo
        return Path(nome_arquivo).stem.replace('_', ' ').title()
    
    def extrair_habilidades(self, texto: str) -> List[str]:
        """Extrai habilidades técnicas do currículo"""
        texto_lower = texto.lower()
        habilidades_encontradas = []
        
        for habilidade in self.habilidades_valorizadas.keys():
            # Busca por palavra completa
            padrao = r'\b' + re.escape(habilidade) + r'\b'
            if re.search(padrao, texto_lower):
                habilidades_encontradas.append(habilidade)
        
        return habilidades_encontradas
    
    def extrair_anos_experiencia(self, texto: str) -> float:
        """Estima anos de experiência profissional"""
        # Procura por padrões de anos
        anos = []
        
        # Padrão: "X anos de experiência"
        match = re.findall(r'(\d+)\s*(?:\+)?\s*anos?\s+de\s+experiência', texto.lower())
        if match:
            anos.extend([int(x) for x in match])
        
        # Padrão: datas (2020 - 2023, etc)
        datas = re.findall(r'(20\d{2})\s*[-–]\s*(20\d{2}|atual|presente)', texto.lower())
        if datas:
            for inicio, fim in datas:
                fim_ano = 2025 if fim in ['atual', 'presente'] else int(fim)
                anos.append(fim_ano - int(inicio))
        
        # Retorna a soma ou estimativa
        return sum(anos) if anos else max(anos) if anos else 0
    
    def extrair_formacao(self, texto: str) -> str:
        """Identifica o nível de formação acadêmica"""
        texto_lower = texto.lower()
        
        for formacao, _ in sorted(self.formacoes.items(), key=lambda x: x[1], reverse=True):
            if formacao in texto_lower:
                return formacao.title()
        
        return "Não identificada"
    
    def extrair_idiomas(self, texto: str) -> List[str]:
        """Extrai idiomas mencionados no currículo"""
        texto_lower = texto.lower()
        idiomas_encontrados = []
        
        for idioma in self.idiomas_valorizados.keys():
            if idioma in texto_lower:
                idiomas_encontrados.append(idioma.title())
        
        return idiomas_encontrados
    
    def extrair_certificacoes(self, texto: str) -> List[str]:
        """Extrai certificações mencionadas"""
        certificacoes_comuns = [
            'aws certified', 'azure certified', 'gcp certified',
            'pmp', 'scrum master', 'cissp', 'ceh', 'comptia',
            'oracle certified', 'microsoft certified', 'google certified'
        ]
        
        texto_lower = texto.lower()
        certificacoes_encontradas = []
        
        for cert in certificacoes_comuns:
            if cert in texto_lower:
                certificacoes_encontradas.append(cert.upper())
        
        return certificacoes_encontradas
    
    def calcular_pontuacao(self, candidato: Dict[str, Any]) -> float:
        """Calcula a pontuação total do candidato"""
        pontuacao = 0.0
        detalhes = {}
        
        # Pontos por habilidades técnicas
        pontos_habilidades = sum([
            self.habilidades_valorizadas.get(h, 0) 
            for h in candidato['habilidades_tecnicas']
        ])
        pontuacao += pontos_habilidades
        detalhes['pontos_habilidades'] = pontos_habilidades
        
        # Pontos por experiência (2 pontos por ano, máximo 30 pontos)
        pontos_experiencia = min(candidato['anos_experiencia'] * 2, 30)
        pontuacao += pontos_experiencia
        detalhes['pontos_experiencia'] = pontos_experiencia
        
        # Pontos por formação
        formacao_lower = candidato['formacao'].lower()
        pontos_formacao = self.formacoes.get(formacao_lower, 0)
        pontuacao += pontos_formacao
        detalhes['pontos_formacao'] = pontos_formacao
        
        # Pontos por idiomas
        pontos_idiomas = sum([
            self.idiomas_valorizados.get(i.lower(), 0) 
            for i in candidato['idiomas']
        ])
        pontuacao += pontos_idiomas
        detalhes['pontos_idiomas'] = pontos_idiomas
        
        # Pontos por certificações (5 pontos cada)
        pontos_certificacoes = len(candidato['certificacoes']) * 5
        pontuacao += pontos_certificacoes
        detalhes['pontos_certificacoes'] = pontos_certificacoes
        
        return pontuacao, detalhes
    
    def analisar_curriculo(self, caminho_pdf: str) -> Candidato:
        """Analisa um único currículo e retorna um objeto Candidato"""
        texto = self.extrair_texto_pdf(caminho_pdf)
        
        if not texto:
            return None
        
        # Extrai informações
        dados = {
            'nome': self.extrair_nome(texto, caminho_pdf),
            'arquivo': os.path.basename(caminho_pdf),
            'habilidades_tecnicas': self.extrair_habilidades(texto),
            'anos_experiencia': self.extrair_anos_experiencia(texto),
            'formacao': self.extrair_formacao(texto),
            'idiomas': self.extrair_idiomas(texto),
            'certificacoes': self.extrair_certificacoes(texto),
        }
        
        # Calcula pontuação
        pontuacao, detalhes = self.calcular_pontuacao(dados)
        dados['pontuacao_total'] = pontuacao
        dados['detalhes'] = detalhes
        
        return Candidato(**dados)
    
    def analisar_pasta(self, caminho_pasta: str) -> List[Candidato]:
        """Analisa todos os currículos em PDF de uma pasta"""
        candidatos = []
        
        pasta = Path(caminho_pasta)
        arquivos_pdf = list(pasta.glob('*.pdf'))
        
        print(f"\n🔍 Analisando {len(arquivos_pdf)} currículos...\n")
        
        for arquivo_pdf in arquivos_pdf:
            print(f"   Processando: {arquivo_pdf.name}")
            candidato = self.analisar_curriculo(str(arquivo_pdf))
            if candidato:
                candidatos.append(candidato)
        
        # Ordena por pontuação (maior para menor)
        candidatos.sort(key=lambda x: x.pontuacao_total, reverse=True)
        
        return candidatos
    
    def gerar_relatorio(self, candidatos: List[Candidato], caminho_saida: str = None):
        """Gera relatório de análise em formato Markdown"""
        if not candidatos:
            print("❌ Nenhum candidato para analisar!")
            return
        
        # Prepara o relatório
        relatorio = "# Relatório de Análise de Currículos\n\n"
        relatorio += f"**Total de candidatos analisados:** {len(candidatos)}\n\n"
        relatorio += "---\n\n"
        
        # Top 3 Candidatos
        relatorio += "## 🏆 Top 3 Candidatos\n\n"
        
        top3 = candidatos[:3]
        
        for i, candidato in enumerate(top3, 1):
            relatorio += f"### {i}º Lugar - {candidato.nome}\n\n"
            relatorio += f"**Pontuação Total:** {candidato.pontuacao_total:.1f} pontos\n\n"
            relatorio += f"**Arquivo:** `{candidato.arquivo}`\n\n"
            
            # Resumo
            relatorio += "#### Resumo do Perfil\n\n"
            relatorio += f"- **Experiência:** {candidato.anos_experiencia:.1f} anos\n"
            relatorio += f"- **Formação:** {candidato.formacao}\n"
            relatorio += f"- **Idiomas:** {', '.join(candidato.idiomas) if candidato.idiomas else 'Não identificados'}\n"
            relatorio += f"- **Certificações:** {len(candidato.certificacoes)}\n\n"
            
            # Habilidades Técnicas
            relatorio += "#### Habilidades Técnicas\n\n"
            if candidato.habilidades_tecnicas:
                relatorio += ", ".join([f"`{h}`" for h in candidato.habilidades_tecnicas[:15]])
                if len(candidato.habilidades_tecnicas) > 15:
                    relatorio += f" e mais {len(candidato.habilidades_tecnicas) - 15}..."
                relatorio += "\n\n"
            else:
                relatorio += "Nenhuma habilidade técnica identificada.\n\n"
            
            # Detalhamento da Pontuação
            relatorio += "#### Detalhamento da Pontuação\n\n"
            relatorio += "| Categoria | Pontos |\n"
            relatorio += "|:----------|-------:|\n"
            relatorio += f"| Habilidades Técnicas | {candidato.detalhes['pontos_habilidades']:.1f} |\n"
            relatorio += f"| Experiência Profissional | {candidato.detalhes['pontos_experiencia']:.1f} |\n"
            relatorio += f"| Formação Acadêmica | {candidato.detalhes['pontos_formacao']:.1f} |\n"
            relatorio += f"| Idiomas | {candidato.detalhes['pontos_idiomas']:.1f} |\n"
            relatorio += f"| Certificações | {candidato.detalhes['pontos_certificacoes']:.1f} |\n"
            relatorio += f"| **Total** | **{candidato.pontuacao_total:.1f}** |\n\n"
            
            if candidato.certificacoes:
                relatorio += "#### Certificações\n\n"
                for cert in candidato.certificacoes:
                    relatorio += f"- {cert}\n"
                relatorio += "\n"
            
            relatorio += "---\n\n"
        
        # Ranking Completo
        relatorio += "## 📊 Ranking Completo\n\n"
        relatorio += "| Posição | Nome | Pontuação | Experiência | Formação | Habilidades |\n"
        relatorio += "|:-------:|:-----|----------:|:-----------:|:---------|:-----------:|\n"
        
        for i, candidato in enumerate(candidatos, 1):
            relatorio += f"| {i}º | {candidato.nome} | {candidato.pontuacao_total:.1f} | "
            relatorio += f"{candidato.anos_experiencia:.1f} anos | {candidato.formacao} | "
            relatorio += f"{len(candidato.habilidades_tecnicas)} |\n"
        
        relatorio += "\n---\n\n"
        relatorio += "*Relatório gerado automaticamente pelo Agente Analisador de Currículos*\n"
        
        # Salva o relatório
        if caminho_saida:
            with open(caminho_saida, 'w', encoding='utf-8') as f:
                f.write(relatorio)
            print(f"\n✅ Relatório salvo em: {caminho_saida}")
        
        return relatorio
    
    def exportar_json(self, candidatos: List[Candidato], caminho_saida: str):
        """Exporta os resultados em formato JSON"""
        dados = [asdict(c) for c in candidatos]
        
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Dados exportados em JSON: {caminho_saida}")


def main():
    """Função principal"""
    print("=" * 60)
    print("   AGENTE ANALISADOR DE CURRÍCULOS")
    print("=" * 60)
    
    # Cria o analisador
    analisador = AnalisadorCurriculos()
    
    # Define pasta de currículos
    pasta_curriculos = "/home/ubuntu/analisador_curriculos/curriculos"
    
    # Verifica se a pasta existe
    if not os.path.exists(pasta_curriculos):
        os.makedirs(pasta_curriculos)
        print(f"\n📁 Pasta criada: {pasta_curriculos}")
        print("   Por favor, adicione os currículos em PDF nesta pasta e execute novamente.")
        return
    
    # Analisa os currículos
    candidatos = analisador.analisar_pasta(pasta_curriculos)
    
    if not candidatos:
        print("\n❌ Nenhum currículo encontrado na pasta!")
        print(f"   Adicione arquivos PDF em: {pasta_curriculos}")
        return
    
    # Gera relatório
    print("\n" + "=" * 60)
    print("   GERANDO RELATÓRIO")
    print("=" * 60)
    
    relatorio_md = "/home/ubuntu/analisador_curriculos/relatorio_analise.md"
    analisador.gerar_relatorio(candidatos, relatorio_md)
    
    # Exporta JSON
    json_saida = "/home/ubuntu/analisador_curriculos/resultados.json"
    analisador.exportar_json(candidatos, json_saida)
    
    print("\n" + "=" * 60)
    print("   ANÁLISE CONCLUÍDA!")
    print("=" * 60)
    print(f"\n📄 Relatório: {relatorio_md}")
    print(f"📊 Dados JSON: {json_saida}")
    print(f"\n🏆 Top 3 Candidatos:")
    for i, candidato in enumerate(candidatos[:3], 1):
        print(f"   {i}º - {candidato.nome} ({candidato.pontuacao_total:.1f} pontos)")
    print()


if __name__ == "__main__":
    main()
