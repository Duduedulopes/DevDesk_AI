# DevDesk AI 🤖

> **IDE local com agente próprio**


![DevDesk AI](https://img.shields.io/badge/DevDesk-AI-green)
![Python](https://img.shields.io/badge/Python-3.8+-blue)


## 🌟 Sobre


DevDesk AI é um ambiente de desenvolvimento inteiro na máquina: editor Monaco, chat que age, terminal, busca, GitHub e paletas, com um agente que conserta e cria código.


**Roda inteiro na máquina.** O padrão é local e sem nuvem: redes próprias em NumPy, grep no projeto, `dotnet build` e `ast.parse` como juízes. APIs externas (ChatGPT, Gemini, Claude, GitHub privado) só entram com chave sua — e o seletor deixa claro quando o chat sai da máquina.


O **motor** é escrito do zero, em NumPy: camada, ativação, custo e retropropagação são código próprio e auditáveis, com o gradiente conferido contra a derivada numérica. Para os **olhos e os ouvidos** (CLIP e Whisper) o projeto usa pesos pré-treinados, baixados uma vez e rodando offline dali em diante — treinar percepção do zero exige bilhões de exemplos, e esse custo não se repete.


## ✨ Características


- **🧠 Motor Próprio**: redes densas, retropropagação e custo escritos do zero com NumPy, com prova numérica do gradiente
- **🤖 Agente que prova**: laço perceber → escolher ferramenta → usar → re-julgar; só o conserto aprovado vira diff com `[s/N]`
- **🖥️ IDE de verdade**: activity bar, Explorer, editor Monaco com abas, chat IA à direita, terminal embaixo, paletas `Ctrl+P` / `Ctrl+Shift+P`, busca `Ctrl+Shift+F`
- **⌨️ Tab fantasma e Ctrl+K**: completa só com o que o projeto já escreveu (medido em pasta inédita, n=80: 100% de precisão, 0% de sugestão errada); extrai método/variável com molde + juiz
- **📦 Fila multi-arquivo**: N erros viram N diffs + cartão lote (aceitar/recusar tudo)
- **🐙 GitHub**: buscar projetos públicos e clonar para a IDE sem sair do painel
- **🧩 Extensões e `regras.md`**: liga/desliga as ferramentas do agente; convenções do projeto (`nomes:`, `ignorar:`) que o código realmente lê
- **👁️ Percepção Pré-treinada**: CLIP (imagem) e Whisper (áudio) com pesos baixados uma vez — offline dali em diante
- **🔍 Investigação Inteligente**: Coleta evidências do sistema sem alterações
- **⚡ Ação Controlada**: Executa comandos com confirmação e capacidade de desfazer
- **🗜️ Compressão Própria**: DEFLATE e gzip escritos do zero, conferidos byte a byte contra o `zlib`
- **🎨 Dois temas**: fósforo verde anos 90 (padrão) e cinza neutro tipo Cursor/VS Code
- **🔒 Privacidade Total**: Tudo roda localmente por padrão; seus dados só saem com sua chave


## 🏗️ Arquitetura


O laço do agente — o `consertar.py` com um catálogo no lugar da ação única:

```
erro do juiz ──▶ PERCEBER (linha, código, mensagem)
                        ▼
                   ESCOLHER a ferramenta (rede ou regra)
                        ▼
                   USAR (ler · procurar · consertar · julgar · terminal)
                        ▼
                   VER O QUE VOLTOU ──▶ juiz de novo ──▶ provado? ──▶ diff + [s/N]
```

A política escolhe a FERRAMENTA; o argumento sai do estado por `==` (nunca palpite da rede). A régua é sempre a mesma que reprovou o código, e cada peça nova só entra se bater a regra numa pasta que o treino não viu (medido: regra 5/5 × rede 5/5 no caminho do painel; Python 321/339, C# 3/3).


### Níveis de Resolução


| Nível | O que o sistema faz | Do que precisa |
|-------|---------------------|----------------|
| **N1** | Reconhece o problema e aplica procedimento conhecido | Classificador + base de casos |
| **N2** | Não reconhece: colhe evidência da máquina e correlaciona | Percepção + investigação |
| **N3** | Evidência não fecha: o agente entra no código com diff e juiz | Laço do agente + Monaco |
| **Desenvolvimento** | O sistema cria projetos do zero e executa pedidos | Criador + terminal com freios |


## 🚀 Como Usar


### Instalação


```bash
# Clone o repositório
git clone https://github.com/Duduedulopes/DevDesk_AI.git
cd DevDesk_AI


# Instale as dependências
pip install -r requirements.txt
```


### Iniciar a IDE


```bash
# Abre a janela (ou o navegador, sem pywebview)
python painel/app.py


# Acesse no navegador
# http://127.0.0.1:8770
```


### Estrutura de Diretórios


```
DevDesk_AI/
├── nucleo/           # Motor da rede neural (Camada, Rede, Ativação, Custo)
├── modelo/           # O agente: laço, políticas, moldes, ferramentas,
│                     # comandos Cmd+K, Tab, regras, github, llm
├── texto/            # Processamento de texto (vocabulário, trigramas)
├── visao/            # CNN do zero e processamento de imagens
├── audio/            # FFT e espectrograma para áudio
├── conhecimento/     # Base de casos e memória do sistema
├── acao/             # Sistema de ações com risco e confirmação
├── painel/           # Servidor web e interface da IDE (Monaco vendorizado)
├── dados/            # Logs, conversas, chaves locais
├── modelos/          # Modelos treinados e checkpoints
├── programas/        # CLI (consertar), treinos e medições
├── provas/           # Testes, juízes e validações
└── caderno/          # Diário de bordo do desenvolvimento
```


## 🎯 Funcionalidades Principais


### 1. O agente no código
- Erro de compilação/execução no chat → passos visíveis (`ler` → `procurar` → `consertar`) → diff no Monaco → aceitar/recusar, um por um ou em lote
- Fila multi-arquivo: cada conserto provado vira o seu cartão
- `regras.md` do projeto: `nomes:` que o leitor não extrai, `ignorar:` que o procurar e o Tab pulam (o juiz não pula nada)


### 2. A IDE
- Editor Monaco com abas, Explorer com ícones por tipo, terminal redimensionável, status bar
- Paletas `Ctrl+P` (arquivos) e `Ctrl+Shift+P` (comandos), busca `Ctrl+Shift+F`, `Ctrl+K` (extrair método/variável)
- Aba GitHub: buscar projetos e clonar para a IDE
- Seletor de agente no topo: DevDesk local, ChatGPT, Gemini, Claude (externos respondem só conversa, com sua chave)


### 3. Investigação Segura
Comandos que **apenas leem** o sistema:
- Status de serviços
- Análise de logs
- Espaço em disco
- Versões de software
- Processos travados
- Estrutura de projetos


### 4. Ação Controlada
Toda alteração passa por:
1. **Nível de risco** declarado antes
2. **Confirmação** explícita do usuário
3. **Registro** completo da ação
4. **Capacidade de desfazer**


### 5. Percepção Multimodal
- **Texto**: Normalização → trigramas → peças
- **Imagem (print)**: CNN → região de texto → caractere → OCR
- **Áudio**: Janela → FFT → espectrograma de mel → CNN
- **Vídeo**: Quadros → CNN + análise de movimento


## 🧪 Testes e Validação


```bash
# A suite inteira
python -m pytest provas/ -q


# O motor: gradiente conferido contra a derivada numérica, MNIST, camadas
python -m pytest provas/test_nucleo.py -q


# A compressão: o que eu escrevo o zlib lê, e o contrário também
python provas/conferir_deflate.py


# Os modelos treinados
python testar_modelos.py
```


## 📊 Progresso do Projeto


| # | Degrau | Status |
|---|--------|--------|
| 1 | Motor NumPy + provas passando | ✅ |
| 2 | Agente com diff, juiz e `[s/N]` (Python + C#) | ✅ |
| 3 | Rede × regra medidas em pasta inédita | ✅ |
| 4 | IDE: shell, Monaco, terminal, paletas, busca | ✅ |
| 5 | Tab fantasma, Cmd+K, fila multi-arquivo, `regras.md` | ✅ |
| 6 | GitHub (buscar/clonar) e seletor de agente externo | ✅ |
| 7 | Percepção (CLIP/Whisper offline) e investigação | 🚧 |
| 8 | Instalador de extensões de terceiros | ⏳ |


## 🛠️ Stack Tecnológica


- **Python 3.8+**: Linguagem principal
- **NumPy**: o motor da rede — tudo que aprende é escrito aqui
- **Monaco (vendorizado)**: o mesmo editor do VS Code, sem CDN
- **tkinter (stdlib)**: diálogo nativo de abrir pasta/arquivo
- **pywebview (opcional)**: janela nativa; sem ele, abre no navegador
- **OpenCV / Pillow**: leitura e preparo de imagem
- **open-clip-torch + torch**: os pesos do CLIP (percepção visual, pré-treinada)
- **faster-whisper**: os pesos do Whisper (transcrição de áudio, pré-treinada)
- **HTTP Server**: servidor web (biblioteca padrão)
- **PowerShell**: integração com o Windows


> As duas linhas de percepção são a única coisa que o projeto não escreveu:
> são pesos pré-treinados, baixados uma vez e usados offline.
> motor, agente, moldes, Tab, compressão, é código deste repositório.


## 📝 Contribuindo


Este é um projeto de estudo, escrito para aprender como cada peça funciona
por dentro. Se algo aqui te for útil, use à vontade, e se achar um erro,
abre uma issue: erro medido vale mais que elogio.


## 📄 Licença


Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.


## 👨‍💻 Autor


**Eduardo Lopes** - 2026


## 🌐 Site do Projeto


Conheça o DevDesk AI pelo site publicitário — a tese, as camadas, o estado atual de cada degrau e o painel em ação:


- **https://duduedulopes.github.io/DevDesk_AI/**
