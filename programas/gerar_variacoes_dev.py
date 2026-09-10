"""Gera variações automáticas para as novas intenções de desenvolvimento."""
import json
import random

# Templates para cada intenção
templates = {
    "gerar_codigo": [
        "crie {requisito}",
        "faz {requisito}",
        "gere {requisito}",
        "escreva {requisito}",
        "me faça {requisito}",
        "preciso de {requisito}",
        "quero {requisito}",
        "desenvolva {requisito}",
        "implemente {requisito}",
        "codifique {requisito}",
        "criar {requisito}",
        "fazer {requisito}",
        "gerar {requisito}",
        "escrever {requisito}",
    ],
    "criar_projeto_completo": [
        "crie um projeto de {tipo}",
        "faz um projeto de {tipo}",
        "monte um projeto de {tipo}",
        "gere um projeto de {tipo}",
        "inicie um projeto de {tipo}",
        "criar projeto {tipo}",
        "fazer projeto {tipo}",
        "montar projeto {tipo}",
        "preciso de um projeto {tipo}",
        "quero um projeto {tipo}",
    ],
    "implementar_funcionalidade": [
        "implemente {funcionalidade}",
        "adicione {funcionalidade}",
        "crie {funcionalidade}",
        "desenvolva {funcionalidade}",
        "adicione funcionalidade de {funcionalidade}",
        "implementar {funcionalidade}",
        "adicionar {funcionalidade}",
        "criar {funcionalidade}",
    ],
    "escrever_classe": [
        "crie uma classe {nome}",
        "escreva uma classe {nome}",
        "faz uma classe {nome}",
        "gere uma classe {nome}",
        "desenvolva uma classe {nome}",
        "criar classe {nome}",
        "escrever classe {nome}",
        "fazer classe {nome}",
    ],
    "escrever_funcao": [
        "crie uma função {requisito}",
        "escreva uma função {requisito}",
        "faz uma função {requisito}",
        "gere uma função {requisito}",
        "desenvolva uma função {requisito}",
        "criar função {requisito}",
        "escrever função {requisito}",
        "fazer função {requisito}",
    ],
    "explicar_conceito": [
        "me explique {conceito}",
        "explique {conceito}",
        "o que é {conceito}",
        "me diz o que é {conceito}",
        "explicar {conceito}",
        "me fale sobre {conceito}",
        "o que significa {conceito}",
    ],
    "sugerir_arquitetura": [
        "que arquitetura usar para {contexto}",
        "sugira uma arquitetura para {contexto}",
        "que arquitetura para {contexto}",
        "sugere arquitetura {contexto}",
        "arquitetura recomendada para {contexto}",
        "melhor arquitetura para {contexto}",
    ],
}

# Variações para preencher os templates
requisitos_codigo = [
    "uma calculadora em C#",
    "um sistema de login",
    "um CRUD em Python",
    "uma API REST",
    "um endpoint para listar usuários",
    "um script para processar CSV",
    "um botão em HTML",
    "uma query SQL para buscar dados",
    "um sistema de autenticação",
    "um CRUD completo",
    "um parser de JSON",
    "um componente React",
    "um serviço de email",
    "um sistema de cache",
    "um interceptor HTTP",
    "um middleware de autenticação",
    "um DTO de resposta",
    "um sistema de logging",
]

tipos_projeto = [
    "site",
    "API",
    "dashboard",
    "e-commerce",
    "blog",
    "sistema",
    "mobile",
    "landing page",
    "CMS",
    "chat",
    "gerenciador",
    "aplicativo",
    "plataforma",
]

funcionalidades = [
    "autenticação JWT",
    "validação de formulário",
    "upload de arquivo",
    "paginação",
    "busca com filtros",
    "ordenação",
    "cache",
    "logging",
    "rate limiting",
    "internacionalização",
    "websockets",
    "notificações",
    "backup automático",
]

nomes_classes = [
    "Produto",
    "Order",
    "Customer",
    "DatabaseConnection",
    "UserRepository",
    "EmailService",
    "CacheManager",
    "Logger",
    "Validator",
    "AuthenticationMiddleware",
    "RequestHandler",
    "ResponseBuilder",
    "DataManager",
    "SecurityService",
]

requisitos_funcao = [
    "para formatar data",
    "para validar CPF",
    "para converter JSON",
    "para gerar hash",
    "de validação de email",
    "para formatar moeda",
    "para calcular idade",
    "de ordenação",
    "para gerar token",
    "para validar telefone",
    "para criptografar senha",
    "para normalizar texto",
]

conceitos = [
    "injeção de dependência",
    "SOLID principles",
    "REST API",
    "MVC",
    "design patterns",
    "async await",
    "herança",
    "polimorfismo",
    "encapsulamento",
    "abstração",
    "interface",
    "decorator pattern",
    "factory pattern",
    "singleton pattern",
]

contextos_arquitetura = [
    "microserviços",
    "app mobile",
    "sistema de pagamento",
    "e-commerce",
    "dashboard",
    "aplicação monolítica",
    "chat",
    "sistema realtime",
    "arquitetura serverless",
    "IoT",
    "API de alta escala",
    "sistema distribuído",
]

def gerar_variacoes(intencao, templates_list, valores, num_variacoes=50):
    """Gera variações para uma intenção."""
    variacoes = []
    for _ in range(num_variacoes):
        template = random.choice(templates_list)
        valor = random.choice(valores)
        # Mapeamento de placeholders para valores
        placeholders = {
            "{requisito}": valor,
            "{tipo}": valor,
            "{funcionalidade}": valor,
            "{nome}": valor,
            "{requisito}": valor,
            "{conceito}": valor,
            "{contexto}": valor,
        }
        pergunta = template
        for placeholder, replacement in placeholders.items():
            pergunta = pergunta.replace(placeholder, replacement)
        variacoes.append({
            "pergunta": pergunta,
            "intencao": intencao,
            "base": f"{intencao}:dev:gen",
            "registro": "dev"
        })
    return variacoes

def main():
    # Configurações
    random.seed(42)

    # Gerar variações para cada intenção
    todas_variacoes = []

    todas_variacoes.extend(gerar_variacoes(
        "gerar_codigo", templates["gerar_codigo"], requisitos_codigo, 100))

    todas_variacoes.extend(gerar_variacoes(
        "criar_projeto_completo", templates["criar_projeto_completo"], tipos_projeto, 80))

    todas_variacoes.extend(gerar_variacoes(
        "implementar_funcionalidade", templates["implementar_funcionalidade"], funcionalidades, 80))

    todas_variacoes.extend(gerar_variacoes(
        "escrever_classe", templates["escrever_classe"], nomes_classes, 80))

    todas_variacoes.extend(gerar_variacoes(
        "escrever_funcao", templates["escrever_funcao"], requisitos_funcao, 80))

    todas_variacoes.extend(gerar_variacoes(
        "explicar_conceito", templates["explicar_conceito"], conceitos, 80))

    todas_variacoes.extend(gerar_variacoes(
        "sugerir_arquitetura", templates["sugerir_arquitetura"], contextos_arquitetura, 80))

    # Adicionar ao arquivo existente
    with open("dados/perguntas_dev.jsonl", "a", encoding="utf-8") as f:
        for var in todas_variacoes:
            f.write(json.dumps(var, ensure_ascii=False) + "\n")

    print(f"Geradas {len(todas_variacoes)} variações para as novas intenções de desenvolvimento.")
    print("Adicionadas a dados/perguntas_dev.jsonl")

if __name__ == "__main__":
    main()