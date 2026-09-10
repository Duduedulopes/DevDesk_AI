"""Análise de código inteligente para detecção de problemas e sugestões de melhoria.

Este módulo implementa análise estática de código, detecção de code smells,
análise de complexidade ciclomática, verificação de boas práticas e sugestões
de refatoração automática.
"""
import re
import ast
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class NivelGravidade(Enum):
    """Níveis de gravidade dos problemas encontrados."""
    CRITICO = "CRÍTICO"
    ALTO = "ALTO"
    MEDIO = "MÉDIO"
    BAIXO = "BAIXO"
    INFO = "INFORMAÇÃO"


@dataclass
class ProblemaCodigo:
    """Representa um problema encontrado no código."""
    tipo: str
    descricao: str
    linha: int
    coluna: int
    gravidade: NivelGravidade
    sugestao: str
    codigo_afetado: str


class AnalisadorCodigo:
    """Analisador de código estática."""

    def __init__(self):
        self.problemas: List[ProblemaCodigo] = []

    def analisar(self, codigo: str, linguagem: str = "python") -> List[ProblemaCodigo]:
        """Analisa o código e retorna problemas encontrados."""
        self.problemas = []

        if linguagem.lower() == "python":
            self._analisar_python(codigo)
        elif linguagem.lower() in ["c#", "csharp"]:
            self._analisar_csharp(codigo)
        elif linguagem.lower() in ["js", "javascript"]:
            self._analisar_javascript(codigo)
        else:
            self.problemas.append(ProblemaCodigo(
                tipo="linguagem_nao_suportada",
                descricao=f"Linguagem {linguagem} não suportada para análise",
                linha=0,
                coluna=0,
                gravidade=NivelGravidade.INFO,
                sugestao="Use Python, C# ou JavaScript para análise completa",
                codigo_afetado=""
            ))

        return sorted(self.problemas, key=lambda p: (p.gravidade.value, p.linha))

    def _analisar_python(self, codigo: str):
        """Analisa código Python."""
        try:
            tree = ast.parse(codigo)
            self._detectar_code_smells_python(tree, codigo)
            self._calcular_complexidade_python(tree, codigo)
            self._verificar_solid_python(tree, codigo)
            self._analisar_performance_python(tree, codigo)
        except SyntaxError as e:
            self.problemas.append(ProblemaCodigo(
                tipo="erro_sintaxe",
                descricao=f"Erro de sintaxe: {e.msg}",
                linha=e.lineno or 0,
                coluna=e.offset or 0,
                gravidade=NivelGravidade.CRITICO,
                sugestao="Corrija o erro de sintaxe antes de continuar",
                codigo_afetado=""
            ))

    def _analisar_csharp(self, codigo: str):
        """Analisa código C#."""
        linhas = codigo.split('\n')
        self._detectar_code_smells_csharp(linhas, codigo)
        self._verificar_solid_csharp(linhas, codigo)
        self._analisar_performance_csharp(linhas, codigo)

    def _analisar_javascript(self, codigo: str):
        """Analisa código JavaScript."""
        linhas = codigo.split('\n')
        self._detectar_code_smells_javascript(linhas, codigo)
        self._verificar_solid_javascript(linhas, codigo)
        self._analisar_performance_javascript(linhas, codigo)

    def _detectar_code_smells_python(self, tree: ast.AST, codigo: str):
        """Detecta code smells em Python."""
        linhas = codigo.split('\n')

        # Funções muito longas
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                inicio = node.lineno
                fim = node.end_lineno if hasattr(node, 'end_lineno') else inicio
                tamanho = fim - inicio + 1

                if tamanho > 50:
                    self.problemas.append(ProblemaCodigo(
                        tipo="funcao_longa",
                        descricao=f"Função '{node.name}' muito longa ({tamanho} linhas)",
                        linha=inicio,
                        coluna=node.col_offset,
                        gravidade=NivelGravidade.ALTO,
                        sugestao="Divida a função em menores, seguindo o princípio Single Responsibility",
                        codigo_afetado=linhas[inicio-1] if inicio <= len(linhas) else ""
                    ))

        # Classes com muitos métodos
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                metodos = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(metodos) > 15:
                    self.problemas.append(ProblemaCodigo(
                        tipo="classe_grande",
                        descricao=f"Classe '{node.name}' com muitos métodos ({len(metodos)})",
                        linha=node.lineno,
                        coluna=node.col_offset,
                        gravidade=NivelGravidade.MEDIO,
                        sugestao="Considere dividir a classe em várias classes menores",
                        codigo_afetado=linhas[node.lineno-1] if node.lineno <= len(linhas) else ""
                    ))

        # Parâmetros demais (Complexidade Essencial)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if len(node.args.args) > 5:
                    self.problemas.append(ProblemaCodigo(
                        tipo="muitos_parametros",
                        descricao=f"Função '{node.name}' com muitos parâmetros ({len(node.args.args)})",
                        linha=node.lineno,
                        coluna=node.col_offset,
                        gravidade=NivelGravidade.MEDIO,
                        sugestao="Considere usar um objeto de parâmetros ou classe de configuração",
                        codigo_afetado=linhas[node.lineno-1] if node.lineno <= len(linhas) else ""
                    ))

        # Código duplicado (simplificado)
        self._detectar_duplicacao_codigo(codigo, linhas)

    def _detectar_duplicacao_codigo(self, codigo: str, linhas: List[str]):
        """Detecta código duplicado."""
        # Remove espaços em branco extras para comparação
        linhas_normalizadas = [linha.strip() for linha in linhas if linha.strip()]

        # Busca linhas duplicadas
        vistos = {}
        for i, linha in enumerate(linhas_normalizadas):
            if len(linha) > 20:  # Ignora linhas muito curtas
                if linha in vistos:
                    self.problemas.append(ProblemaCodigo(
                        tipo="codigo_duplicado",
                        descricao=f"Linha duplicada encontrada (também na linha {vistos[linha] + 1})",
                        linha=i + 1,
                        coluna=0,
                        gravidade=NivelGravidade.BAIXO,
                        sugestao="Extraia o código duplicado para uma função ou método",
                        codigo_afetado=linha
                    ))
                else:
                    vistos[linha] = i

    def _calcular_complexidade_python(self, tree: ast.AST, codigo: str):
        """Calcula complexidade ciclomática em Python."""
        linhas = codigo.split('\n')

        class ComplexityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.complexity = 1
                self.function_complexities = {}

            def visit_FunctionDef(self, node):
                old_complexity = self.complexity
                self.complexity = 1
                self.generic_visit(node)
                self.function_complexities[node.name] = self.complexity
                self.complexity = old_complexity

            def visit_If(self, node):
                self.complexity += 1
                self.generic_visit(node)

            def visit_While(self, node):
                self.complexity += 1
                self.generic_visit(node)

            def visit_For(self, node):
                self.complexity += 1
                self.generic_visit(node)

            def visit_ExceptHandler(self, node):
                self.complexity += 1
                self.generic_visit(node)

            def visit_With(self, node):
                self.complexity += 1
                self.generic_visit(node)

        visitor = ComplexityVisitor()
        visitor.visit(tree)

        for func_name, complexity in visitor.function_complexities.items():
            if complexity > 10:
                gravidade = NivelGravidade.CRITICO if complexity > 20 else NivelGravidade.ALTO
                self.problemas.append(ProblemaCodigo(
                    tipo="complexidade_alta",
                    descricao=f"Função '{func_name}' com complexidade ciclomática alta ({complexity})",
                    linha=0,  # Não temos a linha exata aqui
                    coluna=0,
                    gravidade=gravidade,
                    sugestao="Refatore a função para reduzir complexidade. Extraia métodos menores.",
                    codigo_afetado=""
                ))

    def _verificar_solid_python(self, tree: ast.AST, codigo: str):
        """Verifica princípios SOLID em Python."""
        linhas = codigo.split('\n')

        # Single Responsibility - classes com muitas responsabilidades
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                responsabilidades = set()
                for metodo in node.body:
                    if isinstance(metodo, ast.FunctionDef):
                        # Detecta diferentes tipos de operações
                        if 'save' in metodo.name.lower() or 'persist' in metodo.name.lower():
                            responsabilidades.add('persistencia')
                        if 'send' in metodo.name.lower() or 'notify' in metodo.name.lower():
                            responsabilidades.add('notificacao')
                        if 'validate' in metodo.name.lower() or 'check' in metodo.name.lower():
                            responsabilidades.add('validacao')

                if len(responsabilidades) > 2:
                    self.problemas.append(ProblemaCodigo(
                        tipo="violacao_srp",
                        descricao=f"Classe '{node.name}' viola Single Responsibility (múltiplas responsabilidades: {', '.join(responsabilidades)})",
                        linha=node.lineno,
                        coluna=node.col_offset,
                        gravidade=NivelGravidade.MEDIO,
                        sugestao="Divida a classe em classes com responsabilidades únicas",
                        codigo_afetado=linhas[node.lineno-1] if node.lineno <= len(linhas) else ""
                    ))

        # Open/Closed - hardcoding
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Verifica se tem muitos elif/else (indica extensão por modificação)
                if_count = 1
                for child in ast.walk(node):
                    if isinstance(child, ast.If) and child != node:
                        if_count += 1

                if if_count > 3:
                    self.problemas.append(ProblemaCodigo(
                        tipo="violacao_ocp",
                        descricao="Estrutura condicional complexa sugere violação de Open/Closed",
                        linha=node.lineno,
                        coluna=node.col_offset,
                        gravidade=NivelGravidade.MEDIO,
                        sugestao="Use polimorfismo ou padrão Strategy em vez de muitos if/elif",
                        codigo_afetado=linhas[node.lineno-1] if node.lineno <= len(linhas) else ""
                    ))

    def _analisar_performance_python(self, tree: ast.AST, codigo: str):
        """Analisa problemas de performance em Python."""
        linhas = codigo.split('\n')

        # Loops aninhados profundos
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                profundidade = self._calcular_profundidade_loop(node, tree)
                if profundidade > 2:
                    self.problemas.append(ProblemaCodigo(
                        tipo="loops_aninhados",
                        descricao=f"Loops aninhados com profundidade {profundidade} podem causar performance O(n³)",
                        linha=node.lineno,
                        coluna=node.col_offset,
                        gravidade=NivelGravidade.ALTO,
                        sugestao="Considere usar comprehensions, map/filter ou algoritmos mais eficientes",
                        codigo_afetado=linhas[node.lineno-1] if node.lineno <= len(linhas) else ""
                    ))

        # Uso de += em strings (ineficiente)
        for i, linha in enumerate(linhas):
            if '+=' in linha and 'str' in linha.lower():
                self.problemas.append(ProblemaCodigo(
                    tipo="concatenacao_ineficiente",
                    descricao="Concatenação de strings com += é ineficiente",
                    linha=i + 1,
                    coluna=linha.find('+='),
                    gravidade=NivelGravidade.BAIXO,
                    sugestao="Use join() ou f-strings para melhor performance",
                    codigo_afetado=linha.strip()
                ))

    def _calcular_profundidade_loop(self, node: ast.For, tree: ast.AST) -> int:
        """Calcula profundidade de aninhamento de loops."""
        profundidade = 1
        for child in ast.walk(node):
            if isinstance(child, ast.For) and child != node:
                profundidade += 1
        return profundidade

    def _detectar_code_smells_csharp(self, linhas: List[str], codigo: str):
        """Detecta code smells em C#."""
        # TODO: Implementar análise específica para C#
        for i, linha in enumerate(linhas):
            # Detectar métodos longos
            if '{' in linha and '}' not in linha:
                # Início de bloco - poderia ser início de método longo
                pass

            # Detectar magic numbers
            numeros = re.findall(r'\b\d{2,}\b', linha)
            if numeros and not any(keyword in linha.lower() for keyword in ['const', 'var', 'return']):
                self.problemas.append(ProblemaCodigo(
                    tipo="magic_number",
                    descricao=f"Magic number encontrado: {numeros[0]}",
                    linha=i + 1,
                    coluna=linha.find(numeros[0]),
                    gravidade=NivelGravidade.BAIXO,
                    sugestao="Use constantes nomeadas em vez de números literais",
                    codigo_afetado=linha.strip()
                ))

    def _verificar_solid_csharp(self, linhas: List[str], codigo: str):
        """Verifica princípios SOLID em C#."""
        # TODO: Implementar verificação SOLID específica para C#
        pass

    def _analisar_performance_csharp(self, linhas: List[str], codigo: str):
        """Analisa performance em C#."""
        # TODO: Implementar análise de performance específica para C#
        for i, linha in enumerate(linhas):
            # Detectar string concatenation em loop
            if 'string' in linha.lower() and '+' in linha and 'for' in linhas[max(0, i-5):i].lower():
                self.problemas.append(ProblemaCodigo(
                    tipo="concatenacao_loop",
                    descricao="Concatenação de strings em loop detectada",
                    linha=i + 1,
                    coluna=linha.find('+'),
                    gravidade=NivelGravidade.ALTO,
                    sugestao="Use StringBuilder para concatenar strings em loops",
                    codigo_afetado=linha.strip()
                ))

    def _detectar_code_smells_javascript(self, linhas: List[str], codigo: str):
        """Detecta code smells em JavaScript."""
        for i, linha in enumerate(linhas):
            # Detectar var (deve usar const/let)
            if 'var ' in linha and 'var ' == linha.strip()[:4]:
                self.problemas.append(ProblemaCodigo(
                    tipo="uso_de_var",
                    descricao="Uso de 'var' desencorajado",
                    linha=i + 1,
                    coluna=linha.find('var'),
                    gravidade=NivelGravidade.BAIXO,
                    sugestao="Use 'const' ou 'let' em vez de 'var'",
                    codigo_afetado=linha.strip()
                ))

            # Detectar == (deve usar ===)
            if '==' in linha and '===' not in linha and '!=' not in linha:
                self.problemas.append(ProblemaCodigo(
                    tipo="comparacao_frouxa",
                    descricao="Comparação frouxa (==) detectada",
                    linha=i + 1,
                    coluna=linha.find('=='),
                    gravidade=NivelGravidade.BAIXO,
                    sugestao="Use comparação estrita (===) para evitar coerção de tipo",
                    codigo_afetado=linha.strip()
                ))

    def _verificar_solid_javascript(self, linhas: List[str], codigo: str):
        """Verifica princípios SOLID em JavaScript."""
        # TODO: Implementar verificação SOLID específica para JavaScript
        pass

    def _analisar_performance_javascript(self, linhas: List[str], codigo: str):
        """Analisa performance em JavaScript."""
        for i, linha in enumerate(linhas):
            # Detectar += em strings
            if '+=' in linha and '"' in linha or "'" in linha:
                self.problemas.append(ProblemaCodigo(
                    tipo="concatenacao_ineficiente",
                    descricao="Concatenação de strings com += detectada",
                    linha=i + 1,
                    coluna=linha.find('+='),
                    gravidade=NivelGravidade.BAIXO,
                    sugestao="Use template literals ou join() para melhor performance",
                    codigo_afetado=linha.strip()
                ))


class SugestorRefatoracao:
    """Sugestor automático de refatoração."""

    def __init__(self):
        self.regras_refatoracao = [
            self._extrair_metodo,
            self._extrair_constante,
            self._substituir_condicional_por_polimorfismo,
            self._introduzir_parametro_objeto,
        ]

    def sugerir_refatoracoes(self, problemas: List[ProblemaCodigo]) -> List[Dict[str, Any]]:
        """Gera sugestões de refatoração baseadas nos problemas."""
        sugestoes = []

        for problema in problemas:
            if problema.tipo == "funcao_longa":
                sugestoes.append({
                    "tipo": "Extrair Método",
                    "descricao": "Divida a função longa em métodos menores",
                    "antes": problema.codigo_afetado,
                    "depois": "// Função extraída com responsabilidade única",
                    "beneficio": "Melhora legibilidade e testabilidade"
                })

            elif problema.tipo == "codigo_duplicado":
                sugestoes.append({
                    "tipo": "Extrair Método",
                    "descricao": "Extraia código duplicado para um método reutilizável",
                    "antes": problema.codigo_afetado,
                    "depois": "def metodo_reutilizavel():\n    # Código extraído",
                    "beneficio": "Elimina duplicação e facilita manutenção"
                })

            elif problema.tipo == "muitos_parametros":
                sugestoes.append({
                    "tipo": "Introduzir Objeto Parâmetro",
                    "descricao": "Substitua parâmetros múltiplos por um objeto de configuração",
                    "antes": "def metodo(param1, param2, param3, param4, param5, param6):",
                    "depois": "class Config:\n    pass\n\ndef metodo(config: Config):",
                    "beneficio": "Melhora extensibilidade e legibilidade"
                })

            elif problema.tipo == "magic_number":
                sugestoes.append({
                    "tipo": "Extrair Constante",
                    "descricao": "Substitua número mágico por constante nomeada",
                    "antes": problema.codigo_afetado,
                    "depois": "const MAX_ITENS = 100;\n// Usar MAX_ITENS em vez de 100",
                    "beneficio": "Melhora legibilidade e facilita manutenção"
                })

            elif problema.tipo == "violacao_ocp":
                sugestoes.append({
                    "tipo": "Substituir Condicional por Polimorfismo",
                    "descricao": "Use polimorfismo em vez de condicionais complexas",
                    "antes": "if tipo == 'A': ... elif tipo == 'B': ...",
                    "depois": "interface IProcessador { processar() }\n// Implementações específicas",
                    "beneficio": "Facilita adicionar novos tipos sem modificar código existente"
                })

        return sugestoes


def analisar_codigo_completo(codigo: str, linguagem: str = "python") -> Dict[str, Any]:
    """Análise completa de código com todas as verificações."""
    analisador = AnalisadorCodigo()
    problemas = analisador.analisar(codigo, linguagem)

    sugestor = SugestorRefatoracao()
    refatoracoes = sugestor.sugerir_refatoracoes(problemas)

    # Contar problemas por gravidade
    por_gravidade = {}
    for problema in problemas:
        gravidade = problema.gravidade.value
        por_gravidade[gravidade] = por_gravidade.get(gravidade, 0) + 1

    # Calcular pontuação de qualidade
    pontuacao = _calcular_pontuacao_qualidade(problemas)

    return {
        "problemas": problemas,
        "refatoracoes": refatoracoes,
        "resumo_gravidade": por_gravidade,
        "pontuacao_qualidade": pontuacao,
        "total_problemas": len(problemas),
        "linguagem": linguagem
    }


def _calcular_pontuacao_qualidade(problemas: List[ProblemaCodigo]) -> int:
    """Calcula pontuação de qualidade (0-100)."""
    if not problemas:
        return 100

    penalidades = {
        NivelGravidade.CRITICO: 20,
        NivelGravidade.ALTO: 10,
        NivelGravidade.MEDIO: 5,
        NivelGravidade.BAIXO: 2,
        NivelGravidade.INFO: 0
    }

    total_penalidade = sum(penalidades[p.gravidade] for p in problemas)
    pontuacao = max(0, 100 - total_penalidade)

    return pontuacao