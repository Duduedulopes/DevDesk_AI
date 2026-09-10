"""Sugestões de arquitetura para diferentes tipos de projetos.

Este módulo fornece recomendações de arquitetura baseadas no tipo
de projeto e escala esperada.
"""

ARQUITETURAS = {
    "api": {
        "nome": "API RESTful com Camadas",
        "descricao": "Arquitetura clássica em camadas para APIs REST",
        "camadas": [
            "Controller Layer - Recebe e valida requisições HTTP",
            "Service Layer - Contém regras de negócio",
            "Repository Layer - Acesso a dados",
            "Database - Persistência"
        ],
        "vantagens": [
            "Separação clara de responsabilidades",
            "Fácil de testar cada camada",
            "Escalável horizontalmente",
            "Padrão bem estabelecido"
        ],
        "tecnologias_sugeridas": {
            "csharp": ["ASP.NET Core Web API", "Entity Framework Core", "MediatR"],
            "python": ["FastAPI ou Flask", "SQLAlchemy", "Pydantic"],
            "javascript": ["Express.js", "Sequelize ou TypeORM", "Joi"]
        }
    },
    "microservicos": {
        "nome": "Microserviços com API Gateway",
        "descricao": "Arquitetura de microserviços para sistemas distribuídos",
        "componentes": [
            "API Gateway - Entry point único",
            "Microserviços - Serviços independentes",
            "Service Discovery - Descoberta de serviços",
            "Message Broker - Comunicação assíncrona",
            "Database per Service - Cada serviço tem seu DB"
        ],
        "vantagens": [
            "Escalabilidade independente",
            "Deploy independente",
            "Resiliência (falha isolada)",
            "Tecnologias heterogêneas"
        ],
        "desafios": [
            "Complexidade de distribuição",
            "Consistência de dados",
            "Networking e latência",
            "Debugging distribuído"
        ],
        "tecnologias_sugeridas": {
            "csharp": ["ASP.NET Core", "Docker", "Kubernetes", "RabbitMQ"],
            "python": ["FastAPI", "Docker", "Kubernetes", "Redis"],
            "javascript": ["Node.js", "Docker", "Kubernetes", "Kafka"]
        }
    },
    "ecommerce": {
        "nome": "E-commerce Modular",
        "descricao": "Arquitetura modular para e-commerce",
        "modulos": [
            "Catálogo e Produtos",
            "Carrinho de Compras",
            "Checkout e Pagamento",
            "Pedidos e Fulfillment",
            "Usuários e Autenticação",
            "Notificações"
        ],
        "padroes": [
            "CQRS para separar leitura/escrita",
            "Event Sourcing para auditoria",
            "Saga Pattern para transações distribuídas",
            "Cache para performance"
        ],
        "tecnologias_sugeridas": {
            "csharp": ["ASP.NET Core", "MassTransit", "Redis", "Elasticsearch"],
            "python": ["Django ou FastAPI", "Celery", "Redis", "PostgreSQL"],
            "javascript": ["Node.js", "BullMQ", "Redis", "MongoDB"]
        }
    },
    "mobile": {
        "nome": "Mobile App com Backend",
        "descricao": "Arquitetura para aplicativos mobile",
        "componentes": [
            "Mobile App (iOS/Android)",
            "API Backend",
            "Authentication Service",
            "Push Notification Service",
            "Analytics"
        ],
        "vantagens": [
            "Offline-first possível",
            "Sincronização inteligente",
            "UX nativa",
            "Acesso a hardware do dispositivo"
        ],
        "tecnologias_sugeridas": {
            "mobile": ["React Native ou Flutter", "Expo"],
            "backend": ["ASP.NET Core", "Node.js", "Firebase"],
            "auth": ["Auth0", "Firebase Auth", "JWT"]
        }
    },
    "dashboard": {
        "nome": "Dashboard com Real-time",
        "descricao": "Arquitetura para dashboards com dados em tempo real",
        "componentes": [
            "Frontend Dashboard",
            "API de Dados",
            "WebSocket Server",
            "Cache Layer",
            "Database de Time Series"
        ],
        "vantagens": [
            "Atualização em tempo real",
            "Alta performance",
            "Escalável",
            "User experience excelente"
        ],
        "tecnologias_sugeridas": {
            "frontend": ["React", "Vue.js", "D3.js ou Chart.js"],
            "backend": ["ASP.NET Core SignalR", "Node.js Socket.io"],
            "database": ["Redis", "InfluxDB", "PostgreSQL"]
        }
    },
    "realtime": {
        "nome": "Aplicação Real-time",
        "descricao": "Arquitetura para aplicações com comunicação em tempo real",
        "componentes": [
            "WebSocket Server",
            "Message Broker",
            "Presence Service",
            "Event Store",
            "Database"
        ],
        "casos_de_uso": [
            "Chat e mensageria",
            "Colaboração em tempo real",
            "Notificações live",
            "Gaming multiplayer"
        ],
        "tecnologias_sugeridas": {
            "csharp": ["ASP.NET Core SignalR", "Redis Pub/Sub"],
            "python": ["FastAPI WebSockets", "Redis Pub/Sub"],
            "javascript": ["Socket.io", "Redis Pub/Sub", "Pusher"]
        }
    },
    "serverless": {
        "nome": "Serverless Functions",
        "descricao": "Arquitetura serverless com funções como serviço",
        "componentes": [
            "Function as a Service (FaaS)",
            "Managed Database",
            "Storage Service",
            "API Gateway",
            "CDN"
        ],
        "vantagens": [
            "Pay-per-use",
            "Auto-scaling",
            "Sem gerenciamento de infraestrutura",
            "Deploy rápido"
        ],
        "desafios": [
            "Cold starts",
            "Vendor lock-in",
            "Debugging complexo",
            "Limitações de execução"
        ],
        "tecnologias_sugeridas": {
            "csharp": ["Azure Functions", "AWS Lambda"],
            "python": ["AWS Lambda", "Google Cloud Functions"],
            "javascript": ["AWS Lambda", "Vercel Functions", "Netlify Functions"]
        }
    },
    "iot": {
        "nome": "IoT Platform",
        "descricao": "Arquitetura para Internet das Coisas",
        "componentes": [
            "IoT Hub/Gateway",
            "Message Broker",
            "Stream Processing",
            "Time Series Database",
            "Analytics Engine",
            "Dashboard"
        ],
        "vantagens": [
            "Processamento em escala",
            "Armazenamento eficiente",
            "Análise em tempo real",
            "Integração com dispositivos"
        ],
        "tecnologias_sugeridas": {
            "csharp": ["Azure IoT Hub", "Azure Stream Analytics"],
            "python": ["AWS IoT Core", "Apache Kafka", "InfluxDB"],
            "javascript": ["AWS IoT", "Mosquitto MQTT", "MongoDB"]
        }
    }
}

CONCEITOS_EXPLICACOES = {
    "injecao_dependencia": """**Injeção de Dependência (Dependency Injection)**

É um padrão de design onde as dependências de uma classe são fornecidas
externamente em vez de criadas internamente.

**Benefícios:**
- Reduz acoplamento entre classes
- Facilita testes (mock de dependências)
- Melhora manutenibilidade
- Segue o princípio DIP (Dependency Inversion Principle)

**Exemplo em C#:**
```csharp
// Sem DI
public class UserService {
    private Database db = new Database(); // acoplamento forte
}

// Com DI
public class UserService {
    private readonly Database _db;
    public UserService(Database db) {  // dependência injetada
        _db = db;
    }
}
```""",

    "solid": """**Princípios SOLID**

São cinco princípios de design orientado a objetos:

**S** - Single Responsibility Principle (SRP)
Uma classe deve ter apenas uma razão para mudar.

**O** - Open/Closed Principle (OCP)
Classes devem estar abertas para extensão, fechadas para modificação.

**L** - Liskov Substitution Principle (LSP)
Subclasses devem ser substituíveis por suas classes base.

**I** - Interface Segregation Principle (ISP)
Interfaces específicas são melhores que interfaces genéricas.

**D** - Dependency Inversion Principle (DIP)
Dependa de abstrações, não de implementações concretas.""",

    "rest_api": """**REST API (Representational State Transfer)**

É um estilo de arquitetura para APIs web que usa métodos HTTP padrão.

**Principais conceitos:**
- **Recursos**: Entidades representadas por URLs
- **Métodos HTTP**: GET (ler), POST (criar), PUT/PATCH (atualizar), DELETE (remover)
- **Stateless**: Cada requisição contém todas as informações necessárias
- **Cacheable**: Respostas podem ser cacheadas
- **Uniform Interface**: Interface consistente entre recursos

**Exemplo de endpoints:**
```
GET    /api/produtos        - Listar produtos
GET    /api/produtos/123    - Obter produto específico
POST   /api/produtos        - Criar novo produto
PUT    /api/produtos/123    - Atualizar produto
DELETE /api/produtos/123    - Remover produto
```""",

    "mvc": """**MVC (Model-View-Controller)**

É um padrão de arquitetura que separa a aplicação em três componentes:

**Model**: Representa os dados e regras de negócio
- Entidades, DTOs, repositórios
- Lógica de domínio
- Validações

**View**: Responsável pela apresentação
- Interfaces de usuário
- Templates, componentes
- Exibição de dados

**Controller**: Gerencia o fluxo da aplicação
- Recebe requisições
- Coordena Model e View
- Processa entrada do usuário

**Benefícios:**
- Separação de responsabilidades
- Reutilização de componentes
- Desenvolvimento paralelo
- Manutenibilidade""",

    "async_await": """**Async/Await**

É um padrão para programação assíncrona que torna código assíncrono
parecer síncrono, melhorando legibilidade.

**Conceitos chave:**
- **async**: Marca método como assíncrono
- **await**: Aguarda conclusão de operação assíncrona
- **Task**: Representa operação assíncrona

**Exemplo em C#:**
```csharp
// Sem async/await (bloqueante)
public string ObterDados() {
    var dados = httpClient.GetStringAsync("url").Result; // bloqueia thread
    return dados;
}

// Com async/await (não bloqueante)
public async Task<string> ObterDadosAsync() {
    var dados = await httpClient.GetStringAsync("url"); // não bloqueia
    return dados;
}
```

**Benefícios:**
- Não bloqueia threads
- Melhora escalabilidade
- Código mais legível
- Melhor uso de recursos""",

    "heranca": """**Herança**

É um mecanismo onde uma classe (filha) herda características de outra classe (pai).

**Conceitos:**
- **Classe base/pai**: Define comportamentos comuns
- **Classe derivada/filha**: Herda e pode estender comportamentos
- **override**: Sobrescreve método da classe base
- **base**: Chama implementação da classe base

**Exemplo em C#:**
```csharp
public class Animal {
    public virtual void Falar() {
        Console.WriteLine("Som genérico");
    }
}

public class Cachorro : Animal {
    public override void Falar() {
        Console.WriteLine("Au au!");
    }
}
```

**Benefícios:**
- Reutilização de código
- Hierarquia lógica
- Polimorfismo
- Manutenibilidade

**Cuidados:**
- Evitar herança profunda
- Usar quando tem relação "é um"
- Preferir composição quando possível""",

    "polimorfismo": """**Polimorfismo**

É a capacidade de objetos de diferentes tipos responderem à mesma mensagem
de formas diferentes.

**Tipos de polimorfismo:**

1. **Polimorfismo de sobrecarga** (compile-time):
```csharp
public void Processar(int numero) { }
public void Processar(string texto) { }
```

2. **Polimorfismo de sobrescrita** (runtime):
```csharp
public class Animal {
    public virtual void Falar() { }
}
public class Cachorro : Animal {
    public override void Falar() { Console.WriteLine("Au au!"); }
}
```

3. **Polimorfismo de interface**:
```csharp
public interface IVoador {
    void Voar();
}
public class Passaro : IVoador { }
public class Aviao : IVoador { }
```

**Benefícios:**
- Flexibilidade do código
- Extensibilidade
- Código mais genérico
- Design mais limpo""",

    "encapsulamento": """**Encapsulamento**

É o princípio de esconder detalhes internos e expor apenas o necessário.

**Conceitos:**
- **Campos privados**: Dados internos protegidos
- **Propriedades públicas**: Acesso controlado
- **Métodos públicos**: Interface pública
- **Modificadores de acesso**: Controlam visibilidade

**Exemplo em C#:**
```csharp
public class ContaBancaria {
    private decimal _saldo;  // campo privado

    public decimal Saldo {   // propriedade pública
        get { return _saldo; }
        private set { _saldo = value; }
    }

    public void Depositar(decimal valor) {
        if (valor > 0)
            _saldo += valor;
    }
}
```

**Benefícios:**
- Proteção de dados
- Controle de acesso
- Facilita mudanças internas
- Reduz acoplamento""",

    "abstracao": """**Abstração**

É o processo de esconder detalhes complexos e expor apenas funcionalidades essenciais.

**Níveis de abstração:**
- **Classe abstrata**: Define contrato mas não pode ser instanciada
- **Interface**: Define contrato sem implementação
- **Método abstrato**: Define assinatura sem implementação

**Exemplo em C#:**
```csharp
public abstract class FormaGeometrica {
    public abstract double CalcularArea();  // método abstrato
    public void Desenhar() {
        Console.WriteLine("Desenhando forma...");
    }
}

public class Circulo : FormaGeometrica {
    private double _raio;
    public override double CalcularArea() {
        return Math.PI * _raio * _raio;
    }
}
```

**Benefícios:**
- Simplifica complexidade
- Foca no "o que" não no "como"
- Reutilização
- Manutenibilidade""",

    "interface": """**Interface**

É um contrato que define comportamentos que uma classe deve implementar.

**Características:**
- Define apenas assinaturas de métodos
- Não contém implementação
- Uma classe pode implementar múltiplas interfaces
- Promove loose coupling

**Exemplo em C#:**
```csharp
public interface IRepository<T> {
    T ObterPorId(int id);
    IEnumerable<T> ObterTodos();
    void Adicionar(T entity);
    void Remover(int id);
}

public class ProdutoRepository : IRepository<Produto> {
    // Implementação dos métodos
}
```

**Benefícios:**
- Desacoplamento
- Testabilidade (mock de interfaces)
- Flexibilidade
- Contrato claro

**Boas práticas:**
- Interfaces pequenas e focadas (ISP)
- Nomes descritivos (I prefix)
- Versionamento cuidadoso"""
}


def obter_arquitetura(tipo_projeto: str) -> dict:
    """Obtém sugestão de arquitetura para um tipo de projeto."""
    tipo_normalizado = tipo_projeto.lower().replace(" ", "_")
    for chave, valor in ARQUITETURAS.items():
        if chave in tipo_normalizado or tipo_normalizado in chave:
            return valor
    return None


def explicar_conceito(conceito: str) -> str:
    """Explica um conceito de programação."""
    conceito_normalizado = conceito.lower().replace(" ", "_")
    for chave, explicacao in CONCEITOS_EXPLICACOES.items():
        if chave in conceito_normalizado or conceito_normalizado in chave:
            return explicacao
    return f"Conceito '{conceito}' não encontrado na base de conhecimento."