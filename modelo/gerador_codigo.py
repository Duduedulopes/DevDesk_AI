"""Gerador de código com templates para as novas intenções de desenvolvimento.

Este módulo implementa geração de código baseada em templates para as
novas intenções: gerar_codigo, criar_projeto_completo, implementar_funcionalidade,
escrever_classe, escrever_funcao.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional


class GeradorDeCodigo:
    """Gerador de código baseado em templates."""

    def __init__(self):
        self.templates_csharp = self._carregar_templates_csharp()
        self.templates_python = self._carregar_templates_python()
        self.templates_javascript = self._carregar_templates_javascript()

    def _carregar_templates_csharp(self) -> Dict:
        """Templates para C#."""
        return {
            "calculadora": '''using System;

namespace Calculadora
{{
    public class Program
    {{
        public static void Main(string[] args)
        {{
            Console.WriteLine("Calculadora em C#");
            Console.WriteLine("Operações: +, -, *, /");
            Console.Write("Digite a operação: ");
            string operacao = Console.ReadLine();

            Console.Write("Digite o primeiro número: ");
            double num1 = double.Parse(Console.ReadLine());

            Console.Write("Digite o segundo número: ");
            double num2 = double.Parse(Console.ReadLine());

            double resultado = 0;

            switch (operacao)
            {{
                case "+":
                    resultado = num1 + num2;
                    break;
                case "-":
                    resultado = num1 - num2;
                    break;
                case "*":
                    resultado = num1 * num2;
                    break;
                case "/":
                    resultado = num1 / num2;
                    break;
                default:
                    Console.WriteLine("Operação inválida");
                    return;
            }}

            Console.WriteLine($"Resultado: {{resultado}}");
        }}
    }}
}}''',

            "classe_padrao": '''namespace {namespace}
{{
    public class {nome_classe}
    {{
        public {nome_classe}()
        {{
            // Construtor
        }}

        public void MetodoExemplo()
        {{
            // Implementação
        }}
    }}
}}''',

            "funcao_soma": '''public static double Soma(double a, double b)
{{
    return a + b;
}}''',

            "crud": '''using System;
using System.Collections.Generic;
using System.Linq;

namespace {namespace}
{{
    public class {entidade}Repository
    {{
        private List<{entidade}> _entidades = new List<{entidade}}();

        public void Adicionar({entidade} entidade)
        {{
            _entidades.Add(entidade);
        }}

        public {entidade} ObterPorId(int id)
        {{
            return _entidades.FirstOrDefault(e => e.Id == id);
        }}

        public IEnumerable<{entidade}> ObterTodos()
        {{
            return _entidades;
        }}

        public void Atualizar({entidade} entidade)
        {{
            var existente = ObterPorId(entidade.Id);
            if (existente != null)
            {{
                // Atualizar propriedades
            }}
        }}

        public void Remover(int id)
        {{
            var entidade = ObterPorId(id);
            if (entidade != null)
            {{
                _entidades.Remove(entidade);
            }}
        }}
    }}
}}''',

            "api_rest_completa": '''using Microsoft.AspNetCore.Mvc;
using System.Collections.Generic;
using System.Linq;

namespace {namespace}.Controllers
{{
    [ApiController]
    [Route("api/[controller]")]
    public class {entidade}Controller : ControllerBase
    {{
        private readonly I{entidade}Repository _repository;

        public {entidade}Controller(I{entidade}Repository repository)
        {{
            _repository = repository;
        }}

        [HttpGet]
        public ActionResult<IEnumerable<{entidade}>> ObterTodos()
        {{
            var entidades = _repository.ObterTodos();
            return Ok(entidades);
        }}

        [HttpGet("{{id}}")]
        public ActionResult<{entidade}> ObterPorId(int id)
        {{
            var entidade = _repository.ObterPorId(id);
            if (entidade == null)
                return NotFound();
            return Ok(entidade);
        }}

        [HttpPost]
        public ActionResult<{entidade}> Criar([FromBody] {entidade} entidade)
        {{
            if (!ModelState.IsValid)
                return BadRequest(ModelState);

            _repository.Adicionar(entidade);
            return CreatedAtAction(nameof(ObterPorId), new {{ id = entidade.Id }}, entidade);
        }}

        [HttpPut("{{id}}")]
        public ActionResult Atualizar(int id, [FromBody] {entidade} entidade)
        {{
            if (id != entidade.Id)
                return BadRequest();

            if (!ModelState.IsValid)
                return BadRequest(ModelState);

            _repository.Atualizar(entidade);
            return NoContent();
        }}

        [HttpDelete("{{id}}")]
        public ActionResult Remover(int id)
        {{
            var entidade = _repository.ObterPorId(id);
            if (entidade == null)
                return NotFound();

            _repository.Remover(id);
            return NoContent();
        }}
    }}
}}

// Repository Interface
public interface I{entidade}Repository
{{
    {entidade} ObterPorId(int id);
    IEnumerable<{entidade}> ObterTodos();
    void Adicionar({entidade} entidade);
    void Atualizar({entidade} entidade);
    void Remover(int id);
}}

// Entity
public class {entidade}
{{
    public int Id {{ get; set; }}
    // Adicione outras propriedades aqui
}}''',

            "autenticacao_jwt": '''using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.IdentityModel.Tokens;
using System;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;

namespace {namespace}.Controllers
{{
    [ApiController]
    [Route("api/[controller]")]
    public class AuthController : ControllerBase
    {{
        private readonly string _secretKey = "SuaChaveSecretaSuperSegura123!";
        private readonly string _issuer = "SeuIssuer";
        private readonly string _audience = "SuaAudience";

        [HttpPost("login")]
        public IActionResult Login([FromBody] LoginRequest request)
        {{
            // Validação do usuário (substituir por lógica real)
            if (request.Username == "admin" && request.Password == "senha123")
            {{
                var token = GenerateJwtToken(request.Username);
                return Ok(new {{ token }});
            }}

            return Unauthorized("Credenciais inválidas");
        }}

        private string GenerateJwtToken(string username)
        {{
            var securityKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_secretKey));
            var credentials = new SigningCredentials(securityKey, SecurityAlgorithms.HmacSha256);

            var claims = new[]
            {{
                new Claim(JwtRegisteredClaimNames.Sub, username),
                new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
                new Claim(ClaimTypes.Name, username)
            }};

            var token = new JwtSecurityToken(
                issuer: _issuer,
                audience: _audience,
                claims: claims,
                expires: DateTime.Now.AddHours(1),
                signingCredentials: credentials
            );

            return new JwtSecurityTokenHandler().WriteToken(token);
        }}
    }}

    public class LoginRequest
    {{
        public string Username {{ get; set; }}
        public string Password {{ get; set; }}
    }}
}}

// Startup configuration
public void ConfigureServices(IServiceCollection services)
{{
    services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
        .AddJwtBearer(options =>
        {{
            options.TokenValidationParameters = new TokenValidationParameters
            {{
                ValidateIssuer = true,
                ValidateAudience = true,
                ValidateLifetime = true,
                ValidateIssuerSigningKey = true,
                ValidIssuer = "SeuIssuer",
                ValidAudience = "SuaAudience",
                IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes("SuaChaveSecretaSuperSegura123!"))
            }};
        }});
    
    services.AddAuthorization();
}}''',

            "docker_webapi": '''FROM mcr.microsoft.com/dotnet/aspnet:7.0 AS base
WORKDIR /app
EXPOSE 80
EXPOSE 443

FROM mcr.microsoft.com/dotnet/sdk:7.0 AS build
WORKDIR /src
COPY ["SeuProjeto.csproj", "./"]
RUN dotnet restore "SeuProjeto.csproj"
COPY . .
WORKDIR "/src/."
RUN dotnet build "SeuProjeto.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "SeuProjeto.csproj" -c Release -o /app/publish

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "SeuProjeto.dll"]''',

            "github_actions_ci": '''name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Setup .NET
      uses: actions/setup-dotnet@v3
      with:
        dotnet-version: '7.0.x'

    - name: Restore dependencies
      run: dotnet restore

    - name: Build
      run: dotnet build --no-restore

    - name: Test
      run: dotnet test --no-build --verbosity normal

    - name: Publish
      run: dotnet publish -c Release -o ./publish

    - name: Deploy to Azure
      if: github.ref == 'refs/heads/main'
      uses: azure/webapps-deploy@v2
      with:
        app-name: 'seu-app-name'
        publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
        package: ./publish''',

            "teste_unitario": '''using Xunit;
using {namespace};

namespace {namespace}.Tests
{{
    public class {entidade}Tests
    {{
        [Fact]
        public void Criar_{entidade}_ComDadosValidos_DeveRetornarSucesso()
        {{
            // Arrange
            var entidade = new {entidade}
            {{
                // Configure propriedades
            }};

            // Act
            var resultado = entidade.IsValid();

            // Assert
            Assert.True(resultado);
        }}

        [Theory]
        [InlineData("")]
        [InlineData(null)]
        public void Validar_{entidade}_ComDadosInvalidos_DeveRetornarFalha(string dadoInvalido)
        {{
            // Arrange
            var entidade = new {entidade}
            {{
                // Configure com dado inválido
            }};

            // Act
            var resultado = entidade.IsValid();

            // Assert
            Assert.False(resultado);
        }}
    }}
}}''',
        }

    def _carregar_templates_python(self) -> Dict:
        """Templates para Python."""
        return {
            "calculadora": '''def calculadora():
    """Calculadora simples em Python."""
    print("Calculadora em Python")
    print("Operações: +, -, *, /")

    operacao = input("Digite a operação: ")
    num1 = float(input("Digite o primeiro número: "))
    num2 = float(input("Digite o segundo número: "))

    if operacao == "+":
        resultado = num1 + num2
    elif operacao == "-":
        resultado = num1 - num2
    elif operacao == "*":
        resultado = num1 * num2
    elif operacao == "/":
        resultado = num1 / num2
    else:
        print("Operação inválida")
        return

    print(f"Resultado: {resultado}")

if __name__ == "__main__":
    calculadora()''',

            "classe_padrao": '''class {nome_classe}:
    """Classe {nome_classe}."""

    def __init__(self):
        """Construtor."""
        pass

    def metodo_exemplo(self):
        """Método de exemplo."""
        pass''',

            "funcao_soma": '''def soma(a: float, b: float) -> float:
    """Soma dois números."""
    return a + b''',

            "crud": '''from typing import List, Optional
from dataclasses import dataclass

@dataclass
class {entidade}:
    id: int
    # Adicione outros campos aqui

class {entidade}Repository:
    """Repositório para {entidade}."""

    def __init__(self):
        self._entidades: List[{entidade}] = []

    def adicionar(self, entidade: {entidade}) -> None:
        """Adiciona uma entidade."""
        self._entidades.append(entidade)

    def obter_por_id(self, id: int) -> Optional[{entidade}]:
        """Obtém entidade por ID."""
        for entidade in self._entidades:
            if entidade.id == id:
                return entidade
        return None

    def obter_todos(self) -> List[{entidade}]:
        """Obtém todas as entidades."""
        return self._entidades.copy()

    def atualizar(self, entidade: {entidade}) -> bool:
        """Atualiza uma entidade."""
        for i, e in enumerate(self._entidades):
            if e.id == entidade.id:
                self._entidades[i] = entidade
                return True
        return False

    def remover(self, id: int) -> bool:
        """Remove uma entidade."""
        for i, entidade in enumerate(self._entidades):
            if entidade.id == id:
                self._entidades.pop(i)
                return True
        return False''',

            "api_rest_fastapi": '''from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="{namespace} API", version="1.0.0")

# Models
class {entidade}Base(BaseModel):
    # Adicione campos aqui
    pass

class {entidade}Create({entidade}Base):
    pass

class {entidade}({entidade}Base):
    id: int

    class Config:
        orm_mode = True

# Database (simplified - use real DB in production)
_db: List[{entidade}] = []
_counter = 0

# Routes
@app.get("/api/{entidade.lower()}", response_model=List[{entidade}])
async def obter_todos():
    """Obtém todas as entidades."""
    return _db

@app.get("/api/{entidade.lower()}/{{entidade_id}}", response_model={entidade})
async def obter_por_id(entidade_id: int):
    """Obtém entidade por ID."""
    entidade = next((e for e in _db if e.id == entidade_id), None)
    if not entidade:
        raise HTTPException(status_code=404, detail="Entidade não encontrada")
    return entidade

@app.post("/api/{entidade.lower()}", response_model={entidade})
async def criar(entidade: {entidade}Create):
    """Cria nova entidade."""
    global _counter
    _counter += 1
    nova_entidade = {entidade}(id=_counter, **entidade.dict())
    _db.append(nova_entidade)
    return nova_entidade

@app.put("/api/{entidade.lower()}/{{entidade_id}}", response_model={entidade})
async def atualizar(entidade_id: int, entidade: {entidade}Create):
    """Atualiza entidade existente."""
    existente = next((e for e in _db if e.id == entidade_id), None)
    if not existente:
        raise HTTPException(status_code=404, detail="Entidade não encontrada")
    
    for key, value in entidade.dict().items():
        setattr(existente, key, value)
    
    return existente

@app.delete("/api/{entidade.lower()}/{{entidade_id}}")
async def remover(entidade_id: int):
    """Remove entidade."""
    global _db
    _db = [e for e in _db if e.id != entidade_id]
    return {{"message": "Entidade removida com sucesso"}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)''',

            "autenticacao_jwt": '''from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional

app = FastAPI()

# Configurações
SECRET_KEY = "sua-chave-secreta-super-segura"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica senha."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Gera hash da senha."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria token JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({{"exp": expire}})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtém usuário atual do token."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    return username

@app.post("/login")
async def login(username: str, password: str):
    """Endpoint de login."""
    # Substituir por lógica real de autenticação
    if username == "admin" and password == "senha123":
        access_token = create_access_token(data={{"sub": username}})
        return {{"access_token": access_token, "token_type": "bearer"}}
    
    raise HTTPException(status_code=401, detail="Credenciais inválidas")

@app.get("/protected")
async def protected_route(current_user: str = Depends(get_current_user)):
    """Rota protegida."""
    return {{"message": f"Olá, {{current_user}}! Você está autenticado."}}''',

            "docker_fastapi": '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]''',

            "github_actions_python": '''name: Python CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        pytest --cov=. --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Deploy to server
      run: |
        # Adicione comandos de deploy aqui
        echo "Deploy para produção"''',

            "teste_unitario": '''import pytest
from {namespace} import {entidade}

class Test{entidade}:
    """Testes para {entidade}."""

    def test_criar_entidade_valida(self):
        """Testa criação de entidade válida."""
        entidade = {entidade}(id=1)
        assert entidade.id == 1

    @pytest.mark.parametrize("dado_invalido", ["", None])
    def test_validar_entidade_invalida(self, dado_invalido):
        """Testa validação de entidade inválida."""
        with pytest.raises(ValueError):
            {entidade}(id=dado_invalido)

    def test_atualizar_entidade(self):
        """Testa atualização de entidade."""
        entidade = {entidade}(id=1)
        # Adicione lógica de atualização
        assert True  # Substituir por assert real''',
        }

    def _carregar_templates_javascript(self) -> Dict:
        """Templates para JavaScript."""
        return {
            "calculadora": '''function calculadora() {
    console.log("Calculadora em JavaScript");
    console.log("Operações: +, -, *, /");

    const operacao = prompt("Digite a operação:");
    const num1 = parseFloat(prompt("Digite o primeiro número:"));
    const num2 = parseFloat(prompt("Digite o segundo número:"));

    let resultado;

    switch (operacao) {
        case "+":
            resultado = num1 + num2;
            break;
        case "-":
            resultado = num1 - num2;
            break;
        case "*":
            resultado = num1 * num2;
            break;
        case "/":
            resultado = num1 / num2;
            break;
        default:
            console.log("Operação inválida");
            return;
    }

    console.log(`Resultado: ${resultado}`);
}

calculadora();''',

            "classe_padrao": '''class {nome_classe} {{
    constructor() {{
        // Construtor
    }}

    metodoExemplo() {{
        // Implementação
    }}
}}''',

            "funcao_soma": '''function soma(a, b) {{
    return a + b;
}}''',

            "crud": '''class {entidade}Repository {{
    constructor() {{
        this.entidades = [];
    }}

    adicionar(entidade) {{
        this.entidades.push(entidade);
    }}

    obterPorId(id) {{
        return this.entidades.find(e => e.id === id);
    }}

    obterTodos() {{
        return [...this.entidades];
    }}

    atualizar(entidade) {{
        const index = this.entidades.findIndex(e => e.id === entidade.id);
        if (index !== -1) {{
            this.entidades[index] = entidade;
            return true;
        }}
        return false;
    }}

    remover(id) {{
        const index = this.entidades.findIndex(e => e.id === id);
        if (index !== -1) {{
            this.entidades.splice(index, 1);
            return true;
        }}
        return false;
    }}
}}''',
        }

    def gerar_calculadora(self, linguagem: str = "csharp") -> str:
        """Gera código de calculadora."""
        if linguagem.lower() in ["c#", "csharp"]:
            return self.templates_csharp["calculadora"]
        elif linguagem.lower() == "python":
            return self.templates_python["calculadora"]
        elif linguagem.lower() in ["js", "javascript"]:
            return self.templates_javascript["calculadora"]
        else:
            return f"Linguagem {linguagem} não suportada para calculadora"

    def gerar_classe(self, nome_classe: str, linguagem: str = "csharp", namespace: str = "MeuProjeto") -> str:
        """Gera código de classe."""
        if linguagem.lower() in ["c#", "csharp"]:
            return self.templates_csharp["classe_padrao"].format(
                nome_classe=nome_classe,
                namespace=namespace
            )
        elif linguagem.lower() == "python":
            return self.templates_python["classe_padrao"].format(
                nome_classe=nome_classe
            )
        elif linguagem.lower() in ["js", "javascript"]:
            return self.templates_javascript["classe_padrao"].format(
                nome_classe=nome_classe
            )
        else:
            return f"Linguagem {linguagem} não suportada para classe"

    def gerar_funcao_soma(self, linguagem: str = "csharp") -> str:
        """Gera função de soma."""
        if linguagem.lower() in ["c#", "csharp"]:
            return self.templates_csharp["funcao_soma"]
        elif linguagem.lower() == "python":
            return self.templates_python["funcao_soma"]
        elif linguagem.lower() in ["js", "javascript"]:
            return self.templates_javascript["funcao_soma"]
        else:
            return f"Linguagem {linguagem} não suportada para função"

    def gerar_crud(self, entidade: str, linguagem: str = "csharp", namespace: str = "MeuProjeto") -> str:
        """Gera código CRUD."""
        if linguagem.lower() in ["c#", "csharp"]:
            return self.templates_csharp["crud"].format(
                entidade=entidade,
                namespace=namespace
            )
        elif linguagem.lower() == "python":
            return self.templates_python["crud"].format(
                entidade=entidade
            )
        elif linguagem.lower() in ["js", "javascript"]:
            return self.templates_javascript["crud"].format(
                entidade=entidade
            )
        else:
            return f"Linguagem {linguagem} não suportada para CRUD"

    def gerar_api_rest(self, entidade: str, linguagem: str = "csharp", namespace: str = "MinhaAPI") -> str:
        """Gera API REST completa."""
        if linguagem.lower() in ["c#", "csharp"]:
            return self.templates_csharp["api_rest_completa"].format(
                entidade=entidade,
                namespace=namespace
            )
        elif linguagem.lower() == "python":
            return self.templates_python["api_rest_fastapi"].format(
                entidade=entidade,
                namespace=namespace
            )
        else:
            return f"Linguagem {linguagem} não suportada para API REST"

    def gerar_autenticacao_jwt(self, linguagem: str = "csharp", namespace: str = "MinhaAPI") -> str:
        """Gera sistema de autenticação JWT."""
        if linguagem.lower() in ["c#", "csharp"]:
            return self.templates_csharp["autenticacao_jwt"].format(
                namespace=namespace
            )
        elif linguagem.lower() == "python":
            return self.templates_python["autenticacao_jwt"]
        else:
            return f"Linguagem {linguagem} não suportada para autenticação JWT"

    def gerar_dockerfile(self, linguagem: str = "csharp", nome_projeto: str = "MeuProjeto") -> str:
        """Gera Dockerfile."""
        if linguagem.lower() in ["c#", "csharp"]:
            return self.templates_csharp["docker_webapi"].replace("SeuProjeto", nome_projeto)
        elif linguagem.lower() == "python":
            return self.templates_python["docker_fastapi"]
        else:
            return f"Linguagem {linguagem} não suportada para Docker"

    def gerar_github_actions(self, linguagem: str = "csharp") -> str:
        """Gera pipeline de CI/CD do GitHub Actions."""
        if linguagem.lower() in ["c#", "csharp"]:
            return self.templates_csharp["github_actions_ci"]
        elif linguagem.lower() == "python":
            return self.templates_python["github_actions_python"]
        else:
            return f"Linguagem {linguagem} não suportada para GitHub Actions"

    def gerar_testes_unitarios(self, entidade: str, linguagem: str = "csharp", namespace: str = "MinhaAPI") -> str:
        """Gera testes unitários."""
        if linguagem.lower() in ["c#", "csharp"]:
            return self.templates_csharp["teste_unitario"].format(
                entidade=entidade,
                namespace=namespace
            )
        elif linguagem.lower() == "python":
            return self.templates_python["teste_unitario"].format(
                entidade=entidade,
                namespace=namespace
            )
        else:
            return f"Linguagem {linguagem} não suportada para testes"

    def extrair_parametros(self, texto: str) -> Dict[str, str]:
        """Extrai parâmetros do texto do usuário."""
        parametros = {}

        # Detectar linguagem
        if "c#" in texto.lower() or "csharp" in texto.lower():
            parametros["linguagem"] = "csharp"
        elif "python" in texto.lower():
            parametros["linguagem"] = "python"
        elif "javascript" in texto.lower() or "js" in texto.lower():
            parametros["linguagem"] = "javascript"
        else:
            parametros["linguagem"] = "csharp"  # padrão

        # Detectar tipo de projeto/entidade
        palavras = texto.split()
        for palavra in palavras:
            if palavra[0].isupper() and len(palavra) > 2:
                if "entidade" not in parametros:
                    parametros["entidade"] = palavra
                break

        return parametros