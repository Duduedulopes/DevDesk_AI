# Guia de Instalação - DevDesk AI

## Requisitos do Sistema

- **Sistema Operacional**: Windows 10/11, Linux ou macOS
- **Python**: 3.8 ou superior
- **Memória RAM**: Mínimo 4GB (recomendado 8GB)
- **Espaço em Disco**: Mínimo 2GB livres

## Instalação Passo a Passo

### 1. Clonar o Repositório

```bash
git clone https://github.com/Duduedulopes/DevDesk_AI.git
cd DevDesk_AI
```

### 2. Criar Ambiente Virtual (Opcional mas Recomendado)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 4. Verificar Instalação

```bash
python -c "import numpy; import cv2; print('Instalação concluída com sucesso!')"
```

## Inicialização

### Iniciar o Servidor Web

```bash
python painel/servidor.py
```

O servidor estará disponível em: `http://localhost:8760`

### Iniciar com Porta Personalizada

```bash
python painel/servidor.py --porta 8080
```

## Estrutura de Diretórios

Após a instalação, você terá a seguinte estrutura:

```
DevDesk_AI/
├── nucleo/              # Motor da rede neural
├── texto/               # Processamento de texto
├── visao/               # CNN e processamento de imagens
├── audio/               # Processamento de áudio
├── conhecimento/        # Base de casos
├── acao/                # Sistema de ações
├── painel/              # Servidor web e interface
├── dados/               # Logs e dados (criado automaticamente)
├── modelos/             # Modelos treinados (criado automaticamente)
├── programas/           # Scripts utilitários
├── provas/              # Testes e validações
├── caderno/             # Diário de desenvolvimento
├── public/              # Site estático para deployment
└── requirements.txt     # Dependências Python
```

## Configuração Inicial

### 1. Criar Diretórios de Dados

Os diretórios `dados/` e `modelos/` serão criados automaticamente na primeira execução, mas você pode criá-los manualmente:

```bash
mkdir dados
mkdir modelos
```

### 2. Configurar Caminhos (se necessário)

Edite o arquivo `painel/servidor.py` se precisar alterar caminhos padrão:

```python
# Linha 414: Caminho para o SO Espacial (se usado)
ap.add_argument("--espacial", default="C:/caminho/para/SO-Espacial")

# Linha 415: URL para AutonomousStore (se usado)
ap.add_argument("--loja", default="http://localhost:5071")
```

## Solução de Problemas

### Python não encontrado

**Windows:**
- Baixe Python em [python.org](https://python.org)
- Durante a instalação, marque "Add Python to PATH"

**Linux:**
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip
```

**macOS:**
```bash
brew install python3
```

### Erro ao instalar OpenCV

```bash
pip install opencv-python-headless
```

### Permissão negada no Windows

Execute o PowerShell como Administrador ou use:

```bash
python painel/servidor.py
```

### Porta já em uso

Mude a porta do servidor:

```bash
python painel/servidor.py --porta 8080
```

Ou mate o processo que está usando a porta 8760:

**Windows:**
```bash
netstat -ano | findstr :8760
taskkill /PID <PID> /F
```

**Linux/macOS:**
```bash
lsof -ti:8760 | xargs kill -9
```

## Próximos Passos

1. **Acesse a Interface**: Abra `http://localhost:8760` no navegador
2. **Explore a Documentação**: Leia o `README.md` para entender a arquitetura
3. **Execute os Testes**: Rode os scripts em `provas/` para validar a instalação
4. **Personalize**: Configure os caminhos e parâmetros conforme necessário

## Suporte

Se encontrar problemas durante a instalação:

1. Verifique se todos os requisitos foram atendidos
2. Consulte a seção de solução de problemas acima
3. Abra uma issue no [GitHub](https://github.com/Duduedulopes/DevDesk_AI/issues)

## Atualização

Para atualizar para a versão mais recente:

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```